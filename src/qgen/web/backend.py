#!/usr/bin/env python3
"""FastAPI backend for qgen web interface."""

import json
import os
import sys
import threading
import time
from pathlib import Path
from typing import List, Dict, Any, Optional

from fastapi import FastAPI, HTTPException, BackgroundTasks, UploadFile, File
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

# RAG imports
from qgen.core.chunk_processing import ChunkProcessor
from qgen.core.rag_generation import FactDataManager
from qgen.core.rag_quality import RAGQueryDataManager, RAGQueryQualityFilter
from qgen.core.rag_models import ChunkData, ExtractedFact, RAGQuery

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

# Global status tracking for generation processes
generation_status = {}
status_lock = threading.Lock()

def update_generation_status(project_name: str, operation: str, current: int, total: int, message: str):
    """Update generation status for a project."""
    with status_lock:
        key = f"{project_name}_{operation}"
        generation_status[key] = {
            "operation": operation,
            "current": current,
            "total": total,
            "message": message,
            "progress": (current / total * 100) if total > 0 else 0,
            "completed": current >= total,
            "timestamp": time.time()
        }

def get_generation_status(project_name: str, operation: str):
    """Get current generation status for a project operation."""
    with status_lock:
        key = f"{project_name}_{operation}"
        return generation_status.get(key)

def clear_generation_status(project_name: str, operation: str):
    """Clear generation status for a project operation."""
    with status_lock:
        key = f"{project_name}_{operation}"
        if key in generation_status:
            del generation_status[key]

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

# RAG-specific Pydantic models
class RAGProjectCreateRequest(BaseModel):
    name: str
    domain: str = "general"

class FactExtractionRequest(BaseModel):
    provider: Optional[str] = None
    chunks_dir: str = "chunks"

class RAGQueryGenerationRequest(BaseModel):
    count: Optional[int] = None
    provider: Optional[str] = None

class MultihopGenerationRequest(BaseModel):
    count: Optional[int] = None
    provider: Optional[str] = None
    queries_per_combo: Optional[int] = None

class FilterRequest(BaseModel):
    min_score: Optional[float] = None
    provider: Optional[str] = None

class ApproveItemsRequest(BaseModel):
    item_ids: List[str]

# Background task functions

def background_generate_tuples(project_name: str, project_path: Path, config: ProjectConfig, count: int, provider: str):
    """Background task for tuple generation with progress tracking."""
    try:
        # Initialize status
        update_generation_status(project_name, "tuples", 0, count, "Initializing tuple generation...")
        
        # Change to project directory
        original_cwd = os.getcwd()
        os.chdir(project_path)
        
        try:
            # We'll need to modify core generation to provide progress callbacks
            # For now, simulate progress updates during generation
            update_generation_status(project_name, "tuples", 1, count, "Processing dimensions...")
            
            tuples = core_generate_tuples(config=config, count=count, provider_type=provider)
            
            if tuples:
                # Update progress to completion
                update_generation_status(project_name, "tuples", len(tuples), count, f"Generated {len(tuples)} tuples")
                
                # Save tuples
                data_manager = get_data_manager(str(project_path))
                data_manager.save_tuples(tuples, "generated", {"provider": provider, "count_requested": count})
                
                # Mark as completed
                update_generation_status(project_name, "tuples", len(tuples), len(tuples), f"Completed: {len(tuples)} tuples generated")
            else:
                update_generation_status(project_name, "tuples", 0, count, "Error: No tuples generated")
                
        finally:
            os.chdir(original_cwd)
            
    except Exception as e:
        update_generation_status(project_name, "tuples", 0, count, f"Error: {str(e)}")

def background_generate_queries(project_name: str, project_path: Path, config: ProjectConfig, approved_tuples, queries_per_tuple: int, provider: str):
    """Background task for query generation with progress tracking."""
    try:
        total_queries = len(approved_tuples) * queries_per_tuple
        
        # Initialize status
        update_generation_status(project_name, "queries", 0, total_queries, "Initializing query generation...")
        
        # Change to project directory
        original_cwd = os.getcwd()
        os.chdir(project_path)
        
        try:
            update_generation_status(project_name, "queries", 1, total_queries, "Processing approved tuples...")
            
            queries = core_generate_queries(
                config=config, 
                tuples=approved_tuples, 
                queries_per_tuple=queries_per_tuple,
                provider_type=provider
            )
            
            if queries:
                # Update progress to completion
                update_generation_status(project_name, "queries", len(queries), total_queries, f"Generated {len(queries)} queries")
                
                # Save queries
                data_manager = get_data_manager(str(project_path))
                data_manager.save_queries(queries, "generated", {
                    "provider": provider,
                    "queries_per_tuple": queries_per_tuple,
                    "total_tuples": len(approved_tuples)
                })
                
                # Mark as completed
                update_generation_status(project_name, "queries", len(queries), len(queries), f"Completed: {len(queries)} queries generated")
            else:
                update_generation_status(project_name, "queries", 0, total_queries, "Error: No queries generated")
                
        finally:
            os.chdir(original_cwd)
            
    except Exception as e:
        update_generation_status(project_name, "queries", 0, total_queries, f"Error: {str(e)}")

# RAG Background Task Functions

def background_extract_facts(project_name: str, project_path: Path, provider: str, chunks_dir: str):
    """Background task for RAG fact extraction with progress tracking."""
    try:
        # Change to project directory
        original_cwd = os.getcwd()
        os.chdir(project_path)
        
        try:
            # Load chunks
            chunk_processor = ChunkProcessor()
            chunks = chunk_processor.load_chunks_from_directory(Path(chunks_dir))
            total_chunks = len(chunks)
            
            if not chunks:
                update_generation_status(project_name, "extract_facts", 0, 1, "Error: No chunks found")
                return
            
            update_generation_status(project_name, "extract_facts", 0, total_chunks, "Starting fact extraction...")
            
            # Load RAG config and set provider
            from qgen.core.rag_models import RAGConfig
            from qgen.core.rag_generation import FactExtractor
            
            config = RAGConfig.load_from_file("config.yml") if Path("config.yml").exists() else RAGConfig(llm_provider=provider)
            config.llm_provider = provider
            
            # Extract facts
            extractor = FactExtractor(config)
            facts, batch_metadata = extractor.extract_facts(chunks)
            
            # Save facts
            if facts:
                fact_manager = FactDataManager()
                fact_manager.save_facts(facts, "generated", batch_metadata=batch_metadata)
                update_generation_status(project_name, "extract_facts", total_chunks, total_chunks, f"Completed: {len(facts)} facts extracted")
            else:
                update_generation_status(project_name, "extract_facts", 0, total_chunks, "Error: No facts extracted")
                
        finally:
            os.chdir(original_cwd)
            
    except Exception as e:
        update_generation_status(project_name, "extract_facts", 0, 1, f"Error: {str(e)}")

def background_generate_rag_queries(project_name: str, project_path: Path, provider: str, count: Optional[int]):
    """Background task for RAG query generation with progress tracking."""
    try:
        # Change to project directory
        original_cwd = os.getcwd()
        os.chdir(project_path)
        
        try:
            # Load approved facts
            fact_manager = FactDataManager()
            approved_facts = fact_manager.load_facts("approved")
            
            if not approved_facts:
                update_generation_status(project_name, "generate_queries", 0, 1, "Error: No approved facts found")
                return
            
            target_count = count or len(approved_facts)
            update_generation_status(project_name, "generate_queries", 0, target_count, "Starting query generation...")
            
            # Load RAG config and set provider
            from qgen.core.rag_models import RAGConfig
            from qgen.core.rag_generation import StandardQueryGenerator
            
            config = RAGConfig.load_from_file("config.yml") if Path("config.yml").exists() else RAGConfig(llm_provider=provider)
            config.llm_provider = provider
            
            # Generate queries - need chunks map for context
            from qgen.core.chunk_processing import ChunkProcessor
            
            # Load chunks to create chunks map
            chunks_directory = project_path / "chunks"
            chunk_processor = ChunkProcessor()
            all_chunks = chunk_processor.load_chunks_from_directory(chunks_directory)
            chunks_map = {chunk.chunk_id: chunk for chunk in all_chunks}
            
            # Generate queries
            generator = StandardQueryGenerator(config)
            queries, batch_metadata = generator.generate_queries_from_facts(approved_facts, chunks_map)
            
            if queries:
                query_manager = RAGQueryDataManager(str(project_path))
                # Convert batch_metadata to dict for RAGQueryDataManager
                metadata_dict = batch_metadata.model_dump() if batch_metadata else {}
                query_manager.save_queries(queries, "generated", metadata=metadata_dict)
                update_generation_status(project_name, "generate_queries", len(queries), target_count, f"Completed: {len(queries)} queries generated")
            else:
                update_generation_status(project_name, "generate_queries", 0, target_count, "Error: No queries generated")
                
        finally:
            os.chdir(original_cwd)
            
    except Exception as e:
        update_generation_status(project_name, "generate_queries", 0, 1, f"Error: {str(e)}")

def background_generate_multihop_queries(project_name: str, project_path: Path, provider: str, count: Optional[int], queries_per_combo: Optional[int]):
    """Background task for RAG multi-hop query generation with progress tracking."""
    try:
        # Change to project directory
        original_cwd = os.getcwd()
        os.chdir(project_path)
        
        try:
            # Load approved facts
            fact_manager = FactDataManager(str(project_path))
            approved_facts = fact_manager.load_facts("approved")
            
            if not approved_facts:
                update_generation_status(project_name, "generate_multihop", 0, 1, "Error: No approved facts found")
                return
            
            target_count = count or 10
            update_generation_status(project_name, "generate_multihop", 0, target_count, "Starting multi-hop query generation...")
            
            # Load RAG config and set provider
            from qgen.core.rag_models import RAGConfig
            from qgen.core.adversarial_generation import AdversarialMultiHopGenerator
            
            config = RAGConfig.load_from_file("config.yml") if Path("config.yml").exists() else RAGConfig(llm_provider=provider)
            config.llm_provider = provider
            
            # Generate multi-hop queries - need chunks map for context
            from qgen.core.chunk_processing import ChunkProcessor
            
            # Load chunks to create chunks map
            chunks_directory = project_path / "chunks"
            chunk_processor = ChunkProcessor()
            all_chunks = chunk_processor.load_chunks_from_directory(chunks_directory)
            chunks_map = {chunk.chunk_id: chunk for chunk in all_chunks}
            
            # Generate multi-hop queries
            generator = AdversarialMultiHopGenerator(config)
            queries = generator.generate_multihop_queries(approved_facts, chunks_map)
            
            # Create batch metadata
            from qgen.core.rag_models import BatchMetadata
            batch_metadata = BatchMetadata(
                stage="generated_multihop",
                llm_model=getattr(generator.llm_provider, 'model_name', 'unknown'),
                provider=provider,
                prompt_template="adversarial_multihop",
                total_items=len(queries),
                success_count=len(queries)
            )
            
            if queries:
                query_manager = RAGQueryDataManager(str(project_path))
                # Convert batch_metadata to dict for RAGQueryDataManager
                metadata_dict = batch_metadata.model_dump() if batch_metadata else {}
                query_manager.save_queries(queries, "generated_multihop", metadata=metadata_dict)
                update_generation_status(project_name, "generate_multihop", len(queries), target_count, f"Completed: {len(queries)} multi-hop queries generated")
            else:
                update_generation_status(project_name, "generate_multihop", 0, target_count, "Error: No multi-hop queries generated")
                
        finally:
            os.chdir(original_cwd)
            
    except Exception as e:
        update_generation_status(project_name, "generate_multihop", 0, 1, f"Error: {str(e)}")

def background_filter_queries(project_name: str, project_path: Path, provider: str, min_score: Optional[float]):
    """Background task for RAG query quality filtering with progress tracking."""
    try:
        # Change to project directory
        original_cwd = os.getcwd()
        os.chdir(project_path)
        
        try:
            # Load generated queries
            query_manager = RAGQueryDataManager(str(project_path))
            queries = query_manager.load_queries("generated")
            
            if not queries:
                update_generation_status(project_name, "filter_queries", 0, 1, "Error: No generated queries found")
                return
            
            update_generation_status(project_name, "filter_queries", 0, len(queries), "Starting quality filtering...")
            
            # Filter queries using configured threshold
            from qgen.core.rag_models import RAGConfig
            config = RAGConfig()
            quality_filter = RAGQueryQualityFilter(provider_type=provider)
            filtered_queries, batch_metadata = quality_filter.filter_queries_by_realism(queries, min_score or config.min_realism_score)
            
            # Save filtered queries
            if filtered_queries:
                query_manager.save_queries(filtered_queries, "filtered", batch_metadata=batch_metadata)
                update_generation_status(project_name, "filter_queries", len(queries), len(queries), f"Completed: {len(filtered_queries)} queries passed filter")
            else:
                update_generation_status(project_name, "filter_queries", len(queries), len(queries), "Completed: No queries passed filter")
                
        finally:
            os.chdir(original_cwd)
            
    except Exception as e:
        update_generation_status(project_name, "filter_queries", 0, 1, f"Error: {str(e)}")

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

@app.get("/api/projects/{project_name}/status/{operation}")
async def get_generation_status_endpoint(project_name: str, operation: str):
    """Get generation status for a project operation."""
    status = get_generation_status(project_name, operation)
    if not status:
        raise HTTPException(status_code=404, detail="No active generation found")
    return status

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
                data_manager = get_data_manager(str(d))
                
                # Get data status
                generated_tuples = data_manager.load_tuples("generated")
                approved_tuples = data_manager.load_tuples("approved") 
                generated_queries = data_manager.load_queries("generated")
                approved_queries = data_manager.load_queries("approved")
                
                projects.append({
                    "name": d.name,
                    "path": str(d),
                    "domain": config.domain,
                    "dimensions_count": len(config.dimensions),
                    "data_status": {
                        "generated_tuples": len(generated_tuples),
                        "approved_tuples": len(approved_tuples),
                        "generated_queries": len(generated_queries),
                        "approved_queries": len(approved_queries)
                    },
                    "type": "dimension",
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
        save_project_config(config, str(project_path))
        
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
        
        # Clear any existing status for this operation
        clear_generation_status(project_name, "tuples")
        
        # Start generation in background
        background_tasks.add_task(
            background_generate_tuples,
            project_name, project_path, config, request.count, provider
        )
        
        return {
            "message": "Tuple generation started",
            "status": "started",
            "count_requested": request.count
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
async def generate_queries(project_name: str, request: QueryGenerationRequest, background_tasks: BackgroundTasks):
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
        
        # Clear any existing status for this operation
        clear_generation_status(project_name, "queries")
        
        # Start generation in background
        background_tasks.add_task(
            background_generate_queries,
            project_name, project_path, config, approved_tuples, request.queries_per_tuple, provider
        )
        
        return {
            "message": "Query generation started",
            "status": "started",
            "expected_count": len(approved_tuples) * request.queries_per_tuple
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

# ========================================
# RAG PROJECT ENDPOINTS
# ========================================

@app.post("/api/rag-projects")
async def create_rag_project(request: RAGProjectCreateRequest):
    """Create a new RAG project."""
    try:
        project_path = get_project_path(request.name)
        if project_path.exists():
            raise HTTPException(status_code=400, detail=f"Directory '{request.name}' already exists")
        
        # Create RAG project directory structure
        project_path.mkdir(parents=True)
        (project_path / "chunks").mkdir(parents=True)
        (project_path / "data" / "facts").mkdir(parents=True)
        (project_path / "data" / "queries").mkdir(parents=True)
        (project_path / "data" / "exports").mkdir(parents=True)
        
        # Create a simple marker file to identify RAG projects
        (project_path / ".rag_project").touch()
        
        # Create basic metadata file
        metadata = {
            "name": request.name,
            "type": "rag",
            "domain": request.domain,
            "created_at": time.time()
        }
        
        with open(project_path / "metadata.json", "w") as f:
            json.dump(metadata, f, indent=2)
        
        return {"message": f"RAG project '{request.name}' created successfully", "path": str(project_path)}
        
    except Exception as e:
        raise HTTPException(status_code=500, detail=str(e))

@app.get("/api/rag-projects")
async def list_rag_projects(limit: Optional[int] = None):
    """List available RAG projects in user's working directory."""
    user_dir = Path(USER_CWD)
    projects = []
    
    for d in user_dir.iterdir():
        if d.is_dir() and (d / ".rag_project").exists():
            try:
                metadata_path = d / "metadata.json"
                if metadata_path.exists():
                    with open(metadata_path) as f:
                        metadata = json.load(f)
                    
                    # Count chunks, facts, and queries
                    chunks_count = len(list((d / "chunks").glob("*.jsonl"))) if (d / "chunks").exists() else 0
                    
                    fact_manager = FactDataManager(str(d))
                    try:
                        generated_facts = fact_manager.load_facts("generated")
                        approved_facts = fact_manager.load_facts("approved")
                    except:
                        generated_facts = []
                        approved_facts = []
                    
                    query_manager = RAGQueryDataManager(str(d))
                    try:
                        generated_queries = query_manager.load_queries("generated")
                        approved_queries = query_manager.load_queries("approved")
                    except:
                        generated_queries = []
                        approved_queries = []
                    
                    projects.append({
                        "name": d.name,
                        "path": str(d),
                        "type": "rag",
                        "domain": metadata.get("domain", "general"),
                        "chunks_count": chunks_count,
                        "data_status": {
                            "generated_facts": len(generated_facts),
                            "approved_facts": len(approved_facts),
                            "generated_queries": len(generated_queries),
                            "approved_queries": len(approved_queries)
                        },
                        "modified_time": d.stat().st_mtime
                    })
            except:
                continue
    
    # Sort by modification time, most recent first
    projects.sort(key=lambda x: x["modified_time"], reverse=True)
    
    # Remove modified_time from response
    for project in projects:
        del project["modified_time"]
    
    # Apply limit if specified
    if limit is not None:
        projects = projects[:limit]
    
    return {"projects": projects}

@app.get("/api/rag-projects/{project_name}")
async def get_rag_project(project_name: str):
    """Get RAG project details."""
    try:
        project_path = get_project_path(project_name)
        if not project_path.exists() or not (project_path / ".rag_project").exists():
            raise HTTPException(status_code=404, detail="RAG project not found")
        
        # Load metadata
        metadata_path = project_path / "metadata.json"
        if metadata_path.exists():
            with open(metadata_path) as f:
                metadata = json.load(f)
        else:
            metadata = {"name": project_name, "type": "rag", "domain": "general"}
        
        # Get data status
        chunks_count = len(list((project_path / "chunks").glob("*.jsonl"))) if (project_path / "chunks").exists() else 0
        
        fact_manager = FactDataManager(str(project_path))
        try:
            generated_facts = fact_manager.load_facts("generated")
            approved_facts = fact_manager.load_facts("approved")
        except:
            generated_facts = []
            approved_facts = []
        
        query_manager = RAGQueryDataManager(str(project_path))
        try:
            generated_queries = query_manager.load_queries("generated")
            approved_queries = query_manager.load_queries("approved")
            multihop_queries = query_manager.load_queries("generated_multihop")
        except:
            generated_queries = []
            approved_queries = []
            multihop_queries = []
        
        return {
            "name": metadata["name"],
            "type": "rag",
            "domain": metadata.get("domain", "general"),
            "chunks_count": chunks_count,
            "data_status": {
                "generated_facts": len(generated_facts),
                "approved_facts": len(approved_facts),
                "generated_queries": len(generated_queries),
                "generated_multihop": len(multihop_queries),
                "approved_queries": len(approved_queries)
            }
        }
        
    except Exception as e:
        raise HTTPException(status_code=500, detail=str(e))

@app.post("/api/rag-projects/{project_name}/chunks/upload")
async def upload_chunks(project_name: str, file: UploadFile = File(...)):
    """Upload chunk files to a RAG project."""
    try:
        project_path = get_project_path(project_name)
        if not project_path.exists() or not (project_path / ".rag_project").exists():
            raise HTTPException(status_code=404, detail="RAG project not found")
        
        # Ensure chunks directory exists
        chunks_dir = project_path / "chunks"
        chunks_dir.mkdir(exist_ok=True)
        
        # Save uploaded file
        file_path = chunks_dir / file.filename
        content = await file.read()
        
        with open(file_path, "wb") as f:
            f.write(content)
        
        # Validate JSONL format by trying to load chunks
        try:
            chunk_processor = ChunkProcessor()
            chunks = chunk_processor.load_chunks_from_file(file_path)
            chunks_count = len(chunks)
        except Exception as e:
            # Remove invalid file
            file_path.unlink()
            raise HTTPException(status_code=400, detail=f"Invalid JSONL format: {str(e)}")
        
        return {
            "message": f"Uploaded {file.filename} with {chunks_count} chunks",
            "filename": file.filename,
            "chunks_count": chunks_count
        }
        
    except Exception as e:
        raise HTTPException(status_code=500, detail=str(e))

@app.get("/api/rag-projects/{project_name}/chunks")
async def get_chunks_info(project_name: str):
    """Get chunks information for a RAG project."""
    try:
        project_path = get_project_path(project_name)
        if not project_path.exists() or not (project_path / ".rag_project").exists():
            raise HTTPException(status_code=404, detail="RAG project not found")
        
        chunks_dir = project_path / "chunks"
        if not chunks_dir.exists():
            return {"chunks_files": [], "total_chunks": 0}
        
        chunk_processor = ChunkProcessor()
        chunks_files = []
        total_chunks = 0
        
        for file_path in chunks_dir.glob("*.jsonl"):
            try:
                chunks = chunk_processor.load_chunks_from_file(file_path)
                chunks_files.append({
                    "filename": file_path.name,
                    "chunks_count": len(chunks),
                    "file_size": file_path.stat().st_size
                })
                total_chunks += len(chunks)
            except:
                chunks_files.append({
                    "filename": file_path.name,
                    "chunks_count": 0,
                    "file_size": file_path.stat().st_size,
                    "error": "Invalid format"
                })
        
        return {
            "chunks_files": chunks_files,
            "total_chunks": total_chunks
        }
        
    except Exception as e:
        raise HTTPException(status_code=500, detail=str(e))

# ========================================
# RAG WORKFLOW ENDPOINTS
# ========================================

@app.post("/api/rag-projects/{project_name}/extract-facts")
async def extract_facts(project_name: str, request: FactExtractionRequest, background_tasks: BackgroundTasks):
    """Extract facts from chunks in a RAG project."""
    try:
        project_path = get_project_path(project_name)
        if not project_path.exists() or not (project_path / ".rag_project").exists():
            raise HTTPException(status_code=404, detail="RAG project not found")
        
        provider = request.provider or auto_detect_provider()
        if not provider:
            raise HTTPException(status_code=400, detail="No LLM provider available")
        
        # Clear any existing status
        clear_generation_status(project_name, "extract_facts")
        
        # Start background task
        background_tasks.add_task(
            background_extract_facts,
            project_name, project_path, provider, request.chunks_dir
        )
        
        return {
            "message": "Fact extraction started",
            "provider": provider,
            "chunks_dir": request.chunks_dir
        }
        
    except Exception as e:
        raise HTTPException(status_code=500, detail=str(e))

@app.post("/api/rag-projects/{project_name}/generate-queries")
async def generate_standard_queries(project_name: str, request: RAGQueryGenerationRequest, background_tasks: BackgroundTasks):
    """Generate standard queries from facts in a RAG project."""
    try:
        project_path = get_project_path(project_name)
        if not project_path.exists() or not (project_path / ".rag_project").exists():
            raise HTTPException(status_code=404, detail="RAG project not found")
        
        provider = request.provider or auto_detect_provider()
        if not provider:
            raise HTTPException(status_code=400, detail="No LLM provider available")
        
        # Clear any existing status
        clear_generation_status(project_name, "generate_queries")
        
        # Start background task
        background_tasks.add_task(
            background_generate_rag_queries,
            project_name, project_path, provider, request.count
        )
        
        return {
            "message": "Query generation started",
            "provider": provider,
            "count": request.count
        }
        
    except Exception as e:
        raise HTTPException(status_code=500, detail=str(e))

@app.post("/api/rag-projects/{project_name}/generate-multihop")
async def generate_multihop_queries(project_name: str, request: MultihopGenerationRequest, background_tasks: BackgroundTasks):
    """Generate multi-hop queries from facts in a RAG project."""
    try:
        project_path = get_project_path(project_name)
        if not project_path.exists() or not (project_path / ".rag_project").exists():
            raise HTTPException(status_code=404, detail="RAG project not found")
        
        provider = request.provider or auto_detect_provider()
        if not provider:
            raise HTTPException(status_code=400, detail="No LLM provider available")
        
        # Clear any existing status
        clear_generation_status(project_name, "generate_multihop")
        
        # Start background task
        background_tasks.add_task(
            background_generate_multihop_queries,
            project_name, project_path, provider, request.count, request.queries_per_combo
        )
        
        return {
            "message": "Multi-hop query generation started",
            "provider": provider,
            "count": request.count
        }
        
    except Exception as e:
        raise HTTPException(status_code=500, detail=str(e))

@app.post("/api/rag-projects/{project_name}/filter-queries")
async def filter_queries(project_name: str, request: FilterRequest, background_tasks: BackgroundTasks):
    """Filter queries by quality score in a RAG project."""
    try:
        project_path = get_project_path(project_name)
        if not project_path.exists() or not (project_path / ".rag_project").exists():
            raise HTTPException(status_code=404, detail="RAG project not found")
        
        provider = request.provider or auto_detect_provider()
        if not provider:
            raise HTTPException(status_code=400, detail="No LLM provider available")
        
        # Clear any existing status
        clear_generation_status(project_name, "filter_queries")
        
        # Start background task
        background_tasks.add_task(
            background_filter_queries,
            project_name, project_path, provider, request.min_score
        )
        
        return {
            "message": "Query filtering started",
            "provider": provider,
            "min_score": request.min_score
        }
        
    except Exception as e:
        raise HTTPException(status_code=500, detail=str(e))

# ========================================
# RAG DATA MANAGEMENT ENDPOINTS
# ========================================

@app.get("/api/rag-projects/{project_name}/facts/{stage}")
async def get_facts(project_name: str, stage: str):
    """Get facts from specific stage with source text for highlighting."""
    try:
        project_path = get_project_path(project_name)
        if not project_path.exists() or not (project_path / ".rag_project").exists():
            raise HTTPException(status_code=404, detail="RAG project not found")
        
        fact_manager = FactDataManager(str(project_path))
        facts = fact_manager.load_facts(stage)
        
        # Load chunks to get source text
        chunks_directory = project_path / "chunks"
        chunk_processor = ChunkProcessor()
        all_chunks = chunk_processor.load_chunks_from_directory(chunks_directory)
        
        # Create chunk lookup by ID
        chunk_lookup = {chunk.chunk_id: chunk.text for chunk in all_chunks}
        
        facts_with_highlighting = []
        for fact in facts:
            source_text = chunk_lookup.get(fact.chunk_id, "Source chunk not found")
            
            # Get highlighted chunk using Model2Vec similarity with fallback
            try:
                print(f"🔍 Attempting highlighting for fact {fact.fact_id[:8]}...")
                print(f"    Fact: '{fact.fact_text}'")
                print(f"    Source: '{source_text}'")
                
                # Use the configured highlight similarity threshold instead of hardcoded value
                from qgen.core.rag_models import RAGConfig
                config = RAGConfig()
                print(f"    Using highlight_similarity_threshold: {config.highlight_similarity_threshold}")
                highlighted_html = fact.get_chunk_with_highlight(source_text, similarity_threshold=config.highlight_similarity_threshold)
                
                print(f"    Raw result: '{highlighted_html}'")
                print(f"    Has rich markup: {'[bold yellow on blue]' in highlighted_html}")
                
                # Convert rich markup to HTML for web display
                highlighted_html = highlighted_html.replace("[bold yellow on blue]", '<mark class="bg-yellow-200 text-yellow-900 font-medium px-1 rounded">')
                highlighted_html = highlighted_html.replace("[/bold yellow on blue]", "</mark>")
                
                print(f"    Final HTML: '{highlighted_html}'")
                print(f"    Has mark tags: {'<mark>' in highlighted_html}")
                print(f"✅ Highlighting completed for fact {fact.fact_id[:8]}")
            except Exception as e:
                print(f"⚠️ Highlighting failed for fact {fact.fact_id}: {e}")
                print(f"🔄 Using fallback: sentence-based word highlighting")
                # Simple fallback highlighting using word matching
                import re
                fact_words = [word for word in re.findall(r'\b\w{3,}\b', fact.fact_text)]
                highlighted_html = source_text
                print(f"📝 Fact words to highlight: {fact_words}")
                
                for word in fact_words:
                    # Create pattern that matches the word case-insensitively but preserves original case
                    pattern = r'\b(' + re.escape(word) + r')\b'
                    def replacement_func(match):
                        original_word = match.group(1)
                        return f'<mark class="bg-yellow-200 text-yellow-900 font-medium px-1 rounded">{original_word}</mark>'
                    
                    highlighted_html = re.sub(pattern, replacement_func, highlighted_html, flags=re.IGNORECASE)
                
                print(f"✅ Fallback highlighting complete, found {highlighted_html.count('<mark>')} highlights")
            
            facts_with_highlighting.append({
                "fact_id": fact.fact_id,
                "chunk_id": fact.chunk_id,
                "fact_text": fact.fact_text,
                "extraction_confidence": fact.extraction_confidence,
                "source_text": source_text,
                "highlighted_source": highlighted_html
            })

        return {
            "facts": facts_with_highlighting,
            "count": len(facts)
        }
        
    except Exception as e:
        raise HTTPException(status_code=500, detail=str(e))

@app.post("/api/rag-projects/{project_name}/facts/approve")
async def approve_facts(project_name: str, request: ApproveItemsRequest):
    """Approve selected facts."""
    try:
        project_path = get_project_path(project_name)
        if not project_path.exists() or not (project_path / ".rag_project").exists():
            raise HTTPException(status_code=404, detail="RAG project not found")
        
        fact_manager = FactDataManager(str(project_path))
        generated_facts = fact_manager.load_facts("generated")
        
        # Filter approved facts
        approved_facts = [fact for fact in generated_facts if fact.fact_id in request.item_ids]
        
        if approved_facts:
            fact_manager.save_facts(approved_facts, "approved", custom_metadata={"approved_count": len(approved_facts)})
        
        return {
            "message": f"Approved {len(approved_facts)} facts",
            "approved_count": len(approved_facts)
        }
        
    except Exception as e:
        raise HTTPException(status_code=500, detail=str(e))

@app.get("/api/rag-projects/{project_name}/queries/{stage}")
async def get_rag_queries(project_name: str, stage: str):
    """Get RAG queries from specific stage with chunk highlighting."""
    try:
        project_path = get_project_path(project_name)
        if not project_path.exists() or not (project_path / ".rag_project").exists():
            raise HTTPException(status_code=404, detail="RAG project not found")
        
        query_manager = RAGQueryDataManager(str(project_path))
        queries = query_manager.load_queries(stage)
        
        # Load chunks and facts for highlighting (same logic as CLI)
        chunks_map = {}
        facts_map = {}
        
        try:
            # Load chunks
            chunks_directory = project_path / "chunks"
            chunk_processor = ChunkProcessor()
            all_chunks = chunk_processor.load_chunks_from_directory(chunks_directory)
            chunks_map = {chunk.chunk_id: chunk for chunk in all_chunks}
            
            # Load facts for better highlighting
            fact_manager = FactDataManager(str(project_path))
            approved_facts = fact_manager.load_facts("approved")
            facts_map = {fact.chunk_id: fact for fact in approved_facts}
        except Exception as e:
            print(f"Warning: Could not load chunks/facts for highlighting: {e}")
        
        enhanced_queries = []
        for query in queries:
            highlighted_chunks = []
            
            # Process each source chunk for highlighting
            for chunk_id in query.source_chunk_ids:
                chunk = chunks_map.get(chunk_id)
                if chunk:
                    try:
                        # Use same highlighting logic as CLI
                        original_fact = facts_map.get(chunk_id)
                        if original_fact:
                            highlighted_text = original_fact.get_chunk_with_highlight(chunk.text)
                            highlight_source = "original_fact"
                        else:
                            # Fallback to answer fact (same as CLI)
                            from qgen.core.rag_models import ExtractedFact
                            temp_fact = ExtractedFact(
                                fact_text=query.answer_fact,
                                chunk_id=chunk_id,
                                extraction_confidence=1.0
                            )
                            highlighted_text = temp_fact.get_chunk_with_highlight(chunk.text)
                            highlight_source = "answer_fact"
                        
                        # Convert rich markup to HTML
                        highlighted_html = highlighted_text.replace("[bold yellow on blue]", '<mark class="bg-yellow-200 text-yellow-900 font-medium px-1 rounded">')
                        highlighted_html = highlighted_html.replace("[/bold yellow on blue]", "</mark>")
                        
                        highlighted_chunks.append({
                            "chunk_id": chunk_id,
                            "chunk_text": chunk.text,
                            "highlighted_html": highlighted_html,
                            "source_document": chunk.source_document or "Unknown",
                            "highlight_source": highlight_source,
                            "chunk_index": len(highlighted_chunks) + 1
                        })
                        
                    except Exception as e:
                        # Fallback to plain text
                        highlighted_chunks.append({
                            "chunk_id": chunk_id,
                            "chunk_text": chunk.text,
                            "highlighted_html": chunk.text,  # No highlighting
                            "source_document": chunk.source_document or "Unknown",
                            "highlight_source": "none",
                            "chunk_index": len(highlighted_chunks) + 1
                        })
            
            enhanced_queries.append({
                "query_id": query.query_id,
                "query_text": query.query_text,
                "answer_fact": query.answer_fact,
                "source_chunk_ids": query.source_chunk_ids,
                "difficulty": query.difficulty,
                "realism_rating": getattr(query, 'realism_rating', None),
                "highlighted_chunks": highlighted_chunks
            })
        
        return {
            "queries": enhanced_queries,
            "count": len(queries)
        }
        
    except Exception as e:
        raise HTTPException(status_code=500, detail=str(e))

@app.post("/api/rag-projects/{project_name}/queries/approve")
async def approve_rag_queries(project_name: str, request: ApproveItemsRequest):
    """Approve selected RAG queries."""
    try:
        project_path = get_project_path(project_name)
        if not project_path.exists() or not (project_path / ".rag_project").exists():
            raise HTTPException(status_code=404, detail="RAG project not found")
        
        query_manager = RAGQueryDataManager(str(project_path))
        
        # Load both standard and multihop queries
        standard_queries = query_manager.load_queries("generated")
        multihop_queries = query_manager.load_queries("generated_multihop")
        all_queries = standard_queries + multihop_queries
        
        # Filter approved queries
        approved_queries = [query for query in all_queries if query.query_id in request.item_ids]
        
        if approved_queries:
            query_manager.save_queries(approved_queries, "approved", metadata={"approved_count": len(approved_queries)})
        
        return {
            "message": f"Approved {len(approved_queries)} queries",
            "approved_count": len(approved_queries)
        }
        
    except Exception as e:
        raise HTTPException(status_code=500, detail=str(e))

@app.get("/api/rag-projects/{project_name}/export/{format}")
async def export_rag_queries(project_name: str, format: str, stage: str = "approved"):
    """Export RAG queries to specified format."""
    try:
        project_path = get_project_path(project_name)
        if not project_path.exists() or not (project_path / ".rag_project").exists():
            raise HTTPException(status_code=404, detail="RAG project not found")
        
        if format not in ["csv", "json"]:
            raise HTTPException(status_code=400, detail="Format must be 'csv' or 'json'")
        
        query_manager = RAGQueryDataManager(str(project_path))
        queries = query_manager.load_queries(stage)
        
        if not queries:
            raise HTTPException(status_code=404, detail=f"No {stage} queries found")
        
        # Export using CLI functionality
        from qgen.core.rag_export import RAGExporter
        exporter = RAGExporter(str(project_path))
        exported_path = exporter.export_queries(queries, format, stage)
        
        return {
            "message": f"Exported to {exported_path}",
            "path": exported_path,
            "format": format,
            "queries_count": len(queries)
        }
        
    except Exception as e:
        raise HTTPException(status_code=500, detail=str(e))

@app.get("/api/rag-projects/{project_name}/status/{operation}")
async def get_rag_operation_status(project_name: str, operation: str):
    """Get RAG operation status for a project."""
    status = get_generation_status(project_name, operation)
    if not status:
        raise HTTPException(status_code=404, detail="No active operation found")
    return status

# Serve static files (React build) in production
frontend_dist = Path(__file__).parent / "frontend" / "dist"
frontend_legacy_dist = Path(__file__).parent / "frontend-legacy" / "dist"

# Serve default (shadcn) version at root
if frontend_dist.exists():
    app.mount("/", StaticFiles(directory=str(frontend_dist), html=True), name="static")

# Serve legacy version at /legacy route for reference
if frontend_legacy_dist.exists():
    app.mount("/legacy", StaticFiles(directory=str(frontend_legacy_dist), html=True), name="legacy")

if __name__ == "__main__":
    import uvicorn
    uvicorn.run(app, host="0.0.0.0", port=8888)