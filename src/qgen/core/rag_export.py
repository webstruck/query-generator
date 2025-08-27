"""RAG query export system with multiple formats and comprehensive statistics."""

import json
import csv
from pathlib import Path
from typing import List, Dict, Any, Optional
from datetime import datetime
from collections import Counter

from .rag_models import RAGQuery


class RAGExporter:
    """Export system designed for both CLI and web interface compatibility."""
    
    def __init__(self):
        pass
    
    def export_queries(self, 
                      queries: List[RAGQuery], 
                      format: str, 
                      output_path: str) -> Dict[str, Any]:
        """Export RAG queries with comprehensive statistics.
        
        Args:
            queries: List of RAG queries to export
            format: Export format ('jsonl', 'json', 'csv')
            output_path: Path where to save the exported file
            
        Returns:
            Dictionary with export statistics and metadata
        """
        if not queries:
            raise ValueError("No queries to export")
        
        # Create output directory if it doesn't exist
        Path(output_path).parent.mkdir(parents=True, exist_ok=True)
        
        # Export based on format
        if format.lower() == "jsonl":
            stats = self._export_jsonl(queries, output_path)
        elif format.lower() == "json":
            stats = self._export_json(queries, output_path)
        elif format.lower() == "csv":
            stats = self._export_csv(queries, output_path)
        else:
            raise ValueError(f"Unsupported export format: {format}. Supported: jsonl, json, csv")
        
        # Add file metadata
        file_path = Path(output_path)
        stats.update({
            "export_path": output_path,
            "file_size": file_path.stat().st_size if file_path.exists() else 0,
            "file_size_mb": round(file_path.stat().st_size / (1024 * 1024), 2) if file_path.exists() else 0,
            "format": format.lower(),
            "exported_at": datetime.now().isoformat(),
            "download_ready": True
        })
        
        return stats
    
    def _export_jsonl(self, queries: List[RAGQuery], output_path: str) -> Dict[str, Any]:
        """Export queries as JSONL (one JSON object per line)."""
        with open(output_path, 'w', encoding='utf-8') as f:
            for query in queries:
                record = self._prepare_query_record(query)
                f.write(json.dumps(record, ensure_ascii=False) + '\\n')
        
        return self._generate_export_stats(queries, "jsonl")
    
    def _export_json(self, queries: List[RAGQuery], output_path: str) -> Dict[str, Any]:
        """Export queries as structured JSON."""
        export_data = {
            "metadata": {
                "total_queries": len(queries),
                "export_format": "json",
                "exported_at": datetime.now().isoformat(),
                "generator": "qgen-rag"
            },
            "queries": [self._prepare_query_record(query) for query in queries],
            "statistics": self._generate_detailed_statistics(queries)
        }
        
        with open(output_path, 'w', encoding='utf-8') as f:
            json.dump(export_data, f, indent=2, ensure_ascii=False)
        
        return self._generate_export_stats(queries, "json")
    
    def _export_csv(self, queries: List[RAGQuery], output_path: str) -> Dict[str, Any]:
        """Export queries as CSV format."""
        if not queries:
            raise ValueError("No queries to export to CSV")
        
        # Prepare data
        records = [self._prepare_query_record(query) for query in queries]
        
        # Get all unique fieldnames
        fieldnames = set()
        for record in records:
            fieldnames.update(record.keys())
        
        # Order fieldnames logically
        priority_fields = [
            "query", "answer", "difficulty", "realism_score", 
            "source_chunk_ids", "generation_type", "timestamp"
        ]
        
        ordered_fieldnames = []
        for field in priority_fields:
            if field in fieldnames:
                ordered_fieldnames.append(field)
                fieldnames.remove(field)
        
        # Add remaining fields
        ordered_fieldnames.extend(sorted(fieldnames))
        
        # Write CSV
        with open(output_path, 'w', newline='', encoding='utf-8') as f:
            writer = csv.DictWriter(f, fieldnames=ordered_fieldnames, extrasaction='ignore')
            writer.writeheader()
            
            for record in records:
                # Handle list fields for CSV
                csv_record = record.copy()
                if 'source_chunk_ids' in csv_record and isinstance(csv_record['source_chunk_ids'], list):
                    csv_record['source_chunk_ids'] = ';'.join(csv_record['source_chunk_ids'])
                if 'improvements' in csv_record and isinstance(csv_record['improvements'], list):
                    csv_record['improvements'] = '; '.join(csv_record['improvements'])
                
                writer.writerow(csv_record)
        
        return self._generate_export_stats(queries, "csv")
    
    def _prepare_query_record(self, query: RAGQuery) -> Dict[str, Any]:
        """Prepare a single query for export (format-agnostic)."""
        record = {
            "query": query.query_text,
            "answer": query.answer_fact,
            "source_chunk_ids": query.source_chunk_ids,
            "difficulty": query.difficulty,
            "realism_score": query.realism_rating,
            "generation_type": query.generation_metadata.get("generation_type", "unknown") if query.generation_metadata else "unknown",
            "timestamp": query.generation_metadata.get("timestamp", "") if query.generation_metadata else "",
            "query_id": query.query_id
        }
        
        # Add quality metadata if available
        if hasattr(query, 'quality_metadata') and query.quality_metadata:
            record["quality_reasoning"] = query.quality_metadata.get("reasoning", "")
            record["improvements"] = query.quality_metadata.get("improvements", [])
            record["scored_at"] = query.quality_metadata.get("scored_at", "")
        
        # Add generation metadata
        if query.generation_metadata:
            record["model_used"] = query.generation_metadata.get("model_used", "")
            record["generation_params"] = query.generation_metadata.get("generation_params", {})
        
        return record
    
    def prepare_export_data(self, queries: List[RAGQuery]) -> List[Dict[str, Any]]:
        """Prepare data for export (useful for web preview)."""
        return [self._prepare_query_record(query) for query in queries]
    
    def _generate_export_stats(self, queries: List[RAGQuery], format: str) -> Dict[str, Any]:
        """Generate basic export statistics."""
        stats = {
            "total_queries": len(queries),
            "format": format,
            **self._generate_detailed_statistics(queries)
        }
        return stats
    
    def _generate_detailed_statistics(self, queries: List[RAGQuery]) -> Dict[str, Any]:
        """Generate comprehensive statistics about the exported queries."""
        if not queries:
            return {}
        
        # Difficulty distribution
        difficulty_counts = Counter(query.difficulty for query in queries)
        
        # Realism score statistics
        realism_scores = [q.realism_rating for q in queries if q.realism_rating is not None]
        realism_stats = {}
        if realism_scores:
            realism_stats = {
                "avg_realism_score": round(sum(realism_scores) / len(realism_scores), 2),
                "min_realism_score": min(realism_scores),
                "max_realism_score": max(realism_scores),
                "scored_queries": len(realism_scores),
                "score_distribution": dict(Counter(realism_scores))
            }
        
        # Source chunk statistics
        chunk_counts = [len(q.source_chunk_ids) for q in queries]
        chunk_stats = {
            "avg_chunks_per_query": round(sum(chunk_counts) / len(chunk_counts), 2),
            "min_chunks": min(chunk_counts),
            "max_chunks": max(chunk_counts),
            "single_chunk_queries": sum(1 for c in chunk_counts if c == 1),
            "multi_chunk_queries": sum(1 for c in chunk_counts if c > 1)
        }
        
        # Generation type distribution
        generation_types = [
            q.generation_metadata.get("generation_type", "unknown") 
            for q in queries if q.generation_metadata
        ]
        generation_type_counts = dict(Counter(generation_types)) if generation_types else {}
        
        # Quality metadata statistics
        quality_stats = {}
        queries_with_quality = [q for q in queries if hasattr(q, 'quality_metadata') and q.quality_metadata]
        if queries_with_quality:
            quality_stats = {
                "queries_with_quality_data": len(queries_with_quality),
                "quality_coverage": round(len(queries_with_quality) / len(queries), 2)
            }
        
        return {
            "difficulty_distribution": dict(difficulty_counts),
            "realism_statistics": realism_stats,
            "chunk_statistics": chunk_stats,
            "generation_type_distribution": generation_type_counts,
            "quality_statistics": quality_stats,
            "export_summary": {
                "most_common_difficulty": difficulty_counts.most_common(1)[0][0] if difficulty_counts else "unknown",
                "avg_quality_score": realism_stats.get("avg_realism_score", "N/A"),
                "multi_chunk_percentage": round(chunk_stats["multi_chunk_queries"] / len(queries) * 100, 1) if queries else 0
            }
        }
    
    def generate_export_summary_text(self, stats: Dict[str, Any]) -> str:
        """Generate human-readable export summary."""
        lines = [
            f"📊 Export Summary:",
            f"  • Total queries: {stats['total_queries']}",
            f"  • Format: {stats['format'].upper()}",
            f"  • File size: {stats.get('file_size_mb', 0)} MB",
            ""
        ]
        
        # Difficulty breakdown
        if 'difficulty_distribution' in stats:
            lines.append("🎯 Difficulty Distribution:")
            for difficulty, count in stats['difficulty_distribution'].items():
                percentage = round(count / stats['total_queries'] * 100, 1)
                lines.append(f"  • {difficulty.title()}: {count} ({percentage}%)")
            lines.append("")
        
        # Quality stats
        if 'realism_statistics' in stats and stats['realism_statistics']:
            realism = stats['realism_statistics']
            lines.extend([
                "⭐ Quality Statistics:",
                f"  • Average realism: {realism.get('avg_realism_score', 'N/A')}/5.0",
                f"  • Score range: {realism.get('min_realism_score', 'N/A')}-{realism.get('max_realism_score', 'N/A')}",
                f"  • Scored queries: {realism.get('scored_queries', 0)}",
                ""
            ])
        
        # Chunk stats
        if 'chunk_statistics' in stats:
            chunk = stats['chunk_statistics']
            lines.extend([
                "🔗 Source Chunks:",
                f"  • Average per query: {chunk.get('avg_chunks_per_query', 'N/A')}",
                f"  • Single-chunk queries: {chunk.get('single_chunk_queries', 0)}",
                f"  • Multi-chunk queries: {chunk.get('multi_chunk_queries', 0)}",
                ""
            ])
        
        return "\\n".join(lines)


class RAGQueryDataManagerExtended:
    """Extended data manager with export capabilities."""
    
    def __init__(self, project_path: str = "."):
        self.project_path = Path(project_path)
        self.exports_dir = self.project_path / "data" / "exports"
        self.exports_dir.mkdir(parents=True, exist_ok=True)
    
    def get_available_stages(self) -> List[str]:
        """Get list of available query stages for export."""
        queries_dir = self.project_path / "data" / "queries"
        if not queries_dir.exists():
            return []
        
        stages = []
        for file_path in queries_dir.glob("*.json"):
            stage_name = file_path.stem
            stages.append(stage_name)
        
        return sorted(stages)
    
    def load_queries_for_export(self, stage: str) -> List[RAGQuery]:
        """Load queries from a specific stage for export."""
        from .rag_quality import RAGQueryDataManager
        data_manager = RAGQueryDataManager(str(self.project_path))
        return data_manager.load_queries(stage)
    
    def get_export_filename(self, stage: str, format: str, custom_name: Optional[str] = None) -> str:
        """Generate a standardized export filename."""
        if custom_name:
            return custom_name
        
        timestamp = datetime.now().strftime("%Y%m%d_%H%M%S")
        return f"rag_queries_{stage}_{timestamp}.{format}"
    
    def get_export_path(self, filename: str) -> str:
        """Get full path for export file."""
        return str(self.exports_dir / filename)