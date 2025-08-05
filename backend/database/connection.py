"""
Database connection and session management.

This module handles PostgreSQL database connections, session management,
and provides database utilities for the application.
"""

import asyncio
from typing import AsyncGenerator, Optional
from sqlalchemy import create_engine, text
from sqlalchemy.ext.asyncio import create_async_engine, AsyncSession, async_sessionmaker
from sqlalchemy.orm import sessionmaker, Session
from sqlalchemy.pool import QueuePool
import sys
import os

# Add project root to path
sys.path.append(os.path.dirname(os.path.dirname(os.path.dirname(os.path.abspath(__file__)))))

from config.config import settings, DatabaseConfig
from utils.logger import get_logger
from utils.exceptions import DatabaseError

logger = get_logger(__name__)

# Database engines - both sync and async
engine: Optional[create_engine] = None
async_engine: Optional[create_async_engine] = None

# Session makers
SessionLocal: Optional[sessionmaker] = None
AsyncSessionLocal: Optional[async_sessionmaker] = None

# Connection status
_db_initialized = False
_connection_pool_size = 5
_max_overflow = 10


def create_database_engines():
    """
    Create database engines for both synchronous and asynchronous operations.
    
    Returns:
        Tuple of (sync_engine, async_engine)
    """
    global engine, async_engine
    
    try:
        # Get database configuration
        database_url = DatabaseConfig.get_database_url(settings)
        
        # Create synchronous engine
        engine = create_engine(
            database_url,
            poolclass=QueuePool,
            pool_size=_connection_pool_size,
            max_overflow=_max_overflow,
            pool_pre_ping=True,  # Verify connections before use
            pool_recycle=3600,   # Recycle connections every hour
            echo=settings.database_echo,
            connect_args={
                "options": "-c timezone=UTC"  # Set timezone to UTC
            }
        )
        
        # Create asynchronous engine (replace postgresql with postgresql+asyncpg)
        async_database_url = database_url.replace("postgresql://", "postgresql+asyncpg://")
        async_engine = create_async_engine(
            async_database_url,
            poolclass=QueuePool,
            pool_size=_connection_pool_size,
            max_overflow=_max_overflow,
            pool_pre_ping=True,
            pool_recycle=3600,
            echo=settings.database_echo
        )
        
        logger.info("Database engines created successfully")
        return engine, async_engine
        
    except Exception as e:
        logger.error(f"Failed to create database engines: {e}")
        raise DatabaseError(f"Failed to create database engines: {e}")


def create_session_makers():
    """
    Create session makers for database operations.
    
    Returns:
        Tuple of (sync_session_maker, async_session_maker)
    """
    global SessionLocal, AsyncSessionLocal, engine, async_engine
    
    if not engine or not async_engine:
        raise DatabaseError("Database engines not initialized")
    
    try:
        # Create synchronous session maker
        SessionLocal = sessionmaker(
            bind=engine,
            autocommit=False,
            autoflush=False,
            expire_on_commit=False
        )
        
        # Create asynchronous session maker
        AsyncSessionLocal = async_sessionmaker(
            bind=async_engine,
            class_=AsyncSession,
            autocommit=False,
            autoflush=False,
            expire_on_commit=False
        )
        
        logger.info("Database session makers created successfully")
        return SessionLocal, AsyncSessionLocal
        
    except Exception as e:
        logger.error(f"Failed to create session makers: {e}")
        raise DatabaseError(f"Failed to create session makers: {e}")


async def init_db():
    """
    Initialize database connection and create session makers.
    
    This function should be called during application startup.
    """
    global _db_initialized
    
    try:
        logger.info("Initializing database connection...")
        
        # Create engines
        create_database_engines()
        
        # Create session makers
        create_session_makers()
        
        # Test database connectivity
        await test_database_connection()
        
        _db_initialized = True
        logger.info("Database initialization completed successfully")
        
    except Exception as e:
        logger.error(f"Database initialization failed: {e}")
        raise DatabaseError(f"Database initialization failed: {e}")


async def close_db():
    """
    Close database connections and clean up resources.
    
    This function should be called during application shutdown.
    """
    global engine, async_engine, _db_initialized
    
    try:
        logger.info("Closing database connections...")
        
        if async_engine:
            await async_engine.dispose()
            async_engine = None
        
        if engine:
            engine.dispose()
            engine = None
        
        _db_initialized = False
        logger.info("Database connections closed successfully")
        
    except Exception as e:
        logger.error(f"Error closing database connections: {e}")


async def test_database_connection():
    """
    Test database connectivity by executing a simple query.
    
    Raises:
        DatabaseError: If connection test fails
    """
    try:
        if not async_engine:
            raise DatabaseError("Async engine not initialized")
        
        async with async_engine.begin() as conn:
            result = await conn.execute(text("SELECT 1"))
            row = result.fetchone()
            
            if row and row[0] == 1:
                logger.info("Database connection test successful")
            else:
                raise DatabaseError("Database connection test returned unexpected result")
                
    except Exception as e:
        logger.error(f"Database connection test failed: {e}")
        raise DatabaseError(f"Database connection test failed: {e}")


async def get_db_status() -> bool:
    """
    Check database connection status.
    
    Returns:
        bool: True if database is connected and responsive, False otherwise
    """
    try:
        if not _db_initialized or not async_engine:
            return False
        
        async with async_engine.begin() as conn:
            await conn.execute(text("SELECT 1"))
            return True
            
    except Exception as e:
        logger.warning(f"Database status check failed: {e}")
        return False


def get_database() -> Session:
    """
    Dependency function to get a database session.
    
    This function is used as a FastAPI dependency to provide
    database sessions to route handlers.
    
    Yields:
        Session: SQLAlchemy database session
        
    Raises:
        DatabaseError: If session creation fails
    """
    if not SessionLocal:
        raise DatabaseError("Database not initialized")
    
    db = SessionLocal()
    try:
        yield db
    except Exception as e:
        logger.error(f"Database session error: {e}")
        db.rollback()
        raise DatabaseError(f"Database session error: {e}")
    finally:
        db.close()


async def get_async_database() -> AsyncGenerator[AsyncSession, None]:
    """
    Async dependency function to get a database session.
    
    This function provides async database sessions for
    asynchronous operations.
    
    Yields:
        AsyncSession: SQLAlchemy async database session
        
    Raises:
        DatabaseError: If session creation fails
    """
    if not AsyncSessionLocal:
        raise DatabaseError("Async database not initialized")
    
    async with AsyncSessionLocal() as session:
        try:
            yield session
        except Exception as e:
            logger.error(f"Async database session error: {e}")
            await session.rollback()
            raise DatabaseError(f"Async database session error: {e}")


class DatabaseManager:
    """
    Database manager class for advanced database operations.
    
    Provides utilities for connection management, health checks,
    and database maintenance operations.
    """
    
    def __init__(self):
        self.engine = engine
        self.async_engine = async_engine
    
    async def health_check(self) -> dict:
        """
        Perform a comprehensive database health check.
        
        Returns:
            dict: Health check results
        """
        health_info = {
            "connected": False,
            "response_time_ms": None,
            "pool_status": None,
            "active_connections": None,
            "errors": []
        }
        
        try:
            import time
            start_time = time.time()
            
            # Test connection
            if await get_db_status():
                health_info["connected"] = True
                health_info["response_time_ms"] = (time.time() - start_time) * 1000
            
            # Get pool status
            if engine:
                pool = engine.pool
                health_info["pool_status"] = {
                    "size": pool.size(),
                    "checked_in": pool.checkedin(),
                    "checked_out": pool.checkedout(),
                    "overflow": pool.overflow(),
                    "invalidated": pool.invalidated()
                }
                health_info["active_connections"] = pool.checkedout()
            
        except Exception as e:
            health_info["errors"].append(str(e))
            logger.error(f"Database health check failed: {e}")
        
        return health_info
    
    async def execute_query(self, query: str, params: dict = None) -> list:
        """
        Execute a raw SQL query safely.
        
        Args:
            query: SQL query string
            params: Query parameters
            
        Returns:
            list: Query results
        """
        try:
            if not async_engine:
                raise DatabaseError("Database not initialized")
            
            async with async_engine.begin() as conn:
                result = await conn.execute(text(query), params or {})
                return result.fetchall()
                
        except Exception as e:
            logger.error(f"Query execution failed: {e}")
            raise DatabaseError(f"Query execution failed: {e}")
    
    async def get_table_sizes(self) -> dict:
        """
        Get the size of all tables in the database.
        
        Returns:
            dict: Table sizes in bytes
        """
        try:
            query = """
            SELECT 
                schemaname,
                tablename,
                pg_total_relation_size(schemaname||'.'||tablename) as size
            FROM pg_tables 
            WHERE schemaname = 'public'
            ORDER BY size DESC;
            """
            
            results = await self.execute_query(query)
            
            table_sizes = {}
            for row in results:
                table_name = row[1]
                size_bytes = row[2]
                table_sizes[table_name] = size_bytes
            
            return table_sizes
            
        except Exception as e:
            logger.error(f"Failed to get table sizes: {e}")
            return {}
    
    async def vacuum_analyze(self) -> bool:
        """
        Perform VACUUM ANALYZE on the database for maintenance.
        
        Returns:
            bool: True if successful, False otherwise
        """
        try:
            if not engine:
                raise DatabaseError("Database not initialized")
            
            with engine.begin() as conn:
                conn.execute(text("VACUUM ANALYZE;"))
            
            logger.info("Database VACUUM ANALYZE completed successfully")
            return True
            
        except Exception as e:
            logger.error(f"VACUUM ANALYZE failed: {e}")
            return False


# Global database manager instance
db_manager = DatabaseManager()


# Database connection retry decorator
def retry_db_operation(max_retries: int = 3, delay: float = 1.0):
    """
    Decorator to retry database operations on failure.
    
    Args:
        max_retries: Maximum number of retry attempts
        delay: Delay between retries in seconds
    """
    def decorator(func):
        async def wrapper(*args, **kwargs):
            last_exception = None
            
            for attempt in range(max_retries + 1):
                try:
                    return await func(*args, **kwargs)
                except Exception as e:
                    last_exception = e
                    if attempt < max_retries:
                        logger.warning(f"Database operation failed (attempt {attempt + 1}/{max_retries + 1}): {e}")
                        await asyncio.sleep(delay * (2 ** attempt))  # Exponential backoff
                    else:
                        logger.error(f"Database operation failed after {max_retries + 1} attempts: {e}")
            
            raise last_exception
        
        return wrapper
    return decorator