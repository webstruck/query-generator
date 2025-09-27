"""Unified provider management system for both dimension and RAG projects."""

import os
from abc import ABC, abstractmethod
from typing import Dict, Any, Optional, List, Union, Type
from dataclasses import dataclass
from enum import Enum
import openai
from rich.console import Console

# Import existing functionality to reuse
from ..core.env import load_environment

console = Console()


class ProviderType(Enum):
    """Supported provider types."""
    OPENAI = "openai"
    AZURE = "azure"
    GITHUB = "github"
    OLLAMA = "ollama"


class ProviderStatus(Enum):
    """Provider availability status."""
    AVAILABLE = "available"
    MISSING_CONFIG = "missing_config"
    INVALID_CONFIG = "invalid_config"
    NETWORK_ERROR = "network_error"
    UNKNOWN = "unknown"


@dataclass
class ProviderConfig:
    """Provider configuration data."""
    provider_type: ProviderType
    config: Dict[str, Any]
    status: ProviderStatus
    error_message: Optional[str] = None


class BaseProvider(ABC):
    """Abstract base class for all providers."""

    def __init__(self, provider_type: ProviderType, config: Dict[str, Any]):
        self.provider_type = provider_type
        self.config = config
        self._validate_config()

    @abstractmethod
    def _validate_config(self) -> None:
        """Validate provider configuration."""
        pass

    @abstractmethod
    def generate_text(self, prompt: str, **kwargs) -> str:
        """Generate text using the provider."""
        pass

    @abstractmethod
    def get_structured_response(self, prompt: str, response_model: Type, **kwargs) -> Any:
        """Get structured response using the provider."""
        pass

    @abstractmethod
    def test_connection(self) -> bool:
        """Test if the provider is accessible."""
        pass

    def get_default_model(self) -> str:
        """Get the default model for this provider."""
        return self.config.get("model", "unknown")


class OpenAIProvider(BaseProvider):
    """OpenAI provider implementation."""

    def __init__(self, config: Dict[str, Any]):
        super().__init__(ProviderType.OPENAI, config)
        self._setup_client()

    def _validate_config(self) -> None:
        if not self.config.get("api_key"):
            raise ValueError("OpenAI API key is required")

    def _setup_client(self):
        client_kwargs = {"api_key": self.config["api_key"]}
        if self.config.get("base_url"):
            client_kwargs["base_url"] = self.config["base_url"]
        self.client = openai.OpenAI(**client_kwargs)

    def generate_text(self, prompt: str, **kwargs) -> str:
        params = {
            "model": self.config.get("model", "gpt-3.5-turbo"),
            "temperature": kwargs.get("temperature", 1.0),
            "top_p": kwargs.get("top_p", 1.0),
        }
        params.update(kwargs)

        try:
            response = self.client.chat.completions.create(
                messages=[{"role": "user", "content": prompt}],
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

    def get_structured_response(self, prompt: str, response_model: Type, **kwargs) -> Any:
        """Get structured response using instructor."""
        try:
            import instructor
            client = instructor.from_openai(self.client)

            return client.chat.completions.create(
                model=self.config.get("model", "gpt-3.5-turbo"),
                response_model=response_model,
                messages=[{"role": "user", "content": prompt}],
                **kwargs
            )
        except ImportError:
            raise RuntimeError("instructor library not available for structured responses")

    def test_connection(self) -> bool:
        """Test OpenAI connection."""
        try:
            # Simple test call
            self.generate_text("Hello", max_tokens=1)
            return True
        except Exception:
            return False


class AzureOpenAIProvider(BaseProvider):
    """Azure OpenAI provider implementation."""

    def __init__(self, config: Dict[str, Any]):
        super().__init__(ProviderType.AZURE, config)
        self._setup_client()

    def _validate_config(self) -> None:
        required = ["api_key", "azure_endpoint"]
        missing = [key for key in required if not self.config.get(key)]
        if missing:
            raise ValueError(f"Azure OpenAI missing config: {', '.join(missing)}")

    def _setup_client(self):
        self.client = openai.AzureOpenAI(
            api_key=self.config["api_key"],
            api_version=self.config.get("api_version", "2024-02-01"),
            azure_endpoint=self.config["azure_endpoint"]
        )

    def generate_text(self, prompt: str, **kwargs) -> str:
        params = {
            "model": self.config.get("deployment_name", "gpt-35-turbo"),
            "temperature": kwargs.get("temperature", 1.0),
            "top_p": kwargs.get("top_p", 1.0),
        }
        params.update(kwargs)

        try:
            response = self.client.chat.completions.create(
                messages=[{"role": "user", "content": prompt}],
                **params
            )

            generated_text = response.choices[0].message.content
            if not generated_text:
                raise ValueError("Empty response from Azure OpenAI API")

            return generated_text.strip()

        except openai.AuthenticationError:
            raise ValueError("Invalid Azure OpenAI credentials. Please check your configuration.")
        except openai.RateLimitError:
            raise RuntimeError("Azure OpenAI rate limit exceeded. Please try again later.")
        except openai.APIError as e:
            raise RuntimeError(f"Azure OpenAI API error: {str(e)}")
        except Exception as e:
            raise RuntimeError(f"Unexpected error calling Azure OpenAI API: {str(e)}")

    def get_structured_response(self, prompt: str, response_model: Type, **kwargs) -> Any:
        """Get structured response using instructor."""
        try:
            import instructor
            client = instructor.from_openai(self.client)

            return client.chat.completions.create(
                model=self.config.get("deployment_name", "gpt-35-turbo"),
                response_model=response_model,
                messages=[{"role": "user", "content": prompt}],
                **kwargs
            )
        except ImportError:
            raise RuntimeError("instructor library not available for structured responses")

    def test_connection(self) -> bool:
        """Test Azure OpenAI connection."""
        try:
            self.generate_text("Hello", max_tokens=1)
            return True
        except Exception:
            return False


class GitHubModelsProvider(BaseProvider):
    """GitHub Models provider implementation."""

    def __init__(self, config: Dict[str, Any]):
        super().__init__(ProviderType.GITHUB, config)
        self._setup_client()

    def _validate_config(self) -> None:
        if not self.config.get("api_key"):
            raise ValueError("GitHub token is required")

    def _setup_client(self):
        self.client = openai.OpenAI(
            api_key=self.config["api_key"],
            base_url="https://models.inference.ai.azure.com"
        )

    def generate_text(self, prompt: str, **kwargs) -> str:
        params = {
            "model": self.config.get("model", "gpt-4o-mini"),
            "temperature": kwargs.get("temperature", 1.0),
            "top_p": kwargs.get("top_p", 1.0),
        }
        params.update(kwargs)

        try:
            response = self.client.chat.completions.create(
                messages=[{"role": "user", "content": prompt}],
                **params
            )

            generated_text = response.choices[0].message.content
            if not generated_text:
                raise ValueError("Empty response from GitHub Models API")

            return generated_text.strip()

        except openai.AuthenticationError:
            raise ValueError("Invalid GitHub token. Please check your credentials.")
        except openai.RateLimitError:
            raise RuntimeError("GitHub Models rate limit exceeded. Please try again later.")
        except openai.APIError as e:
            raise RuntimeError(f"GitHub Models API error: {str(e)}")
        except Exception as e:
            raise RuntimeError(f"Unexpected error calling GitHub Models API: {str(e)}")

    def get_structured_response(self, prompt: str, response_model: Type, **kwargs) -> Any:
        """Get structured response using instructor."""
        try:
            import instructor
            client = instructor.from_openai(self.client)

            return client.chat.completions.create(
                model=self.config.get("model", "gpt-4o-mini"),
                response_model=response_model,
                messages=[{"role": "user", "content": prompt}],
                **kwargs
            )
        except ImportError:
            raise RuntimeError("instructor library not available for structured responses")

    def test_connection(self) -> bool:
        """Test GitHub Models connection."""
        try:
            self.generate_text("Hello", max_tokens=1)
            return True
        except Exception:
            return False


class OllamaProvider(BaseProvider):
    """Ollama provider implementation."""

    def __init__(self, config: Dict[str, Any]):
        super().__init__(ProviderType.OLLAMA, config)
        self._setup_client()

    def _validate_config(self) -> None:
        # Ollama doesn't require API keys, just a base URL
        if not self.config.get("base_url"):
            self.config["base_url"] = "http://csali6s001.net.plm.eds.com:11434"
        if not self.config.get("model"):
            self.config["model"] = "qwen3:8b"

    def _setup_client(self):
        self.client = openai.OpenAI(
            api_key="ollama",  # Ollama doesn't need real API key
            base_url=self.config["base_url"]
        )

    def generate_text(self, prompt: str, **kwargs) -> str:
        params = {
            "model": self.config.get("model", "qwen3:8b"),
            "temperature": kwargs.get("temperature", 1.0),
        }
        params.update(kwargs)

        try:
            response = self.client.chat.completions.create(
                messages=[{"role": "user", "content": prompt}],
                **params
            )

            generated_text = response.choices[0].message.content
            if not generated_text:
                raise ValueError("Empty response from Ollama API")

            return generated_text.strip()

        except Exception as e:
            raise RuntimeError(f"Error calling Ollama API: {str(e)}")

    def get_structured_response(self, prompt: str, response_model: Type, **kwargs) -> Any:
        """Get structured response - Ollama might not support instructor."""
        try:
            import instructor
            client = instructor.from_openai(self.client, mode=instructor.Mode.JSON)

            return client.chat.completions.create(
                model=self.config.get("model", "qwen3:8b"),
                response_model=response_model,
                messages=[{"role": "user", "content": prompt}],
                **kwargs
            )
        except ImportError:
            raise RuntimeError("instructor library not available for structured responses")

    def test_connection(self) -> bool:
        """Test Ollama connection."""
        try:
            self.generate_text("Hello")
            return True
        except Exception:
            return False


class ProviderError(Exception):
    """Provider-specific error."""

    def __init__(self, message: str, provider_type: ProviderType, error_code: str = "PROVIDER_ERROR"):
        self.message = message
        self.provider_type = provider_type
        self.error_code = error_code
        super().__init__(message)


class UnifiedProviderManager:
    """Unified provider management system."""

    def __init__(self):
        """Initialize provider manager and load environment."""
        load_environment()
        self._providers = {}
        self._config_cache = {}

    def get_provider_config(self, provider_type: Union[str, ProviderType]) -> Dict[str, Any]:
        """Get configuration for a specific provider."""
        if isinstance(provider_type, str):
            provider_type = ProviderType(provider_type.lower())

        # Use cached config if available
        if provider_type in self._config_cache:
            return self._config_cache[provider_type]

        config = {}

        if provider_type == ProviderType.OPENAI:
            config = {
                "api_key": os.getenv("OPENAI_API_KEY"),
                "base_url": os.getenv("OPENAI_BASE_URL"),
                "model": os.getenv("OPENAI_MODEL", "gpt-3.5-turbo"),
            }
        elif provider_type == ProviderType.AZURE:
            config = {
                "api_key": os.getenv("AZURE_OPENAI_API_KEY"),
                "azure_endpoint": os.getenv("AZURE_OPENAI_ENDPOINT"),
                "deployment_name": os.getenv("AZURE_OPENAI_DEPLOYMENT_NAME"),
                "api_version": os.getenv("AZURE_OPENAI_API_VERSION", "2024-02-01"),
            }
        elif provider_type == ProviderType.GITHUB:
            config = {
                "api_key": os.getenv("GITHUB_TOKEN"),
                "model": os.getenv("GITHUB_MODEL", "gpt-4o-mini"),
            }
        elif provider_type == ProviderType.OLLAMA:
            config = {
                "base_url": os.getenv("OLLAMA_BASE_URL", "http://csali6s001.net.plm.eds.com:11434"),
                "model": os.getenv("OLLAMA_MODEL", "qwen3:8b"),
            }

        # Cache the config
        self._config_cache[provider_type] = config
        return config

    def validate_provider_config(self, provider_type: Union[str, ProviderType]) -> ProviderConfig:
        """Validate a provider's configuration."""
        if isinstance(provider_type, str):
            provider_type = ProviderType(provider_type.lower())

        config = self.get_provider_config(provider_type)

        try:
            # Create provider instance to validate config
            provider = self._create_provider_instance(provider_type, config)

            # Test connection if possible
            try:
                connection_ok = provider.test_connection()
                status = ProviderStatus.AVAILABLE if connection_ok else ProviderStatus.NETWORK_ERROR
                error_msg = None if connection_ok else "Connection test failed"
            except Exception as e:
                status = ProviderStatus.INVALID_CONFIG
                error_msg = str(e)

            return ProviderConfig(
                provider_type=provider_type,
                config=config,
                status=status,
                error_message=error_msg
            )

        except ValueError as e:
            return ProviderConfig(
                provider_type=provider_type,
                config=config,
                status=ProviderStatus.MISSING_CONFIG,
                error_message=str(e)
            )
        except Exception as e:
            return ProviderConfig(
                provider_type=provider_type,
                config=config,
                status=ProviderStatus.UNKNOWN,
                error_message=str(e)
            )

    def get_provider(self, provider_type: Union[str, ProviderType]) -> BaseProvider:
        """Get or create a provider instance."""
        if isinstance(provider_type, str):
            provider_type = ProviderType(provider_type.lower())

        # Return cached provider if available
        if provider_type in self._providers:
            return self._providers[provider_type]

        # Validate configuration first
        provider_config = self.validate_provider_config(provider_type)
        if provider_config.status != ProviderStatus.AVAILABLE:
            if provider_config.status == ProviderStatus.MISSING_CONFIG:
                raise ProviderError(
                    f"Provider {provider_type.value} missing configuration: {provider_config.error_message}",
                    provider_type,
                    "MISSING_CONFIG"
                )
            else:
                raise ProviderError(
                    f"Provider {provider_type.value} configuration error: {provider_config.error_message}",
                    provider_type,
                    "CONFIG_ERROR"
                )

        # Create and cache provider
        provider = self._create_provider_instance(provider_type, provider_config.config)
        self._providers[provider_type] = provider
        return provider

    def _create_provider_instance(self, provider_type: ProviderType, config: Dict[str, Any]) -> BaseProvider:
        """Create a provider instance."""
        if provider_type == ProviderType.OPENAI:
            return OpenAIProvider(config)
        elif provider_type == ProviderType.AZURE:
            return AzureOpenAIProvider(config)
        elif provider_type == ProviderType.GITHUB:
            return GitHubModelsProvider(config)
        elif provider_type == ProviderType.OLLAMA:
            return OllamaProvider(config)
        else:
            raise ValueError(f"Unknown provider type: {provider_type}")

    def detect_available_providers(self) -> List[ProviderConfig]:
        """Detect all available providers with their status."""
        providers = []

        for provider_type in ProviderType:
            config = self.validate_provider_config(provider_type)
            providers.append(config)

        return providers

    def get_best_available_provider(self) -> Optional[BaseProvider]:
        """Get the best available provider based on priority order."""
        # Priority order: Azure > OpenAI > GitHub > Ollama
        priority_order = [
            ProviderType.AZURE,
            ProviderType.OPENAI,
            ProviderType.GITHUB,
            ProviderType.OLLAMA
        ]

        for provider_type in priority_order:
            try:
                provider_config = self.validate_provider_config(provider_type)
                if provider_config.status == ProviderStatus.AVAILABLE:
                    return self.get_provider(provider_type)
            except Exception:
                continue

        return None

    def handle_provider_error(self, error: Exception, fallback_chain: List[str]) -> BaseProvider:
        """Handle provider errors with fallback chain."""
        for fallback_provider in fallback_chain:
            try:
                console.print(f"[yellow]Trying fallback provider: {fallback_provider}[/yellow]")
                return self.get_provider(fallback_provider)
            except Exception as fallback_error:
                console.print(f"[red]Fallback {fallback_provider} also failed: {fallback_error}[/red]")
                continue

        raise ProviderError(
            f"All providers failed. Original error: {error}",
            ProviderType.OPENAI,  # Default for error reporting
            "ALL_PROVIDERS_FAILED"
        )

    def get_provider_status_summary(self) -> Dict[str, Any]:
        """Get a summary of all provider statuses."""
        providers = self.detect_available_providers()

        summary = {
            "total_providers": len(providers),
            "available_count": sum(1 for p in providers if p.status == ProviderStatus.AVAILABLE),
            "providers": {}
        }

        for provider_config in providers:
            summary["providers"][provider_config.provider_type.value] = {
                "status": provider_config.status.value,
                "error": provider_config.error_message,
                "model": provider_config.config.get("model", "unknown")
            }

        return summary

    def show_setup_help(self, provider_type: Union[str, ProviderType]) -> None:
        """Show setup help for a specific provider."""
        if isinstance(provider_type, str):
            provider_type = ProviderType(provider_type.lower())

        from rich.panel import Panel

        if provider_type == ProviderType.OPENAI:
            help_text = """[bold]OpenAI Configuration:[/bold]

Required environment variables:
• OPENAI_API_KEY=your_api_key_here

Optional customization:
• OPENAI_BASE_URL=https://your-proxy.com  # For custom endpoints
• OPENAI_MODEL=gpt-4  # Default model to use

Get API key from: https://platform.openai.com/api-keys"""

        elif provider_type == ProviderType.AZURE:
            help_text = """[bold]Azure OpenAI Configuration:[/bold]

Required environment variables:
• AZURE_OPENAI_API_KEY=your_api_key
• AZURE_OPENAI_ENDPOINT=https://your-resource.openai.azure.com/
• AZURE_OPENAI_DEPLOYMENT_NAME=your_deployment_name

Optional:
• AZURE_OPENAI_API_VERSION=2024-02-01  # API version"""

        elif provider_type == ProviderType.GITHUB:
            help_text = """[bold]GitHub Models Configuration:[/bold]

Required environment variables:
• GITHUB_TOKEN=your_github_token

Optional:
• GITHUB_MODEL=gpt-4o-mini  # Model to use

Get token from: https://github.com/settings/tokens
Token needs 'models:read' scope for GitHub Models"""

        elif provider_type == ProviderType.OLLAMA:
            help_text = """[bold]Ollama Configuration:[/bold]

Optional environment variables:
• OLLAMA_BASE_URL=http://localhost:11434  # Ollama server URL
• OLLAMA_MODEL=qwen3:8b  # Model to use

Default server: http://csali6s001.net.plm.eds.com:11434
Ensure Ollama server is running and model is available"""

        else:
            help_text = f"Unknown provider: {provider_type.value}"

        console.print(Panel(help_text, title=f"{provider_type.value.title()} Setup", border_style="blue"))


# Global provider manager instance
_provider_manager = None


def get_provider_manager() -> UnifiedProviderManager:
    """Get global provider manager instance."""
    global _provider_manager
    if _provider_manager is None:
        _provider_manager = UnifiedProviderManager()
    return _provider_manager