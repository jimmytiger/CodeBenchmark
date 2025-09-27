"""
Unit tests for MetricsEngine.
"""

import pytest
from unittest.mock import Mock, patch
import numpy as np
from typing import List, Dict, Any

from evaluation_engine.core.metrics_engine import MetricsEngine


class TestMetricsEngine:
    """Test cases for MetricsEngine."""

    def test_engine_initialization(self, metrics_engine):
        """Test metrics engine initialization."""
        assert metrics_engine is not None
        assert hasattr(metrics_engine, 'standard_metrics')
        assert hasattr(metrics_engine, 'custom_metrics')

    def test_calculate_bleu_score(self, metrics_engine):
        """Test BLEU score calculation."""
        predictions = ["The cat sat on the mat"]
        references = [["The cat is on the mat"]]
        
        bleu_score = metrics_engine.calculate_bleu(predictions, references)
        
        assert isinstance(bleu_score, float)
        assert 0.0 <= bleu_score <= 1.0

    def test_calculate_rouge_score(self, metrics_engine):
        """Test ROUGE score calculation."""
        predictions = ["The quick brown fox jumps over the lazy dog"]
        references = ["A quick brown fox jumps over a lazy dog"]
        
        rouge_scores = metrics_engine.calculate_rouge(predictions, references)
        
        assert isinstance(rouge_scores, dict)
        assert "rouge1" in rouge_scores
        assert "rouge2" in rouge_scores
        assert "rougeL" in rouge_scores
        
        for score in rouge_scores.values():
            assert 0.0 <= score <= 1.0

    def test_calculate_code_bleu(self, metrics_engine):
        """Test CodeBLEU score calculation."""
        predictions = ["""
def factorial(n):
    if n <= 1:
        return 1
    return n * factorial(n-1)
"""]
        references = [["""
def factorial(n):
    if n == 0 or n == 1:
        return 1
    else:
        return n * factorial(n-1)
"""]]
        
        code_bleu_score = metrics_engine.calculate_code_bleu(predictions, references)
        
        assert isinstance(code_bleu_score, float)
        assert 0.0 <= code_bleu_score <= 1.0

    def test_calculate_pass_at_k(self, metrics_engine):
        """Test Pass@K metric calculation."""
        # Mock execution results
        execution_results = [
            {"passed": True, "test_cases_passed": 5, "total_test_cases": 5},
            {"passed": False, "test_cases_passed": 3, "total_test_cases": 5},
            {"passed": True, "test_cases_passed": 5, "total_test_cases": 5},
            {"passed": False, "test_cases_passed": 2, "total_test_cases": 5},
            {"passed": True, "test_cases_passed": 4, "total_test_cases": 5}
        ]
        
        pass_at_1 = metrics_engine.calculate_pass_at_k(execution_results, k=1)
        pass_at_3 = metrics_engine.calculate_pass_at_k(execution_results, k=3)
        pass_at_5 = metrics_engine.calculate_pass_at_k(execution_results, k=5)
        
        assert isinstance(pass_at_1, float)
        assert isinstance(pass_at_3, float)
        assert isinstance(pass_at_5, float)
        
        assert 0.0 <= pass_at_1 <= 1.0
        assert 0.0 <= pass_at_3 <= 1.0
        assert 0.0 <= pass_at_5 <= 1.0
        
        # Pass@K should be non-decreasing as K increases
        assert pass_at_1 <= pass_at_3 <= pass_at_5

    def test_calculate_meteor_score(self, metrics_engine):
        """Test METEOR score calculation."""
        predictions = ["The cat sat on the mat"]
        references = ["The cat is sitting on the mat"]
        
        meteor_score = metrics_engine.calculate_meteor(predictions, references)
        
        assert isinstance(meteor_score, float)
        assert 0.0 <= meteor_score <= 1.0

    def test_calculate_accuracy(self, metrics_engine):
        """Test accuracy calculation."""
        predictions = ["A", "B", "C", "A", "B"]
        references = ["A", "B", "C", "B", "B"]
        
        accuracy = metrics_engine.calculate_accuracy(predictions, references)
        
        assert isinstance(accuracy, float)
        assert accuracy == 0.8  # 4 out of 5 correct

    def test_calculate_f1_score(self, metrics_engine):
        """Test F1 score calculation."""
        predictions = ["positive", "negative", "positive", "negative", "positive"]
        references = ["positive", "positive", "positive", "negative", "negative"]
        
        f1_score = metrics_engine.calculate_f1_score(predictions, references)
        
        assert isinstance(f1_score, float)
        assert 0.0 <= f1_score <= 1.0

    def test_calculate_code_quality_metrics(self, metrics_engine):
        """Test code quality metrics calculation."""
        code_samples = [
            """
def factorial(n):
    if n <= 1:
        return 1
    return n * factorial(n-1)
""",
            """
def fibonacci(n):
    if n <= 1:
        return n
    return fibonacci(n-1) + fibonacci(n-2)
""",
            """
# This is poorly formatted code
def bad_function(x,y,z):
    if x>0:
        return x+y*z
    else:return 0
"""
        ]
        
        quality_metrics = metrics_engine.calculate_code_quality_metrics(code_samples)
        
        assert isinstance(quality_metrics, dict)
        assert "syntax_validity" in quality_metrics
        assert "style_compliance" in quality_metrics
        assert "complexity_score" in quality_metrics
        assert "maintainability_score" in quality_metrics
        
        # Check that scores are in valid ranges
        for metric_name, scores in quality_metrics.items():
            assert isinstance(scores, list)
            assert len(scores) == len(code_samples)
            for score in scores:
                assert 0.0 <= score <= 1.0

    def test_calculate_security_metrics(self, metrics_engine):
        """Test security metrics calculation."""
        code_samples = [
            """
def safe_function(user_input):
    # Safe code with input validation
    if not isinstance(user_input, str):
        raise ValueError("Invalid input")
    return user_input.strip()
""",
            """
def unsafe_function(user_input):
    # Unsafe code with SQL injection vulnerability
    query = f"SELECT * FROM users WHERE name = '{user_input}'"
    return execute_query(query)
""",
            """
import os
def dangerous_function(filename):
    # Path traversal vulnerability
    return open(f"/data/{filename}", "r").read()
"""
        ]
        
        security_metrics = metrics_engine.calculate_security_metrics(code_samples)
        
        assert isinstance(security_metrics, dict)
        assert "vulnerability_score" in security_metrics
        assert "security_compliance" in security_metrics
        assert "risk_level" in security_metrics
        
        # Unsafe code should have lower security scores
        assert security_metrics["vulnerability_score"][0] > security_metrics["vulnerability_score"][1]
        assert security_metrics["vulnerability_score"][0] > security_metrics["vulnerability_score"][2]

    def test_calculate_multi_turn_metrics(self, metrics_engine, sample_multi_turn_data):
        """Test multi-turn conversation metrics."""
        conversation_data = sample_multi_turn_data
        
        multi_turn_metrics = metrics_engine.calculate_multi_turn_metrics(conversation_data)
        
        assert isinstance(multi_turn_metrics, dict)
        assert "context_retention" in multi_turn_metrics
        assert "coherence_score" in multi_turn_metrics
        assert "goal_achievement" in multi_turn_metrics
        assert "turn_quality" in multi_turn_metrics
        
        for metric_name, score in multi_turn_metrics.items():
            if isinstance(score, (int, float)):
                assert 0.0 <= score <= 1.0

    def test_calculate_composite_metrics(self, metrics_engine):
        """Test composite metrics calculation."""
        individual_metrics = {
            "accuracy": 0.85,
            "bleu": 0.72,
            "rouge1": 0.68,
            "code_quality": 0.90,
            "security_score": 0.95
        }
        
        weights = {
            "accuracy": 0.3,
            "bleu": 0.2,
            "rouge1": 0.1,
            "code_quality": 0.25,
            "security_score": 0.15
        }
        
        composite_score = metrics_engine.calculate_composite_score(individual_metrics, weights)
        
        assert isinstance(composite_score, float)
        assert 0.0 <= composite_score <= 1.0
        
        # Verify weighted calculation
        expected_score = sum(individual_metrics[metric] * weights[metric] 
                           for metric in individual_metrics)
        assert abs(composite_score - expected_score) < 1e-6

    def test_aggregate_metrics(self, metrics_engine):
        """Test metrics aggregation across multiple samples."""
        metric_results = [
            {"accuracy": 0.8, "bleu": 0.7, "rouge1": 0.6},
            {"accuracy": 0.9, "bleu": 0.8, "rouge1": 0.7},
            {"accuracy": 0.85, "bleu": 0.75, "rouge1": 0.65},
            {"accuracy": 0.7, "bleu": 0.6, "rouge1": 0.5}
        ]
        
        aggregated = metrics_engine.aggregate_metrics(metric_results)
        
        assert isinstance(aggregated, dict)
        
        for metric_name in ["accuracy", "bleu", "rouge1"]:
            assert metric_name in aggregated
            assert "mean" in aggregated[metric_name]
            assert "std" in aggregated[metric_name]
            assert "min" in aggregated[metric_name]
            assert "max" in aggregated[metric_name]
            assert "median" in aggregated[metric_name]
            
            # Verify calculations
            values = [result[metric_name] for result in metric_results]
            assert abs(aggregated[metric_name]["mean"] - np.mean(values)) < 1e-6
            assert abs(aggregated[metric_name]["std"] - np.std(values)) < 1e-6
            assert aggregated[metric_name]["min"] == min(values)
            assert aggregated[metric_name]["max"] == max(values)

    def test_statistical_significance(self, metrics_engine):
        """Test statistical significance testing."""
        results_a = [0.8, 0.82, 0.78, 0.85, 0.79, 0.83, 0.81, 0.84, 0.77, 0.86]
        results_b = [0.75, 0.77, 0.73, 0.80, 0.74, 0.78, 0.76, 0.79, 0.72, 0.81]
        
        significance_test = metrics_engine.test_statistical_significance(results_a, results_b)
        
        assert isinstance(significance_test, dict)
        assert "p_value" in significance_test
        assert "is_significant" in significance_test
        assert "effect_size" in significance_test
        assert "confidence_interval" in significance_test
        
        assert isinstance(significance_test["p_value"], float)
        assert isinstance(significance_test["is_significant"], bool)
        assert isinstance(significance_test["effect_size"], float)

    def test_confidence_intervals(self, metrics_engine):
        """Test confidence interval calculation."""
        data = [0.8, 0.82, 0.78, 0.85, 0.79, 0.83, 0.81, 0.84, 0.77, 0.86]
        
        ci_95 = metrics_engine.calculate_confidence_interval(data, confidence=0.95)
        ci_99 = metrics_engine.calculate_confidence_interval(data, confidence=0.99)
        
        assert isinstance(ci_95, tuple)
        assert isinstance(ci_99, tuple)
        assert len(ci_95) == 2
        assert len(ci_99) == 2
        
        # 99% CI should be wider than 95% CI
        assert (ci_99[1] - ci_99[0]) > (ci_95[1] - ci_95[0])
        
        # Mean should be within confidence intervals
        mean_value = np.mean(data)
        assert ci_95[0] <= mean_value <= ci_95[1]
        assert ci_99[0] <= mean_value <= ci_99[1]

    def test_metric_validation(self, metrics_engine):
        """Test metric validation."""
        # Valid metrics
        valid_predictions = ["A", "B", "C"]
        valid_references = ["A", "C", "C"]
        
        is_valid, errors = metrics_engine.validate_metric_inputs(valid_predictions, valid_references)
        assert is_valid is True
        assert len(errors) == 0
        
        # Invalid metrics - mismatched lengths
        invalid_predictions = ["A", "B"]
        invalid_references = ["A", "B", "C"]
        
        is_valid, errors = metrics_engine.validate_metric_inputs(invalid_predictions, invalid_references)
        assert is_valid is False
        assert len(errors) > 0

    def test_custom_metric_registration(self, metrics_engine):
        """Test custom metric registration."""
        def custom_metric(predictions: List[str], references: List[str]) -> float:
            """Custom metric that counts exact matches."""
            matches = sum(1 for p, r in zip(predictions, references) if p == r)
            return matches / len(predictions)
        
        # Register custom metric
        metrics_engine.register_custom_metric("exact_match", custom_metric)
        
        # Test custom metric
        predictions = ["A", "B", "C", "A"]
        references = ["A", "B", "D", "A"]
        
        result = metrics_engine.calculate_custom_metric("exact_match", predictions, references)
        
        assert isinstance(result, float)
        assert result == 0.75  # 3 out of 4 matches

    def test_metric_caching(self, metrics_engine):
        """Test metric calculation caching."""
        predictions = ["The cat sat on the mat"] * 100
        references = [["The cat is on the mat"]] * 100
        
        # First calculation
        import time
        start_time = time.time()
        bleu_score_1 = metrics_engine.calculate_bleu(predictions, references, use_cache=True)
        first_duration = time.time() - start_time
        
        # Second calculation (should be cached)
        start_time = time.time()
        bleu_score_2 = metrics_engine.calculate_bleu(predictions, references, use_cache=True)
        second_duration = time.time() - start_time
        
        # Results should be identical
        assert bleu_score_1 == bleu_score_2
        
        # Second calculation should be faster (cached)
        assert second_duration < first_duration

    def test_batch_metric_calculation(self, metrics_engine):
        """Test batch metric calculation."""
        batch_predictions = [
            ["The cat sat on the mat"],
            ["The dog ran in the park"],
            ["The bird flew over the tree"]
        ]
        
        batch_references = [
            [["The cat is on the mat"]],
            [["The dog runs in the park"]],
            [["The bird flies over the tree"]]
        ]
        
        batch_results = metrics_engine.calculate_batch_metrics(
            batch_predictions, 
            batch_references,
            metrics=["bleu", "rouge"]
        )
        
        assert isinstance(batch_results, list)
        assert len(batch_results) == 3
        
        for result in batch_results:
            assert isinstance(result, dict)
            assert "bleu" in result
            assert "rouge" in result

    def test_metric_error_handling(self, metrics_engine):
        """Test metric calculation error handling."""
        # Empty inputs
        with pytest.raises(ValueError, match="Empty inputs"):
            metrics_engine.calculate_bleu([], [])
        
        # Mismatched lengths
        with pytest.raises(ValueError, match="Length mismatch"):
            metrics_engine.calculate_bleu(["A"], [["A"], ["B"]])
        
        # Invalid metric name
        with pytest.raises(ValueError, match="Unknown metric"):
            metrics_engine.calculate_metric("invalid_metric", ["A"], ["A"])

    def test_performance_metrics(self, metrics_engine, performance_test_data):
        """Test metrics calculation performance."""
        import time
        
        # Large dataset performance test
        predictions = [item["input"] for item in performance_test_data]
        references = [[item["expected_output"]] for item in performance_test_data]
        
        start_time = time.time()
        bleu_scores = metrics_engine.calculate_bleu(predictions, references)
        duration = time.time() - start_time
        
        # Should complete within reasonable time (adjust threshold as needed)
        assert duration < 30.0  # 30 seconds for 1000 samples
        assert isinstance(bleu_scores, float)

    def test_memory_efficiency(self, metrics_engine, performance_test_data):
        """Test memory efficiency of metrics calculation."""
        import psutil
        import os
        
        process = psutil.Process(os.getpid())
        initial_memory = process.memory_info().rss
        
        # Process large dataset
        predictions = [item["input"] for item in performance_test_data]
        references = [[item["expected_output"]] for item in performance_test_data]
        
        # Calculate multiple metrics
        metrics_engine.calculate_bleu(predictions, references)
        metrics_engine.calculate_rouge(predictions, [ref[0] for ref in references])
        
        final_memory = process.memory_info().rss
        memory_increase = final_memory - initial_memory
        
        # Memory increase should be reasonable
        assert memory_increase < 200 * 1024 * 1024  # Less than 200MB