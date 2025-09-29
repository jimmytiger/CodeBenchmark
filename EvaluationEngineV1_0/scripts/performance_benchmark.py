#!/usr/bin/env python3
"""
Performance Benchmarking Script for Multi-Turn Evaluation Engine.

This script runs comprehensive performance benchmarks to establish baselines
and detect performance regressions across different system components.
"""

import asyncio
import json
import logging
import os
import sys
import time
from datetime import datetime
from pathlib import Path
from typing import Dict, List, Any, Optional
import argparse
import statistics

# Add the parent directory to the path so we can import our modules
sys.path.insert(0, str(Path(__file__).parent.parent))

from core.performance_optimizer import (
    PerformanceOptimizer, PerformanceCache, PerformanceProfiler,
    ConcurrentExecutionManager, SystemMonitor
)
from core.orchestrator import MultiTurnOrchestrator
from core.metrics_engine import MetricsEngine
from core.data_models import EvaluationResult, TurnResult, MultiTurnConfig
from core.task_types import MultiTurnTask, TurnData

logger = logging.getLogger(__name__)


class BenchmarkTask(MultiTurnTask):
    """Benchmark task for performance testing."""
    
    def __init__(self, task_id: str, complexity: int = 100):
        """Initialize benchmark task.
        
        Args:
            task_id: Unique task identifier
            complexity: Task complexity factor (affects computation time)
        """
        self.task_id = task_id
        self.complexity = complexity
        self.turn_count = 0
        self.max_turns = 5
    
    def get_id(self) -> str:
        return self.task_id
    
    def get_config(self) -> Dict[str, Any]:
        return {
            'complexity': self.complexity,
            'max_turns': self.max_turns
        }
    
    def execute_turn(self, turn_data: TurnData) -> TurnResult:
        """Execute a benchmark turn."""
        start_time = time.time()
        
        # Simulate computational work based on complexity
        result = sum(i * i for i in range(self.complexity))
        
        # Simulate some processing time
        time.sleep(0.01 * (self.complexity / 100))
        
        execution_time = time.time() - start_time
        self.turn_count += 1
        
        # Determine if task is complete
        done = self.turn_count >= self.max_turns
        reward = 1.0 if done else 0.5
        
        return TurnResult(
            turn=turn_data.turn_number,
            action=f"benchmark_action_{turn_data.turn_number}",
            observation=f"benchmark_result_{result}",
            reward=reward,
            done=done,
            info={
                'computation_result': result,
                'complexity': self.complexity,
                'turn_count': self.turn_count
            },
            execution_time=execution_time,
            tokens_used=self.complexity // 10,  # Simulate token usage
            cost=execution_time * 0.001  # Simulate cost
        )
    
    def should_continue(self, turn_result: TurnResult) -> bool:
        """Check if task should continue."""
        return not turn_result.done


class MockModelAdapter:
    """Mock model adapter for benchmarking."""
    
    def __init__(self, model_id: str = "benchmark_model"):
        self.model_id = model_id
    
    async def generate_action(self, turn_data: TurnData) -> str:
        """Generate a mock action."""
        # Simulate some processing time
        await asyncio.sleep(0.005)
        return f"action_turn_{turn_data.turn_number}"


class PerformanceBenchmark:
    """Main performance benchmarking class."""
    
    def __init__(self, output_dir: str = "benchmark_results"):
        """Initialize the benchmark.
        
        Args:
            output_dir: Directory to save benchmark results
        """
        self.output_dir = Path(output_dir)
        self.output_dir.mkdir(exist_ok=True)
        
        self.optimizer = PerformanceOptimizer()
        self.results: Dict[str, Any] = {}
        self.baseline_file = self.output_dir / "performance_baseline.json"
    
    async def run_all_benchmarks(self) -> Dict[str, Any]:
        """Run all performance benchmarks."""
        logger.info("Starting comprehensive performance benchmarks")
        
        await self.optimizer.start()
        
        try:
            # Run individual benchmark suites
            cache_results = await self.benchmark_caching_performance()
            concurrency_results = await self.benchmark_concurrent_execution()
            orchestrator_results = await self.benchmark_orchestrator_performance()
            metrics_results = await self.benchmark_metrics_calculation()
            memory_results = await self.benchmark_memory_usage()
            scaling_results = await self.benchmark_scaling_performance()
            
            # Compile overall results
            self.results = {
                'timestamp': datetime.now().isoformat(),
                'system_info': self._get_system_info(),
                'benchmarks': {
                    'caching': cache_results,
                    'concurrency': concurrency_results,
                    'orchestrator': orchestrator_results,
                    'metrics': metrics_results,
                    'memory': memory_results,
                    'scaling': scaling_results
                },
                'summary': self._generate_summary()
            }
            
            # Save results
            await self._save_results()
            
            # Compare with baseline if available
            regression_analysis = await self._analyze_regressions()
            if regression_analysis:
                self.results['regression_analysis'] = regression_analysis
            
            logger.info("Performance benchmarks completed successfully")
            return self.results
            
        finally:
            await self.optimizer.stop()
    
    async def benchmark_caching_performance(self) -> Dict[str, Any]:
        """Benchmark caching system performance."""
        logger.info("Benchmarking caching performance")
        
        cache = PerformanceCache(max_size=10000, default_ttl=3600)
        
        # Test cache write performance
        write_times = []
        for i in range(1000):
            start_time = time.time()
            cache.set(f"key_{i}", f"value_{i}")
            write_times.append(time.time() - start_time)
        
        # Test cache read performance (hits)
        read_hit_times = []
        for i in range(500):
            start_time = time.time()
            cache.get(f"key_{i}")
            read_hit_times.append(time.time() - start_time)
        
        # Test cache read performance (misses)
        read_miss_times = []
        for i in range(500):
            start_time = time.time()
            cache.get(f"nonexistent_key_{i}")
            read_miss_times.append(time.time() - start_time)
        
        # Test cache eviction performance
        eviction_start = time.time()
        for i in range(1000, 12000):  # Trigger evictions
            cache.set(f"key_{i}", f"value_{i}")
        eviction_time = time.time() - eviction_start
        
        stats = cache.get_stats()
        
        return {
            'write_performance': {
                'avg_time': statistics.mean(write_times),
                'median_time': statistics.median(write_times),
                'max_time': max(write_times),
                'operations_per_second': 1000 / sum(write_times)
            },
            'read_hit_performance': {
                'avg_time': statistics.mean(read_hit_times),
                'median_time': statistics.median(read_hit_times),
                'max_time': max(read_hit_times),
                'operations_per_second': 500 / sum(read_hit_times)
            },
            'read_miss_performance': {
                'avg_time': statistics.mean(read_miss_times),
                'median_time': statistics.median(read_miss_times),
                'max_time': max(read_miss_times),
                'operations_per_second': 500 / sum(read_miss_times)
            },
            'eviction_performance': {
                'total_time': eviction_time,
                'operations_per_second': 1000 / eviction_time
            },
            'final_stats': stats
        }
    
    async def benchmark_concurrent_execution(self) -> Dict[str, Any]:
        """Benchmark concurrent execution performance."""
        logger.info("Benchmarking concurrent execution performance")
        
        results = {}
        
        # Test different concurrency levels
        concurrency_levels = [1, 2, 4, 8, 16]
        task_counts = [10, 50, 100]
        
        for task_count in task_counts:
            results[f'tasks_{task_count}'] = {}
            
            for concurrency in concurrency_levels:
                # Create CPU-intensive tasks
                def cpu_task(n):
                    return sum(i * i for i in range(n * 100))
                
                tasks = [lambda i=i: cpu_task(i) for i in range(task_count)]
                
                async with ConcurrentExecutionManager(max_workers=concurrency) as manager:
                    start_time = time.time()
                    task_results = await manager.execute_concurrent_evaluations(
                        tasks, max_concurrent=concurrency
                    )
                    end_time = time.time()
                
                execution_time = end_time - start_time
                throughput = len(task_results) / execution_time
                
                results[f'tasks_{task_count}'][f'concurrency_{concurrency}'] = {
                    'execution_time': execution_time,
                    'throughput': throughput,
                    'tasks_completed': len(task_results),
                    'avg_time_per_task': execution_time / len(task_results)
                }
        
        return results
    
    async def benchmark_orchestrator_performance(self) -> Dict[str, Any]:
        """Benchmark orchestrator performance."""
        logger.info("Benchmarking orchestrator performance")
        
        orchestrator = MultiTurnOrchestrator()
        model_adapter = MockModelAdapter()
        
        results = {}
        
        # Test different task complexities
        complexities = [50, 100, 200, 500]
        
        for complexity in complexities:
            task = BenchmarkTask(f"benchmark_task_{complexity}", complexity)
            config = MultiTurnConfig(max_turns=5, conversation_timeout=60)
            
            start_time = time.time()
            evaluation_result = await orchestrator.execute_evaluation(
                task, model_adapter, config
            )
            end_time = time.time()
            
            execution_time = end_time - start_time
            
            results[f'complexity_{complexity}'] = {
                'execution_time': execution_time,
                'total_turns': evaluation_result.total_turns,
                'success': evaluation_result.success,
                'avg_time_per_turn': execution_time / evaluation_result.total_turns,
                'final_metrics': evaluation_result.final_metrics
            }
        
        return results
    
    async def benchmark_metrics_calculation(self) -> Dict[str, Any]:
        """Benchmark metrics calculation performance."""
        logger.info("Benchmarking metrics calculation performance")
        
        metrics_engine = MetricsEngine()
        
        # Create mock evaluation results
        evaluation_counts = [10, 50, 100, 500]
        results = {}
        
        for count in evaluation_counts:
            evaluation_results = []
            
            for i in range(count):
                # Create mock turn results
                turn_results = []
                for turn in range(5):
                    turn_result = TurnResult(
                        turn=turn + 1,
                        action=f"action_{turn}",
                        observation=f"observation_{turn}",
                        reward=0.8 if turn < 4 else 1.0,
                        done=turn == 4,
                        info={'files_changed': [f'file_{turn}.py']},
                        execution_time=0.1,
                        tokens_used=100,
                        cost=0.01
                    )
                    turn_results.append(turn_result)
                
                evaluation_result = EvaluationResult(
                    evaluation_id=f"eval_{i}",
                    task_id=f"task_{i}",
                    model_id="benchmark_model",
                    start_time=datetime.now(),
                    end_time=datetime.now(),
                    success=True,
                    total_turns=5,
                    turn_results=turn_results,
                    final_metrics={},
                    aggregated_metrics=None,
                    metadata={}
                )
                evaluation_results.append(evaluation_result)
            
            # Benchmark metrics calculation
            start_time = time.time()
            aggregated_metrics = metrics_engine.calculate_all_metrics(evaluation_results)
            end_time = time.time()
            
            calculation_time = end_time - start_time
            
            results[f'evaluations_{count}'] = {
                'calculation_time': calculation_time,
                'evaluations_per_second': count / calculation_time,
                'metrics_calculated': len(aggregated_metrics.to_dict()),
                'avg_time_per_evaluation': calculation_time / count
            }
        
        return results
    
    async def benchmark_memory_usage(self) -> Dict[str, Any]:
        """Benchmark memory usage patterns."""
        logger.info("Benchmarking memory usage")
        
        import psutil
        process = psutil.Process()
        
        initial_memory = process.memory_info().rss / 1024 / 1024  # MB
        
        # Test memory usage with different data sizes
        data_sizes = [1000, 5000, 10000, 50000]
        results = {}
        
        for size in data_sizes:
            # Create large data structures
            large_data = []
            
            start_memory = process.memory_info().rss / 1024 / 1024
            
            for i in range(size):
                large_data.append({
                    'id': i,
                    'data': list(range(100)),
                    'metadata': {'timestamp': datetime.now(), 'size': 100}
                })
            
            peak_memory = process.memory_info().rss / 1024 / 1024
            memory_increase = peak_memory - start_memory
            
            # Clean up
            del large_data
            
            # Force garbage collection
            import gc
            gc.collect()
            
            final_memory = process.memory_info().rss / 1024 / 1024
            memory_recovered = peak_memory - final_memory
            
            results[f'size_{size}'] = {
                'memory_increase_mb': memory_increase,
                'peak_memory_mb': peak_memory,
                'memory_recovered_mb': memory_recovered,
                'memory_per_item_kb': (memory_increase * 1024) / size
            }
        
        return {
            'initial_memory_mb': initial_memory,
            'memory_tests': results
        }
    
    async def benchmark_scaling_performance(self) -> Dict[str, Any]:
        """Benchmark performance scaling characteristics."""
        logger.info("Benchmarking scaling performance")
        
        results = {}
        
        # Test scaling with different numbers of concurrent evaluations
        concurrent_counts = [1, 2, 4, 8]
        
        for concurrent_count in concurrent_counts:
            tasks = []
            
            for i in range(concurrent_count):
                async def evaluation_task():
                    orchestrator = MultiTurnOrchestrator()
                    task = BenchmarkTask(f"scale_task_{i}", complexity=100)
                    model_adapter = MockModelAdapter()
                    config = MultiTurnConfig(max_turns=3, conversation_timeout=30)
                    
                    return await orchestrator.execute_evaluation(task, model_adapter, config)
                
                tasks.append(evaluation_task)
            
            start_time = time.time()
            evaluation_results = await self.optimizer.optimize_concurrent_execution(
                tasks, max_concurrent=concurrent_count
            )
            end_time = time.time()
            
            execution_time = end_time - start_time
            throughput = len(evaluation_results) / execution_time
            
            # Calculate efficiency (throughput per unit of concurrency)
            efficiency = throughput / concurrent_count
            
            results[f'concurrent_{concurrent_count}'] = {
                'execution_time': execution_time,
                'throughput': throughput,
                'efficiency': efficiency,
                'evaluations_completed': len(evaluation_results),
                'avg_time_per_evaluation': execution_time / len(evaluation_results)
            }
        
        return results
    
    def _get_system_info(self) -> Dict[str, Any]:
        """Get system information for benchmark context."""
        import platform
        import psutil
        
        return {
            'platform': platform.platform(),
            'python_version': platform.python_version(),
            'cpu_count': psutil.cpu_count(),
            'memory_total_gb': psutil.virtual_memory().total / (1024**3),
            'timestamp': datetime.now().isoformat()
        }
    
    def _generate_summary(self) -> Dict[str, Any]:
        """Generate benchmark summary."""
        summary = {
            'overall_performance': 'good',  # Would be calculated based on metrics
            'key_metrics': {},
            'recommendations': []
        }
        
        # Extract key metrics from benchmark results
        if 'caching' in self.results.get('benchmarks', {}):
            cache_perf = self.results['benchmarks']['caching']
            summary['key_metrics']['cache_write_ops_per_sec'] = cache_perf['write_performance']['operations_per_second']
            summary['key_metrics']['cache_read_ops_per_sec'] = cache_perf['read_hit_performance']['operations_per_second']
        
        if 'orchestrator' in self.results.get('benchmarks', {}):
            orch_perf = self.results['benchmarks']['orchestrator']
            # Get average execution time across complexities
            exec_times = [v['execution_time'] for v in orch_perf.values()]
            summary['key_metrics']['avg_orchestrator_time'] = statistics.mean(exec_times)
        
        # Generate recommendations based on performance
        if summary['key_metrics'].get('cache_write_ops_per_sec', 0) < 1000:
            summary['recommendations'].append("Consider optimizing cache write performance")
        
        if summary['key_metrics'].get('avg_orchestrator_time', 0) > 5.0:
            summary['recommendations'].append("Orchestrator performance may need optimization")
        
        return summary
    
    async def _save_results(self) -> None:
        """Save benchmark results to file."""
        timestamp = datetime.now().strftime("%Y%m%d_%H%M%S")
        results_file = self.output_dir / f"benchmark_results_{timestamp}.json"
        
        with open(results_file, 'w') as f:
            json.dump(self.results, f, indent=2, default=str)
        
        logger.info(f"Benchmark results saved to {results_file}")
        
        # Also save as latest results
        latest_file = self.output_dir / "latest_benchmark_results.json"
        with open(latest_file, 'w') as f:
            json.dump(self.results, f, indent=2, default=str)
    
    async def _analyze_regressions(self) -> Optional[Dict[str, Any]]:
        """Analyze performance regressions against baseline."""
        if not self.baseline_file.exists():
            logger.info("No baseline found, saving current results as baseline")
            with open(self.baseline_file, 'w') as f:
                json.dump(self.results, f, indent=2, default=str)
            return None
        
        # Load baseline
        with open(self.baseline_file, 'r') as f:
            baseline = json.load(f)
        
        regressions = []
        improvements = []
        
        # Compare key metrics
        current_summary = self.results.get('summary', {}).get('key_metrics', {})
        baseline_summary = baseline.get('summary', {}).get('key_metrics', {})
        
        for metric, current_value in current_summary.items():
            if metric in baseline_summary:
                baseline_value = baseline_summary[metric]
                change_percent = ((current_value - baseline_value) / baseline_value) * 100
                
                if abs(change_percent) > 5:  # 5% threshold
                    change_info = {
                        'metric': metric,
                        'current_value': current_value,
                        'baseline_value': baseline_value,
                        'change_percent': change_percent
                    }
                    
                    if change_percent < 0:  # Performance degradation
                        regressions.append(change_info)
                    else:  # Performance improvement
                        improvements.append(change_info)
        
        return {
            'regressions': regressions,
            'improvements': improvements,
            'baseline_timestamp': baseline.get('timestamp'),
            'comparison_timestamp': self.results.get('timestamp')
        }
    
    async def establish_baseline(self) -> None:
        """Establish performance baseline."""
        logger.info("Establishing performance baseline")
        
        results = await self.run_all_benchmarks()
        
        with open(self.baseline_file, 'w') as f:
            json.dump(results, f, indent=2, default=str)
        
        logger.info(f"Performance baseline established and saved to {self.baseline_file}")


async def main():
    """Main benchmark execution function."""
    parser = argparse.ArgumentParser(description="Performance Benchmark Suite")
    parser.add_argument("--output-dir", default="benchmark_results",
                       help="Output directory for benchmark results")
    parser.add_argument("--establish-baseline", action="store_true",
                       help="Establish new performance baseline")
    parser.add_argument("--verbose", "-v", action="store_true",
                       help="Enable verbose logging")
    
    args = parser.parse_args()
    
    # Configure logging
    log_level = logging.DEBUG if args.verbose else logging.INFO
    logging.basicConfig(
        level=log_level,
        format='%(asctime)s - %(name)s - %(levelname)s - %(message)s'
    )
    
    benchmark = PerformanceBenchmark(args.output_dir)
    
    try:
        if args.establish_baseline:
            await benchmark.establish_baseline()
        else:
            results = await benchmark.run_all_benchmarks()
            
            # Print summary
            print("\n" + "="*60)
            print("PERFORMANCE BENCHMARK SUMMARY")
            print("="*60)
            
            summary = results.get('summary', {})
            print(f"Overall Performance: {summary.get('overall_performance', 'unknown')}")
            
            print("\nKey Metrics:")
            for metric, value in summary.get('key_metrics', {}).items():
                print(f"  {metric}: {value:.2f}")
            
            print("\nRecommendations:")
            for rec in summary.get('recommendations', []):
                print(f"  - {rec}")
            
            # Print regression analysis if available
            if 'regression_analysis' in results:
                regression = results['regression_analysis']
                
                if regression['regressions']:
                    print("\n⚠️  PERFORMANCE REGRESSIONS DETECTED:")
                    for reg in regression['regressions']:
                        print(f"  - {reg['metric']}: {reg['change_percent']:.1f}% slower")
                
                if regression['improvements']:
                    print("\n✅ PERFORMANCE IMPROVEMENTS:")
                    for imp in regression['improvements']:
                        print(f"  + {imp['metric']}: {imp['change_percent']:.1f}% faster")
            
            print(f"\nDetailed results saved to: {args.output_dir}")
            
    except Exception as e:
        logger.error(f"Benchmark failed: {e}")
        sys.exit(1)


if __name__ == "__main__":
    asyncio.run(main())