"""LLM API integration for the Query Generation Tool."""

import os
from abc import ABC, abstractmethod
from typing import Dict, Any, Optional
import openai
from rich.console import Console

console = Console()


class LLMProvider(ABC):
    """Abstract base class for LLM providers."""
    
    @abstractmethod
    def generate_text(self, prompt: str, **kwargs) -> str:
        """Generate text using the LLM."""
        pass


class OpenAIProvider(LLMProvider):
    """OpenAI API provider implementation with configurable base URL and model."""
    
    def __init__(self, api_key: Optional[str] = None, base_url: Optional[str] = None, model: Optional[str] = None):
        """Initialize OpenAI provider.
        
        Args:
            api_key: OpenAI API key (uses OPENAI_API_KEY env var if not provided)
            base_url: Custom base URL for OpenAI-compatible APIs (uses OPENAI_BASE_URL env var if not provided)  
            model: Model name to use (uses OPENAI_MODEL env var if not provided, defaults to gpt-3.5-turbo)
        """
        self.api_key = api_key or os.getenv("OPENAI_API_KEY")
        if not self.api_key:
            raise ValueError(
                "OpenAI API key not found. Set OPENAI_API_KEY environment variable or provide api_key parameter."
            )
        
        self.base_url = base_url or os.getenv("OPENAI_BASE_URL")
        self.model = model or os.getenv("OPENAI_MODEL", "gpt-3.5-turbo")
        
        # Create client with optional base_url
        client_kwargs = {"api_key": self.api_key}
        if self.base_url:
            client_kwargs["base_url"] = self.base_url
            
        self.client = openai.OpenAI(**client_kwargs)
    
    def generate_text(self, prompt: str, **kwargs) -> str:
        """Generate text using OpenAI API."""
        # Default parameters - use configured model
        params = {
            "model": self.model,
            "temperature": 1,
            "top_p": 1.0,
        }
        
        # Override with provided parameters
        params.update(kwargs)
        
        try:
            response = self.client.chat.completions.create(
                messages=[
                    {
                        "role": "user",
                        "content": prompt
                    }
                ],
                **params
            )
            
            generated_text = response.choices[0].message.content
            if not generated_text:
                raise ValueError("Empty response from OpenAI API")
            
            return generated_text.strip()
            
        except openai.AuthenticationError:
            raise ValueError("Invalid OpenAI API key. Please check your credentials.")
        except openai.RateLimitError:
            raise RuntimeError("OpenAI API rate limit exceeded. Please try again later.")
        except openai.APIError as e:
            raise RuntimeError(f"OpenAI API error: {str(e)}")
        except Exception as e:
            raise RuntimeError(f"Unexpected error calling OpenAI API: {str(e)}")


class AzureOpenAIProvider(LLMProvider):
    """Azure OpenAI API provider implementation."""
    
    def __init__(
        self, 
        api_key: Optional[str] = None,
        azure_endpoint: Optional[str] = None,
        api_version: str = "2024-02-01",
        deployment_name: Optional[str] = None
    ):
        """Initialize Azure OpenAI provider."""
        self.api_key = api_key or os.getenv("AZURE_OPENAI_API_KEY")
        self.azure_endpoint = azure_endpoint or os.getenv("AZURE_OPENAI_ENDPOINT")
        self.deployment_name = deployment_name or os.getenv("AZURE_OPENAI_DEPLOYMENT_NAME", "gpt-35-turbo")
        
        if not self.api_key:
            raise ValueError(
                "Azure OpenAI API key not found. Set AZURE_OPENAI_API_KEY environment variable or provide api_key parameter."
            )
        if not self.azure_endpoint:
            raise ValueError(
                "Azure OpenAI endpoint not found. Set AZURE_OPENAI_ENDPOINT environment variable or provide azure_endpoint parameter."
            )
        
        self.client = openai.AzureOpenAI(
            api_key=self.api_key,
            azure_endpoint=self.azure_endpoint,
            api_version=api_version
        )
    
    def generate_text(self, prompt: str, **kwargs) -> str:
        """Generate text using Azure OpenAI API."""
        # Default parameters
        params = {
            "model": self.deployment_name,
            "temperature": 1,
            "top_p": 1.0,
        }
        
        # Override with provided parameters
        params.update(kwargs)
        
        # Handle parameter compatibility: convert max_tokens to max_completion_tokens for newer models
        if "max_tokens" in params and "max_completion_tokens" not in params:
            params["max_completion_tokens"] = params.pop("max_tokens")
        
        # Handle temperature restrictions: some Azure models only support temperature=1
        # We'll let the API return the error rather than silently changing user's intent
        
        try:
            response = self.client.chat.completions.create(
                messages=[
                    {
                        "role": "user",
                        "content": prompt
                    }
                ],
                **params
            )
            
            # Better error handling for response parsing
            if not response.choices:
                raise ValueError("Azure OpenAI API returned no choices in response")
            
            choice = response.choices[0]
            if not hasattr(choice, 'message') or not choice.message:
                raise ValueError("Azure OpenAI API returned choice without message")
                
            generated_text = choice.message.content
            if generated_text is None:
                raise ValueError("Azure OpenAI API returned None content")
            if generated_text == "":
                raise ValueError("Azure OpenAI API returned empty string content")
            
            return generated_text.strip()
            
        except openai.AuthenticationError:
            raise ValueError("Invalid Azure OpenAI API key. Please check your credentials.")
        except openai.RateLimitError:
            raise RuntimeError("Azure OpenAI API rate limit exceeded. Please try again later.")
        except openai.APIError as e:
            raise RuntimeError(f"Azure OpenAI API error: {str(e)}")
        except Exception as e:
            raise RuntimeError(f"Unexpected error calling Azure OpenAI API: {str(e)}")


class GitHubModelsProvider(LLMProvider):
    """GitHub Models API provider implementation."""
    
    def __init__(self, api_key: Optional[str] = None):
        """Initialize GitHub Models provider."""
        self.api_key = api_key or os.getenv("GITHUB_TOKEN")
        if not self.api_key:
            raise ValueError(
                "GitHub token not found. Set GITHUB_TOKEN environment variable or provide api_key parameter."
            )
        
        self.client = openai.OpenAI(
            base_url="https://models.github.ai/inference",
            api_key=self.api_key
        )
    
    def generate_text(self, prompt: str, **kwargs) -> str:
        """Generate text using GitHub Models API."""
        # Default parameters
        params = {
            "model": "openai/gpt-4o",  # Default to GPT-4o via GitHub Models
            "temperature": 0.7,
            "top_p": 1.0,
        }
        
        # Override with provided parameters
        params.update(kwargs)
        
        try:
            response = self.client.chat.completions.create(
                messages=[
                    {
                        "role": "user",
                        "content": prompt
                    }
                ],
                **params
            )
            
            generated_text = response.choices[0].message.content
            if not generated_text:
                raise ValueError("Empty response from GitHub Models API")
            
            return generated_text.strip()
            
        except openai.AuthenticationError:
            raise ValueError("Invalid GitHub token or insufficient permissions. Please check your GitHub token has models:read scope.")
        except openai.RateLimitError:
            raise RuntimeError("GitHub Models API rate limit exceeded. Please try again later.")
        except openai.APIError as e:
            raise RuntimeError(f"GitHub Models API error: {str(e)}")
        except Exception as e:
            raise RuntimeError(f"Unexpected error calling GitHub Models API: {str(e)}")


class OllamaProvider(LLMProvider):
    """Ollama API provider implementation using OpenAI-compatible endpoint."""
    
    def __init__(
        self, 
        base_url: Optional[str] = None,
        model: Optional[str] = None,
        api_key: str = "ollama"  # Required but ignored by Ollama
    ):
        """Initialize Ollama provider."""
        self.base_url = base_url or os.getenv("OLLAMA_BASE_URL", "http://csali6s001.net.plm.eds.com:11434")
        self.model = model or os.getenv("OLLAMA_MODEL", "qwen3:8b")
        
        # Ensure base_url ends with /v1/ for OpenAI compatibility
        if not self.base_url.endswith('/'):
            self.base_url += '/'
        if not self.base_url.endswith('v1/'):
            self.base_url += 'v1/'
        
        try:
            self.client = openai.OpenAI(
                base_url=self.base_url,
                api_key=api_key  # Required but ignored by Ollama
            )
        except Exception as e:
            raise ValueError(f"Failed to initialize Ollama client: {str(e)}")
    
    def generate_text(self, prompt: str, **kwargs) -> str:
        """Generate text using Ollama API."""
        # Default parameters optimized for Ollama
        params = {
            "model": self.model,
            "temperature": 0.7,
            "top_p": 1.0,
        }
        
        # Override with provided parameters
        params.update(kwargs)
        
        try:
            response = self.client.chat.completions.create(
                messages=[
                    {
                        "role": "system",
                        "content": "You are a helpful assistant. /no_think"
                    },
                    {
                        "role": "user",
                        "content": prompt
                    }
                ],
                **params
            )
            
            generated_text = response.choices[0].message.content
            if not generated_text:
                raise ValueError("Empty response from Ollama API")
            
            return generated_text.strip()
            
        except openai.APIConnectionError:
            raise RuntimeError(f"Cannot connect to Ollama server at {self.base_url}. Please ensure Ollama is running and accessible.")
        except openai.APIError as e:
            # Handle Ollama-specific errors
            error_msg = str(e)
            if "model" in error_msg.lower() and "not found" in error_msg.lower():
                raise ValueError(f"Model '{self.model}' not found on Ollama server. Please ensure the model is pulled: ollama pull {self.model}")
            else:
                raise RuntimeError(f"Ollama API error: {error_msg}")
        except Exception as e:
            raise RuntimeError(f"Unexpected error calling Ollama API: {str(e)}")


def create_llm_provider(provider_type: str = "openai", **kwargs) -> LLMProvider:
    """Factory function to create LLM providers."""
    if provider_type.lower() == "openai":
        return OpenAIProvider(**kwargs)
    elif provider_type.lower() == "azure":
        return AzureOpenAIProvider(**kwargs)
    elif provider_type.lower() == "github":
        return GitHubModelsProvider(**kwargs)
    elif provider_type.lower() == "ollama":
        return OllamaProvider(**kwargs)
    else:
        raise ValueError(f"Unsupported LLM provider: {provider_type}. Supported providers: openai, azure, github, ollama")