"""CLI entry point for the Query Generation Tool."""

import typer
from pathlib import Path
from rich.console import Console
from typing import Optional

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

app.add_typer(dimensions_app, name="dimensions")
app.add_typer(generate_app, name="generate")


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
        console.print(f"[red]❌ Directory '{project_name}' already exists[/red]")
        raise typer.Exit(1)
    
    # Validate template
    available_domains = list_available_domains()
    if template not in available_domains:
        console.print(f"[red]❌ Unknown template: {template}[/red]")
        console.print(f"Available templates: {', '.join(available_domains)}")
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

        console.print("📁 Created project directory structure")

        # Create prompts directory and copy templates
        prompts_dir = project_path / "prompts"
        prompts_dir.mkdir()
        
        # Copy prompt templates from the package
        package_prompts_dir = Path(__file__).parent.parent / "prompts"
        if package_prompts_dir.exists():
            import shutil
            for template_file in package_prompts_dir.glob("*.txt"):
                shutil.copy2(template_file, prompts_dir / template_file.name)
            console.print(f"📝 Copied {len(list(package_prompts_dir.glob('*.txt')))} prompt templates")
        else:
            console.print("[yellow]⚠️  Prompt templates not found in package[/yellow]")
        
        console.print(f"✅ Project '{project_name}' created successfully!")
        console.print(f"📁 Location: {project_path.absolute()}")
        console.print(f"📋 Template: {template_data['name']}")
        console.print(f"🔧 Dimensions: {len(dimensions)}")
        console.print(f"💡 Example queries: {len(template_data['example_queries'])}")
        
        console.print("\n[bold green]🎯 Next steps:[/bold green]")
        console.print(f"1. [cyan]cd {project_name}[/cyan]")
        console.print("2. [cyan]qgen status[/cyan] - See project overview and recommendations")
        console.print("3. Review and customize [yellow]dimensions.yml[/yellow]")
        console.print("4. [cyan]qgen dimensions validate[/cyan] - Sanitize your dimensions")

        console.print("\n[bold yellow]💡 Customization Tips:[/bold yellow]")
        console.print("📝 Edit these files in your preferred editor:")
        console.print(f"   • [yellow]dimensions.yml[/yellow] - Define query dimensions")
        console.print(f"   • [yellow]prompts/tuple_generation.txt[/yellow] - Customize tuple creation")
        console.print(f"   • [yellow]prompts/query_generation.txt[/yellow] - Customize query generation")
        
        console.print("\n[bold blue]🔍 Need help?[/bold blue]")
        console.print("   • [green]qgen --help[/green] - See all commands")
        console.print("   • [green]qgen dimensions examples[/green] - See dimension examples")
        console.print("   • [green]qgen <command> --help[/green] - Command-specific help")
        
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
    console.print("🔍 Validating dimensions...")
    
    # Validate we're in a project directory
    if not Path("dimensions.yml").exists():
        console.print("[red]❌ Not in a project directory (no dimensions.yml found)[/red]")
        console.print("💡 Run [green]qgen init <project_name>[/green] to create a new project")
        console.print("🔍 Need help? Run [green]qgen --help[/green] for all commands")
        raise typer.Exit(1)
    
    try:
        # Load and validate project
        config = load_project_config(".")
        
        # Basic validation
        basic_issues = validate_dimensions(config.dimensions)
        
        # Quality suggestions
        quality_suggestions = validate_dimension_quality(config.dimensions)
        
        # Display results
        console.print(f"📊 Found {len(config.dimensions)} dimensions")
        console.print(f"💡 Found {len(config.example_queries)} example queries")
        
        if basic_issues:
            console.print("\n[red]❌ Validation Issues:[/red]")
            for issue in basic_issues:
                console.print(f"  • {issue}")
            
            # Add specific guidance for common issues
            if any("No dimensions defined" in issue for issue in basic_issues):
                console.print("\n[bold yellow]💡 Getting started with dimensions:[/bold yellow]")
                console.print("   • Run [cyan]qgen dimensions examples[/cyan] to see examples from different domains")
                console.print("   • Run [cyan]qgen dimensions guide[/cyan] for dimension design principles")
        else:
            console.print("\n✅ All dimensions pass basic validation")
        
        if quality_suggestions:
            console.print("\n[yellow]💡 Quality Suggestions:[/yellow]")
            for suggestion in quality_suggestions:
                console.print(f"  • {suggestion}")
        
        # Overall status
        if not basic_issues and not quality_suggestions:
            console.print("\n🎉 Dimensions look great! Ready for generation.")
            console.print("\n[bold green]🎯 Next Steps:[/bold green]")
            console.print("1. [cyan]qgen generate tuples[/cyan] - Create dimension combinations")
            console.print("2. Consider customizing [yellow]prompts/[/yellow] files first for better results")
            console.print("3. Run [green]qgen --help[/green] to see all available commands")
        elif not basic_issues:
            console.print("\n✅ Dimensions are valid but could be improved")
            console.print("💡 Consider the suggestions above, then run [cyan]qgen generate tuples[/cyan]")
        else:
            console.print("\n❌ Please fix validation issues before proceeding")
            console.print("🔍 Need help? Run [green]qgen dimensions examples[/green] for inspiration")
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
    provider: Optional[str] = typer.Option(None, help="LLM provider: openai or azure (auto-detect if not specified)"),
    skip_guidance: bool = typer.Option(False, help="Skip interactive prompt customization guidance")
):
    """Generate tuple combinations from dimensions."""
    console.print(f"🎲 Generating {count} tuples...")
    
    # Load environment variables
    ensure_environment_loaded(verbose=True)
    
    # Auto-detect provider if not specified
    if provider is None:
        provider = auto_detect_provider()
        if provider is None:
            console.print("[red]❌ No LLM provider configuration found in environment[/red]")
            console.print("💡 Please set either OpenAI or Azure OpenAI environment variables in .env file")
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
        # Load project configuration
        config = load_project_config(".")
        
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
            console.print("\n[bold blue]💡 Customize prompts for better results?[/bold blue]")
            console.print("📝 You can edit [cyan]prompts/tuple_generation.txt[/cyan] to:")
            console.print("   • Tailor the prompt style to your domain")
            console.print("   • Add specific examples and requirements")
            console.print("   • Control how dimension combinations are created")
            
            # Ask user if they want to customize first
            try:
                user_input = input("\n🔄 Customize prompts first? [y/N]: ").strip().lower()
                if user_input in ['y', 'yes']:
                    console.print(f"\n📁 Edit this file in your preferred editor:")
                    console.print(f"   [yellow]prompts/tuple_generation.txt[/yellow]")
                    input("📋 Press Enter when you're ready to continue...")
                console.print("")
            except (EOFError, KeyboardInterrupt):
                console.print("\n🚀 Continuing with generation...")
        
        # Generate tuples
        tuples = core_generate_tuples(config, count, provider)
        
        if not tuples:
            console.print("[red]❌ No tuples generated. Check your configuration and try again.[/red]")
            console.print("💡 Try customizing [yellow]prompts/tuple_generation.txt[/yellow] for better results")
            console.print("🔍 Run [green]qgen dimensions examples[/green] to see working examples")
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
        
        console.print(f"\n✅ Saved data to organized structure:")
        console.print(f"   📊 Generated: {len(tuples)} tuples → {generated_path}")
        console.print(f"   ✅ Approved: {len(approved_tuples)} tuples → {approved_path}")
        if output != "data/tuples/generated.json":
            console.print(f"   📄 Output: {output}")
        console.print(f"🎯 Next step: Run 'qgen generate queries' to generate queries from approved tuples")
        
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
    provider: Optional[str] = typer.Option(None, help="LLM provider: openai or azure (auto-detect if not specified)"),
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
            console.print("💡 Please set either OpenAI or Azure OpenAI environment variables in .env file")
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
            console.print("Run 'qgen generate tuples' first to create tuples")
            raise typer.Exit(1)
        
        # Load project configuration
        config = load_project_config(".")
        
        # Use DataManager to load approved tuples
        data_manager = get_data_manager(".")
        tuples = data_manager.load_tuples("approved")
        
        if not tuples:
            console.print(f"[red]❌ No approved tuples found in {input_file}[/red]")
            console.print("Run 'qgen generate tuples' first to create tuples")
            raise typer.Exit(1)
        
        console.print(f"📊 Found {len(tuples)} approved tuples")
        
        # Interactive prompt customization guidance (unless skipped)
        if not skip_guidance:
            console.print("\n[bold blue]💡 Customize prompts for better results?[/bold blue]")
            console.print("📝 You can edit [cyan]prompts/query_generation.txt[/cyan] to:")
            console.print("   • Add domain-specific examples")
            console.print("   • Adjust tone and style for your use case")
            console.print("   • Control how queries are created from tuples")
            
            # Ask user if they want to customize first
            try:
                user_input = input("\n🔄 Customize prompts first? [y/N]: ").strip().lower()
                if user_input in ['y', 'yes']:
                    console.print(f"\n📁 Edit this file in your preferred editor:")
                    console.print(f"   [yellow]prompts/query_generation.txt[/yellow]")
                    input("📋 Press Enter when you're ready to continue...")
                console.print("")
            except (EOFError, KeyboardInterrupt):
                console.print("\n🚀 Continuing with generation...")
        
        # Generate queries using the core generation function
        from qgen.core.generation import generate_queries as core_generate_queries
        queries = core_generate_queries(config, tuples, queries_per_tuple, provider)
        
        if not queries:
            console.print("[red]❌ No queries generated. Check your configuration and try again.[/red]")
            console.print("💡 Try customizing [yellow]prompts/query_generation.txt[/yellow] for better results")
            console.print("🔍 Run [green]qgen dimensions examples[/green] to see working examples")
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
        
        console.print(f"\n✅ Saved queries to organized structure:")
        console.print(f"   🔄 Generated: {len(queries)} queries → {generated_path}")
        console.print(f"   ✅ Approved: {len(approved_queries)} queries → {approved_path}")
        console.print(f"🎯 Next step: Run 'qgen export' to create final dataset")
        
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
    console.print(f"📊 Exporting {stage} queries in {format} format...")
    
    # Validate we're in a project directory
    if not Path("dimensions.yml").exists():
        console.print("[red]❌ Not in a project directory (no dimensions.yml found)[/red]")
        console.print("💡 Run [green]qgen init <project_name>[/green] to create a new project")
        console.print("🔍 Need help? Run [green]qgen --help[/green] for all commands")
        raise typer.Exit(1)
    
    try:
        from qgen.core.export import export_dataset, get_export_summary
        from qgen.core.data import get_data_manager
        
        # Validate format
        if format not in ["csv", "json"]:
            console.print(f"[red]❌ Unsupported format: {format}[/red]")
            console.print("Supported formats: csv, json")
            raise typer.Exit(1)
        
        # Validate stage
        if stage not in ["approved", "generated"]:
            console.print(f"[red]❌ Unsupported stage: {stage}[/red]")
            console.print("Supported stages: approved, generated")
            raise typer.Exit(1)
        
        # Check if queries exist for the specified stage
        data_manager = get_data_manager(".")
        queries = data_manager.load_queries(stage)
        
        if not queries:
            console.print(f"[red]❌ No {stage} queries found to export[/red]")
            if stage == "approved":
                console.print("💡 Run [cyan]qgen generate queries[/cyan] first to create queries")
                console.print("🔍 Need help? Run [green]qgen --help[/green] to see the workflow")
            raise typer.Exit(1)
        
        # Show summary if requested
        if show_summary:
            summary = get_export_summary(queries)
            console.print(f"\n[bold blue]📈 Export Summary[/bold blue]")
            console.print(f"Total queries: {summary['total_queries']}")
            console.print(f"Unique tuples: {summary['unique_tuples']}")
            
            if summary.get('status_distribution'):
                console.print("\nStatus distribution:")
                for status, count in summary['status_distribution'].items():
                    console.print(f"  {status}: {count}")
        
        # Export the dataset
        exported_path = export_dataset(".", format, output, stage)
        
        console.print(f"\n✅ Successfully exported to: {exported_path}")
        console.print(f"📊 Format: {format.upper()}")
        console.print(f"🎯 Stage: {stage}")
        console.print(f"📄 Queries: {len(queries)}")
        
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
        console.print("[red]❌ Not in a project directory (no dimensions.yml found)[/red]")
        console.print("💡 Run [green]qgen init <project_name>[/green] to create a new project")
        console.print("🔍 Need help? Run [green]qgen --help[/green] for all commands")
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
        
        console.print("\n[bold blue]📊 Project Status[/bold blue]")
        console.print(f"🔧 Dimensions: {len(config.dimensions)}")
        console.print(f"💡 Example queries: {len(config.example_queries)}")
        console.print(f"🤖 LLM providers: {', '.join(available_providers) if available_providers else 'None configured'}")
        if auto_provider:
            console.print(f"🎯 Auto-detected: {auto_provider}")
        
        console.print("\n[bold blue]📁 Data Organization[/bold blue]")
        
        # Tuples status
        tuples_status = project_status.get("tuples", {})
        if tuples_status:
            console.print("📊 Tuples:")
            for stage, info in tuples_status.items():
                if isinstance(info, dict) and "count" in info:
                    console.print(f"   {stage}: {info['count']} items")
        else:
            console.print("📊 Tuples: No data yet")
        
        # Queries status  
        queries_status = project_status.get("queries", {})
        if queries_status:
            console.print("💬 Queries:")
            for stage, info in queries_status.items():
                if isinstance(info, dict) and "count" in info:
                    console.print(f"   {stage}: {info['count']} items")
        else:
            console.print("💬 Queries: No data yet")
        
        # Exports status
        exports_status = project_status.get("exports", {})
        if exports_status and exports_status.get("files", 0) > 0:
            console.print(f"📤 Exports: {exports_status['files']} files")
        else:
            console.print("📤 Exports: No data yet")
        
        console.print("\n[bold green]🎯 Next Steps:[/bold green]")
        if not tuples_status:
            console.print("1. Generate tuples: qgen generate tuples")
        elif not queries_status:
            console.print("1. Generate queries: qgen generate queries")
        elif not exports_status or exports_status.get("files", 0) == 0:
            console.print("1. Export dataset: qgen export")
        else:
            console.print("✅ Project workflow complete!")
        
        # Add recommendations section
        console.print("\n[bold yellow]💡 Recommendations:[/bold yellow]")
        console.print("📝 Customize prompts for better results:")
        console.print(f"   • [cyan]prompts/tuple_generation.txt[/cyan] - Controls dimension combinations")
        console.print(f"   • [cyan]prompts/query_generation.txt[/cyan] - Controls query generation")
        console.print("🔍 Need help?")
        console.print("   • Run [green]qgen --help[/green] to see all commands")
        console.print("   • Run [green]qgen <command> --help[/green] for command-specific help")
        console.print("   • Check [green]qgen dimensions examples[/green] for inspiration")
            
    except Exception as e:
        console.print(f"[red]❌ Error checking project status: {str(e)}[/red]")
        raise typer.Exit(1)


if __name__ == "__main__":
    app()