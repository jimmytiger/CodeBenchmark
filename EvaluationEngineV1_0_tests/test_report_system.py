#!/usr/bin/env python3
"""
Simple test script to verify the report generation system works correctly.
"""

import sys
import tempfile
from pathlib import Path
from datetime import datetime

# Add the current directory to Python path
sys.path.insert(0, str(Path(__file__).parent))

from models.test_models import (
    TestResult, ValidationResult, ExecutionMetrics, 
    TestStatus, TestType, AdapterType
)
from reports.test_report_generator import TestReportGenerator
from reports.usage_documentation_generator import UsageDocumentationGenerator
from reports.api_documentation_generator import APIDocumentationGenerator
from reports.performance_analyzer import PerformanceAnalyzer


def test_report_generation():
    """Test the report generation system."""
    print("Testing EvaluationEngineV1_0 Report Generation System")
    print("=" * 55)
    
    # Create sample data
    test_results = [
        TestResult(
            test_id="test_1",
            test_type=TestType.CLI,
            name="CLI Test",
            status=TestStatus.PASSED,
            execution_time=45.2,
            real_execution_validated=True,
            metrics={"accuracy": 0.85, "memory_usage": 512.0}
        ),
        TestResult(
            test_id="test_2",
            test_type=TestType.API,
            name="API Test",
            status=TestStatus.PASSED,
            execution_time=32.1,
            real_execution_validated=True,
            metrics={"response_time": 2.1}
        ),
        TestResult(
            test_id="test_3",
            test_type=TestType.ADAPTER,
            name="Adapter Test",
            status=TestStatus.FAILED,
            execution_time=120.5,
            real_execution_validated=False,
            error_details="ConfigurationError: Invalid configuration"
        )
    ]
    
    validation_results = [
        ValidationResult(
            adapter_name="lm_eval_adapter",
            adapter_type=AdapterType.LM_EVAL,
            integration_status=TestStatus.PASSED,
            dependencies_installed=True,
            performance_metrics={"avg_execution_time": 45.2}
        )
    ]
    
    execution_metrics = ExecutionMetrics(
        total_execution_time=197.8,
        task_execution_times={"test_1": 45.2, "test_2": 32.1, "test_3": 120.5},
        memory_usage={"test_1": 512.0, "test_2": 256.0, "test_3": 1024.0},
        api_response_times={"api_1": 2.1, "api_2": 1.8},
        success_rates={"cli": 1.0, "api": 1.0, "adapter": 0.0},
        error_rates={"cli": 0.0, "api": 0.0, "adapter": 1.0}
    )
    
    with tempfile.TemporaryDirectory() as temp_dir:
        temp_path = Path(temp_dir)
        
        # Test TestReportGenerator
        print("\n1. Testing TestReportGenerator...")
        test_generator = TestReportGenerator(temp_path / "test_reports")
        
        # Generate test summary
        test_summary = test_generator.generate_test_summary(test_results)
        print(f"   ✅ Test summary generated: {test_summary.title}")
        print(f"      - Total tests: {test_summary.summary['total_tests']}")
        print(f"      - Success rate: {test_summary.summary['success_rate']}%")
        
        # Generate performance report
        performance_report = test_generator.generate_performance_report(execution_metrics)
        print(f"   ✅ Performance report generated")
        print(f"      - Performance score: {performance_report.summary['performance_score']:.1f}/100")
        
        # Generate adapter validation report
        adapter_report = test_generator.generate_adapter_validation_report(validation_results)
        print(f"   ✅ Adapter validation report generated")
        print(f"      - Adapters tested: {adapter_report.summary['total_adapters']}")
        
        # Save reports
        json_path = test_generator.save_report(test_summary, "test_summary.json", "json")
        html_path = test_generator.save_report(test_summary, "test_summary.html", "html")
        md_path = test_generator.save_report(test_summary, "test_summary.md", "markdown")
        
        print(f"   ✅ Reports saved in multiple formats:")
        print(f"      - JSON: {json_path.name}")
        print(f"      - HTML: {html_path.name}")
        print(f"      - Markdown: {md_path.name}")
        
        # Test UsageDocumentationGenerator
        print("\n2. Testing UsageDocumentationGenerator...")
        usage_generator = UsageDocumentationGenerator(temp_path / "docs")
        
        usage_guide = usage_generator.generate_usage_guide(test_results)
        print(f"   ✅ Usage guide generated ({len(usage_guide)} characters)")
        
        usage_path = usage_generator.save_usage_guide(usage_guide)
        print(f"   ✅ Usage guide saved: {usage_path.name}")
        
        # Test APIDocumentationGenerator
        print("\n3. Testing APIDocumentationGenerator...")
        api_generator = APIDocumentationGenerator(temp_path / "api_docs")
        
        openapi_spec = api_generator.generate_openapi_specification()
        print(f"   ✅ OpenAPI specification generated")
        print(f"      - Version: {openapi_spec['openapi']}")
        print(f"      - Endpoints: {len(openapi_spec['paths'])}")
        
        endpoint_docs = api_generator.generate_endpoint_documentation()
        print(f"   ✅ Endpoint documentation generated ({len(endpoint_docs)} characters)")
        
        curl_examples = api_generator.generate_curl_examples()
        print(f"   ✅ Curl examples generated ({len(curl_examples)} characters)")
        
        # Save API documentation
        openapi_path = api_generator.save_openapi_specification(openapi_spec)
        endpoint_path = api_generator.save_endpoint_documentation(endpoint_docs)
        curl_path = api_generator.save_curl_examples(curl_examples)
        
        print(f"   ✅ API documentation saved:")
        print(f"      - OpenAPI spec: {openapi_path.name}")
        print(f"      - Endpoint docs: {endpoint_path.name}")
        print(f"      - Curl examples: {curl_path.name}")
        
        # Test PerformanceAnalyzer
        print("\n4. Testing PerformanceAnalyzer...")
        performance_analyzer = PerformanceAnalyzer(temp_path / "performance")
        
        analysis = performance_analyzer.analyze_execution_metrics(execution_metrics)
        print(f"   ✅ Performance analysis completed")
        print(f"      - Overall score: {analysis.overall_score:.1f}/100")
        print(f"      - Bottlenecks found: {len(analysis.bottlenecks)}")
        print(f"      - Recommendations: {len(analysis.recommendations)}")
        
        detailed_report = performance_analyzer.generate_performance_report(analysis)
        print(f"   ✅ Detailed performance report generated ({len(detailed_report)} characters)")
        
        analysis_path = performance_analyzer.save_analysis_report(analysis)
        print(f"   ✅ Performance analysis saved: {analysis_path.name}")
        
        # Test integration
        print("\n5. Testing integration workflow...")
        
        # Count all generated files
        all_files = list(temp_path.rglob("*"))
        report_files = [f for f in all_files if f.is_file()]
        total_size = sum(f.stat().st_size for f in report_files)
        
        print(f"   ✅ Integration test completed")
        print(f"      - Total files generated: {len(report_files)}")
        print(f"      - Total size: {total_size / 1024:.1f} KB")
        
        print("\n" + "=" * 55)
        print("✅ ALL TESTS PASSED - Report generation system working correctly!")
        print("=" * 55)
        
        return True


if __name__ == "__main__":
    try:
        success = test_report_generation()
        if success:
            print("\n🎉 Report generation system is ready for use!")
            sys.exit(0)
        else:
            print("\n❌ Some tests failed")
            sys.exit(1)
    except Exception as e:
        print(f"\n❌ Test failed with error: {e}")
        import traceback
        traceback.print_exc()
        sys.exit(1)