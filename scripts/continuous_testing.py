#!/usr/bin/env python3
"""
Continuous testing pipeline with automated regression detection.
"""

import os
import json
import time
import subprocess
import threading
from pathlib import Path
from typing import Dict, List, Any, Optional
from dataclasses import dataclass, asdict
import logging
from datetime import datetime, timedelta
import hashlib
import git


@dataclass
class TestRun:
    """Test run data structure."""
    id: str
    timestamp: str
    commit_hash: str
    branch: str
    trigger: str  # 'commit', 'schedule', 'manual'
    test_results: Dict[str, Any]
    performance_metrics: Dict[str, Any]
    security_scan: Dict[str, Any]
    duration: float
    status: str  # 'passed', 'failed', 'error'


@dataclass
class RegressionAlert:
    """Regression alert data structure."""
    timestamp: str
    test_run_id: str
    metric_name: str
    current_value: float
    baseline_value: float
    regression_percentage: float
    severity: str  # 'minor', 'major', 'critical'


class ContinuousTestingPipeline:
    """Continuous testing pipeline with regression detection."""
    
    def __init__(self, config: Dict[str, Any]):
        self.config = config
        self.test_history: List[TestRun] = []
        self.regression_alerts: List[RegressionAlert] = []
        self.running = False
        self.pipeline_thread: Optional[threading.Thread] = None
        
        # Setup logging
        logging.basicConfig(level=logging.INFO)
        self.logger = logging.getLogger(__name__)
        
        # Load existing test history
        self.load_test_history()
        
        # Performance regression thresholds
        self.regression_thresholds = config.get('regression_thresholds', {
            'response_time': 1.2,  # 20% increase
            'throughput': 0.8,     # 20% decrease
            'memory_usage': 1.3,   # 30% increase
            'cpu_usage': 1.3,      # 30% increase
            'test_duration': 1.5,  # 50% increase
            'success_rate': 0.95   # 5% decrease
        })
    
    def load_test_history(self):
        """Load test history from file."""
        history_file = Path(self.config.get('history_file', 'test_history.json'))
        if history_file.exists():
            try:
                with open(history_file, 'r') as f:
                    data = json.load(f)
                    self.test_history = [TestRun(**run) for run in data.get('test_runs', [])]
                    self.regression_alerts = [RegressionAlert(**alert) for alert in data.get('alerts', [])]
            except Exception as e:
                self.logger.error(f"Error loading test history: {e}")
    
    def save_test_history(self):
        """Save test history to file."""
        history_file = Path(self.config.get('history_file', 'test_history.json'))
        try:
            data = {
                'test_runs': [asdict(run) for run in self.test_history],
                'alerts': [asdict(alert) for alert in self.regression_alerts]
            }
            with open(history_file, 'w') as f:
                json.dump(data, f, indent=2)
        except Exception as e:
            self.logger.error(f"Error saving test history: {e}")
    
    def get_git_info(self) -> Dict[str, str]:
        """Get current git information."""
        try:
            repo = git.Repo('.')
            return {
                'commit_hash': repo.head.commit.hexsha,
                'branch': repo.active_branch.name,
                'commit_message': repo.head.commit.message.strip(),
                'author': str(repo.head.commit.author),
                'timestamp': repo.head.commit.committed_datetime.isoformat()
            }
        except Exception as e:
            self.logger.error(f"Error getting git info: {e}")
            return {
                'commit_hash': 'unknown',
                'branch': 'unknown',
                'commit_message': '',
                'author': '',
                'timestamp': datetime.now().isoformat()
            }
    
    def run_tests(self) -> Dict[str, Any]:
        """Run comprehensive test suite."""
        test_results = {}
        
        # Run unit tests
        self.logger.info("Running unit tests...")
        unit_result = self._run_command([
            'pytest', 'evaluation_engine_tests/unit/',
            '--cov=evaluation_engine',
            '--cov-report=json:coverage.json',
            '--json-report', '--json-report-file=unit_results.json',
            '-q'
        ])
        test_results['unit_tests'] = unit_result
        
        # Run integration tests
        self.logger.info("Running integration tests...")
        integration_result = self._run_command([
            'pytest', 'evaluation_engine_tests/integration/',
            '--json-report', '--json-report-file=integration_results.json',
            '-q'
        ])
        test_results['integration_tests'] = integration_result
        
        # Run security tests
        self.logger.info("Running security tests...")
        security_result = self._run_command([
            'pytest', 'evaluation_engine_tests/security/',
            '--json-report', '--json-report-file=security_results.json',
            '-q', '-m', 'security and not slow'
        ])
        test_results['security_tests'] = security_result
        
        # Parse coverage data
        coverage_file = Path('coverage.json')
        if coverage_file.exists():
            try:
                with open(coverage_file, 'r') as f:
                    coverage_data = json.load(f)
                    test_results['coverage'] = {
                        'line_coverage': coverage_data['totals']['percent_covered'],
                        'lines_covered': coverage_data['totals']['covered_lines'],
                        'lines_total': coverage_data['totals']['num_statements']
                    }
            except Exception as e:
                self.logger.error(f"Error parsing coverage data: {e}")
        
        return test_results
    
    def run_performance_tests(self) -> Dict[str, Any]:
        """Run performance benchmarks."""
        self.logger.info("Running performance tests...")
        
        perf_result = self._run_command([
            'pytest', 'evaluation_engine_tests/performance/',
            '--benchmark-only',
            '--benchmark-json=benchmark_results.json',
            '-q'
        ])
        
        performance_metrics = {'test_result': perf_result}
        
        # Parse benchmark results
        benchmark_file = Path('benchmark_results.json')
        if benchmark_file.exists():
            try:
                with open(benchmark_file, 'r') as f:
                    benchmark_data = json.load(f)
                    
                    benchmarks = benchmark_data.get('benchmarks', [])
                    if benchmarks:
                        # Calculate aggregate metrics
                        mean_times = [b['stats']['mean'] for b in benchmarks]
                        performance_metrics.update({
                            'avg_response_time': sum(mean_times) / len(mean_times),
                            'max_response_time': max(mean_times),
                            'min_response_time': min(mean_times),
                            'total_benchmarks': len(benchmarks)
                        })
            except Exception as e:
                self.logger.error(f"Error parsing benchmark data: {e}")
        
        return performance_metrics
    
    def run_security_scan(self) -> Dict[str, Any]:
        """Run security scanning."""
        self.logger.info("Running security scan...")
        
        # Run custom security scanner
        security_result = self._run_command([
            'python', 'scripts/security_scanner.py',
            '--directory', '.',
            '--json-output', 'security_scan.json'
        ])
        
        security_data = {'scan_result': security_result}
        
        # Parse security scan results
        scan_file = Path('security_scan.json')
        if scan_file.exists():
            try:
                with open(scan_file, 'r') as f:
                    scan_data = json.load(f)
                    
                    if scan_data:
                        total_vulns = sum(len(result['vulnerabilities']) for result in scan_data)
                        critical_vulns = sum(
                            sum(1 for v in result['vulnerabilities'] if v['severity'] == 'critical')
                            for result in scan_data
                        )
                        high_vulns = sum(
                            sum(1 for v in result['vulnerabilities'] if v['severity'] == 'high')
                            for result in scan_data
                        )
                        
                        security_data.update({
                            'total_vulnerabilities': total_vulns,
                            'critical_vulnerabilities': critical_vulns,
                            'high_vulnerabilities': high_vulns,
                            'security_score': max(0, 100 - (critical_vulns * 20 + high_vulns * 10))
                        })
            except Exception as e:
                self.logger.error(f"Error parsing security scan data: {e}")
        
        return security_data
    
    def detect_regressions(self, current_run: TestRun):
        """Detect performance regressions compared to baseline."""
        if len(self.test_history) < 2:
            self.logger.info("Not enough test history for regression detection")
            return
        
        # Use last successful run as baseline
        baseline_run = None
        for run in reversed(self.test_history[:-1]):  # Exclude current run
            if run.status == 'passed':
                baseline_run = run
                break
        
        if not baseline_run:
            self.logger.warning("No successful baseline run found")
            return
        
        # Check test performance regressions
        self._check_test_regressions(current_run, baseline_run)
        
        # Check performance benchmark regressions
        self._check_performance_regressions(current_run, baseline_run)
        
        # Check security regressions
        self._check_security_regressions(current_run, baseline_run)
    
    def _check_test_regressions(self, current_run: TestRun, baseline_run: TestRun):
        """Check for test performance regressions."""
        current_tests = current_run.test_results
        baseline_tests = baseline_run.test_results
        
        # Check test duration regression
        current_duration = current_run.duration
        baseline_duration = baseline_run.duration
        
        if current_duration > baseline_duration * self.regression_thresholds['test_duration']:
            regression_pct = ((current_duration - baseline_duration) / baseline_duration) * 100
            self._create_regression_alert(
                current_run.id, 'test_duration', current_duration, baseline_duration,
                regression_pct, 'major' if regression_pct > 50 else 'minor'
            )
        
        # Check coverage regression
        current_coverage = current_tests.get('coverage', {}).get('line_coverage', 0)
        baseline_coverage = baseline_tests.get('coverage', {}).get('line_coverage', 0)
        
        if current_coverage < baseline_coverage * 0.95:  # 5% decrease threshold
            regression_pct = ((baseline_coverage - current_coverage) / baseline_coverage) * 100
            self._create_regression_alert(
                current_run.id, 'test_coverage', current_coverage, baseline_coverage,
                regression_pct, 'major' if regression_pct > 10 else 'minor'
            )
    
    def _check_performance_regressions(self, current_run: TestRun, baseline_run: TestRun):
        """Check for performance benchmark regressions."""
        current_perf = current_run.performance_metrics
        baseline_perf = baseline_run.performance_metrics
        
        # Check response time regression
        current_response_time = current_perf.get('avg_response_time', 0)
        baseline_response_time = baseline_perf.get('avg_response_time', 0)
        
        if (baseline_response_time > 0 and 
            current_response_time > baseline_response_time * self.regression_thresholds['response_time']):
            regression_pct = ((current_response_time - baseline_response_time) / baseline_response_time) * 100
            self._create_regression_alert(
                current_run.id, 'response_time', current_response_time, baseline_response_time,
                regression_pct, 'critical' if regression_pct > 50 else 'major'
            )
    
    def _check_security_regressions(self, current_run: TestRun, baseline_run: TestRun):
        """Check for security regressions."""
        current_security = current_run.security_scan
        baseline_security = baseline_run.security_scan
        
        # Check for new critical vulnerabilities
        current_critical = current_security.get('critical_vulnerabilities', 0)
        baseline_critical = baseline_security.get('critical_vulnerabilities', 0)
        
        if current_critical > baseline_critical:
            self._create_regression_alert(
                current_run.id, 'critical_vulnerabilities', current_critical, baseline_critical,
                ((current_critical - baseline_critical) / max(baseline_critical, 1)) * 100,
                'critical'
            )
        
        # Check security score regression
        current_score = current_security.get('security_score', 100)
        baseline_score = baseline_security.get('security_score', 100)
        
        if current_score < baseline_score * 0.9:  # 10% decrease threshold
            regression_pct = ((baseline_score - current_score) / baseline_score) * 100
            self._create_regression_alert(
                current_run.id, 'security_score', current_score, baseline_score,
                regression_pct, 'major' if regression_pct > 20 else 'minor'
            )
    
    def _create_regression_alert(self, test_run_id: str, metric_name: str, 
                                current_value: float, baseline_value: float,
                                regression_percentage: float, severity: str):
        """Create a regression alert."""
        alert = RegressionAlert(
            timestamp=datetime.now().isoformat(),
            test_run_id=test_run_id,
            metric_name=metric_name,
            current_value=current_value,
            baseline_value=baseline_value,
            regression_percentage=regression_percentage,
            severity=severity
        )
        
        self.regression_alerts.append(alert)
        self.logger.warning(
            f"Regression detected [{severity.upper()}]: {metric_name} "
            f"changed from {baseline_value:.3f} to {current_value:.3f} "
            f"({regression_percentage:+.1f}%)"
        )
        
        # Send notification if configured
        self._send_regression_notification(alert)
    
    def _send_regression_notification(self, alert: RegressionAlert):
        """Send regression notification."""
        # This would integrate with notification systems
        # For now, just log
        self.logger.info(f"Regression notification sent: {alert.metric_name}")
    
    def run_full_pipeline(self, trigger: str = 'manual') -> TestRun:
        """Run the complete testing pipeline."""
        start_time = time.time()
        git_info = self.get_git_info()
        
        # Generate unique test run ID
        run_id = hashlib.md5(
            f"{git_info['commit_hash']}{start_time}".encode()
        ).hexdigest()[:8]
        
        self.logger.info(f"Starting test run {run_id} (trigger: {trigger})")
        
        try:
            # Run tests
            test_results = self.run_tests()
            
            # Run performance tests
            performance_metrics = self.run_performance_tests()
            
            # Run security scan
            security_scan = self.run_security_scan()
            
            # Determine overall status
            status = 'passed'
            for test_type, result in test_results.items():
                if isinstance(result, dict) and result.get('returncode', 0) != 0:
                    status = 'failed'
                    break
            
            # Create test run record
            test_run = TestRun(
                id=run_id,
                timestamp=datetime.now().isoformat(),
                commit_hash=git_info['commit_hash'],
                branch=git_info['branch'],
                trigger=trigger,
                test_results=test_results,
                performance_metrics=performance_metrics,
                security_scan=security_scan,
                duration=time.time() - start_time,
                status=status
            )
            
            # Add to history
            self.test_history.append(test_run)
            
            # Detect regressions
            self.detect_regressions(test_run)
            
            # Save history
            self.save_test_history()
            
            self.logger.info(
                f"Test run {run_id} completed: {status} "
                f"(duration: {test_run.duration:.2f}s)"
            )
            
            return test_run
            
        except Exception as e:
            self.logger.error(f"Error in test pipeline: {e}")
            
            # Create failed test run record
            test_run = TestRun(
                id=run_id,
                timestamp=datetime.now().isoformat(),
                commit_hash=git_info['commit_hash'],
                branch=git_info['branch'],
                trigger=trigger,
                test_results={'error': str(e)},
                performance_metrics={},
                security_scan={},
                duration=time.time() - start_time,
                status='error'
            )
            
            self.test_history.append(test_run)
            self.save_test_history()
            
            return test_run
    
    def start_continuous_monitoring(self, interval_minutes: int = 60):
        """Start continuous testing monitoring."""
        if self.running:
            self.logger.warning("Continuous monitoring already running")
            return
        
        self.running = True
        self.pipeline_thread = threading.Thread(
            target=self._monitoring_loop,
            args=(interval_minutes,),
            daemon=True
        )
        self.pipeline_thread.start()
        self.logger.info(f"Continuous monitoring started (interval: {interval_minutes} minutes)")
    
    def stop_continuous_monitoring(self):
        """Stop continuous testing monitoring."""
        self.running = False
        if self.pipeline_thread:
            self.pipeline_thread.join(timeout=10)
        self.logger.info("Continuous monitoring stopped")
    
    def _monitoring_loop(self, interval_minutes: int):
        """Main monitoring loop."""
        while self.running:
            try:
                # Check for new commits
                git_info = self.get_git_info()
                
                # Check if we need to run tests
                should_run = False
                trigger = 'schedule'
                
                # Check if there's a new commit
                if self.test_history:
                    last_commit = self.test_history[-1].commit_hash
                    if git_info['commit_hash'] != last_commit:
                        should_run = True
                        trigger = 'commit'
                else:
                    should_run = True
                    trigger = 'initial'
                
                # Check scheduled interval
                if not should_run and self.test_history:
                    last_run_time = datetime.fromisoformat(self.test_history[-1].timestamp)
                    if datetime.now() - last_run_time > timedelta(hours=6):  # Run every 6 hours
                        should_run = True
                        trigger = 'schedule'
                
                if should_run:
                    self.logger.info(f"Triggering test run: {trigger}")
                    self.run_full_pipeline(trigger)
                
                # Sleep for the specified interval
                time.sleep(interval_minutes * 60)
                
            except Exception as e:
                self.logger.error(f"Error in monitoring loop: {e}")
                time.sleep(60)  # Wait 1 minute before retrying
    
    def generate_trend_report(self, output_file: str = 'trend_report.html'):
        """Generate trend analysis report."""
        if len(self.test_history) < 2:
            self.logger.warning("Not enough test history for trend analysis")
            return
        
        # Calculate trends
        recent_runs = self.test_history[-10:]  # Last 10 runs
        
        # Test duration trend
        durations = [run.duration for run in recent_runs]
        avg_duration = sum(durations) / len(durations)
        
        # Coverage trend
        coverages = [
            run.test_results.get('coverage', {}).get('line_coverage', 0)
            for run in recent_runs
        ]
        avg_coverage = sum(coverages) / len(coverages) if coverages else 0
        
        # Security score trend
        security_scores = [
            run.security_scan.get('security_score', 100)
            for run in recent_runs
        ]
        avg_security_score = sum(security_scores) / len(security_scores) if security_scores else 100
        
        html_content = f"""
<!DOCTYPE html>
<html>
<head>
    <title>Continuous Testing Trend Report</title>
    <style>
        body {{ font-family: Arial, sans-serif; margin: 20px; }}
        .summary {{ background: #f5f5f5; padding: 15px; border-radius: 5px; margin-bottom: 20px; }}
        .trend {{ margin: 20px 0; }}
        .alert {{ padding: 10px; margin: 5px 0; border-radius: 5px; }}
        .alert.critical {{ background: #f8d7da; }}
        .alert.major {{ background: #fff3cd; }}
        .alert.minor {{ background: #d1ecf1; }}
        table {{ width: 100%; border-collapse: collapse; margin: 20px 0; }}
        th, td {{ padding: 10px; text-align: left; border-bottom: 1px solid #ddd; }}
        th {{ background: #f8f9fa; }}
    </style>
</head>
<body>
    <h1>Continuous Testing Trend Report</h1>
    <p>Generated: {datetime.now().strftime('%Y-%m-%d %H:%M:%S')}</p>
    
    <div class="summary">
        <h2>Summary (Last 10 Runs)</h2>
        <p>Total Test Runs: {len(self.test_history)}</p>
        <p>Average Test Duration: {avg_duration:.2f} seconds</p>
        <p>Average Coverage: {avg_coverage:.1f}%</p>
        <p>Average Security Score: {avg_security_score:.1f}</p>
        <p>Total Regression Alerts: {len(self.regression_alerts)}</p>
    </div>
    
    <h2>Recent Regression Alerts</h2>
"""
        
        recent_alerts = [
            alert for alert in self.regression_alerts
            if datetime.fromisoformat(alert.timestamp) > datetime.now() - timedelta(days=7)
        ]
        
        if recent_alerts:
            for alert in recent_alerts[-10:]:  # Last 10 alerts
                html_content += f"""
    <div class="alert {alert.severity}">
        <strong>{alert.severity.upper()}</strong> - {alert.timestamp}<br>
        <strong>Metric:</strong> {alert.metric_name}<br>
        <strong>Change:</strong> {alert.baseline_value:.3f} → {alert.current_value:.3f} ({alert.regression_percentage:+.1f}%)
    </div>
"""
        else:
            html_content += "<p>No recent regression alerts</p>"
        
        html_content += """
    
    <h2>Test Run History</h2>
    <table>
        <thead>
            <tr>
                <th>Timestamp</th>
                <th>Commit</th>
                <th>Branch</th>
                <th>Status</th>
                <th>Duration</th>
                <th>Coverage</th>
                <th>Security Score</th>
            </tr>
        </thead>
        <tbody>
"""
        
        for run in reversed(recent_runs):
            coverage = run.test_results.get('coverage', {}).get('line_coverage', 0)
            security_score = run.security_scan.get('security_score', 100)
            
            html_content += f"""
            <tr>
                <td>{run.timestamp[:19]}</td>
                <td>{run.commit_hash[:8]}</td>
                <td>{run.branch}</td>
                <td>{run.status}</td>
                <td>{run.duration:.2f}s</td>
                <td>{coverage:.1f}%</td>
                <td>{security_score:.1f}</td>
            </tr>
"""
        
        html_content += """
        </tbody>
    </table>
    
</body>
</html>
"""
        
        with open(output_file, 'w') as f:
            f.write(html_content)
        
        self.logger.info(f"Trend report generated: {output_file}")
    
    def _run_command(self, command: List[str]) -> Dict[str, Any]:
        """Run a command and return result."""
        try:
            result = subprocess.run(
                command,
                capture_output=True,
                text=True,
                timeout=300,  # 5 minute timeout
                check=False
            )
            
            return {
                'command': ' '.join(command),
                'returncode': result.returncode,
                'stdout': result.stdout,
                'stderr': result.stderr
            }
            
        except subprocess.TimeoutExpired:
            return {
                'command': ' '.join(command),
                'returncode': -1,
                'stdout': '',
                'stderr': 'Command timed out'
            }
        except Exception as e:
            return {
                'command': ' '.join(command),
                'returncode': -1,
                'stdout': '',
                'stderr': str(e)
            }


def main():
    """Main function for continuous testing."""
    import argparse
    
    parser = argparse.ArgumentParser(description='Continuous testing pipeline')
    parser.add_argument('--run-once', action='store_true', help='Run pipeline once and exit')
    parser.add_argument('--monitor', action='store_true', help='Start continuous monitoring')
    parser.add_argument('--interval', type=int, default=60, help='Monitoring interval in minutes')
    parser.add_argument('--config', default='continuous_testing_config.json', help='Configuration file')
    parser.add_argument('--generate-report', action='store_true', help='Generate trend report')
    
    args = parser.parse_args()
    
    # Load configuration
    config = {}
    if Path(args.config).exists():
        with open(args.config, 'r') as f:
            config = json.load(f)
    
    pipeline = ContinuousTestingPipeline(config)
    
    if args.run_once:
        test_run = pipeline.run_full_pipeline('manual')
        print(f"Test run completed: {test_run.status}")
        print(f"Duration: {test_run.duration:.2f}s")
        if pipeline.regression_alerts:
            print(f"Regression alerts: {len(pipeline.regression_alerts)}")
    
    elif args.monitor:
        pipeline.start_continuous_monitoring(args.interval)
        try:
            print(f"Continuous monitoring started (interval: {args.interval} minutes)")
            print("Press Ctrl+C to stop...")
            while True:
                time.sleep(10)
        except KeyboardInterrupt:
            pipeline.stop_continuous_monitoring()
            print("Monitoring stopped")
    
    elif args.generate_report:
        pipeline.generate_trend_report()
        print("Trend report generated: trend_report.html")
    
    else:
        print("Please specify --run-once, --monitor, or --generate-report")


if __name__ == '__main__':
    main()