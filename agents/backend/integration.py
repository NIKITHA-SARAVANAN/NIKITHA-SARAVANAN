"""
Integration Agent for third-party API integration with retries and circuit breaker.
"""

import time
from typing import Dict, Any, List
import re

from ..base_agent import BaseAgent


class IntegrationAgent(BaseAgent):
    """Agent responsible for third-party service integration."""
    
    def __init__(self, config: Dict[str, Any] = None):
        """Initialize the Integration agent."""
        super().__init__("IntegrationAgent", config)
        
    def process(self, input_data: Dict[str, Any]) -> Dict[str, Any]:
        """
        Process SRD and generate integration implementations.
        
        Args:
            input_data: Dictionary containing SRD data and dependencies
            
        Returns:
            Generated integration code with error handling
        """
        start_time = time.time()
        
        try:
            # Validate input
            if not self.validate_input(input_data, ['backend_srd']):
                return self.handle_error(ValueError("Missing required 'backend_srd' in input"), "input_validation")
            
            backend_srd = input_data['backend_srd']
            dependencies = input_data.get('dependencies', [])
            
            # Extract integration requirements
            integrations = self._extract_integrations(backend_srd, dependencies)
            
            # Generate integration services
            services = self._generate_integration_services(integrations)
            
            # Generate circuit breaker implementation
            circuit_breaker = self._generate_circuit_breaker()
            
            # Generate retry mechanisms
            retry_logic = self._generate_retry_logic()
            
            # Generate API clients
            api_clients = self._generate_api_clients(integrations)
            
            result = {
                'integrations': integrations,
                'services': services,
                'circuit_breaker': circuit_breaker,
                'retry_logic': retry_logic,
                'api_clients': api_clients
            }
            
            # Log action
            execution_time = int((time.time() - start_time) * 1000)
            self.log_action(
                "design_integrations",
                {"backend_srd_length": len(backend_srd)},
                {"integrations_count": len(integrations)},
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
                "design_integrations",
                input_data,
                {},
                success=False,
                error_message=str(e),
                execution_time_ms=execution_time
            )
            return self.handle_error(e, "integration_design")
    
    def _extract_integrations(self, backend_srd: str, dependencies: List[Dict[str, Any]]) -> List[Dict[str, Any]]:
        """Extract integration requirements from SRD and dependencies."""
        integrations = []
        
        # Integration patterns
        integration_patterns = {
            'payment': r'(?i)(payment|stripe|paypal|credit card|billing)',
            'email': r'(?i)(email|smtp|sendgrid|mailgun|notification)',
            'sms': r'(?i)(sms|twilio|text message)',
            'file_storage': r'(?i)(file|storage|s3|aws|azure|gcp|upload)',
            'authentication': r'(?i)(oauth|auth0|google|facebook|social)',
            'database': r'(?i)(database|postgres|mysql|mongodb|redis)',
            'search': r'(?i)(search|elasticsearch|solr|algolia)',
            'analytics': r'(?i)(analytics|tracking|google analytics|mixpanel)',
            'maps': r'(?i)(map|location|google maps|geocoding)',
            'push_notifications': r'(?i)(push|notification|firebase|apns)'
        }
        
        srd_lower = backend_srd.lower()
        
        # Extract from SRD text
        for integration_type, pattern in integration_patterns.items():
            if re.search(pattern, srd_lower):
                integrations.append({
                    'type': integration_type,
                    'name': f"{integration_type.title()}Integration",
                    'source': 'srd_analysis',
                    'priority': 'high' if integration_type in ['payment', 'authentication'] else 'medium',
                    'complexity': 'high' if integration_type in ['payment', 'authentication'] else 'medium'
                })
        
        # Extract from dependencies
        for dep in dependencies:
            if dep.get('type') == 'service' and dep.get('is_external'):
                integrations.append({
                    'type': 'external_service',
                    'name': f"{dep['name'].title()}Integration",
                    'service_name': dep['name'],
                    'source': 'dependency_analysis',
                    'priority': 'medium',
                    'complexity': 'medium'
                })
        
        # Add default integrations
        if not any(i['type'] == 'database' for i in integrations):
            integrations.append({
                'type': 'database',
                'name': 'DatabaseIntegration',
                'source': 'default',
                'priority': 'high',
                'complexity': 'low'
            })
        
        return integrations
    
    def _generate_integration_services(self, integrations: List[Dict[str, Any]]) -> List[Dict[str, Any]]:
        """Generate integration service implementations."""
        services = []
        
        for integration in integrations:
            service = {
                'name': integration['name'],
                'type': integration['type'],
                'implementation': self._generate_service_implementation(integration),
                'config': self._generate_service_config(integration),
                'tests': self._generate_service_tests(integration)
            }
            services.append(service)
        
        return services
    
    def _generate_service_implementation(self, integration: Dict[str, Any]) -> str:
        """Generate service implementation code."""
        integration_type = integration['type']
        class_name = integration['name']
        
        implementation = f'''"""
{class_name} - Integration service for {integration_type}.
"""

import aiohttp
import asyncio
import logging
from typing import Dict, Any, Optional
from datetime import datetime, timedelta
import json

from .circuit_breaker import CircuitBreaker
from .retry_logic import RetryMechanism

logger = logging.getLogger(__name__)


class {class_name}:
    """Integration service for {integration_type}."""
    
    def __init__(self, config: Dict[str, Any]):
        """Initialize the integration service."""
        self.config = config
        self.base_url = config.get('base_url', '')
        self.api_key = config.get('api_key', '')
        self.timeout = config.get('timeout', 30)
        
        # Initialize circuit breaker and retry mechanism
        self.circuit_breaker = CircuitBreaker(
            failure_threshold=5,
            recovery_timeout=60,
            expected_exception=aiohttp.ClientError
        )
        self.retry_mechanism = RetryMechanism(
            max_retries=3,
            backoff_factor=2,
            max_delay=60
        )
        
        self.session = None
    
    async def __aenter__(self):
        """Async context manager entry."""
        self.session = aiohttp.ClientSession(
            timeout=aiohttp.ClientTimeout(total=self.timeout)
        )
        return self
    
    async def __aexit__(self, exc_type, exc_val, exc_tb):
        """Async context manager exit."""
        if self.session:
            await self.session.close()
    
    async def _make_request(self, method: str, endpoint: str, 
                          data: Optional[Dict[str, Any]] = None,
                          headers: Optional[Dict[str, str]] = None) -> Dict[str, Any]:
        """Make HTTP request with circuit breaker and retry logic."""
        url = f"{{self.base_url}}/{{endpoint.lstrip('/')}}"
        
        # Prepare headers
        request_headers = {{
            'Content-Type': 'application/json',
            'Authorization': f'Bearer {{self.api_key}}'
        }}
        if headers:
            request_headers.update(headers)
        
        async def _request():
            async with self.session.request(
                method=method,
                url=url,
                json=data,
                headers=request_headers
            ) as response:
                response.raise_for_status()
                return await response.json()
        
        # Apply circuit breaker and retry logic
        try:
            result = await self.circuit_breaker.call(
                self.retry_mechanism.execute(_request)
            )
            
            logger.info(f"{{integration_type}} API call successful: {{method}} {{endpoint}}")
            return result
            
        except Exception as e:
            logger.error(f"{{integration_type}} API call failed: {{method}} {{endpoint}} - {{e}}")
            raise
    
    {self._generate_specific_methods(integration_type)}
    
    async def health_check(self) -> bool:
        """Check if the service is healthy."""
        try:
            await self._make_request('GET', '/health')
            return True
        except Exception as e:
            logger.error(f"{{integration_type}} health check failed: {{e}}")
            return False
    
    def get_status(self) -> Dict[str, Any]:
        """Get integration status."""
        return {{
            'service': '{integration_type}',
            'circuit_breaker_state': self.circuit_breaker.state,
            'last_failure': self.circuit_breaker.last_failure_time,
            'failure_count': self.circuit_breaker.failure_count
        }}
'''
        
        return implementation
    
    def _generate_specific_methods(self, integration_type: str) -> str:
        """Generate specific methods based on integration type."""
        methods = {
            'payment': '''
    async def process_payment(self, amount: float, currency: str, 
                            payment_method: str, metadata: Dict[str, Any] = None) -> Dict[str, Any]:
        """Process a payment transaction."""
        data = {
            'amount': int(amount * 100),  # Convert to cents
            'currency': currency,
            'payment_method': payment_method,
            'metadata': metadata or {}
        }
        
        return await self._make_request('POST', '/payments', data)
    
    async def refund_payment(self, payment_id: str, amount: Optional[float] = None) -> Dict[str, Any]:
        """Refund a payment."""
        data = {'payment_id': payment_id}
        if amount:
            data['amount'] = int(amount * 100)
        
        return await self._make_request('POST', '/refunds', data)
    
    async def get_payment_status(self, payment_id: str) -> Dict[str, Any]:
        """Get payment status."""
        return await self._make_request('GET', f'/payments/{payment_id}')''',
            
            'email': '''
    async def send_email(self, to_email: str, subject: str, content: str,
                        from_email: Optional[str] = None, 
                        template_id: Optional[str] = None) -> Dict[str, Any]:
        """Send an email."""
        data = {
            'to': [{'email': to_email}],
            'subject': subject,
            'from': {'email': from_email or self.config.get('default_from_email')},
        }
        
        if template_id:
            data['template_id'] = template_id
            data['dynamic_template_data'] = {'content': content}
        else:
            data['content'] = [{'type': 'text/html', 'value': content}]
        
        return await self._make_request('POST', '/mail/send', data)
    
    async def send_bulk_email(self, recipients: List[str], subject: str, 
                            content: str) -> Dict[str, Any]:
        """Send bulk emails."""
        data = {
            'to': [{'email': email} for email in recipients],
            'subject': subject,
            'content': [{'type': 'text/html', 'value': content}]
        }
        
        return await self._make_request('POST', '/mail/send', data)''',
            
            'file_storage': '''
    async def upload_file(self, file_data: bytes, file_name: str, 
                         content_type: str = 'application/octet-stream') -> Dict[str, Any]:
        """Upload a file."""
        headers = {'Content-Type': content_type}
        
        # For file uploads, we need to handle binary data differently
        url = f"{self.base_url}/files/{file_name}"
        
        async with self.session.put(url, data=file_data, headers=headers) as response:
            response.raise_for_status()
            return {'url': url, 'file_name': file_name, 'status': 'uploaded'}
    
    async def delete_file(self, file_name: str) -> Dict[str, Any]:
        """Delete a file."""
        return await self._make_request('DELETE', f'/files/{file_name}')
    
    async def get_file_url(self, file_name: str, expires_in: int = 3600) -> str:
        """Get a presigned URL for file access."""
        result = await self._make_request('GET', f'/files/{file_name}/url', 
                                        {'expires_in': expires_in})
        return result.get('url', '')''',
            
            'authentication': '''
    async def validate_token(self, token: str) -> Dict[str, Any]:
        """Validate an authentication token."""
        headers = {'Authorization': f'Bearer {token}'}
        return await self._make_request('GET', '/validate', headers=headers)
    
    async def get_user_info(self, user_id: str) -> Dict[str, Any]:
        """Get user information."""
        return await self._make_request('GET', f'/users/{user_id}')
    
    async def update_user_permissions(self, user_id: str, 
                                    permissions: List[str]) -> Dict[str, Any]:
        """Update user permissions."""
        data = {'permissions': permissions}
        return await self._make_request('PUT', f'/users/{user_id}/permissions', data)'''
        }
        
        return methods.get(integration_type, '''
    async def execute_operation(self, operation: str, data: Dict[str, Any]) -> Dict[str, Any]:
        """Execute a generic operation."""
        return await self._make_request('POST', f'/{operation}', data)''')
    
    def _generate_service_config(self, integration: Dict[str, Any]) -> str:
        """Generate service configuration."""
        integration_type = integration['type']
        
        config = f'''"""
Configuration for {integration['name']}.
"""

import os
from typing import Dict, Any

def get_{integration_type}_config() -> Dict[str, Any]:
    """Get {integration_type} integration configuration."""
    return {{
        'base_url': os.getenv('{integration_type.upper()}_BASE_URL', ''),
        'api_key': os.getenv('{integration_type.upper()}_API_KEY', ''),
        'timeout': int(os.getenv('{integration_type.upper()}_TIMEOUT', '30')),
        'max_retries': int(os.getenv('{integration_type.upper()}_MAX_RETRIES', '3')),
        'circuit_breaker_threshold': int(os.getenv('{integration_type.upper()}_CB_THRESHOLD', '5')),
        'circuit_breaker_timeout': int(os.getenv('{integration_type.upper()}_CB_TIMEOUT', '60')),
    }}

# Environment variables required:
# {integration_type.upper()}_BASE_URL - Base URL for the service
# {integration_type.upper()}_API_KEY - API key for authentication
# {integration_type.upper()}_TIMEOUT - Request timeout in seconds (optional)
# {integration_type.upper()}_MAX_RETRIES - Maximum retry attempts (optional)
# {integration_type.upper()}_CB_THRESHOLD - Circuit breaker failure threshold (optional)
# {integration_type.upper()}_CB_TIMEOUT - Circuit breaker recovery timeout (optional)
'''
        
        return config
    
    def _generate_service_tests(self, integration: Dict[str, Any]) -> str:
        """Generate test cases for the service."""
        class_name = integration['name']
        integration_type = integration['type']
        
        tests = f'''"""
Test cases for {class_name}.
"""

import pytest
import asyncio
from unittest.mock import AsyncMock, patch
import aiohttp

from integrations.{integration_type} import {class_name}


@pytest.fixture
def {integration_type}_config():
    """Test configuration."""
    return {{
        'base_url': 'https://api.test.com',
        'api_key': 'test_key',
        'timeout': 30
    }}


@pytest.fixture
async def {integration_type}_service({integration_type}_config):
    """Create service instance for testing."""
    async with {class_name}({integration_type}_config) as service:
        yield service


@pytest.mark.asyncio
async def test_health_check({integration_type}_service):
    """Test health check functionality."""
    with patch.object({integration_type}_service, '_make_request', new_callable=AsyncMock) as mock_request:
        mock_request.return_value = {{'status': 'ok'}}
        
        result = await {integration_type}_service.health_check()
        
        assert result is True
        mock_request.assert_called_once_with('GET', '/health')


@pytest.mark.asyncio
async def test_health_check_failure({integration_type}_service):
    """Test health check failure."""
    with patch.object({integration_type}_service, '_make_request', new_callable=AsyncMock) as mock_request:
        mock_request.side_effect = aiohttp.ClientError("Connection failed")
        
        result = await {integration_type}_service.health_check()
        
        assert result is False


@pytest.mark.asyncio
async def test_circuit_breaker_integration({integration_type}_service):
    """Test circuit breaker functionality."""
    # Test that circuit breaker opens after failures
    with patch.object({integration_type}_service.session, 'request') as mock_request:
        mock_request.side_effect = aiohttp.ClientError("Service unavailable")
        
        # Should fail and open circuit breaker
        for _ in range(6):  # Exceed failure threshold
            try:
                await {integration_type}_service._make_request('GET', '/test')
            except:
                pass
        
        assert {integration_type}_service.circuit_breaker.state == 'open'


def test_get_status({integration_type}_service):
    """Test status reporting."""
    status = {integration_type}_service.get_status()
    
    assert 'service' in status
    assert 'circuit_breaker_state' in status
    assert status['service'] == '{integration_type}'
'''
        
        return tests
    
    def _generate_circuit_breaker(self) -> str:
        """Generate circuit breaker implementation."""
        return '''"""
Circuit Breaker pattern implementation for integration resilience.
"""

import asyncio
import time
from typing import Callable, Any, Type, Optional
from enum import Enum
import logging

logger = logging.getLogger(__name__)


class CircuitBreakerState(Enum):
    """Circuit breaker states."""
    CLOSED = "closed"
    OPEN = "open"
    HALF_OPEN = "half_open"


class CircuitBreakerError(Exception):
    """Exception raised when circuit breaker is open."""
    pass


class CircuitBreaker:
    """Circuit breaker for handling service failures."""
    
    def __init__(self, failure_threshold: int = 5, 
                 recovery_timeout: int = 60,
                 expected_exception: Type[Exception] = Exception):
        """
        Initialize circuit breaker.
        
        Args:
            failure_threshold: Number of failures before opening circuit
            recovery_timeout: Time to wait before attempting recovery
            expected_exception: Exception type that counts as failure
        """
        self.failure_threshold = failure_threshold
        self.recovery_timeout = recovery_timeout
        self.expected_exception = expected_exception
        
        self.failure_count = 0
        self.last_failure_time = None
        self.state = CircuitBreakerState.CLOSED
        
        self._lock = asyncio.Lock()
    
    async def call(self, func: Callable) -> Any:
        """Call a function through the circuit breaker."""
        async with self._lock:
            await self._check_state()
            
            if self.state == CircuitBreakerState.OPEN:
                raise CircuitBreakerError("Circuit breaker is open")
            
            try:
                result = await func()
                await self._on_success()
                return result
                
            except self.expected_exception as e:
                await self._on_failure()
                raise e
    
    async def _check_state(self):
        """Check and update circuit breaker state."""
        if self.state == CircuitBreakerState.OPEN:
            if (time.time() - self.last_failure_time) >= self.recovery_timeout:
                self.state = CircuitBreakerState.HALF_OPEN
                logger.info("Circuit breaker moved to half-open state")
    
    async def _on_success(self):
        """Handle successful call."""
        if self.state == CircuitBreakerState.HALF_OPEN:
            self.state = CircuitBreakerState.CLOSED
            logger.info("Circuit breaker closed after successful call")
        
        self.failure_count = 0
    
    async def _on_failure(self):
        """Handle failed call."""
        self.failure_count += 1
        self.last_failure_time = time.time()
        
        if self.failure_count >= self.failure_threshold:
            self.state = CircuitBreakerState.OPEN
            logger.warning(f"Circuit breaker opened after {self.failure_count} failures")
    
    def reset(self):
        """Reset circuit breaker to closed state."""
        self.state = CircuitBreakerState.CLOSED
        self.failure_count = 0
        self.last_failure_time = None
        logger.info("Circuit breaker manually reset")
    
    @property
    def is_closed(self) -> bool:
        """Check if circuit breaker is closed."""
        return self.state == CircuitBreakerState.CLOSED
    
    @property
    def is_open(self) -> bool:
        """Check if circuit breaker is open."""
        return self.state == CircuitBreakerState.OPEN
    
    @property
    def is_half_open(self) -> bool:
        """Check if circuit breaker is half-open."""
        return self.state == CircuitBreakerState.HALF_OPEN
'''
    
    def _generate_retry_logic(self) -> str:
        """Generate retry mechanism implementation."""
        return '''"""
Retry mechanism with exponential backoff for integration resilience.
"""

import asyncio
import random
import time
from typing import Callable, Any, Type, List
import logging

logger = logging.getLogger(__name__)


class RetryExhaustedError(Exception):
    """Exception raised when all retry attempts are exhausted."""
    pass


class RetryMechanism:
    """Retry mechanism with exponential backoff and jitter."""
    
    def __init__(self, max_retries: int = 3, 
                 backoff_factor: float = 2.0,
                 max_delay: float = 60.0,
                 jitter: bool = True,
                 retryable_exceptions: List[Type[Exception]] = None):
        """
        Initialize retry mechanism.
        
        Args:
            max_retries: Maximum number of retry attempts
            backoff_factor: Factor for exponential backoff
            max_delay: Maximum delay between retries
            jitter: Whether to add random jitter to delays
            retryable_exceptions: List of exceptions that should trigger retry
        """
        self.max_retries = max_retries
        self.backoff_factor = backoff_factor
        self.max_delay = max_delay
        self.jitter = jitter
        self.retryable_exceptions = retryable_exceptions or [Exception]
    
    async def execute(self, func: Callable) -> Any:
        """Execute function with retry logic."""
        last_exception = None
        
        for attempt in range(self.max_retries + 1):
            try:
                if attempt > 0:
                    delay = self._calculate_delay(attempt)
                    logger.info(f"Retrying in {delay:.2f} seconds (attempt {attempt}/{self.max_retries})")
                    await asyncio.sleep(delay)
                
                result = await func()
                
                if attempt > 0:
                    logger.info(f"Function succeeded on attempt {attempt + 1}")
                
                return result
                
            except Exception as e:
                last_exception = e
                
                # Check if exception is retryable
                if not self._is_retryable(e):
                    logger.error(f"Non-retryable exception: {e}")
                    raise e
                
                if attempt == self.max_retries:
                    logger.error(f"All retry attempts exhausted. Last error: {e}")
                    break
                
                logger.warning(f"Attempt {attempt + 1} failed: {e}")
        
        raise RetryExhaustedError(f"Function failed after {self.max_retries + 1} attempts") from last_exception
    
    def _calculate_delay(self, attempt: int) -> float:
        """Calculate delay for given attempt number."""
        delay = min(self.backoff_factor ** (attempt - 1), self.max_delay)
        
        if self.jitter:
            # Add jitter (±25% of the delay)
            jitter_range = delay * 0.25
            delay += random.uniform(-jitter_range, jitter_range)
            delay = max(0, delay)  # Ensure non-negative
        
        return delay
    
    def _is_retryable(self, exception: Exception) -> bool:
        """Check if exception is retryable."""
        return any(isinstance(exception, exc_type) for exc_type in self.retryable_exceptions)


class ExponentialBackoff:
    """Simple exponential backoff implementation."""
    
    def __init__(self, base_delay: float = 1.0, max_delay: float = 60.0, 
                 multiplier: float = 2.0):
        """Initialize exponential backoff."""
        self.base_delay = base_delay
        self.max_delay = max_delay
        self.multiplier = multiplier
        self.attempt = 0
    
    async def wait(self):
        """Wait for the calculated delay."""
        delay = min(self.base_delay * (self.multiplier ** self.attempt), self.max_delay)
        await asyncio.sleep(delay)
        self.attempt += 1
    
    def reset(self):
        """Reset the attempt counter."""
        self.attempt = 0
'''
    
    def _generate_api_clients(self, integrations: List[Dict[str, Any]]) -> str:
        """Generate API client factory."""
        return '''"""
API Client factory for managing integration instances.
"""

import asyncio
from typing import Dict, Any, Optional, Type
import logging

from .circuit_breaker import CircuitBreaker
from .retry_logic import RetryMechanism

logger = logging.getLogger(__name__)


class IntegrationManager:
    """Manages all integration service instances."""
    
    def __init__(self):
        """Initialize integration manager."""
        self.services = {}
        self.configs = {}
    
    def register_service(self, service_name: str, service_class: Type, 
                        config: Dict[str, Any]):
        """Register an integration service."""
        self.configs[service_name] = config
        logger.info(f"Registered service: {service_name}")
    
    async def get_service(self, service_name: str):
        """Get or create service instance."""
        if service_name not in self.services:
            if service_name not in self.configs:
                raise ValueError(f"Service {service_name} not registered")
            
            config = self.configs[service_name]
            service_class = config.pop('service_class')
            service = service_class(config)
            
            self.services[service_name] = service
            logger.info(f"Created service instance: {service_name}")
        
        return self.services[service_name]
    
    async def health_check_all(self) -> Dict[str, bool]:
        """Check health of all services."""
        results = {}
        
        for service_name, service in self.services.items():
            try:
                results[service_name] = await service.health_check()
            except Exception as e:
                logger.error(f"Health check failed for {service_name}: {e}")
                results[service_name] = False
        
        return results
    
    async def close_all(self):
        """Close all service connections."""
        for service_name, service in self.services.items():
            try:
                if hasattr(service, 'close'):
                    await service.close()
                logger.info(f"Closed service: {service_name}")
            except Exception as e:
                logger.error(f"Error closing service {service_name}: {e}")
        
        self.services.clear()


# Global integration manager instance
integration_manager = IntegrationManager()


async def get_integration_service(service_name: str):
    """Get integration service instance."""
    return await integration_manager.get_service(service_name)


async def register_all_services(configs: Dict[str, Dict[str, Any]]):
    """Register all integration services from config."""
    for service_name, config in configs.items():
        integration_manager.register_service(service_name, config)
'''