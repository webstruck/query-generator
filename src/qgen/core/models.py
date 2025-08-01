"""Core data models for the Query Generation Tool."""

from typing import Dict, List, Optional, Any
from pydantic import BaseModel, Field


class Dimension(BaseModel):
    """Represents a dimension for query generation."""
    name: str = Field(..., description="Name of the dimension")
    description: str = Field(..., description="Description of what this dimension represents")
    values: List[str] = Field(..., description="Possible values for this dimension")

    def __str__(self) -> str:
        return f"{self.name}: {self.description}"


class Tuple(BaseModel):
    """Represents a combination of dimension values."""
    values: Dict[str, str] = Field(..., description="Mapping of dimension name to selected value")
    
    def __str__(self) -> str:
        items = [f"{k}: {v}" for k, v in self.values.items()]
        return f"({', '.join(items)})"


class Query(BaseModel):
    """Represents a generated query with its associated tuple."""
    tuple_data: Tuple = Field(..., description="The tuple this query was generated from")
    generated_text: str = Field(..., description="The generated query text")
    status: str = Field(default="pending", description="Status: approved, rejected, or pending")
    
    def __str__(self) -> str:
        return f"Query: {self.generated_text} | Status: {self.status}"


class ProjectConfig(BaseModel):
    """Configuration for a query generation project."""
    domain: str = Field(default="application", description="Domain name for this project")
    dimensions: List[Dimension] = Field(default_factory=list, description="Project dimensions")
    example_queries: List[str] = Field(default_factory=list, description="Example queries for few-shot learning")
    llm_params: Dict[str, Any] = Field(
        default_factory=lambda: {
            "temperature": 0.7,
            "max_tokens": 150,
            "top_p": 1.0
        },
        description="LLM generation parameters"
    )
    prompt_template_paths: Dict[str, str] = Field(
        default_factory=lambda: {
            "tuple_generation": "prompts/tuple_generation.txt",
            "query_generation": "prompts/query_generation.txt"
        },
        description="Paths to prompt template files"
    )
    api_key: Optional[str] = Field(default=None, description="OpenAI API key")
    
    def validate_dimensions(self) -> List[str]:
        """Validate dimensions and return list of issues."""
        issues = []
        
        if not self.dimensions:
            issues.append("No dimensions defined")
            return issues
        
        dimension_names = set()
        for dim in self.dimensions:
            if not dim.name.strip():
                issues.append("Dimension with empty name found")
            elif dim.name in dimension_names:
                issues.append(f"Duplicate dimension name: {dim.name}")
            else:
                dimension_names.add(dim.name)
            
            if not dim.values:
                issues.append(f"Dimension '{dim.name}' has no values")
            elif len(dim.values) < 2:
                issues.append(f"Dimension '{dim.name}' should have at least 2 values")
        
        return issues