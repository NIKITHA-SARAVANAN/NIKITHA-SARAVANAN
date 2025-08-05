"""
Model Developer Agent for generating Pydantic models with validation.
"""

import time
from typing import Dict, Any, List
import re

from ..base_agent import BaseAgent


class ModelDeveloperAgent(BaseAgent):
    """Agent responsible for developing Pydantic data models."""
    
    def __init__(self, config: Dict[str, Any] = None):
        """Initialize the Model Developer agent."""
        super().__init__("ModelDeveloperAgent", config)
        
    def process(self, input_data: Dict[str, Any]) -> Dict[str, Any]:
        """
        Process SRD and generate Pydantic models.
        
        Args:
            input_data: Dictionary containing SRD data and API requirements
            
        Returns:
            Generated Pydantic models with validation
        """
        start_time = time.time()
        
        try:
            # Validate input
            if not self.validate_input(input_data, ['backend_srd']):
                return self.handle_error(ValueError("Missing required 'backend_srd' in input"), "input_validation")
            
            backend_srd = input_data['backend_srd']
            api_requirements = input_data.get('api_requirements', [])
            
            # Extract data models from SRD
            models = self._extract_data_models(backend_srd)
            
            # Generate Pydantic models
            pydantic_models = self._generate_pydantic_models(models)
            
            # Generate database models (SQLAlchemy)
            db_models = self._generate_database_models(models)
            
            # Generate validation rules
            validators = self._generate_validators(models)
            
            result = {
                'models': models,
                'pydantic_models': pydantic_models,
                'db_models': db_models,
                'validators': validators
            }
            
            # Log action
            execution_time = int((time.time() - start_time) * 1000)
            self.log_action(
                "develop_models",
                {"backend_srd_length": len(backend_srd)},
                {"models_count": len(models)},
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
                "develop_models",
                input_data,
                {},
                success=False,
                error_message=str(e),
                execution_time_ms=execution_time
            )
            return self.handle_error(e, "model_development")
    
    def _extract_data_models(self, backend_srd: str) -> List[Dict[str, Any]]:
        """Extract data model requirements from SRD."""
        models = []
        
        # Common entity patterns
        entity_patterns = [
            r'(?i)user(?:s)?',
            r'(?i)account(?:s)?', 
            r'(?i)product(?:s)?',
            r'(?i)order(?:s)?',
            r'(?i)item(?:s)?',
            r'(?i)customer(?:s)?',
            r'(?i)transaction(?:s)?',
            r'(?i)document(?:s)?',
            r'(?i)file(?:s)?',
            r'(?i)report(?:s)?'
        ]
        
        srd_lower = backend_srd.lower()
        
        for pattern in entity_patterns:
            matches = re.findall(pattern, srd_lower)
            if matches:
                entity_name = matches[0].rstrip('s').capitalize()
                
                # Define common fields based on entity type
                fields = self._get_common_fields(entity_name.lower())
                
                models.append({
                    'name': entity_name,
                    'fields': fields,
                    'relationships': [],
                    'validations': self._get_common_validations(entity_name.lower())
                })
        
        # Always include base models
        if not any(m['name'] == 'User' for m in models):
            models.append({
                'name': 'User',
                'fields': [
                    {'name': 'id', 'type': 'int', 'required': False, 'primary_key': True},
                    {'name': 'username', 'type': 'str', 'required': True, 'unique': True},
                    {'name': 'email', 'type': 'EmailStr', 'required': True, 'unique': True},
                    {'name': 'password_hash', 'type': 'str', 'required': True},
                    {'name': 'is_active', 'type': 'bool', 'required': False, 'default': True},
                    {'name': 'created_at', 'type': 'datetime', 'required': False, 'auto_now_add': True},
                    {'name': 'updated_at', 'type': 'datetime', 'required': False, 'auto_now': True}
                ],
                'relationships': [],
                'validations': ['username_length', 'email_format', 'password_strength']
            })
        
        return models
    
    def _get_common_fields(self, entity_type: str) -> List[Dict[str, Any]]:
        """Get common fields for entity types."""
        base_fields = [
            {'name': 'id', 'type': 'int', 'required': False, 'primary_key': True},
            {'name': 'created_at', 'type': 'datetime', 'required': False, 'auto_now_add': True},
            {'name': 'updated_at', 'type': 'datetime', 'required': False, 'auto_now': True}
        ]
        
        entity_fields = {
            'user': [
                {'name': 'username', 'type': 'str', 'required': True, 'unique': True},
                {'name': 'email', 'type': 'EmailStr', 'required': True, 'unique': True},
                {'name': 'password_hash', 'type': 'str', 'required': True},
                {'name': 'is_active', 'type': 'bool', 'required': False, 'default': True}
            ],
            'product': [
                {'name': 'name', 'type': 'str', 'required': True},
                {'name': 'description', 'type': 'str', 'required': False},
                {'name': 'price', 'type': 'Decimal', 'required': True},
                {'name': 'stock_quantity', 'type': 'int', 'required': False, 'default': 0},
                {'name': 'is_available', 'type': 'bool', 'required': False, 'default': True}
            ],
            'order': [
                {'name': 'user_id', 'type': 'int', 'required': True, 'foreign_key': 'users.id'},
                {'name': 'total_amount', 'type': 'Decimal', 'required': True},
                {'name': 'status', 'type': 'str', 'required': True, 'default': 'pending'},
                {'name': 'order_date', 'type': 'datetime', 'required': True, 'auto_now_add': True}
            ]
        }
        
        return base_fields + entity_fields.get(entity_type, [
            {'name': 'name', 'type': 'str', 'required': True},
            {'name': 'description', 'type': 'str', 'required': False}
        ])
    
    def _get_common_validations(self, entity_type: str) -> List[str]:
        """Get common validations for entity types."""
        validations = {
            'user': ['username_length', 'email_format', 'password_strength'],
            'product': ['name_length', 'price_positive'],
            'order': ['amount_positive', 'status_choices']
        }
        
        return validations.get(entity_type, ['name_length'])
    
    def _generate_pydantic_models(self, models: List[Dict[str, Any]]) -> str:
        """Generate Pydantic model definitions."""
        imports = [
            "from pydantic import BaseModel, EmailStr, validator, Field",
            "from typing import Optional, List, Union",
            "from datetime import datetime",
            "from decimal import Decimal",
            "import re"
        ]
        
        model_definitions = []
        
        for model in models:
            # Base model
            base_fields = []
            create_fields = []
            update_fields = []
            response_fields = []
            
            for field in model['fields']:
                field_def = self._generate_field_definition(field)
                
                if not field.get('primary_key') and not field.get('auto_now_add') and not field.get('auto_now'):
                    base_fields.append(field_def)
                
                if field.get('required') and not field.get('primary_key'):
                    create_fields.append(field_def)
                elif not field.get('primary_key'):
                    update_fields.append(f"    {field['name']}: Optional[{field['type']}] = None")
                
                response_fields.append(field_def)
            
            # Generate model classes
            model_name = model['name']
            
            # Base model
            model_definitions.extend([
                f"class {model_name}Base(BaseModel):",
                f'    """Base {model_name.lower()} model."""'
            ])
            model_definitions.extend(base_fields or ["    pass"])
            model_definitions.append("")
            
            # Create model
            model_definitions.extend([
                f"class {model_name}Create({model_name}Base):",
                f'    """Create {model_name.lower()} model."""'
            ])
            model_definitions.extend(create_fields or ["    pass"])
            
            # Add validators for create model
            for validation in model.get('validations', []):
                validator_code = self._generate_validator(validation, model_name)
                if validator_code:
                    model_definitions.extend(["", validator_code])
            
            model_definitions.append("")
            
            # Update model  
            model_definitions.extend([
                f"class {model_name}Update(BaseModel):",
                f'    """Update {model_name.lower()} model."""'
            ])
            model_definitions.extend(update_fields or ["    pass"])
            model_definitions.append("")
            
            # Response model
            model_definitions.extend([
                f"class {model_name}({model_name}Base):",
                f'    """{model_name} response model."""'
            ])
            model_definitions.extend(response_fields)
            model_definitions.extend([
                "",
                "    class Config:",
                "        from_attributes = True",
                ""
            ])
        
        return "\n".join(imports + ["", ""] + model_definitions)
    
    def _generate_field_definition(self, field: Dict[str, Any]) -> str:
        """Generate field definition for Pydantic model."""
        field_type = field['type']
        field_name = field['name']
        
        if field.get('required', True):
            if field.get('default') is not None:
                return f"    {field_name}: {field_type} = {repr(field['default'])}"
            else:
                return f"    {field_name}: {field_type}"
        else:
            default = field.get('default', 'None')
            return f"    {field_name}: Optional[{field_type}] = {default}"
    
    def _generate_validator(self, validation: str, model_name: str) -> str:
        """Generate Pydantic validator."""
        validators = {
            'username_length': """    @validator('username')
    def validate_username(cls, v):
        if len(v) < 3 or len(v) > 50:
            raise ValueError('Username must be between 3 and 50 characters')
        return v""",
            
            'email_format': """    @validator('email')
    def validate_email(cls, v):
        # Additional email validation beyond EmailStr
        if len(v) > 254:
            raise ValueError('Email address too long')
        return v""",
            
            'password_strength': """    @validator('password')
    def validate_password(cls, v):
        if len(v) < 8:
            raise ValueError('Password must be at least 8 characters long')
        if not re.search(r'[A-Z]', v):
            raise ValueError('Password must contain at least one uppercase letter')
        if not re.search(r'[a-z]', v):
            raise ValueError('Password must contain at least one lowercase letter')
        if not re.search(r'\\d', v):
            raise ValueError('Password must contain at least one digit')
        return v""",
            
            'name_length': """    @validator('name')
    def validate_name(cls, v):
        if len(v) < 1 or len(v) > 255:
            raise ValueError('Name must be between 1 and 255 characters')
        return v""",
            
            'price_positive': """    @validator('price')
    def validate_price(cls, v):
        if v <= 0:
            raise ValueError('Price must be positive')
        return v""",
            
            'amount_positive': """    @validator('total_amount')
    def validate_amount(cls, v):
        if v <= 0:
            raise ValueError('Amount must be positive')
        return v"""
        }
        
        return validators.get(validation, "")
    
    def _generate_database_models(self, models: List[Dict[str, Any]]) -> str:
        """Generate SQLAlchemy database models."""
        imports = [
            "from sqlalchemy import Column, Integer, String, Boolean, DateTime, ForeignKey, Decimal, Text",
            "from sqlalchemy.ext.declarative import declarative_base", 
            "from sqlalchemy.orm import relationship",
            "from datetime import datetime"
        ]
        
        model_definitions = [
            "Base = declarative_base()",
            ""
        ]
        
        for model in models:
            model_name = model['name']
            table_name = f"{model_name.lower()}s"
            
            model_definitions.extend([
                f"class {model_name}(Base):",
                f'    """SQLAlchemy model for {model_name.lower()}."""',
                f"    __tablename__ = '{table_name}'",
                ""
            ])
            
            # Generate columns
            for field in model['fields']:
                column_def = self._generate_column_definition(field)
                model_definitions.append(f"    {column_def}")
            
            model_definitions.append("")
        
        return "\n".join(imports + ["", ""] + model_definitions)
    
    def _generate_column_definition(self, field: Dict[str, Any]) -> str:
        """Generate SQLAlchemy column definition."""
        field_name = field['name']
        field_type = field['type']
        
        # Map Pydantic types to SQLAlchemy types
        type_mapping = {
            'int': 'Integer',
            'str': 'String(255)',
            'EmailStr': 'String(255)',
            'bool': 'Boolean',
            'datetime': 'DateTime',
            'Decimal': 'Decimal(10, 2)',
            'Text': 'Text'
        }
        
        sql_type = type_mapping.get(field_type, 'String(255)')
        
        column_args = [sql_type]
        
        if field.get('primary_key'):
            column_args.append('primary_key=True')
        
        if field.get('unique'):
            column_args.append('unique=True')
        
        if field.get('required', True) and not field.get('primary_key'):
            column_args.append('nullable=False')
        
        if field.get('foreign_key'):
            fk = f"ForeignKey('{field['foreign_key']}')"
            column_args.insert(0, fk)
        
        if field.get('default') is not None:
            if field['type'] == 'datetime' and field.get('auto_now_add'):
                column_args.append('default=datetime.utcnow')
            else:
                column_args.append(f"default={repr(field['default'])}")
        
        return f"{field_name} = Column({', '.join(column_args)})"
    
    def _generate_validators(self, models: List[Dict[str, Any]]) -> str:
        """Generate custom validation functions."""
        validators = [
            "# Custom validation functions",
            "",
            "import re",
            "from typing import Any",
            "",
            "def validate_password_strength(password: str) -> bool:",
            '    """Validate password meets security requirements."""',
            "    if len(password) < 8:",
            "        return False",
            "    if not re.search(r'[A-Z]', password):",
            "        return False", 
            "    if not re.search(r'[a-z]', password):",
            "        return False",
            "    if not re.search(r'\\d', password):",
            "        return False",
            "    return True",
            "",
            "def validate_email_format(email: str) -> bool:",
            '    """Validate email format beyond basic checks."""',
            "    if len(email) > 254:",
            "        return False",
            "    pattern = r'^[a-zA-Z0-9._%+-]+@[a-zA-Z0-9.-]+\\.[a-zA-Z]{2,}$'",
            "    return bool(re.match(pattern, email))",
            ""
        ]
        
        return "\n".join(validators)