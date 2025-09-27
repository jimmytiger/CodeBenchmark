#!/usr/bin/env python3
"""
Demo Script for Dataset Expansion Tools

This script demonstrates how to use the dataset expansion tools to generate,
validate, and ensure quality of production-ready datasets.
"""

import json
import sys
import tempfile
import shutil
from pathlib import Path
from typing import Dict, List, Any
import logging

# Add scripts directory to path for imports
sys.path.append(str(Path(__file__).parent))

from dataset_generator import DatasetGenerator
from dataset_validator import DatasetValidator, ValidationLevel
from multilingual_dataset_generator import MultilingualDatasetGenerator
from dataset_quality_assurance import DatasetQualityAssurance, QualityLevel

# Configure logging
logging.basicConfig(level=logging.INFO, format='%(asctime)s - %(levelname)s - %(message)s')
logger = logging.getLogger(__name__)

def demo_basic_dataset_generation():
    """Demonstrate basic dataset generation"""
    print("\n" + "="*60)
    print("DEMO: Basic Dataset Generation")
    print("="*60)
    
    # Create temporary directory for demo
    demo_dir = Path(tempfile.mkdtemp(prefix="dataset_demo_"))
    base_path = demo_dir / "lm_eval" / "tasks"
    base_path.mkdir(parents=True, exist_ok=True)
    
    try:
        # Initialize generator
        generator = DatasetGenerator(str(base_path))
        
        # Generate single-turn problems
        print("Generating single-turn problems...")
        problems = generator.generate_single_turn_problems("code_completion", 5)
        
        print(f"Generated {len(problems)} problems:")
        for i, problem in enumerate(problems[:2]):  # Show first 2
            print(f"  {i+1}. {problem.title} ({problem.language}, {problem.difficulty})")
        
        # Generate multi-turn scenarios
        print("\nGenerating multi-turn scenarios...")
        scenarios = generator.generate_multi_turn_scenarios("code_review_process", 3)
        
        print(f"Generated {len(scenarios)} scenarios:")
        for i, scenario in enumerate(scenarios):
            print(f"  {i+1}. {scenario.id} ({scenario.difficulty}, {len(scenario.turns)} turns)")
        
        # Save datasets
        print("\nSaving datasets...")
        generator.save_datasets(problems, scenarios, str(base_path))
        
        # List created files
        created_files = list(base_path.rglob("*.jsonl"))
        print(f"Created {len(created_files)} dataset files:")
        for file in created_files:
            rel_path = file.relative_to(base_path)
            with open(file, 'r') as f:
                line_count = sum(1 for line in f if line.strip())
            print(f"  {rel_path}: {line_count} items")
        
        print("✅ Basic dataset generation completed successfully!")
        
    finally:
        # Cleanup
        shutil.rmtree(demo_dir)

def demo_multilingual_generation():
    """Demonstrate multilingual dataset generation"""
    print("\n" + "="*60)
    print("DEMO: Multilingual Dataset Generation")
    print("="*60)
    
    # Create temporary directory for demo
    demo_dir = Path(tempfile.mkdtemp(prefix="multilingual_demo_"))
    base_path = demo_dir / "lm_eval" / "tasks"
    base_path.mkdir(parents=True, exist_ok=True)
    
    try:
        # Initialize multilingual generator
        ml_generator = MultilingualDatasetGenerator(str(base_path))
        
        # Generate multilingual dataset
        print("Generating multilingual dataset...")
        target_languages = ["python", "javascript", "java"]
        natural_languages = ["en", "zh", "es"]
        
        problems = ml_generator.generate_multilingual_dataset(
            "function_generation", 3, target_languages, natural_languages
        )
        
        print(f"Generated {len(problems)} multilingual problems:")
        for i, problem in enumerate(problems):
            print(f"  {i+1}. {problem.id}")
            print(f"     Base language: {problem.base_language}")
            print(f"     Natural language: {problem.natural_language}")
            print(f"     Translations: {list(problem.translations.keys())}")
            print(f"     Cross-language pairs: {len(problem.cross_language_pairs)}")
        
        # Generate cross-language evaluation dataset
        print("\nGenerating cross-language evaluation dataset...")
        cross_lang_problems = ml_generator.generate_cross_language_evaluation_dataset(2)
        
        print(f"Generated {len(cross_lang_problems)} cross-language problems:")
        for i, problem in enumerate(cross_lang_problems):
            pairs = problem.cross_language_pairs[0] if problem.cross_language_pairs else ("unknown", "unknown")
            print(f"  {i+1}. {problem.id}: {pairs[0]} → {pairs[1]}")
        
        # Save multilingual datasets
        print("\nSaving multilingual datasets...")
        all_problems = problems + cross_lang_problems
        ml_generator.save_multilingual_datasets(all_problems, str(base_path))
        
        print("✅ Multilingual dataset generation completed successfully!")
        
    finally:
        # Cleanup
        shutil.rmtree(demo_dir)

def demo_dataset_validation():
    """Demonstrate dataset validation"""
    print("\n" + "="*60)
    print("DEMO: Dataset Validation")
    print("="*60)
    
    # Create temporary directory for demo
    demo_dir = Path(tempfile.mkdtemp(prefix="validation_demo_"))
    base_path = demo_dir / "lm_eval" / "tasks"
    base_path.mkdir(parents=True, exist_ok=True)
    
    try:
        # Create sample dataset
        sample_problems = [
            {
                "id": "demo_001",
                "title": "Demo problem 1",
                "language": "python",
                "scenario": "code_completion",
                "difficulty": "simple",
                "context_mode": "minimal_context",
                "prompt": "Complete this function to return the sum of two numbers",
                "reference": ["def add(a, b):\n    return a + b"],
                "tests": [{"type": "unit", "file": "test_demo_001.py", "cmd": "python -m pytest test_demo_001.py"}],
                "metadata": {
                    "time_limit_s": 10,
                    "memory_limit_mb": 100,
                    "author": "demo",
                    "license": "MIT"
                }
            },
            {
                "id": "demo_002",
                "title": "Demo problem 2",
                "language": "javascript",
                "scenario": "bug_fix",
                "difficulty": "intermediate",
                "context_mode": "full_context",
                "prompt": "Fix the bug in this function that should reverse a string",
                "reference": ["function reverseString(str) {\n    return str.split('').reverse().join('');\n}"],
                "tests": [{"type": "unit", "file": "test_demo_002.js", "cmd": "node test_demo_002.js"}],
                "metadata": {
                    "time_limit_s": 15,
                    "memory_limit_mb": 150,
                    "author": "demo",
                    "license": "MIT"
                }
            }
        ]
        
        # Save sample dataset
        sample_file = base_path / "demo_problems.jsonl"
        sample_file.parent.mkdir(parents=True, exist_ok=True)
        
        with open(sample_file, 'w') as f:
            for problem in sample_problems:
                f.write(json.dumps(problem) + '\n')
        
        # Initialize validator
        validator = DatasetValidator(str(base_path))
        
        # Run validation at different levels
        validation_levels = [ValidationLevel.BASIC, ValidationLevel.COMPREHENSIVE]
        
        for level in validation_levels:
            print(f"\nRunning {level.value} validation...")
            report = validator.validate_dataset(str(sample_file), level)
            
            print(f"  Dataset: {Path(report.dataset_path).name}")
            print(f"  Type: {report.dataset_type}")
            print(f"  Items: {report.total_items}")
            print(f"  Status: {report.overall_status.value}")
            print(f"  Quality Score: {report.quality_score:.1f}/100")
            
            # Show validation results
            passed = sum(1 for r in report.validation_results if r.status.value == "pass")
            failed = sum(1 for r in report.validation_results if r.status.value == "fail")
            warned = sum(1 for r in report.validation_results if r.status.value == "warn")
            
            print(f"  Results: {passed} passed, {warned} warnings, {failed} failed")
        
        print("✅ Dataset validation completed successfully!")
        
    finally:
        # Cleanup
        shutil.rmtree(demo_dir)

def demo_quality_assurance():
    """Demonstrate quality assurance"""
    print("\n" + "="*60)
    print("DEMO: Quality Assurance")
    print("="*60)
    
    # Create temporary directory for demo
    demo_dir = Path(tempfile.mkdtemp(prefix="qa_demo_"))
    base_path = demo_dir / "lm_eval" / "tasks"
    base_path.mkdir(parents=True, exist_ok=True)
    
    try:
        # Generate a small dataset for QA
        generator = DatasetGenerator(str(base_path))
        problems = generator.generate_single_turn_problems("algorithm_implementation", 3)
        generator.save_datasets(problems, None, str(base_path))
        
        # Find the generated dataset file
        dataset_file = next(base_path.rglob("*.jsonl"))
        
        # Initialize QA system
        qa_system = DatasetQualityAssurance(str(base_path))
        
        # Run quality assurance at different levels
        qa_levels = [QualityLevel.BASIC, QualityLevel.STANDARD]
        
        for level in qa_levels:
            print(f"\nRunning {level.value} quality assurance...")
            report = qa_system.run_quality_assurance(str(dataset_file), level)
            
            print(f"  Dataset: {Path(report.dataset_path).name}")
            print(f"  Items: {report.total_items}")
            print(f"  Overall Score: {report.overall_score:.1f}/100")
            print(f"  Quality Grade: {report.quality_grade}")
            print(f"  Production Ready: {'Yes' if report.production_ready else 'No'}")
            
            # Show quality check results by category
            categories = {}
            for check in report.quality_checks:
                if check.category not in categories:
                    categories[check.category] = {"pass": 0, "fail": 0, "skip": 0}
                categories[check.category][check.result.value] += 1
            
            print("  Quality Checks by Category:")
            for category, results in categories.items():
                total = sum(results.values())
                print(f"    {category.title()}: {results['pass']}/{total} passed")
        
        print("✅ Quality assurance completed successfully!")
        
    finally:
        # Cleanup
        shutil.rmtree(demo_dir)

def demo_complete_workflow():
    """Demonstrate complete dataset expansion workflow"""
    print("\n" + "="*60)
    print("DEMO: Complete Dataset Expansion Workflow")
    print("="*60)
    
    # Create temporary directory for demo
    demo_dir = Path(tempfile.mkdtemp(prefix="workflow_demo_"))
    base_path = demo_dir / "lm_eval" / "tasks"
    base_path.mkdir(parents=True, exist_ok=True)
    
    try:
        print("Step 1: Generate datasets...")
        
        # Initialize tools
        generator = DatasetGenerator(str(base_path))
        validator = DatasetValidator(str(base_path))
        qa_system = DatasetQualityAssurance(str(base_path))
        
        # Generate datasets
        scenarios = ["code_completion", "bug_fix"]
        all_problems = []
        
        for scenario in scenarios:
            problems = generator.generate_single_turn_problems(scenario, 3)
            all_problems.extend(problems)
            print(f"  Generated {len(problems)} problems for {scenario}")
        
        # Save datasets
        generator.save_datasets(all_problems, None, str(base_path))
        
        print(f"\nStep 2: Validate datasets...")
        
        # Validate all datasets
        reports = validator.validate_all_datasets(ValidationLevel.COMPREHENSIVE)
        
        print(f"  Validated {len(reports)} datasets:")
        for report in reports:
            dataset_name = Path(report.dataset_path).name
            print(f"    {dataset_name}: {report.overall_status.value} ({report.quality_score:.1f}/100)")
        
        print(f"\nStep 3: Run quality assurance...")
        
        # Run QA on all datasets
        qa_results = []
        for report in reports:
            qa_report = qa_system.run_quality_assurance(report.dataset_path, QualityLevel.STANDARD)
            qa_results.append(qa_report)
            
            dataset_name = Path(qa_report.dataset_path).name
            print(f"    {dataset_name}: Grade {qa_report.quality_grade} ({qa_report.overall_score:.1f}/100)")
        
        print(f"\nStep 4: Generate summary...")
        
        # Generate summary statistics
        total_items = sum(report.total_items for report in reports)
        avg_validation_score = sum(report.quality_score for report in reports) / len(reports)
        avg_qa_score = sum(report.overall_score for report in qa_results) / len(qa_results)
        production_ready = sum(1 for report in qa_results if report.production_ready)
        
        print(f"  Summary Statistics:")
        print(f"    Total datasets: {len(reports)}")
        print(f"    Total items: {total_items}")
        print(f"    Average validation score: {avg_validation_score:.1f}/100")
        print(f"    Average QA score: {avg_qa_score:.1f}/100")
        print(f"    Production ready: {production_ready}/{len(qa_results)}")
        
        # Grade distribution
        grades = [report.quality_grade for report in qa_results]
        grade_counts = {grade: grades.count(grade) for grade in set(grades)}
        print(f"    Grade distribution: {grade_counts}")
        
        print("✅ Complete workflow demonstration completed successfully!")
        
    finally:
        # Cleanup
        shutil.rmtree(demo_dir)

def main():
    """Main demo function"""
    print("Dataset Expansion Tools - Demonstration")
    print("This demo shows how to use the dataset expansion tools.")
    
    try:
        # Run all demos
        demo_basic_dataset_generation()
        demo_multilingual_generation()
        demo_dataset_validation()
        demo_quality_assurance()
        demo_complete_workflow()
        
        print("\n" + "="*60)
        print("🎉 ALL DEMOS COMPLETED SUCCESSFULLY!")
        print("="*60)
        print("\nNext steps:")
        print("1. Run the full dataset expansion: python scripts/expand_datasets.py")
        print("2. Validate your datasets: python scripts/dataset_validator.py")
        print("3. Check quality: python scripts/dataset_quality_assurance.py")
        print("4. Read the documentation: scripts/README_DATASET_EXPANSION.md")
        
    except Exception as e:
        print(f"\n❌ Demo failed with error: {e}")
        import traceback
        traceback.print_exc()
        return 1
    
    return 0

if __name__ == "__main__":
    exit(main())