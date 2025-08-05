"""
Main Streamlit application for the SRC to Application Generator.

This module provides a web interface for uploading documents,
monitoring agent workflows, and managing the application generation process.
"""

import sys
import time
from pathlib import Path
from typing import Dict, Any, Optional

import streamlit as st
import requests
import pandas as pd
from datetime import datetime

# Add project root to path for imports
sys.path.append(str(Path(__file__).parent.parent))

from config.config import get_settings


# Configuration
API_BASE_URL = "http://localhost:8000/api/v1"
POLL_INTERVAL = 2  # seconds


class APIClient:
    """Client for communicating with the FastAPI backend."""
    
    def __init__(self, base_url: str):
        self.base_url = base_url
    
    def health_check(self) -> Dict[str, Any]:
        """Check API health."""
        try:
            response = requests.get(f"{self.base_url}/health", timeout=5)
            response.raise_for_status()
            return response.json()
        except requests.RequestException as e:
            return {"status": "error", "error": str(e)}
    
    def upload_document(self, file_content: bytes, filename: str, description: str = "") -> Dict[str, Any]:
        """Upload a document to the API."""
        try:
            files = {"file": (filename, file_content)}
            data = {"description": description} if description else {}
            
            response = requests.post(
                f"{self.base_url}/documents/upload",
                files=files,
                data=data,
                timeout=30
            )
            response.raise_for_status()
            return response.json()
        except requests.RequestException as e:
            return {"error": str(e)}
    
    def parse_document(self, document_id: str) -> Dict[str, Any]:
        """Parse a document."""
        try:
            response = requests.post(
                f"{self.base_url}/documents/{document_id}/parse",
                timeout=60
            )
            response.raise_for_status()
            return response.json()
        except requests.RequestException as e:
            return {"error": str(e)}
    
    def get_document_status(self, document_id: str) -> Dict[str, Any]:
        """Get document processing status."""
        try:
            response = requests.get(
                f"{self.base_url}/documents/{document_id}/status",
                timeout=10
            )
            response.raise_for_status()
            return response.json()
        except requests.RequestException as e:
            return {"error": str(e)}
    
    def list_documents(self) -> Dict[str, Any]:
        """List all documents."""
        try:
            response = requests.get(f"{self.base_url}/documents", timeout=10)
            response.raise_for_status()
            return response.json()
        except requests.RequestException as e:
            return {"error": str(e)}
    
    def list_agents(self) -> Dict[str, Any]:
        """List all agents."""
        try:
            response = requests.get(f"{self.base_url}/agents", timeout=10)
            response.raise_for_status()
            return response.json()
        except requests.RequestException as e:
            return {"error": str(e)}
    
    def create_project(self, name: str, document_id: str, description: str = "") -> Dict[str, Any]:
        """Create a new project."""
        try:
            data = {
                "name": name,
                "document_id": document_id,
                "description": description
            }
            response = requests.post(
                f"{self.base_url}/projects",
                json=data,
                timeout=30
            )
            response.raise_for_status()
            return response.json()
        except requests.RequestException as e:
            return {"error": str(e)}
    
    def list_projects(self) -> Dict[str, Any]:
        """List all projects."""
        try:
            response = requests.get(f"{self.base_url}/projects", timeout=10)
            response.raise_for_status()
            return response.json()
        except requests.RequestException as e:
            return {"error": str(e)}


def init_session_state():
    """Initialize Streamlit session state variables."""
    if "api_client" not in st.session_state:
        st.session_state.api_client = APIClient(API_BASE_URL)
    
    if "uploaded_documents" not in st.session_state:
        st.session_state.uploaded_documents = {}
    
    if "current_document_id" not in st.session_state:
        st.session_state.current_document_id = None
    
    if "projects" not in st.session_state:
        st.session_state.projects = {}


def show_api_status():
    """Show API connection status."""
    with st.sidebar:
        st.subheader("🔗 API Status")
        
        health = st.session_state.api_client.health_check()
        
        if health.get("status") == "healthy":
            st.success("✅ API Connected")
            st.caption(f"Environment: {health.get('environment', 'unknown')}")
            st.caption(f"Uptime: {health.get('uptime_seconds', 0):.0f}s")
        elif health.get("status") == "degraded":
            st.warning("⚠️ API Degraded")
            st.caption("Some services may be unavailable")
        else:
            st.error("❌ API Disconnected")
            st.caption(f"Error: {health.get('error', 'Unknown error')}")


def upload_document_page():
    """Document upload page."""
    st.header("📄 Document Upload")
    st.write("Upload your Software Requirements Specification (SRC) document to begin the application generation process.")
    
    # File upload
    uploaded_file = st.file_uploader(
        "Choose your SRC document",
        type=["pdf", "docx", "md", "txt"],
        help="Supported formats: PDF, Word (DOCX), Markdown, and Text files"
    )
    
    # Document description
    description = st.text_area(
        "Document Description (Optional)",
        placeholder="Describe the purpose and context of this document..."
    )
    
    if uploaded_file is not None:
        # Display file info
        st.info(f"📁 **File:** {uploaded_file.name} ({uploaded_file.size:,} bytes)")
        
        # Upload button
        if st.button("🚀 Upload Document", type="primary"):
            with st.spinner("Uploading document..."):
                file_content = uploaded_file.read()
                result = st.session_state.api_client.upload_document(
                    file_content, uploaded_file.name, description
                )
                
                if "error" in result:
                    st.error(f"❌ Upload failed: {result['error']}")
                else:
                    st.success(f"✅ Document uploaded successfully!")
                    st.session_state.uploaded_documents[result["document_id"]] = result
                    st.session_state.current_document_id = result["document_id"]
                    
                    # Show upload details
                    st.json(result)
                    
                    st.info("➡️ Go to 'Document Processing' to parse your document.")


def document_processing_page():
    """Document processing and parsing page."""
    st.header("⚙️ Document Processing")
    
    # Load documents
    documents_response = st.session_state.api_client.list_documents()
    
    if "error" in documents_response:
        st.error(f"❌ Failed to load documents: {documents_response['error']}")
        return
    
    documents = documents_response if isinstance(documents_response, list) else []
    
    if not documents:
        st.info("📭 No documents uploaded yet. Go to 'Document Upload' to upload a document.")
        return
    
    # Document selection
    st.subheader("📋 Select Document to Process")
    
    doc_options = {
        doc["document_id"]: f"{doc['filename']} ({doc['status']})"
        for doc in documents
    }
    
    selected_doc_id = st.selectbox(
        "Choose document:",
        options=list(doc_options.keys()),
        format_func=lambda x: doc_options[x],
        key="selected_document"
    )
    
    if selected_doc_id:
        # Get selected document details
        selected_doc = next(doc for doc in documents if doc["document_id"] == selected_doc_id)
        
        # Display document info
        col1, col2, col3 = st.columns(3)
        
        with col1:
            st.metric("📄 File Type", selected_doc["file_type"].upper())
        
        with col2:
            st.metric("📏 File Size", f"{selected_doc['file_size']:,} bytes")
        
        with col3:
            st.metric("📅 Uploaded", selected_doc["upload_timestamp"][:10])
        
        # Document status
        status_response = st.session_state.api_client.get_document_status(selected_doc_id)
        
        if "error" not in status_response:
            status = status_response["status"]
            progress = status_response["progress_percent"]
            current_step = status_response["current_step"]
            message = status_response["message"]
            
            # Status display
            st.subheader("📊 Processing Status")
            
            # Progress bar
            st.progress(progress / 100, text=f"{progress}% - {current_step}")
            
            # Status badge
            if status == "uploaded":
                st.info(f"📋 {message}")
            elif status == "parsing":
                st.warning(f"⚙️ {message}")
            elif status == "parsed":
                st.success(f"✅ {message}")
            elif status == "error":
                st.error(f"❌ {message}")
                if status_response.get("error"):
                    st.error(f"Error details: {status_response['error']}")
            
            # Parse button
            if status in ["uploaded", "error"]:
                if st.button("🔍 Parse Document", type="primary"):
                    with st.spinner("Parsing document..."):
                        parse_result = st.session_state.api_client.parse_document(selected_doc_id)
                        
                        if "error" in parse_result:
                            st.error(f"❌ Parsing failed: {parse_result['error']}")
                        else:
                            st.success("✅ Document parsed successfully!")
                            st.rerun()
            
            # Show parsed content if available
            if status == "parsed":
                if st.button("📖 View Parsed Content"):
                    parse_result = st.session_state.api_client.parse_document(selected_doc_id)
                    
                    if "error" not in parse_result:
                        st.subheader("📑 Parsed Sections")
                        st.info(f"Found {parse_result['sections_count']} sections ({parse_result['text_length']:,} characters)")
                        
                        # Show sections
                        for i, section in enumerate(parse_result["sections"], 1):
                            with st.expander(f"Section {i}: {section['title']}"):
                                st.write(f"**Level:** {section['level']}")
                                if section.get('line_number'):
                                    st.write(f"**Line:** {section['line_number']}")
                                st.write("**Content:**")
                                st.text_area(
                                    "Section content",
                                    section["content"],
                                    height=200,
                                    key=f"section_{i}",
                                    label_visibility="collapsed"
                                )
                
                st.info("➡️ Go to 'Project Management' to create a project from this document.")


def project_management_page():
    """Project creation and management page."""
    st.header("🚀 Project Management")
    
    # Load projects
    projects_response = st.session_state.api_client.list_projects()
    
    if "error" in projects_response:
        st.error(f"❌ Failed to load projects: {projects_response['error']}")
        return
    
    projects = projects_response if isinstance(projects_response, list) else []
    
    # Create new project section
    st.subheader("➕ Create New Project")
    
    # Load documents for project creation
    documents_response = st.session_state.api_client.list_documents()
    
    if "error" not in documents_response:
        documents = documents_response if isinstance(documents_response, list) else []
        parsed_docs = [doc for doc in documents if doc["status"] == "parsed"]
        
        if parsed_docs:
            with st.form("create_project"):
                project_name = st.text_input("Project Name", placeholder="My Application")
                
                project_description = st.text_area(
                    "Project Description (Optional)",
                    placeholder="Describe your application..."
                )
                
                doc_options = {
                    doc["document_id"]: f"{doc['filename']} (uploaded {doc['upload_timestamp'][:10]})"
                    for doc in parsed_docs
                }
                
                selected_doc_id = st.selectbox(
                    "Source Document:",
                    options=list(doc_options.keys()),
                    format_func=lambda x: doc_options[x]
                )
                
                if st.form_submit_button("🚀 Create Project", type="primary"):
                    if project_name:
                        with st.spinner("Creating project..."):
                            result = st.session_state.api_client.create_project(
                                project_name, selected_doc_id, project_description
                            )
                            
                            if "error" in result:
                                st.error(f"❌ Project creation failed: {result['error']}")
                            else:
                                st.success("✅ Project created successfully!")
                                st.rerun()
                    else:
                        st.error("❌ Please enter a project name.")
        else:
            st.info("📭 No parsed documents available. Parse a document first to create a project.")
    
    # Existing projects section
    if projects:
        st.subheader("📁 Existing Projects")
        
        for project in projects:
            with st.expander(f"🚀 {project['name']} - {project['status'].title()}"):
                col1, col2 = st.columns(2)
                
                with col1:
                    st.write(f"**Created:** {project['created_at'][:10]}")
                    st.write(f"**Status:** {project['status']}")
                    st.write(f"**Phase:** {project['current_phase']}")
                
                with col2:
                    st.write(f"**Progress:** {project['progress_percent']}%")
                    st.write(f"**Agents Completed:** {len(project['agents_completed'])}")
                    st.write(f"**Agents Pending:** {len(project['agents_pending'])}")
                
                if project.get("description"):
                    st.write(f"**Description:** {project['description']}")
                
                # Progress bar
                st.progress(project['progress_percent'] / 100)
                
                # Generated files
                if project.get("generated_files"):
                    st.write(f"**Generated Files:** {len(project['generated_files'])}")
                else:
                    st.write("**Generated Files:** None yet")
    
    else:
        st.info("📭 No projects created yet.")


def agent_monitoring_page():
    """Agent status monitoring page."""
    st.header("🤖 Agent Monitoring")
    
    # Load agents
    agents_response = st.session_state.api_client.list_agents()
    
    if "error" in agents_response:
        st.error(f"❌ Failed to load agents: {agents_response['error']}")
        return
    
    agents = agents_response if isinstance(agents_response, list) else []
    
    if not agents:
        st.info("🤖 No agents registered yet.")
        return
    
    # Agents overview
    st.subheader("🔍 Agents Overview")
    
    # Agent metrics
    total_agents = len(agents)
    available_agents = len([a for a in agents if a["status"] == "available"])
    running_agents = len([a for a in agents if a["status"] == "running"])
    
    col1, col2, col3 = st.columns(3)
    
    with col1:
        st.metric("🤖 Total Agents", total_agents)
    
    with col2:
        st.metric("✅ Available", available_agents)
    
    with col3:
        st.metric("⚙️ Running", running_agents)
    
    # Agents table
    st.subheader("📊 Agent Details")
    
    agent_data = []
    for agent in agents:
        agent_data.append({
            "Name": agent["name"],
            "Status": agent["status"],
            "Success Rate": f"{agent['success_rate']:.1%}",
            "Executions": agent.get("execution_count", 0),
            "Avg Duration": f"{agent.get('average_duration', 0):.1f}s" if agent.get('average_duration') else "N/A",
            "Last Run": agent.get("last_run", "Never")[:10] if agent.get("last_run") else "Never",
            "Capabilities": ", ".join(agent.get("capabilities", []))
        })
    
    df = pd.DataFrame(agent_data)
    st.dataframe(df, use_container_width=True)
    
    # Individual agent details
    st.subheader("🔧 Agent Details")
    
    for agent in agents:
        with st.expander(f"🤖 {agent['name']} - {agent['status'].title()}"):
            col1, col2 = st.columns(2)
            
            with col1:
                st.write(f"**Description:** {agent['description']}")
                st.write(f"**Status:** {agent['status']}")
                st.write(f"**Success Rate:** {agent['success_rate']:.1%}")
            
            with col2:
                st.write(f"**Executions:** {agent.get('execution_count', 0)}")
                st.write(f"**Average Duration:** {agent.get('average_duration', 0):.1f}s")
                st.write(f"**Last Run:** {agent.get('last_run', 'Never')}")
            
            st.write(f"**Capabilities:** {', '.join(agent.get('capabilities', []))}")


def main():
    """Main Streamlit application."""
    st.set_page_config(
        page_title="SRC to Application Generator",
        page_icon="⚡",
        layout="wide",
        initial_sidebar_state="expanded"
    )
    
    # Initialize session state
    init_session_state()
    
    # Header
    st.title("⚡ SRC to Application Generator")
    st.subtitle("Transform Software Requirements into Full-Stack Applications")
    
    # Show API status in sidebar
    show_api_status()
    
    # Navigation
    with st.sidebar:
        st.subheader("🧭 Navigation")
        
        page = st.radio(
            "Select Page:",
            [
                "📄 Document Upload",
                "⚙️ Document Processing", 
                "🚀 Project Management",
                "🤖 Agent Monitoring"
            ],
            key="navigation"
        )
    
    # Page routing
    if page == "📄 Document Upload":
        upload_document_page()
    elif page == "⚙️ Document Processing":
        document_processing_page()
    elif page == "🚀 Project Management":
        project_management_page()
    elif page == "🤖 Agent Monitoring":
        agent_monitoring_page()
    
    # Footer
    with st.sidebar:
        st.markdown("---")
        st.caption("SRC Generator v1.0.0")
        st.caption("Built with FastAPI + Streamlit")


if __name__ == "__main__":
    main()