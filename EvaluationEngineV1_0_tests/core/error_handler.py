"""
Error handling and exception classes for the testing framework.
Provides comprehensive error classification, recovery mechanisms, and user guidance.

This module implements:
- Comprehensive error classification system
- Graceful degradation for partial failures  
- Retry logic for transient failures
- Detailed error reporting and user guidance
- Requirements 1.5, 2.5, 3.5, 4.5 compliance
"""

import logging
import traceback
import time
import json
from typing import Dict, List, Optional, Any, Callable, Union
from datetime import datetime
from enum import Enum
from dataclasses import dataclass, asdict


class ErrorSeverity(Enum):
    """Error severity levels for classification."""
    LOW = "low"
    MEDIUM = "medium"
    HIGH = "high"
    CRITICAL = "critical"


class ErrorCategory(Enum):
    """Error categories for classification."""
    CONFIGURATION = "configuration"
    DEPENDENCY = "dependency"
    EXECUTION = "execution"
    VALIDATION = "validation"
    ADAPTER = "adapter"
    API = "api"
    NETWORK = "network"
    RESOURCE = "resource"
    PERMISSION = "permission"
    DATA = "data"


@dataclass
class ErrorContext:
    """Structured error context information."""
    test_id: Optional[str] = None
    adapter_name: Optional[str] = None
    endpoint: Optional[str] = None
    config_path: Optional[str] = None
    command: Optional[str] = None
    file_path: Optional[str] = None
    line_number: Optional[int] = None
    user_action: Optional[str] = None
    system_state: Optional[Dict[str, Any]] = None
    additional_info: Optional[Dict[str, Any]] = None


@dataclass
class RecoveryAction:
    """Structured recovery action information."""
    action_type: str  # 'retry', 'fallback', 'skip', 'manual'
    description: str
    command: Optional[str] = None
    parameters: Optional[Dict[str, Any]] = None
    success_probability: float = 0.5
    estimated_time: Optional[int] = None  # seconds


class TestFrameworkError(Exception):
    """Base exception for testing framework errors with enhanced context."""
    
    def __init__(self, 
                 message: str, 
                 error_code: Optional[str] = None,
                 severity: ErrorSeverity = ErrorSeverity.MEDIUM,
                 category: ErrorCategory = ErrorCategory.EXECUTION,
                 context: Optional[ErrorContext] = None,
                 recovery_actions: Optional[List[RecoveryAction]] = None,
                 user_guidance: Optional[str] = None,
                 is_transient: bool = False):
        super().__init__(message)
        self.message = message
        self.error_code = error_code
        self.severity = severity
        self.category = category
        self.context = context or ErrorContext()
        self.recovery_actions = recovery_actions or []
        self.user_guidance = user_guidance
        self.is_transient = is_transient
        self.timestamp = datetime.now()
        self.traceback_str = traceback.format_exc()
        
    def to_dict(self) -> Dict[str, Any]:
        """Convert error to dictionary for serialization."""
        return {
            "message": self.message,
            "error_code": self.error_code,
            "severity": self.severity.value,
            "category": self.category.value,
            "context": asdict(self.context),
            "recovery_actions": [asdict(action) for action in self.recovery_actions],
            "user_guidance": self.user_guidance,
            "is_transient": self.is_transient,
            "timestamp": self.timestamp.isoformat(),
            "traceback": self.traceback_str
        }
        
    def get_user_friendly_message(self) -> str:
        """Get a user-friendly error message with guidance."""
        msg = f"[{self.severity.value.upper()}] {self.message}"
        
        if self.user_guidance:
            msg += f"\n\nGuidance: {self.user_guidance}"
            
        if self.recovery_actions:
            msg += "\n\nSuggested actions:"
            for i, action in enumerate(self.recovery_actions, 1):
                msg += f"\n  {i}. {action.description}"
                if action.command:
                    msg += f"\n     Command: {action.command}"
                    
        return msg


class ConfigurationError(TestFrameworkError):
    """Configuration validation and parsing errors."""
    
    def __init__(self, message: str, config_path: Optional[str] = None, 
                 validation_errors: Optional[List[str]] = None):
        context = ErrorContext(
            config_path=config_path,
            additional_info={"validation_errors": validation_errors or []}
        )
        
        recovery_actions = [
            RecoveryAction(
                action_type="manual",
                description="Check configuration file syntax and required fields",
                command=f"cat {config_path}" if config_path else None,
                success_probability=0.8
            ),
            RecoveryAction(
                action_type="fallback",
                description="Use default configuration",
                success_probability=0.9
            )
        ]
        
        user_guidance = self._generate_config_guidance(validation_errors or [])
        
        super().__init__(
            message=message,
            error_code="CONFIG_ERROR",
            severity=ErrorSeverity.HIGH,
            category=ErrorCategory.CONFIGURATION,
            context=context,
            recovery_actions=recovery_actions,
            user_guidance=user_guidance
        )
        self.config_path = config_path
        self.validation_errors = validation_errors or []
        
    def _generate_config_guidance(self, validation_errors: List[str]) -> str:
        """Generate specific guidance for configuration errors."""
        if not validation_errors:
            return "Please check your configuration file for syntax errors and ensure all required fields are present."
            
        guidance = "Configuration validation failed with the following issues:\n"
        for error in validation_errors:
            guidance += f"  - {error}\n"
        guidance += "\nPlease fix these issues and try again."
        return guidance


class DependencyError(TestFrameworkError):
    """Dependency installation and validation errors."""
    
    def __init__(self, message: str, dependency_name: Optional[str] = None,
                 installation_command: Optional[str] = None):
        context = ErrorContext(
            additional_info={
                "dependency_name": dependency_name,
                "installation_command": installation_command
            }
        )
        
        recovery_actions = []
        if installation_command:
            recovery_actions.append(
                RecoveryAction(
                    action_type="retry",
                    description=f"Install {dependency_name} dependency",
                    command=installation_command,
                    success_probability=0.7,
                    estimated_time=60
                )
            )
        
        recovery_actions.extend([
            RecoveryAction(
                action_type="manual",
                description="Check system requirements and install manually",
                success_probability=0.9
            ),
            RecoveryAction(
                action_type="skip",
                description="Skip tests requiring this dependency",
                success_probability=1.0
            )
        ])
        
        user_guidance = self._generate_dependency_guidance(dependency_name, installation_command)
        
        super().__init__(
            message=message,
            error_code="DEPENDENCY_ERROR",
            severity=ErrorSeverity.HIGH,
            category=ErrorCategory.DEPENDENCY,
            context=context,
            recovery_actions=recovery_actions,
            user_guidance=user_guidance,
            is_transient=True
        )
        self.dependency_name = dependency_name
        self.installation_command = installation_command
        
    def _generate_dependency_guidance(self, dependency_name: Optional[str], 
                                    installation_command: Optional[str]) -> str:
        """Generate specific guidance for dependency errors."""
        guidance = f"Missing dependency: {dependency_name or 'unknown'}\n"
        
        if installation_command:
            guidance += f"Try running: {installation_command}\n"
        
        guidance += "If installation fails, check:\n"
        guidance += "  - Internet connectivity\n"
        guidance += "  - System permissions\n"
        guidance += "  - Package manager configuration\n"
        guidance += "  - System requirements and compatibility"
        
        return guidance


class ExecutionError(TestFrameworkError):
    """Test execution runtime errors."""
    
    def __init__(self, message: str, test_id: Optional[str] = None,
                 exit_code: Optional[int] = None, command: Optional[str] = None):
        context = ErrorContext(
            test_id=test_id,
            command=command,
            additional_info={"exit_code": exit_code}
        )
        
        recovery_actions = [
            RecoveryAction(
                action_type="retry",
                description="Retry the failed operation",
                success_probability=0.3,
                estimated_time=30
            ),
            RecoveryAction(
                action_type="manual",
                description="Check logs and system resources",
                success_probability=0.8
            )
        ]
        
        # Add specific recovery actions based on exit code
        if exit_code == 130:  # SIGINT
            recovery_actions.insert(0, RecoveryAction(
                action_type="manual",
                description="Operation was interrupted - check if intentional",
                success_probability=1.0
            ))
        elif exit_code == 137:  # SIGKILL
            recovery_actions.insert(0, RecoveryAction(
                action_type="manual",
                description="Process was killed - check memory limits",
                success_probability=0.7
            ))
        
        user_guidance = self._generate_execution_guidance(exit_code, command)
        
        super().__init__(
            message=message,
            error_code="EXECUTION_ERROR",
            severity=ErrorSeverity.MEDIUM,
            category=ErrorCategory.EXECUTION,
            context=context,
            recovery_actions=recovery_actions,
            user_guidance=user_guidance,
            is_transient=True
        )
        self.test_id = test_id
        self.exit_code = exit_code
        
    def _generate_execution_guidance(self, exit_code: Optional[int], 
                                   command: Optional[str]) -> str:
        """Generate specific guidance for execution errors."""
        guidance = "Test execution failed"
        
        if command:
            guidance += f" while running: {command}"
            
        if exit_code:
            guidance += f" (exit code: {exit_code})"
            
            if exit_code == 1:
                guidance += "\nGeneral error - check logs for details"
            elif exit_code == 2:
                guidance += "\nInvalid command or arguments"
            elif exit_code == 126:
                guidance += "\nCommand not executable - check permissions"
            elif exit_code == 127:
                guidance += "\nCommand not found - check PATH"
            elif exit_code == 130:
                guidance += "\nOperation interrupted by user (Ctrl+C)"
            elif exit_code == 137:
                guidance += "\nProcess killed - likely out of memory"
            
        guidance += "\n\nCheck system resources, permissions, and logs for more details."
        return guidance


class ValidationError(TestFrameworkError):
    """Real execution validation errors."""
    
    def __init__(self, message: str, validation_type: Optional[str] = None,
                 expected_value: Optional[Any] = None, actual_value: Optional[Any] = None):
        context = ErrorContext(
            additional_info={
                "validation_type": validation_type,
                "expected_value": str(expected_value),
                "actual_value": str(actual_value)
            }
        )
        
        recovery_actions = [
            RecoveryAction(
                action_type="manual",
                description="Review validation criteria and expected values",
                success_probability=0.8
            ),
            RecoveryAction(
                action_type="retry",
                description="Retry validation with updated parameters",
                success_probability=0.5
            )
        ]
        
        user_guidance = self._generate_validation_guidance(
            validation_type, expected_value, actual_value
        )
        
        super().__init__(
            message=message,
            error_code="VALIDATION_ERROR",
            severity=ErrorSeverity.MEDIUM,
            category=ErrorCategory.VALIDATION,
            context=context,
            recovery_actions=recovery_actions,
            user_guidance=user_guidance
        )
        self.validation_type = validation_type
        self.expected_value = expected_value
        self.actual_value = actual_value
        
    def _generate_validation_guidance(self, validation_type: Optional[str],
                                    expected_value: Optional[Any],
                                    actual_value: Optional[Any]) -> str:
        """Generate specific guidance for validation errors."""
        guidance = f"Validation failed for: {validation_type or 'unknown'}\n"
        
        if expected_value is not None and actual_value is not None:
            guidance += f"Expected: {expected_value}\n"
            guidance += f"Actual: {actual_value}\n"
            
        guidance += "\nPossible causes:\n"
        guidance += "  - Test configuration mismatch\n"
        guidance += "  - Environment differences\n"
        guidance += "  - Timing issues\n"
        guidance += "  - Data format changes\n"
        guidance += "\nReview test setup and expected outcomes."
        
        return guidance


class AdapterError(TestFrameworkError):
    """Adapter integration and testing errors."""
    
    def __init__(self, message: str, adapter_name: Optional[str] = None,
                 adapter_method: Optional[str] = None):
        context = ErrorContext(
            adapter_name=adapter_name,
            additional_info={"adapter_method": adapter_method}
        )
        
        recovery_actions = [
            RecoveryAction(
                action_type="manual",
                description=f"Check {adapter_name} adapter configuration and dependencies",
                success_probability=0.7
            ),
            RecoveryAction(
                action_type="retry",
                description="Retry adapter operation with fresh initialization",
                success_probability=0.4
            ),
            RecoveryAction(
                action_type="fallback",
                description="Use alternative adapter if available",
                success_probability=0.6
            )
        ]
        
        user_guidance = self._generate_adapter_guidance(adapter_name, adapter_method)
        
        super().__init__(
            message=message,
            error_code="ADAPTER_ERROR",
            severity=ErrorSeverity.HIGH,
            category=ErrorCategory.ADAPTER,
            context=context,
            recovery_actions=recovery_actions,
            user_guidance=user_guidance
        )
        self.adapter_name = adapter_name
        self.adapter_method = adapter_method
        
    def _generate_adapter_guidance(self, adapter_name: Optional[str],
                                 adapter_method: Optional[str]) -> str:
        """Generate specific guidance for adapter errors."""
        guidance = f"Adapter error in: {adapter_name or 'unknown adapter'}"
        
        if adapter_method:
            guidance += f" (method: {adapter_method})"
            
        guidance += "\n\nCommon adapter issues:\n"
        guidance += "  - Missing or incompatible dependencies\n"
        guidance += "  - Configuration mismatch\n"
        guidance += "  - API changes in external frameworks\n"
        guidance += "  - Network connectivity issues\n"
        guidance += "  - Authentication problems\n"
        
        if adapter_name == "lm_eval_adapter":
            guidance += "\nFor lm_eval_adapter:\n"
            guidance += "  - Check lm-evaluation-harness installation\n"
            guidance += "  - Verify task definitions\n"
            guidance += "  - Check model configuration\n"
        elif adapter_name == "swe_bench_adapter":
            guidance += "\nFor swe_bench_adapter:\n"
            guidance += "  - Check SWE-bench installation\n"
            guidance += "  - Verify environment setup\n"
            guidance += "  - Check task data availability\n"
            
        return guidance


class APIError(TestFrameworkError):
    """API testing and server errors."""
    
    def __init__(self, message: str, endpoint: Optional[str] = None,
                 status_code: Optional[int] = None, response_data: Optional[Dict] = None):
        context = ErrorContext(
            endpoint=endpoint,
            additional_info={
                "status_code": status_code,
                "response_data": response_data
            }
        )
        
        recovery_actions = []
        
        # Add specific recovery actions based on status code
        if status_code == 400:
            recovery_actions.append(RecoveryAction(
                action_type="manual",
                description="Check request format and parameters",
                success_probability=0.8
            ))
        elif status_code == 401:
            recovery_actions.append(RecoveryAction(
                action_type="manual",
                description="Check authentication credentials",
                success_probability=0.9
            ))
        elif status_code == 404:
            recovery_actions.append(RecoveryAction(
                action_type="manual",
                description="Verify endpoint URL and API version",
                success_probability=0.8
            ))
        elif status_code == 429:
            recovery_actions.append(RecoveryAction(
                action_type="retry",
                description="Wait and retry (rate limited)",
                success_probability=0.9,
                estimated_time=60
            ))
        elif status_code and status_code >= 500:
            recovery_actions.append(RecoveryAction(
                action_type="retry",
                description="Retry request (server error)",
                success_probability=0.6,
                estimated_time=30
            ))
        
        recovery_actions.extend([
            RecoveryAction(
                action_type="manual",
                description="Check API server status and logs",
                success_probability=0.7
            ),
            RecoveryAction(
                action_type="fallback",
                description="Use alternative API endpoint if available",
                success_probability=0.5
            )
        ])
        
        user_guidance = self._generate_api_guidance(endpoint, status_code, response_data)
        
        super().__init__(
            message=message,
            error_code="API_ERROR",
            severity=ErrorSeverity.MEDIUM,
            category=ErrorCategory.API,
            context=context,
            recovery_actions=recovery_actions,
            user_guidance=user_guidance,
            is_transient=(status_code and status_code >= 500) or status_code == 429
        )
        self.endpoint = endpoint
        self.status_code = status_code
        self.response_data = response_data
        
    def _generate_api_guidance(self, endpoint: Optional[str], 
                             status_code: Optional[int],
                             response_data: Optional[Dict]) -> str:
        """Generate specific guidance for API errors."""
        guidance = f"API error for endpoint: {endpoint or 'unknown'}"
        
        if status_code:
            guidance += f" (HTTP {status_code})"
            
            if status_code == 400:
                guidance += "\nBad Request - check request format and parameters"
            elif status_code == 401:
                guidance += "\nUnauthorized - check authentication credentials"
            elif status_code == 403:
                guidance += "\nForbidden - check permissions"
            elif status_code == 404:
                guidance += "\nNot Found - check endpoint URL"
            elif status_code == 429:
                guidance += "\nRate Limited - wait before retrying"
            elif status_code >= 500:
                guidance += "\nServer Error - check server status"
                
        if response_data and isinstance(response_data, dict):
            if "error" in response_data:
                guidance += f"\nServer message: {response_data['error']}"
            elif "message" in response_data:
                guidance += f"\nServer message: {response_data['message']}"
                
        guidance += "\n\nTroubleshooting steps:\n"
        guidance += "  - Verify API server is running\n"
        guidance += "  - Check network connectivity\n"
        guidance += "  - Validate request format\n"
        guidance += "  - Review API documentation\n"
        
        return guidance


class NetworkError(TestFrameworkError):
    """Network connectivity and timeout errors."""
    
    def __init__(self, message: str, url: Optional[str] = None, timeout: Optional[int] = None):
        context = ErrorContext(
            additional_info={"url": url, "timeout": timeout}
        )
        
        recovery_actions = [
            RecoveryAction(
                action_type="retry",
                description="Retry with increased timeout",
                success_probability=0.6,
                estimated_time=timeout * 2 if timeout else 60
            ),
            RecoveryAction(
                action_type="manual",
                description="Check network connectivity and firewall settings",
                success_probability=0.8
            )
        ]
        
        user_guidance = f"Network error accessing: {url or 'unknown URL'}\n"
        user_guidance += "Check internet connection and proxy settings."
        
        super().__init__(
            message=message,
            error_code="NETWORK_ERROR",
            severity=ErrorSeverity.MEDIUM,
            category=ErrorCategory.NETWORK,
            context=context,
            recovery_actions=recovery_actions,
            user_guidance=user_guidance,
            is_transient=True
        )


class ResourceError(TestFrameworkError):
    """Resource exhaustion and limit errors."""
    
    def __init__(self, message: str, resource_type: Optional[str] = None, 
                 current_usage: Optional[str] = None, limit: Optional[str] = None):
        context = ErrorContext(
            additional_info={
                "resource_type": resource_type,
                "current_usage": current_usage,
                "limit": limit
            }
        )
        
        recovery_actions = [
            RecoveryAction(
                action_type="manual",
                description="Free up system resources",
                success_probability=0.7
            ),
            RecoveryAction(
                action_type="retry",
                description="Retry with reduced resource requirements",
                success_probability=0.8
            )
        ]
        
        user_guidance = f"Resource exhaustion: {resource_type or 'unknown resource'}\n"
        if current_usage and limit:
            user_guidance += f"Usage: {current_usage}, Limit: {limit}\n"
        user_guidance += "Free up resources or increase limits."
        
        super().__init__(
            message=message,
            error_code="RESOURCE_ERROR",
            severity=ErrorSeverity.HIGH,
            category=ErrorCategory.RESOURCE,
            context=context,
            recovery_actions=recovery_actions,
            user_guidance=user_guidance
        )


class PermissionError(TestFrameworkError):
    """File system and permission errors."""
    
    def __init__(self, message: str, file_path: Optional[str] = None, 
                 required_permission: Optional[str] = None):
        context = ErrorContext(
            file_path=file_path,
            additional_info={"required_permission": required_permission}
        )
        
        recovery_actions = [
            RecoveryAction(
                action_type="manual",
                description="Check and fix file permissions",
                command=f"chmod +{required_permission} {file_path}" if file_path and required_permission else None,
                success_probability=0.9
            ),
            RecoveryAction(
                action_type="manual",
                description="Run with appropriate privileges",
                success_probability=0.8
            )
        ]
        
        user_guidance = f"Permission denied for: {file_path or 'unknown file'}\n"
        user_guidance += "Check file permissions and user privileges."
        
        super().__init__(
            message=message,
            error_code="PERMISSION_ERROR",
            severity=ErrorSeverity.HIGH,
            category=ErrorCategory.PERMISSION,
            context=context,
            recovery_actions=recovery_actions,
            user_guidance=user_guidance
        )


class DataError(TestFrameworkError):
    """Data format and validation errors."""
    
    def __init__(self, message: str, data_type: Optional[str] = None,
                 expected_format: Optional[str] = None, actual_format: Optional[str] = None):
        context = ErrorContext(
            additional_info={
                "data_type": data_type,
                "expected_format": expected_format,
                "actual_format": actual_format
            }
        )
        
        recovery_actions = [
            RecoveryAction(
                action_type="manual",
                description="Validate and fix data format",
                success_probability=0.8
            ),
            RecoveryAction(
                action_type="fallback",
                description="Use alternative data source",
                success_probability=0.6
            )
        ]
        
        user_guidance = f"Data format error for: {data_type or 'unknown data'}\n"
        if expected_format and actual_format:
            user_guidance += f"Expected: {expected_format}, Got: {actual_format}\n"
        user_guidance += "Check data format and structure."
        
        super().__init__(
            message=message,
            error_code="DATA_ERROR",
            severity=ErrorSeverity.MEDIUM,
            category=ErrorCategory.DATA,
            context=context,
            recovery_actions=recovery_actions,
            user_guidance=user_guidance
        )


class ErrorHandler:
    """Centralized error handling and logging with recovery mechanisms."""
    
    def __init__(self, logger_name: str = "TestFramework"):
        self.logger = logging.getLogger(logger_name)
        self.error_history: List[TestFrameworkError] = []
        self.error_counts: Dict[str, int] = {}
        self.recovery_attempts: Dict[str, int] = {}
        self.graceful_degradation_enabled = True
    
    def handle_error(self, error: TestFrameworkError, 
                    context: Optional[Dict[str, Any]] = None,
                    attempt_recovery: bool = True) -> Optional[Any]:
        """Handle and log an error with optional recovery attempts."""
        # Add to history
        self.error_history.append(error)
        
        # Update counts
        error_type = type(error).__name__
        self.error_counts[error_type] = self.error_counts.get(error_type, 0) + 1
        
        # Create comprehensive log entry
        log_data = {
            "error_code": error.error_code,
            "severity": error.severity.value,
            "category": error.category.value,
            "context": error.context.__dict__,
            "timestamp": error.timestamp.isoformat(),
            "is_transient": error.is_transient
        }
        
        if context:
            log_data["additional_context"] = context
            
        # Log based on severity
        if error.severity == ErrorSeverity.CRITICAL:
            self.logger.critical(f"{error_type}: {error.message}", extra=log_data)
        elif error.severity == ErrorSeverity.HIGH:
            self.logger.error(f"{error_type}: {error.message}", extra=log_data)
        elif error.severity == ErrorSeverity.MEDIUM:
            self.logger.warning(f"{error_type}: {error.message}", extra=log_data)
        else:
            self.logger.info(f"{error_type}: {error.message}", extra=log_data)
        
        # Log user-friendly message
        self.logger.info(f"User guidance: {error.get_user_friendly_message()}")
        
        # Log traceback for debugging
        if error.traceback_str and error.traceback_str != "NoneType: None\n":
            self.logger.debug(f"Traceback for {error_type}:\n{error.traceback_str}")
            
        # Attempt recovery if enabled
        if attempt_recovery and error.recovery_actions:
            return self._attempt_recovery(error)
            
        return None
    
    def handle_exception(self, exception: Exception, 
                        context: Optional[Dict[str, Any]] = None,
                        attempt_recovery: bool = True) -> TestFrameworkError:
        """Convert a generic exception to a TestFrameworkError and handle it."""
        if isinstance(exception, TestFrameworkError):
            framework_error = exception
        else:
            # Try to classify the exception
            framework_error = self._classify_exception(exception, context)
        
        self.handle_error(framework_error, context, attempt_recovery)
        return framework_error
        
    def _classify_exception(self, exception: Exception, 
                          context: Optional[Dict[str, Any]] = None) -> TestFrameworkError:
        """Classify a generic exception into a specific TestFrameworkError."""
        error_context = ErrorContext()
        if context:
            error_context.additional_info = context
            
        exception_str = str(exception).lower()
        exception_type = type(exception).__name__
        
        # Network-related errors
        if any(keyword in exception_str for keyword in ['connection', 'timeout', 'network', 'dns']):
            return NetworkError(
                message=str(exception),
                url=context.get('url') if context else None,
                timeout=context.get('timeout') if context else None
            )
            
        # Permission errors
        if any(keyword in exception_str for keyword in ['permission', 'access denied', 'forbidden']):
            return PermissionError(
                message=str(exception),
                file_path=context.get('file_path') if context else None,
                required_permission=context.get('required_permission') if context else None
            )
            
        # Resource errors
        if any(keyword in exception_str for keyword in ['memory', 'disk', 'resource', 'limit']):
            return ResourceError(
                message=str(exception),
                resource_type=context.get('resource_type') if context else None
            )
            
        # Configuration errors
        if any(keyword in exception_str for keyword in ['config', 'yaml', 'json', 'parse']):
            return ConfigurationError(
                message=str(exception),
                config_path=context.get('config_path') if context else None
            )
            
        # Data format errors
        if any(keyword in exception_str for keyword in ['format', 'decode', 'encode', 'schema']):
            return DataError(
                message=str(exception),
                data_type=context.get('data_type') if context else None
            )
            
        # Default to generic error
        return TestFrameworkError(
            message=str(exception),
            error_code="GENERIC_ERROR",
            severity=ErrorSeverity.MEDIUM,
            category=ErrorCategory.EXECUTION,
            context=error_context,
            user_guidance=f"Unclassified {exception_type}: {str(exception)}"
        )
    
    def _attempt_recovery(self, error: TestFrameworkError) -> Optional[Any]:
        """Attempt to recover from an error using its recovery actions."""
        error_key = f"{error.error_code}_{error.message[:50]}"
        attempts = self.recovery_attempts.get(error_key, 0)
        
        if attempts >= 3:  # Max recovery attempts
            self.logger.warning(f"Max recovery attempts reached for {error.error_code}")
            return None
            
        self.recovery_attempts[error_key] = attempts + 1
        
        # Try recovery actions in order of success probability
        sorted_actions = sorted(error.recovery_actions, 
                              key=lambda x: x.success_probability, reverse=True)
        
        for action in sorted_actions:
            if action.action_type == "retry":
                self.logger.info(f"Attempting recovery: {action.description}")
                if action.estimated_time:
                    self.logger.info(f"Estimated time: {action.estimated_time} seconds")
                return self._execute_retry_action(action)
                
            elif action.action_type == "fallback":
                self.logger.info(f"Using fallback: {action.description}")
                return self._execute_fallback_action(action)
                
            elif action.action_type == "skip":
                self.logger.info(f"Skipping operation: {action.description}")
                return self._execute_skip_action(action)
                
        return None
        
    def _execute_retry_action(self, action: RecoveryAction) -> Optional[Any]:
        """Execute a retry recovery action."""
        if action.estimated_time:
            time.sleep(min(action.estimated_time, 300))  # Max 5 minutes
        return {"action": "retry", "description": action.description}
        
    def _execute_fallback_action(self, action: RecoveryAction) -> Optional[Any]:
        """Execute a fallback recovery action."""
        return {"action": "fallback", "description": action.description}
        
    def _execute_skip_action(self, action: RecoveryAction) -> Optional[Any]:
        """Execute a skip recovery action."""
        return {"action": "skip", "description": action.description}
        
    def enable_graceful_degradation(self, enabled: bool = True) -> None:
        """Enable or disable graceful degradation for partial failures."""
        self.graceful_degradation_enabled = enabled
        self.logger.info(f"Graceful degradation {'enabled' if enabled else 'disabled'}")
        
    def should_continue_after_error(self, error: TestFrameworkError) -> bool:
        """Determine if execution should continue after an error."""
        if not self.graceful_degradation_enabled:
            return False
            
        # Critical errors should stop execution
        if error.severity == ErrorSeverity.CRITICAL:
            return False
            
        # Configuration errors in core components should stop execution
        if (error.category == ErrorCategory.CONFIGURATION and 
            error.severity == ErrorSeverity.HIGH):
            return False
            
        # Too many errors should stop execution
        if len(self.error_history) > 50:  # Configurable threshold
            self.logger.error("Too many errors encountered, stopping execution")
            return False
            
        return True
        
    def get_error_summary(self) -> Dict[str, Any]:
        """Get a comprehensive summary of all errors encountered."""
        severity_counts = {}
        category_counts = {}
        
        for error in self.error_history:
            severity_counts[error.severity.value] = severity_counts.get(error.severity.value, 0) + 1
            category_counts[error.category.value] = category_counts.get(error.category.value, 0) + 1
            
        return {
            "total_errors": len(self.error_history),
            "error_counts": self.error_counts.copy(),
            "severity_counts": severity_counts,
            "category_counts": category_counts,
            "recovery_attempts": self.recovery_attempts.copy(),
            "graceful_degradation_enabled": self.graceful_degradation_enabled,
            "recent_errors": [
                {
                    "type": type(error).__name__,
                    "message": error.message,
                    "severity": error.severity.value,
                    "category": error.category.value,
                    "timestamp": error.timestamp.isoformat(),
                    "error_code": error.error_code,
                    "is_transient": error.is_transient,
                    "recovery_actions_count": len(error.recovery_actions)
                }
                for error in self.error_history[-10:]  # Last 10 errors
            ]
        }
        
    def export_error_report(self, file_path: str) -> None:
        """Export detailed error report to file."""
        report = {
            "summary": self.get_error_summary(),
            "detailed_errors": [error.to_dict() for error in self.error_history],
            "export_timestamp": datetime.now().isoformat()
        }
        
        try:
            with open(file_path, 'w') as f:
                json.dump(report, f, indent=2, default=str)
            self.logger.info(f"Error report exported to {file_path}")
        except Exception as e:
            self.logger.error(f"Failed to export error report: {e}")
            
    def get_troubleshooting_guide(self) -> str:
        """Generate a troubleshooting guide based on encountered errors."""
        if not self.error_history:
            return "No errors encountered. System is functioning normally."
            
        guide = "# Troubleshooting Guide\n\n"
        guide += f"Based on {len(self.error_history)} errors encountered:\n\n"
        
        # Group errors by category
        category_errors = {}
        for error in self.error_history:
            category = error.category.value
            if category not in category_errors:
                category_errors[category] = []
            category_errors[category].append(error)
            
        for category, errors in category_errors.items():
            guide += f"## {category.title()} Errors ({len(errors)})\n\n"
            
            # Get unique error types in this category
            unique_errors = {}
            for error in errors:
                error_type = type(error).__name__
                if error_type not in unique_errors:
                    unique_errors[error_type] = error
                    
            for error_type, example_error in unique_errors.items():
                guide += f"### {error_type}\n"
                guide += f"**Common cause:** {example_error.message}\n\n"
                
                if example_error.user_guidance:
                    guide += f"**Guidance:** {example_error.user_guidance}\n\n"
                    
                if example_error.recovery_actions:
                    guide += "**Recovery actions:**\n"
                    for i, action in enumerate(example_error.recovery_actions, 1):
                        guide += f"{i}. {action.description}\n"
                        if action.command:
                            guide += f"   Command: `{action.command}`\n"
                    guide += "\n"
                    
        return guide
    
    def clear_history(self) -> None:
        """Clear error history and counts."""
        self.error_history.clear()
        self.error_counts.clear()
        self.recovery_attempts.clear()
        self.logger.info("Error history cleared")


class RetryHandler:
    """Handle retry logic for failed operations with intelligent backoff."""
    
    def __init__(self, max_retries: int = 3, base_delay: float = 1.0, 
                 max_delay: float = 60.0, backoff_factor: float = 2.0):
        self.max_retries = max_retries
        self.base_delay = base_delay
        self.max_delay = max_delay
        self.backoff_factor = backoff_factor
        self.logger = logging.getLogger(f"{__name__}.RetryHandler")
        self.retry_stats: Dict[str, Dict[str, Any]] = {}
    
    def retry_operation(self, operation: Callable, operation_name: str = None,
                       retry_on: tuple = (Exception,), *args, **kwargs) -> Any:
        """Retry an operation with intelligent exponential backoff."""
        operation_name = operation_name or operation.__name__
        last_exception = None
        
        for attempt in range(self.max_retries + 1):
            try:
                start_time = time.time()
                result = operation(*args, **kwargs)
                
                # Record successful operation
                execution_time = time.time() - start_time
                self._record_success(operation_name, attempt, execution_time)
                
                if attempt > 0:
                    self.logger.info(f"Operation '{operation_name}' succeeded on attempt {attempt + 1}")
                
                return result
                
            except Exception as e:
                last_exception = e
                
                # Check if this exception should trigger a retry
                if not isinstance(e, retry_on):
                    self.logger.error(f"Operation '{operation_name}' failed with non-retryable error: {e}")
                    raise e
                
                if attempt < self.max_retries:
                    delay = min(self.base_delay * (self.backoff_factor ** attempt), self.max_delay)
                    
                    # Add jitter to prevent thundering herd
                    import random
                    jitter = random.uniform(0.1, 0.3) * delay
                    actual_delay = delay + jitter
                    
                    self.logger.warning(
                        f"Operation '{operation_name}' failed (attempt {attempt + 1}/{self.max_retries + 1}): {e}. "
                        f"Retrying in {actual_delay:.2f} seconds..."
                    )
                    
                    # Record failed attempt
                    self._record_failure(operation_name, attempt, str(e))
                    
                    time.sleep(actual_delay)
                else:
                    self.logger.error(f"Operation '{operation_name}' failed after {self.max_retries + 1} attempts")
                    self._record_final_failure(operation_name, str(e))
        
        # If we get here, all retries failed
        raise last_exception
    
    def retry_with_circuit_breaker(self, operation: Callable, operation_name: str = None,
                                 failure_threshold: int = 5, recovery_timeout: int = 60,
                                 *args, **kwargs) -> Any:
        """Retry operation with circuit breaker pattern."""
        operation_name = operation_name or operation.__name__
        
        # Check circuit breaker state
        if self._is_circuit_open(operation_name, failure_threshold, recovery_timeout):
            raise TestFrameworkError(
                f"Circuit breaker open for operation '{operation_name}'",
                error_code="CIRCUIT_BREAKER_OPEN",
                severity=ErrorSeverity.HIGH,
                user_guidance=f"Operation '{operation_name}' has failed too many times. "
                            f"Wait {recovery_timeout} seconds before retrying."
            )
        
        try:
            return self.retry_operation(operation, operation_name, *args, **kwargs)
        except Exception as e:
            self._record_circuit_failure(operation_name)
            raise e
    
    def _record_success(self, operation_name: str, attempt: int, execution_time: float) -> None:
        """Record successful operation."""
        if operation_name not in self.retry_stats:
            self.retry_stats[operation_name] = {
                "total_attempts": 0,
                "successful_attempts": 0,
                "failed_attempts": 0,
                "last_success": None,
                "last_failure": None,
                "average_execution_time": 0.0,
                "circuit_failures": 0,
                "last_circuit_failure": None
            }
        
        stats = self.retry_stats[operation_name]
        stats["total_attempts"] += attempt + 1
        stats["successful_attempts"] += 1
        stats["last_success"] = datetime.now()
        
        # Update average execution time
        if stats["average_execution_time"] == 0:
            stats["average_execution_time"] = execution_time
        else:
            stats["average_execution_time"] = (stats["average_execution_time"] + execution_time) / 2
    
    def _record_failure(self, operation_name: str, attempt: int, error_message: str) -> None:
        """Record failed attempt."""
        if operation_name not in self.retry_stats:
            self.retry_stats[operation_name] = {
                "total_attempts": 0,
                "successful_attempts": 0,
                "failed_attempts": 0,
                "last_success": None,
                "last_failure": None,
                "average_execution_time": 0.0,
                "circuit_failures": 0,
                "last_circuit_failure": None
            }
        
        stats = self.retry_stats[operation_name]
        stats["failed_attempts"] += 1
        stats["last_failure"] = datetime.now()
    
    def _record_final_failure(self, operation_name: str, error_message: str) -> None:
        """Record final failure after all retries exhausted."""
        self._record_failure(operation_name, 0, error_message)
    
    def _record_circuit_failure(self, operation_name: str) -> None:
        """Record circuit breaker failure."""
        if operation_name in self.retry_stats:
            self.retry_stats[operation_name]["circuit_failures"] += 1
            self.retry_stats[operation_name]["last_circuit_failure"] = datetime.now()
    
    def _is_circuit_open(self, operation_name: str, failure_threshold: int, 
                        recovery_timeout: int) -> bool:
        """Check if circuit breaker is open for an operation."""
        if operation_name not in self.retry_stats:
            return False
        
        stats = self.retry_stats[operation_name]
        
        # Check if we've exceeded failure threshold
        if stats["circuit_failures"] < failure_threshold:
            return False
        
        # Check if recovery timeout has passed
        if stats["last_circuit_failure"]:
            time_since_failure = (datetime.now() - stats["last_circuit_failure"]).total_seconds()
            if time_since_failure > recovery_timeout:
                # Reset circuit breaker
                stats["circuit_failures"] = 0
                stats["last_circuit_failure"] = None
                return False
        
        return True
    
    def get_retry_stats(self) -> Dict[str, Dict[str, Any]]:
        """Get retry statistics for all operations."""
        return self.retry_stats.copy()
    
    def reset_stats(self, operation_name: Optional[str] = None) -> None:
        """Reset retry statistics."""
        if operation_name:
            if operation_name in self.retry_stats:
                del self.retry_stats[operation_name]
        else:
            self.retry_stats.clear()


def setup_error_logging(log_level: str = "INFO", log_file: Optional[str] = None) -> logging.Logger:
    """Set up error logging configuration."""
    logger = logging.getLogger("TestFramework")
    logger.setLevel(getattr(logging, log_level.upper()))
    
    # Clear existing handlers
    logger.handlers.clear()
    
    # Console handler
    console_handler = logging.StreamHandler()
    console_formatter = logging.Formatter(
        '%(asctime)s - %(name)s - %(levelname)s - %(message)s'
    )
    console_handler.setFormatter(console_formatter)
    logger.addHandler(console_handler)
    
    # File handler if specified
    if log_file:
        file_handler = logging.FileHandler(log_file)
        file_formatter = logging.Formatter(
            '%(asctime)s - %(name)s - %(levelname)s - %(funcName)s:%(lineno)d - %(message)s'
        )
        file_handler.setFormatter(file_formatter)
        logger.addHandler(file_handler)
    
    return logger


class ErrorContextManager:
    """Context manager for error handling with automatic recovery."""
    
    def __init__(self, error_handler: ErrorHandler, operation_name: str,
                 context: Optional[ErrorContext] = None,
                 attempt_recovery: bool = True,
                 continue_on_error: bool = False):
        self.error_handler = error_handler
        self.operation_name = operation_name
        self.context = context or ErrorContext()
        self.attempt_recovery = attempt_recovery
        self.continue_on_error = continue_on_error
        self.start_time = None
        
    def __enter__(self):
        self.start_time = time.time()
        return self
        
    def __exit__(self, exc_type, exc_val, exc_tb):
        if exc_type is not None:
            execution_time = time.time() - self.start_time if self.start_time else 0
            
            # Add execution context
            self.context.additional_info = self.context.additional_info or {}
            self.context.additional_info.update({
                "operation_name": self.operation_name,
                "execution_time": execution_time
            })
            
            # Handle the exception
            framework_error = self.error_handler.handle_exception(
                exc_val, 
                context=self.context.__dict__,
                attempt_recovery=self.attempt_recovery
            )
            
            # Determine if we should suppress the exception
            if self.continue_on_error and self.error_handler.should_continue_after_error(framework_error):
                return True  # Suppress the exception
                
        return False  # Don't suppress the exception


def create_error_context(test_id: Optional[str] = None, 
                        adapter_name: Optional[str] = None,
                        endpoint: Optional[str] = None,
                        config_path: Optional[str] = None,
                        **kwargs) -> ErrorContext:
    """Create a standardized error context object."""
    return ErrorContext(
        test_id=test_id,
        adapter_name=adapter_name,
        endpoint=endpoint,
        config_path=config_path,
        additional_info=kwargs
    )


def handle_cli_error(error: TestFrameworkError) -> str:
    """Format error for CLI display (Requirement 1.5)."""
    output = f"\n{'='*60}\n"
    output += f"ERROR: {error.message}\n"
    output += f"{'='*60}\n"
    
    if error.error_code:
        output += f"Error Code: {error.error_code}\n"
    
    output += f"Severity: {error.severity.value.upper()}\n"
    output += f"Category: {error.category.value.title()}\n"
    output += f"Time: {error.timestamp.strftime('%Y-%m-%d %H:%M:%S')}\n"
    
    if error.context.test_id:
        output += f"Test ID: {error.context.test_id}\n"
    
    if error.context.adapter_name:
        output += f"Adapter: {error.context.adapter_name}\n"
    
    if error.user_guidance:
        output += f"\nGuidance:\n{error.user_guidance}\n"
    
    if error.recovery_actions:
        output += f"\nSuggested Actions:\n"
        for i, action in enumerate(error.recovery_actions, 1):
            output += f"  {i}. {action.description}\n"
            if action.command:
                output += f"     Command: {action.command}\n"
    
    output += f"{'='*60}\n"
    return output


def handle_api_error(error: TestFrameworkError) -> Dict[str, Any]:
    """Format error for API response (Requirement 2.5)."""
    return {
        "error": {
            "message": error.message,
            "code": error.error_code,
            "severity": error.severity.value,
            "category": error.category.value,
            "timestamp": error.timestamp.isoformat(),
            "context": {
                "endpoint": error.context.endpoint,
                "test_id": error.context.test_id,
                "adapter_name": error.context.adapter_name
            },
            "guidance": error.user_guidance,
            "recovery_actions": [
                {
                    "type": action.action_type,
                    "description": action.description,
                    "command": action.command,
                    "success_probability": action.success_probability
                }
                for action in error.recovery_actions
            ],
            "is_transient": error.is_transient
        }
    }


def handle_adapter_error(error: TestFrameworkError) -> Dict[str, Any]:
    """Format error for adapter validation (Requirement 3.5)."""
    return {
        "adapter_error": {
            "adapter_name": error.context.adapter_name,
            "error_message": error.message,
            "error_code": error.error_code,
            "severity": error.severity.value,
            "timestamp": error.timestamp.isoformat(),
            "diagnostic_info": {
                "category": error.category.value,
                "context": error.context.__dict__,
                "is_transient": error.is_transient
            },
            "troubleshooting": {
                "guidance": error.user_guidance,
                "recovery_actions": [
                    {
                        "action": action.action_type,
                        "description": action.description,
                        "command": action.command,
                        "success_rate": f"{action.success_probability * 100:.1f}%"
                    }
                    for action in error.recovery_actions
                ]
            }
        }
    }


def handle_pipeline_error(error: TestFrameworkError, pipeline_stage: str) -> Dict[str, Any]:
    """Format error for pipeline context (Requirement 4.5)."""
    return {
        "pipeline_error": {
            "stage": pipeline_stage,
            "error_message": error.message,
            "error_code": error.error_code,
            "severity": error.severity.value,
            "category": error.category.value,
            "timestamp": error.timestamp.isoformat(),
            "detailed_context": {
                "test_id": error.context.test_id,
                "config_path": error.context.config_path,
                "command": error.context.command,
                "file_path": error.context.file_path,
                "system_state": error.context.system_state,
                "additional_info": error.context.additional_info
            },
            "impact_assessment": {
                "can_continue": error.severity != ErrorSeverity.CRITICAL,
                "is_transient": error.is_transient,
                "recovery_possible": len(error.recovery_actions) > 0
            },
            "user_guidance": error.user_guidance,
            "recovery_options": [
                {
                    "type": action.action_type,
                    "description": action.description,
                    "command": action.command,
                    "estimated_time": action.estimated_time,
                    "success_probability": action.success_probability
                }
                for action in error.recovery_actions
            ]
        }
    }


# Global error handler instance
_global_error_handler: Optional[ErrorHandler] = None


def get_global_error_handler() -> ErrorHandler:
    """Get or create the global error handler instance."""
    global _global_error_handler
    if _global_error_handler is None:
        _global_error_handler = ErrorHandler()
    return _global_error_handler


def set_global_error_handler(handler: ErrorHandler) -> None:
    """Set the global error handler instance."""
    global _global_error_handler
    _global_error_handler = handler