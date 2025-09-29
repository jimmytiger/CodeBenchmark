"""
Resource Limiter

Provides resource monitoring and limiting capabilities to prevent
resource exhaustion and ensure fair resource allocation during testing.
"""

import os
import sys
import time
import psutil
import threading
import logging
from typing import Dict, Optional, Callable, Any
from dataclasses import dataclass
from contextlib import contextmanager

logger = logging.getLogger(__name__)


@dataclass
class ResourceLimits:
    """Resource limit configuration."""
    max_memory_mb: Optional[int] = None
    max_cpu_percent: Optional[float] = None
    max_disk_mb: Optional[int] = None
    max_network_mb: Optional[int] = None
    max_execution_time: Optional[int] = None
    max_open_files: Optional[int] = None
    max_processes: Optional[int] = None


@dataclass
class ResourceUsage:
    """Current resource usage metrics."""
    memory_mb: float
    cpu_percent: float
    disk_mb: float
    network_mb: float
    execution_time: float
    open_files: int
    processes: int
    timestamp: float


class ResourceLimitExceeded(Exception):
    """Raised when resource limits are exceeded."""
    pass


class ResourceLimiter:
    """
    Monitors and enforces resource limits during test execution.
    
    Features:
    - Memory usage monitoring and limiting
    - CPU usage monitoring and limiting
    - Disk usage monitoring and limiting
    - Network usage monitoring and limiting
    - Process count limiting
    - File descriptor limiting
    - Execution time limiting
    """
    
    def __init__(self, 
                 limits: ResourceLimits,
                 monitoring_interval: float = 1.0,
                 grace_period: float = 5.0):
        """
        Initialize resource limiter.
        
        Args:
            limits: Resource limits configuration
            monitoring_interval: How often to check resource usage (seconds)
            grace_period: Grace period before enforcing limits (seconds)
        """
        self.limits = limits
        self.monitoring_interval = monitoring_interval
        self.grace_period = grace_period
        
        # Monitoring state
        self._monitoring = False
        self._monitor_thread: Optional[threading.Thread] = None
        self._start_time: Optional[float] = None
        self._initial_usage: Optional[ResourceUsage] = None
        self._current_usage: Optional[ResourceUsage] = None
        self._violation_callbacks: Dict[str, Callable] = {}
        
        # Process tracking
        self._tracked_processes: Dict[int, psutil.Process] = {}
        self._lock = threading.Lock()
    
    def add_violation_callback(self, resource_type: str, callback: Callable[[str, ResourceUsage], None]):
        """Add callback for resource limit violations."""
        self._violation_callbacks[resource_type] = callback
    
    @contextmanager
    def monitor_resources(self, process_ids: Optional[list] = None):
        """
        Context manager for resource monitoring.
        
        Args:
            process_ids: Specific process IDs to monitor (None for current process)
        """
        try:
            self.start_monitoring(process_ids)
            yield self
        finally:
            self.stop_monitoring()
    
    def start_monitoring(self, process_ids: Optional[list] = None):
        """Start resource monitoring."""
        if self._monitoring:
            logger.warning("Resource monitoring already active")
            return
        
        self._monitoring = True
        self._start_time = time.time()
        
        # Track processes
        if process_ids:
            for pid in process_ids:
                try:
                    process = psutil.Process(pid)
                    self._tracked_processes[pid] = process
                except psutil.NoSuchProcess:
                    logger.warning(f"Process {pid} not found")
        else:
            # Track current process
            current_process = psutil.Process()
            self._tracked_processes[current_process.pid] = current_process
        
        # Get initial usage
        self._initial_usage = self._get_current_usage()
        
        # Start monitoring thread
        self._monitor_thread = threading.Thread(target=self._monitor_loop, daemon=True)
        self._monitor_thread.start()
        
        logger.info("Started resource monitoring")
    
    def stop_monitoring(self):
        """Stop resource monitoring."""
        if not self._monitoring:
            return
        
        self._monitoring = False
        
        if self._monitor_thread and self._monitor_thread.is_alive():
            self._monitor_thread.join(timeout=2.0)
        
        # Clear tracked processes
        with self._lock:
            self._tracked_processes.clear()
        
        logger.info("Stopped resource monitoring")
    
    def _monitor_loop(self):
        """Main monitoring loop."""
        while self._monitoring:
            try:
                # Get current usage
                current_usage = self._get_current_usage()
                self._current_usage = current_usage
                
                # Check limits (after grace period)
                if time.time() - self._start_time > self.grace_period:
                    self._check_limits(current_usage)
                
                time.sleep(self.monitoring_interval)
                
            except Exception as e:
                logger.error(f"Error in resource monitoring loop: {e}")
                time.sleep(self.monitoring_interval)
    
    def _get_current_usage(self) -> ResourceUsage:
        """Get current resource usage."""
        try:
            with self._lock:
                processes = list(self._tracked_processes.values())
            
            # Aggregate usage across all tracked processes
            total_memory = 0.0
            total_cpu = 0.0
            total_open_files = 0
            
            for process in processes:
                try:
                    # Memory usage
                    memory_info = process.memory_info()
                    total_memory += memory_info.rss / (1024 * 1024)  # Convert to MB
                    
                    # CPU usage
                    total_cpu += process.cpu_percent()
                    
                    # Open files
                    try:
                        total_open_files += len(process.open_files())
                    except (psutil.AccessDenied, psutil.NoSuchProcess):
                        pass
                        
                except (psutil.NoSuchProcess, psutil.AccessDenied):
                    # Process may have terminated
                    continue
            
            # System-wide metrics
            disk_usage = self._get_disk_usage()
            network_usage = self._get_network_usage()
            execution_time = time.time() - self._start_time if self._start_time else 0.0
            
            return ResourceUsage(
                memory_mb=total_memory,
                cpu_percent=total_cpu,
                disk_mb=disk_usage,
                network_mb=network_usage,
                execution_time=execution_time,
                open_files=total_open_files,
                processes=len(processes),
                timestamp=time.time()
            )
            
        except Exception as e:
            logger.error(f"Failed to get resource usage: {e}")
            return ResourceUsage(0, 0, 0, 0, 0, 0, 0, time.time())
    
    def _get_disk_usage(self) -> float:
        """Get disk usage in MB."""
        try:
            # Get disk usage for current working directory
            disk_usage = psutil.disk_usage('.')
            return disk_usage.used / (1024 * 1024)
        except Exception:
            return 0.0
    
    def _get_network_usage(self) -> float:
        """Get network usage in MB."""
        try:
            # Get network I/O statistics
            net_io = psutil.net_io_counters()
            if net_io:
                return (net_io.bytes_sent + net_io.bytes_recv) / (1024 * 1024)
            return 0.0
        except Exception:
            return 0.0
    
    def _check_limits(self, usage: ResourceUsage):
        """Check if resource limits are exceeded."""
        violations = []
        
        # Check memory limit
        if self.limits.max_memory_mb and usage.memory_mb > self.limits.max_memory_mb:
            violations.append(f"Memory limit exceeded: {usage.memory_mb:.1f}MB > {self.limits.max_memory_mb}MB")
            self._trigger_violation_callback('memory', usage)
        
        # Check CPU limit
        if self.limits.max_cpu_percent and usage.cpu_percent > self.limits.max_cpu_percent:
            violations.append(f"CPU limit exceeded: {usage.cpu_percent:.1f}% > {self.limits.max_cpu_percent}%")
            self._trigger_violation_callback('cpu', usage)
        
        # Check disk limit
        if self.limits.max_disk_mb and usage.disk_mb > self.limits.max_disk_mb:
            violations.append(f"Disk limit exceeded: {usage.disk_mb:.1f}MB > {self.limits.max_disk_mb}MB")
            self._trigger_violation_callback('disk', usage)
        
        # Check network limit
        if self.limits.max_network_mb and usage.network_mb > self.limits.max_network_mb:
            violations.append(f"Network limit exceeded: {usage.network_mb:.1f}MB > {self.limits.max_network_mb}MB")
            self._trigger_violation_callback('network', usage)
        
        # Check execution time limit
        if self.limits.max_execution_time and usage.execution_time > self.limits.max_execution_time:
            violations.append(f"Execution time limit exceeded: {usage.execution_time:.1f}s > {self.limits.max_execution_time}s")
            self._trigger_violation_callback('time', usage)
        
        # Check open files limit
        if self.limits.max_open_files and usage.open_files > self.limits.max_open_files:
            violations.append(f"Open files limit exceeded: {usage.open_files} > {self.limits.max_open_files}")
            self._trigger_violation_callback('files', usage)
        
        # Check process count limit
        if self.limits.max_processes and usage.processes > self.limits.max_processes:
            violations.append(f"Process count limit exceeded: {usage.processes} > {self.limits.max_processes}")
            self._trigger_violation_callback('processes', usage)
        
        # Raise exception if any violations
        if violations:
            violation_msg = "; ".join(violations)
            logger.error(f"Resource limit violations: {violation_msg}")
            raise ResourceLimitExceeded(violation_msg)
    
    def _trigger_violation_callback(self, resource_type: str, usage: ResourceUsage):
        """Trigger violation callback if registered."""
        callback = self._violation_callbacks.get(resource_type)
        if callback:
            try:
                callback(resource_type, usage)
            except Exception as e:
                logger.error(f"Error in violation callback for {resource_type}: {e}")
    
    def get_current_usage(self) -> Optional[ResourceUsage]:
        """Get current resource usage."""
        return self._current_usage
    
    def get_usage_summary(self) -> Dict[str, Any]:
        """Get resource usage summary."""
        if not self._current_usage or not self._initial_usage:
            return {}
        
        current = self._current_usage
        initial = self._initial_usage
        
        return {
            'current_usage': {
                'memory_mb': current.memory_mb,
                'cpu_percent': current.cpu_percent,
                'disk_mb': current.disk_mb,
                'network_mb': current.network_mb,
                'execution_time': current.execution_time,
                'open_files': current.open_files,
                'processes': current.processes
            },
            'peak_usage': {
                'memory_mb': max(current.memory_mb, initial.memory_mb),
                'cpu_percent': max(current.cpu_percent, initial.cpu_percent),
                'disk_mb': max(current.disk_mb, initial.disk_mb),
                'network_mb': max(current.network_mb, initial.network_mb),
                'open_files': max(current.open_files, initial.open_files),
                'processes': max(current.processes, initial.processes)
            },
            'limits': {
                'memory_mb': self.limits.max_memory_mb,
                'cpu_percent': self.limits.max_cpu_percent,
                'disk_mb': self.limits.max_disk_mb,
                'network_mb': self.limits.max_network_mb,
                'execution_time': self.limits.max_execution_time,
                'open_files': self.limits.max_open_files,
                'processes': self.limits.max_processes
            },
            'utilization': {
                'memory_percent': (current.memory_mb / self.limits.max_memory_mb * 100) if self.limits.max_memory_mb else 0,
                'cpu_percent': (current.cpu_percent / self.limits.max_cpu_percent * 100) if self.limits.max_cpu_percent else 0,
                'disk_percent': (current.disk_mb / self.limits.max_disk_mb * 100) if self.limits.max_disk_mb else 0,
                'network_percent': (current.network_mb / self.limits.max_network_mb * 100) if self.limits.max_network_mb else 0,
                'time_percent': (current.execution_time / self.limits.max_execution_time * 100) if self.limits.max_execution_time else 0
            }
        }
    
    def is_monitoring(self) -> bool:
        """Check if monitoring is active."""
        return self._monitoring
    
    def add_process(self, pid: int):
        """Add a process to monitoring."""
        try:
            process = psutil.Process(pid)
            with self._lock:
                self._tracked_processes[pid] = process
            logger.info(f"Added process {pid} to monitoring")
        except psutil.NoSuchProcess:
            logger.warning(f"Process {pid} not found")
    
    def remove_process(self, pid: int):
        """Remove a process from monitoring."""
        with self._lock:
            if pid in self._tracked_processes:
                del self._tracked_processes[pid]
                logger.info(f"Removed process {pid} from monitoring")


class ResourceMonitoringContext:
    """Context manager for simplified resource monitoring."""
    
    def __init__(self, limits: ResourceLimits, **kwargs):
        self.limiter = ResourceLimiter(limits, **kwargs)
        self.usage_history: list = []
    
    def __enter__(self):
        self.limiter.start_monitoring()
        return self
    
    def __exit__(self, exc_type, exc_val, exc_tb):
        # Collect final usage
        final_usage = self.limiter.get_current_usage()
        if final_usage:
            self.usage_history.append(final_usage)
        
        self.limiter.stop_monitoring()
        
        # Log resource usage summary
        summary = self.limiter.get_usage_summary()
        if summary:
            logger.info(f"Resource usage summary: {summary}")
    
    def get_usage_summary(self) -> Dict[str, Any]:
        """Get resource usage summary."""
        return self.limiter.get_usage_summary()