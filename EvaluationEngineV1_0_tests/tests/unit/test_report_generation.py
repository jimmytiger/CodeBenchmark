"""
Unit tests for the report generation and documentation system.
"""

import json
import tempfile
from datetime import datetime
from pathlib import Path
from unittest.mock import Mock, patch

import pytest

from EvaluationEngineV1_0_tests.models.test_models import TestResult, ValidationResult, ExecutionMetrics, TestStatus, TestType, AdapterType
from EvaluationEngineV1_0_tests.reports.test_report_generator import TestReportGenerator, Report
from EvaluationEngineV1_0_tests.reports.usage_documentation_generator import UsageDocumentationGenerator
from EvaluationEngineV1_0_tests.reports.api_documentation_generator import APIDocumentationGenerator
from EvaluationEngineV1_0_tests.reports.performance_analyzer import PerformanceAnalyzer, PerformanceAnalysis


class TestReportGenerationSystem:
    """Test suite for the report generation and documentation system."""
    
    @pytest.fixture
    def temp_dir(self):
        """Create temporary directory for test outputs."""
        with tempfile.TemporaryDirectory() as temp_dir:
            yield Path(temp_dir)
    
    @pytest.fixture
    def sample_test_results(self):
        """Create sample test results for testing."""
        return [
            TestResult(
                test_id="test_1",
                test_type=TestType.CLI,
                name="CLI Test 1",
                status=TestStatus.PASSED,
                execution_time=45.2,
                real_execution_validated=True,
                metrics={"accuracy": 0.85, "memory_usage": 512.0}
            ),
            TestResult(
                test_id="test_2",
                test_type=TestType.API,
                name="API Test 1",
                status=TestStatus.PASSED,
                execution_time=32.1,
                real_execution_validated=True,
                metrics={"response_time": 2.1, "memory_usage": 256.0}
            ),
            TestResult(
                test_id="test_3",
                test_type=TestType.ADAPTER,
                name="Adapter Test 1",
                status=TestStatus.FAILED,
                execution_time=120.5,
                real_execution_validated=False,
                error_details="ConfigurationError: Invalid adapter configuration"
            )
        ]
    
    @pytest.fixture
    def sample_validation_results(self):
        """Create sample validation results for testing."""
        return [
            ValidationResult(
                adapter_name="lm_eval_adapter",
                adapter_type=AdapterType.LM_EVAL,
                integration_status=TestStatus.PASSED,
                dependencies_installed=True,
                performance_metrics={"avg_execution_time": 45.2, "memory_usage": 512.0},
                issues_found=[]
            ),
            ValidationResult(
                adapter_name="swe_bench_adapter",
                adapter_type=AdapterType.SWE_BENCH,
                integration_status=TestStatus.FAILED,
                dependencies_installed=False,
                performance_metrics={},
                issues_found=["DependencyError: Missing swe_bench package"]
            )
        ]
    
    @pytest.fixture
    def sample_execution_metrics(self):
        """Create sample execution metrics for testing."""
        return ExecutionMetrics(
            total_execution_time=197.8,
            task_execution_times={
                "test_1": 45.2,
                "test_2": 32.1,
                "test_3": 120.5
            },
            memory_usage={
                "test_1": 512.0,
                "test_2": 256.0,
                "test_3": 1024.0
            },
            api_response_times={
                "api_1": 2.1,
                "api_2": 1.8,
                "api_3": 3.2
            },
            success_rates={
                "cli": 1.0,
                "api": 1.0,
                "adapter": 0.0
            },
            error_rates={
                "cli": 0.0,
                "api": 0.0,
                "adapter": 1.0
            }
        )


class TestTestReportGenerator(TestReportGenerationSystem):
    """Test TestReportGenerator functionality."""
    
    def test_initialization(self, temp_dir):
        """Test TestReportGenerator initialization."""
        generator = TestReportGenerator(temp_dir)
        
        assert generator.output_dir == temp_dir
        assert temp_dir.exists()
    
    def test_generate_test_summary(self, temp_dir, sample_test_results):
        """Test test summary report generation."""
        generator = TestReportGenerator(temp_dir)
        
        report = generator.generate_test_summary(sample_test_results)
        
        assert isinstance(report, Report)
        assert report.title == "Test Execution Summary Report"
        assert report.summary['total_tests'] == 3
        assert report.summary['passed_tests'] == 2
        assert report.summary['failed_tests'] == 1
        assert report.summary['success_rate'] == 66.67
        assert 'test_types' in report.details
        assert 'error_patterns' in report.details
    
    def test_generate_performance_report(self, temp_dir, sample_execution_metrics):
        """Test performance report generation."""
        generator = TestReportGenerator(temp_dir)
        
        report = generator.generate_performance_report(sample_execution_metrics)
        
        assert isinstance(report, Report)
        assert report.title == "Performance Analysis Report"
        assert report.summary['total_execution_time'] == 197.8
        assert report.summary['total_tasks_analyzed'] == 3
        assert 'slowest_tasks' in report.details
        assert 'fastest_tasks' in report.details
    
    def test_generate_adapter_validation_report(self, temp_dir, sample_validation_results):
        """Test adapter validation report generation."""
        generator = TestReportGenerator(temp_dir)
        
        report = generator.generate_adapter_validation_report(sample_validation_results)
        
        assert isinstance(report, Report)
        assert report.title == "Adapter Validation Report"
        assert report.summary['total_adapters'] == 2
        assert report.summary['successful_integrations'] == 1
        assert report.summary['failed_integrations'] == 1
        assert 'adapter_metrics' in report.details
    
    def test_save_report_json(self, temp_dir, sample_test_results):
        """Test saving report in JSON format."""
        generator = TestReportGenerator(temp_dir)
        report = generator.generate_test_summary(sample_test_results)
        
        filepath = generator.save_report(report, "test_report.json", "json")
        
        assert filepath.exists()
        assert filepath.suffix == ".json"
        
        # Verify JSON content
        with open(filepath) as f:
            data = json.load(f)
        
        assert data['title'] == report.title
        assert data['summary']['total_tests'] == 3
    
    def test_save_report_html(self, temp_dir, sample_test_results):
        """Test saving report in HTML format."""
        generator = TestReportGenerator(temp_dir)
        report = generator.generate_test_summary(sample_test_results)
        
        filepath = generator.save_report(report, "test_report.html", "html")
        
        assert filepath.exists()
        assert filepath.suffix == ".html"
        
        # Verify HTML content
        with open(filepath) as f:
            content = f.read()
        
        assert "<html>" in content
        assert report.title in content
    
    def test_save_report_markdown(self, temp_dir, sample_test_results):
        """Test saving report in Markdown format."""
        generator = TestReportGenerator(temp_dir)
        report = generator.generate_test_summary(sample_test_results)
        
        filepath = generator.save_report(report, "test_report.md", "markdown")
        
        assert filepath.exists()
        assert filepath.suffix == ".md"
        
        # Verify Markdown content
        with open(filepath) as f:
            content = f.read()
        
        assert f"# {report.title}" in content
        assert "## Summary" in content


class TestUsageDocumentationGenerator(TestReportGenerationSystem):
    """Test UsageDocumentationGenerator functionality."""
    
    def test_initialization(self, temp_dir):
        """Test UsageDocumentationGenerator initialization."""
        generator = UsageDocumentationGenerator(temp_dir)
        
        assert generator.output_dir == temp_dir
        assert temp_dir.exists()
    
    def test_generate_usage_guide(self, temp_dir, sample_test_results):
        """Test usage guide generation."""
        generator = UsageDocumentationGenerator(temp_dir)
        
        guide = generator.generate_usage_guide(sample_test_results)
        
        assert isinstance(guide, str)
        assert "# EvaluationEngineV1_0 Testing Framework Usage Guide" in guide
        assert "## Overview" in guide
        assert "## CLI Testing Interface" in guide
        assert "## API Testing Interface" in guide
        assert "## Troubleshooting" in guide
    
    def test_generate_examples(self, temp_dir, sample_test_results):
        """Test examples generation."""
        generator = UsageDocumentationGenerator(temp_dir)
        successful_tests = [t for t in sample_test_results if t.status == TestStatus.PASSED]
        
        examples = generator.generate_examples(successful_tests)
        
        assert isinstance(examples, str)
        assert "CLI Testing Example" in examples or "API Testing Example" in examples
    
    def test_generate_troubleshooting_guide(self, temp_dir, sample_test_results):
        """Test troubleshooting guide generation."""
        generator = UsageDocumentationGenerator(temp_dir)
        failed_tests = [t for t in sample_test_results if t.status == TestStatus.FAILED]
        
        guide = generator.generate_troubleshooting_guide(failed_tests)
        
        assert isinstance(guide, str)
        if failed_tests:
            assert "ConfigurationError" in guide
    
    def test_save_usage_guide(self, temp_dir, sample_test_results):
        """Test saving usage guide to file."""
        generator = UsageDocumentationGenerator(temp_dir)
        guide = generator.generate_usage_guide(sample_test_results)
        
        filepath = generator.save_usage_guide(guide)
        
        assert filepath.exists()
        assert filepath.name == "usage.md"
        
        # Verify content
        with open(filepath) as f:
            content = f.read()
        
        assert guide == content


class TestAPIDocumentationGenerator(TestReportGenerationSystem):
    """Test APIDocumentationGenerator functionality."""
    
    def test_initialization(self, temp_dir):
        """Test APIDocumentationGenerator initialization."""
        generator = APIDocumentationGenerator(temp_dir)
        
        assert generator.output_dir == temp_dir
        assert temp_dir.exists()
    
    def test_generate_openapi_specification(self, temp_dir):
        """Test OpenAPI specification generation."""
        generator = APIDocumentationGenerator(temp_dir)
        
        spec = generator.generate_openapi_specification()
        
        assert isinstance(spec, dict)
        assert spec['openapi'] == '3.0.0'
        assert 'info' in spec
        assert 'paths' in spec
        assert 'components' in spec
        assert spec['info']['title'] == "EvaluationEngineV1_0 Testing Framework API"
    
    def test_generate_endpoint_documentation(self, temp_dir):
        """Test endpoint documentation generation."""
        generator = APIDocumentationGenerator(temp_dir)
        
        docs = generator.generate_endpoint_documentation()
        
        assert isinstance(docs, str)
        assert "# API Endpoint Documentation" in docs
        assert "## Endpoints" in docs
        assert "### Evaluations" in docs
        assert "POST" in docs and "GET" in docs
    
    def test_generate_curl_examples(self, temp_dir):
        """Test curl examples generation."""
        generator = APIDocumentationGenerator(temp_dir)
        
        examples = generator.generate_curl_examples()
        
        assert isinstance(examples, str)
        assert "# API Testing with curl" in examples
        assert "curl -X POST" in examples
        assert "http://localhost:8080" in examples
    
    def test_save_openapi_specification(self, temp_dir):
        """Test saving OpenAPI specification to file."""
        generator = APIDocumentationGenerator(temp_dir)
        spec = generator.generate_openapi_specification()
        
        filepath = generator.save_openapi_specification(spec)
        
        assert filepath.exists()
        assert filepath.name == "openapi.json"
        
        # Verify JSON content
        with open(filepath) as f:
            data = json.load(f)
        
        assert data == spec
    
    def test_save_endpoint_documentation(self, temp_dir):
        """Test saving endpoint documentation to file."""
        generator = APIDocumentationGenerator(temp_dir)
        docs = generator.generate_endpoint_documentation()
        
        filepath = generator.save_endpoint_documentation(docs)
        
        assert filepath.exists()
        assert filepath.name == "api_endpoints.md"
        
        # Verify content
        with open(filepath) as f:
            content = f.read()
        
        assert content == docs


class TestPerformanceAnalyzer(TestReportGenerationSystem):
    """Test PerformanceAnalyzer functionality."""
    
    def test_initialization(self, temp_dir):
        """Test PerformanceAnalyzer initialization."""
        analyzer = PerformanceAnalyzer(temp_dir)
        
        assert analyzer.output_dir == temp_dir
        assert temp_dir.exists()
        assert 'execution_time' in analyzer.thresholds
        assert 'memory_usage' in analyzer.thresholds
    
    def test_analyze_execution_metrics(self, temp_dir, sample_execution_metrics):
        """Test execution metrics analysis."""
        analyzer = PerformanceAnalyzer(temp_dir)
        
        analysis = analyzer.analyze_execution_metrics(sample_execution_metrics)
        
        assert isinstance(analysis, PerformanceAnalysis)
        assert 0 <= analysis.overall_score <= 100
        assert 'total_execution_time' in analysis.execution_summary
        assert isinstance(analysis.bottlenecks, list)
        assert isinstance(analysis.recommendations, list)
    
    def test_analyze_test_results_performance(self, temp_dir, sample_test_results):
        """Test performance analysis from test results."""
        analyzer = PerformanceAnalyzer(temp_dir)
        
        analysis = analyzer.analyze_test_results_performance(sample_test_results)
        
        assert isinstance(analysis, PerformanceAnalysis)
        assert analysis.overall_score >= 0
        assert len(analysis.execution_summary) > 0
    
    def test_generate_performance_report(self, temp_dir, sample_execution_metrics):
        """Test performance report generation."""
        analyzer = PerformanceAnalyzer(temp_dir)
        analysis = analyzer.analyze_execution_metrics(sample_execution_metrics)
        
        report = analyzer.generate_performance_report(analysis)
        
        assert isinstance(report, str)
        assert "# Performance Analysis Report" in report
        assert "## Executive Summary" in report
        assert "## Key Metrics" in report
        assert "## Performance Bottlenecks" in report
        assert "## Recommendations" in report
    
    def test_save_analysis_report(self, temp_dir, sample_execution_metrics):
        """Test saving performance analysis to file."""
        analyzer = PerformanceAnalyzer(temp_dir)
        analysis = analyzer.analyze_execution_metrics(sample_execution_metrics)
        
        filepath = analyzer.save_analysis_report(analysis)
        
        assert filepath.exists()
        assert filepath.suffix == ".json"
        
        # Verify JSON content
        with open(filepath) as f:
            data = json.load(f)
        
        assert data['overall_score'] == analysis.overall_score
    
    def test_compare_performance(self, temp_dir, sample_execution_metrics):
        """Test performance comparison functionality."""
        analyzer = PerformanceAnalyzer(temp_dir)
        
        # Create baseline metrics (slightly different)
        baseline_metrics = ExecutionMetrics(
            total_execution_time=220.0,
            task_execution_times={"test_1": 50.0, "test_2": 35.0, "test_3": 135.0},
            memory_usage={"test_1": 600.0, "test_2": 300.0, "test_3": 1200.0},
            api_response_times={"api_1": 2.5, "api_2": 2.0, "api_3": 3.5},
            success_rates={"cli": 0.9, "api": 0.95, "adapter": 0.1},
            error_rates={"cli": 0.1, "api": 0.05, "adapter": 0.9}
        )
        
        comparison = analyzer.compare_performance(sample_execution_metrics, baseline_metrics)
        
        assert isinstance(comparison, dict)
        assert 'execution_time' in comparison
        assert 'memory_usage' in comparison
        assert 'overall' in comparison
        assert 'improvement_rate' in comparison['overall']
    
    def test_performance_scoring(self, temp_dir):
        """Test performance scoring algorithms."""
        analyzer = PerformanceAnalyzer(temp_dir)
        
        # Test execution time scoring
        excellent_score = analyzer._score_execution_time(25.0)
        good_score = analyzer._score_execution_time(45.0)
        poor_score = analyzer._score_execution_time(400.0)
        
        assert excellent_score == 100.0
        assert good_score == 85.0
        assert poor_score < 50.0
        
        # Test memory usage scoring
        excellent_memory = analyzer._score_memory_usage(400.0)
        poor_memory = analyzer._score_memory_usage(5000.0)
        
        assert excellent_memory == 100.0
        assert poor_memory < 50.0
    
    def test_bottleneck_identification(self, temp_dir):
        """Test bottleneck identification."""
        analyzer = PerformanceAnalyzer(temp_dir)
        
        # Create metrics with obvious bottlenecks
        problematic_metrics = ExecutionMetrics(
            total_execution_time=500.0,  # Very slow
            memory_usage={"test_1": 5000.0},  # High memory usage
            api_response_times={"api_1": 15.0},  # Slow API
            error_rates={"component_1": 0.3}  # High error rate
        )
        
        bottlenecks = analyzer._identify_bottlenecks(problematic_metrics)
        
        assert len(bottlenecks) > 0
        assert any(b.type == 'execution_time' for b in bottlenecks)
        assert any(b.severity == 'critical' for b in bottlenecks)


class TestIntegrationReportGeneration(TestReportGenerationSystem):
    """Test integration between different report generation components."""
    
    def test_complete_report_generation_workflow(self, temp_dir, sample_test_results, 
                                                sample_validation_results, sample_execution_metrics):
        """Test complete report generation workflow."""
        # Initialize all generators
        test_generator = TestReportGenerator(temp_dir / "test_reports")
        usage_generator = UsageDocumentationGenerator(temp_dir / "docs")
        api_generator = APIDocumentationGenerator(temp_dir / "api_docs")
        performance_analyzer = PerformanceAnalyzer(temp_dir / "performance")
        
        # Generate all reports
        test_summary = test_generator.generate_test_summary(sample_test_results)
        performance_report = test_generator.generate_performance_report(sample_execution_metrics)
        adapter_report = test_generator.generate_adapter_validation_report(sample_validation_results)
        
        usage_guide = usage_generator.generate_usage_guide(sample_test_results)
        api_spec = api_generator.generate_openapi_specification()
        api_docs = api_generator.generate_endpoint_documentation()
        
        performance_analysis = performance_analyzer.analyze_execution_metrics(sample_execution_metrics)
        performance_detailed = performance_analyzer.generate_performance_report(performance_analysis)
        
        # Save all reports
        test_generator.save_report(test_summary, format="json")
        test_generator.save_report(performance_report, format="html")
        test_generator.save_report(adapter_report, format="markdown")
        
        usage_generator.save_usage_guide(usage_guide)
        api_generator.save_openapi_specification(api_spec)
        api_generator.save_endpoint_documentation(api_docs)
        
        performance_analyzer.save_analysis_report(performance_analysis)
        
        # Verify all files were created
        assert len(list((temp_dir / "test_reports").glob("*.json"))) >= 1
        assert len(list((temp_dir / "test_reports").glob("*.html"))) >= 1
        assert len(list((temp_dir / "test_reports").glob("*.md"))) >= 1
        assert (temp_dir / "docs" / "usage.md").exists()
        assert (temp_dir / "api_docs" / "openapi.json").exists()
        assert (temp_dir / "api_docs" / "api_endpoints.md").exists()
        assert len(list((temp_dir / "performance").glob("*.json"))) >= 1
    
    def test_report_consistency(self, temp_dir, sample_test_results):
        """Test consistency between different report formats."""
        generator = TestReportGenerator(temp_dir)
        report = generator.generate_test_summary(sample_test_results)
        
        # Save in different formats
        json_path = generator.save_report(report, "report.json", "json")
        html_path = generator.save_report(report, "report.html", "html")
        md_path = generator.save_report(report, "report.md", "markdown")
        
        # Verify JSON content
        with open(json_path) as f:
            json_data = json.load(f)
        
        # Verify HTML contains key information
        with open(html_path) as f:
            html_content = f.read()
        
        # Verify Markdown contains key information
        with open(md_path) as f:
            md_content = f.read()
        
        # Check consistency
        assert json_data['title'] == report.title
        assert report.title in html_content
        assert report.title in md_content
        assert str(json_data['summary']['total_tests']) in html_content
        assert str(json_data['summary']['total_tests']) in md_content


if __name__ == "__main__":
    pytest.main([__file__, "-v"])