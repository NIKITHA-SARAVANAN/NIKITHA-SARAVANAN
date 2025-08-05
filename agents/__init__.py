"""
Agents package for the SRS to Angular+FastAPI generator.

This package contains all agent implementations, the agent registry,
and workflow orchestration logic.
"""

from .registry import AgentRegistry, get_agent_registry
from .base import BaseAgent, AgentResult
from .requirements import RequirementsAnalyzer

__all__ = [
    "AgentRegistry",
    "get_agent_registry", 
    "BaseAgent",
    "AgentResult",
    "RequirementsAnalyzer"
]