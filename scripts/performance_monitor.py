#!/usr/bin/env python3
"""
Performance monitoring and alerting system for evaluation engine.
"""

import asyncio
import time
import psutil
import json
import logging
from pathlib import Path
from typing import Dict, List, Any, Optional
from dataclasses import dataclass, asdict
import statistics
import threading
from datetime import datetime, timedelta


@dataclass
class PerformanceMetrics:
    """Performance metrics data structure."""
    timestamp: str
    cpu_usage: float
    memory_usage: float
    memory_available: float
    disk_usage: float
    network_io: Dict[str, int]
    process_count: int
    load_average: List[float]
    response_times: List[float]
    throughput: float
    error_rate: float


@dataclass
class PerformanceAlert:
    """Performance alert data structure."""
    timestamp: str
    severity: str  # 'warning', 'critical'
    metric: str
    value: float
    threshold: float
    message: str


class PerformanceMonitor:
    """Performance monitoring system."""
    
    def __init__(self, config: Dict[str, Any]):
        self.config = config
        self.metrics_history: List[PerformanceMetrics] = []
        self.alerts: List[PerformanceAlert] = []
        self.monitoring = False
        self.monitor_thread: Optional[threading.Thread] = None
        
        # Performance thresholds
        self.thresholds = config.get('thresholds', {
            'cpu_usage': {'warning': 80, 'critical': 95},
            'memory_usage': {'warning': 85, 'critical': 95},
            'disk_usage': {'warning': 85, 'critical': 95},
            'response_time': {'warning': 1.0, 'critical': 5.0},
            'error_rate': {'warning': 0.05, 'critical': 0.1},
            'throughput': {'warning': 10, 'critical': 5}  # minimum items/sec
        })
        
        # Setup logging
        logging.basicConfig(level=logging.INFO)
        self.logger = logging.getLogger(__name__)
    
    def collect_system_metrics(self) -> PerformanceMetrics:
        """Collect system performance metrics."""
        # CPU metrics
        cpu_usage = psutil.cpu_percent(interval=1)
        
        # Memory metrics
        memory = psutil.virtual_memory()
        memory_usage = memory.percent
        memory_available = memory.available / (1024**3)  # GB
        
        # Disk metrics
        disk = psutil.disk_usage('/')
        disk_usage = disk.percent
        
        # Network metrics
        network = psutil.net_io_counters()
        network_io = {
            'bytes_sent': network.bytes_sent,
            'bytes_recv': network.bytes_recv,
            'packets_sent': network.packets_sent,
            'packets_recv': network.packets_recv
        }
        
        # Process metrics
        process_count = len(psutil.pids())
        
        # Load average (Unix-like systems)
        try:
            load_average = list(psutil.getloadavg())
        except AttributeError:
            load_average = [0.0, 0.0, 0.0]  # Windows doesn't have load average
        
        return PerformanceMetrics(
            timestamp=datetime.now().isoformat(),
            cpu_usage=cpu_usage,
            memory_usage=memory_usage,
            memory_available=memory_available,
            disk_usage=disk_usage,
            network_io=network_io,
            process_count=process_count,
            load_average=load_average,
            response_times=[],  # Will be populated by application metrics
            throughput=0.0,     # Will be populated by application metrics
            error_rate=0.0      # Will be populated by application metrics
        )
    
    def check_thresholds(self, metrics: PerformanceMetrics):
        """Check metrics against thresholds and generate alerts."""
        checks = [
            ('cpu_usage', metrics.cpu_usage, '%'),
            ('memory_usage', metrics.memory_usage, '%'),
            ('disk_usage', metrics.disk_usage, '%'),
        ]
        
        # Add application-specific checks if data is available
        if metrics.response_times:
            avg_response_time = statistics.mean(metrics.response_times)
            checks.append(('response_time', avg_response_time, 's'))
        
        if metrics.error_rate > 0:
            checks.append(('error_rate', metrics.error_rate, ''))
        
        if metrics.throughput > 0:
            # For throughput, we alert if it's BELOW threshold
            throughput_thresholds = self.thresholds['throughput']
            if metrics.throughput < throughput_thresholds['critical']:
                self.create_alert('critical', 'throughput', metrics.throughput, 
                                throughput_thresholds['critical'], 
                                f"Throughput critically low: {metrics.throughput:.2f} items/sec")
            elif metrics.throughput < throughput_thresholds['warning']:
                self.create_alert('warning', 'throughput', metrics.throughput,
                                throughput_thresholds['warning'],
                                f"Throughput below warning threshold: {metrics.throughput:.2f} items/sec")
        
        # Check standard metrics
        for metric_name, value, unit in checks:
            if metric_name in self.thresholds:
                thresholds = self.thresholds[metric_name]
                
                if value >= thresholds['critical']:
                    self.create_alert('critical', metric_name, value, thresholds['critical'],
                                    f"{metric_name} critically high: {value:.2f}{unit}")
                elif value >= thresholds['warning']:
                    self.create_alert('warning', metric_name, value, thresholds['warning'],
                                    f"{metric_name} above warning threshold: {value:.2f}{unit}")
    
    def create_alert(self, severity: str, metric: str, value: float, threshold: float, message: str):
        """Create a performance alert."""
        alert = PerformanceAlert(
            timestamp=datetime.now().isoformat(),
            severity=severity,
            metric=metric,
            value=value,
            threshold=threshold,
            message=message
        )
        
        self.alerts.append(alert)
        self.logger.warning(f"Performance Alert [{severity.upper()}]: {message}")
        
        # Send notifications if configured
        if self.config.get('notifications', {}).get('enabled', False):
            self.send_alert_notification(alert)
    
    def send_alert_notification(self, alert: PerformanceAlert):
        """Send alert notification (placeholder for actual implementation)."""
        # This would integrate with actual notification systems
        # like Slack, email, PagerDuty, etc.
        notification_config = self.config.get('notifications', {})
        
        if notification_config.get('slack_webhook'):
            # Send to Slack
            pass
        
        if notification_config.get('email_recipients'):
            # Send email
            pass
        
        # For now, just log
        self.logger.info(f"Alert notification sent: {alert.message}")
    
    def start_monitoring(self, interval: int = 30):
        """Start continuous performance monitoring."""
        if self.monitoring:
            self.logger.warning("Monitoring already started")
            return
        
        self.monitoring = True
        self.monitor_thread = threading.Thread(
            target=self._monitoring_loop,
            args=(interval,),
            daemon=True
        )
        self.monitor_thread.start()
        self.logger.info(f"Performance monitoring started (interval: {interval}s)")
    
    def stop_monitoring(self):
        """Stop performance monitoring."""
        self.monitoring = False
        if self.monitor_thread:
            self.monitor_thread.join(timeout=5)
        self.logger.info("Performance monitoring stopped")
    
    def _monitoring_loop(self, interval: int):
        """Main monitoring loop."""
        while self.monitoring:
            try:
                metrics = self.collect_system_metrics()
                self.metrics_history.append(metrics)
                
                # Keep only recent metrics (last 24 hours)
                cutoff_time = datetime.now() - timedelta(hours=24)
                self.metrics_history = [
                    m for m in self.metrics_history
                    if datetime.fromisoformat(m.timestamp) > cutoff_time
                ]
                
                # Check thresholds
                self.check_thresholds(metrics)
                
                time.sleep(interval)
                
            except Exception as e:
                self.logger.error(f"Error in monitoring loop: {e}")
                time.sleep(interval)
    
    def get_current_metrics(self) -> Optional[PerformanceMetrics]:
        """Get the most recent metrics."""
        return self.metrics_history[-1] if self.metrics_history else None
    
    def get_metrics_summary(self, hours: int = 1) -> Dict[str, Any]:
        """Get performance metrics summary for the specified time period."""
        cutoff_time = datetime.now() - timedelta(hours=hours)
        recent_metrics = [
            m for m in self.metrics_history
            if datetime.fromisoformat(m.timestamp) > cutoff_time
        ]
        
        if not recent_metrics:
            return {}
        
        # Calculate statistics
        cpu_values = [m.cpu_usage for m in recent_metrics]
        memory_values = [m.memory_usage for m in recent_metrics]
        
        summary = {
            'time_period_hours': hours,
            'sample_count': len(recent_metrics),
            'cpu_usage': {
                'mean': statistics.mean(cpu_values),
                'max': max(cpu_values),
                'min': min(cpu_values),
                'stdev': statistics.stdev(cpu_values) if len(cpu_values) > 1 else 0
            },
            'memory_usage': {
                'mean': statistics.mean(memory_values),
                'max': max(memory_values),
                'min': min(memory_values),
                'stdev': statistics.stdev(memory_values) if len(memory_values) > 1 else 0
            },
            'alerts_count': len([a for a in self.alerts 
                               if datetime.fromisoformat(a.timestamp) > cutoff_time])
        }
        
        return summary
    
    def export_metrics(self, output_file: str, format: str = 'json'):
        """Export metrics to file."""
        if format == 'json':
            data = {
                'metrics': [asdict(m) for m in self.metrics_history],
                'alerts': [asdict(a) for a in self.alerts],
                'summary': self.get_metrics_summary(24)  # Last 24 hours
            }
            
            with open(output_file, 'w') as f:
                json.dump(data, f, indent=2)
        
        elif format == 'csv':
            import csv
            
            with open(output_file, 'w', newline='') as f:
                if self.metrics_history:
                    writer = csv.DictWriter(f, fieldnames=asdict(self.metrics_history[0]).keys())
                    writer.writeheader()
                    for metrics in self.metrics_history:
                        writer.writerow(asdict(metrics))
        
        self.logger.info(f"Metrics exported to {output_file}")
    
    def generate_performance_report(self, output_file: str = 'performance_report.html'):
        """Generate HTML performance report."""
        summary = self.get_metrics_summary(24)
        recent_alerts = [a for a in self.alerts 
                        if datetime.fromisoformat(a.timestamp) > datetime.now() - timedelta(hours=24)]
        
        html_content = f"""
<!DOCTYPE html>
<html>
<head>
    <title>Performance Monitoring Report</title>
    <style>
        body {{ font-family: Arial, sans-serif; margin: 20px; }}
        .summary {{ background: #f5f5f5; padding: 15px; border-radius: 5px; margin-bottom: 20px; }}
        .metric {{ margin: 10px 0; }}
        .alert {{ padding: 10px; margin: 5px 0; border-radius: 5px; }}
        .alert.warning {{ background: #fff3cd; border: 1px solid #ffeaa7; }}
        .alert.critical {{ background: #f8d7da; border: 1px solid #f5c6cb; }}
        .chart {{ width: 100%; height: 300px; background: #f9f9f9; margin: 20px 0; }}
    </style>
</head>
<body>
    <h1>Performance Monitoring Report</h1>
    <p>Generated: {datetime.now().strftime('%Y-%m-%d %H:%M:%S')}</p>
    
    <div class="summary">
        <h2>24-Hour Summary</h2>
        <div class="metric">Sample Count: {summary.get('sample_count', 0)}</div>
        <div class="metric">Average CPU Usage: {summary.get('cpu_usage', {}).get('mean', 0):.1f}%</div>
        <div class="metric">Peak CPU Usage: {summary.get('cpu_usage', {}).get('max', 0):.1f}%</div>
        <div class="metric">Average Memory Usage: {summary.get('memory_usage', {}).get('mean', 0):.1f}%</div>
        <div class="metric">Peak Memory Usage: {summary.get('memory_usage', {}).get('max', 0):.1f}%</div>
        <div class="metric">Total Alerts: {len(recent_alerts)}</div>
    </div>
    
    <h2>Recent Alerts</h2>
"""
        
        if recent_alerts:
            for alert in recent_alerts[-10:]:  # Show last 10 alerts
                html_content += f"""
    <div class="alert {alert.severity}">
        <strong>{alert.severity.upper()}</strong> - {alert.timestamp}<br>
        {alert.message}
    </div>
"""
        else:
            html_content += "<p>No recent alerts</p>"
        
        html_content += """
    
    <h2>Performance Trends</h2>
    <div class="chart">
        <!-- Placeholder for performance charts -->
        <p>Performance charts would be displayed here in a full implementation</p>
    </div>
    
</body>
</html>
"""
        
        with open(output_file, 'w') as f:
            f.write(html_content)
        
        self.logger.info(f"Performance report generated: {output_file}")


class LoadTester:
    """Load testing utilities for performance validation."""
    
    def __init__(self, target_url: str = "http://localhost:8000"):
        self.target_url = target_url
        self.results: List[Dict[str, Any]] = []
    
    async def run_load_test(self, 
                           concurrent_users: int = 10,
                           duration_seconds: int = 60,
                           requests_per_second: int = 10) -> Dict[str, Any]:
        """Run load test against the evaluation engine."""
        import aiohttp
        
        self.results = []
        start_time = time.time()
        end_time = start_time + duration_seconds
        
        # Create semaphore to limit concurrent requests
        semaphore = asyncio.Semaphore(concurrent_users)
        
        async def make_request(session: aiohttp.ClientSession, endpoint: str):
            async with semaphore:
                request_start = time.time()
                try:
                    async with session.get(f"{self.target_url}{endpoint}") as response:
                        await response.text()
                        request_end = time.time()
                        
                        self.results.append({
                            'timestamp': request_start,
                            'endpoint': endpoint,
                            'status_code': response.status,
                            'response_time': request_end - request_start,
                            'success': 200 <= response.status < 400
                        })
                        
                except Exception as e:
                    request_end = time.time()
                    self.results.append({
                        'timestamp': request_start,
                        'endpoint': endpoint,
                        'status_code': 0,
                        'response_time': request_end - request_start,
                        'success': False,
                        'error': str(e)
                    })
        
        # Test endpoints
        endpoints = [
            '/api/v1/health',
            '/api/v1/tasks',
            '/api/v1/models',
            '/api/v1/evaluations'
        ]
        
        async with aiohttp.ClientSession() as session:
            tasks = []
            
            while time.time() < end_time:
                # Create batch of requests
                for _ in range(requests_per_second):
                    endpoint = endpoints[len(tasks) % len(endpoints)]
                    task = asyncio.create_task(make_request(session, endpoint))
                    tasks.append(task)
                
                # Wait for batch to complete or timeout
                await asyncio.sleep(1.0 / requests_per_second)
            
            # Wait for remaining tasks
            await asyncio.gather(*tasks, return_exceptions=True)
        
        # Calculate statistics
        successful_requests = [r for r in self.results if r['success']]
        failed_requests = [r for r in self.results if not r['success']]
        
        response_times = [r['response_time'] for r in successful_requests]
        
        stats = {
            'duration': time.time() - start_time,
            'total_requests': len(self.results),
            'successful_requests': len(successful_requests),
            'failed_requests': len(failed_requests),
            'success_rate': len(successful_requests) / len(self.results) if self.results else 0,
            'requests_per_second': len(self.results) / (time.time() - start_time),
            'response_times': {
                'mean': statistics.mean(response_times) if response_times else 0,
                'median': statistics.median(response_times) if response_times else 0,
                'p95': statistics.quantiles(response_times, n=20)[18] if len(response_times) > 20 else 0,
                'p99': statistics.quantiles(response_times, n=100)[98] if len(response_times) > 100 else 0,
                'min': min(response_times) if response_times else 0,
                'max': max(response_times) if response_times else 0
            }
        }
        
        return stats
    
    def generate_load_test_report(self, stats: Dict[str, Any], output_file: str = 'load_test_report.html'):
        """Generate load test report."""
        html_content = f"""
<!DOCTYPE html>
<html>
<head>
    <title>Load Test Report</title>
    <style>
        body {{ font-family: Arial, sans-serif; margin: 20px; }}
        .summary {{ background: #f5f5f5; padding: 15px; border-radius: 5px; margin-bottom: 20px; }}
        .metric {{ margin: 10px 0; }}
        .good {{ color: green; }}
        .warning {{ color: orange; }}
        .bad {{ color: red; }}
    </style>
</head>
<body>
    <h1>Load Test Report</h1>
    <p>Generated: {datetime.now().strftime('%Y-%m-%d %H:%M:%S')}</p>
    
    <div class="summary">
        <h2>Test Summary</h2>
        <div class="metric">Duration: {stats['duration']:.2f} seconds</div>
        <div class="metric">Total Requests: {stats['total_requests']}</div>
        <div class="metric">Successful Requests: {stats['successful_requests']}</div>
        <div class="metric">Failed Requests: {stats['failed_requests']}</div>
        <div class="metric">Success Rate: <span class="{'good' if stats['success_rate'] > 0.95 else 'warning' if stats['success_rate'] > 0.9 else 'bad'}">{stats['success_rate']:.2%}</span></div>
        <div class="metric">Requests/Second: <span class="{'good' if stats['requests_per_second'] > 50 else 'warning' if stats['requests_per_second'] > 20 else 'bad'}">{stats['requests_per_second']:.2f}</span></div>
    </div>
    
    <div class="summary">
        <h2>Response Time Statistics</h2>
        <div class="metric">Mean: {stats['response_times']['mean']:.3f}s</div>
        <div class="metric">Median: {stats['response_times']['median']:.3f}s</div>
        <div class="metric">95th Percentile: {stats['response_times']['p95']:.3f}s</div>
        <div class="metric">99th Percentile: {stats['response_times']['p99']:.3f}s</div>
        <div class="metric">Min: {stats['response_times']['min']:.3f}s</div>
        <div class="metric">Max: {stats['response_times']['max']:.3f}s</div>
    </div>
    
</body>
</html>
"""
        
        with open(output_file, 'w') as f:
            f.write(html_content)
        
        print(f"Load test report generated: {output_file}")


def main():
    """Main function for performance monitoring."""
    import argparse
    
    parser = argparse.ArgumentParser(description='Performance monitoring and load testing')
    parser.add_argument('--monitor', action='store_true', help='Start performance monitoring')
    parser.add_argument('--load-test', action='store_true', help='Run load test')
    parser.add_argument('--duration', type=int, default=60, help='Test duration in seconds')
    parser.add_argument('--users', type=int, default=10, help='Concurrent users for load test')
    parser.add_argument('--rps', type=int, default=10, help='Requests per second')
    parser.add_argument('--url', default='http://localhost:8000', help='Target URL')
    parser.add_argument('--config', default='performance_config.json', help='Configuration file')
    
    args = parser.parse_args()
    
    # Load configuration
    config = {}
    if Path(args.config).exists():
        with open(args.config, 'r') as f:
            config = json.load(f)
    
    if args.monitor:
        monitor = PerformanceMonitor(config)
        monitor.start_monitoring()
        
        try:
            print("Performance monitoring started. Press Ctrl+C to stop.")
            while True:
                time.sleep(10)
                current_metrics = monitor.get_current_metrics()
                if current_metrics:
                    print(f"CPU: {current_metrics.cpu_usage:.1f}%, "
                          f"Memory: {current_metrics.memory_usage:.1f}%, "
                          f"Alerts: {len(monitor.alerts)}")
        except KeyboardInterrupt:
            monitor.stop_monitoring()
            monitor.export_metrics('performance_metrics.json')
            monitor.generate_performance_report()
            print("Monitoring stopped and results exported.")
    
    if args.load_test:
        load_tester = LoadTester(args.url)
        
        print(f"Starting load test: {args.users} users, {args.duration}s duration, {args.rps} RPS")
        stats = asyncio.run(load_tester.run_load_test(
            concurrent_users=args.users,
            duration_seconds=args.duration,
            requests_per_second=args.rps
        ))
        
        print(f"Load test completed:")
        print(f"  Total requests: {stats['total_requests']}")
        print(f"  Success rate: {stats['success_rate']:.2%}")
        print(f"  Requests/second: {stats['requests_per_second']:.2f}")
        print(f"  Mean response time: {stats['response_times']['mean']:.3f}s")
        print(f"  95th percentile: {stats['response_times']['p95']:.3f}s")
        
        load_tester.generate_load_test_report(stats)


if __name__ == '__main__':
    main()