"""
Document parsing utilities for the SRS to Angular+FastAPI generator.

This module provides robust document parsing capabilities for extracting and
structuring content from various file formats including PDF, DOCX, and Markdown.
"""

import re
import mimetypes
from pathlib import Path
from typing import Dict, List, Optional, Union, Any
from dataclasses import dataclass
from abc import ABC, abstractmethod

# Import document processing libraries
try:
    import PyPDF2
except ImportError:
    PyPDF2 = None

try:
    from docx import Document as DocxDocument
except ImportError:
    DocxDocument = None

try:
    import markdown
    from markdown.extensions import toc
except ImportError:
    markdown = None

from .exceptions import DocumentParsingError, UnsupportedFileFormatError
from .logger import get_logger

logger = get_logger(__name__)


@dataclass
class DocumentSection:
    """
    Represents a structured section of a document.
    
    A section has a title, content, level (for hierarchical structure),
    and metadata about its position and context.
    """
    title: str
    content: str
    level: int  # Heading level (1-6)
    line_start: Optional[int] = None
    line_end: Optional[int] = None
    metadata: Optional[Dict[str, Any]] = None
    
    def __post_init__(self):
        if self.metadata is None:
            self.metadata = {}


@dataclass
class ParsedDocument:
    """
    Represents a fully parsed document with structured content.
    
    Contains the raw text, structured sections, metadata, and
    extracted requirements or specifications.
    """
    raw_text: str
    sections: List[DocumentSection]
    metadata: Dict[str, Any]
    file_path: Optional[str] = None
    file_type: Optional[str] = None
    
    def get_sections_by_level(self, level: int) -> List[DocumentSection]:
        """Get all sections at a specific heading level."""
        return [section for section in self.sections if section.level == level]
    
    def get_section_by_title(self, title: str, case_sensitive: bool = False) -> Optional[DocumentSection]:
        """Get a section by its title."""
        for section in self.sections:
            section_title = section.title if case_sensitive else section.title.lower()
            search_title = title if case_sensitive else title.lower()
            if section_title == search_title:
                return section
        return None
    
    def get_sections_containing(self, keyword: str, case_sensitive: bool = False) -> List[DocumentSection]:
        """Get all sections containing a specific keyword in title or content."""
        keyword_lower = keyword if case_sensitive else keyword.lower()
        matching_sections = []
        
        for section in self.sections:
            title = section.title if case_sensitive else section.title.lower()
            content = section.content if case_sensitive else section.content.lower()
            
            if keyword_lower in title or keyword_lower in content:
                matching_sections.append(section)
        
        return matching_sections
    
    def extract_requirements(self) -> List[str]:
        """
        Extract requirements from the document.
        
        Looks for numbered lists, bullet points, and sections that
        typically contain requirements.
        """
        requirements = []
        requirement_patterns = [
            r'(?:REQ|REQUIREMENT)\s*[-:]?\s*(\d+)\.?\s*(.+)',
            r'(\d+\.\d+(?:\.\d+)?)\s+(.+)',
            r'[•\-\*]\s*(.+)',
        ]
        
        # Look in sections that commonly contain requirements
        requirement_sections = [
            'requirements', 'functional requirements', 'non-functional requirements',
            'system requirements', 'user requirements', 'business requirements',
            'specifications', 'features', 'capabilities'
        ]
        
        for section in self.sections:
            section_title_lower = section.title.lower()
            
            # Check if this section likely contains requirements
            if any(req_section in section_title_lower for req_section in requirement_sections):
                # Extract requirements using patterns
                for pattern in requirement_patterns:
                    matches = re.finditer(pattern, section.content, re.MULTILINE | re.IGNORECASE)
                    for match in matches:
                        if len(match.groups()) == 2:
                            req_id, req_text = match.groups()
                            requirements.append(f"{req_id.strip()}: {req_text.strip()}")
                        else:
                            requirements.append(match.group(1).strip())
        
        return requirements
    
    def get_table_of_contents(self) -> List[Dict[str, Any]]:
        """Generate a table of contents from the document sections."""
        toc = []
        for section in self.sections:
            toc.append({
                'title': section.title,
                'level': section.level,
                'line_start': section.line_start,
                'line_end': section.line_end
            })
        return toc


class DocumentParser(ABC):
    """
    Abstract base class for document parsers.
    
    Defines the interface that all document parsers must implement.
    """
    
    @abstractmethod
    def can_parse(self, file_path: Union[str, Path]) -> bool:
        """Check if this parser can handle the given file."""
        pass
    
    @abstractmethod
    def parse(self, file_path: Union[str, Path]) -> ParsedDocument:
        """Parse the document and return structured content."""
        pass


class PDFParser(DocumentParser):
    """Parser for PDF documents using PyPDF2."""
    
    def can_parse(self, file_path: Union[str, Path]) -> bool:
        """Check if this is a PDF file."""
        if PyPDF2 is None:
            return False
        
        file_path = Path(file_path)
        return file_path.suffix.lower() == '.pdf'
    
    def parse(self, file_path: Union[str, Path]) -> ParsedDocument:
        """Parse PDF document."""
        if PyPDF2 is None:
            raise DocumentParsingError(
                "PyPDF2 not available. Install with: pip install PyPDF2",
                file_path=str(file_path),
                file_type="pdf"
            )
        
        file_path = Path(file_path)
        
        try:
            with open(file_path, 'rb') as file:
                pdf_reader = PyPDF2.PdfReader(file)
                
                # Extract metadata
                metadata = {
                    'page_count': len(pdf_reader.pages),
                    'file_size': file_path.stat().st_size,
                    'parser': 'PDFParser'
                }
                
                # Add PDF metadata if available
                if pdf_reader.metadata:
                    pdf_metadata = {
                        'title': pdf_reader.metadata.get('/Title', ''),
                        'author': pdf_reader.metadata.get('/Author', ''),
                        'subject': pdf_reader.metadata.get('/Subject', ''),
                        'creator': pdf_reader.metadata.get('/Creator', ''),
                        'producer': pdf_reader.metadata.get('/Producer', ''),
                        'creation_date': pdf_reader.metadata.get('/CreationDate', ''),
                        'modification_date': pdf_reader.metadata.get('/ModDate', '')
                    }
                    metadata.update(pdf_metadata)
                
                # Extract text from all pages
                raw_text = ""
                page_texts = []
                
                for page_num, page in enumerate(pdf_reader.pages):
                    try:
                        page_text = page.extract_text()
                        page_texts.append(page_text)
                        raw_text += f"\n--- Page {page_num + 1} ---\n"
                        raw_text += page_text
                    except Exception as e:
                        logger.warning(f"Failed to extract text from page {page_num + 1}: {e}")
                        continue
                
                # Parse sections from the raw text
                sections = self._parse_sections(raw_text)
                
                return ParsedDocument(
                    raw_text=raw_text,
                    sections=sections,
                    metadata=metadata,
                    file_path=str(file_path),
                    file_type="pdf"
                )
                
        except Exception as e:
            raise DocumentParsingError(
                f"Failed to parse PDF: {e}",
                file_path=str(file_path),
                file_type="pdf"
            )
    
    def _parse_sections(self, text: str) -> List[DocumentSection]:
        """Parse sections from PDF text using heuristics."""
        sections = []
        lines = text.split('\n')
        current_section = None
        current_content = []
        
        # Patterns for detecting headings
        heading_patterns = [
            r'^(\d+\.?\s+.+)$',  # Numbered headings
            r'^([A-Z][A-Z\s]+)$',  # ALL CAPS headings
            r'^(.+:)$',  # Colon-terminated headings
        ]
        
        for line_num, line in enumerate(lines):
            line = line.strip()
            if not line:
                continue
            
            # Check if this line looks like a heading
            is_heading = False
            heading_level = 1
            
            for pattern in heading_patterns:
                match = re.match(pattern, line)
                if match:
                    is_heading = True
                    # Simple heuristic for heading level based on numbering
                    if '.' in line and line[0].isdigit():
                        heading_level = line.count('.') + 1
                    break
            
            if is_heading:
                # Save previous section if exists
                if current_section:
                    current_section.content = '\n'.join(current_content)
                    sections.append(current_section)
                
                # Start new section
                current_section = DocumentSection(
                    title=line,
                    content="",
                    level=min(heading_level, 6),
                    line_start=line_num,
                    metadata={'detected_by': 'heuristic'}
                )
                current_content = []
            else:
                # Add to current section content
                if current_section:
                    current_content.append(line)
                else:
                    # Content before first heading - create a default section
                    if not sections:
                        current_section = DocumentSection(
                            title="Document Start",
                            content="",
                            level=1,
                            line_start=0,
                            metadata={'detected_by': 'default'}
                        )
                        current_content = [line]
        
        # Don't forget the last section
        if current_section:
            current_section.content = '\n'.join(current_content)
            current_section.line_end = len(lines) - 1
            sections.append(current_section)
        
        return sections


class DOCXParser(DocumentParser):
    """Parser for Microsoft Word documents using python-docx."""
    
    def can_parse(self, file_path: Union[str, Path]) -> bool:
        """Check if this is a DOCX file."""
        if DocxDocument is None:
            return False
        
        file_path = Path(file_path)
        return file_path.suffix.lower() in ['.docx', '.doc']
    
    def parse(self, file_path: Union[str, Path]) -> ParsedDocument:
        """Parse DOCX document."""
        if DocxDocument is None:
            raise DocumentParsingError(
                "python-docx not available. Install with: pip install python-docx",
                file_path=str(file_path),
                file_type="docx"
            )
        
        file_path = Path(file_path)
        
        try:
            doc = DocxDocument(file_path)
            
            # Extract metadata
            core_props = doc.core_properties
            metadata = {
                'title': core_props.title or '',
                'author': core_props.author or '',
                'subject': core_props.subject or '',
                'created': core_props.created.isoformat() if core_props.created else '',
                'modified': core_props.modified.isoformat() if core_props.modified else '',
                'last_modified_by': core_props.last_modified_by or '',
                'revision': core_props.revision or '',
                'file_size': file_path.stat().st_size,
                'parser': 'DOCXParser'
            }
            
            # Extract text and structure
            raw_text = ""
            sections = []
            current_section = None
            current_content = []
            line_num = 0
            
            for paragraph in doc.paragraphs:
                line_num += 1
                text = paragraph.text.strip()
                
                if not text:
                    continue
                
                raw_text += text + '\n'
                
                # Check if this paragraph is a heading
                if paragraph.style.name.startswith('Heading'):
                    # Extract heading level
                    try:
                        level = int(paragraph.style.name.split()[-1])
                    except (ValueError, IndexError):
                        level = 1
                    
                    # Save previous section
                    if current_section:
                        current_section.content = '\n'.join(current_content)
                        current_section.line_end = line_num - 1
                        sections.append(current_section)
                    
                    # Start new section
                    current_section = DocumentSection(
                        title=text,
                        content="",
                        level=level,
                        line_start=line_num,
                        metadata={'style': paragraph.style.name}
                    )
                    current_content = []
                
                else:
                    # Regular paragraph content
                    if current_section:
                        current_content.append(text)
                    else:
                        # Content before first heading
                        if not sections:
                            current_section = DocumentSection(
                                title="Document Start",
                                content="",
                                level=1,
                                line_start=1,
                                metadata={'style': 'default'}
                            )
                            current_content = [text]
            
            # Don't forget the last section
            if current_section:
                current_section.content = '\n'.join(current_content)
                current_section.line_end = line_num
                sections.append(current_section)
            
            return ParsedDocument(
                raw_text=raw_text,
                sections=sections,
                metadata=metadata,
                file_path=str(file_path),
                file_type="docx"
            )
            
        except Exception as e:
            raise DocumentParsingError(
                f"Failed to parse DOCX: {e}",
                file_path=str(file_path),
                file_type="docx"
            )


class MarkdownParser(DocumentParser):
    """Parser for Markdown documents."""
    
    def can_parse(self, file_path: Union[str, Path]) -> bool:
        """Check if this is a Markdown file."""
        file_path = Path(file_path)
        return file_path.suffix.lower() in ['.md', '.markdown', '.txt']
    
    def parse(self, file_path: Union[str, Path]) -> ParsedDocument:
        """Parse Markdown document."""
        file_path = Path(file_path)
        
        try:
            with open(file_path, 'r', encoding='utf-8') as file:
                raw_text = file.read()
            
            # Basic metadata
            metadata = {
                'file_size': file_path.stat().st_size,
                'parser': 'MarkdownParser'
            }
            
            # Parse YAML front matter if present
            frontmatter_match = re.match(r'^---\s*\n(.*?)\n---\s*\n', raw_text, re.DOTALL)
            content_start = 0
            
            if frontmatter_match:
                try:
                    import yaml
                    frontmatter = yaml.safe_load(frontmatter_match.group(1))
                    if isinstance(frontmatter, dict):
                        metadata.update(frontmatter)
                    content_start = frontmatter_match.end()
                except ImportError:
                    logger.warning("YAML not available for frontmatter parsing")
                except Exception as e:
                    logger.warning(f"Failed to parse frontmatter: {e}")
            
            # Extract content after frontmatter
            content = raw_text[content_start:]
            
            # Parse sections based on headers
            sections = self._parse_markdown_sections(content)
            
            return ParsedDocument(
                raw_text=raw_text,
                sections=sections,
                metadata=metadata,
                file_path=str(file_path),
                file_type="markdown"
            )
            
        except Exception as e:
            raise DocumentParsingError(
                f"Failed to parse Markdown: {e}",
                file_path=str(file_path),
                file_type="markdown"
            )
    
    def _parse_markdown_sections(self, content: str) -> List[DocumentSection]:
        """Parse Markdown sections based on headers."""
        sections = []
        lines = content.split('\n')
        current_section = None
        current_content = []
        
        for line_num, line in enumerate(lines):
            # Check for ATX headers (# ## ### etc.)
            atx_match = re.match(r'^(#{1,6})\s+(.+)$', line)
            
            # Check for Setext headers (underlined with = or -)
            setext_match = None
            if line_num > 0 and re.match(r'^[=-]+$', line.strip()):
                prev_line = lines[line_num - 1].strip()
                if prev_line:
                    level = 1 if line.strip().startswith('=') else 2
                    setext_match = (level, prev_line)
            
            if atx_match:
                # Save previous section
                if current_section:
                    current_section.content = '\n'.join(current_content)
                    current_section.line_end = line_num - 1
                    sections.append(current_section)
                
                # Start new section
                level = len(atx_match.group(1))
                title = atx_match.group(2).strip()
                
                current_section = DocumentSection(
                    title=title,
                    content="",
                    level=level,
                    line_start=line_num,
                    metadata={'header_type': 'atx'}
                )
                current_content = []
            
            elif setext_match:
                # Handle Setext header
                level, title = setext_match
                
                # Remove the previous line from current content if it exists
                if current_content and current_content[-1].strip() == title:
                    current_content.pop()
                
                # Save previous section
                if current_section:
                    current_section.content = '\n'.join(current_content)
                    current_section.line_end = line_num - 2
                    sections.append(current_section)
                
                # Start new section
                current_section = DocumentSection(
                    title=title,
                    content="",
                    level=level,
                    line_start=line_num - 1,
                    metadata={'header_type': 'setext'}
                )
                current_content = []
            
            else:
                # Regular content line
                if current_section:
                    current_content.append(line)
                else:
                    # Content before first header
                    if not sections:
                        current_section = DocumentSection(
                            title="Document Start",
                            content="",
                            level=1,
                            line_start=0,
                            metadata={'header_type': 'default'}
                        )
                        current_content = [line]
        
        # Don't forget the last section
        if current_section:
            current_section.content = '\n'.join(current_content)
            current_section.line_end = len(lines) - 1
            sections.append(current_section)
        
        return sections


class DocumentParserFactory:
    """
    Factory class for creating appropriate document parsers.
    
    Automatically detects file type and returns the appropriate parser.
    """
    
    def __init__(self):
        """Initialize the factory with available parsers."""
        self.parsers = [
            PDFParser(),
            DOCXParser(),
            MarkdownParser()
        ]
        
        self.supported_formats = []
        for parser in self.parsers:
            if isinstance(parser, PDFParser) and PyPDF2 is not None:
                self.supported_formats.extend(['pdf'])
            elif isinstance(parser, DOCXParser) and DocxDocument is not None:
                self.supported_formats.extend(['docx', 'doc'])
            elif isinstance(parser, MarkdownParser):
                self.supported_formats.extend(['md', 'markdown', 'txt'])
    
    def get_parser(self, file_path: Union[str, Path]) -> DocumentParser:
        """
        Get the appropriate parser for a file.
        
        Args:
            file_path: Path to the file to parse
            
        Returns:
            DocumentParser instance
            
        Raises:
            UnsupportedFileFormatError: If no parser can handle the file
        """
        file_path = Path(file_path)
        
        # Check if file exists
        if not file_path.exists():
            raise DocumentParsingError(
                f"File not found: {file_path}",
                file_path=str(file_path)
            )
        
        # Try each parser
        for parser in self.parsers:
            if parser.can_parse(file_path):
                return parser
        
        # No parser found
        file_type = file_path.suffix.lower().lstrip('.')
        raise UnsupportedFileFormatError(
            file_type=file_type,
            supported_formats=self.supported_formats
        )
    
    def parse_document(self, file_path: Union[str, Path]) -> ParsedDocument:
        """
        Parse a document using the appropriate parser.
        
        Args:
            file_path: Path to the file to parse
            
        Returns:
            ParsedDocument instance with structured content
        """
        parser = self.get_parser(file_path)
        return parser.parse(file_path)


# Global factory instance
document_parser_factory = DocumentParserFactory()


def parse_document(file_path: Union[str, Path]) -> ParsedDocument:
    """
    Convenience function to parse a document.
    
    Args:
        file_path: Path to the file to parse
        
    Returns:
        ParsedDocument instance with structured content
    """
    return document_parser_factory.parse_document(file_path)


def get_supported_formats() -> List[str]:
    """
    Get list of supported file formats.
    
    Returns:
        List of supported file extensions
    """
    return document_parser_factory.supported_formats.copy()