"""
Document management API routes.

Provides endpoints for uploading, parsing, and managing SRS documents
throughout the processing pipeline.
"""

import os
import uuid
import aiofiles
from datetime import datetime
from typing import List, Optional
from pathlib import Path
from fastapi import APIRouter, File, UploadFile, HTTPException, Depends, Form, Query
from fastapi.responses import FileResponse
from pydantic import BaseModel
import sys

# Add project root to path
sys.path.append(os.path.dirname(os.path.dirname(os.path.dirname(os.path.dirname(os.path.abspath(__file__))))))

from config.config import settings
from utils.logger import get_logger
from utils.document_parser import parse_document, get_supported_formats
from utils.exceptions import DocumentParsingError, UnsupportedFileFormatError
from backend.models.database import Document, DocumentStatus
from backend.database import get_database

logger = get_logger(__name__)

router = APIRouter()


class DocumentInfo(BaseModel):
    """Document information response model."""
    id: str
    filename: str
    file_type: str
    file_size: int
    upload_date: datetime
    status: str
    metadata: dict


class DocumentContent(BaseModel):
    """Document content response model."""
    id: str
    filename: str
    raw_text: str
    sections: List[dict]
    requirements: List[str]
    table_of_contents: List[dict]
    metadata: dict


class DocumentUploadResponse(BaseModel):
    """Document upload response model."""
    id: str
    filename: str
    message: str
    status: str


@router.get("/supported-formats")
async def get_supported_file_formats():
    """
    Get list of supported file formats.
    
    Returns:
        Dict containing supported file formats and size limits
    """
    return {
        "supported_formats": get_supported_formats(),
        "max_file_size_mb": settings.max_file_size_mb,
        "max_file_size_bytes": settings.max_file_size_bytes
    }


@router.post("/upload", response_model=DocumentUploadResponse)
async def upload_document(
    file: UploadFile = File(...),
    description: Optional[str] = Form(None),
    db=Depends(get_database)
):
    """
    Upload and parse an SRS document.
    
    Args:
        file: The uploaded file
        description: Optional description of the document
        db: Database dependency
    
    Returns:
        DocumentUploadResponse: Upload confirmation with document ID
    """
    # Validate file
    if not file.filename:
        raise HTTPException(status_code=400, detail="No file provided")
    
    # Check file size
    if file.size and file.size > settings.max_file_size_bytes:
        raise HTTPException(
            status_code=413,
            detail=f"File too large. Maximum size: {settings.max_file_size_mb}MB"
        )
    
    # Check file type
    file_extension = Path(file.filename).suffix.lower().lstrip('.')
    if file_extension not in settings.allowed_file_types:
        raise HTTPException(
            status_code=415,
            detail=f"Unsupported file type: {file_extension}. "
                   f"Supported types: {', '.join(settings.allowed_file_types)}"
        )
    
    try:
        # Generate unique document ID and filename
        document_id = str(uuid.uuid4())
        safe_filename = f"{document_id}_{file.filename}"
        file_path = Path(settings.upload_dir) / safe_filename
        
        # Ensure upload directory exists
        os.makedirs(settings.upload_dir, exist_ok=True)
        
        # Save uploaded file
        async with aiofiles.open(file_path, 'wb') as f:
            content = await file.read()
            await f.write(content)
        
        logger.info(f"File uploaded: {file.filename} -> {file_path}")
        
        # Create database record
        document = Document(
            id=document_id,
            filename=file.filename,
            file_path=str(file_path),
            file_type=file_extension,
            file_size=len(content),
            description=description,
            status=DocumentStatus.UPLOADED,
            upload_date=datetime.utcnow(),
            metadata={}
        )
        
        # Save to database
        await db.add(document)
        await db.commit()
        
        logger.info(f"Document record created: {document_id}")
        
        return DocumentUploadResponse(
            id=document_id,
            filename=file.filename,
            message="Document uploaded successfully",
            status="uploaded"
        )
        
    except Exception as e:
        logger.error(f"Document upload failed: {e}")
        
        # Clean up file if it was created
        if 'file_path' in locals() and file_path.exists():
            try:
                os.remove(file_path)
            except Exception:
                pass
        
        raise HTTPException(
            status_code=500,
            detail=f"Upload failed: {str(e)}"
        )


@router.post("/{document_id}/parse")
async def parse_document_endpoint(
    document_id: str,
    db=Depends(get_database)
):
    """
    Parse an uploaded document to extract structure and content.
    
    Args:
        document_id: ID of the document to parse
        db: Database dependency
    
    Returns:
        Dict containing parsing results
    """
    try:
        # Get document from database
        document = await db.get(Document, document_id)
        if not document:
            raise HTTPException(status_code=404, detail="Document not found")
        
        if document.status != DocumentStatus.UPLOADED:
            raise HTTPException(
                status_code=400,
                detail=f"Document not in uploadable state: {document.status}"
            )
        
        # Check if file still exists
        if not os.path.exists(document.file_path):
            raise HTTPException(status_code=404, detail="Document file not found")
        
        logger.info(f"Parsing document: {document_id}")
        
        # Update status to parsing
        document.status = DocumentStatus.PARSING
        await db.commit()
        
        # Parse the document
        try:
            parsed_doc = parse_document(document.file_path)
            
            # Extract requirements
            requirements = parsed_doc.extract_requirements()
            
            # Get table of contents
            toc = parsed_doc.get_table_of_contents()
            
            # Update document with parsed content
            document.status = DocumentStatus.PARSED
            document.raw_text = parsed_doc.raw_text
            document.sections = [
                {
                    "title": section.title,
                    "content": section.content,
                    "level": section.level,
                    "line_start": section.line_start,
                    "line_end": section.line_end,
                    "metadata": section.metadata
                }
                for section in parsed_doc.sections
            ]
            document.requirements = requirements
            document.table_of_contents = toc
            document.metadata.update(parsed_doc.metadata)
            document.parsed_date = datetime.utcnow()
            
            await db.commit()
            
            logger.info(f"Document parsed successfully: {document_id}")
            
            return {
                "id": document_id,
                "status": "parsed",
                "sections_count": len(parsed_doc.sections),
                "requirements_count": len(requirements),
                "file_type": parsed_doc.file_type,
                "metadata": parsed_doc.metadata
            }
            
        except (DocumentParsingError, UnsupportedFileFormatError) as e:
            # Update status to failed
            document.status = DocumentStatus.FAILED
            document.error_message = str(e)
            await db.commit()
            
            logger.error(f"Document parsing failed: {document_id} - {e}")
            raise HTTPException(status_code=400, detail=str(e))
        
    except HTTPException:
        raise
    except Exception as e:
        logger.error(f"Document parsing endpoint failed: {e}")
        raise HTTPException(status_code=500, detail=f"Parsing failed: {str(e)}")


@router.get("/", response_model=List[DocumentInfo])
async def list_documents(
    status: Optional[str] = Query(None, description="Filter by status"),
    limit: int = Query(50, ge=1, le=100, description="Limit number of results"),
    offset: int = Query(0, ge=0, description="Offset for pagination"),
    db=Depends(get_database)
):
    """
    List uploaded documents with optional filtering.
    
    Args:
        status: Optional status filter
        limit: Maximum number of documents to return
        offset: Number of documents to skip
        db: Database dependency
    
    Returns:
        List of document information
    """
    try:
        # Build query
        query = db.query(Document)
        
        if status:
            query = query.filter(Document.status == status)
        
        # Apply pagination
        documents = query.offset(offset).limit(limit).all()
        
        return [
            DocumentInfo(
                id=doc.id,
                filename=doc.filename,
                file_type=doc.file_type,
                file_size=doc.file_size,
                upload_date=doc.upload_date,
                status=doc.status.value,
                metadata=doc.metadata or {}
            )
            for doc in documents
        ]
        
    except Exception as e:
        logger.error(f"List documents failed: {e}")
        raise HTTPException(status_code=500, detail=f"Failed to list documents: {str(e)}")


@router.get("/{document_id}", response_model=DocumentContent)
async def get_document(
    document_id: str,
    db=Depends(get_database)
):
    """
    Get detailed information about a specific document.
    
    Args:
        document_id: ID of the document
        db: Database dependency
    
    Returns:
        Detailed document information including content
    """
    try:
        document = await db.get(Document, document_id)
        if not document:
            raise HTTPException(status_code=404, detail="Document not found")
        
        return DocumentContent(
            id=document.id,
            filename=document.filename,
            raw_text=document.raw_text or "",
            sections=document.sections or [],
            requirements=document.requirements or [],
            table_of_contents=document.table_of_contents or [],
            metadata=document.metadata or {}
        )
        
    except HTTPException:
        raise
    except Exception as e:
        logger.error(f"Get document failed: {e}")
        raise HTTPException(status_code=500, detail=f"Failed to get document: {str(e)}")


@router.get("/{document_id}/download")
async def download_document(
    document_id: str,
    db=Depends(get_database)
):
    """
    Download the original document file.
    
    Args:
        document_id: ID of the document
        db: Database dependency
    
    Returns:
        File response with the original document
    """
    try:
        document = await db.get(Document, document_id)
        if not document:
            raise HTTPException(status_code=404, detail="Document not found")
        
        if not os.path.exists(document.file_path):
            raise HTTPException(status_code=404, detail="Document file not found")
        
        return FileResponse(
            path=document.file_path,
            filename=document.filename,
            media_type='application/octet-stream'
        )
        
    except HTTPException:
        raise
    except Exception as e:
        logger.error(f"Download document failed: {e}")
        raise HTTPException(status_code=500, detail=f"Failed to download document: {str(e)}")


@router.delete("/{document_id}")
async def delete_document(
    document_id: str,
    db=Depends(get_database)
):
    """
    Delete a document and its associated file.
    
    Args:
        document_id: ID of the document
        db: Database dependency
    
    Returns:
        Deletion confirmation
    """
    try:
        document = await db.get(Document, document_id)
        if not document:
            raise HTTPException(status_code=404, detail="Document not found")
        
        # Delete the file if it exists
        if os.path.exists(document.file_path):
            try:
                os.remove(document.file_path)
                logger.info(f"Document file deleted: {document.file_path}")
            except Exception as e:
                logger.warning(f"Failed to delete document file: {e}")
        
        # Delete the database record
        await db.delete(document)
        await db.commit()
        
        logger.info(f"Document deleted: {document_id}")
        
        return {"message": "Document deleted successfully", "id": document_id}
        
    except HTTPException:
        raise
    except Exception as e:
        logger.error(f"Delete document failed: {e}")
        raise HTTPException(status_code=500, detail=f"Failed to delete document: {str(e)}")