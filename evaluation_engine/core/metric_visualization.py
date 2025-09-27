"""
Metric Visualization and Analysis Tools.

This module provides visualization capabilities and comparative analysis
tools for comprehensive evaluation metrics.
"""

import json
import statistics
from typing import Dict, List, Any, Optional, Tuple
from dataclasses import dataclass
from enum import Enum
import math

from .metrics_engine import MetricResult, MetricType


class ChartType(Enum):
    """Types of charts for visualization."""
    BAR_CHART = "bar_chart"
    LINE_CHART = "line_chart"
    SCATTER_PLOT = "scatter_plot"
    HISTOGRAM = "histogram"
    BOX_PLOT = "box_plot"
    HEATMAP = "heatmap"
    RADAR_CHART = "radar_chart"
    TREEMAP = "treemap"


class VisualizationFormat(Enum):
    """Output formats for visualizations."""
    JSON = "json"
    HTML = "html"
    SVG = "svg"
    PNG = "png"
    PDF = "pdf"


@dataclass
class ChartConfig:
    """Configuration for chart generation."""
    chart_type: ChartType
    title: str
    x_axis_label: str = ""
    y_axis_label: str = ""
    width: int = 800
    height: int = 600
    color_scheme: str = "default"
    interactive: bool = True
    show_legend: bool = True
    show_grid: bool = True


@dataclass
class VisualizationData:
    """Data structure for visualization."""
    data: List[Dict[str, Any]]
    metadata: Dict[str, Any]
    chart_config: ChartConfig


class MetricVisualizationEngine:
    """
    Engine for generating metric visualizations and comparative analysis.
    """
    
    def __init__(self):
        """Initialize the visualization engine."""
        self.color_schemes = {
            'default': ['#1f77b4', '#ff7f0e', '#2ca02c', '#d62728', '#9467bd'],
            'pastel': ['#aec7e8', '#ffbb78', '#98df8a', '#ff9896', '#c5b0d5'],
            'dark': ['#1f1f1f', '#ff6b6b', '#4ecdc4', '#45b7d1', '#96ceb4'],
            'professional': ['#2c3e50', '#3498db', '#e74c3c', '#f39c12', '#27ae60']
        }
        
        self.chart_templates = self._initialize_chart_templates()
    
    def _initialize_chart_templates(self) -> Dict[ChartType, Dict[str, Any]]:
        """Initialize chart templates."""
        return {
            ChartType.BAR_CHART: {
                'type': 'bar',
                'layout': {
                    'title': '',
                    'xaxis': {'title': ''},
                    'yaxis': {'title': ''},
                    'showlegend': True
                }
            },
            ChartType.LINE_CHART: {
                'type': 'scatter',
                'mode': 'lines+markers',
                'layout': {
                    'title': '',
                    'xaxis': {'title': ''},
                    'yaxis': {'title': ''},
                    'showlegend': True
                }
            },
            ChartType.SCATTER_PLOT: {
                'type': 'scatter',
                'mode': 'markers',
                'layout': {
                    'title': '',
                    'xaxis': {'title': ''},
                    'yaxis': {'title': ''},
                    'showlegend': True
                }
            },
            ChartType.HISTOGRAM: {
                'type': 'histogram',
                'layout': {
                    'title': '',
                    'xaxis': {'title': ''},
                    'yaxis': {'title': 'Frequency'},
                    'showlegend': False
                }
            },
            ChartType.BOX_PLOT: {
                'type': 'box',
                'layout': {
                    'title': '',
                    'xaxis': {'title': ''},
                    'yaxis': {'title': ''},
                    'showlegend': False
                }
            },
            ChartType.HEATMAP: {
                'type': 'heatmap',
                'layout': {
                    'title': '',
                    'xaxis': {'title': ''},
                    'yaxis': {'title': ''}
                }
            },
            ChartType.RADAR_CHART: {
                'type': 'scatterpolar',
                'mode': 'lines+markers',
                'fill': 'toself',
                'layout': {
                    'title': '',
                    'polar': {
                        'radialaxis': {'visible': True, 'range': [0, 1]}
                    },
                    'showlegend': True
                }
            }
        }
    
    def create_metric_comparison_chart(self, 
                                     evaluation_results: List[Dict[str, Any]],
                                     metrics_to_compare: List[str],
                                     chart_type: ChartType = ChartType.BAR_CHART,
                                     title: str = "Metric Comparison") -> VisualizationData:
        """
        Create a chart comparing metrics across evaluations.
        
        Args:
            evaluation_results: List of evaluation results
            metrics_to_compare: List of metric names to compare
            chart_type: Type of chart to generate
            title: Chart title
            
        Returns:
            Visualization data structure
        """
        chart_data = []
        
        if chart_type == ChartType.BAR_CHART:
            chart_data = self._create_bar_chart_data(evaluation_results, metrics_to_compare)
        elif chart_type == ChartType.RADAR_CHART:
            chart_data = self._create_radar_chart_data(evaluation_results, metrics_to_compare)
        elif chart_type == ChartType.LINE_CHART:
            chart_data = self._create_line_chart_data(evaluation_results, metrics_to_compare)
        elif chart_type == ChartType.HEATMAP:
            chart_data = self._create_heatmap_data(evaluation_results, metrics_to_compare)
        
        config = ChartConfig(
            chart_type=chart_type,
            title=title,
            x_axis_label="Evaluations" if chart_type != ChartType.RADAR_CHART else "",
            y_axis_label="Metric Values" if chart_type != ChartType.RADAR_CHART else ""
        )
        
        return VisualizationData(
            data=chart_data,
            metadata={
                'metrics_compared': metrics_to_compare,
                'evaluation_count': len(evaluation_results),
                'chart_type': chart_type.value
            },
            chart_config=config
        )
    
    def _create_bar_chart_data(self, 
                             evaluation_results: List[Dict[str, Any]], 
                             metrics: List[str]) -> List[Dict[str, Any]]:
        """Create data for bar chart."""
        chart_data = []
        
        for metric_name in metrics:
            values = []
            labels = []
            
            for i, result in enumerate(evaluation_results):
                eval_metrics = result.get('metrics', {})
                if metric_name in eval_metrics:
                    metric = eval_metrics[metric_name]
                    value = metric.value if hasattr(metric, 'value') else metric
                    values.append(value)
                    labels.append(result.get('evaluation_id', f'Eval {i+1}'))
            
            if values:
                chart_data.append({
                    'x': labels,
                    'y': values,
                    'name': metric_name,
                    'type': 'bar'
                })
        
        return chart_data
    
    def _create_radar_chart_data(self, 
                               evaluation_results: List[Dict[str, Any]], 
                               metrics: List[str]) -> List[Dict[str, Any]]:
        """Create data for radar chart."""
        chart_data = []
        
        for i, result in enumerate(evaluation_results):
            eval_metrics = result.get('metrics', {})
            
            theta = []  # Metric names
            r = []      # Metric values
            
            for metric_name in metrics:
                if metric_name in eval_metrics:
                    metric = eval_metrics[metric_name]
                    value = metric.value if hasattr(metric, 'value') else metric
                    theta.append(metric_name)
                    r.append(value)
            
            if theta and r:
                # Close the radar chart
                theta.append(theta[0])
                r.append(r[0])
                
                chart_data.append({
                    'theta': theta,
                    'r': r,
                    'name': result.get('evaluation_id', f'Eval {i+1}'),
                    'type': 'scatterpolar',
                    'mode': 'lines+markers',
                    'fill': 'toself'
                })
        
        return chart_data
    
    def _create_line_chart_data(self, 
                              evaluation_results: List[Dict[str, Any]], 
                              metrics: List[str]) -> List[Dict[str, Any]]:
        """Create data for line chart."""
        chart_data = []
        
        for metric_name in metrics:
            x_values = []
            y_values = []
            
            for i, result in enumerate(evaluation_results):
                eval_metrics = result.get('metrics', {})
                if metric_name in eval_metrics:
                    metric = eval_metrics[metric_name]
                    value = metric.value if hasattr(metric, 'value') else metric
                    x_values.append(i)
                    y_values.append(value)
            
            if x_values and y_values:
                chart_data.append({
                    'x': x_values,
                    'y': y_values,
                    'name': metric_name,
                    'type': 'scatter',
                    'mode': 'lines+markers'
                })
        
        return chart_data
    
    def _create_heatmap_data(self, 
                           evaluation_results: List[Dict[str, Any]], 
                           metrics: List[str]) -> List[Dict[str, Any]]:
        """Create data for heatmap."""
        # Create matrix of metric values
        z_values = []
        y_labels = []
        x_labels = [result.get('evaluation_id', f'Eval {i+1}') 
                   for i, result in enumerate(evaluation_results)]
        
        for metric_name in metrics:
            row = []
            for result in evaluation_results:
                eval_metrics = result.get('metrics', {})
                if metric_name in eval_metrics:
                    metric = eval_metrics[metric_name]
                    value = metric.value if hasattr(metric, 'value') else metric
                    row.append(value)
                else:
                    row.append(0.0)
            
            z_values.append(row)
            y_labels.append(metric_name)
        
        return [{
            'z': z_values,
            'x': x_labels,
            'y': y_labels,
            'type': 'heatmap',
            'colorscale': 'Viridis'
        }]
    
    def create_performance_distribution_chart(self, 
                                            metric_results: Dict[str, List[float]],
                                            chart_type: ChartType = ChartType.BOX_PLOT) -> VisualizationData:
        """
        Create a chart showing performance distribution.
        
        Args:
            metric_results: Dictionary mapping metric names to lists of values
            chart_type: Type of chart to generate
            
        Returns:
            Visualization data structure
        """
        chart_data = []
        
        if chart_type == ChartType.BOX_PLOT:
            for metric_name, values in metric_results.items():
                chart_data.append({
                    'y': values,
                    'name': metric_name,
                    'type': 'box'
                })
        
        elif chart_type == ChartType.HISTOGRAM:
            for metric_name, values in metric_results.items():
                chart_data.append({
                    'x': values,
                    'name': metric_name,
                    'type': 'histogram',
                    'opacity': 0.7
                })
        
        config = ChartConfig(
            chart_type=chart_type,
            title="Performance Distribution",
            x_axis_label="Metrics" if chart_type == ChartType.BOX_PLOT else "Values",
            y_axis_label="Values" if chart_type == ChartType.BOX_PLOT else "Frequency"
        )
        
        return VisualizationData(
            data=chart_data,
            metadata={
                'metrics_analyzed': list(metric_results.keys()),
                'total_values': sum(len(values) for values in metric_results.values())
            },
            chart_config=config
        )
    
    def create_correlation_heatmap(self, 
                                 evaluation_results: List[Dict[str, Any]],
                                 metrics_to_analyze: Optional[List[str]] = None) -> VisualizationData:
        """
        Create a correlation heatmap between metrics.
        
        Args:
            evaluation_results: List of evaluation results
            metrics_to_analyze: Optional list of metrics to analyze
            
        Returns:
            Visualization data structure
        """
        # Extract metric values
        all_metrics = {}
        for result in evaluation_results:
            eval_metrics = result.get('metrics', {})
            for metric_name, metric in eval_metrics.items():
                if metrics_to_analyze is None or metric_name in metrics_to_analyze:
                    if metric_name not in all_metrics:
                        all_metrics[metric_name] = []
                    
                    value = metric.value if hasattr(metric, 'value') else metric
                    all_metrics[metric_name].append(value)
        
        # Calculate correlation matrix
        metric_names = list(all_metrics.keys())
        correlation_matrix = []
        
        for metric1 in metric_names:
            row = []
            for metric2 in metric_names:
                if metric1 == metric2:
                    correlation = 1.0
                else:
                    correlation = self._calculate_correlation(
                        all_metrics[metric1], all_metrics[metric2]
                    )
                row.append(correlation)
            correlation_matrix.append(row)
        
        chart_data = [{
            'z': correlation_matrix,
            'x': metric_names,
            'y': metric_names,
            'type': 'heatmap',
            'colorscale': 'RdBu',
            'zmid': 0
        }]
        
        config = ChartConfig(
            chart_type=ChartType.HEATMAP,
            title="Metric Correlation Matrix",
            x_axis_label="Metrics",
            y_axis_label="Metrics"
        )
        
        return VisualizationData(
            data=chart_data,
            metadata={
                'metrics_analyzed': metric_names,
                'correlation_matrix': correlation_matrix
            },
            chart_config=config
        )
    
    def create_trend_analysis_chart(self, 
                                  time_series_data: List[Dict[str, Any]],
                                  metrics_to_track: List[str]) -> VisualizationData:
        """
        Create a trend analysis chart over time.
        
        Args:
            time_series_data: List of time-stamped evaluation results
            metrics_to_track: List of metrics to track over time
            
        Returns:
            Visualization data structure
        """
        chart_data = []
        
        for metric_name in metrics_to_track:
            timestamps = []
            values = []
            
            for data_point in time_series_data:
                if 'timestamp' in data_point and 'metrics' in data_point:
                    eval_metrics = data_point['metrics']
                    if metric_name in eval_metrics:
                        metric = eval_metrics[metric_name]
                        value = metric.value if hasattr(metric, 'value') else metric
                        timestamps.append(data_point['timestamp'])
                        values.append(value)
            
            if timestamps and values:
                chart_data.append({
                    'x': timestamps,
                    'y': values,
                    'name': metric_name,
                    'type': 'scatter',
                    'mode': 'lines+markers'
                })
        
        config = ChartConfig(
            chart_type=ChartType.LINE_CHART,
            title="Metric Trends Over Time",
            x_axis_label="Time",
            y_axis_label="Metric Values"
        )
        
        return VisualizationData(
            data=chart_data,
            metadata={
                'metrics_tracked': metrics_to_track,
                'time_range': {
                    'start': min(dp['timestamp'] for dp in time_series_data if 'timestamp' in dp),
                    'end': max(dp['timestamp'] for dp in time_series_data if 'timestamp' in dp)
                } if time_series_data else None
            },
            chart_config=config
        )
    
    def generate_dashboard_data(self, 
                              evaluation_results: List[Dict[str, Any]],
                              key_metrics: Optional[List[str]] = None) -> Dict[str, Any]:
        """
        Generate comprehensive dashboard data.
        
        Args:
            evaluation_results: List of evaluation results
            key_metrics: Optional list of key metrics to highlight
            
        Returns:
            Dashboard data structure
        """
        if not evaluation_results:
            return {}
        
        # Extract all metrics if not specified
        if key_metrics is None:
            all_metric_names = set()
            for result in evaluation_results:
                eval_metrics = result.get('metrics', {})
                all_metric_names.update(eval_metrics.keys())
            key_metrics = list(all_metric_names)[:10]  # Limit to top 10
        
        dashboard_data = {
            'summary': self._generate_summary_stats(evaluation_results, key_metrics),
            'charts': {},
            'tables': {},
            'alerts': []
        }
        
        # Generate key charts
        dashboard_data['charts']['metric_comparison'] = self.create_metric_comparison_chart(
            evaluation_results, key_metrics, ChartType.BAR_CHART, "Key Metrics Comparison"
        )
        
        dashboard_data['charts']['performance_radar'] = self.create_metric_comparison_chart(
            evaluation_results[:5], key_metrics, ChartType.RADAR_CHART, "Performance Radar"
        )
        
        # Extract metric values for distribution analysis
        metric_values = {}
        for metric_name in key_metrics:
            values = []
            for result in evaluation_results:
                eval_metrics = result.get('metrics', {})
                if metric_name in eval_metrics:
                    metric = eval_metrics[metric_name]
                    value = metric.value if hasattr(metric, 'value') else metric
                    values.append(value)
            if values:
                metric_values[metric_name] = values
        
        if metric_values:
            dashboard_data['charts']['distribution'] = self.create_performance_distribution_chart(
                metric_values, ChartType.BOX_PLOT
            )
            
            dashboard_data['charts']['correlation'] = self.create_correlation_heatmap(
                evaluation_results, key_metrics
            )
        
        # Generate ranking table
        dashboard_data['tables']['rankings'] = self._generate_ranking_table(
            evaluation_results, key_metrics
        )
        
        # Generate alerts
        dashboard_data['alerts'] = self._generate_alerts(evaluation_results, key_metrics)
        
        return dashboard_data
    
    def _generate_summary_stats(self, 
                              evaluation_results: List[Dict[str, Any]], 
                              metrics: List[str]) -> Dict[str, Any]:
        """Generate summary statistics."""
        summary = {
            'total_evaluations': len(evaluation_results),
            'metrics_analyzed': len(metrics),
            'metric_statistics': {}
        }
        
        for metric_name in metrics:
            values = []
            for result in evaluation_results:
                eval_metrics = result.get('metrics', {})
                if metric_name in eval_metrics:
                    metric = eval_metrics[metric_name]
                    value = metric.value if hasattr(metric, 'value') else metric
                    values.append(value)
            
            if values:
                summary['metric_statistics'][metric_name] = {
                    'mean': statistics.mean(values),
                    'median': statistics.median(values),
                    'std_dev': statistics.stdev(values) if len(values) > 1 else 0.0,
                    'min': min(values),
                    'max': max(values),
                    'count': len(values)
                }
        
        return summary
    
    def _generate_ranking_table(self, 
                              evaluation_results: List[Dict[str, Any]], 
                              metrics: List[str]) -> Dict[str, Any]:
        """Generate ranking table data."""
        # Calculate composite scores for ranking
        scored_results = []
        
        for result in evaluation_results:
            eval_metrics = result.get('metrics', {})
            
            # Calculate average score across key metrics
            scores = []
            for metric_name in metrics:
                if metric_name in eval_metrics:
                    metric = eval_metrics[metric_name]
                    value = metric.value if hasattr(metric, 'value') else metric
                    scores.append(value)
            
            avg_score = statistics.mean(scores) if scores else 0.0
            
            scored_results.append({
                'evaluation_id': result.get('evaluation_id', 'Unknown'),
                'model': result.get('model', 'Unknown'),
                'composite_score': avg_score,
                'individual_scores': {
                    metric: eval_metrics[metric].value 
                    if hasattr(eval_metrics[metric], 'value') 
                    else eval_metrics[metric]
                    for metric in metrics
                    if metric in eval_metrics
                }
            })
        
        # Sort by composite score
        scored_results.sort(key=lambda x: x['composite_score'], reverse=True)
        
        # Add ranks
        for i, result in enumerate(scored_results):
            result['rank'] = i + 1
        
        return {
            'columns': ['rank', 'evaluation_id', 'model', 'composite_score'] + metrics,
            'data': scored_results[:20]  # Top 20
        }
    
    def _generate_alerts(self, 
                       evaluation_results: List[Dict[str, Any]], 
                       metrics: List[str]) -> List[Dict[str, Any]]:
        """Generate alerts based on metric analysis."""
        alerts = []
        
        # Analyze each metric for potential issues
        for metric_name in metrics:
            values = []
            for result in evaluation_results:
                eval_metrics = result.get('metrics', {})
                if metric_name in eval_metrics:
                    metric = eval_metrics[metric_name]
                    value = metric.value if hasattr(metric, 'value') else metric
                    values.append(value)
            
            if not values:
                continue
            
            mean_val = statistics.mean(values)
            std_val = statistics.stdev(values) if len(values) > 1 else 0.0
            
            # Low performance alert
            if mean_val < 0.3:
                alerts.append({
                    'type': 'warning',
                    'metric': metric_name,
                    'message': f"Low average performance in {metric_name}: {mean_val:.3f}",
                    'severity': 'high' if mean_val < 0.2 else 'medium'
                })
            
            # High variance alert
            if std_val > 0.3:
                alerts.append({
                    'type': 'info',
                    'metric': metric_name,
                    'message': f"High variance in {metric_name}: σ={std_val:.3f}",
                    'severity': 'medium'
                })
            
            # Outlier detection
            if len(values) >= 4:
                try:
                    q1, q3 = statistics.quantiles(values, n=4)[0], statistics.quantiles(values, n=4)[2]
                    iqr = q3 - q1
                    lower_bound = q1 - 1.5 * iqr
                    upper_bound = q3 + 1.5 * iqr
                    
                    outliers = [v for v in values if v < lower_bound or v > upper_bound]
                    if outliers:
                        alerts.append({
                            'type': 'info',
                            'metric': metric_name,
                            'message': f"Outliers detected in {metric_name}: {len(outliers)} values",
                            'severity': 'low'
                        })
                except Exception:
                    pass
        
        return alerts
    
    def _calculate_correlation(self, values1: List[float], values2: List[float]) -> float:
        """Calculate Pearson correlation coefficient."""
        if len(values1) != len(values2) or len(values1) < 2:
            return 0.0
        
        try:
            mean1 = statistics.mean(values1)
            mean2 = statistics.mean(values2)
            
            numerator = sum((x - mean1) * (y - mean2) for x, y in zip(values1, values2))
            
            sum_sq1 = sum((x - mean1) ** 2 for x in values1)
            sum_sq2 = sum((y - mean2) ** 2 for y in values2)
            
            denominator = math.sqrt(sum_sq1 * sum_sq2)
            
            if denominator == 0:
                return 0.0
            
            return numerator / denominator
        except Exception:
            return 0.0
    
    def export_visualization(self, 
                           visualization_data: VisualizationData,
                           format: VisualizationFormat = VisualizationFormat.JSON,
                           filename: Optional[str] = None) -> str:
        """
        Export visualization data in specified format.
        
        Args:
            visualization_data: Visualization data to export
            format: Export format
            filename: Optional filename
            
        Returns:
            Exported data as string or filename
        """
        if format == VisualizationFormat.JSON:
            return json.dumps({
                'data': visualization_data.data,
                'metadata': visualization_data.metadata,
                'config': {
                    'chart_type': visualization_data.chart_config.chart_type.value,
                    'title': visualization_data.chart_config.title,
                    'x_axis_label': visualization_data.chart_config.x_axis_label,
                    'y_axis_label': visualization_data.chart_config.y_axis_label,
                    'width': visualization_data.chart_config.width,
                    'height': visualization_data.chart_config.height,
                    'color_scheme': visualization_data.chart_config.color_scheme,
                    'interactive': visualization_data.chart_config.interactive,
                    'show_legend': visualization_data.chart_config.show_legend,
                    'show_grid': visualization_data.chart_config.show_grid
                }
            }, indent=2)
        
        elif format == VisualizationFormat.HTML:
            return self._generate_html_chart(visualization_data)
        
        else:
            # For other formats, return JSON as fallback
            return self.export_visualization(visualization_data, VisualizationFormat.JSON, filename)
    
    def _generate_html_chart(self, visualization_data: VisualizationData) -> str:
        """Generate HTML chart using Plotly.js."""
        config = visualization_data.chart_config
        
        html_template = f"""
<!DOCTYPE html>
<html>
<head>
    <title>{config.title}</title>
    <script src="https://cdn.plot.ly/plotly-latest.min.js"></script>
    <style>
        body {{ font-family: Arial, sans-serif; margin: 20px; }}
        .chart-container {{ width: {config.width}px; height: {config.height}px; }}
    </style>
</head>
<body>
    <h1>{config.title}</h1>
    <div id="chart" class="chart-container"></div>
    
    <script>
        var data = {json.dumps(visualization_data.data)};
        var layout = {{
            title: '{config.title}',
            xaxis: {{ title: '{config.x_axis_label}' }},
            yaxis: {{ title: '{config.y_axis_label}' }},
            showlegend: {str(config.show_legend).lower()},
            width: {config.width},
            height: {config.height}
        }};
        
        var config = {{
            responsive: true,
            displayModeBar: {str(config.interactive).lower()}
        }};
        
        Plotly.newPlot('chart', data, layout, config);
    </script>
</body>
</html>
        """
        
        return html_template