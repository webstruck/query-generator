"""Shared utilities and unified systems for both dimension and RAG projects."""

from .export import UnifiedExporter, ExportResult, ExportFormat
from .providers import UnifiedProviderManager, ProviderType, ProviderStatus, get_provider_manager
from .errors import (
    QGenError, ValidationError, ConfigurationError, ProviderError,
    ProcessingError, DataError, ProjectError, ErrorCode,
    handle_provider_errors, handle_processing_errors, handle_data_errors,
    ErrorContext, get_error_reporter, create_user_friendly_message
)

__all__ = [
    # Export system
    "UnifiedExporter",
    "ExportResult",
    "ExportFormat",

    # Provider system
    "UnifiedProviderManager",
    "ProviderType",
    "ProviderStatus",
    "get_provider_manager",

    # Error system
    "QGenError",
    "ValidationError",
    "ConfigurationError",
    "ProviderError",
    "ProcessingError",
    "DataError",
    "ProjectError",
    "ErrorCode",
    "handle_provider_errors",
    "handle_processing_errors",
    "handle_data_errors",
    "ErrorContext",
    "get_error_reporter",
    "create_user_friendly_message"
]