"""RAG CLI commands for fact extraction and query generation."""

import typer
from pathlib import Path
from rich.console import Console
from rich.progress import Progress
from typing import Optional
from datetime import datetime

from qgen.core.rag_models import RAGConfig, BatchMetadata, RAGQuery
from qgen.core.chunk_processing import ChunkProcessor
from qgen.core.rag_generation import FactExtractor, FactDataManager, StandardQueryGenerator, QueryDataManager
from qgen.core.adversarial_generation import generate_adversarial_multihop_queries
from qgen.core.rag_quality import RAGQueryQualityFilter, RAGQueryDataManager
from qgen.core.rag_export import RAGExporter, RAGQueryDataManagerExtended
from qgen.core.rich_output import show_error_panel, create_success_panel, create_info_panel, create_header_panel
from qgen.core.env import auto_detect_provider, get_available_providers, validate_llm_provider, show_provider_setup_help
from .review import review_queries

console = Console()
rag_app = typer.Typer(help="RAG query generation commands (run from inside project directory)")


@rag_app.command("extract-facts")
def extract_facts_cmd(
    input_chunks: Optional[str] = typer.Option(None, help="Chunks directory (default: chunks/)"),
    provider: Optional[str] = typer.Option(None, help="LLM provider: openai, azure, github, or ollama (auto-detect if not specified)"),
    no_review: bool = typer.Option(False, help="Skip review interface")
):
    """Extract salient facts from chunks."""
    
    console.print("[blue]🔍 Starting fact extraction from chunks...[/blue]")
    
    # Validate RAG project
    if not Path("config.yml").exists():
        show_error_panel(
            "Not in a RAG Project Directory",
            "No config.yml found. RAG commands must be run from inside the project directory.",
            [
                "1. Create project: qgen init myproject --rag",
                "2. Navigate to project: cd myproject", 
                "3. Run RAG commands from inside the project directory",
                f"Current directory: {Path.cwd()}"
            ]
        )
        raise typer.Exit(1)
    
    # Auto-detect provider if not specified (environment already loaded globally)
    if provider is None:
        provider = auto_detect_provider()
        if provider is None:
            console.print("[red]❌ No LLM provider configuration found in environment[/red]")
            console.print("💡 Please set OpenAI, Azure OpenAI, or GitHub Models environment variables in .env file")
            raise typer.Exit(1)
        console.print(f"[blue]🔍 Auto-detected provider: {provider}[/blue]")
    else:
        # Validate specified provider is available
        if provider not in ["openai", "azure", "github", "ollama"]:
            console.print(f"[red]❌ Invalid provider: {provider}. Must be one of: openai, azure, github, ollama[/red]")
            raise typer.Exit(1)
            
        available_providers = get_available_providers()
        if provider not in available_providers:
            console.print(f"[red]❌ Provider '{provider}' not available[/red]")
            if available_providers:
                console.print(f"Available providers: {', '.join(available_providers)}")
            else:
                console.print("No providers configured. Please check your .env file.")
            raise typer.Exit(1)
    
    try:
        # Load configuration
        config = RAGConfig.load_from_file("config.yml")
        
        # Override provider if specified
        config.llm_provider = provider
        
        # Display header with provider information
        console.print(create_header_panel("🔍 RAG Fact Extraction", f"Extracting facts using {config.llm_provider.title()}"))
        
        # Load chunks
        chunks_dir = Path(input_chunks or "chunks")
        if not chunks_dir.exists():
            show_error_panel(
                "Chunks Directory Not Found",
                f"Directory '{chunks_dir}' does not exist",
                [
                    f"Create the directory: mkdir -p {chunks_dir}",
                    "Add your JSONL chunk files to the directory",
                    "Check the example.jsonl file for format reference"
                ]
            )
            raise typer.Exit(1)
        
        processor = ChunkProcessor()
        chunks = processor.load_chunks_from_directory(chunks_dir)
        
        if not chunks:
            show_error_panel(
                "No Chunks Found",
                f"No valid chunks found in {chunks_dir}",
                [
                    "Make sure JSONL files contain valid chunk data",
                    "Check the example.jsonl file for correct format",
                    "Verify chunk_id and text fields are present"
                ]
            )
            raise typer.Exit(1)
        
        # Show chunks summary
        summary = processor.get_chunks_summary(chunks)
        summary_text = f"""Total chunks: {summary['total_chunks']}
Chunks with relations: {summary['chunks_with_relations']}
Chunks with metadata: {summary['chunks_with_metadata']}
Average text length: {summary['avg_text_length']} chars"""
        
        console.print()
        console.print(create_info_panel("📊 Chunks Summary", summary_text))
        
        # Extract facts
        console.print()
        extractor = FactExtractor(config)
        facts, batch_metadata = extractor.extract_facts(chunks)
        
        if not facts:
            console.print("[yellow]⚠️  No facts were extracted from the chunks[/yellow]")
            console.print("💡 Consider:")
            console.print("• Checking if chunks contain meaningful content")
            console.print("• Adjusting the fact extraction prompt template")
            console.print("• Reviewing chunk text quality and length")
            raise typer.Exit(0)
        
        # Save generated facts with batch metadata
        fact_manager = FactDataManager()
        generated_path = fact_manager.save_facts(
            facts, 
            "generated", 
            batch_metadata=batch_metadata
        )
        
        # Review facts if requested
        approved_facts = facts
        if not no_review:
            from qgen.cli.review import review_facts
            console.print(f"\n[blue]🔍 Launching fact review interface...[/blue]")
            approved_facts = review_facts(facts)
            
            if not approved_facts:
                console.print("[yellow]⚠️  No facts were approved during review.[/yellow]")
                raise typer.Exit(0)
        
        # Save approved facts with updated batch metadata
        approved_batch_metadata = BatchMetadata(
            stage="approved",
            llm_model=batch_metadata.llm_model,
            provider=batch_metadata.provider,
            prompt_template=batch_metadata.prompt_template,
            llm_params=batch_metadata.llm_params,
            total_items=len(facts),
            success_count=len(approved_facts),
            failure_count=len(facts) - len(approved_facts),
            custom_metadata={
                "approval_rate": len(approved_facts) / len(facts) if facts else 0,
                "original_batch_id": batch_metadata.batch_id
            }
        )
        
        approved_path = fact_manager.save_facts(
            approved_facts,
            "approved",
            batch_metadata=approved_batch_metadata
        )
        
        # Show completion summary
        console.print()
        completion_text = f"""Generated: {len(facts)} facts
Approved: {len(approved_facts)} facts
Approval rate: {len(approved_facts) / len(facts) * 100:.1f}%
Saved to: {Path(approved_path).name}"""
        
        console.print(create_success_panel("✅ Fact Extraction Complete", completion_text))
        
        # Show next steps
        console.print(f"\n[yellow]💡 Next steps:[/yellow]")
        console.print(f"1. Review extracted facts in: {approved_path}")
        console.print(f"2. Generate queries: [cyan]qgen rag generate-queries[/cyan]")
        console.print(f"3. Check project status: [cyan]qgen rag status[/cyan]")
        console.print(f"\n[dim]ℹ️  Note: Run all RAG commands from inside the project directory[/dim]")
        
    except Exception as e:
        console.print(f"[red]❌ Fact extraction failed: {str(e)}[/red]")
        raise typer.Exit(1)


@rag_app.command("status")
def rag_status_cmd():
    """Show RAG project status and statistics."""
    
    if not Path("config.yml").exists():
        show_error_panel(
            "Not in a RAG Project Directory", 
            "No config.yml found. RAG commands must be run from inside the project directory.",
            [
                "1. Create project: qgen init myproject --rag",
                "2. Navigate to project: cd myproject",
                "3. Run RAG commands from inside the project directory",
                f"Current directory: {Path.cwd()}"
            ]
        )
        raise typer.Exit(1)
    
    try:
        # Load configuration
        config = RAGConfig.load_from_file("config.yml")
        
        # Check project structure
        project_structure = {
            "chunks": Path("chunks").exists(),
            "data": Path("data").exists(),
            "facts": Path("data/facts").exists(),
            "queries": Path("data/queries").exists(), 
            "exports": Path("data/exports").exists(),
            "prompts": Path("prompts").exists()
        }
        
        # Get data summaries
        fact_manager = FactDataManager()
        generated_facts = fact_manager.get_facts_summary("generated")
        approved_facts = fact_manager.get_facts_summary("approved")
        
        # Get query summaries (standard + multi-hop)
        query_manager = QueryDataManager()
        generated_queries = query_manager.get_queries_summary("generated")
        approved_queries = query_manager.get_queries_summary("approved")
        
        # Get multi-hop query summaries
        generated_multihop = query_manager.get_queries_summary("generated_multihop") 
        approved_multihop = query_manager.get_queries_summary("approved_multihop")
        
        # Count chunks
        chunks_count = 0
        chunks_dir = Path("chunks")
        if chunks_dir.exists():
            jsonl_files = list(chunks_dir.glob("*.jsonl"))
            if jsonl_files:
                processor = ChunkProcessor()
                try:
                    chunks = processor.load_chunks_from_directory(chunks_dir)
                    chunks_count = len(chunks)
                except:
                    pass
        
        # Project overview
        overview_text = f"""Project Type: RAG Query Generation
LLM Provider: {config.llm_provider}
Embedding Model: {config.embedding_model}

Directory Structure:
✅ chunks/     {'✓' if project_structure['chunks'] else '✗'}
✅ data/       {'✓' if project_structure['data'] else '✗'}  
✅ prompts/    {'✓' if project_structure['prompts'] else '✗'}"""
        
        console.print(create_info_panel("📋 RAG Project Overview", overview_text))
        
        # Data status with multi-hop breakdown
        total_generated_queries = generated_queries['count'] + generated_multihop['count']
        total_approved_queries = approved_queries['count'] + approved_multihop['count']
        
        data_text = f"""Input Chunks: {chunks_count}

Generated Facts: {generated_facts['count']}
Approved Facts: {approved_facts['count']}

Query Generation:
• Standard Queries: {generated_queries['count']} generated, {approved_queries['count']} approved
• Multi-hop Queries: {generated_multihop['count']} generated, {approved_multihop['count']} approved
• Total Queries: {total_generated_queries} generated, {total_approved_queries} approved"""
        
        if approved_facts['count'] > 0:
            data_text += f"""

Fact Quality:
• Avg Confidence: {approved_facts['avg_confidence']:.2f}
• High Confidence Facts: {approved_facts['high_confidence_count']}"""
        
        if total_approved_queries > 0 and total_generated_queries > 0:
            data_text += f"""

Overall Query Approval Rate: {total_approved_queries}/{total_generated_queries} ({total_approved_queries/total_generated_queries*100:.1f}%)"""
        
        console.print()
        console.print(create_info_panel("📊 Data Status", data_text))
        
        # Configuration summary  
        config_text = f"""Query Ratios:
• Standard: {config.standard_ratio:.1%}
• Adversarial: {config.adversarial_ratio:.1%}  
• Multi-hop: {config.multihop_ratio:.1%}

Quality Control:
• Min Realism Score: {config.min_realism_score}
• Similarity Threshold: {config.similarity_threshold}"""
        
        console.print()
        console.print(create_info_panel("⚙️  Configuration", config_text))
        
        # Recommendations based on current state
        recommendations = []
        if chunks_count == 0:
            recommendations.append("Add chunk data to chunks/ directory")
        elif generated_facts['count'] == 0:
            recommendations.append("Run: qgen rag extract-facts")
        elif approved_facts['count'] == 0:
            recommendations.append("Review and approve extracted facts")
        elif total_generated_queries == 0:
            recommendations.append("Generate standard queries: qgen rag generate-queries")
            recommendations.append("Generate multi-hop queries: qgen rag generate-multihop")
        elif total_approved_queries == 0:
            recommendations.append("Review and approve generated queries")
            recommendations.append("OR use quality filtering: qgen rag filter")
        else:
            recommendations.append(f"Filter by quality: qgen rag filter --min-score {config.high_realism_threshold}")
            recommendations.append("Export final dataset: qgen rag export --format jsonl")
            
        # Additional recommendations for multi-hop
        if generated_multihop['count'] == 0 and approved_facts['count'] > 0:
            recommendations.append("Consider generating multi-hop queries: qgen rag generate-multihop")
        elif generated_multihop['count'] > 0 and approved_multihop['count'] == 0:
            recommendations.append("Review multi-hop queries: qgen rag review-queries")
        
        if recommendations:
            rec_text = "\n".join(f"• {rec}" for rec in recommendations)
            console.print()
            console.print(create_info_panel("💡 Recommendations", rec_text))
        
    except Exception as e:
        console.print(f"[red]❌ Error checking project status: {str(e)}[/red]")
        raise typer.Exit(1)


@rag_app.command("review-facts")  
def review_facts_cmd():
    """Review existing generated facts."""
    if not Path("config.yml").exists():
        show_error_panel(
            "Not in a RAG Project Directory", 
            "No config.yml found. RAG commands must be run from inside the project directory.",
            [
                "1. Create project: qgen init myproject --rag",
                "2. Navigate to project: cd myproject",
                "3. Run RAG commands from inside the project directory",
                f"Current directory: {Path.cwd()}"
            ]
        )
        raise typer.Exit(1)
    
    try:
        # Load generated facts
        fact_manager = FactDataManager()
        facts = fact_manager.load_facts("generated")
        
        if not facts:
            show_error_panel(
                "No Generated Facts Found",
                "No facts found to review", 
                [
                    "Run: qgen rag extract-facts to extract facts first",
                    "Check if data/facts/generated.json exists"
                ]
            )
            raise typer.Exit(1)
        
        # Launch review interface
        from qgen.cli.review import review_facts
        console.print(f"[blue]🔍 Reviewing {len(facts)} generated facts...[/blue]")
        approved_facts = review_facts(facts)
        
        if not approved_facts:
            console.print("[yellow]⚠️  No facts were approved during review.[/yellow]")
            raise typer.Exit(0)
        
        # Load original batch metadata for continuity
        original_batch_metadata = fact_manager.load_batch_metadata("generated")
        
        # Create approved batch metadata
        if original_batch_metadata:
            approved_batch_metadata = BatchMetadata(
                stage="approved",
                llm_model=original_batch_metadata.llm_model,
                provider=original_batch_metadata.provider,
                prompt_template=original_batch_metadata.prompt_template,
                llm_params=original_batch_metadata.llm_params,
                total_items=len(facts),
                success_count=len(approved_facts),
                failure_count=len(facts) - len(approved_facts),
                custom_metadata={
                    "approval_rate": len(approved_facts) / len(facts) if facts else 0,
                    "original_batch_id": original_batch_metadata.batch_id,
                    "reviewed_at": datetime.now().isoformat()
                }
            )
        else:
            # Fallback if no original metadata
            approved_batch_metadata = BatchMetadata(
                stage="approved",
                llm_model="unknown",
                provider="unknown",
                prompt_template="unknown",
                total_items=len(facts),
                success_count=len(approved_facts),
                failure_count=len(facts) - len(approved_facts),
                custom_metadata={
                    "approval_rate": len(approved_facts) / len(facts) if facts else 0,
                    "reviewed_at": datetime.now().isoformat()
                }
            )
        
        # Save approved facts with proper metadata
        approved_path = fact_manager.save_facts(
            approved_facts,
            "approved",
            batch_metadata=approved_batch_metadata
        )
        
        # Show completion summary  
        completion_text = f"""Generated: {len(facts)} facts
Approved: {len(approved_facts)} facts
Approval rate: {len(approved_facts) / len(facts) * 100:.1f}%
Saved to: {Path(approved_path).name}"""
        
        console.print()
        console.print(create_success_panel("✅ Fact Review Complete", completion_text))
        
    except Exception as e:
        console.print(f"[red]❌ Fact review failed: {str(e)}[/red]")
        raise typer.Exit(1)


@rag_app.command("generate-queries")
def generate_queries_cmd(
    count: Optional[int] = typer.Option(None, "--count", "-c", help="Number of queries to generate (default: all facts)"),
    provider: Optional[str] = typer.Option(None, "--provider", "-p", help="LLM provider (openai, azure, github, ollama)"),
    no_review: bool = typer.Option(False, "--no-review", help="Skip interactive review process")
):
    """Generate standard queries from approved facts."""
    
    try:
        # Load configuration (environment already loaded globally)
        config = RAGConfig()
        
        # Auto-detect provider if not specified (consistent with fact extraction)
        if provider is None:
            provider = auto_detect_provider()
            if provider is None:
                console.print("[red]❌ No LLM provider configuration found in environment[/red]")
                console.print("💡 Please set OpenAI, Azure OpenAI, or GitHub Models environment variables in .env file")
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
        
        # Set provider in config
        config.llm_provider = provider
        
        # Validate provider configuration (should always pass now, but double-check)
        if not validate_llm_provider(config.llm_provider):
            console.print(f"[red]❌ {config.llm_provider.title()} provider not configured[/red]")
            show_provider_setup_help(config.llm_provider) 
            raise typer.Exit(1)
            
        # Display header
        console.print(create_header_panel("🤖 RAG Query Generation", f"Generating queries using {config.llm_provider.title()}"))
        
        # Load approved facts
        fact_manager = FactDataManager()
        facts = fact_manager.load_facts("approved")
        
        if not facts:
            show_error_panel(
                "No Approved Facts Found", 
                "You need approved facts before generating queries.",
                [
                    "1. Run fact extraction: qgen rag extract-facts --input chunks/",
                    "2. Review and approve facts: qgen rag review-facts"
                ]
            )
            raise typer.Exit(1)
        
        # Load chunks for context
        chunk_processor = ChunkProcessor()
        chunks = chunk_processor.load_chunks_from_directory(Path("chunks"))
        chunks_map = {chunk.chunk_id: chunk for chunk in chunks}
        
        # Apply count limit if specified
        original_fact_count = len(facts)
        if count:
            if count > original_fact_count:
                console.print(f"[yellow]⚠️  Requested {count} facts, but only {original_fact_count} approved facts available[/yellow]")
                console.print(f"[blue]📝 Processing all {original_fact_count} facts[/blue]")
            elif count < original_fact_count:
                facts = facts[:count]
                console.print(f"[blue]📝 Limiting to first {count} of {original_fact_count} facts[/blue]")
            else:
                console.print(f"[blue]📝 Processing all {count} facts[/blue]")
        else:
            console.print(f"[blue]📊 Processing all {len(facts)} approved facts[/blue]")
        
        # Generate queries
        query_generator = StandardQueryGenerator(config)
        queries, batch_metadata = query_generator.generate_queries_from_facts(facts, chunks_map)
        
        if not queries:
            console.print("[yellow]⚠️  No queries were generated.[/yellow]")
            raise typer.Exit(0)
        
        # Save generated queries
        query_manager = QueryDataManager()
        saved_path = query_manager.save_queries(queries, "generated", batch_metadata=batch_metadata)
        
        # Review queries if requested
        approved_queries = queries
        if not no_review:
            console.print("\n[bold blue]📝 Starting query review process...[/bold blue]")
            approved_queries = review_queries(queries, chunks_map)
            
            if not approved_queries:
                console.print("[yellow]⚠️  No queries were approved during review.[/yellow]")
                raise typer.Exit(0)
        
        # Save approved queries with updated batch metadata
        approved_batch_metadata = BatchMetadata(
            stage="approved",
            llm_model=batch_metadata.llm_model,
            provider=batch_metadata.provider,
            prompt_template=batch_metadata.prompt_template,
            llm_params=batch_metadata.llm_params,
            total_items=len(queries),
            success_count=len(approved_queries),
            failure_count=len(queries) - len(approved_queries),
            custom_metadata={
                "approval_rate": len(approved_queries) / len(queries) if queries else 0,
                "original_batch_id": batch_metadata.batch_id,
                "query_type": "standard"
            }
        )
        
        approved_path = query_manager.save_queries(
            approved_queries,
            "approved",
            batch_metadata=approved_batch_metadata
        )
        
        # Display summary
        summary_text = f"""Generated: {len(queries)} queries
Approved: {len(approved_queries)} queries  
Approval Rate: {len(approved_queries)/len(queries)*100:.1f}%
Provider: {config.llm_provider.title()}
Files: {saved_path}, {approved_path}"""
        
        console.print()
        console.print(create_success_panel("✅ Query Generation Complete", summary_text))
        
    except Exception as e:
        console.print(f"[red]❌ Query generation failed: {str(e)}[/red]")
        raise typer.Exit(1)


@rag_app.command("review-queries")  
def review_queries_cmd():
    """Review existing generated queries without regenerating."""
    
    try:
        # Load generated queries (environment already loaded globally)
        query_manager = QueryDataManager()
        standard_queries = query_manager.load_queries("generated")
        multihop_queries = query_manager.load_queries("generated_multihop")
        
        # Combine both types of queries
        queries = standard_queries + multihop_queries
        
        if not queries:
            show_error_panel(
                "No Generated Queries Found",
                "You need to generate queries first.",
                ["qgen rag generate-queries", "qgen rag generate-multihop"]
            )
            raise typer.Exit(1)
        
        console.print(f"[dim]✅ Loaded {len(standard_queries)} standard + {len(multihop_queries)} multi-hop queries[/dim]")
        
        # Load chunks for context
        chunk_processor = ChunkProcessor()
        chunks = chunk_processor.load_chunks_from_directory(Path("chunks"))
        chunks_map = {chunk.chunk_id: chunk for chunk in chunks}
        
        # Load original batch metadata for continuity
        original_batch_metadata = query_manager.load_batch_metadata("generated")
        
        console.print(create_header_panel("📝 Query Review", f"Reviewing {len(queries)} generated queries"))
        
        # Review queries
        approved_queries = review_queries(queries, chunks_map)
        
        if not approved_queries:
            console.print("[yellow]⚠️  No queries were approved during review.[/yellow]")
            raise typer.Exit(0)
        
        # Create approved batch metadata
        if original_batch_metadata:
            approved_batch_metadata = BatchMetadata(
                stage="approved",
                llm_model=original_batch_metadata.llm_model,
                provider=original_batch_metadata.provider,
                prompt_template=original_batch_metadata.prompt_template,
                llm_params=original_batch_metadata.llm_params,
                total_items=len(queries),
                success_count=len(approved_queries),
                failure_count=len(queries) - len(approved_queries),
                custom_metadata={
                    "approval_rate": len(approved_queries) / len(queries) if queries else 0,
                    "original_batch_id": original_batch_metadata.batch_id,
                    "reviewed_at": datetime.now().isoformat(),
                    "query_type": "standard"
                }
            )
        else:
            # Fallback if no original metadata
            approved_batch_metadata = BatchMetadata(
                stage="approved",
                llm_model="unknown",
                provider="unknown",
                prompt_template="unknown",
                total_items=len(queries),
                success_count=len(approved_queries),
                failure_count=len(queries) - len(approved_queries),
                custom_metadata={
                    "approval_rate": len(approved_queries) / len(queries) if queries else 0,
                    "reviewed_at": datetime.now().isoformat(),
                    "query_type": "standard"
                }
            )
        
        # Save approved queries with proper metadata
        approved_path = query_manager.save_queries(
            approved_queries,
            "approved", 
            batch_metadata=approved_batch_metadata
        )
        
        # Display completion message
        completion_text = f"""Generated: {len(queries)} queries
Approved: {len(approved_queries)} queries
Approval Rate: {len(approved_queries)/len(queries)*100:.1f}%
File: {approved_path}"""
        
        console.print()
        console.print(create_success_panel("✅ Query Review Complete", completion_text))
        
    except Exception as e:
        console.print(f"[red]❌ Query review failed: {str(e)}[/red]")
        raise typer.Exit(1)


@rag_app.command("generate-multihop")
def generate_multihop_queries_cmd(
    count: Optional[int] = typer.Option(None, "--count", "-c", help="Max number of chunk combinations to process"),
    provider: Optional[str] = typer.Option(None, "--provider", "-p", help="LLM provider (openai, azure, github, ollama)"),
    no_review: bool = typer.Option(False, "--no-review", help="Skip interactive review process"),
    queries_per_combo: Optional[int] = typer.Option(None, "--queries-per-combo", help="Queries per chunk combination (default: from config)")
):
    """Generate adversarial multi-hop queries requiring multiple chunks to answer."""
    
    try:
        # Load configuration
        config = RAGConfig.load_from_file("config.yml")
        
        # Override queries per combination if specified
        if queries_per_combo:
            config.multihop_queries_per_combination = queries_per_combo
        
        # Auto-detect provider if not specified
        if provider is None:
            provider = auto_detect_provider()
            if provider is None:
                console.print("[red]❌ No LLM provider configuration found in environment[/red]")
                console.print("💡 Please set OpenAI, Azure OpenAI, or GitHub Models environment variables in .env file")
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
        
        # Set provider in config
        config.llm_provider = provider
        
        # Display header
        console.print(create_header_panel(
            "🔗 Adversarial Multi-Hop Query Generation", 
            f"Creating challenging multi-hop queries using {config.llm_provider.title()}"
        ))
        
        # Load approved facts
        fact_manager = FactDataManager()
        facts = fact_manager.load_facts("approved")
        
        if not facts:
            show_error_panel(
                "No Approved Facts Found", 
                "You need approved facts before generating multi-hop queries.",
                [
                    "1. Run fact extraction: qgen rag extract-facts --input chunks/",
                    "2. Review and approve facts: qgen rag review-facts"
                ]
            )
            raise typer.Exit(1)
        
        # Load chunks for context
        chunk_processor = ChunkProcessor()
        chunks = chunk_processor.load_chunks_from_directory(Path("chunks"))
        chunks_map = {chunk.chunk_id: chunk for chunk in chunks}
        
        # Show configuration summary
        config_text = f"""Chunk Range: {config.multihop_chunk_range[0]}-{config.multihop_chunk_range[1]} chunks per query
Queries per Combination: {config.multihop_queries_per_combination}
Similarity Threshold: {config.similarity_threshold}
Available Facts: {len(facts)}
Available Chunks: {len(chunks_map)}"""
        
        console.print()
        console.print(create_info_panel("⚙️  Multi-Hop Configuration", config_text))
        
        # Generate multi-hop queries
        console.print()
        console.print("[blue]🔗 Analyzing chunk relationships and generating adversarial multi-hop queries...[/blue]")
        
        queries = generate_adversarial_multihop_queries(config, facts, chunks_map)
        
        if not queries:
            console.print("[yellow]⚠️  No multi-hop queries were generated.[/yellow]")
            console.print("💡 This might happen if:")
            console.print("• No chunk combinations meet the similarity threshold")
            console.print("• Chunks lack related_chunks relationships") 
            console.print("• Chunk content is too dissimilar for multi-hop reasoning")
            raise typer.Exit(0)
        
        # Apply count limit if specified
        if count and count < len(queries):
            console.print(f"[blue]📝 Limiting to first {count} of {len(queries)} generated queries[/blue]")
            queries = queries[:count]
        
        # Create batch metadata
        batch_metadata = BatchMetadata(
            stage="generated",
            llm_model=f"{provider}-default",  # Simplified model name
            provider=provider,
            prompt_template=config.prompt_templates.get("multihop_query", "prompts/multihop_query_generation.txt"),
            llm_params=config.llm_params,
            total_items=len(queries),
            success_count=len(queries),
            failure_count=0,
            custom_metadata={
                "query_type": "multihop_adversarial",
                "chunk_range": config.multihop_chunk_range,
                "queries_per_combination": config.multihop_queries_per_combination,
                "similarity_threshold": config.similarity_threshold
            }
        )
        
        # Save generated queries
        query_manager = QueryDataManager()
        saved_path = query_manager.save_queries(queries, "generated_multihop", batch_metadata=batch_metadata)
        
        # Review queries if requested
        approved_queries = queries
        if not no_review:
            console.print("\n[bold blue]📝 Starting multi-hop query review process...[/bold blue]")
            console.print("[dim]Note: Multi-hop queries will show all related chunks with highlighting[/dim]")
            approved_queries = review_queries(queries, chunks_map)
            
            if not approved_queries:
                console.print("[yellow]⚠️  No multi-hop queries were approved during review.[/yellow]")
                raise typer.Exit(0)
        
        # Save approved queries with updated batch metadata
        approved_batch_metadata = BatchMetadata(
            stage="approved",
            llm_model=batch_metadata.llm_model,
            provider=batch_metadata.provider,
            prompt_template=batch_metadata.prompt_template,
            llm_params=batch_metadata.llm_params,
            total_items=len(queries),
            success_count=len(approved_queries),
            failure_count=len(queries) - len(approved_queries),
            custom_metadata={
                "approval_rate": len(approved_queries) / len(queries) if queries else 0,
                "original_batch_id": batch_metadata.batch_id,
                "query_type": "multihop_adversarial",
                "chunk_range": config.multihop_chunk_range
            }
        )
        
        approved_path = query_manager.save_queries(
            approved_queries,
            "approved_multihop",
            batch_metadata=approved_batch_metadata
        )
        
        # Display summary
        summary_text = f"""Generated: {len(queries)} multi-hop queries
Approved: {len(approved_queries)} queries  
Approval Rate: {len(approved_queries)/len(queries)*100:.1f}%
Provider: {config.llm_provider.title()}
Query Type: Adversarial Multi-Hop
Avg Chunks per Query: {sum(len(q.source_chunk_ids) for q in approved_queries) / len(approved_queries):.1f}
Files: {saved_path}, {approved_path}"""
        
        console.print()
        console.print(create_success_panel("✅ Multi-Hop Query Generation Complete", summary_text))
        
        # Show next steps
        console.print(f"\n[yellow]💡 Next steps:[/yellow]")
        console.print(f"1. Review multi-hop queries in: {approved_path}")
        console.print(f"2. Combine with regular queries for full dataset")
        console.print(f"3. Export final dataset: [cyan]qgen export --format csv[/cyan]")
        console.print(f"\n[dim]ℹ️  Multi-hop queries test advanced reasoning across multiple chunks[/dim]")
        
    except Exception as e:
        console.print(f"[red]❌ Multi-hop query generation failed: {str(e)}[/red]")
        raise typer.Exit(1)


@rag_app.command("filter")
def filter_queries_cmd(
    min_score: Optional[float] = typer.Option(None, "--min-score", "-s", help="Minimum realism score (overrides config)"),
    input_stage: str = typer.Option("generated", "--input", "-i", help="Input stage: generated"),
    output_stage: str = typer.Option("approved", "--output", "-o", help="Output stage: approved"),
    provider: Optional[str] = typer.Option(None, "--provider", "-p", help="LLM provider (openai, azure, github, ollama)"),
    no_review: bool = typer.Option(False, "--no-review", help="Skip interactive review of filtered results"),
    show_failed: bool = typer.Option(False, "--show-failed", help="Display queries that failed filtering"),
):
    """Filter queries based on realism scores and quality metrics."""
    
    try:
        console.print(create_header_panel("🎯 RAG Query Quality Filtering", "Evaluating query realism and quality"))
        
        # Validate RAG project
        if not Path("config.yml").exists():
            show_error_panel(
                "Not in a RAG Project Directory",
                "No config.yml found. RAG commands must be run from inside the project directory.",
                [
                    "1. Create project: qgen init myproject --rag",
                    "2. Navigate to project: cd myproject", 
                    "3. Run RAG commands from inside the project directory"
                ]
            )
            raise typer.Exit(1)
        
        # Load configuration
        config = RAGConfig.load_from_file("config.yml")
        
        # Override min score if provided
        if min_score is not None:
            if min_score < 1.0 or min_score > 5.0:
                console.print("[red]❌ Minimum score must be between 1.0 and 5.0[/red]")
                raise typer.Exit(1)
            config.min_realism_score = min_score
        
        # Auto-detect provider if not specified
        if provider is None:
            provider = auto_detect_provider()
            if provider is None:
                console.print("[red]❌ No LLM provider configuration found in environment[/red]")
                show_provider_setup_help()
                raise typer.Exit(1)
            console.print(f"[blue]🔍 Auto-detected provider: {provider}[/blue]")
        else:
            # Validate specified provider is available
            available_providers = get_available_providers()
            if provider not in available_providers:
                console.print(f"[red]❌ Provider '{provider}' not available. Available: {', '.join(available_providers)}[/red]")
                raise typer.Exit(1)
        
        # Update config with provider
        config.llm_provider = provider
        
        # Load queries
        data_manager = RAGQueryDataManager()
        queries = data_manager.load_queries(input_stage)
        
        if not queries:
            show_error_panel(
                f"No {input_stage.title()} Queries Found",
                f"No queries found in '{input_stage}' stage.",
                [
                    "1. Generate queries first: qgen rag generate-queries",
                    "2. Or generate multi-hop queries: qgen rag generate-multihop",
                    f"Current directory: {Path.cwd()}"
                ]
            )
            raise typer.Exit(1)
        
        console.print(f"[blue]📊 Found {len(queries)} queries in '{input_stage}' stage[/blue]")
        console.print(f"[blue]🎯 Filtering threshold: {config.min_realism_score}/5.0[/blue]")
        
        # Create quality filter
        quality_filter = RAGQueryQualityFilter(config)
        
        # CLI-specific progress callback with Rich progress bar
        def progress_callback(current: int, total: int, message: str):
            # This will be called by the filter to update progress
            pass
        
        # Run filtering with progress tracking
        with Progress() as progress:
            task = progress.add_task("Filtering queries...", total=len(queries))
            
            def rich_progress_callback(current: int, total: int, message: str):
                progress.update(task, completed=current, description=f"[cyan]{message}[/cyan]")
            
            passed_queries, failed_queries, stats = quality_filter.filter_queries(
                queries, 
                progress_callback=rich_progress_callback
            )
        
        # Save filtered results
        data_manager.save_queries(
            passed_queries, 
            output_stage, 
            metadata={
                "filtering_stats": stats,
                "source_stage": input_stage,
                "filter_threshold": config.min_realism_score,
                "provider_used": provider
            }
        )
        
        # Display summary
        summary = quality_filter.get_filtering_summary(passed_queries, failed_queries, stats)
        console.print()
        console.print(create_success_panel("✅ Quality Filtering Complete", summary))
        
        # Show failed queries if requested
        if show_failed and failed_queries:
            console.print("\n[yellow]📉 Queries that failed filtering:[/yellow]")
            for i, query in enumerate(failed_queries[:5], 1):  # Show first 5
                score = query.realism_rating or 0
                reasoning = query.reasoning or "No reasoning available"
                console.print(f"\n[dim]{i}. Score: {score}/5.0[/dim]")
                console.print(f"[red]Query:[/red] {query.query_text}")
                console.print(f"[dim]Reason:[/dim] {reasoning[:100]}...")
            
            if len(failed_queries) > 5:
                console.print(f"\n[dim]... and {len(failed_queries) - 5} more failed queries[/dim]")
        
        # Offer review of results
        if not no_review and passed_queries:
            console.print(f"\n[yellow]💡 Next steps:[/yellow]")
            console.print(f"1. Review filtered queries: [cyan]qgen rag review-queries[/cyan]")
            console.print(f"2. Export final dataset: [cyan]qgen rag export --format jsonl[/cyan]")
            
            if typer.confirm("\n🔍 Would you like to review the filtered queries now?"):
                console.print("\n[blue]📝 Starting query review...[/blue]")
                
                # Load chunks for context
                chunk_processor = ChunkProcessor()
                chunks = chunk_processor.load_chunks_from_directory(Path("chunks"))
                chunks_map = {chunk.chunk_id: chunk for chunk in chunks}
                
                # Use existing review interface
                reviewed_queries = review_queries(passed_queries, chunks_map)
                
                if reviewed_queries:
                    # Save reviewed queries
                    data_manager.save_queries(
                        reviewed_queries, 
                        "approved",
                        metadata={
                            "review_completed": True,
                            "reviewed_at": datetime.now().isoformat(),
                            "source_filtering": stats
                        }
                    )
                    console.print(f"[green]✅ Review complete: {len(reviewed_queries)} queries approved[/green]")
        
    except Exception as e:
        console.print(f"[red]❌ Quality filtering failed: {str(e)}[/red]")
        raise typer.Exit(1)


@rag_app.command("export")
def export_queries_cmd(
    format: str = typer.Option("jsonl", "--format", "-f", help="Export format: jsonl, json, csv"),
    stage: str = typer.Option("approved", "--stage", "-s", help="Stage to export: generated, approved, etc."),
    output: Optional[str] = typer.Option(None, "--output", "-o", help="Output file path (auto-generated if not specified)"),
    show_stats: bool = typer.Option(True, "--stats/--no-stats", help="Show detailed export statistics"),
    preview: bool = typer.Option(False, "--preview", help="Preview export data without saving"),
):
    """Export RAG queries to file with comprehensive statistics."""
    
    try:
        console.print(create_header_panel("📊 RAG Query Export", f"Exporting queries from '{stage}' stage"))
        
        # Validate RAG project
        if not Path("config.yml").exists():
            show_error_panel(
                "Not in a RAG Project Directory",
                "No config.yml found. RAG commands must be run from inside the project directory.",
                [
                    "1. Create project: qgen init myproject --rag",
                    "2. Navigate to project: cd myproject", 
                    "3. Run RAG commands from inside the project directory"
                ]
            )
            raise typer.Exit(1)
        
        # Validate format
        supported_formats = ["jsonl", "json", "csv"]
        if format.lower() not in supported_formats:
            console.print(f"[red]❌ Unsupported format '{format}'. Supported: {', '.join(supported_formats)}[/red]")
            raise typer.Exit(1)
        
        # Load queries
        data_manager = RAGQueryDataManagerExtended()
        available_stages = data_manager.get_available_stages()
        
        if not available_stages:
            show_error_panel(
                "No Query Data Found",
                "No query stages found in this project.",
                [
                    "1. Generate queries: qgen rag generate-queries",
                    "2. Or generate multi-hop queries: qgen rag generate-multihop",
                    "3. Review and approve queries before exporting"
                ]
            )
            raise typer.Exit(1)
        
        if stage not in available_stages:
            console.print(f"[red]❌ Stage '{stage}' not found. Available stages: {', '.join(available_stages)}[/red]")
            
            # Suggest closest match
            if "approved" in available_stages:
                console.print("[yellow]💡 Try: --stage approved[/yellow]")
            elif "generated" in available_stages:
                console.print("[yellow]💡 Try: --stage generated[/yellow]")
                
            raise typer.Exit(1)
        
        # Load queries from stage
        queries = data_manager.load_queries_for_export(stage)
        
        if not queries:
            show_error_panel(
                f"No Queries in '{stage}' Stage",
                f"The '{stage}' stage exists but contains no queries.",
                [
                    "1. Check if queries were properly generated",
                    "2. Verify the stage name is correct",
                    f"3. Available stages: {', '.join(available_stages)}"
                ]
            )
            raise typer.Exit(1)
        
        console.print(f"[blue]📋 Found {len(queries)} queries in '{stage}' stage[/blue]")
        
        # Preview mode
        if preview:
            console.print(f"\n[yellow]👀 Preview of export data (first 3 queries):[/yellow]")
            
            exporter = RAGExporter()
            preview_data = exporter.prepare_export_data(queries[:3])
            
            for i, record in enumerate(preview_data, 1):
                console.print(f"\n[dim]Query {i}:[/dim]")
                console.print(f"[white]Query:[/white] {record['query']}")
                console.print(f"[white]Answer:[/white] {record['answer']}")
                console.print(f"[white]Difficulty:[/white] {record['difficulty']}")
                if record.get('realism_score'):
                    console.print(f"[white]Realism:[/white] {record['realism_score']}/5.0")
                console.print(f"[white]Chunks:[/white] {len(record['source_chunk_ids'])}")
            
            if len(queries) > 3:
                console.print(f"\n[dim]... and {len(queries) - 3} more queries[/dim]")
                
            console.print(f"\n[blue]ℹ️  Run without --preview to export all {len(queries)} queries[/blue]")
            return
        
        # Generate output filename if not provided
        if not output:
            filename = data_manager.get_export_filename(stage, format)
            output = data_manager.get_export_path(filename)
        else:
            # Ensure output directory exists
            Path(output).parent.mkdir(parents=True, exist_ok=True)
        
        # Export queries
        console.print(f"[blue]💾 Exporting to: {output}[/blue]")
        
        exporter = RAGExporter()
        stats = exporter.export_queries(queries, format, output)
        
        # Display results
        console.print()
        console.print(create_success_panel(
            "✅ Export Complete", 
            f"Successfully exported {len(queries)} queries to {format.upper()} format"
        ))
        
        console.print(f"[green]📁 File saved: {output}[/green]")
        console.print(f"[green]📏 File size: {stats.get('file_size_mb', 0)} MB[/green]")
        
        # Show detailed statistics
        if show_stats:
            console.print("\n" + exporter.generate_export_summary_text(stats))
        
        # Show next steps
        console.print(f"\n[yellow]💡 Next steps:[/yellow]")
        console.print(f"• Use the exported file for RAG evaluation")
        console.print(f"• File location: {output}")
        
        if format == "jsonl":
            console.print("• JSONL format is ideal for most RAG evaluation tools")
        elif format == "json":
            console.print("• JSON format includes metadata and statistics")
        elif format == "csv":
            console.print("• CSV format is suitable for analysis in spreadsheets")
        
        # Additional export suggestions
        if stage == "generated" and "approved" in available_stages:
            console.print(f"\n[dim]💡 Consider exporting 'approved' stage for final dataset[/dim]")
        
        if format != "jsonl":
            console.print(f"[dim]💡 Try --format jsonl for RAG evaluation compatibility[/dim]")
        
    except Exception as e:
        console.print(f"[red]❌ Export failed: {str(e)}[/red]")
        raise typer.Exit(1)


if __name__ == "__main__":
    rag_app()