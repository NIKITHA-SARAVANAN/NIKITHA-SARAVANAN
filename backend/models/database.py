"""
Database models for the SRS to Angular+FastAPI generator.

This module defines SQLAlchemy models for storing documents, workflows,
agent executions, and other application data.
"""

import uuid
from datetime import datetime
from enum import Enum
from typing import Optional, Dict, List, Any
from sqlalchemy import Column, String, Integer, Float, DateTime, Text, JSON, Boolean, ForeignKey
from sqlalchemy.ext.declarative import declarative_base
from sqlalchemy.orm import relationship
from sqlalchemy.dialects.postgresql import UUID, ENUM
import sys
import os

# Add project root to path
sys.path.append(os.path.dirname(os.path.dirname(os.path.dirname(os.path.abspath(__file__)))))

from utils.logger import get_logger

logger = get_logger(__name__)

Base = declarative_base()


class DocumentStatus(str, Enum):
    """Document processing status enumeration."""
    UPLOADED = "uploaded"
    PARSING = "parsing"
    PARSED = "parsed"
    PROCESSING = "processing"
    SRD_GENERATED = "srd_generated"
    COMPLETED = "completed"
    FAILED = "failed"


class WorkflowStatus(str, Enum):
    """Workflow execution status enumeration."""
    PENDING = "pending"
    RUNNING = "running"
    WAITING_APPROVAL = "waiting_approval"
    COMPLETED = "completed"
    FAILED = "failed"
    CANCELLED = "cancelled"


class AgentStatus(str, Enum):
    """Agent execution status enumeration."""
    PENDING = "pending"
    RUNNING = "running"
    COMPLETED = "completed"
    FAILED = "failed"
    TIMEOUT = "timeout"
    CANCELLED = "cancelled"


class Document(Base):
    """
    Document model for storing uploaded SRS documents.
    
    Stores document metadata, parsed content, requirements,
    and processing status throughout the workflow.
    """
    __tablename__ = "documents"
    
    # Primary identification
    id = Column(UUID(as_uuid=True), primary_key=True, default=uuid.uuid4)
    filename = Column(String(255), nullable=False)
    file_path = Column(String(500), nullable=False)
    file_type = Column(String(50), nullable=False)
    file_size = Column(Integer, nullable=False)
    
    # Content and metadata
    description = Column(Text)
    raw_text = Column(Text)
    metadata = Column(JSON, default={})
    
    # Document structure
    sections = Column(JSON, default=[])  # List of document sections
    requirements = Column(JSON, default=[])  # Extracted requirements
    table_of_contents = Column(JSON, default=[])  # Table of contents
    
    # Processing status
    status = Column(ENUM(DocumentStatus), default=DocumentStatus.UPLOADED, nullable=False)
    error_message = Column(Text)
    
    # Timestamps
    upload_date = Column(DateTime, default=datetime.utcnow, nullable=False)
    parsed_date = Column(DateTime)
    completed_date = Column(DateTime)
    
    # Generated outputs
    backend_srd = Column(Text)  # Generated backend SRD
    frontend_srd = Column(Text)  # Generated frontend SRD
    srd_metadata = Column(JSON, default={})
    
    # Relationships
    workflows = relationship("Workflow", back_populates="document", cascade="all, delete-orphan")
    
    def __repr__(self):
        return f"<Document(id='{self.id}', filename='{self.filename}', status='{self.status}')>"


class Workflow(Base):
    """
    Workflow model for managing document processing workflows.
    
    Tracks the execution of multi-agent workflows including
    approval states, progress, and execution logs.
    """
    __tablename__ = "workflows"
    
    # Primary identification
    id = Column(UUID(as_uuid=True), primary_key=True, default=uuid.uuid4)
    document_id = Column(UUID(as_uuid=True), ForeignKey("documents.id"), nullable=False)
    
    # Workflow configuration
    workflow_type = Column(String(50), nullable=False)  # full_generation, backend_only, frontend_only
    options = Column(JSON, default={})
    
    # Execution state
    status = Column(ENUM(WorkflowStatus), default=WorkflowStatus.PENDING, nullable=False)
    stages = Column(JSON, default=[])  # List of workflow stages
    current_stage_index = Column(Integer, default=0)
    
    # Progress tracking
    progress_percentage = Column(Float, default=0.0)
    started_date = Column(DateTime)
    completed_date = Column(DateTime)
    
    # Timestamps
    created_date = Column(DateTime, default=datetime.utcnow, nullable=False)
    updated_date = Column(DateTime, default=datetime.utcnow, onupdate=datetime.utcnow, nullable=False)
    
    # Human-in-the-loop
    pending_approvals = Column(JSON, default=[])  # List of pending approval requests
    approval_history = Column(JSON, default=[])  # History of approvals/rejections
    
    # Execution logs and results
    execution_logs = Column(JSON, default=[])  # Detailed execution logs
    generated_files = Column(JSON, default=[])  # List of generated files
    final_output = Column(JSON, default={})  # Final workflow output
    
    # Error handling
    error_message = Column(Text)
    failure_stage = Column(String(100))
    retry_count = Column(Integer, default=0)
    rejection_reason = Column(Text)
    
    # Relationships
    document = relationship("Document", back_populates="workflows")
    agent_executions = relationship("AgentExecution", back_populates="workflow", cascade="all, delete-orphan")
    
    def __repr__(self):
        return f"<Workflow(id='{self.id}', type='{self.workflow_type}', status='{self.status}')>"


class AgentExecution(Base):
    """
    Agent execution model for tracking individual agent runs.
    
    Stores detailed information about each agent execution including
    inputs, outputs, performance metrics, and decision trees.
    """
    __tablename__ = "agent_executions"
    
    # Primary identification
    id = Column(UUID(as_uuid=True), primary_key=True, default=uuid.uuid4)
    workflow_id = Column(UUID(as_uuid=True), ForeignKey("workflows.id"), nullable=False)
    agent_name = Column(String(100), nullable=False)
    
    # Execution context
    stage_name = Column(String(100), nullable=False)
    execution_order = Column(Integer, nullable=False)
    retry_attempt = Column(Integer, default=0)
    
    # Input and output data
    input_data = Column(JSON, default={})
    output_data = Column(JSON, default={})
    configuration = Column(JSON, default={})
    
    # Execution state
    status = Column(ENUM(AgentStatus), default=AgentStatus.PENDING, nullable=False)
    
    # Timing information
    start_time = Column(DateTime, nullable=False)
    end_time = Column(DateTime)
    execution_time_seconds = Column(Float)
    timeout_seconds = Column(Integer)
    
    # Decision tracking
    decision_tree = Column(JSON, default=[])  # Agent decision log
    reasoning = Column(Text)  # Agent reasoning explanation
    confidence_score = Column(Float)  # Confidence in decision (0.0-1.0)
    
    # Performance metrics
    tokens_used = Column(Integer)  # LLM tokens consumed
    api_calls_made = Column(Integer)  # Number of API calls
    memory_peak_mb = Column(Float)  # Peak memory usage
    
    # Results and artifacts
    generated_files = Column(JSON, default=[])  # Files generated by agent
    code_changes = Column(JSON, default=[])  # Code modifications made
    validation_results = Column(JSON, default={})  # Validation check results
    
    # Error handling
    error_message = Column(Text)
    error_type = Column(String(100))
    stack_trace = Column(Text)
    
    # Quality metrics
    code_quality_score = Column(Float)  # Code quality assessment
    security_score = Column(Float)  # Security assessment
    performance_score = Column(Float)  # Performance assessment
    
    # Relationships
    workflow = relationship("Workflow", back_populates="agent_executions")
    
    def __repr__(self):
        return f"<AgentExecution(id='{self.id}', agent='{self.agent_name}', status='{self.status}')>"


class HumanApproval(Base):
    """
    Human approval model for tracking approval requests and responses.
    
    Manages the human-in-the-loop approval process including
    content review, modifications, and approval history.
    """
    __tablename__ = "human_approvals"
    
    # Primary identification
    id = Column(UUID(as_uuid=True), primary_key=True, default=uuid.uuid4)
    workflow_id = Column(UUID(as_uuid=True), ForeignKey("workflows.id"), nullable=False)
    stage_name = Column(String(100), nullable=False)
    
    # Approval request details
    approval_type = Column(String(50), nullable=False)  # srd_review, code_review, test_review
    title = Column(String(200), nullable=False)
    description = Column(Text)
    
    # Content to review
    content = Column(JSON, nullable=False)  # Content requiring approval
    original_content = Column(JSON)  # Original content before modifications
    
    # Request state
    status = Column(String(20), default="pending", nullable=False)  # pending, approved, rejected, timeout
    priority = Column(String(20), default="normal")  # low, normal, high, urgent
    
    # Timing
    requested_date = Column(DateTime, default=datetime.utcnow, nullable=False)
    responded_date = Column(DateTime)
    timeout_date = Column(DateTime)
    
    # Response details
    approved = Column(Boolean)
    response_comment = Column(Text)
    modifications = Column(JSON, default={})  # User modifications to content
    
    # Reviewer information
    reviewer_id = Column(String(100))  # User ID of reviewer
    reviewer_role = Column(String(50))  # Role of reviewer
    
    # Metadata
    metadata = Column(JSON, default={})
    
    def __repr__(self):
        return f"<HumanApproval(id='{self.id}', type='{self.approval_type}', status='{self.status}')>"


class GeneratedFile(Base):
    """
    Generated file model for tracking all files created during workflows.
    
    Maintains a record of all generated code files, documentation,
    tests, and other artifacts with version history.
    """
    __tablename__ = "generated_files"
    
    # Primary identification
    id = Column(UUID(as_uuid=True), primary_key=True, default=uuid.uuid4)
    workflow_id = Column(UUID(as_uuid=True), ForeignKey("workflows.id"), nullable=False)
    agent_execution_id = Column(UUID(as_uuid=True), ForeignKey("agent_executions.id"))
    
    # File details
    filename = Column(String(255), nullable=False)
    file_path = Column(String(500), nullable=False)
    file_type = Column(String(50), nullable=False)  # typescript, python, html, css, etc.
    file_category = Column(String(50), nullable=False)  # component, service, model, test, etc.
    
    # Content
    content = Column(Text, nullable=False)
    content_hash = Column(String(64))  # SHA-256 hash for change detection
    file_size = Column(Integer)
    
    # Version information
    version = Column(Integer, default=1)
    is_latest = Column(Boolean, default=True)
    parent_file_id = Column(UUID(as_uuid=True), ForeignKey("generated_files.id"))
    
    # Generation context
    generated_by_agent = Column(String(100), nullable=False)
    generation_prompt = Column(Text)  # Prompt used to generate file
    generation_config = Column(JSON, default={})
    
    # Quality metrics
    lines_of_code = Column(Integer)
    complexity_score = Column(Float)
    maintainability_score = Column(Float)
    test_coverage = Column(Float)
    
    # Validation results
    syntax_valid = Column(Boolean)
    lint_score = Column(Float)
    security_issues = Column(JSON, default=[])
    
    # Timestamps
    created_date = Column(DateTime, default=datetime.utcnow, nullable=False)
    modified_date = Column(DateTime, default=datetime.utcnow, onupdate=datetime.utcnow)
    
    # Metadata
    metadata = Column(JSON, default={})
    tags = Column(JSON, default=[])  # Tags for categorization
    
    # Relationships
    children = relationship("GeneratedFile", backref="parent", remote_side=[id])
    
    def __repr__(self):
        return f"<GeneratedFile(id='{self.id}', filename='{self.filename}', type='{self.file_type}')>"


class SystemMetrics(Base):
    """
    System metrics model for tracking application performance and usage.
    
    Stores aggregate metrics about agent performance, workflow success rates,
    and system resource usage.
    """
    __tablename__ = "system_metrics"
    
    # Primary identification
    id = Column(UUID(as_uuid=True), primary_key=True, default=uuid.uuid4)
    metric_name = Column(String(100), nullable=False)
    metric_category = Column(String(50), nullable=False)  # agent, workflow, system, usage
    
    # Metric data
    metric_value = Column(Float, nullable=False)
    metric_unit = Column(String(20))  # seconds, bytes, percentage, count, etc.
    
    # Context
    context = Column(JSON, default={})  # Additional context data
    tags = Column(JSON, default=[])  # Tags for filtering and grouping
    
    # Timing
    timestamp = Column(DateTime, default=datetime.utcnow, nullable=False)
    period_start = Column(DateTime)  # For aggregate metrics
    period_end = Column(DateTime)
    
    # Metadata
    source = Column(String(100))  # Source of the metric
    metadata = Column(JSON, default={})
    
    def __repr__(self):
        return f"<SystemMetrics(name='{self.metric_name}', value={self.metric_value}, timestamp='{self.timestamp}')>"


# Index definitions for better query performance
from sqlalchemy import Index

# Document indexes
Index("idx_documents_status", Document.status)
Index("idx_documents_upload_date", Document.upload_date)
Index("idx_documents_file_type", Document.file_type)

# Workflow indexes
Index("idx_workflows_status", Workflow.status)
Index("idx_workflows_document_id", Workflow.document_id)
Index("idx_workflows_created_date", Workflow.created_date)
Index("idx_workflows_workflow_type", Workflow.workflow_type)

# Agent execution indexes
Index("idx_agent_executions_workflow_id", AgentExecution.workflow_id)
Index("idx_agent_executions_agent_name", AgentExecution.agent_name)
Index("idx_agent_executions_status", AgentExecution.status)
Index("idx_agent_executions_start_time", AgentExecution.start_time)

# Human approval indexes
Index("idx_human_approvals_workflow_id", HumanApproval.workflow_id)
Index("idx_human_approvals_status", HumanApproval.status)
Index("idx_human_approvals_requested_date", HumanApproval.requested_date)

# Generated file indexes
Index("idx_generated_files_workflow_id", GeneratedFile.workflow_id)
Index("idx_generated_files_file_type", GeneratedFile.file_type)
Index("idx_generated_files_is_latest", GeneratedFile.is_latest)
Index("idx_generated_files_generated_by_agent", GeneratedFile.generated_by_agent)

# System metrics indexes
Index("idx_system_metrics_metric_name", SystemMetrics.metric_name)
Index("idx_system_metrics_category", SystemMetrics.metric_category)
Index("idx_system_metrics_timestamp", SystemMetrics.timestamp)


async def create_tables():
    """
    Create all database tables.
    
    This function creates all tables defined in the models.
    Should be called during application startup.
    """
    try:
        from backend.database import engine
        
        # Import all models to ensure they're registered
        import backend.models.database
        
        # Create tables
        Base.metadata.create_all(bind=engine)
        
        logger.info("Database tables created successfully")
        
    except Exception as e:
        logger.error(f"Failed to create database tables: {e}")
        raise


async def drop_tables():
    """
    Drop all database tables.
    
    Warning: This will delete all data! Use with caution.
    """
    try:
        from backend.database import engine
        
        Base.metadata.drop_all(bind=engine)
        
        logger.warning("All database tables dropped")
        
    except Exception as e:
        logger.error(f"Failed to drop database tables: {e}")
        raise