"""
Pydantic models for configuration-driven evaluation API endpoints.

Defines data structures for configuration API requests and responses.
"""

from pydantic import BaseModel, Field, field_validator
from typing import List, Dict, Any, Optional, Union
from datetime import datetime
from enum import Enum
import json


class ConfigFormat(str, Enum):
    """Configuration file format enumeration."""
    YAML = "yaml"
    JSON = "json"


class ConfigValidationStatus(str, Enum):
    """Configuration validation status enumeration."""
    VALID = "valid"
    INVALID = "invalid"
    WARNING = "warning"


class TaskExecutionStatus(str, Enum):
    """Task execution status enumeration."""
    PENDING = "pending"
    RUNNING = "running"
    COMPLETED = "completed"
    FAILED = "failed"
    SKIPPED = "skipped"


class ConfigEvaluationStatus(str, Enum):
    """Configuration evaluation status enumeration."""
    CREATED = "created"
    VALIDATING = "validating"
    BUILDING = "building"
    RUNNING = "running"
    COMPLETED = "completed"
    FAILED = "failed"
    CANCELLED = "cancelled"


# Request Models
class ConfigUploadRequest(BaseModel):
    """Request model for configuration file upload."""
    
    config_content: str = Field(..., description="Configuration file content")
    format: ConfigFormat = Field(..., description="Configuration format (yaml/json)")
    name: Optional[str] = Field(None, description="Configuration name")
    description: Optional[str] = Field(None, description="Configuration description")
    
    @field_validator('config_content')
    @classmethod
    def validate_config_content(cls, v):
        if not v or not v.strip():
            raise ValueError('Configuration content cannot be empty')
        return v


class ConfigValidationRequest(BaseModel):
    """Request model for configuration validation."""
    
    config_content: str = Field(..., description="Configuration content to validate")
    format: ConfigFormat = Field(..., description="Configuration format")
    
    @field_validator('config_content')
    @classmethod
    def validate_config_content(cls, v):
        if not v or not v.strip():
            raise ValueError('Configuration content cannot be empty')
        return v


class ConfigExecutionRequest(BaseModel):
    """Request model for configuration execution."""
    
    config_id: Optional[str] = Field(None, description="ID of uploaded configuration")
    config_content: Optional[str] = Field(None, description="Inline configuration content")
    format: Optional[ConfigFormat] = Field(None, description="Configuration format (required if using config_content)")
    task_filter: Optional[List[str]] = Field(None, description="Filter to specific task names")
    parameter_overrides: Optional[Dict[str, Any]] = Field(None, description="Parameter overrides")
    fail_fast: bool = Field(False, description="Stop execution on first task failure")
    dry_run: bool = Field(False, description="Validate and build tasks but don't execute")
    
    @field_validator('format')
    @classmethod
    def validate_format_required(cls, v, info):
        # Check if config_content is provided and format is required
        if hasattr(info, 'data') and info.data.get('config_content') and not v:
            raise ValueError('Format is required when using inline config_content')
        return v
    
    def __init__(self, **data):
        super().__init__(**data)
        # Ensure either config_id or config_content is provided
        if not self.config_id and not self.config_content:
            raise ValueError('Either config_id or config_content must be provided')
        if self.config_id and self.config_content:
            raise ValueError('Cannot specify both config_id and config_content')


class ConfigTaskStatusRequest(BaseModel):
    """Request model for task status updates."""
    
    evaluation_id: str = Field(..., description="Evaluation ID")
    task_name: str = Field(..., description="Task name")
    status: TaskExecutionStatus = Field(..., description="New task status")
    progress: Optional[float] = Field(None, ge=0.0, le=1.0, description="Task progress (0.0-1.0)")
    message: Optional[str] = Field(None, description="Status message")
    error: Optional[str] = Field(None, description="Error message if failed")


# Response Models
class ConfigValidationError(BaseModel):
    """Configuration validation error."""
    
    type: str = Field(..., description="Error type")
    message: str = Field(..., description="Error message")
    severity: str = Field(..., description="Error severity (error/warning/info)")
    location: Optional[str] = Field(None, description="Error location in config")
    suggestion: Optional[str] = Field(None, description="Suggested fix")


class ConfigValidationResponse(BaseModel):
    """Response model for configuration validation."""
    
    is_valid: bool = Field(..., description="Whether configuration is valid")
    status: ConfigValidationStatus = Field(..., description="Validation status")
    errors: List[ConfigValidationError] = Field(default_factory=list, description="Validation errors")
    warnings: List[ConfigValidationError] = Field(default_factory=list, description="Validation warnings")
    task_count: Optional[int] = Field(None, description="Number of tasks in configuration")
    model_count: Optional[int] = Field(None, description="Number of models in configuration")
    estimated_duration: Optional[int] = Field(None, description="Estimated execution duration in seconds")


class ConfigUploadResponse(BaseModel):
    """Response model for configuration upload."""
    
    config_id: str = Field(..., description="Unique configuration identifier")
    name: str = Field(..., description="Configuration name")
    format: ConfigFormat = Field(..., description="Configuration format")
    validation: ConfigValidationResponse = Field(..., description="Validation results")
    uploaded_at: datetime = Field(..., description="Upload timestamp")
    size_bytes: int = Field(..., description="Configuration size in bytes")


class ConfigInfo(BaseModel):
    """Basic configuration information."""
    
    config_id: str = Field(..., description="Configuration identifier")
    name: str = Field(..., description="Configuration name")
    description: Optional[str] = Field(None, description="Configuration description")
    format: ConfigFormat = Field(..., description="Configuration format")
    uploaded_at: datetime = Field(..., description="Upload timestamp")
    size_bytes: int = Field(..., description="Configuration size in bytes")
    is_valid: bool = Field(..., description="Whether configuration is valid")
    task_count: int = Field(..., description="Number of tasks")
    model_count: int = Field(..., description="Number of models")


class ConfigDetail(ConfigInfo):
    """Detailed configuration information."""
    
    content: str = Field(..., description="Configuration content")
    validation: ConfigValidationResponse = Field(..., description="Validation results")
    metadata: Dict[str, Any] = Field(..., description="Configuration metadata")
    tasks: List[Dict[str, Any]] = Field(..., description="Task definitions")
    models: Dict[str, Dict[str, Any]] = Field(..., description="Model definitions")


class TaskExecutionInfo(BaseModel):
    """Task execution information."""
    
    task_name: str = Field(..., description="Task name")
    status: TaskExecutionStatus = Field(..., description="Current status")
    progress: float = Field(0.0, ge=0.0, le=1.0, description="Progress percentage (0.0-1.0)")
    start_time: Optional[datetime] = Field(None, description="Task start time")
    end_time: Optional[datetime] = Field(None, description="Task end time")
    execution_time: Optional[float] = Field(None, description="Execution time in seconds")
    error_message: Optional[str] = Field(None, description="Error message if failed")
    metrics_summary: Optional[Dict[str, float]] = Field(None, description="Task metrics summary")


class ConfigExecutionResponse(BaseModel):
    """Response model for configuration execution."""
    
    evaluation_id: str = Field(..., description="Unique evaluation identifier")
    config_id: Optional[str] = Field(None, description="Configuration ID (if using uploaded config)")
    status: ConfigEvaluationStatus = Field(..., description="Current evaluation status")
    message: str = Field(..., description="Response message")
    created_at: datetime = Field(..., description="Creation timestamp")
    estimated_completion: Optional[datetime] = Field(None, description="Estimated completion time")
    task_count: int = Field(..., description="Total number of tasks")
    dry_run: bool = Field(..., description="Whether this is a dry run")


class ConfigExecutionStatus(BaseModel):
    """Response model for configuration execution status."""
    
    evaluation_id: str = Field(..., description="Evaluation identifier")
    config_id: Optional[str] = Field(None, description="Configuration ID")
    status: ConfigEvaluationStatus = Field(..., description="Current status")
    progress: float = Field(..., ge=0.0, le=1.0, description="Overall progress (0.0-1.0)")
    start_time: Optional[datetime] = Field(None, description="Evaluation start time")
    end_time: Optional[datetime] = Field(None, description="Evaluation end time")
    execution_time: Optional[float] = Field(None, description="Total execution time in seconds")
    
    # Task information
    total_tasks: int = Field(..., description="Total number of tasks")
    completed_tasks: int = Field(0, description="Number of completed tasks")
    failed_tasks: int = Field(0, description="Number of failed tasks")
    running_tasks: int = Field(0, description="Number of currently running tasks")
    pending_tasks: int = Field(0, description="Number of pending tasks")
    
    # Current execution info
    current_task: Optional[str] = Field(None, description="Currently executing task")
    task_details: List[TaskExecutionInfo] = Field(default_factory=list, description="Detailed task information")
    
    # Error information
    error_message: Optional[str] = Field(None, description="Error message if failed")
    
    # Execution metadata
    dry_run: bool = Field(False, description="Whether this was a dry run")
    fail_fast: bool = Field(False, description="Whether fail-fast mode was enabled")


class ConfigExecutionResults(BaseModel):
    """Complete configuration execution results."""
    
    evaluation_id: str = Field(..., description="Evaluation identifier")
    config_id: Optional[str] = Field(None, description="Configuration ID")
    config_metadata: Dict[str, Any] = Field(..., description="Configuration metadata")
    
    # Execution summary
    status: ConfigEvaluationStatus = Field(..., description="Final status")
    start_time: datetime = Field(..., description="Execution start time")
    end_time: datetime = Field(..., description="Execution end time")
    total_execution_time: float = Field(..., description="Total execution time in seconds")
    
    # Task results
    total_tasks: int = Field(..., description="Total number of tasks")
    completed_tasks: int = Field(..., description="Number of completed tasks")
    failed_tasks: int = Field(..., description="Number of failed tasks")
    skipped_tasks: int = Field(..., description="Number of skipped tasks")
    success_rate: float = Field(..., description="Success rate percentage")
    
    # Detailed results
    task_results: Dict[str, Dict[str, Any]] = Field(..., description="Individual task results")
    task_summaries: Dict[str, Dict[str, Any]] = Field(..., description="Task summaries")
    execution_order: List[str] = Field(..., description="Task execution order")
    
    # Validation info
    validation_errors: List[ConfigValidationError] = Field(default_factory=list, description="Validation errors")
    validation_warnings: List[ConfigValidationError] = Field(default_factory=list, description="Validation warnings")
    
    # Export info
    export_formats: List[str] = Field(default_factory=list, description="Available export formats")
    download_urls: Dict[str, str] = Field(default_factory=dict, description="Download URLs by format")


class ConfigListResponse(BaseModel):
    """Response model for configuration list."""
    
    configurations: List[ConfigInfo] = Field(..., description="List of configurations")
    total: int = Field(..., description="Total number of configurations")
    page: int = Field(..., description="Current page number")
    page_size: int = Field(..., description="Items per page")
    has_next: bool = Field(..., description="Whether there are more pages")
    has_previous: bool = Field(..., description="Whether there are previous pages")


class ConfigExecutionListResponse(BaseModel):
    """Response model for execution list."""
    
    executions: List[ConfigExecutionStatus] = Field(..., description="List of executions")
    total: int = Field(..., description="Total number of executions")
    page: int = Field(..., description="Current page number")
    page_size: int = Field(..., description="Items per page")
    has_next: bool = Field(..., description="Whether there are more pages")
    has_previous: bool = Field(..., description="Whether there are previous pages")


class ConfigExportRequest(BaseModel):
    """Request model for configuration results export."""
    
    evaluation_id: str = Field(..., description="Evaluation ID to export")
    format: str = Field(..., description="Export format (json, csv, xlsx, pdf)")
    include_raw_results: bool = Field(False, description="Include raw evaluation results")
    include_config: bool = Field(True, description="Include configuration in export")
    
    @field_validator('format')
    @classmethod
    def validate_format(cls, v):
        supported_formats = ["json", "csv", "xlsx", "pdf"]
        if v.lower() not in supported_formats:
            raise ValueError(f"Unsupported format. Supported formats: {supported_formats}")
        return v.lower()


class ConfigExportResponse(BaseModel):
    """Response model for configuration export."""
    
    export_id: str = Field(..., description="Export identifier")
    evaluation_id: str = Field(..., description="Source evaluation ID")
    format: str = Field(..., description="Export format")
    status: str = Field(..., description="Export status")
    created_at: datetime = Field(..., description="Export creation time")
    estimated_completion: Optional[datetime] = Field(None, description="Estimated completion time")
    download_url: Optional[str] = Field(None, description="Download URL when ready")
    file_size: Optional[int] = Field(None, description="File size in bytes when ready")
    expires_at: Optional[datetime] = Field(None, description="Download expiration time")


class ConfigTemplateInfo(BaseModel):
    """Configuration template information."""
    
    template_id: str = Field(..., description="Template identifier")
    name: str = Field(..., description="Template name")
    description: str = Field(..., description="Template description")
    category: str = Field(..., description="Template category")
    tags: List[str] = Field(default_factory=list, description="Template tags")
    created_at: datetime = Field(..., description="Template creation time")
    updated_at: datetime = Field(..., description="Template last update time")


class ConfigTemplateDetail(ConfigTemplateInfo):
    """Detailed configuration template."""
    
    content: str = Field(..., description="Template content")
    variables: Dict[str, Any] = Field(default_factory=dict, description="Template variables")
    example_values: Dict[str, Any] = Field(default_factory=dict, description="Example variable values")
    usage_instructions: str = Field(..., description="Usage instructions")


class ConfigWebSocketMessage(BaseModel):
    """WebSocket message for configuration execution updates."""
    
    type: str = Field(..., description="Message type")
    evaluation_id: str = Field(..., description="Related evaluation ID")
    timestamp: datetime = Field(default_factory=datetime.utcnow, description="Message timestamp")
    data: Dict[str, Any] = Field(..., description="Message data")
    
    class Config:
        json_encoders = {
            datetime: lambda v: v.isoformat()
        }


# Utility Models
class ConfigMetrics(BaseModel):
    """Configuration system metrics."""
    
    total_configurations: int = Field(..., description="Total number of configurations")
    active_executions: int = Field(..., description="Number of active executions")
    completed_executions: int = Field(..., description="Number of completed executions")
    failed_executions: int = Field(..., description="Number of failed executions")
    average_execution_time: float = Field(..., description="Average execution time in seconds")
    success_rate: float = Field(..., description="Overall success rate percentage")
    most_used_tasks: List[Dict[str, Any]] = Field(..., description="Most frequently used tasks")
    most_used_models: List[Dict[str, Any]] = Field(..., description="Most frequently used models")