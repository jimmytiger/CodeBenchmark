#!/usr/bin/env python3
"""
Final Integration and Validation Testing System

This module provides comprehensive end-to-end validation of the entire
EvaluationEngineV1_0_tests framework, ensuring all components work together
correctly and all requirements are satisfied.
"""

import asyncio
import json
import logging
import os
import subprocess
import sys
import time
from dataclasses import dataclass, asdict
from pathlib import Path
from typing import Dict, List, Optional, Any, Tuple
import yaml

# Import our testing framework components
try:
    from .core.test_orchestrator import TestOrchestrator
    from .core.config_manager import ConfigManager
    from .core.error_handler import ErrorHandler
    from .core.real_execution_validator import RealExecutionValidator
    from .core.metrics_collector import MetricsCollector
    from .cli.cli_test_runner import CLITestRunner
    from .api.api_test_client import APITestClient
    from .api.api_test_server import APITestServer
    from .adapters.lm_eval_adapter_validator import LMEvalAdapterValidator
    from .adapters.swe_bench_adapter_validator import SWEBenchAdapterValidator
    from .reports.test_report_generator import TestReportGenerator
except ImportError:
    # Fallback for direct execution
    import sys
    from pathlib import Path
    sys.path.insert(0, str(Path(__file__).parent))
    
    from core.test_orchestrator import TestOrchestrator
    from core.config_manager import ConfigManager
    from core.error_handler import ErrorHandler
    from core.real_execution_validator import RealExecutionValidator
    from core.metrics_collector import MetricsCollector
    from cli.cli_test_runner import CLITestRunner
    from api.api_test_client import APITestClient
    from api.api_test_server import APITestServer
    from adapters.lm_eval_adapter_validator import LMEvalAdapterValidator
    from adapters.swe_bench_adapter_validator import SWEBenchAdapterValidator
    from reports.test_report_generator import TestReportGenerator


@dataclass
class ValidationResult:
    """Result of a validation test"""
    component: str
    test_name: str
    status: str  # 'passed', 'failed', 'skipped'
    execution_time: float
    details: str
    requirements_validated: List[str]
    errors: List[str] = None
    
    def __post_init__(self):
        if self.errors is None:
            self.errors = []


@dataclass
class IntegrationTestSuite:
    """Complete integration test suite results"""
    total_tests: int
    passed_tests: int
    failed_tests: int
    skipped_tests: int
    total_execution_time: float
    validation_results: List[ValidationResult]
    requirements_coverage: Dict[str, bool]
    component_status: Dict[str, str]
    final_status: str


class FinalIntegrationValidator:
    """
    Comprehensive integration and validation testing system
    
    This class orchestrates the final validation of all components,
    ensuring complete end-to-end functionality and requirements compliance.
    """
    
    def __init__(self, config_path: Optional[str] = None):
        """Initialize the final integration validator"""
        self.logger = logging.getLogger(__name__)
        self.config_manager = ConfigManager()
        self.error_handler = ErrorHandler()
        self.test_orchestrator = TestOrchestrator()
        self.real_execution_validator = RealExecutionValidator()
        self.metrics_collector = MetricsCollector()
        self.report_generator = TestReportGenerator()
        
        # Load configuration
        if config_path:
            self.config = self.config_manager.load_config(config_path)
        else:
            self.config = self._load_default_config()
        
        # Initialize validation results
        self.validation_results: List[ValidationResult] = []
        self.start_time = None
        self.end_time = None
        
        # Requirements mapping
        self.requirements_map = self._build_requirements_map()
        
    def _load_default_config(self) -> Dict[str, Any]:
        """Load default configuration for final validation"""
        return {
            'validation': {
                'run_cli_tests': True,
                'run_api_tests': True,
                'run_adapter_tests': True,
                'run_pipeline_tests': True,
                'run_performance_tests': True,
                'validate_documentation': True,
                'timeout_seconds': 1800,  # 30 minutes
                'parallel_execution': True
            },
            'cli_tests': {
                'test_builtin_tasks': True,
                'test_custom_tasks': True,
                'test_error_handling': True
            },
            'api_tests': {
                'test_endpoints': True,
                'test_async_operations': True,
                'test_curl_commands': True
            },
            'adapter_tests': {
                'test_lm_eval': True,
                'test_swe_bench': True,
                'validate_real_execution': True
            },
            'documentation_tests': {
                'validate_usage_guide': True,
                'validate_api_docs': True,
                'validate_examples': True
            }
        }
    
    def _build_requirements_map(self) -> Dict[str, List[str]]:
        """Build mapping of requirements to test components"""
        return {
            # CLI Testing Interface Requirements (1.x)
            '1.1': ['cli_real_execution', 'cli_builtin_tasks'],
            '1.2': ['cli_builtin_tasks', 'cli_task_loading'],
            '1.3': ['cli_custom_tasks', 'cli_task_discovery'],
            '1.4': ['cli_reporting', 'cli_execution_reports'],
            '1.5': ['cli_error_handling', 'cli_error_messages'],
            '1.6': ['cli_configuration', 'cli_parameter_handling'],
            
            # API Testing Interface Requirements (2.x)
            '2.1': ['api_curl_support', 'api_http_status'],
            '2.2': ['api_async_processing', 'api_evaluation_requests'],
            '2.3': ['api_json_responses', 'api_endpoint_queries'],
            '2.4': ['api_real_execution', 'api_evaluation_processing'],
            '2.5': ['api_error_handling', 'api_error_responses'],
            '2.6': ['api_batch_processing', 'api_concurrent_requests'],
            
            # Core Adapter Validation Requirements (3.x)
            '3.1': ['lm_eval_integration', 'lm_eval_harness_integration'],
            '3.2': ['swe_bench_integration', 'swe_bench_task_handling'],
            '3.3': ['adapter_task_validation', 'adapter_testing'],
            '3.4': ['adapter_dependencies', 'dependency_installation'],
            '3.5': ['adapter_error_diagnostics', 'adapter_validation_failures'],
            '3.6': ['adapter_standardized_results', 'adapter_result_processing'],
            
            # Complete Analysis Pipeline Requirements (4.x)
            '4.1': ['pipeline_configuration', 'configuration_validation'],
            '4.2': ['pipeline_execution', 'pipeline_stage_processing'],
            '4.3': ['pipeline_reporting', 'result_report_generation'],
            '4.4': ['pipeline_metrics', 'performance_tracking'],
            '4.5': ['pipeline_error_handling', 'error_context_provision'],
            '4.6': ['pipeline_result_storage', 'structured_result_saving']
        }
    
    async def run_complete_validation(self) -> IntegrationTestSuite:
        """
        Run the complete integration and validation test suite
        
        Returns:
            IntegrationTestSuite: Complete test results
        """
        self.logger.info("Starting final integration and validation testing")
        self.start_time = time.time()
        
        try:
            # Run all validation components
            await self._validate_cli_interface()
            await self._validate_api_interface()
            await self._validate_adapters()
            await self._validate_pipeline()
            await self._validate_documentation()
            await self._validate_requirements_coverage()
            
            # Generate final test suite results
            test_suite = self._generate_test_suite_results()
            
            # Generate comprehensive report
            await self._generate_final_report(test_suite)
            
            self.logger.info(f"Final validation completed: {test_suite.final_status}")
            return test_suite
            
        except Exception as e:
            self.logger.error(f"Final validation failed: {str(e)}")
            self.error_handler.handle_error(e, {"context": "final_validation"})
            raise
        finally:
            self.end_time = time.time()
    
    async def _validate_cli_interface(self):
        """Validate CLI testing interface (Requirements 1.x)"""
        self.logger.info("Validating CLI interface...")
        
        try:
            cli_runner = CLITestRunner()
            
            # Test CLI real execution (1.1)
            result = await self._run_validation_test(
                "cli_real_execution",
                "CLI Real Execution Test",
                lambda: cli_runner.test_real_execution(),
                ['1.1']
            )
            self.validation_results.append(result)
            
            # Test builtin tasks (1.2)
            result = await self._run_validation_test(
                "cli_builtin_tasks",
                "CLI Builtin Tasks Test",
                lambda: cli_runner.test_builtin_tasks(['hellaswag']),
                ['1.2']
            )
            self.validation_results.append(result)
            
            # Test custom tasks (1.3)
            result = await self._run_validation_test(
                "cli_custom_tasks",
                "CLI Custom Tasks Test",
                lambda: cli_runner.test_custom_task_discovery(),
                ['1.3']
            )
            self.validation_results.append(result)
            
            # Test error handling (1.5)
            result = await self._run_validation_test(
                "cli_error_handling",
                "CLI Error Handling Test",
                lambda: cli_runner.test_error_scenarios(),
                ['1.5']
            )
            self.validation_results.append(result)
            
            # Test configuration handling (1.6)
            result = await self._run_validation_test(
                "cli_configuration",
                "CLI Configuration Test",
                lambda: cli_runner.test_configuration_variations(),
                ['1.6']
            )
            self.validation_results.append(result)
            
        except Exception as e:
            self.logger.error(f"CLI validation failed: {str(e)}")
            self.validation_results.append(ValidationResult(
                component="cli",
                test_name="CLI Interface Validation",
                status="failed",
                execution_time=0.0,
                details=f"CLI validation failed: {str(e)}",
                requirements_validated=['1.1', '1.2', '1.3', '1.4', '1.5', '1.6'],
                errors=[str(e)]
            ))
    
    async def _validate_api_interface(self):
        """Validate API testing interface (Requirements 2.x)"""
        self.logger.info("Validating API interface...")
        
        try:
            # Start API test server
            api_server = APITestServer()
            await api_server.start_server("localhost", 8080)
            
            try:
                api_client = APITestClient("http://localhost:8080")
                
                # Test API endpoints (2.1, 2.3)
                result = await self._run_validation_test(
                    "api_endpoints",
                    "API Endpoints Test",
                    lambda: api_client.test_all_endpoints(),
                    ['2.1', '2.3']
                )
                self.validation_results.append(result)
                
                # Test async operations (2.2)
                result = await self._run_validation_test(
                    "api_async_operations",
                    "API Async Operations Test",
                    lambda: api_client.test_async_evaluations(),
                    ['2.2']
                )
                self.validation_results.append(result)
                
                # Test real execution (2.4)
                result = await self._run_validation_test(
                    "api_real_execution",
                    "API Real Execution Test",
                    lambda: api_client.test_real_execution_validation(),
                    ['2.4']
                )
                self.validation_results.append(result)
                
                # Test error handling (2.5)
                result = await self._run_validation_test(
                    "api_error_handling",
                    "API Error Handling Test",
                    lambda: api_client.test_error_scenarios(),
                    ['2.5']
                )
                self.validation_results.append(result)
                
                # Test concurrent requests (2.6)
                result = await self._run_validation_test(
                    "api_concurrent_requests",
                    "API Concurrent Requests Test",
                    lambda: api_client.test_concurrent_requests(),
                    ['2.6']
                )
                self.validation_results.append(result)
                
            finally:
                await api_server.stop_server()
                
        except Exception as e:
            self.logger.error(f"API validation failed: {str(e)}")
            self.validation_results.append(ValidationResult(
                component="api",
                test_name="API Interface Validation",
                status="failed",
                execution_time=0.0,
                details=f"API validation failed: {str(e)}",
                requirements_validated=['2.1', '2.2', '2.3', '2.4', '2.5', '2.6'],
                errors=[str(e)]
            ))
    
    async def _validate_adapters(self):
        """Validate core adapters (Requirements 3.x)"""
        self.logger.info("Validating core adapters...")
        
        try:
            # Test LM Eval adapter (3.1)
            lm_eval_validator = LMEvalAdapterValidator()
            result = await self._run_validation_test(
                "lm_eval_integration",
                "LM Eval Adapter Integration Test",
                lambda: lm_eval_validator.validate_integration(),
                ['3.1', '3.3', '3.4', '3.6']
            )
            self.validation_results.append(result)
            
            # Test SWE-bench adapter (3.2)
            swe_bench_validator = SWEBenchAdapterValidator()
            result = await self._run_validation_test(
                "swe_bench_integration",
                "SWE-bench Adapter Integration Test",
                lambda: swe_bench_validator.validate_integration(),
                ['3.2', '3.3', '3.4', '3.6']
            )
            self.validation_results.append(result)
            
            # Test adapter error handling (3.5)
            result = await self._run_validation_test(
                "adapter_error_handling",
                "Adapter Error Handling Test",
                lambda: self._test_adapter_error_scenarios(),
                ['3.5']
            )
            self.validation_results.append(result)
            
        except Exception as e:
            self.logger.error(f"Adapter validation failed: {str(e)}")
            self.validation_results.append(ValidationResult(
                component="adapters",
                test_name="Adapter Validation",
                status="failed",
                execution_time=0.0,
                details=f"Adapter validation failed: {str(e)}",
                requirements_validated=['3.1', '3.2', '3.3', '3.4', '3.5', '3.6'],
                errors=[str(e)]
            ))
    
    async def _validate_pipeline(self):
        """Validate complete analysis pipeline (Requirements 4.x)"""
        self.logger.info("Validating analysis pipeline...")
        
        try:
            # Test pipeline configuration (4.1)
            result = await self._run_validation_test(
                "pipeline_configuration",
                "Pipeline Configuration Test",
                lambda: self.test_orchestrator.test_configuration_validation(),
                ['4.1']
            )
            self.validation_results.append(result)
            
            # Test pipeline execution (4.2)
            result = await self._run_validation_test(
                "pipeline_execution",
                "Pipeline Execution Test",
                lambda: self.test_orchestrator.test_complete_pipeline(),
                ['4.2']
            )
            self.validation_results.append(result)
            
            # Test pipeline reporting (4.3)
            result = await self._run_validation_test(
                "pipeline_reporting",
                "Pipeline Reporting Test",
                lambda: self.test_orchestrator.test_report_generation(),
                ['4.3']
            )
            self.validation_results.append(result)
            
            # Test pipeline metrics (4.4)
            result = await self._run_validation_test(
                "pipeline_metrics",
                "Pipeline Metrics Test",
                lambda: self.metrics_collector.test_metrics_collection(),
                ['4.4']
            )
            self.validation_results.append(result)
            
            # Test pipeline error handling (4.5)
            result = await self._run_validation_test(
                "pipeline_error_handling",
                "Pipeline Error Handling Test",
                lambda: self.test_orchestrator.test_error_scenarios(),
                ['4.5']
            )
            self.validation_results.append(result)
            
            # Test result storage (4.6)
            result = await self._run_validation_test(
                "pipeline_result_storage",
                "Pipeline Result Storage Test",
                lambda: self.test_orchestrator.test_result_storage(),
                ['4.6']
            )
            self.validation_results.append(result)
            
        except Exception as e:
            self.logger.error(f"Pipeline validation failed: {str(e)}")
            self.validation_results.append(ValidationResult(
                component="pipeline",
                test_name="Pipeline Validation",
                status="failed",
                execution_time=0.0,
                details=f"Pipeline validation failed: {str(e)}",
                requirements_validated=['4.1', '4.2', '4.3', '4.4', '4.5', '4.6'],
                errors=[str(e)]
            ))
    
    async def _validate_documentation(self):
        """Validate documentation accuracy and completeness"""
        self.logger.info("Validating documentation...")
        
        try:
            # Validate usage documentation
            result = await self._run_validation_test(
                "documentation_usage",
                "Usage Documentation Validation",
                lambda: self._validate_usage_documentation(),
                ['8.1', '8.6']
            )
            self.validation_results.append(result)
            
            # Validate API documentation
            result = await self._run_validation_test(
                "documentation_api",
                "API Documentation Validation",
                lambda: self._validate_api_documentation(),
                ['8.2']
            )
            self.validation_results.append(result)
            
            # Validate examples
            result = await self._run_validation_test(
                "documentation_examples",
                "Examples Validation",
                lambda: self._validate_examples(),
                ['8.3']
            )
            self.validation_results.append(result)
            
        except Exception as e:
            self.logger.error(f"Documentation validation failed: {str(e)}")
            self.validation_results.append(ValidationResult(
                component="documentation",
                test_name="Documentation Validation",
                status="failed",
                execution_time=0.0,
                details=f"Documentation validation failed: {str(e)}",
                requirements_validated=['8.1', '8.2', '8.3', '8.4', '8.5', '8.6'],
                errors=[str(e)]
            ))
    
    async def _run_validation_test(
        self, 
        component: str, 
        test_name: str, 
        test_func, 
        requirements: List[str]
    ) -> ValidationResult:
        """Run a single validation test and return results"""
        start_time = time.time()
        
        try:
            self.logger.info(f"Running {test_name}...")
            
            # Execute the test function
            if asyncio.iscoroutinefunction(test_func):
                result = await test_func()
            else:
                result = test_func()
            
            execution_time = time.time() - start_time
            
            # Validate real execution if applicable
            real_execution_valid = True
            if hasattr(result, 'execution_data'):
                real_execution_valid = self.real_execution_validator.validate_real_execution(
                    result.execution_data
                )
            
            status = "passed" if result and real_execution_valid else "failed"
            details = f"Test completed successfully" if status == "passed" else "Test failed validation"
            
            return ValidationResult(
                component=component,
                test_name=test_name,
                status=status,
                execution_time=execution_time,
                details=details,
                requirements_validated=requirements
            )
            
        except Exception as e:
            execution_time = time.time() - start_time
            self.logger.error(f"{test_name} failed: {str(e)}")
            
            return ValidationResult(
                component=component,
                test_name=test_name,
                status="failed",
                execution_time=execution_time,
                details=f"Test failed with error: {str(e)}",
                requirements_validated=requirements,
                errors=[str(e)]
            )
    
    def _test_adapter_error_scenarios(self) -> bool:
        """Test adapter error handling scenarios"""
        try:
            # Test invalid adapter configuration
            lm_eval_validator = LMEvalAdapterValidator()
            
            # Test with invalid task
            try:
                lm_eval_validator.test_builtin_tasks(['invalid_task_name'])
                return False  # Should have failed
            except Exception:
                pass  # Expected failure
            
            # Test with missing dependencies
            try:
                swe_bench_validator = SWEBenchAdapterValidator()
                swe_bench_validator.validate_integration()
            except Exception:
                pass  # May fail due to dependencies
            
            return True
            
        except Exception as e:
            self.logger.error(f"Adapter error scenario test failed: {str(e)}")
            return False
    
    def _validate_usage_documentation(self) -> bool:
        """Validate usage documentation accuracy"""
        try:
            docs_path = Path("docs/usage.md")
            if not docs_path.exists():
                return False
            
            # Check if documentation contains required sections
            content = docs_path.read_text()
            required_sections = [
                "Installation",
                "Quick Start",
                "CLI Usage",
                "API Usage",
                "Examples"
            ]
            
            for section in required_sections:
                if section not in content:
                    self.logger.warning(f"Missing section in usage.md: {section}")
                    return False
            
            return True
            
        except Exception as e:
            self.logger.error(f"Usage documentation validation failed: {str(e)}")
            return False
    
    def _validate_api_documentation(self) -> bool:
        """Validate API documentation accuracy"""
        try:
            docs_path = Path("docs/api_specification.md")
            if not docs_path.exists():
                return False
            
            # Check if API documentation contains required endpoints
            content = docs_path.read_text()
            required_endpoints = [
                "/api/v1/evaluations",
                "/api/v1/tasks",
                "/api/v1/adapters"
            ]
            
            for endpoint in required_endpoints:
                if endpoint not in content:
                    self.logger.warning(f"Missing endpoint in API docs: {endpoint}")
                    return False
            
            return True
            
        except Exception as e:
            self.logger.error(f"API documentation validation failed: {str(e)}")
            return False
    
    def _validate_examples(self) -> bool:
        """Validate that examples work correctly"""
        try:
            examples_dir = Path("examples")
            if not examples_dir.exists():
                return False
            
            # Test CLI examples
            cli_examples = examples_dir / "cli"
            if cli_examples.exists():
                for example_file in cli_examples.glob("*.sh"):
                    # Basic syntax check
                    result = subprocess.run(
                        ["bash", "-n", str(example_file)],
                        capture_output=True,
                        text=True
                    )
                    if result.returncode != 0:
                        self.logger.error(f"Syntax error in {example_file}: {result.stderr}")
                        return False
            
            # Test API examples
            api_examples = examples_dir / "api"
            if api_examples.exists():
                for example_file in api_examples.glob("*.sh"):
                    # Basic syntax check
                    result = subprocess.run(
                        ["bash", "-n", str(example_file)],
                        capture_output=True,
                        text=True
                    )
                    if result.returncode != 0:
                        self.logger.error(f"Syntax error in {example_file}: {result.stderr}")
                        return False
            
            return True
            
        except Exception as e:
            self.logger.error(f"Examples validation failed: {str(e)}")
            return False
    
    async def _validate_requirements_coverage(self):
        """Validate that all requirements are covered by tests"""
        self.logger.info("Validating requirements coverage...")
        
        # Get all requirements that should be covered
        all_requirements = set()
        for req_list in self.requirements_map.values():
            all_requirements.update(req_list)
        
        # Get requirements covered by validation results
        covered_requirements = set()
        for result in self.validation_results:
            covered_requirements.update(result.requirements_validated)
        
        # Check coverage
        uncovered_requirements = all_requirements - covered_requirements
        
        if uncovered_requirements:
            self.logger.warning(f"Uncovered requirements: {uncovered_requirements}")
            
        coverage_result = ValidationResult(
            component="requirements",
            test_name="Requirements Coverage Validation",
            status="passed" if not uncovered_requirements else "failed",
            execution_time=0.0,
            details=f"Coverage: {len(covered_requirements)}/{len(all_requirements)} requirements",
            requirements_validated=list(covered_requirements)
        )
        
        if uncovered_requirements:
            coverage_result.errors = [f"Uncovered requirements: {list(uncovered_requirements)}"]
        
        self.validation_results.append(coverage_result)
    
    def _generate_test_suite_results(self) -> IntegrationTestSuite:
        """Generate final test suite results"""
        total_tests = len(self.validation_results)
        passed_tests = sum(1 for r in self.validation_results if r.status == "passed")
        failed_tests = sum(1 for r in self.validation_results if r.status == "failed")
        skipped_tests = sum(1 for r in self.validation_results if r.status == "skipped")
        
        total_execution_time = self.end_time - self.start_time if self.end_time else 0.0
        
        # Build requirements coverage map
        requirements_coverage = {}
        for req_id in self.requirements_map.keys():
            requirements_coverage[req_id] = any(
                req_id in result.requirements_validated and result.status == "passed"
                for result in self.validation_results
            )
        
        # Build component status map
        component_status = {}
        for result in self.validation_results:
            if result.component not in component_status:
                component_status[result.component] = "passed"
            if result.status == "failed":
                component_status[result.component] = "failed"
        
        # Determine final status
        final_status = "passed" if failed_tests == 0 else "failed"
        
        return IntegrationTestSuite(
            total_tests=total_tests,
            passed_tests=passed_tests,
            failed_tests=failed_tests,
            skipped_tests=skipped_tests,
            total_execution_time=total_execution_time,
            validation_results=self.validation_results,
            requirements_coverage=requirements_coverage,
            component_status=component_status,
            final_status=final_status
        )
    
    async def _generate_final_report(self, test_suite: IntegrationTestSuite):
        """Generate comprehensive final validation report"""
        try:
            # Generate detailed report
            report_data = {
                'test_suite_summary': asdict(test_suite),
                'detailed_results': [asdict(result) for result in self.validation_results],
                'requirements_analysis': self._analyze_requirements_coverage(test_suite),
                'component_analysis': self._analyze_component_status(test_suite),
                'recommendations': self._generate_recommendations(test_suite)
            }
            
            # Save JSON report
            report_path = Path("final_integration_validation_report.json")
            with open(report_path, 'w') as f:
                json.dump(report_data, f, indent=2, default=str)
            
            # Generate human-readable report
            await self._generate_human_readable_report(test_suite, report_data)
            
            self.logger.info(f"Final validation report saved to {report_path}")
            
        except Exception as e:
            self.logger.error(f"Failed to generate final report: {str(e)}")
    
    def _analyze_requirements_coverage(self, test_suite: IntegrationTestSuite) -> Dict[str, Any]:
        """Analyze requirements coverage"""
        total_requirements = len(test_suite.requirements_coverage)
        covered_requirements = sum(1 for covered in test_suite.requirements_coverage.values() if covered)
        coverage_percentage = (covered_requirements / total_requirements) * 100 if total_requirements > 0 else 0
        
        uncovered = [req for req, covered in test_suite.requirements_coverage.items() if not covered]
        
        return {
            'total_requirements': total_requirements,
            'covered_requirements': covered_requirements,
            'coverage_percentage': coverage_percentage,
            'uncovered_requirements': uncovered
        }
    
    def _analyze_component_status(self, test_suite: IntegrationTestSuite) -> Dict[str, Any]:
        """Analyze component status"""
        total_components = len(test_suite.component_status)
        passed_components = sum(1 for status in test_suite.component_status.values() if status == "passed")
        
        failed_components = [comp for comp, status in test_suite.component_status.items() if status == "failed"]
        
        return {
            'total_components': total_components,
            'passed_components': passed_components,
            'failed_components': failed_components,
            'success_rate': (passed_components / total_components) * 100 if total_components > 0 else 0
        }
    
    def _generate_recommendations(self, test_suite: IntegrationTestSuite) -> List[str]:
        """Generate recommendations based on test results"""
        recommendations = []
        
        if test_suite.failed_tests > 0:
            recommendations.append("Address failed test cases before deployment")
        
        if test_suite.requirements_coverage and not all(test_suite.requirements_coverage.values()):
            recommendations.append("Implement tests for uncovered requirements")
        
        if any(status == "failed" for status in test_suite.component_status.values()):
            recommendations.append("Fix failing components before production use")
        
        if test_suite.total_execution_time > 1800:  # 30 minutes
            recommendations.append("Consider optimizing test execution time")
        
        return recommendations
    
    async def _generate_human_readable_report(self, test_suite: IntegrationTestSuite, report_data: Dict[str, Any]):
        """Generate human-readable validation report"""
        report_content = f"""
# Final Integration and Validation Report

## Executive Summary

**Overall Status**: {test_suite.final_status.upper()}
**Total Tests**: {test_suite.total_tests}
**Passed**: {test_suite.passed_tests}
**Failed**: {test_suite.failed_tests}
**Skipped**: {test_suite.skipped_tests}
**Execution Time**: {test_suite.total_execution_time:.2f} seconds

## Requirements Coverage

**Coverage**: {report_data['requirements_analysis']['coverage_percentage']:.1f}%
**Covered Requirements**: {report_data['requirements_analysis']['covered_requirements']}/{report_data['requirements_analysis']['total_requirements']}

### Uncovered Requirements
{chr(10).join(f"- {req}" for req in report_data['requirements_analysis']['uncovered_requirements'])}

## Component Status

**Success Rate**: {report_data['component_analysis']['success_rate']:.1f}%

### Component Results
{chr(10).join(f"- {comp}: {status}" for comp, status in test_suite.component_status.items())}

### Failed Components
{chr(10).join(f"- {comp}" for comp in report_data['component_analysis']['failed_components'])}

## Detailed Test Results

{chr(10).join(self._format_test_result(result) for result in test_suite.validation_results)}

## Recommendations

{chr(10).join(f"- {rec}" for rec in report_data['recommendations'])}

## Next Steps

1. Address any failed test cases
2. Implement tests for uncovered requirements
3. Fix failing components
4. Re-run validation to confirm fixes
5. Proceed with deployment if all tests pass

---
Report generated on: {time.strftime('%Y-%m-%d %H:%M:%S')}
"""
        
        # Save human-readable report
        report_path = Path("FINAL_INTEGRATION_VALIDATION_REPORT.md")
        with open(report_path, 'w') as f:
            f.write(report_content)
        
        self.logger.info(f"Human-readable report saved to {report_path}")
    
    def _format_test_result(self, result: ValidationResult) -> str:
        """Format a single test result for the report"""
        status_emoji = "✅" if result.status == "passed" else "❌" if result.status == "failed" else "⏭️"
        
        formatted = f"""
### {status_emoji} {result.test_name}

**Component**: {result.component}
**Status**: {result.status}
**Execution Time**: {result.execution_time:.2f}s
**Requirements**: {', '.join(result.requirements_validated)}
**Details**: {result.details}
"""
        
        if result.errors:
            formatted += f"\n**Errors**:\n{chr(10).join(f'- {error}' for error in result.errors)}"
        
        return formatted


async def main():
    """Main entry point for final integration validation"""
    logging.basicConfig(
        level=logging.INFO,
        format='%(asctime)s - %(name)s - %(levelname)s - %(message)s'
    )
    
    try:
        validator = FinalIntegrationValidator()
        test_suite = await validator.run_complete_validation()
        
        print(f"\n{'='*60}")
        print("FINAL INTEGRATION VALIDATION RESULTS")
        print(f"{'='*60}")
        print(f"Overall Status: {test_suite.final_status.upper()}")
        print(f"Total Tests: {test_suite.total_tests}")
        print(f"Passed: {test_suite.passed_tests}")
        print(f"Failed: {test_suite.failed_tests}")
        print(f"Skipped: {test_suite.skipped_tests}")
        print(f"Execution Time: {test_suite.total_execution_time:.2f}s")
        print(f"{'='*60}")
        
        # Exit with appropriate code
        sys.exit(0 if test_suite.final_status == "passed" else 1)
        
    except Exception as e:
        logging.error(f"Final validation failed: {str(e)}")
        sys.exit(1)


if __name__ == "__main__":
    asyncio.run(main())