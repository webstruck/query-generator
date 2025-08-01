"""Dimension validation functions for the Query Generation Tool."""

from typing import List

from .models import Dimension


def validate_dimensions(dimensions: List[Dimension]) -> List[str]:
    """Validate a list of dimensions and return any issues.
    
    Args:
        dimensions: List of dimensions to validate
        
    Returns:
        List of validation issue descriptions
    """
    issues = []
    
    if not dimensions:
        issues.append("No dimensions defined")
        return issues
    
    dimension_names = set()
    for i, dim in enumerate(dimensions):
        # Check for empty names
        if not dim.name.strip():
            issues.append(f"Dimension at index {i} has empty name")
            continue
        
        # Check for duplicate names
        if dim.name in dimension_names:
            issues.append(f"Duplicate dimension name: '{dim.name}'")
        else:
            dimension_names.add(dim.name)
        
        # Check for empty or insufficient values
        if not dim.values:
            issues.append(f"Dimension '{dim.name}' has no values")
        elif len(dim.values) < 2:
            issues.append(f"Dimension '{dim.name}' should have at least 2 values for meaningful variation")
        
        # Check for duplicate values within dimension
        if len(dim.values) != len(set(dim.values)):
            issues.append(f"Dimension '{dim.name}' has duplicate values")
        
        # Check for empty values
        empty_values = [v for v in dim.values if not v.strip()]
        if empty_values:
            issues.append(f"Dimension '{dim.name}' has empty values")
    
    return issues


