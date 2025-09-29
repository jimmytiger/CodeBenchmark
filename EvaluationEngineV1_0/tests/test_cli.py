"""
Tests for Multi-Turn Evaluation CLI

Tests command-line interface functionality, configuration parsing,
and interactive monitoring.
"""

import pytest
import json
import yaml
import tempfile
import os
from pathlib import Path
from unittest.mock import Mock, patch, AsyncMock
from click.testing import CliRunner

from ..cli.multi_turn_cli import cli, MultiTurnCLI
from ..cli.config_parser import ConfigParser
from ..cli.interactive_monitor import InteractiveMonitor
from ..core.data_models import MultiTurnConfig, FeedbackConfig, SafetyConfig


@pytest.fixture
def cli_runner():
    """Create CLI runner for testing."""
    return CliRunner()


@pytest.fixture
def config_parser():
    """Create config parser instance."""
    return ConfigParser()


@pytest.fixture
def interactive_monitor():
    """Create interactive monitor instance."""
    return InteractiveMonitor()


@pytest.fixture
def sample_config():
    """Sample configuration dictionary."""
    return {
        "model_id": "gpt-4",
        "task_ids": ["task1", "task2"],
        "max_turns": 10,
        "timeout_seconds": 3600,
        "feedback_strategy": "adaptive",
        "safety_level": "moderate",
        "enable_context_retention": True,
        "metadata": {"test": "data"}
    }


@pytest.fixture
def temp_config_file(sample_config):
    """Create temporary configuration file."""
    with tempfile.NamedTemporaryFile(mode='w', suffix='.yaml', delete=False) as f:
        yaml.dump(sample_config, f)
        temp_path = f.name
    
    yield temp_path
    
    # Cleanup
    os.unlink(temp_path)


class TestConfigParser:
    """Test configuration parser functionality."""
    
    def test_parse_yaml_config(self, config_parser, temp_config_file):
        """Test parsing YAML configuration file."""
        config_data = config_parser.parse_config_file(temp_config_file)
        
        assert config_data["model_id"] == "gpt-4"
        assert config_data["task_ids"] == ["task1", "task2"]
        assert config_data["max_turns"] == 10
        assert config_data["enable_context_retention"] is True
    
    def test_parse_json_config(self, config_parser, sample_config):
        """Test parsing JSON configuration file."""
        with tempfile.NamedTemporaryFile(mode='w', suffix='.json', delete=False) as f:
            json.dump(sample_config, f)
            temp_path = f.name
        
        try:
            config_data = config_parser.parse_config_file(temp_path)
            
            assert config_data["model_id"] == "gpt-4"
            assert config_data["task_ids"] == ["task1", "task2"]
            
        finally:
            os.unlink(temp_path)
    
    def test_parse_nonexistent_file(self, config_parser):
        """Test parsing non-existent configuration file."""
        with pytest.raises(FileNotFoundError):
            config_parser.parse_config_file("nonexistent.yaml")
    
    def test_parse_invalid_yaml(self, config_parser):
        """Test parsing invalid YAML file."""
        with tempfile.NamedTemporaryFile(mode='w', suffix='.yaml', delete=False) as f:
            f.write("invalid: yaml: content: [")
            temp_path = f.name
        
        try:
            with pytest.raises(ValueError, match="Invalid configuration file format"):
                config_parser.parse_config_file(temp_path)
        finally:
            os.unlink(temp_path)
    
    def test_validate_config_success(self, config_parser, sample_config):
        """Test successful configuration validation."""
        result = config_parser.validate_config(sample_config)
        
        assert result["valid"] is True
        assert len(result["errors"]) == 0
    
    def test_validate_config_missing_required_field(self, config_parser):
        """Test validation with missing required field."""
        config = {"model_id": "gpt-4"}  # Missing task_ids
        
        result = config_parser.validate_config(config)
        
        assert result["valid"] is False
        assert any("Missing required field: task_ids" in error for error in result["errors"])
    
    def test_validate_config_invalid_type(self, config_parser):
        """Test validation with invalid field type."""
        config = {
            "model_id": "gpt-4",
            "task_ids": "not_a_list",  # Should be list
            "max_turns": "not_a_number"  # Should be number
        }
        
        result = config_parser.validate_config(config)
        
        assert result["valid"] is False
        assert any("task_ids must be a list" in error for error in result["errors"])
        assert any("max_turns must be a number" in error for error in result["errors"])
    
    def test_validate_config_out_of_range(self, config_parser):
        """Test validation with out-of-range values."""
        config = {
            "model_id": "gpt-4",
            "task_ids": ["task1"],
            "max_turns": 200,  # Too high
            "timeout_seconds": 30  # Too low
        }
        
        result = config_parser.validate_config(config)
        
        assert result["valid"] is False
        assert any("max_turns must be between 1 and 100" in error for error in result["errors"])
        assert any("timeout_seconds must be between 60 and 86400" in error for error in result["errors"])
    
    def test_validate_config_invalid_choice(self, config_parser):
        """Test validation with invalid choice values."""
        config = {
            "model_id": "gpt-4",
            "task_ids": ["task1"],
            "feedback_strategy": "invalid_strategy",
            "safety_level": "invalid_level"
        }
        
        result = config_parser.validate_config(config)
        
        assert result["valid"] is False
        assert any("feedback_strategy must be one of" in error for error in result["errors"])
        assert any("safety_level must be one of" in error for error in result["errors"])
    
    def test_create_multi_turn_config(self, config_parser, sample_config):
        """Test creating MultiTurnConfig from configuration data."""
        config = config_parser.create_multi_turn_config(sample_config)
        
        assert isinstance(config, MultiTurnConfig)
        assert config.max_turns == 10
        assert config.conversation_timeout == 3600
        assert config.enable_context_retention is True
        assert isinstance(config.feedback_config, FeedbackConfig)
        assert isinstance(config.safety_config, SafetyConfig)
    
    def test_get_template_basic(self, config_parser):
        """Test getting basic configuration template."""
        template = config_parser.get_template("basic")
        
        assert "model_id" in template
        assert "task_ids" in template
        assert "max_turns" in template
        assert template["feedback_strategy"] == "adaptive"
    
    def test_get_template_advanced(self, config_parser):
        """Test getting advanced configuration template."""
        template = config_parser.get_template("advanced")
        
        assert "model_id" in template
        assert "task_ids" in template
        assert "max_feedback_length" in template
        assert "allowed_tools" in template
        assert "resource_limits" in template
    
    def test_get_template_swe_bench(self, config_parser):
        """Test getting SWE-bench configuration template."""
        template = config_parser.get_template("swe_bench")
        
        assert "model_id" in template
        assert "swe_bench" in template["task_ids"][0]
        assert template["max_turns"] == 20
        assert "pytest" in template["allowed_tools"]
    
    def test_get_template_intercode(self, config_parser):
        """Test getting InterCode configuration template."""
        template = config_parser.get_template("intercode")
        
        assert "model_id" in template
        assert "intercode" in template["task_ids"][0]
        assert template["safety_level"] == "strict"
        assert "sqlite3" in template["allowed_tools"]
    
    def test_get_template_invalid(self, config_parser):
        """Test getting invalid template."""
        with pytest.raises(ValueError, match="Template 'invalid' not found"):
            config_parser.get_template("invalid")
    
    def test_export_config_yaml(self, config_parser, sample_config):
        """Test exporting configuration to YAML."""
        config = config_parser.create_multi_turn_config(sample_config)
        
        with tempfile.NamedTemporaryFile(mode='w', suffix='.yaml', delete=False) as f:
            temp_path = f.name
        
        try:
            config_parser.export_config(config, temp_path, 'yaml')
            
            # Verify file was created and contains expected data
            assert os.path.exists(temp_path)
            
            with open(temp_path, 'r') as f:
                exported_data = yaml.safe_load(f)
            
            assert exported_data["max_turns"] == 10
            assert exported_data["enable_context_retention"] is True
            
        finally:
            os.unlink(temp_path)
    
    def test_export_config_json(self, config_parser, sample_config):
        """Test exporting configuration to JSON."""
        config = config_parser.create_multi_turn_config(sample_config)
        
        with tempfile.NamedTemporaryFile(mode='w', suffix='.json', delete=False) as f:
            temp_path = f.name
        
        try:
            config_parser.export_config(config, temp_path, 'json')
            
            # Verify file was created and contains expected data
            assert os.path.exists(temp_path)
            
            with open(temp_path, 'r') as f:
                exported_data = json.load(f)
            
            assert exported_data["max_turns"] == 10
            assert exported_data["enable_context_retention"] is True
            
        finally:
            os.unlink(temp_path)
    
    def test_merge_configs(self, config_parser):
        """Test merging configuration dictionaries."""
        base_config = {
            "model_id": "gpt-3.5",
            "max_turns": 5,
            "metadata": {"version": "1.0"}
        }
        
        override_config = {
            "model_id": "gpt-4",
            "timeout_seconds": 7200,
            "metadata": {"experiment": "test"}
        }
        
        merged = config_parser.merge_configs(base_config, override_config)
        
        assert merged["model_id"] == "gpt-4"  # Overridden
        assert merged["max_turns"] == 5  # From base
        assert merged["timeout_seconds"] == 7200  # From override
        assert merged["metadata"]["version"] == "1.0"  # Merged dict
        assert merged["metadata"]["experiment"] == "test"  # Merged dict


class TestCLICommands:
    """Test CLI command functionality."""
    
    @patch('EvaluationEngineV1_0.cli.multi_turn_cli.MultiTurnCLI._get_orchestrator')
    @patch('EvaluationEngineV1_0.cli.multi_turn_cli.MultiTurnCLI._get_task_registry')
    def test_run_command_basic(self, mock_registry, mock_orchestrator, cli_runner):
        """Test basic run command."""
        # Mock registry
        registry = Mock()
        registry.create_task_instance.return_value = Mock()
        mock_registry.return_value = registry
        
        # Mock orchestrator
        orchestrator = Mock()
        mock_orchestrator.return_value = orchestrator
        
        result = cli_runner.invoke(cli, [
            'run',
            '--model-id', 'gpt-4',
            '--task-id', 'task1',
            '--max-turns', '5'
        ])
        
        assert result.exit_code == 0
        assert "Starting multi-turn evaluation" in result.output
        assert "gpt-4" in result.output
    
    def test_run_config_command(self, cli_runner, temp_config_file):
        """Test run-config command."""
        with patch('EvaluationEngineV1_0.cli.multi_turn_cli.MultiTurnCLI._get_orchestrator'):
            with patch('EvaluationEngineV1_0.cli.multi_turn_cli.MultiTurnCLI._get_task_registry'):
                result = cli_runner.invoke(cli, [
                    'run-config',
                    temp_config_file
                ])
                
                assert result.exit_code == 0
                assert "Loading configuration from" in result.output
                assert "gpt-4" in result.output
    
    @patch('EvaluationEngineV1_0.cli.multi_turn_cli.MultiTurnCLI._get_task_registry')
    def test_list_tasks_command(self, mock_registry, cli_runner):
        """Test list-tasks command."""
        # Mock registry
        registry = Mock()
        registry.get_tasks_by_type.return_value = [
            {"task_id": "task1", "type": "multi_turn", "description": "Test task 1"},
            {"task_id": "task2", "type": "multi_turn", "description": "Test task 2"}
        ]
        mock_registry.return_value = registry
        
        result = cli_runner.invoke(cli, ['list-tasks'])
        
        assert result.exit_code == 0
        assert "task1" in result.output
        assert "task2" in result.output
    
    @patch('EvaluationEngineV1_0.cli.multi_turn_cli.MultiTurnCLI._get_task_registry')
    def test_describe_task_command(self, mock_registry, cli_runner):
        """Test describe-task command."""
        # Mock registry
        registry = Mock()
        registry.has_task.return_value = True
        registry.get_task_info.return_value = {
            "task_id": "task1",
            "type": "multi_turn",
            "description": "Test task description",
            "category": "coding",
            "difficulty": "intermediate",
            "requirements": ["Python knowledge"],
            "metrics": ["success_rate", "efficiency"]
        }
        mock_registry.return_value = registry
        
        result = cli_runner.invoke(cli, ['describe-task', 'task1'])
        
        assert result.exit_code == 0
        assert "task1" in result.output
        assert "Test task description" in result.output
    
    def test_describe_task_not_found(self, cli_runner):
        """Test describe-task command with non-existent task."""
        with patch('EvaluationEngineV1_0.cli.multi_turn_cli.MultiTurnCLI._get_task_registry') as mock_registry:
            registry = Mock()
            registry.has_task.return_value = False
            mock_registry.return_value = registry
            
            result = cli_runner.invoke(cli, ['describe-task', 'nonexistent'])
            
            assert result.exit_code == 1
            assert "Task not found" in result.output
    
    def test_init_config_command(self, cli_runner):
        """Test init-config command."""
        with tempfile.NamedTemporaryFile(suffix='.yaml', delete=False) as f:
            temp_path = f.name
        
        try:
            result = cli_runner.invoke(cli, [
                'init-config',
                '--output', temp_path,
                '--template', 'basic'
            ])
            
            assert result.exit_code == 0
            assert "Configuration template 'basic' written to" in result.output
            
            # Verify file was created
            assert os.path.exists(temp_path)
            
            # Verify content
            with open(temp_path, 'r') as f:
                config_data = yaml.safe_load(f)
            
            assert "model_id" in config_data
            assert "task_ids" in config_data
            
        finally:
            os.unlink(temp_path)
    
    def test_validate_config_command_valid(self, cli_runner, temp_config_file):
        """Test validate-config command with valid configuration."""
        result = cli_runner.invoke(cli, ['validate-config', temp_config_file])
        
        assert result.exit_code == 0
        assert "Configuration is valid" in result.output
        assert "Configuration Summary" in result.output
    
    def test_validate_config_command_invalid(self, cli_runner):
        """Test validate-config command with invalid configuration."""
        # Create invalid config file
        invalid_config = {"model_id": "gpt-4"}  # Missing task_ids
        
        with tempfile.NamedTemporaryFile(mode='w', suffix='.yaml', delete=False) as f:
            yaml.dump(invalid_config, f)
            temp_path = f.name
        
        try:
            result = cli_runner.invoke(cli, ['validate-config', temp_path])
            
            assert result.exit_code == 1
            assert "Configuration validation failed" in result.output
            
        finally:
            os.unlink(temp_path)


class TestInteractiveMonitor:
    """Test interactive monitor functionality."""
    
    def test_monitor_creation(self, interactive_monitor):
        """Test monitor instance creation."""
        assert interactive_monitor is not None
        assert len(interactive_monitor.evaluations) == 0
        assert not interactive_monitor.is_monitoring
    
    @pytest.mark.asyncio
    async def test_handle_connection_established(self, interactive_monitor):
        """Test handling connection established event."""
        data = {
            "type": "connection_established",
            "connection_id": "conn_123",
            "message": "Connection established"
        }
        
        # Mock websocket
        interactive_monitor.websocket = AsyncMock()
        
        await interactive_monitor._handle_connection_established(data)
        
        # Verify subscription message was sent
        interactive_monitor.websocket.send.assert_called_once()
        sent_message = json.loads(interactive_monitor.websocket.send.call_args[0][0])
        assert sent_message["type"] == "subscribe"
        assert sent_message["subscription_type"] == "system"
    
    @pytest.mark.asyncio
    async def test_handle_evaluation_progress(self, interactive_monitor):
        """Test handling evaluation progress event."""
        data = {
            "type": "evaluation_progress",
            "evaluation_id": "eval_123",
            "data": {
                "progress": 0.5,
                "current_task": "task1",
                "current_turn": 3
            }
        }
        
        await interactive_monitor._handle_evaluation_progress(data)
        
        # Verify evaluation was added/updated
        assert "eval_123" in interactive_monitor.evaluations
        eval_data = interactive_monitor.evaluations["eval_123"]
        assert eval_data["progress"] == 0.5
        assert eval_data["current_task"] == "task1"
        assert eval_data["current_turn"] == 3
    
    @pytest.mark.asyncio
    async def test_handle_turn_executed(self, interactive_monitor):
        """Test handling turn executed event."""
        data = {
            "type": "turn_executed",
            "evaluation_id": "eval_123",
            "data": {
                "turn_number": 5,
                "action": {"type": "code_execution"},
                "reward": 1.0,
                "done": False
            }
        }
        
        # Mock console to capture output
        with patch.object(interactive_monitor.console, 'print') as mock_print:
            await interactive_monitor._handle_turn_executed(data)
            
            # Verify console output
            mock_print.assert_called_once()
            call_args = mock_print.call_args[0][0]
            assert "Turn Executed" in call_args
            assert "eval_123" in call_args
            assert "Turn 5" in call_args
    
    @pytest.mark.asyncio
    async def test_handle_evaluation_completed(self, interactive_monitor):
        """Test handling evaluation completed event."""
        # Setup initial evaluation
        interactive_monitor.evaluations["eval_123"] = {
            "evaluation_id": "eval_123",
            "status": "running"
        }
        
        data = {
            "type": "evaluation_completed",
            "evaluation_id": "eval_123",
            "data": {
                "overall_success_rate": 0.8,
                "total_turns_executed": 25
            }
        }
        
        # Mock console to capture output
        with patch.object(interactive_monitor.console, 'print') as mock_print:
            await interactive_monitor._handle_evaluation_completed(data)
            
            # Verify evaluation status was updated
            eval_data = interactive_monitor.evaluations["eval_123"]
            assert eval_data["status"] == "completed"
            assert eval_data["progress"] == 1.0
            
            # Verify console output
            mock_print.assert_called_once()
            call_args = mock_print.call_args[0][0]
            assert "Evaluation Completed" in call_args
            assert "0.8" in call_args  # Success rate
    
    @pytest.mark.asyncio
    async def test_handle_safety_incident(self, interactive_monitor):
        """Test handling safety incident event."""
        # Setup initial evaluation
        interactive_monitor.evaluations["eval_123"] = {
            "evaluation_id": "eval_123",
            "safety_incidents": 0
        }
        
        data = {
            "type": "safety_incident",
            "evaluation_id": "eval_123",
            "data": {
                "incident_type": "dangerous_command",
                "severity": "high"
            }
        }
        
        # Mock console to capture output
        with patch.object(interactive_monitor.console, 'print') as mock_print:
            await interactive_monitor._handle_safety_incident(data)
            
            # Verify safety incident count was incremented
            eval_data = interactive_monitor.evaluations["eval_123"]
            assert eval_data["safety_incidents"] == 1
            
            # Verify console output
            mock_print.assert_called_once()
            call_args = mock_print.call_args[0][0]
            assert "Safety Incident" in call_args
            assert "dangerous_command" in call_args
    
    @pytest.mark.asyncio
    async def test_subscribe_to_evaluation(self, interactive_monitor):
        """Test subscribing to evaluation updates."""
        # Mock websocket
        interactive_monitor.websocket = AsyncMock()
        
        await interactive_monitor.subscribe_to_evaluation("eval_123")
        
        # Verify subscription message was sent
        interactive_monitor.websocket.send.assert_called_once()
        sent_message = json.loads(interactive_monitor.websocket.send.call_args[0][0])
        assert sent_message["type"] == "subscribe"
        assert sent_message["subscription_type"] == "evaluation"
        assert sent_message["evaluation_id"] == "eval_123"
    
    def test_display_evaluation_summary(self, interactive_monitor):
        """Test displaying evaluation summary."""
        evaluation_data = {
            "evaluation_id": "eval_123",
            "model_id": "gpt-4",
            "status": "running",
            "progress": 0.6,
            "completed_tasks": 3,
            "total_tasks": 5,
            "safety_incidents": 1,
            "total_turns_executed": 15
        }
        
        # Mock console to capture output
        with patch.object(interactive_monitor.console, 'print') as mock_print:
            interactive_monitor.display_evaluation_summary(evaluation_data)
            
            # Verify console was called
            mock_print.assert_called_once()
    
    def test_display_turn_details(self, interactive_monitor):
        """Test displaying turn details."""
        turn_data = {
            "turn_number": 5,
            "action": {"type": "code_execution", "code": "print('hello')"},
            "observation": {"stdout": "hello\n", "stderr": ""},
            "reward": 1.0,
            "done": False
        }
        
        # Mock console to capture output
        with patch.object(interactive_monitor.console, 'print') as mock_print:
            interactive_monitor.display_turn_details(turn_data)
            
            # Verify console was called
            mock_print.assert_called_once()


if __name__ == "__main__":
    pytest.main([__file__])