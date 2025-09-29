"""
Tests for configuration data models.
"""

import pytest
from evaluation_engine.config.models import (
    ConfigMetadata,
    ModelConfig,
    TaskConfig,
    DefaultConfig,
    OutputConfig,
    EvaluationConfig,
    ValidationError,
    ValidationResult,
    ValidationSeverity,
    ConfigFormat
)


class TestConfigMetadata:
    """Test ConfigMetadata data model."""
    
    def test_minimal_metadata(self):
        """Test creating metadata with minimal required fields."""
        metadata = ConfigMetadata(name="test-config")
        assert metadata.name == "test-config"
        assert metadata.version == "1.0"  # default value
        assert metadata.author is None
    
    def test_full_metadata(self):
        """Test creating metadata with all fields."""
        metadata = ConfigMetadata(
            name="test-config",
            version="2.0",
            author="Test Author",
            description="Test description"
        )
        assert metadata.name == "test-config"
        assert metadata.version == "2.0"
        assert metadata.author == "Test Author"
        assert metadata.description == "Test description"


class TestModelConfig:
    """Test ModelConfig data model."""
    
    def test_minimal_model_config(self):
        """Test creating model config with minimal required fields."""
        model = ModelConfig(
            name="test-model",
            type="openai",
            model_name="gpt-3.5-turbo"
        )
        assert model.name == "test-model"
        assert model.type == "openai"
        assert model.model_name == "gpt-3.5-turbo"
        assert model.parameters == {}
        assert model.prompt_template is None
        assert model.system_prompt is None
    
    def test_full_model_config(self):
        """Test creating model config with all fields."""
        model = ModelConfig(
            name="test-model",
            type="openai",
            model_name="gpt-3.5-turbo",
            parameters={"temperature": 0.7},
            prompt_template="Question: {question}",
            system_prompt="You are a helpful assistant"
        )
        assert model.parameters == {"temperature": 0.7}
        assert model.prompt_template == "Question: {question}"
        assert model.system_prompt == "You are a helpful assistant"
    
    def test_empty_name_validation(self):
        """Test that empty name raises ValueError."""
        with pytest.raises(ValueError, match="Model name cannot be empty"):
            ModelConfig(name="", type="openai", model_name="gpt-3.5-turbo")
    
    def test_empty_type_validation(self):
        """Test that empty type raises ValueError."""
        with pytest.raises(ValueError, match="Model type cannot be empty"):
            ModelConfig(name="test", type="", model_name="gpt-3.5-turbo")
    
    def test_empty_model_name_validation(self):
        """Test that empty model_name raises ValueError."""
        with pytest.raises(ValueError, match="Model name cannot be empty"):
            ModelConfig(name="test", type="openai", model_name="")


class TestTaskConfig:
    """Test TaskConfig data model."""
    
    def test_minimal_task_config(self):
        """Test creating task config with minimal required fields."""
        task = TaskConfig(
            name="test-task",
            model_ref="test-model",
            task_name="hellaswag"
        )
        assert task.name == "test-task"
        assert task.model_ref == "test-model"
        assert task.task_name == "hellaswag"
        assert task.description is None
        assert task.task_config is None
        assert task.num_fewshot is None
        assert task.batch_size is None
        assert task.depends_on == []
    
    def test_full_task_config(self):
        """Test creating task config with all fields."""
        task = TaskConfig(
            name="test-task",
            model_ref="test-model",
            task_name="hellaswag",
            description="Test task",
            task_config={"limit": 100},
            num_fewshot=5,
            batch_size=32,
            depends_on=["other-task"]
        )
        assert task.description == "Test task"
        assert task.task_config == {"limit": 100}
        assert task.num_fewshot == 5
        assert task.batch_size == 32
        assert task.depends_on == ["other-task"]
    
    def test_empty_name_validation(self):
        """Test that empty name raises ValueError."""
        with pytest.raises(ValueError, match="Task name cannot be empty"):
            TaskConfig(name="", model_ref="test-model", task_name="hellaswag")
    
    def test_empty_model_ref_validation(self):
        """Test that empty model_ref raises ValueError."""
        with pytest.raises(ValueError, match="Model reference cannot be empty"):
            TaskConfig(name="test-task", model_ref="", task_name="hellaswag")
    
    def test_empty_task_name_validation(self):
        """Test that empty task_name raises ValueError."""
        with pytest.raises(ValueError, match="Task name cannot be empty"):
            TaskConfig(name="test-task", model_ref="test-model", task_name="")


class TestDefaultConfig:
    """Test DefaultConfig data model."""
    
    def test_default_values(self):
        """Test default configuration values."""
        defaults = DefaultConfig()
        assert defaults.num_fewshot == 5
        assert defaults.batch_size == 32
        assert defaults.output == {"format": ["json"], "save_predictions": True}
    
    def test_custom_values(self):
        """Test custom configuration values."""
        defaults = DefaultConfig(
            num_fewshot=10,
            batch_size=64,
            output={"format": ["csv"], "save_predictions": False}
        )
        assert defaults.num_fewshot == 10
        assert defaults.batch_size == 64
        assert defaults.output == {"format": ["csv"], "save_predictions": False}


class TestOutputConfig:
    """Test OutputConfig data model."""
    
    def test_default_values(self):
        """Test default output configuration values."""
        output = OutputConfig()
        assert output.directory == "./results"
        assert output.formats == ["json"]
        assert output.include_raw_responses is False
        assert output.generate_report is True
        assert output.compare_models is False
    
    def test_custom_values(self):
        """Test custom output configuration values."""
        output = OutputConfig(
            directory="/tmp/results",
            formats=["json", "csv"],
            include_raw_responses=True,
            generate_report=False,
            compare_models=True
        )
        assert output.directory == "/tmp/results"
        assert output.formats == ["json", "csv"]
        assert output.include_raw_responses is True
        assert output.generate_report is False
        assert output.compare_models is True
    
    def test_invalid_format_validation(self):
        """Test that invalid format raises ValueError."""
        with pytest.raises(ValueError, match="Unsupported output format: invalid"):
            OutputConfig(formats=["json", "invalid"])


class TestValidationError:
    """Test ValidationError data model."""
    
    def test_minimal_error(self):
        """Test creating validation error with minimal fields."""
        error = ValidationError(
            type="syntax",
            message="Test error",
            severity=ValidationSeverity.ERROR
        )
        assert error.type == "syntax"
        assert error.message == "Test error"
        assert error.severity == ValidationSeverity.ERROR
        assert error.location is None
        assert error.suggestion is None
    
    def test_full_error(self):
        """Test creating validation error with all fields."""
        error = ValidationError(
            type="semantic",
            message="Test error",
            severity=ValidationSeverity.WARNING,
            location="config.yaml:10",
            suggestion="Fix the issue"
        )
        assert error.type == "semantic"
        assert error.location == "config.yaml:10"
        assert error.suggestion == "Fix the issue"
    
    def test_string_representation(self):
        """Test string representation of validation error."""
        error = ValidationError(
            type="syntax",
            message="Test error",
            severity=ValidationSeverity.ERROR,
            location="config.yaml:10",
            suggestion="Fix the issue"
        )
        str_repr = str(error)
        assert "ERROR: Test error" in str_repr
        assert "Location: config.yaml:10" in str_repr
        assert "Suggestion: Fix the issue" in str_repr


class TestValidationResult:
    """Test ValidationResult data model."""
    
    def test_empty_result(self):
        """Test empty validation result."""
        result = ValidationResult(is_valid=True)
        assert result.is_valid is True
        assert result.errors == []
        assert result.warnings == []
        assert not result.has_errors()
        assert not result.has_warnings()
    
    def test_add_error(self):
        """Test adding errors to validation result."""
        result = ValidationResult(is_valid=True)
        
        error = ValidationError(
            type="syntax",
            message="Test error",
            severity=ValidationSeverity.ERROR
        )
        result.add_error(error)
        
        assert result.is_valid is False
        assert len(result.errors) == 1
        assert result.has_errors()
    
    def test_add_warning(self):
        """Test adding warnings to validation result."""
        result = ValidationResult(is_valid=True)
        
        warning = ValidationError(
            type="semantic",
            message="Test warning",
            severity=ValidationSeverity.WARNING
        )
        result.add_error(warning)
        
        assert result.is_valid is True  # warnings don't invalidate
        assert len(result.warnings) == 1
        assert result.has_warnings()
    
    def test_get_all_issues(self):
        """Test getting all issues (errors and warnings)."""
        result = ValidationResult(is_valid=True)
        
        error = ValidationError(
            type="syntax",
            message="Test error",
            severity=ValidationSeverity.ERROR
        )
        warning = ValidationError(
            type="semantic",
            message="Test warning",
            severity=ValidationSeverity.WARNING
        )
        
        result.add_error(error)
        result.add_error(warning)
        
        all_issues = result.get_all_issues()
        assert len(all_issues) == 2
        assert error in all_issues
        assert warning in all_issues