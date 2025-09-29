# Security Guide

This guide covers the comprehensive security features implemented in the Evaluation Engine Testing Framework.

## Overview

The security system provides multiple layers of protection:

1. **Sandboxed Execution** - Isolated execution environments
2. **Resource Limiting** - Prevent resource exhaustion
3. **Command Validation** - Block dangerous commands
4. **API Security** - Authentication and rate limiting
5. **Secure File Handling** - Safe file operations
6. **Security Management** - Centralized security control

## Components

### 1. Sandbox Executor

Provides isolated execution environments for running tests safely.

**Features:**
- Process isolation
- File system restrictions
- Resource limits
- Network isolation
- Timeout enforcement

**Usage:**
```python
from security.sandbox_executor import SandboxExecutor

executor = SandboxExecutor(
    base_sandbox_dir=Path("/tmp/sandbox"),
    max_execution_time=300,
    max_memory_mb=1024,
    allow_network=False
)

with executor.create_sandbox("test_env") as sandbox:
    result = sandbox.execute_command(["python", "test_script.py"])
    print(result['stdout'])
```

### 2. Resource Limiter

Monitors and enforces resource limits during execution.

**Features:**
- Memory usage monitoring
- CPU usage monitoring
- Execution time limits
- Process count limits
- File descriptor limits

**Usage:**
```python
from security.resource_limiter import ResourceLimiter, ResourceLimits

limits = ResourceLimits(
    max_memory_mb=512,
    max_cpu_percent=80,
    max_execution_time=300
)

limiter = ResourceLimiter(limits)

with limiter.monitor_resources():
    # Your code here
    pass
```

### 3. Command Validator

Validates and sanitizes commands before execution.

**Features:**
- Command whitelist/blacklist
- Shell injection prevention
- Argument validation
- Path restriction
- Environment variable validation

**Usage:**
```python
from security.command_validator import CommandValidator

validator = CommandValidator()

try:
    validated_cmd, env_vars = validator.validate_command("echo hello")
    # Command is safe to execute
except CommandValidationError as e:
    # Command is dangerous
    print(f"Command blocked: {e}")
```

### 4. API Security

Provides authentication and rate limiting for API endpoints.

**Features:**
- API key authentication
- JWT token authentication
- Permission-based authorization
- Rate limiting
- Audit logging

**Usage:**
```python
from security.api_security import APIAuthenticator, RateLimiter

# Authentication
auth = APIAuthenticator()
api_key = auth.generate_api_key("test_key", permissions=["read", "write"])

# Rate limiting
limiter = RateLimiter()
allowed, info = limiter.check_rate_limit("user_key")
```

### 5. Secure File Handler

Provides secure file operations with access controls.

**Features:**
- Path traversal prevention
- File type validation
- Size limits
- Secure temporary files
- Access logging

**Usage:**
```python
from security.secure_file_handler import SecureFileHandler

handler = SecureFileHandler(base_dir=Path("/secure/files"))

# Safe file operations
content = handler.safe_read_file("data.txt")
handler.safe_write_file("output.txt", "safe content")

# Temporary files
with handler.create_temp_file(suffix='.txt') as temp_file:
    temp_file.write_text("temporary data")
```

### 6. Security Manager

Central security management system that coordinates all components.

**Features:**
- Unified security configuration
- Security event monitoring
- Emergency stop capabilities
- Comprehensive audit logging
- Security metrics

**Usage:**
```python
from security.security_manager import SecurityManager, SecurityConfig

config = SecurityConfig(
    enable_sandbox=True,
    enable_resource_limits=True,
    enable_command_validation=True,
    enable_api_security=True,
    enable_file_security=True
)

manager = SecurityManager(config)

# Secure execution context
with manager.secure_execution_context("test_context") as sandbox:
    result = sandbox.execute_command(["python", "test.py"])

# Command validation and execution
result = manager.validate_and_execute_command("echo hello")

# API authentication
auth_result = manager.authenticate_api_request(key_id="...", key_secret="...")

# File operations
content = manager.secure_file_operation('read', 'file.txt')
```

## Security Configuration

### Basic Configuration

```python
from security.security_manager import SecurityConfig

config = SecurityConfig(
    # Enable/disable components
    enable_sandbox=True,
    enable_resource_limits=True,
    enable_command_validation=True,
    enable_api_security=True,
    enable_file_security=True,
    
    # Resource limits
    max_execution_time=300,
    max_memory_mb=1024,
    max_cpu_percent=80,
    
    # Security settings
    allow_network=False,
    enable_audit_logging=True,
    enable_emergency_stop=True
)
```

### Advanced Configuration

```python
from security.resource_limiter import ResourceLimits
from security.command_validator import CommandPolicy
from security.api_security import RateLimitConfig
from security.secure_file_handler import FileAccessPolicy

# Custom resource limits
resource_limits = ResourceLimits(
    max_memory_mb=2048,
    max_cpu_percent=90,
    max_execution_time=600,
    max_open_files=100,
    max_processes=10
)

# Custom command policy
command_policy = CommandPolicy(
    allowed_commands={'python', 'pytest', 'coverage'},
    blocked_commands={'rm', 'sudo', 'wget'},
    allow_shell_operators=False,
    max_command_length=500
)

# Custom rate limiting
rate_limit_config = RateLimitConfig(
    requests_per_minute=120,
    requests_per_hour=2000,
    burst_limit=20
)

# Custom file policy
file_policy = FileAccessPolicy(
    allowed_extensions={'.py', '.txt', '.json', '.yaml'},
    max_file_size=50 * 1024 * 1024,  # 50MB
    allow_executable=False
)

config = SecurityConfig(
    resource_limits=resource_limits,
    command_policy=command_policy,
    default_rate_limit=rate_limit_config,
    file_access_policy=file_policy
)
```

## Security Best Practices

### 1. Principle of Least Privilege

- Only enable necessary security components
- Use minimal permissions for API keys
- Restrict file access to required directories
- Limit resource usage to actual needs

### 2. Defense in Depth

- Use multiple security layers
- Enable all relevant security components
- Configure strict policies
- Monitor security events

### 3. Regular Security Audits

```python
# Check security status
status = manager.get_security_status()
print(f"Security enabled: {status['security_enabled']}")
print(f"Emergency stop: {status['emergency_stop']}")

# Review security metrics
metrics = manager.get_security_metrics()
print(f"Security violations: {metrics['security_violations']}")

# Audit log review
audit_log = manager.get_audit_log(limit=100)
for entry in audit_log:
    if entry['event_type'] == 'security_violation':
        print(f"Violation: {entry['details']}")
```

### 4. Emergency Procedures

```python
# Trigger emergency stop
manager.trigger_emergency_stop("Security breach detected")

# Reset emergency stop (admin only)
manager.reset_emergency_stop("Threat resolved")

# Disable security (extreme caution)
manager.disable_security("Maintenance mode")
```

## Common Security Scenarios

### 1. Testing Untrusted Code

```python
config = SecurityConfig(
    enable_sandbox=True,
    enable_resource_limits=True,
    enable_command_validation=True,
    max_execution_time=60,
    max_memory_mb=256,
    allow_network=False
)

manager = SecurityManager(config)

with manager.secure_execution_context("untrusted_test") as sandbox:
    # Run untrusted code safely
    result = sandbox.execute_command(["python", "untrusted_script.py"])
```

### 2. API Rate Limiting

```python
# Set up rate limiting for API endpoints
@manager.rate_limiter.rate_limit_decorator(
    key_extractor=lambda request: request.headers.get('X-API-Key'),
    endpoint='evaluation'
)
def evaluation_endpoint(request):
    # API endpoint implementation
    pass
```

### 3. Secure File Processing

```python
# Process uploaded files securely
with manager.file_handler.create_temp_dir() as temp_dir:
    # Copy uploaded file to secure location
    secure_file = manager.file_handler.safe_copy_file(
        uploaded_file_path,
        temp_dir / "input.txt"
    )
    
    # Process file safely
    content = manager.file_handler.safe_read_file(secure_file)
    processed_content = process_content(content)
    
    # Write results securely
    output_file = manager.file_handler.safe_write_file(
        temp_dir / "output.txt",
        processed_content
    )
```

## Troubleshooting

### Common Issues

1. **Sandbox Creation Fails**
   - Check directory permissions
   - Ensure sufficient disk space
   - Verify base directory exists

2. **Resource Limits Exceeded**
   - Increase resource limits
   - Optimize code for efficiency
   - Check for memory leaks

3. **Command Validation Errors**
   - Review command policy
   - Add necessary commands to whitelist
   - Check for shell injection attempts

4. **API Authentication Failures**
   - Verify API key credentials
   - Check key expiration
   - Review permission requirements

5. **File Operation Errors**
   - Check file permissions
   - Verify file extensions are allowed
   - Ensure file size is within limits

### Debug Mode

```python
import logging

# Enable debug logging
logging.basicConfig(level=logging.DEBUG)

# Security manager will log detailed information
manager = SecurityManager(config)
```

### Security Monitoring

```python
# Set up violation callbacks
def handle_violation(resource_type, usage):
    print(f"Resource violation: {resource_type}")
    # Send alert, log to external system, etc.

manager.resource_limiter.add_violation_callback('memory', handle_violation)
```

## Integration Examples

### With Flask API

```python
from flask import Flask, request, jsonify
from security.security_manager import SecurityManager

app = Flask(__name__)
manager = SecurityManager()

@app.before_request
def authenticate():
    api_key = request.headers.get('X-API-Key')
    api_secret = request.headers.get('X-API-Secret')
    
    try:
        auth_result = manager.authenticate_api_request(
            key_id=api_key,
            key_secret=api_secret
        )
        request.auth = auth_result
    except Exception as e:
        return jsonify({'error': 'Authentication failed'}), 401

@app.route('/evaluate', methods=['POST'])
def evaluate():
    # Check rate limit
    rate_result = manager.check_rate_limit(request.auth['key_id'])
    if not rate_result['allowed']:
        return jsonify({'error': 'Rate limit exceeded'}), 429
    
    # Secure execution
    with manager.secure_execution_context("evaluation") as sandbox:
        result = sandbox.execute_command(["python", "evaluate.py"])
        return jsonify({'result': result})
```

### With Testing Framework

```python
import pytest
from security.security_manager import SecurityManager

@pytest.fixture
def secure_manager():
    config = SecurityConfig(enable_sandbox=True)
    return SecurityManager(config)

def test_secure_evaluation(secure_manager):
    with secure_manager.secure_execution_context("test") as sandbox:
        result = sandbox.execute_command(["python", "test_script.py"])
        assert result['success']
```

## Performance Considerations

### Resource Monitoring Overhead

- Monitoring interval affects performance
- Lower intervals = higher accuracy, more overhead
- Recommended: 1-5 seconds for most use cases

### Sandbox Performance

- Sandbox creation has overhead
- Reuse sandboxes when possible
- Clean up promptly to free resources

### File Operations

- Validation adds small overhead
- Temporary files are cleaned automatically
- Use appropriate file size limits

## Security Updates

### Keeping Components Updated

1. Regularly update dependencies
2. Review security policies
3. Monitor for new threats
4. Update blocked command lists
5. Review audit logs regularly

### Security Patches

```bash
# Update security dependencies
pip install -r security_requirements.txt --upgrade

# Run security tests
python -m pytest tests/unit/test_security_components.py

# Run security demonstration
python demo_security_features.py
```

This comprehensive security system provides robust protection for the evaluation engine testing framework while maintaining usability and performance.