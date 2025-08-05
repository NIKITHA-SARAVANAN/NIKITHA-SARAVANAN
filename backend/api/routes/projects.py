"""
Project management endpoints for the SRC Generator API.

These endpoints handle project creation, tracking, and generated application management.
"""

import uuid
from datetime import datetime
from pathlib import Path
from typing import List, Optional, Dict, Any

from fastapi import APIRouter, HTTPException
from pydantic import BaseModel

from config.config import get_settings
from utils.logging_config import get_logger, log_processing_step

logger = get_logger(__name__)
router = APIRouter()


class ProjectCreateRequest(BaseModel):
    """Project creation request model."""
    
    name: str
    description: Optional[str] = None
    document_id: str
    frontend_srd_id: Optional[str] = None
    backend_srd_id: Optional[str] = None


class ProjectResponse(BaseModel):
    """Project response model."""
    
    project_id: str
    name: str
    description: Optional[str] = None
    status: str
    created_at: datetime
    updated_at: datetime
    document_id: str
    frontend_srd_id: Optional[str] = None
    backend_srd_id: Optional[str] = None
    progress_percent: int
    current_phase: str
    generated_files: List[Dict[str, Any]]
    agents_completed: List[str]
    agents_pending: List[str]


class ProjectPhaseResponse(BaseModel):
    """Project phase status response model."""
    
    project_id: str
    phase: str
    status: str
    started_at: Optional[datetime] = None
    completed_at: Optional[datetime] = None
    progress_percent: int
    current_step: str
    message: str
    agents_involved: List[str]
    outputs: List[Dict[str, Any]]


class GeneratedFileResponse(BaseModel):
    """Generated file response model."""
    
    file_id: str
    filename: str
    file_path: str
    file_type: str
    component_type: str  # e.g., "component", "service", "model", "route"
    generated_by: str  # agent that generated this file
    generated_at: datetime
    size_bytes: int
    content_preview: Optional[str] = None


# Mock project storage
project_store = {}
project_phases = [
    "requirements_analysis",
    "backend_design", 
    "frontend_design",
    "code_generation",
    "testing",
    "review",
    "completion"
]


@router.post("/projects", response_model=ProjectResponse)
async def create_project(request: ProjectCreateRequest):
    """
    Create a new project for application generation.
    
    Initializes a new project with the provided SRC document and
    sets up the multi-phase generation workflow.
    """
    # Generate project ID
    project_id = str(uuid.uuid4())
    
    # TODO: Validate that document_id exists
    # TODO: Validate SRD IDs if provided
    
    try:
        # Create project record
        project_data = {
            "name": request.name,
            "description": request.description,
            "status": "created",
            "created_at": datetime.utcnow(),
            "updated_at": datetime.utcnow(),
            "document_id": request.document_id,
            "frontend_srd_id": request.frontend_srd_id,
            "backend_srd_id": request.backend_srd_id,
            "progress_percent": 0,
            "current_phase": "requirements_analysis",
            "generated_files": [],
            "agents_completed": [],
            "agents_pending": [
                "requirements_analyzer",
                "api_designer", 
                "model_developer",
                "component_designer",
                "code_reviewer"
            ],
            "phases": {
                phase: {
                    "status": "pending",
                    "started_at": None,
                    "completed_at": None,
                    "progress_percent": 0,
                    "current_step": "Not started",
                    "message": "Waiting to start",
                    "agents_involved": [],
                    "outputs": []
                } for phase in project_phases
            }
        }
        
        # Set first phase to ready
        project_data["phases"]["requirements_analysis"]["status"] = "ready"
        project_data["phases"]["requirements_analysis"]["message"] = "Ready to begin requirements analysis"
        
        project_store[project_id] = project_data
        
        log_processing_step(
            "project_creation",
            "COMPLETE",
            details={
                "project_id": project_id,
                "project_name": request.name,
                "document_id": request.document_id
            }
        )
        
        logger.info(
            "Project created successfully",
            project_id=project_id,
            project_name=request.name,
            document_id=request.document_id
        )
        
        return ProjectResponse(
            project_id=project_id,
            **{k: v for k, v in project_data.items() if k != "phases"}
        )
        
    except Exception as e:
        logger.error(
            "Project creation failed",
            project_name=request.name,
            error=str(e)
        )
        raise HTTPException(
            status_code=500,
            detail=f"Failed to create project: {str(e)}"
        )


@router.get("/projects", response_model=List[ProjectResponse])
async def list_projects():
    """
    List all projects.
    
    Returns a list of all projects with their current status and progress.
    """
    projects = []
    
    for project_id, project_data in project_store.items():
        projects.append(ProjectResponse(
            project_id=project_id,
            **{k: v for k, v in project_data.items() if k != "phases"}
        ))
    
    # Sort by creation time (most recent first)
    projects.sort(key=lambda x: x.created_at, reverse=True)
    
    logger.info(f"Listed {len(projects)} projects")
    return projects


@router.get("/projects/{project_id}", response_model=ProjectResponse)
async def get_project(project_id: str):
    """
    Get detailed information about a specific project.
    
    Returns comprehensive project information including current status,
    progress, and generated files.
    """
    if project_id not in project_store:
        raise HTTPException(
            status_code=404,
            detail=f"Project '{project_id}' not found"
        )
    
    project_data = project_store[project_id]
    
    return ProjectResponse(
        project_id=project_id,
        **{k: v for k, v in project_data.items() if k != "phases"}
    )


@router.get("/projects/{project_id}/phases/{phase}", response_model=ProjectPhaseResponse)
async def get_project_phase(project_id: str, phase: str):
    """
    Get detailed information about a specific project phase.
    
    Returns phase-specific status, progress, and outputs.
    """
    if project_id not in project_store:
        raise HTTPException(
            status_code=404,
            detail=f"Project '{project_id}' not found"
        )
    
    if phase not in project_phases:
        raise HTTPException(
            status_code=400,
            detail=f"Invalid phase '{phase}'. Valid phases: {', '.join(project_phases)}"
        )
    
    project_data = project_store[project_id]
    phase_data = project_data["phases"][phase]
    
    return ProjectPhaseResponse(
        project_id=project_id,
        phase=phase,
        **phase_data
    )


@router.post("/projects/{project_id}/phases/{phase}/start")
async def start_project_phase(project_id: str, phase: str):
    """
    Start a specific project phase.
    
    Initiates the specified phase if prerequisites are met.
    """
    if project_id not in project_store:
        raise HTTPException(
            status_code=404,
            detail=f"Project '{project_id}' not found"
        )
    
    if phase not in project_phases:
        raise HTTPException(
            status_code=400,
            detail=f"Invalid phase '{phase}'. Valid phases: {', '.join(project_phases)}"
        )
    
    project_data = project_store[project_id]
    phase_data = project_data["phases"][phase]
    
    # Check if phase can be started
    if phase_data["status"] not in ["ready", "failed"]:
        raise HTTPException(
            status_code=409,
            detail=f"Phase '{phase}' cannot be started (current status: {phase_data['status']})"
        )
    
    try:
        # Update phase status
        phase_data.update({
            "status": "running",
            "started_at": datetime.utcnow(),
            "progress_percent": 0,
            "current_step": "Initializing phase",
            "message": f"Starting {phase} phase"
        })
        
        # Update project status
        project_data["current_phase"] = phase
        project_data["updated_at"] = datetime.utcnow()
        
        log_processing_step(
            f"project_phase_{phase}",
            "START",
            details={
                "project_id": project_id,
                "phase": phase
            }
        )
        
        logger.info(
            "Project phase started",
            project_id=project_id,
            phase=phase
        )
        
        # TODO: Start actual phase execution (agent workflows)
        
        return {"message": f"Phase '{phase}' started successfully"}
        
    except Exception as e:
        logger.error(
            "Failed to start project phase",
            project_id=project_id,
            phase=phase,
            error=str(e)
        )
        raise HTTPException(
            status_code=500,
            detail=f"Failed to start phase: {str(e)}"
        )


@router.get("/projects/{project_id}/files", response_model=List[GeneratedFileResponse])
async def list_project_files(project_id: str):
    """
    List all generated files for a project.
    
    Returns a list of all files generated during the project workflow.
    """
    if project_id not in project_store:
        raise HTTPException(
            status_code=404,
            detail=f"Project '{project_id}' not found"
        )
    
    project_data = project_store[project_id]
    generated_files = project_data.get("generated_files", [])
    
    files = []
    for file_data in generated_files:
        files.append(GeneratedFileResponse(**file_data))
    
    return files


@router.get("/projects/{project_id}/files/{file_id}")
async def get_project_file(project_id: str, file_id: str):
    """
    Get the content of a specific generated file.
    
    Returns the full content of a generated file.
    """
    if project_id not in project_store:
        raise HTTPException(
            status_code=404,
            detail=f"Project '{project_id}' not found"
        )
    
    project_data = project_store[project_id]
    generated_files = project_data.get("generated_files", [])
    
    # Find the file
    file_data = None
    for f in generated_files:
        if f["file_id"] == file_id:
            file_data = f
            break
    
    if not file_data:
        raise HTTPException(
            status_code=404,
            detail=f"File '{file_id}' not found in project"
        )
    
    try:
        # Read file content
        file_path = Path(file_data["file_path"])
        if not file_path.exists():
            raise HTTPException(
                status_code=404,
                detail="Generated file no longer exists on disk"
            )
        
        with open(file_path, 'r', encoding='utf-8') as f:
            content = f.read()
        
        return {
            "file_info": file_data,
            "content": content
        }
        
    except Exception as e:
        logger.error(
            "Failed to read generated file",
            project_id=project_id,
            file_id=file_id,
            error=str(e)
        )
        raise HTTPException(
            status_code=500,
            detail=f"Failed to read file: {str(e)}"
        )


@router.post("/projects/{project_id}/export")
async def export_project(project_id: str):
    """
    Export the complete generated project as a ZIP file.
    
    Creates a downloadable ZIP archive containing all generated files.
    """
    if project_id not in project_store:
        raise HTTPException(
            status_code=404,
            detail=f"Project '{project_id}' not found"
        )
    
    # TODO: Implement ZIP file generation
    # For now, return placeholder response
    
    logger.info(
        "Project export requested",
        project_id=project_id
    )
    
    return {
        "message": "Project export feature will be implemented in future milestone",
        "project_id": project_id,
        "status": "not_implemented"
    }


@router.delete("/projects/{project_id}")
async def delete_project(project_id: str):
    """
    Delete a project and all associated files.
    
    Removes the project and cleans up all generated files.
    """
    if project_id not in project_store:
        raise HTTPException(
            status_code=404,
            detail=f"Project '{project_id}' not found"
        )
    
    try:
        project_data = project_store[project_id]
        
        # Delete all generated files
        generated_files = project_data.get("generated_files", [])
        for file_data in generated_files:
            file_path = Path(file_data["file_path"])
            if file_path.exists():
                file_path.unlink()
        
        # Remove project from store
        del project_store[project_id]
        
        logger.info(
            "Project deleted successfully",
            project_id=project_id,
            project_name=project_data["name"]
        )
        
        return {"message": "Project deleted successfully"}
        
    except Exception as e:
        logger.error(
            "Failed to delete project",
            project_id=project_id,
            error=str(e)
        )
        raise HTTPException(
            status_code=500,
            detail=f"Failed to delete project: {str(e)}"
        )