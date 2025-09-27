"""
Comprehensive Metrics Engine for AI Evaluation.

This module provides a centralized metrics calculation system that supports
standard NLP metrics, code quality metrics, functional metrics, and custom
scenario-specific metrics for both single-turn and multi-turn evaluations.
"""

import re
import ast
import math
import statistics
import subprocess
import tempfile
import os
from typing import Dict, List, Any, Optional, Union, Tuple, Callable
from collections import defaultdict, Counter
from dataclasses import dataclass
from enum import Enum
import json

# Import standard metrics libraries
try:
    from nltk.translate.bleu_score import sentence_bleu, SmoothingFunction
    from nltk.translate.meteor_score import meteor_score
    from nltk.tokenize import word_tokenize
    NLTK_AVAILABLE = True
except ImportError:
    NLTK_AVAILABLE = False

try:
    from rouge_score import rouge_scorer
    ROUGE_AVAILABLE = True
except ImportError:
    ROUGE_AVAILABLE = False

try:
    from codebleu import calc_codebleu
    CODEBLEU_AVAILABLE = True
except ImportError:
    CODEBLEU_AVAILABLE = False


class MetricType(Enum):
    """Types of metrics supported by the engine."""
    STANDARD_NLP = "standard_nlp"
    CODE_QUALITY = "code_quality"
    FUNCTIONAL = "functional"
    MULTI_TURN = "multi_turn"
    CUSTOM = "custom"
    COMPOSITE = "composite"


@dataclass
class MetricResult:
    """Result of a metric calculation."""
    name: str
    value: float
    metric_type: MetricType
    metadata: Dict[str, Any] = None
    
    def __post_init__(self):
        if self.metadata is None:
            self.metadata = {}


@dataclass
class MetricConfig:
    """Configuration for metric calculation."""
    name: str
    metric_type: MetricType
    weight: float = 1.0
    enabled: bool = True
    parameters: Dict[str, Any] = None
    
    def __post_init__(self):
        if self.parameters is None:
            self.parameters = {}


class MetricsEngine:
    """
    Comprehensive metrics calculation engine.
    
    Supports standard NLP metrics (BLEU, ROUGE, METEOR), code quality metrics,
    functional metrics (Pass@K), and custom scenario-specific metrics.
    """
    
    def __init__(self):
        """Initialize the metrics engine."""
        self.metric_calculators = self._initialize_calculators()
        self.custom_metrics = {}
        self.composite_metrics = {}
        
        # Initialize NLTK components if available
        if NLTK_AVAILABLE:
            self._initialize_nltk()
            
        # Initialize ROUGE scorer if available
        if ROUGE_AVAILABLE:
            self.rouge_scorer = rouge_scorer.RougeScorer(
                ['rouge1', 'rouge2', 'rougeL'], use_stemmer=True
            )
        
    def _initialize_nltk(self):
        """Initialize NLTK components."""
        try:
            import nltk
            # Download required NLTK data
            nltk.download('punkt', quiet=True)
            nltk.download('wordnet', quiet=True)
            nltk.download('omw-1.4', quiet=True)
        except Exception:
            pass  # Continue without NLTK if download fails
    
    def _initialize_calculators(self) -> Dict[str, Callable]:
        """Initialize metric calculator functions."""
        return {
            # Standard NLP metrics
            'bleu': self._calculate_bleu,
            'rouge_1': self._calculate_rouge_1,
            'rouge_2': self._calculate_rouge_2,
            'rouge_l': self._calculate_rouge_l,
            'meteor': self._calculate_meteor,
            'codebleu': self._calculate_codebleu,
            'exact_match': self._calculate_exact_match,
            'edit_distance': self._calculate_edit_distance,
            
            # Code quality metrics
            'syntax_valid': self._calculate_syntax_validity,
            'cyclomatic_complexity': self._calculate_cyclomatic_complexity,
            'security_score': self._calculate_security_score,
            'code_style_score': self._calculate_code_style_score,
            'performance_score': self._calculate_performance_score,
            
            # Functional metrics
            'pass_at_1': self._calculate_pass_at_k,
            'pass_at_5': self._calculate_pass_at_k,
            'pass_at_10': self._calculate_pass_at_k,
            'execution_success': self._calculate_execution_success,
            'test_coverage': self._calculate_test_coverage,
            'runtime_correctness': self._calculate_runtime_correctness,
            'memory_efficiency': self._calculate_memory_efficiency,
            
            # Multi-turn specific metrics
            'context_retention': self._calculate_context_retention,
            'conversation_coherence': self._calculate_conversation_coherence,
            'turn_quality': self._calculate_turn_quality,
            'goal_achievement': self._calculate_goal_achievement,
        }
    
    def calculate_standard_metrics(self, 
                                 predictions: List[str], 
                                 references: List[str],
                                 metric_configs: Optional[List[MetricConfig]] = None) -> Dict[str, MetricResult]:
        """
        Calculate standard NLP metrics.
        
        Args:
            predictions: List of predicted texts
            references: List of reference texts
            metric_configs: Optional list of metric configurations
            
        Returns:
            Dictionary of metric results
        """
        if len(predictions) != len(references):
            raise ValueError("Predictions and references must have the same length")
        
        results = {}
        
        # Default metrics if none specified
        if metric_configs is None:
            metric_configs = [
                MetricConfig('bleu', MetricType.STANDARD_NLP),
                MetricConfig('rouge_l', MetricType.STANDARD_NLP),
                MetricConfig('exact_match', MetricType.STANDARD_NLP),
                MetricConfig('edit_distance', MetricType.STANDARD_NLP),
            ]
        
        for config in metric_configs:
            if not config.enabled or config.name not in self.metric_calculators:
                continue
                
            try:
                calculator = self.metric_calculators[config.name]
                
                # Calculate metric for each prediction-reference pair
                scores = []
                for pred, ref in zip(predictions, references):
                    if config.name in ['pass_at_1', 'pass_at_5', 'pass_at_10']:
                        # Pass@K metrics need special handling
                        k = int(config.name.split('_')[-1])
                        score = calculator(pred, ref, k=k, **config.parameters)
                    else:
                        score = calculator(pred, ref, **config.parameters)
                    scores.append(score)
                
                # Aggregate scores
                avg_score = statistics.mean(scores) if scores else 0.0
                
                results[config.name] = MetricResult(
                    name=config.name,
                    value=avg_score,
                    metric_type=config.metric_type,
                    metadata={
                        'individual_scores': scores,
                        'std_dev': statistics.stdev(scores) if len(scores) > 1 else 0.0,
                        'min_score': min(scores) if scores else 0.0,
                        'max_score': max(scores) if scores else 0.0,
                        'weight': config.weight
                    }
                )
                
            except Exception as e:
                # Log error and continue with other metrics
                results[config.name] = MetricResult(
                    name=config.name,
                    value=0.0,
                    metric_type=config.metric_type,
                    metadata={'error': str(e)}
                )
        
        return results
    
    def calculate_code_quality_metrics(self, 
                                     code_predictions: List[str],
                                     code_references: Optional[List[str]] = None,
                                     language: str = 'python') -> Dict[str, MetricResult]:
        """
        Calculate code quality metrics.
        
        Args:
            code_predictions: List of predicted code
            code_references: Optional list of reference code
            language: Programming language
            
        Returns:
            Dictionary of code quality metric results
        """
        results = {}
        
        # Code quality metrics that don't need references
        quality_metrics = [
            'syntax_valid',
            'cyclomatic_complexity', 
            'security_score',
            'code_style_score',
            'performance_score'
        ]
        
        for metric_name in quality_metrics:
            if metric_name not in self.metric_calculators:
                continue
                
            calculator = self.metric_calculators[metric_name]
            scores = []
            
            for code in code_predictions:
                try:
                    score = calculator(code, language=language)
                    scores.append(score)
                except Exception as e:
                    scores.append(0.0)
            
            avg_score = statistics.mean(scores) if scores else 0.0
            
            results[metric_name] = MetricResult(
                name=metric_name,
                value=avg_score,
                metric_type=MetricType.CODE_QUALITY,
                metadata={
                    'individual_scores': scores,
                    'language': language,
                    'std_dev': statistics.stdev(scores) if len(scores) > 1 else 0.0
                }
            )
        
        # If references are provided, calculate comparison metrics
        if code_references and len(code_references) == len(code_predictions):
            comparison_results = self.calculate_standard_metrics(
                code_predictions, 
                code_references,
                [MetricConfig('codebleu', MetricType.CODE_QUALITY)]
            )
            results.update(comparison_results)
        
        return results
    
    def calculate_functional_metrics(self,
                                   code_predictions: List[str],
                                   test_cases: List[List[Dict[str, Any]]],
                                   language: str = 'python') -> Dict[str, MetricResult]:
        """
        Calculate functional metrics like Pass@K.
        
        Args:
            code_predictions: List of predicted code
            test_cases: List of test cases for each prediction
            language: Programming language
            
        Returns:
            Dictionary of functional metric results
        """
        results = {}
        
        if len(code_predictions) != len(test_cases):
            raise ValueError("Code predictions and test cases must have the same length")
        
        # Calculate Pass@K metrics
        for k in [1, 5, 10]:
            if len(code_predictions) >= k:
                pass_at_k_scores = []
                
                for code, tests in zip(code_predictions, test_cases):
                    score = self._calculate_pass_at_k(code, tests, k=k, language=language)
                    pass_at_k_scores.append(score)
                
                avg_score = statistics.mean(pass_at_k_scores) if pass_at_k_scores else 0.0
                
                results[f'pass_at_{k}'] = MetricResult(
                    name=f'pass_at_{k}',
                    value=avg_score,
                    metric_type=MetricType.FUNCTIONAL,
                    metadata={
                        'individual_scores': pass_at_k_scores,
                        'k': k,
                        'language': language
                    }
                )
        
        # Calculate other functional metrics
        functional_metrics = ['execution_success', 'runtime_correctness', 'memory_efficiency']
        
        for metric_name in functional_metrics:
            if metric_name not in self.metric_calculators:
                continue
                
            calculator = self.metric_calculators[metric_name]
            scores = []
            
            for code, tests in zip(code_predictions, test_cases):
                try:
                    score = calculator(code, tests, language=language)
                    scores.append(score)
                except Exception:
                    scores.append(0.0)
            
            avg_score = statistics.mean(scores) if scores else 0.0
            
            results[metric_name] = MetricResult(
                name=metric_name,
                value=avg_score,
                metric_type=MetricType.FUNCTIONAL,
                metadata={
                    'individual_scores': scores,
                    'language': language
                }
            )
        
        return results
    
    def calculate_multi_turn_metrics(self,
                                   conversation_history: List[Dict[str, Any]],
                                   turn_results: Dict[str, Any],
                                   scenario_config: Optional[Dict[str, Any]] = None) -> Dict[str, MetricResult]:
        """
        Calculate multi-turn conversation metrics.
        
        Args:
            conversation_history: List of conversation turns
            turn_results: Results from individual turns
            scenario_config: Optional scenario configuration
            
        Returns:
            Dictionary of multi-turn metric results
        """
        results = {}
        
        multi_turn_metrics = [
            'context_retention',
            'conversation_coherence', 
            'turn_quality',
            'goal_achievement'
        ]
        
        for metric_name in multi_turn_metrics:
            if metric_name not in self.metric_calculators:
                continue
                
            calculator = self.metric_calculators[metric_name]
            
            try:
                score = calculator(
                    conversation_history=conversation_history,
                    turn_results=turn_results,
                    scenario_config=scenario_config
                )
                
                results[metric_name] = MetricResult(
                    name=metric_name,
                    value=score,
                    metric_type=MetricType.MULTI_TURN,
                    metadata={
                        'num_turns': len(conversation_history),
                        'scenario_type': scenario_config.get('scenario_type') if scenario_config else None
                    }
                )
                
            except Exception as e:
                results[metric_name] = MetricResult(
                    name=metric_name,
                    value=0.0,
                    metric_type=MetricType.MULTI_TURN,
                    metadata={'error': str(e)}
                )
        
        return results
    
    def register_custom_metric(self, 
                             name: str, 
                             calculator: Callable,
                             metric_type: MetricType = MetricType.CUSTOM):
        """
        Register a custom metric calculator.
        
        Args:
            name: Name of the metric
            calculator: Function that calculates the metric
            metric_type: Type of the metric
        """
        self.custom_metrics[name] = {
            'calculator': calculator,
            'metric_type': metric_type
        }
        self.metric_calculators[name] = calculator
    
    def create_composite_metric(self,
                              name: str,
                              component_metrics: List[str],
                              weights: Optional[List[float]] = None,
                              aggregation_method: str = 'weighted_average') -> None:
        """
        Create a composite metric from multiple component metrics.
        
        Args:
            name: Name of the composite metric
            component_metrics: List of component metric names
            weights: Optional weights for each component
            aggregation_method: Method to aggregate components
        """
        if weights is None:
            weights = [1.0] * len(component_metrics)
        
        if len(weights) != len(component_metrics):
            raise ValueError("Weights must match number of component metrics")
        
        self.composite_metrics[name] = {
            'components': component_metrics,
            'weights': weights,
            'aggregation_method': aggregation_method
        }
    
    def calculate_composite_metrics(self, 
                                  metric_results: Dict[str, MetricResult]) -> Dict[str, MetricResult]:
        """
        Calculate composite metrics from existing metric results.
        
        Args:
            metric_results: Dictionary of existing metric results
            
        Returns:
            Dictionary of composite metric results
        """
        composite_results = {}
        
        for composite_name, config in self.composite_metrics.items():
            components = config['components']
            weights = config['weights']
            method = config['aggregation_method']
            
            # Get component values
            component_values = []
            available_weights = []
            
            for i, component in enumerate(components):
                if component in metric_results:
                    component_values.append(metric_results[component].value)
                    available_weights.append(weights[i])
            
            if not component_values:
                continue
            
            # Calculate composite value
            if method == 'weighted_average':
                total_weight = sum(available_weights)
                if total_weight > 0:
                    composite_value = sum(
                        val * weight for val, weight in zip(component_values, available_weights)
                    ) / total_weight
                else:
                    composite_value = statistics.mean(component_values)
            elif method == 'geometric_mean':
                composite_value = math.prod(component_values) ** (1.0 / len(component_values))
            elif method == 'harmonic_mean':
                composite_value = len(component_values) / sum(1.0 / val for val in component_values if val > 0)
            else:
                composite_value = statistics.mean(component_values)
            
            composite_results[composite_name] = MetricResult(
                name=composite_name,
                value=composite_value,
                metric_type=MetricType.COMPOSITE,
                metadata={
                    'components': components,
                    'component_values': dict(zip(components, component_values)),
                    'weights': dict(zip(components, available_weights)),
                    'aggregation_method': method
                }
            )
        
        return composite_results
    
    def aggregate_metrics(self, 
                         metric_results_list: List[Dict[str, MetricResult]]) -> Dict[str, MetricResult]:
        """
        Aggregate metrics across multiple evaluations.
        
        Args:
            metric_results_list: List of metric result dictionaries
            
        Returns:
            Dictionary of aggregated metric results
        """
        if not metric_results_list:
            return {}
        
        # Collect all metric names
        all_metric_names = set()
        for results in metric_results_list:
            all_metric_names.update(results.keys())
        
        aggregated_results = {}
        
        for metric_name in all_metric_names:
            # Collect values for this metric across all evaluations
            values = []
            metric_type = None
            
            for results in metric_results_list:
                if metric_name in results:
                    values.append(results[metric_name].value)
                    if metric_type is None:
                        metric_type = results[metric_name].metric_type
            
            if not values:
                continue
            
            # Calculate aggregated statistics
            mean_value = statistics.mean(values)
            std_dev = statistics.stdev(values) if len(values) > 1 else 0.0
            
            aggregated_results[metric_name] = MetricResult(
                name=metric_name,
                value=mean_value,
                metric_type=metric_type or MetricType.STANDARD_NLP,
                metadata={
                    'individual_values': values,
                    'std_dev': std_dev,
                    'min_value': min(values),
                    'max_value': max(values),
                    'count': len(values),
                    'confidence_interval_95': self._calculate_confidence_interval(values, 0.95)
                }
            )
        
        return aggregated_results
    
    def generate_statistical_analysis(self, 
                                    metric_results: Dict[str, MetricResult]) -> Dict[str, Any]:
        """
        Generate statistical analysis of metric results.
        
        Args:
            metric_results: Dictionary of metric results
            
        Returns:
            Dictionary containing statistical analysis
        """
        analysis = {
            'summary': {},
            'correlations': {},
            'outliers': {},
            'trends': {},
            'recommendations': []
        }
        
        # Summary statistics
        values = [result.value for result in metric_results.values()]
        if values:
            analysis['summary'] = {
                'total_metrics': len(metric_results),
                'mean_score': statistics.mean(values),
                'median_score': statistics.median(values),
                'std_dev': statistics.stdev(values) if len(values) > 1 else 0.0,
                'min_score': min(values),
                'max_score': max(values),
                'score_range': max(values) - min(values) if values else 0.0
            }
        
        # Identify outliers using IQR method
        if len(values) >= 4:
            q1 = statistics.quantiles(values, n=4)[0]
            q3 = statistics.quantiles(values, n=4)[2]
            iqr = q3 - q1
            lower_bound = q1 - 1.5 * iqr
            upper_bound = q3 + 1.5 * iqr
            
            outliers = []
            for name, result in metric_results.items():
                if result.value < lower_bound or result.value > upper_bound:
                    outliers.append({
                        'metric': name,
                        'value': result.value,
                        'type': 'low' if result.value < lower_bound else 'high'
                    })
            
            analysis['outliers'] = outliers
        
        # Generate recommendations
        recommendations = []
        
        # Low performance recommendations
        low_performers = [
            name for name, result in metric_results.items() 
            if result.value < 0.3
        ]
        if low_performers:
            recommendations.append({
                'type': 'improvement',
                'message': f"Low performance detected in: {', '.join(low_performers)}",
                'metrics': low_performers
            })
        
        # High variance recommendations
        high_variance_metrics = [
            name for name, result in metric_results.items()
            if result.metadata.get('std_dev', 0) > 0.2
        ]
        if high_variance_metrics:
            recommendations.append({
                'type': 'consistency',
                'message': f"High variance detected in: {', '.join(high_variance_metrics)}",
                'metrics': high_variance_metrics
            })
        
        analysis['recommendations'] = recommendations
        
        return analysis
    
    # Standard NLP Metric Calculators
    
    def _calculate_bleu(self, prediction: str, reference: str, **kwargs) -> float:
        """Calculate BLEU score."""
        if not NLTK_AVAILABLE:
            return self._simple_bleu(prediction, reference)
        
        try:
            pred_tokens = word_tokenize(prediction.lower())
            ref_tokens = word_tokenize(reference.lower())
            
            smoothing = SmoothingFunction().method1
            score = sentence_bleu([ref_tokens], pred_tokens, smoothing_function=smoothing)
            return score
        except Exception:
            return self._simple_bleu(prediction, reference)
    
    def _simple_bleu(self, prediction: str, reference: str) -> float:
        """Simple BLEU implementation without NLTK."""
        pred_words = prediction.lower().split()
        ref_words = reference.lower().split()
        
        if not pred_words or not ref_words:
            return 0.0
        
        # Calculate n-gram precision for n=1,2,3,4
        precisions = []
        for n in range(1, 5):
            pred_ngrams = [tuple(pred_words[i:i+n]) for i in range(len(pred_words)-n+1)]
            ref_ngrams = [tuple(ref_words[i:i+n]) for i in range(len(ref_words)-n+1)]
            
            if not pred_ngrams:
                precisions.append(0.0)
                continue
            
            matches = sum(min(pred_ngrams.count(ngram), ref_ngrams.count(ngram)) 
                         for ngram in set(pred_ngrams))
            precision = matches / len(pred_ngrams)
            precisions.append(precision)
        
        # Geometric mean of precisions
        if all(p > 0 for p in precisions):
            bleu = math.prod(precisions) ** (1.0 / len(precisions))
        else:
            bleu = 0.0
        
        # Brevity penalty
        bp = min(1.0, math.exp(1 - len(ref_words) / len(pred_words))) if pred_words else 0.0
        
        return bleu * bp
    
    def _calculate_rouge_1(self, prediction: str, reference: str, **kwargs) -> float:
        """Calculate ROUGE-1 score."""
        if ROUGE_AVAILABLE:
            try:
                scores = self.rouge_scorer.score(reference, prediction)
                return scores['rouge1'].fmeasure
            except Exception:
                pass
        
        return self._simple_rouge_n(prediction, reference, n=1)
    
    def _calculate_rouge_2(self, prediction: str, reference: str, **kwargs) -> float:
        """Calculate ROUGE-2 score."""
        if ROUGE_AVAILABLE:
            try:
                scores = self.rouge_scorer.score(reference, prediction)
                return scores['rouge2'].fmeasure
            except Exception:
                pass
        
        return self._simple_rouge_n(prediction, reference, n=2)
    
    def _calculate_rouge_l(self, prediction: str, reference: str, **kwargs) -> float:
        """Calculate ROUGE-L score."""
        if ROUGE_AVAILABLE:
            try:
                scores = self.rouge_scorer.score(reference, prediction)
                return scores['rougeL'].fmeasure
            except Exception:
                pass
        
        return self._simple_rouge_l(prediction, reference)
    
    def _simple_rouge_n(self, prediction: str, reference: str, n: int) -> float:
        """Simple ROUGE-n implementation."""
        pred_words = prediction.lower().split()
        ref_words = reference.lower().split()
        
        if len(ref_words) < n:
            return 0.0
        
        pred_ngrams = [tuple(pred_words[i:i+n]) for i in range(len(pred_words)-n+1)]
        ref_ngrams = [tuple(ref_words[i:i+n]) for i in range(len(ref_words)-n+1)]
        
        if not ref_ngrams:
            return 0.0
        
        matches = sum(min(pred_ngrams.count(ngram), ref_ngrams.count(ngram)) 
                     for ngram in set(ref_ngrams))
        
        recall = matches / len(ref_ngrams)
        precision = matches / len(pred_ngrams) if pred_ngrams else 0.0
        
        if recall + precision == 0:
            return 0.0
        
        f1 = 2 * recall * precision / (recall + precision)
        return f1
    
    def _simple_rouge_l(self, prediction: str, reference: str) -> float:
        """Simple ROUGE-L implementation using LCS."""
        pred_words = prediction.lower().split()
        ref_words = reference.lower().split()
        
        lcs_length = self._lcs_length(pred_words, ref_words)
        
        if not ref_words or not pred_words:
            return 0.0
        
        recall = lcs_length / len(ref_words)
        precision = lcs_length / len(pred_words)
        
        if recall + precision == 0:
            return 0.0
        
        f1 = 2 * recall * precision / (recall + precision)
        return f1
    
    def _lcs_length(self, seq1: List[str], seq2: List[str]) -> int:
        """Calculate longest common subsequence length."""
        m, n = len(seq1), len(seq2)
        dp = [[0] * (n + 1) for _ in range(m + 1)]
        
        for i in range(1, m + 1):
            for j in range(1, n + 1):
                if seq1[i-1] == seq2[j-1]:
                    dp[i][j] = dp[i-1][j-1] + 1
                else:
                    dp[i][j] = max(dp[i-1][j], dp[i][j-1])
        
        return dp[m][n]
    
    def _calculate_meteor(self, prediction: str, reference: str, **kwargs) -> float:
        """Calculate METEOR score."""
        if NLTK_AVAILABLE:
            try:
                pred_tokens = word_tokenize(prediction.lower())
                ref_tokens = word_tokenize(reference.lower())
                return meteor_score([ref_tokens], pred_tokens)
            except Exception:
                pass
        
        # Simple fallback implementation
        return self._simple_meteor(prediction, reference)
    
    def _simple_meteor(self, prediction: str, reference: str) -> float:
        """Simple METEOR implementation."""
        pred_words = set(prediction.lower().split())
        ref_words = set(reference.lower().split())
        
        if not ref_words:
            return 0.0
        
        matches = len(pred_words & ref_words)
        precision = matches / len(pred_words) if pred_words else 0.0
        recall = matches / len(ref_words)
        
        if precision + recall == 0:
            return 0.0
        
        f_mean = (precision * recall) / (0.9 * precision + 0.1 * recall)
        return f_mean
    
    def _calculate_codebleu(self, prediction: str, reference: str, **kwargs) -> float:
        """Calculate CodeBLEU score."""
        if CODEBLEU_AVAILABLE:
            try:
                result = calc_codebleu([reference], [prediction], lang="python")
                return result['codebleu']
            except Exception:
                pass
        
        # Fallback to regular BLEU for code
        return self._calculate_bleu(prediction, reference)
    
    def _calculate_exact_match(self, prediction: str, reference: str, **kwargs) -> float:
        """Calculate exact match score."""
        return 1.0 if prediction.strip() == reference.strip() else 0.0
    
    def _calculate_edit_distance(self, prediction: str, reference: str, **kwargs) -> float:
        """Calculate normalized edit distance (1 - normalized Levenshtein distance)."""
        def levenshtein_distance(s1: str, s2: str) -> int:
            if len(s1) < len(s2):
                return levenshtein_distance(s2, s1)
            
            if len(s2) == 0:
                return len(s1)
            
            previous_row = list(range(len(s2) + 1))
            for i, c1 in enumerate(s1):
                current_row = [i + 1]
                for j, c2 in enumerate(s2):
                    insertions = previous_row[j + 1] + 1
                    deletions = current_row[j] + 1
                    substitutions = previous_row[j] + (c1 != c2)
                    current_row.append(min(insertions, deletions, substitutions))
                previous_row = current_row
            
            return previous_row[-1]
        
        distance = levenshtein_distance(prediction, reference)
        max_len = max(len(prediction), len(reference))
        
        if max_len == 0:
            return 1.0
        
        return 1.0 - (distance / max_len)
    
    # Code Quality Metric Calculators
    
    def _calculate_syntax_validity(self, code: str, language: str = 'python', **kwargs) -> float:
        """Calculate syntax validity score."""
        if language.lower() == 'python':
            try:
                ast.parse(code)
                return 1.0
            except SyntaxError:
                return 0.0
            except Exception:
                return 0.0
        
        # For other languages, use basic heuristics
        return self._basic_syntax_check(code, language)
    
    def _basic_syntax_check(self, code: str, language: str) -> float:
        """Basic syntax check for non-Python languages."""
        # Simple heuristics for common syntax issues
        score = 1.0
        
        # Check for balanced brackets
        brackets = {'(': ')', '[': ']', '{': '}'}
        stack = []
        
        for char in code:
            if char in brackets:
                stack.append(char)
            elif char in brackets.values():
                if not stack:
                    score -= 0.2
                    break
                expected = brackets[stack.pop()]
                if char != expected:
                    score -= 0.2
                    break
        
        if stack:
            score -= 0.2
        
        # Check for basic language-specific patterns
        if language.lower() in ['javascript', 'java', 'c++', 'c']:
            if code.count(';') == 0 and len(code.strip()) > 20:
                score -= 0.1  # Missing semicolons
        
        return max(0.0, score)
    
    def _calculate_cyclomatic_complexity(self, code: str, language: str = 'python', **kwargs) -> float:
        """Calculate cyclomatic complexity."""
        if language.lower() == 'python':
            return self._python_cyclomatic_complexity(code)
        
        return self._generic_cyclomatic_complexity(code)
    
    def _python_cyclomatic_complexity(self, code: str) -> float:
        """Calculate cyclomatic complexity for Python code."""
        try:
            tree = ast.parse(code)
            complexity = 1  # Base complexity
            
            for node in ast.walk(tree):
                if isinstance(node, (ast.If, ast.While, ast.For, ast.AsyncFor)):
                    complexity += 1
                elif isinstance(node, ast.ExceptHandler):
                    complexity += 1
                elif isinstance(node, (ast.And, ast.Or)):
                    complexity += 1
                elif isinstance(node, ast.comprehension):
                    complexity += 1
            
            return float(complexity)
        except Exception:
            return 1.0
    
    def _generic_cyclomatic_complexity(self, code: str) -> float:
        """Generic cyclomatic complexity calculation."""
        complexity = 1  # Base complexity
        
        # Count decision points
        decision_keywords = ['if', 'while', 'for', 'case', 'catch', '&&', '||', '?']
        
        for keyword in decision_keywords:
            complexity += code.lower().count(keyword)
        
        return float(complexity)
    
    def _calculate_security_score(self, code: str, language: str = 'python', **kwargs) -> float:
        """Calculate security score based on common vulnerabilities."""
        score = 1.0
        
        # Common security anti-patterns
        security_issues = {
            'eval': 0.3,
            'exec': 0.3,
            'input(': 0.1,
            'raw_input': 0.1,
            'subprocess.call': 0.2,
            'os.system': 0.3,
            'shell=True': 0.2,
            'pickle.loads': 0.2,
            'yaml.load': 0.1,
            'sql': 0.1,  # Potential SQL injection
            'SELECT': 0.1,
            'INSERT': 0.1,
            'UPDATE': 0.1,
            'DELETE': 0.1,
        }
        
        code_lower = code.lower()
        for pattern, penalty in security_issues.items():
            if pattern.lower() in code_lower:
                score -= penalty
        
        # Check for hardcoded secrets (simple patterns)
        secret_patterns = [
            r'password\s*=\s*["\'][^"\']+["\']',
            r'api_key\s*=\s*["\'][^"\']+["\']',
            r'secret\s*=\s*["\'][^"\']+["\']',
            r'token\s*=\s*["\'][^"\']+["\']',
        ]
        
        for pattern in secret_patterns:
            if re.search(pattern, code, re.IGNORECASE):
                score -= 0.2
        
        return max(0.0, score)
    
    def _calculate_code_style_score(self, code: str, language: str = 'python', **kwargs) -> float:
        """Calculate code style score."""
        if language.lower() == 'python':
            return self._python_style_score(code)
        
        return self._generic_style_score(code)
    
    def _python_style_score(self, code: str) -> float:
        """Calculate Python code style score."""
        score = 1.0
        lines = code.split('\n')
        
        # Check line length (PEP 8: max 79 characters)
        long_lines = sum(1 for line in lines if len(line) > 79)
        if long_lines > 0:
            score -= min(0.2, long_lines * 0.05)
        
        # Check for proper indentation (4 spaces)
        indented_lines = [line for line in lines if line.startswith(' ')]
        improper_indent = sum(1 for line in indented_lines 
                             if len(line) - len(line.lstrip()) % 4 != 0)
        if improper_indent > 0:
            score -= min(0.2, improper_indent * 0.05)
        
        # Check for function/class naming conventions
        if re.search(r'def [A-Z]', code):  # CamelCase function names
            score -= 0.1
        
        if re.search(r'class [a-z]', code):  # lowercase class names
            score -= 0.1
        
        # Check for proper spacing around operators
        if re.search(r'[a-zA-Z0-9][+\-*/=][a-zA-Z0-9]', code):
            score -= 0.1
        
        return max(0.0, score)
    
    def _generic_style_score(self, code: str) -> float:
        """Generic code style score."""
        score = 1.0
        
        # Basic style checks
        if not re.search(r'\n\s*\n', code) and len(code) > 100:
            score -= 0.1  # No blank lines in longer code
        
        # Check for consistent indentation
        lines = [line for line in code.split('\n') if line.strip()]
        if lines:
            indent_chars = set()
            for line in lines:
                if line.startswith(' ') or line.startswith('\t'):
                    indent_chars.add(line[0])
            
            if len(indent_chars) > 1:
                score -= 0.2  # Mixed indentation
        
        return max(0.0, score)
    
    def _calculate_performance_score(self, code: str, language: str = 'python', **kwargs) -> float:
        """Calculate performance score based on algorithmic patterns."""
        score = 1.0
        
        # Check for potential performance issues
        performance_issues = {
            'nested loops': len(re.findall(r'for.*for', code, re.DOTALL)) * 0.1,
            'string concatenation in loop': code.count('+=') * 0.05,
            'inefficient sorting': code.count('.sort()') * 0.02,
            'global variables': len(re.findall(r'global\s+\w+', code)) * 0.05,
        }
        
        for issue, penalty in performance_issues.items():
            score -= penalty
        
        # Bonus for good practices
        if 'list comprehension' in code or '[' in code and 'for' in code:
            score += 0.1
        
        if 'generator' in code or 'yield' in code:
            score += 0.1
        
        return max(0.0, min(1.0, score))
    
    # Functional Metric Calculators
    
    def _calculate_pass_at_k(self, code: str, test_cases: List[Dict[str, Any]], 
                           k: int = 1, language: str = 'python', **kwargs) -> float:
        """Calculate Pass@K metric."""
        if not test_cases:
            return 0.0
        
        # For simplicity, we'll simulate execution
        # In a real implementation, this would execute code in a sandbox
        passed_tests = 0
        
        for test_case in test_cases[:k]:  # Only consider first k test cases
            if self._simulate_test_execution(code, test_case, language):
                passed_tests += 1
        
        return passed_tests / min(len(test_cases), k)
    
    def _simulate_test_execution(self, code: str, test_case: Dict[str, Any], 
                               language: str) -> bool:
        """Simulate test execution (placeholder implementation)."""
        # This is a simplified simulation
        # Real implementation would use sandbox execution
        
        if language.lower() == 'python':
            try:
                # Basic syntax check
                ast.parse(code)
                
                # Check if code contains expected patterns from test case
                expected_output = test_case.get('expected_output', '')
                if expected_output and str(expected_output).lower() in code.lower():
                    return True
                
                # Check for function definition if test case specifies function name
                func_name = test_case.get('function_name', '')
                if func_name and f'def {func_name}' in code:
                    return True
                
                return False
            except Exception:
                return False
        
        return False  # Default for unsupported languages
    
    def _calculate_execution_success(self, code: str, test_cases: List[Dict[str, Any]], 
                                   language: str = 'python', **kwargs) -> float:
        """Calculate execution success rate."""
        if not test_cases:
            return 0.0
        
        successful_executions = sum(
            1 for test_case in test_cases
            if self._simulate_test_execution(code, test_case, language)
        )
        
        return successful_executions / len(test_cases)
    
    def _calculate_test_coverage(self, code: str, test_cases: List[Dict[str, Any]], 
                               language: str = 'python', **kwargs) -> float:
        """Calculate test coverage score."""
        # Simplified coverage calculation
        # Real implementation would use coverage tools
        
        if not code.strip():
            return 0.0
        
        # Count lines of code
        code_lines = [line.strip() for line in code.split('\n') if line.strip()]
        executable_lines = [line for line in code_lines 
                          if not line.startswith('#') and not line.startswith('"""')]
        
        if not executable_lines:
            return 0.0
        
        # Estimate coverage based on test cases
        coverage_score = min(len(test_cases) / len(executable_lines), 1.0)
        return coverage_score
    
    def _calculate_runtime_correctness(self, code: str, test_cases: List[Dict[str, Any]], 
                                     language: str = 'python', **kwargs) -> float:
        """Calculate runtime correctness score."""
        return self._calculate_execution_success(code, test_cases, language)
    
    def _calculate_memory_efficiency(self, code: str, test_cases: List[Dict[str, Any]], 
                                   language: str = 'python', **kwargs) -> float:
        """Calculate memory efficiency score."""
        score = 1.0
        
        # Check for memory-inefficient patterns
        inefficient_patterns = {
            'list(range(': 0.1,  # Should use range directly
            '.copy()': 0.05,     # Unnecessary copying
            'global': 0.1,       # Global variables
            'import *': 0.1,     # Import everything
        }
        
        for pattern, penalty in inefficient_patterns.items():
            if pattern in code:
                score -= penalty
        
        return max(0.0, score)
    
    # Multi-turn Metric Calculators
    
    def _calculate_context_retention(self, conversation_history: List[Dict[str, Any]], 
                                   turn_results: Dict[str, Any], 
                                   scenario_config: Optional[Dict[str, Any]] = None, 
                                   **kwargs) -> float:
        """Calculate context retention score across turns."""
        if len(conversation_history) < 2:
            return 0.5
        
        retention_scores = []
        
        for i in range(1, len(conversation_history)):
            current_turn = conversation_history[i]
            previous_turns = conversation_history[:i]
            
            # Calculate how well current turn references previous context
            current_content = current_turn.get('content', '').lower()
            previous_content = ' '.join([
                turn.get('content', '') for turn in previous_turns[-3:]  # Last 3 turns
            ]).lower()
            
            if not previous_content:
                retention_scores.append(0.5)
                continue
            
            # Simple word overlap metric
            current_words = set(current_content.split())
            previous_words = set(previous_content.split())
            
            if not previous_words:
                retention_scores.append(0.5)
                continue
            
            overlap = len(current_words & previous_words)
            retention_score = min(overlap / 20.0, 1.0)  # Normalize
            retention_scores.append(retention_score)
        
        return statistics.mean(retention_scores) if retention_scores else 0.5
    
    def _calculate_conversation_coherence(self, conversation_history: List[Dict[str, Any]], 
                                        turn_results: Dict[str, Any], 
                                        scenario_config: Optional[Dict[str, Any]] = None, 
                                        **kwargs) -> float:
        """Calculate conversation coherence score."""
        if len(conversation_history) < 2:
            return 0.5
        
        coherence_scores = []
        
        for i in range(1, len(conversation_history)):
            prev_turn = conversation_history[i-1]
            curr_turn = conversation_history[i]
            
            prev_content = prev_turn.get('content', '')
            curr_content = curr_turn.get('content', '')
            
            coherence = self._calculate_turn_coherence(prev_content, curr_content)
            coherence_scores.append(coherence)
        
        return statistics.mean(coherence_scores) if coherence_scores else 0.5
    
    def _calculate_turn_coherence(self, prev_content: str, curr_content: str) -> float:
        """Calculate coherence between two consecutive turns."""
        if not prev_content.strip() or not curr_content.strip():
            return 0.5
        
        # Check for explicit connection words
        connection_words = [
            'however', 'therefore', 'moreover', 'furthermore', 'additionally',
            'consequently', 'meanwhile', 'nevertheless', 'thus', 'hence',
            'building on', 'following up', 'as mentioned', 'previously'
        ]
        
        coherence_score = 0.5  # Base score
        
        curr_lower = curr_content.lower()
        for word in connection_words:
            if word in curr_lower:
                coherence_score += 0.1
                break
        
        # Check for topic continuity
        prev_words = set(prev_content.lower().split())
        curr_words = set(curr_content.lower().split())
        
        overlap = len(prev_words & curr_words)
        topic_continuity = min(overlap / 15.0, 0.3)  # Max 0.3 from topic continuity
        coherence_score += topic_continuity
        
        return min(coherence_score, 1.0)
    
    def _calculate_turn_quality(self, conversation_history: List[Dict[str, Any]], 
                              turn_results: Dict[str, Any], 
                              scenario_config: Optional[Dict[str, Any]] = None, 
                              **kwargs) -> float:
        """Calculate average turn quality."""
        if not turn_results:
            return 0.0
        
        quality_scores = []
        
        for turn_id, result in turn_results.items():
            response = result.get('response', '')
            
            # Calculate turn quality based on response characteristics
            quality = self._calculate_response_quality(response)
            quality_scores.append(quality)
        
        return statistics.mean(quality_scores) if quality_scores else 0.0
    
    def _calculate_response_quality(self, response: str) -> float:
        """Calculate quality of a single response."""
        if not response.strip():
            return 0.0
        
        quality_indicators = [
            len(response) > 50,  # Sufficient length
            response.count('.') > 1,  # Multiple sentences
            any(word in response.lower() for word in ['because', 'since', 'therefore']),  # Reasoning
            len(response.split()) > 20,  # Sufficient word count
            not response.lower().startswith("i don't"),  # Not a rejection
        ]
        
        return sum(quality_indicators) / len(quality_indicators)
    
    def _calculate_goal_achievement(self, conversation_history: List[Dict[str, Any]], 
                                  turn_results: Dict[str, Any], 
                                  scenario_config: Optional[Dict[str, Any]] = None, 
                                  **kwargs) -> float:
        """Calculate goal achievement score."""
        if not scenario_config:
            return 0.5
        
        # Look for completion indicators in the conversation
        all_content = ' '.join([
            turn.get('content', '') for turn in conversation_history
        ]).lower()
        
        completion_indicators = [
            'complete', 'finished', 'done', 'accomplished', 'achieved',
            'successful', 'resolved', 'solved', 'implemented'
        ]
        
        goal_score = 0.0
        for indicator in completion_indicators:
            if indicator in all_content:
                goal_score += 0.2
        
        # Check if all required turns were completed
        expected_turns = scenario_config.get('expected_turns', len(turn_results))
        completion_rate = len(turn_results) / expected_turns if expected_turns > 0 else 1.0
        
        return min((goal_score + completion_rate) / 2, 1.0)
    
    def _calculate_confidence_interval(self, values: List[float], confidence: float) -> Tuple[float, float]:
        """Calculate confidence interval for a list of values."""
        if len(values) < 2:
            return (0.0, 0.0)
        
        mean = statistics.mean(values)
        std_err = statistics.stdev(values) / math.sqrt(len(values))
        
        # Use t-distribution approximation (simplified)
        t_value = 1.96 if confidence == 0.95 else 2.576  # For 95% and 99%
        margin = t_value * std_err
        
        return (mean - margin, mean + margin)