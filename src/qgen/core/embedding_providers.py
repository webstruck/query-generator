"""Embedding provider abstraction for different embedding models."""

# Set SSL certificates early - before any network imports
import os
import certifi

# Configure SSL certificate environment variables globally
cert_file = certifi.where()
os.environ['SSL_CERT_FILE'] = cert_file
os.environ['REQUESTS_CA_BUNDLE'] = cert_file
os.environ['CURL_CA_BUNDLE'] = cert_file

from abc import ABC, abstractmethod
from typing import List, Union, Optional, Any
import threading
import numpy as np
import hashlib
import pickle
from pathlib import Path


class EmbeddingCache:
    """Simple cache for embedding computations to avoid recomputation."""
    
    def __init__(self, cache_dir: str):
        self.cache_dir = Path(cache_dir)
        self.cache_dir.mkdir(parents=True, exist_ok=True)
    
    def _get_cache_path(self, text: str, model_name: str) -> Path:
        """Generate cache file path for text and model."""
        text_hash = hashlib.md5(f"{model_name}:{text}".encode()).hexdigest()
        return self.cache_dir / f"{text_hash}.pkl"
    
    def get(self, text: str, model_name: str) -> Optional[np.ndarray]:
        """Retrieve cached embedding if available."""
        cache_path = self._get_cache_path(text, model_name)
        if cache_path.exists():
            try:
                with open(cache_path, 'rb') as f:
                    return pickle.load(f)
            except (pickle.PickleError, IOError):
                # If cache is corrupted, return None to recompute
                return None
        return None
    
    def set(self, text: str, model_name: str, embedding: np.ndarray):
        """Store embedding in cache."""
        try:
            cache_path = self._get_cache_path(text, model_name)
            with open(cache_path, 'wb') as f:
                pickle.dump(embedding, f)
        except (pickle.PickleError, IOError, OSError):
            # Silently fail if caching doesn't work
            pass


class BaseEmbeddingProvider(ABC):
    """Abstract base class for embedding providers."""
    
    def __init__(self, cache: Optional[EmbeddingCache] = None):
        self.cache = cache
    
    def encode(self, texts: Union[str, List[str]]) -> np.ndarray:
        """Encode text(s) into embeddings with caching support.
        
        Args:
            texts: Single text string or list of text strings
            
        Returns:
            numpy array of embeddings
        """
        if isinstance(texts, str):
            texts = [texts]
            return_single = True
        else:
            return_single = False
        
        embeddings = []
        texts_to_compute = []
        indices_to_compute = []
        
        # Check cache for each text
        for i, text in enumerate(texts):
            if self.cache:
                cached_embedding = self.cache.get(text, self.get_model_name())
                if cached_embedding is not None:
                    embeddings.append(cached_embedding)
                    continue
            
            # Track texts that need computation
            texts_to_compute.append(text)
            indices_to_compute.append(i)
            embeddings.append(None)  # Placeholder
        
        # Compute embeddings for uncached texts
        if texts_to_compute:
            computed_embeddings = self._encode_batch(texts_to_compute)
            
            # Fill in computed embeddings and cache them
            for j, computed_embedding in enumerate(computed_embeddings):
                original_idx = indices_to_compute[j]
                embeddings[original_idx] = computed_embedding
                
                # Cache the computed embedding
                if self.cache:
                    self.cache.set(texts[original_idx], self.get_model_name(), computed_embedding)
        
        result = np.array(embeddings)
        return result[0] if return_single else result
    
    @abstractmethod
    def _encode_batch(self, texts: List[str]) -> np.ndarray:
        """Encode a batch of texts into embeddings (without caching logic).
        
        Args:
            texts: List of text strings
            
        Returns:
            numpy array of embeddings
        """
        pass
    
    @abstractmethod
    def get_model_name(self) -> str:
        """Get the model name for this provider."""
        pass
    
    @abstractmethod
    def is_available(self) -> bool:
        """Check if this provider is available (dependencies installed)."""
        pass


class Model2VecProvider(BaseEmbeddingProvider):
    """Fast static embeddings provider using model2vec."""
    
    def __init__(self, model_name: str = "minishlab/potion-base-8M", cache: Optional[EmbeddingCache] = None):
        super().__init__(cache)
        self.model_name = model_name
        self._model = None
        self._lock = threading.Lock()
    
    def _get_model(self):
        """Lazy load and cache the model."""
        if self._model is None:
            with self._lock:
                if self._model is None:
                    try:
                        # Apply SSL fix globally
                        self._apply_ssl_fix()
                        
                        from model2vec import StaticModel
                        self._model = StaticModel.from_pretrained(self.model_name)
                            
                    except ImportError:
                        raise ImportError("model2vec not installed. Install with: pip install model2vec")
                    except Exception as e:
                        raise RuntimeError(f"Failed to load model2vec model '{self.model_name}': {e}")
        return self._model
    
    def _apply_ssl_fix(self):
        """Apply SSL certificate fix using environment variables."""
        import certifi
        import os
        
        # Set SSL certificate environment variables to certifi bundle
        cert_file = certifi.where()
        os.environ['SSL_CERT_FILE'] = cert_file
        os.environ['REQUESTS_CA_BUNDLE'] = cert_file
        os.environ['CURL_CA_BUNDLE'] = cert_file
        
        print(f"🔧 SSL certificates set to: {cert_file}")
        print(f"   SSL_CERT_FILE: {os.environ.get('SSL_CERT_FILE')}")
        print(f"   REQUESTS_CA_BUNDLE: {os.environ.get('REQUESTS_CA_BUNDLE')}")
        print(f"   CURL_CA_BUNDLE: {os.environ.get('CURL_CA_BUNDLE')}")
        
    def _encode_batch(self, texts: List[str]) -> np.ndarray:
        """Encode texts using model2vec static embeddings."""
        model = self._get_model()
        embeddings = model.encode(texts)
        return embeddings
    
    def get_model_name(self) -> str:
        return f"model2vec:{self.model_name}"
    
    def is_available(self) -> bool:
        """Check if model2vec is available."""
        try:
            import model2vec
            return True
        except ImportError:
            return False


class SentenceTransformerProvider(BaseEmbeddingProvider):
    """Sentence transformer embeddings provider."""
    
    def __init__(self, model_name: str = "sentence-transformers/all-MiniLM-L6-v2", cache: Optional[EmbeddingCache] = None):
        super().__init__(cache)
        self.model_name = model_name
        self._model = None
        self._lock = threading.Lock()
    
    def _get_model(self):
        """Lazy load and cache the model."""
        if self._model is None:
            with self._lock:
                if self._model is None:
                    try:
                        # Apply SSL fix globally
                        self._apply_ssl_fix()
                        
                        from sentence_transformers import SentenceTransformer
                        self._model = SentenceTransformer(self.model_name)
                            
                    except ImportError:
                        raise ImportError("sentence-transformers not installed. Install with: pip install sentence-transformers")
                    except Exception as e:
                        raise RuntimeError(f"Failed to load sentence-transformer model '{self.model_name}': {e}")
        return self._model
    
    def _apply_ssl_fix(self):
        """Apply SSL certificate fix using environment variables."""
        import certifi
        import os
        
        # Set SSL certificate environment variables to certifi bundle
        cert_file = certifi.where()
        os.environ['SSL_CERT_FILE'] = cert_file
        os.environ['REQUESTS_CA_BUNDLE'] = cert_file
        os.environ['CURL_CA_BUNDLE'] = cert_file
        
        print(f"🔧 SSL certificates set to: {cert_file}")
        print(f"   SSL_CERT_FILE: {os.environ.get('SSL_CERT_FILE')}")
        print(f"   REQUESTS_CA_BUNDLE: {os.environ.get('REQUESTS_CA_BUNDLE')}")
        print(f"   CURL_CA_BUNDLE: {os.environ.get('CURL_CA_BUNDLE')}")
        
    def _encode_batch(self, texts: List[str]) -> np.ndarray:
        """Encode texts using sentence transformers."""
        model = self._get_model()
        embeddings = model.encode(texts)
        return embeddings
    
    def get_model_name(self) -> str:
        return f"sentence-transformers:{self.model_name}"
    
    def is_available(self) -> bool:
        """Check if sentence-transformers is available."""
        try:
            import sentence_transformers
            return True
        except ImportError:
            return False




class EmbeddingProviderFactory:
    """Factory for creating embedding providers with fallback logic."""
    
    @staticmethod
    def create_provider(preferred_provider: str = "model2vec", cache_dir: Optional[str] = None) -> BaseEmbeddingProvider:
        """Create an embedding provider with fallback.
        
        Args:
            preferred_provider: Preferred provider ("model2vec" or "sentence-transformers")
            
        Returns:
            Best available embedding provider
            
        Raises:
            RuntimeError: If no embedding providers are available
        """
        providers = []
        
        if preferred_provider == "model2vec":
            providers = [
                ("model2vec", Model2VecProvider),
                ("sentence-transformers", SentenceTransformerProvider)
            ]
        elif preferred_provider == "sentence-transformers":
            providers = [
                ("sentence-transformers", SentenceTransformerProvider),
                ("model2vec", Model2VecProvider)
            ]
        else:
            # Default: model2vec first, then sentence-transformers
            providers = [
                ("model2vec", Model2VecProvider),
                ("sentence-transformers", SentenceTransformerProvider)
            ]
        
        cache = EmbeddingCache(cache_dir) if cache_dir else None
        
        for _, provider_class in providers:
            provider = provider_class(cache=cache)
            if provider.is_available():
                return provider
        
        # If no providers available, raise error with helpful message
        raise RuntimeError(
            "No embedding providers available. Please install one of:\n"
            "  pip install model2vec         # Fast static embeddings (recommended)\n"
            "  pip install sentence-transformers  # Comprehensive transformers"
        )
    
    @staticmethod
    def get_default_provider(cache_dir: Optional[str] = None) -> BaseEmbeddingProvider:
        """Get the default embedding provider (model2vec with fallback)."""
        return EmbeddingProviderFactory.create_provider("model2vec", cache_dir=cache_dir)