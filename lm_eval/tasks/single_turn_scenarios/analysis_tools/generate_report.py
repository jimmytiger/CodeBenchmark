"""
Comprehensive report generation tool for single_turn_scenarios evaluation results.

This module generates HTML, CSV, and SVG reports with radar charts, heatmaps,
trend graphs, and detailed comparison tables.
"""

import json
import pandas as pd
import numpy as np
from typing import List, Dict, Any, Optional
from pathlib import Path
from datetime import datetime
import matplotlib.pyplot as plt
import seaborn as sns
import base64
from io import BytesIO

try:
    from .compare_models import ModelComparator, ComparisonReport
    from .context_impact import ContextAnalyzer, ContextReport
except ImportError:
    # Fallback for direct execution
    import sys
    from pathlib import Path
    sys.path.append(str(Path(__file__).parent))
    
    from compare_models import ModelComparator, ComparisonReport
    from context_impact import ContextAnalyzer, ContextReport


class ReportGenerator:
    """
    Comprehensive report generation tool.
    
    Generates HTML, CSV, and SVG reports with visualizations and detailed
    comparison tables for evaluation results.
    """
    
    def __init__(self, results_data: List[Dict[str, Any]]):
        """
        Initialize the report generator.
        
        Args:
            results_data: List of evaluation result dictionaries
        """
        self.results_data = results_data
        self.df = self._load_results_to_dataframe()
        self.model_comparator = ModelComparator(results_data)
        self.context_analyzer = ContextAnalyzer(results_data)
        
    def _load_results_to_dataframe(self) -> pd.DataFrame:
        """Convert results data to pandas DataFrame for analysis."""
        rows = []
        
        for result in self.results_data:
            row = {
                'id': result.get('id'),
                'model': result.get('model'),
                'config': result.get('config'),
                'scenario': result.get('scenario'),
                'difficulty': result.get('difficulty'),
                'language': result.get('language'),
                'context_mode': result.get('context_mode'),
                'timestamp': result.get('timestamp')
            }
            
            # Add all metrics
            metrics = result.get('metrics', {})
            for metric_name, value in metrics.items():
                row[f'metric_{metric_name}'] = value
                
            # Add runtime information
            runtime = result.get('runtime', {})
            row['runtime_time_s'] = runtime.get('time_s')
            row['runtime_peak_memory_mb'] = runtime.get('peak_memory_mb')
            
            rows.append(row)
            
        return pd.DataFrame(rows)
    
    def generate_html_report(self, 
                           output_path: str,
                           title: str = "Single Turn Scenarios Evaluation Report") -> str:
        """
        Generate comprehensive HTML report.
        
        Args:
            output_path: Path to save the HTML report
            title: Report title
            
        Returns:
            Path to generated HTML file
        """
        # Perform analyses
        models = self.df['model'].unique().tolist()
        metrics = [col for col in self.df.columns if col.startswith('metric_')]
        
        model_report = self.model_comparator.compare_models(models, metrics)
        context_report = self.context_analyzer.analyze_context_impact(models, metrics)
        
        # Generate visualizations as base64 encoded images
        visualizations = self._generate_visualizations(models, metrics)
        
        # Generate HTML content
        html_content = self._create_html_content(
            title, model_report, context_report, visualizations
        )
        
        # Save HTML file
        output_file = Path(output_path)
        output_file.parent.mkdir(parents=True, exist_ok=True)
        
        with open(output_file, 'w', encoding='utf-8') as f:
            f.write(html_content)
        
        return str(output_file)
    
    def _generate_visualizations(self, 
                               models: List[str], 
                               metrics: List[str]) -> Dict[str, str]:
        """Generate visualizations as base64 encoded strings."""
        visualizations = {}
        
        # Model comparison radar chart
        try:
            fig = self.model_comparator.create_radar_chart(models, metrics)
            visualizations['radar_chart'] = self._fig_to_base64(fig)
            plt.close(fig)
        except Exception as e:
            print(f"Could not generate radar chart: {e}")
        
        # Context impact heatmap
        try:
            fig = self.context_analyzer.create_context_heatmap(models, metrics)
            if fig:
                visualizations['context_heatmap'] = self._fig_to_base64(fig)
                plt.close(fig)
        except Exception as e:
            print(f"Could not generate context heatmap: {e}")
        
        # Performance trend graphs
        try:
            fig = self._create_performance_trends(models, metrics)
            visualizations['performance_trends'] = self._fig_to_base64(fig)
            plt.close(fig)
        except Exception as e:
            print(f"Could not generate performance trends: {e}")
        
        # Metric distribution plots
        try:
            fig = self._create_metric_distributions(metrics)
            visualizations['metric_distributions'] = self._fig_to_base64(fig)
            plt.close(fig)
        except Exception as e:
            print(f"Could not generate metric distributions: {e}")
        
        return visualizations
    
    def _fig_to_base64(self, fig: plt.Figure) -> str:
        """Convert matplotlib figure to base64 encoded string."""
        buffer = BytesIO()
        fig.savefig(buffer, format='png', dpi=150, bbox_inches='tight')
        buffer.seek(0)
        image_base64 = base64.b64encode(buffer.getvalue()).decode()
        buffer.close()
        return image_base64
    
    def _create_performance_trends(self, 
                                 models: List[str], 
                                 metrics: List[str]) -> plt.Figure:
        """Create performance trend graphs across scenarios and difficulties."""
        fig, axes = plt.subplots(2, 2, figsize=(16, 12))
        fig.suptitle('Performance Trends Analysis', fontsize=16, fontweight='bold')
        
        # Trend by scenario
        ax1 = axes[0, 0]
        scenario_data = self.df.groupby(['model', 'scenario']).agg({
            'metric_exact_match': 'mean',
            'metric_pass_at_1': 'mean'
        }).reset_index()
        
        for model in models:
            model_data = scenario_data[scenario_data['model'] == model]
            if len(model_data) > 0:
                ax1.plot(model_data['scenario'], model_data['metric_exact_match'], 
                        marker='o', label=f'{model} (Exact Match)')
        
        ax1.set_title('Performance by Scenario')
        ax1.set_xlabel('Scenario')
        ax1.set_ylabel('Score')
        ax1.legend()
        ax1.tick_params(axis='x', rotation=45)
        
        # Trend by difficulty
        ax2 = axes[0, 1]
        difficulty_data = self.df.groupby(['model', 'difficulty']).agg({
            'metric_exact_match': 'mean',
            'metric_pass_at_1': 'mean'
        }).reset_index()
        
        for model in models:
            model_data = difficulty_data[difficulty_data['model'] == model]
            if len(model_data) > 0:
                ax2.plot(model_data['difficulty'], model_data['metric_exact_match'], 
                        marker='s', label=f'{model} (Exact Match)')
        
        ax2.set_title('Performance by Difficulty')
        ax2.set_xlabel('Difficulty')
        ax2.set_ylabel('Score')
        ax2.legend()
        
        # Trend by language
        ax3 = axes[1, 0]
        language_data = self.df.groupby(['model', 'language']).agg({
            'metric_exact_match': 'mean',
            'metric_pass_at_1': 'mean'
        }).reset_index()
        
        for model in models:
            model_data = language_data[language_data['model'] == model]
            if len(model_data) > 0:
                ax3.plot(model_data['language'], model_data['metric_exact_match'], 
                        marker='^', label=f'{model} (Exact Match)')
        
        ax3.set_title('Performance by Language')
        ax3.set_xlabel('Programming Language')
        ax3.set_ylabel('Score')
        ax3.legend()
        ax3.tick_params(axis='x', rotation=45)
        
        # Runtime performance
        ax4 = axes[1, 1]
        runtime_data = self.df.groupby('model').agg({
            'runtime_time_s': 'mean',
            'runtime_peak_memory_mb': 'mean'
        }).reset_index()
        
        ax4_twin = ax4.twinx()
        
        x_pos = np.arange(len(runtime_data))
        ax4.bar(x_pos - 0.2, runtime_data['runtime_time_s'], 0.4, 
               label='Avg Runtime (s)', alpha=0.7)
        ax4_twin.bar(x_pos + 0.2, runtime_data['runtime_peak_memory_mb'], 0.4, 
                    label='Avg Memory (MB)', alpha=0.7, color='orange')
        
        ax4.set_title('Runtime Performance')
        ax4.set_xlabel('Model')
        ax4.set_ylabel('Runtime (seconds)')
        ax4_twin.set_ylabel('Memory (MB)')
        ax4.set_xticks(x_pos)
        ax4.set_xticklabels(runtime_data['model'], rotation=45)
        ax4.legend(loc='upper left')
        ax4_twin.legend(loc='upper right')
        
        plt.tight_layout()
        return fig
    
    def _create_metric_distributions(self, metrics: List[str]) -> plt.Figure:
        """Create distribution plots for key metrics."""
        key_metrics = ['metric_exact_match', 'metric_pass_at_1', 'metric_codebleu', 'metric_syntax_valid']
        available_metrics = [m for m in key_metrics if m in self.df.columns]
        
        if not available_metrics:
            # Create empty plot if no metrics available
            fig, ax = plt.subplots(figsize=(10, 6))
            ax.text(0.5, 0.5, 'No metric data available', 
                   ha='center', va='center', transform=ax.transAxes)
            return fig
        
        n_metrics = len(available_metrics)
        cols = 2
        rows = (n_metrics + 1) // 2
        
        fig, axes = plt.subplots(rows, cols, figsize=(12, 4 * rows))
        fig.suptitle('Metric Distributions', fontsize=16, fontweight='bold')
        
        if rows == 1:
            axes = [axes] if n_metrics == 1 else axes
        else:
            axes = axes.flatten()
        
        for i, metric in enumerate(available_metrics):
            ax = axes[i]
            
            # Create histogram for each model
            models = self.df['model'].unique()
            for model in models:
                model_data = self.df[self.df['model'] == model][metric].dropna()
                if len(model_data) > 0:
                    ax.hist(model_data, alpha=0.6, label=model, bins=20)
            
            ax.set_title(f'Distribution: {metric.replace("metric_", "")}')
            ax.set_xlabel('Score')
            ax.set_ylabel('Frequency')
            ax.legend()
            ax.grid(True, alpha=0.3)
        
        # Hide unused subplots
        for i in range(n_metrics, len(axes)):
            axes[i].set_visible(False)
        
        plt.tight_layout()
        return fig
    
    def _create_html_content(self, 
                           title: str,
                           model_report: ComparisonReport,
                           context_report: ContextReport,
                           visualizations: Dict[str, str]) -> str:
        """Create HTML content for the report."""
        
        # Generate summary statistics
        summary_stats = self._generate_summary_statistics()
        
        html_template = f"""
<!DOCTYPE html>
<html lang="en">
<head>
    <meta charset="UTF-8">
    <meta name="viewport" content="width=device-width, initial-scale=1.0">
    <title>{title}</title>
    <style>
        body {{
            font-family: 'Segoe UI', Tahoma, Geneva, Verdana, sans-serif;
            margin: 0;
            padding: 20px;
            background-color: #f5f5f5;
        }}
        .container {{
            max-width: 1200px;
            margin: 0 auto;
            background-color: white;
            padding: 30px;
            border-radius: 10px;
            box-shadow: 0 0 20px rgba(0,0,0,0.1);
        }}
        h1 {{
            color: #2c3e50;
            text-align: center;
            border-bottom: 3px solid #3498db;
            padding-bottom: 10px;
        }}
        h2 {{
            color: #34495e;
            border-left: 4px solid #3498db;
            padding-left: 15px;
            margin-top: 30px;
        }}
        h3 {{
            color: #7f8c8d;
        }}
        .summary-grid {{
            display: grid;
            grid-template-columns: repeat(auto-fit, minmax(200px, 1fr));
            gap: 20px;
            margin: 20px 0;
        }}
        .summary-card {{
            background: linear-gradient(135deg, #667eea 0%, #764ba2 100%);
            color: white;
            padding: 20px;
            border-radius: 10px;
            text-align: center;
        }}
        .summary-card h3 {{
            margin: 0;
            color: white;
        }}
        .summary-card .value {{
            font-size: 2em;
            font-weight: bold;
            margin: 10px 0;
        }}
        table {{
            width: 100%;
            border-collapse: collapse;
            margin: 20px 0;
        }}
        th, td {{
            border: 1px solid #ddd;
            padding: 12px;
            text-align: left;
        }}
        th {{
            background-color: #3498db;
            color: white;
        }}
        tr:nth-child(even) {{
            background-color: #f2f2f2;
        }}
        .visualization {{
            text-align: center;
            margin: 30px 0;
        }}
        .visualization img {{
            max-width: 100%;
            height: auto;
            border: 1px solid #ddd;
            border-radius: 5px;
        }}
        .metric-highlight {{
            background-color: #e8f5e8;
            font-weight: bold;
        }}
        .timestamp {{
            text-align: center;
            color: #7f8c8d;
            font-style: italic;
            margin-top: 30px;
        }}
    </style>
</head>
<body>
    <div class="container">
        <h1>{title}</h1>
        
        <div class="timestamp">
            Generated on: {datetime.now().strftime('%Y-%m-%d %H:%M:%S')}
        </div>
        
        <h2>📊 Executive Summary</h2>
        <div class="summary-grid">
            {self._generate_summary_cards(summary_stats)}
        </div>
        
        <h2>📈 Performance Visualizations</h2>
        {self._generate_visualization_section(visualizations)}
        
        <h2>🏆 Model Performance Comparison</h2>
        {self._generate_model_comparison_section(model_report)}
        
        <h2>🎯 Context Impact Analysis</h2>
        {self._generate_context_analysis_section(context_report)}
        
        <h2>📋 Detailed Results</h2>
        {self._generate_detailed_results_section()}
        
        <h2>📝 Methodology</h2>
        {self._generate_methodology_section()}
        
    </div>
</body>
</html>
"""
        return html_template
    
    def _generate_summary_statistics(self) -> Dict[str, Any]:
        """Generate summary statistics for the report."""
        return {
            'total_evaluations': len(self.df),
            'unique_models': self.df['model'].nunique(),
            'scenarios_tested': self.df['scenario'].nunique(),
            'languages_tested': self.df['language'].nunique(),
            'avg_exact_match': self.df['metric_exact_match'].mean() if 'metric_exact_match' in self.df.columns else 0,
            'avg_pass_at_1': self.df['metric_pass_at_1'].mean() if 'metric_pass_at_1' in self.df.columns else 0,
            'avg_runtime': self.df['runtime_time_s'].mean() if 'runtime_time_s' in self.df.columns else 0
        }
    
    def _generate_summary_cards(self, stats: Dict[str, Any]) -> str:
        """Generate HTML for summary cards."""
        cards = []
        
        card_configs = [
            ('Total Evaluations', stats['total_evaluations'], ''),
            ('Models Tested', stats['unique_models'], ''),
            ('Scenarios', stats['scenarios_tested'], ''),
            ('Languages', stats['languages_tested'], ''),
            ('Avg Exact Match', f"{stats['avg_exact_match']:.2%}", ''),
            ('Avg Pass@1', f"{stats['avg_pass_at_1']:.2%}", ''),
            ('Avg Runtime', f"{stats['avg_runtime']:.2f}s", '')
        ]
        
        for title, value, unit in card_configs:
            cards.append(f"""
            <div class="summary-card">
                <h3>{title}</h3>
                <div class="value">{value}{unit}</div>
            </div>
            """)
        
        return ''.join(cards)
    
    def _generate_visualization_section(self, visualizations: Dict[str, str]) -> str:
        """Generate HTML for visualization section."""
        sections = []
        
        viz_configs = [
            ('radar_chart', 'Model Performance Radar Chart', 'Normalized performance comparison across all metrics'),
            ('context_heatmap', 'Context Impact Heatmap', 'Relative improvement from baseline context mode'),
            ('performance_trends', 'Performance Trends', 'Performance analysis across scenarios, difficulties, and languages'),
            ('metric_distributions', 'Metric Distributions', 'Distribution of metric scores across models')
        ]
        
        for viz_key, title, description in viz_configs:
            if viz_key in visualizations:
                sections.append(f"""
                <div class="visualization">
                    <h3>{title}</h3>
                    <p>{description}</p>
                    <img src="data:image/png;base64,{visualizations[viz_key]}" alt="{title}">
                </div>
                """)
        
        return ''.join(sections) if sections else "<p>No visualizations available.</p>"
    
    def _generate_model_comparison_section(self, report: ComparisonReport) -> str:
        """Generate HTML for model comparison section."""
        # Performance matrix table
        matrix_html = report.performance_matrix.to_html(
            classes='performance-matrix',
            table_id='performance-table',
            float_format=lambda x: f'{x:.3f}' if pd.notna(x) else 'N/A'
        )
        
        # Rankings summary
        rankings_html = self._format_rankings(report.rankings)
        
        return f"""
        <h3>Performance Matrix</h3>
        {matrix_html}
        
        <h3>Model Rankings by Metric</h3>
        {rankings_html}
        """
    
    def _generate_context_analysis_section(self, report: ContextReport) -> str:
        """Generate HTML for context analysis section."""
        # Context comparison table
        comparison_html = report.context_comparison.to_html(
            classes='context-comparison',
            index=False,
            float_format=lambda x: f'{x:.3f}' if pd.notna(x) else 'N/A'
        )
        
        # Improvement matrix
        improvement_html = report.improvement_matrix.to_html(
            classes='improvement-matrix',
            index=False,
            float_format=lambda x: f'{x:.2f}%' if pd.notna(x) and 'rel_improvement' in str(x) else f'{x:.3f}' if pd.notna(x) else 'N/A'
        )
        
        return f"""
        <h3>Context Mode Comparison</h3>
        {comparison_html}
        
        <h3>Context Improvement Matrix</h3>
        {improvement_html}
        """
    
    def _generate_detailed_results_section(self) -> str:
        """Generate HTML for detailed results section."""
        # Sample of detailed results
        sample_size = min(50, len(self.df))
        sample_df = self.df.head(sample_size)
        
        # Select key columns for display
        display_cols = ['id', 'model', 'scenario', 'difficulty', 'language', 'context_mode']
        metric_cols = [col for col in sample_df.columns if col.startswith('metric_')][:5]  # First 5 metrics
        display_cols.extend(metric_cols)
        
        results_html = sample_df[display_cols].to_html(
            classes='detailed-results',
            index=False,
            float_format=lambda x: f'{x:.3f}' if pd.notna(x) else 'N/A'
        )
        
        return f"""
        <h3>Sample Results (First {sample_size} entries)</h3>
        {results_html}
        <p><em>Note: Showing first {sample_size} results. Full results available in CSV export.</em></p>
        """
    
    def _generate_methodology_section(self) -> str:
        """Generate HTML for methodology section."""
        return """
        <h3>Evaluation Methodology</h3>
        <p>This report presents results from the single_turn_scenarios evaluation framework, which provides:</p>
        <ul>
            <li><strong>Multi-language Support:</strong> Evaluation across Python, JavaScript, Java, C++, Go, and Rust</li>
            <li><strong>Scenario Classification:</strong> Tasks categorized by type (basic, advanced, comprehensive)</li>
            <li><strong>Difficulty Levels:</strong> Simple, Intermediate, and Complex problem classifications</li>
            <li><strong>Context Modes:</strong> No context, minimal context, full context, and domain context</li>
            <li><strong>Comprehensive Metrics:</strong> Text similarity, code quality, functional correctness, and consistency</li>
        </ul>
        
        <h3>Statistical Analysis</h3>
        <p>Statistical significance testing includes:</p>
        <ul>
            <li>Pairwise t-tests between models and context modes</li>
            <li>ANOVA for multi-group comparisons</li>
            <li>Effect size calculations (Cohen's d)</li>
            <li>95% confidence intervals for performance estimates</li>
        </ul>
        """
    
    def _format_rankings(self, rankings: Dict[str, List[str]]) -> str:
        """Format rankings as HTML table."""
        if not rankings:
            return "<p>No ranking data available.</p>"
        
        html = "<table><thead><tr><th>Metric</th><th>Ranking (Best to Worst)</th></tr></thead><tbody>"
        
        for metric, ranking in rankings.items():
            ranking_str = " → ".join(ranking)
            html += f"<tr><td>{metric}</td><td>{ranking_str}</td></tr>"
        
        html += "</tbody></table>"
        return html
    
    def export_csv_results(self, output_path: str) -> str:
        """Export results to CSV format."""
        output_file = Path(output_path)
        output_file.parent.mkdir(parents=True, exist_ok=True)
        
        self.df.to_csv(output_file, index=False)
        return str(output_file)
    
    def create_summary_dashboard(self, output_dir: str) -> str:
        """Create a summary dashboard with key visualizations."""
        output_path = Path(output_dir)
        output_path.mkdir(parents=True, exist_ok=True)
        
        models = self.df['model'].unique().tolist()
        metrics = [col for col in self.df.columns if col.startswith('metric_')]
        
        # Generate key visualizations
        visualizations = {}
        
        # Model comparison radar chart
        try:
            fig = self.model_comparator.create_radar_chart(models, metrics)
            fig.savefig(output_path / 'model_comparison_radar.svg', format='svg', bbox_inches='tight')
            plt.close(fig)
        except Exception as e:
            print(f"Could not generate radar chart: {e}")
        
        # Context impact heatmap
        try:
            fig = self.context_analyzer.create_context_heatmap(models, metrics)
            if fig:
                fig.savefig(output_path / 'context_impact_heatmap.svg', format='svg', bbox_inches='tight')
                plt.close(fig)
        except Exception as e:
            print(f"Could not generate context heatmap: {e}")
        
        # Performance trends
        try:
            fig = self._create_performance_trends(models, metrics)
            fig.savefig(output_path / 'performance_trends.svg', format='svg', bbox_inches='tight')
            plt.close(fig)
        except Exception as e:
            print(f"Could not generate performance trends: {e}")
        
        return str(output_path)


def main():
    """Example usage of ReportGenerator."""
    import argparse
    
    parser = argparse.ArgumentParser(description='Generate comprehensive evaluation report')
    parser.add_argument('--results', required=True, 
                       help='Path to results JSON file')
    parser.add_argument('--output', required=True,
                       help='Output directory for reports')
    parser.add_argument('--title', default='Single Turn Scenarios Evaluation Report',
                       help='Report title')
    parser.add_argument('--format', choices=['html', 'csv', 'dashboard', 'all'], 
                       default='all', help='Output format')
    
    args = parser.parse_args()
    
    # Load results
    with open(args.results, 'r') as f:
        results_data = [json.loads(line) for line in f]
    
    # Create report generator
    generator = ReportGenerator(results_data)
    
    output_dir = Path(args.output)
    output_dir.mkdir(parents=True, exist_ok=True)
    
    # Generate reports based on format
    if args.format in ['html', 'all']:
        html_path = generator.generate_html_report(
            output_dir / 'evaluation_report.html',
            args.title
        )
        print(f"HTML report generated: {html_path}")
    
    if args.format in ['csv', 'all']:
        csv_path = generator.export_csv_results(
            output_dir / 'evaluation_results.csv'
        )
        print(f"CSV results exported: {csv_path}")
    
    if args.format in ['dashboard', 'all']:
        dashboard_path = generator.create_summary_dashboard(
            output_dir / 'dashboard'
        )
        print(f"Dashboard created: {dashboard_path}")
    
    print(f"Report generation complete. Output saved to {args.output}")


if __name__ == '__main__':
    main()