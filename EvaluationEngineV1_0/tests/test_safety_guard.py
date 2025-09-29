"""
Comprehensive tests for the safety guard framework.

This module includes unit tests, integration tests, and penetration testing
scenarios to validate the safety system's effectiveness.
"""

import os
import pytest
import tempfile
import time
from datetime import datetime, timedelta
from unittest.mock import Mock, patch, MagicMock

from EvaluationEngineV1_0.core.safety_guard import (
    SafetyGuard,
    ResourceMonitor,
    CommandFilter,
    IncidentLogger,
    SafetyIncident,
    create_test_safety_config,
    create_penetration_test_scenarios
)
from EvaluationEngineV1_0.core.data_models import SafetyConfig
from EvaluationEngineV1_0.core.exceptions import SafetyViolationError


class TestSafetyIncident:
    """Test SafetyIncident data class."""
    
    def test_incident_creation(self):
        """Test creating a safety incident."""
        incident = SafetyIncident(
            incident_id="test_001",
            timestamp=datetime.now(),
            incident_type="test_violation",
            severity="medium",
            description="Test incident"
        )
        
        assert incident.incident_id == "test_001"
        assert incident.incident_type == "test_violation"
        assert incident.severity == "medium"
        assert incident.description == "Test incident"
        assert not incident.resolved
    
    def test_incident_to_dict(self):
        """Test converting incident to dictionary."""
        timestamp = datetime.now()
        incident = SafetyIncident(
            incident_id="test_001",
            timestamp=timestamp,
            incident_type="test_violation",
            severity="high",
            description="Test incident",
            context={"key": "value"},
            action_taken="blocked",
            resolved=True
        )
        
        result = incident.to_dict()
        
        assert result["incident_id"] == "test_001"
        assert result["timestamp"] == timestamp.isoformat()
        assert result["incident_type"] == "test_violation"
        assert result["severity"] == "high"
        assert result["description"] == "Test incident"
        assert result["context"] == {"key": "value"}
        assert result["action_taken"] == "blocked"
        assert result["resolved"] is True


class TestResourceMonitor:
    """Test ResourceMonitor class."""
    
    def test_resource_monitor_initialization(self):
        """Test resource monitor initialization."""
        limits = {
            "max_memory_mb": 512,
            "max_cpu_percent": 75.0,
            "max_processes": 5
        }
        
        monitor = ResourceMonitor(limits)
        
        assert monitor.max_memory_mb == 512
        assert monitor.max_cpu_percent == 75.0
        assert monitor.max_processes == 5
    
    def test_within_limits_default(self):
        """Test that resource monitor starts within limits."""
        limits = {
            "max_memory_mb": 1024,
            "max_cpu_percent": 80.0,
            "max_processes": 10
        }
        
        monitor = ResourceMonitor(limits)
        within_limits, reason = monitor.within_limits()
        
        # Should be within limits initially
        assert within_limits is True
        assert reason is None
    
    @patch('psutil.virtual_memory')
    def test_memory_limit_exceeded(self, mock_memory):
        """Test memory limit detection."""
        # Mock memory usage that exceeds limit
        mock_memory.return_value.used = 2 * 1024 * 1024 * 1024  # 2GB
        
        limits = {"max_memory_mb": 100}  # 100MB limit
        monitor = ResourceMonitor(limits)
        monitor.initial_memory = 0  # Start from 0 for easier calculation
        
        within_limits, reason = monitor.within_limits()
        
        assert within_limits is False
        assert "Memory usage" in reason
        assert "exceeds limit" in reason
    
    def test_get_current_usage(self):
        """Test getting current resource usage."""
        limits = {"max_memory_mb": 1024}
        monitor = ResourceMonitor(limits)
        
        usage = monitor.get_current_usage()
        
        assert isinstance(usage, dict)
        assert "memory_mb" in usage
        assert "cpu_percent" in usage
        assert "uptime_seconds" in usage
        assert usage["uptime_seconds"] >= 0


class TestCommandFilter:
    """Test CommandFilter class."""
    
    def test_command_filter_initialization(self):
        """Test command filter initialization."""
        patterns = [r"rm\s+-rf", r"sudo\s+"]
        filter_obj = CommandFilter(patterns)
        
        assert len(filter_obj.dangerous_patterns) == 2
        assert len(filter_obj.builtin_patterns) > 0
    
    def test_dangerous_command_detection(self):
        """Test detection of dangerous commands."""
        patterns = [r"custom_dangerous"]
        filter_obj = CommandFilter(patterns)
        
        # Test built-in dangerous patterns
        dangerous_commands = [
            "rm -rf /",
            "sudo rm file",
            "chmod 777 /etc",
            "eval('malicious code')",
            "exec('malicious code')",
            "subprocess.call(['rm', 'file'])",
            "os.system('rm file')"
        ]
        
        for cmd in dangerous_commands:
            is_dangerous, pattern = filter_obj.is_dangerous_command(cmd)
            assert is_dangerous is True, f"Command '{cmd}' should be detected as dangerous"
            assert pattern is not None
    
    def test_safe_command_detection(self):
        """Test that safe commands are not flagged."""
        patterns = []
        filter_obj = CommandFilter(patterns)
        
        safe_commands = [
            "ls -la",
            "cat file.txt",
            "echo 'hello world'",
            "python script.py",
            "git status",
            "mkdir new_dir"
        ]
        
        for cmd in safe_commands:
            is_dangerous, pattern = filter_obj.is_dangerous_command(cmd)
            assert is_dangerous is False, f"Command '{cmd}' should not be flagged as dangerous"
            assert pattern is None
    
    def test_custom_pattern_detection(self):
        """Test detection of custom dangerous patterns."""
        patterns = [r"custom_bad_command"]
        filter_obj = CommandFilter(patterns)
        
        is_dangerous, pattern = filter_obj.is_dangerous_command("custom_bad_command arg")
        assert is_dangerous is True
        assert "custom_bad_command" in pattern
    
    def test_empty_command(self):
        """Test handling of empty commands."""
        filter_obj = CommandFilter([])
        
        is_dangerous, pattern = filter_obj.is_dangerous_command("")
        assert is_dangerous is False
        assert pattern is None
        
        is_dangerous, pattern = filter_obj.is_dangerous_command(None)
        assert is_dangerous is False
        assert pattern is None


class TestIncidentLogger:
    """Test IncidentLogger class."""
    
    def test_incident_logger_initialization(self):
        """Test incident logger initialization."""
        logger = IncidentLogger()
        
        assert len(logger.incidents) == 0
        assert logger.log_file is None
    
    def test_log_incident(self):
        """Test logging an incident."""
        logger = IncidentLogger()
        
        incident_id = logger.log_incident(
            "test_type",
            "Test description",
            severity="high",
            context={"key": "value"},
            action_taken="blocked"
        )
        
        assert incident_id.startswith("incident_")
        assert len(logger.incidents) == 1
        
        incident = logger.incidents[0]
        assert incident.incident_type == "test_type"
        assert incident.description == "Test description"
        assert incident.severity == "high"
        assert incident.context == {"key": "value"}
        assert incident.action_taken == "blocked"
    
    def test_get_incidents_filtering(self):
        """Test filtering incidents by various criteria."""
        logger = IncidentLogger()
        
        # Log different types of incidents
        logger.log_incident("type1", "Description 1", severity="low")
        logger.log_incident("type2", "Description 2", severity="high")
        logger.log_incident("type1", "Description 3", severity="medium")
        
        # Filter by type
        type1_incidents = logger.get_incidents(incident_type="type1")
        assert len(type1_incidents) == 2
        
        # Filter by severity
        high_incidents = logger.get_incidents(severity="high")
        assert len(high_incidents) == 1
        
        # Filter by time
        recent_incidents = logger.get_incidents(since=datetime.now() - timedelta(minutes=1))
        assert len(recent_incidents) == 3
    
    def test_incident_count(self):
        """Test getting incident count."""
        logger = IncidentLogger()
        
        assert logger.get_incident_count() == 0
        
        logger.log_incident("test", "Test incident")
        assert logger.get_incident_count() == 1
        
        logger.log_incident("test", "Another incident")
        assert logger.get_incident_count() == 2
    
    def test_clear_incidents(self):
        """Test clearing incidents."""
        logger = IncidentLogger()
        
        logger.log_incident("test", "Test incident")
        assert logger.get_incident_count() == 1
        
        logger.clear_incidents()
        assert logger.get_incident_count() == 0


class TestSafetyGuard:
    """Test SafetyGuard class."""
    
    def test_safety_guard_initialization(self):
        """Test safety guard initialization."""
        config = create_test_safety_config()
        guard = SafetyGuard(config)
        
        assert guard.config == config
        assert len(guard.tool_whitelist) == len(config.allowed_tools)
        assert guard.safety_enabled is True
        assert guard.violation_count == 0
    
    def test_tool_validation(self):
        """Test tool whitelist validation."""
        config = SafetyConfig(allowed_tools=["python", "git"])
        guard = SafetyGuard(config)
        
        assert guard.validate_tool("python") is True
        assert guard.validate_tool("git") is True
        assert guard.validate_tool("rm") is False
        assert guard.validate_tool("sudo") is False
    
    def test_add_remove_tools(self):
        """Test adding and removing tools from whitelist."""
        config = SafetyConfig(allowed_tools=["python"])
        guard = SafetyGuard(config)
        
        assert guard.validate_tool("git") is False
        
        guard.add_allowed_tool("git")
        assert guard.validate_tool("git") is True
        
        guard.remove_allowed_tool("git")
        assert guard.validate_tool("git") is False
    
    def test_action_validation_safe(self):
        """Test validation of safe actions."""
        config = create_test_safety_config()
        guard = SafetyGuard(config)
        
        # Create safe action
        action = create_mock_action("echo 'hello world'")
        
        is_valid, reason = guard.validate_action(action)
        
        assert is_valid is True
        assert reason is None
    
    def test_action_validation_dangerous(self):
        """Test validation of dangerous actions."""
        config = create_test_safety_config()
        guard = SafetyGuard(config)
        
        # Create dangerous action
        action = create_mock_action("rm -rf /")
        
        is_valid, reason = guard.validate_action(action)
        
        assert is_valid is False
        assert "Dangerous command blocked" in reason
        assert guard.violation_count == 1
    
    def test_tool_whitelist_validation(self):
        """Test tool whitelist validation in actions."""
        config = SafetyConfig(allowed_tools=["python"])
        guard = SafetyGuard(config)
        
        # Action with allowed tool
        allowed_action = create_mock_action("python script.py", tool="python")
        
        is_valid, reason = guard.validate_action(allowed_action)
        assert is_valid is True
        
        # Action with disallowed tool
        disallowed_action = create_mock_action("rm file", tool="rm")
        
        is_valid, reason = guard.validate_action(disallowed_action)
        assert is_valid is False
        assert "not allowed" in reason
    
    @patch('EvaluationEngineV1_0.core.safety_guard.ResourceMonitor.within_limits')
    def test_is_safe_to_continue_resource_limit(self, mock_within_limits):
        """Test safety check with resource limits exceeded."""
        mock_within_limits.return_value = (False, "Memory limit exceeded")
        
        config = create_test_safety_config()
        guard = SafetyGuard(config)
        
        is_safe, reason = guard.is_safe_to_continue({}, "test observation")
        
        assert is_safe is False
        assert "Memory limit exceeded" in reason
    
    def test_is_safe_to_continue_dangerous_observation(self):
        """Test safety check with dangerous content in observation."""
        config = create_test_safety_config()
        guard = SafetyGuard(config)
        
        # Dangerous observation should be logged but not block continuation
        is_safe, reason = guard.is_safe_to_continue({}, "rm -rf /")
        
        assert is_safe is True  # Dangerous observation doesn't block continuation
        assert reason is None
        
        # But it should be logged as an incident
        incidents = guard.incident_logger.get_incidents(incident_type="dangerous_content_detected")
        assert len(incidents) > 0
    
    def test_excessive_violations_disable_safety(self):
        """Test that excessive violations disable the safety system."""
        config = create_test_safety_config()
        guard = SafetyGuard(config)
        guard.max_violations = 3  # Lower threshold for testing
        
        # Create dangerous action
        action = create_mock_action("rm -rf /")
        
        # Trigger violations up to the limit
        for i in range(3):
            is_valid, reason = guard.validate_action(action)
            assert is_valid is False
        
        # Safety system should now be disabled
        assert guard.safety_enabled is False
        
        # Further actions should be blocked due to disabled safety
        is_valid, reason = guard.validate_action(action)
        assert is_valid is False
        assert "Safety system disabled" in reason
    
    def test_get_safety_metrics(self):
        """Test getting safety metrics."""
        config = create_test_safety_config()
        guard = SafetyGuard(config)
        
        # Log some incidents
        guard.incident_logger.log_incident("test_type", "Test incident", severity="medium")
        guard.violation_count = 2
        
        metrics = guard.get_safety_metrics()
        
        assert "total_incidents" in metrics
        assert "violation_count" in metrics
        assert "safety_enabled" in metrics
        assert "allowed_tools" in metrics
        assert "resource_usage" in metrics
        assert "incidents_by_type" in metrics
        assert "incidents_by_severity" in metrics
        
        assert metrics["total_incidents"] == 1
        assert metrics["violation_count"] == 2
        assert metrics["safety_enabled"] is True
        assert isinstance(metrics["allowed_tools"], list)
    
    def test_reset_safety_guard(self):
        """Test resetting safety guard state."""
        config = create_test_safety_config()
        guard = SafetyGuard(config)
        
        # Modify state
        guard.violation_count = 5
        guard.safety_enabled = False
        guard.incident_logger.log_incident("test", "Test incident")
        
        # Reset
        guard.reset()
        
        assert guard.violation_count == 0
        assert guard.safety_enabled is True
        assert guard.incident_logger.get_incident_count() == 0
    
    def test_shutdown_safety_guard(self):
        """Test shutting down safety guard."""
        config = create_test_safety_config()
        guard = SafetyGuard(config)
        
        # Add some state
        guard.incident_logger.log_incident("test", "Test incident")
        
        # Shutdown should log final state
        guard.shutdown()
        
        # Should have logged a shutdown incident
        incidents = guard.incident_logger.get_incidents(incident_type="safety_guard_shutdown")
        assert len(incidents) == 1


class TestPenetrationScenarios:
    """Test penetration testing scenarios."""
    
    def test_penetration_test_scenarios(self):
        """Test all penetration testing scenarios."""
        config = create_test_safety_config()
        guard = SafetyGuard(config)
        
        scenarios = create_penetration_test_scenarios()
        
        for scenario in scenarios:
            action = create_mock_action(scenario["action"])
            
            is_valid, reason = guard.validate_action(action)
            
            if scenario["expected_blocked"]:
                assert is_valid is False, f"Scenario '{scenario['name']}' should be blocked"
                assert reason is not None
            else:
                assert is_valid is True, f"Scenario '{scenario['name']}' should be allowed"
                assert reason is None
    
    def test_resource_exhaustion_scenarios(self):
        """Test resource exhaustion detection."""
        # Create config with very low limits for testing
        config = SafetyConfig(
            resource_limits={
                "max_memory_mb": 1,  # Very low limit
                "max_cpu_percent": 1.0,
                "max_processes": 1
            }
        )
        
        guard = SafetyGuard(config)
        
        # The resource monitor should detect limits being exceeded
        # (This test may be flaky depending on actual system usage)
        with patch.object(guard.resource_monitor, 'within_limits') as mock_limits:
            mock_limits.return_value = (False, "Test resource limit exceeded")
            
            is_safe, reason = guard.is_safe_to_continue({}, "test")
            
            assert is_safe is False
            assert "Test resource limit exceeded" in reason
    
    def test_command_injection_scenarios(self):
        """Test various command injection attempts."""
        config = create_test_safety_config()
        guard = SafetyGuard(config)
        
        injection_attempts = [
            "python -c \"__import__('os').system('rm -rf /')\"",
            "echo 'test'; rm -rf /",
            "python script.py && sudo rm /etc/passwd",
            "eval(input())",
            "exec(open('malicious.py').read())",
            "subprocess.call(['rm', '-rf', '/'])"
        ]
        
        for attempt in injection_attempts:
            action = create_mock_action(attempt)
            
            is_valid, reason = guard.validate_action(action)
            
            assert is_valid is False, f"Injection attempt should be blocked: {attempt}"
            assert reason is not None


class TestSafetyConfigValidation:
    """Test safety configuration validation."""
    
    def test_valid_safety_config(self):
        """Test validation of valid safety configuration."""
        config = SafetyConfig(
            allowed_tools=["python", "git"],
            max_execution_time=300,
            max_memory_mb=1024,
            max_disk_mb=1024,
            file_system_access="restricted"
        )
        
        assert config.validate() is True
    
    def test_invalid_safety_config_values(self):
        """Test validation of invalid safety configuration values."""
        # Test negative execution time
        with pytest.raises(ValueError, match="max_execution_time must be positive"):
            config = SafetyConfig(max_execution_time=-1)
            config.validate()
        
        # Test negative memory limit
        with pytest.raises(ValueError, match="max_memory_mb must be positive"):
            config = SafetyConfig(max_memory_mb=-1)
            config.validate()
        
        # Test invalid file system access
        with pytest.raises(ValueError, match="Invalid file_system_access value"):
            config = SafetyConfig(file_system_access="invalid")
            config.validate()
    
    def test_default_safety_config_values(self):
        """Test that default safety configuration values are set correctly."""
        config = SafetyConfig()
        
        assert len(config.allowed_tools) > 0
        assert len(config.resource_limits) > 0
        assert len(config.dangerous_patterns) > 0
        assert config.enable_sandboxing is True
        assert config.max_execution_time > 0
        assert config.max_memory_mb > 0


class TestIntegrationScenarios:
    """Integration tests for the complete safety system."""
    
    def test_complete_safety_workflow(self):
        """Test complete safety workflow from action validation to incident logging."""
        config = create_test_safety_config()
        guard = SafetyGuard(config)
        
        # Test safe action
        safe_action = create_mock_action("echo 'hello'")
        
        is_valid, reason = guard.validate_action(safe_action)
        assert is_valid is True
        assert guard.violation_count == 0
        
        # Test dangerous action
        dangerous_action = create_mock_action("rm -rf /")
        
        is_valid, reason = guard.validate_action(dangerous_action)
        assert is_valid is False
        assert guard.violation_count == 1
        
        # Check that incident was logged
        incidents = guard.incident_logger.get_incidents()
        assert len(incidents) == 1
        assert incidents[0].incident_type == "dangerous_command_blocked"
        
        # Test safety metrics
        metrics = guard.get_safety_metrics()
        assert metrics["total_incidents"] == 1
        assert metrics["violation_count"] == 1
    
    def test_safety_system_recovery(self):
        """Test safety system behavior after reset."""
        config = create_test_safety_config()
        guard = SafetyGuard(config)
        
        # Cause some violations
        action = create_mock_action("rm -rf /")
        
        guard.validate_action(action)
        assert guard.violation_count == 1
        
        # Reset and verify clean state
        guard.reset()
        assert guard.violation_count == 0
        assert guard.safety_enabled is True
        assert guard.incident_logger.get_incident_count() == 0
        
        # Verify normal operation after reset
        safe_action = create_mock_action("echo 'test'")
        
        is_valid, reason = guard.validate_action(safe_action)
        assert is_valid is True


# Utility functions for testing
class MockAction:
    """Simple mock action class for testing."""
    def __init__(self, command: str, tool: str = None):
        self.command = command
        self.tool = tool
    
    def __str__(self):
        return self.command

def create_mock_action(command: str, tool: str = None):
    """Create a mock action with the given command."""
    return MockAction(command, tool)


def create_mock_env_state():
    """Create a mock environment state for testing."""
    return {
        "current_directory": "/tmp",
        "files_modified": [],
        "processes_running": [],
        "network_connections": []
    }


if __name__ == "__main__":
    pytest.main([__file__])