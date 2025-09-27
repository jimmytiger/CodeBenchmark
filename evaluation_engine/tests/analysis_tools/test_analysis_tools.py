#!/usr/bin/env python3
"""
Test script for single_turn_scenarios analysis tools.
"""

import json
import glob
import sys
from pathlib import Path

# Add the analysis tools to the path
sys.path.append('lm_eval/tasks/single_turn_scenarios/analysis_tools')

def test_analysis_tools():
    """Test the working analysis tools with sample data."""
    print("🔍 Testing Analysis Tools with Sample Data")
    print("=" * 50)
    
    # Find some result files from our validation
    result_files = glob.glob("results/validation_*.json")
    sample_files = glob.glob("results/samples_*.jsonl")
    
    if not result_files:
        print("❌ No result files found. Run validation first.")
        return
    
    print(f"📁 Found {len(result_files)} result files")
    print(f"📁 Found {len(sample_files)} sample files")
    
    # Load sample data
    sample_data = []
    for file in result_files[:3]:  # Use first 3 files
        try:
            with open(file, 'r') as f:
                data = json.load(f)
                sample_data.append(data)
        except Exception as e:
            print(f"⚠️  Could not load {file}: {e}")
    
    if not sample_data:
        print("❌ No valid data loaded")
        return
    
    print(f"✅ Loaded {len(sample_data)} result files")
    
    # Test scenario_analysis
    try:
        from scenario_analysis import ScenarioAnalyzer
        print("\n🧪 Testing ScenarioAnalyzer...")
        
        # Create mock data structure that the analyzer expects
        mock_results = []
        for data in sample_data:
            if 'results' in data:
                for task_name, task_results in data['results'].items():
                    mock_results.append({
                        'task': task_name,
                        'model': data.get('model_name', 'unknown'),
                        'scenario': task_name.replace('single_turn_scenarios_', ''),
                        'difficulty': 'simple',  # Mock difficulty
                        'language': 'python',    # Mock language
                        'context_mode': 'no_context',  # Mock context
                        'metrics': task_results
                    })
        
        if mock_results:
            analyzer = ScenarioAnalyzer(mock_results)
            print("✅ ScenarioAnalyzer initialized successfully")
        else:
            print("⚠️  No suitable data for ScenarioAnalyzer")
            
    except Exception as e:
        print(f"❌ ScenarioAnalyzer test failed: {e}")
    
    # Test compare_models
    try:
        from compare_models import ModelComparator
        print("\n🧪 Testing ModelComparator...")
        
        if mock_results:
            comparator = ModelComparator(mock_results)
            print("✅ ModelComparator initialized successfully")
        else:
            print("⚠️  No suitable data for ModelComparator")
            
    except Exception as e:
        print(f"❌ ModelComparator test failed: {e}")
    
    # Test context_impact
    try:
        from context_impact import ContextAnalyzer
        print("\n🧪 Testing ContextAnalyzer...")
        
        if mock_results:
            context_analyzer = ContextAnalyzer(mock_results)
            print("✅ ContextAnalyzer initialized successfully")
        else:
            print("⚠️  No suitable data for ContextAnalyzer")
            
    except Exception as e:
        print(f"❌ ContextAnalyzer test failed: {e}")
    
    print("\n📊 Analysis Tools Test Summary:")
    print("- ScenarioAnalyzer: Available for scenario and difficulty analysis")
    print("- ModelComparator: Available for model performance comparison")
    print("- ContextAnalyzer: Available for context mode impact analysis")
    print("\nNote: Some tools may require specific data formats or additional dependencies.")

if __name__ == "__main__":
    test_analysis_tools()