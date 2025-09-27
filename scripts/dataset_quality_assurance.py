#!/usr/bin/env python3
"""
Dataset Quality Assurance System for AI Evaluation Engine

This tool provides comprehensive quality assurance, integrity checking,
and automated testing for datasets to ensure production readiness.
"""

import json
import os
import re
import ast
import hashlib
import subprocess
import tempfile
from pathlib import Path
from typing import Dict, List, Any, Optional, Tuple, Set
import argparse
import logging
from dataclasses import dataclass, asdict
from enum import Enum
import concurrent.futures
from datetime import datetime

# Configure logging
logging.basicConfig(level=logging.INFO, format='%(asctime)s - %(levelname)s - %(message)s')
logger = logging.getLogger(__name__)

class QualityLevel(Enum):
    BASIC = "basic"
    STANDARD = "standard"
    PREMIUM = "premium"
    PRODUCTION = "production"

class TestResult(Enum):
    PASS = "pass"
    FAIL = "fail"
    SKIP = "skip"
    ERROR = "error"

@dataclass
class QualityCheck:
    """Individual quality check result"""
    check_name: str
    category: str
    result: TestResult
    score: float  # 0-100
    message: str
    details: Dict[str, Any] = None
    recommendations: List[str] = None
    execution_time: float = 0.0

@dataclass
class DatasetQualityReport:
    """Complete quality assurance report"""
    dataset_path: str
    dataset_type: str
    quality_level: str
    total_items: int
    quality_checks: List[QualityCheck]
    overall_score: float
    quality_grade: str  # A, B, C, D, F
    production_ready: bool
    timestamp: str
    execution_time: float

class DatasetQualityAssurance:
    """Main quality assurance system"""
    
    def __init__(self, base_path: str = "lm_eval/tasks"):
        self.base_path = Path(base_path)
        self.temp_dir = Path(tempfile.mkdtemp(prefix="dataset_qa_"))
        self.supported_languages = {
            "python": {"extension": "py", "runner": "python", "syntax_checker": self._check_python_syntax},
            "javascript": {"extension": "js", "runner": "node", "syntax_checker": self._check_javascript_syntax},
            "java": {"extension": "java", "runner": "java", "syntax_checker": self._check_java_syntax},
            "cpp": {"extension": "cpp", "runner": "g++", "syntax_checker": self._check_cpp_syntax},
            "go": {"extension": "go", "runner": "go", "syntax_checker": self._check_go_syntax},
            "rust": {"extension": "rs", "runner": "cargo", "syntax_checker": self._check_rust_syntax},
            "sql": {"extension": "sql", "runner": "sqlite3", "syntax_checker": self._check_sql_syntax}
        }
        
    def run_quality_assurance(self, dataset_path: str, quality_level: QualityLevel = QualityLevel.STANDARD) -> DatasetQualityReport:
        """Run comprehensive quality assurance on a dataset"""
        start_time = datetime.now()
        logger.info(f"Running quality assurance on: {dataset_path}")
        logger.info(f"Quality level: {quality_level.value}")
        
        dataset_path = Path(dataset_path)
        if not dataset_path.exists():
            return self._create_error_report(str(dataset_path), "Dataset file does not exist")
        
        # Load dataset
        items = self._load_dataset_items(dataset_path)
        dataset_type = self._determine_dataset_type(dataset_path)
        
        # Run quality checks based on level
        quality_checks = []
        
        if quality_level in [QualityLevel.BASIC, QualityLevel.STANDARD, QualityLevel.PREMIUM, QualityLevel.PRODUCTION]:
            quality_checks.extend(self._run_basic_quality_checks(items, dataset_type))
        
        if quality_level in [QualityLevel.STANDARD, QualityLevel.PREMIUM, QualityLevel.PRODUCTION]:
            quality_checks.extend(self._run_standard_quality_checks(items, dataset_type, dataset_path))
        
        if quality_level in [QualityLevel.PREMIUM, QualityLevel.PRODUCTION]:
            quality_checks.extend(self._run_premium_quality_checks(items, dataset_type, dataset_path))
        
        if quality_level == QualityLevel.PRODUCTION:
            quality_checks.extend(self._run_production_quality_checks(items, dataset_type, dataset_path))
        
        # Calculate overall metrics
        overall_score = self._calculate_overall_score(quality_checks)
        quality_grade = self._calculate_quality_grade(overall_score)
        production_ready = self._assess_production_readiness(quality_checks, overall_score)
        
        end_time = datetime.now()
        execution_time = (end_time - start_time).total_seconds()
        
        return DatasetQualityReport(
            dataset_path=str(dataset_path),
            dataset_type=dataset_type,
            quality_level=quality_level.value,
            total_items=len(items),
            quality_checks=quality_checks,
            overall_score=overall_score,
            quality_grade=quality_grade,
            production_ready=production_ready,
            timestamp=start_time.isoformat(),
            execution_time=execution_time
        )
    
    def _run_basic_quality_checks(self, items: List[Dict[str, Any]], dataset_type: str) -> List[QualityCheck]:
        """Run basic quality checks"""
        checks = []
        
        # Data completeness check
        checks.append(self._check_data_completeness(items, dataset_type))
        
        # Schema validation check
        checks.append(self._check_schema_validation(items, dataset_type))
        
        # ID uniqueness check
        checks.append(self._check_id_uniqueness(items))
        
        # Basic content validation
        checks.append(self._check_basic_content_validation(items, dataset_type))
        
        return checks
    
    def _run_standard_quality_checks(self, items: List[Dict[str, Any]], dataset_type: str, dataset_path: Path) -> List[QualityCheck]:
        """Run standard quality checks"""
        checks = []
        
        # Content quality assessment
        checks.append(self._check_content_quality(items, dataset_type))
        
        # Language distribution check
        checks.append(self._check_language_distribution(items))
        
        # Difficulty distribution check
        checks.append(self._check_difficulty_distribution(items))
        
        # Syntax validation for code content
        checks.append(self._check_syntax_validation(items, dataset_type))
        
        # Test case validation
        checks.append(self._check_test_case_validation(items, dataset_type))
        
        return checks
    
    def _run_premium_quality_checks(self, items: List[Dict[str, Any]], dataset_type: str, dataset_path: Path) -> List[QualityCheck]:
        """Run premium quality checks"""
        checks = []
        
        # Code execution validation
        checks.append(self._check_code_execution_validation(items, dataset_type))
        
        # Reference solution quality
        checks.append(self._check_reference_solution_quality(items, dataset_type))
        
        # Prompt engineering quality
        checks.append(self._check_prompt_engineering_quality(items, dataset_type))
        
        # Metadata completeness and accuracy
        checks.append(self._check_metadata_quality(items, dataset_type))
        
        # Cross-validation consistency
        checks.append(self._check_cross_validation_consistency(items, dataset_type))
        
        return checks
    
    def _run_production_quality_checks(self, items: List[Dict[str, Any]], dataset_type: str, dataset_path: Path) -> List[QualityCheck]:
        """Run production-level quality checks"""
        checks = []
        
        # Performance benchmarking
        checks.append(self._check_performance_benchmarking(items, dataset_type))
        
        # Security vulnerability assessment
        checks.append(self._check_security_vulnerabilities(items, dataset_type))
        
        # Scalability assessment
        checks.append(self._check_scalability_assessment(items, dataset_type))
        
        # Compliance validation
        checks.append(self._check_compliance_validation(items, dataset_type))
        
        # Production readiness assessment
        checks.append(self._check_production_readiness(items, dataset_type, dataset_path))
        
        return checks
    
    def _check_data_completeness(self, items: List[Dict[str, Any]], dataset_type: str) -> QualityCheck:
        """Check data completeness"""
        start_time = datetime.now()
        
        if not items:
            return QualityCheck(
                check_name="data_completeness",
                category="basic",
                result=TestResult.FAIL,
                score=0.0,
                message="Dataset is empty",
                recommendations=["Add dataset items", "Verify file format"],
                execution_time=(datetime.now() - start_time).total_seconds()
            )
        
        required_fields = self._get_required_fields(dataset_type)
        missing_data = []
        
        for i, item in enumerate(items):
            for field in required_fields:
                if field not in item or not item[field]:
                    missing_data.append(f"Item {i}: missing '{field}'")
        
        completeness_score = max(0, 100 - (len(missing_data) / len(items)) * 100)
        
        if missing_data:
            result = TestResult.FAIL if completeness_score < 50 else TestResult.PASS
            message = f"Data completeness: {completeness_score:.1f}% ({len(missing_data)} missing fields)"
        else:
            result = TestResult.PASS
            message = "All required fields are present"
        
        return QualityCheck(
            check_name="data_completeness",
            category="basic",
            result=result,
            score=completeness_score,
            message=message,
            details={"missing_fields": missing_data[:10]} if missing_data else None,
            recommendations=["Complete missing required fields", "Validate data integrity"] if missing_data else None,
            execution_time=(datetime.now() - start_time).total_seconds()
        )
    
    def _check_schema_validation(self, items: List[Dict[str, Any]], dataset_type: str) -> QualityCheck:
        """Check schema validation"""
        start_time = datetime.now()
        
        schema_errors = []
        valid_items = 0
        
        for i, item in enumerate(items):
            try:
                # Basic type checking
                if not isinstance(item, dict):
                    schema_errors.append(f"Item {i}: not a dictionary")
                    continue
                
                # Check required field types
                if dataset_type == "single_turn":
                    if 'reference' in item and not isinstance(item['reference'], list):
                        schema_errors.append(f"Item {i}: 'reference' must be a list")
                    if 'tests' in item and not isinstance(item['tests'], list):
                        schema_errors.append(f"Item {i}: 'tests' must be a list")
                elif dataset_type == "multi_turn":
                    if 'turns' in item and not isinstance(item['turns'], list):
                        schema_errors.append(f"Item {i}: 'turns' must be a list")
                    if 'success_metrics' in item and not isinstance(item['success_metrics'], dict):
                        schema_errors.append(f"Item {i}: 'success_metrics' must be a dictionary")
                
                if not schema_errors or len(schema_errors) == len([e for e in schema_errors if f"Item {i}:" not in e]):
                    valid_items += 1
                    
            except Exception as e:
                schema_errors.append(f"Item {i}: validation error - {e}")
        
        schema_score = (valid_items / len(items)) * 100 if items else 0
        
        if schema_errors:
            result = TestResult.FAIL if schema_score < 80 else TestResult.PASS
            message = f"Schema validation: {schema_score:.1f}% valid ({len(schema_errors)} errors)"
        else:
            result = TestResult.PASS
            message = "All items pass schema validation"
        
        return QualityCheck(
            check_name="schema_validation",
            category="basic",
            result=result,
            score=schema_score,
            message=message,
            details={"schema_errors": schema_errors[:10]} if schema_errors else None,
            recommendations=["Fix schema violations", "Validate data types"] if schema_errors else None,
            execution_time=(datetime.now() - start_time).total_seconds()
        )
    
    def _check_id_uniqueness(self, items: List[Dict[str, Any]]) -> QualityCheck:
        """Check ID uniqueness"""
        start_time = datetime.now()
        
        ids = [item.get('id') for item in items if item.get('id')]
        unique_ids = set(ids)
        duplicate_count = len(ids) - len(unique_ids)
        
        uniqueness_score = (len(unique_ids) / len(ids)) * 100 if ids else 100
        
        if duplicate_count > 0:
            result = TestResult.FAIL
            message = f"ID uniqueness: {uniqueness_score:.1f}% ({duplicate_count} duplicates)"
            recommendations = ["Ensure all IDs are unique", "Use UUID or sequential numbering"]
        else:
            result = TestResult.PASS
            message = "All IDs are unique"
            recommendations = None
        
        return QualityCheck(
            check_name="id_uniqueness",
            category="basic",
            result=result,
            score=uniqueness_score,
            message=message,
            details={"duplicate_count": duplicate_count} if duplicate_count > 0 else None,
            recommendations=recommendations,
            execution_time=(datetime.now() - start_time).total_seconds()
        )
    
    def _check_basic_content_validation(self, items: List[Dict[str, Any]], dataset_type: str) -> QualityCheck:
        """Check basic content validation"""
        start_time = datetime.now()
        
        content_issues = []
        valid_content = 0
        
        for i, item in enumerate(items):
            # Check prompt length and quality
            prompt = item.get('prompt', '')
            if not prompt:
                content_issues.append(f"Item {i}: empty prompt")
            elif len(prompt) < 20:
                content_issues.append(f"Item {i}: prompt too short ({len(prompt)} chars)")
            elif len(prompt) > 5000:
                content_issues.append(f"Item {i}: prompt too long ({len(prompt)} chars)")
            else:
                valid_content += 1
            
            # Check reference solutions for single-turn
            if dataset_type == "single_turn":
                references = item.get('reference', [])
                if not references:
                    content_issues.append(f"Item {i}: missing reference solution")
                elif any(not ref or len(str(ref)) < 10 for ref in references):
                    content_issues.append(f"Item {i}: reference solution too short")
        
        content_score = (valid_content / len(items)) * 100 if items else 0
        
        if content_issues:
            result = TestResult.FAIL if content_score < 70 else TestResult.PASS
            message = f"Content validation: {content_score:.1f}% valid ({len(content_issues)} issues)"
        else:
            result = TestResult.PASS
            message = "Basic content validation passed"
        
        return QualityCheck(
            check_name="basic_content_validation",
            category="basic",
            result=result,
            score=content_score,
            message=message,
            details={"content_issues": content_issues[:10]} if content_issues else None,
            recommendations=["Improve content quality", "Ensure adequate prompt length"] if content_issues else None,
            execution_time=(datetime.now() - start_time).total_seconds()
        )
    
    def _check_content_quality(self, items: List[Dict[str, Any]], dataset_type: str) -> QualityCheck:
        """Check content quality"""
        start_time = datetime.now()
        
        quality_issues = []
        quality_scores = []
        
        for i, item in enumerate(items):
            item_score = 100
            
            # Prompt quality assessment
            prompt = item.get('prompt', '')
            if prompt:
                # Check for clarity indicators
                clarity_indicators = ['implement', 'create', 'write', 'design', 'fix', 'complete']
                if not any(indicator in prompt.lower() for indicator in clarity_indicators):
                    quality_issues.append(f"Item {i}: prompt lacks clear action words")
                    item_score -= 10
                
                # Check for context
                if len(prompt.split()) < 10:
                    quality_issues.append(f"Item {i}: prompt lacks sufficient context")
                    item_score -= 15
                
                # Check for technical terms
                if dataset_type == "single_turn" and item.get('scenario') in ['algorithm_implementation', 'system_design']:
                    technical_terms = ['algorithm', 'data structure', 'complexity', 'performance', 'scalability']
                    if not any(term in prompt.lower() for term in technical_terms):
                        quality_issues.append(f"Item {i}: prompt lacks technical depth")
                        item_score -= 10
            
            quality_scores.append(max(0, item_score))
        
        avg_quality_score = sum(quality_scores) / len(quality_scores) if quality_scores else 0
        
        if quality_issues:
            result = TestResult.FAIL if avg_quality_score < 60 else TestResult.PASS
            message = f"Content quality: {avg_quality_score:.1f}% ({len(quality_issues)} issues)"
        else:
            result = TestResult.PASS
            message = "Content quality assessment passed"
        
        return QualityCheck(
            check_name="content_quality",
            category="standard",
            result=result,
            score=avg_quality_score,
            message=message,
            details={"quality_issues": quality_issues[:10]} if quality_issues else None,
            recommendations=["Improve prompt clarity", "Add technical depth"] if quality_issues else None,
            execution_time=(datetime.now() - start_time).total_seconds()
        )
    
    def _check_language_distribution(self, items: List[Dict[str, Any]]) -> QualityCheck:
        """Check programming language distribution"""
        start_time = datetime.now()
        
        languages = [item.get('language') for item in items if item.get('language')]
        language_counts = {lang: languages.count(lang) for lang in set(languages)}
        
        # Calculate distribution score
        if len(language_counts) == 0:
            distribution_score = 0
            result = TestResult.FAIL
            message = "No programming languages specified"
        elif len(language_counts) == 1:
            distribution_score = 30
            result = TestResult.FAIL
            message = f"Only one language: {list(language_counts.keys())[0]}"
        elif len(language_counts) < 3:
            distribution_score = 60
            result = TestResult.PASS
            message = f"Limited diversity: {len(language_counts)} languages"
        else:
            distribution_score = 90
            result = TestResult.PASS
            message = f"Good diversity: {len(language_counts)} languages"
        
        return QualityCheck(
            check_name="language_distribution",
            category="standard",
            result=result,
            score=distribution_score,
            message=message,
            details={"language_distribution": language_counts},
            recommendations=["Add more programming languages", "Balance language distribution"] if distribution_score < 80 else None,
            execution_time=(datetime.now() - start_time).total_seconds()
        )
    
    def _check_difficulty_distribution(self, items: List[Dict[str, Any]]) -> QualityCheck:
        """Check difficulty level distribution"""
        start_time = datetime.now()
        
        difficulties = [item.get('difficulty') for item in items if item.get('difficulty')]
        difficulty_counts = {diff: difficulties.count(diff) for diff in set(difficulties)}
        
        expected_difficulties = {"simple", "intermediate", "complex"}
        present_difficulties = set(difficulty_counts.keys())
        missing_difficulties = expected_difficulties - present_difficulties
        
        if not difficulties:
            distribution_score = 0
            result = TestResult.FAIL
            message = "No difficulty levels specified"
        elif missing_difficulties:
            distribution_score = 50
            result = TestResult.FAIL
            message = f"Missing difficulties: {missing_difficulties}"
        else:
            # Check balance
            total = len(difficulties)
            balance_score = 100
            for diff, count in difficulty_counts.items():
                ratio = count / total
                if ratio < 0.2 or ratio > 0.6:  # Should be between 20% and 60%
                    balance_score -= 20
            
            distribution_score = max(70, balance_score)
            result = TestResult.PASS
            message = f"All difficulties present, balance score: {balance_score:.1f}%"
        
        return QualityCheck(
            check_name="difficulty_distribution",
            category="standard",
            result=result,
            score=distribution_score,
            message=message,
            details={"difficulty_distribution": difficulty_counts},
            recommendations=["Add missing difficulty levels", "Balance difficulty distribution"] if distribution_score < 80 else None,
            execution_time=(datetime.now() - start_time).total_seconds()
        )
    
    def _check_syntax_validation(self, items: List[Dict[str, Any]], dataset_type: str) -> QualityCheck:
        """Check syntax validation for code content"""
        start_time = datetime.now()
        
        syntax_errors = []
        valid_syntax_count = 0
        total_code_items = 0
        
        for i, item in enumerate(items):
            language = item.get('language')
            if not language or language not in self.supported_languages:
                continue
            
            # Check reference code syntax for single-turn
            if dataset_type == "single_turn":
                references = item.get('reference', [])
                for j, ref in enumerate(references):
                    if isinstance(ref, str) and ref.strip():
                        total_code_items += 1
                        syntax_checker = self.supported_languages[language]['syntax_checker']
                        is_valid, error_msg = syntax_checker(ref)
                        
                        if is_valid:
                            valid_syntax_count += 1
                        else:
                            syntax_errors.append(f"Item {i}, reference {j}: {error_msg}")
        
        if total_code_items == 0:
            syntax_score = 100  # No code to validate
            result = TestResult.SKIP
            message = "No code content to validate"
        else:
            syntax_score = (valid_syntax_count / total_code_items) * 100
            if syntax_errors:
                result = TestResult.FAIL if syntax_score < 80 else TestResult.PASS
                message = f"Syntax validation: {syntax_score:.1f}% valid ({len(syntax_errors)} errors)"
            else:
                result = TestResult.PASS
                message = "All code passes syntax validation"
        
        return QualityCheck(
            check_name="syntax_validation",
            category="standard",
            result=result,
            score=syntax_score,
            message=message,
            details={"syntax_errors": syntax_errors[:10]} if syntax_errors else None,
            recommendations=["Fix syntax errors", "Validate code before adding to dataset"] if syntax_errors else None,
            execution_time=(datetime.now() - start_time).total_seconds()
        )
    
    def _check_test_case_validation(self, items: List[Dict[str, Any]], dataset_type: str) -> QualityCheck:
        """Check test case validation"""
        start_time = datetime.now()
        
        test_issues = []
        valid_tests = 0
        total_items_with_tests = 0
        
        for i, item in enumerate(items):
            tests = item.get('tests', [])
            if tests:
                total_items_with_tests += 1
                item_valid = True
                
                for j, test in enumerate(tests):
                    if not isinstance(test, dict):
                        test_issues.append(f"Item {i}, test {j}: not a dictionary")
                        item_valid = False
                        continue
                    
                    required_test_fields = ['type', 'file', 'cmd']
                    for field in required_test_fields:
                        if field not in test:
                            test_issues.append(f"Item {i}, test {j}: missing '{field}'")
                            item_valid = False
                    
                    # Validate test type
                    valid_test_types = ['unit', 'integration', 'performance', 'security', 'e2e']
                    if test.get('type') not in valid_test_types:
                        test_issues.append(f"Item {i}, test {j}: invalid test type '{test.get('type')}'")
                        item_valid = False
                
                if item_valid:
                    valid_tests += 1
        
        if total_items_with_tests == 0:
            test_score = 0
            result = TestResult.FAIL
            message = "No test cases defined"
        else:
            test_score = (valid_tests / total_items_with_tests) * 100
            if test_issues:
                result = TestResult.FAIL if test_score < 70 else TestResult.PASS
                message = f"Test validation: {test_score:.1f}% valid ({len(test_issues)} issues)"
            else:
                result = TestResult.PASS
                message = "All test cases are valid"
        
        return QualityCheck(
            check_name="test_case_validation",
            category="standard",
            result=result,
            score=test_score,
            message=message,
            details={"test_issues": test_issues[:10]} if test_issues else None,
            recommendations=["Add test cases for all items", "Fix test case format"] if test_issues else None,
            execution_time=(datetime.now() - start_time).total_seconds()
        )
    
    # Syntax checkers for different languages
    def _check_python_syntax(self, code: str) -> Tuple[bool, str]:
        """Check Python syntax"""
        try:
            ast.parse(code)
            return True, ""
        except SyntaxError as e:
            return False, f"Python syntax error: {e}"
        except Exception as e:
            return False, f"Python validation error: {e}"
    
    def _check_javascript_syntax(self, code: str) -> Tuple[bool, str]:
        """Check JavaScript syntax"""
        try:
            # Simple JavaScript syntax check using node
            with tempfile.NamedTemporaryFile(mode='w', suffix='.js', delete=False) as f:
                f.write(code)
                f.flush()
                
                result = subprocess.run(['node', '--check', f.name], 
                                      capture_output=True, text=True, timeout=5)
                os.unlink(f.name)
                
                if result.returncode == 0:
                    return True, ""
                else:
                    return False, f"JavaScript syntax error: {result.stderr}"
        except subprocess.TimeoutExpired:
            return False, "JavaScript syntax check timeout"
        except Exception as e:
            return False, f"JavaScript validation error: {e}"
    
    def _check_java_syntax(self, code: str) -> Tuple[bool, str]:
        """Check Java syntax"""
        try:
            # Extract class name from code
            class_match = re.search(r'class\s+(\w+)', code)
            if not class_match:
                return False, "No class definition found"
            
            class_name = class_match.group(1)
            
            with tempfile.NamedTemporaryFile(mode='w', suffix='.java', delete=False) as f:
                f.write(code)
                f.flush()
                
                # Rename file to match class name
                java_file = f.name.replace('.java', f'_{class_name}.java')
                os.rename(f.name, java_file)
                
                result = subprocess.run(['javac', java_file], 
                                      capture_output=True, text=True, timeout=10)
                
                # Cleanup
                os.unlink(java_file)
                class_file = java_file.replace('.java', '.class')
                if os.path.exists(class_file):
                    os.unlink(class_file)
                
                if result.returncode == 0:
                    return True, ""
                else:
                    return False, f"Java syntax error: {result.stderr}"
        except subprocess.TimeoutExpired:
            return False, "Java syntax check timeout"
        except Exception as e:
            return False, f"Java validation error: {e}"
    
    def _check_cpp_syntax(self, code: str) -> Tuple[bool, str]:
        """Check C++ syntax"""
        try:
            with tempfile.NamedTemporaryFile(mode='w', suffix='.cpp', delete=False) as f:
                f.write(code)
                f.flush()
                
                result = subprocess.run(['g++', '-fsyntax-only', f.name], 
                                      capture_output=True, text=True, timeout=10)
                os.unlink(f.name)
                
                if result.returncode == 0:
                    return True, ""
                else:
                    return False, f"C++ syntax error: {result.stderr}"
        except subprocess.TimeoutExpired:
            return False, "C++ syntax check timeout"
        except Exception as e:
            return False, f"C++ validation error: {e}"
    
    def _check_go_syntax(self, code: str) -> Tuple[bool, str]:
        """Check Go syntax"""
        try:
            with tempfile.NamedTemporaryFile(mode='w', suffix='.go', delete=False) as f:
                f.write(code)
                f.flush()
                
                result = subprocess.run(['go', 'fmt', f.name], 
                                      capture_output=True, text=True, timeout=5)
                os.unlink(f.name)
                
                if result.returncode == 0:
                    return True, ""
                else:
                    return False, f"Go syntax error: {result.stderr}"
        except subprocess.TimeoutExpired:
            return False, "Go syntax check timeout"
        except Exception as e:
            return False, f"Go validation error: {e}"
    
    def _check_rust_syntax(self, code: str) -> Tuple[bool, str]:
        """Check Rust syntax"""
        # Simplified Rust syntax check
        return True, ""  # Would need rustc for proper validation
    
    def _check_sql_syntax(self, code: str) -> Tuple[bool, str]:
        """Check SQL syntax"""
        # Basic SQL syntax validation
        sql_keywords = ['SELECT', 'INSERT', 'UPDATE', 'DELETE', 'CREATE', 'DROP', 'ALTER']
        if any(keyword in code.upper() for keyword in sql_keywords):
            return True, ""
        else:
            return False, "No valid SQL keywords found"
    
    # Placeholder methods for premium and production checks
    def _check_code_execution_validation(self, items: List[Dict[str, Any]], dataset_type: str) -> QualityCheck:
        """Check code execution validation"""
        return QualityCheck(
            check_name="code_execution_validation",
            category="premium",
            result=TestResult.SKIP,
            score=100.0,
            message="Code execution validation not implemented",
            execution_time=0.0
        )
    
    def _check_reference_solution_quality(self, items: List[Dict[str, Any]], dataset_type: str) -> QualityCheck:
        """Check reference solution quality"""
        return QualityCheck(
            check_name="reference_solution_quality",
            category="premium",
            result=TestResult.SKIP,
            score=100.0,
            message="Reference solution quality check not implemented",
            execution_time=0.0
        )
    
    def _check_prompt_engineering_quality(self, items: List[Dict[str, Any]], dataset_type: str) -> QualityCheck:
        """Check prompt engineering quality"""
        return QualityCheck(
            check_name="prompt_engineering_quality",
            category="premium",
            result=TestResult.SKIP,
            score=100.0,
            message="Prompt engineering quality check not implemented",
            execution_time=0.0
        )
    
    def _check_metadata_quality(self, items: List[Dict[str, Any]], dataset_type: str) -> QualityCheck:
        """Check metadata quality"""
        return QualityCheck(
            check_name="metadata_quality",
            category="premium",
            result=TestResult.SKIP,
            score=100.0,
            message="Metadata quality check not implemented",
            execution_time=0.0
        )
    
    def _check_cross_validation_consistency(self, items: List[Dict[str, Any]], dataset_type: str) -> QualityCheck:
        """Check cross-validation consistency"""
        return QualityCheck(
            check_name="cross_validation_consistency",
            category="premium",
            result=TestResult.SKIP,
            score=100.0,
            message="Cross-validation consistency check not implemented",
            execution_time=0.0
        )
    
    def _check_performance_benchmarking(self, items: List[Dict[str, Any]], dataset_type: str) -> QualityCheck:
        """Check performance benchmarking"""
        return QualityCheck(
            check_name="performance_benchmarking",
            category="production",
            result=TestResult.SKIP,
            score=100.0,
            message="Performance benchmarking not implemented",
            execution_time=0.0
        )
    
    def _check_security_vulnerabilities(self, items: List[Dict[str, Any]], dataset_type: str) -> QualityCheck:
        """Check security vulnerabilities"""
        return QualityCheck(
            check_name="security_vulnerabilities",
            category="production",
            result=TestResult.SKIP,
            score=100.0,
            message="Security vulnerability check not implemented",
            execution_time=0.0
        )
    
    def _check_scalability_assessment(self, items: List[Dict[str, Any]], dataset_type: str) -> QualityCheck:
        """Check scalability assessment"""
        return QualityCheck(
            check_name="scalability_assessment",
            category="production",
            result=TestResult.SKIP,
            score=100.0,
            message="Scalability assessment not implemented",
            execution_time=0.0
        )
    
    def _check_compliance_validation(self, items: List[Dict[str, Any]], dataset_type: str) -> QualityCheck:
        """Check compliance validation"""
        return QualityCheck(
            check_name="compliance_validation",
            category="production",
            result=TestResult.SKIP,
            score=100.0,
            message="Compliance validation not implemented",
            execution_time=0.0
        )
    
    def _check_production_readiness(self, items: List[Dict[str, Any]], dataset_type: str, dataset_path: Path) -> QualityCheck:
        """Check production readiness"""
        start_time = datetime.now()
        
        readiness_score = 100
        readiness_issues = []
        
        # Check dataset size
        min_production_size = 100
        if len(items) < min_production_size:
            readiness_score -= 30
            readiness_issues.append(f"Dataset too small: {len(items)} < {min_production_size}")
        
        # Check metadata completeness
        items_with_complete_metadata = 0
        for item in items:
            metadata = item.get('metadata', {})
            required_metadata = ['author', 'license', 'time_limit_s', 'memory_limit_mb']
            if all(field in metadata for field in required_metadata):
                items_with_complete_metadata += 1
        
        metadata_completeness = (items_with_complete_metadata / len(items)) * 100 if items else 0
        if metadata_completeness < 90:
            readiness_score -= 20
            readiness_issues.append(f"Incomplete metadata: {metadata_completeness:.1f}% complete")
        
        # Check test coverage
        items_with_tests = sum(1 for item in items if item.get('tests'))
        test_coverage = (items_with_tests / len(items)) * 100 if items else 0
        if test_coverage < 95:
            readiness_score -= 25
            readiness_issues.append(f"Low test coverage: {test_coverage:.1f}%")
        
        readiness_score = max(0, readiness_score)
        
        if readiness_issues:
            result = TestResult.FAIL if readiness_score < 70 else TestResult.PASS
            message = f"Production readiness: {readiness_score:.1f}% ({len(readiness_issues)} issues)"
        else:
            result = TestResult.PASS
            message = "Dataset is production ready"
        
        return QualityCheck(
            check_name="production_readiness",
            category="production",
            result=result,
            score=readiness_score,
            message=message,
            details={"readiness_issues": readiness_issues} if readiness_issues else None,
            recommendations=["Address production readiness issues", "Expand dataset size", "Complete metadata"] if readiness_issues else None,
            execution_time=(datetime.now() - start_time).total_seconds()
        )
    
    # Utility methods
    def _load_dataset_items(self, dataset_path: Path) -> List[Dict[str, Any]]:
        """Load dataset items from file"""
        items = []
        try:
            with open(dataset_path, 'r', encoding='utf-8') as f:
                for line in f:
                    line = line.strip()
                    if line:
                        items.append(json.loads(line))
        except Exception as e:
            logger.error(f"Error loading dataset {dataset_path}: {e}")
        return items
    
    def _determine_dataset_type(self, dataset_path: Path) -> str:
        """Determine dataset type"""
        if "single_turn" in str(dataset_path) or "problems.jsonl" in dataset_path.name:
            return "single_turn"
        elif "multi_turn" in str(dataset_path) or "scenarios.jsonl" in dataset_path.name:
            return "multi_turn"
        else:
            return "unknown"
    
    def _get_required_fields(self, dataset_type: str) -> List[str]:
        """Get required fields for dataset type"""
        if dataset_type == "single_turn":
            return ['id', 'title', 'language', 'scenario', 'difficulty', 'context_mode', 'prompt', 'reference', 'tests', 'metadata']
        elif dataset_type == "multi_turn":
            return ['id', 'scenario', 'difficulty', 'language', 'context_mode', 'turns', 'success_metrics', 'metadata']
        else:
            return ['id']
    
    def _calculate_overall_score(self, quality_checks: List[QualityCheck]) -> float:
        """Calculate overall quality score"""
        if not quality_checks:
            return 0.0
        
        # Weight different categories
        category_weights = {
            "basic": 0.4,
            "standard": 0.3,
            "premium": 0.2,
            "production": 0.1
        }
        
        weighted_scores = []
        for check in quality_checks:
            if check.result != TestResult.SKIP:
                weight = category_weights.get(check.category, 0.1)
                weighted_scores.append(check.score * weight)
        
        return sum(weighted_scores) / sum(category_weights.values()) if weighted_scores else 0.0
    
    def _calculate_quality_grade(self, score: float) -> str:
        """Calculate quality grade based on score"""
        if score >= 90:
            return "A"
        elif score >= 80:
            return "B"
        elif score >= 70:
            return "C"
        elif score >= 60:
            return "D"
        else:
            return "F"
    
    def _assess_production_readiness(self, quality_checks: List[QualityCheck], overall_score: float) -> bool:
        """Assess if dataset is production ready"""
        # Must have no failed basic checks
        basic_failures = [check for check in quality_checks 
                         if check.category == "basic" and check.result == TestResult.FAIL]
        
        if basic_failures:
            return False
        
        # Must have overall score >= 80
        if overall_score < 80:
            return False
        
        # Must pass production readiness check if present
        production_checks = [check for check in quality_checks 
                           if check.check_name == "production_readiness"]
        
        if production_checks and production_checks[0].result == TestResult.FAIL:
            return False
        
        return True
    
    def _create_error_report(self, dataset_path: str, error_message: str) -> DatasetQualityReport:
        """Create error report for failed validation"""
        return DatasetQualityReport(
            dataset_path=dataset_path,
            dataset_type="unknown",
            quality_level="unknown",
            total_items=0,
            quality_checks=[QualityCheck(
                check_name="file_access",
                category="basic",
                result=TestResult.FAIL,
                score=0.0,
                message=error_message,
                execution_time=0.0
            )],
            overall_score=0.0,
            quality_grade="F",
            production_ready=False,
            timestamp=datetime.now().isoformat(),
            execution_time=0.0
        )
    
    def generate_quality_report(self, report: DatasetQualityReport, output_file: str = None) -> str:
        """Generate comprehensive quality report"""
        report_lines = []
        report_lines.append("# Dataset Quality Assurance Report")
        report_lines.append(f"Generated: {report.timestamp}")
        report_lines.append("")
        
        # Summary
        report_lines.append("## Summary")
        report_lines.append(f"- Dataset: {report.dataset_path}")
        report_lines.append(f"- Type: {report.dataset_type}")
        report_lines.append(f"- Items: {report.total_items}")
        report_lines.append(f"- Quality Level: {report.quality_level}")
        report_lines.append(f"- Overall Score: {report.overall_score:.1f}/100")
        report_lines.append(f"- Quality Grade: {report.quality_grade}")
        report_lines.append(f"- Production Ready: {'Yes' if report.production_ready else 'No'}")
        report_lines.append(f"- Execution Time: {report.execution_time:.2f}s")
        report_lines.append("")
        
        # Quality checks
        report_lines.append("## Quality Checks")
        report_lines.append("")
        
        categories = {}
        for check in report.quality_checks:
            if check.category not in categories:
                categories[check.category] = []
            categories[check.category].append(check)
        
        for category, checks in categories.items():
            report_lines.append(f"### {category.title()} Checks")
            report_lines.append("")
            
            for check in checks:
                status_icon = {"pass": "✅", "fail": "❌", "skip": "⏭️", "error": "🔥"}[check.result.value]
                report_lines.append(f"  {status_icon} **{check.check_name}**: {check.message} (Score: {check.score:.1f}/100)")
                
                if check.recommendations:
                    report_lines.append("    - Recommendations:")
                    for rec in check.recommendations:
                        report_lines.append(f"      - {rec}")
                
                report_lines.append("")
        
        # Recommendations
        report_lines.append("## Overall Recommendations")
        report_lines.append("")
        
        if not report.production_ready:
            report_lines.append("### Critical Issues")
            failed_checks = [check for check in report.quality_checks if check.result == TestResult.FAIL]
            for check in failed_checks:
                report_lines.append(f"- Fix {check.check_name}: {check.message}")
            report_lines.append("")
        
        if report.quality_grade in ["C", "D", "F"]:
            report_lines.append("### Quality Improvements")
            report_lines.append("- Address failing quality checks")
            report_lines.append("- Improve content quality and completeness")
            report_lines.append("- Add comprehensive test coverage")
            report_lines.append("")
        
        report_content = "\n".join(report_lines)
        
        if output_file:
            with open(output_file, 'w') as f:
                f.write(report_content)
            logger.info(f"Quality report saved to: {output_file}")
        
        return report_content

def main():
    """Main function for command-line usage"""
    parser = argparse.ArgumentParser(description="Run quality assurance on datasets")
    parser.add_argument("--dataset", type=str, required=True, help="Dataset file to validate")
    parser.add_argument("--level", choices=["basic", "standard", "premium", "production"], 
                       default="standard", help="Quality assurance level")
    parser.add_argument("--output", type=str, help="Output file for quality report")
    parser.add_argument("--format", choices=["text", "json"], default="text", help="Output format")
    parser.add_argument("--base-path", type=str, default="lm_eval/tasks", help="Base path for task directories")
    
    args = parser.parse_args()
    
    qa_system = DatasetQualityAssurance(args.base_path)
    quality_level = QualityLevel(args.level)
    
    # Run quality assurance
    report = qa_system.run_quality_assurance(args.dataset, quality_level)
    
    # Generate report
    if args.format == "json":
        report_content = json.dumps(asdict(report), indent=2)
        
        if args.output:
            with open(args.output, 'w') as f:
                f.write(report_content)
        else:
            print(report_content)
    else:
        report_content = qa_system.generate_quality_report(report, args.output)
        
        if not args.output:
            print(report_content)
    
    # Exit with appropriate code
    if not report.production_ready:
        logger.error("Dataset is not production ready")
        exit(1)
    else:
        logger.info("Dataset passed quality assurance")
        exit(0)

if __name__ == "__main__":
    main()