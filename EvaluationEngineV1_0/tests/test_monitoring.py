"""
Tests for the monitoring and observability system.

This module tests all aspects of monitoring including performance tracking,
resource monitoring, health checks, and alerting.
"""

import pytest
import time
import threading
from datetime import datetime, timedelta
from unittest.mock import Mock, patch, MagicMock

from EvaluationEngineV1_0.core.monitoring import (
    MonitoringSystem, ResourceMonitor, PerformanceTracker, HealthChecker,
    AlertManager, HealthStatus, MetricType, MetricValue, HealthCheck,
    HealthCheckResult, SystemStatus, get_monitoring_system, set_monitoring_system
)


class TestMetricValue:
    """Test cases for MetricValue dataclass."""
    
    def test_metric_value_creation(self):
        """Test MetricValue creation."""
        timestamp = datetime.now()
        metric = MetricValue(
            name="test_metric",
            value=42.5,
            metric_type=MetricType.GAUGE,
            timestamp=timestamp,
            tags={"env": "test"},
            unit="seconds"
        )
        
        assert metric.name == "test_metric"
        assert metric.value == 42.5
        assert metric.metric_type == MetricType.GAUGE
        assert metric.timestamp == timestamp
        assert metric.tags == {"env": "test"}
        assert metric.unit == "seconds"


class TestResourceMonitor:
    """Test cases for ResourceMonitor class."""
    
    def test_init(self):
        """Test ResourceMonitor initialization."""
        monitor = ResourceMonitor(collection_interval=2.0)
        assert monitor.collection_interval == 2.0
        assert not monitor.running
        assert monitor.thread is None
    
    @patch('psutil.cpu_percent')
    @patch('psutil.virtual_memory')
    @patch('psutil.disk_usage')
    def test_get_current_metrics(self, mock_disk, mock_memory, mock_cpu):
        """Test getting current system metrics."""
        # Mock system metrics
        mock_cpu.return_value = 25.5
        mock_memory.return_value = Mock(percent=60.0)
        mock_disk.return_value = Mock(percent=45.0)
        
        monitor = ResourceMonitor()
        metrics = monitor.get_current_metrics()
        
        assert 'cpu_percent' in metrics
        assert 'memory_percent' in metrics
        assert 'disk_percent' in metrics
        assert 'uptime' in metrics
        assert 'timestamp' in metrics
        assert metrics['cpu_percent'] == 25.5
        assert metrics['memory_percent'] == 60.0
        assert metrics['disk_percent'] == 45.0
    
    def test_start_stop(self):
        """Test starting and stopping resource monitoring."""
        monitor = ResourceMonitor()
        
        # Test start
        monitor.start()
        assert monitor.running
        assert monitor.thread is not None
        assert monitor.thread.is_alive()
        
        # Test stop
        monitor.stop()
        assert not monitor.running
    
    def test_get_metric_history_empty(self):
        """Test getting metric history when empty."""
        monitor = ResourceMonitor()
        history = monitor.get_metric_history("cpu_percent")
        assert history == []
    
    def test_get_metric_stats_empty(self):
        """Test getting metric stats when empty."""
        monitor = ResourceMonitor()
        stats = monitor.get_metric_stats("cpu_percent")
        assert stats == {}
    
    def test_get_metric_stats_with_data(self):
        """Test getting metric stats with data."""
        monitor = ResourceMonitor()
        
        # Manually add some test data
        now = datetime.now()
        test_data = [
            (now - timedelta(seconds=3), 10.0),
            (now - timedelta(seconds=2), 20.0),
            (now - timedelta(seconds=1), 30.0),
            (now, 40.0)
        ]
        monitor.metrics_history['cpu_percent'].extend(test_data)
        
        stats = monitor.get_metric_stats('cpu_percent')
        
        assert stats['min'] == 10.0
        assert stats['max'] == 40.0
        assert stats['avg'] == 25.0
        assert stats['count'] == 4
        assert stats['current'] == 40.0


class TestPerformanceTracker:
    """Test cases for PerformanceTracker class."""
    
    def test_init(self):
        """Test PerformanceTracker initialization."""
        tracker = PerformanceTracker()
        assert len(tracker.metrics) == 0
        assert len(tracker.active_timers) == 0
        assert len(tracker.counters) == 0
        assert len(tracker.gauges) == 0
    
    def test_increment_counter(self):
        """Test incrementing counter metrics."""
        tracker = PerformanceTracker()
        
        tracker.increment_counter("requests", 1)
        tracker.increment_counter("requests", 5)
        
        assert tracker.counters["requests"] == 6
        assert len(tracker.metrics["requests"]) == 2
        assert tracker.metrics["requests"][0].metric_type == MetricType.COUNTER
    
    def test_set_gauge(self):
        """Test setting gauge metrics."""
        tracker = PerformanceTracker()
        
        tracker.set_gauge("temperature", 25.5)
        tracker.set_gauge("temperature", 26.0)
        
        assert tracker.gauges["temperature"] == 26.0
        assert len(tracker.metrics["temperature"]) == 2
        assert tracker.metrics["temperature"][0].metric_type == MetricType.GAUGE
    
    def test_timer_operations(self):
        """Test timer start/stop operations."""
        tracker = PerformanceTracker()
        
        timer_id = tracker.start_timer("operation_duration")
        assert timer_id in tracker.active_timers
        
        time.sleep(0.01)  # Small delay
        duration = tracker.stop_timer(timer_id)
        
        assert timer_id not in tracker.active_timers
        assert duration > 0
        assert len(tracker.metrics["operation_duration"]) == 1
        assert tracker.metrics["operation_duration"][0].metric_type == MetricType.TIMER
    
    def test_stop_nonexistent_timer(self):
        """Test stopping a non-existent timer."""
        tracker = PerformanceTracker()
        duration = tracker.stop_timer("nonexistent")
        assert duration == 0.0
    
    def test_record_histogram(self):
        """Test recording histogram values."""
        tracker = PerformanceTracker()
        
        tracker.record_histogram("response_time", 0.5)
        tracker.record_histogram("response_time", 1.2)
        
        assert len(tracker.metrics["response_time"]) == 2
        assert tracker.metrics["response_time"][0].metric_type == MetricType.HISTOGRAM
    
    def test_get_metric_summary(self):
        """Test getting metric summary."""
        tracker = PerformanceTracker()
        
        # Add some test data
        tracker.record_histogram("test_metric", 10.0)
        tracker.record_histogram("test_metric", 20.0)
        tracker.record_histogram("test_metric", 30.0)
        
        summary = tracker.get_metric_summary("test_metric")
        
        assert summary['count'] == 3
        assert summary['min'] == 10.0
        assert summary['max'] == 30.0
        assert summary['avg'] == 20.0
        assert summary['sum'] == 60.0
        assert summary['latest'] == 30.0
        assert summary['metric_type'] == 'histogram'
    
    def test_get_metric_summary_empty(self):
        """Test getting metric summary for non-existent metric."""
        tracker = PerformanceTracker()
        summary = tracker.get_metric_summary("nonexistent")
        assert summary == {}
    
    def test_get_all_metrics(self):
        """Test getting all current metrics."""
        tracker = PerformanceTracker()
        
        tracker.increment_counter("requests", 5)
        tracker.set_gauge("temperature", 25.0)
        timer_id = tracker.start_timer("operation")
        
        all_metrics = tracker.get_all_metrics()
        
        assert all_metrics['counters']['requests'] == 5
        assert all_metrics['gauges']['temperature'] == 25.0
        assert all_metrics['active_timers'] == 1
        
        tracker.stop_timer(timer_id)
        all_metrics = tracker.get_all_metrics()
        assert all_metrics['active_timers'] == 0


class TestHealthChecker:
    """Test cases for HealthChecker class."""
    
    def test_init(self):
        """Test HealthChecker initialization."""
        checker = HealthChecker()
        assert len(checker.health_checks) == 0
        assert len(checker.last_results) == 0
    
    def test_register_health_check(self):
        """Test registering health checks."""
        checker = HealthChecker()
        
        def dummy_check():
            return True
        
        health_check = HealthCheck(
            name="test_check",
            check_function=dummy_check,
            description="Test health check"
        )
        
        checker.register_health_check(health_check)
        assert "test_check" in checker.health_checks
        assert checker.health_checks["test_check"] == health_check
    
    def test_unregister_health_check(self):
        """Test unregistering health checks."""
        checker = HealthChecker()
        
        def dummy_check():
            return True
        
        health_check = HealthCheck(
            name="test_check",
            check_function=dummy_check,
            description="Test health check"
        )
        
        checker.register_health_check(health_check)
        checker.unregister_health_check("test_check")
        
        assert "test_check" not in checker.health_checks
    
    def test_run_health_check_success(self):
        """Test running successful health check."""
        checker = HealthChecker()
        
        def passing_check():
            return True
        
        health_check = HealthCheck(
            name="passing_check",
            check_function=passing_check,
            description="Always passes"
        )
        
        checker.register_health_check(health_check)
        result = checker.run_health_check("passing_check")
        
        assert result.name == "passing_check"
        assert result.status == HealthStatus.HEALTHY
        assert "passed" in result.message
        assert result.duration >= 0
    
    def test_run_health_check_failure(self):
        """Test running failing health check."""
        checker = HealthChecker()
        
        def failing_check():
            return False
        
        health_check = HealthCheck(
            name="failing_check",
            check_function=failing_check,
            description="Always fails",
            critical=True
        )
        
        checker.register_health_check(health_check)
        result = checker.run_health_check("failing_check")
        
        assert result.name == "failing_check"
        assert result.status == HealthStatus.CRITICAL
        assert "failed" in result.message
        assert result.critical
    
    def test_run_health_check_exception(self):
        """Test running health check that raises exception."""
        checker = HealthChecker()
        
        def error_check():
            raise ValueError("Test error")
        
        health_check = HealthCheck(
            name="error_check",
            check_function=error_check,
            description="Raises error"
        )
        
        checker.register_health_check(health_check)
        result = checker.run_health_check("error_check")
        
        assert result.name == "error_check"
        assert result.status == HealthStatus.CRITICAL
        assert "error" in result.message
        assert "Test error" in result.message
    
    def test_run_nonexistent_health_check(self):
        """Test running non-existent health check."""
        checker = HealthChecker()
        result = checker.run_health_check("nonexistent")
        
        assert result.name == "nonexistent"
        assert result.status == HealthStatus.UNKNOWN
        assert "not found" in result.message
    
    def test_run_all_health_checks(self):
        """Test running all health checks."""
        checker = HealthChecker()
        
        def check1():
            return True
        
        def check2():
            return False
        
        checker.register_health_check(HealthCheck("check1", check1, "Check 1"))
        checker.register_health_check(HealthCheck("check2", check2, "Check 2"))
        
        results = checker.run_all_health_checks()
        
        assert len(results) == 2
        assert any(r.name == "check1" for r in results)
        assert any(r.name == "check2" for r in results)
    
    def test_get_overall_status(self):
        """Test getting overall health status."""
        checker = HealthChecker()
        
        # No checks - should be unknown
        assert checker.get_overall_status() == HealthStatus.UNKNOWN
        
        # Add passing check
        def passing_check():
            return True
        
        checker.register_health_check(HealthCheck("passing", passing_check, "Passing"))
        checker.run_health_check("passing")
        assert checker.get_overall_status() == HealthStatus.HEALTHY
        
        # Add failing non-critical check
        def warning_check():
            return False
        
        checker.register_health_check(HealthCheck("warning", warning_check, "Warning", critical=False))
        checker.run_health_check("warning")
        assert checker.get_overall_status() == HealthStatus.WARNING
        
        # Add failing critical check
        def critical_check():
            return False
        
        checker.register_health_check(HealthCheck("critical", critical_check, "Critical", critical=True))
        checker.run_health_check("critical")
        assert checker.get_overall_status() == HealthStatus.CRITICAL


class TestAlertManager:
    """Test cases for AlertManager class."""
    
    def test_init(self):
        """Test AlertManager initialization."""
        manager = AlertManager()
        assert len(manager.alert_rules) == 0
        assert len(manager.active_alerts) == 0
        assert len(manager.alert_handlers) == 0
    
    def test_add_alert_rule(self):
        """Test adding alert rules."""
        manager = AlertManager()
        
        def condition(metrics):
            return metrics.get('cpu_percent', 0) > 80
        
        manager.add_alert_rule("high_cpu", condition, "CPU usage high", "warning")
        
        assert len(manager.alert_rules) == 1
        assert manager.alert_rules[0]['name'] == "high_cpu"
        assert manager.alert_rules[0]['message'] == "CPU usage high"
        assert manager.alert_rules[0]['severity'] == "warning"
    
    def test_add_alert_handler(self):
        """Test adding alert handlers."""
        manager = AlertManager()
        
        def handler(name, message, severity):
            pass
        
        manager.add_alert_handler(handler)
        assert len(manager.alert_handlers) == 1
        assert manager.alert_handlers[0] == handler
    
    def test_check_alerts_trigger(self):
        """Test triggering alerts."""
        manager = AlertManager()
        handler_calls = []
        
        def condition(metrics):
            return metrics.get('cpu_percent', 0) > 80
        
        def handler(name, message, severity):
            handler_calls.append((name, message, severity))
        
        manager.add_alert_rule("high_cpu", condition, "CPU usage high", "warning")
        manager.add_alert_handler(handler)
        
        # Trigger alert
        manager.check_alerts({'cpu_percent': 85})
        
        assert len(manager.active_alerts) == 1
        assert "high_cpu" in manager.active_alerts
        assert len(handler_calls) == 1
        assert handler_calls[0][0] == "high_cpu"
    
    def test_check_alerts_resolve(self):
        """Test resolving alerts."""
        manager = AlertManager()
        
        def condition(metrics):
            return metrics.get('cpu_percent', 0) > 80
        
        manager.add_alert_rule("high_cpu", condition, "CPU usage high", "warning")
        
        # Trigger alert
        manager.check_alerts({'cpu_percent': 85})
        assert len(manager.active_alerts) == 1
        
        # Resolve alert
        manager.check_alerts({'cpu_percent': 70})
        assert len(manager.active_alerts) == 0
    
    def test_get_active_alerts(self):
        """Test getting active alerts."""
        manager = AlertManager()
        
        def condition(metrics):
            return metrics.get('cpu_percent', 0) > 80
        
        manager.add_alert_rule("high_cpu", condition, "CPU usage high", "warning")
        manager.check_alerts({'cpu_percent': 85})
        
        active_alerts = manager.get_active_alerts()
        assert len(active_alerts) == 1
        assert "high_cpu" in active_alerts
        assert active_alerts["high_cpu"]["message"] == "CPU usage high"
        assert active_alerts["high_cpu"]["severity"] == "warning"


class TestMonitoringSystem:
    """Test cases for MonitoringSystem class."""
    
    def test_init(self):
        """Test MonitoringSystem initialization."""
        system = MonitoringSystem()
        
        assert system.resource_monitor is not None
        assert system.performance_tracker is not None
        assert system.health_checker is not None
        assert system.alert_manager is not None
        assert system.start_time is not None
        
        # Check default health checks are registered
        assert len(system.health_checker.health_checks) > 0
        assert "cpu_usage" in system.health_checker.health_checks
        assert "memory_usage" in system.health_checker.health_checks
        assert "disk_usage" in system.health_checker.health_checks
        
        # Check default alerts are configured
        assert len(system.alert_manager.alert_rules) > 0
    
    def test_start_stop(self):
        """Test starting and stopping monitoring system."""
        system = MonitoringSystem()
        
        system.start()
        assert system.resource_monitor.running
        
        system.stop()
        assert not system.resource_monitor.running
    
    @patch('psutil.cpu_percent')
    @patch('psutil.virtual_memory')
    @patch('psutil.disk_usage')
    def test_get_system_status(self, mock_disk, mock_memory, mock_cpu):
        """Test getting system status."""
        # Mock system metrics
        mock_cpu.return_value = 25.0
        mock_memory.return_value = Mock(percent=60.0)
        mock_disk.return_value = Mock(percent=45.0)
        
        system = MonitoringSystem()
        status = system.get_system_status()
        
        assert isinstance(status, SystemStatus)
        assert status.status in HealthStatus
        assert len(status.health_checks) > 0
        assert 'cpu_percent' in status.system_metrics
        assert status.uptime >= 0
    
    @patch('psutil.cpu_percent')
    @patch('psutil.virtual_memory')
    @patch('psutil.disk_usage')
    def test_get_performance_summary(self, mock_disk, mock_memory, mock_cpu):
        """Test getting performance summary."""
        # Mock system metrics
        mock_cpu.return_value = 25.0
        mock_memory.return_value = Mock(percent=60.0)
        mock_disk.return_value = Mock(percent=45.0)
        
        system = MonitoringSystem()
        summary = system.get_performance_summary()
        
        assert 'resource_metrics' in summary
        assert 'performance_metrics' in summary
        assert 'active_alerts' in summary
        assert 'uptime' in summary
        assert summary['uptime'] >= 0


class TestGlobalMonitoringSystem:
    """Test cases for global monitoring system functions."""
    
    def test_get_monitoring_system_singleton(self):
        """Test that get_monitoring_system returns singleton."""
        system1 = get_monitoring_system()
        system2 = get_monitoring_system()
        assert system1 is system2
    
    def test_set_monitoring_system(self):
        """Test setting custom global monitoring system."""
        custom_system = MonitoringSystem()
        set_monitoring_system(custom_system)
        
        retrieved_system = get_monitoring_system()
        assert retrieved_system is custom_system


class TestMonitoringIntegration:
    """Integration tests for monitoring system."""
    
    @patch('psutil.cpu_percent')
    @patch('psutil.virtual_memory')
    @patch('psutil.disk_usage')
    def test_full_monitoring_cycle(self, mock_disk, mock_memory, mock_cpu):
        """Test complete monitoring cycle."""
        # Mock high resource usage to trigger alerts
        mock_cpu.return_value = 85.0
        mock_memory.return_value = Mock(percent=85.0)
        mock_disk.return_value = Mock(percent=90.0)
        
        system = MonitoringSystem()
        
        # Start monitoring
        system.start()
        
        # Get system status (should trigger alerts)
        status = system.get_system_status()
        
        # Check that alerts were triggered
        active_alerts = system.alert_manager.get_active_alerts()
        assert len(active_alerts) > 0
        
        # Check health status reflects issues
        assert status.status in [HealthStatus.WARNING, HealthStatus.CRITICAL]
        
        # Stop monitoring
        system.stop()
    
    def test_performance_tracking_integration(self):
        """Test performance tracking integration."""
        system = MonitoringSystem()
        
        # Track some performance metrics
        system.performance_tracker.increment_counter("evaluations_completed", 5)
        system.performance_tracker.set_gauge("active_evaluations", 3)
        
        timer_id = system.performance_tracker.start_timer("evaluation_duration")
        time.sleep(0.01)
        system.performance_tracker.stop_timer(timer_id)
        
        # Get performance summary
        summary = system.get_performance_summary()
        
        assert summary['performance_metrics']['counters']['evaluations_completed'] == 5
        assert summary['performance_metrics']['gauges']['active_evaluations'] == 3
        assert len(system.performance_tracker.metrics['evaluation_duration']) == 1
    
    def test_custom_health_check_integration(self):
        """Test custom health check integration."""
        system = MonitoringSystem()
        
        # Add custom health check
        def custom_check():
            return False  # Always fail
        
        custom_health_check = HealthCheck(
            name="custom_service",
            check_function=custom_check,
            description="Custom service health",
            critical=True
        )
        
        system.health_checker.register_health_check(custom_health_check)
        
        # Get system status
        status = system.get_system_status()
        
        # Should have critical status due to failing custom check
        assert status.status == HealthStatus.CRITICAL
        
        # Check that custom health check result is included
        custom_result = next(
            (hc for hc in status.health_checks if hc.name == "custom_service"), 
            None
        )
        assert custom_result is not None
        assert custom_result.status == HealthStatus.CRITICAL


if __name__ == "__main__":
    pytest.main([__file__])