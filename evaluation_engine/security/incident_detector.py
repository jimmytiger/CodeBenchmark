"""
Automated Security Incident Detection and Response System

Provides real-time security incident detection and automated response workflows.
"""

import asyncio
import json
import logging
from datetime import datetime, timedelta
from typing import Dict, List, Optional, Any, Callable, Set
from dataclasses import dataclass, asdict
from pathlib import Path
from enum import Enum
import hashlib
import re
from collections import defaultdict, deque
import statistics

from .audit_logger import SecurityEvent, EventSeverity, EventCategory

logger = logging.getLogger(__name__)

class IncidentSeverity(Enum):
    """Security incident severity levels"""
    CRITICAL = "CRITICAL"
    HIGH = "HIGH"
    MEDIUM = "MEDIUM"
    LOW = "LOW"

class IncidentStatus(Enum):
    """Security incident status"""
    OPEN = "OPEN"
    INVESTIGATING = "INVESTIGATING"
    CONTAINED = "CONTAINED"
    RESOLVED = "RESOLVED"
    CLOSED = "CLOSED"

class ResponseAction(Enum):
    """Automated response actions"""
    ALERT = "ALERT"
    BLOCK_IP = "BLOCK_IP"
    DISABLE_USER = "DISABLE_USER"
    QUARANTINE_RESOURCE = "QUARANTINE_RESOURCE"
    ESCALATE = "ESCALATE"
    LOG_ONLY = "LOG_ONLY"

@dataclass
class SecurityIncident:
    """Represents a security incident"""
    incident_id: str
    title: str
    description: str
    severity: IncidentSeverity
    status: IncidentStatus
    category: EventCategory
    created_at: datetime
    updated_at: datetime
    detected_by: str
    affected_resources: List[str]
    related_events: List[str]  # Event IDs
    indicators: Dict[str, Any]
    response_actions: List[str]
    assignee: Optional[str] = None
    resolution_notes: Optional[str] = None
    closed_at: Optional[datetime] = None
    metadata: Dict[str, Any] = None
    
    def __post_init__(self):
        if self.metadata is None:
            self.metadata = {}
        if not self.incident_id:
            self.incident_id = self._generate_incident_id()
    
    def _generate_incident_id(self) -> str:
        """Generate unique incident ID"""
        data = f"{self.created_at.isoformat()}{self.title}{self.category.value}"
        return f"INC-{hashlib.sha256(data.encode()).hexdigest()[:8].upper()}"

@dataclass
class DetectionRule:
    """Represents a security detection rule"""
    rule_id: str
    name: str
    description: str
    category: EventCategory
    severity: IncidentSeverity
    conditions: Dict[str, Any]
    time_window: int  # seconds
    threshold: int
    enabled: bool = True
    created_at: datetime = None
    updated_at: datetime = None
    
    def __post_init__(self):
        if self.created_at is None:
            self.created_at = datetime.utcnow()
        if self.updated_at is None:
            self.updated_at = self.created_at

class ThreatIntelligence:
    """Threat intelligence and IOC management"""
    
    def __init__(self):
        self.malicious_ips: Set[str] = set()
        self.malicious_domains: Set[str] = set()
        self.malicious_hashes: Set[str] = set()
        self.suspicious_patterns: List[re.Pattern] = []
        self.last_update = datetime.utcnow()
    
    def load_threat_feeds(self):
        """Load threat intelligence feeds"""
        # In a real implementation, this would fetch from external threat feeds
        # For now, we'll use some common indicators
        
        # Known malicious IPs (examples)
        self.malicious_ips.update([
            "192.168.1.100",  # Example internal scanner
            "10.0.0.50",      # Example compromised host
        ])
        
        # Suspicious patterns
        self.suspicious_patterns = [
            re.compile(r'(?i)(union|select|insert|delete|drop|exec|script)', re.IGNORECASE),
            re.compile(r'(?i)(\.\.\/|\.\.\\)', re.IGNORECASE),  # Path traversal
            re.compile(r'(?i)(cmd\.exe|powershell|bash|sh)', re.IGNORECASE),  # Command injection
            re.compile(r'(?i)(<script|javascript:|vbscript:)', re.IGNORECASE),  # XSS
        ]
        
        self.last_update = datetime.utcnow()
        logger.info("Loaded threat intelligence feeds")
    
    def is_malicious_ip(self, ip: str) -> bool:
        """Check if IP is known malicious"""
        return ip in self.malicious_ips
    
    def is_malicious_domain(self, domain: str) -> bool:
        """Check if domain is known malicious"""
        return domain in self.malicious_domains
    
    def contains_suspicious_pattern(self, text: str) -> bool:
        """Check if text contains suspicious patterns"""
        for pattern in self.suspicious_patterns:
            if pattern.search(text):
                return True
        return False

class AnomalyDetector:
    """Statistical anomaly detection for security events"""
    
    def __init__(self, window_size: int = 100):
        self.window_size = window_size
        self.event_counts: Dict[str, deque] = defaultdict(lambda: deque(maxlen=window_size))
        self.baselines: Dict[str, Dict[str, float]] = {}
    
    def update_baseline(self, metric_name: str, value: float):
        """Update baseline statistics for a metric"""
        self.event_counts[metric_name].append(value)
        
        if len(self.event_counts[metric_name]) >= 10:  # Minimum samples for baseline
            values = list(self.event_counts[metric_name])
            self.baselines[metric_name] = {
                'mean': statistics.mean(values),
                'stdev': statistics.stdev(values) if len(values) > 1 else 0,
                'median': statistics.median(values),
                'min': min(values),
                'max': max(values)
            }
    
    def is_anomalous(self, metric_name: str, value: float, threshold: float = 3.0) -> bool:
        """Check if value is anomalous using z-score"""
        if metric_name not in self.baselines:
            return False
        
        baseline = self.baselines[metric_name]
        if baseline['stdev'] == 0:
            return False
        
        z_score = abs(value - baseline['mean']) / baseline['stdev']
        return z_score > threshold

class SecurityIncidentDetector:
    """Automated security incident detection and response system"""
    
    def __init__(self, config: Optional[Dict[str, Any]] = None):
        self.config = config or {}
        self.detection_rules: Dict[str, DetectionRule] = {}
        self.incidents: Dict[str, SecurityIncident] = {}
        self.event_buffer: deque = deque(maxlen=10000)
        
        # Components
        self.threat_intel = ThreatIntelligence()
        self.anomaly_detector = AnomalyDetector()
        
        # Response handlers
        self.response_handlers: Dict[ResponseAction, Callable] = {}
        
        # Detection state
        self.is_running = False
        self.detection_task: Optional[asyncio.Task] = None
        
        # Load default rules and threat intelligence
        self._load_default_rules()
        self.threat_intel.load_threat_feeds()
        
        # Setup alert monitoring
        self.alert_dir = Path("security/alerts")
        self.alert_dir.mkdir(parents=True, exist_ok=True)
    
    def _load_default_rules(self):
        """Load default detection rules"""
        default_rules = [
            DetectionRule(
                rule_id="failed_auth_brute_force",
                name="Failed Authentication Brute Force",
                description="Multiple failed authentication attempts from same IP",
                category=EventCategory.AUTHENTICATION,
                severity=IncidentSeverity.HIGH,
                conditions={
                    "event_type": "authentication",
                    "result": "failed",
                    "group_by": "ip_address"
                },
                time_window=300,  # 5 minutes
                threshold=5
            ),
            DetectionRule(
                rule_id="privilege_escalation",
                name="Privilege Escalation Attempt",
                description="User attempting to access resources above their privilege level",
                category=EventCategory.AUTHORIZATION,
                severity=IncidentSeverity.HIGH,
                conditions={
                    "event_type": "authorization",
                    "result": "denied",
                    "group_by": "user_id"
                },
                time_window=600,  # 10 minutes
                threshold=3
            ),
            DetectionRule(
                rule_id="suspicious_data_access",
                name="Suspicious Data Access Pattern",
                description="Unusual data access patterns indicating potential data exfiltration",
                category=EventCategory.DATA_ACCESS,
                severity=IncidentSeverity.MEDIUM,
                conditions={
                    "event_type": "data_access",
                    "action": "read",
                    "group_by": "user_id"
                },
                time_window=3600,  # 1 hour
                threshold=50
            ),
            DetectionRule(
                rule_id="security_violation_pattern",
                name="Security Violation Pattern",
                description="Multiple security violations indicating potential attack",
                category=EventCategory.SECURITY_VIOLATION,
                severity=IncidentSeverity.CRITICAL,
                conditions={
                    "category": "security_violation",
                    "group_by": "ip_address"
                },
                time_window=900,  # 15 minutes
                threshold=2
            ),
            DetectionRule(
                rule_id="configuration_tampering",
                name="Configuration Tampering",
                description="Unauthorized configuration changes",
                category=EventCategory.CONFIGURATION_CHANGE,
                severity=IncidentSeverity.HIGH,
                conditions={
                    "event_type": "configuration_change",
                    "group_by": "user_id"
                },
                time_window=1800,  # 30 minutes
                threshold=10
            )
        ]
        
        for rule in default_rules:
            self.detection_rules[rule.rule_id] = rule
        
        logger.info(f"Loaded {len(default_rules)} default detection rules")
    
    async def start_detection(self):
        """Start incident detection"""
        if self.is_running:
            return
        
        self.is_running = True
        self.detection_task = asyncio.create_task(self._detection_loop())
        logger.info("Started security incident detection")
    
    async def stop_detection(self):
        """Stop incident detection"""
        self.is_running = False
        if self.detection_task:
            self.detection_task.cancel()
            try:
                await self.detection_task
            except asyncio.CancelledError:
                pass
        logger.info("Stopped security incident detection")
    
    async def _detection_loop(self):
        """Main detection loop"""
        while self.is_running:
            try:
                # Check for new alerts
                await self._check_alert_files()
                
                # Run detection rules
                await self._run_detection_rules()
                
                # Update anomaly baselines
                self._update_anomaly_baselines()
                
                # Clean up old incidents
                self._cleanup_old_incidents()
                
                # Sleep before next iteration
                await asyncio.sleep(30)  # Check every 30 seconds
                
            except asyncio.CancelledError:
                break
            except Exception as e:
                logger.error(f"Error in detection loop: {e}")
                await asyncio.sleep(60)
    
    async def _check_alert_files(self):
        """Check for new alert files from other components"""
        for alert_file in self.alert_dir.glob("*.json"):
            try:
                with open(alert_file, 'r') as f:
                    alert_data = json.load(f)
                
                # Process alert
                await self._process_alert(alert_data)
                
                # Remove processed alert file
                alert_file.unlink()
                
            except Exception as e:
                logger.error(f"Error processing alert file {alert_file}: {e}")
    
    async def _process_alert(self, alert_data: Dict[str, Any]):
        """Process alert and potentially create incident"""
        alert_type = alert_data.get('alert_type', 'unknown')
        
        if alert_type == 'security_threshold_exceeded':
            await self._handle_threshold_alert(alert_data)
        elif alert_type == 'vulnerability_alert':
            await self._handle_vulnerability_alert(alert_data)
        else:
            logger.warning(f"Unknown alert type: {alert_type}")
    
    async def _handle_threshold_alert(self, alert_data: Dict[str, Any]):
        """Handle security threshold exceeded alert"""
        severity_map = {
            'CRITICAL': IncidentSeverity.CRITICAL,
            'HIGH': IncidentSeverity.HIGH,
            'MEDIUM': IncidentSeverity.MEDIUM,
            'LOW': IncidentSeverity.LOW
        }
        
        severity = severity_map.get(alert_data.get('severity', 'MEDIUM'), IncidentSeverity.MEDIUM)
        
        incident = SecurityIncident(
            incident_id="",
            title=f"Security Event Threshold Exceeded - {alert_data.get('severity', 'UNKNOWN')}",
            description=f"Security event threshold exceeded: {alert_data.get('count', 0)} events of severity {alert_data.get('severity', 'UNKNOWN')}",
            severity=severity,
            status=IncidentStatus.OPEN,
            category=EventCategory.SECURITY_VIOLATION,
            created_at=datetime.utcnow(),
            updated_at=datetime.utcnow(),
            detected_by="threshold_monitor",
            affected_resources=[],
            related_events=[alert_data.get('latest_event', {}).get('event_id', '')],
            indicators={'threshold_exceeded': True, 'event_count': alert_data.get('count', 0)},
            response_actions=[]
        )
        
        await self._create_incident(incident)
    
    async def _handle_vulnerability_alert(self, alert_data: Dict[str, Any]):
        """Handle vulnerability alert"""
        critical_vulns = alert_data.get('critical_vulnerabilities', [])
        
        incident = SecurityIncident(
            incident_id="",
            title=f"Critical Vulnerabilities Detected",
            description=f"Found {len(critical_vulns)} critical vulnerabilities requiring immediate attention",
            severity=IncidentSeverity.CRITICAL,
            status=IncidentStatus.OPEN,
            category=EventCategory.VULNERABILITY,
            created_at=datetime.utcnow(),
            updated_at=datetime.utcnow(),
            detected_by="vulnerability_scanner",
            affected_resources=[v.get('package', 'unknown') for v in critical_vulns],
            related_events=[],
            indicators={'vulnerability_count': len(critical_vulns), 'scan_id': alert_data.get('scan_id')},
            response_actions=[]
        )
        
        await self._create_incident(incident)
    
    async def _run_detection_rules(self):
        """Run all enabled detection rules"""
        current_time = datetime.utcnow()
        
        for rule in self.detection_rules.values():
            if not rule.enabled:
                continue
            
            try:
                await self._evaluate_rule(rule, current_time)
            except Exception as e:
                logger.error(f"Error evaluating rule {rule.rule_id}: {e}")
    
    async def _evaluate_rule(self, rule: DetectionRule, current_time: datetime):
        """Evaluate a single detection rule"""
        # Get events within time window
        window_start = current_time - timedelta(seconds=rule.time_window)
        relevant_events = [
            event for event in self.event_buffer
            if event.timestamp >= window_start and self._matches_conditions(event, rule.conditions)
        ]
        
        if len(relevant_events) < rule.threshold:
            return
        
        # Group events if specified
        group_by = rule.conditions.get('group_by')
        if group_by:
            groups = defaultdict(list)
            for event in relevant_events:
                group_key = getattr(event, group_by, 'unknown')
                groups[group_key].append(event)
            
            # Check each group against threshold
            for group_key, group_events in groups.items():
                if len(group_events) >= rule.threshold:
                    await self._create_incident_from_rule(rule, group_events, group_key)
        else:
            # No grouping, check total count
            if len(relevant_events) >= rule.threshold:
                await self._create_incident_from_rule(rule, relevant_events)
    
    def _matches_conditions(self, event: SecurityEvent, conditions: Dict[str, Any]) -> bool:
        """Check if event matches rule conditions"""
        for key, value in conditions.items():
            if key == 'group_by':
                continue
            
            event_value = getattr(event, key, None)
            if event_value != value:
                return False
        
        return True
    
    async def _create_incident_from_rule(self, rule: DetectionRule, events: List[SecurityEvent],
                                       group_key: Optional[str] = None):
        """Create incident from detection rule match"""
        # Check if similar incident already exists
        existing_incident = self._find_similar_incident(rule, group_key)
        if existing_incident:
            # Update existing incident
            existing_incident.related_events.extend([e.event_id for e in events])
            existing_incident.updated_at = datetime.utcnow()
            return
        
        # Create new incident
        title = rule.name
        if group_key:
            title += f" - {group_key}"
        
        description = f"{rule.description}. Detected {len(events)} events in {rule.time_window} seconds."
        
        affected_resources = list(set([
            event.resource for event in events if event.resource
        ]))
        
        incident = SecurityIncident(
            incident_id="",
            title=title,
            description=description,
            severity=rule.severity,
            status=IncidentStatus.OPEN,
            category=rule.category,
            created_at=datetime.utcnow(),
            updated_at=datetime.utcnow(),
            detected_by=f"rule:{rule.rule_id}",
            affected_resources=affected_resources,
            related_events=[e.event_id for e in events],
            indicators={'rule_id': rule.rule_id, 'event_count': len(events), 'group_key': group_key},
            response_actions=[]
        )
        
        await self._create_incident(incident)
    
    def _find_similar_incident(self, rule: DetectionRule, group_key: Optional[str]) -> Optional[SecurityIncident]:
        """Find similar open incident"""
        for incident in self.incidents.values():
            if (incident.status in [IncidentStatus.OPEN, IncidentStatus.INVESTIGATING] and
                incident.indicators.get('rule_id') == rule.rule_id and
                incident.indicators.get('group_key') == group_key):
                return incident
        return None
    
    async def _create_incident(self, incident: SecurityIncident):
        """Create new security incident"""
        self.incidents[incident.incident_id] = incident
        
        # Log incident creation
        logger.critical(f"SECURITY INCIDENT CREATED: {incident.incident_id} - {incident.title}")
        
        # Determine and execute response actions
        response_actions = self._determine_response_actions(incident)
        incident.response_actions = response_actions
        
        for action in response_actions:
            await self._execute_response_action(action, incident)
        
        # Save incident to file
        await self._save_incident(incident)
    
    def _determine_response_actions(self, incident: SecurityIncident) -> List[str]:
        """Determine appropriate response actions for incident"""
        actions = [ResponseAction.ALERT.value]  # Always alert
        
        # Add actions based on severity and category
        if incident.severity == IncidentSeverity.CRITICAL:
            actions.append(ResponseAction.ESCALATE.value)
            
            if incident.category == EventCategory.AUTHENTICATION:
                actions.append(ResponseAction.BLOCK_IP.value)
            elif incident.category == EventCategory.SECURITY_VIOLATION:
                actions.append(ResponseAction.QUARANTINE_RESOURCE.value)
        
        elif incident.severity == IncidentSeverity.HIGH:
            if incident.category == EventCategory.AUTHENTICATION:
                actions.append(ResponseAction.BLOCK_IP.value)
            elif incident.category == EventCategory.AUTHORIZATION:
                actions.append(ResponseAction.DISABLE_USER.value)
        
        return actions
    
    async def _execute_response_action(self, action: str, incident: SecurityIncident):
        """Execute automated response action"""
        try:
            if action == ResponseAction.ALERT.value:
                await self._send_alert(incident)
            elif action == ResponseAction.BLOCK_IP.value:
                await self._block_ip(incident)
            elif action == ResponseAction.DISABLE_USER.value:
                await self._disable_user(incident)
            elif action == ResponseAction.QUARANTINE_RESOURCE.value:
                await self._quarantine_resource(incident)
            elif action == ResponseAction.ESCALATE.value:
                await self._escalate_incident(incident)
            
            logger.info(f"Executed response action {action} for incident {incident.incident_id}")
            
        except Exception as e:
            logger.error(f"Failed to execute response action {action}: {e}")
    
    async def _send_alert(self, incident: SecurityIncident):
        """Send alert notification"""
        alert_data = {
            'incident_id': incident.incident_id,
            'title': incident.title,
            'severity': incident.severity.value,
            'category': incident.category.value,
            'created_at': incident.created_at.isoformat(),
            'description': incident.description,
            'affected_resources': incident.affected_resources
        }
        
        # Save alert for notification system
        alert_file = Path("security/notifications") / f"incident_alert_{incident.incident_id}.json"
        alert_file.parent.mkdir(parents=True, exist_ok=True)
        
        with open(alert_file, 'w') as f:
            json.dump(alert_data, f, indent=2, default=str)
    
    async def _block_ip(self, incident: SecurityIncident):
        """Block IP address (placeholder implementation)"""
        # In a real implementation, this would integrate with firewall/WAF
        logger.warning(f"IP blocking requested for incident {incident.incident_id}")
    
    async def _disable_user(self, incident: SecurityIncident):
        """Disable user account (placeholder implementation)"""
        # In a real implementation, this would integrate with identity management
        logger.warning(f"User disabling requested for incident {incident.incident_id}")
    
    async def _quarantine_resource(self, incident: SecurityIncident):
        """Quarantine affected resource (placeholder implementation)"""
        # In a real implementation, this would isolate the resource
        logger.warning(f"Resource quarantine requested for incident {incident.incident_id}")
    
    async def _escalate_incident(self, incident: SecurityIncident):
        """Escalate incident to security team"""
        escalation_data = {
            'incident_id': incident.incident_id,
            'escalation_reason': 'Critical severity incident',
            'escalated_at': datetime.utcnow().isoformat(),
            'incident_data': asdict(incident)
        }
        
        # Save escalation for notification system
        escalation_file = Path("security/escalations") / f"escalation_{incident.incident_id}.json"
        escalation_file.parent.mkdir(parents=True, exist_ok=True)
        
        with open(escalation_file, 'w') as f:
            json.dump(escalation_data, f, indent=2, default=str)
    
    async def _save_incident(self, incident: SecurityIncident):
        """Save incident to persistent storage"""
        incident_file = Path("security/incidents") / f"{incident.incident_id}.json"
        incident_file.parent.mkdir(parents=True, exist_ok=True)
        
        with open(incident_file, 'w') as f:
            json.dump(asdict(incident), f, indent=2, default=str)
    
    def _update_anomaly_baselines(self):
        """Update anomaly detection baselines"""
        current_time = datetime.utcnow()
        hour_ago = current_time - timedelta(hours=1)
        
        # Count events by type in last hour
        recent_events = [e for e in self.event_buffer if e.timestamp >= hour_ago]
        
        event_counts = defaultdict(int)
        for event in recent_events:
            event_counts[event.event_type] += 1
        
        # Update baselines
        for event_type, count in event_counts.items():
            self.anomaly_detector.update_baseline(f"events_per_hour_{event_type}", count)
    
    def _cleanup_old_incidents(self):
        """Clean up old resolved incidents"""
        cutoff_time = datetime.utcnow() - timedelta(days=30)
        
        to_remove = []
        for incident_id, incident in self.incidents.items():
            if (incident.status == IncidentStatus.CLOSED and 
                incident.closed_at and incident.closed_at < cutoff_time):
                to_remove.append(incident_id)
        
        for incident_id in to_remove:
            del self.incidents[incident_id]
        
        if to_remove:
            logger.info(f"Cleaned up {len(to_remove)} old incidents")
    
    def process_security_event(self, event: SecurityEvent):
        """Process incoming security event"""
        self.event_buffer.append(event)
        
        # Check for immediate threats
        self._check_immediate_threats(event)
    
    def _check_immediate_threats(self, event: SecurityEvent):
        """Check for immediate security threats"""
        # Check against threat intelligence
        if event.ip_address and self.threat_intel.is_malicious_ip(event.ip_address):
            asyncio.create_task(self._create_threat_intel_incident(event, "malicious_ip"))
        
        # Check for suspicious patterns
        if event.description and self.threat_intel.contains_suspicious_pattern(event.description):
            asyncio.create_task(self._create_threat_intel_incident(event, "suspicious_pattern"))
    
    async def _create_threat_intel_incident(self, event: SecurityEvent, threat_type: str):
        """Create incident based on threat intelligence match"""
        incident = SecurityIncident(
            incident_id="",
            title=f"Threat Intelligence Match - {threat_type}",
            description=f"Event matched threat intelligence indicator: {threat_type}",
            severity=IncidentSeverity.HIGH,
            status=IncidentStatus.OPEN,
            category=EventCategory.SECURITY_VIOLATION,
            created_at=datetime.utcnow(),
            updated_at=datetime.utcnow(),
            detected_by="threat_intelligence",
            affected_resources=[event.resource] if event.resource else [],
            related_events=[event.event_id],
            indicators={'threat_type': threat_type, 'matched_indicator': True},
            response_actions=[]
        )
        
        await self._create_incident(incident)
    
    def add_detection_rule(self, rule: DetectionRule):
        """Add custom detection rule"""
        self.detection_rules[rule.rule_id] = rule
        logger.info(f"Added detection rule: {rule.rule_id}")
    
    def remove_detection_rule(self, rule_id: str):
        """Remove detection rule"""
        if rule_id in self.detection_rules:
            del self.detection_rules[rule_id]
            logger.info(f"Removed detection rule: {rule_id}")
    
    def get_incident(self, incident_id: str) -> Optional[SecurityIncident]:
        """Get incident by ID"""
        return self.incidents.get(incident_id)
    
    def list_incidents(self, status: Optional[IncidentStatus] = None,
                      severity: Optional[IncidentSeverity] = None,
                      limit: int = 100) -> List[SecurityIncident]:
        """List incidents with optional filters"""
        incidents = list(self.incidents.values())
        
        if status:
            incidents = [i for i in incidents if i.status == status]
        
        if severity:
            incidents = [i for i in incidents if i.severity == severity]
        
        # Sort by creation time (newest first)
        incidents.sort(key=lambda x: x.created_at, reverse=True)
        
        return incidents[:limit]
    
    def update_incident_status(self, incident_id: str, status: IncidentStatus,
                              notes: Optional[str] = None, assignee: Optional[str] = None):
        """Update incident status"""
        incident = self.incidents.get(incident_id)
        if not incident:
            raise ValueError(f"Incident {incident_id} not found")
        
        incident.status = status
        incident.updated_at = datetime.utcnow()
        
        if notes:
            incident.resolution_notes = notes
        
        if assignee:
            incident.assignee = assignee
        
        if status == IncidentStatus.CLOSED:
            incident.closed_at = datetime.utcnow()
        
        # Save updated incident
        asyncio.create_task(self._save_incident(incident))
        
        logger.info(f"Updated incident {incident_id} status to {status.value}")
    
    def get_detection_statistics(self) -> Dict[str, Any]:
        """Get detection system statistics"""
        open_incidents = [i for i in self.incidents.values() if i.status == IncidentStatus.OPEN]
        
        stats = {
            'status': 'active' if self.is_running else 'stopped',
            'total_incidents': len(self.incidents),
            'open_incidents': len(open_incidents),
            'detection_rules': len(self.detection_rules),
            'enabled_rules': len([r for r in self.detection_rules.values() if r.enabled]),
            'event_buffer_size': len(self.event_buffer),
            'incidents_by_severity': {},
            'incidents_by_category': {},
            'threat_intel_last_update': self.threat_intel.last_update.isoformat()
        }
        
        # Count by severity
        for severity in IncidentSeverity:
            count = len([i for i in self.incidents.values() if i.severity == severity])
            stats['incidents_by_severity'][severity.value] = count
        
        # Count by category
        for category in EventCategory:
            count = len([i for i in self.incidents.values() if i.category == category])
            stats['incidents_by_category'][category.value] = count
        
        return stats