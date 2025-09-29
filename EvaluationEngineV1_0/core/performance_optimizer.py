"""
Performance Optimization Module for Multi-Turn Evaluation Engine.

This module implements performance profiling, caching strategies, and concurrent
execution optimization to improve system performance and scalability.
"""

import asyncio
import cProfile
import functools
import hashlib
import logging
import pickle
import pstats
import time
import threading
from collections import defaultdict, deque
from concurrent.futures import ThreadPoolExecutor, ProcessPoolExecutor
from dataclasses import dataclass, field
from datetime import datetime, timedelta
from typing import Any, Dict, List, Optional, Callable, Union, Tuple
from weakref import WeakValueDictionary
import psutil
import json

from .data_models import EvaluationResult, TurnResult, AggregatedMetrics
from .exceptions import PerformanceError, ResourceExhaustionError

logger = logging.getLogger(__name__)


@dataclass
class PerformanceMetrics:
    """Performance metrics for system monitoring."""
    cpu_usage: float
    memory_usage: float
    disk_io: Dict[str, float]
    network_io: Dict[str, float]
    active_threads: int
    active_processes: int
    cache_hit_rate: float
    avg_response_time: float
    throughput: float
    timestamp: datetime = field(default_factory=datetime.now)


@dataclass
class ProfileResult:
    """Result of performance profiling."""
    function_name: str
    total_time: float
    call_count: int
    avg_time_per_call: float
    cumulative_time: float
    hotspots: List[Dict[str, Any]]
    memory_usage: float


class PerformanceCache:
    """High-performance caching system with TTL and LRU eviction."""
    
    def __init__(self, max_size: int = 10000, default_ttl: int = 3600):
        """Initialize the cache.
        
        Args:
            max_size: Maximum number of items to cache
            default_ttl: Default time-to-live in seconds
        """
        self.max_size = max_size
        self.default_ttl = default_ttl
        self._cache: Dict[str, Dict[str, Any]] = {}
        self._access_times: Dict[str, float] = {}
        self._expiry_times: Dict[str, float] = {}
        self._lock = threading.RLock()
        self._hits = 0
        self._misses = 0
        
        # Start cleanup thread
        self._cleanup_thread = threading.Thread(target=self._cleanup_expired, daemon=True)
        self._cleanup_thread.start()
    
    def get(self, key: str) -> Optional[Any]:
        """Get item from cache."""
        with self._lock:
            current_time = time.time()
            
            if key not in self._cache:
                self._misses += 1
                return None
            
            # Check expiry
            if current_time > self._expiry_times.get(key, 0):
                self._remove_key(key)
                self._misses += 1
                return None
            
            # Update access time
            self._access_times[key] = current_time
            self._hits += 1
            return self._cache[key]['value']
    
    def set(self, key: str, value: Any, ttl: Optional[int] = None) -> None:
        """Set item in cache."""
        with self._lock:
            current_time = time.time()
            ttl = ttl or self.default_ttl
            
            # Evict if at capacity
            if len(self._cache) >= self.max_size and key not in self._cache:
                self._evict_lru()
            
            self._cache[key] = {'value': value, 'size': self._estimate_size(value)}
            self._access_times[key] = current_time
            self._expiry_times[key] = current_time + ttl
    
    def invalidate(self, key: str) -> bool:
        """Remove item from cache."""
        with self._lock:
            if key in self._cache:
                self._remove_key(key)
                return True
            return False
    
    def clear(self) -> None:
        """Clear all cache entries."""
        with self._lock:
            self._cache.clear()
            self._access_times.clear()
            self._expiry_times.clear()
    
    def get_stats(self) -> Dict[str, Any]:
        """Get cache statistics."""
        with self._lock:
            total_requests = self._hits + self._misses
            hit_rate = self._hits / total_requests if total_requests > 0 else 0.0
            
            return {
                'size': len(self._cache),
                'max_size': self.max_size,
                'hits': self._hits,
                'misses': self._misses,
                'hit_rate': hit_rate,
                'memory_usage': sum(item['size'] for item in self._cache.values())
            }
    
    def _remove_key(self, key: str) -> None:
        """Remove key from all data structures."""
        self._cache.pop(key, None)
        self._access_times.pop(key, None)
        self._expiry_times.pop(key, None)
    
    def _evict_lru(self) -> None:
        """Evict least recently used item."""
        if not self._access_times:
            return
        
        lru_key = min(self._access_times.keys(), key=lambda k: self._access_times[k])
        self._remove_key(lru_key)
    
    def _cleanup_expired(self) -> None:
        """Background thread to clean up expired entries."""
        while True:
            try:
                current_time = time.time()
                expired_keys = []
                
                with self._lock:
                    for key, expiry_time in self._expiry_times.items():
                        if current_time > expiry_time:
                            expired_keys.append(key)
                
                for key in expired_keys:
                    with self._lock:
                        self._remove_key(key)
                
                time.sleep(60)  # Cleanup every minute
            except Exception as e:
                logger.error(f"Cache cleanup error: {e}")
                time.sleep(60)
    
    @staticmethod
    def _estimate_size(obj: Any) -> int:
        """Estimate object size in bytes."""
        try:
            return len(pickle.dumps(obj))
        except Exception:
            return 1024  # Default estimate


class PerformanceProfiler:
    """Performance profiler for identifying bottlenecks."""
    
    def __init__(self):
        """Initialize the profiler."""
        self.profiles: Dict[str, ProfileResult] = {}
        self._active_profiles: Dict[str, cProfile.Profile] = {}
        self._lock = threading.Lock()
    
    def start_profiling(self, name: str) -> None:
        """Start profiling a section."""
        with self._lock:
            if name in self._active_profiles:
                logger.warning(f"Profile {name} already active")
                return
            
            profile = cProfile.Profile()
            profile.enable()
            self._active_profiles[name] = profile
    
    def stop_profiling(self, name: str) -> Optional[ProfileResult]:
        """Stop profiling and return results."""
        with self._lock:
            if name not in self._active_profiles:
                logger.warning(f"Profile {name} not found")
                return None
            
            profile = self._active_profiles.pop(name)
            profile.disable()
            
            # Analyze results
            stats = pstats.Stats(profile)
            stats.sort_stats('cumulative')
            
            # Extract key metrics
            total_time = stats.total_tt
            call_count = stats.total_calls
            avg_time = total_time / call_count if call_count > 0 else 0.0
            
            # Get hotspots
            hotspots = []
            for func, (cc, nc, tt, ct, callers) in stats.stats.items():
                hotspots.append({
                    'function': f"{func[0]}:{func[1]}({func[2]})",
                    'calls': cc,
                    'total_time': tt,
                    'cumulative_time': ct,
                    'avg_time': tt / cc if cc > 0 else 0.0
                })
            
            # Sort by cumulative time
            hotspots.sort(key=lambda x: x['cumulative_time'], reverse=True)
            
            result = ProfileResult(
                function_name=name,
                total_time=total_time,
                call_count=call_count,
                avg_time_per_call=avg_time,
                cumulative_time=sum(h['cumulative_time'] for h in hotspots[:10]),
                hotspots=hotspots[:20],  # Top 20 hotspots
                memory_usage=self._get_memory_usage()
            )
            
            self.profiles[name] = result
            return result
    
    def profile_function(self, func: Callable) -> Callable:
        """Decorator to profile a function."""
        @functools.wraps(func)
        def wrapper(*args, **kwargs):
            name = f"{func.__module__}.{func.__name__}"
            self.start_profiling(name)
            try:
                result = func(*args, **kwargs)
                return result
            finally:
                self.stop_profiling(name)
        return wrapper
    
    def profile_async_function(self, func: Callable) -> Callable:
        """Decorator to profile an async function."""
        @functools.wraps(func)
        async def wrapper(*args, **kwargs):
            name = f"{func.__module__}.{func.__name__}"
            self.start_profiling(name)
            try:
                result = await func(*args, **kwargs)
                return result
            finally:
                self.stop_profiling(name)
        return wrapper
    
    def get_profile_summary(self) -> Dict[str, Any]:
        """Get summary of all profiles."""
        return {
            'total_profiles': len(self.profiles),
            'profiles': {name: {
                'total_time': profile.total_time,
                'call_count': profile.call_count,
                'avg_time_per_call': profile.avg_time_per_call,
                'memory_usage': profile.memory_usage,
                'top_hotspots': profile.hotspots[:5]
            } for name, profile in self.profiles.items()}
        }
    
    @staticmethod
    def _get_memory_usage() -> float:
        """Get current memory usage in MB."""
        process = psutil.Process()
        return process.memory_info().rss / 1024 / 1024


class ConcurrentExecutionManager:
    """Manager for concurrent evaluation execution."""
    
    def __init__(self, max_workers: int = None, use_processes: bool = False):
        """Initialize the execution manager.
        
        Args:
            max_workers: Maximum number of concurrent workers
            use_processes: Whether to use processes instead of threads
        """
        self.max_workers = max_workers or min(32, (psutil.cpu_count() or 1) + 4)
        self.use_processes = use_processes
        self._executor = None
        self._active_tasks: Dict[str, asyncio.Task] = {}
        self._task_results: Dict[str, Any] = {}
        self._lock = asyncio.Lock()
    
    async def __aenter__(self):
        """Async context manager entry."""
        if self.use_processes:
            self._executor = ProcessPoolExecutor(max_workers=self.max_workers)
        else:
            self._executor = ThreadPoolExecutor(max_workers=self.max_workers)
        return self
    
    async def __aexit__(self, exc_type, exc_val, exc_tb):
        """Async context manager exit."""
        if self._executor:
            self._executor.shutdown(wait=True)
    
    async def execute_concurrent_evaluations(self, 
                                           evaluation_tasks: List[Callable],
                                           max_concurrent: int = None) -> List[Any]:
        """Execute multiple evaluations concurrently.
        
        Args:
            evaluation_tasks: List of evaluation functions to execute
            max_concurrent: Maximum concurrent executions
            
        Returns:
            List of evaluation results
        """
        max_concurrent = max_concurrent or self.max_workers
        semaphore = asyncio.Semaphore(max_concurrent)
        
        async def execute_with_semaphore(task_func, task_id):
            async with semaphore:
                try:
                    if asyncio.iscoroutinefunction(task_func):
                        result = await task_func()
                    else:
                        loop = asyncio.get_event_loop()
                        result = await loop.run_in_executor(self._executor, task_func)
                    
                    async with self._lock:
                        self._task_results[task_id] = result
                    
                    return result
                except Exception as e:
                    logger.error(f"Task {task_id} failed: {e}")
                    async with self._lock:
                        self._task_results[task_id] = e
                    raise
        
        # Create tasks
        tasks = []
        for i, task_func in enumerate(evaluation_tasks):
            task_id = f"eval_task_{i}_{int(time.time())}"
            task = asyncio.create_task(execute_with_semaphore(task_func, task_id))
            tasks.append(task)
            
            async with self._lock:
                self._active_tasks[task_id] = task
        
        # Wait for completion
        try:
            results = await asyncio.gather(*tasks, return_exceptions=True)
            return results
        finally:
            # Cleanup
            async with self._lock:
                self._active_tasks.clear()
    
    async def get_active_task_count(self) -> int:
        """Get number of active tasks."""
        async with self._lock:
            return len(self._active_tasks)
    
    async def cancel_all_tasks(self) -> int:
        """Cancel all active tasks."""
        cancelled_count = 0
        async with self._lock:
            for task in self._active_tasks.values():
                if not task.done():
                    task.cancel()
                    cancelled_count += 1
            self._active_tasks.clear()
        
        return cancelled_count


class SystemMonitor:
    """System resource monitor for performance tracking."""
    
    def __init__(self, monitoring_interval: float = 1.0):
        """Initialize the monitor.
        
        Args:
            monitoring_interval: Interval between monitoring samples in seconds
        """
        self.monitoring_interval = monitoring_interval
        self._metrics_history: deque = deque(maxlen=1000)
        self._monitoring = False
        self._monitor_task: Optional[asyncio.Task] = None
        self._alert_thresholds = {
            'cpu_usage': 80.0,
            'memory_usage': 85.0,
            'disk_usage': 90.0
        }
        self._alert_callbacks: List[Callable] = []
    
    async def start_monitoring(self) -> None:
        """Start system monitoring."""
        if self._monitoring:
            return
        
        self._monitoring = True
        self._monitor_task = asyncio.create_task(self._monitor_loop())
        logger.info("System monitoring started")
    
    async def stop_monitoring(self) -> None:
        """Stop system monitoring."""
        self._monitoring = False
        if self._monitor_task:
            self._monitor_task.cancel()
            try:
                await self._monitor_task
            except asyncio.CancelledError:
                pass
        logger.info("System monitoring stopped")
    
    async def _monitor_loop(self) -> None:
        """Main monitoring loop."""
        while self._monitoring:
            try:
                metrics = await self._collect_metrics()
                self._metrics_history.append(metrics)
                
                # Check for alerts
                await self._check_alerts(metrics)
                
                await asyncio.sleep(self.monitoring_interval)
            except asyncio.CancelledError:
                break
            except Exception as e:
                logger.error(f"Monitoring error: {e}")
                await asyncio.sleep(self.monitoring_interval)
    
    async def _collect_metrics(self) -> PerformanceMetrics:
        """Collect current system metrics."""
        # CPU usage
        cpu_usage = psutil.cpu_percent(interval=None)
        
        # Memory usage
        memory = psutil.virtual_memory()
        memory_usage = memory.percent
        
        # Disk I/O
        disk_io = psutil.disk_io_counters()
        disk_metrics = {
            'read_bytes': disk_io.read_bytes if disk_io else 0,
            'write_bytes': disk_io.write_bytes if disk_io else 0,
            'read_count': disk_io.read_count if disk_io else 0,
            'write_count': disk_io.write_count if disk_io else 0
        }
        
        # Network I/O
        network_io = psutil.net_io_counters()
        network_metrics = {
            'bytes_sent': network_io.bytes_sent if network_io else 0,
            'bytes_recv': network_io.bytes_recv if network_io else 0,
            'packets_sent': network_io.packets_sent if network_io else 0,
            'packets_recv': network_io.packets_recv if network_io else 0
        }
        
        # Process counts
        active_threads = threading.active_count()
        active_processes = len(psutil.pids())
        
        return PerformanceMetrics(
            cpu_usage=cpu_usage,
            memory_usage=memory_usage,
            disk_io=disk_metrics,
            network_io=network_metrics,
            active_threads=active_threads,
            active_processes=active_processes,
            cache_hit_rate=0.0,  # Will be updated by cache
            avg_response_time=0.0,  # Will be updated by profiler
            throughput=0.0  # Will be updated by orchestrator
        )
    
    async def _check_alerts(self, metrics: PerformanceMetrics) -> None:
        """Check for alert conditions."""
        alerts = []
        
        if metrics.cpu_usage > self._alert_thresholds['cpu_usage']:
            alerts.append(f"High CPU usage: {metrics.cpu_usage:.1f}%")
        
        if metrics.memory_usage > self._alert_thresholds['memory_usage']:
            alerts.append(f"High memory usage: {metrics.memory_usage:.1f}%")
        
        # Check disk usage
        for partition in psutil.disk_partitions():
            try:
                usage = psutil.disk_usage(partition.mountpoint)
                usage_percent = (usage.used / usage.total) * 100
                if usage_percent > self._alert_thresholds['disk_usage']:
                    alerts.append(f"High disk usage on {partition.mountpoint}: {usage_percent:.1f}%")
            except (PermissionError, FileNotFoundError):
                continue
        
        # Trigger alert callbacks
        for alert in alerts:
            for callback in self._alert_callbacks:
                try:
                    await callback(alert, metrics)
                except Exception as e:
                    logger.error(f"Alert callback failed: {e}")
    
    def add_alert_callback(self, callback: Callable) -> None:
        """Add alert callback function."""
        self._alert_callbacks.append(callback)
    
    def get_current_metrics(self) -> Optional[PerformanceMetrics]:
        """Get the most recent metrics."""
        return self._metrics_history[-1] if self._metrics_history else None
    
    def get_metrics_history(self, limit: int = 100) -> List[PerformanceMetrics]:
        """Get metrics history."""
        return list(self._metrics_history)[-limit:]
    
    def get_performance_summary(self) -> Dict[str, Any]:
        """Get performance summary statistics."""
        if not self._metrics_history:
            return {}
        
        recent_metrics = list(self._metrics_history)[-60:]  # Last 60 samples
        
        cpu_values = [m.cpu_usage for m in recent_metrics]
        memory_values = [m.memory_usage for m in recent_metrics]
        
        return {
            'avg_cpu_usage': sum(cpu_values) / len(cpu_values),
            'max_cpu_usage': max(cpu_values),
            'avg_memory_usage': sum(memory_values) / len(memory_values),
            'max_memory_usage': max(memory_values),
            'active_threads': recent_metrics[-1].active_threads,
            'sample_count': len(recent_metrics),
            'monitoring_duration': len(self._metrics_history) * self.monitoring_interval
        }


class PerformanceOptimizer:
    """Main performance optimization coordinator."""
    
    def __init__(self):
        """Initialize the performance optimizer."""
        self.cache = PerformanceCache()
        self.profiler = PerformanceProfiler()
        self.monitor = SystemMonitor()
        self.concurrent_manager = ConcurrentExecutionManager()
        self._optimization_enabled = True
        self._performance_history: List[Dict[str, Any]] = []
    
    async def start(self) -> None:
        """Start performance optimization systems."""
        await self.monitor.start_monitoring()
        logger.info("Performance optimizer started")
    
    async def stop(self) -> None:
        """Stop performance optimization systems."""
        await self.monitor.stop_monitoring()
        logger.info("Performance optimizer stopped")
    
    def cache_result(self, key: str, value: Any, ttl: int = 3600) -> None:
        """Cache a computation result."""
        if self._optimization_enabled:
            self.cache.set(key, value, ttl)
    
    def get_cached_result(self, key: str) -> Optional[Any]:
        """Get cached result."""
        if self._optimization_enabled:
            return self.cache.get(key)
        return None
    
    def create_cache_key(self, *args, **kwargs) -> str:
        """Create a cache key from arguments."""
        key_data = {
            'args': str(args),
            'kwargs': str(sorted(kwargs.items()))
        }
        key_string = json.dumps(key_data, sort_keys=True)
        return hashlib.md5(key_string.encode()).hexdigest()
    
    def cached_function(self, ttl: int = 3600):
        """Decorator to cache function results."""
        def decorator(func: Callable) -> Callable:
            @functools.wraps(func)
            def wrapper(*args, **kwargs):
                if not self._optimization_enabled:
                    return func(*args, **kwargs)
                
                cache_key = f"{func.__name__}_{self.create_cache_key(*args, **kwargs)}"
                
                # Try cache first
                cached_result = self.cache.get(cache_key)
                if cached_result is not None:
                    return cached_result
                
                # Compute and cache
                result = func(*args, **kwargs)
                self.cache.set(cache_key, result, ttl)
                return result
            
            return wrapper
        return decorator
    
    def cached_async_function(self, ttl: int = 3600):
        """Decorator to cache async function results."""
        def decorator(func: Callable) -> Callable:
            @functools.wraps(func)
            async def wrapper(*args, **kwargs):
                if not self._optimization_enabled:
                    return await func(*args, **kwargs)
                
                cache_key = f"{func.__name__}_{self.create_cache_key(*args, **kwargs)}"
                
                # Try cache first
                cached_result = self.cache.get(cache_key)
                if cached_result is not None:
                    return cached_result
                
                # Compute and cache
                result = await func(*args, **kwargs)
                self.cache.set(cache_key, result, ttl)
                return result
            
            return wrapper
        return decorator
    
    async def optimize_concurrent_execution(self, 
                                          tasks: List[Callable],
                                          max_concurrent: int = None) -> List[Any]:
        """Execute tasks with optimal concurrency."""
        async with ConcurrentExecutionManager(use_processes=False) as manager:
            return await manager.execute_concurrent_evaluations(tasks, max_concurrent)
    
    def get_optimization_report(self) -> Dict[str, Any]:
        """Get comprehensive optimization report."""
        cache_stats = self.cache.get_stats()
        profile_summary = self.profiler.get_profile_summary()
        performance_summary = self.monitor.get_performance_summary()
        
        return {
            'cache_performance': cache_stats,
            'profiling_results': profile_summary,
            'system_performance': performance_summary,
            'optimization_enabled': self._optimization_enabled,
            'recommendations': self._generate_recommendations(cache_stats, performance_summary)
        }
    
    def _generate_recommendations(self, 
                                cache_stats: Dict[str, Any], 
                                perf_stats: Dict[str, Any]) -> List[str]:
        """Generate performance optimization recommendations."""
        recommendations = []
        
        # Cache recommendations
        if cache_stats.get('hit_rate', 0) < 0.5:
            recommendations.append("Consider increasing cache TTL or size for better hit rates")
        
        # CPU recommendations
        avg_cpu = perf_stats.get('avg_cpu_usage', 0)
        if avg_cpu > 80:
            recommendations.append("High CPU usage detected - consider reducing concurrent evaluations")
        elif avg_cpu < 30:
            recommendations.append("Low CPU usage - consider increasing concurrent evaluations")
        
        # Memory recommendations
        avg_memory = perf_stats.get('avg_memory_usage', 0)
        if avg_memory > 85:
            recommendations.append("High memory usage - consider reducing cache size or batch sizes")
        
        return recommendations
    
    def enable_optimization(self) -> None:
        """Enable performance optimizations."""
        self._optimization_enabled = True
        logger.info("Performance optimization enabled")
    
    def disable_optimization(self) -> None:
        """Disable performance optimizations."""
        self._optimization_enabled = False
        logger.info("Performance optimization disabled")


# Global performance optimizer instance
performance_optimizer = PerformanceOptimizer()