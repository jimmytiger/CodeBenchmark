#!/usr/bin/env python3
"""
Demonstration script for the report generation and documentation system.

This script shows how to use all components of the report generation system:
- TestReportGenerator for comprehensive reports
- UsageDocumentationGenerator for usage.md
- APIDocumentationGenerator for API specifications  
- PerformanceAnalyzer for execution analysis
"""

import json
import logging
from datetime import datetime
from pathlib import Path

from EvaluationEngineV1_0_tests.models.test_models import (
    TestResult, ValidationResult, ExecutionMetrics, 
    TestStatus, TestType, AdapterType
)
from EvaluationEngineV1_0_tests.reports.test_report_generator import TestReportGenerator
from EvaluationEngineV1_0_tests.reports.usage_documentation_generator import UsageDocumentationGenerator
from EvaluationEngineV1_0_tests.reports.api_documentation_generator import APIDocumentationGenerator
from EvaluationEngineV1_0_tests.reports.performance_analyzer import PerformanceAnalyzer


def setup_logging():
    """Setup logging for the demonstration."""
    logging.basicConfig(
        level=logging.INFO,
        format='%(asctime)s - %(name)s - %(levelname)s - %(message)s'
    )


def create_sample_data():
    """Create sample test data for demonstration."""
    
    # Sample test results
    test_results = [
        TestResult(
            test_id="cli_test_001",
            test_type=TestType.CLI,
            name="CLI Builtin Tasks Test",
            status=TestStatus.PASSED,
            execution_time=45.2,
            real_execution_validated=True,
            metrics={
                "accuracy": 0.85,
                "memory_usage": 512.0,
                "api_response_time": 2.1
            },
            artifacts=["cli_test_001.log", "cli_test_001_results.json"]
        ),
        TestResult(
            test_id="api_test_001",
            test_type=TestType.API,
            name="API Evaluation Endpoint Test",
            status=TestStatus.PASSED,
            execution_time=32.1,
            real_execution_validated=True,
            metrics={
                "response_time": 1.8,
                "memory_usage": 256.0,
                "throughput": 15.5
            },
            artifacts=["api_test_001.log"]
        ),
        TestResult(
            test_id="adapter_test_001",
            test_type=TestType.ADAPTER,
            name="LM Eval Adapter Integration Test",
            status=TestStatus.PASSED,
            execution_time=78.5,
            real_execution_validated=True,
            metrics={
                "integration_score": 0.95,
                "memory_usage": 1024.0,
                "dependency_check": 1.0
            }
        ),
        TestResult(
            test_id="adapter_test_002",
            test_type=TestType.ADAPTER,
            name="SWE-bench Adapter Integration Test",
            status=TestStatus.FAILED,
            execution_time=120.5,
            real_execution_validated=False,
            error_details="DependencyError: swe_bench package not found. Please install with: pip install swe_bench",
            metrics={
                "integration_score": 0.0,
                "memory_usage": 128.0
            }
        ),
        TestResult(
            test_id="performance_test_001",
            test_type=TestType.PERFORMANCE,
            name="Load Testing - 10 Concurrent Requests",
            status=TestStatus.PASSED,
            execution_time=95.3,
            real_execution_validated=True,
            metrics={
                "avg_response_time": 3.2,
                "max_response_time": 8.1,
                "min_response_time": 1.5,
                "memory_usage": 768.0,
                "cpu_usage": 45.2
            }
        )
    ]
    
    # Sample validation results
    validation_results = [
        ValidationResult(
            adapter_name="lm_eval_adapter",
            adapter_type=AdapterType.LM_EVAL,
            integration_status=TestStatus.PASSED,
            dependencies_installed=True,
            test_results=[test_results[2]],  # Reference to adapter test
            performance_metrics={
                "avg_execution_time": 78.5,
                "memory_usage": 1024.0,
                "success_rate": 1.0
            },
            issues_found=[],
            recommendations=[
                "Consider implementing caching for repeated task evaluations",
                "Monitor memory usage for large datasets"
            ],
            validation_time=78.5
        ),
        ValidationResult(
            adapter_name="swe_bench_adapter",
            adapter_type=AdapterType.SWE_BENCH,
            integration_status=TestStatus.FAILED,
            dependencies_installed=False,
            test_results=[test_results[3]],  # Reference to failed adapter test
            performance_metrics={},
            issues_found=[
                "DependencyError: swe_bench package not found",
                "ConfigurationError: SWE-bench environment not configured"
            ],
            recommendations=[
                "Install swe_bench package: pip install swe_bench",
                "Configure SWE-bench environment variables",
                "Verify Docker installation for containerized execution"
            ],
            validation_time=120.5
        )
    ]
    
    # Sample execution metrics
    execution_metrics = ExecutionMetrics(
        total_execution_time=371.6,  # Sum of all test execution times
        task_execution_times={
            "cli_test_001": 45.2,
            "api_test_001": 32.1,
            "adapter_test_001": 78.5,
            "adapter_test_002": 120.5,
            "performance_test_001": 95.3
        },
        memory_usage={
            "cli_test_001": 512.0,
            "api_test_001": 256.0,
            "adapter_test_001": 1024.0,
            "adapter_test_002": 128.0,
            "performance_test_001": 768.0
        },
        api_response_times={
            "evaluation_endpoint": 1.8,
            "status_endpoint": 0.5,
            "results_endpoint": 2.1,
            "tasks_endpoint": 0.8,
            "adapters_endpoint": 1.2
        },
        success_rates={
            "cli": 1.0,
            "api": 1.0,
            "adapter": 0.5,
            "performance": 1.0
        },
        error_rates={
            "cli": 0.0,
            "api": 0.0,
            "adapter": 0.5,
            "performance": 0.0
        }
    )
    
    return test_results, validation_results, execution_metrics


def demonstrate_test_report_generator(test_results, validation_results, execution_metrics, output_dir):
    """Demonstrate TestReportGenerator functionality."""
    print("\n" + "="*60)
    print("DEMONSTRATING TEST REPORT GENERATOR")
    print("="*60)
    
    generator = TestReportGenerator(output_dir / "test_reports")
    
    # Generate test summary report
    print("\n1. Generating test summary report...")
    test_summary = generator.generate_test_summary(test_results)
    print(f"   - Total tests: {test_summary.summary['total_tests']}")
    print(f"   - Success rate: {test_summary.summary['success_rate']}%")
    print(f"   - Real execution rate: {test_summary.summary['real_execution_rate']}%")
    
    # Save in multiple formats
    json_path = generator.save_report(test_summary, "test_summary.json", "json")
    html_path = generator.save_report(test_summary, "test_summary.html", "html")
    md_path = generator.save_report(test_summary, "test_summary.md", "markdown")
    
    print(f"   - Saved JSON report: {json_path}")
    print(f"   - Saved HTML report: {html_path}")
    print(f"   - Saved Markdown report: {md_path}")
    
    # Generate performance report
    print("\n2. Generating performance report...")
    performance_report = generator.generate_performance_report(execution_metrics)
    print(f"   - Performance score: {performance_report.summary['performance_score']:.1f}/100")
    print(f"   - Total execution time: {performance_report.summary['total_execution_time']}s")
    
    perf_path = generator.save_report(performance_report, "performance_report.json", "json")
    print(f"   - Saved performance report: {perf_path}")
    
    # Generate adapter validation report
    print("\n3. Generating adapter validation report...")
    adapter_report = generator.generate_adapter_validation_report(validation_results)
    print(f"   - Adapters tested: {adapter_report.summary['total_adapters']}")
    print(f"   - Integration success rate: {adapter_report.summary['integration_success_rate']}%")
    
    adapter_path = generator.save_report(adapter_report, "adapter_validation.json", "json")
    print(f"   - Saved adapter report: {adapter_path}")


def demonstrate_usage_documentation_generator(test_results, output_dir):
    """Demonstrate UsageDocumentationGenerator functionality."""
    print("\n" + "="*60)
    print("DEMONSTRATING USAGE DOCUMENTATION GENERATOR")
    print("="*60)
    
    generator = UsageDocumentationGenerator(output_dir / "docs")
    
    # Generate comprehensive usage guide
    print("\n1. Generating comprehensive usage guide...")
    usage_guide = generator.generate_usage_guide(test_results)
    print(f"   - Generated usage guide ({len(usage_guide)} characters)")
    
    # Save usage guide
    usage_path = generator.save_usage_guide(usage_guide)
    print(f"   - Saved usage guide: {usage_path}")
    
    # Generate examples
    print("\n2. Generating code examples...")
    successful_tests = [t for t in test_results if t.status == TestStatus.PASSED]
    examples = generator.generate_examples(successful_tests)
    print(f"   - Generated examples from {len(successful_tests)} successful tests")
    
    # Generate troubleshooting guide
    print("\n3. Generating troubleshooting guide...")
    failed_tests = [t for t in test_results if t.status == TestStatus.FAILED]
    troubleshooting = generator.generate_troubleshooting_guide(failed_tests)
    print(f"   - Generated troubleshooting guide for {len(failed_tests)} failed tests")


def demonstrate_api_documentation_generator(test_results, output_dir):
    """Demonstrate APIDocumentationGenerator functionality."""
    print("\n" + "="*60)
    print("DEMONSTRATING API DOCUMENTATION GENERATOR")
    print("="*60)
    
    generator = APIDocumentationGenerator(output_dir / "api_docs")
    
    # Generate OpenAPI specification
    print("\n1. Generating OpenAPI specification...")
    openapi_spec = generator.generate_openapi_specification(test_results)
    print(f"   - Generated OpenAPI {openapi_spec['openapi']} specification")
    print(f"   - API title: {openapi_spec['info']['title']}")
    print(f"   - Number of endpoints: {len(openapi_spec['paths'])}")
    
    # Save OpenAPI spec
    openapi_path = generator.save_openapi_specification(openapi_spec)
    print(f"   - Saved OpenAPI spec: {openapi_path}")
    
    # Generate endpoint documentation
    print("\n2. Generating endpoint documentation...")
    endpoint_docs = generator.generate_endpoint_documentation(test_results)
    print(f"   - Generated endpoint documentation ({len(endpoint_docs)} characters)")
    
    # Save endpoint docs
    endpoint_path = generator.save_endpoint_documentation(endpoint_docs)
    print(f"   - Saved endpoint docs: {endpoint_path}")
    
    # Generate curl examples
    print("\n3. Generating curl examples...")
    curl_examples = generator.generate_curl_examples(test_results)
    print(f"   - Generated curl examples ({len(curl_examples)} characters)")
    
    # Save curl examples
    curl_path = generator.save_curl_examples(curl_examples)
    print(f"   - Saved curl examples: {curl_path}")


def demonstrate_performance_analyzer(execution_metrics, test_results, output_dir):
    """Demonstrate PerformanceAnalyzer functionality."""
    print("\n" + "="*60)
    print("DEMONSTRATING PERFORMANCE ANALYZER")
    print("="*60)
    
    analyzer = PerformanceAnalyzer(output_dir / "performance")
    
    # Analyze execution metrics
    print("\n1. Analyzing execution metrics...")
    analysis = analyzer.analyze_execution_metrics(execution_metrics)
    print(f"   - Overall performance score: {analysis.overall_score:.1f}/100")
    print(f"   - Number of bottlenecks identified: {len(analysis.bottlenecks)}")
    print(f"   - Number of recommendations: {len(analysis.recommendations)}")
    
    # Show bottlenecks
    if analysis.bottlenecks:
        print("\n   Identified bottlenecks:")
        for bottleneck in analysis.bottlenecks:
            print(f"     - {bottleneck['type']} ({bottleneck['severity']} severity)")
    
    # Show top recommendations
    if analysis.recommendations:
        print("\n   Top recommendations:")
        for i, rec in enumerate(analysis.recommendations[:3], 1):
            print(f"     {i}. {rec}")
    
    # Generate detailed performance report
    print("\n2. Generating detailed performance report...")
    detailed_report = analyzer.generate_performance_report(analysis)
    print(f"   - Generated detailed report ({len(detailed_report)} characters)")
    
    # Save analysis
    analysis_path = analyzer.save_analysis_report(analysis)
    print(f"   - Saved performance analysis: {analysis_path}")
    
    # Analyze test results performance
    print("\n3. Analyzing test results performance...")
    test_analysis = analyzer.analyze_test_results_performance(test_results)
    print(f"   - Test results performance score: {test_analysis.overall_score:.1f}/100")
    
    # Demonstrate performance comparison
    print("\n4. Demonstrating performance comparison...")
    # Create baseline metrics (slightly worse performance)
    baseline_metrics = ExecutionMetrics(
        total_execution_time=420.0,  # 13% slower
        task_execution_times={k: v * 1.13 for k, v in execution_metrics.task_execution_times.items()},
        memory_usage={k: v * 1.2 for k, v in execution_metrics.memory_usage.items()},
        api_response_times={k: v * 1.15 for k, v in execution_metrics.api_response_times.items()},
        success_rates={k: v * 0.95 for k, v in execution_metrics.success_rates.items()},
        error_rates={k: v * 1.1 for k, v in execution_metrics.error_rates.items()}
    )
    
    comparison = analyzer.compare_performance(execution_metrics, baseline_metrics)
    print(f"   - Performance comparison completed")
    print(f"   - Overall improvement: {comparison['overall']['overall_improvement']}")
    print(f"   - Metrics improved: {comparison['overall']['improvements']}/4")


def demonstrate_integration_workflow(test_results, validation_results, execution_metrics, output_dir):
    """Demonstrate complete integration workflow."""
    print("\n" + "="*60)
    print("DEMONSTRATING COMPLETE INTEGRATION WORKFLOW")
    print("="*60)
    
    # Initialize all generators
    test_generator = TestReportGenerator(output_dir / "reports")
    usage_generator = UsageDocumentationGenerator(output_dir / "docs")
    api_generator = APIDocumentationGenerator(output_dir / "api")
    performance_analyzer = PerformanceAnalyzer(output_dir / "performance")
    
    print("\n1. Generating all reports simultaneously...")
    
    # Generate all reports
    reports = {
        'test_summary': test_generator.generate_test_summary(test_results),
        'performance_report': test_generator.generate_performance_report(execution_metrics),
        'adapter_validation': test_generator.generate_adapter_validation_report(validation_results),
        'usage_guide': usage_generator.generate_usage_guide(test_results),
        'openapi_spec': api_generator.generate_openapi_specification(),
        'endpoint_docs': api_generator.generate_endpoint_documentation(),
        'performance_analysis': performance_analyzer.analyze_execution_metrics(execution_metrics)
    }
    
    print(f"   - Generated {len(reports)} different reports/documents")
    
    print("\n2. Saving all reports in multiple formats...")
    
    # Save reports in different formats
    saved_files = []
    
    # Test reports
    saved_files.append(test_generator.save_report(reports['test_summary'], format="json"))
    saved_files.append(test_generator.save_report(reports['performance_report'], format="html"))
    saved_files.append(test_generator.save_report(reports['adapter_validation'], format="markdown"))
    
    # Documentation
    saved_files.append(usage_generator.save_usage_guide(reports['usage_guide']))
    saved_files.append(api_generator.save_openapi_specification(reports['openapi_spec']))
    saved_files.append(api_generator.save_endpoint_documentation(reports['endpoint_docs']))
    
    # Performance analysis
    saved_files.append(performance_analyzer.save_analysis_report(reports['performance_analysis']))
    
    print(f"   - Saved {len(saved_files)} files")
    
    print("\n3. Generating summary of all generated files...")
    total_size = sum(f.stat().st_size for f in saved_files if f.exists())
    print(f"   - Total files generated: {len(saved_files)}")
    print(f"   - Total size: {total_size / 1024:.1f} KB")
    
    print("\n   Generated files:")
    for file_path in saved_files:
        if file_path.exists():
            size_kb = file_path.stat().st_size / 1024
            print(f"     - {file_path.name} ({size_kb:.1f} KB)")


def main():
    """Main demonstration function."""
    print("EvaluationEngineV1_0 Report Generation System Demonstration")
    print("=" * 60)
    
    # Setup
    setup_logging()
    output_dir = Path("demo_reports")
    output_dir.mkdir(exist_ok=True)
    
    # Create sample data
    print("\nCreating sample test data...")
    test_results, validation_results, execution_metrics = create_sample_data()
    print(f"Created {len(test_results)} test results, {len(validation_results)} validation results")
    
    # Demonstrate each component
    demonstrate_test_report_generator(test_results, validation_results, execution_metrics, output_dir)
    demonstrate_usage_documentation_generator(test_results, output_dir)
    demonstrate_api_documentation_generator(test_results, output_dir)
    demonstrate_performance_analyzer(execution_metrics, test_results, output_dir)
    
    # Demonstrate integration
    demonstrate_integration_workflow(test_results, validation_results, execution_metrics, output_dir)
    
    print("\n" + "="*60)
    print("DEMONSTRATION COMPLETED SUCCESSFULLY")
    print("="*60)
    print(f"\nAll generated files are available in: {output_dir.absolute()}")
    print("\nYou can now:")
    print("1. Review the generated reports in different formats")
    print("2. Open the HTML reports in a web browser")
    print("3. Use the OpenAPI specification with tools like Swagger UI")
    print("4. Follow the usage guide for step-by-step instructions")
    print("5. Review performance analysis for optimization opportunities")


if __name__ == "__main__":
    main()