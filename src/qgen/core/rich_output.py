"""Rich formatting utilities for beautiful CLI output."""

from typing import List, Optional, Dict, Any
from pathlib import Path
from rich.console import Console
from rich.panel import Panel
from rich.columns import Columns
from rich.text import Text
from rich.table import Table
from rich import box
from rich.padding import Padding

console = Console()


def create_panel(content: str, style: str = "info", title: str = "", emoji: str = "", 
                subtitle: str = "", padding: tuple = (0, 1)) -> Panel:
    """Create a formatted panel with specified style.
    
    Args:
        content: Panel content text
        style: Panel style - "success", "info", "action", "tip", "header", "error", "warning"
        title: Panel title (optional)
        emoji: Custom emoji (uses default for style if not provided)
        subtitle: Subtitle for header style panels
        padding: Panel padding tuple (vertical, horizontal)
    
    Returns:
        Rich Panel object
    """
    # Style configurations: (color, default_emoji, bold_style)
    styles = {
        "success": ("green", "✅", "bold green"),
        "info": ("blue", "📋", "bold blue"), 
        "action": ("yellow", "🎯", "bold yellow"),
        "tip": ("cyan", "💡", "bold cyan"),
        "header": ("magenta", "🚀", "bold magenta"),
        "error": ("red", "❌", "bold red"),
        "warning": ("yellow", "⚠️", "bold yellow")
    }
    
    color, default_emoji, title_style = styles.get(style, ("blue", "📋", "bold blue"))
    display_emoji = emoji or default_emoji
    
    # Special handling for header style
    if style == "header":
        panel_content = f"[bold]{content}[/bold]"
        if subtitle:
            panel_content += f"\n[dim]{subtitle}[/dim]"
        panel_padding = (1, 2)  # Headers get more padding
    else:
        panel_content = content
        panel_padding = padding
    
    # Create title with emoji if provided
    panel_title = f"[{title_style}]{display_emoji} {title}[/{title_style}]" if title else None
    
    return Panel(
        panel_content,
        title=panel_title,
        border_style=color,
        padding=panel_padding
    )


# Backward compatibility functions - these delegate to create_panel
def create_success_panel(title: str, content: str, emoji: str = "✅") -> Panel:
    """Create a success panel with green border."""
    return create_panel(content, "success", title, emoji)


def create_info_panel(title: str, content: str, emoji: str = "📋") -> Panel:
    """Create an info panel with blue border."""
    return create_panel(content, "info", title, emoji)


def create_action_panel(title: str, content: str, emoji: str = "🎯") -> Panel:
    """Create an action panel with yellow border."""
    return create_panel(content, "action", title, emoji)


def create_tip_panel(title: str, content: str, emoji: str = "💡") -> Panel:
    """Create a tip panel with cyan border."""
    return create_panel(content, "tip", title, emoji)


def create_header_panel(title: str, subtitle: str = "", emoji: str = "🚀") -> Panel:
    """Create a header panel with prominent styling."""
    return create_panel(title, "header", title, emoji, subtitle)


def format_file_path(path: Path, max_length: int = 60) -> str:
    """Format file path for display, truncating if too long."""
    path_str = str(path)
    if len(path_str) <= max_length:
        return f"[dim]{path_str}[/dim]"
    
    # Truncate from the middle
    start_len = max_length // 2 - 2
    end_len = max_length - start_len - 3
    return f"[dim]{path_str[:start_len]}...{path_str[-end_len:]}[/dim]"


def format_numbered_list(items: List[str], start: int = 1) -> str:
    """Format a numbered list with proper spacing."""
    formatted_items = []
    for i, item in enumerate(items, start):
        formatted_items.append(f"[bold]{i}.[/bold] {item}")
    return "\n".join(formatted_items)


def format_bullet_list(items: List[str], bullet: str = "•") -> str:
    """Format a bullet list with proper spacing."""
    formatted_items = []
    for item in items:
        formatted_items.append(f"[bold]{bullet}[/bold] {item}")
    return "\n".join(formatted_items)


def format_key_value_pairs(pairs: Dict[str, Any], separator: str = ": ") -> str:
    """Format key-value pairs for display."""
    formatted_pairs = []
    for key, value in pairs.items():
        formatted_pairs.append(f"[bold]{key}[/bold]{separator}[dim]{value}[/dim]")
    return "\n".join(formatted_pairs)


def show_project_init_success(project_path: Path, template_name: str, 
                              dimensions_count: int, examples_count: int) -> None:
    """Show beautifully formatted project initialization success message."""
    
    # Project info panel
    project_info = format_key_value_pairs({
        "Location": format_file_path(project_path, 70),
        "Template": template_name,
        "Dimensions": f"{dimensions_count} configured",
        "Examples": f"{examples_count} ready"
    })
    
    # Next steps panel
    next_steps = format_numbered_list([
        f"cd {project_path.name}",
        "qgen status                    [dim]# View project overview[/dim]", 
        "Review dimensions.yml          [dim]# Customize dimensions[/dim]",
        "qgen dimensions validate       [dim]# Check quality[/dim]"
    ])
    
    # Customization tips panel
    customization_tips = format_bullet_list([
        "[bold]dimensions.yml[/bold] - Define query dimensions",
        "[bold]prompts/[/bold] - Customize generation templates"
    ])
    
    # Help panel
    help_info = (
        "[bold]qgen --help[/bold]                [dim]# All commands[/dim]\n"
        "[bold]qgen dimensions examples[/bold]   [dim]# See examples[/dim]\n"
        "[bold]qgen <command> --help[/bold]      [dim]# Command help[/dim]"
    )
    
    # Display all panels
    console.print()
    console.print(create_success_panel("Project Created", project_info))
    console.print()
    console.print(create_action_panel("Next Steps", next_steps))
    console.print()
    console.print(create_tip_panel("Customization", customization_tips))
    console.print()
    console.print(create_info_panel("Need Help?", help_info))
    console.print()


def show_project_status(config: 'ProjectConfig', data_summary: Dict[str, Any], 
                       recommendations: List[str]) -> None:
    """Show beautifully formatted project status."""
    
    # Project overview panel
    overview = format_key_value_pairs({
        "Domain": config.domain,
        "Dimensions": len(config.dimensions),
        "Example Queries": len(config.example_queries)
    })
    
    # Data summary panel
    data_info = format_key_value_pairs({
        "Generated Tuples": data_summary.get('tuples_generated', 0),
        "Approved Tuples": data_summary.get('tuples_approved', 0),
        "Generated Queries": data_summary.get('queries_generated', 0),
        "Approved Queries": data_summary.get('queries_approved', 0)
    })
    
    # Display panels
    console.print()
    console.print(create_info_panel("Project Overview", overview))
    console.print()
    console.print(create_info_panel("Data Summary", data_info))
    
    if recommendations:
        console.print()
        rec_content = format_bullet_list(recommendations)
        console.print(create_action_panel("Recommendations", rec_content))
    
    console.print()


def show_generation_summary(stage: str, approved_count: int, total_count: Optional[int] = None, 
                          file_path: Optional[Path] = None, next_step: Optional[str] = None,
                          processing_time: Optional[float] = None) -> None:
    """Show beautifully formatted generation summary."""
    
    summary_info = format_key_value_pairs({
        "Approved": f"{approved_count} {stage}{'s' if approved_count != 1 else ''}"
    })
    
    if total_count and total_count != approved_count:
        approval_rate = (approved_count / total_count * 100) if total_count > 0 else 0
        summary_info += f"\n[bold]Total Reviewed[/bold]: [dim]{total_count}[/dim]"
        summary_info += f"\n[bold]Approval Rate[/bold]: [dim]{approval_rate:.1f}%[/dim]"
    
    if file_path:
        summary_info += f"\n[bold]Saved to[/bold]: {format_file_path(file_path, 60)}"
    
    if processing_time:
        summary_info += f"\n[bold]Time[/bold]: [dim]{processing_time:.1f}s[/dim]"
    
    console.print()
    console.print(create_success_panel(f"{stage.title()} Review Complete", summary_info))
    
    if next_step:
        console.print()
        console.print(create_action_panel("Next Step", next_step))
    
    console.print()


def show_export_summary(format_type: str, file_path: Path, query_count: int,
                       export_stats: Dict[str, Any]) -> None:
    """Show beautifully formatted export summary."""
    
    export_info = format_key_value_pairs({
        "Format": format_type.upper(),
        "File": format_file_path(file_path, 60),
        "Queries": query_count
    })
    
    if export_stats:
        # Build additional stats from the export summary
        additional_stats = {"Unique Tuples": export_stats.get('unique_tuples', 0)}
        
        # Add status distribution if available
        if 'status_distribution' in export_stats:
            status_dist = export_stats['status_distribution']
            for status, count in status_dist.items():
                additional_stats[f"{status.title()}"] = count
        
        if additional_stats:
            stats_info = format_key_value_pairs(additional_stats)
            export_info += f"\n\n{stats_info}"
    
    console.print()
    console.print(create_success_panel("Dataset Exported", export_info))
    console.print()


def show_error_panel(title: str, message: str, suggestions: Optional[List[str]] = None) -> None:
    """Show a formatted error panel with optional suggestions."""
    
    content = f"[red]{message}[/red]"
    
    if suggestions:
        content += "\n\n[bold]Suggestions:[/bold]\n"
        content += format_bullet_list(suggestions)
    
    console.print()
    console.print(create_panel(content, "error", title))
    console.print()


def show_validation_results(issues: List[str], suggestions: List[str]) -> None:
    """Show formatted dimension validation results."""
    
    if issues:
        issues_content = format_bullet_list(issues)
        console.print()
        console.print(Panel(
            issues_content,
            title="[bold red]⚠️  Validation Issues[/bold red]",
            border_style="red",
            padding=(0, 1)
        ))
    
    if suggestions:
        suggestions_content = format_bullet_list(suggestions)
        console.print()
        console.print(create_tip_panel("Quality Suggestions", suggestions_content))
    
    if not issues and not suggestions:
        console.print()
        console.print(create_success_panel(
            "Validation Complete", 
            "Your dimensions look great! ✨"
        ))
    
    console.print()


def show_generation_start(stage: str, count: int, provider: str) -> None:
    """Show formatted generation start message."""
    info_content = format_key_value_pairs({
        "Stage": stage.title(),
        "Count": f"{count} items",
        "Provider": provider,
        "Status": "Starting generation..."
    })
    
    console.print()
    console.print(create_info_panel(f"🚀 {stage.title()} Generation", info_content))
    console.print()


def show_tuples_found(count: int, file_path: str) -> None:
    """Show formatted message for found tuples."""
    info_content = format_key_value_pairs({
        "Found": f"{count} approved tuples",
        "Source": file_path
    })
    
    console.print()
    console.print(create_info_panel("📊 Input Data", info_content))


def show_prompt_customization_offer() -> None:
    """Show prompt customization guidance panel."""
    content = (
        "📝 You can edit [cyan]prompts/query_generation.txt[/cyan] to:\n\n"
        "[bold]Benefits:[/bold]\n"
        "• Add domain-specific examples\n"
        "• Adjust tone and style for your use case\n"
        "• Control how queries are created from tuples\n"
        "• Improve generation quality\n\n"
        "[bold]🔄 Customize prompts first?[/bold] [dim](y/N)[/dim]"
    )
    
    console.print()
    console.print(create_tip_panel("Prompt Customization", content))


def show_file_edit_instruction(file_path: str) -> None:
    """Show file editing instruction panel."""
    content = f"📁 Edit this file in your preferred editor:\n\n[yellow]{file_path}[/yellow]\n\n📋 Press Enter when you're ready to continue..."
    
    console.print()
    console.print(create_action_panel("📝 Edit Prompt", content))


def show_review_start(item_type: str, count: int) -> None:
    """Show formatted review start message."""
    content = (
        f"Review and approve each {item_type} individually.\n\n"
        "[bold]Available actions (single letter shortcuts):[/bold]\n"
        "• [green][bold]A[/bold]pprove[/green] / [green][bold]a[/bold][/green] - Accept the item\n"
        "• [red][bold]R[/bold]eject[/red] / [red][bold]r[/bold][/red] - Decline the item\n"
        "• [yellow][bold]E[/bold]dit[/yellow] / [yellow][bold]e[/bold][/yellow] - Modify the item\n"
        "• [cyan][bold]S[/bold]kip[/cyan] / [cyan][bold]s[/bold][/cyan] - Skip for now\n"
        "• [dim][bold]Q[/bold]uit[/dim] / [dim][bold]q[/bold][/dim] - Exit review"
    )
    
    console.print()
    console.print(create_action_panel(f"🔍 Review {count} {item_type.title()}s", content))
    console.print()


def show_review_summary(item_type: str, total: int, approved: int, rejected: int) -> None:
    """Show formatted review completion summary."""
    approval_rate = (approved / total * 100) if total > 0 else 0
    
    content = format_key_value_pairs({
        "Total Reviewed": total,
        "Approved": f"{approved} ({approval_rate:.1f}%)",
        "Rejected": rejected,
        "Approval Rate": f"{approval_rate:.1f}%"
    })
    
    if approval_rate >= 80:
        panel_func = create_success_panel
        emoji = "✅"
    elif approval_rate >= 60:
        panel_func = create_action_panel  
        emoji = "⚠️"
    else:
        panel_func = Panel
        emoji = "❌"
        
    console.print()
    console.print(panel_func(f"{emoji} Review Complete", content))
    console.print()


def show_no_items_generated(item_type: str) -> None:
    """Show error panel when no items are generated."""
    suggestions = [
        "Check your configuration and try again",
        f"Try customizing [yellow]prompts/{item_type}_generation.txt[/yellow] for better results",
        "Run [cyan]qgen dimensions examples[/cyan] to see working examples",
        "Verify your LLM provider is properly configured"
    ]
    
    show_error_panel(
        f"No {item_type.title()}s Generated",
        f"The generation process completed but no {item_type}s were created.",
        suggestions
    )