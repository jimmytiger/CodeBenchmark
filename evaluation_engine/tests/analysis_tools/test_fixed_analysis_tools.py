#!/usr/bin/env python3
"""
Test script to verify that the fixed analysis tools work correctly.
"""

import sys
import json
import glob
from pathlib import Path

def test_analysis_tools_imports():
    """Test importing all analysis tools."""
    print("🧪 Testing Analysis Tools Imports")
    print("=" * 50)
    
    # Test individual imports
    tools_status = {}
    
    # Test scenario_analysis
    try:
        sys.path.append('lm_eval/tasks/single_turn_scenarios/analysis_tools')
        from scenario_analysis import ScenarioAnalyzer
        tools_status['ScenarioAnalyzer'] = 'success'
        print("✅ ScenarioAnalyzer import successful")
    except Exception as e:
        tools_status['ScenarioAnalyzer'] = f'failed: {e}'
        print(f"❌ ScenarioAnalyzer import failed: {e}")
    
    # Test compare_models
    try:
        from compare_models import ModelComparator
        tools_status['ModelComparator'] = 'success'
        print("✅ ModelComparator import successful")
    except Exception as e:
        tools_status['ModelComparator'] = f'failed: {e}'
        print(f"❌ ModelComparator import failed: {e}")
    
    # Test context_impact
    try:
        from context_impact import ContextAnalyzer
        tools_status['ContextAnalyzer'] = 'success'
        print("✅ ContextAnalyzer import successful")
    except Exception as e:
        tools_status['ContextAnalyzer'] = f'failed: {e}'
        print(f"❌ ContextAnalyzer import failed: {e}")
    
    # Test generate_report
    try:
        from generate_report import ReportGenerator
        tools_status['ReportGenerator'] = 'success'
        print("✅ ReportGenerator import successful")
    except Exception as e:
        tools_status['ReportGenerator'] = f'failed: {e}'
        print(f"❌ ReportGenerator import failed: {e}")
    
    # Test run_analysis
    try:
        from run_analysis import load_results
        tools_status['run_analysis'] = 'success'
        print("✅ run_analysis import successful")
    except Exception as e:
        tools_status['run_analysis'] = f'failed: {e}'
        print(f"❌ run_analysis import failed: {e}")
    
    # Test __init__.py
    try:
        sys.path.append('lm_eval/tasks/single_turn_scenarios')
        from analysis_tools import get_available_tools
        available = get_available_tools()
        tools_status['__init__.py'] = 'success'
        print(f"✅ __init__.py import successful: {len(available)} tools available")
    except Exception as e:
        tools_status['__init__.py'] = f'failed: {e}'
        print(f"❌ __init__.py import failed: {e}")
    
    return tools_status

def test_standalone_runner():
    """Test the standalone analysis runner."""
    print("\n🧪 Testing Standalone Analysis Runner")
    print("=" * 50)
    
    try:
        # Import the standalone runner
        sys.path.append('lm_eval/tasks/single_turn_scenarios/analysis_tools')
        import run_analysis_standalone
        
        print("✅ Standalone runner import successful")
        
        # Test with sample data if available
        result_files = glob.glob("results/validation_*.json")
        if result_files:
            sample_file = result_files[0]
            print(f"📁 Testing with sample file: {sample_file}")
            
            # Test loading results
            results = run_analysis_standalone.load_results(sample_file)
            print(f"✅ Loaded {len(results)} result entries")
            
            # Test tool availability
            available_tools = [name for name, available in run_analysis_standalone.TOOLS_AVAILABLE.items() if available]
            print(f"✅ Available tools in standalone runner: {', '.join(available_tools)}")
            
        else:
            print("⚠️  No sample result files found for testing")
            
        return True
        
    except Exception as e:
        print(f"❌ Standalone runner test failed: {e}")
        return False

def test_tool_initialization():
    """Test initializing analysis tools with mock data."""
    print("\n🧪 Testing Tool Initialization")
    print("=" * 50)
    
    # Create mock data
    mock_data = [
        {
            'task': 'single_turn_scenarios_function_generation',
            'model': 'claude-3-haiku',
            'scenario': 'function_generation',
            'difficulty': 'simple',
            'language': 'python',
            'context_mode': 'no_context',
            'metrics': {'exact_match': 0.8, 'syntax_validity': 1.0}
        },
        {
            'task': 'single_turn_scenarios_code_completion',
            'model': 'claude-3-haiku',
            'scenario': 'code_completion',
            'difficulty': 'intermediate',
            'language': 'python',
            'context_mode': 'minimal_context',
            'metrics': {'exact_match': 0.6, 'syntax_validity': 0.9}
        }
    ]
    
    initialization_results = {}
    
    # Test ScenarioAnalyzer
    try:
        sys.path.append('lm_eval/tasks/single_turn_scenarios/analysis_tools')
        from scenario_analysis import ScenarioAnalyzer
        analyzer = ScenarioAnalyzer(mock_data)
        initialization_results['ScenarioAnalyzer'] = 'success'
        print("✅ ScenarioAnalyzer initialization successful")
    except Exception as e:
        initialization_results['ScenarioAnalyzer'] = f'failed: {e}'
        print(f"❌ ScenarioAnalyzer initialization failed: {e}")
    
    # Test ModelComparator
    try:
        from compare_models import ModelComparator
        comparator = ModelComparator(mock_data)
        initialization_results['ModelComparator'] = 'success'
        print("✅ ModelComparator initialization successful")
    except Exception as e:
        initialization_results['ModelComparator'] = f'failed: {e}'
        print(f"❌ ModelComparator initialization failed: {e}")
    
    # Test ContextAnalyzer
    try:
        from context_impact import ContextAnalyzer
        context_analyzer = ContextAnalyzer(mock_data)
        initialization_results['ContextAnalyzer'] = 'success'
        print("✅ ContextAnalyzer initialization successful")
    except Exception as e:
        initialization_results['ContextAnalyzer'] = f'failed: {e}'
        print(f"❌ ContextAnalyzer initialization failed: {e}")
    
    return initialization_results

def main():
    """Main test function."""
    print("🔧 Testing Fixed Analysis Tools")
    print("=" * 70)
    
    # Test imports
    import_results = test_analysis_tools_imports()
    
    # Test standalone runner
    standalone_success = test_standalone_runner()
    
    # Test tool initialization
    init_results = test_tool_initialization()
    
    # Summary
    print("\n📊 TEST SUMMARY")
    print("=" * 70)
    
    successful_imports = sum(1 for status in import_results.values() if status == 'success')
    total_imports = len(import_results)
    
    successful_inits = sum(1 for status in init_results.values() if status == 'success')
    total_inits = len(init_results)
    
    print(f"✅ Import tests: {successful_imports}/{total_imports} successful")
    print(f"✅ Initialization tests: {successful_inits}/{total_inits} successful")
    print(f"✅ Standalone runner: {'working' if standalone_success else 'failed'}")
    
    if successful_imports == total_imports and successful_inits == total_inits and standalone_success:
        print("\n🎉 All analysis tools are now working correctly!")
        return 0
    else:
        print("\n⚠️  Some issues remain:")
        for tool, status in import_results.items():
            if status != 'success':
                print(f"   - {tool}: {status}")
        for tool, status in init_results.items():
            if status != 'success':
                print(f"   - {tool} init: {status}")
        return 1

if __name__ == "__main__":
    sys.exit(main())