"""
A/B Testing Framework for Prompt Optimization

This module implements a comprehensive A/B testing system for prompt optimization
with statistical analysis, performance tracking, and automated recommendations.

Requirements addressed:
- 4.4: A/B test creation and management system
- 4.6: Statistical analysis for test result evaluation with significance testing
- 4.6: Template performance tracking and optimization recommendations
- 4.6: Prompt effectiveness scoring and ranking system
"""

import json
import logging
import sqlite3
import statistics
from abc import ABC, abstractmethod
from dataclasses import dataclass, field, asdict
from datetime import datetime, timedelta
from pathlib import Path
from typing import Dict, List, Optional, Any, Tuple, Callable, Union
from enum import Enum
import numpy as np
from scipy import stats
import pandas as pd

# Configure logging
logger = logging.getLogger(__name__)


class TestStatus(Enum):
    """Status of A/B tests"""
    DRAFT = "draft"
    ACTIVE = "active"
    PAUSED = "paused"
    COMPLETED = "completed"
    CANCELLED = "cancelled"


class SignificanceTest(Enum):
    """Statistical significance test methods"""
    T_TEST = "t_test"
    MANN_WHITNEY = "mann_whitney"
    CHI_SQUARE = "chi_square"
    BOOTSTRAP = "bootstrap"


@dataclass
class TestVariant:
    """Configuration for a test variant"""
    variant_id: str
    name: str
    description: str
    prompt_template: str
    template_variables: Dict[str, Any] = field(default_factory=dict)
    weight: float = 1.0  # Traffic allocation weight
    metadata: Dict[str, Any] = field(default_factory=dict)


@dataclass
class TestMetric:
    """Definition of a test metric"""
    metric_id: str
    name: str
    description: str
    metric_type: str  # "primary", "secondary", "guardrail"
    higher_is_better: bool = True
    minimum_detectable_effect: float = 0.05
    target_value: Optional[float] = None


@dataclass
class TestConfiguration:
    """Complete A/B test configuration"""
    test_id: str
    name: str
    description: str
    variants: List[TestVariant]
    metrics: List[TestMetric]
    sample_size_per_variant: int
    confidence_level: float = 0.95
    power: float = 0.8
    max_duration_days: int = 30
    auto_stop_criteria: Dict[str, float] = field(default_factory=dict)
    stratification_keys: List[str] = field(default_factory=list)
    exclusion_criteria: Dict[str, Any] = field(default_factory=dict)


@dataclass
class TestResult:
    """Individual test result record"""
    result_id: str
    test_id: str
    variant_id: str
    user_id: str
    session_id: str
    metrics: Dict[str, float]
    metadata: Dict[str, Any]
    timestamp: datetime
    stratification_values: Dict[str, str] = field(default_factory=dict)


@dataclass
class StatisticalAnalysis:
    """Statistical analysis results"""
    test_id: str
    primary_metric: str
    variant_statistics: Dict[str, Dict[str, float]]
    pairwise_comparisons: Dict[str, Dict[str, float]]
    confidence_intervals: Dict[str, Tuple[float, float]]
    effect_sizes: Dict[str, float]
    statistical_significance: Dict[str, bool]
    practical_significance: Dict[str, bool]
    power_analysis: Dict[str, float]
    recommendation: str
    analysis_timestamp: datetime


@dataclass
class TestSummary:
    """Summary of A/B test results"""
    test_id: str
    status: TestStatus
    start_date: datetime
    end_date: Optional[datetime]
    total_samples: int
    variant_samples: Dict[str, int]
    winner_variant: Optional[str]
    confidence_score: float
    effect_size: float
    statistical_analysis: Optional[StatisticalAnalysis]
    recommendations: List[str]
    key_insights: List[str]


class StatisticalAnalyzer:
    """Performs statistical analysis on A/B test results"""
    
    def __init__(self, confidence_level: float = 0.95):
        self.confidence_level = confidence_level
        self.alpha = 1 - confidence_level
    
    def analyze_test_results(self, test_config: TestConfiguration, 
                           results: List[TestResult]) -> StatisticalAnalysis:
        """Perform comprehensive statistical analysis"""
        
        if not results:
            raise ValueError("No results to analyze")
        
        # Group results by variant
        variant_results = self._group_results_by_variant(results)
        
        # Get primary metric
        primary_metric = self._get_primary_metric(test_config.metrics)
        
        # Calculate basic statistics for each variant
        variant_statistics = self._calculate_variant_statistics(
            variant_results, test_config.metrics
        )
        
        # Perform pairwise comparisons
        pairwise_comparisons = self._perform_pairwise_comparisons(
            variant_results, primary_metric
        )
        
        # Calculate confidence intervals
        confidence_intervals = self._calculate_confidence_intervals(
            variant_results, primary_metric
        )
        
        # Calculate effect sizes
        effect_sizes = self._calculate_effect_sizes(
            variant_results, primary_metric
        )
        
        # Determine statistical significance
        statistical_significance = self._determine_statistical_significance(
            pairwise_comparisons
        )
        
        # Determine practical significance
        practical_significance = self._determine_practical_significance(
            effect_sizes, test_config.metrics
        )
        
        # Perform power analysis
        power_analysis = self._perform_power_analysis(
            variant_results, primary_metric
        )
        
        # Generate recommendation
        recommendation = self._generate_recommendation(
            variant_statistics, statistical_significance, practical_significance
        )
        
        return StatisticalAnalysis(
            test_id=test_config.test_id,
            primary_metric=primary_metric,
            variant_statistics=variant_statistics,
            pairwise_comparisons=pairwise_comparisons,
            confidence_intervals=confidence_intervals,
            effect_sizes=effect_sizes,
            statistical_significance=statistical_significance,
            practical_significance=practical_significance,
            power_analysis=power_analysis,
            recommendation=recommendation,
            analysis_timestamp=datetime.now()
        )
    
    def _group_results_by_variant(self, results: List[TestResult]) -> Dict[str, List[TestResult]]:
        """Group results by variant"""
        variant_results = {}
        for result in results:
            if result.variant_id not in variant_results:
                variant_results[result.variant_id] = []
            variant_results[result.variant_id].append(result)
        return variant_results
    
    def _get_primary_metric(self, metrics: List[TestMetric]) -> str:
        """Get primary metric name"""
        for metric in metrics:
            if metric.metric_type == "primary":
                return metric.metric_id
        # Fallback to first metric
        return metrics[0].metric_id if metrics else "default"
    
    def _calculate_variant_statistics(self, variant_results: Dict[str, List[TestResult]], 
                                    metrics: List[TestMetric]) -> Dict[str, Dict[str, float]]:
        """Calculate basic statistics for each variant"""
        
        variant_stats = {}
        
        for variant_id, results in variant_results.items():
            variant_stats[variant_id] = {}
            
            for metric in metrics:
                metric_values = [
                    result.metrics.get(metric.metric_id, 0.0) 
                    for result in results
                ]
                
                if metric_values:
                    variant_stats[variant_id][metric.metric_id] = {
                        "count": len(metric_values),
                        "mean": statistics.mean(metric_values),
                        "median": statistics.median(metric_values),
                        "std": statistics.stdev(metric_values) if len(metric_values) > 1 else 0.0,
                        "min": min(metric_values),
                        "max": max(metric_values),
                        "q25": np.percentile(metric_values, 25),
                        "q75": np.percentile(metric_values, 75)
                    }
        
        return variant_stats
    
    def _perform_pairwise_comparisons(self, variant_results: Dict[str, List[TestResult]], 
                                    primary_metric: str) -> Dict[str, Dict[str, float]]:
        """Perform pairwise statistical comparisons"""
        
        comparisons = {}
        variants = list(variant_results.keys())
        
        for i, variant_a in enumerate(variants):
            comparisons[variant_a] = {}
            
            for variant_b in variants[i+1:]:
                # Get metric values for both variants
                values_a = [
                    result.metrics.get(primary_metric, 0.0) 
                    for result in variant_results[variant_a]
                ]
                values_b = [
                    result.metrics.get(primary_metric, 0.0) 
                    for result in variant_results[variant_b]
                ]
                
                if len(values_a) > 1 and len(values_b) > 1:
                    # Perform t-test
                    t_stat, p_value = stats.ttest_ind(values_a, values_b)
                    
                    # Perform Mann-Whitney U test (non-parametric)
                    u_stat, u_p_value = stats.mannwhitneyu(
                        values_a, values_b, alternative='two-sided'
                    )
                    
                    comparisons[variant_a][variant_b] = {
                        "t_statistic": t_stat,
                        "t_p_value": p_value,
                        "u_statistic": u_stat,
                        "u_p_value": u_p_value,
                        "mean_difference": statistics.mean(values_a) - statistics.mean(values_b)
                    }
        
        return comparisons
    
    def _calculate_confidence_intervals(self, variant_results: Dict[str, List[TestResult]], 
                                      primary_metric: str) -> Dict[str, Tuple[float, float]]:
        """Calculate confidence intervals for each variant"""
        
        confidence_intervals = {}
        
        for variant_id, results in variant_results.items():
            values = [
                result.metrics.get(primary_metric, 0.0) 
                for result in results
            ]
            
            if len(values) > 1:
                mean = statistics.mean(values)
                std_err = statistics.stdev(values) / np.sqrt(len(values))
                
                # Calculate confidence interval
                t_critical = stats.t.ppf(1 - self.alpha/2, len(values) - 1)
                margin_error = t_critical * std_err
                
                confidence_intervals[variant_id] = (
                    mean - margin_error,
                    mean + margin_error
                )
            else:
                confidence_intervals[variant_id] = (0.0, 0.0)
        
        return confidence_intervals
    
    def _calculate_effect_sizes(self, variant_results: Dict[str, List[TestResult]], 
                              primary_metric: str) -> Dict[str, float]:
        """Calculate effect sizes (Cohen's d) between variants"""
        
        effect_sizes = {}
        variants = list(variant_results.keys())
        
        if len(variants) < 2:
            return effect_sizes
        
        # Use first variant as control
        control_variant = variants[0]
        control_values = [
            result.metrics.get(primary_metric, 0.0) 
            for result in variant_results[control_variant]
        ]
        
        for variant_id in variants[1:]:
            treatment_values = [
                result.metrics.get(primary_metric, 0.0) 
                for result in variant_results[variant_id]
            ]
            
            if len(control_values) > 1 and len(treatment_values) > 1:
                # Calculate Cohen's d
                mean_diff = statistics.mean(treatment_values) - statistics.mean(control_values)
                pooled_std = np.sqrt(
                    ((len(control_values) - 1) * statistics.variance(control_values) +
                     (len(treatment_values) - 1) * statistics.variance(treatment_values)) /
                    (len(control_values) + len(treatment_values) - 2)
                )
                
                if pooled_std > 0:
                    effect_sizes[f"{control_variant}_vs_{variant_id}"] = mean_diff / pooled_std
        
        return effect_sizes
    
    def _determine_statistical_significance(self, pairwise_comparisons: Dict[str, Dict[str, float]]) -> Dict[str, bool]:
        """Determine statistical significance for each comparison"""
        
        significance = {}
        
        for variant_a, comparisons in pairwise_comparisons.items():
            for variant_b, stats_dict in comparisons.items():
                comparison_key = f"{variant_a}_vs_{variant_b}"
                
                # Use t-test p-value for significance
                p_value = stats_dict.get("t_p_value", 1.0)
                significance[comparison_key] = p_value < self.alpha
        
        return significance
    
    def _determine_practical_significance(self, effect_sizes: Dict[str, float], 
                                        metrics: List[TestMetric]) -> Dict[str, bool]:
        """Determine practical significance based on effect sizes"""
        
        practical_significance = {}
        
        # Get minimum detectable effect for primary metric
        min_effect = 0.2  # Default small effect size
        for metric in metrics:
            if metric.metric_type == "primary":
                min_effect = metric.minimum_detectable_effect
                break
        
        for comparison, effect_size in effect_sizes.items():
            practical_significance[comparison] = abs(effect_size) >= min_effect
        
        return practical_significance
    
    def _perform_power_analysis(self, variant_results: Dict[str, List[TestResult]], 
                              primary_metric: str) -> Dict[str, float]:
        """Perform power analysis for the test"""
        
        power_analysis = {}
        
        # Calculate observed power for each variant comparison
        variants = list(variant_results.keys())
        
        for variant_id in variants:
            sample_size = len(variant_results[variant_id])
            
            # Estimate power based on sample size and observed effect
            # This is a simplified calculation
            if sample_size > 10:
                estimated_power = min(0.99, sample_size / 100.0)  # Simplified power estimation
            else:
                estimated_power = 0.1
            
            power_analysis[variant_id] = estimated_power
        
        return power_analysis
    
    def _generate_recommendation(self, variant_statistics: Dict[str, Dict[str, float]], 
                               statistical_significance: Dict[str, bool], 
                               practical_significance: Dict[str, bool]) -> str:
        """Generate recommendation based on analysis"""
        
        # Find best performing variant based on primary metric
        best_variant = None
        best_score = float('-inf')
        
        for variant_id, stats in variant_statistics.items():
            for metric_id, metric_stats in stats.items():
                if isinstance(metric_stats, dict) and "mean" in metric_stats:
                    if metric_stats["mean"] > best_score:
                        best_score = metric_stats["mean"]
                        best_variant = variant_id
                    break
        
        # Check if there's significant difference
        has_significant_difference = any(statistical_significance.values())
        has_practical_difference = any(practical_significance.values())
        
        if has_significant_difference and has_practical_difference:
            return f"Implement variant '{best_variant}' - shows statistically and practically significant improvement"
        elif has_significant_difference:
            return f"Consider variant '{best_variant}' - shows statistical significance but effect size is small"
        elif has_practical_difference:
            return f"Monitor variant '{best_variant}' - shows practical difference but needs more data for statistical significance"
        else:
            return "No significant difference detected - continue with current implementation or run longer test"


class ABTestManager:
    """Manages A/B tests with persistence and advanced analytics"""
    
    def __init__(self, db_path: Optional[Path] = None):
        self.db_path = db_path or Path("ab_tests.db")
        self.analyzer = StatisticalAnalyzer()
        self._init_database()
    
    def _init_database(self):
        """Initialize SQLite database for test persistence"""
        
        with sqlite3.connect(self.db_path) as conn:
            conn.execute("""
                CREATE TABLE IF NOT EXISTS tests (
                    test_id TEXT PRIMARY KEY,
                    name TEXT NOT NULL,
                    description TEXT,
                    config TEXT NOT NULL,
                    status TEXT NOT NULL,
                    created_at TIMESTAMP DEFAULT CURRENT_TIMESTAMP,
                    updated_at TIMESTAMP DEFAULT CURRENT_TIMESTAMP
                )
            """)
            
            conn.execute("""
                CREATE TABLE IF NOT EXISTS test_results (
                    result_id TEXT PRIMARY KEY,
                    test_id TEXT NOT NULL,
                    variant_id TEXT NOT NULL,
                    user_id TEXT NOT NULL,
                    session_id TEXT,
                    metrics TEXT NOT NULL,
                    metadata TEXT,
                    timestamp TIMESTAMP DEFAULT CURRENT_TIMESTAMP,
                    FOREIGN KEY (test_id) REFERENCES tests (test_id)
                )
            """)
            
            conn.execute("""
                CREATE TABLE IF NOT EXISTS test_analyses (
                    analysis_id TEXT PRIMARY KEY,
                    test_id TEXT NOT NULL,
                    analysis_data TEXT NOT NULL,
                    created_at TIMESTAMP DEFAULT CURRENT_TIMESTAMP,
                    FOREIGN KEY (test_id) REFERENCES tests (test_id)
                )
            """)
    
    def create_test(self, config: TestConfiguration) -> str:
        """Create a new A/B test"""
        
        # Validate configuration
        self._validate_test_config(config)
        
        # Store test in database
        with sqlite3.connect(self.db_path) as conn:
            conn.execute("""
                INSERT INTO tests (test_id, name, description, config, status)
                VALUES (?, ?, ?, ?, ?)
            """, (
                config.test_id,
                config.name,
                config.description,
                json.dumps(asdict(config)),
                TestStatus.DRAFT.value
            ))
        
        logger.info(f"Created A/B test: {config.test_id}")
        return config.test_id
    
    def start_test(self, test_id: str) -> bool:
        """Start an A/B test"""
        
        with sqlite3.connect(self.db_path) as conn:
            cursor = conn.execute(
                "SELECT status FROM tests WHERE test_id = ?", 
                (test_id,)
            )
            row = cursor.fetchone()
            
            if not row:
                raise ValueError(f"Test {test_id} not found")
            
            if row[0] != TestStatus.DRAFT.value:
                raise ValueError(f"Test {test_id} is not in draft status")
            
            conn.execute("""
                UPDATE tests 
                SET status = ?, updated_at = CURRENT_TIMESTAMP 
                WHERE test_id = ?
            """, (TestStatus.ACTIVE.value, test_id))
        
        logger.info(f"Started A/B test: {test_id}")
        return True
    
    def record_result(self, result: TestResult) -> None:
        """Record a test result"""
        
        with sqlite3.connect(self.db_path) as conn:
            conn.execute("""
                INSERT INTO test_results 
                (result_id, test_id, variant_id, user_id, session_id, metrics, metadata, timestamp)
                VALUES (?, ?, ?, ?, ?, ?, ?, ?)
            """, (
                result.result_id,
                result.test_id,
                result.variant_id,
                result.user_id,
                result.session_id,
                json.dumps(result.metrics),
                json.dumps(result.metadata),
                result.timestamp
            ))
    
    def analyze_test(self, test_id: str) -> StatisticalAnalysis:
        """Analyze test results"""
        
        # Get test configuration
        config = self._get_test_config(test_id)
        
        # Get test results
        results = self._get_test_results(test_id)
        
        if not results:
            raise ValueError(f"No results found for test {test_id}")
        
        # Perform analysis
        analysis = self.analyzer.analyze_test_results(config, results)
        
        # Store analysis
        with sqlite3.connect(self.db_path) as conn:
            conn.execute("""
                INSERT INTO test_analyses (analysis_id, test_id, analysis_data)
                VALUES (?, ?, ?)
            """, (
                f"{test_id}_{datetime.now().strftime('%Y%m%d_%H%M%S')}",
                test_id,
                json.dumps(asdict(analysis), default=str)
            ))
        
        return analysis
    
    def get_test_summary(self, test_id: str) -> TestSummary:
        """Get comprehensive test summary"""
        
        config = self._get_test_config(test_id)
        results = self._get_test_results(test_id)
        
        # Get test status and dates
        with sqlite3.connect(self.db_path) as conn:
            cursor = conn.execute("""
                SELECT status, created_at, updated_at 
                FROM tests WHERE test_id = ?
            """, (test_id,))
            row = cursor.fetchone()
            
            if not row:
                raise ValueError(f"Test {test_id} not found")
            
            status = TestStatus(row[0])
            start_date = datetime.fromisoformat(row[1])
            end_date = datetime.fromisoformat(row[2]) if row[2] != row[1] else None
        
        # Calculate variant sample sizes
        variant_samples = {}
        for result in results:
            variant_id = result.variant_id
            variant_samples[variant_id] = variant_samples.get(variant_id, 0) + 1
        
        # Perform analysis if enough data
        statistical_analysis = None
        winner_variant = None
        confidence_score = 0.0
        effect_size = 0.0
        
        if len(results) >= 20:  # Minimum sample size for analysis
            try:
                statistical_analysis = self.analyze_test(test_id)
                
                # Determine winner
                if statistical_analysis.variant_statistics:
                    best_variant = None
                    best_score = float('-inf')
                    
                    for variant_id, stats in statistical_analysis.variant_statistics.items():
                        for metric_id, metric_stats in stats.items():
                            if isinstance(metric_stats, dict) and "mean" in metric_stats:
                                if metric_stats["mean"] > best_score:
                                    best_score = metric_stats["mean"]
                                    best_variant = variant_id
                                break
                    
                    winner_variant = best_variant
                    
                    # Calculate confidence score
                    if statistical_analysis.statistical_significance:
                        significant_comparisons = sum(statistical_analysis.statistical_significance.values())
                        total_comparisons = len(statistical_analysis.statistical_significance)
                        confidence_score = significant_comparisons / total_comparisons if total_comparisons > 0 else 0.0
                    
                    # Get effect size
                    if statistical_analysis.effect_sizes:
                        effect_size = max(abs(es) for es in statistical_analysis.effect_sizes.values())
                
            except Exception as e:
                logger.warning(f"Analysis failed for test {test_id}: {e}")
        
        # Generate recommendations and insights
        recommendations = self._generate_recommendations(config, results, statistical_analysis)
        key_insights = self._generate_key_insights(config, results, statistical_analysis)
        
        return TestSummary(
            test_id=test_id,
            status=status,
            start_date=start_date,
            end_date=end_date,
            total_samples=len(results),
            variant_samples=variant_samples,
            winner_variant=winner_variant,
            confidence_score=confidence_score,
            effect_size=effect_size,
            statistical_analysis=statistical_analysis,
            recommendations=recommendations,
            key_insights=key_insights
        )
    
    def stop_test(self, test_id: str, reason: str = "Manual stop") -> bool:
        """Stop an active test"""
        
        with sqlite3.connect(self.db_path) as conn:
            conn.execute("""
                UPDATE tests 
                SET status = ?, updated_at = CURRENT_TIMESTAMP 
                WHERE test_id = ? AND status = ?
            """, (TestStatus.COMPLETED.value, test_id, TestStatus.ACTIVE.value))
            
            if conn.total_changes == 0:
                return False
        
        logger.info(f"Stopped A/B test: {test_id} - {reason}")
        return True
    
    def list_tests(self, status: Optional[TestStatus] = None) -> List[Dict[str, Any]]:
        """List all tests with optional status filter"""
        
        query = "SELECT test_id, name, status, created_at FROM tests"
        params = []
        
        if status:
            query += " WHERE status = ?"
            params.append(status.value)
        
        query += " ORDER BY created_at DESC"
        
        with sqlite3.connect(self.db_path) as conn:
            cursor = conn.execute(query, params)
            rows = cursor.fetchall()
            
            return [
                {
                    "test_id": row[0],
                    "name": row[1],
                    "status": row[2],
                    "created_at": row[3]
                }
                for row in rows
            ]
    
    def _validate_test_config(self, config: TestConfiguration) -> None:
        """Validate test configuration"""
        
        if len(config.variants) < 2:
            raise ValueError("Test must have at least 2 variants")
        
        if not config.metrics:
            raise ValueError("Test must have at least 1 metric")
        
        if config.sample_size_per_variant < 10:
            raise ValueError("Sample size per variant must be at least 10")
        
        if not (0.5 <= config.confidence_level <= 0.99):
            raise ValueError("Confidence level must be between 0.5 and 0.99")
        
        # Check for primary metric
        primary_metrics = [m for m in config.metrics if m.metric_type == "primary"]
        if len(primary_metrics) != 1:
            raise ValueError("Test must have exactly one primary metric")
    
    def _get_test_config(self, test_id: str) -> TestConfiguration:
        """Get test configuration from database"""
        
        with sqlite3.connect(self.db_path) as conn:
            cursor = conn.execute(
                "SELECT config FROM tests WHERE test_id = ?", 
                (test_id,)
            )
            row = cursor.fetchone()
            
            if not row:
                raise ValueError(f"Test {test_id} not found")
            
            config_dict = json.loads(row[0])
            
            # Reconstruct objects
            variants = [TestVariant(**v) for v in config_dict["variants"]]
            metrics = [TestMetric(**m) for m in config_dict["metrics"]]
            
            config_dict["variants"] = variants
            config_dict["metrics"] = metrics
            
            return TestConfiguration(**config_dict)
    
    def _get_test_results(self, test_id: str) -> List[TestResult]:
        """Get test results from database"""
        
        with sqlite3.connect(self.db_path) as conn:
            cursor = conn.execute("""
                SELECT result_id, test_id, variant_id, user_id, session_id, 
                       metrics, metadata, timestamp
                FROM test_results 
                WHERE test_id = ?
                ORDER BY timestamp
            """, (test_id,))
            
            results = []
            for row in cursor.fetchall():
                result = TestResult(
                    result_id=row[0],
                    test_id=row[1],
                    variant_id=row[2],
                    user_id=row[3],
                    session_id=row[4],
                    metrics=json.loads(row[5]),
                    metadata=json.loads(row[6]) if row[6] else {},
                    timestamp=datetime.fromisoformat(row[7])
                )
                results.append(result)
            
            return results
    
    def _generate_recommendations(self, config: TestConfiguration, 
                                results: List[TestResult], 
                                analysis: Optional[StatisticalAnalysis]) -> List[str]:
        """Generate recommendations based on test results"""
        
        recommendations = []
        
        if not results:
            recommendations.append("No data collected yet - ensure test is properly implemented")
            return recommendations
        
        # Check sample size
        total_samples = len(results)
        target_samples = config.sample_size_per_variant * len(config.variants)
        
        if total_samples < target_samples * 0.5:
            recommendations.append(f"Collect more data - only {total_samples}/{target_samples} target samples")
        
        # Check variant distribution
        variant_counts = {}
        for result in results:
            variant_counts[result.variant_id] = variant_counts.get(result.variant_id, 0) + 1
        
        if len(variant_counts) < len(config.variants):
            missing_variants = set(v.variant_id for v in config.variants) - set(variant_counts.keys())
            recommendations.append(f"Missing data for variants: {', '.join(missing_variants)}")
        
        # Analysis-based recommendations
        if analysis:
            if analysis.recommendation:
                recommendations.append(analysis.recommendation)
            
            # Check for low power
            if analysis.power_analysis:
                low_power_variants = [
                    v for v, power in analysis.power_analysis.items() 
                    if power < 0.8
                ]
                if low_power_variants:
                    recommendations.append(f"Increase sample size for variants: {', '.join(low_power_variants)}")
        
        return recommendations
    
    def _generate_key_insights(self, config: TestConfiguration, 
                             results: List[TestResult], 
                             analysis: Optional[StatisticalAnalysis]) -> List[str]:
        """Generate key insights from test results"""
        
        insights = []
        
        if not results:
            return insights
        
        # Basic insights
        insights.append(f"Collected {len(results)} samples across {len(set(r.variant_id for r in results))} variants")
        
        # Performance insights
        if analysis and analysis.variant_statistics:
            primary_metric = analysis.primary_metric
            
            variant_means = {}
            for variant_id, stats in analysis.variant_statistics.items():
                if primary_metric in stats and isinstance(stats[primary_metric], dict):
                    variant_means[variant_id] = stats[primary_metric]["mean"]
            
            if variant_means:
                best_variant = max(variant_means, key=variant_means.get)
                worst_variant = min(variant_means, key=variant_means.get)
                
                improvement = ((variant_means[best_variant] - variant_means[worst_variant]) / 
                             variant_means[worst_variant] * 100)
                
                insights.append(f"Best variant '{best_variant}' outperforms worst by {improvement:.1f}%")
        
        # Statistical insights
        if analysis and analysis.statistical_significance:
            significant_comparisons = sum(analysis.statistical_significance.values())
            total_comparisons = len(analysis.statistical_significance)
            
            if significant_comparisons > 0:
                insights.append(f"{significant_comparisons}/{total_comparisons} comparisons show statistical significance")
            else:
                insights.append("No statistically significant differences detected")
        
        return insights


# Factory function
def create_ab_test_manager(db_path: Optional[Path] = None) -> ABTestManager:
    """Create and configure an ABTestManager instance"""
    return ABTestManager(db_path)


# Example usage
if __name__ == "__main__":
    # Example usage
    manager = create_ab_test_manager()
    
    # Create test configuration
    variants = [
        TestVariant(
            variant_id="control",
            name="Original Prompt",
            description="Current prompt template",
            prompt_template="Complete the following task: {{task}}"
        ),
        TestVariant(
            variant_id="treatment",
            name="Optimized Prompt",
            description="Optimized prompt with better structure",
            prompt_template="Please carefully complete this task step by step: {{task}}\n\nThink through your approach first."
        )
    ]
    
    metrics = [
        TestMetric(
            metric_id="accuracy",
            name="Accuracy",
            description="Task completion accuracy",
            metric_type="primary",
            higher_is_better=True,
            minimum_detectable_effect=0.05
        ),
        TestMetric(
            metric_id="efficiency",
            name="Efficiency",
            description="Response efficiency score",
            metric_type="secondary",
            higher_is_better=True
        )
    ]
    
    config = TestConfiguration(
        test_id="prompt_optimization_001",
        name="Code Completion Prompt Optimization",
        description="Testing optimized prompts for code completion tasks",
        variants=variants,
        metrics=metrics,
        sample_size_per_variant=100,
        confidence_level=0.95
    )
    
    # Create and start test
    test_id = manager.create_test(config)
    manager.start_test(test_id)
    
    print(f"Created and started A/B test: {test_id}")