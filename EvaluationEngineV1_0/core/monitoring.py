"""
Monitoring and observability system for the Multi-Turn Evaluation Engine.

This module provides comprehensive monitoring capabilities including performance tracking,
resource monitoring, health checks, and system status reporting.
"""

import time
import psutil
import threading
from datetime import datetime, timedelta
from typing import Dict, Any, List, Optional, Callable, Union
from dataclasses import dataclass, field
from enum import Enum
from collections import defaultdict, deque
import json
import logging


class HealthStatus(Enum):
    """Health status levels."""
    HEALTHY = "healthy"
    WARNING = "warning"
    CRITICAL = "critical"
    UNKNOWN = "unknown"


class MetricType(Enum):
    """Types of metrics that can be collected."""
    COUNTER = "counter"
    GAUGE = "gauge"
    HISTOGRAM = "histogram"
    TIMER = "timer"


@dataclass
class MetricValue:
    """A single metric value with metadata."""
    name: str
    value: Union[int, float]
    metric_type: MetricType
    timestamp: datetime
    tags: Dict[str, str] = field(default_factory=dict)
    unit: Optional[str] = None


@dataclass
class HealthCheck:
    """Health check definition."""
    name: str
    check_function: Callable[[], bool]
    description: str
    timeout: float = 5.0
    critical: bool = False
    tags: Dict[str, str] = field(default_factory=dict)


@dataclass
class HealthCheckResult:
    """Result of a health check."""
    name: str
    status: HealthStatus
    message: str
    timestamp: datetime
    duration: float
    critical: bool = False
    details: Dict[str, Any] = field(default_factory=dict)


@dataclass
class SystemStatus:
    """Overall system status."""
    status: HealthStatus
    timestamp: datetime
    health_checks: List[HealthCheckResult]
    system_metrics: Dict[str, Any]
    uptime: float
    version: str = "1.0.0"


class ResourceMonitor:
    """Monitors system resource usage."""
    
    def __init__(self, collection_interval: float = 1.0):
        self.collection_interval = collection_interval
        self.metrics_history: Dict[str, deque] = defaultdict(lambda: deque(maxlen=1000))
        self.running = False
        self.thread: Optional[threading.Thread] = None
        self.start_time = time.time()
    
    def start(self):
        """Start resource monitoring."""
        if not self.running:
            self.running = True
            self.thread = threading.Thread(target=self._collect_metrics, daemon=True)
            self.thread.start()
    
    def stop(self):
        """Stop resource monitoring."""
        self.running = False
        if self.thread:
            self.thread.join(timeout=5.0)
    
    def _collect_metrics(self):
        """Collect system metrics in background thread."""
        while self.running:
            try:
                timestamp = datetime.now()
                
                # CPU metrics
                cpu_percent = psutil.cpu_percent(interval=None)
                cpu_count = psutil.cpu_count()
                
                # Memory metrics
                memory = psutil.virtual_memory()
                memory_percent = memory.percent
                memory_used = memory.used
                memory_available = memory.available
                
                # Disk metrics
                disk = psutil.disk_usage('/')
                disk_percent = disk.percent
                disk_used = disk.used
                disk_free = disk.free
                
                # Network metrics (if available)
                try:
                    network = psutil.net_io_counters()
                    bytes_sent = network.bytes_sent
                    bytes_recv = network.bytes_recv
                except:
                    bytes_sent = bytes_recv = 0
                
                # Store metrics
                metrics = {
                    'cpu_percent': cpu_percent,
                    'cpu_count': cpu_count,
                    'memory_percent': memory_percent,
                    'memory_used': memory_used,
                    'memory_available': memory_available,
                    'disk_percent': disk_percent,
                    'disk_used': disk_used,
                    'disk_free': disk_free,
                    'network_bytes_sent': bytes_sent,
                    'network_bytes_recv': bytes_recv,
                    'timestamp': timestamp
                }
                
                for metric_name, value in metrics.items():
                    if metric_name != 'timestamp':
                        self.metrics_history[metric_name].append((timestamp, value))
                
            except Exception as e:
                logging.error(f"Error collecting system metrics: {e}")
            
            time.sleep(self.collection_interval)
    
    def get_current_metrics(self) -> Dict[str, Any]:
        """Get current system metrics."""
        try:
            return {
                'cpu_percent': psutil.cpu_percent(),
                'memory_percent': psutil.virtual_memory().percent,
                'disk_percent': psutil.disk_usage('/').percent,
                'uptime': time.time() - self.start_time,
                'timestamp': datetime.now()
            }
        except Exception as e:
            logging.error(f"Error getting current metrics: {e}")
            return {}
    
    def get_metric_history(self, metric_name: str, duration: timedelta = None) -> List[tuple]:
        """Get historical data for a specific metric."""
        if metric_name not in self.metrics_history:
            return []
        
        history = list(self.metrics_history[metric_name])
        
        if duration:
            cutoff_time = datetime.now() - duration
            history = [(ts, val) for ts, val in history if ts >= cutoff_time]
        
        return history
    
    def get_metric_stats(self, metric_name: str, duration: timedelta = None) -> Dict[str, float]:
        """Get statistical summary for a metric."""
        history = self.get_metric_history(metric_name, duration)
        
        if not history:
            return {}
        
        values = [val for _, val in history]
        
        return {
            'min': min(values),
            'max': max(values),
            'avg': sum(values) / len(values),
            'count': len(values),
            'current': values[-1] if values else 0
        }


class PerformanceTracker:
    """Tracks performance metrics for evaluations."""
    
    def __init__(self):
        self.metrics: Dict[str, List[MetricValue]] = defaultdict(list)
        self.active_timers: Dict[str, float] = {}
        self.counters: Dict[str, int] = defaultdict(int)
        self.gauges: Dict[str, float] = {}
    
    def increment_counter(self, name: str, value: int = 1, tags: Dict[str, str] = None):
        """Increment a counter metric."""
        self.counters[name] += value
        self._record_metric(name, self.counters[name], MetricType.COUNTER, tags)
    
    def set_gauge(self, name: str, value: float, tags: Dict[str, str] = None):
        """Set a gauge metric value."""
        self.gauges[name] = value
        self._record_metric(name, value, MetricType.GAUGE, tags)
    
    def start_timer(self, name: str) -> str:
        """Start a timer and return timer ID."""
        timer_id = f"{name}_{int(time.time() * 1000000)}"
        self.active_timers[timer_id] = time.time()
        return timer_id
    
    def stop_timer(self, timer_id: str, tags: Dict[str, str] = None) -> float:
        """Stop a timer and record the duration."""
        if timer_id not in self.active_timers:
            return 0.0
        
        duration = time.time() - self.active_timers[timer_id]
        del self.active_timers[timer_id]
        
        # Extract metric name from timer ID
        name = timer_id.rsplit('_', 1)[0]
        self._record_metric(name, duration, MetricType.TIMER, tags)
        
        return duration
    
    def record_histogram(self, name: str, value: float, tags: Dict[str, str] = None):
        """Record a histogram value."""
        self._record_metric(name, value, MetricType.HISTOGRAM, tags)
    
    def _record_metric(self, name: str, value: Union[int, float], 
                      metric_type: MetricType, tags: Dict[str, str] = None):
        """Record a metric value."""
        metric = MetricValue(
            name=name,
            value=value,
            metric_type=metric_type,
            timestamp=datetime.now(),
            tags=tags or {}
        )
        self.metrics[name].append(metric)
    
    def get_metric_summary(self, name: str, duration: timedelta = None) -> Dict[str, Any]:
        """Get summary statistics for a metric."""
        if name not in self.metrics:
            return {}
        
        metrics = self.metrics[name]
        
        if duration:
            cutoff_time = datetime.now() - duration
            metrics = [m for m in metrics if m.timestamp >= cutoff_time]
        
        if not metrics:
            return {}
        
        values = [m.value for m in metrics]
        
        return {
            'count': len(values),
            'min': min(values),
            'max': max(values),
            'avg': sum(values) / len(values),
            'sum': sum(values),
            'latest': values[-1],
            'metric_type': metrics[0].metric_type.value
        }
    
    def get_all_metrics(self) -> Dict[str, Any]:
        """Get all current metric values."""
        return {
            'counters': dict(self.counters),
            'gauges': dict(self.gauges),
            'active_timers': len(self.active_timers)
        }


class HealthChecker:
    """Manages health checks for system components."""
    
    def __init__(self):
        self.health_checks: Dict[str, HealthCheck] = {}
        self.last_results: Dict[str, HealthCheckResult] = {}
    
    def register_health_check(self, health_check: HealthCheck):
        """Register a new health check."""
        self.health_checks[health_check.name] = health_check
    
    def unregister_health_check(self, name: str):
        """Unregister a health check."""
        if name in self.health_checks:
            del self.health_checks[name]
        if name in self.last_results:
            del self.last_results[name]
    
    def run_health_check(self, name: str) -> HealthCheckResult:
        """Run a specific health check."""
        if name not in self.health_checks:
            return HealthCheckResult(
                name=name,
                status=HealthStatus.UNKNOWN,
                message=f"Health check '{name}' not found",
                timestamp=datetime.now(),
                duration=0.0
            )
        
        health_check = self.health_checks[name]
        start_time = time.time()
        
        try:
            # Run the health check with timeout
            result = self._run_with_timeout(health_check.check_function, health_check.timeout)
            duration = time.time() - start_time
            
            if result:
                status = HealthStatus.HEALTHY
                message = f"Health check '{name}' passed"
            else:
                status = HealthStatus.CRITICAL if health_check.critical else HealthStatus.WARNING
                message = f"Health check '{name}' failed"
            
            result = HealthCheckResult(
                name=name,
                status=status,
                message=message,
                timestamp=datetime.now(),
                duration=duration,
                critical=health_check.critical
            )
            
        except Exception as e:
            duration = time.time() - start_time
            result = HealthCheckResult(
                name=name,
                status=HealthStatus.CRITICAL,
                message=f"Health check '{name}' error: {str(e)}",
                timestamp=datetime.now(),
                duration=duration,
                critical=health_check.critical,
                details={'error': str(e)}
            )
        
        self.last_results[name] = result
        return result
    
    def run_all_health_checks(self) -> List[HealthCheckResult]:
        """Run all registered health checks."""
        results = []
        for name in self.health_checks:
            result = self.run_health_check(name)
            results.append(result)
        return results
    
    def get_overall_status(self) -> HealthStatus:
        """Get overall system health status."""
        if not self.last_results:
            return HealthStatus.UNKNOWN
        
        has_critical = any(r.status == HealthStatus.CRITICAL for r in self.last_results.values())
        has_warning = any(r.status == HealthStatus.WARNING for r in self.last_results.values())
        
        if has_critical:
            return HealthStatus.CRITICAL
        elif has_warning:
            return HealthStatus.WARNING
        else:
            return HealthStatus.HEALTHY
    
    def _run_with_timeout(self, func: Callable, timeout: float) -> bool:
        """Run function with timeout."""
        import signal
        
        def timeout_handler(signum, frame):
            raise TimeoutError("Health check timed out")
        
        # Set up timeout
        old_handler = signal.signal(signal.SIGALRM, timeout_handler)
        signal.alarm(int(timeout))
        
        try:
            result = func()
            signal.alarm(0)  # Cancel alarm
            return result
        finally:
            signal.signal(signal.SIGALRM, old_handler)


class AlertManager:
    """Manages alerts and notifications for monitoring events."""
    
    def __init__(self):
        self.alert_rules: List[Dict[str, Any]] = []
        self.active_alerts: Dict[str, Dict[str, Any]] = {}
        self.alert_handlers: List[Callable] = []
    
    def add_alert_rule(self, name: str, condition: Callable[[Dict[str, Any]], bool], 
                      message: str, severity: str = "warning"):
        """Add an alert rule."""
        self.alert_rules.append({
            'name': name,
            'condition': condition,
            'message': message,
            'severity': severity
        })
    
    def add_alert_handler(self, handler: Callable[[str, str, str], None]):
        """Add an alert handler function."""
        self.alert_handlers.append(handler)
    
    def check_alerts(self, metrics: Dict[str, Any]):
        """Check all alert rules against current metrics."""
        for rule in self.alert_rules:
            try:
                if rule['condition'](metrics):
                    self._trigger_alert(rule['name'], rule['message'], rule['severity'])
                else:
                    self._resolve_alert(rule['name'])
            except Exception as e:
                logging.error(f"Error checking alert rule '{rule['name']}': {e}")
    
    def _trigger_alert(self, name: str, message: str, severity: str):
        """Trigger an alert."""
        if name not in self.active_alerts:
            self.active_alerts[name] = {
                'message': message,
                'severity': severity,
                'triggered_at': datetime.now(),
                'count': 1
            }
            
            # Notify handlers
            for handler in self.alert_handlers:
                try:
                    handler(name, message, severity)
                except Exception as e:
                    logging.error(f"Error in alert handler: {e}")
        else:
            self.active_alerts[name]['count'] += 1
    
    def _resolve_alert(self, name: str):
        """Resolve an active alert."""
        if name in self.active_alerts:
            del self.active_alerts[name]
    
    def get_active_alerts(self) -> Dict[str, Dict[str, Any]]:
        """Get all active alerts."""
        return self.active_alerts.copy()


class MonitoringSystem:
    """Main monitoring system that coordinates all monitoring components."""
    
    def __init__(self):
        self.resource_monitor = ResourceMonitor()
        self.performance_tracker = PerformanceTracker()
        self.health_checker = HealthChecker()
        self.alert_manager = AlertManager()
        self.start_time = datetime.now()
        self._setup_default_health_checks()
        self._setup_default_alerts()
    
    def start(self):
        """Start the monitoring system."""
        self.resource_monitor.start()
        logging.info("Monitoring system started")
    
    def stop(self):
        """Stop the monitoring system."""
        self.resource_monitor.stop()
        logging.info("Monitoring system stopped")
    
    def get_system_status(self) -> SystemStatus:
        """Get comprehensive system status."""
        health_results = self.health_checker.run_all_health_checks()
        overall_status = self.health_checker.get_overall_status()
        system_metrics = self.resource_monitor.get_current_metrics()
        uptime = (datetime.now() - self.start_time).total_seconds()
        
        # Check alerts
        all_metrics = {
            **system_metrics,
            **self.performance_tracker.get_all_metrics()
        }
        self.alert_manager.check_alerts(all_metrics)
        
        return SystemStatus(
            status=overall_status,
            timestamp=datetime.now(),
            health_checks=health_results,
            system_metrics=system_metrics,
            uptime=uptime
        )
    
    def get_performance_summary(self) -> Dict[str, Any]:
        """Get performance metrics summary."""
        return {
            'resource_metrics': self.resource_monitor.get_current_metrics(),
            'performance_metrics': self.performance_tracker.get_all_metrics(),
            'active_alerts': self.alert_manager.get_active_alerts(),
            'uptime': (datetime.now() - self.start_time).total_seconds()
        }
    
    def _setup_default_health_checks(self):
        """Set up default health checks."""
        # CPU health check
        def cpu_health_check():
            cpu_percent = psutil.cpu_percent(interval=1)
            return cpu_percent < 90.0
        
        self.health_checker.register_health_check(HealthCheck(
            name="cpu_usage",
            check_function=cpu_health_check,
            description="Check CPU usage is below 90%",
            critical=True
        ))
        
        # Memory health check
        def memory_health_check():
            memory_percent = psutil.virtual_memory().percent
            return memory_percent < 85.0
        
        self.health_checker.register_health_check(HealthCheck(
            name="memory_usage",
            check_function=memory_health_check,
            description="Check memory usage is below 85%",
            critical=True
        ))
        
        # Disk health check
        def disk_health_check():
            disk_percent = psutil.disk_usage('/').percent
            return disk_percent < 90.0
        
        self.health_checker.register_health_check(HealthCheck(
            name="disk_usage",
            check_function=disk_health_check,
            description="Check disk usage is below 90%",
            critical=False
        ))
    
    def _setup_default_alerts(self):
        """Set up default alert rules."""
        # High CPU usage alert
        self.alert_manager.add_alert_rule(
            name="high_cpu_usage",
            condition=lambda m: m.get('cpu_percent', 0) > 80,
            message="CPU usage is above 80%",
            severity="warning"
        )
        
        # High memory usage alert
        self.alert_manager.add_alert_rule(
            name="high_memory_usage",
            condition=lambda m: m.get('memory_percent', 0) > 80,
            message="Memory usage is above 80%",
            severity="warning"
        )
        
        # High disk usage alert
        self.alert_manager.add_alert_rule(
            name="high_disk_usage",
            condition=lambda m: m.get('disk_percent', 0) > 85,
            message="Disk usage is above 85%",
            severity="critical"
        )


# Global monitoring system instance
_global_monitoring_system: Optional[MonitoringSystem] = None


def get_monitoring_system() -> MonitoringSystem:
    """Get the global monitoring system instance."""
    global _global_monitoring_system
    if _global_monitoring_system is None:
        _global_monitoring_system = MonitoringSystem()
    return _global_monitoring_system


def set_monitoring_system(system: MonitoringSystem):
    """Set the global monitoring system instance."""
    global _global_monitoring_system
    _global_monitoring_system = system