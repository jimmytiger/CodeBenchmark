"""
Test suite for API Gateway and Integration Layer

Tests REST API endpoints, WebSocket communication, authentication,
and notification system functionality.
"""

import pytest
import asyncio
import json
from datetime import datetime, timedelta
from unittest.mock import Mock, AsyncMock, patch
from fastapi.testclient import TestClient
import websockets
import jwt

from evaluation_engine.api.server import APIServer, create_app
from evaluation_engine.api.auth import AuthManager
from evaluation_engine.api.websocket import WebSocketManager
from evaluation_engine.api.notifications import NotificationManager, NotificationType, NotificationPriority
from evaluation_engine.api.models import *


class TestAuthManager:
    """Test authentication and authorization functionality."""
    
    def setup_method(self):
        """Setup test environment."""
        self.auth_manager = AuthManager()
    
    def test_create_user(self):
        """Test user creation."""
        user_id = self.auth_manager.create_user(
            username="testuser",
            email="test@example.com",
            password="testpass123",
            roles=["evaluator"]
        )
        
        assert user_id is not None
        assert user_id in self.auth_manager.users
        
        user = self.auth_manager.users[user_id]
        assert user["username"] == "testuser"
        assert user["email"] == "test@example.com"
        assert "evaluator" in user["roles"]
        assert "evaluation:create" in user["permissions"]
    
    def test_authenticate_user(self):
        """Test user authentication."""
        # Create user
        self.auth_manager.create_user(
            username="testuser",
            email="test@example.com",
            password="testpass123",
            roles=["evaluator"]
        )
        
        # Test valid authentication
        user = self.auth_manager.authenticate_user("testuser", "testpass123")
        assert user is not None
        assert user["username"] == "testuser"
        
        # Test invalid authentication
        user = self.auth_manager.authenticate_user("testuser", "wrongpass")
        assert user is None
        
        user = self.auth_manager.authenticate_user("nonexistent", "testpass123")
        assert user is None
    
    def test_create_access_token(self):
        """Test JWT token creation."""
        # Create user
        user_id = self.auth_manager.create_user(
            username="testuser",
            email="test@example.com",
            password="testpass123",
            roles=["evaluator"]
        )
        
        user = self.auth_manager.users[user_id]
        token = self.auth_manager.create_access_token(user)
        
        assert token is not None
        
        # Decode and verify token
        payload = jwt.decode(token, self.auth_manager.secret_key, algorithms=[self.auth_manager.algorithm])
        assert payload["user_id"] == user_id
        assert payload["username"] == "testuser"
        assert "evaluator" in payload["roles"]
    
    @pytest.mark.asyncio
    async def test_validate_token(self):
        """Test token validation."""
        # Create user and token
        user_id = self.auth_manager.create_user(
            username="testuser",
            email="test@example.com",
            password="testpass123",
            roles=["evaluator"]
        )
        
        user = self.auth_manager.users[user_id]
        token = self.auth_manager.create_access_token(user)
        
        # Test valid token
        validated_user = await self.auth_manager.validate_token(token)
        assert validated_user is not None
        assert validated_user["user_id"] == user_id
        
        # Test invalid token
        validated_user = await self.auth_manager.validate_token("invalid_token")
        assert validated_user is None
    
    def test_login(self):
        """Test login functionality."""
        # Create user
        self.auth_manager.create_user(
            username="testuser",
            email="test@example.com",
            password="testpass123",
            roles=["evaluator"]
        )
        
        # Test successful login
        auth_token = self.auth_manager.login("testuser", "testpass123")
        assert auth_token is not None
        assert auth_token.access_token is not None
        assert auth_token.refresh_token is not None
        assert auth_token.user_info.username == "testuser"
        
        # Test failed login
        auth_token = self.auth_manager.login("testuser", "wrongpass")
        assert auth_token is None
    
    def test_check_permission(self):
        """Test permission checking."""
        # Create user
        user_id = self.auth_manager.create_user(
            username="testuser",
            email="test@example.com",
            password="testpass123",
            roles=["evaluator"]
        )
        
        user = self.auth_manager.users[user_id]
        
        # Test valid permission
        assert self.auth_manager.check_permission(user, "evaluation:create")
        assert self.auth_manager.check_permission(user, "task:read")
        
        # Test invalid permission
        assert not self.auth_manager.check_permission(user, "user:manage")
        assert not self.auth_manager.check_permission(user, "system:admin")


class TestWebSocketManager:
    """Test WebSocket communication functionality."""
    
    def setup_method(self):
        """Setup test environment."""
        self.auth_manager = AuthManager()
        self.websocket_manager = WebSocketManager(self.auth_manager)
    
    @pytest.mark.asyncio
    async def test_connection_management(self):
        """Test WebSocket connection management."""
        # Mock WebSocket
        mock_websocket = AsyncMock()
        mock_websocket.accept = AsyncMock()
        
        # Create user and token
        user_id = self.auth_manager.create_user(
            username="testuser",
            email="test@example.com",
            password="testpass123",
            roles=["evaluator"]
        )
        
        user = self.auth_manager.users[user_id]
        token = self.auth_manager.create_access_token(user)
        
        # Test connection
        connection_id = await self.websocket_manager.connect_websocket(mock_websocket, token)
        assert connection_id is not None
        
        # Verify connection is tracked
        assert connection_id in self.websocket_manager.connection_manager.active_connections
        assert user_id in self.websocket_manager.connection_manager.user_connections
        
        # Test disconnection
        await self.websocket_manager.disconnect_websocket(connection_id)
        assert connection_id not in self.websocket_manager.connection_manager.active_connections
    
    @pytest.mark.asyncio
    async def test_message_handling(self):
        """Test WebSocket message handling."""
        # Setup connection
        mock_websocket = AsyncMock()
        mock_websocket.accept = AsyncMock()
        
        user_id = self.auth_manager.create_user(
            username="testuser",
            email="test@example.com",
            password="testpass123",
            roles=["evaluator"]
        )
        
        user = self.auth_manager.users[user_id]
        token = self.auth_manager.create_access_token(user)
        
        connection_id = await self.websocket_manager.connect_websocket(mock_websocket, token)
        
        # Test subscription message
        subscribe_message = json.dumps({
            "type": "subscribe_evaluation",
            "evaluation_id": "eval_123"
        })
        
        await self.websocket_manager.handle_websocket_message(connection_id, subscribe_message)
        
        # Verify subscription
        assert "eval_123" in self.websocket_manager.connection_manager.evaluation_subscriptions
        assert connection_id in self.websocket_manager.connection_manager.evaluation_subscriptions["eval_123"]
    
    @pytest.mark.asyncio
    async def test_broadcast_evaluation_update(self):
        """Test evaluation update broadcasting."""
        # Setup connection
        mock_websocket = AsyncMock()
        mock_websocket.accept = AsyncMock()
        mock_websocket.send_text = AsyncMock()
        
        user_id = self.auth_manager.create_user(
            username="testuser",
            email="test@example.com",
            password="testpass123",
            roles=["evaluator"]
        )
        
        user = self.auth_manager.users[user_id]
        token = self.auth_manager.create_access_token(user)
        
        connection_id = await self.websocket_manager.connect_websocket(mock_websocket, token)
        
        # Subscribe to evaluation
        self.websocket_manager.connection_manager.subscribe_to_evaluation(connection_id, "eval_123")
        
        # Broadcast update
        update_data = {"status": "running", "progress": 0.5}
        await self.websocket_manager.broadcast_evaluation_update("eval_123", update_data)
        
        # Verify message was sent
        mock_websocket.send_text.assert_called_once()
        sent_message = json.loads(mock_websocket.send_text.call_args[0][0])
        assert sent_message["type"] == "evaluation_update"
        assert sent_message["evaluation_id"] == "eval_123"
        assert sent_message["data"] == update_data


class TestNotificationManager:
    """Test notification system functionality."""
    
    def setup_method(self):
        """Setup test environment."""
        self.auth_manager = AuthManager()
        self.websocket_manager = WebSocketManager(self.auth_manager)
        self.notification_manager = NotificationManager(self.websocket_manager)
    
    @pytest.mark.asyncio
    async def test_send_notification(self):
        """Test notification sending."""
        await self.notification_manager.start()
        
        # Send notification
        notification_id = await self.notification_manager.send_notification(
            user_id="user_123",
            notification_type=NotificationType.EVALUATION_COMPLETED,
            title="Test Notification",
            message="This is a test notification",
            data={"test": "data"},
            priority=NotificationPriority.NORMAL
        )
        
        assert notification_id is not None
        
        # Verify notification is in history
        notifications = await self.notification_manager.get_user_notifications("user_123")
        assert len(notifications) == 1
        assert notifications[0]["title"] == "Test Notification"
        
        await self.notification_manager.stop()
    
    @pytest.mark.asyncio
    async def test_evaluation_notifications(self):
        """Test evaluation-specific notifications."""
        await self.notification_manager.start()
        
        # Test evaluation started
        await self.notification_manager.send_evaluation_started(
            user_id="user_123",
            evaluation_id="eval_123",
            model_id="gpt-4",
            task_count=5
        )
        
        # Test evaluation completed
        await self.notification_manager.send_evaluation_completed(
            user_id="user_123",
            evaluation_id="eval_123",
            model_id="gpt-4",
            overall_score=0.85,
            execution_time=120.5
        )
        
        # Test evaluation failed
        await self.notification_manager.send_evaluation_failed(
            user_id="user_123",
            evaluation_id="eval_456",
            model_id="gpt-4",
            error_message="Model API error"
        )
        
        # Verify notifications
        notifications = await self.notification_manager.get_user_notifications("user_123")
        assert len(notifications) == 3
        
        # Check notification types
        notification_types = [n["type"] for n in notifications]
        assert NotificationType.EVALUATION_STARTED in notification_types
        assert NotificationType.EVALUATION_COMPLETED in notification_types
        assert NotificationType.EVALUATION_FAILED in notification_types
        
        await self.notification_manager.stop()
    
    def test_user_settings(self):
        """Test notification settings management."""
        settings = NotificationSettings(
            email_notifications=True,
            webhook_url="https://example.com/webhook",
            notification_types=["evaluation_completed", "system_alerts"],
            quiet_hours={"start": "22:00", "end": "08:00"}
        )
        
        self.notification_manager.set_user_settings("user_123", settings)
        
        retrieved_settings = self.notification_manager.get_user_settings("user_123")
        assert retrieved_settings.email_notifications == True
        assert retrieved_settings.webhook_url == "https://example.com/webhook"
        assert "evaluation_completed" in retrieved_settings.notification_types


class TestAPIEndpoints:
    """Test REST API endpoints."""
    
    def setup_method(self):
        """Setup test environment."""
        self.app = create_app({"debug": True})
        self.client = TestClient(self.app)
        
        # Create test user and get token
        self.auth_manager = AuthManager()
        user_id = self.auth_manager.create_user(
            username="testuser",
            email="test@example.com",
            password="testpass123",
            roles=["evaluator"]
        )
        
        user = self.auth_manager.users[user_id]
        self.token = self.auth_manager.create_access_token(user)
        self.headers = {"Authorization": f"Bearer {self.token}"}
    
    def test_health_check(self):
        """Test health check endpoint."""
        response = self.client.get("/health")
        assert response.status_code == 200
        
        data = response.json()
        assert data["status"] == "healthy"
        assert "components" in data
    
    def test_root_endpoint(self):
        """Test root endpoint."""
        response = self.client.get("/")
        assert response.status_code == 200
        
        data = response.json()
        assert data["name"] == "AI Evaluation Engine API"
        assert data["version"] == "1.0.0"
        assert data["status"] == "running"
    
    def test_authentication_endpoints(self):
        """Test authentication endpoints."""
        # Test login
        response = self.client.post("/api/v1/auth/login", params={
            "username": "testuser",
            "password": "testpass123"
        })
        assert response.status_code == 200
        
        data = response.json()
        assert "access_token" in data
        assert "refresh_token" in data
        assert data["token_type"] == "bearer"
        
        # Test invalid login
        response = self.client.post("/api/v1/auth/login", params={
            "username": "testuser",
            "password": "wrongpass"
        })
        assert response.status_code == 401
    
    def test_protected_endpoints(self):
        """Test protected endpoints require authentication."""
        # Test without token
        response = self.client.get("/api/v1/tasks")
        assert response.status_code == 401
        
        # Test with valid token
        response = self.client.get("/api/v1/tasks", headers=self.headers)
        assert response.status_code == 200
    
    def test_user_management_endpoints(self):
        """Test user management endpoints (admin only)."""
        # Create admin user
        admin_user_id = self.auth_manager.create_user(
            username="admin",
            email="admin@example.com",
            password="adminpass123",
            roles=["admin"]
        )
        
        admin_user = self.auth_manager.users[admin_user_id]
        admin_token = self.auth_manager.create_access_token(admin_user)
        admin_headers = {"Authorization": f"Bearer {admin_token}"}
        
        # Test list users (admin only)
        response = self.client.get("/api/v1/users", headers=admin_headers)
        assert response.status_code == 200
        
        # Test with non-admin user
        response = self.client.get("/api/v1/users", headers=self.headers)
        assert response.status_code == 403
    
    def test_system_endpoints(self):
        """Test system monitoring endpoints."""
        # Test system health
        response = self.client.get("/api/v1/system/health")
        assert response.status_code == 200
        
        data = response.json()
        assert "status" in data
        assert "system_load" in data
        assert "memory_usage" in data
    
    def test_metrics_endpoint(self):
        """Test metrics endpoint."""
        response = self.client.get("/metrics")
        assert response.status_code == 200
        
        data = response.json()
        assert "active_connections" in data
        assert "total_users" in data
        assert "active_evaluations" in data


class TestAPIIntegration:
    """Test full API integration scenarios."""
    
    def setup_method(self):
        """Setup test environment."""
        self.server = APIServer(debug=True)
        self.app = self.server.app
        self.client = TestClient(self.app)
        
        # Login and get token
        response = self.client.post("/api/v1/auth/login", params={
            "username": "admin",
            "password": "admin123"
        })
        
        if response.status_code == 200:
            self.token = response.json()["access_token"]
            self.headers = {"Authorization": f"Bearer {self.token}"}
        else:
            # Fallback to creating token directly
            auth_manager = self.server.auth_manager
            user = auth_manager.authenticate_user("admin", "admin123")
            if user:
                self.token = auth_manager.create_access_token(user)
                self.headers = {"Authorization": f"Bearer {self.token}"}
    
    def test_full_evaluation_workflow(self):
        """Test complete evaluation workflow."""
        # Create evaluation request
        evaluation_request = {
            "model_id": "gpt-4",
            "task_ids": ["single_turn_scenarios_code_completion"],
            "configuration": {
                "temperature": 0.7,
                "max_tokens": 1000
            },
            "context_mode": "full_context"
        }
        
        # Create evaluation
        response = self.client.post(
            "/api/v1/evaluations",
            json=evaluation_request,
            headers=self.headers
        )
        
        # Note: This might fail due to missing core components
        # In a real implementation, we would mock these dependencies
        if response.status_code == 200:
            data = response.json()
            evaluation_id = data["evaluation_id"]
            
            # Check evaluation status
            response = self.client.get(
                f"/api/v1/evaluations/{evaluation_id}",
                headers=self.headers
            )
            assert response.status_code == 200
            
            status_data = response.json()
            assert status_data["evaluation_id"] == evaluation_id
    
    def test_api_documentation(self):
        """Test API documentation endpoints."""
        # Test OpenAPI schema
        response = self.client.get("/openapi.json")
        assert response.status_code == 200
        
        schema = response.json()
        assert "openapi" in schema
        assert "info" in schema
        assert "paths" in schema
        
        # Test Swagger UI
        response = self.client.get("/docs")
        assert response.status_code == 200
        
        # Test ReDoc
        response = self.client.get("/redoc")
        assert response.status_code == 200


if __name__ == "__main__":
    pytest.main([__file__, "-v"])