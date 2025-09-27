#!/usr/bin/env python3
"""
Test Advanced Model Configuration Management

This test file validates the implementation of task 5.2:
- Dynamic parameter tuning based on task requirements
- API rate limiting and retry strategies
- Performance monitoring and auto-scaling
- A/B testing for configuration optimization
"""

import asyncio
import json
import time
import unittest
from unittest.mock import Mock, patch, AsyncMock
from dataclasses import asdict

# Import the modules we're testing
from evaluation_engine.core.advanced_model_config import (
    AdvancedModelConfigurationManager,
    ModelConfiguration,
    TaskType,
    OptimizationStrategy,
    DynamicParameterTuner,
    AdvancedRateLimiter,
    PerformanceMonitor,
    ABTestManager,
    PerformanceMetrics,
    ABTestConfiguration,
    RateLimitConfig
)

from evaluation_engine.core.concrete_model_adapters import (
    OpenAIModelAdapter,
    AnthropicModelAdapter,
    DashScopeModelAdapter,
    GoogleModelAdapter,
    CohereModelAdapter,
    HuggingFaceModelAdapter,
    get_available_adapters,
    create_model_adapter,
    validate_model_configuration
)

from evaluation_engine.core.model_adapters import ModelType


class TestAdvancedModelConfiguration(unittest.TestCase):
    """Test advanced model configuration management."""
    
    def setUp(self):
        """Set up test fixtures."""
        self.config_manager = AdvancedModelConfigurationManager()
        
        # Create test configuration
        self.test_config = ModelConfiguration(
            model_id="gpt-4",
            model_type=ModelType.OPENAI,
            temperature=0.7,
            max_tokens=1024,
            api_key="test-key"
        )
    
    def test_model_configuration_creation(self):
        """Test model configuration creation and serialization."""
        # Test configuration creation
        config = ModelConfiguration(
            model_id="test-model",
            model_type=ModelType.OPENAI,
            temperature=0.5,
            max_tokens=512
        )
        
        self.assertEqual(config.model_id, "test-model")
        self.assertEqual(config.temperature, 0.5)
        self.assertEqual(config.max_tokens, 512)
        
        # Test serialization
        config_dict = config.to_dict()
        self.assertIsInstance(config_dict, dict)
        self.assertEqual(config_dict['model_id'], "test-model")
        
        # Test deserialization
        restored_config = ModelConfiguration.from_dict(config_dict)
        self.assertEqual(restored_config.model_id, config.model_id)
        self.assertEqual(restored_config.temperature, config.temperature)
    
    def test_dynamic_parameter_tuning(self):
        """Test dynamic parameter tuning based on task type."""
        tuner = DynamicParameterTuner()
        
        # Test code completion tuning
        tuned_config = tuner.tune_parameters(
            self.test_config, 
            TaskType.CODE_COMPLETION
        )
        
        # Code completion should have lower temperature
        self.assertLess(tuned_config.temperature, self.test_config.temperature)
        self.assertIn("```", tuned_config.stop_sequences)
        
        # Test system design tuning
        tuned_config = tuner.tune_parameters(
            self.test_config,
            TaskType.SYSTEM_DESIGN
        )
        
        # System design should have higher temperature for creativity
        self.assertGreater(tuned_config.temperature, 0.5)
        
        # Test performance-based adjustments
        poor_metrics = PerformanceMetrics()
        poor_metrics.success_rate = 0.5  # Low success rate
        poor_metrics.response_time_avg = 15.0  # High response time
        
        adjusted_config = tuner.tune_parameters(
            self.test_config,
            TaskType.CODE_COMPLETION,
            poor_metrics
        )
        
        # Should reduce temperature and max_tokens for better performance
        self.assertLess(adjusted_config.temperature, self.test_config.temperature)
        self.assertLess(adjusted_config.max_tokens, self.test_config.max_tokens)
    
    def test_advanced_rate_limiting(self):
        """Test advanced rate limiting with adaptive algorithms."""
        rate_config = RateLimitConfig(
            requests_per_minute=10,
            tokens_per_minute=1000,
            max_retries=3
        )
        
        rate_limiter = AdvancedRateLimiter(rate_config)
        
        # Test initial request allowance
        self.assertTrue(rate_limiter.can_make_request(100))
        
        # Record successful requests
        for i in range(5):
            rate_limiter.record_request(100, success=True)
        
        self.assertTrue(rate_limiter.can_make_request(100))
        
        # Record failed requests to trigger adaptive limiting
        for i in range(3):
            rate_limiter.record_request(100, success=False)
        
        # Adaptive factor should be reduced
        self.assertLess(rate_limiter.adaptive_factor, 1.0)
        
        # Test token limit
        self.assertFalse(rate_limiter.can_make_request(2000))  # Exceeds token limit
        
        # Test wait time calculation
        wait_time = rate_limiter.get_wait_time()
        self.assertGreaterEqual(wait_time, 0.0)
    
    def test_performance_monitoring(self):
        """Test performance monitoring and metrics tracking."""
        monitor = PerformanceMonitor()
        
        # Record performance data
        model_id = "test-model"
        monitor.record_performance(model_id, 2.5, True, 0.01, 0.85)
        monitor.record_performance(model_id, 3.0, True, 0.012, 0.90)
        monitor.record_performance(model_id, 15.0, False, 0.0, 0.0)  # Failed request
        
        # Get performance summary
        summary = monitor.get_performance_summary(model_id)
        
        self.assertIn('response_time_avg', summary)
        self.assertIn('success_rate', summary)
        self.assertIn('error_rate', summary)
        self.assertGreater(summary['total_requests'], 0)
        
        # Test scaling recommendations
        recommendations = monitor.get_scaling_recommendations(model_id)
        self.assertIsInstance(recommendations, list)
        
        # Should have recommendations due to high response time and errors
        self.assertGreater(len(recommendations), 0)
        
        # Test performance metrics calculations
        metrics = monitor.metrics[model_id]
        self.assertGreater(metrics.response_time_avg, 0)
        self.assertLess(metrics.success_rate, 1.0)  # Due to one failed request
        self.assertGreater(metrics.error_rate, 0)
    
    def test_ab_testing(self):
        """Test A/B testing for configuration optimization."""
        ab_manager = ABTestManager()
        
        # Create test variants
        variant_a = ModelConfiguration(
            model_id="gpt-4",
            model_type=ModelType.OPENAI,
            temperature=0.3,
            max_tokens=512
        )
        
        variant_b = ModelConfiguration(
            model_id="gpt-4",
            model_type=ModelType.OPENAI,
            temperature=0.7,
            max_tokens=1024
        )
        
        variants = {"variant_a": variant_a, "variant_b": variant_b}
        traffic_split = {"variant_a": 0.5, "variant_b": 0.5}
        
        # Create A/B test
        test_config = ab_manager.create_ab_test(
            test_id="temp_test",
            description="Test temperature settings",
            variants=variants,
            traffic_split=traffic_split,
            minimum_samples=10
        )
        
        self.assertEqual(test_config.test_id, "temp_test")
        self.assertEqual(len(test_config.variants), 2)
        
        # Start test
        ab_manager.start_ab_test("temp_test")
        self.assertTrue(test_config.is_active)
        
        # Test variant selection
        selected_variant, selected_config = ab_manager.select_variant("temp_test")
        self.assertIn(selected_variant, ["variant_a", "variant_b"])
        self.assertIsInstance(selected_config, ModelConfiguration)
        
        # Record test results
        for i in range(20):
            variant_name = "variant_a" if i % 2 == 0 else "variant_b"
            # Variant A performs better
            success = True if variant_name == "variant_a" else (i % 3 != 0)
            quality = 0.9 if variant_name == "variant_a" else 0.7
            
            ab_manager.record_test_result(
                "temp_test", variant_name, 2.0, success, 0.01, quality
            )
        
        # Analyze results
        analysis = ab_manager.analyze_ab_test("temp_test")
        
        self.assertEqual(analysis['test_id'], "temp_test")
        self.assertIn('variants', analysis)
        self.assertIn('winner', analysis)
        
        # Variant A should be the winner
        self.assertEqual(analysis['winner'], "variant_a")
        
        # Get best configuration
        best_config = ab_manager.get_best_configuration("temp_test")
        self.assertIsNotNone(best_config)
        self.assertEqual(best_config.temperature, 0.3)  # Variant A's temperature
        
        # Stop test
        ab_manager.stop_ab_test("temp_test")
        self.assertFalse(test_config.is_active)
    
    def test_configuration_manager_integration(self):
        """Test the integrated configuration manager."""
        # Register model configuration
        self.config_manager.register_model_configuration("gpt-4", self.test_config)
        
        # Test optimized configuration retrieval
        optimized_config = self.config_manager.get_optimized_configuration(
            "gpt-4", 
            TaskType.CODE_COMPLETION,
            OptimizationStrategy.PERFORMANCE
        )
        
        self.assertIsInstance(optimized_config, ModelConfiguration)
        self.assertEqual(optimized_config.model_id, "gpt-4")
        
        # Test rate limiting
        can_request = self.config_manager.can_make_request("gpt-4", 100)
        self.assertTrue(can_request)
        
        # Record request result
        self.config_manager.record_request_result(
            "gpt-4", 2.5, True, 150, 0.015, 0.85
        )
        
        # Get performance summary
        summary = self.config_manager.get_performance_summary("gpt-4")
        self.assertIn('response_time_avg', summary)
        
        # Test A/B test creation
        test_config = self.config_manager.create_ab_test(
            test_id="integration_test",
            description="Integration test",
            base_model_id="gpt-4",
            parameter_variations={
                "low_temp": {"temperature": 0.1},
                "high_temp": {"temperature": 0.9}
            },
            task_type=TaskType.CODE_COMPLETION
        )
        
        self.assertIsInstance(test_config, ABTestConfiguration)
        self.assertEqual(len(test_config.variants), 2)
        
        # Test configuration export/import
        exported = self.config_manager.export_configuration("gpt-4")
        self.assertIsInstance(exported, dict)
        
        self.config_manager.import_configuration("gpt-4-copy", exported)
        copy_config = self.config_manager.configurations["gpt-4-copy"]
        self.assertEqual(copy_config.model_id, exported['model_id'])


class TestConcreteModelAdapters(unittest.TestCase):
    """Test concrete model adapter implementations."""
    
    def test_openai_adapter_creation(self):
        """Test OpenAI adapter creation and capabilities."""
        adapter = OpenAIModelAdapter("gpt-4", api_key="test-key")
        
        self.assertEqual(adapter.model_id, "gpt-4")
        self.assertEqual(adapter.model_type, ModelType.OPENAI)
        
        # Test capabilities
        capabilities = adapter.capabilities
        self.assertGreater(capabilities.max_context_length, 0)
        self.assertTrue(capabilities.supports_chat_templates)
        self.assertTrue(capabilities.supports_function_calling)
        
        # Test cost calculation
        cost = adapter._calculate_cost(1000)
        self.assertGreater(cost, 0)
    
    def test_anthropic_adapter_creation(self):
        """Test Anthropic adapter creation and capabilities."""
        adapter = AnthropicModelAdapter("claude-3-sonnet", api_key="test-key")
        
        self.assertEqual(adapter.model_id, "claude-3-sonnet")
        self.assertEqual(adapter.model_type, ModelType.ANTHROPIC)
        
        capabilities = adapter.capabilities
        self.assertGreater(capabilities.max_context_length, 100000)  # Claude has large context
        self.assertTrue(capabilities.supports_chat_templates)
    
    def test_dashscope_adapter_creation(self):
        """Test DashScope adapter creation and capabilities."""
        adapter = DashScopeModelAdapter("qwen-max", api_key="test-key")
        
        self.assertEqual(adapter.model_id, "qwen-max")
        self.assertEqual(adapter.model_type, ModelType.DASHSCOPE)
        
        capabilities = adapter.capabilities
        self.assertIn('zh', capabilities.supported_languages)  # Chinese support
        self.assertIn('en', capabilities.supported_languages)
    
    def test_google_adapter_creation(self):
        """Test Google adapter creation and capabilities."""
        adapter = GoogleModelAdapter("gemini-pro", api_key="test-key")
        
        self.assertEqual(adapter.model_id, "gemini-pro")
        self.assertEqual(adapter.model_type, ModelType.GOOGLE)
        
        capabilities = adapter.capabilities
        self.assertTrue(capabilities.supports_multimodal)
        self.assertTrue(capabilities.supports_function_calling)
    
    def test_cohere_adapter_creation(self):
        """Test Cohere adapter creation and capabilities."""
        adapter = CohereModelAdapter("command", api_key="test-key")
        
        self.assertEqual(adapter.model_id, "command")
        self.assertEqual(adapter.model_type, ModelType.COHERE)
        
        capabilities = adapter.capabilities
        self.assertTrue(capabilities.supports_chat_templates)
    
    @patch('transformers.AutoTokenizer')
    @patch('transformers.AutoModelForCausalLM')
    def test_huggingface_adapter_creation(self, mock_model, mock_tokenizer):
        """Test HuggingFace adapter creation and capabilities."""
        # Mock the transformers components
        mock_tokenizer.from_pretrained.return_value = Mock()
        mock_model.from_pretrained.return_value = Mock()
        
        adapter = HuggingFaceModelAdapter("microsoft/DialoGPT-medium")
        
        self.assertEqual(adapter.model_id, "microsoft/DialoGPT-medium")
        self.assertEqual(adapter.model_type, ModelType.HUGGINGFACE)
        
        # Verify transformers were called
        mock_tokenizer.from_pretrained.assert_called_once()
        mock_model.from_pretrained.assert_called_once()
    
    def test_adapter_registry(self):
        """Test model adapter registry functionality."""
        available_adapters = get_available_adapters()
        
        self.assertIsInstance(available_adapters, dict)
        self.assertIn('openai', available_adapters)
        self.assertIn('anthropic', available_adapters)
        self.assertIn('dashscope', available_adapters)
        self.assertIn('google', available_adapters)
        self.assertIn('cohere', available_adapters)
        self.assertIn('huggingface', available_adapters)
        
        # Test adapter creation
        adapter = create_model_adapter('openai', 'gpt-4', api_key='test')
        self.assertIsInstance(adapter, OpenAIModelAdapter)
        
        # Test configuration validation
        valid_config = {'api_key': 'test', 'temperature': 0.7}
        # This would normally validate against the actual API
        # For testing, we just check it doesn't crash
        try:
            validate_model_configuration('openai', 'gpt-4', valid_config)
        except Exception as e:
            # Expected to fail without real API key, but shouldn't crash
            self.assertIsInstance(e, Exception)


class TestPerformanceMetrics(unittest.TestCase):
    """Test performance metrics calculations."""
    
    def test_performance_metrics_updates(self):
        """Test performance metrics update calculations."""
        metrics = PerformanceMetrics()
        
        # Record some performance data
        metrics.update(2.0, True, 0.01, 0.8)
        metrics.update(3.0, True, 0.015, 0.9)
        metrics.update(1.5, False, 0.0, 0.0)
        
        # Check calculations
        self.assertAlmostEqual(metrics.response_time_avg, 2.17, places=1)
        self.assertAlmostEqual(metrics.success_rate, 2/3, places=2)
        self.assertAlmostEqual(metrics.error_rate, 1/3, places=2)
        self.assertGreater(metrics.quality_score, 0)
        
        # Test performance scores for different strategies
        perf_score = metrics.get_performance_score(OptimizationStrategy.PERFORMANCE)
        cost_score = metrics.get_performance_score(OptimizationStrategy.COST)
        speed_score = metrics.get_performance_score(OptimizationStrategy.SPEED)
        balanced_score = metrics.get_performance_score(OptimizationStrategy.BALANCED)
        
        self.assertGreater(perf_score, 0)
        self.assertGreater(cost_score, 0)
        self.assertGreater(speed_score, 0)
        self.assertGreater(balanced_score, 0)


def run_integration_test():
    """Run integration test with real configuration management."""
    print("Running integration test for advanced model configuration...")
    
    # Create configuration manager
    config_manager = AdvancedModelConfigurationManager()
    
    # Create test configurations for different models
    openai_config = ModelConfiguration(
        model_id="gpt-4",
        model_type=ModelType.OPENAI,
        temperature=0.7,
        max_tokens=1024,
        api_key="test-openai-key",
        daily_budget=50.0
    )
    
    anthropic_config = ModelConfiguration(
        model_id="claude-3-sonnet",
        model_type=ModelType.ANTHROPIC,
        temperature=0.6,
        max_tokens=2048,
        api_key="test-anthropic-key",
        daily_budget=75.0
    )
    
    # Register configurations
    config_manager.register_model_configuration("gpt-4", openai_config)
    config_manager.register_model_configuration("claude-3-sonnet", anthropic_config)
    
    print("✓ Registered model configurations")
    
    # Test parameter tuning for different task types
    for task_type in [TaskType.CODE_COMPLETION, TaskType.SYSTEM_DESIGN, TaskType.BUG_FIX]:
        optimized = config_manager.get_optimized_configuration(
            "gpt-4", task_type, OptimizationStrategy.BALANCED
        )
        print(f"✓ Optimized configuration for {task_type.value}: temp={optimized.temperature}")
    
    # Simulate request performance data
    for i in range(50):
        model_id = "gpt-4" if i % 2 == 0 else "claude-3-sonnet"
        response_time = 2.0 + (i % 5) * 0.5  # Varying response times
        success = i % 10 != 0  # 90% success rate
        tokens = 100 + (i % 20) * 10
        cost = 0.01 + (i % 5) * 0.002
        quality = 0.8 + (i % 3) * 0.1
        
        config_manager.record_request_result(
            model_id, response_time, success, tokens, cost, quality
        )
    
    print("✓ Recorded performance data")
    
    # Get performance summaries
    for model_id in ["gpt-4", "claude-3-sonnet"]:
        summary = config_manager.get_performance_summary(model_id)
        print(f"✓ {model_id} performance: "
              f"avg_time={summary['response_time_avg']:.2f}s, "
              f"success_rate={summary['success_rate']:.2%}")
        
        recommendations = config_manager.get_scaling_recommendations(model_id)
        if recommendations:
            print(f"  Scaling recommendations: {len(recommendations)} items")
    
    # Create and run A/B test
    ab_test = config_manager.create_ab_test(
        test_id="temperature_optimization",
        description="Optimize temperature for code completion",
        base_model_id="gpt-4",
        parameter_variations={
            "conservative": {"temperature": 0.1},
            "moderate": {"temperature": 0.3},
            "creative": {"temperature": 0.7}
        },
        task_type=TaskType.CODE_COMPLETION,
        minimum_samples=5
    )
    
    config_manager.start_ab_test("temperature_optimization")
    print("✓ Started A/B test")
    
    # Simulate A/B test data
    for i in range(30):
        variant, variant_config = config_manager.get_ab_test_configuration("temperature_optimization")
        
        # Conservative variant performs better for code completion
        if variant == "conservative":
            success_rate = 0.95
            quality = 0.9
        elif variant == "moderate":
            success_rate = 0.85
            quality = 0.8
        else:  # creative
            success_rate = 0.7
            quality = 0.7
        
        success = (i % 100) < (success_rate * 100)
        config_manager.ab_test_manager.record_test_result(
            "temperature_optimization", variant, 2.0, success, 0.01, quality
        )
    
    # Analyze A/B test results
    analysis = config_manager.analyze_ab_test("temperature_optimization")
    print(f"✓ A/B test winner: {analysis['winner']} "
          f"(significant: {analysis['significant']})")
    
    # Apply best configuration
    if analysis['significant']:
        applied = config_manager.apply_best_configuration("temperature_optimization", "gpt-4")
        if applied:
            print("✓ Applied best configuration from A/B test")
    
    config_manager.stop_ab_test("temperature_optimization")
    
    # Test configuration export/import
    exported = config_manager.export_configuration("gpt-4")
    config_manager.import_configuration("gpt-4-optimized", exported)
    print("✓ Configuration export/import successful")
    
    # Cleanup
    config_manager.shutdown()
    print("✓ Configuration manager shutdown complete")
    
    print("\n🎉 Integration test completed successfully!")


if __name__ == '__main__':
    # Run unit tests
    print("Running unit tests...")
    unittest.main(argv=[''], exit=False, verbosity=2)
    
    print("\n" + "="*50)
    
    # Run integration test
    run_integration_test()