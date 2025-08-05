"""
Agent Registry for the SRC to Application Generator.

This module implements a plugin-based system for registering, discovering,
and managing agent workflows throughout the application generation process.
"""

import inspect
from abc import ABC, abstractmethod
from datetime import datetime
from typing import Any, Dict, List, Optional, Type, Callable
from dataclasses import dataclass, field
from enum import Enum

from utils.logging_config import LoggerMixin, log_agent_event
from utils.exceptions import AgentError, ValidationError


class AgentStatus(Enum):
    """Agent execution status enumeration."""
    AVAILABLE = "available"
    RUNNING = "running"
    BUSY = "busy"
    ERROR = "error"
    DISABLED = "disabled"


class AgentCapability(Enum):
    """Agent capability types."""
    DOCUMENT_ANALYSIS = "document_analysis"
    SRD_GENERATION = "srd_generation"
    API_DESIGN = "api_design"
    MODEL_GENERATION = "model_generation"
    COMPONENT_SCAFFOLDING = "component_scaffolding"
    CODE_REVIEW = "code_review"
    SECURITY_ANALYSIS = "security_analysis"
    TEST_GENERATION = "test_generation"
    PERFORMANCE_ANALYSIS = "performance_analysis"


@dataclass
class AgentMetadata:
    """Metadata for registered agents."""
    
    name: str
    description: str
    version: str
    capabilities: List[AgentCapability]
    dependencies: List[str] = field(default_factory=list)
    timeout_seconds: int = 300
    max_retries: int = 3
    requires_human_approval: bool = False
    tags: List[str] = field(default_factory=list)


@dataclass
class AgentExecutionContext:
    """Context information for agent execution."""
    
    execution_id: str
    agent_id: str
    input_data: Dict[str, Any]
    options: Dict[str, Any] = field(default_factory=dict)
    started_at: Optional[datetime] = None
    user_id: Optional[str] = None
    project_id: Optional[str] = None


@dataclass
class AgentExecutionResult:
    """Result of agent execution."""
    
    execution_id: str
    agent_id: str
    status: str
    started_at: datetime
    completed_at: Optional[datetime] = None
    duration_seconds: Optional[float] = None
    output_data: Optional[Dict[str, Any]] = None
    error: Optional[str] = None
    logs: List[Dict[str, Any]] = field(default_factory=list)
    metrics: Dict[str, Any] = field(default_factory=dict)


class BaseAgent(ABC, LoggerMixin):
    """
    Abstract base class for all agents in the system.
    
    All agents must inherit from this class and implement the required methods.
    """
    
    def __init__(self, metadata: AgentMetadata):
        self.metadata = metadata
        self.status = AgentStatus.AVAILABLE
        self.execution_count = 0
        self.success_count = 0
        self.last_execution = None
        
    @abstractmethod
    async def execute(self, context: AgentExecutionContext) -> AgentExecutionResult:
        """
        Execute the agent with the given context.
        
        Args:
            context: Execution context containing input data and options
            
        Returns:
            AgentExecutionResult with output data and execution metadata
            
        Raises:
            AgentError: If execution fails
        """
        pass
    
    @abstractmethod
    def validate_input(self, input_data: Dict[str, Any]) -> bool:
        """
        Validate input data before execution.
        
        Args:
            input_data: Input data to validate
            
        Returns:
            True if input is valid
            
        Raises:
            ValidationError: If input is invalid
        """
        pass
    
    async def pre_execute(self, context: AgentExecutionContext) -> None:
        """Hook called before execution starts."""
        self.status = AgentStatus.RUNNING
        self.execution_count += 1
        self.last_execution = datetime.utcnow()
        
        log_agent_event(
            self.metadata.name,
            "PRE_EXECUTE",
            f"Starting execution for {context.execution_id}",
            {"execution_id": context.execution_id}
        )
    
    async def post_execute(self, context: AgentExecutionContext, result: AgentExecutionResult) -> None:
        """Hook called after execution completes."""
        self.status = AgentStatus.AVAILABLE
        
        if result.status == "completed":
            self.success_count += 1
        
        log_agent_event(
            self.metadata.name,
            "POST_EXECUTE",
            f"Completed execution for {context.execution_id}",
            {
                "execution_id": context.execution_id,
                "status": result.status,
                "duration": result.duration_seconds
            }
        )
    
    async def handle_error(self, context: AgentExecutionContext, error: Exception) -> AgentExecutionResult:
        """Handle execution errors and create error result."""
        self.status = AgentStatus.ERROR
        
        error_msg = str(error)
        self.log_error(
            f"Agent execution failed: {error_msg}",
            execution_id=context.execution_id,
            error_type=type(error).__name__
        )
        
        log_agent_event(
            self.metadata.name,
            "ERROR",
            f"Execution failed for {context.execution_id}: {error_msg}",
            {
                "execution_id": context.execution_id,
                "error": error_msg,
                "error_type": type(error).__name__
            }
        )
        
        return AgentExecutionResult(
            execution_id=context.execution_id,
            agent_id=context.agent_id,
            status="failed",
            started_at=context.started_at or datetime.utcnow(),
            completed_at=datetime.utcnow(),
            error=error_msg
        )
    
    @property
    def success_rate(self) -> float:
        """Calculate agent success rate."""
        if self.execution_count == 0:
            return 0.0
        return self.success_count / self.execution_count
    
    def to_dict(self) -> Dict[str, Any]:
        """Convert agent to dictionary representation."""
        return {
            "name": self.metadata.name,
            "description": self.metadata.description,
            "version": self.metadata.version,
            "capabilities": [cap.value for cap in self.metadata.capabilities],
            "status": self.status.value,
            "execution_count": self.execution_count,
            "success_count": self.success_count,
            "success_rate": self.success_rate,
            "last_execution": self.last_execution.isoformat() if self.last_execution else None,
            "timeout_seconds": self.metadata.timeout_seconds,
            "requires_human_approval": self.metadata.requires_human_approval,
            "tags": self.metadata.tags
        }


class AgentRegistry(LoggerMixin):
    """
    Registry for managing all agents in the system.
    
    Provides functionality to register, discover, and execute agents
    with proper error handling and monitoring.
    """
    
    def __init__(self):
        self._agents: Dict[str, BaseAgent] = {}
        self._execution_history: Dict[str, AgentExecutionResult] = {}
        self._hooks: Dict[str, List[Callable]] = {
            "pre_register": [],
            "post_register": [],
            "pre_execute": [],
            "post_execute": []
        }
        
        self.log_info("Agent registry initialized")
    
    def register_agent(self, agent_id: str, agent: BaseAgent) -> None:
        """
        Register an agent in the registry.
        
        Args:
            agent_id: Unique identifier for the agent
            agent: Agent instance to register
            
        Raises:
            ValueError: If agent_id is already registered
        """
        if agent_id in self._agents:
            raise ValueError(f"Agent with ID '{agent_id}' is already registered")
        
        # Run pre-register hooks
        for hook in self._hooks["pre_register"]:
            hook(agent_id, agent)
        
        self._agents[agent_id] = agent
        
        # Run post-register hooks
        for hook in self._hooks["post_register"]:
            hook(agent_id, agent)
        
        self.log_info(
            f"Agent registered successfully",
            agent_id=agent_id,
            agent_name=agent.metadata.name,
            capabilities=[cap.value for cap in agent.metadata.capabilities]
        )
    
    def unregister_agent(self, agent_id: str) -> None:
        """
        Unregister an agent from the registry.
        
        Args:
            agent_id: ID of the agent to unregister
            
        Raises:
            KeyError: If agent_id is not found
        """
        if agent_id not in self._agents:
            raise KeyError(f"Agent with ID '{agent_id}' not found")
        
        agent = self._agents[agent_id]
        
        # Check if agent is currently running
        if agent.status == AgentStatus.RUNNING:
            raise ValueError(f"Cannot unregister running agent '{agent_id}'")
        
        del self._agents[agent_id]
        
        self.log_info(
            f"Agent unregistered successfully",
            agent_id=agent_id,
            agent_name=agent.metadata.name
        )
    
    def get_agent(self, agent_id: str) -> BaseAgent:
        """
        Get an agent by ID.
        
        Args:
            agent_id: ID of the agent to retrieve
            
        Returns:
            Agent instance
            
        Raises:
            KeyError: If agent_id is not found
        """
        if agent_id not in self._agents:
            raise KeyError(f"Agent with ID '{agent_id}' not found")
        
        return self._agents[agent_id]
    
    def list_agents(self, capability: Optional[AgentCapability] = None,
                   status: Optional[AgentStatus] = None,
                   tags: Optional[List[str]] = None) -> List[Dict[str, Any]]:
        """
        List registered agents with optional filtering.
        
        Args:
            capability: Filter by agent capability
            status: Filter by agent status
            tags: Filter by agent tags
            
        Returns:
            List of agent information dictionaries
        """
        agents = []
        
        for agent_id, agent in self._agents.items():
            # Apply filters
            if capability and capability not in agent.metadata.capabilities:
                continue
            
            if status and agent.status != status:
                continue
            
            if tags and not any(tag in agent.metadata.tags for tag in tags):
                continue
            
            agent_info = agent.to_dict()
            agent_info["agent_id"] = agent_id
            agents.append(agent_info)
        
        return agents
    
    def get_agents_by_capability(self, capability: AgentCapability) -> List[str]:
        """
        Get agent IDs that have a specific capability.
        
        Args:
            capability: Capability to search for
            
        Returns:
            List of agent IDs
        """
        return [
            agent_id for agent_id, agent in self._agents.items()
            if capability in agent.metadata.capabilities
        ]
    
    async def execute_agent(self, agent_id: str, input_data: Dict[str, Any],
                          options: Optional[Dict[str, Any]] = None,
                          execution_id: Optional[str] = None) -> AgentExecutionResult:
        """
        Execute an agent with the provided input.
        
        Args:
            agent_id: ID of the agent to execute
            input_data: Input data for the agent
            options: Optional execution options
            execution_id: Optional custom execution ID
            
        Returns:
            AgentExecutionResult with execution details
            
        Raises:
            KeyError: If agent_id is not found
            AgentError: If agent execution fails
        """
        import uuid
        
        if agent_id not in self._agents:
            raise KeyError(f"Agent with ID '{agent_id}' not found")
        
        agent = self._agents[agent_id]
        
        # Check agent status
        if agent.status not in [AgentStatus.AVAILABLE, AgentStatus.ERROR]:
            raise AgentError(
                f"Agent '{agent_id}' is not available (status: {agent.status.value})",
                agent_id
            )
        
        # Create execution context
        execution_id = execution_id or str(uuid.uuid4())
        context = AgentExecutionContext(
            execution_id=execution_id,
            agent_id=agent_id,
            input_data=input_data,
            options=options or {},
            started_at=datetime.utcnow()
        )
        
        try:
            # Validate input
            agent.validate_input(input_data)
            
            # Run pre-execute hooks
            for hook in self._hooks["pre_execute"]:
                await hook(context)
            
            # Execute agent
            await agent.pre_execute(context)
            result = await agent.execute(context)
            await agent.post_execute(context, result)
            
            # Store execution result
            self._execution_history[execution_id] = result
            
            # Run post-execute hooks
            for hook in self._hooks["post_execute"]:
                await hook(context, result)
            
            self.log_info(
                f"Agent executed successfully",
                agent_id=agent_id,
                execution_id=execution_id,
                status=result.status,
                duration=result.duration_seconds
            )
            
            return result
            
        except Exception as e:
            # Handle execution error
            result = await agent.handle_error(context, e)
            self._execution_history[execution_id] = result
            
            return result
    
    def get_execution_result(self, execution_id: str) -> AgentExecutionResult:
        """
        Get the result of a previous execution.
        
        Args:
            execution_id: ID of the execution
            
        Returns:
            AgentExecutionResult
            
        Raises:
            KeyError: If execution_id is not found
        """
        if execution_id not in self._execution_history:
            raise KeyError(f"Execution with ID '{execution_id}' not found")
        
        return self._execution_history[execution_id]
    
    def list_executions(self, agent_id: Optional[str] = None,
                       limit: int = 100) -> List[AgentExecutionResult]:
        """
        List execution history with optional filtering.
        
        Args:
            agent_id: Filter by agent ID
            limit: Maximum number of results
            
        Returns:
            List of execution results
        """
        executions = list(self._execution_history.values())
        
        # Filter by agent_id if provided
        if agent_id:
            executions = [e for e in executions if e.agent_id == agent_id]
        
        # Sort by start time (most recent first)
        executions.sort(key=lambda x: x.started_at, reverse=True)
        
        return executions[:limit]
    
    def add_hook(self, hook_type: str, hook_func: Callable) -> None:
        """
        Add a hook function to be called at specific events.
        
        Args:
            hook_type: Type of hook (pre_register, post_register, pre_execute, post_execute)
            hook_func: Function to call
        """
        if hook_type not in self._hooks:
            raise ValueError(f"Invalid hook type: {hook_type}")
        
        self._hooks[hook_type].append(hook_func)
        
        self.log_info(f"Hook added for {hook_type}")
    
    def get_registry_stats(self) -> Dict[str, Any]:
        """
        Get registry statistics.
        
        Returns:
            Dictionary with registry statistics
        """
        total_agents = len(self._agents)
        available_agents = len([a for a in self._agents.values() if a.status == AgentStatus.AVAILABLE])
        running_agents = len([a for a in self._agents.values() if a.status == AgentStatus.RUNNING])
        
        total_executions = len(self._execution_history)
        successful_executions = len([e for e in self._execution_history.values() if e.status == "completed"])
        
        return {
            "total_agents": total_agents,
            "available_agents": available_agents,
            "running_agents": running_agents,
            "total_executions": total_executions,
            "successful_executions": successful_executions,
            "success_rate": successful_executions / total_executions if total_executions > 0 else 0,
            "capabilities": list(set(
                cap.value for agent in self._agents.values()
                for cap in agent.metadata.capabilities
            ))
        }


# Global agent registry instance
agent_registry = AgentRegistry()


def get_agent_registry() -> AgentRegistry:
    """Get the global agent registry instance."""
    return agent_registry