"""
Result formatter for CLI test outputs.
"""

import json
import csv
import logging
from typing import Dict, List, Any, Optional
from pathlib import Path
from datetime import datetime
import yaml

from ..models.test_models import TestResult, TestSuiteResults


class CLIResultFormatter:
    """Formats CLI test results for display and output."""
    
    def __init__(self):
        self.logger = logging.getLogger(f"{__name__}.CLIResultFormatter")
    
    def format_test_result(self, test_result: TestResult, 
                          format_type: str = "json") -> str:
        """Format a single test result."""
        if format_type == "json":
            return self._format_json(test_result)
        elif format_type == "yaml":
            return self._format_yaml(test_result)
        elif format_type == "table":
            return self._format_table([test_result])
        elif format_type == "csv":
            return self._format_csv([test_result])
        else:
            raise ValueError(f"Unsupported format type: {format_type}")
    
    def format_test_suite_results(self, suite_results: TestSuiteResults,
                                 format_type: str = "json") -> str:
        """Format test suite results."""
        if format_type == "json":
            return self._format_suite_json(suite_results)
        elif format_type == "yaml":
            return self._format_suite_yaml(suite_results)
        elif format_type == "table":
            return self._format_suite_table(suite_results)
        elif format_type == "csv":
            return self._format_suite_csv(suite_results)
        else:
            raise ValueError(f"Unsupported format type: {format_type}")
    
    def save_results(self, results: Any, output_path: Path, 
                    format_type: str = "json") -> None:
        """Save results to file."""
        output_path.parent.mkdir(parents=True, exist_ok=True)
        
        if isinstance(results, TestResult):
            content = self.format_test_result(results, format_type)
        elif isinstance(results, TestSuiteResults):
            content = self.format_test_suite_results(results, format_type)
        else:
            # Generic formatting
            if format_type == "json":
                content = json.dumps(results, indent=2, default=str)
            elif format_type == "yaml":
                content = yaml.dump(results, default_flow_style=False)
            else:
                content = str(results)
        
        with open(output_path, 'w', encoding='utf-8') as f:
            f.write(content)
        
        self.logger.info(f"Results saved to {output_path}")
    
    def display_results(self, results: Any, format_type: str = "table") -> None:
        """Display results to console."""
        if isinstance(results, TestResult):
            content = self.format_test_result(results, format_type)
        elif isinstance(results, TestSuiteResults):
            content = self.format_test_suite_results(results, format_type)
        else:
            content = str(results)
        
        print(content)
    
    def create_summary_report(self, suite_results: TestSuiteResults) -> str:
        """Create a summary report for test suite results."""
        lines = []
        
        # Header
        lines.append("=" * 60)
        lines.append(f"CLI Test Suite Results: {suite_results.suite_name}")
        lines.append("=" * 60)
        lines.append("")
        
        # Summary statistics
        lines.append("Summary:")
        lines.append(f"  Suite ID: {suite_results.suite_id}")
        lines.append(f"  Total Tests: {suite_results.total_tests}")
        lines.append(f"  Passed: {suite_results.passed_tests}")
        lines.append(f"  Failed: {suite_results.failed_tests}")
        lines.append(f"  Errors: {suite_results.error_tests}")
        lines.append(f"  Skipped: {suite_results.skipped_tests}")
        lines.append(f"  Success Rate: {suite_results.success_rate:.1%}")
        lines.append(f"  Total Execution Time: {suite_results.total_execution_time:.2f}s")
        lines.append("")
        
        # Performance metrics
        if suite_results.execution_metrics:
            metrics = suite_results.execution_metrics
            lines.append("Performance Metrics:")
            
            if metrics.memory_usage:
                peak_memory = metrics.memory_usage.get("peak_rss", 0) / 1024 / 1024
                lines.append(f"  Peak Memory Usage: {peak_memory:.1f} MB")
            
            if metrics.resource_consumption:
                avg_cpu = metrics.resource_consumption.get("avg_cpu_percent", 0)
                lines.append(f"  Average CPU Usage: {avg_cpu:.1f}%")
            
            if metrics.api_response_times:
                avg_response = metrics.api_response_times.get("avg_response_time", 0)
                lines.append(f"  Average API Response Time: {avg_response:.3f}s")
            
            lines.append("")
        
        # Individual test results
        lines.append("Individual Test Results:")
        lines.append("-" * 40)
        
        for result in suite_results.test_results:
            status_symbol = "✓" if result.status.value == "passed" else "✗"
            lines.append(f"  {status_symbol} {result.name}")
            lines.append(f"    Status: {result.status.value}")
            lines.append(f"    Execution Time: {result.execution_time:.2f}s")
            lines.append(f"    Real Execution Validated: {'Yes' if result.real_execution_validated else 'No'}")
            
            if result.error_details:
                lines.append(f"    Error: {result.error_details}")
            
            if result.metrics:
                lines.append(f"    Metrics: {result.metrics}")
            
            lines.append("")
        
        # Failed tests details
        failed_tests = [r for r in suite_results.test_results 
                       if r.status.value in ["failed", "error"]]
        
        if failed_tests:
            lines.append("Failed Test Details:")
            lines.append("-" * 40)
            
            for result in failed_tests:
                lines.append(f"Test: {result.name}")
                lines.append(f"  Status: {result.status.value}")
                lines.append(f"  Error: {result.error_details or 'No details available'}")
                
                if result.logs:
                    lines.append("  Recent Logs:")
                    for log_line in result.logs[-5:]:  # Last 5 log lines
                        lines.append(f"    {log_line}")
                
                lines.append("")
        
        # Recommendations
        lines.append("Recommendations:")
        lines.append("-" * 40)
        
        if suite_results.failed_tests > 0:
            lines.append("• Review failed test logs for specific error details")
            lines.append("• Check system requirements and dependencies")
        
        if not all(r.real_execution_validated for r in suite_results.test_results):
            lines.append("• Some tests may not have performed real execution")
            lines.append("• Verify test configuration and environment setup")
        
        if suite_results.success_rate < 0.8:
            lines.append("• Success rate is below 80% - investigate common failure patterns")
        
        lines.append("")
        lines.append("=" * 60)
        
        return "\n".join(lines)
    
    def _format_json(self, test_result: TestResult) -> str:
        """Format test result as JSON."""
        result_dict = {
            "test_id": test_result.test_id,
            "test_type": test_result.test_type.value,
            "name": test_result.name,
            "status": test_result.status.value,
            "execution_time": test_result.execution_time,
            "real_execution_validated": test_result.real_execution_validated,
            "metrics": test_result.metrics,
            "error_details": test_result.error_details,
            "artifacts": test_result.artifacts,
            "started_at": test_result.started_at.isoformat() if test_result.started_at else None,
            "completed_at": test_result.completed_at.isoformat() if test_result.completed_at else None,
            "retry_count": test_result.retry_count
        }
        
        return json.dumps(result_dict, indent=2)
    
    def _format_yaml(self, test_result: TestResult) -> str:
        """Format test result as YAML."""
        result_dict = {
            "test_id": test_result.test_id,
            "test_type": test_result.test_type.value,
            "name": test_result.name,
            "status": test_result.status.value,
            "execution_time": test_result.execution_time,
            "real_execution_validated": test_result.real_execution_validated,
            "metrics": test_result.metrics,
            "error_details": test_result.error_details,
            "artifacts": test_result.artifacts,
            "started_at": test_result.started_at.isoformat() if test_result.started_at else None,
            "completed_at": test_result.completed_at.isoformat() if test_result.completed_at else None,
            "retry_count": test_result.retry_count
        }
        
        return yaml.dump(result_dict, default_flow_style=False)
    
    def _format_table(self, test_results: List[TestResult]) -> str:
        """Format test results as table."""
        if not test_results:
            return "No test results to display."
        
        # Table headers
        headers = ["Test Name", "Status", "Time (s)", "Real Exec", "Metrics"]
        col_widths = [30, 10, 10, 10, 20]
        
        lines = []
        
        # Header row
        header_row = " | ".join(h.ljust(w) for h, w in zip(headers, col_widths))
        lines.append(header_row)
        lines.append("-" * len(header_row))
        
        # Data rows
        for result in test_results:
            name = result.name[:29] if len(result.name) > 29 else result.name
            status = result.status.value
            time_str = f"{result.execution_time:.2f}"
            real_exec = "Yes" if result.real_execution_validated else "No"
            metrics_str = f"{len(result.metrics)} metrics" if result.metrics else "None"
            
            row_data = [name, status, time_str, real_exec, metrics_str]
            row = " | ".join(data.ljust(w) for data, w in zip(row_data, col_widths))
            lines.append(row)
        
        return "\n".join(lines)
    
    def _format_csv(self, test_results: List[TestResult]) -> str:
        """Format test results as CSV."""
        import io
        
        output = io.StringIO()
        writer = csv.writer(output)
        
        # Header
        writer.writerow([
            "test_id", "test_type", "name", "status", "execution_time",
            "real_execution_validated", "error_details", "metrics_count",
            "artifacts_count", "started_at", "completed_at"
        ])
        
        # Data rows
        for result in test_results:
            writer.writerow([
                result.test_id,
                result.test_type.value,
                result.name,
                result.status.value,
                result.execution_time,
                result.real_execution_validated,
                result.error_details or "",
                len(result.metrics),
                len(result.artifacts),
                result.started_at.isoformat() if result.started_at else "",
                result.completed_at.isoformat() if result.completed_at else ""
            ])
        
        return output.getvalue()
    
    def _format_suite_json(self, suite_results: TestSuiteResults) -> str:
        """Format test suite results as JSON."""
        suite_dict = {
            "suite_id": suite_results.suite_id,
            "suite_name": suite_results.suite_name,
            "total_tests": suite_results.total_tests,
            "passed_tests": suite_results.passed_tests,
            "failed_tests": suite_results.failed_tests,
            "skipped_tests": suite_results.skipped_tests,
            "error_tests": suite_results.error_tests,
            "success_rate": suite_results.success_rate,
            "total_execution_time": suite_results.total_execution_time,
            "started_at": suite_results.started_at.isoformat(),
            "completed_at": suite_results.completed_at.isoformat() if suite_results.completed_at else None,
            "test_results": [
                {
                    "test_id": r.test_id,
                    "name": r.name,
                    "status": r.status.value,
                    "execution_time": r.execution_time,
                    "real_execution_validated": r.real_execution_validated,
                    "metrics": r.metrics,
                    "error_details": r.error_details
                }
                for r in suite_results.test_results
            ],
            "execution_metrics": suite_results.execution_metrics.__dict__ if suite_results.execution_metrics else None
        }
        
        return json.dumps(suite_dict, indent=2)
    
    def _format_suite_yaml(self, suite_results: TestSuiteResults) -> str:
        """Format test suite results as YAML."""
        suite_dict = {
            "suite_id": suite_results.suite_id,
            "suite_name": suite_results.suite_name,
            "summary": {
                "total_tests": suite_results.total_tests,
                "passed_tests": suite_results.passed_tests,
                "failed_tests": suite_results.failed_tests,
                "skipped_tests": suite_results.skipped_tests,
                "error_tests": suite_results.error_tests,
                "success_rate": suite_results.success_rate,
                "total_execution_time": suite_results.total_execution_time
            },
            "timestamps": {
                "started_at": suite_results.started_at.isoformat(),
                "completed_at": suite_results.completed_at.isoformat() if suite_results.completed_at else None
            },
            "test_results": [
                {
                    "test_id": r.test_id,
                    "name": r.name,
                    "status": r.status.value,
                    "execution_time": r.execution_time,
                    "real_execution_validated": r.real_execution_validated,
                    "metrics": r.metrics,
                    "error_details": r.error_details
                }
                for r in suite_results.test_results
            ]
        }
        
        return yaml.dump(suite_dict, default_flow_style=False)
    
    def _format_suite_table(self, suite_results: TestSuiteResults) -> str:
        """Format test suite results as table."""
        lines = []
        
        # Suite summary
        lines.append(f"Test Suite: {suite_results.suite_name}")
        lines.append(f"Suite ID: {suite_results.suite_id}")
        lines.append(f"Success Rate: {suite_results.success_rate:.1%} ({suite_results.passed_tests}/{suite_results.total_tests})")
        lines.append(f"Total Time: {suite_results.total_execution_time:.2f}s")
        lines.append("")
        
        # Individual test results table
        lines.append(self._format_table(suite_results.test_results))
        
        return "\n".join(lines)
    
    def _format_suite_csv(self, suite_results: TestSuiteResults) -> str:
        """Format test suite results as CSV."""
        return self._format_csv(suite_results.test_results)


def create_cli_result_formatter() -> CLIResultFormatter:
    """Factory function to create a CLI result formatter."""
    return CLIResultFormatter()