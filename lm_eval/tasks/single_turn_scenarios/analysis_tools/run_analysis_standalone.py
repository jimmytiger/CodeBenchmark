#!/usr/bin/env python3
"""
Standalone comprehensive analysis runner for single_turn_scenarios evaluation results.

This script can be run directly without relative import issues.
It demonstrates how to use all analysis tools together to generate
a complete evaluation report.
"""

import json
import argparse
import sys
from pathlib import Path
from typing import List, Dict, Any

# Add current directory to path for imports
current_dir = Path(__file__).parent
sys.path.insert(0, str(current_dir))

# Import analysis tools
try:
    from compare_models import ModelComparator
    from context_impact import ContextAnalyzer
    from scenario_analysis import ScenarioAnalyzer
    from generate_report import ReportGenerator
    
    TOOLS_AVAILABLE = {
        'ModelComparator': True,
        'ContextAnalyzer': True,
        'ScenarioAnalyzer': True,
        'ReportGenerator': True
    }
except ImportError as e:
    print(f"Warning: Some analysis tools could not be imported: {e}")
    TOOLS_AVAILABLE = {
        'ModelComparator': False,
        'ContextAnalyzer': False,
        'ScenarioAnalyzer': False,
        'ReportGenerator': False
    }


def load_results_from_json(results_path: str) -> List[Dict[str, Any]]:
    """Load evaluation results from JSON file."""
    results = []
    
    try:
        with open(results_path, 'r') as f:
            data = json.load(f)
            
        # Handle different JSON structures
        if isinstance(data, list):
            results = data
        elif isinstance(data, dict):
            if 'results' in data:
                # lm-eval format
                for task_name, task_results in data['results'].items():
                    result_entry = {
                        'task': task_name,
                        'model': data.get('model_name', 'unknown'),
                        'scenario': task_name.replace('single_turn_scenarios_', ''),
                        'difficulty': 'unknown',
                        'language': 'python',
                        'context_mode': 'unknown',
                        'metrics': task_results
                    }
                    results.append(result_entry)
            else:
                results = [data]
                
    except Exception as e:
        print(f"Error loading results from {results_path}: {e}")
        
    return results


def load_results_from_jsonl(results_path: str) -> List[Dict[str, Any]]:
    """Load evaluation results from JSONL file."""
    results = []
    
    try:
        with open(results_path, 'r') as f:
            for line_num, line in enumerate(f, 1):
                line = line.strip()
                if line:
                    try:
                        result = json.loads(line)
                        results.append(result)
                    except json.JSONDecodeError as e:
                        print(f"Warning: Could not parse line {line_num} in {results_path}: {e}")
                        
    except Exception as e:
        print(f"Error loading results from {results_path}: {e}")
        
    return results


def load_results(results_path: str) -> List[Dict[str, Any]]:
    """Load evaluation results from JSON or JSONL file."""
    path = Path(results_path)
    
    if not path.exists():
        print(f"Error: Results file {results_path} does not exist")
        return []
    
    if path.suffix.lower() == '.jsonl':
        return load_results_from_jsonl(results_path)
    else:
        return load_results_from_json(results_path)


def run_model_comparison(results_data: List[Dict[str, Any]], output_dir: Path):
    """Run model comparison analysis."""
    if not TOOLS_AVAILABLE['ModelComparator']:
        print("❌ ModelComparator not available")
        return
        
    print("🔍 Running model comparison analysis...")
    
    try:
        comparator = ModelComparator(results_data)
        report = comparator.generate_comparison_report()
        
        # Save results
        output_file = output_dir / "model_comparison.json"
        with open(output_file, 'w') as f:
            json.dump(report.__dict__, f, indent=2, default=str)
            
        print(f"✅ Model comparison saved to {output_file}")
        
    except Exception as e:
        print(f"❌ Model comparison failed: {e}")


def run_context_analysis(results_data: List[Dict[str, Any]], output_dir: Path):
    """Run context impact analysis."""
    if not TOOLS_AVAILABLE['ContextAnalyzer']:
        print("❌ ContextAnalyzer not available")
        return
        
    print("🔍 Running context impact analysis...")
    
    try:
        analyzer = ContextAnalyzer(results_data)
        report = analyzer.generate_context_report()
        
        # Save results
        output_file = output_dir / "context_analysis.json"
        with open(output_file, 'w') as f:
            json.dump(report.__dict__, f, indent=2, default=str)
            
        print(f"✅ Context analysis saved to {output_file}")
        
    except Exception as e:
        print(f"❌ Context analysis failed: {e}")


def run_scenario_analysis(results_data: List[Dict[str, Any]], output_dir: Path):
    """Run scenario performance analysis."""
    if not TOOLS_AVAILABLE['ScenarioAnalyzer']:
        print("❌ ScenarioAnalyzer not available")
        return
        
    print("🔍 Running scenario analysis...")
    
    try:
        analyzer = ScenarioAnalyzer(results_data)
        report = analyzer.generate_scenario_report()
        
        # Save results
        output_file = output_dir / "scenario_analysis.json"
        with open(output_file, 'w') as f:
            json.dump(report.__dict__, f, indent=2, default=str)
            
        print(f"✅ Scenario analysis saved to {output_file}")
        
    except Exception as e:
        print(f"❌ Scenario analysis failed: {e}")


def generate_comprehensive_report(results_data: List[Dict[str, Any]], output_dir: Path):
    """Generate comprehensive HTML report."""
    if not TOOLS_AVAILABLE['ReportGenerator']:
        print("❌ ReportGenerator not available")
        return
        
    print("📊 Generating comprehensive report...")
    
    try:
        generator = ReportGenerator(results_data)
        report_path = generator.generate_html_report(output_dir / "comprehensive_report.html")
        
        print(f"✅ Comprehensive report saved to {report_path}")
        
    except Exception as e:
        print(f"❌ Report generation failed: {e}")


def main():
    """Main analysis runner."""
    parser = argparse.ArgumentParser(
        description="Run comprehensive analysis on single_turn_scenarios evaluation results"
    )
    parser.add_argument(
        "results_path",
        help="Path to evaluation results file (JSON or JSONL)"
    )
    parser.add_argument(
        "--output-dir",
        default="analysis_output",
        help="Output directory for analysis results (default: analysis_output)"
    )
    parser.add_argument(
        "--skip-model-comparison",
        action="store_true",
        help="Skip model comparison analysis"
    )
    parser.add_argument(
        "--skip-context-analysis",
        action="store_true",
        help="Skip context impact analysis"
    )
    parser.add_argument(
        "--skip-scenario-analysis",
        action="store_true",
        help="Skip scenario performance analysis"
    )
    parser.add_argument(
        "--skip-report-generation",
        action="store_true",
        help="Skip comprehensive report generation"
    )
    
    args = parser.parse_args()
    
    print("🚀 Single Turn Scenarios - Comprehensive Analysis")
    print("=" * 60)
    
    # Check tool availability
    available_tools = [name for name, available in TOOLS_AVAILABLE.items() if available]
    unavailable_tools = [name for name, available in TOOLS_AVAILABLE.items() if not available]
    
    print(f"✅ Available tools: {', '.join(available_tools)}")
    if unavailable_tools:
        print(f"❌ Unavailable tools: {', '.join(unavailable_tools)}")
    print()
    
    # Load results
    print(f"📁 Loading results from {args.results_path}...")
    results_data = load_results(args.results_path)
    
    if not results_data:
        print("❌ No results data loaded. Exiting.")
        return 1
        
    print(f"✅ Loaded {len(results_data)} result entries")
    
    # Create output directory
    output_dir = Path(args.output_dir)
    output_dir.mkdir(exist_ok=True)
    print(f"📂 Output directory: {output_dir}")
    print()
    
    # Run analyses
    if not args.skip_model_comparison:
        run_model_comparison(results_data, output_dir)
        
    if not args.skip_context_analysis:
        run_context_analysis(results_data, output_dir)
        
    if not args.skip_scenario_analysis:
        run_scenario_analysis(results_data, output_dir)
        
    if not args.skip_report_generation:
        generate_comprehensive_report(results_data, output_dir)
    
    print()
    print("🏁 Analysis completed!")
    print(f"📊 Results saved to: {output_dir}")
    
    return 0


if __name__ == "__main__":
    sys.exit(main())