#!/usr/bin/env python3
"""
Comprehensive demonstration of EvaluationEngineV1_0 testing framework.

This script demonstrates all major features of the testing framework:
1. CLI testing with builtin and custom tasks
2. API testing with curl generation and programmatic calls
3. Adapter validation for lm_eval and swe_bench
4. Real execution validation
5. Complete pipeline testing
6. Report generation

Run this script to see the testing framework in action.
"""

import asyncio
import logging
import sys
import time
from pathlib import Path
from typing import Dict, Any

# Import testing framework components
from .core.test_orchestrator import TestOrchestrator
from .core.config_manager import ConfigManager
from .core.metrics_collector import MetricsCollector
from .cli.cli_test_runner import CLITestRunner
from .api.api_test_server import APITestServer
from .api.curl_test_generator import CurlTestGenerator
from .api.api_test_client import APITestClient
from .models.test_models import TestConfiguration, TestType, AdapterType


def setup_logging():
    """Setup logging for the demonstration."""
    logging.basicConfig(
        level=logging.INFO,
        format='%(asctime)s - %(name)s - %(levelname)s - %(message)s',
        handlers=[
            logging.StreamHandler(sys.stdout),
            logging.FileHandler('demo_testing.log')
        ]
    )
    return logging.getLogger(__name__)


def demonstrate_cli_testing(logger):
    """Demonstrate CLI testing capabilities."""
    logger.info("=== CLI Testing Demonstration ===")
    
    try:
        # Create CLI test runner
        cli_runner = CLITestRunner()
        
        # Test 1: Builtin tasks
        logger.info("Testing builtin tasks...")
        builtin_config = {
            "timeout": 60,
            "verbose": True,
            "output_format": "json",
            "limit": 5  # Limit to 5 samples for demo
        }
        
        result = cli_runner.run_builtin_tasks(["hellaswag"], builtin_config)
        logger.info(f"Builtin task test result: {result['success']}")
        
        if result.get("metrics"):
            logger.info(f"Metrics: {result['metrics']}")
        
        # Test 2: Custom tasks (if directory exists)
        custom_task_dir = Path("lm_eval/tasks")
        if custom_task_dir.exists():
            logger.info("Testing custom tasks...")
            custom_config = {
                "timeout": 120,
                "verbose": True,
                "output_format": "json"
            }
            
            result = cli_runner.run_custom_tasks(custom_task_dir, custom_config)
            logger.info(f"Custom task test result: {result['success']}")
        else:
            logger.info("Custom task directory not found, skipping custom task test")
        
        # Test 3: Adapter testing
        logger.info("Testing lm_eval adapter...")
        adapter_config = {
            "timeout": 180,
            "verbose": True,
            "output_format": "json"
        }
        
        result = cli_runner.run_adapter_tests("lm_eval", adapter_config)
        logger.info(f"Adapter test result: {result['success']}")
        
        logger.info("CLI testing demonstration completed successfully")
        
    except Exception as e:
        logger.error(f"CLI testing demonstration failed: {e}")


def demonstrate_api_testing(logger):
    """Demonstrate API testing capabilities."""
    logger.info("=== API Testing Demonstration ===")
    
    api_server = None
    
    try:
        # Start API test server
        logger.info("Starting API test server...")
        api_server = APITestServer(host="localhost", port=8001)
        api_server.start_server()
        
        if not api_server.is_running():
            raise Exception("Failed to start API server")
        
        logger.info("API server started successfully")
        
        # Generate curl commands
        logger.info("Generating curl test commands...")
        curl_generator = CurlTestGenerator(base_url="http://localhost:8001")
        
        # Generate individual commands
        health_cmd = curl_generator.generate_health_check()
        logger.info(f"Health check command: {health_cmd}")
        
        eval_config = {
            "model_id": "demo_model",
            "tasks": ["hellaswag", "arc_easy"],
            "evaluation_config": {"limit": 5}
        }
        
        create_cmd = curl_generator.generate_evaluation_request(eval_config)
        logger.info(f"Create evaluation command: {create_cmd}")
        
        # Generate comprehensive test script
        script_content = curl_generator.generate_comprehensive_test_script(eval_config)
        script_path = Path("demo_api_test.sh")
        curl_generator.save_test_script(script_content, script_path)
        logger.info(f"Comprehensive test script saved to: {script_path}")
        
        # Test with API client
        logger.info("Testing with API client...")
        api_client = APITestClient(base_url="http://localhost:8001")
        
        # Health check
        success, result = api_client.test_health_check()
        logger.info(f"API health check: {success}")
        
        # List tasks
        success, result = api_client.test_list_tasks()
        logger.info(f"List tasks: {success}")
        if success and result.get("response_data"):
            tasks = result["response_data"].get("tasks", [])
            logger.info(f"Available tasks: {len(tasks)}")
        
        # Create evaluation
        success, result = api_client.test_create_evaluation(
            "demo_model", ["hellaswag"], {"limit": 3}
        )
        logger.info(f"Create evaluation: {success}")
        
        if success and result.get("response_data"):
            evaluation_id = result["response_data"].get("evaluation_id")
            if evaluation_id:
                logger.info(f"Created evaluation: {evaluation_id}")
                
                # Wait for completion (with timeout)
                logger.info("Waiting for evaluation completion...")
                success, completion_result = api_client.wait_for_evaluation_completion(
                    evaluation_id, max_wait_time=60, poll_interval=2
                )
                
                if success:
                    logger.info("Evaluation completed successfully")
                    
                    # Get results
                    success, results = api_client.test_get_evaluation_results(evaluation_id)
                    if success:
                        logger.info("Retrieved evaluation results")
                    else:
                        logger.warning("Failed to retrieve results")
                else:
                    logger.warning("Evaluation did not complete in time")
        
        api_client.close()
        logger.info("API testing demonstration completed successfully")
        
    except Exception as e:
        logger.error(f"API testing demonstration failed: {e}")
    
    finally:
        if api_server and api_server.is_running():
            logger.info("Stopping API server...")
            api_server.stop_server()


async def demonstrate_async_api_testing(logger):
    """Demonstrate asynchronous API testing."""
    logger.info("=== Async API Testing Demonstration ===")
    
    api_server = None
    
    try:
        # Start API server
        logger.info("Starting API server for async testing...")
        api_server = APITestServer(host="localhost", port=8002)
        api_server.start_server()
        
        if not api_server.is_running():
            raise Exception("Failed to start API server")
        
        # Import async manager
        from .api.async_evaluation_manager import AsyncEvaluationManager
        
        # Create async manager
        async_manager = AsyncEvaluationManager(
            base_url="http://localhost:8002",
            max_concurrent=3,
            timeout=30
        )
        
        # Test concurrent evaluations
        logger.info("Testing concurrent evaluations...")
        evaluation_configs = [
            {
                "model_id": f"concurrent_model_{i}",
                "tasks": ["hellaswag"],
                "config": {"limit": 2, "concurrent_id": i}
            }
            for i in range(3)
        ]
        
        concurrent_results = await async_manager.run_concurrent_evaluations(evaluation_configs)
        
        logger.info(f"Concurrent evaluations completed:")
        logger.info(f"  Total: {concurrent_results['total_evaluations']}")
        logger.info(f"  Successful creations: {concurrent_results['successful_creations']}")
        logger.info(f"  Successful completions: {concurrent_results['successful_completions']}")
        logger.info(f"  Total time: {concurrent_results['total_time']:.2f}s")
        
        if concurrent_results['errors']:
            logger.warning(f"Errors encountered: {len(concurrent_results['errors'])}")
        
        logger.info("Async API testing demonstration completed successfully")
        
    except Exception as e:
        logger.error(f"Async API testing demonstration failed: {e}")
    
    finally:
        if api_server and api_server.is_running():
            logger.info("Stopping API server...")
            api_server.stop_server()


def demonstrate_orchestrator_testing(logger):
    """Demonstrate test orchestrator capabilities."""
    logger.info("=== Test Orchestrator Demonstration ===")
    
    try:
        # Create orchestrator
        config_manager = ConfigManager()
        metrics_collector = MetricsCollector()
        orchestrator = TestOrchestrator(config_manager, metrics_collector)
        
        # Create test suite configuration
        suite_config = {
            "suite_id": "demo_suite",
            "suite_name": "Demonstration Test Suite",
            "cli_tests": {
                "tasks": ["hellaswag"],
                "execution_params": {"timeout": 60, "verbose": True},
                "timeout": 60
            },
            "api_tests": {
                "endpoints": ["/health", "/api/v1/tasks"],
                "execution_params": {"timeout": 30},
                "timeout": 30
            },
            "adapter_tests": {
                "adapters": ["lm_eval"],
                "execution_params": {"timeout": 120},
                "timeout": 120
            },
            "parallel": False,
            "max_workers": 2
        }
        
        # Execute test suite
        logger.info("Executing test suite...")
        suite_results = orchestrator.execute_test_suite(suite_config)
        
        # Display results
        logger.info(f"Test suite completed:")
        logger.info(f"  Suite ID: {suite_results.suite_id}")
        logger.info(f"  Total tests: {suite_results.total_tests}")
        logger.info(f"  Passed: {suite_results.passed_tests}")
        logger.info(f"  Failed: {suite_results.failed_tests}")
        logger.info(f"  Success rate: {suite_results.success_rate:.1%}")
        logger.info(f"  Total time: {suite_results.total_execution_time:.2f}s")
        
        # Display individual test results
        for result in suite_results.test_results:
            status_symbol = "✓" if result.status.value == "passed" else "✗"
            logger.info(f"  {status_symbol} {result.name}: {result.status.value}")
        
        # Display metrics if available
        if suite_results.execution_metrics:
            metrics = suite_results.execution_metrics
            logger.info("Execution metrics:")
            if metrics.memory_usage:
                peak_memory = metrics.memory_usage.get("peak_rss", 0) / 1024 / 1024
                logger.info(f"  Peak memory: {peak_memory:.1f} MB")
            if metrics.resource_consumption:
                avg_cpu = metrics.resource_consumption.get("avg_cpu_percent", 0)
                logger.info(f"  Average CPU: {avg_cpu:.1f}%")
        
        logger.info("Test orchestrator demonstration completed successfully")
        
    except Exception as e:
        logger.error(f"Test orchestrator demonstration failed: {e}")


def demonstrate_real_execution_validation(logger):
    """Demonstrate real execution validation."""
    logger.info("=== Real Execution Validation Demonstration ===")
    
    try:
        from .core.real_execution_validator import RealExecutionValidator
        from .models.test_models import TestResult, TestStatus
        
        # Create validator
        validator = RealExecutionValidator()
        
        # Configure validation
        validator.configure_validation(
            mock_detection=True,
            resource_tracking=True,
            api_call_tracking=True
        )
        
        # Start tracking
        validator.start_tracking()
        
        # Simulate some real execution
        logger.info("Simulating real execution...")
        time.sleep(1)  # Simulate processing time
        
        # Record some metrics
        validator.record_resource_snapshot()
        validator.record_api_call("/test/endpoint", "GET", {"result": "success"})
        
        # Create mock test result
        test_result = TestResult(
            test_id="validation_demo",
            test_type=TestType.UNIT,
            name="Validation Demo Test",
            status=TestStatus.PASSED,
            execution_time=1.0,
            real_execution_validated=False,
            logs=["Test started", "Processing data", "Test completed"],
            metrics={"accuracy": 0.85, "tokens": 100}
        )
        
        # Create mock test config
        test_config = TestConfiguration(
            test_id="validation_demo",
            test_type=TestType.UNIT,
            name="Validation Demo Test",
            description="Demo test for validation",
            real_execution_required=True
        )
        
        # Validate real execution
        is_valid = validator.validate_real_execution(test_result, test_config)
        logger.info(f"Real execution validation result: {is_valid}")
        
        # Get validation report
        report = validator.get_validation_report()
        logger.info("Validation report:")
        logger.info(f"  Mock objects found: {report['mock_objects_found']}")
        logger.info(f"  API calls recorded: {report['api_calls_recorded']}")
        logger.info(f"  Resource snapshots: {report['resource_snapshots']}")
        
        if report['memory_growth'] is not None:
            logger.info(f"  Memory growth: {report['memory_growth']} bytes")
        
        validator.stop_tracking()
        logger.info("Real execution validation demonstration completed successfully")
        
    except Exception as e:
        logger.error(f"Real execution validation demonstration failed: {e}")


def demonstrate_report_generation(logger):
    """Demonstrate report generation capabilities."""
    logger.info("=== Report Generation Demonstration ===")
    
    try:
        from .cli.cli_result_formatter import CLIResultFormatter
        from .models.test_models import TestSuiteResults, TestResult, TestStatus
        
        # Create formatter
        formatter = CLIResultFormatter()
        
        # Create mock test suite results
        test_results = [
            TestResult(
                test_id="demo_test_1",
                test_type=TestType.CLI,
                name="Demo CLI Test 1",
                status=TestStatus.PASSED,
                execution_time=15.5,
                real_execution_validated=True,
                metrics={"accuracy": 0.85, "tokens": 150}
            ),
            TestResult(
                test_id="demo_test_2",
                test_type=TestType.API,
                name="Demo API Test 2",
                status=TestStatus.PASSED,
                execution_time=8.2,
                real_execution_validated=True,
                metrics={"response_time": 0.5, "status_code": 200}
            ),
            TestResult(
                test_id="demo_test_3",
                test_type=TestType.ADAPTER,
                name="Demo Adapter Test 3",
                status=TestStatus.FAILED,
                execution_time=25.1,
                real_execution_validated=False,
                error_details="Adapter initialization failed"
            )
        ]
        
        suite_results = TestSuiteResults(
            suite_id="demo_suite_report",
            suite_name="Demo Report Suite",
            total_tests=3,
            passed_tests=2,
            failed_tests=1,
            skipped_tests=0,
            error_tests=0,
            total_execution_time=48.8,
            test_results=test_results
        )
        
        # Generate summary report
        summary_report = formatter.create_summary_report(suite_results)
        logger.info("Generated summary report:")
        print("\n" + "="*60)
        print(summary_report)
        print("="*60 + "\n")
        
        # Save reports in different formats
        reports_dir = Path("demo_reports")
        reports_dir.mkdir(exist_ok=True)
        
        # JSON format
        formatter.save_results(suite_results, reports_dir / "demo_results.json", "json")
        logger.info(f"JSON report saved to: {reports_dir / 'demo_results.json'}")
        
        # YAML format
        formatter.save_results(suite_results, reports_dir / "demo_results.yaml", "yaml")
        logger.info(f"YAML report saved to: {reports_dir / 'demo_results.yaml'}")
        
        # CSV format
        formatter.save_results(suite_results, reports_dir / "demo_results.csv", "csv")
        logger.info(f"CSV report saved to: {reports_dir / 'demo_results.csv'}")
        
        logger.info("Report generation demonstration completed successfully")
        
    except Exception as e:
        logger.error(f"Report generation demonstration failed: {e}")


def main():
    """Main demonstration function."""
    logger = setup_logging()
    
    logger.info("Starting EvaluationEngineV1_0 Testing Framework Demonstration")
    logger.info("=" * 70)
    
    try:
        # Demonstrate each component
        demonstrate_cli_testing(logger)
        print()
        
        demonstrate_api_testing(logger)
        print()
        
        # Run async demo
        asyncio.run(demonstrate_async_api_testing(logger))
        print()
        
        demonstrate_orchestrator_testing(logger)
        print()
        
        demonstrate_real_execution_validation(logger)
        print()
        
        demonstrate_report_generation(logger)
        print()
        
        logger.info("=" * 70)
        logger.info("All demonstrations completed successfully!")
        logger.info("Check the generated files:")
        logger.info("  - demo_testing.log: Detailed execution log")
        logger.info("  - demo_api_test.sh: Generated API test script")
        logger.info("  - demo_reports/: Generated test reports")
        
    except KeyboardInterrupt:
        logger.info("Demonstration interrupted by user")
    except Exception as e:
        logger.error(f"Demonstration failed: {e}")
        sys.exit(1)


if __name__ == "__main__":
    main()