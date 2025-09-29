"""
Core data models for the testing framework.
"""

from dataclasses import dataclass, field
from typing import Dict, List, Optional, Any, Union
from datetime import datetime
from enum import Enum
from pathlib import Path


class TestStatus(Enum):
    """Test execution status."""
    PENDING = "pending"
    RUNNING = "running"
    PASSED = "passed"
    FAILED = "failed"
    SKIPPED = "skipped"
    ERROR = "error"


class TestType(Enum):
    """Type of test being executed."""
    CLI = "cli"
    API = "api"
    ADAPTER = "adapter"
    PIPELINE = "pipeline"
    UNIT = "unit"
    INTEGRATION = "integration"
    PERFORMANCE = "performance"


class AdapterType(Enum):
    """Types of adapters to test."""
    LM_EVAL = "lm_eval"
    SWE_BENCH = "swe_bench"
    INTERCODE = "intercode"
    CONVCODE = "convcode"
    ALL = "all"


@dataclass
class TestConfiguration:
    """Configuration for test execution."""
    test_id: str
    test_type: TestType
    name: str
    description: str
    target_adapters: List[AdapterType] = field(default_factory=list)
    task_selection: Dict[str, Any] = field(default_factory=dict)
    execution_params: Dict[str, Any] = field(default_factory=dict)
    output_config: Dict[str, Any] = field(default_factory=dict)
    timeout: int = 300  # 5 minutes default
    retry_count: int = 0
    real_execution_required: bool = True
    created_at: datetime = field(default_factory=datetime.now)


@dataclass
class TestResult:
    """Result of a single test execution."""
    test_id: str
    test_type: TestType
    name: str
    status: TestStatus
    execution_time: float
    real_execution_validated: bool
    metrics: Dict[str, float] = field(default_factory=dict)
    error_details: Optional[str] = None
    artifacts: List[str] = field(default_factory=list)
    logs: List[str] = field(default_factory=list)
    started_at: Optional[datetime] = None
    completed_at: Optional[datetime] = None
    retry_count: int = 0
    
    def __post_init__(self):
        if self.started_at is None:
            self.started_at = datetime.now()
        if self.status in [TestStatus.PASSED, TestStatus.FAILED, TestStatus.ERROR] and self.completed_at is None:
            self.completed_at = datetime.now()


@dataclass
class ValidationResult:
    """Result of adapter validation."""
    adapter_name: str
    adapter_type: AdapterType
    integration_status: TestStatus
    dependencies_installed: bool
    test_results: List[TestResult] = field(default_factory=list)
    performance_metrics: Dict[str, float] = field(default_factory=dict)
    issues_found: List[str] = field(default_factory=list)
    recommendations: List[str] = field(default_factory=list)
    validation_time: float = 0.0
    validated_at: datetime = field(default_factory=datetime.now)


@dataclass
class ExecutionMetrics:
    """Metrics collected during test execution."""
    total_execution_time: float
    task_execution_times: Dict[str, float] = field(default_factory=dict)
    memory_usage: Dict[str, float] = field(default_factory=dict)
    api_response_times: Dict[str, float] = field(default_factory=dict)
    error_rates: Dict[str, float] = field(default_factory=dict)
    success_rates: Dict[str, float] = field(default_factory=dict)
    resource_consumption: Dict[str, float] = field(default_factory=dict)
    network_usage: Dict[str, float] = field(default_factory=dict)
    collected_at: datetime = field(default_factory=datetime.now)


@dataclass
class CLITestConfig:
    """Configuration for CLI testing."""
    tasks: List[str] = field(default_factory=list)
    adapters: List[AdapterType] = field(default_factory=list)
    execution_timeout: int = 300
    output_format: str = "json"
    verbose: bool = False
    config_file: Optional[Path] = None
    custom_task_dir: Optional[Path] = None
    parallel_execution: bool = False
    max_workers: int = 4


@dataclass
class APITestConfig:
    """Configuration for API testing."""
    server_host: str = "localhost"
    server_port: int = 8000
    test_endpoints: List[str] = field(default_factory=list)
    concurrent_requests: int = 5
    timeout: int = 30
    auth_token: Optional[str] = None
    ssl_verify: bool = True
    rate_limit: Optional[int] = None


@dataclass
class AdapterTestConfig:
    """Configuration for adapter testing."""
    adapter_name: str
    adapter_type: AdapterType
    test_task_count: int = 1
    dependency_check: bool = True
    performance_benchmark: bool = True
    custom_task_dir: Optional[Path] = None
    installation_timeout: int = 600  # 10 minutes for dependency installation
    test_timeout: int = 300  # 5 minutes per test
    real_execution_only: bool = True


@dataclass
class TestSuiteResults:
    """Results from a complete test suite execution."""
    suite_id: str
    suite_name: str
    total_tests: int
    passed_tests: int
    failed_tests: int
    skipped_tests: int
    error_tests: int
    total_execution_time: float
    test_results: List[TestResult] = field(default_factory=list)
    validation_results: List[ValidationResult] = field(default_factory=list)
    execution_metrics: Optional[ExecutionMetrics] = None
    summary_report: str = ""
    artifacts_dir: Optional[Path] = None
    started_at: datetime = field(default_factory=datetime.now)
    completed_at: Optional[datetime] = None
    
    @property
    def success_rate(self) -> float:
        """Calculate overall success rate."""
        if self.total_tests == 0:
            return 0.0
        return self.passed_tests / self.total_tests
    
    @property
    def is_successful(self) -> bool:
        """Check if the entire suite was successful."""
        return self.failed_tests == 0 and self.error_tests == 0 and self.passed_tests > 0


@dataclass
class TaskInfo:
    """Information about a test task."""
    task_id: str
    task_name: str
    task_type: str
    description: str
    adapter_type: AdapterType
    difficulty: str = "medium"
    estimated_time: int = 60  # seconds
    requirements: List[str] = field(default_factory=list)
    custom_config: Dict[str, Any] = field(default_factory=dict)


@dataclass
class DependencyInfo:
    """Information about adapter dependencies."""
    name: str
    version: Optional[str] = None
    required: bool = True
    installation_command: Optional[str] = None
    check_command: Optional[str] = None
    description: str = ""


@dataclass
class AdapterInfo:
    """Information about an adapter."""
    name: str
    adapter_type: AdapterType
    version: str
    description: str
    dependencies: List[DependencyInfo] = field(default_factory=list)
    supported_tasks: List[str] = field(default_factory=list)
    configuration_schema: Dict[str, Any] = field(default_factory=dict)
    performance_baseline: Dict[str, float] = field(default_factory=dict)


@dataclass
class ReportConfig:
    """Configuration for report generation."""
    output_dir: Path
    formats: List[str] = field(default_factory=lambda: ["html", "json", "markdown"])
    include_logs: bool = True
    include_artifacts: bool = True
    include_performance_charts: bool = True
    template_dir: Optional[Path] = None
    custom_sections: List[str] = field(default_factory=list)


# Utility functions for model validation and conversion

def validate_test_config(config: TestConfiguration) -> List[str]:
    """Validate test configuration and return list of errors."""
    errors = []
    
    if not config.test_id:
        errors.append("test_id is required")
    
    if not config.name:
        errors.append("name is required")
    
    if config.timeout <= 0:
        errors.append("timeout must be positive")
    
    if config.retry_count < 0:
        errors.append("retry_count cannot be negative")
    
    return errors


def create_test_result(test_config: TestConfiguration, 
                      status: TestStatus = TestStatus.PENDING) -> TestResult:
    """Create a TestResult from TestConfiguration."""
    return TestResult(
        test_id=test_config.test_id,
        test_type=test_config.test_type,
        name=test_config.name,
        status=status,
        execution_time=0.0,
        real_execution_validated=False
    )


def merge_execution_metrics(metrics_list: List[ExecutionMetrics]) -> ExecutionMetrics:
    """Merge multiple ExecutionMetrics into a single aggregated result."""
    if not metrics_list:
        return ExecutionMetrics(total_execution_time=0.0)
    
    merged = ExecutionMetrics(
        total_execution_time=sum(m.total_execution_time for m in metrics_list)
    )
    
    # Merge dictionaries by combining values
    for metrics in metrics_list:
        for key, value in metrics.task_execution_times.items():
            merged.task_execution_times[key] = merged.task_execution_times.get(key, 0) + value
        
        for key, value in metrics.memory_usage.items():
            merged.memory_usage[key] = max(merged.memory_usage.get(key, 0), value)
        
        for key, value in metrics.api_response_times.items():
            merged.api_response_times[key] = merged.api_response_times.get(key, 0) + value
    
    return merged