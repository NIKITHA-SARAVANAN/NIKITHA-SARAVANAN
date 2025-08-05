"""
Enhanced document parser for SRS documents with type detection and error handling.
"""

import logging
import re
from pathlib import Path
from typing import Dict, List, Optional, Any, Union
from dataclasses import dataclass, field

import PyPDF2
from docx import Document
import markdown

from .file_detector import FileTypeDetector

logger = logging.getLogger(__name__)


@dataclass
class ParsedSection:
    """Represents a parsed section of a document."""
    title: str
    content: str
    level: int = 1
    section_type: str = "general"
    subsections: List['ParsedSection'] = field(default_factory=list)


@dataclass
class ParsedDocument:
    """Represents a completely parsed document."""
    file_path: str
    file_type: str
    raw_text: str
    sections: List[ParsedSection] = field(default_factory=list)
    metadata: Dict[str, Any] = field(default_factory=dict)
    parsing_errors: List[str] = field(default_factory=list)
    is_valid: bool = True


class DocumentParser:
    """Enhanced parser for SRS documents with graceful error handling."""
    
    def __init__(self):
        """Initialize the document parser."""
        self.file_detector = FileTypeDetector()
        self.section_patterns = {
            'requirement': r'(?i)(requirement|req|functional|non-functional)',
            'architecture': r'(?i)(architecture|design|system|component)',
            'interface': r'(?i)(interface|api|ui|user interface)',
            'database': r'(?i)(database|data|storage|persistence)',
            'security': r'(?i)(security|authentication|authorization)',
            'performance': r'(?i)(performance|scalability|load)',
            'testing': r'(?i)(test|testing|qa|quality)',
            'deployment': r'(?i)(deployment|installation|setup)'
        }
    
    def parse_document(self, file_path: Union[str, Path]) -> ParsedDocument:
        """
        Parse a document and return structured data.
        
        Args:
            file_path: Path to the document to parse
            
        Returns:
            ParsedDocument with parsed content and metadata
        """
        file_path = Path(file_path)
        
        # Initialize result
        result = ParsedDocument(
            file_path=str(file_path),
            file_type="unknown",
            raw_text="",
            metadata={'file_name': file_path.name}
        )
        
        try:
            # Detect file type
            detection_result = self.file_detector.detect_type(file_path)
            
            if detection_result['error']:
                result.parsing_errors.append(detection_result['error'])
                result.is_valid = False
                return result
            
            if not detection_result['is_supported']:
                result.parsing_errors.append(f"Unsupported file type: {detection_result['detected_type']}")
                result.is_valid = False
                return result
            
            result.file_type = detection_result['detected_type']
            result.metadata.update(detection_result)
            
            # Parse based on file type
            if result.file_type == 'pdf':
                result = self._parse_pdf(file_path, result)
            elif result.file_type in ['docx', 'doc']:
                result = self._parse_docx(file_path, result)
            elif result.file_type == 'md':
                result = self._parse_markdown(file_path, result)
            elif result.file_type == 'txt':
                result = self._parse_text(file_path, result)
            else:
                result.parsing_errors.append(f"No parser available for type: {result.file_type}")
                result.is_valid = False
            
            # Extract sections if parsing was successful
            if result.is_valid and result.raw_text:
                result.sections = self._extract_sections(result.raw_text)
            
        except Exception as e:
            logger.error(f"Error parsing document {file_path}: {e}")
            result.parsing_errors.append(f"Parsing failed: {str(e)}")
            result.is_valid = False
        
        return result
    
    def _parse_pdf(self, file_path: Path, result: ParsedDocument) -> ParsedDocument:
        """Parse PDF document."""
        try:
            with open(file_path, 'rb') as file:
                pdf_reader = PyPDF2.PdfReader(file)
                
                # Extract metadata
                if pdf_reader.metadata:
                    result.metadata['pdf_title'] = pdf_reader.metadata.get('/Title', '')
                    result.metadata['pdf_author'] = pdf_reader.metadata.get('/Author', '')
                    result.metadata['pdf_creator'] = pdf_reader.metadata.get('/Creator', '')
                
                result.metadata['page_count'] = len(pdf_reader.pages)
                
                # Extract text from all pages
                text_content = []
                for page_num, page in enumerate(pdf_reader.pages):
                    try:
                        page_text = page.extract_text()
                        if page_text.strip():
                            text_content.append(f"--- Page {page_num + 1} ---\n{page_text}")
                    except Exception as e:
                        result.parsing_errors.append(f"Error reading page {page_num + 1}: {str(e)}")
                
                result.raw_text = "\n\n".join(text_content)
                
        except Exception as e:
            result.parsing_errors.append(f"PDF parsing error: {str(e)}")
            result.is_valid = False
        
        return result
    
    def _parse_docx(self, file_path: Path, result: ParsedDocument) -> ParsedDocument:
        """Parse DOCX document."""
        try:
            doc = Document(file_path)
            
            # Extract core properties
            if hasattr(doc, 'core_properties'):
                props = doc.core_properties
                result.metadata['title'] = props.title or ''
                result.metadata['author'] = props.author or ''
                result.metadata['subject'] = props.subject or ''
                result.metadata['created'] = str(props.created) if props.created else ''
                result.metadata['modified'] = str(props.modified) if props.modified else ''
            
            # Extract text from paragraphs
            text_content = []
            for paragraph in doc.paragraphs:
                if paragraph.text.strip():
                    text_content.append(paragraph.text)
            
            # Extract text from tables
            for table in doc.tables:
                table_text = []
                for row in table.rows:
                    row_text = []
                    for cell in row.cells:
                        row_text.append(cell.text.strip())
                    table_text.append(" | ".join(row_text))
                
                if table_text:
                    text_content.append("TABLE:\n" + "\n".join(table_text))
            
            result.raw_text = "\n\n".join(text_content)
            
        except Exception as e:
            result.parsing_errors.append(f"DOCX parsing error: {str(e)}")
            result.is_valid = False
        
        return result
    
    def _parse_markdown(self, file_path: Path, result: ParsedDocument) -> ParsedDocument:
        """Parse Markdown document."""
        try:
            with open(file_path, 'r', encoding='utf-8') as file:
                content = file.read()
            
            # Parse markdown to extract metadata if present
            if content.startswith('---'):
                parts = content.split('---', 2)
                if len(parts) >= 3:
                    # YAML frontmatter present
                    frontmatter = parts[1].strip()
                    content = parts[2].strip()
                    
                    # Basic YAML parsing for title, author, etc.
                    for line in frontmatter.split('\n'):
                        if ':' in line:
                            key, value = line.split(':', 1)
                            result.metadata[key.strip()] = value.strip().strip('"\'')
            
            result.raw_text = content
            
        except Exception as e:
            result.parsing_errors.append(f"Markdown parsing error: {str(e)}")
            result.is_valid = False
        
        return result
    
    def _parse_text(self, file_path: Path, result: ParsedDocument) -> ParsedDocument:
        """Parse plain text document."""
        try:
            with open(file_path, 'r', encoding='utf-8') as file:
                result.raw_text = file.read()
                
        except UnicodeDecodeError:
            try:
                # Try with different encoding
                with open(file_path, 'r', encoding='latin-1') as file:
                    result.raw_text = file.read()
                    result.metadata['encoding'] = 'latin-1'
            except Exception as e:
                result.parsing_errors.append(f"Text parsing error: {str(e)}")
                result.is_valid = False
        except Exception as e:
            result.parsing_errors.append(f"Text parsing error: {str(e)}")
            result.is_valid = False
        
        return result
    
    def _extract_sections(self, text: str) -> List[ParsedSection]:
        """Extract structured sections from text."""
        sections = []
        
        # Split by common heading patterns
        heading_patterns = [
            r'^#{1,6}\s+(.+)$',  # Markdown headers
            r'^(.+)\n={3,}$',    # Underlined headers
            r'^(.+)\n-{3,}$',    # Underlined headers
            r'^\d+\.?\s+(.+)$',  # Numbered sections
            r'^[A-Z][A-Z\s]+$'   # ALL CAPS headers
        ]
        
        lines = text.split('\n')
        current_section = None
        current_content = []
        
        for i, line in enumerate(lines):
            line_stripped = line.strip()
            
            if not line_stripped:
                current_content.append(line)
                continue
            
            # Check if this line is a heading
            is_heading = False
            heading_level = 1
            
            for pattern in heading_patterns:
                match = re.match(pattern, line_stripped, re.MULTILINE)
                if match:
                    is_heading = True
                    # Determine heading level
                    if pattern.startswith('^#{'):
                        heading_level = len(line_stripped) - len(line_stripped.lstrip('#'))
                    break
            
            if is_heading:
                # Save previous section
                if current_section:
                    current_section.content = '\n'.join(current_content).strip()
                    sections.append(current_section)
                
                # Start new section
                section_title = line_stripped.lstrip('#').strip()
                section_type = self._classify_section(section_title)
                
                current_section = ParsedSection(
                    title=section_title,
                    content="",
                    level=heading_level,
                    section_type=section_type
                )
                current_content = []
            else:
                current_content.append(line)
        
        # Add final section
        if current_section:
            current_section.content = '\n'.join(current_content).strip()
            sections.append(current_section)
        
        return sections
    
    def _classify_section(self, title: str) -> str:
        """Classify section type based on title."""
        title_lower = title.lower()
        
        for section_type, pattern in self.section_patterns.items():
            if re.search(pattern, title_lower):
                return section_type
        
        return "general"