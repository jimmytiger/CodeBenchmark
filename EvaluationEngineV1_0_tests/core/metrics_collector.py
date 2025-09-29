"""
Metrics collection and performance monitoring for the testing framework.
"""

import time
import psutil
import logging
import threading
from typing import Dict, List, Optional, Any, Callable
from datetime import datetime, timedelta
from dataclasses import dataclass, field
from collections import defaultdict, deque

from models.test_models import ExecutionMetrics, TestResult


@dataclass
class MetricSnapshot:
    """A single metric measurement at a point in time."""
    timestamp: datetime
    metric_name: str
    value: float
    tags: Dict[str, str] = field(default_factory=dict)


class MetricsCollector:
    """Collects and aggregates performance metrics during test execution."""
    
    def __init__(self, collection_interval: float = 1.0):
        self.collection_interval = collection_interval
        self.logger = logging.getLogger(f"{__name__}.MetricsCollector")
        
        # Metric storage
        self._metrics: Dict[str, deque] = defaultdict(lambda: deque(maxlen=1000))
        self._counters: Dict[str, float] = defaultdict(float)
        self._timers: Dict[str, float] = {}
        self._gauges: Dict[str, float] = {}
        
        # Collection state
        self._collecting = False
        self._collection_thread: Optional[threading.Thread] = None
        self._start_time: Optional[datetime] = None
        
        # System monitoring
        self._process = psutil.Process()
        self._initial_memory = self._process.memory_info().rss
        self._peak_memory = self._initial_memory
    
    def start_collection(self) -> None:
        """Start metrics collection."""
        if self._collecting:
            self.logger.warning("Metrics collection already started")
            return
        
        self._collecting = True
        self._start_time = datetime.now()
        self._collection_thread = threading.Thread(target=self._collect_system_metrics)
        self._collection_thread.daemon = True
        self._collection_thread.start()
        
        self.logger.info("Started metrics collection")
    
    def stop_collection(self) -> None:
        """Stop metrics collection."""
        if not self._collecting:
            return
        
        self._collecting = False
        if self._collection_thread:
            self._collection_thread.join(timeout=5.0)
        
        self.logger.info("Stopped metrics collection")
    
    def record_metric(self, name: str, value: float, 
                     tags: Optional[Dict[str, str]] = None) -> None:
        """Record a metric value."""
        snapshot = MetricSnapshot(
            timestamp=datetime.now(),
            metric_name=name,
            value=value,
            tags=tags or {}
        )
        self._metrics[name].append(snapshot)
    
    def increment_counter(self, name: str, value: float = 1.0) -> None:
        """Increment a counter metric."""
        self._counters[name] += value
        self.record_metric(f"{name}_total", self._counters[name])
    
    def set_gauge(self, name: str, value: float) -> None:
        """Set a gauge metric value."""
        self._gauges[name] = value
        self.record_metric(name, value)
    
    def start_timer(self, name: str) -> None:
        """Start a timer for measuring duration."""
        self._timers[name] = time.time()
    
    def stop_timer(self, name: str) -> float:
        """Stop a timer and record the duration."""
        if name not in self._timers:
            self.logger.warning(f"Timer '{name}' was not started")
            return 0.0
        
        duration = time.time() - self._timers[name]
        del self._timers[name]
        self.record_metric(f"{name}_duration", duration)
        return duration
    
    def time_operation(self, name: str):
        """Context manager for timing operations."""
        return TimerContext(self, name)
    
    def record_test_result(self, test_result: TestResult) -> None:
        """Record metrics from a test result."""
        # Basic test metrics
        self.increment_counter(f"tests_{test_result.status.value}")
        self.record_metric("test_execution_time", test_result.execution_time,
                          tags={"test_id": test_result.test_id, "test_type": test_result.test_type.value})
        
        # Real execution validation
        if test_result.real_execution_validated:
            self.increment_counter("real_execution_validated")
        else:
            self.increment_counter("real_execution_failed")
        
        # Custom metrics from test result
        for metric_name, value in test_result.metrics.items():
            self.record_metric(f"test_{metric_name}", value,
                             tags={"test_id": test_result.test_id})
    
    def record_api_call(self, endpoint: str, method: str, 
                       response_time: float, status_code: int) -> None:
        """Record API call metrics."""
        tags = {
            "endpoint": endpoint,
            "method": method,
            "status_code": str(status_code)
        }
        
        self.record_metric("api_response_time", response_time, tags=tags)
        self.increment_counter(f"api_calls_{status_code}")
        
        if 200 <= status_code < 300:
            self.increment_counter("api_calls_success")
        else:
            self.increment_counter("api_calls_error")
    
    def record_adapter_metrics(self, adapter_name: str, 
                              operation: str, metrics: Dict[str, float]) -> None:
        """Record adapter-specific metrics."""
        tags = {"adapter": adapter_name, "operation": operation}
        
        for metric_name, value in metrics.items():
            self.record_metric(f"adapter_{metric_name}", value, tags=tags)
    
    def get_execution_metrics(self) -> ExecutionMetrics:
        """Get aggregated execution metrics."""
        total_time = 0.0
        if self._start_time:
            total_time = (datetime.now() - self._start_time).total_seconds()
        
        return ExecutionMetrics(
            total_execution_time=total_time,
            task_execution_times=self._get_task_execution_times(),
            memory_usage=self._get_memory_metrics(),
            api_response_times=self._get_api_response_times(),
            error_rates=self._get_error_rates(),
            success_rates=self._get_success_rates(),
            resource_consumption=self._get_resource_metrics(),
            network_usage=self._get_network_metrics()
        )
    
    def get_metric_summary(self, metric_name: str) -> Dict[str, float]:
        """Get summary statistics for a metric."""
        if metric_name not in self._metrics:
            return {}
        
        values = [snapshot.value for snapshot in self._metrics[metric_name]]
        if not values:
            return {}
        
        return {
            "count": len(values),
            "min": min(values),
            "max": max(values),
            "mean": sum(values) / len(values),
            "latest": values[-1] if values else 0.0
        }
    
    def get_all_metrics(self) -> Dict[str, List[MetricSnapshot]]:
        """Get all collected metrics."""
        return {name: list(snapshots) for name, snapshots in self._metrics.items()}
    
    def clear_metrics(self) -> None:
        """Clear all collected metrics."""
        self._metrics.clear()
        self._counters.clear()
        self._timers.clear()
        self._gauges.clear()
        self.logger.info("Cleared all metrics")
    
    def _collect_system_metrics(self) -> None:
        """Background thread for collecting system metrics."""
        while self._collecting:
            try:
                # CPU usage
                cpu_percent = psutil.cpu_percent(interval=None)
                self.set_gauge("system_cpu_percent", cpu_percent)
                
                # Memory usage
                memory_info = self._process.memory_info()
                current_memory = memory_info.rss
                self.set_gauge("process_memory_rss", current_memory)
                self.set_gauge("process_memory_vms", memory_info.vms)
                
                # Track peak memory
                if current_memory > self._peak_memory:
                    self._peak_memory = current_memory
                    self.set_gauge("process_memory_peak", self._peak_memory)
                
                # Memory percentage
                memory_percent = self._process.memory_percent()
                self.set_gauge("process_memory_percent", memory_percent)
                
                # Thread count
                thread_count = self._process.num_threads()
                self.set_gauge("process_threads", thread_count)
                
                # File descriptors (Unix only)
                try:
                    fd_count = self._process.num_fds()
                    self.set_gauge("process_file_descriptors", fd_count)
                except (AttributeError, psutil.AccessDenied):
                    pass  # Not available on Windows or access denied
                
                # System-wide metrics
                system_memory = psutil.virtual_memory()
                self.set_gauge("system_memory_percent", system_memory.percent)
                self.set_gauge("system_memory_available", system_memory.available)
                
            except Exception as e:
                self.logger.warning(f"Error collecting system metrics: {e}")
            
            time.sleep(self.collection_interval)
    
    def _get_task_execution_times(self) -> Dict[str, float]:
        """Get task execution times from metrics."""
        task_times = {}
        
        for metric_name, snapshots in self._metrics.items():
            if metric_name.endswith("_duration") and "test" in metric_name:
                if snapshots:
                    task_times[metric_name] = snapshots[-1].value
        
        return task_times
    
    def _get_memory_metrics(self) -> Dict[str, float]:
        """Get memory usage metrics."""
        memory_metrics = {}
        
        # Current memory usage
        if "process_memory_rss" in self._metrics:
            snapshots = self._metrics["process_memory_rss"]
            if snapshots:
                memory_metrics["current_rss"] = snapshots[-1].value
        
        # Peak memory usage
        if "process_memory_peak" in self._metrics:
            snapshots = self._metrics["process_memory_peak"]
            if snapshots:
                memory_metrics["peak_rss"] = snapshots[-1].value
        
        # Memory growth
        memory_metrics["memory_growth"] = self._peak_memory - self._initial_memory
        
        return memory_metrics
    
    def _get_api_response_times(self) -> Dict[str, float]:
        """Get API response time metrics."""
        api_metrics = {}
        
        if "api_response_time" in self._metrics:
            snapshots = self._metrics["api_response_time"]
            if snapshots:
                times = [s.value for s in snapshots]
                api_metrics["avg_response_time"] = sum(times) / len(times)
                api_metrics["max_response_time"] = max(times)
                api_metrics["min_response_time"] = min(times)
        
        return api_metrics
    
    def _get_error_rates(self) -> Dict[str, float]:
        """Get error rate metrics."""
        error_rates = {}
        
        # Test error rates
        total_tests = sum(self._counters.get(f"tests_{status}", 0) 
                         for status in ["passed", "failed", "error", "skipped"])
        
        if total_tests > 0:
            failed_tests = self._counters.get("tests_failed", 0)
            error_tests = self._counters.get("tests_error", 0)
            error_rates["test_failure_rate"] = (failed_tests + error_tests) / total_tests
        
        # API error rates
        total_api_calls = sum(self._counters.get(f"api_calls_{code}", 0) 
                             for code in range(200, 600))
        
        if total_api_calls > 0:
            api_errors = self._counters.get("api_calls_error", 0)
            error_rates["api_error_rate"] = api_errors / total_api_calls
        
        return error_rates
    
    def _get_success_rates(self) -> Dict[str, float]:
        """Get success rate metrics."""
        success_rates = {}
        
        # Test success rates
        total_tests = sum(self._counters.get(f"tests_{status}", 0) 
                         for status in ["passed", "failed", "error", "skipped"])
        
        if total_tests > 0:
            passed_tests = self._counters.get("tests_passed", 0)
            success_rates["test_success_rate"] = passed_tests / total_tests
        
        # Real execution validation rate
        total_validated = (self._counters.get("real_execution_validated", 0) + 
                          self._counters.get("real_execution_failed", 0))
        
        if total_validated > 0:
            validated = self._counters.get("real_execution_validated", 0)
            success_rates["real_execution_rate"] = validated / total_validated
        
        return success_rates
    
    def _get_resource_metrics(self) -> Dict[str, float]:
        """Get resource consumption metrics."""
        resource_metrics = {}
        
        # CPU metrics
        if "system_cpu_percent" in self._metrics:
            snapshots = self._metrics["system_cpu_percent"]
            if snapshots:
                cpu_values = [s.value for s in snapshots]
                resource_metrics["avg_cpu_percent"] = sum(cpu_values) / len(cpu_values)
                resource_metrics["max_cpu_percent"] = max(cpu_values)
        
        # Thread metrics
        if "process_threads" in self._metrics:
            snapshots = self._metrics["process_threads"]
            if snapshots:
                resource_metrics["max_threads"] = max(s.value for s in snapshots)
        
        return resource_metrics
    
    def _get_network_metrics(self) -> Dict[str, float]:
        """Get network usage metrics (placeholder for future implementation)."""
        # This could be extended to track actual network usage
        # For now, we'll use API call counts as a proxy
        network_metrics = {}
        
        total_api_calls = sum(self._counters.get(f"api_calls_{code}", 0) 
                             for code in range(200, 600))
        network_metrics["total_api_calls"] = total_api_calls
        
        return network_metrics


class TimerContext:
    """Context manager for timing operations."""
    
    def __init__(self, metrics_collector: MetricsCollector, timer_name: str):
        self.metrics_collector = metrics_collector
        self.timer_name = timer_name
    
    def __enter__(self):
        self.metrics_collector.start_timer(self.timer_name)
        return self
    
    def __exit__(self, exc_type, exc_val, exc_tb):
        self.metrics_collector.stop_timer(self.timer_name)


def create_metrics_collector(collection_interval: float = 1.0) -> MetricsCollector:
    """Factory function to create a metrics collector."""
    return MetricsCollector(collection_interval=collection_interval)