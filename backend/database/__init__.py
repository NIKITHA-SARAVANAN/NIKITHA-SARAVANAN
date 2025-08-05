"""
Database package for the SRS to Angular+FastAPI generator.

This package contains database connection management, session handling,
and database utilities.
"""

from .connection import (
    engine,
    SessionLocal,
    get_database,
    init_db,
    close_db,
    get_db_status
)

__all__ = [
    "engine",
    "SessionLocal", 
    "get_database",
    "init_db",
    "close_db",
    "get_db_status"
]