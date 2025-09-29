"""
InterCode integration adapter for the Multi-Turn Evaluation Engine.

This module provides integration with InterCode for interactive code execution
evaluation tasks supporting Python, Bash, and SQL environments.
"""

import logging
import subprocess
import tempfile
import shutil
import json
import os
import sys
import sqlite3
from typing import Any, Dict, List, Optional, Union
from dataclasses import dataclass
from datetime import datetime
from pathlib import Path
from io import StringIO
import contextlib

from .adapters import BenchmarkAdapter, AdapterInfo, StandardizedResult, AdapterStatus
from .environment import UnifiedEnv, Observation, Action, Reward, Info
from .task_types import BaseTask, TaskType, MultiTurnTask, TurnData, TurnResult
from .exceptions import AdapterError, ConfigurationError, TaskExecutionError


@dataclass
class InterCodeTaskInfo:
    """Information about an InterCode task.
    
    Attributes:
        task_id: Unique identifier for the task
        task_type: Type of InterCode task (python, bash, sql)
        query: The task query/problem statement
        gold: Expected output or solution
        setup: Setup code or commands
        metadata: Additional task metadata
    """
    task_id: str
    task_type: str  # python, bash, sql
    query: str
    gold: str
    setup: Optional[str] = None
    metadata: Dict[str, Any] = None
    
    def __post_init__(self):
        if self.metadata is None:
            self.metadata = {}


class InterCodeEnvironment(UnifiedEnv):
    """Environment for InterCode tasks.
    
    This environment provides interactive execution for Python, Bash, and SQL
    tasks with state persistence and variable tracking.
    """
    
    def __init__(self, task_info: InterCodeTaskInfo, config: Dict[str, Any]):
        """Initialize the InterCode environment.
        
        Args:
            task_info: Information about the InterCode task
            config: Environment configuration
        """
        super().__init__(config)
        self.task_info = task_info
        self.work_dir = None
        self.execution_history = []
        self.variables = {}
        self.current_output = ""
        self.error_output = ""
        self.is_complete = False
        self._logger = logging.getLogger(f"{self.__class__.__module__}.{self.__class__.__name__}")
        
        # Configuration
        self.timeout = config.get("timeout", 30)
        self.max_output_length = config.get("max_output_length", 10000)
        self.enable_persistence = config.get("enable_persistence", True)
        
        # Task-specific setup
        self.executor = None
        self._setup_executor()
    
    def _setup_executor(self) -> None:
        """Set up the appropriate executor for the task type."""
        if self.task_info.task_type == "python":
            self.executor = PythonExecutor(self.config)
        elif self.task_info.task_type == "bash":
            self.executor = BashExecutor(self.config)
        elif self.task_info.task_type == "sql":
            self.executor = SQLExecutor(self.config)
        else:
            raise ConfigurationError(f"Unsupported task type: {self.task_info.task_type}")
    
    def reset(self) -> Observation:
        """Reset the environment to initial state.
        
        Returns:
            Initial observation with task information
        """
        try:
            # Clean up previous state
            self._cleanup()
            
            # Create work directory
            self.work_dir = Path(tempfile.mkdtemp(prefix="intercode_"))
            
            # Reset executor
            self.executor.reset(self.work_dir)
            
            # Run setup if provided
            if self.task_info.setup:
                setup_result = self.executor.execute(self.task_info.setup)
                if not setup_result["success"]:
                    self._logger.warning(f"Setup failed: {setup_result.get('error', 'Unknown error')}")
            
            # Reset state
            self.execution_history = []
            self.variables = {}
            self.current_output = ""
            self.error_output = ""
            self.is_complete = False
            
            # Create initial observation
            observation = {
                "task_id": self.task_info.task_id,
                "task_type": self.task_info.task_type,
                "query": self.task_info.query,
                "gold": self.task_info.gold,
                "work_dir": str(self.work_dir),
                "setup_complete": True,
                "variables": self.variables.copy(),
                "history_length": 0
            }
            
            self._mark_initialized()
            self._update_state(0.0, False, {"setup_complete": True})
            
            self._logger.info(f"InterCode environment initialized for {self.task_info.task_id}")
            return observation
            
        except Exception as e:
            error_msg = f"Failed to reset InterCode environment: {str(e)}"
            self._logger.error(error_msg)
            self._cleanup()
            raise TaskExecutionError(error_msg) from e
    
    def step(self, action: Action) -> tuple[Observation, Reward, bool, Info]:
        """Execute an action in the InterCode environment.
        
        Args:
            action: The code/command to execute
            
        Returns:
            Tuple of (observation, reward, done, info)
        """
        if not self._initialized:
            raise TaskExecutionError("Environment not initialized. Call reset() first.")
        
        start_time = datetime.now()
        
        try:
            # Execute the action
            result = self.executor.execute(action)
            
            # Update state
            self.current_output = result.get("stdout", "")
            self.error_output = result.get("stderr", "")
            
            # Store execution history
            execution_record = {
                "action": action,
                "result": result,
                "timestamp": start_time.isoformat(),
                "step": len(self.execution_history) + 1
            }
            self.execution_history.append(execution_record)
            
            # Update variables if available
            if "variables" in result:
                self.variables.update(result["variables"])
            
            # Check completion
            done = self._check_completion(result)
            self.is_complete = done
            
            # Calculate reward
            reward = self._calculate_reward(result, done)
            
            # Create observation
            observation = self._create_observation(result)
            
            # Create info
            execution_time = (datetime.now() - start_time).total_seconds()
            info = {
                "execution_time": execution_time,
                "success": result.get("success", False),
                "step_count": len(self.execution_history),
                "output_length": len(self.current_output),
                "error_length": len(self.error_output),
                "variables_count": len(self.variables),
                "done": done
            }
            
            self._update_state(reward, done, info)
            
            return observation, reward, done, info
            
        except Exception as e:
            error_msg = f"Failed to execute action: {str(e)}"
            self._logger.error(error_msg)
            
            # Return error observation
            observation = {
                "error": error_msg,
                "action": action,
                "timestamp": datetime.now().isoformat(),
                "task_id": self.task_info.task_id
            }
            
            info = {
                "error": error_msg,
                "execution_time": (datetime.now() - start_time).total_seconds()
            }
            
            return observation, 0.0, False, info
    
    def success(self) -> bool:
        """Check if the task was completed successfully.
        
        Returns:
            True if task completed successfully
        """
        if not self.execution_history:
            return False
        
        # Check if the last execution was successful and matches expected output
        last_result = self.execution_history[-1]["result"]
        
        if not last_result.get("success", False):
            return False
        
        # Compare output with gold standard
        output = last_result.get("stdout", "").strip()
        expected = self.task_info.gold.strip()
        
        return output == expected
    
    def info(self) -> Dict[str, Any]:
        """Get current environment information.
        
        Returns:
            Dictionary containing environment information
        """
        return {
            "task_id": self.task_info.task_id,
            "task_type": self.task_info.task_type,
            "work_dir": str(self.work_dir) if self.work_dir else None,
            "initialized": self._initialized,
            "execution_steps": len(self.execution_history),
            "variables_count": len(self.variables),
            "current_output_length": len(self.current_output),
            "error_output_length": len(self.error_output),
            "is_complete": self.is_complete,
            "success": self.success()
        }
    
    def get_metrics(self) -> Dict[str, float]:
        """Get current performance metrics.
        
        Returns:
            Dictionary of performance metrics
        """
        if not self.execution_history:
            return {
                "execution_steps": 0.0,
                "success_rate": 0.0,
                "error_rate": 0.0,
                "completion_rate": 0.0
            }
        
        successful_steps = sum(1 for h in self.execution_history 
                              if h["result"].get("success", False))
        error_steps = sum(1 for h in self.execution_history 
                         if not h["result"].get("success", False))
        
        total_steps = len(self.execution_history)
        success_rate = successful_steps / total_steps if total_steps > 0 else 0.0
        error_rate = error_steps / total_steps if total_steps > 0 else 0.0
        completion_rate = 1.0 if self.is_complete else 0.0
        
        return {
            "execution_steps": float(total_steps),
            "success_rate": success_rate,
            "error_rate": error_rate,
            "completion_rate": completion_rate,
            "variables_count": float(len(self.variables))
        }
    
    def cleanup(self) -> None:
        """Clean up environment resources."""
        self._cleanup()
    
    def _check_completion(self, result: Dict[str, Any]) -> bool:
        """Check if the task is complete based on the result.
        
        Args:
            result: Execution result
            
        Returns:
            True if task is complete
        """
        # Task is complete if output matches expected result
        if result.get("success", False):
            output = result.get("stdout", "").strip()
            expected = self.task_info.gold.strip()
            return output == expected
        
        return False
    
    def _calculate_reward(self, result: Dict[str, Any], done: bool) -> float:
        """Calculate reward for the execution result.
        
        Args:
            result: Execution result
            done: Whether task is complete
            
        Returns:
            Reward value
        """
        if not result.get("success", False):
            return 0.0
        
        # Base reward for successful execution
        reward = 0.2
        
        # Bonus for producing output
        if result.get("stdout"):
            reward += 0.2
        
        # Large bonus for completion
        if done:
            reward += 0.6
        
        return min(reward, 1.0)
    
    def _create_observation(self, result: Dict[str, Any]) -> Observation:
        """Create observation from execution result.
        
        Args:
            result: Execution result
            
        Returns:
            Observation for the agent
        """
        observation = {
            "task_id": self.task_info.task_id,
            "task_type": self.task_info.task_type,
            "stdout": result.get("stdout", ""),
            "stderr": result.get("stderr", ""),
            "success": result.get("success", False),
            "variables": self.variables.copy(),
            "step_count": len(self.execution_history),
            "is_complete": self.is_complete,
            "timestamp": datetime.now().isoformat()
        }
        
        # Truncate output if too long
        if len(observation["stdout"]) > self.max_output_length:
            observation["stdout"] = observation["stdout"][:self.max_output_length] + "...[truncated]"
        
        if len(observation["stderr"]) > self.max_output_length:
            observation["stderr"] = observation["stderr"][:self.max_output_length] + "...[truncated]"
        
        return observation
    
    def _cleanup(self) -> None:
        """Clean up work directory and resources."""
        try:
            if self.executor:
                self.executor.cleanup()
            
            if self.work_dir and self.work_dir.exists():
                shutil.rmtree(self.work_dir, ignore_errors=True)
                self._logger.info(f"Cleaned up work directory: {self.work_dir}")
            
        except Exception as e:
            self._logger.warning(f"Cleanup failed: {e}")
        finally:
            self.work_dir = None


class BaseExecutor:
    """Base class for code executors."""
    
    def __init__(self, config: Dict[str, Any]):
        self.config = config
        self.timeout = config.get("timeout", 30)
        self._logger = logging.getLogger(f"{self.__class__.__module__}.{self.__class__.__name__}")
    
    def reset(self, work_dir: Path) -> None:
        """Reset the executor state."""
        self.work_dir = work_dir
    
    def execute(self, code: str) -> Dict[str, Any]:
        """Execute code and return result."""
        raise NotImplementedError
    
    def cleanup(self) -> None:
        """Clean up executor resources."""
        pass


class PythonExecutor(BaseExecutor):
    """Executor for Python code."""
    
    def __init__(self, config: Dict[str, Any]):
        super().__init__(config)
        self.globals_dict = {}
        self.locals_dict = {}
    
    def reset(self, work_dir: Path) -> None:
        """Reset Python execution state."""
        super().reset(work_dir)
        self.globals_dict = {"__builtins__": __builtins__}
        self.locals_dict = {}
        
        # Add work directory to Python path
        if str(work_dir) not in sys.path:
            sys.path.insert(0, str(work_dir))
    
    def execute(self, code: str) -> Dict[str, Any]:
        """Execute Python code.
        
        Args:
            code: Python code to execute
            
        Returns:
            Execution result dictionary
        """
        try:
            # Capture stdout and stderr
            old_stdout = sys.stdout
            old_stderr = sys.stderr
            
            stdout_capture = StringIO()
            stderr_capture = StringIO()
            
            sys.stdout = stdout_capture
            sys.stderr = stderr_capture
            
            try:
                # Change to work directory
                old_cwd = os.getcwd()
                os.chdir(self.work_dir)
                
                # Execute code
                exec(code, self.globals_dict, self.locals_dict)
                
                # Get output
                stdout_output = stdout_capture.getvalue()
                stderr_output = stderr_capture.getvalue()
                
                # Extract variables (excluding builtins)
                variables = {k: str(v) for k, v in self.locals_dict.items() 
                           if not k.startswith('__')}
                
                return {
                    "success": True,
                    "stdout": stdout_output,
                    "stderr": stderr_output,
                    "variables": variables
                }
                
            finally:
                os.chdir(old_cwd)
                sys.stdout = old_stdout
                sys.stderr = old_stderr
                
        except Exception as e:
            return {
                "success": False,
                "stdout": stdout_capture.getvalue() if 'stdout_capture' in locals() else "",
                "stderr": str(e),
                "variables": {},
                "error": str(e)
            }


class BashExecutor(BaseExecutor):
    """Executor for Bash commands."""
    
    def __init__(self, config: Dict[str, Any]):
        super().__init__(config)
        self.env_vars = os.environ.copy()
    
    def reset(self, work_dir: Path) -> None:
        """Reset Bash execution state."""
        super().reset(work_dir)
        self.env_vars = os.environ.copy()
        self.env_vars["PWD"] = str(work_dir)
    
    def execute(self, command: str) -> Dict[str, Any]:
        """Execute Bash command.
        
        Args:
            command: Bash command to execute
            
        Returns:
            Execution result dictionary
        """
        try:
            result = subprocess.run(
                command,
                shell=True,
                capture_output=True,
                text=True,
                timeout=self.timeout,
                cwd=self.work_dir,
                env=self.env_vars
            )
            
            # Update environment variables if command was successful
            if result.returncode == 0:
                # Try to capture environment changes (simplified)
                env_result = subprocess.run(
                    "env",
                    shell=True,
                    capture_output=True,
                    text=True,
                    cwd=self.work_dir,
                    env=self.env_vars
                )
                
                if env_result.returncode == 0:
                    for line in env_result.stdout.split('\n'):
                        if '=' in line:
                            key, value = line.split('=', 1)
                            self.env_vars[key] = value
            
            return {
                "success": result.returncode == 0,
                "stdout": result.stdout,
                "stderr": result.stderr,
                "returncode": result.returncode,
                "variables": dict(self.env_vars)
            }
            
        except subprocess.TimeoutExpired:
            return {
                "success": False,
                "stdout": "",
                "stderr": "Command timed out",
                "returncode": -1,
                "variables": {},
                "error": "Timeout"
            }
        except Exception as e:
            return {
                "success": False,
                "stdout": "",
                "stderr": str(e),
                "returncode": -1,
                "variables": {},
                "error": str(e)
            }


class SQLExecutor(BaseExecutor):
    """Executor for SQL commands."""
    
    def __init__(self, config: Dict[str, Any]):
        super().__init__(config)
        self.db_path = None
        self.connection = None
    
    def reset(self, work_dir: Path) -> None:
        """Reset SQL execution state."""
        super().reset(work_dir)
        
        # Close existing connection
        if self.connection:
            self.connection.close()
        
        # Create new database
        self.db_path = work_dir / "intercode.db"
        self.connection = sqlite3.connect(str(self.db_path))
        self.connection.row_factory = sqlite3.Row  # Enable column access by name
    
    def execute(self, sql: str) -> Dict[str, Any]:
        """Execute SQL command.
        
        Args:
            sql: SQL command to execute
            
        Returns:
            Execution result dictionary
        """
        try:
            cursor = self.connection.cursor()
            
            # Execute SQL
            cursor.execute(sql)
            
            # Get results
            if sql.strip().upper().startswith(('SELECT', 'PRAGMA')):
                rows = cursor.fetchall()
                # Convert rows to list of dictionaries
                results = [dict(row) for row in rows]
                stdout = json.dumps(results, indent=2) if results else "No results"
            else:
                # For INSERT, UPDATE, DELETE, etc.
                self.connection.commit()
                stdout = f"Query executed successfully. Rows affected: {cursor.rowcount}"
                results = []
            
            # Get table information for variables
            cursor.execute("SELECT name FROM sqlite_master WHERE type='table';")
            tables = [row[0] for row in cursor.fetchall()]
            
            return {
                "success": True,
                "stdout": stdout,
                "stderr": "",
                "results": results,
                "variables": {"tables": tables}
            }
            
        except sqlite3.Error as e:
            return {
                "success": False,
                "stdout": "",
                "stderr": str(e),
                "results": [],
                "variables": {},
                "error": str(e)
            }
        except Exception as e:
            return {
                "success": False,
                "stdout": "",
                "stderr": str(e),
                "results": [],
                "variables": {},
                "error": str(e)
            }
    
    def cleanup(self) -> None:
        """Clean up SQL resources."""
        if self.connection:
            self.connection.close()
            self.connection = None


class InterCodeTaskWrapper(MultiTurnTask):
    """Wrapper for InterCode tasks."""
    
    def __init__(self, task_info: InterCodeTaskInfo, config: Dict[str, Any]):
        """Initialize the task wrapper.
        
        Args:
            task_info: InterCode task information
            config: Task configuration
        """
        super().__init__(task_info.task_id, config)
        self.task_info = task_info
        self.environment = None
    
    def get_task_type(self) -> TaskType:
        """Get the task type.
        
        Returns:
            TaskType.MULTI_TURN
        """
        return TaskType.MULTI_TURN
    
    def validate_config(self, config: Dict[str, Any]) -> bool:
        """Validate task configuration.
        
        Args:
            config: Configuration to validate
            
        Returns:
            True if valid
        """
        if not isinstance(config, dict):
            raise ConfigurationError("Configuration must be a dictionary")
        
        return True
    
    def get_required_capabilities(self) -> List[str]:
        """Get required capabilities.
        
        Returns:
            List of required capabilities
        """
        capabilities = ["code_execution", "interactive_environment"]
        
        if self.task_info.task_type == "python":
            capabilities.extend(["python_execution", "variable_tracking"])
        elif self.task_info.task_type == "bash":
            capabilities.extend(["bash_execution", "environment_variables"])
        elif self.task_info.task_type == "sql":
            capabilities.extend(["sql_execution", "database_operations"])
        
        return capabilities
    
    def execute_turn(self, turn_data: TurnData) -> TurnResult:
        """Execute a single turn.
        
        Args:
            turn_data: Data for the current turn
            
        Returns:
            TurnResult containing the turn outcome
        """
        if not self.environment:
            self.environment = InterCodeEnvironment(self.task_info, self.config)
            if turn_data.turn_number == 1:
                self.environment.reset()
        
        # Extract action from turn data
        action = turn_data.input_context
        
        # Execute step
        observation, reward, done, info = self.environment.step(action)
        
        return TurnResult(
            turn=turn_data.turn_number,
            action=action,
            observation=observation,
            reward=reward,
            done=done,
            info=info,
            execution_time=info.get("execution_time", 0.0)
        )
    
    def should_continue(self, turn_result: TurnResult) -> bool:
        """Determine if evaluation should continue.
        
        Args:
            turn_result: Result of the most recent turn
            
        Returns:
            True if evaluation should continue
        """
        return not turn_result.done
    
    def get_initial_context(self) -> str:
        """Get initial context for the first turn.
        
        Returns:
            Initial context string
        """
        return f"""
InterCode Task: {self.task_info.task_id}
Task Type: {self.task_info.task_type.upper()}

Query: {self.task_info.query}

Expected Output: {self.task_info.gold}

You can execute {self.task_info.task_type} code interactively. 
The environment maintains state between executions.
Your goal is to produce the expected output.
"""
    
    def is_successful(self, turn_results: List[TurnResult]) -> bool:
        """Determine if the task was successful.
        
        Args:
            turn_results: List of all turn results
            
        Returns:
            True if task was successful
        """
        # Check if environment indicates success
        if self.environment:
            return self.environment.success()
        
        # Fallback: check if any turn was successful
        if not turn_results:
            return False
        
        return any(tr.reward > 0.8 for tr in turn_results)


class InterCodeAdapter(BenchmarkAdapter):
    """Adapter for InterCode integration."""
    
    def __init__(self, config: Dict[str, Any]):
        """Initialize the InterCode adapter.
        
        Args:
            config: Adapter configuration
        """
        super().__init__(config)
        self.supported_types = config.get("supported_types", ["python", "bash", "sql"])
        self.tasks_cache = {}
    
    def get_adapter_info(self) -> AdapterInfo:
        """Get adapter information.
        
        Returns:
            AdapterInfo describing the InterCode adapter
        """
        return AdapterInfo(
            name="intercode_adapter",
            version="1.0.0",
            description="Adapter for InterCode interactive code execution evaluation",
            supported_task_types=[TaskType.MULTI_TURN],
            required_dependencies=["python", "sqlite3"],
            supported_formats=["json", "jsonl"],
            capabilities=[
                "python_execution",
                "bash_execution", 
                "sql_execution",
                "interactive_environment",
                "variable_tracking",
                "state_persistence",
                "stdout_stderr_collection"
            ],
            metadata={
                "benchmark_type": "interactive_coding",
                "supports_persistence": True,
                "execution_types": self.supported_types
            }
        )
    
    def initialize(self) -> bool:
        """Initialize the adapter.
        
        Returns:
            True if initialization was successful
        """
        try:
            self._set_status(AdapterStatus.INITIALIZING)
            
            # Check Python availability
            try:
                import sys
                self._logger.info(f"Python {sys.version} available")
            except Exception as e:
                raise AdapterError(f"Python not available: {e}")
            
            # Check SQLite availability if SQL tasks are supported
            if "sql" in self.supported_types:
                try:
                    import sqlite3
                    self._logger.info(f"SQLite {sqlite3.sqlite_version} available")
                except Exception as e:
                    raise AdapterError(f"SQLite not available: {e}")
            
            self._logger.info("InterCode adapter initialized successfully")
            self._set_status(AdapterStatus.READY)
            return True
            
        except Exception as e:
            error_msg = f"Failed to initialize InterCode adapter: {str(e)}"
            self._set_status(AdapterStatus.ERROR, error_msg)
            return False
    
    def create_environment(self, task_config: Dict[str, Any]) -> UnifiedEnv:
        """Create environment for an InterCode task.
        
        Args:
            task_config: Task configuration
            
        Returns:
            InterCodeEnvironment instance
        """
        if not self.is_ready():
            raise AdapterError("Adapter not initialized")
        
        # Extract task info from config
        task_info = self._create_task_info(task_config)
        
        return InterCodeEnvironment(task_info, task_config)
    
    def load_tasks(self, task_filter: Optional[Dict[str, Any]] = None) -> List[BaseTask]:
        """Load InterCode tasks.
        
        Args:
            task_filter: Optional filter criteria
            
        Returns:
            List of InterCode tasks
        """
        if not self.is_ready():
            raise AdapterError("Adapter not initialized")
        
        # For now, return mock tasks for each supported type
        # In a real implementation, this would load from the InterCode dataset
        tasks = []
        
        mock_tasks = [
            {
                "task_id": "python_example_1",
                "task_type": "python",
                "query": "Create a list of numbers from 1 to 5 and print their sum",
                "gold": "15",
                "setup": None
            },
            {
                "task_id": "bash_example_1", 
                "task_type": "bash",
                "query": "List all .py files in the current directory",
                "gold": "",  # Would be filled with actual expected output
                "setup": "touch test1.py test2.py test3.txt"
            },
            {
                "task_id": "sql_example_1",
                "task_type": "sql", 
                "query": "Create a table 'users' with id and name columns, insert a user, then select all users",
                "gold": '[{"id": 1, "name": "John"}]',
                "setup": None
            }
        ]
        
        # Filter by task type if specified
        if task_filter and "task_type" in task_filter:
            target_type = task_filter["task_type"]
            mock_tasks = [t for t in mock_tasks if t["task_type"] == target_type]
        
        for task_data in mock_tasks:
            if task_data["task_type"] in self.supported_types:
                task_info = InterCodeTaskInfo(**task_data)
                task_wrapper = InterCodeTaskWrapper(task_info, {
                    "task_name": task_data["task_id"],
                    "adapter": "intercode"
                })
                tasks.append(task_wrapper)
        
        return tasks
    
    def convert_results(self, results: Any) -> StandardizedResult:
        """Convert InterCode results to standardized format.
        
        Args:
            results: Raw results from InterCode evaluation
            
        Returns:
            StandardizedResult object
        """
        if isinstance(results, dict):
            task_id = results.get("task_id", "unknown")
            success = results.get("success", False)
            
            # Calculate score based on success and execution efficiency
            score = 1.0 if success else 0.0
            if not success and "execution_steps" in results:
                # Partial credit based on progress
                max_steps = results.get("max_steps", 10)
                steps = min(results["execution_steps"], max_steps)
                score = steps / max_steps * 0.5
            
            return StandardizedResult(
                task_id=task_id,
                adapter_name="intercode_adapter",
                success=success,
                score=score,
                execution_time=results.get("execution_time", 0.0),
                turns=results.get("execution_steps", 1),
                tokens_used=results.get("tokens_used", 0),
                cost=results.get("cost", 0.0),
                metadata={
                    "task_type": results.get("task_type", "unknown"),
                    "execution_steps": results.get("execution_steps", 0),
                    "variables_count": results.get("variables_count", 0),
                    "output_length": results.get("output_length", 0)
                },
                raw_result=results
            )
        else:
            return StandardizedResult(
                task_id="unknown",
                adapter_name="intercode_adapter",
                success=False,
                score=0.0,
                execution_time=0.0,
                turns=1,
                tokens_used=0,
                cost=0.0,
                metadata={"conversion_error": "Unsupported result format"},
                raw_result=results
            )
    
    def _create_task_info(self, task_config: Dict[str, Any]) -> InterCodeTaskInfo:
        """Create InterCodeTaskInfo from configuration.
        
        Args:
            task_config: Task configuration
            
        Returns:
            InterCodeTaskInfo object
        """
        required_fields = ["task_id", "task_type", "query", "gold"]
        
        for field in required_fields:
            if field not in task_config:
                raise ConfigurationError(f"Missing required field: {field}")
        
        if task_config["task_type"] not in self.supported_types:
            raise ConfigurationError(f"Unsupported task type: {task_config['task_type']}")
        
        return InterCodeTaskInfo(
            task_id=task_config["task_id"],
            task_type=task_config["task_type"],
            query=task_config["query"],
            gold=task_config["gold"],
            setup=task_config.get("setup"),
            metadata=task_config.get("metadata", {})
        )