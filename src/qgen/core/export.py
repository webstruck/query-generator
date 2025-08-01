"""Export functionality for queries and datasets."""

import csv
import json
from pathlib import Path
from typing import List, Dict, Any, Optional
from datetime import datetime

from .models import Query, Tuple
from .data import DataManager


def flatten_query_for_export(query: Query) -> Dict[str, Any]:
    """Flatten a Query object for export to CSV/JSON."""
    flattened = {
        "query": query.generated_text,
        "status": query.status,
    }
    
    # Add tuple dimension values as separate columns
    for dim_name, dim_value in query.tuple_data.values.items():
        flattened[f"dimension_{dim_name}"] = dim_value
    
    return flattened


def export_queries_to_csv(queries: List[Query], output_path: str) -> None:
    """Export queries to CSV format."""
    if not queries:
        raise ValueError("No queries to export")
    
    # Flatten all queries
    flattened_queries = [flatten_query_for_export(query) for query in queries]
    
    # Get all unique column names
    all_columns = set()
    for row in flattened_queries:
        all_columns.update(row.keys())
    
    # Sort columns for consistent output
    columns = sorted(all_columns)
    
    # Ensure core columns come first
    priority_columns = ["query", "status"]
    for col in reversed(priority_columns):
        if col in columns:
            columns.remove(col)
            columns.insert(0, col)
    
    # Write CSV
    output_path = Path(output_path)
    output_path.parent.mkdir(parents=True, exist_ok=True)
    
    with open(output_path, 'w', newline='', encoding='utf-8') as csvfile:
        writer = csv.DictWriter(csvfile, fieldnames=columns)
        writer.writeheader()
        writer.writerows(flattened_queries)


def export_queries_to_json(queries: List[Query], output_path: str) -> None:
    """Export queries to JSON format."""
    if not queries:
        raise ValueError("No queries to export")
    
    # Create export data structure
    export_data = {
        "export_info": {
            "timestamp": datetime.now().isoformat(),
            "total_queries": len(queries),
            "format": "json"
        },
        "queries": []
    }
    
    # Add queries with full structure
    for query in queries:
        query_data = {
            "query": query.generated_text,
            "status": query.status,
            "tuple": query.tuple_data.values,
            "dimensions": list(query.tuple_data.values.keys())
        }
        export_data["queries"].append(query_data)
    
    # Write JSON
    output_path = Path(output_path)
    output_path.parent.mkdir(parents=True, exist_ok=True)
    
    with open(output_path, 'w', encoding='utf-8') as jsonfile:
        json.dump(export_data, jsonfile, indent=2, ensure_ascii=False)


def export_dataset(
    project_path: str,
    format_type: str = "csv",
    output_path: Optional[str] = None,
    stage: str = "approved"
) -> str:
    """
    Export queries as a dataset.
    
    Args:
        project_path: Path to the project directory
        format_type: Export format ('csv' or 'json')
        output_path: Custom output path (optional)
        stage: Which stage of queries to export ('approved', 'raw', 'final')
    
    Returns:
        Path to the exported file
    """
    if format_type not in ["csv", "json"]:
        raise ValueError(f"Unsupported format: {format_type}. Use 'csv' or 'json'")
    
    # Load queries using DataManager
    data_manager = DataManager(project_path)
    queries = data_manager.load_queries(stage)
    
    if not queries:
        raise ValueError(f"No {stage} queries found to export")
    
    # Determine output path
    if output_path is None:
        timestamp = datetime.now().strftime("%Y%m%d_%H%M%S")
        filename = f"dataset_{stage}_{timestamp}.{format_type}"
        output_path = str(Path(project_path) / "data" / "exports" / filename)
    
    # Export based on format
    if format_type == "csv":
        export_queries_to_csv(queries, output_path)
    elif format_type == "json":
        export_queries_to_json(queries, output_path)
    
    return output_path


def get_export_summary(queries: List[Query]) -> Dict[str, Any]:
    """Get summary statistics for export."""
    if not queries:
        return {"total_queries": 0}
    
    # Count by status
    status_counts = {}
    for query in queries:
        status_counts[query.status] = status_counts.get(query.status, 0) + 1
    
    # Count by dimensions
    dimension_stats = {}
    for query in queries:
        for dim_name, dim_value in query.tuple_data.values.items():
            if dim_name not in dimension_stats:
                dimension_stats[dim_name] = {}
            dimension_stats[dim_name][dim_value] = dimension_stats[dim_name].get(dim_value, 0) + 1
    
    return {
        "total_queries": len(queries),
        "status_distribution": status_counts,
        "dimension_distribution": dimension_stats,
        "unique_tuples": len(set(tuple(sorted(q.tuple_data.values.items())) for q in queries))
    }