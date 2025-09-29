"""
Scenario-specific environment implementations for multi-turn evaluation.

This module contains concrete implementations of the UnifiedEnv interface
for different evaluation scenarios including repository bug fixing,
interactive debugging, requirement clarification, data science scripting,
command line operations, and cross-language bug fixing.
"""

import os
import subprocess
import tempfile
import shutil
from typing import Any, Dict, List, Optional, Tuple, Union
from dataclasses import dataclass, field
from datetime import datetime
import json
import re

from .environment import UnifiedEnv, Observation, Action, Reward, Info
from .exceptions import TaskExecutionError, SafetyViolationError


@dataclass
class RepositoryState:
    """State information for repository-based environments."""
    repo_path: str
    current_branch: str
    modified_files: List[str] = field(default_factory=list)
    test_results: Dict[str, Any] = field(default_factory=dict)
    commit_history: List[str] = field(default_factory=list)


@dataclass
class DebuggingState:
    """State information for debugging environments."""
    current_file: Optional[str] = None
    breakpoints: List[int] = field(default_factory=list)
    variables: Dict[str, Any] = field(default_factory=dict)
    call_stack: List[str] = field(default_factory=list)
    error_messages: List[str] = field(default_factory=list)


@dataclass
class RequirementState:
    """State information for requirement clarification environments."""
    requirements: List[str] = field(default_factory=list)
    clarifications: List[str] = field(default_factory=list)
    ambiguities: List[str] = field(default_factory=list)
    resolved_items: List[str] = field(default_factory=list)


class RepositoryBugFixEnv(UnifiedEnv):
    """Environment for repository bug fixing scenarios.
    
    This environment simulates a software repository where the agent needs to
    identify and fix bugs by examining code, running tests, and making changes.
    """
    
    def __init__(self, config: Dict[str, Any]):
        """Initialize the repository bug fix environment.
        
        Args:
            config: Configuration dictionary containing:
                - repo_url: URL or path to the repository
                - bug_description: Description of the bug to fix
                - test_command: Command to run tests
                - target_files: List of files likely to contain the bug
                - success_criteria: Criteria for successful bug fix
        """
        super().__init__(config)
        self.repo_url = config.get("repo_url", "")
        self.bug_description = config.get("bug_description", "")
        self.test_command = config.get("test_command", "python -m pytest")
        self.target_files = config.get("target_files", [])
        self.success_criteria = config.get("success_criteria", {})
        
        self.repo_state = RepositoryState(
            repo_path="",
            current_branch="main"
        )
        self._temp_dir = None
        self._initial_test_results = None
        self._bug_fixed = False
    
    def reset(self) -> Observation:
        """Reset the repository environment."""
        try:
            # Create temporary directory for repository
            if self._temp_dir:
                shutil.rmtree(self._temp_dir, ignore_errors=True)
            
            self._temp_dir = tempfile.mkdtemp(prefix="repo_bugfix_")
            self.repo_state.repo_path = self._temp_dir
            
            # Initialize repository (mock implementation)
            self._setup_mock_repository()
            
            # Run initial tests to establish baseline
            self._initial_test_results = self._run_tests()
            
            self._mark_initialized()
            self._bug_fixed = False
            
            observation = {
                "type": "repository_initialized",
                "repo_path": self.repo_state.repo_path,
                "bug_description": self.bug_description,
                "target_files": self.target_files,
                "initial_test_results": self._initial_test_results,
                "available_commands": [
                    "examine_file", "edit_file", "run_tests", 
                    "git_status", "git_diff", "search_code"
                ]
            }
            
            return observation
            
        except Exception as e:
            raise TaskExecutionError(f"Failed to reset repository environment: {str(e)}")
    
    def step(self, action: Action) -> Tuple[Observation, Reward, bool, Info]:
        """Execute an action in the repository environment."""
        if not self._initialized:
            raise TaskExecutionError("Environment not initialized. Call reset() first.")
        
        start_time = datetime.now()
        
        try:
            # Parse action
            if isinstance(action, str):
                action_data = {"command": action, "args": {}}
            elif isinstance(action, dict):
                action_data = action
            else:
                raise TaskExecutionError(f"Invalid action type: {type(action)}")
            
            command = action_data.get("command", "")
            args = action_data.get("args", {})
            
            # Execute command
            observation, reward = self._execute_command(command, args)
            
            # Check if bug is fixed
            done = self._check_completion()
            
            # Update state
            execution_time = (datetime.now() - start_time).total_seconds()
            info = {
                "command": command,
                "args": args,
                "execution_time": execution_time,
                "repo_state": {
                    "modified_files": self.repo_state.modified_files,
                    "current_branch": self.repo_state.current_branch
                }
            }
            
            self._update_state(reward, done, info)
            
            return observation, reward, done, info
            
        except Exception as e:
            raise TaskExecutionError(f"Failed to execute action: {str(e)}")
    
    def success(self) -> bool:
        """Check if the bug has been successfully fixed."""
        return self._bug_fixed
    
    def info(self) -> Dict[str, Any]:
        """Get current repository information."""
        return {
            "environment_type": "repository_bugfix",
            "repo_path": self.repo_state.repo_path,
            "bug_description": self.bug_description,
            "modified_files": self.repo_state.modified_files,
            "test_results": self.repo_state.test_results,
            "bug_fixed": self._bug_fixed,
            "step_count": self._state.step_count
        }
    
    def get_metrics(self) -> Dict[str, float]:
        """Get repository bug fix metrics."""
        files_examined = len(set(self.repo_state.modified_files))
        test_pass_rate = self._calculate_test_pass_rate()
        
        return {
            "files_examined": float(files_examined),
            "test_pass_rate": test_pass_rate,
            "bug_fixed": 1.0 if self._bug_fixed else 0.0,
            "steps_taken": float(self._state.step_count)
        }
    
    def cleanup(self) -> None:
        """Clean up repository resources."""
        if self._temp_dir and os.path.exists(self._temp_dir):
            shutil.rmtree(self._temp_dir, ignore_errors=True)
    
    def _setup_mock_repository(self) -> None:
        """Set up a mock repository with a bug."""
        # Create mock Python files with a bug
        main_file = os.path.join(self._temp_dir, "main.py")
        with open(main_file, "w") as f:
            f.write("""
def calculate_sum(numbers):
    # Bug: should handle empty list
    return sum(numbers)

def main():
    result = calculate_sum([1, 2, 3])
    print(f"Sum: {result}")

if __name__ == "__main__":
    main()
""")
        
        test_file = os.path.join(self._temp_dir, "test_main.py")
        with open(test_file, "w") as f:
            f.write("""
import pytest
from main import calculate_sum

def test_calculate_sum_normal():
    assert calculate_sum([1, 2, 3]) == 6

def test_calculate_sum_empty():
    # This test will fail due to the bug
    assert calculate_sum([]) == 0
""")
    
    def _execute_command(self, command: str, args: Dict[str, Any]) -> Tuple[Observation, float]:
        """Execute a repository command."""
        if command == "examine_file":
            return self._examine_file(args.get("filename", ""))
        elif command == "edit_file":
            return self._edit_file(args.get("filename", ""), args.get("content", ""))
        elif command == "run_tests":
            return self._run_tests_command()
        elif command == "git_status":
            return self._git_status()
        elif command == "search_code":
            return self._search_code(args.get("pattern", ""))
        else:
            return {"error": f"Unknown command: {command}"}, -0.1
    
    def _examine_file(self, filename: str) -> Tuple[Observation, float]:
        """Examine a file in the repository."""
        file_path = os.path.join(self.repo_state.repo_path, filename)
        if not os.path.exists(file_path):
            return {"error": f"File not found: {filename}"}, -0.1
        
        try:
            with open(file_path, "r") as f:
                content = f.read()
            
            return {
                "type": "file_content",
                "filename": filename,
                "content": content,
                "line_count": len(content.split("\n"))
            }, 0.1
        except Exception as e:
            return {"error": f"Failed to read file: {str(e)}"}, -0.1
    
    def _edit_file(self, filename: str, content: str) -> Tuple[Observation, float]:
        """Edit a file in the repository."""
        file_path = os.path.join(self.repo_state.repo_path, filename)
        
        try:
            with open(file_path, "w") as f:
                f.write(content)
            
            if filename not in self.repo_state.modified_files:
                self.repo_state.modified_files.append(filename)
            
            return {
                "type": "file_edited",
                "filename": filename,
                "message": f"File {filename} has been modified"
            }, 0.2
        except Exception as e:
            return {"error": f"Failed to edit file: {str(e)}"}, -0.2
    
    def _run_tests(self) -> Dict[str, Any]:
        """Run tests and return results."""
        try:
            result = subprocess.run(
                ["python", "-m", "pytest", "-v"],
                cwd=self.repo_state.repo_path,
                capture_output=True,
                text=True,
                timeout=30
            )
            
            return {
                "returncode": result.returncode,
                "stdout": result.stdout,
                "stderr": result.stderr,
                "passed": result.returncode == 0
            }
        except subprocess.TimeoutExpired:
            return {"error": "Test execution timed out", "passed": False}
        except Exception as e:
            return {"error": f"Failed to run tests: {str(e)}", "passed": False}
    
    def _run_tests_command(self) -> Tuple[Observation, float]:
        """Run tests command."""
        test_results = self._run_tests()
        self.repo_state.test_results = test_results
        
        if test_results.get("passed", False):
            self._bug_fixed = True
            reward = 1.0
        else:
            reward = 0.0
        
        return {
            "type": "test_results",
            "results": test_results
        }, reward
    
    def _git_status(self) -> Tuple[Observation, float]:
        """Get git status."""
        return {
            "type": "git_status",
            "modified_files": self.repo_state.modified_files,
            "current_branch": self.repo_state.current_branch
        }, 0.0
    
    def _search_code(self, pattern: str) -> Tuple[Observation, float]:
        """Search for code patterns."""
        matches = []
        for root, dirs, files in os.walk(self.repo_state.repo_path):
            for file in files:
                if file.endswith(('.py', '.js', '.java', '.cpp')):
                    file_path = os.path.join(root, file)
                    try:
                        with open(file_path, 'r') as f:
                            content = f.read()
                            if re.search(pattern, content, re.IGNORECASE):
                                matches.append({
                                    "file": os.path.relpath(file_path, self.repo_state.repo_path),
                                    "matches": len(re.findall(pattern, content, re.IGNORECASE))
                                })
                    except Exception:
                        continue
        
        return {
            "type": "search_results",
            "pattern": pattern,
            "matches": matches
        }, 0.1 if matches else 0.0
    
    def _check_completion(self) -> bool:
        """Check if the bug fix is complete."""
        return self._bug_fixed
    
    def _calculate_test_pass_rate(self) -> float:
        """Calculate the current test pass rate."""
        if not self.repo_state.test_results:
            return 0.0
        return 1.0 if self.repo_state.test_results.get("passed", False) else 0.0


class InteractiveDebuggingEnv(UnifiedEnv):
    """Environment for interactive debugging scenarios."""
    
    def __init__(self, config: Dict[str, Any]):
        """Initialize the interactive debugging environment."""
        super().__init__(config)
        self.program_file = config.get("program_file", "")
        self.error_description = config.get("error_description", "")
        self.debugging_state = DebuggingState()
        self._debug_session_active = False
        self._error_resolved = False
    
    def reset(self) -> Observation:
        """Reset the debugging environment."""
        self._mark_initialized()
        self._debug_session_active = False
        self._error_resolved = False
        self.debugging_state = DebuggingState()
        
        return {
            "type": "debug_session_started",
            "program_file": self.program_file,
            "error_description": self.error_description,
            "available_commands": [
                "set_breakpoint", "run_program", "step_over", 
                "inspect_variable", "examine_stack", "fix_code"
            ]
        }
    
    def step(self, action: Action) -> Tuple[Observation, Reward, bool, Info]:
        """Execute a debugging action."""
        if not self._initialized:
            raise TaskExecutionError("Environment not initialized. Call reset() first.")
        
        # Mock debugging implementation
        command = action.get("command", "") if isinstance(action, dict) else str(action)
        
        if command == "run_program":
            observation = {"type": "program_output", "output": "Mock program execution"}
            reward = 0.1
        elif command == "set_breakpoint":
            line = action.get("line", 1) if isinstance(action, dict) else 1
            self.debugging_state.breakpoints.append(line)
            observation = {"type": "breakpoint_set", "line": line}
            reward = 0.1
        elif command == "fix_code":
            self._error_resolved = True
            observation = {"type": "code_fixed", "message": "Error has been resolved"}
            reward = 1.0
        else:
            observation = {"type": "unknown_command", "command": command}
            reward = -0.1
        
        done = self._error_resolved
        info = {"debugging_state": self.debugging_state.__dict__}
        
        self._update_state(reward, done, info)
        return observation, reward, done, info
    
    def success(self) -> bool:
        """Check if the debugging session was successful."""
        return self._error_resolved
    
    def info(self) -> Dict[str, Any]:
        """Get debugging session information."""
        return {
            "environment_type": "interactive_debugging",
            "program_file": self.program_file,
            "error_description": self.error_description,
            "debugging_state": self.debugging_state.__dict__,
            "error_resolved": self._error_resolved
        }
    
    def get_metrics(self) -> Dict[str, float]:
        """Get debugging metrics."""
        return {
            "breakpoints_set": float(len(self.debugging_state.breakpoints)),
            "error_resolved": 1.0 if self._error_resolved else 0.0,
            "steps_taken": float(self._state.step_count)
        }


class RequirementClarificationEnv(UnifiedEnv):
    """Environment for requirement clarification scenarios."""
    
    def __init__(self, config: Dict[str, Any]):
        """Initialize the requirement clarification environment."""
        super().__init__(config)
        self.initial_requirements = config.get("initial_requirements", [])
        self.stakeholder_responses = config.get("stakeholder_responses", {})
        self.requirement_state = RequirementState(
            requirements=self.initial_requirements.copy()
        )
        self._clarification_complete = False
    
    def reset(self) -> Observation:
        """Reset the requirement clarification environment."""
        self._mark_initialized()
        self._clarification_complete = False
        self.requirement_state = RequirementState(
            requirements=self.initial_requirements.copy()
        )
        
        return {
            "type": "requirements_presented",
            "requirements": self.requirement_state.requirements,
            "available_commands": [
                "ask_clarification", "identify_ambiguity", 
                "propose_solution", "finalize_requirements"
            ]
        }
    
    def step(self, action: Action) -> Tuple[Observation, Reward, bool, Info]:
        """Execute a requirement clarification action."""
        if not self._initialized:
            raise TaskExecutionError("Environment not initialized. Call reset() first.")
        
        command = action.get("command", "") if isinstance(action, dict) else str(action)
        
        if command == "ask_clarification":
            question = action.get("question", "") if isinstance(action, dict) else ""
            response = self._get_stakeholder_response(question)
            self.requirement_state.clarifications.append(f"Q: {question} A: {response}")
            observation = {"type": "clarification_received", "question": question, "response": response}
            reward = 0.3
        elif command == "identify_ambiguity":
            ambiguity = action.get("ambiguity", "") if isinstance(action, dict) else ""
            self.requirement_state.ambiguities.append(ambiguity)
            observation = {"type": "ambiguity_identified", "ambiguity": ambiguity}
            reward = 0.2
        elif command == "finalize_requirements":
            self._clarification_complete = True
            observation = {"type": "requirements_finalized", "final_requirements": self.requirement_state.requirements}
            reward = 1.0
        else:
            observation = {"type": "unknown_command", "command": command}
            reward = -0.1
        
        done = self._clarification_complete
        info = {"requirement_state": self.requirement_state.__dict__}
        
        self._update_state(reward, done, info)
        return observation, reward, done, info
    
    def success(self) -> bool:
        """Check if requirement clarification was successful."""
        return self._clarification_complete
    
    def info(self) -> Dict[str, Any]:
        """Get requirement clarification information."""
        return {
            "environment_type": "requirement_clarification",
            "requirement_state": self.requirement_state.__dict__,
            "clarification_complete": self._clarification_complete
        }
    
    def get_metrics(self) -> Dict[str, float]:
        """Get requirement clarification metrics."""
        return {
            "clarifications_made": float(len(self.requirement_state.clarifications)),
            "ambiguities_identified": float(len(self.requirement_state.ambiguities)),
            "requirements_finalized": 1.0 if self._clarification_complete else 0.0,
            "steps_taken": float(self._state.step_count)
        }
    
    def _get_stakeholder_response(self, question: str) -> str:
        """Get a mock stakeholder response to a question."""
        # Simple mock implementation
        responses = [
            "That's a good question. Let me clarify...",
            "The requirement should be interpreted as...",
            "We need to consider the edge case where...",
            "The business logic requires that..."
        ]
        import random
        return random.choice(responses)


class DataScienceScriptEnv(UnifiedEnv):
    """Environment for data science script development scenarios."""
    
    def __init__(self, config: Dict[str, Any]):
        """Initialize the data science script environment."""
        super().__init__(config)
        self.dataset_path = config.get("dataset_path", "")
        self.analysis_goal = config.get("analysis_goal", "")
        self.required_outputs = config.get("required_outputs", [])
        self._script_complete = False
        self._outputs_generated = []
    
    def reset(self) -> Observation:
        """Reset the data science environment."""
        self._mark_initialized()
        self._script_complete = False
        self._outputs_generated = []
        
        return {
            "type": "dataset_loaded",
            "dataset_path": self.dataset_path,
            "analysis_goal": self.analysis_goal,
            "required_outputs": self.required_outputs,
            "available_commands": [
                "explore_data", "create_visualization", "run_analysis", 
                "generate_report", "validate_results"
            ]
        }
    
    def step(self, action: Action) -> Tuple[Observation, Reward, bool, Info]:
        """Execute a data science action."""
        if not self._initialized:
            raise TaskExecutionError("Environment not initialized. Call reset() first.")
        
        command = action.get("command", "") if isinstance(action, dict) else str(action)
        
        if command == "explore_data":
            observation = {"type": "data_summary", "summary": "Mock data exploration results"}
            reward = 0.2
        elif command == "create_visualization":
            viz_type = action.get("type", "plot") if isinstance(action, dict) else "plot"
            self._outputs_generated.append(f"visualization_{viz_type}")
            observation = {"type": "visualization_created", "viz_type": viz_type}
            reward = 0.3
        elif command == "generate_report":
            self._outputs_generated.append("report")
            self._script_complete = len(self._outputs_generated) >= len(self.required_outputs)
            observation = {"type": "report_generated", "outputs": self._outputs_generated}
            reward = 0.5 if self._script_complete else 0.3
        else:
            observation = {"type": "unknown_command", "command": command}
            reward = -0.1
        
        done = self._script_complete
        info = {"outputs_generated": self._outputs_generated}
        
        self._update_state(reward, done, info)
        return observation, reward, done, info
    
    def success(self) -> bool:
        """Check if the data science script was completed successfully."""
        return self._script_complete
    
    def info(self) -> Dict[str, Any]:
        """Get data science script information."""
        return {
            "environment_type": "data_science_script",
            "dataset_path": self.dataset_path,
            "analysis_goal": self.analysis_goal,
            "outputs_generated": self._outputs_generated,
            "script_complete": self._script_complete
        }
    
    def get_metrics(self) -> Dict[str, float]:
        """Get data science metrics."""
        completion_rate = len(self._outputs_generated) / max(len(self.required_outputs), 1)
        return {
            "completion_rate": min(completion_rate, 1.0),
            "outputs_generated": float(len(self._outputs_generated)),
            "script_complete": 1.0 if self._script_complete else 0.0,
            "steps_taken": float(self._state.step_count)
        }


class CommandLineEnv(UnifiedEnv):
    """Environment for command line operation scenarios."""
    
    def __init__(self, config: Dict[str, Any]):
        """Initialize the command line environment."""
        super().__init__(config)
        self.allowed_commands = config.get("allowed_commands", ["ls", "cat", "grep", "find"])
        self.goal_description = config.get("goal_description", "")
        self.working_directory = config.get("working_directory", "/tmp")
        self._goal_achieved = False
        self._command_history = []
    
    def reset(self) -> Observation:
        """Reset the command line environment."""
        self._mark_initialized()
        self._goal_achieved = False
        self._command_history = []
        
        return {
            "type": "terminal_ready",
            "working_directory": self.working_directory,
            "goal_description": self.goal_description,
            "allowed_commands": self.allowed_commands,
            "prompt": f"{self.working_directory}$ "
        }
    
    def step(self, action: Action) -> Tuple[Observation, Reward, bool, Info]:
        """Execute a command line action."""
        if not self._initialized:
            raise TaskExecutionError("Environment not initialized. Call reset() first.")
        
        command = str(action) if not isinstance(action, dict) else action.get("command", "")
        
        # Validate command safety
        is_valid, error_msg = self.validate_action(command)
        if not is_valid:
            raise SafetyViolationError(f"Unsafe command: {error_msg}", "dangerous_command")
        
        # Mock command execution
        self._command_history.append(command)
        
        if command.startswith("ls"):
            output = "file1.txt  file2.py  directory1/"
            reward = 0.1
        elif command.startswith("cat"):
            output = "Mock file content"
            reward = 0.1
        elif command == "goal_complete":
            self._goal_achieved = True
            output = "Goal has been achieved!"
            reward = 1.0
        else:
            output = f"Command executed: {command}"
            reward = 0.05
        
        observation = {
            "type": "command_output",
            "command": command,
            "output": output,
            "prompt": f"{self.working_directory}$ "
        }
        
        done = self._goal_achieved
        info = {"command_history": self._command_history}
        
        self._update_state(reward, done, info)
        return observation, reward, done, info
    
    def success(self) -> bool:
        """Check if the command line goal was achieved."""
        return self._goal_achieved
    
    def info(self) -> Dict[str, Any]:
        """Get command line environment information."""
        return {
            "environment_type": "command_line",
            "working_directory": self.working_directory,
            "goal_description": self.goal_description,
            "command_history": self._command_history,
            "goal_achieved": self._goal_achieved
        }
    
    def get_metrics(self) -> Dict[str, float]:
        """Get command line metrics."""
        return {
            "commands_executed": float(len(self._command_history)),
            "goal_achieved": 1.0 if self._goal_achieved else 0.0,
            "steps_taken": float(self._state.step_count)
        }
    
    def validate_action(self, action: Action) -> Tuple[bool, Optional[str]]:
        """Validate command line action for safety."""
        command = str(action)
        
        # Check for dangerous commands
        dangerous_patterns = [
            r"rm\s+-rf",
            r"sudo\s+",
            r"chmod\s+777",
            r">\s*/dev/",
            r"mkfs\.",
            r"dd\s+if="
        ]
        
        for pattern in dangerous_patterns:
            if re.search(pattern, command):
                return False, f"Dangerous command pattern detected: {pattern}"
        
        # Check if command is in allowed list
        command_name = command.split()[0] if command.split() else ""
        if command_name not in self.allowed_commands and command_name != "goal_complete":
            return False, f"Command not in allowed list: {command_name}"
        
        return True, None


class CrossLanguageFixEnv(UnifiedEnv):
    """Environment for cross-language bug fixing scenarios."""
    
    def __init__(self, config: Dict[str, Any]):
        """Initialize the cross-language fix environment."""
        super().__init__(config)
        self.languages = config.get("languages", ["python", "javascript"])
        self.bug_description = config.get("bug_description", "")
        self.project_structure = config.get("project_structure", {})
        self._fixes_applied = {}
        self._all_tests_passing = False
    
    def reset(self) -> Observation:
        """Reset the cross-language environment."""
        self._mark_initialized()
        self._fixes_applied = {}
        self._all_tests_passing = False
        
        return {
            "type": "project_loaded",
            "languages": self.languages,
            "bug_description": self.bug_description,
            "project_structure": self.project_structure,
            "available_commands": [
                "examine_file", "fix_python", "fix_javascript", 
                "run_tests", "check_integration"
            ]
        }
    
    def step(self, action: Action) -> Tuple[Observation, Reward, bool, Info]:
        """Execute a cross-language fix action."""
        if not self._initialized:
            raise TaskExecutionError("Environment not initialized. Call reset() first.")
        
        command = action.get("command", "") if isinstance(action, dict) else str(action)
        
        if command.startswith("fix_"):
            language = command.split("_")[1]
            if language in self.languages:
                self._fixes_applied[language] = True
                observation = {"type": "fix_applied", "language": language}
                reward = 0.4
            else:
                observation = {"type": "invalid_language", "language": language}
                reward = -0.1
        elif command == "run_tests":
            all_fixed = all(self._fixes_applied.get(lang, False) for lang in self.languages)
            self._all_tests_passing = all_fixed
            observation = {"type": "test_results", "all_passing": all_fixed}
            reward = 1.0 if all_fixed else 0.2
        else:
            observation = {"type": "unknown_command", "command": command}
            reward = -0.1
        
        done = self._all_tests_passing
        info = {"fixes_applied": self._fixes_applied}
        
        self._update_state(reward, done, info)
        return observation, reward, done, info
    
    def success(self) -> bool:
        """Check if all cross-language fixes were successful."""
        return self._all_tests_passing
    
    def info(self) -> Dict[str, Any]:
        """Get cross-language fix information."""
        return {
            "environment_type": "cross_language_fix",
            "languages": self.languages,
            "bug_description": self.bug_description,
            "fixes_applied": self._fixes_applied,
            "all_tests_passing": self._all_tests_passing
        }
    
    def get_metrics(self) -> Dict[str, float]:
        """Get cross-language fix metrics."""
        fix_completion = len(self._fixes_applied) / max(len(self.languages), 1)
        return {
            "fix_completion_rate": min(fix_completion, 1.0),
            "languages_fixed": float(len(self._fixes_applied)),
            "all_tests_passing": 1.0 if self._all_tests_passing else 0.0,
            "steps_taken": float(self._state.step_count)
        }