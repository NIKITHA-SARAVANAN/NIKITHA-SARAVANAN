"""
Main Streamlit application for the SRS to Angular+FastAPI generator.

This module provides the user interface for uploading SRS documents,
managing workflows, and monitoring the code generation process.
"""

import streamlit as st
import requests
import json
import time
import os
import sys
from datetime import datetime
from typing import Dict, List, Optional, Any
from pathlib import Path
import plotly.express as px
import plotly.graph_objects as go
from plotly.subplots import make_subplots
import pandas as pd

# Add project root to path
sys.path.append(os.path.dirname(os.path.dirname(os.path.abspath(__file__))))

from config.config import settings

# Configure Streamlit page
st.set_page_config(
    page_title="SRS to Angular+FastAPI Generator",
    page_icon="🚀",
    layout="wide",
    initial_sidebar_state="expanded"
)

# API base URL
API_BASE_URL = f"http://{settings.backend_host}:{settings.backend_port}"

# Custom CSS for better styling
st.markdown("""
<style>
    .main-header {
        text-align: center;
        padding: 1rem 0;
        border-bottom: 2px solid #f0f2f6;
        margin-bottom: 2rem;
    }
    
    .status-success {
        color: #28a745;
        font-weight: bold;
    }
    
    .status-error {
        color: #dc3545;
        font-weight: bold;
    }
    
    .status-warning {
        color: #ffc107;
        font-weight: bold;
    }
    
    .status-info {
        color: #17a2b8;
        font-weight: bold;
    }
    
    .metric-card {
        background-color: #f8f9fa;
        padding: 1rem;
        border-radius: 0.5rem;
        border-left: 4px solid #007bff;
        margin: 0.5rem 0;
    }
    
    .workflow-stage {
        padding: 0.5rem;
        margin: 0.25rem 0;
        border-radius: 0.25rem;
        border-left: 3px solid;
    }
    
    .stage-pending {
        border-left-color: #6c757d;
        background-color: #f8f9fa;
    }
    
    .stage-running {
        border-left-color: #007bff;
        background-color: #e7f1ff;
    }
    
    .stage-completed {
        border-left-color: #28a745;
        background-color: #d4edda;
    }
    
    .stage-failed {
        border-left-color: #dc3545;
        background-color: #f8d7da;
    }
</style>
""", unsafe_allow_html=True)


class APIClient:
    """API client for communicating with the FastAPI backend."""
    
    def __init__(self, base_url: str):
        self.base_url = base_url
        self.session = requests.Session()
    
    def get_health(self) -> Dict[str, Any]:
        """Get application health status."""
        try:
            response = self.session.get(f"{self.base_url}/health", timeout=5)
            response.raise_for_status()
            return response.json()
        except Exception as e:
            return {"status": "error", "error": str(e)}
    
    def get_detailed_health(self) -> Dict[str, Any]:
        """Get detailed health status."""
        try:
            response = self.session.get(f"{self.base_url}/health/detailed", timeout=10)
            response.raise_for_status()
            return response.json()
        except Exception as e:
            return {"status": "error", "error": str(e)}
    
    def get_supported_formats(self) -> Dict[str, Any]:
        """Get supported file formats."""
        try:
            response = self.session.get(f"{self.base_url}/api/v1/documents/supported-formats")
            response.raise_for_status()
            return response.json()
        except Exception as e:
            return {"error": str(e)}
    
    def upload_document(self, file_data: bytes, filename: str, description: str = None) -> Dict[str, Any]:
        """Upload a document to the backend."""
        try:
            files = {"file": (filename, file_data)}
            data = {"description": description} if description else {}
            
            response = self.session.post(
                f"{self.base_url}/api/v1/documents/upload",
                files=files,
                data=data,
                timeout=60
            )
            response.raise_for_status()
            return response.json()
        except Exception as e:
            return {"error": str(e)}
    
    def parse_document(self, document_id: str) -> Dict[str, Any]:
        """Parse an uploaded document."""
        try:
            response = self.session.post(
                f"{self.base_url}/api/v1/documents/{document_id}/parse",
                timeout=120
            )
            response.raise_for_status()
            return response.json()
        except Exception as e:
            return {"error": str(e)}
    
    def get_document(self, document_id: str) -> Dict[str, Any]:
        """Get document details."""
        try:
            response = self.session.get(f"{self.base_url}/api/v1/documents/{document_id}")
            response.raise_for_status()
            return response.json()
        except Exception as e:
            return {"error": str(e)}
    
    def list_documents(self, status: str = None, limit: int = 50) -> List[Dict[str, Any]]:
        """List uploaded documents."""
        try:
            params = {"limit": limit}
            if status:
                params["status"] = status
            
            response = self.session.get(
                f"{self.base_url}/api/v1/documents/",
                params=params
            )
            response.raise_for_status()
            return response.json()
        except Exception as e:
            return []
    
    def start_workflow(self, document_id: str, workflow_type: str, options: Dict[str, Any] = None) -> Dict[str, Any]:
        """Start a workflow for document processing."""
        try:
            data = {
                "document_id": document_id,
                "workflow_type": workflow_type,
                "options": options or {}
            }
            
            response = self.session.post(
                f"{self.base_url}/api/v1/workflow/start",
                json=data,
                timeout=30
            )
            response.raise_for_status()
            return response.json()
        except Exception as e:
            return {"error": str(e)}
    
    def get_workflow(self, workflow_id: str) -> Dict[str, Any]:
        """Get workflow status and details."""
        try:
            response = self.session.get(f"{self.base_url}/api/v1/workflow/{workflow_id}")
            response.raise_for_status()
            return response.json()
        except Exception as e:
            return {"error": str(e)}
    
    def update_workflow(self, workflow_id: str, action: str, data: Dict[str, Any] = None, comment: str = None) -> Dict[str, Any]:
        """Update workflow status."""
        try:
            payload = {
                "action": action,
                "data": data,
                "comment": comment
            }
            
            response = self.session.post(
                f"{self.base_url}/api/v1/workflow/{workflow_id}/update",
                json=payload
            )
            response.raise_for_status()
            return response.json()
        except Exception as e:
            return {"error": str(e)}
    
    def get_agents(self) -> List[Dict[str, Any]]:
        """Get list of available agents."""
        try:
            response = self.session.get(f"{self.base_url}/api/v1/agents/")
            response.raise_for_status()
            return response.json()
        except Exception as e:
            return []
    
    def get_agent_registry(self) -> Dict[str, Any]:
        """Get agent registry information."""
        try:
            response = self.session.get(f"{self.base_url}/api/v1/agents/registry")
            response.raise_for_status()
            return response.json()
        except Exception as e:
            return {"error": str(e)}


# Initialize API client
@st.cache_resource
def get_api_client():
    """Get cached API client instance."""
    return APIClient(API_BASE_URL)


def show_header():
    """Display the application header."""
    st.markdown("""
    <div class="main-header">
        <h1>🚀 SRS to Angular+FastAPI Generator</h1>
        <p>Transform your Software Requirements Specification into full-stack applications</p>
    </div>
    """, unsafe_allow_html=True)


def show_sidebar():
    """Display the sidebar with navigation and system status."""
    st.sidebar.title("Navigation")
    
    # Navigation menu
    page = st.sidebar.radio(
        "Choose a page:",
        ["🏠 Dashboard", "📄 Documents", "⚙️ Workflows", "🤖 Agents", "📊 Analytics", "❤️ Health"]
    )
    
    # System status in sidebar
    st.sidebar.markdown("---")
    st.sidebar.subheader("System Status")
    
    api_client = get_api_client()
    health = api_client.get_health()
    
    if "error" in health:
        st.sidebar.error("❌ Backend Offline")
    else:
        st.sidebar.success("✅ Backend Online")
        uptime_hours = health.get("uptime_seconds", 0) / 3600
        st.sidebar.info(f"⏱️ Uptime: {uptime_hours:.1f}h")
    
    return page


def show_dashboard():
    """Display the main dashboard."""
    st.header("📊 Dashboard")
    
    api_client = get_api_client()
    
    # Metrics row
    col1, col2, col3, col4 = st.columns(4)
    
    # Get documents
    documents = api_client.list_documents()
    
    with col1:
        st.metric("📄 Total Documents", len(documents))
    
    with col2:
        parsed_docs = len([d for d in documents if d.get("status") == "parsed"])
        st.metric("✅ Parsed Documents", parsed_docs)
    
    with col3:
        # This would come from workflow API
        st.metric("⚙️ Active Workflows", 0)
    
    with col4:
        # This would come from agents API
        agents = api_client.get_agents()
        available_agents = len([a for a in agents if a.get("status") == "available"])
        st.metric("🤖 Available Agents", available_agents)
    
    # Recent activity
    st.subheader("📈 Recent Activity")
    
    if documents:
        # Create a DataFrame for recent documents
        df = pd.DataFrame(documents[:10])  # Last 10 documents
        df["upload_date"] = pd.to_datetime(df["upload_date"])
        
        # Status distribution chart
        col1, col2 = st.columns(2)
        
        with col1:
            status_counts = df["status"].value_counts()
            fig = px.pie(
                values=status_counts.values,
                names=status_counts.index,
                title="Document Status Distribution"
            )
            st.plotly_chart(fig, use_container_width=True)
        
        with col2:
            # Upload timeline
            daily_uploads = df.groupby(df["upload_date"].dt.date).size()
            fig = px.line(
                x=daily_uploads.index,
                y=daily_uploads.values,
                title="Daily Document Uploads",
                labels={"x": "Date", "y": "Documents"}
            )
            st.plotly_chart(fig, use_container_width=True)
        
        # Recent documents table
        st.subheader("📋 Recent Documents")
        
        display_df = df[["filename", "status", "file_type", "upload_date"]].copy()
        display_df["upload_date"] = display_df["upload_date"].dt.strftime("%Y-%m-%d %H:%M")
        
        st.dataframe(display_df, use_container_width=True)
    else:
        st.info("📭 No documents uploaded yet. Go to the Documents page to get started!")


def show_documents_page():
    """Display the documents management page."""
    st.header("📄 Document Management")
    
    api_client = get_api_client()
    
    # Upload section
    st.subheader("📤 Upload New Document")
    
    # Get supported formats
    formats_info = api_client.get_supported_formats()
    
    if "error" not in formats_info:
        supported_formats = formats_info.get("supported_formats", [])
        max_size_mb = formats_info.get("max_file_size_mb", 50)
        
        st.info(f"📋 Supported formats: {', '.join(supported_formats)} | Max size: {max_size_mb}MB")
        
        # File upload
        uploaded_file = st.file_uploader(
            "Choose an SRS document",
            type=supported_formats,
            help=f"Upload your Software Requirements Specification document"
        )
        
        description = st.text_area(
            "Document Description (optional)",
            placeholder="Brief description of the SRS document..."
        )
        
        if uploaded_file is not None:
            col1, col2 = st.columns([3, 1])
            
            with col1:
                st.write(f"📁 **File:** {uploaded_file.name}")
                st.write(f"📊 **Size:** {uploaded_file.size / 1024:.1f} KB")
                st.write(f"🏷️ **Type:** {uploaded_file.type}")
            
            with col2:
                if st.button("🚀 Upload Document", type="primary"):
                    with st.spinner("Uploading document..."):
                        # Read file data
                        file_data = uploaded_file.read()
                        
                        # Upload document
                        result = api_client.upload_document(
                            file_data, 
                            uploaded_file.name, 
                            description
                        )
                        
                        if "error" in result:
                            st.error(f"❌ Upload failed: {result['error']}")
                        else:
                            st.success(f"✅ Document uploaded successfully!")
                            st.info(f"📄 Document ID: {result['id']}")
                            
                            # Auto-parse the document
                            if st.button("🔍 Parse Document"):
                                with st.spinner("Parsing document..."):
                                    parse_result = api_client.parse_document(result['id'])
                                    
                                    if "error" in parse_result:
                                        st.error(f"❌ Parsing failed: {parse_result['error']}")
                                    else:
                                        st.success("✅ Document parsed successfully!")
                                        st.rerun()
    
    # Documents list
    st.subheader("📋 Document Library")
    
    # Filters
    col1, col2 = st.columns([2, 1])
    
    with col1:
        status_filter = st.selectbox(
            "Filter by Status",
            ["All", "uploaded", "parsing", "parsed", "failed"],
            key="status_filter"
        )
    
    with col2:
        if st.button("🔄 Refresh"):
            st.rerun()
    
    # Get documents
    status = None if status_filter == "All" else status_filter
    documents = api_client.list_documents(status=status)
    
    if documents:
        for doc in documents:
            with st.expander(f"📄 {doc['filename']} - {doc['status'].upper()}"):
                col1, col2, col3 = st.columns([2, 1, 1])
                
                with col1:
                    st.write(f"**ID:** {doc['id']}")
                    st.write(f"**Type:** {doc['file_type']}")
                    st.write(f"**Size:** {doc['file_size'] / 1024:.1f} KB")
                    st.write(f"**Uploaded:** {doc['upload_date']}")
                
                with col2:
                    # Status badge
                    status = doc['status']
                    if status == "parsed":
                        st.markdown('<span class="status-success">✅ Parsed</span>', unsafe_allow_html=True)
                    elif status == "failed":
                        st.markdown('<span class="status-error">❌ Failed</span>', unsafe_allow_html=True)
                    elif status == "parsing":
                        st.markdown('<span class="status-warning">⏳ Parsing</span>', unsafe_allow_html=True)
                    else:
                        st.markdown('<span class="status-info">📄 Uploaded</span>', unsafe_allow_html=True)
                
                with col3:
                    if status == "uploaded":
                        if st.button(f"🔍 Parse", key=f"parse_{doc['id']}"):
                            with st.spinner("Parsing document..."):
                                parse_result = api_client.parse_document(doc['id'])
                                
                                if "error" in parse_result:
                                    st.error(f"❌ Parsing failed: {parse_result['error']}")
                                else:
                                    st.success("✅ Document parsed!")
                                    st.rerun()
                    
                    elif status == "parsed":
                        if st.button(f"⚙️ Start Workflow", key=f"workflow_{doc['id']}"):
                            st.session_state.selected_document = doc['id']
                            st.session_state.show_workflow_dialog = True
                            st.rerun()
                
                # Show document details if parsed
                if status == "parsed":
                    doc_details = api_client.get_document(doc['id'])
                    if "error" not in doc_details:
                        st.write("**Content Summary:**")
                        sections = doc_details.get('sections', [])
                        requirements = doc_details.get('requirements', [])
                        
                        st.write(f"- 📚 Sections: {len(sections)}")
                        st.write(f"- 📋 Requirements: {len(requirements)}")
                        
                        if sections:
                            with st.expander("📖 Document Sections"):
                                for i, section in enumerate(sections[:5]):  # Show first 5 sections
                                    st.write(f"**{i+1}. {section['title']}** (Level {section['level']})")
                        
                        if requirements:
                            with st.expander("📋 Extracted Requirements"):
                                for i, req in enumerate(requirements[:10]):  # Show first 10 requirements
                                    st.write(f"{i+1}. {req}")
    else:
        st.info("📭 No documents found. Upload a document to get started!")
    
    # Workflow start dialog
    if st.session_state.get('show_workflow_dialog', False):
        show_workflow_start_dialog(api_client)


def show_workflow_start_dialog(api_client: APIClient):
    """Show the workflow start dialog."""
    st.subheader("🚀 Start New Workflow")
    
    document_id = st.session_state.get('selected_document')
    
    col1, col2 = st.columns(2)
    
    with col1:
        workflow_type = st.selectbox(
            "Workflow Type",
            ["full_generation", "backend_only", "frontend_only"],
            help="Choose what to generate"
        )
    
    with col2:
        if st.button("❌ Cancel"):
            st.session_state.show_workflow_dialog = False
            st.rerun()
    
    st.write("**Workflow Options:**")
    
    # Advanced options
    with st.expander("⚙️ Advanced Options"):
        include_tests = st.checkbox("Generate Tests", value=True)
        include_docs = st.checkbox("Generate Documentation", value=True)
        code_style = st.selectbox("Code Style", ["standard", "strict", "relaxed"])
        
        options = {
            "include_tests": include_tests,
            "include_docs": include_docs,
            "code_style": code_style
        }
    
    col1, col2 = st.columns(2)
    
    with col1:
        if st.button("🚀 Start Workflow", type="primary"):
            with st.spinner("Starting workflow..."):
                result = api_client.start_workflow(document_id, workflow_type, options)
                
                if "error" in result:
                    st.error(f"❌ Failed to start workflow: {result['error']}")
                else:
                    st.success(f"✅ Workflow started successfully!")
                    st.info(f"🔧 Workflow ID: {result['id']}")
                    st.session_state.show_workflow_dialog = False
                    st.rerun()
    
    with col2:
        if st.button("❌ Cancel", key="cancel_workflow"):
            st.session_state.show_workflow_dialog = False
            st.rerun()


def show_workflows_page():
    """Display the workflows management page."""
    st.header("⚙️ Workflow Management")
    
    # Placeholder for workflow management
    st.info("🚧 Workflow management interface coming soon!")
    
    api_client = get_api_client()
    
    # Show workflow list when available
    st.subheader("📋 Active Workflows")
    st.write("This section will show:")
    st.write("- Active workflow list")
    st.write("- Workflow progress tracking") 
    st.write("- Human approval requests")
    st.write("- Workflow logs and results")


def show_agents_page():
    """Display the agents management page."""
    st.header("🤖 Agent Management")
    
    api_client = get_api_client()
    
    # Agent registry overview
    st.subheader("📊 Agent Registry")
    
    registry = api_client.get_agent_registry()
    
    if "error" not in registry:
        col1, col2, col3, col4 = st.columns(4)
        
        with col1:
            st.metric("🤖 Total Agents", registry.get("total_agents", 0))
        
        with col2:
            st.metric("✅ Available", registry.get("available_agents", 0))
        
        with col3:
            st.metric("🔄 Busy", registry.get("busy_agents", 0))
        
        with col4:
            st.metric("❌ Error", registry.get("error_agents", 0))
        
        # Category breakdown
        categories = registry.get("categories", {})
        if categories:
            st.subheader("📋 Agents by Category")
            
            fig = px.bar(
                x=list(categories.keys()),
                y=list(categories.values()),
                title="Agent Distribution by Category"
            )
            st.plotly_chart(fig, use_container_width=True)
    
    # Agent list
    st.subheader("🤖 Agent Details")
    
    agents = api_client.get_agents()
    
    if agents:
        # Filter controls
        col1, col2 = st.columns(2)
        
        with col1:
            category_filter = st.selectbox(
                "Filter by Category",
                ["All"] + list(set(agent.get("category", "unknown") for agent in agents))
            )
        
        with col2:
            status_filter = st.selectbox(
                "Filter by Status",
                ["All", "available", "busy", "error", "disabled"]
            )
        
        # Filter agents
        filtered_agents = agents
        if category_filter != "All":
            filtered_agents = [a for a in filtered_agents if a.get("category") == category_filter]
        if status_filter != "All":
            filtered_agents = [a for a in filtered_agents if a.get("status") == status_filter]
        
        # Display agents
        for agent in filtered_agents:
            with st.expander(f"🤖 {agent['name']} - {agent['status'].upper()}"):
                col1, col2 = st.columns([2, 1])
                
                with col1:
                    st.write(f"**Description:** {agent['description']}")
                    st.write(f"**Category:** {agent['category']}")
                    st.write(f"**Version:** {agent['version']}")
                    st.write(f"**Capabilities:** {', '.join(agent['capabilities'])}")
                    
                    if agent.get("last_executed"):
                        st.write(f"**Last Executed:** {agent['last_executed']}")
                
                with col2:
                    # Status badge
                    status = agent['status']
                    if status == "available":
                        st.markdown('<span class="status-success">✅ Available</span>', unsafe_allow_html=True)
                    elif status == "busy":
                        st.markdown('<span class="status-warning">🔄 Busy</span>', unsafe_allow_html=True)
                    elif status == "error":
                        st.markdown('<span class="status-error">❌ Error</span>', unsafe_allow_html=True)
                    else:
                        st.markdown('<span class="status-info">⏸️ Disabled</span>', unsafe_allow_html=True)
                    
                    # Performance metrics
                    executions = agent.get("total_executions", 0)
                    success_rate = agent.get("success_rate", 0) * 100
                    
                    st.metric("Executions", executions)
                    st.metric("Success Rate", f"{success_rate:.1f}%")
    else:
        st.warning("⚠️ No agents found or backend unavailable")


def show_analytics_page():
    """Display the analytics page."""
    st.header("📊 Analytics & Insights")
    
    st.info("🚧 Analytics dashboard coming soon!")
    
    st.write("This section will include:")
    st.write("- 📈 Processing time trends")
    st.write("- 🎯 Success rate analytics") 
    st.write("- 🔍 Error pattern analysis")
    st.write("- 📊 Resource usage metrics")
    st.write("- 🤖 Agent performance comparisons")


def show_health_page():
    """Display the system health page."""
    st.header("❤️ System Health")
    
    api_client = get_api_client()
    
    # Basic health check
    col1, col2 = st.columns(2)
    
    with col1:
        st.subheader("🏥 Basic Health")
        health = api_client.get_health()
        
        if "error" in health:
            st.error("❌ Backend Offline")
            st.write(f"Error: {health['error']}")
        else:
            st.success("✅ System Healthy")
            st.write(f"**Environment:** {health.get('environment', 'unknown')}")
            st.write(f"**Version:** {health.get('version', 'unknown')}")
            
            uptime_seconds = health.get('uptime_seconds', 0)
            uptime_hours = uptime_seconds / 3600
            st.write(f"**Uptime:** {uptime_hours:.1f} hours")
    
    with col2:
        if st.button("🔄 Refresh Health Status"):
            st.rerun()
    
    # Detailed health check
    st.subheader("🔍 Detailed Health Status")
    
    detailed_health = api_client.get_detailed_health()
    
    if "error" not in detailed_health:
        # System resources
        system_info = detailed_health.get("system", {})
        if system_info and "error" not in system_info:
            st.subheader("💻 System Resources")
            
            col1, col2, col3 = st.columns(3)
            
            with col1:
                cpu_info = system_info.get("cpu", {})
                cpu_usage = cpu_info.get("usage_percent", 0)
                st.metric("CPU Usage", f"{cpu_usage:.1f}%")
                
                # CPU usage bar
                fig = go.Figure(go.Indicator(
                    mode="gauge+number",
                    value=cpu_usage,
                    domain={'x': [0, 1], 'y': [0, 1]},
                    title={'text': "CPU %"},
                    gauge={'axis': {'range': [None, 100]},
                           'bar': {'color': "darkblue"},
                           'steps': [{'range': [0, 50], 'color': "lightgray"},
                                   {'range': [50, 85], 'color': "yellow"},
                                   {'range': [85, 100], 'color': "red"}]}
                ))
                fig.update_layout(height=200)
                st.plotly_chart(fig, use_container_width=True)
            
            with col2:
                memory_info = system_info.get("memory", {})
                memory_percent = memory_info.get("percent", 0)
                st.metric("Memory Usage", f"{memory_percent:.1f}%")
                
                # Memory usage bar
                fig = go.Figure(go.Indicator(
                    mode="gauge+number",
                    value=memory_percent,
                    domain={'x': [0, 1], 'y': [0, 1]},
                    title={'text': "Memory %"},
                    gauge={'axis': {'range': [None, 100]},
                           'bar': {'color': "darkgreen"},
                           'steps': [{'range': [0, 50], 'color': "lightgray"},
                                   {'range': [50, 85], 'color': "yellow"},
                                   {'range': [85, 100], 'color': "red"}]}
                ))
                fig.update_layout(height=200)
                st.plotly_chart(fig, use_container_width=True)
            
            with col3:
                disk_info = system_info.get("disk", {})
                disk_percent = disk_info.get("percent", 0)
                st.metric("Disk Usage", f"{disk_percent:.1f}%")
                
                # Disk usage bar
                fig = go.Figure(go.Indicator(
                    mode="gauge+number",
                    value=disk_percent,
                    domain={'x': [0, 1], 'y': [0, 1]},
                    title={'text': "Disk %"},
                    gauge={'axis': {'range': [None, 100]},
                           'bar': {'color': "darkorange"},
                           'steps': [{'range': [0, 50], 'color': "lightgray"},
                                   {'range': [50, 85], 'color': "yellow"},
                                   {'range': [85, 100], 'color': "red"}]}
                ))
                fig.update_layout(height=200)
                st.plotly_chart(fig, use_container_width=True)
        
        # Database status
        st.subheader("🗃️ Database Status")
        db_info = detailed_health.get("database", {})
        
        col1, col2 = st.columns(2)
        
        with col1:
            if db_info.get("connected"):
                st.success("✅ Database Connected")
            else:
                st.error("❌ Database Disconnected")
                if "error" in db_info:
                    st.write(f"Error: {db_info['error']}")
        
        with col2:
            st.write(f"**URL:** {db_info.get('url', 'Unknown')}")
            st.write(f"**Echo Mode:** {db_info.get('echo', False)}")
        
        # Dependencies status
        st.subheader("📦 Dependencies")
        deps = detailed_health.get("dependencies", {})
        
        if deps:
            col1, col2 = st.columns(2)
            
            for i, (dep_name, status) in enumerate(deps.items()):
                target_col = col1 if i % 2 == 0 else col2
                
                with target_col:
                    if status:
                        st.success(f"✅ {dep_name}")
                    else:
                        st.error(f"❌ {dep_name}")


def main():
    """Main application function."""
    # Initialize session state
    if 'show_workflow_dialog' not in st.session_state:
        st.session_state.show_workflow_dialog = False
    
    # Show header
    show_header()
    
    # Show sidebar and get selected page
    page = show_sidebar()
    
    # Route to appropriate page
    if page == "🏠 Dashboard":
        show_dashboard()
    elif page == "📄 Documents":
        show_documents_page()
    elif page == "⚙️ Workflows":
        show_workflows_page()
    elif page == "🤖 Agents":
        show_agents_page()
    elif page == "📊 Analytics":
        show_analytics_page()
    elif page == "❤️ Health":
        show_health_page()


if __name__ == "__main__":
    main()