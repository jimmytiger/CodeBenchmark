"""
API Endpoints Router

Defines all REST API endpoints for the evaluation engine.
Implements comprehensive API documentation with OpenAPI/Swagger integration.
"""

from fastapi import APIRouter, Depends, HTTPException, Query, Path, WebSocket, WebSocketDisconnect
from fastapi.security import HTTPBearer, HTTPAuthorizationCredentials
from typing import List, Dict, Any, Optional
import logging
from datetime import datetime

from .models import *
from .auth import AuthManager, PermissionChecker
from .websocket import WebSocketManager

logger = logging.getLogger(__name__)

# Create router
router = APIRouter()

# Initialize components (these would be injected in production)
auth_manager = AuthManager()
websocket_manager = WebSocketManager(auth_manager)
permission_checker = PermissionChecker(auth_manager)

# Security scheme
security = HTTPBearer()


# Authentication Endpoints
@router.post("/auth/login", response_model=AuthToken, tags=["Authentication"])
async def login(username: str, password: str):
    """
    Authenticate user and return JWT token.
    
    Implements requirement 11.4: Authentication with JWT.
    """
    try:
        auth_token = auth_manager.login(username, password)
        if not auth_token:
            raise HTTPException(status_code=401, detail="Invalid credentials")
        
        return auth_token
        
    except Exception as e:
        logger.error(f"Login error: {str(e)}")
        raise HTTPException(status_code=500, detail="Authentication failed")


@router.post("/auth/refresh", tags=["Authentication"])
async def refresh_token(refresh_token: str):
    """
    Refresh access token using refresh token.
    
    Implements requirement 11.4: Token refresh mechanism.
    """
    try:
        new_access_token = auth_manager.refresh_access_token(refresh_token)
        if not new_access_token:
            raise HTTPException(status_code=401, detail="Invalid refresh token")
        
        return {
            "access_token": new_access_token,
            "token_type": "bearer",
            "expires_in": int(auth_manager.token_expiry.total_seconds())
        }
        
    except Exception as e:
        logger.error(f"Token refresh error: {str(e)}")
        raise HTTPException(status_code=500, detail="Token refresh failed")


@router.post("/auth/logout", tags=["Authentication"])
async def logout(refresh_token: str):
    """
    Logout user by invalidating refresh token.
    
    Implements requirement 11.4: Secure logout.
    """
    try:
        success = auth_manager.logout(refresh_token)
        if not success:
            raise HTTPException(status_code=400, detail="Invalid refresh token")
        
        return {"message": "Logged out successfully"}
        
    except Exception as e:
        logger.error(f"Logout error: {str(e)}")
        raise HTTPException(status_code=500, detail="Logout failed")


# User Management Endpoints (Admin only)
@router.get("/users", response_model=List[UserInfo], tags=["User Management"])
async def list_users(
    current_user: dict = Depends(permission_checker.require_permission("user:manage"))
):
    """
    List all users (admin only).
    
    Implements requirement 11.4: Role-based access control.
    """
    try:
        users = auth_manager.get_all_users()
        return users
        
    except Exception as e:
        logger.error(f"Error listing users: {str(e)}")
        raise HTTPException(status_code=500, detail="Failed to list users")


@router.get("/users/{user_id}", response_model=UserInfo, tags=["User Management"])
async def get_user(
    user_id: str = Path(..., description="User ID"),
    current_user: dict = Depends(permission_checker.require_permission("user:manage"))
):
    """
    Get user information by ID (admin only).
    
    Implements requirement 11.4: User information access control.
    """
    try:
        user_info = auth_manager.get_user_info(user_id)
        if not user_info:
            raise HTTPException(status_code=404, detail="User not found")
        
        return user_info
        
    except HTTPException:
        raise
    except Exception as e:
        logger.error(f"Error getting user: {str(e)}")
        raise HTTPException(status_code=500, detail="Failed to get user")


@router.put("/users/{user_id}/roles", tags=["User Management"])
async def update_user_roles(
    user_id: str = Path(..., description="User ID"),
    roles: List[str] = ...,
    current_user: dict = Depends(permission_checker.require_permission("user:manage"))
):
    """
    Update user roles (admin only).
    
    Implements requirement 11.4: Role management.
    """
    try:
        success = auth_manager.update_user_roles(user_id, roles)
        if not success:
            raise HTTPException(status_code=404, detail="User not found")
        
        return {"message": "User roles updated successfully"}
        
    except HTTPException:
        raise
    except Exception as e:
        logger.error(f"Error updating user roles: {str(e)}")
        raise HTTPException(status_code=500, detail="Failed to update user roles")


@router.delete("/users/{user_id}", tags=["User Management"])
async def deactivate_user(
    user_id: str = Path(..., description="User ID"),
    current_user: dict = Depends(permission_checker.require_permission("user:manage"))
):
    """
    Deactivate user account (admin only).
    
    Implements requirement 11.4: User account management.
    """
    try:
        success = auth_manager.deactivate_user(user_id)
        if not success:
            raise HTTPException(status_code=404, detail="User not found")
        
        return {"message": "User deactivated successfully"}
        
    except HTTPException:
        raise
    except Exception as e:
        logger.error(f"Error deactivating user: {str(e)}")
        raise HTTPException(status_code=500, detail="Failed to deactivate user")


# System Health and Monitoring
@router.get("/system/health", response_model=SystemHealth, tags=["System"])
async def get_system_health():
    """
    Get system health status.
    
    Implements requirement 11.6: System health monitoring.
    """
    try:
        import psutil
        
        # Get system metrics
        cpu_percent = psutil.cpu_percent(interval=1)
        memory = psutil.virtual_memory()
        disk = psutil.disk_usage('/')
        
        return SystemHealth(
            status="healthy" if cpu_percent < 80 and memory.percent < 80 else "warning",
            active_evaluations=0,  # This would be populated from evaluation manager
            system_load=cpu_percent,
            memory_usage=memory.percent,
            disk_usage=disk.percent,
            uptime=0.0  # This would be calculated from startup time
        )
        
    except Exception as e:
        logger.error(f"Error getting system health: {str(e)}")
        raise HTTPException(status_code=500, detail="Failed to get system health")


@router.get("/system/stats", tags=["System"])
async def get_system_stats(
    current_user: dict = Depends(permission_checker.require_permission("system:monitor"))
):
    """
    Get detailed system statistics (admin only).
    
    Implements requirement 11.6: Detailed system monitoring.
    """
    try:
        # Get WebSocket connection stats
        ws_stats = websocket_manager.get_connection_stats()
        
        # Get system stats
        import psutil
        
        return {
            "websocket_connections": ws_stats,
            "system_resources": {
                "cpu_count": psutil.cpu_count(),
                "memory_total": psutil.virtual_memory().total,
                "disk_total": psutil.disk_usage('/').total,
                "boot_time": psutil.boot_time()
            },
            "process_info": {
                "pid": psutil.Process().pid,
                "memory_info": psutil.Process().memory_info()._asdict(),
                "cpu_percent": psutil.Process().cpu_percent()
            }
        }
        
    except Exception as e:
        logger.error(f"Error getting system stats: {str(e)}")
        raise HTTPException(status_code=500, detail="Failed to get system stats")


# Export and Integration Endpoints
@router.post("/export", tags=["Export"])
async def export_results(
    request: ExportRequest,
    current_user: dict = Depends(permission_checker.require_permission("analytics:read"))
):
    """
    Export evaluation results in various formats.
    
    Implements requirement 11.5: Data export in multiple formats.
    """
    try:
        # Validate export format
        supported_formats = ["json", "csv", "pdf", "xlsx"]
        if request.format not in supported_formats:
            raise HTTPException(
                status_code=400, 
                detail=f"Unsupported format. Supported formats: {supported_formats}"
            )
        
        # This would integrate with the actual export functionality
        # For now, return a placeholder response
        return {
            "export_id": "export_123",
            "status": "processing",
            "format": request.format,
            "evaluation_count": len(request.evaluation_ids),
            "estimated_completion": datetime.utcnow().isoformat()
        }
        
    except HTTPException:
        raise
    except Exception as e:
        logger.error(f"Error exporting results: {str(e)}")
        raise HTTPException(status_code=500, detail="Export failed")


@router.get("/export/{export_id}/status", tags=["Export"])
async def get_export_status(
    export_id: str = Path(..., description="Export ID"),
    current_user: dict = Depends(permission_checker.require_permission("analytics:read"))
):
    """
    Get export status and download link.
    
    Implements requirement 11.5: Export status tracking.
    """
    try:
        # This would check the actual export status
        # For now, return a placeholder response
        return {
            "export_id": export_id,
            "status": "completed",
            "download_url": f"/export/{export_id}/download",
            "file_size": 1024000,
            "expires_at": datetime.utcnow().isoformat()
        }
        
    except Exception as e:
        logger.error(f"Error getting export status: {str(e)}")
        raise HTTPException(status_code=500, detail="Failed to get export status")


# WebSocket Endpoint
@router.websocket("/ws")
async def websocket_endpoint(websocket: WebSocket, token: str = Query(...)):
    """
    WebSocket endpoint for real-time communication.
    
    Implements requirement 11.2: WebSocket interfaces for progress monitoring
    and real-time updates.
    """
    connection_id = None
    try:
        # Connect WebSocket with authentication
        connection_id = await websocket_manager.connect_websocket(websocket, token)
        if not connection_id:
            return
        
        # Handle messages
        while True:
            try:
                # Receive message
                message = await websocket.receive_text()
                
                # Handle message
                await websocket_manager.handle_websocket_message(connection_id, message)
                
            except WebSocketDisconnect:
                break
            except Exception as e:
                logger.error(f"Error handling WebSocket message: {str(e)}")
                break
                
    except Exception as e:
        logger.error(f"WebSocket error: {str(e)}")
    finally:
        # Clean up connection
        if connection_id:
            await websocket_manager.disconnect_websocket(connection_id)


# Notification Management
@router.get("/notifications/settings", response_model=NotificationSettings, tags=["Notifications"])
async def get_notification_settings(
    current_user: dict = Depends(security)
):
    """
    Get user notification settings.
    
    Implements requirement 11.2: Notification system configuration.
    """
    try:
        # This would retrieve actual user notification settings
        # For now, return default settings
        return NotificationSettings(
            email_notifications=True,
            webhook_url=None,
            notification_types=["evaluation_completed", "evaluation_failed", "system_alerts"],
            quiet_hours={"start": "22:00", "end": "08:00"}
        )
        
    except Exception as e:
        logger.error(f"Error getting notification settings: {str(e)}")
        raise HTTPException(status_code=500, detail="Failed to get notification settings")


@router.put("/notifications/settings", tags=["Notifications"])
async def update_notification_settings(
    settings: NotificationSettings,
    current_user: dict = Depends(security)
):
    """
    Update user notification settings.
    
    Implements requirement 11.2: Notification system configuration.
    """
    try:
        # This would update actual user notification settings
        # For now, return success response
        return {"message": "Notification settings updated successfully"}
        
    except Exception as e:
        logger.error(f"Error updating notification settings: {str(e)}")
        raise HTTPException(status_code=500, detail="Failed to update notification settings")


# API Documentation Endpoints
@router.get("/docs/openapi.json", tags=["Documentation"])
async def get_openapi_schema():
    """
    Get OpenAPI schema for API documentation.
    
    Implements requirement 11.1: API documentation with OpenAPI/Swagger integration.
    """
    from fastapi.openapi.utils import get_openapi
    from fastapi import FastAPI
    
    # This would return the actual OpenAPI schema
    # The FastAPI framework automatically generates this
    return {"message": "OpenAPI schema available at /openapi.json"}


@router.get("/docs/examples", tags=["Documentation"])
async def get_api_examples():
    """
    Get API usage examples and code samples.
    
    Implements requirement 11.1: Comprehensive API documentation.
    """
    return {
        "examples": {
            "create_evaluation": {
                "description": "Create a new evaluation",
                "request": {
                    "model_id": "gpt-4",
                    "task_ids": ["single_turn_scenarios_code_completion"],
                    "configuration": {
                        "temperature": 0.7,
                        "max_tokens": 1000
                    }
                },
                "curl": """curl -X POST "http://localhost:8000/evaluations" \\
     -H "Authorization: Bearer YOUR_TOKEN" \\
     -H "Content-Type: application/json" \\
     -d '{"model_id": "gpt-4", "task_ids": ["single_turn_scenarios_code_completion"]}'"""
            },
            "websocket_connection": {
                "description": "Connect to WebSocket for real-time updates",
                "javascript": """
const ws = new WebSocket('ws://localhost:8000/ws?token=YOUR_TOKEN');
ws.onmessage = function(event) {
    const data = JSON.parse(event.data);
    console.log('Received:', data);
};
ws.send(JSON.stringify({
    type: 'subscribe_evaluation',
    evaluation_id: 'eval_123'
}));"""
            }
        }
    }