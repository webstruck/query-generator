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
        env_path: Path to .env file. If None, searches for .env in current directory and parent directories.
        verbose: Whether to print loading status messages.
        
    Returns:
        True if .env file was found and loaded, False otherwise.
    """
    global _env_loaded
    
    if _env_loaded:
        if verbose:
            console.print("[dim]✅ Environment already loaded[/dim]")
        return True
    
    # If no specific path provided, search for .env file
    if env_path is None:
        # Look for .env in current directory, parent directories, and query-generator subdirectory
        current_dir = Path.cwd()
        search_paths = [current_dir] + list(current_dir.parents)
        
        # Also check for query-generator subdirectory in parents (for when running from project dirs)
        for parent in [current_dir] + list(current_dir.parents):
            qg_path = parent / "query-generator"
            if qg_path.exists():
                search_paths.append(qg_path)
        
        for path in search_paths:
            env_file = path / ".env"
            if env_file.exists():
                env_path = str(env_file)
                break
    
    if env_path and Path(env_path).exists():
        success = load_dotenv(env_path, override=True)
        if success:
            _env_loaded = True
            if verbose:
                console.print(f"[green]✅ Environment loaded from {env_path}[/green]")
            return True
        else:
            if verbose:
                console.print(f"[yellow]⚠️  Failed to load environment from {env_path}[/yellow]")
            return False
    else:
        if verbose:
            console.print(f"[yellow]⚠️  No .env file found{' at ' + env_path if env_path else ''}[/yellow]")
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
    }


def get_github_models_config() -> dict:
    """Get GitHub Models configuration from environment variables."""
    return {
        "api_key": os.getenv("GITHUB_TOKEN"),
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


def get_available_providers() -> list[str]:
    """Get list of available LLM providers based on environment configuration."""
    providers = []
    
    if has_openai_config():
        providers.append("openai")
    
    if has_azure_openai_config():
        providers.append("azure")
    
    if has_github_models_config():
        providers.append("github")
    
    return providers


def auto_detect_provider() -> Optional[str]:
    """Auto-detect the best available provider based on environment configuration."""
    if has_azure_openai_config():
        return "azure"
    elif has_openai_config():
        return "openai"
    elif has_github_models_config():
        return "github"
    else:
        return None