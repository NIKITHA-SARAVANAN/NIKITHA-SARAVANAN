"""
Agent management endpoints for the SRC Generator API.

These endpoints handle agent workflows, status monitoring, and execution control.
"""

from datetime import datetime
from typing import List, Optional, Dict, Any

from fastapi import APIRouter, HTTPException
from pydantic import BaseModel

from utils.logging_config import get_logger, log_agent_event

logger = get_logger(__name__)
router = APIRouter()


class AgentInfo(BaseModel):
    """Agent information model."""
    
    agent_id: str
    name: str
    description: str
    status: str
    last_run: Optional[datetime] = None
    success_rate: float
    average_duration: Optional[float] = None
    capabilities: List[str]


class AgentExecutionRequest(BaseModel):
    """Agent execution request model."""
    
    agent_id: str
    input_data: Dict[str, Any]
    options: Optional[Dict[str, Any]] = None


class AgentExecutionResponse(BaseModel):
    """Agent execution response model."""
    
    execution_id: str
    agent_id: str
    status: str
    started_at: datetime
    input_data: Dict[str, Any]
    progress_percent: int
    current_step: str
    message: str


class AgentResultResponse(BaseModel):
    """Agent execution result model."""
    
    execution_id: str
    agent_id: str
    status: str
    started_at: datetime
    completed_at: Optional[datetime] = None
    duration_seconds: Optional[float] = None
    input_data: Dict[str, Any]
    output_data: Optional[Dict[str, Any]] = None
    error: Optional[str] = None
    logs: List[Dict[str, Any]]


# Mock agent registry and execution tracking
agent_registry = {
    "requirements_analyzer": {
        "name": "Requirements Analyzer",
        "description": "Analyzes SRC documents and generates separate frontend/backend SRDs",
        "status": "available",
        "last_run": None,
        "success_rate": 0.95,
        "average_duration": 45.0,
        "capabilities": ["document_analysis", "srd_generation", "dependency_detection"]
    },
    "api_designer": {
        "name": "API Designer Agent",
        "description": "Generates FastAPI route skeletons and OpenAPI schemas",
        "status": "available",
        "last_run": None,
        "success_rate": 0.92,
        "average_duration": 30.0,
        "capabilities": ["api_design", "openapi_generation", "route_scaffolding"]
    },
    "model_developer": {
        "name": "Model Developer Agent",
        "description": "Generates Pydantic models with validation",
        "status": "available",
        "last_run": None,
        "success_rate": 0.98,
        "average_duration": 20.0,
        "capabilities": ["model_generation", "validation_rules", "schema_design"]
    },
    "component_designer": {
        "name": "Component Designer Agent",
        "description": "Generates Angular component sketches with lazy loading",
        "status": "available",
        "last_run": None,
        "success_rate": 0.89,
        "average_duration": 35.0,
        "capabilities": ["component_scaffolding", "lazy_loading", "responsive_design"]
    },
    "code_reviewer": {
        "name": "Code Review Agent",
        "description": "Reviews generated code for quality and security issues",
        "status": "available",
        "last_run": None,
        "success_rate": 0.94,
        "average_duration": 25.0,
        "capabilities": ["code_review", "security_analysis", "best_practices"]
    }
}

execution_history = {}


@router.get("/agents", response_model=List[AgentInfo])
async def list_agents():
    """
    List all available agents.
    
    Returns information about all registered agents including their
    status, capabilities, and performance metrics.
    """
    agents = []
    
    for agent_id, agent_data in agent_registry.items():
        agents.append(AgentInfo(
            agent_id=agent_id,
            name=agent_data["name"],
            description=agent_data["description"],
            status=agent_data["status"],
            last_run=agent_data["last_run"],
            success_rate=agent_data["success_rate"],
            average_duration=agent_data["average_duration"],
            capabilities=agent_data["capabilities"]
        ))
    
    logger.info(f"Listed {len(agents)} available agents")
    return agents


@router.get("/agents/{agent_id}", response_model=AgentInfo)
async def get_agent(agent_id: str):
    """
    Get detailed information about a specific agent.
    
    Returns comprehensive information about the agent including
    its current status and capabilities.
    """
    if agent_id not in agent_registry:
        raise HTTPException(
            status_code=404,
            detail=f"Agent '{agent_id}' not found"
        )
    
    agent_data = agent_registry[agent_id]
    
    return AgentInfo(
        agent_id=agent_id,
        name=agent_data["name"],
        description=agent_data["description"],
        status=agent_data["status"],
        last_run=agent_data["last_run"],
        success_rate=agent_data["success_rate"],
        average_duration=agent_data["average_duration"],
        capabilities=agent_data["capabilities"]
    )


@router.post("/agents/execute", response_model=AgentExecutionResponse)
async def execute_agent(request: AgentExecutionRequest):
    """
    Execute an agent with the provided input data.
    
    Starts agent execution and returns execution tracking information.
    This is a skeleton implementation - actual agent logic will be added later.
    """
    if request.agent_id not in agent_registry:
        raise HTTPException(
            status_code=404,
            detail=f"Agent '{request.agent_id}' not found"
        )
    
    agent_data = agent_registry[request.agent_id]
    
    if agent_data["status"] != "available":
        raise HTTPException(
            status_code=409,
            detail=f"Agent '{request.agent_id}' is not available (status: {agent_data['status']})"
        )
    
    # Generate execution ID
    import uuid
    execution_id = str(uuid.uuid4())
    
    # Update agent status
    agent_registry[request.agent_id]["status"] = "running"
    agent_registry[request.agent_id]["last_run"] = datetime.utcnow()
    
    # Track execution
    execution_history[execution_id] = {
        "agent_id": request.agent_id,
        "status": "running",
        "started_at": datetime.utcnow(),
        "completed_at": None,
        "input_data": request.input_data,
        "output_data": None,
        "error": None,
        "progress_percent": 0,
        "current_step": "Initializing",
        "logs": []
    }
    
    log_agent_event(
        request.agent_id,
        "START",
        f"Agent execution started",
        {"execution_id": execution_id, "input_keys": list(request.input_data.keys())}
    )
    
    logger.info(
        "Agent execution started",
        agent_id=request.agent_id,
        execution_id=execution_id
    )
    
    # TODO: Start actual agent execution in background task
    # For now, we'll simulate progress
    
    return AgentExecutionResponse(
        execution_id=execution_id,
        agent_id=request.agent_id,
        status="running",
        started_at=datetime.utcnow(),
        input_data=request.input_data,
        progress_percent=0,
        current_step="Initializing",
        message="Agent execution started"
    )


@router.get("/agents/executions/{execution_id}", response_model=AgentResultResponse)
async def get_execution_result(execution_id: str):
    """
    Get the result of an agent execution.
    
    Returns the current status and results of an agent execution.
    """
    if execution_id not in execution_history:
        raise HTTPException(
            status_code=404,
            detail=f"Execution '{execution_id}' not found"
        )
    
    execution_data = execution_history[execution_id]
    
    return AgentResultResponse(
        execution_id=execution_id,
        agent_id=execution_data["agent_id"],
        status=execution_data["status"],
        started_at=execution_data["started_at"],
        completed_at=execution_data["completed_at"],
        duration_seconds=(
            (execution_data["completed_at"] - execution_data["started_at"]).total_seconds()
            if execution_data["completed_at"] else None
        ),
        input_data=execution_data["input_data"],
        output_data=execution_data["output_data"],
        error=execution_data["error"],
        logs=execution_data["logs"]
    )


@router.get("/agents/executions", response_model=List[AgentResultResponse])
async def list_executions(agent_id: Optional[str] = None, limit: int = 50):
    """
    List agent executions.
    
    Returns a list of recent agent executions, optionally filtered by agent ID.
    """
    executions = []
    
    for execution_id, execution_data in execution_history.items():
        # Filter by agent_id if provided
        if agent_id and execution_data["agent_id"] != agent_id:
            continue
        
        executions.append(AgentResultResponse(
            execution_id=execution_id,
            agent_id=execution_data["agent_id"],
            status=execution_data["status"],
            started_at=execution_data["started_at"],
            completed_at=execution_data["completed_at"],
            duration_seconds=(
                (execution_data["completed_at"] - execution_data["started_at"]).total_seconds()
                if execution_data["completed_at"] else None
            ),
            input_data=execution_data["input_data"],
            output_data=execution_data["output_data"],
            error=execution_data["error"],
            logs=execution_data["logs"]
        ))
    
    # Sort by start time (most recent first) and limit results
    executions.sort(key=lambda x: x.started_at, reverse=True)
    return executions[:limit]


@router.post("/agents/{agent_id}/stop")
async def stop_agent(agent_id: str):
    """
    Stop a running agent.
    
    Attempts to gracefully stop a running agent execution.
    """
    if agent_id not in agent_registry:
        raise HTTPException(
            status_code=404,
            detail=f"Agent '{agent_id}' not found"
        )
    
    agent_data = agent_registry[agent_id]
    
    if agent_data["status"] != "running":
        raise HTTPException(
            status_code=409,
            detail=f"Agent '{agent_id}' is not running (status: {agent_data['status']})"
        )
    
    # TODO: Implement actual agent stopping logic
    
    # Update agent status
    agent_registry[agent_id]["status"] = "available"
    
    log_agent_event(
        agent_id,
        "STOP",
        "Agent execution stopped by user request"
    )
    
    logger.info(
        "Agent execution stopped",
        agent_id=agent_id
    )
    
    return {"message": f"Agent '{agent_id}' stopped successfully"}


@router.get("/agents/{agent_id}/metrics")
async def get_agent_metrics(agent_id: str):
    """
    Get performance metrics for a specific agent.
    
    Returns detailed performance and usage statistics for the agent.
    """
    if agent_id not in agent_registry:
        raise HTTPException(
            status_code=404,
            detail=f"Agent '{agent_id}' not found"
        )
    
    # Calculate metrics from execution history
    agent_executions = [
        exec_data for exec_data in execution_history.values()
        if exec_data["agent_id"] == agent_id
    ]
    
    total_executions = len(agent_executions)
    successful_executions = len([
        exec_data for exec_data in agent_executions
        if exec_data["status"] == "completed"
    ])
    failed_executions = len([
        exec_data for exec_data in agent_executions
        if exec_data["status"] == "failed"
    ])
    
    # Calculate average duration for completed executions
    completed_executions = [
        exec_data for exec_data in agent_executions
        if exec_data["status"] == "completed" and exec_data["completed_at"]
    ]
    
    average_duration = None
    if completed_executions:
        durations = [
            (exec_data["completed_at"] - exec_data["started_at"]).total_seconds()
            for exec_data in completed_executions
        ]
        average_duration = sum(durations) / len(durations)
    
    return {
        "agent_id": agent_id,
        "total_executions": total_executions,
        "successful_executions": successful_executions,
        "failed_executions": failed_executions,
        "success_rate": successful_executions / total_executions if total_executions > 0 else 0,
        "average_duration_seconds": average_duration,
        "current_status": agent_registry[agent_id]["status"],
        "last_execution": agent_executions[-1]["started_at"] if agent_executions else None
    }