"""
PerformanceAnalyzer for comprehensive execution analysis.

This module analyzes execution metrics, identifies performance bottlenecks,
and generates detailed performance reports with recommendations.
"""

import json
import logging
import statistics
from datetime import datetime, timedelta
from pathlib import Path
from typing import Dict, List, Any, Optional, Tuple
from dataclasses import dataclass, asdict

from models.test_models import ExecutionMetrics, TestResult


@dataclass
class PerformanceAnalysis:
    """Performance analysis results"""
    overall_score: float
    execution_summary: Dict[str, Any]
    bottlenecks: List[Dict[str, Any]]
    recommendations: List[str]
    trends: Dict[str, Any]
    resource_usage: Dict[str, Any]
    comparative_analysis: Dict[str, Any]


@dataclass
class Bottleneck:
    """Performance bottleneck identification"""
    type: str  # 'execution_time', 'memory_usage', 'api_response', 'error_rate'
    severity: str  # 'critical', 'high', 'medium', 'low'
    description: str
    affected_components: List[str]
    impact_score: float
    recommendations: List[str]


class PerformanceAnalyzer:
    """
    Analyzes execution performance and generates comprehensive reports.
    
    Provides detailed analysis of execution metrics, identifies bottlenecks,
    and generates actionable recommendations for performance improvements.
    """
    
    def __init__(self, output_dir: Path = None):
        """
        Initialize the performance analyzer.
        
        Args:
            output_dir: Directory to save analysis reports
        """
        self.output_dir = output_dir or Path("reports/performance")
        self.output_dir.mkdir(parents=True, exist_ok=True)
        self.logger = logging.getLogger(__name__)
        
        # Performance thresholds
        self.thresholds = {
            'execution_time': {
                'excellent': 30.0,
                'good': 60.0,
                'acceptable': 120.0,
                'poor': 300.0
            },
            'memory_usage': {
                'excellent': 512.0,  # MB
                'good': 1024.0,
                'acceptable': 2048.0,
                'poor': 4096.0
            },
            'api_response_time': {
                'excellent': 1.0,
                'good': 3.0,
                'acceptable': 5.0,
                'poor': 10.0
            },
            'error_rate': {
                'excellent': 0.01,
                'good': 0.05,
                'acceptable': 0.10,
                'poor': 0.20
            }
        }
        
    def analyze_execution_metrics(self, metrics: ExecutionMetrics) -> PerformanceAnalysis:
        """
        Analyze execution metrics and generate comprehensive performance analysis.
        
        Args:
            metrics: Execution metrics to analyze
            
        Returns:
            Comprehensive performance analysis
        """
        # Calculate overall performance score
        overall_score = self._calculate_overall_score(metrics)
        
        # Generate execution summary
        execution_summary = self._generate_execution_summary(metrics)
        
        # Identify bottlenecks
        bottlenecks = self._identify_bottlenecks(metrics)
        
        # Generate recommendations
        recommendations = self._generate_recommendations(metrics, bottlenecks)
        
        # Analyze trends (if historical data available)
        trends = self._analyze_trends(metrics)
        
        # Analyze resource usage
        resource_usage = self._analyze_resource_usage(metrics)
        
        # Comparative analysis
        comparative_analysis = self._generate_comparative_analysis(metrics)
        
        analysis = PerformanceAnalysis(
            overall_score=overall_score,
            execution_summary=execution_summary,
            bottlenecks=[asdict(b) for b in bottlenecks],
            recommendations=recommendations,
            trends=trends,
            resource_usage=resource_usage,
            comparative_analysis=comparative_analysis
        )
        
        self.logger.info(f"Generated performance analysis with score: {overall_score:.2f}")
        return analysis
        
    def analyze_test_results_performance(self, test_results: List[TestResult]) -> PerformanceAnalysis:
        """
        Analyze performance from test results.
        
        Args:
            test_results: List of test results to analyze
            
        Returns:
            Performance analysis based on test results
        """
        # Extract metrics from test results
        execution_times = [r.execution_time for r in test_results if r.execution_time]
        
        # Create synthetic ExecutionMetrics from test results
        task_execution_times = {}
        memory_usage = {}
        api_response_times = {}
        success_rates = {}
        error_rates = {}
        
        for result in test_results:
            if result.execution_time:
                task_execution_times[result.test_id] = result.execution_time
            
            # Extract metrics from result metrics if available
            if result.metrics:
                if 'memory_usage' in result.metrics:
                    memory_usage[result.test_id] = result.metrics['memory_usage']
                if 'api_response_time' in result.metrics:
                    api_response_times[result.test_id] = result.metrics['api_response_time']
        
        # Calculate success/error rates by test type
        test_types = {}
        for result in test_results:
            test_type = result.test_type.value if hasattr(result.test_type, 'value') else str(result.test_type)
            status = result.status.value if hasattr(result.status, 'value') else str(result.status)
            
            if test_type not in test_types:
                test_types[test_type] = {'total': 0, 'passed': 0, 'failed': 0}
            
            test_types[test_type]['total'] += 1
            if status == 'passed':
                test_types[test_type]['passed'] += 1
            elif status == 'failed':
                test_types[test_type]['failed'] += 1
        
        for test_type, counts in test_types.items():
            if counts['total'] > 0:
                success_rates[test_type] = counts['passed'] / counts['total']
                error_rates[test_type] = counts['failed'] / counts['total']
        
        # Create ExecutionMetrics object
        metrics = ExecutionMetrics(
            total_execution_time=sum(execution_times),
            task_execution_times=task_execution_times,
            memory_usage=memory_usage,
            api_response_times=api_response_times,
            success_rates=success_rates,
            error_rates=error_rates
        )
        
        return self.analyze_execution_metrics(metrics)
        
    def generate_performance_report(self, analysis: PerformanceAnalysis) -> str:
        """
        Generate detailed performance report from analysis.
        
        Args:
            analysis: Performance analysis results
            
        Returns:
            Detailed performance report as markdown string
        """
        content = f"""# Performance Analysis Report

*Generated on {datetime.now().strftime('%Y-%m-%d %H:%M:%S')}*

## Executive Summary

**Overall Performance Score: {analysis.overall_score:.1f}/100**

{self._get_performance_rating(analysis.overall_score)}

## Key Metrics

### Execution Performance
- **Total Execution Time**: {analysis.execution_summary.get('total_execution_time', 0):.2f} seconds
- **Average Task Time**: {analysis.execution_summary.get('avg_task_time', 0):.2f} seconds
- **Fastest Task**: {analysis.execution_summary.get('fastest_task_time', 0):.2f} seconds
- **Slowest Task**: {analysis.execution_summary.get('slowest_task_time', 0):.2f} seconds

### Resource Usage
- **Peak Memory Usage**: {analysis.resource_usage.get('peak_memory', 0):.1f} MB
- **Average Memory Usage**: {analysis.resource_usage.get('avg_memory', 0):.1f} MB
- **Memory Efficiency**: {analysis.resource_usage.get('memory_efficiency', 0):.1f}%

### API Performance
- **Average API Response Time**: {analysis.execution_summary.get('avg_api_response_time', 0):.2f} seconds
- **API Success Rate**: {analysis.execution_summary.get('api_success_rate', 0):.1f}%
- **API Error Rate**: {analysis.execution_summary.get('api_error_rate', 0):.1f}%

## Performance Bottlenecks

{self._format_bottlenecks(analysis.bottlenecks)}

## Detailed Analysis

### Execution Time Analysis

{self._generate_execution_time_analysis(analysis)}

### Memory Usage Analysis

{self._generate_memory_usage_analysis(analysis)}

### API Performance Analysis

{self._generate_api_performance_analysis(analysis)}

### Error Rate Analysis

{self._generate_error_rate_analysis(analysis)}

## Comparative Analysis

{self._format_comparative_analysis(analysis.comparative_analysis)}

## Performance Trends

{self._format_trends(analysis.trends)}

## Recommendations

{self._format_recommendations(analysis.recommendations)}

## Performance Optimization Guide

### Immediate Actions (High Impact)

1. **Address Critical Bottlenecks**: Focus on bottlenecks marked as 'critical' severity
2. **Optimize Slowest Tasks**: Review and optimize tasks with execution times > 120 seconds
3. **Memory Management**: Implement memory optimization for tasks using > 2GB RAM

### Short-term Improvements (Medium Impact)

1. **API Response Optimization**: Implement caching for frequently accessed endpoints
2. **Parallel Processing**: Enable parallel execution for independent tasks
3. **Resource Pooling**: Implement connection pooling for external services

### Long-term Optimizations (Strategic)

1. **Architecture Review**: Consider microservices architecture for better scalability
2. **Caching Strategy**: Implement comprehensive caching at multiple levels
3. **Performance Monitoring**: Set up continuous performance monitoring

## Performance Benchmarks

### Task Performance Benchmarks

{self._generate_task_benchmarks(analysis)}

### System Resource Benchmarks

{self._generate_resource_benchmarks(analysis)}

## Monitoring Recommendations

### Key Performance Indicators (KPIs)

1. **Execution Time KPIs**
   - Average task execution time < 60 seconds
   - 95th percentile execution time < 120 seconds
   - Maximum execution time < 300 seconds

2. **Resource Usage KPIs**
   - Average memory usage < 1GB
   - Peak memory usage < 2GB
   - Memory efficiency > 80%

3. **API Performance KPIs**
   - Average API response time < 3 seconds
   - API success rate > 95%
   - API error rate < 5%

### Alerting Thresholds

- **Critical**: Execution time > 300 seconds, Memory usage > 4GB, Error rate > 20%
- **Warning**: Execution time > 120 seconds, Memory usage > 2GB, Error rate > 10%
- **Info**: Execution time > 60 seconds, Memory usage > 1GB, Error rate > 5%

## Performance Testing Strategy

### Load Testing

1. **Baseline Testing**: Establish performance baselines with standard workloads
2. **Stress Testing**: Test system limits with increased load
3. **Spike Testing**: Test system response to sudden load increases
4. **Volume Testing**: Test with large datasets and extended execution times

### Performance Regression Testing

1. **Automated Performance Tests**: Include performance tests in CI/CD pipeline
2. **Performance Budgets**: Set performance budgets for key metrics
3. **Regression Detection**: Automatically detect performance regressions
4. **Performance Reporting**: Generate performance reports for each release

## Appendix

### Raw Performance Data

```json
{json.dumps(asdict(analysis), indent=2, default=str)}
```

### Performance Analysis Methodology

This performance analysis uses the following methodology:

1. **Data Collection**: Gather execution metrics from test runs
2. **Bottleneck Identification**: Analyze metrics to identify performance bottlenecks
3. **Scoring Algorithm**: Calculate overall performance score based on weighted metrics
4. **Trend Analysis**: Analyze performance trends over time (if historical data available)
5. **Recommendation Generation**: Generate actionable recommendations based on analysis

### Performance Score Calculation

The overall performance score is calculated using the following weighted formula:

- Execution Time Performance: 40%
- Memory Usage Efficiency: 25%
- API Response Performance: 20%
- Error Rate Performance: 15%

Each component is scored from 0-100 based on predefined thresholds and combined to create the overall score.

---

*This performance analysis was automatically generated by the EvaluationEngineV1_0 testing framework.*
"""
        
        self.logger.info("Generated detailed performance report")
        return content
        
    def save_analysis_report(self, analysis: PerformanceAnalysis, filename: str = None) -> Path:
        """
        Save performance analysis report to file.
        
        Args:
            analysis: Performance analysis to save
            filename: Optional filename (auto-generated if not provided)
            
        Returns:
            Path to saved report file
        """
        if not filename:
            timestamp = datetime.now().strftime("%Y%m%d_%H%M%S")
            filename = f"performance_analysis_{timestamp}.json"
        
        filepath = self.output_dir / filename
        
        with open(filepath, 'w') as f:
            json.dump(asdict(analysis), f, indent=2, default=str)
        
        self.logger.info(f"Saved performance analysis to {filepath}")
        return filepath
        
    def compare_performance(self, current_metrics: ExecutionMetrics, 
                          baseline_metrics: ExecutionMetrics) -> Dict[str, Any]:
        """
        Compare current performance against baseline.
        
        Args:
            current_metrics: Current execution metrics
            baseline_metrics: Baseline metrics for comparison
            
        Returns:
            Performance comparison results
        """
        comparison = {
            'execution_time': {
                'current': current_metrics.total_execution_time,
                'baseline': baseline_metrics.total_execution_time,
                'change_percent': self._calculate_percent_change(
                    baseline_metrics.total_execution_time,
                    current_metrics.total_execution_time
                ),
                'improvement': current_metrics.total_execution_time < baseline_metrics.total_execution_time
            },
            'memory_usage': {},
            'api_response_times': {},
            'error_rates': {}
        }
        
        # Compare memory usage
        current_avg_memory = statistics.mean(current_metrics.memory_usage.values()) if current_metrics.memory_usage else 0
        baseline_avg_memory = statistics.mean(baseline_metrics.memory_usage.values()) if baseline_metrics.memory_usage else 0
        
        comparison['memory_usage'] = {
            'current': current_avg_memory,
            'baseline': baseline_avg_memory,
            'change_percent': self._calculate_percent_change(baseline_avg_memory, current_avg_memory),
            'improvement': current_avg_memory < baseline_avg_memory
        }
        
        # Compare API response times
        current_avg_api = statistics.mean(current_metrics.api_response_times.values()) if current_metrics.api_response_times else 0
        baseline_avg_api = statistics.mean(baseline_metrics.api_response_times.values()) if baseline_metrics.api_response_times else 0
        
        comparison['api_response_times'] = {
            'current': current_avg_api,
            'baseline': baseline_avg_api,
            'change_percent': self._calculate_percent_change(baseline_avg_api, current_avg_api),
            'improvement': current_avg_api < baseline_avg_api
        }
        
        # Compare error rates
        current_avg_error = statistics.mean(current_metrics.error_rates.values()) if current_metrics.error_rates else 0
        baseline_avg_error = statistics.mean(baseline_metrics.error_rates.values()) if baseline_metrics.error_rates else 0
        
        comparison['error_rates'] = {
            'current': current_avg_error,
            'baseline': baseline_avg_error,
            'change_percent': self._calculate_percent_change(baseline_avg_error, current_avg_error),
            'improvement': current_avg_error < baseline_avg_error
        }
        
        # Overall improvement assessment
        improvements = sum([
            comparison['execution_time']['improvement'],
            comparison['memory_usage']['improvement'],
            comparison['api_response_times']['improvement'],
            comparison['error_rates']['improvement']
        ])
        
        comparison['overall'] = {
            'improvements': improvements,
            'total_metrics': 4,
            'improvement_rate': improvements / 4,
            'overall_improvement': improvements >= 2
        }
        
        self.logger.info(f"Performance comparison completed: {improvements}/4 metrics improved")
        return comparison
        
    def _calculate_overall_score(self, metrics: ExecutionMetrics) -> float:
        """Calculate overall performance score."""
        scores = []
        weights = []
        
        # Execution time score (40% weight)
        exec_score = self._score_execution_time(metrics.total_execution_time)
        scores.append(exec_score)
        weights.append(0.4)
        
        # Memory usage score (25% weight)
        if metrics.memory_usage:
            avg_memory = statistics.mean(metrics.memory_usage.values())
            memory_score = self._score_memory_usage(avg_memory)
            scores.append(memory_score)
            weights.append(0.25)
        
        # API response time score (20% weight)
        if metrics.api_response_times:
            avg_api_time = statistics.mean(metrics.api_response_times.values())
            api_score = self._score_api_response_time(avg_api_time)
            scores.append(api_score)
            weights.append(0.2)
        
        # Error rate score (15% weight)
        if metrics.error_rates:
            avg_error_rate = statistics.mean(metrics.error_rates.values())
            error_score = self._score_error_rate(avg_error_rate)
            scores.append(error_score)
            weights.append(0.15)
        
        # Calculate weighted average
        if scores:
            total_weight = sum(weights)
            weighted_sum = sum(score * weight for score, weight in zip(scores, weights))
            return weighted_sum / total_weight
        
        return 0.0
        
    def _score_execution_time(self, execution_time: float) -> float:
        """Score execution time performance."""
        thresholds = self.thresholds['execution_time']
        
        if execution_time <= thresholds['excellent']:
            return 100.0
        elif execution_time <= thresholds['good']:
            return 85.0
        elif execution_time <= thresholds['acceptable']:
            return 70.0
        elif execution_time <= thresholds['poor']:
            return 50.0
        else:
            return max(0.0, 50.0 - (execution_time - thresholds['poor']) / 10)
            
    def _score_memory_usage(self, memory_usage: float) -> float:
        """Score memory usage performance."""
        thresholds = self.thresholds['memory_usage']
        
        if memory_usage <= thresholds['excellent']:
            return 100.0
        elif memory_usage <= thresholds['good']:
            return 85.0
        elif memory_usage <= thresholds['acceptable']:
            return 70.0
        elif memory_usage <= thresholds['poor']:
            return 50.0
        else:
            return max(0.0, 50.0 - (memory_usage - thresholds['poor']) / 100)
            
    def _score_api_response_time(self, response_time: float) -> float:
        """Score API response time performance."""
        thresholds = self.thresholds['api_response_time']
        
        if response_time <= thresholds['excellent']:
            return 100.0
        elif response_time <= thresholds['good']:
            return 85.0
        elif response_time <= thresholds['acceptable']:
            return 70.0
        elif response_time <= thresholds['poor']:
            return 50.0
        else:
            return max(0.0, 50.0 - (response_time - thresholds['poor']) * 5)
            
    def _score_error_rate(self, error_rate: float) -> float:
        """Score error rate performance."""
        thresholds = self.thresholds['error_rate']
        
        if error_rate <= thresholds['excellent']:
            return 100.0
        elif error_rate <= thresholds['good']:
            return 85.0
        elif error_rate <= thresholds['acceptable']:
            return 70.0
        elif error_rate <= thresholds['poor']:
            return 50.0
        else:
            return max(0.0, 50.0 - (error_rate - thresholds['poor']) * 100)
            
    def _generate_execution_summary(self, metrics: ExecutionMetrics) -> Dict[str, Any]:
        """Generate execution summary statistics."""
        task_times = list(metrics.task_execution_times.values())
        
        summary = {
            'total_execution_time': metrics.total_execution_time,
            'task_count': len(task_times),
            'avg_task_time': statistics.mean(task_times) if task_times else 0,
            'median_task_time': statistics.median(task_times) if task_times else 0,
            'fastest_task_time': min(task_times) if task_times else 0,
            'slowest_task_time': max(task_times) if task_times else 0,
            'task_time_std': statistics.stdev(task_times) if len(task_times) > 1 else 0
        }
        
        # API metrics
        if metrics.api_response_times:
            api_times = list(metrics.api_response_times.values())
            summary.update({
                'avg_api_response_time': statistics.mean(api_times),
                'median_api_response_time': statistics.median(api_times),
                'fastest_api_response': min(api_times),
                'slowest_api_response': max(api_times)
            })
        
        # Success/error rates
        if metrics.success_rates:
            summary['avg_success_rate'] = statistics.mean(metrics.success_rates.values()) * 100
        if metrics.error_rates:
            summary['avg_error_rate'] = statistics.mean(metrics.error_rates.values()) * 100
            
        return summary
        
    def _identify_bottlenecks(self, metrics: ExecutionMetrics) -> List[Bottleneck]:
        """Identify performance bottlenecks."""
        bottlenecks = []
        
        # Execution time bottlenecks
        if metrics.total_execution_time > self.thresholds['execution_time']['poor']:
            bottlenecks.append(Bottleneck(
                type='execution_time',
                severity='critical',
                description=f"Total execution time ({metrics.total_execution_time:.1f}s) exceeds acceptable threshold",
                affected_components=['overall_execution'],
                impact_score=0.9,
                recommendations=[
                    "Optimize slowest tasks",
                    "Implement parallel processing",
                    "Review algorithm efficiency"
                ]
            ))
        
        # Memory usage bottlenecks
        if metrics.memory_usage:
            peak_memory = max(metrics.memory_usage.values())
            if peak_memory > self.thresholds['memory_usage']['poor']:
                bottlenecks.append(Bottleneck(
                    type='memory_usage',
                    severity='high',
                    description=f"Peak memory usage ({peak_memory:.1f}MB) exceeds acceptable threshold",
                    affected_components=['memory_management'],
                    impact_score=0.7,
                    recommendations=[
                        "Implement memory optimization",
                        "Add garbage collection",
                        "Review data structures"
                    ]
                ))
        
        # API response time bottlenecks
        if metrics.api_response_times:
            slow_apis = {k: v for k, v in metrics.api_response_times.items() 
                        if v > self.thresholds['api_response_time']['acceptable']}
            if slow_apis:
                bottlenecks.append(Bottleneck(
                    type='api_response',
                    severity='medium',
                    description=f"{len(slow_apis)} API endpoints have slow response times",
                    affected_components=list(slow_apis.keys()),
                    impact_score=0.5,
                    recommendations=[
                        "Implement API caching",
                        "Optimize database queries",
                        "Add connection pooling"
                    ]
                ))
        
        # Error rate bottlenecks
        if metrics.error_rates:
            high_error_components = {k: v for k, v in metrics.error_rates.items() 
                                   if v > self.thresholds['error_rate']['acceptable']}
            if high_error_components:
                bottlenecks.append(Bottleneck(
                    type='error_rate',
                    severity='high',
                    description=f"{len(high_error_components)} components have high error rates",
                    affected_components=list(high_error_components.keys()),
                    impact_score=0.8,
                    recommendations=[
                        "Improve error handling",
                        "Add retry mechanisms",
                        "Review component reliability"
                    ]
                ))
        
        return bottlenecks
        
    def _generate_recommendations(self, metrics: ExecutionMetrics, bottlenecks: List[Bottleneck]) -> List[str]:
        """Generate performance improvement recommendations."""
        recommendations = []
        
        # Add bottleneck-specific recommendations
        for bottleneck in bottlenecks:
            recommendations.extend(bottleneck.recommendations)
        
        # Add general recommendations based on metrics
        if metrics.total_execution_time > self.thresholds['execution_time']['good']:
            recommendations.append("Consider implementing asynchronous processing for long-running tasks")
        
        if metrics.memory_usage and max(metrics.memory_usage.values()) > self.thresholds['memory_usage']['good']:
            recommendations.append("Implement memory profiling to identify memory leaks")
        
        if metrics.api_response_times and statistics.mean(metrics.api_response_times.values()) > self.thresholds['api_response_time']['good']:
            recommendations.append("Add API response caching to improve performance")
        
        # Remove duplicates while preserving order
        seen = set()
        unique_recommendations = []
        for rec in recommendations:
            if rec not in seen:
                seen.add(rec)
                unique_recommendations.append(rec)
        
        return unique_recommendations
        
    def _analyze_trends(self, metrics: ExecutionMetrics) -> Dict[str, Any]:
        """Analyze performance trends (placeholder for historical data)."""
        # This would analyze historical data if available
        return {
            'trend_analysis': 'Historical data not available',
            'performance_direction': 'unknown',
            'trend_confidence': 0.0
        }
        
    def _analyze_resource_usage(self, metrics: ExecutionMetrics) -> Dict[str, Any]:
        """Analyze resource usage patterns."""
        resource_analysis = {}
        
        if metrics.memory_usage:
            memory_values = list(metrics.memory_usage.values())
            resource_analysis['memory'] = {
                'peak_usage': max(memory_values),
                'avg_usage': statistics.mean(memory_values),
                'min_usage': min(memory_values),
                'usage_variance': statistics.variance(memory_values) if len(memory_values) > 1 else 0,
                'efficiency_score': self._calculate_memory_efficiency(memory_values)
            }
        
        return resource_analysis
        
    def _generate_comparative_analysis(self, metrics: ExecutionMetrics) -> Dict[str, Any]:
        """Generate comparative analysis against benchmarks."""
        return {
            'benchmark_comparison': 'Baseline benchmarks not available',
            'industry_comparison': 'Industry benchmarks not available',
            'relative_performance': 'unknown'
        }
        
    def _calculate_percent_change(self, baseline: float, current: float) -> float:
        """Calculate percentage change between baseline and current values."""
        if baseline == 0:
            return 0.0 if current == 0 else 100.0
        return ((current - baseline) / baseline) * 100
        
    def _calculate_memory_efficiency(self, memory_values: List[float]) -> float:
        """Calculate memory usage efficiency score."""
        if not memory_values:
            return 0.0
        
        peak_memory = max(memory_values)
        avg_memory = statistics.mean(memory_values)
        
        # Efficiency is higher when average is closer to peak (less variance)
        efficiency = (avg_memory / peak_memory) * 100 if peak_memory > 0 else 0
        return min(100.0, efficiency)
        
    def _get_performance_rating(self, score: float) -> str:
        """Get performance rating description based on score."""
        if score >= 90:
            return "🟢 **Excellent Performance** - System is performing optimally with minimal bottlenecks."
        elif score >= 75:
            return "🟡 **Good Performance** - System is performing well with minor optimization opportunities."
        elif score >= 60:
            return "🟠 **Acceptable Performance** - System is functional but has room for improvement."
        elif score >= 40:
            return "🔴 **Poor Performance** - System has significant performance issues that need attention."
        else:
            return "🚨 **Critical Performance Issues** - System requires immediate optimization."
            
    def _format_bottlenecks(self, bottlenecks: List[Dict[str, Any]]) -> str:
        """Format bottlenecks for report display."""
        if not bottlenecks:
            return "✅ No significant performance bottlenecks identified."
        
        formatted = []
        for bottleneck in bottlenecks:
            severity_icon = {
                'critical': '🚨',
                'high': '🔴',
                'medium': '🟠',
                'low': '🟡'
            }.get(bottleneck['severity'], '⚪')
            
            formatted.append(f"""
### {severity_icon} {bottleneck['type'].replace('_', ' ').title()} - {bottleneck['severity'].title()} Severity

**Description:** {bottleneck['description']}

**Impact Score:** {bottleneck['impact_score']:.1f}/1.0

**Affected Components:** {', '.join(bottleneck['affected_components'])}

**Recommendations:**
{chr(10).join(f"- {rec}" for rec in bottleneck['recommendations'])}
""")
        
        return '\n'.join(formatted)
        
    def _format_recommendations(self, recommendations: List[str]) -> str:
        """Format recommendations for report display."""
        if not recommendations:
            return "No specific recommendations at this time."
        
        formatted = []
        for i, rec in enumerate(recommendations, 1):
            formatted.append(f"{i}. {rec}")
        
        return '\n'.join(formatted)
        
    def _format_comparative_analysis(self, analysis: Dict[str, Any]) -> str:
        """Format comparative analysis for report display."""
        return f"""
**Benchmark Comparison:** {analysis.get('benchmark_comparison', 'Not available')}

**Industry Comparison:** {analysis.get('industry_comparison', 'Not available')}

**Relative Performance:** {analysis.get('relative_performance', 'Unknown')}
"""
        
    def _format_trends(self, trends: Dict[str, Any]) -> str:
        """Format trends analysis for report display."""
        return f"""
**Trend Analysis:** {trends.get('trend_analysis', 'Not available')}

**Performance Direction:** {trends.get('performance_direction', 'Unknown')}

**Trend Confidence:** {trends.get('trend_confidence', 0):.1f}%
"""
        
    def _generate_execution_time_analysis(self, analysis: PerformanceAnalysis) -> str:
        """Generate detailed execution time analysis."""
        return f"""
The execution time analysis shows:

- **Total execution time:** {analysis.execution_summary.get('total_execution_time', 0):.2f} seconds
- **Average task time:** {analysis.execution_summary.get('avg_task_time', 0):.2f} seconds
- **Performance variance:** {analysis.execution_summary.get('task_time_std', 0):.2f} seconds

**Analysis:** {'Tasks show consistent performance' if analysis.execution_summary.get('task_time_std', 0) < 30 else 'High variance in task execution times indicates optimization opportunities'}
"""
        
    def _generate_memory_usage_analysis(self, analysis: PerformanceAnalysis) -> str:
        """Generate detailed memory usage analysis."""
        peak_memory = analysis.resource_usage.get('memory', {}).get('peak_usage', 0)
        avg_memory = analysis.resource_usage.get('memory', {}).get('avg_usage', 0)
        
        return f"""
The memory usage analysis shows:

- **Peak memory usage:** {peak_memory:.1f} MB
- **Average memory usage:** {avg_memory:.1f} MB
- **Memory efficiency:** {analysis.resource_usage.get('memory', {}).get('efficiency_score', 0):.1f}%

**Analysis:** {'Memory usage is well-optimized' if peak_memory < 1024 else 'Consider memory optimization strategies'}
"""
        
    def _generate_api_performance_analysis(self, analysis: PerformanceAnalysis) -> str:
        """Generate detailed API performance analysis."""
        avg_api_time = analysis.execution_summary.get('avg_api_response_time', 0)
        
        return f"""
The API performance analysis shows:

- **Average API response time:** {avg_api_time:.2f} seconds
- **API success rate:** {analysis.execution_summary.get('avg_success_rate', 0):.1f}%

**Analysis:** {'API performance is optimal' if avg_api_time < 3 else 'API response times could be improved'}
"""
        
    def _generate_error_rate_analysis(self, analysis: PerformanceAnalysis) -> str:
        """Generate detailed error rate analysis."""
        error_rate = analysis.execution_summary.get('avg_error_rate', 0)
        
        return f"""
The error rate analysis shows:

- **Average error rate:** {error_rate:.1f}%

**Analysis:** {'Error rates are within acceptable limits' if error_rate < 5 else 'Error rates require attention'}
"""
        
    def _generate_task_benchmarks(self, analysis: PerformanceAnalysis) -> str:
        """Generate task performance benchmarks."""
        return f"""
| Metric | Excellent | Good | Acceptable | Poor |
|--------|-----------|------|------------|------|
| Execution Time | < 30s | < 60s | < 120s | > 300s |
| Memory Usage | < 512MB | < 1GB | < 2GB | > 4GB |
| API Response | < 1s | < 3s | < 5s | > 10s |
| Error Rate | < 1% | < 5% | < 10% | > 20% |

**Current Performance:**
- Execution Time: {analysis.execution_summary.get('avg_task_time', 0):.1f}s
- Memory Usage: {analysis.resource_usage.get('memory', {}).get('avg_usage', 0):.1f}MB
- API Response: {analysis.execution_summary.get('avg_api_response_time', 0):.1f}s
- Error Rate: {analysis.execution_summary.get('avg_error_rate', 0):.1f}%
"""
        
    def _generate_resource_benchmarks(self, analysis: PerformanceAnalysis) -> str:
        """Generate system resource benchmarks."""
        return f"""
**CPU Utilization:** Not measured (consider adding CPU monitoring)

**Memory Utilization:**
- Peak: {analysis.resource_usage.get('memory', {}).get('peak_usage', 0):.1f}MB
- Average: {analysis.resource_usage.get('memory', {}).get('avg_usage', 0):.1f}MB
- Efficiency: {analysis.resource_usage.get('memory', {}).get('efficiency_score', 0):.1f}%

**Network I/O:** Not measured (consider adding network monitoring)

**Disk I/O:** Not measured (consider adding disk monitoring)
"""