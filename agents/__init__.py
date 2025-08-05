"""
Multi-agent system for SRS processing and code generation.
"""

from .requirements_analyzer import RequirementsAnalyzer
from .base_agent import BaseAgent

# Backend agents
from .backend import (
    APIDesignerAgent,
    ModelDeveloperAgent, 
    BusinessLogicAgent,
    IntegrationAgent,
    DatabaseMigrationAgent
)

# Frontend agents  
from .frontend import (
    ComponentDesignerAgent,
    ServiceDeveloperAgent,
    UIImplementationAgent,
    StateManagementAgent
)

__all__ = [
    # Core agents
    "RequirementsAnalyzer", 
    "BaseAgent",
    
    # Backend agents
    "APIDesignerAgent",
    "ModelDeveloperAgent",
    "BusinessLogicAgent", 
    "IntegrationAgent",
    "DatabaseMigrationAgent",
    
    # Frontend agents
    "ComponentDesignerAgent",
    "ServiceDeveloperAgent", 
    "UIImplementationAgent",
    "StateManagementAgent"
]