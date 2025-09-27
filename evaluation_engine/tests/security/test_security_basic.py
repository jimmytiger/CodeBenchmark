"""
Basic test for Security Framework components
"""

import asyncio
import tempfile
import shutil
from datetime import datetime

# Test basic imports
try:
    from evaluation_engine.security.vulnerability_scanner import VulnerabilityScanner
    from evaluation_engine.security.encryption_manager import EncryptionManager
    from evaluation_engine.security.audit_logger import AuditLogger, EventSeverity, EventCategory
    from evaluation_engine.security.incident_detector import SecurityIncidentDetector
    from evaluation_engine.security.compliance_manager import ComplianceManager, ComplianceFramework
    from evaluation_engine.security.access_control import AccessControlManager, Permission
    print("✅ All security modules imported successfully")
except ImportError as e:
    print(f"❌ Import error: {e}")
    exit(1)

def test_vulnerability_scanner():
    """Test vulnerability scanner basic functionality"""
    try:
        scanner = VulnerabilityScanner()
        assert scanner.scan_interval == 3600
        assert not scanner.is_scanning
        print("✅ Vulnerability scanner initialized")
        return True
    except Exception as e:
        print(f"❌ Vulnerability scanner test failed: {e}")
        return False

def test_encryption_manager():
    """Test encryption manager basic functionality"""
    try:
        # Create temporary directory
        temp_dir = tempfile.mkdtemp()
        
        try:
            config = {'key_store_path': f"{temp_dir}/keys"}
            encryption_manager = EncryptionManager(config)
            
            # Test data encryption/decryption
            test_data = "This is sensitive test data"
            encrypted_data = encryption_manager.encrypt_data(test_data)
            decrypted_data = encryption_manager.decrypt_data(encrypted_data)
            
            assert decrypted_data.decode() == test_data
            print("✅ Encryption manager working")
            return True
            
        finally:
            shutil.rmtree(temp_dir)
            
    except Exception as e:
        print(f"❌ Encryption manager test failed: {e}")
        return False

def test_audit_logger():
    """Test audit logger basic functionality"""
    try:
        # Create temporary directory
        temp_dir = tempfile.mkdtemp()
        
        try:
            config = {'log_dir': f"{temp_dir}/logs"}
            audit_logger = AuditLogger(config)
            
            # Log a test event
            audit_logger.log_security_event(
                severity=EventSeverity.INFO,
                category=EventCategory.SYSTEM_ACCESS,
                event_type="test",
                description="Test event",
                source="test"
            )
            
            # Wait for processing
            import time
            time.sleep(0.2)
            
            # Stop processing
            audit_logger.stop_processing()
            
            print("✅ Audit logger working")
            return True
            
        finally:
            shutil.rmtree(temp_dir)
            
    except Exception as e:
        print(f"❌ Audit logger test failed: {e}")
        return False

def test_incident_detector():
    """Test incident detector basic functionality"""
    try:
        incident_detector = SecurityIncidentDetector()
        assert len(incident_detector.detection_rules) > 0
        assert not incident_detector.is_running
        print("✅ Incident detector initialized")
        return True
    except Exception as e:
        print(f"❌ Incident detector test failed: {e}")
        return False

def test_compliance_manager():
    """Test compliance manager basic functionality"""
    try:
        compliance_manager = ComplianceManager()
        assert ComplianceFramework.GDPR in compliance_manager.enabled_frameworks
        
        # Test GDPR data subject registration
        subject = compliance_manager.gdpr.register_data_subject("test_subject", "test@example.com")
        assert subject.subject_id == "test_subject"
        
        print("✅ Compliance manager working")
        return True
    except Exception as e:
        print(f"❌ Compliance manager test failed: {e}")
        return False

def test_access_control():
    """Test access control basic functionality"""
    try:
        access_manager = AccessControlManager()
        assert len(access_manager.roles) > 0
        assert "admin" in access_manager.roles
        
        # Test user creation
        user_id = access_manager.create_user(
            username="testuser",
            email="test@example.com",
            password="password123",
            roles=["viewer"]
        )
        
        assert user_id in access_manager.users
        assert access_manager.has_permission(user_id, Permission.VIEW_EVALUATION)
        
        print("✅ Access control working")
        return True
    except Exception as e:
        print(f"❌ Access control test failed: {e}")
        return False

async def test_integration():
    """Test basic integration between components"""
    try:
        # Create temporary directory
        temp_dir = tempfile.mkdtemp()
        
        try:
            config = {
                'log_dir': f"{temp_dir}/logs",
                'key_store_path': f"{temp_dir}/keys"
            }
            
            # Initialize components
            audit_logger = AuditLogger(config)
            encryption_manager = EncryptionManager(config)
            access_manager = AccessControlManager()
            
            # Create user
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
            
            # Test encryption
            sensitive_data = "Sensitive integration test data"
            encrypted_data = encryption_manager.encrypt_data(sensitive_data)
            decrypted_data = encryption_manager.decrypt_data(encrypted_data)
            
            assert decrypted_data.decode() == sensitive_data
            
            # Wait for processing
            await asyncio.sleep(0.2)
            
            # Stop audit logger
            audit_logger.stop_processing()
            
            print("✅ Integration test passed")
            return True
            
        finally:
            shutil.rmtree(temp_dir)
            
    except Exception as e:
        print(f"❌ Integration test failed: {e}")
        return False

def main():
    """Run all tests"""
    print("Running Security Framework Basic Tests...")
    print("=" * 50)
    
    tests = [
        test_vulnerability_scanner,
        test_encryption_manager,
        test_audit_logger,
        test_incident_detector,
        test_compliance_manager,
        test_access_control
    ]
    
    passed = 0
    total = len(tests)
    
    for test in tests:
        if test():
            passed += 1
    
    # Run integration test
    if asyncio.run(test_integration()):
        passed += 1
    total += 1
    
    print("=" * 50)
    print(f"Tests passed: {passed}/{total}")
    
    if passed == total:
        print("🎉 All Security Framework tests passed!")
        return True
    else:
        print("❌ Some tests failed")
        return False

if __name__ == "__main__":
    success = main()
    exit(0 if success else 1)