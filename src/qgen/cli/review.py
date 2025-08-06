"""Simple review interface for tuples and queries."""

from typing import List, Optional
from rich.console import Console
from rich.table import Table
from rich.prompt import Confirm, Prompt
from rich.panel import Panel

from qgen.core.models import Tuple, Query
from qgen.core.rich_output import show_review_start, show_review_summary

console = Console()


def review_tuples(tuples: List[Tuple]) -> List[Tuple]:
    """Simple CLI interface to review and approve tuples."""
    if not tuples:
        console.print("[yellow]No tuples to review.[/yellow]")
        return []
    
    show_review_start("tuple", len(tuples))
    
    approved_tuples = []
    rejected_count = 0
    
    for i, tuple_obj in enumerate(tuples):
        console.print(f"\n[bold]Tuple {i+1}/{len(tuples)}:[/bold]")
        
        # Display tuple in a table
        table = Table(show_header=True, header_style="bold magenta")
        table.add_column("Dimension", style="cyan")
        table.add_column("Value", style="green")
        
        for dim_name, value in tuple_obj.values.items():
            table.add_row(dim_name, value)
        
        console.print(table)
        
        # Get user decision
        while True:
            choice = Prompt.ask(
                "\n[bold]Action[/bold] ([green]a[/green]pprove/[red]r[/red]eject/[yellow]e[/yellow]dit/[cyan]s[/cyan]kip/[dim]q[/dim]uit)",
                default="a"
            ).lower()
            
            # Normalize single letter shortcuts
            if choice in ["approve", "a"]:
                approved_tuples.append(tuple_obj)
                console.print("[green]✅ Approved[/green]")
                break
            elif choice in ["reject", "r"]:
                rejected_count += 1
                console.print("[red]❌ Rejected[/red]")
                break
            elif choice in ["edit", "e"]:
                edited_tuple = edit_tuple(tuple_obj)
                if edited_tuple:
                    approved_tuples.append(edited_tuple)
                    console.print("[green]✅ Edited and approved[/green]")
                else:
                    console.print("[yellow]⚠️  Edit cancelled[/yellow]")
                break
            elif choice in ["skip", "s"]:
                console.print("[yellow]⏩ Skipped[/yellow]")
                break
            elif choice in ["quit", "q"]:
                console.print(f"\n[blue]Review stopped. {len(approved_tuples)} tuples approved so far.[/blue]")
                return approved_tuples
    
    show_review_summary("tuple", len(tuples), len(approved_tuples), rejected_count)
    return approved_tuples


def edit_tuple(tuple_obj: Tuple) -> Optional[Tuple]:
    """Allow user to edit a tuple."""
    console.print("\n[bold blue]Editing tuple:[/bold blue]")
    
    new_values = {}
    
    for dim_name, current_value in tuple_obj.values.items():
        new_value = Prompt.ask(
            f"{dim_name}",
            default=current_value
        )
        new_values[dim_name] = new_value
    
    # Confirm the edit
    console.print("\n[bold]New tuple:[/bold]")
    table = Table(show_header=True, header_style="bold magenta")
    table.add_column("Dimension", style="cyan")
    table.add_column("Value", style="green")
    
    for dim_name, value in new_values.items():
        table.add_row(dim_name, value)
    
    console.print(table)
    
    if Confirm.ask("Save these changes?"):
        return Tuple(values=new_values)
    else:
        return None


def review_queries(queries: List[Query]) -> List[Query]:
    """Simple CLI interface to review and approve queries."""
    if not queries:
        console.print("[yellow]No queries to review.[/yellow]")
        return []
    
    show_review_start("query", len(queries))
    
    approved_queries = []
    rejected_count = 0
    
    for i, query in enumerate(queries):
        console.print(f"\n[bold]Query {i+1}/{len(queries)}:[/bold]")
        
        # Display source tuple
        console.print("[dim]Source tuple:[/dim]")
        tuple_info = ", ".join([f"{k}: {v}" for k, v in query.tuple_data.values.items()])
        console.print(f"[dim]{tuple_info}[/dim]")
        
        # Display query
        query_panel = Panel(
            query.generated_text,
            title="Generated Query",
            title_align="left",
            border_style="blue"
        )
        console.print(query_panel)
        
        # Get user decision
        while True:
            choice = Prompt.ask(
                "\n[bold]Action[/bold] ([green]a[/green]pprove/[red]r[/red]eject/[yellow]e[/yellow]dit/[cyan]s[/cyan]kip/[dim]q[/dim]uit)",
                default="a"
            ).lower()
            
            # Normalize single letter shortcuts
            if choice in ["approve", "a"]:
                query.status = "approved"
                approved_queries.append(query)
                console.print("[green]✅ Approved[/green]")
                break
            elif choice in ["reject", "r"]:
                query.status = "rejected"
                rejected_count += 1
                console.print("[red]❌ Rejected[/red]")
                break
            elif choice in ["edit", "e"]:
                edited_query = edit_query(query)
                if edited_query:
                    edited_query.status = "approved"
                    approved_queries.append(edited_query)
                    console.print("[green]✅ Edited and approved[/green]")
                else:
                    console.print("[yellow]⚠️  Edit cancelled[/yellow]")
                break
            elif choice in ["skip", "s"]:
                query.status = "skipped"
                console.print("[yellow]⏩ Skipped[/yellow]")
                break
            elif choice in ["quit", "q"]:
                console.print(f"\n[blue]Review stopped. {len(approved_queries)} queries approved so far.[/blue]")
                return approved_queries
    
    show_review_summary("query", len(queries), len(approved_queries), rejected_count)
    return approved_queries


def edit_query(query: Query) -> Optional[Query]:
    """Allow user to edit a query."""
    console.print(f"\n[bold blue]Editing query:[/bold blue]")
    console.print(f"[dim]Current: {query.generated_text}[/dim]")
    
    new_text = Prompt.ask(
        "New query text",
        default=query.generated_text
    )
    
    if new_text != query.generated_text:
        # Create new query with updated text
        new_query = Query(
            tuple_data=query.tuple_data,
            generated_text=new_text,
            status="pending"  # Will be set to approved by caller
        )
        return new_query
    else:
        return query


def quick_review_summary(tuples: List[Tuple], queries: List[Query]) -> None:
    """Display a quick summary of tuples and queries for review."""
    console.print("\n[bold blue]Generated Content Summary[/bold blue]")
    
    if tuples:
        console.print(f"\n[bold]📊 {len(tuples)} Tuples Generated:[/bold]")
        for i, tuple_obj in enumerate(tuples[:5]):  # Show first 5
            tuple_desc = ", ".join([f"{k}: {v}" for k, v in tuple_obj.values.items()])
            console.print(f"  {i+1}. {tuple_desc}")
        
        if len(tuples) > 5:
            console.print(f"  ... and {len(tuples) - 5} more")
    
    if queries:
        console.print(f"\n[bold]💬 {len(queries)} Queries Generated:[/bold]")
        for i, query in enumerate(queries[:3]):  # Show first 3
            console.print(f"  {i+1}. {query.generated_text[:80]}...")
        
        if len(queries) > 3:
            console.print(f"  ... and {len(queries) - 3} more")
    
    console.print()