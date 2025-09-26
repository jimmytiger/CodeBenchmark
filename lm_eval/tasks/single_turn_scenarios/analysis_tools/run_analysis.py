#!/usr/bin/env python3
"""
Comprehensive analysis runner for single_turn_scenarios evaluation results.

This script demonstrates how to use all analysis tools together to generate
a complete evaluation report with model comparison, context impact analysis,
scenario performance analysis, and comprehensive reporting.
"""

import json
import argparse
from pathlib import Path
from typing import List, Dict, Any

try:
    from .compare_models import ModelComparator
    from .context_impact import ContextAnalyzer
    from .scenario_analysis import ScenarioAnalyzer
    from .generate_report import ReportGenerator
except ImportError:
    # Fallback for direct execution
    import sys
    from pathlib import Path
    sys.path.append(str(Path(__file__).parent))
    
    from compare_models import ModelComparator
    from context_impact import ContextAnalyzer
    from scenario_analysis import ScenarioAnalyzer
    from generate_report import ReportGenerator


def load_results(results_path: str) -> List[Dict[str, Any]]:
    """Load evaluation results from JSONL file."""
    results = []
    
    with open(results_path, 'r') as f:
        for line in f:
            line = line.strip()
            if line:
                try:
                    result = json.loads(line)
                    results.append(result)
                except json.JSONDecodeError as e:
                    print(f"Warning: Could not parse line: {line[:100]}... Error: {e}")
    
    return results


def run_comprehensive_analysis(results_path: str, 
                             output_dir: str,
                             models: List[str] = None,
                             metrics: List[str] = None) -> None:
    """
    Run comprehensive analysis on evaluation results.
    
    Args:
        results_path: Path to JSONL results file
        output_dir: Output directory for analysis results
        models: List of models to analyze (None for all)
        metrics: List of metrics to analyze (None for all)
    """
    print("Loading evaluation results...")
    results_data = load_results(results_path)
    
    if not results_data:
        print("No results found in the input file.")
        return
    
    print(f"Loaded {len(results_data)} evaluation results")
    
    # Create output directory
    output_path = Path(output_dir)
    output_path.mkdir(parents=True, exist_ok=True)
    
    # Initialize analyzers
    print("Initializing analysis tools...")
    model_comparator = ModelComparator(results_data)
    context_analyzer = ContextAnalyzer(results_data)
    scenario_analyzer = ScenarioAnalyzer(results_data)
    report_generator = ReportGenerator(results_data)
    
    # Determine models and metrics if not specified
    if models is None:
        models = list(set(result.get('model') for result in results_data if result.get('model')))
        print(f"Found models: {models}")
    
    if metrics is None:
        # Extract all metric names from results
        all_metrics = set()
        for result in results_data:
            metrics_dict = result.get('metrics', {})
            for metric_name in metrics_dict.keys():
                all_metrics.add(f'metric_{metric_name}')
        metrics = list(all_metrics)
        print(f"Found metrics: {[m.replace('metric_', '') for m in metrics]}")
    
    # Run model comparison analysis
    print("Running model comparison analysis...")
    model_report = model_comparator.compare_models(models, metrics)
    model_comparator.export_results(model_report, output_path / 'model_comparison')
    
    # Create model comparison visualizations
    try:
        radar_fig = model_comparator.create_radar_chart(
            models, metrics, 
            save_path=str(output_path / 'model_comparison_radar.png')
        )
        print("Generated model comparison radar chart")
    except Exception as e:
        print(f"Could not generate radar chart: {e}")
    
    # Run context impact analysis
    print("Running context impact analysis...")
    context_report = context_analyzer.analyze_context_impact(models, metrics)
    context_analyzer.export_results(context_report, output_path / 'context_analysis')
    
    # Create context impact visualizations
    try:
        heatmap_fig = context_analyzer.create_context_heatmap(
            models, metrics,
            save_path=str(output_path / 'context_impact_heatmap.png')
        )
        print("Generated context impact heatmap")
    except Exception as e:
        print(f"Could not generate context heatmap: {e}")
    
    # Create context comparison plots for each model
    for model in models:
        for metric in metrics[:3]:  # Limit to first 3 metrics to avoid too many plots
            try:
                comparison_fig = context_analyzer.create_context_comparison_plot(
                    model, metric,
                    save_path=str(output_path / f'context_comparison_{model}_{metric.replace("metric_", "")}.png')
                )
                print(f"Generated context comparison plot for {model} - {metric}")
            except Exception as e:
                print(f"Could not generate context comparison for {model}-{metric}: {e}")
    
    # Run scenario and difficulty analysis
    print("Running scenario and difficulty analysis...")
    scenario_report = scenario_analyzer.analyze_scenarios_and_difficulty(models, metrics)
    scenario_analyzer.export_results(scenario_report, output_path / 'scenario_analysis')
    
    # Create scenario analysis visualizations
    for metric in metrics[:3]:  # Limit to first 3 metrics
        try:
            scenario_fig = scenario_analyzer.create_scenario_performance_chart(
                models, metric,
                save_path=str(output_path / f'scenario_performance_{metric.replace("metric_", "")}.png')
            )
            print(f"Generated scenario performance chart for {metric}")
        except Exception as e:
            print(f"Could not generate scenario chart for {metric}: {e}")
        
        try:
            difficulty_fig = scenario_analyzer.create_difficulty_sensitivity_chart(
                models, metric,
                save_path=str(output_path / f'difficulty_sensitivity_{metric.replace("metric_", "")}.png')
            )
            print(f"Generated difficulty sensitivity chart for {metric}")
        except Exception as e:
            print(f"Could not generate difficulty chart for {metric}: {e}")
        
        try:
            language_fig = scenario_analyzer.create_language_adaptation_chart(
                models, metric,
                save_path=str(output_path / f'language_adaptation_{metric.replace("metric_", "")}.png')
            )
            print(f"Generated language adaptation chart for {metric}")
        except Exception as e:
            print(f"Could not generate language chart for {metric}: {e}")
    
    # Generate comprehensive reports
    print("Generating comprehensive reports...")
    
    # HTML report
    html_path = report_generator.generate_html_report(
        str(output_path / 'comprehensive_report.html'),
        title="Single Turn Scenarios Comprehensive Analysis Report"
    )
    print(f"Generated HTML report: {html_path}")
    
    # CSV export
    csv_path = report_generator.export_csv_results(
        str(output_path / 'evaluation_results.csv')
    )
    print(f"Exported CSV results: {csv_path}")
    
    # Dashboard
    dashboard_path = report_generator.create_summary_dashboard(
        str(output_path / 'dashboard')
    )
    print(f"Created summary dashboard: {dashboard_path}")
    
    # Generate summary statistics
    print("\n" + "="*60)
    print("ANALYSIS SUMMARY")
    print("="*60)
    
    print(f"Total evaluations analyzed: {len(results_data)}")
    print(f"Models analyzed: {len(models)}")
    print(f"Metrics analyzed: {len(metrics)}")
    
    # Print top performing models
    if model_report.performance_matrix is not None and not model_report.performance_matrix.empty:
        print("\nTop performing models by metric:")
        for metric_col in model_report.performance_matrix.columns:
            if model_report.performance_matrix[metric_col].notna().any():
                best_model = model_report.performance_matrix[metric_col].idxmax()
                best_score = model_report.performance_matrix.loc[best_model, metric_col]
                print(f"  {metric_col}: {best_model} ({best_score:.3f})")
    
    # Print context impact summary
    if hasattr(context_report, 'improvement_matrix') and not context_report.improvement_matrix.empty:
        print("\nContext impact summary:")
        improvement_cols = [col for col in context_report.improvement_matrix.columns 
                          if 'rel_improvement' in col]
        if improvement_cols:
            avg_improvements = context_report.improvement_matrix[improvement_cols].mean()
            for col in improvement_cols:
                metric_name = col.replace('_rel_improvement', '')
                print(f"  {metric_name}: {avg_improvements[col]:.1f}% average improvement")
    
    print(f"\nAll analysis results saved to: {output_path}")
    print("="*60)


def main():
    """Main entry point for the analysis runner."""
    parser = argparse.ArgumentParser(
        description='Run comprehensive analysis on single_turn_scenarios evaluation results',
        formatter_class=argparse.RawDescriptionHelpFormatter,
        epilog="""
Examples:
  # Analyze all models and metrics
  python run_analysis.py --results results.jsonl --output analysis_output/
  
  # Analyze specific models
  python run_analysis.py --results results.jsonl --output analysis_output/ \\
    --models claude-3-5-sonnet deepseek-coder
  
  # Analyze specific metrics
  python run_analysis.py --results results.jsonl --output analysis_output/ \\
    --metrics exact_match pass_at_1 codebleu
  
  # Full analysis with specific models and metrics
  python run_analysis.py --results results.jsonl --output analysis_output/ \\
    --models claude-3-5-sonnet deepseek-coder openai-gpt-4 \\
    --metrics exact_match pass_at_1 codebleu syntax_valid
        """
    )
    
    parser.add_argument(
        '--results', 
        required=True,
        help='Path to JSONL file containing evaluation results'
    )
    
    parser.add_argument(
        '--output', 
        required=True,
        help='Output directory for analysis results'
    )
    
    parser.add_argument(
        '--models', 
        nargs='+',
        help='Models to analyze (default: all models in results)'
    )
    
    parser.add_argument(
        '--metrics', 
        nargs='+',
        help='Metrics to analyze (default: all metrics in results)'
    )
    
    args = parser.parse_args()
    
    # Validate input file
    if not Path(args.results).exists():
        print(f"Error: Results file not found: {args.results}")
        return 1
    
    try:
        run_comprehensive_analysis(
            results_path=args.results,
            output_dir=args.output,
            models=args.models,
            metrics=args.metrics
        )
        return 0
    except Exception as e:
        print(f"Error during analysis: {e}")
        import traceback
        traceback.print_exc()
        return 1


if __name__ == '__main__':
    exit(main())