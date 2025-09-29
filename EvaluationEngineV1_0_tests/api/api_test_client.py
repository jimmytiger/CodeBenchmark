"""
API test client for programmatic testing of EvaluationEngineV1_0 API.
"""

import requests
import logging
import time
import json
from typing import Dict, List, Optional, Any, Tuple
from datetime import datetime

try:
    from ..models.test_models import TestConfiguration, APITestConfig
    from ..core.real_execution_validator import RealExecutionValidator
    from ..core.error_handler import APIError, ExecutionError
except ImportError:
    # Fallback for direct execution
    import sys
    from pathlib import Path
    sys.path.insert(0, str(Path(__file__).parent.parent))
    
    from models.test_models import TestConfiguration, APITestConfig
    from core.real_execution_validator import RealExecutionValidator
    from core.error_handler import APIError, ExecutionError


class APITestClient:
    """Client for testing EvaluationEngineV1_0 API programmatically."""
    
    def __init__(self, base_url: str = "http://localhost:8000", 
                 timeout: int = 30):
        self.base_url = base_url.rstrip('/')
        self.timeout = timeout
        self.logger = logging.getLogger(f"{__name__}.APITestClient")
        self.real_execution_validator = RealExecutionValidator()
        
        # Session for connection reuse
        self.session = requests.Session()
        self.session.headers.update({
            'Content-Type': 'application/json',
            'Accept': 'application/json',
            'User-Agent': 'EvaluationEngineV1_0-TestClient/1.0'
        })
    
    def run_test(self, test_config: TestConfiguration) -> Dict[str, Any]:
        """Run API test based on configuration."""
        self.logger.info(f"Running API test: {test_config.name}")
        
        result = {
            "success": False,
            "metrics": {},
            "artifacts": [],
            "logs": [],
            "error": None,
            "execution_time": 0.0,
            "api_calls": [],
            "evaluation_id": None
        }
        
        start_time = time.time()
        
        try:
            # Start real execution validation
            self.real_execution_validator.start_tracking()
            
            # Run API test sequence
            if test_config.task_selection.get("type") == "full_workflow":
                self._run_full_workflow_test(test_config, result)
            elif test_config.task_selection.get("type") == "endpoint_specific":
                self._run_endpoint_specific_test(test_config, result)
            else:
                self._run_basic_api_test(test_config, result)
            
            # Validate real execution
            if test_config.real_execution_required:
                from ..models.test_models import TestResult, TestStatus
                test_result = TestResult(
                    test_id=test_config.test_id,
                    test_type=test_config.test_type,
                    name=test_config.name,
                    status=TestStatus.RUNNING,
                    execution_time=result["execution_time"],
                    real_execution_validated=False,
                    logs=result["logs"]
                )
                
                real_execution_valid = self.real_execution_validator.validate_real_execution(
                    test_result, test_config
                )
                result["real_execution_validated"] = real_execution_valid
                
                if not real_execution_valid:
                    result["logs"].append("WARNING: Real execution validation failed")
            
            result["success"] = True
            result["logs"].append("API test completed successfully")
            
        except Exception as e:
            result["error"] = str(e)
            result["logs"].append(f"API test failed: {e}")
            self.logger.error(f"API test failed: {e}")
        
        finally:
            result["execution_time"] = time.time() - start_time
            self.real_execution_validator.stop_tracking()
        
        return result
    
    def test_health_check(self) -> Tuple[bool, Dict[str, Any]]:
        """Test health check endpoint."""
        try:
            response = self.session.get(f"{self.base_url}/health", timeout=self.timeout)
            
            # Record API call
            self.real_execution_validator.record_api_call(
                "/health", "GET", response.json() if response.content else None
            )
            
            success = response.status_code == 200
            result = {
                "status_code": response.status_code,
                "response_time": response.elapsed.total_seconds(),
                "response_data": response.json() if response.content else None
            }
            
            return success, result
            
        except Exception as e:
            return False, {"error": str(e)}
    
    def test_create_evaluation(self, model_id: str, tasks: List[str], 
                             config: Optional[Dict[str, Any]] = None) -> Tuple[bool, Dict[str, Any]]:
        """Test evaluation creation endpoint."""
        try:
            data = {
                "model_id": model_id,
                "tasks": tasks,
                "config": config or {}
            }
            
            response = self.session.post(
                f"{self.base_url}/api/v1/evaluations",
                json=data,
                timeout=self.timeout
            )
            
            # Record API call
            self.real_execution_validator.record_api_call(
                "/api/v1/evaluations", "POST", response.json() if response.content else None
            )
            
            success = response.status_code == 201
            result = {
                "status_code": response.status_code,
                "response_time": response.elapsed.total_seconds(),
                "response_data": response.json() if response.content else None
            }
            
            return success, result
            
        except Exception as e:
            return False, {"error": str(e)}
    
    def test_get_evaluation_status(self, evaluation_id: str) -> Tuple[bool, Dict[str, Any]]:
        """Test evaluation status endpoint."""
        try:
            response = self.session.get(
                f"{self.base_url}/api/v1/evaluations/{evaluation_id}/status",
                timeout=self.timeout
            )
            
            # Record API call
            self.real_execution_validator.record_api_call(
                f"/api/v1/evaluations/{evaluation_id}/status", "GET", 
                response.json() if response.content else None
            )
            
            success = response.status_code == 200
            result = {
                "status_code": response.status_code,
                "response_time": response.elapsed.total_seconds(),
                "response_data": response.json() if response.content else None
            }
            
            return success, result
            
        except Exception as e:
            return False, {"error": str(e)}
    
    def test_get_evaluation_results(self, evaluation_id: str) -> Tuple[bool, Dict[str, Any]]:
        """Test evaluation results endpoint."""
        try:
            response = self.session.get(
                f"{self.base_url}/api/v1/evaluations/{evaluation_id}/results",
                timeout=self.timeout
            )
            
            # Record API call
            self.real_execution_validator.record_api_call(
                f"/api/v1/evaluations/{evaluation_id}/results", "GET",
                response.json() if response.content else None
            )
            
            success = response.status_code == 200
            result = {
                "status_code": response.status_code,
                "response_time": response.elapsed.total_seconds(),
                "response_data": response.json() if response.content else None
            }
            
            return success, result
            
        except Exception as e:
            return False, {"error": str(e)}
    
    def test_list_evaluations(self) -> Tuple[bool, Dict[str, Any]]:
        """Test list evaluations endpoint."""
        try:
            response = self.session.get(
                f"{self.base_url}/api/v1/evaluations",
                timeout=self.timeout
            )
            
            # Record API call
            self.real_execution_validator.record_api_call(
                "/api/v1/evaluations", "GET", response.json() if response.content else None
            )
            
            success = response.status_code == 200
            result = {
                "status_code": response.status_code,
                "response_time": response.elapsed.total_seconds(),
                "response_data": response.json() if response.content else None
            }
            
            return success, result
            
        except Exception as e:
            return False, {"error": str(e)}
    
    def test_list_tasks(self) -> Tuple[bool, Dict[str, Any]]:
        """Test list tasks endpoint."""
        try:
            response = self.session.get(
                f"{self.base_url}/api/v1/tasks",
                timeout=self.timeout
            )
            
            # Record API call
            self.real_execution_validator.record_api_call(
                "/api/v1/tasks", "GET", response.json() if response.content else None
            )
            
            success = response.status_code == 200
            result = {
                "status_code": response.status_code,
                "response_time": response.elapsed.total_seconds(),
                "response_data": response.json() if response.content else None
            }
            
            return success, result
            
        except Exception as e:
            return False, {"error": str(e)}
    
    def test_list_adapters(self) -> Tuple[bool, Dict[str, Any]]:
        """Test list adapters endpoint."""
        try:
            response = self.session.get(
                f"{self.base_url}/api/v1/adapters",
                timeout=self.timeout
            )
            
            # Record API call
            self.real_execution_validator.record_api_call(
                "/api/v1/adapters", "GET", response.json() if response.content else None
            )
            
            success = response.status_code == 200
            result = {
                "status_code": response.status_code,
                "response_time": response.elapsed.total_seconds(),
                "response_data": response.json() if response.content else None
            }
            
            return success, result
            
        except Exception as e:
            return False, {"error": str(e)}
    
    def wait_for_evaluation_completion(self, evaluation_id: str, 
                                     max_wait_time: int = 300,
                                     poll_interval: int = 5) -> Tuple[bool, Dict[str, Any]]:
        """Wait for evaluation to complete."""
        start_time = time.time()
        
        while time.time() - start_time < max_wait_time:
            success, result = self.test_get_evaluation_status(evaluation_id)
            
            if not success:
                return False, result
            
            status = result.get("response_data", {}).get("status")
            
            if status in ["completed", "failed", "cancelled"]:
                return True, result
            
            time.sleep(poll_interval)
        
        return False, {"error": "Evaluation did not complete within timeout"}
    
    def run_full_evaluation_workflow(self, model_id: str, tasks: List[str],
                                   config: Optional[Dict[str, Any]] = None) -> Dict[str, Any]:
        """Run complete evaluation workflow."""
        workflow_result = {
            "success": False,
            "steps": {},
            "evaluation_id": None,
            "final_results": None,
            "total_time": 0.0,
            "error": None
        }
        
        start_time = time.time()
        
        try:
            # Step 1: Health check
            success, result = self.test_health_check()
            workflow_result["steps"]["health_check"] = {"success": success, "result": result}
            
            if not success:
                raise APIError("Health check failed")
            
            # Step 2: List tasks
            success, result = self.test_list_tasks()
            workflow_result["steps"]["list_tasks"] = {"success": success, "result": result}
            
            # Step 3: Create evaluation
            success, result = self.test_create_evaluation(model_id, tasks, config)
            workflow_result["steps"]["create_evaluation"] = {"success": success, "result": result}
            
            if not success:
                raise APIError("Failed to create evaluation")
            
            evaluation_id = result.get("response_data", {}).get("evaluation_id")
            if not evaluation_id:
                raise APIError("No evaluation ID returned")
            
            workflow_result["evaluation_id"] = evaluation_id
            
            # Step 4: Wait for completion
            success, result = self.wait_for_evaluation_completion(evaluation_id)
            workflow_result["steps"]["wait_completion"] = {"success": success, "result": result}
            
            if not success:
                raise APIError("Evaluation did not complete successfully")
            
            # Step 5: Get results
            success, result = self.test_get_evaluation_results(evaluation_id)
            workflow_result["steps"]["get_results"] = {"success": success, "result": result}
            
            if success:
                workflow_result["final_results"] = result.get("response_data")
            
            workflow_result["success"] = True
            
        except Exception as e:
            workflow_result["error"] = str(e)
        
        finally:
            workflow_result["total_time"] = time.time() - start_time
        
        return workflow_result
    
    def _run_full_workflow_test(self, test_config: TestConfiguration, result: Dict[str, Any]) -> None:
        """Run full workflow API test."""
        task_selection = test_config.task_selection
        model_id = task_selection.get("model_id", "test_model")
        tasks = task_selection.get("tasks", ["hellaswag"])
        config = task_selection.get("config", {})
        
        workflow_result = self.run_full_evaluation_workflow(model_id, tasks, config)
        
        result["metrics"]["workflow_success"] = 1.0 if workflow_result["success"] else 0.0
        result["metrics"]["total_api_calls"] = len(workflow_result["steps"])
        result["metrics"]["workflow_time"] = workflow_result["total_time"]
        
        if workflow_result["evaluation_id"]:
            result["evaluation_id"] = workflow_result["evaluation_id"]
        
        result["logs"].append(f"Workflow completed: {workflow_result['success']}")
        
        if not workflow_result["success"]:
            raise APIError(workflow_result.get("error", "Workflow failed"))
    
    def _run_endpoint_specific_test(self, test_config: TestConfiguration, result: Dict[str, Any]) -> None:
        """Run endpoint-specific API test."""
        endpoint = test_config.task_selection.get("endpoint")
        
        if endpoint == "/health":
            success, test_result = self.test_health_check()
        elif endpoint == "/api/v1/tasks":
            success, test_result = self.test_list_tasks()
        elif endpoint == "/api/v1/adapters":
            success, test_result = self.test_list_adapters()
        elif endpoint == "/api/v1/evaluations":
            success, test_result = self.test_list_evaluations()
        else:
            raise APIError(f"Unknown endpoint: {endpoint}")
        
        result["metrics"]["endpoint_success"] = 1.0 if success else 0.0
        result["metrics"]["response_time"] = test_result.get("response_time", 0.0)
        result["metrics"]["status_code"] = test_result.get("status_code", 0)
        
        result["logs"].append(f"Endpoint {endpoint} test: {'success' if success else 'failed'}")
        
        if not success:
            raise APIError(f"Endpoint test failed: {test_result.get('error', 'Unknown error')}")
    
    def _run_basic_api_test(self, test_config: TestConfiguration, result: Dict[str, Any]) -> None:
        """Run basic API test."""
        # Test basic endpoints
        endpoints_tested = 0
        endpoints_successful = 0
        total_response_time = 0.0
        
        # Health check
        success, test_result = self.test_health_check()
        endpoints_tested += 1
        if success:
            endpoints_successful += 1
        total_response_time += test_result.get("response_time", 0.0)
        result["logs"].append(f"Health check: {'success' if success else 'failed'}")
        
        # List tasks
        success, test_result = self.test_list_tasks()
        endpoints_tested += 1
        if success:
            endpoints_successful += 1
        total_response_time += test_result.get("response_time", 0.0)
        result["logs"].append(f"List tasks: {'success' if success else 'failed'}")
        
        # List adapters
        success, test_result = self.test_list_adapters()
        endpoints_tested += 1
        if success:
            endpoints_successful += 1
        total_response_time += test_result.get("response_time", 0.0)
        result["logs"].append(f"List adapters: {'success' if success else 'failed'}")
        
        # Calculate metrics
        result["metrics"]["endpoints_tested"] = endpoints_tested
        result["metrics"]["endpoints_successful"] = endpoints_successful
        result["metrics"]["success_rate"] = endpoints_successful / endpoints_tested if endpoints_tested > 0 else 0.0
        result["metrics"]["average_response_time"] = total_response_time / endpoints_tested if endpoints_tested > 0 else 0.0
        
        if endpoints_successful < endpoints_tested:
            raise APIError(f"Some endpoints failed: {endpoints_successful}/{endpoints_tested} successful")
    
    def close(self) -> None:
        """Close the API client session."""
        self.session.close()


def create_api_test_client(base_url: str = "http://localhost:8000", 
                          timeout: int = 30) -> APITestClient:
    """Factory function to create an API test client."""
    return APITestClient(base_url=base_url, timeout=timeout)