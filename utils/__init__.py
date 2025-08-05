"""
Utility modules for the SRS to Angular+FastAPI generator.

This package contains utilities for document parsing, logging, exception handling,
and other common functionality used across the application.
"""

from .document_parser import DocumentParser, ParsedDocument, DocumentParsingError
from .logger import get_logger, setup_structured_logging, log_agent_activity
from .exceptions import (
    SRSGeneratorError,
    DocumentParsingError,
    UnsupportedFileFormatError,
    ProcessingError,
    AgentExecutionError,
    ValidationError
)

__all__ = [
    # Document parsing
    "DocumentParser",
    "ParsedDocument", 
    "DocumentParsingError",
    
    # Logging
    "get_logger",
    "setup_structured_logging",
    "log_agent_activity",
    
    # Exceptions
    "SRSGeneratorError",
    "DocumentParsingError",
    "UnsupportedFileFormatError", 
    "ProcessingError",
    "AgentExecutionError",
    "ValidationError"
]