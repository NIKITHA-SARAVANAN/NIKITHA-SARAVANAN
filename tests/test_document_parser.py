"""
Tests for document parsing functionality.

Tests the document parser for various file formats and edge cases.
"""

import pytest
import tempfile
from pathlib import Path

from utils.document_parser import DocumentParser, ParsedDocument, DocumentSection
from utils.exceptions import ParsingError, UnsupportedFileFormatError


class TestDocumentSection:
    """Test the DocumentSection class."""
    
    def test_section_creation(self):
        """Test creating a document section."""
        section = DocumentSection(
            title="Test Section",
            content="This is test content",
            level=1,
            line_number=5
        )
        
        assert section.title == "Test Section"
        assert section.content == "This is test content"
        assert section.level == 1
        assert section.line_number == 5
        assert len(section.subsections) == 0
    
    def test_add_subsection(self):
        """Test adding subsections."""
        parent = DocumentSection("Parent", "Parent content", 1)
        child = DocumentSection("Child", "Child content", 2)
        
        parent.add_subsection(child)
        
        assert len(parent.subsections) == 1
        assert parent.subsections[0] == child
    
    def test_to_dict(self):
        """Test converting section to dictionary."""
        section = DocumentSection("Test", "Content", 1, 10)
        section_dict = section.to_dict()
        
        assert section_dict["title"] == "Test"
        assert section_dict["content"] == "Content"
        assert section_dict["level"] == 1
        assert section_dict["line_number"] == 10
        assert section_dict["subsections"] == []


class TestParsedDocument:
    """Test the ParsedDocument class."""
    
    def test_document_creation(self):
        """Test creating a parsed document."""
        doc = ParsedDocument(
            raw_text="Test content",
            file_path="/test/file.txt",
            file_type="txt"
        )
        
        assert doc.raw_text == "Test content"
        assert doc.file_path == "/test/file.txt"
        assert doc.file_type == "txt"
        assert len(doc.sections) == 0
    
    def test_add_section(self):
        """Test adding sections to document."""
        doc = ParsedDocument("Test")
        section = DocumentSection("Section 1", "Content 1", 1)
        
        doc.add_section(section)
        
        assert len(doc.sections) == 1
        assert doc.sections[0] == section
    
    def test_get_section_by_title(self):
        """Test finding section by title."""
        doc = ParsedDocument("Test")
        section1 = DocumentSection("Section 1", "Content 1", 1)
        section2 = DocumentSection("Section 2", "Content 2", 1)
        
        doc.add_section(section1)
        doc.add_section(section2)
        
        found = doc.get_section_by_title("Section 1")
        assert found == section1
        
        not_found = doc.get_section_by_title("Nonexistent")
        assert not_found is None
    
    def test_get_all_text(self):
        """Test getting all text from document."""
        doc = ParsedDocument("Raw text")
        section1 = DocumentSection("Sec 1", "Content 1", 1)
        section2 = DocumentSection("Sec 2", "Content 2", 1)
        
        doc.add_section(section1)
        doc.add_section(section2)
        
        all_text = doc.get_all_text()
        assert "# Sec 1" in all_text
        assert "Content 1" in all_text
        assert "# Sec 2" in all_text
        assert "Content 2" in all_text


class TestDocumentParser:
    """Test the DocumentParser class."""
    
    def setup_method(self):
        """Set up test fixtures."""
        self.parser = DocumentParser()
    
    def test_parser_initialization(self):
        """Test parser initialization."""
        assert self.parser is not None
        assert hasattr(self.parser, 'SUPPORTED_EXTENSIONS')
        assert '.txt' in self.parser.SUPPORTED_EXTENSIONS
        assert '.md' in self.parser.SUPPORTED_EXTENSIONS
    
    def test_parse_content(self):
        """Test parsing content directly."""
        content = "# Title\n\nThis is content."
        doc = self.parser.parse_content(content, "md")
        
        assert doc.raw_text == content
        assert doc.file_type == "md"
    
    def test_detect_file_type(self):
        """Test file type detection."""
        with tempfile.NamedTemporaryFile(suffix=".txt", delete=False) as tmp:
            tmp_path = Path(tmp.name)
            file_type = self.parser._detect_file_type(tmp_path)
            assert file_type == "txt"
        
        tmp_path.unlink()  # Clean up
    
    def test_parse_text_file(self):
        """Test parsing a text file."""
        content = "This is a test document.\n\nWith multiple paragraphs."
        
        with tempfile.NamedTemporaryFile(mode='w', suffix=".txt", delete=False) as tmp:
            tmp.write(content)
            tmp_path = Path(tmp.name)
        
        try:
            doc = self.parser.parse_file(tmp_path)
            assert doc.raw_text == content
            assert doc.file_type == "txt"
            assert len(doc.sections) >= 1  # Should create at least one section
        finally:
            tmp_path.unlink()  # Clean up
    
    def test_parse_markdown_file(self):
        """Test parsing a markdown file."""
        content = """# Main Title

This is the introduction.

## Section 1

Content of section 1.

## Section 2

Content of section 2.
"""
        
        with tempfile.NamedTemporaryFile(mode='w', suffix=".md", delete=False) as tmp:
            tmp.write(content)
            tmp_path = Path(tmp.name)
        
        try:
            doc = self.parser.parse_file(tmp_path)
            assert doc.raw_text == content
            assert doc.file_type == "md"
            assert len(doc.sections) >= 3  # Should find 3 sections
            
            # Check section hierarchy
            main_title = doc.get_section_by_title("Main Title")
            assert main_title is not None
            assert main_title.level == 1
            
        finally:
            tmp_path.unlink()  # Clean up
    
    def test_unsupported_file_format(self):
        """Test handling of unsupported file formats."""
        with tempfile.NamedTemporaryFile(suffix=".unsupported", delete=False) as tmp:
            tmp_path = Path(tmp.name)
        
        try:
            with pytest.raises(UnsupportedFileFormatError):
                self.parser.parse_file(tmp_path)
        finally:
            tmp_path.unlink()  # Clean up
    
    def test_file_not_found(self):
        """Test handling of non-existent files."""
        nonexistent_path = Path("/nonexistent/file.txt")
        
        with pytest.raises(ParsingError, match="File not found"):
            self.parser.parse_file(nonexistent_path)
    
    def test_extract_markdown_sections(self):
        """Test markdown section extraction."""
        content = """# Header 1

Content 1

## Header 2

Content 2

### Header 3

Content 3
"""
        doc = ParsedDocument(content, file_type="md")
        self.parser._extract_markdown_sections(doc)
        
        assert len(doc.sections) == 3
        assert doc.sections[0].title == "Header 1"
        assert doc.sections[0].level == 1
        assert doc.sections[1].title == "Header 2"
        assert doc.sections[1].level == 2
        assert doc.sections[2].title == "Header 3"
        assert doc.sections[2].level == 3


def test_convenience_function():
    """Test the convenience parse_document function."""
    from utils.document_parser import parse_document
    
    content = "Test content"
    
    with tempfile.NamedTemporaryFile(mode='w', suffix=".txt", delete=False) as tmp:
        tmp.write(content)
        tmp_path = Path(tmp.name)
    
    try:
        doc = parse_document(tmp_path)
        assert isinstance(doc, ParsedDocument)
        assert doc.raw_text == content
    finally:
        tmp_path.unlink()  # Clean up