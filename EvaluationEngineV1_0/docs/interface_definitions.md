# Multi-Turn Evaluation Engine Interface Definitions

## Table of Contents

1. [Core Interfaces](#core-interfaces)
2. [Adapter Interfaces](#adapter-interfaces)
3. [Environment Interfaces](#environment-interfaces)
4. [Metrics Interfaces](#metrics-interfaces)
5. [Safety Interfaces](#safety-interfaces)
6. [Data Model Interfaces](#data-model-interfaces)
7. [API Interfaces](#api-interfaces)
8. [WebSocket Interfaces](#websocket-interfaces)

## Core Interfaces

### BaseTask Interface

The foundation interface for all evaluation tasks.

```python
from abc import ABC, abstractmethod
from typing import Dict, Any, List
from enum import Enum

class TaskType(Enum):
    """Task type enumeration."""
    SINGLE_TURN = "single_turn"
    MULTI_TURN = "multi_turn"

class BaseTask(ABC):
    """
    Base interface for all evaluation tasks.
    
    This interface defines the common contract that all tasks must implement,
    regardless of whether they are single-turn or multi-turn.
    """
    
    @abstractmethod
    def get_task_type(self) -> TaskType:
        """
        Get the type of this task.
        
        Returns:
            TaskType: Either SINGLE_TURN or MULTI_TURN
        """
        pass
    
    @abstractmethod
    def get_task_id(self) -> str:
        """
        Get unique identifier for this task.
        
        Returns:
            str: Unique task identifier
        """
        pass
    
    @abstractmethod
    def get_description(self) -> str:
        """
        Get human-readable description of the task.
        
        Returns:
            str: Task description
        """
        pass
    
    @abstractmethod
    def validate_config(self, config: Dict[str, Any]) -> bool:
        """
        Validate task configuration.
        
        Args:
            config: Configuration dictionary to validate
            
        Returns:
            bool: True if configuration is valid
        """
        pass
    
    @abstractmethod
    def get_required_capabilities(self) -> List[str]:
        """
        Get list of required capabilities for this task.
        
        Returns:
            List[str]: List of required capability names
        """
        pass
    
    @abstractmethod
    def get_metadata(self) -> Dict[str, Any]:
        """
        Get task metadata.
        
        Returns:
            Dict[str, Any]: Task metadata including category, difficulty, etc.
        """
        pass
```

### SingleTurnTask Interface

Interface for single-turn evaluation tasks.

```python
from typing import Any

class SingleTurnTask(BaseTask):
    """
    Interface for single-turn evaluation tasks.
    
    Single-turn tasks execute once with a single input and produce a single output.
    """
    
    def get_task_type(self) -> TaskType:
        """Return SINGLE_TURN task type."""
        return TaskType.SINGLE_TURN
    
    @abstractmethod
    def execute(self, input_data: Any, model_adapter: 'ModelAdapter') -> 'TaskResult':
        """
        Execute single-turn evaluation.
        
        Args:
            input_data: Input data for the task
            model_adapter: Model adapter for generating responses
            
        Returns:
            TaskResult: Result of the task execution
        """
        pass
    
    @abstractmethod
    def evaluate_response(self, response: Any, expected: Any) -> Dict[str, float]:
        """
        Evaluate model response against expected output.
        
        Args:
            response: Model's response
            expected: Expected output
            
        Returns:
            Dict[str, float]: Evaluation metrics
        """
        pass
```

### MultiTurnTask Interface

Interface for multi-turn evaluation tasks.

```python
from typing import List

class MultiTurnTask(BaseTask):
    """
    Interface for multi-turn evaluation tasks.
    
    Multi-turn tasks involve multiple rounds of interaction between
    the model and the environment.
    """
    
    def get_task_type(self) -> TaskType:
        """Return MULTI_TURN task type."""
        return TaskType.MULTI_TURN
    
    @abstractmethod
    def create_environment(self, config: Dict[str, Any]) -> 'UnifiedEnv':
        """
        Create environment instance for this task.
        
        Args:
            config: Environment configuration
            
        Returns:
            UnifiedEnv: Environment instance
        """
        pass
    
    @abstractmethod
    def get_initial_context(self) -> Dict[str, Any]:
        """
        Get initial context for the task.
        
        Returns:
            Dict[str, Any]: Initial context information
        """
        pass
    
    @abstractmethod
    def should_continue(self, turn_result: 'TurnResult', context: Dict[str, Any]) -> bool:
        """
        Determine if evaluation should continue to next turn.
        
        Args:
            turn_result: Result of the current turn
            context: Current evaluation context
            
        Returns:
            bool: True if evaluation should continue
        """
        pass
    
    @abstractmethod
    def calculate_final_score(self, turn_results: List['TurnResult']) -> float:
        """
        Calculate final score based on all turn results.
        
        Args:
            turn_results: List of all turn results
            
        Returns:
            float: Final task score
        """
        pass
```

## Adapter Interfaces

### BenchmarkAdapter Interface

Base interface for all benchmark adapters.

```python
from abc import ABC, abstractmethod
from typing import Dict, List, Any, Optional

class BenchmarkAdapter(ABC):
    """
    Base interface for benchmark tool adapters.
    
    Adapters provide integration with external benchmark tools and platforms,
    translating between the unified evaluation interface and tool-specific APIs.
    """
    
    @abstractmethod
    def get_adapter_name(self) -> str:
        """
        Get the name of this adapter.
        
        Returns:
            str: Adapter name
        """
        pass
    
    @abstractmethod
    def get_supported_task_types(self) -> List[TaskType]:
        """
        Get list of supported task types.
        
        Returns:
            List[TaskType]: Supported task types
        """
        pass
    
    @abstractmethod
    def create_environment(self, task_config: Dict[str, Any]) -> 'UnifiedEnv':
        """
        Create environment instance for the benchmark.
        
        Args:
            task_config: Task-specific configuration
            
        Returns:
            UnifiedEnv: Environment instance
        """
        pass
    
    @abstractmethod
    def load_tasks(self, task_filter: Optional[Dict[str, Any]] = None) -> List['Task']:
        """
        Load available tasks from the benchmark.
        
        Args:
            task_filter: Optional filter criteria
            
        Returns:
            List[Task]: Available tasks
        """
        pass
    
    @abstractmethod
    def convert_results(self, results: Any) -> 'StandardizedResult':
        """
        Convert benchmark-specific results to standardized format.
        
        Args:
            results: Raw results from the benchmark
            
        Returns:
            StandardizedResult: Standardized result object
        """
        pass
    
    @abstractmethod
    def validate_configuration(self, config: Dict[str, Any]) -> bool:
        """
        Validate adapter configuration.
        
        Args:
            config: Configuration to validate
            
        Returns:
            bool: True if configuration is valid
        """
        pass
    
    @abstractmethod
    def get_health_status(self) -> Dict[str, Any]:
        """
        Get adapter health status.
        
        Returns:
            Dict[str, Any]: Health status information
        """
        pass
```

### ModelAdapter Interface

Interface for model adapters that handle different AI models.

```python
from typing import AsyncGenerator

class ModelAdapter(ABC):
    """
    Interface for AI model adapters.
    
    Model adapters provide a unified interface for interacting with
    different AI models and APIs.
    """
    
    @abstractmethod
    def get_model_id(self) -> str:
        """
        Get the model identifier.
        
        Returns:
            str: Model ID
        """
        pass
    
    @abstractmethod
    async def generate_response(self, 
                              prompt: str, 
                              context: Dict[str, Any],
                              config: Dict[str, Any]) -> 'ModelResponse':
        """
        Generate response from the model.
        
        Args:
            prompt: Input prompt
            context: Conversation context
            config: Generation configuration
            
        Returns:
            ModelResponse: Generated response with metadata
        """
        pass
    
    @abstractmethod
    async def generate_streaming_response(self, 
                                        prompt: str, 
                                        context: Dict[str, Any],
                                        config: Dict[str, Any]) -> AsyncGenerator[str, None]:
        """
        Generate streaming response from the model.
        
        Args:
            prompt: Input prompt
            context: Conversation context
            config: Generation configuration
            
        Yields:
            str: Response chunks
        """
        pass
    
    @abstractmethod
    def get_token_count(self, text: str) -> int:
        """
        Get token count for text.
        
        Args:
            text: Text to count tokens for
            
        Returns:
            int: Number of tokens
        """
        pass
    
    @abstractmethod
    def calculate_cost(self, input_tokens: int, output_tokens: int) -> float:
        """
        Calculate cost for token usage.
        
        Args:
            input_tokens: Number of input tokens
            output_tokens: Number of output tokens
            
        Returns:
            float: Cost in USD
        """
        pass
```

## Environment Interfaces

### UnifiedEnv Interface

The core environment interface that all evaluation environments must implement.

```python
from typing import Tuple, Dict, Any

class UnifiedEnv(ABC):
    """
    Unified environment interface for all evaluation tasks.
    
    This interface provides a standardized way to interact with different
    evaluation environments, following the OpenAI Gym-style API.
    """
    
    @abstractmethod
    def reset(self) -> Dict[str, Any]:
        """
        Reset environment to initial state.
        
        Returns:
            Dict[str, Any]: Initial observation
        """
        pass
    
    @abstractmethod
    def step(self, action: Dict[str, Any]) -> Tuple[Dict[str, Any], float, bool, Dict[str, Any]]:
        """
        Execute action and return (observation, reward, done, info).
        
        Args:
            action: Action to execute
            
        Returns:
            Tuple containing:
            - observation: New environment state
            - reward: Reward for the action
            - done: Whether episode is finished
            - info: Additional information
        """
        pass
    
    @abstractmethod
    def success(self) -> bool:
        """
        Check if task has been completed successfully.
        
        Returns:
            bool: True if task completed successfully
        """
        pass
    
    @abstractmethod
    def info(self) -> Dict[str, Any]:
        """
        Get current environment information and metadata.
        
        Returns:
            Dict[str, Any]: Environment information
        """
        pass
    
    @abstractmethod
    def get_metrics(self) -> Dict[str, float]:
        """
        Get current performance metrics.
        
        Returns:
            Dict[str, float]: Current metrics
        """
        pass
    
    @abstractmethod
    def close(self):
        """
        Clean up environment resources.
        """
        pass
    
    def render(self, mode: str = 'human') -> Any:
        """
        Render environment state (optional).
        
        Args:
            mode: Rendering mode
            
        Returns:
            Any: Rendered output (optional)
        """
        pass
```

### Action Interface

Interface for actions that can be executed in environments.

```python
class Action(ABC):
    """
    Base interface for actions in evaluation environments.
    """
    
    @abstractmethod
    def get_action_type(self) -> str:
        """
        Get the type of this action.
        
        Returns:
            str: Action type identifier
        """
        pass
    
    @abstractmethod
    def get_parameters(self) -> Dict[str, Any]:
        """
        Get action parameters.
        
        Returns:
            Dict[str, Any]: Action parameters
        """
        pass
    
    @abstractmethod
    def validate(self) -> bool:
        """
        Validate action parameters.
        
        Returns:
            bool: True if action is valid
        """
        pass
    
    @abstractmethod
    def to_dict(self) -> Dict[str, Any]:
        """
        Convert action to dictionary representation.
        
        Returns:
            Dict[str, Any]: Action as dictionary
        """
        pass
```

## Metrics Interfaces

### MetricsCalculator Interface

Interface for calculating evaluation metrics.

```python
from typing import List

class MetricsCalculator(ABC):
    """
    Interface for calculating evaluation metrics.
    
    Metrics calculators compute various performance measures
    from evaluation results.
    """
    
    @abstractmethod
    def get_calculator_name(self) -> str:
        """
        Get the name of this metrics calculator.
        
        Returns:
            str: Calculator name
        """
        pass
    
    @abstractmethod
    def get_supported_metrics(self) -> List[str]:
        """
        Get list of metrics this calculator can compute.
        
        Returns:
            List[str]: Supported metric names
        """
        pass
    
    @abstractmethod
    def calculate_task_metrics(self, turn_results: List['TurnResult']) -> Dict[str, float]:
        """
        Calculate metrics for a single task.
        
        Args:
            turn_results: List of turn results for the task
            
        Returns:
            Dict[str, float]: Calculated metrics
        """
        pass
    
    @abstractmethod
    def calculate_aggregated_metrics(self, task_results: List['TaskResult']) -> Dict[str, float]:
        """
        Calculate aggregated metrics across multiple tasks.
        
        Args:
            task_results: List of task results
            
        Returns:
            Dict[str, float]: Aggregated metrics
        """
        pass
    
    @abstractmethod
    def validate_results(self, results: List['TurnResult']) -> bool:
        """
        Validate that results are suitable for metric calculation.
        
        Args:
            results: Results to validate
            
        Returns:
            bool: True if results are valid
        """
        pass
```

### MetricsAggregator Interface

Interface for aggregating metrics across evaluations.

```python
class MetricsAggregator(ABC):
    """
    Interface for aggregating metrics across multiple evaluations.
    """
    
    @abstractmethod
    def aggregate_metrics(self, 
                         metric_sets: List[Dict[str, float]], 
                         aggregation_method: str) -> Dict[str, float]:
        """
        Aggregate metrics using specified method.
        
        Args:
            metric_sets: List of metric dictionaries
            aggregation_method: Method to use ('mean', 'median', 'max', etc.)
            
        Returns:
            Dict[str, float]: Aggregated metrics
        """
        pass
    
    @abstractmethod
    def calculate_confidence_intervals(self, 
                                     metric_sets: List[Dict[str, float]], 
                                     confidence_level: float = 0.95) -> Dict[str, Tuple[float, float]]:
        """
        Calculate confidence intervals for metrics.
        
        Args:
            metric_sets: List of metric dictionaries
            confidence_level: Confidence level (default 0.95)
            
        Returns:
            Dict[str, Tuple[float, float]]: Confidence intervals (lower, upper)
        """
        pass
```

## Safety Interfaces

### SafetyPolicy Interface

Interface for implementing safety policies.

```python
class SafetyPolicy(ABC):
    """
    Interface for safety policies that validate actions and monitor execution.
    """
    
    @abstractmethod
    def get_policy_name(self) -> str:
        """
        Get the name of this safety policy.
        
        Returns:
            str: Policy name
        """
        pass
    
    @abstractmethod
    def validate_action(self, action: Action, context: Dict[str, Any]) -> Tuple[bool, str]:
        """
        Validate action against safety policy.
        
        Args:
            action: Action to validate
            context: Current execution context
            
        Returns:
            Tuple[bool, str]: (is_valid, reason)
        """
        pass
    
    @abstractmethod
    def monitor_execution(self, execution_info: Dict[str, Any]) -> List[str]:
        """
        Monitor execution for safety violations.
        
        Args:
            execution_info: Information about current execution
            
        Returns:
            List[str]: List of detected violations
        """
        pass
    
    @abstractmethod
    def get_risk_level(self, action: Action, context: Dict[str, Any]) -> str:
        """
        Assess risk level of an action.
        
        Args:
            action: Action to assess
            context: Current execution context
            
        Returns:
            str: Risk level ('low', 'medium', 'high', 'critical')
        """
        pass
```

### SafetyIncidentHandler Interface

Interface for handling safety incidents.

```python
class SafetyIncidentHandler(ABC):
    """
    Interface for handling safety incidents and violations.
    """
    
    @abstractmethod
    def handle_incident(self, incident: 'SafetyIncident') -> 'IncidentResponse':
        """
        Handle a safety incident.
        
        Args:
            incident: Safety incident to handle
            
        Returns:
            IncidentResponse: Response to the incident
        """
        pass
    
    @abstractmethod
    def log_incident(self, incident: 'SafetyIncident'):
        """
        Log safety incident for audit purposes.
        
        Args:
            incident: Incident to log
        """
        pass
    
    @abstractmethod
    def get_incident_history(self, 
                           evaluation_id: str, 
                           limit: int = 100) -> List['SafetyIncident']:
        """
        Get incident history for an evaluation.
        
        Args:
            evaluation_id: Evaluation ID
            limit: Maximum number of incidents to return
            
        Returns:
            List[SafetyIncident]: List of incidents
        """
        pass
```

## Data Model Interfaces

### Serializable Interface

Interface for objects that can be serialized.

```python
class Serializable(ABC):
    """
    Interface for objects that can be serialized to/from dictionaries.
    """
    
    @abstractmethod
    def to_dict(self) -> Dict[str, Any]:
        """
        Convert object to dictionary representation.
        
        Returns:
            Dict[str, Any]: Object as dictionary
        """
        pass
    
    @classmethod
    @abstractmethod
    def from_dict(cls, data: Dict[str, Any]) -> 'Serializable':
        """
        Create object from dictionary representation.
        
        Args:
            data: Dictionary data
            
        Returns:
            Serializable: Created object
        """
        pass
    
    @abstractmethod
    def validate(self) -> bool:
        """
        Validate object data.
        
        Returns:
            bool: True if object is valid
        """
        pass
```

### Configurable Interface

Interface for configurable components.

```python
class Configurable(ABC):
    """
    Interface for components that can be configured.
    """
    
    @abstractmethod
    def configure(self, config: Dict[str, Any]):
        """
        Configure the component.
        
        Args:
            config: Configuration dictionary
        """
        pass
    
    @abstractmethod
    def get_configuration(self) -> Dict[str, Any]:
        """
        Get current configuration.
        
        Returns:
            Dict[str, Any]: Current configuration
        """
        pass
    
    @abstractmethod
    def validate_configuration(self, config: Dict[str, Any]) -> bool:
        """
        Validate configuration.
        
        Args:
            config: Configuration to validate
            
        Returns:
            bool: True if configuration is valid
        """
        pass
    
    @abstractmethod
    def get_default_configuration(self) -> Dict[str, Any]:
        """
        Get default configuration.
        
        Returns:
            Dict[str, Any]: Default configuration
        """
        pass
```

## API Interfaces

### APIEndpoint Interface

Interface for API endpoint implementations.

```python
from fastapi import Request, Response

class APIEndpoint(ABC):
    """
    Interface for API endpoint implementations.
    """
    
    @abstractmethod
    def get_route_path(self) -> str:
        """
        Get the route path for this endpoint.
        
        Returns:
            str: Route path
        """
        pass
    
    @abstractmethod
    def get_http_methods(self) -> List[str]:
        """
        Get supported HTTP methods.
        
        Returns:
            List[str]: Supported methods
        """
        pass
    
    @abstractmethod
    async def handle_request(self, request: Request) -> Response:
        """
        Handle incoming request.
        
        Args:
            request: FastAPI request object
            
        Returns:
            Response: FastAPI response object
        """
        pass
    
    @abstractmethod
    def get_openapi_schema(self) -> Dict[str, Any]:
        """
        Get OpenAPI schema for this endpoint.
        
        Returns:
            Dict[str, Any]: OpenAPI schema
        """
        pass
```

### AuthenticationProvider Interface

Interface for authentication providers.

```python
class AuthenticationProvider(ABC):
    """
    Interface for authentication providers.
    """
    
    @abstractmethod
    async def authenticate(self, credentials: Dict[str, Any]) -> Optional['User']:
        """
        Authenticate user with provided credentials.
        
        Args:
            credentials: User credentials
            
        Returns:
            Optional[User]: Authenticated user or None
        """
        pass
    
    @abstractmethod
    async def validate_token(self, token: str) -> Optional['User']:
        """
        Validate authentication token.
        
        Args:
            token: Authentication token
            
        Returns:
            Optional[User]: User associated with token or None
        """
        pass
    
    @abstractmethod
    async def refresh_token(self, refresh_token: str) -> Optional[str]:
        """
        Refresh authentication token.
        
        Args:
            refresh_token: Refresh token
            
        Returns:
            Optional[str]: New access token or None
        """
        pass
```

## WebSocket Interfaces

### WebSocketHandler Interface

Interface for WebSocket message handlers.

```python
class WebSocketHandler(ABC):
    """
    Interface for WebSocket message handlers.
    """
    
    @abstractmethod
    async def handle_connection(self, websocket: 'WebSocket', user: 'User') -> str:
        """
        Handle new WebSocket connection.
        
        Args:
            websocket: WebSocket connection
            user: Authenticated user
            
        Returns:
            str: Connection ID
        """
        pass
    
    @abstractmethod
    async def handle_message(self, connection_id: str, message: Dict[str, Any]):
        """
        Handle incoming WebSocket message.
        
        Args:
            connection_id: Connection ID
            message: Message data
        """
        pass
    
    @abstractmethod
    async def handle_disconnection(self, connection_id: str):
        """
        Handle WebSocket disconnection.
        
        Args:
            connection_id: Connection ID
        """
        pass
    
    @abstractmethod
    async def broadcast_message(self, message: Dict[str, Any], filter_func: Optional[callable] = None):
        """
        Broadcast message to connected clients.
        
        Args:
            message: Message to broadcast
            filter_func: Optional function to filter recipients
        """
        pass
```

### WebSocketSubscription Interface

Interface for WebSocket subscriptions.

```python
class WebSocketSubscription(ABC):
    """
    Interface for WebSocket subscription management.
    """
    
    @abstractmethod
    def subscribe(self, connection_id: str, subscription_type: str, filters: Dict[str, Any]):
        """
        Subscribe connection to events.
        
        Args:
            connection_id: Connection ID
            subscription_type: Type of subscription
            filters: Subscription filters
        """
        pass
    
    @abstractmethod
    def unsubscribe(self, connection_id: str, subscription_type: str):
        """
        Unsubscribe connection from events.
        
        Args:
            connection_id: Connection ID
            subscription_type: Type of subscription
        """
        pass
    
    @abstractmethod
    def get_subscribers(self, event_type: str, event_data: Dict[str, Any]) -> List[str]:
        """
        Get list of subscribers for an event.
        
        Args:
            event_type: Type of event
            event_data: Event data for filtering
            
        Returns:
            List[str]: List of connection IDs
        """
        pass
```

---

These interface definitions provide a comprehensive contract for all components in the Multi-Turn Evaluation Engine. Implementing these interfaces ensures consistency, extensibility, and maintainability across the entire system.

For implementation examples and best practices, refer to the [Developer Guide](developer_guide.md) and existing adapter implementations in the codebase.