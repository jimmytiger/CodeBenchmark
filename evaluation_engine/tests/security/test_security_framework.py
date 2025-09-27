"""
Comprehensive tests for the Security and Compliance Framework

Tests all components of the security system including:
- Vulnerability scanning
- Encryption management
- Audit logging
- Incident detection
- Compliance management
- Access control
"""

import asyncio
import json
import pytest
import tempfile
import shutil
from datetime import datetime, timedelta
from pathlib import Path
from unittest.mock import Mock, patch

# Import security components
from evaluation_engine.security.vulnerability_scanner import VulnerabilityScanner, Vulnerability, ScanResult
from evaluation_engine.security.encryption_manager import EncryptionManager, EncryptedData
from evaluation_engine.security.audit_logger import AuditLogger, SecurityEvent, EventSeverity, EventCategory
from evaluation_engine.security.incident_detector import SecurityIncidentDetector, SecurityIncident, IncidentSeverity
from evaluation_engine.security.compliance_manager import ComplianceManager, ComplianceFramework, DataSubject
from evaluation_engine.security.access_control import AccessControlManager, Permission, Role, User

class TestVulnerabilityScanner:
    """Test vulnerability scanning functionality"""
    
    @pytest.fixture
    def scanner(self):
        """Create vulnerability scanner instance"""
        return VulnerabilityScanner({'scan_interval': 10})
    
    def test_scanner_initialization(self, scanner):
        """Test scanner initialization"""
        assert scanner.scan_interval == 10
        assert not scanner.is_scanning
        assert len(scanner.scan_history) == 0
    
    @pytest.mark.asyncio
    async def test_vulnerability_database_update(self, scanner):
        """Test vulnerability database update"""
        result = await scanner.vuln_db.update_database()
        assert isinstance(result, bool)
    
    def test_severity_mapping(self, scanner):
        """Test severity level mapping"""
        assert scanner._map_severity('CRITICAL') == 'CRITICAL'
        assert scanner._map_severity('moderate') == 'MEDIUM'
        assert scanner._map_severity('unknown') == 'MEDIUM'
    
    def test_vulnerability_creation(self):
        """Test vulnerability object creation"""
        vuln = Vulnerability(
            id="test-vuln-1",
            severity="HIGH",
            package="test-package",
            version="1.0.0",
            description="Test vulnerability"
        )
        
        assert vuln.id == "test-vuln-1"
        assert vuln.severity == "HIGH"
        assert vuln.discovered_date is not None
    
    def test_scan_result_properties(self):
        """Test scan result properties"""
        vulnerabilities = [
            Vulnerability("1", "CRITICAL", "pkg1", "1.0", "Critical vuln"),
            Vulnerability("2", "HIGH", "pkg2", "2.0", "High vuln"),
            Vulnerability("3", "MEDIUM", "pkg3", "3.0", "Medium vuln"),
            Vulnerability("4", "LOW", "pkg4", "4.0", "Low vuln")
        ]
        
        scan_result = ScanResult(
            scan_id="test-scan",
            timestamp=datetime.utcnow(),
            vulnerabilities=vulnerabilities,
            total_packages=10,
            vulnerable_packages=4,
            scan_duration=30.5,
            scan_type="test"
        )
        
        assert scan_result.critical_count == 1
        assert scan_result.high_count == 1
        assert scan_result.medium_count == 1
        assert scan_result.low_count == 1

class TestEncryptionManager:
    """Test encryption management functionality"""
    
    @pytest.fixture
    def temp_dir(self):
        """Create temporary directory for testing"""
        temp_dir = tempfile.mkdtemp()
        yield temp_dir
        shutil.rmtree(temp_dir)
    
    @pytest.fixture
    def encryption_manager(self, temp_dir):
        """Create encryption manager instance"""
        config = {'key_store_path': f"{temp_dir}/keys"}
        return EncryptionManager(config)
    
    def test_encryption_manager_initialization(self, encryption_manager):
        """Test encryption manager initialization"""
        assert encryption_manager.default_algorithm == 'AES-256-GCM'
        
        # Should have default keys
        active_keys = encryption_manager.key_manager.list_keys(active_only=True)
        assert len(active_keys) > 0
    
    def test_symmetric_key_generation(self, encryption_manager):
        """Test symmetric key generation"""
        key_id = encryption_manager.key_manager.generate_symmetric_key("AES-256-GCM")
        assert key_id is not None
        
        key_info = encryption_manager.key_manager.get_key(key_id)
        assert key_info is not None
        
        key, key_data = key_info
        assert key.key_type == "symmetric"
        assert key.algorithm == "AES-256-GCM"
        assert len(key_data) == 32  # 256 bits
    
    def test_asymmetric_key_generation(self, encryption_manager):
        """Test asymmetric key generation"""
        private_key_id, public_key_id = encryption_manager.key_manager.generate_asymmetric_keypair("RSA-2048")
        
        assert private_key_id is not None
        assert public_key_id is not None
        
        private_key_info = encryption_manager.key_manager.get_key(private_key_id)
        public_key_info = encryption_manager.key_manager.get_key(public_key_id)
        
        assert private_key_info is not None
        assert public_key_info is not None
    
    def test_data_encryption_decryption(self, encryption_manager):
        """Test data encryption and decryption"""
        test_data = "This is sensitive test data"
        
        # Encrypt data
        encrypted_data = encryption_manager.encrypt_data(test_data)
        assert isinstance(encrypted_data, EncryptedData)
        assert encrypted_data.data != test_data.encode()
        
        # Decrypt data
        decrypted_data = encryption_manager.decrypt_data(encrypted_data)
        assert decrypted_data.decode() == test_data
    
    def test_fernet_encryption(self, encryption_manager):
        """Test Fernet encryption"""
        key_id = encryption_manager.key_manager.generate_symmetric_key("Fernet")
        test_data = "Fernet test data"
        
        encrypted_data = encryption_manager.encrypt_data(test_data, key_id, "Fernet")
        decrypted_data = encryption_manager.decrypt_data(encrypted_data)
        
        assert decrypted_data.decode() == test_data
    
    @pytest.mark.asyncio
    async def test_file_encryption(self, encryption_manager, temp_dir):
        """Test file encryption and decryption"""
        # Create test file
        test_file = Path(temp_dir) / "test.txt"
        test_content = "This is test file content"
        
        with open(test_file, 'w') as f:
            f.write(test_content)
        
        # Encrypt file
        encrypted_file = await encryption_manager.encrypt_file(str(test_file))
        assert Path(encrypted_file).exists()
        
        # Decrypt file
        decrypted_file = await encryption_manager.decrypt_file(encrypted_file)
        
        with open(decrypted_file, 'r') as f:
            decrypted_content = f.read()
        
        assert decrypted_content == test_content
    
    def test_key_rotation(self, encryption_manager):
        """Test key rotation"""
        # Generate initial key
        old_key_id = encryption_manager.key_manager.generate_symmetric_key("AES-256-GCM")
        
        # Rotate key
        new_key_id = encryption_manager.key_manager.rotate_key(old_key_id)
        
        assert new_key_id != old_key_id
        
        # Old key should be inactive
        old_key_info = encryption_manager.key_manager.get_key(old_key_id)
        assert old_key_info is None  # Should return None for inactive key
        
        # New key should be active
        new_key_info = encryption_manager.key_manager.get_key(new_key_id)
        assert new_key_info is not None

class TestAuditLogger:
    """Test audit logging functionality"""
    
    @pytest.fixture
    def temp_dir(self):
        """Create temporary directory for testing"""
        temp_dir = tempfile.mkdtemp()
        yield temp_dir
        shutil.rmtree(temp_dir)
    
    @pytest.fixture
    def audit_logger(self, temp_dir):
        """Create audit logger instance"""
        config = {'log_dir': f"{temp_dir}/logs"}
        return AuditLogger(config)
    
    def test_audit_logger_initialization(self, audit_logger):
        """Test audit logger initialization"""
        assert audit_logger.is_running
        assert audit_logger.log_dir.exists()
    
    def test_security_event_logging(self, audit_logger):
        """Test security event logging"""
        audit_logger.log_security_event(
            severity=EventSeverity.HIGH,
            category=EventCategory.AUTHENTICATION,
            event_type="login_attempt",
            description="Failed login attempt",
            source="auth_system",
            user_id="test_user",
            ip_address="192.168.1.100"
        )
        
        # Wait for processing
        import time
        time.sleep(0.2)
        
        assert len(audit_logger.security_events) > 0
        event = audit_logger.security_events[-1]
        assert event.severity == EventSeverity.HIGH
        assert event.category == EventCategory.AUTHENTICATION
    
    def test_authentication_event_logging(self, audit_logger):
        """Test authentication event logging"""
        audit_logger.log_authentication_event(
            user_id="test_user",
            action="login",
            result="success",
            ip_address="192.168.1.100"
        )
        
        import time
        time.sleep(0.2)
        
        assert len(audit_logger.security_events) > 0
        event = audit_logger.security_events[-1]
        assert event.user_id == "test_user"
        assert event.action == "login"
    
    def test_event_search(self, audit_logger):
        """Test event search functionality"""
        # Log multiple events
        for i in range(5):
            audit_logger.log_security_event(
                severity=EventSeverity.INFO,
                category=EventCategory.DATA_ACCESS,
                event_type="data_read",
                description=f"Data access {i}",
                source="data_system",
                user_id=f"user_{i}"
            )
        
        import time
        time.sleep(0.2)
        
        # Search events
        events = audit_logger.search_events(
            category=EventCategory.DATA_ACCESS,
            limit=3
        )
        
        assert len(events) <= 3
        for event in events:
            assert event.category == EventCategory.DATA_ACCESS
    
    def test_event_statistics(self, audit_logger):
        """Test event statistics"""
        # Log events with different severities
        severities = [EventSeverity.CRITICAL, EventSeverity.HIGH, EventSeverity.MEDIUM, EventSeverity.LOW]
        
        for severity in severities:
            audit_logger.log_security_event(
                severity=severity,
                category=EventCategory.SECURITY_VIOLATION,
                event_type="test_event",
                description="Test event",
                source="test_system"
            )
        
        import time
        time.sleep(0.2)
        
        stats = audit_logger.get_event_statistics(hours=1)
        assert stats['total_events'] >= 4
        assert 'by_severity' in stats
        assert 'by_category' in stats

class TestSecurityIncidentDetector:
    """Test security incident detection functionality"""
    
    @pytest.fixture
    def incident_detector(self):
        """Create incident detector instance"""
        return SecurityIncidentDetector()
    
    def test_incident_detector_initialization(self, incident_detector):
        """Test incident detector initialization"""
        assert len(incident_detector.detection_rules) > 0
        assert not incident_detector.is_running
    
    def test_threat_intelligence_loading(self, incident_detector):
        """Test threat intelligence loading"""
        incident_detector.threat_intel.load_threat_feeds()
        
        assert len(incident_detector.threat_intel.malicious_ips) > 0
        assert len(incident_detector.threat_intel.suspicious_patterns) > 0
    
    def test_malicious_ip_detection(self, incident_detector):
        """Test malicious IP detection"""
        # Add test IP to malicious list
        incident_detector.threat_intel.malicious_ips.add("192.168.1.100")
        
        assert incident_detector.threat_intel.is_malicious_ip("192.168.1.100")
        assert not incident_detector.threat_intel.is_malicious_ip("192.168.1.200")
    
    def test_suspicious_pattern_detection(self, incident_detector):
        """Test suspicious pattern detection"""
        test_strings = [
            "SELECT * FROM users WHERE id = 1",  # SQL injection
            "../../../etc/passwd",               # Path traversal
            "<script>alert('xss')</script>",     # XSS
            "cmd.exe /c dir"                     # Command injection
        ]
        
        for test_string in test_strings:
            assert incident_detector.threat_intel.contains_suspicious_pattern(test_string)
    
    def test_security_event_processing(self, incident_detector):
        """Test security event processing"""
        event = SecurityEvent(
            event_id="test-event-1",
            timestamp=datetime.utcnow(),
            severity=EventSeverity.HIGH,
            category=EventCategory.AUTHENTICATION,
            event_type="authentication",
            description="Failed login attempt",
            source="auth_system",
            user_id="test_user",
            ip_address="192.168.1.100",
            result="failed"
        )
        
        incident_detector.process_security_event(event)
        
        assert len(incident_detector.event_buffer) == 1
        assert incident_detector.event_buffer[0] == event
    
    def test_incident_creation(self, incident_detector):
        """Test incident creation"""
        incident = SecurityIncident(
            incident_id="",
            title="Test Incident",
            description="Test incident description",
            severity=IncidentSeverity.HIGH,
            status=incident_detector.IncidentStatus.OPEN,
            category=EventCategory.SECURITY_VIOLATION,
            created_at=datetime.utcnow(),
            updated_at=datetime.utcnow(),
            detected_by="test_system",
            affected_resources=["resource1"],
            related_events=["event1"],
            indicators={"test": True},
            response_actions=[]
        )
        
        # Test incident ID generation
        assert incident.incident_id.startswith("INC-")
        assert len(incident.incident_id) == 12  # INC- + 8 chars

class TestComplianceManager:
    """Test compliance management functionality"""
    
    @pytest.fixture
    def compliance_manager(self):
        """Create compliance manager instance"""
        return ComplianceManager()
    
    def test_compliance_manager_initialization(self, compliance_manager):
        """Test compliance manager initialization"""
        assert ComplianceFramework.GDPR in compliance_manager.enabled_frameworks
        assert ComplianceFramework.SOC2 in compliance_manager.enabled_frameworks
    
    def test_gdpr_data_subject_registration(self, compliance_manager):
        """Test GDPR data subject registration"""
        subject = compliance_manager.gdpr.register_data_subject(
            subject_id="test_subject_1",
            email="test@example.com"
        )
        
        assert subject.subject_id == "test_subject_1"
        assert subject.email == "test@example.com"
        assert "test_subject_1" in compliance_manager.gdpr.data_subjects
    
    def test_gdpr_consent_management(self, compliance_manager):
        """Test GDPR consent management"""
        from evaluation_engine.security.compliance_manager import ProcessingPurpose, ConsentStatus
        
        # Register data subject
        compliance_manager.gdpr.register_data_subject("test_subject_2")
        
        # Record consent
        result = compliance_manager.gdpr.record_consent(
            subject_id="test_subject_2",
            purposes=[ProcessingPurpose.EVALUATION, ProcessingPurpose.ANALYTICS]
        )
        
        assert result is True
        
        subject = compliance_manager.gdpr.data_subjects["test_subject_2"]
        assert subject.consent_status == ConsentStatus.GIVEN
        assert ProcessingPurpose.EVALUATION in subject.consent_purposes
    
    def test_gdpr_data_subject_rights(self, compliance_manager):
        """Test GDPR data subject rights"""
        # Register data subject
        compliance_manager.gdpr.register_data_subject("test_subject_3", "test3@example.com")
        
        # Test access request
        access_result = compliance_manager.gdpr.handle_data_subject_request(
            subject_id="test_subject_3",
            request_type="access"
        )
        
        assert access_result['status'] == 'success'
        assert 'data' in access_result
        assert 'subject_info' in access_result['data']
    
    def test_gdpr_erasure_request(self, compliance_manager):
        """Test GDPR erasure request (right to be forgotten)"""
        # Register data subject
        compliance_manager.gdpr.register_data_subject("test_subject_4")
        
        # Verify subject exists
        assert "test_subject_4" in compliance_manager.gdpr.data_subjects
        
        # Process erasure request
        erasure_result = compliance_manager.gdpr.handle_data_subject_request(
            subject_id="test_subject_4",
            request_type="erasure"
        )
        
        assert erasure_result['status'] == 'success'
        assert "test_subject_4" not in compliance_manager.gdpr.data_subjects
    
    def test_soc2_control_assessment(self, compliance_manager):
        """Test SOC2 control assessment"""
        result = compliance_manager.soc2.assess_control(
            control_id="CC6.1",
            assessment_result="EFFECTIVE",
            evidence=["security_policy.pdf", "access_logs.json"],
            assessor="security_team"
        )
        
        assert result is True
        assert "CC6.1" in compliance_manager.soc2.control_assessments
        
        assessment = compliance_manager.soc2.control_assessments["CC6.1"]
        assert assessment['assessment_result'] == "EFFECTIVE"
    
    def test_soc2_evidence_collection(self, compliance_manager):
        """Test SOC2 evidence collection"""
        evidence_id = compliance_manager.soc2.collect_evidence(
            control_id="CC6.2",
            evidence_type="log_analysis",
            evidence_data={"log_entries": 1000, "anomalies": 0}
        )
        
        assert evidence_id is not None
        assert "CC6.2" in compliance_manager.soc2.evidence_collection
        assert len(compliance_manager.soc2.evidence_collection["CC6.2"]) == 1
    
    def test_compliance_violation_handling(self, compliance_manager):
        """Test compliance violation handling"""
        from evaluation_engine.security.compliance_manager import ComplianceViolation
        
        breach_id = compliance_manager.handle_data_breach(
            breach_description="Unauthorized access to user data",
            affected_data_subjects=["user1", "user2"],
            breach_type="unauthorized_access"
        )
        
        assert breach_id.startswith("BREACH-")
        assert len(compliance_manager.violations) > 0
    
    def test_compliance_report_generation(self, compliance_manager):
        """Test compliance report generation"""
        report = compliance_manager.generate_compliance_report(
            framework=ComplianceFramework.GDPR
        )
        
        assert report['framework'] == 'GDPR'
        assert 'report_period' in report
        assert 'violations' in report
        assert 'compliance_status' in report

class TestAccessControlManager:
    """Test access control functionality"""
    
    @pytest.fixture
    def access_manager(self):
        """Create access control manager instance"""
        return AccessControlManager()
    
    def test_access_manager_initialization(self, access_manager):
        """Test access control manager initialization"""
        assert len(access_manager.roles) > 0
        assert "admin" in access_manager.roles
        assert "evaluator" in access_manager.roles
        assert "viewer" in access_manager.roles
    
    def test_user_creation(self, access_manager):
        """Test user creation"""
        user_id = access_manager.create_user(
            username="testuser",
            email="test@example.com",
            password="secure_password123",
            roles=["evaluator"]
        )
        
        assert user_id is not None
        assert user_id in access_manager.users
        
        user = access_manager.users[user_id]
        assert user.username == "testuser"
        assert "evaluator" in user.roles
    
    def test_user_authentication(self, access_manager):
        """Test user authentication"""
        # Create user
        user_id = access_manager.create_user(
            username="authuser",
            email="auth@example.com",
            password="password123",
            roles=["viewer"]
        )
        
        # Authenticate user
        session_id = access_manager.authenticate_user(
            username="authuser",
            password="password123",
            ip_address="192.168.1.100"
        )
        
        assert session_id is not None
        assert session_id in access_manager.sessions
        
        # Get user from session
        user = access_manager.get_user_from_session(session_id)
        assert user is not None
        assert user.username == "authuser"
    
    def test_failed_authentication(self, access_manager):
        """Test failed authentication"""
        # Create user
        access_manager.create_user(
            username="failuser",
            email="fail@example.com",
            password="correct_password",
            roles=["viewer"]
        )
        
        # Try wrong password
        session_id = access_manager.authenticate_user(
            username="failuser",
            password="wrong_password"
        )
        
        assert session_id is None
    
    def test_permission_checking(self, access_manager):
        """Test permission checking"""
        # Create user with evaluator role
        user_id = access_manager.create_user(
            username="permuser",
            email="perm@example.com",
            password="password123",
            roles=["evaluator"]
        )
        
        # Check permissions
        assert access_manager.has_permission(user_id, Permission.CREATE_EVALUATION)
        assert access_manager.has_permission(user_id, Permission.VIEW_EVALUATION)
        assert not access_manager.has_permission(user_id, Permission.SYSTEM_ADMIN)
    
    def test_role_management(self, access_manager):
        """Test role management"""
        # Create custom role
        role_id = access_manager.create_role(
            name="Custom Role",
            description="Custom role for testing",
            permissions=[Permission.VIEW_DATA, Permission.EXPORT_DATA]
        )
        
        assert role_id in access_manager.roles
        
        role = access_manager.roles[role_id]
        assert role.name == "Custom Role"
        assert Permission.VIEW_DATA in role.permissions
    
    def test_role_assignment(self, access_manager):
        """Test role assignment and revocation"""
        # Create user and role
        user_id = access_manager.create_user(
            username="roleuser",
            email="role@example.com",
            password="password123",
            roles=["viewer"]
        )
        
        role_id = access_manager.create_role(
            name="Test Role",
            description="Test role",
            permissions=[Permission.CREATE_TASK]
        )
        
        # Assign role
        result = access_manager.assign_role(user_id, role_id)
        assert result is True
        
        user = access_manager.users[user_id]
        assert role_id in user.roles
        
        # Check permission
        assert access_manager.has_permission(user_id, Permission.CREATE_TASK)
        
        # Revoke role
        result = access_manager.revoke_role(user_id, role_id)
        assert result is True
        assert role_id not in user.roles
    
    def test_api_key_authentication(self, access_manager):
        """Test API key authentication"""
        # Create user
        user_id = access_manager.create_user(
            username="apiuser",
            email="api@example.com",
            password="password123",
            roles=["evaluator"]
        )
        
        user = access_manager.users[user_id]
        api_key = user.api_key
        
        # Authenticate with API key
        session_id = access_manager.authenticate_api_key(api_key)
        assert session_id is not None
        
        # Verify session
        session_user = access_manager.get_user_from_session(session_id)
        assert session_user.user_id == user_id
    
    def test_session_management(self, access_manager):
        """Test session management"""
        # Create and authenticate user
        user_id = access_manager.create_user(
            username="sessionuser",
            email="session@example.com",
            password="password123",
            roles=["viewer"]
        )
        
        session_id = access_manager.authenticate_user(
            username="sessionuser",
            password="password123"
        )
        
        assert session_id in access_manager.sessions
        
        # Logout user
        result = access_manager.logout_user(session_id)
        assert result is True
        assert session_id not in access_manager.sessions
    
    def test_access_audit(self, access_manager):
        """Test access audit functionality"""
        # Create user
        user_id = access_manager.create_user(
            username="audituser",
            email="audit@example.com",
            password="password123",
            roles=["evaluator"]
        )
        
        # Generate some access requests
        access_manager.has_permission(user_id, Permission.CREATE_EVALUATION)
        access_manager.has_permission(user_id, Permission.SYSTEM_ADMIN)
        
        # Get audit trail
        audit_trail = access_manager.get_access_audit(user_id=user_id)
        assert len(audit_trail) >= 2
        
        # Check that one was granted and one was denied
        granted = [r for r in audit_trail if r.context.get('granted', False)]
        denied = [r for r in audit_trail if not r.context.get('granted', False)]
        
        assert len(granted) >= 1
        assert len(denied) >= 1

@pytest.mark.asyncio
async def test_security_framework_integration():
    """Test integration between security components"""
    # Create temporary directory
    temp_dir = tempfile.mkdtemp()
    
    try:
        # Initialize all components
        config = {
            'log_dir': f"{temp_dir}/logs",
            'key_store_path': f"{temp_dir}/keys"
        }
        
        audit_logger = AuditLogger(config)
        encryption_manager = EncryptionManager(config)
        incident_detector = SecurityIncidentDetector()
        compliance_manager = ComplianceManager()
        access_manager = AccessControlManager()
        
        # Test integration scenario: User authentication with audit logging
        user_id = access_manager.create_user(
            username="integrationuser",
            email="integration@example.com",
            password="password123",
            roles=["evaluator"]
        )
        
        # Log authentication event
        audit_logger.log_authentication_event(
            user_id=user_id,
            action="login",
            result="success",
            ip_address="192.168.1.100"
        )
        
        # Wait for processing
        await asyncio.sleep(0.2)
        
        # Verify event was logged
        assert len(audit_logger.security_events) > 0
        
        # Test data encryption for compliance
        sensitive_data = "Personal information for compliance testing"
        encrypted_data = encryption_manager.encrypt_data(sensitive_data)
        
        # Verify encryption worked
        assert encrypted_data.data != sensitive_data.encode()
        
        # Test decryption
        decrypted_data = encryption_manager.decrypt_data(encrypted_data)
        assert decrypted_data.decode() == sensitive_data
        
        # Test GDPR compliance
        compliance_manager.gdpr.register_data_subject(
            subject_id=user_id,
            email="integration@example.com"
        )
        
        # Verify data subject was registered
        assert user_id in compliance_manager.gdpr.data_subjects
        
        # Test incident detection with security event
        security_event = SecurityEvent(
            event_id="integration-test-1",
            timestamp=datetime.utcnow(),
            severity=EventSeverity.HIGH,
            category=EventCategory.SECURITY_VIOLATION,
            event_type="test_violation",
            description="Integration test security violation",
            source="integration_test",
            user_id=user_id
        )
        
        incident_detector.process_security_event(security_event)
        
        # Verify event was processed
        assert len(incident_detector.event_buffer) > 0
        
        print("✅ Security framework integration test passed")
        
    finally:
        # Cleanup
        audit_logger.stop_processing()
        shutil.rmtree(temp_dir)

if __name__ == "__main__":
    # Run basic tests
    print("Running Security Framework Tests...")
    
    # Test vulnerability scanner
    scanner = VulnerabilityScanner()
    print("✅ Vulnerability scanner initialized")
    
    # Test encryption manager
    encryption_manager = EncryptionManager()
    test_data = "Test encryption data"
    encrypted = encryption_manager.encrypt_data(test_data)
    decrypted = encryption_manager.decrypt_data(encrypted)
    assert decrypted.decode() == test_data
    print("✅ Encryption manager working")
    
    # Test audit logger
    audit_logger = AuditLogger()
    audit_logger.log_security_event(
        severity=EventSeverity.INFO,
        category=EventCategory.SYSTEM_ACCESS,
        event_type="test",
        description="Test event",
        source="test"
    )
    print("✅ Audit logger working")
    
    # Test incident detector
    incident_detector = SecurityIncidentDetector()
    print("✅ Incident detector initialized")
    
    # Test compliance manager
    compliance_manager = ComplianceManager()
    compliance_manager.gdpr.register_data_subject("test_subject")
    print("✅ Compliance manager working")
    
    # Test access control
    access_manager = AccessControlManager()
    user_id = access_manager.create_user("testuser", "test@example.com", "password", ["viewer"])
    assert access_manager.has_permission(user_id, Permission.VIEW_EVALUATION)
    print("✅ Access control working")
    
    # Run integration test
    asyncio.run(test_security_framework_integration())
    
    print("\n🎉 All Security Framework tests passed!")
    
    # Cleanup
    audit_logger.stop_processing()