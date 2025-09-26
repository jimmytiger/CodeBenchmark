#!/usr/bin/env python3
"""
Comprehensive validation script for all single_turn_scenarios tasks.
Tests each task type and validates the analysis tools.
"""

import subprocess
import json
import os
import glob
from datetime import datetime
from pathlib import Path

def run_task_evaluation(task_name, limit=1, timeout=300):
    """Run a single task evaluation and return results."""
    timestamp = datetime.now().strftime("%Y%m%d_%H%M%S")
    output_file = f"results/validation_{task_name}_{timestamp}.json"
    
    cmd = [
        "python", "-m", "lm_eval",
        "--model", "claude-local",
        "--model_args", "model=claude-3-haiku-20240307",
        "--tasks", task_name,
        "--limit", str(limit),
        "--output_path", output_file,
        "--predict_only"
    ]
    
    print(f"🧪 Testing: {task_name}")
    
    try:
        result = subprocess.run(cmd, capture_output=True, text=True, timeout=timeout)
        
        if result.returncode == 0:
            print(f"✅ SUCCESS: {task_name}")
            
            # Find actual output files
            pattern = output_file.replace('.json', '_*.json')
            actual_files = glob.glob(pattern)
            
            if actual_files:
                main_file = actual_files[0]
                sample_pattern = main_file.replace('.json', '').replace('results/', 'results/samples_') + '.jsonl'
                sample_files = glob.glob(sample_pattern)
                
                return {
                    'task': task_name,
                    'status': 'success',
                    'main_file': main_file,
                    'sample_file': sample_files[0] if sample_files else None,
                    'error': None
                }
            else:
                return {
                    'task': task_name,
                    'status': 'success_no_files',
                    'main_file': None,
                    'sample_file': None,
                    'error': 'No output files found'
                }
        else:
            print(f"❌ FAILED: {task_name}")
            print(f"   Error: {result.stderr[:200]}...")
            return {
                'task': task_name,
                'status': 'failed',
                'main_file': None,
                'sample_file': None,
                'error': result.stderr
            }
            
    except subprocess.TimeoutExpired:
        print(f"⏰ TIMEOUT: {task_name}")
        return {
            'task': task_name,
            'status': 'timeout',
            'main_file': None,
            'sample_file': None,
            'error': 'Evaluation timeout'
        }
    except Exception as e:
        print(f"💥 EXCEPTION: {task_name} - {e}")
        return {
            'task': task_name,
            'status': 'exception',
            'main_file': None,
            'sample_file': None,
            'error': str(e)
        }

def test_analysis_tools():
    """Test the analysis tools in the analysis_tools directory."""
    print("\n🔍 Testing Analysis Tools")
    print("=" * 50)
    
    analysis_dir = Path("lm_eval/tasks/single_turn_scenarios/analysis_tools")
    if not analysis_dir.exists():
        print("❌ Analysis tools directory not found")
        return []
    
    analysis_results = []
    
    # List all Python scripts in analysis_tools
    analysis_scripts = list(analysis_dir.glob("*.py"))
    
    for script in analysis_scripts:
        print(f"🧪 Testing: {script.name}")
        
        try:
            # Try to import the script to check for syntax errors
            import importlib.util
            spec = importlib.util.spec_from_file_location("analysis_module", script)
            if spec and spec.loader:
                module = importlib.util.module_from_spec(spec)
                spec.loader.exec_module(module)
                print(f"✅ Import successful: {script.name}")
                analysis_results.append({
                    'script': script.name,
                    'status': 'import_success',
                    'error': None
                })
            else:
                print(f"❌ Import failed: {script.name}")
                analysis_results.append({
                    'script': script.name,
                    'status': 'import_failed',
                    'error': 'Could not create module spec'
                })
                
        except Exception as e:
            print(f"❌ Import error: {script.name} - {e}")
            analysis_results.append({
                'script': script.name,
                'status': 'import_error',
                'error': str(e)
            })
    
    return analysis_results

def main():
    """Main validation function."""
    print("🚀 Single Turn Scenarios - Comprehensive Task Validation")
    print("=" * 70)
    
    # Ensure results directory exists
    os.makedirs("results", exist_ok=True)
    
    # List of all single_turn_scenarios tasks to test
    tasks_to_test = [
        "single_turn_scenarios_function_generation",
        "single_turn_scenarios_code_completion",
        "single_turn_scenarios_bug_fix",
        "single_turn_scenarios_algorithm_implementation",
        "single_turn_scenarios_api_design",
        "single_turn_scenarios_system_design",
        "single_turn_scenarios_security",
        "single_turn_scenarios_database_design",
        "single_turn_scenarios_performance_optimization",
        "single_turn_scenarios_full_stack",
        "single_turn_scenarios_testing_strategy",
        "single_turn_scenarios_documentation",
        "single_turn_scenarios_code_translation",
        # Suite tasks
        "single_turn_scenarios_python",
        "single_turn_scenarios_intermediate",
        "single_turn_scenarios_minimal_context",
    ]
    
    print(f"📋 Testing {len(tasks_to_test)} task types...")
    print()
    
    # Test each task
    results = []
    for task in tasks_to_test:
        result = run_task_evaluation(task, limit=1)
        results.append(result)
        print()
    
    # Test analysis tools
    analysis_results = test_analysis_tools()
    
    # Generate summary report
    print("\n📊 VALIDATION SUMMARY")
    print("=" * 70)
    
    successful_tasks = [r for r in results if r['status'] == 'success']
    failed_tasks = [r for r in results if r['status'] in ['failed', 'timeout', 'exception']]
    
    print(f"✅ Successful tasks: {len(successful_tasks)}/{len(results)}")
    print(f"❌ Failed tasks: {len(failed_tasks)}/{len(results)}")
    
    if successful_tasks:
        print("\n✅ SUCCESSFUL TASKS:")
        for result in successful_tasks:
            print(f"   - {result['task']}")
    
    if failed_tasks:
        print("\n❌ FAILED TASKS:")
        for result in failed_tasks:
            print(f"   - {result['task']} ({result['status']})")
            if result['error']:
                error_preview = result['error'][:100] + "..." if len(result['error']) > 100 else result['error']
                print(f"     Error: {error_preview}")
    
    # Analysis tools summary
    if analysis_results:
        successful_analysis = [r for r in analysis_results if r['status'] == 'import_success']
        failed_analysis = [r for r in analysis_results if r['status'] != 'import_success']
        
        print(f"\n🔍 Analysis Tools: {len(successful_analysis)}/{len(analysis_results)} working")
        
        if successful_analysis:
            print("✅ Working analysis tools:")
            for result in successful_analysis:
                print(f"   - {result['script']}")
        
        if failed_analysis:
            print("❌ Failed analysis tools:")
            for result in failed_analysis:
                print(f"   - {result['script']} ({result['status']})")
    
    # Save detailed results
    report = {
        'timestamp': datetime.now().isoformat(),
        'task_results': results,
        'analysis_results': analysis_results,
        'summary': {
            'total_tasks': len(results),
            'successful_tasks': len(successful_tasks),
            'failed_tasks': len(failed_tasks),
            'success_rate': len(successful_tasks) / len(results) * 100
        }
    }
    
    report_file = f"results/validation_report_{datetime.now().strftime('%Y%m%d_%H%M%S')}.json"
    with open(report_file, 'w') as f:
        json.dump(report, f, indent=2)
    
    print(f"\n📄 Detailed report saved to: {report_file}")
    
    # Generate usage examples for successful tasks
    if successful_tasks:
        print("\n🎯 USAGE EXAMPLES FOR SUCCESSFUL TASKS:")
        print("=" * 70)
        
        for i, result in enumerate(successful_tasks[:3]):  # Show first 3 examples
            task = result['task']
            print(f"\n{i+1}. {task}:")
            print(f"   python -m lm_eval --model claude-local \\")
            print(f"     --model_args model=claude-3-haiku-20240307 \\")
            print(f"     --tasks {task} --limit 2 \\")
            print(f"     --output_path results/{task.replace('single_turn_scenarios_', '')}.json")
    
    print(f"\n🏁 Validation completed! Success rate: {len(successful_tasks)}/{len(results)} ({len(successful_tasks)/len(results)*100:.1f}%)")

if __name__ == "__main__":
    main()