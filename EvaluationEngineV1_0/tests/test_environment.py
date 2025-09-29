"""
Unit tests for the unified environment interface.

This module tests the UnifiedEnv abstract class and its implementations
to ensure they provide consistent execution patterns across different
evaluation scenarios.
"""

import pytest
from datetime import datetime
from typing import Any, Dict, Tuple

import sys
import os
sys.path.insert(0, os.path.join(os.path.dirname(__file__), '..', '..'))

from EvaluationEngineV1_0.core.environment import (
    UnifiedEnv, MockEnvironment, EnvironmentState, StepResult,
    Observation, Action, Reward, Info
)
from EvaluationEngineV1_0.core.exceptions import TaskExecutionError


class TestEnvironmentState:
    """Test cases for EnvironmentState dataclass."""
    
    def test_environment_state_creation(self):
        """Test basic EnvironmentState creation."""
        state = EnvironmentState(
            step_count=5,
            is_done=False,
            last_reward=0.8,
            metadata={"key": "value"}
        )
        
        assert state.step_count == 5
        assert state.is_done is False
        assert state.last_reward == 0.8
        assert state.metadata == {"key": "value"}
        assert isinstance(state.timestamp, datetime)
    
    def test_environment_state_auto_timestamp(self):
        """Test that EnvironmentState automatically sets timestamp."""
        state = EnvironmentState(0, False, 0.0, {})
        assert isinstance(state.timestamp, datetime)
        
        # Test with explicit timestamp
        explicit_time = datetime(2023, 1, 1, 12, 0, 0)
        state_with_time = EnvironmentState(0, False, 0.0, {}, explicit_time)
        assert state_with_time.timestamp == explicit_time


class TestStepResult:
    """Test cases for StepResult dataclass."""
    
    def test_step_result_creation(self):
        """Test basic StepResult creation."""
        result = StepResult(
            observation="test observation",
            reward=0.5,
            done=False,
            info={"step": 1},
            execution_time=1.2
        )
        
        assert result.observation == "test observation"
        assert result.reward == 0.5
        assert result.done is False
        assert result.info == {"step": 1}
        assert result.execution_time == 1.2
        assert isinstance(result.timestamp, datetime)
    
    def test_step_result_defaults(self):
        """Test StepResult with default values."""
        result = StepResult(
            observation="test",
            reward=0.0,
            done=True,
            info={}
        )
        
        assert result.execution_time == 0.0
        assert isinstance(result.timestamp, datetime)


class MockTestEnvironment(UnifiedEnv):
    """Simple mock environment for testing UnifiedEnv base functionality."""
    
    def __init__(self, config: Dict[str, Any]):
        super().__init__(config)
        self._step_count = 0
        self._is_successful = False
    
    def reset(self) -> Observation:
        """Reset the test environment."""
        self._mark_initialized()
        self._step_count = 0
        self._is_successful = False
        return "Initial observation"
    
    def step(self, action: Action) -> Tuple[Observation, Reward, bool, Info]:
        """Execute a step in the test environment."""
        if not self._initialized:
            raise TaskExecutionError("Environment not initialized")
        
        self._step_count += 1
        reward = 0.1 * self._step_count
        done = self._step_count >= 3
        
        if done:
            self._is_successful = True
        
        observation = f"Step {self._step_count} with action: {action}"
        info = {"step": self._step_count, "action": str(action)}
        
        self._update_state(reward, done, info)
        
        return observation, reward, done, info
    
    def success(self) -> bool:
        """Check if task was successful."""
        return self._is_successful
    
    def info(self) -> Dict[str, Any]:
        """Get environment info."""
        return {
            "step_count": self._step_count,
            "successful": self._is_successful,
            "initialized": self._initialized
        }
    
    def get_metrics(self) -> Dict[str, float]:
        """Get performance metrics."""
        return {
            "progress": self._step_count / 3.0,
            "success_rate": 1.0 if self._is_successful else 0.0
        }


class TestUnifiedEnv:
    """Test cases for UnifiedEnv abstract base class."""
    
    def test_unified_env_cannot_be_instantiated(self):
        """Test that UnifiedEnv cannot be instantiated directly."""
        with pytest.raises(TypeError):
            UnifiedEnv({})
    
    def test_unified_env_initialization(self):
        """Test UnifiedEnv initialization through subclass."""
        config = {"test": "value"}
        env = MockTestEnvironment(config)
        
        assert env.get_config() == config
        assert env.config is not config  # Should be a copy
        assert not env.is_initialized()
        
        # Check initial state
        state = env.get_state()
        assert state.step_count == 0
        assert state.is_done is False
        assert state.last_reward == 0.0
        assert state.metadata == {}
    
    def test_unified_env_reset_and_initialization(self):
        """Test environment reset and initialization."""
        env = MockTestEnvironment({})
        
        # Initially not initialized
        assert not env.is_initialized()
        
        # Reset should initialize
        obs = env.reset()
        assert env.is_initialized()
        assert obs == "Initial observation"
        
        # State should be reset
        state = env.get_state()
        assert state.step_count == 0
        assert state.is_done is False
    
    def test_unified_env_step_execution(self):
        """Test environment step execution."""
        env = MockTestEnvironment({})
        env.reset()
        
        # Execute first step
        obs, reward, done, info = env.step("test_action")
        
        assert obs == "Step 1 with action: test_action"
        assert reward == 0.1
        assert done is False
        assert info["step"] == 1
        assert info["action"] == "test_action"
        
        # Check state update
        state = env.get_state()
        assert state.step_count == 1
        assert state.last_reward == 0.1
        assert state.is_done is False
    
    def test_unified_env_step_without_reset(self):
        """Test that step fails without reset."""
        env = MockTestEnvironment({})
        
        with pytest.raises(TaskExecutionError, match="Environment not initialized"):
            env.step("action")
    
    def test_unified_env_complete_episode(self):
        """Test complete episode execution."""
        env = MockTestEnvironment({})
        env.reset()
        
        # Execute steps until done
        step_count = 0
        done = False
        
        while not done and step_count < 5:  # Safety limit
            obs, reward, done, info = env.step(f"action_{step_count}")
            step_count += 1
        
        assert done is True
        assert env.success() is True
        assert step_count == 3  # Should complete in 3 steps
        
        # Check final state
        state = env.get_state()
        assert state.step_count == 3
        assert state.is_done is True
    
    def test_unified_env_info_and_metrics(self):
        """Test environment info and metrics."""
        env = MockTestEnvironment({})
        env.reset()
        
        # Initial info and metrics
        info = env.info()
        metrics = env.get_metrics()
        
        assert info["step_count"] == 0
        assert info["successful"] is False
        assert info["initialized"] is True
        
        assert metrics["progress"] == 0.0
        assert metrics["success_rate"] == 0.0
        
        # After some steps
        env.step("action1")
        env.step("action2")
        
        info = env.info()
        metrics = env.get_metrics()
        
        assert info["step_count"] == 2
        assert metrics["progress"] == 2.0 / 3.0
    
    def test_unified_env_action_validation(self):
        """Test action validation."""
        env = MockTestEnvironment({})
        
        # Default validation should pass
        is_valid, error = env.validate_action("any_action")
        assert is_valid is True
        assert error is None
    
    def test_unified_env_cleanup(self):
        """Test environment cleanup."""
        env = MockTestEnvironment({})
        
        # Should not raise any errors
        env.cleanup()


class TestMockEnvironment:
    """Test cases for MockEnvironment implementation."""
    
    def test_mock_environment_creation(self):
        """Test MockEnvironment creation with default config."""
        env = MockEnvironment({})
        
        assert env.max_steps == 10
        assert env.success_probability == 0.1
        assert env.reward_range == (0.0, 1.0)
        assert not env.is_initialized()
    
    def test_mock_environment_custom_config(self):
        """Test MockEnvironment with custom configuration."""
        config = {
            "max_steps": 5,
            "success_probability": 0.5,
            "reward_range": (0.2, 0.8)
        }
        env = MockEnvironment(config)
        
        assert env.max_steps == 5
        assert env.success_probability == 0.5
        assert env.reward_range == (0.2, 0.8)
    
    def test_mock_environment_reset(self):
        """Test MockEnvironment reset."""
        env = MockEnvironment({"max_steps": 3})
        
        obs = env.reset()
        
        assert env.is_initialized()
        assert "Mock environment initialized" in obs
        assert "Max steps: 3" in obs
        assert not env._successful
        assert len(env._observations) == 1
    
    def test_mock_environment_step_execution(self):
        """Test MockEnvironment step execution."""
        # Use high success probability for predictable testing
        env = MockEnvironment({
            "max_steps": 2,
            "success_probability": 1.0,  # Always succeed
            "reward_range": (0.8, 1.0)
        })
        env.reset()
        
        obs, reward, done, info = env.step("test_action")
        
        assert "Step 1" in obs
        assert "test_action" in obs
        assert reward >= 0.8  # Should be high due to success
        assert done is True  # Should be done due to success
        assert info["step_successful"] is True
        assert info["total_successful"] is True
        assert env.success() is True
    
    def test_mock_environment_max_steps(self):
        """Test MockEnvironment respects max_steps."""
        env = MockEnvironment({
            "max_steps": 2,
            "success_probability": 0.0  # Never succeed
        })
        env.reset()
        
        # First step
        obs1, reward1, done1, info1 = env.step("action1")
        assert done1 is False
        assert info1["steps_remaining"] == 1
        
        # Second step (should be done due to max_steps)
        obs2, reward2, done2, info2 = env.step("action2")
        assert done2 is True
        assert info2["steps_remaining"] == 0
    
    def test_mock_environment_step_without_reset(self):
        """Test MockEnvironment step without reset."""
        env = MockEnvironment({})
        
        with pytest.raises(TaskExecutionError, match="Environment not initialized"):
            env.step("action")
    
    def test_mock_environment_step_after_done(self):
        """Test MockEnvironment step after episode is done."""
        env = MockEnvironment({"max_steps": 1})
        env.reset()
        
        # First step should complete the episode
        env.step("action1")
        
        # Second step should fail
        with pytest.raises(TaskExecutionError, match="already in terminal state"):
            env.step("action2")
    
    def test_mock_environment_info(self):
        """Test MockEnvironment info method."""
        config = {"max_steps": 3, "success_probability": 0.2}
        env = MockEnvironment(config)
        env.reset()
        
        info = env.info()
        
        assert info["environment_type"] == "mock"
        assert info["initialized"] is True
        assert info["successful"] is False
        assert info["step_count"] == 0
        assert info["max_steps"] == 3
        assert info["is_done"] is False
        assert info["observation_count"] == 1  # Reset creates one observation
        assert info["config"] == config
    
    def test_mock_environment_metrics(self):
        """Test MockEnvironment metrics calculation."""
        env = MockEnvironment({"max_steps": 4})
        env.reset()
        
        # Initial metrics
        metrics = env.get_metrics()
        assert metrics["progress"] == 0.0
        assert metrics["success_rate"] == 0.0
        assert metrics["efficiency"] == 0.0
        assert metrics["steps_taken"] == 0.0
        
        # After some steps
        env.step("action1")
        env.step("action2")
        
        metrics = env.get_metrics()
        assert metrics["progress"] == 2.0 / 4.0
        assert metrics["steps_taken"] == 2.0
        
        # If successful, efficiency should be calculated
        if env.success():
            assert metrics["success_rate"] == 1.0
            assert metrics["efficiency"] > 0.0
    
    def test_mock_environment_observation_history(self):
        """Test MockEnvironment maintains observation history."""
        env = MockEnvironment({"max_steps": 3})
        env.reset()
        
        # Execute a few steps
        env.step("action1")
        env.step("action2")
        
        info = env.info()
        assert info["observation_count"] == 3  # Reset + 2 steps
        
        # Check that observations are stored
        _, _, _, step_info = env.step("action3")
        history = step_info["observation_history"]
        assert len(history) == 4  # Reset + 3 steps
        assert "Mock environment initialized" in history[0]
        assert "action1" in history[1]
        assert "action2" in history[2]
        assert "action3" in history[3]