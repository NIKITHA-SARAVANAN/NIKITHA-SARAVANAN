"""
Configuration management for the SRS to Angular+FastAPI generator.

This module provides centralized configuration management using environment variables
and supports different environments (development, production, testing).
"""

import os
import logging
from typing import Optional, List
from pathlib import Path
from pydantic import BaseSettings, validator, Field
from enum import Enum


class Environment(str, Enum):
    """Supported environment types."""
    DEVELOPMENT = "development"
    PRODUCTION = "production"
    TESTING = "testing"


class LLMProvider(str, Enum):
    """Supported LLM providers."""
    OPENAI = "openai"
    ANTHROPIC = "anthropic"
    AZURE_OPENAI = "azure_openai"


class LogLevel(str, Enum):
    """Supported log levels."""
    DEBUG = "DEBUG"
    INFO = "INFO"
    WARNING = "WARNING"
    ERROR = "ERROR"
    CRITICAL = "CRITICAL"


class LogFormat(str, Enum):
    """Supported log formats."""
    JSON = "json"
    TEXT = "text"


class Settings(BaseSettings):
    """Application settings with environment variable support."""
    
    # Environment Configuration
    environment: Environment = Field(default=Environment.DEVELOPMENT, env="ENVIRONMENT")
    debug: bool = Field(default=True, env="DEBUG")
    
    # Database Configuration
    database_url: str = Field(..., env="DATABASE_URL")
    redis_url: str = Field(default="redis://localhost:6379", env="REDIS_URL")
    database_echo: bool = Field(default=False, env="DATABASE_ECHO")
    
    # LLM Configuration
    openai_api_key: Optional[str] = Field(default=None, env="OPENAI_API_KEY")
    anthropic_api_key: Optional[str] = Field(default=None, env="ANTHROPIC_API_KEY")
    llm_provider: LLMProvider = Field(default=LLMProvider.OPENAI, env="LLM_PROVIDER")
    llm_model: str = Field(default="gpt-4-turbo-preview", env="LLM_MODEL")
    llm_temperature: float = Field(default=0.2, env="LLM_TEMPERATURE")
    max_tokens: int = Field(default=4000, env="MAX_TOKENS")
    
    # Agent Configuration
    max_agent_retries: int = Field(default=3, env="MAX_AGENT_RETRIES")
    human_approval_timeout: int = Field(default=300, env="HUMAN_APPROVAL_TIMEOUT")
    enable_auto_rollback: bool = Field(default=True, env="ENABLE_AUTO_ROLLBACK")
    agent_execution_timeout: int = Field(default=600, env="AGENT_EXECUTION_TIMEOUT")
    max_concurrent_agents: int = Field(default=3, env="MAX_CONCURRENT_AGENTS")
    
    # Logging Configuration
    log_level: LogLevel = Field(default=LogLevel.INFO, env="LOG_LEVEL")
    log_format: LogFormat = Field(default=LogFormat.JSON, env="LOG_FORMAT")
    langsmith_api_key: Optional[str] = Field(default=None, env="LANGSMITH_API_KEY")
    langsmith_project: str = Field(default="srs-generator", env="LANGSMITH_PROJECT")
    
    # Server Configuration
    backend_host: str = Field(default="0.0.0.0", env="BACKEND_HOST")
    backend_port: int = Field(default=8000, env="BACKEND_PORT")
    frontend_host: str = Field(default="localhost", env="FRONTEND_HOST")
    frontend_port: int = Field(default=8501, env="FRONTEND_PORT")
    
    # File Upload Configuration
    max_file_size_mb: int = Field(default=50, env="MAX_FILE_SIZE_MB")
    allowed_file_types: List[str] = Field(
        default=["pdf", "docx", "md", "txt"], 
        env="ALLOWED_FILE_TYPES"
    )
    upload_dir: str = Field(default="uploads/", env="UPLOAD_DIR")
    
    # Security Configuration
    secret_key: str = Field(..., env="SECRET_KEY")
    access_token_expire_minutes: int = Field(default=30, env="ACCESS_TOKEN_EXPIRE_MINUTES")
    algorithm: str = Field(default="HS256", env="ALGORITHM")
    
    # MCP Server Configuration
    mcp_file_server_port: int = Field(default=3001, env="MCP_FILE_SERVER_PORT")
    mcp_search_server_port: int = Field(default=3002, env="MCP_SEARCH_SERVER_PORT")
    mcp_validation_server_port: int = Field(default=3003, env="MCP_VALIDATION_SERVER_PORT")
    
    # Code Generation Configuration
    output_dir: str = Field(default="output/", env="OUTPUT_DIR")
    backup_enabled: bool = Field(default=True, env="BACKUP_ENABLED")
    git_auto_commit: bool = Field(default=False, env="GIT_AUTO_COMMIT")
    docker_export: bool = Field(default=False, env="DOCKER_EXPORT")
    
    # Performance Configuration
    worker_processes: int = Field(default=1, env="WORKER_PROCESSES")
    worker_connections: int = Field(default=1000, env="WORKER_CONNECTIONS")
    keep_alive_timeout: int = Field(default=5, env="KEEP_ALIVE_TIMEOUT")
    
    class Config:
        """Pydantic configuration."""
        env_file = ".env"
        env_file_encoding = "utf-8"
        case_sensitive = False
    
    @validator("allowed_file_types", pre=True)
    def parse_file_types(cls, v):
        """Parse comma-separated file types."""
        if isinstance(v, str):
            return [item.strip() for item in v.split(",")]
        return v
    
    @validator("max_file_size_mb")
    def validate_file_size(cls, v):
        """Validate file size is reasonable."""
        if v <= 0:
            raise ValueError("max_file_size_mb must be positive")
        if v > 500:  # 500MB max
            raise ValueError("max_file_size_mb cannot exceed 500MB")
        return v
    
    @validator("llm_temperature")
    def validate_temperature(cls, v):
        """Validate LLM temperature is in valid range."""
        if not 0.0 <= v <= 2.0:
            raise ValueError("llm_temperature must be between 0.0 and 2.0")
        return v
    
    @validator("max_tokens")
    def validate_max_tokens(cls, v):
        """Validate max tokens is reasonable."""
        if v <= 0:
            raise ValueError("max_tokens must be positive")
        if v > 100000:  # Reasonable upper limit
            raise ValueError("max_tokens cannot exceed 100,000")
        return v
    
    @property
    def is_development(self) -> bool:
        """Check if running in development mode."""
        return self.environment == Environment.DEVELOPMENT
    
    @property
    def is_production(self) -> bool:
        """Check if running in production mode."""
        return self.environment == Environment.PRODUCTION
    
    @property
    def is_testing(self) -> bool:
        """Check if running in testing mode."""
        return self.environment == Environment.TESTING
    
    @property
    def max_file_size_bytes(self) -> int:
        """Get max file size in bytes."""
        return self.max_file_size_mb * 1024 * 1024
    
    @property
    def log_config(self) -> dict:
        """Get logging configuration dictionary."""
        return {
            "version": 1,
            "disable_existing_loggers": False,
            "formatters": {
                "json": {
                    "format": '{"timestamp": "%(asctime)s", "level": "%(levelname)s", "logger": "%(name)s", "message": "%(message)s"}',
                    "datefmt": "%Y-%m-%d %H:%M:%S"
                },
                "text": {
                    "format": "%(asctime)s - %(name)s - %(levelname)s - %(message)s",
                    "datefmt": "%Y-%m-%d %H:%M:%S"
                }
            },
            "handlers": {
                "console": {
                    "class": "logging.StreamHandler",
                    "formatter": self.log_format.value,
                    "level": self.log_level.value
                },
                "file": {
                    "class": "logging.handlers.RotatingFileHandler",
                    "filename": "logs/app.log",
                    "maxBytes": 10485760,  # 10MB
                    "backupCount": 5,
                    "formatter": self.log_format.value,
                    "level": self.log_level.value
                }
            },
            "root": {
                "level": self.log_level.value,
                "handlers": ["console", "file"]
            }
        }


def get_settings() -> Settings:
    """
    Get application settings instance.
    
    This function loads settings from environment variables and .env file.
    It also ensures required directories exist.
    
    Returns:
        Settings: Configured settings instance
    """
    # Ensure config directory exists and .env file is loaded from the right location
    config_dir = Path(__file__).parent
    env_file = config_dir / ".env"
    
    if env_file.exists():
        from dotenv import load_dotenv
        load_dotenv(env_file)
    
    settings = Settings()
    
    # Ensure required directories exist
    os.makedirs("logs", exist_ok=True)
    os.makedirs(settings.upload_dir, exist_ok=True)
    os.makedirs(settings.output_dir, exist_ok=True)
    
    return settings


def setup_logging(settings: Settings) -> None:
    """
    Setup application logging based on configuration.
    
    Args:
        settings: Application settings
    """
    import logging.config
    
    # Ensure logs directory exists
    os.makedirs("logs", exist_ok=True)
    
    # Configure logging
    logging.config.dictConfig(settings.log_config)
    
    # Log startup information
    logger = logging.getLogger(__name__)
    logger.info(f"Application starting in {settings.environment} mode")
    logger.info(f"Log level set to {settings.log_level}")
    logger.info(f"LLM provider: {settings.llm_provider}")


# Global settings instance
settings = get_settings()


class DatabaseConfig:
    """Database-specific configuration utilities."""
    
    @staticmethod
    def get_database_url(settings: Settings) -> str:
        """Get the database URL for the current environment."""
        return settings.database_url
    
    @staticmethod
    def get_redis_url(settings: Settings) -> str:
        """Get the Redis URL for the current environment."""
        return settings.redis_url


class AgentConfig:
    """Agent-specific configuration utilities."""
    
    @staticmethod
    def get_llm_config(settings: Settings) -> dict:
        """Get LLM configuration for agents."""
        config = {
            "provider": settings.llm_provider,
            "model": settings.llm_model,
            "temperature": settings.llm_temperature,
            "max_tokens": settings.max_tokens,
        }
        
        if settings.llm_provider == LLMProvider.OPENAI:
            config["api_key"] = settings.openai_api_key
        elif settings.llm_provider == LLMProvider.ANTHROPIC:
            config["api_key"] = settings.anthropic_api_key
        
        return config
    
    @staticmethod
    def get_agent_timeouts(settings: Settings) -> dict:
        """Get timeout configurations for agents."""
        return {
            "execution_timeout": settings.agent_execution_timeout,
            "human_approval_timeout": settings.human_approval_timeout,
            "max_retries": settings.max_agent_retries,
        }


# Export commonly used instances
__all__ = [
    "Settings",
    "Environment", 
    "LLMProvider",
    "LogLevel",
    "LogFormat",
    "get_settings",
    "setup_logging",
    "settings",
    "DatabaseConfig",
    "AgentConfig"
]