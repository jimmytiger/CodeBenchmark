#!/usr/bin/env python3
"""
Demonstration of the Real Execution Validation System

This script shows how to use the RealExecutionValidator to validate
that tests perform real execution without mock data.
"""

import time
import logging
import sys
import os

# Add the current directory to Python path
sys.path.insert(0, os.path.dirname(os.path.abspath(__file__)))

from models.test_models import TestResult, ExecutionMetrics, TestType, TestStatus

# Set up logging
logging.basicConfig(level=logging.INFO)
logger = logging.getLogger(__name__)

def demo_real_execution_validation():
    """Demonstrate real execution validation capabilities."""
    
    print("=" * 60)
    print("Real Execution Validation System Demo")
    print("=" * 60)
    
    # Import here to avoid circular import issues
    from core.real_execution_validator import RealExecutionValidator, RealExecutionContext
    
    # Create validator
    validator = RealExecutionValidator()
    
    # Configure for demo (disable mock detection since we're in a demo environment)
    validator.configure_validation(
        mock_detection=False,  # Disabled for demo
        resource_tracking=True,
        api_call_tracking=True
    )
    
    print("\n1. Testing with REALISTIC execution data:")
    print("-" * 40)
    
    # Create realistic test result
    real_test_result = TestResult(
        test_id='demo_real_001',
        test_type=TestType.INTEGRATION,
        name='Real API Integration Test',
        status=TestStatus.PASSED,
        execution_time=3.2,
        real_execution_validated=True,
        metrics={
            'api_calls': 5,
            'tokens_used': 150,
            'model_responses': 3,
            'network_requests': 8
        },
        logs=[
            'Starting integration test',
            'Making API call to https://api.openai.com/v1/completions',
            'Received response with 50 tokens',
            'Processing model output',
            'Test completed successfully'
        ],
        artifacts=['response_1.json', 'response_2.json']
    )
    
    # Create realistic execution data
    realistic_execution_data = {
        'test_result': real_test_result,
        'api_logs': [
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
        ],
        'network_logs': [
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
        ],
        'resource_metrics': ExecutionMetrics(
            total_execution_time=3.2,
            task_execution_times={'demo_real_001': 3.2},
            memory_usage={'peak_mb': 128, 'average_mb': 96},
            api_response_times={'/api/completions': [1.2, 0.8, 1.5, 1.1]},
            error_rates={'overall': 0.02},
            success_rates={'overall': 0.98}
        )
    }
    
    # Validate realistic execution
    is_valid = validator.comprehensive_validation(realistic_execution_data)
    print(f"Realistic execution validation result: {'✅ PASSED' if is_valid else '❌ FAILED'}")
    
    # Generate detailed report
    report = validator.generate_validation_report(realistic_execution_data)
    print(f"Confidence score: {report['confidence_score']:.2%}")
    print(f"Checks performed: {list(report['checks_performed'].keys())}")
    
    print("\n2. Testing with SUSPICIOUS execution data:")
    print("-" * 40)
    
    # Create suspicious test result
    suspicious_test_result = TestResult(
        test_id='demo_suspicious_001',
        test_type=TestType.UNIT,
        name='Suspicious Fast Test',
        status=TestStatus.PASSED,
        execution_time=0.001,  # Too fast
        real_execution_validated=False,
        metrics={
            'api_calls': 0,  # No API calls
            'tokens_used': 0,
            'model_responses': 0,
            'network_requests': 0
        },
        logs=[],  # No logs
        artifacts=[]
    )
    
    # Create suspicious execution data
    suspicious_execution_data = {
        'test_result': suspicious_test_result,
        'api_logs': [],  # No API calls
        'network_logs': [],  # No network activity
        'resource_metrics': ExecutionMetrics(
            total_execution_time=0.001,  # Too fast
            task_execution_times={'demo_suspicious_001': 0.001},
            memory_usage={'peak_mb': 1, 'average_mb': 1},  # Too low
            api_response_times={},
            error_rates={'overall': 0.0},  # Too perfect
            success_rates={'overall': 1.0}  # Too perfect
        )
    }
    
    # Validate suspicious execution
    is_valid = validator.comprehensive_validation(suspicious_execution_data)
    print(f"Suspicious execution validation result: {'✅ PASSED' if is_valid else '❌ FAILED'}")
    
    # Generate detailed report
    report = validator.generate_validation_report(suspicious_execution_data)
    print(f"Confidence score: {report['confidence_score']:.2%}")
    print(f"Recommendations: {report['recommendations']}")
    
    print("\n3. Testing individual validation components:")
    print("-" * 40)
    
    # Test score distribution validation
    realistic_scores = [0.85, 0.92, 0.78, 0.89, 0.91, 0.76, 0.94]
    perfect_scores = [1.0, 1.0, 1.0, 1.0, 1.0]
    
    print(f"Realistic scores validation: {'✅ PASSED' if validator._validate_score_distribution(realistic_scores) else '❌ FAILED'}")
    print(f"Perfect scores validation: {'✅ PASSED' if validator._validate_score_distribution(perfect_scores) else '❌ FAILED'}")
    
    # Test response time validation
    realistic_times = [1.2, 0.8, 1.5, 1.1, 0.9, 1.3, 0.7]
    identical_times = [1.0, 1.0, 1.0, 1.0, 1.0]
    
    print(f"Realistic response times validation: {'✅ PASSED' if validator._validate_response_time_patterns(realistic_times) else '❌ FAILED'}")
    print(f"Identical response times validation: {'✅ PASSED' if validator._validate_response_time_patterns(identical_times) else '❌ FAILED'}")
    
    print("\n4. Testing context manager usage:")
    print("-" * 40)
    
    # Import context manager
    from core.real_execution_validator import RealExecutionContext
    
    # Demonstrate context manager usage
    with RealExecutionContext(validator) as ctx_validator:
        print("Starting tracked execution...")
        
        # Simulate some real execution activities
        ctx_validator.record_api_call('https://api.openai.com/v1/completions', 'POST', {'result': 'success'})
        ctx_validator.record_resource_snapshot()
        ctx_validator.record_network_connection('api.openai.com', 443, 1024, 2048)
        ctx_validator.record_file_operation('write', '/tmp/test_results.json', 512)
        
        time.sleep(0.1)  # Simulate some processing time
        
        print("Execution tracking completed")
    
    # Get validation report
    validation_report = ctx_validator.get_validation_report()
    print(f"Tracked activities: {validation_report['execution_indicators']}")
    
    print("\n5. Custom validation thresholds:")
    print("-" * 40)
    
    # Set custom thresholds
    custom_thresholds = {
        'min_execution_time': 2.0,  # Require at least 2 seconds
        'max_success_rate': 0.95,   # Allow up to 5% failures
        'min_response_time_variance': 0.05  # Require some variance
    }
    
    validator.set_validation_thresholds(custom_thresholds)
    print(f"Custom thresholds applied: {custom_thresholds}")
    
    # Test with custom thresholds
    test_metrics = ExecutionMetrics(
        total_execution_time=2.5,  # Meets minimum
        memory_usage={'peak_mb': 64},
        success_rates={'overall': 0.94},  # Within allowed range
        api_response_times={'/api/test': [1.0, 1.2, 0.8, 1.5]}  # Has variance
    )
    
    is_valid = validator.validate_resource_consumption(test_metrics)
    print(f"Custom threshold validation: {'✅ PASSED' if is_valid else '❌ FAILED'}")
    
    print("\n" + "=" * 60)
    print("Demo completed! The Real Execution Validation System provides:")
    print("• Mock detection mechanisms")
    print("• API call authenticity validation")
    print("• Resource consumption verification")
    print("• Result pattern analysis")
    print("• Comprehensive reporting")
    print("• Configurable validation thresholds")
    print("=" * 60)

if __name__ == "__main__":
    demo_real_execution_validation()