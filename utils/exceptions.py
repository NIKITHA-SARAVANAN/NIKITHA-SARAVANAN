"""
Custom exceptions for the SRS to Angular+FastAPI generator.

This module defines a hierarchy of custom exceptions for different types of
errors that can occur during document processing and code generation.
"""

from typing import Optional, Dict, Any


class SRSGeneratorError(Exception):
    """
    Base exception class for all SRS Generator errors.
    
    All custom exceptions in the application should inherit from this class.
    """
    
    def __init__(
        self, 
        message: str, 
        error_code: Optional[str] = None,
        details: Optional[Dict[str, Any]] = None
    ):
        """
        Initialize the exception.
        
        Args:
            message: Human-readable error message
            error_code: Machine-readable error code for API responses
            details: Additional error details for debugging
        """
        super().__init__(message)
        self.message = message
        self.error_code = error_code or self.__class__.__name__
        self.details = details or {}
    
    def to_dict(self) -> Dict[str, Any]:
        """Convert exception to dictionary for JSON serialization."""
        return {
            "error": self.error_code,
            "message": self.message,
            "details": self.details
        }


class DocumentParsingError(SRSGeneratorError):
    """
    Raised when document parsing fails.
    
    This includes errors reading files, extracting text, or parsing content.
    """
    
    def __init__(
        self, 
        message: str, 
        file_path: Optional[str] = None,
        file_type: Optional[str] = None,
        **kwargs
    ):
        details = kwargs.get("details", {})
        if file_path:
            details["file_path"] = file_path
        if file_type:
            details["file_type"] = file_type
        
        super().__init__(message, error_code="DOCUMENT_PARSING_ERROR", details=details)
        self.file_path = file_path
        self.file_type = file_type


class UnsupportedFileFormatError(DocumentParsingError):
    """
    Raised when an unsupported file format is encountered.
    
    This is a specific type of document parsing error for format issues.
    """
    
    def __init__(self, file_type: str, supported_formats: list, **kwargs):
        message = f"Unsupported file format: {file_type}. Supported formats: {', '.join(supported_formats)}"
        details = kwargs.get("details", {})
        details.update({
            "unsupported_format": file_type,
            "supported_formats": supported_formats
        })
        
        super().__init__(
            message, 
            error_code="UNSUPPORTED_FILE_FORMAT",
            file_type=file_type,
            details=details
        )
        self.supported_formats = supported_formats


class ProcessingError(SRSGeneratorError):
    """
    Raised when document or code processing fails.
    
    This is a general processing error that can occur during various stages
    of the document analysis and code generation pipeline.
    """
    
    def __init__(
        self, 
        message: str, 
        stage: Optional[str] = None,
        agent_name: Optional[str] = None,
        **kwargs
    ):
        details = kwargs.get("details", {})
        if stage:
            details["processing_stage"] = stage
        if agent_name:
            details["agent_name"] = agent_name
        
        super().__init__(message, error_code="PROCESSING_ERROR", details=details)
        self.stage = stage
        self.agent_name = agent_name


class AgentExecutionError(ProcessingError):
    """
    Raised when an agent fails to execute successfully.
    
    This includes timeout errors, validation failures, and other agent-specific issues.
    """
    
    def __init__(
        self, 
        message: str, 
        agent_name: str,
        execution_stage: Optional[str] = None,
        retry_count: Optional[int] = None,
        **kwargs
    ):
        details = kwargs.get("details", {})
        details.update({
            "agent_name": agent_name,
            "execution_stage": execution_stage,
            "retry_count": retry_count
        })
        
        super().__init__(
            message, 
            error_code="AGENT_EXECUTION_ERROR",
            stage="agent_execution",
            agent_name=agent_name,
            details=details
        )
        self.execution_stage = execution_stage
        self.retry_count = retry_count


class ValidationError(SRSGeneratorError):
    """
    Raised when validation fails.
    
    This includes input validation, output validation, and cross-validation errors.
    """
    
    def __init__(
        self, 
        message: str, 
        validation_type: Optional[str] = None,
        field_name: Optional[str] = None,
        **kwargs
    ):
        details = kwargs.get("details", {})
        if validation_type:
            details["validation_type"] = validation_type
        if field_name:
            details["field_name"] = field_name
        
        super().__init__(message, error_code="VALIDATION_ERROR", details=details)
        self.validation_type = validation_type
        self.field_name = field_name


class TimeoutError(AgentExecutionError):
    """
    Raised when an operation times out.
    
    This is a specific type of agent execution error for timeout scenarios.
    """
    
    def __init__(
        self, 
        message: str, 
        agent_name: str,
        timeout_duration: Optional[int] = None,
        **kwargs
    ):
        details = kwargs.get("details", {})
        if timeout_duration:
            details["timeout_duration"] = timeout_duration
        
        super().__init__(
            message, 
            agent_name=agent_name,
            error_code="TIMEOUT_ERROR",
            execution_stage="timeout",
            details=details
        )
        self.timeout_duration = timeout_duration


class ConfigurationError(SRSGeneratorError):
    """
    Raised when configuration is invalid or missing.
    
    This includes missing environment variables, invalid settings, etc.
    """
    
    def __init__(
        self, 
        message: str, 
        config_key: Optional[str] = None,
        **kwargs
    ):
        details = kwargs.get("details", {})
        if config_key:
            details["config_key"] = config_key
        
        super().__init__(message, error_code="CONFIGURATION_ERROR", details=details)
        self.config_key = config_key


class DatabaseError(SRSGeneratorError):
    """
    Raised when database operations fail.
    
    This includes connection errors, query failures, and data integrity issues.
    """
    
    def __init__(
        self, 
        message: str, 
        operation: Optional[str] = None,
        table_name: Optional[str] = None,
        **kwargs
    ):
        details = kwargs.get("details", {})
        if operation:
            details["database_operation"] = operation
        if table_name:
            details["table_name"] = table_name
        
        super().__init__(message, error_code="DATABASE_ERROR", details=details)
        self.operation = operation
        self.table_name = table_name


class ExternalServiceError(SRSGeneratorError):
    """
    Raised when external service calls fail.
    
    This includes API calls, web searches, and other external dependencies.
    """
    
    def __init__(
        self, 
        message: str, 
        service_name: Optional[str] = None,
        status_code: Optional[int] = None,
        **kwargs
    ):
        details = kwargs.get("details", {})
        if service_name:
            details["service_name"] = service_name
        if status_code:
            details["status_code"] = status_code
        
        super().__init__(message, error_code="EXTERNAL_SERVICE_ERROR", details=details)
        self.service_name = service_name
        self.status_code = status_code


class SecurityError(SRSGeneratorError):
    """
    Raised when security violations are detected.
    
    This includes authentication failures, authorization errors, and security policy violations.
    """
    
    def __init__(
        self, 
        message: str, 
        security_issue: Optional[str] = None,
        **kwargs
    ):
        details = kwargs.get("details", {})
        if security_issue:
            details["security_issue"] = security_issue
        
        super().__init__(message, error_code="SECURITY_ERROR", details=details)
        self.security_issue = security_issue


# Exception mapping for HTTP status codes
HTTP_EXCEPTION_MAP = {
    400: ValidationError,
    401: SecurityError,
    403: SecurityError,
    404: ProcessingError,
    408: TimeoutError,
    422: ValidationError,
    500: ProcessingError,
    502: ExternalServiceError,
    503: ExternalServiceError,
    504: TimeoutError
}


def get_exception_for_status_code(status_code: int) -> type:
    """
    Get the appropriate exception class for an HTTP status code.
    
    Args:
        status_code: HTTP status code
        
    Returns:
        Exception class to use for this status code
    """
    return HTTP_EXCEPTION_MAP.get(status_code, SRSGeneratorError)


def handle_exception(func):
    """
    Decorator to handle exceptions and convert them to appropriate types.
    
    This decorator can be used to wrap functions and automatically convert
    standard exceptions to our custom exception hierarchy.
    """
    import functools
    
    @functools.wraps(func)
    def wrapper(*args, **kwargs):
        try:
            return func(*args, **kwargs)
        except SRSGeneratorError:
            # Re-raise our custom exceptions as-is
            raise
        except FileNotFoundError as e:
            raise DocumentParsingError(f"File not found: {e}")
        except PermissionError as e:
            raise SecurityError(f"Permission denied: {e}")
        except TimeoutError as e:
            raise TimeoutError(f"Operation timed out: {e}", agent_name="unknown")
        except ValueError as e:
            raise ValidationError(f"Invalid value: {e}")
        except Exception as e:
            # Convert unexpected exceptions to ProcessingError
            raise ProcessingError(f"Unexpected error: {e}")
    
    return wrapper