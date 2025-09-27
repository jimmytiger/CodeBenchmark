"""
Pydantic models for API requests and responses.

Defines data structures for REST API endpoints with validation.
"""

from pydantic import BaseModel, Field, validator
from typing import List, Dict, Any, Optional, Union
from datetime import datetime
from enum import Enum


class EvaluationStatus(str, Enum):
    """Evaluation status enumeration."""
    CREATED = "created"
    RUNNING = "running"
    COMPLETED = "completed"
    FAILED = "failed"
    CANCELLED = "cancelled"


class TaskCategory(str, Enum):
    """Task category enumeration."""
    SINGLE_TURN = "single_turn"
    MULTI_TURN = "multi_turn"
    DOMAIN_SPECIFIC = "domain_specific"


class DifficultyLevel(str, Enum):
    """Difficulty level enumeration."""
    BEGINNER = "beginner"
    INTERMEDIATE = "intermediate"
    ADVANCED = "advanced"
    EXPERT = "expert"


class ContextMode(str, Enum):
    """Context mode enumeration."""
    NO_CONTEXT = "no_context"
    MINIMAL_CONTEXT = "minimal_context"
    FULL_CONTEXT = "full_context"
    DOMAIN_CONTEXT = "domain_context"


# Request Models
class EvaluationRequest(BaseModel):
    """Request model for creating evaluations."""
    
    model_id: str = Field(..., description="ID of the model to evaluate")
    task_ids: List[str] = Field(..., min_items=1, description="List of task IDs to execute")
    configuration: Optional[Dict[str, Any]] = Field(None, description="Evaluation configuration")
    context_mode: ContextMode = Field(ContextMode.FULL_CONTEXT, description="Context mode for evaluation")
    metadata: Optional[Dict[str, Any]] = Field(None, description="Additional metadata")
    
    @validator('task_ids')
    def validate_task_ids(cls, v):
        if not v:
            raise ValueError('At least one task ID is required')
        return v


class ModelConfigRequest(BaseModel):
    """Request model for model configuration."""
    
    parameters: Dict[str, Any] = Field(..., description="Model parameters")
    api_settings: Optional[Dict[str, Any]] = Field(None, description="API-specific settings")
    rate_limits: Optional[Dict[str, Union[int, float]]] = Field(None, description="Rate limiting configuration")


class TaskFilter(BaseModel):
    """Filter parameters for task queries."""
    
    category: Optional[TaskCategory] = Field(None, description="Filter by task category")
    difficulty: Optional[DifficultyLevel] = Field(None, description="Filter by difficulty level")
    language: Optional[str] = Field(None, description="Filter by programming language")
    tags: Optional[List[str]] = Field(None, description="Filter by tags")


# Response Models
class EvaluationResponse(BaseModel):
    """Response model for evaluation creation."""
    
    evaluation_id: str = Field(..., description="Unique evaluation identifier")
    status: EvaluationStatus = Field(..., description="Current evaluation status")
    message: str = Field(..., description="Response message")
    created_at: datetime = Field(..., description="Creation timestamp")


class EvaluationStatus(BaseModel):
    """Response model for evaluation status."""
    
    evaluation_id: str = Field(..., description="Evaluation identifier")
    status: EvaluationStatus = Field(..., description="Current status")
    progress: float = Field(..., ge=0.0, le=1.0, description="Progress percentage (0.0-1.0)")
    current_task: Optional[str] = Field(None, description="Currently executing task")
    completed_tasks: int = Field(..., ge=0, description="Number of completed tasks")
    total_tasks: int = Field(..., ge=0, description="Total number of tasks")
    start_time: Optional[datetime] = Field(None, description="Evaluation start time")
    estimated_completion: Optional[datetime] = Field(None, description="Estimated completion time")
    error_message: Optional[str] = Field(None, description="Error message if failed")


class TaskInfo(BaseModel):
    """Basic task information."""
    
    task_id: str = Field(..., description="Task identifier")
    name: str = Field(..., description="Task name")
    category: TaskCategory = Field(..., description="Task category")
    difficulty: DifficultyLevel = Field(..., description="Difficulty level")
    description: str = Field(..., description="Task description")
    languages: List[str] = Field(..., description="Supported programming languages")
    tags: List[str] = Field(..., description="Task tags")
    estimated_duration: Optional[int] = Field(None, description="Estimated duration in seconds")


class TaskDetail(TaskInfo):
    """Detailed task information."""
    
    requirements: List[str] = Field(..., description="Task requirements")
    evaluation_criteria: List[str] = Field(..., description="Evaluation criteria")
    sample_input: Optional[Dict[str, Any]] = Field(None, description="Sample input data")
    sample_output: Optional[Dict[str, Any]] = Field(None, description="Sample expected output")
    metrics: List[str] = Field(..., description="Available metrics")
    dependencies: List[str] = Field(..., description="Task dependencies")


class ModelInfo(BaseModel):
    """Model information."""
    
    model_id: str = Field(..., description="Model identifier")
    name: str = Field(..., description="Model name")
    provider: str = Field(..., description="Model provider")
    version: str = Field(..., description="Model version")
    capabilities: List[str] = Field(..., description="Model capabilities")
    supported_tasks: List[str] = Field(..., description="Supported task types")
    rate_limits: Dict[str, Union[int, float]] = Field(..., description="Rate limits")
    cost_per_token: Optional[float] = Field(None, description="Cost per token")


class TaskResult(BaseModel):
    """Individual task result."""
    
    task_id: str = Field(..., description="Task identifier")
    status: str = Field(..., description="Task execution status")
    score: float = Field(..., description="Overall task score")
    metrics: Dict[str, float] = Field(..., description="Detailed metrics")
    execution_time: float = Field(..., description="Execution time in seconds")
    output: Optional[str] = Field(None, description="Model output")
    error_message: Optional[str] = Field(None, description="Error message if failed")


class EvaluationResults(BaseModel):
    """Complete evaluation results."""
    
    evaluation_id: str = Field(..., description="Evaluation identifier")
    model_id: str = Field(..., description="Model identifier")
    task_results: List[TaskResult] = Field(..., description="Individual task results")
    summary_metrics: Dict[str, float] = Field(..., description="Summary metrics")
    overall_score: float = Field(..., description="Overall evaluation score")
    completed_at: datetime = Field(..., description="Completion timestamp")
    execution_time: float = Field(..., description="Total execution time")


class AnalyticsSummary(BaseModel):
    """Analytics summary response."""
    
    total_evaluations: int = Field(..., description="Total number of evaluations")
    total_tasks_executed: int = Field(..., description="Total tasks executed")
    average_performance: float = Field(..., description="Average performance score")
    top_performing_models: List[Dict[str, Any]] = Field(..., description="Top performing models")
    performance_trends: Dict[str, List[float]] = Field(..., description="Performance trends over time")
    task_category_breakdown: Dict[str, int] = Field(..., description="Task category distribution")


class ComparisonReport(BaseModel):
    """Model comparison report."""
    
    model_ids: List[str] = Field(..., description="Compared model IDs")
    comparison_metrics: Dict[str, Dict[str, float]] = Field(..., description="Comparison metrics by model")
    statistical_significance: Dict[str, Dict[str, float]] = Field(..., description="Statistical significance tests")
    performance_rankings: Dict[str, int] = Field(..., description="Performance rankings by metric")
    recommendations: List[str] = Field(..., description="Recommendations based on comparison")
    generated_at: datetime = Field(default_factory=datetime.utcnow, description="Report generation time")


class WebSocketMessage(BaseModel):
    """WebSocket message structure."""
    
    type: str = Field(..., description="Message type")
    evaluation_id: Optional[str] = Field(None, description="Related evaluation ID")
    data: Dict[str, Any] = Field(..., description="Message data")
    timestamp: datetime = Field(default_factory=datetime.utcnow, description="Message timestamp")


class SystemHealth(BaseModel):
    """System health status."""
    
    status: str = Field(..., description="Overall system status")
    active_evaluations: int = Field(..., description="Number of active evaluations")
    system_load: float = Field(..., description="System load percentage")
    memory_usage: float = Field(..., description="Memory usage percentage")
    disk_usage: float = Field(..., description="Disk usage percentage")
    uptime: float = Field(..., description="System uptime in seconds")
    last_check: datetime = Field(default_factory=datetime.utcnow, description="Last health check time")


class UserInfo(BaseModel):
    """User information."""
    
    user_id: str = Field(..., description="User identifier")
    username: str = Field(..., description="Username")
    email: str = Field(..., description="User email")
    roles: List[str] = Field(..., description="User roles")
    permissions: List[str] = Field(..., description="User permissions")
    created_at: datetime = Field(..., description="Account creation time")
    last_login: Optional[datetime] = Field(None, description="Last login time")


class AuthToken(BaseModel):
    """Authentication token response."""
    
    access_token: str = Field(..., description="JWT access token")
    token_type: str = Field("bearer", description="Token type")
    expires_in: int = Field(..., description="Token expiration time in seconds")
    refresh_token: Optional[str] = Field(None, description="Refresh token")
    user_info: UserInfo = Field(..., description="User information")


class ErrorResponse(BaseModel):
    """Error response model."""
    
    error: str = Field(..., description="Error type")
    message: str = Field(..., description="Error message")
    details: Optional[Dict[str, Any]] = Field(None, description="Additional error details")
    timestamp: datetime = Field(default_factory=datetime.utcnow, description="Error timestamp")
    request_id: Optional[str] = Field(None, description="Request identifier for tracking")


class PaginatedResponse(BaseModel):
    """Paginated response wrapper."""
    
    items: List[Any] = Field(..., description="Response items")
    total: int = Field(..., description="Total number of items")
    page: int = Field(..., description="Current page number")
    page_size: int = Field(..., description="Items per page")
    has_next: bool = Field(..., description="Whether there are more pages")
    has_previous: bool = Field(..., description="Whether there are previous pages")


class ExportRequest(BaseModel):
    """Export request model."""
    
    evaluation_ids: List[str] = Field(..., description="Evaluation IDs to export")
    format: str = Field(..., description="Export format (json, csv, pdf)")
    include_details: bool = Field(False, description="Include detailed results")
    filters: Optional[Dict[str, Any]] = Field(None, description="Additional filters")


class NotificationSettings(BaseModel):
    """Notification settings."""
    
    email_notifications: bool = Field(True, description="Enable email notifications")
    webhook_url: Optional[str] = Field(None, description="Webhook URL for notifications")
    notification_types: List[str] = Field(..., description="Types of notifications to receive")
    quiet_hours: Optional[Dict[str, str]] = Field(None, description="Quiet hours configuration")


class LoginRequest(BaseModel):
    """Login request model."""
    
    username: str = Field(..., description="Username")
    password: str = Field(..., description="Password")


class RefreshTokenRequest(BaseModel):
    """Refresh token request model."""
    
    refresh_token: str = Field(..., description="Refresh token")


class LogoutRequest(BaseModel):
    """Logout request model."""
    
    refresh_token: str = Field(..., description="Refresh token to invalidate")