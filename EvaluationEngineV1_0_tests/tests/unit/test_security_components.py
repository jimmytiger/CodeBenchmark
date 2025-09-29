"""
Unit tests for security components.
"""

import pytest
import tempfile
import time
import os
from pathlib import Path
from unittest.mock import Mock, patch, MagicMock

from EvaluationEngineV1_0_tests.security.sandbox_executor import SandboxExecutor, SandboxExecutionError
from EvaluationEngineV1_0_tests.security.resource_limiter import ResourceLimiter, ResourceLimits, ResourceLimitExceeded
from EvaluationEngineV1_0_tests.security.command_validator import CommandValidator, CommandPolicy, CommandValidationError
from EvaluationEngineV1_0_tests.security.api_security import APIAuthenticator, RateLimiter, AuthenticationError, RateLimitExceeded
from EvaluationEngineV1_0_tests.security.secure_file_handler import SecureFileHandler, FileAccessPolicy, SecureFileError
from EvaluationEngineV1_0_tests.security.security_manager import SecurityManager, SecurityConfig, SecurityViolation
from EvaluationEngineV1_0_tests.security.security_monitor import SecurityMonitor, SecurityAlert
from EvaluationEngineV1_0_tests.security.security_config_validator import SecurityConfigValidator, SecurityValidationResult
from EvaluationEngineV1_0_tests.security.security_utils import SecurityUtils, SecurityContextManager


class TestSandboxExecutor:
    """Test sandbox executor functionality."""
    
    def test_sandbox_creation(self):
        """Test sandbox environment creation."""
        with tempfile.TemporaryDirectory() as temp_dir:
            executor = SandboxExecutor(base_sandbox_dir=Path(temp_dir))
            
            with executor.create_sandbox("test_sandbox") as sandbox:
                assert sandbox is not None
                assert sandbox.sandbox_path.exists()
                assert sandbox.working_dir.exists()
    
    def test_command_execution(self):
        """Test command execution in sandbox."""
        with tempfile.TemporaryDirectory() as temp_dir:
            executor = SandboxExecutor(
                base_sandbox_dir=Path(temp_dir),
                max_memory_mb=0,  # Disable memory limits for testing
                max_execution_time=0  # Disable time limits for testing
            )
            
            with executor.create_sandbox("test_sandbox") as sandbox:
                # Use a simpler command that doesn't require resource limits
                result = sandbox.execute_command(["python", "-c", "print('hello world')"])
                assert result['success'] is True
                assert "hello world" in result['stdout']
    
    def test_dangerous_command_blocking(self):
        """Test that dangerous commands are blocked."""
        with tempfile.TemporaryDirectory() as temp_dir:
            executor = SandboxExecutor(base_sandbox_dir=Path(temp_dir))
            
            with executor.create_sandbox("test_sandbox") as sandbox:
                with pytest.raises(SandboxExecutionError):
                    sandbox.execute_command(["rm", "-rf", "/"])
    
    def test_file_operations(self):
        """Test file operations in sandbox."""
        with tempfile.TemporaryDirectory() as temp_dir:
            executor = SandboxExecutor(base_sandbox_dir=Path(temp_dir))
            
            with executor.create_sandbox("test_sandbox") as sandbox:
                # Write file
                test_content = "test content"
                file_path = sandbox.write_file("test.txt", test_content)
                assert file_path.exists()
                
                # Read file
                content = sandbox.get_file_content("test.txt")
                assert content == test_content
                
                # List files
                files = sandbox.list_files()
                assert "test.txt" in files


class TestResourceLimiter:
    """Test resource limiter functionality."""
    
    def test_resource_monitoring(self):
        """Test resource monitoring."""
        limits = ResourceLimits(
            max_memory_mb=100,
            max_cpu_percent=50,
            max_execution_time=10
        )
        
        limiter = ResourceLimiter(limits)
        
        with limiter.monitor_resources():
            time.sleep(0.1)  # Brief execution
            usage = limiter.get_current_usage()
            assert usage is not None
    
    def test_memory_limit_enforcement(self):
        """Test memory limit enforcement."""
        limits = ResourceLimits(max_memory_mb=1)  # Very low limit
        limiter = ResourceLimiter(limits, grace_period=0.1)
        
        # Mock the monitoring loop to simulate violation
        with patch.object(limiter, '_check_limits') as mock_check:
            mock_check.side_effect = ResourceLimitExceeded("Memory limit exceeded")
            
            with pytest.raises(ResourceLimitExceeded):
                with limiter.monitor_resources():
                    time.sleep(0.2)  # Wait for monitoring to detect violation
    
    def test_usage_summary(self):
        """Test usage summary generation."""
        limits = ResourceLimits(max_memory_mb=100)
        limiter = ResourceLimiter(limits)
        
        with limiter.monitor_resources():
            time.sleep(0.1)
            summary = limiter.get_usage_summary()
            assert 'current_usage' in summary
            assert 'limits' in summary


class TestCommandValidator:
    """Test command validator functionality."""
    
    def test_allowed_command_validation(self):
        """Test validation of allowed commands."""
        validator = CommandValidator()
        
        # Test allowed command
        validated_cmd, env_vars = validator.validate_command("echo hello")
        assert validated_cmd == ["echo", "hello"]
        assert isinstance(env_vars, dict)
    
    def test_blocked_command_validation(self):
        """Test blocking of dangerous commands."""
        validator = CommandValidator()
        
        # Test blocked command
        with pytest.raises(CommandValidationError):
            validator.validate_command("rm -rf /")
    
    def test_shell_injection_prevention(self):
        """Test prevention of shell injection."""
        validator = CommandValidator()
        
        # Test shell injection attempts
        with pytest.raises(CommandValidationError):
            validator.validate_command("echo hello; rm -rf /")
        
        with pytest.raises(CommandValidationError):
            validator.validate_command("echo `rm -rf /`")
    
    def test_custom_policy(self):
        """Test custom command policy."""
        policy = CommandPolicy(
            allowed_commands={'custom_cmd'},
            blocked_commands={'echo'},
            allowed_paths={'/usr/bin', '/bin'},
            blocked_paths={'/etc'},
            allow_shell_operators=False
        )
        
        validator = CommandValidator(policy)
        
        # Test custom allowed command
        validated_cmd, _ = validator.validate_command("custom_cmd arg")
        assert validated_cmd == ["custom_cmd", "arg"]
        
        # Test blocked command (even though normally allowed)
        with pytest.raises(CommandValidationError):
            validator.validate_command("echo hello")
    
    def test_argument_validation(self):
        """Test argument validation."""
        validator = CommandValidator()
        
        # Test long command
        long_cmd = "echo " + "a" * 2000
        with pytest.raises(CommandValidationError):
            validator.validate_command(long_cmd)
        
        # Test too many arguments
        many_args = ["echo"] + ["arg"] * 100
        with pytest.raises(CommandValidationError):
            validator.validate_command(many_args)


class TestAPIAuthenticator:
    """Test API authenticator functionality."""
    
    def test_api_key_generation(self):
        """Test API key generation."""
        auth = APIAuthenticator()
        
        api_key = auth.generate_api_key(
            name="test_key",
            permissions=["read", "write"]
        )
        
        assert api_key.key_id
        assert api_key.key_secret
        assert api_key.name == "test_key"
        assert api_key.permissions == ["read", "write"]
    
    def test_api_key_authentication(self):
        """Test API key authentication."""
        auth = APIAuthenticator()
        
        # Generate key
        api_key = auth.generate_api_key("test_key")
        
        # Authenticate with correct credentials
        authenticated_key = auth.authenticate_api_key(
            api_key.key_id,
            api_key.key_secret
        )
        assert authenticated_key.key_id == api_key.key_id
        
        # Authenticate with wrong credentials
        with pytest.raises(AuthenticationError):
            auth.authenticate_api_key(api_key.key_id, "wrong_secret")
    
    def test_jwt_token_generation(self):
        """Test JWT token generation and authentication."""
        auth = APIAuthenticator()
        
        # Generate token
        token = auth.generate_jwt_token(
            user_id="test_user",
            permissions=["read"]
        )
        assert isinstance(token, str)
        
        # Authenticate token
        payload = auth.authenticate_jwt_token(token)
        assert payload['user_id'] == "test_user"
        assert payload['permissions'] == ["read"]
    
    def test_permission_checking(self):
        """Test permission checking."""
        auth = APIAuthenticator()
        
        # Test admin permission
        assert auth.check_permission(["admin"], "any_permission")
        
        # Test specific permission
        assert auth.check_permission(["read", "write"], "read")
        assert not auth.check_permission(["read"], "write")
        
        # Test wildcard permission
        assert auth.check_permission(["api:*"], "api:read")
        assert not auth.check_permission(["api:*"], "db:read")


class TestRateLimiter:
    """Test rate limiter functionality."""
    
    def test_rate_limit_checking(self):
        """Test rate limit checking."""
        limiter = RateLimiter()
        
        # First request should be allowed
        allowed, info = limiter.check_rate_limit("test_key")
        assert allowed is True
        assert 'remaining_minute' in info
    
    def test_rate_limit_enforcement(self):
        """Test rate limit enforcement."""
        from EvaluationEngineV1_0_tests.security.api_security import RateLimitConfig
        
        config = RateLimitConfig(requests_per_minute=2)
        limiter = RateLimiter(config)
        
        # First two requests should be allowed
        allowed, _ = limiter.check_rate_limit("test_key")
        assert allowed is True
        
        allowed, _ = limiter.check_rate_limit("test_key")
        assert allowed is True
        
        # Third request should be blocked
        allowed, _ = limiter.check_rate_limit("test_key")
        assert allowed is False
    
    def test_rate_limit_reset(self):
        """Test rate limit reset."""
        limiter = RateLimiter()
        
        # Make some requests
        limiter.check_rate_limit("test_key")
        limiter.check_rate_limit("test_key")
        
        # Reset and check
        limiter.reset_rate_limit("test_key")
        status = limiter.get_rate_limit_status("test_key")
        assert status['remaining_minute'] == limiter.default_config.requests_per_minute


class TestSecureFileHandler:
    """Test secure file handler functionality."""
    
    def test_file_validation(self):
        """Test file path validation."""
        with tempfile.TemporaryDirectory() as temp_dir:
            # Create policy that allows the temp directory
            policy = FileAccessPolicy(
                allowed_extensions={'.txt', '.py'},
                blocked_extensions={'.exe'},
                allowed_paths={str(temp_dir)},
                blocked_paths={'/etc', '/var'},
                max_file_size=1024*1024
            )
            handler = SecureFileHandler(base_dir=Path(temp_dir), policy=policy)
            
            # Valid path
            valid_path = Path(temp_dir) / "test.txt"
            validated = handler.validate_path(valid_path)
            assert validated == valid_path.resolve()
            
            # Invalid extension
            with pytest.raises(SecureFileError):
                handler.validate_path(Path(temp_dir) / "test.exe")
    
    def test_safe_file_operations(self):
        """Test safe file operations."""
        with tempfile.TemporaryDirectory() as temp_dir:
            # Create policy that allows the temp directory
            policy = FileAccessPolicy(
                allowed_extensions={'.txt', '.py'},
                blocked_extensions={'.exe'},
                allowed_paths={str(temp_dir)},
                blocked_paths={'/etc', '/var'},
                max_file_size=1024*1024
            )
            handler = SecureFileHandler(base_dir=Path(temp_dir), policy=policy)
            
            test_file = Path(temp_dir) / "test.txt"
            test_content = "test content"
            
            # Write file
            written_path = handler.safe_write_file(test_file, test_content)
            assert written_path.exists()
            
            # Read file
            content = handler.safe_read_file(test_file)
            assert content == test_content
            
            # Delete file
            deleted = handler.safe_delete_file(test_file)
            assert deleted is True
            assert not test_file.exists()
    
    def test_temporary_file_handling(self):
        """Test temporary file handling."""
        with tempfile.TemporaryDirectory() as temp_dir:
            handler = SecureFileHandler(base_dir=Path(temp_dir))
            
            # Create temporary file
            with handler.create_temp_file(suffix='.txt', content='temp content') as temp_path:
                assert temp_path.exists()
                assert temp_path.read_text() == 'temp content'
            
            # File should be cleaned up
            assert not temp_path.exists()
    
    def test_checksum_calculation(self):
        """Test file checksum calculation."""
        with tempfile.TemporaryDirectory() as temp_dir:
            # Create policy that allows the temp directory
            policy = FileAccessPolicy(
                allowed_extensions={'.txt', '.py'},
                blocked_extensions={'.exe'},
                allowed_paths={str(temp_dir)},
                blocked_paths={'/etc', '/var'},
                max_file_size=1024*1024
            )
            handler = SecureFileHandler(base_dir=Path(temp_dir), policy=policy)
            
            test_file = Path(temp_dir) / "test.txt"
            test_content = "test content"
            
            handler.safe_write_file(test_file, test_content)
            checksum = handler.calculate_checksum(test_file)
            
            assert isinstance(checksum, str)
            assert len(checksum) == 64  # SHA256 hex length


class TestSecurityManager:
    """Test security manager functionality."""
    
    def test_security_manager_initialization(self):
        """Test security manager initialization."""
        config = SecurityConfig(
            enable_sandbox=True,
            enable_resource_limits=True,
            enable_command_validation=True,
            enable_api_security=True,
            enable_file_security=True
        )
        
        manager = SecurityManager(config)
        
        status = manager.get_security_status()
        assert status['security_enabled'] is True
        assert status['components']['sandbox_executor'] is True
        assert status['components']['resource_limiter'] is True
        assert status['components']['command_validator'] is True
        assert status['components']['api_authenticator'] is True
        assert status['components']['file_handler'] is True
    
    def test_secure_execution_context(self):
        """Test secure execution context."""
        with tempfile.TemporaryDirectory() as temp_dir:
            config = SecurityConfig(
                enable_sandbox=True,
                sandbox_base_dir=Path(temp_dir),
                max_memory_mb=0,  # Disable memory limits for testing
                max_execution_time=0  # Disable time limits for testing
            )
            manager = SecurityManager(config)
            
            with manager.secure_execution_context("test_context") as sandbox:
                assert sandbox is not None
                result = sandbox.execute_command(["python", "-c", "print('test')"])
                assert result['success'] is True
    
    def test_command_validation_and_execution(self):
        """Test command validation and execution."""
        manager = SecurityManager()
        
        # Valid command
        result = manager.validate_and_execute_command("echo hello")
        assert result['success'] is True
        
        # Invalid command should raise SecurityViolation
        with pytest.raises(SecurityViolation):
            manager.validate_and_execute_command("rm -rf /")
    
    def test_api_authentication(self):
        """Test API authentication through security manager."""
        manager = SecurityManager()
        
        # Generate API key
        api_key = manager.api_authenticator.generate_api_key("test_key")
        
        # Authenticate
        auth_result = manager.authenticate_api_request(
            key_id=api_key.key_id,
            key_secret=api_key.key_secret
        )
        assert auth_result['type'] == 'api_key'
        assert auth_result['key_id'] == api_key.key_id
    
    def test_emergency_stop(self):
        """Test emergency stop functionality."""
        manager = SecurityManager()
        
        # Trigger emergency stop
        manager.trigger_emergency_stop("Test emergency")
        
        status = manager.get_security_status()
        assert status['emergency_stop'] is True
        
        # Operations should be blocked
        with pytest.raises(SecurityViolation):
            manager.validate_and_execute_command("echo test")
    
    def test_security_metrics(self):
        """Test security metrics collection."""
        manager = SecurityManager()
        
        # Perform some operations
        manager.validate_and_execute_command("echo test")
        
        metrics = manager.get_security_metrics()
        assert 'command_validations' in metrics
        assert metrics['command_validations'] > 0
    
    def test_audit_logging(self):
        """Test audit logging."""
        manager = SecurityManager()
        
        # Perform operation that generates audit log
        manager.validate_and_execute_command("echo test")
        
        audit_log = manager.get_audit_log()
        assert len(audit_log) > 0
        assert any(entry['event_type'] == 'command_executed' for entry in audit_log)


if __name__ == "__main__":
    pytest.main([__file__])