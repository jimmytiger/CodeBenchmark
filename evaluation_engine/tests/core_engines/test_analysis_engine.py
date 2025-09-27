#!/usr/bin/env python3
"""
Test suite for AnalysisEngine implementation.

Tests statistical analysis capabilities including trend identification,
anomaly detection, cross-model comparison, and pattern recognition.
"""

import unittest
import time
import statistics
import random
from typing import Dict, List, Any

from evaluation_engine.core.analysis_engine import (
    AnalysisEngine, TrendType, AnomalyType, TrendAnalysis, 
    AnomalyDetection, PerformanceComparison, PatternRecognition
)
from evaluation_engine.core.metrics_engine import MetricResult, MetricType
from evaluation_engine.core.composite_metrics import CompositeMetricsSystem
from evaluation_engine.core.scenario_metrics import ScenarioSpecificMetrics


class TestAnalysisEngine(unittest.TestCase):
    """Test cases for AnalysisEngine."""
    
    def setUp(self):
        """Set up test fixtures."""
        self.analysis_engine = AnalysisEngine()
        
        # Create sample evaluation results
        self.sample_results = self._create_sample_evaluation_results()
        
        # Add results to engine
        for result in self.sample_results:
            self.analysis_engine.add_evaluation_result(result)
    
    def _create_sample_evaluation_results(self) -> List[Dict[str, Any]]:
        """Create sample evaluation results for testing."""
        results = []
        base_time = time.time() - 3600  # 1 hour ago
        
        for i in range(20):
            timestamp = base_time + i * 180  # 3 minutes apart
            
            # Create trending data
            trend_factor = i * 0.02  # Gradual improvement
            noise = random.uniform(-0.1, 0.1)
            
            metrics = {
                'bleu': MetricResult(
                    name='bleu',
                    value=0.6 + trend_factor + noise,
                    metric_type=MetricType.STANDARD_NLP
                ),
                'code_quality': MetricResult(
                    name='code_quality',
                    value=0.7 + trend_factor * 0.5 + noise,
                    metric_type=MetricType.CODE_QUALITY
                ),
                'pass_at_1': MetricResult(
                    name='pass_at_1',
                    value=0.5 + trend_factor * 1.5 + noise,
                    metric_type=MetricType.FUNCTIONAL
                )
            }
            
            # Add some anomalies
            if i == 10:  # Anomaly at position 10
                metrics['bleu'].value = 0.2  # Sudden drop
            elif i == 15:  # Another anomaly
                metrics['code_quality'].value = 0.95  # Sudden spike
            
            results.append({
                'evaluation_id': f'eval_{i}',
                'timestamp': timestamp,
                'model_name': 'test_model',
                'metrics': metrics
            })
        
        return results
    
    def test_trend_analysis(self):
        """Test trend analysis functionality."""
        print("\n=== Testing Trend Analysis ===")
        
        # Test trend analysis for improving metric
        trend = self.analysis_engine.perform_trend_analysis('pass_at_1')
        
        self.assertIsNotNone(trend)
        self.assertIsInstance(trend, TrendAnalysis)
        
        print(f"Trend Type: {trend.trend_type}")
        print(f"Confidence: {trend.confidence:.3f}")
        print(f"Slope: {trend.slope:.6f}")
        print(f"R-squared: {trend.r_squared:.3f}")
        print(f"Change Rate: {trend.change_rate:.6f}")
        
        # Should detect increasing trend for pass_at_1
        self.assertEqual(trend.trend_type, TrendType.INCREASING)
        self.assertGreater(trend.confidence, 0.1)  # Lower threshold due to noise
        self.assertGreater(trend.slope, 0)
        
        # Test trend analysis for stable metric
        stable_trend = self.analysis_engine.perform_trend_analysis('code_quality')
        self.assertIsNotNone(stable_trend)
        
        print(f"\nStable Metric Trend: {stable_trend.trend_type}")
        print(f"Stable Metric Confidence: {stable_trend.confidence:.3f}")
    
    def test_anomaly_detection(self):
        """Test anomaly detection functionality."""
        print("\n=== Testing Anomaly Detection ===")
        
        # Detect anomalies in all metrics
        anomalies = self.analysis_engine.detect_anomalies()
        
        self.assertIsInstance(anomalies, list)
        self.assertGreater(len(anomalies), 0)  # Should detect the anomalies we added
        
        print(f"Total anomalies detected: {len(anomalies)}")
        
        for anomaly in anomalies[:5]:  # Show first 5
            print(f"Anomaly: {anomaly.anomaly_type.value}")
            print(f"  Severity: {anomaly.severity:.3f}")
            print(f"  Confidence: {anomaly.confidence:.3f}")
            print(f"  Metrics: {anomaly.affected_metrics}")
            print(f"  Description: {anomaly.description}")
            print()
        
        # Test specific metric anomaly detection
        bleu_anomalies = self.analysis_engine.detect_anomalies('bleu')
        self.assertGreater(len(bleu_anomalies), 0)
        
        # Should detect the sudden drop we added
        outlier_anomalies = [a for a in bleu_anomalies if a.anomaly_type == AnomalyType.OUTLIER_LOW]
        self.assertGreater(len(outlier_anomalies), 0)
    
    def test_model_comparison(self):
        """Test cross-model performance comparison."""
        print("\n=== Testing Model Comparison ===")
        
        # Create results for multiple models
        model_results = {
            'model_a': {
                'metrics': {
                    'bleu': MetricResult('bleu', 0.75, MetricType.STANDARD_NLP),
                    'code_quality': MetricResult('code_quality', 0.80, MetricType.CODE_QUALITY),
                    'pass_at_1': MetricResult('pass_at_1', 0.65, MetricType.FUNCTIONAL)
                }
            },
            'model_b': {
                'metrics': {
                    'bleu': MetricResult('bleu', 0.70, MetricType.STANDARD_NLP),
                    'code_quality': MetricResult('code_quality', 0.85, MetricType.CODE_QUALITY),
                    'pass_at_1': MetricResult('pass_at_1', 0.60, MetricType.FUNCTIONAL)
                }
            },
            'model_c': {
                'metrics': {
                    'bleu': MetricResult('bleu', 0.68, MetricType.STANDARD_NLP),
                    'code_quality': MetricResult('code_quality', 0.75, MetricType.CODE_QUALITY),
                    'pass_at_1': MetricResult('pass_at_1', 0.70, MetricType.FUNCTIONAL)
                }
            }
        }
        
        comparison = self.analysis_engine.compare_model_performance(model_results)
        
        self.assertIsInstance(comparison, PerformanceComparison)
        self.assertGreater(len(comparison.model_rankings), 0)
        
        print(f"Model Rankings:")
        for ranking in comparison.model_rankings:
            print(f"\nMetric: {ranking['metric']}")
            for model_rank in ranking['rankings']:
                print(f"  {model_rank['rank']}. {model_rank['model']}: {model_rank['score']:.3f}")
        
        print(f"\nStatistical Tests:")
        for metric, test in comparison.statistical_tests.items():
            print(f"  {metric}: p-value={test.p_value:.4f}, significant={test.is_significant}")
        
        print(f"\nRecommendations:")
        for rec in comparison.recommendations:
            print(f"  - {rec}")
        
        self.assertGreater(len(comparison.recommendations), 0)
    
    def test_confidence_intervals(self):
        """Test confidence interval calculations."""
        print("\n=== Testing Confidence Intervals ===")
        
        # Test with sample data
        sample_values = [0.6, 0.65, 0.7, 0.68, 0.72, 0.69, 0.71, 0.67, 0.73, 0.66]
        
        intervals = self.analysis_engine.calculate_confidence_intervals(sample_values)
        
        self.assertIsInstance(intervals, dict)
        self.assertIn(0.95, intervals)
        
        ci_95 = intervals[0.95]
        print(f"95% Confidence Interval:")
        print(f"  Mean: {ci_95.mean:.3f}")
        print(f"  Lower Bound: {ci_95.lower_bound:.3f}")
        print(f"  Upper Bound: {ci_95.upper_bound:.3f}")
        print(f"  Margin of Error: {ci_95.margin_of_error:.3f}")
        print(f"  Sample Size: {ci_95.sample_size}")
        
        # Verify interval properties
        self.assertLess(ci_95.lower_bound, ci_95.mean)
        self.assertGreater(ci_95.upper_bound, ci_95.mean)
        self.assertEqual(ci_95.sample_size, len(sample_values))
        self.assertAlmostEqual(ci_95.mean, statistics.mean(sample_values), places=3)
    
    def test_pattern_recognition(self):
        """Test pattern recognition functionality."""
        print("\n=== Testing Pattern Recognition ===")
        
        # Test pattern recognition on metrics with trends
        patterns = self.analysis_engine.identify_performance_patterns('pass_at_1')
        
        self.assertIsInstance(patterns, list)
        
        if patterns:
            print(f"Patterns detected in pass_at_1:")
            for pattern in patterns:
                print(f"  Pattern: {pattern.pattern_type}")
                print(f"  Strength: {pattern.strength:.3f}")
                print(f"  Description: {pattern.description}")
                if pattern.frequency:
                    print(f"  Frequency: {pattern.frequency:.3f}")
                print()
        else:
            print("No patterns detected in pass_at_1")
        
        # Test with cyclical data
        self._add_cyclical_data()
        cyclical_patterns = self.analysis_engine.identify_performance_patterns('cyclical_metric')
        
        if cyclical_patterns:
            print(f"Cyclical patterns detected:")
            for pattern in cyclical_patterns:
                print(f"  Pattern: {pattern.pattern_type}")
                print(f"  Strength: {pattern.strength:.3f}")
                if pattern.frequency:
                    print(f"  Frequency: {pattern.frequency:.3f}")
    
    def _add_cyclical_data(self):
        """Add cyclical data for pattern testing."""
        import math
        
        base_time = time.time()
        for i in range(20):
            timestamp = base_time + i * 60  # 1 minute apart
            
            # Create cyclical pattern
            cyclical_value = 0.5 + 0.3 * math.sin(2 * math.pi * i / 8)  # Period of 8
            
            result = {
                'evaluation_id': f'cyclical_{i}',
                'timestamp': timestamp,
                'metrics': {
                    'cyclical_metric': MetricResult(
                        'cyclical_metric', cyclical_value, MetricType.CUSTOM
                    )
                }
            }
            
            self.analysis_engine.add_evaluation_result(result)
    
    def test_comprehensive_analysis(self):
        """Test comprehensive analysis generation."""
        print("\n=== Testing Comprehensive Analysis ===")
        
        analysis = self.analysis_engine.generate_comprehensive_analysis(self.sample_results)
        
        self.assertIsInstance(analysis, dict)
        
        # Check required sections
        required_sections = [
            'summary_statistics', 'trend_analysis', 'anomaly_detection',
            'pattern_recognition', 'performance_distribution', 'recommendations'
        ]
        
        for section in required_sections:
            self.assertIn(section, analysis)
        
        print("Analysis sections generated:")
        for section in required_sections:
            if analysis[section]:
                print(f"  ✓ {section}")
            else:
                print(f"  - {section} (empty)")
        
        # Check summary statistics
        summary_stats = analysis['summary_statistics']
        self.assertIn('bleu', summary_stats)
        
        bleu_stats = summary_stats['bleu']
        print(f"\nBLEU Statistics:")
        print(f"  Count: {bleu_stats['count']}")
        print(f"  Mean: {bleu_stats['mean']:.3f}")
        print(f"  Std Dev: {bleu_stats['std_dev']:.3f}")
        print(f"  Range: {bleu_stats['range']:.3f}")
        
        # Check trend analysis
        trend_analysis = analysis['trend_analysis']
        if 'pass_at_1' in trend_analysis:
            trend = trend_analysis['pass_at_1']
            print(f"\nPass@1 Trend:")
            print(f"  Type: {trend['trend_type']}")
            print(f"  Confidence: {trend['confidence']:.3f}")
            print(f"  Change Rate: {trend['change_rate']:.6f}")
        
        # Check anomaly detection
        anomaly_detection = analysis['anomaly_detection']
        print(f"\nAnomaly Detection:")
        print(f"  Total Anomalies: {anomaly_detection['total_anomalies']}")
        print(f"  Anomalies by Type: {dict(anomaly_detection['anomalies_by_type'])}")
        
        # Check recommendations
        recommendations = analysis['recommendations']
        print(f"\nRecommendations ({len(recommendations)}):")
        for i, rec in enumerate(recommendations[:5], 1):
            print(f"  {i}. {rec}")
        
        self.assertGreater(len(recommendations), 0)
    
    def test_integration_with_existing_tools(self):
        """Test integration with existing analysis tools."""
        print("\n=== Testing Integration with Existing Tools ===")
        
        # Test that analysis engine can work with existing metric results
        from evaluation_engine.core.metrics_engine import MetricsEngine
        
        metrics_engine = MetricsEngine()
        
        # Calculate some standard metrics
        predictions = ["def hello(): return 'world'", "def add(a, b): return a + b"]
        references = ["def hello(): return 'world'", "def add(x, y): return x + y"]
        
        standard_metrics = metrics_engine.calculate_standard_metrics(predictions, references)
        
        # Create evaluation result with these metrics
        evaluation_result = {
            'evaluation_id': 'integration_test',
            'timestamp': time.time(),
            'metrics': standard_metrics
        }
        
        # Add to analysis engine
        self.analysis_engine.add_evaluation_result(evaluation_result)
        
        # Verify it was added
        self.assertGreater(len(self.analysis_engine.evaluation_history), len(self.sample_results))
        
        # Test that we can analyze the integrated data
        for metric_name in standard_metrics.keys():
            if metric_name in self.analysis_engine.metric_history:
                history = self.analysis_engine.metric_history[metric_name]
                self.assertGreater(len(history), 0)
                print(f"  ✓ {metric_name}: {len(history)} data points")
        
        print("Integration with existing metrics successful")
    
    def test_real_time_capabilities(self):
        """Test real-time analysis capabilities."""
        print("\n=== Testing Real-time Capabilities ===")
        
        # Test adding results in real-time
        initial_count = len(self.analysis_engine.evaluation_history)
        
        # Add a new result
        new_result = {
            'evaluation_id': 'realtime_test',
            'timestamp': time.time(),
            'metrics': {
                'bleu': MetricResult('bleu', 0.85, MetricType.STANDARD_NLP),
                'code_quality': MetricResult('code_quality', 0.90, MetricType.CODE_QUALITY)
            }
        }
        
        self.analysis_engine.add_evaluation_result(new_result)
        
        # Verify it was added
        self.assertEqual(len(self.analysis_engine.evaluation_history), initial_count + 1)
        
        # Test that caches are cleared
        self.assertEqual(len(self.analysis_engine.trend_cache), 0)
        
        # Test immediate analysis
        recent_anomalies = self.analysis_engine.detect_anomalies(lookback_window=5)
        self.assertIsInstance(recent_anomalies, list)
        
        print(f"Real-time analysis completed:")
        print(f"  Total evaluations: {len(self.analysis_engine.evaluation_history)}")
        print(f"  Recent anomalies: {len(recent_anomalies)}")
        print(f"  Cache cleared: ✓")


def run_analysis_engine_tests():
    """Run all analysis engine tests."""
    print("🧪 Running Analysis Engine Tests")
    print("=" * 50)
    
    # Create test suite
    test_suite = unittest.TestLoader().loadTestsFromTestCase(TestAnalysisEngine)
    
    # Run tests with detailed output
    runner = unittest.TextTestRunner(verbosity=2, stream=None)
    result = runner.run(test_suite)
    
    # Print summary
    print("\n" + "=" * 50)
    print("📊 Analysis Engine Test Summary")
    print("=" * 50)
    
    if result.wasSuccessful():
        print("✅ All tests passed!")
        print(f"   Tests run: {result.testsRun}")
        print(f"   Failures: {len(result.failures)}")
        print(f"   Errors: {len(result.errors)}")
    else:
        print("❌ Some tests failed!")
        print(f"   Tests run: {result.testsRun}")
        print(f"   Failures: {len(result.failures)}")
        print(f"   Errors: {len(result.errors)}")
        
        if result.failures:
            print("\nFailures:")
            for test, traceback in result.failures:
                print(f"  - {test}: {traceback}")
        
        if result.errors:
            print("\nErrors:")
            for test, traceback in result.errors:
                print(f"  - {test}: {traceback}")
    
    return result.wasSuccessful()


if __name__ == "__main__":
    success = run_analysis_engine_tests()
    exit(0 if success else 1)