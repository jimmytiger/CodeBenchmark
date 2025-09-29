"""
Tests for ConfigDrivenEvaluator.

This module tests the main configuration-driven evaluation functionality,
including batch execution, error recovery, and result collection.
"""

import pytest
import tempfile
import json
import os
from datetime import datetime
from unittest.mock import Mock, patch, MagicMock
from pathlib import Path

from evaluation_engine.config.evaluator import (
    ConfigDrivenEvaluator,
    BatchExecutionResult,
    ConfigDrivenEvaluationResult
)
from evaluation_engine.config.models import (
    EvaluationConfig,
    TaskConfig,
    ModelConfig,
    ConfigMetadata,
    DefaultConfig,
    OutputConfig,
    ValidationResult,
    ValidationError,
    ValidationSeverity
)
from evaluation_engine.core.unified_framework import (
    UnifiedEvaluationFramework,
    EvaluationResult,
    EvaluationRequest,
    ExecutionStatus
)


class TestConfigDrivenEvaluator:
    """Test ConfigDrivenEvaluator functionality."""
    
    @pytest.fixture
    def mock_framework(self):
        """Create mock UnifiedEvaluationFramework."""
        framework = Mock(spec=UnifiedEvaluationFramework)
        
        # Mock successful evaluation result
        mock_result = Mock(spec=EvaluationResult)
        mock_result.evaluation_id = "test_eval_123"
        mock_result.status = ExecutionStatus.COMPLETED
        mock_result.start_time = datetime.now()
        mock_result.end_time = datetime.now()
        mock_result.results = {"test_task": {"accuracy": 0.85}}
        mock_result.metrics_summary = {"test_task_accuracy": 0.85}
        mock_result.analysis = {"summary": "Test completed successfully"}
        mock_result.error = None
        
        framework.evaluate.return_value = mock_result
        return framework
    
    @pytest.fixture
    def sample_config(self):
        """Create sample evaluation configuration."""
        return EvaluationConfig(
            metadata=ConfigMetadata(
                name="test_evaluation",
                version="1.0",
                author="test_author"
            ),
            models={
                "test_model": ModelConfig(
                    name="test_model",
                    type="openai",
                    model_name="gpt-3.5-turbo",
                    parameters={"temperature": 0.7}
                )
            },
            tasks=[
                TaskConfig(
                    name="task1",
                    model_ref="test_model",
                    task_name="hellaswag",
                    num_fewshot=5,
                    depends_on=[]
                ),
                TaskConfig(
                    name="task2",
                    model_ref="test_model",
                    task_name="arc_easy",
                    num_fewshot=10,
                    depends_on=["task1"]
                )
            ],
            defaults=DefaultConfig(num_fewshot=5, batch_size=32),
            output=OutputConfig(directory="./test_results")
        )
    
    @pytest.fixture
    def evaluator(self, mock_framework):
        """Create ConfigDrivenEvaluator with mock framework."""
        return ConfigDrivenEvaluator(framework=mock_framework)
    
    def test_init_with_framework(self, mock_framework):
        """Test initialization with provided framework."""
        evaluator = ConfigDrivenEvaluator(framework=mock_framework)
        assert evaluator.framework is mock_framework
        assert evaluator.parser is not None
        assert evaluator.validator is not None
        assert evaluator.builder is not None
    
    def test_init_without_framework(self):
        """Test initialization without framework (creates new one)."""
        evaluator = ConfigDrivenEvaluator()
        assert evaluator.framework is not None
        assert isinstance(evaluator.framework, UnifiedEvaluationFramework)
    
    def test_run_from_config_success(self, evaluator, sample_config):
        """Test successful configuration-driven evaluation."""
        # Mock the evaluator's parser and validator directly
        with patch.object(evaluator.parser, 'parse_config', return_value=sample_config):
            with patch.object(evaluator.validator, 'validate_config', 
                            return_value=ValidationResult(is_valid=True)):
                
                # Create temporary config file
                with tempfile.NamedTemporaryFile(mode='w', suffix='.yaml', delete=False) as f:
                    f.write("test: config")
                    config_path = f.name
                
                try:
                    # Run evaluation
                    result = evaluator.run_from_config(config_path)
                    
                    # Verify result
                    assert isinstance(result, ConfigDrivenEvaluationResult)
                    assert result.config_metadata.name == "test_evaluation"
                    assert result.validation_result.is_valid
                    assert result.batch_result.total_tasks == 2
                    assert result.batch_result.completed_tasks == 2
                    assert result.batch_result.failed_tasks == 0
                    assert result.config_path == config_path
                    
                finally:
                    os.unlink(config_path)
    
    def test_run_from_config_validation_failure(self, evaluator, sample_config):
        """Test evaluation with validation failure."""
        # Setup validation failure
        mock_validation_result = ValidationResult(is_valid=False)
        mock_validation_result.add_error(ValidationError(
            type="semantic",
            message="Test validation error",
            severity=ValidationSeverity.ERROR
        ))
        
        with patch.object(evaluator.parser, 'parse_config', return_value=sample_config):
            with patch.object(evaluator.validator, 'validate_config', 
                            return_value=mock_validation_result):
                
                # Create temporary config file
                with tempfile.NamedTemporaryFile(mode='w', suffix='.yaml', delete=False) as f:
                    f.write("test: config")
                    config_path = f.name
                
                try:
                    # Run evaluation - should raise ValueError
                    with pytest.raises(ValueError, match="Configuration validation failed"):
                        evaluator.run_from_config(config_path)
                        
                finally:
                    os.unlink(config_path)
    
    def test_run_from_config_dict(self, evaluator, sample_config):
        """Test evaluation from configuration dictionary."""
        config_dict = {
            "metadata": {"name": "test_evaluation"},
            "tasks": [{"name": "task1", "model_ref": "test_model", "task_name": "hellaswag"}],
            "models": {"test_model": {"type": "openai", "model_name": "gpt-3.5-turbo"}}
        }
        
        with patch.object(evaluator.parser, '_parse_raw_config', return_value=sample_config):
            with patch.object(evaluator.validator, 'validate_config', 
                            return_value=ValidationResult(is_valid=True)):
                
                # Run evaluation
                result = evaluator.run_from_config_dict(config_dict)
                
                # Verify result
                assert isinstance(result, ConfigDrivenEvaluationResult)
                assert result.config_path is None  # No file path for dict-based config
    
    def test_run_from_config_with_task_filter(self, evaluator, sample_config):
        """Test evaluation with task filtering."""
        with patch.object(evaluator.parser, 'parse_config', return_value=sample_config):
            with patch.object(evaluator.validator, 'validate_config', 
                            return_value=ValidationResult(is_valid=True)):
                
                # Create temporary config file
                with tempfile.NamedTemporaryFile(mode='w', suffix='.yaml', delete=False) as f:
                    f.write("test: config")
                    config_path = f.name
                
                try:
                    # Run with task filter
                    result = evaluator.run_from_config(config_path, task_filter=["task1"])
                    
                    # Should only execute task1
                    assert result.batch_result.total_tasks == 1
                    assert "task1" in result.batch_result.execution_order
                    assert "task2" not in result.batch_result.execution_order
                    
                finally:
                    os.unlink(config_path)
    
    def test_run_from_config_dry_run(self, evaluator, sample_config):
        """Test dry run mode (validation only, no execution)."""
        with patch.object(evaluator.parser, 'parse_config', return_value=sample_config):
            with patch.object(evaluator.validator, 'validate_config', 
                            return_value=ValidationResult(is_valid=True)):
                
                # Create temporary config file
                with tempfile.NamedTemporaryFile(mode='w', suffix='.yaml', delete=False) as f:
                    f.write("test: config")
                    config_path = f.name
                
                try:
                    # Run in dry run mode
                    result = evaluator.run_from_config(config_path, dry_run=True)
                    
                    # Should have skipped all tasks
                    assert result.batch_result.total_tasks == 2
                    assert result.batch_result.completed_tasks == 0
                    assert result.batch_result.skipped_tasks == 2
                    assert result.batch_result.execution_time == 0.0
                    
                finally:
                    os.unlink(config_path)
    
    def test_run_from_config_with_parameter_overrides(self, evaluator, sample_config):
        """Test evaluation with parameter overrides."""
        overrides = {
            "defaults": {"num_fewshot": 10},
            "output": {"directory": "./custom_results"}
        }
        
        with patch.object(evaluator.parser, 'parse_config', return_value=sample_config):
            with patch.object(evaluator.validator, 'validate_config', 
                            return_value=ValidationResult(is_valid=True)):
                
                # Create temporary config file
                with tempfile.NamedTemporaryFile(mode='w', suffix='.yaml', delete=False) as f:
                    f.write("test: config")
                    config_path = f.name
                
                try:
                    # Run with overrides
                    result = evaluator.run_from_config(config_path, parameter_overrides=overrides)
                    
                    # Verify overrides were applied (indirectly through successful execution)
                    assert result.batch_result.completed_tasks == 2
                    
                finally:
                    os.unlink(config_path)
    
    def test_validate_config_file_success(self, evaluator, sample_config):
        """Test successful configuration file validation."""
        with patch.object(evaluator.parser, 'parse_config', return_value=sample_config):
            with patch.object(evaluator.validator, 'validate_config') as mock_validate:
                mock_validate.return_value = ValidationResult(is_valid=True)
                
                # Create temporary config file
                with tempfile.NamedTemporaryFile(mode='w', suffix='.yaml', delete=False) as f:
                    f.write("test: config")
                    config_path = f.name
                
                try:
                    result = evaluator.validate_config_file(config_path)
                    
                    assert result.is_valid
                    assert not result.has_errors()
                    
                finally:
                    os.unlink(config_path)
    
    def test_validate_config_file_failure(self, evaluator):
        """Test configuration file validation with errors."""
        with patch.object(evaluator.parser, 'parse_config', 
                         side_effect=ValueError("Parse error")):
            
            # Create temporary config file
            with tempfile.NamedTemporaryFile(mode='w', suffix='.yaml', delete=False) as f:
                f.write("invalid: config")
                config_path = f.name
            
            try:
                result = evaluator.validate_config_file(config_path)
                
                assert not result.is_valid
                assert result.has_errors()
                assert "Parse error" in str(result.errors[0])
                
            finally:
                os.unlink(config_path)
    
    def test_execution_callbacks(self, evaluator, sample_config):
        """Test execution callback functionality."""
        callback_events = []
        
        def test_callback(event_type, event_data):
            callback_events.append((event_type, event_data))
        
        # Add callback
        evaluator.add_execution_callback(test_callback)
        
        with patch.object(evaluator.parser, 'parse_config', return_value=sample_config):
            with patch.object(evaluator.validator, 'validate_config', 
                            return_value=ValidationResult(is_valid=True)):
                
                # Create temporary config file
                with tempfile.NamedTemporaryFile(mode='w', suffix='.yaml', delete=False) as f:
                    f.write("test: config")
                    config_path = f.name
                
                try:
                    # Run evaluation
                    evaluator.run_from_config(config_path)
                    
                    # Verify callbacks were called
                    assert len(callback_events) > 0
                    
                    # Check for task_started and task_completed events
                    event_types = [event[0] for event in callback_events]
                    assert "task_started" in event_types
                    assert "task_completed" in event_types
                    
                finally:
                    os.unlink(config_path)
        
        # Remove callback
        evaluator.remove_execution_callback(test_callback)
        assert test_callback not in evaluator._execution_callbacks
    
    def test_export_results(self, evaluator, sample_config):
        """Test result export functionality."""
        with patch.object(evaluator.parser, 'parse_config', return_value=sample_config):
            with patch.object(evaluator.validator, 'validate_config', 
                            return_value=ValidationResult(is_valid=True)):
                
                # Create temporary config file
                with tempfile.NamedTemporaryFile(mode='w', suffix='.yaml', delete=False) as f:
                    f.write("test: config")
                    config_path = f.name
                
                try:
                    # Run evaluation
                    result = evaluator.run_from_config(config_path)
                    
                    # Export results
                    with tempfile.NamedTemporaryFile(mode='w', suffix='.json', delete=False) as f:
                        output_path = f.name
                    
                    try:
                        success = evaluator.export_results(output_path, result)
                        assert success
                        
                        # Verify exported file
                        assert os.path.exists(output_path)
                        
                        with open(output_path, 'r') as f:
                            exported_data = json.load(f)
                        
                        assert exported_data["config_metadata"]["name"] == "test_evaluation"
                        assert exported_data["execution"]["total_tasks"] == 2
                        
                    finally:
                        if os.path.exists(output_path):
                            os.unlink(output_path)
                    
                finally:
                    os.unlink(config_path)
    
    def test_get_current_execution(self, evaluator, sample_config):
        """Test getting current execution result."""
        # Initially no execution
        assert evaluator.get_current_execution() is None
        
        with patch.object(evaluator.parser, 'parse_config', return_value=sample_config):
            with patch.object(evaluator.validator, 'validate_config', 
                            return_value=ValidationResult(is_valid=True)):
                
                # Create temporary config file
                with tempfile.NamedTemporaryFile(mode='w', suffix='.yaml', delete=False) as f:
                    f.write("test: config")
                    config_path = f.name
                
                try:
                    # Run evaluation
                    result = evaluator.run_from_config(config_path)
                    
                    # Should now have current execution
                    current = evaluator.get_current_execution()
                    assert current is not None
                    assert current is result
                    
                finally:
                    os.unlink(config_path)


class TestBatchExecutionResult:
    """Test BatchExecutionResult functionality."""
    
    def test_success_rate_calculation(self):
        """Test success rate calculation."""
        result = BatchExecutionResult(
            total_tasks=10,
            completed_tasks=8,
            failed_tasks=2,
            skipped_tasks=0,
            execution_time=60.0
        )
        
        assert result.success_rate == 80.0
    
    def test_success_rate_zero_tasks(self):
        """Test success rate with zero tasks."""
        result = BatchExecutionResult(
            total_tasks=0,
            completed_tasks=0,
            failed_tasks=0,
            skipped_tasks=0,
            execution_time=0.0
        )
        
        assert result.success_rate == 0.0
    
    def test_is_successful(self):
        """Test is_successful property."""
        # Successful case
        successful_result = BatchExecutionResult(
            total_tasks=5,
            completed_tasks=5,
            failed_tasks=0,
            skipped_tasks=0,
            execution_time=30.0
        )
        assert successful_result.is_successful
        
        # Failed case
        failed_result = BatchExecutionResult(
            total_tasks=5,
            completed_tasks=3,
            failed_tasks=2,
            skipped_tasks=0,
            execution_time=30.0
        )
        assert not failed_result.is_successful


class TestConfigDrivenEvaluationResult:
    """Test ConfigDrivenEvaluationResult functionality."""
    
    @pytest.fixture
    def sample_result(self):
        """Create sample evaluation result."""
        metadata = ConfigMetadata(name="test_eval", version="1.0")
        validation_result = ValidationResult(is_valid=True)
        batch_result = BatchExecutionResult(
            total_tasks=2,
            completed_tasks=2,
            failed_tasks=0,
            skipped_tasks=0,
            execution_time=45.0
        )
        
        start_time = datetime(2024, 1, 1, 10, 0, 0)
        end_time = datetime(2024, 1, 1, 10, 5, 0)
        
        return ConfigDrivenEvaluationResult(
            config_metadata=metadata,
            validation_result=validation_result,
            batch_result=batch_result,
            start_time=start_time,
            end_time=end_time,
            config_path="/path/to/config.yaml"
        )
    
    def test_total_execution_time(self, sample_result):
        """Test total execution time calculation."""
        assert sample_result.total_execution_time == 300.0  # 5 minutes
    
    def test_to_dict(self, sample_result):
        """Test conversion to dictionary."""
        result_dict = sample_result.to_dict()
        
        assert result_dict["config_metadata"]["name"] == "test_eval"
        assert result_dict["validation"]["is_valid"] is True
        assert result_dict["execution"]["total_tasks"] == 2
        assert result_dict["execution"]["completed_tasks"] == 2
        assert result_dict["execution"]["success_rate"] == 100.0
        assert result_dict["timing"]["total_execution_time"] == 300.0
        assert result_dict["config_path"] == "/path/to/config.yaml"


class TestErrorRecovery:
    """Test error recovery and failure handling."""
    
    @pytest.fixture
    def failing_framework(self):
        """Create framework that fails on certain tasks."""
        framework = Mock(spec=UnifiedEvaluationFramework)
        
        def mock_evaluate(request):
            # Check if this is task2 by looking at the tasks list
            task_names = request.tasks if hasattr(request, 'tasks') else []
            
            # Fail on arc_easy (task2), succeed on others
            if "arc_easy" in task_names:
                result = Mock(spec=EvaluationResult)
                result.status = ExecutionStatus.FAILED
                result.error = "Simulated task failure"
                result.start_time = datetime.now()
                result.end_time = datetime.now()
                return result
            else:
                result = Mock(spec=EvaluationResult)
                result.status = ExecutionStatus.COMPLETED
                result.start_time = datetime.now()
                result.end_time = datetime.now()
                result.results = {"test": {"accuracy": 0.8}}
                result.metrics_summary = {"test_accuracy": 0.8}
                result.analysis = {"summary": "Success"}
                result.error = None
                return result
        
        framework.evaluate.side_effect = mock_evaluate
        return framework
    
    def test_task_failure_recovery(self, failing_framework):
        """Test recovery from individual task failures."""
        evaluator = ConfigDrivenEvaluator(framework=failing_framework)
        
        config = EvaluationConfig(
            metadata=ConfigMetadata(name="test_failure_recovery"),
            models={
                "test_model": ModelConfig(
                    name="test_model",
                    type="openai",
                    model_name="gpt-3.5-turbo"
                )
            },
            tasks=[
                TaskConfig(
                    name="task1",
                    model_ref="test_model",
                    task_name="hellaswag",
                    depends_on=[]
                ),
                TaskConfig(
                    name="task2",
                    model_ref="test_model",
                    task_name="arc_easy",
                    depends_on=[]
                ),
                TaskConfig(
                    name="task3",
                    model_ref="test_model",
                    task_name="truthfulqa_mc",
                    depends_on=[]
                )
            ]
        )
        
        with patch.object(evaluator.parser, 'parse_config', return_value=config):
            with patch.object(evaluator.validator, 'validate_config', 
                            return_value=ValidationResult(is_valid=True)):
                
                # Create temporary config file
                with tempfile.NamedTemporaryFile(mode='w', suffix='.yaml', delete=False) as f:
                    f.write("test: config")
                    config_path = f.name
                
                try:
                    # Run evaluation (should continue despite task2 failure)
                    result = evaluator.run_from_config(config_path, fail_fast=False)
                    
                    # Should have 2 completed, 1 failed
                    assert result.batch_result.total_tasks == 3
                    assert result.batch_result.completed_tasks == 2
                    assert result.batch_result.failed_tasks == 1
                    assert "task2" in result.batch_result.task_errors
                    
                finally:
                    os.unlink(config_path)
    
    def test_fail_fast_mode(self, failing_framework):
        """Test fail-fast mode stops on first failure."""
        evaluator = ConfigDrivenEvaluator(framework=failing_framework)
        
        config = EvaluationConfig(
            metadata=ConfigMetadata(name="test_fail_fast"),
            models={
                "test_model": ModelConfig(
                    name="test_model",
                    type="openai",
                    model_name="gpt-3.5-turbo"
                )
            },
            tasks=[
                TaskConfig(
                    name="task1",
                    model_ref="test_model",
                    task_name="hellaswag",
                    depends_on=[]
                ),
                TaskConfig(
                    name="task2",
                    model_ref="test_model",
                    task_name="arc_easy",
                    depends_on=["task1"]
                ),
                TaskConfig(
                    name="task3",
                    model_ref="test_model",
                    task_name="truthfulqa_mc",
                    depends_on=["task2"]
                )
            ]
        )
        
        with patch.object(evaluator.parser, 'parse_config', return_value=config):
            with patch.object(evaluator.validator, 'validate_config', 
                            return_value=ValidationResult(is_valid=True)):
                
                # Create temporary config file
                with tempfile.NamedTemporaryFile(mode='w', suffix='.yaml', delete=False) as f:
                    f.write("test: config")
                    config_path = f.name
                
                try:
                    # Run evaluation with fail_fast=True
                    result = evaluator.run_from_config(config_path, fail_fast=True)
                    
                    # Should stop after task2 fails, task3 should be skipped
                    assert result.batch_result.completed_tasks == 1  # task1
                    assert result.batch_result.failed_tasks == 1     # task2
                    # task3 should be marked as failed due to fail-fast
                    assert result.batch_result.total_tasks == 3
                    
                finally:
                    os.unlink(config_path)


if __name__ == "__main__":
    pytest.main([__file__])