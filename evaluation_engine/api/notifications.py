"""
Notification System for Real-time Communication

Implements notification delivery through multiple channels including
WebSocket, email, and webhooks.
"""

import asyncio
import aiohttp
import smtplib
from email.mime.text import MIMEText
from email.mime.multipart import MIMEMultipart
from typing import Dict, Any, List, Optional, Union
import logging
from datetime import datetime
from enum import Enum
import json
from dataclasses import dataclass

from .models import NotificationSettings
from .websocket import WebSocketManager

logger = logging.getLogger(__name__)


class NotificationType(str, Enum):
    """Notification type enumeration."""
    EVALUATION_STARTED = "evaluation_started"
    EVALUATION_COMPLETED = "evaluation_completed"
    EVALUATION_FAILED = "evaluation_failed"
    EVALUATION_CANCELLED = "evaluation_cancelled"
    SYSTEM_ALERT = "system_alert"
    SYSTEM_WARNING = "system_warning"
    SYSTEM_ERROR = "system_error"
    USER_ACTION_REQUIRED = "user_action_required"


class NotificationPriority(str, Enum):
    """Notification priority levels."""
    LOW = "low"
    NORMAL = "normal"
    HIGH = "high"
    URGENT = "urgent"


@dataclass
class Notification:
    """Notification data structure."""
    
    notification_id: str
    user_id: str
    type: NotificationType
    priority: NotificationPriority
    title: str
    message: str
    data: Dict[str, Any]
    created_at: datetime
    channels: List[str]  # websocket, email, webhook
    metadata: Optional[Dict[str, Any]] = None


class NotificationChannel:
    """Base class for notification channels."""
    
    async def send(self, notification: Notification, settings: NotificationSettings) -> bool:
        """Send notification through this channel."""
        raise NotImplementedError


class WebSocketChannel(NotificationChannel):
    """WebSocket notification channel."""
    
    def __init__(self, websocket_manager: WebSocketManager):
        self.websocket_manager = websocket_manager
    
    async def send(self, notification: Notification, settings: NotificationSettings) -> bool:
        """Send notification via WebSocket."""
        try:
            notification_data = {
                "notification_id": notification.notification_id,
                "type": notification.type,
                "priority": notification.priority,
                "title": notification.title,
                "message": notification.message,
                "data": notification.data,
                "created_at": notification.created_at.isoformat(),
                "metadata": notification.metadata
            }
            
            await self.websocket_manager.send_notification(
                notification.user_id, 
                notification_data
            )
            
            logger.debug(f"Sent WebSocket notification {notification.notification_id} to user {notification.user_id}")
            return True
            
        except Exception as e:
            logger.error(f"Failed to send WebSocket notification: {str(e)}")
            return False


class EmailChannel(NotificationChannel):
    """Email notification channel."""
    
    def __init__(self, smtp_host: str, smtp_port: int, 
                 smtp_username: str, smtp_password: str,
                 from_email: str):
        self.smtp_host = smtp_host
        self.smtp_port = smtp_port
        self.smtp_username = smtp_username
        self.smtp_password = smtp_password
        self.from_email = from_email
    
    async def send(self, notification: Notification, settings: NotificationSettings) -> bool:
        """Send notification via email."""
        if not settings.email_notifications:
            return True  # Skip if email notifications are disabled
        
        try:
            # Check quiet hours
            if self._is_quiet_hours(settings.quiet_hours):
                logger.debug(f"Skipping email notification during quiet hours: {notification.notification_id}")
                return True
            
            # Get user email (this would come from user management system)
            user_email = await self._get_user_email(notification.user_id)
            if not user_email:
                logger.warning(f"No email found for user {notification.user_id}")
                return False
            
            # Create email message
            msg = MIMEMultipart()
            msg['From'] = self.from_email
            msg['To'] = user_email
            msg['Subject'] = f"[AI Evaluation Engine] {notification.title}"
            
            # Create email body
            body = self._create_email_body(notification)
            msg.attach(MIMEText(body, 'html'))
            
            # Send email
            await self._send_email(msg)
            
            logger.info(f"Sent email notification {notification.notification_id} to {user_email}")
            return True
            
        except Exception as e:
            logger.error(f"Failed to send email notification: {str(e)}")
            return False
    
    def _is_quiet_hours(self, quiet_hours: Optional[Dict[str, str]]) -> bool:
        """Check if current time is within quiet hours."""
        if not quiet_hours:
            return False
        
        try:
            from datetime import time
            
            now = datetime.now().time()
            start_time = time.fromisoformat(quiet_hours["start"])
            end_time = time.fromisoformat(quiet_hours["end"])
            
            if start_time <= end_time:
                return start_time <= now <= end_time
            else:  # Quiet hours span midnight
                return now >= start_time or now <= end_time
                
        except Exception:
            return False
    
    async def _get_user_email(self, user_id: str) -> Optional[str]:
        """Get user email address."""
        # This would integrate with user management system
        # For now, return a placeholder
        return f"user_{user_id}@example.com"
    
    def _create_email_body(self, notification: Notification) -> str:
        """Create HTML email body."""
        priority_colors = {
            NotificationPriority.LOW: "#28a745",
            NotificationPriority.NORMAL: "#007bff",
            NotificationPriority.HIGH: "#fd7e14",
            NotificationPriority.URGENT: "#dc3545"
        }
        
        color = priority_colors.get(notification.priority, "#007bff")
        
        return f"""
        <html>
        <body style="font-family: Arial, sans-serif; margin: 0; padding: 20px;">
            <div style="max-width: 600px; margin: 0 auto;">
                <div style="background-color: {color}; color: white; padding: 20px; border-radius: 5px 5px 0 0;">
                    <h2 style="margin: 0;">{notification.title}</h2>
                    <p style="margin: 5px 0 0 0; opacity: 0.9;">Priority: {notification.priority.upper()}</p>
                </div>
                <div style="background-color: #f8f9fa; padding: 20px; border-radius: 0 0 5px 5px; border: 1px solid #dee2e6;">
                    <p style="margin: 0 0 15px 0; font-size: 16px; line-height: 1.5;">
                        {notification.message}
                    </p>
                    {self._format_notification_data(notification.data)}
                    <hr style="margin: 20px 0; border: none; border-top: 1px solid #dee2e6;">
                    <p style="margin: 0; font-size: 12px; color: #6c757d;">
                        Sent at: {notification.created_at.strftime('%Y-%m-%d %H:%M:%S UTC')}<br>
                        Notification ID: {notification.notification_id}
                    </p>
                </div>
            </div>
        </body>
        </html>
        """
    
    def _format_notification_data(self, data: Dict[str, Any]) -> str:
        """Format notification data for email display."""
        if not data:
            return ""
        
        html = "<div style='background-color: white; padding: 15px; border-radius: 3px; margin: 15px 0;'>"
        html += "<h4 style='margin: 0 0 10px 0; color: #495057;'>Details:</h4>"
        
        for key, value in data.items():
            if isinstance(value, dict):
                value = json.dumps(value, indent=2)
            html += f"<p style='margin: 5px 0;'><strong>{key.replace('_', ' ').title()}:</strong> {value}</p>"
        
        html += "</div>"
        return html
    
    async def _send_email(self, msg: MIMEMultipart):
        """Send email using SMTP."""
        loop = asyncio.get_event_loop()
        
        def send_sync():
            with smtplib.SMTP(self.smtp_host, self.smtp_port) as server:
                server.starttls()
                server.login(self.smtp_username, self.smtp_password)
                server.send_message(msg)
        
        await loop.run_in_executor(None, send_sync)


class WebhookChannel(NotificationChannel):
    """Webhook notification channel."""
    
    def __init__(self, timeout: int = 30):
        self.timeout = timeout
    
    async def send(self, notification: Notification, settings: NotificationSettings) -> bool:
        """Send notification via webhook."""
        if not settings.webhook_url:
            return True  # Skip if no webhook URL configured
        
        try:
            payload = {
                "notification_id": notification.notification_id,
                "user_id": notification.user_id,
                "type": notification.type,
                "priority": notification.priority,
                "title": notification.title,
                "message": notification.message,
                "data": notification.data,
                "created_at": notification.created_at.isoformat(),
                "metadata": notification.metadata
            }
            
            async with aiohttp.ClientSession() as session:
                async with session.post(
                    settings.webhook_url,
                    json=payload,
                    timeout=aiohttp.ClientTimeout(total=self.timeout),
                    headers={"Content-Type": "application/json"}
                ) as response:
                    if response.status == 200:
                        logger.info(f"Sent webhook notification {notification.notification_id}")
                        return True
                    else:
                        logger.warning(f"Webhook returned status {response.status} for notification {notification.notification_id}")
                        return False
            
        except asyncio.TimeoutError:
            logger.error(f"Webhook timeout for notification {notification.notification_id}")
            return False
        except Exception as e:
            logger.error(f"Failed to send webhook notification: {str(e)}")
            return False


class NotificationManager:
    """
    Notification manager for handling all notification delivery.
    
    Implements requirement 11.2: Notification system for evaluation 
    completion and alerts.
    """
    
    def __init__(self, websocket_manager: WebSocketManager):
        self.websocket_manager = websocket_manager
        self.channels: Dict[str, NotificationChannel] = {}
        self.user_settings: Dict[str, NotificationSettings] = {}
        
        # Initialize default channels
        self.channels["websocket"] = WebSocketChannel(websocket_manager)
        
        # Notification queue for reliable delivery
        self.notification_queue: asyncio.Queue = asyncio.Queue()
        self.processing_task: Optional[asyncio.Task] = None
        
        # Notification history (in-memory, would use database in production)
        self.notification_history: Dict[str, List[Notification]] = {}
    
    def configure_email_channel(self, smtp_host: str, smtp_port: int,
                               smtp_username: str, smtp_password: str,
                               from_email: str):
        """Configure email notification channel."""
        self.channels["email"] = EmailChannel(
            smtp_host, smtp_port, smtp_username, smtp_password, from_email
        )
        logger.info("Email notification channel configured")
    
    def configure_webhook_channel(self, timeout: int = 30):
        """Configure webhook notification channel."""
        self.channels["webhook"] = WebhookChannel(timeout)
        logger.info("Webhook notification channel configured")
    
    async def start(self):
        """Start notification processing."""
        if not self.processing_task or self.processing_task.done():
            self.processing_task = asyncio.create_task(self._process_notifications())
            logger.info("Started notification processing")
    
    async def stop(self):
        """Stop notification processing."""
        if self.processing_task and not self.processing_task.done():
            self.processing_task.cancel()
            try:
                await self.processing_task
            except asyncio.CancelledError:
                pass
            logger.info("Stopped notification processing")
    
    async def send_notification(self, user_id: str, notification_type: NotificationType,
                               title: str, message: str, data: Optional[Dict[str, Any]] = None,
                               priority: NotificationPriority = NotificationPriority.NORMAL,
                               channels: Optional[List[str]] = None) -> str:
        """
        Send notification to user.
        
        Implements requirement 11.2: Notification delivery system.
        """
        import uuid
        
        # Generate notification ID
        notification_id = str(uuid.uuid4())
        
        # Create notification
        notification = Notification(
            notification_id=notification_id,
            user_id=user_id,
            type=notification_type,
            priority=priority,
            title=title,
            message=message,
            data=data or {},
            created_at=datetime.utcnow(),
            channels=channels or ["websocket"],
            metadata={"source": "evaluation_engine"}
        )
        
        # Add to queue
        await self.notification_queue.put(notification)
        
        # Add to history
        if user_id not in self.notification_history:
            self.notification_history[user_id] = []
        self.notification_history[user_id].append(notification)
        
        # Keep only last 100 notifications per user
        if len(self.notification_history[user_id]) > 100:
            self.notification_history[user_id] = self.notification_history[user_id][-100:]
        
        logger.debug(f"Queued notification {notification_id} for user {user_id}")
        return notification_id
    
    async def send_evaluation_started(self, user_id: str, evaluation_id: str, 
                                    model_id: str, task_count: int):
        """Send evaluation started notification."""
        await self.send_notification(
            user_id=user_id,
            notification_type=NotificationType.EVALUATION_STARTED,
            title="Evaluation Started",
            message=f"Evaluation {evaluation_id} has started with model {model_id}",
            data={
                "evaluation_id": evaluation_id,
                "model_id": model_id,
                "task_count": task_count
            },
            priority=NotificationPriority.NORMAL,
            channels=["websocket"]
        )
    
    async def send_evaluation_completed(self, user_id: str, evaluation_id: str,
                                      model_id: str, overall_score: float,
                                      execution_time: float):
        """Send evaluation completed notification."""
        await self.send_notification(
            user_id=user_id,
            notification_type=NotificationType.EVALUATION_COMPLETED,
            title="Evaluation Completed",
            message=f"Evaluation {evaluation_id} completed successfully with score {overall_score:.2f}",
            data={
                "evaluation_id": evaluation_id,
                "model_id": model_id,
                "overall_score": overall_score,
                "execution_time": execution_time
            },
            priority=NotificationPriority.NORMAL,
            channels=["websocket", "email"]
        )
    
    async def send_evaluation_failed(self, user_id: str, evaluation_id: str,
                                   model_id: str, error_message: str):
        """Send evaluation failed notification."""
        await self.send_notification(
            user_id=user_id,
            notification_type=NotificationType.EVALUATION_FAILED,
            title="Evaluation Failed",
            message=f"Evaluation {evaluation_id} failed: {error_message}",
            data={
                "evaluation_id": evaluation_id,
                "model_id": model_id,
                "error_message": error_message
            },
            priority=NotificationPriority.HIGH,
            channels=["websocket", "email"]
        )
    
    async def send_system_alert(self, alert_type: str, message: str, 
                              severity: str = "warning", 
                              affected_users: Optional[List[str]] = None):
        """Send system alert to users."""
        priority_map = {
            "info": NotificationPriority.LOW,
            "warning": NotificationPriority.NORMAL,
            "error": NotificationPriority.HIGH,
            "critical": NotificationPriority.URGENT
        }
        
        priority = priority_map.get(severity, NotificationPriority.NORMAL)
        
        # Send to all users if no specific users specified
        if not affected_users:
            affected_users = list(self.user_settings.keys())
        
        for user_id in affected_users:
            await self.send_notification(
                user_id=user_id,
                notification_type=NotificationType.SYSTEM_ALERT,
                title=f"System Alert: {alert_type}",
                message=message,
                data={
                    "alert_type": alert_type,
                    "severity": severity
                },
                priority=priority,
                channels=["websocket", "email"] if severity in ["error", "critical"] else ["websocket"]
            )
    
    async def get_user_notifications(self, user_id: str, limit: int = 50) -> List[Dict[str, Any]]:
        """Get notification history for user."""
        notifications = self.notification_history.get(user_id, [])
        
        # Return most recent notifications
        recent_notifications = notifications[-limit:] if len(notifications) > limit else notifications
        
        return [
            {
                "notification_id": n.notification_id,
                "type": n.type,
                "priority": n.priority,
                "title": n.title,
                "message": n.message,
                "data": n.data,
                "created_at": n.created_at.isoformat(),
                "metadata": n.metadata
            }
            for n in reversed(recent_notifications)
        ]
    
    def set_user_settings(self, user_id: str, settings: NotificationSettings):
        """Set notification settings for user."""
        self.user_settings[user_id] = settings
        logger.info(f"Updated notification settings for user {user_id}")
    
    def get_user_settings(self, user_id: str) -> NotificationSettings:
        """Get notification settings for user."""
        return self.user_settings.get(user_id, NotificationSettings(
            email_notifications=True,
            webhook_url=None,
            notification_types=["evaluation_completed", "evaluation_failed", "system_alerts"],
            quiet_hours=None
        ))
    
    async def _process_notifications(self):
        """Process notification queue."""
        while True:
            try:
                # Get notification from queue
                notification = await self.notification_queue.get()
                
                # Get user settings
                settings = self.get_user_settings(notification.user_id)
                
                # Check if notification type is enabled
                if notification.type not in settings.notification_types:
                    logger.debug(f"Skipping disabled notification type {notification.type} for user {notification.user_id}")
                    continue
                
                # Send through each requested channel
                for channel_name in notification.channels:
                    if channel_name in self.channels:
                        try:
                            success = await self.channels[channel_name].send(notification, settings)
                            if success:
                                logger.debug(f"Sent notification {notification.notification_id} via {channel_name}")
                            else:
                                logger.warning(f"Failed to send notification {notification.notification_id} via {channel_name}")
                        except Exception as e:
                            logger.error(f"Error sending notification via {channel_name}: {str(e)}")
                    else:
                        logger.warning(f"Unknown notification channel: {channel_name}")
                
                # Mark task as done
                self.notification_queue.task_done()
                
            except asyncio.CancelledError:
                break
            except Exception as e:
                logger.error(f"Error processing notification: {str(e)}")
                await asyncio.sleep(1)  # Brief pause before continuing