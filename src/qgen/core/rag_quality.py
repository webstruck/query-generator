"""RAG query quality filtering and realism scoring system."""

import json
from typing import List, Tuple, Optional, Dict, Any, Callable
from datetime import datetime
from pathlib import Path
from rich.console import Console
from rich.progress import Progress, TaskID

from .rag_models import RAGQuery, RAGConfig, RealismScoreResponse
from .structured_llm import StructuredLLMProvider, RateLimitExceededException
from .llm_api import create_llm_provider

console = Console()


class RAGQueryQualityFilter:
    """LLM-based quality filtering for RAG queries (web + CLI compatible)."""
    
    def __init__(self, config: RAGConfig):
        self.config = config
        self.structured_llm = StructuredLLMProvider(
            provider_name=config.llm_provider,
            **config.llm_params
        )
        self.prompt_template = self._load_prompt_template()
    
    def _load_prompt_template(self) -> str:
        """Load realism scoring prompt template."""
        template_path = Path(self.config.prompt_templates.get("realism_scoring", "prompts/realism_scoring.txt"))
        
        if template_path.exists():
            return template_path.read_text(encoding='utf-8')
        else:
            # Fallback to default prompt
            return self._get_default_realism_prompt()
    
    def _get_default_realism_prompt(self) -> str:
        """Default realism scoring prompt if template file not found."""
        return """Evaluate this RAG query for realism and quality on a scale of 1-5.

Query: {query_text}
Expected Answer: {answer_fact}
Difficulty Level: {difficulty}
Source Chunks: {chunk_count} chunk(s)

Evaluate based on these criteria:
1. **Naturalness**: Does this sound like a real user would ask it?
2. **Language Quality**: Is the language natural, varied, and well-formed?
3. **Complexity Appropriateness**: Is the complexity suitable for the difficulty level?
4. **RAG Utility**: Would this query be useful for evaluating RAG systems?
5. **Answer Alignment**: Does the query naturally lead to the expected answer?

Scoring Guide:
- 1: Clearly artificial, poor language, inappropriate complexity
- 2: Somewhat artificial, basic language issues, complexity mismatch
- 3: Average realism, acceptable language, mostly appropriate complexity
- 4: Good realism, natural language, appropriate complexity
- 5: Excellent realism, very natural language, perfect complexity match

Provide your assessment with detailed reasoning and suggestions for improvement."""
    
    def score_query_realism(self, query: RAGQuery) -> RealismScoreResponse:
        """Score individual query realism using structured LLM output."""
        try:
            # Prepare prompt variables
            prompt_vars = {
                "query_text": query.query_text,
                "answer_fact": query.answer_fact,
                "difficulty": query.difficulty,
                "chunk_count": len(query.source_chunk_ids)
            }
            
            # Format prompt
            formatted_prompt = self.prompt_template.format(**prompt_vars)
            
            # Get structured response
            response = self.structured_llm.generate_structured(
                prompt=formatted_prompt,
                response_model=RealismScoreResponse
            )
            
            return response
            
        except Exception as e:
            console.print(f"[red]Warning: Failed to score query {query.query_id}: {e}[/red]")
            # Return default low score if scoring fails
            return RealismScoreResponse(
                score=1,
                reasoning=f"Failed to score query due to error: {str(e)}",
                improvements=["Query could not be properly evaluated"]
            )
    
    def filter_queries(self, 
                      queries: List[RAGQuery], 
                      progress_callback: Optional[Callable[[int, int, str], None]] = None
                      ) -> Tuple[List[RAGQuery], List[RAGQuery], Dict[str, Any]]:
        """Filter queries based on realism scores with optional progress tracking.
        
        Returns:
            Tuple of (passed_queries, failed_queries, filtering_stats)
        """
        passed_queries = []
        failed_queries = []
        scoring_stats = {
            "total_queries": len(queries),
            "scores": [],
            "score_distribution": {1: 0, 2: 0, 3: 0, 4: 0, 5: 0},
            "avg_score": 0.0,
            "pass_rate": 0.0,
            "filtering_threshold": self.config.min_realism_score,
            "filtered_at": datetime.now().isoformat()
        }
        
        console.print(f"[blue]🎯 Starting quality filtering with threshold {self.config.min_realism_score}[/blue]")
        
        for i, query in enumerate(queries):
            if progress_callback:
                progress_callback(i, len(queries), f"Scoring query {i+1}/{len(queries)}: {query.query_text[:50]}...")
            
            try:
                # Score the query
                score_response = self.score_query_realism(query)
                
                # Update query with scoring results
                query.realism_rating = float(score_response.score)
                query.quality_metadata = {
                    "realism_score": score_response.score,
                    "reasoning": score_response.reasoning,
                    "improvements": score_response.improvements,
                    "scored_at": datetime.now().isoformat(),
                    "scorer_config": {
                        "threshold": self.config.min_realism_score,
                        "model": self.config.llm_provider
                    }
                }
                
                # Collect statistics
                scoring_stats["scores"].append(score_response.score)
                scoring_stats["score_distribution"][score_response.score] += 1
                
                # Filter based on threshold
                if score_response.score >= self.config.min_realism_score:
                    query.status = "approved"
                    passed_queries.append(query)
                else:
                    query.status = "rejected"
                    failed_queries.append(query)
                    
            except RateLimitExceededException as e:
                console.print(f"[red]❌ Failed to score query {query.query_id}: {e}[/red]")
                console.print("[red]🛑 Rate limit exceeded. Stopping processing to avoid further failures.[/red]")
                console.print("[yellow]💡 Suggestion: Wait for the rate limit to reset or switch to a different provider (--provider ollama)[/yellow]")
                break
        
        # Complete final statistics
        if scoring_stats["scores"]:
            scoring_stats["avg_score"] = sum(scoring_stats["scores"]) / len(scoring_stats["scores"])
            scoring_stats["pass_rate"] = len(passed_queries) / len(queries)
        
        # Final progress update
        if progress_callback:
            progress_callback(len(queries), len(queries), f"Filtering complete: {len(passed_queries)}/{len(queries)} passed")
        
        console.print(f"[green]✅ Quality filtering complete: {len(passed_queries)}/{len(queries)} queries passed (pass rate: {scoring_stats['pass_rate']:.1%})[/green]")
        
        return passed_queries, failed_queries, scoring_stats
    
    def batch_score_queries(self, queries: List[RAGQuery]) -> List[RAGQuery]:
        """Score queries without filtering, just add realism ratings."""
        console.print(f"[blue]📊 Scoring {len(queries)} queries for realism...[/blue]")
        
        for i, query in enumerate(queries):
            console.print(f"[dim]Scoring query {i+1}/{len(queries)}...[/dim]")
            
            score_response = self.score_query_realism(query)
            query.realism_rating = float(score_response.score)
            query.quality_metadata = {
                "realism_score": score_response.score,
                "reasoning": score_response.reasoning,
                "improvements": score_response.improvements,
                "scored_at": datetime.now().isoformat()
            }
        
        console.print("[green]✅ Batch scoring complete[/green]")
        return queries
    
    def get_filtering_summary(self, passed: List[RAGQuery], failed: List[RAGQuery], stats: Dict[str, Any]) -> str:
        """Generate human-readable filtering summary."""
        total = len(passed) + len(failed)
        
        summary_lines = [
            f"Quality Filtering Results:",
            f"  • Total queries processed: {total}",
            f"  • Passed threshold ({self.config.min_realism_score}): {len(passed)} ({stats['pass_rate']:.1%})",
            f"  • Failed threshold: {len(failed)} ({(1-stats['pass_rate']):.1%})",
            f"  • Average realism score: {stats['avg_score']:.2f}/5.0",
            "",
            f"Score Distribution:",
        ]
        
        for score in range(1, 6):
            count = stats["score_distribution"][score]
            percentage = (count / total * 100) if total > 0 else 0
            summary_lines.append(f"  • Score {score}: {count} queries ({percentage:.1f}%)")
        
        return "\n".join(summary_lines)


class RAGQueryDataManager:
    """Extended data manager for RAG queries with quality filtering support."""
    
    def __init__(self, project_path: str = "."):
        self.project_path = Path(project_path)
        self.data_dir = self.project_path / "data" / "queries"
        self.data_dir.mkdir(parents=True, exist_ok=True)
    
    def load_queries(self, stage: str) -> List[RAGQuery]:
        """Load RAG queries from specified stage."""
        file_path = self.data_dir / f"{stage}.json"
        
        if not file_path.exists():
            return []
        
        try:
            with open(file_path, 'r', encoding='utf-8') as f:
                data = json.load(f)
                return [RAGQuery(**query_data) for query_data in data.get("queries", [])]
        except Exception as e:
            console.print(f"[red]Error loading queries from {file_path}: {e}[/red]")
            return []
    
    def save_queries(self, queries: List[RAGQuery], stage: str, metadata: Optional[Dict[str, Any]] = None):
        """Save RAG queries to specified stage with metadata."""
        file_path = self.data_dir / f"{stage}.json"
        
        # Prepare data structure
        data = {
            "queries": [query.model_dump() for query in queries],
            "metadata": {
                "count": len(queries),
                "stage": stage,
                "saved_at": datetime.now().isoformat(),
                **(metadata or {})
            }
        }
        
        # Custom JSON encoder for datetime objects
        def json_serializer(obj):
            if isinstance(obj, datetime):
                return obj.isoformat()
            raise TypeError(f"Object of type {type(obj)} is not JSON serializable")
        
        try:
            with open(file_path, 'w', encoding='utf-8') as f:
                json.dump(data, f, indent=2, ensure_ascii=False, default=json_serializer)
            
            console.print(f"[green]💾 Saved {len(queries)} queries to {stage} stage[/green]")
            
        except Exception as e:
            console.print(f"[red]Error saving queries to {file_path}: {e}[/red]")
            raise
    
    def get_query_stats(self) -> Dict[str, Any]:
        """Get comprehensive query statistics for web dashboard."""
        generated_queries = self.load_queries("generated")
        approved_queries = self.load_queries("approved")
        
        stats = {
            "total_generated": len(generated_queries),
            "total_approved": len(approved_queries),
            "approval_rate": len(approved_queries) / len(generated_queries) if generated_queries else 0,
        }
        
        # Quality distribution for approved queries
        if approved_queries:
            scores = [q.realism_rating for q in approved_queries if q.realism_rating is not None]
            if scores:
                stats["quality_stats"] = {
                    "avg_realism_score": sum(scores) / len(scores),
                    "min_score": min(scores),
                    "max_score": max(scores),
                    "scored_queries": len(scores)
                }
        
        # Difficulty breakdown
        difficulty_counts = {}
        for query in approved_queries:
            difficulty = query.difficulty
            difficulty_counts[difficulty] = difficulty_counts.get(difficulty, 0) + 1
        
        stats["difficulty_breakdown"] = difficulty_counts
        
        return stats