"""
Unit tests for TestOrchestrator component.

Tests test coordination, execution, and orchestration functionality.
"""

import pytest
from unittest.mock import patch, MagicMock, AsyncMock
from pathlib import Path
import asyncio

import sys
import os
sys.path.append(os.path.join(os.path.dirname(__file__), '../../'))

from core.test_orchestrator import TestOrchestrator
from models.test_models import TestConfiguration, TestResult, TestSuiteResults
from core.error_handler import ExecutionError


class TestTestOrchestrator:
    """Unit tests for TestOrchestrator class."""
    
    def setup_method(self):
        """Set up test fixtures."""
        self.orchestrator = TestOrchestrator()
        self.sample_config = TestConfiguration(
            test_type='cli',
            target_adapters=['lm_eval', 'swe_bench'],
            task_selection={'builtin_tasks': ['hellaswag']},
            execution_params={'timeout': 300, 'verbose': True},
            output_config={'format': 'json', 'save_results': True}
        )
    
    def test_initialize_orchestrator(self):
        """Test orchestrator initialization."""
        assert self.orchestrator is not None
        assert hasattr(self.orchestrator, 'config_manager')
        assert hasattr(self.orchestrator, 'metrics_collector')
        assert hasattr(self.orchestrator, 'error_handler')
    
    @patch('core.test_orchestrator.TestOrchestrator._execute_test_suite')
    def test_execute_test_suite_success(self, mock_execute):
        """Test successful test suite execution."""
        mock_result = TestSuiteResults(
            suite_id='test_suite_001',
            total_tests=5,
            passed_tests=4,
            failed_tests=1,
            execution_time=120.5,
            test_results=[],
            summary={'success_rate': 0.8}
        )
        mock_execute.return_value = mock_result
        
        result = self.orchestrator.execute_test_suite(self.sample_config)
        
        assert result.suite_id == 'test_suite_001'
        assert result.total_tests == 5
        assert result.passed_tests == 4
        assert result.success_rate == 0.8
        mock_execute.assert_called_once_with(self.sample_config)
    
    def test_validate_configuration(self):
        """Test configuration validation."""
        # Valid configuration
        is_valid, errors = self.orchestrator.validate_configuration(self.sample_config)
        assert is_valid is True
        assert len(errors) == 0
        
        # Invalid configuration - missing required fields
        invalid_config = TestConfiguration(
            test_type='invalid_type',
            target_adapters=[],
            task_selection={},
            execution_params={},
            output_config={}
        )
        is_valid, errors = self.orchestrator.validate_configuration(invalid_config)
        assert is_valid is False
        assert len(errors) > 0
    
    @patch('core.test_orchestrator.TestOrchestrator._run_cli_tests')
    def test_execute_cli_tests(self, mock_cli_tests):
        """Test CLI test execution."""
        mock_results = [
            TestResult('test_001', 'cli', 'passed', 1.5, True, {}, None, []),
            TestResult('test_002', 'cli', 'failed', 2.0, True, {}, 'Error', [])
        ]
        mock_cli_tests.return_value = mock_results
        
        config = self.sample_config
        config.test_type = 'cli'
        
        results = self.orchestrator._execute_test_suite(config)
        
        assert len(results.test_results) == 2
        assert results.passed_tests == 1
        assert results.failed_tests == 1
        mock_cli_tests.assert_called_once()
    
    @patch('core.test_orchestrator.TestOrchestrator._run_api_tests')
    def test_execute_api_tests(self, mock_api_tests):
        """Test API test execution."""
        mock_results = [
            TestResult('api_001', 'api', 'passed', 0.8, True, {}, None, []),
            TestResult('api_002', 'api', 'passed', 1.2, True, {}, None, [])
        ]
        mock_api_tests.return_value = mock_results
        
        config = self.sample_config
        config.test_type = 'api'
        
        results = self.orchestrator._execute_test_suite(config)
        
        assert len(results.test_results) == 2
        assert results.passed_tests == 2
        assert results.failed_tests == 0
        mock_api_tests.assert_called_once()
    
    @patch('core.test_orchestrator.TestOrchestrator._run_adapter_tests')
    def test_execute_adapter_tests(self, mock_adapter_tests):
        """Test adapter validation tests."""
        mock_results = [
            TestResult('adapter_001', 'adapter', 'passed', 5.0, True, {}, None, [])
        ]
        mock_adapter_tests.return_value = mock_results
        
        config = self.sample_config
        config.test_type = 'adapter'
        
        results = self.orchestrator._execute_test_suite(config)
        
        assert len(results.test_results) == 1
        assert results.passed_tests == 1
        mock_adapter_tests.assert_called_once()
    
    def test_parallel_test_execution(self):
        """Test parallel execution of independent tests."""
        with patch('concurrent.futures.ThreadPoolExecutor') as mock_executor:
            mock_future = MagicMock()
            mock_future.result.return_value = TestResult('test_001', 'unit', 'passed', 1.0, True, {}, None, [])
            mock_executor.return_value.__enter__.return_value.submit.return_value = mock_future
            
            test_functions = [
                lambda: TestResult('test_001', 'unit', 'passed', 1.0, True, {}, None, []),
                lambda: TestResult('test_002', 'unit', 'passed', 1.5, True, {}, None, [])
            ]
            
            results = self.orchestrator._execute_parallel_tests(test_functions, max_workers=2)
            
            assert len(results) == 2
            assert all(result.status == 'passed' for result in results)
    
    def test_sequential_test_execution(self):
        """Test sequential execution of dependent tests."""
        test_functions = [
            lambda: TestResult('test_001', 'unit', 'passed', 1.0, True, {}, None, []),
            lambda: TestResult('test_002', 'unit', 'passed', 1.5, True, {}, None, [])
        ]
        
        results = self.orchestrator._execute_sequential_tests(test_functions)
        
        assert len(results) == 2
        assert results[0].test_id == 'test_001'
        assert results[1].test_id == 'test_002'
    
    def test_error_handling_during_execution(self):
        """Test error handling during test execution."""
        def failing_test():
            raise ExecutionError("Test execution failed")
        
        with patch.object(self.orchestrator.error_handler, 'handle_error') as mock_handle:
            mock_handle.return_value = {
                'error_type': 'ExecutionError',
                'recoverable': False,
                'suggestions': []
            }
            
            result = self.orchestrator._execute_single_test(failing_test, 'test_001')
            
            assert result.status == 'failed'
            assert result.error_details is not None
            mock_handle.assert_called_once()
    
    def test_timeout_handling(self):
        """Test timeout handling for long-running tests."""
        def long_running_test():
            import time
            time.sleep(10)  # Simulate long-running test
            return TestResult('test_001', 'unit', 'passed', 10.0, True, {}, None, [])
        
        with patch('signal.alarm') as mock_alarm:
            result = self.orchestrator._execute_with_timeout(
                long_running_test, 
                timeout=1,
                test_id='test_001'
            )
            
            assert result.status == 'failed'
            assert 'timeout' in result.error_details.lower()
            mock_alarm.assert_called()
    
    def test_resource_monitoring(self):
        """Test resource monitoring during test execution."""
        with patch('psutil.Process') as mock_process:
            mock_process.return_value.memory_info.return_value.rss = 1024 * 1024 * 100  # 100MB
            mock_process.return_value.cpu_percent.return_value = 25.5
            
            def test_function():
                return TestResult('test_001', 'unit', 'passed', 1.0, True, {}, None, [])
            
            result = self.orchestrator._execute_with_monitoring(test_function, 'test_001')
            
            assert result.status == 'passed'
            assert 'memory_usage' in result.metrics
            assert 'cpu_usage' in result.metrics
    
    def test_test_dependency_resolution(self):
        """Test resolution of test dependencies."""
        test_dependencies = {
            'test_001': [],
            'test_002': ['test_001'],
            'test_003': ['test_001', 'test_002']
        }
        
        execution_order = self.orchestrator._resolve_test_dependencies(test_dependencies)
        
        assert execution_order.index('test_001') < execution_order.index('test_002')
        assert execution_order.index('test_002') < execution_order.index('test_003')
    
    def test_test_result_aggregation(self):
        """Test aggregation of test results."""
        test_results = [
            TestResult('test_001', 'unit', 'passed', 1.0, True, {'accuracy': 0.9}, None, []),
            TestResult('test_002', 'unit', 'failed', 2.0, True, {}, 'Error', []),
            TestResult('test_003', 'integration', 'passed', 3.0, True, {'accuracy': 0.8}, None, [])
        ]
        
        aggregated = self.orchestrator._aggregate_results(test_results)
        
        assert aggregated.total_tests == 3
        assert aggregated.passed_tests == 2
        assert aggregated.failed_tests == 1
        assert aggregated.success_rate == 2/3
        assert aggregated.total_execution_time == 6.0
    
    def test_cleanup_after_execution(self):
        """Test cleanup operations after test execution."""
        with patch('shutil.rmtree') as mock_rmtree, \
             patch('os.path.exists') as mock_exists:
            
            mock_exists.return_value = True
            
            self.orchestrator._cleanup_test_artifacts(['temp_dir_1', 'temp_dir_2'])
            
            assert mock_rmtree.call_count == 2
    
    def test_real_execution_validation(self):
        """Test validation that tests perform real execution."""
        # Mock test result with indicators of real execution
        real_result = TestResult(
            'test_001', 'unit', 'passed', 2.5, True,
            {'api_calls': 5, 'tokens_used': 150}, None, []
        )
        
        is_real = self.orchestrator.validate_real_execution(real_result)
        assert is_real is True
        
        # Mock test result with indicators of mock execution
        mock_result = TestResult(
            'test_002', 'unit', 'passed', 0.01, False,
            {'api_calls': 0, 'tokens_used': 0}, None, []
        )
        
        is_real = self.orchestrator.validate_real_execution(mock_result)
        assert is_real is False
    
    @patch('core.test_orchestrator.TestOrchestrator._generate_test_report')
    def test_report_generation(self, mock_generate_report):
        """Test test report generation."""
        mock_report = {
            'summary': {'total': 5, 'passed': 4, 'failed': 1},
            'details': [],
            'recommendations': []
        }
        mock_generate_report.return_value = mock_report
        
        test_results = TestSuiteResults(
            'suite_001', 5, 4, 1, 120.0, [], {'success_rate': 0.8}
        )
        
        report = self.orchestrator.generate_report(test_results)
        
        assert report['summary']['total'] == 5
        assert report['summary']['passed'] == 4
        mock_generate_report.assert_called_once_with(test_results)