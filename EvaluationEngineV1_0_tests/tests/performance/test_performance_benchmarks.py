"""
Performance benchmarking tests for evaluation engine components.

Tests performance characteristics, scalability, and resource usage.
"""

import pytest
import time
import threading
import multiprocessing
import tempfile
import json
from pathlib import Path
from unittest.mock import patch, MagicMock
from concurrent.futures import ThreadPoolExecutor, ProcessPoolExecutor

import sys
import os
sys.path.append(os.path.join(os.path.dirname(__file__), '../../'))

from core.test_orchestrator import TestOrchestrator
from core.metrics_collector import MetricsCollector
from models.test_models import TestConfiguration, TestResult
from cli.cli_test_runner import CLITestRunner
from api.api_test_client import APITestClient


class TestPerformanceBenchmarks:
    """Performance benchmarking tests."""
    
    def setup_method(self):
        """Set up test fixtures."""
        self.orchestrator = TestOrchestrator()
        self.metrics_collector = MetricsCollector()
        self.cli_runner = CLITestRunner()
        self.api_client = APITestClient()
        self.temp_dir = tempfile.mkdtemp()
        
        # Performance test configuration
        self.perf_config = TestConfiguration(
            test_type='performance',
            target_adapters=['lm_eval', 'swe_bench'],
            task_selection={
                'builtin_tasks': ['hellaswag', 'arc_easy', 'winogrande'],
                'swe_tasks': ['django__django-12345', 'flask__flask-67890']
            },
            execution_params={
                'timeout': 1200,  # 20 minutes for performance tests
                'verbose': False,  # Reduce logging overhead
                'parallel_execution': True,
                'max_workers': 4
            },
            output_config={
                'format': 'json',
                'save_results': True,
                'output_dir': self.temp_dir
            }
        )
    
    def teardown_method(self):
        """Clean up test fixtures."""
        import shutil
        if os.path.exists(self.temp_dir):
            shutil.rmtree(self.temp_dir)
    
    def test_single_task_execution_performance(self):
        """Test performance of single task execution."""
        with patch('subprocess.run') as mock_run:
            mock_run.return_value.returncode = 0
            mock_run.return_value.stdout = json.dumps({
                "results": {"hellaswag": {"acc": 0.85}}
            })
            
            start_time = time.time()
            
            # Execute single task multiple times to get average
            execution_times = []
            for _ in range(5):
                task_start = time.time()
                result = self.cli_runner.run_builtin_tasks(['hellaswag'], {})
                task_end = time.time()
                execution_times.append(task_end - task_start)
            
            end_time = time.time()
            
            # Performance assertions
            avg_execution_time = sum(execution_times) / len(execution_times)
            assert avg_execution_time < 10.0  # Should complete within 10 seconds
            assert max(execution_times) - min(execution_times) < 5.0  # Low variance
            
            # Record performance metrics
            self.metrics_collector.record_metric('single_task_avg_time', avg_execution_time)
            self.metrics_collector.record_metric('single_task_variance', 
                                                max(execution_times) - min(execution_times))
    
    def test_parallel_execution_scalability(self):
        """Test scalability of parallel task execution."""
        task_counts = [1, 2, 4, 8, 16]
        execution_times = {}
        
        with patch('subprocess.run') as mock_run:
            mock_run.return_value.returncode = 0
            mock_run.return_value.stdout = json.dumps({
                "results": {"hellaswag": {"acc": 0.85}}
            })
            
            for task_count in task_counts:
                tasks = [f'task_{i}' for i in range(task_count)]
                
                start_time = time.time()
                
                # Execute tasks in parallel
                with ThreadPoolExecutor(max_workers=min(task_count, 4)) as executor:
                    futures = [
                        executor.submit(self.cli_runner.run_builtin_tasks, [task], {})
                        for task in tasks
                    ]
                    results = [future.result() for future in futures]
                
                end_time = time.time()
                execution_times[task_count] = end_time - start_time
                
                # Verify all tasks completed
                assert len(results) == task_count
        
        # Analyze scalability
        # Execution time should not increase linearly with task count
        assert execution_times[8] < execution_times[1] * 6  # Should be better than linear
        assert execution_times[16] < execution_times[1] * 12  # Should scale well
        
        # Record scalability metrics
        for count, exec_time in execution_times.items():
            self.metrics_collector.record_metric(f'parallel_execution_{count}_tasks', exec_time)
    
    def test_memory_usage_under_load(self):
        """Test memory usage under various load conditions."""
        import psutil
        
        process = psutil.Process()
        initial_memory = process.memory_info().rss / 1024 / 1024  # MB
        
        memory_measurements = []
        
        with patch('subprocess.run') as mock_run:
            mock_run.return_value.returncode = 0
            mock_run.return_value.stdout = json.dumps({
                "results": {"hellaswag": {"acc": 0.85}}
            })
            
            # Execute increasing numbers of tasks and measure memory
            for task_count in [1, 5, 10, 20]:
                tasks = [f'task_{i}' for i in range(task_count)]
                
                # Measure memory before execution
                memory_before = process.memory_info().rss / 1024 / 1024
                
                # Execute tasks
                results = []
                for task in tasks:
                    result = self.cli_runner.run_builtin_tasks([task], {})
                    results.append(result)
                
                # Measure memory after execution
                memory_after = process.memory_info().rss / 1024 / 1024
                memory_increase = memory_after - memory_before
                
                memory_measurements.append({
                    'task_count': task_count,
                    'memory_before': memory_before,
                    'memory_after': memory_after,
                    'memory_increase': memory_increase
                })
        
        # Memory usage should not grow excessively
        max_memory_increase = max(m['memory_increase'] for m in memory_measurements)
        assert max_memory_increase < 500  # Should not use more than 500MB additional
        
        # Memory increase should be roughly linear with task count
        memory_per_task = memory_measurements[-1]['memory_increase'] / memory_measurements[-1]['task_count']
        assert memory_per_task < 50  # Should not use more than 50MB per task
        
        # Record memory metrics
        for measurement in memory_measurements:
            self.metrics_collector.record_metric(
                f'memory_usage_{measurement["task_count"]}_tasks',
                measurement['memory_increase']
            )
    
    def test_cpu_utilization_efficiency(self):
        """Test CPU utilization efficiency during execution."""
        import psutil
        
        cpu_measurements = []
        
        with patch('subprocess.run') as mock_run:
            mock_run.return_value.returncode = 0
            mock_run.return_value.stdout = json.dumps({
                "results": {"hellaswag": {"acc": 0.85}}
            })
            
            # Test different levels of parallelism
            for worker_count in [1, 2, 4, 8]:
                config = self.perf_config
                config.execution_params['max_workers'] = worker_count
                
                # Start CPU monitoring
                cpu_percent_samples = []
                
                def monitor_cpu():
                    for _ in range(10):  # Monitor for 10 samples
                        cpu_percent_samples.append(psutil.cpu_percent(interval=0.1))
                
                monitor_thread = threading.Thread(target=monitor_cpu)
                monitor_thread.start()
                
                # Execute test suite
                start_time = time.time()
                results = self.orchestrator.execute_test_suite(config)
                end_time = time.time()
                
                monitor_thread.join()
                
                avg_cpu_usage = sum(cpu_percent_samples) / len(cpu_percent_samples)
                execution_time = end_time - start_time
                
                cpu_measurements.append({
                    'worker_count': worker_count,
                    'avg_cpu_usage': avg_cpu_usage,
                    'execution_time': execution_time,
                    'cpu_efficiency': avg_cpu_usage / worker_count  # CPU per worker
                })
        
        # CPU usage should increase with worker count but not linearly
        assert cpu_measurements[-1]['avg_cpu_usage'] > cpu_measurements[0]['avg_cpu_usage']
        
        # Execution time should decrease with more workers (up to a point)
        assert cpu_measurements[1]['execution_time'] <= cpu_measurements[0]['execution_time']
        
        # Record CPU metrics
        for measurement in cpu_measurements:
            self.metrics_collector.record_metric(
                f'cpu_usage_{measurement["worker_count"]}_workers',
                measurement['avg_cpu_usage']
            )
    
    def test_api_response_time_performance(self):
        """Test API response time performance under load."""
        response_times = []
        
        with patch('requests.post') as mock_post:
            mock_post.return_value.status_code = 200
            mock_post.return_value.json.return_value = {
                'evaluation_id': 'eval_123',
                'status': 'completed',
                'results': {'hellaswag': {'acc': 0.85}}
            }
            
            # Test API response times with concurrent requests
            concurrent_requests = [1, 5, 10, 20, 50]
            
            for request_count in concurrent_requests:
                start_time = time.time()
                
                with ThreadPoolExecutor(max_workers=min(request_count, 10)) as executor:
                    futures = [
                        executor.submit(self.api_client.run_evaluation, {'task': 'hellaswag'})
                        for _ in range(request_count)
                    ]
                    results = [future.result() for future in futures]
                
                end_time = time.time()
                total_time = end_time - start_time
                avg_response_time = total_time / request_count
                
                response_times.append({
                    'request_count': request_count,
                    'total_time': total_time,
                    'avg_response_time': avg_response_time,
                    'requests_per_second': request_count / total_time
                })
                
                # Verify all requests completed successfully
                assert len(results) == request_count
        
        # Response time should not degrade significantly under load
        single_request_time = response_times[0]['avg_response_time']
        high_load_time = response_times[-1]['avg_response_time']
        assert high_load_time < single_request_time * 3  # Should not be more than 3x slower
        
        # Should handle reasonable throughput
        max_throughput = max(rt['requests_per_second'] for rt in response_times)
        assert max_throughput > 5  # Should handle at least 5 requests per second
        
        # Record API performance metrics
        for measurement in response_times:
            self.metrics_collector.record_metric(
                f'api_response_time_{measurement["request_count"]}_requests',
                measurement['avg_response_time']
            )
    
    def test_large_dataset_processing_performance(self):
        """Test performance with large datasets."""
        dataset_sizes = [100, 500, 1000, 5000]
        processing_times = []
        
        with patch('subprocess.run') as mock_run:
            for size in dataset_sizes:
                # Mock large dataset results
                mock_results = {
                    f"task_{i}": {"acc": 0.85, "processing_time": 0.1}
                    for i in range(size)
                }
                
                mock_run.return_value.returncode = 0
                mock_run.return_value.stdout = json.dumps({"results": mock_results})
                
                start_time = time.time()
                
                # Process large dataset
                config = self.perf_config
                config.task_selection['builtin_tasks'] = [f'task_{i}' for i in range(size)]
                
                results = self.orchestrator.execute_test_suite(config)
                
                end_time = time.time()
                processing_time = end_time - start_time
                
                processing_times.append({
                    'dataset_size': size,
                    'processing_time': processing_time,
                    'items_per_second': size / processing_time
                })
        
        # Processing should scale reasonably with dataset size
        # Time should increase but not exponentially
        largest_dataset = processing_times[-1]
        smallest_dataset = processing_times[0]
        
        time_ratio = largest_dataset['processing_time'] / smallest_dataset['processing_time']
        size_ratio = largest_dataset['dataset_size'] / smallest_dataset['dataset_size']
        
        # Time increase should be less than size increase (due to parallelization)
        assert time_ratio < size_ratio
        
        # Should maintain reasonable throughput even with large datasets
        min_throughput = min(pt['items_per_second'] for pt in processing_times)
        assert min_throughput > 1  # Should process at least 1 item per second
        
        # Record dataset processing metrics
        for measurement in processing_times:
            self.metrics_collector.record_metric(
                f'dataset_processing_{measurement["dataset_size"]}_items',
                measurement['processing_time']
            )
    
    def test_concurrent_user_simulation(self):
        """Test performance under concurrent user load."""
        user_counts = [1, 5, 10, 25]
        performance_results = []
        
        def simulate_user_session():
            """Simulate a user session with multiple operations."""
            session_start = time.time()
            
            with patch('subprocess.run') as mock_run:
                mock_run.return_value.returncode = 0
                mock_run.return_value.stdout = json.dumps({
                    "results": {"hellaswag": {"acc": 0.85}}
                })
                
                # Simulate user workflow
                operations = [
                    lambda: self.cli_runner.run_builtin_tasks(['hellaswag'], {}),
                    lambda: self.cli_runner.run_builtin_tasks(['arc_easy'], {}),
                ]
                
                for operation in operations:
                    operation()
            
            session_end = time.time()
            return session_end - session_start
        
        for user_count in user_counts:
            start_time = time.time()
            
            # Simulate concurrent users
            with ThreadPoolExecutor(max_workers=user_count) as executor:
                futures = [
                    executor.submit(simulate_user_session)
                    for _ in range(user_count)
                ]
                session_times = [future.result() for future in futures]
            
            end_time = time.time()
            total_time = end_time - start_time
            
            performance_results.append({
                'user_count': user_count,
                'total_time': total_time,
                'avg_session_time': sum(session_times) / len(session_times),
                'max_session_time': max(session_times),
                'users_per_second': user_count / total_time
            })
        
        # System should handle concurrent users reasonably
        single_user_time = performance_results[0]['avg_session_time']
        multi_user_time = performance_results[-1]['avg_session_time']
        
        # Session time should not degrade too much under load
        assert multi_user_time < single_user_time * 2
        
        # Should support reasonable concurrent user load
        max_concurrent_throughput = max(pr['users_per_second'] for pr in performance_results)
        assert max_concurrent_throughput > 2  # Should handle at least 2 users per second
        
        # Record concurrent user metrics
        for measurement in performance_results:
            self.metrics_collector.record_metric(
                f'concurrent_users_{measurement["user_count"]}',
                measurement['avg_session_time']
            )
    
    def test_memory_leak_detection(self):
        """Test for memory leaks during extended operation."""
        import psutil
        import gc
        
        process = psutil.Process()
        memory_samples = []
        
        with patch('subprocess.run') as mock_run:
            mock_run.return_value.returncode = 0
            mock_run.return_value.stdout = json.dumps({
                "results": {"hellaswag": {"acc": 0.85}}
            })
            
            # Run multiple iterations and monitor memory
            for iteration in range(20):
                # Force garbage collection before measurement
                gc.collect()
                
                memory_before = process.memory_info().rss / 1024 / 1024  # MB
                
                # Execute test operation
                result = self.cli_runner.run_builtin_tasks(['hellaswag'], {})
                
                memory_after = process.memory_info().rss / 1024 / 1024  # MB
                
                memory_samples.append({
                    'iteration': iteration,
                    'memory_before': memory_before,
                    'memory_after': memory_after,
                    'memory_increase': memory_after - memory_before
                })
                
                # Small delay between iterations
                time.sleep(0.1)
        
        # Analyze memory trend
        memory_increases = [sample['memory_increase'] for sample in memory_samples]
        avg_increase = sum(memory_increases) / len(memory_increases)
        
        # Memory should not consistently increase (indicating a leak)
        # Allow for some variation but overall trend should be stable
        assert avg_increase < 5  # Should not consistently increase by more than 5MB per iteration
        
        # Check for consistent upward trend (potential leak)
        first_half_avg = sum(memory_increases[:10]) / 10
        second_half_avg = sum(memory_increases[10:]) / 10
        
        # Second half should not be significantly higher than first half
        assert second_half_avg < first_half_avg + 10  # Allow 10MB tolerance
        
        # Record memory leak metrics
        self.metrics_collector.record_metric('avg_memory_increase_per_iteration', avg_increase)
        self.metrics_collector.record_metric('memory_trend_difference', second_half_avg - first_half_avg)
    
    def test_generate_performance_report(self):
        """Test generation of comprehensive performance report."""
        # Execute various performance tests to collect metrics
        self.test_single_task_execution_performance()
        self.test_memory_usage_under_load()
        self.test_api_response_time_performance()
        
        # Generate performance report
        performance_report = self.metrics_collector.generate_performance_report()
        
        assert 'summary' in performance_report
        assert 'detailed_metrics' in performance_report
        assert 'performance_analysis' in performance_report
        assert 'recommendations' in performance_report
        
        # Verify report completeness
        assert len(performance_report['detailed_metrics']) > 0
        assert 'execution_time' in performance_report['summary']
        assert 'memory_usage' in performance_report['summary']
        assert 'throughput' in performance_report['summary']
        
        # Save performance report
        report_path = Path(self.temp_dir) / "performance_report.json"
        with open(report_path, 'w') as f:
            json.dump(performance_report, f, indent=2)
        
        assert report_path.exists()
        assert report_path.stat().st_size > 0