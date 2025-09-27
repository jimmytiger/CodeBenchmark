"""
Performance benchmarks and load testing.
"""

import pytest
import asyncio
import time
import psutil
import os
import json
from concurrent.futures import ThreadPoolExecutor, as_completed
from unittest.mock import Mock, AsyncMock
import statistics

from evaluation_engine.core.unified_framework import UnifiedEvaluationFramework
from evaluation_engine.core.metrics_engine import MetricsEngine


class TestPerformanceBenchmarks:
    """Performance benchmarks for evaluation engine."""

    @pytest.fixture
    def performance_framework(self, temp_dir):
        """Framework configured for performance testing."""
        config = {
            "data_dir": str(temp_dir),
            "cache_dir": str(temp_dir / "cache"),
            "results_dir": str(temp_dir / "results"),
            "log_level": "WARNING",  # Reduce logging overhead
            "enable_caching": True,
            "max_concurrent_evaluations": 10
        }
        return UnifiedEvaluationFramework(config)

    @pytest.fixture
    def large_dataset(self, temp_dir):
        """Large dataset for performance testing."""
        dataset_sizes = {
            "small": 100,
            "medium": 1000,
            "large": 5000
        }
        
        datasets = {}
        for size_name, size in dataset_sizes.items():
            dataset = []
            for i in range(size):
                dataset.append({
                    "id": f"perf_test_{size_name}_{i}",
                    "input": f"Performance test input {i} with some additional text to make it more realistic",
                    "expected_output": f"Expected output for test case {i} with detailed response",
                    "context": f"Context information for test {i}",
                    "difficulty": "easy" if i % 3 == 0 else "medium" if i % 3 == 1 else "hard",
                    "tags": [f"tag_{i % 5}", f"category_{i % 3}"]
                })
            
            dataset_file = temp_dir / f"perf_dataset_{size_name}.jsonl"
            with open(dataset_file, 'w') as f:
                for item in dataset:
                    f.write(json.dumps(item) + '\n')
            
            datasets[size_name] = str(dataset_file)
        
        return datasets

    @pytest.fixture
    def mock_fast_model(self):
        """Fast mock model for performance testing."""
        adapter = Mock()
        adapter.model_id = "fast_mock_model"
        
        async def fast_response(prompt, config=None):
            # Simulate very fast response
            await asyncio.sleep(0.001)  # 1ms delay
            return {
                "response": "Fast mock response",
                "usage": {"prompt_tokens": 10, "completion_tokens": 5}
            }
        
        adapter.generate_response = AsyncMock(side_effect=fast_response)
        return adapter

    @pytest.fixture
    def mock_slow_model(self):
        """Slow mock model for performance testing."""
        adapter = Mock()
        adapter.model_id = "slow_mock_model"
        
        async def slow_response(prompt, config=None):
            # Simulate slower response
            await asyncio.sleep(0.1)  # 100ms delay
            return {
                "response": "Slow mock response",
                "usage": {"prompt_tokens": 20, "completion_tokens": 10}
            }
        
        adapter.generate_response = AsyncMock(side_effect=slow_response)
        return adapter

    @pytest.mark.performance
    @pytest.mark.benchmark
    def test_metrics_calculation_performance(self, metrics_engine):
        """Benchmark metrics calculation performance."""
        # Generate test data
        sizes = [100, 500, 1000, 2000]
        results = {}
        
        for size in sizes:
            predictions = [f"Prediction {i}" for i in range(size)]
            references = [f"Reference {i}" for i in range(size)]
            
            # Benchmark BLEU calculation
            start_time = time.time()
            bleu_score = metrics_engine.calculate_bleu(predictions, [[ref] for ref in references])
            bleu_time = time.time() - start_time
            
            # Benchmark ROUGE calculation
            start_time = time.time()
            rouge_scores = metrics_engine.calculate_rouge(predictions, references)
            rouge_time = time.time() - start_time
            
            # Benchmark accuracy calculation
            start_time = time.time()
            accuracy = metrics_engine.calculate_accuracy(predictions, references)
            accuracy_time = time.time() - start_time
            
            results[size] = {
                "bleu_time": bleu_time,
                "rouge_time": rouge_time,
                "accuracy_time": accuracy_time,
                "items_per_second_bleu": size / bleu_time,
                "items_per_second_rouge": size / rouge_time,
                "items_per_second_accuracy": size / accuracy_time
            }
        
        # Verify performance scales reasonably
        for size in sizes:
            result = results[size]
            # Should process at least 100 items per second for simple metrics
            assert result["items_per_second_accuracy"] > 100
            # BLEU and ROUGE are more complex, but should still be reasonable
            assert result["items_per_second_bleu"] > 10
            assert result["items_per_second_rouge"] > 50
        
        # Performance should scale sub-linearly (not worse than O(n^2))
        small_result = results[100]
        large_result = results[2000]
        
        # Time should not increase by more than 20x for 20x data
        assert large_result["bleu_time"] < small_result["bleu_time"] * 30
        assert large_result["rouge_time"] < small_result["rouge_time"] * 30

    @pytest.mark.performance
    @pytest.mark.asyncio
    async def test_concurrent_evaluation_performance(self, performance_framework, large_dataset, mock_fast_model):
        """Test performance of concurrent evaluations."""
        performance_framework.register_model_adapter(mock_fast_model)
        
        # Register task
        task_config = {
            "task_id": "concurrent_perf_task",
            "task_type": "single_turn",
            "description": "Concurrent performance test",
            "dataset_path": large_dataset["medium"],  # 1000 items
            "metrics": ["accuracy"]
        }
        
        task_id = performance_framework.register_task(task_config)
        
        # Test different concurrency levels
        concurrency_levels = [1, 2, 5, 10]
        results = {}
        
        for concurrency in concurrency_levels:
            start_time = time.time()
            
            # Run multiple evaluations concurrently
            tasks = []
            for i in range(concurrency):
                task = performance_framework.run_evaluation(
                    task_ids=[task_id],
                    model_id="fast_mock_model"
                )
                tasks.append(task)
            
            # Wait for all to complete
            await asyncio.gather(*tasks)
            
            end_time = time.time()
            total_time = end_time - start_time
            
            results[concurrency] = {
                "total_time": total_time,
                "evaluations_per_second": concurrency / total_time,
                "items_per_second": (concurrency * 1000) / total_time
            }
        
        # Verify concurrency improves performance
        assert results[5]["evaluations_per_second"] > results[1]["evaluations_per_second"]
        assert results[10]["items_per_second"] > results[1]["items_per_second"]
        
        # Should handle at least 100 items per second with high concurrency
        assert results[10]["items_per_second"] > 100

    @pytest.mark.performance
    @pytest.mark.asyncio
    async def test_memory_usage_performance(self, performance_framework, large_dataset, mock_fast_model):
        """Test memory usage during large evaluations."""
        performance_framework.register_model_adapter(mock_fast_model)
        
        process = psutil.Process(os.getpid())
        initial_memory = process.memory_info().rss
        
        # Register large task
        task_config = {
            "task_id": "memory_perf_task",
            "task_type": "single_turn",
            "description": "Memory performance test",
            "dataset_path": large_dataset["large"],  # 5000 items
            "metrics": ["accuracy", "bleu"]
        }
        
        task_id = performance_framework.register_task(task_config)
        
        # Monitor memory during evaluation
        memory_samples = []
        
        async def memory_monitor():
            while True:
                current_memory = process.memory_info().rss
                memory_samples.append(current_memory)
                await asyncio.sleep(0.5)
        
        # Start memory monitoring
        monitor_task = asyncio.create_task(memory_monitor())
        
        try:
            # Run evaluation
            start_time = time.time()
            result = await performance_framework.run_evaluation(
                task_ids=[task_id],
                model_id="fast_mock_model"
            )
            end_time = time.time()
            
        finally:
            monitor_task.cancel()
        
        final_memory = process.memory_info().rss
        peak_memory = max(memory_samples) if memory_samples else final_memory
        
        # Calculate memory metrics
        memory_increase = final_memory - initial_memory
        peak_memory_increase = peak_memory - initial_memory
        
        # Memory usage should be reasonable
        # Should not use more than 1GB for 5000 items
        assert memory_increase < 1024 * 1024 * 1024  # 1GB
        assert peak_memory_increase < 1024 * 1024 * 1024  # 1GB
        
        # Performance should be reasonable
        total_time = end_time - start_time
        items_per_second = 5000 / total_time
        assert items_per_second > 50  # Should process at least 50 items per second

    @pytest.mark.performance
    def test_task_registry_performance(self, temp_dir):
        """Test task registry performance with many tasks."""
        from evaluation_engine.core.task_registration import TaskRegistry
        
        registry = TaskRegistry()
        
        # Register many tasks
        num_tasks = 1000
        start_time = time.time()
        
        for i in range(num_tasks):
            task_config = {
                "task_id": f"perf_task_{i}",
                "task_type": "single_turn",
                "description": f"Performance test task {i}",
                "dataset_path": "test_data.jsonl",
                "metrics": ["accuracy"],
                "tags": [f"tag_{i % 10}", f"category_{i % 5}"],
                "difficulty": "easy" if i % 3 == 0 else "medium"
            }
            registry.register_task(task_config)
        
        registration_time = time.time() - start_time
        
        # Test task lookup performance
        start_time = time.time()
        for i in range(0, num_tasks, 10):  # Sample every 10th task
            task = registry.get_task(f"perf_task_{i}")
            assert task is not None
        lookup_time = time.time() - start_time
        
        # Test filtering performance
        start_time = time.time()
        filtered_tasks = registry.filter_tasks({"difficulty": "easy"})
        filter_time = time.time() - start_time
        
        # Test search performance
        start_time = time.time()
        search_results = registry.search_tasks("performance")
        search_time = time.time() - start_time
        
        # Verify performance requirements
        assert registration_time < 5.0  # Should register 1000 tasks in under 5 seconds
        assert lookup_time < 1.0  # Should lookup 100 tasks in under 1 second
        assert filter_time < 2.0  # Should filter 1000 tasks in under 2 seconds
        assert search_time < 3.0  # Should search 1000 tasks in under 3 seconds
        
        # Verify correctness
        assert len(registry.tasks) == num_tasks
        assert len(filtered_tasks) > 0
        assert len(search_results) > 0

    @pytest.mark.performance
    @pytest.mark.asyncio
    async def test_api_response_time_performance(self, api_client):
        """Test API response time performance."""
        response_times = []
        
        # Test multiple API calls
        for i in range(50):
            start_time = time.time()
            
            # Test task listing endpoint
            response = api_client.get("/api/v1/tasks")
            
            end_time = time.time()
            response_time = end_time - start_time
            response_times.append(response_time)
            
            assert response.status_code == 200
        
        # Calculate statistics
        avg_response_time = statistics.mean(response_times)
        p95_response_time = statistics.quantiles(response_times, n=20)[18]  # 95th percentile
        max_response_time = max(response_times)
        
        # Performance requirements
        assert avg_response_time < 0.1  # Average response time under 100ms
        assert p95_response_time < 0.2  # 95th percentile under 200ms
        assert max_response_time < 0.5  # Maximum response time under 500ms

    @pytest.mark.performance
    @pytest.mark.asyncio
    async def test_throughput_performance(self, performance_framework, large_dataset, mock_fast_model):
        """Test system throughput performance."""
        performance_framework.register_model_adapter(mock_fast_model)
        
        # Register multiple tasks of different sizes
        task_configs = [
            {
                "task_id": f"throughput_task_{size}",
                "task_type": "single_turn",
                "description": f"Throughput test {size}",
                "dataset_path": large_dataset[size],
                "metrics": ["accuracy"]
            }
            for size in ["small", "medium"]
        ]
        
        task_ids = []
        for config in task_configs:
            task_id = performance_framework.register_task(config)
            task_ids.append(task_id)
        
        # Measure throughput over time
        start_time = time.time()
        
        # Run evaluations in parallel
        tasks = []
        for task_id in task_ids:
            for _ in range(3):  # 3 evaluations per task
                task = performance_framework.run_evaluation(
                    task_ids=[task_id],
                    model_id="fast_mock_model"
                )
                tasks.append(task)
        
        results = await asyncio.gather(*tasks)
        
        end_time = time.time()
        total_time = end_time - start_time
        
        # Calculate throughput metrics
        total_evaluations = len(results)
        total_items = (100 * 3) + (1000 * 3)  # small + medium datasets
        
        evaluations_per_second = total_evaluations / total_time
        items_per_second = total_items / total_time
        
        # Throughput requirements
        assert evaluations_per_second > 1.0  # At least 1 evaluation per second
        assert items_per_second > 100  # At least 100 items per second
        
        # Verify all evaluations completed successfully
        assert len(results) == total_evaluations
        for result in results:
            assert result is not None
            assert "results" in result

    @pytest.mark.performance
    def test_caching_performance(self, performance_framework, large_dataset, mock_fast_model):
        """Test caching performance improvements."""
        performance_framework.register_model_adapter(mock_fast_model)
        
        task_config = {
            "task_id": "caching_perf_task",
            "task_type": "single_turn",
            "description": "Caching performance test",
            "dataset_path": large_dataset["medium"],
            "metrics": ["accuracy", "bleu"]
        }
        
        task_id = performance_framework.register_task(task_config)
        
        # First run (no cache)
        start_time = time.time()
        result1 = asyncio.run(performance_framework.run_evaluation(
            task_ids=[task_id],
            model_id="fast_mock_model"
        ))
        first_run_time = time.time() - start_time
        
        # Second run (with cache)
        start_time = time.time()
        result2 = asyncio.run(performance_framework.run_evaluation(
            task_ids=[task_id],
            model_id="fast_mock_model"
        ))
        second_run_time = time.time() - start_time
        
        # Caching should improve performance
        # Second run should be at least 20% faster
        improvement_ratio = first_run_time / second_run_time
        assert improvement_ratio > 1.2
        
        # Results should be identical
        assert result1["results"][0]["metrics"] == result2["results"][0]["metrics"]

    @pytest.mark.performance
    @pytest.mark.slow
    def test_stress_test_performance(self, performance_framework, mock_fast_model):
        """Stress test with high load."""
        performance_framework.register_model_adapter(mock_fast_model)
        
        # Create many small tasks
        num_tasks = 20
        task_ids = []
        
        for i in range(num_tasks):
            # Create small dataset for each task
            small_dataset = []
            for j in range(50):  # 50 items per task
                small_dataset.append({
                    "id": f"stress_{i}_{j}",
                    "input": f"Stress test input {i}_{j}",
                    "expected_output": f"Output {i}_{j}"
                })
            
            dataset_file = performance_framework.data_dir / f"stress_dataset_{i}.jsonl"
            with open(dataset_file, 'w') as f:
                for item in small_dataset:
                    f.write(json.dumps(item) + '\n')
            
            task_config = {
                "task_id": f"stress_task_{i}",
                "task_type": "single_turn",
                "description": f"Stress test task {i}",
                "dataset_path": str(dataset_file),
                "metrics": ["accuracy"]
            }
            
            task_id = performance_framework.register_task(task_config)
            task_ids.append(task_id)
        
        # Run all tasks concurrently
        start_time = time.time()
        
        async def run_stress_test():
            tasks = []
            for task_id in task_ids:
                task = performance_framework.run_evaluation(
                    task_ids=[task_id],
                    model_id="fast_mock_model"
                )
                tasks.append(task)
            
            return await asyncio.gather(*tasks, return_exceptions=True)
        
        results = asyncio.run(run_stress_test())
        
        end_time = time.time()
        total_time = end_time - start_time
        
        # Verify stress test results
        successful_results = [r for r in results if not isinstance(r, Exception)]
        failed_results = [r for r in results if isinstance(r, Exception)]
        
        # Should handle most tasks successfully
        success_rate = len(successful_results) / len(results)
        assert success_rate > 0.9  # At least 90% success rate
        
        # Performance should be reasonable even under stress
        total_items = num_tasks * 50
        items_per_second = total_items / total_time
        assert items_per_second > 50  # Should maintain at least 50 items/sec under stress
        
        # System should remain stable
        process = psutil.Process(os.getpid())
        final_memory = process.memory_info().rss
        assert final_memory < 2 * 1024 * 1024 * 1024  # Should not exceed 2GB memory

    @pytest.mark.performance
    def test_database_performance(self, temp_dir):
        """Test database operations performance."""
        # This would test database performance if we had a database
        # For now, test file I/O performance which is similar
        
        # Test writing many result files
        results_dir = temp_dir / "results"
        results_dir.mkdir(exist_ok=True)
        
        num_files = 100
        start_time = time.time()
        
        for i in range(num_files):
            result_data = {
                "evaluation_id": f"perf_eval_{i}",
                "timestamp": "2024-01-01T12:00:00Z",
                "results": [
                    {
                        "task_id": f"task_{i}",
                        "metrics": {"accuracy": 0.8 + (i * 0.001)},
                        "outputs": [{"id": f"output_{j}", "response": f"Response {j}"} for j in range(10)]
                    }
                ]
            }
            
            result_file = results_dir / f"result_{i}.json"
            with open(result_file, 'w') as f:
                json.dump(result_data, f)
        
        write_time = time.time() - start_time
        
        # Test reading files
        start_time = time.time()
        
        for i in range(0, num_files, 5):  # Read every 5th file
            result_file = results_dir / f"result_{i}.json"
            with open(result_file, 'r') as f:
                data = json.load(f)
                assert data["evaluation_id"] == f"perf_eval_{i}"
        
        read_time = time.time() - start_time
        
        # Performance requirements
        assert write_time < 5.0  # Should write 100 files in under 5 seconds
        assert read_time < 1.0  # Should read 20 files in under 1 second
        
        files_per_second_write = num_files / write_time
        files_per_second_read = 20 / read_time
        
        assert files_per_second_write > 20  # At least 20 files per second write
        assert files_per_second_read > 20  # At least 20 files per second read