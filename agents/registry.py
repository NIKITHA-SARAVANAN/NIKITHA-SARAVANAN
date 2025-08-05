"""
Agent registry and plugin system for the SRS to Angular+FastAPI generator.

This module provides the central registry for managing all agents,
their lifecycle, and plugin-based discovery.
"""

import asyncio
import importlib
import inspect
from typing import Dict, List, Optional, Any, Type, Set
from pathlib import Path
import sys
import os

# Add project root to path
sys.path.append(os.path.dirname(os.path.dirname(os.path.abspath(__file__))))

from agents.base import BaseAgent, AgentCapabilities, AgentCategory, AgentStatus
from utils.logger import get_logger
from utils.exceptions import AgentExecutionError, ProcessingError


class AgentRegistry:
    """
    Central registry for managing all agents in the system.
    
    Provides agent discovery, registration, lifecycle management,
    and execution coordination.
    """
    
    def __init__(self):
        """Initialize the agent registry."""
        self.logger = get_logger(__name__)
        
        # Agent storage
        self._agents: Dict[str, BaseAgent] = {}
        self._agent_classes: Dict[str, Type[BaseAgent]] = {}
        self._categories: Dict[AgentCategory, List[str]] = {
            category: [] for category in AgentCategory
        }
        
        # Plugin system
        self._plugin_directories: List[Path] = []
        self._discovered_plugins: Set[str] = set()
        
        # Registry state
        self._initialized = False
        
        self.logger.info("Agent registry initialized")
    
    async def initialize(self, plugin_directories: Optional[List[str]] = None):
        """
        Initialize the registry and discover agents.
        
        Args:
            plugin_directories: Additional directories to search for agent plugins
        """
        if self._initialized:
            self.logger.warning("Agent registry already initialized")
            return
        
        try:
            # Set up plugin directories
            self._setup_plugin_directories(plugin_directories)
            
            # Discover and register built-in agents
            await self._discover_builtin_agents()
            
            # Discover and register plugin agents
            await self._discover_plugin_agents()
            
            # Initialize all agents
            await self._initialize_agents()
            
            self._initialized = True
            
            self.logger.info(
                f"Agent registry initialized with {len(self._agents)} agents",
                agent_count=len(self._agents),
                categories={cat.value: len(agents) for cat, agents in self._categories.items()}
            )
            
        except Exception as e:
            self.logger.error(f"Failed to initialize agent registry: {e}")
            raise ProcessingError(f"Agent registry initialization failed: {e}")
    
    def _setup_plugin_directories(self, additional_dirs: Optional[List[str]] = None):
        """Setup plugin discovery directories."""
        # Default plugin directories
        current_dir = Path(__file__).parent
        self._plugin_directories = [
            current_dir,  # agents/ directory
            current_dir / "requirements",  # requirements agents
            current_dir / "backend",  # backend agents
            current_dir / "frontend",  # frontend agents
            current_dir / "testing",  # testing agents
        ]
        
        # Add additional directories
        if additional_dirs:
            for dir_path in additional_dirs:
                path = Path(dir_path)
                if path.exists() and path.is_dir():
                    self._plugin_directories.append(path)
                else:
                    self.logger.warning(f"Plugin directory not found: {dir_path}")
    
    async def _discover_builtin_agents(self):
        """Discover and register built-in agents."""
        # Import built-in agent modules
        builtin_modules = [
            "agents.requirements",
            "agents.backend.api_designer",
            "agents.backend.model_developer", 
            "agents.backend.business_logic",
            "agents.backend.integration",
            "agents.backend.database_migration",
            "agents.frontend.component_designer",
            "agents.frontend.service_developer",
            "agents.frontend.ui_implementation",
            "agents.frontend.state_management",
            "agents.frontend.router",
            "agents.testing.test_generator",
            "agents.testing.code_review"
        ]
        
        for module_name in builtin_modules:
            try:
                await self._discover_agents_in_module(module_name)
            except ImportError as e:
                self.logger.debug(f"Built-in module not found: {module_name} - {e}")
            except Exception as e:
                self.logger.error(f"Error discovering agents in {module_name}: {e}")
    
    async def _discover_plugin_agents(self):
        """Discover agents in plugin directories."""
        for plugin_dir in self._plugin_directories:
            if not plugin_dir.exists():
                continue
            
            # Find all Python files in the directory
            for py_file in plugin_dir.rglob("*.py"):
                if py_file.name.startswith("_"):
                    continue  # Skip private files
                
                # Convert file path to module name
                relative_path = py_file.relative_to(plugin_dir.parent)
                module_name = ".".join(relative_path.with_suffix("").parts)
                
                if module_name in self._discovered_plugins:
                    continue
                
                self._discovered_plugins.add(module_name)
                
                try:
                    await self._discover_agents_in_module(module_name)
                except Exception as e:
                    self.logger.error(f"Error discovering agents in {module_name}: {e}")
    
    async def _discover_agents_in_module(self, module_name: str):
        """Discover agents in a specific module."""
        try:
            module = importlib.import_module(module_name)
            
            # Find all classes that inherit from BaseAgent
            for name, obj in inspect.getmembers(module, inspect.isclass):
                if (issubclass(obj, BaseAgent) and 
                    obj != BaseAgent and 
                    not inspect.isabstract(obj)):
                    
                    # Register the agent class
                    agent_name = getattr(obj, '_agent_name', name)
                    self._agent_classes[agent_name] = obj
                    
                    self.logger.debug(f"Discovered agent class: {agent_name} in {module_name}")
                    
        except ImportError as e:
            self.logger.debug(f"Could not import module {module_name}: {e}")
        except Exception as e:
            self.logger.error(f"Error discovering agents in module {module_name}: {e}")
    
    async def _initialize_agents(self):
        """Initialize all discovered agent classes."""
        for agent_name, agent_class in self._agent_classes.items():
            try:
                # Create agent instance
                agent_instance = agent_class()
                
                # Register the agent
                await self.register_agent(agent_instance)
                
            except Exception as e:
                self.logger.error(f"Failed to initialize agent {agent_name}: {e}")
    
    async def register_agent(self, agent: BaseAgent):
        """
        Register an agent instance.
        
        Args:
            agent: Agent instance to register
        """
        agent_name = agent.capabilities.name
        
        if agent_name in self._agents:
            self.logger.warning(f"Agent {agent_name} already registered, replacing...")
        
        # Register the agent
        self._agents[agent_name] = agent
        
        # Add to category list
        category = agent.capabilities.category
        if agent_name not in self._categories[category]:
            self._categories[category].append(agent_name)
        
        self.logger.info(f"Agent registered: {agent_name} ({category.value})")
    
    async def unregister_agent(self, agent_name: str):
        """
        Unregister an agent.
        
        Args:
            agent_name: Name of the agent to unregister
        """
        if agent_name not in self._agents:
            self.logger.warning(f"Agent {agent_name} not found for unregistration")
            return
        
        agent = self._agents[agent_name]
        
        # Remove from main registry
        del self._agents[agent_name]
        
        # Remove from category list
        category = agent.capabilities.category
        if agent_name in self._categories[category]:
            self._categories[category].remove(agent_name)
        
        self.logger.info(f"Agent unregistered: {agent_name}")
    
    def get_agent(self, agent_name: str) -> Optional[BaseAgent]:
        """
        Get an agent by name.
        
        Args:
            agent_name: Name of the agent
            
        Returns:
            BaseAgent instance or None if not found
        """
        return self._agents.get(agent_name)
    
    def list_agents(self, category: Optional[AgentCategory] = None, 
                   status: Optional[AgentStatus] = None) -> List[BaseAgent]:
        """
        List agents with optional filtering.
        
        Args:
            category: Filter by category
            status: Filter by status
            
        Returns:
            List of matching agents
        """
        agents = list(self._agents.values())
        
        if category:
            agents = [agent for agent in agents if agent.capabilities.category == category]
        
        if status:
            agents = [agent for agent in agents if agent.status == status]
        
        return agents
    
    def get_agent_names(self, category: Optional[AgentCategory] = None) -> List[str]:
        """
        Get list of agent names.
        
        Args:
            category: Filter by category
            
        Returns:
            List of agent names
        """
        if category:
            return self._categories[category].copy()
        else:
            return list(self._agents.keys())
    
    def get_categories(self) -> Dict[AgentCategory, List[str]]:
        """
        Get agents organized by category.
        
        Returns:
            Dictionary mapping categories to agent lists
        """
        return {cat: agents.copy() for cat, agents in self._categories.items()}
    
    async def execute_agent(self, agent_name: str, inputs: Dict[str, Any], 
                          workflow_id: Optional[str] = None) -> Any:
        """
        Execute an agent by name.
        
        Args:
            agent_name: Name of the agent to execute
            inputs: Input data for the agent
            workflow_id: Optional workflow ID for tracking
            
        Returns:
            Agent execution result
        """
        agent = self.get_agent(agent_name)
        if not agent:
            raise AgentExecutionError(
                f"Agent not found: {agent_name}",
                agent_name=agent_name
            )
        
        try:
            return await agent.run(inputs, workflow_id)
        except Exception as e:
            self.logger.error(f"Agent execution failed: {agent_name} - {e}")
            raise
    
    async def execute_agent_with_retry(self, agent_name: str, inputs: Dict[str, Any],
                                     max_retries: Optional[int] = None) -> Any:
        """
        Execute an agent with retry logic.
        
        Args:
            agent_name: Name of the agent to execute
            inputs: Input data for the agent
            max_retries: Maximum number of retries
            
        Returns:
            Agent execution result
        """
        agent = self.get_agent(agent_name)
        if not agent:
            raise AgentExecutionError(
                f"Agent not found: {agent_name}",
                agent_name=agent_name
            )
        
        try:
            return await agent.retry_execution(inputs, max_retries)
        except Exception as e:
            self.logger.error(f"Agent retry execution failed: {agent_name} - {e}")
            raise
    
    def enable_agent(self, agent_name: str):
        """
        Enable an agent.
        
        Args:
            agent_name: Name of the agent to enable
        """
        agent = self.get_agent(agent_name)
        if agent:
            agent.enable()
            self.logger.info(f"Agent enabled: {agent_name}")
        else:
            self.logger.warning(f"Agent not found for enabling: {agent_name}")
    
    def disable_agent(self, agent_name: str):
        """
        Disable an agent.
        
        Args:
            agent_name: Name of the agent to disable
        """
        agent = self.get_agent(agent_name)
        if agent:
            agent.disable()
            self.logger.info(f"Agent disabled: {agent_name}")
        else:
            self.logger.warning(f"Agent not found for disabling: {agent_name}")
    
    def get_registry_status(self) -> Dict[str, Any]:
        """
        Get registry status and statistics.
        
        Returns:
            Dictionary containing registry information
        """
        total_agents = len(self._agents)
        available_agents = len([a for a in self._agents.values() if a.status == AgentStatus.IDLE])
        busy_agents = len([a for a in self._agents.values() if a.status == AgentStatus.BUSY])
        error_agents = len([a for a in self._agents.values() if a.status == AgentStatus.ERROR])
        disabled_agents = len([a for a in self._agents.values() if a.status == AgentStatus.DISABLED])
        
        category_counts = {
            category.value: len(agents) for category, agents in self._categories.items()
        }
        
        return {
            "initialized": self._initialized,
            "total_agents": total_agents,
            "available_agents": available_agents,
            "busy_agents": busy_agents,
            "error_agents": error_agents,
            "disabled_agents": disabled_agents,
            "categories": category_counts,
            "discovered_plugins": len(self._discovered_plugins),
            "plugin_directories": [str(d) for d in self._plugin_directories]
        }
    
    def get_agent_status_list(self) -> List[Dict[str, Any]]:
        """
        Get detailed status for all agents.
        
        Returns:
            List of agent status dictionaries
        """
        return [agent.get_status() for agent in self._agents.values()]
    
    async def health_check(self) -> Dict[str, Any]:
        """
        Perform a health check on all agents.
        
        Returns:
            Health check results
        """
        healthy_agents = 0
        unhealthy_agents = 0
        agent_health = {}
        
        for agent_name, agent in self._agents.items():
            try:
                # Simple health check - verify agent is not in error state
                if agent.status != AgentStatus.ERROR:
                    healthy_agents += 1
                    agent_health[agent_name] = "healthy"
                else:
                    unhealthy_agents += 1
                    agent_health[agent_name] = "unhealthy"
                    
            except Exception as e:
                unhealthy_agents += 1
                agent_health[agent_name] = f"error: {e}"
        
        return {
            "healthy_agents": healthy_agents,
            "unhealthy_agents": unhealthy_agents,
            "total_agents": len(self._agents),
            "health_percentage": (healthy_agents / len(self._agents)) * 100 if self._agents else 100,
            "agent_health": agent_health
        }
    
    async def shutdown(self):
        """Shutdown the registry and cleanup resources."""
        self.logger.info("Shutting down agent registry...")
        
        # Disable all agents
        for agent in self._agents.values():
            try:
                agent.disable()
            except Exception as e:
                self.logger.error(f"Error disabling agent {agent.capabilities.name}: {e}")
        
        # Clear registry
        self._agents.clear()
        self._agent_classes.clear()
        for category_list in self._categories.values():
            category_list.clear()
        
        self._initialized = False
        
        self.logger.info("Agent registry shutdown completed")


# Global registry instance
_agent_registry: Optional[AgentRegistry] = None


async def get_agent_registry() -> AgentRegistry:
    """
    Get the global agent registry instance.
    
    Returns:
        AgentRegistry: Global registry instance
    """
    global _agent_registry
    
    if _agent_registry is None:
        _agent_registry = AgentRegistry()
        await _agent_registry.initialize()
    
    return _agent_registry


async def initialize_agent_registry(plugin_directories: Optional[List[str]] = None) -> AgentRegistry:
    """
    Initialize the global agent registry.
    
    Args:
        plugin_directories: Additional plugin directories
        
    Returns:
        AgentRegistry: Initialized registry instance
    """
    global _agent_registry
    
    if _agent_registry is not None:
        await _agent_registry.shutdown()
    
    _agent_registry = AgentRegistry()
    await _agent_registry.initialize(plugin_directories)
    
    return _agent_registry


async def shutdown_agent_registry():
    """Shutdown the global agent registry."""
    global _agent_registry
    
    if _agent_registry is not None:
        await _agent_registry.shutdown()
        _agent_registry = None