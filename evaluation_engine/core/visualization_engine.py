"""
Visualization and Reporting Engine for AI Evaluation System.

This module provides interactive charts, performance dashboards, comparative
visualizations, and exportable reports in multiple formats.
"""

import json
import csv
import time
import base64
import io
from typing import Dict, List, Any, Optional, Union, Tuple
from dataclasses import dataclass, field
from enum import Enum
from datetime import datetime, timedelta
import statistics
import math

# Optional dependencies for visualization
try:
    import matplotlib.pyplot as plt
    import matplotlib.dates as mdates
    from matplotlib.figure import Figure
    import seaborn as sns
    MATPLOTLIB_AVAILABLE = True
except ImportError:
    MATPLOTLIB_AVAILABLE = False

try:
    import plotly.graph_objects as go
    import plotly.express as px
    from plotly.subplots import make_subplots
    import plotly.offline as pyo
    PLOTLY_AVAILABLE = True
except ImportError:
    PLOTLY_AVAILABLE = False

from .analysis_engine import AnalysisEngine, TrendAnalysis, AnomalyDetection
from .metrics_engine import MetricResult, MetricType


class ChartType(Enum):
    """Types of charts that can be generated."""
    LINE_CHART = "line_chart"
    BAR_CHART = "bar_chart"
    SCATTER_PLOT = "scatter_plot"
    HISTOGRAM = "histogram"
    BOX_PLOT = "box_plot"
    HEATMAP = "heatmap"
    RADAR_CHART = "radar_chart"
    TREEMAP = "treemap"
    GAUGE_CHART = "gauge_chart"
    CANDLESTICK = "candlestick"


class ReportFormat(Enum):
    """Supported report formats."""
    HTML = "html"
    PDF = "pdf"
    JSON = "json"
    CSV = "csv"
    MARKDOWN = "markdown"
    EXCEL = "excel"


@dataclass
class ChartConfig:
    """Configuration for chart generation."""
    chart_type: ChartType
    title: str
    x_axis_label: str = ""
    y_axis_label: str = ""
    width: int = 800
    height: int = 600
    theme: str = "default"
    interactive: bool = True
    show_legend: bool = True
    color_scheme: Optional[List[str]] = None
    metadata: Dict[str, Any] = field(default_factory=dict)


@dataclass
class DashboardConfig:
    """Configuration for dashboard generation."""
    title: str
    layout: str = "grid"  # grid, tabs, single_page
    refresh_interval: int = 30  # seconds
    auto_refresh: bool = False
    theme: str = "light"
    charts: List[ChartConfig] = field(default_factory=list)
    filters: Dict[str, Any] = field(default_factory=dict)
    metadata: Dict[str, Any] = field(default_factory=dict)


@dataclass
class ReportConfig:
    """Configuration for report generation."""
    title: str
    format: ReportFormat
    include_charts: bool = True
    include_tables: bool = True
    include_analysis: bool = True
    include_recommendations: bool = True
    template: Optional[str] = None
    metadata: Dict[str, Any] = field(default_factory=dict)


class VisualizationEngine:
    """
    Comprehensive visualization and reporting engine.
    
    Provides interactive charts, performance dashboards, comparative
    visualizations, and exportable reports in multiple formats.
    """
    
    def __init__(self, analysis_engine: Optional[AnalysisEngine] = None):
        """Initialize the visualization engine."""
        self.analysis_engine = analysis_engine
        
        # Chart generation backends
        self.backends = {
            'matplotlib': MATPLOTLIB_AVAILABLE,
            'plotly': PLOTLY_AVAILABLE
        }
        
        # Default configurations
        self.default_colors = [
            '#1f77b4', '#ff7f0e', '#2ca02c', '#d62728', '#9467bd',
            '#8c564b', '#e377c2', '#7f7f7f', '#bcbd22', '#17becf'
        ]
        
        # Chart cache
        self.chart_cache: Dict[str, Any] = {}
        
        # Dashboard registry
        self.dashboards: Dict[str, DashboardConfig] = {}
        
        # Report templates
        self.report_templates = self._initialize_report_templates()
        
        # Initialize visualization backends
        self._initialize_backends()
    
    def _initialize_backends(self):
        """Initialize visualization backends."""
        if MATPLOTLIB_AVAILABLE:
            plt.style.use('default')
            sns.set_palette("husl")
        
        if PLOTLY_AVAILABLE:
            # Set default plotly theme
            pass
    
    def _initialize_report_templates(self) -> Dict[str, str]:
        """Initialize report templates."""
        return {
            'html_basic': '''
<!DOCTYPE html>
<html>
<head>
    <title>{title}</title>
    <style>
        body {{ font-family: Arial, sans-serif; margin: 40px; }}
        .header {{ background-color: #f8f9fa; padding: 20px; border-radius: 5px; }}
        .section {{ margin: 20px 0; }}
        .chart {{ margin: 20px 0; text-align: center; }}
        .table {{ border-collapse: collapse; width: 100%; }}
        .table th, .table td {{ border: 1px solid #ddd; padding: 8px; text-align: left; }}
        .table th {{ background-color: #f2f2f2; }}
        .metric {{ display: inline-block; margin: 10px; padding: 15px; background-color: #e9ecef; border-radius: 5px; }}
        .recommendation {{ background-color: #d4edda; padding: 15px; border-radius: 5px; margin: 10px 0; }}
    </style>
</head>
<body>
    <div class="header">
        <h1>{title}</h1>
        <p>Generated on: {timestamp}</p>
        {summary}
    </div>
    {content}
</body>
</html>
            ''',
            
            'markdown_basic': '''
# {title}

**Generated on:** {timestamp}

{summary}

{content}
            '''
        }
    
    def create_line_chart(self, 
                         data: Dict[str, List[Union[float, int]]],
                         config: ChartConfig,
                         timestamps: Optional[List[float]] = None) -> Dict[str, Any]:
        """
        Create a line chart.
        
        Args:
            data: Dictionary mapping series names to values
            config: Chart configuration
            timestamps: Optional timestamps for x-axis
            
        Returns:
            Chart data and metadata
        """
        if not data:
            return {'error': 'No data provided'}
        
        chart_data = {
            'type': 'line_chart',
            'config': config,
            'data': data,
            'timestamps': timestamps,
            'created_at': time.time()
        }
        
        # Generate chart using available backend
        if PLOTLY_AVAILABLE and config.interactive:
            chart_data['plotly'] = self._create_plotly_line_chart(data, config, timestamps)
        
        if MATPLOTLIB_AVAILABLE:
            chart_data['matplotlib'] = self._create_matplotlib_line_chart(data, config, timestamps)
        
        # Generate ASCII chart as fallback
        chart_data['ascii'] = self._create_ascii_line_chart(data, config)
        
        return chart_data
    
    def create_bar_chart(self,
                        data: Dict[str, Union[float, int]],
                        config: ChartConfig) -> Dict[str, Any]:
        """
        Create a bar chart.
        
        Args:
            data: Dictionary mapping categories to values
            config: Chart configuration
            
        Returns:
            Chart data and metadata
        """
        if not data:
            return {'error': 'No data provided'}
        
        chart_data = {
            'type': 'bar_chart',
            'config': config,
            'data': data,
            'created_at': time.time()
        }
        
        # Generate chart using available backend
        if PLOTLY_AVAILABLE and config.interactive:
            chart_data['plotly'] = self._create_plotly_bar_chart(data, config)
        
        if MATPLOTLIB_AVAILABLE:
            chart_data['matplotlib'] = self._create_matplotlib_bar_chart(data, config)
        
        # Generate ASCII chart as fallback
        chart_data['ascii'] = self._create_ascii_bar_chart(data, config)
        
        return chart_data
    
    def create_scatter_plot(self,
                           x_data: List[float],
                           y_data: List[float],
                           config: ChartConfig,
                           labels: Optional[List[str]] = None,
                           colors: Optional[List[str]] = None) -> Dict[str, Any]:
        """
        Create a scatter plot.
        
        Args:
            x_data: X-axis values
            y_data: Y-axis values
            config: Chart configuration
            labels: Optional point labels
            colors: Optional point colors
            
        Returns:
            Chart data and metadata
        """
        if len(x_data) != len(y_data):
            return {'error': 'X and Y data must have same length'}
        
        chart_data = {
            'type': 'scatter_plot',
            'config': config,
            'x_data': x_data,
            'y_data': y_data,
            'labels': labels,
            'colors': colors,
            'created_at': time.time()
        }
        
        # Generate chart using available backend
        if PLOTLY_AVAILABLE and config.interactive:
            chart_data['plotly'] = self._create_plotly_scatter_plot(x_data, y_data, config, labels, colors)
        
        if MATPLOTLIB_AVAILABLE:
            chart_data['matplotlib'] = self._create_matplotlib_scatter_plot(x_data, y_data, config, labels, colors)
        
        return chart_data
    
    def create_heatmap(self,
                      data: List[List[float]],
                      config: ChartConfig,
                      x_labels: Optional[List[str]] = None,
                      y_labels: Optional[List[str]] = None) -> Dict[str, Any]:
        """
        Create a heatmap.
        
        Args:
            data: 2D array of values
            config: Chart configuration
            x_labels: Optional x-axis labels
            y_labels: Optional y-axis labels
            
        Returns:
            Chart data and metadata
        """
        if not data or not data[0]:
            return {'error': 'No data provided'}
        
        chart_data = {
            'type': 'heatmap',
            'config': config,
            'data': data,
            'x_labels': x_labels,
            'y_labels': y_labels,
            'created_at': time.time()
        }
        
        # Generate chart using available backend
        if PLOTLY_AVAILABLE and config.interactive:
            chart_data['plotly'] = self._create_plotly_heatmap(data, config, x_labels, y_labels)
        
        if MATPLOTLIB_AVAILABLE:
            chart_data['matplotlib'] = self._create_matplotlib_heatmap(data, config, x_labels, y_labels)
        
        return chart_data
    
    def create_performance_dashboard(self,
                                   evaluation_results: List[Dict[str, Any]],
                                   config: DashboardConfig) -> Dict[str, Any]:
        """
        Create a comprehensive performance dashboard.
        
        Args:
            evaluation_results: List of evaluation results
            config: Dashboard configuration
            
        Returns:
            Dashboard data and components
        """
        dashboard_data = {
            'type': 'performance_dashboard',
            'config': config,
            'created_at': time.time(),
            'charts': [],
            'metrics_summary': {},
            'trends': {},
            'anomalies': []
        }
        
        if not evaluation_results:
            dashboard_data['error'] = 'No evaluation results provided'
            return dashboard_data
        
        # Extract metrics from results
        all_metrics = self._extract_metrics_from_results(evaluation_results)
        
        # Create metrics summary
        dashboard_data['metrics_summary'] = self._create_metrics_summary(all_metrics)
        
        # Create trend charts
        trend_charts = self._create_trend_charts(all_metrics, evaluation_results)
        dashboard_data['charts'].extend(trend_charts)
        
        # Create comparison charts
        comparison_charts = self._create_comparison_charts(all_metrics)
        dashboard_data['charts'].extend(comparison_charts)
        
        # Create distribution charts
        distribution_charts = self._create_distribution_charts(all_metrics)
        dashboard_data['charts'].extend(distribution_charts)
        
        # Add anomaly detection if analysis engine is available
        if self.analysis_engine:
            anomalies = self.analysis_engine.detect_anomalies()
            dashboard_data['anomalies'] = [
                {
                    'type': a.anomaly_type.value,
                    'severity': a.severity,
                    'confidence': a.confidence,
                    'metrics': a.affected_metrics,
                    'description': a.description,
                    'timestamp': a.timestamp
                }
                for a in anomalies[-10:]  # Last 10 anomalies
            ]
        
        return dashboard_data
    
    def create_model_comparison_visualization(self,
                                            model_results: Dict[str, Dict[str, Any]],
                                            metrics_to_compare: Optional[List[str]] = None) -> Dict[str, Any]:
        """
        Create visualization for model comparison.
        
        Args:
            model_results: Dictionary mapping model names to results
            metrics_to_compare: Optional list of metrics to compare
            
        Returns:
            Comparison visualization data
        """
        if len(model_results) < 2:
            return {'error': 'Need at least 2 models for comparison'}
        
        comparison_data = {
            'type': 'model_comparison',
            'created_at': time.time(),
            'charts': [],
            'rankings': {},
            'statistical_tests': {}
        }
        
        # Extract metrics
        all_metrics = set()
        for model_name, results in model_results.items():
            metrics = results.get('metrics', {})
            all_metrics.update(metrics.keys())
        
        if metrics_to_compare:
            all_metrics = set(metrics_to_compare) & all_metrics
        
        # Create ranking bar chart
        ranking_data = {}
        for metric_name in all_metrics:
            model_scores = {}
            for model_name, results in model_results.items():
                metrics = results.get('metrics', {})
                if metric_name in metrics:
                    metric_result = metrics[metric_name]
                    value = metric_result.value if hasattr(metric_result, 'value') else metric_result
                    model_scores[model_name] = value
            
            if model_scores:
                ranking_data[metric_name] = model_scores
        
        # Create bar chart for each metric
        for metric_name, scores in ranking_data.items():
            chart_config = ChartConfig(
                chart_type=ChartType.BAR_CHART,
                title=f"Model Comparison - {metric_name}",
                x_axis_label="Models",
                y_axis_label=metric_name,
                height=400
            )
            
            chart = self.create_bar_chart(scores, chart_config)
            comparison_data['charts'].append(chart)
        
        # Create radar chart for overall comparison
        if len(all_metrics) >= 3:
            radar_chart = self._create_model_radar_chart(model_results, list(all_metrics))
            comparison_data['charts'].append(radar_chart)
        
        # Add statistical analysis if analysis engine is available
        if self.analysis_engine:
            performance_comparison = self.analysis_engine.compare_model_performance(model_results)
            comparison_data['rankings'] = performance_comparison.model_rankings
            comparison_data['statistical_tests'] = {
                name: {
                    'p_value': test.p_value,
                    'is_significant': test.is_significant,
                    'effect_size': test.effect_size
                }
                for name, test in performance_comparison.statistical_tests.items()
            }
        
        return comparison_data
    
    def generate_report(self,
                       evaluation_results: List[Dict[str, Any]],
                       config: ReportConfig,
                       analysis_data: Optional[Dict[str, Any]] = None) -> Dict[str, Any]:
        """
        Generate comprehensive evaluation report.
        
        Args:
            evaluation_results: List of evaluation results
            config: Report configuration
            analysis_data: Optional pre-computed analysis data
            
        Returns:
            Generated report data
        """
        report_data = {
            'type': 'evaluation_report',
            'format': config.format.value,
            'config': config,
            'created_at': time.time(),
            'content': {},
            'charts': [],
            'tables': [],
            'analysis': {},
            'recommendations': []
        }
        
        # Generate analysis if not provided
        if analysis_data is None and self.analysis_engine:
            analysis_data = self.analysis_engine.generate_comprehensive_analysis(evaluation_results)
        
        # Create report content based on format
        if config.format == ReportFormat.HTML:
            report_data['content'] = self._generate_html_report(
                evaluation_results, config, analysis_data
            )
        elif config.format == ReportFormat.MARKDOWN:
            report_data['content'] = self._generate_markdown_report(
                evaluation_results, config, analysis_data
            )
        elif config.format == ReportFormat.JSON:
            report_data['content'] = self._generate_json_report(
                evaluation_results, config, analysis_data
            )
        elif config.format == ReportFormat.CSV:
            report_data['content'] = self._generate_csv_report(
                evaluation_results, config, analysis_data
            )
        
        # Add charts if requested
        if config.include_charts:
            report_data['charts'] = self._generate_report_charts(evaluation_results, analysis_data)
        
        # Add tables if requested
        if config.include_tables:
            report_data['tables'] = self._generate_report_tables(evaluation_results, analysis_data)
        
        # Add analysis if requested
        if config.include_analysis and analysis_data:
            report_data['analysis'] = analysis_data
        
        # Add recommendations if requested
        if config.include_recommendations and analysis_data:
            report_data['recommendations'] = analysis_data.get('recommendations', [])
        
        return report_data
    
    def create_leaderboard(self,
                          evaluation_results: List[Dict[str, Any]],
                          ranking_metric: str = 'overall_score',
                          top_n: int = 10) -> Dict[str, Any]:
        """
        Create a leaderboard visualization.
        
        Args:
            evaluation_results: List of evaluation results
            ranking_metric: Metric to use for ranking
            top_n: Number of top results to show
            
        Returns:
            Leaderboard data and visualization
        """
        leaderboard_data = {
            'type': 'leaderboard',
            'ranking_metric': ranking_metric,
            'top_n': top_n,
            'created_at': time.time(),
            'rankings': [],
            'chart': None
        }
        
        # Extract and rank results
        ranked_results = []
        for result in evaluation_results:
            metrics = result.get('metrics', {})
            if ranking_metric in metrics:
                metric_result = metrics[ranking_metric]
                score = metric_result.value if hasattr(metric_result, 'value') else metric_result
                
                ranked_results.append({
                    'model_name': result.get('model_name', 'Unknown'),
                    'evaluation_id': result.get('evaluation_id', ''),
                    'score': score,
                    'timestamp': result.get('timestamp', time.time())
                })
        
        # Sort by score (descending)
        ranked_results.sort(key=lambda x: x['score'], reverse=True)
        
        # Take top N
        top_results = ranked_results[:top_n]
        leaderboard_data['rankings'] = [
            {
                'rank': i + 1,
                'model_name': result['model_name'],
                'score': result['score'],
                'evaluation_id': result['evaluation_id']
            }
            for i, result in enumerate(top_results)
        ]
        
        # Create leaderboard chart
        if top_results:
            chart_data = {name: result['score'] for name, result in 
                         [(r['model_name'], r) for r in top_results]}
            
            chart_config = ChartConfig(
                chart_type=ChartType.BAR_CHART,
                title=f"Leaderboard - {ranking_metric}",
                x_axis_label="Models",
                y_axis_label=ranking_metric,
                height=500
            )
            
            leaderboard_data['chart'] = self.create_bar_chart(chart_data, chart_config)
        
        return leaderboard_data
    
    def export_chart(self,
                    chart_data: Dict[str, Any],
                    format: str = 'png',
                    filename: Optional[str] = None) -> Dict[str, Any]:
        """
        Export chart to file.
        
        Args:
            chart_data: Chart data from create_* methods
            format: Export format (png, svg, html, json)
            filename: Optional filename
            
        Returns:
            Export result with file path or data
        """
        export_result = {
            'format': format,
            'timestamp': time.time(),
            'success': False
        }
        
        try:
            if format.lower() in ['png', 'svg', 'pdf'] and MATPLOTLIB_AVAILABLE:
                # Export matplotlib chart
                if 'matplotlib' in chart_data:
                    fig = chart_data['matplotlib']
                    if filename:
                        fig.savefig(filename, format=format, dpi=300, bbox_inches='tight')
                        export_result['filename'] = filename
                    else:
                        # Return as base64 encoded data
                        buffer = io.BytesIO()
                        fig.savefig(buffer, format=format, dpi=300, bbox_inches='tight')
                        buffer.seek(0)
                        export_result['data'] = base64.b64encode(buffer.getvalue()).decode()
                    
                    export_result['success'] = True
            
            elif format.lower() == 'html' and PLOTLY_AVAILABLE:
                # Export plotly chart
                if 'plotly' in chart_data:
                    fig = chart_data['plotly']
                    if filename:
                        fig.write_html(filename)
                        export_result['filename'] = filename
                    else:
                        export_result['data'] = fig.to_html()
                    
                    export_result['success'] = True
            
            elif format.lower() == 'json':
                # Export as JSON
                export_data = {
                    'chart_type': chart_data.get('type'),
                    'config': chart_data.get('config').__dict__ if hasattr(chart_data.get('config'), '__dict__') else chart_data.get('config'),
                    'data': chart_data.get('data'),
                    'created_at': chart_data.get('created_at')
                }
                
                if filename:
                    with open(filename, 'w') as f:
                        json.dump(export_data, f, indent=2, default=str)
                    export_result['filename'] = filename
                else:
                    export_result['data'] = json.dumps(export_data, indent=2, default=str)
                
                export_result['success'] = True
        
        except Exception as e:
            export_result['error'] = str(e)
        
        return export_result
    
    # Backend-specific chart creation methods
    
    def _create_plotly_line_chart(self, data, config, timestamps):
        """Create line chart using Plotly."""
        if not PLOTLY_AVAILABLE:
            return None
        
        fig = go.Figure()
        
        colors = config.color_scheme or self.default_colors
        
        for i, (series_name, values) in enumerate(data.items()):
            x_data = timestamps if timestamps else list(range(len(values)))
            
            fig.add_trace(go.Scatter(
                x=x_data,
                y=values,
                mode='lines+markers',
                name=series_name,
                line=dict(color=colors[i % len(colors)])
            ))
        
        fig.update_layout(
            title=config.title,
            xaxis_title=config.x_axis_label,
            yaxis_title=config.y_axis_label,
            width=config.width,
            height=config.height,
            showlegend=config.show_legend
        )
        
        return fig
    
    def _create_matplotlib_line_chart(self, data, config, timestamps):
        """Create line chart using Matplotlib."""
        if not MATPLOTLIB_AVAILABLE:
            return None
        
        fig, ax = plt.subplots(figsize=(config.width/100, config.height/100))
        
        colors = config.color_scheme or self.default_colors
        
        for i, (series_name, values) in enumerate(data.items()):
            x_data = timestamps if timestamps else list(range(len(values)))
            ax.plot(x_data, values, label=series_name, color=colors[i % len(colors)], marker='o')
        
        ax.set_title(config.title)
        ax.set_xlabel(config.x_axis_label)
        ax.set_ylabel(config.y_axis_label)
        
        if config.show_legend:
            ax.legend()
        
        plt.tight_layout()
        return fig
    
    def _create_ascii_line_chart(self, data, config):
        """Create simple ASCII line chart."""
        if not data:
            return "No data to display"
        
        # Simple ASCII representation
        lines = [f"Chart: {config.title}", "=" * len(config.title)]
        
        for series_name, values in data.items():
            if values:
                min_val = min(values)
                max_val = max(values)
                range_val = max_val - min_val if max_val != min_val else 1
                
                lines.append(f"\n{series_name}:")
                
                # Create simple bar representation
                for i, val in enumerate(values[-10:]):  # Last 10 values
                    normalized = int(((val - min_val) / range_val) * 20)
                    bar = "█" * normalized + "░" * (20 - normalized)
                    lines.append(f"  {i:2d}: {bar} {val:.3f}")
        
        return "\n".join(lines)
    
    def _create_plotly_bar_chart(self, data, config):
        """Create bar chart using Plotly."""
        if not PLOTLY_AVAILABLE:
            return None
        
        fig = go.Figure(data=[
            go.Bar(
                x=list(data.keys()),
                y=list(data.values()),
                marker_color=config.color_scheme or self.default_colors[0]
            )
        ])
        
        fig.update_layout(
            title=config.title,
            xaxis_title=config.x_axis_label,
            yaxis_title=config.y_axis_label,
            width=config.width,
            height=config.height
        )
        
        return fig
    
    def _create_matplotlib_bar_chart(self, data, config):
        """Create bar chart using Matplotlib."""
        if not MATPLOTLIB_AVAILABLE:
            return None
        
        fig, ax = plt.subplots(figsize=(config.width/100, config.height/100))
        
        categories = list(data.keys())
        values = list(data.values())
        colors = config.color_scheme or [self.default_colors[0]] * len(categories)
        
        ax.bar(categories, values, color=colors)
        ax.set_title(config.title)
        ax.set_xlabel(config.x_axis_label)
        ax.set_ylabel(config.y_axis_label)
        
        plt.xticks(rotation=45)
        plt.tight_layout()
        return fig
    
    def _create_ascii_bar_chart(self, data, config):
        """Create simple ASCII bar chart."""
        if not data:
            return "No data to display"
        
        lines = [f"Chart: {config.title}", "=" * len(config.title)]
        
        max_val = max(data.values()) if data.values() else 1
        max_label_len = max(len(str(k)) for k in data.keys()) if data else 0
        
        for category, value in data.items():
            normalized = int((value / max_val) * 30)
            bar = "█" * normalized
            lines.append(f"{category:>{max_label_len}}: {bar} {value:.3f}")
        
        return "\n".join(lines)
    
    def _create_plotly_scatter_plot(self, x_data, y_data, config, labels, colors):
        """Create scatter plot using Plotly."""
        if not PLOTLY_AVAILABLE:
            return None
        
        fig = go.Figure(data=go.Scatter(
            x=x_data,
            y=y_data,
            mode='markers',
            text=labels,
            marker=dict(
                color=colors or self.default_colors[0],
                size=8
            )
        ))
        
        fig.update_layout(
            title=config.title,
            xaxis_title=config.x_axis_label,
            yaxis_title=config.y_axis_label,
            width=config.width,
            height=config.height
        )
        
        return fig
    
    def _create_matplotlib_scatter_plot(self, x_data, y_data, config, labels, colors):
        """Create scatter plot using Matplotlib."""
        if not MATPLOTLIB_AVAILABLE:
            return None
        
        fig, ax = plt.subplots(figsize=(config.width/100, config.height/100))
        
        scatter_colors = colors or [self.default_colors[0]] * len(x_data)
        ax.scatter(x_data, y_data, c=scatter_colors, alpha=0.7)
        
        if labels:
            for i, label in enumerate(labels):
                ax.annotate(label, (x_data[i], y_data[i]), xytext=(5, 5), 
                           textcoords='offset points', fontsize=8)
        
        ax.set_title(config.title)
        ax.set_xlabel(config.x_axis_label)
        ax.set_ylabel(config.y_axis_label)
        
        plt.tight_layout()
        return fig
    
    def _create_plotly_heatmap(self, data, config, x_labels, y_labels):
        """Create heatmap using Plotly."""
        if not PLOTLY_AVAILABLE:
            return None
        
        fig = go.Figure(data=go.Heatmap(
            z=data,
            x=x_labels,
            y=y_labels,
            colorscale='Viridis'
        ))
        
        fig.update_layout(
            title=config.title,
            width=config.width,
            height=config.height
        )
        
        return fig
    
    def _create_matplotlib_heatmap(self, data, config, x_labels, y_labels):
        """Create heatmap using Matplotlib."""
        if not MATPLOTLIB_AVAILABLE:
            return None
        
        fig, ax = plt.subplots(figsize=(config.width/100, config.height/100))
        
        im = ax.imshow(data, cmap='viridis', aspect='auto')
        
        if x_labels:
            ax.set_xticks(range(len(x_labels)))
            ax.set_xticklabels(x_labels)
        
        if y_labels:
            ax.set_yticks(range(len(y_labels)))
            ax.set_yticklabels(y_labels)
        
        ax.set_title(config.title)
        plt.colorbar(im)
        plt.tight_layout()
        return fig
    
    # Helper methods for dashboard and report generation
    
    def _extract_metrics_from_results(self, evaluation_results):
        """Extract metrics from evaluation results."""
        all_metrics = {}
        
        for result in evaluation_results:
            metrics = result.get('metrics', {})
            timestamp = result.get('timestamp', time.time())
            
            for metric_name, metric_result in metrics.items():
                if metric_name not in all_metrics:
                    all_metrics[metric_name] = []
                
                value = metric_result.value if hasattr(metric_result, 'value') else metric_result
                all_metrics[metric_name].append((timestamp, value))
        
        return all_metrics
    
    def _create_metrics_summary(self, all_metrics):
        """Create summary statistics for metrics."""
        summary = {}
        
        for metric_name, values in all_metrics.items():
            metric_values = [v for t, v in values]
            
            if metric_values:
                summary[metric_name] = {
                    'count': len(metric_values),
                    'mean': statistics.mean(metric_values),
                    'median': statistics.median(metric_values),
                    'std_dev': statistics.stdev(metric_values) if len(metric_values) > 1 else 0.0,
                    'min': min(metric_values),
                    'max': max(metric_values),
                    'latest': metric_values[-1]
                }
        
        return summary
    
    def _create_trend_charts(self, all_metrics, evaluation_results):
        """Create trend charts for metrics."""
        charts = []
        
        for metric_name, values in all_metrics.items():
            if len(values) >= 3:  # Need at least 3 points for trend
                timestamps = [t for t, v in values]
                metric_values = [v for t, v in values]
                
                chart_config = ChartConfig(
                    chart_type=ChartType.LINE_CHART,
                    title=f"{metric_name} Trend Over Time",
                    x_axis_label="Time",
                    y_axis_label=metric_name,
                    height=400
                )
                
                chart = self.create_line_chart(
                    {metric_name: metric_values},
                    chart_config,
                    timestamps
                )
                charts.append(chart)
        
        return charts
    
    def _create_comparison_charts(self, all_metrics):
        """Create comparison charts for metrics."""
        charts = []
        
        if len(all_metrics) >= 2:
            # Create comparison bar chart
            latest_values = {}
            for metric_name, values in all_metrics.items():
                if values:
                    latest_values[metric_name] = values[-1][1]  # Latest value
            
            if latest_values:
                chart_config = ChartConfig(
                    chart_type=ChartType.BAR_CHART,
                    title="Latest Metric Values Comparison",
                    x_axis_label="Metrics",
                    y_axis_label="Values",
                    height=400
                )
                
                chart = self.create_bar_chart(latest_values, chart_config)
                charts.append(chart)
        
        return charts
    
    def _create_distribution_charts(self, all_metrics):
        """Create distribution charts for metrics."""
        charts = []
        
        # This would create histograms/box plots for metric distributions
        # Simplified implementation for now
        
        return charts
    
    def _create_model_radar_chart(self, model_results, metrics):
        """Create radar chart for model comparison."""
        # Simplified radar chart implementation
        # In practice, would use plotly or matplotlib radar charts
        
        chart_data = {
            'type': 'radar_chart',
            'config': ChartConfig(
                chart_type=ChartType.RADAR_CHART,
                title="Model Performance Radar Chart",
                height=500
            ),
            'models': {},
            'metrics': metrics,
            'created_at': time.time()
        }
        
        for model_name, results in model_results.items():
            model_metrics = results.get('metrics', {})
            model_values = []
            
            for metric in metrics:
                if metric in model_metrics:
                    metric_result = model_metrics[metric]
                    value = metric_result.value if hasattr(metric_result, 'value') else metric_result
                    model_values.append(value)
                else:
                    model_values.append(0.0)
            
            chart_data['models'][model_name] = model_values
        
        return chart_data
    
    def _generate_html_report(self, evaluation_results, config, analysis_data):
        """Generate HTML report."""
        template = self.report_templates.get('html_basic', '')
        
        # Create summary
        summary = f"<p>Total Evaluations: {len(evaluation_results)}</p>"
        if analysis_data:
            summary += f"<p>Metrics Analyzed: {len(analysis_data.get('summary_statistics', {}))}</p>"
        
        # Create content sections
        content_sections = []
        
        if analysis_data:
            # Summary statistics section
            if 'summary_statistics' in analysis_data:
                content_sections.append("<div class='section'><h2>Summary Statistics</h2>")
                
                for metric, stats in analysis_data['summary_statistics'].items():
                    content_sections.append(f"""
                    <div class='metric'>
                        <h3>{metric}</h3>
                        <p>Mean: {stats['mean']:.3f}</p>
                        <p>Std Dev: {stats['std_dev']:.3f}</p>
                        <p>Range: {stats['min']:.3f} - {stats['max']:.3f}</p>
                    </div>
                    """)
                
                content_sections.append("</div>")
            
            # Recommendations section
            if 'recommendations' in analysis_data:
                content_sections.append("<div class='section'><h2>Recommendations</h2>")
                
                for rec in analysis_data['recommendations']:
                    content_sections.append(f"<div class='recommendation'>{rec}</div>")
                
                content_sections.append("</div>")
        
        content = "\n".join(content_sections)
        
        return template.format(
            title=config.title,
            timestamp=datetime.now().strftime("%Y-%m-%d %H:%M:%S"),
            summary=summary,
            content=content
        )
    
    def _generate_markdown_report(self, evaluation_results, config, analysis_data):
        """Generate Markdown report."""
        template = self.report_templates.get('markdown_basic', '')
        
        # Create summary
        summary = f"**Total Evaluations:** {len(evaluation_results)}\n"
        if analysis_data:
            summary += f"**Metrics Analyzed:** {len(analysis_data.get('summary_statistics', {}))}\n"
        
        # Create content sections
        content_sections = []
        
        if analysis_data:
            # Summary statistics section
            if 'summary_statistics' in analysis_data:
                content_sections.append("## Summary Statistics\n")
                
                for metric, stats in analysis_data['summary_statistics'].items():
                    content_sections.append(f"### {metric}\n")
                    content_sections.append(f"- **Mean:** {stats['mean']:.3f}")
                    content_sections.append(f"- **Std Dev:** {stats['std_dev']:.3f}")
                    content_sections.append(f"- **Range:** {stats['min']:.3f} - {stats['max']:.3f}\n")
            
            # Recommendations section
            if 'recommendations' in analysis_data:
                content_sections.append("## Recommendations\n")
                
                for i, rec in enumerate(analysis_data['recommendations'], 1):
                    content_sections.append(f"{i}. {rec}")
        
        content = "\n".join(content_sections)
        
        return template.format(
            title=config.title,
            timestamp=datetime.now().strftime("%Y-%m-%d %H:%M:%S"),
            summary=summary,
            content=content
        )
    
    def _generate_json_report(self, evaluation_results, config, analysis_data):
        """Generate JSON report."""
        report = {
            'title': config.title,
            'generated_at': datetime.now().isoformat(),
            'total_evaluations': len(evaluation_results),
            'evaluation_results': evaluation_results,
            'analysis': analysis_data or {},
            'metadata': config.metadata
        }
        
        return json.dumps(report, indent=2, default=str)
    
    def _generate_csv_report(self, evaluation_results, config, analysis_data):
        """Generate CSV report."""
        if not evaluation_results:
            return "No data to export"
        
        # Extract all metrics
        all_metrics = set()
        for result in evaluation_results:
            metrics = result.get('metrics', {})
            all_metrics.update(metrics.keys())
        
        # Create CSV content
        output = io.StringIO()
        writer = csv.writer(output)
        
        # Header
        header = ['evaluation_id', 'model_name', 'timestamp'] + sorted(all_metrics)
        writer.writerow(header)
        
        # Data rows
        for result in evaluation_results:
            row = [
                result.get('evaluation_id', ''),
                result.get('model_name', ''),
                result.get('timestamp', '')
            ]
            
            metrics = result.get('metrics', {})
            for metric in sorted(all_metrics):
                if metric in metrics:
                    metric_result = metrics[metric]
                    value = metric_result.value if hasattr(metric_result, 'value') else metric_result
                    row.append(value)
                else:
                    row.append('')
            
            writer.writerow(row)
        
        return output.getvalue()
    
    def _generate_report_charts(self, evaluation_results, analysis_data):
        """Generate charts for report."""
        charts = []
        
        # Extract metrics for charting
        all_metrics = self._extract_metrics_from_results(evaluation_results)
        
        # Create trend charts
        trend_charts = self._create_trend_charts(all_metrics, evaluation_results)
        charts.extend(trend_charts)
        
        return charts
    
    def _generate_report_tables(self, evaluation_results, analysis_data):
        """Generate tables for report."""
        tables = []
        
        if analysis_data and 'summary_statistics' in analysis_data:
            # Summary statistics table
            stats_table = {
                'title': 'Summary Statistics',
                'headers': ['Metric', 'Mean', 'Std Dev', 'Min', 'Max', 'Count'],
                'rows': []
            }
            
            for metric, stats in analysis_data['summary_statistics'].items():
                stats_table['rows'].append([
                    metric,
                    f"{stats['mean']:.3f}",
                    f"{stats['std_dev']:.3f}",
                    f"{stats['min']:.3f}",
                    f"{stats['max']:.3f}",
                    str(stats['count'])
                ])
            
            tables.append(stats_table)
        
        return tables