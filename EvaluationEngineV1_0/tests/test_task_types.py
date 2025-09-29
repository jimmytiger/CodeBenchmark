"""
Unit tests for the task type system.

This module tests the BaseTask, SingleTurnTask, and MultiTurnTask classes
to ensure they properly implement the unified task type architecture.
"""

import pytest
from datetime import datetime
from typing import Any, Dict, List

import sys
import os
sys.path.insert(0, os.path.join(os.path.dirname(__file__), '..', '..'))

from EvaluationEngineV1_0.core.task_types import (
    BaseTask, SingleTurnTask, MultiTurnTask, TaskType,
    TaskResult, TurnData, TurnResult
)
from EvaluationEngineV1_0.core.exceptions import (
    ConfigurationError, TaskExecutionError
)


class TestTaskResult:
    """Test cases for TaskResult dataclass."""
    
    def test_task_result_creation(self):
        """Test basic TaskResult creation."""
        result = TaskResult(
            task_id="test_task",
            success=True,
            score=0.85,
            execution_time=1.5,
            metadata={"key": "value"}
        )
        
        assert result.task_id == "test_task"
        assert result.success is True
        assert result.score == 0.85
        assert result.execution_time == 1.5
        assert result.metadata == {"key": "value"}
        assert result.error is None
        assert isinstance(result.timestamp, datetime)
    
    def test_task_result_with_error(self):
        """Test TaskResult creation with error."""
        result = TaskResult(
            task_id="failed_task",
            success=False,
            score=0.0,
            execution_time=0.5,
            metadata={},
            error="Task execution failed"
        )
        
        assert result.success is False
        assert result.error == "Task execution failed"
    
    def test_task_result_score_validation(self):
        """Test that TaskResult validates score range."""
        # Valid scores
        TaskResult("test", True, 0.0, 1.0, {})
        TaskResult("test", True, 1.0, 1.0, {})
        TaskResult("test", True, 0.5, 1.0, {})
        
        # Invalid scores
        with pytest.raises(ValueError, match="Score must be between 0.0 and 1.0"):
            TaskResult("test", True, -0.1, 1.0, {})
        
        with pytest.raises(ValueError, match="Score must be between 0.0 and 1.0"):
            TaskResult("test", True, 1.1, 1.0, {})


class TestTurnData:
    """Test cases for TurnData dataclass."""
    
    def test_turn_data_creation(self):
        """Test basic TurnData creation."""
        turn_data = TurnData(
            turn_number=1,
            input_context="Initial context",
            previous_actions=[],
            environment_state={"step": 0}
        )
        
        assert turn_data.turn_number == 1
        assert turn_data.input_context == "Initial context"
        assert turn_data.previous_actions == []
        assert turn_data.environment_state == {"step": 0}
        assert isinstance(turn_data.timestamp, datetime)
    
    def test_turn_data_validation(self):
        """Test TurnData validation."""
        # Valid turn number
        TurnData(1, "context", [], {})
        
        # Invalid turn number
        with pytest.raises(ValueError, match="Turn number must be >= 1"):
            TurnData(0, "context", [], {})
        
        with pytest.raises(ValueError, match="Turn number must be >= 1"):
            TurnData(-1, "context", [], {})


class TestTurnResult:
    """Test cases for TurnResult dataclass."""
    
    def test_turn_result_creation(self):
        """Test basic TurnResult creation."""
        turn_result = TurnResult(
            turn=1,
            action="test_action",
            observation="test_observation",
            reward=0.5,
            done=False,
            info={"key": "value"},
            execution_time=1.0
        )
        
        assert turn_result.turn == 1
        assert turn_result.action == "test_action"
        assert turn_result.observation == "test_observation"
        assert turn_result.reward == 0.5
        assert turn_result.done is False
        assert turn_result.info == {"key": "value"}
        assert turn_result.execution_time == 1.0
        assert turn_result.tokens_used == 0
        assert turn_result.cost == 0.0
        assert isinstance(turn_result.timestamp, datetime)


class MockSingleTurnTask(SingleTurnTask):
    """Mock implementation of SingleTurnTask for testing."""
    
    def execute(self, input_data: Any) -> TaskResult:
        """Mock execute method."""
        return TaskResult(
            task_id=self.task_id,
            success=True,
            score=0.8,
            execution_time=1.0,
            metadata={"input": str(input_data)}
        )
    
    def get_required_capabilities(self) -> List[str]:
        """Mock capabilities."""
        return ["python"]


class MockMultiTurnTask(MultiTurnTask):
    """Mock implementation of MultiTurnTask for testing."""
    
    def __init__(self, task_id: str, config: Dict[str, Any]):
        super().__init__(task_id, config)
        self._turn_count = 0
        self._success = False
    
    def execute_turn(self, turn_data: TurnData) -> TurnResult:
        """Mock execute_turn method."""
        self._turn_count += 1
        done = self._turn_count >= 3  # Complete after 3 turns
        if done:
            self._success = True
        
        return TurnResult(
            turn=turn_data.turn_number,
            action=f"action_{self._turn_count}",
            observation=f"observation_{self._turn_count}",
            reward=0.5 if not done else 1.0,
            done=done,
            info={"turn_count": self._turn_count},
            execution_time=0.5
        )
    
    def should_continue(self, turn_result: TurnResult) -> bool:
        """Mock should_continue method."""
        return not turn_result.done
    
    def get_initial_context(self) -> str:
        """Mock initial context."""
        return "Initial context for multi-turn task"
    
    def is_successful(self, turn_results: List[TurnResult]) -> bool:
        """Mock success check."""
        return self._success
    
    def get_required_capabilities(self) -> List[str]:
        """Mock capabilities."""
        return ["python", "git"]


class TestBaseTask:
    """Test cases for BaseTask abstract class."""
    
    def test_base_task_cannot_be_instantiated(self):
        """Test that BaseTask cannot be instantiated directly."""
        with pytest.raises(TypeError):
            BaseTask("test", {})
    
    def test_base_task_initialization(self):
        """Test BaseTask initialization through subclass."""
        config = {"timeout": 30, "max_tokens": 1000}
        task = MockSingleTurnTask("test_task", config)
        
        assert task.get_id() == "test_task"
        assert task.get_config() == config
        assert task.config is not config  # Should be a copy
    
    def test_base_task_config_validation(self):
        """Test configuration validation."""
        # Valid config
        valid_config = {"timeout": 30, "max_tokens": 1000}
        task = MockSingleTurnTask("test", valid_config)
        assert task.get_config() == valid_config
        
        # Invalid config type
        with pytest.raises(ConfigurationError, match="must be a dictionary"):
            MockSingleTurnTask("test", "invalid")


class TestSingleTurnTask:
    """Test cases for SingleTurnTask class."""
    
    def test_single_turn_task_type(self):
        """Test that SingleTurnTask returns correct type."""
        config = {"timeout": 30, "max_tokens": 1000}
        task = MockSingleTurnTask("test", config)
        assert task.get_task_type() == TaskType.SINGLE_TURN
    
    def test_single_turn_task_execution(self):
        """Test SingleTurnTask execution."""
        config = {"timeout": 30, "max_tokens": 1000}
        task = MockSingleTurnTask("test", config)
        
        result = task.execute("test input")
        
        assert isinstance(result, TaskResult)
        assert result.task_id == "test"
        assert result.success is True
        assert result.score == 0.8
        assert result.metadata["input"] == "test input"
    
    def test_single_turn_task_config_validation(self):
        """Test SingleTurnTask configuration validation."""
        # Valid config
        valid_config = {"timeout": 30, "max_tokens": 1000}
        task = MockSingleTurnTask("test", valid_config)
        assert task.validate_config(valid_config) is True
        
        # Missing required fields
        with pytest.raises(ConfigurationError, match="Missing required field: timeout"):
            MockSingleTurnTask("test", {"max_tokens": 1000})
        
        with pytest.raises(ConfigurationError, match="Missing required field: max_tokens"):
            MockSingleTurnTask("test", {"timeout": 30})
        
        # Invalid timeout
        with pytest.raises(ConfigurationError, match="timeout must be a positive number"):
            MockSingleTurnTask("test", {"timeout": -1, "max_tokens": 1000})
        
        with pytest.raises(ConfigurationError, match="timeout must be a positive number"):
            MockSingleTurnTask("test", {"timeout": "invalid", "max_tokens": 1000})
        
        # Invalid max_tokens
        with pytest.raises(ConfigurationError, match="max_tokens must be a positive integer"):
            MockSingleTurnTask("test", {"timeout": 30, "max_tokens": -1})
        
        with pytest.raises(ConfigurationError, match="max_tokens must be a positive integer"):
            MockSingleTurnTask("test", {"timeout": 30, "max_tokens": "invalid"})
    
    def test_single_turn_task_capabilities(self):
        """Test SingleTurnTask capabilities."""
        config = {"timeout": 30, "max_tokens": 1000}
        task = MockSingleTurnTask("test", config)
        capabilities = task.get_required_capabilities()
        
        assert isinstance(capabilities, list)
        assert "python" in capabilities


class TestMultiTurnTask:
    """Test cases for MultiTurnTask class."""
    
    def test_multi_turn_task_type(self):
        """Test that MultiTurnTask returns correct type."""
        config = {"max_turns": 5, "turn_timeout": 30, "max_tokens_per_turn": 1000}
        task = MockMultiTurnTask("test", config)
        assert task.get_task_type() == TaskType.MULTI_TURN
    
    def test_multi_turn_task_execution(self):
        """Test MultiTurnTask turn execution."""
        config = {"max_turns": 5, "turn_timeout": 30, "max_tokens_per_turn": 1000}
        task = MockMultiTurnTask("test", config)
        
        # Execute first turn
        turn_data = TurnData(1, "context", [], {})
        result1 = task.execute_turn(turn_data)
        
        assert isinstance(result1, TurnResult)
        assert result1.turn == 1
        assert result1.done is False
        assert task.should_continue(result1) is True
        
        # Execute more turns until completion
        turn_results = [result1]
        for turn_num in range(2, 4):
            turn_data = TurnData(turn_num, "context", [], {})
            result = task.execute_turn(turn_data)
            turn_results.append(result)
            
            if result.done:
                break
        
        # Check final state
        final_result = turn_results[-1]
        assert final_result.done is True
        assert task.should_continue(final_result) is False
        assert task.is_successful(turn_results) is True
    
    def test_multi_turn_task_initial_context(self):
        """Test MultiTurnTask initial context."""
        config = {"max_turns": 5, "turn_timeout": 30, "max_tokens_per_turn": 1000}
        task = MockMultiTurnTask("test", config)
        
        context = task.get_initial_context()
        assert isinstance(context, str)
        assert len(context) > 0
    
    def test_multi_turn_task_config_validation(self):
        """Test MultiTurnTask configuration validation."""
        # Valid config
        valid_config = {"max_turns": 5, "turn_timeout": 30, "max_tokens_per_turn": 1000}
        task = MockMultiTurnTask("test", valid_config)
        assert task.validate_config(valid_config) is True
        
        # Missing required fields
        with pytest.raises(ConfigurationError, match="Missing required field: max_turns"):
            MockMultiTurnTask("test", {"turn_timeout": 30, "max_tokens_per_turn": 1000})
        
        # Invalid max_turns
        with pytest.raises(ConfigurationError, match="max_turns must be a positive integer"):
            MockMultiTurnTask("test", {"max_turns": -1, "turn_timeout": 30, "max_tokens_per_turn": 1000})
        
        # Invalid turn_timeout
        with pytest.raises(ConfigurationError, match="turn_timeout must be a positive number"):
            MockMultiTurnTask("test", {"max_turns": 5, "turn_timeout": -1, "max_tokens_per_turn": 1000})
        
        # Invalid max_tokens_per_turn
        with pytest.raises(ConfigurationError, match="max_tokens_per_turn must be a positive integer"):
            MockMultiTurnTask("test", {"max_turns": 5, "turn_timeout": 30, "max_tokens_per_turn": -1})
    
    def test_multi_turn_task_final_result_calculation(self):
        """Test MultiTurnTask final result calculation."""
        config = {"max_turns": 5, "turn_timeout": 30, "max_tokens_per_turn": 1000}
        task = MockMultiTurnTask("test", config)
        
        # Create some turn results
        turn_results = []
        for i in range(3):
            turn_result = TurnResult(
                turn=i+1,
                action=f"action_{i+1}",
                observation=f"obs_{i+1}",
                reward=0.5,
                done=(i == 2),  # Last turn is done
                info={},
                execution_time=1.0,
                tokens_used=100,
                cost=0.01
            )
            turn_results.append(turn_result)
        
        # Calculate final result
        final_result = task.calculate_final_result(turn_results)
        
        assert isinstance(final_result, TaskResult)
        assert final_result.task_id == "test"
        assert final_result.execution_time == 3.0  # Sum of all turn times
        assert final_result.metadata["turns"] == 3
        assert final_result.metadata["total_tokens"] == 300
        assert final_result.metadata["total_cost"] == 0.03
    
    def test_multi_turn_task_empty_results(self):
        """Test MultiTurnTask with no turn results."""
        config = {"max_turns": 5, "turn_timeout": 30, "max_tokens_per_turn": 1000}
        task = MockMultiTurnTask("test", config)
        
        final_result = task.calculate_final_result([])
        
        assert final_result.success is False
        assert final_result.score == 0.0
        assert final_result.execution_time == 0.0
        assert final_result.metadata["turns"] == 0
        assert "No turns executed" in final_result.metadata["error"]
    
    def test_multi_turn_task_capabilities(self):
        """Test MultiTurnTask capabilities."""
        config = {"max_turns": 5, "turn_timeout": 30, "max_tokens_per_turn": 1000}
        task = MockMultiTurnTask("test", config)
        capabilities = task.get_required_capabilities()
        
        assert isinstance(capabilities, list)
        assert "python" in capabilities
        assert "git" in capabilities


class TestTaskType:
    """Test cases for TaskType enum."""
    
    def test_task_type_values(self):
        """Test TaskType enum values."""
        assert TaskType.SINGLE_TURN.value == "single_turn"
        assert TaskType.MULTI_TURN.value == "multi_turn"
    
    def test_task_type_comparison(self):
        """Test TaskType comparison."""
        assert TaskType.SINGLE_TURN != TaskType.MULTI_TURN
        assert TaskType.SINGLE_TURN == TaskType.SINGLE_TURN