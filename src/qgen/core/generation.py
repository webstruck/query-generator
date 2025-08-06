"""Core generation logic for tuples and queries."""

import re
from typing import List
from rich.console import Console
from rich.progress import Progress, SpinnerColumn, TextColumn

from .models import ProjectConfig, Dimension, Tuple, Query
from .llm_api import create_llm_provider

console = Console()


def load_prompt_template(template_path: str) -> str:
    """Load prompt template from file."""
    try:
        with open(template_path, 'r', encoding='utf-8') as f:
            return f.read().strip()
    except FileNotFoundError:
        raise FileNotFoundError(f"Prompt template not found: {template_path}")
    except Exception as e:
        raise RuntimeError(f"Error loading prompt template: {str(e)}")


def format_dimensions_description(dimensions: List[Dimension]) -> str:
    """Format dimensions for prompt template."""
    descriptions = []
    for dim in dimensions:
        values_str = ", ".join(dim.values)
        descriptions.append(f"- {dim.name}: {dim.description}. Possible values: {values_str}")
    return "\n".join(descriptions)


def parse_tuples_from_response(response: str, dimensions: List[Dimension]) -> List[Tuple]:
    """Parse tuples from LLM response."""
    tuples = []
    dimension_names = [dim.name for dim in dimensions]
    
    # Look for patterns like (feature: value, persona: value, scenario: value)
    # More flexible regex to handle various formats
    tuple_pattern = r'\([^)]+\)'
    matches = re.findall(tuple_pattern, response)
    
    for match in matches:
        # Remove parentheses and split by commas
        content = match.strip('()')
        parts = [part.strip() for part in content.split(',')]
        
        tuple_values = {}
        
        # Handle two formats:
        # 1. key: value format: (feature: search, persona: buyer, scenario: specific)
        # 2. value only format: (search, buyer, specific) - values in dimension order
        
        has_keys = any(':' in part for part in parts)
        
        if has_keys:
            # Format 1: key: value pairs
            for part in parts:
                if ':' in part:
                    key, value = part.split(':', 1)
                    key = key.strip().lower()
                    value = value.strip().strip('"\'')
                    
                    # Match dimension names (case insensitive)
                    for dim_name in dimension_names:
                        if key == dim_name.lower() or key in dim_name.lower():
                            tuple_values[dim_name] = value
                            break
        else:
            # Format 2: values in dimension order
            if len(parts) == len(dimensions):
                for dim, part in zip(dimensions, parts):
                    value = part.strip().strip('"\'')
                    tuple_values[dim.name] = value
        
        # Only add if we have values for all dimensions
        if len(tuple_values) == len(dimensions):
            # Validate that values are in allowed dimension values
            valid = True
            for dim in dimensions:
                if dim.name in tuple_values:
                    value = tuple_values[dim.name]
                    # Case-insensitive matching
                    if not any(v.lower() == value.lower() for v in dim.values):
                        valid = False
                        break
            
            if valid:
                tuples.append(Tuple(values=tuple_values))
    
    return tuples


def deduplicate_tuples(tuples: List[Tuple]) -> List[Tuple]:
    """Remove duplicate tuples."""
    seen = set()
    unique_tuples = []
    
    for tuple_obj in tuples:
        # Create a hashable representation
        tuple_key = tuple(sorted(tuple_obj.values.items()))
        if tuple_key not in seen:
            seen.add(tuple_key)
            unique_tuples.append(tuple_obj)
    
    return unique_tuples


def generate_tuples(config: ProjectConfig, count: int, provider_type: str = "openai") -> List[Tuple]:
    """Generate tuples using LLM."""
    if not config.dimensions:
        raise ValueError("No dimensions defined in project config")
    
    # Load prompt template
    template_path = config.prompt_template_paths.get("tuple_generation", "prompts/tuple_generation.txt")
    prompt_template = load_prompt_template(template_path)
    
    # Format dimensions description
    dimensions_desc = format_dimensions_description(config.dimensions)
    dimension_names = ", ".join([dim.name for dim in config.dimensions])
    
    # Create prompt
    prompt = prompt_template.format(
        count=count,
        domain=config.domain,
        dimensions_description=dimensions_desc,
        dimension_names=dimension_names
    )
    
    console.print(f"🎲 Generating {count} tuples...")
    
    # Create LLM provider
    try:
        if provider_type == "azure":
            llm = create_llm_provider("azure")
        elif provider_type == "github":
            llm = create_llm_provider("github")
        else:
            llm = create_llm_provider("openai", api_key=config.api_key)
    except Exception as e:
        console.print(f"[red]❌ Error creating LLM provider: {str(e)}[/red]")
        raise
    
    # Generate tuples
    with Progress(
        SpinnerColumn(),
        TextColumn("[progress.description]{task.description}"),
        console=console,
    ) as progress:
        progress.add_task("Calling LLM...", total=None)
        
        try:
            response = llm.generate_text(prompt, **config.llm_params)
        except Exception as e:
            console.print(f"[red]❌ Error generating tuples: {str(e)}[/red]")
            raise
    
    # Parse tuples from response
    tuples = parse_tuples_from_response(response, config.dimensions)
    
    if not tuples:
        console.print("[yellow]⚠️  No valid tuples found in LLM response[/yellow]")
        console.print(f"Raw response: {response}")
        return []
    
    # Deduplicate
    unique_tuples = deduplicate_tuples(tuples)
    
    console.print(f"✅ Generated {len(unique_tuples)} unique tuples (from {len(tuples)} total)")
    
    return unique_tuples


def generate_queries(config: ProjectConfig, tuples: List[Tuple], queries_per_tuple: int = 3, provider_type: str = "openai") -> List[Query]:
    """Generate queries from tuples using LLM."""
    if not tuples:
        raise ValueError("No tuples provided for query generation")
    
    # Load prompt template
    template_path = config.prompt_template_paths.get("query_generation", "prompts/query_generation.txt")
    prompt_template = load_prompt_template(template_path)
    
    # Create LLM provider
    try:
        if provider_type == "azure":
            llm = create_llm_provider("azure")
        elif provider_type == "github":
            llm = create_llm_provider("github")
        else:
            llm = create_llm_provider("openai", api_key=config.api_key)
    except Exception as e:
        console.print(f"[red]❌ Error creating LLM provider: {str(e)}[/red]")
        raise
    
    # Format few-shot examples
    few_shot_examples = ""
    if config.example_queries:
        examples_text = "\n".join([f"- {query}" for query in config.example_queries])
        few_shot_examples = f"Example queries:\n{examples_text}\n"
    
    queries = []
    
    with Progress(
        SpinnerColumn(),
        TextColumn("[progress.description]{task.description}"),
        console=console,
    ) as progress:
        task = progress.add_task(f"Generating queries...", total=len(tuples))
        
        for i, tuple_obj in enumerate(tuples):
            # Format tuple description
            tuple_desc = ", ".join([f"{k}: {v}" for k, v in tuple_obj.values.items()])
            
            # Create prompt for this tuple - ask for multiple queries
            prompt = prompt_template.format(
                domain=config.domain,
                tuple_description=tuple_desc,
                few_shot_examples=few_shot_examples,
                count=queries_per_tuple
            )
            
            try:
                response = llm.generate_text(prompt, **config.llm_params)
                
                # Parse multiple queries from the response
                query_lines = [line.strip() for line in response.strip().split('\n') if line.strip()]
                
                # Clean up query lines (remove numbering, bullets, etc.)
                parsed_queries = []
                for line in query_lines:
                    # Remove common prefixes like "1.", "-", "*", etc.
                    cleaned = line.lstrip('0123456789.-* ').strip()
                    if cleaned and len(cleaned) > 10:  # Filter out very short responses
                        parsed_queries.append(cleaned)
                
                # Create Query objects, limit to requested count
                for query_text in parsed_queries[:queries_per_tuple]:
                    query = Query(
                        tuple_data=tuple_obj,
                        generated_text=query_text,
                        status="pending"
                    )
                    queries.append(query)
                    
            except Exception as e:
                console.print(f"[red]❌ Error generating queries for tuple {i+1}: {str(e)}[/red]")
                # Continue with other queries
                continue
            
            progress.update(task, advance=1)
    
    console.print(f"✅ Generated {len(queries)} queries from {len(tuples)} tuples")
    
    return queries