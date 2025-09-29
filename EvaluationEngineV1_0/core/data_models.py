"""
Core data models for multi-turn evaluation.

This module defines the comprehensive data models required for multi-turn
evaluation including results, metrics, and configuration structures.
"""

from abc import ABC, abstractmethod
from dataclasses import dataclass, field
from datetime import datetime
from enum import Enum
from typing import Any, Dict, List, Optional, Union
import json


class TerminationReason(Enum):
    """Reasons for evaluation termination."""
    SUCCESS = "success"
    MAX_TURNS = "max_turns"
    TIMEOUT = "timeout"
    SAFETY_VIOLATION = "safety_violation"
    ERROR = "error"
    USER_REQUESTED = "user_requested"
    RESOURCE_EXHAUSTION = "resource_exhaustion"


class ContextStrategy(Enum):
    """Strategies for context management."""
    FULL = "full"
    ADAPTIVE = "adaptive"
    MINIMAL = "minimal"
    SLIDING_WINDOW = "sliding_window"


@dataclass
class ProcessedFeedback:
    """Processed feedback from environment execution.
    
    Attributes:
        original: Original raw feedback data
        filtered: Feedback after safety filtering
        contextualized: Feedback with added context
        final: Final processed feedback ready for model consumption
        processing_time: Time spent processing feedback
        truncated: Whether feedback was truncated due to length limits
    """
    original: Dict[str, Any]
    filtered: Dict[str, Any]
    contextualized: Dict[str, Any]
    final: Dict[str, Any]
    processing_time: float = 0.0
    truncated: bool = False
    timestamp: datetime = field(default_factory=datetime.now)


@dataclass
class EvaluationResult:
    """Complete evaluation result for a task.
    
    Attributes:
        evaluation_id: Unique identifier for this evaluation run
        task_id: Identifier of the evaluated task
        model_id: Identifier of the model used
        start_time: When evaluation started
        end_time: When evaluation completed
        success: Whether the task was completed successfully
        total_turns: Total number of turns executed
        turn_results: Results from each individual turn
        final_metrics: Final calculated metrics
        aggregated_metrics: Aggregated metrics across dimensions
        termination_reason: Why the evaluation terminated
        metadata: Additional evaluation-specific information
    """
    evaluation_id: str
    task_id: str
    model_id: str
    start_time: datetime
    end_time: datetime
    success: bool
    total_turns: int
    turn_results: List['TurnResult']
    final_metrics: Dict[str, float]
    aggregated_metrics: 'AggregatedMetrics'
    termination_reason: TerminationReason
    metadata: Dict[str, Any] = field(default_factory=dict)
    
    @property
    def duration(self) -> float:
        """Get evaluation duration in seconds."""
        return (self.end_time - self.start_time).total_seconds()
    
    def to_dict(self) -> Dict[str, Any]:
        """Convert to dictionary for serialization."""
        return {
            'evaluation_id': self.evaluation_id,
            'task_id': self.task_id,
            'model_id': self.model_id,
            'start_time': self.start_time.isoformat(),
            'end_time': self.end_time.isoformat(),
            'duration': self.duration,
            'success': self.success,
            'total_turns': self.total_turns,
            'termination_reason': self.termination_reason.value,
            'final_metrics': self.final_metrics,
            'aggregated_metrics': self.aggregated_metrics.to_dict(),
            'metadata': self.metadata
        }
    
    def to_json(self) -> str:
        """Convert to JSON string."""
        return json.dumps(self.to_dict(), indent=2)


@dataclass
class AggregatedMetrics:
    """Aggregated metrics across all evaluation dimensions.
    
    This class contains comprehensive metrics covering task success,
    efficiency, repair quality, robustness, cost, and safety dimensions.
    """
    
    # Task Success Metrics (Requirements 4.1, 4.2)
    resolved_percentage: float = 0.0
    recall: float = 0.0
    mrr: float = 0.0  # Mean Reciprocal Rank
    
    # Efficiency Metrics (Requirements 4.2)
    avg_turns: float = 0.0
    avg_steps: float = 0.0
    redundancy_rate: float = 0.0
    
    # Repair Quality Metrics (Requirements 4.3)
    edit_churn: float = 0.0
    files_touched: int = 0
    
    # Robustness Metrics (Requirements 4.4)
    recovery_rate: float = 0.0
    stability_score: float = 0.0
    
    # Cost Metrics (Requirements 4.5)
    wall_time_per_solved: float = 0.0
    tokens_per_solved: int = 0
    cost_per_solved: float = 0.0
    
    # Safety Metrics (Requirements 4.6)
    safety_incidents: int = 0
    policy_violations: int = 0
    
    def to_dict(self) -> Dict[str, Union[float, int]]:
        """Convert to dictionary for serialization."""
        return {
            # Task Success
            'resolved_percentage': self.resolved_percentage,
            'recall': self.recall,
            'mrr': self.mrr,
            
            # Efficiency
            'avg_turns': self.avg_turns,
            'avg_steps': self.avg_steps,
            'redundancy_rate': self.redundancy_rate,
            
            # Repair Quality
            'edit_churn': self.edit_churn,
            'files_touched': self.files_touched,
            
            # Robustness
            'recovery_rate': self.recovery_rate,
            'stability_score': self.stability_score,
            
            # Cost
            'wall_time_per_solved': self.wall_time_per_solved,
            'tokens_per_solved': self.tokens_per_solved,
            'cost_per_solved': self.cost_per_solved,
            
            # Safety
            'safety_incidents': self.safety_incidents,
            'policy_violations': self.policy_violations
        }
    
    @classmethod
    def from_dict(cls, data: Dict[str, Union[float, int]]) -> 'AggregatedMetrics':
        """Create from dictionary."""
        return cls(**data)


@dataclass
class StandardizedOutput:
    """Standardized output schema for cross-benchmark comparison.
    
    This schema ensures consistent output format across different
    benchmark tools and evaluation scenarios (Requirements 6.1, 6.2, 6.3).
    """
    run_id: str
    task_id: str
    sample_id: str
    success: bool
    turns: int
    steps: int
    wall_time_s: float
    token_in: int
    token_out: int
    cost_usd: float
    files_touched: int
    edit_added: int
    edit_deleted: int
    redundancy_rate: float
    recovered: bool
    safety_incidents: int
    notes: str = ""
    timestamp: datetime = field(default_factory=datetime.now)
    
    def to_csv_row(self) -> List[str]:
        """Convert to CSV row format."""
        return [
            self.run_id,
            self.task_id,
            self.sample_id,
            str(self.success),
            str(self.turns),
            str(self.steps),
            str(self.wall_time_s),
            str(self.token_in),
            str(self.token_out),
            str(self.cost_usd),
            str(self.files_touched),
            str(self.edit_added),
            str(self.edit_deleted),
            str(self.redundancy_rate),
            str(self.recovered),
            str(self.safety_incidents),
            self.notes,
            self.timestamp.isoformat()
        ]
    
    @classmethod
    def csv_headers(cls) -> List[str]:
        """Get CSV headers."""
        return [
            'run_id', 'task_id', 'sample_id', 'success', 'turns', 'steps',
            'wall_time_s', 'token_in', 'token_out', 'cost_usd', 'files_touched',
            'edit_added', 'edit_deleted', 'redundancy_rate', 'recovered',
            'safety_incidents', 'notes', 'timestamp'
        ]
    
    def to_dict(self) -> Dict[str, Any]:
        """Convert to dictionary."""
        return {
            'run_id': self.run_id,
            'task_id': self.task_id,
            'sample_id': self.sample_id,
            'success': self.success,
            'turns': self.turns,
            'steps': self.steps,
            'wall_time_s': self.wall_time_s,
            'token_in': self.token_in,
            'token_out': self.token_out,
            'cost_usd': self.cost_usd,
            'files_touched': self.files_touched,
            'edit_added': self.edit_added,
            'edit_deleted': self.edit_deleted,
            'redundancy_rate': self.redundancy_rate,
            'recovered': self.recovered,
            'safety_incidents': self.safety_incidents,
            'notes': self.notes,
            'timestamp': self.timestamp.isoformat()
        }


# Configuration Models

@dataclass
class FeedbackConfig:
    """Configuration for feedback processing (Requirements 5.1, 5.2).
    
    Attributes:
        max_feedback_length: Maximum length of processed feedback
        context_strategy: Strategy for context management
        max_context_length: Maximum total context length
        enable_stack_summarization: Whether to summarize stack traces
        enable_file_context: Whether to include file context
        top_k_assertions: Number of top assertions to keep
        truncation_strategy: How to truncate when over limits
        preserve_error_info: Always preserve error information
    """
    max_feedback_length: int = 10000
    context_strategy: ContextStrategy = ContextStrategy.ADAPTIVE
    max_context_length: int = 50000
    enable_stack_summarization: bool = True
    enable_file_context: bool = True
    top_k_assertions: int = 5
    truncation_strategy: str = "intelligent"  # "intelligent", "tail", "head"
    preserve_error_info: bool = True
    
    def validate(self) -> bool:
        """Validate configuration values."""
        if self.max_feedback_length <= 0:
            raise ValueError("max_feedback_length must be positive")
        if self.max_context_length <= 0:
            raise ValueError("max_context_length must be positive")
        if self.top_k_assertions <= 0:
            raise ValueError("top_k_assertions must be positive")
        if self.truncation_strategy not in ["intelligent", "tail", "head"]:
            raise ValueError("Invalid truncation_strategy")
        return True


@dataclass
class SafetyConfig:
    """Configuration for safety controls (Requirements 5.3, 5.4, 5.5).
    
    Attributes:
        allowed_tools: List of allowed tools and commands
        resource_limits: Resource usage limits
        dangerous_patterns: Patterns to detect and block
        enable_sandboxing: Whether to enable execution sandboxing
        max_execution_time: Maximum time per action in seconds
        max_memory_mb: Maximum memory usage in MB
        max_disk_mb: Maximum disk usage in MB
        network_access: Whether network access is allowed
        file_system_access: File system access restrictions
    """
    allowed_tools: List[str] = field(default_factory=lambda: ["python", "bash", "git"])
    resource_limits: Dict[str, Any] = field(default_factory=dict)
    dangerous_patterns: List[str] = field(default_factory=list)
    enable_sandboxing: bool = True
    max_execution_time: int = 300  # seconds
    max_memory_mb: int = 1024
    max_disk_mb: int = 1024
    network_access: bool = False
    file_system_access: str = "restricted"  # "none", "restricted", "full"
    
    def __post_init__(self):
        """Initialize default resource limits and dangerous patterns."""
        if not self.resource_limits:
            self.resource_limits = {
                "max_processes": 10,
                "max_open_files": 100,
                "max_cpu_percent": 80.0
            }
        
        if not self.dangerous_patterns:
            self.dangerous_patterns = [
                r"rm\s+-rf\s+/",
                r"sudo\s+",
                r"chmod\s+777",
                r"eval\s*\(",
                r"exec\s*\(",
                r"__import__\s*\(",
                r"subprocess\.call",
                r"os\.system"
            ]
    
    def validate(self) -> bool:
        """Validate configuration values."""
        if self.max_execution_time <= 0:
            raise ValueError("max_execution_time must be positive")
        if self.max_memory_mb <= 0:
            raise ValueError("max_memory_mb must be positive")
        if self.max_disk_mb <= 0:
            raise ValueError("max_disk_mb must be positive")
        if self.file_system_access not in ["none", "restricted", "full"]:
            raise ValueError("Invalid file_system_access value")
        return True


@dataclass
class MultiTurnConfig:
    """Configuration for multi-turn evaluation (Requirements 7.1, 7.2, 7.3).
    
    Attributes:
        max_turns: Maximum number of turns allowed
        conversation_timeout: Total timeout for conversation in seconds
        enable_context_retention: Whether to retain context between turns
        termination_conditions: List of termination condition names
        feedback_config: Configuration for feedback processing
        safety_config: Configuration for safety controls
        enable_recovery: Whether to enable error recovery
        recovery_max_attempts: Maximum recovery attempts per error
    """
    max_turns: int = 10
    conversation_timeout: int = 3600  # seconds
    enable_context_retention: bool = True
    termination_conditions: List[str] = field(
        default_factory=lambda: ["success", "max_turns", "timeout"]
    )
    feedback_config: FeedbackConfig = field(default_factory=FeedbackConfig)
    safety_config: SafetyConfig = field(default_factory=SafetyConfig)
    enable_recovery: bool = True
    recovery_max_attempts: int = 3
    
    def validate(self) -> bool:
        """Validate configuration values."""
        if self.max_turns <= 0:
            raise ValueError("max_turns must be positive")
        if self.conversation_timeout <= 0:
            raise ValueError("conversation_timeout must be positive")
        if self.recovery_max_attempts < 0:
            raise ValueError("recovery_max_attempts must be non-negative")
        
        valid_conditions = {
            "success", "max_turns", "timeout", "safety_violation", "error"
        }
        for condition in self.termination_conditions:
            if condition not in valid_conditions:
                raise ValueError(f"Invalid termination condition: {condition}")
        
        # Validate nested configurations
        self.feedback_config.validate()
        self.safety_config.validate()
        
        return True


# Enhanced TurnResult with ProcessedFeedback
@dataclass
class TurnResult:
    """Enhanced result of a single turn execution.
    
    This extends the basic TurnResult from task_types.py with additional
    fields for multi-turn evaluation support.
    """
    turn: int
    action: Any
    observation: Any
    reward: float
    done: bool
    info: Dict[str, Any]
    execution_time: float
    processed_feedback: Optional[ProcessedFeedback] = None
    tokens_used: int = 0
    cost: float = 0.0
    safety_violations: List[str] = field(default_factory=list)
    recovery_attempts: int = 0
    timestamp: datetime = field(default_factory=datetime.now)
    
    def to_dict(self) -> Dict[str, Any]:
        """Convert to dictionary for serialization."""
        return {
            'turn': self.turn,
            'action': str(self.action),
            'observation': str(self.observation),
            'reward': self.reward,
            'done': self.done,
            'info': self.info,
            'execution_time': self.execution_time,
            'tokens_used': self.tokens_used,
            'cost': self.cost,
            'safety_violations': self.safety_violations,
            'recovery_attempts': self.recovery_attempts,
            'timestamp': self.timestamp.isoformat(),
            'processed_feedback': (
                self.processed_feedback.final if self.processed_feedback else None
            )
        }


# Data validation utilities
class DataValidator:
    """Utility class for validating data models."""
    
    @staticmethod
    def validate_evaluation_result(result: EvaluationResult) -> bool:
        """Validate an EvaluationResult instance."""
        if not result.evaluation_id:
            raise ValueError("evaluation_id cannot be empty")
        if not result.task_id:
            raise ValueError("task_id cannot be empty")
        if not result.model_id:
            raise ValueError("model_id cannot be empty")
        if result.start_time > result.end_time:
            raise ValueError("start_time cannot be after end_time")
        if result.total_turns < 0:
            raise ValueError("total_turns cannot be negative")
        if len(result.turn_results) != result.total_turns:
            raise ValueError("turn_results length must match total_turns")
        return True
    
    @staticmethod
    def validate_standardized_output(output: StandardizedOutput) -> bool:
        """Validate a StandardizedOutput instance."""
        if not output.run_id:
            raise ValueError("run_id cannot be empty")
        if not output.task_id:
            raise ValueError("task_id cannot be empty")
        if not output.sample_id:
            raise ValueError("sample_id cannot be empty")
        if output.turns < 0:
            raise ValueError("turns cannot be negative")
        if output.steps < 0:
            raise ValueError("steps cannot be negative")
        if output.wall_time_s < 0:
            raise ValueError("wall_time_s cannot be negative")
        if output.cost_usd < 0:
            raise ValueError("cost_usd cannot be negative")
        return True


@dataclass
class ModelConfig:
    """Configuration for a model used in evaluation.
    
    Attributes:
        model_id: Unique identifier for the model
        model_type: Type of model (e.g., 'openai', 'huggingface', 'anthropic')
        parameters: Model-specific parameters
        device: Device to run the model on
        api_key: API key for external models (optional)
        base_url: Base URL for API models (optional)
    """
    model_id: str
    model_type: str
    parameters: Dict[str, Any] = field(default_factory=dict)
    device: str = "auto"
    api_key: Optional[str] = None
    base_url: Optional[str] = None
    
    def validate(self) -> bool:
        """Validate model configuration."""
        if not self.model_id:
            raise ValueError("model_id cannot be empty")
        if not self.model_type:
            raise ValueError("model_type cannot be empty")
        return True


@dataclass
class TaskConfig:
    """Configuration for an evaluation task.
    
    Attributes:
        task_id: Unique identifier for the task
        task_type: Type of task ('single_turn' or 'multi_turn')
        model_ref: Reference to the model to use
        parameters: Task-specific parameters
        adapter: Adapter to use for the task (optional)
        timeout: Task timeout in seconds
        max_retries: Maximum number of retries on failure
    """
    task_id: str
    task_type: str
    model_ref: str
    parameters: Dict[str, Any] = field(default_factory=dict)
    adapter: Optional[str] = None
    timeout: int = 3600
    max_retries: int = 3
    
    def validate(self) -> bool:
        """Validate task configuration."""
        if not self.task_id:
            raise ValueError("task_id cannot be empty")
        if not self.task_type:
            raise ValueError("task_type cannot be empty")
        if self.task_type not in ["single_turn", "multi_turn"]:
            raise ValueError("task_type must be 'single_turn' or 'multi_turn'")
        if not self.model_ref:
            raise ValueError("model_ref cannot be empty")
        if self.timeout <= 0:
            raise ValueError("timeout must be positive")
        if self.max_retries < 0:
            raise ValueError("max_retries must be non-negative")
        return True


@dataclass
class EvaluationConfig:
    """Complete configuration for an evaluation run.
    
    Attributes:
        models: Dictionary of model configurations
        tasks: List of task configurations
        evaluation_settings: General evaluation settings
        multi_turn_config: Multi-turn specific configuration
        output_settings: Output and export settings
        metadata: Additional metadata
    """
    models: Dict[str, ModelConfig] = field(default_factory=dict)
    tasks: List[TaskConfig] = field(default_factory=list)
    evaluation_settings: Dict[str, Any] = field(default_factory=dict)
    multi_turn_config: Optional[MultiTurnConfig] = None
    output_settings: Dict[str, Any] = field(default_factory=dict)
    metadata: Dict[str, Any] = field(default_factory=dict)
    
    def validate(self) -> bool:
        """Validate evaluation configuration."""
        if not self.models:
            raise ValueError("At least one model must be configured")
        if not self.tasks:
            raise ValueError("At least one task must be configured")
        
        # Validate all models
        for model_id, model_config in self.models.items():
            model_config.validate()
        
        # Validate all tasks
        for task_config in self.tasks:
            task_config.validate()
            # Check that model_ref exists
            if task_config.model_ref not in self.models:
                raise ValueError(f"Task {task_config.task_id} references unknown model {task_config.model_ref}")
        
        # Validate multi-turn config if present
        if self.multi_turn_config:
            self.multi_turn_config.validate()
        
        return True
    
    def get_multi_turn_tasks(self) -> List[TaskConfig]:
        """Get all multi-turn tasks."""
        return [task for task in self.tasks if task.task_type == "multi_turn"]
    
    def get_single_turn_tasks(self) -> List[TaskConfig]:
        """Get all single-turn tasks."""
        return [task for task in self.tasks if task.task_type == "single_turn"]