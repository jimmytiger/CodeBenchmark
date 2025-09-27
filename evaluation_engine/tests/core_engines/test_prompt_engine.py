"""
Test suite for the Intelligent Prompt Engine

This test suite validates all components of the prompt engine including:
- Context-aware prompt generation
- Model-specific adaptations
- Template system with conditional logic
- A/B testing framework
- Prompt optimization algorithms
"""

import pytest
import json
import tempfile
from pathlib import Path
from datetime import datetime, timedelta
from unittest.mock import Mock, patch

# Import the modules to test
from evaluation_engine.core.prompt_engine import (
    PromptEngine, ModelProfile, TaskConfig, TemplateSpec, ABTestConfig,
    ContextMode, PromptStyle, ReasoningStyle, OutputFormat,
    ContextSelector, ModelStyleAdapter, PromptOptimizer, TemplateEngine,
    create_prompt_engine
)

from evaluation_engine.core.ab_testing import (
    ABTestManager, TestConfiguration, TestVariant, TestMetric, TestResult,
    StatisticalAnalyzer, TestStatus, create_ab_test_manager
)


class TestTemplateEngine:
    """Test the template engine functionality"""
    
    def test_template_rendering(self):
        """Test basic template rendering"""
        engine = TemplateEngine()
        
        template = "Hello {{name}}, your score is {{score}}"
        variables = {"name": "Alice", "score": 95}
        
        result = engine.render_template(template, variables)
        assert result == "Hello Alice, your score is 95"
    
    def test_conditional_logic(self):
        """Test conditional logic in templates"""
        engine = TemplateEngine()
        
        template = """
        Task: {{task}}
        {% if examples %}
        Examples:
        {% for example in examples %}
        - {{ example }}
        {% endfor %}
        {% endif %}
        """
        
        variables = {
            "task": "Complete the function",
            "examples": ["example1", "example2"]
        }
        
        result = engine.render_template(template, variables)
        assert "Examples:" in result
        assert "example1" in result
        assert "example2" in result
    
    def test_custom_filters(self):
        """Test custom Jinja2 filters"""
        engine = TemplateEngine()
        
        template = "{{ code | format_code_block('python') }}"
        variables = {"code": "print('hello')"}
        
        result = engine.render_template(template, variables)
        assert "```python" in result
        assert "print('hello')" in result
    
    def test_template_validation(self):
        """Test template validation"""
        engine = TemplateEngine()
        
        valid_template = "Hello {{name}}"
        invalid_template = "Hello {{name"
        
        assert engine.validate_template(valid_template, ["name"]) == True
        assert engine.validate_template(invalid_template, ["name"]) == False


class TestContextSelector:
    """Test context mode selection logic"""
    
    def test_context_selection_small_model(self):
        """Test context selection for small context window models"""
        selector = ContextSelector()
        
        model_profile = ModelProfile(
            model_id="small-model",
            model_family="test",
            context_window=2000,
            supports_system_messages=True,
            supports_function_calling=False,
            supports_multimodal=False,
            preferred_style=PromptStyle.DIRECT_IMPERATIVE,
            preferred_reasoning=ReasoningStyle.STEP_BY_STEP,
            preferred_format=OutputFormat.STRUCTURED_JSON
        )
        
        task_config = TaskConfig(
            task_id="test_task",
            task_type="code_completion",
            scenario_type="single_turn",
            domain="programming",
            difficulty_level="easy"
        )
        
        context_mode = selector.select_optimal_context(model_profile, task_config)
        assert context_mode == ContextMode.MINIMAL_CONTEXT
    
    def test_context_selection_large_model(self):
        """Test context selection for large context window models"""
        selector = ContextSelector()
        
        model_profile = ModelProfile(
            model_id="large-model",
            model_family="test",
            context_window=32000,
            supports_system_messages=True,
            supports_function_calling=True,
            supports_multimodal=True,
            preferred_style=PromptStyle.CONVERSATIONAL_POLITE,
            preferred_reasoning=ReasoningStyle.ANALYTICAL_DETAILED,
            preferred_format=OutputFormat.MARKDOWN_STRUCTURED
        )
        
        task_config = TaskConfig(
            task_id="test_task",
            task_type="quantitative_trading",
            scenario_type="multi_turn",
            domain="quantitative_finance",
            difficulty_level="hard",
            requires_multi_turn=True
        )
        
        context_mode = selector.select_optimal_context(model_profile, task_config)
        assert context_mode == ContextMode.DOMAIN_CONTEXT
    
    def test_context_strategies(self):
        """Test different context strategies"""
        selector = ContextSelector()
        
        task_data = {
            "brief_context": "Brief context",
            "full_context": "Full detailed context",
            "domain_context": "Domain-specific context",
            "examples": ["ex1", "ex2", "ex3"],
            "domain_examples": ["domain_ex1", "domain_ex2"],
            "background": "Background info",
            "domain_knowledge": {"key1": "value1"},
            "best_practices": ["practice1", "practice2"]
        }
        
        # Test no context
        no_context = selector._no_context_strategy(task_data)
        assert no_context["context_information"] == ""
        assert no_context["examples"] == []
        
        # Test minimal context
        minimal_context = selector._minimal_context_strategy(task_data)
        assert minimal_context["context_information"] == "Brief context"
        assert len(minimal_context["examples"]) == 1
        
        # Test full context
        full_context = selector._full_context_strategy(task_data)
        assert full_context["context_information"] == "Full detailed context"
        assert len(full_context["examples"]) <= 3
        
        # Test domain context
        domain_context = selector._domain_context_strategy(task_data)
        assert domain_context["context_information"] == "Domain-specific context"
        assert "domain_knowledge" in domain_context


class TestModelStyleAdapter:
    """Test model-specific style adaptations"""
    
    def test_openai_style_adaptation(self):
        """Test OpenAI-specific style adaptation"""
        adapter = ModelStyleAdapter()
        
        model_profile = ModelProfile(
            model_id="gpt-4",
            model_family="openai_gpt",
            context_window=8192,
            supports_system_messages=True,
            supports_function_calling=True,
            supports_multimodal=False,
            preferred_style=PromptStyle.DIRECT_IMPERATIVE,
            preferred_reasoning=ReasoningStyle.STEP_BY_STEP,
            preferred_format=OutputFormat.STRUCTURED_JSON
        )
        
        base_prompt = "{{SYSTEM_PREFIX}} coding tasks. {{TASK_PREFIX}} complete this function."
        
        adapted_prompt = adapter.adapt_prompt_style(base_prompt, model_profile)
        
        assert "You are a helpful AI assistant specialized in" in adapted_prompt
        assert "Please" in adapted_prompt
        assert "JSON format" in adapted_prompt
    
    def test_anthropic_style_adaptation(self):
        """Test Anthropic Claude-specific style adaptation"""
        adapter = ModelStyleAdapter()
        
        model_profile = ModelProfile(
            model_id="claude-3",
            model_family="anthropic_claude",
            context_window=200000,
            supports_system_messages=True,
            supports_function_calling=False,
            supports_multimodal=True,
            preferred_style=PromptStyle.CONVERSATIONAL_POLITE,
            preferred_reasoning=ReasoningStyle.ANALYTICAL_DETAILED,
            preferred_format=OutputFormat.MARKDOWN_STRUCTURED
        )
        
        base_prompt = "{{SYSTEM_PREFIX}} coding tasks. {{TASK_PREFIX}} complete this function."
        
        adapted_prompt = adapter.adapt_prompt_style(base_prompt, model_profile)
        
        assert "I'm Claude" in adapted_prompt
        assert "I'd be happy to help you" in adapted_prompt
        assert "markdown formatting" in adapted_prompt
    
    def test_unknown_model_fallback(self):
        """Test fallback for unknown model families"""
        adapter = ModelStyleAdapter()
        
        model_profile = ModelProfile(
            model_id="unknown-model",
            model_family="unknown_family",
            context_window=4000,
            supports_system_messages=True,
            supports_function_calling=False,
            supports_multimodal=False,
            preferred_style=PromptStyle.TECHNICAL_PRECISE,
            preferred_reasoning=ReasoningStyle.IMPLEMENTATION_FOCUSED,
            preferred_format=OutputFormat.CODE_BLOCKS
        )
        
        base_prompt = "{{SYSTEM_PREFIX}} coding tasks."
        
        adapted_prompt = adapter.adapt_prompt_style(base_prompt, model_profile)
        
        # Should use huggingface_local as fallback
        assert "I am an AI assistant focused on" in adapted_prompt


class TestPromptOptimizer:
    """Test prompt optimization algorithms"""
    
    def test_token_efficiency_optimization(self):
        """Test token efficiency optimization"""
        optimizer = PromptOptimizer()
        
        model_profile = ModelProfile(
            model_id="test-model",
            model_family="test",
            context_window=4000,
            supports_system_messages=True,
            supports_function_calling=False,
            supports_multimodal=False,
            preferred_style=PromptStyle.DIRECT_IMPERATIVE,
            preferred_reasoning=ReasoningStyle.STEP_BY_STEP,
            preferred_format=OutputFormat.STRUCTURED_JSON,
            token_efficiency_factor=0.8
        )
        
        task_config = TaskConfig(
            task_id="test_task",
            task_type="code_completion",
            scenario_type="single_turn",
            domain="programming",
            difficulty_level="easy"
        )
        
        verbose_prompt = "Please kindly help me very much with this really important task and also provide assistance"
        
        optimized_prompt, score = optimizer.optimize_prompt(verbose_prompt, model_profile, task_config)
        
        # Should be shorter and have a positive optimization score
        assert len(optimized_prompt) < len(verbose_prompt)
        assert score > 0
    
    def test_attention_pattern_optimization(self):
        """Test attention pattern optimization"""
        optimizer = PromptOptimizer()
        
        model_profile = ModelProfile(
            model_id="test-model",
            model_family="test",
            context_window=4000,
            supports_system_messages=True,
            supports_function_calling=False,
            supports_multimodal=False,
            preferred_style=PromptStyle.DIRECT_IMPERATIVE,
            preferred_reasoning=ReasoningStyle.STEP_BY_STEP,
            preferred_format=OutputFormat.STRUCTURED_JSON,
            attention_pattern_preference="structured"
        )
        
        task_config = TaskConfig(
            task_id="test_task",
            task_type="bug_fix",
            scenario_type="single_turn",
            domain="programming",
            difficulty_level="easy"
        )
        
        base_prompt = "Fix this bug in the code"
        
        optimized_prompt, score = optimizer.optimize_prompt(base_prompt, model_profile, task_config)
        
        # Should add IMPORTANT prefix for bug_fix tasks
        assert "IMPORTANT:" in optimized_prompt
        assert score > 0


class TestPromptEngine:
    """Test the main PromptEngine class"""
    
    def test_prompt_generation(self):
        """Test basic prompt generation"""
        engine = create_prompt_engine()
        
        model_profile = ModelProfile(
            model_id="gpt-4",
            model_family="openai_gpt",
            context_window=8192,
            supports_system_messages=True,
            supports_function_calling=True,
            supports_multimodal=False,
            preferred_style=PromptStyle.DIRECT_IMPERATIVE,
            preferred_reasoning=ReasoningStyle.STEP_BY_STEP,
            preferred_format=OutputFormat.STRUCTURED_JSON
        )
        
        task_config = TaskConfig(
            task_id="test_task",
            task_type="code_completion",
            scenario_type="single_turn",
            domain="programming",
            difficulty_level="easy",
            language="python",
            requires_code_execution=True
        )
        
        task_data = {
            "description": "Complete the fibonacci function",
            "code_context": "def fibonacci(n):",
            "examples": ["fibonacci(5) = 5"]
        }
        
        optimized_prompt = engine.generate_prompt(task_config, model_profile, task_data)
        
        assert optimized_prompt.prompt_text is not None
        assert len(optimized_prompt.prompt_text) > 0
        assert optimized_prompt.context_mode in ContextMode
        assert optimized_prompt.estimated_tokens > 0
        assert 0 <= optimized_prompt.optimization_score <= 1
        assert "fibonacci" in optimized_prompt.prompt_text.lower()
    
    def test_custom_template_creation(self):
        """Test custom template creation"""
        engine = create_prompt_engine()
        
        template_spec = TemplateSpec(
            template_id="custom_test",
            base_template="Custom template: {{custom_var}}",
            variables={"custom_var": "test_value"}
        )
        
        template_id = engine.create_custom_template(template_spec)
        assert template_id == "custom_test"
        assert template_id in engine.base_templates
    
    def test_prompt_caching(self):
        """Test prompt caching functionality"""
        engine = create_prompt_engine()
        
        model_profile = ModelProfile(
            model_id="test-model",
            model_family="test",
            context_window=4000,
            supports_system_messages=True,
            supports_function_calling=False,
            supports_multimodal=False,
            preferred_style=PromptStyle.DIRECT_IMPERATIVE,
            preferred_reasoning=ReasoningStyle.STEP_BY_STEP,
            preferred_format=OutputFormat.STRUCTURED_JSON
        )
        
        task_config = TaskConfig(
            task_id="cache_test",
            task_type="code_completion",
            scenario_type="single_turn",
            domain="programming",
            difficulty_level="easy"
        )
        
        task_data = {"description": "Test task"}
        
        # Generate prompt twice
        prompt1 = engine.generate_prompt(task_config, model_profile, task_data)
        prompt2 = engine.generate_prompt(task_config, model_profile, task_data)
        
        # Should be identical (cached)
        assert prompt1.prompt_text == prompt2.prompt_text
        
        # Check cache stats
        stats = engine.get_cache_stats()
        assert stats["cache_size"] >= 1
    
    def test_ab_testing_integration(self):
        """Test A/B testing integration"""
        engine = create_prompt_engine()
        
        ab_config = ABTestConfig(
            test_id="prompt_test_001",
            test_name="Test Prompt Optimization",
            variants=[
                {"variant_id": "control", "template": "Basic prompt"},
                {"variant_id": "treatment", "template": "Optimized prompt"}
            ],
            sample_size=50,
            success_metrics=["accuracy", "efficiency"]
        )
        
        test_id = engine.run_ab_test(ab_config)
        assert test_id == "prompt_test_001"
        
        # Record some test results
        engine.record_ab_test_result(test_id, "control", {"accuracy": 0.8, "efficiency": 0.7})
        engine.record_ab_test_result(test_id, "treatment", {"accuracy": 0.85, "efficiency": 0.75})
        
        # Should not have results yet (need more samples)
        result = engine.analyze_ab_test(test_id)
        assert result is None  # Not enough samples


class TestABTestManager:
    """Test the A/B testing framework"""
    
    def test_test_creation(self):
        """Test A/B test creation"""
        with tempfile.TemporaryDirectory() as temp_dir:
            db_path = Path(temp_dir) / "test.db"
            manager = create_ab_test_manager(db_path)
            
            variants = [
                TestVariant(
                    variant_id="control",
                    name="Control",
                    description="Original prompt",
                    prompt_template="Complete: {{task}}"
                ),
                TestVariant(
                    variant_id="treatment",
                    name="Treatment",
                    description="Optimized prompt",
                    prompt_template="Please complete step by step: {{task}}"
                )
            ]
            
            metrics = [
                TestMetric(
                    metric_id="accuracy",
                    name="Accuracy",
                    description="Task accuracy",
                    metric_type="primary"
                )
            ]
            
            config = TestConfiguration(
                test_id="test_001",
                name="Prompt Test",
                description="Testing prompt optimization",
                variants=variants,
                metrics=metrics,
                sample_size_per_variant=50
            )
            
            test_id = manager.create_test(config)
            assert test_id == "test_001"
            
            # Test should be in draft status
            tests = manager.list_tests()
            assert len(tests) == 1
            assert tests[0]["status"] == TestStatus.DRAFT.value
    
    def test_test_lifecycle(self):
        """Test complete A/B test lifecycle"""
        with tempfile.TemporaryDirectory() as temp_dir:
            db_path = Path(temp_dir) / "test.db"
            manager = create_ab_test_manager(db_path)
            
            # Create test
            variants = [
                TestVariant("control", "Control", "Control variant", "Template A"),
                TestVariant("treatment", "Treatment", "Treatment variant", "Template B")
            ]
            
            metrics = [
                TestMetric("accuracy", "Accuracy", "Accuracy metric", "primary")
            ]
            
            config = TestConfiguration(
                test_id="lifecycle_test",
                name="Lifecycle Test",
                description="Test lifecycle",
                variants=variants,
                metrics=metrics,
                sample_size_per_variant=30
            )
            
            test_id = manager.create_test(config)
            
            # Start test
            assert manager.start_test(test_id) == True
            
            # Record results
            for i in range(60):  # 30 per variant
                variant_id = "control" if i < 30 else "treatment"
                accuracy = 0.8 + (0.1 if variant_id == "treatment" else 0) + (i % 10) * 0.01
                
                result = TestResult(
                    result_id=f"result_{i}",
                    test_id=test_id,
                    variant_id=variant_id,
                    user_id=f"user_{i}",
                    session_id=f"session_{i}",
                    metrics={"accuracy": accuracy},
                    metadata={},
                    timestamp=datetime.now()
                )
                
                manager.record_result(result)
            
            # Analyze test
            analysis = manager.analyze_test(test_id)
            assert analysis is not None
            assert analysis.test_id == test_id
            assert "control" in analysis.variant_statistics
            assert "treatment" in analysis.variant_statistics
            
            # Get test summary
            summary = manager.get_test_summary(test_id)
            assert summary.test_id == test_id
            assert summary.total_samples == 60
            assert summary.variant_samples["control"] == 30
            assert summary.variant_samples["treatment"] == 30
            
            # Stop test
            assert manager.stop_test(test_id) == True
    
    def test_statistical_analysis(self):
        """Test statistical analysis functionality"""
        analyzer = StatisticalAnalyzer()
        
        # Create mock test configuration
        variants = [
            TestVariant("control", "Control", "Control variant", "Template A"),
            TestVariant("treatment", "Treatment", "Treatment variant", "Template B")
        ]
        
        metrics = [
            TestMetric("accuracy", "Accuracy", "Accuracy metric", "primary")
        ]
        
        config = TestConfiguration(
            test_id="stats_test",
            name="Statistics Test",
            description="Test statistics",
            variants=variants,
            metrics=metrics,
            sample_size_per_variant=50
        )
        
        # Create mock results with clear difference
        results = []
        for i in range(100):
            variant_id = "control" if i < 50 else "treatment"
            # Treatment has higher accuracy
            base_accuracy = 0.7 if variant_id == "control" else 0.8
            accuracy = base_accuracy + (i % 10) * 0.01
            
            result = TestResult(
                result_id=f"result_{i}",
                test_id="stats_test",
                variant_id=variant_id,
                user_id=f"user_{i}",
                session_id=f"session_{i}",
                metrics={"accuracy": accuracy},
                metadata={},
                timestamp=datetime.now()
            )
            results.append(result)
        
        # Analyze results
        analysis = analyzer.analyze_test_results(config, results)
        
        assert analysis.test_id == "stats_test"
        assert analysis.primary_metric == "accuracy"
        assert "control" in analysis.variant_statistics
        assert "treatment" in analysis.variant_statistics
        
        # Treatment should have higher mean accuracy
        control_mean = analysis.variant_statistics["control"]["accuracy"]["mean"]
        treatment_mean = analysis.variant_statistics["treatment"]["accuracy"]["mean"]
        assert treatment_mean > control_mean
        
        # Should have confidence intervals
        assert "control" in analysis.confidence_intervals
        assert "treatment" in analysis.confidence_intervals
        
        # Should have recommendation
        assert analysis.recommendation is not None
        assert len(analysis.recommendation) > 0


class TestIntegration:
    """Integration tests for the complete prompt engine system"""
    
    def test_end_to_end_prompt_optimization(self):
        """Test end-to-end prompt optimization workflow"""
        # Create prompt engine
        engine = create_prompt_engine()
        
        # Create model profiles for different models
        openai_profile = ModelProfile(
            model_id="gpt-4",
            model_family="openai_gpt",
            context_window=8192,
            supports_system_messages=True,
            supports_function_calling=True,
            supports_multimodal=False,
            preferred_style=PromptStyle.DIRECT_IMPERATIVE,
            preferred_reasoning=ReasoningStyle.STEP_BY_STEP,
            preferred_format=OutputFormat.STRUCTURED_JSON
        )
        
        claude_profile = ModelProfile(
            model_id="claude-3",
            model_family="anthropic_claude",
            context_window=200000,
            supports_system_messages=True,
            supports_function_calling=False,
            supports_multimodal=True,
            preferred_style=PromptStyle.CONVERSATIONAL_POLITE,
            preferred_reasoning=ReasoningStyle.ANALYTICAL_DETAILED,
            preferred_format=OutputFormat.MARKDOWN_STRUCTURED
        )
        
        # Create task configuration
        task_config = TaskConfig(
            task_id="integration_test",
            task_type="code_completion",
            scenario_type="single_turn",
            domain="programming",
            difficulty_level="intermediate",
            language="python",
            requires_code_execution=True
        )
        
        task_data = {
            "description": "Implement a binary search algorithm",
            "code_context": "def binary_search(arr, target):",
            "examples": [
                "binary_search([1,2,3,4,5], 3) should return 2",
                "binary_search([1,2,3,4,5], 6) should return -1"
            ],
            "requirements": ["Handle empty arrays", "Return -1 if not found"]
        }
        
        # Generate prompts for both models
        openai_prompt = engine.generate_prompt(task_config, openai_profile, task_data)
        claude_prompt = engine.generate_prompt(task_config, claude_profile, task_data)
        
        # Verify prompts are different and model-specific
        assert openai_prompt.prompt_text != claude_prompt.prompt_text
        
        # Check that model-specific adaptations are applied
        assert openai_prompt.model_adaptations["style"] == "direct_imperative"
        assert claude_prompt.model_adaptations["style"] == "conversational_polite"
        assert openai_prompt.model_adaptations["format"] == "structured_json"
        assert claude_prompt.model_adaptations["format"] == "markdown_structured"
        
        # Verify both prompts contain task information
        for prompt in [openai_prompt, claude_prompt]:
            assert "binary search" in prompt.prompt_text.lower()
            assert "python" in prompt.prompt_text.lower()
            assert prompt.estimated_tokens > 0
            assert 0 <= prompt.optimization_score <= 1
    
    def test_multi_turn_prompt_generation(self):
        """Test prompt generation for multi-turn scenarios"""
        engine = create_prompt_engine()
        
        model_profile = ModelProfile(
            model_id="gpt-4",
            model_family="openai_gpt",
            context_window=8192,
            supports_system_messages=True,
            supports_function_calling=True,
            supports_multimodal=False,
            preferred_style=PromptStyle.DIRECT_IMPERATIVE,
            preferred_reasoning=ReasoningStyle.STEP_BY_STEP,
            preferred_format=OutputFormat.STRUCTURED_JSON
        )
        
        task_config = TaskConfig(
            task_id="multi_turn_test",
            task_type="code_review",
            scenario_type="multi_turn",
            domain="programming",
            difficulty_level="intermediate",
            requires_multi_turn=True
        )
        
        task_data = {
            "description": "Review and improve this code",
            "conversation_context": "Previous turn: Initial code submission",
            "code_context": "def process_data(data): return data.upper()",
            "turn_number": 2
        }
        
        prompt = engine.generate_prompt(task_config, model_profile, task_data)
        
        # Should use multi-turn template
        assert "multi-turn conversation" in prompt.prompt_text.lower()
        assert "previous turn" in prompt.prompt_text.lower()
        assert prompt.context_mode in [ContextMode.FULL_CONTEXT, ContextMode.DOMAIN_CONTEXT]
    
    def test_domain_specific_prompts(self):
        """Test domain-specific prompt generation"""
        engine = create_prompt_engine()
        
        model_profile = ModelProfile(
            model_id="gpt-4",
            model_family="openai_gpt",
            context_window=16000,
            supports_system_messages=True,
            supports_function_calling=True,
            supports_multimodal=False,
            preferred_style=PromptStyle.TECHNICAL_PRECISE,
            preferred_reasoning=ReasoningStyle.ANALYTICAL_DETAILED,
            preferred_format=OutputFormat.STRUCTURED_JSON
        )
        
        # Test quantitative finance domain
        quant_task_config = TaskConfig(
            task_id="quant_test",
            task_type="strategy_development",
            scenario_type="multi_turn",
            domain="quantitative_finance",
            difficulty_level="expert",
            requires_multi_turn=True
        )
        
        quant_task_data = {
            "description": "Develop a momentum trading strategy",
            "domain_context": "High-frequency trading environment",
            "domain_knowledge": {
                "sharpe_ratio": "Risk-adjusted return measure",
                "alpha": "Excess return over benchmark"
            },
            "best_practices": [
                "Always consider transaction costs",
                "Implement proper risk management"
            ]
        }
        
        quant_prompt = engine.generate_prompt(quant_task_config, model_profile, quant_task_data)
        
        # Should use domain-specific template and context
        # Check that domain context is properly selected
        assert quant_prompt.context_mode == ContextMode.DOMAIN_CONTEXT
        assert "momentum" in quant_prompt.prompt_text.lower()
        
        # Check that domain-specific variables are available in template variables
        assert "domain" in quant_prompt.template_variables
        assert quant_prompt.template_variables["domain"] == "quantitative_finance"
        assert "domain_knowledge" in quant_prompt.template_variables
        assert "best_practices" in quant_prompt.template_variables


if __name__ == "__main__":
    # Run tests
    pytest.main([__file__, "-v"])