"""
Comprehensive unit tests for configuration CLI functionality.

This module provides comprehensive test coverage for the CLI interface,
including command parsing, error handling, and integration scenarios.
"""

import pytest
import tempfile
import json
import os
import sys
from pathlib import Path
from unittest.mock import Mock, patch, MagicMock
from click.testing import CliRunner
from datetime import datetime

from evaluation_engine.cli.config_cli import (
    config_cli, run_command, validate_command, list_tasks_command,
    list_models_command, template_command, status_command
)
from evaluation_engine.config.models import (
    EvaluationConfig, ConfigMetadata, TaskConfig, ModelConfig,
    ValidationResult, ValidationError, ValidationSeverity
)


class TestConfigCLIBasic:
    """Test basic CLI functionality."""
    
    def setup_method(self):
        """Set up test fixtures."""
        self.runner = CliRunner()
    
    def test_config_cli_help(self):
        """Test CLI help output."""
        result = self.runner.invoke(config_cli, ['--help'])
        
        assert result.exit_code == 0
        assert "Configuration-driven evaluation commands" in result.output
        assert "run" in result.output
        assert "validate" in result.output
        assert "list-tasks" in result.output
        assert "list-models" in result.output
    
    def test_run_command_help(self):
        """Test run command help output."""
        result = self.runner.invoke(run_command, ['--help'])
        
        assert result.exit_code == 0
        assert "Run evaluation from configuration file" in result.output
        assert "--dry-run" in result.output
        assert "--task-filter" in result.output
        assert "--output-dir" in result.output
        assert "--verbose" in result.output
    
    def test_validate_command_help(self):
        """Test validate command help output."""
        result = self.runner.invoke(validate_command, ['--help'])
        
        assert result.exit_code == 0
        assert "Validate configuration file" in result.output
        assert "--format" in result.output
        assert "--verbose" in result.output


class TestRunCommand:
    """Test the run command functionality."""
    
    def setup_method(self):
        """Set up test fixtures."""
        self.runner = CliRunner()
        
        # Sample configuration
        self.sample_config = {
            "metadata": {
                "name": "CLI Test Config",
                "version": "1.0"
            },
            "models": {
                "test_model": {
                    "name": "test_model",
                    "type": "openai",
                    "model_name": "gpt-3.5-turbo",
                    "parameters": {"temperature": 0.7}
                }
            },
            "tasks": [{
                "name": "test_task",
                "model_ref": "test_model",
                "task_name": "hellaswag",
                "num_fewshot": 5
            }],
            "output": {
                "directory": "./test_results"
            }
        }
    
    def test_run_command_success(self):
        """Test successful run command execution."""
        with tempfile.NamedTemporaryFile(mode='w', suffix='.json', delete=False) as f:
            json.dump(self.sample_config, f)
            config_path = f.name
        
        try:
            with patch('evaluation_engine.cli.config_cli.ConfigDrivenEvaluator') as mock_evaluator_class:
                # Mock evaluator instance
                mock_evaluator = Mock()
                mock_evaluator_class.return_value = mock_evaluator
                
                # Mock successful result
                mock_result = Mock()
                mock_result.config_metadata.name = "CLI Test Config"
                mock_result.batch_result.total_tasks = 1
                mock_result.batch_result.completed_tasks = 1
                mock_result.batch_result.failed_tasks = 0
                mock_result.batch_result.success_rate = 100.0
                mock_result.total_execution_time = 30.5
                mock_evaluator.run_from_config.return_value = mock_result
                
                result = self.runner.invoke(run_command, [config_path])
                
                assert result.exit_code == 0
                assert "CLI Test Config" in result.output
                assert "Completed: 1" in result.output
                assert "Success rate: 100.0%" in result.output
                
        finally:
            os.unlink(config_path)
    
    def test_run_command_dry_run(self):
        """Test run command with dry-run flag."""
        with tempfile.NamedTemporaryFile(mode='w', suffix='.json', delete=False) as f:
            json.dump(self.sample_config, f)
            config_path = f.name
        
        try:
            with patch('evaluation_engine.cli.config_cli.ConfigDrivenEvaluator') as mock_evaluator_class:
                mock_evaluator = Mock()
                mock_evaluator_class.return_value = mock_evaluator
                
                mock_result = Mock()
                mock_result.config_metadata.name = "CLI Test Config"
                mock_result.batch_result.total_tasks = 1
                mock_result.batch_result.skipped_tasks = 1
                mock_result.batch_result.completed_tasks = 0
                mock_evaluator.run_from_config.return_value = mock_result
                
                result = self.runner.invoke(run_command, [config_path, '--dry-run'])
                
                assert result.exit_code == 0
                assert "DRY RUN MODE" in result.output
                assert "Skipped: 1" in result.output
                
                # Verify dry_run parameter was passed
                mock_evaluator.run_from_config.assert_called_once()
                call_kwargs = mock_evaluator.run_from_config.call_args[1]
                assert call_kwargs['dry_run'] is True
                
        finally:
            os.unlink(config_path)
    
    def test_run_command_with_task_filter(self):
        """Test run command with task filter."""
        with tempfile.NamedTemporaryFile(mode='w', suffix='.json', delete=False) as f:
            json.dump(self.sample_config, f)
            config_path = f.name
        
        try:
            with patch('evaluation_engine.cli.config_cli.ConfigDrivenEvaluator') as mock_evaluator_class:
                mock_evaluator = Mock()
                mock_evaluator_class.return_value = mock_evaluator
                
                mock_result = Mock()
                mock_result.config_metadata.name = "CLI Test Config"
                mock_result.batch_result.total_tasks = 1
                mock_result.batch_result.completed_tasks = 1
                mock_evaluator.run_from_config.return_value = mock_result
                
                result = self.runner.invoke(run_command, [
                    config_path, 
                    '--task-filter', 'test_task,another_task'
                ])
                
                assert result.exit_code == 0
                
                # Verify task_filter parameter was passed
                mock_evaluator.run_from_config.assert_called_once()
                call_kwargs = mock_evaluator.run_from_config.call_args[1]
                assert call_kwargs['task_filter'] == ['test_task', 'another_task']
                
        finally:
            os.unlink(config_path)
    
    def test_run_command_with_parameter_overrides(self):
        """Test run command with parameter overrides."""
        with tempfile.NamedTemporaryFile(mode='w', suffix='.json', delete=False) as f:
            json.dump(self.sample_config, f)
            config_path = f.name
        
        try:
            with patch('evaluation_engine.cli.config_cli.ConfigDrivenEvaluator') as mock_evaluator_class:
                mock_evaluator = Mock()
                mock_evaluator_class.return_value = mock_evaluator
                
                mock_result = Mock()
                mock_result.config_metadata.name = "CLI Test Config"
                mock_result.batch_result.total_tasks = 1
                mock_result.batch_result.completed_tasks = 1
                mock_evaluator.run_from_config.return_value = mock_result
                
                result = self.runner.invoke(run_command, [
                    config_path,
                    '--override', 'variables.temperature=0.5',
                    '--override', 'defaults.batch_size=16'
                ])
                
                assert result.exit_code == 0
                
                # Verify parameter_overrides were passed
                mock_evaluator.run_from_config.assert_called_once()
                call_kwargs = mock_evaluator.run_from_config.call_args[1]
                overrides = call_kwargs['parameter_overrides']
                assert overrides['variables']['temperature'] == '0.5'
                assert overrides['defaults']['batch_size'] == '16'
                
        finally:
            os.unlink(config_path)
    
    def test_run_command_with_output_dir(self):
        """Test run command with custom output directory."""
        with tempfile.NamedTemporaryFile(mode='w', suffix='.json', delete=False) as f:
            json.dump(self.sample_config, f)
            config_path = f.name
        
        try:
            with patch('evaluation_engine.cli.config_cli.ConfigDrivenEvaluator') as mock_evaluator_class:
                mock_evaluator = Mock()
                mock_evaluator_class.return_value = mock_evaluator
                
                mock_result = Mock()
                mock_result.config_metadata.name = "CLI Test Config"
                mock_result.batch_result.total_tasks = 1
                mock_result.batch_result.completed_tasks = 1
                mock_evaluator.run_from_config.return_value = mock_result
                
                result = self.runner.invoke(run_command, [
                    config_path,
                    '--output-dir', '/custom/output/path'
                ])
                
                assert result.exit_code == 0
                
                # Verify output directory override
                mock_evaluator.run_from_config.assert_called_once()
                call_kwargs = mock_evaluator.run_from_config.call_args[1]
                overrides = call_kwargs['parameter_overrides']
                assert overrides['output']['directory'] == '/custom/output/path'
                
        finally:
            os.unlink(config_path)
    
    def test_run_command_verbose_mode(self):
        """Test run command with verbose output."""
        with tempfile.NamedTemporaryFile(mode='w', suffix='.json', delete=False) as f:
            json.dump(self.sample_config, f)
            config_path = f.name
        
        try:
            with patch('evaluation_engine.cli.config_cli.ConfigDrivenEvaluator') as mock_evaluator_class:
                mock_evaluator = Mock()
                mock_evaluator_class.return_value = mock_evaluator
                
                mock_result = Mock()
                mock_result.config_metadata.name = "CLI Test Config"
                mock_result.config_metadata.version = "1.0"
                mock_result.config_metadata.author = "Test Author"
                mock_result.batch_result.total_tasks = 1
                mock_result.batch_result.completed_tasks = 1
                mock_result.batch_result.execution_order = ["test_task"]
                mock_result.total_execution_time = 45.2
                mock_evaluator.run_from_config.return_value = mock_result
                
                result = self.runner.invoke(run_command, [config_path, '--verbose'])
                
                assert result.exit_code == 0
                assert "Configuration Details:" in result.output
                assert "Version: 1.0" in result.output
                assert "Execution Order:" in result.output
                assert "test_task" in result.output
                
        finally:
            os.unlink(config_path)
    
    def test_run_command_file_not_found(self):
        """Test run command with non-existent file."""
        result = self.runner.invoke(run_command, ['/nonexistent/config.yaml'])
        
        assert result.exit_code != 0
        assert "Error" in result.output
    
    def test_run_command_validation_failure(self):
        """Test run command with configuration validation failure."""
        with tempfile.NamedTemporaryFile(mode='w', suffix='.json', delete=False) as f:
            json.dump(self.sample_config, f)
            config_path = f.name
        
        try:
            with patch('evaluation_engine.cli.config_cli.ConfigDrivenEvaluator') as mock_evaluator_class:
                mock_evaluator = Mock()
                mock_evaluator_class.return_value = mock_evaluator
                
                # Mock validation failure
                mock_evaluator.run_from_config.side_effect = ValueError("Configuration validation failed")
                
                result = self.runner.invoke(run_command, [config_path])
                
                assert result.exit_code != 0
                assert "Configuration validation failed" in result.output
                
        finally:
            os.unlink(config_path)
    
    def test_run_command_execution_failure(self):
        """Test run command with execution failure."""
        with tempfile.NamedTemporaryFile(mode='w', suffix='.json', delete=False) as f:
            json.dump(self.sample_config, f)
            config_path = f.name
        
        try:
            with patch('evaluation_engine.cli.config_cli.ConfigDrivenEvaluator') as mock_evaluator_class:
                mock_evaluator = Mock()
                mock_evaluator_class.return_value = mock_evaluator
                
                # Mock execution failure
                mock_result = Mock()
                mock_result.config_metadata.name = "CLI Test Config"
                mock_result.batch_result.total_tasks = 1
                mock_result.batch_result.completed_tasks = 0
                mock_result.batch_result.failed_tasks = 1
                mock_result.batch_result.success_rate = 0.0
                mock_result.batch_result.task_errors = {"test_task": "Task execution failed"}
                mock_evaluator.run_from_config.return_value = mock_result
                
                result = self.runner.invoke(run_command, [config_path])
                
                assert result.exit_code != 0
                assert "Failed: 1" in result.output
                assert "Task execution failed" in result.output
                
        finally:
            os.unlink(config_path)


class TestValidateCommand:
    """Test the validate command functionality."""
    
    def setup_method(self):
        """Set up test fixtures."""
        self.runner = CliRunner()
        
        self.valid_config = {
            "metadata": {"name": "Valid Config"},
            "models": {
                "test_model": {
                    "name": "test_model",
                    "type": "openai",
                    "model_name": "gpt-3.5-turbo"
                }
            },
            "tasks": [{
                "name": "test_task",
                "model_ref": "test_model",
                "task_name": "hellaswag"
            }]
        }
    
    def test_validate_command_success(self):
        """Test successful validation."""
        with tempfile.NamedTemporaryFile(mode='w', suffix='.json', delete=False) as f:
            json.dump(self.valid_config, f)
            config_path = f.name
        
        try:
            with patch('evaluation_engine.cli.config_cli.ConfigDrivenEvaluator') as mock_evaluator_class:
                mock_evaluator = Mock()
                mock_evaluator_class.return_value = mock_evaluator
                
                # Mock successful validation
                mock_validation = Mock()
                mock_validation.is_valid = True
                mock_validation.errors = []
                mock_validation.warnings = []
                mock_evaluator.validate_config_file.return_value = mock_validation
                
                result = self.runner.invoke(validate_command, [config_path])
                
                assert result.exit_code == 0
                assert "Configuration is valid" in result.output
                assert "✓" in result.output
                
        finally:
            os.unlink(config_path)
    
    def test_validate_command_with_errors(self):
        """Test validation with errors."""
        with tempfile.NamedTemporaryFile(mode='w', suffix='.json', delete=False) as f:
            json.dump(self.valid_config, f)
            config_path = f.name
        
        try:
            with patch('evaluation_engine.cli.config_cli.ConfigDrivenEvaluator') as mock_evaluator_class:
                mock_evaluator = Mock()
                mock_evaluator_class.return_value = mock_evaluator
                
                # Mock validation with errors
                mock_error = Mock()
                mock_error.type = "semantic"
                mock_error.message = "Model reference not found"
                mock_error.severity = ValidationSeverity.ERROR
                mock_error.location = "tasks[0].model_ref"
                mock_error.suggestion = "Check model definitions"
                
                mock_validation = Mock()
                mock_validation.is_valid = False
                mock_validation.errors = [mock_error]
                mock_validation.warnings = []
                mock_evaluator.validate_config_file.return_value = mock_validation
                
                result = self.runner.invoke(validate_command, [config_path])
                
                assert result.exit_code != 0
                assert "Configuration is invalid" in result.output
                assert "Model reference not found" in result.output
                assert "tasks[0].model_ref" in result.output
                assert "Check model definitions" in result.output
                
        finally:
            os.unlink(config_path)
    
    def test_validate_command_with_warnings(self):
        """Test validation with warnings."""
        with tempfile.NamedTemporaryFile(mode='w', suffix='.json', delete=False) as f:
            json.dump(self.valid_config, f)
            config_path = f.name
        
        try:
            with patch('evaluation_engine.cli.config_cli.ConfigDrivenEvaluator') as mock_evaluator_class:
                mock_evaluator = Mock()
                mock_evaluator_class.return_value = mock_evaluator
                
                # Mock validation with warnings
                mock_warning = Mock()
                mock_warning.type = "performance"
                mock_warning.message = "Large batch size may cause memory issues"
                mock_warning.severity = ValidationSeverity.WARNING
                mock_warning.location = "tasks[0].batch_size"
                mock_warning.suggestion = "Consider reducing batch size"
                
                mock_validation = Mock()
                mock_validation.is_valid = True
                mock_validation.errors = []
                mock_validation.warnings = [mock_warning]
                mock_evaluator.validate_config_file.return_value = mock_validation
                
                result = self.runner.invoke(validate_command, [config_path])
                
                assert result.exit_code == 0
                assert "Configuration is valid" in result.output
                assert "Warnings:" in result.output
                assert "Large batch size may cause memory issues" in result.output
                
        finally:
            os.unlink(config_path)
    
    def test_validate_command_verbose_mode(self):
        """Test validation with verbose output."""
        with tempfile.NamedTemporaryFile(mode='w', suffix='.json', delete=False) as f:
            json.dump(self.valid_config, f)
            config_path = f.name
        
        try:
            with patch('evaluation_engine.cli.config_cli.ConfigDrivenEvaluator') as mock_evaluator_class:
                mock_evaluator = Mock()
                mock_evaluator_class.return_value = mock_evaluator
                
                mock_validation = Mock()
                mock_validation.is_valid = True
                mock_validation.errors = []
                mock_validation.warnings = []
                mock_evaluator.validate_config_file.return_value = mock_validation
                
                # Mock parsed config for verbose output
                mock_config = Mock()
                mock_config.metadata.name = "Valid Config"
                mock_config.metadata.version = "1.0"
                mock_config.tasks = [Mock()]
                mock_config.models = {"test_model": Mock()}
                
                with patch('evaluation_engine.cli.config_cli.ConfigParser') as mock_parser_class:
                    mock_parser = Mock()
                    mock_parser_class.return_value = mock_parser
                    mock_parser.parse_config.return_value = mock_config
                    
                    result = self.runner.invoke(validate_command, [config_path, '--verbose'])
                    
                    assert result.exit_code == 0
                    assert "Configuration Details:" in result.output
                    assert "Tasks: 1" in result.output
                    assert "Models: 1" in result.output
                
        finally:
            os.unlink(config_path)


class TestListCommands:
    """Test list-tasks and list-models commands."""
    
    def setup_method(self):
        """Set up test fixtures."""
        self.runner = CliRunner()
    
    def test_list_tasks_command(self):
        """Test list-tasks command."""
        with patch('evaluation_engine.cli.config_cli.ConfigValidator') as mock_validator_class:
            mock_validator = Mock()
            mock_validator_class.return_value = mock_validator
            
            # Mock available tasks
            mock_validator._get_lm_eval_tasks.return_value = [
                "hellaswag", "arc_easy", "arc_challenge", "truthfulqa_mc",
                "gsm8k", "humaneval", "python_coding", "multi_turn_coding"
            ]
            
            result = self.runner.invoke(list_tasks_command)
            
            assert result.exit_code == 0
            assert "Available lm-eval tasks:" in result.output
            assert "hellaswag" in result.output
            assert "arc_easy" in result.output
            assert "python_coding" in result.output
    
    def test_list_tasks_command_with_filter(self):
        """Test list-tasks command with filter."""
        with patch('evaluation_engine.cli.config_cli.ConfigValidator') as mock_validator_class:
            mock_validator = Mock()
            mock_validator_class.return_value = mock_validator
            
            mock_validator._get_lm_eval_tasks.return_value = [
                "hellaswag", "arc_easy", "arc_challenge", "truthfulqa_mc",
                "gsm8k", "humaneval", "python_coding", "multi_turn_coding"
            ]
            
            result = self.runner.invoke(list_tasks_command, ['--filter', 'coding'])
            
            assert result.exit_code == 0
            assert "python_coding" in result.output
            assert "multi_turn_coding" in result.output
            assert "hellaswag" not in result.output
    
    def test_list_models_command(self):
        """Test list-models command."""
        with patch('evaluation_engine.cli.config_cli.ModelTemplateManager') as mock_manager_class:
            mock_manager = Mock()
            mock_manager_class.return_value = mock_manager
            
            # Mock available templates
            mock_manager.get_builtin_template_names.return_value = [
                "openai:default", "openai:qa", "openai:fewshot",
                "anthropic:default", "anthropic:conversation",
                "huggingface:default", "huggingface:llama2-chat"
            ]
            
            result = self.runner.invoke(list_models_command)
            
            assert result.exit_code == 0
            assert "Available model templates:" in result.output
            assert "openai:default" in result.output
            assert "anthropic:conversation" in result.output
            assert "huggingface:llama2-chat" in result.output
    
    def test_list_models_command_with_type_filter(self):
        """Test list-models command with type filter."""
        with patch('evaluation_engine.cli.config_cli.ModelTemplateManager') as mock_manager_class:
            mock_manager = Mock()
            mock_manager_class.return_value = mock_manager
            
            mock_manager.get_builtin_template_names.return_value = [
                "openai:default", "openai:qa", "openai:fewshot"
            ]
            
            result = self.runner.invoke(list_models_command, ['--type', 'openai'])
            
            assert result.exit_code == 0
            assert "openai:default" in result.output
            assert "openai:qa" in result.output
            assert "anthropic" not in result.output


class TestTemplateCommand:
    """Test template command functionality."""
    
    def setup_method(self):
        """Set up test fixtures."""
        self.runner = CliRunner()
    
    def test_template_command_generate(self):
        """Test template generation."""
        result = self.runner.invoke(template_command, ['basic'])
        
        assert result.exit_code == 0
        assert "metadata:" in result.output
        assert "models:" in result.output
        assert "tasks:" in result.output
        assert "output:" in result.output
    
    def test_template_command_save_to_file(self):
        """Test template generation with file output."""
        with tempfile.NamedTemporaryFile(mode='w', suffix='.yaml', delete=False) as f:
            output_path = f.name
        
        try:
            result = self.runner.invoke(template_command, [
                'multi-model', 
                '--output', output_path
            ])
            
            assert result.exit_code == 0
            assert f"Template saved to {output_path}" in result.output
            
            # Verify file was created
            assert os.path.exists(output_path)
            
            # Verify content
            with open(output_path, 'r') as f:
                content = f.read()
                assert "metadata:" in content
                assert "models:" in content
                
        finally:
            if os.path.exists(output_path):
                os.unlink(output_path)
    
    def test_template_command_invalid_template(self):
        """Test template command with invalid template name."""
        result = self.runner.invoke(template_command, ['nonexistent-template'])
        
        assert result.exit_code != 0
        assert "Unknown template" in result.output


class TestStatusCommand:
    """Test status command functionality."""
    
    def setup_method(self):
        """Set up test fixtures."""
        self.runner = CliRunner()
    
    def test_status_command_no_executions(self):
        """Test status command with no running executions."""
        with patch('evaluation_engine.cli.config_cli._get_running_executions') as mock_get_executions:
            mock_get_executions.return_value = []
            
            result = self.runner.invoke(status_command)
            
            assert result.exit_code == 0
            assert "No running evaluations" in result.output
    
    def test_status_command_with_executions(self):
        """Test status command with running executions."""
        mock_executions = [
            {
                "evaluation_id": "eval_123",
                "config_name": "Test Config",
                "status": "running",
                "progress": 0.6,
                "start_time": datetime.now(),
                "total_tasks": 5,
                "completed_tasks": 3
            },
            {
                "evaluation_id": "eval_456",
                "config_name": "Another Config",
                "status": "completed",
                "progress": 1.0,
                "start_time": datetime.now(),
                "total_tasks": 2,
                "completed_tasks": 2
            }
        ]
        
        with patch('evaluation_engine.cli.config_cli._get_running_executions') as mock_get_executions:
            mock_get_executions.return_value = mock_executions
            
            result = self.runner.invoke(status_command)
            
            assert result.exit_code == 0
            assert "Running Evaluations:" in result.output
            assert "eval_123" in result.output
            assert "Test Config" in result.output
            assert "60%" in result.output
            assert "3/5" in result.output


class TestCLIErrorHandling:
    """Test CLI error handling scenarios."""
    
    def setup_method(self):
        """Set up test fixtures."""
        self.runner = CliRunner()
    
    def test_invalid_config_file_format(self):
        """Test handling of invalid configuration file format."""
        with tempfile.NamedTemporaryFile(mode='w', suffix='.txt', delete=False) as f:
            f.write("This is not a valid config file")
            config_path = f.name
        
        try:
            result = self.runner.invoke(run_command, [config_path])
            
            assert result.exit_code != 0
            assert "Error" in result.output
            
        finally:
            os.unlink(config_path)
    
    def test_permission_denied_error(self):
        """Test handling of permission denied errors."""
        # Create a file and remove read permissions
        with tempfile.NamedTemporaryFile(mode='w', suffix='.json', delete=False) as f:
            json.dump({"test": "config"}, f)
            config_path = f.name
        
        try:
            # Remove read permissions
            os.chmod(config_path, 0o000)
            
            result = self.runner.invoke(run_command, [config_path])
            
            assert result.exit_code != 0
            assert "Error" in result.output
            
        finally:
            # Restore permissions and clean up
            os.chmod(config_path, 0o644)
            os.unlink(config_path)
    
    def test_keyboard_interrupt_handling(self):
        """Test handling of keyboard interrupt during execution."""
        with tempfile.NamedTemporaryFile(mode='w', suffix='.json', delete=False) as f:
            json.dump({"metadata": {"name": "test"}}, f)
            config_path = f.name
        
        try:
            with patch('evaluation_engine.cli.config_cli.ConfigDrivenEvaluator') as mock_evaluator_class:
                mock_evaluator = Mock()
                mock_evaluator_class.return_value = mock_evaluator
                
                # Mock keyboard interrupt
                mock_evaluator.run_from_config.side_effect = KeyboardInterrupt()
                
                result = self.runner.invoke(run_command, [config_path])
                
                assert result.exit_code != 0
                assert "interrupted" in result.output.lower()
                
        finally:
            os.unlink(config_path)
    
    def test_unexpected_exception_handling(self):
        """Test handling of unexpected exceptions."""
        with tempfile.NamedTemporaryFile(mode='w', suffix='.json', delete=False) as f:
            json.dump({"metadata": {"name": "test"}}, f)
            config_path = f.name
        
        try:
            with patch('evaluation_engine.cli.config_cli.ConfigDrivenEvaluator') as mock_evaluator_class:
                mock_evaluator = Mock()
                mock_evaluator_class.return_value = mock_evaluator
                
                # Mock unexpected exception
                mock_evaluator.run_from_config.side_effect = RuntimeError("Unexpected error")
                
                result = self.runner.invoke(run_command, [config_path])
                
                assert result.exit_code != 0
                assert "Unexpected error occurred" in result.output
                
        finally:
            os.unlink(config_path)


class TestCLIIntegration:
    """Test CLI integration scenarios."""
    
    def setup_method(self):
        """Set up test fixtures."""
        self.runner = CliRunner()
    
    def test_full_workflow_integration(self):
        """Test complete workflow from validation to execution."""
        config = {
            "metadata": {"name": "Integration Test"},
            "models": {
                "test_model": {
                    "name": "test_model",
                    "type": "openai",
                    "model_name": "gpt-3.5-turbo"
                }
            },
            "tasks": [{
                "name": "test_task",
                "model_ref": "test_model",
                "task_name": "hellaswag"
            }]
        }
        
        with tempfile.NamedTemporaryFile(mode='w', suffix='.json', delete=False) as f:
            json.dump(config, f)
            config_path = f.name
        
        try:
            with patch('evaluation_engine.cli.config_cli.ConfigDrivenEvaluator') as mock_evaluator_class:
                mock_evaluator = Mock()
                mock_evaluator_class.return_value = mock_evaluator
                
                # Mock validation success
                mock_validation = Mock()
                mock_validation.is_valid = True
                mock_validation.errors = []
                mock_validation.warnings = []
                mock_evaluator.validate_config_file.return_value = mock_validation
                
                # Step 1: Validate
                validate_result = self.runner.invoke(validate_command, [config_path])
                assert validate_result.exit_code == 0
                assert "Configuration is valid" in validate_result.output
                
                # Mock execution success
                mock_result = Mock()
                mock_result.config_metadata.name = "Integration Test"
                mock_result.batch_result.total_tasks = 1
                mock_result.batch_result.completed_tasks = 1
                mock_result.batch_result.failed_tasks = 0
                mock_result.batch_result.success_rate = 100.0
                mock_evaluator.run_from_config.return_value = mock_result
                
                # Step 2: Execute
                run_result = self.runner.invoke(run_command, [config_path])
                assert run_result.exit_code == 0
                assert "Integration Test" in run_result.output
                assert "Success rate: 100.0%" in run_result.output
                
        finally:
            os.unlink(config_path)


if __name__ == "__main__":
    pytest.main([__file__])