"""
Unit tests for CLITestRunner component.

Tests command-line interface testing functionality.
"""

import pytest
import tempfile
import json
import subprocess
from pathlib import Path
from unittest.mock import patch, MagicMock

import sys
import os
sys.path.append(os.path.join(os.path.dirname(__file__), '../../'))

from cli.cli_test_runner import CLITestRunner
from models.test_models import TestResult
from core.error_handler import ExecutionError, ConfigurationError


class TestCLITestRunner:
    """Unit tests for CLITestRunner class."""
    
    def setup_method(self):
        """Set up test fixtures."""
        self.cli_runner = CLITestRunner()
        self.temp_dir = tempfile.mkdtemp()
        self.config = {
            'timeout': 300,
            'verbose': True,
            'output_dir': self.temp_dir
        }
    
    def teardown_method(self):
        """Clean up test fixtures."""
        import shutil
        if os.path.exists(self.temp_dir):
            shutil.rmtree(self.temp_dir)
    
    def test_run_builtin_tasks_success(self):
        """Test successful execution of builtin tasks."""
        with patch('subprocess.run') as mock_run:
            mock_run.return_value.returncode = 0
            mock_run.return_value.stdout = json.dumps({
                "results": {
                    "hellaswag": {"acc": 0.85, "acc_stderr": 0.02},
                    "arc_easy": {"acc": 0.78, "acc_stderr": 0.03}
                }
            })
            
            results = self.cli_runner.run_builtin_tasks(['hellaswag', 'arc_easy'], self.config)
            
            assert isinstance(results, list)
            assert len(results) == 2
            assert all(isinstance(r, TestResult) for r in results)
            assert all(r.status == 'passed' for r in results)
            assert all(r.real_execution_validated is True for r in results)
    
    def test_run_builtin_tasks_failure(self):
        """Test handling of builtin task execution failure."""
        with patch('subprocess.run') as mock_run:
            mock_run.return_value.returncode = 1
            mock_run.return_value.stderr = "Task execution failed"
            
            results = self.cli_runner.run_builtin_tasks(['hellaswag'], self.config)
            
            assert len(results) == 1
            assert results[0].status == 'failed'
            assert 'Task execution failed' in results[0].error_details
    
    def test_run_custom_tasks_success(self):
        """Test successful execution of custom tasks."""
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
        
        with patch('subprocess.run') as mock_run:
            mock_run.return_value.returncode = 0
            mock_run.return_value.stdout = json.dumps({
                "results": {
                    "math_task": {"exact_match": 0.9, "exact_match_stderr": 0.05}
                }
            })
            
            results = self.cli_runner.run_custom_tasks(custom_task_dir, self.config)
            
            assert len(results) > 0
            assert results[0].status == 'passed'
            assert 'exact_match' in results[0].metrics
    
    def test_run_adapter_tests_success(self):
        """Test successful adapter testing."""
        with patch('subprocess.run') as mock_run:
            mock_run.return_value.returncode = 0
            mock_run.return_value.stdout = json.dumps({
                "adapter_status": "success",
                "tests_passed": 5,
                "tests_failed": 0
            })
            
            results = self.cli_runner.run_adapter_tests('lm_eval', self.config)
            
            assert len(results) > 0
            assert results[0].status == 'passed'
            assert results[0].test_type == 'adapter'
    
    def test_run_full_pipeline_success(self):
        """Test successful full pipeline execution."""
        with patch('subprocess.run') as mock_run:
            mock_run.return_value.returncode = 0
            mock_run.return_value.stdout = json.dumps({
                "results": {
                    "hellaswag": {"acc": 0.85},
                    "django__django-12345": {"resolved": True}
                },
                "pipeline_status": "completed"
            })
            
            results = self.cli_runner.run_full_pipeline(self.config)
            
            assert len(results) > 0
            assert any(r.test_type == 'pipeline' for r in results)
            assert all(r.status == 'passed' for r in results if r.test_type == 'pipeline')
    
    def test_command_construction(self):
        """Test proper CLI command construction."""
        tasks = ['hellaswag', 'arc_easy']
        config = {
            'model': 'hf-causal',
            'model_args': 'pretrained=gpt2',
            'batch_size': 8,
            'device': 'cuda'
        }
        
        command = self.cli_runner._construct_command(tasks, config)
        
        assert isinstance(command, list)
        assert 'lm_eval' in command[0] or 'python' in command[0]
        assert '--tasks' in command
        assert 'hellaswag,arc_easy' in command
        assert '--model' in command
        assert 'hf-causal' in command
    
    def test_timeout_handling(self):
        """Test timeout handling for long-running commands."""
        with patch('subprocess.run') as mock_run:
            mock_run.side_effect = subprocess.TimeoutExpired('lm_eval', 300)
            
            results = self.cli_runner.run_builtin_tasks(['hellaswag'], {'timeout': 300})
            
            assert len(results) == 1
            assert results[0].status == 'failed'
            assert 'timeout' in results[0].error_details.lower()
    
    def test_output_parsing(self):
        """Test parsing of command output."""
        # Test valid JSON output
        valid_output = json.dumps({
            "results": {
                "hellaswag": {"acc": 0.85, "acc_stderr": 0.02}
            }
        })
        
        parsed = self.cli_runner._parse_output(valid_output)
        assert 'results' in parsed
        assert 'hellaswag' in parsed['results']
        
        # Test invalid JSON output
        invalid_output = "This is not valid JSON"
        
        with pytest.raises(ValueError):
            self.cli_runner._parse_output(invalid_output)
    
    def test_result_validation(self):
        """Test validation of execution results."""
        # Valid result
        valid_result = {
            "results": {
                "hellaswag": {"acc": 0.85, "acc_stderr": 0.02}
            },
            "metadata": {
                "execution_time": 45.2,
                "model_calls": 100
            }
        }
        
        is_valid = self.cli_runner._validate_result(valid_result)
        assert is_valid is True
        
        # Invalid result - missing required fields
        invalid_result = {
            "results": {}
        }
        
        is_valid = self.cli_runner._validate_result(invalid_result)
        assert is_valid is False
    
    def test_environment_setup(self):
        """Test environment setup for CLI execution."""
        with patch.dict(os.environ, {}, clear=True):
            env = self.cli_runner._setup_environment({'api_key': 'test_key'})
            
            assert 'OPENAI_API_KEY' in env or 'API_KEY' in env
            assert env.get('PYTHONPATH') is not None
    
    def test_working_directory_management(self):
        """Test working directory management during execution."""
        original_cwd = os.getcwd()
        test_dir = Path(self.temp_dir) / "test_workspace"
        test_dir.mkdir()
        
        with patch('subprocess.run') as mock_run:
            mock_run.return_value.returncode = 0
            mock_run.return_value.stdout = '{"results": {}}'
            
            self.cli_runner.run_builtin_tasks(['hellaswag'], {'working_dir': str(test_dir)})
            
            # Should have changed to test directory for execution
            mock_run.assert_called()
            call_kwargs = mock_run.call_args[1]
            assert call_kwargs.get('cwd') == str(test_dir)
        
        # Should restore original directory
        assert os.getcwd() == original_cwd
    
    def test_logging_configuration(self):
        """Test logging configuration for CLI execution."""
        with patch('logging.getLogger') as mock_logger:
            mock_logger_instance = MagicMock()
            mock_logger.return_value = mock_logger_instance
            
            self.cli_runner._configure_logging({'verbose': True, 'log_level': 'DEBUG'})
            
            mock_logger.assert_called()
            mock_logger_instance.setLevel.assert_called()
    
    def test_error_recovery(self):
        """Test error recovery mechanisms."""
        with patch('subprocess.run') as mock_run:
            # First call fails, second succeeds
            mock_run.side_effect = [
                MagicMock(returncode=1, stderr="Temporary failure"),
                MagicMock(returncode=0, stdout=json.dumps({
                    "results": {"hellaswag": {"acc": 0.85}}
                }))
            ]
            
            results = self.cli_runner.run_builtin_tasks_with_retry(
                ['hellaswag'], 
                self.config, 
                max_retries=2
            )
            
            assert len(results) == 1
            assert results[0].status == 'passed'
            assert mock_run.call_count == 2
    
    def test_batch_processing(self):
        """Test batch processing of multiple task sets."""
        task_batches = [
            ['hellaswag', 'arc_easy'],
            ['winogrande', 'piqa'],
            ['boolq', 'rte']
        ]
        
        with patch('subprocess.run') as mock_run:
            mock_run.return_value.returncode = 0
            mock_run.return_value.stdout = json.dumps({
                "results": {"task": {"acc": 0.85}}
            })
            
            all_results = self.cli_runner.run_task_batches(task_batches, self.config)
            
            assert len(all_results) == len(task_batches)
            assert all(len(batch_results) > 0 for batch_results in all_results)
    
    def test_configuration_validation(self):
        """Test validation of CLI configuration."""
        # Valid configuration
        valid_config = {
            'timeout': 300,
            'verbose': True,
            'model': 'hf-causal',
            'batch_size': 8
        }
        
        is_valid, errors = self.cli_runner.validate_config(valid_config)
        assert is_valid is True
        assert len(errors) == 0
        
        # Invalid configuration
        invalid_config = {
            'timeout': -1,  # Invalid timeout
            'batch_size': 'invalid'  # Invalid type
        }
        
        is_valid, errors = self.cli_runner.validate_config(invalid_config)
        assert is_valid is False
        assert len(errors) > 0
    
    def test_result_formatting(self):
        """Test formatting of CLI results."""
        test_results = [
            TestResult('test_001', 'cli', 'passed', 1.5, True, {'acc': 0.85}, None, []),
            TestResult('test_002', 'cli', 'failed', 2.0, False, {}, 'Error', [])
        ]
        
        # Test JSON formatting
        json_output = self.cli_runner.format_results(test_results, format='json')
        parsed_json = json.loads(json_output)
        assert len(parsed_json) == 2
        assert parsed_json[0]['test_id'] == 'test_001'
        
        # Test table formatting
        table_output = self.cli_runner.format_results(test_results, format='table')
        assert 'test_001' in table_output
        assert 'passed' in table_output
        assert 'failed' in table_output
    
    def test_cleanup_after_execution(self):
        """Test cleanup operations after CLI execution."""
        # Create temporary files
        temp_files = [
            Path(self.temp_dir) / "temp_result.json",
            Path(self.temp_dir) / "temp_log.txt"
        ]
        
        for temp_file in temp_files:
            temp_file.write_text("temporary data")
        
        # Run cleanup
        self.cli_runner.cleanup_execution_artifacts(self.temp_dir, keep_results=True)
        
        # Results should be kept, logs should be cleaned
        assert (Path(self.temp_dir) / "temp_result.json").exists()
        assert not (Path(self.temp_dir) / "temp_log.txt").exists()