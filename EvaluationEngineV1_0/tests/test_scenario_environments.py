"""
Unit tests for scenario-specific environments.

This module tests all scenario-specific environment implementations
including repository bug fixing, interactive debugging, requirement
clarification, data science scripting, command line operations,
and cross-language bug fixing.
"""

import pytest
import tempfile
import shutil
import os
from unittest.mock import patch, MagicMock

from EvaluationEngineV1_0.core.scenario_environments import (
    RepositoryBugFixEnv,
    InteractiveDebuggingEnv,
    RequirementClarificationEnv,
    DataScienceScriptEnv,
    CommandLineEnv,
    CrossLanguageFixEnv,
    RepositoryState,
    DebuggingState,
    RequirementState
)
from EvaluationEngineV1_0.core.exceptions import TaskExecutionError, SafetyViolationError


class TestRepositoryState:
    """Test RepositoryState data class."""
    
    def test_creation(self):
        """Test basic creation."""
        state = RepositoryState(
            repo_path="/tmp/repo",
            current_branch="main"
        )
        
        assert state.repo_path == "/tmp/repo"
        assert state.current_branch == "main"
        assert state.modified_files == []
        assert state.test_results == {}
        assert state.commit_history == []
    
    def test_with_data(self):
        """Test creation with data."""
        state = RepositoryState(
            repo_path="/tmp/repo",
            current_branch="feature",
            modified_files=["file1.py", "file2.py"],
            test_results={"passed": True},
            commit_history=["commit1", "commit2"]
        )
        
        assert state.repo_path == "/tmp/repo"
        assert state.current_branch == "feature"
        assert state.modified_files == ["file1.py", "file2.py"]
        assert state.test_results == {"passed": True}
        assert state.commit_history == ["commit1", "commit2"]


class TestDebuggingState:
    """Test DebuggingState data class."""
    
    def test_creation(self):
        """Test basic creation."""
        state = DebuggingState()
        
        assert state.current_file is None
        assert state.breakpoints == []
        assert state.variables == {}
        assert state.call_stack == []
        assert state.error_messages == []
    
    def test_with_data(self):
        """Test creation with data."""
        state = DebuggingState(
            current_file="main.py",
            breakpoints=[10, 20],
            variables={"x": 5, "y": "test"},
            call_stack=["main", "func1"],
            error_messages=["Error 1", "Error 2"]
        )
        
        assert state.current_file == "main.py"
        assert state.breakpoints == [10, 20]
        assert state.variables == {"x": 5, "y": "test"}
        assert state.call_stack == ["main", "func1"]
        assert state.error_messages == ["Error 1", "Error 2"]


class TestRequirementState:
    """Test RequirementState data class."""
    
    def test_creation(self):
        """Test basic creation."""
        state = RequirementState()
        
        assert state.requirements == []
        assert state.clarifications == []
        assert state.ambiguities == []
        assert state.resolved_items == []
    
    def test_with_data(self):
        """Test creation with data."""
        state = RequirementState(
            requirements=["req1", "req2"],
            clarifications=["clarif1"],
            ambiguities=["ambig1"],
            resolved_items=["resolved1"]
        )
        
        assert state.requirements == ["req1", "req2"]
        assert state.clarifications == ["clarif1"]
        assert state.ambiguities == ["ambig1"]
        assert state.resolved_items == ["resolved1"]


class TestRepositoryBugFixEnv:
    """Test RepositoryBugFixEnv environment."""
    
    def test_initialization(self):
        """Test environment initialization."""
        config = {
            "repo_url": "https://github.com/test/repo",
            "bug_description": "Test bug",
            "test_command": "pytest",
            "target_files": ["main.py"],
            "success_criteria": {"tests_pass": True}
        }
        
        env = RepositoryBugFixEnv(config)
        
        assert env.repo_url == "https://github.com/test/repo"
        assert env.bug_description == "Test bug"
        assert env.test_command == "pytest"
        assert env.target_files == ["main.py"]
        assert env.success_criteria == {"tests_pass": True}
        assert not env._initialized
        assert not env._bug_fixed
    
    def test_reset(self):
        """Test environment reset."""
        config = {
            "bug_description": "Test bug",
            "target_files": ["main.py"]
        }
        
        env = RepositoryBugFixEnv(config)
        observation = env.reset()
        
        assert env._initialized
        assert not env._bug_fixed
        assert isinstance(observation, dict)
        assert observation["type"] == "repository_initialized"
        assert "bug_description" in observation
        assert "target_files" in observation
        assert "available_commands" in observation
        
        # Cleanup
        env.cleanup()
    
    def test_examine_file_action(self):
        """Test examine file action."""
        config = {"bug_description": "Test bug"}
        env = RepositoryBugFixEnv(config)
        env.reset()
        
        # Test examining existing file
        action = {"command": "examine_file", "args": {"filename": "main.py"}}
        observation, reward, done, info = env.step(action)
        
        assert isinstance(observation, dict)
        assert reward > 0  # Should get positive reward for examining file
        assert not done  # Should not be done yet
        assert "command" in info
        
        env.cleanup()
    
    def test_edit_file_action(self):
        """Test edit file action."""
        config = {"bug_description": "Test bug"}
        env = RepositoryBugFixEnv(config)
        env.reset()
        
        # Test editing file
        new_content = """
def calculate_sum(numbers):
    if not numbers:
        return 0
    return sum(numbers)
"""
        action = {"command": "edit_file", "args": {"filename": "main.py", "content": new_content}}
        observation, reward, done, info = env.step(action)
        
        assert isinstance(observation, dict)
        assert observation["type"] == "file_edited"
        assert reward > 0
        assert "main.py" in env.repo_state.modified_files
        
        env.cleanup()
    
    def test_run_tests_action(self):
        """Test run tests action."""
        config = {"bug_description": "Test bug"}
        env = RepositoryBugFixEnv(config)
        env.reset()
        
        # Mock subprocess to avoid actual test execution
        with patch('subprocess.run') as mock_run:
            mock_run.return_value = MagicMock(returncode=0, stdout="All tests passed", stderr="")
            
            action = {"command": "run_tests", "args": {}}
            observation, reward, done, info = env.step(action)
            
            assert isinstance(observation, dict)
            assert observation["type"] == "test_results"
            assert env._bug_fixed  # Should be marked as fixed when tests pass
            assert done  # Should be done when bug is fixed
            assert reward == 1.0  # Should get maximum reward
        
        env.cleanup()
    
    def test_search_code_action(self):
        """Test search code action."""
        config = {"bug_description": "Test bug"}
        env = RepositoryBugFixEnv(config)
        env.reset()
        
        action = {"command": "search_code", "args": {"pattern": "calculate_sum"}}
        observation, reward, done, info = env.step(action)
        
        assert isinstance(observation, dict)
        assert observation["type"] == "search_results"
        assert "pattern" in observation
        assert "matches" in observation
        
        env.cleanup()
    
    def test_success_method(self):
        """Test success method."""
        config = {"bug_description": "Test bug"}
        env = RepositoryBugFixEnv(config)
        env.reset()
        
        assert not env.success()
        
        env._bug_fixed = True
        assert env.success()
        
        env.cleanup()
    
    def test_info_method(self):
        """Test info method."""
        config = {"bug_description": "Test bug"}
        env = RepositoryBugFixEnv(config)
        env.reset()
        
        info = env.info()
        
        assert isinstance(info, dict)
        assert info["environment_type"] == "repository_bugfix"
        assert "bug_description" in info
        assert "modified_files" in info
        assert "bug_fixed" in info
        
        env.cleanup()
    
    def test_get_metrics(self):
        """Test get_metrics method."""
        config = {"bug_description": "Test bug"}
        env = RepositoryBugFixEnv(config)
        env.reset()
        
        metrics = env.get_metrics()
        
        assert isinstance(metrics, dict)
        assert "files_examined" in metrics
        assert "test_pass_rate" in metrics
        assert "bug_fixed" in metrics
        assert "steps_taken" in metrics
        
        env.cleanup()
    
    def test_step_without_reset(self):
        """Test step without reset raises error."""
        config = {"bug_description": "Test bug"}
        env = RepositoryBugFixEnv(config)
        
        with pytest.raises(TaskExecutionError, match="Environment not initialized"):
            env.step({"command": "examine_file"})


class TestInteractiveDebuggingEnv:
    """Test InteractiveDebuggingEnv environment."""
    
    def test_initialization(self):
        """Test environment initialization."""
        config = {
            "program_file": "buggy_program.py",
            "error_description": "IndexError on line 15"
        }
        
        env = InteractiveDebuggingEnv(config)
        
        assert env.program_file == "buggy_program.py"
        assert env.error_description == "IndexError on line 15"
        assert not env._debug_session_active
        assert not env._error_resolved
    
    def test_reset(self):
        """Test environment reset."""
        config = {
            "program_file": "buggy_program.py",
            "error_description": "IndexError on line 15"
        }
        
        env = InteractiveDebuggingEnv(config)
        observation = env.reset()
        
        assert env._initialized
        assert not env._debug_session_active
        assert not env._error_resolved
        assert isinstance(observation, dict)
        assert observation["type"] == "debug_session_started"
        assert "available_commands" in observation
    
    def test_set_breakpoint_action(self):
        """Test set breakpoint action."""
        config = {"program_file": "test.py", "error_description": "Test error"}
        env = InteractiveDebuggingEnv(config)
        env.reset()
        
        action = {"command": "set_breakpoint", "line": 10}
        observation, reward, done, info = env.step(action)
        
        assert observation["type"] == "breakpoint_set"
        assert observation["line"] == 10
        assert 10 in env.debugging_state.breakpoints
        assert reward > 0
        assert not done
    
    def test_fix_code_action(self):
        """Test fix code action."""
        config = {"program_file": "test.py", "error_description": "Test error"}
        env = InteractiveDebuggingEnv(config)
        env.reset()
        
        action = {"command": "fix_code"}
        observation, reward, done, info = env.step(action)
        
        assert observation["type"] == "code_fixed"
        assert env._error_resolved
        assert reward == 1.0
        assert done
    
    def test_success_method(self):
        """Test success method."""
        config = {"program_file": "test.py", "error_description": "Test error"}
        env = InteractiveDebuggingEnv(config)
        env.reset()
        
        assert not env.success()
        
        env._error_resolved = True
        assert env.success()
    
    def test_get_metrics(self):
        """Test get_metrics method."""
        config = {"program_file": "test.py", "error_description": "Test error"}
        env = InteractiveDebuggingEnv(config)
        env.reset()
        
        # Set some breakpoints
        env.debugging_state.breakpoints = [10, 20]
        
        metrics = env.get_metrics()
        
        assert isinstance(metrics, dict)
        assert metrics["breakpoints_set"] == 2.0
        assert metrics["error_resolved"] == 0.0
        assert "steps_taken" in metrics


class TestRequirementClarificationEnv:
    """Test RequirementClarificationEnv environment."""
    
    def test_initialization(self):
        """Test environment initialization."""
        config = {
            "initial_requirements": ["Req 1", "Req 2"],
            "stakeholder_responses": {"question1": "answer1"}
        }
        
        env = RequirementClarificationEnv(config)
        
        assert env.initial_requirements == ["Req 1", "Req 2"]
        assert env.stakeholder_responses == {"question1": "answer1"}
        assert not env._clarification_complete
    
    def test_reset(self):
        """Test environment reset."""
        config = {
            "initial_requirements": ["Req 1", "Req 2"]
        }
        
        env = RequirementClarificationEnv(config)
        observation = env.reset()
        
        assert env._initialized
        assert not env._clarification_complete
        assert observation["type"] == "requirements_presented"
        assert observation["requirements"] == ["Req 1", "Req 2"]
        assert "available_commands" in observation
    
    def test_ask_clarification_action(self):
        """Test ask clarification action."""
        config = {"initial_requirements": ["Req 1"]}
        env = RequirementClarificationEnv(config)
        env.reset()
        
        action = {"command": "ask_clarification", "question": "What does Req 1 mean?"}
        observation, reward, done, info = env.step(action)
        
        assert observation["type"] == "clarification_received"
        assert observation["question"] == "What does Req 1 mean?"
        assert "response" in observation
        assert len(env.requirement_state.clarifications) == 1
        assert reward > 0
        assert not done
    
    def test_identify_ambiguity_action(self):
        """Test identify ambiguity action."""
        config = {"initial_requirements": ["Req 1"]}
        env = RequirementClarificationEnv(config)
        env.reset()
        
        action = {"command": "identify_ambiguity", "ambiguity": "Req 1 is unclear"}
        observation, reward, done, info = env.step(action)
        
        assert observation["type"] == "ambiguity_identified"
        assert observation["ambiguity"] == "Req 1 is unclear"
        assert "Req 1 is unclear" in env.requirement_state.ambiguities
        assert reward > 0
        assert not done
    
    def test_finalize_requirements_action(self):
        """Test finalize requirements action."""
        config = {"initial_requirements": ["Req 1"]}
        env = RequirementClarificationEnv(config)
        env.reset()
        
        action = {"command": "finalize_requirements"}
        observation, reward, done, info = env.step(action)
        
        assert observation["type"] == "requirements_finalized"
        assert env._clarification_complete
        assert reward == 1.0
        assert done
    
    def test_success_method(self):
        """Test success method."""
        config = {"initial_requirements": ["Req 1"]}
        env = RequirementClarificationEnv(config)
        env.reset()
        
        assert not env.success()
        
        env._clarification_complete = True
        assert env.success()
    
    def test_get_metrics(self):
        """Test get_metrics method."""
        config = {"initial_requirements": ["Req 1"]}
        env = RequirementClarificationEnv(config)
        env.reset()
        
        # Add some data
        env.requirement_state.clarifications = ["clarif1", "clarif2"]
        env.requirement_state.ambiguities = ["ambig1"]
        
        metrics = env.get_metrics()
        
        assert isinstance(metrics, dict)
        assert metrics["clarifications_made"] == 2.0
        assert metrics["ambiguities_identified"] == 1.0
        assert metrics["requirements_finalized"] == 0.0


class TestDataScienceScriptEnv:
    """Test DataScienceScriptEnv environment."""
    
    def test_initialization(self):
        """Test environment initialization."""
        config = {
            "dataset_path": "/data/dataset.csv",
            "analysis_goal": "Predict customer churn",
            "required_outputs": ["visualization", "model", "report"]
        }
        
        env = DataScienceScriptEnv(config)
        
        assert env.dataset_path == "/data/dataset.csv"
        assert env.analysis_goal == "Predict customer churn"
        assert env.required_outputs == ["visualization", "model", "report"]
        assert not env._script_complete
        assert env._outputs_generated == []
    
    def test_reset(self):
        """Test environment reset."""
        config = {
            "dataset_path": "/data/dataset.csv",
            "analysis_goal": "Predict customer churn",
            "required_outputs": ["visualization", "report"]
        }
        
        env = DataScienceScriptEnv(config)
        observation = env.reset()
        
        assert env._initialized
        assert not env._script_complete
        assert observation["type"] == "dataset_loaded"
        assert observation["dataset_path"] == "/data/dataset.csv"
        assert observation["analysis_goal"] == "Predict customer churn"
        assert "available_commands" in observation
    
    def test_explore_data_action(self):
        """Test explore data action."""
        config = {"dataset_path": "/data/test.csv", "analysis_goal": "Test", "required_outputs": []}
        env = DataScienceScriptEnv(config)
        env.reset()
        
        action = {"command": "explore_data"}
        observation, reward, done, info = env.step(action)
        
        assert observation["type"] == "data_summary"
        assert reward > 0
        assert not done
    
    def test_create_visualization_action(self):
        """Test create visualization action."""
        config = {"dataset_path": "/data/test.csv", "analysis_goal": "Test", "required_outputs": ["viz"]}
        env = DataScienceScriptEnv(config)
        env.reset()
        
        action = {"command": "create_visualization", "type": "histogram"}
        observation, reward, done, info = env.step(action)
        
        assert observation["type"] == "visualization_created"
        assert observation["viz_type"] == "histogram"
        assert "visualization_histogram" in env._outputs_generated
        assert reward > 0
    
    def test_generate_report_action(self):
        """Test generate report action."""
        config = {"dataset_path": "/data/test.csv", "analysis_goal": "Test", "required_outputs": ["report"]}
        env = DataScienceScriptEnv(config)
        env.reset()
        
        action = {"command": "generate_report"}
        observation, reward, done, info = env.step(action)
        
        assert observation["type"] == "report_generated"
        assert "report" in env._outputs_generated
        assert env._script_complete  # Should be complete since we have all required outputs
        assert done
        assert reward > 0
    
    def test_success_method(self):
        """Test success method."""
        config = {"dataset_path": "/data/test.csv", "analysis_goal": "Test", "required_outputs": []}
        env = DataScienceScriptEnv(config)
        env.reset()
        
        assert not env.success()
        
        env._script_complete = True
        assert env.success()
    
    def test_get_metrics(self):
        """Test get_metrics method."""
        config = {"dataset_path": "/data/test.csv", "analysis_goal": "Test", "required_outputs": ["viz", "report"]}
        env = DataScienceScriptEnv(config)
        env.reset()
        
        # Add some outputs
        env._outputs_generated = ["viz"]
        
        metrics = env.get_metrics()
        
        assert isinstance(metrics, dict)
        assert metrics["completion_rate"] == 0.5  # 1 out of 2 required outputs
        assert metrics["outputs_generated"] == 1.0
        assert metrics["script_complete"] == 0.0


class TestCommandLineEnv:
    """Test CommandLineEnv environment."""
    
    def test_initialization(self):
        """Test environment initialization."""
        config = {
            "allowed_commands": ["ls", "cat", "grep"],
            "goal_description": "Find all Python files",
            "working_directory": "/home/user"
        }
        
        env = CommandLineEnv(config)
        
        assert env.allowed_commands == ["ls", "cat", "grep"]
        assert env.goal_description == "Find all Python files"
        assert env.working_directory == "/home/user"
        assert not env._goal_achieved
        assert env._command_history == []
    
    def test_reset(self):
        """Test environment reset."""
        config = {
            "allowed_commands": ["ls", "cat"],
            "goal_description": "List files",
            "working_directory": "/tmp"
        }
        
        env = CommandLineEnv(config)
        observation = env.reset()
        
        assert env._initialized
        assert not env._goal_achieved
        assert observation["type"] == "terminal_ready"
        assert observation["working_directory"] == "/tmp"
        assert observation["goal_description"] == "List files"
        assert "prompt" in observation
    
    def test_ls_command(self):
        """Test ls command execution."""
        config = {"allowed_commands": ["ls"], "goal_description": "Test", "working_directory": "/tmp"}
        env = CommandLineEnv(config)
        env.reset()
        
        action = "ls -la"
        observation, reward, done, info = env.step(action)
        
        assert observation["type"] == "command_output"
        assert observation["command"] == "ls -la"
        assert "output" in observation
        assert "ls -la" in env._command_history
        assert reward > 0
        assert not done
    
    def test_goal_complete_command(self):
        """Test goal complete command."""
        config = {"allowed_commands": ["ls"], "goal_description": "Test", "working_directory": "/tmp"}
        env = CommandLineEnv(config)
        env.reset()
        
        action = "goal_complete"
        observation, reward, done, info = env.step(action)
        
        assert observation["command"] == "goal_complete"
        assert env._goal_achieved
        assert reward == 1.0
        assert done
    
    def test_validate_action_safe(self):
        """Test action validation for safe commands."""
        config = {"allowed_commands": ["ls", "cat"], "goal_description": "Test", "working_directory": "/tmp"}
        env = CommandLineEnv(config)
        
        is_valid, error_msg = env.validate_action("ls -la")
        assert is_valid
        assert error_msg is None
    
    def test_validate_action_dangerous(self):
        """Test action validation for dangerous commands."""
        config = {"allowed_commands": ["ls", "cat"], "goal_description": "Test", "working_directory": "/tmp"}
        env = CommandLineEnv(config)
        
        is_valid, error_msg = env.validate_action("rm -rf /")
        assert not is_valid
        assert "Dangerous command pattern detected" in error_msg
    
    def test_validate_action_not_allowed(self):
        """Test action validation for non-allowed commands."""
        config = {"allowed_commands": ["ls"], "goal_description": "Test", "working_directory": "/tmp"}
        env = CommandLineEnv(config)
        
        is_valid, error_msg = env.validate_action("cat file.txt")
        assert not is_valid
        assert "Command not in allowed list" in error_msg
    
    def test_safety_violation(self):
        """Test safety violation on dangerous command."""
        config = {"allowed_commands": ["ls"], "goal_description": "Test", "working_directory": "/tmp"}
        env = CommandLineEnv(config)
        env.reset()
        
        with pytest.raises(SafetyViolationError, match="Unsafe command"):
            env.step("sudo rm -rf /")
    
    def test_success_method(self):
        """Test success method."""
        config = {"allowed_commands": ["ls"], "goal_description": "Test", "working_directory": "/tmp"}
        env = CommandLineEnv(config)
        env.reset()
        
        assert not env.success()
        
        env._goal_achieved = True
        assert env.success()
    
    def test_get_metrics(self):
        """Test get_metrics method."""
        config = {"allowed_commands": ["ls"], "goal_description": "Test", "working_directory": "/tmp"}
        env = CommandLineEnv(config)
        env.reset()
        
        # Execute some commands
        env._command_history = ["ls", "cat file.txt"]
        
        metrics = env.get_metrics()
        
        assert isinstance(metrics, dict)
        assert metrics["commands_executed"] == 2.0
        assert metrics["goal_achieved"] == 0.0
        assert "steps_taken" in metrics


class TestCrossLanguageFixEnv:
    """Test CrossLanguageFixEnv environment."""
    
    def test_initialization(self):
        """Test environment initialization."""
        config = {
            "languages": ["python", "javascript", "java"],
            "bug_description": "Cross-language integration bug",
            "project_structure": {"python": ["main.py"], "javascript": ["app.js"]}
        }
        
        env = CrossLanguageFixEnv(config)
        
        assert env.languages == ["python", "javascript", "java"]
        assert env.bug_description == "Cross-language integration bug"
        assert env.project_structure == {"python": ["main.py"], "javascript": ["app.js"]}
        assert env._fixes_applied == {}
        assert not env._all_tests_passing
    
    def test_reset(self):
        """Test environment reset."""
        config = {
            "languages": ["python", "javascript"],
            "bug_description": "Integration bug",
            "project_structure": {}
        }
        
        env = CrossLanguageFixEnv(config)
        observation = env.reset()
        
        assert env._initialized
        assert env._fixes_applied == {}
        assert not env._all_tests_passing
        assert observation["type"] == "project_loaded"
        assert observation["languages"] == ["python", "javascript"]
        assert "available_commands" in observation
    
    def test_fix_python_action(self):
        """Test fix Python action."""
        config = {"languages": ["python", "javascript"], "bug_description": "Test", "project_structure": {}}
        env = CrossLanguageFixEnv(config)
        env.reset()
        
        action = {"command": "fix_python"}
        observation, reward, done, info = env.step(action)
        
        assert observation["type"] == "fix_applied"
        assert observation["language"] == "python"
        assert env._fixes_applied["python"] is True
        assert reward > 0
        assert not done  # Not done until all languages are fixed
    
    def test_fix_invalid_language(self):
        """Test fix action for invalid language."""
        config = {"languages": ["python"], "bug_description": "Test", "project_structure": {}}
        env = CrossLanguageFixEnv(config)
        env.reset()
        
        action = {"command": "fix_java"}
        observation, reward, done, info = env.step(action)
        
        assert observation["type"] == "invalid_language"
        assert observation["language"] == "java"
        assert reward < 0
        assert not done
    
    def test_run_tests_all_fixed(self):
        """Test run tests when all languages are fixed."""
        config = {"languages": ["python", "javascript"], "bug_description": "Test", "project_structure": {}}
        env = CrossLanguageFixEnv(config)
        env.reset()
        
        # Fix all languages first
        env._fixes_applied = {"python": True, "javascript": True}
        
        action = {"command": "run_tests"}
        observation, reward, done, info = env.step(action)
        
        assert observation["type"] == "test_results"
        assert observation["all_passing"] is True
        assert env._all_tests_passing
        assert reward == 1.0
        assert done
    
    def test_run_tests_not_all_fixed(self):
        """Test run tests when not all languages are fixed."""
        config = {"languages": ["python", "javascript"], "bug_description": "Test", "project_structure": {}}
        env = CrossLanguageFixEnv(config)
        env.reset()
        
        # Fix only one language
        env._fixes_applied = {"python": True}
        
        action = {"command": "run_tests"}
        observation, reward, done, info = env.step(action)
        
        assert observation["type"] == "test_results"
        assert observation["all_passing"] is False
        assert not env._all_tests_passing
        assert reward < 1.0
        assert not done
    
    def test_success_method(self):
        """Test success method."""
        config = {"languages": ["python"], "bug_description": "Test", "project_structure": {}}
        env = CrossLanguageFixEnv(config)
        env.reset()
        
        assert not env.success()
        
        env._all_tests_passing = True
        assert env.success()
    
    def test_get_metrics(self):
        """Test get_metrics method."""
        config = {"languages": ["python", "javascript", "java"], "bug_description": "Test", "project_structure": {}}
        env = CrossLanguageFixEnv(config)
        env.reset()
        
        # Fix some languages
        env._fixes_applied = {"python": True, "javascript": True}
        
        metrics = env.get_metrics()
        
        assert isinstance(metrics, dict)
        assert metrics["fix_completion_rate"] == 2.0 / 3.0  # 2 out of 3 languages fixed
        assert metrics["languages_fixed"] == 2.0
        assert metrics["all_tests_passing"] == 0.0
        assert "steps_taken" in metrics


if __name__ == "__main__":
    pytest.main([__file__])