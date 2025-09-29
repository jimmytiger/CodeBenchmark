"""
Performance Testing and Benchmarking Suite

This module provides performance tests, load testing, and benchmarking
for the multi-turn evaluation engine.

Requirements: 10.1, 10.2, 10.3, 10.4, 10.5
"""

import pytest
import time
import asyncio
import threading
import concurrent.futures
import psutil
import gc
import sys
from typing import List, Dict, Any
from dataclasses import dataclass
from unittest.mock import Mock

from ..core.data_models import (
    EvaluationConfig, TaskConfig, ModelConfig, MultiTurnConfig,
    EvaluationResult, AggregatedMetrics
)
from ..core.compatibility import ConfigurationAdapter, LegacyEvaluationBridge


@dataclass
class PerformanceMetrics:
    """Performance metrics for benchmarking."""
    execution_time: float
    memory_usage_mb: float
    cpu_usage_percent: float
    operations_per_second: float
    peak_memory_mb: float
    thread_count: int


class PerformanceMonitor:
    """Monitor system performance during tests."""
    
    def __init__(self):
        self.start_time = None
        self.start_memory = None
        self.start_cpu = None
        self.peak_memory = 0
        self.measurements = []
    
    def start(self):
        """Start performance monitoring."""
        self.start_time = time.time()
        self.start_memory = psutil.Process().memory_info().rss / 1024 / 1024  # MB
        self.start_cpu = psutil.cpu_percent()
        self.peak_memory = self.start_memory
        self.measurements = []
    
    def measure(self):
        """Take a performance measurement."""
        current_memory = psutil.Process().memory_info().rss / 1024 / 1024
        self.peak_memory = max(self.peak_memory, current_memory)
        
        measurement = {
            'time': time.time() - self.start_time,
            'memory_mb': current_memory,
            'cpu_percent': psutil.cpu_percent(),
            'thread_count': threading.active_count()
        }
        self.measurements.append(measurement)
        return measurement
    
    def stop(self) -> PerformanceMetrics:
        """Stop monitoring and return metrics."""
        end_time = time.time()
        end_memory = psutil.Process().memory_info().rss / 1024 / 1024
        end_cpu = psutil.cpu_percent()
        
        execution_time = end_time - self.start_time
        memory_usage = end_memory - self.start_memory
        
        return PerformanceMetrics(
            execution_time=execution_time,
            memory_usage_mb=memory_usage,
            cpu_usage_percent=end_cpu,
            operations_per_second=len(self.measurements) / execution_time if execution_time > 0 else 0,
            peak_memory_mb=self.peak_memory,
            thread_count=threading.active_count()
        )


@pytest.mark.performance
class TestConfigurationPerformance:
    """Test performance of configuration operations."""
    
    def test_configuration_creation_performance(self):
        """Test performance of creating configurations."""
        monitor = PerformanceMonitor()
        monitor.start()
        
        # Create many configurations
        configs = []
        for i in range(1000):
            model_config = ModelConfig(
                model_id=f"model_{i}",
                model_type="mock",
                parameters={"param": i}
            )
            
            task_config = TaskConfig(
                task_id=f"task_{i}",
                task_type="single_turn",
                model_ref=f"model_{i}"
            )
            
            config = EvaluationConfig(
                models={f"model_{i}": model_config},
                tasks=[task_config]
            )
            configs.append(config)
            
            if i % 100 == 0:
                monitor.measure()
        
        metrics = monitor.stop()
        
        # Performance assertions
        assert metrics.execution_time < 5.0, f"Configuration creation took {metrics.execution_time:.3f}s"
        assert metrics.memory_usage_mb < 100, f"Memory usage: {metrics.memory_usage_mb:.1f}MB"
        assert len(configs) == 1000
    
    def test_configuration_validation_performance(self):
        """Test performance of configuration validation."""
        # Create large configuration
        models = {}
        tasks = []
        
        for i in range(100):
            model_id = f"model_{i}"
            models[model_id] = ModelConfig(
                model_id=model_id,
                model_type="mock"
            )
            
            for j in range(10):
                tasks.append(TaskConfig(
                    task_id=f"task_{i}_{j}",
                    task_type="single_turn",
                    model_ref=model_id
                ))
        
        config = EvaluationConfig(models=models, tasks=tasks)
        
        monitor = PerformanceMonitor()
        monitor.start()
        
        # Validate multiple times
        for _ in range(100):
            config.validate()
            monitor.measure()
        
        metrics = monitor.stop()
        
        # Validation should be fast
        assert metrics.execution_time < 2.0, f"Validation took {metrics.execution_time:.3f}s"
        assert metrics.operations_per_second > 50, f"Only {metrics.operations_per_second:.1f} validations/sec"
    
    def test_configuration_serialization_performance(self):
        """Test performance of configuration serialization."""
        import json
        
        # Create configuration
        config = EvaluationConfig(
            models={f"model_{i}": ModelConfig(
                model_id=f"model_{i}",
                model_type="mock",
                parameters={f"param_{j}": f"value_{j}" for j in range(10)}
            ) for i in range(50)},
            tasks=[TaskConfig(
                task_id=f"task_{i}",
                task_type="single_turn",
                model_ref=f"model_{i % 50}"
            ) for i in range(500)]
        )
        
        monitor = PerformanceMonitor()
        monitor.start()
        
        # Serialize multiple times
        serialized_configs = []
        for _ in range(100):
            # Convert to dict for serialization
            config_dict = {
                "models": {k: {
                    "model_id": v.model_id,
                    "model_type": v.model_type,
                    "parameters": v.parameters
                } for k, v in config.models.items()},
                "tasks": [{
                    "task_id": t.task_id,
                    "task_type": t.task_type,
                    "model_ref": t.model_ref
                } for t in config.tasks]
            }
            
            json_str = json.dumps(config_dict)
            serialized_configs.append(json_str)
            monitor.measure()
        
        metrics = monitor.stop()
        
        # Serialization should be efficient
        assert metrics.execution_time < 3.0, f"Serialization took {metrics.execution_time:.3f}s"
        assert len(serialized_configs) == 100


@pytest.mark.performance
class TestCompatibilityPerformance:
    """Test performance of backward compatibility layer."""
    
    def test_configuration_adaptation_performance(self):
        """Test performance of configuration adaptation."""
        adapter = ConfigurationAdapter()
        
        # Create legacy configurations
        legacy_configs = []
        for i in range(1000):
            legacy_config = {
                'model': f'model_{i}',
                'tasks': f'task_{i}_1,task_{i}_2,task_{i}_3',
                'model_args': {'param': i},
                'num_fewshot': i % 10,
                'batch_size': (i % 8) + 1
            }
            legacy_configs.append(legacy_config)
        
        monitor = PerformanceMonitor()
        monitor.start()
        
        # Adapt configurations
        adapted_configs = []
        for config in legacy_configs:
            adapted = adapter.adapt_legacy_config(config)
            adapted_configs.append(adapted)
            
            if len(adapted_configs) % 100 == 0:
                monitor.measure()
        
        metrics = monitor.stop()
        
        # Adaptation should be fast
        assert metrics.execution_time < 5.0, f"Adaptation took {metrics.execution_time:.3f}s"
        assert len(adapted_configs) == 1000
        assert metrics.operations_per_second > 200, f"Only {metrics.operations_per_second:.1f} adaptations/sec"
    
    def test_legacy_bridge_performance(self):
        """Test performance of legacy evaluation bridge."""
        bridge = LegacyEvaluationBridge()
        
        monitor = PerformanceMonitor()
        monitor.start()
        
        # Perform multiple evaluations
        results = []
        for i in range(100):
            result = bridge.evaluate(
                model=f'model_{i}',
                tasks=f'task_{i}',
                model_args={'param': i}
            )
            results.append(result)
            
            if i % 10 == 0:
                monitor.measure()
        
        metrics = monitor.stop()
        
        # Bridge operations should be efficient
        assert metrics.execution_time < 10.0, f"Bridge operations took {metrics.execution_time:.3f}s"
        assert len(results) == 100
    
    def test_result_conversion_performance(self):
        """Test performance of result format conversion."""
        bridge = LegacyEvaluationBridge()
        
        # Create mock evaluation results
        results = []
        for i in range(1000):
            metrics = AggregatedMetrics(
                resolved_percentage=0.8 + (i % 20) / 100,
                recall=0.75 + (i % 25) / 100,
                mrr=0.7 + (i % 30) / 100,
                avg_turns=1 + (i % 5),
                avg_steps=5 + (i % 10),
                redundancy_rate=(i % 10) / 100,
                edit_churn=i % 5,
                files_touched=i % 3,
                recovery_rate=0.9 + (i % 10) / 100,
                stability_score=0.85 + (i % 15) / 100,
                wall_time_per_solved=10 + (i % 50),
                tokens_per_solved=100 + (i % 500),
                cost_per_solved=0.01 + (i % 10) / 1000,
                safety_incidents=i % 2,
                policy_violations=i % 3
            )
            
            result = EvaluationResult(
                evaluation_id=f"eval_{i}",
                task_id=f"task_{i}",
                model_id=f"model_{i}",
                success=(i % 3) == 0,
                total_turns=1 + (i % 5),
                turn_results=[],
                aggregated_metrics=metrics,
                metadata={}
            )
            results.append(result)
        
        monitor = PerformanceMonitor()
        monitor.start()
        
        # Convert results to legacy format
        legacy_results = bridge._convert_results_to_legacy_format(results)
        
        metrics = monitor.stop()
        
        # Conversion should be fast
        assert metrics.execution_time < 2.0, f"Result conversion took {metrics.execution_time:.3f}s"
        assert 'results' in legacy_results
        assert len(legacy_results['results']) == 1000


@pytest.mark.performance
class TestConcurrencyPerformance:
    """Test performance under concurrent load."""
    
    def test_concurrent_configuration_creation(self):
        """Test concurrent configuration creation."""
        def create_config(task_id: int) -> EvaluationConfig:
            model_config = ModelConfig(
                model_id=f"model_{task_id}",
                model_type="mock"
            )
            
            task_config = TaskConfig(
                task_id=f"task_{task_id}",
                task_type="single_turn",
                model_ref=f"model_{task_id}"
            )
            
            config = EvaluationConfig(
                models={f"model_{task_id}": model_config},
                tasks=[task_config]
            )
            
            config.validate()
            return config
        
        monitor = PerformanceMonitor()
        monitor.start()
        
        # Create configurations concurrently
        with concurrent.futures.ThreadPoolExecutor(max_workers=10) as executor:
            futures = [executor.submit(create_config, i) for i in range(100)]
            configs = [future.result() for future in concurrent.futures.as_completed(futures)]
        
        metrics = monitor.stop()
        
        # Concurrent creation should be efficient
        assert metrics.execution_time < 5.0, f"Concurrent creation took {metrics.execution_time:.3f}s"
        assert len(configs) == 100
        assert metrics.peak_memory_mb < 200, f"Peak memory: {metrics.peak_memory_mb:.1f}MB"
    
    def test_concurrent_adaptation(self):
        """Test concurrent configuration adaptation."""
        adapter = ConfigurationAdapter()
        
        def adapt_config(config_id: int) -> EvaluationConfig:
            legacy_config = {
                'model': f'model_{config_id}',
                'tasks': f'task_{config_id}',
                'model_args': {'param': config_id},
                'num_fewshot': config_id % 10
            }
            return adapter.adapt_legacy_config(legacy_config)
        
        monitor = PerformanceMonitor()
        monitor.start()
        
        # Adapt configurations concurrently
        with concurrent.futures.ThreadPoolExecutor(max_workers=8) as executor:
            futures = [executor.submit(adapt_config, i) for i in range(200)]
            adapted_configs = [future.result() for future in concurrent.futures.as_completed(futures)]
        
        metrics = monitor.stop()
        
        # Concurrent adaptation should be efficient
        assert metrics.execution_time < 3.0, f"Concurrent adaptation took {metrics.execution_time:.3f}s"
        assert len(adapted_configs) == 200
    
    def test_thread_safety(self):
        """Test thread safety of core components."""
        adapter = ConfigurationAdapter()
        bridge = LegacyEvaluationBridge()
        
        results = []
        errors = []
        
        def worker(worker_id: int):
            try:
                for i in range(50):
                    # Test adapter thread safety
                    legacy_config = {
                        'model': f'model_{worker_id}_{i}',
                        'tasks': f'task_{worker_id}_{i}',
                        'model_args': {'worker': worker_id, 'iteration': i}
                    }
                    
                    adapted = adapter.adapt_legacy_config(legacy_config)
                    adapted.validate()
                    
                    # Test bridge thread safety
                    result = bridge.evaluate(
                        model=f'model_{worker_id}',
                        tasks=f'task_{worker_id}_{i}'
                    )
                    
                    results.append((worker_id, i, adapted, result))
                    
            except Exception as e:
                errors.append((worker_id, str(e)))
        
        monitor = PerformanceMonitor()
        monitor.start()
        
        # Run multiple workers concurrently
        threads = []
        for worker_id in range(5):
            thread = threading.Thread(target=worker, args=(worker_id,))
            threads.append(thread)
            thread.start()
        
        # Wait for all threads to complete
        for thread in threads:
            thread.join()
        
        metrics = monitor.stop()
        
        # Should complete without errors
        assert len(errors) == 0, f"Thread safety errors: {errors}"
        assert len(results) == 250  # 5 workers * 50 iterations
        assert metrics.execution_time < 10.0, f"Thread safety test took {metrics.execution_time:.3f}s"


@pytest.mark.performance
class TestMemoryPerformance:
    """Test memory usage and garbage collection."""
    
    def test_memory_leak_detection(self):
        """Test for memory leaks in repeated operations."""
        import gc
        
        # Force garbage collection
        gc.collect()
        initial_objects = len(gc.get_objects())
        initial_memory = psutil.Process().memory_info().rss / 1024 / 1024
        
        # Perform many operations
        for i in range(1000):
            model_config = ModelConfig(
                model_id=f"temp_model_{i}",
                model_type="mock",
                parameters={"temp_param": i}
            )
            
            task_config = TaskConfig(
                task_id=f"temp_task_{i}",
                task_type="single_turn",
                model_ref=f"temp_model_{i}"
            )
            
            config = EvaluationConfig(
                models={f"temp_model_{i}": model_config},
                tasks=[task_config]
            )
            
            config.validate()
            
            # Clear references
            del model_config, task_config, config
            
            # Periodic garbage collection
            if i % 100 == 0:
                gc.collect()
        
        # Final garbage collection
        gc.collect()
        final_objects = len(gc.get_objects())
        final_memory = psutil.Process().memory_info().rss / 1024 / 1024
        
        # Check for memory leaks
        object_growth = final_objects - initial_objects
        memory_growth = final_memory - initial_memory
        
        assert object_growth < 1000, f"Object count grew by {object_growth}"
        assert memory_growth < 50, f"Memory usage grew by {memory_growth:.1f}MB"
    
    def test_large_configuration_memory_usage(self):
        """Test memory usage with large configurations."""
        monitor = PerformanceMonitor()
        monitor.start()
        
        # Create progressively larger configurations
        for size in [10, 50, 100, 500]:
            models = {f"model_{i}": ModelConfig(
                model_id=f"model_{i}",
                model_type="mock",
                parameters={f"param_{j}": f"value_{j}" for j in range(10)}
            ) for i in range(size)}
            
            tasks = [TaskConfig(
                task_id=f"task_{i}",
                task_type="single_turn",
                model_ref=f"model_{i % size}",
                parameters={f"task_param_{j}": j for j in range(5)}
            ) for i in range(size * 10)]
            
            config = EvaluationConfig(models=models, tasks=tasks)
            config.validate()
            
            monitor.measure()
            
            # Clear references
            del models, tasks, config
            gc.collect()
        
        metrics = monitor.stop()
        
        # Memory usage should be reasonable
        assert metrics.peak_memory_mb < 500, f"Peak memory usage: {metrics.peak_memory_mb:.1f}MB"
    
    def test_garbage_collection_efficiency(self):
        """Test garbage collection efficiency."""
        import gc
        
        # Disable automatic garbage collection
        gc.disable()
        
        try:
            initial_memory = psutil.Process().memory_info().rss / 1024 / 1024
            
            # Create many objects
            objects = []
            for i in range(10000):
                config = EvaluationConfig(
                    models={f"model_{i}": ModelConfig(
                        model_id=f"model_{i}",
                        model_type="mock"
                    )},
                    tasks=[TaskConfig(
                        task_id=f"task_{i}",
                        task_type="single_turn",
                        model_ref=f"model_{i}"
                    )]
                )
                objects.append(config)
            
            peak_memory = psutil.Process().memory_info().rss / 1024 / 1024
            
            # Clear references
            objects.clear()
            
            # Manual garbage collection
            start_time = time.time()
            collected = gc.collect()
            gc_time = time.time() - start_time
            
            final_memory = psutil.Process().memory_info().rss / 1024 / 1024
            
            # Garbage collection should be efficient
            assert gc_time < 1.0, f"Garbage collection took {gc_time:.3f}s"
            assert collected > 0, "No objects were collected"
            
            memory_freed = peak_memory - final_memory
            assert memory_freed > 0, f"No memory was freed (freed: {memory_freed:.1f}MB)"
            
        finally:
            # Re-enable automatic garbage collection
            gc.enable()


@pytest.mark.performance
class TestScalabilityPerformance:
    """Test scalability with increasing load."""
    
    def test_linear_scaling_performance(self):
        """Test that performance scales linearly with load."""
        adapter = ConfigurationAdapter()
        
        # Test different load sizes
        load_sizes = [10, 50, 100, 500]
        execution_times = []
        
        for size in load_sizes:
            monitor = PerformanceMonitor()
            monitor.start()
            
            # Create configurations
            for i in range(size):
                legacy_config = {
                    'model': f'model_{i}',
                    'tasks': f'task_{i}',
                    'model_args': {'param': i}
                }
                
                adapted = adapter.adapt_legacy_config(legacy_config)
                adapted.validate()
            
            metrics = monitor.stop()
            execution_times.append(metrics.execution_time)
        
        # Check that scaling is reasonable (not exponential)
        for i in range(1, len(execution_times)):
            ratio = execution_times[i] / execution_times[i-1]
            size_ratio = load_sizes[i] / load_sizes[i-1]
            
            # Execution time should scale roughly linearly
            assert ratio <= size_ratio * 2, f"Performance degraded significantly at size {load_sizes[i]}"
    
    def test_memory_scaling(self):
        """Test memory usage scaling."""
        # Test different configuration sizes
        sizes = [10, 50, 100, 200]
        memory_usage = []
        
        for size in sizes:
            gc.collect()
            initial_memory = psutil.Process().memory_info().rss / 1024 / 1024
            
            # Create configuration
            models = {f"model_{i}": ModelConfig(
                model_id=f"model_{i}",
                model_type="mock"
            ) for i in range(size)}
            
            tasks = [TaskConfig(
                task_id=f"task_{i}",
                task_type="single_turn",
                model_ref=f"model_{i % size}"
            ) for i in range(size * 5)]
            
            config = EvaluationConfig(models=models, tasks=tasks)
            config.validate()
            
            peak_memory = psutil.Process().memory_info().rss / 1024 / 1024
            memory_used = peak_memory - initial_memory
            memory_usage.append(memory_used)
            
            # Clean up
            del models, tasks, config
            gc.collect()
        
        # Memory usage should scale reasonably
        for i in range(1, len(memory_usage)):
            ratio = memory_usage[i] / memory_usage[i-1] if memory_usage[i-1] > 0 else 1
            size_ratio = sizes[i] / sizes[i-1]
            
            # Memory should not grow exponentially
            assert ratio <= size_ratio * 2, f"Memory usage grew too much at size {sizes[i]}"


if __name__ == '__main__':
    # Run performance tests
    pytest.main([
        __file__,
        "-v",
        "--tb=short",
        "-m", "performance"
    ])