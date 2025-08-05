"""
Base agent class with common functionality for all agents in the system.
"""

import logging
import json
from abc import ABC, abstractmethod
from datetime import datetime
from typing import Dict, Any, List, Optional
from dataclasses import dataclass, field
import uuid

logger = logging.getLogger(__name__)


@dataclass
class AgentAction:
    """Represents an action taken by an agent."""
    action_id: str = field(default_factory=lambda: str(uuid.uuid4()))
    agent_name: str = ""
    action_type: str = ""
    timestamp: datetime = field(default_factory=datetime.now)
    input_data: Dict[str, Any] = field(default_factory=dict)
    output_data: Dict[str, Any] = field(default_factory=dict)
    success: bool = True
    error_message: str = ""
    execution_time_ms: int = 0


@dataclass
class AgentLog:
    """Comprehensive logging for agent decisions and actions."""
    session_id: str
    agent_name: str
    actions: List[AgentAction] = field(default_factory=list)
    decision_tree: Dict[str, Any] = field(default_factory=dict)
    metadata: Dict[str, Any] = field(default_factory=dict)


class BaseAgent(ABC):
    """Base class for all agents in the multi-agent system."""
    
    def __init__(self, name: str, config: Optional[Dict[str, Any]] = None):
        """
        Initialize the base agent.
        
        Args:
            name: Name of the agent
            config: Configuration dictionary for the agent
        """
        self.name = name
        self.config = config or {}
        self.logger = logging.getLogger(f"agent.{name}")
        self.session_id = str(uuid.uuid4())
        self.agent_log = AgentLog(session_id=self.session_id, agent_name=name)
        
    @abstractmethod
    def process(self, input_data: Dict[str, Any]) -> Dict[str, Any]:
        """
        Process input data and return results.
        
        Args:
            input_data: Input data for processing
            
        Returns:
            Dictionary containing processing results
        """
        pass
    
    def log_action(self, action_type: str, input_data: Dict[str, Any], 
                   output_data: Dict[str, Any], success: bool = True, 
                   error_message: str = "", execution_time_ms: int = 0) -> str:
        """
        Log an agent action.
        
        Args:
            action_type: Type of action performed
            input_data: Input data for the action
            output_data: Output data from the action
            success: Whether the action was successful
            error_message: Error message if action failed
            execution_time_ms: Execution time in milliseconds
            
        Returns:
            Action ID
        """
        action = AgentAction(
            agent_name=self.name,
            action_type=action_type,
            input_data=input_data,
            output_data=output_data,
            success=success,
            error_message=error_message,
            execution_time_ms=execution_time_ms
        )
        
        self.agent_log.actions.append(action)
        
        self.logger.info(f"Action logged: {action_type} - Success: {success}")
        if not success:
            self.logger.error(f"Action failed: {error_message}")
            
        return action.action_id
    
    def add_decision(self, decision_point: str, options: List[str], 
                     chosen_option: str, reasoning: str):
        """
        Add a decision to the decision tree.
        
        Args:
            decision_point: Description of the decision point
            options: Available options
            chosen_option: The chosen option
            reasoning: Reasoning for the choice
        """
        decision_id = str(uuid.uuid4())
        decision = {
            'id': decision_id,
            'timestamp': datetime.now().isoformat(),
            'decision_point': decision_point,
            'options': options,
            'chosen_option': chosen_option,
            'reasoning': reasoning
        }
        
        if 'decisions' not in self.agent_log.decision_tree:
            self.agent_log.decision_tree['decisions'] = []
        
        self.agent_log.decision_tree['decisions'].append(decision)
        
        self.logger.info(f"Decision logged: {decision_point} -> {chosen_option}")
    
    def get_log_summary(self) -> Dict[str, Any]:
        """Get a summary of the agent's log."""
        return {
            'session_id': self.session_id,
            'agent_name': self.name,
            'total_actions': len(self.agent_log.actions),
            'successful_actions': sum(1 for a in self.agent_log.actions if a.success),
            'failed_actions': sum(1 for a in self.agent_log.actions if not a.success),
            'decisions_made': len(self.agent_log.decision_tree.get('decisions', [])),
            'session_start': min((a.timestamp for a in self.agent_log.actions), default=datetime.now()).isoformat(),
            'last_action': max((a.timestamp for a in self.agent_log.actions), default=datetime.now()).isoformat()
        }
    
    def export_log(self) -> str:
        """Export the complete agent log as JSON."""
        def serialize_datetime(obj):
            if isinstance(obj, datetime):
                return obj.isoformat()
            raise TypeError(f"Object of type {type(obj)} is not JSON serializable")
        
        return json.dumps(self.agent_log, default=serialize_datetime, indent=2)
    
    def validate_input(self, input_data: Dict[str, Any], required_keys: List[str]) -> bool:
        """
        Validate that input data contains required keys.
        
        Args:
            input_data: Input data to validate
            required_keys: List of required keys
            
        Returns:
            True if valid, False otherwise
        """
        missing_keys = [key for key in required_keys if key not in input_data]
        
        if missing_keys:
            self.logger.error(f"Missing required keys: {missing_keys}")
            return False
        
        return True
    
    def handle_error(self, error: Exception, context: str = "") -> Dict[str, Any]:
        """
        Handle errors in a consistent way.
        
        Args:
            error: The exception that occurred
            context: Additional context about where the error occurred
            
        Returns:
            Error response dictionary
        """
        error_msg = f"Error in {self.name}"
        if context:
            error_msg += f" ({context})"
        error_msg += f": {str(error)}"
        
        self.logger.error(error_msg, exc_info=True)
        
        return {
            'success': False,
            'error': error_msg,
            'error_type': type(error).__name__,
            'agent': self.name,
            'context': context
        }