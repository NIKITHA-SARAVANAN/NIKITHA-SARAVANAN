"""
Document management endpoints for the SRC Generator API.

These endpoints handle document upload, parsing, and SRD generation.
"""

import uuid
from datetime import datetime
from pathlib import Path
from typing import List, Optional

from fastapi import APIRouter, File, Form, HTTPException, UploadFile
from pydantic import BaseModel

from config.config import get_settings
from utils.document_parser import DocumentParser, ParsedDocument
from utils.exceptions import ParsingError, UnsupportedFileFormatError
from utils.logging_config import get_logger, log_processing_step

logger = get_logger(__name__)
router = APIRouter()


class DocumentUploadResponse(BaseModel):
    """Response model for document upload."""
    
    document_id: str
    filename: str
    file_size: int
    file_type: str
    upload_timestamp: datetime
    status: str
    message: str


class ParsedDocumentResponse(BaseModel):
    """Response model for parsed document."""
    
    document_id: str
    filename: str
    file_type: str
    sections_count: int
    text_length: int
    sections: List[dict]
    metadata: dict
    parsed_timestamp: datetime


class DocumentStatusResponse(BaseModel):
    """Response model for document processing status."""
    
    document_id: str
    status: str
    progress_percent: int
    current_step: str
    message: str
    error: Optional[str] = None
    timestamp: datetime


# In-memory storage for demo (in production, use database)
document_store = {}
processing_status = {}


@router.post("/documents/upload", response_model=DocumentUploadResponse)
async def upload_document(
    file: UploadFile = File(...),
    description: Optional[str] = Form(None)
):
    """
    Upload a document for processing.
    
    Accepts PDF, DOCX, Markdown, and text files and stores them
    for subsequent parsing and analysis.
    """
    settings = get_settings()
    
    # Validate file
    if not file.filename:
        raise HTTPException(
            status_code=400,
            detail="No filename provided"
        )
    
    # Check file size
    file_content = await file.read()
    file_size = len(file_content)
    
    if file_size > settings.file_upload.max_file_size_bytes:
        raise HTTPException(
            status_code=413,
            detail=f"File too large. Maximum size: {settings.file_upload.max_file_size_mb}MB"
        )
    
    # Check file extension
    file_extension = Path(file.filename).suffix.lower()
    if file_extension not in [f".{ext}" for ext in settings.file_upload.allowed_extensions]:
        raise HTTPException(
            status_code=400,
            detail=f"Unsupported file type. Allowed: {', '.join(settings.file_upload.allowed_extensions)}"
        )
    
    try:
        # Generate unique document ID
        document_id = str(uuid.uuid4())
        
        # Save file temporarily
        temp_dir = settings.code_generation.temp_dir
        temp_file_path = temp_dir / f"{document_id}_{file.filename}"
        
        with open(temp_file_path, "wb") as temp_file:
            temp_file.write(file_content)
        
        # Store document metadata
        document_store[document_id] = {
            "filename": file.filename,
            "file_path": str(temp_file_path),
            "file_size": file_size,
            "file_type": file_extension[1:],  # Remove dot
            "description": description,
            "upload_timestamp": datetime.utcnow(),
            "parsed_document": None
        }
        
        # Initialize processing status
        processing_status[document_id] = {
            "status": "uploaded",
            "progress_percent": 10,
            "current_step": "Upload completed",
            "message": "Document uploaded successfully",
            "error": None,
            "timestamp": datetime.utcnow()
        }
        
        logger.info(
            "Document uploaded successfully",
            document_id=document_id,
            filename=file.filename,
            file_size=file_size
        )
        
        log_processing_step(
            "document_upload",
            "COMPLETE",
            details={
                "document_id": document_id,
                "filename": file.filename,
                "file_size": file_size
            }
        )
        
        return DocumentUploadResponse(
            document_id=document_id,
            filename=file.filename,
            file_size=file_size,
            file_type=file_extension[1:],
            upload_timestamp=datetime.utcnow(),
            status="uploaded",
            message="Document uploaded successfully"
        )
        
    except Exception as e:
        logger.error(
            "Document upload failed",
            filename=file.filename,
            error=str(e)
        )
        raise HTTPException(
            status_code=500,
            detail=f"Upload failed: {str(e)}"
        )


@router.post("/documents/{document_id}/parse", response_model=ParsedDocumentResponse)
async def parse_document(document_id: str):
    """
    Parse an uploaded document into structured content.
    
    Extracts text and sections from the document and prepares it
    for requirements analysis.
    """
    if document_id not in document_store:
        raise HTTPException(
            status_code=404,
            detail="Document not found"
        )
    
    document_info = document_store[document_id]
    
    try:
        # Update processing status
        processing_status[document_id].update({
            "status": "parsing",
            "progress_percent": 30,
            "current_step": "Parsing document",
            "message": "Extracting text and sections from document",
            "timestamp": datetime.utcnow()
        })
        
        log_processing_step(
            "document_parsing",
            "START",
            details={"document_id": document_id}
        )
        
        # Parse the document
        parser = DocumentParser()
        parsed_doc = parser.parse_file(document_info["file_path"])
        
        # Store parsed document
        document_info["parsed_document"] = parsed_doc.to_dict()
        
        # Update processing status
        processing_status[document_id].update({
            "status": "parsed",
            "progress_percent": 50,
            "current_step": "Document parsed successfully",
            "message": f"Found {len(parsed_doc.sections)} sections",
            "timestamp": datetime.utcnow()
        })
        
        log_processing_step(
            "document_parsing",
            "COMPLETE",
            details={
                "document_id": document_id,
                "sections_found": len(parsed_doc.sections),
                "text_length": len(parsed_doc.raw_text)
            }
        )
        
        logger.info(
            "Document parsed successfully",
            document_id=document_id,
            sections_count=len(parsed_doc.sections),
            text_length=len(parsed_doc.raw_text)
        )
        
        return ParsedDocumentResponse(
            document_id=document_id,
            filename=document_info["filename"],
            file_type=document_info["file_type"],
            sections_count=len(parsed_doc.sections),
            text_length=len(parsed_doc.raw_text),
            sections=[section.to_dict() for section in parsed_doc.sections],
            metadata=parsed_doc.metadata,
            parsed_timestamp=datetime.utcnow()
        )
        
    except (ParsingError, UnsupportedFileFormatError) as e:
        error_msg = str(e)
        processing_status[document_id].update({
            "status": "error",
            "progress_percent": 0,
            "current_step": "Parsing failed",
            "message": "Document parsing failed",
            "error": error_msg,
            "timestamp": datetime.utcnow()
        })
        
        log_processing_step(
            "document_parsing",
            "FAILED",
            details={
                "document_id": document_id,
                "error": error_msg
            }
        )
        
        logger.error(
            "Document parsing failed",
            document_id=document_id,
            error=error_msg
        )
        
        raise HTTPException(
            status_code=400,
            detail=error_msg
        )
    
    except Exception as e:
        error_msg = f"Unexpected error during parsing: {str(e)}"
        processing_status[document_id].update({
            "status": "error",
            "progress_percent": 0,
            "current_step": "Parsing failed",
            "message": "Unexpected error occurred",
            "error": error_msg,
            "timestamp": datetime.utcnow()
        })
        
        logger.error(
            "Unexpected error during document parsing",
            document_id=document_id,
            error=str(e)
        )
        
        raise HTTPException(
            status_code=500,
            detail=error_msg
        )


@router.get("/documents/{document_id}/status", response_model=DocumentStatusResponse)
async def get_document_status(document_id: str):
    """
    Get the processing status of a document.
    
    Returns current processing status, progress, and any errors.
    """
    if document_id not in processing_status:
        raise HTTPException(
            status_code=404,
            detail="Document not found"
        )
    
    status_info = processing_status[document_id]
    
    return DocumentStatusResponse(
        document_id=document_id,
        status=status_info["status"],
        progress_percent=status_info["progress_percent"],
        current_step=status_info["current_step"],
        message=status_info["message"],
        error=status_info.get("error"),
        timestamp=status_info["timestamp"]
    )


@router.get("/documents/{document_id}", response_model=ParsedDocumentResponse)
async def get_document(document_id: str):
    """
    Get a parsed document by ID.
    
    Returns the full parsed document with sections and metadata.
    """
    if document_id not in document_store:
        raise HTTPException(
            status_code=404,
            detail="Document not found"
        )
    
    document_info = document_store[document_id]
    parsed_doc_dict = document_info.get("parsed_document")
    
    if not parsed_doc_dict:
        raise HTTPException(
            status_code=400,
            detail="Document has not been parsed yet"
        )
    
    return ParsedDocumentResponse(
        document_id=document_id,
        filename=document_info["filename"],
        file_type=document_info["file_type"],
        sections_count=len(parsed_doc_dict["sections"]),
        text_length=len(parsed_doc_dict["raw_text"]),
        sections=parsed_doc_dict["sections"],
        metadata=parsed_doc_dict["metadata"],
        parsed_timestamp=document_info["upload_timestamp"]
    )


@router.get("/documents", response_model=List[DocumentUploadResponse])
async def list_documents():
    """
    List all uploaded documents.
    
    Returns a list of all documents with their basic information.
    """
    documents = []
    
    for document_id, doc_info in document_store.items():
        status_info = processing_status.get(document_id, {})
        
        documents.append(DocumentUploadResponse(
            document_id=document_id,
            filename=doc_info["filename"],
            file_size=doc_info["file_size"],
            file_type=doc_info["file_type"],
            upload_timestamp=doc_info["upload_timestamp"],
            status=status_info.get("status", "unknown"),
            message=status_info.get("message", "No status available")
        ))
    
    return documents


@router.delete("/documents/{document_id}")
async def delete_document(document_id: str):
    """
    Delete a document and clean up associated files.
    
    Removes the document from storage and deletes temporary files.
    """
    if document_id not in document_store:
        raise HTTPException(
            status_code=404,
            detail="Document not found"
        )
    
    try:
        document_info = document_store[document_id]
        
        # Delete temporary file
        temp_file_path = Path(document_info["file_path"])
        if temp_file_path.exists():
            temp_file_path.unlink()
        
        # Remove from storage
        del document_store[document_id]
        if document_id in processing_status:
            del processing_status[document_id]
        
        logger.info(
            "Document deleted successfully",
            document_id=document_id,
            filename=document_info["filename"]
        )
        
        return {"message": "Document deleted successfully"}
        
    except Exception as e:
        logger.error(
            "Failed to delete document",
            document_id=document_id,
            error=str(e)
        )
        raise HTTPException(
            status_code=500,
            detail=f"Failed to delete document: {str(e)}"
        )