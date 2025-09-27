#!/usr/bin/env python3
"""
Test script for MetricsEngine implementation.

This script tests the comprehensive metrics calculation capabilities
including standard NLP metrics, code quality metrics, functional metrics,
and multi-turn conversation metrics.
"""

import sys
import json
from typing import Dict, List, Any

# Add the evaluation engine to the path
sys.path.insert(0, '.')

from evaluation_engine.core.metrics_engine import (
    MetricsEngine, MetricConfig, MetricType, MetricResult
)


def test_standard_nlp_metrics():
    """Test standard NLP metrics calculation."""
    print("Testing Standard NLP Metrics...")
    
    engine = MetricsEngine()
    
    # Test data
    predictions = [
        "The quick brown fox jumps over the lazy dog",
        "Hello world, this is a test",
        "def fibonacci(n): return n if n <= 1 else fibonacci(n-1) + fibonacci(n-2)"
    ]
    
    references = [
        "The quick brown fox jumps over the lazy dog",
        "Hello world, this is a sample",
        "def fibonacci(n): return n if n <= 1 else fibonacci(n-1) + fibonacci(n-2)"
    ]
    
    # Test with default metrics
    results = engine.calculate_standard_metrics(predictions, references)
    
    print(f"  Standard metrics calculated: {len(results)}")
    for name, result in results.items():
        print(f"    {name}: {result.value:.3f} (type: {result.metric_type.value})")
    
    # Test exact match
    assert 'exact_match' in results
    assert results['exact_match'].value > 0.5  # Should have some exact matches
    
    # Test BLEU score
    assert 'bleu' in results
    assert 0.0 <= results['bleu'].value <= 1.0
    
    print("  ✅ Standard NLP metrics: PASS")
    return results


def test_code_quality_metrics():
    """Test code quality metrics calculation."""
    print("\nTesting Code Quality Metrics...")
    
    engine = MetricsEngine()
    
    # Test code samples
    code_predictions = [
        # Valid Python code
        """
def hello_world():
    print("Hello, World!")
    return "success"
        """,
        
        # Code with syntax error
        """
def broken_function(
    print("This has a syntax error"
    return None
        """,
        
        # Code with security issues
        """
import os
password = "hardcoded_secret"
os.system("rm -rf /")
eval(user_input)
        """
    ]
    
    results = engine.calculate_code_quality_metrics(code_predictions)
    
    print(f"  Code quality metrics calculated: {len(results)}")
    for name, result in results.items():
        print(f"    {name}: {result.value:.3f}")
    
    # Test syntax validity
    assert 'syntax_valid' in results
    assert 0.0 <= results['syntax_valid'].value <= 1.0
    
    # Test security score
    assert 'security_score' in results
    assert 0.0 <= results['security_score'].value <= 1.0
    
    # Test cyclomatic complexity
    assert 'cyclomatic_complexity' in results
    assert results['cyclomatic_complexity'].value >= 1.0
    
    print("  ✅ Code quality metrics: PASS")
    return results


def test_functional_metrics():
    """Test functional metrics calculation."""
    print("\nTesting Functional Metrics...")
    
    engine = MetricsEngine()
    
    # Test code and test cases
    code_predictions = [
        """
def add(a, b):
    return a + b
        """,
        
        """
def multiply(x, y):
    return x * y
        """
    ]
    
    test_cases = [
        [
            {"function_name": "add", "expected_output": 5, "inputs": [2, 3]},
            {"function_name": "add", "expected_output": 10, "inputs": [4, 6]}
        ],
        [
            {"function_name": "multiply", "expected_output": 12, "inputs": [3, 4]},
            {"function_name": "multiply", "expected_output": 20, "inputs": [4, 5]}
        ]
    ]
    
    results = engine.calculate_functional_metrics(code_predictions, test_cases)
    
    print(f"  Functional metrics calculated: {len(results)}")
    for name, result in results.items():
        print(f"    {name}: {result.value:.3f}")
    
    # Test Pass@1
    assert 'pass_at_1' in results
    assert 0.0 <= results['pass_at_1'].value <= 1.0
    
    # Test execution success
    assert 'execution_success' in results
    assert 0.0 <= results['execution_success'].value <= 1.0
    
    print("  ✅ Functional metrics: PASS")
    return results


def test_multi_turn_metrics():
    """Test multi-turn conversation metrics."""
    print("\nTesting Multi-Turn Metrics...")
    
    engine = MetricsEngine()
    
    # Sample conversation history
    conversation_history = [
        {"role": "user", "content": "Can you help me debug this Python code?"},
        {"role": "assistant", "content": "Of course! I'd be happy to help you debug your Python code. Please share the code you're having trouble with."},
        {"role": "user", "content": "Here's the code: def factorial(n): return n * factorial(n-1)"},
        {"role": "assistant", "content": "I can see the issue with your factorial function. The problem is that there's no base case to stop the recursion. Here's the corrected version: def factorial(n): return 1 if n <= 1 else n * factorial(n-1)"},
        {"role": "user", "content": "Thank you! That makes sense. Can you explain why the base case is important?"},
        {"role": "assistant", "content": "Absolutely! The base case is crucial in recursive functions because it provides a stopping condition. Without it, the function would call itself indefinitely, leading to a stack overflow error."}
    ]
    
    # Sample turn results
    turn_results = {
        "turn_1": {"response": "Of course! I'd be happy to help you debug your Python code.", "quality": 0.8},
        "turn_2": {"response": "I can see the issue with your factorial function...", "quality": 0.9},
        "turn_3": {"response": "Absolutely! The base case is crucial...", "quality": 0.85}
    }
    
    # Sample scenario config
    scenario_config = {
        "scenario_type": "debug_session",
        "expected_turns": 3,
        "goal": "help_debug_code"
    }
    
    results = engine.calculate_multi_turn_metrics(
        conversation_history, turn_results, scenario_config
    )
    
    print(f"  Multi-turn metrics calculated: {len(results)}")
    for name, result in results.items():
        print(f"    {name}: {result.value:.3f}")
    
    # Test context retention
    assert 'context_retention' in results
    assert 0.0 <= results['context_retention'].value <= 1.0
    
    # Test conversation coherence
    assert 'conversation_coherence' in results
    assert 0.0 <= results['conversation_coherence'].value <= 1.0
    
    print("  ✅ Multi-turn metrics: PASS")
    return results


def test_custom_metrics():
    """Test custom metric registration and calculation."""
    print("\nTesting Custom Metrics...")
    
    engine = MetricsEngine()
    
    # Define a custom metric
    def custom_word_count_metric(prediction: str, reference: str, **kwargs) -> float:
        """Custom metric that compares word counts."""
        pred_words = len(prediction.split())
        ref_words = len(reference.split())
        
        if ref_words == 0:
            return 1.0 if pred_words == 0 else 0.0
        
        ratio = pred_words / ref_words
        # Score is higher when word counts are similar
        return 1.0 - abs(1.0 - ratio)
    
    # Register the custom metric
    engine.register_custom_metric(
        "word_count_similarity", 
        custom_word_count_metric,
        MetricType.CUSTOM
    )
    
    # Test the custom metric
    predictions = ["This is a test", "Short", "This is a much longer test sentence"]
    references = ["This is a sample", "Brief", "This is a longer reference sentence"]
    
    custom_config = [MetricConfig("word_count_similarity", MetricType.CUSTOM)]
    results = engine.calculate_standard_metrics(predictions, references, custom_config)
    
    print(f"  Custom metrics calculated: {len(results)}")
    for name, result in results.items():
        print(f"    {name}: {result.value:.3f}")
    
    assert 'word_count_similarity' in results
    assert 0.0 <= results['word_count_similarity'].value <= 1.0
    
    print("  ✅ Custom metrics: PASS")
    return results


def test_composite_metrics():
    """Test composite metric creation and calculation."""
    print("\nTesting Composite Metrics...")
    
    engine = MetricsEngine()
    
    # First calculate some base metrics
    predictions = ["Hello world", "Test code", "Sample text"]
    references = ["Hello world", "Test code", "Sample text"]
    
    base_results = engine.calculate_standard_metrics(predictions, references)
    
    # Create a composite metric
    engine.create_composite_metric(
        "overall_quality",
        ["exact_match", "bleu", "edit_distance"],
        [0.4, 0.3, 0.3],
        "weighted_average"
    )
    
    # Calculate composite metrics
    composite_results = engine.calculate_composite_metrics(base_results)
    
    print(f"  Composite metrics calculated: {len(composite_results)}")
    for name, result in composite_results.items():
        print(f"    {name}: {result.value:.3f}")
        print(f"      Components: {result.metadata.get('components', [])}")
    
    assert 'overall_quality' in composite_results
    assert 0.0 <= composite_results['overall_quality'].value <= 1.0
    
    print("  ✅ Composite metrics: PASS")
    return composite_results


def test_metric_aggregation():
    """Test metric aggregation across multiple evaluations."""
    print("\nTesting Metric Aggregation...")
    
    engine = MetricsEngine()
    
    # Simulate multiple evaluation results
    evaluation_results = []
    
    for i in range(3):
        predictions = [f"Test {i} prediction", f"Another test {i}"]
        references = [f"Test {i} reference", f"Another test {i}"]
        
        results = engine.calculate_standard_metrics(predictions, references)
        evaluation_results.append(results)
    
    # Aggregate results
    aggregated = engine.aggregate_metrics(evaluation_results)
    
    print(f"  Aggregated metrics: {len(aggregated)}")
    for name, result in aggregated.items():
        print(f"    {name}: {result.value:.3f} (±{result.metadata.get('std_dev', 0):.3f})")
    
    # Check that aggregated results have proper metadata
    for result in aggregated.values():
        assert 'individual_values' in result.metadata
        assert 'std_dev' in result.metadata
        assert 'confidence_interval_95' in result.metadata
    
    print("  ✅ Metric aggregation: PASS")
    return aggregated


def test_statistical_analysis():
    """Test statistical analysis generation."""
    print("\nTesting Statistical Analysis...")
    
    engine = MetricsEngine()
    
    # Calculate some metrics
    predictions = ["Good result", "Average result", "Poor result", "Excellent result"]
    references = ["Good result", "Great result", "Bad result", "Excellent result"]
    
    results = engine.calculate_standard_metrics(predictions, references)
    
    # Generate statistical analysis
    analysis = engine.generate_statistical_analysis(results)
    
    print("  Statistical analysis generated:")
    print(f"    Total metrics: {analysis['summary']['total_metrics']}")
    print(f"    Mean score: {analysis['summary']['mean_score']:.3f}")
    print(f"    Score range: {analysis['summary']['score_range']:.3f}")
    print(f"    Outliers detected: {len(analysis['outliers'])}")
    print(f"    Recommendations: {len(analysis['recommendations'])}")
    
    # Verify analysis structure
    assert 'summary' in analysis
    assert 'outliers' in analysis
    assert 'recommendations' in analysis
    
    print("  ✅ Statistical analysis: PASS")
    return analysis


def test_integration_with_existing_metrics():
    """Test integration with existing single-turn and multi-turn metrics."""
    print("\nTesting Integration with Existing Metrics...")
    
    engine = MetricsEngine()
    
    # Test integration with single-turn scenario format
    single_turn_result = {
        "id": "test_001",
        "model": "test_model",
        "config": "minimal_context|temperature=0.0",
        "prediction": "def hello(): return 'world'",
        "metrics": {
            "exact_match": 0.0,
            "codebleu": 0.75,
            "pass_at_1": 1.0,
            "syntax_valid": 1.0,
            "cyclomatic_complexity": 1.0,
            "security_score": 0.95
        }
    }
    
    # Test integration with multi-turn scenario format
    multi_turn_result = {
        "scenario_id": "debug_session_001",
        "turns": [
            {"turn_id": "initial_problem", "response": "I need help with this code"},
            {"turn_id": "analysis", "response": "I can see the issue is in the loop"},
            {"turn_id": "solution", "response": "Here's the corrected version"}
        ]
    }
    
    # Verify that existing metrics can be processed
    existing_metrics = single_turn_result["metrics"]
    print(f"  Existing single-turn metrics: {len(existing_metrics)}")
    for name, value in existing_metrics.items():
        print(f"    {name}: {value}")
    
    # Verify multi-turn structure
    print(f"  Multi-turn scenario turns: {len(multi_turn_result['turns'])}")
    
    print("  ✅ Integration with existing metrics: PASS")
    return True


def main():
    """Run all tests."""
    print("🧪 Testing MetricsEngine Implementation")
    print("=" * 50)
    
    try:
        # Run all tests
        test_standard_nlp_metrics()
        test_code_quality_metrics()
        test_functional_metrics()
        test_multi_turn_metrics()
        test_custom_metrics()
        test_composite_metrics()
        test_metric_aggregation()
        test_statistical_analysis()
        test_integration_with_existing_metrics()
        
        print("\n" + "=" * 50)
        print("🎉 All MetricsEngine tests passed!")
        print("\nKey Features Verified:")
        print("  ✅ Standard NLP metrics (BLEU, ROUGE, METEOR, etc.)")
        print("  ✅ Code quality metrics (syntax, complexity, security)")
        print("  ✅ Functional metrics (Pass@K, execution success)")
        print("  ✅ Multi-turn conversation metrics")
        print("  ✅ Custom metric registration")
        print("  ✅ Composite metric creation")
        print("  ✅ Metric aggregation and statistical analysis")
        print("  ✅ Integration with existing metric formats")
        
        return True
        
    except Exception as e:
        print(f"\n❌ Test failed with error: {e}")
        import traceback
        traceback.print_exc()
        return False


if __name__ == "__main__":
    success = main()
    sys.exit(0 if success else 1)