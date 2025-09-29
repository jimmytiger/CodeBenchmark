#!/usr/bin/env python3
"""
Simple script to run CLI tests for EvaluationEngineV1_0.

This script provides an easy way to run various CLI tests without
having to remember all the command-line arguments.
"""

import sys
import logging
from pathlib import Path

from .cli.cli_test_runner import CLITestRunner
from .cli.cli_result_formatter import CLIResultFormatter
from .core.error_handler import setup_error_logging


def run_builtin_tests():
    """Run tests with builtin tasks."""
    print("Running builtin task tests...")
    
    runner = CLITestRunner()
    formatter = CLIResultFormatter()
    
    # Test configuration
    config = {
        "timeout": 300,
        "verbose": True,
        "output_format": "json",
        "limit": 5  # Limit samples for faster testing
    }
    
    # Test hellaswag task
    tasks = ["hellaswag"]
    result = runner.run_builtin_tasks(tasks, config)
    
    # Display results
    print(f"\nBuiltin Test Results:")
    print(f"Success: {result['success']}")
    print(f"Execution Time: {result['execution_time']:.2f}s")
    print(f"Command: {result['command']}")
    print(f"Return Code: {result['return_code']}")
    
    if result.get('metrics'):
        print(f"Metrics: {result['metrics']}")
    
    if result.get('error'):
        print(f"Error: {result['error']}")
    
    # Save results
    output_path = Path("builtin_test_results.json")
    formatter.save_results(result, output_path, "json")
    print(f"Results saved to: {output_path}")
    
    return result['success']


def run_custom_tests():
    """Run tests with custom tasks."""
    print("Running custom task tests...")
    
    custom_task_dir = Path("lm_eval/tasks")
    
    if not custom_task_dir.exists():
        print(f"Custom task directory not found: {custom_task_dir}")
        print("Skipping custom task tests")
        return True
    
    runner = CLITestRunner()
    formatter = CLIResultFormatter()
    
    # Test configuration
    config = {
        "timeout": 600,
        "verbose": True,
        "output_format": "json"
    }
    
    result = runner.run_custom_tasks(custom_task_dir, config)
    
    # Display results
    print(f"\nCustom Test Results:")
    print(f"Success: {result['success']}")
    print(f"Execution Time: {result['execution_time']:.2f}s")
    
    if result.get('metrics'):
        print(f"Metrics: {result['metrics']}")
    
    if result.get('error'):
        print(f"Error: {result['error']}")
    
    # Save results
    output_path = Path("custom_test_results.json")
    formatter.save_results(result, output_path, "json")
    print(f"Results saved to: {output_path}")
    
    return result['success']


def run_adapter_tests():
    """Run adapter validation tests."""
    print("Running adapter tests...")
    
    runner = CLITestRunner()
    formatter = CLIResultFormatter()
    
    # Test configuration
    config = {
        "timeout": 600,
        "verbose": True,
        "output_format": "json"
    }
    
    # Test lm_eval adapter
    result = runner.run_adapter_tests("lm_eval", config)
    
    # Display results
    print(f"\nAdapter Test Results:")
    print(f"Success: {result['success']}")
    print(f"Execution Time: {result['execution_time']:.2f}s")
    
    if result.get('metrics'):
        print(f"Metrics: {result['metrics']}")
    
    if result.get('error'):
        print(f"Error: {result['error']}")
    
    # Save results
    output_path = Path("adapter_test_results.json")
    formatter.save_results(result, output_path, "json")
    print(f"Results saved to: {output_path}")
    
    return result['success']


def run_pipeline_tests():
    """Run full pipeline tests."""
    print("Running pipeline tests...")
    
    runner = CLITestRunner()
    formatter = CLIResultFormatter()
    
    # Test configuration
    config = {
        "timeout": 1200,
        "verbose": True,
        "output_format": "json"
    }
    
    result = runner.run_full_pipeline(config)
    
    # Display results
    print(f"\nPipeline Test Results:")
    print(f"Success: {result['success']}")
    print(f"Execution Time: {result['execution_time']:.2f}s")
    
    if result.get('metrics'):
        print(f"Metrics: {result['metrics']}")
    
    if result.get('error'):
        print(f"Error: {result['error']}")
    
    # Save results
    output_path = Path("pipeline_test_results.json")
    formatter.save_results(result, output_path, "json")
    print(f"Results saved to: {output_path}")
    
    return result['success']


def main():
    """Main function to run all CLI tests."""
    # Setup logging
    setup_error_logging("INFO", "cli_tests.log")
    
    print("EvaluationEngineV1_0 CLI Testing")
    print("=" * 40)
    
    results = {}
    
    try:
        # Run all test types
        print("\n1. Testing builtin tasks...")
        results['builtin'] = run_builtin_tests()
        
        print("\n2. Testing custom tasks...")
        results['custom'] = run_custom_tests()
        
        print("\n3. Testing adapters...")
        results['adapter'] = run_adapter_tests()
        
        print("\n4. Testing pipeline...")
        results['pipeline'] = run_pipeline_tests()
        
        # Summary
        print("\n" + "=" * 40)
        print("Test Summary:")
        total_tests = len(results)
        passed_tests = sum(1 for success in results.values() if success)
        
        for test_type, success in results.items():
            status = "PASSED" if success else "FAILED"
            print(f"  {test_type.capitalize()}: {status}")
        
        print(f"\nOverall: {passed_tests}/{total_tests} tests passed")
        
        if passed_tests == total_tests:
            print("🎉 All tests passed!")
            sys.exit(0)
        else:
            print("❌ Some tests failed. Check the logs for details.")
            sys.exit(1)
    
    except KeyboardInterrupt:
        print("\nTests interrupted by user")
        sys.exit(1)
    except Exception as e:
        print(f"\nTest execution failed: {e}")
        sys.exit(1)


if __name__ == "__main__":
    main()