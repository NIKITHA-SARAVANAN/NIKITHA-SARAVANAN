#!/usr/bin/env python3
"""
Script to run the FastAPI backend server.

This script starts the FastAPI application with proper configuration
and logging setup.
"""

import sys
from pathlib import Path

# Add project root to path
project_root = Path(__file__).parent
sys.path.append(str(project_root))

import uvicorn
from config.config import get_settings
from utils.logging_config import setup_logging


def main():
    """Run the FastAPI backend server."""
    # Setup logging
    setup_logging()
    
    # Get settings
    settings = get_settings()
    
    print(f"🚀 Starting SRC Generator API Server")
    print(f"📍 Environment: {settings.environment}")
    print(f"🌐 Host: {settings.api.host}")
    print(f"🔌 Port: {settings.api.port}")
    print(f"📖 Docs: http://{settings.api.host}:{settings.api.port}/docs")
    print(f"🔗 Health: http://{settings.api.host}:{settings.api.port}/api/v1/health")
    
    # Run the server
    uvicorn.run(
        "backend.main:app",
        host=settings.api.host,
        port=settings.api.port,
        reload=settings.api.reload,
        log_level=settings.logging.level.lower(),
        access_log=True
    )


if __name__ == "__main__":
    main()