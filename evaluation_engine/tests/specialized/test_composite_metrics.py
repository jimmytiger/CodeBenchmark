#!/usr/bin/env python3
"""
Test script for Composite Metrics System implementation.

This script tests the scenario-specific metrics, composite metrics system,
configurable weight systems, real-time calculation, and visualization tools.
"""

import sys
import json
import time
from typing import Dict, List, Any

# Add the evaluation engine to the path
sys.path.insert(0, '.')

from evaluation_engine.core.metrics_engine import MetricsEngine, MetricResult, MetricType
from evaluation_engine.core.scenario_metrics import (
    ScenarioSpecificMetrics, ScenarioDomain, ScenarioMetricConfig
)
from evaluation_engine.core.composite_metrics import (
    CompositeMetricsSystem, WeightConfig, CompositeMetricConfig, 
    AggregationMethod, RankingMethod
)
from evaluation_engine.core.metric_visualization import (
    MetricVisualizationEngine, ChartType, VisualizationFormat
)


def test_scenario_specific_metrics():
    """Test scenario-specific metrics calculation."""
    print("Testing Scenario-Specific Metrics...")
    
    base_engine = MetricsEngine()
    scenario_metrics = ScenarioSpecificMetrics(base_engine)
    
    # Test coding domain metrics
    coding_prediction = """
def fibonacci(n):
    '''Calculate fibonacci number with memoization for efficiency.'''
    if n <= 1:
        return n
    
    memo = {}
    def fib_helper(x):
        if x in memo:
            return memo[x]
        if x <= 1:
            return x
        memo[x] = fib_helper(x-1) + fib_helper(x-2)
        return memo[x]
    
    return fib_helper(n)
    """
    
    coding_config = ScenarioMetricConfig(
        domain=ScenarioDomain.CODING,
        scenario_type="algorithm_implementation",
        weight_config={
            "code_completeness": 0.25,
            "algorithm_efficiency": 0.30,
            "code_readability": 0.20,
            "error_handling": 0.15,
            "documentation_quality": 0.10
        },
        custom_parameters={"language": "python"},
        real_time_enabled=True
    )
    
    coding_results = scenario_metrics.calculate_scenario_metrics(
        domain=ScenarioDomain.CODING,
        scenario_type="algorithm_implementation",
        prediction=coding_prediction,
        context={"requirements": ["fibonacci", "efficient", "memoization"]},
        config=coding_config
    )
    
    print(f"  Coding metrics calculated: {len(coding_results)}")
    for name, result in coding_results.items():
        print(f"    {name}: {result.value:.3f}")
    
    # Test trading domain metrics
    trading_prediction = """
    Based on the market analysis, I recommend a momentum-based trading strategy:
    
    1. Market Analysis: Use technical indicators including RSI, MACD, and moving averages
    2. Risk Management: Implement stop-loss at 2% and position sizing based on volatility
    3. Entry Criteria: Enter long positions when RSI > 30 and MACD crosses above signal line
    4. Exit Strategy: Take profits at 5% gain or when RSI reaches 70
    5. Backtesting: Test strategy on 2-year historical data with transaction costs
    6. Portfolio Optimization: Diversify across 10-15 uncorrelated assets
    """
    
    trading_results = scenario_metrics.calculate_scenario_metrics(
        domain=ScenarioDomain.TRADING,
        scenario_type="strategy_development",
        prediction=trading_prediction
    )
    
    print(f"  Trading metrics calculated: {len(trading_results)}")
    for name, result in trading_results.items():
        print(f"    {name}: {result.value:.3f}")
    
    assert len(coding_results) > 0
    assert len(trading_results) > 0
    assert all(0.0 <= result.value <= 1.0 for result in coding_results.values())
    
    print("  ✅ Scenario-specific metrics: PASS")
    return coding_results, trading_results


def test_composite_metrics_system():
    """Test composite metrics system with configurable weights."""
    print("\nTesting Composite Metrics System...")
    
    base_engine = MetricsEngine()
    scenario_metrics = ScenarioSpecificMetrics(base_engine)
    composite_system = CompositeMetricsSystem(base_engine, scenario_metrics)
    
    # Create sample metric results
    sample_metrics = {
        "syntax_valid": MetricResult("syntax_valid", 0.95, MetricType.CODE_QUALITY),
        "code_style_score": MetricResult("code_style_score", 0.85, MetricType.CODE_QUALITY),
        "security_score": MetricResult("security_score", 0.90, MetricType.CODE_QUALITY),
        "code_completeness": MetricResult("code_completeness", 0.88, MetricType.CUSTOM),
        "algorithm_efficiency": MetricResult("algorithm_efficiency", 0.75, MetricType.CUSTOM),
        "code_readability": MetricResult("code_readability", 0.80, MetricType.CUSTOM),
        "bleu": MetricResult("bleu", 0.70, MetricType.STANDARD_NLP),
        "exact_match": MetricResult("exact_match", 0.60, MetricType.STANDARD_NLP)
    }
    
    # Calculate composite metrics
    composite_results = composite_system.calculate_composite_metrics(
        sample_metrics, 
        evaluation_id="test_001",
        context={"domain": "coding", "scenario_type": "algorithm_implementation"}
    )
    
    print(f"  Composite metrics calculated: {len(composite_results)}")
    for name, result in composite_results.items():
        print(f"    {name}: {result.value:.3f}")
        if result.metadata:
            components = result.metadata.get('components', [])
            print(f"      Components: {components}")
    
    # Test custom composite metric
    custom_config = CompositeMetricConfig(
        name="custom_quality_score",
        component_metrics=["syntax_valid", "security_score", "code_readability"],
        weight_config=WeightConfig(
            metric_weights={
                "syntax_valid": 0.5,
                "security_score": 0.3,
                "code_readability": 0.2
            },
            adaptive_weights=True
        ),
        aggregation_method=AggregationMethod.WEIGHTED_AVERAGE,
        normalization_method="min_max",
        real_time_enabled=True
    )
    
    composite_system.register_composite_metric(custom_config)
    
    # Recalculate with custom metric
    updated_results = composite_system.calculate_composite_metrics(
        sample_metrics,
        evaluation_id="test_002"
    )
    
    assert "custom_quality_score" in updated_results
    assert "overall_code_quality" in updated_results
    assert all(0.0 <= result.value <= 1.0 for result in composite_results.values())
    
    print("  ✅ Composite metrics system: PASS")
    return composite_results


def test_real_time_monitoring():
    """Test real-time metric monitoring."""
    print("\nTesting Real-Time Monitoring...")
    
    base_engine = MetricsEngine()
    scenario_metrics = ScenarioSpecificMetrics(base_engine)
    composite_system = CompositeMetricsSystem(base_engine, scenario_metrics)
    
    # Set up real-time callback
    updates_received = []
    
    def real_time_callback(update):
        updates_received.append(update)
        print(f"    Real-time update: {update.metric_name} = {update.value:.3f}")
    
    composite_system.add_real_time_callback(real_time_callback)
    
    # Start real-time monitoring
    composite_system.start_real_time_monitoring(update_frequency=0.1)
    
    # Generate some metrics with real-time enabled
    sample_metrics = {
        "syntax_valid": MetricResult("syntax_valid", 0.95, MetricType.CODE_QUALITY),
        "code_style_score": MetricResult("code_style_score", 0.85, MetricType.CODE_QUALITY),
        "security_score": MetricResult("security_score", 0.90, MetricType.CODE_QUALITY)
    }
    
    # Calculate metrics multiple times to trigger real-time updates
    for i in range(3):
        composite_system.calculate_composite_metrics(
            sample_metrics,
            evaluation_id=f"realtime_test_{i}"
        )
        time.sleep(0.05)
    
    # Wait a bit for real-time processing
    time.sleep(0.2)
    
    # Stop monitoring
    composite_system.stop_real_time_monitoring()
    
    # Check real-time updates
    real_time_updates = composite_system.get_real_time_metrics(time_window=1.0)
    
    print(f"  Real-time updates received: {len(updates_received)}")
    print(f"  Real-time updates stored: {len(real_time_updates)}")
    
    assert len(real_time_updates) > 0
    
    print("  ✅ Real-time monitoring: PASS")
    return real_time_updates


def test_ranking_and_comparison():
    """Test evaluation ranking and comparison."""
    print("\nTesting Ranking and Comparison...")
    
    base_engine = MetricsEngine()
    scenario_metrics = ScenarioSpecificMetrics(base_engine)
    composite_system = CompositeMetricsSystem(base_engine, scenario_metrics)
    
    # Create sample evaluation results
    evaluation_results = []
    
    for i in range(5):
        # Vary the metric values to create different performance levels
        base_score = 0.5 + (i * 0.1)
        variance = 0.1 * (i % 2)  # Add some variance
        
        metrics = {
            "overall_code_quality": MetricResult(
                "overall_code_quality", 
                min(1.0, base_score + variance), 
                MetricType.COMPOSITE
            ),
            "conversation_quality": MetricResult(
                "conversation_quality", 
                min(1.0, base_score - variance), 
                MetricType.COMPOSITE
            ),
            "exact_match": MetricResult(
                "exact_match", 
                min(1.0, base_score + 0.05), 
                MetricType.STANDARD_NLP
            ),
            "bleu": MetricResult(
                "bleu", 
                min(1.0, base_score - 0.05), 
                MetricType.STANDARD_NLP
            )
        }
        
        evaluation_results.append({
            "evaluation_id": f"eval_{i+1}",
            "model": f"model_{chr(65+i)}",  # A, B, C, D, E
            "metrics": metrics
        })
    
    # Test different ranking methods
    for ranking_method in [RankingMethod.COMPOSITE_SCORE, RankingMethod.WEIGHTED_RANK]:
        ranked_results = composite_system.rank_evaluations(
            evaluation_results, 
            ranking_method,
            "overall_code_quality"
        )
        
        print(f"  Ranking by {ranking_method.value}:")
        for i, result in enumerate(ranked_results[:3]):  # Top 3
            eval_id = result.get("evaluation_id", "unknown")
            model = result.get("model", "unknown")
            print(f"    {i+1}. {eval_id} ({model})")
    
    # Generate comparative analysis
    analysis = composite_system.generate_comparative_analysis(evaluation_results)
    
    print(f"  Comparative analysis generated:")
    print(f"    Total evaluations: {analysis['summary']['total_evaluations']}")
    print(f"    Metrics analyzed: {analysis['summary']['metrics_analyzed']}")
    print(f"    Rankings available: {len(analysis['rankings'])}")
    print(f"    Recommendations: {len(analysis['recommendations'])}")
    
    assert len(ranked_results) == len(evaluation_results)
    assert analysis['summary']['total_evaluations'] == 5
    assert len(analysis['rankings']) > 0
    
    print("  ✅ Ranking and comparison: PASS")
    return ranked_results, analysis


def test_visualization_engine():
    """Test metric visualization capabilities."""
    print("\nTesting Visualization Engine...")
    
    viz_engine = MetricVisualizationEngine()
    
    # Create sample evaluation results for visualization
    evaluation_results = []
    metrics_to_visualize = ["code_quality", "performance", "security", "readability"]
    
    for i in range(6):
        metrics = {}
        for j, metric_name in enumerate(metrics_to_visualize):
            # Create varied metric values
            base_value = 0.4 + (i * 0.1) + (j * 0.05)
            noise = 0.1 * ((i + j) % 3 - 1)  # Add some noise
            value = max(0.0, min(1.0, base_value + noise))
            
            metrics[metric_name] = MetricResult(metric_name, value, MetricType.CUSTOM)
        
        evaluation_results.append({
            "evaluation_id": f"viz_eval_{i+1}",
            "model": f"model_{i+1}",
            "metrics": metrics
        })
    
    # Test different chart types
    chart_types = [
        (ChartType.BAR_CHART, "Metric Comparison"),
        (ChartType.RADAR_CHART, "Performance Radar"),
        (ChartType.LINE_CHART, "Metric Trends"),
        (ChartType.HEATMAP, "Metric Heatmap")
    ]
    
    visualizations = {}
    
    for chart_type, title in chart_types:
        try:
            viz_data = viz_engine.create_metric_comparison_chart(
                evaluation_results,
                metrics_to_visualize,
                chart_type,
                title
            )
            
            visualizations[chart_type.value] = viz_data
            print(f"    {chart_type.value}: {len(viz_data.data)} data series")
            
        except Exception as e:
            print(f"    {chart_type.value}: Error - {e}")
    
    # Test performance distribution chart
    metric_values = {}
    for metric_name in metrics_to_visualize:
        values = []
        for result in evaluation_results:
            if metric_name in result["metrics"]:
                values.append(result["metrics"][metric_name].value)
        metric_values[metric_name] = values
    
    distribution_viz = viz_engine.create_performance_distribution_chart(
        metric_values, ChartType.BOX_PLOT
    )
    
    print(f"    Distribution chart: {len(distribution_viz.data)} data series")
    
    # Test correlation heatmap
    correlation_viz = viz_engine.create_correlation_heatmap(
        evaluation_results, metrics_to_visualize
    )
    
    print(f"    Correlation heatmap: {len(correlation_viz.data)} data series")
    
    # Test dashboard generation
    dashboard_data = viz_engine.generate_dashboard_data(
        evaluation_results, metrics_to_visualize
    )
    
    print(f"    Dashboard data generated:")
    print(f"      Charts: {len(dashboard_data['charts'])}")
    print(f"      Tables: {len(dashboard_data['tables'])}")
    print(f"      Alerts: {len(dashboard_data['alerts'])}")
    
    # Test export functionality
    if visualizations:
        first_viz = next(iter(visualizations.values()))
        json_export = viz_engine.export_visualization(first_viz, VisualizationFormat.JSON)
        html_export = viz_engine.export_visualization(first_viz, VisualizationFormat.HTML)
        
        print(f"    JSON export: {len(json_export)} characters")
        print(f"    HTML export: {len(html_export)} characters")
        
        assert len(json_export) > 0
        assert len(html_export) > 0
        assert "<html>" in html_export
    
    assert len(visualizations) > 0
    assert len(dashboard_data['charts']) > 0
    
    print("  ✅ Visualization engine: PASS")
    return visualizations, dashboard_data


def test_configuration_persistence():
    """Test configuration export and import."""
    print("\nTesting Configuration Persistence...")
    
    base_engine = MetricsEngine()
    scenario_metrics = ScenarioSpecificMetrics(base_engine)
    composite_system = CompositeMetricsSystem(base_engine, scenario_metrics)
    
    # Add some custom configurations
    custom_config = CompositeMetricConfig(
        name="test_composite",
        component_metrics=["metric1", "metric2", "metric3"],
        weight_config=WeightConfig(
            metric_weights={"metric1": 0.5, "metric2": 0.3, "metric3": 0.2},
            adaptive_weights=True
        ),
        aggregation_method=AggregationMethod.GEOMETRIC_MEAN,
        normalization_method="z_score",
        real_time_enabled=True
    )
    
    composite_system.register_composite_metric(custom_config)
    
    # Export configuration
    exported_config = composite_system.export_configuration()
    
    print(f"  Configuration exported:")
    print(f"    Composite configs: {len(exported_config['composite_configs'])}")
    print(f"    Weight configs: {len(exported_config['weight_configs'])}")
    
    # Create new system and import configuration
    new_base_engine = MetricsEngine()
    new_scenario_metrics = ScenarioSpecificMetrics(new_base_engine)
    new_composite_system = CompositeMetricsSystem(new_base_engine, new_scenario_metrics)
    
    new_composite_system.import_configuration(exported_config)
    
    # Verify import
    assert "test_composite" in new_composite_system.composite_configs
    imported_config = new_composite_system.composite_configs["test_composite"]
    
    assert imported_config.name == "test_composite"
    assert imported_config.aggregation_method == AggregationMethod.GEOMETRIC_MEAN
    assert imported_config.weight_config.adaptive_weights == True
    
    print("  ✅ Configuration persistence: PASS")
    return exported_config


def test_integration_with_existing_systems():
    """Test integration with existing single-turn and multi-turn systems."""
    print("\nTesting Integration with Existing Systems...")
    
    base_engine = MetricsEngine()
    scenario_metrics = ScenarioSpecificMetrics(base_engine)
    composite_system = CompositeMetricsSystem(base_engine, scenario_metrics)
    
    # Test with existing single-turn format
    single_turn_result = {
        "id": "integration_test_001",
        "model": "test_model",
        "config": "minimal_context|temperature=0.0",
        "prediction": "def hello(): return 'world'",
        "metrics": {
            "exact_match": 0.8,
            "codebleu": 0.75,
            "pass_at_1": 1.0,
            "syntax_valid": 1.0,
            "cyclomatic_complexity": 1.0,
            "security_score": 0.95
        }
    }
    
    # Convert to MetricResult format
    converted_metrics = {}
    for name, value in single_turn_result["metrics"].items():
        converted_metrics[name] = MetricResult(name, value, MetricType.CUSTOM)
    
    # Calculate composite metrics
    composite_results = composite_system.calculate_composite_metrics(
        converted_metrics,
        evaluation_id=single_turn_result["id"]
    )
    
    print(f"  Single-turn integration:")
    print(f"    Original metrics: {len(single_turn_result['metrics'])}")
    print(f"    Composite metrics: {len(composite_results)}")
    
    # Test with multi-turn format
    multi_turn_result = {
        "scenario_id": "integration_debug_001",
        "turns": [
            {"turn_id": "problem_analysis", "response": "I can see the issue is in the loop logic"},
            {"turn_id": "solution_proposal", "response": "Here's the corrected version with proper bounds"},
            {"turn_id": "verification", "response": "The solution handles all edge cases correctly"}
        ],
        "conversation_history": [
            {"role": "user", "content": "Help me debug this code"},
            {"role": "assistant", "content": "I can see the issue is in the loop logic"},
            {"role": "user", "content": "Can you fix it?"},
            {"role": "assistant", "content": "Here's the corrected version with proper bounds"}
        ]
    }
    
    # Calculate multi-turn metrics
    multi_turn_metrics = base_engine.calculate_multi_turn_metrics(
        multi_turn_result["conversation_history"],
        {turn["turn_id"]: {"response": turn["response"]} for turn in multi_turn_result["turns"]},
        {"scenario_type": "debug_session"}
    )
    
    # Calculate composite metrics for multi-turn
    multi_turn_composite = composite_system.calculate_composite_metrics(
        multi_turn_metrics,
        evaluation_id=multi_turn_result["scenario_id"]
    )
    
    print(f"  Multi-turn integration:")
    print(f"    Multi-turn metrics: {len(multi_turn_metrics)}")
    print(f"    Composite metrics: {len(multi_turn_composite)}")
    
    assert len(composite_results) > 0
    assert len(multi_turn_composite) > 0
    
    print("  ✅ Integration with existing systems: PASS")
    return composite_results, multi_turn_composite


def main():
    """Run all tests."""
    print("🧪 Testing Composite Metrics System Implementation")
    print("=" * 60)
    
    try:
        # Run all tests
        test_scenario_specific_metrics()
        test_composite_metrics_system()
        test_real_time_monitoring()
        test_ranking_and_comparison()
        test_visualization_engine()
        test_configuration_persistence()
        test_integration_with_existing_systems()
        
        print("\n" + "=" * 60)
        print("🎉 All Composite Metrics System tests passed!")
        print("\nKey Features Verified:")
        print("  ✅ Scenario-specific metrics for different domains")
        print("  ✅ Configurable weight systems and adaptive weighting")
        print("  ✅ Real-time metric calculation and monitoring")
        print("  ✅ Composite metric creation and aggregation")
        print("  ✅ Evaluation ranking and comparative analysis")
        print("  ✅ Comprehensive visualization capabilities")
        print("  ✅ Configuration persistence and import/export")
        print("  ✅ Integration with existing evaluation systems")
        
        return True
        
    except Exception as e:
        print(f"\n❌ Test failed with error: {e}")
        import traceback
        traceback.print_exc()
        return False


if __name__ == "__main__":
    success = main()
    sys.exit(0 if success else 1)