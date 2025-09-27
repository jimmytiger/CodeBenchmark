"""
Composite Metrics System for AI Evaluation Engine.

This module provides configurable weight systems, real-time metric calculation,
and comparative analysis tools for comprehensive evaluation.
"""

import time
import threading
import statistics
from typing import Dict, List, Any, Optional, Callable, Tuple
from dataclasses import dataclass, field
from enum import Enum
import json
from collections import defaultdict, deque
import math

from .metrics_engine import MetricsEngine, MetricResult, MetricType
from .scenario_metrics import ScenarioSpecificMetrics, ScenarioDomain


class AggregationMethod(Enum):
    """Methods for aggregating composite metrics."""
    WEIGHTED_AVERAGE = "weighted_average"
    GEOMETRIC_MEAN = "geometric_mean"
    HARMONIC_MEAN = "harmonic_mean"
    MIN = "min"
    MAX = "max"
    MEDIAN = "median"
    PERCENTILE = "percentile"
    CUSTOM = "custom"


class RankingMethod(Enum):
    """Methods for ranking evaluations."""
    COMPOSITE_SCORE = "composite_score"
    WEIGHTED_RANK = "weighted_rank"
    PARETO_OPTIMAL = "pareto_optimal"
    MULTI_CRITERIA = "multi_criteria"


@dataclass
class WeightConfig:
    """Configuration for metric weights."""
    metric_weights: Dict[str, float]
    domain_weights: Dict[str, float] = field(default_factory=dict)
    scenario_weights: Dict[str, float] = field(default_factory=dict)
    temporal_decay: float = 0.0  # For time-based weight decay
    adaptive_weights: bool = False  # Enable adaptive weight adjustment


@dataclass
class CompositeMetricConfig:
    """Configuration for composite metrics."""
    name: str
    component_metrics: List[str]
    weight_config: WeightConfig
    aggregation_method: AggregationMethod
    normalization_method: str = "min_max"  # min_max, z_score, none
    threshold_config: Optional[Dict[str, float]] = None
    real_time_enabled: bool = False
    update_frequency: float = 1.0  # seconds


@dataclass
class RealTimeMetricUpdate:
    """Real-time metric update data."""
    metric_name: str
    value: float
    timestamp: float
    evaluation_id: str
    metadata: Dict[str, Any] = field(default_factory=dict)


class CompositeMetricsSystem:
    """
    Comprehensive composite metrics system with configurable weights,
    real-time calculation, and comparative analysis.
    """
    
    def __init__(self, base_engine: MetricsEngine, scenario_metrics: ScenarioSpecificMetrics):
        """Initialize the composite metrics system."""
        self.base_engine = base_engine
        self.scenario_metrics = scenario_metrics
        
        # Composite metric configurations
        self.composite_configs: Dict[str, CompositeMetricConfig] = {}
        
        # Weight configurations
        self.weight_configs: Dict[str, WeightConfig] = {}
        
        # Real-time system
        self.real_time_enabled = False
        self.real_time_updates: deque = deque(maxlen=10000)
        self.real_time_callbacks: List[Callable] = []
        self.real_time_thread: Optional[threading.Thread] = None
        self.real_time_stop_event = threading.Event()
        
        # Ranking and comparison
        self.evaluation_history: List[Dict[str, Any]] = []
        self.ranking_cache: Dict[str, List[Dict[str, Any]]] = {}
        
        # Performance tracking
        self.performance_metrics: Dict[str, List[float]] = defaultdict(list)
        
        # Initialize default configurations
        self._initialize_default_configs()
    
    def _initialize_default_configs(self):
        """Initialize default composite metric configurations."""
        
        # Overall code quality composite
        self.register_composite_metric(CompositeMetricConfig(
            name="overall_code_quality",
            component_metrics=[
                "syntax_valid", "code_style_score", "security_score",
                "code_completeness", "algorithm_efficiency", "code_readability"
            ],
            weight_config=WeightConfig(
                metric_weights={
                    "syntax_valid": 0.25,
                    "code_style_score": 0.15,
                    "security_score": 0.20,
                    "code_completeness": 0.20,
                    "algorithm_efficiency": 0.15,
                    "code_readability": 0.05
                }
            ),
            aggregation_method=AggregationMethod.WEIGHTED_AVERAGE,
            real_time_enabled=True
        ))
        
        # Trading strategy quality composite
        self.register_composite_metric(CompositeMetricConfig(
            name="trading_strategy_quality",
            component_metrics=[
                "strategy_coherence", "risk_management_quality", "market_analysis_depth",
                "backtesting_rigor", "execution_efficiency", "quantitative_rigor"
            ],
            weight_config=WeightConfig(
                metric_weights={
                    "strategy_coherence": 0.20,
                    "risk_management_quality": 0.25,
                    "market_analysis_depth": 0.15,
                    "backtesting_rigor": 0.20,
                    "execution_efficiency": 0.10,
                    "quantitative_rigor": 0.10
                }
            ),
            aggregation_method=AggregationMethod.WEIGHTED_AVERAGE
        ))
        
        # Multi-turn conversation quality composite
        self.register_composite_metric(CompositeMetricConfig(
            name="conversation_quality",
            component_metrics=[
                "context_retention", "conversation_coherence", "turn_quality", "goal_achievement"
            ],
            weight_config=WeightConfig(
                metric_weights={
                    "context_retention": 0.30,
                    "conversation_coherence": 0.25,
                    "turn_quality": 0.25,
                    "goal_achievement": 0.20
                }
            ),
            aggregation_method=AggregationMethod.WEIGHTED_AVERAGE,
            real_time_enabled=True
        ))
        
        # Overall evaluation quality (meta-composite)
        self.register_composite_metric(CompositeMetricConfig(
            name="overall_evaluation_score",
            component_metrics=[
                "overall_code_quality", "conversation_quality", "exact_match", "bleu"
            ],
            weight_config=WeightConfig(
                metric_weights={
                    "overall_code_quality": 0.40,
                    "conversation_quality": 0.30,
                    "exact_match": 0.15,
                    "bleu": 0.15
                },
                adaptive_weights=True
            ),
            aggregation_method=AggregationMethod.WEIGHTED_AVERAGE,
            real_time_enabled=True
        ))
    
    def register_composite_metric(self, config: CompositeMetricConfig):
        """Register a new composite metric configuration."""
        self.composite_configs[config.name] = config
        
        # Register with base engine
        self.base_engine.create_composite_metric(
            config.name,
            config.component_metrics,
            list(config.weight_config.metric_weights.values()),
            config.aggregation_method.value
        )
    
    def calculate_composite_metrics(self, 
                                  metric_results: Dict[str, MetricResult],
                                  evaluation_id: Optional[str] = None,
                                  context: Optional[Dict[str, Any]] = None) -> Dict[str, MetricResult]:
        """
        Calculate composite metrics with advanced aggregation and weighting.
        
        Args:
            metric_results: Base metric results
            evaluation_id: Optional evaluation identifier
            context: Optional context for adaptive weighting
            
        Returns:
            Dictionary of composite metric results
        """
        composite_results = {}
        
        for config_name, config in self.composite_configs.items():
            try:
                # Get component values
                component_values = {}
                available_components = []
                
                for component in config.component_metrics:
                    if component in metric_results:
                        component_values[component] = metric_results[component].value
                        available_components.append(component)
                    elif component in composite_results:
                        # Allow nested composites
                        component_values[component] = composite_results[component].value
                        available_components.append(component)
                
                if not available_components:
                    continue
                
                # Apply adaptive weighting if enabled
                weights = self._get_adaptive_weights(config, component_values, context)
                
                # Normalize values if specified
                normalized_values = self._normalize_values(
                    component_values, config.normalization_method
                )
                
                # Calculate composite value
                composite_value = self._aggregate_values(
                    normalized_values, weights, config.aggregation_method
                )
                
                # Apply thresholds if configured
                if config.threshold_config:
                    composite_value = self._apply_thresholds(composite_value, config.threshold_config)
                
                # Create result
                composite_results[config_name] = MetricResult(
                    name=config_name,
                    value=composite_value,
                    metric_type=MetricType.COMPOSITE,
                    metadata={
                        'components': available_components,
                        'component_values': component_values,
                        'weights': weights,
                        'aggregation_method': config.aggregation_method.value,
                        'normalization_method': config.normalization_method,
                        'evaluation_id': evaluation_id
                    }
                )
                
                # Real-time update if enabled
                if config.real_time_enabled and evaluation_id:
                    self._emit_real_time_update(
                        config_name, composite_value, evaluation_id, context
                    )
                
            except Exception as e:
                composite_results[config_name] = MetricResult(
                    name=config_name,
                    value=0.0,
                    metric_type=MetricType.COMPOSITE,
                    metadata={'error': str(e)}
                )
        
        return composite_results
    
    def _get_adaptive_weights(self, 
                            config: CompositeMetricConfig,
                            component_values: Dict[str, float],
                            context: Optional[Dict[str, Any]]) -> Dict[str, float]:
        """Get adaptive weights based on context and performance."""
        base_weights = config.weight_config.metric_weights
        
        if not config.weight_config.adaptive_weights:
            return base_weights
        
        adaptive_weights = base_weights.copy()
        
        # Adjust weights based on component performance
        for component, value in component_values.items():
            if component in adaptive_weights:
                # Boost weight for high-performing components
                if value > 0.8:
                    adaptive_weights[component] *= 1.1
                elif value < 0.3:
                    adaptive_weights[component] *= 0.9
        
        # Adjust weights based on context
        if context:
            domain = context.get('domain')
            scenario_type = context.get('scenario_type')
            
            # Domain-specific weight adjustments
            if domain and domain in config.weight_config.domain_weights:
                domain_multiplier = config.weight_config.domain_weights[domain]
                for component in adaptive_weights:
                    adaptive_weights[component] *= domain_multiplier
            
            # Scenario-specific weight adjustments
            if scenario_type and scenario_type in config.weight_config.scenario_weights:
                scenario_multiplier = config.weight_config.scenario_weights[scenario_type]
                for component in adaptive_weights:
                    adaptive_weights[component] *= scenario_multiplier
        
        # Normalize weights to sum to 1
        total_weight = sum(adaptive_weights.values())
        if total_weight > 0:
            adaptive_weights = {k: v / total_weight for k, v in adaptive_weights.items()}
        
        return adaptive_weights
    
    def _normalize_values(self, 
                         values: Dict[str, float], 
                         method: str) -> Dict[str, float]:
        """Normalize metric values."""
        if method == "none" or not values:
            return values
        
        value_list = list(values.values())
        
        if method == "min_max":
            min_val = min(value_list)
            max_val = max(value_list)
            if max_val == min_val:
                return {k: 1.0 for k in values}
            return {k: (v - min_val) / (max_val - min_val) for k, v in values.items()}
        
        elif method == "z_score":
            mean_val = statistics.mean(value_list)
            std_val = statistics.stdev(value_list) if len(value_list) > 1 else 1.0
            if std_val == 0:
                return {k: 0.0 for k in values}
            return {k: (v - mean_val) / std_val for k, v in values.items()}
        
        return values
    
    def _aggregate_values(self, 
                         values: Dict[str, float],
                         weights: Dict[str, float],
                         method: AggregationMethod) -> float:
        """Aggregate values using specified method."""
        if not values:
            return 0.0
        
        # Filter to available components
        available_values = []
        available_weights = []
        
        for component, value in values.items():
            if component in weights:
                available_values.append(value)
                available_weights.append(weights[component])
        
        if not available_values:
            return 0.0
        
        if method == AggregationMethod.WEIGHTED_AVERAGE:
            total_weight = sum(available_weights)
            if total_weight == 0:
                return statistics.mean(available_values)
            return sum(v * w for v, w in zip(available_values, available_weights)) / total_weight
        
        elif method == AggregationMethod.GEOMETRIC_MEAN:
            # Ensure all values are positive for geometric mean
            positive_values = [max(v, 0.001) for v in available_values]
            return math.prod(positive_values) ** (1.0 / len(positive_values))
        
        elif method == AggregationMethod.HARMONIC_MEAN:
            # Ensure all values are positive for harmonic mean
            positive_values = [max(v, 0.001) for v in available_values]
            return len(positive_values) / sum(1.0 / v for v in positive_values)
        
        elif method == AggregationMethod.MIN:
            return min(available_values)
        
        elif method == AggregationMethod.MAX:
            return max(available_values)
        
        elif method == AggregationMethod.MEDIAN:
            return statistics.median(available_values)
        
        else:
            return statistics.mean(available_values)
    
    def _apply_thresholds(self, value: float, thresholds: Dict[str, float]) -> float:
        """Apply threshold transformations to the value."""
        if 'min_threshold' in thresholds and value < thresholds['min_threshold']:
            value = thresholds['min_threshold']
        
        if 'max_threshold' in thresholds and value > thresholds['max_threshold']:
            value = thresholds['max_threshold']
        
        if 'penalty_threshold' in thresholds and value < thresholds['penalty_threshold']:
            penalty = thresholds.get('penalty_factor', 0.5)
            value *= penalty
        
        return value
    
    def start_real_time_monitoring(self, update_frequency: float = 1.0):
        """Start real-time metric monitoring."""
        if self.real_time_enabled:
            return
        
        self.real_time_enabled = True
        self.real_time_stop_event.clear()
        
        self.real_time_thread = threading.Thread(
            target=self._real_time_monitor_loop,
            args=(update_frequency,),
            daemon=True
        )
        self.real_time_thread.start()
    
    def stop_real_time_monitoring(self):
        """Stop real-time metric monitoring."""
        if not self.real_time_enabled:
            return
        
        self.real_time_enabled = False
        self.real_time_stop_event.set()
        
        if self.real_time_thread:
            self.real_time_thread.join(timeout=5.0)
    
    def _real_time_monitor_loop(self, update_frequency: float):
        """Real-time monitoring loop."""
        while not self.real_time_stop_event.wait(update_frequency):
            try:
                # Process any pending updates
                self._process_real_time_updates()
                
                # Update performance metrics
                self._update_performance_metrics()
                
            except Exception as e:
                # Log error but continue monitoring
                pass
    
    def _emit_real_time_update(self, 
                             metric_name: str, 
                             value: float, 
                             evaluation_id: str,
                             context: Optional[Dict[str, Any]]):
        """Emit a real-time metric update."""
        update = RealTimeMetricUpdate(
            metric_name=metric_name,
            value=value,
            timestamp=time.time(),
            evaluation_id=evaluation_id,
            metadata=context or {}
        )
        
        self.real_time_updates.append(update)
        
        # Trigger callbacks
        for callback in self.real_time_callbacks:
            try:
                callback(update)
            except Exception:
                pass
    
    def add_real_time_callback(self, callback: Callable[[RealTimeMetricUpdate], None]):
        """Add a callback for real-time updates."""
        self.real_time_callbacks.append(callback)
    
    def _process_real_time_updates(self):
        """Process pending real-time updates."""
        # This could trigger alerts, update dashboards, etc.
        pass
    
    def _update_performance_metrics(self):
        """Update performance tracking metrics."""
        # Track system performance metrics
        current_time = time.time()
        
        # Example: track update frequency
        self.performance_metrics['update_frequency'].append(current_time)
        
        # Keep only recent data (last 1000 updates)
        for metric_name in self.performance_metrics:
            if len(self.performance_metrics[metric_name]) > 1000:
                self.performance_metrics[metric_name] = \
                    self.performance_metrics[metric_name][-1000:]
    
    def rank_evaluations(self, 
                        evaluation_results: List[Dict[str, Any]],
                        ranking_method: RankingMethod = RankingMethod.COMPOSITE_SCORE,
                        primary_metric: str = "overall_evaluation_score") -> List[Dict[str, Any]]:
        """
        Rank evaluations based on composite metrics.
        
        Args:
            evaluation_results: List of evaluation results
            ranking_method: Method to use for ranking
            primary_metric: Primary metric for ranking
            
        Returns:
            Ranked list of evaluations
        """
        if not evaluation_results:
            return []
        
        if ranking_method == RankingMethod.COMPOSITE_SCORE:
            return self._rank_by_composite_score(evaluation_results, primary_metric)
        elif ranking_method == RankingMethod.WEIGHTED_RANK:
            return self._rank_by_weighted_score(evaluation_results)
        elif ranking_method == RankingMethod.PARETO_OPTIMAL:
            return self._rank_by_pareto_optimal(evaluation_results)
        elif ranking_method == RankingMethod.MULTI_CRITERIA:
            return self._rank_by_multi_criteria(evaluation_results)
        else:
            return evaluation_results
    
    def _rank_by_composite_score(self, 
                               evaluations: List[Dict[str, Any]], 
                               metric_name: str) -> List[Dict[str, Any]]:
        """Rank by single composite score."""
        def get_score(evaluation):
            metrics = evaluation.get('metrics', {})
            if metric_name in metrics:
                return metrics[metric_name].value if hasattr(metrics[metric_name], 'value') else metrics[metric_name]
            return 0.0
        
        return sorted(evaluations, key=get_score, reverse=True)
    
    def _rank_by_weighted_score(self, evaluations: List[Dict[str, Any]]) -> List[Dict[str, Any]]:
        """Rank by weighted combination of multiple metrics."""
        # Use overall_evaluation_score if available, otherwise calculate
        return self._rank_by_composite_score(evaluations, "overall_evaluation_score")
    
    def _rank_by_pareto_optimal(self, evaluations: List[Dict[str, Any]]) -> List[Dict[str, Any]]:
        """Rank by Pareto optimality."""
        # Simplified Pareto ranking - in practice would be more sophisticated
        return self._rank_by_composite_score(evaluations, "overall_evaluation_score")
    
    def _rank_by_multi_criteria(self, evaluations: List[Dict[str, Any]]) -> List[Dict[str, Any]]:
        """Rank using multi-criteria decision analysis."""
        # Simplified MCDA - in practice would use TOPSIS, AHP, etc.
        return self._rank_by_composite_score(evaluations, "overall_evaluation_score")
    
    def generate_comparative_analysis(self, 
                                    evaluation_results: List[Dict[str, Any]]) -> Dict[str, Any]:
        """
        Generate comparative analysis of evaluations.
        
        Args:
            evaluation_results: List of evaluation results
            
        Returns:
            Comprehensive comparative analysis
        """
        if not evaluation_results:
            return {}
        
        analysis = {
            'summary': {},
            'rankings': {},
            'performance_distribution': {},
            'metric_correlations': {},
            'outlier_analysis': {},
            'trend_analysis': {},
            'recommendations': []
        }
        
        # Extract all metrics
        all_metrics = {}
        for eval_result in evaluation_results:
            metrics = eval_result.get('metrics', {})
            for metric_name, metric_value in metrics.items():
                if metric_name not in all_metrics:
                    all_metrics[metric_name] = []
                
                value = metric_value.value if hasattr(metric_value, 'value') else metric_value
                all_metrics[metric_name].append(value)
        
        # Summary statistics
        analysis['summary'] = {
            'total_evaluations': len(evaluation_results),
            'metrics_analyzed': len(all_metrics),
            'metric_statistics': {}
        }
        
        for metric_name, values in all_metrics.items():
            if values:
                analysis['summary']['metric_statistics'][metric_name] = {
                    'mean': statistics.mean(values),
                    'median': statistics.median(values),
                    'std_dev': statistics.stdev(values) if len(values) > 1 else 0.0,
                    'min': min(values),
                    'max': max(values),
                    'range': max(values) - min(values)
                }
        
        # Rankings
        for method in RankingMethod:
            try:
                ranked = self.rank_evaluations(evaluation_results, method)
                analysis['rankings'][method.value] = [
                    {
                        'rank': i + 1,
                        'evaluation_id': result.get('evaluation_id', f'eval_{i}'),
                        'score': self._get_primary_score(result)
                    }
                    for i, result in enumerate(ranked[:10])  # Top 10
                ]
            except Exception:
                pass
        
        # Performance distribution
        for metric_name, values in all_metrics.items():
            if len(values) >= 4:
                try:
                    quartiles = statistics.quantiles(values, n=4)
                    analysis['performance_distribution'][metric_name] = {
                        'q1': quartiles[0],
                        'q2': quartiles[1],
                        'q3': quartiles[2],
                        'iqr': quartiles[2] - quartiles[0]
                    }
                except Exception:
                    pass
        
        # Simple correlation analysis
        metric_names = list(all_metrics.keys())
        if len(metric_names) >= 2:
            correlations = {}
            for i, metric1 in enumerate(metric_names):
                for metric2 in metric_names[i+1:]:
                    try:
                        values1 = all_metrics[metric1]
                        values2 = all_metrics[metric2]
                        if len(values1) == len(values2) and len(values1) > 1:
                            corr = self._calculate_correlation(values1, values2)
                            correlations[f"{metric1}_vs_{metric2}"] = corr
                    except Exception:
                        pass
            
            analysis['metric_correlations'] = correlations
        
        # Generate recommendations
        recommendations = []
        
        # Low performance recommendations
        for metric_name, stats in analysis['summary']['metric_statistics'].items():
            if stats['mean'] < 0.3:
                recommendations.append({
                    'type': 'improvement',
                    'metric': metric_name,
                    'message': f"Low average performance in {metric_name} ({stats['mean']:.3f})",
                    'suggestion': f"Focus on improving {metric_name} across evaluations"
                })
        
        # High variance recommendations
        for metric_name, stats in analysis['summary']['metric_statistics'].items():
            if stats['std_dev'] > 0.3:
                recommendations.append({
                    'type': 'consistency',
                    'metric': metric_name,
                    'message': f"High variance in {metric_name} (σ={stats['std_dev']:.3f})",
                    'suggestion': f"Work on consistency in {metric_name}"
                })
        
        analysis['recommendations'] = recommendations
        
        return analysis
    
    def _get_primary_score(self, evaluation_result: Dict[str, Any]) -> float:
        """Get primary score from evaluation result."""
        metrics = evaluation_result.get('metrics', {})
        
        # Try composite metrics first
        for composite_name in ['overall_evaluation_score', 'overall_code_quality', 'conversation_quality']:
            if composite_name in metrics:
                metric = metrics[composite_name]
                return metric.value if hasattr(metric, 'value') else metric
        
        # Fall back to any available metric
        if metrics:
            first_metric = next(iter(metrics.values()))
            return first_metric.value if hasattr(first_metric, 'value') else first_metric
        
        return 0.0
    
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
    
    def get_real_time_metrics(self, 
                            evaluation_id: Optional[str] = None,
                            metric_name: Optional[str] = None,
                            time_window: Optional[float] = None) -> List[RealTimeMetricUpdate]:
        """
        Get real-time metric updates.
        
        Args:
            evaluation_id: Filter by evaluation ID
            metric_name: Filter by metric name
            time_window: Time window in seconds (from now)
            
        Returns:
            List of matching real-time updates
        """
        current_time = time.time()
        updates = list(self.real_time_updates)
        
        # Apply filters
        if evaluation_id:
            updates = [u for u in updates if u.evaluation_id == evaluation_id]
        
        if metric_name:
            updates = [u for u in updates if u.metric_name == metric_name]
        
        if time_window:
            cutoff_time = current_time - time_window
            updates = [u for u in updates if u.timestamp >= cutoff_time]
        
        return sorted(updates, key=lambda u: u.timestamp, reverse=True)
    
    def export_configuration(self) -> Dict[str, Any]:
        """Export current configuration for persistence."""
        return {
            'composite_configs': {
                name: {
                    'name': config.name,
                    'component_metrics': config.component_metrics,
                    'weight_config': {
                        'metric_weights': config.weight_config.metric_weights,
                        'domain_weights': config.weight_config.domain_weights,
                        'scenario_weights': config.weight_config.scenario_weights,
                        'temporal_decay': config.weight_config.temporal_decay,
                        'adaptive_weights': config.weight_config.adaptive_weights
                    },
                    'aggregation_method': config.aggregation_method.value,
                    'normalization_method': config.normalization_method,
                    'threshold_config': config.threshold_config,
                    'real_time_enabled': config.real_time_enabled,
                    'update_frequency': config.update_frequency
                }
                for name, config in self.composite_configs.items()
            },
            'weight_configs': {
                name: {
                    'metric_weights': config.metric_weights,
                    'domain_weights': config.domain_weights,
                    'scenario_weights': config.scenario_weights,
                    'temporal_decay': config.temporal_decay,
                    'adaptive_weights': config.adaptive_weights
                }
                for name, config in self.weight_configs.items()
            }
        }
    
    def import_configuration(self, config_data: Dict[str, Any]):
        """Import configuration from exported data."""
        # Import composite configs
        if 'composite_configs' in config_data:
            for name, config_dict in config_data['composite_configs'].items():
                weight_config = WeightConfig(
                    metric_weights=config_dict['weight_config']['metric_weights'],
                    domain_weights=config_dict['weight_config'].get('domain_weights', {}),
                    scenario_weights=config_dict['weight_config'].get('scenario_weights', {}),
                    temporal_decay=config_dict['weight_config'].get('temporal_decay', 0.0),
                    adaptive_weights=config_dict['weight_config'].get('adaptive_weights', False)
                )
                
                composite_config = CompositeMetricConfig(
                    name=config_dict['name'],
                    component_metrics=config_dict['component_metrics'],
                    weight_config=weight_config,
                    aggregation_method=AggregationMethod(config_dict['aggregation_method']),
                    normalization_method=config_dict.get('normalization_method', 'min_max'),
                    threshold_config=config_dict.get('threshold_config'),
                    real_time_enabled=config_dict.get('real_time_enabled', False),
                    update_frequency=config_dict.get('update_frequency', 1.0)
                )
                
                self.register_composite_metric(composite_config)
        
        # Import weight configs
        if 'weight_configs' in config_data:
            for name, weight_dict in config_data['weight_configs'].items():
                weight_config = WeightConfig(
                    metric_weights=weight_dict['metric_weights'],
                    domain_weights=weight_dict.get('domain_weights', {}),
                    scenario_weights=weight_dict.get('scenario_weights', {}),
                    temporal_decay=weight_dict.get('temporal_decay', 0.0),
                    adaptive_weights=weight_dict.get('adaptive_weights', False)
                )
                self.weight_configs[name] = weight_config