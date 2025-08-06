"""CLI entry point for the Query Generation Tool."""

import typer
from pathlib import Path
from rich.console import Console
from typing import Optional
from qgen.core.rich_output import (
    show_project_init_success, 
    show_project_status,
    show_error_panel,
    show_validation_results,
    show_generation_summary,
    show_export_summary,
    show_generation_start,
    show_tuples_found,
    show_prompt_customization_offer,
    show_file_edit_instruction,
    show_no_items_generated,
    create_success_panel,
    create_action_panel,
    create_info_panel,
    create_tip_panel,
    format_file_path,
    format_key_value_pairs,
    format_numbered_list
)

from qgen.core.env import ensure_environment_loaded, get_available_providers, auto_detect_provider

from qgen.core.config import load_project_config, save_project_config, ConfigurationError
from qgen.core.dimensions import validate_dimensions
from qgen.core.guidance import (
    show_dimension_examples, 
    validate_dimension_quality, 
    show_dimension_creation_guide,
    get_domain_template,
    list_available_domains
)
from qgen.core.models import ProjectConfig, Dimension, Query
from qgen.core.generation import generate_tuples as core_generate_tuples
from qgen.core.data import get_data_manager
from qgen.cli.review import review_tuples

app = typer.Typer(help="Query Generation Tool - Generate synthetic queries using LLMs")
console = Console()

# Command groups
dimensions_app = typer.Typer(help="Manage dimensions")
generate_app = typer.Typer(help="Generate tuples and queries")
review_app = typer.Typer(help="Review existing tuples and queries")

app.add_typer(dimensions_app, name="dimensions")
app.add_typer(generate_app, name="generate")
app.add_typer(review_app, name="review")


@app.command()
def init(
    project_name: str = typer.Argument(help="Name of the project to create"),
    template: Optional[str] = typer.Option(
        "real_estate", 
        help="Template to use: " + ", ".join(list_available_domains())
    )
):
    """Initialize a new query generation project."""
    console.print(f"🚀 Initializing project: {project_name}")
    console.print(f"📋 Using template: {template}")
    
    # Check if directory already exists
    project_path = Path(project_name)
    if project_path.exists():
        show_error_panel(
            "Directory Already Exists", 
            f"Directory '{project_name}' already exists",
            ["Choose a different project name", "Remove the existing directory first"]
        )
        raise typer.Exit(1)
    
    # Validate template
    available_domains = list_available_domains()
    if template not in available_domains:
        show_error_panel(
            "Unknown Template",
            f"Template '{template}' not found",
            [f"Available templates: {', '.join(available_domains)}", "Use qgen init --help to see template options"]
        )
        raise typer.Exit(1)
    
    try:
        # Create project directory
        project_path.mkdir(parents=True)
        
        # Get template data
        template_data = get_domain_template(template)
        
        # Create ProjectConfig from template
        dimensions = [Dimension(**dim) for dim in template_data['dimensions']]
        config = ProjectConfig(
            domain=template_data['name'],
            dimensions=dimensions,
            example_queries=template_data['example_queries']
        )
        
        # Save configuration files
        save_project_config(config, str(project_path))
        
        # Create comprehensive data directory structure
        data_dir = project_path / "data"
        data_dir.mkdir()
        
        # Create subdirectories for organized data management
        (data_dir / "tuples").mkdir()
        (data_dir / "queries").mkdir()
        (data_dir / "exports").mkdir()

        # Create prompts directory and copy templates
        prompts_dir = project_path / "prompts"
        prompts_dir.mkdir()
        
        # Copy prompt templates from the package
        package_prompts_dir = Path(__file__).parent.parent / "prompts"
        template_count = 0
        if package_prompts_dir.exists():
            import shutil
            for template_file in package_prompts_dir.glob("*.txt"):
                shutil.copy2(template_file, prompts_dir / template_file.name)
                template_count += 1
        
        # Show beautiful success message using panels
        show_project_init_success(
            project_path=project_path,
            template_name=template_data['name'],
            dimensions_count=len(dimensions),
            examples_count=len(template_data['example_queries'])
        )
        
    except Exception as e:
        console.print(f"[red]❌ Failed to create project: {str(e)}[/red]")
        # Clean up if directory was created
        if project_path.exists():
            import shutil
            shutil.rmtree(project_path)
        raise typer.Exit(1)




@dimensions_app.command("validate")
def validate_dimensions_cmd():
    """Validate current project dimensions."""
    
    # Validate we're in a project directory
    if not Path("dimensions.yml").exists():
        show_error_panel(
            "Not in a Project Directory",
            "No dimensions.yml found in current directory",
            ["Run qgen init <project_name> to create a new project", "Use qgen --help to see all commands"]
        )
        raise typer.Exit(1)
    
    try:
        # Load and validate project
        config = load_project_config(".")
        
        # Basic validation
        basic_issues = validate_dimensions(config.dimensions)
        
        # Quality suggestions
        quality_suggestions = validate_dimension_quality(config.dimensions)
        
        # Show project overview
        project_info = format_key_value_pairs({
            "Dimensions": len(config.dimensions),
            "Example Queries": len(config.example_queries),
            "Domain": config.domain
        })
        
        console.print()
        console.print(create_info_panel("📊 Project Analysis", project_info))
        
        # Use the existing validation results display function
        show_validation_results(basic_issues, quality_suggestions)
        
        # Next steps based on validation results
        if not basic_issues and not quality_suggestions:
            next_steps = format_numbered_list([
                "[cyan]qgen generate tuples[/cyan] - Create dimension combinations",
                "Consider customizing [yellow]prompts/[/yellow] files first for better results", 
                "Run [green]qgen --help[/green] to see all available commands"
            ])
            console.print(create_action_panel("🎯 Next Steps", next_steps))
        elif not basic_issues:
            console.print(create_action_panel("🎯 Next Steps", 
                "Consider the suggestions above, then run [cyan]qgen generate tuples[/cyan]"))
        else:
            show_error_panel(
                "Validation Failed",
                "Please fix validation issues before proceeding",
                ["Run qgen dimensions examples for inspiration", "Check qgen dimensions guide for best practices"]
            )
            raise typer.Exit(1)
            
    except ConfigurationError as e:
        console.print(f"[red]❌ Configuration error: {str(e)}[/red]")
        raise typer.Exit(1)
    except Exception as e:
        console.print(f"[red]❌ Validation failed: {str(e)}[/red]")
        raise typer.Exit(1)


@dimensions_app.command("examples")
def show_dimension_examples_cmd(
    domain: Optional[str] = typer.Option(None, help="Specific domain to show")
):
    """Show examples of dimensions from different domains."""
    if domain:
        console.print(f"📚 Showing examples for domain: {domain}")
    else:
        console.print("📚 Showing dimension examples from all domains...")
    
    try:
        show_dimension_examples(domain)
        
        if not domain:
            console.print("\n[bold]💡 Creating Your Own Dimensions?[/bold]")
            console.print("Run: qgen dimensions guide")
            
    except Exception as e:
        console.print(f"[red]❌ Error showing examples: {str(e)}[/red]")
        raise typer.Exit(1)


@dimensions_app.command("guide")
def show_dimension_guide():
    """Show guide for creating effective dimensions."""
    show_dimension_creation_guide()


@generate_app.command("tuples")
def generate_tuples(
    count: int = typer.Option(20, help="Number of tuples to generate"),
    review: bool = typer.Option(True, help="Launch review interface after generation"),
    output: str = typer.Option("data/tuples/generated.json", help="Output file for generated tuples"),
    provider: Optional[str] = typer.Option(None, help="LLM provider: openai, azure, or github (auto-detect if not specified)"),
    skip_guidance: bool = typer.Option(False, help="Skip interactive prompt customization guidance")
):
    """Generate tuple combinations from dimensions."""
    
    # Load environment variables
    ensure_environment_loaded(verbose=True)
    
    # Auto-detect provider if not specified
    if provider is None:
        provider = auto_detect_provider()
        if provider is None:
            console.print("[red]❌ No LLM provider configuration found in environment[/red]")
            console.print("💡 Please set OpenAI, Azure OpenAI, or GitHub Models environment variables in .env file")
            console.print("🔍 Need help? Run [green]qgen --help[/green] or check project documentation")
            raise typer.Exit(1)
        console.print(f"[blue]🔍 Auto-detected provider: {provider}[/blue]")
    else:
        # Validate specified provider is available
        available_providers = get_available_providers()
        if provider not in available_providers:
            console.print(f"[red]❌ Provider '{provider}' not available[/red]")
            if available_providers:
                console.print(f"Available providers: {', '.join(available_providers)}")
            else:
                console.print("No providers configured. Please check your .env file.")
            raise typer.Exit(1)
    
    # Validate we're in a project directory
    if not Path("dimensions.yml").exists():
        show_error_panel(
            "Not in a Project Directory",
            "No dimensions.yml found in current directory",
            ["Run qgen init <project_name> to create a new project", "Use qgen --help to see all commands"]
        )
        raise typer.Exit(1)
    
    try:
        # Load project configuration
        config = load_project_config(".")
        
        # Show generation start info
        show_generation_start("tuple", count, provider)
        
        # Validate dimensions before generation
        validation_issues = validate_dimensions(config.dimensions)
        if validation_issues:
            console.print("[red]❌ Dimension validation failed:[/red]")
            for issue in validation_issues:
                console.print(f"  • {issue}")
            console.print("\nRun 'qgen dimensions validate' for more details")
            raise typer.Exit(1)
        
        # Interactive prompt customization guidance (unless skipped)
        if not skip_guidance:
            # Show tuple-specific customization panel
            content = (
                "📝 You can edit [cyan]prompts/tuple_generation.txt[/cyan] to:\n\n"
                "[bold]Benefits:[/bold]\n"
                "• Tailor the prompt style to your domain\n"
                "• Add specific examples and requirements\n"
                "• Control how dimension combinations are created\n"
                "• Improve tuple diversity and quality\n\n"
                "[bold]🔄 Customize prompts first?[/bold] [dim](y/N)[/dim]"
            )
            
            console.print()
            console.print(create_tip_panel("Prompt Customization", content))
            
            # Ask user if they want to customize first
            try:
                user_input = input().strip().lower()
                if user_input in ['y', 'yes']:
                    show_file_edit_instruction("prompts/tuple_generation.txt")
                    input()
            except (EOFError, KeyboardInterrupt):
                console.print("\n🚀 Continuing with generation...")
        
        # Generate tuples
        tuples = core_generate_tuples(config, count, provider)
        
        if not tuples:
            show_no_items_generated("tuple")
            raise typer.Exit(1)
        
        # Review tuples if requested
        approved_tuples = tuples
        if review:
            approved_tuples = review_tuples(tuples)
            
            if not approved_tuples:
                console.print("[yellow]⚠️  No tuples approved. Exiting without saving.[/yellow]")
                raise typer.Exit(0)
        
        # Use DataManager for organized saving
        data_manager = get_data_manager(".")
        
        # Save generated tuples
        generated_path = data_manager.save_tuples(
            tuples, 
            "generated", 
            {"provider": provider, "count_requested": count}
        )
        
        # Save approved tuples
        approved_path = data_manager.save_tuples(
            approved_tuples,
            "approved",
            {
                "provider": provider,
                "generated_count": len(tuples),
                "approval_rate": len(approved_tuples) / len(tuples) if tuples else 0
            }
        )
        
        # Also save to specified output path for backward compatibility
        if output != "data/tuples/generated.json":
            output_path = Path(output)
            output_path.parent.mkdir(parents=True, exist_ok=True)
            import json
            with open(output_path, 'w', encoding='utf-8') as f:
                json.dump(
                    [{"values": t.values} for t in approved_tuples],
                    f,
                    indent=2,
                    ensure_ascii=False
                )
        
        # Show generation summary
        show_generation_summary("tuple", len(tuples), file_path=Path(generated_path))
        
        # Show approval summary if different
        if len(approved_tuples) != len(tuples):
            approval_rate = len(approved_tuples) / len(tuples) * 100 if tuples else 0
            approval_info = f"{len(approved_tuples)} tuples ({approval_rate:.1f}% approval rate)"
            console.print()
            console.print(create_success_panel("✅ Approval Complete", 
                f"Approved: {approval_info}\nSaved to: {format_file_path(Path(approved_path), 60)}"))
        
        # Additional output info if custom path
        if output != "data/tuples/generated.json":
            console.print()
            console.print(create_info_panel("📄 Additional Output", 
                f"Also saved to: {format_file_path(Path(output), 60)}"))
        
        # Next steps
        console.print()
        console.print(create_action_panel("🎯 Next Steps", 
            "Run [cyan]qgen generate queries[/cyan] to generate queries from approved tuples"))
        
    except ConfigurationError as e:
        console.print(f"[red]❌ Configuration error: {str(e)}[/red]")
        raise typer.Exit(1)
    except Exception as e:
        console.print(f"[red]❌ Failed to generate tuples: {str(e)}[/red]")
        raise typer.Exit(1)


@generate_app.command("queries")
def generate_queries(
    input_file: Optional[str] = typer.Option(
        None, 
        help="Path to approved tuples file (default: data/tuples/approved.json)"
    ),
    review: bool = typer.Option(True, help="Launch review interface after generation"),
    provider: Optional[str] = typer.Option(None, help="LLM provider: openai, azure, or github (auto-detect if not specified)"),
    queries_per_tuple: int = typer.Option(3, help="Number of queries to generate per tuple"),
    skip_guidance: bool = typer.Option(False, help="Skip interactive prompt customization guidance")
):
    """Generate queries from approved tuples."""
    console.print("💬 Generating queries from tuples...")
    
    # Load environment variables
    ensure_environment_loaded(verbose=True)
    
    # Auto-detect provider if not specified
    if provider is None:
        provider = auto_detect_provider()
        if provider is None:
            console.print("[red]❌ No LLM provider configuration found in environment[/red]")
            console.print("💡 Please set OpenAI, Azure OpenAI, or GitHub Models environment variables in .env file")
            console.print("🔍 Need help? Run [green]qgen --help[/green] or check project documentation")
            raise typer.Exit(1)
        console.print(f"[blue]🔍 Auto-detected provider: {provider}[/blue]")
    else:
        # Validate specified provider is available
        available_providers = get_available_providers()
        if provider not in available_providers:
            console.print(f"[red]❌ Provider '{provider}' not available[/red]")
            if available_providers:
                console.print(f"Available providers: {', '.join(available_providers)}")
            else:
                console.print("No providers configured. Please check your .env file.")
            raise typer.Exit(1)
    
    # Validate we're in a project directory
    if not Path("dimensions.yml").exists():
        console.print("[red]❌ Not in a project directory (no dimensions.yml found)[/red]")
        console.print("💡 Run [green]qgen init <project_name>[/green] to create a new project")
        console.print("🔍 Need help? Run [green]qgen --help[/green] for all commands")
        raise typer.Exit(1)
    
    try:
        # Determine input file
        if input_file is None:
            input_file = "data/tuples/approved.json"
        
        # Check if input file exists
        input_path = Path(input_file)
        if not input_path.exists():
            console.print(f"[red]❌ Input file not found: {input_file}[/red]")
            console.print("Run 'qgen generate tuples' first to create tuples or 'qgen review tuples' if they exist")
            raise typer.Exit(1)
        
        # Load project configuration
        config = load_project_config(".")
        
        # Use DataManager to load approved tuples
        data_manager = get_data_manager(".")
        tuples = data_manager.load_tuples("approved")
        
        if not tuples:
            console.print(f"[red]❌ No approved tuples found in {input_file}[/red]")
            console.print("Run 'qgen generate tuples' first to create tuples or 'qgen review tuples' if they exist")
            raise typer.Exit(1)
        
        show_tuples_found(len(tuples), input_file)
        
        # Interactive prompt customization guidance (unless skipped)
        if not skip_guidance:
            show_prompt_customization_offer()
            
            # Ask user if they want to customize first
            try:
                user_input = input().strip().lower()
                if user_input in ['y', 'yes']:
                    show_file_edit_instruction("prompts/query_generation.txt")
                    input()
            except (EOFError, KeyboardInterrupt):
                console.print("\n🚀 Continuing with generation...")
        
        # Show generation start
        show_generation_start("query", len(tuples) * queries_per_tuple, provider)
        
        # Generate queries using the core generation function
        from qgen.core.generation import generate_queries as core_generate_queries
        queries = core_generate_queries(config, tuples, queries_per_tuple, provider)
        
        if not queries:
            show_no_items_generated("query")
            raise typer.Exit(1)
        
        # Review queries if requested
        if review:
            from qgen.cli.review import review_queries
            approved_queries = review_queries(queries)
            
            if not approved_queries:
                console.print("[yellow]⚠️  No queries approved. Exiting without saving.[/yellow]")
                raise typer.Exit(0)
        else:
            # Auto-approve all queries when review is skipped
            approved_queries = []
            for query in queries:
                # Create a copy with approved status
                approved_query = Query(
                    tuple_data=query.tuple_data,
                    generated_text=query.generated_text,
                    status="approved"
                )
                approved_queries.append(approved_query)
        
        # Use DataManager to save queries
        generated_path = data_manager.save_queries(
            queries, 
            "generated",
            {
                "provider": provider,
                "queries_per_tuple": queries_per_tuple,
                "total_tuples": len(tuples)
            }
        )
        
        approved_path = data_manager.save_queries(
            approved_queries,
            "approved", 
            {
                "provider": provider,
                "queries_per_tuple": queries_per_tuple,
                "approval_rate": len(approved_queries) / len(queries) if queries else 0,
                "total_tuples": len(tuples)
            }
        )
        
        # Show generation summary
        show_generation_summary("query", len(queries), file_path=Path(generated_path))
        
        # Show approval summary if different
        if len(approved_queries) != len(queries):
            approval_rate = len(approved_queries) / len(queries) * 100 if queries else 0
            approval_info = f"{len(approved_queries)} queries ({approval_rate:.1f}% approval rate)"
            console.print()
            console.print(create_success_panel("✅ Approval Complete", 
                f"Approved: {approval_info}\nSaved to: {format_file_path(Path(approved_path), 60)}"))
        
        # Next steps
        console.print()
        console.print(create_action_panel("🎯 Next Steps", 
            "Run [cyan]qgen export[/cyan] to create final dataset"))
        
    except ConfigurationError as e:
        console.print(f"[red]❌ Configuration error: {str(e)}[/red]")
        raise typer.Exit(1)
    except Exception as e:
        console.print(f"[red]❌ Failed to generate queries: {str(e)}[/red]")
        raise typer.Exit(1)


@app.command()
def export(
    format: str = typer.Option("csv", help="Export format: csv or json"),
    output: Optional[str] = typer.Option(None, help="Output file path (auto-generated if not specified)"),
    stage: str = typer.Option("approved", help="Stage to export: approved or generated"),
    show_summary: bool = typer.Option(True, help="Show export summary statistics")
):
    """Export generated queries to file."""
    
    # Validate we're in a project directory
    if not Path("dimensions.yml").exists():
        show_error_panel(
            "Not in a Project Directory",
            "No dimensions.yml found in current directory",
            ["Run qgen init <project_name> to create a new project", "Use qgen --help to see all commands"]
        )
        raise typer.Exit(1)
    
    try:
        from qgen.core.export import export_dataset, get_export_summary
        from qgen.core.data import get_data_manager
        
        # Validate format
        if format not in ["csv", "json"]:
            show_error_panel(
                "Unsupported Format",
                f"Format '{format}' is not supported",
                ["Use 'csv' for spreadsheet compatibility", "Use 'json' for programmatic access", "Supported formats: csv, json"]
            )
            raise typer.Exit(1)
        
        # Validate stage
        if stage not in ["approved", "generated"]:
            show_error_panel(
                "Unsupported Stage",
                f"Stage '{stage}' is not supported", 
                ["Use 'approved' for final dataset", "Use 'generated' for all queries", "Supported stages: approved, generated"]
            )
            raise typer.Exit(1)
        
        # Check if queries exist for the specified stage
        data_manager = get_data_manager(".")
        queries = data_manager.load_queries(stage)
        
        if not queries:
            suggestions = ["Run qgen generate queries first to create queries", "If queries exist, try: qgen review queries", "Use qgen --help to see the workflow"]
            if stage == "generated":
                suggestions = ["Run qgen generate queries to create queries", "If queries exist, try: qgen review queries", "Check if queries exist in approved stage instead"]
            
            show_error_panel(
                f"No {stage.title()} Queries Found",
                f"No queries available for export at '{stage}' stage",
                suggestions
            )
            raise typer.Exit(1)
        
        # Show pre-export summary
        if show_summary:
            summary = get_export_summary(queries)
            
            # Prepare summary info
            summary_info = format_key_value_pairs({
                "Total Queries": summary['total_queries'],
                "Unique Tuples": summary['unique_tuples'],
                "Export Format": format.upper(),
                "Export Stage": stage
            })
            
            if summary.get('status_distribution'):
                status_info = "\n\n[bold]Status Distribution:[/bold]\n"
                for status, count in summary['status_distribution'].items():
                    status_info += f"• {status}: {count}\n"
                summary_info += status_info.rstrip()
            
            console.print()
            console.print(create_info_panel("📈 Export Preview", summary_info))
        
        # Export the dataset
        exported_path = export_dataset(".", format, output, stage)
        
        # Show export success with panels
        show_export_summary(format, Path(exported_path), len(queries), 
                          get_export_summary(queries) if show_summary else {})
        
        # Update project status by triggering a refresh
        data_manager.get_project_status()  # This will update exports info
        
    except ValueError as e:
        console.print(f"[red]❌ Export error: {str(e)}[/red]")
        raise typer.Exit(1)
    except Exception as e:
        console.print(f"[red]❌ Failed to export: {str(e)}[/red]")
        raise typer.Exit(1)


@app.command()
def status():
    """Show current project status and data organization."""
    # Load environment
    ensure_environment_loaded(verbose=False)
    
    # Check if we're in a project directory
    if not Path("dimensions.yml").exists():
        show_error_panel(
            "Not in a Project Directory",
            "No dimensions.yml found in current directory",
            ["Run qgen init <project_name> to create a new project", "Use qgen --help to see all commands"]
        )
        raise typer.Exit(1)
    
    try:
        # Load project config
        config = load_project_config(".")
        
        # Get data status
        data_manager = get_data_manager(".")
        project_status = data_manager.get_project_status()
        
        # Available providers
        available_providers = get_available_providers()
        auto_provider = auto_detect_provider()
        
        # Prepare data for panel display
        data_summary = {
            'tuples_generated': 0,
            'tuples_approved': 0,
            'queries_generated': 0,
            'queries_approved': 0,
            'exports': 0
        }
        
        # Process tuples data
        tuples_status = project_status.get("tuples", {})
        for stage, info in tuples_status.items():
            if isinstance(info, dict) and "count" in info:
                if stage == "generated":
                    data_summary['tuples_generated'] = info['count']
                elif stage == "approved":
                    data_summary['tuples_approved'] = info['count']
        
        # Process queries data
        queries_status = project_status.get("queries", {})
        for stage, info in queries_status.items():
            if isinstance(info, dict) and "count" in info:
                if stage == "generated":
                    data_summary['queries_generated'] = info['count']
                elif stage == "approved":
                    data_summary['queries_approved'] = info['count']
        
        # Process exports data
        exports_status = project_status.get("exports", {})
        if exports_status:
            data_summary['exports'] = exports_status.get("files", 0)
        
        # Generate recommendations
        recommendations = []
        if not tuples_status:
            recommendations.append("Generate tuples: [cyan]qgen generate tuples[/cyan]")
        elif not queries_status:
            recommendations.append("Generate queries: [cyan]qgen generate queries[/cyan]")
        elif data_summary['exports'] == 0:
            recommendations.append("Export dataset: [cyan]qgen export[/cyan]")
        
        if data_summary['tuples_generated'] > 0 or data_summary['queries_generated'] > 0:
            recommendations.append("Customize prompts in [yellow]prompts/[/yellow] directory")
            recommendations.append("Run [cyan]qgen dimensions validate[/cyan] to check quality")
        
        recommendations.extend([
            "Check [cyan]qgen dimensions examples[/cyan] for inspiration",
            "Use [cyan]qgen --help[/cyan] to see all commands"
        ])
        
        # Show beautiful status using panels
        show_project_status(config, data_summary, recommendations)
            
    except Exception as e:
        console.print(f"[red]❌ Error checking project status: {str(e)}[/red]")
        raise typer.Exit(1)


@review_app.command("tuples")
def review_tuples_cmd():
    """Review existing generated tuples."""
    # Check if we're in a project directory
    if not Path("dimensions.yml").exists():
        show_error_panel(
            "Not in a Project Directory",
            "No dimensions.yml found in current directory",
            ["Run qgen init <project_name> to create a new project", "Use qgen --help to see all commands"]
        )
        raise typer.Exit(1)
    
    try:
        # Use DataManager to load generated tuples
        data_manager = get_data_manager(".")
        tuples = data_manager.load_tuples("generated")
        
        if not tuples:
            show_error_panel(
                "No Generated Tuples Found",
                "No tuples available for review",
                ["Run qgen generate tuples to create tuples first", "If tuples exist, try: qgen review tuples", "Check if tuples exist in data/tuples/generated.json"]
            )
            raise typer.Exit(1)
        
        # Launch review interface
        approved_tuples = review_tuples(tuples)
        
        if not approved_tuples:
            console.print("[yellow]⚠️  No tuples were approved during review.[/yellow]")
            raise typer.Exit(0)
        
        # Save approved tuples
        approved_path = data_manager.save_tuples(
            approved_tuples,
            "approved",
            {
                "generated_count": len(tuples),
                "approval_rate": len(approved_tuples) / len(tuples) if tuples else 0
            }
        )
        
        # Show success summary
        show_generation_summary(
            "tuple", 
            len(approved_tuples), 
            total_count=len(tuples), 
            file_path=Path(approved_path), 
            next_step="Run [cyan]qgen generate queries[/cyan] to generate queries from approved tuples"
        )
        
    except Exception as e:
        console.print(f"[red]❌ Failed to review tuples: {str(e)}[/red]")
        raise typer.Exit(1)


@review_app.command("queries")
def review_queries_cmd():
    """Review existing generated queries."""
    # Check if we're in a project directory
    if not Path("dimensions.yml").exists():
        show_error_panel(
            "Not in a Project Directory", 
            "No dimensions.yml found in current directory",
            ["Run qgen init <project_name> to create a new project", "Use qgen --help to see all commands"]
        )
        raise typer.Exit(1)
    
    try:
        # Use DataManager to load generated queries
        data_manager = get_data_manager(".")
        queries = data_manager.load_queries("generated")
        
        if not queries:
            show_error_panel(
                "No Generated Queries Found",
                "No queries available for review",
                ["Run qgen generate queries to create queries first", "If queries exist, try: qgen review queries", "Check if queries exist in data/queries/generated/"]
            )
            raise typer.Exit(1)
        
        # Launch review interface
        from qgen.cli.review import review_queries
        approved_queries = review_queries(queries)
        
        if not approved_queries:
            console.print("[yellow]⚠️  No queries were approved during review.[/yellow]")
            raise typer.Exit(0)
        
        # Save approved queries
        approved_path = data_manager.save_queries(
            approved_queries,
            "approved", 
            {
                "generated_count": len(queries),
                "approval_rate": len(approved_queries) / len(queries) if queries else 0
            }
        )
        
        # Show success summary
        show_generation_summary(
            "query",
            len(approved_queries),
            total_count=len(queries), 
            file_path=Path(approved_path),
            next_step="Run [cyan]qgen export[/cyan] to export final dataset"
        )
        
    except Exception as e:
        console.print(f"[red]❌ Failed to review queries: {str(e)}[/red]")
        raise typer.Exit(1)


if __name__ == "__main__":
    app()