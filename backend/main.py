"""
Main FastAPI application for the SRC to Application Generator.

This module sets up the FastAPI application with all routes, middleware,
and configuration for the multi-agent system.
"""

import logging
import sys
from contextlib import asynccontextmanager
from pathlib import Path

from fastapi import FastAPI, HTTPException
from fastapi.middleware.cors import CORSMiddleware
from fastapi.middleware.trustedhost import TrustedHostMiddleware
from fastapi.responses import JSONResponse

# Add project root to path for imports
sys.path.append(str(Path(__file__).parent.parent))

from config.config import get_settings
from utils.logging_config import setup_logging, get_logger
from utils.exceptions import SRCGeneratorException

from .api.routes import health, documents, agents, projects
from .core.exceptions import ValidationError, NotFoundError


# Setup logging before creating the app
setup_logging()
logger = get_logger(__name__)


@asynccontextmanager
async def lifespan(app: FastAPI):
    """
    Application lifespan manager for startup and shutdown events.
    """
    # Startup
    logger.info("Starting SRC Generator API server")
    settings = get_settings()
    logger.info(
        "Server configuration loaded",
        environment=settings.environment,
        host=settings.api.host,
        port=settings.api.port
    )
    
    # TODO: Initialize database connections
    # TODO: Initialize agent registry
    # TODO: Setup MCP servers
    
    yield
    
    # Shutdown
    logger.info("Shutting down SRC Generator API server")
    # TODO: Cleanup resources


def create_app() -> FastAPI:
    """
    Create and configure the FastAPI application.
    
    Returns:
        Configured FastAPI application instance
    """
    settings = get_settings()
    
    # Create FastAPI app with custom configuration
    app = FastAPI(
        title="SRC to Application Generator API",
        description="A sophisticated multi-agent system that transforms Software Requirements Specification (SRC) documents into fully functional Angular + FastAPI applications.",
        version="1.0.0",
        openapi_url="/api/v1/openapi.json",
        docs_url="/docs",
        redoc_url="/redoc",
        lifespan=lifespan
    )
    
    # Add middleware
    _add_middleware(app)
    
    # Add exception handlers
    _add_exception_handlers(app)
    
    # Include routers
    _include_routers(app)
    
    logger.info("FastAPI application created and configured")
    return app


def _add_middleware(app: FastAPI) -> None:
    """Add middleware to the FastAPI application."""
    settings = get_settings()
    
    # CORS middleware
    app.add_middleware(
        CORSMiddleware,
        allow_origins=["*"] if settings.is_development else ["http://localhost:8501"],
        allow_credentials=True,
        allow_methods=["*"],
        allow_headers=["*"],
    )
    
    # Trusted host middleware
    if settings.is_production:
        app.add_middleware(
            TrustedHostMiddleware,
            allowed_hosts=["localhost", "127.0.0.1", settings.api.host]
        )
    
    logger.info("Middleware configured")


def _add_exception_handlers(app: FastAPI) -> None:
    """Add custom exception handlers to the FastAPI application."""
    
    @app.exception_handler(SRCGeneratorException)
    async def src_generator_exception_handler(request, exc: SRCGeneratorException):
        """Handle custom SRC Generator exceptions."""
        logger.error(
            "SRC Generator exception occurred",
            exception_type=type(exc).__name__,
            message=exc.message,
            details=exc.details
        )
        
        return JSONResponse(
            status_code=400,
            content={
                "error": type(exc).__name__,
                "message": exc.message,
                "details": exc.details
            }
        )
    
    @app.exception_handler(ValidationError)
    async def validation_exception_handler(request, exc: ValidationError):
        """Handle validation errors."""
        logger.warning(
            "Validation error occurred",
            errors=exc.errors
        )
        
        return JSONResponse(
            status_code=422,
            content={
                "error": "ValidationError",
                "message": "Validation failed",
                "errors": exc.errors
            }
        )
    
    @app.exception_handler(NotFoundError)
    async def not_found_exception_handler(request, exc: NotFoundError):
        """Handle not found errors."""
        return JSONResponse(
            status_code=404,
            content={
                "error": "NotFoundError",
                "message": str(exc)
            }
        )
    
    @app.exception_handler(Exception)
    async def general_exception_handler(request, exc: Exception):
        """Handle unexpected exceptions."""
        logger.error(
            "Unexpected exception occurred",
            exception_type=type(exc).__name__,
            message=str(exc),
            path=request.url.path
        )
        
        return JSONResponse(
            status_code=500,
            content={
                "error": "InternalServerError",
                "message": "An unexpected error occurred"
            }
        )
    
    logger.info("Exception handlers configured")


def _include_routers(app: FastAPI) -> None:
    """Include all route modules in the FastAPI application."""
    
    # API v1 prefix
    api_v1_prefix = "/api/v1"
    
    # Include routers
    app.include_router(
        health.router,
        prefix=api_v1_prefix,
        tags=["Health"]
    )
    
    app.include_router(
        documents.router,
        prefix=api_v1_prefix,
        tags=["Documents"]
    )
    
    app.include_router(
        agents.router,
        prefix=api_v1_prefix,
        tags=["Agents"]
    )
    
    app.include_router(
        projects.router,
        prefix=api_v1_prefix,
        tags=["Projects"]
    )
    
    logger.info("API routes configured")


# Create the application instance
app = create_app()


# Root endpoint
@app.get("/")
async def root():
    """Root endpoint with basic API information."""
    return {
        "name": "SRC to Application Generator API",
        "version": "1.0.0",
        "status": "running",
        "docs": "/docs",
        "health": "/api/v1/health"
    }


if __name__ == "__main__":
    import uvicorn
    
    settings = get_settings()
    
    uvicorn.run(
        "main:app",
        host=settings.api.host,
        port=settings.api.port,
        reload=settings.api.reload,
        log_level=settings.logging.level.lower()
    )