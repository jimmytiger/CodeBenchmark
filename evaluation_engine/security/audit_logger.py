"""
Comprehensive Audit Logging and Security Event Monitoring

Provides detailed audit trails and security event tracking.
"""

import asyncio
import json
import logging
import os
import sys
from datetime import datetime, timedelta
from typing import Dict, List, Optional, Any, Union, Callable
from dataclasses import dataclass, asdict
from pathlib import Path
from enum import Enum
import hashlib
import threading
from queue import Queue, Empty
import gzip
import shutil

logger = logging.getLogger(__name__)

class EventSeverity(Enum):
    """Security event severity levels"""
    CRITICAL = "CRITICAL"
    HIGH = "HIGH"
    MEDIUM = "MEDIUM"
    LOW = "LOW"
    INFO = "INFO"

class EventCategory(Enum):
    """Security event categories"""
    AUTHENTICATION = "authentication"
    AUTHORIZATION = "authorization"
    DATA_ACCESS = "data_access"
    SYSTEM_ACCESS = "system_access"
    CONFIGURATION_CHANGE = "configuration_change"
    SECURITY_VIOLATION = "security_violation"
    VULNERABILITY = "vulnerability"
    INCIDENT = "incident"
    COMPLIANCE = "compliance"
    AUDIT = "audit"

@dataclass
class SecurityEvent:
    """Represents a security event"""
    event_id: str
    timestamp: datetime
    severity: EventSeverity
    category: EventCategory
    event_type: str
    description: str
    source: str
    user_id: Optional[str] = None
    session_id: Optional[str] = None
    ip_address: Optional[str] = None
    user_agent: Optional[str] = None
    resource: Optional[str] = None
    action: Optional[str] = None
    result: Optional[str] = None
    metadata: Dict[str, Any] = None
    
    def __post_init__(self):
        if self.metadata is None:
            self.metadata = {}
        if not self.event_id:
            self.event_id = self._generate_event_id()
    
    def _generate_event_id(self) -> str:
        """Generate unique event ID"""
        data = f"{self.timestamp.isoformat()}{self.source}{self.event_type}{self.description}"
        return hashlib.sha256(data.encode()).hexdigest()[:16]

@dataclass
class AuditLogEntry:
    """Represents an audit log entry"""
    log_id: str
    timestamp: datetime
    level: str
    message: str
    module: str
    function: str
    line_number: int
    user_id: Optional[str] = None
    session_id: Optional[str] = None
    request_id: Optional[str] = None
    metadata: Dict[str, Any] = None
    
    def __post_init__(self):
        if self.metadata is None:
            self.metadata = {}
        if not self.log_id:
            self.log_id = self._generate_log_id()
    
    def _generate_log_id(self) -> str:
        """Generate unique log ID"""
        data = f"{self.timestamp.isoformat()}{self.module}{self.function}{self.message}"
        return hashlib.sha256(data.encode()).hexdigest()[:16]

class LogRotationManager:
    """Manages log file rotation and archival"""
    
    def __init__(self, log_dir: str, max_file_size: int = 100 * 1024 * 1024,  # 100MB
                 max_files: int = 10, compress_old: bool = True):
        self.log_dir = Path(log_dir)
        self.log_dir.mkdir(parents=True, exist_ok=True)
        self.max_file_size = max_file_size
        self.max_files = max_files
        self.compress_old = compress_old
    
    def should_rotate(self, log_file: Path) -> bool:
        """Check if log file should be rotated"""
        if not log_file.exists():
            return False
        return log_file.stat().st_size >= self.max_file_size
    
    def rotate_log(self, log_file: Path):
        """Rotate log file"""
        if not log_file.exists():
            return
        
        # Find next rotation number
        base_name = log_file.stem
        extension = log_file.suffix
        rotation_num = 1
        
        while True:
            rotated_name = f"{base_name}.{rotation_num}{extension}"
            rotated_path = log_file.parent / rotated_name
            if not rotated_path.exists():
                break
            rotation_num += 1
        
        # Rotate existing files
        for i in range(rotation_num - 1, 0, -1):
            old_name = f"{base_name}.{i}{extension}"
            new_name = f"{base_name}.{i + 1}{extension}"
            old_path = log_file.parent / old_name
            new_path = log_file.parent / new_name
            
            if old_path.exists():
                if i + 1 > self.max_files:
                    # Delete old file
                    old_path.unlink()
                else:
                    # Move to next rotation
                    old_path.rename(new_path)
                    if self.compress_old and not new_name.endswith('.gz'):
                        self._compress_file(new_path)
        
        # Move current log to .1
        rotated_path = log_file.parent / f"{base_name}.1{extension}"
        log_file.rename(rotated_path)
        
        if self.compress_old:
            self._compress_file(rotated_path)
    
    def _compress_file(self, file_path: Path):
        """Compress log file"""
        compressed_path = file_path.with_suffix(file_path.suffix + '.gz')
        with open(file_path, 'rb') as f_in:
            with gzip.open(compressed_path, 'wb') as f_out:
                shutil.copyfileobj(f_in, f_out)
        file_path.unlink()

class SecurityEventHandler:
    """Handles security events with alerting and response"""
    
    def __init__(self):
        self.handlers: Dict[EventCategory, List[Callable]] = {}
        self.alert_thresholds: Dict[EventSeverity, int] = {
            EventSeverity.CRITICAL: 1,
            EventSeverity.HIGH: 3,
            EventSeverity.MEDIUM: 10,
            EventSeverity.LOW: 50
        }
        self.event_counts: Dict[EventSeverity, int] = {
            severity: 0 for severity in EventSeverity
        }
        self.last_reset = datetime.utcnow()
    
    def register_handler(self, category: EventCategory, handler: Callable[[SecurityEvent], None]):
        """Register event handler for specific category"""
        if category not in self.handlers:
            self.handlers[category] = []
        self.handlers[category].append(handler)
    
    async def handle_event(self, event: SecurityEvent):
        """Handle security event"""
        # Update event counts
        self.event_counts[event.severity] += 1
        
        # Check if alert threshold reached
        if self.event_counts[event.severity] >= self.alert_thresholds[event.severity]:
            await self._trigger_alert(event)
        
        # Call registered handlers
        if event.category in self.handlers:
            for handler in self.handlers[event.category]:
                try:
                    if asyncio.iscoroutinefunction(handler):
                        await handler(event)
                    else:
                        handler(event)
                except Exception as e:
                    logger.error(f"Error in event handler: {e}")
    
    async def _trigger_alert(self, event: SecurityEvent):
        """Trigger security alert"""
        alert_data = {
            'alert_type': 'security_threshold_exceeded',
            'severity': event.severity.value,
            'count': self.event_counts[event.severity],
            'threshold': self.alert_thresholds[event.severity],
            'latest_event': asdict(event),
            'timestamp': datetime.utcnow().isoformat()
        }
        
        # Save alert for incident detector
        alert_file = Path("security/alerts") / f"threshold_alert_{event.event_id}.json"
        alert_file.parent.mkdir(parents=True, exist_ok=True)
        
        with open(alert_file, 'w') as f:
            json.dump(alert_data, f, indent=2, default=str)
        
        logger.critical(f"SECURITY ALERT: {event.severity.value} event threshold exceeded")
    
    def reset_counts(self):
        """Reset event counts (typically called hourly)"""
        self.event_counts = {severity: 0 for severity in EventSeverity}
        self.last_reset = datetime.utcnow()

class AuditLogger:
    """Comprehensive audit logging and security event monitoring system"""
    
    def __init__(self, config: Optional[Dict[str, Any]] = None):
        self.config = config or {}
        self.log_dir = Path(self.config.get('log_dir', 'security/logs'))
        self.log_dir.mkdir(parents=True, exist_ok=True)
        
        # Initialize components
        self.rotation_manager = LogRotationManager(
            str(self.log_dir),
            max_file_size=self.config.get('max_file_size', 100 * 1024 * 1024),
            max_files=self.config.get('max_files', 10)
        )
        
        self.event_handler = SecurityEventHandler()
        
        # Setup logging
        self._setup_logging()
        
        # Event queues for async processing
        self.security_event_queue = Queue()
        self.audit_log_queue = Queue()
        
        # Background processing
        self.processing_thread = None
        self.is_running = False
        
        # Event storage
        self.security_events: List[SecurityEvent] = []
        self.audit_logs: List[AuditLogEntry] = []
        
        # Start background processing
        self.start_processing()
    
    def _setup_logging(self):
        """Setup structured logging"""
        # Security events logger
        self.security_logger = logging.getLogger('security_events')
        self.security_logger.setLevel(logging.INFO)
        
        security_handler = logging.FileHandler(self.log_dir / 'security_events.log')
        security_formatter = logging.Formatter(
            '%(asctime)s - %(levelname)s - %(message)s'
        )
        security_handler.setFormatter(security_formatter)
        self.security_logger.addHandler(security_handler)
        
        # Audit logger
        self.audit_logger = logging.getLogger('audit_trail')
        self.audit_logger.setLevel(logging.INFO)
        
        audit_handler = logging.FileHandler(self.log_dir / 'audit_trail.log')
        audit_formatter = logging.Formatter(
            '%(asctime)s - %(name)s - %(levelname)s - %(funcName)s:%(lineno)d - %(message)s'
        )
        audit_handler.setFormatter(audit_formatter)
        self.audit_logger.addHandler(audit_handler)
        
        # System logger
        self.system_logger = logging.getLogger('system_events')
        self.system_logger.setLevel(logging.INFO)
        
        system_handler = logging.FileHandler(self.log_dir / 'system_events.log')
        system_handler.setFormatter(audit_formatter)
        self.system_logger.addHandler(system_handler)
    
    def start_processing(self):
        """Start background event processing"""
        if self.is_running:
            return
        
        self.is_running = True
        self.processing_thread = threading.Thread(target=self._process_events, daemon=True)
        self.processing_thread.start()
        logger.info("Started audit logging background processing")
    
    def stop_processing(self):
        """Stop background event processing"""
        self.is_running = False
        if self.processing_thread:
            self.processing_thread.join(timeout=5)
        logger.info("Stopped audit logging background processing")
    
    def _process_events(self):
        """Background thread for processing events"""
        while self.is_running:
            try:
                # Process security events
                try:
                    while True:
                        event = self.security_event_queue.get_nowait()
                        self._write_security_event(event)
                        try:
                            asyncio.run(self.event_handler.handle_event(event))
                        except Exception as e:
                            logger.error(f"Error handling event: {e}")
                        self.security_events.append(event)
                        
                        # Rotate logs if needed
                        log_file = self.log_dir / 'security_events.log'
                        if self.rotation_manager.should_rotate(log_file):
                            self.rotation_manager.rotate_log(log_file)
                        
                except Empty:
                    pass
                
                # Process audit logs
                try:
                    while True:
                        log_entry = self.audit_log_queue.get_nowait()
                        self._write_audit_log(log_entry)
                        self.audit_logs.append(log_entry)
                        
                        # Rotate logs if needed
                        log_file = self.log_dir / 'audit_trail.log'
                        if self.rotation_manager.should_rotate(log_file):
                            self.rotation_manager.rotate_log(log_file)
                        
                except Empty:
                    pass
                
                # Clean old events from memory (keep last 1000)
                if len(self.security_events) > 1000:
                    self.security_events = self.security_events[-1000:]
                
                if len(self.audit_logs) > 1000:
                    self.audit_logs = self.audit_logs[-1000:]
                
                # Sleep briefly
                threading.Event().wait(0.1)
                
            except Exception as e:
                logger.error(f"Error in event processing: {e}")
                threading.Event().wait(1)
    
    def _write_security_event(self, event: SecurityEvent):
        """Write security event to log"""
        event_data = {
            'event_id': event.event_id,
            'timestamp': event.timestamp.isoformat(),
            'severity': event.severity.value,
            'category': event.category.value,
            'event_type': event.event_type,
            'description': event.description,
            'source': event.source,
            'user_id': event.user_id,
            'session_id': event.session_id,
            'ip_address': event.ip_address,
            'user_agent': event.user_agent,
            'resource': event.resource,
            'action': event.action,
            'result': event.result,
            'metadata': event.metadata
        }
        
        self.security_logger.info(json.dumps(event_data, default=str))
    
    def _write_audit_log(self, log_entry: AuditLogEntry):
        """Write audit log entry"""
        log_data = {
            'log_id': log_entry.log_id,
            'timestamp': log_entry.timestamp.isoformat(),
            'level': log_entry.level,
            'message': log_entry.message,
            'module': log_entry.module,
            'function': log_entry.function,
            'line_number': log_entry.line_number,
            'user_id': log_entry.user_id,
            'session_id': log_entry.session_id,
            'request_id': log_entry.request_id,
            'metadata': log_entry.metadata
        }
        
        self.audit_logger.info(json.dumps(log_data, default=str))
    
    def log_security_event(self, severity: EventSeverity, category: EventCategory,
                          event_type: str, description: str, source: str,
                          user_id: Optional[str] = None, session_id: Optional[str] = None,
                          ip_address: Optional[str] = None, user_agent: Optional[str] = None,
                          resource: Optional[str] = None, action: Optional[str] = None,
                          result: Optional[str] = None, metadata: Optional[Dict[str, Any]] = None):
        """Log a security event"""
        event = SecurityEvent(
            event_id="",  # Will be generated
            timestamp=datetime.utcnow(),
            severity=severity,
            category=category,
            event_type=event_type,
            description=description,
            source=source,
            user_id=user_id,
            session_id=session_id,
            ip_address=ip_address,
            user_agent=user_agent,
            resource=resource,
            action=action,
            result=result,
            metadata=metadata or {}
        )
        
        self.security_event_queue.put(event)
    
    def log_audit_entry(self, level: str, message: str, module: str, function: str,
                       line_number: int, user_id: Optional[str] = None,
                       session_id: Optional[str] = None, request_id: Optional[str] = None,
                       metadata: Optional[Dict[str, Any]] = None):
        """Log an audit entry"""
        log_entry = AuditLogEntry(
            log_id="",  # Will be generated
            timestamp=datetime.utcnow(),
            level=level,
            message=message,
            module=module,
            function=function,
            line_number=line_number,
            user_id=user_id,
            session_id=session_id,
            request_id=request_id,
            metadata=metadata or {}
        )
        
        self.audit_log_queue.put(log_entry)
    
    def log_authentication_event(self, user_id: str, action: str, result: str,
                                ip_address: Optional[str] = None,
                                user_agent: Optional[str] = None,
                                metadata: Optional[Dict[str, Any]] = None):
        """Log authentication event"""
        severity = EventSeverity.HIGH if result == "failed" else EventSeverity.INFO
        
        self.log_security_event(
            severity=severity,
            category=EventCategory.AUTHENTICATION,
            event_type="authentication",
            description=f"User {action} attempt",
            source="authentication_system",
            user_id=user_id,
            ip_address=ip_address,
            user_agent=user_agent,
            action=action,
            result=result,
            metadata=metadata
        )
    
    def log_authorization_event(self, user_id: str, resource: str, action: str,
                               result: str, ip_address: Optional[str] = None,
                               metadata: Optional[Dict[str, Any]] = None):
        """Log authorization event"""
        severity = EventSeverity.MEDIUM if result == "denied" else EventSeverity.INFO
        
        self.log_security_event(
            severity=severity,
            category=EventCategory.AUTHORIZATION,
            event_type="authorization",
            description=f"Access {action} on {resource}",
            source="authorization_system",
            user_id=user_id,
            ip_address=ip_address,
            resource=resource,
            action=action,
            result=result,
            metadata=metadata
        )
    
    def log_data_access_event(self, user_id: str, resource: str, action: str,
                             result: str, data_classification: Optional[str] = None,
                             metadata: Optional[Dict[str, Any]] = None):
        """Log data access event"""
        severity = EventSeverity.HIGH if data_classification == "sensitive" else EventSeverity.INFO
        
        metadata = metadata or {}
        if data_classification:
            metadata['data_classification'] = data_classification
        
        self.log_security_event(
            severity=severity,
            category=EventCategory.DATA_ACCESS,
            event_type="data_access",
            description=f"Data {action} on {resource}",
            source="data_access_system",
            user_id=user_id,
            resource=resource,
            action=action,
            result=result,
            metadata=metadata
        )
    
    def log_security_violation(self, violation_type: str, description: str,
                              source: str, severity: EventSeverity = EventSeverity.HIGH,
                              user_id: Optional[str] = None,
                              ip_address: Optional[str] = None,
                              metadata: Optional[Dict[str, Any]] = None):
        """Log security violation"""
        self.log_security_event(
            severity=severity,
            category=EventCategory.SECURITY_VIOLATION,
            event_type=violation_type,
            description=description,
            source=source,
            user_id=user_id,
            ip_address=ip_address,
            result="violation_detected",
            metadata=metadata
        )
    
    def log_configuration_change(self, user_id: str, component: str, change_type: str,
                                old_value: Any, new_value: Any,
                                metadata: Optional[Dict[str, Any]] = None):
        """Log configuration change"""
        metadata = metadata or {}
        metadata.update({
            'component': component,
            'change_type': change_type,
            'old_value': str(old_value),
            'new_value': str(new_value)
        })
        
        self.log_security_event(
            severity=EventSeverity.MEDIUM,
            category=EventCategory.CONFIGURATION_CHANGE,
            event_type="configuration_change",
            description=f"Configuration changed: {component}",
            source="configuration_system",
            user_id=user_id,
            action=change_type,
            result="success",
            metadata=metadata
        )
    
    def search_events(self, start_time: Optional[datetime] = None,
                     end_time: Optional[datetime] = None,
                     severity: Optional[EventSeverity] = None,
                     category: Optional[EventCategory] = None,
                     user_id: Optional[str] = None,
                     limit: int = 100) -> List[SecurityEvent]:
        """Search security events"""
        events = self.security_events.copy()
        
        # Apply filters
        if start_time:
            events = [e for e in events if e.timestamp >= start_time]
        
        if end_time:
            events = [e for e in events if e.timestamp <= end_time]
        
        if severity:
            events = [e for e in events if e.severity == severity]
        
        if category:
            events = [e for e in events if e.category == category]
        
        if user_id:
            events = [e for e in events if e.user_id == user_id]
        
        # Sort by timestamp (newest first) and limit
        events.sort(key=lambda x: x.timestamp, reverse=True)
        return events[:limit]
    
    def get_event_statistics(self, hours: int = 24) -> Dict[str, Any]:
        """Get event statistics for the last N hours"""
        cutoff_time = datetime.utcnow() - timedelta(hours=hours)
        recent_events = [e for e in self.security_events if e.timestamp >= cutoff_time]
        
        stats = {
            'total_events': len(recent_events),
            'by_severity': {},
            'by_category': {},
            'unique_users': len(set(e.user_id for e in recent_events if e.user_id)),
            'unique_sources': len(set(e.source for e in recent_events)),
            'time_range': {
                'start': cutoff_time.isoformat(),
                'end': datetime.utcnow().isoformat()
            }
        }
        
        # Count by severity
        for severity in EventSeverity:
            count = len([e for e in recent_events if e.severity == severity])
            stats['by_severity'][severity.value] = count
        
        # Count by category
        for category in EventCategory:
            count = len([e for e in recent_events if e.category == category])
            stats['by_category'][category.value] = count
        
        return stats
    
    def export_events(self, output_file: str, start_time: Optional[datetime] = None,
                     end_time: Optional[datetime] = None, format: str = "json"):
        """Export events to file"""
        events = self.search_events(start_time=start_time, end_time=end_time, limit=None)
        
        output_path = Path(output_file)
        output_path.parent.mkdir(parents=True, exist_ok=True)
        
        if format.lower() == "json":
            with open(output_path, 'w') as f:
                json.dump([asdict(event) for event in events], f, indent=2, default=str)
        elif format.lower() == "csv":
            import csv
            with open(output_path, 'w', newline='') as f:
                if events:
                    writer = csv.DictWriter(f, fieldnames=asdict(events[0]).keys())
                    writer.writeheader()
                    for event in events:
                        writer.writerow(asdict(event))
        else:
            raise ValueError(f"Unsupported export format: {format}")
        
        logger.info(f"Exported {len(events)} events to {output_path}")
    
    def get_audit_status(self) -> Dict[str, Any]:
        """Get audit logging system status"""
        return {
            'status': 'active' if self.is_running else 'stopped',
            'log_directory': str(self.log_dir),
            'security_events_count': len(self.security_events),
            'audit_logs_count': len(self.audit_logs),
            'queue_sizes': {
                'security_events': self.security_event_queue.qsize(),
                'audit_logs': self.audit_log_queue.qsize()
            },
            'event_handler_counts': self.event_handler.event_counts,
            'last_reset': self.event_handler.last_reset.isoformat()
        }