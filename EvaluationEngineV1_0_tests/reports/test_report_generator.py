"""
TestReportGenerator for comprehensive test execution reports.

This module generates detailed reports from test execution results including:
- Test summary reports
- Performance analysis reports  
- Adapter validation reports
- Error analysis reports
"""

import json
import logging
from datetime import datetime
from pathlib import Path
from typing import Dict, List, Any, Optional
from dataclasses import dataclass, asdict

from models.test_models import TestResult, ValidationResult, ExecutionMetrics


@dataclass
class Report:
    """Base report structure"""
    title: str
    generated_at: datetime
    summary: Dict[str, Any]
    details: Dict[str, Any]
    metadata: Dict[str, Any]


class TestReportGenerator:
    """
    Generates comprehensive reports from test execution results.
    
    Supports multiple report formats and provides detailed analysis
    of test execution, performance metrics, and validation results.
    """
    
    def __init__(self, output_dir: Path = None):
        """
        Initialize the report generator.
        
        Args:
            output_dir: Directory to save generated reports
        """
        self.output_dir = output_dir or Path("reports")
        self.output_dir.mkdir(exist_ok=True)
        self.logger = logging.getLogger(__name__)
        
    def generate_test_summary(self, results: List[TestResult]) -> Report:
        """
        Generate a comprehensive test summary report.
        
        Args:
            results: List of test results to analyze
            
        Returns:
            Report object containing test summary
        """
        total_tests = len(results)
        passed_tests = len([r for r in results if (r.status.value if hasattr(r.status, 'value') else str(r.status)) == 'passed'])
        failed_tests = len([r for r in results if (r.status.value if hasattr(r.status, 'value') else str(r.status)) == 'failed'])
        skipped_tests = len([r for r in results if (r.status.value if hasattr(r.status, 'value') else str(r.status)) == 'skipped'])
        
        # Calculate success rate
        success_rate = (passed_tests / total_tests * 100) if total_tests > 0 else 0
        
        # Analyze execution times
        execution_times = [r.execution_time for r in results if r.execution_time]
        avg_execution_time = sum(execution_times) / len(execution_times) if execution_times else 0
        total_execution_time = sum(execution_times)
        
        # Analyze real execution validation
        real_execution_validated = len([r for r in results if r.real_execution_validated])
        real_execution_rate = (real_execution_validated / total_tests * 100) if total_tests > 0 else 0
        
        # Group results by test type
        test_types = {}
        for result in results:
            test_type = result.test_type.value if hasattr(result.test_type, 'value') else str(result.test_type)
            status = result.status.value if hasattr(result.status, 'value') else str(result.status)
            
            if test_type not in test_types:
                test_types[test_type] = {'passed': 0, 'failed': 0, 'skipped': 0, 'error': 0}
            
            if status in test_types[test_type]:
                test_types[test_type][status] += 1
        
        # Collect error patterns
        error_patterns = {}
        for result in results:
            status = result.status.value if hasattr(result.status, 'value') else str(result.status)
            if status == 'failed' and result.error_details:
                error_type = result.error_details.split(':')[0] if ':' in result.error_details else 'Unknown'
                error_patterns[error_type] = error_patterns.get(error_type, 0) + 1
        
        summary = {
            'total_tests': total_tests,
            'passed_tests': passed_tests,
            'failed_tests': failed_tests,
            'skipped_tests': skipped_tests,
            'success_rate': round(success_rate, 2),
            'real_execution_rate': round(real_execution_rate, 2),
            'avg_execution_time': round(avg_execution_time, 2),
            'total_execution_time': round(total_execution_time, 2)
        }
        
        details = {
            'test_types': test_types,
            'error_patterns': error_patterns,
            'individual_results': [asdict(result) for result in results]
        }
        
        metadata = {
            'report_type': 'test_summary',
            'generator_version': '1.0',
            'total_results_analyzed': total_tests
        }
        
        report = Report(
            title="Test Execution Summary Report",
            generated_at=datetime.now(),
            summary=summary,
            details=details,
            metadata=metadata
        )
        
        self.logger.info(f"Generated test summary report for {total_tests} test results")
        return report
        
    def generate_performance_report(self, metrics: ExecutionMetrics) -> Report:
        """
        Generate a performance analysis report.
        
        Args:
            metrics: Execution metrics to analyze
            
        Returns:
            Report object containing performance analysis
        """
        # Analyze task execution times
        task_times = metrics.task_execution_times
        slowest_tasks = sorted(task_times.items(), key=lambda x: x[1], reverse=True)[:10]
        fastest_tasks = sorted(task_times.items(), key=lambda x: x[1])[:10]
        
        # Analyze memory usage patterns
        memory_usage = metrics.memory_usage
        peak_memory = max(memory_usage.values()) if memory_usage else 0
        avg_memory = sum(memory_usage.values()) / len(memory_usage) if memory_usage else 0
        
        # Analyze API response times
        api_times = metrics.api_response_times
        avg_api_time = sum(api_times.values()) / len(api_times) if api_times else 0
        slowest_apis = sorted(api_times.items(), key=lambda x: x[1], reverse=True)[:5]
        
        # Calculate performance scores
        performance_score = self._calculate_performance_score(metrics)
        
        summary = {
            'total_execution_time': round(metrics.total_execution_time, 2),
            'peak_memory_usage': round(peak_memory, 2),
            'avg_memory_usage': round(avg_memory, 2),
            'avg_api_response_time': round(avg_api_time, 2),
            'performance_score': round(performance_score, 2),
            'total_tasks_analyzed': len(task_times)
        }
        
        details = {
            'slowest_tasks': slowest_tasks,
            'fastest_tasks': fastest_tasks,
            'slowest_apis': slowest_apis,
            'memory_usage_timeline': memory_usage,
            'task_execution_times': task_times,
            'api_response_times': api_times,
            'success_rates': metrics.success_rates,
            'error_rates': metrics.error_rates
        }
        
        metadata = {
            'report_type': 'performance_analysis',
            'generator_version': '1.0',
            'metrics_version': getattr(metrics, 'version', '1.0')
        }
        
        report = Report(
            title="Performance Analysis Report",
            generated_at=datetime.now(),
            summary=summary,
            details=details,
            metadata=metadata
        )
        
        self.logger.info("Generated performance analysis report")
        return report
        
    def generate_adapter_validation_report(self, validations: List[ValidationResult]) -> Report:
        """
        Generate adapter validation report.
        
        Args:
            validations: List of adapter validation results
            
        Returns:
            Report object containing adapter validation analysis
        """
        total_adapters = len(validations)
        successful_integrations = len([v for v in validations if (v.integration_status.value if hasattr(v.integration_status, 'value') else str(v.integration_status)) == 'passed'])
        failed_integrations = len([v for v in validations if (v.integration_status.value if hasattr(v.integration_status, 'value') else str(v.integration_status)) == 'failed'])
        
        # Analyze dependency installation
        dependencies_installed = len([v for v in validations if v.dependencies_installed])
        dependency_success_rate = (dependencies_installed / total_adapters * 100) if total_adapters > 0 else 0
        
        # Collect adapter-specific metrics
        adapter_metrics = {}
        all_issues = []
        
        for validation in validations:
            adapter_name = validation.adapter_name
            adapter_metrics[adapter_name] = {
                'integration_status': validation.integration_status.value if hasattr(validation.integration_status, 'value') else str(validation.integration_status),
                'dependencies_installed': validation.dependencies_installed,
                'test_count': len(validation.test_results),
                'passed_tests': len([t for t in validation.test_results if (t.status.value if hasattr(t.status, 'value') else str(t.status)) == 'passed']),
                'performance_metrics': validation.performance_metrics,
                'issues_count': len(validation.issues_found)
            }
            all_issues.extend(validation.issues_found)
        
        # Analyze common issues
        issue_patterns = {}
        for issue in all_issues:
            issue_type = issue.split(':')[0] if ':' in issue else issue
            issue_patterns[issue_type] = issue_patterns.get(issue_type, 0) + 1
        
        summary = {
            'total_adapters': total_adapters,
            'successful_integrations': successful_integrations,
            'failed_integrations': failed_integrations,
            'integration_success_rate': round((successful_integrations / total_adapters * 100) if total_adapters > 0 else 0, 2),
            'dependency_success_rate': round(dependency_success_rate, 2),
            'total_issues_found': len(all_issues)
        }
        
        details = {
            'adapter_metrics': adapter_metrics,
            'issue_patterns': issue_patterns,
            'validation_details': [asdict(validation) for validation in validations]
        }
        
        metadata = {
            'report_type': 'adapter_validation',
            'generator_version': '1.0',
            'adapters_analyzed': [v.adapter_name for v in validations]
        }
        
        report = Report(
            title="Adapter Validation Report",
            generated_at=datetime.now(),
            summary=summary,
            details=details,
            metadata=metadata
        )
        
        self.logger.info(f"Generated adapter validation report for {total_adapters} adapters")
        return report
        
    def save_report(self, report: Report, filename: str = None, format: str = 'json') -> Path:
        """
        Save report to file.
        
        Args:
            report: Report object to save
            filename: Optional filename (auto-generated if not provided)
            format: Output format ('json', 'html', 'markdown')
            
        Returns:
            Path to saved report file
        """
        if not filename:
            timestamp = datetime.now().strftime("%Y%m%d_%H%M%S")
            report_type = report.metadata.get('report_type', 'report')
            filename = f"{report_type}_{timestamp}.{format}"
        
        filepath = self.output_dir / filename
        
        if format == 'json':
            self._save_json_report(report, filepath)
        elif format == 'html':
            self._save_html_report(report, filepath)
        elif format == 'markdown':
            self._save_markdown_report(report, filepath)
        else:
            raise ValueError(f"Unsupported format: {format}")
        
        self.logger.info(f"Saved report to {filepath}")
        return filepath
        
    def _calculate_performance_score(self, metrics: ExecutionMetrics) -> float:
        """Calculate overall performance score based on metrics."""
        # Simple scoring algorithm - can be enhanced
        base_score = 100.0
        
        # Penalize slow execution times
        if metrics.total_execution_time > 300:  # 5 minutes
            base_score -= 20
        elif metrics.total_execution_time > 60:  # 1 minute
            base_score -= 10
        
        # Penalize high error rates
        avg_error_rate = sum(metrics.error_rates.values()) / len(metrics.error_rates) if metrics.error_rates else 0
        base_score -= avg_error_rate * 50
        
        # Reward high success rates
        avg_success_rate = sum(metrics.success_rates.values()) / len(metrics.success_rates) if metrics.success_rates else 0
        base_score += (avg_success_rate - 0.8) * 25 if avg_success_rate > 0.8 else 0
        
        return max(0, min(100, base_score))
        
    def _save_json_report(self, report: Report, filepath: Path):
        """Save report as JSON."""
        report_dict = asdict(report)
        # Convert datetime to string for JSON serialization
        report_dict['generated_at'] = report.generated_at.isoformat()
        
        with open(filepath, 'w') as f:
            json.dump(report_dict, f, indent=2, default=str)
            
    def _save_html_report(self, report: Report, filepath: Path):
        """Save report as HTML."""
        html_content = self._generate_html_content(report)
        with open(filepath, 'w') as f:
            f.write(html_content)
            
    def _save_markdown_report(self, report: Report, filepath: Path):
        """Save report as Markdown."""
        markdown_content = self._generate_markdown_content(report)
        with open(filepath, 'w') as f:
            f.write(markdown_content)
            
    def _generate_html_content(self, report: Report) -> str:
        """Generate HTML content for report."""
        return f"""
<!DOCTYPE html>
<html>
<head>
    <title>{report.title}</title>
    <style>
        body {{ font-family: Arial, sans-serif; margin: 40px; }}
        .summary {{ background-color: #f5f5f5; padding: 20px; border-radius: 5px; }}
        .metric {{ margin: 10px 0; }}
        .success {{ color: green; }}
        .failure {{ color: red; }}
        table {{ border-collapse: collapse; width: 100%; }}
        th, td {{ border: 1px solid #ddd; padding: 8px; text-align: left; }}
        th {{ background-color: #f2f2f2; }}
    </style>
</head>
<body>
    <h1>{report.title}</h1>
    <p><strong>Generated:</strong> {report.generated_at.strftime('%Y-%m-%d %H:%M:%S')}</p>
    
    <h2>Summary</h2>
    <div class="summary">
        {self._format_summary_html(report.summary)}
    </div>
    
    <h2>Details</h2>
    <pre>{json.dumps(report.details, indent=2, default=str)}</pre>
</body>
</html>
"""
        
    def _generate_markdown_content(self, report: Report) -> str:
        """Generate Markdown content for report."""
        content = f"""# {report.title}

**Generated:** {report.generated_at.strftime('%Y-%m-%d %H:%M:%S')}

## Summary

{self._format_summary_markdown(report.summary)}

## Details

```json
{json.dumps(report.details, indent=2, default=str)}
```

## Metadata

- Report Type: {report.metadata.get('report_type', 'Unknown')}
- Generator Version: {report.metadata.get('generator_version', 'Unknown')}
"""
        return content
        
    def _format_summary_html(self, summary: Dict[str, Any]) -> str:
        """Format summary data as HTML."""
        html_parts = []
        for key, value in summary.items():
            formatted_key = key.replace('_', ' ').title()
            html_parts.append(f'<div class="metric"><strong>{formatted_key}:</strong> {value}</div>')
        return '\n'.join(html_parts)
        
    def _format_summary_markdown(self, summary: Dict[str, Any]) -> str:
        """Format summary data as Markdown."""
        markdown_parts = []
        for key, value in summary.items():
            formatted_key = key.replace('_', ' ').title()
            markdown_parts.append(f'- **{formatted_key}:** {value}')
        return '\n'.join(markdown_parts)