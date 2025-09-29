"""
WebSocket Handler for Multi-Turn Evaluation

Provides real-time communication for evaluation progress monitoring,
turn-by-turn updates, and system notifications.
"""

import asyncio
import json
import logging
from typing import Dict, Set, Optional, Any, List
from datetime import datetime
from fastapi import WebSocket, WebSocketDisconnect
from pydantic import ValidationError

from .models import WebSocketMessage, SubscriptionRequest
from ..core.exceptions import EvaluationError

logger = logging.getLogger(__name__)


class WebSocketConnection:
    """Represents a WebSocket connection with metadata."""
    
    def __init__(self, websocket: WebSocket, connection_id: str, user_id: str):
        self.websocket = websocket
        self.connection_id = connection_id
        self.user_id = user_id
        self.connected_at = datetime.utcnow()
        self.subscriptions: Set[str] = set()
        self.last_ping = datetime.utcnow()
        self.is_active = True
    
    async def send_message(self, message: Dict[str, Any]):
        """Send message to WebSocket client."""
        try:
            await self.websocket.send_text(json.dumps(message, default=str))
        except Exception as e:
            logger.error(f"Error sending WebSocket message: {str(e)}")
            self.is_active = False
    
    async def send_error(self, error_type: str, message: str, details: Optional[Dict[str, Any]] = None):
        """Send error message to client."""
        error_message = {
            "type": "error",
            "error": error_type,
            "message": message,
            "details": details or {},
            "timestamp": datetime.utcnow().isoformat()
        }
        await self.send_message(error_message)
    
    def add_subscription(self, subscription_key: str):
        """Add subscription for this connection."""
        self.subscriptions.add(subscription_key)
    
    def remove_subscription(self, subscription_key: str):
        """Remove subscription for this connection."""
        self.subscriptions.discard(subscription_key)
    
    def has_subscription(self, subscription_key: str) -> bool:
        """Check if connection has specific subscription."""
        return subscription_key in self.subscriptions


class WebSocketHandler:
    """
    Handles WebSocket connections for multi-turn evaluation monitoring.
    
    Implements requirement 9.1: WebSocket support for real-time evaluation progress.
    """
    
    def __init__(self):
        self.connections: Dict[str, WebSocketConnection] = {}
        self.evaluation_subscribers: Dict[str, Set[str]] = {}  # evaluation_id -> connection_ids
        self.system_subscribers: Set[str] = set()  # connection_ids subscribed to system events
        self.connection_counter = 0
        self._cleanup_task: Optional[asyncio.Task] = None
        self._start_cleanup_task()
    
    def _start_cleanup_task(self):
        """Start background task for connection cleanup."""
        if self._cleanup_task is None or self._cleanup_task.done():
            self._cleanup_task = asyncio.create_task(self._cleanup_connections())
    
    async def _cleanup_connections(self):
        """Background task to cleanup inactive connections."""
        while True:
            try:
                await asyncio.sleep(30)  # Check every 30 seconds
                
                inactive_connections = []
                for conn_id, connection in self.connections.items():
                    if not connection.is_active:
                        inactive_connections.append(conn_id)
                    elif (datetime.utcnow() - connection.last_ping).total_seconds() > 300:  # 5 minutes timeout
                        logger.info(f"Connection {conn_id} timed out")
                        connection.is_active = False
                        inactive_connections.append(conn_id)
                
                # Remove inactive connections
                for conn_id in inactive_connections:
                    await self._remove_connection(conn_id)
                
            except Exception as e:
                logger.error(f"Error in connection cleanup: {str(e)}")
    
    async def connect(self, websocket: WebSocket, user_id: str) -> str:
        """
        Accept WebSocket connection and return connection ID.
        
        Args:
            websocket: FastAPI WebSocket instance
            user_id: Authenticated user ID
            
        Returns:
            Connection ID string
        """
        try:
            await websocket.accept()
            
            # Generate connection ID
            self.connection_counter += 1
            connection_id = f"ws_{self.connection_counter}_{user_id}_{int(datetime.utcnow().timestamp())}"
            
            # Create connection object
            connection = WebSocketConnection(websocket, connection_id, user_id)
            self.connections[connection_id] = connection
            
            # Send welcome message
            welcome_message = {
                "type": "connection_established",
                "connection_id": connection_id,
                "message": "WebSocket connection established",
                "timestamp": datetime.utcnow().isoformat(),
                "available_subscriptions": [
                    "evaluation_progress",
                    "evaluation_completed",
                    "turn_executed",
                    "safety_incident",
                    "system_status"
                ]
            }
            await connection.send_message(welcome_message)
            
            logger.info(f"WebSocket connection established: {connection_id} for user {user_id}")
            return connection_id
            
        except Exception as e:
            logger.error(f"Error establishing WebSocket connection: {str(e)}")
            raise
    
    async def disconnect(self, connection_id: str):
        """
        Disconnect WebSocket connection.
        
        Args:
            connection_id: Connection ID to disconnect
        """
        await self._remove_connection(connection_id)
    
    async def _remove_connection(self, connection_id: str):
        """Remove connection and clean up subscriptions."""
        if connection_id in self.connections:
            connection = self.connections[connection_id]
            
            # Remove from all subscriptions
            for subscription in connection.subscriptions.copy():
                await self._unsubscribe(connection_id, subscription)
            
            # Remove from system subscribers
            self.system_subscribers.discard(connection_id)
            
            # Remove connection
            del self.connections[connection_id]
            
            logger.info(f"WebSocket connection removed: {connection_id}")
    
    async def handle_message(self, connection_id: str, message: str):
        """
        Handle incoming WebSocket message.
        
        Args:
            connection_id: Connection ID
            message: JSON message string
        """
        if connection_id not in self.connections:
            logger.warning(f"Message received for unknown connection: {connection_id}")
            return
        
        connection = self.connections[connection_id]
        connection.last_ping = datetime.utcnow()
        
        try:
            # Parse message
            data = json.loads(message)
            message_type = data.get("type")
            
            if message_type == "ping":
                await self._handle_ping(connection)
            elif message_type == "subscribe":
                await self._handle_subscribe(connection, data)
            elif message_type == "unsubscribe":
                await self._handle_unsubscribe(connection, data)
            elif message_type == "get_status":
                await self._handle_get_status(connection, data)
            else:
                await connection.send_error("invalid_message_type", f"Unknown message type: {message_type}")
                
        except json.JSONDecodeError:
            await connection.send_error("invalid_json", "Invalid JSON message")
        except ValidationError as e:
            await connection.send_error("validation_error", "Message validation failed", {"details": str(e)})
        except Exception as e:
            logger.error(f"Error handling WebSocket message: {str(e)}")
            await connection.send_error("internal_error", "Internal server error")
    
    async def _handle_ping(self, connection: WebSocketConnection):
        """Handle ping message."""
        pong_message = {
            "type": "pong",
            "timestamp": datetime.utcnow().isoformat()
        }
        await connection.send_message(pong_message)
    
    async def _handle_subscribe(self, connection: WebSocketConnection, data: Dict[str, Any]):
        """Handle subscription request."""
        try:
            subscription_type = data.get("subscription_type")
            evaluation_id = data.get("evaluation_id")
            
            if subscription_type == "evaluation":
                if not evaluation_id:
                    await connection.send_error("missing_parameter", "evaluation_id required for evaluation subscription")
                    return
                
                # Subscribe to specific evaluation
                subscription_key = f"evaluation:{evaluation_id}"
                connection.add_subscription(subscription_key)
                
                if evaluation_id not in self.evaluation_subscribers:
                    self.evaluation_subscribers[evaluation_id] = set()
                self.evaluation_subscribers[evaluation_id].add(connection.connection_id)
                
                await connection.send_message({
                    "type": "subscription_confirmed",
                    "subscription_type": "evaluation",
                    "evaluation_id": evaluation_id,
                    "message": f"Subscribed to evaluation {evaluation_id}",
                    "timestamp": datetime.utcnow().isoformat()
                })
                
            elif subscription_type == "system":
                # Subscribe to system events
                subscription_key = "system:events"
                connection.add_subscription(subscription_key)
                self.system_subscribers.add(connection.connection_id)
                
                await connection.send_message({
                    "type": "subscription_confirmed",
                    "subscription_type": "system",
                    "message": "Subscribed to system events",
                    "timestamp": datetime.utcnow().isoformat()
                })
                
            else:
                await connection.send_error("invalid_subscription", f"Unknown subscription type: {subscription_type}")
                
        except Exception as e:
            logger.error(f"Error handling subscription: {str(e)}")
            await connection.send_error("subscription_error", "Failed to process subscription")
    
    async def _handle_unsubscribe(self, connection: WebSocketConnection, data: Dict[str, Any]):
        """Handle unsubscription request."""
        try:
            subscription_type = data.get("subscription_type")
            evaluation_id = data.get("evaluation_id")
            
            if subscription_type == "evaluation":
                if not evaluation_id:
                    await connection.send_error("missing_parameter", "evaluation_id required for evaluation unsubscription")
                    return
                
                await self._unsubscribe(connection.connection_id, f"evaluation:{evaluation_id}")
                
                await connection.send_message({
                    "type": "unsubscription_confirmed",
                    "subscription_type": "evaluation",
                    "evaluation_id": evaluation_id,
                    "message": f"Unsubscribed from evaluation {evaluation_id}",
                    "timestamp": datetime.utcnow().isoformat()
                })
                
            elif subscription_type == "system":
                await self._unsubscribe(connection.connection_id, "system:events")
                
                await connection.send_message({
                    "type": "unsubscription_confirmed",
                    "subscription_type": "system",
                    "message": "Unsubscribed from system events",
                    "timestamp": datetime.utcnow().isoformat()
                })
                
        except Exception as e:
            logger.error(f"Error handling unsubscription: {str(e)}")
            await connection.send_error("unsubscription_error", "Failed to process unsubscription")
    
    async def _unsubscribe(self, connection_id: str, subscription_key: str):
        """Remove subscription for connection."""
        if connection_id in self.connections:
            connection = self.connections[connection_id]
            connection.remove_subscription(subscription_key)
        
        # Remove from evaluation subscribers
        if subscription_key.startswith("evaluation:"):
            evaluation_id = subscription_key.split(":", 1)[1]
            if evaluation_id in self.evaluation_subscribers:
                self.evaluation_subscribers[evaluation_id].discard(connection_id)
                if not self.evaluation_subscribers[evaluation_id]:
                    del self.evaluation_subscribers[evaluation_id]
        
        # Remove from system subscribers
        elif subscription_key == "system:events":
            self.system_subscribers.discard(connection_id)
    
    async def _handle_get_status(self, connection: WebSocketConnection, data: Dict[str, Any]):
        """Handle status request."""
        try:
            status_type = data.get("status_type", "connection")
            
            if status_type == "connection":
                status_message = {
                    "type": "status_response",
                    "status_type": "connection",
                    "data": {
                        "connection_id": connection.connection_id,
                        "user_id": connection.user_id,
                        "connected_at": connection.connected_at.isoformat(),
                        "subscriptions": list(connection.subscriptions),
                        "is_active": connection.is_active
                    },
                    "timestamp": datetime.utcnow().isoformat()
                }
                await connection.send_message(status_message)
                
            elif status_type == "system":
                status_message = {
                    "type": "status_response",
                    "status_type": "system",
                    "data": {
                        "total_connections": len(self.connections),
                        "active_connections": sum(1 for conn in self.connections.values() if conn.is_active),
                        "total_subscriptions": sum(len(conn.subscriptions) for conn in self.connections.values()),
                        "evaluation_subscriptions": len(self.evaluation_subscribers),
                        "system_subscriptions": len(self.system_subscribers)
                    },
                    "timestamp": datetime.utcnow().isoformat()
                }
                await connection.send_message(status_message)
                
        except Exception as e:
            logger.error(f"Error handling status request: {str(e)}")
            await connection.send_error("status_error", "Failed to get status")
    
    # Event broadcasting methods
    
    async def broadcast_evaluation_progress(self, evaluation_id: str, progress_data: Dict[str, Any]):
        """
        Broadcast evaluation progress to subscribers.
        
        Args:
            evaluation_id: Evaluation ID
            progress_data: Progress information
        """
        if evaluation_id not in self.evaluation_subscribers:
            return
        
        message = {
            "type": "evaluation_progress",
            "evaluation_id": evaluation_id,
            "data": progress_data,
            "timestamp": datetime.utcnow().isoformat()
        }
        
        await self._broadcast_to_subscribers(self.evaluation_subscribers[evaluation_id], message)
    
    async def broadcast_turn_executed(self, evaluation_id: str, turn_data: Dict[str, Any]):
        """
        Broadcast turn execution to subscribers.
        
        Args:
            evaluation_id: Evaluation ID
            turn_data: Turn execution data
        """
        if evaluation_id not in self.evaluation_subscribers:
            return
        
        message = {
            "type": "turn_executed",
            "evaluation_id": evaluation_id,
            "data": turn_data,
            "timestamp": datetime.utcnow().isoformat()
        }
        
        await self._broadcast_to_subscribers(self.evaluation_subscribers[evaluation_id], message)
    
    async def broadcast_evaluation_completed(self, evaluation_id: str, results_data: Dict[str, Any]):
        """
        Broadcast evaluation completion to subscribers.
        
        Args:
            evaluation_id: Evaluation ID
            results_data: Evaluation results
        """
        if evaluation_id not in self.evaluation_subscribers:
            return
        
        message = {
            "type": "evaluation_completed",
            "evaluation_id": evaluation_id,
            "data": results_data,
            "timestamp": datetime.utcnow().isoformat()
        }
        
        await self._broadcast_to_subscribers(self.evaluation_subscribers[evaluation_id], message)
    
    async def broadcast_safety_incident(self, evaluation_id: str, incident_data: Dict[str, Any]):
        """
        Broadcast safety incident to subscribers.
        
        Args:
            evaluation_id: Evaluation ID
            incident_data: Safety incident information
        """
        if evaluation_id not in self.evaluation_subscribers:
            return
        
        message = {
            "type": "safety_incident",
            "evaluation_id": evaluation_id,
            "data": incident_data,
            "timestamp": datetime.utcnow().isoformat()
        }
        
        await self._broadcast_to_subscribers(self.evaluation_subscribers[evaluation_id], message)
    
    async def broadcast_system_event(self, event_data: Dict[str, Any]):
        """
        Broadcast system event to system subscribers.
        
        Args:
            event_data: System event data
        """
        message = {
            "type": "system_event",
            "data": event_data,
            "timestamp": datetime.utcnow().isoformat()
        }
        
        await self._broadcast_to_subscribers(self.system_subscribers, message)
    
    async def _broadcast_to_subscribers(self, subscriber_ids: Set[str], message: Dict[str, Any]):
        """
        Broadcast message to specific subscribers.
        
        Args:
            subscriber_ids: Set of connection IDs
            message: Message to broadcast
        """
        if not subscriber_ids:
            return
        
        # Send to all subscribers
        tasks = []
        for connection_id in subscriber_ids.copy():  # Copy to avoid modification during iteration
            if connection_id in self.connections:
                connection = self.connections[connection_id]
                if connection.is_active:
                    tasks.append(connection.send_message(message))
                else:
                    # Remove inactive connection
                    tasks.append(self._remove_connection(connection_id))
        
        if tasks:
            await asyncio.gather(*tasks, return_exceptions=True)
    
    def get_connection_stats(self) -> Dict[str, Any]:
        """Get WebSocket connection statistics."""
        active_connections = sum(1 for conn in self.connections.values() if conn.is_active)
        
        return {
            "total_connections": len(self.connections),
            "active_connections": active_connections,
            "inactive_connections": len(self.connections) - active_connections,
            "evaluation_subscriptions": len(self.evaluation_subscribers),
            "system_subscriptions": len(self.system_subscribers),
            "total_subscriptions": sum(len(conn.subscriptions) for conn in self.connections.values())
        }
    
    async def shutdown(self):
        """Shutdown WebSocket handler and cleanup resources."""
        logger.info("Shutting down WebSocket handler...")
        
        # Cancel cleanup task
        if self._cleanup_task and not self._cleanup_task.done():
            self._cleanup_task.cancel()
            try:
                await self._cleanup_task
            except asyncio.CancelledError:
                pass
        
        # Close all connections
        close_tasks = []
        for connection_id in list(self.connections.keys()):
            connection = self.connections[connection_id]
            try:
                await connection.websocket.close()
            except Exception:
                pass
            close_tasks.append(self._remove_connection(connection_id))
        
        if close_tasks:
            await asyncio.gather(*close_tasks, return_exceptions=True)
        
        logger.info("WebSocket handler shutdown complete")