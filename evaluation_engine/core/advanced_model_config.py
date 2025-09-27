"""
Advanced Model Configuration Management System

This module provides comprehensive model configuration management with:
- Dynamic parameter tuning based on task requirements
- API rate limiting and retry strategies
- Performance monitoring and auto-scaling
- A/B testing for configuration optimization
- Cost optimization and budget management
"""

import asyncio
import json
import logging
import time
import statistics
from dataclasses import dataclass, field, asdict
from typing import Any, Dict, List, Optional, Tuple, Callable, Union
from enum import Enum
from collections import defaultdict, deque
import threading
from concurrent.futures import ThreadPoolExecutor

from .model_adapters import ModelAdapter, ModelType, RateLimitConfig, ModelCapabilities, ModelMetrics


eval_logger = logging.getLogger(__name__)


class TaskType(Enum):
    """Types of evaluation tasks."""
    CODE_COMPLETION = "code_completion"
    BUG_FIX = "bug_fix"
    FUNCTION_GENERATION = "function_generation"
    CODE_TRANSLATION = "code_translation"
    ALGORITHM_IMPLEMENTATION = "algorithm_implementation"
    API_DESIGN = "api_design"
    SYSTEM_DESIGN = "system_design"
    DATABASE_DESIGN = "database_design"
    SECURITY = "security"
    PERFORMANCE_OPTIMIZATION = "performance_optimization"
    DOCUMENTATION = "documentation"
    TESTING = "testing"
    FULL_STACK = "full_stack"
    MULTI_TURN = "multi_turn"


class OptimizationStrategy(Enum):
    """Strategies for parameter optimization."""
    PERFORMANCE = "performance"  # Optimize for best results
    COST = "cost"  # Optimize for lowest cost
    SPEED = "speed"  # Optimize for fastest response
    BALANCED = "balanced"  # Balance all factors


@dataclass
class ModelConfiguration:
    """Comprehensive model configuration."""
    model_id: str
    model_type: ModelType
    
    # Generation parameters
    temperature: float = 0.7
    max_tokens: int = 2048
    top_p: float = 1.0
    top_k: int = 50
    frequency_penalty: float = 0.0
    presence_penalty: float = 0.0
    stop_sequences: List[str] = field(default_factory=list)
    
    # API configuration
    api_key: Optional[str] = None
    api_base: Optional[str] = None
    timeout: float = 30.0
    
    # Rate limiting
    rate_limit_config: RateLimitConfig = field(default_factory=RateLimitConfig)
    
    # Task-specific optimizations
    task_optimizations: Dict[TaskType, Dict[str, Any]] = field(default_factory=dict)
    
    # Cost management
    max_cost_per_request: float = 1.0
    daily_budget: float = 100.0
    
    # Performance targets
    target_response_time: float = 5.0
    target_success_rate: float = 0.95
    
    # A/B testing
    ab_test_variant: Optional[str] = None
    ab_test_weight: float = 1.0
    
    def to_dict(self) -> Dict[str, Any]:
        """Convert to dictionary."""
        return asdict(self)
    
    @classmethod
    def from_dict(cls, data: Dict[str, Any]) -> 'ModelConfiguration':
        """Create from dictionary."""
        # Handle nested objects
        if 'rate_limit_config' in data and isinstance(data['rate_limit_config'], dict):
            data['rate_limit_config'] = RateLimitConfig(**data['rate_limit_config'])
        
        # Handle task optimizations enum keys
        if 'task_optimizations' in data:
            task_opts = {}
            for task_str, opts in data['task_optimizations'].items():
                if isinstance(task_str, str):
                    task_type = TaskType(task_str)
                    task_opts[task_type] = opts
                else:
                    task_opts[task_str] = opts
            data['task_optimizations'] = task_opts
        
        return cls(**data)


@dataclass
class PerformanceMetrics:
    """Performance metrics for model configuration."""
    response_time_avg: float = 0.0
    response_time_p95: float = 0.0
    success_rate: float = 0.0
    error_rate: float = 0.0
    cost_per_request: float = 0.0
    tokens_per_second: float = 0.0
    quality_score: float = 0.0
    
    # Time series data
    response_times: deque = field(default_factory=lambda: deque(maxlen=1000))
    success_history: deque = field(default_factory=lambda: deque(maxlen=1000))
    cost_history: deque = field(default_factory=lambda: deque(maxlen=1000))
    
    def update(self, response_time: float, success: bool, cost: float, quality: float = 0.0):
        """Update metrics with new data point."""
        self.response_times.append(response_time)
        self.success_history.append(success)
        self.cost_history.append(cost)
        
        # Calculate averages
        if self.response_times:
            self.response_time_avg = statistics.mean(self.response_times)
            self.response_time_p95 = statistics.quantiles(self.response_times, n=20)[18] if len(self.response_times) > 20 else max(self.response_times)
        
        if self.success_history:
            self.success_rate = sum(self.success_history) / len(self.success_history)
            self.error_rate = 1.0 - self.success_rate
        
        if self.cost_history:
            self.cost_per_request = statistics.mean(self.cost_history)
        
        # Update quality score (weighted average)
        if quality > 0:
            if self.quality_score == 0:
                self.quality_score = quality
            else:
                self.quality_score = 0.9 * self.quality_score + 0.1 * quality
    
    def get_performance_score(self, strategy: OptimizationStrategy = OptimizationStrategy.BALANCED) -> float:
        """Calculate overall performance score based on strategy."""
        if strategy == OptimizationStrategy.PERFORMANCE:
            return self.quality_score * 0.7 + self.success_rate * 0.3
        elif strategy == OptimizationStrategy.COST:
            cost_score = max(0, 1.0 - self.cost_per_request / 10.0)  # Normalize cost
            return cost_score * 0.6 + self.success_rate * 0.4
        elif strategy == OptimizationStrategy.SPEED:
            speed_score = max(0, 1.0 - self.response_time_avg / 30.0)  # Normalize response time
            return speed_score * 0.6 + self.success_rate * 0.4
        else:  # BALANCED
            quality_score = self.quality_score * 0.3
            cost_score = max(0, 1.0 - self.cost_per_request / 10.0) * 0.2
            speed_score = max(0, 1.0 - self.response_time_avg / 30.0) * 0.2
            success_score = self.success_rate * 0.3
            return quality_score + cost_score + speed_score + success_score


@dataclass
class ABTestConfiguration:
    """A/B test configuration."""
    test_id: str
    description: str
    variants: Dict[str, ModelConfiguration]
    traffic_split: Dict[str, float]  # Percentage of traffic for each variant
    success_metric: str = "quality_score"
    minimum_samples: int = 100
    confidence_level: float = 0.95
    max_duration_hours: int = 24
    
    # Test state
    start_time: Optional[float] = None
    end_time: Optional[float] = None
    is_active: bool = False
    results: Dict[str, PerformanceMetrics] = field(default_factory=dict)


class DynamicParameterTuner:
    """Dynamic parameter tuning based on task requirements and performance."""
    
    def __init__(self):
        self.task_profiles = self._initialize_task_profiles()
        self.performance_history: Dict[str, List[PerformanceMetrics]] = defaultdict(list)
    
    def _initialize_task_profiles(self) -> Dict[TaskType, Dict[str, Any]]:
        """Initialize default parameter profiles for different task types."""
        return {
            TaskType.CODE_COMPLETION: {
                "temperature": 0.2,
                "max_tokens": 512,
                "top_p": 0.9,
                "stop_sequences": ["\n\n", "```"]
            },
            TaskType.BUG_FIX: {
                "temperature": 0.1,
                "max_tokens": 1024,
                "top_p": 0.8,
                "stop_sequences": ["```"]
            },
            TaskType.FUNCTION_GENERATION: {
                "temperature": 0.3,
                "max_tokens": 1024,
                "top_p": 0.9,
                "stop_sequences": ["\n\ndef ", "\n\nclass "]
            },
            TaskType.CODE_TRANSLATION: {
                "temperature": 0.1,
                "max_tokens": 2048,
                "top_p": 0.8,
                "stop_sequences": ["```"]
            },
            TaskType.ALGORITHM_IMPLEMENTATION: {
                "temperature": 0.4,
                "max_tokens": 2048,
                "top_p": 0.9,
                "stop_sequences": ["```"]
            },
            TaskType.API_DESIGN: {
                "temperature": 0.5,
                "max_tokens": 1536,
                "top_p": 0.9,
                "stop_sequences": []
            },
            TaskType.SYSTEM_DESIGN: {
                "temperature": 0.6,
                "max_tokens": 2048,
                "top_p": 0.95,
                "stop_sequences": []
            },
            TaskType.DATABASE_DESIGN: {
                "temperature": 0.3,
                "max_tokens": 1536,
                "top_p": 0.9,
                "stop_sequences": ["```"]
            },
            TaskType.SECURITY: {
                "temperature": 0.2,
                "max_tokens": 1536,
                "top_p": 0.8,
                "stop_sequences": ["```"]
            },
            TaskType.PERFORMANCE_OPTIMIZATION: {
                "temperature": 0.3,
                "max_tokens": 1536,
                "top_p": 0.9,
                "stop_sequences": ["```"]
            },
            TaskType.DOCUMENTATION: {
                "temperature": 0.4,
                "max_tokens": 2048,
                "top_p": 0.9,
                "stop_sequences": []
            },
            TaskType.TESTING: {
                "temperature": 0.3,
                "max_tokens": 1536,
                "top_p": 0.9,
                "stop_sequences": ["```"]
            },
            TaskType.FULL_STACK: {
                "temperature": 0.5,
                "max_tokens": 2048,
                "top_p": 0.95,
                "stop_sequences": []
            },
            TaskType.MULTI_TURN: {
                "temperature": 0.6,
                "max_tokens": 1024,
                "top_p": 0.9,
                "stop_sequences": []
            }
        }
    
    def tune_parameters(
        self, 
        base_config: ModelConfiguration, 
        task_type: TaskType,
        performance_feedback: Optional[PerformanceMetrics] = None
    ) -> ModelConfiguration:
        """Tune parameters based on task type and performance feedback."""
        tuned_config = ModelConfiguration(**asdict(base_config))
        
        # Apply task-specific optimizations
        if task_type in self.task_profiles:
            profile = self.task_profiles[task_type]
            for param, value in profile.items():
                setattr(tuned_config, param, value)
        
        # Apply performance-based adjustments
        if performance_feedback:
            tuned_config = self._apply_performance_adjustments(tuned_config, performance_feedback)
        
        # Store task-specific optimizations
        if task_type not in tuned_config.task_optimizations:
            tuned_config.task_optimizations[task_type] = {}
        
        tuned_config.task_optimizations[task_type].update(self.task_profiles.get(task_type, {}))
        
        return tuned_config
    
    def _apply_performance_adjustments(
        self, 
        config: ModelConfiguration, 
        metrics: PerformanceMetrics
    ) -> ModelConfiguration:
        """Apply adjustments based on performance metrics."""
        # If response time is too high, reduce max_tokens
        if metrics.response_time_avg > config.target_response_time:
            config.max_tokens = max(256, int(config.max_tokens * 0.8))
        
        # If success rate is low, reduce temperature for more deterministic output
        if metrics.success_rate < config.target_success_rate:
            config.temperature = max(0.1, config.temperature * 0.8)
        
        # If cost is too high, reduce max_tokens
        if metrics.cost_per_request > config.max_cost_per_request:
            config.max_tokens = max(256, int(config.max_tokens * 0.9))
        
        return config


class AdvancedRateLimiter:
    """Advanced rate limiting with adaptive algorithms."""
    
    def __init__(self, config: RateLimitConfig):
        self.config = config
        self.request_times: deque = deque(maxlen=1000)
        self.token_usage: deque = deque(maxlen=1000)
        self.error_count = 0
        self.consecutive_errors = 0
        self.adaptive_factor = 1.0
        self._lock = threading.Lock()
    
    def can_make_request(self, estimated_tokens: int = 0) -> bool:
        """Check if request can be made within current limits."""
        with self._lock:
            current_time = time.time()
            
            # Clean old entries
            self._clean_old_entries(current_time)
            
            # Apply adaptive rate limiting based on error rate
            effective_rpm = int(self.config.requests_per_minute * self.adaptive_factor)
            effective_tpm = int(self.config.tokens_per_minute * self.adaptive_factor)
            
            # Check request rate limit
            if len(self.request_times) >= effective_rpm:
                return False
            
            # Check token rate limit
            total_tokens = sum(tokens for _, tokens in self.token_usage)
            if total_tokens + estimated_tokens > effective_tpm:
                return False
            
            return True
    
    def record_request(self, tokens_used: int = 0, success: bool = True):
        """Record a request for rate limiting."""
        with self._lock:
            current_time = time.time()
            self.request_times.append(current_time)
            if tokens_used > 0:
                self.token_usage.append((current_time, tokens_used))
            
            # Update error tracking
            if not success:
                self.error_count += 1
                self.consecutive_errors += 1
                # Reduce rate limit after consecutive errors
                if self.consecutive_errors >= 3:
                    self.adaptive_factor = max(0.1, self.adaptive_factor * 0.5)
            else:
                self.consecutive_errors = 0
                # Gradually restore rate limit after successful requests
                if self.adaptive_factor < 1.0:
                    self.adaptive_factor = min(1.0, self.adaptive_factor * 1.1)
    
    def _clean_old_entries(self, current_time: float):
        """Remove entries older than 1 minute."""
        cutoff_time = current_time - 60
        
        # Clean request times
        while self.request_times and self.request_times[0] < cutoff_time:
            self.request_times.popleft()
        
        # Clean token usage
        while self.token_usage and self.token_usage[0][0] < cutoff_time:
            self.token_usage.popleft()
    
    def get_wait_time(self) -> float:
        """Get recommended wait time before next request."""
        if not self.request_times:
            return 0.0
        
        current_time = time.time()
        oldest_request = self.request_times[0]
        time_since_oldest = current_time - oldest_request
        
        if time_since_oldest < 60:
            return max(0, 60 - time_since_oldest)
        
        return 0.0


class PerformanceMonitor:
    """Monitor and track model performance with auto-scaling capabilities."""
    
    def __init__(self):
        self.metrics: Dict[str, PerformanceMetrics] = {}
        self.alerts: List[Dict[str, Any]] = []
        self.auto_scaling_enabled = True
        self.scaling_thresholds = {
            'response_time_high': 10.0,
            'error_rate_high': 0.1,
            'success_rate_low': 0.8
        }
        self._monitor_thread = None
        self._stop_monitoring = False
    
    def start_monitoring(self):
        """Start performance monitoring in background thread."""
        if self._monitor_thread is None or not self._monitor_thread.is_alive():
            self._stop_monitoring = False
            self._monitor_thread = threading.Thread(target=self._monitor_loop, daemon=True)
            self._monitor_thread.start()
            eval_logger.info("Performance monitoring started")
    
    def stop_monitoring(self):
        """Stop performance monitoring."""
        self._stop_monitoring = True
        if self._monitor_thread and self._monitor_thread.is_alive():
            self._monitor_thread.join(timeout=5)
        eval_logger.info("Performance monitoring stopped")
    
    def record_performance(
        self, 
        model_id: str, 
        response_time: float, 
        success: bool, 
        cost: float, 
        quality: float = 0.0
    ):
        """Record performance metrics for a model."""
        if model_id not in self.metrics:
            self.metrics[model_id] = PerformanceMetrics()
        
        self.metrics[model_id].update(response_time, success, cost, quality)
        
        # Check for immediate alerts
        self._check_alerts(model_id)
    
    def get_performance_summary(self, model_id: str) -> Dict[str, Any]:
        """Get performance summary for a model."""
        if model_id not in self.metrics:
            return {}
        
        metrics = self.metrics[model_id]
        return {
            'response_time_avg': metrics.response_time_avg,
            'response_time_p95': metrics.response_time_p95,
            'success_rate': metrics.success_rate,
            'error_rate': metrics.error_rate,
            'cost_per_request': metrics.cost_per_request,
            'quality_score': metrics.quality_score,
            'total_requests': len(metrics.response_times)
        }
    
    def get_scaling_recommendations(self, model_id: str) -> List[Dict[str, Any]]:
        """Get auto-scaling recommendations for a model."""
        if model_id not in self.metrics:
            return []
        
        metrics = self.metrics[model_id]
        recommendations = []
        
        # High response time - recommend reducing load or increasing resources
        if metrics.response_time_avg > self.scaling_thresholds['response_time_high']:
            recommendations.append({
                'type': 'scale_up',
                'reason': 'High response time',
                'current_value': metrics.response_time_avg,
                'threshold': self.scaling_thresholds['response_time_high'],
                'action': 'Increase concurrent request limit or reduce max_tokens'
            })
        
        # High error rate - recommend reducing load
        if metrics.error_rate > self.scaling_thresholds['error_rate_high']:
            recommendations.append({
                'type': 'scale_down',
                'reason': 'High error rate',
                'current_value': metrics.error_rate,
                'threshold': self.scaling_thresholds['error_rate_high'],
                'action': 'Reduce request rate or implement circuit breaker'
            })
        
        # Low success rate - recommend configuration changes
        if metrics.success_rate < self.scaling_thresholds['success_rate_low']:
            recommendations.append({
                'type': 'optimize_config',
                'reason': 'Low success rate',
                'current_value': metrics.success_rate,
                'threshold': self.scaling_thresholds['success_rate_low'],
                'action': 'Adjust model parameters or implement retry logic'
            })
        
        return recommendations
    
    def _monitor_loop(self):
        """Background monitoring loop."""
        while not self._stop_monitoring:
            try:
                # Check all models for performance issues
                for model_id in list(self.metrics.keys()):
                    self._check_alerts(model_id)
                    
                    # Apply auto-scaling if enabled
                    if self.auto_scaling_enabled:
                        recommendations = self.get_scaling_recommendations(model_id)
                        for rec in recommendations:
                            eval_logger.info(f"Auto-scaling recommendation for {model_id}: {rec}")
                
                time.sleep(30)  # Check every 30 seconds
                
            except Exception as e:
                eval_logger.error(f"Error in performance monitoring loop: {e}")
                time.sleep(60)  # Wait longer on error
    
    def _check_alerts(self, model_id: str):
        """Check for performance alerts."""
        if model_id not in self.metrics:
            return
        
        metrics = self.metrics[model_id]
        current_time = time.time()
        
        # Response time alert
        if metrics.response_time_avg > self.scaling_thresholds['response_time_high']:
            alert = {
                'timestamp': current_time,
                'model_id': model_id,
                'type': 'high_response_time',
                'value': metrics.response_time_avg,
                'threshold': self.scaling_thresholds['response_time_high']
            }
            self.alerts.append(alert)
            eval_logger.warning(f"High response time alert for {model_id}: {metrics.response_time_avg:.2f}s")
        
        # Error rate alert
        if metrics.error_rate > self.scaling_thresholds['error_rate_high']:
            alert = {
                'timestamp': current_time,
                'model_id': model_id,
                'type': 'high_error_rate',
                'value': metrics.error_rate,
                'threshold': self.scaling_thresholds['error_rate_high']
            }
            self.alerts.append(alert)
            eval_logger.warning(f"High error rate alert for {model_id}: {metrics.error_rate:.2%}")


class ABTestManager:
    """Manage A/B tests for model configuration optimization."""
    
    def __init__(self):
        self.active_tests: Dict[str, ABTestConfiguration] = {}
        self.completed_tests: Dict[str, ABTestConfiguration] = {}
        self.performance_monitor = PerformanceMonitor()
    
    def create_ab_test(
        self,
        test_id: str,
        description: str,
        variants: Dict[str, ModelConfiguration],
        traffic_split: Dict[str, float],
        success_metric: str = "quality_score",
        minimum_samples: int = 100,
        confidence_level: float = 0.95,
        max_duration_hours: int = 24
    ) -> ABTestConfiguration:
        """Create a new A/B test."""
        # Validate traffic split
        if abs(sum(traffic_split.values()) - 1.0) > 0.01:
            raise ValueError("Traffic split must sum to 1.0")
        
        if set(traffic_split.keys()) != set(variants.keys()):
            raise ValueError("Traffic split keys must match variant keys")
        
        test_config = ABTestConfiguration(
            test_id=test_id,
            description=description,
            variants=variants,
            traffic_split=traffic_split,
            success_metric=success_metric,
            minimum_samples=minimum_samples,
            confidence_level=confidence_level,
            max_duration_hours=max_duration_hours
        )
        
        # Initialize results for each variant
        for variant_name in variants.keys():
            test_config.results[variant_name] = PerformanceMetrics()
        
        self.active_tests[test_id] = test_config
        eval_logger.info(f"Created A/B test: {test_id}")
        
        return test_config
    
    def start_ab_test(self, test_id: str):
        """Start an A/B test."""
        if test_id not in self.active_tests:
            raise ValueError(f"Test {test_id} not found")
        
        test = self.active_tests[test_id]
        test.start_time = time.time()
        test.is_active = True
        
        eval_logger.info(f"Started A/B test: {test_id}")
    
    def stop_ab_test(self, test_id: str):
        """Stop an A/B test."""
        if test_id not in self.active_tests:
            raise ValueError(f"Test {test_id} not found")
        
        test = self.active_tests[test_id]
        test.end_time = time.time()
        test.is_active = False
        
        # Move to completed tests
        self.completed_tests[test_id] = test
        del self.active_tests[test_id]
        
        eval_logger.info(f"Stopped A/B test: {test_id}")
    
    def select_variant(self, test_id: str) -> Tuple[str, ModelConfiguration]:
        """Select a variant for the current request based on traffic split."""
        if test_id not in self.active_tests:
            raise ValueError(f"Test {test_id} not found")
        
        test = self.active_tests[test_id]
        if not test.is_active:
            raise ValueError(f"Test {test_id} is not active")
        
        # Simple random selection based on traffic split
        import random
        rand_val = random.random()
        cumulative = 0.0
        
        for variant_name, weight in test.traffic_split.items():
            cumulative += weight
            if rand_val <= cumulative:
                return variant_name, test.variants[variant_name]
        
        # Fallback to first variant
        first_variant = list(test.variants.keys())[0]
        return first_variant, test.variants[first_variant]
    
    def record_test_result(
        self,
        test_id: str,
        variant_name: str,
        response_time: float,
        success: bool,
        cost: float,
        quality: float = 0.0
    ):
        """Record a result for an A/B test variant."""
        if test_id not in self.active_tests:
            return  # Test may have ended
        
        test = self.active_tests[test_id]
        if variant_name in test.results:
            test.results[variant_name].update(response_time, success, cost, quality)
    
    def analyze_ab_test(self, test_id: str) -> Dict[str, Any]:
        """Analyze A/B test results."""
        test = None
        if test_id in self.active_tests:
            test = self.active_tests[test_id]
        elif test_id in self.completed_tests:
            test = self.completed_tests[test_id]
        else:
            raise ValueError(f"Test {test_id} not found")
        
        analysis = {
            'test_id': test_id,
            'description': test.description,
            'is_active': test.is_active,
            'start_time': test.start_time,
            'end_time': test.end_time,
            'variants': {},
            'winner': None,
            'confidence': 0.0,
            'significant': False
        }
        
        # Analyze each variant
        variant_scores = {}
        for variant_name, metrics in test.results.items():
            variant_analysis = {
                'sample_size': len(metrics.response_times),
                'response_time_avg': metrics.response_time_avg,
                'success_rate': metrics.success_rate,
                'cost_per_request': metrics.cost_per_request,
                'quality_score': metrics.quality_score,
                'performance_score': metrics.get_performance_score()
            }
            
            analysis['variants'][variant_name] = variant_analysis
            variant_scores[variant_name] = variant_analysis['performance_score']
        
        # Determine winner
        if variant_scores:
            winner = max(variant_scores.keys(), key=lambda k: variant_scores[k])
            analysis['winner'] = winner
            
            # Simple significance test (would use proper statistical tests in production)
            sample_sizes = [len(metrics.response_times) for metrics in test.results.values()]
            if all(size >= test.minimum_samples for size in sample_sizes):
                analysis['significant'] = True
                analysis['confidence'] = test.confidence_level
        
        return analysis
    
    def get_best_configuration(self, test_id: str) -> Optional[ModelConfiguration]:
        """Get the best performing configuration from an A/B test."""
        analysis = self.analyze_ab_test(test_id)
        
        if analysis['significant'] and analysis['winner']:
            test = self.active_tests.get(test_id) or self.completed_tests.get(test_id)
            if test:
                return test.variants[analysis['winner']]
        
        return None


class AdvancedModelConfigurationManager:
    """
    Advanced model configuration management system.
    
    Provides comprehensive configuration management with:
    - Dynamic parameter tuning
    - Performance monitoring and auto-scaling
    - A/B testing for optimization
    - Cost management and budget control
    """
    
    def __init__(self):
        self.configurations: Dict[str, ModelConfiguration] = {}
        self.parameter_tuner = DynamicParameterTuner()
        self.performance_monitor = PerformanceMonitor()
        self.ab_test_manager = ABTestManager()
        self.rate_limiters: Dict[str, AdvancedRateLimiter] = {}
        
        # Start monitoring
        self.performance_monitor.start_monitoring()
    
    def register_model_configuration(
        self, 
        model_id: str, 
        config: ModelConfiguration
    ):
        """Register a model configuration."""
        self.configurations[model_id] = config
        
        # Create rate limiter
        self.rate_limiters[model_id] = AdvancedRateLimiter(config.rate_limit_config)
        
        eval_logger.info(f"Registered configuration for model: {model_id}")
    
    def get_optimized_configuration(
        self, 
        model_id: str, 
        task_type: TaskType,
        optimization_strategy: OptimizationStrategy = OptimizationStrategy.BALANCED
    ) -> ModelConfiguration:
        """Get optimized configuration for a specific task."""
        if model_id not in self.configurations:
            raise ValueError(f"No configuration found for model: {model_id}")
        
        base_config = self.configurations[model_id]
        
        # Get performance feedback
        performance_feedback = None
        if model_id in self.performance_monitor.metrics:
            performance_feedback = self.performance_monitor.metrics[model_id]
        
        # Tune parameters
        optimized_config = self.parameter_tuner.tune_parameters(
            base_config, task_type, performance_feedback
        )
        
        return optimized_config
    
    def can_make_request(self, model_id: str, estimated_tokens: int = 0) -> bool:
        """Check if a request can be made within rate limits."""
        if model_id not in self.rate_limiters:
            return True
        
        return self.rate_limiters[model_id].can_make_request(estimated_tokens)
    
    def record_request_result(
        self,
        model_id: str,
        response_time: float,
        success: bool,
        tokens_used: int = 0,
        cost: float = 0.0,
        quality_score: float = 0.0
    ):
        """Record the result of a model request."""
        # Update rate limiter
        if model_id in self.rate_limiters:
            self.rate_limiters[model_id].record_request(tokens_used, success)
        
        # Update performance monitor
        self.performance_monitor.record_performance(
            model_id, response_time, success, cost, quality_score
        )
    
    def get_performance_summary(self, model_id: str) -> Dict[str, Any]:
        """Get performance summary for a model."""
        return self.performance_monitor.get_performance_summary(model_id)
    
    def get_scaling_recommendations(self, model_id: str) -> List[Dict[str, Any]]:
        """Get auto-scaling recommendations."""
        return self.performance_monitor.get_scaling_recommendations(model_id)
    
    def create_ab_test(
        self,
        test_id: str,
        description: str,
        base_model_id: str,
        parameter_variations: Dict[str, Dict[str, Any]],
        task_type: TaskType,
        **test_kwargs
    ) -> ABTestConfiguration:
        """Create an A/B test for configuration optimization."""
        if base_model_id not in self.configurations:
            raise ValueError(f"Base model {base_model_id} not found")
        
        base_config = self.configurations[base_model_id]
        variants = {}
        
        # Create variants
        for variant_name, param_changes in parameter_variations.items():
            variant_config = ModelConfiguration(**asdict(base_config))
            
            # Apply parameter changes
            for param, value in param_changes.items():
                setattr(variant_config, param, value)
            
            # Set A/B test metadata
            variant_config.ab_test_variant = variant_name
            
            variants[variant_name] = variant_config
        
        # Default traffic split (equal)
        traffic_split = {name: 1.0 / len(variants) for name in variants.keys()}
        if 'traffic_split' in test_kwargs:
            traffic_split = test_kwargs.pop('traffic_split')
        
        return self.ab_test_manager.create_ab_test(
            test_id, description, variants, traffic_split, **test_kwargs
        )
    
    def start_ab_test(self, test_id: str):
        """Start an A/B test."""
        self.ab_test_manager.start_ab_test(test_id)
    
    def stop_ab_test(self, test_id: str):
        """Stop an A/B test."""
        self.ab_test_manager.stop_ab_test(test_id)
    
    def get_ab_test_configuration(self, test_id: str) -> Tuple[str, ModelConfiguration]:
        """Get configuration for A/B test."""
        return self.ab_test_manager.select_variant(test_id)
    
    def analyze_ab_test(self, test_id: str) -> Dict[str, Any]:
        """Analyze A/B test results."""
        return self.ab_test_manager.analyze_ab_test(test_id)
    
    def apply_best_configuration(self, test_id: str, model_id: str) -> bool:
        """Apply the best configuration from an A/B test."""
        best_config = self.ab_test_manager.get_best_configuration(test_id)
        if best_config:
            self.register_model_configuration(model_id, best_config)
            eval_logger.info(f"Applied best configuration from test {test_id} to model {model_id}")
            return True
        return False
    
    def export_configuration(self, model_id: str) -> Dict[str, Any]:
        """Export model configuration to dictionary."""
        if model_id not in self.configurations:
            raise ValueError(f"Model {model_id} not found")
        
        config = self.configurations[model_id]
        return config.to_dict()
    
    def import_configuration(self, model_id: str, config_data: Dict[str, Any]):
        """Import model configuration from dictionary."""
        config = ModelConfiguration.from_dict(config_data)
        self.register_model_configuration(model_id, config)
    
    def shutdown(self):
        """Shutdown the configuration manager."""
        self.performance_monitor.stop_monitoring()
        eval_logger.info("Advanced model configuration manager shutdown")


# Global instance
advanced_config_manager = AdvancedModelConfigurationManager()