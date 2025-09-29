"""
Security Manager

Central security management system that coordinates all security
components and provides unified security controls.
"""

import logging
import threading
import time
from typing import Dict, List, Optional, Any, Callable
from pathlib import Path
from contextlib import contextmanager
from dataclasses import dataclass

from .sandbox_executor import SandboxExecutor, SandboxExecutionError
from .resource_limiter import ResourceLimiter, ResourceLimits, ResourceLimitExceeded
from .command_validator import CommandValidator, CommandPolicy, CommandValidationError
from .api_security import APIAuthenticator, RateLimiter, RateLimitConfig, AuthenticationError, RateLimitExceeded
from .secure_file_handler import SecureFileHandler, FileAccessPolicy, SecureFileError
from .security_monitor import SecurityMonitor, SecurityAlert
from .security_config_validator import SecurityConfigValidator, SecurityValidationResult
from .security_utils import SecurityUtils, SecurityContextManager

logger = logging.getLogger(__name__)


@dataclass
class SecurityConfig:
    """Comprehensive security configuration."""
    # Sandbox configuration
    enable_sandbox: bool = True
    sandbox_base_dir: Optional[Path] = None
    max_execution_time: int = 300
    max_memory_mb: int = 1024
    max_cpu_percent: int = 80
    allow_network: bool = False
    
    # Resource limits
    enable_resource_limits: bool = True
    resource_limits: Optional[ResourceLimits] = None
    monitoring_interval: float = 1.0
    
    # Command validation
    enable_command_validation: bool = True
    command_policy: Optional[CommandPolicy] = None
    
    # API security
    enable_api_security: bool = True
    api_secret_key: Optional[str] = None
    default_rate_limit: Optional[RateLimitConfig] = None
    
    # File security
    enable_file_security: bool = True
    secure_file_base_dir: Optional[Path] = None
    file_access_policy: Optional[FileAccessPolicy] = None
    
    # Audit and logging
    enable_audit_logging: bool = True
    max_audit_entries: int = 10000
    
    # Emergency controls
    enable_emergency_stop: bool = True
    emergency_stop_triggers: List[str] = None


class SecurityViolation(Exception):
    """Raised when security violations are detected."""
    pass


class SecurityManager:
    """
    Central security management system that coordinates all security components.
    
    Features:
    - Unified security configuration
    - Coordinated security enforcement
    - Security event monitoring
    - Emergency stop capabilities
    - Comprehensive audit logging
    - Security metrics and reporting
    """
    
    def __init__(self, config: Optional[SecurityConfig] = None):
        """
        Initialize security manager.
        
        Args:
            config: Security configuration (uses default if None)
        """
        self.config = config or SecurityConfig()
        
        # Validate configuration
        self.config_validator = SecurityConfigValidator()
        validation_result = self.config_validator.validate_security_config(self.config)
        
        if not validation_result.is_valid:
            logger.warning(f"Security configuration has errors: {validation_result.errors}")
        
        if validation_result.warnings:
            logger.warning(f"Security configuration warnings: {validation_result.warnings}")
        
        # Initialize security components
        self._init_components()
        
        # Initialize security monitor
        self.security_monitor = SecurityMonitor()
        self.security_monitor.start_monitoring()
        
        # Security state
        self._security_enabled = True
        self._emergency_stop = False
        self._violation_count = 0
        self._lock = threading.Lock()
        
        # Audit log
        self.audit_log: List[Dict] = []
        
        # Security metrics
        self.metrics = {
            'sandbox_executions': 0,
            'resource_violations': 0,
            'command_validations': 0,
            'api_authentications': 0,
            'file_operations': 0,
            'security_violations': 0,
            'emergency_stops': 0
        }
        
        logger.info(f"Security manager initialized with score: {validation_result.security_score}/100")
    
    def _init_components(self):
        """Initialize security components based on configuration."""
        # Sandbox executor
        if self.config.enable_sandbox:
            self.sandbox_executor = SandboxExecutor(
                base_sandbox_dir=self.config.sandbox_base_dir,
                max_execution_time=self.config.max_execution_time,
                max_memory_mb=self.config.max_memory_mb,
                max_cpu_percent=self.config.max_cpu_percent,
                allow_network=self.config.allow_network
            )
        else:
            self.sandbox_executor = None
        
        # Resource limiter
        if self.config.enable_resource_limits:
            limits = self.config.resource_limits or ResourceLimits(
                max_memory_mb=self.config.max_memory_mb,
                max_cpu_percent=self.config.max_cpu_percent,
                max_execution_time=self.config.max_execution_time
            )
            self.resource_limiter = ResourceLimiter(
                limits=limits,
                monitoring_interval=self.config.monitoring_interval
            )
        else:
            self.resource_limiter = None
        
        # Command validator
        if self.config.enable_command_validation:
            self.command_validator = CommandValidator(
                policy=self.config.command_policy
            )
        else:
            self.command_validator = None
        
        # API security
        if self.config.enable_api_security:
            self.api_authenticator = APIAuthenticator(
                secret_key=self.config.api_secret_key
            )
            self.rate_limiter = RateLimiter(
                default_config=self.config.default_rate_limit
            )
        else:
            self.api_authenticator = None
            self.rate_limiter = None
        
        # Secure file handler
        if self.config.enable_file_security:
            self.file_handler = SecureFileHandler(
                base_dir=self.config.secure_file_base_dir,
                policy=self.config.file_access_policy
            )
        else:
            self.file_handler = None
    
    @contextmanager
    def secure_execution_context(self, 
                                context_id: str,
                                sandbox_config: Optional[Dict] = None,
                                resource_config: Optional[Dict] = None):
        """
        Create a secure execution context with all security measures enabled.
        
        Args:
            context_id: Unique identifier for the execution context
            sandbox_config: Sandbox-specific configuration
            resource_config: Resource limit configuration
        """
        if not self._security_enabled:
            raise SecurityViolation("Security is disabled")
        
        if self._emergency_stop:
            raise SecurityViolation("Emergency stop is active")
        
        sandbox_context = None
        resource_context = None
        
        try:
            self._log_security_event('execution_context_start', {
                'context_id': context_id,
                'sandbox_enabled': self.sandbox_executor is not None,
                'resource_limits_enabled': self.resource_limiter is not None
            })
            
            # Start resource monitoring
            if self.resource_limiter:
                resource_context = self.resource_limiter.monitor_resources()
                resource_context.__enter__()
            
            # Create sandbox if enabled
            if self.sandbox_executor:
                sandbox_context = self.sandbox_executor.create_sandbox(
                    sandbox_id=context_id,
                    **(sandbox_config or {})
                )
                sandbox_env = sandbox_context.__enter__()
                yield sandbox_env
            else:
                yield None
            
        except Exception as e:
            self._handle_security_violation('execution_context_error', {
                'context_id': context_id,
                'error': str(e)
            })
            raise
        
        finally:
            # Cleanup contexts
            if sandbox_context:
                try:
                    sandbox_context.__exit__(None, None, None)
                except Exception as e:
                    logger.error(f"Error cleaning up sandbox context: {e}")
            
            if resource_context:
                try:
                    resource_context.__exit__(None, None, None)
                except Exception as e:
                    logger.error(f"Error cleaning up resource context: {e}")
            
            self._log_security_event('execution_context_end', {
                'context_id': context_id
            })
    
    def validate_and_execute_command(self, 
                                   command: str,
                                   context_id: Optional[str] = None,
                                   **kwargs) -> Dict[str, Any]:
        """
        Validate and execute command with full security checks.
        
        Args:
            command: Command to execute
            context_id: Execution context ID
            **kwargs: Additional execution parameters
            
        Returns:
            Execution results
        """
        if not self._security_enabled:
            raise SecurityViolation("Security is disabled")
        
        if self._emergency_stop:
            raise SecurityViolation("Emergency stop is active")
        
        try:
            # Validate command
            if self.command_validator:
                validated_command, env_vars = self.command_validator.validate_command(command)
                self.metrics['command_validations'] += 1
            else:
                validated_command = command.split() if isinstance(command, str) else command
                env_vars = {}
            
            # Execute in sandbox if available
            if self.sandbox_executor and context_id:
                with self.sandbox_executor.create_sandbox(context_id) as sandbox:
                    result = sandbox.execute_command(
                        validated_command,
                        env=env_vars,
                        **kwargs
                    )
                    self.metrics['sandbox_executions'] += 1
            else:
                # Direct execution (less secure)
                import subprocess
                result = subprocess.run(
                    validated_command,
                    capture_output=True,
                    text=True,
                    timeout=self.config.max_execution_time,
                    **kwargs
                )
                result = {
                    'return_code': result.returncode,
                    'stdout': result.stdout,
                    'stderr': result.stderr,
                    'success': result.returncode == 0
                }
            
            self._log_security_event('command_executed', {
                'command': str(validated_command),
                'context_id': context_id,
                'success': result.get('success', False)
            })
            
            return result
            
        except (CommandValidationError, SandboxExecutionError) as e:
            self._handle_security_violation('command_execution_error', {
                'command': command,
                'context_id': context_id,
                'error': str(e)
            })
            raise SecurityViolation(f"Command execution failed: {e}")
        
        except Exception as e:
            self._handle_security_violation('unexpected_execution_error', {
                'command': command,
                'context_id': context_id,
                'error': str(e)
            })
            raise
    
    def authenticate_api_request(self, 
                               key_id: Optional[str] = None,
                               key_secret: Optional[str] = None,
                               jwt_token: Optional[str] = None) -> Dict[str, Any]:
        """
        Authenticate API request.
        
        Args:
            key_id: API key ID
            key_secret: API key secret
            jwt_token: JWT token
            
        Returns:
            Authentication result
        """
        if not self.api_authenticator:
            raise SecurityViolation("API security is disabled")
        
        try:
            if key_id and key_secret:
                api_key = self.api_authenticator.authenticate_api_key(key_id, key_secret)
                auth_result = {
                    'type': 'api_key',
                    'key_id': api_key.key_id,
                    'permissions': api_key.permissions,
                    'rate_limit': api_key.rate_limit
                }
            elif jwt_token:
                payload = self.api_authenticator.authenticate_jwt_token(jwt_token)
                auth_result = {
                    'type': 'jwt',
                    'user_id': payload.get('user_id'),
                    'permissions': payload.get('permissions', []),
                    'expires_at': payload.get('exp')
                }
            else:
                raise AuthenticationError("No authentication credentials provided")
            
            self.metrics['api_authentications'] += 1
            
            self._log_security_event('api_authentication_success', {
                'auth_type': auth_result['type'],
                'identifier': auth_result.get('key_id') or auth_result.get('user_id')
            })
            
            return auth_result
            
        except AuthenticationError as e:
            self._handle_security_violation('api_authentication_failed', {
                'key_id': key_id,
                'error': str(e)
            })
            raise SecurityViolation(f"API authentication failed: {e}")
    
    def check_rate_limit(self, key: str, endpoint: Optional[str] = None) -> Dict[str, Any]:
        """
        Check rate limit for API request.
        
        Args:
            key: Rate limiting key
            endpoint: API endpoint
            
        Returns:
            Rate limit information
        """
        if not self.rate_limiter:
            return {'allowed': True}
        
        try:
            allowed, rate_info = self.rate_limiter.check_rate_limit(key, endpoint)
            
            if not allowed:
                self._handle_security_violation('rate_limit_exceeded', {
                    'key': key,
                    'endpoint': endpoint,
                    'limit_type': rate_info.get('limit_type')
                })
                raise SecurityViolation(f"Rate limit exceeded for {key}")
            
            return {'allowed': True, 'rate_info': rate_info}
            
        except RateLimitExceeded as e:
            raise SecurityViolation(f"Rate limit exceeded: {e}")
    
    def secure_file_operation(self, 
                            operation: str,
                            file_path: str,
                            **kwargs) -> Any:
        """
        Perform secure file operation.
        
        Args:
            operation: File operation type
            file_path: File path
            **kwargs: Operation-specific parameters
            
        Returns:
            Operation result
        """
        if not self.file_handler:
            raise SecurityViolation("File security is disabled")
        
        try:
            operation_map = {
                'read': self.file_handler.safe_read_file,
                'write': self.file_handler.safe_write_file,
                'copy': self.file_handler.safe_copy_file,
                'delete': self.file_handler.safe_delete_file,
                'checksum': self.file_handler.calculate_checksum
            }
            
            if operation not in operation_map:
                raise SecurityViolation(f"Unknown file operation: {operation}")
            
            result = operation_map[operation](file_path, **kwargs)
            self.metrics['file_operations'] += 1
            
            self._log_security_event('file_operation_success', {
                'operation': operation,
                'file_path': file_path
            })
            
            return result
            
        except SecureFileError as e:
            self._handle_security_violation('file_operation_failed', {
                'operation': operation,
                'file_path': file_path,
                'error': str(e)
            })
            raise SecurityViolation(f"File operation failed: {e}")
    
    def _handle_security_violation(self, violation_type: str, details: Dict[str, Any]):
        """Handle security violation."""
        with self._lock:
            self._violation_count += 1
            self.metrics['security_violations'] += 1
        
        # Record in security monitor
        self.security_monitor.record_security_event(f"{violation_type}_violation", details)
        
        self._log_security_event('security_violation', {
            'violation_type': violation_type,
            'details': details,
            'violation_count': self._violation_count
        })
        
        # Check for emergency stop triggers
        if self.config.enable_emergency_stop:
            self._check_emergency_stop_triggers(violation_type, details)
        
        logger.warning(f"Security violation: {violation_type} - {details}")
    
    def _check_emergency_stop_triggers(self, violation_type: str, details: Dict[str, Any]):
        """Check if emergency stop should be triggered."""
        triggers = self.config.emergency_stop_triggers or [
            'multiple_auth_failures',
            'resource_exhaustion',
            'command_injection_attempt'
        ]
        
        # Check violation count threshold
        if self._violation_count >= 10:
            self.trigger_emergency_stop("Multiple security violations detected")
        
        # Check specific triggers
        if violation_type in triggers:
            self.trigger_emergency_stop(f"Emergency stop trigger: {violation_type}")
    
    def trigger_emergency_stop(self, reason: str):
        """Trigger emergency stop."""
        with self._lock:
            self._emergency_stop = True
            self.metrics['emergency_stops'] += 1
        
        self._log_security_event('emergency_stop_triggered', {
            'reason': reason,
            'timestamp': time.time()
        })
        
        # Cleanup all resources
        self._emergency_cleanup()
        
        logger.critical(f"EMERGENCY STOP TRIGGERED: {reason}")
    
    def _emergency_cleanup(self):
        """Perform emergency cleanup of all resources."""
        try:
            # Cleanup sandbox environments
            if self.sandbox_executor:
                self.sandbox_executor.cleanup_all_sandboxes()
            
            # Stop resource monitoring
            if self.resource_limiter:
                self.resource_limiter.stop_monitoring()
            
            # Cleanup temporary files
            if self.file_handler:
                self.file_handler.cleanup_temp_files()
            
            logger.info("Emergency cleanup completed")
            
        except Exception as e:
            logger.error(f"Error during emergency cleanup: {e}")
    
    def reset_emergency_stop(self, reason: str):
        """Reset emergency stop (admin only)."""
        with self._lock:
            self._emergency_stop = False
            self._violation_count = 0
        
        self._log_security_event('emergency_stop_reset', {
            'reason': reason,
            'timestamp': time.time()
        })
        
        logger.info(f"Emergency stop reset: {reason}")
    
    def disable_security(self, reason: str):
        """Disable security (admin only - use with extreme caution)."""
        with self._lock:
            self._security_enabled = False
        
        self._log_security_event('security_disabled', {
            'reason': reason,
            'timestamp': time.time()
        })
        
        logger.warning(f"SECURITY DISABLED: {reason}")
    
    def enable_security(self, reason: str):
        """Re-enable security."""
        with self._lock:
            self._security_enabled = True
        
        self._log_security_event('security_enabled', {
            'reason': reason,
            'timestamp': time.time()
        })
        
        logger.info(f"Security enabled: {reason}")
    
    def _log_security_event(self, event_type: str, details: Dict[str, Any]):
        """Log security event."""
        if not self.config.enable_audit_logging:
            return
        
        event = {
            'timestamp': time.time(),
            'event_type': event_type,
            'details': details
        }
        
        self.audit_log.append(event)
        
        # Maintain audit log size
        if len(self.audit_log) > self.config.max_audit_entries:
            self.audit_log = self.audit_log[-self.config.max_audit_entries:]
    
    def get_security_status(self) -> Dict[str, Any]:
        """Get current security status."""
        return {
            'security_enabled': self._security_enabled,
            'emergency_stop': self._emergency_stop,
            'violation_count': self._violation_count,
            'components': {
                'sandbox_executor': self.sandbox_executor is not None,
                'resource_limiter': self.resource_limiter is not None,
                'command_validator': self.command_validator is not None,
                'api_authenticator': self.api_authenticator is not None,
                'rate_limiter': self.rate_limiter is not None,
                'file_handler': self.file_handler is not None
            },
            'metrics': self.metrics.copy(),
            'config': {
                'enable_sandbox': self.config.enable_sandbox,
                'enable_resource_limits': self.config.enable_resource_limits,
                'enable_command_validation': self.config.enable_command_validation,
                'enable_api_security': self.config.enable_api_security,
                'enable_file_security': self.config.enable_file_security,
                'enable_audit_logging': self.config.enable_audit_logging,
                'enable_emergency_stop': self.config.enable_emergency_stop
            }
        }
    
    def get_audit_log(self, limit: int = 100) -> List[Dict[str, Any]]:
        """Get recent audit log entries."""
        return self.audit_log[-limit:]
    
    def get_security_metrics(self) -> Dict[str, Any]:
        """Get security metrics."""
        return self.metrics.copy()
    
    def get_security_alerts(self, severity_filter: Optional[str] = None) -> List[SecurityAlert]:
        """Get active security alerts."""
        return self.security_monitor.get_active_alerts(severity_filter)
    
    def resolve_security_alert(self, alert_id: str, resolution_note: Optional[str] = None):
        """Resolve a security alert."""
        self.security_monitor.resolve_alert(alert_id, resolution_note)
    
    def get_threat_analysis(self) -> Dict[str, Any]:
        """Get current threat analysis."""
        return self.security_monitor.get_threat_analysis()
    
    def validate_configuration(self) -> SecurityValidationResult:
        """Validate current security configuration."""
        return self.config_validator.validate_security_config(self.config)
    
    def get_security_recommendations(self, target_environment: str = "production") -> List[str]:
        """Get security recommendations for current configuration."""
        return self.config_validator.get_security_recommendations(self.config, target_environment)
    
    def assess_security_risk(self) -> Tuple[str, List[str]]:
        """Assess current security risk level."""
        return self.config_validator.assess_security_risk(self.config)
    
    def create_security_context(self, operation_name: str) -> SecurityContextManager:
        """Create a security context manager for an operation."""
        return SecurityContextManager(operation_name, self)
    
    def generate_security_report(self) -> Dict[str, Any]:
        """Generate comprehensive security report."""
        # Get security monitor report
        monitor_report = self.security_monitor.export_security_report()
        
        # Get configuration validation
        config_validation = self.validate_configuration()
        
        # Get threat analysis
        threat_analysis = self.get_threat_analysis()
        
        # Get system security check
        system_check = SecurityUtils.check_system_security()
        
        return {
            'report_timestamp': datetime.now().isoformat(),
            'security_manager_status': self.get_security_status(),
            'configuration_validation': {
                'is_valid': config_validation.is_valid,
                'security_score': config_validation.security_score,
                'warnings': config_validation.warnings,
                'errors': config_validation.errors,
                'recommendations': config_validation.recommendations
            },
            'monitoring_report': monitor_report,
            'threat_analysis': threat_analysis,
            'system_security_check': system_check,
            'security_recommendations': self.get_security_recommendations(),
            'risk_assessment': {
                'risk_level': self.assess_security_risk()[0],
                'risk_factors': self.assess_security_risk()[1]
            }
        }
    
    def export_security_logs(self, format: str = 'json') -> str:
        """Export security logs in specified format."""
        if format.lower() == 'json':
            import json
            return json.dumps(self.audit_log, indent=2, default=str)
        elif format.lower() == 'text':
            return SecurityUtils.generate_security_report(self.audit_log)
        else:
            raise ValueError(f"Unsupported format: {format}")
    
    def update_security_config(self, new_config: SecurityConfig):
        """Update security configuration with validation."""
        # Validate new configuration
        validation_result = self.config_validator.validate_security_config(new_config)
        
        if not validation_result.is_valid:
            raise SecurityViolation(f"Invalid security configuration: {validation_result.errors}")
        
        # Log configuration change
        self._log_security_event('configuration_updated', {
            'old_config_hash': hash(str(self.config.__dict__)),
            'new_config_hash': hash(str(new_config.__dict__)),
            'validation_score': validation_result.security_score
        })
        
        # Update configuration
        old_config = self.config
        self.config = new_config
        
        # Reinitialize components if needed
        try:
            self._init_components()
            logger.info(f"Security configuration updated (score: {validation_result.security_score}/100)")
        except Exception as e:
            # Rollback on failure
            self.config = old_config
            self._init_components()
            raise SecurityViolation(f"Failed to update security configuration: {e}")
    
    def add_security_alert_handler(self, handler: Callable[[SecurityAlert], None]):
        """Add a handler for security alerts."""
        self.security_monitor.add_alert_handler(handler)
    
    def cleanup(self):
        """Cleanup all security resources."""
        try:
            if hasattr(self, 'security_monitor'):
                self.security_monitor.stop_monitoring()
            
            if self.sandbox_executor:
                self.sandbox_executor.cleanup_all_sandboxes()
            
            if self.resource_limiter:
                self.resource_limiter.stop_monitoring()
            
            if self.file_handler:
                self.file_handler.cleanup_temp_files()
            
            logger.info("Security manager cleanup completed")
            
        except Exception as e:
            logger.error(f"Error during security manager cleanup: {e}")
    
    def __enter__(self):
        """Context manager entry."""
        return self
    
    def __exit__(self, exc_type, exc_val, exc_tb):
        """Context manager exit."""
        self.cleanup()