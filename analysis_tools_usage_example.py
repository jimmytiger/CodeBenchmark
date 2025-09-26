#!/usr/bin/env python3
"""
Usage example for the single_turn_scenarios analysis tools.
"""

import sys
import json
import glob
from pathlib import Path

# Add analysis tools to path
sys.path.append('lm_eval/tasks/single_turn_scenarios/analysis_tools')

def main():
    """Demonstrate analysis tools usage."""
    print("📊 Analysis Tools Usage Example")
    print("=" * 50)
    
    # Load sample data from validation results
    result_files = glob.glob("results/validation_*.json")
    if not result_files:
        print("❌ No result files found. Run validation first.")
        return
    
    # Prepare sample data
    sample_data = []
    for file in result_files[:3]:
        with open(file, 'r') as f:
            data = json.load(f)
        if 'results' in data:
            for task_name, task_results in data['results'].items():
                sample_data.append({
                    'task': task_name,
                    'model': data.get('model_name', 'claude-3-haiku'),
                    'scenario': task_name.replace('single_turn_scenarios_', ''),
                    'difficulty': 'simple',
                    'language': 'python',
                    'context_mode': 'no_context',
                    'metrics': task_results
                })
    
    print(f"✅ Loaded {len(sample_data)} sample entries")
    
    # Example 1: ScenarioAnalyzer
    print("\n🔍 Example 1: ScenarioAnalyzer")
    from scenario_analysis import ScenarioAnalyzer
    analyzer = ScenarioAnalyzer(sample_data)
    print(f"   DataFrame shape: {analyzer.df.shape}")
    print("   Available methods:", [m for m in dir(analyzer) if not m.startswith('_')])
    
    # Example 2: ModelComparator  
    print("\n🔍 Example 2: ModelComparator")
    from compare_models import ModelComparator
    comparator = ModelComparator(sample_data)
    print(f"   DataFrame shape: {comparator.df.shape}")
    
    # Example 3: ContextAnalyzer
    print("\n🔍 Example 3: ContextAnalyzer")
    from context_impact import ContextAnalyzer
    context_analyzer = ContextAnalyzer(sample_data)
    print(f"   DataFrame shape: {context_analyzer.df.shape}")
    
    print("\n✅ All analysis tools working correctly!")

if __name__ == "__main__":
    main()