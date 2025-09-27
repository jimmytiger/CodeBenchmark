#!/usr/bin/env python3
"""
AI Evaluation Engine - Setup Validation Script

This script validates that the AI Evaluation Engine is properly installed
and integrated with lm-evaluation-harness.
"""

import sys
import os
import subprocess
import importlib
import json
from pathlib import Path
from typing import List, Dict, Any, Optional
import logging

# Configure logging
logging.basicConfig(
    level=logging.INFO,
    format='%(asctime)s - %(levelname)s - %(message)s'
)
logger = logging.getLogger(__name__)


class ValidationResult:
    """Container for validation results"""
    def __init__(self, name: str, passed: bool, message: str, details: Optional[Dict] = None):
        self.name = name
        self.passed = passed
        self.message = message
        self.details = details or {}


class SetupValidator:
    """Comprehensive setup validation"""
    
    def __init__(self):
        self.results: List[ValidationResult] = []
        self.python_version = sys.version_info
        
    def run_all_validations(self) -> bool:
        """Run all validation checks"""
        logger.info("🔍 Starting AI Evaluation Engine setup validation...")
        
        # Core validations
        self.validate_python_version()
        self.validate_core_imports()
        self.validate_lm_eval_integration()
        self.validate_evaluation_engine()
        self.validate_task_discovery()
        self.validate_extended_registry()
        self.validate_docker_setup()
        self.validate_configuration_files()
        self.validate_directory_structure()
        self.validate_dependencies()
        
        # Optional validations
        self.validate_api_keys()
        self.validate_database_connection()
        self.validate_redis_connection()
        
        # Summary
        self.print_validation_summary()
        
        # Return overall success
        return all(result.passed for result in self.results if result.name != "API Keys" and result.name != "Database Connection" and result.name != "Redis Connection")
    
    def validate_python_version(self):
        """Validate Python version"""
        try:
            if self.python_version >= (3, 9):
                self.results.append(ValidationResult(
                    "Python Version",
                    True,
                    f"Python {self.python_version.major}.{self.python_version.minor}.{self.python_version.micro} ✓",
                    {"version": f"{self.python_version.major}.{self.python_version.minor}.{self.python_version.micro}"}
                ))
            else:
                self.results.append(ValidationResult(
                    "Python Version",
                    False,
                    f"Python 3.9+ required, found {self.python_version.major}.{self.python_version.minor}",
                    {"version": f"{self.python_version.major}.{self.python_version.minor}.{self.python_version.micro}"}
                ))
        except Exception as e:
            self.results.append(ValidationResult(
                "Python Version",
                False,
                f"Error checking Python version: {e}"
            ))
    
    def validate_core_imports(self):
        """Validate core package imports"""
        core_packages = [
            "lm_eval",
            "evaluation_engine",
            "torch",
            "transformers",
            "datasets",
            "numpy",
            "pandas"
        ]
        
        failed_imports = []
        import_details = {}
        
        for package in core_packages:
            try:
                module = importlib.import_module(package)
                version = getattr(module, '__version__', 'unknown')
                import_details[package] = version
                logger.debug(f"✓ {package} {version}")
            except ImportError as e:
                failed_imports.append(f"{package}: {e}")
                logger.error(f"✗ Failed to import {package}: {e}")
        
        if not failed_imports:
            self.results.append(ValidationResult(
                "Core Imports",
                True,
                f"All {len(core_packages)} core packages imported successfully ✓",
                import_details
            ))
        else:
            self.results.append(ValidationResult(
                "Core Imports",
                False,
                f"Failed to import {len(failed_imports)} packages: {', '.join(failed_imports)}",
                {"failed": failed_imports, "successful": import_details}
            ))
    
    def validate_lm_eval_integration(self):
        """Validate lm-eval integration"""
        try:
            from lm_eval.tasks import get_task_dict
            from lm_eval.evaluator import simple_evaluate
            from lm_eval.api.model import LM
            
            # Test task discovery using TaskManager
            from lm_eval.tasks import TaskManager
            task_manager = TaskManager()
            all_tasks = task_manager.all_tasks
            task_count = len(all_tasks)
            
            # Test basic functionality
            if task_count > 0:
                self.results.append(ValidationResult(
                    "lm-eval Integration",
                    True,
                    f"lm-eval integration working, {task_count} tasks available ✓",
                    {"task_count": task_count, "sample_tasks": all_tasks[:5]}
                ))
            else:
                self.results.append(ValidationResult(
                    "lm-eval Integration",
                    False,
                    "lm-eval integration working but no tasks found",
                    {"task_count": 0}
                ))
                
        except Exception as e:
            self.results.append(ValidationResult(
                "lm-eval Integration",
                False,
                f"lm-eval integration failed: {e}"
            ))
    
    def validate_evaluation_engine(self):
        """Validate evaluation engine components"""
        try:
            from evaluation_engine.core.unified_framework import UnifiedEvaluationFramework, EvaluationRequest
            from evaluation_engine.core.task_registration import ExtendedTaskRegistry
            
            # Test framework initialization
            framework = UnifiedEvaluationFramework()
            
            # Test request validation
            request = EvaluationRequest(
                model="dummy",
                tasks=["dummy_task"],
                limit=1
            )
            
            # Test basic functionality
            available_tasks = framework.list_available_tasks()
            
            self.results.append(ValidationResult(
                "Evaluation Engine",
                True,
                f"Evaluation engine components loaded successfully ✓",
                {
                    "framework_initialized": True,
                    "available_tasks_count": len(available_tasks),
                    "request_validation": True
                }
            ))
            
        except Exception as e:
            self.results.append(ValidationResult(
                "Evaluation Engine",
                False,
                f"Evaluation engine validation failed: {e}"
            ))
    
    def validate_task_discovery(self):
        """Validate task discovery and categorization"""
        try:
            from lm_eval.tasks import TaskManager
            
            task_manager = TaskManager()
            all_tasks = task_manager.all_tasks
            
            # Categorize tasks
            categories = {
                "single_turn_scenarios": [t for t in all_tasks if "single_turn_scenarios" in t],
                "multi_turn_scenarios": [t for t in all_tasks if "multi_turn_scenarios" in t],
                "python_coding": [t for t in all_tasks if "python_coding" in t],
                "multi_turn_coding": [t for t in all_tasks if "multi_turn_coding" in t]
            }
            
            total_custom_tasks = sum(len(tasks) for tasks in categories.values())
            
            if total_custom_tasks > 0:
                self.results.append(ValidationResult(
                    "Task Discovery",
                    True,
                    f"Task discovery working, found {total_custom_tasks} custom tasks ✓",
                    {
                        "categories": {k: len(v) for k, v in categories.items()},
                        "sample_tasks": {k: v[:3] for k, v in categories.items() if v}
                    }
                ))
            else:
                self.results.append(ValidationResult(
                    "Task Discovery",
                    False,
                    "Task discovery working but no custom tasks found",
                    {"total_tasks": len(all_tasks), "custom_tasks": 0}
                ))
                
        except Exception as e:
            self.results.append(ValidationResult(
                "Task Discovery",
                False,
                f"Task discovery failed: {e}"
            ))
    
    def validate_extended_registry(self):
        """Validate extended task registry functionality"""
        try:
            from evaluation_engine.core.task_registration import extended_registry
            
            # Test registry functionality
            hierarchy = extended_registry.get_task_hierarchy()
            
            # Test task filtering
            single_turn_tasks = extended_registry.discover_tasks({"category": "single_turn_scenarios"})
            multi_turn_tasks = extended_registry.discover_tasks({"category": "multi_turn_scenarios"})
            
            self.results.append(ValidationResult(
                "Extended Registry",
                True,
                f"Extended registry working, {len(hierarchy)} categories ✓",
                {
                    "categories": list(hierarchy.keys()),
                    "single_turn_tasks": len(single_turn_tasks),
                    "multi_turn_tasks": len(multi_turn_tasks)
                }
            ))
            
        except Exception as e:
            self.results.append(ValidationResult(
                "Extended Registry",
                False,
                f"Extended registry validation failed: {e}"
            ))
    
    def validate_docker_setup(self):
        """Validate Docker setup for secure code execution"""
        try:
            import docker
            
            # Test Docker client
            client = docker.from_env()
            
            # Check if Docker is running
            client.ping()
            
            # Check for evaluation containers
            images = client.images.list()
            eval_images = [img for img in images if any('ai-eval' in tag for tag in img.tags)]
            
            self.results.append(ValidationResult(
                "Docker Setup",
                True,
                f"Docker available, {len(eval_images)} evaluation images found ✓",
                {
                    "docker_available": True,
                    "total_images": len(images),
                    "eval_images": len(eval_images)
                }
            ))
            
        except ImportError:
            self.results.append(ValidationResult(
                "Docker Setup",
                False,
                "Docker Python client not installed"
            ))
        except Exception as e:
            self.results.append(ValidationResult(
                "Docker Setup",
                False,
                f"Docker setup validation failed: {e}"
            ))
    
    def validate_configuration_files(self):
        """Validate configuration files"""
        config_files = [
            ".env",
            "pyproject.toml",
            "docker-compose.yml",
            "Dockerfile"
        ]
        
        found_files = []
        missing_files = []
        
        for config_file in config_files:
            if Path(config_file).exists():
                found_files.append(config_file)
            else:
                missing_files.append(config_file)
        
        if len(found_files) >= 3:  # Allow some flexibility
            self.results.append(ValidationResult(
                "Configuration Files",
                True,
                f"Configuration files present: {', '.join(found_files)} ✓",
                {"found": found_files, "missing": missing_files}
            ))
        else:
            self.results.append(ValidationResult(
                "Configuration Files",
                False,
                f"Missing critical configuration files: {', '.join(missing_files)}",
                {"found": found_files, "missing": missing_files}
            ))
    
    def validate_directory_structure(self):
        """Validate directory structure"""
        required_dirs = [
            "lm_eval/tasks/single_turn_scenarios",
            "lm_eval/tasks/multi_turn_scenarios",
            "evaluation_engine/core",
            "results",
            "logs"
        ]
        
        found_dirs = []
        missing_dirs = []
        
        for directory in required_dirs:
            if Path(directory).exists():
                found_dirs.append(directory)
            else:
                missing_dirs.append(directory)
        
        if len(found_dirs) >= 4:  # Allow some flexibility
            self.results.append(ValidationResult(
                "Directory Structure",
                True,
                f"Directory structure valid, {len(found_dirs)}/{len(required_dirs)} directories found ✓",
                {"found": found_dirs, "missing": missing_dirs}
            ))
        else:
            self.results.append(ValidationResult(
                "Directory Structure",
                False,
                f"Invalid directory structure, missing: {', '.join(missing_dirs)}",
                {"found": found_dirs, "missing": missing_dirs}
            ))
    
    def validate_dependencies(self):
        """Validate key dependencies"""
        try:
            # Test key functionality
            import torch
            import transformers
            import datasets
            
            # Test versions
            torch_version = torch.__version__
            transformers_version = transformers.__version__
            datasets_version = datasets.__version__
            
            self.results.append(ValidationResult(
                "Dependencies",
                True,
                f"Key dependencies validated ✓",
                {
                    "torch": torch_version,
                    "transformers": transformers_version,
                    "datasets": datasets_version
                }
            ))
            
        except Exception as e:
            self.results.append(ValidationResult(
                "Dependencies",
                False,
                f"Dependency validation failed: {e}"
            ))
    
    def validate_api_keys(self):
        """Validate API keys (optional)"""
        api_keys = {
            "OPENAI_API_KEY": os.getenv("OPENAI_API_KEY"),
            "ANTHROPIC_API_KEY": os.getenv("ANTHROPIC_API_KEY"),
            "DASHSCOPE_API_KEY": os.getenv("DASHSCOPE_API_KEY")
        }
        
        available_keys = [k for k, v in api_keys.items() if v]
        
        if available_keys:
            self.results.append(ValidationResult(
                "API Keys",
                True,
                f"API keys configured: {', '.join(available_keys)} ✓",
                {"configured_keys": available_keys}
            ))
        else:
            self.results.append(ValidationResult(
                "API Keys",
                False,
                "No API keys configured (optional for basic functionality)",
                {"configured_keys": []}
            ))
    
    def validate_database_connection(self):
        """Validate database connection (optional)"""
        try:
            database_url = os.getenv("DATABASE_URL")
            if database_url:
                # Try to connect (would need actual database setup)
                self.results.append(ValidationResult(
                    "Database Connection",
                    True,
                    "Database URL configured ✓",
                    {"database_configured": True}
                ))
            else:
                self.results.append(ValidationResult(
                    "Database Connection",
                    False,
                    "Database URL not configured (optional)",
                    {"database_configured": False}
                ))
        except Exception as e:
            self.results.append(ValidationResult(
                "Database Connection",
                False,
                f"Database validation failed: {e}"
            ))
    
    def validate_redis_connection(self):
        """Validate Redis connection (optional)"""
        try:
            redis_url = os.getenv("REDIS_URL")
            if redis_url:
                self.results.append(ValidationResult(
                    "Redis Connection",
                    True,
                    "Redis URL configured ✓",
                    {"redis_configured": True}
                ))
            else:
                self.results.append(ValidationResult(
                    "Redis Connection",
                    False,
                    "Redis URL not configured (optional)",
                    {"redis_configured": False}
                ))
        except Exception as e:
            self.results.append(ValidationResult(
                "Redis Connection",
                False,
                f"Redis validation failed: {e}"
            ))
    
    def print_validation_summary(self):
        """Print validation summary"""
        print("\n" + "="*80)
        print("🔍 AI EVALUATION ENGINE - SETUP VALIDATION SUMMARY")
        print("="*80)
        
        passed_count = sum(1 for r in self.results if r.passed)
        total_count = len(self.results)
        
        # Core validations (required)
        core_validations = [r for r in self.results if r.name not in ["API Keys", "Database Connection", "Redis Connection"]]
        core_passed = sum(1 for r in core_validations if r.passed)
        core_total = len(core_validations)
        
        print(f"\n📊 OVERALL STATUS: {core_passed}/{core_total} core validations passed")
        print(f"📊 TOTAL STATUS: {passed_count}/{total_count} validations passed")
        
        print(f"\n{'Validation':<25} {'Status':<10} {'Details'}")
        print("-" * 80)
        
        for result in self.results:
            status = "✅ PASS" if result.passed else "❌ FAIL"
            print(f"{result.name:<25} {status:<10} {result.message}")
        
        # Recommendations
        print(f"\n💡 RECOMMENDATIONS:")
        failed_core = [r for r in core_validations if not r.passed]
        
        if not failed_core:
            print("✅ All core components are working correctly!")
            print("🚀 Your AI Evaluation Engine is ready to use!")
            print("\nNext steps:")
            print("1. Configure API keys in .env file for model access")
            print("2. Run a test evaluation: python -m lm_eval --model dummy --tasks single_turn_scenarios_function_generation --limit 1")
            print("3. Check the documentation for advanced usage")
        else:
            print("❌ Some core components need attention:")
            for result in failed_core:
                print(f"   - {result.name}: {result.message}")
            print("\nPlease fix these issues before proceeding.")
        
        print("\n" + "="*80)
    
    def export_results(self, output_path: str = "validation_results.json"):
        """Export validation results to JSON"""
        from datetime import datetime
        export_data = {
            "timestamp": datetime.now().isoformat(),
            "python_version": f"{self.python_version.major}.{self.python_version.minor}.{self.python_version.micro}",
            "total_validations": len(self.results),
            "passed_validations": sum(1 for r in self.results if r.passed),
            "results": [
                {
                    "name": r.name,
                    "passed": r.passed,
                    "message": r.message,
                    "details": r.details
                }
                for r in self.results
            ]
        }
        
        with open(output_path, 'w') as f:
            json.dump(export_data, f, indent=2)
        
        print(f"📄 Validation results exported to {output_path}")


def main():
    """Main validation function"""
    validator = SetupValidator()
    success = validator.run_all_validations()
    
    # Export results
    validator.export_results()
    
    # Exit with appropriate code
    sys.exit(0 if success else 1)


if __name__ == "__main__":
    main()