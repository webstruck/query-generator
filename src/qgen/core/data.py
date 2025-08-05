"""Data directory management utilities."""

import json
from datetime import datetime
from pathlib import Path
from typing import List, Dict, Any, Optional
from rich.console import Console

from .models import Tuple, Query

console = Console()


class DataManager:
    """Manages the organized data directory structure."""
    
    def __init__(self, project_dir: str = "."):
        """Initialize data manager for a project directory."""
        self.project_dir = Path(project_dir)
        self.data_dir = self.project_dir / "data"
        
    def ensure_directories(self) -> None:
        """Ensure all data directories exist."""
        directories = [
            self.data_dir / "tuples",
            self.data_dir / "queries",
            self.data_dir / "exports"
        ]
        
        for directory in directories:
            directory.mkdir(parents=True, exist_ok=True)
    
    def save_tuples(self, tuples: List[Tuple], stage: str, metadata: Optional[Dict[str, Any]] = None) -> Path:
        """Save tuples to the appropriate file based on stage.
        
        Args:
            tuples: List of tuples to save
            stage: Stage of tuples ('generated', 'approved', 'rejected')
            metadata: Optional metadata to include
            
        Returns:
            Path where tuples were saved
        """
        self.ensure_directories()
        
        # Prepare data structure
        data = {
            "metadata": {
                "count": len(tuples),
                "stage": stage,
                "timestamp": datetime.now().isoformat(),
                **(metadata or {})
            },
            "tuples": [{"values": t.values} for t in tuples]
        }
        
        # Determine file path
        file_path = self.data_dir / "tuples" / f"{stage}.json"
        
        # Save to file
        with open(file_path, 'w', encoding='utf-8') as f:
            json.dump(data, f, indent=2, ensure_ascii=False)
        
        return file_path
    
    def load_tuples(self, stage: str = "approved") -> List[Tuple]:
        """Load tuples from a specific stage.
        
        Args:
            stage: Stage to load ('generated', 'approved', 'rejected')
            
        Returns:
            List of loaded tuples
        """
        file_path = self.data_dir / "tuples" / f"{stage}.json"
        
        if not file_path.exists():
            console.print(f"[yellow]⚠️  No {stage} tuples found at {file_path}[/yellow]")
            return []
        
        try:
            with open(file_path, 'r', encoding='utf-8') as f:
                data = json.load(f)
            
            tuples = []
            for tuple_data in data.get("tuples", []):
                tuples.append(Tuple(values=tuple_data["values"]))
            
            return tuples
            
        except Exception as e:
            console.print(f"[red]❌ Error loading tuples from {file_path}: {str(e)}[/red]")
            return []
    
    def save_queries(self, queries: List[Query], stage: str, metadata: Optional[Dict[str, Any]] = None) -> Path:
        """Save queries to the appropriate file based on stage.
        
        Args:
            queries: List of queries to save
            stage: Stage of queries ('generated', 'approved')
            metadata: Optional metadata to include
            
        Returns:
            Path where queries were saved
        """
        self.ensure_directories()
        
        # Prepare data structure
        data = {
            "metadata": {
                "count": len(queries),
                "stage": stage,
                "timestamp": datetime.now().isoformat(),
                **(metadata or {})
            },
            "queries": [
                {
                    "text": q.generated_text,
                    "status": q.status,
                    "tuple_data": q.tuple_data.values
                } 
                for q in queries
            ]
        }
        
        # Determine file path
        file_path = self.data_dir / "queries" / f"{stage}.json"
        
        # Save to file
        with open(file_path, 'w', encoding='utf-8') as f:
            json.dump(data, f, indent=2, ensure_ascii=False)
        
        return file_path
    
    def load_queries(self, stage: str = "approved") -> List[Query]:
        """Load queries from a specific stage.
        
        Args:
            stage: Stage to load ('generated', 'approved')
            
        Returns:
            List of loaded queries
        """
        file_path = self.data_dir / "queries" / f"{stage}.json"
        
        if not file_path.exists():
            console.print(f"[yellow]⚠️  No {stage} queries found at {file_path}[/yellow]")
            return []
        
        try:
            with open(file_path, 'r', encoding='utf-8') as f:
                data = json.load(f)
            
            queries = []
            for query_data in data.get("queries", []):
                # Reconstruct Tuple and Query objects
                tuple_obj = Tuple(values=query_data["tuple_data"])
                query = Query(
                    tuple_data=tuple_obj,
                    generated_text=query_data["text"],
                    status=query_data.get("status", "pending")
                )
                queries.append(query)
            
            return queries
            
        except Exception as e:
            console.print(f"[red]❌ Error loading queries from {file_path}: {str(e)}[/red]")
            return []
    
    def get_project_status(self) -> Dict[str, Any]:
        """Get overview of project data status."""
        status = {
            "tuples": {},
            "queries": {},
            "exports": {}
        }
        
        # Check tuple files
        for stage in ["generated", "approved", "rejected"]:
            file_path = self.data_dir / "tuples" / f"{stage}.json"
            if file_path.exists():
                try:
                    with open(file_path, 'r') as f:
                        data = json.load(f)
                    status["tuples"][stage] = {
                        "count": data.get("metadata", {}).get("count", 0),
                        "timestamp": data.get("metadata", {}).get("timestamp", "unknown")
                    }
                except:
                    status["tuples"][stage] = {"count": 0, "error": "invalid file"}
        
        # Check query files
        for stage in ["generated", "approved"]:
            file_path = self.data_dir / "queries" / f"{stage}.json"
            if file_path.exists():
                try:
                    with open(file_path, 'r') as f:
                        data = json.load(f)
                    status["queries"][stage] = {
                        "count": data.get("metadata", {}).get("count", 0),
                        "timestamp": data.get("metadata", {}).get("timestamp", "unknown")
                    }
                except:
                    status["queries"][stage] = {"count": 0, "error": "invalid file"}
        
        # Check exports
        exports_dir = self.data_dir / "exports"
        if exports_dir.exists():
            export_files = list(exports_dir.glob("*"))
            status["exports"] = {
                "files": len(export_files),
                "formats": list(set(f.suffix for f in export_files))
            }
        
        return status
    
    def cleanup_old_files(self, days: int = 30) -> None:
        """Clean up old files older than specified days."""
        # Implementation for cleaning up old files
        # This would be useful for long-running projects
        pass


def get_data_manager(project_dir: str = ".") -> DataManager:
    """Get a DataManager instance for the specified project directory."""
    return DataManager(project_dir)