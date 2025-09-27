"""
Extended Model Adapters for AI Evaluation Engine

This module provides extended model adapters that build upon lm-eval's LM base class
to support additional model backends, advanced configuration options, and plugin
architecture for custom model integrations.
"""

import abc
import asyncio
import logging
import time
from dataclasses import dataclass, field
from typing import Any, Dict, List, Optional, Tuple, Union, Callable
from enum import Enum

from lm_eval.api.model import LM
from lm_eval.api.instance import Instance


eval_logger = logging.getLogger(__name__)


class ModelType(Enum):
    """Enumeration of supported model types."""
    OPENAI = "openai"
    ANTHROPIC = "anthropic"
    DASHSCOPE = "dashscope"
    GOOGLE = "google"
    COHERE = "cohere"
    HUGGINGFACE = "huggingface"
    LOCAL = "local"
    CUSTOM = "custom"


@dataclass
class RateLimitConfig:
    """Configuration for API rate limiting."""
    requests_per_minute: int = 60
    tokens_per_minute: int = 10000
    max_concurrent_requests: int = 10
    backoff_factor: float = 2.0
    max_retries: int = 3
    
    def to_dict(self) -> Dict[str, Any]:
        """Convert to dictionary."""
        return {
            'requests_per_minute': self.requests_per_minute,
            'tokens_per_minute': self.tokens_per_minute,
            'max_concurrent_requests': self.max_concurrent_requests,
            'backoff_factor': self.backoff_factor,
            'max_retries': self.max_retries
        }


@dataclass
class ModelCapabilities:
    """Describes model capabilities and limitations."""
    max_context_length: int = 4096
    max_output_length: int = 2048
    supports_function_calling: bool = False
    supports_streaming: bool = False
    supports_chat_templates: bool = False
    supports_system_messages: bool = False
    supports_multimodal: bool = False
    supported_languages: List[str] = field(default_factory=lambda: ["en"])
    
    def to_dict(self) -> Dict[str, Any]:
        """Convert to dictionary."""
        return {
            'max_context_length': self.max_context_length,
            'max_output_length': self.max_output_length,
            'supports_function_calling': self.supports_function_calling,
            'supports_streaming': self.supports_streaming,
            'supports_chat_templates': self.supports_chat_templates,
            'supports_system_messages': self.supports_system_messages,
            'supports_multimodal': self.supports_multimodal,
            'supported_languages': self.supported_languages
        }


@dataclass
class ModelMetrics:
    """Tracks model performance metrics."""
    total_requests: int = 0
    successful_requests: int = 0
    failed_requests: int = 0
    total_tokens_used: int = 0
    total_cost: float = 0.0
    average_response_time: float = 0.0
    error_rate: float = 0.0
    
    def update_request(self, success: bool, tokens_used: int = 0, 
                      response_time: float = 0.0, cost: float = 0.0):
        """Update metrics with new request data."""
        self.total_requests += 1
        if success:
            self.successful_requests += 1
        else:
            self.failed_requests += 1
        
        self.total_tokens_used += tokens_used
        self.total_cost += cost
        
        # Update average response time
        if self.total_requests > 1:
            self.average_response_time = (
                (self.average_response_time * (self.total_requests - 1) + response_time) 
                / self.total_requests
            )
        else:
            self.average_response_time = response_time
        
        self.error_rate = self.failed_requests / self.total_requests if self.total_requests > 0 else 0.0
    
    def to_dict(self) -> Dict[str, Any]:
        """Convert to dictionary."""
        return {
            'total_requests': self.total_requests,
            'successful_requests': self.successful_requests,
            'failed_requests': self.failed_requests,
            'total_tokens_used': self.total_tokens_used,
            'total_cost': self.total_cost,
            'average_response_time': self.average_response_time,
            'error_rate': self.error_rate
        }


class ModelAdapter(LM):
    """
    Extended model adapter that builds upon lm-eval's LM base class.
    
    This class provides additional functionality for:
    - Advanced configuration management
    - Rate limiting and retry logic
    - Performance monitoring
    - Plugin architecture support
    """
    
    def __init__(
        self,
        model_id: str,
        model_type: ModelType,
        api_key: Optional[str] = None,
        api_base: Optional[str] = None,
        rate_limit_config: Optional[RateLimitConfig] = None,
        model_kwargs: Optional[Dict[str, Any]] = None,
        **kwargs
    ):
        """Initialize ModelAdapter with extended configuration."""
        super().__init__()
        
        self.model_id = model_id
        self.model_type = model_type
        self.api_key = api_key
        self.api_base = api_base
        self.model_kwargs = model_kwargs or {}
        
        # Rate limiting and performance tracking
        self.rate_limit_config = rate_limit_config or RateLimitConfig()
        self.metrics = ModelMetrics()
        self.capabilities = self._get_model_capabilities()
        
        # Request tracking for rate limiting
        self._request_times: List[float] = []
        self._token_usage: List[Tuple[float, int]] = []  # (timestamp, tokens)
        self._semaphore = asyncio.Semaphore(self.rate_limit_config.max_concurrent_requests)
        
        # Plugin hooks
        self._pre_request_hooks: List[Callable] = []
        self._post_request_hooks: List[Callable] = []
        self._error_hooks: List[Callable] = []
    
    @abc.abstractmethod
    def _get_model_capabilities(self) -> ModelCapabilities:
        """Get model capabilities. Must be implemented by subclasses."""
        pass
    
    def add_pre_request_hook(self, hook: Callable[[Dict[str, Any]], Dict[str, Any]]):
        """Add a hook that runs before each request."""
        self._pre_request_hooks.append(hook)
    
    def add_post_request_hook(self, hook: Callable[[Dict[str, Any], Any], Any]):
        """Add a hook that runs after each successful request."""
        self._post_request_hooks.append(hook)
    
    def add_error_hook(self, hook: Callable[[Exception, Dict[str, Any]], None]):
        """Add a hook that runs when an error occurs."""
        self._error_hooks.append(hook)
    
    def _run_pre_request_hooks(self, request_data: Dict[str, Any]) -> Dict[str, Any]:
        """Run all pre-request hooks."""
        for hook in self._pre_request_hooks:
            try:
                request_data = hook(request_data) or request_data
            except Exception as e:
                eval_logger.warning(f"Pre-request hook failed: {e}")
        return request_data
    
    def _run_post_request_hooks(self, request_data: Dict[str, Any], response: Any) -> Any:
        """Run all post-request hooks."""
        for hook in self._post_request_hooks:
            try:
                response = hook(request_data, response) or response
            except Exception as e:
                eval_logger.warning(f"Post-request hook failed: {e}")
        return response
    
    def _run_error_hooks(self, error: Exception, request_data: Dict[str, Any]):
        """Run all error hooks."""
        for hook in self._error_hooks:
            try:
                hook(error, request_data)
            except Exception as e:
                eval_logger.warning(f"Error hook failed: {e}")
    
    def _check_rate_limits(self) -> bool:
        """Check if request can be made within rate limits."""
        current_time = time.time()
        
        # Clean old request times (older than 1 minute)
        self._request_times = [t for t in self._request_times if current_time - t < 60]
        self._token_usage = [(t, tokens) for t, tokens in self._token_usage if current_time - t < 60]
        
        # Check request rate limit
        if len(self._request_times) >= self.rate_limit_config.requests_per_minute:
            return False
        
        # Check token rate limit
        total_tokens = sum(tokens for _, tokens in self._token_usage)
        if total_tokens >= self.rate_limit_config.tokens_per_minute:
            return False
        
        return True
    
    def _wait_for_rate_limit(self):
        """Wait until rate limits allow a new request."""
        while not self._check_rate_limits():
            time.sleep(1)  # Wait 1 second before checking again
    
    def _record_request(self, tokens_used: int = 0):
        """Record a request for rate limiting purposes."""
        current_time = time.time()
        self._request_times.append(current_time)
        if tokens_used > 0:
            self._token_usage.append((current_time, tokens_used))
    
    async def _make_request_with_retry(
        self, 
        request_func: Callable, 
        request_data: Dict[str, Any],
        max_retries: Optional[int] = None
    ) -> Any:
        """Make a request with retry logic and rate limiting."""
        max_retries = max_retries or self.rate_limit_config.max_retries
        
        for attempt in range(max_retries + 1):
            try:
                # Wait for rate limits
                self._wait_for_rate_limit()
                
                # Run pre-request hooks
                processed_data = self._run_pre_request_hooks(request_data.copy())
                
                # Make the request
                start_time = time.time()
                async with self._semaphore:
                    response = await request_func(processed_data)
                response_time = time.time() - start_time
                
                # Record successful request
                tokens_used = self._extract_token_usage(response)
                cost = self._calculate_cost(tokens_used)
                self._record_request(tokens_used)
                self.metrics.update_request(True, tokens_used, response_time, cost)
                
                # Run post-request hooks
                response = self._run_post_request_hooks(processed_data, response)
                
                return response
                
            except Exception as e:
                # Record failed request
                self.metrics.update_request(False)
                
                # Run error hooks
                self._run_error_hooks(e, request_data)
                
                if attempt == max_retries:
                    eval_logger.error(f"Request failed after {max_retries + 1} attempts: {e}")
                    raise
                
                # Exponential backoff
                wait_time = self.rate_limit_config.backoff_factor ** attempt
                eval_logger.warning(f"Request failed (attempt {attempt + 1}), retrying in {wait_time}s: {e}")
                await asyncio.sleep(wait_time)
    
    def _extract_token_usage(self, response: Any) -> int:
        """Extract token usage from response. Override in subclasses."""
        return 0
    
    def _calculate_cost(self, tokens_used: int) -> float:
        """Calculate cost based on token usage. Override in subclasses."""
        return 0.0
    
    def get_model_info(self) -> Dict[str, Any]:
        """Get comprehensive model information."""
        return {
            'model_id': self.model_id,
            'model_type': self.model_type.value,
            'capabilities': self.capabilities.to_dict(),
            'rate_limits': self.rate_limit_config.to_dict(),
            'metrics': self.metrics.to_dict()
        }
    
    def validate_request(self, request_data: Dict[str, Any]) -> bool:
        """Validate request against model capabilities."""
        # Check context length
        if 'prompt' in request_data:
            # Rough token estimation (actual implementation would use proper tokenization)
            estimated_tokens = len(request_data['prompt'].split()) * 1.3
            if estimated_tokens > self.capabilities.max_context_length:
                eval_logger.warning(f"Request may exceed context length: {estimated_tokens} > {self.capabilities.max_context_length}")
                return False
        
        return True
    
    # Abstract methods from LM base class - must be implemented by subclasses
    @abc.abstractmethod
    def loglikelihood(self, requests) -> List[Tuple[float, bool]]:
        """Compute log-likelihood of generating continuations."""
        pass
    
    @abc.abstractmethod
    def loglikelihood_rolling(self, requests) -> List[float]:
        """Compute rolling log-likelihood for perplexity."""
        pass
    
    @abc.abstractmethod
    def generate_until(self, requests) -> List[str]:
        """Generate text until stopping criteria."""
        pass


class PluginRegistry:
    """Registry for model adapter plugins."""
    
    def __init__(self):
        self._plugins: Dict[str, type] = {}
        self._plugin_metadata: Dict[str, Dict[str, Any]] = {}
    
    def register_plugin(
        self, 
        name: str, 
        plugin_class: type, 
        metadata: Optional[Dict[str, Any]] = None
    ):
        """Register a model adapter plugin."""
        if not issubclass(plugin_class, ModelAdapter):
            raise ValueError(f"Plugin {name} must inherit from ModelAdapter")
        
        self._plugins[name] = plugin_class
        self._plugin_metadata[name] = metadata or {}
        eval_logger.info(f"Registered model adapter plugin: {name}")
    
    def get_plugin(self, name: str) -> Optional[type]:
        """Get a registered plugin by name."""
        return self._plugins.get(name)
    
    def list_plugins(self) -> List[str]:
        """List all registered plugins."""
        return list(self._plugins.keys())
    
    def get_plugin_metadata(self, name: str) -> Dict[str, Any]:
        """Get metadata for a plugin."""
        return self._plugin_metadata.get(name, {})
    
    def create_adapter(
        self, 
        plugin_name: str, 
        model_id: str, 
        **kwargs
    ) -> ModelAdapter:
        """Create a model adapter instance using a registered plugin."""
        plugin_class = self.get_plugin(plugin_name)
        if not plugin_class:
            raise ValueError(f"Unknown plugin: {plugin_name}")
        
        return plugin_class(model_id=model_id, **kwargs)


# Global plugin registry
plugin_registry = PluginRegistry()


def register_model_adapter(name: str, metadata: Optional[Dict[str, Any]] = None):
    """Decorator for registering model adapter plugins."""
    def decorator(cls):
        plugin_registry.register_plugin(name, cls, metadata)
        return cls
    return decorator


class AdvancedTaskInterface(abc.ABC):
    """
    Advanced interface for tasks that require extended functionality.
    
    This interface defines additional methods that tasks can implement
    to support advanced evaluation scenarios.
    """
    
    @abc.abstractmethod
    def supports_multi_turn(self) -> bool:
        """Check if task supports multi-turn evaluation."""
        pass
    
    @abc.abstractmethod
    def get_context_modes(self) -> List[str]:
        """Get supported context modes."""
        pass
    
    @abc.abstractmethod
    def validate_scenario_config(self, config: Dict[str, Any]) -> bool:
        """Validate scenario configuration."""
        pass
    
    @abc.abstractmethod
    def process_advanced_metrics(self, results: List[Dict[str, Any]]) -> Dict[str, float]:
        """Process advanced metrics for evaluation results."""
        pass


class BackwardCompatibilityMixin:
    """
    Mixin to ensure backward compatibility with existing lm-eval tasks.
    
    This mixin provides default implementations and compatibility layers
    to ensure that existing lm-eval tasks continue to work with the
    extended evaluation engine.
    """
    
    def ensure_compatibility(self, task_config: Dict[str, Any]) -> Dict[str, Any]:
        """Ensure task configuration is compatible with extended features."""
        # Add default values for extended fields if not present
        defaults = {
            'context_mode': 'full_context',
            'difficulty_level': 'intermediate',
            'supported_languages': ['python'],
            'max_turns': 1,
            'enable_context_retention': False,
            'security_analysis_enabled': False,
            'code_execution_enabled': False
        }
        
        for key, default_value in defaults.items():
            if key not in task_config:
                task_config[key] = default_value
        
        return task_config
    
    def convert_legacy_metrics(self, metrics: Dict[str, Any]) -> Dict[str, Any]:
        """Convert legacy metric formats to extended format."""
        # Handle legacy metric configurations
        if 'metric' in metrics and isinstance(metrics['metric'], str):
            # Convert single metric to list format
            metrics = {
                'metric_list': [{'metric': metrics['metric']}]
            }
        
        return metrics
    
    def wrap_legacy_task(self, task_class: type) -> type:
        """Wrap a legacy task class to support extended features."""
        class WrappedTask(task_class, BackwardCompatibilityMixin):
            def __init__(self, *args, **kwargs):
                # Ensure compatibility of configuration
                if 'config' in kwargs:
                    kwargs['config'] = self.ensure_compatibility(kwargs['config'])
                
                super().__init__(*args, **kwargs)
            
            def supports_multi_turn(self) -> bool:
                return False  # Legacy tasks don't support multi-turn by default
            
            def get_context_modes(self) -> List[str]:
                return ['full_context']  # Default context mode
            
            def validate_scenario_config(self, config: Dict[str, Any]) -> bool:
                return True  # Accept all configurations for legacy tasks
            
            def process_advanced_metrics(self, results: List[Dict[str, Any]]) -> Dict[str, float]:
                return {}  # No advanced metrics for legacy tasks
        
        return WrappedTask


# Utility functions for plugin development
def create_model_adapter_plugin(
    name: str,
    model_type: ModelType,
    capabilities: ModelCapabilities,
    request_handler: Callable,
    metadata: Optional[Dict[str, Any]] = None
) -> type:
    """
    Factory function to create a model adapter plugin.
    
    This function simplifies the creation of model adapter plugins by
    providing a template implementation that handles common functionality.
    """
    
    @register_model_adapter(name, metadata)
    class GeneratedModelAdapter(ModelAdapter):
        def __init__(self, model_id: str, **kwargs):
            super().__init__(
                model_id=model_id,
                model_type=model_type,
                **kwargs
            )
            self._request_handler = request_handler
        
        def _get_model_capabilities(self) -> ModelCapabilities:
            return capabilities
        
        def loglikelihood(self, requests) -> List[Tuple[float, bool]]:
            # Implementation using the provided request handler
            return self._request_handler('loglikelihood', requests)
        
        def loglikelihood_rolling(self, requests) -> List[float]:
            return self._request_handler('loglikelihood_rolling', requests)
        
        def generate_until(self, requests) -> List[str]:
            return self._request_handler('generate_until', requests)
    
    return GeneratedModelAdapter