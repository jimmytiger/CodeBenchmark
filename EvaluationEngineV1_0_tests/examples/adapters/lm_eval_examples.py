#!/usr/bin/env python3
"""
LM-Eval Adapter Examples for EvaluationEngineV1_0 Testing Framework

This script demonstrates how to validate and test the lm_eval adapter
with various configurations and scenarios.
"""

import sys
import logging
import time
import json
from pathlib import Path
from typing import Dict, List, Any, Optional

# Add the test framework to the path
sys.path.insert(0, str(Path(__file__).parent.parent.parent))

from adapters.lm_eval_adapter_validator import LMEvalAdapterValidator
from core.config_manager import ConfigManager
from core.metrics_collector import MetricsCollector
from core.real_execution_validator import RealExecutionValidator
from models.test_models import TestConfiguration, TestType, AdapterType


def setup_logging() -> logging.Logger:
    """Setup logging for the examples."""
    logging.basicConfig(
        level=logging.INFO,
        format='%(asctime)s - %(name)s - %(levelname)s - %(message)s',
        handlers=[
            logging.StreamHandler(sys.stdout),
            logging.FileHandler('lm_eval_examples.log')
        ]
    )
    return logging.getLogger(__name__)


def example_1_basic_validation(logger: logging.Logger) -> Dict[str, Any]:
    """Example 1: Basic LM-Eval adapter validation."""
    logger.info("=== Example 1: Basic LM-Eval Adapter Validation ===")
    
    try:
        # Create validator
        validator = LMEvalAdapterValidator()
        
        # Basic validation
        logger.info("Running basic adapter validation...")
        validation_result = validator.validate_integration()
        
        logger.info(f"Validation result: {validation_result.integration_status}")
        logger.info(f"Dependencies installed: {validation_result.dependencies_installed}")
        
        if validation_result.issues_found:
            logger.warning("Issues found during validation:")
            for issue in validation_result.issues_found:
                logger.warning(f"  - {issue}")
        
        # Performance metrics
        if validation_result.performance_metrics:
            logger.info("Performance metrics:")
            for metric, value in validation_result.performance_metrics.items():
                logger.info(f"  {metric}: {value}")
        
        return {
            "success": validation_result.integration_status == "success",
            "dependencies_ok": validation_result.dependencies_installed,
            "issues_count": len(validation_result.issues_found),
            "metrics": validation_result.performance_metrics
        }
        
    except Exception as e:
        logger.error(f"Basic validation failed: {e}")
        return {"success": False, "error": str(e)}


def example_2_builtin_task_testing(logger: logging.Logger) -> Dict[str, Any]:
    """Example 2: Test builtin tasks with lm_eval adapter."""
    logger.info("=== Example 2: Builtin Task Testing ===")
    
    try:
        validator = LMEvalAdapterValidator()
        
        # Test with different builtin tasks
        tasks_to_test = ["hellaswag", "arc_easy"]
        results = {}
        
        for task in tasks_to_test:
            logger.info(f"Testing builtin task: {task}")
            
            # Configure test
            config = {
                "tasks": [task],
                "limit": 3,  # Small sample for example
                "timeout": 120,
                "verbose": True
            }
            
            start_time = time.time()
            test_result = validator.test_builtin_tasks(task_count=1, config=config)
            execution_time = time.time() - start_time
            
            results[task] = {
                "success": len([r for r in test_result.test_results if r.status.value == "passed"]) > 0,
                "execution_time": execution_time,
                "test_count": len(test_result.test_results),
                "passed_tests": len([r for r in test_result.test_results if r.status.value == "passed"]),
                "failed_tests": len([r for r in test_result.test_results if r.status.value == "failed"])
            }
            
            logger.info(f"  Task {task} results:")
            logger.info(f"    Success: {results[task]['success']}")
            logger.info(f"    Execution time: {results[task]['execution_time']:.2f}s")
            logger.info(f"    Tests: {results[task]['passed_tests']}/{results[task]['test_count']} passed")
        
        # Summary
        total_success = sum(1 for r in results.values() if r["success"])
        logger.info(f"Builtin task testing summary: {total_success}/{len(tasks_to_test)} tasks successful")
        
        return {
            "success": total_success == len(tasks_to_test),
            "task_results": results,
            "total_tasks": len(tasks_to_test),
            "successful_tasks": total_success
        }
        
    except Exception as e:
        logger.error(f"Builtin task testing failed: {e}")
        return {"success": False, "error": str(e)}


def example_3_custom_task_testing(logger: logging.Logger) -> Dict[str, Any]:
    """Example 3: Test custom tasks with lm_eval adapter."""
    logger.info("=== Example 3: Custom Task Testing ===")
    
    try:
        validator = LMEvalAdapterValidator()
        
        # Check for custom task directory
        custom_task_dir = Path("lm_eval/tasks")
        if not custom_task_dir.exists():
            logger.warning(f"Custom task directory not found: {custom_task_dir}")
            return {
                "success": False,
                "error": "Custom task directory not found",
                "directory": str(custom_task_dir)
            }
        
        logger.info(f"Testing custom tasks from: {custom_task_dir}")
        
        # Test custom tasks
        test_result = validator.test_custom_tasks(custom_task_dir)
        
        # Analyze results
        total_tests = len(test_result.test_results)
        passed_tests = len([r for r in test_result.test_results if r.status.value == "passed"])
        failed_tests = len([r for r in test_result.test_results if r.status.value == "failed"])
        
        logger.info(f"Custom task testing results:")
        logger.info(f"  Total tests: {total_tests}")
        logger.info(f"  Passed: {passed_tests}")
        logger.info(f"  Failed: {failed_tests}")
        logger.info(f"  Success rate: {passed_tests/total_tests*100:.1f}%" if total_tests > 0 else "  No tests run")
        
        # Show individual test results
        for test_result_item in test_result.test_results[:5]:  # Show first 5
            status_symbol = "✓" if test_result_item.status.value == "passed" else "✗"
            logger.info(f"  {status_symbol} {test_result_item.name}: {test_result_item.execution_time:.2f}s")
        
        if len(test_result.test_results) > 5:
            logger.info(f"  ... and {len(test_result.test_results) - 5} more tests")
        
        return {
            "success": passed_tests > 0,
            "total_tests": total_tests,
            "passed_tests": passed_tests,
            "failed_tests": failed_tests,
            "success_rate": passed_tests/total_tests if total_tests > 0 else 0.0,
            "custom_task_dir": str(custom_task_dir)
        }
        
    except Exception as e:
        logger.error(f"Custom task testing failed: {e}")
        return {"success": False, "error": str(e)}


def example_4_performance_benchmarking(logger: logging.Logger) -> Dict[str, Any]:
    """Example 4: Performance benchmarking of lm_eval adapter."""
    logger.info("=== Example 4: Performance Benchmarking ===")
    
    try:
        validator = LMEvalAdapterValidator()
        metrics_collector = MetricsCollector()
        
        # Start metrics collection
        metrics_collector.start_collection()
        
        # Benchmark configuration
        benchmark_config = {
            "tasks": ["hellaswag"],
            "limit": 10,  # Moderate sample size for benchmarking
            "timeout": 300,
            "verbose": False  # Reduce output for cleaner benchmark
        }
        
        logger.info("Starting performance benchmark...")
        logger.info(f"Configuration: {benchmark_config}")
        
        # Run benchmark
        start_time = time.time()
        test_result = validator.test_builtin_tasks(task_count=1, config=benchmark_config)
        end_time = time.time()
        
        # Stop metrics collection
        metrics = metrics_collector.stop_collection()
        
        # Calculate performance metrics
        total_time = end_time - start_time
        successful_tests = len([r for r in test_result.test_results if r.status.value == "passed"])
        
        logger.info("=== Performance Benchmark Results ===")
        logger.info(f"Total execution time: {total_time:.2f}s")
        logger.info(f"Successful tests: {successful_tests}")
        logger.info(f"Average time per test: {total_time/successful_tests:.2f}s" if successful_tests > 0 else "N/A")
        
        # System metrics
        if metrics:
            logger.info("System resource usage:")
            if "peak_memory_mb" in metrics:
                logger.info(f"  Peak memory: {metrics['peak_memory_mb']:.1f} MB")
            if "avg_cpu_percent" in metrics:
                logger.info(f"  Average CPU: {metrics['avg_cpu_percent']:.1f}%")
            if "total_api_calls" in metrics:
                logger.info(f"  API calls: {metrics['total_api_calls']}")
        
        # Performance analysis
        performance_score = 0.0
        if successful_tests > 0 and total_time > 0:
            # Simple performance score: tests per second
            performance_score = successful_tests / total_time
        
        logger.info(f"Performance score: {performance_score:.2f} tests/second")
        
        return {
            "success": successful_tests > 0,
            "total_time": total_time,
            "successful_tests": successful_tests,
            "performance_score": performance_score,
            "system_metrics": metrics,
            "benchmark_config": benchmark_config
        }
        
    except Exception as e:
        logger.error(f"Performance benchmarking failed: {e}")
        return {"success": False, "error": str(e)}


def example_5_real_execution_validation(logger: logging.Logger) -> Dict[str, Any]:
    """Example 5: Validate real execution (no mocks) with lm_eval adapter."""
    logger.info("=== Example 5: Real Execution Validation ===")
    
    try:
        validator = LMEvalAdapterValidator()
        real_validator = RealExecutionValidator()
        
        # Configure real execution validation
        real_validator.configure_validation(
            mock_detection=True,
            resource_tracking=True,
            api_call_tracking=True
        )
        
        # Start tracking
        real_validator.start_tracking()
        
        logger.info("Running test with real execution validation...")
        
        # Run test
        config = {
            "tasks": ["hellaswag"],
            "limit": 2,  # Small sample for validation
            "timeout": 120,
            "verbose": True
        }
        
        test_result = validator.test_builtin_tasks(task_count=1, config=config)
        
        # Create test configuration for validation
        test_config = TestConfiguration(
            test_id="lm_eval_real_execution",
            test_type=TestType.ADAPTER,
            name="LM-Eval Real Execution Test",
            description="Validate real execution with lm_eval adapter",
            real_execution_required=True
        )
        
        # Validate real execution for each test result
        validation_results = []
        for test_res in test_result.test_results:
            is_real = real_validator.validate_real_execution(test_res, test_config)
            validation_results.append(is_real)
        
        real_validator.stop_tracking()
        
        # Get validation report
        validation_report = real_validator.get_validation_report()
        
        logger.info("=== Real Execution Validation Results ===")
        logger.info(f"Tests validated as real: {sum(validation_results)}/{len(validation_results)}")
        logger.info(f"Mock objects detected: {validation_report['mock_objects_found']}")
        logger.info(f"API calls recorded: {validation_report['api_calls_recorded']}")
        logger.info(f"Resource snapshots: {validation_report['resource_snapshots']}")
        
        if validation_report["memory_growth"] is not None:
            logger.info(f"Memory growth: {validation_report['memory_growth']} bytes")
        
        if validation_report["errors"]:
            logger.warning("Validation errors:")
            for error in validation_report["errors"]:
                logger.warning(f"  - {error}")
        
        all_real = all(validation_results)
        logger.info(f"Overall real execution validation: {'PASSED' if all_real else 'FAILED'}")
        
        return {
            "success": all_real,
            "validated_tests": len(validation_results),
            "real_execution_tests": sum(validation_results),
            "validation_report": validation_report,
            "all_tests_real": all_real
        }
        
    except Exception as e:
        logger.error(f"Real execution validation failed: {e}")
        return {"success": False, "error": str(e)}


def example_6_error_handling_and_recovery(logger: logging.Logger) -> Dict[str, Any]:
    """Example 6: Test error handling and recovery scenarios."""
    logger.info("=== Example 6: Error Handling and Recovery ===")
    
    try:
        validator = LMEvalAdapterValidator()
        error_scenarios = []
        
        # Scenario 1: Invalid task
        logger.info("Testing invalid task handling...")
        try:
            config = {"tasks": ["nonexistent_task"], "limit": 1, "timeout": 30}
            result = validator.test_builtin_tasks(task_count=1, config=config)
            error_scenarios.append({
                "scenario": "invalid_task",
                "handled_gracefully": not any(r.status.value == "passed" for r in result.test_results),
                "error_message": "Task should fail gracefully"
            })
        except Exception as e:
            error_scenarios.append({
                "scenario": "invalid_task",
                "handled_gracefully": True,
                "error_message": str(e)
            })
        
        # Scenario 2: Timeout handling
        logger.info("Testing timeout handling...")
        try:
            config = {"tasks": ["hellaswag"], "limit": 1, "timeout": 1}  # Very short timeout
            result = validator.test_builtin_tasks(task_count=1, config=config)
            error_scenarios.append({
                "scenario": "timeout",
                "handled_gracefully": True,
                "error_message": "Timeout handled without crash"
            })
        except Exception as e:
            error_scenarios.append({
                "scenario": "timeout",
                "handled_gracefully": True,
                "error_message": str(e)
            })
        
        # Scenario 3: Invalid configuration
        logger.info("Testing invalid configuration handling...")
        try:
            config = {"tasks": [], "limit": -1, "timeout": 0}  # Invalid config
            result = validator.test_builtin_tasks(task_count=1, config=config)
            error_scenarios.append({
                "scenario": "invalid_config",
                "handled_gracefully": not any(r.status.value == "passed" for r in result.test_results),
                "error_message": "Invalid config should be rejected"
            })
        except Exception as e:
            error_scenarios.append({
                "scenario": "invalid_config",
                "handled_gracefully": True,
                "error_message": str(e)
            })
        
        # Summary
        handled_gracefully = sum(1 for s in error_scenarios if s["handled_gracefully"])
        total_scenarios = len(error_scenarios)
        
        logger.info("=== Error Handling Summary ===")
        logger.info(f"Error scenarios tested: {total_scenarios}")
        logger.info(f"Handled gracefully: {handled_gracefully}")
        
        for scenario in error_scenarios:
            status = "✓" if scenario["handled_gracefully"] else "✗"
            logger.info(f"  {status} {scenario['scenario']}: {scenario['error_message']}")
        
        return {
            "success": handled_gracefully == total_scenarios,
            "total_scenarios": total_scenarios,
            "handled_gracefully": handled_gracefully,
            "scenarios": error_scenarios
        }
        
    except Exception as e:
        logger.error(f"Error handling testing failed: {e}")
        return {"success": False, "error": str(e)}


def main():
    """Main function to run all lm_eval adapter examples."""
    logger = setup_logging()
    
    logger.info("Starting LM-Eval Adapter Examples")
    logger.info("=" * 50)
    
    # Results storage
    results = {}
    
    try:
        # Run all examples
        examples = [
            ("Basic Validation", example_1_basic_validation),
            ("Builtin Task Testing", example_2_builtin_task_testing),
            ("Custom Task Testing", example_3_custom_task_testing),
            ("Performance Benchmarking", example_4_performance_benchmarking),
            ("Real Execution Validation", example_5_real_execution_validation),
            ("Error Handling", example_6_error_handling_and_recovery)
        ]
        
        for example_name, example_func in examples:
            logger.info(f"\nRunning {example_name}...")
            try:
                result = example_func(logger)
                results[example_name] = result
                status = "✓ PASSED" if result.get("success", False) else "✗ FAILED"
                logger.info(f"{example_name}: {status}")
            except Exception as e:
                logger.error(f"{example_name} failed with exception: {e}")
                results[example_name] = {"success": False, "error": str(e)}
        
        # Overall summary
        logger.info("\n" + "=" * 50)
        logger.info("LM-Eval Adapter Examples Summary")
        logger.info("=" * 50)
        
        total_examples = len(examples)
        successful_examples = sum(1 for r in results.values() if r.get("success", False))
        
        for example_name, result in results.items():
            status = "✓ PASSED" if result.get("success", False) else "✗ FAILED"
            logger.info(f"  {status} {example_name}")
            if not result.get("success", False) and "error" in result:
                logger.info(f"    Error: {result['error']}")
        
        logger.info(f"\nOverall: {successful_examples}/{total_examples} examples passed")
        
        # Save results to file
        results_file = Path("lm_eval_examples_results.json")
        with open(results_file, 'w') as f:
            json.dump(results, f, indent=2, default=str)
        logger.info(f"Detailed results saved to: {results_file}")
        
        if successful_examples == total_examples:
            logger.info("🎉 All LM-Eval adapter examples completed successfully!")
            sys.exit(0)
        else:
            logger.warning("⚠️ Some examples failed. Check the logs for details.")
            sys.exit(1)
    
    except KeyboardInterrupt:
        logger.info("Examples interrupted by user")
        sys.exit(1)
    except Exception as e:
        logger.error(f"Examples failed: {e}")
        sys.exit(1)


if __name__ == "__main__":
    main()