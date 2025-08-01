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
    """OpenAI API provider implementation."""
    
    def __init__(self, api_key: Optional[str] = None):
        """Initialize OpenAI provider."""
        self.api_key = api_key or os.getenv("OPENAI_API_KEY")
        if not self.api_key:
            raise ValueError(
                "OpenAI API key not found. Set OPENAI_API_KEY environment variable or provide api_key parameter."
            )
        
        self.client = openai.OpenAI(api_key=self.api_key)
    
    def generate_text(self, prompt: str, **kwargs) -> str:
        """Generate text using OpenAI API."""
        # Default parameters
        params = {
            "model": "gpt-3.5-turbo",
            "temperature": 0.7,
            "max_tokens": 500,
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
            "temperature": 0.7,
            "max_tokens": 500,
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
                raise ValueError("Empty response from Azure OpenAI API")
            
            return generated_text.strip()
            
        except openai.AuthenticationError:
            raise ValueError("Invalid Azure OpenAI API key. Please check your credentials.")
        except openai.RateLimitError:
            raise RuntimeError("Azure OpenAI API rate limit exceeded. Please try again later.")
        except openai.APIError as e:
            raise RuntimeError(f"Azure OpenAI API error: {str(e)}")
        except Exception as e:
            raise RuntimeError(f"Unexpected error calling Azure OpenAI API: {str(e)}")


def create_llm_provider(provider_type: str = "openai", **kwargs) -> LLMProvider:
    """Factory function to create LLM providers."""
    if provider_type.lower() == "openai":
        return OpenAIProvider(**kwargs)
    elif provider_type.lower() == "azure":
        return AzureOpenAIProvider(**kwargs)
    else:
        raise ValueError(f"Unsupported LLM provider: {provider_type}")