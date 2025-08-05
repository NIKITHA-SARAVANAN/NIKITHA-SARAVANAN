"""
Health check endpoints for the SRC Generator API.

These endpoints provide system health status and monitoring information.
"""

import asyncio
import platform
import psutil
from datetime import datetime, timezone
from typing import Dict, Any

from fastapi import APIRouter, Depends
from pydantic import BaseModel

from config.config import get_settings
from utils.logging_config import get_logger


logger = get_logger(__name__)
router = APIRouter()


class HealthResponse(BaseModel):
    """Health check response model."""
    
    status: str
    timestamp: datetime
    version: str
    environment: str
    uptime_seconds: float
    system_info: Dict[str, Any]
    dependencies: Dict[str, str]


class DetailedHealthResponse(BaseModel):
    """Detailed health check response model."""
    
    status: str
    timestamp: datetime
    version: str
    environment: str
    uptime_seconds: float
    system_info: Dict[str, Any]
    dependencies: Dict[str, str]
    performance_metrics: Dict[str, Any]
    agent_status: Dict[str, Any]


# Track startup time for uptime calculation
startup_time = datetime.now(timezone.utc)


@router.get("/health", response_model=HealthResponse)
async def health_check():
    """
    Basic health check endpoint.
    
    Returns basic system health information including status,
    timestamp, and system metrics.
    """
    try:
        settings = get_settings()
        current_time = datetime.now(timezone.utc)
        uptime = (current_time - startup_time).total_seconds()
        
        # Get basic system information
        system_info = {
            "platform": platform.system(),
            "platform_version": platform.version(),
            "python_version": platform.python_version(),
            "cpu_count": psutil.cpu_count(),
            "memory_total_gb": round(psutil.virtual_memory().total / (1024**3), 2),
            "memory_available_gb": round(psutil.virtual_memory().available / (1024**3), 2),
            "memory_percent": psutil.virtual_memory().percent,
            "disk_usage_percent": psutil.disk_usage('/').percent
        }
        
        # Check dependencies status
        dependencies = await _check_dependencies()
        
        # Determine overall status
        status = "healthy" if all(
            dep_status == "ok" for dep_status in dependencies.values()
        ) else "degraded"
        
        response = HealthResponse(
            status=status,
            timestamp=current_time,
            version="1.0.0",
            environment=settings.environment,
            uptime_seconds=uptime,
            system_info=system_info,
            dependencies=dependencies
        )
        
        logger.info("Health check completed", status=status)
        return response
        
    except Exception as e:
        logger.error("Health check failed", error=str(e))
        return HealthResponse(
            status="unhealthy",
            timestamp=datetime.now(timezone.utc),
            version="1.0.0",
            environment="unknown",
            uptime_seconds=0,
            system_info={},
            dependencies={}
        )


@router.get("/health/detailed", response_model=DetailedHealthResponse)
async def detailed_health_check():
    """
    Detailed health check endpoint.
    
    Returns comprehensive system health information including
    performance metrics and agent status.
    """
    try:
        settings = get_settings()
        current_time = datetime.now(timezone.utc)
        uptime = (current_time - startup_time).total_seconds()
        
        # Get detailed system information
        system_info = {
            "platform": platform.system(),
            "platform_version": platform.version(),
            "python_version": platform.python_version(),
            "cpu_count": psutil.cpu_count(),
            "memory_total_gb": round(psutil.virtual_memory().total / (1024**3), 2),
            "memory_available_gb": round(psutil.virtual_memory().available / (1024**3), 2),
            "memory_percent": psutil.virtual_memory().percent,
            "disk_usage_percent": psutil.disk_usage('/').percent,
            "boot_time": datetime.fromtimestamp(psutil.boot_time()).isoformat(),
            "load_average": list(psutil.getloadavg()) if hasattr(psutil, 'getloadavg') else None
        }
        
        # Get performance metrics
        performance_metrics = await _get_performance_metrics()
        
        # Check dependencies status
        dependencies = await _check_dependencies()
        
        # Get agent status
        agent_status = await _get_agent_status()
        
        # Determine overall status
        status = "healthy"
        if not all(dep_status == "ok" for dep_status in dependencies.values()):
            status = "degraded"
        if any(agent["status"] == "error" for agent in agent_status.values()):
            status = "degraded"
        if system_info["memory_percent"] > 90 or system_info["disk_usage_percent"] > 90:
            status = "degraded"
        
        response = DetailedHealthResponse(
            status=status,
            timestamp=current_time,
            version="1.0.0",
            environment=settings.environment,
            uptime_seconds=uptime,
            system_info=system_info,
            dependencies=dependencies,
            performance_metrics=performance_metrics,
            agent_status=agent_status
        )
        
        logger.info("Detailed health check completed", status=status)
        return response
        
    except Exception as e:
        logger.error("Detailed health check failed", error=str(e))
        return DetailedHealthResponse(
            status="unhealthy",
            timestamp=datetime.now(timezone.utc),
            version="1.0.0",
            environment="unknown",
            uptime_seconds=0,
            system_info={},
            dependencies={},
            performance_metrics={},
            agent_status={}
        )


@router.get("/health/readiness")
async def readiness_check():
    """
    Readiness check endpoint for Kubernetes or container orchestration.
    
    Returns 200 if the service is ready to receive traffic,
    503 if not ready.
    """
    try:
        # Check if critical dependencies are available
        dependencies = await _check_dependencies()
        
        # Service is ready if core dependencies are ok
        core_deps = ["file_system", "memory"]
        is_ready = all(
            dependencies.get(dep) == "ok" for dep in core_deps
        )
        
        if is_ready:
            return {"status": "ready", "timestamp": datetime.now(timezone.utc)}
        else:
            from fastapi import HTTPException
            raise HTTPException(
                status_code=503,
                detail="Service not ready"
            )
            
    except Exception as e:
        logger.error("Readiness check failed", error=str(e))
        from fastapi import HTTPException
        raise HTTPException(
            status_code=503,
            detail="Service not ready"
        )


@router.get("/health/liveness")
async def liveness_check():
    """
    Liveness check endpoint for Kubernetes or container orchestration.
    
    Returns 200 if the service is alive and should not be restarted,
    503 if the service should be restarted.
    """
    try:
        # Basic check that the service is responsive
        current_time = datetime.now(timezone.utc)
        uptime = (current_time - startup_time).total_seconds()
        
        # Check if memory usage is critically high
        memory_percent = psutil.virtual_memory().percent
        if memory_percent > 95:
            from fastapi import HTTPException
            raise HTTPException(
                status_code=503,
                detail="Critical memory usage"
            )
        
        return {
            "status": "alive",
            "timestamp": current_time,
            "uptime_seconds": uptime
        }
        
    except Exception as e:
        logger.error("Liveness check failed", error=str(e))
        from fastapi import HTTPException
        raise HTTPException(
            status_code=503,
            detail="Service not alive"
        )


async def _check_dependencies() -> Dict[str, str]:
    """Check the status of external dependencies."""
    dependencies = {}
    
    try:
        # Check file system accessibility
        import tempfile
        with tempfile.NamedTemporaryFile() as tmp:
            tmp.write(b"test")
        dependencies["file_system"] = "ok"
    except Exception:
        dependencies["file_system"] = "error"
    
    try:
        # Check memory availability
        memory = psutil.virtual_memory()
        if memory.percent < 95:
            dependencies["memory"] = "ok"
        else:
            dependencies["memory"] = "degraded"
    except Exception:
        dependencies["memory"] = "error"
    
    try:
        # Check disk space
        disk = psutil.disk_usage('/')
        if disk.percent < 95:
            dependencies["disk"] = "ok"
        else:
            dependencies["disk"] = "degraded"
    except Exception:
        dependencies["disk"] = "error"
    
    # TODO: Add database connectivity check
    dependencies["database"] = "not_configured"
    
    # TODO: Add LLM provider connectivity check
    dependencies["llm_provider"] = "not_configured"
    
    # TODO: Add MCP servers check
    dependencies["mcp_servers"] = "not_configured"
    
    return dependencies


async def _get_performance_metrics() -> Dict[str, Any]:
    """Get current performance metrics."""
    try:
        return {
            "cpu_percent": psutil.cpu_percent(interval=1),
            "memory_usage_mb": psutil.virtual_memory().used / (1024**2),
            "disk_io": {
                "read_bytes": psutil.disk_io_counters().read_bytes if psutil.disk_io_counters() else 0,
                "write_bytes": psutil.disk_io_counters().write_bytes if psutil.disk_io_counters() else 0,
            },
            "network_io": {
                "bytes_sent": psutil.net_io_counters().bytes_sent,
                "bytes_recv": psutil.net_io_counters().bytes_recv,
            },
            "open_files": len(psutil.Process().open_files()),
            "threads": psutil.Process().num_threads()
        }
    except Exception as e:
        logger.warning("Failed to get performance metrics", error=str(e))
        return {}


async def _get_agent_status() -> Dict[str, Any]:
    """Get the status of all registered agents."""
    # TODO: Implement agent registry integration
    return {
        "requirements_analyzer": {"status": "not_configured", "last_run": None},
        "api_designer": {"status": "not_configured", "last_run": None},
        "model_developer": {"status": "not_configured", "last_run": None},
        "component_designer": {"status": "not_configured", "last_run": None},
        "code_reviewer": {"status": "not_configured", "last_run": None}
    }