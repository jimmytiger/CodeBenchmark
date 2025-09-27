#!/usr/bin/env python3

import json
import os
import sys
import glob
from pathlib import Path

def load_results(results_dir):
    """Load the multi-turn coding results."""
    
    # Find result files with the actual naming pattern
    result_files = glob.glob(os.path.join(results_dir, "multi_turn_results_*.json"))
    
    results = {}
    
    if result_files:
        latest_result = max(result_files, key=os.path.getmtime)
        with open(latest_result, 'r') as f:
            results['Multi-Turn Coding'] = json.load(f)
            
    return results

def extract_metrics(result_data):
    """Extract metrics from result data."""
    if 'results' not in result_data:
        return {}
    
    task_results = result_data['results'].get('multi_turn_coding_eval_claude_code', {})
    
    metrics = {}
    for key, value in task_results.items():
        if key.endswith('_stderr,extract_responses') or 'alias' in key:
            continue
        if isinstance(value, (int, float)):
            # Clean up metric names
            clean_name = key.replace(',extract_responses', '').replace('_', ' ').title()
            metrics[clean_name] = value
    
    return metrics

def main():
    if len(sys.argv) != 2:
        print("Usage: python analyze_my_results.py <results_directory>")
        print("Example: python analyze_my_results.py results/results")
        sys.exit(1)
    
    results_dir = sys.argv[1]
    
    if not os.path.exists(results_dir):
        print(f"❌ Results directory not found: {results_dir}")
        sys.exit(1)
    
    print("🧪 Multi-Turn Coding Evaluation Results")
    print("=" * 60)
    
    results = load_results(results_dir)
    
    if not results:
        print("❌ No result files found")
        print(f"Looking for files matching: multi_turn_results_*.json")
        print(f"Found files: {os.listdir(results_dir)}")
        sys.exit(1)
    
    # Display results
    for scenario, data in results.items():
        print(f"\n📊 {scenario}")
        print("-" * 40)
        
        metrics = extract_metrics(data)
        
        if not metrics:
            print("   No metrics found")
            continue
            
        for metric, value in metrics.items():
            if value >= 0.9:
                status = "🟢"
            elif value >= 0.7:
                status = "🟡"
            elif value >= 0.5:
                status = "🟠"
            else:
                status = "🔴"
            
            print(f"   {status} {metric:<35} {value:.3f}")
    
    print(f"\n✅ Analysis complete!")
    print(f"📁 Results directory: {results_dir}")
    
    # Show generated artifacts
    output_dir = "./output"
    if os.path.exists(output_dir):
        dirs = [d for d in os.listdir(output_dir) if os.path.isdir(os.path.join(output_dir, d))]
        if dirs:
            print(f"📂 Generated artifacts: {len(dirs)} problems")
            print(f"   Latest: {sorted(dirs)[-1] if dirs else 'None'}")

if __name__ == "__main__":
    main()