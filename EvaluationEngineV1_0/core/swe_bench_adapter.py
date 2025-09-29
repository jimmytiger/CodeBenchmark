"""
SWE-bench integration adapter for the Multi-Turn Evaluation Engine.

This module provides integration with SWE-bench for software engineering
evaluation tasks involving git operations, dependency installation, and test execution.
"""

import logging
import subprocess
import tempfile
import shutil
import json
import os
import re
from typing import Any, Dict, List, Optional, Union
from dataclasses import dataclass
from datetime import datetime
from pathlib import Path

from .adapters import BenchmarkAdapter, AdapterInfo, StandardizedResult, AdapterStatus
from .environment import UnifiedEnv, Observation, Action, Reward, Info
from .task_types import BaseTask, TaskType, MultiTurnTask, TurnData, TurnResult
from .exceptions import AdapterError, ConfigurationError, TaskExecutionError


@dataclass
class SWEBenchTaskInfo:
    """Information about a SWE-bench task.
    
    Attributes:
        instance_id: Unique identifier for the task instance
        repo: Repository name (e.g., "django/django")
        base_commit: Base commit hash
        patch: The patch to apply
        test_patch: Test patch for validation
        problem_statement: Description of the problem
        hints_text: Optional hints for solving the problem
        created_at: When the task was created
        version: Version of the task format
        environment: Environment setup information
    """
    instance_id: str
    repo: str
    base_commit: str
    patch: str
    test_patch: str
    problem_statement: str
    hints_text: str
    created_at: str
    version: str
    environment: Dict[str, Any]


class SWEBenchEnvironment(UnifiedEnv):
    """Environment for SWE-bench tasks.
    
    This environment manages git repositories, dependency installation,
    and test execution for software engineering tasks.
    """
    
    def __init__(self, task_info: SWEBenchTaskInfo, config: Dict[str, Any]):
        """Initialize the SWE-bench environment.
        
        Args:
            task_info: Information about the SWE-bench task
            config: Environment configuration
        """
        super().__init__(config)
        self.task_info = task_info
        self.work_dir = None
        self.repo_dir = None
        self.original_cwd = os.getcwd()
        self.test_results = []
        self.modifications = []
        self.git_commits = []
        self._logger = logging.getLogger(f"{self.__class__.__module__}.{self.__class__.__name__}")
        
        # Configuration
        self.timeout = config.get("timeout", 300)  # 5 minutes default
        self.max_file_size = config.get("max_file_size", 1024 * 1024)  # 1MB default
        self.allowed_commands = config.get("allowed_commands", [
            "git", "python", "pip", "pytest", "python3", "ls", "cat", "grep", "find"
        ])
    
    def reset(self) -> Observation:
        """Reset the environment by setting up the repository.
        
        Returns:
            Initial observation with problem statement and setup info
        """
        try:
            # Clean up previous work directory if it exists
            self._cleanup()
            
            # Create new work directory
            self.work_dir = Path(tempfile.mkdtemp(prefix="swe_bench_"))
            self.repo_dir = self.work_dir / "repo"
            
            # Clone repository and checkout base commit
            self._setup_repository()
            
            # Install dependencies
            self._install_dependencies()
            
            # Create initial observation
            observation = {
                "problem_statement": self.task_info.problem_statement,
                "hints": self.task_info.hints_text,
                "repo": self.task_info.repo,
                "base_commit": self.task_info.base_commit,
                "work_dir": str(self.work_dir),
                "repo_dir": str(self.repo_dir),
                "instance_id": self.task_info.instance_id,
                "available_commands": self.allowed_commands,
                "setup_complete": True
            }
            
            self._mark_initialized()
            self._update_state(0.0, False, {"setup_complete": True})
            
            self._logger.info(f"SWE-bench environment initialized for {self.task_info.instance_id}")
            return observation
            
        except Exception as e:
            error_msg = f"Failed to reset SWE-bench environment: {str(e)}"
            self._logger.error(error_msg)
            self._cleanup()
            raise TaskExecutionError(error_msg) from e
    
    def step(self, action: Action) -> tuple[Observation, Reward, bool, Info]:
        """Execute an action in the SWE-bench environment.
        
        Args:
            action: The action to execute (command, file modification, etc.)
            
        Returns:
            Tuple of (observation, reward, done, info)
        """
        if not self._initialized:
            raise TaskExecutionError("Environment not initialized. Call reset() first.")
        
        start_time = datetime.now()
        
        try:
            # Parse and validate action
            parsed_action = self._parse_action(action)
            
            # Execute the action
            result = self._execute_action(parsed_action)
            
            # Check if task is complete
            done = self._check_completion()
            
            # Calculate reward
            reward = self._calculate_reward(result, done)
            
            # Create observation
            observation = self._create_observation(result)
            
            # Create info
            execution_time = (datetime.now() - start_time).total_seconds()
            info = {
                "action_type": parsed_action.get("type", "unknown"),
                "execution_time": execution_time,
                "result": result,
                "done": done,
                "work_dir": str(self.work_dir),
                "modifications_count": len(self.modifications),
                "test_results": self.test_results[-1] if self.test_results else None
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
                "timestamp": datetime.now().isoformat()
            }
            
            info = {
                "error": error_msg,
                "execution_time": (datetime.now() - start_time).total_seconds()
            }
            
            return observation, 0.0, False, info
    
    def success(self) -> bool:
        """Check if the task was completed successfully.
        
        Returns:
            True if all tests pass and the solution is correct
        """
        if not self.test_results:
            return False
        
        # Check the most recent test results
        latest_results = self.test_results[-1]
        return (latest_results.get("passed", 0) > 0 and 
                latest_results.get("failed", 0) == 0 and
                latest_results.get("errors", 0) == 0)
    
    def info(self) -> Dict[str, Any]:
        """Get current environment information.
        
        Returns:
            Dictionary containing environment information
        """
        return {
            "instance_id": self.task_info.instance_id,
            "repo": self.task_info.repo,
            "base_commit": self.task_info.base_commit,
            "work_dir": str(self.work_dir) if self.work_dir else None,
            "initialized": self._initialized,
            "modifications_count": len(self.modifications),
            "test_runs": len(self.test_results),
            "latest_test_results": self.test_results[-1] if self.test_results else None,
            "git_commits": len(self.git_commits),
            "success": self.success()
        }
    
    def get_metrics(self) -> Dict[str, float]:
        """Get current performance metrics.
        
        Returns:
            Dictionary of performance metrics
        """
        if not self.test_results:
            return {
                "test_success_rate": 0.0,
                "modifications_count": float(len(self.modifications)),
                "test_runs": 0.0,
                "completion_rate": 0.0
            }
        
        latest_results = self.test_results[-1]
        total_tests = latest_results.get("total", 0)
        passed_tests = latest_results.get("passed", 0)
        
        success_rate = passed_tests / total_tests if total_tests > 0 else 0.0
        completion_rate = 1.0 if self.success() else 0.0
        
        return {
            "test_success_rate": success_rate,
            "modifications_count": float(len(self.modifications)),
            "test_runs": float(len(self.test_results)),
            "completion_rate": completion_rate,
            "passed_tests": float(passed_tests),
            "total_tests": float(total_tests)
        }
    
    def cleanup(self) -> None:
        """Clean up environment resources."""
        self._cleanup()
    
    def _setup_repository(self) -> None:
        """Set up the git repository for the task."""
        try:
            # Clone the repository
            repo_url = f"https://github.com/{self.task_info.repo}.git"
            
            self._logger.info(f"Cloning repository {repo_url}")
            result = subprocess.run([
                "git", "clone", repo_url, str(self.repo_dir)
            ], capture_output=True, text=True, timeout=self.timeout)
            
            if result.returncode != 0:
                raise AdapterError(f"Failed to clone repository: {result.stderr}")
            
            # Change to repo directory
            os.chdir(self.repo_dir)
            
            # Checkout base commit
            self._logger.info(f"Checking out base commit {self.task_info.base_commit}")
            result = subprocess.run([
                "git", "checkout", self.task_info.base_commit
            ], capture_output=True, text=True, timeout=30)
            
            if result.returncode != 0:
                raise AdapterError(f"Failed to checkout base commit: {result.stderr}")
            
            # Create a new branch for modifications
            branch_name = f"swe_bench_{self.task_info.instance_id}"
            result = subprocess.run([
                "git", "checkout", "-b", branch_name
            ], capture_output=True, text=True, timeout=30)
            
            if result.returncode != 0:
                self._logger.warning(f"Failed to create branch: {result.stderr}")
            
        except subprocess.TimeoutExpired:
            raise AdapterError("Repository setup timed out")
        except Exception as e:
            raise AdapterError(f"Repository setup failed: {str(e)}") from e
    
    def _install_dependencies(self) -> None:
        """Install project dependencies."""
        try:
            # Look for common dependency files
            dependency_files = [
                "requirements.txt",
                "setup.py",
                "pyproject.toml",
                "environment.yml"
            ]
            
            for dep_file in dependency_files:
                dep_path = self.repo_dir / dep_file
                if dep_path.exists():
                    self._logger.info(f"Installing dependencies from {dep_file}")
                    
                    if dep_file == "requirements.txt":
                        result = subprocess.run([
                            "pip", "install", "-r", str(dep_path)
                        ], capture_output=True, text=True, timeout=self.timeout)
                    elif dep_file == "setup.py":
                        result = subprocess.run([
                            "pip", "install", "-e", "."
                        ], capture_output=True, text=True, timeout=self.timeout, cwd=self.repo_dir)
                    else:
                        continue  # Skip other formats for now
                    
                    if result.returncode != 0:
                        self._logger.warning(f"Dependency installation warning: {result.stderr}")
                    else:
                        self._logger.info("Dependencies installed successfully")
                    break
            
        except subprocess.TimeoutExpired:
            self._logger.warning("Dependency installation timed out")
        except Exception as e:
            self._logger.warning(f"Dependency installation failed: {str(e)}")
    
    def _parse_action(self, action: Action) -> Dict[str, Any]:
        """Parse an action into a structured format.
        
        Args:
            action: The action to parse
            
        Returns:
            Parsed action dictionary
        """
        if isinstance(action, str):
            # Try to parse as JSON first
            try:
                parsed = json.loads(action)
                if isinstance(parsed, dict):
                    return parsed
            except json.JSONDecodeError:
                pass
            
            # Parse as command
            return {
                "type": "command",
                "command": action.strip()
            }
        
        elif isinstance(action, dict):
            return action
        
        else:
            return {
                "type": "unknown",
                "raw_action": action
            }
    
    def _execute_action(self, action: Dict[str, Any]) -> Dict[str, Any]:
        """Execute a parsed action.
        
        Args:
            action: Parsed action dictionary
            
        Returns:
            Execution result
        """
        action_type = action.get("type", "unknown")
        
        if action_type == "command":
            return self._execute_command(action["command"])
        elif action_type == "file_edit":
            return self._execute_file_edit(action)
        elif action_type == "run_tests":
            return self._execute_tests(action.get("test_command", "pytest"))
        else:
            return {
                "success": False,
                "error": f"Unknown action type: {action_type}",
                "action": action
            }
    
    def _execute_command(self, command: str) -> Dict[str, Any]:
        """Execute a shell command.
        
        Args:
            command: Command to execute
            
        Returns:
            Command execution result
        """
        try:
            # Validate command
            if not self._is_command_allowed(command):
                return {
                    "success": False,
                    "error": f"Command not allowed: {command}",
                    "stdout": "",
                    "stderr": ""
                }
            
            # Execute command in repo directory
            result = subprocess.run(
                command,
                shell=True,
                capture_output=True,
                text=True,
                timeout=self.timeout,
                cwd=self.repo_dir
            )
            
            return {
                "success": result.returncode == 0,
                "returncode": result.returncode,
                "stdout": result.stdout,
                "stderr": result.stderr,
                "command": command
            }
            
        except subprocess.TimeoutExpired:
            return {
                "success": False,
                "error": "Command timed out",
                "command": command,
                "stdout": "",
                "stderr": ""
            }
        except Exception as e:
            return {
                "success": False,
                "error": str(e),
                "command": command,
                "stdout": "",
                "stderr": ""
            }
    
    def _execute_file_edit(self, action: Dict[str, Any]) -> Dict[str, Any]:
        """Execute a file edit action.
        
        Args:
            action: File edit action
            
        Returns:
            Edit execution result
        """
        try:
            file_path = action.get("file_path")
            content = action.get("content")
            operation = action.get("operation", "write")  # write, append, patch
            
            if not file_path:
                return {
                    "success": False,
                    "error": "No file path specified"
                }
            
            # Resolve file path relative to repo directory
            full_path = self.repo_dir / file_path
            
            # Ensure file is within repo directory (security check)
            try:
                full_path.resolve().relative_to(self.repo_dir.resolve())
            except ValueError:
                return {
                    "success": False,
                    "error": "File path outside repository"
                }
            
            # Check file size limits
            if content and len(content) > self.max_file_size:
                return {
                    "success": False,
                    "error": f"Content too large (max {self.max_file_size} bytes)"
                }
            
            # Backup original file if it exists
            backup_content = None
            if full_path.exists():
                backup_content = full_path.read_text()
            
            # Perform the operation
            if operation == "write":
                full_path.parent.mkdir(parents=True, exist_ok=True)
                full_path.write_text(content)
            elif operation == "append":
                full_path.parent.mkdir(parents=True, exist_ok=True)
                with open(full_path, "a") as f:
                    f.write(content)
            else:
                return {
                    "success": False,
                    "error": f"Unsupported operation: {operation}"
                }
            
            # Record modification
            modification = {
                "file_path": file_path,
                "operation": operation,
                "timestamp": datetime.now().isoformat(),
                "backup_content": backup_content,
                "new_content": content if operation == "write" else None
            }
            self.modifications.append(modification)
            
            return {
                "success": True,
                "file_path": file_path,
                "operation": operation,
                "modification_id": len(self.modifications) - 1
            }
            
        except Exception as e:
            return {
                "success": False,
                "error": str(e),
                "file_path": action.get("file_path")
            }
    
    def _execute_tests(self, test_command: str = "pytest") -> Dict[str, Any]:
        """Execute tests and parse results.
        
        Args:
            test_command: Test command to run
            
        Returns:
            Test execution results
        """
        try:
            # Run tests
            result = subprocess.run(
                test_command,
                shell=True,
                capture_output=True,
                text=True,
                timeout=self.timeout,
                cwd=self.repo_dir
            )
            
            # Parse test results
            test_results = self._parse_test_output(result.stdout, result.stderr)
            test_results.update({
                "returncode": result.returncode,
                "command": test_command,
                "timestamp": datetime.now().isoformat()
            })
            
            # Store results
            self.test_results.append(test_results)
            
            return {
                "success": result.returncode == 0,
                "test_results": test_results,
                "stdout": result.stdout,
                "stderr": result.stderr
            }
            
        except subprocess.TimeoutExpired:
            return {
                "success": False,
                "error": "Test execution timed out",
                "test_results": {"passed": 0, "failed": 0, "errors": 1, "total": 0}
            }
        except Exception as e:
            return {
                "success": False,
                "error": str(e),
                "test_results": {"passed": 0, "failed": 0, "errors": 1, "total": 0}
            }
    
    def _parse_test_output(self, stdout: str, stderr: str) -> Dict[str, Any]:
        """Parse test output to extract results.
        
        Args:
            stdout: Standard output from test command
            stderr: Standard error from test command
            
        Returns:
            Parsed test results
        """
        # Default results
        results = {
            "passed": 0,
            "failed": 0,
            "errors": 0,
            "skipped": 0,
            "total": 0
        }
        
        # Try to parse pytest output
        output = stdout + stderr
        
        # Look for pytest summary line
        pytest_pattern = r"=+ (\d+) failed,?\s*(\d+) passed.*in"
        match = re.search(pytest_pattern, output)
        if match:
            results["failed"] = int(match.group(1))
            results["passed"] = int(match.group(2))
            results["total"] = results["failed"] + results["passed"]
            return results
        
        # Look for other pytest patterns
        patterns = [
            (r"(\d+) passed", "passed"),
            (r"(\d+) failed", "failed"),
            (r"(\d+) error", "errors"),
            (r"(\d+) skipped", "skipped")
        ]
        
        for pattern, key in patterns:
            match = re.search(pattern, output)
            if match:
                results[key] = int(match.group(1))
        
        results["total"] = sum(results[k] for k in ["passed", "failed", "errors", "skipped"])
        
        return results
    
    def _is_command_allowed(self, command: str) -> bool:
        """Check if a command is allowed.
        
        Args:
            command: Command to check
            
        Returns:
            True if command is allowed
        """
        # Extract the first word (command name)
        cmd_parts = command.strip().split()
        if not cmd_parts:
            return False
        
        cmd_name = cmd_parts[0]
        
        # Check against allowed commands
        return cmd_name in self.allowed_commands
    
    def _check_completion(self) -> bool:
        """Check if the task is complete.
        
        Returns:
            True if task is complete
        """
        # Task is complete if tests pass
        return self.success()
    
    def _calculate_reward(self, result: Dict[str, Any], done: bool) -> float:
        """Calculate reward for the action result.
        
        Args:
            result: Action execution result
            done: Whether task is complete
            
        Returns:
            Reward value
        """
        if not result.get("success", False):
            return 0.0
        
        # Base reward for successful action
        reward = 0.1
        
        # Bonus for test results
        if "test_results" in result:
            test_results = result["test_results"]
            total = test_results.get("total", 0)
            passed = test_results.get("passed", 0)
            
            if total > 0:
                test_score = passed / total
                reward += test_score * 0.5
        
        # Large bonus for completion
        if done and self.success():
            reward += 1.0
        
        return min(reward, 1.0)
    
    def _create_observation(self, result: Dict[str, Any]) -> Observation:
        """Create observation from action result.
        
        Args:
            result: Action execution result
            
        Returns:
            Observation for the agent
        """
        observation = {
            "result": result,
            "timestamp": datetime.now().isoformat(),
            "work_dir": str(self.work_dir),
            "modifications_count": len(self.modifications),
            "test_runs": len(self.test_results)
        }
        
        # Add test results if available
        if self.test_results:
            observation["latest_test_results"] = self.test_results[-1]
        
        # Add success status
        observation["success"] = self.success()
        
        return observation
    
    def _cleanup(self) -> None:
        """Clean up work directory and restore original directory."""
        try:
            # Restore original working directory
            os.chdir(self.original_cwd)
            
            # Remove work directory
            if self.work_dir and self.work_dir.exists():
                shutil.rmtree(self.work_dir, ignore_errors=True)
                self._logger.info(f"Cleaned up work directory: {self.work_dir}")
            
        except Exception as e:
            self._logger.warning(f"Cleanup failed: {e}")
        finally:
            self.work_dir = None
            self.repo_dir = None


class SWEBenchTaskWrapper(MultiTurnTask):
    """Wrapper for SWE-bench tasks."""
    
    def __init__(self, task_info: SWEBenchTaskInfo, config: Dict[str, Any]):
        """Initialize the task wrapper.
        
        Args:
            task_info: SWE-bench task information
            config: Task configuration
        """
        super().__init__(task_info.instance_id, config)
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
        return [
            "git_operations",
            "file_editing",
            "command_execution",
            "test_execution",
            "python_environment"
        ]
    
    def execute_turn(self, turn_data: TurnData) -> TurnResult:
        """Execute a single turn.
        
        Args:
            turn_data: Data for the current turn
            
        Returns:
            TurnResult containing the turn outcome
        """
        if not self.environment:
            self.environment = SWEBenchEnvironment(self.task_info, self.config)
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
SWE-bench Task: {self.task_info.instance_id}
Repository: {self.task_info.repo}
Base Commit: {self.task_info.base_commit}

Problem Statement:
{self.task_info.problem_statement}

Hints:
{self.task_info.hints_text}

You can use the following types of actions:
1. Command execution: "command: <shell_command>"
2. File editing: {{"type": "file_edit", "file_path": "path/to/file", "content": "...", "operation": "write"}}
3. Run tests: {{"type": "run_tests", "test_command": "pytest"}}

Start by exploring the repository structure and understanding the problem.
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


class SWEBenchAdapter(BenchmarkAdapter):
    """Adapter for SWE-bench integration."""
    
    def __init__(self, config: Dict[str, Any]):
        """Initialize the SWE-bench adapter.
        
        Args:
            config: Adapter configuration
        """
        super().__init__(config)
        self.dataset_path = config.get("dataset_path", "swe-bench/SWE-bench_Lite")
        self.tasks_cache = {}
    
    def get_adapter_info(self) -> AdapterInfo:
        """Get adapter information.
        
        Returns:
            AdapterInfo describing the SWE-bench adapter
        """
        return AdapterInfo(
            name="swe_bench_adapter",
            version="1.0.0",
            description="Adapter for SWE-bench software engineering evaluation",
            supported_task_types=[TaskType.MULTI_TURN],
            required_dependencies=["git", "python", "pytest"],
            supported_formats=["json", "jsonl"],
            capabilities=[
                "git_operations",
                "dependency_installation",
                "test_execution",
                "file_modification",
                "multi_file_editing",
                "version_control",
                "rollback_support"
            ],
            metadata={
                "benchmark_type": "software_engineering",
                "supports_rollback": True,
                "requires_git": True
            }
        )
    
    def initialize(self) -> bool:
        """Initialize the adapter.
        
        Returns:
            True if initialization was successful
        """
        try:
            self._set_status(AdapterStatus.INITIALIZING)
            
            # Check for required tools
            required_tools = ["git", "python", "pip"]
            for tool in required_tools:
                result = subprocess.run(
                    ["which", tool], 
                    capture_output=True, 
                    text=True
                )
                if result.returncode != 0:
                    raise AdapterError(f"Required tool not found: {tool}")
            
            self._logger.info("SWE-bench adapter initialized successfully")
            self._set_status(AdapterStatus.READY)
            return True
            
        except Exception as e:
            error_msg = f"Failed to initialize SWE-bench adapter: {str(e)}"
            self._set_status(AdapterStatus.ERROR, error_msg)
            return False
    
    def create_environment(self, task_config: Dict[str, Any]) -> UnifiedEnv:
        """Create environment for a SWE-bench task.
        
        Args:
            task_config: Task configuration
            
        Returns:
            SWEBenchEnvironment instance
        """
        if not self.is_ready():
            raise AdapterError("Adapter not initialized")
        
        # Extract task info from config
        task_info = self._create_task_info(task_config)
        
        return SWEBenchEnvironment(task_info, task_config)
    
    def load_tasks(self, task_filter: Optional[Dict[str, Any]] = None) -> List[BaseTask]:
        """Load SWE-bench tasks.
        
        Args:
            task_filter: Optional filter criteria
            
        Returns:
            List of SWE-bench tasks
        """
        if not self.is_ready():
            raise AdapterError("Adapter not initialized")
        
        # For now, return a mock task list
        # In a real implementation, this would load from the SWE-bench dataset
        tasks = []
        
        # Mock task data
        mock_tasks = [
            {
                "instance_id": "django__django-12345",
                "repo": "django/django",
                "base_commit": "abc123",
                "patch": "mock patch content",
                "test_patch": "mock test patch",
                "problem_statement": "Fix issue with Django model validation",
                "hints_text": "Check the model validation logic",
                "created_at": "2023-01-01",
                "version": "1.0",
                "environment": {"python": "3.8"}
            }
        ]
        
        for task_data in mock_tasks:
            task_info = SWEBenchTaskInfo(**task_data)
            task_wrapper = SWEBenchTaskWrapper(task_info, {
                "task_name": task_data["instance_id"],
                "adapter": "swe_bench"
            })
            tasks.append(task_wrapper)
        
        return tasks
    
    def convert_results(self, results: Any) -> StandardizedResult:
        """Convert SWE-bench results to standardized format.
        
        Args:
            results: Raw results from SWE-bench evaluation
            
        Returns:
            StandardizedResult object
        """
        if isinstance(results, dict):
            task_id = results.get("instance_id", "unknown")
            success = results.get("success", False)
            
            # Extract metrics
            test_results = results.get("test_results", {})
            passed = test_results.get("passed", 0)
            total = test_results.get("total", 1)
            score = passed / total if total > 0 else 0.0
            
            return StandardizedResult(
                task_id=task_id,
                adapter_name="swe_bench_adapter",
                success=success,
                score=score,
                execution_time=results.get("execution_time", 0.0),
                turns=results.get("turns", 1),
                tokens_used=results.get("tokens_used", 0),
                cost=results.get("cost", 0.0),
                metadata={
                    "test_results": test_results,
                    "modifications": results.get("modifications", []),
                    "git_commits": results.get("git_commits", [])
                },
                raw_result=results
            )
        else:
            return StandardizedResult(
                task_id="unknown",
                adapter_name="swe_bench_adapter",
                success=False,
                score=0.0,
                execution_time=0.0,
                turns=1,
                tokens_used=0,
                cost=0.0,
                metadata={"conversion_error": "Unsupported result format"},
                raw_result=results
            )
    
    def _create_task_info(self, task_config: Dict[str, Any]) -> SWEBenchTaskInfo:
        """Create SWEBenchTaskInfo from configuration.
        
        Args:
            task_config: Task configuration
            
        Returns:
            SWEBenchTaskInfo object
        """
        required_fields = [
            "instance_id", "repo", "base_commit", "patch", 
            "test_patch", "problem_statement"
        ]
        
        for field in required_fields:
            if field not in task_config:
                raise ConfigurationError(f"Missing required field: {field}")
        
        return SWEBenchTaskInfo(
            instance_id=task_config["instance_id"],
            repo=task_config["repo"],
            base_commit=task_config["base_commit"],
            patch=task_config["patch"],
            test_patch=task_config["test_patch"],
            problem_statement=task_config["problem_statement"],
            hints_text=task_config.get("hints_text", ""),
            created_at=task_config.get("created_at", ""),
            version=task_config.get("version", "1.0"),
            environment=task_config.get("environment", {})
        )