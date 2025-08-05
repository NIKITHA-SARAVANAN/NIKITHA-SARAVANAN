"""
Agents management API routes.

Provides endpoints for managing agent registry, monitoring agent status,
and viewing agent execution history.
"""

from datetime import datetime
from typing import List, Optional, Dict, Any
from fastapi import APIRouter, HTTPException, Depends, Query
from pydantic import BaseModel
import sys
import os

# Add project root to path
sys.path.append(os.path.dirname(os.path.dirname(os.path.dirname(os.path.dirname(os.path.abspath(__file__))))))

from config.config import settings
from utils.logger import get_logger

logger = get_logger(__name__)

router = APIRouter()


class AgentInfo(BaseModel):
    """Agent information response model."""
    name: str
    description: str
    category: str  # requirements, backend, frontend, testing
    status: str    # available, busy, error, disabled
    version: str
    capabilities: List[str]
    last_executed: Optional[datetime]
    total_executions: int
    success_rate: float


class AgentExecution(BaseModel):
    """Agent execution history model."""
    id: str
    agent_name: str
    workflow_id: str
    document_id: str
    start_time: datetime
    end_time: Optional[datetime]
    status: str
    input_data: Dict[str, Any]
    output_data: Optional[Dict[str, Any]]
    error_message: Optional[str]
    execution_time_seconds: Optional[float]


class AgentRegistry(BaseModel):
    """Agent registry information model."""
    total_agents: int
    available_agents: int
    busy_agents: int
    error_agents: int
    categories: Dict[str, int]
    last_updated: datetime


@router.get("/registry", response_model=AgentRegistry)
async def get_agent_registry():
    """
    Get agent registry information.
    
    Returns:
        AgentRegistry: Current registry status
    """
    try:
        # This would be implemented with the actual agent registry
        # For now, return mock data
        
        agents_data = get_mock_agents_data()
        
        # Calculate statistics
        total_agents = len(agents_data)
        available_agents = sum(1 for agent in agents_data if agent["status"] == "available")
        busy_agents = sum(1 for agent in agents_data if agent["status"] == "busy")
        error_agents = sum(1 for agent in agents_data if agent["status"] == "error")
        
        # Count by categories
        categories = {}
        for agent in agents_data:
            category = agent["category"]
            categories[category] = categories.get(category, 0) + 1
        
        return AgentRegistry(
            total_agents=total_agents,
            available_agents=available_agents,
            busy_agents=busy_agents,
            error_agents=error_agents,
            categories=categories,
            last_updated=datetime.utcnow()
        )
        
    except Exception as e:
        logger.error(f"Failed to get agent registry: {e}")
        raise HTTPException(status_code=500, detail=f"Failed to get agent registry: {str(e)}")


@router.get("/", response_model=List[AgentInfo])
async def list_agents(
    category: Optional[str] = Query(None, description="Filter by category"),
    status: Optional[str] = Query(None, description="Filter by status")
):
    """
    List all available agents with their current status.
    
    Args:
        category: Optional category filter (requirements, backend, frontend, testing)
        status: Optional status filter (available, busy, error, disabled)
    
    Returns:
        List of agent information
    """
    try:
        agents_data = get_mock_agents_data()
        
        # Apply filters
        if category:
            agents_data = [agent for agent in agents_data if agent["category"] == category]
        
        if status:
            agents_data = [agent for agent in agents_data if agent["status"] == status]
        
        # Convert to response models
        agents = []
        for agent_data in agents_data:
            agents.append(AgentInfo(
                name=agent_data["name"],
                description=agent_data["description"],
                category=agent_data["category"],
                status=agent_data["status"],
                version=agent_data["version"],
                capabilities=agent_data["capabilities"],
                last_executed=agent_data.get("last_executed"),
                total_executions=agent_data.get("total_executions", 0),
                success_rate=agent_data.get("success_rate", 1.0)
            ))
        
        return agents
        
    except Exception as e:
        logger.error(f"Failed to list agents: {e}")
        raise HTTPException(status_code=500, detail=f"Failed to list agents: {str(e)}")


@router.get("/{agent_name}", response_model=AgentInfo)
async def get_agent(agent_name: str):
    """
    Get detailed information about a specific agent.
    
    Args:
        agent_name: Name of the agent
    
    Returns:
        AgentInfo: Detailed agent information
    """
    try:
        agents_data = get_mock_agents_data()
        
        agent_data = next((agent for agent in agents_data if agent["name"] == agent_name), None)
        if not agent_data:
            raise HTTPException(status_code=404, detail="Agent not found")
        
        return AgentInfo(
            name=agent_data["name"],
            description=agent_data["description"],
            category=agent_data["category"],
            status=agent_data["status"],
            version=agent_data["version"],
            capabilities=agent_data["capabilities"],
            last_executed=agent_data.get("last_executed"),
            total_executions=agent_data.get("total_executions", 0),
            success_rate=agent_data.get("success_rate", 1.0)
        )
        
    except HTTPException:
        raise
    except Exception as e:
        logger.error(f"Failed to get agent: {e}")
        raise HTTPException(status_code=500, detail=f"Failed to get agent: {str(e)}")


@router.get("/{agent_name}/history", response_model=List[AgentExecution])
async def get_agent_history(
    agent_name: str,
    limit: int = Query(50, ge=1, le=100, description="Limit number of results"),
    offset: int = Query(0, ge=0, description="Offset for pagination")
):
    """
    Get execution history for a specific agent.
    
    Args:
        agent_name: Name of the agent
        limit: Maximum number of executions to return
        offset: Number of executions to skip
    
    Returns:
        List of agent executions
    """
    try:
        # This would query the actual execution history from database
        # For now, return mock data
        
        mock_executions = get_mock_execution_history(agent_name)
        
        # Apply pagination
        paginated_executions = mock_executions[offset:offset + limit]
        
        return [
            AgentExecution(
                id=execution["id"],
                agent_name=execution["agent_name"],
                workflow_id=execution["workflow_id"],
                document_id=execution["document_id"],
                start_time=execution["start_time"],
                end_time=execution.get("end_time"),
                status=execution["status"],
                input_data=execution["input_data"],
                output_data=execution.get("output_data"),
                error_message=execution.get("error_message"),
                execution_time_seconds=execution.get("execution_time_seconds")
            )
            for execution in paginated_executions
        ]
        
    except HTTPException:
        raise
    except Exception as e:
        logger.error(f"Failed to get agent history: {e}")
        raise HTTPException(status_code=500, detail=f"Failed to get agent history: {str(e)}")


@router.post("/{agent_name}/enable")
async def enable_agent(agent_name: str):
    """
    Enable an agent for execution.
    
    Args:
        agent_name: Name of the agent
    
    Returns:
        Dict containing confirmation message
    """
    try:
        # This would interact with the actual agent registry
        # For now, just return success
        
        logger.info(f"Agent enabled: {agent_name}")
        
        return {
            "message": f"Agent {agent_name} enabled successfully",
            "agent_name": agent_name,
            "status": "available"
        }
        
    except Exception as e:
        logger.error(f"Failed to enable agent: {e}")
        raise HTTPException(status_code=500, detail=f"Failed to enable agent: {str(e)}")


@router.post("/{agent_name}/disable")
async def disable_agent(agent_name: str):
    """
    Disable an agent from execution.
    
    Args:
        agent_name: Name of the agent
    
    Returns:
        Dict containing confirmation message
    """
    try:
        # This would interact with the actual agent registry
        # For now, just return success
        
        logger.info(f"Agent disabled: {agent_name}")
        
        return {
            "message": f"Agent {agent_name} disabled successfully",
            "agent_name": agent_name,
            "status": "disabled"
        }
        
    except Exception as e:
        logger.error(f"Failed to disable agent: {e}")
        raise HTTPException(status_code=500, detail=f"Failed to disable agent: {str(e)}")


@router.get("/metrics/performance")
async def get_agent_performance_metrics():
    """
    Get performance metrics for all agents.
    
    Returns:
        Dict containing performance metrics
    """
    try:
        # This would calculate real metrics from execution history
        # For now, return mock metrics
        
        return {
            "total_executions": 1234,
            "average_execution_time": 45.6,
            "success_rate": 0.95,
            "agents_by_category": {
                "requirements": {"executions": 100, "success_rate": 0.98},
                "backend": {"executions": 500, "success_rate": 0.94},
                "frontend": {"executions": 450, "success_rate": 0.96},
                "testing": {"executions": 184, "success_rate": 0.92}
            },
            "recent_failures": [
                {
                    "agent_name": "IntegrationAgent",
                    "error": "API timeout",
                    "timestamp": datetime.utcnow().isoformat()
                }
            ]
        }
        
    except Exception as e:
        logger.error(f"Failed to get performance metrics: {e}")
        raise HTTPException(status_code=500, detail=f"Failed to get performance metrics: {str(e)}")


def get_mock_agents_data() -> List[Dict[str, Any]]:
    """Get mock agents data for development."""
    return [
        {
            "name": "RequirementsAnalyzer",
            "description": "Analyzes SRS documents and generates separate backend/frontend SRDs",
            "category": "requirements",
            "status": "available",
            "version": "1.0.0",
            "capabilities": ["document_parsing", "requirements_extraction", "srd_generation"],
            "last_executed": datetime(2024, 1, 15, 10, 30),
            "total_executions": 25,
            "success_rate": 0.96
        },
        {
            "name": "APIDesignerAgent",
            "description": "Designs FastAPI routes and OpenAPI schemas",
            "category": "backend",
            "status": "available",
            "version": "1.0.0",
            "capabilities": ["api_design", "openapi_generation", "route_planning"],
            "total_executions": 18,
            "success_rate": 0.94
        },
        {
            "name": "ModelDeveloperAgent",
            "description": "Generates Pydantic models with validation",
            "category": "backend",
            "status": "available",
            "version": "1.0.0",
            "capabilities": ["model_generation", "validation_rules", "serialization"],
            "total_executions": 20,
            "success_rate": 0.95
        },
        {
            "name": "BusinessLogicAgent",
            "description": "Implements core business rule functions and classes",
            "category": "backend",
            "status": "busy",
            "version": "1.0.0",
            "capabilities": ["business_logic", "function_generation", "class_design"],
            "total_executions": 15,
            "success_rate": 0.93
        },
        {
            "name": "IntegrationAgent",
            "description": "Handles third-party API integration with resilience patterns",
            "category": "backend",
            "status": "error",
            "version": "1.0.0",
            "capabilities": ["api_integration", "retry_logic", "circuit_breaker"],
            "total_executions": 12,
            "success_rate": 0.83
        },
        {
            "name": "DatabaseMigrationAgent",
            "description": "Generates Alembic migration scripts with rollback support",
            "category": "backend",
            "status": "available",
            "version": "1.0.0",
            "capabilities": ["migration_generation", "schema_design", "rollback_scripts"],
            "total_executions": 10,
            "success_rate": 0.90
        },
        {
            "name": "ComponentDesignerAgent",
            "description": "Designs Angular component architecture with lazy loading",
            "category": "frontend",
            "status": "available",
            "version": "1.0.0",
            "capabilities": ["component_design", "lazy_loading", "architecture_planning"],
            "total_executions": 22,
            "success_rate": 0.95
        },
        {
            "name": "ServiceDeveloperAgent",
            "description": "Generates Angular services with caching and retry logic",
            "category": "frontend",
            "status": "available",
            "version": "1.0.0",
            "capabilities": ["service_generation", "caching", "retry_logic"],
            "total_executions": 20,
            "success_rate": 0.94
        },
        {
            "name": "UIImplementationAgent",
            "description": "Implements responsive SCSS/HTML with accessibility features",
            "category": "frontend",
            "status": "available",
            "version": "1.0.0",
            "capabilities": ["ui_implementation", "responsive_design", "accessibility"],
            "total_executions": 18,
            "success_rate": 0.97
        },
        {
            "name": "StateManagementAgent",
            "description": "Generates NgRx store and effects with optimistic updates",
            "category": "frontend",
            "status": "available",
            "version": "1.0.0",
            "capabilities": ["state_management", "ngrx", "optimistic_updates"],
            "total_executions": 16,
            "success_rate": 0.94
        },
        {
            "name": "RouterAgent",
            "description": "Configures Angular routing and navigation with guards",
            "category": "frontend",
            "status": "available",
            "version": "1.0.0",
            "capabilities": ["routing", "navigation", "route_guards"],
            "total_executions": 14,
            "success_rate": 0.96
        },
        {
            "name": "TestGeneratorAgent",
            "description": "Generates comprehensive test suites with edge case coverage",
            "category": "testing",
            "status": "available",
            "version": "1.0.0",
            "capabilities": ["test_generation", "edge_cases", "coverage_analysis"],
            "total_executions": 8,
            "success_rate": 0.88
        },
        {
            "name": "CodeReviewAgent",
            "description": "Performs automated code quality and security analysis",
            "category": "testing",
            "status": "available",
            "version": "1.0.0",
            "capabilities": ["code_review", "security_analysis", "quality_metrics"],
            "total_executions": 6,
            "success_rate": 0.92
        }
    ]


def get_mock_execution_history(agent_name: str) -> List[Dict[str, Any]]:
    """Get mock execution history for an agent."""
    base_time = datetime(2024, 1, 1)
    
    return [
        {
            "id": f"exec_{i}_{agent_name.lower()}",
            "agent_name": agent_name,
            "workflow_id": f"workflow_{i}",
            "document_id": f"doc_{i}",
            "start_time": base_time.replace(day=i+1, hour=10, minute=30),
            "end_time": base_time.replace(day=i+1, hour=10, minute=35),
            "status": "completed" if i % 10 != 0 else "failed",
            "input_data": {"document_id": f"doc_{i}", "config": {}},
            "output_data": {"result": "success"} if i % 10 != 0 else None,
            "error_message": "Timeout error" if i % 10 == 0 else None,
            "execution_time_seconds": 300.0 if i % 10 != 0 else None
        }
        for i in range(1, 21)
    ]