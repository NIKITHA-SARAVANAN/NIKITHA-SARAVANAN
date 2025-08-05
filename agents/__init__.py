"""
Multi-agent system package for the SRC to Application Generator.

This package contains all agent implementations, the agent registry,
and coordination logic for the multi-agent workflows.
"""

from .agent_registry import AgentRegistry

__all__ = ["AgentRegistry"]