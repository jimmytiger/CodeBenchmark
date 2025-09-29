"""
Tests for the SWE-bench integration adapter.

This module contains comprehensive tests for the SWE-bench adapter,
including git operations, file editing, and test execution.
"""

import pytest
import tempfile
import shutil
import json
import os
from unittest.mock import Mock, patch, MagicMock
from pathlib import Path
from typing import Dict, Any

from EvaluationEngineV1_0.core.swe_bench_adapter import (
    SWEBenchAdapter,
    SWEBenchEnvironment,
    SWEBenchTaskWrapper,
    SWEBenchTaskInfo
)
from EvaluationEngineV1_0.core.adapters import AdapterInfo, StandardizedResult, AdapterStatus
from EvaluationEngineV1_0.core.task_types import TaskType, TurnData, TurnResult
from EvaluationEngineV1_0.core.exceptions import AdapterError, ConfigurationError, TaskExecutionError


class TestSWEBenchTaskInfo:
    """Test cases for SWEBenchTaskInfo dataclass."""
    
    def test_task_info_creation(self):
        """Test creating SWEBenchTaskInfo."""
        task_info = SWEBenchTaskInfo(
            instance_id="test_instance",
            repo="test/repo",
            base_commit="abc123",
            patch="test patch",
            test_patch="test test patch",
            problem_statement="Test problem",
            hints_text="Test hints",
            created_at="2023-01-01",
            version="1.0",
            environment={"python": "3.8"}
        )
        
        assert task_info.instance_id == "test_instance"
        assert task_info.repo == "test/repo"
        assert task_info.base_commit == "abc123"
        assert task_info.patch == "test patch"
        assert task_info.test_patch == "test test patch"
        assert task_info.problem_statement == "Test problem"
        assert task_info.hints_text == "Test hints"
        assert task_info.created_at == "2023-01-01"
        assert task_info.version == "1.0"
        assert task_info.environment == {"python": "3.8"}


class TestSWEBenchEnvironment:
    """Test cases for SWEBenchEnvironment."""
    
    def setup_method(self):
        """Set up test fixtures."""
        self.task_info = SWEBenchTaskInfo(
            instance_id="test_instance",
            repo="test/repo",
            base_commit="abc123",
            patch="test patch",
            test_patch="test test patch",
            problem_statement="Test problem statement",
            hints_text="Test hints",
            created_at="2023-01-01",
            version="1.0",
            environment={"python": "3.8"}
        )
        
        self.config = {
            "timeout": 30,
            "max_file_size": 1024,
            "allowed_commands": ["git", "python", "pytest", "ls", "cat"]
        }
    
    def test_environment_initialization(self):
        """Test environment initialization."""
        env = SWEBenchEnvironment(self.task_info, self.config)
        
        assert env.task_info == self.task_info
        assert env.config == self.config
        assert env.timeout == 30
        assert env.max_file_size == 1024
        assert "git" in env.allowed_commands
        assert env.work_dir is None
        assert env.repo_dir is None
    
    @patch('subprocess.run')
    @patch('tempfile.mkdtemp')
    def test_environment_reset_success(self, mock_mkdtemp, mock_subprocess):
        """Test successful environment reset."""
        # Mock temporary directory
        mock_work_dir = "/tmp/test_work_dir"
        mock_mkdtemp.return_value = mock_work_dir
        
        # Mock successful subprocess calls
        mock_subprocess.return_value = Mock(returncode=0, stdout="", stderr="")
        
        env = SWEBenchEnvironment(self.task_info, self.config)
        
        with patch('os.chdir'), patch('pathlib.Path.exists', return_value=False):
            observation = env.reset()
        
        assert env.is_initialized()
        assert isinstance(observation, dict)
        assert observation["problem_statement"] == "Test problem statement"
        assert observation["repo"] == "test/repo"
        assert observation["instance_id"] == "test_instance"
        assert observation["setup_complete"] is True
    
    @patch('subprocess.run')
    def test_environment_reset_git_failure(self, mock_subprocess):
        """Test environment reset with git failure."""
        # Mock failed git clone
        mock_subprocess.return_value = Mock(returncode=1, stdout="", stderr="Git error")
        
        env = SWEBenchEnvironment(self.task_info, self.config)
        
        with patch('tempfile.mkdtemp', return_value="/tmp/test"):
            with pytest.raises(TaskExecutionError, match="Failed to reset SWE-bench environment"):
                env.reset()
    
    def test_step_without_reset(self):
        """Test stepping without reset raises error."""
        env = SWEBenchEnvironment(self.task_info, self.config)
        
        with pytest.raises(TaskExecutionError, match="not initialized"):
            env.step("test command")
    
    @patch('subprocess.run')
    @patch('tempfile.mkdtemp')
    def test_step_command_execution(self, mock_mkdtemp, mock_subprocess):
        """Test command execution in step."""
        # Setup environment
        mock_mkdtemp.return_value = "/tmp/test_work_dir"
        mock_subprocess.return_value = Mock(returncode=0, stdout="test output", stderr="")
        
        env = SWEBenchEnvironment(self.task_info, self.config)
        
        with patch('os.chdir'), patch('pathlib.Path.exists', return_value=False):
            env.reset()
        
        # Test command execution
        mock_subprocess.return_value = Mock(returncode=0, stdout="ls output", stderr="")
        
        observation, reward, done, info = env.step("ls -la")
        
        assert isinstance(observation, dict)
        assert "result" in observation
        assert observation["result"]["success"] is True
        assert observation["result"]["stdout"] == "ls output"
        assert reward > 0
        assert info["action_type"] == "command"
    
    @patch('subprocess.run')
    @patch('tempfile.mkdtemp')
    def test_step_file_edit(self, mock_mkdtemp, mock_subprocess):
        """Test file editing in step."""
        # Setup environment
        mock_mkdtemp.return_value = "/tmp/test_work_dir"
        mock_subprocess.return_value = Mock(returncode=0, stdout="", stderr="")
        
        env = SWEBenchEnvironment(self.task_info, self.config)
        
        with patch('os.chdir'), patch('pathlib.Path.exists', return_value=False):
            env.reset()
        
        # Test file edit
        action = {
            "type": "file_edit",
            "file_path": "test.py",
            "content": "print('hello world')",
            "operation": "write"
        }
        
        with patch('pathlib.Path.write_text') as mock_write:
            with patch('pathlib.Path.exists', return_value=False):
                observation, reward, done, info = env.step(action)
        
        assert observation["result"]["success"] is True
        assert observation["result"]["file_path"] == "test.py"
        assert len(env.modifications) == 1
        mock_write.assert_called_once_with("print('hello world')")
    
    @patch('subprocess.run')
    @patch('tempfile.mkdtemp')
    def test_step_run_tests(self, mock_mkdtemp, mock_subprocess):
        """Test running tests in step."""
        # Setup environment
        mock_mkdtemp.return_value = "/tmp/test_work_dir"
        mock_subprocess.return_value = Mock(returncode=0, stdout="", stderr="")
        
        env = SWEBenchEnvironment(self.task_info, self.config)
        
        with patch('os.chdir'), patch('pathlib.Path.exists', return_value=False):
            env.reset()
        
        # Test running tests
        action = {
            "type": "run_tests",
            "test_command": "pytest -v"
        }
        
        # Mock test output
        test_output = "=== 2 passed, 1 failed in 1.23s ==="
        mock_subprocess.return_value = Mock(returncode=1, stdout=test_output, stderr="")
        
        observation, reward, done, info = env.step(action)
        
        assert "test_results" in observation["result"]
        assert len(env.test_results) == 1
        assert env.test_results[0]["passed"] == 2
        assert env.test_results[0]["failed"] == 1
    
    def test_parse_action_string(self):
        """Test parsing string actions."""
        env = SWEBenchEnvironment(self.task_info, self.config)
        
        # Test command string
        parsed = env._parse_action("ls -la")
        assert parsed["type"] == "command"
        assert parsed["command"] == "ls -la"
        
        # Test JSON string
        json_action = '{"type": "file_edit", "file_path": "test.py"}'
        parsed = env._parse_action(json_action)
        assert parsed["type"] == "file_edit"
        assert parsed["file_path"] == "test.py"
    
    def test_parse_action_dict(self):
        """Test parsing dictionary actions."""
        env = SWEBenchEnvironment(self.task_info, self.config)
        
        action = {"type": "run_tests", "test_command": "pytest"}
        parsed = env._parse_action(action)
        
        assert parsed == action
    
    def test_is_command_allowed(self):
        """Test command validation."""
        env = SWEBenchEnvironment(self.task_info, self.config)
        
        assert env._is_command_allowed("git status") is True
        assert env._is_command_allowed("python test.py") is True
        assert env._is_command_allowed("rm -rf /") is False
        assert env._is_command_allowed("") is False
    
    def test_parse_test_output_pytest(self):
        """Test parsing pytest output."""
        env = SWEBenchEnvironment(self.task_info, self.config)
        
        # Test successful output
        output = "=== 5 passed in 2.34s ==="
        results = env._parse_test_output(output, "")
        assert results["passed"] == 5
        assert results["failed"] == 0
        assert results["total"] == 5
        
        # Test mixed results
        output = "=== 2 failed, 3 passed in 1.23s ==="
        results = env._parse_test_output(output, "")
        assert results["passed"] == 3
        assert results["failed"] == 2
        assert results["total"] == 5
    
    def test_success_determination(self):
        """Test success determination."""
        env = SWEBenchEnvironment(self.task_info, self.config)
        
        # No test results
        assert env.success() is False
        
        # Failed tests
        env.test_results = [{"passed": 0, "failed": 1, "errors": 0, "total": 1}]
        assert env.success() is False
        
        # Successful tests
        env.test_results = [{"passed": 3, "failed": 0, "errors": 0, "total": 3}]
        assert env.success() is True
    
    def test_get_metrics(self):
        """Test metrics calculation."""
        env = SWEBenchEnvironment(self.task_info, self.config)
        
        # No test results
        metrics = env.get_metrics()
        assert metrics["test_success_rate"] == 0.0
        assert metrics["test_runs"] == 0.0
        
        # With test results
        env.test_results = [{"passed": 2, "failed": 1, "errors": 0, "total": 3}]
        env.modifications = [{"file": "test.py"}]
        
        metrics = env.get_metrics()
        assert metrics["test_success_rate"] == 2.0 / 3.0
        assert metrics["modifications_count"] == 1.0
        assert metrics["test_runs"] == 1.0
    
    def test_cleanup(self):
        """Test environment cleanup."""
        env = SWEBenchEnvironment(self.task_info, self.config)
        
        with patch('os.chdir') as mock_chdir:
            with patch('shutil.rmtree') as mock_rmtree:
                with patch('pathlib.Path.exists', return_value=True):
                    env.work_dir = Path("/tmp/test_work_dir")
                    env.cleanup()
        
        mock_chdir.assert_called_once()
        mock_rmtree.assert_called_once()


class TestSWEBenchTaskWrapper:
    """Test cases for SWEBenchTaskWrapper."""
    
    def setup_method(self):
        """Set up test fixtures."""
        self.task_info = SWEBenchTaskInfo(
            instance_id="test_instance",
            repo="test/repo",
            base_commit="abc123",
            patch="test patch",
            test_patch="test test patch",
            problem_statement="Test problem statement",
            hints_text="Test hints",
            created_at="2023-01-01",
            version="1.0",
            environment={"python": "3.8"}
        )
        
        self.config = {"task_name": "test_instance"}
    
    def test_task_wrapper_initialization(self):
        """Test task wrapper initialization."""
        wrapper = SWEBenchTaskWrapper(self.task_info, self.config)
        
        assert wrapper.task_info == self.task_info
        assert wrapper.get_id() == "test_instance"
        assert wrapper.config == self.config
        assert wrapper.environment is None
    
    def test_task_type(self):
        """Test task type."""
        wrapper = SWEBenchTaskWrapper(self.task_info, self.config)
        
        assert wrapper.get_task_type() == TaskType.MULTI_TURN
    
    def test_required_capabilities(self):
        """Test required capabilities."""
        wrapper = SWEBenchTaskWrapper(self.task_info, self.config)
        
        capabilities = wrapper.get_required_capabilities()
        
        assert "git_operations" in capabilities
        assert "file_editing" in capabilities
        assert "command_execution" in capabilities
        assert "test_execution" in capabilities
        assert "python_environment" in capabilities
    
    def test_validate_config(self):
        """Test configuration validation."""
        wrapper = SWEBenchTaskWrapper(self.task_info, self.config)
        
        assert wrapper.validate_config({"valid": "config"})
        
        with pytest.raises(ConfigurationError):
            wrapper.validate_config("not_a_dict")
    
    def test_get_initial_context(self):
        """Test getting initial context."""
        wrapper = SWEBenchTaskWrapper(self.task_info, self.config)
        
        context = wrapper.get_initial_context()
        
        assert "test_instance" in context
        assert "test/repo" in context
        assert "Test problem statement" in context
        assert "Test hints" in context
        assert "command:" in context
        assert "file_edit" in context
    
    @patch('EvaluationEngineV1_0.core.swe_bench_adapter.SWEBenchEnvironment')
    def test_execute_turn(self, mock_env_class):
        """Test executing a turn."""
        # Mock environment
        mock_env = Mock()
        mock_env.step.return_value = ("observation", 0.5, False, {"info": "test"})
        mock_env_class.return_value = mock_env
        
        wrapper = SWEBenchTaskWrapper(self.task_info, self.config)
        
        turn_data = TurnData(
            turn_number=1,
            input_context="ls -la",
            previous_actions=[],
            environment_state={}
        )
        
        result = wrapper.execute_turn(turn_data)
        
        assert isinstance(result, TurnResult)
        assert result.turn == 1
        assert result.action == "ls -la"
        assert result.observation == "observation"
        assert result.reward == 0.5
        assert result.done is False
        assert result.info == {"info": "test"}
    
    def test_should_continue(self):
        """Test should continue logic."""
        wrapper = SWEBenchTaskWrapper(self.task_info, self.config)
        
        # Should continue if not done
        turn_result = TurnResult(
            turn=1, action="test", observation="test", reward=0.5,
            done=False, info={}, execution_time=1.0
        )
        assert wrapper.should_continue(turn_result) is True
        
        # Should not continue if done
        turn_result.done = True
        assert wrapper.should_continue(turn_result) is False
    
    def test_is_successful_with_environment(self):
        """Test success determination with environment."""
        wrapper = SWEBenchTaskWrapper(self.task_info, self.config)
        
        # Mock environment
        mock_env = Mock()
        mock_env.success.return_value = True
        wrapper.environment = mock_env
        
        assert wrapper.is_successful([]) is True
        
        mock_env.success.return_value = False
        assert wrapper.is_successful([]) is False
    
    def test_is_successful_without_environment(self):
        """Test success determination without environment."""
        wrapper = SWEBenchTaskWrapper(self.task_info, self.config)
        
        # No environment, check turn results
        turn_results = [
            TurnResult(1, "test", "test", 0.9, False, {}, 1.0),
            TurnResult(2, "test", "test", 0.5, False, {}, 1.0)
        ]
        
        assert wrapper.is_successful(turn_results) is True
        
        # Low rewards
        turn_results = [
            TurnResult(1, "test", "test", 0.3, False, {}, 1.0),
            TurnResult(2, "test", "test", 0.2, False, {}, 1.0)
        ]
        
        assert wrapper.is_successful(turn_results) is False


class TestSWEBenchAdapter:
    """Test cases for SWEBenchAdapter."""
    
    def test_adapter_info(self):
        """Test adapter information."""
        adapter = SWEBenchAdapter({})
        info = adapter.get_adapter_info()
        
        assert info.name == "swe_bench_adapter"
        assert info.version == "1.0.0"
        assert TaskType.MULTI_TURN in info.supported_task_types
        assert "git" in info.required_dependencies
        assert "git_operations" in info.capabilities
        assert "multi_file_editing" in info.capabilities
        assert info.metadata["requires_git"] is True
    
    @patch('subprocess.run')
    def test_adapter_initialization_success(self, mock_subprocess):
        """Test successful adapter initialization."""
        # Mock successful tool checks
        mock_subprocess.return_value = Mock(returncode=0)
        
        adapter = SWEBenchAdapter({})
        
        assert adapter.initialize()
        assert adapter.is_ready()
        assert adapter.get_status() == AdapterStatus.READY
    
    @patch('subprocess.run')
    def test_adapter_initialization_missing_tool(self, mock_subprocess):
        """Test adapter initialization with missing tool."""
        # Mock missing tool
        mock_subprocess.return_value = Mock(returncode=1)
        
        adapter = SWEBenchAdapter({})
        
        assert not adapter.initialize()
        assert adapter.get_status() == AdapterStatus.ERROR
        assert "Required tool not found" in adapter.get_error_message()
    
    @patch('subprocess.run')
    def test_create_environment(self, mock_subprocess):
        """Test creating environment."""
        mock_subprocess.return_value = Mock(returncode=0)
        
        adapter = SWEBenchAdapter({})
        adapter.initialize()
        
        task_config = {
            "instance_id": "test_instance",
            "repo": "test/repo",
            "base_commit": "abc123",
            "patch": "test patch",
            "test_patch": "test test patch",
            "problem_statement": "Test problem"
        }
        
        env = adapter.create_environment(task_config)
        
        assert isinstance(env, SWEBenchEnvironment)
        assert env.task_info.instance_id == "test_instance"
    
    @patch('subprocess.run')
    def test_create_environment_missing_fields(self, mock_subprocess):
        """Test creating environment with missing required fields."""
        mock_subprocess.return_value = Mock(returncode=0)
        
        adapter = SWEBenchAdapter({})
        adapter.initialize()
        
        task_config = {"instance_id": "test"}  # Missing required fields
        
        with pytest.raises(ConfigurationError, match="Missing required field"):
            adapter.create_environment(task_config)
    
    @patch('subprocess.run')
    def test_load_tasks(self, mock_subprocess):
        """Test loading tasks."""
        mock_subprocess.return_value = Mock(returncode=0)
        
        adapter = SWEBenchAdapter({})
        adapter.initialize()
        
        tasks = adapter.load_tasks()
        
        assert len(tasks) == 1  # Mock task
        assert isinstance(tasks[0], SWEBenchTaskWrapper)
        assert tasks[0].get_id() == "django__django-12345"
    
    def test_convert_results_dict_format(self):
        """Test converting dictionary results."""
        adapter = SWEBenchAdapter({})
        
        results = {
            "instance_id": "test_instance",
            "success": True,
            "test_results": {"passed": 3, "total": 3},
            "execution_time": 45.2,
            "turns": 5,
            "modifications": ["file1.py", "file2.py"]
        }
        
        standardized = adapter.convert_results(results)
        
        assert standardized.task_id == "test_instance"
        assert standardized.adapter_name == "swe_bench_adapter"
        assert standardized.success is True
        assert standardized.score == 1.0  # 3/3 tests passed
        assert standardized.execution_time == 45.2
        assert standardized.turns == 5
        assert standardized.metadata["test_results"]["passed"] == 3
    
    def test_convert_results_unsupported_format(self):
        """Test converting unsupported result format."""
        adapter = SWEBenchAdapter({})
        
        results = "unsupported string format"
        
        standardized = adapter.convert_results(results)
        
        assert standardized.task_id == "unknown"
        assert standardized.success is False
        assert standardized.score == 0.0
        assert "conversion_error" in standardized.metadata
    
    def test_create_task_info_valid(self):
        """Test creating task info with valid config."""
        adapter = SWEBenchAdapter({})
        
        config = {
            "instance_id": "test_instance",
            "repo": "test/repo",
            "base_commit": "abc123",
            "patch": "test patch",
            "test_patch": "test test patch",
            "problem_statement": "Test problem",
            "hints_text": "Test hints",
            "created_at": "2023-01-01",
            "version": "1.0",
            "environment": {"python": "3.8"}
        }
        
        task_info = adapter._create_task_info(config)
        
        assert isinstance(task_info, SWEBenchTaskInfo)
        assert task_info.instance_id == "test_instance"
        assert task_info.repo == "test/repo"
        assert task_info.hints_text == "Test hints"
    
    def test_create_task_info_missing_field(self):
        """Test creating task info with missing required field."""
        adapter = SWEBenchAdapter({})
        
        config = {
            "instance_id": "test_instance",
            "repo": "test/repo"
            # Missing other required fields
        }
        
        with pytest.raises(ConfigurationError, match="Missing required field"):
            adapter._create_task_info(config)
    
    @patch('subprocess.run')
    def test_adapter_not_ready_operations(self, mock_subprocess):
        """Test operations when adapter is not ready."""
        adapter = SWEBenchAdapter({})
        # Don't initialize
        
        with pytest.raises(AdapterError, match="not initialized"):
            adapter.create_environment({"instance_id": "test"})
        
        with pytest.raises(AdapterError, match="not initialized"):
            adapter.load_tasks()


class TestSWEBenchIntegration:
    """Integration tests for SWE-bench adapter."""
    
    @patch('subprocess.run')
    @patch('tempfile.mkdtemp')
    def test_end_to_end_workflow(self, mock_mkdtemp, mock_subprocess):
        """Test end-to-end SWE-bench workflow."""
        # Setup mocks
        mock_mkdtemp.return_value = "/tmp/test_work_dir"
        mock_subprocess.return_value = Mock(returncode=0, stdout="", stderr="")
        
        # Initialize adapter
        adapter = SWEBenchAdapter({})
        assert adapter.initialize()
        
        # Load tasks
        tasks = adapter.load_tasks()
        assert len(tasks) == 1
        
        task = tasks[0]
        assert isinstance(task, SWEBenchTaskWrapper)
        
        # Get initial context
        context = task.get_initial_context()
        assert "django__django-12345" in context
        
        # Create environment through adapter
        task_config = {
            "instance_id": "test_instance",
            "repo": "test/repo",
            "base_commit": "abc123",
            "patch": "test patch",
            "test_patch": "test test patch",
            "problem_statement": "Test problem"
        }
        
        env = adapter.create_environment(task_config)
        assert isinstance(env, SWEBenchEnvironment)
        
        # Test environment operations
        with patch('os.chdir'), patch('pathlib.Path.exists', return_value=False):
            observation = env.reset()
            assert observation["setup_complete"] is True
        
        # Test command execution
        mock_subprocess.return_value = Mock(returncode=0, stdout="file1.py\nfile2.py", stderr="")
        obs, reward, done, info = env.step("ls *.py")
        
        assert obs["result"]["success"] is True
        assert "file1.py" in obs["result"]["stdout"]
        
        # Test file editing
        edit_action = {
            "type": "file_edit",
            "file_path": "test.py",
            "content": "# Fixed code\nprint('hello')",
            "operation": "write"
        }
        
        with patch('pathlib.Path.write_text'):
            with patch('pathlib.Path.exists', return_value=False):
                obs, reward, done, info = env.step(edit_action)
        
        assert obs["result"]["success"] is True
        assert len(env.modifications) == 1
        
        # Test running tests
        test_action = {"type": "run_tests", "test_command": "pytest -v"}
        mock_subprocess.return_value = Mock(
            returncode=0, 
            stdout="=== 3 passed in 1.23s ===", 
            stderr=""
        )
        
        obs, reward, done, info = env.step(test_action)
        
        assert obs["result"]["success"] is True
        assert env.test_results[-1]["passed"] == 3
        assert env.success() is True
        
        # Convert final results
        final_result = {
            "instance_id": "test_instance",
            "success": env.success(),
            "test_results": env.test_results[-1],
            "execution_time": 30.0,
            "turns": 3,
            "modifications": env.modifications
        }
        
        standardized = adapter.convert_results(final_result)
        assert standardized.success is True
        assert standardized.score == 1.0
        
        # Cleanup
        env.cleanup()