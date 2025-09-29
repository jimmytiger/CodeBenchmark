#!/usr/bin/env python3
"""
Test script for SWE-bench adapter validator.

This script demonstrates the SWE-bench adapter validation functionality
and can be used to verify the implementation works correctly.
"""

import sys
import logging
from pathlib import Path

# Add the project root to Python path
project_root = Path(__file__).parent.parent
sys.path.insert(0, str(project_root))

from EvaluationEngineV1_0_tests.core.swe_bench_adapter_validator import SWEBenchAdapterValidator
from EvaluationEngineV1_0_tests.models.test_models import TestStatus


def setup_logging():
    """Set up logging for the test."""
    logging.basicConfig(
        level=logging.INFO,
        format='%(asctime)s - %(name)s - %(levelname)s - %(message)s',
        handlers=[
            logging.StreamHandler(),
            logging.FileHandler('swe_bench_validator_test.log')
        ]
    )


def test_swe_bench_validator():
    """Test the SWE-bench adapter validator."""
    print("=" * 60)
    print("SWE-bench Adapter Validator Test")
    print("=" * 60)
    
    # Initialize validator
    config = {
        "timeout": 300,
        "test_task_count": 1
    }
    
    validator = SWEBenchAdapterValidator(config)
    
    # Test 1: Get adapter info
    print("\n1. Testing adapter info retrieval...")
    try:
        adapter_info = validator.get_adapter_info()
        print(f"   ✓ Adapter Name: {adapter_info.name}")
        print(f"   ✓ Adapter Type: {adapter_info.adapter_type.value}")
        print(f"   ✓ Version: {adapter_info.version}")
        print(f"   ✓ Dependencies: {len(adapter_info.dependencies)}")
    except Exception as e:
        print(f"   ✗ Failed: {e}")
    
    # Test 2: Install dependencies
    print("\n2. Testing dependency installation...")
    try:
        deps_installed = validator.install_dependencies()
        if deps_installed:
            print("   ✓ All required dependencies are available")
        else:
            print("   ⚠ Some dependencies are missing")
        
        print("   Dependency status:")
        for dep_name, status in validator.dependency_status.items():
            print(f"     - {dep_name}: {status}")
    except Exception as e:
        print(f"   ✗ Failed: {e}")
    
    # Test 3: Environment setup
    print("\n3. Testing environment setup...")
    try:
        env_setup = validator.setup_environment()
        if env_setup:
            print("   ✓ Environment setup successful")
            print(f"   ✓ Work directory: {validator.work_dir}")
        else:
            print("   ✗ Environment setup failed")
    except Exception as e:
        print(f"   ✗ Failed: {e}")
    
    # Test 4: Full integration validation
    print("\n4. Testing full integration validation...")
    try:
        validation_result = validator.validate_integration()
        
        print(f"   Integration Status: {validation_result.integration_status.value}")
        print(f"   Dependencies Installed: {validation_result.dependencies_installed}")
        print(f"   Validation Time: {validation_result.validation_time:.2f}s")
        print(f"   Test Results: {len(validation_result.test_results)}")
        
        if validation_result.test_results:
            print("   Test Results Details:")
            for i, test_result in enumerate(validation_result.test_results):
                status_symbol = "✓" if test_result.status == TestStatus.PASSED else "✗"
                print(f"     {i+1}. {status_symbol} {test_result.name}: {test_result.status.value}")
                if test_result.error_details:
                    print(f"        Error: {test_result.error_details}")
        
        if validation_result.issues_found:
            print("   Issues Found:")
            for issue in validation_result.issues_found:
                print(f"     - {issue}")
        
        if validation_result.recommendations:
            print("   Recommendations:")
            for rec in validation_result.recommendations:
                print(f"     - {rec}")
        
        if validation_result.performance_metrics:
            print("   Performance Metrics:")
            for metric, value in validation_result.performance_metrics.items():
                print(f"     - {metric}: {value}")
        
    except Exception as e:
        print(f"   ✗ Failed: {e}")
        import traceback
        traceback.print_exc()
    
    # Test 5: Software task testing
    print("\n5. Testing software task execution...")
    try:
        task_results = validator.test_software_tasks(1)
        
        if task_results:
            print(f"   ✓ Executed {len(task_results)} task(s)")
            for i, result in enumerate(task_results):
                status_symbol = "✓" if result.status == TestStatus.PASSED else "✗"
                print(f"     {i+1}. {status_symbol} {result.name}: {result.status.value}")
                print(f"        Execution Time: {result.execution_time:.2f}s")
                print(f"        Real Execution Validated: {result.real_execution_validated}")
                
                if result.metrics:
                    print("        Metrics:")
                    for metric, value in result.metrics.items():
                        print(f"          - {metric}: {value}")
        else:
            print("   ⚠ No tasks were executed")
            
    except Exception as e:
        print(f"   ✗ Failed: {e}")
        import traceback
        traceback.print_exc()
    
    print("\n" + "=" * 60)
    print("SWE-bench Adapter Validator Test Complete")
    print("=" * 60)


def main():
    """Main function."""
    setup_logging()
    
    try:
        test_swe_bench_validator()
    except KeyboardInterrupt:
        print("\nTest interrupted by user")
    except Exception as e:
        print(f"\nTest failed with error: {e}")
        import traceback
        traceback.print_exc()
        return 1
    
    return 0


if __name__ == "__main__":
    sys.exit(main())