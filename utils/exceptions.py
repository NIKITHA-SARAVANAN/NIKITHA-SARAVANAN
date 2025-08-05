"""
Custom exception classes for the SRC to Application Generator.

This module defines all custom exceptions used throughout the application
for better error handling and debugging.
"""

from typing import Any, Dict, Optional


class SRCGeneratorException(Exception):
    """Base exception class for all SRC Generator related errors."""
    
    def __init__(self, message: str, details: Optional[Dict[str, Any]] = None):
        self.message = message
        self.details = details or {}
        super().__init__(self.message)
    
    def __str__(self) -> str:
        if self.details:
            return f"{self.message} | Details: {self.details}"
        return self.message


class ParsingError(SRCGeneratorException):
    """Raised when document parsing fails."""
    
    def __init__(self, message: str, file_path: Optional[str] = None, 
                 file_type: Optional[str] = None, details: Optional[Dict[str, Any]] = None):
        self.file_path = file_path
        self.file_type = file_type
        
        error_details = {
            "file_path": file_path,
            "file_type": file_type,
            **(details or {})
        }
        
        super().__init__(message, error_details)


class UnsupportedFileFormatError(SRCGeneratorException):
    """Raised when an unsupported file format is encountered."""
    
    def __init__(self, file_format: str, supported_formats: list):
        self.file_format = file_format
        self.supported_formats = supported_formats
        
        message = f"Unsupported file format: {file_format}. Supported formats: {', '.join(supported_formats)}"
        details = {
            "file_format": file_format,
            "supported_formats": supported_formats
        }
        
        super().__init__(message, details)


class ProcessingError(SRCGeneratorException):
    """Raised when document or data processing fails."""
    
    def __init__(self, message: str, stage: Optional[str] = None, 
                 agent: Optional[str] = None, details: Optional[Dict[str, Any]] = None):
        self.stage = stage
        self.agent = agent
        
        error_details = {
            "processing_stage": stage,
            "agent": agent,
            **(details or {})
        }
        
        super().__init__(message, error_details)


class AgentError(SRCGeneratorException):
    """Raised when an agent workflow fails."""
    
    def __init__(self, message: str, agent_name: str, 
                 iteration: Optional[int] = None, details: Optional[Dict[str, Any]] = None):
        self.agent_name = agent_name
        self.iteration = iteration
        
        error_details = {
            "agent_name": agent_name,
            "iteration": iteration,
            **(details or {})
        }
        
        super().__init__(message, error_details)


class ValidationError(SRCGeneratorException):
    """Raised when validation fails."""
    
    def __init__(self, message: str, validation_type: str, 
                 errors: Optional[list] = None, details: Optional[Dict[str, Any]] = None):
        self.validation_type = validation_type
        self.errors = errors or []
        
        error_details = {
            "validation_type": validation_type,
            "validation_errors": self.errors,
            **(details or {})
        }
        
        super().__init__(message, error_details)


class ConfigurationError(SRCGeneratorException):
    """Raised when configuration is invalid or missing."""
    
    def __init__(self, message: str, config_key: Optional[str] = None, 
                 details: Optional[Dict[str, Any]] = None):
        self.config_key = config_key
        
        error_details = {
            "config_key": config_key,
            **(details or {})
        }
        
        super().__init__(message, error_details)


class MCPServerError(SRCGeneratorException):
    """Raised when MCP server operations fail."""
    
    def __init__(self, message: str, server_type: str, 
                 operation: Optional[str] = None, details: Optional[Dict[str, Any]] = None):
        self.server_type = server_type
        self.operation = operation
        
        error_details = {
            "server_type": server_type,
            "operation": operation,
            **(details or {})
        }
        
        super().__init__(message, error_details)


class CodeGenerationError(SRCGeneratorException):
    """Raised when code generation fails."""
    
    def __init__(self, message: str, component_type: str, 
                 template: Optional[str] = None, details: Optional[Dict[str, Any]] = None):
        self.component_type = component_type
        self.template = template
        
        error_details = {
            "component_type": component_type,
            "template": template,
            **(details or {})
        }
        
        super().__init__(message, error_details)