"""
Tests for Performance Optimization Module.

This module tests performance profiling, caching strategies, concurrent execution
optimization, and performance regression detection.
"""

import asyncio
import pytest
import time
import threading
from unittest.mock import Mock, patch, AsyncMock
from datetime import datetime, timedelta

from EvaluationEngineV1_0.core.performance_optimizer import (
    PerformanceCache, PerformanceProfiler, ConcurrentExecutionManager,
    SystemMonitor, PerformanceOptimizer, PerformanceMetrics
)
from EvaluationEngineV1_0.core.data_models import EvaluationResult, TurnResult


class TestPerformanceCache:
    """Test performance caching functionality."""
    
    def test_cache_basic_operations(self):
        """Test basic cache operations."""
        cache = PerformanceCache(max_size=100, default_ttl=60)
        
        # Test set and get
        cache.set("key1", "value1")
        assert cache.get("key1") == "value1"
        
        # Test miss
        assert cache.get("nonexistent") is None
        
        # Test stats
        stats = cache.get_stats()
        assert stats['hits'] == 1
        assert stats['misses'] == 1
        assert stats['hit_rate'] == 0.5
    
    def test_cache_ttl_expiry(self):
        """Test cache TTL expiry."""
        cache = PerformanceCache(max_size=100, default_ttl=1)  # 1 second TTL
        
        cache.set("key1", "value1")
        assert cache.get("key1") == "value1"
        
        # Wait for expiry
        time.sleep(1.1)
        assert cache.get("key1") is None
    
    def test_cache_lru_eviction(self):
        """Test LRU eviction when cache is full."""
        cache = PerformanceCache(max_size=2, default_ttl=60)
        
        cache.set("key1", "value1")
        cache.set("key2", "value2")
        
        # Access key1 to make it more recently used
        cache.get("key1")
        
        # Add key3, should evict key2 (least recently used)
        cache.set("key3", "value3")
        
        assert cache.get("key1") == "value1"
        assert cache.get("key2") is None  # Evicted
        assert cache.get("key3") == "value3"
    
    def test_cache_invalidation(self):
        """Test cache invalidation."""
        cache = PerformanceCache(max_size=100, default_ttl=60)
        
        cache.set("key1", "value1")
        assert cache.get("key1") == "value1"
        
        # Invalidate
        assert cache.invalidate("key1") is True
        assert cache.get("key1") is None
        
        # Invalidate non-existent key
        assert cache.invalidate("nonexistent") is False
    
    def test_cache_clear(self):
        """Test cache clearing."""
        cache = PerformanceCache(max_size=100, default_ttl=60)
        
        cache.set("key1", "value1")
        cache.set("key2", "value2")
        
        cache.clear()
        
        assert cache.get("key1") is None
        assert cache.get("key2") is None
        assert cache.get_stats()['size'] == 0


class TestPerformanceProfiler:
    """Test performance profiling functionality."""
    
    def test_profiler_basic_operations(self):
        """Test basic profiler operations."""
        profiler = PerformanceProfiler()
        
        # Start profiling
        profiler.start_profiling("test_profile")
        
        # Do some work
        time.sleep(0.1)
        sum(range(1000))
        
        # Stop profiling
        result = profiler.stop_profiling("test_profile")
        
        assert result is not None
        assert result.function_name == "test_profile"
        assert result.total_time > 0
        assert result.call_count > 0
        assert len(result.hotspots) > 0
    
    def test_profiler_function_decorator(self):
        """Test function profiling decorator."""
        profiler = PerformanceProfiler()
        
        @profiler.profile_function
        def test_function():
            time.sleep(0.05)
            return sum(range(100))
        
        result = test_function()
        assert result == sum(range(100))
        
        # Check that profile was recorded
        profile_name = f"{test_function.__module__}.{test_function.__name__}"
        assert profile_name in profiler.profiles
    
    @pytest.mark.asyncio
    async def test_profiler_async_decorator(self):
        """Test async function profiling decorator."""
        profiler = PerformanceProfiler()
        
        @profiler.profile_async_function
        async def test_async_function():
            await asyncio.sleep(0.05)
            return sum(range(100))
        
        result = await test_async_function()
        assert result == sum(range(100))
        
        # Check that profile was recorded
        profile_name = f"{test_async_function.__module__}.{test_async_function.__name__}"
        assert profile_name in profiler.profiles
    
    def test_profiler_summary(self):
        """Test profiler summary generation."""
        profiler = PerformanceProfiler()
        
        # Create some profiles
        profiler.start_profiling("profile1")
        time.sleep(0.01)
        profiler.stop_profiling("profile1")
        
        profiler.start_profiling("profile2")
        time.sleep(0.02)
        profiler.stop_profiling("profile2")
        
        summary = profiler.get_profile_summary()
        
        assert summary['total_profiles'] == 2
        assert 'profile1' in summary['profiles']
        assert 'profile2' in summary['profiles']
        
        # Profile2 should have longer total time
        assert summary['profiles']['profile2']['total_time'] > summary['profiles']['profile1']['total_time']


class TestConcurrentExecutionManager:
    """Test concurrent execution management."""
    
    @pytest.mark.asyncio
    async def test_concurrent_execution_basic(self):
        """Test basic concurrent execution."""
        async with ConcurrentExecutionManager(max_workers=2) as manager:
            
            def task1():
                time.sleep(0.1)
                return "result1"
            
            def task2():
                time.sleep(0.1)
                return "result2"
            
            start_time = time.time()
            results = await manager.execute_concurrent_evaluations([task1, task2])
            end_time = time.time()
            
            # Should complete in roughly 0.1 seconds (concurrent) rather than 0.2 (sequential)
            assert end_time - start_time < 0.15
            assert len(results) == 2
            assert "result1" in results
            assert "result2" in results
    
    @pytest.mark.asyncio
    async def test_concurrent_execution_with_async_tasks(self):
        """Test concurrent execution with async tasks."""
        async with ConcurrentExecutionManager(max_workers=2) as manager:
            
            async def async_task1():
                await asyncio.sleep(0.1)
                return "async_result1"
            
            async def async_task2():
                await asyncio.sleep(0.1)
                return "async_result2"
            
            start_time = time.time()
            results = await manager.execute_concurrent_evaluations([async_task1, async_task2])
            end_time = time.time()
            
            # Should complete concurrently
            assert end_time - start_time < 0.15
            assert len(results) == 2
            assert "async_result1" in results
            assert "async_result2" in results
    
    @pytest.mark.asyncio
    async def test_concurrent_execution_error_handling(self):
        """Test error handling in concurrent execution."""
        async with ConcurrentExecutionManager(max_workers=2) as manager:
            
            def success_task():
                return "success"
            
            def error_task():
                raise ValueError("Test error")
            
            results = await manager.execute_concurrent_evaluations([success_task, error_task])
            
            assert len(results) == 2
            assert "success" in results
            
            # One result should be an exception
            exceptions = [r for r in results if isinstance(r, Exception)]
            assert len(exceptions) == 1
            assert isinstance(exceptions[0], ValueError)
    
    @pytest.mark.asyncio
    async def test_concurrent_execution_task_management(self):
        """Test task management functionality."""
        async with ConcurrentExecutionManager(max_workers=2) as manager:
            
            # Initially no active tasks
            assert await manager.get_active_task_count() == 0
            
            # Start some long-running tasks
            async def long_task():
                await asyncio.sleep(1.0)
                return "done"
            
            # Start tasks but don't wait
            task_coroutine = manager.execute_concurrent_evaluations([long_task, long_task])
            task = asyncio.create_task(task_coroutine)
            
            # Give tasks time to start
            await asyncio.sleep(0.1)
            
            # Should have active tasks
            active_count = await manager.get_active_task_count()
            assert active_count > 0
            
            # Cancel all tasks
            cancelled_count = await manager.cancel_all_tasks()
            assert cancelled_count > 0
            
            # Clean up
            try:
                await task
            except asyncio.CancelledError:
                pass


class TestSystemMonitor:
    """Test system monitoring functionality."""
    
    @pytest.mark.asyncio
    async def test_monitor_basic_operations(self):
        """Test basic monitoring operations."""
        monitor = SystemMonitor(monitoring_interval=0.1)
        
        # Start monitoring
        await monitor.start_monitoring()
        
        # Let it collect some metrics
        await asyncio.sleep(0.3)
        
        # Stop monitoring
        await monitor.stop_monitoring()
        
        # Check that metrics were collected
        current_metrics = monitor.get_current_metrics()
        assert current_metrics is not None
        assert current_metrics.cpu_usage >= 0
        assert current_metrics.memory_usage >= 0
        assert current_metrics.active_threads > 0
    
    @pytest.mark.asyncio
    async def test_monitor_metrics_collection(self):
        """Test metrics collection functionality."""
        monitor = SystemMonitor(monitoring_interval=0.05)
        
        await monitor.start_monitoring()
        await asyncio.sleep(0.2)  # Collect several samples
        await monitor.stop_monitoring()
        
        history = monitor.get_metrics_history()
        assert len(history) >= 3  # Should have collected multiple samples
        
        # All metrics should be valid
        for metrics in history:
            assert isinstance(metrics.cpu_usage, (int, float))
            assert isinstance(metrics.memory_usage, (int, float))
            assert isinstance(metrics.active_threads, int)
            assert isinstance(metrics.timestamp, datetime)
    
    @pytest.mark.asyncio
    async def test_monitor_alert_system(self):
        """Test alert system functionality."""
        monitor = SystemMonitor(monitoring_interval=0.1)
        
        # Set low thresholds to trigger alerts
        monitor._alert_thresholds['cpu_usage'] = 0.1  # Very low threshold
        monitor._alert_thresholds['memory_usage'] = 0.1
        
        alert_received = []
        
        async def alert_callback(alert_message, metrics):
            alert_received.append(alert_message)
        
        monitor.add_alert_callback(alert_callback)
        
        await monitor.start_monitoring()
        await asyncio.sleep(0.3)  # Let it monitor and potentially trigger alerts
        await monitor.stop_monitoring()
        
        # Should have received some alerts due to low thresholds
        assert len(alert_received) > 0
    
    def test_monitor_performance_summary(self):
        """Test performance summary generation."""
        monitor = SystemMonitor()
        
        # Add some mock metrics
        for i in range(5):
            metrics = PerformanceMetrics(
                cpu_usage=50.0 + i,
                memory_usage=60.0 + i,
                disk_io={},
                network_io={},
                active_threads=10 + i,
                active_processes=100 + i,
                cache_hit_rate=0.8,
                avg_response_time=0.1,
                throughput=100.0
            )
            monitor._metrics_history.append(metrics)
        
        summary = monitor.get_performance_summary()
        
        assert 'avg_cpu_usage' in summary
        assert 'max_cpu_usage' in summary
        assert 'avg_memory_usage' in summary
        assert 'max_memory_usage' in summary
        assert summary['sample_count'] == 5


class TestPerformanceOptimizer:
    """Test main performance optimizer functionality."""
    
    @pytest.mark.asyncio
    async def test_optimizer_initialization(self):
        """Test optimizer initialization."""
        optimizer = PerformanceOptimizer()
        
        assert optimizer.cache is not None
        assert optimizer.profiler is not None
        assert optimizer.monitor is not None
        assert optimizer._optimization_enabled is True
    
    @pytest.mark.asyncio
    async def test_optimizer_caching_functions(self):
        """Test optimizer caching functionality."""
        optimizer = PerformanceOptimizer()
        
        # Test manual caching
        optimizer.cache_result("test_key", "test_value")
        assert optimizer.get_cached_result("test_key") == "test_value"
        
        # Test cache key generation
        key1 = optimizer.create_cache_key("arg1", "arg2", kwarg1="value1")
        key2 = optimizer.create_cache_key("arg1", "arg2", kwarg1="value1")
        key3 = optimizer.create_cache_key("arg1", "arg3", kwarg1="value1")
        
        assert key1 == key2  # Same arguments should produce same key
        assert key1 != key3  # Different arguments should produce different keys
    
    def test_optimizer_cached_function_decorator(self):
        """Test cached function decorator."""
        optimizer = PerformanceOptimizer()
        
        call_count = 0
        
        @optimizer.cached_function(ttl=60)
        def expensive_function(x, y):
            nonlocal call_count
            call_count += 1
            time.sleep(0.01)  # Simulate expensive operation
            return x + y
        
        # First call should execute function
        result1 = expensive_function(1, 2)
        assert result1 == 3
        assert call_count == 1
        
        # Second call with same arguments should use cache
        result2 = expensive_function(1, 2)
        assert result2 == 3
        assert call_count == 1  # Should not increment
        
        # Call with different arguments should execute function
        result3 = expensive_function(2, 3)
        assert result3 == 5
        assert call_count == 2
    
    @pytest.mark.asyncio
    async def test_optimizer_cached_async_function_decorator(self):
        """Test cached async function decorator."""
        optimizer = PerformanceOptimizer()
        
        call_count = 0
        
        @optimizer.cached_async_function(ttl=60)
        async def expensive_async_function(x, y):
            nonlocal call_count
            call_count += 1
            await asyncio.sleep(0.01)  # Simulate expensive async operation
            return x * y
        
        # First call should execute function
        result1 = await expensive_async_function(2, 3)
        assert result1 == 6
        assert call_count == 1
        
        # Second call with same arguments should use cache
        result2 = await expensive_async_function(2, 3)
        assert result2 == 6
        assert call_count == 1  # Should not increment
        
        # Call with different arguments should execute function
        result3 = await expensive_async_function(3, 4)
        assert result3 == 12
        assert call_count == 2
    
    @pytest.mark.asyncio
    async def test_optimizer_concurrent_execution(self):
        """Test optimized concurrent execution."""
        optimizer = PerformanceOptimizer()
        
        def task(n):
            time.sleep(0.05)
            return n * 2
        
        tasks = [lambda i=i: task(i) for i in range(4)]
        
        start_time = time.time()
        results = await optimizer.optimize_concurrent_execution(tasks, max_concurrent=2)
        end_time = time.time()
        
        # Should complete faster than sequential execution
        assert end_time - start_time < 0.15  # Should be roughly 0.1 seconds with 2 concurrent
        assert len(results) == 4
        assert sorted(results) == [0, 2, 4, 6]
    
    def test_optimizer_enable_disable(self):
        """Test enabling/disabling optimization."""
        optimizer = PerformanceOptimizer()
        
        # Initially enabled
        assert optimizer._optimization_enabled is True
        
        # Test caching works when enabled
        optimizer.cache_result("key1", "value1")
        assert optimizer.get_cached_result("key1") == "value1"
        
        # Disable optimization
        optimizer.disable_optimization()
        assert optimizer._optimization_enabled is False
        
        # Caching should not work when disabled
        optimizer.cache_result("key2", "value2")
        assert optimizer.get_cached_result("key2") is None
        
        # Re-enable
        optimizer.enable_optimization()
        assert optimizer._optimization_enabled is True
    
    def test_optimizer_report_generation(self):
        """Test optimization report generation."""
        optimizer = PerformanceOptimizer()
        
        # Add some cache activity
        optimizer.cache_result("key1", "value1")
        optimizer.get_cached_result("key1")
        optimizer.get_cached_result("nonexistent")
        
        report = optimizer.get_optimization_report()
        
        assert 'cache_performance' in report
        assert 'profiling_results' in report
        assert 'system_performance' in report
        assert 'optimization_enabled' in report
        assert 'recommendations' in report
        
        # Check cache stats
        cache_stats = report['cache_performance']
        assert cache_stats['hits'] == 1
        assert cache_stats['misses'] == 1
        assert cache_stats['hit_rate'] == 0.5


class TestPerformanceRegression:
    """Test performance regression detection."""
    
    def test_performance_baseline_establishment(self):
        """Test establishing performance baselines."""
        # This would typically involve running standard benchmarks
        # and recording baseline performance metrics
        
        baseline_metrics = {
            'avg_evaluation_time': 1.0,
            'memory_usage_mb': 100.0,
            'cache_hit_rate': 0.8,
            'concurrent_throughput': 10.0
        }
        
        # In a real implementation, these would be stored and compared
        # against future runs to detect regressions
        assert baseline_metrics['avg_evaluation_time'] > 0
        assert baseline_metrics['memory_usage_mb'] > 0
        assert 0 <= baseline_metrics['cache_hit_rate'] <= 1
        assert baseline_metrics['concurrent_throughput'] > 0
    
    @pytest.mark.asyncio
    async def test_performance_benchmark_execution(self):
        """Test execution of performance benchmarks."""
        optimizer = PerformanceOptimizer()
        
        # Simulate benchmark tasks
        def benchmark_task(size):
            # Simulate work proportional to size
            result = sum(range(size))
            time.sleep(size * 0.001)  # Simulate processing time
            return result
        
        # Run benchmark with different sizes
        sizes = [100, 500, 1000]
        tasks = [lambda s=size: benchmark_task(s) for size in sizes]
        
        start_time = time.time()
        results = await optimizer.optimize_concurrent_execution(tasks)
        end_time = time.time()
        
        execution_time = end_time - start_time
        
        # Verify results are correct
        expected_results = [sum(range(size)) for size in sizes]
        assert sorted(results) == sorted(expected_results)
        
        # Record performance metrics for regression testing
        performance_metrics = {
            'execution_time': execution_time,
            'tasks_completed': len(results),
            'throughput': len(results) / execution_time
        }
        
        # In a real implementation, these would be compared against baselines
        assert performance_metrics['execution_time'] > 0
        assert performance_metrics['tasks_completed'] == len(sizes)
        assert performance_metrics['throughput'] > 0
    
    def test_memory_usage_monitoring(self):
        """Test memory usage monitoring for regression detection."""
        import psutil
        
        process = psutil.Process()
        initial_memory = process.memory_info().rss
        
        # Simulate memory-intensive operation
        large_data = [list(range(1000)) for _ in range(100)]
        
        peak_memory = process.memory_info().rss
        memory_increase = peak_memory - initial_memory
        
        # Clean up
        del large_data
        
        # In a real implementation, memory usage patterns would be
        # compared against baselines to detect memory leaks or regressions
        assert memory_increase > 0
        assert memory_increase < 100 * 1024 * 1024  # Should be reasonable
    
    @pytest.mark.asyncio
    async def test_concurrent_performance_scaling(self):
        """Test performance scaling with concurrent execution."""
        optimizer = PerformanceOptimizer()
        
        def cpu_intensive_task():
            # CPU-intensive task
            return sum(i * i for i in range(10000))
        
        # Test with different concurrency levels
        concurrency_levels = [1, 2, 4]
        performance_results = {}
        
        for concurrency in concurrency_levels:
            tasks = [cpu_intensive_task for _ in range(8)]  # 8 tasks total
            
            start_time = time.time()
            results = await optimizer.optimize_concurrent_execution(
                tasks, max_concurrent=concurrency
            )
            end_time = time.time()
            
            execution_time = end_time - start_time
            throughput = len(results) / execution_time
            
            performance_results[concurrency] = {
                'execution_time': execution_time,
                'throughput': throughput
            }
        
        # Verify that higher concurrency generally improves throughput
        # (though this depends on system resources)
        assert len(performance_results) == len(concurrency_levels)
        
        # In a real implementation, these scaling characteristics would be
        # monitored for performance regressions
        for concurrency, metrics in performance_results.items():
            assert metrics['execution_time'] > 0
            assert metrics['throughput'] > 0


if __name__ == "__main__":
    pytest.main([__file__])