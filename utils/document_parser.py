"""
Document parsing utilities for the SRC to Application Generator.

This module provides functionality to parse various document formats
including PDF, DOCX, and Markdown files into structured text.
"""

import mimetypes
import re
from pathlib import Path
from typing import Dict, List, Optional, Tuple, Union

import markdown
from bs4 import BeautifulSoup
from docx import Document
from PyPDF2 import PdfReader

from .exceptions import ParsingError, UnsupportedFileFormatError
from .logging_config import LoggerMixin


class DocumentSection:
    """Represents a section of a parsed document."""
    
    def __init__(self, title: str, content: str, level: int = 1, 
                 line_number: Optional[int] = None):
        self.title = title
        self.content = content
        self.level = level
        self.line_number = line_number
        self.subsections: List[DocumentSection] = []
    
    def add_subsection(self, subsection: 'DocumentSection') -> None:
        """Add a subsection to this section."""
        self.subsections.append(subsection)
    
    def to_dict(self) -> Dict:
        """Convert section to dictionary."""
        return {
            "title": self.title,
            "content": self.content,
            "level": self.level,
            "line_number": self.line_number,
            "subsections": [sub.to_dict() for sub in self.subsections]
        }
    
    def __str__(self) -> str:
        return f"Section(title='{self.title}', level={self.level}, content_length={len(self.content)})"


class ParsedDocument:
    """Represents a completely parsed document with structured content."""
    
    def __init__(self, raw_text: str, file_path: Optional[str] = None, 
                 file_type: Optional[str] = None):
        self.raw_text = raw_text
        self.file_path = file_path
        self.file_type = file_type
        self.sections: List[DocumentSection] = []
        self.metadata: Dict = {}
    
    def add_section(self, section: DocumentSection) -> None:
        """Add a section to the document."""
        self.sections.append(section)
    
    def get_section_by_title(self, title: str) -> Optional[DocumentSection]:
        """Get a section by its title."""
        for section in self.sections:
            if section.title.lower() == title.lower():
                return section
        return None
    
    def get_all_text(self) -> str:
        """Get all text content from all sections."""
        return "\n\n".join([
            f"# {section.title}\n{section.content}"
            for section in self.sections
        ])
    
    def to_dict(self) -> Dict:
        """Convert document to dictionary."""
        return {
            "file_path": self.file_path,
            "file_type": self.file_type,
            "raw_text": self.raw_text,
            "sections": [section.to_dict() for section in self.sections],
            "metadata": self.metadata
        }
    
    def __str__(self) -> str:
        return f"ParsedDocument(sections={len(self.sections)}, text_length={len(self.raw_text)})"


class DocumentParser(LoggerMixin):
    """Main document parser supporting multiple file formats."""
    
    SUPPORTED_EXTENSIONS = {'.pdf', '.docx', '.md', '.txt'}
    SUPPORTED_MIME_TYPES = {
        'application/pdf',
        'application/vnd.openxmlformats-officedocument.wordprocessingml.document',
        'text/markdown',
        'text/plain'
    }
    
    def __init__(self):
        """Initialize the document parser."""
        self.logger.info("Document parser initialized")
    
    def parse_file(self, file_path: Union[str, Path]) -> ParsedDocument:
        """
        Parse a document file into structured content.
        
        Args:
            file_path: Path to the document file
            
        Returns:
            ParsedDocument with structured content
            
        Raises:
            UnsupportedFileFormatError: If file format is not supported
            ParsingError: If parsing fails
        """
        file_path = Path(file_path)
        
        if not file_path.exists():
            raise ParsingError(f"File not found: {file_path}")
        
        # Detect file type
        file_type = self._detect_file_type(file_path)
        
        self.logger.info(
            "Starting document parsing",
            file_path=str(file_path),
            file_type=file_type,
            file_size=file_path.stat().st_size
        )
        
        try:
            # Parse based on file type
            if file_type == 'pdf':
                raw_text = self._parse_pdf(file_path)
            elif file_type == 'docx':
                raw_text = self._parse_docx(file_path)
            elif file_type in ['md', 'markdown']:
                raw_text = self._parse_markdown(file_path)
            elif file_type == 'txt':
                raw_text = self._parse_text(file_path)
            else:
                raise UnsupportedFileFormatError(
                    file_type, 
                    list(self.SUPPORTED_EXTENSIONS)
                )
            
            # Create parsed document
            parsed_doc = ParsedDocument(
                raw_text=raw_text,
                file_path=str(file_path),
                file_type=file_type
            )
            
            # Extract sections
            self._extract_sections(parsed_doc)
            
            self.logger.info(
                "Document parsing completed",
                file_path=str(file_path),
                sections_found=len(parsed_doc.sections),
                text_length=len(raw_text)
            )
            
            return parsed_doc
            
        except Exception as e:
            self.logger.error(
                "Document parsing failed",
                file_path=str(file_path),
                error=str(e)
            )
            raise ParsingError(
                f"Failed to parse document: {e}",
                file_path=str(file_path),
                file_type=file_type
            )
    
    def parse_content(self, content: str, content_type: str = 'txt') -> ParsedDocument:
        """
        Parse document content directly from string.
        
        Args:
            content: Document content as string
            content_type: Type of content ('txt', 'md', 'html')
            
        Returns:
            ParsedDocument with structured content
        """
        self.logger.info(
            "Parsing content directly",
            content_type=content_type,
            content_length=len(content)
        )
        
        try:
            parsed_doc = ParsedDocument(
                raw_text=content,
                file_type=content_type
            )
            
            # Extract sections
            self._extract_sections(parsed_doc)
            
            return parsed_doc
            
        except Exception as e:
            raise ParsingError(f"Failed to parse content: {e}")
    
    def _detect_file_type(self, file_path: Path) -> str:
        """Detect file type from extension and MIME type."""
        # Check extension first
        extension = file_path.suffix.lower()
        
        if extension == '.pdf':
            return 'pdf'
        elif extension == '.docx':
            return 'docx'
        elif extension in ['.md', '.markdown']:
            return 'md'
        elif extension == '.txt':
            return 'txt'
        
        # Fallback to MIME type detection
        mime_type, _ = mimetypes.guess_type(str(file_path))
        
        if mime_type == 'application/pdf':
            return 'pdf'
        elif mime_type == 'application/vnd.openxmlformats-officedocument.wordprocessingml.document':
            return 'docx'
        elif mime_type == 'text/markdown':
            return 'md'
        elif mime_type == 'text/plain':
            return 'txt'
        
        raise UnsupportedFileFormatError(
            extension or mime_type or "unknown",
            list(self.SUPPORTED_EXTENSIONS)
        )
    
    def _parse_pdf(self, file_path: Path) -> str:
        """Parse PDF file and extract text."""
        try:
            with open(file_path, 'rb') as file:
                reader = PdfReader(file)
                text_parts = []
                
                for page_num, page in enumerate(reader.pages, 1):
                    try:
                        page_text = page.extract_text()
                        if page_text.strip():
                            text_parts.append(f"[Page {page_num}]\n{page_text}")
                    except Exception as e:
                        self.logger.warning(
                            f"Failed to extract text from page {page_num}",
                            error=str(e)
                        )
                
                return "\n\n".join(text_parts)
                
        except Exception as e:
            raise ParsingError(f"PDF parsing failed: {e}")
    
    def _parse_docx(self, file_path: Path) -> str:
        """Parse DOCX file and extract text."""
        try:
            doc = Document(file_path)
            text_parts = []
            
            for paragraph in doc.paragraphs:
                if paragraph.text.strip():
                    text_parts.append(paragraph.text)
            
            # Also extract text from tables
            for table in doc.tables:
                for row in table.rows:
                    row_text = []
                    for cell in row.cells:
                        if cell.text.strip():
                            row_text.append(cell.text.strip())
                    if row_text:
                        text_parts.append(" | ".join(row_text))
            
            return "\n\n".join(text_parts)
            
        except Exception as e:
            raise ParsingError(f"DOCX parsing failed: {e}")
    
    def _parse_markdown(self, file_path: Path) -> str:
        """Parse Markdown file."""
        try:
            with open(file_path, 'r', encoding='utf-8') as file:
                return file.read()
        except Exception as e:
            raise ParsingError(f"Markdown parsing failed: {e}")
    
    def _parse_text(self, file_path: Path) -> str:
        """Parse plain text file."""
        try:
            with open(file_path, 'r', encoding='utf-8') as file:
                return file.read()
        except UnicodeDecodeError:
            # Try with different encoding
            with open(file_path, 'r', encoding='latin-1') as file:
                return file.read()
        except Exception as e:
            raise ParsingError(f"Text parsing failed: {e}")
    
    def _extract_sections(self, parsed_doc: ParsedDocument) -> None:
        """Extract sections from parsed document text."""
        text = parsed_doc.raw_text
        
        # Try different section detection methods
        if parsed_doc.file_type == 'md':
            self._extract_markdown_sections(parsed_doc)
        else:
            self._extract_generic_sections(parsed_doc)
    
    def _extract_markdown_sections(self, parsed_doc: ParsedDocument) -> None:
        """Extract sections from Markdown content."""
        lines = parsed_doc.raw_text.split('\n')
        current_section = None
        content_lines = []
        
        for line_num, line in enumerate(lines, 1):
            # Check for headers
            header_match = re.match(r'^(#{1,6})\s+(.+)$', line.strip())
            
            if header_match:
                # Save previous section
                if current_section:
                    current_section.content = '\n'.join(content_lines).strip()
                    parsed_doc.add_section(current_section)
                
                # Start new section
                level = len(header_match.group(1))
                title = header_match.group(2).strip()
                current_section = DocumentSection(
                    title=title,
                    content="",
                    level=level,
                    line_number=line_num
                )
                content_lines = []
            else:
                # Add to current section content
                if line.strip() or content_lines:  # Keep empty lines only if there's content
                    content_lines.append(line)
        
        # Save last section
        if current_section:
            current_section.content = '\n'.join(content_lines).strip()
            parsed_doc.add_section(current_section)
    
    def _extract_generic_sections(self, parsed_doc: ParsedDocument) -> None:
        """Extract sections from generic text using common patterns."""
        text = parsed_doc.raw_text
        
        # Try to find sections using various patterns
        patterns = [
            r'^([A-Z][A-Z\s]{2,})\s*$',  # ALL CAPS headers
            r'^(\d+\.?\s+[A-Z][^.!?]*)\s*$',  # Numbered sections
            r'^([A-Z][a-z\s]+):?\s*$',  # Title case headers
        ]
        
        sections_found = False
        
        for pattern in patterns:
            sections = self._extract_sections_by_pattern(text, pattern)
            if len(sections) > 1:  # Found meaningful sections
                for section in sections:
                    parsed_doc.add_section(section)
                sections_found = True
                break
        
        # If no sections found, create a single section with all content
        if not sections_found:
            section = DocumentSection(
                title="Document Content",
                content=text.strip(),
                level=1
            )
            parsed_doc.add_section(section)
    
    def _extract_sections_by_pattern(self, text: str, pattern: str) -> List[DocumentSection]:
        """Extract sections using a specific regex pattern."""
        lines = text.split('\n')
        sections = []
        current_section = None
        content_lines = []
        
        for line_num, line in enumerate(lines, 1):
            match = re.match(pattern, line.strip())
            
            if match:
                # Save previous section
                if current_section:
                    current_section.content = '\n'.join(content_lines).strip()
                    sections.append(current_section)
                
                # Start new section
                title = match.group(1).strip()
                current_section = DocumentSection(
                    title=title,
                    content="",
                    level=1,
                    line_number=line_num
                )
                content_lines = []
            else:
                # Add to current section content
                content_lines.append(line)
        
        # Save last section
        if current_section:
            current_section.content = '\n'.join(content_lines).strip()
            sections.append(current_section)
        
        return sections


# Convenience function for quick parsing
def parse_document(file_path: Union[str, Path]) -> ParsedDocument:
    """
    Convenience function to parse a document.
    
    Args:
        file_path: Path to the document file
        
    Returns:
        ParsedDocument with structured content
    """
    parser = DocumentParser()
    return parser.parse_file(file_path)