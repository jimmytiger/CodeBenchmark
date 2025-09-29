"""
Tests for Multi-Turn Evaluation API Endpoints

Tests REST API endpoints, WebSocket functionality, and integration
with the multi-turn orchestrator.
"""

import pytest
import asyncio
import json
from datetime import datetime, timedelta
from unittest.mock import Mock, patch, AsyncMock
from fastapi.testclient import TestClient
from fastapi import FastAPI

from ..api.multi_turn_endpoints import router, active_evaluations
from ..api.models import (
    MultiTurnEvaluationRequest, MultiTurnEvaluationStatus,
    FeedbackStrategy, SafetyLevel, TerminationReason
)
from ..core.data_models import MultiTurnConfig, FeedbackConfig, SafetyConfig


@pytest.fixture
def app():
    """Create FastAPI app for testing."""
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
    with patch('EvaluationEngineV1_0.api.multi_turn_endpoints.get_current_user') as mock:
        mock.return_value = {"user_id": "test_user", "username": "testuser", "roles": ["user"]}
        yield mock


@pytest.fixture
def mock_admin_auth():
    """Mock admin authentication."""
    with patch('EvaluationEngineV1_0.api.multi_turn_endpoints.get_current_user') as mock_user:
        with patch('EvaluationEngineV1_0.api.multi_turn_endpoints.require_admin') as mock_admin:
            mock_user.return_value = {"user_id": "admin_user", "username": "admin", "roles": ["admin"]}
            mock_admin.return_value = {"user_id": "admin_user", "username": "admin", "roles": ["admin"]}
            yield mock_user, mock_admin


@pytest.fixture
def mock_orchestrator():
    """Mock multi-turn orchestrator."""
    with patch('EvaluationEngineV1_0.api.multi_turn_endpoints.get_orchestrator') as mock:
        orchestrator = Mock()
        mock.return_value = orchestrator
        yield orchestrator


@pytest.fixture
def mock_task_registry():
    """Mock task registry."""
    with patch('EvaluationEngineV1_0.api.multi_turn_endpoints.get_task_registry') as mock:
        registry = Mock()
        registry.has_task.return_value = True
        registry.get_task_type.return_value = "multi_turn"
        registry.create_task_instance.return_value = Mock()
        mock.return_value = registry
        yield registry


@pytest.fixture
def sample_evaluation_request():
    """Sample evaluation request."""
    return MultiTurnEvaluationRequest(
        model_id="gpt-4",
        task_ids=["swe_bench_lite_001", "intercode_python_001"],
        max_turns=10,
        timeout_seconds=3600,
        feedback_strategy=FeedbackStrategy.ADAPTIVE,
        safety_level=SafetyLevel.MODERATE,
        enable_context_retention=True,
        metadata={"test": "data"}
    )


@pytest.fixture(autouse=True)
def cleanup_evaluations():
    """Clean up active evaluations after each test."""
    yield
    active_evaluations.clear()


class TestMultiTurnEvaluationEndpoints:
    """Test multi-turn evaluation REST API endpoints."""
    
    def test_create_evaluation_success(self, client, mock_auth, mock_task_registry, sample_evaluation_request):
        """Test successful evaluation creation."""
        response = client.post(
            "/multi-turn/evaluations",
            json=sample_evaluation_request.dict(),
            headers={"Authorization": "Bearer test_token"}
        )
        
        assert response.status_code == 200
        data = response.json()
        
        assert "evaluation_id" in data
        assert data["status"] == MultiTurnEvaluationStatus.CREATED
        assert data["message"] == "Multi-turn evaluation created successfully"
        assert "websocket_url" in data
        assert "estimated_duration" in data
        
        # Check that evaluation was stored
        assert len(active_evaluations) == 1
        eval_id = data["evaluation_id"]
        assert eval_id in active_evaluations
        
        eval_data = active_evaluations[eval_id]
        assert eval_data["model_id"] == "gpt-4"
        assert eval_data["task_ids"] == ["swe_bench_lite_001", "intercode_python_001"]
        assert eval_data["created_by"] == "test_user"
    
    def test_create_evaluation_invalid_task(self, client, mock_auth, mock_task_registry, sample_evaluation_request):
        """Test evaluation creation with invalid task."""
        mock_task_registry.has_task.return_value = False
        
        response = client.post(
            "/multi-turn/evaluations",
            json=sample_evaluation_request.dict(),
            headers={"Authorization": "Bearer test_token"}
        )
        
        assert response.status_code == 400
        assert "Task not found" in response.json()["detail"]
    
    def test_create_evaluation_single_turn_task(self, client, mock_auth, mock_task_registry, sample_evaluation_request):
        """Test evaluation creation with single-turn task."""
        mock_task_registry.get_task_type.return_value = "single_turn"
        
        response = client.post(
            "/multi-turn/evaluations",
            json=sample_evaluation_request.dict(),
            headers={"Authorization": "Bearer test_token"}
        )
        
        assert response.status_code == 400
        assert "not a multi-turn task" in response.json()["detail"]
    
    def test_create_evaluation_validation_error(self, client, mock_auth):
        """Test evaluation creation with validation error."""
        invalid_request = {
            "model_id": "gpt-4",
            "task_ids": [],  # Empty task list should fail validation
            "max_turns": 10
        }
        
        response = client.post(
            "/multi-turn/evaluations",
            json=invalid_request,
            headers={"Authorization": "Bearer test_token"}
        )
        
        assert response.status_code == 422  # Validation error
    
    def test_get_evaluation_status(self, client, mock_auth):
        """Test getting evaluation status."""
        # Create test evaluation
        eval_id = "test_eval_001"
        active_evaluations[eval_id] = {
            "id": eval_id,
            "model_id": "gpt-4",
            "task_ids": ["task1", "task2"],
            "status": MultiTurnEvaluationStatus.RUNNING,
            "created_at": datetime.utcnow(),
            "created_by": "test_user",
            "progress": 0.5,
            "current_task": "task1",
            "current_turn": 3,
            "completed_tasks": 1,
            "total_tasks": 2,
            "safety_incidents": 0,
            "total_turns_executed": 5
        }
        
        response = client.get(
            f"/multi-turn/evaluations/{eval_id}/status",
            headers={"Authorization": "Bearer test_token"}
        )
        
        assert response.status_code == 200
        data = response.json()
        
        assert data["evaluation_id"] == eval_id
        assert data["status"] == MultiTurnEvaluationStatus.RUNNING
        assert data["progress"] == 0.5
        assert data["current_task"] == "task1"
        assert data["current_turn"] == 3
        assert data["completed_tasks"] == 1
        assert data["total_tasks"] == 2
    
    def test_get_evaluation_status_not_found(self, client, mock_auth):
        """Test getting status for non-existent evaluation."""
        response = client.get(
            "/multi-turn/evaluations/nonexistent/status",
            headers={"Authorization": "Bearer test_token"}
        )
        
        assert response.status_code == 404
        assert "Evaluation not found" in response.json()["detail"]
    
    def test_get_evaluation_results_success(self, client, mock_auth):
        """Test getting evaluation results."""
        eval_id = "test_eval_001"
        active_evaluations[eval_id] = {
            "id": eval_id,
            "model_id": "gpt-4",
            "status": MultiTurnEvaluationStatus.COMPLETED,
            "created_by": "test_user",
            "results": {
                "task_results": [
                    {
                        "task_id": "task1",
                        "success": True,
                        "total_turns": 5,
                        "execution_time": 120.0
                    }
                ],
                "aggregated_metrics": {"success_rate": 1.0},
                "overall_success_rate": 1.0,
                "average_turns_per_task": 5.0,
                "total_execution_time": 120.0,
                "total_tokens": 1000,
                "total_cost": 0.02,
                "safety_summary": {"total_incidents": 0}
            },
            "completed_at": datetime.utcnow()
        }
        
        response = client.get(
            f"/multi-turn/evaluations/{eval_id}/results",
            headers={"Authorization": "Bearer test_token"}
        )
        
        assert response.status_code == 200
        data = response.json()
        
        assert data["evaluation_id"] == eval_id
        assert data["model_id"] == "gpt-4"
        assert data["overall_success_rate"] == 1.0
        assert len(data["task_results"]) == 1
    
    def test_get_evaluation_results_not_completed(self, client, mock_auth):
        """Test getting results for incomplete evaluation."""
        eval_id = "test_eval_001"
        active_evaluations[eval_id] = {
            "id": eval_id,
            "status": MultiTurnEvaluationStatus.RUNNING,
            "created_by": "test_user"
        }
        
        response = client.get(
            f"/multi-turn/evaluations/{eval_id}/results",
            headers={"Authorization": "Bearer test_token"}
        )
        
        assert response.status_code == 400
        assert "Evaluation not completed" in response.json()["detail"]
    
    def test_control_evaluation_pause(self, client, mock_auth):
        """Test pausing evaluation."""
        eval_id = "test_eval_001"
        active_evaluations[eval_id] = {
            "id": eval_id,
            "status": MultiTurnEvaluationStatus.RUNNING,
            "created_by": "test_user"
        }
        
        control_request = {
            "evaluation_id": eval_id,
            "action": "pause",
            "reason": "User requested pause"
        }
        
        response = client.post(
            f"/multi-turn/evaluations/{eval_id}/control",
            json=control_request,
            headers={"Authorization": "Bearer test_token"}
        )
        
        assert response.status_code == 200
        data = response.json()
        
        assert data["new_status"] == MultiTurnEvaluationStatus.PAUSED
        assert active_evaluations[eval_id]["status"] == MultiTurnEvaluationStatus.PAUSED
    
    def test_control_evaluation_invalid_action(self, client, mock_auth):
        """Test invalid control action."""
        eval_id = "test_eval_001"
        active_evaluations[eval_id] = {
            "id": eval_id,
            "status": MultiTurnEvaluationStatus.RUNNING,
            "created_by": "test_user"
        }
        
        control_request = {
            "evaluation_id": eval_id,
            "action": "invalid_action"
        }
        
        response = client.post(
            f"/multi-turn/evaluations/{eval_id}/control",
            json=control_request,
            headers={"Authorization": "Bearer test_token"}
        )
        
        assert response.status_code == 400
        assert "Invalid action" in response.json()["detail"]
    
    def test_control_evaluation_invalid_state(self, client, mock_auth):
        """Test control action on invalid state."""
        eval_id = "test_eval_001"
        active_evaluations[eval_id] = {
            "id": eval_id,
            "status": MultiTurnEvaluationStatus.COMPLETED,
            "created_by": "test_user"
        }
        
        control_request = {
            "evaluation_id": eval_id,
            "action": "pause"
        }
        
        response = client.post(
            f"/multi-turn/evaluations/{eval_id}/control",
            json=control_request,
            headers={"Authorization": "Bearer test_token"}
        )
        
        assert response.status_code == 400
        assert "Cannot pause evaluation" in response.json()["detail"]
    
    def test_list_evaluations(self, client, mock_auth):
        """Test listing evaluations."""
        # Create test evaluations
        for i in range(5):
            eval_id = f"test_eval_{i:03d}"
            active_evaluations[eval_id] = {
                "id": eval_id,
                "model_id": f"model_{i}",
                "status": MultiTurnEvaluationStatus.RUNNING if i % 2 == 0 else MultiTurnEvaluationStatus.COMPLETED,
                "created_at": datetime.utcnow() - timedelta(hours=i),
                "created_by": "test_user",
                "progress": 0.5,
                "completed_tasks": 1,
                "total_tasks": 2,
                "safety_incidents": 0
            }
        
        response = client.get(
            "/multi-turn/evaluations?page=1&page_size=3",
            headers={"Authorization": "Bearer test_token"}
        )
        
        assert response.status_code == 200
        data = response.json()
        
        assert data["total"] == 5
        assert len(data["items"]) == 3
        assert data["page"] == 1
        assert data["page_size"] == 3
        assert data["has_next"] is True
        assert data["has_previous"] is False
    
    def test_list_evaluations_with_filters(self, client, mock_auth):
        """Test listing evaluations with filters."""
        # Create test evaluations
        active_evaluations["eval_1"] = {
            "id": "eval_1",
            "model_id": "gpt-4",
            "status": MultiTurnEvaluationStatus.RUNNING,
            "created_at": datetime.utcnow(),
            "created_by": "test_user",
            "progress": 0.5,
            "completed_tasks": 1,
            "total_tasks": 2,
            "safety_incidents": 0
        }
        active_evaluations["eval_2"] = {
            "id": "eval_2",
            "model_id": "gpt-3.5",
            "status": MultiTurnEvaluationStatus.COMPLETED,
            "created_at": datetime.utcnow(),
            "created_by": "test_user",
            "progress": 1.0,
            "completed_tasks": 2,
            "total_tasks": 2,
            "safety_incidents": 0
        }
        
        # Filter by status
        response = client.get(
            f"/multi-turn/evaluations?status={MultiTurnEvaluationStatus.RUNNING}",
            headers={"Authorization": "Bearer test_token"}
        )
        
        assert response.status_code == 200
        data = response.json()
        
        assert data["total"] == 1
        assert data["items"][0]["evaluation_id"] == "eval_1"
        
        # Filter by model_id
        response = client.get(
            "/multi-turn/evaluations?model_id=gpt-3.5",
            headers={"Authorization": "Bearer test_token"}
        )
        
        assert response.status_code == 200
        data = response.json()
        
        assert data["total"] == 1
        assert data["items"][0]["evaluation_id"] == "eval_2"
    
    def test_get_orchestrator_status(self, client, mock_auth):
        """Test getting orchestrator status."""
        # Create test evaluations in different states
        active_evaluations["eval_1"] = {
            "status": MultiTurnEvaluationStatus.RUNNING,
            "created_at": datetime.utcnow(),
            "safety_incidents": 1
        }
        active_evaluations["eval_2"] = {
            "status": MultiTurnEvaluationStatus.CREATED,
            "created_at": datetime.utcnow(),
            "safety_incidents": 0
        }
        active_evaluations["eval_3"] = {
            "status": MultiTurnEvaluationStatus.COMPLETED,
            "created_at": datetime.utcnow() - timedelta(days=1),
            "completed_at": datetime.utcnow() - timedelta(hours=1),
            "safety_incidents": 0
        }
        
        with patch('psutil.cpu_percent', return_value=25.0):
            with patch('psutil.virtual_memory') as mock_memory:
                mock_memory.return_value.percent = 60.0
                with patch('psutil.disk_usage') as mock_disk:
                    mock_disk.return_value.percent = 45.0
                    
                    response = client.get(
                        "/multi-turn/orchestrator/status",
                        headers={"Authorization": "Bearer test_token"}
                    )
        
        assert response.status_code == 200
        data = response.json()
        
        assert data["active_evaluations"] == 1
        assert data["queued_evaluations"] == 1
        assert data["total_evaluations_today"] == 2
        assert data["safety_incidents_today"] == 1
        assert "resource_usage" in data
        assert data["resource_usage"]["cpu_percent"] == 25.0
    
    def test_get_metrics_snapshot(self, client, mock_auth):
        """Test getting metrics snapshot."""
        response = client.get(
            "/multi-turn/metrics/snapshot",
            headers={"Authorization": "Bearer test_token"}
        )
        
        assert response.status_code == 200
        data = response.json()
        
        assert "task_success_metrics" in data
        assert "efficiency_metrics" in data
        assert "repair_quality_metrics" in data
        assert "robustness_metrics" in data
        assert "cost_metrics" in data
        assert "safety_metrics" in data
        assert "timestamp" in data
    
    def test_get_metrics_snapshot_specific_evaluation(self, client, mock_auth):
        """Test getting metrics snapshot for specific evaluation."""
        eval_id = "test_eval_001"
        active_evaluations[eval_id] = {
            "id": eval_id,
            "status": MultiTurnEvaluationStatus.RUNNING,
            "created_by": "test_user"
        }
        
        response = client.get(
            f"/multi-turn/metrics/snapshot?evaluation_id={eval_id}",
            headers={"Authorization": "Bearer test_token"}
        )
        
        assert response.status_code == 200
        data = response.json()
        
        assert "task_success_metrics" in data
        assert data["task_success_metrics"]["resolved_percentage"] == 0.75
    
    def test_delete_evaluation_admin(self, client, mock_admin_auth):
        """Test deleting evaluation as admin."""
        eval_id = "test_eval_001"
        active_evaluations[eval_id] = {
            "id": eval_id,
            "status": MultiTurnEvaluationStatus.COMPLETED,
            "created_by": "test_user"
        }
        
        response = client.delete(
            f"/multi-turn/evaluations/{eval_id}",
            headers={"Authorization": "Bearer admin_token"}
        )
        
        assert response.status_code == 200
        data = response.json()
        
        assert data["message"] == "Evaluation deleted successfully"
        assert eval_id not in active_evaluations
    
    def test_delete_evaluation_active(self, client, mock_admin_auth):
        """Test deleting active evaluation (should fail)."""
        eval_id = "test_eval_001"
        active_evaluations[eval_id] = {
            "id": eval_id,
            "status": MultiTurnEvaluationStatus.RUNNING,
            "created_by": "test_user"
        }
        
        response = client.delete(
            f"/multi-turn/evaluations/{eval_id}",
            headers={"Authorization": "Bearer admin_token"}
        )
        
        assert response.status_code == 400
        assert "Cannot delete active evaluation" in response.json()["detail"]
    
    def test_system_cleanup_admin(self, client, mock_admin_auth):
        """Test system cleanup as admin."""
        # Create old evaluations
        old_date = datetime.utcnow() - timedelta(days=10)
        active_evaluations["old_eval_1"] = {
            "status": MultiTurnEvaluationStatus.COMPLETED,
            "created_at": old_date
        }
        active_evaluations["old_eval_2"] = {
            "status": MultiTurnEvaluationStatus.FAILED,
            "created_at": old_date
        }
        active_evaluations["recent_eval"] = {
            "status": MultiTurnEvaluationStatus.COMPLETED,
            "created_at": datetime.utcnow()
        }
        
        response = client.post(
            "/multi-turn/system/cleanup?older_than_days=7",
            headers={"Authorization": "Bearer admin_token"}
        )
        
        assert response.status_code == 200
        data = response.json()
        
        assert data["deleted_count"] == 2
        assert "old_eval_1" not in active_evaluations
        assert "old_eval_2" not in active_evaluations
        assert "recent_eval" in active_evaluations


class TestWebSocketIntegration:
    """Test WebSocket integration with multi-turn evaluation."""
    
    @pytest.mark.asyncio
    async def test_websocket_handler_creation(self):
        """Test WebSocket handler creation."""
        from ..api.websocket_handler import WebSocketHandler
        
        handler = WebSocketHandler()
        assert handler is not None
        assert len(handler.connections) == 0
        assert len(handler.evaluation_subscribers) == 0
        assert len(handler.system_subscribers) == 0
    
    @pytest.mark.asyncio
    async def test_websocket_connection_stats(self):
        """Test WebSocket connection statistics."""
        from ..api.websocket_handler import WebSocketHandler
        
        handler = WebSocketHandler()
        stats = handler.get_connection_stats()
        
        assert "total_connections" in stats
        assert "active_connections" in stats
        assert "evaluation_subscriptions" in stats
        assert "system_subscriptions" in stats
        assert stats["total_connections"] == 0
    
    @pytest.mark.asyncio
    async def test_broadcast_evaluation_progress(self):
        """Test broadcasting evaluation progress."""
        from ..api.websocket_handler import WebSocketHandler, WebSocketConnection
        
        handler = WebSocketHandler()
        
        # Mock WebSocket connection
        mock_websocket = AsyncMock()
        connection = WebSocketConnection(mock_websocket, "conn_1", "user_1")
        handler.connections["conn_1"] = connection
        
        # Add subscription
        evaluation_id = "eval_123"
        handler.evaluation_subscribers[evaluation_id] = {"conn_1"}
        connection.add_subscription(f"evaluation:{evaluation_id}")
        
        # Broadcast progress
        progress_data = {
            "progress": 0.5,
            "current_task": "task_1",
            "current_turn": 3
        }
        
        await handler.broadcast_evaluation_progress(evaluation_id, progress_data)
        
        # Verify message was sent
        mock_websocket.send_text.assert_called_once()
        sent_message = json.loads(mock_websocket.send_text.call_args[0][0])
        
        assert sent_message["type"] == "evaluation_progress"
        assert sent_message["evaluation_id"] == evaluation_id
        assert sent_message["data"] == progress_data
    
    @pytest.mark.asyncio
    async def test_broadcast_turn_executed(self):
        """Test broadcasting turn execution."""
        from ..api.websocket_handler import WebSocketHandler, WebSocketConnection
        
        handler = WebSocketHandler()
        
        # Mock WebSocket connection
        mock_websocket = AsyncMock()
        connection = WebSocketConnection(mock_websocket, "conn_1", "user_1")
        handler.connections["conn_1"] = connection
        
        # Add subscription
        evaluation_id = "eval_123"
        handler.evaluation_subscribers[evaluation_id] = {"conn_1"}
        connection.add_subscription(f"evaluation:{evaluation_id}")
        
        # Broadcast turn execution
        turn_data = {
            "turn_number": 3,
            "action": {"type": "code_execution", "code": "print('hello')"},
            "observation": {"stdout": "hello\n", "stderr": ""},
            "reward": 1.0
        }
        
        await handler.broadcast_turn_executed(evaluation_id, turn_data)
        
        # Verify message was sent
        mock_websocket.send_text.assert_called_once()
        sent_message = json.loads(mock_websocket.send_text.call_args[0][0])
        
        assert sent_message["type"] == "turn_executed"
        assert sent_message["evaluation_id"] == evaluation_id
        assert sent_message["data"] == turn_data
    
    @pytest.mark.asyncio
    async def test_broadcast_safety_incident(self):
        """Test broadcasting safety incident."""
        from ..api.websocket_handler import WebSocketHandler, WebSocketConnection
        
        handler = WebSocketHandler()
        
        # Mock WebSocket connection
        mock_websocket = AsyncMock()
        connection = WebSocketConnection(mock_websocket, "conn_1", "user_1")
        handler.connections["conn_1"] = connection
        
        # Add subscription
        evaluation_id = "eval_123"
        handler.evaluation_subscribers[evaluation_id] = {"conn_1"}
        connection.add_subscription(f"evaluation:{evaluation_id}")
        
        # Broadcast safety incident
        incident_data = {
            "incident_type": "dangerous_command",
            "command": "rm -rf /",
            "severity": "high",
            "action_taken": "blocked"
        }
        
        await handler.broadcast_safety_incident(evaluation_id, incident_data)
        
        # Verify message was sent
        mock_websocket.send_text.assert_called_once()
        sent_message = json.loads(mock_websocket.send_text.call_args[0][0])
        
        assert sent_message["type"] == "safety_incident"
        assert sent_message["evaluation_id"] == evaluation_id
        assert sent_message["data"] == incident_data


if __name__ == "__main__":
    pytest.main([__file__])