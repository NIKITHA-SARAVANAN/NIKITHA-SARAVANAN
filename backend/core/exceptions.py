"""
Backend-specific exception classes for the FastAPI application.

These exceptions are specifically designed for HTTP responses and
FastAPI error handling.
"""

from typing import Any, Dict, List, Optional


class ValidationError(Exception):
    """Raised when request validation fails."""
    
    def __init__(self, errors: List[Dict[str, Any]]):
        self.errors = errors
        super().__init__("Validation failed")


class NotFoundError(Exception):
    """Raised when a requested resource is not found."""
    
    def __init__(self, resource: str, identifier: str):
        self.resource = resource
        self.identifier = identifier
        super().__init__(f"{resource} with id '{identifier}' not found")


class UnauthorizedError(Exception):
    """Raised when authentication is required but not provided."""
    
    def __init__(self, message: str = "Authentication required"):
        super().__init__(message)


class ForbiddenError(Exception):
    """Raised when access is forbidden."""
    
    def __init__(self, message: str = "Access forbidden"):
        super().__init__(message)


class ConflictError(Exception):
    """Raised when a resource conflict occurs."""
    
    def __init__(self, resource: str, message: str):
        self.resource = resource
        super().__init__(f"Conflict with {resource}: {message}")


class ServiceUnavailableError(Exception):
    """Raised when a service is temporarily unavailable."""
    
    def __init__(self, service: str, message: str = "Service temporarily unavailable"):
        self.service = service
        super().__init__(f"{service}: {message}")