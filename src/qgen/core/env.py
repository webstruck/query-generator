"""Environment variable management for the Query Generation Tool."""

import os
from pathlib import Path
from typing import Optional
from dotenv import load_dotenv
from rich.console import Console

console = Console()

# Global flag to track if .env has been loaded
_env_loaded = False


def load_environment(env_path: Optional[str] = None, verbose: bool = False) -> bool:
    """Load environment variables from .env file.
    
    Args:
        env_path: Specific path to .env file (optional)
        verbose: Whether to print loading status messages
        
    Returns:
        True if .env file was found and loaded, False otherwise
    """
    global _env_loaded
    
    if _env_loaded:
        if verbose:
            console.print("[dim]✅ Environment already loaded[/dim]")
        return True
    
    # Use load_dotenv() built-in discovery or specific path
    if env_path:
        success = load_dotenv(env_path, override=True)
        found_path = env_path if Path(env_path).exists() else None
    else:
        # load_dotenv() automatically searches current dir and parents
        success = load_dotenv(override=True)
        # Try to find which .env file was loaded for verbose output
        found_path = None
        for path in [Path.cwd()] + list(Path.cwd().parents):
            env_file = path / ".env"
            if env_file.exists():
                found_path = str(env_file)
                break
    
    if success:
        _env_loaded = True
        if verbose and found_path:
            console.print(f"[green]✅ Environment loaded from {found_path}[/green]")
        return True
    else:
        if verbose:
            console.print("[yellow]⚠️  No .env file found[/yellow]")
        return False


def ensure_environment_loaded(verbose: bool = False) -> None:
    """Ensure environment variables are loaded. Call this at the start of main functions."""
    load_environment(verbose=verbose)


def get_azure_openai_config() -> dict:
    """Get Azure OpenAI configuration from environment variables."""
    return {
        "api_key": os.getenv("AZURE_OPENAI_API_KEY"),
        "azure_endpoint": os.getenv("AZURE_OPENAI_ENDPOINT"),
        "deployment_name": os.getenv("AZURE_OPENAI_DEPLOYMENT_NAME"),
        "api_version": os.getenv("AZURE_OPENAI_API_VERSION", "2024-02-01"),
    }


def get_openai_config() -> dict:
    """Get OpenAI configuration from environment variables."""
    return {
        "api_key": os.getenv("OPENAI_API_KEY"),
        "base_url": os.getenv("OPENAI_BASE_URL"),
        "model": os.getenv("OPENAI_MODEL", "gpt-3.5-turbo"),
    }


def get_github_models_config() -> dict:
    """Get GitHub Models configuration from environment variables."""
    return {
        "api_key": os.getenv("GITHUB_TOKEN"),
    }


def get_ollama_config() -> dict:
    """Get Ollama configuration from environment variables."""
    return {
        "base_url": os.getenv("OLLAMA_BASE_URL", "http://csali6s001.net.plm.eds.com:11434"),
        "model": os.getenv("OLLAMA_MODEL", "qwen3:8b"),
    }


def has_azure_openai_config() -> bool:
    """Check if Azure OpenAI configuration is available."""
    config = get_azure_openai_config()
    return bool(config["api_key"] and config["azure_endpoint"])


def has_openai_config() -> bool:
    """Check if OpenAI configuration is available."""
    config = get_openai_config()
    return bool(config["api_key"])


def has_github_models_config() -> bool:
    """Check if GitHub Models configuration is available."""
    config = get_github_models_config()
    return bool(config["api_key"])


def has_ollama_config() -> bool:
    """Check if Ollama configuration is available.
    
    Ollama is considered available if either:
    1. OLLAMA_BASE_URL is explicitly set, or
    2. Default server appears to be accessible (basic check)
    """
    # For now, we'll assume Ollama is available if user explicitly sets OLLAMA_BASE_URL
    # or if they haven't set it but might be using default configuration
    # In practice, this would require a network check to the server
    config = get_ollama_config()
    # Always return True since Ollama config has defaults and doesn't require API keys
    # The actual connection test will happen when making requests
    return True


def get_available_providers() -> list[str]:
    """Get list of available LLM providers based on environment configuration."""
    providers = []
    
    if has_openai_config():
        providers.append("openai")
    
    if has_azure_openai_config():
        providers.append("azure")
    
    if has_github_models_config():
        providers.append("github")
    
    if has_ollama_config():
        providers.append("ollama")
    
    return providers


def auto_detect_provider() -> Optional[str]:
    """Auto-detect the best available provider based on environment configuration."""
    if has_azure_openai_config():
        return "azure"
    elif has_openai_config():
        return "openai"
    elif has_github_models_config():
        return "github"
    elif has_ollama_config():
        return "ollama"
    else:
        return None


def validate_llm_provider(provider: str) -> bool:
    """Validate that a specific LLM provider is properly configured."""
    if provider == "openai":
        return has_openai_config()
    elif provider == "azure":
        return has_azure_openai_config()
    elif provider == "github":
        return has_github_models_config()
    elif provider == "ollama":
        return has_ollama_config()
    else:
        return False


def show_provider_setup_help(provider: str) -> None:
    """Show setup help for a specific provider."""
    from rich.console import Console
    from .rich_output import show_error_panel
    
    console = Console()
    
    if provider == "openai":
        show_error_panel(
            "OpenAI Configuration Missing",
            "OpenAI API key not found in environment.",
            [
                "Set OPENAI_API_KEY environment variable",
                "Add to .env file: OPENAI_API_KEY=your_key_here",
                "Get API key from: https://platform.openai.com/api-keys",
                "",
                "Optional customization:",
                "OPENAI_BASE_URL=https://your-proxy.com  # For custom endpoints",
                "OPENAI_MODEL=gpt-4  # Default model to use"
            ]
        )
    elif provider == "azure":
        show_error_panel(
            "Azure OpenAI Configuration Missing", 
            "Azure OpenAI configuration not found in environment.",
            [
                "Set AZURE_OPENAI_API_KEY environment variable",
                "Set AZURE_OPENAI_ENDPOINT environment variable", 
                "Set AZURE_OPENAI_DEPLOYMENT_NAME environment variable",
                "Add to .env file with your Azure OpenAI details"
            ]
        )
    elif provider == "github":
        show_error_panel(
            "GitHub Models Configuration Missing",
            "GitHub token not found in environment.",
            [
                "Set GITHUB_TOKEN environment variable",
                "Add to .env file: GITHUB_TOKEN=your_token_here", 
                "Get token from: https://github.com/settings/tokens",
                "Token needs 'models:read' scope for GitHub Models"
            ]
        )
    elif provider == "ollama":
        show_error_panel(
            "Ollama Configuration",
            "Ollama server configuration.",
            [
                "Default server: http://csali6s001.net.plm.eds.com:11434",
                "Default model: qwen3:8b",
                "Override with OLLAMA_BASE_URL and OLLAMA_MODEL environment variables",
                "Ensure Ollama server is running and model is available"
            ]
        )
    else:
        show_error_panel(
            f"Unknown Provider: {provider}",
            f"Provider '{provider}' is not supported.",
            [
                "Supported providers: openai, azure, github, ollama",
                "Check your configuration and try again"
            ]
        )