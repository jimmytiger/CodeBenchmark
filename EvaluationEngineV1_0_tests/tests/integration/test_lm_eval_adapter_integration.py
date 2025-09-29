"""
Integration tests for lm_eval_adapter validation.

Tests integration with lm-evaluation-harness and custom task execution.
"""

import pytest
import os
import tempfile
import json
from pathlib import Path
from unittest.mock import patch, MagicMock

import sys
sys.path.append(os.path.join(os.path.dirname(__file__), '../../'))

from adapters.lm_eval_adapter_validator import LMEvalAdapterValidator
from core.error_handler import DependencyError, ExecutionError
from models.test_models import ValidationResult, TestResult


class TestLMEvalAdapterIntegration:
    """Integration tests for LMEvalAdapterValidator."""
    
    def setup_method(self):
        """Set up test fixtures."""
        self.validator = LMEvalAdapterValidator()
        self.temp_dir = tempfile.mkdtemp()
        self.custom_task_dir = Path(self.temp_dir) / "custom_tasks"
        self.custom_task_dir.mkdir(exist_ok=True)
    
    def teardown_method(self):
        """Clean up test fixtures."""
        import shutil
        if os.path.exists(self.temp_dir):
            shutil.rmtree(self.temp_dir)
    
    def test_validate_integration_success(self):
        """Test successful integration validation."""
        with patch('subprocess.run') as mock_run:
            # Mock successful lm_eval installation check
            mock_run.return_value.returncode = 0
            mock_run.return_value.stdout = "lm_eval 0.4.0"
            
            result = self.validator.validate_integration()
            
            assert isinstance(result, ValidationResult)
            assert result.adapter_name == 'lm_eval'
            assert result.integration_status == 'success'
            assert result.dependencies_installed is True
    
    def test_validate_integration_missing_dependency(self):
        """Test integration validation with missing dependencies."""
        with patch('subprocess.run') as mock_run:
            # Mock missing lm_eval package
            mock_run.side_effect = FileNotFoundError("lm_eval not found")
            
            result = self.validator.validate_integration()
            
            assert result.integration_status == 'failed'
            assert result.dependencies_installed is False
            assert len(result.issues_found) > 0
    
    def test_install_dependencies_success(self):
        """Test successful dependency installation."""
        with patch('subprocess.run') as mock_run:
            mock_run.return_value.returncode = 0
            
            success = self.validator.install_dependencies()
            
            assert success is True
            # Should have called pip install
            mock_run.assert_called()
            call_args = mock_run.call_args[0][0]
            assert 'pip' in call_args
            assert 'install' in call_args
    
    def test_install_dependencies_failure(self):
        """Test dependency installation failure."""
        with patch('subprocess.run') as mock_run:
            mock_run.return_value.returncode = 1
            mock_run.return_value.stderr = "Installation failed"
            
            success = self.validator.install_dependencies()
            
            assert success is False
    
    def test_test_builtin_tasks_success(self):
        """Test successful builtin task execution."""
        with patch('subprocess.run') as mock_run:
            # Mock successful lm_eval execution
            mock_run.return_value.returncode = 0
            mock_run.return_value.stdout = json.dumps({
                "results": {
                    "hellaswag": {
                        "acc": 0.85,
                        "acc_stderr": 0.02
                    }
                }
            })
            
            results = self.validator.test_builtin_tasks(task_count=1)
            
            assert isinstance(results, list)
            assert len(results) > 0
            assert all(isinstance(r, TestResult) for r in results)
            assert results[0].status == 'passed'
            assert results[0].real_execution_validated is True
    
    def test_test_builtin_tasks_execution_failure(self):
        """Test builtin task execution failure."""
        with patch('subprocess.run') as mock_run:
            mock_run.return_value.returncode = 1
            mock_run.return_value.stderr = "Task execution failed"
            
            results = self.validator.test_builtin_tasks(task_count=1)
            
            assert len(results) > 0
            assert results[0].status == 'failed'
            assert 'Task execution failed' in results[0].error_details
    
    def test_discover_custom_tasks(self):
        """Test discovery of custom tasks in lm_eval/tasks directory."""
        # Create mock custom task files
        custom_task_1 = self.custom_task_dir / "custom_task_1.yaml"
        custom_task_2 = self.custom_task_dir / "custom_task_2.py"
        
        custom_task_1.write_text("""
task: custom_task_1
dataset_path: test_data.json
output_type: multiple_choice
metric: acc
""")
        
        custom_task_2.write_text("""
def doc_to_text(doc):
    return doc['question']

def doc_to_target(doc):
    return doc['answer']
""")
        
        discovered_tasks = self.validator.discover_custom_tasks(self.custom_task_dir)
        
        assert len(discovered_tasks) == 2
        assert 'custom_task_1' in [task['name'] for task in discovered_tasks]
        assert any(task['type'] == 'yaml' for task in discovered_tasks)
        assert any(task['type'] == 'python' for task in discovered_tasks)
    
    def test_test_custom_tasks_success(self):
        """Test successful custom task execution."""
        # Create a simple custom task
        custom_task = self.custom_task_dir / "simple_task.yaml"
        custom_task.write_text("""
task: simple_task
dataset_path: test_data.json
output_type: generate_until
metric: exact_match
""")
        
        # Create mock test data
        test_data = self.custom_task_dir / "test_data.json"
        test_data.write_text(json.dumps([
            {"question": "What is 2+2?", "answer": "4"},
            {"question": "What is 3+3?", "answer": "6"}
        ]))
        
        with patch('subprocess.run') as mock_run:
            mock_run.return_value.returncode = 0
            mock_run.return_value.stdout = json.dumps({
                "results": {
                    "simple_task": {
                        "exact_match": 0.9,
                        "exact_match_stderr": 0.05
                    }
                }
            })
            
            results = self.validator.test_custom_tasks(self.custom_task_dir)
            
            assert len(results) > 0
            assert results[0].status == 'passed'
            assert results[0].real_execution_validated is True
            assert 'exact_match' in results[0].metrics
    
    def test_validate_task_format(self):
        """Test validation of custom task format."""
        # Valid YAML task
        valid_task = {
            'task': 'test_task',
            'dataset_path': 'data.json',
            'output_type': 'multiple_choice',
            'metric': 'acc'
        }
        
        is_valid, errors = self.validator.validate_task_format(valid_task, 'yaml')
        assert is_valid is True
        assert len(errors) == 0
        
        # Invalid task - missing required fields
        invalid_task = {
            'task': 'test_task'
            # Missing other required fields
        }
        
        is_valid, errors = self.validator.validate_task_format(invalid_task, 'yaml')
        assert is_valid is False
        assert len(errors) > 0
    
    def test_execute_with_different_models(self):
        """Test execution with different model configurations."""
        model_configs = [
            {'model': 'hf-causal', 'model_args': 'pretrained=gpt2'},
            {'model': 'openai-completions', 'model_args': 'engine=text-davinci-003'}
        ]
        
        for config in model_configs:
            with patch('subprocess.run') as mock_run:
                mock_run.return_value.returncode = 0
                mock_run.return_value.stdout = json.dumps({
                    "results": {"hellaswag": {"acc": 0.8}}
                })
                
                results = self.validator.test_with_model_config(config, ['hellaswag'])
                
                assert len(results) > 0
                assert results[0].status == 'passed'
                # Verify model config was used in command
                call_args = mock_run.call_args[0][0]
                assert config['model'] in ' '.join(call_args)
    
    def test_performance_benchmarking(self):
        """Test performance benchmarking of lm_eval adapter."""
        with patch('subprocess.run') as mock_run, \
             patch('time.time') as mock_time:
            
            # Mock timing
            mock_time.side_effect = [1000.0, 1005.0]  # 5 second execution
            
            mock_run.return_value.returncode = 0
            mock_run.return_value.stdout = json.dumps({
                "results": {"hellaswag": {"acc": 0.85}}
            })
            
            benchmark_result = self.validator.benchmark_performance(['hellaswag'])
            
            assert 'execution_time' in benchmark_result
            assert 'throughput' in benchmark_result
            assert 'memory_usage' in benchmark_result
            assert benchmark_result['execution_time'] > 0
    
    def test_error_handling_and_recovery(self):
        """Test error handling and recovery mechanisms."""
        with patch('subprocess.run') as mock_run:
            # First call fails, second succeeds (retry logic)
            mock_run.side_effect = [
                MagicMock(returncode=1, stderr="Temporary failure"),
                MagicMock(returncode=0, stdout=json.dumps({
                    "results": {"hellaswag": {"acc": 0.85}}
                }))
            ]
            
            results = self.validator.test_builtin_tasks_with_retry(['hellaswag'], max_retries=2)
            
            assert len(results) > 0
            assert results[0].status == 'passed'
            assert mock_run.call_count == 2
    
    def test_concurrent_task_execution(self):
        """Test concurrent execution of multiple tasks."""
        tasks = ['hellaswag', 'arc_easy', 'winogrande']
        
        with patch('subprocess.run') as mock_run:
            mock_run.return_value.returncode = 0
            mock_run.return_value.stdout = json.dumps({
                "results": {
                    "hellaswag": {"acc": 0.85},
                    "arc_easy": {"acc": 0.78},
                    "winogrande": {"acc": 0.72}
                }
            })
            
            results = self.validator.test_tasks_concurrent(tasks, max_workers=2)
            
            assert len(results) == len(tasks)
            assert all(r.status == 'passed' for r in results)
    
    def test_integration_with_evaluation_engine(self):
        """Test integration with the main evaluation engine."""
        with patch('sys.path'), \
             patch('importlib.import_module') as mock_import:
            
            # Mock the evaluation engine module
            mock_engine = MagicMock()
            mock_engine.run_evaluation.return_value = {
                'results': {'hellaswag': {'acc': 0.85}},
                'metadata': {'execution_time': 5.2}
            }
            mock_import.return_value = mock_engine
            
            result = self.validator.test_integration_with_engine(['hellaswag'])
            
            assert result.status == 'passed'
            assert result.real_execution_validated is True
            assert 'acc' in result.metrics
    
    def test_cleanup_after_tests(self):
        """Test cleanup operations after test execution."""
        # Create some temporary files
        temp_files = [
            self.custom_task_dir / "temp_result_1.json",
            self.custom_task_dir / "temp_result_2.json"
        ]
        
        for temp_file in temp_files:
            temp_file.write_text('{"test": "data"}')
        
        # Run cleanup
        self.validator.cleanup_test_artifacts(str(self.custom_task_dir))
        
        # Verify files are cleaned up
        for temp_file in temp_files:
            assert not temp_file.exists()
    
    def test_generate_integration_report(self):
        """Test generation of integration test report."""
        # Mock some test results
        test_results = [
            TestResult('lm_eval_001', 'integration', 'passed', 5.2, True, 
                      {'acc': 0.85}, None, ['result.json']),
            TestResult('lm_eval_002', 'integration', 'failed', 2.1, False, 
                      {}, 'Task failed', [])
        ]
        
        validation_result = ValidationResult(
            adapter_name='lm_eval',
            integration_status='partial',
            dependencies_installed=True,
            test_results=test_results,
            performance_metrics={'avg_execution_time': 3.65},
            issues_found=['One task failed execution']
        )
        
        report = self.validator.generate_integration_report(validation_result)
        
        assert 'summary' in report
        assert 'test_results' in report
        assert 'performance_analysis' in report
        assert 'recommendations' in report
        assert report['summary']['total_tests'] == 2
        assert report['summary']['passed_tests'] == 1