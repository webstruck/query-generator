"""Advanced adversarial and multi-hop query generation for RAG evaluation."""

import random
import numpy as np
from typing import List, Dict, Optional, Tuple, Set
from datetime import datetime
from rich.console import Console
from rich.progress import Progress

from .rag_models import ChunkData, ExtractedFact, RAGQuery, RAGConfig
from .embedding_providers import EmbeddingProviderFactory
from .structured_llm import StructuredLLMProvider
from .llm_api import create_llm_provider

console = Console()


class ChunkCombinationFinder:
    """Finds optimal chunk combinations for multi-hop adversarial queries."""
    
    def __init__(self, config: RAGConfig, embedding_provider):
        self.config = config
        self.embedding_provider = embedding_provider
        
    def find_multihop_combinations(self, facts: List[ExtractedFact], 
                                 chunks_map: Dict[str, ChunkData]) -> List[List[str]]:
        """Find chunk combinations that work well for multi-hop adversarial queries."""
        combinations = []
        
        # Strategy 1: Use explicit related_chunks relationships
        explicit_combinations = self._find_explicit_combinations(facts, chunks_map)
        combinations.extend(explicit_combinations)
        
        # Strategy 2: Use semantic similarity for implicit relationships
        semantic_combinations = self._find_semantic_combinations(facts, chunks_map)
        combinations.extend(semantic_combinations)
        
        # Remove duplicates and validate
        unique_combinations = self._deduplicate_combinations(combinations)
        valid_combinations = self._validate_combinations(unique_combinations, chunks_map)
        
        console.print(f"[blue]🔗 Found {len(valid_combinations)} valid chunk combinations for multi-hop queries[/blue]")
        return valid_combinations
    
    def _find_explicit_combinations(self, facts: List[ExtractedFact], 
                                  chunks_map: Dict[str, ChunkData]) -> List[List[str]]:
        """Find combinations using explicit related_chunks relationships."""
        combinations = []
        
        for fact in facts:
            chunk = chunks_map.get(fact.chunk_id)
            if not chunk or not chunk.related_chunks:
                continue
                
            # Build combinations from related chunks
            for related_id in chunk.related_chunks:
                if related_id not in chunks_map:
                    continue
                    
                # Start with primary chunk + one related
                base_combo = [chunk.chunk_id, related_id]
                
                # Expand to target size range
                min_size, max_size = self.config.multihop_chunk_range
                target_size = random.randint(min_size, max_size)
                
                # Add more related chunks if available
                related_chunk = chunks_map[related_id]
                available_chunks = set(chunk.related_chunks + (related_chunk.related_chunks or []))
                available_chunks -= {chunk.chunk_id, related_id}  # Remove already used
                
                while len(base_combo) < target_size and available_chunks:
                    next_chunk = available_chunks.pop()
                    if next_chunk in chunks_map:
                        base_combo.append(next_chunk)
                
                if len(base_combo) >= min_size:
                    combinations.append(base_combo)
        
        return combinations
    
    def _find_semantic_combinations(self, facts: List[ExtractedFact], 
                                  chunks_map: Dict[str, ChunkData]) -> List[List[str]]:
        """Find combinations using semantic similarity when no explicit relations exist."""
        combinations = []
        
        # Pre-compute all chunk embeddings
        chunk_embeddings = self._compute_chunk_embeddings(chunks_map)
        
        for fact in facts:
            chunk = chunks_map.get(fact.chunk_id)
            if not chunk:
                continue
                
            # Skip if this chunk already has explicit relationships
            if chunk.related_chunks:
                continue
                
            # Find semantically similar chunks
            similar_chunks = self._find_similar_chunks(
                chunk, chunks_map, chunk_embeddings
            )
            
            if len(similar_chunks) >= 1:  # Need at least 1 similar chunk for multi-hop
                min_size, max_size = self.config.multihop_chunk_range
                target_size = random.randint(min_size, max_size)
                
                # Build combination starting with the fact's chunk
                combination = [chunk.chunk_id]
                
                # Add similar chunks up to target size
                for similar_chunk, similarity in similar_chunks[:target_size-1]:
                    combination.append(similar_chunk.chunk_id)
                
                if len(combination) >= min_size:
                    combinations.append(combination)
        
        return combinations
    
    def _compute_chunk_embeddings(self, chunks_map: Dict[str, ChunkData]) -> Dict[str, np.ndarray]:
        """Pre-compute embeddings for all chunks with caching."""
        console.print("[dim]🔢 Computing chunk embeddings for similarity analysis...[/dim]")
        
        chunk_texts = [chunk.text for chunk in chunks_map.values()]
        chunk_ids = list(chunks_map.keys())
        
        # Use the embedding provider with caching
        embeddings = self.embedding_provider.encode(chunk_texts)
        
        return dict(zip(chunk_ids, embeddings))
    
    def _find_similar_chunks(self, target_chunk: ChunkData, 
                           chunks_map: Dict[str, ChunkData],
                           embeddings_map: Dict[str, np.ndarray]) -> List[Tuple[ChunkData, float]]:
        """Find chunks similar to target chunk using embedding similarity."""
        target_embedding = embeddings_map[target_chunk.chunk_id]
        similar_chunks = []
        
        for chunk_id, chunk in chunks_map.items():
            if chunk_id == target_chunk.chunk_id:
                continue
                
            chunk_embedding = embeddings_map[chunk_id]
            
            # Compute cosine similarity
            similarity = np.dot(target_embedding, chunk_embedding) / (
                np.linalg.norm(target_embedding) * np.linalg.norm(chunk_embedding)
            )
            
            # Use a slightly lower threshold for multi-hop (want related but not identical)
            multihop_threshold = self.config.similarity_threshold * 0.8
            if similarity >= multihop_threshold:
                similar_chunks.append((chunk, similarity))
        
        # Sort by similarity descending
        similar_chunks.sort(key=lambda x: x[1], reverse=True)
        return similar_chunks
    
    def _deduplicate_combinations(self, combinations: List[List[str]]) -> List[List[str]]:
        """Remove duplicate combinations."""
        unique_combinations = []
        seen_combinations = set()
        
        for combo in combinations:
            # Sort to handle different orderings of same chunks
            sorted_combo = tuple(sorted(combo))
            if sorted_combo not in seen_combinations:
                seen_combinations.add(sorted_combo)
                unique_combinations.append(combo)
        
        return unique_combinations
    
    def _validate_combinations(self, combinations: List[List[str]], 
                             chunks_map: Dict[str, ChunkData]) -> List[List[str]]:
        """Validate that all chunk IDs in combinations exist."""
        valid_combinations = []
        
        for combo in combinations:
            if all(chunk_id in chunks_map for chunk_id in combo):
                valid_combinations.append(combo)
        
        return valid_combinations


class AdversarialMultiHopGenerator:
    """Generates challenging multi-hop queries that require multiple chunks to answer."""
    
    def __init__(self, config: RAGConfig):
        self.config = config
        self.llm_provider = create_llm_provider(config.llm_provider)
        
        # Set up embedding provider with caching
        cache_dir = "cache/embeddings"
        self.embedding_provider = EmbeddingProviderFactory.get_default_provider(cache_dir=cache_dir)
        
        # Initialize chunk combination finder
        self.combination_finder = ChunkCombinationFinder(config, self.embedding_provider)
        
        # Load prompt template
        self.prompt_template = self._load_prompt_template()
    
    def generate_multihop_queries(self, facts: List[ExtractedFact], 
                                chunks_map: Dict[str, ChunkData]) -> List[RAGQuery]:
        """Generate adversarial multi-hop queries from facts and chunks."""
        
        # Find optimal chunk combinations
        combinations = self.combination_finder.find_multihop_combinations(facts, chunks_map)
        
        if not combinations:
            console.print("[yellow]⚠️  No suitable chunk combinations found for multi-hop queries[/yellow]")
            return []
        
        queries = []
        
        with Progress() as progress:
            task = progress.add_task(
                "Generating adversarial multi-hop queries...", 
                total=len(combinations) * self.config.multihop_queries_per_combination
            )
            
            for combination in combinations:
                # Generate multiple queries per combination
                for i in range(self.config.multihop_queries_per_combination):
                    try:
                        query = self._generate_single_multihop_query(combination, chunks_map, facts)
                        if query:
                            queries.append(query)
                        progress.update(task, advance=1)
                    except Exception as e:
                        console.print(f"[red]❌ Error generating multi-hop query: {e}[/red]")
                        progress.update(task, advance=1)
                        continue
        
        console.print(f"[green]✅ Generated {len(queries)} adversarial multi-hop queries[/green]")
        return queries
    
    def _generate_single_multihop_query(self, chunk_ids: List[str], 
                                      chunks_map: Dict[str, ChunkData],
                                      facts: List[ExtractedFact]) -> Optional[RAGQuery]:
        """Generate a single adversarial multi-hop query from chunk combination."""
        
        # Get chunks for this combination
        chunks = [chunks_map[chunk_id] for chunk_id in chunk_ids]
        
        # Find relevant facts from these chunks
        relevant_facts = [f for f in facts if f.chunk_id in chunk_ids]
        
        # Create context for LLM prompt
        chunk_contexts = []
        for i, chunk in enumerate(chunks, 1):
            chunk_facts = [f.fact_text for f in relevant_facts if f.chunk_id == chunk.chunk_id]
            chunk_context = f"Chunk {i} (ID: {chunk.chunk_id}):\nText: {chunk.text}"
            if chunk_facts:
                chunk_context += f"\nKey Facts: {'; '.join(chunk_facts)}"
            chunk_contexts.append(chunk_context)
        
        # Prepare prompt for multi-hop query generation
        prompt = self.prompt_template.format(
            num_chunks=len(chunks),
            chunk_contexts="\n\n".join(chunk_contexts),
            chunk_ids=", ".join(chunk_ids),
            difficulty_instruction="Create an adversarial query that requires combining information from ALL chunks and might be challenging for retrieval systems."
        )
        
        try:
            # Generate query using LLM
            response = self.llm_provider.generate_text(prompt, **self.config.llm_params)
            
            # Parse response
            query_text, answer_fact, reasoning = self._parse_multihop_response(response)
            
            if not query_text or not answer_fact:
                return None
            
            # Create RAG query
            query = RAGQuery(
                query_id=f"mhop_adv_{datetime.now().strftime('%Y%m%d_%H%M%S')}_{random.randint(1000,9999)}",
                query_text=query_text,
                source_chunk_ids=chunk_ids,
                answer_fact=answer_fact,
                difficulty="multi-hop",
                reasoning=reasoning,
                generated_at=datetime.now(),
                status="pending"
            )
            
            return query
            
        except Exception as e:
            console.print(f"[red]❌ Error in LLM generation: {e}[/red]")
            return None
    
    def _load_prompt_template(self) -> str:
        """Load the multi-hop query generation prompt template."""
        template_path = self.config.prompt_templates.get("multihop_query", "prompts/multihop_query_generation.txt")
        
        try:
            with open(template_path, 'r', encoding='utf-8') as f:
                return f.read()
        except FileNotFoundError:
            # Return default template if file not found
            return self._get_default_multihop_template()
    
    def _get_default_multihop_template(self) -> str:
        """Default multi-hop query generation template."""
        return """You are an expert at creating challenging multi-hop queries for RAG evaluation.

Given {num_chunks} related chunks, create an adversarial question that:
1. Requires information from ALL {num_chunks} chunks to answer completely
2. Is challenging for retrieval systems (might retrieve partial information)
3. Sounds natural and realistic - something a real user would ask
4. Tests the system's ability to synthesize information across multiple sources

Chunks:
{chunk_contexts}

{difficulty_instruction}

Requirements:
- The question must be answerable only by combining facts from multiple chunks
- Make it realistic - something a real user would ask
- Include some complexity that makes it challenging for retrieval
- Ensure all chunks contribute essential information to the answer

Provide your response in this format:
QUERY: [The multi-hop question that requires all chunks]
ANSWER: [Complete answer combining information from all chunks]
REASONING: [Brief explanation of why this query requires all chunks and what makes it adversarial]
"""
    
    def _parse_multihop_response(self, response: str) -> Tuple[Optional[str], Optional[str], Optional[str]]:
        """Parse LLM response to extract query, answer, and reasoning."""
        import re
        
        # Extract query
        query_match = re.search(r'QUERY:\s*(.+?)(?=\nANSWER:|$)', response, re.DOTALL)
        query_text = query_match.group(1).strip() if query_match else None
        
        # Extract answer
        answer_match = re.search(r'ANSWER:\s*(.+?)(?=\nREASONING:|$)', response, re.DOTALL)
        answer_fact = answer_match.group(1).strip() if answer_match else None
        
        # Extract reasoning
        reasoning_match = re.search(r'REASONING:\s*(.+?)$', response, re.DOTALL)
        reasoning = reasoning_match.group(1).strip() if reasoning_match else None
        
        return query_text, answer_fact, reasoning


def generate_adversarial_multihop_queries(config: RAGConfig, facts: List[ExtractedFact], 
                                        chunks_map: Dict[str, ChunkData]) -> List[RAGQuery]:
    """Main function to generate adversarial multi-hop queries."""
    generator = AdversarialMultiHopGenerator(config)
    return generator.generate_multihop_queries(facts, chunks_map)