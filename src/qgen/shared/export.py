"""Unified export system for both dimension and RAG projects."""

import csv
import json
from abc import ABC, abstractmethod
from pathlib import Path
from typing import List, Dict, Any, Optional, Union
from datetime import datetime
from enum import Enum

# Import models from both systems
from ..core.models import Query as DimensionQuery
from ..core.rag_models import RAGQuery


class ExportFormat(Enum):
    """Supported export formats."""
    CSV = "csv"
    JSON = "json"
    JSONL = "jsonl"


class ProjectType(Enum):
    """Supported project types."""
    DIMENSION = "dimension"
    RAG = "rag"


class ExportResult:
    """Result of an export operation with metadata."""

    def __init__(self,
                 output_path: str,
                 stats: Dict[str, Any],
                 format: ExportFormat,
                 project_type: ProjectType):
        self.output_path = output_path
        self.stats = stats
        self.format = format
        self.project_type = project_type
        self.exported_at = datetime.now().isoformat()

        # Add file metadata
        file_path = Path(output_path)
        if file_path.exists():
            self.file_size = file_path.stat().st_size
            self.file_size_mb = round(self.file_size / (1024 * 1024), 2)
        else:
            self.file_size = 0
            self.file_size_mb = 0

    def to_dict(self) -> Dict[str, Any]:
        """Convert to dictionary for JSON serialization."""
        return {
            "output_path": self.output_path,
            "stats": self.stats,
            "format": self.format.value,
            "project_type": self.project_type.value,
            "exported_at": self.exported_at,
            "file_size": self.file_size,
            "file_size_mb": self.file_size_mb,
            "download_ready": True
        }


class BaseFormatter(ABC):
    """Base class for all export formatters."""

    @abstractmethod
    def format(self, data: List[Union[DimensionQuery, RAGQuery]], output_path: str) -> Dict[str, Any]:
        """Format and save data to the specified path."""
        pass

    @abstractmethod
    def prepare_record(self, query: Union[DimensionQuery, RAGQuery]) -> Dict[str, Any]:
        """Prepare a single query record for export."""
        pass

    def generate_stats(self, data: List[Union[DimensionQuery, RAGQuery]]) -> Dict[str, Any]:
        """Generate basic statistics for the export."""
        return {
            "total_queries": len(data),
            "exported_at": datetime.now().isoformat()
        }


class DimensionCSVFormatter(BaseFormatter):
    """CSV formatter for dimension-based queries."""

    def format(self, data: List[DimensionQuery], output_path: str) -> Dict[str, Any]:
        if not data:
            raise ValueError("No queries to export")

        # Prepare records
        records = [self.prepare_record(query) for query in data]

        # Get all unique column names
        all_columns = set()
        for record in records:
            all_columns.update(record.keys())

        # Sort columns for consistent output with priority ordering
        priority_columns = ["query", "status"]
        columns = []

        for col in priority_columns:
            if col in all_columns:
                columns.append(col)
                all_columns.remove(col)

        # Add dimension columns next
        dimension_cols = sorted([col for col in all_columns if col.startswith("dimension_")])
        columns.extend(dimension_cols)
        all_columns.difference_update(dimension_cols)

        # Add remaining columns
        columns.extend(sorted(all_columns))

        # Write CSV
        Path(output_path).parent.mkdir(parents=True, exist_ok=True)
        with open(output_path, 'w', newline='', encoding='utf-8') as csvfile:
            writer = csv.DictWriter(csvfile, fieldnames=columns)
            writer.writeheader()
            writer.writerows(records)

        return self.generate_dimension_stats(data)

    def prepare_record(self, query: DimensionQuery) -> Dict[str, Any]:
        record = {
            "query": query.generated_text,
            "status": query.status,
        }

        # Add tuple dimension values as separate columns
        for dim_name, dim_value in query.tuple_data.values.items():
            record[f"dimension_{dim_name}"] = dim_value

        return record

    def generate_dimension_stats(self, data: List[DimensionQuery]) -> Dict[str, Any]:
        """Generate statistics specific to dimension queries."""
        stats = self.generate_stats(data)

        # Status distribution
        status_counts = {}
        for query in data:
            status_counts[query.status] = status_counts.get(query.status, 0) + 1

        # Dimension distribution
        dimension_stats = {}
        for query in data:
            for dim_name, dim_value in query.tuple_data.values.items():
                if dim_name not in dimension_stats:
                    dimension_stats[dim_name] = {}
                dimension_stats[dim_name][dim_value] = dimension_stats[dim_name].get(dim_value, 0) + 1

        stats.update({
            "status_distribution": status_counts,
            "dimension_distribution": dimension_stats,
            "unique_tuples": len(set(tuple(sorted(q.tuple_data.values.items())) for q in data)),
            "format": "csv"
        })

        return stats


class DimensionJSONFormatter(BaseFormatter):
    """JSON formatter for dimension-based queries."""

    def format(self, data: List[DimensionQuery], output_path: str) -> Dict[str, Any]:
        if not data:
            raise ValueError("No queries to export")

        # Create export data structure
        export_data = {
            "export_info": {
                "timestamp": datetime.now().isoformat(),
                "total_queries": len(data),
                "format": "json",
                "project_type": "dimension"
            },
            "queries": [self.prepare_record(query) for query in data],
            "statistics": self.generate_dimension_stats(data)
        }

        # Write JSON
        Path(output_path).parent.mkdir(parents=True, exist_ok=True)
        with open(output_path, 'w', encoding='utf-8') as jsonfile:
            json.dump(export_data, jsonfile, indent=2, ensure_ascii=False)

        return self.generate_dimension_stats(data)

    def prepare_record(self, query: DimensionQuery) -> Dict[str, Any]:
        return {
            "query": query.generated_text,
            "status": query.status,
            "tuple": query.tuple_data.values,
            "dimensions": list(query.tuple_data.values.keys())
        }

    def generate_dimension_stats(self, data: List[DimensionQuery]) -> Dict[str, Any]:
        """Generate statistics specific to dimension queries."""
        stats = self.generate_stats(data)

        # Status distribution
        status_counts = {}
        for query in data:
            status_counts[query.status] = status_counts.get(query.status, 0) + 1

        # Dimension distribution
        dimension_stats = {}
        for query in data:
            for dim_name, dim_value in query.tuple_data.values.items():
                if dim_name not in dimension_stats:
                    dimension_stats[dim_name] = {}
                dimension_stats[dim_name][dim_value] = dimension_stats[dim_name].get(dim_value, 0) + 1

        stats.update({
            "status_distribution": status_counts,
            "dimension_distribution": dimension_stats,
            "unique_tuples": len(set(tuple(sorted(q.tuple_data.values.items())) for q in data)),
            "format": "json"
        })

        return stats


class RAGCSVFormatter(BaseFormatter):
    """CSV formatter for RAG queries."""

    def format(self, data: List[RAGQuery], output_path: str) -> Dict[str, Any]:
        if not data:
            raise ValueError("No queries to export")

        # Prepare records
        records = [self.prepare_record(query) for query in data]

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
        Path(output_path).parent.mkdir(parents=True, exist_ok=True)
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

        return self.generate_rag_stats(data)

    def prepare_record(self, query: RAGQuery) -> Dict[str, Any]:
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

    def generate_rag_stats(self, data: List[RAGQuery]) -> Dict[str, Any]:
        """Generate statistics specific to RAG queries."""
        from collections import Counter

        stats = self.generate_stats(data)

        # Difficulty distribution
        difficulty_counts = Counter(query.difficulty for query in data)

        # Realism score statistics
        realism_scores = [q.realism_rating for q in data if q.realism_rating is not None]
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
        chunk_counts = [len(q.source_chunk_ids) for q in data]
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
            for q in data if q.generation_metadata
        ]
        generation_type_counts = dict(Counter(generation_types)) if generation_types else {}

        stats.update({
            "format": "csv",
            "difficulty_distribution": dict(difficulty_counts),
            "realism_statistics": realism_stats,
            "chunk_statistics": chunk_stats,
            "generation_type_distribution": generation_type_counts,
        })

        return stats


class RAGJSONFormatter(BaseFormatter):
    """JSON formatter for RAG queries."""

    def format(self, data: List[RAGQuery], output_path: str) -> Dict[str, Any]:
        if not data:
            raise ValueError("No queries to export")

        export_data = {
            "metadata": {
                "total_queries": len(data),
                "export_format": "json",
                "exported_at": datetime.now().isoformat(),
                "generator": "qgen-rag",
                "project_type": "rag"
            },
            "queries": [self.prepare_record(query) for query in data],
            "statistics": self.generate_rag_stats(data)
        }

        Path(output_path).parent.mkdir(parents=True, exist_ok=True)
        with open(output_path, 'w', encoding='utf-8') as f:
            json.dump(export_data, f, indent=2, ensure_ascii=False)

        return self.generate_rag_stats(data)

    def prepare_record(self, query: RAGQuery) -> Dict[str, Any]:
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

    def generate_rag_stats(self, data: List[RAGQuery]) -> Dict[str, Any]:
        """Generate statistics specific to RAG queries."""
        from collections import Counter

        stats = self.generate_stats(data)

        # Difficulty distribution
        difficulty_counts = Counter(query.difficulty for query in data)

        # Realism score statistics
        realism_scores = [q.realism_rating for q in data if q.realism_rating is not None]
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
        chunk_counts = [len(q.source_chunk_ids) for q in data]
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
            for q in data if q.generation_metadata
        ]
        generation_type_counts = dict(Counter(generation_types)) if generation_types else {}

        stats.update({
            "format": "json",
            "difficulty_distribution": dict(difficulty_counts),
            "realism_statistics": realism_stats,
            "chunk_statistics": chunk_stats,
            "generation_type_distribution": generation_type_counts,
        })

        return stats


class RAGJSONLFormatter(BaseFormatter):
    """JSONL formatter for RAG queries."""

    def format(self, data: List[RAGQuery], output_path: str) -> Dict[str, Any]:
        if not data:
            raise ValueError("No queries to export")

        Path(output_path).parent.mkdir(parents=True, exist_ok=True)
        with open(output_path, 'w', encoding='utf-8') as f:
            for query in data:
                record = self.prepare_record(query)
                f.write(json.dumps(record, ensure_ascii=False) + '\n')

        return self.generate_rag_stats(data)

    def prepare_record(self, query: RAGQuery) -> Dict[str, Any]:
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

    def generate_rag_stats(self, data: List[RAGQuery]) -> Dict[str, Any]:
        """Generate statistics specific to RAG queries."""
        from collections import Counter

        stats = self.generate_stats(data)

        # Difficulty distribution
        difficulty_counts = Counter(query.difficulty for query in data)

        # Realism score statistics
        realism_scores = [q.realism_rating for q in data if q.realism_rating is not None]
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
        chunk_counts = [len(q.source_chunk_ids) for q in data]
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
            for q in data if q.generation_metadata
        ]
        generation_type_counts = dict(Counter(generation_types)) if generation_types else {}

        stats.update({
            "format": "jsonl",
            "difficulty_distribution": dict(difficulty_counts),
            "realism_statistics": realism_stats,
            "chunk_statistics": chunk_stats,
            "generation_type_distribution": generation_type_counts,
        })

        return stats


class FormatterFactory:
    """Factory for creating format-specific exporters."""

    @staticmethod
    def create(project_type: ProjectType, format: ExportFormat) -> BaseFormatter:
        """Create appropriate formatter based on project type and format."""
        formatters = {
            (ProjectType.DIMENSION, ExportFormat.CSV): DimensionCSVFormatter,
            (ProjectType.DIMENSION, ExportFormat.JSON): DimensionJSONFormatter,
            (ProjectType.RAG, ExportFormat.CSV): RAGCSVFormatter,
            (ProjectType.RAG, ExportFormat.JSON): RAGJSONFormatter,
            (ProjectType.RAG, ExportFormat.JSONL): RAGJSONLFormatter,
        }

        formatter_class = formatters.get((project_type, format))
        if not formatter_class:
            raise ValueError(f"Unsupported combination: {project_type.value} + {format.value}")

        return formatter_class()


class UnifiedExporter:
    """Unified export system for both dimension and RAG projects."""

    def __init__(self):
        pass

    def export(self,
               project_type: Union[str, ProjectType],
               data: List[Union[DimensionQuery, RAGQuery]],
               format: Union[str, ExportFormat],
               output_path: str) -> ExportResult:
        """Export data using the appropriate formatter.

        Args:
            project_type: Project type ('dimension' or 'rag')
            data: List of queries to export
            format: Export format ('csv', 'json', 'jsonl')
            output_path: Path where to save the exported file

        Returns:
            ExportResult with metadata and statistics
        """
        # Convert string inputs to enums
        if isinstance(project_type, str):
            project_type = ProjectType(project_type.lower())
        if isinstance(format, str):
            format = ExportFormat(format.lower())

        # Validate format support for project type
        if project_type == ProjectType.DIMENSION and format == ExportFormat.JSONL:
            raise ValueError("JSONL format is not supported for dimension projects")

        # Get appropriate formatter
        formatter = FormatterFactory.create(project_type, format)

        # Perform export
        stats = formatter.format(data, output_path)

        # Return result
        return ExportResult(output_path, stats, format, project_type)

    def get_supported_formats(self, project_type: Union[str, ProjectType]) -> List[ExportFormat]:
        """Get list of supported formats for a project type."""
        if isinstance(project_type, str):
            project_type = ProjectType(project_type.lower())

        if project_type == ProjectType.DIMENSION:
            return [ExportFormat.CSV, ExportFormat.JSON]
        elif project_type == ProjectType.RAG:
            return [ExportFormat.CSV, ExportFormat.JSON, ExportFormat.JSONL]
        else:
            return []

    def generate_export_summary(self, result: ExportResult) -> str:
        """Generate human-readable export summary."""
        lines = [
            f"📊 Export Summary:",
            f"  • Total queries: {result.stats.get('total_queries', 0)}",
            f"  • Format: {result.format.value.upper()}",
            f"  • Project type: {result.project_type.value.title()}",
            f"  • File size: {result.file_size_mb} MB",
            f"  • Path: {result.output_path}",
            ""
        ]

        # Add project-specific statistics
        if result.project_type == ProjectType.DIMENSION:
            if 'status_distribution' in result.stats:
                lines.append("📈 Status Distribution:")
                for status, count in result.stats['status_distribution'].items():
                    percentage = round(count / result.stats['total_queries'] * 100, 1)
                    lines.append(f"  • {status.title()}: {count} ({percentage}%)")
                lines.append("")

            if 'unique_tuples' in result.stats:
                lines.append(f"🎯 Unique dimension combinations: {result.stats['unique_tuples']}")
                lines.append("")

        elif result.project_type == ProjectType.RAG:
            # Difficulty breakdown
            if 'difficulty_distribution' in result.stats:
                lines.append("🎯 Difficulty Distribution:")
                for difficulty, count in result.stats['difficulty_distribution'].items():
                    percentage = round(count / result.stats['total_queries'] * 100, 1)
                    lines.append(f"  • {difficulty.title()}: {count} ({percentage}%)")
                lines.append("")

            # Quality stats
            if 'realism_statistics' in result.stats and result.stats['realism_statistics']:
                realism = result.stats['realism_statistics']
                lines.extend([
                    "⭐ Quality Statistics:",
                    f"  • Average realism: {realism.get('avg_realism_score', 'N/A')}/5.0",
                    f"  • Score range: {realism.get('min_realism_score', 'N/A')}-{realism.get('max_realism_score', 'N/A')}",
                    f"  • Scored queries: {realism.get('scored_queries', 0)}",
                    ""
                ])

            # Chunk stats
            if 'chunk_statistics' in result.stats:
                chunk = result.stats['chunk_statistics']
                lines.extend([
                    "🔗 Source Chunks:",
                    f"  • Average per query: {chunk.get('avg_chunks_per_query', 'N/A')}",
                    f"  • Single-chunk queries: {chunk.get('single_chunk_queries', 0)}",
                    f"  • Multi-chunk queries: {chunk.get('multi_chunk_queries', 0)}",
                    ""
                ])

        return "\n".join(lines)