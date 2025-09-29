"""
Task type system for the Multi-Turn Evaluation Engine.

This module defines the unified task type architecture that supports both
single-turn and multi-turn evaluation scenarios through a common interface.
"""

from abc import ABC, abstractmethod
from enum import Enum
from typing import Any, Dict, List, Optional, Union
from dataclasses import dataclass
from datetime import datetime

from .exceptions import ConfigurationError, TaskExecutionError


class TaskType(Enum):
    """Enumeration of supported task types."""
    SINGLE_TURN = "single_turn"
    MULTI_TURN = "multi_turn"


@dataclass
class TaskResult:
    """Result of a task execution.
    
    Attributes:
        task_id: Unique identifier for the task
        success: Whether the task completed successfully
        score: Numerical score for the task (0.0 to 1.0)
        execution_time: Time taken to execute the task in seconds
        metadata: Additional task-specific information
        error: Error information if task failed
    """
    task_id: str
    success: bool
    score: float
    execution_time: float
    metadata: Dict[str, Any]
    error: Optional[str] = None
    timestamp: datetime = None
    
    def __post_init__(self):
        if self.timestamp is None:
            self.timestamp = datetime.now()
        
        # Validate score range
        if not 0.0 <= self.score <= 1.0:
            raise ValueError(f"Score must be between 0.0 and 1.0, got {self.score}")


@dataclass
class TurnData:
    """Data for a single turn in multi-turn evaluation.
    
    Attributes:
        turn_number: Sequential turn number (1-based)
        input_context: Context provided to the model for this turn
        previous_actions: List of actions taken in previous turns
        environment_state: Current state of the evaluation environment
        timestamp: When this turn was initiated
    """
    turn_number: int
    input_context: str
    previous_actions: List[Any]
    environment_state: Dict[str, Any]
    timestamp: datetime = None
    
    def __post_init__(self):
        if self.timestamp is None:
            self.timestamp = datetime.now()
        
        if self.turn_number < 1:
            raise ValueError(f"Turn number must be >= 1, got {self.turn_number}")


@dataclass 
class TurnResult:
    """Result of a single turn execution.
    
    Attributes:
        turn: Turn number this result corresponds to
        action: Action taken during this turn
        observation: Observation received after the action
        reward: Reward received for this turn
        done: Whether the task is complete after this turn
        info: Additional information about the turn
        execution_time: Time taken for this turn in seconds
        tokens_used: Number of tokens consumed (if applicable)
        cost: Cost incurred for this turn (if applicable)
    """
    turn: int
    action: Any
    observation: Any
    reward: float
    done: bool
    info: Dict[str, Any]
    execution_time: float
    tokens_used: int = 0
    cost: float = 0.0
    timestamp: datetime = None
    
    def __post_init__(self):
        if self.timestamp is None:
            self.timestamp = datetime.now()


class BaseTask(ABC):
    """Abstract base class for all evaluation tasks.
    
    This class defines the common interface that all tasks must implement,
    regardless of whether they are single-turn or multi-turn.
    """
    
    def __init__(self, task_id: str, config: Dict[str, Any]):
        """Initialize the base task.
        
        Args:
            task_id: Unique identifier for this task
            config: Configuration dictionary for the task
            
        Raises:
            ConfigurationError: If the configuration is invalid
        """
        self.task_id = task_id
        self._validate_config(config)
        self.config = config.copy() if isinstance(config, dict) else config
    
    @abstractmethod
    def get_task_type(self) -> TaskType:
        """Get the type of this task.
        
        Returns:
            TaskType enum value indicating single-turn or multi-turn
        """
        pass
    
    @abstractmethod
    def validate_config(self, config: Dict[str, Any]) -> bool:
        """Validate the task configuration.
        
        Args:
            config: Configuration dictionary to validate
            
        Returns:
            True if configuration is valid
            
        Raises:
            ConfigurationError: If configuration is invalid
        """
        pass
    
    @abstractmethod
    def get_required_capabilities(self) -> List[str]:
        """Get the list of capabilities required by this task.
        
        Returns:
            List of capability names (e.g., ["python", "git", "filesystem"])
        """
        pass
    
    def get_id(self) -> str:
        """Get the unique identifier for this task.
        
        Returns:
            Task ID string
        """
        return self.task_id
    
    def get_config(self) -> Dict[str, Any]:
        """Get the task configuration.
        
        Returns:
            Copy of the task configuration dictionary
        """
        return self.config.copy()
    
    def _validate_config(self, config: Dict[str, Any]) -> None:
        """Internal configuration validation.
        
        Args:
            config: Configuration to validate
            
        Raises:
            ConfigurationError: If configuration is invalid
        """
        if not isinstance(config, dict):
            raise ConfigurationError("Task configuration must be a dictionary")
        
        # Delegate to subclass validation
        try:
            self.validate_config(config)
        except Exception as e:
            if isinstance(e, ConfigurationError):
                raise
            raise ConfigurationError(f"Configuration validation failed: {str(e)}")


class SingleTurnTask(BaseTask):
    """Single-turn evaluation task.
    
    This class represents tasks that complete in a single interaction,
    such as traditional question-answering or code generation tasks.
    """
    
    def get_task_type(self) -> TaskType:
        """Get the task type.
        
        Returns:
            TaskType.SINGLE_TURN
        """
        return TaskType.SINGLE_TURN
    
    @abstractmethod
    def execute(self, input_data: Any) -> TaskResult:
        """Execute the single-turn evaluation.
        
        Args:
            input_data: Input data for the task
            
        Returns:
            TaskResult containing the evaluation outcome
            
        Raises:
            TaskExecutionError: If execution fails
        """
        pass
    
    def validate_config(self, config: Dict[str, Any]) -> bool:
        """Validate single-turn task configuration.
        
        Args:
            config: Configuration to validate
            
        Returns:
            True if valid
            
        Raises:
            ConfigurationError: If configuration is invalid
        """
        required_fields = ["timeout", "max_tokens"]
        for field in required_fields:
            if field not in config:
                raise ConfigurationError(f"Missing required field: {field}")
        
        if not isinstance(config["timeout"], (int, float)) or config["timeout"] <= 0:
            raise ConfigurationError("timeout must be a positive number")
        
        if not isinstance(config["max_tokens"], int) or config["max_tokens"] <= 0:
            raise ConfigurationError("max_tokens must be a positive integer")
        
        return True


class MultiTurnTask(BaseTask):
    """Multi-turn evaluation task with conversation state.
    
    This class represents tasks that require multiple interactions
    to complete, such as debugging sessions or iterative problem solving.
    """
    
    def get_task_type(self) -> TaskType:
        """Get the task type.
        
        Returns:
            TaskType.MULTI_TURN
        """
        return TaskType.MULTI_TURN
    
    @abstractmethod
    def execute_turn(self, turn_data: TurnData) -> TurnResult:
        """Execute a single turn in the multi-turn evaluation.
        
        Args:
            turn_data: Data for the current turn
            
        Returns:
            TurnResult containing the turn outcome
            
        Raises:
            TaskExecutionError: If turn execution fails
        """
        pass
    
    @abstractmethod
    def should_continue(self, turn_result: TurnResult) -> bool:
        """Determine if the evaluation should continue.
        
        Args:
            turn_result: Result of the most recent turn
            
        Returns:
            True if evaluation should continue, False if complete
        """
        pass
    
    @abstractmethod
    def get_initial_context(self) -> str:
        """Get the initial context for the first turn.
        
        Returns:
            Initial context string to provide to the model
        """
        pass
    
    @abstractmethod
    def is_successful(self, turn_results: List[TurnResult]) -> bool:
        """Determine if the overall task was successful.
        
        Args:
            turn_results: List of all turn results
            
        Returns:
            True if the task was completed successfully
        """
        pass
    
    def validate_config(self, config: Dict[str, Any]) -> bool:
        """Validate multi-turn task configuration.
        
        Args:
            config: Configuration to validate
            
        Returns:
            True if valid
            
        Raises:
            ConfigurationError: If configuration is invalid
        """
        required_fields = ["max_turns", "turn_timeout", "max_tokens_per_turn"]
        for field in required_fields:
            if field not in config:
                raise ConfigurationError(f"Missing required field: {field}")
        
        if not isinstance(config["max_turns"], int) or config["max_turns"] <= 0:
            raise ConfigurationError("max_turns must be a positive integer")
        
        if not isinstance(config["turn_timeout"], (int, float)) or config["turn_timeout"] <= 0:
            raise ConfigurationError("turn_timeout must be a positive number")
        
        if not isinstance(config["max_tokens_per_turn"], int) or config["max_tokens_per_turn"] <= 0:
            raise ConfigurationError("max_tokens_per_turn must be a positive integer")
        
        return True
    
    def calculate_final_result(self, turn_results: List[TurnResult]) -> TaskResult:
        """Calculate the final task result from all turn results.
        
        Args:
            turn_results: List of all turn results
            
        Returns:
            TaskResult summarizing the entire multi-turn evaluation
        """
        if not turn_results:
            return TaskResult(
                task_id=self.task_id,
                success=False,
                score=0.0,
                execution_time=0.0,
                metadata={"turns": 0, "error": "No turns executed"}
            )
        
        total_time = sum(tr.execution_time for tr in turn_results)
        total_tokens = sum(tr.tokens_used for tr in turn_results)
        total_cost = sum(tr.cost for tr in turn_results)
        success = self.is_successful(turn_results)
        
        # Calculate score based on success and efficiency
        if success:
            # Base score for success, with efficiency bonus
            max_turns = self.config.get("max_turns", 10)
            efficiency_bonus = max(0, (max_turns - len(turn_results)) / max_turns * 0.2)
            score = min(1.0, 0.8 + efficiency_bonus)
        else:
            # Partial credit based on progress
            score = min(0.5, len(turn_results) / self.config.get("max_turns", 10) * 0.5)
        
        return TaskResult(
            task_id=self.task_id,
            success=success,
            score=score,
            execution_time=total_time,
            metadata={
                "turns": len(turn_results),
                "total_tokens": total_tokens,
                "total_cost": total_cost,
                "turn_results": [
                    {
                        "turn": tr.turn,
                        "reward": tr.reward,
                        "done": tr.done,
                        "execution_time": tr.execution_time
                    }
                    for tr in turn_results
                ]
            }
        )