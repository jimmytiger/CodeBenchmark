"""
End-to-end tests for complete evaluation pipeline.

Tests the entire evaluation pipeline from configuration to results.
"""

import pytest
import os
import tempfile
import json
import time
from pathlib import Path
from unittest.mock import patch, MagicMock

import sys
sys.path.append(os.path.join(os.path.dirname(__file__), '../../'))

from core.test_orchestrator import TestOrchestrator
from core.pipeline_validator import PipelineValidator
from models.test_models import TestConfiguration, TestSuiteResults
from cli.cli_test_runner import CLITestRunner
from api.api_test_client import APITestClient


class TestCompleteEvaluationPipeline:
    """End-to-end tests for complete evaluation pipeline."""
    
    def setup_method(self):
        """Set up test fixtures."""
        self.orchestrator = TestOrchestrator()
        self.pipeline_validator = PipelineValidator()
        self.cli_runner = CLITestRunner()
        self.api_client = APITestClient()
        self.temp_dir = tempfile.mkdtemp()
        
        # Sample configuration for testing
        self.test_config = TestConfiguration(
            test_type='pipeline',
            target_adapters=['lm_eval', 'swe_bench'],
            task_selection={
                'builtin_tasks': ['hellaswag', 'arc_easy'],
                'custom_tasks': [],
                'swe_tasks': ['django__django-12345']
            },
            execution_params={
                'timeout': 600,
                'verbose': True,
                'parallel_execution': True,
                'max_workers': 2
            },
            output_config={
                'format': 'json',
                'save_results': True,
                'output_dir': self.temp_dir
            }
        )
    
    def teardown_method(self):
        """Clean up test fixtures."""
        import shutil
        if os.path.exists(self.temp_dir):
            shutil.rmtree(self.temp_dir)
    
    def test_complete_pipeline_success(self):
        """Test successful execution of complete evaluation pipeline."""
        with patch('subprocess.run') as mock_run, \
             patch('time.time') as mock_time:
            
            # Mock timing
            mock_time.side_effect = [1000.0, 1120.0]  # 2 minute execution
            
            # Mock successful execution for all adapters
            mock_run.return_value.returncode = 0
            mock_run.return_value.stdout = json.dumps({
                "results": {
                    "hellaswag": {"acc": 0.85, "acc_stderr": 0.02},
                    "arc_easy": {"acc": 0.78, "acc_stderr": 0.03},
                    "django__django-12345": {"resolved": True, "execution_time": 45.2}
                },
                "metadata": {
                    "total_execution_time": 120.0,
                    "tasks_completed": 3,
                    "adapters_used": ["lm_eval", "swe_bench"]
                }
            })
            
            results = self.orchestrator.execute_test_suite(self.test_config)
            
            assert isinstance(results, TestSuiteResults)
            assert results.total_tests >= 3
            assert results.passed_tests > 0
            assert results.success_rate > 0.5
            assert results.execution_time > 0
    
    def test_pipeline_with_configuration_validation(self):
        """Test pipeline execution with configuration validation."""
        # Test with invalid configuration
        invalid_config = TestConfiguration(
            test_type='invalid_type',
            target_adapters=[],
            task_selection={},
            execution_params={},
            output_config={}
        )
        
        is_valid, errors = self.pipeline_validator.validate_pipeline_config(invalid_config)
        
        assert is_valid is False
        assert len(errors) > 0
        assert any('test_type' in error for error in errors)
    
    def test_pipeline_dependency_installation(self):
        """Test automatic dependency installation in pipeline."""
        with patch('subprocess.run') as mock_run:
            # Mock dependency check and installation
            mock_run.side_effect = [
                # First call: check lm_eval (not found)
                MagicMock(returncode=1, stderr="lm_eval not found"),
                # Second call: install lm_eval (success)
                MagicMock(returncode=0, stdout="Successfully installed lm_eval"),
                # Third call: check swe_bench (found)
                MagicMock(returncode=0, stdout="swe_bench 1.0.0"),
                # Fourth call: run evaluation (success)
                MagicMock(returncode=0, stdout=json.dumps({
                    "results": {"hellaswag": {"acc": 0.85}}
                }))
            ]
            
            results = self.pipeline_validator.validate_and_install_dependencies(self.test_config)
            
            assert results['lm_eval']['installed'] is True
            assert results['swe_bench']['installed'] is True
            assert mock_run.call_count >= 3
    
    def test_pipeline_with_parallel_execution(self):
        """Test pipeline execution with parallel task processing."""
        config = self.test_config
        config.execution_params['parallel_execution'] = True
        config.execution_params['max_workers'] = 3
        
        with patch('concurrent.futures.ThreadPoolExecutor') as mock_executor:
            mock_future = MagicMock()
            mock_future.result.return_value = {
                'test_id': 'test_001',
                'status': 'passed',
                'execution_time': 30.0
            }
            mock_executor.return_value.__enter__.return_value.submit.return_value = mock_future
            
            results = self.orchestrator.execute_parallel_pipeline(config)
            
            assert results.total_tests > 0
            assert results.execution_time > 0
            # Verify parallel execution was used
            mock_executor.assert_called_with(max_workers=3)
    
    def test_pipeline_error_handling_and_recovery(self):
        """Test pipeline error handling and recovery mechanisms."""
        with patch('subprocess.run') as mock_run:
            # Simulate mixed success/failure scenarios
            mock_run.side_effect = [
                # First task fails
                MagicMock(returncode=1, stderr="Task 1 failed"),
                # Second task succeeds
                MagicMock(returncode=0, stdout=json.dumps({
                    "results": {"arc_easy": {"acc": 0.78}}
                })),
                # Third task fails initially, then succeeds on retry
                MagicMock(returncode=1, stderr="Temporary failure"),
                MagicMock(returncode=0, stdout=json.dumps({
                    "results": {"django__django-12345": {"resolved": True}}
                }))
            ]
            
            results = self.pipeline_validator.execute_with_error_recovery(self.test_config)
            
            assert results.total_tests >= 3
            assert results.passed_tests >= 2  # At least 2 should pass after recovery
            assert results.failed_tests >= 1   # At least 1 should fail
    
    def test_pipeline_resource_monitoring(self):
        """Test resource monitoring during pipeline execution."""
        with patch('psutil.Process') as mock_process, \
             patch('subprocess.run') as mock_run:
            
            # Mock resource usage
            mock_process.return_value.memory_info.return_value.rss = 1024 * 1024 * 512  # 512MB
            mock_process.return_value.cpu_percent.return_value = 75.5
            
            mock_run.return_value.returncode = 0
            mock_run.return_value.stdout = json.dumps({
                "results": {"hellaswag": {"acc": 0.85}}
            })
            
            results = self.pipeline_validator.execute_with_monitoring(self.test_config)
            
            assert 'resource_usage' in results.summary
            assert results.summary['resource_usage']['peak_memory_mb'] > 0
            assert results.summary['resource_usage']['avg_cpu_percent'] > 0
    
    def test_cli_to_api_pipeline_integration(self):
        """Test integration between CLI and API interfaces."""
        # First, run CLI test to generate configuration
        cli_config_path = Path(self.temp_dir) / "cli_config.yaml"
        
        with patch('subprocess.run') as mock_run:
            mock_run.return_value.returncode = 0
            mock_run.return_value.stdout = json.dumps({
                "results": {"hellaswag": {"acc": 0.85}}
            })
            
            cli_results = self.cli_runner.run_builtin_tasks(
                ['hellaswag'], 
                {'output_config': str(cli_config_path)}
            )
            
            assert len(cli_results) > 0
            assert cli_results[0].status == 'passed'
        
        # Then, use API to run additional tests with same configuration
        with patch('requests.post') as mock_post:
            mock_post.return_value.status_code = 200
            mock_post.return_value.json.return_value = {
                'evaluation_id': 'eval_123',
                'status': 'completed',
                'results': {'arc_easy': {'acc': 0.78}}
            }
            
            api_results = self.api_client.run_evaluation_from_config(str(cli_config_path))
            
            assert api_results['status'] == 'completed'
            assert 'results' in api_results
    
    def test_pipeline_with_custom_tasks(self):
        """Test pipeline execution with custom tasks."""
        # Create custom task directory and files
        custom_task_dir = Path(self.temp_dir) / "custom_tasks"
        custom_task_dir.mkdir()
        
        custom_task = custom_task_dir / "math_task.yaml"
        custom_task.write_text("""
task: math_task
dataset_path: math_data.json
output_type: generate_until
metric: exact_match
""")
        
        math_data = custom_task_dir / "math_data.json"
        math_data.write_text(json.dumps([
            {"question": "What is 2+2?", "answer": "4"},
            {"question": "What is 5*3?", "answer": "15"}
        ]))
        
        # Update configuration to include custom tasks
        config = self.test_config
        config.task_selection['custom_tasks'] = [str(custom_task_dir)]
        
        with patch('subprocess.run') as mock_run:
            mock_run.return_value.returncode = 0
            mock_run.return_value.stdout = json.dumps({
                "results": {
                    "math_task": {"exact_match": 0.9, "exact_match_stderr": 0.05}
                }
            })
            
            results = self.orchestrator.execute_test_suite(config)
            
            assert results.total_tests > 0
            assert any('math_task' in str(result.test_id) for result in results.test_results)
    
    def test_pipeline_performance_benchmarking(self):
        """Test performance benchmarking throughout pipeline."""
        with patch('time.time') as mock_time, \
             patch('subprocess.run') as mock_run:
            
            # Mock detailed timing for different pipeline stages
            mock_time.side_effect = [
                1000.0,  # Start
                1010.0,  # After dependency check
                1020.0,  # After lm_eval tasks
                1050.0,  # After swe_bench tasks
                1060.0   # End
            ]
            
            mock_run.return_value.returncode = 0
            mock_run.return_value.stdout = json.dumps({
                "results": {
                    "hellaswag": {"acc": 0.85},
                    "django__django-12345": {"resolved": True}
                }
            })
            
            benchmark_results = self.pipeline_validator.benchmark_pipeline_performance(self.test_config)
            
            assert 'total_execution_time' in benchmark_results
            assert 'stage_timings' in benchmark_results
            assert 'throughput' in benchmark_results
            assert benchmark_results['total_execution_time'] == 60.0
    
    def test_pipeline_result_aggregation_and_analysis(self):
        """Test result aggregation and analysis across adapters."""
        with patch('subprocess.run') as mock_run:
            # Mock results from multiple adapters
            mock_run.return_value.returncode = 0
            mock_run.return_value.stdout = json.dumps({
                "results": {
                    "hellaswag": {"acc": 0.85, "acc_stderr": 0.02},
                    "arc_easy": {"acc": 0.78, "acc_stderr": 0.03},
                    "winogrande": {"acc": 0.72, "acc_stderr": 0.04},
                    "django__django-12345": {"resolved": True, "execution_time": 45.2},
                    "flask__flask-67890": {"resolved": False, "execution_time": 30.1}
                }
            })
            
            results = self.orchestrator.execute_test_suite(self.test_config)
            analysis = self.pipeline_validator.analyze_pipeline_results(results)
            
            assert 'adapter_performance' in analysis
            assert 'overall_metrics' in analysis
            assert 'recommendations' in analysis
            
            # Check lm_eval adapter analysis
            lm_eval_perf = analysis['adapter_performance']['lm_eval']
            assert lm_eval_perf['avg_accuracy'] > 0.7
            assert lm_eval_perf['task_count'] == 3
            
            # Check swe_bench adapter analysis
            swe_bench_perf = analysis['adapter_performance']['swe_bench']
            assert swe_bench_perf['resolution_rate'] == 0.5  # 1 out of 2 resolved
    
    def test_pipeline_with_real_execution_validation(self):
        """Test pipeline with comprehensive real execution validation."""
        with patch('subprocess.run') as mock_run, \
             patch('requests.post') as mock_requests:
            
            # Mock real API calls and responses
            mock_requests.return_value.status_code = 200
            mock_requests.return_value.json.return_value = {
                'choices': [{'text': 'Generated response'}],
                'usage': {'total_tokens': 150}
            }
            
            mock_run.return_value.returncode = 0
            mock_run.return_value.stdout = json.dumps({
                "results": {"hellaswag": {"acc": 0.85}},
                "metadata": {
                    "api_calls": 5,
                    "tokens_used": 750,
                    "execution_time": 45.2
                }
            })
            
            results = self.orchestrator.execute_test_suite(self.test_config)
            validation_report = self.pipeline_validator.validate_real_execution(results)
            
            assert validation_report['is_real_execution'] is True
            assert validation_report['confidence_score'] > 0.8
            assert 'evidence' in validation_report
            assert len(validation_report['evidence']) > 0
    
    def test_pipeline_cleanup_and_artifact_management(self):
        """Test cleanup and artifact management after pipeline execution."""
        # Create some temporary artifacts
        artifacts_dir = Path(self.temp_dir) / "artifacts"
        artifacts_dir.mkdir()
        
        temp_files = [
            artifacts_dir / "temp_result_1.json",
            artifacts_dir / "temp_result_2.json",
            artifacts_dir / "temp_config.yaml"
        ]
        
        for temp_file in temp_files:
            temp_file.write_text('{"temporary": "data"}')
        
        with patch('subprocess.run') as mock_run:
            mock_run.return_value.returncode = 0
            mock_run.return_value.stdout = json.dumps({
                "results": {"hellaswag": {"acc": 0.85}}
            })
            
            results = self.orchestrator.execute_test_suite(self.test_config)
            
            # Run cleanup
            self.pipeline_validator.cleanup_pipeline_artifacts(
                self.test_config, 
                results,
                keep_results=True,
                keep_logs=False
            )
            
            # Verify temporary files are cleaned up but results are kept
            for temp_file in temp_files:
                if 'result' in temp_file.name:
                    assert temp_file.exists()  # Results should be kept
                else:
                    assert not temp_file.exists()  # Other files should be cleaned
    
    def test_pipeline_failure_scenarios(self):
        """Test pipeline behavior under various failure scenarios."""
        failure_scenarios = [
            {
                'name': 'dependency_failure',
                'mock_returncode': 1,
                'mock_stderr': 'Failed to install dependencies'
            },
            {
                'name': 'timeout_failure',
                'mock_returncode': 124,  # Timeout exit code
                'mock_stderr': 'Command timed out'
            },
            {
                'name': 'memory_failure',
                'mock_returncode': 137,  # Out of memory
                'mock_stderr': 'Out of memory'
            }
        ]
        
        for scenario in failure_scenarios:
            with patch('subprocess.run') as mock_run:
                mock_run.return_value.returncode = scenario['mock_returncode']
                mock_run.return_value.stderr = scenario['mock_stderr']
                
                results = self.orchestrator.execute_test_suite(self.test_config)
                
                assert results.failed_tests > 0
                assert any(scenario['mock_stderr'] in str(result.error_details) 
                          for result in results.test_results 
                          if result.error_details)
    
    def test_pipeline_report_generation(self):
        """Test comprehensive report generation after pipeline execution."""
        with patch('subprocess.run') as mock_run:
            mock_run.return_value.returncode = 0
            mock_run.return_value.stdout = json.dumps({
                "results": {
                    "hellaswag": {"acc": 0.85, "acc_stderr": 0.02},
                    "django__django-12345": {"resolved": True, "execution_time": 45.2}
                }
            })
            
            results = self.orchestrator.execute_test_suite(self.test_config)
            report = self.pipeline_validator.generate_comprehensive_report(results)
            
            assert 'executive_summary' in report
            assert 'detailed_results' in report
            assert 'performance_analysis' in report
            assert 'recommendations' in report
            assert 'appendices' in report
            
            # Verify report completeness
            assert report['executive_summary']['total_tests'] > 0
            assert report['executive_summary']['success_rate'] > 0
            assert len(report['detailed_results']) > 0