"""
Base agent classes and interfaces for the SRS to Angular+FastAPI generator.

This module defines the abstract base classes and common interfaces
that all agents must implement.
"""

import asyncio
import time
from abc import ABC, abstractmethod
from typing import Dict, List, Optional, Any, Union
from dataclasses import dataclass, field
from datetime import datetime
from enum import Enum
import sys
import os

# Add project root to path
sys.path.append(os.path.dirname(os.path.dirname(os.path.abspath(__file__))))

from config.config import settings, AgentConfig
from utils.logger import get_logger, log_agent_activity, AgentActivityLogger
from utils.exceptions import AgentExecutionError, ValidationError, TimeoutError


class AgentStatus(str, Enum):
    """Agent execution status enumeration."""
    IDLE = "idle"
    BUSY = "busy"
    ERROR = "error"
    DISABLED = "disabled"


class AgentCategory(str, Enum):
    """Agent category enumeration."""
    REQUIREMENTS = "requirements"
    BACKEND = "backend"
    FRONTEND = "frontend"
    TESTING = "testing"
    INTEGRATION = "integration"


@dataclass
class AgentResult:
    """
    Result returned by agent execution.
    
    Contains the agent output, metadata, and execution information.
    """
    success: bool
    data: Dict[str, Any] = field(default_factory=dict)
    files_generated: List[str] = field(default_factory=list)
    error: Optional[str] = None
    execution_time: Optional[float] = None
    metadata: Dict[str, Any] = field(default_factory=dict)
    requires_approval: bool = False
    approval_content: Optional[Dict[str, Any]] = None


@dataclass
class AgentCapabilities:
    """
    Agent capabilities and requirements definition.
    
    Defines what an agent can do and what it needs to function.
    """
    name: str
    description: str
    category: AgentCategory
    version: str
    capabilities: List[str]
    dependencies: List[str] = field(default_factory=list)
    input_requirements: List[str] = field(default_factory=list)
    output_types: List[str] = field(default_factory=list)
    max_execution_time: int = 300  # seconds
    memory_limit_mb: int = 512
    requires_human_approval: bool = False


class BaseAgent(ABC):
    """
    Abstract base class for all agents.
    
    Provides common functionality and defines the interface
    that all agents must implement.
    """
    
    def __init__(self, capabilities: AgentCapabilities):
        """
        Initialize the base agent.
        
        Args:
            capabilities: Agent capabilities definition
        """
        self.capabilities = capabilities
        self.status = AgentStatus.IDLE
        self.logger = get_logger(f"agents.{capabilities.name}")
        self.activity_logger = AgentActivityLogger(capabilities.name)
        
        # Performance tracking
        self.execution_count = 0
        self.success_count = 0
        self.total_execution_time = 0.0
        self.last_execution_time = None
        
        # Configuration from settings
        agent_timeouts = AgentConfig.get_agent_timeouts(settings)
        self.max_retries = agent_timeouts["max_retries"]
        self.execution_timeout = agent_timeouts["execution_timeout"]
        
        # Agent-specific configuration
        self.config = self._load_configuration()
        
        self.logger.info(f"Agent {self.capabilities.name} initialized")
    
    @abstractmethod
    async def execute(self, inputs: Dict[str, Any]) -> AgentResult:
        """
        Execute the agent with given inputs.
        
        Args:
            inputs: Input data for the agent
            
        Returns:
            AgentResult: Agent execution result
        """
        pass
    
    @abstractmethod
    def validate_inputs(self, inputs: Dict[str, Any]) -> bool:
        """
        Validate input data before execution.
        
        Args:
            inputs: Input data to validate
            
        Returns:
            bool: True if inputs are valid, False otherwise
        """
        pass
    
    def _load_configuration(self) -> Dict[str, Any]:
        """
        Load agent-specific configuration.
        
        Returns:
            dict: Agent configuration
        """
        # Default configuration
        config = {
            "llm_config": AgentConfig.get_llm_config(settings),
            "max_retries": self.max_retries,
            "timeout": self.execution_timeout,
        }
        
        # Load agent-specific config if available
        # This could be extended to load from files or external sources
        return config
    
    async def run(self, inputs: Dict[str, Any], workflow_id: Optional[str] = None) -> AgentResult:
        """
        Run the agent with comprehensive error handling and logging.
        
        Args:
            inputs: Input data for the agent
            workflow_id: Optional workflow ID for tracking
            
        Returns:
            AgentResult: Agent execution result
        """
        if self.status == AgentStatus.DISABLED:
            raise AgentExecutionError(
                "Agent is disabled",
                agent_name=self.capabilities.name
            )
        
        if self.status == AgentStatus.BUSY:
            raise AgentExecutionError(
                "Agent is already busy",
                agent_name=self.capabilities.name
            )
        
        # Validate inputs
        if not self.validate_inputs(inputs):
            raise ValidationError(
                "Invalid input data provided to agent",
                validation_type="agent_input",
                details={"agent": self.capabilities.name, "inputs": str(inputs)[:1000]}
            )
        
        # Set status to busy
        self.status = AgentStatus.BUSY
        start_time = time.time()
        
        # Start activity logging
        self.activity_logger.start_execution(
            task="agent_execution",
            workflow_id=workflow_id,
            inputs=inputs
        )
        
        try:
            # Execute with timeout
            result = await asyncio.wait_for(
                self.execute(inputs),
                timeout=self.execution_timeout
            )
            
            # Record successful execution
            end_time = time.time()
            execution_time = end_time - start_time
            
            self.execution_count += 1
            if result.success:
                self.success_count += 1
            self.total_execution_time += execution_time
            self.last_execution_time = datetime.utcnow()
            
            # Update result with execution time
            result.execution_time = execution_time
            
            # Log successful completion
            self.activity_logger.end_execution(
                status="success" if result.success else "failed",
                result={"files_generated": len(result.files_generated)}
            )
            
            self.logger.info(
                f"Agent {self.capabilities.name} completed execution",
                execution_time=execution_time,
                success=result.success,
                files_generated=len(result.files_generated)
            )
            
            return result
            
        except asyncio.TimeoutError:
            # Handle timeout
            self.execution_count += 1
            execution_time = time.time() - start_time
            self.total_execution_time += execution_time
            
            error_msg = f"Agent execution timed out after {self.execution_timeout} seconds"
            self.activity_logger.log_error(
                TimeoutError(error_msg, self.capabilities.name, self.execution_timeout)
            )
            self.activity_logger.end_execution("timeout")
            
            self.logger.error(error_msg, execution_time=execution_time)
            
            raise TimeoutError(
                error_msg,
                agent_name=self.capabilities.name,
                timeout_duration=self.execution_timeout
            )
            
        except Exception as e:
            # Handle other errors
            self.execution_count += 1
            execution_time = time.time() - start_time
            self.total_execution_time += execution_time
            
            self.activity_logger.log_error(e, {"execution_time": execution_time})
            self.activity_logger.end_execution("failed", {"error": str(e)})
            
            self.logger.error(
                f"Agent {self.capabilities.name} execution failed: {e}",
                execution_time=execution_time,
                error_type=type(e).__name__
            )
            
            if isinstance(e, AgentExecutionError):
                raise
            else:
                raise AgentExecutionError(
                    f"Agent execution failed: {e}",
                    agent_name=self.capabilities.name,
                    execution_stage="execution"
                )
        
        finally:
            # Reset status
            self.status = AgentStatus.IDLE
    
    async def retry_execution(self, inputs: Dict[str, Any], max_retries: Optional[int] = None) -> AgentResult:
        """
        Execute agent with retry logic.
        
        Args:
            inputs: Input data for the agent
            max_retries: Maximum number of retries (overrides default)
            
        Returns:
            AgentResult: Agent execution result
        """
        retries = max_retries or self.max_retries
        last_error = None
        
        for attempt in range(retries + 1):
            try:
                self.activity_logger.log_decision(
                    f"execution_attempt_{attempt + 1}",
                    f"Attempting execution (attempt {attempt + 1}/{retries + 1})",
                    f"Starting execution attempt {attempt + 1}",
                    alternatives=[f"attempt_{i}" for i in range(1, retries + 2)],
                    confidence=1.0 - (attempt * 0.1)  # Decreasing confidence with retries
                )
                
                result = await self.run(inputs)
                
                if result.success:
                    return result
                else:
                    # If execution "succeeded" but result indicates failure
                    last_error = AgentExecutionError(
                        result.error or "Agent execution returned failure",
                        agent_name=self.capabilities.name,
                        retry_count=attempt
                    )
                    
                    if attempt < retries:
                        self.logger.warning(
                            f"Agent execution attempt {attempt + 1} failed, retrying...",
                            error=result.error
                        )
                        await asyncio.sleep(2 ** attempt)  # Exponential backoff
                    
            except Exception as e:
                last_error = e
                
                if attempt < retries:
                    self.logger.warning(
                        f"Agent execution attempt {attempt + 1} failed, retrying...",
                        error=str(e)
                    )
                    await asyncio.sleep(2 ** attempt)  # Exponential backoff
                else:
                    self.logger.error(
                        f"Agent execution failed after {retries + 1} attempts",
                        final_error=str(e)
                    )
        
        # All retries exhausted
        if last_error:
            raise last_error
        else:
            raise AgentExecutionError(
                f"Agent execution failed after {retries + 1} attempts",
                agent_name=self.capabilities.name,
                retry_count=retries
            )
    
    def get_status(self) -> Dict[str, Any]:
        """
        Get current agent status and performance metrics.
        
        Returns:
            dict: Agent status information
        """
        success_rate = (self.success_count / self.execution_count) if self.execution_count > 0 else 0.0
        avg_execution_time = (self.total_execution_time / self.execution_count) if self.execution_count > 0 else 0.0
        
        return {
            "name": self.capabilities.name,
            "status": self.status.value,
            "category": self.capabilities.category.value,
            "description": self.capabilities.description,
            "version": self.capabilities.version,
            "capabilities": self.capabilities.capabilities,
            "execution_count": self.execution_count,
            "success_count": self.success_count,
            "success_rate": success_rate,
            "total_execution_time": self.total_execution_time,
            "average_execution_time": avg_execution_time,
            "last_execution_time": self.last_execution_time.isoformat() if self.last_execution_time else None,
            "max_execution_time": self.capabilities.max_execution_time,
            "requires_human_approval": self.capabilities.requires_human_approval
        }
    
    def reset_metrics(self):
        """Reset performance metrics."""
        self.execution_count = 0
        self.success_count = 0
        self.total_execution_time = 0.0
        self.last_execution_time = None
        
        self.logger.info(f"Agent {self.capabilities.name} metrics reset")
    
    def enable(self):
        """Enable the agent."""
        if self.status == AgentStatus.DISABLED:
            self.status = AgentStatus.IDLE
            self.logger.info(f"Agent {self.capabilities.name} enabled")
    
    def disable(self):
        """Disable the agent."""
        if self.status != AgentStatus.BUSY:
            self.status = AgentStatus.DISABLED
            self.logger.info(f"Agent {self.capabilities.name} disabled")
    
    def __repr__(self):
        return f"<{self.__class__.__name__}(name='{self.capabilities.name}', status='{self.status}')>"


class LLMAgent(BaseAgent):
    """
    Base class for agents that use Large Language Models.
    
    Provides common LLM functionality and prompt management.
    """
    
    def __init__(self, capabilities: AgentCapabilities):
        """Initialize LLM agent."""
        super().__init__(capabilities)
        
        # LLM configuration
        self.llm_config = self.config["llm_config"]
        self.llm_client = self._initialize_llm_client()
    
    def _initialize_llm_client(self):
        """
        Initialize LLM client based on configuration.
        
        Returns:
            LLM client instance
        """
        provider = self.llm_config["provider"]
        
        if provider == "openai":
            try:
                import openai
                return openai.AsyncOpenAI(api_key=self.llm_config["api_key"])
            except ImportError:
                self.logger.error("OpenAI client not available. Install with: pip install openai")
                return None
        
        elif provider == "anthropic":
            try:
                import anthropic
                return anthropic.AsyncAnthropic(api_key=self.llm_config["api_key"])
            except ImportError:
                self.logger.error("Anthropic client not available. Install with: pip install anthropic")
                return None
        
        else:
            self.logger.error(f"Unsupported LLM provider: {provider}")
            return None
    
    async def call_llm(self, prompt: str, system_prompt: Optional[str] = None) -> str:
        """
        Call the LLM with a prompt.
        
        Args:
            prompt: User prompt
            system_prompt: Optional system prompt
            
        Returns:
            str: LLM response
        """
        if not self.llm_client:
            raise AgentExecutionError(
                "LLM client not initialized",
                agent_name=self.capabilities.name
            )
        
        try:
            provider = self.llm_config["provider"]
            
            if provider == "openai":
                messages = []
                if system_prompt:
                    messages.append({"role": "system", "content": system_prompt})
                messages.append({"role": "user", "content": prompt})
                
                response = await self.llm_client.chat.completions.create(
                    model=self.llm_config["model"],
                    messages=messages,
                    temperature=self.llm_config["temperature"],
                    max_tokens=self.llm_config["max_tokens"]
                )
                
                return response.choices[0].message.content
            
            elif provider == "anthropic":
                # Anthropic API call
                response = await self.llm_client.messages.create(
                    model=self.llm_config["model"],
                    system=system_prompt or "",
                    messages=[{"role": "user", "content": prompt}],
                    temperature=self.llm_config["temperature"],
                    max_tokens=self.llm_config["max_tokens"]
                )
                
                return response.content[0].text
            
            else:
                raise AgentExecutionError(
                    f"Unsupported LLM provider: {provider}",
                    agent_name=self.capabilities.name
                )
                
        except Exception as e:
            self.logger.error(f"LLM call failed: {e}")
            raise AgentExecutionError(
                f"LLM call failed: {e}",
                agent_name=self.capabilities.name,
                execution_stage="llm_call"
            )
    
    def build_prompt(self, template: str, **kwargs) -> str:
        """
        Build a prompt from a template with variables.
        
        Args:
            template: Prompt template with placeholders
            **kwargs: Variables to substitute in template
            
        Returns:
            str: Formatted prompt
        """
        try:
            return template.format(**kwargs)
        except KeyError as e:
            raise ValidationError(
                f"Missing template variable: {e}",
                validation_type="prompt_template",
                field_name=str(e)
            )


# Agent decorator for automatic registration
def agent(category: AgentCategory, capabilities: List[str], **kwargs):
    """
    Decorator to automatically register an agent.
    
    Args:
        category: Agent category
        capabilities: List of agent capabilities
        **kwargs: Additional agent metadata
    """
    def decorator(cls):
        # This would be used by the registry to auto-register agents
        cls._agent_category = category
        cls._agent_capabilities = capabilities
        cls._agent_metadata = kwargs
        return cls
    
    return decorator