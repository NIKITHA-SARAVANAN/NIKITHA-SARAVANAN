"""
API Designer Agent for generating FastAPI route skeletons and OpenAPI schemas.
"""

import time
from typing import Dict, Any, List
from pathlib import Path
import json

from ..base_agent import BaseAgent


class APIDesignerAgent(BaseAgent):
    """Agent responsible for designing API routes and OpenAPI schemas."""
    
    def __init__(self, config: Dict[str, Any] = None):
        """Initialize the API Designer agent."""
        super().__init__("APIDesignerAgent", config)
        
    def process(self, input_data: Dict[str, Any]) -> Dict[str, Any]:
        """
        Process SRD and generate FastAPI route skeletons.
        
        Args:
            input_data: Dictionary containing SRD data and requirements
            
        Returns:
            Generated API routes and schemas
        """
        start_time = time.time()
        
        try:
            # Validate input
            if not self.validate_input(input_data, ['backend_srd']):
                return self.handle_error(ValueError("Missing required 'backend_srd' in input"), "input_validation")
            
            backend_srd = input_data['backend_srd']
            dependencies = input_data.get('dependencies', [])
            
            # Extract API requirements
            api_requirements = self._extract_api_requirements(backend_srd)
            
            # Generate routes
            routes = self._generate_fastapi_routes(api_requirements)
            
            # Generate OpenAPI schema
            openapi_schema = self._generate_openapi_schema(api_requirements)
            
            # Generate main application file
            app_file = self._generate_app_file(routes)
            
            # Generate models file
            models_file = self._generate_models_file(api_requirements)
            
            # Log decision
            self.add_decision(
                "api_architecture_choice",
                ["RESTful", "GraphQL", "Hybrid"],
                "RESTful",
                "Chose RESTful architecture based on SRD requirements and FastAPI compatibility"
            )
            
            result = {
                'routes': routes,
                'openapi_schema': openapi_schema,
                'app_file': app_file,
                'models_file': models_file,
                'api_requirements': api_requirements
            }
            
            # Log action
            execution_time = int((time.time() - start_time) * 1000)
            self.log_action(
                "design_api",
                {"backend_srd_length": len(backend_srd)},
                {"routes_count": len(routes), "endpoints_count": sum(len(r['endpoints']) for r in routes)},
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
                "design_api",
                input_data,
                {},
                success=False,
                error_message=str(e),
                execution_time_ms=execution_time
            )
            return self.handle_error(e, "api_design")
    
    def _extract_api_requirements(self, backend_srd: str) -> List[Dict[str, Any]]:
        """Extract API requirements from backend SRD."""
        requirements = []
        
        # Common API patterns
        api_patterns = {
            'authentication': ['auth', 'login', 'register', 'token'],
            'user_management': ['user', 'profile', 'account'],
            'data_operations': ['create', 'read', 'update', 'delete', 'crud'],
            'file_operations': ['upload', 'download', 'file'],
            'search': ['search', 'filter', 'query'],
            'reporting': ['report', 'export', 'analytics']
        }
        
        srd_lower = backend_srd.lower()
        
        for category, keywords in api_patterns.items():
            if any(keyword in srd_lower for keyword in keywords):
                requirements.append({
                    'category': category,
                    'keywords': keywords,
                    'priority': 'high' if category in ['authentication', 'data_operations'] else 'medium'
                })
        
        return requirements
    
    def _generate_fastapi_routes(self, api_requirements: List[Dict[str, Any]]) -> List[Dict[str, Any]]:
        """Generate FastAPI route definitions."""
        routes = []
        
        # Authentication routes
        if any(req['category'] == 'authentication' for req in api_requirements):
            routes.append({
                'module': 'auth',
                'prefix': '/auth',
                'endpoints': [
                    {
                        'method': 'POST',
                        'path': '/login',
                        'function': 'login',
                        'description': 'User login endpoint'
                    },
                    {
                        'method': 'POST',
                        'path': '/register',
                        'function': 'register',
                        'description': 'User registration endpoint'
                    },
                    {
                        'method': 'POST',
                        'path': '/refresh',
                        'function': 'refresh_token',
                        'description': 'Token refresh endpoint'
                    },
                    {
                        'method': 'POST',
                        'path': '/logout',
                        'function': 'logout',
                        'description': 'User logout endpoint'
                    }
                ]
            })
        
        # User management routes
        if any(req['category'] == 'user_management' for req in api_requirements):
            routes.append({
                'module': 'users',
                'prefix': '/users',
                'endpoints': [
                    {
                        'method': 'GET',
                        'path': '/',
                        'function': 'get_users',
                        'description': 'Get all users'
                    },
                    {
                        'method': 'GET',
                        'path': '/{user_id}',
                        'function': 'get_user',
                        'description': 'Get user by ID'
                    },
                    {
                        'method': 'POST',
                        'path': '/',
                        'function': 'create_user',
                        'description': 'Create new user'
                    },
                    {
                        'method': 'PUT',
                        'path': '/{user_id}',
                        'function': 'update_user',
                        'description': 'Update user'
                    },
                    {
                        'method': 'DELETE',
                        'path': '/{user_id}',
                        'function': 'delete_user',
                        'description': 'Delete user'
                    }
                ]
            })
        
        # Data operations routes (generic CRUD)
        if any(req['category'] == 'data_operations' for req in api_requirements):
            routes.append({
                'module': 'data',
                'prefix': '/api/v1',
                'endpoints': [
                    {
                        'method': 'GET',
                        'path': '/items',
                        'function': 'get_items',
                        'description': 'Get all items'
                    },
                    {
                        'method': 'GET',
                        'path': '/items/{item_id}',
                        'function': 'get_item',
                        'description': 'Get item by ID'
                    },
                    {
                        'method': 'POST',
                        'path': '/items',
                        'function': 'create_item',
                        'description': 'Create new item'
                    },
                    {
                        'method': 'PUT',
                        'path': '/items/{item_id}',
                        'function': 'update_item',
                        'description': 'Update item'
                    },
                    {
                        'method': 'DELETE',
                        'path': '/items/{item_id}',
                        'function': 'delete_item',
                        'description': 'Delete item'
                    }
                ]
            })
        
        return routes
    
    def _generate_openapi_schema(self, api_requirements: List[Dict[str, Any]]) -> Dict[str, Any]:
        """Generate OpenAPI schema definition."""
        return {
            "openapi": "3.0.2",
            "info": {
                "title": "Generated API",
                "description": "API generated from SRS requirements",
                "version": "1.0.0"
            },
            "servers": [
                {
                    "url": "http://localhost:8000",
                    "description": "Development server"
                }
            ],
            "components": {
                "securitySchemes": {
                    "bearerAuth": {
                        "type": "http",
                        "scheme": "bearer",
                        "bearerFormat": "JWT"
                    }
                },
                "schemas": {
                    "User": {
                        "type": "object",
                        "properties": {
                            "id": {"type": "integer"},
                            "username": {"type": "string"},
                            "email": {"type": "string", "format": "email"},
                            "created_at": {"type": "string", "format": "date-time"}
                        }
                    },
                    "LoginRequest": {
                        "type": "object",
                        "required": ["username", "password"],
                        "properties": {
                            "username": {"type": "string"},
                            "password": {"type": "string"}
                        }
                    },
                    "Token": {
                        "type": "object",
                        "properties": {
                            "access_token": {"type": "string"},
                            "token_type": {"type": "string"},
                            "expires_in": {"type": "integer"}
                        }
                    },
                    "ErrorResponse": {
                        "type": "object",
                        "properties": {
                            "error": {"type": "string"},
                            "message": {"type": "string"},
                            "status_code": {"type": "integer"}
                        }
                    }
                }
            },
            "security": [
                {"bearerAuth": []}
            ]
        }
    
    def _generate_app_file(self, routes: List[Dict[str, Any]]) -> str:
        """Generate main FastAPI application file."""
        imports = [
            "from fastapi import FastAPI, HTTPException, Depends, status",
            "from fastapi.middleware.cors import CORSMiddleware",
            "from fastapi.security import HTTPBearer, HTTPAuthorizationCredentials",
            "import logging"
        ]
        
        # Add route imports
        for route in routes:
            imports.append(f"from routers import {route['module']}")
        
        app_content = [
            "# Generated FastAPI Application",
            "",
            *imports,
            "",
            "# Configure logging",
            "logging.basicConfig(level=logging.INFO)",
            "logger = logging.getLogger(__name__)",
            "",
            "# Initialize FastAPI app",
            "app = FastAPI(",
            "    title=\"Generated API\",",
            "    description=\"API generated from SRS requirements\",",
            "    version=\"1.0.0\"",
            ")",
            "",
            "# CORS middleware",
            "app.add_middleware(",
            "    CORSMiddleware,",
            "    allow_origins=[\"*\"],",
            "    allow_credentials=True,",
            "    allow_methods=[\"*\"],",
            "    allow_headers=[\"*\"],",
            ")",
            "",
            "# Security",
            "security = HTTPBearer()",
            "",
            "# Include routers",
        ]
        
        for route in routes:
            app_content.append(f"app.include_router({route['module']}.router, prefix=\"{route['prefix']}\", tags=[\"{route['module']}\"])")
        
        app_content.extend([
            "",
            "@app.get(\"/\")",
            "async def root():",
            "    \"\"\"Root endpoint.\"\"\"",
            "    return {\"message\": \"Welcome to the Generated API\"}",
            "",
            "@app.get(\"/health\")",
            "async def health_check():",
            "    \"\"\"Health check endpoint.\"\"\"",
            "    return {\"status\": \"healthy\"}",
            "",
            "if __name__ == \"__main__\":",
            "    import uvicorn",
            "    uvicorn.run(app, host=\"0.0.0.0\", port=8000)"
        ])
        
        return "\n".join(app_content)
    
    def _generate_models_file(self, api_requirements: List[Dict[str, Any]]) -> str:
        """Generate Pydantic models file."""
        models_content = [
            "# Generated Pydantic Models",
            "",
            "from pydantic import BaseModel, EmailStr",
            "from typing import Optional, List",
            "from datetime import datetime",
            "",
            "class UserBase(BaseModel):",
            "    \"\"\"Base user model.\"\"\"",
            "    username: str",
            "    email: EmailStr",
            "",
            "class UserCreate(UserBase):",
            "    \"\"\"User creation model.\"\"\"",
            "    password: str",
            "",
            "class UserUpdate(BaseModel):",
            "    \"\"\"User update model.\"\"\"",
            "    username: Optional[str] = None",
            "    email: Optional[EmailStr] = None",
            "",
            "class User(UserBase):",
            "    \"\"\"User response model.\"\"\"",
            "    id: int",
            "    created_at: datetime",
            "    is_active: bool = True",
            "",
            "    class Config:",
            "        from_attributes = True",
            "",
            "class LoginRequest(BaseModel):",
            "    \"\"\"Login request model.\"\"\"",
            "    username: str",
            "    password: str",
            "",
            "class Token(BaseModel):",
            "    \"\"\"Token response model.\"\"\"",
            "    access_token: str",
            "    token_type: str",
            "    expires_in: int",
            "",
            "class ErrorResponse(BaseModel):",
            "    \"\"\"Error response model.\"\"\"",
            "    error: str",
            "    message: str",
            "    status_code: int",
            "",
            "# Generic models for data operations",
            "class ItemBase(BaseModel):",
            "    \"\"\"Base item model.\"\"\"",
            "    name: str",
            "    description: Optional[str] = None",
            "",
            "class ItemCreate(ItemBase):",
            "    \"\"\"Item creation model.\"\"\"",
            "    pass",
            "",
            "class ItemUpdate(BaseModel):",
            "    \"\"\"Item update model.\"\"\"",
            "    name: Optional[str] = None",
            "    description: Optional[str] = None",
            "",
            "class Item(ItemBase):",
            "    \"\"\"Item response model.\"\"\"",
            "    id: int",
            "    created_at: datetime",
            "    updated_at: Optional[datetime] = None",
            "",
            "    class Config:",
            "        from_attributes = True"
        ]
        
        return "\n".join(models_content)