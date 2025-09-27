"""
AI Evaluation Engine Core Module

This module provides the core functionality for the AI Evaluation Engine,
including extended task classes, model adapters, plugin system, and
compatibility layers for seamless integration with lm-eval.
"""

from .extended_tasks import (
    AdvancedTask,
    MultiTurnTask,
    ExtendedTaskConfig,
    ScenarioConfig,
    TurnConfig,
    ScenarioType,
    ContextMode,
    DifficultyLevel
)

from .model_adapters import (
    ModelAdapter,
    ModelType,
    ModelCapabilities,
    RateLimitConfig,
    ModelMetrics,
    plugin_registry,
    register_model_adapter
)

from .dataset_formats import (
    SingleTurnProblem,
    MultiTurnScenario,
    TestCase,
    TurnData,
    DatasetLoader,
    DatasetFormat
)

from .plugin_system import (
    PluginManager,
    PluginInterface,
    ModelAdapterPlugin,
    TaskPlugin,
    MetricPlugin,
    PluginType,
    PluginMetadata,
    plugin_manager,
    register_plugin
)

from .compatibility import (
    LegacyTaskWrapper,
    LegacyModelWrapper,
    CompatibilityManager,
    compatibility_manager,
    convert_legacy_task,
    convert_legacy_model,
    ensure_compatibility
)

from .metrics_engine import (
    MetricsEngine,
    MetricResult,
    MetricConfig,
    MetricType
)

from .scenario_metrics import (
    ScenarioSpecificMetrics,
    ScenarioDomain,
    ScenarioMetricConfig
)

from .composite_metrics import (
    CompositeMetricsSystem,
    WeightConfig,
    CompositeMetricConfig,
    AggregationMethod,
    RankingMethod,
    RealTimeMetricUpdate
)

from .metric_visualization import (
    MetricVisualizationEngine,
    ChartType,
    VisualizationFormat,
    ChartConfig,
    VisualizationData
)

__all__ = [
    # Extended Tasks
    'AdvancedTask',
    'MultiTurnTask',
    'ExtendedTaskConfig',
    'ScenarioConfig',
    'TurnConfig',
    'ScenarioType',
    'ContextMode',
    'DifficultyLevel',
    
    # Model Adapters
    'ModelAdapter',
    'ModelType',
    'ModelCapabilities',
    'RateLimitConfig',
    'ModelMetrics',
    'plugin_registry',
    'register_model_adapter',
    
    # Dataset Formats
    'SingleTurnProblem',
    'MultiTurnScenario',
    'TestCase',
    'TurnData',
    'DatasetLoader',
    'DatasetFormat',
    
    # Plugin System
    'PluginManager',
    'PluginInterface',
    'ModelAdapterPlugin',
    'TaskPlugin',
    'MetricPlugin',
    'PluginType',
    'PluginMetadata',
    'plugin_manager',
    'register_plugin',
    
    # Compatibility
    'LegacyTaskWrapper',
    'LegacyModelWrapper',
    'CompatibilityManager',
    'compatibility_manager',
    'convert_legacy_task',
    'convert_legacy_model',
    'ensure_compatibility',
    
    # Metrics Engine
    'MetricsEngine',
    'MetricResult',
    'MetricConfig',
    'MetricType',
    
    # Scenario-Specific Metrics
    'ScenarioSpecificMetrics',
    'ScenarioDomain',
    'ScenarioMetricConfig',
    
    # Composite Metrics System
    'CompositeMetricsSystem',
    'WeightConfig',
    'CompositeMetricConfig',
    'AggregationMethod',
    'RankingMethod',
    'RealTimeMetricUpdate',
    
    # Metric Visualization
    'MetricVisualizationEngine',
    'ChartType',
    'VisualizationFormat',
    'ChartConfig',
    'VisualizationData'
]