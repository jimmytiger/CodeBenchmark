"""
WebSocket Manager for Real-time Communication

Implements WebSocket interfaces for progress monitoring, live updates,
and real-time metrics streaming.
"""

from fastapi import WebSocket, WebSocketDisconnect
from typing import Dict, List, Any, Optional, Set
import json
import asyncio
import logging
from datetime import datetime
import uuid

from .models import WebSocketMessage, SystemHealth
from .auth import AuthManager

logger = logging.getLogger(__name__)


class ConnectionManager:
    """Manages WebSocket connections and message broadcasting."""
    
    def __init__(self):
        # Active connections by connection ID
        self.active_connections: Dict[str, WebSocket] = {}
        
        # User connections mapping
        self.user_connections: Dict[str, Set[str]] = {}  # user_id -> connection_ids
        
        # Evaluation subscriptions
        self.evaluation_subscriptions: Dict[str, Set[str]] = {}  # evaluation_id -> connection_ids
        
        # System monitoring subscriptions
        self.system_monitoring_subscriptions: Set[str] = set()
        
        # Connection metadata
        self.connection_metadata: Dict[str, Dict[str, Any]] = {}
    
    async def connect(self, websocket: WebSocket, user_id: str, 
                     connection_metadata: Optional[Dict[str, Any]] = None) -> str:
        """Accept WebSocket connection and register it."""
        await websocket.accept()
        
        # Generate connection ID
        connection_id = str(uuid.uuid4())
        
        # Store connection
        self.active_connections[connection_id] = websocket
        
        # Associate with user
        if user_id not in self.user_connections:
            self.user_connections[user_id] = set()
        self.user_connections[user_id].add(connection_id)
        
        # Store metadata
        self.connection_metadata[connection_id] = {
            "user_id": user_id,
            "connected_at": datetime.utcnow(),
            "last_activity": datetime.utcnow(),
            **(connection_metadata or {})
        }
        
        logger.info(f"WebSocket connection established: {connection_id} for user {user_id}")
        return connection_id
    
    def disconnect(self, connection_id: str):
        """Remove WebSocket connection."""
        if connection_id in self.active_connections:
            # Get user ID
            metadata = self.connection_metadata.get(connection_id, {})
            user_id = metadata.get("user_id")
            
            # Remove from active connections
            del self.active_connections[connection_id]
            
            # Remove from user connections
            if user_id and user_id in self.user_connections:
                self.user_connections[user_id].discard(connection_id)
                if not self.user_connections[user_id]:
                    del self.user_connections[user_id]
            
            # Remove from evaluation subscriptions
            for evaluation_id, subscribers in self.evaluation_subscriptions.items():
                subscribers.discard(connection_id)
            
            # Remove from system monitoring
            self.system_monitoring_subscriptions.discard(connection_id)
            
            # Remove metadata
            if connection_id in self.connection_metadata:
                del self.connection_metadata[connection_id]
            
            logger.info(f"WebSocket connection closed: {connection_id}")
    
    async def send_personal_message(self, message: Dict[str, Any], connection_id: str):
        """Send message to specific connection."""
        if connection_id in self.active_connections:
            try:
                websocket = self.active_connections[connection_id]
                await websocket.send_text(json.dumps(message))
                
                # Update last activity
                if connection_id in self.connection_metadata:
                    self.connection_metadata[connection_id]["last_activity"] = datetime.utcnow()
                    
            except Exception as e:
                logger.error(f"Error sending message to {connection_id}: {str(e)}")
                self.disconnect(connection_id)
    
    async def send_to_user(self, message: Dict[str, Any], user_id: str):
        """Send message to all connections of a specific user."""
        if user_id in self.user_connections:
            connection_ids = list(self.user_connections[user_id])
            for connection_id in connection_ids:
                await self.send_personal_message(message, connection_id)
    
    async def broadcast(self, message: Dict[str, Any]):
        """Broadcast message to all active connections."""
        if self.active_connections:
            connection_ids = list(self.active_connections.keys())
            for connection_id in connection_ids:
                await self.send_personal_message(message, connection_id)
    
    async def broadcast_to_subscribers(self, message: Dict[str, Any], 
                                     subscriber_ids: Set[str]):
        """Broadcast message to specific subscribers."""
        for connection_id in list(subscriber_ids):
            await self.send_personal_message(message, connection_id)
    
    def subscribe_to_evaluation(self, connection_id: str, evaluation_id: str):
        """Subscribe connection to evaluation updates."""
        if evaluation_id not in self.evaluation_subscriptions:
            self.evaluation_subscriptions[evaluation_id] = set()
        
        self.evaluation_subscriptions[evaluation_id].add(connection_id)
        logger.info(f"Connection {connection_id} subscribed to evaluation {evaluation_id}")
    
    def unsubscribe_from_evaluation(self, connection_id: str, evaluation_id: str):
        """Unsubscribe connection from evaluation updates."""
        if evaluation_id in self.evaluation_subscriptions:
            self.evaluation_subscriptions[evaluation_id].discard(connection_id)
            
            # Clean up empty subscriptions
            if not self.evaluation_subscriptions[evaluation_id]:
                del self.evaluation_subscriptions[evaluation_id]
    
    def subscribe_to_system_monitoring(self, connection_id: str):
        """Subscribe connection to system monitoring updates."""
        self.system_monitoring_subscriptions.add(connection_id)
        logger.info(f"Connection {connection_id} subscribed to system monitoring")
    
    def unsubscribe_from_system_monitoring(self, connection_id: str):
        """Unsubscribe connection from system monitoring updates."""
        self.system_monitoring_subscriptions.discard(connection_id)
    
    def get_connection_count(self) -> int:
        """Get total number of active connections."""
        return len(self.active_connections)
    
    def get_user_connection_count(self, user_id: str) -> int:
        """Get number of connections for specific user."""
        return len(self.user_connections.get(user_id, set()))


class WebSocketManager:
    """
    WebSocket manager for real-time communication.
    
    Implements requirement 11.2: WebSocket interfaces for progress monitoring,
    real-time metrics streaming, and system health monitoring.
    """
    
    def __init__(self, auth_manager: Optional[AuthManager] = None):
        self.connection_manager = ConnectionManager()
        self.auth_manager = auth_manager
        
        # System monitoring task
        self.system_monitoring_task: Optional[asyncio.Task] = None
        self.system_monitoring_interval = 30  # seconds
        
        # Message queue for reliable delivery
        self.message_queue: Dict[str, List[Dict[str, Any]]] = {}
    
    async def connect_websocket(self, websocket: WebSocket, token: str) -> Optional[str]:
        """
        Handle WebSocket connection with authentication.
        
        Implements requirement 11.4: Authentication for WebSocket connections.
        """
        try:
            # Validate authentication token
            user = None
            if self.auth_manager:
                user = await self.auth_manager.validate_token(token)
                if not user:
                    await websocket.close(code=4001, reason="Invalid authentication")
                    return None
            
            # Accept connection
            user_id = user["user_id"] if user else "anonymous"
            connection_id = await self.connection_manager.connect(
                websocket, user_id, {"authenticated": user is not None}
            )
            
            # Send welcome message
            welcome_message = {
                "type": "connection_established",
                "connection_id": connection_id,
                "user_id": user_id,
                "timestamp": datetime.utcnow().isoformat()
            }
            await self.connection_manager.send_personal_message(welcome_message, connection_id)
            
            # Start system monitoring if first connection
            if self.connection_manager.get_connection_count() == 1:
                await self.start_system_monitoring()
            
            return connection_id
            
        except Exception as e:
            logger.error(f"Error connecting WebSocket: {str(e)}")
            await websocket.close(code=4000, reason="Connection error")
            return None
    
    async def disconnect_websocket(self, connection_id: str):
        """Handle WebSocket disconnection."""
        self.connection_manager.disconnect(connection_id)
        
        # Stop system monitoring if no connections
        if self.connection_manager.get_connection_count() == 0:
            await self.stop_system_monitoring()
    
    async def handle_websocket_message(self, connection_id: str, message: str):
        """
        Handle incoming WebSocket message.
        
        Supports subscription management and real-time interaction.
        """
        try:
            data = json.loads(message)
            message_type = data.get("type")
            
            if message_type == "subscribe_evaluation":
                evaluation_id = data.get("evaluation_id")
                if evaluation_id:
                    self.connection_manager.subscribe_to_evaluation(connection_id, evaluation_id)
                    await self.send_subscription_confirmation(connection_id, "evaluation", evaluation_id)
            
            elif message_type == "unsubscribe_evaluation":
                evaluation_id = data.get("evaluation_id")
                if evaluation_id:
                    self.connection_manager.unsubscribe_from_evaluation(connection_id, evaluation_id)
                    await self.send_unsubscription_confirmation(connection_id, "evaluation", evaluation_id)
            
            elif message_type == "subscribe_system_monitoring":
                self.connection_manager.subscribe_to_system_monitoring(connection_id)
                await self.send_subscription_confirmation(connection_id, "system_monitoring", None)
            
            elif message_type == "unsubscribe_system_monitoring":
                self.connection_manager.unsubscribe_from_system_monitoring(connection_id)
                await self.send_unsubscription_confirmation(connection_id, "system_monitoring", None)
            
            elif message_type == "ping":
                await self.send_pong(connection_id)
            
            else:
                logger.warning(f"Unknown message type: {message_type}")
                
        except json.JSONDecodeError:
            logger.error(f"Invalid JSON message from {connection_id}: {message}")
        except Exception as e:
            logger.error(f"Error handling WebSocket message: {str(e)}")
    
    async def broadcast_evaluation_update(self, evaluation_id: str, update_data: Dict[str, Any]):
        """
        Broadcast evaluation progress update to subscribers.
        
        Implements requirement 11.2: Real-time progress monitoring.
        """
        message = WebSocketMessage(
            type="evaluation_update",
            evaluation_id=evaluation_id,
            data=update_data
        )
        
        # Get subscribers
        subscribers = self.connection_manager.evaluation_subscriptions.get(evaluation_id, set())
        
        if subscribers:
            await self.connection_manager.broadcast_to_subscribers(
                message.dict(), subscribers
            )
            logger.debug(f"Broadcasted evaluation update to {len(subscribers)} subscribers")
    
    async def broadcast_system_health(self, health_data: SystemHealth):
        """
        Broadcast system health information to monitoring subscribers.
        
        Implements requirement 11.2: System health monitoring.
        """
        message = WebSocketMessage(
            type="system_health",
            data=health_data.dict()
        )
        
        if self.connection_manager.system_monitoring_subscriptions:
            await self.connection_manager.broadcast_to_subscribers(
                message.dict(), 
                self.connection_manager.system_monitoring_subscriptions
            )
    
    async def send_notification(self, user_id: str, notification_data: Dict[str, Any]):
        """
        Send notification to specific user.
        
        Implements requirement 11.2: Notification system.
        """
        message = WebSocketMessage(
            type="notification",
            data=notification_data
        )
        
        await self.connection_manager.send_to_user(message.dict(), user_id)
    
    async def broadcast_alert(self, alert_data: Dict[str, Any], severity: str = "info"):
        """
        Broadcast system alert to all connected users.
        
        Implements requirement 11.2: Alert broadcasting.
        """
        message = WebSocketMessage(
            type="system_alert",
            data={
                "severity": severity,
                **alert_data
            }
        )
        
        await self.connection_manager.broadcast(message.dict())
    
    async def send_subscription_confirmation(self, connection_id: str, 
                                           subscription_type: str, 
                                           subscription_id: Optional[str]):
        """Send subscription confirmation message."""
        message = {
            "type": "subscription_confirmed",
            "subscription_type": subscription_type,
            "subscription_id": subscription_id,
            "timestamp": datetime.utcnow().isoformat()
        }
        await self.connection_manager.send_personal_message(message, connection_id)
    
    async def send_unsubscription_confirmation(self, connection_id: str, 
                                             subscription_type: str, 
                                             subscription_id: Optional[str]):
        """Send unsubscription confirmation message."""
        message = {
            "type": "unsubscription_confirmed",
            "subscription_type": subscription_type,
            "subscription_id": subscription_id,
            "timestamp": datetime.utcnow().isoformat()
        }
        await self.connection_manager.send_personal_message(message, connection_id)
    
    async def send_pong(self, connection_id: str):
        """Send pong response to ping."""
        message = {
            "type": "pong",
            "timestamp": datetime.utcnow().isoformat()
        }
        await self.connection_manager.send_personal_message(message, connection_id)
    
    async def start_system_monitoring(self):
        """Start system monitoring task."""
        if not self.system_monitoring_task or self.system_monitoring_task.done():
            self.system_monitoring_task = asyncio.create_task(self._system_monitoring_loop())
            logger.info("Started system monitoring")
    
    async def stop_system_monitoring(self):
        """Stop system monitoring task."""
        if self.system_monitoring_task and not self.system_monitoring_task.done():
            self.system_monitoring_task.cancel()
            try:
                await self.system_monitoring_task
            except asyncio.CancelledError:
                pass
            logger.info("Stopped system monitoring")
    
    async def _system_monitoring_loop(self):
        """System monitoring loop that broadcasts health updates."""
        while True:
            try:
                # Get system health data
                health_data = await self._get_system_health()
                
                # Broadcast to subscribers
                await self.broadcast_system_health(health_data)
                
                # Wait for next interval
                await asyncio.sleep(self.system_monitoring_interval)
                
            except asyncio.CancelledError:
                break
            except Exception as e:
                logger.error(f"Error in system monitoring loop: {str(e)}")
                await asyncio.sleep(self.system_monitoring_interval)
    
    async def _get_system_health(self) -> SystemHealth:
        """Get current system health metrics."""
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
    
    def get_connection_stats(self) -> Dict[str, Any]:
        """Get WebSocket connection statistics."""
        return {
            "total_connections": self.connection_manager.get_connection_count(),
            "unique_users": len(self.connection_manager.user_connections),
            "evaluation_subscriptions": len(self.connection_manager.evaluation_subscriptions),
            "system_monitoring_subscriptions": len(self.connection_manager.system_monitoring_subscriptions)
        }