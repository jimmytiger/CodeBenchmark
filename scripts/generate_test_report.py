#!/usr/bin/env python3
"""
Generate comprehensive test report from multiple test result files.
"""

import argparse
import json
import xml.etree.ElementTree as ET
from pathlib import Path
from typing import Dict, List, Any
import time
from dataclasses import dataclass, asdict


@dataclass
class TestSuite:
    """Test suite information."""
    name: str
    tests: int
    failures: int
    errors: int
    skipped: int
    time: float
    test_cases: List[Dict[str, Any]]


@dataclass
class TestReport:
    """Complete test report."""
    timestamp: str
    total_tests: int
    total_failures: int
    total_errors: int
    total_skipped: int
    total_time: float
    success_rate: float
    test_suites: List[TestSuite]
    coverage_data: Dict[str, Any]
    performance_data: Dict[str, Any]
    security_data: Dict[str, Any]


class TestReportGenerator:
    """Generate comprehensive test reports."""
    
    def __init__(self):
        self.report_data = TestReport(
            timestamp=time.strftime('%Y-%m-%d %H:%M:%S'),
            total_tests=0,
            total_failures=0,
            total_errors=0,
            total_skipped=0,
            total_time=0.0,
            success_rate=0.0,
            test_suites=[],
            coverage_data={},
            performance_data={},
            security_data={}
        )
    
    def parse_junit_xml(self, xml_file: Path) -> TestSuite:
        """Parse JUnit XML file."""
        try:
            tree = ET.parse(xml_file)
            root = tree.getroot()
            
            # Handle both testsuite and testsuites root elements
            if root.tag == 'testsuites':
                testsuite = root.find('testsuite')
                if testsuite is None:
                    testsuite = root
            else:
                testsuite = root
            
            suite_name = testsuite.get('name', xml_file.stem)
            tests = int(testsuite.get('tests', 0))
            failures = int(testsuite.get('failures', 0))
            errors = int(testsuite.get('errors', 0))
            skipped = int(testsuite.get('skipped', 0))
            time_attr = testsuite.get('time', '0')
            suite_time = float(time_attr) if time_attr else 0.0
            
            test_cases = []
            for testcase in testsuite.findall('testcase'):
                case_data = {
                    'name': testcase.get('name', ''),
                    'classname': testcase.get('classname', ''),
                    'time': float(testcase.get('time', 0)),
                    'status': 'passed'
                }
                
                # Check for failures, errors, or skips
                if testcase.find('failure') is not None:
                    case_data['status'] = 'failed'
                    failure = testcase.find('failure')
                    case_data['failure_message'] = failure.get('message', '')
                    case_data['failure_text'] = failure.text or ''
                elif testcase.find('error') is not None:
                    case_data['status'] = 'error'
                    error = testcase.find('error')
                    case_data['error_message'] = error.get('message', '')
                    case_data['error_text'] = error.text or ''
                elif testcase.find('skipped') is not None:
                    case_data['status'] = 'skipped'
                    skipped_elem = testcase.find('skipped')
                    case_data['skip_message'] = skipped_elem.get('message', '')
                
                test_cases.append(case_data)
            
            return TestSuite(
                name=suite_name,
                tests=tests,
                failures=failures,
                errors=errors,
                skipped=skipped,
                time=suite_time,
                test_cases=test_cases
            )
            
        except Exception as e:
            print(f"Error parsing {xml_file}: {e}")
            return TestSuite(
                name=xml_file.stem,
                tests=0,
                failures=1,
                errors=0,
                skipped=0,
                time=0.0,
                test_cases=[{
                    'name': 'Parse Error',
                    'status': 'error',
                    'error_message': str(e)
                }]
            )
    
    def parse_coverage_xml(self, xml_file: Path) -> Dict[str, Any]:
        """Parse coverage XML file."""
        try:
            tree = ET.parse(xml_file)
            root = tree.getroot()
            
            coverage_data = {
                'line_rate': float(root.get('line-rate', 0)),
                'branch_rate': float(root.get('branch-rate', 0)),
                'lines_covered': int(root.get('lines-covered', 0)),
                'lines_valid': int(root.get('lines-valid', 0)),
                'branches_covered': int(root.get('branches-covered', 0)),
                'branches_valid': int(root.get('branches-valid', 0)),
                'packages': []
            }
            
            packages = root.find('packages')
            if packages is not None:
                for package in packages.findall('package'):
                    package_data = {
                        'name': package.get('name', ''),
                        'line_rate': float(package.get('line-rate', 0)),
                        'branch_rate': float(package.get('branch-rate', 0)),
                        'classes': []
                    }
                    
                    classes = package.find('classes')
                    if classes is not None:
                        for cls in classes.findall('class'):
                            class_data = {
                                'name': cls.get('name', ''),
                                'filename': cls.get('filename', ''),
                                'line_rate': float(cls.get('line-rate', 0)),
                                'branch_rate': float(cls.get('branch-rate', 0))
                            }
                            package_data['classes'].append(class_data)
                    
                    coverage_data['packages'].append(package_data)
            
            return coverage_data
            
        except Exception as e:
            print(f"Error parsing coverage file {xml_file}: {e}")
            return {}
    
    def parse_benchmark_json(self, json_file: Path) -> Dict[str, Any]:
        """Parse pytest-benchmark JSON file."""
        try:
            with open(json_file, 'r') as f:
                data = json.load(f)
            
            benchmarks = data.get('benchmarks', [])
            performance_data = {
                'total_benchmarks': len(benchmarks),
                'machine_info': data.get('machine_info', {}),
                'commit_info': data.get('commit_info', {}),
                'benchmarks': []
            }
            
            for benchmark in benchmarks:
                bench_data = {
                    'name': benchmark.get('name', ''),
                    'fullname': benchmark.get('fullname', ''),
                    'params': benchmark.get('params', {}),
                    'stats': benchmark.get('stats', {}),
                    'extra_info': benchmark.get('extra_info', {})
                }
                performance_data['benchmarks'].append(bench_data)
            
            return performance_data
            
        except Exception as e:
            print(f"Error parsing benchmark file {json_file}: {e}")
            return {}
    
    def parse_security_json(self, json_file: Path) -> Dict[str, Any]:
        """Parse security scan JSON files."""
        try:
            with open(json_file, 'r') as f:
                data = json.load(f)
            
            # Handle different security tool formats
            if 'results' in data and 'metrics' in data:
                # Bandit format
                return {
                    'tool': 'bandit',
                    'total_issues': len(data['results']),
                    'high_severity': sum(1 for r in data['results'] if r.get('issue_severity') == 'HIGH'),
                    'medium_severity': sum(1 for r in data['results'] if r.get('issue_severity') == 'MEDIUM'),
                    'low_severity': sum(1 for r in data['results'] if r.get('issue_severity') == 'LOW'),
                    'issues': data['results']
                }
            elif isinstance(data, list):
                # Safety format
                return {
                    'tool': 'safety',
                    'total_vulnerabilities': len(data),
                    'vulnerabilities': data
                }
            else:
                return {'tool': 'unknown', 'data': data}
                
        except Exception as e:
            print(f"Error parsing security file {json_file}: {e}")
            return {}
    
    def collect_test_results(self, result_dirs: List[str]):
        """Collect test results from directories."""
        for result_dir in result_dirs:
            result_path = Path(result_dir)
            if not result_path.exists():
                print(f"Warning: Result directory {result_dir} does not exist")
                continue
            
            # Find JUnit XML files
            for xml_file in result_path.glob('**/*.xml'):
                if 'junit' in xml_file.name or 'test-results' in xml_file.name:
                    suite = self.parse_junit_xml(xml_file)
                    self.report_data.test_suites.append(suite)
                    
                    # Update totals
                    self.report_data.total_tests += suite.tests
                    self.report_data.total_failures += suite.failures
                    self.report_data.total_errors += suite.errors
                    self.report_data.total_skipped += suite.skipped
                    self.report_data.total_time += suite.time
                
                elif 'coverage' in xml_file.name:
                    coverage_data = self.parse_coverage_xml(xml_file)
                    if coverage_data:
                        self.report_data.coverage_data = coverage_data
            
            # Find benchmark JSON files
            for json_file in result_path.glob('**/*benchmark*.json'):
                performance_data = self.parse_benchmark_json(json_file)
                if performance_data:
                    self.report_data.performance_data = performance_data
            
            # Find security JSON files
            for json_file in result_path.glob('**/*security*.json'):
                security_data = self.parse_security_json(json_file)
                if security_data:
                    if 'security_scans' not in self.report_data.security_data:
                        self.report_data.security_data['security_scans'] = []
                    self.report_data.security_data['security_scans'].append(security_data)
        
        # Calculate success rate
        if self.report_data.total_tests > 0:
            passed_tests = (self.report_data.total_tests - 
                          self.report_data.total_failures - 
                          self.report_data.total_errors)
            self.report_data.success_rate = (passed_tests / self.report_data.total_tests) * 100
    
    def generate_html_report(self, output_file: str):
        """Generate HTML report."""
        html_content = f"""
<!DOCTYPE html>
<html lang="en">
<head>
    <meta charset="UTF-8">
    <meta name="viewport" content="width=device-width, initial-scale=1.0">
    <title>Comprehensive Test Report</title>
    <style>
        body {{
            font-family: 'Segoe UI', Tahoma, Geneva, Verdana, sans-serif;
            margin: 0;
            padding: 20px;
            background-color: #f5f5f5;
        }}
        .container {{
            max-width: 1200px;
            margin: 0 auto;
            background: white;
            padding: 30px;
            border-radius: 10px;
            box-shadow: 0 2px 10px rgba(0,0,0,0.1);
        }}
        .header {{
            text-align: center;
            margin-bottom: 30px;
            padding-bottom: 20px;
            border-bottom: 2px solid #eee;
        }}
        .summary {{
            display: grid;
            grid-template-columns: repeat(auto-fit, minmax(200px, 1fr));
            gap: 20px;
            margin-bottom: 30px;
        }}
        .summary-card {{
            background: #f8f9fa;
            padding: 20px;
            border-radius: 8px;
            text-align: center;
            border-left: 4px solid #007bff;
        }}
        .summary-card.success {{ border-left-color: #28a745; }}
        .summary-card.warning {{ border-left-color: #ffc107; }}
        .summary-card.danger {{ border-left-color: #dc3545; }}
        .summary-card h3 {{
            margin: 0 0 10px 0;
            color: #333;
        }}
        .summary-card .value {{
            font-size: 2em;
            font-weight: bold;
            color: #007bff;
        }}
        .summary-card.success .value {{ color: #28a745; }}
        .summary-card.warning .value {{ color: #ffc107; }}
        .summary-card.danger .value {{ color: #dc3545; }}
        .test-suites {{
            margin-bottom: 30px;
        }}
        .test-suite {{
            margin-bottom: 20px;
            border: 1px solid #ddd;
            border-radius: 8px;
            overflow: hidden;
        }}
        .test-suite-header {{
            background: #f8f9fa;
            padding: 15px;
            border-bottom: 1px solid #ddd;
            cursor: pointer;
        }}
        .test-suite-header:hover {{
            background: #e9ecef;
        }}
        .test-suite-content {{
            display: none;
            padding: 15px;
        }}
        .test-suite-content.show {{
            display: block;
        }}
        .test-case {{
            padding: 10px;
            margin: 5px 0;
            border-radius: 4px;
            border-left: 4px solid #28a745;
        }}
        .test-case.failed {{
            border-left-color: #dc3545;
            background: #fff5f5;
        }}
        .test-case.error {{
            border-left-color: #fd7e14;
            background: #fff8f0;
        }}
        .test-case.skipped {{
            border-left-color: #6c757d;
            background: #f8f9fa;
        }}
        .status-badge {{
            display: inline-block;
            padding: 4px 8px;
            border-radius: 4px;
            font-size: 0.8em;
            font-weight: bold;
            text-transform: uppercase;
        }}
        .status-passed {{ background: #d4edda; color: #155724; }}
        .status-failed {{ background: #f8d7da; color: #721c24; }}
        .status-error {{ background: #ffeaa7; color: #856404; }}
        .status-skipped {{ background: #e2e3e5; color: #383d41; }}
        .coverage-section, .performance-section, .security-section {{
            margin-top: 30px;
            padding: 20px;
            background: #f8f9fa;
            border-radius: 8px;
        }}
        .progress-bar {{
            width: 100%;
            height: 20px;
            background: #e9ecef;
            border-radius: 10px;
            overflow: hidden;
        }}
        .progress-fill {{
            height: 100%;
            background: linear-gradient(90deg, #28a745, #20c997);
            transition: width 0.3s ease;
        }}
        .error-details {{
            background: #f8f9fa;
            padding: 10px;
            margin-top: 10px;
            border-radius: 4px;
            font-family: monospace;
            font-size: 0.9em;
            white-space: pre-wrap;
        }}
        .timestamp {{
            color: #6c757d;
            font-size: 0.9em;
        }}
        table {{
            width: 100%;
            border-collapse: collapse;
            margin-top: 15px;
        }}
        th, td {{
            padding: 10px;
            text-align: left;
            border-bottom: 1px solid #ddd;
        }}
        th {{
            background: #f8f9fa;
            font-weight: bold;
        }}
    </style>
    <script>
        function toggleTestSuite(element) {{
            const content = element.nextElementSibling;
            content.classList.toggle('show');
        }}
    </script>
</head>
<body>
    <div class="container">
        <div class="header">
            <h1>Comprehensive Test Report</h1>
            <p class="timestamp">Generated on {self.report_data.timestamp}</p>
        </div>
        
        <div class="summary">
            <div class="summary-card">
                <h3>Total Tests</h3>
                <div class="value">{self.report_data.total_tests}</div>
            </div>
            <div class="summary-card success">
                <h3>Success Rate</h3>
                <div class="value">{self.report_data.success_rate:.1f}%</div>
            </div>
            <div class="summary-card {'danger' if self.report_data.total_failures > 0 else 'success'}">
                <h3>Failures</h3>
                <div class="value">{self.report_data.total_failures}</div>
            </div>
            <div class="summary-card {'warning' if self.report_data.total_errors > 0 else 'success'}">
                <h3>Errors</h3>
                <div class="value">{self.report_data.total_errors}</div>
            </div>
            <div class="summary-card">
                <h3>Duration</h3>
                <div class="value">{self.report_data.total_time:.1f}s</div>
            </div>
        </div>
"""
        
        # Test Suites Section
        if self.report_data.test_suites:
            html_content += """
        <div class="test-suites">
            <h2>Test Suites</h2>
"""
            
            for suite in self.report_data.test_suites:
                success_rate = ((suite.tests - suite.failures - suite.errors) / suite.tests * 100) if suite.tests > 0 else 0
                
                html_content += f"""
            <div class="test-suite">
                <div class="test-suite-header" onclick="toggleTestSuite(this)">
                    <h3>{suite.name}</h3>
                    <p>Tests: {suite.tests} | Failures: {suite.failures} | Errors: {suite.errors} | Success: {success_rate:.1f}% | Time: {suite.time:.2f}s</p>
                </div>
                <div class="test-suite-content">
"""
                
                for test_case in suite.test_cases:
                    status_class = f"status-{test_case['status']}"
                    test_class = test_case['status']
                    
                    html_content += f"""
                    <div class="test-case {test_class}">
                        <div>
                            <strong>{test_case['name']}</strong>
                            <span class="status-badge {status_class}">{test_case['status']}</span>
                            <span style="float: right;">{test_case['time']:.3f}s</span>
                        </div>
                        <div style="font-size: 0.9em; color: #666;">{test_case.get('classname', '')}</div>
"""
                    
                    if test_case['status'] in ['failed', 'error']:
                        error_key = 'failure_text' if test_case['status'] == 'failed' else 'error_text'
                        if error_key in test_case and test_case[error_key]:
                            html_content += f"""
                        <div class="error-details">{test_case[error_key][:500]}{'...' if len(test_case[error_key]) > 500 else ''}</div>
"""
                    
                    html_content += """
                    </div>
"""
                
                html_content += """
                </div>
            </div>
"""
            
            html_content += """
        </div>
"""
        
        # Coverage Section
        if self.report_data.coverage_data:
            coverage = self.report_data.coverage_data
            line_rate = coverage.get('line_rate', 0) * 100
            branch_rate = coverage.get('branch_rate', 0) * 100
            
            html_content += f"""
        <div class="coverage-section">
            <h2>Code Coverage</h2>
            <div style="margin-bottom: 20px;">
                <h4>Line Coverage: {line_rate:.1f}%</h4>
                <div class="progress-bar">
                    <div class="progress-fill" style="width: {line_rate}%;"></div>
                </div>
            </div>
            <div style="margin-bottom: 20px;">
                <h4>Branch Coverage: {branch_rate:.1f}%</h4>
                <div class="progress-bar">
                    <div class="progress-fill" style="width: {branch_rate}%;"></div>
                </div>
            </div>
            <p>Lines Covered: {coverage.get('lines_covered', 0)} / {coverage.get('lines_valid', 0)}</p>
            <p>Branches Covered: {coverage.get('branches_covered', 0)} / {coverage.get('branches_valid', 0)}</p>
        </div>
"""
        
        # Performance Section
        if self.report_data.performance_data:
            perf = self.report_data.performance_data
            html_content += f"""
        <div class="performance-section">
            <h2>Performance Benchmarks</h2>
            <p>Total Benchmarks: {perf.get('total_benchmarks', 0)}</p>
            
            <table>
                <thead>
                    <tr>
                        <th>Benchmark</th>
                        <th>Mean (s)</th>
                        <th>Min (s)</th>
                        <th>Max (s)</th>
                        <th>StdDev</th>
                    </tr>
                </thead>
                <tbody>
"""
            
            for benchmark in perf.get('benchmarks', []):
                stats = benchmark.get('stats', {})
                html_content += f"""
                    <tr>
                        <td>{benchmark.get('name', 'Unknown')}</td>
                        <td>{stats.get('mean', 0):.4f}</td>
                        <td>{stats.get('min', 0):.4f}</td>
                        <td>{stats.get('max', 0):.4f}</td>
                        <td>{stats.get('stddev', 0):.4f}</td>
                    </tr>
"""
            
            html_content += """
                </tbody>
            </table>
        </div>
"""
        
        # Security Section
        if self.report_data.security_data:
            html_content += """
        <div class="security-section">
            <h2>Security Scan Results</h2>
"""
            
            for scan in self.report_data.security_data.get('security_scans', []):
                tool = scan.get('tool', 'Unknown')
                html_content += f"""
            <h3>{tool.title()} Results</h3>
"""
                
                if tool == 'bandit':
                    total_issues = scan.get('total_issues', 0)
                    high_severity = scan.get('high_severity', 0)
                    medium_severity = scan.get('medium_severity', 0)
                    low_severity = scan.get('low_severity', 0)
                    
                    html_content += f"""
            <p>Total Issues: {total_issues}</p>
            <p>High Severity: <span class="{'status-failed' if high_severity > 0 else 'status-passed'}">{high_severity}</span></p>
            <p>Medium Severity: <span class="{'status-warning' if medium_severity > 0 else 'status-passed'}">{medium_severity}</span></p>
            <p>Low Severity: {low_severity}</p>
"""
                
                elif tool == 'safety':
                    total_vulns = scan.get('total_vulnerabilities', 0)
                    html_content += f"""
            <p>Total Vulnerabilities: <span class="{'status-failed' if total_vulns > 0 else 'status-passed'}">{total_vulns}</span></p>
"""
            
            html_content += """
        </div>
"""
        
        html_content += """
    </div>
</body>
</html>
"""
        
        with open(output_file, 'w') as f:
            f.write(html_content)
        
        print(f"HTML report generated: {output_file}")
    
    def generate_json_report(self, output_file: str):
        """Generate JSON report."""
        with open(output_file, 'w') as f:
            json.dump(asdict(self.report_data), f, indent=2)
        
        print(f"JSON report generated: {output_file}")


def main():
    """Main function."""
    parser = argparse.ArgumentParser(description='Generate comprehensive test report')
    
    parser.add_argument(
        '--unit-results',
        nargs='+',
        help='Unit test result directories'
    )
    
    parser.add_argument(
        '--integration-results',
        nargs='+',
        help='Integration test result directories'
    )
    
    parser.add_argument(
        '--e2e-results',
        nargs='+',
        help='E2E test result directories'
    )
    
    parser.add_argument(
        '--performance-results',
        nargs='+',
        help='Performance test result directories'
    )
    
    parser.add_argument(
        '--security-results',
        nargs='+',
        help='Security test result directories'
    )
    
    parser.add_argument(
        '--output',
        default='comprehensive-test-report.html',
        help='Output HTML file'
    )
    
    parser.add_argument(
        '--json-output',
        help='Output JSON file'
    )
    
    args = parser.parse_args()
    
    # Collect all result directories
    all_result_dirs = []
    for result_list in [args.unit_results, args.integration_results, args.e2e_results, 
                       args.performance_results, args.security_results]:
        if result_list:
            all_result_dirs.extend(result_list)
    
    if not all_result_dirs:
        print("No result directories specified")
        return 1
    
    # Generate report
    generator = TestReportGenerator()
    generator.collect_test_results(all_result_dirs)
    generator.generate_html_report(args.output)
    
    if args.json_output:
        generator.generate_json_report(args.json_output)
    
    # Print summary
    print(f"\nTest Report Summary:")
    print(f"Total Tests: {generator.report_data.total_tests}")
    print(f"Success Rate: {generator.report_data.success_rate:.1f}%")
    print(f"Failures: {generator.report_data.total_failures}")
    print(f"Errors: {generator.report_data.total_errors}")
    print(f"Duration: {generator.report_data.total_time:.2f}s")
    
    return 0 if generator.report_data.total_failures == 0 and generator.report_data.total_errors == 0 else 1


if __name__ == '__main__':
    exit(main())