"""
Unified environment interface for the Multi-Turn Evaluation Engine.

This module defines the standardized environment interface that all evaluation
tasks must implement, providing consistent execution patterns across different
benchmark sources and task types.
"""

from abc import ABC, abstractmethod
from typing import Any, Dict, List, Optional, Tuple, Union
from dataclasses import dataclass
from datetime import datetime

from .exceptions import TaskExecutionError, SafetyViolationError


# Type aliases for clarity
Observation = Union[str, Dict[str, Any], List[Any]]
Action = Union[str, Dict[str, Any], List[Any]]
Reward = float
Info = Dict[str, Any]


@dataclass
class EnvironmentState:
    """Represents the current state of an evaluation environment.
    
    Attributes:
        step_count: Number of steps taken in this environment
        is_done: Whether the environment has reached a terminal state
        last_reward: The most recent reward received
        metadata: Environment-specific state information
        timestamp: When this state was captured
    """
    step_count: int
    is_done: bool
    last_reward: float
    metadata: Dict[str, Any]
    timestamp: datetime = None
    
    def __post_init__(self):
        if self.timestamp is None:
            self.timestamp = datetime.now()


@dataclass
class StepResult:
    """Result of a single environment step.
    
    Attributes:
        observation: The observation received after taking the action
        reward: The reward received for the action
        done: Whether the environment has reached a terminal state
        info: Additional information about the step
        execution_time: Time taken to execute the step
    """
    observation: Observation
    reward: Reward
    done: bool
    info: Info
    execution_time: float = 0.0
    timestamp: datetime = None
    
    def __post_init__(self):
        if self.timestamp is None:
            self.timestamp = datetime.now()


class UnifiedEnv(ABC):
    """Unified environment interface for all evaluation tasks.
    
    This abstract base class defines the standard interface that all evaluation
    environments must implement, regardless of their underlying benchmark source
    or task complexity. It follows the OpenAI Gym-style interface with additional
    methods for evaluation-specific functionality.
    """
    
    def __init__(self, config: Dict[str, Any]):
        """Initialize the environment.
        
        Args:
            config: Configuration dictionary for the environment
        """
        self.config = config.copy()
        self._state = EnvironmentState(
            step_count=0,
            is_done=False,
            last_reward=0.0,
            metadata={}
        )
        self._initialized = False
    
    @abstractmethod
    def reset(self) -> Observation:
        """Reset the environment to its initial state.
        
        This method should restore the environment to a clean starting state
        and return the initial observation that will be provided to the agent.
        
        Returns:
            Initial observation for the agent
            
        Raises:
            TaskExecutionError: If reset fails
        """
        pass
    
    @abstractmethod
    def step(self, action: Action) -> Tuple[Observation, Reward, bool, Info]:
        """Execute an action in the environment.
        
        This method executes the given action, updates the environment state,
        and returns the resulting observation, reward, termination status,
        and additional information.
        
        Args:
            action: The action to execute
            
        Returns:
            Tuple of (observation, reward, done, info) where:
            - observation: The new observation after the action
            - reward: The reward received for this action
            - done: Whether the environment has reached a terminal state
            - info: Additional information about the step
            
        Raises:
            TaskExecutionError: If action execution fails
            SafetyViolationError: If action violates safety policies
        """
        pass
    
    @abstractmethod
    def success(self) -> bool:
        """Check if the task has been completed successfully.
        
        This method determines whether the current state represents
        successful completion of the evaluation task.
        
        Returns:
            True if the task has been completed successfully
        """
        pass
    
    @abstractmethod
    def info(self) -> Dict[str, Any]:
        """Get current environment information and metadata.
        
        This method returns detailed information about the current
        environment state, including metrics, diagnostics, and
        task-specific metadata.
        
        Returns:
            Dictionary containing environment information
        """
        pass
    
    @abstractmethod
    def get_metrics(self) -> Dict[str, float]:
        """Get current performance metrics.
        
        This method returns quantitative metrics about the current
        evaluation state, such as progress indicators, efficiency
        measures, and quality scores.
        
        Returns:
            Dictionary mapping metric names to values
        """
        pass
    
    def get_state(self) -> EnvironmentState:
        """Get the current environment state.
        
        Returns:
            Current EnvironmentState object
        """
        return self._state
    
    def is_initialized(self) -> bool:
        """Check if the environment has been initialized.
        
        Returns:
            True if reset() has been called successfully
        """
        return self._initialized
    
    def get_config(self) -> Dict[str, Any]:
        """Get the environment configuration.
        
        Returns:
            Copy of the environment configuration
        """
        return self.config.copy()
    
    def validate_action(self, action: Action) -> Tuple[bool, Optional[str]]:
        """Validate an action before execution.
        
        This method can be overridden by subclasses to implement
        action validation logic, such as checking for dangerous
        commands or invalid parameters.
        
        Args:
            action: The action to validate
            
        Returns:
            Tuple of (is_valid, error_message)
        """
        return True, None
    
    def cleanup(self) -> None:
        """Clean up environment resources.
        
        This method should be called when the environment is no longer
        needed to ensure proper cleanup of resources like temporary files,
        processes, or network connections.
        """
        pass
    
    def _update_state(self, reward: float, done: bool, metadata: Dict[str, Any]) -> None:
        """Update the internal environment state.
        
        Args:
            reward: The reward from the last step
            done: Whether the environment is in a terminal state
            metadata: Additional metadata to store
        """
        self._state.step_count += 1
        self._state.last_reward = reward
        self._state.is_done = done
        self._state.metadata.update(metadata)
        self._state.timestamp = datetime.now()
    
    def _mark_initialized(self) -> None:
        """Mark the environment as initialized.
        
        This should be called by subclasses after successful reset().
        """
        self._initialized = True
        self._state.step_count = 0
        self._state.is_done = False
        self._state.last_reward = 0.0
        self._state.metadata.clear()
        self._state.timestamp = datetime.now()


class MockEnvironment(UnifiedEnv):
    """Mock environment implementation for testing purposes.
    
    This class provides a simple implementation of the UnifiedEnv interface
    that can be used for testing and development without requiring external
    dependencies or complex setup.
    """
    
    def __init__(self, config: Dict[str, Any]):
        """Initialize the mock environment.
        
        Args:
            config: Configuration dictionary. Supports:
                - max_steps: Maximum number of steps before termination
                - success_probability: Probability of success on each step
                - reward_range: Tuple of (min_reward, max_reward)
        """
        super().__init__(config)
        self.max_steps = config.get("max_steps", 10)
        self.success_probability = config.get("success_probability", 0.1)
        self.reward_range = config.get("reward_range", (0.0, 1.0))
        self._successful = False
        self._observations = []
    
    def reset(self) -> Observation:
        """Reset the mock environment.
        
        Returns:
            Initial observation string
        """
        self._mark_initialized()
        self._successful = False
        self._observations = []
        
        initial_obs = f"Mock environment initialized. Max steps: {self.max_steps}"
        self._observations.append(initial_obs)
        return initial_obs
    
    def step(self, action: Action) -> Tuple[Observation, Reward, bool, Info]:
        """Execute a step in the mock environment.
        
        Args:
            action: The action to execute (can be any type)
            
        Returns:
            Tuple of (observation, reward, done, info)
        """
        if not self._initialized:
            raise TaskExecutionError("Environment not initialized. Call reset() first.")
        
        if self._state.is_done:
            raise TaskExecutionError("Environment is already in terminal state.")
        
        # Simulate action execution
        import random
        
        # Determine if this step is successful
        step_successful = random.random() < self.success_probability
        if step_successful:
            self._successful = True
        
        # Calculate reward
        reward = random.uniform(*self.reward_range)
        if step_successful:
            reward = max(reward, 0.8)  # Boost reward for success
        
        # Determine if episode is done
        done = (self._successful or 
                self._state.step_count >= self.max_steps - 1)
        
        # Create observation
        observation = (f"Step {self._state.step_count + 1}: "
                      f"Action '{action}' executed. "
                      f"Success: {step_successful}")
        self._observations.append(observation)
        
        # Create info
        info = {
            "step_successful": step_successful,
            "total_successful": self._successful,
            "steps_remaining": max(0, self.max_steps - self._state.step_count - 1),
            "action_type": type(action).__name__,
            "observation_history": self._observations.copy()
        }
        
        # Update state
        self._update_state(reward, done, {"step_successful": step_successful})
        
        return observation, reward, done, info
    
    def success(self) -> bool:
        """Check if the task was completed successfully.
        
        Returns:
            True if the task was successful
        """
        return self._successful
    
    def info(self) -> Dict[str, Any]:
        """Get current environment information.
        
        Returns:
            Dictionary with environment information
        """
        return {
            "environment_type": "mock",
            "initialized": self._initialized,
            "successful": self._successful,
            "step_count": self._state.step_count,
            "max_steps": self.max_steps,
            "is_done": self._state.is_done,
            "last_reward": self._state.last_reward,
            "observation_count": len(self._observations),
            "config": self.get_config()
        }
    
    def get_metrics(self) -> Dict[str, float]:
        """Get current performance metrics.
        
        Returns:
            Dictionary of performance metrics
        """
        progress = self._state.step_count / self.max_steps if self.max_steps > 0 else 0.0
        success_rate = 1.0 if self._successful else 0.0
        efficiency = (1.0 - progress) if self._successful else 0.0
        
        return {
            "progress": progress,
            "success_rate": success_rate,
            "efficiency": efficiency,
            "steps_taken": float(self._state.step_count),
            "average_reward": self._state.last_reward
        }