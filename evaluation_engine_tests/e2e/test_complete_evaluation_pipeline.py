"""
End-to-end tests for complete evaluation pipeline.
"""

import pytest
import asyncio
import json
import tempfile
import subprocess
import time
from pathlib import Path
from unittest.mock import Mock, patch, AsyncMock

from evaluation_engine.core.unified_framework import UnifiedEvaluationFramework
from evaluation_engine.api.server import app
from fastapi.testclient import TestClient


class TestCompleteEvaluationPipeline:
    """Test complete evaluation pipeline from API to results."""

    @pytest.fixture
    def api_client(self):
        """FastAPI test client."""
        return TestClient(app)

    @pytest.fixture
    def complete_dataset(self, temp_dir):
        """Create complete dataset for E2E testing."""
        # Single-turn tasks
        single_turn_data = [
            {
                "id": "e2e_single_1",
                "input": "Write a function to reverse a string",
                "expected_output": "def reverse_string(s):\n    return s[::-1]",
                "test_cases": [
                    {"input": "hello", "expected": "olleh"},
                    {"input": "world", "expected": "dlrow"}
                ],
                "difficulty": "easy",
                "language": "python"
            },
            {
                "id": "e2e_single_2", 
                "input": "Implement a function to check if a number is prime",
                "expected_output": "def is_prime(n):\n    if n < 2:\n        return False\n    for i in range(2, int(n**0.5) + 1):\n        if n % i == 0:\n            return False\n    return True",
                "test_cases": [
                    {"input": 7, "expected": True},
                    {"input": 4, "expected": False},
                    {"input": 1, "expected": False}
                ],
                "difficulty": "medium",
                "language": "python"
            }
        ]
        
        # Multi-turn conversation data
        multi_turn_data = [
            {
                "conversation_id": "e2e_conv_1",
                "scenario": "code_review",
                "turns": [
                    {
                        "turn_id": 1,
                        "role": "user",
                        "content": "Please review this sorting function: def sort_list(lst): return sorted(lst)",
                        "expected_response_type": "code_review"
                    },
                    {
                        "turn_id": 2,
                        "role": "assistant",
                        "content": "The function works but could be more explicit about the sorting algorithm and handle edge cases.",
                        "expected_response_type": "improvement_suggestion"
                    },
                    {
                        "turn_id": 3,
                        "role": "user",
                        "content": "Can you implement a more robust version?",
                        "expected_response_type": "improved_code"
                    }
                ],
                "success_criteria": {
                    "coherence_threshold": 0.8,
                    "context_retention_threshold": 0.7,
                    "goal_achievement_threshold": 0.9
                }
            }
        ]
        
        # Save datasets
        single_turn_file = temp_dir / "e2e_single_turn.jsonl"
        with open(single_turn_file, 'w') as f:
            for item in single_turn_data:
                f.write(json.dumps(item) + '\n')
        
        multi_turn_file = temp_dir / "e2e_multi_turn.jsonl"
        with open(multi_turn_file, 'w') as f:
            for item in multi_turn_data:
                f.write(json.dumps(item) + '\n')
        
        return {
            "single_turn": str(single_turn_file),
            "multi_turn": str(multi_turn_file)
        }

    @pytest.fixture
    def mock_model_server(self):
        """Mock external model server."""
        responses = {
            "reverse_string": "def reverse_string(s):\n    return s[::-1]",
            "is_prime": "def is_prime(n):\n    if n < 2:\n        return False\n    for i in range(2, int(n**0.5) + 1):\n        if n % i == 0:\n            return False\n    return True",
            "code_review": "The function is simple and works correctly. However, it could benefit from input validation and documentation.",
            "improved_code": "def sort_list(lst):\n    \"\"\"Sort a list using the built-in sorted function.\"\"\"\n    if not isinstance(lst, list):\n        raise TypeError('Input must be a list')\n    return sorted(lst)"
        }
        
        class MockModelServer:
            def __init__(self):
                self.responses = responses
                self.call_count = 0
            
            async def generate_response(self, prompt, model_config=None):
                self.call_count += 1
                # Simple prompt matching
                if "reverse" in prompt.lower():
                    return {"response": self.responses["reverse_string"], "usage": {"prompt_tokens": 30, "completion_tokens": 15}}
                elif "prime" in prompt.lower():
                    return {"response": self.responses["is_prime"], "usage": {"prompt_tokens": 40, "completion_tokens": 25}}
                elif "review" in prompt.lower():
                    return {"response": self.responses["code_review"], "usage": {"prompt_tokens": 50, "completion_tokens": 20}}
                elif "robust" in prompt.lower() or "implement" in prompt.lower():
                    return {"response": self.responses["improved_code"], "usage": {"prompt_tokens": 60, "completion_tokens": 30}}
                else:
                    return {"response": "Generic response", "usage": {"prompt_tokens": 20, "completion_tokens": 10}}
        
        return MockModelServer()

    @pytest.mark.e2e
    @pytest.mark.asyncio
    async def test_complete_single_turn_pipeline(self, api_client, complete_dataset, mock_model_server, temp_dir):
        """Test complete single-turn evaluation pipeline via API."""
        # Setup evaluation framework
        config = {
            "data_dir": str(temp_dir),
            "cache_dir": str(temp_dir / "cache"),
            "results_dir": str(temp_dir / "results"),
            "log_level": "INFO"
        }
        
        with patch('evaluation_engine.api.server.evaluation_framework') as mock_framework:
            # Configure mock framework
            mock_framework.register_task.return_value = "e2e_single_task"
            mock_framework.register_model_adapter.return_value = True
            mock_framework.run_evaluation.return_value = {
                "evaluation_id": "e2e_eval_123",
                "model_id": "test_model",
                "results": [
                    {
                        "task_id": "e2e_single_task",
                        "metrics": {
                            "accuracy": 0.95,
                            "bleu": 0.88,
                            "code_quality": 0.92,
                            "execution_success": 1.0
                        },
                        "outputs": [
                            {"id": "e2e_single_1", "response": "def reverse_string(s):\n    return s[::-1]"},
                            {"id": "e2e_single_2", "response": "def is_prime(n):\n    if n < 2:\n        return False\n    for i in range(2, int(n**0.5) + 1):\n        if n % i == 0:\n            return False\n    return True"}
                        ],
                        "execution_time": 45.2
                    }
                ],
                "timestamp": "2024-01-01T12:00:00Z",
                "analysis": {
                    "strengths": ["High accuracy", "Good code quality"],
                    "weaknesses": ["Could improve documentation"],
                    "recommendations": ["Add more comprehensive test cases"]
                }
            }
            
            # Register task via API
            task_payload = {
                "task_id": "e2e_single_task",
                "task_type": "single_turn",
                "description": "E2E single-turn test",
                "dataset_path": complete_dataset["single_turn"],
                "metrics": ["accuracy", "bleu", "code_quality", "execution_success"],
                "context_mode": "full_context"
            }
            
            response = api_client.post("/api/v1/tasks", json=task_payload)
            assert response.status_code == 201
            
            # Register model via API
            model_payload = {
                "model_id": "test_model",
                "model_type": "mock",
                "config": {
                    "api_key": "test_key",
                    "base_url": "http://localhost:8000",
                    "max_tokens": 1000,
                    "temperature": 0.7
                }
            }
            
            response = api_client.post("/api/v1/models", json=model_payload)
            assert response.status_code == 201
            
            # Start evaluation via API
            evaluation_payload = {
                "task_ids": ["e2e_single_task"],
                "model_id": "test_model",
                "config": {
                    "enable_analysis": True,
                    "enable_visualization": True,
                    "save_results": True
                }
            }
            
            response = api_client.post("/api/v1/evaluations", json=evaluation_payload)
            assert response.status_code == 202
            
            evaluation_id = response.json()["evaluation_id"]
            
            # Poll for completion
            max_polls = 30
            for _ in range(max_polls):
                response = api_client.get(f"/api/v1/evaluations/{evaluation_id}")
                if response.status_code == 200:
                    result = response.json()
                    if result["status"] == "completed":
                        break
                time.sleep(1)
            else:
                pytest.fail("Evaluation did not complete within timeout")
            
            # Verify results
            assert result["status"] == "completed"
            assert "results" in result
            assert len(result["results"]) == 1
            
            task_result = result["results"][0]
            assert task_result["task_id"] == "e2e_single_task"
            assert "metrics" in task_result
            assert task_result["metrics"]["accuracy"] > 0.9
            assert "analysis" in result

    @pytest.mark.e2e
    @pytest.mark.asyncio
    async def test_complete_multi_turn_pipeline(self, api_client, complete_dataset, mock_model_server, temp_dir):
        """Test complete multi-turn evaluation pipeline."""
        with patch('evaluation_engine.api.server.evaluation_framework') as mock_framework:
            # Configure mock framework for multi-turn
            mock_framework.register_task.return_value = "e2e_multi_task"
            mock_framework.register_model_adapter.return_value = True
            mock_framework.run_evaluation.return_value = {
                "evaluation_id": "e2e_multi_eval_456",
                "model_id": "test_model",
                "results": [
                    {
                        "task_id": "e2e_multi_task",
                        "metrics": {
                            "coherence": 0.87,
                            "context_retention": 0.82,
                            "goal_achievement": 0.91,
                            "turn_quality": 0.89
                        },
                        "conversation_results": [
                            {
                                "conversation_id": "e2e_conv_1",
                                "turns": [
                                    {"turn_id": 1, "response": "The function is simple and works correctly.", "quality_score": 0.85},
                                    {"turn_id": 2, "response": "Here's an improved version with validation.", "quality_score": 0.92}
                                ],
                                "overall_score": 0.89
                            }
                        ],
                        "execution_time": 78.5
                    }
                ],
                "timestamp": "2024-01-01T12:05:00Z"
            }
            
            # Register multi-turn task
            task_payload = {
                "task_id": "e2e_multi_task",
                "task_type": "multi_turn",
                "description": "E2E multi-turn test",
                "dataset_path": complete_dataset["multi_turn"],
                "metrics": ["coherence", "context_retention", "goal_achievement"],
                "max_turns": 3,
                "conversation_timeout": 300
            }
            
            response = api_client.post("/api/v1/tasks", json=task_payload)
            assert response.status_code == 201
            
            # Start multi-turn evaluation
            evaluation_payload = {
                "task_ids": ["e2e_multi_task"],
                "model_id": "test_model",
                "config": {
                    "enable_multi_turn": True,
                    "conversation_analysis": True
                }
            }
            
            response = api_client.post("/api/v1/evaluations", json=evaluation_payload)
            assert response.status_code == 202
            
            evaluation_id = response.json()["evaluation_id"]
            
            # Poll for completion
            max_polls = 30
            for _ in range(max_polls):
                response = api_client.get(f"/api/v1/evaluations/{evaluation_id}")
                if response.status_code == 200:
                    result = response.json()
                    if result["status"] == "completed":
                        break
                time.sleep(1)
            else:
                pytest.fail("Multi-turn evaluation did not complete")
            
            # Verify multi-turn results
            assert result["status"] == "completed"
            task_result = result["results"][0]
            assert "conversation_results" in task_result
            assert task_result["metrics"]["coherence"] > 0.8

    @pytest.mark.e2e
    @pytest.mark.requires_docker
    async def test_sandbox_execution_pipeline(self, api_client, temp_dir):
        """Test complete pipeline with sandbox execution."""
        # Create dataset with executable code
        code_dataset = [
            {
                "id": "e2e_sandbox_1",
                "input": "Write a function to calculate the sum of a list",
                "expected_output": "def sum_list(lst):\n    return sum(lst)",
                "test_cases": [
                    {"input": [1, 2, 3, 4, 5], "expected": 15},
                    {"input": [], "expected": 0},
                    {"input": [-1, 1], "expected": 0}
                ],
                "language": "python",
                "enable_execution": True
            }
        ]
        
        dataset_file = temp_dir / "e2e_sandbox.jsonl"
        with open(dataset_file, 'w') as f:
            for item in code_dataset:
                f.write(json.dumps(item) + '\n')
        
        with patch('evaluation_engine.api.server.evaluation_framework') as mock_framework:
            with patch('evaluation_engine.core.sandbox_executor.SandboxExecutor') as mock_executor:
                # Configure mock sandbox
                mock_executor_instance = Mock()
                mock_executor_instance.execute_code.return_value = {
                    "success": True,
                    "output": "15",
                    "execution_time": 0.05,
                    "memory_usage": 2048,
                    "test_results": [
                        {"passed": True, "output": 15, "expected": 15},
                        {"passed": True, "output": 0, "expected": 0},
                        {"passed": True, "output": 0, "expected": 0}
                    ],
                    "security_violations": []
                }
                mock_executor.return_value = mock_executor_instance
                
                # Configure mock framework
                mock_framework.register_task.return_value = "e2e_sandbox_task"
                mock_framework.run_evaluation.return_value = {
                    "evaluation_id": "e2e_sandbox_eval_789",
                    "model_id": "test_model",
                    "results": [
                        {
                            "task_id": "e2e_sandbox_task",
                            "metrics": {
                                "accuracy": 1.0,
                                "pass_at_k": 1.0,
                                "execution_success": 1.0,
                                "security_score": 1.0
                            },
                            "execution_results": [
                                {
                                    "id": "e2e_sandbox_1",
                                    "code": "def sum_list(lst):\n    return sum(lst)",
                                    "execution_success": True,
                                    "test_results": [
                                        {"passed": True, "output": 15, "expected": 15},
                                        {"passed": True, "output": 0, "expected": 0},
                                        {"passed": True, "output": 0, "expected": 0}
                                    ]
                                }
                            ]
                        }
                    ]
                }
                
                # Register sandbox-enabled task
                task_payload = {
                    "task_id": "e2e_sandbox_task",
                    "task_type": "single_turn",
                    "description": "E2E sandbox test",
                    "dataset_path": str(dataset_file),
                    "metrics": ["accuracy", "pass_at_k", "execution_success", "security_score"],
                    "enable_sandbox": True,
                    "sandbox_config": {
                        "timeout": 30,
                        "memory_limit": "256MB",
                        "enable_network": False
                    }
                }
                
                response = api_client.post("/api/v1/tasks", json=task_payload)
                assert response.status_code == 201
                
                # Start evaluation with sandbox
                evaluation_payload = {
                    "task_ids": ["e2e_sandbox_task"],
                    "model_id": "test_model",
                    "config": {
                        "enable_sandbox": True,
                        "security_scanning": True
                    }
                }
                
                response = api_client.post("/api/v1/evaluations", json=evaluation_payload)
                assert response.status_code == 202
                
                evaluation_id = response.json()["evaluation_id"]
                
                # Wait for completion
                max_polls = 30
                for _ in range(max_polls):
                    response = api_client.get(f"/api/v1/evaluations/{evaluation_id}")
                    if response.status_code == 200:
                        result = response.json()
                        if result["status"] == "completed":
                            break
                    time.sleep(1)
                
                # Verify sandbox execution
                assert result["status"] == "completed"
                task_result = result["results"][0]
                assert task_result["metrics"]["execution_success"] == 1.0
                assert "execution_results" in task_result

    @pytest.mark.e2e
    @pytest.mark.slow
    async def test_large_scale_evaluation(self, api_client, temp_dir):
        """Test large-scale evaluation pipeline."""
        # Create large dataset
        large_dataset = []
        for i in range(100):  # 100 test cases
            large_dataset.append({
                "id": f"large_scale_{i}",
                "input": f"Write a function to process item {i}",
                "expected_output": f"def process_item_{i}(data):\n    return data * {i}",
                "difficulty": "easy" if i < 50 else "medium"
            })
        
        dataset_file = temp_dir / "large_scale_dataset.jsonl"
        with open(dataset_file, 'w') as f:
            for item in large_dataset:
                f.write(json.dumps(item) + '\n')
        
        with patch('evaluation_engine.api.server.evaluation_framework') as mock_framework:
            # Configure mock for large scale
            mock_framework.register_task.return_value = "large_scale_task"
            mock_framework.run_evaluation.return_value = {
                "evaluation_id": "large_scale_eval_999",
                "model_id": "test_model",
                "results": [
                    {
                        "task_id": "large_scale_task",
                        "metrics": {
                            "accuracy": 0.89,
                            "bleu": 0.76,
                            "processing_time_per_item": 0.5
                        },
                        "total_items": 100,
                        "successful_items": 89,
                        "failed_items": 11,
                        "execution_time": 250.0
                    }
                ],
                "performance_stats": {
                    "throughput": 0.4,  # items per second
                    "memory_peak": "512MB",
                    "cpu_usage_avg": 0.75
                }
            }
            
            # Register large-scale task
            task_payload = {
                "task_id": "large_scale_task",
                "task_type": "single_turn",
                "description": "Large-scale evaluation test",
                "dataset_path": str(dataset_file),
                "metrics": ["accuracy", "bleu"],
                "batch_size": 10,
                "enable_parallel_processing": True
            }
            
            response = api_client.post("/api/v1/tasks", json=task_payload)
            assert response.status_code == 201
            
            # Start large-scale evaluation
            evaluation_payload = {
                "task_ids": ["large_scale_task"],
                "model_id": "test_model",
                "config": {
                    "max_concurrent_requests": 5,
                    "enable_progress_tracking": True,
                    "enable_performance_monitoring": True
                }
            }
            
            response = api_client.post("/api/v1/evaluations", json=evaluation_payload)
            assert response.status_code == 202
            
            evaluation_id = response.json()["evaluation_id"]
            
            # Monitor progress
            progress_updates = []
            max_polls = 60  # Longer timeout for large scale
            for _ in range(max_polls):
                response = api_client.get(f"/api/v1/evaluations/{evaluation_id}")
                if response.status_code == 200:
                    result = response.json()
                    progress_updates.append(result.get("progress", 0))
                    if result["status"] == "completed":
                        break
                time.sleep(2)
            
            # Verify large-scale results
            assert result["status"] == "completed"
            assert "performance_stats" in result
            assert result["results"][0]["total_items"] == 100
            
            # Verify progress was tracked
            assert len(progress_updates) > 1
            assert max(progress_updates) == 100  # Should reach 100% completion

    @pytest.mark.e2e
    async def test_error_recovery_pipeline(self, api_client, temp_dir):
        """Test error recovery in complete pipeline."""
        # Create dataset that will cause some failures
        error_dataset = [
            {
                "id": "error_test_1",
                "input": "Valid input",
                "expected_output": "Valid output"
            },
            {
                "id": "error_test_2",
                "input": "This will cause an error",
                "expected_output": "Error output"
            },
            {
                "id": "error_test_3",
                "input": "Another valid input",
                "expected_output": "Another valid output"
            }
        ]
        
        dataset_file = temp_dir / "error_dataset.jsonl"
        with open(dataset_file, 'w') as f:
            for item in error_dataset:
                f.write(json.dumps(item) + '\n')
        
        with patch('evaluation_engine.api.server.evaluation_framework') as mock_framework:
            # Configure mock to simulate errors
            mock_framework.register_task.return_value = "error_recovery_task"
            mock_framework.run_evaluation.return_value = {
                "evaluation_id": "error_recovery_eval_111",
                "model_id": "test_model",
                "results": [
                    {
                        "task_id": "error_recovery_task",
                        "metrics": {
                            "accuracy": 0.67,  # 2 out of 3 successful
                            "success_rate": 0.67
                        },
                        "successful_items": 2,
                        "failed_items": 1,
                        "errors": [
                            {
                                "item_id": "error_test_2",
                                "error_type": "ModelAPIError",
                                "error_message": "API rate limit exceeded",
                                "retry_count": 3,
                                "recovery_action": "skipped"
                            }
                        ],
                        "recovery_stats": {
                            "total_retries": 3,
                            "successful_recoveries": 0,
                            "failed_recoveries": 1
                        }
                    }
                ],
                "status": "completed_with_errors"
            }
            
            # Register task with error recovery
            task_payload = {
                "task_id": "error_recovery_task",
                "task_type": "single_turn",
                "description": "Error recovery test",
                "dataset_path": str(dataset_file),
                "metrics": ["accuracy"],
                "error_handling": {
                    "max_retries": 3,
                    "retry_delay": 1,
                    "continue_on_error": True,
                    "error_threshold": 0.5
                }
            }
            
            response = api_client.post("/api/v1/tasks", json=task_payload)
            assert response.status_code == 201
            
            # Start evaluation with error recovery
            evaluation_payload = {
                "task_ids": ["error_recovery_task"],
                "model_id": "test_model",
                "config": {
                    "enable_error_recovery": True,
                    "fail_fast": False
                }
            }
            
            response = api_client.post("/api/v1/evaluations", json=evaluation_payload)
            assert response.status_code == 202
            
            evaluation_id = response.json()["evaluation_id"]
            
            # Wait for completion
            max_polls = 30
            for _ in range(max_polls):
                response = api_client.get(f"/api/v1/evaluations/{evaluation_id}")
                if response.status_code == 200:
                    result = response.json()
                    if result["status"] in ["completed", "completed_with_errors"]:
                        break
                time.sleep(1)
            
            # Verify error recovery
            assert result["status"] == "completed_with_errors"
            task_result = result["results"][0]
            assert "errors" in task_result
            assert len(task_result["errors"]) == 1
            assert task_result["successful_items"] == 2
            assert "recovery_stats" in task_result

    @pytest.mark.e2e
    async def test_real_time_monitoring_pipeline(self, api_client, temp_dir):
        """Test real-time monitoring during evaluation."""
        # Create dataset for monitoring test
        monitoring_dataset = [
            {"id": f"monitor_{i}", "input": f"Test input {i}", "expected_output": f"Output {i}"}
            for i in range(20)
        ]
        
        dataset_file = temp_dir / "monitoring_dataset.jsonl"
        with open(dataset_file, 'w') as f:
            for item in monitoring_dataset:
                f.write(json.dumps(item) + '\n')
        
        with patch('evaluation_engine.api.server.evaluation_framework') as mock_framework:
            # Configure mock with progress simulation
            progress_states = [
                {"status": "running", "progress": 0, "current_item": 0},
                {"status": "running", "progress": 25, "current_item": 5},
                {"status": "running", "progress": 50, "current_item": 10},
                {"status": "running", "progress": 75, "current_item": 15},
                {"status": "completed", "progress": 100, "current_item": 20}
            ]
            
            call_count = 0
            def mock_get_evaluation_status(eval_id):
                nonlocal call_count
                if call_count < len(progress_states):
                    state = progress_states[call_count]
                    call_count += 1
                    return {
                        "evaluation_id": eval_id,
                        **state,
                        "metrics": {"accuracy": 0.8 + (call_count * 0.02)},
                        "performance": {
                            "items_per_second": 2.5,
                            "estimated_completion": f"{(20 - state['current_item']) * 0.4:.1f}s"
                        }
                    }
                return progress_states[-1]
            
            mock_framework.get_evaluation_status.side_effect = mock_get_evaluation_status
            mock_framework.register_task.return_value = "monitoring_task"
            mock_framework.run_evaluation.return_value = {
                "evaluation_id": "monitoring_eval_222",
                "status": "started"
            }
            
            # Register monitoring task
            task_payload = {
                "task_id": "monitoring_task",
                "task_type": "single_turn",
                "description": "Real-time monitoring test",
                "dataset_path": str(dataset_file),
                "metrics": ["accuracy"],
                "enable_real_time_monitoring": True
            }
            
            response = api_client.post("/api/v1/tasks", json=task_payload)
            assert response.status_code == 201
            
            # Start evaluation with monitoring
            evaluation_payload = {
                "task_ids": ["monitoring_task"],
                "model_id": "test_model",
                "config": {
                    "enable_real_time_updates": True,
                    "update_interval": 1
                }
            }
            
            response = api_client.post("/api/v1/evaluations", json=evaluation_payload)
            assert response.status_code == 202
            
            evaluation_id = response.json()["evaluation_id"]
            
            # Monitor progress in real-time
            progress_history = []
            max_polls = 10
            for _ in range(max_polls):
                response = api_client.get(f"/api/v1/evaluations/{evaluation_id}/status")
                if response.status_code == 200:
                    status = response.json()
                    progress_history.append(status["progress"])
                    if status["status"] == "completed":
                        break
                time.sleep(1)
            
            # Verify real-time monitoring
            assert len(progress_history) > 1
            assert progress_history[0] < progress_history[-1]  # Progress should increase
            assert progress_history[-1] == 100  # Should reach completion

    @pytest.mark.e2e
    async def test_result_export_pipeline(self, api_client, temp_dir):
        """Test complete pipeline with result export."""
        with patch('evaluation_engine.api.server.evaluation_framework') as mock_framework:
            # Configure mock framework
            mock_framework.register_task.return_value = "export_test_task"
            mock_framework.run_evaluation.return_value = {
                "evaluation_id": "export_eval_333",
                "model_id": "test_model",
                "results": [
                    {
                        "task_id": "export_test_task",
                        "metrics": {"accuracy": 0.92, "bleu": 0.85},
                        "outputs": [{"id": "test_1", "response": "Test response"}]
                    }
                ],
                "analysis": {"summary": "Good performance overall"},
                "timestamp": "2024-01-01T12:00:00Z"
            }
            
            # Mock export functionality
            def mock_export_results(eval_id, format_type):
                export_file = temp_dir / f"export_{eval_id}.{format_type}"
                if format_type == "json":
                    with open(export_file, 'w') as f:
                        json.dump({"evaluation_id": eval_id, "format": format_type}, f)
                elif format_type == "csv":
                    with open(export_file, 'w') as f:
                        f.write("task_id,accuracy,bleu\nexport_test_task,0.92,0.85\n")
                elif format_type == "html":
                    with open(export_file, 'w') as f:
                        f.write(f"<html><body><h1>Evaluation {eval_id}</h1></body></html>")
                return str(export_file)
            
            mock_framework.export_results.side_effect = mock_export_results
            
            # Complete evaluation first
            task_payload = {
                "task_id": "export_test_task",
                "task_type": "single_turn",
                "description": "Export test",
                "dataset_path": "/tmp/test.jsonl",
                "metrics": ["accuracy", "bleu"]
            }
            
            api_client.post("/api/v1/tasks", json=task_payload)
            
            evaluation_payload = {
                "task_ids": ["export_test_task"],
                "model_id": "test_model"
            }
            
            response = api_client.post("/api/v1/evaluations", json=evaluation_payload)
            evaluation_id = response.json()["evaluation_id"]
            
            # Test different export formats
            export_formats = ["json", "csv", "html"]
            
            for format_type in export_formats:
                response = api_client.post(
                    f"/api/v1/evaluations/{evaluation_id}/export",
                    json={"format": format_type}
                )
                
                assert response.status_code == 200
                export_data = response.json()
                assert "export_url" in export_data
                assert format_type in export_data["export_url"]
                
                # Verify file was created
                export_file = temp_dir / f"export_{evaluation_id}.{format_type}"
                assert export_file.exists()
                
                # Verify content based on format
                if format_type == "json":
                    with open(export_file, 'r') as f:
                        data = json.load(f)
                        assert data["evaluation_id"] == evaluation_id
                elif format_type == "csv":
                    with open(export_file, 'r') as f:
                        content = f.read()
                        assert "accuracy" in content
                        assert "0.92" in content
                elif format_type == "html":
                    with open(export_file, 'r') as f:
                        content = f.read()
                        assert "<html>" in content
                        assert evaluation_id in content