"""Educational guidance system for the Query Generation Tool."""

import yaml
from pathlib import Path
from typing import Dict, List, Optional
from rich.console import Console
from rich.panel import Panel

from .models import Dimension

console = Console()


def _get_examples_directory() -> Path:
    """Get the path to the examples directory."""
    return Path(__file__).parent.parent / "examples" / "dimensions"


def _load_domain_yml(domain: str) -> Optional[Dict]:
    """Load domain configuration from YAML file."""
    examples_dir = _get_examples_directory()
    yml_path = examples_dir / f"{domain}.yml"
    
    if not yml_path.exists():
        return None
    
    try:
        with open(yml_path, 'r', encoding='utf-8') as f:
            return yaml.safe_load(f)
    except Exception as e:
        console.print(f"[red]Error loading {domain}.yml: {str(e)}[/red]")
        return None


def list_available_domains() -> List[str]:
    """Get list of available domain templates."""
    examples_dir = _get_examples_directory()
    if not examples_dir.exists():
        return []
    
    domains = []
    for yml_file in examples_dir.glob("*.yml"):
        domain_name = yml_file.stem
        domains.append(domain_name)
    
    return sorted(domains)


def get_domain_template(domain: str) -> Dict:
    """Get domain template data for project initialization."""
    domain_data = _load_domain_yml(domain)
    if not domain_data:
        raise ValueError(f"Domain template '{domain}' not found")
    
    # Extract metadata from YAML, with fallbacks
    name = domain_data.get("name", domain.replace("_", " ").title())
    description = domain_data.get("description", f"{domain} domain template")
    
    return {
        "name": name,
        "description": description,
        "dimensions": domain_data.get("dimensions", []),
        "example_queries": domain_data.get("example_queries", [])
    }


def show_dimension_examples(domain: str = None) -> None:
    """Display examples of dimensions from different domains.
    
    Args:
        domain: Specific domain to show, or None for all domains
    """
    available_domains = list_available_domains()
    
    if domain and domain not in available_domains:
        console.print(f"[red]Unknown domain: {domain}[/red]")
        console.print(f"Available domains: {', '.join(available_domains)}")
        return
    
    domains_to_show = [domain] if domain else available_domains
    
    for domain_key in domains_to_show:
        try:
            template = get_domain_template(domain_key)
            
            # Create the content
            content = f"[bold blue]{template['name']}[/bold blue]\n"
            content += f"{template['description']}\n\n"
            
            content += "[bold]Dimensions:[/bold]\n"
            for dim in template['dimensions']:
                content += f"• [green]{dim['name']}[/green]: {dim['description']}\n"
                content += f"  Values: {', '.join(dim['values'])}\n"
            
            content += "\n[bold]Example Queries:[/bold]\n"
            for query in template['example_queries']:
                content += f"• {query}\n"
            
            console.print(Panel(content, title=f"Domain: {domain_key}", border_style="blue"))
            console.print()
            
        except Exception as e:
            console.print(f"[red]Error loading domain '{domain_key}': {str(e)}[/red]")


def validate_dimension_quality(dimensions: List[Dimension]) -> List[str]:
    """Perform quality checks on dimensions beyond basic validation.
    
    Args:
        dimensions: List of dimensions to check
        
    Returns:
        List of quality suggestions and warnings
    """
    suggestions = []
    
    if len(dimensions) < 2:
        suggestions.append("Consider adding more dimensions for better query variation")
    elif len(dimensions) > 5:
        suggestions.append("Many dimensions can lead to sparse coverage - consider if all are necessary")
    
    for dim in dimensions:
        # Check for very few values
        if len(dim.values) == 2:
            suggestions.append(f"Dimension '{dim.name}' has only 2 values - consider adding more for richer variation")
        
        # Check for too many values
        elif len(dim.values) > 10:
            suggestions.append(f"Dimension '{dim.name}' has many values ({len(dim.values)}) - ensure they're all distinct and necessary")
        
        # Check for generic names
        generic_names = ["type", "category", "kind", "style", "mode"]
        if dim.name.lower() in generic_names:
            suggestions.append(f"Dimension '{dim.name}' has a generic name - consider being more specific")
        
        # Check for vague descriptions
        if len(dim.description.split()) < 4:
            suggestions.append(f"Dimension '{dim.name}' description is quite brief - consider adding more context")
    
    return suggestions


def show_dimension_creation_guide() -> None:
    """Display guidance on creating effective dimensions."""
    guide_content = """
[bold blue]Creating Effective Dimensions[/bold blue]

[bold]1. What are Dimensions?[/bold]
Dimensions are axes of variation that systematically categorize different aspects of user queries.
They help generate diverse, representative queries by varying key characteristics.

[bold]2. Types of Dimensions to Consider:[/bold]
• [green]Functional[/green]: What task/action the user wants (search, schedule, analyze)
• [green]User-based[/green]: Who is the user (persona, expertise level, role)  
• [green]Context[/green]: Situation or scenario (urgent, casual, complex)
• [green]Quality[/green]: How well-formed the request is (specific, vague, ambiguous)

[bold]3. Best Practices:[/bold]
• Start with 2-4 dimensions (you can always add more)
• Each dimension should have 3-6 distinct values
• Values should be mutually exclusive within a dimension
• Use specific, descriptive names rather than generic ones
• Consider your domain's unique characteristics

[bold]4. Common Patterns:[/bold]
Most applications benefit from some version of:
• [yellow]User Intent/Goal[/yellow] - What they're trying to accomplish
• [yellow]User Type/Persona[/yellow] - Who they are
• [yellow]Query Quality[/yellow] - How well-specified their request is

[bold yellow]💡 Need inspiration?[/bold yellow]
Run [cyan]qgen dimensions examples[/cyan] to see real dimension examples from different domains!
"""
    
    console.print(Panel(guide_content, title="Dimension Creation Guide", border_style="green"))