"""
Tests for configuration management module.

Tests the configuration loading, validation, and environment handling.
"""

import pytest
import os
from pathlib import Path

from config.config import Settings, get_settings, reload_settings


class TestSettings:
    """Test the Settings configuration class."""
    
    def test_default_settings(self):
        """Test that default settings are loaded correctly."""
        settings = Settings()
        
        assert settings.environment == "development"
        assert settings.api.host == "0.0.0.0"
        assert settings.api.port == 8000
        assert settings.logging.level == "INFO"
        assert settings.file_upload.max_file_size_mb == 50
    
    def test_environment_detection(self):
        """Test environment detection methods."""
        settings = Settings()
        
        # Test development environment
        assert settings.is_development is True
        assert settings.is_production is False
        
        # Test production environment
        settings.environment = "production"
        assert settings.is_development is False
        assert settings.is_production is True
    
    def test_file_upload_settings(self):
        """Test file upload configuration."""
        settings = Settings()
        
        assert settings.file_upload.max_file_size_mb == 50
        assert settings.file_upload.max_file_size_bytes == 50 * 1024 * 1024
        assert "pdf" in settings.file_upload.allowed_extensions
        assert "docx" in settings.file_upload.allowed_extensions
    
    def test_code_generation_paths(self):
        """Test code generation path configuration."""
        settings = Settings()
        
        assert settings.code_generation.output_dir.exists()
        assert settings.code_generation.temp_dir.exists()
        assert settings.code_generation.enable_validation is True


class TestGlobalSettings:
    """Test global settings functions."""
    
    def test_get_settings(self):
        """Test get_settings function."""
        settings = get_settings()
        assert isinstance(settings, Settings)
        
        # Test that it returns the same instance
        settings2 = get_settings()
        assert settings is settings2
    
    def test_reload_settings(self):
        """Test reload_settings function."""
        original_settings = get_settings()
        reloaded_settings = reload_settings()
        
        assert isinstance(reloaded_settings, Settings)
        # Should be a new instance after reload
        assert original_settings is not reloaded_settings


@pytest.fixture
def temp_env_var():
    """Fixture to temporarily set environment variables."""
    original_value = os.environ.get("ENVIRONMENT")
    yield
    if original_value is not None:
        os.environ["ENVIRONMENT"] = original_value
    elif "ENVIRONMENT" in os.environ:
        del os.environ["ENVIRONMENT"]


def test_environment_variable_override(temp_env_var):
    """Test that environment variables override defaults."""
    os.environ["ENVIRONMENT"] = "production"
    os.environ["API_PORT"] = "9000"
    
    settings = Settings()
    
    assert settings.environment == "production"
    assert settings.api.port == 9000