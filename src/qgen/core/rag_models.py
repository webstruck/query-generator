from pydantic import BaseModel, Field
from typing import List, Dict, Optional, Any
from datetime import datetime
import yaml
import uuid
import os
from pathlib import Path


class ChunkData(BaseModel):
    """Data model for a text chunk from the knowledge base."""
    chunk_id: str = Field(..., description="Unique identifier for chunk")
    text: str = Field(..., description="Chunk content text")
    source_document: Optional[str] = None
    section: Optional[str] = None
    related_chunks: Optional[List[str]] = []
    custom_metadata: Optional[Dict[str, Any]] = {}
    
    @classmethod
    def __init_subclass__(cls, **kwargs):
        super().__init_subclass__(**kwargs)
    
    @classmethod  
    def model_validate(cls, obj):
        """Custom validation that moves unknown fields to custom_metadata."""
        if not isinstance(obj, dict):
            return super().model_validate(obj)
        
        # Known field names
        known_fields = {'chunk_id', 'text', 'source_document', 'section', 'related_chunks', 'custom_metadata'}
        
        # Separate known and unknown fields
        clean_obj = {}
        extra_fields = {}
        
        for key, value in obj.items():
            if key in known_fields:
                clean_obj[key] = value
            else:
                extra_fields[key] = value
        
        # If there are extra fields, merge them into custom_metadata
        if extra_fields:
            existing_metadata = clean_obj.get('custom_metadata', {})
            if not isinstance(existing_metadata, dict):
                existing_metadata = {}
            
            # Merge extra fields into custom_metadata
            clean_obj['custom_metadata'] = {**existing_metadata, **extra_fields}
        
        return super().model_validate(clean_obj)


class FactSpan(BaseModel):
    """Represents the span of text in a chunk where a fact was extracted."""
    start: Optional[int] = None  # Character start position
    end: Optional[int] = None    # Character end position
    highlighted_text: Optional[str] = None  # The actual text span


class ExtractedFact(BaseModel):
    """Data model for a fact extracted from a chunk."""
    fact_id: str = Field(default_factory=lambda: str(uuid.uuid4()))
    chunk_id: str
    fact_text: str
    extraction_confidence: float
    reasoning: Optional[str] = None  # LLM reasoning for extraction
    span: Optional[FactSpan] = None  # Where in chunk this fact was found
    extracted_at: datetime = Field(default_factory=datetime.now)
    
    def get_chunk_with_highlight(self, chunk_text: str, similarity_threshold: float = None) -> str:
        """Return chunk text with fact highlighted using embedding-based similarity.
        
        Args:
            chunk_text: The chunk text to highlight
            similarity_threshold: Minimum similarity score to highlight a sentence (uses config.highlight_similarity_threshold if None)
            
        Returns:
            Chunk text with matching sentences highlighted
        """
        # Use config value if no threshold provided
        if similarity_threshold is None:
            config = RAGConfig()
            similarity_threshold = config.highlight_similarity_threshold
            
        print(f"🚀 ENTERING get_chunk_with_highlight for fact: '{self.fact_text[:50]}...'")
        print(f"🚀 Chunk text length: {len(chunk_text)}, Threshold: {similarity_threshold}")
        
        try:
            from .embedding_providers import EmbeddingProviderFactory
            import numpy as np
            import re
            
            # Split chunk into sentences
            sentences = re.split(r'[.!?]+', chunk_text)
            sentences = [s.strip() for s in sentences if s.strip()]
            
            if not sentences:
                return chunk_text
            
            # Get embedding provider with fallback
            cache_dir = os.path.join(os.getcwd(), "cache", "embeddings")
            provider = None
            fact_embedding = None
            sentence_embeddings = None
            
            # Try Model2Vec first
            try:
                provider = EmbeddingProviderFactory.get_default_provider(cache_dir=cache_dir)
                print(f"🔧 Using embedding provider: {provider.__class__.__name__}")
                
                # Generate embeddings
                print(f"🔄 Generating embeddings with {provider.__class__.__name__} for fact and {len(sentences)} sentences...")
                fact_embedding = provider.encode([self.fact_text])
                print(f"✅ Fact embedding generated: {fact_embedding.shape}")
                sentence_embeddings = provider.encode(sentences)
                print(f"✅ Sentence embeddings generated: {sentence_embeddings.shape}")
                print(f"📊 Generated embeddings - fact: {fact_embedding.shape}, sentences: {sentence_embeddings.shape}")
                
            except Exception as model2vec_error:
                print(f"⚠️ Model2Vec embedding failed: {model2vec_error}")
                print(f"🔄 Trying sentence-transformers fallback...")
                
                try:
                    provider = EmbeddingProviderFactory.create_provider("sentence-transformers", cache_dir=cache_dir)
                    print(f"✅ Using fallback provider: {provider.__class__.__name__}")
                    
                    # Generate embeddings with sentence-transformers
                    print(f"🔄 Generating embeddings with {provider.__class__.__name__} for fact and {len(sentences)} sentences...")
                    fact_embedding = provider.encode([self.fact_text])
                    print(f"✅ Fact embedding generated: {fact_embedding.shape}")
                    sentence_embeddings = provider.encode(sentences)
                    print(f"✅ Sentence embeddings generated: {sentence_embeddings.shape}")
                    print(f"📊 Generated embeddings - fact: {fact_embedding.shape}, sentences: {sentence_embeddings.shape}")
                    
                except Exception as sentence_transformers_error:
                    print(f"❌ Sentence-transformers fallback also failed: {sentence_transformers_error}")
                    print(f"❌ Error type: {type(sentence_transformers_error).__name__}")
                    # Return original text without highlighting if all embedding methods fail
                    return chunk_text
            
            # Calculate similarities and highlight sentences above threshold
            highlighted_text = chunk_text
            
            print(f"🔍 DEBUG: Highlighting with threshold {similarity_threshold}")
            print(f"📄 Fact text: '{self.fact_text}'")
            print(f"📄 Chunk sentences ({len(sentences)}):")
            
            max_similarity = 0.0
            
            for i, sent_emb in enumerate(sentence_embeddings):
                # Cosine similarity
                similarity = np.dot(fact_embedding[0], sent_emb) / (
                    np.linalg.norm(fact_embedding[0]) * np.linalg.norm(sent_emb)
                )
                
                sentence = sentences[i]
                print(f"  {i+1}: '{sentence}' -> similarity: {similarity:.4f} {'✅ HIGHLIGHT' if similarity >= similarity_threshold else '❌ skip'}")
                
                # Track maximum similarity
                max_similarity = max(max_similarity, similarity)
                
                # Highlight if above threshold
                if similarity >= similarity_threshold:
                    # Find the sentence in original text (with punctuation) using fuzzy matching
                    highlighted_sentence = f"[bold yellow on blue]{sentence}[/bold yellow on blue]"
                    
                    # Replace the sentence in the chunk text
                    # Use a more robust replacement that handles punctuation
                    import re
                    # Escape special regex characters in sentence
                    escaped_sentence = re.escape(sentence)
                    # Match the sentence with optional punctuation at the end
                    pattern = escaped_sentence + r'[.!?]*'
                    old_highlighted_text = highlighted_text
                    highlighted_text = re.sub(pattern, highlighted_sentence, highlighted_text, count=1)
                    
                    if highlighted_text != old_highlighted_text:
                        print(f"    ✅ Successfully highlighted sentence {i+1}")
                    else:
                        print(f"    ❌ Failed to replace sentence {i+1} in text")
            
            # Summary
            print(f"📊 SUMMARY: Max similarity: {max_similarity:.4f}, Threshold: {similarity_threshold}")
            print(f"🎯 Final result has highlighting: {'[bold yellow on blue]' in highlighted_text}")
            
            # Test what would happen with different thresholds
            print(f"📈 Threshold Analysis:")
            test_thresholds = [0.5, 0.6, 0.65, 0.7, 0.75, 0.8]
            for test_thresh in test_thresholds:
                count = sum(1 for i, sent_emb in enumerate(sentence_embeddings) 
                           if (np.dot(fact_embedding[0], sent_emb) / 
                               (np.linalg.norm(fact_embedding[0]) * np.linalg.norm(sent_emb))) >= test_thresh)
                print(f"  Threshold {test_thresh}: {count} sentences would be highlighted")
            
            print("=" * 60)
            
            return highlighted_text
            
        except Exception:
            # If embedding fails, return original text without highlighting
            return chunk_text


class BatchMetadata(BaseModel):
    """Global metadata for a batch of fact extractions or query generations."""
    batch_id: str = Field(default_factory=lambda: str(uuid.uuid4()))
    stage: str  # "generated", "approved", etc.
    created_at: datetime = Field(default_factory=datetime.now)
    llm_model: str  # Changed from model_used to avoid Pydantic conflict
    provider: str
    prompt_template: str
    llm_params: Dict[str, Any] = {}
    total_items: int
    success_count: int
    failure_count: int = 0
    processing_time_seconds: Optional[float] = None
    custom_metadata: Dict[str, Any] = {}
    
    class Config:
        json_encoders = {
            datetime: lambda v: v.isoformat()
        }


class RAGQuery(BaseModel):
    """Data model for a generated RAG query."""
    query_id: str = Field(default_factory=lambda: str(uuid.uuid4()))
    query_text: str
    source_chunk_ids: List[str]  # Multiple for multi-hop
    answer_fact: str
    difficulty: str  # "standard", "adversarial", "multi-hop"
    realism_rating: Optional[float] = None
    reasoning: Optional[str] = None  # LLM reasoning for generation
    generated_at: datetime = Field(default_factory=datetime.now)
    status: str = "pending"  # "pending", "approved", "rejected"
    quality_metadata: Optional[Dict[str, Any]] = None  # Quality filtering metadata
    generation_metadata: Optional[Dict[str, Any]] = None  # Generation process metadata


class RAGConfig(BaseModel):
    """Configuration for RAG query generation."""
    # Generation ratios
    standard_ratio: float = 0.6
    adversarial_ratio: float = 0.3
    multihop_ratio: float = 0.1
    
    # Multi-hop settings
    multihop_chunk_range: List[int] = [2, 4]
    multihop_queries_per_combination: int = 2
    
    # Adversarial settings
    similarity_threshold: float = 0.7
    
    # Quality control
    min_realism_score: float = 3.5
    high_confidence_threshold: float = 0.8  # Threshold for "high confidence" statistics
    low_confidence_threshold: float = 0.6   # Threshold for "low confidence" statistics
    high_realism_threshold: float = 4.0     # Threshold for "high realism" statistics  
    low_realism_threshold: float = 3.0      # Threshold for "low realism" statistics
    
    # Embedding settings
    embedding_model: str = "model2vec"
    embedding_batch_size: int = 32
    cache_embeddings: bool = True
    
    # Highlighting settings
    highlight_similarity_threshold: float = 0.8  # Minimum similarity to highlight sentences
    
    # LLM settings
    llm_provider: str = "openai"
    llm_params: Dict[str, Any] = {}
    
    # Prompt template paths
    prompt_templates: Dict[str, str] = {
        "fact_extraction": "prompts/fact_extraction.txt",
        "standard_query": "prompts/standard_query_generation.txt", 
        "adversarial_query": "prompts/adversarial_query_generation.txt",
        "multihop_query": "prompts/multihop_query_generation.txt",
        "realism_scoring": "prompts/realism_scoring.txt"
    }
    
    @classmethod
    def load_from_file(cls, config_path: str) -> "RAGConfig":
        """Load RAG configuration from YAML file."""
        with open(config_path, 'r') as f:
            config_data = yaml.safe_load(f)
        return cls(**config_data)
    
    def save_to_file(self, config_path: str):
        """Save RAG configuration to YAML file."""
        with open(config_path, 'w') as f:
            yaml.dump(self.model_dump(), f, default_flow_style=False)


# =============================================================================
# INSTRUCTOR STRUCTURED RESPONSE MODELS
# These models define the expected structure of LLM responses for reliable parsing
# =============================================================================

class FactExtractionResponse(BaseModel):
    """Structured response for fact extraction from chunks."""
    fact: str = Field(..., description="The extracted salient fact from the chunk")
    confidence: float = Field(..., ge=0.0, le=1.0, description="Confidence score from 0.0 to 1.0")
    reasoning: str = Field(..., description="Brief explanation of why this fact was chosen")
    span_start: Optional[int] = Field(None, description="Character start position of fact in chunk text")
    span_end: Optional[int] = Field(None, description="Character end position of fact in chunk text")
    highlighted_text: Optional[str] = Field(None, description="The actual text span that supports this fact")


class StandardQueryResponse(BaseModel):
    """Structured response for standard query generation."""
    query: str = Field(..., description="The generated user query")
    reasoning: str = Field(..., description="Brief explanation of the query design")


class AdversarialQueryResponse(BaseModel):
    """Structured response for adversarial query generation."""
    query: str = Field(..., description="The adversarial query that might confuse retrieval")
    reasoning: str = Field(..., description="Explanation of the adversarial strategy used")
    distractor_terms: List[str] = Field(default=[], description="Key terms from distractor chunks used in query")


class MultiHopQueryResponse(BaseModel):
    """Structured response for multi-hop query generation."""
    query: str = Field(..., description="The multi-hop query requiring multiple chunks")
    answer: str = Field(..., description="The complete answer combining all chunks")
    reasoning: str = Field(..., description="Explanation of how the query requires multiple chunks")
    chunk_roles: List[str] = Field(..., description="Description of what each chunk contributes to the answer")


class RealismScoreResponse(BaseModel):
    """Structured response for query realism scoring."""
    score: int = Field(..., ge=1, le=5, description="Realism score from 1 (artificial) to 5 (very realistic)")
    reasoning: str = Field(..., description="Detailed explanation of the score")
    improvements: List[str] = Field(default=[], description="Suggestions to make the query more realistic")