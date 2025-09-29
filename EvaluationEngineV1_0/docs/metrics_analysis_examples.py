# Metrics Analysis Examples
# Comprehensive examples for analyzing multi-turn evaluation results

import pandas as pd
import matplotlib.pyplot as plt
import seaborn as sns
import numpy as np
from typing import Dict, List, Any
import json

class MetricsAnalyzer:
    """Comprehensive metrics analysis for multi-turn evaluations."""
    
    def __init__(self, results_file: str):
        """Initialize with results file."""
        self.results = self.load_results(results_file)
        self.df = self.create_dataframe()
    
    def load_results(self, file_path: str) -> Dict[str, Any]:
        """Load evaluation results from JSON file."""
        with open(file_path, 'r') as f:
            return json.load(f)
    
    def create_dataframe(self) -> pd.DataFrame:
        """Create pandas DataFrame from results."""
        data = []
        for task_result in self.results.get('task_results', []):
            row = {
                'task_id': task_result['task_id'],
                'success': task_result['success'],
                'total_turns': task_result['total_turns'],
                'execution_time': task_result['execution_time'],
                'total_tokens': task_result['total_tokens'],
                'total_cost': task_result['total_cost'],
                'termination_reason': task_result['termination_reason']
            }
            
            # Add metrics
            metrics = task_result.get('final_metrics', {})
            for metric_name, value in metrics.items():
                row[f'metric_{metric_name}'] = value
            
            data.append(row)
        
        return pd.DataFrame(data)
    
    def analyze_success_rates(self):
        """Analyze success rates across different dimensions."""
        print("=== SUCCESS RATE ANALYSIS ===")
        
        # Overall success rate
        overall_success = self.df['success'].mean()
        print(f"Overall Success Rate: {overall_success:.2%}")
        
        # Success rate by task category
        self.df['task_category'] = self.df['task_id'].str.extract(r'([^_]+)')
        category_success = self.df.groupby('task_category')['success'].agg(['mean', 'count'])
        print("\nSuccess Rate by Category:")
        print(category_success)
        
        # Success rate by difficulty (if available)
        if 'difficulty' in self.df.columns:
            difficulty_success = self.df.groupby('difficulty')['success'].mean()
            print("\nSuccess Rate by Difficulty:")
            print(difficulty_success)
    
    def analyze_efficiency_metrics(self):
        """Analyze efficiency metrics."""
        print("\n=== EFFICIENCY ANALYSIS ===")
        
        # Turn statistics
        print(f"Average Turns: {self.df['total_turns'].mean():.1f}")
        print(f"Median Turns: {self.df['total_turns'].median():.1f}")
        print(f"Turn Range: {self.df['total_turns'].min()}-{self.df['total_turns'].max()}")
        
        # Time statistics
        print(f"\nAverage Execution Time: {self.df['execution_time'].mean():.1f}s")
        print(f"Median Execution Time: {self.df['execution_time'].median():.1f}s")
        
        # Efficiency correlation
        correlation = self.df['total_turns'].corr(self.df['execution_time'])
        print(f"\nTurns-Time Correlation: {correlation:.3f}")
    
    def analyze_cost_metrics(self):
        """Analyze cost-related metrics."""
        print("\n=== COST ANALYSIS ===")
        
        total_cost = self.df['total_cost'].sum()
        avg_cost_per_task = self.df['total_cost'].mean()
        
        print(f"Total Cost: ${total_cost:.2f}")
        print(f"Average Cost per Task: ${avg_cost_per_task:.2f}")
        
        # Cost efficiency (cost per successful task)
        successful_tasks = self.df[self.df['success'] == True]
        if len(successful_tasks) > 0:
            cost_per_success = successful_tasks['total_cost'].mean()
            print(f"Average Cost per Successful Task: ${cost_per_success:.2f}")
        
        # Token usage
        print(f"\nAverage Tokens per Task: {self.df['total_tokens'].mean():.0f}")
        print(f"Total Tokens Used: {self.df['total_tokens'].sum():,}")
    
    def create_visualizations(self):
        """Create comprehensive visualizations."""
        fig, axes = plt.subplots(2, 3, figsize=(18, 12))
        
        # Success rate by category
        category_success = self.df.groupby('task_category')['success'].mean()
        axes[0, 0].bar(category_success.index, category_success.values)
        axes[0, 0].set_title('Success Rate by Category')
        axes[0, 0].set_ylabel('Success Rate')
        
        # Turn distribution
        axes[0, 1].hist(self.df['total_turns'], bins=20, alpha=0.7)
        axes[0, 1].set_title('Distribution of Turns')
        axes[0, 1].set_xlabel('Total Turns')
        axes[0, 1].set_ylabel('Frequency')
        
        # Cost vs Success
        success_colors = ['red' if not s else 'green' for s in self.df['success']]
        axes[0, 2].scatter(self.df['total_cost'], self.df['total_turns'], c=success_colors, alpha=0.6)
        axes[0, 2].set_title('Cost vs Turns (Green=Success, Red=Failure)')
        axes[0, 2].set_xlabel('Total Cost ($)')
        axes[0, 2].set_ylabel('Total Turns')
        
        # Execution time distribution
        axes[1, 0].boxplot([self.df[self.df['success'] == True]['execution_time'],
                           self.df[self.df['success'] == False]['execution_time']],
                          labels=['Success', 'Failure'])
        axes[1, 0].set_title('Execution Time by Outcome')
        axes[1, 0].set_ylabel('Execution Time (s)')
        
        # Termination reasons
        termination_counts = self.df['termination_reason'].value_counts()
        axes[1, 1].pie(termination_counts.values, labels=termination_counts.index, autopct='%1.1f%%')
        axes[1, 1].set_title('Termination Reasons')
        
        # Success rate trend (if multiple runs)
        if 'run_id' in self.df.columns:
            run_success = self.df.groupby('run_id')['success'].mean()
            axes[1, 2].plot(run_success.index, run_success.values, marker='o')
            axes[1, 2].set_title('Success Rate Trend')
            axes[1, 2].set_xlabel('Run ID')
            axes[1, 2].set_ylabel('Success Rate')
        else:
            axes[1, 2].text(0.5, 0.5, 'No trend data\navailable', 
                           ha='center', va='center', transform=axes[1, 2].transAxes)
            axes[1, 2].set_title('Success Rate Trend')
        
        plt.tight_layout()
        plt.savefig('evaluation_analysis.png', dpi=300, bbox_inches='tight')
        plt.show()
    
    def compare_with_baseline(self, baseline_file: str):
        """Compare results with baseline."""
        baseline_analyzer = MetricsAnalyzer(baseline_file)
        
        print("\n=== BASELINE COMPARISON ===")
        
        # Success rate comparison
        current_success = self.df['success'].mean()
        baseline_success = baseline_analyzer.df['success'].mean()
        success_change = current_success - baseline_success
        
        print(f"Current Success Rate: {current_success:.2%}")
        print(f"Baseline Success Rate: {baseline_success:.2%}")
        print(f"Change: {success_change:+.2%}")
        
        # Efficiency comparison
        current_turns = self.df['total_turns'].mean()
        baseline_turns = baseline_analyzer.df['total_turns'].mean()
        turns_change = current_turns - baseline_turns
        
        print(f"\nCurrent Avg Turns: {current_turns:.1f}")
        print(f"Baseline Avg Turns: {baseline_turns:.1f}")
        print(f"Change: {turns_change:+.1f}")
        
        # Cost comparison
        current_cost = self.df['total_cost'].mean()
        baseline_cost = baseline_analyzer.df['total_cost'].mean()
        cost_change = current_cost - baseline_cost
        
        print(f"\nCurrent Avg Cost: ${current_cost:.2f}")
        print(f"Baseline Avg Cost: ${baseline_cost:.2f}")
        print(f"Change: ${cost_change:+.2f}")
    
    def generate_report(self, output_file: str = 'evaluation_report.html'):
        """Generate comprehensive HTML report."""
        html_content = f"""
        <!DOCTYPE html>
        <html>
        <head>
            <title>Multi-Turn Evaluation Report</title>
            <style>
                body {{ font-family: Arial, sans-serif; margin: 40px; }}
                .metric {{ background: #f5f5f5; padding: 10px; margin: 10px 0; border-radius: 5px; }}
                .success {{ color: green; }}
                .failure {{ color: red; }}
                table {{ border-collapse: collapse; width: 100%; }}
                th, td {{ border: 1px solid #ddd; padding: 8px; text-align: left; }}
                th {{ background-color: #f2f2f2; }}
            </style>
        </head>
        <body>
            <h1>Multi-Turn Evaluation Report</h1>
            
            <h2>Executive Summary</h2>
            <div class="metric">
                <strong>Overall Success Rate:</strong> {self.df['success'].mean():.2%}
            </div>
            <div class="metric">
                <strong>Average Turns per Task:</strong> {self.df['total_turns'].mean():.1f}
            </div>
            <div class="metric">
                <strong>Total Cost:</strong> ${self.df['total_cost'].sum():.2f}
            </div>
            <div class="metric">
                <strong>Average Execution Time:</strong> {self.df['execution_time'].mean():.1f}s
            </div>
            
            <h2>Detailed Results</h2>
            {self.df.to_html(classes='table table-striped')}
            
            <h2>Category Analysis</h2>
            {self.df.groupby('task_category').agg({
                'success': 'mean',
                'total_turns': 'mean',
                'total_cost': 'mean',
                'execution_time': 'mean'
            }).round(2).to_html()}
            
        </body>
        </html>
        """
        
        with open(output_file, 'w') as f:
            f.write(html_content)
        
        print(f"Report generated: {output_file}")

# Example usage
if __name__ == "__main__":
    # Analyze results
    analyzer = MetricsAnalyzer('evaluation_results.json')
    
    # Run all analyses
    analyzer.analyze_success_rates()
    analyzer.analyze_efficiency_metrics()
    analyzer.analyze_cost_metrics()
    
    # Create visualizations
    analyzer.create_visualizations()
    
    # Compare with baseline (if available)
    try:
        analyzer.compare_with_baseline('baseline_results.json')
    except FileNotFoundError:
        print("No baseline file found for comparison")
    
    # Generate report
    analyzer.generate_report()