"""
Central test orchestrator for coordinating all testing activities.
"""

import asyncio
import logging
import threading
from typing import Dict, List, Optional, Any, Callable
from datetime import datetime
from pathlib import Path
from concurrent.futures import ThreadPoolExecutor, as_completed

from models.test_models import (
    TestConfiguration, TestResult, TestSuiteResults, TestStatus, 
    TestType, ExecutionMetrics, ValidationResult
)
from .config_manager import ConfigManager
from .metrics_collector import MetricsCollector
from .real_execution_validator import RealExecutionValidator
from .pipeline_validator import PipelineValidator
from .error_handler import ErrorHandler, TestFrameworkError, ExecutionError

# Import security components
try:
    from ..security.security_manager import SecurityManager, SecurityConfig, SecurityViolation
    SECURITY_AVAILABLE = True
except ImportError:
    SECURITY_AVAILABLE = False
    SecurityManager = None
    SecurityConfig = None
    SecurityViolation = Exception


class TestOrchestrator:
    """Central orchestrator for coordinating all testing activities."""
    
    def __init__(self, config_manager: Optional[ConfigManager] = None,
                 metrics_collector: Optional[MetricsCollector] = None,
                 security_manager: Optional[SecurityManager] = None):
        self.config_manager = config_manager or ConfigManager()
        self.metrics_collector = metrics_collector or MetricsCollector()
        self.real_execution_validator = RealExecutionValidator()
        self.pipeline_validator = PipelineValidator()
        self.error_handler = ErrorHandler("TestOrchestrator")
        
        # Initialize security manager if available
        if SECURITY_AVAILABLE and security_manager is not None:
            self.security_manager = security_manager
        elif SECURITY_AVAILABLE:
            # Create default security configuration for testing
            security_config = SecurityConfig(
                enable_sandbox=True,
                enable_resource_limits=True,
                enable_command_validation=True,
                enable_file_security=True,
                max_execution_time=600,
                max_memory_mb=2048,
                allow_network=False
            )
            self.security_manager = SecurityManager(security_config)
        else:
            self.security_manager = None
        
        self.logger = logging.getLogger(f"{__name__}.TestOrchestrator")
        
        # Test execution state
        self._active_tests: Dict[str, TestResult] = {}
        self._test_queue: List[TestConfiguration] = []
        self._execution_lock = threading.Lock()
        self._shutdown_event = threading.Event()
        
        # Callbacks
        self._test_started_callbacks: List[Callable[[TestResult], None]] = []
        self._test_completed_callbacks: List[Callable[[TestResult], None]] = []
        self._suite_completed_callbacks: List[Callable[[TestSuiteResults], None]] = []
    
    def execute_test_suite(self, suite_config: Dict[str, Any]) -> TestSuiteResults:
        """Execute a complete test suite."""
        suite_id = suite_config.get("suite_id", f"suite_{datetime.now().strftime('%Y%m%d_%H%M%S')}")
        suite_name = suite_config.get("suite_name", "Test Suite")
        
        self.logger.info(f"Starting test suite execution: {suite_name} ({suite_id})")
        
        # Start metrics collection
        self.metrics_collector.start_collection()
        
        try:
            # Create test suite results
            suite_results = TestSuiteResults(
                suite_id=suite_id,
                suite_name=suite_name,
                total_tests=0,
                passed_tests=0,
                failed_tests=0,
                skipped_tests=0,
                error_tests=0,
                total_execution_time=0.0
            )
            
            # Generate test configurations from suite config
            test_configs = self._generate_test_configurations(suite_config)
            suite_results.total_tests = len(test_configs)
            
            # Execute tests
            if suite_config.get("parallel", False):
                test_results = self._execute_tests_parallel(test_configs, suite_config)
            else:
                test_results = self._execute_tests_sequential(test_configs, suite_config)
            
            # Process results
            for result in test_results:
                suite_results.test_results.append(result)
                
                if result.status == TestStatus.PASSED:
                    suite_results.passed_tests += 1
                elif result.status == TestStatus.FAILED:
                    suite_results.failed_tests += 1
                elif result.status == TestStatus.SKIPPED:
                    suite_results.skipped_tests += 1
                elif result.status == TestStatus.ERROR:
                    suite_results.error_tests += 1
                
                suite_results.total_execution_time += result.execution_time
            
            # Collect final metrics
            suite_results.execution_metrics = self.metrics_collector.get_execution_metrics()
            suite_results.completed_at = datetime.now()
            
            # Generate summary report
            suite_results.summary_report = self._generate_suite_summary(suite_results)
            
            # Notify callbacks
            for callback in self._suite_completed_callbacks:
                try:
                    callback(suite_results)
                except Exception as e:
                    self.logger.warning(f"Suite completion callback failed: {e}")
            
            self.logger.info(f"Test suite completed: {suite_results.passed_tests}/{suite_results.total_tests} passed")
            return suite_results
            
        except Exception as e:
            error = self.error_handler.handle_exception(e, {"suite_id": suite_id})
            raise error
        finally:
            self.metrics_collector.stop_collection()
    
    def execute_single_test(self, test_config: TestConfiguration) -> TestResult:
        """Execute a single test."""
        test_result = TestResult(
            test_id=test_config.test_id,
            test_type=test_config.test_type,
            name=test_config.name,
            status=TestStatus.PENDING,
            execution_time=0.0,
            real_execution_validated=False,
            started_at=datetime.now()
        )
        
        # Add to active tests
        with self._execution_lock:
            self._active_tests[test_config.test_id] = test_result
        
        # Notify test started
        for callback in self._test_started_callbacks:
            try:
                callback(test_result)
            except Exception as e:
                self.logger.warning(f"Test started callback failed: {e}")
        
        try:
            self.logger.info(f"Starting test: {test_config.name} ({test_config.test_id})")
            
            # Update status
            test_result.status = TestStatus.RUNNING
            
            # Start timing
            with self.metrics_collector.time_operation(f"test_{test_config.test_id}"):
                # Execute test based on type
                if test_config.test_type == TestType.CLI:
                    self._execute_cli_test(test_config, test_result)
                elif test_config.test_type == TestType.API:
                    self._execute_api_test(test_config, test_result)
                elif test_config.test_type == TestType.ADAPTER:
                    self._execute_adapter_test(test_config, test_result)
                elif test_config.test_type == TestType.PIPELINE:
                    self._execute_pipeline_test(test_config, test_result)
                else:
                    raise ExecutionError(f"Unsupported test type: {test_config.test_type}")
                
                # Validate real execution if required
                if test_config.real_execution_required:
                    test_result.real_execution_validated = self.real_execution_validator.validate_real_execution(
                        test_result, test_config
                    )
                else:
                    test_result.real_execution_validated = True
            
            # Update final status
            if test_result.status == TestStatus.RUNNING:
                test_result.status = TestStatus.PASSED
            
            # Record metrics
            self.metrics_collector.record_test_result(test_result)
            
            self.logger.info(f"Test completed: {test_config.name} - {test_result.status.value}")
            
        except Exception as e:
            test_result.status = TestStatus.ERROR
            test_result.error_details = str(e)
            self.error_handler.handle_exception(e, {"test_id": test_config.test_id})
            self.logger.error(f"Test failed: {test_config.name} - {e}")
        
        finally:
            # Update completion time and execution time
            test_result.completed_at = datetime.now()
            if test_result.started_at:
                test_result.execution_time = (test_result.completed_at - test_result.started_at).total_seconds()
            
            # Remove from active tests
            with self._execution_lock:
                self._active_tests.pop(test_config.test_id, None)
            
            # Notify test completed
            for callback in self._test_completed_callbacks:
                try:
                    callback(test_result)
                except Exception as e:
                    self.logger.warning(f"Test completed callback failed: {e}")
        
        return test_result
    
    def validate_real_execution(self, test_result: TestResult, 
                               test_config: TestConfiguration) -> bool:
        """Validate that test used real execution without mocks."""
        return self.real_execution_validator.validate_real_execution(test_result, test_config)
    
    def collect_metrics(self, execution_context: Dict[str, Any]) -> ExecutionMetrics:
        """Collect execution metrics from current context."""
        return self.metrics_collector.get_execution_metrics()
    
    def get_active_tests(self) -> Dict[str, TestResult]:
        """Get currently active tests."""
        with self._execution_lock:
            return self._active_tests.copy()
    
    def cancel_test(self, test_id: str) -> bool:
        """Cancel a running test."""
        with self._execution_lock:
            if test_id in self._active_tests:
                test_result = self._active_tests[test_id]
                test_result.status = TestStatus.SKIPPED
                test_result.error_details = "Test cancelled by user"
                self.logger.info(f"Test cancelled: {test_id}")
                return True
        return False
    
    def shutdown(self) -> None:
        """Shutdown the orchestrator and cancel all active tests."""
        self.logger.info("Shutting down test orchestrator")
        self._shutdown_event.set()
        
        # Cancel all active tests
        with self._execution_lock:
            for test_id in list(self._active_tests.keys()):
                self.cancel_test(test_id)
        
        # Stop metrics collection
        self.metrics_collector.stop_collection()
    
    def add_test_started_callback(self, callback: Callable[[TestResult], None]) -> None:
        """Add callback for test started events."""
        self._test_started_callbacks.append(callback)
    
    def add_test_completed_callback(self, callback: Callable[[TestResult], None]) -> None:
        """Add callback for test completed events."""
        self._test_completed_callbacks.append(callback)
    
    def add_suite_completed_callback(self, callback: Callable[[TestSuiteResults], None]) -> None:
        """Add callback for suite completed events."""
        self._suite_completed_callbacks.append(callback)
    
    def _generate_test_configurations(self, suite_config: Dict[str, Any]) -> List[TestConfiguration]:
        """Generate individual test configurations from suite configuration."""
        test_configs = []
        
        # CLI tests
        if "cli_tests" in suite_config:
            cli_config = suite_config["cli_tests"]
            for i, task in enumerate(cli_config.get("tasks", [])):
                test_configs.append(TestConfiguration(
                    test_id=f"cli_test_{i}_{task}",
                    test_type=TestType.CLI,
                    name=f"CLI Test: {task}",
                    description=f"CLI test for task {task}",
                    task_selection={"task": task},
                    execution_params=cli_config.get("execution_params", {}),
                    timeout=cli_config.get("timeout", 300)
                ))
        
        # API tests
        if "api_tests" in suite_config:
            api_config = suite_config["api_tests"]
            for i, endpoint in enumerate(api_config.get("endpoints", [])):
                test_configs.append(TestConfiguration(
                    test_id=f"api_test_{i}_{endpoint.replace('/', '_')}",
                    test_type=TestType.API,
                    name=f"API Test: {endpoint}",
                    description=f"API test for endpoint {endpoint}",
                    task_selection={"endpoint": endpoint},
                    execution_params=api_config.get("execution_params", {}),
                    timeout=api_config.get("timeout", 60)
                ))
        
        # Adapter tests
        if "adapter_tests" in suite_config:
            adapter_config = suite_config["adapter_tests"]
            for adapter_name in adapter_config.get("adapters", []):
                test_configs.append(TestConfiguration(
                    test_id=f"adapter_test_{adapter_name}",
                    test_type=TestType.ADAPTER,
                    name=f"Adapter Test: {adapter_name}",
                    description=f"Validation test for {adapter_name} adapter",
                    task_selection={"adapter": adapter_name},
                    execution_params=adapter_config.get("execution_params", {}),
                    timeout=adapter_config.get("timeout", 600)
                ))
        
        # Pipeline tests
        if "pipeline_tests" in suite_config:
            pipeline_config = suite_config["pipeline_tests"]
            test_configs.append(TestConfiguration(
                test_id="pipeline_test_full",
                test_type=TestType.PIPELINE,
                name="Full Pipeline Test",
                description="End-to-end pipeline validation test",
                task_selection=pipeline_config.get("task_selection", {}),
                execution_params=pipeline_config.get("execution_params", {}),
                timeout=pipeline_config.get("timeout", 1200)
            ))
        
        return test_configs
    
    def _execute_tests_sequential(self, test_configs: List[TestConfiguration], 
                                 suite_config: Dict[str, Any]) -> List[TestResult]:
        """Execute tests sequentially."""
        results = []
        
        for test_config in test_configs:
            if self._shutdown_event.is_set():
                break
            
            result = self.execute_single_test(test_config)
            results.append(result)
        
        return results
    
    def _execute_tests_parallel(self, test_configs: List[TestConfiguration], 
                               suite_config: Dict[str, Any]) -> List[TestResult]:
        """Execute tests in parallel."""
        max_workers = suite_config.get("max_workers", 4)
        results = []
        
        with ThreadPoolExecutor(max_workers=max_workers) as executor:
            # Submit all tests
            future_to_config = {
                executor.submit(self.execute_single_test, config): config 
                for config in test_configs
            }
            
            # Collect results as they complete
            for future in as_completed(future_to_config):
                if self._shutdown_event.is_set():
                    break
                
                try:
                    result = future.result()
                    results.append(result)
                except Exception as e:
                    config = future_to_config[future]
                    self.logger.error(f"Parallel test execution failed for {config.test_id}: {e}")
                    
                    # Create error result
                    error_result = TestResult(
                        test_id=config.test_id,
                        test_type=config.test_type,
                        name=config.name,
                        status=TestStatus.ERROR,
                        execution_time=0.0,
                        real_execution_validated=False,
                        error_details=str(e)
                    )
                    results.append(error_result)
        
        return results
    
    def _execute_cli_test(self, test_config: TestConfiguration, test_result: TestResult) -> None:
        """Execute a CLI test with security controls."""
        # Import here to avoid circular imports
        from cli.cli_test_runner import CLITestRunner
        
        # Execute with security context if available
        if self.security_manager:
            try:
                with self.security_manager.secure_execution_context(
                    context_id=f"cli_test_{test_config.test_id}"
                ) as sandbox:
                    cli_runner = CLITestRunner(security_manager=self.security_manager)
                    cli_result = cli_runner.run_test(test_config, sandbox=sandbox)
            except SecurityViolation as e:
                test_result.status = TestStatus.ERROR
                test_result.error_details = f"Security violation during CLI test: {e}"
                return
        else:
            cli_runner = CLITestRunner()
            cli_result = cli_runner.run_test(test_config)
        
        # Update test result with CLI-specific data
        test_result.metrics.update(cli_result.get("metrics", {}))
        test_result.artifacts.extend(cli_result.get("artifacts", []))
        test_result.logs.extend(cli_result.get("logs", []))
        
        if not cli_result.get("success", False):
            test_result.status = TestStatus.FAILED
            test_result.error_details = cli_result.get("error", "CLI test failed")
    
    def _execute_api_test(self, test_config: TestConfiguration, test_result: TestResult) -> None:
        """Execute an API test with security controls."""
        # Import here to avoid circular imports
        from api.api_test_client import APITestClient
        
        try:
            if self.security_manager:
                # Use security manager for API authentication and rate limiting
                api_client = APITestClient(security_manager=self.security_manager)
            else:
                api_client = APITestClient()
            
            api_result = api_client.run_test(test_config)
            
        except SecurityViolation as e:
            test_result.status = TestStatus.ERROR
            test_result.error_details = f"Security violation during API test: {e}"
            return
        
        # Update test result with API-specific data
        test_result.metrics.update(api_result.get("metrics", {}))
        test_result.artifacts.extend(api_result.get("artifacts", []))
        test_result.logs.extend(api_result.get("logs", []))
        
        if not api_result.get("success", False):
            test_result.status = TestStatus.FAILED
            test_result.error_details = api_result.get("error", "API test failed")
    
    def _execute_adapter_test(self, test_config: TestConfiguration, test_result: TestResult) -> None:
        """Execute an adapter test."""
        # Import here to avoid circular imports
        from adapters.adapter_validator import AdapterValidator
        
        adapter_validator = AdapterValidator()
        adapter_result = adapter_validator.validate_adapter(test_config)
        
        # Update test result with adapter-specific data
        test_result.metrics.update(adapter_result.get("metrics", {}))
        test_result.artifacts.extend(adapter_result.get("artifacts", []))
        test_result.logs.extend(adapter_result.get("logs", []))
        
        if not adapter_result.get("success", False):
            test_result.status = TestStatus.FAILED
            test_result.error_details = adapter_result.get("error", "Adapter test failed")
    
    def _execute_pipeline_test(self, test_config: TestConfiguration, test_result: TestResult) -> None:
        """Execute a pipeline test."""
        pipeline_result = self.pipeline_validator.validate_pipeline(test_config)
        
        # Update test result with pipeline-specific data
        test_result.metrics.update(pipeline_result.get("metrics", {}))
        test_result.artifacts.extend(pipeline_result.get("artifacts", []))
        test_result.logs.extend(pipeline_result.get("logs", []))
        
        if not pipeline_result.get("success", False):
            test_result.status = TestStatus.FAILED
            test_result.error_details = pipeline_result.get("error", "Pipeline test failed")
    
    def _generate_suite_summary(self, suite_results: TestSuiteResults) -> str:
        """Generate a summary report for the test suite."""
        summary_lines = [
            f"Test Suite: {suite_results.suite_name}",
            f"Suite ID: {suite_results.suite_id}",
            f"Execution Time: {suite_results.total_execution_time:.2f} seconds",
            f"",
            f"Results Summary:",
            f"  Total Tests: {suite_results.total_tests}",
            f"  Passed: {suite_results.passed_tests}",
            f"  Failed: {suite_results.failed_tests}",
            f"  Errors: {suite_results.error_tests}",
            f"  Skipped: {suite_results.skipped_tests}",
            f"  Success Rate: {suite_results.success_rate:.1%}",
            f""
        ]
        
        if suite_results.execution_metrics:
            metrics = suite_results.execution_metrics
            summary_lines.extend([
                f"Performance Metrics:",
                f"  Peak Memory: {metrics.memory_usage.get('peak_rss', 0) / 1024 / 1024:.1f} MB",
                f"  Average CPU: {metrics.resource_consumption.get('avg_cpu_percent', 0):.1f}%",
                f"  API Calls: {metrics.network_usage.get('total_api_calls', 0)}",
                f""
            ])
        
        if suite_results.failed_tests > 0 or suite_results.error_tests > 0:
            summary_lines.append("Failed/Error Tests:")
            for result in suite_results.test_results:
                if result.status in [TestStatus.FAILED, TestStatus.ERROR]:
                    summary_lines.append(f"  - {result.name}: {result.error_details or 'No details'}")
        
        return "\n".join(summary_lines)