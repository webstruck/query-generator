"""Structured LLM API integration using instructor for reliable parsing."""

from typing import Type, TypeVar, Any, Dict, Optional
import instructor
from openai import OpenAI
from pydantic import BaseModel

from .llm_api import create_llm_provider
from .env import (
    get_openai_config, 
    get_azure_openai_config, 
    get_github_models_config,
    get_ollama_config,
    has_openai_config,
    has_azure_openai_config, 
    has_github_models_config,
    has_ollama_config
)

T = TypeVar('T', bound=BaseModel)


class StructuredLLMProvider:
    """LLM provider that returns structured responses using instructor."""
    
    def __init__(self, provider_name: str, **kwargs):
        self.provider_name = provider_name
        
        # Get provider configuration
        if provider_name == "openai":
            self.provider_info = get_openai_config()
        elif provider_name == "azure":
            self.provider_info = get_azure_openai_config()
        elif provider_name == "github":
            self.provider_info = get_github_models_config()
        elif provider_name == "ollama":
            self.provider_info = get_ollama_config()
        else:
            raise ValueError(f"Unsupported provider: {provider_name}")
        
        # Create base LLM provider for compatibility
        self.base_provider = create_llm_provider(provider_name, **kwargs)
        
        # Initialize instructor-patched client
        self._setup_instructor_client()
    
    # Simple cache for remembering which models need JSON mode
    _json_mode_cache = set()
    
    def _needs_json_mode(self, model_name: str) -> bool:
        """Check if we've learned that this model needs JSON mode."""
        return model_name in self._json_mode_cache
    
    def _remember_json_mode(self, model_name: str):
        """Remember that this model needs JSON mode."""
        self._json_mode_cache.add(model_name)

    def _setup_instructor_client(self):
        """Set up the instructor-patched OpenAI client."""
        if self.provider_name == "openai":
            from openai import OpenAI
            client_kwargs = {"api_key": self.provider_info.get("api_key")}
            if self.provider_info.get("base_url"):
                client_kwargs["base_url"] = self.provider_info.get("base_url")
            
            raw_client = OpenAI(**client_kwargs)
            
            # Check if we already know this model needs JSON mode
            model = self.provider_info.get("model", "gpt-3.5-turbo")
            if self._needs_json_mode(model):
                self.client = instructor.from_openai(raw_client, mode=instructor.Mode.JSON)
            else:
                self.client = instructor.from_openai(raw_client)  # Default TOOLS mode
            return
            
        elif self.provider_name == "azure":
            from openai import AzureOpenAI
            raw_client = AzureOpenAI(
                api_key=self.provider_info.get("api_key"),
                api_version=self.provider_info.get("api_version", "2024-02-01"),
                azure_endpoint=self.provider_info.get("azure_endpoint")
            )
            self.client = instructor.from_openai(raw_client)
            
        elif self.provider_name == "github":
            from openai import OpenAI
            raw_client = OpenAI(
                api_key=self.provider_info.get("api_key"),
                base_url="https://models.inference.ai.azure.com"
            )
            self.client = instructor.from_openai(raw_client)
            
        elif self.provider_name == "ollama":
            from openai import OpenAI
            base_url = self.provider_info.get("base_url")
            # Ensure base_url ends with /v1/ for OpenAI compatibility
            if not base_url.endswith('/'):
                base_url += '/'
            if not base_url.endswith('v1/'):
                base_url += 'v1/'
            
            raw_client = OpenAI(
                api_key="ollama",  # Required but ignored by Ollama
                base_url=base_url
            )
            
            # Ollama models typically need JSON mode
            self.client = instructor.from_openai(raw_client, mode=instructor.Mode.JSON)
            
        else:
            raise ValueError(f"Unsupported provider: {self.provider_name}")
    
    def generate_structured(
        self, 
        prompt: str, 
        response_model: Type[T],
        model_name: Optional[str] = None,
        **llm_params
    ) -> T:
        """Generate structured response using instructor."""
        
        # Use provider-specific model if not specified
        if model_name is None:
            if self.provider_name == "openai":
                model_name = self.provider_info.get("model", "gpt-4o-mini")  # Use configured model or fallback
            elif self.provider_name == "azure":
                model_name = self.provider_info.get("deployment_name", "gpt-4o-mini")
            elif self.provider_name == "github":
                model_name = "gpt-4o-mini"  # Available in GitHub Models
            elif self.provider_name == "ollama":
                model_name = self.provider_info.get("model", "qwen3:8b")  # Default Ollama model
        
        # Default parameters
        default_params = {
            # "temperature": 0.7,
        }
        
        # Merge with user parameters
        final_params = {**default_params, **llm_params}
        
        # Generate structured response
        try:
            response = self.client.chat.completions.create(
                model=model_name,
                response_model=response_model,
                messages=[{"role": "user", "content": prompt}],
                **final_params
            )
            return response
            
        except Exception as e:
            error_msg = str(e).lower()
            
            # Check if this is the "multiple tool calls" error indicating we need JSON mode
            if ("instructor does not support multiple tool calls" in error_msg or 
                "does not support multiple tool calls" in error_msg):
                
                # Remember this model needs JSON mode for future calls
                self._remember_json_mode(model_name)
                
                # Retry with JSON mode
                from openai import OpenAI
                client_kwargs = {"api_key": self.provider_info.get("api_key")}
                if self.provider_info.get("base_url"):
                    client_kwargs["base_url"] = self.provider_info.get("base_url")
                
                raw_client = OpenAI(**client_kwargs)
                json_client = instructor.from_openai(raw_client, mode=instructor.Mode.JSON)
                
                response = json_client.chat.completions.create(
                    model=model_name,
                    response_model=response_model,
                    messages=[{"role": "user", "content": prompt}],
                    **final_params
                )
                return response
            else:
                # Re-raise other errors with more context
                raise RuntimeError(f"Failed to generate structured response with model {model_name}: {str(e)}")
    
    def generate_text(self, prompt: str, **llm_params) -> str:
        """Generate plain text response (fallback to base provider)."""
        return self.base_provider.generate_text(prompt, **llm_params)


def create_structured_llm_provider(provider_name: str, **kwargs) -> StructuredLLMProvider:
    """Factory function to create structured LLM provider."""
    return StructuredLLMProvider(provider_name, **kwargs)


# =============================================================================
# CONVENIENCE FUNCTIONS FOR RAG TASKS
# =============================================================================

def extract_fact_structured(provider: StructuredLLMProvider, prompt: str, **kwargs):
    """Extract fact using structured response."""
    from .rag_models import FactExtractionResponse
    return provider.generate_structured(prompt, FactExtractionResponse, **kwargs)


def generate_standard_query_structured(provider: StructuredLLMProvider, prompt: str, **kwargs):
    """Generate standard query using structured response."""
    from .rag_models import StandardQueryResponse
    return provider.generate_structured(prompt, StandardQueryResponse, **kwargs)


def generate_adversarial_query_structured(provider: StructuredLLMProvider, prompt: str, **kwargs):
    """Generate adversarial query using structured response."""
    from .rag_models import AdversarialQueryResponse
    return provider.generate_structured(prompt, AdversarialQueryResponse, **kwargs)


def generate_multihop_query_structured(provider: StructuredLLMProvider, prompt: str, **kwargs):
    """Generate multi-hop query using structured response."""
    from .rag_models import MultiHopQueryResponse
    return provider.generate_structured(prompt, MultiHopQueryResponse, **kwargs)


def score_realism_structured(provider: StructuredLLMProvider, prompt: str, **kwargs):
    """Score query realism using structured response."""
    from .rag_models import RealismScoreResponse
    return provider.generate_structured(prompt, RealismScoreResponse, **kwargs)