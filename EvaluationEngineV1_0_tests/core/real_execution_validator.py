"""
Real execution validator to ensure tests use actual execution without mocks.
"""

import logging
import inspect
import sys
import gc
import re
import json
import hashlib
import socket
import subprocess
import statistics
from typing import Dict, List, Optional, Any, Set, Tuple
from unittest.mock import Mock, MagicMock, patch
from unittest import mock
import psutil
import time
import threading
import requests
from pathlib import Path
from collections import defaultdict
import urllib.parse

try:
    from ..models.test_models import TestResult, TestConfiguration, ExecutionMetrics
    from .error_handler import ValidationError
except ImportError:
    # Fallback for direct execution
    import sys
    import os
    sys.path.append(os.path.dirname(os.path.dirname(os.path.abspath(__file__))))
    from models.test_models import TestResult, TestConfiguration, ExecutionMetrics
    from core.error_handler import ValidationError


class RealExecutionValidator:
    """Validates that tests perform real execution without mock data."""
    
    def __init__(self):
        self.logger = logging.getLogger(f"{__name__}.RealExecutionValidator")
        self._mock_detection_enabled = True
        self._resource_tracking_enabled = True
        self._api_call_tracking_enabled = True
        self._network_tracking_enabled = True
        
        # Tracking state
        self._initial_memory = None
        self._initial_cpu_time = None
        self._api_calls_made = []
        self._mock_objects_found = []
        self._resource_snapshots = []
        self._network_connections = []
        self._file_operations = []
        
        # Validation thresholds (can be customized)
        self._validation_thresholds = {
            'min_execution_time': 0.1,  # seconds
            'min_memory_growth': 1024 * 1024,  # 1MB
            'min_api_calls': 1,
            'min_network_activity': 1,
            'max_success_rate': 0.99,  # Allow some failures for realism
            'min_response_time_variance': 0.01  # seconds
        }
        
        # Mock framework detection patterns
        self._mock_frameworks = {
            'unittest.mock', 'mock', 'pytest', 'responses', 'httpretty', 
            'requests_mock', 'freezegun', 'fakeredis', 'mongomock',
            'moto', 'vcrpy', 'betamax'
        }
        
        # Known model API endpoints for validation
        self._model_api_patterns = [
            r'api\.openai\.com',
            r'api\.anthropic\.com',
            r'api\.cohere\.ai',
            r'api\.huggingface\.co',
            r'dashscope\.aliyuncs\.com',
            r'api\.deepseek\.com',
            r'generativelanguage\.googleapis\.com'
        ]
    
    def validate_real_execution(self, test_result: TestResult, 
                               test_config: TestConfiguration) -> bool:
        """Validate that test execution was real and not mocked."""
        self.logger.info(f"Validating real execution for test: {test_result.test_id}")
        
        validation_results = {
            "no_mocks": self._validate_no_mocks(),
            "resource_consumption": self._validate_resource_consumption(test_result),
            "api_calls": self._validate_actual_api_calls(test_result),
            "execution_artifacts": self._validate_execution_artifacts(test_result),
            "timing_patterns": self._validate_timing_patterns(test_result)
        }
        
        # Log validation details
        for check, passed in validation_results.items():
            status = "PASSED" if passed else "FAILED"
            self.logger.info(f"Real execution check '{check}': {status}")
        
        # Overall validation passes if all checks pass
        overall_valid = all(validation_results.values())
        
        if not overall_valid:
            failed_checks = [check for check, passed in validation_results.items() if not passed]
            self.logger.warning(f"Real execution validation failed for checks: {failed_checks}")
        else:
            self.logger.info("Real execution validation passed all checks")
        
        return overall_valid
    
    def start_tracking(self) -> None:
        """Start tracking execution for validation."""
        self.logger.debug("Starting real execution tracking")
        
        # Record initial resource state
        if self._resource_tracking_enabled:
            try:
                process = psutil.Process()
                self._initial_memory = process.memory_info().rss
                self._initial_cpu_time = process.cpu_times().user + process.cpu_times().system
                self._resource_snapshots = []
            except Exception as e:
                self.logger.warning(f"Failed to initialize resource tracking: {e}")
        
        # Clear tracking state
        self._api_calls_made.clear()
        self._mock_objects_found.clear()
        self._network_connections.clear()
        self._file_operations.clear()
    
    def stop_tracking(self) -> None:
        """Stop tracking execution."""
        self.logger.debug("Stopping real execution tracking")
    
    def record_api_call(self, endpoint: str, method: str, response_data: Any) -> None:
        """Record an API call for validation."""
        if self._api_call_tracking_enabled:
            self._api_calls_made.append({
                "endpoint": endpoint,
                "method": method,
                "response_data": response_data,
                "timestamp": time.time()
            })
    
    def record_resource_snapshot(self) -> None:
        """Record a resource usage snapshot."""
        if self._resource_tracking_enabled:
            try:
                process = psutil.Process()
                snapshot = {
                    "timestamp": time.time(),
                    "memory_rss": process.memory_info().rss,
                    "memory_vms": process.memory_info().vms,
                    "cpu_percent": process.cpu_percent(),
                    "num_threads": process.num_threads()
                }
                self._resource_snapshots.append(snapshot)
            except Exception as e:
                self.logger.warning(f"Failed to record resource snapshot: {e}")
    
    def record_network_connection(self, destination: str, port: int, 
                                bytes_sent: int, bytes_received: int) -> None:
        """Record a network connection for validation."""
        if self._network_tracking_enabled:
            connection = {
                "timestamp": time.time(),
                "destination": destination,
                "port": port,
                "bytes_sent": bytes_sent,
                "bytes_received": bytes_received
            }
            self._network_connections.append(connection)
    
    def record_file_operation(self, operation: str, path: str, size: int = 0) -> None:
        """Record a file system operation for validation."""
        file_op = {
            "timestamp": time.time(),
            "operation": operation,
            "path": path,
            "size": size
        }
        self._file_operations.append(file_op)
    
    def _validate_no_mocks(self) -> bool:
        """Validate that no mock objects are present in the system."""
        if not self._mock_detection_enabled:
            return True
        
        mock_objects = self._find_mock_objects()
        
        if mock_objects:
            self.logger.warning(f"Found {len(mock_objects)} mock objects in system")
            for mock_info in mock_objects[:5]:  # Log first 5
                self.logger.warning(f"Mock object: {mock_info}")
            return False
        
        return True
    
    def _validate_resource_consumption(self, test_result: TestResult) -> bool:
        """Validate realistic resource consumption patterns."""
        if not self._resource_tracking_enabled or not self._initial_memory:
            return True
        
        try:
            current_process = psutil.Process()
            current_memory = current_process.memory_info().rss
            memory_growth = current_memory - self._initial_memory
            
            # Check for reasonable memory usage (at least some growth expected for real execution)
            min_expected_growth = 1024 * 1024  # 1MB minimum
            max_reasonable_growth = 1024 * 1024 * 1024  # 1GB maximum
            
            if memory_growth < min_expected_growth:
                self.logger.warning(f"Suspiciously low memory growth: {memory_growth} bytes")
                return False
            
            if memory_growth > max_reasonable_growth:
                self.logger.warning(f"Excessive memory growth: {memory_growth} bytes")
                return False
            
            # Check execution time is reasonable
            if test_result.execution_time < 0.1:  # Less than 100ms is suspicious for real execution
                self.logger.warning(f"Suspiciously fast execution time: {test_result.execution_time}s")
                return False
            
            return True
            
        except Exception as e:
            self.logger.warning(f"Resource consumption validation failed: {e}")
            return False
    
    def _validate_actual_api_calls(self, test_result: TestResult) -> bool:
        """Validate that actual API calls were made."""
        if not self._api_call_tracking_enabled:
            return True
        
        # For tests that should make API calls, verify they were made
        expected_api_calls = self._get_expected_api_calls(test_result)
        
        if expected_api_calls and not self._api_calls_made:
            self.logger.warning("Expected API calls but none were recorded")
            return False
        
        # Validate API call patterns
        for api_call in self._api_calls_made:
            if not self._validate_api_call_authenticity(api_call):
                return False
        
        return True
    
    def _validate_execution_artifacts(self, test_result: TestResult) -> bool:
        """Validate that execution produced realistic artifacts."""
        # Check for presence of logs
        if not test_result.logs:
            self.logger.warning("No execution logs found - suspicious for real execution")
            return False
        
        # Check log content for real execution indicators
        real_execution_indicators = [
            "http", "request", "response", "model", "evaluation", 
            "task", "result", "score", "time", "error"
        ]
        
        log_content = " ".join(test_result.logs).lower()
        indicators_found = sum(1 for indicator in real_execution_indicators 
                              if indicator in log_content)
        
        if indicators_found < 2:  # At least 2 indicators expected
            self.logger.warning(f"Few real execution indicators in logs: {indicators_found}")
            return False
        
        # Check for metrics that indicate real computation
        if not test_result.metrics:
            self.logger.warning("No metrics recorded - suspicious for real execution")
            return False
        
        return True
    
    def _validate_timing_patterns(self, test_result: TestResult) -> bool:
        """Validate that timing patterns are consistent with real execution."""
        # Real execution should have some variability and minimum duration
        if test_result.execution_time <= 0:
            self.logger.warning("Zero or negative execution time")
            return False
        
        # Check for suspiciously round numbers (might indicate fake timing)
        if test_result.execution_time == round(test_result.execution_time):
            self.logger.warning(f"Suspiciously round execution time: {test_result.execution_time}")
            return False
        
        # Check resource snapshots for realistic patterns
        if self._resource_snapshots and len(self._resource_snapshots) > 1:
            memory_values = [s["memory_rss"] for s in self._resource_snapshots]
            if len(set(memory_values)) == 1:  # All values identical
                self.logger.warning("No memory usage variation during execution")
                return False
        
        return True
    
    def _find_mock_objects(self) -> List[str]:
        """Find mock objects in the current Python environment."""
        mock_objects = []
        
        try:
            # Check all objects in garbage collector
            for obj in gc.get_objects():
                if isinstance(obj, (Mock, MagicMock)):
                    mock_info = f"{type(obj).__name__} at {id(obj)}"
                    mock_objects.append(mock_info)
                    self._mock_objects_found.append(obj)
            
            # Check modules for mock patches
            for module_name, module in sys.modules.items():
                if module is None:
                    continue
                
                try:
                    for attr_name in dir(module):
                        attr = getattr(module, attr_name, None)
                        if isinstance(attr, (Mock, MagicMock)):
                            mock_info = f"{module_name}.{attr_name}"
                            mock_objects.append(mock_info)
                except Exception:
                    continue  # Skip modules that can't be inspected
            
        except Exception as e:
            self.logger.warning(f"Error during mock detection: {e}")
        
        return mock_objects
    
    def _get_expected_api_calls(self, test_result: TestResult) -> List[str]:
        """Get expected API calls based on test type."""
        expected_calls = []
        
        # Determine expected calls based on test type and configuration
        if test_result.test_type.value == "api":
            expected_calls = ["evaluation_api", "status_api"]
        elif test_result.test_type.value == "adapter":
            expected_calls = ["model_api", "evaluation_api"]
        elif "lm_eval" in test_result.name.lower():
            expected_calls = ["model_api"]
        
        return expected_calls
    
    def _validate_api_call_authenticity(self, api_call: Dict[str, Any]) -> bool:
        """Validate that an API call appears authentic."""
        # Check for realistic response data
        response_data = api_call.get("response_data")
        
        if response_data is None:
            return True  # No response data to validate
        
        # Check for mock-like response patterns
        if isinstance(response_data, dict):
            # Look for overly simple or fake-looking responses
            if len(response_data) == 1 and "mock" in str(response_data).lower():
                self.logger.warning(f"Suspicious API response: {response_data}")
                return False
            
            # Check for realistic response structure
            if "error" in response_data or "result" in response_data or "data" in response_data:
                return True  # Looks like a real API response
        
        return True
    
    def get_validation_report(self) -> Dict[str, Any]:
        """Get a detailed validation report."""
        return {
            "mock_objects_found": len(self._mock_objects_found),
            "api_calls_recorded": len(self._api_calls_made),
            "resource_snapshots": len(self._resource_snapshots),
            "validation_enabled": {
                "mock_detection": self._mock_detection_enabled,
                "resource_tracking": self._resource_tracking_enabled,
                "api_call_tracking": self._api_call_tracking_enabled
            },
            "memory_growth": self._calculate_memory_growth(),
            "execution_indicators": self._get_execution_indicators()
        }
    
    def _calculate_memory_growth(self) -> Optional[int]:
        """Calculate memory growth during execution."""
        if not self._initial_memory:
            return None
        
        try:
            current_memory = psutil.Process().memory_info().rss
            return current_memory - self._initial_memory
        except Exception:
            return None
    
    def _get_execution_indicators(self) -> Dict[str, int]:
        """Get counts of various execution indicators."""
        return {
            "mock_objects": len(self._mock_objects_found),
            "api_calls": len(self._api_calls_made),
            "resource_snapshots": len(self._resource_snapshots),
            "network_connections": len(self._network_connections),
            "file_operations": len(self._file_operations)
        }
    
    # Additional validation methods referenced in tests
    
    def validate_no_mocks(self, execution_context: Dict[str, Any]) -> bool:
        """Validate that no mock objects are present in execution context."""
        if not self._mock_detection_enabled:
            return True
        
        # Check for mock objects in context
        if execution_context.get('mock_objects_detected', False):
            self.logger.warning("Mock objects detected in execution context")
            return False
        
        # Check for lack of real activity indicators
        if not execution_context.get('api_calls_made', False) and \
           not execution_context.get('network_activity', False):
            self.logger.warning("No real activity indicators found")
            return False
        
        # Use existing mock detection
        mock_objects = self._find_mock_objects()
        if mock_objects:
            self.logger.warning(f"Found {len(mock_objects)} mock objects")
            return False
        
        return True
    
    def validate_actual_model_calls(self, api_logs: List[Dict[str, Any]]) -> bool:
        """Validate that actual model API calls were made."""
        if not api_logs:
            self.logger.warning("No API logs provided for validation")
            return False
        
        model_api_calls = 0
        for log_entry in api_logs:
            endpoint = log_entry.get('endpoint', '')
            
            # Check if endpoint matches known model API patterns
            for pattern in self._model_api_patterns:
                if re.search(pattern, endpoint):
                    model_api_calls += 1
                    break
            
            # Validate response characteristics
            if not self._validate_api_response_authenticity(log_entry):
                return False
        
        if model_api_calls == 0:
            self.logger.warning("No model API calls found in logs")
            return False
        
        self.logger.info(f"Validated {model_api_calls} model API calls")
        return True
    
    def validate_genuine_results(self, results: Dict[str, Any]) -> bool:
        """Validate that results appear genuine and not fabricated."""
        if not results:
            self.logger.warning("No results provided for validation")
            return False
        
        # Check for realistic score distributions
        scores = results.get('scores', [])
        if scores:
            if not self._validate_score_distribution(scores):
                return False
        
        # Check for realistic response times
        response_times = results.get('response_times', [])
        if response_times:
            if not self._validate_response_time_patterns(response_times):
                return False
        
        # Check for realistic token counts
        token_counts = results.get('token_counts', [])
        if token_counts:
            if not self._validate_token_count_patterns(token_counts):
                return False
        
        # Check for realistic metadata
        metadata = results.get('metadata', {})
        if not self._validate_result_metadata(metadata):
            return False
        
        return True
    
    def validate_resource_consumption(self, metrics: ExecutionMetrics) -> bool:
        """Validate that resource consumption appears realistic."""
        # Check execution time
        if metrics.total_execution_time < self._validation_thresholds['min_execution_time']:
            self.logger.warning(f"Execution time too low: {metrics.total_execution_time}s")
            return False
        
        # Check memory usage
        peak_memory = metrics.memory_usage.get('peak_mb', 0)
        if peak_memory < 10:  # Less than 10MB is suspicious
            self.logger.warning(f"Memory usage too low: {peak_memory}MB")
            return False
        
        # Check for realistic API response times
        api_times = metrics.api_response_times
        for endpoint, times in api_times.items():
            if isinstance(times, list) and len(times) > 1:
                if not self._validate_response_time_variance(times):
                    return False
        
        # Check success rates (too perfect is suspicious)
        overall_success = metrics.success_rates.get('overall', 1.0)
        if overall_success > self._validation_thresholds['max_success_rate']:
            self.logger.warning(f"Success rate too perfect: {overall_success}")
            return False
        
        return True
    
    def detect_mock_frameworks(self) -> bool:
        """Detect if mock frameworks are present in the system."""
        loaded_modules = set(sys.modules.keys())
        mock_modules_found = loaded_modules.intersection(self._mock_frameworks)
        
        if mock_modules_found:
            self.logger.warning(f"Mock frameworks detected: {mock_modules_found}")
            return True
        
        return False
    
    def validate_network_activity(self, network_logs: List[Dict[str, Any]]) -> bool:
        """Validate that actual network activity occurred."""
        if not network_logs:
            self.logger.warning("No network activity logs provided")
            return False
        
        total_bytes_sent = 0
        total_bytes_received = 0
        
        for log_entry in network_logs:
            bytes_sent = log_entry.get('bytes_sent', 0)
            bytes_received = log_entry.get('bytes_received', 0)
            
            total_bytes_sent += bytes_sent
            total_bytes_received += bytes_received
            
            # Validate realistic network patterns
            if not self._validate_network_entry(log_entry):
                return False
        
        # Check for minimum network activity
        min_activity = 512  # 512 bytes minimum
        if total_bytes_sent < min_activity or total_bytes_received < min_activity:
            self.logger.warning(f"Network activity too low: sent={total_bytes_sent}, received={total_bytes_received}")
            return False
        
        return True
    
    def validate_file_system_operations(self, fs_operations: List[Dict[str, Any]]) -> bool:
        """Validate file system operations."""
        if not fs_operations:
            return True  # File operations are optional
        
        for operation in fs_operations:
            if not self._validate_fs_operation(operation):
                return False
        
        return True
    
    def comprehensive_validation(self, execution_data: Dict[str, Any]) -> bool:
        """Perform comprehensive validation of execution data."""
        test_result = execution_data.get('test_result')
        if not test_result:
            self.logger.error("No test result provided for validation")
            return False
        
        validation_checks = []
        
        # Validate API logs
        api_logs = execution_data.get('api_logs', [])
        if api_logs:
            validation_checks.append(self.validate_actual_model_calls(api_logs))
        
        # Validate network activity
        network_logs = execution_data.get('network_logs', [])
        if network_logs:
            validation_checks.append(self.validate_network_activity(network_logs))
        
        # Validate resource metrics
        resource_metrics = execution_data.get('resource_metrics')
        if resource_metrics:
            validation_checks.append(self.validate_resource_consumption(resource_metrics))
        
        # Validate test result itself
        validation_checks.append(self._validate_test_result_authenticity(test_result))
        
        # Check for mock frameworks (only if mock detection is enabled)
        if self._mock_detection_enabled:
            validation_checks.append(not self.detect_mock_frameworks())
        else:
            validation_checks.append(True)  # Pass this check if disabled
        
        # Overall validation passes if most checks pass (allow some flexibility)
        passed_checks = sum(validation_checks)
        total_checks = len(validation_checks)
        
        if total_checks == 0:
            return False
        
        success_rate = passed_checks / total_checks
        threshold = 0.8  # 80% of checks must pass
        
        is_valid = success_rate >= threshold
        self.logger.info(f"Comprehensive validation: {passed_checks}/{total_checks} checks passed ({success_rate:.2%})")
        
        return is_valid
    
    def generate_validation_report(self, execution_data: Dict[str, Any]) -> Dict[str, Any]:
        """Generate a detailed validation report."""
        test_result = execution_data.get('test_result')
        api_logs = execution_data.get('api_logs', [])
        network_logs = execution_data.get('network_logs', [])
        resource_metrics = execution_data.get('resource_metrics')
        
        # Perform individual validations
        checks = {
            'mock_detection': not self.detect_mock_frameworks() if self._mock_detection_enabled else True,
            'api_calls': self.validate_actual_model_calls(api_logs) if api_logs else None,
            'network_activity': self.validate_network_activity(network_logs) if network_logs else None,
            'resource_consumption': self.validate_resource_consumption(resource_metrics) if resource_metrics else None,
            'result_authenticity': self._validate_test_result_authenticity(test_result) if test_result else None
        }
        
        # Calculate overall validation result
        valid_checks = [v for v in checks.values() if v is not None]
        validation_result = sum(valid_checks) / len(valid_checks) if valid_checks else False
        
        # Calculate confidence score
        confidence_score = self._calculate_confidence_score(execution_data, checks)
        
        return {
            'validation_result': validation_result > 0.8,
            'confidence_score': confidence_score,
            'checks_performed': {k: v for k, v in checks.items() if v is not None},
            'evidence': {
                'api_calls_count': len(api_logs),
                'network_connections': len(network_logs),
                'execution_time': test_result.execution_time if test_result else 0,
                'memory_usage': resource_metrics.memory_usage if resource_metrics else {},
                'mock_frameworks_detected': self.detect_mock_frameworks()
            },
            'recommendations': self._generate_recommendations(checks)
        }
    
    def set_validation_thresholds(self, thresholds: Dict[str, Any]) -> None:
        """Set custom validation thresholds."""
        self._validation_thresholds.update(thresholds)
        self.logger.info(f"Updated validation thresholds: {thresholds}")
    
    # Helper methods for validation
    
    def _validate_api_response_authenticity(self, log_entry: Dict[str, Any]) -> bool:
        """Validate that an API response appears authentic."""
        # Check for realistic status codes
        status_code = log_entry.get('status_code', 0)
        if status_code not in [200, 201, 400, 401, 403, 404, 429, 500, 502, 503]:
            return False
        
        # Check for realistic response times
        response_time = log_entry.get('response_time', 0)
        if response_time <= 0 or response_time > 60:  # 0-60 seconds is reasonable
            return False
        
        # Check for realistic token usage
        tokens_used = log_entry.get('tokens_used', 0)
        if tokens_used < 0 or tokens_used > 100000:  # Reasonable token range
            return False
        
        return True
    
    def _validate_score_distribution(self, scores: List[float]) -> bool:
        """Validate that score distribution appears realistic."""
        if len(scores) < 2:
            return True  # Can't validate distribution with < 2 scores
        
        # Check for perfect scores (suspicious)
        perfect_scores = sum(1 for score in scores if score == 1.0)
        if perfect_scores == len(scores):
            self.logger.warning("All scores are perfect (1.0) - suspicious")
            return False
        
        # Check for variance (identical scores are suspicious)
        if len(set(scores)) == 1:
            self.logger.warning("All scores are identical - suspicious")
            return False
        
        # Check for reasonable range
        if min(scores) < 0 or max(scores) > 1:
            self.logger.warning("Scores outside valid range [0, 1]")
            return False
        
        return True
    
    def _validate_response_time_patterns(self, response_times: List[float]) -> bool:
        """Validate response time patterns."""
        if len(response_times) < 2:
            return True
        
        # Check for identical response times (suspicious)
        if len(set(response_times)) == 1:
            self.logger.warning("All response times are identical - suspicious")
            return False
        
        # Check for reasonable variance
        if len(response_times) > 2:
            variance = statistics.variance(response_times)
            if variance < self._validation_thresholds['min_response_time_variance']:
                self.logger.warning(f"Response time variance too low: {variance}")
                return False
        
        return True
    
    def _validate_token_count_patterns(self, token_counts: List[int]) -> bool:
        """Validate token count patterns."""
        if len(token_counts) < 2:
            return True
        
        # Check for identical token counts (suspicious)
        if len(set(token_counts)) == 1:
            self.logger.warning("All token counts are identical - suspicious")
            return False
        
        # Check for reasonable range
        if any(count < 0 or count > 100000 for count in token_counts):
            self.logger.warning("Token counts outside reasonable range")
            return False
        
        return True
    
    def _validate_result_metadata(self, metadata: Dict[str, Any]) -> bool:
        """Validate result metadata for authenticity."""
        if not metadata:
            self.logger.warning("No metadata provided - suspicious")
            return False
        
        # Check for realistic timestamp
        timestamp = metadata.get('timestamp')
        if timestamp:
            current_time = time.time()
            if abs(current_time - timestamp) > 3600:  # More than 1 hour difference
                self.logger.warning("Timestamp too far from current time")
                return False
        
        # Check for model version information
        model_version = metadata.get('model_version')
        if not model_version:
            self.logger.warning("No model version in metadata")
            return False
        
        return True
    
    def _validate_response_time_variance(self, times: List[float]) -> bool:
        """Validate response time variance."""
        if len(times) < 2:
            return True
        
        variance = statistics.variance(times)
        return variance >= self._validation_thresholds['min_response_time_variance']
    
    def _validate_network_entry(self, log_entry: Dict[str, Any]) -> bool:
        """Validate a single network log entry."""
        destination = log_entry.get('destination', '')
        if not destination:
            return False
        
        # Check for realistic port numbers
        port = log_entry.get('port', 0)
        if port <= 0 or port > 65535:
            return False
        
        # Check for realistic byte counts
        bytes_sent = log_entry.get('bytes_sent', 0)
        bytes_received = log_entry.get('bytes_received', 0)
        
        if bytes_sent < 0 or bytes_received < 0:
            return False
        
        return True
    
    def _validate_fs_operation(self, operation: Dict[str, Any]) -> bool:
        """Validate a file system operation."""
        op_type = operation.get('operation', '')
        if op_type not in ['read', 'write', 'delete', 'create']:
            return False
        
        path = operation.get('path', '')
        if not path:
            return False
        
        size = operation.get('size', 0)
        if size < 0:
            return False
        
        return True
    
    def _validate_test_result_authenticity(self, test_result: TestResult) -> bool:
        """Validate that a test result appears authentic."""
        # Check execution time
        if test_result.execution_time <= 0:
            return False
        
        # Check for realistic metrics
        if not test_result.metrics:
            self.logger.warning("No metrics in test result")
            return False
        
        # Check for logs (real execution should produce logs)
        if not test_result.logs:
            self.logger.warning("No logs in test result")
            return False
        
        return True
    
    def _calculate_confidence_score(self, execution_data: Dict[str, Any], 
                                  checks: Dict[str, Any]) -> float:
        """Calculate confidence score for validation."""
        score = 0.0
        max_score = 0.0
        
        # Weight different types of evidence
        weights = {
            'mock_detection': 0.3,
            'api_calls': 0.25,
            'network_activity': 0.2,
            'resource_consumption': 0.15,
            'result_authenticity': 0.1
        }
        
        for check_name, result in checks.items():
            if result is not None:
                weight = weights.get(check_name, 0.1)
                max_score += weight
                if result:
                    score += weight
        
        return score / max_score if max_score > 0 else 0.0
    
    def _generate_recommendations(self, checks: Dict[str, Any]) -> List[str]:
        """Generate recommendations based on validation results."""
        recommendations = []
        
        if checks.get('mock_detection') is False:
            recommendations.append("Remove mock frameworks from test environment")
        
        if checks.get('api_calls') is False:
            recommendations.append("Ensure real API calls are made during testing")
        
        if checks.get('network_activity') is False:
            recommendations.append("Verify network connectivity and activity")
        
        if checks.get('resource_consumption') is False:
            recommendations.append("Check resource usage patterns for realism")
        
        if checks.get('result_authenticity') is False:
            recommendations.append("Validate test result structure and content")
        
        return recommendations
    
    def configure_validation(self, mock_detection: bool = True,
                           resource_tracking: bool = True,
                           api_call_tracking: bool = True) -> None:
        """Configure validation settings."""
        self._mock_detection_enabled = mock_detection
        self._resource_tracking_enabled = resource_tracking
        self._api_call_tracking_enabled = api_call_tracking
        
        self.logger.info(f"Validation configured: mock_detection={mock_detection}, "
                        f"resource_tracking={resource_tracking}, api_call_tracking={api_call_tracking}")


# Context manager for real execution validation
class RealExecutionContext:
    """Context manager for tracking real execution validation."""
    
    def __init__(self, validator: RealExecutionValidator):
        self.validator = validator
    
    def __enter__(self):
        self.validator.start_tracking()
        return self.validator
    
    def __exit__(self, exc_type, exc_val, exc_tb):
        self.validator.stop_tracking()


def create_real_execution_validator() -> RealExecutionValidator:
    """Factory function to create a real execution validator."""
    return RealExecutionValidator()