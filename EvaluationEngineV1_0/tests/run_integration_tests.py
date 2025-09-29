#!/usr/bin/env python3
"""
Integration Test Runner

This script runs comprehensive integration tests for the multi-turn evaluation engine,
including performance benchmarks, load testing, and compatibility validation.

Requirements: 10.1, 10.2, 10.3, 10.4, 10.5
"""

import sys
import os
import time
import subprocess
import argparse
from pathlib import Path
from typing import List, Dict, Any
import json

# Add the project root to Python path
project_root = Path(__file__).parent.parent.parent
sys.path.insert(0, str(project_root))

from EvaluationEngineV1_0.tests.test_data_generator import TestDataGenerator, TestScenarioGenerator


class IntegrationTestRunner:
    """Run comprehensive integration tests."""
    
    def __init__(self, verbose: bool = False):
        self.verbose = verbose
        self.test_results = {}
        self.generator = TestDataGenerator()
        self.scenario_generator = TestScenarioGenerator()
    
    def run_compatibility_tests(self) -> Dict[str, Any]:
        """Run backward compatibility tests."""
        print("Running backward compatibility tests...")
        
        cmd = [
            sys.executable, "-m", "pytest",
            "EvaluationEngineV1_0/tests/test_compatibility.py",
            "-v" if self.verbose else "-q",
            "--tb=short"
        ]
        
        start_time = time.time()
        result = subprocess.run(cmd, capture_output=True, text=True, cwd=project_root)
        execution_time = time.time() - start_time
        
        return {
            "name": "Backward Compatibility Tests",
            "success": result.returncode == 0,
            "execution_time": execution_time,
            "stdout": result.stdout,
            "stderr": result.stderr,
            "return_code": result.returncode
        }
    
    def run_integration_tests(self) -> Dict[str, Any]:
        """Run end-to-end integration tests."""
        print("Running end-to-end integration tests...")
        
        cmd = [
            sys.executable, "-m", "pytest",
            "EvaluationEngineV1_0/tests/test_integration.py",
            "-v" if self.verbose else "-q",
            "--tb=short",
            "-m", "integration"
        ]
        
        start_time = time.time()
        result = subprocess.run(cmd, capture_output=True, text=True, cwd=project_root)
        execution_time = time.time() - start_time
        
        return {
            "name": "End-to-End Integration Tests",
            "success": result.returncode == 0,
            "execution_time": execution_time,
            "stdout": result.stdout,
            "stderr": result.stderr,
            "return_code": result.returncode
        }
    
    def run_performance_tests(self) -> Dict[str, Any]:
        """Run performance and load tests."""
        print("Running performance tests...")
        
        cmd = [
            sys.executable, "-m", "pytest",
            "EvaluationEngineV1_0/tests/test_performance.py",
            "-v" if self.verbose else "-q",
            "--tb=short",
            "-m", "performance"
        ]
        
        start_time = time.time()
        result = subprocess.run(cmd, capture_output=True, text=True, cwd=project_root)
        execution_time = time.time() - start_time
        
        return {
            "name": "Performance Tests",
            "success": result.returncode == 0,
            "execution_time": execution_time,
            "stdout": result.stdout,
            "stderr": result.stderr,
            "return_code": result.returncode
        }
    
    def validate_test_scenarios(self) -> Dict[str, Any]:
        """Validate generated test scenarios."""
        print("Validating test scenarios...")
        
        start_time = time.time()
        errors = []
        
        try:
            # Test single-turn scenario
            single_config, single_tasks = self.scenario_generator.generate_single_turn_scenario()
            single_config.validate()
            
            # Test multi-turn scenario
            multi_config, multi_tasks = self.scenario_generator.generate_multi_turn_scenario()
            multi_config.validate()
            
            # Test mixed scenario
            mixed_config, mixed_tasks = self.scenario_generator.generate_mixed_scenario()
            mixed_config.validate()
            
            # Test error scenarios
            error_scenarios = self.scenario_generator.generate_error_scenarios()
            for name, config, expected_error in error_scenarios:
                try:
                    config.validate()
                    errors.append(f"Error scenario '{name}' should have failed validation")
                except ValueError as e:
                    if expected_error not in str(e):
                        errors.append(f"Error scenario '{name}' failed with unexpected error: {e}")
            
        except Exception as e:
            errors.append(f"Scenario validation failed: {e}")
        
        execution_time = time.time() - start_time
        
        return {
            "name": "Test Scenario Validation",
            "success": len(errors) == 0,
            "execution_time": execution_time,
            "errors": errors,
            "scenarios_tested": 3 + len(error_scenarios) if 'error_scenarios' in locals() else 3
        }
    
    def test_data_generation(self) -> Dict[str, Any]:
        """Test data generation capabilities."""
        print("Testing data generation...")
        
        start_time = time.time()
        errors = []
        
        try:
            # Generate various configurations
            for i in range(10):
                config = self.generator.generate_evaluation_config(
                    num_models=2 + i % 3,
                    num_tasks=3 + i % 5
                )
                config.validate()
            
            # Generate evaluation results
            for i in range(5):
                result = self.generator.generate_evaluation_result(
                    num_turns=1 + i % 10
                )
                # Basic validation
                assert result.evaluation_id
                assert result.task_id
                assert result.model_id
                assert len(result.turn_results) == result.total_turns
            
            # Generate legacy configurations
            for i in range(5):
                legacy_config = self.generator.generate_legacy_config()
                assert 'model' in legacy_config
                assert 'tasks' in legacy_config
            
        except Exception as e:
            errors.append(f"Data generation failed: {e}")
        
        execution_time = time.time() - start_time
        
        return {
            "name": "Data Generation Tests",
            "success": len(errors) == 0,
            "execution_time": execution_time,
            "errors": errors,
            "configs_generated": 10,
            "results_generated": 5,
            "legacy_configs_generated": 5
        }
    
    def run_all_tests(self) -> Dict[str, Any]:
        """Run all integration tests."""
        print("Starting comprehensive integration test suite...")
        print("=" * 60)
        
        total_start_time = time.time()
        
        # Run all test categories
        test_categories = [
            self.validate_test_scenarios,
            self.test_data_generation,
            self.run_compatibility_tests,
            self.run_integration_tests,
            self.run_performance_tests
        ]
        
        results = []
        for test_func in test_categories:
            try:
                result = test_func()
                results.append(result)
                
                # Print immediate feedback
                status = "✓ PASS" if result["success"] else "✗ FAIL"
                print(f"{status} {result['name']} ({result['execution_time']:.2f}s)")
                
                if not result["success"] and self.verbose:
                    if "errors" in result:
                        for error in result["errors"]:
                            print(f"  Error: {error}")
                    if "stderr" in result and result["stderr"]:
                        print(f"  Stderr: {result['stderr']}")
                
            except Exception as e:
                error_result = {
                    "name": test_func.__name__,
                    "success": False,
                    "execution_time": 0,
                    "error": str(e)
                }
                results.append(error_result)
                print(f"✗ FAIL {test_func.__name__} (Exception: {e})")
        
        total_execution_time = time.time() - total_start_time
        
        # Calculate summary statistics
        total_tests = len(results)
        passed_tests = sum(1 for r in results if r["success"])
        failed_tests = total_tests - passed_tests
        
        summary = {
            "total_execution_time": total_execution_time,
            "total_tests": total_tests,
            "passed_tests": passed_tests,
            "failed_tests": failed_tests,
            "success_rate": passed_tests / total_tests if total_tests > 0 else 0,
            "results": results
        }
        
        # Print summary
        print("=" * 60)
        print(f"Integration Test Summary:")
        print(f"  Total Tests: {total_tests}")
        print(f"  Passed: {passed_tests}")
        print(f"  Failed: {failed_tests}")
        print(f"  Success Rate: {summary['success_rate']:.1%}")
        print(f"  Total Time: {total_execution_time:.2f}s")
        
        if failed_tests > 0:
            print("\nFailed Tests:")
            for result in results:
                if not result["success"]:
                    print(f"  - {result['name']}")
        
        return summary
    
    def save_results(self, results: Dict[str, Any], output_file: str):
        """Save test results to file."""
        with open(output_file, 'w') as f:
            json.dump(results, f, indent=2, default=str)
        print(f"\nTest results saved to: {output_file}")


def main():
    """Main entry point."""
    parser = argparse.ArgumentParser(description="Run integration tests for multi-turn evaluation engine")
    parser.add_argument("-v", "--verbose", action="store_true", help="Verbose output")
    parser.add_argument("-o", "--output", help="Output file for test results")
    parser.add_argument("--compatibility-only", action="store_true", help="Run only compatibility tests")
    parser.add_argument("--performance-only", action="store_true", help="Run only performance tests")
    parser.add_argument("--integration-only", action="store_true", help="Run only integration tests")
    
    args = parser.parse_args()
    
    runner = IntegrationTestRunner(verbose=args.verbose)
    
    # Run specific test categories if requested
    if args.compatibility_only:
        results = {"results": [runner.run_compatibility_tests()]}
    elif args.performance_only:
        results = {"results": [runner.run_performance_tests()]}
    elif args.integration_only:
        results = {"results": [runner.run_integration_tests()]}
    else:
        # Run all tests
        results = runner.run_all_tests()
    
    # Save results if requested
    if args.output:
        runner.save_results(results, args.output)
    
    # Exit with appropriate code
    if "success_rate" in results:
        exit_code = 0 if results["success_rate"] == 1.0 else 1
    else:
        exit_code = 0 if all(r["success"] for r in results["results"]) else 1
    
    sys.exit(exit_code)


if __name__ == "__main__":
    main()