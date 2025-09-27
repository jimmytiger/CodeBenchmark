"""
Analysis Engine for AI Evaluation System.

This module provides comprehensive statistical analysis capabilities including
trend identification, anomaly detection, cross-model performance comparison,
confidence intervals, and pattern recognition for evaluation results.
"""

import statistics
import math
import numpy as np
from typing import Dict, List, Any, Optional, Tuple, Union
from dataclasses import dataclass, field
from enum import Enum
from collections import defaultdict, Counter
import json
import time
from datetime import datetime, timedelta

from .metrics_engine import MetricResult, MetricType
from .composite_metrics import CompositeMetricsSystem, RealTimeMetricUpdate


class TrendType(Enum):
    """Types of trends that can be identified."""
    INCREASING = "increasing"
    DECREASING = "decreasing"
    STABLE = "stable"
    VOLATILE = "volatile"
    CYCLICAL = "cyclical"
    UNKNOWN = "unknown"


class AnomalyType(Enum):
    """Types of anomalies that can be detected."""
    OUTLIER_HIGH = "outlier_high"
    OUTLIER_LOW = "outlier_low"
    SUDDEN_CHANGE = "sudden_change"
    PATTERN_BREAK = "pattern_break"
    PERFORMANCE_DROP = "performance_drop"
    PERFORMANCE_SPIKE = "performance_spike"


@dataclass
class TrendAnalysis:
    """Results of trend analysis."""
    trend_type: TrendType
    confidence: float
    slope: float
    r_squared: float
    start_value: float
    end_value: float
    change_rate: float
    metadata: Dict[str, Any] = field(default_factory=dict)


@dataclass
class AnomalyDetection:
    """Results of anomaly detection."""
    anomaly_type: AnomalyType
    severity: float
    confidence: float
    affected_metrics: List[str]
    timestamp: Optional[float] = None
    description: str = ""
    metadata: Dict[str, Any] = field(default_factory=dict)


@dataclass
class StatisticalSignificance:
    """Statistical significance test results."""
    test_name: str
    statistic: float
    p_value: float
    is_significant: bool
    confidence_level: float
    effect_size: Optional[float] = None
    metadata: Dict[str, Any] = field(default_factory=dict)


@dataclass
class ConfidenceInterval:
    """Confidence interval calculation results."""
    lower_bound: float
    upper_bound: float
    confidence_level: float
    mean: float
    margin_of_error: float
    sample_size: int


@dataclass
class PatternRecognition:
    """Pattern recognition results."""
    pattern_type: str
    strength: float
    frequency: Optional[float] = None
    phase: Optional[float] = None
    amplitude: Optional[float] = None
    description: str = ""
    metadata: Dict[str, Any] = field(default_factory=dict)


@dataclass
class PerformanceComparison:
    """Cross-model performance comparison results."""
    model_rankings: List[Dict[str, Any]]
    statistical_tests: Dict[str, StatisticalSignificance]
    effect_sizes: Dict[str, float]
    confidence_intervals: Dict[str, ConfidenceInterval]
    recommendations: List[str]


class AnalysisEngine:
    """
    Comprehensive statistical analysis engine for AI evaluation results.
    
    Provides trend identification, anomaly detection, cross-model comparison,
    confidence intervals, and pattern recognition capabilities.
    """
    
    def __init__(self, composite_system: Optional[CompositeMetricsSystem] = None):
        """Initialize the analysis engine."""
        self.composite_system = composite_system
        
        # Historical data storage
        self.evaluation_history: List[Dict[str, Any]] = []
        self.metric_history: Dict[str, List[Tuple[float, float]]] = defaultdict(list)  # (timestamp, value)
        
        # Analysis cache
        self.trend_cache: Dict[str, TrendAnalysis] = {}
        self.anomaly_cache: List[AnomalyDetection] = []
        self.pattern_cache: Dict[str, PatternRecognition] = {}
        
        # Configuration
        self.confidence_levels = [0.90, 0.95, 0.99]
        self.anomaly_threshold = 2.0  # Standard deviations
        self.trend_window_size = 10  # Minimum points for trend analysis
        
        # Statistical test configurations
        self.significance_level = 0.05
        self.effect_size_thresholds = {
            'small': 0.2,
            'medium': 0.5,
            'large': 0.8
        }
    
    def add_evaluation_result(self, 
                            evaluation_result: Dict[str, Any],
                            timestamp: Optional[float] = None):
        """
        Add evaluation result to historical data.
        
        Args:
            evaluation_result: Evaluation result dictionary
            timestamp: Optional timestamp (defaults to current time)
        """
        if timestamp is None:
            timestamp = time.time()
        
        # Add timestamp to result
        evaluation_result['timestamp'] = timestamp
        evaluation_result['datetime'] = datetime.fromtimestamp(timestamp)
        
        # Store in history
        self.evaluation_history.append(evaluation_result)
        
        # Update metric history
        metrics = evaluation_result.get('metrics', {})
        for metric_name, metric_result in metrics.items():
            value = metric_result.value if hasattr(metric_result, 'value') else metric_result
            self.metric_history[metric_name].append((timestamp, value))
        
        # Clear caches that might be affected
        self._clear_analysis_cache()
    
    def perform_trend_analysis(self, 
                             metric_name: str,
                             window_size: Optional[int] = None) -> Optional[TrendAnalysis]:
        """
        Perform trend analysis on a specific metric.
        
        Args:
            metric_name: Name of the metric to analyze
            window_size: Optional window size (defaults to configured value)
            
        Returns:
            TrendAnalysis object or None if insufficient data
        """
        if window_size is None:
            window_size = self.trend_window_size
        
        # Check cache first
        cache_key = f"{metric_name}_{window_size}"
        if cache_key in self.trend_cache:
            return self.trend_cache[cache_key]
        
        # Get metric history
        if metric_name not in self.metric_history:
            return None
        
        history = self.metric_history[metric_name]
        if len(history) < window_size:
            return None
        
        # Use most recent window
        recent_history = history[-window_size:]
        timestamps = [t for t, v in recent_history]
        values = [v for t, v in recent_history]
        
        # Use sequential indices instead of timestamps for regression
        indices = list(range(len(values)))
        
        # Perform linear regression
        slope, r_squared = self._calculate_linear_regression(indices, values)
        
        # Determine trend type
        trend_type = self._classify_trend(slope, r_squared, values)
        
        # Calculate confidence based on R-squared and data consistency
        confidence = self._calculate_trend_confidence(r_squared, values)
        
        # Calculate change rate
        start_value = values[0]
        end_value = values[-1]
        time_span = timestamps[-1] - timestamps[0]
        change_rate = (end_value - start_value) / len(values) if len(values) > 1 else 0.0
        
        trend_analysis = TrendAnalysis(
            trend_type=trend_type,
            confidence=confidence,
            slope=slope,
            r_squared=r_squared,
            start_value=start_value,
            end_value=end_value,
            change_rate=change_rate,
            metadata={
                'window_size': window_size,
                'data_points': len(values),
                'time_span': time_span,
                'metric_name': metric_name
            }
        )
        
        # Cache result
        self.trend_cache[cache_key] = trend_analysis
        
        return trend_analysis
    
    def detect_anomalies(self, 
                        metric_name: Optional[str] = None,
                        lookback_window: int = 50) -> List[AnomalyDetection]:
        """
        Detect anomalies in metric data.
        
        Args:
            metric_name: Optional specific metric to analyze (analyzes all if None)
            lookback_window: Number of recent data points to analyze
            
        Returns:
            List of detected anomalies
        """
        anomalies = []
        
        metrics_to_analyze = [metric_name] if metric_name else list(self.metric_history.keys())
        
        for metric in metrics_to_analyze:
            if metric not in self.metric_history:
                continue
            
            history = self.metric_history[metric]
            if len(history) < 10:  # Need minimum data for anomaly detection
                continue
            
            # Use recent window
            recent_history = history[-lookback_window:] if len(history) > lookback_window else history
            timestamps = [t for t, v in recent_history]
            values = [v for t, v in recent_history]
            
            # Statistical outlier detection
            mean_val = statistics.mean(values)
            std_val = statistics.stdev(values) if len(values) > 1 else 0.0
            
            if std_val > 0:
                for i, (timestamp, value) in enumerate(recent_history):
                    z_score = abs(value - mean_val) / std_val
                    
                    if z_score > self.anomaly_threshold:
                        anomaly_type = AnomalyType.OUTLIER_HIGH if value > mean_val else AnomalyType.OUTLIER_LOW
                        severity = min(z_score / self.anomaly_threshold, 5.0)  # Cap at 5x threshold
                        confidence = min(z_score / 3.0, 1.0)  # Confidence based on z-score
                        
                        anomalies.append(AnomalyDetection(
                            anomaly_type=anomaly_type,
                            severity=severity,
                            confidence=confidence,
                            affected_metrics=[metric],
                            timestamp=timestamp,
                            description=f"Statistical outlier in {metric}: {value:.3f} (z-score: {z_score:.2f})",
                            metadata={
                                'z_score': z_score,
                                'mean': mean_val,
                                'std_dev': std_val,
                                'value': value
                            }
                        ))
            
            # Sudden change detection
            if len(values) >= 5:
                for i in range(2, len(values) - 2):
                    before_window = values[max(0, i-2):i]
                    after_window = values[i+1:min(len(values), i+3)]
                    
                    if before_window and after_window:
                        before_mean = statistics.mean(before_window)
                        after_mean = statistics.mean(after_window)
                        
                        change_magnitude = abs(after_mean - before_mean)
                        relative_change = change_magnitude / (before_mean + 1e-8)  # Avoid division by zero
                        
                        if relative_change > 0.5:  # 50% change threshold
                            anomalies.append(AnomalyDetection(
                                anomaly_type=AnomalyType.SUDDEN_CHANGE,
                                severity=min(relative_change, 3.0),
                                confidence=min(relative_change / 0.5, 1.0),
                                affected_metrics=[metric],
                                timestamp=timestamps[i],
                                description=f"Sudden change in {metric}: {relative_change:.1%} change",
                                metadata={
                                    'before_mean': before_mean,
                                    'after_mean': after_mean,
                                    'relative_change': relative_change
                                }
                            ))
        
        # Update anomaly cache
        self.anomaly_cache.extend(anomalies)
        
        # Keep only recent anomalies in cache
        cutoff_time = time.time() - (7 * 24 * 3600)  # 7 days
        self.anomaly_cache = [a for a in self.anomaly_cache if a.timestamp and a.timestamp > cutoff_time]
        
        return anomalies
    
    def compare_model_performance(self, 
                                model_results: Dict[str, Dict[str, Any]],
                                metrics_to_compare: Optional[List[str]] = None) -> PerformanceComparison:
        """
        Compare performance across multiple models with statistical significance testing.
        
        Args:
            model_results: Dictionary mapping model names to their results
            metrics_to_compare: Optional list of metrics to compare
            
        Returns:
            PerformanceComparison object with detailed analysis
        """
        if not model_results or len(model_results) < 2:
            return PerformanceComparison(
                model_rankings=[],
                statistical_tests={},
                effect_sizes={},
                confidence_intervals={},
                recommendations=["Need at least 2 models for comparison"]
            )
        
        # Extract metrics from all models
        all_metrics = set()
        for model_name, results in model_results.items():
            metrics = results.get('metrics', {})
            all_metrics.update(metrics.keys())
        
        if metrics_to_compare:
            all_metrics = set(metrics_to_compare) & all_metrics
        
        # Calculate rankings for each metric
        model_rankings = []
        statistical_tests = {}
        effect_sizes = {}
        confidence_intervals = {}
        
        for metric_name in all_metrics:
            # Collect metric values for each model
            model_values = {}
            for model_name, results in model_results.items():
                metrics = results.get('metrics', {})
                if metric_name in metrics:
                    metric_result = metrics[metric_name]
                    value = metric_result.value if hasattr(metric_result, 'value') else metric_result
                    model_values[model_name] = value
            
            if len(model_values) < 2:
                continue
            
            # Rank models for this metric
            ranked_models = sorted(model_values.items(), key=lambda x: x[1], reverse=True)
            
            model_rankings.append({
                'metric': metric_name,
                'rankings': [{'model': model, 'score': score, 'rank': i+1} 
                           for i, (model, score) in enumerate(ranked_models)]
            })
            
            # Statistical significance testing (simplified t-test for top 2 models)
            if len(ranked_models) >= 2:
                top_model_score = ranked_models[0][1]
                second_model_score = ranked_models[1][1]
                
                # Simplified statistical test (in practice, would need multiple samples)
                effect_size = abs(top_model_score - second_model_score) / max(top_model_score, second_model_score, 0.001)
                
                # Mock p-value calculation (in practice, would use proper statistical tests)
                p_value = max(0.001, 1.0 - effect_size)
                is_significant = p_value < self.significance_level
                
                statistical_tests[metric_name] = StatisticalSignificance(
                    test_name="simplified_comparison",
                    statistic=effect_size,
                    p_value=p_value,
                    is_significant=is_significant,
                    confidence_level=1.0 - self.significance_level,
                    effect_size=effect_size,
                    metadata={
                        'top_model': ranked_models[0][0],
                        'top_score': top_model_score,
                        'second_model': ranked_models[1][0],
                        'second_score': second_model_score
                    }
                )
                
                effect_sizes[metric_name] = effect_size
                
                # Calculate confidence intervals (simplified)
                all_scores = list(model_values.values())
                mean_score = statistics.mean(all_scores)
                std_score = statistics.stdev(all_scores) if len(all_scores) > 1 else 0.0
                
                for confidence_level in self.confidence_levels:
                    margin_of_error = self._calculate_margin_of_error(std_score, len(all_scores), confidence_level)
                    
                    confidence_intervals[f"{metric_name}_{confidence_level}"] = ConfidenceInterval(
                        lower_bound=mean_score - margin_of_error,
                        upper_bound=mean_score + margin_of_error,
                        confidence_level=confidence_level,
                        mean=mean_score,
                        margin_of_error=margin_of_error,
                        sample_size=len(all_scores)
                    )
        
        # Generate recommendations
        recommendations = self._generate_comparison_recommendations(
            model_rankings, statistical_tests, effect_sizes
        )
        
        return PerformanceComparison(
            model_rankings=model_rankings,
            statistical_tests=statistical_tests,
            effect_sizes=effect_sizes,
            confidence_intervals=confidence_intervals,
            recommendations=recommendations
        )
    
    def calculate_confidence_intervals(self, 
                                     metric_values: List[float],
                                     confidence_levels: Optional[List[float]] = None) -> Dict[float, ConfidenceInterval]:
        """
        Calculate confidence intervals for metric values.
        
        Args:
            metric_values: List of metric values
            confidence_levels: Optional list of confidence levels
            
        Returns:
            Dictionary mapping confidence levels to ConfidenceInterval objects
        """
        if not metric_values:
            return {}
        
        if confidence_levels is None:
            confidence_levels = self.confidence_levels
        
        mean_val = statistics.mean(metric_values)
        std_val = statistics.stdev(metric_values) if len(metric_values) > 1 else 0.0
        n = len(metric_values)
        
        intervals = {}
        
        for confidence_level in confidence_levels:
            margin_of_error = self._calculate_margin_of_error(std_val, n, confidence_level)
            
            intervals[confidence_level] = ConfidenceInterval(
                lower_bound=mean_val - margin_of_error,
                upper_bound=mean_val + margin_of_error,
                confidence_level=confidence_level,
                mean=mean_val,
                margin_of_error=margin_of_error,
                sample_size=n
            )
        
        return intervals
    
    def identify_performance_patterns(self, 
                                    metric_name: str,
                                    pattern_types: Optional[List[str]] = None) -> List[PatternRecognition]:
        """
        Identify patterns in performance data.
        
        Args:
            metric_name: Name of the metric to analyze
            pattern_types: Optional list of pattern types to look for
            
        Returns:
            List of identified patterns
        """
        if metric_name not in self.metric_history:
            return []
        
        history = self.metric_history[metric_name]
        if len(history) < 10:
            return []
        
        timestamps = [t for t, v in history]
        values = [v for t, v in history]
        
        patterns = []
        
        # Cyclical pattern detection
        if not pattern_types or 'cyclical' in pattern_types:
            cyclical_pattern = self._detect_cyclical_pattern(values)
            if cyclical_pattern:
                patterns.append(cyclical_pattern)
        
        # Seasonal pattern detection
        if not pattern_types or 'seasonal' in pattern_types:
            seasonal_pattern = self._detect_seasonal_pattern(timestamps, values)
            if seasonal_pattern:
                patterns.append(seasonal_pattern)
        
        # Performance degradation pattern
        if not pattern_types or 'degradation' in pattern_types:
            degradation_pattern = self._detect_degradation_pattern(values)
            if degradation_pattern:
                patterns.append(degradation_pattern)
        
        # Performance improvement pattern
        if not pattern_types or 'improvement' in pattern_types:
            improvement_pattern = self._detect_improvement_pattern(values)
            if improvement_pattern:
                patterns.append(improvement_pattern)
        
        return patterns
    
    def generate_comprehensive_analysis(self, 
                                      evaluation_results: List[Dict[str, Any]]) -> Dict[str, Any]:
        """
        Generate comprehensive statistical analysis of evaluation results.
        
        Args:
            evaluation_results: List of evaluation results
            
        Returns:
            Comprehensive analysis dictionary
        """
        analysis = {
            'summary_statistics': {},
            'trend_analysis': {},
            'anomaly_detection': {},
            'pattern_recognition': {},
            'performance_distribution': {},
            'correlation_analysis': {},
            'recommendations': [],
            'metadata': {
                'analysis_timestamp': time.time(),
                'total_evaluations': len(evaluation_results),
                'analysis_engine_version': '1.0.0'
            }
        }
        
        # Add evaluation results to history
        for result in evaluation_results:
            self.add_evaluation_result(result)
        
        # Extract all metrics
        all_metrics = set()
        for result in evaluation_results:
            metrics = result.get('metrics', {})
            all_metrics.update(metrics.keys())
        
        # Summary statistics for each metric
        for metric_name in all_metrics:
            values = []
            for result in evaluation_results:
                metrics = result.get('metrics', {})
                if metric_name in metrics:
                    metric_result = metrics[metric_name]
                    value = metric_result.value if hasattr(metric_result, 'value') else metric_result
                    values.append(value)
            
            if values:
                analysis['summary_statistics'][metric_name] = {
                    'count': len(values),
                    'mean': statistics.mean(values),
                    'median': statistics.median(values),
                    'std_dev': statistics.stdev(values) if len(values) > 1 else 0.0,
                    'min': min(values),
                    'max': max(values),
                    'range': max(values) - min(values),
                    'quartiles': statistics.quantiles(values, n=4) if len(values) >= 4 else [],
                    'confidence_intervals': self.calculate_confidence_intervals(values)
                }
        
        # Trend analysis for each metric
        for metric_name in all_metrics:
            trend = self.perform_trend_analysis(metric_name)
            if trend:
                analysis['trend_analysis'][metric_name] = {
                    'trend_type': trend.trend_type.value,
                    'confidence': trend.confidence,
                    'slope': trend.slope,
                    'r_squared': trend.r_squared,
                    'change_rate': trend.change_rate,
                    'start_value': trend.start_value,
                    'end_value': trend.end_value
                }
        
        # Anomaly detection
        anomalies = self.detect_anomalies()
        analysis['anomaly_detection'] = {
            'total_anomalies': len(anomalies),
            'anomalies_by_type': Counter(a.anomaly_type.value for a in anomalies),
            'recent_anomalies': [
                {
                    'type': a.anomaly_type.value,
                    'severity': a.severity,
                    'confidence': a.confidence,
                    'metrics': a.affected_metrics,
                    'description': a.description
                }
                for a in anomalies[-10:]  # Last 10 anomalies
            ]
        }
        
        # Pattern recognition
        for metric_name in all_metrics:
            patterns = self.identify_performance_patterns(metric_name)
            if patterns:
                analysis['pattern_recognition'][metric_name] = [
                    {
                        'pattern_type': p.pattern_type,
                        'strength': p.strength,
                        'description': p.description,
                        'frequency': p.frequency,
                        'amplitude': p.amplitude
                    }
                    for p in patterns
                ]
        
        # Performance distribution analysis
        for metric_name in all_metrics:
            if metric_name in analysis['summary_statistics']:
                stats = analysis['summary_statistics'][metric_name]
                analysis['performance_distribution'][metric_name] = {
                    'distribution_type': self._classify_distribution(stats),
                    'skewness': self._calculate_skewness(stats),
                    'performance_bands': self._calculate_performance_bands(stats)
                }
        
        # Simple correlation analysis
        if len(all_metrics) >= 2:
            correlations = {}
            metric_list = list(all_metrics)
            
            for i, metric1 in enumerate(metric_list):
                for metric2 in metric_list[i+1:]:
                    values1 = []
                    values2 = []
                    
                    for result in evaluation_results:
                        metrics = result.get('metrics', {})
                        if metric1 in metrics and metric2 in metrics:
                            val1 = metrics[metric1].value if hasattr(metrics[metric1], 'value') else metrics[metric1]
                            val2 = metrics[metric2].value if hasattr(metrics[metric2], 'value') else metrics[metric2]
                            values1.append(val1)
                            values2.append(val2)
                    
                    if len(values1) >= 3:  # Need at least 3 points for correlation
                        correlation = self._calculate_correlation(values1, values2)
                        correlations[f"{metric1}_vs_{metric2}"] = {
                            'correlation': correlation,
                            'strength': self._classify_correlation_strength(correlation),
                            'sample_size': len(values1)
                        }
            
            analysis['correlation_analysis'] = correlations
        
        # Generate recommendations
        analysis['recommendations'] = self._generate_comprehensive_recommendations(analysis)
        
        return analysis
    
    # Helper methods
    
    def _clear_analysis_cache(self):
        """Clear analysis caches."""
        self.trend_cache.clear()
        self.pattern_cache.clear()
    
    def _calculate_linear_regression(self, x_values: List[float], y_values: List[float]) -> Tuple[float, float]:
        """Calculate linear regression slope and R-squared."""
        if len(x_values) != len(y_values) or len(x_values) < 2:
            return 0.0, 0.0
        
        n = len(x_values)
        sum_x = sum(x_values)
        sum_y = sum(y_values)
        sum_xy = sum(x * y for x, y in zip(x_values, y_values))
        sum_x2 = sum(x * x for x in x_values)
        sum_y2 = sum(y * y for y in y_values)
        
        # Calculate slope
        denominator = n * sum_x2 - sum_x * sum_x
        if denominator == 0:
            return 0.0, 0.0
        
        slope = (n * sum_xy - sum_x * sum_y) / denominator
        
        # Calculate R-squared
        y_mean = sum_y / n
        ss_tot = sum((y - y_mean) ** 2 for y in y_values)
        
        if ss_tot == 0:
            return slope, 1.0
        
        # Calculate predicted values
        intercept = (sum_y - slope * sum_x) / n
        ss_res = sum((y - (slope * x + intercept)) ** 2 for x, y in zip(x_values, y_values))
        
        r_squared = 1 - (ss_res / ss_tot)
        
        return slope, max(0.0, r_squared)
    
    def _classify_trend(self, slope: float, r_squared: float, values: List[float]) -> TrendType:
        """Classify trend type based on slope and R-squared."""
        if r_squared < 0.3:
            # Low correlation, check for volatility
            if len(values) > 1:
                std_dev = statistics.stdev(values)
                mean_val = statistics.mean(values)
                cv = std_dev / mean_val if mean_val != 0 else 0
                
                if cv > 0.3:
                    return TrendType.VOLATILE
                else:
                    return TrendType.STABLE
            return TrendType.UNKNOWN
        
        # Strong correlation, classify by slope
        if abs(slope) < 1e-6:
            return TrendType.STABLE
        elif slope > 0:
            return TrendType.INCREASING
        else:
            return TrendType.DECREASING
    
    def _calculate_trend_confidence(self, r_squared: float, values: List[float]) -> float:
        """Calculate confidence in trend analysis."""
        base_confidence = r_squared
        
        # Adjust for sample size
        sample_size_factor = min(len(values) / 20.0, 1.0)  # Full confidence at 20+ points
        
        # Adjust for data consistency
        if len(values) > 1:
            cv = statistics.stdev(values) / statistics.mean(values) if statistics.mean(values) != 0 else 1.0
            consistency_factor = max(0.1, 1.0 - cv)
        else:
            consistency_factor = 0.5
        
        return base_confidence * sample_size_factor * consistency_factor
    
    def _calculate_margin_of_error(self, std_dev: float, sample_size: int, confidence_level: float) -> float:
        """Calculate margin of error for confidence interval."""
        if sample_size <= 1:
            return 0.0
        
        # Use t-distribution critical value (approximated)
        if confidence_level == 0.90:
            t_critical = 1.645
        elif confidence_level == 0.95:
            t_critical = 1.96
        elif confidence_level == 0.99:
            t_critical = 2.576
        else:
            # Approximate for other confidence levels
            t_critical = 1.96
        
        standard_error = std_dev / math.sqrt(sample_size)
        return t_critical * standard_error
    
    def _calculate_correlation(self, values1: List[float], values2: List[float]) -> float:
        """Calculate Pearson correlation coefficient."""
        if len(values1) != len(values2) or len(values1) < 2:
            return 0.0
        
        mean1 = statistics.mean(values1)
        mean2 = statistics.mean(values2)
        
        numerator = sum((x - mean1) * (y - mean2) for x, y in zip(values1, values2))
        
        sum_sq1 = sum((x - mean1) ** 2 for x in values1)
        sum_sq2 = sum((y - mean2) ** 2 for y in values2)
        
        denominator = math.sqrt(sum_sq1 * sum_sq2)
        
        if denominator == 0:
            return 0.0
        
        return numerator / denominator
    
    def _detect_cyclical_pattern(self, values: List[float]) -> Optional[PatternRecognition]:
        """Detect cyclical patterns in data."""
        if len(values) < 8:  # Need minimum data for cycle detection
            return None
        
        # Simple cycle detection using autocorrelation
        max_lag = min(len(values) // 3, 20)
        best_correlation = 0.0
        best_period = 0
        
        for lag in range(2, max_lag):
            if lag >= len(values):
                break
            
            # Calculate autocorrelation at this lag
            correlation = self._calculate_autocorrelation(values, lag)
            
            if correlation > best_correlation:
                best_correlation = correlation
                best_period = lag
        
        if best_correlation > 0.5:  # Threshold for cyclical pattern
            return PatternRecognition(
                pattern_type="cyclical",
                strength=best_correlation,
                frequency=1.0 / best_period if best_period > 0 else 0.0,
                description=f"Cyclical pattern detected with period {best_period}",
                metadata={'period': best_period, 'correlation': best_correlation}
            )
        
        return None
    
    def _calculate_autocorrelation(self, values: List[float], lag: int) -> float:
        """Calculate autocorrelation at given lag."""
        if lag >= len(values) or lag <= 0:
            return 0.0
        
        n = len(values) - lag
        if n <= 1:
            return 0.0
        
        values1 = values[:-lag]
        values2 = values[lag:]
        
        return self._calculate_correlation(values1, values2)
    
    def _detect_seasonal_pattern(self, timestamps: List[float], values: List[float]) -> Optional[PatternRecognition]:
        """Detect seasonal patterns in time series data."""
        # Simplified seasonal detection - would need more sophisticated methods in practice
        if len(values) < 12:  # Need at least a year of data for seasonal patterns
            return None
        
        # This is a placeholder - real seasonal detection would analyze time-based patterns
        return None
    
    def _detect_degradation_pattern(self, values: List[float]) -> Optional[PatternRecognition]:
        """Detect performance degradation patterns."""
        if len(values) < 5:
            return None
        
        # Check for consistent decline
        recent_values = values[-5:]
        if len(recent_values) >= 3:
            slope, r_squared = self._calculate_linear_regression(
                list(range(len(recent_values))), recent_values
            )
            
            if slope < -0.01 and r_squared > 0.6:  # Declining trend
                strength = min(abs(slope) * 10, 1.0)  # Scale strength
                return PatternRecognition(
                    pattern_type="degradation",
                    strength=strength,
                    description=f"Performance degradation detected (slope: {slope:.4f})",
                    metadata={'slope': slope, 'r_squared': r_squared}
                )
        
        return None
    
    def _detect_improvement_pattern(self, values: List[float]) -> Optional[PatternRecognition]:
        """Detect performance improvement patterns."""
        if len(values) < 5:
            return None
        
        # Check for consistent improvement
        recent_values = values[-5:]
        if len(recent_values) >= 3:
            slope, r_squared = self._calculate_linear_regression(
                list(range(len(recent_values))), recent_values
            )
            
            if slope > 0.01 and r_squared > 0.6:  # Improving trend
                strength = min(slope * 10, 1.0)  # Scale strength
                return PatternRecognition(
                    pattern_type="improvement",
                    strength=strength,
                    description=f"Performance improvement detected (slope: {slope:.4f})",
                    metadata={'slope': slope, 'r_squared': r_squared}
                )
        
        return None
    
    def _classify_distribution(self, stats: Dict[str, Any]) -> str:
        """Classify the distribution type based on statistics."""
        mean = stats['mean']
        median = stats['median']
        std_dev = stats['std_dev']
        
        if std_dev == 0:
            return "constant"
        
        # Simple classification based on mean vs median
        skew_ratio = abs(mean - median) / std_dev
        
        if skew_ratio < 0.1:
            return "normal"
        elif mean > median:
            return "right_skewed"
        else:
            return "left_skewed"
    
    def _calculate_skewness(self, stats: Dict[str, Any]) -> float:
        """Calculate skewness measure."""
        mean = stats['mean']
        median = stats['median']
        std_dev = stats['std_dev']
        
        if std_dev == 0:
            return 0.0
        
        # Simplified skewness measure
        return (mean - median) / std_dev
    
    def _calculate_performance_bands(self, stats: Dict[str, Any]) -> Dict[str, float]:
        """Calculate performance bands (excellent, good, fair, poor)."""
        mean = stats['mean']
        std_dev = stats['std_dev']
        
        return {
            'excellent': mean + std_dev,
            'good': mean + 0.5 * std_dev,
            'fair': mean - 0.5 * std_dev,
            'poor': mean - std_dev
        }
    
    def _classify_correlation_strength(self, correlation: float) -> str:
        """Classify correlation strength."""
        abs_corr = abs(correlation)
        
        if abs_corr >= 0.8:
            return "very_strong"
        elif abs_corr >= 0.6:
            return "strong"
        elif abs_corr >= 0.4:
            return "moderate"
        elif abs_corr >= 0.2:
            return "weak"
        else:
            return "very_weak"
    
    def _generate_comparison_recommendations(self, 
                                           rankings: List[Dict[str, Any]],
                                           statistical_tests: Dict[str, StatisticalSignificance],
                                           effect_sizes: Dict[str, float]) -> List[str]:
        """Generate recommendations based on model comparison."""
        recommendations = []
        
        # Identify consistently top-performing models
        model_scores = defaultdict(list)
        for ranking in rankings:
            for model_rank in ranking['rankings']:
                model_scores[model_rank['model']].append(model_rank['rank'])
        
        # Find models with consistently good performance
        consistent_performers = []
        for model, ranks in model_scores.items():
            avg_rank = statistics.mean(ranks)
            if avg_rank <= 2.0:  # Average rank of 2 or better
                consistent_performers.append((model, avg_rank))
        
        if consistent_performers:
            consistent_performers.sort(key=lambda x: x[1])
            best_model = consistent_performers[0][0]
            recommendations.append(f"Model '{best_model}' shows consistently strong performance across metrics")
        
        # Identify metrics with significant differences
        significant_metrics = [
            metric for metric, test in statistical_tests.items() 
            if test.is_significant
        ]
        
        if significant_metrics:
            recommendations.append(f"Significant performance differences found in: {', '.join(significant_metrics)}")
        
        # Identify large effect sizes
        large_effects = [
            metric for metric, effect in effect_sizes.items()
            if effect > self.effect_size_thresholds['large']
        ]
        
        if large_effects:
            recommendations.append(f"Large effect sizes detected in: {', '.join(large_effects)}")
        
        return recommendations
    
    def _generate_comprehensive_recommendations(self, analysis: Dict[str, Any]) -> List[str]:
        """Generate comprehensive recommendations based on analysis."""
        recommendations = []
        
        # Trend-based recommendations
        trend_analysis = analysis.get('trend_analysis', {})
        declining_metrics = [
            metric for metric, trend in trend_analysis.items()
            if trend['trend_type'] == 'decreasing' and trend['confidence'] > 0.7
        ]
        
        if declining_metrics:
            recommendations.append(f"Declining performance trends detected in: {', '.join(declining_metrics)}")
        
        # Anomaly-based recommendations
        anomaly_detection = analysis.get('anomaly_detection', {})
        if anomaly_detection.get('total_anomalies', 0) > 5:
            recommendations.append("High number of anomalies detected - investigate data quality and model stability")
        
        # Performance distribution recommendations
        performance_dist = analysis.get('performance_distribution', {})
        high_variance_metrics = [
            metric for metric, dist in performance_dist.items()
            if abs(dist.get('skewness', 0)) > 1.0
        ]
        
        if high_variance_metrics:
            recommendations.append(f"High variance detected in: {', '.join(high_variance_metrics)} - consider consistency improvements")
        
        # Correlation-based recommendations
        correlation_analysis = analysis.get('correlation_analysis', {})
        strong_correlations = [
            pair for pair, corr_info in correlation_analysis.items()
            if corr_info['strength'] in ['strong', 'very_strong']
        ]
        
        if strong_correlations:
            recommendations.append(f"Strong correlations found between metrics: {', '.join(strong_correlations)}")
        
        return recommendations