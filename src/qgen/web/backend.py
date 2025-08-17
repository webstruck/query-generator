#!/usr/bin/env python3
"""FastAPI backend for qgen web interface."""

import json
import os
import sys
from pathlib import Path
from typing import List, Dict, Any, Optional

from fastapi import FastAPI, HTTPException, BackgroundTasks
from fastapi.middleware.cors import CORSMiddleware
from fastapi.staticfiles import StaticFiles
from pydantic import BaseModel

# Add src to path for imports
sys.path.insert(0, str(Path(__file__).parent.parent.parent))

from qgen.core.config import load_project_config, save_project_config, ConfigurationError  
from qgen.core.models import ProjectConfig, Dimension, Tuple, Query
from qgen.core.generation import generate_tuples as core_generate_tuples, generate_queries as core_generate_queries
from qgen.core.data import get_data_manager
from qgen.core.env import ensure_environment_loaded, get_available_providers, auto_detect_provider
from qgen.core.dimensions import validate_dimensions
from qgen.core.guidance import get_domain_template, list_available_domains

app = FastAPI(title="QGen Web API")

# CORS middleware for development
app.add_middleware(
    CORSMiddleware,
    allow_origins=["http://localhost:5173"],  # Vite dev server
    allow_credentials=True,
    allow_methods=["*"],
    allow_headers=["*"],
)

# Load environment on startup
ensure_environment_loaded(verbose=False)

# Get user's working directory from environment variable
USER_CWD = os.environ.get('QGEN_USER_CWD', os.getcwd())

def get_project_path(project_name: str) -> Path:
    """Get the full path to a project in the user's working directory."""
    return Path(USER_CWD) / project_name

# Pydantic models for API
class ProjectCreateRequest(BaseModel):
    name: str
    template: str

class DimensionRequest(BaseModel):
    name: str
    description: str
    values: List[str]

class TupleGenerationRequest(BaseModel):
    count: int = 20
    provider: Optional[str] = None

class QueryGenerationRequest(BaseModel):
    queries_per_tuple: int = 3
    provider: Optional[str] = None

class QueryUpdateRequest(BaseModel):
    status: str
    text: Optional[str] = None

# API Routes

@app.get("/api/health")
async def health_check():
    """Health check endpoint."""
    return {"status": "ok"}

@app.get("/api/providers")
async def get_providers():
    """Get available LLM providers."""
    providers = get_available_providers()
    auto_provider = auto_detect_provider()
    return {
        "available": providers,
        "auto_detected": auto_provider
    }

@app.get("/api/templates")
async def get_templates():
    """Get available project templates."""
    return {"templates": list_available_domains()}

@app.post("/api/projects")
async def create_project(request: ProjectCreateRequest):
    """Create a new project."""
    try:
        project_path = get_project_path(request.name)
        if project_path.exists():
            raise HTTPException(status_code=400, detail=f"Directory '{request.name}' already exists")
        
        # Create project directory structure
        project_path.mkdir(parents=True)
        (project_path / "data" / "tuples").mkdir(parents=True)
        (project_path / "data" / "queries").mkdir(parents=True)
        (project_path / "data" / "exports").mkdir(parents=True)
        (project_path / "prompts").mkdir(parents=True)
        
        # Get template configuration
        domain_config = get_domain_template(request.template)
        
        # Create project config
        config = ProjectConfig(
            domain=domain_config["name"],
            dimensions=[Dimension(**dim) for dim in domain_config["dimensions"]],
            example_queries=domain_config["example_queries"]
        )
        
        # Save configuration
        save_project_config(config, str(project_path))
        
        # Copy prompt templates
        src_prompts_dir = Path(__file__).parent.parent / "prompts"
        dst_prompts_dir = project_path / "prompts"
        
        if src_prompts_dir.exists():
            import shutil
            for prompt_file in src_prompts_dir.glob("*.txt"):
                shutil.copy2(prompt_file, dst_prompts_dir)
        
        return {"message": f"Project '{request.name}' created successfully", "path": str(project_path)}
        
    except Exception as e:
        raise HTTPException(status_code=500, detail=str(e))

@app.get("/api/projects")
async def list_projects(limit: Optional[int] = None):
    """List available projects in user's working directory, sorted by modification time."""
    user_dir = Path(USER_CWD)
    projects = []
    
    for d in user_dir.iterdir():
        if d.is_dir() and (d / "config.yml").exists():
            try:
                config = load_project_config(str(d))
                projects.append({
                    "name": d.name,
                    "path": str(d),
                    "domain": config.domain,
                    "dimensions_count": len(config.dimensions),
                    "modified_time": d.stat().st_mtime
                })
            except:
                continue
    
    # Sort by modification time, most recent first
    projects.sort(key=lambda x: x["modified_time"], reverse=True)
    
    # Remove modified_time from response (internal use only)
    for project in projects:
        del project["modified_time"]
    
    # Apply limit if specified
    if limit is not None:
        projects = projects[:limit]
    
    return {"projects": projects}

@app.get("/api/projects/{project_name}")
async def get_project(project_name: str):
    """Get project details."""
    try:
        project_path = get_project_path(project_name)
        if not project_path.exists() or not (project_path / "config.yml").exists():
            raise HTTPException(status_code=404, detail="Project not found")
        
        config = load_project_config(str(project_path))
        data_manager = get_data_manager(str(project_path))
        
        # Get data status
        generated_tuples = data_manager.load_tuples("generated")
        approved_tuples = data_manager.load_tuples("approved") 
        generated_queries = data_manager.load_queries("generated")
        approved_queries = data_manager.load_queries("approved")
        
        return {
            "name": project_name,
            "domain": config.domain,
            "dimensions": [
                {
                    "name": dim.name,
                    "description": dim.description,
                    "values": dim.values
                }
                for dim in config.dimensions
            ],
            "example_queries": config.example_queries,
            "data_status": {
                "generated_tuples": len(generated_tuples),
                "approved_tuples": len(approved_tuples),
                "generated_queries": len(generated_queries),
                "approved_queries": len(approved_queries)
            }
        }
        
    except Exception as e:
        raise HTTPException(status_code=500, detail=str(e))

@app.put("/api/projects/{project_name}/dimensions")
async def update_dimensions(project_name: str, dimensions: List[DimensionRequest]):
    """Update project dimensions."""
    try:
        project_path = get_project_path(project_name)
        if not project_path.exists():
            raise HTTPException(status_code=404, detail="Project not found")
        
        config = load_project_config(str(project_path))
        
        # Convert to Dimension objects
        new_dimensions = [
            Dimension(name=dim.name, description=dim.description, values=dim.values)
            for dim in dimensions
        ]
        
        # Validate dimensions
        validation_issues = validate_dimensions(new_dimensions)
        if validation_issues:
            raise HTTPException(status_code=400, detail={"validation_errors": validation_issues})
        
        # Update and save config
        config.dimensions = new_dimensions
        save_project_config(str(project_path), config)
        
        return {"message": "Dimensions updated successfully"}
        
    except Exception as e:
        raise HTTPException(status_code=500, detail=str(e))

@app.post("/api/projects/{project_name}/generate/tuples")
async def generate_tuples(project_name: str, request: TupleGenerationRequest, background_tasks: BackgroundTasks):
    """Generate tuples for project."""
    try:
        project_path = get_project_path(project_name)
        if not project_path.exists():
            raise HTTPException(status_code=404, detail="Project not found")
        
        config = load_project_config(str(project_path))
        
        # Determine provider
        provider = request.provider or auto_detect_provider()
        if not provider:
            raise HTTPException(status_code=400, detail="No LLM provider available")
        
        # Change to project directory for generation
        original_cwd = os.getcwd()
        os.chdir(project_path)
        
        try:
            tuples = core_generate_tuples(config=config, count=request.count, provider_type=provider)
        finally:
            os.chdir(original_cwd)
        
        if not tuples:
            raise HTTPException(status_code=500, detail="No tuples generated")
        
        # Save tuples
        data_manager = get_data_manager(str(project_path))
        data_manager.save_tuples(tuples, "generated", {"provider": provider, "count_requested": request.count})
        
        return {
            "message": f"Generated {len(tuples)} tuples",
            "count": len(tuples),
            "tuples": [{"values": t.values} for t in tuples]
        }
        
    except Exception as e:
        raise HTTPException(status_code=500, detail=str(e))

@app.get("/api/projects/{project_name}/tuples/{stage}")
async def get_tuples(project_name: str, stage: str):
    """Get tuples from specific stage."""
    try:
        project_path = get_project_path(project_name)
        if not project_path.exists():
            raise HTTPException(status_code=404, detail="Project not found")
        
        data_manager = get_data_manager(str(project_path))
        tuples = data_manager.load_tuples(stage)
        
        return {
            "tuples": [{"values": t.values} for t in tuples],
            "count": len(tuples)
        }
        
    except Exception as e:
        raise HTTPException(status_code=500, detail=str(e))

@app.post("/api/projects/{project_name}/tuples/{stage}")
async def save_tuples(project_name: str, stage: str, tuples_data: Dict[str, Any]):
    """Save tuples to specific stage."""
    try:
        project_path = get_project_path(project_name)
        if not project_path.exists():
            raise HTTPException(status_code=404, detail="Project not found")
        
        # Convert to Tuple objects
        tuples = [Tuple(values=t["values"]) for t in tuples_data["tuples"]]
        
        data_manager = get_data_manager(str(project_path))
        data_manager.save_tuples(tuples, stage)
        
        return {"message": f"Saved {len(tuples)} tuples to {stage}"}
        
    except Exception as e:
        raise HTTPException(status_code=500, detail=str(e))

@app.post("/api/projects/{project_name}/generate/queries")
async def generate_queries(project_name: str, request: QueryGenerationRequest):
    """Generate queries from approved tuples."""
    try:
        project_path = get_project_path(project_name)
        if not project_path.exists():
            raise HTTPException(status_code=404, detail="Project not found")
        
        config = load_project_config(str(project_path))
        data_manager = get_data_manager(str(project_path))
        
        # Load approved tuples
        approved_tuples = data_manager.load_tuples("approved")
        if not approved_tuples:
            raise HTTPException(status_code=400, detail="No approved tuples found")
        
        # Determine provider
        provider = request.provider or auto_detect_provider()
        if not provider:
            raise HTTPException(status_code=400, detail="No LLM provider available")
        
        # Change to project directory for generation
        original_cwd = os.getcwd()
        os.chdir(project_path)
        
        try:
            queries = core_generate_queries(
                config=config, 
                tuples=approved_tuples, 
                queries_per_tuple=request.queries_per_tuple,
                provider_type=provider
            )
        finally:
            os.chdir(original_cwd)
        
        if not queries:
            raise HTTPException(status_code=500, detail="No queries generated")
        
        # Save queries
        data_manager.save_queries(queries, "generated", {
            "provider": provider,
            "queries_per_tuple": request.queries_per_tuple,
            "total_tuples": len(approved_tuples)
        })
        
        return {
            "message": f"Generated {len(queries)} queries",
            "count": len(queries),
            "queries": [
                {
                    "id": i,
                    "text": q.generated_text,
                    "status": q.status,
                    "tuple_data": q.tuple_data.values
                }
                for i, q in enumerate(queries)
            ]
        }
        
    except Exception as e:
        raise HTTPException(status_code=500, detail=str(e))

@app.get("/api/projects/{project_name}/queries/{stage}")
async def get_queries(project_name: str, stage: str):
    """Get queries from specific stage."""
    try:
        project_path = get_project_path(project_name)
        if not project_path.exists():
            raise HTTPException(status_code=404, detail="Project not found")
        
        data_manager = get_data_manager(str(project_path))
        queries = data_manager.load_queries(stage)
        
        return {
            "queries": [
                {
                    "id": i,
                    "text": q.generated_text,
                    "status": q.status,
                    "tuple_data": q.tuple_data.values
                }
                for i, q in enumerate(queries)
            ],
            "count": len(queries)
        }
        
    except Exception as e:
        raise HTTPException(status_code=500, detail=str(e))

@app.put("/api/projects/{project_name}/queries/{query_id}")
async def update_query(project_name: str, query_id: int, request: QueryUpdateRequest):
    """Update a specific query."""
    try:
        project_path = get_project_path(project_name)
        if not project_path.exists():
            raise HTTPException(status_code=404, detail="Project not found")
        
        data_manager = get_data_manager(str(project_path))
        queries = data_manager.load_queries("generated")
        
        if query_id >= len(queries):
            raise HTTPException(status_code=404, detail="Query not found")
        
        # Update query
        queries[query_id].status = request.status
        if request.text:
            queries[query_id].generated_text = request.text
        
        # Save back
        data_manager.save_queries(queries, "generated")
        
        return {"message": "Query updated successfully"}
        
    except Exception as e:
        raise HTTPException(status_code=500, detail=str(e))

@app.post("/api/projects/{project_name}/queries/approve")
async def approve_queries(project_name: str, query_ids: List[int]):
    """Approve multiple queries."""
    try:
        project_path = get_project_path(project_name)
        if not project_path.exists():
            raise HTTPException(status_code=404, detail="Project not found")
        
        data_manager = get_data_manager(str(project_path))
        all_queries = data_manager.load_queries("generated")
        
        # Get approved queries
        approved_queries = [all_queries[i] for i in query_ids if i < len(all_queries)]
        for query in approved_queries:
            query.status = "approved"
        
        # Save approved queries
        data_manager.save_queries(approved_queries, "approved")
        
        # Update generated queries status
        for i in query_ids:
            if i < len(all_queries):
                all_queries[i].status = "approved"
        data_manager.save_queries(all_queries, "generated")
        
        return {"message": f"Approved {len(approved_queries)} queries"}
        
    except Exception as e:
        raise HTTPException(status_code=500, detail=str(e))

@app.get("/api/projects/{project_name}/export/{format}")
async def export_data(project_name: str, format: str, stage: str = "approved"):
    """Export project data."""
    try:
        from qgen.core.export import export_dataset
        
        project_path = get_project_path(project_name)
        if not project_path.exists():
            raise HTTPException(status_code=404, detail="Project not found")
        
        if format not in ["csv", "json"]:
            raise HTTPException(status_code=400, detail="Unsupported format")
        
        # Export dataset
        exported_path = export_dataset(str(project_path), format, None, stage)
        
        return {
            "message": f"Exported to {exported_path}",
            "path": exported_path,
            "format": format
        }
        
    except Exception as e:
        raise HTTPException(status_code=500, detail=str(e))

@app.get("/api/projects/{project_name}/download/{filename}")
async def download_file(project_name: str, filename: str):
    """Download exported file."""
    try:
        project_path = get_project_path(project_name)
        file_path = project_path / "data" / "exports" / filename
        
        if not file_path.exists():
            raise HTTPException(status_code=404, detail="File not found")
        
        from fastapi.responses import FileResponse
        return FileResponse(
            path=str(file_path),
            filename=filename,
            media_type='application/octet-stream'
        )
        
    except Exception as e:
        raise HTTPException(status_code=500, detail=str(e))

# Serve static files (React build) in production
frontend_dist = Path(__file__).parent / "frontend" / "dist"
if frontend_dist.exists():
    app.mount("/", StaticFiles(directory=str(frontend_dist), html=True), name="static")

if __name__ == "__main__":
    import uvicorn
    uvicorn.run(app, host="0.0.0.0", port=8000)