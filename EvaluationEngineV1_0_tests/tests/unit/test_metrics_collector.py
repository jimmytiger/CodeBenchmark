"""
Unit tests for MetricsCollector component.

Tests metrics collection, aggregation, and analysis functionality.
"""

import pytest
import time
from unittest.mock import patch, MagicMock
from datetime import datetime, timedelta

import sys
import os
sys.path.append(os.path.join(os.path.dirname(__file__), '../../'))

from core.metrics_collector import MetricsCollector, ExecutionMetrics
from models.test_models import TestResult


class TestMetricsCollector:
    """Unit tests for MetricsCollector class."""
    
    def setup_method(self):
        """Set up test fixtures."""
        self.metrics_collector = MetricsCollector()
        self.sample_test_result = TestResult(
            test_id="test_001",
            test_type="unit",
            status="passed",
            execution_time=1.5,
            real_execution_validated=True,
            metrics={"accuracy": 0.95, "latency": 0.2},
            error_details=None,
            artifacts=["result.json"]
        )
    
    def test_start_timing(self):
        """Test starting timing measurement."""
        timer_id = self.metrics_collector.start_timing("test_operation")
        assert timer_id is not None
        assert timer_id in self.metrics_collector._active_timers
    
    def test_stop_timing(self):
        """Test stopping timing measurement."""
        timer_id = self.metrics_collector.start_timing("test_operation")
        time.sleep(0.1)  # Small delay to ensure measurable time
        
        elapsed_time = self.metrics_collector.stop_timing(timer_id)
        assert elapsed_time > 0
        assert timer_id not in self.metrics_collector._active_timers
    
    def test_stop_timing_invalid_id(self):
        """Test stopping timing with invalid timer ID."""
        with pytest.raises(ValueError, match="Timer ID not found"):
            self.metrics_collector.stop_timing("invalid_timer_id")
    
    def test_record_metric(self):
        """Test recording individual metrics."""
        self.metrics_collector.record_metric("accuracy", 0.95)
        self.metrics_collector.record_metric("latency", 0.2)
        
        metrics = self.metrics_collector.get_metrics()
        assert metrics["accuracy"] == 0.95
        assert metrics["latency"] == 0.2
    
    def test_record_test_result(self):
        """Test recording test result metrics."""
        self.metrics_collector.record_test_result(self.sample_test_result)
        
        metrics = self.metrics_collector.get_metrics()
        assert "test_results" in metrics
        assert len(metrics["test_results"]) == 1
        assert metrics["test_results"][0].test_id == "test_001"
    
    def test_calculate_success_rate(self):
        """Test success rate calculation."""
        # Add multiple test results
        passed_result = self.sample_test_result
        failed_result = TestResult(
            test_id="test_002",
            test_type="unit",
            status="failed",
            execution_time=0.8,
            real_execution_validated=True,
            metrics={},
            error_details="Test failed",
            artifacts=[]
        )
        
        self.metrics_collector.record_test_result(passed_result)
        self.metrics_collector.record_test_result(failed_result)
        
        success_rate = self.metrics_collector.calculate_success_rate()
        assert success_rate == 0.5  # 1 passed out of 2 total
    
    def test_calculate_average_execution_time(self):
        """Test average execution time calculation."""
        result1 = self.sample_test_result  # 1.5 seconds
        result2 = TestResult(
            test_id="test_002",
            test_type="unit",
            status="passed",
            execution_time=2.5,
            real_execution_validated=True,
            metrics={},
            error_details=None,
            artifacts=[]
        )
        
        self.metrics_collector.record_test_result(result1)
        self.metrics_collector.record_test_result(result2)
        
        avg_time = self.metrics_collector.calculate_average_execution_time()
        assert avg_time == 2.0  # (1.5 + 2.5) / 2
    
    def test_get_execution_metrics(self):
        """Test getting comprehensive execution metrics."""
        # Record some test results and metrics
        self.metrics_collector.record_test_result(self.sample_test_result)
        self.metrics_collector.record_metric("memory_usage_mb", 256)
        self.metrics_collector.record_metric("cpu_usage_percent", 45.2)
        
        execution_metrics = self.metrics_collector.get_execution_metrics()
        
        assert isinstance(execution_metrics, ExecutionMetrics)
        assert execution_metrics.total_execution_time > 0
        assert len(execution_metrics.task_execution_times) > 0
        assert "memory_usage_mb" in execution_metrics.memory_usage
        assert execution_metrics.success_rates["overall"] > 0
    
    def test_reset_metrics(self):
        """Test resetting all metrics."""
        self.metrics_collector.record_metric("test_metric", 100)
        self.metrics_collector.record_test_result(self.sample_test_result)
        
        # Verify metrics exist
        metrics = self.metrics_collector.get_metrics()
        assert len(metrics) > 0
        
        # Reset and verify empty
        self.metrics_collector.reset_metrics()
        metrics = self.metrics_collector.get_metrics()
        assert len(metrics) == 0
    
    def test_memory_usage_tracking(self):
        """Test memory usage tracking."""
        with patch('psutil.Process') as mock_process:
            mock_process.return_value.memory_info.return_value.rss = 1024 * 1024 * 100  # 100MB
            
            self.metrics_collector.track_memory_usage("test_component")
            metrics = self.metrics_collector.get_metrics()
            
            assert "memory_usage" in metrics
            assert "test_component" in metrics["memory_usage"]
    
    def test_api_response_time_tracking(self):
        """Test API response time tracking."""
        self.metrics_collector.record_api_response_time("/api/test", 0.5)
        self.metrics_collector.record_api_response_time("/api/test", 0.3)
        
        metrics = self.metrics_collector.get_metrics()
        assert "api_response_times" in metrics
        assert "/api/test" in metrics["api_response_times"]
        
        # Should have recorded both response times
        response_times = metrics["api_response_times"]["/api/test"]
        assert len(response_times) == 2
        assert 0.5 in response_times
        assert 0.3 in response_times
    
    def test_error_rate_calculation(self):
        """Test error rate calculation by test type."""
        # Add mixed results
        passed_unit = TestResult("test_001", "unit", "passed", 1.0, True, {}, None, [])
        failed_unit = TestResult("test_002", "unit", "failed", 1.0, True, {}, "Error", [])
        passed_integration = TestResult("test_003", "integration", "passed", 2.0, True, {}, None, [])
        
        for result in [passed_unit, failed_unit, passed_integration]:
            self.metrics_collector.record_test_result(result)
        
        error_rates = self.metrics_collector.calculate_error_rates()
        assert error_rates["unit"] == 0.5  # 1 failed out of 2 unit tests
        assert error_rates["integration"] == 0.0  # 0 failed out of 1 integration test
        assert error_rates["overall"] == 1/3  # 1 failed out of 3 total tests
    
    def test_performance_percentiles(self):
        """Test performance percentile calculations."""
        # Add multiple execution times
        execution_times = [1.0, 1.5, 2.0, 2.5, 3.0, 3.5, 4.0, 4.5, 5.0]
        for i, exec_time in enumerate(execution_times):
            result = TestResult(f"test_{i:03d}", "unit", "passed", exec_time, True, {}, None, [])
            self.metrics_collector.record_test_result(result)
        
        percentiles = self.metrics_collector.calculate_performance_percentiles()
        assert "p50" in percentiles
        assert "p90" in percentiles
        assert "p95" in percentiles
        assert "p99" in percentiles
        
        # P50 should be around the median
        assert abs(percentiles["p50"] - 3.0) < 0.5
    
    @patch('time.time')
    def test_timing_context_manager(self, mock_time):
        """Test timing context manager functionality."""
        mock_time.side_effect = [1000.0, 1001.5]  # 1.5 second duration
        
        with self.metrics_collector.time_operation("test_op") as timer:
            pass  # Simulate some operation
        
        metrics = self.metrics_collector.get_metrics()
        assert "operation_times" in metrics
        assert "test_op" in metrics["operation_times"]
        assert metrics["operation_times"]["test_op"] == 1.5