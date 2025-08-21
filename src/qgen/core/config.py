"""Project configuration management for the Query Generation Tool."""

import os
import yaml
from pathlib import Path
from typing import Dict, List, Optional

from .models import ProjectConfig, Dimension


class ConfigurationError(Exception):
    """Raised when there's an issue with project configuration."""
    pass


def load_project_config(directory: str = ".") -> ProjectConfig:
    """Load ProjectConfig by assembling from dimensions.yml and config.yml files.
    
    Args:
        directory: Project directory path
        
    Returns:
        ProjectConfig: Assembled configuration object
        
    Raises:
        ConfigurationError: If required files are missing or invalid
    """
    dir_path = Path(directory)
    dimensions_file = dir_path / "dimensions.yml"
    config_file = dir_path / "config.yml"
    
    # Load dimensions and example queries
    if not dimensions_file.exists():
        raise ConfigurationError(f"dimensions.yml not found in {directory}")
    
    with open(dimensions_file, 'r') as f:
        dimensions_data = yaml.safe_load(f)
    
    dimensions = [Dimension(**dim) for dim in dimensions_data.get('dimensions', [])]
    example_queries = dimensions_data.get('example_queries', [])
    domain = dimensions_data.get('domain', 'application')
    
    # Load technical configuration (optional)
    llm_params = {
        "temperature": 1,
        "top_p": 1.0
    }
    prompt_template_paths = {
        "tuple_generation": "prompts/tuple_generation.txt",
        "query_generation": "prompts/query_generation.txt"
    }
    api_key = None
    
    if config_file.exists():
        with open(config_file, 'r') as f:
            config_data = yaml.safe_load(f)
        
        llm_params.update(config_data.get('llm_params', {}))
        prompt_template_paths.update(config_data.get('prompt_template_paths', {}))
        api_key = config_data.get('api_key')
    
    return ProjectConfig(
        domain=domain,
        dimensions=dimensions,
        example_queries=example_queries,
        llm_params=llm_params,
        prompt_template_paths=prompt_template_paths,
        api_key=api_key
    )


def save_project_config(config: ProjectConfig, directory: str = ".") -> None:
    """Save ProjectConfig by splitting into dimensions.yml and config.yml files.
    
    Args:
        config: ProjectConfig object to save
        directory: Target directory path
    """
    dir_path = Path(directory)
    dir_path.mkdir(parents=True, exist_ok=True)
    
    # Save dimensions and example queries
    dimensions_data = {
        'domain': config.domain,
        'dimensions': [dim.model_dump() for dim in config.dimensions],
        'example_queries': config.example_queries
    }
    
    dimensions_file = dir_path / "dimensions.yml"
    with open(dimensions_file, 'w') as f:
        yaml.dump(dimensions_data, f, default_flow_style=False, indent=2)
    
    # Save technical configuration
    config_data = {
        'llm_params': config.llm_params,
        'prompt_template_paths': config.prompt_template_paths
    }
    
    if config.api_key:
        config_data['api_key'] = config.api_key
    
    config_file = dir_path / "config.yml"
    with open(config_file, 'w') as f:
        yaml.dump(config_data, f, default_flow_style=False, indent=2)


def validate_project_directory(directory: str) -> List[str]:
    """Validate that a directory contains a valid project configuration.
    
    Args:
        directory: Directory path to validate
        
    Returns:
        List of validation issues (empty if valid)
    """
    issues = []
    dir_path = Path(directory)
    
    if not dir_path.exists():
        issues.append(f"Directory does not exist: {directory}")
        return issues
    
    if not dir_path.is_dir():
        issues.append(f"Path is not a directory: {directory}")
        return issues
    
    # Check for required files
    dimensions_file = dir_path / "dimensions.yml"
    if not dimensions_file.exists():
        issues.append("Missing dimensions.yml file")
    
    # Try to load and validate configuration
    try:
        config = load_project_config(directory)
        validation_issues = config.validate_dimensions()
        issues.extend(validation_issues)
    except Exception as e:
        issues.append(f"Configuration loading error: {str(e)}")
    
    return issues