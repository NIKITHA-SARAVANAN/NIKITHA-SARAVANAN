"""
Main FastAPI application for the SRS to Angular+FastAPI generator.

This module sets up the FastAPI application with all necessary middleware,
exception handlers, and route configurations.
"""

import asyncio
import uvicorn
from contextlib import asynccontextmanager
from fastapi import FastAPI, HTTPException, Request, UploadFile, File, Form
from fastapi.middleware.cors import CORSMiddleware
from fastapi.middleware.gzip import GZipMiddleware
from fastapi.exception_handlers import http_exception_handler
from fastapi.responses import JSONResponse
from fastapi.staticfiles import StaticFiles
import logging
import sys
import os

# Add project root to path
sys.path.append(os.path.dirname(os.path.dirname(os.path.abspath(__file__))))

from config.config import settings, setup_logging
from utils.logger import setup_structured_logging, get_logger
from utils.exceptions import SRSGeneratorError, handle_exception
from backend.api.routes import health, documents, workflow, agents
from backend.database import init_db, close_db
from backend.models.database import create_tables

logger = get_logger(__name__)


@asynccontextmanager
async def lifespan(app: FastAPI):
    """
    Application lifespan manager.
    
    Handles startup and shutdown tasks including database initialization,
    logging setup, and cleanup.
    """
    # Startup
    logger.info("Starting SRS Generator application")
    
    try:
        # Setup logging
        setup_structured_logging()
        
        # Initialize database
        await init_db()
        await create_tables()
        
        # Create required directories
        os.makedirs(settings.upload_dir, exist_ok=True)
        os.makedirs(settings.output_dir, exist_ok=True)
        
        logger.info("Application startup completed successfully")
        
        yield
        
    except Exception as e:
        logger.error(f"Application startup failed: {e}")
        raise
    
    finally:
        # Shutdown
        logger.info("Shutting down SRS Generator application")
        
        try:
            # Close database connections
            await close_db()
            
            logger.info("Application shutdown completed successfully")
            
        except Exception as e:
            logger.error(f"Error during application shutdown: {e}")


def create_app() -> FastAPI:
    """
    Create and configure the FastAPI application.
    
    Returns:
        FastAPI: Configured application instance
    """
    app = FastAPI(
        title="SRS to Angular+FastAPI Generator",
        description=(
            "A sophisticated multi-agent system that transforms Software Requirements "
            "Specification (SRS) documents into fully functional Angular + FastAPI applications."
        ),
        version="1.0.0",
        docs_url="/docs",
        redoc_url="/redoc",
        openapi_url="/openapi.json",
        lifespan=lifespan,
        debug=settings.debug
    )
    
    # Add middleware
    setup_middleware(app)
    
    # Add exception handlers
    setup_exception_handlers(app)
    
    # Include API routes
    setup_routes(app)
    
    return app


def setup_middleware(app: FastAPI) -> None:
    """
    Setup application middleware.
    
    Args:
        app: FastAPI application instance
    """
    # CORS middleware
    app.add_middleware(
        CORSMiddleware,
        allow_origins=["http://localhost:8501", "http://127.0.0.1:8501"],  # Streamlit frontend
        allow_credentials=True,
        allow_methods=["GET", "POST", "PUT", "DELETE"],
        allow_headers=["*"],
    )
    
    # GZip compression middleware
    app.add_middleware(GZipMiddleware, minimum_size=1000)
    
    # Request logging middleware
    @app.middleware("http")
    async def log_requests(request: Request, call_next):
        """Log all HTTP requests."""
        start_time = asyncio.get_event_loop().time()
        
        # Log request
        logger.info(
            f"Request: {request.method} {request.url.path}",
            method=request.method,
            path=request.url.path,
            query_params=str(request.query_params),
            client_host=request.client.host if request.client else None
        )
        
        # Process request
        response = await call_next(request)
        
        # Calculate duration
        process_time = asyncio.get_event_loop().time() - start_time
        
        # Log response
        logger.info(
            f"Response: {response.status_code}",
            method=request.method,
            path=request.url.path,
            status_code=response.status_code,
            process_time=process_time
        )
        
        # Add process time header
        response.headers["X-Process-Time"] = str(process_time)
        
        return response


def setup_exception_handlers(app: FastAPI) -> None:
    """
    Setup custom exception handlers.
    
    Args:
        app: FastAPI application instance
    """
    @app.exception_handler(SRSGeneratorError)
    async def srs_exception_handler(request: Request, exc: SRSGeneratorError):
        """Handle custom SRS Generator exceptions."""
        logger.error(
            f"SRS Generator error: {exc.message}",
            error_code=exc.error_code,
            details=exc.details,
            path=request.url.path
        )
        
        return JSONResponse(
            status_code=400,
            content=exc.to_dict()
        )
    
    @app.exception_handler(HTTPException)
    async def custom_http_exception_handler(request: Request, exc: HTTPException):
        """Handle HTTP exceptions with structured logging."""
        logger.warning(
            f"HTTP exception: {exc.detail}",
            status_code=exc.status_code,
            path=request.url.path
        )
        
        return await http_exception_handler(request, exc)
    
    @app.exception_handler(Exception)
    async def general_exception_handler(request: Request, exc: Exception):
        """Handle unexpected exceptions."""
        logger.error(
            f"Unhandled exception: {str(exc)}",
            exception_type=type(exc).__name__,
            path=request.url.path
        )
        
        if settings.debug:
            # In debug mode, include the full traceback
            import traceback
            return JSONResponse(
                status_code=500,
                content={
                    "error": "INTERNAL_SERVER_ERROR",
                    "message": str(exc),
                    "traceback": traceback.format_exc()
                }
            )
        else:
            # In production, return a generic error message
            return JSONResponse(
                status_code=500,
                content={
                    "error": "INTERNAL_SERVER_ERROR",
                    "message": "An unexpected error occurred"
                }
            )


def setup_routes(app: FastAPI) -> None:
    """
    Setup API routes.
    
    Args:
        app: FastAPI application instance
    """
    # Include API routers
    app.include_router(health.router, tags=["Health"])
    app.include_router(documents.router, prefix="/api/v1/documents", tags=["Documents"])
    app.include_router(workflow.router, prefix="/api/v1/workflow", tags=["Workflow"])
    app.include_router(agents.router, prefix="/api/v1/agents", tags=["Agents"])
    
    # Serve static files (for generated code, logs, etc.)
    if os.path.exists("static"):
        app.mount("/static", StaticFiles(directory="static"), name="static")


# Create the application instance
app = create_app()


def run_server():
    """
    Run the FastAPI server.
    
    This function is called when the module is executed directly.
    """
    logger.info(f"Starting server on {settings.backend_host}:{settings.backend_port}")
    
    uvicorn.run(
        "backend.main:app",
        host=settings.backend_host,
        port=settings.backend_port,
        reload=settings.debug,
        log_level=settings.log_level.lower(),
        workers=settings.worker_processes if not settings.debug else 1,
        access_log=True
    )


if __name__ == "__main__":
    run_server()