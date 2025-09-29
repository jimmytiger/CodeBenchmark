"""
Tests for configuration-driven evaluation API endpoints.

Tests all configuration API functionality including upload, validation,
execution, and result management.
"""

import pytest
import json
import tempfile
import os
from datetime import datetime
from unittest.mock import Mock, patch, AsyncMock
from fastapi.testclient import TestClient
from fastapi import FastAPI

from evaluation_engine.api.config_endpoints import router
from evaluation_engine.api.config_models import *
from evaluation_engine.config.models import EvaluationConfig, ConfigMetadata, TaskConfig, ModelConfig


def mock_permission_dependency():
    """Mock permission dependency."""
    return {"user_id": "test_user"}


@pytest.fixture
def app():
    """Create test FastAPI app."""
    from evaluation_engine.api.config_endpoints import permission_checker
    
    app = FastAPI()
    
    # Override all permission dependencies before including router
    app.dependency_overrides[permission_checker.require_permission("config:create")] = mock_permission_dependency
    app.dependency_overrides[permission_checker.require_permission("config:read")] = mock_permission_dependency
    app.dependency_overrides[permission_checker.require_permission("config:execute")] = mock_permission_dependency
    app.dependency_overrides[permission_checker.require_permission("config:delete")] = mock_permission_dependency
    
    app.include_router(router)
    return app


@pytest.fixture
def client(app):
    """Create test client."""
    return TestClient(app)


@pytest.fixture
def sample_config_yaml():
    """Sample YAML configuration."""
    return """
metadata:
  name: "Test Configuration"
  version: "1.0"
  author: "Test User"
  description: "Test configuration for API testing"

variables:
  output_dir: "./test_results"
  batch_size: 16

models:
  test_model:
    name: "test_model"
    type: "openai"
    model_name: "gpt-3.5-turbo"
    parameters:
      temperature: 0.7
      max_tokens: 1000

defaults:
  num_fewshot: 5
  batch_size: "${batch_size}"

tasks:
  - name: "test_task"
    description: "Test task"
    model_ref: "test_model"
    task_name: "hellaswag"
    num_fewshot: 10
    depends_on: []

output:
  directory: "${output_dir}"
  formats: ["json"]
"""


@pytest.fixture
def sample_config_json():
    """Sample JSON configuration."""
    return json.dumps({
        "metadata": {
            "name": "Test Configuration JSON",
            "version": "1.0",
            "author": "Test User",
            "description": "Test JSON configuration"
        },
        "variables": {
            "output_dir": "./test_results"
        },
        "models": {
            "test_model": {
                "name": "test_model",
                "type": "openai",
                "model_name": "gpt-3.5-turbo",
                "parameters": {
                    "temperature": 0.7
                }
            }
        },
        "defaults": {
            "num_fewshot": 5
        },
        "tasks": [
            {
                "name": "test_task",
                "description": "Test task",
                "model_ref": "test_model",
                "task_name": "hellaswag",
                "depends_on": []
            }
        ],
        "output": {
            "directory": "./test_results",
            "formats": ["json"]
        }
    })


class TestConfigurationUpload:
    """Test configuration upload endpoints."""
    
    def test_upload_yaml_configuration(self, client, sample_config_yaml):
        """Test uploading YAML configuration."""
        with patch('evaluation_engine.api.config_endpoints.ConfigParser') as mock_parser, \
             patch('evaluation_engine.api.config_endpoints.ConfigValidator') as mock_validator:
            
            # Mock parser and validator
            mock_config = Mock()
            mock_config.metadata = ConfigMetadata(name="Test Config")
            mock_config.tasks = [Mock()]
            mock_config.models = {"test_model": Mock()}
            
            mock_parser.return_value.parse_config.return_value = mock_config
            
            mock_validation = Mock()
            mock_validation.is_valid = True
            mock_validation.errors = []
            mock_validation.warnings = []
            mock_validator.return_value.validate_config.return_value = mock_validation
            
            # Test upload
            response = client.post(
                "/config/upload",
                json={
                    "config_content": sample_config_yaml,
                    "format": "yaml",
                    "name": "Test Config",
                    "description": "Test description"
                }
            )
            
            print(f"Response status: {response.status_code}")
            print(f"Response content: {response.content}")
            assert response.status_code == 200
            data = response.json()
            assert "config_id" in data
            assert data["name"] == "Test Config"
            assert data["format"] == "yaml"
            assert data["validation"]["is_valid"] is True
    
    def test_upload_json_configuration(self, client, mock_auth, sample_config_json):
        """Test uploading JSON configuration."""
        with patch('evaluation_engine.api.config_endpoints.ConfigParser') as mock_parser, \
             patch('evaluation_engine.api.config_endpoints.ConfigValidator') as mock_validator:
            
            # Mock parser and validator
            mock_config = Mock()
            mock_config.metadata = ConfigMetadata(name="Test Config JSON")
            mock_config.tasks = [Mock()]
            mock_config.models = {"test_model": Mock()}
            
            mock_parser.return_value.parse_config.return_value = mock_config
            
            mock_validation = Mock()
            mock_validation.is_valid = True
            mock_validation.errors = []
            mock_validation.warnings = []
            mock_validator.return_value.validate_config.return_value = mock_validation
            
            # Test upload
            response = client.post(
                "/config/upload",
                json={
                    "config_content": sample_config_json,
                    "format": "json",
                    "name": "Test Config JSON"
                }
            )
            
            assert response.status_code == 200
            data = response.json()
            assert data["name"] == "Test Config JSON"
            assert data["format"] == "json"
    
    def test_upload_invalid_configuration(self, client, mock_auth):
        """Test uploading invalid configuration."""
        with patch('evaluation_engine.api.config_endpoints.ConfigParser') as mock_parser:
            mock_parser.return_value.parse_config.side_effect = Exception("Invalid YAML")
            
            response = client.post(
                "/config/upload",
                json={
                    "config_content": "invalid: yaml: content:",
                    "format": "yaml"
                }
            )
            
            assert response.status_code == 400
            assert "Configuration upload failed" in response.json()["detail"]
    
    def test_upload_file_yaml(self, client, mock_auth, sample_config_yaml):
        """Test uploading configuration file (YAML)."""
        with patch('evaluation_engine.api.config_endpoints.ConfigParser') as mock_parser, \
             patch('evaluation_engine.api.config_endpoints.ConfigValidator') as mock_validator:
            
            # Mock parser and validator
            mock_config = Mock()
            mock_config.metadata = ConfigMetadata(name="Test Config")
            mock_config.tasks = [Mock()]
            mock_config.models = {"test_model": Mock()}
            
            mock_parser.return_value.parse_config.return_value = mock_config
            
            mock_validation = Mock()
            mock_validation.is_valid = True
            mock_validation.errors = []
            mock_validation.warnings = []
            mock_validator.return_value.validate_config.return_value = mock_validation
            
            # Create temporary file
            with tempfile.NamedTemporaryFile(mode='w', suffix='.yaml', delete=False) as f:
                f.write(sample_config_yaml)
                temp_path = f.name
            
            try:
                # Test file upload
                with open(temp_path, 'rb') as f:
                    response = client.post(
                        "/config/upload-file",
                        files={"file": ("test_config.yaml", f, "text/yaml")}
                    )
                
                assert response.status_code == 200
                data = response.json()
                assert data["name"] == "test_config"
                assert data["format"] == "yaml"
                
            finally:
                os.unlink(temp_path)
    
    def test_upload_file_unsupported_format(self, client, mock_auth):
        """Test uploading file with unsupported format."""
        with tempfile.NamedTemporaryFile(mode='w', suffix='.txt', delete=False) as f:
            f.write("some content")
            temp_path = f.name
        
        try:
            with open(temp_path, 'rb') as f:
                response = client.post(
                    "/config/upload-file",
                    files={"file": ("test_config.txt", f, "text/plain")}
                )
            
            assert response.status_code == 400
            assert "Unsupported file format" in response.json()["detail"]
            
        finally:
            os.unlink(temp_path)


class TestConfigurationValidation:
    """Test configuration validation endpoints."""
    
    def test_validate_valid_configuration(self, client, mock_auth, sample_config_yaml):
        """Test validating valid configuration."""
        with patch('evaluation_engine.api.config_endpoints.ConfigParser') as mock_parser, \
             patch('evaluation_engine.api.config_endpoints.ConfigValidator') as mock_validator:
            
            # Mock parser and validator
            mock_config = Mock()
            mock_config.tasks = [Mock()]
            mock_config.models = {"test_model": Mock()}
            
            mock_parser.return_value.parse_config.return_value = mock_config
            
            mock_validation = Mock()
            mock_validation.is_valid = True
            mock_validation.errors = []
            mock_validation.warnings = []
            mock_validator.return_value.validate_config.return_value = mock_validation
            
            # Test validation
            response = client.post(
                "/config/validate",
                json={
                    "config_content": sample_config_yaml,
                    "format": "yaml"
                }
            )
            
            assert response.status_code == 200
            data = response.json()
            assert data["is_valid"] is True
            assert data["status"] == "valid"
            assert len(data["errors"]) == 0
    
    def test_validate_invalid_configuration(self, client, mock_auth):
        """Test validating invalid configuration."""
        with patch('evaluation_engine.api.config_endpoints.ConfigParser') as mock_parser, \
             patch('evaluation_engine.api.config_endpoints.ConfigValidator') as mock_validator:
            
            # Mock parser and validator
            mock_config = Mock()
            mock_config.tasks = []
            mock_config.models = {}
            
            mock_parser.return_value.parse_config.return_value = mock_config
            
            mock_error = Mock()
            mock_error.type = "validation"
            mock_error.message = "No tasks defined"
            mock_error.severity.value = "error"
            mock_error.location = None
            mock_error.suggestion = None
            
            mock_validation = Mock()
            mock_validation.is_valid = False
            mock_validation.errors = [mock_error]
            mock_validation.warnings = []
            mock_validator.return_value.validate_config.return_value = mock_validation
            
            # Test validation
            response = client.post(
                "/config/validate",
                json={
                    "config_content": "metadata:\n  name: test",
                    "format": "yaml"
                }
            )
            
            assert response.status_code == 200
            data = response.json()
            assert data["is_valid"] is False
            assert data["status"] == "invalid"
            assert len(data["errors"]) == 1
            assert data["errors"][0]["message"] == "No tasks defined"


class TestConfigurationManagement:
    """Test configuration management endpoints."""
    
    def test_list_configurations_empty(self, client, mock_auth):
        """Test listing configurations when none exist."""
        # Clear configurations
        with patch('evaluation_engine.api.config_endpoints._configurations', {}):
            response = client.get("/config/")
            
            assert response.status_code == 200
            data = response.json()
            assert data["total"] == 0
            assert len(data["configurations"]) == 0
    
    def test_list_configurations_with_data(self, client, mock_auth):
        """Test listing configurations with data."""
        # Mock configurations
        mock_configs = {
            "config1": {
                "config_id": "config1",
                "name": "Test Config 1",
                "description": "Description 1",
                "format": ConfigFormat.YAML,
                "uploaded_at": datetime.utcnow(),
                "size_bytes": 1000,
                "is_valid": True,
                "validation": Mock(task_count=2, model_count=1)
            }
        }
        
        with patch('evaluation_engine.api.config_endpoints._configurations', mock_configs):
            response = client.get("/config/")
            
            assert response.status_code == 200
            data = response.json()
            assert data["total"] == 1
            assert len(data["configurations"]) == 1
            assert data["configurations"][0]["config_id"] == "config1"
    
    def test_get_configuration_details(self, client, mock_auth):
        """Test getting configuration details."""
        # Mock configuration
        mock_config_obj = Mock()
        mock_config_obj.metadata = ConfigMetadata(name="Test", version="1.0", author="User")
        mock_config_obj.tasks = [Mock(name="task1", description="desc", model_ref="model1", task_name="test", depends_on=[])]
        mock_config_obj.models = {"model1": Mock(name="model1", type="openai", model_name="gpt-3.5", parameters={})}
        
        mock_config = {
            "config_id": "config1",
            "name": "Test Config",
            "description": "Test description",
            "format": ConfigFormat.YAML,
            "uploaded_at": datetime.utcnow(),
            "size_bytes": 1000,
            "is_valid": True,
            "content": "test content",
            "validation": Mock(),
            "config_object": mock_config_obj
        }
        
        with patch('evaluation_engine.api.config_endpoints._configurations', {"config1": mock_config}):
            response = client.get("/config/config1")
            
            assert response.status_code == 200
            data = response.json()
            assert data["config_id"] == "config1"
            assert data["name"] == "Test Config"
            assert data["content"] == "test content"
    
    def test_get_nonexistent_configuration(self, client, mock_auth):
        """Test getting nonexistent configuration."""
        with patch('evaluation_engine.api.config_endpoints._configurations', {}):
            response = client.get("/config/nonexistent")
            
            assert response.status_code == 404
            assert "Configuration not found" in response.json()["detail"]
    
    def test_delete_configuration(self, client, mock_auth):
        """Test deleting configuration."""
        mock_config = {
            "config_id": "config1",
            "name": "Test Config"
        }
        
        with patch('evaluation_engine.api.config_endpoints._configurations', {"config1": mock_config}), \
             patch('evaluation_engine.api.config_endpoints._executions', {}):
            
            response = client.delete("/config/config1")
            
            assert response.status_code == 200
            assert "deleted successfully" in response.json()["message"]
    
    def test_delete_configuration_with_active_execution(self, client, mock_auth):
        """Test deleting configuration with active execution."""
        mock_config = {"config_id": "config1"}
        mock_execution = {
            "config_id": "config1",
            "status": ConfigEvaluationStatus.RUNNING
        }
        
        with patch('evaluation_engine.api.config_endpoints._configurations', {"config1": mock_config}), \
             patch('evaluation_engine.api.config_endpoints._executions', {"exec1": mock_execution}):
            
            response = client.delete("/config/config1")
            
            assert response.status_code == 409
            assert "active executions" in response.json()["detail"]


class TestConfigurationExecution:
    """Test configuration execution endpoints."""
    
    def test_execute_uploaded_configuration(self, client, mock_auth):
        """Test executing uploaded configuration."""
        # Mock configuration
        mock_config_obj = Mock()
        mock_config_obj.tasks = [Mock()]
        mock_config_obj.metadata.name = "Test Config"
        
        mock_config = {
            "config_id": "config1",
            "is_valid": True,
            "config_object": mock_config_obj
        }
        
        with patch('evaluation_engine.api.config_endpoints._configurations', {"config1": mock_config}), \
             patch('evaluation_engine.api.config_endpoints._executions', {}):
            
            response = client.post(
                "/config/execute",
                json={
                    "config_id": "config1",
                    "dry_run": True
                }
            )
            
            assert response.status_code == 200
            data = response.json()
            assert "evaluation_id" in data
            assert data["config_id"] == "config1"
            assert data["status"] == "created"
            assert data["dry_run"] is True
    
    def test_execute_inline_configuration(self, client, mock_auth, sample_config_yaml):
        """Test executing inline configuration."""
        with patch('evaluation_engine.api.config_endpoints.ConfigParser') as mock_parser:
            mock_config = Mock()
            mock_config.tasks = [Mock()]
            mock_config.metadata.name = "Inline Config"
            mock_parser.return_value.parse_config.return_value = mock_config
            
            response = client.post(
                "/config/execute",
                json={
                    "config_content": sample_config_yaml,
                    "format": "yaml",
                    "dry_run": True
                }
            )
            
            assert response.status_code == 200
            data = response.json()
            assert "evaluation_id" in data
            assert data["config_id"] is None
            assert data["dry_run"] is True
    
    def test_execute_nonexistent_configuration(self, client, mock_auth):
        """Test executing nonexistent configuration."""
        with patch('evaluation_engine.api.config_endpoints._configurations', {}):
            response = client.post(
                "/config/execute",
                json={"config_id": "nonexistent"}
            )
            
            assert response.status_code == 404
            assert "Configuration not found" in response.json()["detail"]
    
    def test_execute_invalid_configuration(self, client, mock_auth):
        """Test executing invalid configuration."""
        mock_config = {
            "config_id": "config1",
            "is_valid": False
        }
        
        with patch('evaluation_engine.api.config_endpoints._configurations', {"config1": mock_config}):
            response = client.post(
                "/config/execute",
                json={"config_id": "config1"}
            )
            
            assert response.status_code == 400
            assert "not valid" in response.json()["detail"]


class TestExecutionManagement:
    """Test execution management endpoints."""
    
    def test_list_executions(self, client, mock_auth):
        """Test listing executions."""
        mock_execution = {
            "evaluation_id": "exec1",
            "config_id": "config1",
            "status": ConfigEvaluationStatus.COMPLETED,
            "created_at": datetime.utcnow(),
            "task_count": 2,
            "task_details": []
        }
        
        with patch('evaluation_engine.api.config_endpoints._executions', {"exec1": mock_execution}):
            response = client.get("/config/executions")
            
            assert response.status_code == 200
            data = response.json()
            assert data["total"] == 1
            assert len(data["executions"]) == 1
            assert data["executions"][0]["evaluation_id"] == "exec1"
    
    def test_get_execution_status(self, client, mock_auth):
        """Test getting execution status."""
        mock_execution = {
            "evaluation_id": "exec1",
            "config_id": "config1",
            "status": ConfigEvaluationStatus.RUNNING,
            "created_at": datetime.utcnow(),
            "task_count": 2,
            "task_details": [],
            "progress": 0.5
        }
        
        with patch('evaluation_engine.api.config_endpoints._executions', {"exec1": mock_execution}):
            response = client.get("/config/executions/exec1")
            
            assert response.status_code == 200
            data = response.json()
            assert data["evaluation_id"] == "exec1"
            assert data["status"] == "running"
            assert data["progress"] == 0.5
    
    def test_get_execution_results(self, client, mock_auth):
        """Test getting execution results."""
        mock_execution = {
            "evaluation_id": "exec1",
            "config_id": "config1",
            "status": ConfigEvaluationStatus.COMPLETED,
            "created_at": datetime.utcnow(),
            "task_count": 2,
            "result_data": {
                "config_metadata": {"name": "Test"},
                "total_execution_time": 120.5,
                "completed_tasks": 2,
                "failed_tasks": 0,
                "skipped_tasks": 0,
                "success_rate": 100.0,
                "task_results": {},
                "task_summaries": {},
                "execution_order": ["task1", "task2"]
            }
        }
        
        with patch('evaluation_engine.api.config_endpoints._executions', {"exec1": mock_execution}):
            response = client.get("/config/executions/exec1/results")
            
            assert response.status_code == 200
            data = response.json()
            assert data["evaluation_id"] == "exec1"
            assert data["status"] == "completed"
            assert data["success_rate"] == 100.0
    
    def test_cancel_execution(self, client, mock_auth):
        """Test cancelling execution."""
        mock_execution = {
            "evaluation_id": "exec1",
            "status": ConfigEvaluationStatus.RUNNING
        }
        
        with patch('evaluation_engine.api.config_endpoints._executions', {"exec1": mock_execution}):
            response = client.post("/config/executions/exec1/cancel")
            
            assert response.status_code == 200
            assert "cancelled successfully" in response.json()["message"]


class TestResultExport:
    """Test result export endpoints."""
    
    def test_export_results(self, client, mock_auth):
        """Test exporting results."""
        mock_execution = {
            "evaluation_id": "exec1",
            "status": ConfigEvaluationStatus.COMPLETED,
            "result_data": {"test": "data"}
        }
        
        with patch('evaluation_engine.api.config_endpoints._executions', {"exec1": mock_execution}), \
             patch('evaluation_engine.api.config_endpoints._exports', {}):
            
            response = client.post(
                "/config/executions/exec1/export",
                json={
                    "evaluation_id": "exec1",
                    "format": "json",
                    "include_raw_results": True
                }
            )
            
            assert response.status_code == 200
            data = response.json()
            assert "export_id" in data
            assert data["evaluation_id"] == "exec1"
            assert data["format"] == "json"
            assert data["status"] == "processing"
    
    def test_get_export_status(self, client, mock_auth):
        """Test getting export status."""
        mock_export = {
            "export_id": "export1",
            "evaluation_id": "exec1",
            "format": "json",
            "status": "completed",
            "created_at": datetime.utcnow(),
            "download_url": "/download/export1",
            "file_size": 1024
        }
        
        with patch('evaluation_engine.api.config_endpoints._exports', {"export1": mock_export}):
            response = client.get("/config/exports/export1/status")
            
            assert response.status_code == 200
            data = response.json()
            assert data["export_id"] == "export1"
            assert data["status"] == "completed"
            assert data["download_url"] == "/download/export1"


class TestErrorHandling:
    """Test error handling in configuration API."""
    
    def test_upload_empty_content(self, client, mock_auth):
        """Test uploading empty configuration content."""
        response = client.post(
            "/config/upload",
            json={
                "config_content": "",
                "format": "yaml"
            }
        )
        
        assert response.status_code == 422  # Validation error
    
    def test_validate_empty_content(self, client, mock_auth):
        """Test validating empty configuration content."""
        response = client.post(
            "/config/validate",
            json={
                "config_content": "",
                "format": "yaml"
            }
        )
        
        assert response.status_code == 422  # Validation error
    
    def test_execute_without_config(self, client, mock_auth):
        """Test executing without providing configuration."""
        response = client.post(
            "/config/execute",
            json={}
        )
        
        assert response.status_code == 422  # Validation error
    
    def test_execute_with_both_config_sources(self, client, mock_auth):
        """Test executing with both config_id and config_content."""
        response = client.post(
            "/config/execute",
            json={
                "config_id": "config1",
                "config_content": "test content",
                "format": "yaml"
            }
        )
        
        assert response.status_code == 422  # Validation error


if __name__ == "__main__":
    pytest.main([__file__])