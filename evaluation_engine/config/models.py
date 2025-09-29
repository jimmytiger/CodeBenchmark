"""
Data models and type definitions for configuration-driven evaluation.

This module defines the core data structures used throughout the
configuration system, including configuration schemas and validation results.
"""

from dataclasses import dataclass, field
from typing import Dict, List, Optional, Any, Union
from enum import Enum


class ConfigFormat(Enum):
    """Supported configuration file formats."""
    YAML = "yaml"
    JSON = "json"
    UNKNOWN = "unknown"


class ValidationSeverity(Enum):
    """Validation error severity levels."""
    ERROR = "error"
    WARNING = "warning"
    INFO = "info"


@dataclass
class ConfigMetadata:
    """Metadata information for configuration files."""
    name: str
    version: str = "1.0"
    author: Optional[str] = None
    description: Optional[str] = None
    created_at: Optional[str] = None
    updated_at: Optional[str] = None


@dataclass
class ModelConfig:
    """Configuration for a specific model."""
    name: str
    type: str  # "openai", "huggingface", "anthropic", "custom"
    model_name: str  # Actual model name/identifier
    parameters: Dict[str, Any] = field(default_factory=dict)
    prompt_template: Optional[str] = None
    system_prompt: Optional[str] = None
    
    def __post_init__(self):
        """Validate model configuration after initialization."""
        if not self.name:
            raise ValueError("Model name cannot be empty")
        if not self.type:
            raise ValueError("Model type cannot be empty")
        if not self.model_name:
            raise ValueError("Model name cannot be empty")


@dataclass
class TaskConfig:
    """Configuration for an evaluation task."""
    name: str
    model_ref: str  # Reference to a model defined in models section
    task_name: str  # lm-eval task name (e.g., "hellaswag", "arc_easy")
    description: Optional[str] = None
    task_config: Optional[Dict[str, Any]] = None
    num_fewshot: Optional[int] = None
    batch_size: Optional[int] = None
    depends_on: List[str] = field(default_factory=list)
    
    def __post_init__(self):
        """Validate task configuration after initialization."""
        if not self.name:
            raise ValueError("Task name cannot be empty")
        if not self.model_ref:
            raise ValueError("Model reference cannot be empty")
        if not self.task_name:
            raise ValueError("Task name cannot be empty")


@dataclass
class DefaultConfig:
    """Default configuration values."""
    num_fewshot: int = 5
    batch_size: int = 32
    output: Optional[Dict[str, Any]] = None
    
    def __post_init__(self):
        """Set default output configuration if not provided."""
        if self.output is None:
            self.output = {
                "format": ["json"],
                "save_predictions": True
            }


@dataclass
class OutputConfig:
    """Configuration for evaluation output."""
    directory: str = "./results"
    formats: List[str] = field(default_factory=lambda: ["json"])
    include_raw_responses: bool = False
    generate_report: bool = True
    compare_models: bool = False
    
    def __post_init__(self):
        """Validate output configuration."""
        supported_formats = {"json", "csv", "html", "yaml"}
        for fmt in self.formats:
            if fmt not in supported_formats:
                raise ValueError(f"Unsupported output format: {fmt}")


@dataclass
class EvaluationConfig:
    """Complete evaluation configuration."""
    metadata: ConfigMetadata
    tasks: List[TaskConfig]
    models: Dict[str, ModelConfig] = field(default_factory=dict)
    variables: Dict[str, Any] = field(default_factory=dict)
    defaults: Optional[DefaultConfig] = None
    output: Optional[OutputConfig] = None
    
    def __post_init__(self):
        """Initialize default configurations if not provided."""
        if self.defaults is None:
            self.defaults = DefaultConfig()
        if self.output is None:
            self.output = OutputConfig()


@dataclass
class ValidationError:
    """Represents a validation error or warning."""
    type: str  # "syntax", "semantic", "runtime"
    message: str
    severity: ValidationSeverity
    location: Optional[str] = None  # File location or path
    suggestion: Optional[str] = None  # Suggested fix
    
    def __str__(self) -> str:
        """String representation of validation error."""
        parts = [f"{self.severity.value.upper()}: {self.message}"]
        if self.location:
            parts.append(f"Location: {self.location}")
        if self.suggestion:
            parts.append(f"Suggestion: {self.suggestion}")
        return " | ".join(parts)


@dataclass
class ValidationResult:
    """Result of configuration validation."""
    is_valid: bool
    errors: List[ValidationError] = field(default_factory=list)
    warnings: List[ValidationError] = field(default_factory=list)
    
    def add_error(self, error: ValidationError):
        """Add a validation error."""
        if error.severity == ValidationSeverity.ERROR:
            self.errors.append(error)
            self.is_valid = False
        elif error.severity == ValidationSeverity.WARNING:
            self.warnings.append(error)
    
    def has_errors(self) -> bool:
        """Check if there are any errors."""
        return len(self.errors) > 0
    
    def has_warnings(self) -> bool:
        """Check if there are any warnings."""
        return len(self.warnings) > 0
    
    def get_all_issues(self) -> List[ValidationError]:
        """Get all errors and warnings combined."""
        return self.errors + self.warnings


# Type aliases for better readability
ConfigDict = Dict[str, Any]
VariableDict = Dict[str, Any]
ModelDict = Dict[str, ModelConfig]