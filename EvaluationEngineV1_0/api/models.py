"""
Pydantic models for multi-turn evaluation API requests and responses.

Defines data structures for REST API endpoints with validation.
"""

from pydantic import BaseModel, Field, field_validator
from typing import List, Dict, Any, Optional, Union
from datetime import datetime
from enum import Enum


class MultiTurnEvaluationStatus(str, Enum):
    """Multi-turn evaluation status enumeration."""
    CREATED = "created"
    INITIALIZING = "initializing"
    RUNNING = "running"
    PAUSED = "paused"
    COMPLETED = "completed"
    FAILED = "failed"
    CANCELLED = "cancelled"
    TERMINATED = "terminated"


class TerminationReason(str, Enum):
    """Termination reason enumeration."""
    SUCCESS = "success"
    MAX_TURNS = "max_turns"
    TIMEOUT = "timeout"
    SAFETY_VIOLATION = "safety_violation"
    ERROR = "error"
    USER_CANCELLED = "user_cancelled"


class FeedbackStrategy(str, Enum):
    """Feedback processing strategy enumeration."""
    FULL = "full"
    ADAPTIVE = "adaptive"
    MINIMAL = "minimal"
    TOP_K = "top_k"


class SafetyLevel(str, Enum):
    """Safety level enumeration."""
    STRICT = "strict"
    MODERATE = "moderate"
    PERMISSIVE = "permissive"


# Request Models
class MultiTurnEvaluationRequest(BaseModel):
    """Request model for creating multi-turn evaluations."""
    
    model_id: str = Field(..., description="ID of the model to evaluate")
    task_ids: List[str] = Field(..., min_length=1, description="List of multi-turn task IDs")
    max_turns: int = Field(10, ge=1, le=100, description="Maximum number of turns per task")
    timeout_seconds: int = Field(3600, ge=60, le=86400, description="Evaluation timeout in seconds")
    feedback_strategy: FeedbackStrategy = Field(FeedbackStrategy.ADAPTIVE, description="Feedback processing strategy")
    safety_level: SafetyLevel = Field(SafetyLevel.MODERATE, description="Safety enforcement level")
    enable_context_retention: bool = Field(True, description="Enable context retention between turns")
    configuration: Optional[Dict[str, Any]] = Field(None, description="Additional configuration")
    metadata: Optional[Dict[str, Any]] = Field(None, description="Evaluation metadata")
    
    @field_validator('task_ids')
    @classmethod
    def validate_task_ids(cls, v):
        if not v:
            raise ValueError('At least one task ID is required')
        return v


class TurnExecutionRequest(BaseModel):
    """Request model for executing a single turn."""
    
    evaluation_id: str = Field(..., description="Evaluation ID")
    turn_number: int = Field(..., ge=1, description="Turn number")
    action: Dict[str, Any] = Field(..., description="Action to execute")
    override_safety: bool = Field(False, description="Override safety checks (admin only)")


class EvaluationControlRequest(BaseModel):
    """Request model for evaluation control operations."""
    
    evaluation_id: str = Field(..., description="Evaluation ID")
    action: str = Field(..., description="Control action (pause, resume, cancel, terminate)")
    reason: Optional[str] = Field(None, description="Reason for the action")


class FeedbackConfigRequest(BaseModel):
    """Request model for feedback configuration."""
    
    max_feedback_length: int = Field(10000, ge=100, le=100000, description="Maximum feedback length")
    context_strategy: str = Field("adaptive", description="Context management strategy")
    max_context_length: int = Field(50000, ge=1000, le=200000, description="Maximum context length")
    enable_stack_summarization: bool = Field(True, description="Enable stack trace summarization")
    enable_file_context: bool = Field(True, description="Enable file context extraction")
    top_k_assertions: int = Field(5, ge=1, le=20, description="Number of top assertions to include")


class SafetyConfigRequest(BaseModel):
    """Request model for safety configuration."""
    
    allowed_tools: List[str] = Field(default_factory=lambda: ["python", "bash", "git"], description="Allowed tools")
    resource_limits: Dict[str, Any] = Field(default_factory=dict, description="Resource limits")
    dangerous_patterns: List[str] = Field(default_factory=list, description="Dangerous command patterns")
    enable_sandboxing: bool = Field(True, description="Enable execution sandboxing")
    max_execution_time: int = Field(300, ge=10, le=3600, description="Max execution time per action")


# Response Models
class MultiTurnEvaluationResponse(BaseModel):
    """Response model for multi-turn evaluation creation."""
    
    evaluation_id: str = Field(..., description="Unique evaluation identifier")
    status: MultiTurnEvaluationStatus = Field(..., description="Current evaluation status")
    message: str = Field(..., description="Response message")
    created_at: datetime = Field(..., description="Creation timestamp")
    estimated_duration: Optional[int] = Field(None, description="Estimated duration in seconds")
    websocket_url: str = Field(..., description="WebSocket URL for real-time updates")


class TurnResult(BaseModel):
    """Result of a single turn execution."""
    
    turn_number: int = Field(..., description="Turn number")
    action: Dict[str, Any] = Field(..., description="Executed action")
    observation: Dict[str, Any] = Field(..., description="Environment observation")
    reward: float = Field(..., description="Turn reward")
    done: bool = Field(..., description="Whether task is complete")
    info: Dict[str, Any] = Field(..., description="Additional information")
    processed_feedback: Dict[str, Any] = Field(..., description="Processed feedback")
    execution_time: float = Field(..., description="Turn execution time")
    tokens_used: int = Field(..., description="Tokens used in this turn")
    cost: float = Field(..., description="Cost for this turn")
    safety_violations: List[str] = Field(default_factory=list, description="Safety violations detected")


class MultiTurnTaskResult(BaseModel):
    """Result of a complete multi-turn task."""
    
    task_id: str = Field(..., description="Task identifier")
    status: str = Field(..., description="Task completion status")
    success: bool = Field(..., description="Whether task was completed successfully")
    total_turns: int = Field(..., description="Total number of turns executed")
    turn_results: List[TurnResult] = Field(..., description="Results for each turn")
    termination_reason: TerminationReason = Field(..., description="Reason for termination")
    final_metrics: Dict[str, float] = Field(..., description="Final task metrics")
    execution_time: float = Field(..., description="Total task execution time")
    total_tokens: int = Field(..., description="Total tokens used")
    total_cost: float = Field(..., description="Total cost")


class MultiTurnEvaluationStatusResponse(BaseModel):
    """Status response for multi-turn evaluation."""
    
    evaluation_id: str = Field(..., description="Evaluation identifier")
    status: MultiTurnEvaluationStatus = Field(..., description="Current status")
    progress: float = Field(..., ge=0.0, le=1.0, description="Progress percentage")
    current_task: Optional[str] = Field(None, description="Currently executing task")
    current_turn: Optional[int] = Field(None, description="Current turn number")
    completed_tasks: int = Field(..., description="Number of completed tasks")
    total_tasks: int = Field(..., description="Total number of tasks")
    start_time: Optional[datetime] = Field(None, description="Evaluation start time")
    estimated_completion: Optional[datetime] = Field(None, description="Estimated completion time")
    error_message: Optional[str] = Field(None, description="Error message if failed")
    safety_incidents: int = Field(0, description="Number of safety incidents")
    total_turns_executed: int = Field(0, description="Total turns executed across all tasks")


class MultiTurnEvaluationResults(BaseModel):
    """Complete multi-turn evaluation results."""
    
    evaluation_id: str = Field(..., description="Evaluation identifier")
    model_id: str = Field(..., description="Model identifier")
    task_results: List[MultiTurnTaskResult] = Field(..., description="Results for each task")
    aggregated_metrics: Dict[str, float] = Field(..., description="Aggregated metrics")
    overall_success_rate: float = Field(..., description="Overall success rate")
    average_turns_per_task: float = Field(..., description="Average turns per task")
    total_execution_time: float = Field(..., description="Total execution time")
    total_tokens: int = Field(..., description="Total tokens used")
    total_cost: float = Field(..., description="Total cost")
    safety_summary: Dict[str, int] = Field(..., description="Safety incidents summary")
    completed_at: datetime = Field(..., description="Completion timestamp")


class OrchestratorStatus(BaseModel):
    """Orchestrator status information."""
    
    active_evaluations: int = Field(..., description="Number of active evaluations")
    queued_evaluations: int = Field(..., description="Number of queued evaluations")
    total_evaluations_today: int = Field(..., description="Total evaluations started today")
    average_execution_time: float = Field(..., description="Average execution time")
    resource_usage: Dict[str, float] = Field(..., description="Current resource usage")
    safety_incidents_today: int = Field(..., description="Safety incidents today")


class WebSocketMessage(BaseModel):
    """WebSocket message structure for multi-turn evaluation."""
    
    type: str = Field(..., description="Message type")
    evaluation_id: str = Field(..., description="Related evaluation ID")
    data: Dict[str, Any] = Field(..., description="Message data")
    timestamp: datetime = Field(default_factory=datetime.utcnow, description="Message timestamp")


class SubscriptionRequest(BaseModel):
    """WebSocket subscription request."""
    
    type: str = Field(..., description="Subscription type")
    evaluation_id: Optional[str] = Field(None, description="Evaluation ID to subscribe to")
    filters: Optional[Dict[str, Any]] = Field(None, description="Subscription filters")


class MetricsSnapshot(BaseModel):
    """Metrics snapshot for monitoring."""
    
    timestamp: datetime = Field(default_factory=datetime.utcnow, description="Snapshot timestamp")
    task_success_metrics: Dict[str, float] = Field(..., description="Task success metrics")
    efficiency_metrics: Dict[str, float] = Field(..., description="Efficiency metrics")
    repair_quality_metrics: Dict[str, float] = Field(..., description="Repair quality metrics")
    robustness_metrics: Dict[str, float] = Field(..., description="Robustness metrics")
    cost_metrics: Dict[str, float] = Field(..., description="Cost metrics")
    safety_metrics: Dict[str, int] = Field(..., description="Safety metrics")


class ErrorResponse(BaseModel):
    """Error response model."""
    
    error: str = Field(..., description="Error type")
    message: str = Field(..., description="Error message")
    details: Optional[Dict[str, Any]] = Field(None, description="Additional error details")
    timestamp: datetime = Field(default_factory=datetime.utcnow, description="Error timestamp")
    evaluation_id: Optional[str] = Field(None, description="Related evaluation ID")
    turn_number: Optional[int] = Field(None, description="Related turn number")


class PaginatedResponse(BaseModel):
    """Paginated response wrapper."""
    
    items: List[Any] = Field(..., description="Response items")
    total: int = Field(..., description="Total number of items")
    page: int = Field(..., description="Current page number")
    page_size: int = Field(..., description="Items per page")
    has_next: bool = Field(..., description="Whether there are more pages")
    has_previous: bool = Field(..., description="Whether there are previous pages")