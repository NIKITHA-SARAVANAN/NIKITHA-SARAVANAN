"""
File type detection utility for SRS documents.
"""

import magic
import mimetypes
from pathlib import Path
from typing import Optional, Dict, Any
import logging

logger = logging.getLogger(__name__)


class FileTypeDetector:
    """Detects file types for document parsing."""
    
    SUPPORTED_TYPES = {
        'application/pdf': 'pdf',
        'application/vnd.openxmlformats-officedocument.wordprocessingml.document': 'docx',
        'application/msword': 'doc',
        'text/markdown': 'md',
        'text/plain': 'txt',
        'text/x-markdown': 'md'
    }
    
    def __init__(self):
        """Initialize the file type detector."""
        try:
            self.magic = magic.Magic(mime=True)
        except Exception as e:
            logger.warning(f"Could not initialize python-magic: {e}")
            self.magic = None
    
    def detect_type(self, file_path: Path) -> Dict[str, Any]:
        """
        Detect the file type and return metadata.
        
        Args:
            file_path: Path to the file to analyze
            
        Returns:
            Dictionary containing file type information
        """
        result = {
            'file_path': str(file_path),
            'file_name': file_path.name,
            'file_size': 0,
            'mime_type': None,
            'detected_type': None,
            'is_supported': False,
            'error': None
        }
        
        try:
            if not file_path.exists():
                result['error'] = "File does not exist"
                return result
            
            result['file_size'] = file_path.stat().st_size
            
            # Try python-magic first
            if self.magic:
                try:
                    mime_type = self.magic.from_file(str(file_path))
                    result['mime_type'] = mime_type
                except Exception as e:
                    logger.warning(f"Magic detection failed: {e}")
            
            # Fallback to mimetypes
            if not result['mime_type']:
                mime_type, _ = mimetypes.guess_type(str(file_path))
                result['mime_type'] = mime_type
            
            # Handle markdown files by extension if mime detection fails
            if file_path.suffix.lower() in ['.md', '.markdown']:
                result['mime_type'] = 'text/markdown'
            
            # Determine if supported
            if result['mime_type'] in self.SUPPORTED_TYPES:
                result['detected_type'] = self.SUPPORTED_TYPES[result['mime_type']]
                result['is_supported'] = True
            else:
                result['detected_type'] = 'unknown'
                result['error'] = f"Unsupported file type: {result['mime_type']}"
            
        except Exception as e:
            result['error'] = f"Error detecting file type: {str(e)}"
            logger.error(f"File type detection failed for {file_path}: {e}")
        
        return result
    
    def is_supported(self, file_path: Path) -> bool:
        """
        Check if a file type is supported.
        
        Args:
            file_path: Path to the file
            
        Returns:
            True if supported, False otherwise
        """
        detection_result = self.detect_type(file_path)
        return detection_result['is_supported']
    
    def get_supported_extensions(self) -> list:
        """Get list of supported file extensions."""
        return ['.pdf', '.docx', '.doc', '.md', '.markdown', '.txt']