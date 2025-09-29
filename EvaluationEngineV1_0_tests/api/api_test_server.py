"""
API test server for EvaluationEngineV1_0 testing.
"""

import asyncio
import logging
import threading
import time
import uuid
from typing import Dict, List, Optional, Any
from datetime import datetime
from pathlib import Path
import json

from flask import Flask, request, jsonify, Response
from flask_cors import CORS
import requests

from ..models.test_models import TestConfiguration, TestResult, TestStatus, TestType
from ..core.real_execution_validator import RealExecutionValidator
from ..core.error_handler import APIError, ExecutionError


class APITestServer:
    """Test API server for EvaluationEngineV1_0 testing."""
    
    def __init__(self, host: str = "localhost", port: int = 8000):
        self.host = host
        self.port = port
        self.app = Flask(__name__)
        CORS(self.app)
        
        self.logger = logging.getLogger(f"{__name__}.APITestServer")
        self.real_execution_validator = RealExecutionValidator()
        
        # Server state
        self._server_thread: Optional[threading.Thread] = None
        self._shutdown_event = threading.Event()
        self._running = False
        
        # Evaluation state
        self._evaluations: Dict[str, Dict[str, Any]] = {}
        self._evaluation_results: Dict[str, Dict[str, Any]] = {}
        
        # Register endpoints
        self._register_endpoints()
    
    def start_server(self) -> None:
        """Start the API test server."""
        if self._running:
            self.logger.warning("Server is already running")
            return
        
        self.logger.info(f"Starting API test server on {self.host}:{self.port}")
        
        self._server_thread = threading.Thread(
            target=self._run_server,
            daemon=True
        )
        self._server_thread.start()
        
        # Wait for server to start
        time.sleep(2)
        
        # Verify server is running
        try:
            response = requests.get(f"http://{self.host}:{self.port}/health", timeout=5)
            if response.status_code == 200:
                self._running = True
                self.logger.info("API test server started successfully")
            else:
                raise Exception(f"Server health check failed: {response.status_code}")
        except Exception as e:
            self.logger.error(f"Failed to start API test server: {e}")
            raise APIError(f"Server startup failed: {e}")
    
    def stop_server(self) -> None:
        """Stop the API test server."""
        if not self._running:
            return
        
        self.logger.info("Stopping API test server")
        self._shutdown_event.set()
        self._running = False
        
        if self._server_thread:
            self._server_thread.join(timeout=10)
    
    def is_running(self) -> bool:
        """Check if server is running."""
        return self._running
    
    def get_server_url(self) -> str:
        """Get server URL."""
        return f"http://{self.host}:{self.port}"
    
    def _run_server(self) -> None:
        """Run the Flask server."""
        try:
            self.app.run(
                host=self.host,
                port=self.port,
                debug=False,
                use_reloader=False,
                threaded=True
            )
        except Exception as e:
            self.logger.error(f"Server error: {e}")
    
    def _register_endpoints(self) -> None:
        """Register API endpoints."""
        
        @self.app.route('/health', methods=['GET'])
        def health_check():
            """Health check endpoint."""
            return jsonify({
                "status": "healthy",
                "timestamp": datetime.now().isoformat(),
                "server": "EvaluationEngineV1_0 Test Server",
                "version": "1.0.0"
            })
        
        @self.app.route('/api/v1/evaluations', methods=['POST'])
        def create_evaluation():
            """Create a new evaluation."""
            try:
                data = request.get_json()
                
                # Validate request
                if not data:
                    return jsonify({"error": "No data provided"}), 400
                
                required_fields = ["model_id", "tasks"]
                for field in required_fields:
                    if field not in data:
                        return jsonify({"error": f"Missing required field: {field}"}), 400
                
                # Create evaluation
                evaluation_id = str(uuid.uuid4())
                evaluation = {
                    "evaluation_id": evaluation_id,
                    "model_id": data["model_id"],
                    "tasks": data["tasks"],
                    "status": "created",
                    "created_at": datetime.now().isoformat(),
                    "config": data.get("config", {}),
                    "progress": 0.0
                }
                
                self._evaluations[evaluation_id] = evaluation
                
                # Start evaluation asynchronously
                self._start_evaluation_async(evaluation_id)
                
                # Record API call for validation
                self.real_execution_validator.record_api_call(
                    "/api/v1/evaluations", "POST", evaluation
                )
                
                return jsonify({
                    "evaluation_id": evaluation_id,
                    "status": "created",
                    "message": "Evaluation created successfully",
                    "check_status_url": f"/api/v1/evaluations/{evaluation_id}/status"
                }), 201
                
            except Exception as e:
                self.logger.error(f"Error creating evaluation: {e}")
                return jsonify({"error": str(e)}), 500
        
        @self.app.route('/api/v1/evaluations/<evaluation_id>/status', methods=['GET'])
        def get_evaluation_status(evaluation_id):
            """Get evaluation status."""
            try:
                if evaluation_id not in self._evaluations:
                    return jsonify({"error": "Evaluation not found"}), 404
                
                evaluation = self._evaluations[evaluation_id]
                
                response = {
                    "evaluation_id": evaluation_id,
                    "status": evaluation["status"],
                    "progress": evaluation["progress"],
                    "created_at": evaluation["created_at"],
                    "model_id": evaluation["model_id"],
                    "tasks": evaluation["tasks"]
                }
                
                if "started_at" in evaluation:
                    response["started_at"] = evaluation["started_at"]
                
                if "completed_at" in evaluation:
                    response["completed_at"] = evaluation["completed_at"]
                
                if "error" in evaluation:
                    response["error"] = evaluation["error"]
                
                # Record API call for validation
                self.real_execution_validator.record_api_call(
                    f"/api/v1/evaluations/{evaluation_id}/status", "GET", response
                )
                
                return jsonify(response)
                
            except Exception as e:
                self.logger.error(f"Error getting evaluation status: {e}")
                return jsonify({"error": str(e)}), 500
        
        @self.app.route('/api/v1/evaluations/<evaluation_id>/results', methods=['GET'])
        def get_evaluation_results(evaluation_id):
            """Get evaluation results."""
            try:
                if evaluation_id not in self._evaluations:
                    return jsonify({"error": "Evaluation not found"}), 404
                
                evaluation = self._evaluations[evaluation_id]
                
                if evaluation["status"] != "completed":
                    return jsonify({
                        "error": "Evaluation not completed",
                        "status": evaluation["status"]
                    }), 400
                
                if evaluation_id not in self._evaluation_results:
                    return jsonify({"error": "Results not available"}), 404
                
                results = self._evaluation_results[evaluation_id]
                
                # Record API call for validation
                self.real_execution_validator.record_api_call(
                    f"/api/v1/evaluations/{evaluation_id}/results", "GET", results
                )
                
                return jsonify(results)
                
            except Exception as e:
                self.logger.error(f"Error getting evaluation results: {e}")
                return jsonify({"error": str(e)}), 500
        
        @self.app.route('/api/v1/evaluations', methods=['GET'])
        def list_evaluations():
            """List all evaluations."""
            try:
                evaluations = []
                for eval_id, evaluation in self._evaluations.items():
                    evaluations.append({
                        "evaluation_id": eval_id,
                        "model_id": evaluation["model_id"],
                        "status": evaluation["status"],
                        "progress": evaluation["progress"],
                        "created_at": evaluation["created_at"],
                        "task_count": len(evaluation["tasks"])
                    })
                
                response = {
                    "evaluations": evaluations,
                    "total": len(evaluations)
                }
                
                # Record API call for validation
                self.real_execution_validator.record_api_call(
                    "/api/v1/evaluations", "GET", response
                )
                
                return jsonify(response)
                
            except Exception as e:
                self.logger.error(f"Error listing evaluations: {e}")
                return jsonify({"error": str(e)}), 500
        
        @self.app.route('/api/v1/tasks', methods=['GET'])
        def list_tasks():
            """List available tasks."""
            try:
                # Mock task list
                tasks = [
                    {
                        "task_id": "hellaswag",
                        "name": "HellaSwag",
                        "description": "Commonsense reasoning task",
                        "type": "multiple_choice",
                        "difficulty": "medium"
                    },
                    {
                        "task_id": "arc_easy",
                        "name": "ARC Easy",
                        "description": "Science questions (easy)",
                        "type": "multiple_choice",
                        "difficulty": "easy"
                    },
                    {
                        "task_id": "arc_challenge",
                        "name": "ARC Challenge",
                        "description": "Science questions (challenging)",
                        "type": "multiple_choice",
                        "difficulty": "hard"
                    },
                    {
                        "task_id": "winogrande",
                        "name": "WinoGrande",
                        "description": "Pronoun resolution task",
                        "type": "multiple_choice",
                        "difficulty": "medium"
                    }
                ]
                
                response = {
                    "tasks": tasks,
                    "total": len(tasks)
                }
                
                # Record API call for validation
                self.real_execution_validator.record_api_call(
                    "/api/v1/tasks", "GET", response
                )
                
                return jsonify(response)
                
            except Exception as e:
                self.logger.error(f"Error listing tasks: {e}")
                return jsonify({"error": str(e)}), 500
        
        @self.app.route('/api/v1/adapters', methods=['GET'])
        def list_adapters():
            """List available adapters."""
            try:
                adapters = [
                    {
                        "adapter_id": "lm_eval",
                        "name": "LM-Eval Adapter",
                        "description": "Integration with lm-evaluation-harness",
                        "status": "available",
                        "supported_tasks": ["hellaswag", "arc_easy", "arc_challenge", "winogrande"]
                    },
                    {
                        "adapter_id": "swe_bench",
                        "name": "SWE-bench Adapter",
                        "description": "Software engineering evaluation tasks",
                        "status": "available",
                        "supported_tasks": ["swe_bench_lite"]
                    }
                ]
                
                response = {
                    "adapters": adapters,
                    "total": len(adapters)
                }
                
                # Record API call for validation
                self.real_execution_validator.record_api_call(
                    "/api/v1/adapters", "GET", response
                )
                
                return jsonify(response)
                
            except Exception as e:
                self.logger.error(f"Error listing adapters: {e}")
                return jsonify({"error": str(e)}), 500
        
        @self.app.route('/api/v1/evaluations/<evaluation_id>', methods=['DELETE'])
        def cancel_evaluation(evaluation_id):
            """Cancel an evaluation."""
            try:
                if evaluation_id not in self._evaluations:
                    return jsonify({"error": "Evaluation not found"}), 404
                
                evaluation = self._evaluations[evaluation_id]
                
                if evaluation["status"] in ["completed", "failed", "cancelled"]:
                    return jsonify({
                        "error": "Cannot cancel evaluation",
                        "status": evaluation["status"]
                    }), 400
                
                # Cancel evaluation
                evaluation["status"] = "cancelled"
                evaluation["completed_at"] = datetime.now().isoformat()
                
                response = {
                    "evaluation_id": evaluation_id,
                    "status": "cancelled",
                    "message": "Evaluation cancelled successfully"
                }
                
                # Record API call for validation
                self.real_execution_validator.record_api_call(
                    f"/api/v1/evaluations/{evaluation_id}", "DELETE", response
                )
                
                return jsonify(response)
                
            except Exception as e:
                self.logger.error(f"Error cancelling evaluation: {e}")
                return jsonify({"error": str(e)}), 500
    
    def _start_evaluation_async(self, evaluation_id: str) -> None:
        """Start evaluation asynchronously."""
        def run_evaluation():
            try:
                evaluation = self._evaluations[evaluation_id]
                
                # Update status to running
                evaluation["status"] = "running"
                evaluation["started_at"] = datetime.now().isoformat()
                evaluation["progress"] = 0.1
                
                self.logger.info(f"Starting evaluation {evaluation_id}")
                
                # Simulate evaluation execution
                tasks = evaluation["tasks"]
                total_tasks = len(tasks)
                
                results = {
                    "evaluation_id": evaluation_id,
                    "model_id": evaluation["model_id"],
                    "task_results": [],
                    "summary": {
                        "total_tasks": total_tasks,
                        "completed_tasks": 0,
                        "success_rate": 0.0,
                        "total_execution_time": 0.0
                    }
                }
                
                # Process each task
                for i, task in enumerate(tasks):
                    if self._shutdown_event.is_set():
                        break
                    
                    # Simulate task execution
                    task_start_time = time.time()
                    time.sleep(2)  # Simulate processing time
                    task_execution_time = time.time() - task_start_time
                    
                    # Create mock result
                    task_result = {
                        "task_id": task,
                        "status": "completed",
                        "success": True,
                        "score": 0.75 + (i * 0.05),  # Varying scores
                        "execution_time": task_execution_time,
                        "metrics": {
                            "accuracy": 0.75 + (i * 0.05),
                            "tokens_used": 1000 + (i * 100)
                        }
                    }
                    
                    results["task_results"].append(task_result)
                    results["summary"]["completed_tasks"] += 1
                    results["summary"]["total_execution_time"] += task_execution_time
                    
                    # Update progress
                    progress = (i + 1) / total_tasks
                    evaluation["progress"] = progress
                    
                    self.logger.info(f"Evaluation {evaluation_id} progress: {progress:.1%}")
                
                # Calculate final metrics
                if results["task_results"]:
                    successful_tasks = sum(1 for r in results["task_results"] if r["success"])
                    results["summary"]["success_rate"] = successful_tasks / len(results["task_results"])
                
                # Complete evaluation
                evaluation["status"] = "completed"
                evaluation["completed_at"] = datetime.now().isoformat()
                evaluation["progress"] = 1.0
                
                self._evaluation_results[evaluation_id] = results
                
                self.logger.info(f"Evaluation {evaluation_id} completed successfully")
                
            except Exception as e:
                self.logger.error(f"Evaluation {evaluation_id} failed: {e}")
                evaluation["status"] = "failed"
                evaluation["error"] = str(e)
                evaluation["completed_at"] = datetime.now().isoformat()
        
        # Start evaluation in background thread
        eval_thread = threading.Thread(target=run_evaluation, daemon=True)
        eval_thread.start()


def create_api_test_server(host: str = "localhost", port: int = 8000) -> APITestServer:
    """Factory function to create an API test server."""
    return APITestServer(host=host, port=port)