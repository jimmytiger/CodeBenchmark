#!/usr/bin/env python3
"""
Dataset Validation Tool for AI Evaluation Engine

This tool validates dataset quality, integrity, and completeness for both
single-turn and multi-turn scenarios, ensuring production readiness.
"""

import json
import os
import re
import hashlib
from pathlib import Path
from typing import Dict, List, Any, Optional, Tuple, Set
import argparse
import logging
from dataclasses import dataclass, asdict
from enum import Enum
import jsonschema
from jsonschema import validate, ValidationError
import yaml

# Configure logging
logging.basicConfig(level=logging.INFO, format='%(asctime)s - %(levelname)s - %(message)s')
logger = logging.getLogger(__name__)

class ValidationLevel(Enum):
    BASIC = "basic"
    COMPREHENSIVE = "comprehensive"
    PRODUCTION = "production"

class ValidationStatus(Enum):
    PASS = "pass"
    WARN = "warn"
    FAIL = "fail"

@dataclass
class ValidationResult:
    """Result of a validation check"""
    check_name: str
    status: ValidationStatus
    message: str
    details: Dict[str, Any] = None
    suggestions: List[str] = None

@dataclass
class DatasetValidationReport:
    """Complete validation report for a dataset"""
    dataset_path: str
    dataset_type: str
    total_items: int
    validation_results: List[ValidationResult]
    overall_status: ValidationStatus
    quality_score: float
    timestamp: str

class DatasetValidator:
    """Main dataset validation class"""
    
    def __init__(self, base_path: str = "lm_eval/tasks"):
        self.base_path = Path(base_path)
        self.single_turn_schema = self._load_single_turn_schema()
        self.multi_turn_schema = self._load_multi_turn_schema()
        self.language_extensions = {
            "python": [".py"], "javascript": [".js"], "java": [".java"],
            "cpp": [".cpp", ".cc", ".cxx"], "go": [".go"], "rust": [".rs"],
            "typescript": [".ts"], "sql": [".sql"], "shell": [".sh", ".bash"]
        }
        
    def validate_dataset(self, dataset_path: str, validation_level: ValidationLevel = ValidationLevel.COMPREHENSIVE) -> DatasetValidationReport:
        """Validate a complete dataset"""
        logger.info(f"Validating dataset: {dataset_path}")
        
        dataset_path = Path(dataset_path)
        if not dataset_path.exists():
            return DatasetValidationReport(
                dataset_path=str(dataset_path),
                dataset_type="unknown",
                total_items=0,
                validation_results=[ValidationResult("file_exists", ValidationStatus.FAIL, "Dataset file does not exist")],
                overall_status=ValidationStatus.FAIL,
                quality_score=0.0,
                timestamp=self._get_timestamp()
            )
        
        # Determine dataset type
        dataset_type = self._determine_dataset_type(dataset_path)
        
        # Load dataset
        items = self._load_dataset_items(dataset_path)
        
        # Run validation checks
        validation_results = []
        
        if validation_level in [ValidationLevel.BASIC, ValidationLevel.COMPREHENSIVE, ValidationLevel.PRODUCTION]:
            validation_results.extend(self._run_basic_validation(items, dataset_type))
        
        if validation_level in [ValidationLevel.COMPREHENSIVE, ValidationLevel.PRODUCTION]:
            validation_results.extend(self._run_comprehensive_validation(items, dataset_type, dataset_path))
        
        if validation_level == ValidationLevel.PRODUCTION:
            validation_results.extend(self._run_production_validation(items, dataset_type, dataset_path))
        
        # Calculate overall status and quality score
        overall_status, quality_score = self._calculate_overall_metrics(validation_results)
        
        return DatasetValidationReport(
            dataset_path=str(dataset_path),
            dataset_type=dataset_type,
            total_items=len(items),
            validation_results=validation_results,
            overall_status=overall_status,
            quality_score=quality_score,
            timestamp=self._get_timestamp()
        )
    
    def validate_all_datasets(self, validation_level: ValidationLevel = ValidationLevel.COMPREHENSIVE) -> List[DatasetValidationReport]:
        """Validate all datasets in the task directory"""
        logger.info("Validating all datasets")
        
        reports = []
        
        # Find all dataset files
        dataset_files = []
        dataset_files.extend(self.base_path.glob("single_turn_scenarios/**/*.jsonl"))
        dataset_files.extend(self.base_path.glob("multi_turn_scenarios/**/*.jsonl"))
        dataset_files.extend(self.base_path.glob("**/*problems.jsonl"))
        dataset_files.extend(self.base_path.glob("**/*scenarios.jsonl"))
        
        for dataset_file in dataset_files:
            try:
                report = self.validate_dataset(dataset_file, validation_level)
                reports.append(report)
            except Exception as e:
                logger.error(f"Error validating {dataset_file}: {e}")
                reports.append(DatasetValidationReport(
                    dataset_path=str(dataset_file),
                    dataset_type="unknown",
                    total_items=0,
                    validation_results=[ValidationResult("validation_error", ValidationStatus.FAIL, f"Validation error: {e}")],
                    overall_status=ValidationStatus.FAIL,
                    quality_score=0.0,
                    timestamp=self._get_timestamp()
                ))
        
        return reports
    
    def _determine_dataset_type(self, dataset_path: Path) -> str:
        """Determine if dataset is single-turn or multi-turn"""
        if "single_turn" in str(dataset_path) or "problems.jsonl" in dataset_path.name:
            return "single_turn"
        elif "multi_turn" in str(dataset_path) or "scenarios.jsonl" in dataset_path.name:
            return "multi_turn"
        else:
            return "unknown"
    
    def _load_dataset_items(self, dataset_path: Path) -> List[Dict[str, Any]]:
        """Load dataset items from JSONL file"""
        items = []
        try:
            with open(dataset_path, 'r', encoding='utf-8') as f:
                for line_num, line in enumerate(f, 1):
                    line = line.strip()
                    if line:
                        try:
                            item = json.loads(line)
                            items.append(item)
                        except json.JSONDecodeError as e:
                            logger.warning(f"Invalid JSON on line {line_num} in {dataset_path}: {e}")
        except Exception as e:
            logger.error(f"Error loading dataset {dataset_path}: {e}")
        
        return items
    
    def _run_basic_validation(self, items: List[Dict[str, Any]], dataset_type: str) -> List[ValidationResult]:
        """Run basic validation checks"""
        results = []
        
        # Check if dataset is not empty
        if not items:
            results.append(ValidationResult(
                "dataset_not_empty",
                ValidationStatus.FAIL,
                "Dataset is empty",
                suggestions=["Add dataset items", "Check file format"]
            ))
            return results
        
        results.append(ValidationResult(
            "dataset_not_empty",
            ValidationStatus.PASS,
            f"Dataset contains {len(items)} items"
        ))
        
        # Schema validation
        schema = self.single_turn_schema if dataset_type == "single_turn" else self.multi_turn_schema
        schema_errors = []
        
        for i, item in enumerate(items):
            try:
                validate(instance=item, schema=schema)
            except ValidationError as e:
                schema_errors.append(f"Item {i}: {e.message}")
        
        if schema_errors:
            results.append(ValidationResult(
                "schema_validation",
                ValidationStatus.FAIL,
                f"Schema validation failed for {len(schema_errors)} items",
                details={"errors": schema_errors[:10]},  # Limit to first 10 errors
                suggestions=["Fix schema violations", "Check required fields", "Validate data types"]
            ))
        else:
            results.append(ValidationResult(
                "schema_validation",
                ValidationStatus.PASS,
                "All items pass schema validation"
            ))
        
        # Check for duplicate IDs
        ids = [item.get('id') for item in items if item.get('id')]
        duplicate_ids = [id for id in set(ids) if ids.count(id) > 1]
        
        if duplicate_ids:
            results.append(ValidationResult(
                "unique_ids",
                ValidationStatus.FAIL,
                f"Found {len(duplicate_ids)} duplicate IDs",
                details={"duplicate_ids": duplicate_ids},
                suggestions=["Ensure all IDs are unique", "Use UUID or sequential numbering"]
            ))
        else:
            results.append(ValidationResult(
                "unique_ids",
                ValidationStatus.PASS,
                "All IDs are unique"
            ))
        
        # Check required fields
        required_fields = self._get_required_fields(dataset_type)
        missing_fields = []
        
        for i, item in enumerate(items):
            for field in required_fields:
                if field not in item or not item[field]:
                    missing_fields.append(f"Item {i}: missing '{field}'")
        
        if missing_fields:
            results.append(ValidationResult(
                "required_fields",
                ValidationStatus.FAIL,
                f"Missing required fields in {len(missing_fields)} cases",
                details={"missing_fields": missing_fields[:10]},
                suggestions=["Add missing required fields", "Check field names", "Validate field values"]
            ))
        else:
            results.append(ValidationResult(
                "required_fields",
                ValidationStatus.PASS,
                "All required fields are present"
            ))
        
        return results
    
    def _run_comprehensive_validation(self, items: List[Dict[str, Any]], dataset_type: str, dataset_path: Path) -> List[ValidationResult]:
        """Run comprehensive validation checks"""
        results = []
        
        # Language distribution check
        languages = [item.get('language') for item in items if item.get('language')]
        language_counts = {lang: languages.count(lang) for lang in set(languages)}
        
        if len(language_counts) < 2:
            results.append(ValidationResult(
                "language_diversity",
                ValidationStatus.WARN,
                f"Limited language diversity: {list(language_counts.keys())}",
                details={"language_distribution": language_counts},
                suggestions=["Add more programming languages", "Ensure balanced language distribution"]
            ))
        else:
            results.append(ValidationResult(
                "language_diversity",
                ValidationStatus.PASS,
                f"Good language diversity: {len(language_counts)} languages"
            ))
        
        # Difficulty distribution check
        difficulties = [item.get('difficulty') for item in items if item.get('difficulty')]
        difficulty_counts = {diff: difficulties.count(diff) for diff in set(difficulties)}
        
        expected_difficulties = {"simple", "intermediate", "complex"}
        missing_difficulties = expected_difficulties - set(difficulty_counts.keys())
        
        if missing_difficulties:
            results.append(ValidationResult(
                "difficulty_distribution",
                ValidationStatus.WARN,
                f"Missing difficulty levels: {missing_difficulties}",
                details={"difficulty_distribution": difficulty_counts},
                suggestions=["Add problems for missing difficulty levels", "Ensure balanced difficulty distribution"]
            ))
        else:
            results.append(ValidationResult(
                "difficulty_distribution",
                ValidationStatus.PASS,
                "All difficulty levels represented"
            ))
        
        # Context mode distribution check
        context_modes = [item.get('context_mode') for item in items if item.get('context_mode')]
        context_counts = {mode: context_modes.count(mode) for mode in set(context_modes)}
        
        if len(context_counts) < 2:
            results.append(ValidationResult(
                "context_mode_diversity",
                ValidationStatus.WARN,
                f"Limited context mode diversity: {list(context_counts.keys())}",
                details={"context_mode_distribution": context_counts},
                suggestions=["Add different context modes", "Ensure balanced context distribution"]
            ))
        else:
            results.append(ValidationResult(
                "context_mode_diversity",
                ValidationStatus.PASS,
                f"Good context mode diversity: {len(context_counts)} modes"
            ))
        
        # Content quality checks
        content_issues = []
        
        for i, item in enumerate(items):
            # Check prompt quality
            prompt = item.get('prompt', '')
            if len(prompt) < 50:
                content_issues.append(f"Item {i}: prompt too short ({len(prompt)} chars)")
            elif len(prompt) > 2000:
                content_issues.append(f"Item {i}: prompt too long ({len(prompt)} chars)")
            
            # Check reference solutions
            if dataset_type == "single_turn":
                references = item.get('reference', [])
                if not references:
                    content_issues.append(f"Item {i}: missing reference solution")
                elif any(len(ref) < 20 for ref in references):
                    content_issues.append(f"Item {i}: reference solution too short")
        
        if content_issues:
            results.append(ValidationResult(
                "content_quality",
                ValidationStatus.WARN,
                f"Content quality issues found in {len(content_issues)} items",
                details={"content_issues": content_issues[:10]},
                suggestions=["Review and improve content quality", "Ensure adequate prompt length", "Provide complete reference solutions"]
            ))
        else:
            results.append(ValidationResult(
                "content_quality",
                ValidationStatus.PASS,
                "Content quality checks passed"
            ))
        
        # Test file validation
        test_issues = []
        
        for i, item in enumerate(items):
            tests = item.get('tests', [])
            if not tests:
                test_issues.append(f"Item {i}: no test cases defined")
            else:
                for j, test in enumerate(tests):
                    if 'file' not in test:
                        test_issues.append(f"Item {i}, test {j}: missing test file")
                    elif 'cmd' not in test:
                        test_issues.append(f"Item {i}, test {j}: missing test command")
        
        if test_issues:
            results.append(ValidationResult(
                "test_validation",
                ValidationStatus.WARN,
                f"Test validation issues found in {len(test_issues)} cases",
                details={"test_issues": test_issues[:10]},
                suggestions=["Add test cases for all items", "Ensure test files and commands are specified"]
            ))
        else:
            results.append(ValidationResult(
                "test_validation",
                ValidationStatus.PASS,
                "Test validation checks passed"
            ))
        
        return results
    
    def _run_production_validation(self, items: List[Dict[str, Any]], dataset_type: str, dataset_path: Path) -> List[ValidationResult]:
        """Run production-level validation checks"""
        results = []
        
        # Dataset size check
        min_size = 100  # Production requirement
        if len(items) < min_size:
            results.append(ValidationResult(
                "production_size",
                ValidationStatus.FAIL,
                f"Dataset too small for production: {len(items)} < {min_size}",
                suggestions=[f"Expand dataset to at least {min_size} items", "Use dataset generator to create more items"]
            ))
        else:
            results.append(ValidationResult(
                "production_size",
                ValidationStatus.PASS,
                f"Dataset meets production size requirement: {len(items)} items"
            ))
        
        # Metadata completeness check
        metadata_issues = []
        
        for i, item in enumerate(items):
            metadata = item.get('metadata', {})
            required_metadata = ['author', 'license', 'time_limit_s', 'memory_limit_mb']
            
            for field in required_metadata:
                if field not in metadata:
                    metadata_issues.append(f"Item {i}: missing metadata field '{field}'")
        
        if metadata_issues:
            results.append(ValidationResult(
                "metadata_completeness",
                ValidationStatus.WARN,
                f"Metadata completeness issues in {len(metadata_issues)} items",
                details={"metadata_issues": metadata_issues[:10]},
                suggestions=["Add complete metadata for all items", "Include author, license, and resource limits"]
            ))
        else:
            results.append(ValidationResult(
                "metadata_completeness",
                ValidationStatus.PASS,
                "Metadata completeness checks passed"
            ))
        
        # Security validation
        security_issues = []
        
        for i, item in enumerate(items):
            prompt = item.get('prompt', '')
            references = item.get('reference', [])
            
            # Check for potentially dangerous patterns
            dangerous_patterns = [
                r'eval\s*\(',
                r'exec\s*\(',
                r'__import__',
                r'subprocess',
                r'os\.system',
                r'shell=True'
            ]
            
            for pattern in dangerous_patterns:
                if re.search(pattern, prompt, re.IGNORECASE):
                    security_issues.append(f"Item {i}: potentially dangerous pattern in prompt: {pattern}")
                
                for ref in references:
                    if re.search(pattern, str(ref), re.IGNORECASE):
                        security_issues.append(f"Item {i}: potentially dangerous pattern in reference: {pattern}")
        
        if security_issues:
            results.append(ValidationResult(
                "security_validation",
                ValidationStatus.WARN,
                f"Security concerns found in {len(security_issues)} items",
                details={"security_issues": security_issues[:10]},
                suggestions=["Review and sanitize dangerous code patterns", "Use safe alternatives", "Add security warnings"]
            ))
        else:
            results.append(ValidationResult(
                "security_validation",
                ValidationStatus.PASS,
                "Security validation checks passed"
            ))
        
        # Performance validation
        performance_issues = []
        
        for i, item in enumerate(items):
            metadata = item.get('metadata', {})
            time_limit = metadata.get('time_limit_s', 0)
            memory_limit = metadata.get('memory_limit_mb', 0)
            
            if time_limit <= 0:
                performance_issues.append(f"Item {i}: invalid time limit: {time_limit}")
            elif time_limit > 300:  # 5 minutes max
                performance_issues.append(f"Item {i}: time limit too high: {time_limit}s")
            
            if memory_limit <= 0:
                performance_issues.append(f"Item {i}: invalid memory limit: {memory_limit}")
            elif memory_limit > 2048:  # 2GB max
                performance_issues.append(f"Item {i}: memory limit too high: {memory_limit}MB")
        
        if performance_issues:
            results.append(ValidationResult(
                "performance_validation",
                ValidationStatus.WARN,
                f"Performance validation issues in {len(performance_issues)} items",
                details={"performance_issues": performance_issues[:10]},
                suggestions=["Set reasonable resource limits", "Ensure time limits are positive", "Keep memory limits reasonable"]
            ))
        else:
            results.append(ValidationResult(
                "performance_validation",
                ValidationStatus.PASS,
                "Performance validation checks passed"
            ))
        
        return results
    
    def _calculate_overall_metrics(self, validation_results: List[ValidationResult]) -> Tuple[ValidationStatus, float]:
        """Calculate overall validation status and quality score"""
        if not validation_results:
            return ValidationStatus.FAIL, 0.0
        
        fail_count = sum(1 for result in validation_results if result.status == ValidationStatus.FAIL)
        warn_count = sum(1 for result in validation_results if result.status == ValidationStatus.WARN)
        pass_count = sum(1 for result in validation_results if result.status == ValidationStatus.PASS)
        
        total_checks = len(validation_results)
        
        # Calculate quality score (0-100)
        quality_score = (pass_count * 100 + warn_count * 50) / total_checks
        
        # Determine overall status
        if fail_count > 0:
            overall_status = ValidationStatus.FAIL
        elif warn_count > total_checks * 0.3:  # More than 30% warnings
            overall_status = ValidationStatus.WARN
        else:
            overall_status = ValidationStatus.PASS
        
        return overall_status, quality_score
    
    def _get_required_fields(self, dataset_type: str) -> List[str]:
        """Get required fields for dataset type"""
        if dataset_type == "single_turn":
            return ['id', 'title', 'language', 'scenario', 'difficulty', 'context_mode', 'prompt', 'reference', 'tests', 'metadata']
        elif dataset_type == "multi_turn":
            return ['id', 'scenario', 'difficulty', 'language', 'context_mode', 'turns', 'success_metrics', 'metadata']
        else:
            return ['id']
    
    def _load_single_turn_schema(self) -> Dict[str, Any]:
        """Load JSON schema for single-turn problems"""
        return {
            "type": "object",
            "required": ["id", "title", "language", "scenario", "difficulty", "context_mode", "prompt", "reference", "tests", "metadata"],
            "properties": {
                "id": {"type": "string", "pattern": "^[a-zA-Z0-9_]+$"},
                "title": {"type": "string", "minLength": 5},
                "language": {"type": "string", "enum": ["python", "javascript", "java", "cpp", "go", "rust", "typescript", "sql", "shell"]},
                "scenario": {"type": "string"},
                "difficulty": {"type": "string", "enum": ["simple", "intermediate", "complex"]},
                "context_mode": {"type": "string", "enum": ["no_context", "minimal_context", "full_context", "domain_context"]},
                "prompt": {"type": "string", "minLength": 10},
                "reference": {"type": "array", "items": {"type": "string"}, "minItems": 1},
                "tests": {"type": "array", "items": {"type": "object", "required": ["type", "file", "cmd"]}},
                "metadata": {"type": "object", "required": ["time_limit_s", "memory_limit_mb", "author", "license"]}
            }
        }
    
    def _load_multi_turn_schema(self) -> Dict[str, Any]:
        """Load JSON schema for multi-turn scenarios"""
        return {
            "type": "object",
            "required": ["id", "scenario", "difficulty", "language", "context_mode", "turns", "success_metrics", "metadata"],
            "properties": {
                "id": {"type": "string", "pattern": "^[a-zA-Z0-9_]+$"},
                "scenario": {"type": "string"},
                "difficulty": {"type": "string", "enum": ["simple", "intermediate", "complex"]},
                "language": {"type": "string", "enum": ["python", "javascript", "java", "cpp", "go", "rust", "typescript", "sql", "shell"]},
                "context_mode": {"type": "string", "enum": ["no_context", "minimal_context", "full_context", "domain_context"]},
                "turns": {"type": "array", "items": {"type": "object"}, "minItems": 1},
                "success_metrics": {"type": "object"},
                "metadata": {"type": "object", "required": ["author", "license"]}
            }
        }
    
    def _get_timestamp(self) -> str:
        """Get current timestamp"""
        from datetime import datetime
        return datetime.now().isoformat()
    
    def generate_validation_report(self, reports: List[DatasetValidationReport], output_file: str = None) -> str:
        """Generate a comprehensive validation report"""
        report_lines = []
        report_lines.append("# Dataset Validation Report")
        report_lines.append(f"Generated: {self._get_timestamp()}")
        report_lines.append("")
        
        # Summary
        total_datasets = len(reports)
        passed_datasets = sum(1 for r in reports if r.overall_status == ValidationStatus.PASS)
        warned_datasets = sum(1 for r in reports if r.overall_status == ValidationStatus.WARN)
        failed_datasets = sum(1 for r in reports if r.overall_status == ValidationStatus.FAIL)
        
        avg_quality_score = sum(r.quality_score for r in reports) / total_datasets if total_datasets > 0 else 0
        
        report_lines.append("## Summary")
        report_lines.append(f"- Total datasets: {total_datasets}")
        report_lines.append(f"- Passed: {passed_datasets}")
        report_lines.append(f"- Warnings: {warned_datasets}")
        report_lines.append(f"- Failed: {failed_datasets}")
        report_lines.append(f"- Average quality score: {avg_quality_score:.1f}/100")
        report_lines.append("")
        
        # Detailed results
        report_lines.append("## Detailed Results")
        report_lines.append("")
        
        for report in reports:
            report_lines.append(f"### {report.dataset_path}")
            report_lines.append(f"- Type: {report.dataset_type}")
            report_lines.append(f"- Items: {report.total_items}")
            report_lines.append(f"- Status: {report.overall_status.value.upper()}")
            report_lines.append(f"- Quality Score: {report.quality_score:.1f}/100")
            report_lines.append("")
            
            # Validation results
            for result in report.validation_results:
                status_icon = {"pass": "✅", "warn": "⚠️", "fail": "❌"}[result.status.value]
                report_lines.append(f"  {status_icon} **{result.check_name}**: {result.message}")
                
                if result.suggestions:
                    report_lines.append("    - Suggestions:")
                    for suggestion in result.suggestions:
                        report_lines.append(f"      - {suggestion}")
            
            report_lines.append("")
        
        # Recommendations
        report_lines.append("## Recommendations")
        report_lines.append("")
        
        if failed_datasets > 0:
            report_lines.append("### Critical Issues")
            report_lines.append("- Fix failed datasets before production deployment")
            report_lines.append("- Address schema validation errors")
            report_lines.append("- Ensure minimum dataset sizes are met")
            report_lines.append("")
        
        if warned_datasets > 0:
            report_lines.append("### Improvements")
            report_lines.append("- Address warning issues to improve quality")
            report_lines.append("- Improve content diversity and distribution")
            report_lines.append("- Complete missing metadata fields")
            report_lines.append("")
        
        report_lines.append("### General Recommendations")
        report_lines.append("- Maintain regular validation checks")
        report_lines.append("- Monitor dataset quality over time")
        report_lines.append("- Implement automated validation in CI/CD")
        report_lines.append("")
        
        report_content = "\n".join(report_lines)
        
        if output_file:
            with open(output_file, 'w') as f:
                f.write(report_content)
            logger.info(f"Validation report saved to: {output_file}")
        
        return report_content

def main():
    """Main function for command-line usage"""
    parser = argparse.ArgumentParser(description="Validate datasets for AI evaluation engine")
    parser.add_argument("--dataset", type=str, help="Specific dataset file to validate")
    parser.add_argument("--level", choices=["basic", "comprehensive", "production"], default="comprehensive", help="Validation level")
    parser.add_argument("--output", type=str, help="Output file for validation report")
    parser.add_argument("--base-path", type=str, default="lm_eval/tasks", help="Base path for task directories")
    parser.add_argument("--format", choices=["text", "json"], default="text", help="Output format")
    
    args = parser.parse_args()
    
    validator = DatasetValidator(args.base_path)
    validation_level = ValidationLevel(args.level)
    
    if args.dataset:
        # Validate single dataset
        report = validator.validate_dataset(args.dataset, validation_level)
        reports = [report]
    else:
        # Validate all datasets
        reports = validator.validate_all_datasets(validation_level)
    
    # Generate report
    if args.format == "json":
        report_data = [asdict(report) for report in reports]
        report_content = json.dumps(report_data, indent=2)
        
        if args.output:
            with open(args.output, 'w') as f:
                f.write(report_content)
        else:
            print(report_content)
    else:
        report_content = validator.generate_validation_report(reports, args.output)
        
        if not args.output:
            print(report_content)
    
    # Exit with appropriate code
    failed_reports = [r for r in reports if r.overall_status == ValidationStatus.FAIL]
    if failed_reports:
        logger.error(f"Validation failed for {len(failed_reports)} datasets")
        exit(1)
    else:
        logger.info("All datasets passed validation")
        exit(0)

if __name__ == "__main__":
    main()