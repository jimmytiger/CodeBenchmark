"""
Configuration API Usage Examples

This module demonstrates how to use the configuration-driven evaluation API
endpoints for uploading, validating, executing, and managing configurations.
"""

import requests
import json
import time
import yaml
from typing import Dict, Any, Optional


class ConfigurationAPIClient:
    """
    Client for interacting with the configuration-driven evaluation API.
    
    Provides convenient methods for all configuration API operations.
    """
    
    def __init__(self, base_url: str = "http://localhost:8000", api_token: Optional[str] = None):
        """
        Initialize API client.
        
        Args:
            base_url: Base URL of the API server
            api_token: Authentication token (if required)
        """
        self.base_url = base_url.rstrip('/')
        self.api_base = f"{self.base_url}/api/v1/config"
        self.headers = {"Content-Type": "application/json"}
        
        if api_token:
            self.headers["Authorization"] = f"Bearer {api_token}"
    
    def upload_configuration(self, config_content: str, format_type: str, 
                           name: Optional[str] = None, description: Optional[str] = None) -> Dict[str, Any]:
        """
        Upload a configuration file.
        
        Args:
            config_content: Configuration file content
            format_type: Configuration format ('yaml' or 'json')
            name: Optional configuration name
            description: Optional configuration description
            
        Returns:
            Upload response with config_id and validation results
        """
        payload = {
            "config_content": config_content,
            "format": format_type
        }
        
        if name:
            payload["name"] = name
        if description:
            payload["description"] = description
        
        response = requests.post(f"{self.api_base}/upload", json=payload, headers=self.headers)
        response.raise_for_status()
        return response.json()
    
    def upload_configuration_file(self, file_path: str, name: Optional[str] = None, 
                                description: Optional[str] = None) -> Dict[str, Any]:
        """
        Upload a configuration file from disk.
        
        Args:
            file_path: Path to configuration file
            name: Optional configuration name
            description: Optional configuration description
            
        Returns:
            Upload response with config_id and validation results
        """
        with open(file_path, 'rb') as f:
            files = {"file": f}
            data = {}
            if name:
                data["name"] = name
            if description:
                data["description"] = description
            
            # Remove Content-Type header for file upload
            headers = {k: v for k, v in self.headers.items() if k != "Content-Type"}
            
            response = requests.post(f"{self.api_base}/upload-file", files=files, data=data, headers=headers)
            response.raise_for_status()
            return response.json()
    
    def validate_configuration(self, config_content: str, format_type: str) -> Dict[str, Any]:
        """
        Validate a configuration without uploading.
        
        Args:
            config_content: Configuration content to validate
            format_type: Configuration format ('yaml' or 'json')
            
        Returns:
            Validation results
        """
        payload = {
            "config_content": config_content,
            "format": format_type
        }
        
        response = requests.post(f"{self.api_base}/validate", json=payload, headers=self.headers)
        response.raise_for_status()
        return response.json()
    
    def list_configurations(self, page: int = 1, page_size: int = 20) -> Dict[str, Any]:
        """
        List uploaded configurations.
        
        Args:
            page: Page number
            page_size: Items per page
            
        Returns:
            List of configurations with pagination info
        """
        params = {"page": page, "page_size": page_size}
        response = requests.get(f"{self.api_base}/", params=params, headers=self.headers)
        response.raise_for_status()
        return response.json()
    
    def get_configuration(self, config_id: str) -> Dict[str, Any]:
        """
        Get configuration details.
        
        Args:
            config_id: Configuration ID
            
        Returns:
            Detailed configuration information
        """
        response = requests.get(f"{self.api_base}/{config_id}", headers=self.headers)
        response.raise_for_status()
        return response.json()
    
    def execute_configuration(self, config_id: Optional[str] = None, 
                            config_content: Optional[str] = None,
                            format_type: Optional[str] = None,
                            task_filter: Optional[list] = None,
                            parameter_overrides: Optional[Dict[str, Any]] = None,
                            fail_fast: bool = False,
                            dry_run: bool = False) -> Dict[str, Any]:
        """
        Execute a configuration.
        
        Args:
            config_id: ID of uploaded configuration (alternative to config_content)
            config_content: Inline configuration content (alternative to config_id)
            format_type: Format of inline configuration (required if using config_content)
            task_filter: List of specific tasks to execute
            parameter_overrides: Parameter overrides
            fail_fast: Stop on first task failure
            dry_run: Validate and build but don't execute
            
        Returns:
            Execution response with evaluation_id
        """
        payload = {
            "fail_fast": fail_fast,
            "dry_run": dry_run
        }
        
        if config_id:
            payload["config_id"] = config_id
        elif config_content:
            payload["config_content"] = config_content
            payload["format"] = format_type
        else:
            raise ValueError("Either config_id or config_content must be provided")
        
        if task_filter:
            payload["task_filter"] = task_filter
        if parameter_overrides:
            payload["parameter_overrides"] = parameter_overrides
        
        response = requests.post(f"{self.api_base}/execute", json=payload, headers=self.headers)
        response.raise_for_status()
        return response.json()
    
    def get_execution_status(self, evaluation_id: str) -> Dict[str, Any]:
        """
        Get execution status.
        
        Args:
            evaluation_id: Evaluation ID
            
        Returns:
            Execution status and progress information
        """
        response = requests.get(f"{self.api_base}/executions/{evaluation_id}", headers=self.headers)
        response.raise_for_status()
        return response.json()
    
    def get_execution_results(self, evaluation_id: str) -> Dict[str, Any]:
        """
        Get execution results.
        
        Args:
            evaluation_id: Evaluation ID
            
        Returns:
            Complete execution results
        """
        response = requests.get(f"{self.api_base}/executions/{evaluation_id}/results", headers=self.headers)
        response.raise_for_status()
        return response.json()
    
    def wait_for_completion(self, evaluation_id: str, timeout: int = 3600, poll_interval: int = 5) -> Dict[str, Any]:
        """
        Wait for execution to complete.
        
        Args:
            evaluation_id: Evaluation ID
            timeout: Maximum wait time in seconds
            poll_interval: Polling interval in seconds
            
        Returns:
            Final execution status
        """
        start_time = time.time()
        
        while time.time() - start_time < timeout:
            status = self.get_execution_status(evaluation_id)
            
            if status["status"] in ["completed", "failed", "cancelled"]:
                return status
            
            print(f"Execution {evaluation_id}: {status['status']} - Progress: {status['progress']:.1%}")
            time.sleep(poll_interval)
        
        raise TimeoutError(f"Execution {evaluation_id} did not complete within {timeout} seconds")
    
    def export_results(self, evaluation_id: str, format_type: str = "json", 
                      include_raw_results: bool = False, include_config: bool = True) -> Dict[str, Any]:
        """
        Export execution results.
        
        Args:
            evaluation_id: Evaluation ID
            format_type: Export format ('json', 'csv', 'xlsx', 'pdf')
            include_raw_results: Include raw evaluation results
            include_config: Include configuration in export
            
        Returns:
            Export response with export_id
        """
        payload = {
            "evaluation_id": evaluation_id,
            "format": format_type,
            "include_raw_results": include_raw_results,
            "include_config": include_config
        }
        
        response = requests.post(f"{self.api_base}/executions/{evaluation_id}/export", 
                               json=payload, headers=self.headers)
        response.raise_for_status()
        return response.json()
    
    def download_export(self, export_id: str, output_path: str):
        """
        Download exported results.
        
        Args:
            export_id: Export ID
            output_path: Local path to save the file
        """
        response = requests.get(f"{self.api_base}/exports/{export_id}/download", headers=self.headers)
        response.raise_for_status()
        
        with open(output_path, 'wb') as f:
            f.write(response.content)


def example_basic_workflow():
    """
    Example: Basic configuration workflow.
    
    Demonstrates uploading, validating, and executing a simple configuration.
    """
    print("=== Basic Configuration Workflow ===")
    
    # Initialize client
    client = ConfigurationAPIClient()
    
    # Sample configuration
    config_yaml = """
metadata:
  name: "Basic Example Configuration"
  version: "1.0"
  author: "API Example"
  description: "Simple configuration for demonstration"

variables:
  output_dir: "./example_results"
  temperature: 0.7

models:
  gpt35:
    name: "gpt35"
    type: "openai"
    model_name: "gpt-3.5-turbo"
    parameters:
      temperature: "${temperature}"
      max_tokens: 1000

defaults:
  num_fewshot: 5
  batch_size: 8

tasks:
  - name: "hellaswag_example"
    description: "HellaSwag example task"
    model_ref: "gpt35"
    task_name: "hellaswag"
    num_fewshot: 10
    task_config:
      limit: 50
    depends_on: []

output:
  directory: "${output_dir}"
  formats: ["json"]
"""
    
    try:
        # Step 1: Validate configuration
        print("1. Validating configuration...")
        validation = client.validate_configuration(config_yaml, "yaml")
        print(f"   Validation result: {'✓ Valid' if validation['is_valid'] else '✗ Invalid'}")
        
        if not validation['is_valid']:
            print("   Errors:")
            for error in validation['errors']:
                print(f"     - {error['message']}")
            return
        
        # Step 2: Upload configuration
        print("2. Uploading configuration...")
        upload_result = client.upload_configuration(
            config_yaml, 
            "yaml", 
            name="Basic Example",
            description="Configuration for basic workflow example"
        )
        config_id = upload_result['config_id']
        print(f"   Uploaded with ID: {config_id}")
        
        # Step 3: Execute configuration (dry run)
        print("3. Executing configuration (dry run)...")
        execution = client.execute_configuration(
            config_id=config_id,
            dry_run=True,
            parameter_overrides={
                "variables": {"temperature": 0.5}
            }
        )
        evaluation_id = execution['evaluation_id']
        print(f"   Started execution: {evaluation_id}")
        
        # Step 4: Wait for completion
        print("4. Waiting for completion...")
        final_status = client.wait_for_completion(evaluation_id, timeout=300)
        print(f"   Final status: {final_status['status']}")
        
        # Step 5: Get results
        if final_status['status'] == 'completed':
            print("5. Getting results...")
            results = client.get_execution_results(evaluation_id)
            print(f"   Success rate: {results['success_rate']:.1f}%")
            print(f"   Total tasks: {results['total_tasks']}")
            print(f"   Execution time: {results['total_execution_time']:.2f}s")
        
    except Exception as e:
        print(f"Error: {e}")


def example_inline_execution():
    """
    Example: Inline configuration execution.
    
    Demonstrates executing configuration without uploading.
    """
    print("\n=== Inline Configuration Execution ===")
    
    client = ConfigurationAPIClient()
    
    # Simple inline configuration
    config_dict = {
        "metadata": {
            "name": "Inline Example",
            "version": "1.0"
        },
        "models": {
            "test_model": {
                "name": "test_model",
                "type": "openai",
                "model_name": "gpt-3.5-turbo",
                "parameters": {"temperature": 0.7}
            }
        },
        "tasks": [
            {
                "name": "quick_test",
                "description": "Quick test task",
                "model_ref": "test_model",
                "task_name": "arc_easy",
                "task_config": {"limit": 10},
                "depends_on": []
            }
        ],
        "output": {
            "directory": "./inline_results",
            "formats": ["json"]
        }
    }
    
    try:
        # Execute inline configuration
        print("1. Executing inline configuration...")
        execution = client.execute_configuration(
            config_content=json.dumps(config_dict),
            format_type="json",
            dry_run=True,
            fail_fast=True
        )
        
        evaluation_id = execution['evaluation_id']
        print(f"   Started execution: {evaluation_id}")
        
        # Monitor execution
        print("2. Monitoring execution...")
        final_status = client.wait_for_completion(evaluation_id, timeout=180)
        print(f"   Final status: {final_status['status']}")
        
    except Exception as e:
        print(f"Error: {e}")


def example_batch_operations():
    """
    Example: Batch operations with multiple configurations.
    
    Demonstrates managing multiple configurations and executions.
    """
    print("\n=== Batch Operations Example ===")
    
    client = ConfigurationAPIClient()
    
    try:
        # List existing configurations
        print("1. Listing existing configurations...")
        configs = client.list_configurations(page=1, page_size=10)
        print(f"   Found {configs['total']} configurations")
        
        for config in configs['configurations'][:3]:  # Show first 3
            print(f"   - {config['name']} (ID: {config['config_id'][:8]}...)")
        
        # If we have configurations, execute the first valid one
        if configs['configurations']:
            valid_configs = [c for c in configs['configurations'] if c['is_valid']]
            
            if valid_configs:
                config = valid_configs[0]
                print(f"\n2. Executing configuration: {config['name']}")
                
                execution = client.execute_configuration(
                    config_id=config['config_id'],
                    dry_run=True,
                    task_filter=None,  # Execute all tasks
                    parameter_overrides={
                        "defaults": {"batch_size": 4}
                    }
                )
                
                print(f"   Started execution: {execution['evaluation_id']}")
                
                # Check status periodically
                for i in range(5):
                    time.sleep(2)
                    status = client.get_execution_status(execution['evaluation_id'])
                    print(f"   Status check {i+1}: {status['status']} ({status['progress']:.1%})")
                    
                    if status['status'] in ['completed', 'failed']:
                        break
        
    except Exception as e:
        print(f"Error: {e}")


def example_export_workflow():
    """
    Example: Export workflow.
    
    Demonstrates exporting results in different formats.
    """
    print("\n=== Export Workflow Example ===")
    
    client = ConfigurationAPIClient()
    
    # This example assumes you have a completed execution
    # In practice, you would get this from a real execution
    example_evaluation_id = "example-evaluation-id"
    
    try:
        # Note: This will fail unless you have a real completed execution
        print("1. Starting export...")
        export_response = client.export_results(
            evaluation_id=example_evaluation_id,
            format_type="json",
            include_raw_results=True,
            include_config=True
        )
        
        export_id = export_response['export_id']
        print(f"   Export started: {export_id}")
        
        # Wait for export completion
        print("2. Waiting for export completion...")
        while True:
            status_response = requests.get(
                f"{client.api_base}/exports/{export_id}/status",
                headers=client.headers
            )
            status = status_response.json()
            
            print(f"   Export status: {status['status']}")
            
            if status['status'] == 'completed':
                print("3. Downloading export...")
                client.download_export(export_id, f"export_{export_id}.json")
                print(f"   Downloaded to: export_{export_id}.json")
                break
            elif status['status'] == 'failed':
                print("   Export failed!")
                break
            
            time.sleep(2)
        
    except requests.exceptions.HTTPError as e:
        if e.response.status_code == 404:
            print("   No completed execution found for export example")
        else:
            print(f"   Error: {e}")
    except Exception as e:
        print(f"Error: {e}")


def example_error_handling():
    """
    Example: Error handling.
    
    Demonstrates proper error handling for common scenarios.
    """
    print("\n=== Error Handling Example ===")
    
    client = ConfigurationAPIClient()
    
    # Example 1: Invalid configuration
    print("1. Testing invalid configuration...")
    invalid_config = "invalid: yaml: content:"
    
    try:
        validation = client.validate_configuration(invalid_config, "yaml")
        print(f"   Unexpected success: {validation}")
    except requests.exceptions.HTTPError as e:
        print(f"   Expected error: {e.response.status_code} - {e.response.json()['detail']}")
    
    # Example 2: Non-existent configuration
    print("2. Testing non-existent configuration...")
    try:
        config = client.get_configuration("non-existent-id")
        print(f"   Unexpected success: {config}")
    except requests.exceptions.HTTPError as e:
        print(f"   Expected error: {e.response.status_code} - {e.response.json()['detail']}")
    
    # Example 3: Invalid execution request
    print("3. Testing invalid execution request...")
    try:
        execution = client.execute_configuration()  # No config provided
        print(f"   Unexpected success: {execution}")
    except (requests.exceptions.HTTPError, ValueError) as e:
        print(f"   Expected error: {e}")


if __name__ == "__main__":
    """
    Run all examples.
    
    Note: These examples assume the API server is running on localhost:8000
    and may require authentication depending on your setup.
    """
    print("Configuration API Examples")
    print("=" * 50)
    
    # Run examples
    example_basic_workflow()
    example_inline_execution()
    example_batch_operations()
    example_export_workflow()
    example_error_handling()
    
    print("\n" + "=" * 50)
    print("Examples completed!")
    print("\nTo use these examples with a real API server:")
    print("1. Start the evaluation engine API server")
    print("2. Update the base_url in ConfigurationAPIClient if needed")
    print("3. Add authentication token if required")
    print("4. Modify configurations to match your available models and tasks")