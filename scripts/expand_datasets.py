#!/usr/bin/env python3
"""
Dataset Expansion Script for AI Evaluation Engine

This script orchestrates the complete dataset expansion process, using all
the tools we've created to generate, validate, and ensure quality of
production-ready datasets.
"""

import json
import os
import sys
import subprocess
from pathlib import Path
from typing import Dict, List, Any, Optional
import argparse
import logging
from datetime import datetime
import concurrent.futures

# Add scripts directory to path for imports
sys.path.append(str(Path(__file__).parent))

from dataset_generator import DatasetGenerator
from dataset_validator import DatasetValidator, ValidationLevel
from multilingual_dataset_generator import MultilingualDatasetGenerator
from dataset_quality_assurance import DatasetQualityAssurance, QualityLevel

# Configure logging
logging.basicConfig(level=logging.INFO, format='%(asctime)s - %(levelname)s - %(message)s')
logger = logging.getLogger(__name__)

class DatasetExpansionOrchestrator:
    """Orchestrates the complete dataset expansion process"""
    
    def __init__(self, base_path: str = "lm_eval/tasks", output_dir: str = None):
        self.base_path = Path(base_path)
        self.output_dir = Path(output_dir) if output_dir else self.base_path
        
        # Initialize all tools
        self.dataset_generator = DatasetGenerator(str(self.base_path))
        self.validator = DatasetValidator(str(self.base_path))
        self.multilingual_generator = MultilingualDatasetGenerator(str(self.base_path))
        self.qa_system = DatasetQualityAssurance(str(self.base_path))
        
        # Configuration
        self.single_turn_scenarios = [
            "code_completion", "bug_fix", "function_generation", "code_translation",
            "algorithm_implementation", "api_design", "system_design", "database_design",
            "security_implementation", "performance_optimization", "documentation_generation",
            "testing_strategy", "full_stack_development"
        ]
        
        self.multi_turn_scenarios = [
            "code_review_process", "debugging_session", "design_iteration", "teaching_dialogue",
            "collaborative_development", "requirements_refinement", "architecture_discussion",
            "performance_tuning"
        ]
        
        self.quantitative_trading_scenarios = [
            "strategy_development", "multifactor_model_construction", "market_research_analysis",
            "portfolio_risk_assessment", "execution_algorithm_optimization", "high_frequency_trading",
            "fundamental_quant_analysis", "technical_quant_analysis"
        ]
        
        self.target_languages = ["python", "javascript", "java", "cpp", "go", "rust", "typescript"]
        self.natural_languages = ["en", "zh", "es", "fr", "de"]
    
    def expand_all_datasets(self, target_size: int = 100, include_multilingual: bool = True,
                          quality_level: str = "production") -> Dict[str, Any]:
        """Expand all datasets to production size"""
        logger.info("Starting comprehensive dataset expansion")
        logger.info(f"Target size per scenario: {target_size}")
        logger.info(f"Include multilingual: {include_multilingual}")
        logger.info(f"Quality level: {quality_level}")
        
        expansion_results = {
            "start_time": datetime.now().isoformat(),
            "target_size": target_size,
            "include_multilingual": include_multilingual,
            "quality_level": quality_level,
            "single_turn_results": {},
            "multi_turn_results": {},
            "multilingual_results": {},
            "validation_results": {},
            "quality_assurance_results": {},
            "summary": {}
        }
        
        try:
            # Step 1: Expand single-turn scenarios
            logger.info("Step 1: Expanding single-turn scenarios")
            expansion_results["single_turn_results"] = self._expand_single_turn_scenarios(target_size)
            
            # Step 2: Expand multi-turn scenarios
            logger.info("Step 2: Expanding multi-turn scenarios")
            expansion_results["multi_turn_results"] = self._expand_multi_turn_scenarios(target_size)
            
            # Step 3: Generate multilingual datasets (if requested)
            if include_multilingual:
                logger.info("Step 3: Generating multilingual datasets")
                expansion_results["multilingual_results"] = self._generate_multilingual_datasets(target_size // 2)
            
            # Step 4: Validate all datasets
            logger.info("Step 4: Validating all datasets")
            expansion_results["validation_results"] = self._validate_all_datasets()
            
            # Step 5: Run quality assurance
            logger.info("Step 5: Running quality assurance")
            expansion_results["quality_assurance_results"] = self._run_quality_assurance(quality_level)
            
            # Step 6: Generate summary
            logger.info("Step 6: Generating summary")
            expansion_results["summary"] = self._generate_expansion_summary(expansion_results)
            
            expansion_results["end_time"] = datetime.now().isoformat()
            expansion_results["status"] = "completed"
            
        except Exception as e:
            logger.error(f"Dataset expansion failed: {e}")
            expansion_results["end_time"] = datetime.now().isoformat()
            expansion_results["status"] = "failed"
            expansion_results["error"] = str(e)
        
        return expansion_results
    
    def _expand_single_turn_scenarios(self, target_size: int) -> Dict[str, Any]:
        """Expand single-turn scenarios"""
        results = {}
        
        with concurrent.futures.ThreadPoolExecutor(max_workers=4) as executor:
            future_to_scenario = {}
            
            for scenario in self.single_turn_scenarios:
                future = executor.submit(self._expand_single_scenario, scenario, target_size)
                future_to_scenario[future] = scenario
            
            for future in concurrent.futures.as_completed(future_to_scenario):
                scenario = future_to_scenario[future]
                try:
                    result = future.result()
                    results[scenario] = result
                    logger.info(f"Completed single-turn scenario: {scenario}")
                except Exception as e:
                    logger.error(f"Failed to expand single-turn scenario {scenario}: {e}")
                    results[scenario] = {"status": "failed", "error": str(e)}
        
        return results
    
    def _expand_multi_turn_scenarios(self, target_size: int) -> Dict[str, Any]:
        """Expand multi-turn scenarios"""
        results = {}
        
        # Regular multi-turn scenarios
        with concurrent.futures.ThreadPoolExecutor(max_workers=4) as executor:
            future_to_scenario = {}
            
            for scenario in self.multi_turn_scenarios:
                future = executor.submit(self._expand_multi_scenario, scenario, target_size)
                future_to_scenario[future] = scenario
            
            for future in concurrent.futures.as_completed(future_to_scenario):
                scenario = future_to_scenario[future]
                try:
                    result = future.result()
                    results[scenario] = result
                    logger.info(f"Completed multi-turn scenario: {scenario}")
                except Exception as e:
                    logger.error(f"Failed to expand multi-turn scenario {scenario}: {e}")
                    results[scenario] = {"status": "failed", "error": str(e)}
        
        # Quantitative trading scenarios
        results["quantitative_trading"] = {}
        for scenario in self.quantitative_trading_scenarios:
            try:
                result = self._expand_quantitative_trading_scenario(scenario, target_size)
                results["quantitative_trading"][scenario] = result
                logger.info(f"Completed quantitative trading scenario: {scenario}")
            except Exception as e:
                logger.error(f"Failed to expand quantitative trading scenario {scenario}: {e}")
                results["quantitative_trading"][scenario] = {"status": "failed", "error": str(e)}
        
        return results
    
    def _generate_multilingual_datasets(self, target_size: int) -> Dict[str, Any]:
        """Generate multilingual datasets"""
        results = {}
        
        try:
            # Generate multilingual datasets for key scenarios
            key_scenarios = ["code_completion", "function_generation", "algorithm_implementation", "bug_fix"]
            
            for scenario in key_scenarios:
                logger.info(f"Generating multilingual dataset for: {scenario}")
                problems = self.multilingual_generator.generate_multilingual_dataset(
                    scenario, target_size, self.target_languages[:5], self.natural_languages[:3]
                )
                
                # Save multilingual datasets
                self.multilingual_generator.save_multilingual_datasets(problems, str(self.output_dir))
                
                results[scenario] = {
                    "status": "completed",
                    "problems_generated": len(problems),
                    "languages": self.target_languages[:5],
                    "natural_languages": self.natural_languages[:3]
                }
            
            # Generate cross-language evaluation dataset
            logger.info("Generating cross-language evaluation dataset")
            cross_lang_problems = self.multilingual_generator.generate_cross_language_evaluation_dataset(target_size)
            self.multilingual_generator.save_multilingual_datasets(cross_lang_problems, str(self.output_dir))
            
            results["cross_language_evaluation"] = {
                "status": "completed",
                "problems_generated": len(cross_lang_problems)
            }
            
        except Exception as e:
            logger.error(f"Failed to generate multilingual datasets: {e}")
            results["error"] = str(e)
        
        return results
    
    def _expand_single_scenario(self, scenario: str, target_size: int) -> Dict[str, Any]:
        """Expand a single single-turn scenario"""
        try:
            # Check current size
            current_size = self._get_current_dataset_size(scenario, "single_turn")
            
            if current_size >= target_size:
                return {
                    "status": "already_sufficient",
                    "current_size": current_size,
                    "target_size": target_size
                }
            
            # Generate additional problems
            problems_needed = target_size - current_size
            logger.info(f"Generating {problems_needed} problems for {scenario}")
            
            problems = self.dataset_generator.generate_single_turn_problems(scenario, problems_needed)
            
            # Save problems
            self.dataset_generator.save_datasets(problems, None, str(self.output_dir))
            
            return {
                "status": "completed",
                "current_size": current_size,
                "problems_generated": len(problems),
                "new_total_size": current_size + len(problems)
            }
            
        except Exception as e:
            return {"status": "failed", "error": str(e)}
    
    def _expand_multi_scenario(self, scenario: str, target_size: int) -> Dict[str, Any]:
        """Expand a single multi-turn scenario"""
        try:
            # Check current size
            current_size = self._get_current_dataset_size(scenario, "multi_turn")
            
            if current_size >= target_size:
                return {
                    "status": "already_sufficient",
                    "current_size": current_size,
                    "target_size": target_size
                }
            
            # Generate additional scenarios
            scenarios_needed = target_size - current_size
            logger.info(f"Generating {scenarios_needed} scenarios for {scenario}")
            
            scenarios = self.dataset_generator.generate_multi_turn_scenarios(scenario, scenarios_needed)
            
            # Save scenarios
            self.dataset_generator.save_datasets(None, scenarios, str(self.output_dir))
            
            return {
                "status": "completed",
                "current_size": current_size,
                "scenarios_generated": len(scenarios),
                "new_total_size": current_size + len(scenarios)
            }
            
        except Exception as e:
            return {"status": "failed", "error": str(e)}
    
    def _expand_quantitative_trading_scenario(self, scenario: str, target_size: int) -> Dict[str, Any]:
        """Expand a quantitative trading scenario"""
        try:
            # Check current size
            current_size = self._get_current_dataset_size(scenario, "quantitative_trading")
            
            if current_size >= target_size:
                return {
                    "status": "already_sufficient",
                    "current_size": current_size,
                    "target_size": target_size
                }
            
            # Generate additional scenarios
            scenarios_needed = target_size - current_size
            logger.info(f"Generating {scenarios_needed} quantitative trading scenarios for {scenario}")
            
            scenarios = self.dataset_generator.generate_multi_turn_scenarios(scenario, scenarios_needed)
            
            # Save scenarios in quantitative trading directory
            qt_dir = self.output_dir / "multi_turn_scenarios" / "quantitative_trading" / scenario
            qt_dir.mkdir(parents=True, exist_ok=True)
            
            scenarios_file = qt_dir / "scenarios.jsonl"
            with open(scenarios_file, 'a') as f:  # Append to existing file
                for scenario_obj in scenarios:
                    f.write(json.dumps(scenario_obj.__dict__) + '\n')
            
            return {
                "status": "completed",
                "current_size": current_size,
                "scenarios_generated": len(scenarios),
                "new_total_size": current_size + len(scenarios)
            }
            
        except Exception as e:
            return {"status": "failed", "error": str(e)}
    
    def _get_current_dataset_size(self, scenario: str, dataset_type: str) -> int:
        """Get current size of a dataset"""
        try:
            if dataset_type == "single_turn":
                # Check both main problems file and scenario-specific file
                main_file = self.base_path / "single_turn_scenarios" / "problems.jsonl"
                scenario_file = self.base_path / "single_turn_scenarios" / scenario / "problems.jsonl"
                
                count = 0
                
                # Count from main file
                if main_file.exists():
                    with open(main_file, 'r') as f:
                        for line in f:
                            try:
                                item = json.loads(line.strip())
                                if item.get('scenario') == scenario:
                                    count += 1
                            except:
                                continue
                
                # Count from scenario-specific file
                if scenario_file.exists():
                    with open(scenario_file, 'r') as f:
                        count += sum(1 for line in f if line.strip())
                
                return count
                
            elif dataset_type == "multi_turn":
                scenario_file = self.base_path / "multi_turn_scenarios" / scenario / "scenarios.jsonl"
                if scenario_file.exists():
                    with open(scenario_file, 'r') as f:
                        return sum(1 for line in f if line.strip())
                return 0
                
            elif dataset_type == "quantitative_trading":
                scenario_file = self.base_path / "multi_turn_scenarios" / "quantitative_trading" / scenario / "scenarios.jsonl"
                if scenario_file.exists():
                    with open(scenario_file, 'r') as f:
                        return sum(1 for line in f if line.strip())
                return 0
                
        except Exception as e:
            logger.warning(f"Error getting current dataset size for {scenario}: {e}")
            return 0
    
    def _validate_all_datasets(self) -> Dict[str, Any]:
        """Validate all datasets"""
        try:
            validation_level = ValidationLevel.COMPREHENSIVE
            reports = self.validator.validate_all_datasets(validation_level)
            
            results = {
                "total_datasets": len(reports),
                "passed": sum(1 for r in reports if r.overall_status.value == "pass"),
                "warned": sum(1 for r in reports if r.overall_status.value == "warn"),
                "failed": sum(1 for r in reports if r.overall_status.value == "fail"),
                "average_quality_score": sum(r.quality_score for r in reports) / len(reports) if reports else 0,
                "reports": [
                    {
                        "dataset_path": r.dataset_path,
                        "dataset_type": r.dataset_type,
                        "total_items": r.total_items,
                        "overall_status": r.overall_status.value,
                        "quality_score": r.quality_score
                    }
                    for r in reports
                ]
            }
            
            # Save validation report
            validation_report = self.validator.generate_validation_report(
                reports, str(self.output_dir / "validation_report.md")
            )
            
            return results
            
        except Exception as e:
            logger.error(f"Validation failed: {e}")
            return {"status": "failed", "error": str(e)}
    
    def _run_quality_assurance(self, quality_level: str) -> Dict[str, Any]:
        """Run quality assurance on all datasets"""
        try:
            qa_level = QualityLevel(quality_level)
            
            # Find all dataset files
            dataset_files = []
            dataset_files.extend(self.output_dir.glob("single_turn_scenarios/**/*.jsonl"))
            dataset_files.extend(self.output_dir.glob("multi_turn_scenarios/**/*.jsonl"))
            dataset_files.extend(self.output_dir.glob("multilingual_datasets/**/*.jsonl"))
            
            qa_results = []
            
            for dataset_file in dataset_files:
                try:
                    report = self.qa_system.run_quality_assurance(str(dataset_file), qa_level)
                    qa_results.append(report)
                except Exception as e:
                    logger.warning(f"QA failed for {dataset_file}: {e}")
            
            results = {
                "total_datasets": len(qa_results),
                "production_ready": sum(1 for r in qa_results if r.production_ready),
                "average_score": sum(r.overall_score for r in qa_results) / len(qa_results) if qa_results else 0,
                "grade_distribution": {},
                "reports": [
                    {
                        "dataset_path": r.dataset_path,
                        "overall_score": r.overall_score,
                        "quality_grade": r.quality_grade,
                        "production_ready": r.production_ready
                    }
                    for r in qa_results
                ]
            }
            
            # Calculate grade distribution
            grades = [r.quality_grade for r in qa_results]
            for grade in ["A", "B", "C", "D", "F"]:
                results["grade_distribution"][grade] = grades.count(grade)
            
            return results
            
        except Exception as e:
            logger.error(f"Quality assurance failed: {e}")
            return {"status": "failed", "error": str(e)}
    
    def _generate_expansion_summary(self, expansion_results: Dict[str, Any]) -> Dict[str, Any]:
        """Generate expansion summary"""
        summary = {
            "total_scenarios_processed": 0,
            "total_problems_generated": 0,
            "total_scenarios_generated": 0,
            "successful_expansions": 0,
            "failed_expansions": 0,
            "validation_summary": {},
            "quality_summary": {},
            "recommendations": []
        }
        
        # Count single-turn results
        for scenario, result in expansion_results.get("single_turn_results", {}).items():
            summary["total_scenarios_processed"] += 1
            if result.get("status") == "completed":
                summary["successful_expansions"] += 1
                summary["total_problems_generated"] += result.get("problems_generated", 0)
            else:
                summary["failed_expansions"] += 1
        
        # Count multi-turn results
        for scenario, result in expansion_results.get("multi_turn_results", {}).items():
            if isinstance(result, dict) and "status" in result:
                summary["total_scenarios_processed"] += 1
                if result.get("status") == "completed":
                    summary["successful_expansions"] += 1
                    summary["total_scenarios_generated"] += result.get("scenarios_generated", 0)
                else:
                    summary["failed_expansions"] += 1
            elif isinstance(result, dict):  # Quantitative trading nested results
                for qt_scenario, qt_result in result.items():
                    summary["total_scenarios_processed"] += 1
                    if qt_result.get("status") == "completed":
                        summary["successful_expansions"] += 1
                        summary["total_scenarios_generated"] += qt_result.get("scenarios_generated", 0)
                    else:
                        summary["failed_expansions"] += 1
        
        # Validation summary
        validation_results = expansion_results.get("validation_results", {})
        if validation_results and "status" not in validation_results:
            summary["validation_summary"] = {
                "total_datasets": validation_results.get("total_datasets", 0),
                "passed": validation_results.get("passed", 0),
                "failed": validation_results.get("failed", 0),
                "average_quality_score": validation_results.get("average_quality_score", 0)
            }
        
        # Quality assurance summary
        qa_results = expansion_results.get("quality_assurance_results", {})
        if qa_results and "status" not in qa_results:
            summary["quality_summary"] = {
                "total_datasets": qa_results.get("total_datasets", 0),
                "production_ready": qa_results.get("production_ready", 0),
                "average_score": qa_results.get("average_score", 0),
                "grade_distribution": qa_results.get("grade_distribution", {})
            }
        
        # Generate recommendations
        if summary["failed_expansions"] > 0:
            summary["recommendations"].append("Review and fix failed dataset expansions")
        
        if validation_results.get("failed", 0) > 0:
            summary["recommendations"].append("Address validation failures before production use")
        
        if qa_results.get("production_ready", 0) < qa_results.get("total_datasets", 1):
            summary["recommendations"].append("Improve dataset quality to meet production standards")
        
        if not summary["recommendations"]:
            summary["recommendations"].append("All datasets successfully expanded and validated")
        
        return summary
    
    def save_expansion_results(self, results: Dict[str, Any], output_file: str = None):
        """Save expansion results to file"""
        if not output_file:
            timestamp = datetime.now().strftime("%Y%m%d_%H%M%S")
            output_file = str(self.output_dir / f"dataset_expansion_results_{timestamp}.json")
        
        with open(output_file, 'w') as f:
            json.dumps(results, f, indent=2, default=str)
        
        logger.info(f"Expansion results saved to: {output_file}")
        
        # Also save a summary report
        summary_file = output_file.replace('.json', '_summary.md')
        self._generate_summary_report(results, summary_file)
    
    def _generate_summary_report(self, results: Dict[str, Any], output_file: str):
        """Generate human-readable summary report"""
        lines = []
        lines.append("# Dataset Expansion Summary Report")
        lines.append(f"Generated: {results.get('start_time', 'Unknown')}")
        lines.append("")
        
        summary = results.get("summary", {})
        
        lines.append("## Overview")
        lines.append(f"- Total scenarios processed: {summary.get('total_scenarios_processed', 0)}")
        lines.append(f"- Successful expansions: {summary.get('successful_expansions', 0)}")
        lines.append(f"- Failed expansions: {summary.get('failed_expansions', 0)}")
        lines.append(f"- Total problems generated: {summary.get('total_problems_generated', 0)}")
        lines.append(f"- Total scenarios generated: {summary.get('total_scenarios_generated', 0)}")
        lines.append("")
        
        # Validation summary
        validation_summary = summary.get("validation_summary", {})
        if validation_summary:
            lines.append("## Validation Results")
            lines.append(f"- Total datasets validated: {validation_summary.get('total_datasets', 0)}")
            lines.append(f"- Passed validation: {validation_summary.get('passed', 0)}")
            lines.append(f"- Failed validation: {validation_summary.get('failed', 0)}")
            lines.append(f"- Average quality score: {validation_summary.get('average_quality_score', 0):.1f}/100")
            lines.append("")
        
        # Quality assurance summary
        quality_summary = summary.get("quality_summary", {})
        if quality_summary:
            lines.append("## Quality Assurance Results")
            lines.append(f"- Total datasets assessed: {quality_summary.get('total_datasets', 0)}")
            lines.append(f"- Production ready: {quality_summary.get('production_ready', 0)}")
            lines.append(f"- Average quality score: {quality_summary.get('average_score', 0):.1f}/100")
            
            grade_dist = quality_summary.get("grade_distribution", {})
            if grade_dist:
                lines.append("- Grade distribution:")
                for grade, count in grade_dist.items():
                    lines.append(f"  - {grade}: {count}")
            lines.append("")
        
        # Recommendations
        recommendations = summary.get("recommendations", [])
        if recommendations:
            lines.append("## Recommendations")
            for rec in recommendations:
                lines.append(f"- {rec}")
            lines.append("")
        
        # Status
        status = results.get("status", "unknown")
        lines.append(f"## Status: {status.upper()}")
        if status == "failed":
            error = results.get("error", "Unknown error")
            lines.append(f"Error: {error}")
        
        with open(output_file, 'w') as f:
            f.write('\n'.join(lines))
        
        logger.info(f"Summary report saved to: {output_file}")

def main():
    """Main function for command-line usage"""
    parser = argparse.ArgumentParser(description="Expand datasets to production size")
    parser.add_argument("--target-size", type=int, default=100, help="Target size per scenario")
    parser.add_argument("--scenarios", nargs="+", help="Specific scenarios to expand (optional)")
    parser.add_argument("--type", choices=["single", "multi", "both"], default="both", help="Type of scenarios to expand")
    parser.add_argument("--include-multilingual", action="store_true", help="Include multilingual datasets")
    parser.add_argument("--quality-level", choices=["basic", "standard", "premium", "production"], 
                       default="production", help="Quality assurance level")
    parser.add_argument("--output-dir", type=str, help="Output directory for expanded datasets")
    parser.add_argument("--base-path", type=str, default="lm_eval/tasks", help="Base path for task directories")
    parser.add_argument("--parallel", action="store_true", help="Run expansions in parallel")
    
    args = parser.parse_args()
    
    # Initialize orchestrator
    orchestrator = DatasetExpansionOrchestrator(args.base_path, args.output_dir)
    
    # Run expansion
    if args.scenarios:
        # Expand specific scenarios
        logger.info(f"Expanding specific scenarios: {args.scenarios}")
        # Implementation for specific scenarios would go here
        results = {"status": "not_implemented", "message": "Specific scenario expansion not implemented"}
    else:
        # Expand all datasets
        results = orchestrator.expand_all_datasets(
            target_size=args.target_size,
            include_multilingual=args.include_multilingual,
            quality_level=args.quality_level
        )
    
    # Save results
    orchestrator.save_expansion_results(results)
    
    # Print summary
    summary = results.get("summary", {})
    print("\n" + "="*60)
    print("DATASET EXPANSION SUMMARY")
    print("="*60)
    print(f"Status: {results.get('status', 'unknown').upper()}")
    print(f"Scenarios processed: {summary.get('total_scenarios_processed', 0)}")
    print(f"Successful expansions: {summary.get('successful_expansions', 0)}")
    print(f"Failed expansions: {summary.get('failed_expansions', 0)}")
    print(f"Problems generated: {summary.get('total_problems_generated', 0)}")
    print(f"Scenarios generated: {summary.get('total_scenarios_generated', 0)}")
    
    validation_summary = summary.get("validation_summary", {})
    if validation_summary:
        print(f"Datasets validated: {validation_summary.get('total_datasets', 0)}")
        print(f"Validation passed: {validation_summary.get('passed', 0)}")
    
    quality_summary = summary.get("quality_summary", {})
    if quality_summary:
        print(f"Production ready: {quality_summary.get('production_ready', 0)}")
        print(f"Average quality score: {quality_summary.get('average_score', 0):.1f}/100")
    
    print("="*60)
    
    # Exit with appropriate code
    if results.get("status") == "failed":
        exit(1)
    elif summary.get("failed_expansions", 0) > 0:
        exit(2)
    else:
        exit(0)

if __name__ == "__main__":
    main()