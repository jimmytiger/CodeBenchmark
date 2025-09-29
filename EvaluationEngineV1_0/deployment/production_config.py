"""
Production Configuration Management for Multi-Turn Evaluation Engine.

This module provides production-ready configuration management with environment
variable support, validation, and secure defaults.
"""

import os
import logging
import json
from dataclasses import dataclass, field
from pathlib import Path
from typing import Dict, Any, Optional, List, Union
from enum import Enum
import yaml

logger = logging.getLogger(__name__)


class Environment(Enum):
    """Deployment environment types."""
    DEVELOPMENT = "development"
    STAGING = "staging"
    PRODUCTION = "production"
    TESTING = "testing"


class LogLevel(Enum):
    """Logging levels."""
    DEBUG = "DEBUG"
    INFO = "INFO"
    WARNING = "WARNING"
    ERROR = "ERROR"
    CRITICAL = "CRITICAL"


@dataclass
class DatabaseConfig:
    """Database configuration."""
    host: str = "localhost"
    port: int = 5432
    database: str = "evaluation_engine"
    username: str = "eval_user"
    password: str = ""
    ssl_mode: str = "prefer"
    pool_size: int = 10
    max_overflow: int = 20
    pool_timeout: int = 30
    
    @classmethod
    def from_env(cls) -> 'DatabaseConfig':
        """Create database config from environment variables."""
        return cls(
            host=os.getenv('DB_HOST', 'localhost'),
            port=int(os.getenv('DB_PORT', '5432')),
            database=os.getenv('DB_NAME', 'evaluation_engine'),
            username=os.getenv('DB_USER', 'eval_user'),
            password=os.getenv('DB_PASSWORD', ''),
            ssl_mode=os.getenv('DB_SSL_MODE', 'prefer'),
            pool_size=int(os.getenv('DB_POOL_SIZE', '10')),
            max_overflow=int(os.getenv('DB_MAX_OVERFLOW', '20')),
            pool_timeout=int(os.getenv('DB_POOL_TIMEOUT', '30'))
        )
    
    def get_connection_string(self) -> str:
        """Get database connection string."""
        return (f"postgresql://{self.username}:{self.password}@"
                f"{self.host}:{self.port}/{self.database}?sslmode={self.ssl_mode}")


@dataclass
class RedisConfig:
    """Redis configuration for caching and session storage."""
    host: str = "localhost"
    port: int = 6379
    database: int = 0
    password: Optional[str] = None
    ssl: bool = False
    max_connections: int = 50
    socket_timeout: int = 5
    socket_connect_timeout: int = 5
    
    @classmethod
    def from_env(cls) -> 'RedisConfig':
        """Create Redis config from environment variables."""
        return cls(
            host=os.getenv('REDIS_HOST', 'localhost'),
            port=int(os.getenv('REDIS_PORT', '6379')),
            database=int(os.getenv('REDIS_DB', '0')),
            password=os.getenv('REDIS_PASSWORD'),
            ssl=os.getenv('REDIS_SSL', 'false').lower() == 'true',
            max_connections=int(os.getenv('REDIS_MAX_CONNECTIONS', '50')),
            socket_timeout=int(os.getenv('REDIS_SOCKET_TIMEOUT', '5')),
            socket_connect_timeout=int(os.getenv('REDIS_CONNECT_TIMEOUT', '5'))
        )
    
    def get_connection_url(self) -> str:
        """Get Redis connection URL."""
        scheme = "rediss" if self.ssl else "redis"
        auth = f":{self.password}@" if self.password else ""
        return f"{scheme}://{auth}{self.host}:{self.port}/{self.database}"


@dataclass
class SecurityConfig:
    """Security configuration."""
    secret_key: str = ""
    jwt_secret: str = ""
    jwt_expiration_hours: int = 24
    api_key_header: str = "X-API-Key"
    cors_origins: List[str] = field(default_factory=list)
    rate_limit_per_minute: int = 100
    max_request_size_mb: int = 10
    enable_https_only: bool = True
    
    @classmethod
    def from_env(cls) -> 'SecurityConfig':
        """Create security config from environment variables."""
        cors_origins = []
        if os.getenv('CORS_ORIGINS'):
            cors_origins = [origin.strip() for origin in os.getenv('CORS_ORIGINS').split(',')]
        
        return cls(
            secret_key=os.getenv('SECRET_KEY', ''),
            jwt_secret=os.getenv('JWT_SECRET', ''),
            jwt_expiration_hours=int(os.getenv('JWT_EXPIRATION_HOURS', '24')),
            api_key_header=os.getenv('API_KEY_HEADER', 'X-API-Key'),
            cors_origins=cors_origins,
            rate_limit_per_minute=int(os.getenv('RATE_LIMIT_PER_MINUTE', '100')),
            max_request_size_mb=int(os.getenv('MAX_REQUEST_SIZE_MB', '10')),
            enable_https_only=os.getenv('HTTPS_ONLY', 'true').lower() == 'true'
        )
    
    def validate(self) -> List[str]:
        """Validate security configuration."""
        errors = []
        
        if not self.secret_key:
            errors.append("SECRET_KEY is required")
        elif len(self.secret_key) < 32:
            errors.append("SECRET_KEY must be at least 32 characters long")
        
        if not self.jwt_secret:
            errors.append("JWT_SECRET is required")
        elif len(self.jwt_secret) < 32:
            errors.append("JWT_SECRET must be at least 32 characters long")
        
        return errors


@dataclass
class PerformanceConfig:
    """Performance and scaling configuration."""
    max_concurrent_evaluations: int = 10
    worker_processes: int = 4
    worker_threads_per_process: int = 8
    cache_size_mb: int = 512
    cache_ttl_seconds: int = 3600
    request_timeout_seconds: int = 300
    max_memory_usage_mb: int = 2048
    enable_profiling: bool = False
    
    @classmethod
    def from_env(cls) -> 'PerformanceConfig':
        """Create performance config from environment variables."""
        return cls(
            max_concurrent_evaluations=int(os.getenv('MAX_CONCURRENT_EVALUATIONS', '10')),
            worker_processes=int(os.getenv('WORKER_PROCESSES', '4')),
            worker_threads_per_process=int(os.getenv('WORKER_THREADS', '8')),
            cache_size_mb=int(os.getenv('CACHE_SIZE_MB', '512')),
            cache_ttl_seconds=int(os.getenv('CACHE_TTL_SECONDS', '3600')),
            request_timeout_seconds=int(os.getenv('REQUEST_TIMEOUT_SECONDS', '300')),
            max_memory_usage_mb=int(os.getenv('MAX_MEMORY_MB', '2048')),
            enable_profiling=os.getenv('ENABLE_PROFILING', 'false').lower() == 'true'
        )


@dataclass
class MonitoringConfig:
    """Monitoring and observability configuration."""
    enable_metrics: bool = True
    metrics_port: int = 9090
    health_check_interval: int = 30
    log_level: LogLevel = LogLevel.INFO
    log_format: str = "json"
    enable_tracing: bool = False
    jaeger_endpoint: Optional[str] = None
    prometheus_endpoint: Optional[str] = None
    
    @classmethod
    def from_env(cls) -> 'MonitoringConfig':
        """Create monitoring config from environment variables."""
        log_level_str = os.getenv('LOG_LEVEL', 'INFO').upper()
        log_level = LogLevel(log_level_str) if log_level_str in [l.value for l in LogLevel] else LogLevel.INFO
        
        return cls(
            enable_metrics=os.getenv('ENABLE_METRICS', 'true').lower() == 'true',
            metrics_port=int(os.getenv('METRICS_PORT', '9090')),
            health_check_interval=int(os.getenv('HEALTH_CHECK_INTERVAL', '30')),
            log_level=log_level,
            log_format=os.getenv('LOG_FORMAT', 'json'),
            enable_tracing=os.getenv('ENABLE_TRACING', 'false').lower() == 'true',
            jaeger_endpoint=os.getenv('JAEGER_ENDPOINT'),
            prometheus_endpoint=os.getenv('PROMETHEUS_ENDPOINT')
        )


@dataclass
class StorageConfig:
    """Storage configuration for results and artifacts."""
    results_storage_type: str = "filesystem"  # filesystem, s3, gcs
    results_storage_path: str = "/app/results"
    s3_bucket: Optional[str] = None
    s3_region: Optional[str] = None
    s3_access_key: Optional[str] = None
    s3_secret_key: Optional[str] = None
    gcs_bucket: Optional[str] = None
    gcs_credentials_path: Optional[str] = None
    max_result_size_mb: int = 100
    retention_days: int = 30
    
    @classmethod
    def from_env(cls) -> 'StorageConfig':
        """Create storage config from environment variables."""
        return cls(
            results_storage_type=os.getenv('RESULTS_STORAGE_TYPE', 'filesystem'),
            results_storage_path=os.getenv('RESULTS_STORAGE_PATH', '/app/results'),
            s3_bucket=os.getenv('S3_BUCKET'),
            s3_region=os.getenv('S3_REGION'),
            s3_access_key=os.getenv('S3_ACCESS_KEY'),
            s3_secret_key=os.getenv('S3_SECRET_KEY'),
            gcs_bucket=os.getenv('GCS_BUCKET'),
            gcs_credentials_path=os.getenv('GCS_CREDENTIALS_PATH'),
            max_result_size_mb=int(os.getenv('MAX_RESULT_SIZE_MB', '100')),
            retention_days=int(os.getenv('RETENTION_DAYS', '30'))
        )


@dataclass
class ProductionConfig:
    """Main production configuration."""
    environment: Environment = Environment.PRODUCTION
    debug: bool = False
    host: str = "0.0.0.0"
    port: int = 8000
    app_name: str = "Multi-Turn Evaluation Engine"
    version: str = "1.0.0"
    
    # Component configurations
    database: DatabaseConfig = field(default_factory=DatabaseConfig)
    redis: RedisConfig = field(default_factory=RedisConfig)
    security: SecurityConfig = field(default_factory=SecurityConfig)
    performance: PerformanceConfig = field(default_factory=PerformanceConfig)
    monitoring: MonitoringConfig = field(default_factory=MonitoringConfig)
    storage: StorageConfig = field(default_factory=StorageConfig)
    
    @classmethod
    def from_env(cls) -> 'ProductionConfig':
        """Create production config from environment variables."""
        env_str = os.getenv('ENVIRONMENT', 'production').lower()
        environment = Environment(env_str) if env_str in [e.value for e in Environment] else Environment.PRODUCTION
        
        return cls(
            environment=environment,
            debug=os.getenv('DEBUG', 'false').lower() == 'true',
            host=os.getenv('HOST', '0.0.0.0'),
            port=int(os.getenv('PORT', '8000')),
            app_name=os.getenv('APP_NAME', 'Multi-Turn Evaluation Engine'),
            version=os.getenv('APP_VERSION', '1.0.0'),
            database=DatabaseConfig.from_env(),
            redis=RedisConfig.from_env(),
            security=SecurityConfig.from_env(),
            performance=PerformanceConfig.from_env(),
            monitoring=MonitoringConfig.from_env(),
            storage=StorageConfig.from_env()
        )
    
    @classmethod
    def from_file(cls, config_path: Union[str, Path]) -> 'ProductionConfig':
        """Load configuration from file."""
        config_path = Path(config_path)
        
        if not config_path.exists():
            raise FileNotFoundError(f"Configuration file not found: {config_path}")
        
        with open(config_path, 'r') as f:
            if config_path.suffix.lower() in ['.yml', '.yaml']:
                config_data = yaml.safe_load(f)
            else:
                config_data = json.load(f)
        
        # Create config from data
        config = cls()
        
        # Update fields from config data
        for key, value in config_data.items():
            if hasattr(config, key):
                if key in ['database', 'redis', 'security', 'performance', 'monitoring', 'storage']:
                    # Handle nested configurations
                    nested_config = getattr(config, key)
                    for nested_key, nested_value in value.items():
                        if hasattr(nested_config, nested_key):
                            setattr(nested_config, nested_key, nested_value)
                else:
                    setattr(config, key, value)
        
        return config
    
    def validate(self) -> List[str]:
        """Validate the entire configuration."""
        errors = []
        
        # Validate security configuration
        security_errors = self.security.validate()
        errors.extend(security_errors)
        
        # Validate port range
        if not (1 <= self.port <= 65535):
            errors.append(f"Invalid port number: {self.port}")
        
        # Validate performance settings
        if self.performance.max_concurrent_evaluations <= 0:
            errors.append("max_concurrent_evaluations must be positive")
        
        if self.performance.worker_processes <= 0:
            errors.append("worker_processes must be positive")
        
        # Validate storage configuration
        if self.storage.results_storage_type not in ['filesystem', 's3', 'gcs']:
            errors.append(f"Invalid storage type: {self.storage.results_storage_type}")
        
        if self.storage.results_storage_type == 's3':
            if not self.storage.s3_bucket:
                errors.append("S3 bucket is required when using S3 storage")
        
        if self.storage.results_storage_type == 'gcs':
            if not self.storage.gcs_bucket:
                errors.append("GCS bucket is required when using GCS storage")
        
        return errors
    
    def to_dict(self) -> Dict[str, Any]:
        """Convert configuration to dictionary."""
        def convert_dataclass(obj):
            if hasattr(obj, '__dataclass_fields__'):
                return {k: convert_dataclass(v) for k, v in obj.__dict__.items()}
            elif isinstance(obj, Enum):
                return obj.value
            elif isinstance(obj, list):
                return [convert_dataclass(item) for item in obj]
            else:
                return obj
        
        return convert_dataclass(self)
    
    def save_to_file(self, config_path: Union[str, Path]) -> None:
        """Save configuration to file."""
        config_path = Path(config_path)
        config_data = self.to_dict()
        
        config_path.parent.mkdir(parents=True, exist_ok=True)
        
        with open(config_path, 'w') as f:
            if config_path.suffix.lower() in ['.yml', '.yaml']:
                yaml.dump(config_data, f, default_flow_style=False, indent=2)
            else:
                json.dump(config_data, f, indent=2)
    
    def setup_logging(self) -> None:
        """Setup logging based on configuration."""
        log_level = getattr(logging, self.monitoring.log_level.value)
        
        if self.monitoring.log_format == "json":
            # JSON logging format for production
            import json_logging
            json_logging.init_non_web(enable_json=True)
            
            logging.basicConfig(
                level=log_level,
                format='%(asctime)s %(name)s %(levelname)s %(message)s'
            )
        else:
            # Standard logging format
            logging.basicConfig(
                level=log_level,
                format='%(asctime)s - %(name)s - %(levelname)s - %(message)s'
            )
        
        # Set specific logger levels
        logging.getLogger('uvicorn').setLevel(logging.WARNING)
        logging.getLogger('fastapi').setLevel(logging.INFO)
    
    def get_environment_summary(self) -> Dict[str, Any]:
        """Get a summary of the current environment configuration."""
        return {
            'environment': self.environment.value,
            'debug': self.debug,
            'host': self.host,
            'port': self.port,
            'app_name': self.app_name,
            'version': self.version,
            'database_host': self.database.host,
            'redis_host': self.redis.host,
            'max_concurrent_evaluations': self.performance.max_concurrent_evaluations,
            'worker_processes': self.performance.worker_processes,
            'log_level': self.monitoring.log_level.value,
            'storage_type': self.storage.results_storage_type
        }


class ConfigurationManager:
    """Configuration manager for handling different environments."""
    
    def __init__(self):
        """Initialize configuration manager."""
        self._config: Optional[ProductionConfig] = None
        self._config_file_path: Optional[Path] = None
    
    def load_config(self, 
                   config_file: Optional[Union[str, Path]] = None,
                   use_env: bool = True) -> ProductionConfig:
        """Load configuration from file and/or environment variables.
        
        Args:
            config_file: Path to configuration file
            use_env: Whether to use environment variables
            
        Returns:
            ProductionConfig instance
        """
        if config_file:
            self._config_file_path = Path(config_file)
            self._config = ProductionConfig.from_file(config_file)
        elif use_env:
            self._config = ProductionConfig.from_env()
        else:
            self._config = ProductionConfig()
        
        # Validate configuration
        errors = self._config.validate()
        if errors:
            error_msg = "Configuration validation failed:\n" + "\n".join(f"  - {error}" for error in errors)
            raise ValueError(error_msg)
        
        # Setup logging
        self._config.setup_logging()
        
        logger.info(f"Configuration loaded for environment: {self._config.environment.value}")
        return self._config
    
    def get_config(self) -> ProductionConfig:
        """Get current configuration."""
        if self._config is None:
            self._config = self.load_config()
        return self._config
    
    def reload_config(self) -> ProductionConfig:
        """Reload configuration from file."""
        if self._config_file_path:
            return self.load_config(self._config_file_path, use_env=False)
        else:
            return self.load_config(use_env=True)
    
    def create_default_config_file(self, config_path: Union[str, Path]) -> None:
        """Create a default configuration file."""
        config = ProductionConfig()
        config.save_to_file(config_path)
        logger.info(f"Default configuration file created: {config_path}")


# Global configuration manager instance
config_manager = ConfigurationManager()