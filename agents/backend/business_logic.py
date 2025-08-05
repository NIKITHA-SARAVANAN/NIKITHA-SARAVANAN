"""
Business Logic Agent for implementing business rules and workflows.
"""

import time
from typing import Dict, Any, List
import re

from ..base_agent import BaseAgent


class BusinessLogicAgent(BaseAgent):
    """Agent responsible for implementing business logic and rules."""
    
    def __init__(self, config: Dict[str, Any] = None):
        """Initialize the Business Logic agent."""
        super().__init__("BusinessLogicAgent", config)
        
    def process(self, input_data: Dict[str, Any]) -> Dict[str, Any]:
        """
        Process SRD and generate business logic implementations.
        
        Args:
            input_data: Dictionary containing SRD data and models
            
        Returns:
            Generated business logic functions and classes
        """
        start_time = time.time()
        
        try:
            # Validate input
            if not self.validate_input(input_data, ['backend_srd']):
                return self.handle_error(ValueError("Missing required 'backend_srd' in input"), "input_validation")
            
            backend_srd = input_data['backend_srd']
            models = input_data.get('models', [])
            
            # Extract business rules
            business_rules = self._extract_business_rules(backend_srd)
            
            # Generate business logic services
            services = self._generate_business_services(business_rules, models)
            
            # Generate workflow implementations
            workflows = self._generate_workflows(business_rules)
            
            # Generate validation logic
            validators = self._generate_business_validators(business_rules)
            
            # Generate exception handlers
            exceptions = self._generate_business_exceptions(business_rules)
            
            result = {
                'business_rules': business_rules,
                'services': services,
                'workflows': workflows,
                'validators': validators,
                'exceptions': exceptions
            }
            
            # Log action
            execution_time = int((time.time() - start_time) * 1000)
            self.log_action(
                "implement_business_logic",
                {"backend_srd_length": len(backend_srd)},
                {"rules_count": len(business_rules), "services_count": len(services)},
                success=True,
                execution_time_ms=execution_time
            )
            
            return {
                'success': True,
                'result': result,
                'execution_time_ms': execution_time
            }
            
        except Exception as e:
            execution_time = int((time.time() - start_time) * 1000)
            self.log_action(
                "implement_business_logic",
                input_data,
                {},
                success=False,
                error_message=str(e),
                execution_time_ms=execution_time
            )
            return self.handle_error(e, "business_logic_implementation")
    
    def _extract_business_rules(self, backend_srd: str) -> List[Dict[str, Any]]:
        """Extract business rules from SRD."""
        rules = []
        
        # Common business rule patterns
        rule_patterns = {
            'validation': [
                r'(?i)(must|shall|should) (validate|check|verify)',
                r'(?i)(required|mandatory|compulsory)',
                r'(?i)(minimum|maximum|range|limit)'
            ],
            'calculation': [
                r'(?i)(calculate|compute|determine)',
                r'(?i)(total|sum|average|percentage)',
                r'(?i)(formula|equation|algorithm)'
            ],
            'workflow': [
                r'(?i)(process|workflow|procedure)',
                r'(?i)(step|stage|phase)',
                r'(?i)(approve|reject|submit|review)'
            ],
            'authorization': [
                r'(?i)(authorize|permission|access)',
                r'(?i)(role|user type|admin)',
                r'(?i)(allowed|denied|restricted)'
            ],
            'notification': [
                r'(?i)(notify|alert|send)',
                r'(?i)(email|message|notification)',
                r'(?i)(trigger|event|when)'
            ]
        }
        
        srd_lines = backend_srd.split('\n')
        
        for line_num, line in enumerate(srd_lines):
            line_lower = line.lower().strip()
            if not line_lower:
                continue
                
            for rule_type, patterns in rule_patterns.items():
                for pattern in patterns:
                    if re.search(pattern, line_lower):
                        rules.append({
                            'type': rule_type,
                            'description': line.strip(),
                            'line_number': line_num + 1,
                            'priority': self._determine_priority(line_lower),
                            'complexity': self._determine_complexity(line_lower)
                        })
                        break
        
        # Add default business rules
        default_rules = [
            {
                'type': 'validation',
                'description': 'Validate user input data',
                'priority': 'high',
                'complexity': 'low'
            },
            {
                'type': 'authorization',
                'description': 'Check user permissions',
                'priority': 'high',
                'complexity': 'medium'
            },
            {
                'type': 'workflow',
                'description': 'Handle CRUD operations',
                'priority': 'medium',
                'complexity': 'low'
            }
        ]
        
        # Add default rules if not found
        for default_rule in default_rules:
            if not any(r['type'] == default_rule['type'] for r in rules):
                rules.append(default_rule)
        
        return rules
    
    def _determine_priority(self, text: str) -> str:
        """Determine priority based on keywords."""
        high_keywords = ['critical', 'essential', 'required', 'must', 'shall']
        medium_keywords = ['should', 'recommended', 'important']
        
        if any(keyword in text for keyword in high_keywords):
            return 'high'
        elif any(keyword in text for keyword in medium_keywords):
            return 'medium'
        else:
            return 'low'
    
    def _determine_complexity(self, text: str) -> str:
        """Determine complexity based on keywords."""
        high_keywords = ['complex', 'algorithm', 'multiple', 'integration']
        medium_keywords = ['calculation', 'workflow', 'process']
        
        if any(keyword in text for keyword in high_keywords):
            return 'high'
        elif any(keyword in text for keyword in medium_keywords):
            return 'medium'
        else:
            return 'low'
    
    def _generate_business_services(self, business_rules: List[Dict[str, Any]], models: List[Dict[str, Any]]) -> List[Dict[str, Any]]:
        """Generate business service classes."""
        services = []
        
        # Group rules by type
        rules_by_type = {}
        for rule in business_rules:
            rule_type = rule['type']
            if rule_type not in rules_by_type:
                rules_by_type[rule_type] = []
            rules_by_type[rule_type].append(rule)
        
        # Generate services for each rule type
        for rule_type, type_rules in rules_by_type.items():
            service_name = f"{rule_type.title()}Service"
            
            methods = []
            for rule in type_rules:
                method = self._generate_service_method(rule, models)
                methods.append(method)
            
            services.append({
                'name': service_name,
                'type': rule_type,
                'methods': methods,
                'dependencies': self._get_service_dependencies(rule_type)
            })
        
        return services
    
    def _generate_service_method(self, rule: Dict[str, Any], models: List[Dict[str, Any]]) -> Dict[str, Any]:
        """Generate a service method for a business rule."""
        rule_type = rule['type']
        
        method_templates = {
            'validation': {
                'name': 'validate_data',
                'params': ['data: Dict[str, Any]'],
                'return_type': 'bool',
                'body': self._generate_validation_method_body(rule)
            },
            'calculation': {
                'name': 'calculate_value',
                'params': ['input_data: Dict[str, Any]'],
                'return_type': 'float',
                'body': self._generate_calculation_method_body(rule)
            },
            'workflow': {
                'name': 'process_workflow',
                'params': ['entity_id: int', 'action: str'],
                'return_type': 'Dict[str, Any]',
                'body': self._generate_workflow_method_body(rule)
            },
            'authorization': {
                'name': 'check_permission',
                'params': ['user_id: int', 'resource: str', 'action: str'],
                'return_type': 'bool',
                'body': self._generate_authorization_method_body(rule)
            },
            'notification': {
                'name': 'send_notification',
                'params': ['recipient: str', 'message: str', 'type: str'],
                'return_type': 'bool',
                'body': self._generate_notification_method_body(rule)
            }
        }
        
        template = method_templates.get(rule_type, method_templates['validation'])
        
        return {
            'name': template['name'],
            'params': template['params'],
            'return_type': template['return_type'],
            'body': template['body'],
            'description': rule['description'],
            'async': rule.get('complexity', 'low') == 'high'
        }
    
    def _generate_validation_method_body(self, rule: Dict[str, Any]) -> str:
        """Generate validation method body."""
        return '''        """
        Validate business data according to rules.
        
        Args:
            data: Data to validate
            
        Returns:
            True if valid, False otherwise
            
        Raises:
            ValidationError: If validation fails
        """
        try:
            # TODO: Implement specific validation logic
            if not data:
                return False
            
            # Add specific validation rules here
            return True
            
        except Exception as e:
            self.logger.error(f"Validation failed: {e}")
            raise ValidationError(f"Data validation failed: {e}")'''
    
    def _generate_calculation_method_body(self, rule: Dict[str, Any]) -> str:
        """Generate calculation method body."""
        return '''        """
        Perform business calculations.
        
        Args:
            input_data: Input data for calculation
            
        Returns:
            Calculated result
            
        Raises:
            CalculationError: If calculation fails
        """
        try:
            # TODO: Implement specific calculation logic
            result = 0.0
            
            # Add calculation logic here
            
            return result
            
        except Exception as e:
            self.logger.error(f"Calculation failed: {e}")
            raise CalculationError(f"Calculation failed: {e}")'''
    
    def _generate_workflow_method_body(self, rule: Dict[str, Any]) -> str:
        """Generate workflow method body."""
        return '''        """
        Process business workflow.
        
        Args:
            entity_id: ID of entity to process
            action: Action to perform
            
        Returns:
            Workflow result
            
        Raises:
            WorkflowError: If workflow fails
        """
        try:
            # TODO: Implement specific workflow logic
            
            # Validate action
            valid_actions = ['create', 'update', 'delete', 'approve', 'reject']
            if action not in valid_actions:
                raise ValueError(f"Invalid action: {action}")
            
            # Process workflow
            result = {
                'entity_id': entity_id,
                'action': action,
                'status': 'completed',
                'timestamp': datetime.utcnow()
            }
            
            return result
            
        except Exception as e:
            self.logger.error(f"Workflow failed: {e}")
            raise WorkflowError(f"Workflow processing failed: {e}")'''
    
    def _generate_authorization_method_body(self, rule: Dict[str, Any]) -> str:
        """Generate authorization method body."""
        return '''        """
        Check user authorization.
        
        Args:
            user_id: User ID
            resource: Resource being accessed
            action: Action being performed
            
        Returns:
            True if authorized, False otherwise
        """
        try:
            # TODO: Implement authorization logic
            
            # Get user permissions
            # user_permissions = self.get_user_permissions(user_id)
            
            # Check if user has permission for resource and action
            # return self.has_permission(user_permissions, resource, action)
            
            # Placeholder implementation
            return True
            
        except Exception as e:
            self.logger.error(f"Authorization check failed: {e}")
            return False'''
    
    def _generate_notification_method_body(self, rule: Dict[str, Any]) -> str:
        """Generate notification method body."""
        return '''        """
        Send business notification.
        
        Args:
            recipient: Notification recipient
            message: Message content
            type: Notification type
            
        Returns:
            True if sent successfully, False otherwise
        """
        try:
            # TODO: Implement notification logic
            
            # Validate notification type
            valid_types = ['email', 'sms', 'push', 'in_app']
            if type not in valid_types:
                raise ValueError(f"Invalid notification type: {type}")
            
            # Send notification based on type
            # if type == 'email':
            #     return self.send_email(recipient, message)
            # elif type == 'sms':
            #     return self.send_sms(recipient, message)
            
            # Placeholder implementation
            self.logger.info(f"Notification sent to {recipient}: {message}")
            return True
            
        except Exception as e:
            self.logger.error(f"Notification failed: {e}")
            return False'''
    
    def _get_service_dependencies(self, rule_type: str) -> List[str]:
        """Get service dependencies for rule type."""
        dependencies = {
            'validation': ['logging', 'typing'],
            'calculation': ['logging', 'decimal', 'math'],
            'workflow': ['logging', 'datetime', 'typing'],
            'authorization': ['logging', 'typing'],
            'notification': ['logging', 'smtplib', 'typing']
        }
        
        return dependencies.get(rule_type, ['logging', 'typing'])
    
    def _generate_workflows(self, business_rules: List[Dict[str, Any]]) -> str:
        """Generate workflow implementations."""
        workflow_code = [
            "# Business Workflow Implementations",
            "",
            "from typing import Dict, Any, List",
            "from datetime import datetime",
            "import logging",
            "",
            "logger = logging.getLogger(__name__)",
            "",
            "class WorkflowEngine:",
            '    """Core workflow engine for business processes."""',
            "",
            "    def __init__(self):",
            "        self.workflows = {}",
            "        self.active_workflows = {}",
            "",
            "    def register_workflow(self, name: str, steps: List[Dict[str, Any]]):",
            '        """Register a new workflow."""',
            "        self.workflows[name] = steps",
            "        logger.info(f'Registered workflow: {name}')",
            "",
            "    def start_workflow(self, workflow_name: str, data: Dict[str, Any]) -> str:",
            '        """Start a workflow instance."""',
            "        if workflow_name not in self.workflows:",
            "            raise ValueError(f'Unknown workflow: {workflow_name}')",
            "",
            "        workflow_id = f'{workflow_name}_{datetime.utcnow().timestamp()}'",
            "        self.active_workflows[workflow_id] = {",
            "            'name': workflow_name,",
            "            'data': data,",
            "            'current_step': 0,",
            "            'status': 'running',",
            "            'started_at': datetime.utcnow()",
            "        }",
            "",
            "        return workflow_id",
            "",
            "    def execute_step(self, workflow_id: str) -> Dict[str, Any]:",
            '        """Execute the next step in a workflow."""',
            "        if workflow_id not in self.active_workflows:",
            "            raise ValueError(f'Unknown workflow instance: {workflow_id}')",
            "",
            "        workflow = self.active_workflows[workflow_id]",
            "        steps = self.workflows[workflow['name']]",
            "",
            "        if workflow['current_step'] >= len(steps):",
            "            workflow['status'] = 'completed'",
            "            return {'status': 'completed', 'result': workflow['data']}",
            "",
            "        current_step = steps[workflow['current_step']]",
            "        # Execute step logic here",
            "",
            "        workflow['current_step'] += 1",
            "        return {'status': 'step_completed', 'step': current_step}"
        ]
        
        return "\n".join(workflow_code)
    
    def _generate_business_validators(self, business_rules: List[Dict[str, Any]]) -> str:
        """Generate business validation functions."""
        validator_code = [
            "# Business Validation Functions",
            "",
            "from typing import Any, Dict, List",
            "import re",
            "",
            "class ValidationError(Exception):",
            '    """Custom validation error."""',
            "    pass",
            "",
            "class CalculationError(Exception):",
            '    """Custom calculation error."""',
            "    pass", 
            "",
            "class WorkflowError(Exception):",
            '    """Custom workflow error."""',
            "    pass",
            "",
            "def validate_business_rules(data: Dict[str, Any], rules: List[str]) -> bool:",
            '    """Validate data against business rules."""',
            "    for rule in rules:",
            "        if not eval(f'validate_{rule}(data)'):",
            "            return False",
            "    return True",
            "",
            "def validate_required_fields(data: Dict[str, Any]) -> bool:",
            '    """Validate required fields are present."""',
            "    required_fields = ['id', 'name']  # Add required fields",
            "    return all(field in data for field in required_fields)",
            "",
            "def validate_data_types(data: Dict[str, Any]) -> bool:",
            '    """Validate data types."""',
            "    # Add type validation logic",
            "    return True",
            "",
            "def validate_business_constraints(data: Dict[str, Any]) -> bool:",
            '    """Validate business constraints."""',
            "    # Add constraint validation logic", 
            "    return True"
        ]
        
        return "\n".join(validator_code)
    
    def _generate_business_exceptions(self, business_rules: List[Dict[str, Any]]) -> str:
        """Generate custom business exceptions."""
        exception_code = [
            "# Custom Business Exceptions",
            "",
            "class BusinessException(Exception):",
            '    """Base exception for business logic errors."""',
            "    def __init__(self, message: str, error_code: str = None):",
            "        super().__init__(message)",
            "        self.error_code = error_code",
            "",
            "class ValidationError(BusinessException):",
            '    """Exception raised when business validation fails."""',
            "    pass",
            "",
            "class CalculationError(BusinessException):",
            '    """Exception raised when business calculation fails."""',
            "    pass",
            "",
            "class WorkflowError(BusinessException):",
            '    """Exception raised when workflow processing fails."""',
            "    pass",
            "",
            "class AuthorizationError(BusinessException):",
            '    """Exception raised when authorization fails."""',
            "    pass",
            "",
            "class NotificationError(BusinessException):",
            '    """Exception raised when notification fails."""',
            "    pass"
        ]
        
        return "\n".join(exception_code)