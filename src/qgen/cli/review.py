"""Simple review interface for tuples and queries."""

from typing import List, Optional, Dict
from datetime import datetime
from rich.console import Console
from rich.table import Table
from rich.prompt import Confirm, Prompt
from rich.panel import Panel

from qgen.core.models import Tuple, Query
from qgen.core.rag_models import ExtractedFact, RAGQuery, ChunkData
from qgen.core.rich_output import show_review_start, show_review_summary
from qgen.core.chunk_processing import ChunkProcessor

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


def review_facts(facts: List[ExtractedFact]) -> List[ExtractedFact]:
    """Simple CLI interface to review and approve extracted facts."""
    if not facts:
        console.print("[yellow]No facts to review.[/yellow]")
        return []
    
    show_review_start("fact", len(facts))
    
    # Load chunks for context
    chunks_dict = {}
    try:
        from pathlib import Path
        chunks_dir = Path("chunks")
        if chunks_dir.exists():
            processor = ChunkProcessor()
            chunks = processor.load_chunks_from_directory(chunks_dir)
            chunks_dict = {chunk.chunk_id: chunk for chunk in chunks}
            console.print(f"[dim]✅ Loaded {len(chunks)} chunks for context[/dim]")
    except Exception as e:
        console.print(f"[dim]⚠️  Could not load chunks for context: {e}[/dim]")
    
    approved_facts = []
    rejected_count = 0
    
    for i, fact in enumerate(facts):
        console.print(f"\n[bold]Fact {i+1}/{len(facts)}:[/bold]")
        
        # Display fact details in a panel
        fact_content = f"""[bold cyan]Chunk ID:[/bold cyan] {fact.chunk_id}
[bold green]Extracted Fact:[/bold green] {fact.fact_text}
[bold yellow]Confidence:[/bold yellow] {fact.extraction_confidence:.2f}
[bold blue]Reasoning:[/bold blue] {getattr(fact, 'reasoning', 'N/A')}"""
        
        fact_panel = Panel(
            fact_content,
            title=f"Fact {fact.fact_id[:8]}...",  # Show only first 8 chars of UUID
            border_style="bright_blue",
            padding=(1, 2)
        )
        console.print(fact_panel)
        
        # Show chunk context with highlighting
        chunk = chunks_dict.get(fact.chunk_id)
        if chunk:
            console.print(f"\n[bold]📄 Chunk Context:[/bold]")
            
            # Get highlighted chunk text using embedding-based similarity
            highlighted_text = fact.get_chunk_with_highlight(chunk.text)
            
            # Display chunk with highlighting in a panel
            chunk_panel = Panel(
                highlighted_text,
                title=f"Source: {chunk.source_document or 'Unknown'}",
                border_style="dim",
                padding=(1, 2)
            )
            console.print(chunk_panel)
            
            # Show span information if available
            if fact.span and fact.span.start is not None:
                console.print(f"[dim]📍 Span: characters {fact.span.start}-{fact.span.end}[/dim]")
        else:
            console.print(f"[dim]⚠️  Chunk context not available for {fact.chunk_id}[/dim]")
        
        # Get user decision
        while True:
            choice = Prompt.ask(
                "\n[bold]Action[/bold] ([green]a[/green]pprove/[red]r[/red]eject/[yellow]e[/yellow]dit/[cyan]s[/cyan]kip/[dim]q[/dim]uit)",
                default="a"
            ).lower()
            
            if choice in ["approve", "a"]:
                approved_facts.append(fact)
                console.print("[green]✅ Approved[/green]")
                break
            elif choice in ["reject", "r"]:
                rejected_count += 1
                console.print("[red]❌ Rejected[/red]")
                break
            elif choice in ["edit", "e"]:
                edited_fact = edit_fact(fact)
                if edited_fact:
                    approved_facts.append(edited_fact)
                    console.print("[green]✅ Edited and approved[/green]")
                else:
                    console.print("[yellow]⚠️  Edit cancelled[/yellow]")
                break
            elif choice in ["skip", "s"]:
                console.print("[yellow]⏩ Skipped[/yellow]")
                break
            elif choice in ["quit", "q"]:
                console.print(f"\n[blue]Review stopped. {len(approved_facts)} facts approved so far.[/blue]")
                return approved_facts
            else:
                console.print("[red]Invalid choice. Please use a/r/e/s/q[/red]")
    
    show_review_summary("fact", len(facts), len(approved_facts), rejected_count)
    return approved_facts


def edit_fact(fact: ExtractedFact) -> Optional[ExtractedFact]:
    """Allow user to edit an extracted fact."""
    console.print(f"\n[bold blue]Editing fact:[/bold blue]")
    console.print(f"[dim]Current: {fact.fact_text}[/dim]")
    
    new_fact_text = Prompt.ask(
        "New fact text",
        default=fact.fact_text
    )
    
    if new_fact_text != fact.fact_text:
        # Update fact with new text
        fact.fact_text = new_fact_text
        
        # Ask for new confidence if text changed significantly
        if len(new_fact_text) != len(fact.fact_text):
            try:
                new_confidence = float(Prompt.ask(
                    "New confidence (0.0-1.0)",
                    default=str(fact.extraction_confidence)
                ))
                if 0.0 <= new_confidence <= 1.0:
                    fact.extraction_confidence = new_confidence
            except ValueError:
                pass  # Keep original confidence if invalid input
        
        return fact
    else:
        return fact


def review_queries(queries: List[RAGQuery], chunks_map: Dict[str, ChunkData]) -> List[RAGQuery]:
    """Review and approve RAG queries with interactive CLI interface."""
    
    if not queries:
        console.print("[yellow]No queries to review.[/yellow]")
        return []
    
    console.print(f"\n[bold blue]📝 RAG Query Review Interface[/bold blue]")
    console.print(f"[dim]Reviewing {len(queries)} generated queries[/dim]")
    console.print("[dim]Commands: [bold](a)[/bold]pprove, [bold](r)[/bold]eject, [bold](e)[/bold]dit, [bold](s)[/bold]kip, [bold](q)[/bold]uit[/dim]\n")
    
    # Load original facts for multi-hop highlighting
    facts_map = {}
    try:
        from qgen.core.rag_generation import FactDataManager
        fact_manager = FactDataManager()
        approved_facts = fact_manager.load_facts("approved")
        facts_map = {fact.chunk_id: fact for fact in approved_facts}
        console.print(f"[dim]✅ Loaded {len(facts_map)} facts for enhanced highlighting[/dim]")
    except Exception as e:
        console.print(f"[dim]⚠️  Could not load facts for highlighting: {e}[/dim]")
    
    approved_queries = []
    
    for i, query in enumerate(queries, 1):
        # Display query information
        console.print(f"Query {i}/{len(queries)}:")
        
        # Main query panel
        query_panel = Panel(
            f"Query ID: {query.query_id[:12]}...\n"
            f"Query: {query.query_text}\n"
            f"Answer Fact: {query.answer_fact}\n" +
            (f"Difficulty: {query.difficulty}\n" if query.difficulty else "") +
            (f"Realism Score: {query.realism_score:.2f}\n" if hasattr(query, 'realism_score') and query.realism_score else "") +
            (f"Source Fact ID: {query.source_fact_id}\n" if hasattr(query, 'source_fact_id') and query.source_fact_id else "") +
            (f"Reasoning: {query.reasoning}" if hasattr(query, 'reasoning') and query.reasoning else ""),
            title=f"Query {query.query_id[:8]}...",
            border_style="blue",
            padding=(1, 2)
        )
        console.print(query_panel)
        
        # Show source chunk context with highlighting if available
        if query.source_chunk_ids:
            # Display header based on number of chunks
            if len(query.source_chunk_ids) == 1:
                console.print("📄 Source Chunk Context:")
            else:
                console.print(f"📄 Source Chunks Context ({len(query.source_chunk_ids)} chunks):")
            
            # Show all chunks for multi-hop queries
            for chunk_idx, chunk_id in enumerate(query.source_chunk_ids, 1):
                chunk = chunks_map.get(chunk_id)
                if chunk:
                    # Use cached embeddings to highlight relevant text based on original fact
                    try:
                        from qgen.core.rag_models import ExtractedFact
                        
                        # Try to use original fact for this chunk, fallback to answer fact
                        original_fact = facts_map.get(chunk_id)
                        if original_fact:
                            # Use the original extracted fact for this specific chunk
                            highlighting_fact = original_fact
                            highlight_source = "original fact"
                        else:
                            # Fallback: create temporary fact using answer fact
                            highlighting_fact = ExtractedFact(
                                fact_text=query.answer_fact,
                                chunk_id=chunk_id,
                                extraction_confidence=1.0
                            )
                            highlight_source = "answer fact"
                        
                        # Get highlighted text using the appropriate fact
                        highlighted_text = highlighting_fact.get_chunk_with_highlight(chunk.text)
                        
                        # For multi-hop, show chunk number in title
                        title_suffix = ""
                        if len(query.source_chunk_ids) > 1:
                            title_suffix = f" (Chunk {chunk_idx}/{len(query.source_chunk_ids)})"
                        
                        chunk_panel = Panel(
                            highlighted_text,
                            title=f"Source: {chunk.source_document or 'Unknown'}{title_suffix} (highlighting: {highlight_source})",
                            border_style="dim",
                            padding=(1, 2)
                        )
                        console.print(chunk_panel)
                        
                    except Exception as e:
                        # Fallback to plain text if highlighting fails
                        title_suffix = ""
                        if len(query.source_chunk_ids) > 1:
                            title_suffix = f" (Chunk {chunk_idx}/{len(query.source_chunk_ids)})"
                        
                        chunk_panel = Panel(
                            chunk.text,
                            title=f"Source: {chunk.source_document or 'Unknown'}{title_suffix} (highlighting failed: {str(e)[:50]}...)",
                            border_style="dim",
                            padding=(1, 2)
                        )
                        console.print(chunk_panel)
                else:
                    console.print(f"[red]⚠️  Chunk {chunk_id} not found in chunks map[/red]")
            
            # For multi-hop queries, show additional info
            if len(query.source_chunk_ids) > 1:
                multihop_info = f"[dim]🔗 Multi-hop query requiring {len(query.source_chunk_ids)} chunks to answer completely[/dim]"
                console.print(multihop_info)
        
        # Get user decision
        while True:
            try:
                choice = Prompt.ask(
                    "\n[bold]Action[/bold] ([green]a[/green]pprove/[red]r[/red]eject/[yellow]e[/yellow]dit/[cyan]s[/cyan]kip/[dim]q[/dim]uit)",
                    default="a"
                ).lower()
                
                if choice in ["approve", "a"]:
                    approved_queries.append(query)
                    console.print("[green]✅ Approved[/green]")
                    break
                elif choice in ["reject", "r"]:
                    console.print("[red]❌ Rejected[/red]")
                    break
                elif choice in ["edit", "e"]:
                    edited_query = edit_query(query)
                    if edited_query:
                        approved_queries.append(edited_query)
                        console.print("[green]✅ Edited and approved[/green]")
                    else:
                        console.print("[yellow]⚠️  Edit cancelled[/yellow]")
                    break
                elif choice in ["skip", "s"]:
                    console.print("[yellow]⏩ Skipped[/yellow]")
                    break
                elif choice in ["quit", "q"]:
                    console.print(f"\n[blue]Review stopped. {len(approved_queries)} queries approved so far.[/blue]")
                    return approved_queries
                else:
                    console.print("[red]Invalid choice. Please use a/r/e/s/q[/red]")
                    # Continue if they don't confirm quit
                    
            except KeyboardInterrupt:
                console.print(f"\n[yellow]Review interrupted. Approved {len(approved_queries)} queries.[/yellow]")
                return approved_queries
    
    console.print(f"[green]✅ Review complete! Approved {len(approved_queries)} out of {len(queries)} queries.[/green]")
    return approved_queries


def edit_query(query: RAGQuery) -> Optional[RAGQuery]:
    """Allow user to edit a query."""
    console.print("\n[bold]Editing Query[/bold]")
    console.print("[dim]Press Enter to keep current value[/dim]")
    
    # Edit query text
    new_query_text = Prompt.ask(
        "Query text",
        default=query.query_text
    )
    
    # Edit answer fact if needed
    new_answer_fact = Prompt.ask(
        "Answer fact",
        default=query.answer_fact
    )
    
    # Edit difficulty if provided
    new_difficulty = query.difficulty
    if query.difficulty:
        new_difficulty = Prompt.ask(
            "Difficulty",
            choices=["standard", "adversarial", "multi-hop"],
            default=query.difficulty
        )
    
    # Edit realism score if provided
    new_realism_score = getattr(query, 'realism_score', None)
    if hasattr(query, 'realism_score') and query.realism_score is not None:
        try:
            score_input = Prompt.ask(
                "Realism score (1.0-5.0)",
                default=str(query.realism_score)
            )
            new_realism_score = float(score_input)
            if not (1.0 <= new_realism_score <= 5.0):
                new_realism_score = query.realism_score
        except ValueError:
            pass  # Keep original score if invalid input
    
    # Ask for confirmation if changes were made
    if (new_query_text != query.query_text or 
        new_answer_fact != query.answer_fact or
        new_difficulty != query.difficulty or
        new_realism_score != getattr(query, 'realism_score', None)):
        
        if Confirm.ask("Save changes?"):
            # Update query with new values
            query.query_text = new_query_text
            query.answer_fact = new_answer_fact
            query.difficulty = new_difficulty
            query.realism_score = new_realism_score
            return query
    
    return None  # No changes or cancelled