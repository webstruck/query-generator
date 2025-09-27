"""Unified error handling system for both dimension and RAG projects."""

import traceback
from datetime import datetime
from typing import Dict, Any, Optional, List
from enum import Enum
import logging


class ErrorCode(Enum):
    """Standard error codes across the application."""

    # General errors
    UNKNOWN_ERROR = "UNKNOWN_ERROR"
    VALIDATION_ERROR = "VALIDATION_ERROR"
    CONFIGURATION_ERROR = "CONFIGURATION_ERROR"
    FILE_NOT_FOUND = "FILE_NOT_FOUND"
    PERMISSION_ERROR = "PERMISSION_ERROR"

    # Provider errors
    PROVIDER_ERROR = "PROVIDER_ERROR"
    PROVIDER_MISSING_CONFIG = "PROVIDER_MISSING_CONFIG"
    PROVIDER_INVALID_CONFIG = "PROVIDER_INVALID_CONFIG"
    PROVIDER_NETWORK_ERROR = "PROVIDER_NETWORK_ERROR"
    PROVIDER_RATE_LIMIT = "PROVIDER_RATE_LIMIT"
    PROVIDER_AUTH_ERROR = "PROVIDER_AUTH_ERROR"
    ALL_PROVIDERS_FAILED = "ALL_PROVIDERS_FAILED"

    # Processing errors
    PROCESSING_ERROR = "PROCESSING_ERROR"
    GENERATION_ERROR = "GENERATION_ERROR"
    PARSING_ERROR = "PARSING_ERROR"
    QUALITY_CHECK_FAILED = "QUALITY_CHECK_FAILED"

    # Data errors
    DATA_ERROR = "DATA_ERROR"
    EXPORT_ERROR = "EXPORT_ERROR"
    IMPORT_ERROR = "IMPORT_ERROR"
    DATA_CORRUPTION = "DATA_CORRUPTION"

    # Project errors
    PROJECT_ERROR = "PROJECT_ERROR"
    PROJECT_NOT_FOUND = "PROJECT_NOT_FOUND"
    PROJECT_INVALID_TYPE = "PROJECT_INVALID_TYPE"
    PROJECT_INIT_ERROR = "PROJECT_INIT_ERROR"


class QGenError(Exception):
    """Base exception class for all qgen errors."""

    def __init__(self,
                 message: str,
                 error_code: ErrorCode,
                 context: Optional[Dict[str, Any]] = None,
                 cause: Optional[Exception] = None):
        """
        Initialize QGen error.

        Args:
            message: Human-readable error message
            error_code: Standardized error code
            context: Additional context for debugging
            cause: Original exception that caused this error
        """
        super().__init__(message)
        self.message = message
        self.error_code = error_code
        self.context = context or {}
        self.cause = cause
        self.timestamp = datetime.utcnow()

        # Capture stack trace
        self.stack_trace = traceback.format_exc() if cause else None

    def to_dict(self) -> Dict[str, Any]:
        """Convert error to dictionary for serialization."""
        return {
            "message": self.message,
            "error_code": self.error_code.value,
            "context": self.context,
            "timestamp": self.timestamp.isoformat(),
            "cause": str(self.cause) if self.cause else None,
            "stack_trace": self.stack_trace
        }

    def __str__(self) -> str:
        return f"[{self.error_code.value}] {self.message}"


class ValidationError(QGenError):
    """Error in data validation."""

    def __init__(self, message: str, field: Optional[str] = None, value: Any = None):
        context = {}
        if field:
            context["field"] = field
        if value is not None:
            context["value"] = str(value)

        super().__init__(message, ErrorCode.VALIDATION_ERROR, context)


class ConfigurationError(QGenError):
    """Error in configuration."""

    def __init__(self, message: str, config_key: Optional[str] = None):
        context = {}
        if config_key:
            context["config_key"] = config_key

        super().__init__(message, ErrorCode.CONFIGURATION_ERROR, context)


class ProviderError(QGenError):
    """Error related to LLM providers."""

    def __init__(self,
                 message: str,
                 provider_type: Optional[str] = None,
                 error_code: ErrorCode = ErrorCode.PROVIDER_ERROR,
                 cause: Optional[Exception] = None):
        context = {}
        if provider_type:
            context["provider_type"] = provider_type

        super().__init__(message, error_code, context, cause)


class ProcessingError(QGenError):
    """Error during processing operations."""

    def __init__(self,
                 message: str,
                 operation: Optional[str] = None,
                 error_code: ErrorCode = ErrorCode.PROCESSING_ERROR,
                 cause: Optional[Exception] = None):
        context = {}
        if operation:
            context["operation"] = operation

        super().__init__(message, error_code, context, cause)


class DataError(QGenError):
    """Error related to data operations."""

    def __init__(self,
                 message: str,
                 file_path: Optional[str] = None,
                 error_code: ErrorCode = ErrorCode.DATA_ERROR,
                 cause: Optional[Exception] = None):
        context = {}
        if file_path:
            context["file_path"] = file_path

        super().__init__(message, error_code, context, cause)


class ProjectError(QGenError):
    """Error related to project operations."""

    def __init__(self,
                 message: str,
                 project_name: Optional[str] = None,
                 project_type: Optional[str] = None,
                 error_code: ErrorCode = ErrorCode.PROJECT_ERROR,
                 cause: Optional[Exception] = None):
        context = {}
        if project_name:
            context["project_name"] = project_name
        if project_type:
            context["project_type"] = project_type

        super().__init__(message, error_code, context, cause)


def handle_provider_errors(func):
    """Decorator to handle provider-specific errors."""
    def wrapper(*args, **kwargs):
        try:
            return func(*args, **kwargs)
        except Exception as e:
            # Convert common provider errors to standardized format
            if "authentication" in str(e).lower() or "unauthorized" in str(e).lower():
                raise ProviderError(
                    f"Provider authentication failed: {e}",
                    error_code=ErrorCode.PROVIDER_AUTH_ERROR,
                    cause=e
                )
            elif "rate limit" in str(e).lower():
                raise ProviderError(
                    f"Provider rate limit exceeded: {e}",
                    error_code=ErrorCode.PROVIDER_RATE_LIMIT,
                    cause=e
                )
            elif "network" in str(e).lower() or "connection" in str(e).lower():
                raise ProviderError(
                    f"Provider network error: {e}",
                    error_code=ErrorCode.PROVIDER_NETWORK_ERROR,
                    cause=e
                )
            else:
                raise ProviderError(f"Provider operation failed: {e}", cause=e)

    return wrapper


def handle_processing_errors(operation: str):
    """Decorator to handle processing errors with operation context."""
    def decorator(func):
        def wrapper(*args, **kwargs):
            try:
                return func(*args, **kwargs)
            except QGenError:
                # Re-raise qgen errors as-is
                raise
            except Exception as e:
                raise ProcessingError(
                    f"Processing operation '{operation}' failed: {e}",
                    operation=operation,
                    cause=e
                )
        return wrapper
    return decorator


def handle_data_errors(func):
    """Decorator to handle data operation errors."""
    def wrapper(*args, **kwargs):
        try:
            return func(*args, **kwargs)
        except QGenError:
            # Re-raise qgen errors as-is
            raise
        except FileNotFoundError as e:
            raise DataError(
                f"File not found: {e}",
                file_path=str(e).split("'")[1] if "'" in str(e) else None,
                error_code=ErrorCode.FILE_NOT_FOUND,
                cause=e
            )
        except PermissionError as e:
            raise DataError(
                f"Permission denied: {e}",
                error_code=ErrorCode.PERMISSION_ERROR,
                cause=e
            )
        except Exception as e:
            raise DataError(f"Data operation failed: {e}", cause=e)

    return wrapper


class ErrorContext:
    """Context manager for capturing and handling errors."""

    def __init__(self, operation: str, **context):
        self.operation = operation
        self.context = context

    def __enter__(self):
        return self

    def __exit__(self, exc_type, exc_val, exc_tb):
        if exc_type and not issubclass(exc_type, QGenError):
            # Convert non-QGen exceptions to QGen errors
            raise ProcessingError(
                f"Operation '{self.operation}' failed: {exc_val}",
                operation=self.operation,
                cause=exc_val
            )
        return False  # Don't suppress exceptions


class ErrorReporter:
    """Centralized error reporting and logging."""

    def __init__(self):
        self.logger = logging.getLogger("qgen.errors")
        self._setup_logging()

    def _setup_logging(self):
        """Setup error logging configuration."""
        if not self.logger.handlers:
            handler = logging.StreamHandler()
            formatter = logging.Formatter(
                '%(asctime)s - %(name)s - %(levelname)s - %(message)s'
            )
            handler.setFormatter(formatter)
            self.logger.addHandler(handler)
            self.logger.setLevel(logging.ERROR)

    def report_error(self, error: QGenError, additional_context: Optional[Dict[str, Any]] = None):
        """Report an error with full context."""
        context = {
            "error_code": error.error_code.value,
            "context": error.context,
            "timestamp": error.timestamp.isoformat()
        }

        if additional_context:
            context.update(additional_context)

        self.logger.error(
            f"Error occurred: {error.message}",
            extra=context,
            exc_info=error.cause
        )

    def report_provider_failure(self,
                              provider_type: str,
                              error: Exception,
                              fallback_attempted: bool = False):
        """Report provider failure with specialized logging."""
        error_info = {
            "provider_type": provider_type,
            "fallback_attempted": fallback_attempted,
            "error_type": type(error).__name__
        }

        self.logger.error(
            f"Provider {provider_type} failed: {error}",
            extra=error_info,
            exc_info=error
        )

    def get_error_summary(self, errors: List[QGenError]) -> Dict[str, Any]:
        """Generate summary statistics for a list of errors."""
        if not errors:
            return {"total_errors": 0}

        error_codes = [e.error_code.value for e in errors]
        error_code_counts = {}
        for code in error_codes:
            error_code_counts[code] = error_code_counts.get(code, 0) + 1

        return {
            "total_errors": len(errors),
            "error_code_distribution": error_code_counts,
            "first_error": errors[0].timestamp.isoformat(),
            "last_error": errors[-1].timestamp.isoformat(),
            "most_common_error": max(error_code_counts, key=error_code_counts.get)
        }


# Global error reporter instance
_error_reporter = None


def get_error_reporter() -> ErrorReporter:
    """Get global error reporter instance."""
    global _error_reporter
    if _error_reporter is None:
        _error_reporter = ErrorReporter()
    return _error_reporter


def create_user_friendly_message(error: QGenError) -> str:
    """Create user-friendly error message with helpful suggestions."""
    base_message = error.message

    suggestions = []

    if error.error_code == ErrorCode.PROVIDER_MISSING_CONFIG:
        suggestions.extend([
            "Check your environment variables or .env file",
            "Run 'qgen status' to see provider configuration",
            "See setup documentation for your provider"
        ])
    elif error.error_code == ErrorCode.PROVIDER_AUTH_ERROR:
        suggestions.extend([
            "Verify your API key is correct and not expired",
            "Check if your API key has the required permissions",
            "Try regenerating your API key"
        ])
    elif error.error_code == ErrorCode.PROVIDER_RATE_LIMIT:
        suggestions.extend([
            "Wait a few minutes before trying again",
            "Consider upgrading your API plan for higher limits",
            "Try using a different provider as fallback"
        ])
    elif error.error_code == ErrorCode.FILE_NOT_FOUND:
        suggestions.extend([
            "Check if the file path is correct",
            "Verify the file exists and is accessible",
            "Make sure you're in the correct directory"
        ])
    elif error.error_code == ErrorCode.PROJECT_NOT_FOUND:
        suggestions.extend([
            "Run 'qgen status' to see available projects",
            "Initialize a new project with 'qgen init'",
            "Check if you're in the correct directory"
        ])

    if suggestions:
        suggestion_text = "\n".join(f"  • {s}" for s in suggestions)
        return f"{base_message}\n\nSuggestions:\n{suggestion_text}"

    return base_message


def chain_errors(*errors: Exception) -> QGenError:
    """Chain multiple errors together for complex failure scenarios."""
    if not errors:
        return QGenError("Unknown error occurred", ErrorCode.UNKNOWN_ERROR)

    primary_error = errors[0]
    chained_context = []

    for i, error in enumerate(errors):
        chained_context.append({
            "step": i + 1,
            "error": str(error),
            "type": type(error).__name__
        })

    if isinstance(primary_error, QGenError):
        primary_error.context["error_chain"] = chained_context
        return primary_error
    else:
        return QGenError(
            f"Multiple errors occurred: {primary_error}",
            ErrorCode.PROCESSING_ERROR,
            context={"error_chain": chained_context},
            cause=primary_error
        )