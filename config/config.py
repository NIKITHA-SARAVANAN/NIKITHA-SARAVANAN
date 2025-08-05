"""
Configuration management module for the SRC to Application Generator.

This module handles all environment variables and configuration settings
across development and production environments.
"""

import os
from pathlib import Path
from typing import List, Optional

from pydantic import BaseSettings, Field
from dotenv import load_dotenv


# Load environment variables from .env file
BASE_DIR = Path(__file__).parent.parent
ENV_FILE = BASE_DIR / "config" / ".env"

if ENV_FILE.exists():
    load_dotenv(ENV_FILE)


class DatabaseSettings(BaseSettings):
    """Database configuration settings."""
    
    url: str = Field(default="sqlite:///./src_generator.db", env="DATABASE_URL")
    echo: bool = Field(default=False, env="DATABASE_ECHO")
    
    class Config:
        env_prefix = "DATABASE_"


class APISettings(BaseSettings):
    """API server configuration settings."""
    
    host: str = Field(default="0.0.0.0", env="API_HOST")
    port: int = Field(default=8000, env="API_PORT")
    reload: bool = Field(default=True, env="API_RELOAD")
    workers: int = Field(default=1, env="WORKER_PROCESSES")
    max_concurrent_requests: int = Field(default=10, env="MAX_CONCURRENT_REQUESTS")
    timeout_seconds: int = Field(default=60, env="REQUEST_TIMEOUT_SECONDS")
    
    class Config:
        env_prefix = "API_"


class StreamlitSettings(BaseSettings):
    """Streamlit configuration settings."""
    
    host: str = Field(default="0.0.0.0", env="STREAMLIT_HOST")
    port: int = Field(default=8501, env="STREAMLIT_PORT")
    
    class Config:
        env_prefix = "STREAMLIT_"


class LLMSettings(BaseSettings):
    """LLM provider configuration settings."""
    
    openai_api_key: Optional[str] = Field(default=None, env="OPENAI_API_KEY")
    anthropic_api_key: Optional[str] = Field(default=None, env="ANTHROPIC_API_KEY")
    default_provider: str = Field(default="openai", env="DEFAULT_LLM_PROVIDER")
    default_model: str = Field(default="gpt-4-turbo-preview", env="DEFAULT_MODEL")
    
    class Config:
        env_prefix = "LLM_"


class LangSmithSettings(BaseSettings):
    """LangSmith observability configuration."""
    
    tracing_enabled: bool = Field(default=True, env="LANGCHAIN_TRACING_V2")
    endpoint: str = Field(default="https://api.smith.langchain.com", env="LANGCHAIN_ENDPOINT")
    api_key: Optional[str] = Field(default=None, env="LANGCHAIN_API_KEY")
    project: str = Field(default="src-generator", env="LANGCHAIN_PROJECT")
    
    class Config:
        env_prefix = "LANGCHAIN_"


class SecuritySettings(BaseSettings):
    """Security and authentication settings."""
    
    secret_key: str = Field(default="dev-secret-key-change-in-production", env="SECRET_KEY")
    algorithm: str = Field(default="HS256", env="ALGORITHM")
    access_token_expire_minutes: int = Field(default=30, env="ACCESS_TOKEN_EXPIRE_MINUTES")
    
    class Config:
        env_prefix = "SECURITY_"


class FileUploadSettings(BaseSettings):
    """File upload configuration settings."""
    
    max_file_size_mb: int = Field(default=50, env="MAX_FILE_SIZE_MB")
    allowed_extensions: List[str] = Field(
        default=["pdf", "docx", "md", "txt"], 
        env="ALLOWED_EXTENSIONS"
    )
    
    @property
    def max_file_size_bytes(self) -> int:
        """Convert MB to bytes."""
        return self.max_file_size_mb * 1024 * 1024
    
    def __init__(self, **kwargs):
        super().__init__(**kwargs)
        # Handle comma-separated string from env
        if isinstance(self.allowed_extensions, str):
            self.allowed_extensions = [ext.strip() for ext in self.allowed_extensions.split(",")]
    
    class Config:
        env_prefix = "FILE_"


class LoggingSettings(BaseSettings):
    """Logging configuration settings."""
    
    level: str = Field(default="INFO", env="LOG_LEVEL")
    format: str = Field(default="structured", env="LOG_FORMAT")
    file_max_size_mb: int = Field(default=100, env="LOG_FILE_MAX_SIZE_MB")
    file_backup_count: int = Field(default=5, env="LOG_FILE_BACKUP_COUNT")
    
    class Config:
        env_prefix = "LOG_"


class AgentSettings(BaseSettings):
    """Agent workflow configuration settings."""
    
    max_iterations: int = Field(default=10, env="MAX_AGENT_ITERATIONS")
    timeout_seconds: int = Field(default=300, env="AGENT_TIMEOUT_SECONDS")
    enable_human_loop: bool = Field(default=True, env="ENABLE_HUMAN_LOOP")
    
    class Config:
        env_prefix = "AGENT_"


class MCPSettings(BaseSettings):
    """MCP (Model Context Protocol) configuration settings."""
    
    server_port: int = Field(default=3000, env="MCP_SERVER_PORT")
    log_level: str = Field(default="DEBUG", env="MCP_LOG_LEVEL")
    
    class Config:
        env_prefix = "MCP_"


class CodeGenerationSettings(BaseSettings):
    """Code generation configuration settings."""
    
    output_dir: Path = Field(default=BASE_DIR / "output", env="OUTPUT_DIR")
    temp_dir: Path = Field(default=BASE_DIR / "temp", env="TEMP_DIR")
    enable_validation: bool = Field(default=True, env="ENABLE_CODE_VALIDATION")
    enable_security_scan: bool = Field(default=True, env="ENABLE_SECURITY_SCAN")
    
    def __init__(self, **kwargs):
        super().__init__(**kwargs)
        # Ensure directories exist
        self.output_dir.mkdir(parents=True, exist_ok=True)
        self.temp_dir.mkdir(parents=True, exist_ok=True)
    
    class Config:
        env_prefix = "CODE_"


class Settings(BaseSettings):
    """Main application settings combining all configuration sections."""
    
    environment: str = Field(default="development", env="ENVIRONMENT")
    
    # Sub-configurations
    database: DatabaseSettings = DatabaseSettings()
    api: APISettings = APISettings()
    streamlit: StreamlitSettings = StreamlitSettings()
    llm: LLMSettings = LLMSettings()
    langsmith: LangSmithSettings = LangSmithSettings()
    security: SecuritySettings = SecuritySettings()
    file_upload: FileUploadSettings = FileUploadSettings()
    logging: LoggingSettings = LoggingSettings()
    agent: AgentSettings = AgentSettings()
    mcp: MCPSettings = MCPSettings()
    code_generation: CodeGenerationSettings = CodeGenerationSettings()
    
    @property
    def is_development(self) -> bool:
        """Check if running in development environment."""
        return self.environment.lower() == "development"
    
    @property
    def is_production(self) -> bool:
        """Check if running in production environment."""
        return self.environment.lower() == "production"
    
    class Config:
        case_sensitive = False
        env_file = ".env"
        env_file_encoding = "utf-8"


# Global settings instance
settings = Settings()


def get_settings() -> Settings:
    """Get application settings instance."""
    return settings


def reload_settings() -> Settings:
    """Reload settings from environment variables."""
    global settings
    settings = Settings()
    return settings