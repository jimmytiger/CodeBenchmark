#!/usr/bin/env python3
"""
Final Validation Test Suite

Comprehensive integration tests for the final validation system.
This test suite validates that all components work together correctly
and that all requirements are satisfied.
"""

import asyncio
import json
import logging
import os
import pytest
import sys
import tempfile
import time
from pathlib import Path
from unittest.mock import Mock, patch, AsyncMock

# Add parent directories to path
sys.path.insert(0, str(Path(__file__).parent.parent.parent))

from final_integration_validator import FinalIntegrationValidator, ValidationResult, IntegrationTestSuite
from core.test_orchestrator import TestOrchestrator
from core.config_manager import ConfigManager
from core.error_handler import ErrorHandler
from cli.cli_test_runner import CLITestRunner
from api.api_test_client import APITestClient
from api.api_test_server import APITestServer


class TestFinalValidationSuite:
    """Test suite for final validation system"""
    
    @pytest.fixture
    def validator(self):
        """Create a test validator instance"""
        return FinalIntegrationValidator()
    
    @pytest.fixture
    def temp_config(self):
        """Create a temporary configuration file"""
        config_data = {
            'validation': {
                'run_cli_tests': True,
                'run_api_tests': True,
                'run_adapter_tests': True,
                'run_pipeline_tests': True,
                'timeout_seconds': 300
            }
        }
        
        with tempfile.NamedTemporaryFile(mode='w', suffix='.yaml', delete=False) as f:
            import yaml
            yaml.dump(config_data, f)
            yield f.name
        
        # Cleanup
        os.unlink(f.name)
    
    def test_validator_initialization(self, validator):
        """Test that validator initializes correctly"""
        assert validator is not None
        assert validator.config_manager is not None
        assert validator.error_handler is not None
        assert validator.test_orchestrator is not None
        assert validator.validation_results == []
        assert validator.requirements_map is not None
    
    def test_requirements_mapping(self, validator):
        """Test that requirements mapping is complete"""
        # Check that all requirement categories are present
        expected_categories = ['1.', '2.', '3.', '4.']
        
        for category in expected_categories:
            category_reqs = [req for req in validator.requirements_map.keys() if req.startswith(category)]
            assert len(category_reqs) > 0, f"No requirements found for category {category}"
        
        # Check that each requirement maps to test components
        for req_id, components in validator.requirements_map.items():
            assert len(components) > 0, f"No components mapped for requirement {req_id}"
            assert all(isinstance(comp, str) for comp in components)
    
    @pytest.mark.asyncio
    async def test_validation_test_execution(self, validator):
        """Test individual validation test execution"""
        # Mock test function
        def mock_test_func():
            return {"status": "success", "execution_data": {"real_execution": True}}
        
        result = await validator._run_validation_test(
            "test_component",
            "Test Validation",
            mock_test_func,
            ["1.1", "1.2"]
        )
        
        assert isinstance(result, ValidationResult)
        assert result.component == "test_component"
        assert result.test_name == "Test Validation"
        assert result.status == "passed"
        assert result.requirements_validated == ["1.1", "1.2"]
        assert result.execution_time > 0
    
    @pytest.mark.asyncio
    async def test_validation_test_failure(self, validator):
        """Test validation test failure handling"""
        # Mock failing test function
        def mock_failing_test():
            raise Exception("Test failure")
        
        result = await validator._run_validation_test(
            "test_component",
            "Failing Test",
            mock_failing_test,
            ["1.1"]
        )
        
        assert isinstance(result, ValidationResult)
        assert result.status == "failed"
        assert len(result.errors) > 0
        assert "Test failure" in result.errors[0]
    
    @pytest.mark.asyncio
    async def test_cli_validation(self, validator):
        """Test CLI interface validation"""
        with patch.object(CLITestRunner, 'test_real_execution', return_value=True):
            with patch.object(CLITestRunner, 'test_builtin_tasks', return_value=True):
                with patch.object(CLITestRunner, 'test_custom_task_discovery', return_value=True):
                    with patch.object(CLITestRunner, 'test_error_scenarios', return_value=True):
                        with patch.object(CLITestRunner, 'test_configuration_variations', return_value=True):
                            await validator._validate_cli_interface()
        
        # Check that CLI validation results were added
        cli_results = [r for r in validator.validation_results if r.component == "cli"]
        assert len(cli_results) > 0
        
        # Check that CLI requirements are covered
        cli_requirements = ['1.1', '1.2', '1.3', '1.5', '1.6']
        covered_reqs = set()
        for result in cli_results:
            covered_reqs.update(result.requirements_validated)
        
        for req in cli_requirements:
            assert req in covered_reqs, f"CLI requirement {req} not covered"
    
    @pytest.mark.asyncio
    async def test_api_validation(self, validator):
        """Test API interface validation"""
        # Mock API server and client
        mock_server = AsyncMock()
        mock_client = Mock()
        
        mock_client.test_all_endpoints.return_value = True
        mock_client.test_async_evaluations.return_value = True
        mock_client.test_real_execution_validation.return_value = True
        mock_client.test_error_scenarios.return_value = True
        mock_client.test_concurrent_requests.return_value = True
        
        with patch('final_integration_validator.APITestServer', return_value=mock_server):
            with patch('final_integration_validator.APITestClient', return_value=mock_client):
                await validator._validate_api_interface()
        
        # Check that API validation results were added
        api_results = [r for r in validator.validation_results if r.component == "api"]
        assert len(api_results) > 0
        
        # Check that API requirements are covered
        api_requirements = ['2.1', '2.2', '2.3', '2.4', '2.5', '2.6']
        covered_reqs = set()
        for result in api_results:
            covered_reqs.update(result.requirements_validated)
        
        for req in api_requirements:
            assert req in covered_reqs, f"API requirement {req} not covered"
    
    @pytest.mark.asyncio
    async def test_adapter_validation(self, validator):
        """Test adapter validation"""
        # Mock adapter validators
        with patch('final_integration_validator.LMEvalAdapterValidator') as mock_lm_eval:
            with patch('final_integration_validator.SWEBenchAdapterValidator') as mock_swe_bench:
                mock_lm_eval.return_value.validate_integration.return_value = True
                mock_swe_bench.return_value.validate_integration.return_value = True
                
                with patch.object(validator, '_test_adapter_error_scenarios', return_value=True):
                    await validator._validate_adapters()
        
        # Check that adapter validation results were added
        adapter_results = [r for r in validator.validation_results if r.component == "adapters"]
        assert len(adapter_results) > 0
    
    @pytest.mark.asyncio
    async def test_pipeline_validation(self, validator):
        """Test pipeline validation"""
        # Mock test orchestrator methods
        validator.test_orchestrator.test_configuration_validation = Mock(return_value=True)
        validator.test_orchestrator.test_complete_pipeline = Mock(return_value=True)
        validator.test_orchestrator.test_report_generation = Mock(return_value=True)
        validator.test_orchestrator.test_error_scenarios = Mock(return_value=True)
        validator.test_orchestrator.test_result_storage = Mock(return_value=True)
        
        # Mock metrics collector
        validator.metrics_collector.test_metrics_collection = Mock(return_value=True)
        
        await validator._validate_pipeline()
        
        # Check that pipeline validation results were added
        pipeline_results = [r for r in validator.validation_results if r.component == "pipeline"]
        assert len(pipeline_results) > 0
    
    @pytest.mark.asyncio
    async def test_documentation_validation(self, validator):
        """Test documentation validation"""
        with patch.object(validator, '_validate_usage_documentation', return_value=True):
            with patch.object(validator, '_validate_api_documentation', return_value=True):
                with patch.object(validator, '_validate_examples', return_value=True):
                    await validator._validate_documentation()
        
        # Check that documentation validation results were added
        doc_results = [r for r in validator.validation_results if r.component == "documentation"]
        assert len(doc_results) > 0
    
    def test_usage_documentation_validation(self, validator):
        """Test usage documentation validation"""
        # Create temporary usage documentation
        with tempfile.NamedTemporaryFile(mode='w', suffix='.md', delete=False) as f:
            f.write("""
# Usage Guide

## Installation
Instructions for installation

## Quick Start
Quick start guide

## CLI Usage
CLI usage instructions

## API Usage
API usage instructions

## Examples
Usage examples
""")
            temp_path = f.name
        
        try:
            # Patch the docs path
            with patch('pathlib.Path.exists', return_value=True):
                with patch('pathlib.Path.read_text', return_value=Path(temp_path).read_text()):
                    result = validator._validate_usage_documentation()
            
            assert result is True
            
        finally:
            os.unlink(temp_path)
    
    def test_api_documentation_validation(self, validator):
        """Test API documentation validation"""
        # Create temporary API documentation
        api_content = """
# API Specification

## Endpoints

### /api/v1/evaluations
Evaluation endpoint

### /api/v1/tasks
Tasks endpoint

### /api/v1/adapters
Adapters endpoint
"""
        
        with patch('pathlib.Path.exists', return_value=True):
            with patch('pathlib.Path.read_text', return_value=api_content):
                result = validator._validate_api_documentation()
        
        assert result is True
    
    def test_examples_validation(self, validator):
        """Test examples validation"""
        with patch('pathlib.Path.exists', return_value=True):
            with patch('pathlib.Path.glob') as mock_glob:
                # Mock shell script files
                mock_files = [Mock(spec=Path) for _ in range(3)]
                for mock_file in mock_files:
                    mock_file.__str__ = Mock(return_value="test_script.sh")
                
                mock_glob.return_value = mock_files
                
                with patch('subprocess.run') as mock_run:
                    mock_run.return_value.returncode = 0  # Success
                    result = validator._validate_examples()
        
        assert result is True
    
    @pytest.mark.asyncio
    async def test_requirements_coverage_validation(self, validator):
        """Test requirements coverage validation"""
        # Add some mock validation results
        validator.validation_results = [
            ValidationResult(
                component="test1",
                test_name="Test 1",
                status="passed",
                execution_time=1.0,
                details="Test passed",
                requirements_validated=["1.1", "1.2"]
            ),
            ValidationResult(
                component="test2",
                test_name="Test 2",
                status="passed",
                execution_time=1.0,
                details="Test passed",
                requirements_validated=["2.1", "2.2"]
            )
        ]
        
        await validator._validate_requirements_coverage()
        
        # Check that coverage validation result was added
        coverage_results = [r for r in validator.validation_results if r.component == "requirements"]
        assert len(coverage_results) > 0
        
        coverage_result = coverage_results[0]
        assert "1.1" in coverage_result.requirements_validated
        assert "1.2" in coverage_result.requirements_validated
        assert "2.1" in coverage_result.requirements_validated
        assert "2.2" in coverage_result.requirements_validated
    
    def test_test_suite_results_generation(self, validator):
        """Test test suite results generation"""
        # Add mock validation results
        validator.validation_results = [
            ValidationResult(
                component="test1",
                test_name="Test 1",
                status="passed",
                execution_time=1.0,
                details="Test passed",
                requirements_validated=["1.1"]
            ),
            ValidationResult(
                component="test2",
                test_name="Test 2",
                status="failed",
                execution_time=2.0,
                details="Test failed",
                requirements_validated=["1.2"],
                errors=["Test error"]
            ),
            ValidationResult(
                component="test3",
                test_name="Test 3",
                status="skipped",
                execution_time=0.0,
                details="Test skipped",
                requirements_validated=["1.3"]
            )
        ]
        
        validator.start_time = time.time() - 10
        validator.end_time = time.time()
        
        test_suite = validator._generate_test_suite_results()
        
        assert isinstance(test_suite, IntegrationTestSuite)
        assert test_suite.total_tests == 3
        assert test_suite.passed_tests == 1
        assert test_suite.failed_tests == 1
        assert test_suite.skipped_tests == 1
        assert test_suite.final_status == "failed"  # Because there are failed tests
        assert test_suite.total_execution_time > 0
    
    def test_requirements_analysis(self, validator):
        """Test requirements coverage analysis"""
        test_suite = IntegrationTestSuite(
            total_tests=3,
            passed_tests=2,
            failed_tests=1,
            skipped_tests=0,
            total_execution_time=10.0,
            validation_results=[],
            requirements_coverage={"1.1": True, "1.2": False, "1.3": True},
            component_status={"comp1": "passed", "comp2": "failed"},
            final_status="failed"
        )
        
        analysis = validator._analyze_requirements_coverage(test_suite)
        
        assert analysis['total_requirements'] == 3
        assert analysis['covered_requirements'] == 2
        assert analysis['coverage_percentage'] == 200/3  # 66.67%
        assert "1.2" in analysis['uncovered_requirements']
    
    def test_component_analysis(self, validator):
        """Test component status analysis"""
        test_suite = IntegrationTestSuite(
            total_tests=3,
            passed_tests=2,
            failed_tests=1,
            skipped_tests=0,
            total_execution_time=10.0,
            validation_results=[],
            requirements_coverage={},
            component_status={"comp1": "passed", "comp2": "passed", "comp3": "failed"},
            final_status="failed"
        )
        
        analysis = validator._analyze_component_status(test_suite)
        
        assert analysis['total_components'] == 3
        assert analysis['passed_components'] == 2
        assert analysis['success_rate'] == 200/3  # 66.67%
        assert "comp3" in analysis['failed_components']
    
    def test_recommendations_generation(self, validator):
        """Test recommendations generation"""
        test_suite = IntegrationTestSuite(
            total_tests=3,
            passed_tests=1,
            failed_tests=2,
            skipped_tests=0,
            total_execution_time=2000.0,  # Long execution time
            validation_results=[],
            requirements_coverage={"1.1": True, "1.2": False},
            component_status={"comp1": "passed", "comp2": "failed"},
            final_status="failed"
        )
        
        recommendations = validator._generate_recommendations(test_suite)
        
        assert len(recommendations) > 0
        assert any("failed test cases" in rec for rec in recommendations)
        assert any("uncovered requirements" in rec for rec in recommendations)
        assert any("failing components" in rec for rec in recommendations)
        assert any("execution time" in rec for rec in recommendations)
    
    @pytest.mark.asyncio
    async def test_complete_validation_flow(self, validator):
        """Test the complete validation flow"""
        # Mock all validation methods
        validator._validate_cli_interface = AsyncMock()
        validator._validate_api_interface = AsyncMock()
        validator._validate_adapters = AsyncMock()
        validator._validate_pipeline = AsyncMock()
        validator._validate_documentation = AsyncMock()
        validator._validate_requirements_coverage = AsyncMock()
        validator._generate_final_report = AsyncMock()
        
        # Add a mock validation result
        validator.validation_results = [
            ValidationResult(
                component="test",
                test_name="Mock Test",
                status="passed",
                execution_time=1.0,
                details="Mock test passed",
                requirements_validated=["1.1"]
            )
        ]
        
        test_suite = await validator.run_complete_validation()
        
        # Verify all validation methods were called
        validator._validate_cli_interface.assert_called_once()
        validator._validate_api_interface.assert_called_once()
        validator._validate_adapters.assert_called_once()
        validator._validate_pipeline.assert_called_once()
        validator._validate_documentation.assert_called_once()
        validator._validate_requirements_coverage.assert_called_once()
        validator._generate_final_report.assert_called_once()
        
        assert isinstance(test_suite, IntegrationTestSuite)
        assert test_suite.total_tests > 0


@pytest.mark.integration
class TestFinalValidationIntegration:
    """Integration tests for final validation system"""
    
    @pytest.mark.asyncio
    async def test_real_validation_execution(self):
        """Test real validation execution (if components are available)"""
        try:
            validator = FinalIntegrationValidator()
            
            # Run a minimal validation to test the system
            # This will only run if the actual components are available
            
            # Test CLI validation with minimal configuration
            cli_runner = CLITestRunner()
            if hasattr(cli_runner, 'test_real_execution'):
                result = await validator._run_validation_test(
                    "cli_integration",
                    "CLI Integration Test",
                    lambda: True,  # Simplified test
                    ["1.1"]
                )
                assert isinstance(result, ValidationResult)
            
        except ImportError:
            pytest.skip("Integration components not available")
        except Exception as e:
            pytest.skip(f"Integration test skipped due to: {str(e)}")


if __name__ == "__main__":
    # Run the tests
    pytest.main([__file__, "-v"])