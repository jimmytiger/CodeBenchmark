"""
Basic tests for configuration API functionality without authentication.

Tests the core configuration API logic by mocking authentication.
"""

import pytest
import json
import tempfile
import os
from datetime import datetime
from unittest.mock import Mock, patch, MagicMock

from evaluation_engine.api.config_models import *
from evaluation_engine.config.models import EvaluationConfig, ConfigMetadata, TaskConfig, ModelConfig


class TestConfigurationModels:
    """Test configuration API models."""
    
    def test_config_upload_request_validation(self):
        """Test ConfigUploadRequest validation."""
        # Valid request
        request = ConfigUploadRequest(
            config_content="test content",
            format=ConfigFormat.YAML,
            name="Test Config"
        )
        assert request.config_content == "test content"
        assert request.format == ConfigFormat.YAML
        
        # Invalid request - empty content
        with pytest.raises(ValueError, match="Configuration content cannot be empty"):
            ConfigUploadRequest(
                config_content="",
                format=ConfigFormat.YAML
            )
    
    def test_config_validation_request(self):
        """Test ConfigValidationRequest validation."""
        request = ConfigValidationRequest(
            config_content="test: content",
            format=ConfigFormat.YAML
        )
        assert request.config_content == "test: content"
        
        # Invalid - empty content
        with pytest.raises(ValueError):
            ConfigValidationRequest(
                config_content="   ",
                format=ConfigFormat.YAML
            )
    
    def test_config_execution_request(self):
        """Test ConfigExecutionRequest validation."""
        # Valid with config_id
        request = ConfigExecutionRequest(
            config_id="test-config-id",
            dry_run=True
        )
        assert request.config_id == "test-config-id"
        assert request.dry_run is True
        
        # Valid with inline config
        request = ConfigExecutionRequest(
            config_content="test: content",
            format=ConfigFormat.YAML,
            fail_fast=True
        )
        assert request.config_content == "test: content"
        assert request.format == ConfigFormat.YAML
        
        # Invalid - neither config_id nor config_content
        with pytest.raises(ValueError, match="Either config_id or config_content must be provided"):
            ConfigExecutionRequest(dry_run=True)
        
        # Invalid - both config_id and config_content
        with pytest.raises(ValueError, match="Cannot specify both config_id and config_content"):
            ConfigExecutionRequest(
                config_id="test-id",
                config_content="test content",
                format=ConfigFormat.YAML
            )
    
    def test_config_export_request(self):
        """Test ConfigExportRequest validation."""
        request = ConfigExportRequest(
            evaluation_id="test-eval-id",
            format="json",
            include_raw_results=True
        )
        assert request.evaluation_id == "test-eval-id"
        assert request.format == "json"
        
        # Test format validation
        with pytest.raises(ValueError, match="Unsupported format"):
            ConfigExportRequest(
                evaluation_id="test-eval-id",
                format="unsupported"
            )


class TestConfigurationLogic:
    """Test configuration API logic without FastAPI dependencies."""
    
    def test_estimate_execution_duration(self):
        """Test execution duration estimation."""
        from evaluation_engine.api.config_endpoints import _estimate_execution_duration
        
        # Mock config with tasks
        mock_config = Mock()
        mock_config.tasks = [Mock(), Mock(), Mock()]  # 3 tasks
        
        duration = _estimate_execution_duration(mock_config)
        assert duration == 180  # 3 tasks * 60 seconds each
    
    def test_estimate_completion_time(self):
        """Test completion time estimation."""
        from evaluation_engine.api.config_endpoints import _estimate_completion_time
        
        mock_config = Mock()
        mock_config.tasks = [Mock(), Mock()]  # 2 tasks
        
        # Test dry run
        completion_time = _estimate_completion_time(mock_config, dry_run=True)
        assert completion_time > datetime.utcnow()
        
        # Test normal run
        completion_time = _estimate_completion_time(mock_config, dry_run=False)
        assert completion_time > datetime.utcnow()
    
    def test_create_execution_status(self):
        """Test execution status creation."""
        from evaluation_engine.api.config_endpoints import _create_execution_status
        
        execution_data = {
            "evaluation_id": "test-eval-id",
            "config_id": "test-config-id",
            "status": ConfigEvaluationStatus.RUNNING,
            "progress": 0.5,
            "task_count": 3,
            "task_details": [
                {
                    "task_name": "task1",
                    "status": TaskExecutionStatus.COMPLETED,
                    "progress": 1.0
                },
                {
                    "task_name": "task2",
                    "status": TaskExecutionStatus.RUNNING,
                    "progress": 0.5
                },
                {
                    "task_name": "task3",
                    "status": TaskExecutionStatus.PENDING,
                    "progress": 0.0
                }
            ]
        }
        
        status = _create_execution_status(execution_data)
        
        assert status.evaluation_id == "test-eval-id"
        assert status.config_id == "test-config-id"
        assert status.status == ConfigEvaluationStatus.RUNNING
        assert status.progress == 0.5
        assert status.total_tasks == 3
        assert status.completed_tasks == 1
        assert status.running_tasks == 1
        assert status.pending_tasks == 1
        assert len(status.task_details) == 3


class TestConfigurationIntegration:
    """Test configuration API integration with existing components."""
    
    def test_config_parser_integration(self):
        """Test integration with ConfigParser."""
        from evaluation_engine.config.parser import ConfigParser
        
        # Create a simple YAML config
        config_yaml = """
metadata:
  name: "Test Config"
  version: "1.0"

models:
  test_model:
    name: "test_model"
    type: "openai"
    model_name: "gpt-3.5-turbo"
    parameters:
      temperature: 0.7

tasks:
  - name: "test_task"
    model_ref: "test_model"
    task_name: "hellaswag"
    depends_on: []

output:
  directory: "./results"
  formats: ["json"]
"""
        
        # Test parsing
        parser = ConfigParser()
        
        with tempfile.NamedTemporaryFile(mode='w', suffix='.yaml', delete=False) as f:
            f.write(config_yaml)
            temp_path = f.name
        
        try:
            config = parser.parse_config(temp_path)
            
            assert config.metadata.name == "Test Config"
            assert len(config.tasks) == 1
            assert len(config.models) == 1
            assert config.tasks[0].name == "test_task"
            assert config.models["test_model"].type == "openai"
            
        finally:
            os.unlink(temp_path)
    
    def test_config_validator_integration(self):
        """Test integration with ConfigValidator."""
        from evaluation_engine.config.validator import ConfigValidator
        from evaluation_engine.config.models import EvaluationConfig, ConfigMetadata, TaskConfig, ModelConfig, DefaultConfig, OutputConfig
        
        # Create a valid config
        config = EvaluationConfig(
            metadata=ConfigMetadata(name="Test Config"),
            variables={},
            models={
                "test_model": ModelConfig(
                    name="test_model",
                    type="openai",
                    model_name="gpt-3.5-turbo",
                    parameters={}
                )
            },
            defaults=DefaultConfig(),
            tasks=[
                TaskConfig(
                    name="test_task",
                    model_ref="test_model",
                    task_name="hellaswag",
                    depends_on=[]
                )
            ],
            output=OutputConfig(directory="./results", formats=["json"])
        )
        
        validator = ConfigValidator()
        result = validator.validate_config(config)
        
        assert result.is_valid
        assert len(result.errors) == 0
    
    def test_config_evaluator_integration(self):
        """Test integration with ConfigDrivenEvaluator."""
        from evaluation_engine.config.evaluator import ConfigDrivenEvaluator
        
        # Create evaluator
        evaluator = ConfigDrivenEvaluator()
        
        # Test that evaluator is properly initialized
        assert evaluator.framework is not None
        assert evaluator.parser is not None
        assert evaluator.validator is not None
        assert evaluator.builder is not None


class TestConfigurationAPIWorkflow:
    """Test complete configuration API workflow."""
    
    def test_upload_validate_execute_workflow(self):
        """Test the complete workflow from upload to execution."""
        # This test simulates the API workflow without FastAPI
        
        # Step 1: Simulate configuration upload
        config_content = """
metadata:
  name: "Workflow Test Config"
  version: "1.0"

models:
  gpt35:
    name: "gpt35"
    type: "openai"
    model_name: "gpt-3.5-turbo"
    parameters:
      temperature: 0.7

tasks:
  - name: "test_task"
    model_ref: "gpt35"
    task_name: "hellaswag"
    task_config:
      limit: 10
    depends_on: []

output:
  directory: "./test_results"
  formats: ["json"]
"""
        
        upload_request = ConfigUploadRequest(
            config_content=config_content,
            format=ConfigFormat.YAML,
            name="Workflow Test"
        )
        
        assert upload_request.config_content is not None
        assert upload_request.format == ConfigFormat.YAML
        
        # Step 2: Simulate validation
        validation_request = ConfigValidationRequest(
            config_content=config_content,
            format=ConfigFormat.YAML
        )
        
        assert validation_request.config_content == config_content
        
        # Step 3: Simulate execution request
        execution_request = ConfigExecutionRequest(
            config_content=config_content,
            format=ConfigFormat.YAML,
            dry_run=True,
            task_filter=["test_task"]
        )
        
        assert execution_request.config_content == config_content
        assert execution_request.dry_run is True
        assert execution_request.task_filter == ["test_task"]
        
        # Step 4: Simulate export request
        export_request = ConfigExportRequest(
            evaluation_id="test-eval-id",
            format="json",
            include_raw_results=True
        )
        
        assert export_request.evaluation_id == "test-eval-id"
        assert export_request.format == "json"
    
    def test_error_scenarios(self):
        """Test error handling scenarios."""
        
        # Test invalid configuration content
        with pytest.raises(ValueError):
            ConfigUploadRequest(
                config_content="",
                format=ConfigFormat.YAML
            )
        
        # Test invalid execution request
        with pytest.raises(ValueError):
            ConfigExecutionRequest()
        
        # Test invalid export format
        with pytest.raises(ValueError):
            ConfigExportRequest(
                evaluation_id="test-id",
                format="invalid-format"
            )


if __name__ == "__main__":
    pytest.main([__file__])