"""
Health check API routes.

Provides endpoints for monitoring application health, system status,
and dependency availability.
"""

import asyncio
import psutil
import time
from datetime import datetime
from typing import Dict, Any, Optional
from fastapi import APIRouter, HTTPException, Depends
from pydantic import BaseModel
import sys
import os

# Add project root to path
sys.path.append(os.path.dirname(os.path.dirname(os.path.dirname(os.path.dirname(os.path.abspath(__file__))))))

from config.config import settings
from utils.logger import get_logger
from backend.database import get_db_status
from backend.models.database import Document

logger = get_logger(__name__)

router = APIRouter()


class HealthStatus(BaseModel):
    """Health status response model."""
    status: str
    timestamp: datetime
    version: str
    environment: str
    uptime_seconds: float


class DetailedHealthStatus(BaseModel):
    """Detailed health status response model."""
    status: str
    timestamp: datetime
    version: str
    environment: str
    uptime_seconds: float
    system: Dict[str, Any]
    database: Dict[str, Any]
    dependencies: Dict[str, Any]
    agent_registry: Dict[str, Any]


# Application start time for uptime calculation
_start_time = time.time()


@router.get("/health", response_model=HealthStatus)
async def health_check():
    """
    Basic health check endpoint.
    
    Returns basic application status information.
    
    Returns:
        HealthStatus: Basic health information
    """
    try:
        uptime = time.time() - _start_time
        
        return HealthStatus(
            status="healthy",
            timestamp=datetime.utcnow(),
            version="1.0.0",
            environment=settings.environment.value,
            uptime_seconds=uptime
        )
    except Exception as e:
        logger.error(f"Health check failed: {e}")
        raise HTTPException(status_code=503, detail="Service unavailable")


@router.get("/health/detailed", response_model=DetailedHealthStatus)
async def detailed_health_check():
    """
    Detailed health check endpoint.
    
    Returns comprehensive system status including database connectivity,
    system resources, and dependency availability.
    
    Returns:
        DetailedHealthStatus: Comprehensive health information
    """
    try:
        uptime = time.time() - _start_time
        
        # System information
        system_info = await get_system_info()
        
        # Database status
        db_status = await get_database_status()
        
        # Dependencies status
        deps_status = await get_dependencies_status()
        
        # Agent registry status
        agent_status = await get_agent_registry_status()
        
        # Determine overall status
        overall_status = "healthy"
        if not db_status["connected"] or not all(deps_status.values()):
            overall_status = "degraded"
        
        return DetailedHealthStatus(
            status=overall_status,
            timestamp=datetime.utcnow(),
            version="1.0.0",
            environment=settings.environment.value,
            uptime_seconds=uptime,
            system=system_info,
            database=db_status,
            dependencies=deps_status,
            agent_registry=agent_status
        )
    except Exception as e:
        logger.error(f"Detailed health check failed: {e}")
        raise HTTPException(status_code=503, detail="Service unavailable")


@router.get("/health/readiness")
async def readiness_check():
    """
    Kubernetes-style readiness check.
    
    Returns 200 if the application is ready to serve requests,
    503 otherwise.
    """
    try:
        # Check database connectivity
        db_status = await get_database_status()
        
        if not db_status["connected"]:
            raise HTTPException(status_code=503, detail="Database not ready")
        
        return {"status": "ready"}
    except HTTPException:
        raise
    except Exception as e:
        logger.error(f"Readiness check failed: {e}")
        raise HTTPException(status_code=503, detail="Service not ready")


@router.get("/health/liveness")
async def liveness_check():
    """
    Kubernetes-style liveness check.
    
    Returns 200 if the application is alive, 503 otherwise.
    """
    try:
        # Simple check to ensure the application is responding
        return {"status": "alive"}
    except Exception as e:
        logger.error(f"Liveness check failed: {e}")
        raise HTTPException(status_code=503, detail="Service not alive")


async def get_system_info() -> Dict[str, Any]:
    """
    Get system resource information.
    
    Returns:
        Dict containing system information
    """
    try:
        # CPU information
        cpu_percent = psutil.cpu_percent(interval=1)
        cpu_count = psutil.cpu_count()
        
        # Memory information
        memory = psutil.virtual_memory()
        
        # Disk information
        disk = psutil.disk_usage('/')
        
        # Process information
        process = psutil.Process()
        process_memory = process.memory_info()
        
        return {
            "cpu": {
                "usage_percent": cpu_percent,
                "count": cpu_count
            },
            "memory": {
                "total": memory.total,
                "available": memory.available,
                "percent": memory.percent,
                "process_rss": process_memory.rss,
                "process_vms": process_memory.vms
            },
            "disk": {
                "total": disk.total,
                "used": disk.used,
                "free": disk.free,
                "percent": (disk.used / disk.total) * 100
            },
            "load_average": os.getloadavg() if hasattr(os, 'getloadavg') else None
        }
    except Exception as e:
        logger.warning(f"Failed to get system info: {e}")
        return {"error": str(e)}


async def get_database_status() -> Dict[str, Any]:
    """
    Get database connectivity status.
    
    Returns:
        Dict containing database status information
    """
    try:
        db_status = await get_db_status()
        
        # Try a simple query to test connectivity
        # This would be implemented in the database module
        
        return {
            "connected": db_status,
            "url": settings.database_url.replace(
                settings.database_url.split('@')[0].split('://')[-1] + '@', 
                '***@'
            ) if '@' in settings.database_url else settings.database_url,
            "echo": settings.database_echo
        }
    except Exception as e:
        logger.warning(f"Database status check failed: {e}")
        return {
            "connected": False,
            "error": str(e)
        }


async def get_dependencies_status() -> Dict[str, bool]:
    """
    Check status of external dependencies.
    
    Returns:
        Dict mapping dependency names to their availability status
    """
    dependencies = {}
    
    # Check document parsing libraries
    try:
        import PyPDF2
        dependencies["PyPDF2"] = True
    except ImportError:
        dependencies["PyPDF2"] = False
    
    try:
        from docx import Document
        dependencies["python-docx"] = True
    except ImportError:
        dependencies["python-docx"] = False
    
    try:
        import markdown
        dependencies["markdown"] = True
    except ImportError:
        dependencies["markdown"] = False
    
    # Check LLM provider availability
    try:
        if settings.llm_provider.value == "openai" and settings.openai_api_key:
            dependencies["openai"] = True
        elif settings.llm_provider.value == "anthropic" and settings.anthropic_api_key:
            dependencies["anthropic"] = True
        else:
            dependencies["llm_provider"] = False
    except Exception:
        dependencies["llm_provider"] = False
    
    # Check Redis availability (if configured)
    try:
        import redis
        r = redis.from_url(settings.redis_url)
        await asyncio.to_thread(r.ping)
        dependencies["redis"] = True
    except Exception:
        dependencies["redis"] = False
    
    # Check LangSmith availability (if configured)
    if settings.langsmith_api_key:
        try:
            from langsmith import Client
            dependencies["langsmith"] = True
        except ImportError:
            dependencies["langsmith"] = False
    else:
        dependencies["langsmith"] = True  # Not required if not configured
    
    return dependencies


async def get_agent_registry_status() -> Dict[str, Any]:
    """
    Get agent registry status information.
    
    Returns:
        Dict containing agent registry status
    """
    try:
        # This would be implemented once we have the agent registry
        # For now, return placeholder information
        
        return {
            "initialized": True,
            "available_agents": [
                "RequirementsAnalyzer",
                "APIDesignerAgent", 
                "ModelDeveloperAgent",
                "BusinessLogicAgent",
                "IntegrationAgent",
                "DatabaseMigrationAgent",
                "ComponentDesignerAgent",
                "ServiceDeveloperAgent", 
                "UIImplementationAgent",
                "StateManagementAgent",
                "RouterAgent"
            ],
            "active_workflows": 0,
            "total_processed": 0
        }
    except Exception as e:
        logger.warning(f"Agent registry status check failed: {e}")
        return {
            "initialized": False,
            "error": str(e)
        }