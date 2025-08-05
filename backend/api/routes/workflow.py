"""
Workflow orchestration API routes.

Provides endpoints for managing document processing workflows,
agent execution, and human-in-the-loop interactions.
"""

import asyncio
from datetime import datetime
from typing import List, Optional, Dict, Any
from fastapi import APIRouter, HTTPException, Depends, Body
from pydantic import BaseModel
import sys
import os

# Add project root to path
sys.path.append(os.path.dirname(os.path.dirname(os.path.dirname(os.path.dirname(os.path.abspath(__file__))))))

from config.config import settings
from utils.logger import get_logger
from backend.models.database import Document, Workflow, WorkflowStatus
from backend.database import get_database

logger = get_logger(__name__)

router = APIRouter()


class WorkflowRequest(BaseModel):
    """Workflow creation request model."""
    document_id: str
    workflow_type: str = "full_generation"  # full_generation, backend_only, frontend_only
    options: Dict[str, Any] = {}


class WorkflowResponse(BaseModel):
    """Workflow response model."""
    id: str
    document_id: str
    status: str
    workflow_type: str
    created_date: datetime
    updated_date: datetime
    progress: float
    current_stage: str
    stages: List[Dict[str, Any]]
    options: Dict[str, Any]


class WorkflowUpdateRequest(BaseModel):
    """Workflow update request model."""
    action: str  # approve, reject, modify, cancel
    data: Optional[Dict[str, Any]] = None
    comment: Optional[str] = None


class HumanApprovalRequest(BaseModel):
    """Human approval request model."""
    stage_id: str
    approval_type: str  # srd_review, code_review, test_review
    content: Dict[str, Any]
    timeout_seconds: Optional[int] = None


@router.post("/start", response_model=WorkflowResponse)
async def start_workflow(
    request: WorkflowRequest,
    db=Depends(get_database)
):
    """
    Start a new workflow for document processing.
    
    Args:
        request: Workflow configuration
        db: Database dependency
    
    Returns:
        WorkflowResponse: Created workflow information
    """
    try:
        # Verify document exists and is ready
        document = await db.get(Document, request.document_id)
        if not document:
            raise HTTPException(status_code=404, detail="Document not found")
        
        if document.status.value not in ["parsed", "srd_generated"]:
            raise HTTPException(
                status_code=400,
                detail=f"Document not ready for workflow: {document.status.value}"
            )
        
        # Create workflow stages based on type
        stages = create_workflow_stages(request.workflow_type)
        
        # Create workflow record
        workflow = Workflow(
            document_id=request.document_id,
            workflow_type=request.workflow_type,
            status=WorkflowStatus.PENDING,
            stages=stages,
            options=request.options,
            created_date=datetime.utcnow(),
            updated_date=datetime.utcnow()
        )
        
        await db.add(workflow)
        await db.commit()
        
        logger.info(f"Workflow started: {workflow.id} for document {request.document_id}")
        
        # Start async workflow execution
        asyncio.create_task(execute_workflow(workflow.id))
        
        return WorkflowResponse(
            id=workflow.id,
            document_id=workflow.document_id,
            status=workflow.status.value,
            workflow_type=workflow.workflow_type,
            created_date=workflow.created_date,
            updated_date=workflow.updated_date,
            progress=0.0,
            current_stage=stages[0]["name"] if stages else "none",
            stages=stages,
            options=workflow.options
        )
        
    except HTTPException:
        raise
    except Exception as e:
        logger.error(f"Failed to start workflow: {e}")
        raise HTTPException(status_code=500, detail=f"Failed to start workflow: {str(e)}")


@router.get("/{workflow_id}", response_model=WorkflowResponse)
async def get_workflow(
    workflow_id: str,
    db=Depends(get_database)
):
    """
    Get workflow status and details.
    
    Args:
        workflow_id: ID of the workflow
        db: Database dependency
    
    Returns:
        WorkflowResponse: Workflow information
    """
    try:
        workflow = await db.get(Workflow, workflow_id)
        if not workflow:
            raise HTTPException(status_code=404, detail="Workflow not found")
        
        # Calculate progress
        progress = calculate_workflow_progress(workflow.stages, workflow.current_stage_index or 0)
        
        # Get current stage name
        current_stage = "completed"
        if workflow.current_stage_index is not None and workflow.current_stage_index < len(workflow.stages):
            current_stage = workflow.stages[workflow.current_stage_index]["name"]
        
        return WorkflowResponse(
            id=workflow.id,
            document_id=workflow.document_id,
            status=workflow.status.value,
            workflow_type=workflow.workflow_type,
            created_date=workflow.created_date,
            updated_date=workflow.updated_date,
            progress=progress,
            current_stage=current_stage,
            stages=workflow.stages,
            options=workflow.options
        )
        
    except HTTPException:
        raise
    except Exception as e:
        logger.error(f"Failed to get workflow: {e}")
        raise HTTPException(status_code=500, detail=f"Failed to get workflow: {str(e)}")


@router.post("/{workflow_id}/update")
async def update_workflow(
    workflow_id: str,
    request: WorkflowUpdateRequest,
    db=Depends(get_database)
):
    """
    Update workflow status or respond to human approval requests.
    
    Args:
        workflow_id: ID of the workflow
        request: Update request
        db: Database dependency
    
    Returns:
        Dict containing update confirmation
    """
    try:
        workflow = await db.get(Workflow, workflow_id)
        if not workflow:
            raise HTTPException(status_code=404, detail="Workflow not found")
        
        if request.action == "approve":
            await handle_workflow_approval(workflow, request.data, db)
        elif request.action == "reject":
            await handle_workflow_rejection(workflow, request.comment, db)
        elif request.action == "modify":
            await handle_workflow_modification(workflow, request.data, db)
        elif request.action == "cancel":
            await handle_workflow_cancellation(workflow, db)
        else:
            raise HTTPException(status_code=400, detail=f"Unknown action: {request.action}")
        
        workflow.updated_date = datetime.utcnow()
        await db.commit()
        
        logger.info(f"Workflow updated: {workflow_id} - {request.action}")
        
        return {
            "message": f"Workflow {request.action} successful",
            "workflow_id": workflow_id,
            "status": workflow.status.value
        }
        
    except HTTPException:
        raise
    except Exception as e:
        logger.error(f"Failed to update workflow: {e}")
        raise HTTPException(status_code=500, detail=f"Failed to update workflow: {str(e)}")


@router.get("/{workflow_id}/logs")
async def get_workflow_logs(
    workflow_id: str,
    limit: int = 100,
    db=Depends(get_database)
):
    """
    Get workflow execution logs.
    
    Args:
        workflow_id: ID of the workflow
        limit: Maximum number of log entries to return
        db: Database dependency
    
    Returns:
        Dict containing workflow logs
    """
    try:
        workflow = await db.get(Workflow, workflow_id)
        if not workflow:
            raise HTTPException(status_code=404, detail="Workflow not found")
        
        # Get logs from workflow execution history
        logs = workflow.execution_logs or []
        
        # Limit results
        if limit and len(logs) > limit:
            logs = logs[-limit:]
        
        return {
            "workflow_id": workflow_id,
            "logs": logs,
            "total_count": len(workflow.execution_logs or [])
        }
        
    except HTTPException:
        raise
    except Exception as e:
        logger.error(f"Failed to get workflow logs: {e}")
        raise HTTPException(status_code=500, detail=f"Failed to get workflow logs: {str(e)}")


@router.post("/{workflow_id}/human-approval", response_model=Dict[str, Any])
async def request_human_approval(
    workflow_id: str,
    request: HumanApprovalRequest,
    db=Depends(get_database)
):
    """
    Request human approval for a workflow stage.
    
    Args:
        workflow_id: ID of the workflow
        request: Human approval request
        db: Database dependency
    
    Returns:
        Dict containing approval request information
    """
    try:
        workflow = await db.get(Workflow, workflow_id)
        if not workflow:
            raise HTTPException(status_code=404, detail="Workflow not found")
        
        # Create approval request
        approval_id = f"{workflow_id}_{request.stage_id}_{int(datetime.utcnow().timestamp())}"
        
        approval_request = {
            "id": approval_id,
            "workflow_id": workflow_id,
            "stage_id": request.stage_id,
            "approval_type": request.approval_type,
            "content": request.content,
            "requested_date": datetime.utcnow().isoformat(),
            "timeout_seconds": request.timeout_seconds or settings.human_approval_timeout,
            "status": "pending"
        }
        
        # Store approval request in workflow
        if not workflow.pending_approvals:
            workflow.pending_approvals = []
        workflow.pending_approvals.append(approval_request)
        
        # Update workflow status
        workflow.status = WorkflowStatus.WAITING_APPROVAL
        workflow.updated_date = datetime.utcnow()
        
        await db.commit()
        
        logger.info(f"Human approval requested: {approval_id}")
        
        return {
            "approval_id": approval_id,
            "message": "Human approval requested",
            "timeout_seconds": approval_request["timeout_seconds"],
            "content": request.content
        }
        
    except HTTPException:
        raise
    except Exception as e:
        logger.error(f"Failed to request human approval: {e}")
        raise HTTPException(status_code=500, detail=f"Failed to request human approval: {str(e)}")


def create_workflow_stages(workflow_type: str) -> List[Dict[str, Any]]:
    """
    Create workflow stages based on type.
    
    Args:
        workflow_type: Type of workflow
    
    Returns:
        List of workflow stages
    """
    base_stages = [
        {
            "name": "requirements_analysis",
            "description": "Analyze SRS and generate separate SRDs",
            "agent": "RequirementsAnalyzer",
            "status": "pending",
            "requires_approval": True
        }
    ]
    
    backend_stages = [
        {
            "name": "api_design",
            "description": "Design FastAPI routes and OpenAPI schemas",
            "agent": "APIDesignerAgent",
            "status": "pending",
            "requires_approval": False
        },
        {
            "name": "model_development",
            "description": "Generate Pydantic models with validation",
            "agent": "ModelDeveloperAgent",
            "status": "pending",
            "requires_approval": False
        },
        {
            "name": "business_logic",
            "description": "Implement core business rules",
            "agent": "BusinessLogicAgent",
            "status": "pending",
            "requires_approval": False
        },
        {
            "name": "integration",
            "description": "Third-party API integration with resilience",
            "agent": "IntegrationAgent",
            "status": "pending",
            "requires_approval": False
        },
        {
            "name": "database_migration",
            "description": "Generate Alembic migration scripts",
            "agent": "DatabaseMigrationAgent",
            "status": "pending",
            "requires_approval": False
        }
    ]
    
    frontend_stages = [
        {
            "name": "component_design",
            "description": "Design Angular component architecture",
            "agent": "ComponentDesignerAgent",
            "status": "pending",
            "requires_approval": False
        },
        {
            "name": "service_development",
            "description": "Generate Angular services with caching/retry",
            "agent": "ServiceDeveloperAgent",
            "status": "pending",
            "requires_approval": False
        },
        {
            "name": "ui_implementation",
            "description": "Implement responsive SCSS/HTML",
            "agent": "UIImplementationAgent",
            "status": "pending",
            "requires_approval": False
        },
        {
            "name": "state_management",
            "description": "Generate NgRx store and effects",
            "agent": "StateManagementAgent",
            "status": "pending",
            "requires_approval": False
        },
        {
            "name": "routing",
            "description": "Configure Angular routing and navigation",
            "agent": "RouterAgent",
            "status": "pending",
            "requires_approval": False
        }
    ]
    
    test_stages = [
        {
            "name": "test_generation",
            "description": "Generate comprehensive test suites",
            "agent": "TestGeneratorAgent",
            "status": "pending",
            "requires_approval": True
        },
        {
            "name": "code_review",
            "description": "Automated code quality and security review",
            "agent": "CodeReviewAgent",
            "status": "pending",
            "requires_approval": True
        }
    ]
    
    if workflow_type == "full_generation":
        return base_stages + backend_stages + frontend_stages + test_stages
    elif workflow_type == "backend_only":
        return base_stages + backend_stages + test_stages
    elif workflow_type == "frontend_only":
        return base_stages + frontend_stages + test_stages
    else:
        return base_stages


def calculate_workflow_progress(stages: List[Dict[str, Any]], current_index: int) -> float:
    """
    Calculate workflow progress percentage.
    
    Args:
        stages: List of workflow stages
        current_index: Current stage index
    
    Returns:
        Progress percentage (0.0 to 100.0)
    """
    if not stages:
        return 100.0
    
    completed_stages = sum(1 for stage in stages if stage.get("status") == "completed")
    return (completed_stages / len(stages)) * 100.0


async def execute_workflow(workflow_id: str):
    """
    Execute workflow asynchronously.
    
    This function would orchestrate the execution of all workflow stages,
    calling appropriate agents and handling approvals.
    
    Args:
        workflow_id: ID of the workflow to execute
    """
    # This is a placeholder for the actual workflow execution logic
    # The real implementation would:
    # 1. Load the workflow from database
    # 2. Execute each stage sequentially
    # 3. Handle human approvals
    # 4. Manage agent failures and retries
    # 5. Update workflow status and progress
    
    logger.info(f"Workflow execution started: {workflow_id}")
    
    # For now, just log that execution started
    # The actual implementation would be added in the agents module


async def handle_workflow_approval(workflow: Workflow, data: Optional[Dict[str, Any]], db):
    """Handle workflow approval action."""
    workflow.status = WorkflowStatus.RUNNING
    # Continue workflow execution logic here


async def handle_workflow_rejection(workflow: Workflow, comment: Optional[str], db):
    """Handle workflow rejection action."""
    workflow.status = WorkflowStatus.FAILED
    if comment:
        workflow.rejection_reason = comment


async def handle_workflow_modification(workflow: Workflow, data: Optional[Dict[str, Any]], db):
    """Handle workflow modification action."""
    if data:
        workflow.options.update(data)
    workflow.status = WorkflowStatus.RUNNING


async def handle_workflow_cancellation(workflow: Workflow, db):
    """Handle workflow cancellation action."""
    workflow.status = WorkflowStatus.CANCELLED