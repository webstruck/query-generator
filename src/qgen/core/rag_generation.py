"""RAG query generation logic using structured LLM responses."""

from typing import List, Dict, Optional, Any, Tuple
from rich.progress import Progress, SpinnerColumn, TextColumn
from rich.console import Console
from datetime import datetime
from pathlib import Path

from .rag_models import ChunkData, ExtractedFact, RAGQuery, RAGConfig, BatchMetadata, FactSpan
from .structured_llm import create_structured_llm_provider, extract_fact_structured, generate_standard_query_structured, RateLimitExceededException
import time

console = Console()


class FactExtractor:
    """Extracts salient facts from text chunks using structured LLM responses."""
    
    def __init__(self, config: RAGConfig):
        self.config = config
        
        # Create structured LLM provider
        self.llm_provider = create_structured_llm_provider(
            config.llm_provider, 
            **config.llm_params
        )
        
        # Load prompt template
        self.prompt_template = self._load_prompt_template(
            config.prompt_templates["fact_extraction"]
        )
    
    def _load_prompt_template(self, template_path: str) -> str:
        """Load prompt template from file."""
        try:
            template_file = Path(template_path)
            if template_file.exists():
                return template_file.read_text(encoding='utf-8')
            else:
                # Fallback to default template
                return self._get_default_fact_extraction_template()
        except Exception as e:
            console.print(f"[yellow]⚠️  Warning: Could not load template {template_path}: {e}[/yellow]")
            return self._get_default_fact_extraction_template()
    
    def _get_default_fact_extraction_template(self) -> str:
        """Get default fact extraction template."""
        return """You are an expert at extracting salient facts from text chunks.

Given the following text chunk, identify ONE key fact that a user might want to ask a question about.
The fact should be:
- Specific and actionable
- Clearly stated in the text
- Something a real user would want to know

Chunk ID: {chunk_id}
Chunk Text: {chunk_text}

Extract the most important fact that users would commonly ask about."""
    
    def extract_facts(self, chunks: List[ChunkData]) -> tuple[List[ExtractedFact], BatchMetadata]:
        """Extract salient facts from chunks using structured responses."""
        facts = []
        start_time = time.time()
        failure_count = 0
        
        console.print(f"[blue]🔍 Extracting facts from {len(chunks)} chunks...[/blue]")
        
        with Progress() as progress:
            task = progress.add_task("Extracting facts...", total=len(chunks))
            
            for chunk in chunks:
                try:
                    fact = self._extract_fact_from_chunk(chunk)
                    if fact:
                        facts.append(fact)
                        progress.update(
                            task, 
                            advance=1,
                            description=f"Extracted fact from {chunk.chunk_id}"
                        )
                    else:
                        failure_count += 1
                        progress.update(
                            task,
                            advance=1, 
                            description=f"No fact extracted from {chunk.chunk_id}"
                        )
                        
                except RateLimitExceededException as e:
                    console.print(f"[red]❌ Failed to extract fact from chunk {chunk.chunk_id}: {e}[/red]")
                    console.print("[red]🛑 Rate limit exceeded. Stopping processing to avoid further failures.[/red]")
                    console.print("[yellow]💡 Suggestion: Wait for the rate limit to reset or switch to a different provider (--provider ollama)[/yellow]")
                    break
                except Exception as e:
                    console.print(f"[red]❌ Error extracting fact from {chunk.chunk_id}: {e}[/red]")
                    failure_count += 1
                    progress.update(task, advance=1)
                    continue
        
        end_time = time.time()
        processing_time = end_time - start_time
        
        # Create batch metadata
        batch_metadata = BatchMetadata(
            stage="generated",
            llm_model=getattr(self.llm_provider, 'model_name', 'unknown'),
            provider=self.config.llm_provider,
            prompt_template=self.config.prompt_templates["fact_extraction"],
            llm_params=self.config.llm_params,
            total_items=len(chunks),
            success_count=len(facts),
            failure_count=failure_count,
            processing_time_seconds=processing_time
        )
        
        console.print(f"[green]✅ Extracted {len(facts)} facts successfully[/green]")
        return facts, batch_metadata
    
    def _extract_fact_from_chunk(self, chunk: ChunkData) -> Optional[ExtractedFact]:
        """Extract a single salient fact from a chunk using structured response."""
        # Format prompt with chunk data
        prompt = self.prompt_template.format(
            chunk_id=chunk.chunk_id,
            chunk_text=chunk.text
        )
        
        try:
            # Get structured response using instructor
            response = extract_fact_structured(self.llm_provider, prompt)
            
            # Create span information if provided
            span = None
            if response.span_start is not None and response.span_end is not None:
                span = FactSpan(
                    start=response.span_start,
                    end=response.span_end,
                    highlighted_text=response.highlighted_text
                )
            
            # Create ExtractedFact from structured response (UUID auto-generated)
            fact = ExtractedFact(
                chunk_id=chunk.chunk_id,
                fact_text=response.fact,
                extraction_confidence=response.confidence,
                reasoning=response.reasoning,
                span=span
            )
            
            return fact
            
        except Exception as e:
            console.print(f"[red]❌ Failed to extract fact from chunk {chunk.chunk_id}: {e}[/red]")
            return None


class FactDataManager:
    """Manages fact data storage and retrieval."""
    
    def __init__(self, project_root: str = "."):
        self.project_root = Path(project_root)
        self.facts_dir = self.project_root / "data" / "facts"
        self.facts_dir.mkdir(parents=True, exist_ok=True)
    
    def save_facts(self, facts: List[ExtractedFact], stage: str, 
                   batch_metadata: Optional[BatchMetadata] = None, 
                   custom_metadata: Optional[Dict] = None) -> str:
        """Save facts to JSON file with BatchMetadata."""
        import json
        
        file_path = self.facts_dir / f"{stage}.json"
        
        # Create or use provided batch metadata
        if batch_metadata is None:
            batch_metadata = BatchMetadata(
                stage=stage,
                llm_model="unknown",
                provider="unknown", 
                prompt_template="unknown",
                total_items=len(facts),
                success_count=len(facts),
                custom_metadata=custom_metadata or {}
            )
        
        # Prepare data with structured metadata
        data = {
            "batch_metadata": batch_metadata.model_dump(),
            "facts": [fact.model_dump() for fact in facts]
        }
        
        # Custom JSON encoder for datetime objects
        def json_serializer(obj):
            if isinstance(obj, datetime):
                return obj.isoformat()
            raise TypeError(f"Object of type {type(obj)} is not JSON serializable")
        
        # Save to file
        with open(file_path, 'w', encoding='utf-8') as f:
            json.dump(data, f, indent=2, ensure_ascii=False, default=json_serializer)
        
        console.print(f"[green]💾 Saved {len(facts)} facts to {file_path}[/green]")
        return str(file_path)
    
    def load_facts(self, stage: str) -> List[ExtractedFact]:
        """Load facts from JSON file."""
        import json
        
        file_path = self.facts_dir / f"{stage}.json"
        
        if not file_path.exists():
            return []
        
        try:
            with open(file_path, 'r', encoding='utf-8') as f:
                data = json.load(f)
            
            facts = []
            for fact_data in data.get("facts", []):
                facts.append(ExtractedFact(**fact_data))
            
            console.print(f"[blue]📂 Loaded {len(facts)} facts from {file_path}[/blue]")
            return facts
            
        except Exception as e:
            console.print(f"[red]❌ Error loading facts from {file_path}: {e}[/red]")
            return []
    
    def load_batch_metadata(self, stage: str) -> Optional[BatchMetadata]:
        """Load batch metadata from JSON file."""
        import json
        
        file_path = self.facts_dir / f"{stage}.json"
        
        if not file_path.exists():
            return None
        
        try:
            with open(file_path, 'r', encoding='utf-8') as f:
                data = json.load(f)
            
            batch_data = data.get("batch_metadata")
            if batch_data:
                return BatchMetadata(**batch_data)
            return None
            
        except Exception as e:
            console.print(f"[red]❌ Error loading batch metadata from {file_path}: {e}[/red]")
            return None
    
    def get_facts_summary(self, stage: str) -> Dict:
        """Get summary of facts data."""
        facts = self.load_facts(stage)
        
        if not facts:
            return {"count": 0, "stage": stage}
        
        # Load config for thresholds
        from .rag_models import RAGConfig
        config = RAGConfig()
        
        # Calculate statistics
        confidences = [fact.extraction_confidence for fact in facts]
        
        summary = {
            "stage": stage,
            "count": len(facts),
            "avg_confidence": sum(confidences) / len(confidences) if confidences else 0,
            "min_confidence": min(confidences) if confidences else 0,
            "max_confidence": max(confidences) if confidences else 0,
            "high_confidence_count": sum(1 for c in confidences if c >= config.high_confidence_threshold),
            "low_confidence_count": sum(1 for c in confidences if c < config.low_confidence_threshold)
        }
        
        return summary


class StandardQueryGenerator:
    """Generator for standard RAG queries from extracted facts."""
    
    def __init__(self, config: RAGConfig):
        self.config = config
        self.llm_provider = create_structured_llm_provider(config.llm_provider)
        self.prompt_template = self._load_prompt_template()
    
    def _load_prompt_template(self) -> str:
        """Load standard query generation prompt template."""
        template_path = Path(self.config.prompt_templates.get("standard_query", "prompts/standard_query.txt"))
        
        if template_path.exists():
            return template_path.read_text(encoding='utf-8')
        
        # Default template if file doesn't exist
        return """Based on the following chunk of text and the extracted fact, generate a natural question that a user might ask to retrieve this information.

Chunk: {chunk_text}

Extracted Fact: {fact_text}

Generate a natural, realistic question that would lead to this fact as the answer. The question should:
1. Be conversational and realistic
2. Not directly copy phrases from the fact
3. Be specific enough to get this fact as the answer
4. Sound like something a real user would ask

Return only the question, no explanation."""
    
    def generate_queries_from_facts(self, facts: List[ExtractedFact], chunks_map: Dict[str, ChunkData]) -> Tuple[List[RAGQuery], BatchMetadata]:
        """Generate standard queries from a list of facts."""
        
        start_time = time.time()
        queries = []
        failure_count = 0
        
        console.print(f"[blue]🔄 Generating standard queries from {len(facts)} facts...[/blue]")
        
        with Progress(
            SpinnerColumn(),
            TextColumn("[progress.description]{task.description}"),
            console=console,
            transient=True
        ) as progress:
            task = progress.add_task("Generating queries...", total=len(facts))
            
            for fact in facts:
                try:
                    chunk = chunks_map.get(fact.chunk_id)
                    if not chunk:
                        console.print(f"[yellow]⚠️  Chunk {fact.chunk_id} not found for fact {fact.fact_id}[/yellow]")
                        failure_count += 1
                        continue
                    
                    query = self._generate_query_from_fact(fact, chunk)
                    if query:
                        queries.append(query)
                    else:
                        failure_count += 1
                        
                    progress.update(task, advance=1)
                    
                except RateLimitExceededException as e:
                    console.print(f"[red]❌ Failed to generate query from fact {fact.fact_id}: {e}[/red]")
                    console.print("[red]🛑 Rate limit exceeded. Stopping processing to avoid further failures.[/red]")
                    console.print("[yellow]💡 Suggestion: Wait for the rate limit to reset or switch to a different provider (--provider ollama)[/yellow]")
                    break
                except Exception as e:
                    console.print(f"[red]❌ Error generating query for fact {fact.fact_id}: {e}[/red]")
                    failure_count += 1
                    progress.update(task, advance=1)
                    continue
        
        end_time = time.time()
        processing_time = end_time - start_time
        
        # Create batch metadata
        batch_metadata = BatchMetadata(
            stage="generated",
            llm_model=getattr(self.llm_provider, 'model_name', 'unknown'),
            provider=self.config.llm_provider,
            prompt_template=self.config.prompt_templates.get("standard_query", "default"),
            llm_params=self.config.llm_params,
            total_items=len(facts),
            success_count=len(queries),
            failure_count=failure_count,
            processing_time_seconds=processing_time,
            custom_metadata={
                "query_type": "standard",
                "source_facts_count": len(facts)
            }
        )
        
        console.print(f"[green]✅ Generated {len(queries)} standard queries successfully[/green]")
        return queries, batch_metadata
    
    def _generate_query_from_fact(self, fact: ExtractedFact, chunk: ChunkData) -> Optional[RAGQuery]:
        """Generate a single standard query from a fact."""
        try:
            # Format prompt
            prompt = self.prompt_template.format(
                chunk_text=chunk.text,
                fact_text=fact.fact_text
            )
            
            # Get structured response
            response = generate_standard_query_structured(self.llm_provider, prompt)
            
            if not response.query or len(response.query.strip()) < 10:
                return None
            
            # Create RAGQuery with UUID
            query = RAGQuery(
                query_text=response.query.strip(),
                source_chunk_ids=[chunk.chunk_id],
                answer_fact=fact.fact_text,
                difficulty="standard",
                realism_score=response.realism_score if hasattr(response, 'realism_score') else None,
                source_fact_id=fact.fact_id,
                reasoning=response.reasoning if hasattr(response, 'reasoning') else None
            )
            
            return query
            
        except Exception as e:
            console.print(f"[red]❌ Failed to generate query from fact {fact.fact_id}: {e}[/red]")
            return None


class QueryDataManager:
    """Manage query data storage and retrieval."""
    
    def __init__(self, project_root: str = "."):
        self.project_root = Path(project_root)
        self.queries_dir = self.project_root / "data" / "queries"
        self.queries_dir.mkdir(parents=True, exist_ok=True)
    
    def save_queries(self, queries: List[RAGQuery], stage: str, batch_metadata: BatchMetadata = None, custom_metadata: Dict[str, Any] = None) -> str:
        """Save queries to JSON file with batch metadata."""
        import json
        
        file_path = self.queries_dir / f"{stage}.json"
        
        # Create or use provided batch metadata
        if batch_metadata is None:
            batch_metadata = BatchMetadata(
                stage=stage,
                llm_model="unknown",
                provider="unknown", 
                prompt_template="unknown",
                total_items=len(queries),
                success_count=len(queries),
                custom_metadata=custom_metadata or {}
            )
        
        # Prepare data with structured metadata
        data = {
            "batch_metadata": batch_metadata.model_dump(),
            "queries": [query.model_dump() for query in queries]
        }
        
        # Custom JSON encoder for datetime objects
        def json_serializer(obj):
            if isinstance(obj, datetime):
                return obj.isoformat()
            raise TypeError(f"Object of type {type(obj)} is not JSON serializable")
        
        # Save to file
        with open(file_path, 'w', encoding='utf-8') as f:
            json.dump(data, f, indent=2, ensure_ascii=False, default=json_serializer)
        
        console.print(f"[green]💾 Saved {len(queries)} queries to {file_path}[/green]")
        return str(file_path)
    
    def load_queries(self, stage: str) -> List[RAGQuery]:
        """Load queries from JSON file."""
        import json
        
        file_path = self.queries_dir / f"{stage}.json"
        
        if not file_path.exists():
            console.print(f"[yellow]📂 No {stage} queries found at {file_path}[/yellow]")
            return []
        
        with open(file_path, 'r', encoding='utf-8') as f:
            data = json.load(f)
        
        queries = []
        for query_data in data.get("queries", []):
            query = RAGQuery(**query_data)
            queries.append(query)
        
        console.print(f"[green]📂 Loaded {len(queries)} queries from {file_path}[/green]")
        return queries
    
    def load_batch_metadata(self, stage: str) -> Optional[BatchMetadata]:
        """Load batch metadata for a stage."""
        import json
        
        file_path = self.queries_dir / f"{stage}.json"
        
        if not file_path.exists():
            return None
        
        with open(file_path, 'r', encoding='utf-8') as f:
            data = json.load(f)
        
        batch_data = data.get("batch_metadata")
        if batch_data:
            return BatchMetadata(**batch_data)
        
        return None
    
    def get_queries_summary(self, stage: str) -> Dict[str, Any]:
        """Get summary statistics for queries."""
        queries = self.load_queries(stage)
        
        if not queries:
            return {"count": 0, "stage": stage}
        
        # Load config for thresholds
        from .rag_models import RAGConfig
        config = RAGConfig()
        
        # Calculate statistics
        realism_scores = [q.realism_score for q in queries if hasattr(q, 'realism_score') and q.realism_score is not None]
        difficulties = [q.difficulty for q in queries if q.difficulty]
        
        from collections import Counter
        difficulty_counts = Counter(difficulties)
        
        summary = {
            "stage": stage,
            "count": len(queries),
            "difficulty_distribution": dict(difficulty_counts),
            "avg_realism_score": sum(realism_scores) / len(realism_scores) if realism_scores else None,
            "min_realism_score": min(realism_scores) if realism_scores else None,
            "max_realism_score": max(realism_scores) if realism_scores else None,
            "high_realism_count": sum(1 for s in realism_scores if s >= config.high_realism_threshold) if realism_scores else 0,
            "low_realism_count": sum(1 for s in realism_scores if s < config.low_realism_threshold) if realism_scores else 0
        }
        
        return summary