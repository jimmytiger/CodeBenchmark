#!/usr/bin/env python3
"""
Test Script for Dataset Expansion Tools

This script tests all the dataset expansion tools to ensure they work correctly
before running the full expansion process.
"""

import json
import os
import sys
import tempfile
import shutil
from pathlib import Path
from typing import Dict, List, Any
import argparse
import logging
import unittest
from datetime import datetime

# Add scripts directory to path for imports
sys.path.append(str(Path(__file__).parent))

from dataset_generator import DatasetGenerator, SingleTurnProblem, MultiTurnScenario
from dataset_validator import DatasetValidator, ValidationLevel
from multilingual_dataset_generator import MultilingualDatasetGenerator
from dataset_quality_assurance import DatasetQualityAssurance, QualityLevel

# Configure logging
logging.basicConfig(level=logging.INFO, format='%(asctime)s - %(levelname)s - %(message)s')
logger = logging.getLogger(__name__)

class TestDatasetExpansionTools(unittest.TestCase):
    """Test suite for dataset expansion tools"""
    
    def setUp(self):
        """Set up test environment"""
        self.test_dir = Path(tempfile.mkdtemp(prefix="dataset_test_"))
        self.base_path = self.test_dir / "lm_eval" / "tasks"
        self.base_path.mkdir(parents=True, exist_ok=True)
        
        # Create test directory structure
        (self.base_path / "single_turn_scenarios").mkdir(exist_ok=True)
        (self.base_path / "multi_turn_scenarios").mkdir(exist_ok=True)
        
        # Initialize tools
        self.dataset_generator = DatasetGenerator(str(self.base_path))
        self.validator = DatasetValidator(str(self.base_path))
        self.multilingual_generator = MultilingualDatasetGenerator(str(self.base_path))
        self.qa_system = DatasetQualityAssurance(str(self.base_path))
        
        logger.info(f"Test environment created at: {self.test_dir}")
    
    def tearDown(self):
        """Clean up test environment"""
        if self.test_dir.exists():
            shutil.rmtree(self.test_dir)
        logger.info("Test environment cleaned up")
    
    def test_dataset_generator_single_turn(self):
        """Test single-turn dataset generation"""
        logger.info("Testing single-turn dataset generation")
        
        # Test generating problems for a scenario
        scenario = "code_completion"
        count = 5
        
        problems = self.dataset_generator.generate_single_turn_problems(scenario, count)
        
        # Assertions
        self.assertEqual(len(problems), count)
        self.assertIsInstance(problems[0], SingleTurnProblem)
        self.assertEqual(problems[0].scenario, scenario)
        self.assertIn(problems[0].difficulty, ["simple", "intermediate", "complex"])
        self.assertIn(problems[0].language, ["python", "javascript", "java", "cpp", "go", "rust", "typescript"])
        self.assertTrue(len(problems[0].prompt) > 0)
        self.assertTrue(len(problems[0].reference) > 0)
        self.assertTrue(len(problems[0].tests) > 0)
        
        logger.info("✅ Single-turn dataset generation test passed")
    
    def test_dataset_generator_multi_turn(self):
        """Test multi-turn dataset generation"""
        logger.info("Testing multi-turn dataset generation")
        
        # Test generating scenarios for a scenario type
        scenario = "code_review_process"
        count = 3
        
        scenarios = self.dataset_generator.generate_multi_turn_scenarios(scenario, count)
        
        # Assertions
        self.assertEqual(len(scenarios), count)
        self.assertIsInstance(scenarios[0], MultiTurnScenario)
        self.assertEqual(scenarios[0].scenario, scenario)
        self.assertIn(scenarios[0].difficulty, ["simple", "intermediate", "complex"])
        self.assertTrue(len(scenarios[0].turns) > 0)
        self.assertIsInstance(scenarios[0].success_metrics, dict)
        
        logger.info("✅ Multi-turn dataset generation test passed")
    
    def test_dataset_saving(self):
        """Test dataset saving functionality"""
        logger.info("Testing dataset saving")
        
        # Generate test data
        problems = self.dataset_generator.generate_single_turn_problems("function_generation", 2)
        scenarios = self.dataset_generator.generate_multi_turn_scenarios("debugging_session", 2)
        
        # Save datasets
        self.dataset_generator.save_datasets(problems, scenarios, str(self.base_path))
        
        # Check files were created
        function_gen_file = self.base_path / "single_turn_scenarios" / "function_generation" / "problems.jsonl"
        debug_file = self.base_path / "multi_turn_scenarios" / "debugging_session" / "scenarios.jsonl"
        
        self.assertTrue(function_gen_file.exists())
        self.assertTrue(debug_file.exists())
        
        # Check file contents
        with open(function_gen_file, 'r') as f:
            lines = f.readlines()
            self.assertEqual(len(lines), 2)
            
            # Validate JSON structure
            for line in lines:
                data = json.loads(line.strip())
                self.assertIn('id', data)
                self.assertIn('scenario', data)
                self.assertEqual(data['scenario'], 'function_generation')
        
        logger.info("✅ Dataset saving test passed")
    
    def test_dataset_validator(self):
        """Test dataset validation"""
        logger.info("Testing dataset validation")
        
        # Create a test dataset file
        test_problems = [
            {
                "id": "test_001",
                "title": "Test problem",
                "language": "python",
                "scenario": "code_completion",
                "difficulty": "simple",
                "context_mode": "minimal_context",
                "prompt": "Complete this function to return the sum of two numbers",
                "reference": ["def add(a, b):\n    return a + b"],
                "tests": [{"type": "unit", "file": "test_001.py", "cmd": "python -m pytest test_001.py"}],
                "metadata": {
                    "time_limit_s": 10,
                    "memory_limit_mb": 100,
                    "author": "test",
                    "license": "MIT"
                }
            }
        ]
        
        test_file = self.base_path / "test_problems.jsonl"
        with open(test_file, 'w') as f:
            for problem in test_problems:
                f.write(json.dumps(problem) + '\n')
        
        # Run validation
        report = self.validator.validate_dataset(str(test_file), ValidationLevel.BASIC)
        
        # Assertions
        self.assertEqual(report.total_items, 1)
        self.assertEqual(report.dataset_type, "single_turn")
        self.assertTrue(len(report.validation_results) > 0)
        
        logger.info("✅ Dataset validation test passed")
    
    def test_multilingual_generator(self):
        """Test multilingual dataset generation"""
        logger.info("Testing multilingual dataset generation")
        
        # Test multilingual problem generation
        scenario = "code_completion"
        count = 2
        target_languages = ["python", "javascript"]
        natural_languages = ["en", "zh"]
        
        problems = self.multilingual_generator.generate_multilingual_dataset(
            scenario, count, target_languages, natural_languages
        )
        
        # Assertions
        self.assertEqual(len(problems), count)
        self.assertIn(problems[0].base_language, target_languages)
        self.assertIn(problems[0].natural_language, natural_languages)
        self.assertTrue(len(problems[0].translations) > 0)
        self.assertIsInstance(problems[0].cross_language_pairs, list)
        
        logger.info("✅ Multilingual dataset generation test passed")
    
    def test_cross_language_evaluation(self):
        """Test cross-language evaluation dataset generation"""
        logger.info("Testing cross-language evaluation dataset generation")
        
        # Generate cross-language evaluation dataset
        count = 2
        problems = self.multilingual_generator.generate_cross_language_evaluation_dataset(count)
        
        # Assertions
        self.assertEqual(len(problems), count)
        self.assertEqual(problems[0].scenario, "code_translation")
        self.assertTrue(len(problems[0].cross_language_pairs) > 0)
        
        # Check that we have source and target language translations
        for problem in problems:
            self.assertTrue(len(problem.translations) >= 2)
        
        logger.info("✅ Cross-language evaluation test passed")
    
    def test_quality_assurance_basic(self):
        """Test basic quality assurance"""
        logger.info("Testing basic quality assurance")
        
        # Create a test dataset
        test_problems = [
            {
                "id": "qa_test_001",
                "title": "QA test problem",
                "language": "python",
                "scenario": "function_generation",
                "difficulty": "intermediate",
                "context_mode": "full_context",
                "prompt": "Write a function that implements binary search on a sorted array",
                "reference": ["def binary_search(arr, target):\n    left, right = 0, len(arr) - 1\n    while left <= right:\n        mid = (left + right) // 2\n        if arr[mid] == target:\n            return mid\n        elif arr[mid] < target:\n            left = mid + 1\n        else:\n            right = mid - 1\n    return -1"],
                "tests": [{"type": "unit", "file": "qa_test_001.py", "cmd": "python -m pytest qa_test_001.py"}],
                "metadata": {
                    "time_limit_s": 15,
                    "memory_limit_mb": 200,
                    "author": "qa_test",
                    "license": "MIT"
                }
            }
        ]
        
        test_file = self.base_path / "qa_test_problems.jsonl"
        with open(test_file, 'w') as f:
            for problem in test_problems:
                f.write(json.dumps(problem) + '\n')
        
        # Run quality assurance
        report = self.qa_system.run_quality_assurance(str(test_file), QualityLevel.BASIC)
        
        # Assertions
        self.assertEqual(report.total_items, 1)
        self.assertTrue(len(report.quality_checks) > 0)
        self.assertIsInstance(report.overall_score, float)
        self.assertIn(report.quality_grade, ["A", "B", "C", "D", "F"])
        
        logger.info("✅ Quality assurance test passed")
    
    def test_invalid_dataset_handling(self):
        """Test handling of invalid datasets"""
        logger.info("Testing invalid dataset handling")
        
        # Create an invalid dataset
        invalid_problems = [
            {
                "id": "invalid_001",
                # Missing required fields
                "prompt": "This is an invalid problem"
            }
        ]
        
        invalid_file = self.base_path / "invalid_problems.jsonl"
        with open(invalid_file, 'w') as f:
            for problem in invalid_problems:
                f.write(json.dumps(problem) + '\n')
        
        # Run validation - should detect issues
        report = self.validator.validate_dataset(str(invalid_file), ValidationLevel.BASIC)
        
        # Should have validation failures
        failed_checks = [check for check in report.validation_results if check.status.value == "fail"]
        self.assertTrue(len(failed_checks) > 0)
        
        logger.info("✅ Invalid dataset handling test passed")
    
    def test_empty_dataset_handling(self):
        """Test handling of empty datasets"""
        logger.info("Testing empty dataset handling")
        
        # Create an empty dataset file
        empty_file = self.base_path / "empty_problems.jsonl"
        empty_file.touch()
        
        # Run validation
        report = self.validator.validate_dataset(str(empty_file), ValidationLevel.BASIC)
        
        # Should detect empty dataset
        self.assertEqual(report.total_items, 0)
        empty_check = next((check for check in report.validation_results if "empty" in check.message.lower()), None)
        self.assertIsNotNone(empty_check)
        
        logger.info("✅ Empty dataset handling test passed")
    
    def test_file_not_found_handling(self):
        """Test handling of non-existent files"""
        logger.info("Testing file not found handling")
        
        non_existent_file = self.base_path / "does_not_exist.jsonl"
        
        # Run validation on non-existent file
        report = self.validator.validate_dataset(str(non_existent_file), ValidationLevel.BASIC)
        
        # Should handle gracefully
        self.assertEqual(report.overall_status.value, "fail")
        self.assertTrue(any("does not exist" in check.message for check in report.validation_results))
        
        logger.info("✅ File not found handling test passed")
    
    def test_language_support(self):
        """Test support for different programming languages"""
        logger.info("Testing programming language support")
        
        languages = ["python", "javascript", "java", "cpp", "go", "rust"]
        
        for language in languages:
            problems = self.dataset_generator.generate_single_turn_problems("algorithm_implementation", 1)
            
            # Check that problems can be generated for different languages
            self.assertTrue(len(problems) > 0)
            
            # The language selection is random, so we just check that it's valid
            self.assertIn(problems[0].language, languages + ["typescript", "sql", "shell"])
        
        logger.info("✅ Programming language support test passed")
    
    def test_difficulty_levels(self):
        """Test different difficulty levels"""
        logger.info("Testing difficulty levels")
        
        difficulties = ["simple", "intermediate", "complex"]
        
        for _ in range(10):  # Generate multiple problems to test randomness
            problems = self.dataset_generator.generate_single_turn_problems("bug_fix", 1)
            self.assertIn(problems[0].difficulty, difficulties)
        
        logger.info("✅ Difficulty levels test passed")
    
    def test_context_modes(self):
        """Test different context modes"""
        logger.info("Testing context modes")
        
        context_modes = ["no_context", "minimal_context", "full_context", "domain_context"]
        
        for _ in range(10):  # Generate multiple problems to test randomness
            problems = self.dataset_generator.generate_single_turn_problems("api_design", 1)
            self.assertIn(problems[0].context_mode, context_modes)
        
        logger.info("✅ Context modes test passed")

def run_integration_test():
    """Run integration test with actual dataset expansion"""
    logger.info("Running integration test")
    
    test_dir = Path(tempfile.mkdtemp(prefix="integration_test_"))
    base_path = test_dir / "lm_eval" / "tasks"
    base_path.mkdir(parents=True, exist_ok=True)
    
    try:
        # Initialize tools
        generator = DatasetGenerator(str(base_path))
        validator = DatasetValidator(str(base_path))
        qa_system = DatasetQualityAssurance(str(base_path))
        
        # Generate small datasets
        logger.info("Generating test datasets...")
        
        # Single-turn
        problems = generator.generate_single_turn_problems("code_completion", 5)
        generator.save_datasets(problems, None, str(base_path))
        
        # Multi-turn
        scenarios = generator.generate_multi_turn_scenarios("code_review_process", 3)
        generator.save_datasets(None, scenarios, str(base_path))
        
        # Validate datasets
        logger.info("Validating datasets...")
        reports = validator.validate_all_datasets(ValidationLevel.COMPREHENSIVE)
        
        # Run quality assurance
        logger.info("Running quality assurance...")
        for report in reports:
            qa_report = qa_system.run_quality_assurance(report.dataset_path, QualityLevel.STANDARD)
            logger.info(f"QA Score for {Path(report.dataset_path).name}: {qa_report.overall_score:.1f}/100")
        
        logger.info("✅ Integration test completed successfully")
        return True
        
    except Exception as e:
        logger.error(f"❌ Integration test failed: {e}")
        return False
        
    finally:
        # Cleanup
        if test_dir.exists():
            shutil.rmtree(test_dir)

def main():
    """Main function for running tests"""
    parser = argparse.ArgumentParser(description="Test dataset expansion tools")
    parser.add_argument("--integration", action="store_true", help="Run integration test")
    parser.add_argument("--verbose", action="store_true", help="Verbose output")
    
    args = parser.parse_args()
    
    if args.verbose:
        logging.getLogger().setLevel(logging.DEBUG)
    
    if args.integration:
        # Run integration test
        success = run_integration_test()
        exit(0 if success else 1)
    else:
        # Run unit tests
        unittest.main(argv=[''], exit=False, verbosity=2 if args.verbose else 1)

if __name__ == "__main__":
    main()