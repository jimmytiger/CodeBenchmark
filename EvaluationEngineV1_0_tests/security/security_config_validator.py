"""
Security Configuration Validator

Validates security configurations and provides recommendations
for secure testing environments.
"""

import logging
from typing import Dict, List, Optional, Any, Tuple
from pathlib import Path
from dataclasses import dataclass

from .security_manager import SecurityConfig
from .resource_limiter import ResourceLimits
from .command_validator import CommandPolicy
from .api_security import RateLimitConfig
from .secure_file_handler import FileAccessPolicy

logger = logging.getLogger(__name__)


@dataclass
class SecurityValidationResult:
    """Result of security configuration validation."""
    is_valid: bool
    warnings: List[str]
    errors: List[str]
    recommendations: List[str]
    security_score: int  # 0-100


class SecurityConfigValidator:
    """
    Validates security configurations and provides security recommendations.
    
    Features:
    - Configuration validation
    - Security best practices checking
    - Risk assessment
    - Recommendations generation
    """
    
    def __init__(self):
        """Initialize security configuration validator."""
        self.logger = logging.getLogger(f"{__name__}.SecurityConfigValidator")
    
    def validate_security_config(self, config: SecurityConfig) -> SecurityValidationResult:
        """
        Validate a security configuration.
        
        Args:
            config: Security configuration to validate
            
        Returns:
            Validation result with warnings, errors, and recommendations
        """
        warnings = []
        errors = []
        recommendations = []
        security_score = 100
        
        # Validate basic security settings
        self._validate_basic_settings(config, warnings, errors, recommendations)
        
        # Validate sandbox configuration
        if config.enable_sandbox:
            self._validate_sandbox_config(config, warnings, errors, recommendations)
        else:
            warnings.append("Sandbox execution is disabled - tests will run without isolation")
            security_score -= 20
            recommendations.append("Enable sandbox execution for better security isolation")
        
        # Validate resource limits
        if config.enable_resource_limits:
            self._validate_resource_limits(config, warnings, errors, recommendations)
        else:
            warnings.append("Resource limits are disabled - tests may consume excessive resources")
            security_score -= 15
            recommendations.append("Enable resource limits to prevent resource exhaustion")
        
        # Validate command validation
        if config.enable_command_validation:
            self._validate_command_policy(config, warnings, errors, recommendations)
        else:
            errors.append("Command validation is disabled - dangerous commands may be executed")
            security_score -= 30
            recommendations.append("Enable command validation to prevent dangerous command execution")
        
        # Validate API security
        if config.enable_api_security:
            self._validate_api_security(config, warnings, errors, recommendations)
        else:
            warnings.append("API security is disabled - API endpoints are unprotected")
            security_score -= 10
            recommendations.append("Enable API security for production environments")
        
        # Validate file security
        if config.enable_file_security:
            self._validate_file_security(config, warnings, errors, recommendations)
        else:
            warnings.append("File security is disabled - file operations are unrestricted")
            security_score -= 10
            recommendations.append("Enable file security to prevent unauthorized file access")
        
        # Validate audit logging
        if not config.enable_audit_logging:
            warnings.append("Audit logging is disabled - security events will not be logged")
            security_score -= 5
            recommendations.append("Enable audit logging for security monitoring")
        
        # Validate emergency stop
        if not config.enable_emergency_stop:
            warnings.append("Emergency stop is disabled - cannot halt operations during security incidents")
            security_score -= 5
            recommendations.append("Enable emergency stop for incident response")
        
        # Calculate final security score
        security_score = max(0, security_score - len(errors) * 10 - len(warnings) * 2)
        
        is_valid = len(errors) == 0
        
        self.logger.info(f"Security configuration validation completed: "
                        f"Valid={is_valid}, Score={security_score}, "
                        f"Warnings={len(warnings)}, Errors={len(errors)}")
        
        return SecurityValidationResult(
            is_valid=is_valid,
            warnings=warnings,
            errors=errors,
            recommendations=recommendations,
            security_score=security_score
        )
    
    def _validate_basic_settings(self, config: SecurityConfig, 
                                warnings: List[str], errors: List[str], 
                                recommendations: List[str]):
        """Validate basic security settings."""
        # Check execution time limits
        if config.max_execution_time <= 0:
            errors.append("Maximum execution time must be positive")
        elif config.max_execution_time > 3600:  # 1 hour
            warnings.append(f"Very long execution time limit: {config.max_execution_time}s")
            recommendations.append("Consider reducing execution time limit for better security")
        
        # Check memory limits
        if config.max_memory_mb <= 0:
            errors.append("Maximum memory must be positive")
        elif config.max_memory_mb > 8192:  # 8GB
            warnings.append(f"Very high memory limit: {config.max_memory_mb}MB")
            recommendations.append("Consider reducing memory limit to prevent resource exhaustion")
        
        # Check CPU limits
        if config.max_cpu_percent <= 0 or config.max_cpu_percent > 100:
            errors.append("CPU percentage must be between 1 and 100")
        elif config.max_cpu_percent > 90:
            warnings.append(f"Very high CPU limit: {config.max_cpu_percent}%")
            recommendations.append("Consider reducing CPU limit to prevent system overload")
        
        # Check network access
        if config.allow_network:
            warnings.append("Network access is enabled - tests can make external connections")
            recommendations.append("Disable network access unless required for testing")
    
    def _validate_sandbox_config(self, config: SecurityConfig, 
                                warnings: List[str], errors: List[str], 
                                recommendations: List[str]):
        """Validate sandbox configuration."""
        if config.sandbox_base_dir:
            sandbox_path = Path(config.sandbox_base_dir)
            
            # Check if sandbox directory exists and is writable
            if not sandbox_path.exists():
                try:
                    sandbox_path.mkdir(parents=True, exist_ok=True)
                except Exception as e:
                    errors.append(f"Cannot create sandbox directory: {e}")
            
            # Check permissions
            if sandbox_path.exists() and not sandbox_path.is_dir():
                errors.append("Sandbox base path is not a directory")
            
            # Check if it's in a safe location
            unsafe_paths = ['/etc', '/var', '/sys', '/proc', '/dev', '/root', '/boot']
            sandbox_str = str(sandbox_path.resolve())
            for unsafe_path in unsafe_paths:
                if sandbox_str.startswith(unsafe_path):
                    errors.append(f"Sandbox directory in unsafe location: {sandbox_str}")
                    break
    
    def _validate_resource_limits(self, config: SecurityConfig, 
                                 warnings: List[str], errors: List[str], 
                                 recommendations: List[str]):
        """Validate resource limits configuration."""
        if config.resource_limits:
            limits = config.resource_limits
            
            # Validate memory limits
            if limits.max_memory_mb and limits.max_memory_mb < 64:
                warnings.append("Very low memory limit may cause test failures")
            
            # Validate CPU limits
            if limits.max_cpu_percent and limits.max_cpu_percent < 10:
                warnings.append("Very low CPU limit may cause test timeouts")
            
            # Validate execution time
            if limits.max_execution_time and limits.max_execution_time < 30:
                warnings.append("Very short execution time limit may cause test failures")
            
            # Validate file limits
            if limits.max_open_files and limits.max_open_files < 10:
                warnings.append("Very low file descriptor limit may cause test failures")
            
            # Validate process limits
            if limits.max_processes and limits.max_processes < 2:
                warnings.append("Very low process limit may cause test failures")
        
        # Check monitoring interval
        if config.monitoring_interval < 0.1:
            warnings.append("Very short monitoring interval may impact performance")
        elif config.monitoring_interval > 10:
            warnings.append("Long monitoring interval may miss resource violations")
    
    def _validate_command_policy(self, config: SecurityConfig, 
                                warnings: List[str], errors: List[str], 
                                recommendations: List[str]):
        """Validate command validation policy."""
        if config.command_policy:
            policy = config.command_policy
            
            # Check if dangerous commands are blocked
            dangerous_commands = {'rm', 'sudo', 'wget', 'curl', 'chmod', 'chown'}
            if policy.blocked_commands:
                unblocked_dangerous = dangerous_commands - policy.blocked_commands
                if unblocked_dangerous:
                    warnings.append(f"Dangerous commands not blocked: {unblocked_dangerous}")
                    recommendations.append("Consider blocking all dangerous commands")
            else:
                warnings.append("No commands are explicitly blocked")
                recommendations.append("Define blocked commands list for better security")
            
            # Check shell operators
            if policy.allow_shell_operators:
                warnings.append("Shell operators are allowed - risk of command injection")
                recommendations.append("Disable shell operators unless required")
            
            # Check file redirection
            if policy.allow_file_redirection:
                warnings.append("File redirection is allowed - risk of unauthorized file access")
                recommendations.append("Disable file redirection unless required")
            
            # Check command length limits
            if policy.max_command_length > 2000:
                warnings.append("Very long command length limit may allow complex attacks")
                recommendations.append("Consider reducing maximum command length")
            
            # Check argument limits
            if policy.max_arguments > 100:
                warnings.append("Very high argument limit may allow resource exhaustion")
                recommendations.append("Consider reducing maximum argument count")
    
    def _validate_api_security(self, config: SecurityConfig, 
                              warnings: List[str], errors: List[str], 
                              recommendations: List[str]):
        """Validate API security configuration."""
        if not config.api_secret_key:
            warnings.append("No API secret key configured - using generated key")
            recommendations.append("Configure a strong API secret key for production")
        elif len(config.api_secret_key) < 32:
            warnings.append("API secret key is too short")
            recommendations.append("Use a longer API secret key (at least 32 characters)")
        
        if config.default_rate_limit:
            rate_config = config.default_rate_limit
            
            # Check rate limits
            if rate_config.requests_per_minute > 1000:
                warnings.append("Very high rate limit may not prevent abuse")
                recommendations.append("Consider reducing rate limits for better protection")
            
            if rate_config.burst_limit > 50:
                warnings.append("Very high burst limit may allow rapid attacks")
                recommendations.append("Consider reducing burst limit")
        else:
            warnings.append("No default rate limiting configured")
            recommendations.append("Configure default rate limits for API protection")
    
    def _validate_file_security(self, config: SecurityConfig, 
                               warnings: List[str], errors: List[str], 
                               recommendations: List[str]):
        """Validate file security configuration."""
        if config.file_access_policy:
            policy = config.file_access_policy
            
            # Check dangerous extensions
            dangerous_extensions = {'.exe', '.bat', '.sh', '.ps1', '.vbs'}
            if policy.allowed_extensions:
                dangerous_allowed = dangerous_extensions & policy.allowed_extensions
                if dangerous_allowed:
                    warnings.append(f"Dangerous file extensions allowed: {dangerous_allowed}")
                    recommendations.append("Remove dangerous extensions from allowed list")
            
            # Check file size limits
            if policy.max_file_size > 1024 * 1024 * 1024:  # 1GB
                warnings.append("Very large file size limit may allow resource exhaustion")
                recommendations.append("Consider reducing maximum file size")
            
            # Check executable files
            if policy.allow_executable:
                warnings.append("Executable files are allowed - security risk")
                recommendations.append("Disable executable files unless required")
            
            # Check symbolic links
            if policy.allow_symlinks:
                warnings.append("Symbolic links are allowed - risk of path traversal")
                recommendations.append("Disable symbolic links unless required")
        else:
            warnings.append("No file access policy configured - using defaults")
            recommendations.append("Configure explicit file access policy")
    
    def generate_secure_config(self, 
                              environment: str = "testing",
                              risk_level: str = "medium") -> SecurityConfig:
        """
        Generate a secure configuration based on environment and risk level.
        
        Args:
            environment: Target environment ("testing", "staging", "production")
            risk_level: Security risk level ("low", "medium", "high")
            
        Returns:
            Secure security configuration
        """
        # Base configuration
        config = SecurityConfig()
        
        # Adjust based on environment
        if environment == "production":
            config.enable_sandbox = True
            config.enable_resource_limits = True
            config.enable_command_validation = True
            config.enable_api_security = True
            config.enable_file_security = True
            config.enable_audit_logging = True
            config.enable_emergency_stop = True
            config.allow_network = False
            
        elif environment == "staging":
            config.enable_sandbox = True
            config.enable_resource_limits = True
            config.enable_command_validation = True
            config.enable_api_security = True
            config.enable_file_security = True
            config.allow_network = True  # May need external access
            
        else:  # testing
            config.enable_sandbox = True
            config.enable_resource_limits = True
            config.enable_command_validation = True
            config.allow_network = True
        
        # Adjust based on risk level
        if risk_level == "high":
            config.max_execution_time = 300  # 5 minutes
            config.max_memory_mb = 512
            config.max_cpu_percent = 50
            
            # Strict resource limits
            config.resource_limits = ResourceLimits(
                max_memory_mb=512,
                max_cpu_percent=50,
                max_execution_time=300,
                max_open_files=50,
                max_processes=5
            )
            
            # Strict command policy
            config.command_policy = CommandPolicy(
                allowed_commands={'python', 'pytest', 'echo', 'cat', 'ls'},
                blocked_commands={'rm', 'sudo', 'wget', 'curl', 'chmod', 'chown', 'kill'},
                allow_shell_operators=False,
                allow_file_redirection=False,
                max_command_length=200,
                max_arguments=10
            )
            
            # Strict rate limiting
            config.default_rate_limit = RateLimitConfig(
                requests_per_minute=30,
                requests_per_hour=500,
                burst_limit=5
            )
            
            # Strict file policy
            config.file_access_policy = FileAccessPolicy(
                allowed_extensions={'.txt', '.json', '.yaml', '.py'},
                max_file_size=10 * 1024 * 1024,  # 10MB
                allow_executable=False,
                allow_symlinks=False
            )
            
        elif risk_level == "medium":
            config.max_execution_time = 600  # 10 minutes
            config.max_memory_mb = 1024
            config.max_cpu_percent = 70
            
        else:  # low
            config.max_execution_time = 1200  # 20 minutes
            config.max_memory_mb = 2048
            config.max_cpu_percent = 80
        
        self.logger.info(f"Generated secure configuration for {environment} environment "
                        f"with {risk_level} risk level")
        
        return config
    
    def get_security_recommendations(self, 
                                   current_config: SecurityConfig,
                                   target_environment: str = "production") -> List[str]:
        """
        Get security recommendations for improving configuration.
        
        Args:
            current_config: Current security configuration
            target_environment: Target environment
            
        Returns:
            List of security recommendations
        """
        recommendations = []
        
        # Validate current configuration
        validation_result = self.validate_security_config(current_config)
        recommendations.extend(validation_result.recommendations)
        
        # Generate ideal configuration for comparison
        ideal_config = self.generate_secure_config(target_environment, "high")
        
        # Compare configurations and suggest improvements
        if not current_config.enable_sandbox and ideal_config.enable_sandbox:
            recommendations.append("Enable sandbox execution for better isolation")
        
        if not current_config.enable_resource_limits and ideal_config.enable_resource_limits:
            recommendations.append("Enable resource limits to prevent resource exhaustion")
        
        if not current_config.enable_command_validation and ideal_config.enable_command_validation:
            recommendations.append("Enable command validation to prevent dangerous commands")
        
        if current_config.max_execution_time > ideal_config.max_execution_time:
            recommendations.append(f"Reduce execution time limit to {ideal_config.max_execution_time}s")
        
        if current_config.max_memory_mb > ideal_config.max_memory_mb:
            recommendations.append(f"Reduce memory limit to {ideal_config.max_memory_mb}MB")
        
        if current_config.allow_network and not ideal_config.allow_network:
            recommendations.append("Disable network access unless required for testing")
        
        return list(set(recommendations))  # Remove duplicates
    
    def assess_security_risk(self, config: SecurityConfig) -> Tuple[str, List[str]]:
        """
        Assess security risk level of configuration.
        
        Args:
            config: Security configuration to assess
            
        Returns:
            Tuple of (risk_level, risk_factors)
        """
        risk_factors = []
        risk_score = 0
        
        # Check for high-risk configurations
        if not config.enable_sandbox:
            risk_factors.append("No sandbox isolation")
            risk_score += 30
        
        if not config.enable_command_validation:
            risk_factors.append("No command validation")
            risk_score += 25
        
        if config.allow_network:
            risk_factors.append("Network access enabled")
            risk_score += 15
        
        if not config.enable_resource_limits:
            risk_factors.append("No resource limits")
            risk_score += 20
        
        if config.max_execution_time > 1800:  # 30 minutes
            risk_factors.append("Very long execution time limit")
            risk_score += 10
        
        if config.max_memory_mb > 4096:  # 4GB
            risk_factors.append("Very high memory limit")
            risk_score += 10
        
        if not config.enable_audit_logging:
            risk_factors.append("No audit logging")
            risk_score += 5
        
        # Determine risk level
        if risk_score >= 50:
            risk_level = "HIGH"
        elif risk_score >= 25:
            risk_level = "MEDIUM"
        else:
            risk_level = "LOW"
        
        return risk_level, risk_factors