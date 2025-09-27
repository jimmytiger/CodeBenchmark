#!/usr/bin/env python3
"""
Integration test for Analysis and Visualization Engines.

This test demonstrates the complete workflow of statistical analysis
and visualization capabilities working together.
"""

import unittest
import time
import json
import tempfile
import os
from typing import Dict, List, Any

from evaluation_engine.core.analysis_engine import AnalysisEngine
from evaluation_engine.core.visualization_engine import (
    VisualizationEngine, ChartType, ReportFormat, ChartConfig, 
    DashboardConfig, ReportConfig
)
from evaluation_engine.core.metrics_engine import MetricResult, MetricType


class TestAnalysisVisualizationIntegration(unittest.TestCase):
    """Integration tests for Analysis and Visualization Engines."""
    
    def setUp(self):
        """Set up test fixtures."""
        self.analysis_engine = AnalysisEngine()
        self.viz_engine = VisualizationEngine(self.analysis_engine)
        
        # Create comprehensive evaluation dataset
        self.evaluation_results = self._create_comprehensive_dataset()
        
        # Add results to analysis engine
        for result in self.evaluation_results:
            self.analysis_engine.add_evaluation_result(result)
    
    def _create_comprehensive_dataset(self) -> List[Dict[str, Any]]:
        """Create a comprehensive dataset for testing."""
        results = []
        base_time = time.time() - 7200  # 2 hours ago
        
        models = ['gpt-4', 'claude-3', 'gemini-pro', 'llama-2']
        scenarios = ['code_completion', 'bug_fix', 'algorithm_design', 'code_review']
        
        for i in range(40):
            model_name = models[i % len(models)]
            scenario = scenarios[i % len(scenarios)]
            timestamp = base_time + i * 180  # 3 minutes apart
            
            # Create realistic performance patterns
            base_performance = 0.5 + (i * 0.01)  # Gradual improvement over time
            
            # Model-specific performance characteristics
            model_modifiers = {
                'gpt-4': {'bleu': 0.15, 'code_quality': 0.12, 'pass_at_1': 0.18},
                'claude-3': {'bleu': 0.12, 'code_quality': 0.15, 'pass_at_1': 0.14},
                'gemini-pro': {'bleu': 0.10, 'code_quality': 0.08, 'pass_at_1': 0.12},
                'llama-2': {'bleu': 0.08, 'code_quality': 0.10, 'pass_at_1': 0.09}
            }
            
            # Scenario-specific difficulty
            scenario_difficulty = {
                'code_completion': 0.0,
                'bug_fix': -0.05,
                'algorithm_design': -0.10,
                'code_review': -0.03
            }
            
            # Add some noise and occasional anomalies
            noise = (i % 7) * 0.005 - 0.015  # Cyclical noise
            anomaly_factor = 1.0
            
            # Create anomalies at specific points
            if i in [10, 25, 35]:  # Specific anomaly points
                anomaly_factor = 0.6 if i == 10 else 1.4  # Drop then spike
            
            modifier = model_modifiers[model_name]
            difficulty = scenario_difficulty[scenario]
            
            metrics = {
                'bleu': MetricResult(
                    name='bleu',
                    value=max(0.0, min(1.0, (base_performance + modifier['bleu'] + difficulty + noise) * anomaly_factor)),
                    metric_type=MetricType.STANDARD_NLP
                ),
                'code_quality': MetricResult(
                    name='code_quality',
                    value=max(0.0, min(1.0, (base_performance + modifier['code_quality'] + difficulty + noise * 0.8) * anomaly_factor)),
                    metric_type=MetricType.CODE_QUALITY
                ),
                'pass_at_1': MetricResult(
                    name='pass_at_1',
                    value=max(0.0, min(1.0, (base_performance + modifier['pass_at_1'] + difficulty + noise * 1.2) * anomaly_factor)),
                    metric_type=MetricType.FUNCTIONAL
                ),
                'execution_time': MetricResult(
                    name='execution_time',
                    value=max(0.1, 2.0 - (base_performance * 1.5) + (noise * 0.5)),  # Faster execution over time
                    metric_type=MetricType.CUSTOM
                )
            }
            
            results.append({
                'evaluation_id': f'eval_{i:03d}',
                'model_name': model_name,
                'scenario': scenario,
                'timestamp': timestamp,
                'metrics': metrics,
                'metadata': {
                    'dataset_size': 100 + (i % 50),
                    'temperature': 0.7 + (i % 3) * 0.1,
                    'max_tokens': 1000 + (i % 5) * 200
                }
            })
        
        return results
    
    def test_comprehensive_analysis_and_visualization(self):
        """Test comprehensive analysis with visualization."""
        print("\n=== Comprehensive Analysis and Visualization Test ===")
        
        # Generate comprehensive analysis
        analysis = self.analysis_engine.generate_comprehensive_analysis(self.evaluation_results)
        
        # Verify analysis components
        self.assertIn('summary_statistics', analysis)
        self.assertIn('trend_analysis', analysis)
        self.assertIn('anomaly_detection', analysis)
        self.assertIn('recommendations', analysis)
        
        print(f"Analysis completed:")
        print(f"  Metrics analyzed: {len(analysis['summary_statistics'])}")
        print(f"  Trends identified: {len(analysis['trend_analysis'])}")
        print(f"  Anomalies detected: {analysis['anomaly_detection']['total_anomalies']}")
        print(f"  Recommendations: {len(analysis['recommendations'])}")
        
        # Create comprehensive dashboard
        dashboard_config = DashboardConfig(
            title="Comprehensive AI Evaluation Dashboard",
            layout="grid",
            auto_refresh=False,
            theme="light"
        )
        
        dashboard = self.viz_engine.create_performance_dashboard(
            self.evaluation_results, dashboard_config
        )
        
        # Verify dashboard components
        self.assertIn('charts', dashboard)
        self.assertIn('metrics_summary', dashboard)
        self.assertIn('anomalies', dashboard)
        
        print(f"\nDashboard created:")
        print(f"  Charts generated: {len(dashboard['charts'])}")
        print(f"  Metrics summarized: {len(dashboard['metrics_summary'])}")
        print(f"  Anomalies visualized: {len(dashboard['anomalies'])}")
        
        # Generate comprehensive report
        report_config = ReportConfig(
            title="AI Model Evaluation Report",
            format=ReportFormat.HTML,
            include_charts=True,
            include_analysis=True,
            include_recommendations=True
        )
        
        report = self.viz_engine.generate_report(
            self.evaluation_results, report_config, analysis
        )
        
        # Verify report
        self.assertEqual(report['format'], 'html')
        self.assertIn('content', report)
        self.assertGreater(len(report['content']), 1000)  # Substantial content
        
        print(f"\nComprehensive report generated:")
        print(f"  Format: {report['format']}")
        print(f"  Content length: {len(report['content'])} characters")
        print(f"  Charts included: {len(report.get('charts', []))}")
        print(f"  Analysis sections: {len(report.get('analysis', {}))}")
    
    def test_model_performance_comparison_workflow(self):
        """Test complete model performance comparison workflow."""
        print("\n=== Model Performance Comparison Workflow ===")
        
        # Group results by model
        model_results = {}
        for result in self.evaluation_results:
            model_name = result['model_name']
            if model_name not in model_results:
                model_results[model_name] = {'metrics': {}, 'evaluations': []}
            
            model_results[model_name]['evaluations'].append(result)
        
        # Calculate average metrics for each model
        for model_name, data in model_results.items():
            evaluations = data['evaluations']
            avg_metrics = {}
            
            # Get all metric names
            all_metric_names = set()
            for eval_result in evaluations:
                all_metric_names.update(eval_result['metrics'].keys())
            
            # Calculate averages
            for metric_name in all_metric_names:
                values = []
                for eval_result in evaluations:
                    if metric_name in eval_result['metrics']:
                        metric_result = eval_result['metrics'][metric_name]
                        value = metric_result.value if hasattr(metric_result, 'value') else metric_result
                        values.append(value)
                
                if values:
                    avg_value = sum(values) / len(values)
                    avg_metrics[metric_name] = MetricResult(
                        name=metric_name,
                        value=avg_value,
                        metric_type=MetricType.COMPOSITE
                    )
            
            model_results[model_name]['metrics'] = avg_metrics
        
        # Perform statistical comparison
        comparison = self.analysis_engine.compare_model_performance(model_results)
        
        print(f"Statistical comparison completed:")
        print(f"  Models compared: {len(model_results)}")
        print(f"  Metrics compared: {len(comparison.model_rankings)}")
        print(f"  Statistical tests: {len(comparison.statistical_tests)}")
        
        # Show rankings
        for ranking in comparison.model_rankings:
            print(f"\n  {ranking['metric']} Rankings:")
            for model_rank in ranking['rankings'][:3]:  # Top 3
                print(f"    {model_rank['rank']}. {model_rank['model']}: {model_rank['score']:.3f}")
        
        # Create comparison visualization
        comparison_viz = self.viz_engine.create_model_comparison_visualization(model_results)
        
        self.assertEqual(comparison_viz['type'], 'model_comparison')
        self.assertIn('charts', comparison_viz)
        
        print(f"\nComparison visualization created:")
        print(f"  Comparison charts: {len(comparison_viz['charts'])}")
        
        # Create leaderboard
        leaderboard = self.viz_engine.create_leaderboard(
            self.evaluation_results,
            ranking_metric='bleu',
            top_n=10
        )
        
        print(f"\nLeaderboard created:")
        print(f"  Top entries: {len(leaderboard['rankings'])}")
        
        for i, ranking in enumerate(leaderboard['rankings'][:5], 1):
            print(f"    {i}. {ranking['model_name']}: {ranking['score']:.3f}")
    
    def test_trend_analysis_with_visualization(self):
        """Test trend analysis with corresponding visualizations."""
        print("\n=== Trend Analysis with Visualization ===")
        
        # Analyze trends for each metric
        metrics_to_analyze = ['bleu', 'code_quality', 'pass_at_1', 'execution_time']
        trend_results = {}
        
        for metric_name in metrics_to_analyze:
            trend = self.analysis_engine.perform_trend_analysis(metric_name)
            if trend:
                trend_results[metric_name] = trend
                
                print(f"\n{metric_name} Trend Analysis:")
                print(f"  Type: {trend.trend_type.value}")
                print(f"  Confidence: {trend.confidence:.3f}")
                print(f"  Slope: {trend.slope:.6f}")
                print(f"  R-squared: {trend.r_squared:.3f}")
                print(f"  Change rate: {trend.change_rate:.6f}")
        
        # Create trend visualizations
        for metric_name in trend_results.keys():
            # Extract time series data
            metric_history = self.analysis_engine.metric_history[metric_name]
            timestamps = [t for t, v in metric_history]
            values = [v for t, v in metric_history]
            
            # Create line chart
            chart_config = ChartConfig(
                chart_type=ChartType.LINE_CHART,
                title=f"{metric_name} Trend Analysis",
                x_axis_label="Time",
                y_axis_label=metric_name,
                height=400
            )
            
            chart = self.viz_engine.create_line_chart(
                {metric_name: values},
                chart_config,
                timestamps
            )
            
            self.assertEqual(chart['type'], 'line_chart')
            print(f"  Trend chart created for {metric_name}")
        
        print(f"\nTrend analysis completed for {len(trend_results)} metrics")
    
    def test_anomaly_detection_with_visualization(self):
        """Test anomaly detection with visualization."""
        print("\n=== Anomaly Detection with Visualization ===")
        
        # Detect anomalies
        anomalies = self.analysis_engine.detect_anomalies()
        
        print(f"Anomaly detection completed:")
        print(f"  Total anomalies: {len(anomalies)}")
        
        # Group anomalies by type
        anomaly_types = {}
        for anomaly in anomalies:
            anomaly_type = anomaly.anomaly_type.value
            if anomaly_type not in anomaly_types:
                anomaly_types[anomaly_type] = []
            anomaly_types[anomaly_type].append(anomaly)
        
        print(f"  Anomaly types detected: {list(anomaly_types.keys())}")
        
        for anomaly_type, type_anomalies in anomaly_types.items():
            print(f"    {anomaly_type}: {len(type_anomalies)} instances")
            
            # Show example
            if type_anomalies:
                example = type_anomalies[0]
                print(f"      Example: {example.description}")
        
        # Create anomaly visualization
        if anomalies:
            # Create scatter plot showing anomalies
            all_values = []
            all_timestamps = []
            anomaly_points = []
            
            for metric_name in ['bleu', 'code_quality', 'pass_at_1']:
                if metric_name in self.analysis_engine.metric_history:
                    history = self.analysis_engine.metric_history[metric_name]
                    for timestamp, value in history:
                        all_values.append(value)
                        all_timestamps.append(timestamp)
                        
                        # Check if this point is an anomaly
                        is_anomaly = any(
                            a.timestamp and abs(a.timestamp - timestamp) < 60  # Within 1 minute
                            for a in anomalies
                            if metric_name in a.affected_metrics
                        )
                        anomaly_points.append(is_anomaly)
            
            if all_values and all_timestamps:
                chart_config = ChartConfig(
                    chart_type=ChartType.SCATTER_PLOT,
                    title="Anomaly Detection Visualization",
                    x_axis_label="Time",
                    y_axis_label="Metric Value",
                    height=500
                )
                
                colors = ['red' if is_anomaly else 'blue' for is_anomaly in anomaly_points]
                
                chart = self.viz_engine.create_scatter_plot(
                    all_timestamps, all_values, chart_config, colors=colors
                )
                
                self.assertEqual(chart['type'], 'scatter_plot')
                print(f"  Anomaly visualization created with {len(all_values)} data points")
    
    def test_pattern_recognition_workflow(self):
        """Test pattern recognition workflow."""
        print("\n=== Pattern Recognition Workflow ===")
        
        # Identify patterns in different metrics
        metrics_to_analyze = ['bleu', 'code_quality', 'pass_at_1']
        pattern_results = {}
        
        for metric_name in metrics_to_analyze:
            patterns = self.analysis_engine.identify_performance_patterns(metric_name)
            if patterns:
                pattern_results[metric_name] = patterns
                
                print(f"\n{metric_name} Patterns:")
                for pattern in patterns:
                    print(f"  {pattern.pattern_type}: strength={pattern.strength:.3f}")
                    if pattern.frequency:
                        print(f"    Frequency: {pattern.frequency:.3f}")
                    print(f"    Description: {pattern.description}")
        
        print(f"\nPattern recognition completed for {len(pattern_results)} metrics")
        
        # Create pattern visualization (simplified)
        for metric_name, patterns in pattern_results.items():
            if patterns:
                # Create a simple representation
                pattern_data = {
                    pattern.pattern_type: pattern.strength
                    for pattern in patterns
                }
                
                chart_config = ChartConfig(
                    chart_type=ChartType.BAR_CHART,
                    title=f"{metric_name} Pattern Strengths",
                    x_axis_label="Pattern Type",
                    y_axis_label="Strength",
                    height=300
                )
                
                chart = self.viz_engine.create_bar_chart(pattern_data, chart_config)
                self.assertEqual(chart['type'], 'bar_chart')
                print(f"  Pattern chart created for {metric_name}")
    
    def test_export_and_sharing_workflow(self):
        """Test export and sharing workflow."""
        print("\n=== Export and Sharing Workflow ===")
        
        # Generate analysis
        analysis = self.analysis_engine.generate_comprehensive_analysis(self.evaluation_results)
        
        # Create multiple report formats
        formats_to_test = [
            (ReportFormat.HTML, 'html'),
            (ReportFormat.JSON, 'json'),
            (ReportFormat.CSV, 'csv'),
            (ReportFormat.MARKDOWN, 'md')
        ]
        
        exported_reports = {}
        
        for report_format, extension in formats_to_test:
            config = ReportConfig(
                title="AI Evaluation Export Test",
                format=report_format,
                include_charts=True,
                include_analysis=True,
                include_recommendations=True
            )
            
            report = self.viz_engine.generate_report(
                self.evaluation_results, config, analysis
            )
            
            # Export to temporary file
            with tempfile.NamedTemporaryFile(
                mode='w', suffix=f'.{extension}', delete=False
            ) as tmp_file:
                tmp_file.write(report['content'])
                exported_reports[report_format.value] = tmp_file.name
            
            print(f"  {report_format.value.upper()} report exported: {os.path.basename(tmp_file.name)}")
        
        # Verify exports
        for format_name, filepath in exported_reports.items():
            self.assertTrue(os.path.exists(filepath))
            
            with open(filepath, 'r') as f:
                content = f.read()
                self.assertGreater(len(content), 100)  # Should have substantial content
            
            # Cleanup
            os.unlink(filepath)
        
        # Test chart exports
        data = {'Metric A': [0.6, 0.7, 0.8], 'Metric B': [0.5, 0.6, 0.7]}
        config = ChartConfig(ChartType.LINE_CHART, "Test Export Chart")
        chart = self.viz_engine.create_line_chart(data, config)
        
        # Export chart as JSON
        chart_export = self.viz_engine.export_chart(chart, 'json')
        self.assertTrue(chart_export['success'])
        
        print(f"  Chart export successful: {chart_export['format']}")
        print(f"\nExport and sharing workflow completed successfully")


def run_integration_tests():
    """Run all integration tests."""
    print("🔗 Running Analysis and Visualization Integration Tests")
    print("=" * 60)
    
    # Create test suite
    test_suite = unittest.TestLoader().loadTestsFromTestCase(TestAnalysisVisualizationIntegration)
    
    # Run tests with detailed output
    runner = unittest.TextTestRunner(verbosity=2, stream=None)
    result = runner.run(test_suite)
    
    # Print summary
    print("\n" + "=" * 60)
    print("📊 Integration Test Summary")
    print("=" * 60)
    
    if result.wasSuccessful():
        print("✅ All integration tests passed!")
        print(f"   Tests run: {result.testsRun}")
        print(f"   Failures: {len(result.failures)}")
        print(f"   Errors: {len(result.errors)}")
        
        print("\n🎉 Analysis and Visualization Engines are fully integrated!")
        print("   ✓ Statistical analysis capabilities")
        print("   ✓ Trend identification and anomaly detection")
        print("   ✓ Cross-model performance comparison")
        print("   ✓ Interactive charts and dashboards")
        print("   ✓ Multi-format report generation")
        print("   ✓ Pattern recognition and visualization")
        print("   ✓ Export and sharing capabilities")
        
    else:
        print("❌ Some integration tests failed!")
        print(f"   Tests run: {result.testsRun}")
        print(f"   Failures: {len(result.failures)}")
        print(f"   Errors: {len(result.errors)}")
        
        if result.failures:
            print("\nFailures:")
            for test, traceback in result.failures:
                print(f"  - {test}")
        
        if result.errors:
            print("\nErrors:")
            for test, traceback in result.errors:
                print(f"  - {test}")
    
    return result.wasSuccessful()


if __name__ == "__main__":
    success = run_integration_tests()
    exit(0 if success else 1)