"""
Unit tests for RealExecutionValidator component.

Tests validation of real execution vs mock data usage.
"""

import pytest
from unittest.mock import patch, MagicMock
import time
import statistics

import sys
import os
sys.path.append(os.path.join(os.path.dirname(__file__), '../../'))

from ...core.real_execution_validator import RealExecutionValidator, RealExecutionContext
from ...models.test_models import TestResult, ExecutionMetrics, TestType, TestStatus
from ...core.error_handler import ValidationError


class TestRealExecutionValidator:
    """Unit tests for RealExecutionValidator class."""
    
    def setup_method(self):
        """Set up test fixtures."""
        self.validator = RealExecutionValidator()
        self.real_result = TestResult(
            test_id='test_001',
            test_type=TestType.INTEGRATION,
            name='Real Integration Test',
            status=TestStatus.PASSED,
            execution_time=2.5,
            real_execution_validated=True,
            metrics={
                'api_calls': 5,
                'tokens_used': 150,
                'model_responses': 3,
                'network_requests': 8
            },
            error_details=None,
            artifacts=['response_1.json', 'response_2.json'],
            logs=['Starting test', 'Making API call', 'Processing response', 'Test completed']
        )
        
        self.mock_result = TestResult(
            test_id='test_002',
            test_type=TestType.UNIT,
            name='Mock Unit Test',
            status=TestStatus.PASSED,
            execution_time=0.01,
            real_execution_validated=False,
            metrics={
                'api_calls': 0,
                'tokens_used': 0,
                'model_responses': 0,
                'network_requests': 0
            },
            error_details=None,
            artifacts=[],
            logs=[]
        )
    
    def test_validate_no_mocks_real_execution(self):
        """Test validation passes for real execution."""
        execution_context = {
            'api_calls_made': True,
            'network_activity': True,
            'file_operations': True,
            'mock_objects_detected': False
        }
        
        is_real = self.validator.validate_no_mocks(execution_context)
        assert is_real is True
    
    def test_validate_no_mocks_mock_detected(self):
        """Test validation fails when mocks are detected."""
        execution_context = {
            'api_calls_made': False,
            'network_activity': False,
            'file_operations': True,
            'mock_objects_detected': True
        }
        
        is_real = self.validator.validate_no_mocks(execution_context)
        assert is_real is False
    
    def test_validate_actual_model_calls(self):
        """Test validation of actual model API calls."""
        api_logs = [
            {
                'timestamp': time.time(),
                'endpoint': 'https://api.openai.com/v1/completions',
                'method': 'POST',
                'status_code': 200,
                'response_time': 1.2,
                'tokens_used': 50
            },
            {
                'timestamp': time.time(),
                'endpoint': 'https://api.anthropic.com/v1/messages',
                'method': 'POST',
                'status_code': 200,
                'response_time': 0.8,
                'tokens_used': 75
            }
        ]
        
        is_valid = self.validator.validate_actual_model_calls(api_logs)
        assert is_valid is True
    
    def test_validate_actual_model_calls_no_calls(self):
        """Test validation fails when no model calls are made."""
        api_logs = []
        
        is_valid = self.validator.validate_actual_model_calls(api_logs)
        assert is_valid is False
    
    def test_validate_genuine_results(self):
        """Test validation of genuine evaluation results."""
        # Real results should have variability and realistic patterns
        results = {
            'scores': [0.85, 0.92, 0.78, 0.89, 0.91],
            'response_times': [1.2, 0.8, 1.5, 1.1, 0.9],
            'token_counts': [45, 52, 38, 49, 51],
            'metadata': {
                'model_version': 'gpt-3.5-turbo-0613',
                'timestamp': time.time(),
                'request_id': 'req_abc123'
            }
        }
        
        is_genuine = self.validator.validate_genuine_results(results)
        assert is_genuine is True
    
    def test_validate_genuine_results_suspicious_patterns(self):
        """Test validation fails for suspicious result patterns."""
        # Fake results often have perfect scores or identical values
        results = {
            'scores': [1.0, 1.0, 1.0, 1.0, 1.0],  # Too perfect
            'response_times': [0.1, 0.1, 0.1, 0.1, 0.1],  # Too consistent
            'token_counts': [50, 50, 50, 50, 50],  # Identical
            'metadata': {}  # Missing realistic metadata
        }
        
        is_genuine = self.validator.validate_genuine_results(results)
        assert is_genuine is False
    
    def test_validate_resource_consumption(self):
        """Test validation of realistic resource consumption."""
        metrics = ExecutionMetrics(
            total_execution_time=120.5,
            task_execution_times={'task_1': 45.2, 'task_2': 75.3},
            memory_usage={'peak_mb': 256, 'average_mb': 180},
            api_response_times={'/api/evaluate': [1.2, 0.8, 1.5]},
            error_rates={'overall': 0.05},
            success_rates={'overall': 0.95}
        )
        
        is_realistic = self.validator.validate_resource_consumption(metrics)
        assert is_realistic is True
    
    def test_validate_resource_consumption_unrealistic(self):
        """Test validation fails for unrealistic resource consumption."""
        metrics = ExecutionMetrics(
            total_execution_time=0.001,  # Too fast
            task_execution_times={'task_1': 0.0001, 'task_2': 0.0001},
            memory_usage={'peak_mb': 1, 'average_mb': 1},  # Too low
            api_response_times={'/api/evaluate': [0.001, 0.001, 0.001]},  # Too fast
            error_rates={'overall': 0.0},  # Too perfect
            success_rates={'overall': 1.0}  # Too perfect
        )
        
        is_realistic = self.validator.validate_resource_consumption(metrics)
        assert is_realistic is False
    
    def test_detect_mock_frameworks(self):
        """Test detection of mock frameworks in execution."""
        with patch('sys.modules') as mock_modules:
            # Simulate mock frameworks being imported
            mock_modules.keys.return_value = [
                'unittest.mock',
                'pytest',
                'responses',
                'httpretty',
                'my_module'
            ]
            
            mock_detected = self.validator.detect_mock_frameworks()
            assert mock_detected is True
    
    def test_detect_mock_frameworks_none_present(self):
        """Test when no mock frameworks are detected."""
        with patch('sys.modules') as mock_modules:
            mock_modules.keys.return_value = [
                'requests',
                'json',
                'os',
                'sys',
                'my_module'
            ]
            
            mock_detected = self.validator.detect_mock_frameworks()
            assert mock_detected is False
    
    def test_validate_network_activity(self):
        """Test validation of actual network activity."""
        network_logs = [
            {
                'timestamp': time.time(),
                'destination': 'api.openai.com',
                'port': 443,
                'bytes_sent': 1024,
                'bytes_received': 2048,
                'duration': 1.2
            },
            {
                'timestamp': time.time(),
                'destination': 'huggingface.co',
                'port': 443,
                'bytes_sent': 512,
                'bytes_received': 1536,
                'duration': 0.8
            }
        ]
        
        has_activity = self.validator.validate_network_activity(network_logs)
        assert has_activity is True
    
    def test_validate_network_activity_no_activity(self):
        """Test validation fails when no network activity detected."""
        network_logs = []
        
        has_activity = self.validator.validate_network_activity(network_logs)
        assert has_activity is False
    
    def test_validate_file_system_operations(self):
        """Test validation of file system operations."""
        fs_operations = [
            {
                'operation': 'write',
                'path': '/tmp/test_results.json',
                'size': 1024,
                'timestamp': time.time()
            },
            {
                'operation': 'read',
                'path': '/tmp/config.yaml',
                'size': 512,
                'timestamp': time.time()
            }
        ]
        
        has_operations = self.validator.validate_file_system_operations(fs_operations)
        assert has_operations is True
    
    def test_comprehensive_validation_real_execution(self):
        """Test comprehensive validation of real execution."""
        # Temporarily disable mock detection for this test since we're in a test environment
        self.validator.configure_validation(mock_detection=False)
        
        execution_data = {
            'test_result': self.real_result,
            'api_logs': [
                {
                    'endpoint': 'https://api.openai.com/v1/completions',
                    'status_code': 200,
                    'response_time': 1.2,
                    'tokens_used': 50
                }
            ],
            'network_logs': [
                {
                    'destination': 'api.openai.com',
                    'port': 443,
                    'bytes_sent': 1024,
                    'bytes_received': 2048,
                    'duration': 1.2
                }
            ],
            'resource_metrics': ExecutionMetrics(
                total_execution_time=2.5,
                task_execution_times={'test_001': 2.5},
                memory_usage={'peak_mb': 128},
                api_response_times={'/api/test': [1.2, 0.8, 1.5]},  # Add variance
                error_rates={'overall': 0.02},  # Add some realistic error rate
                success_rates={'overall': 0.98}  # Realistic success rate
            )
        }
        
        is_valid = self.validator.comprehensive_validation(execution_data)
        assert is_valid is True
    
    def test_comprehensive_validation_mock_execution(self):
        """Test comprehensive validation fails for mock execution."""
        # Re-enable mock detection for this test
        self.validator.configure_validation(mock_detection=True)
        
        execution_data = {
            'test_result': self.mock_result,
            'api_logs': [],
            'network_logs': [],
            'resource_metrics': ExecutionMetrics(
                total_execution_time=0.01,
                task_execution_times={'test_002': 0.01},
                memory_usage={'peak_mb': 1},
                api_response_times={},
                error_rates={'overall': 0.0},
                success_rates={'overall': 1.0}
            )
        }
        
        is_valid = self.validator.comprehensive_validation(execution_data)
        assert is_valid is False
    
    def test_generate_validation_report(self):
        """Test generation of validation report."""
        # Disable mock detection for test environment
        self.validator.configure_validation(mock_detection=False)
        
        execution_data = {
            'test_result': self.real_result,
            'api_logs': [
                {
                    'endpoint': 'https://api.openai.com/v1/completions',
                    'status_code': 200,
                    'response_time': 1.2,
                    'tokens_used': 50
                }
            ],
            'network_logs': [
                {
                    'destination': 'api.openai.com',
                    'port': 443,
                    'bytes_sent': 1024,
                    'bytes_received': 2048,
                    'duration': 1.2
                }
            ],
            'resource_metrics': ExecutionMetrics(
                total_execution_time=2.5,
                task_execution_times={'test_001': 2.5},
                memory_usage={'peak_mb': 128},
                api_response_times={'/api/test': [1.2, 0.8, 1.5]},  # Add variance
                error_rates={'overall': 0.02},  # Realistic error rate
                success_rates={'overall': 0.98}  # Realistic success rate
            )
        }
        
        report = self.validator.generate_validation_report(execution_data)
        
        assert 'validation_result' in report
        assert 'checks_performed' in report
        assert 'evidence' in report
        assert 'confidence_score' in report
        assert report['validation_result'] is True
    
    def test_validation_with_custom_thresholds(self):
        """Test validation with custom thresholds."""
        # Disable mock detection for test environment
        self.validator.configure_validation(mock_detection=False)
        
        custom_thresholds = {
            'min_execution_time': 1.0,
            'min_api_calls': 3,
            'min_memory_usage': 64,
            'max_success_rate': 0.98  # Allow some failures for realism
        }
        
        self.validator.set_validation_thresholds(custom_thresholds)
        
        # Test with execution that meets custom thresholds
        execution_data = {
            'test_result': self.real_result,
            'api_logs': [
                {
                    'endpoint': 'https://api.openai.com/v1/completions',
                    'status_code': 200,
                    'response_time': 1.2,
                    'tokens_used': 50
                } for _ in range(5)
            ],
            'resource_metrics': ExecutionMetrics(
                total_execution_time=2.5,
                task_execution_times={'test_001': 2.5},
                memory_usage={'peak_mb': 128},
                api_response_times={'/api/test': [1.2, 0.8, 1.5]},  # Add variance
                error_rates={'overall': 0.02},
                success_rates={'overall': 0.98}
            )
        }
        
        is_valid = self.validator.comprehensive_validation(execution_data)
        assert is_valid is True
    
    def test_mock_detection_mechanisms(self):
        """Test comprehensive mock detection mechanisms."""
        # Note: In test environment, mock objects will be present, so we test the detection logic
        
        # Test mock framework detection
        with patch('sys.modules') as mock_modules:
            mock_modules.keys.return_value = ['unittest.mock', 'requests', 'json']
            assert self.validator.detect_mock_frameworks() is True
        
        # Test with no mock frameworks
        with patch('sys.modules') as mock_modules:
            mock_modules.keys.return_value = ['requests', 'json', 'os']
            assert self.validator.detect_mock_frameworks() is False
        
        # Test that mock objects are detected (expected in test environment)
        mock_objects = self.validator._find_mock_objects()
        # In test environment, we expect to find some mock objects
        assert isinstance(mock_objects, list)
    
    def test_api_call_validation_comprehensive(self):
        """Test comprehensive API call validation."""
        # Test with realistic model API calls
        api_logs = [
            {
                'endpoint': 'https://api.openai.com/v1/completions',
                'method': 'POST',
                'status_code': 200,
                'response_time': 1.2,
                'tokens_used': 50
            },
            {
                'endpoint': 'https://api.anthropic.com/v1/messages',
                'method': 'POST',
                'status_code': 200,
                'response_time': 0.8,
                'tokens_used': 75
            }
        ]
        
        assert self.validator.validate_actual_model_calls(api_logs) is True
        
        # Test with suspicious API calls
        suspicious_logs = [
            {
                'endpoint': 'http://localhost:8000/mock',
                'method': 'POST',
                'status_code': 999,  # Invalid status code
                'response_time': -1,  # Invalid response time
                'tokens_used': -10   # Invalid token count
            }
        ]
        
        assert self.validator.validate_actual_model_calls(suspicious_logs) is False
    
    def test_resource_consumption_validation_enhanced(self):
        """Test enhanced resource consumption validation."""
        # Test realistic resource consumption
        realistic_metrics = ExecutionMetrics(
            total_execution_time=5.2,
            task_execution_times={'task_1': 2.1, 'task_2': 3.1},
            memory_usage={'peak_mb': 128, 'average_mb': 96},
            api_response_times={'/api/evaluate': [1.2, 0.8, 1.5, 1.1]},
            error_rates={'overall': 0.02},
            success_rates={'overall': 0.98}
        )
        
        assert self.validator.validate_resource_consumption(realistic_metrics) is True
        
        # Test unrealistic resource consumption
        unrealistic_metrics = ExecutionMetrics(
            total_execution_time=0.001,  # Too fast
            task_execution_times={'task_1': 0.0001},
            memory_usage={'peak_mb': 1},  # Too low
            api_response_times={'/api/evaluate': [0.001, 0.001, 0.001]},  # Too consistent
            error_rates={'overall': 0.0},  # Too perfect
            success_rates={'overall': 1.0}  # Too perfect
        )
        
        assert self.validator.validate_resource_consumption(unrealistic_metrics) is False
    
    def test_genuine_results_validation(self):
        """Test validation of genuine vs fabricated results."""
        # Test realistic results with variance
        genuine_results = {
            'scores': [0.85, 0.92, 0.78, 0.89, 0.91],
            'response_times': [1.2, 0.8, 1.5, 1.1, 0.9],
            'token_counts': [45, 52, 38, 49, 51],
            'metadata': {
                'model_version': 'gpt-3.5-turbo-0613',
                'timestamp': time.time(),
                'request_id': 'req_abc123'
            }
        }
        
        assert self.validator.validate_genuine_results(genuine_results) is True
        
        # Test suspicious results
        suspicious_results = {
            'scores': [1.0, 1.0, 1.0, 1.0, 1.0],  # Too perfect
            'response_times': [0.1, 0.1, 0.1, 0.1, 0.1],  # Too consistent
            'token_counts': [50, 50, 50, 50, 50],  # Identical
            'metadata': {}  # Missing metadata
        }
        
        assert self.validator.validate_genuine_results(suspicious_results) is False
    
    def test_real_execution_context_manager(self):
        """Test the real execution context manager."""
        with RealExecutionContext(self.validator) as validator:
            # Simulate some tracking
            validator.record_api_call('https://api.openai.com/v1/completions', 'POST', {'result': 'test'})
            validator.record_resource_snapshot()
            validator.record_network_connection('api.openai.com', 443, 1024, 2048)
            validator.record_file_operation('write', '/tmp/test.json', 512)
        
        # Verify tracking data was recorded
        assert len(validator._api_calls_made) == 1
        assert len(validator._resource_snapshots) >= 1
        assert len(validator._network_connections) == 1
        assert len(validator._file_operations) == 1
    
    def test_validation_report_generation(self):
        """Test comprehensive validation report generation."""
        execution_data = {
            'test_result': self.real_result,
            'api_logs': [
                {
                    'endpoint': 'https://api.openai.com/v1/completions',
                    'status_code': 200,
                    'response_time': 1.2,
                    'tokens_used': 50
                }
            ],
            'network_logs': [
                {
                    'destination': 'api.openai.com',
                    'port': 443,
                    'bytes_sent': 1024,
                    'bytes_received': 2048,
                    'duration': 1.2
                }
            ],
            'resource_metrics': ExecutionMetrics(
                total_execution_time=2.5,
                task_execution_times={'test_001': 2.5},
                memory_usage={'peak_mb': 128},
                api_response_times={'/api/test': [1.2, 0.8, 1.5]},
                error_rates={'overall': 0.02},
                success_rates={'overall': 0.98}
            )
        }
        
        report = self.validator.generate_validation_report(execution_data)
        
        # Verify report structure
        assert 'validation_result' in report
        assert 'confidence_score' in report
        assert 'checks_performed' in report
        assert 'evidence' in report
        assert 'recommendations' in report
        
        # Verify report content
        assert isinstance(report['validation_result'], bool)
        assert 0 <= report['confidence_score'] <= 1
        assert isinstance(report['checks_performed'], dict)
        assert isinstance(report['evidence'], dict)
        assert isinstance(report['recommendations'], list)
    
    def test_score_distribution_validation(self):
        """Test score distribution validation patterns."""
        # Test realistic score distribution
        realistic_scores = [0.85, 0.92, 0.78, 0.89, 0.91, 0.76, 0.94]
        assert self.validator._validate_score_distribution(realistic_scores) is True
        
        # Test perfect scores (suspicious)
        perfect_scores = [1.0, 1.0, 1.0, 1.0, 1.0]
        assert self.validator._validate_score_distribution(perfect_scores) is False
        
        # Test identical scores (suspicious)
        identical_scores = [0.85, 0.85, 0.85, 0.85, 0.85]
        assert self.validator._validate_score_distribution(identical_scores) is False
        
        # Test out of range scores
        invalid_scores = [0.85, 1.2, 0.78, -0.1, 0.91]
        assert self.validator._validate_score_distribution(invalid_scores) is False
    
    def test_response_time_pattern_validation(self):
        """Test response time pattern validation."""
        # Test realistic response times with variance
        realistic_times = [1.2, 0.8, 1.5, 1.1, 0.9, 1.3, 0.7]
        assert self.validator._validate_response_time_patterns(realistic_times) is True
        
        # Test identical response times (suspicious)
        identical_times = [1.0, 1.0, 1.0, 1.0, 1.0]
        assert self.validator._validate_response_time_patterns(identical_times) is False
        
        # Test with custom threshold
        self.validator.set_validation_thresholds({'min_response_time_variance': 0.1})
        low_variance_times = [1.0, 1.01, 1.02, 1.01, 1.0]
        assert self.validator._validate_response_time_patterns(low_variance_times) is False
    
    def test_network_activity_validation_detailed(self):
        """Test detailed network activity validation."""
        # Test realistic network activity
        realistic_network = [
            {
                'destination': 'api.openai.com',
                'port': 443,
                'bytes_sent': 1024,
                'bytes_received': 2048,
                'duration': 1.2
            },
            {
                'destination': 'api.anthropic.com',
                'port': 443,
                'bytes_sent': 512,
                'bytes_received': 1536,
                'duration': 0.8
            }
        ]
        
        assert self.validator.validate_network_activity(realistic_network) is True
        
        # Test insufficient network activity
        minimal_network = [
            {
                'destination': 'localhost',
                'port': 8000,
                'bytes_sent': 10,
                'bytes_received': 20,
                'duration': 0.1
            }
        ]
        
        assert self.validator.validate_network_activity(minimal_network) is False
        
        # Test invalid network data
        invalid_network = [
            {
                'destination': '',  # Empty destination
                'port': -1,  # Invalid port
                'bytes_sent': -100,  # Negative bytes
                'bytes_received': -200,
                'duration': 0.1
            }
        ]
        
        assert self.validator.validate_network_activity(invalid_network) is False
    
    def test_file_system_operations_validation(self):
        """Test file system operations validation."""
        # Test valid file operations
        valid_operations = [
            {
                'operation': 'write',
                'path': '/tmp/test_results.json',
                'size': 1024,
                'timestamp': time.time()
            },
            {
                'operation': 'read',
                'path': '/tmp/config.yaml',
                'size': 512,
                'timestamp': time.time()
            }
        ]
        
        assert self.validator.validate_file_system_operations(valid_operations) is True
        
        # Test invalid file operations
        invalid_operations = [
            {
                'operation': 'invalid_op',  # Invalid operation type
                'path': '',  # Empty path
                'size': -100,  # Negative size
                'timestamp': time.time()
            }
        ]
        
        assert self.validator.validate_file_system_operations(invalid_operations) is False
        
        # Test empty operations (should be valid)
        assert self.validator.validate_file_system_operations([]) is True
    
    def test_confidence_score_calculation(self):
        """Test confidence score calculation."""
        # Test high confidence scenario
        high_confidence_checks = {
            'mock_detection': True,
            'api_calls': True,
            'network_activity': True,
            'resource_consumption': True,
            'result_authenticity': True
        }
        
        execution_data = {'test_result': self.real_result}
        score = self.validator._calculate_confidence_score(execution_data, high_confidence_checks)
        assert score == 1.0
        
        # Test low confidence scenario
        low_confidence_checks = {
            'mock_detection': False,
            'api_calls': False,
            'network_activity': False,
            'resource_consumption': False,
            'result_authenticity': False
        }
        
        score = self.validator._calculate_confidence_score(execution_data, low_confidence_checks)
        assert score == 0.0
        
        # Test mixed scenario
        mixed_checks = {
            'mock_detection': True,
            'api_calls': False,
            'network_activity': True,
            'resource_consumption': False,
            'result_authenticity': True
        }
        
        score = self.validator._calculate_confidence_score(execution_data, mixed_checks)
        assert 0.0 < score < 1.0
    
    def test_validation_configuration(self):
        """Test validation configuration options."""
        # Test disabling specific validations
        self.validator.configure_validation(
            mock_detection=False,
            resource_tracking=False,
            api_call_tracking=True
        )
        
        # Verify configuration was applied
        assert self.validator._mock_detection_enabled is False
        assert self.validator._resource_tracking_enabled is False
        assert self.validator._api_call_tracking_enabled is True
        
        # Test that disabled validations are skipped
        execution_context = {'mock_objects_detected': True}
        assert self.validator.validate_no_mocks(execution_context) is True  # Should pass because disabled