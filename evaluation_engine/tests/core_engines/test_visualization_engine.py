#!/usr/bin/env python3
"""
Test suite for VisualizationEngine implementation.

Tests interactive charts, performance dashboards, comparative visualizations,
and exportable reports in multiple formats.
"""

import unittest
import time
import json
import tempfile
import os
from typing import Dict, List, Any

from evaluation_engine.core.visualization_engine import (
    VisualizationEngine, ChartType, ReportFormat, ChartConfig, 
    DashboardConfig, ReportConfig
)
from evaluation_engine.core.analysis_engine import AnalysisEngine
from evaluation_engine.core.metrics_engine import MetricResult, MetricType


class TestVisualizationEngine(unittest.TestCase):
    """Test cases for VisualizationEngine."""
    
    def setUp(self):
        """Set up test fixtures."""
        self.analysis_engine = AnalysisEngine()
        self.viz_engine = VisualizationEngine(self.analysis_engine)
        
        # Create sample evaluation results
        self.sample_results = self._create_sample_evaluation_results()
        
        # Add results to analysis engine
        for result in self.sample_results:
            self.analysis_engine.add_evaluation_result(result)
    
    def _create_sample_evaluation_results(self) -> List[Dict[str, Any]]:
        """Create sample evaluation results for testing."""
        results = []
        base_time = time.time() - 3600  # 1 hour ago
        
        models = ['model_a', 'model_b', 'model_c']
        
        for i in range(15):
            model_name = models[i % len(models)]
            timestamp = base_time + i * 240  # 4 minutes apart
            
            # Create varying performance data
            base_performance = 0.6 + (i * 0.02)  # Gradual improvement
            model_modifier = {'model_a': 0.05, 'model_b': -0.02, 'model_c': 0.01}[model_name]
            
            metrics = {
                'bleu': MetricResult(
                    name='bleu',
                    value=base_performance + model_modifier + (i % 3) * 0.01,
                    metric_type=MetricType.STANDARD_NLP
                ),
                'code_quality': MetricResult(
                    name='code_quality',
                    value=base_performance + model_modifier * 0.8 + (i % 2) * 0.015,
                    metric_type=MetricType.CODE_QUALITY
                ),
                'pass_at_1': MetricResult(
                    name='pass_at_1',
                    value=base_performance + model_modifier * 1.2 + (i % 4) * 0.008,
                    metric_type=MetricType.FUNCTIONAL
                )
            }
            
            results.append({
                'evaluation_id': f'eval_{i}',
                'model_name': model_name,
                'timestamp': timestamp,
                'metrics': metrics
            })
        
        return results
    
    def test_line_chart_creation(self):
        """Test line chart creation functionality."""
        print("\n=== Testing Line Chart Creation ===")
        
        # Prepare data
        data = {
            'BLEU Score': [0.6, 0.65, 0.7, 0.68, 0.72, 0.69, 0.71],
            'Code Quality': [0.7, 0.72, 0.75, 0.73, 0.76, 0.74, 0.77]
        }
        
        timestamps = [time.time() - i * 300 for i in range(7, 0, -1)]
        
        config = ChartConfig(
            chart_type=ChartType.LINE_CHART,
            title="Performance Trends",
            x_axis_label="Time",
            y_axis_label="Score",
            height=500
        )
        
        chart = self.viz_engine.create_line_chart(data, config, timestamps)
        
        self.assertIsInstance(chart, dict)
        self.assertEqual(chart['type'], 'line_chart')
        self.assertIn('data', chart)
        self.assertIn('config', chart)
        self.assertIn('created_at', chart)
        
        # Should have ASCII fallback
        self.assertIn('ascii', chart)
        self.assertIsInstance(chart['ascii'], str)
        
        print(f"Chart created successfully:")
        print(f"  Type: {chart['type']}")
        print(f"  Data series: {list(data.keys())}")
        print(f"  Backends available: {[k for k in chart.keys() if k not in ['type', 'data', 'config', 'created_at', 'timestamps']]}")
        
        # Test ASCII output
        print(f"\nASCII Chart Preview:")
        print(chart['ascii'][:200] + "..." if len(chart['ascii']) > 200 else chart['ascii'])
    
    def test_bar_chart_creation(self):
        """Test bar chart creation functionality."""
        print("\n=== Testing Bar Chart Creation ===")
        
        # Prepare data
        data = {
            'Model A': 0.85,
            'Model B': 0.78,
            'Model C': 0.82,
            'Model D': 0.76
        }
        
        config = ChartConfig(
            chart_type=ChartType.BAR_CHART,
            title="Model Performance Comparison",
            x_axis_label="Models",
            y_axis_label="Score",
            height=400
        )
        
        chart = self.viz_engine.create_bar_chart(data, config)
        
        self.assertIsInstance(chart, dict)
        self.assertEqual(chart['type'], 'bar_chart')
        self.assertIn('data', chart)
        self.assertEqual(chart['data'], data)
        
        # Should have ASCII fallback
        self.assertIn('ascii', chart)
        
        print(f"Bar chart created successfully:")
        print(f"  Categories: {len(data)}")
        print(f"  Max value: {max(data.values()):.3f}")
        print(f"  Min value: {min(data.values()):.3f}")
        
        # Test ASCII output
        print(f"\nASCII Bar Chart:")
        print(chart['ascii'])
    
    def test_scatter_plot_creation(self):
        """Test scatter plot creation functionality."""
        print("\n=== Testing Scatter Plot Creation ===")
        
        # Prepare data
        x_data = [0.6, 0.65, 0.7, 0.68, 0.72, 0.69, 0.71, 0.75]
        y_data = [0.7, 0.72, 0.75, 0.73, 0.76, 0.74, 0.77, 0.78]
        labels = [f"Point {i+1}" for i in range(len(x_data))]
        
        config = ChartConfig(
            chart_type=ChartType.SCATTER_PLOT,
            title="BLEU vs Code Quality",
            x_axis_label="BLEU Score",
            y_axis_label="Code Quality Score",
            height=500
        )
        
        chart = self.viz_engine.create_scatter_plot(x_data, y_data, config, labels)
        
        self.assertIsInstance(chart, dict)
        self.assertEqual(chart['type'], 'scatter_plot')
        self.assertIn('x_data', chart)
        self.assertIn('y_data', chart)
        self.assertEqual(len(chart['x_data']), len(chart['y_data']))
        
        print(f"Scatter plot created successfully:")
        print(f"  Data points: {len(x_data)}")
        print(f"  X range: {min(x_data):.3f} - {max(x_data):.3f}")
        print(f"  Y range: {min(y_data):.3f} - {max(y_data):.3f}")
    
    def test_heatmap_creation(self):
        """Test heatmap creation functionality."""
        print("\n=== Testing Heatmap Creation ===")
        
        # Prepare data (correlation matrix)
        data = [
            [1.0, 0.8, 0.6],
            [0.8, 1.0, 0.7],
            [0.6, 0.7, 1.0]
        ]
        
        x_labels = ['BLEU', 'Code Quality', 'Pass@1']
        y_labels = ['BLEU', 'Code Quality', 'Pass@1']
        
        config = ChartConfig(
            chart_type=ChartType.HEATMAP,
            title="Metric Correlation Matrix",
            height=500
        )
        
        chart = self.viz_engine.create_heatmap(data, config, x_labels, y_labels)
        
        self.assertIsInstance(chart, dict)
        self.assertEqual(chart['type'], 'heatmap')
        self.assertIn('data', chart)
        self.assertEqual(len(chart['data']), 3)
        self.assertEqual(len(chart['data'][0]), 3)
        
        print(f"Heatmap created successfully:")
        print(f"  Matrix size: {len(data)}x{len(data[0])}")
        print(f"  X labels: {x_labels}")
        print(f"  Y labels: {y_labels}")
    
    def test_performance_dashboard_creation(self):
        """Test performance dashboard creation."""
        print("\n=== Testing Performance Dashboard Creation ===")
        
        config = DashboardConfig(
            title="AI Model Performance Dashboard",
            layout="grid",
            auto_refresh=False,
            theme="light"
        )
        
        dashboard = self.viz_engine.create_performance_dashboard(self.sample_results, config)
        
        self.assertIsInstance(dashboard, dict)
        self.assertEqual(dashboard['type'], 'performance_dashboard')
        self.assertIn('charts', dashboard)
        self.assertIn('metrics_summary', dashboard)
        self.assertIn('anomalies', dashboard)
        
        print(f"Dashboard created successfully:")
        print(f"  Charts generated: {len(dashboard['charts'])}")
        print(f"  Metrics summarized: {len(dashboard['metrics_summary'])}")
        print(f"  Anomalies detected: {len(dashboard['anomalies'])}")
        
        # Check metrics summary
        metrics_summary = dashboard['metrics_summary']
        for metric_name, stats in metrics_summary.items():
            print(f"  {metric_name}: mean={stats['mean']:.3f}, std={stats['std_dev']:.3f}")
        
        # Check charts
        for i, chart in enumerate(dashboard['charts'][:3]):  # Show first 3 charts
            chart_config = chart.get('config')
            if chart_config:
                title = chart_config.title if hasattr(chart_config, 'title') else 'Unknown'
                print(f"  Chart {i+1}: {title}")
    
    def test_model_comparison_visualization(self):
        """Test model comparison visualization."""
        print("\n=== Testing Model Comparison Visualization ===")
        
        # Create model results
        model_results = {}
        models = ['model_a', 'model_b', 'model_c']
        
        for model in models:
            model_metrics = {}
            for result in self.sample_results:
                if result['model_name'] == model:
                    model_metrics = result['metrics']
                    break
            
            model_results[model] = {'metrics': model_metrics}
        
        comparison = self.viz_engine.create_model_comparison_visualization(model_results)
        
        self.assertIsInstance(comparison, dict)
        self.assertEqual(comparison['type'], 'model_comparison')
        self.assertIn('charts', comparison)
        
        print(f"Model comparison created successfully:")
        print(f"  Models compared: {len(model_results)}")
        print(f"  Comparison charts: {len(comparison['charts'])}")
        
        # Check rankings if available
        if 'rankings' in comparison:
            print(f"  Rankings available: {len(comparison['rankings'])}")
        
        # Check statistical tests if available
        if 'statistical_tests' in comparison:
            print(f"  Statistical tests: {len(comparison['statistical_tests'])}")
            for metric, test in comparison['statistical_tests'].items():
                print(f"    {metric}: p-value={test['p_value']:.4f}, significant={test['is_significant']}")
    
    def test_leaderboard_creation(self):
        """Test leaderboard creation."""
        print("\n=== Testing Leaderboard Creation ===")
        
        leaderboard = self.viz_engine.create_leaderboard(
            self.sample_results,
            ranking_metric='bleu',
            top_n=5
        )
        
        self.assertIsInstance(leaderboard, dict)
        self.assertEqual(leaderboard['type'], 'leaderboard')
        self.assertIn('rankings', leaderboard)
        self.assertIn('chart', leaderboard)
        
        rankings = leaderboard['rankings']
        self.assertLessEqual(len(rankings), 5)  # Should respect top_n
        
        print(f"Leaderboard created successfully:")
        print(f"  Ranking metric: {leaderboard['ranking_metric']}")
        print(f"  Top entries: {len(rankings)}")
        
        print(f"\nTop 5 Rankings:")
        for ranking in rankings:
            print(f"  {ranking['rank']}. {ranking['model_name']}: {ranking['score']:.3f}")
        
        # Check if chart was created
        if leaderboard['chart'] and 'data' in leaderboard['chart']:
            print(f"  Chart data points: {len(leaderboard['chart']['data'])}")
    
    def test_report_generation(self):
        """Test report generation in multiple formats."""
        print("\n=== Testing Report Generation ===")
        
        # Generate analysis data
        analysis_data = self.analysis_engine.generate_comprehensive_analysis(self.sample_results)
        
        # Test HTML report
        html_config = ReportConfig(
            title="AI Evaluation Report",
            format=ReportFormat.HTML,
            include_charts=True,
            include_analysis=True,
            include_recommendations=True
        )
        
        html_report = self.viz_engine.generate_report(self.sample_results, html_config, analysis_data)
        
        self.assertIsInstance(html_report, dict)
        self.assertEqual(html_report['format'], 'html')
        self.assertIn('content', html_report)
        
        print(f"HTML Report generated:")
        print(f"  Format: {html_report['format']}")
        print(f"  Content length: {len(html_report['content'])} characters")
        print(f"  Charts included: {len(html_report.get('charts', []))}")
        
        # Test JSON report
        json_config = ReportConfig(
            title="AI Evaluation Report",
            format=ReportFormat.JSON,
            include_analysis=True
        )
        
        json_report = self.viz_engine.generate_report(self.sample_results, json_config, analysis_data)
        
        self.assertEqual(json_report['format'], 'json')
        
        # Verify JSON content is valid
        json_content = json_report['content']
        parsed_json = json.loads(json_content)
        self.assertIn('title', parsed_json)
        self.assertIn('total_evaluations', parsed_json)
        
        print(f"JSON Report generated:")
        print(f"  Total evaluations: {parsed_json['total_evaluations']}")
        print(f"  Analysis included: {'analysis' in parsed_json}")
        
        # Test CSV report
        csv_config = ReportConfig(
            title="AI Evaluation Report",
            format=ReportFormat.CSV
        )
        
        csv_report = self.viz_engine.generate_report(self.sample_results, csv_config)
        
        self.assertEqual(csv_report['format'], 'csv')
        
        csv_content = csv_report['content']
        csv_lines = csv_content.strip().split('\n')
        
        print(f"CSV Report generated:")
        print(f"  Lines: {len(csv_lines)}")
        print(f"  Header: {csv_lines[0] if csv_lines else 'None'}")
        
        # Test Markdown report
        md_config = ReportConfig(
            title="AI Evaluation Report",
            format=ReportFormat.MARKDOWN,
            include_recommendations=True
        )
        
        md_report = self.viz_engine.generate_report(self.sample_results, md_config, analysis_data)
        
        self.assertEqual(md_report['format'], 'markdown')
        
        print(f"Markdown Report generated:")
        print(f"  Content length: {len(md_report['content'])} characters")
        print(f"  Recommendations: {len(md_report.get('recommendations', []))}")
    
    def test_chart_export(self):
        """Test chart export functionality."""
        print("\n=== Testing Chart Export ===")
        
        # Create a simple chart
        data = {'Series A': [1, 2, 3, 4, 5], 'Series B': [2, 3, 4, 5, 6]}
        config = ChartConfig(
            chart_type=ChartType.LINE_CHART,
            title="Test Chart",
            x_axis_label="X",
            y_axis_label="Y"
        )
        
        chart = self.viz_engine.create_line_chart(data, config)
        
        # Test JSON export
        json_export = self.viz_engine.export_chart(chart, 'json')
        
        self.assertIsInstance(json_export, dict)
        self.assertEqual(json_export['format'], 'json')
        
        if json_export['success']:
            print(f"JSON export successful:")
            print(f"  Format: {json_export['format']}")
            print(f"  Data length: {len(json_export.get('data', ''))}")
            
            # Verify JSON is valid
            json_data = json.loads(json_export['data'])
            self.assertIn('chart_type', json_data)
            self.assertIn('data', json_data)
        else:
            print(f"JSON export failed: {json_export.get('error', 'Unknown error')}")
        
        # Test file export (with temporary file)
        with tempfile.NamedTemporaryFile(suffix='.json', delete=False) as tmp_file:
            file_export = self.viz_engine.export_chart(chart, 'json', tmp_file.name)
            
            if file_export['success']:
                print(f"File export successful:")
                print(f"  Filename: {file_export['filename']}")
                
                # Verify file exists and has content
                self.assertTrue(os.path.exists(tmp_file.name))
                
                with open(tmp_file.name, 'r') as f:
                    file_content = f.read()
                    self.assertGreater(len(file_content), 0)
                    
                    # Verify it's valid JSON
                    json.loads(file_content)
                
                # Cleanup
                os.unlink(tmp_file.name)
            else:
                print(f"File export failed: {file_export.get('error', 'Unknown error')}")
    
    def test_backend_availability(self):
        """Test visualization backend availability."""
        print("\n=== Testing Backend Availability ===")
        
        backends = self.viz_engine.backends
        
        print(f"Available backends:")
        for backend, available in backends.items():
            status = "✓" if available else "✗"
            print(f"  {status} {backend}")
        
        # Test that at least ASCII fallback works
        data = {'Test': [1, 2, 3]}
        config = ChartConfig(ChartType.LINE_CHART, "Test Chart")
        
        chart = self.viz_engine.create_line_chart(data, config)
        self.assertIn('ascii', chart)
        self.assertIsInstance(chart['ascii'], str)
        
        print(f"\nASCII fallback working: ✓")
    
    def test_integration_with_analysis_engine(self):
        """Test integration with analysis engine."""
        print("\n=== Testing Integration with Analysis Engine ===")
        
        # Create dashboard with analysis engine
        config = DashboardConfig(
            title="Integrated Dashboard",
            auto_refresh=False
        )
        
        dashboard = self.viz_engine.create_performance_dashboard(self.sample_results, config)
        
        # Should have anomalies from analysis engine
        self.assertIn('anomalies', dashboard)
        anomalies = dashboard['anomalies']
        
        print(f"Integration successful:")
        print(f"  Anomalies detected: {len(anomalies)}")
        
        for anomaly in anomalies[:3]:  # Show first 3
            print(f"    {anomaly['type']}: {anomaly['description']}")
        
        # Test model comparison with statistical analysis
        model_results = {}
        for model in ['model_a', 'model_b', 'model_c']:
            model_metrics = {}
            for result in self.sample_results:
                if result['model_name'] == model:
                    model_metrics = result['metrics']
                    break
            model_results[model] = {'metrics': model_metrics}
        
        comparison = self.viz_engine.create_model_comparison_visualization(model_results)
        
        # Should have statistical tests from analysis engine
        if 'statistical_tests' in comparison:
            print(f"  Statistical tests: {len(comparison['statistical_tests'])}")
        
        print("Integration with analysis engine: ✓")


def run_visualization_engine_tests():
    """Run all visualization engine tests."""
    print("🎨 Running Visualization Engine Tests")
    print("=" * 50)
    
    # Create test suite
    test_suite = unittest.TestLoader().loadTestsFromTestCase(TestVisualizationEngine)
    
    # Run tests with detailed output
    runner = unittest.TextTestRunner(verbosity=2, stream=None)
    result = runner.run(test_suite)
    
    # Print summary
    print("\n" + "=" * 50)
    print("📊 Visualization Engine Test Summary")
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
    success = run_visualization_engine_tests()
    exit(0 if success else 1)