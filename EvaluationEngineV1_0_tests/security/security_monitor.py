"""
Security Monitor

Real-time security monitoring and alerting system for the
evaluation engine testing framework.
"""

import time
import threading
import logging
from typing import Dict, List, Optional, Callable, Any
from dataclasses import dataclass, field
from datetime import datetime, timedelta
from collections import defaultdict, deque
import json

logger = logging.getLogger(__name__)


@dataclass
class SecurityAlert:
    """Security alert information."""
    alert_id: str
    alert_type: str
    severity: str  # LOW, MEDIUM, HIGH, CRITICAL
    title: str
    description: str
    source: str
    timestamp: datetime
    details: Dict[str, Any] = field(default_factory=dict)
    resolved: bool = False
    resolved_at: Optional[datetime] = None


@dataclass
class SecurityMetrics:
    """Security metrics for monitoring."""
    total_violations: int = 0
    violations_by_type: Dict[str, int] = field(default_factory=lambda: defaultdict(int))
    violations_by_severity: Dict[str, int] = field(default_factory=lambda: defaultdict(int))
    active_alerts: int = 0
    resolved_alerts: int = 0
    last_violation_time: Optional[datetime] = None
    monitoring_start_time: datetime = field(default_factory=datetime.now)


class SecurityMonitor:
    """
    Real-time security monitoring and alerting system.
    
    Features:
    - Real-time security event monitoring
    - Alert generation and management
    - Security metrics collection
    - Threat pattern detection
    - Automated response triggers
    - Security dashboard data
    """
    
    def __init__(self, 
                 alert_threshold: int = 5,
                 monitoring_interval: float = 1.0,
                 max_alerts: int = 1000):
        """
        Initialize security monitor.
        
        Args:
            alert_threshold: Number of violations before generating alert
            monitoring_interval: How often to check for patterns (seconds)
            max_alerts: Maximum number of alerts to keep in memory
        """
        self.alert_threshold = alert_threshold
        self.monitoring_interval = monitoring_interval
        self.max_alerts = max_alerts
        
        # Monitoring state
        self._monitoring = False
        self._monitor_thread: Optional[threading.Thread] = None
        self._shutdown_event = threading.Event()
        
        # Alerts and metrics
        self.alerts: Dict[str, SecurityAlert] = {}
        self.metrics = SecurityMetrics()
        self._lock = threading.Lock()
        
        # Event tracking
        self.recent_events: deque = deque(maxlen=1000)
        self.violation_patterns: Dict[str, List[datetime]] = defaultdict(list)
        
        # Alert handlers
        self.alert_handlers: List[Callable[[SecurityAlert], None]] = []
        
        # Threat detection rules
        self.threat_rules = {
            'rapid_violations': {
                'threshold': 10,
                'time_window': 60,  # seconds
                'severity': 'HIGH'
            },
            'repeated_command_injection': {
                'threshold': 3,
                'time_window': 300,  # 5 minutes
                'severity': 'CRITICAL'
            },
            'resource_exhaustion_attempts': {
                'threshold': 5,
                'time_window': 120,  # 2 minutes
                'severity': 'HIGH'
            },
            'authentication_failures': {
                'threshold': 5,
                'time_window': 300,  # 5 minutes
                'severity': 'MEDIUM'
            }
        }
        
        self.logger = logging.getLogger(f"{__name__}.SecurityMonitor")
    
    def start_monitoring(self):
        """Start security monitoring."""
        if self._monitoring:
            self.logger.warning("Security monitoring already active")
            return
        
        self._monitoring = True
        self._shutdown_event.clear()
        
        # Start monitoring thread
        self._monitor_thread = threading.Thread(target=self._monitoring_loop, daemon=True)
        self._monitor_thread.start()
        
        self.logger.info("Security monitoring started")
    
    def stop_monitoring(self):
        """Stop security monitoring."""
        if not self._monitoring:
            return
        
        self._monitoring = False
        self._shutdown_event.set()
        
        if self._monitor_thread and self._monitor_thread.is_alive():
            self._monitor_thread.join(timeout=5.0)
        
        self.logger.info("Security monitoring stopped")
    
    def record_security_event(self, event_type: str, details: Dict[str, Any]):
        """
        Record a security event for monitoring.
        
        Args:
            event_type: Type of security event
            details: Event details
        """
        event = {
            'timestamp': datetime.now(),
            'event_type': event_type,
            'details': details
        }
        
        with self._lock:
            self.recent_events.append(event)
            
            # Update metrics
            if event_type.endswith('_violation'):
                self.metrics.total_violations += 1
                self.metrics.violations_by_type[event_type] += 1
                self.metrics.last_violation_time = event['timestamp']
                
                # Track violation patterns
                self.violation_patterns[event_type].append(event['timestamp'])
                
                # Clean old patterns
                cutoff_time = datetime.now() - timedelta(hours=1)
                self.violation_patterns[event_type] = [
                    ts for ts in self.violation_patterns[event_type]
                    if ts > cutoff_time
                ]
        
        # Check for threat patterns
        self._check_threat_patterns(event_type, event)
        
        self.logger.debug(f"Security event recorded: {event_type}")
    
    def generate_alert(self, 
                      alert_type: str,
                      severity: str,
                      title: str,
                      description: str,
                      source: str,
                      details: Optional[Dict[str, Any]] = None) -> SecurityAlert:
        """
        Generate a security alert.
        
        Args:
            alert_type: Type of alert
            severity: Alert severity (LOW, MEDIUM, HIGH, CRITICAL)
            title: Alert title
            description: Alert description
            source: Alert source
            details: Additional alert details
            
        Returns:
            Generated security alert
        """
        alert_id = f"{alert_type}_{int(time.time())}"
        
        alert = SecurityAlert(
            alert_id=alert_id,
            alert_type=alert_type,
            severity=severity,
            title=title,
            description=description,
            source=source,
            timestamp=datetime.now(),
            details=details or {}
        )
        
        with self._lock:
            self.alerts[alert_id] = alert
            self.metrics.active_alerts += 1
            self.metrics.violations_by_severity[severity] += 1
            
            # Maintain alert limit
            if len(self.alerts) > self.max_alerts:
                # Remove oldest resolved alerts
                oldest_resolved = [
                    (aid, alert) for aid, alert in self.alerts.items()
                    if alert.resolved
                ]
                if oldest_resolved:
                    oldest_resolved.sort(key=lambda x: x[1].resolved_at or x[1].timestamp)
                    for aid, _ in oldest_resolved[:len(self.alerts) - self.max_alerts + 1]:
                        del self.alerts[aid]
        
        # Notify alert handlers
        for handler in self.alert_handlers:
            try:
                handler(alert)
            except Exception as e:
                self.logger.error(f"Alert handler failed: {e}")
        
        self.logger.warning(f"Security alert generated: {severity} - {title}")
        return alert
    
    def resolve_alert(self, alert_id: str, resolution_note: Optional[str] = None):
        """
        Resolve a security alert.
        
        Args:
            alert_id: Alert ID to resolve
            resolution_note: Optional resolution note
        """
        with self._lock:
            if alert_id in self.alerts:
                alert = self.alerts[alert_id]
                if not alert.resolved:
                    alert.resolved = True
                    alert.resolved_at = datetime.now()
                    if resolution_note:
                        alert.details['resolution_note'] = resolution_note
                    
                    self.metrics.active_alerts -= 1
                    self.metrics.resolved_alerts += 1
                    
                    self.logger.info(f"Security alert resolved: {alert_id}")
    
    def get_active_alerts(self, severity_filter: Optional[str] = None) -> List[SecurityAlert]:
        """
        Get active security alerts.
        
        Args:
            severity_filter: Optional severity filter
            
        Returns:
            List of active alerts
        """
        with self._lock:
            alerts = [alert for alert in self.alerts.values() if not alert.resolved]
            
            if severity_filter:
                alerts = [alert for alert in alerts if alert.severity == severity_filter]
            
            # Sort by timestamp (newest first)
            alerts.sort(key=lambda x: x.timestamp, reverse=True)
            
            return alerts
    
    def get_alert_summary(self) -> Dict[str, Any]:
        """Get summary of security alerts."""
        with self._lock:
            active_by_severity = defaultdict(int)
            for alert in self.alerts.values():
                if not alert.resolved:
                    active_by_severity[alert.severity] += 1
            
            return {
                'total_alerts': len(self.alerts),
                'active_alerts': self.metrics.active_alerts,
                'resolved_alerts': self.metrics.resolved_alerts,
                'active_by_severity': dict(active_by_severity),
                'recent_alert_count': len([
                    alert for alert in self.alerts.values()
                    if alert.timestamp > datetime.now() - timedelta(hours=24)
                ])
            }
    
    def get_security_metrics(self) -> SecurityMetrics:
        """Get current security metrics."""
        with self._lock:
            return SecurityMetrics(
                total_violations=self.metrics.total_violations,
                violations_by_type=dict(self.metrics.violations_by_type),
                violations_by_severity=dict(self.metrics.violations_by_severity),
                active_alerts=self.metrics.active_alerts,
                resolved_alerts=self.metrics.resolved_alerts,
                last_violation_time=self.metrics.last_violation_time,
                monitoring_start_time=self.metrics.monitoring_start_time
            )
    
    def get_threat_analysis(self) -> Dict[str, Any]:
        """Get threat analysis based on recent events."""
        with self._lock:
            recent_events = list(self.recent_events)
        
        # Analyze recent events
        now = datetime.now()
        last_hour = now - timedelta(hours=1)
        last_day = now - timedelta(days=1)
        
        events_last_hour = [e for e in recent_events if e['timestamp'] > last_hour]
        events_last_day = [e for e in recent_events if e['timestamp'] > last_day]
        
        # Count event types
        event_types_hour = defaultdict(int)
        event_types_day = defaultdict(int)
        
        for event in events_last_hour:
            event_types_hour[event['event_type']] += 1
        
        for event in events_last_day:
            event_types_day[event['event_type']] += 1
        
        # Identify trends
        trends = []
        for event_type, count in event_types_hour.items():
            if count >= 5:
                trends.append(f"High frequency of {event_type}: {count} in last hour")
        
        # Risk assessment
        risk_score = 0
        risk_factors = []
        
        if self.metrics.active_alerts > 0:
            risk_score += self.metrics.active_alerts * 10
            risk_factors.append(f"{self.metrics.active_alerts} active alerts")
        
        if len(events_last_hour) > 20:
            risk_score += 20
            risk_factors.append("High event frequency")
        
        critical_alerts = len([a for a in self.alerts.values() 
                              if not a.resolved and a.severity == 'CRITICAL'])
        if critical_alerts > 0:
            risk_score += critical_alerts * 50
            risk_factors.append(f"{critical_alerts} critical alerts")
        
        # Determine risk level
        if risk_score >= 100:
            risk_level = "CRITICAL"
        elif risk_score >= 50:
            risk_level = "HIGH"
        elif risk_score >= 20:
            risk_level = "MEDIUM"
        else:
            risk_level = "LOW"
        
        return {
            'risk_level': risk_level,
            'risk_score': risk_score,
            'risk_factors': risk_factors,
            'trends': trends,
            'events_last_hour': len(events_last_hour),
            'events_last_day': len(events_last_day),
            'event_types_hour': dict(event_types_hour),
            'event_types_day': dict(event_types_day)
        }
    
    def add_alert_handler(self, handler: Callable[[SecurityAlert], None]):
        """Add an alert handler function."""
        self.alert_handlers.append(handler)
        self.logger.info("Alert handler added")
    
    def _monitoring_loop(self):
        """Main monitoring loop."""
        while self._monitoring and not self._shutdown_event.is_set():
            try:
                # Check for threat patterns
                self._check_all_threat_patterns()
                
                # Clean old data
                self._cleanup_old_data()
                
                # Sleep until next check
                self._shutdown_event.wait(self.monitoring_interval)
                
            except Exception as e:
                self.logger.error(f"Error in monitoring loop: {e}")
                time.sleep(self.monitoring_interval)
    
    def _check_threat_patterns(self, event_type: str, event: Dict[str, Any]):
        """Check for specific threat patterns in real-time."""
        # Check for rapid violations
        if event_type.endswith('_violation'):
            recent_violations = [
                e for e in self.recent_events
                if e['event_type'].endswith('_violation') and
                e['timestamp'] > datetime.now() - timedelta(seconds=60)
            ]
            
            if len(recent_violations) >= 10:
                self.generate_alert(
                    alert_type='rapid_violations',
                    severity='HIGH',
                    title='Rapid Security Violations Detected',
                    description=f'Detected {len(recent_violations)} violations in the last minute',
                    source='SecurityMonitor',
                    details={'violation_count': len(recent_violations)}
                )
        
        # Check for command injection attempts
        if event_type == 'command_injection_attempt':
            recent_injections = [
                e for e in self.recent_events
                if e['event_type'] == 'command_injection_attempt' and
                e['timestamp'] > datetime.now() - timedelta(minutes=5)
            ]
            
            if len(recent_injections) >= 3:
                self.generate_alert(
                    alert_type='repeated_command_injection',
                    severity='CRITICAL',
                    title='Repeated Command Injection Attempts',
                    description=f'Detected {len(recent_injections)} injection attempts in 5 minutes',
                    source='SecurityMonitor',
                    details={'injection_attempts': len(recent_injections)}
                )
    
    def _check_all_threat_patterns(self):
        """Check all configured threat patterns."""
        now = datetime.now()
        
        for rule_name, rule_config in self.threat_rules.items():
            threshold = rule_config['threshold']
            time_window = rule_config['time_window']
            severity = rule_config['severity']
            
            # Count matching events in time window
            cutoff_time = now - timedelta(seconds=time_window)
            matching_events = [
                e for e in self.recent_events
                if e['timestamp'] > cutoff_time and
                self._event_matches_rule(e, rule_name)
            ]
            
            if len(matching_events) >= threshold:
                # Check if we already have an active alert for this pattern
                existing_alert = any(
                    alert.alert_type == rule_name and not alert.resolved
                    for alert in self.alerts.values()
                )
                
                if not existing_alert:
                    self.generate_alert(
                        alert_type=rule_name,
                        severity=severity,
                        title=f'Threat Pattern Detected: {rule_name.replace("_", " ").title()}',
                        description=f'Detected {len(matching_events)} matching events in {time_window} seconds',
                        source='SecurityMonitor',
                        details={
                            'event_count': len(matching_events),
                            'time_window': time_window,
                            'threshold': threshold
                        }
                    )
    
    def _event_matches_rule(self, event: Dict[str, Any], rule_name: str) -> bool:
        """Check if an event matches a threat detection rule."""
        event_type = event['event_type']
        
        if rule_name == 'rapid_violations':
            return event_type.endswith('_violation')
        elif rule_name == 'repeated_command_injection':
            return event_type == 'command_injection_attempt'
        elif rule_name == 'resource_exhaustion_attempts':
            return event_type in ['memory_limit_exceeded', 'cpu_limit_exceeded', 'time_limit_exceeded']
        elif rule_name == 'authentication_failures':
            return event_type in ['api_authentication_failed', 'jwt_auth_failed']
        
        return False
    
    def _cleanup_old_data(self):
        """Clean up old monitoring data."""
        cutoff_time = datetime.now() - timedelta(hours=24)
        
        with self._lock:
            # Clean old violation patterns
            for event_type in list(self.violation_patterns.keys()):
                self.violation_patterns[event_type] = [
                    ts for ts in self.violation_patterns[event_type]
                    if ts > cutoff_time
                ]
                
                if not self.violation_patterns[event_type]:
                    del self.violation_patterns[event_type]
    
    def export_security_report(self) -> Dict[str, Any]:
        """Export comprehensive security report."""
        metrics = self.get_security_metrics()
        alert_summary = self.get_alert_summary()
        threat_analysis = self.get_threat_analysis()
        
        # Get recent critical events
        recent_critical_events = [
            {
                'timestamp': event['timestamp'].isoformat(),
                'event_type': event['event_type'],
                'details': event['details']
            }
            for event in self.recent_events
            if event['timestamp'] > datetime.now() - timedelta(hours=24) and
            event['event_type'].endswith('_violation')
        ]
        
        return {
            'report_timestamp': datetime.now().isoformat(),
            'monitoring_duration': (datetime.now() - metrics.monitoring_start_time).total_seconds(),
            'metrics': {
                'total_violations': metrics.total_violations,
                'violations_by_type': metrics.violations_by_type,
                'violations_by_severity': metrics.violations_by_severity,
                'last_violation_time': metrics.last_violation_time.isoformat() if metrics.last_violation_time else None
            },
            'alerts': alert_summary,
            'threat_analysis': threat_analysis,
            'recent_critical_events': recent_critical_events[-50:],  # Last 50 events
            'active_alerts': [
                {
                    'alert_id': alert.alert_id,
                    'alert_type': alert.alert_type,
                    'severity': alert.severity,
                    'title': alert.title,
                    'timestamp': alert.timestamp.isoformat(),
                    'details': alert.details
                }
                for alert in self.get_active_alerts()
            ]
        }
    
    def __enter__(self):
        """Context manager entry."""
        self.start_monitoring()
        return self
    
    def __exit__(self, exc_type, exc_val, exc_tb):
        """Context manager exit."""
        self.stop_monitoring()