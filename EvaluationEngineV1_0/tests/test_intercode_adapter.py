"""
Tests for the InterCode integration adapter.

This module contains comprehensive tests for the InterCode adapter,
including Python, Bash, and SQL execution environments.
"""

import pytest
import tempfile
import shutil
import json
import os
import sqlite3
from unittest.mock import Mock, patch, MagicMock
from pathlib import Path
from typing import Dict, Any

from EvaluationEngineV1_0.core.intercode_adapter import (
    InterCodeAdapter,
    InterCodeEnvironment,
    InterCodeTaskWrapper,
    InterCodeTaskInfo,
    PythonExecutor,
    BashExecutor,
    SQLExecutor
)
from EvaluationEngineV1_0.core.adapters import AdapterInfo, StandardizedResult, AdapterStatus
from EvaluationEngineV1_0.core.task_types import TaskType, TurnData, TurnResult
from EvaluationEngineV1_0.core.exceptions import AdapterError, ConfigurationError, TaskExecutionError


class TestInterCodeTaskInfo:
    """Test cases for InterCodeTaskInfo dataclass."""
    
    def test_task_info_creation(self):
        """Test creating InterCodeTaskInfo."""
        task_info = InterCodeTaskInfo(
            task_id="test_task",
            task_type="python",
            query="Print hello world",
            gold="hello world",
            setup="import os",
            metadata={"difficulty": "easy"}
        )
        
        assert task_info.task_id == "test_task"
        assert task_info.task_type == "python"
        assert task_info.query == "Print hello world"
        assert task_info.gold == "hello world"
        assert task_info.setup == "import os"
        assert task_info.metadata == {"difficulty": "easy"}
    
    def test_task_info_defaults(self):
        """Test InterCodeTaskInfo with default values."""
        task_info = InterCodeTaskInfo(
            task_id="test_task",
            task_type="python",
            query="Print hello world",
            gold="hello world"
        )
        
        assert task_info.setup is None
        assert task_info.metadata == {}


class TestPythonExecutor:
    """Test cases for PythonExecutor."""
    
    def setup_method(self):
        """Set up test fixtures."""
        self.config = {"timeout": 30}
        self.executor = PythonExecutor(self.config)
        self.work_dir = Path(tempfile.mkdtemp())
    
    def teardown_method(self):
        """Clean up test fixtures."""
        if self.work_dir.exists():
            shutil.rmtree(self.work_dir)
    
    def test_executor_initialization(self):
        """Test executor initialization."""
        assert self.executor.config == self.config
        assert self.executor.timeout == 30
        assert self.executor.globals_dict == {}
        assert self.executor.locals_dict == {}
    
    def test_executor_reset(self):
        """Test executor reset."""
        self.executor.reset(self.work_dir)
        
        assert self.executor.work_dir == self.work_dir
        assert "__builtins__" in self.executor.globals_dict
        assert self.executor.locals_dict == {}
    
    def test_execute_simple_code(self):
        """Test executing simple Python code."""
        self.executor.reset(self.work_dir)
        
        result = self.executor.execute("print('hello world')")
        
        assert result["success"] is True
        assert "hello world" in result["stdout"]
        assert result["stderr"] == ""
        assert isinstance(result["variables"], dict)
    
    def test_execute_with_variables(self):
        """Test executing code that creates variables."""
        self.executor.reset(self.work_dir)
        
        result = self.executor.execute("x = 42\ny = 'test'\nprint(x, y)")
        
        assert result["success"] is True
        assert "42 test" in result["stdout"]
        assert "x" in result["variables"]
        assert "y" in result["variables"]
        assert result["variables"]["x"] == "42"
        assert result["variables"]["y"] == "test"
    
    def test_execute_with_error(self):
        """Test executing code with syntax error."""
        self.executor.reset(self.work_dir)
        
        result = self.executor.execute("print('hello world'")  # Missing closing parenthesis
        
        assert result["success"] is False
        assert "error" in result
        assert result["stderr"] != ""
    
    def test_execute_persistent_state(self):
        """Test that variables persist between executions."""
        self.executor.reset(self.work_dir)
        
        # First execution
        result1 = self.executor.execute("x = 10")
        assert result1["success"] is True
        assert result1["variables"]["x"] == "10"
        
        # Second execution using previous variable
        result2 = self.executor.execute("y = x * 2\nprint(y)")
        assert result2["success"] is True
        assert "20" in result2["stdout"]
        assert result2["variables"]["y"] == "20"


class TestBashExecutor:
    """Test cases for BashExecutor."""
    
    def setup_method(self):
        """Set up test fixtures."""
        self.config = {"timeout": 30}
        self.executor = BashExecutor(self.config)
        self.work_dir = Path(tempfile.mkdtemp())
    
    def teardown_method(self):
        """Clean up test fixtures."""
        if self.work_dir.exists():
            shutil.rmtree(self.work_dir)
    
    def test_executor_initialization(self):
        """Test executor initialization."""
        assert self.executor.config == self.config
        assert self.executor.timeout == 30
        assert isinstance(self.executor.env_vars, dict)
    
    def test_executor_reset(self):
        """Test executor reset."""
        self.executor.reset(self.work_dir)
        
        assert self.executor.work_dir == self.work_dir
        assert self.executor.env_vars["PWD"] == str(self.work_dir)
    
    def test_execute_simple_command(self):
        """Test executing simple bash command."""
        self.executor.reset(self.work_dir)
        
        result = self.executor.execute("echo 'hello world'")
        
        assert result["success"] is True
        assert "hello world" in result["stdout"]
        assert result["returncode"] == 0
    
    def test_execute_file_operations(self):
        """Test executing file operations."""
        self.executor.reset(self.work_dir)
        
        # Create a file
        result1 = self.executor.execute("echo 'test content' > test.txt")
        assert result1["success"] is True
        
        # Read the file
        result2 = self.executor.execute("cat test.txt")
        assert result2["success"] is True
        assert "test content" in result2["stdout"]
    
    def test_execute_failed_command(self):
        """Test executing failed command."""
        self.executor.reset(self.work_dir)
        
        result = self.executor.execute("ls /nonexistent/directory")
        
        assert result["success"] is False
        assert result["returncode"] != 0
        assert result["stderr"] != ""
    
    @patch('subprocess.run')
    def test_execute_timeout(self, mock_run):
        """Test command timeout handling."""
        from subprocess import TimeoutExpired
        mock_run.side_effect = TimeoutExpired("test", 30)
        
        self.executor.reset(self.work_dir)
        
        result = self.executor.execute("sleep 100")
        
        assert result["success"] is False
        assert "timed out" in result["stderr"]
        assert result["error"] == "Timeout"


class TestSQLExecutor:
    """Test cases for SQLExecutor."""
    
    def setup_method(self):
        """Set up test fixtures."""
        self.config = {"timeout": 30}
        self.executor = SQLExecutor(self.config)
        self.work_dir = Path(tempfile.mkdtemp())
    
    def teardown_method(self):
        """Clean up test fixtures."""
        self.executor.cleanup()
        if self.work_dir.exists():
            shutil.rmtree(self.work_dir)
    
    def test_executor_initialization(self):
        """Test executor initialization."""
        assert self.executor.config == self.config
        assert self.executor.timeout == 30
        assert self.executor.db_path is None
        assert self.executor.connection is None
    
    def test_executor_reset(self):
        """Test executor reset."""
        self.executor.reset(self.work_dir)
        
        assert self.executor.work_dir == self.work_dir
        assert self.executor.db_path == self.work_dir / "intercode.db"
        assert self.executor.connection is not None
    
    def test_execute_create_table(self):
        """Test creating a table."""
        self.executor.reset(self.work_dir)
        
        result = self.executor.execute("CREATE TABLE users (id INTEGER, name TEXT)")
        
        assert result["success"] is True
        assert "successfully" in result["stdout"]
        assert "users" in result["variables"]["tables"]
    
    def test_execute_insert_and_select(self):
        """Test inserting and selecting data."""
        self.executor.reset(self.work_dir)
        
        # Create table
        self.executor.execute("CREATE TABLE users (id INTEGER, name TEXT)")
        
        # Insert data
        result1 = self.executor.execute("INSERT INTO users VALUES (1, 'John')")
        assert result1["success"] is True
        
        # Select data
        result2 = self.executor.execute("SELECT * FROM users")
        assert result2["success"] is True
        assert len(result2["results"]) == 1
        assert result2["results"][0]["id"] == 1
        assert result2["results"][0]["name"] == "John"
    
    def test_execute_invalid_sql(self):
        """Test executing invalid SQL."""
        self.executor.reset(self.work_dir)
        
        result = self.executor.execute("INVALID SQL STATEMENT")
        
        assert result["success"] is False
        assert result["stderr"] != ""
        assert "error" in result
    
    def test_cleanup(self):
        """Test executor cleanup."""
        self.executor.reset(self.work_dir)
        
        # Connection should be open
        assert self.executor.connection is not None
        
        # Cleanup
        self.executor.cleanup()
        
        # Connection should be closed
        assert self.executor.connection is None


class TestInterCodeEnvironment:
    """Test cases for InterCodeEnvironment."""
    
    def setup_method(self):
        """Set up test fixtures."""
        self.task_info = InterCodeTaskInfo(
            task_id="test_task",
            task_type="python",
            query="Print hello world",
            gold="hello world"
        )
        
        self.config = {
            "timeout": 30,
            "max_output_length": 1000,
            "enable_persistence": True
        }
    
    def test_environment_initialization(self):
        """Test environment initialization."""
        env = InterCodeEnvironment(self.task_info, self.config)
        
        assert env.task_info == self.task_info
        assert env.config == self.config
        assert env.timeout == 30
        assert env.max_output_length == 1000
        assert env.work_dir is None
        assert len(env.execution_history) == 0
    
    def test_environment_reset(self):
        """Test environment reset."""
        env = InterCodeEnvironment(self.task_info, self.config)
        
        observation = env.reset()
        
        assert env.is_initialized()
        assert isinstance(observation, dict)
        assert observation["task_id"] == "test_task"
        assert observation["task_type"] == "python"
        assert observation["query"] == "Print hello world"
        assert observation["setup_complete"] is True
        assert env.work_dir is not None
        
        # Cleanup
        env.cleanup()
    
    def test_step_without_reset(self):
        """Test stepping without reset raises error."""
        env = InterCodeEnvironment(self.task_info, self.config)
        
        with pytest.raises(TaskExecutionError, match="not initialized"):
            env.step("print('hello')")
    
    def test_step_python_execution(self):
        """Test Python code execution in step."""
        env = InterCodeEnvironment(self.task_info, self.config)
        env.reset()
        
        observation, reward, done, info = env.step("print('hello world')")
        
        assert isinstance(observation, dict)
        assert observation["success"] is True
        assert "hello world" in observation["stdout"]
        assert reward > 0
        assert done is True  # Should be done because output matches gold
        assert info["success"] is True
        assert len(env.execution_history) == 1
        
        # Cleanup
        env.cleanup()
    
    def test_step_multiple_executions(self):
        """Test multiple executions with state persistence."""
        env = InterCodeEnvironment(self.task_info, self.config)
        env.reset()
        
        # First execution
        obs1, reward1, done1, info1 = env.step("x = 42")
        assert obs1["success"] is True
        assert not done1  # Not done yet
        
        # Second execution using previous variable
        obs2, reward2, done2, info2 = env.step("print(x)")
        assert obs2["success"] is True
        assert "42" in obs2["stdout"]
        assert len(env.execution_history) == 2
        
        # Cleanup
        env.cleanup()
    
    def test_success_determination(self):
        """Test success determination."""
        env = InterCodeEnvironment(self.task_info, self.config)
        env.reset()
        
        # Initially not successful
        assert env.success() is False
        
        # Execute code that produces expected output
        env.step("print('hello world')")
        
        # Should be successful now
        assert env.success() is True
        
        # Cleanup
        env.cleanup()
    
    def test_get_metrics(self):
        """Test metrics calculation."""
        env = InterCodeEnvironment(self.task_info, self.config)
        env.reset()
        
        # Initial metrics
        metrics = env.get_metrics()
        assert metrics["execution_steps"] == 0.0
        assert metrics["success_rate"] == 0.0
        
        # Execute some code
        env.step("print('hello')")
        env.step("x = 42")
        
        metrics = env.get_metrics()
        assert metrics["execution_steps"] == 2.0
        assert metrics["success_rate"] == 1.0  # Both executions successful
        
        # Cleanup
        env.cleanup()
    
    def test_bash_environment(self):
        """Test Bash environment."""
        task_info = InterCodeTaskInfo(
            task_id="bash_task",
            task_type="bash",
            query="List files",
            gold="test.txt"
        )
        
        env = InterCodeEnvironment(task_info, self.config)
        env.reset()
        
        # Create a file and list it
        env.step("touch test.txt")
        obs, reward, done, info = env.step("ls test.txt")
        
        assert obs["success"] is True
        assert "test.txt" in obs["stdout"]
        
        # Cleanup
        env.cleanup()
    
    def test_sql_environment(self):
        """Test SQL environment."""
        task_info = InterCodeTaskInfo(
            task_id="sql_task",
            task_type="sql",
            query="Create and query table",
            gold='[{"id": 1, "name": "John"}]'
        )
        
        env = InterCodeEnvironment(task_info, self.config)
        env.reset()
        
        # Create table and insert data
        env.step("CREATE TABLE users (id INTEGER, name TEXT)")
        env.step("INSERT INTO users VALUES (1, 'John')")
        obs, reward, done, info = env.step("SELECT * FROM users")
        
        assert obs["success"] is True
        assert "John" in obs["stdout"]
        
        # Cleanup
        env.cleanup()


class TestInterCodeTaskWrapper:
    """Test cases for InterCodeTaskWrapper."""
    
    def setup_method(self):
        """Set up test fixtures."""
        self.task_info = InterCodeTaskInfo(
            task_id="test_task",
            task_type="python",
            query="Print hello world",
            gold="hello world"
        )
        
        self.config = {"task_name": "test_task"}
    
    def test_task_wrapper_initialization(self):
        """Test task wrapper initialization."""
        wrapper = InterCodeTaskWrapper(self.task_info, self.config)
        
        assert wrapper.task_info == self.task_info
        assert wrapper.get_id() == "test_task"
        assert wrapper.config == self.config
        assert wrapper.environment is None
    
    def test_task_type(self):
        """Test task type."""
        wrapper = InterCodeTaskWrapper(self.task_info, self.config)
        
        assert wrapper.get_task_type() == TaskType.MULTI_TURN
    
    def test_required_capabilities(self):
        """Test required capabilities."""
        wrapper = InterCodeTaskWrapper(self.task_info, self.config)
        
        capabilities = wrapper.get_required_capabilities()
        
        assert "code_execution" in capabilities
        assert "interactive_environment" in capabilities
        assert "python_execution" in capabilities
        assert "variable_tracking" in capabilities
    
    def test_get_initial_context(self):
        """Test getting initial context."""
        wrapper = InterCodeTaskWrapper(self.task_info, self.config)
        
        context = wrapper.get_initial_context()
        
        assert "test_task" in context
        assert "PYTHON" in context
        assert "Print hello world" in context
        assert "hello world" in context
    
    def test_execute_turn(self):
        """Test executing a turn."""
        wrapper = InterCodeTaskWrapper(self.task_info, self.config)
        
        turn_data = TurnData(
            turn_number=1,
            input_context="print('hello world')",
            previous_actions=[],
            environment_state={}
        )
        
        result = wrapper.execute_turn(turn_data)
        
        assert isinstance(result, TurnResult)
        assert result.turn == 1
        assert result.action == "print('hello world')"
        assert result.reward > 0
        
        # Cleanup
        if wrapper.environment:
            wrapper.environment.cleanup()
    
    def test_should_continue(self):
        """Test should continue logic."""
        wrapper = InterCodeTaskWrapper(self.task_info, self.config)
        
        # Should continue if not done
        turn_result = TurnResult(
            turn=1, action="test", observation="test", reward=0.5,
            done=False, info={}, execution_time=1.0
        )
        assert wrapper.should_continue(turn_result) is True
        
        # Should not continue if done
        turn_result.done = True
        assert wrapper.should_continue(turn_result) is False
    
    def test_is_successful(self):
        """Test success determination."""
        wrapper = InterCodeTaskWrapper(self.task_info, self.config)
        
        # Test with environment
        mock_env = Mock()
        mock_env.success.return_value = True
        wrapper.environment = mock_env
        
        assert wrapper.is_successful([]) is True
        
        # Test without environment
        wrapper.environment = None
        turn_results = [
            TurnResult(1, "test", "test", 0.9, False, {}, 1.0)
        ]
        
        assert wrapper.is_successful(turn_results) is True


class TestInterCodeAdapter:
    """Test cases for InterCodeAdapter."""
    
    def test_adapter_info(self):
        """Test adapter information."""
        adapter = InterCodeAdapter({})
        info = adapter.get_adapter_info()
        
        assert info.name == "intercode_adapter"
        assert info.version == "1.0.0"
        assert TaskType.MULTI_TURN in info.supported_task_types
        assert "python" in info.required_dependencies
        assert "python_execution" in info.capabilities
        assert "interactive_environment" in info.capabilities
        assert info.metadata["supports_persistence"] is True
    
    def test_adapter_initialization_success(self):
        """Test successful adapter initialization."""
        adapter = InterCodeAdapter({})
        
        assert adapter.initialize()
        assert adapter.is_ready()
        assert adapter.get_status() == AdapterStatus.READY
    
    def test_create_environment(self):
        """Test creating environment."""
        adapter = InterCodeAdapter({})
        adapter.initialize()
        
        task_config = {
            "task_id": "test_task",
            "task_type": "python",
            "query": "Print hello",
            "gold": "hello"
        }
        
        env = adapter.create_environment(task_config)
        
        assert isinstance(env, InterCodeEnvironment)
        assert env.task_info.task_id == "test_task"
        
        # Cleanup
        env.cleanup()
    
    def test_create_environment_missing_fields(self):
        """Test creating environment with missing required fields."""
        adapter = InterCodeAdapter({})
        adapter.initialize()
        
        task_config = {"task_id": "test"}  # Missing required fields
        
        with pytest.raises(ConfigurationError, match="Missing required field"):
            adapter.create_environment(task_config)
    
    def test_create_environment_unsupported_type(self):
        """Test creating environment with unsupported task type."""
        adapter = InterCodeAdapter({"supported_types": ["python"]})
        adapter.initialize()
        
        task_config = {
            "task_id": "test_task",
            "task_type": "unsupported",
            "query": "Test",
            "gold": "test"
        }
        
        with pytest.raises(ConfigurationError, match="Unsupported task type"):
            adapter.create_environment(task_config)
    
    def test_load_tasks(self):
        """Test loading tasks."""
        adapter = InterCodeAdapter({})
        adapter.initialize()
        
        tasks = adapter.load_tasks()
        
        assert len(tasks) == 3  # python, bash, sql examples
        assert all(isinstance(task, InterCodeTaskWrapper) for task in tasks)
        
        task_types = [task.task_info.task_type for task in tasks]
        assert "python" in task_types
        assert "bash" in task_types
        assert "sql" in task_types
    
    def test_load_tasks_with_filter(self):
        """Test loading tasks with filter."""
        adapter = InterCodeAdapter({})
        adapter.initialize()
        
        tasks = adapter.load_tasks({"task_type": "python"})
        
        assert len(tasks) == 1
        assert tasks[0].task_info.task_type == "python"
    
    def test_convert_results_dict_format(self):
        """Test converting dictionary results."""
        adapter = InterCodeAdapter({})
        
        results = {
            "task_id": "test_task",
            "success": True,
            "execution_time": 2.5,
            "execution_steps": 3,
            "task_type": "python",
            "variables_count": 2
        }
        
        standardized = adapter.convert_results(results)
        
        assert standardized.task_id == "test_task"
        assert standardized.adapter_name == "intercode_adapter"
        assert standardized.success is True
        assert standardized.score == 1.0
        assert standardized.execution_time == 2.5
        assert standardized.turns == 3
        assert standardized.metadata["task_type"] == "python"
    
    def test_convert_results_partial_success(self):
        """Test converting results with partial success."""
        adapter = InterCodeAdapter({})
        
        results = {
            "task_id": "test_task",
            "success": False,
            "execution_steps": 5,
            "max_steps": 10
        }
        
        standardized = adapter.convert_results(results)
        
        assert standardized.success is False
        assert standardized.score == 0.25  # 5/10 * 0.5 partial credit
    
    def test_convert_results_unsupported_format(self):
        """Test converting unsupported result format."""
        adapter = InterCodeAdapter({})
        
        results = "unsupported string format"
        
        standardized = adapter.convert_results(results)
        
        assert standardized.task_id == "unknown"
        assert standardized.success is False
        assert standardized.score == 0.0
        assert "conversion_error" in standardized.metadata
    
    def test_create_task_info_valid(self):
        """Test creating task info with valid config."""
        adapter = InterCodeAdapter({})
        
        config = {
            "task_id": "test_task",
            "task_type": "python",
            "query": "Print hello",
            "gold": "hello",
            "setup": "import os",
            "metadata": {"difficulty": "easy"}
        }
        
        task_info = adapter._create_task_info(config)
        
        assert isinstance(task_info, InterCodeTaskInfo)
        assert task_info.task_id == "test_task"
        assert task_info.task_type == "python"
        assert task_info.setup == "import os"
    
    def test_adapter_not_ready_operations(self):
        """Test operations when adapter is not ready."""
        adapter = InterCodeAdapter({})
        # Don't initialize
        
        with pytest.raises(AdapterError, match="not initialized"):
            adapter.create_environment({"task_id": "test"})
        
        with pytest.raises(AdapterError, match="not initialized"):
            adapter.load_tasks()


class TestInterCodeIntegration:
    """Integration tests for InterCode adapter."""
    
    def test_end_to_end_python_workflow(self):
        """Test end-to-end Python workflow."""
        # Initialize adapter
        adapter = InterCodeAdapter({})
        assert adapter.initialize()
        
        # Load tasks
        tasks = adapter.load_tasks({"task_type": "python"})
        assert len(tasks) == 1
        
        task = tasks[0]
        assert isinstance(task, InterCodeTaskWrapper)
        
        # Get initial context
        context = task.get_initial_context()
        assert "python" in context.lower()
        
        # Create environment through adapter
        task_config = {
            "task_id": "python_test",
            "task_type": "python",
            "query": "Calculate 2 + 3 and print the result",
            "gold": "5"
        }
        
        env = adapter.create_environment(task_config)
        assert isinstance(env, InterCodeEnvironment)
        
        # Test environment operations
        observation = env.reset()
        assert observation["setup_complete"] is True
        
        # Execute Python code
        obs, reward, done, info = env.step("result = 2 + 3\nprint(result)")
        
        assert obs["success"] is True
        assert "5" in obs["stdout"]
        assert done is True  # Should be done because output matches gold
        assert env.success() is True
        
        # Convert final results
        final_result = {
            "task_id": "python_test",
            "success": env.success(),
            "execution_time": 1.0,
            "execution_steps": 1,
            "task_type": "python"
        }
        
        standardized = adapter.convert_results(final_result)
        assert standardized.success is True
        assert standardized.score == 1.0
        
        # Cleanup
        env.cleanup()
    
    def test_end_to_end_sql_workflow(self):
        """Test end-to-end SQL workflow."""
        # Initialize adapter
        adapter = InterCodeAdapter({})
        assert adapter.initialize()
        
        # Create SQL task
        task_config = {
            "task_id": "sql_test",
            "task_type": "sql",
            "query": "Create a users table and insert a user",
            "gold": '[{"id": 1, "name": "Alice"}]'
        }
        
        env = adapter.create_environment(task_config)
        env.reset()
        
        # Execute SQL commands
        env.step("CREATE TABLE users (id INTEGER, name TEXT)")
        env.step("INSERT INTO users VALUES (1, 'Alice')")
        obs, reward, done, info = env.step("SELECT * FROM users")
        
        assert obs["success"] is True
        assert "Alice" in obs["stdout"]
        
        # Cleanup
        env.cleanup()