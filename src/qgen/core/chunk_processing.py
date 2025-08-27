import json
from pathlib import Path
from typing import List, Dict, Set
from rich.console import Console
from rich.progress import Progress, SpinnerColumn, TextColumn

from .rag_models import ChunkData

console = Console()


class ChunkProcessor:
    """Processor for loading and validating chunk data from JSONL files."""
    
    def __init__(self):
        self.processed_chunks: List[ChunkData] = []
        self.chunk_ids: Set[str] = set()
    
    def load_chunks_from_file(self, file_path: Path) -> List[ChunkData]:
        """Load and validate a single JSONL file."""
        chunks = self._load_jsonl_file(file_path)
        # For single file, we can't validate cross-references to other files
        # But we can validate internal references within the same file
        chunk_ids_in_file = {chunk.chunk_id for chunk in chunks}
        for chunk in chunks:
            if chunk.related_chunks:
                for related_id in chunk.related_chunks:
                    if related_id not in chunk_ids_in_file:
                        # Just warn, don't fail - the reference might be in another file
                        console.print(f"[yellow]⚠️ Chunk {chunk.chunk_id} references chunk {related_id} not in this file[/yellow]")
        return chunks
    
    def load_chunks_from_directory(self, chunks_dir: Path) -> List[ChunkData]:
        """Load and validate all JSONL files in chunks directory."""
        chunks = []
        jsonl_files = list(chunks_dir.glob("*.jsonl"))
        
        if not jsonl_files:
            raise FileNotFoundError(f"No JSONL files found in {chunks_dir}")
        
        console.print(f"[blue]📁 Found {len(jsonl_files)} JSONL files to process[/blue]")
        
        for file_path in jsonl_files:
            console.print(f"[dim]Processing: {file_path.name}[/dim]")
            file_chunks = self._load_jsonl_file(file_path)
            chunks.extend(file_chunks)
        
        # Validate cross-references
        self._validate_chunk_references(chunks)
        
        console.print(f"[green]✅ Loaded {len(chunks)} valid chunks[/green]")
        return chunks
    
    def _load_jsonl_file(self, file_path: Path) -> List[ChunkData]:
        """Load and validate a single JSONL file."""
        chunks = []
        
        try:
            with open(file_path, 'r', encoding='utf-8') as f:
                for line_num, line in enumerate(f, 1):
                    line = line.strip()
                    if not line:
                        continue
                    
                    try:
                        data = json.loads(line)
                        chunk = ChunkData.model_validate(data)
                        
                        # Check for duplicate chunk_ids
                        if chunk.chunk_id in self.chunk_ids:
                            raise ValueError(f"Duplicate chunk_id: {chunk.chunk_id}")
                        
                        self.chunk_ids.add(chunk.chunk_id)
                        chunks.append(chunk)
                        
                    except json.JSONDecodeError as e:
                        raise ValueError(f"Invalid JSON at line {line_num} in {file_path}: {e}")
                    except Exception as e:
                        raise ValueError(f"Invalid chunk data at line {line_num} in {file_path}: {e}")
        
        except FileNotFoundError:
            raise FileNotFoundError(f"File not found: {file_path}")
        except PermissionError:
            raise PermissionError(f"Permission denied reading file: {file_path}")
        
        return chunks
    
    def _validate_chunk_references(self, chunks: List[ChunkData]):
        """Validate that related_chunks references point to existing chunks."""
        chunk_id_set = {chunk.chunk_id for chunk in chunks}
        
        for chunk in chunks:
            if chunk.related_chunks:
                for related_id in chunk.related_chunks:
                    if related_id not in chunk_id_set:
                        raise ValueError(
                            f"Chunk {chunk.chunk_id} references non-existent chunk: {related_id}"
                        )
    
    def validate_chunk_schema(self, chunk_data: dict) -> bool:
        """Validate that chunk data conforms to expected schema."""
        try:
            ChunkData(**chunk_data)
            return True
        except Exception:
            return False
    
    def get_chunks_summary(self, chunks: List[ChunkData]) -> Dict[str, any]:
        """Generate summary statistics for loaded chunks."""
        total_chunks = len(chunks)
        chunks_with_relations = sum(1 for chunk in chunks if chunk.related_chunks)
        chunks_with_metadata = sum(1 for chunk in chunks if chunk.custom_metadata)
        
        # Calculate text length statistics
        text_lengths = [len(chunk.text) for chunk in chunks]
        avg_text_length = sum(text_lengths) / len(text_lengths) if text_lengths else 0
        
        return {
            "total_chunks": total_chunks,
            "chunks_with_relations": chunks_with_relations,
            "chunks_with_metadata": chunks_with_metadata,
            "avg_text_length": round(avg_text_length, 2),
            "min_text_length": min(text_lengths) if text_lengths else 0,
            "max_text_length": max(text_lengths) if text_lengths else 0
        }