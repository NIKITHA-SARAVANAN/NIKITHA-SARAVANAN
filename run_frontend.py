#!/usr/bin/env python3
"""
Script to run the Streamlit frontend application.

This script starts the Streamlit web interface with proper configuration.
"""

import sys
import subprocess
from pathlib import Path

# Add project root to path
project_root = Path(__file__).parent
sys.path.append(str(project_root))

from config.config import get_settings


def main():
    """Run the Streamlit frontend application."""
    # Get settings
    settings = get_settings()
    
    print(f"🎨 Starting SRC Generator Frontend")
    print(f"📍 Environment: {settings.environment}")
    print(f"🌐 Host: {settings.streamlit.host}")
    print(f"🔌 Port: {settings.streamlit.port}")
    print(f"🖥️  UI: http://{settings.streamlit.host}:{settings.streamlit.port}")
    
    # Streamlit command
    cmd = [
        "streamlit", "run",
        "frontend/app.py",
        "--server.address", settings.streamlit.host,
        "--server.port", str(settings.streamlit.port),
        "--browser.gatherUsageStats", "false",
        "--theme.base", "light"
    ]
    
    # Run Streamlit
    try:
        subprocess.run(cmd, check=True)
    except subprocess.CalledProcessError as e:
        print(f"❌ Failed to start Streamlit: {e}")
        sys.exit(1)
    except KeyboardInterrupt:
        print("\n👋 Shutting down Streamlit frontend...")
        sys.exit(0)


if __name__ == "__main__":
    main()