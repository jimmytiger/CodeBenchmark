"""
Integration tests for configuration API with the existing evaluation system.

Tests the complete flow from configuration upload to execution and results.
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
from evaluation_engine.config.evaluator import ConfigDrivenEvaluator
from evaluation_engine.config.models import EvaluationConfig, ConfigMetadata


@pytest.fixture
def app():
    """Create test FastAPI app."""
    app = FastAPI()
    app.include_router(router)
    return app


@pytest.fixture
def client(app):
    """Create test client."""
    return TestClient(app)


@pytest.fixture
def mock_auth():
    """Mock authentication."""
    with patch('evaluation_engine.api.config_endpoints.permission_checker') as mock_checker:
        mock_checker.require_permission.return_value = lambda: {"user_id": "test_user"}
        yield mock_checker


@pytest.fixture
def complete_config_yaml():
    """Complete valid YAML configuration for integration testing."""
    return """
metadata:
  name: "Integration Test Configuration"
  version: "1.0"
  author: "Integration Test"
  description: "Complete configuration for integration testing"

variables:
  output_dir: "./integration_test_results"
  default_batch_size: 8
  model_temperature: 0.7

models:
  gpt35_turbo:
    name: "gpt35_turbo"
    type: "openai"
    model_name: "gpt-3.5-turbo"
    parameters:
      temperature: "${model_temperature}"
      max_tokens: 1000
      top_p: 1.0
    system_prompt: "You are a helpful assistant for evaluation tasks."
    prompt_template: "Question: {question}\\nAnswer:"

  claude_sonnet:
    name: "claude_sonnet"
    type: "anthropic"
    model_name: "claude-3-sonnet-20240229"
    parameters:
      temperature: 0.5
      max_tokens: 1500
    system_prompt: "You are Claude, an AI assistant created by Anthropic."
    prompt_template: "Human: {question}\\n\\nAssistant:"

defaults:
  num_fewshot: 5
  batch_size: "${default_batch_size}"
  output:
    format: ["json", "csv"]
    save_predictions: true

tasks:
  - name: "hellaswag_gpt35"
    description: "HellaSwag commonsense reasoning with GPT-3.5"
    model_ref: "gpt35_turbo"
    task_name: "hellaswag"
    num_fewshot: 10
    batch_size: 4
    task_config:
      limit: 100
    depends_on: []

  - name: "arc_easy_claude"
    description: "ARC Easy reasoning with Claude"
    model_ref: "claude_sonnet"
    task_name: "arc_easy"
    num_fewshot: 25
    batch_size: 2
    task_config:
      limit: 50
    depends_on: []

  - name: "comparison_task"
    description: "Comparison task that depends on previous tasks"
    model_ref: "gpt35_turbo"
    task_name: "truthfulqa_mc"
    num_fewshot: 0
    task_config:
      limit: 25
    depends_on: ["hellaswag_gpt35", "arc_easy_claude"]

output:
  directory: "${output_dir}"
  formats: ["json", "html", "csv"]
  include_raw_responses: true
  generate_report: true
  compare_models: true
"""


class TestConfigurationAPIIntegration:
    """Integration tests for configuration API."""
    
    def test_complete_workflow_dry_run(self, client, mock_auth, complete_config_yaml):
        """Test complete workflow from upload to execution (dry run)."""
        with patch('evaluation_engine.api.config_endpoints.ConfigParser') as mock_parser, \
             patch('evaluation_engine.api.config_endpoints.ConfigValidator') as mock_validator, \
             patch('evaluation_engine.api.config_endpoints._config_evaluator') as mock_evaluator:
            
            # Mock parser
            mock_config = Mock()
            mock_config.metadata = ConfigMetadata(
                name="Integration Test Configuration",
                version="1.0",
                author="Integration Test"
            )
            mock_config.tasks = [Mock(), Mock(), Mock()]  # 3 tasks
            mock_config.models = {"gpt35_turbo": Mock(), "claude_sonnet": Mock()}
            
            mock_parser.return_value.parse_config.return_value = mock_config
            
            # Mock validator
            mock_validation = Mock()
            mock_validation.is_valid = True
            mock_validation.errors = []
            mock_validation.warnings = []
            mock_validator.return_value.validate_config.return_value = mock_validation
            
            # Mock evaluator result
            mock_result = Mock()
            mock_result.end_time = datetime.utcnow()
            mock_result.total_execution_time = 30.0
            mock_result.to_dict.return_value = {
                "config_metadata": {"name": "Integration Test Configuration"},
                "total_execution_time": 30.0,
                "completed_tasks": 0,
                "failed_tasks": 0,
                "skipped_tasks": 3,
                "success_rate": 100.0,
                "task_results": {},
                "task_summaries": {},
                "execution_order": ["hellaswag_gpt35", "arc_easy_claude", "comparison_task"]
            }
            mock_evaluator.run_from_config.return_value = mock_result
            
            # Step 1: Upload configuration
            upload_response = client.post(
                "/config/upload",
                json={
                    "config_content": complete_config_yaml,
                    "format": "yaml",
                    "name": "Integration Test Config",
                    "description": "Configuration for integration testing"
                }
            )
            
            assert upload_response.status_code == 200
            upload_data = upload_response.json()
            config_id = upload_data["config_id"]
            assert upload_data["validation"]["is_valid"] is True
            assert upload_data["validation"]["task_count"] == 3
            assert upload_data["validation"]["model_count"] == 2
            
            # Step 2: Get configuration details
            details_response = client.get(f"/config/{config_id}")
            assert details_response.status_code == 200
            details_data = details_response.json()
            assert details_data["name"] == "Integration Test Config"
            assert len(details_data["tasks"]) == 3
            assert len(details_data["models"]) == 2
            
            # Step 3: Execute configuration (dry run)
            execute_response = client.post(
                "/config/execute",
                json={
                    "config_id": config_id,
                    "dry_run": True,
                    "task_filter": ["hellaswag_gpt35", "arc_easy_claude"],
                    "parameter_overrides": {
                        "variables": {
                            "model_temperature": 0.5
                        }
                    }
                }
            )
            
            assert execute_response.status_code == 200
            execute_data = execute_response.json()
            evaluation_id = execute_data["evaluation_id"]
            assert execute_data["config_id"] == config_id
            assert execute_data["dry_run"] is True
            assert execute_data["task_count"] == 3
            
            # Step 4: Check execution status (simulate completion)
            # First, simulate the background task completion
            import evaluation_engine.api.config_endpoints as endpoints_module
            endpoints_module._executions[evaluation_id]["status"] = "completed"
            endpoints_module._executions[evaluation_id]["end_time"] = datetime.utcnow()
            endpoints_module._executions[evaluation_id]["result_data"] = mock_result.to_dict()
            
            status_response = client.get(f"/config/executions/{evaluation_id}")
            assert status_response.status_code == 200
            status_data = status_response.json()
            assert status_data["evaluation_id"] == evaluation_id
            assert status_data["dry_run"] is True
            
            # Step 5: Get execution results
            results_response = client.get(f"/config/executions/{evaluation_id}/results")
            assert results_response.status_code == 200
            results_data = results_response.json()
            assert results_data["evaluation_id"] == evaluation_id
            assert results_data["success_rate"] == 100.0
            assert results_data["skipped_tasks"] == 3  # Dry run skips all tasks
    
    def test_inline_configuration_execution(self, client, mock_auth, complete_config_yaml):
        """Test executing inline configuration without uploading."""
        with patch('evaluation_engine.api.config_endpoints.ConfigParser') as mock_parser, \
             patch('evaluation_engine.api.config_endpoints._config_evaluator') as mock_evaluator:
            
            # Mock parser
            mock_config = Mock()
            mock_config.metadata = Mock()
            mock_config.metadata.name = "Inline Config"
            mock_config.tasks = [Mock()]
            
            mock_parser.return_value.parse_config.return_value = mock_config
            
            # Mock evaluator result
            mock_result = Mock()
            mock_result.end_time = datetime.utcnow()
            mock_result.total_execution_time = 15.0
            mock_result.to_dict.return_value = {
                "config_metadata": {"name": "Inline Config"},
                "total_execution_time": 15.0,
                "completed_tasks": 0,
                "failed_tasks": 0,
                "skipped_tasks": 1,
                "success_rate": 100.0
            }
            mock_evaluator.run_from_config.return_value = mock_result
            
            # Execute inline configuration
            response = client.post(
                "/config/execute",
                json={
                    "config_content": complete_config_yaml,
                    "format": "yaml",
                    "dry_run": True,
                    "fail_fast": True
                }
            )
            
            assert response.status_code == 200
            data = response.json()
            assert data["config_id"] is None  # No uploaded config
            assert data["dry_run"] is True
    
    def test_configuration_validation_workflow(self, client, mock_auth):
        """Test configuration validation workflow."""
        invalid_config = """
metadata:
  name: "Invalid Config"

# Missing required sections
tasks: []
models: {}
"""
        
        with patch('evaluation_engine.api.config_endpoints.ConfigParser') as mock_parser, \
             patch('evaluation_engine.api.config_endpoints.ConfigValidator') as mock_validator:
            
            # Mock parser
            mock_config = Mock()
            mock_config.tasks = []
            mock_config.models = {}
            mock_parser.return_value.parse_config.return_value = mock_config
            
            # Mock validator with errors
            mock_error = Mock()
            mock_error.type = "validation"
            mock_error.message = "No tasks defined"
            mock_error.severity.value = "error"
            mock_error.location = "tasks"
            mock_error.suggestion = "Add at least one task"
            
            mock_validation = Mock()
            mock_validation.is_valid = False
            mock_validation.errors = [mock_error]
            mock_validation.warnings = []
            mock_validator.return_value.validate_config.return_value = mock_validation
            
            # Test validation
            response = client.post(
                "/config/validate",
                json={
                    "config_content": invalid_config,
                    "format": "yaml"
                }
            )
            
            assert response.status_code == 200
            data = response.json()
            assert data["is_valid"] is False
            assert data["status"] == "invalid"
            assert len(data["errors"]) == 1
            assert data["errors"][0]["message"] == "No tasks defined"
            assert data["errors"][0]["suggestion"] == "Add at least one task"
    
    def test_execution_with_parameter_overrides(self, client, mock_auth, complete_config_yaml):
        """Test execution with parameter overrides."""
        with patch('evaluation_engine.api.config_endpoints.ConfigParser') as mock_parser, \
             patch('evaluation_engine.api.config_endpoints.ConfigValidator') as mock_validator, \
             patch('evaluation_engine.api.config_endpoints._config_evaluator') as mock_evaluator:
            
            # Mock components
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
            
            # Upload configuration first
            upload_response = client.post(
                "/config/upload",
                json={
                    "config_content": complete_config_yaml,
                    "format": "yaml"
                }
            )
            config_id = upload_response.json()["config_id"]
            
            # Execute with overrides
            response = client.post(
                "/config/execute",
                json={
                    "config_id": config_id,
                    "dry_run": True,
                    "parameter_overrides": {
                        "variables": {
                            "model_temperature": 0.1,
                            "default_batch_size": 16
                        },
                        "defaults": {
                            "num_fewshot": 10
                        },
                        "tasks": {
                            "hellaswag_gpt35": {
                                "batch_size": 2
                            }
                        }
                    },
                    "task_filter": ["hellaswag_gpt35"],
                    "fail_fast": True
                }
            )
            
            assert response.status_code == 200
            data = response.json()
            assert "evaluation_id" in data
            
            # Verify that the evaluator was called with the correct parameters
            mock_evaluator.run_from_config.assert_called_once()
            call_args = mock_evaluator.run_from_config.call_args
            assert call_args[1]["task_filter"] == ["hellaswag_gpt35"]
            assert call_args[1]["fail_fast"] is True
            assert call_args[1]["dry_run"] is True
            assert call_args[1]["parameter_overrides"] is not None
    
    def test_export_workflow(self, client, mock_auth):
        """Test result export workflow."""
        # Mock completed execution
        mock_execution = {
            "evaluation_id": "exec1",
            "config_id": "config1",
            "status": "completed",
            "result_data": {
                "config_metadata": {"name": "Test Config"},
                "task_summaries": {
                    "task1": {"status": "completed", "execution_time": 30.5}
                },
                "success_rate": 100.0
            }
        }
        
        with patch('evaluation_engine.api.config_endpoints._executions', {"exec1": mock_execution}), \
             patch('evaluation_engine.api.config_endpoints._exports', {}):
            
            # Start export
            export_response = client.post(
                "/config/executions/exec1/export",
                json={
                    "evaluation_id": "exec1",
                    "format": "json",
                    "include_raw_results": True,
                    "include_config": True
                }
            )
            
            assert export_response.status_code == 200
            export_data = export_response.json()
            export_id = export_data["export_id"]
            assert export_data["evaluation_id"] == "exec1"
            assert export_data["format"] == "json"
            assert export_data["status"] == "processing"
            
            # Check export status
            import evaluation_engine.api.config_endpoints as endpoints_module
            endpoints_module._exports[export_id]["status"] = "completed"
            endpoints_module._exports[export_id]["download_url"] = f"/download/{export_id}"
            endpoints_module._exports[export_id]["file_size"] = 2048
            
            status_response = client.get(f"/config/exports/{export_id}/status")
            assert status_response.status_code == 200
            status_data = status_response.json()
            assert status_data["status"] == "completed"
            assert status_data["download_url"] is not None
    
    def test_error_handling_integration(self, client, mock_auth):
        """Test error handling in integration scenarios."""
        # Test uploading configuration that fails parsing
        with patch('evaluation_engine.api.config_endpoints.ConfigParser') as mock_parser:
            mock_parser.return_value.parse_config.side_effect = Exception("YAML parsing error")
            
            response = client.post(
                "/config/upload",
                json={
                    "config_content": "invalid: yaml: content:",
                    "format": "yaml"
                }
            )
            
            assert response.status_code == 400
            assert "Configuration upload failed" in response.json()["detail"]
        
        # Test executing non-existent configuration
        response = client.post(
            "/config/execute",
            json={"config_id": "non-existent-config"}
        )
        
        assert response.status_code == 404
        assert "Configuration not found" in response.json()["detail"]
        
        # Test getting results for non-existent execution
        response = client.get("/config/executions/non-existent-exec/results")
        
        assert response.status_code == 404
        assert "Execution not found" in response.json()["detail"]


if __name__ == "__main__":
    pytest.main([__file__])