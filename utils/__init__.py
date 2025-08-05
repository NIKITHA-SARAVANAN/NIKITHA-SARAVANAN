"""
Utilities package for document parsing and processing.
"""

from .document_parser import DocumentParser, ParsedDocument
from .file_detector import FileTypeDetector

__all__ = ["DocumentParser", "ParsedDocument", "FileTypeDetector"]