"""
Intelligent Prompt Engine for AI Evaluation Engine

This module implements a comprehensive prompt generation system with context-aware
capabilities, model-specific adaptations, and optimization algorithms.

Requirements addressed:
- 4.1: Automatic context mode selection based on model capabilities
- 4.2: Model-specific prompt style adaptation
- 4.3: Comprehensive template system with conditional logic
- 4.4: A/B testing framework for prompt optimization
- 4.6: Prompt effectiveness scoring and ranking
"""

import re
import json
import yaml
import hashlib
import logging
from abc import ABC, abstractmethod
from dataclasses import dataclass, field
from typing import Dict, List, Optional, Any, Union, Tuple, Callable
from enum import Enum
from pathlib import Path
import jinja2
from jinja2 import Environment, BaseLoader, Template
import statistics
from datetime import datetime, timedelta

# Configure logging
logger = logging.getLogger(__name__)


class ContextMode(Enum):
    """Context modes for prompt generation"""
    NO_CONTEXT = "no_context"
    MINIMAL_CONTEXT = "minimal_context"
    FULL_CONTEXT = "full_context"
    DOMAIN_CONTEXT = "domain_context"


class PromptStyle(Enum):
    """Prompt styles for different models"""
    DIRECT_IMPERATIVE = "direct_imperative"
    CONVERSATIONAL_POLITE = "conversational_polite"
    FORMAL_CHINESE = "formal_chinese"
    TECHNICAL_PRECISE = "technical_precise"
    BUSINESS_FOCUSED = "business_focused"
    IMPLEMENTATION_FOCUSED = "implementation_focused"


class ReasoningStyle(Enum):
    """Reasoning styles for different models"""
    STEP_BY_STEP = "step_by_step"
    ANALYTICAL_DETAILED = "analytical_detailed"
    STRUCTURED_LOGICAL = "structured_logical"
    MULTI_MODAL_AWARE = "multi_modal_aware"
    PRACTICAL_ORIENTED = "practical_oriented"
    IMPLEMENTATION_FOCUSED = "implementation_focused"


class OutputFormat(Enum):
    """Output formats for different models"""
    STRUCTURED_JSON = "structured_json"
    MARKDOWN_STRUCTURED = "markdown_structured"
    BILINGUAL_SUPPORT = "bilingual_support"
    STRUCTURED_RESPONSE = "structured_response"
    CODE_BLOCKS = "code_blocks"


@dataclass
class ModelProfile:
    """Profile containing model-specific characteristics"""
    model_id: str
    model_family: str  # openai, anthropic, dashscope, etc.
    context_window: int
    supports_system_messages: bool
    supports_function_calling: bool
    supports_multimodal: bool
    preferred_style: PromptStyle
    preferred_reasoning: ReasoningStyle
    preferred_format: OutputFormat
    token_efficiency_factor: float = 1.0
    attention_pattern_preference: str = "balanced"
    training_data_alignment: Dict[str, float] = field(default_factory=dict)


@dataclass
class TaskConfig:
    """Configuration for a specific evaluation task"""
    task_id: str
    task_type: str
    scenario_type: str
    domain: str
    difficulty_level: str
    language: Optional[str] = None
    requires_code_execution: bool = False
    requires_multi_turn: bool = False
    context_requirements: List[str] = field(default_factory=list)
    success_criteria: Dict[str, float] = field(default_factory=dict)


@dataclass
class TemplateSpec:
    """Specification for creating custom templates"""
    template_id: str
    base_template: str
    variables: Dict[str, Any]
    conditional_blocks: Dict[str, str] = field(default_factory=dict)
    model_adaptations: Dict[str, Dict[str, str]] = field(default_factory=dict)
    validation_rules: List[str] = field(default_factory=list)


@dataclass
class OptimizedPrompt:
    """Result of prompt optimization"""
    prompt_text: str
    context_mode: ContextMode
    estimated_tokens: int
    optimization_score: float
    model_adaptations: Dict[str, str]
    template_variables: Dict[str, Any]
    metadata: Dict[str, Any] = field(default_factory=dict)


@dataclass
class ABTestConfig:
    """Configuration for A/B testing prompts"""
    test_id: str
    test_name: str
    variants: List[Dict[str, Any]]
    sample_size: int
    confidence_level: float = 0.95
    success_metrics: List[str] = field(default_factory=list)
    duration_hours: int = 24
    auto_stop_criteria: Dict[str, float] = field(default_factory=dict)


@dataclass
class ABTestResult:
    """Results of A/B testing"""
    test_id: str
    winner_variant: str
    confidence_score: float
    statistical_significance: bool
    performance_metrics: Dict[str, Dict[str, float]]
    recommendations: List[str]
    test_duration: timedelta
    sample_sizes: Dict[str, int]


class TemplateEngine:
    """Advanced template engine with conditional logic and variable substitution"""
    
    def __init__(self):
        self.env = Environment(
            loader=BaseLoader(),
            autoescape=False,
            trim_blocks=True,
            lstrip_blocks=True
        )
        self._register_custom_filters()
    
    def _register_custom_filters(self):
        """Register custom Jinja2 filters for prompt generation"""
        
        def truncate_context(text: str, max_tokens: int = 1000) -> str:
            """Truncate context to fit within token limits"""
            words = text.split()
            if len(words) <= max_tokens:
                return text
            return ' '.join(words[:max_tokens]) + "..."
        
        def format_code_block(code: str, language: str = "python") -> str:
            """Format code with proper markdown blocks"""
            return f"```{language}\n{code}\n```"
        
        def extract_key_points(text: str, max_points: int = 5) -> List[str]:
            """Extract key points from text"""
            sentences = text.split('.')
            return [s.strip() for s in sentences[:max_points] if s.strip()]
        
        self.env.filters['truncate_context'] = truncate_context
        self.env.filters['format_code_block'] = format_code_block
        self.env.filters['extract_key_points'] = extract_key_points
    
    def render_template(self, template_str: str, variables: Dict[str, Any]) -> str:
        """Render template with variables"""
        try:
            template = self.env.from_string(template_str)
            return template.render(**variables)
        except Exception as e:
            logger.error(f"Template rendering failed: {e}")
            raise ValueError(f"Template rendering error: {e}")
    
    def validate_template(self, template_str: str, required_vars: List[str]) -> bool:
        """Validate template syntax and required variables"""
        try:
            template = self.env.from_string(template_str)
            # Check if all required variables are present
            template_vars = template.environment.parse(template_str).find_all(jinja2.nodes.Name)
            template_var_names = {node.name for node in template_vars}
            
            missing_vars = set(required_vars) - template_var_names
            if missing_vars:
                logger.warning(f"Missing required variables: {missing_vars}")
                return False
            
            return True
        except Exception as e:
            logger.error(f"Template validation failed: {e}")
            return False


class ContextSelector:
    """Intelligent context mode selection based on model capabilities"""
    
    def __init__(self):
        self.context_strategies = {
            ContextMode.NO_CONTEXT: self._no_context_strategy,
            ContextMode.MINIMAL_CONTEXT: self._minimal_context_strategy,
            ContextMode.FULL_CONTEXT: self._full_context_strategy,
            ContextMode.DOMAIN_CONTEXT: self._domain_context_strategy
        }
    
    def select_optimal_context(self, model_profile: ModelProfile, task_config: TaskConfig) -> ContextMode:
        """Select optimal context mode based on model and task characteristics"""
        
        # Consider model context window
        if model_profile.context_window < 4000:
            return ContextMode.MINIMAL_CONTEXT
        
        # Priority for domain-specific contexts
        if task_config.domain in ["quantitative_finance", "cybersecurity"]:
            if model_profile.context_window > 8000:  # Lower threshold for domain context
                return ContextMode.DOMAIN_CONTEXT
            else:
                return ContextMode.FULL_CONTEXT
        
        # Consider task complexity
        if task_config.requires_multi_turn:
            if model_profile.context_window > 16000:
                return ContextMode.DOMAIN_CONTEXT
            else:
                return ContextMode.FULL_CONTEXT
        
        # Consider task type
        if task_config.task_type in ["code_completion", "bug_fix"]:
            return ContextMode.FULL_CONTEXT
        
        # Default strategy
        if model_profile.context_window > 8000:
            return ContextMode.FULL_CONTEXT
        else:
            return ContextMode.MINIMAL_CONTEXT
    
    def _no_context_strategy(self, task_data: Dict[str, Any]) -> Dict[str, Any]:
        """Strategy for no context mode"""
        return {
            "context_information": "",
            "examples": [],
            "background": ""
        }
    
    def _minimal_context_strategy(self, task_data: Dict[str, Any]) -> Dict[str, Any]:
        """Strategy for minimal context mode"""
        return {
            "context_information": task_data.get("brief_context", ""),
            "examples": task_data.get("examples", [])[:1],  # Only one example
            "background": ""
        }
    
    def _full_context_strategy(self, task_data: Dict[str, Any]) -> Dict[str, Any]:
        """Strategy for full context mode"""
        return {
            "context_information": task_data.get("full_context", ""),
            "examples": task_data.get("examples", [])[:3],  # Up to 3 examples
            "background": task_data.get("background", "")
        }
    
    def _domain_context_strategy(self, task_data: Dict[str, Any]) -> Dict[str, Any]:
        """Strategy for domain-specific context mode"""
        return {
            "context_information": task_data.get("domain_context", ""),
            "examples": task_data.get("domain_examples", []),
            "background": task_data.get("domain_background", ""),
            "domain_knowledge": task_data.get("domain_knowledge", {}),
            "best_practices": task_data.get("best_practices", [])
        }


class ModelStyleAdapter:
    """Adapts prompt style for different model families"""
    
    def __init__(self):
        self.style_templates = self._load_style_templates()
    
    def _load_style_templates(self) -> Dict[str, Dict[str, str]]:
        """Load model-specific style templates"""
        return {
            "openai_gpt": {
                "system_prefix": "You are a helpful AI assistant specialized in",
                "task_prefix": "Please",
                "instruction_style": "direct",
                "output_format": "Provide your response in the following format:",
                "reasoning_prompt": "Think step by step:"
            },
            "anthropic_claude": {
                "system_prefix": "I'm Claude, an AI assistant created by Anthropic. I'm here to help with",
                "task_prefix": "I'd be happy to help you",
                "instruction_style": "conversational",
                "output_format": "I'll structure my response as follows:",
                "reasoning_prompt": "Let me think through this carefully:"
            },
            "dashscope_qwen": {
                "system_prefix": "我是通义千问，一个由阿里云开发的AI助手。我专门协助",
                "task_prefix": "请",
                "instruction_style": "formal",
                "output_format": "我将按以下格式提供回答：",
                "reasoning_prompt": "让我逐步分析："
            },
            "google_gemini": {
                "system_prefix": "I'm Gemini, Google's AI model. I can help you with",
                "task_prefix": "I'll assist you to",
                "instruction_style": "technical",
                "output_format": "Here's my structured response:",
                "reasoning_prompt": "Let me analyze this systematically:"
            },
            "cohere_command": {
                "system_prefix": "I'm Command, Cohere's language model designed for",
                "task_prefix": "I can help you",
                "instruction_style": "business",
                "output_format": "My response will include:",
                "reasoning_prompt": "Here's my analysis:"
            },
            "huggingface_local": {
                "system_prefix": "I am an AI assistant focused on",
                "task_prefix": "I will",
                "instruction_style": "technical",
                "output_format": "Response format:",
                "reasoning_prompt": "Implementation approach:"
            }
        }
    
    def adapt_prompt_style(self, base_prompt: str, model_profile: ModelProfile) -> str:
        """Adapt prompt style for specific model"""
        
        model_family = model_profile.model_family.lower()
        if model_family not in self.style_templates:
            model_family = "huggingface_local"  # Default fallback
        
        style_config = self.style_templates[model_family]
        
        # Apply style adaptations
        adapted_prompt = self._apply_style_transformations(
            base_prompt, style_config, model_profile
        )
        
        return adapted_prompt
    
    def _apply_style_transformations(self, prompt: str, style_config: Dict[str, str], 
                                   model_profile: ModelProfile) -> str:
        """Apply style transformations to prompt"""
        
        # Replace style markers with model-specific versions
        transformations = {
            "{{SYSTEM_PREFIX}}": style_config["system_prefix"],
            "{{TASK_PREFIX}}": style_config["task_prefix"],
            "{{OUTPUT_FORMAT}}": style_config["output_format"],
            "{{REASONING_PROMPT}}": style_config["reasoning_prompt"]
        }
        
        adapted_prompt = prompt
        for marker, replacement in transformations.items():
            adapted_prompt = adapted_prompt.replace(marker, replacement)
        
        # Apply model-specific formatting
        if model_profile.preferred_format == OutputFormat.STRUCTURED_JSON:
            adapted_prompt += "\n\nPlease provide your response in valid JSON format."
        elif model_profile.preferred_format == OutputFormat.MARKDOWN_STRUCTURED:
            adapted_prompt += "\n\nPlease structure your response using markdown formatting."
        elif model_profile.preferred_format == OutputFormat.CODE_BLOCKS:
            adapted_prompt += "\n\nPlease use code blocks for any code examples."
        
        return adapted_prompt


class PromptOptimizer:
    """Optimizes prompts for token efficiency and attention patterns"""
    
    def __init__(self):
        self.optimization_strategies = {
            "token_efficiency": self._optimize_token_efficiency,
            "attention_patterns": self._optimize_attention_patterns,
            "training_alignment": self._optimize_training_alignment
        }
    
    def optimize_prompt(self, prompt: str, model_profile: ModelProfile, 
                       task_config: TaskConfig) -> Tuple[str, float]:
        """Optimize prompt and return optimized version with score"""
        
        optimized_prompt = prompt
        optimization_score = 0.0
        
        # Apply optimization strategies
        for strategy_name, strategy_func in self.optimization_strategies.items():
            optimized_prompt, score_delta = strategy_func(
                optimized_prompt, model_profile, task_config
            )
            optimization_score += score_delta
        
        # Normalize score
        optimization_score = min(1.0, max(0.0, optimization_score / len(self.optimization_strategies)))
        
        return optimized_prompt, optimization_score
    
    def _optimize_token_efficiency(self, prompt: str, model_profile: ModelProfile, 
                                 task_config: TaskConfig) -> Tuple[str, float]:
        """Optimize for token efficiency"""
        
        # Remove redundant phrases
        redundant_patterns = [
            r'\b(please|kindly)\s+',
            r'\b(very|really|quite)\s+',
            r'\s+and\s+also\s+',
            r'\s{2,}'  # Multiple spaces
        ]
        
        optimized = prompt
        original_length = len(prompt.split())
        
        for pattern in redundant_patterns:
            optimized = re.sub(pattern, ' ', optimized, flags=re.IGNORECASE)
        
        # Clean up extra whitespace
        optimized = ' '.join(optimized.split())
        
        new_length = len(optimized.split())
        efficiency_gain = (original_length - new_length) / original_length if original_length > 0 else 0
        
        return optimized, efficiency_gain * model_profile.token_efficiency_factor
    
    def _optimize_attention_patterns(self, prompt: str, model_profile: ModelProfile, 
                                   task_config: TaskConfig) -> Tuple[str, float]:
        """Optimize for attention patterns"""
        
        # Move important information to the beginning and end
        if "IMPORTANT:" not in prompt and task_config.task_type in ["bug_fix", "security"]:
            prompt = "IMPORTANT: " + prompt
        
        # Add structure markers for better attention
        if model_profile.attention_pattern_preference == "structured":
            # Add numbered sections if not present
            if not re.search(r'\d+\.', prompt):
                sections = prompt.split('\n\n')
                if len(sections) > 1:
                    numbered_sections = [f"{i+1}. {section}" for i, section in enumerate(sections)]
                    prompt = '\n\n'.join(numbered_sections)
        
        return prompt, 0.1  # Small improvement score
    
    def _optimize_training_alignment(self, prompt: str, model_profile: ModelProfile, 
                                   task_config: TaskConfig) -> Tuple[str, float]:
        """Optimize for training data alignment"""
        
        alignment_score = 0.0
        
        # Check alignment with model's training data patterns
        domain_alignment = model_profile.training_data_alignment.get(task_config.domain, 0.5)
        
        # Adjust prompt based on alignment
        if domain_alignment < 0.3:  # Low alignment
            # Add more context and examples
            if "For example:" not in prompt:
                prompt += "\n\nFor example, consider similar scenarios in this domain."
            alignment_score = 0.2
        elif domain_alignment > 0.7:  # High alignment
            # Can be more concise
            alignment_score = 0.3
        
        return prompt, alignment_score


class ABTestManager:
    """Manages A/B testing for prompt optimization"""
    
    def __init__(self):
        self.active_tests: Dict[str, ABTestConfig] = {}
        self.test_results: Dict[str, List[Dict[str, Any]]] = {}
        self.completed_tests: Dict[str, ABTestResult] = {}
    
    def create_ab_test(self, config: ABTestConfig) -> str:
        """Create a new A/B test"""
        
        # Validate configuration
        if len(config.variants) < 2:
            raise ValueError("A/B test requires at least 2 variants")
        
        if config.sample_size < 30:
            raise ValueError("Sample size should be at least 30 for statistical significance")
        
        # Store test configuration
        self.active_tests[config.test_id] = config
        self.test_results[config.test_id] = []
        
        logger.info(f"Created A/B test: {config.test_id} with {len(config.variants)} variants")
        return config.test_id
    
    def record_test_result(self, test_id: str, variant_id: str, 
                          metrics: Dict[str, float]) -> None:
        """Record result for a test variant"""
        
        if test_id not in self.active_tests:
            raise ValueError(f"Test {test_id} not found")
        
        result = {
            "variant_id": variant_id,
            "metrics": metrics,
            "timestamp": datetime.now()
        }
        
        self.test_results[test_id].append(result)
    
    def analyze_test_results(self, test_id: str) -> Optional[ABTestResult]:
        """Analyze test results and determine winner"""
        
        if test_id not in self.active_tests:
            raise ValueError(f"Test {test_id} not found")
        
        config = self.active_tests[test_id]
        results = self.test_results[test_id]
        
        if len(results) < config.sample_size:
            logger.info(f"Test {test_id} needs more samples: {len(results)}/{config.sample_size}")
            return None
        
        # Group results by variant
        variant_results = {}
        for result in results:
            variant_id = result["variant_id"]
            if variant_id not in variant_results:
                variant_results[variant_id] = []
            variant_results[variant_id].append(result["metrics"])
        
        # Calculate statistical significance
        winner_variant, confidence_score, is_significant = self._calculate_statistical_significance(
            variant_results, config.confidence_level
        )
        
        # Generate recommendations
        recommendations = self._generate_recommendations(variant_results, winner_variant)
        
        # Create result object
        test_result = ABTestResult(
            test_id=test_id,
            winner_variant=winner_variant,
            confidence_score=confidence_score,
            statistical_significance=is_significant,
            performance_metrics=self._calculate_performance_metrics(variant_results),
            recommendations=recommendations,
            test_duration=datetime.now() - min(r["timestamp"] for r in results),
            sample_sizes={v: len(variant_results[v]) for v in variant_results}
        )
        
        # Store completed test
        self.completed_tests[test_id] = test_result
        
        # Clean up active test
        if is_significant:
            del self.active_tests[test_id]
        
        return test_result
    
    def _calculate_statistical_significance(self, variant_results: Dict[str, List[Dict[str, float]]], 
                                          confidence_level: float) -> Tuple[str, float, bool]:
        """Calculate statistical significance using t-test"""
        
        # For simplicity, using the first metric for comparison
        # In practice, you'd want to use the primary success metric
        
        variants = list(variant_results.keys())
        if len(variants) < 2:
            return variants[0], 0.0, False
        
        # Get primary metric values for each variant
        primary_metric = "accuracy"  # Default primary metric
        
        variant_scores = {}
        for variant_id, results in variant_results.items():
            scores = [r.get(primary_metric, 0.0) for r in results]
            variant_scores[variant_id] = scores
        
        # Find best performing variant
        variant_means = {v: statistics.mean(scores) for v, scores in variant_scores.items()}
        winner_variant = max(variant_means, key=variant_means.get)
        
        # Calculate confidence (simplified)
        winner_scores = variant_scores[winner_variant]
        if len(winner_scores) > 1:
            winner_std = statistics.stdev(winner_scores)
            confidence_score = min(0.99, max(0.5, 1.0 - (winner_std / variant_means[winner_variant])))
        else:
            confidence_score = 0.5
        
        is_significant = confidence_score >= confidence_level
        
        return winner_variant, confidence_score, is_significant
    
    def _calculate_performance_metrics(self, variant_results: Dict[str, List[Dict[str, float]]]) -> Dict[str, Dict[str, float]]:
        """Calculate performance metrics for each variant"""
        
        performance_metrics = {}
        
        for variant_id, results in variant_results.items():
            if not results:
                continue
            
            # Aggregate metrics across all results for this variant
            all_metrics = {}
            for result in results:
                for metric_name, value in result.items():
                    if metric_name not in all_metrics:
                        all_metrics[metric_name] = []
                    all_metrics[metric_name].append(value)
            
            # Calculate statistics for each metric
            variant_metrics = {}
            for metric_name, values in all_metrics.items():
                variant_metrics[metric_name] = {
                    "mean": statistics.mean(values),
                    "median": statistics.median(values),
                    "std": statistics.stdev(values) if len(values) > 1 else 0.0,
                    "min": min(values),
                    "max": max(values),
                    "count": len(values)
                }
            
            performance_metrics[variant_id] = variant_metrics
        
        return performance_metrics
    
    def _generate_recommendations(self, variant_results: Dict[str, List[Dict[str, float]]], 
                                winner_variant: str) -> List[str]:
        """Generate recommendations based on test results"""
        
        recommendations = []
        
        # Basic recommendations
        recommendations.append(f"Use variant '{winner_variant}' as it shows the best performance")
        
        # Analyze performance patterns
        if len(variant_results) > 2:
            recommendations.append("Consider running follow-up tests with variations of the winning prompt")
        
        # Check for close results
        variant_means = {}
        for variant_id, results in variant_results.items():
            if results:
                primary_scores = [r.get("accuracy", 0.0) for r in results]
                variant_means[variant_id] = statistics.mean(primary_scores)
        
        if len(variant_means) > 1:
            sorted_variants = sorted(variant_means.items(), key=lambda x: x[1], reverse=True)
            if len(sorted_variants) > 1 and abs(sorted_variants[0][1] - sorted_variants[1][1]) < 0.05:
                recommendations.append("Results are close - consider testing with larger sample size")
        
        return recommendations


class PromptEngine:
    """Main prompt engine class that orchestrates all prompt generation capabilities"""
    
    def __init__(self, template_dir: Optional[Path] = None):
        self.template_engine = TemplateEngine()
        self.context_selector = ContextSelector()
        self.style_adapter = ModelStyleAdapter()
        self.optimizer = PromptOptimizer()
        self.ab_test_manager = ABTestManager()
        
        # Load base templates
        self.base_templates = self._load_base_templates(template_dir)
        
        # Cache for optimized prompts
        self.prompt_cache: Dict[str, OptimizedPrompt] = {}
    
    def _load_base_templates(self, template_dir: Optional[Path]) -> Dict[str, str]:
        """Load base prompt templates"""
        
        # Default templates if no directory provided
        default_templates = {
            "single_turn_base": """{{SYSTEM_PREFIX}} {{task_description}}.

Context: {{context_information}}

{% if examples %}
Examples:
{% for example in examples %}
{{ loop.index }}. {{ example }}
{% endfor %}
{% endif %}

Task: {{task_description}}

{{REASONING_PROMPT}}

{{OUTPUT_FORMAT}}
""",
            
            "multi_turn_base": """{{SYSTEM_PREFIX}} {{task_description}}.

This is a multi-turn conversation. Context from previous turns:
{{conversation_context}}

Current turn context: {{context_information}}

{% if examples %}
Examples of similar interactions:
{% for example in examples %}
{{ loop.index }}. {{ example }}
{% endfor %}
{% endif %}

Current task: {{task_description}}

{{REASONING_PROMPT}}

{{OUTPUT_FORMAT}}
""",
            
            "code_task_base": """{{SYSTEM_PREFIX}} {{task_description}}.

Programming Context:
- Language: {{language}}
- Task Type: {{task_type}}
{% if requirements %}
- Requirements: {{requirements}}
{% endif %}

{{context_information}}

{% if code_examples %}
Code Examples:
{% for example in code_examples %}
```{{language}}
{{ example }}
```
{% endfor %}
{% endif %}

Task: {{task_description}}

{{REASONING_PROMPT}}

Please provide your solution in the following format:
```{{language}}
# Your code here
```

Explanation: [Brief explanation of your approach]
""",
            
            "domain_specific_base": """{{SYSTEM_PREFIX}} {{task_description}} in the {{domain}} domain.

Domain Context: {{domain_context}}

{% if domain_knowledge %}
Relevant Domain Knowledge:
{% for key, value in domain_knowledge.items() %}
- {{key}}: {{value}}
{% endfor %}
{% endif %}

{% if best_practices %}
Best Practices:
{% for practice in best_practices %}
- {{ practice }}
{% endfor %}
{% endif %}

{{context_information}}

Task: {{task_description}}

{{REASONING_PROMPT}}

{{OUTPUT_FORMAT}}
"""
        }
        
        if template_dir and template_dir.exists():
            # Load templates from directory
            loaded_templates = {}
            for template_file in template_dir.glob("*.txt"):
                template_name = template_file.stem
                loaded_templates[template_name] = template_file.read_text()
            return loaded_templates
        
        return default_templates
    
    def generate_prompt(self, task_config: TaskConfig, model_profile: ModelProfile, 
                       task_data: Dict[str, Any] = None) -> OptimizedPrompt:
        """Generate optimized prompt for given task and model"""
        
        # Create cache key
        cache_key = self._create_cache_key(task_config, model_profile, task_data)
        
        # Check cache
        if cache_key in self.prompt_cache:
            return self.prompt_cache[cache_key]
        
        # Select optimal context mode
        context_mode = self.select_context_mode(model_profile, task_config)
        
        # Prepare context data
        context_data = self.context_selector.context_strategies[context_mode](task_data or {})
        
        # Select appropriate base template
        base_template = self._select_base_template(task_config)
        
        # Prepare template variables
        template_variables = self._prepare_template_variables(
            task_config, context_data, task_data or {}
        )
        
        # Render base prompt
        base_prompt = self.template_engine.render_template(base_template, template_variables)
        
        # Adapt prompt style for model
        styled_prompt = self.style_adapter.adapt_prompt_style(base_prompt, model_profile)
        
        # Optimize prompt
        optimized_prompt_text, optimization_score = self.optimizer.optimize_prompt(
            styled_prompt, model_profile, task_config
        )
        
        # Estimate token count (rough approximation)
        estimated_tokens = len(optimized_prompt_text.split()) * 1.3  # Rough token estimation
        
        # Create optimized prompt object
        optimized_prompt = OptimizedPrompt(
            prompt_text=optimized_prompt_text,
            context_mode=context_mode,
            estimated_tokens=int(estimated_tokens),
            optimization_score=optimization_score,
            model_adaptations={
                "style": model_profile.preferred_style.value,
                "reasoning": model_profile.preferred_reasoning.value,
                "format": model_profile.preferred_format.value
            },
            template_variables=template_variables,
            metadata={
                "task_id": task_config.task_id,
                "model_id": model_profile.model_id,
                "generation_timestamp": datetime.now().isoformat()
            }
        )
        
        # Cache the result
        self.prompt_cache[cache_key] = optimized_prompt
        
        return optimized_prompt
    
    def select_context_mode(self, model_profile: ModelProfile, task_config: TaskConfig) -> ContextMode:
        """Select optimal context mode based on model capabilities"""
        return self.context_selector.select_optimal_context(model_profile, task_config)
    
    def adapt_prompt_style(self, model_profile: ModelProfile) -> PromptStyle:
        """Adapt prompt style for specific model"""
        return model_profile.preferred_style
    
    def run_ab_test(self, test_config: ABTestConfig) -> str:
        """Create and run A/B test for prompt optimization"""
        return self.ab_test_manager.create_ab_test(test_config)
    
    def record_ab_test_result(self, test_id: str, variant_id: str, 
                             metrics: Dict[str, float]) -> None:
        """Record A/B test result"""
        self.ab_test_manager.record_test_result(test_id, variant_id, metrics)
    
    def analyze_ab_test(self, test_id: str) -> Optional[ABTestResult]:
        """Analyze A/B test results"""
        return self.ab_test_manager.analyze_test_results(test_id)
    
    def create_custom_template(self, template_spec: TemplateSpec) -> str:
        """Create custom template from specification"""
        
        # Validate template
        if not self.template_engine.validate_template(
            template_spec.base_template, 
            list(template_spec.variables.keys())
        ):
            raise ValueError("Invalid template specification")
        
        # Store custom template
        self.base_templates[template_spec.template_id] = template_spec.base_template
        
        logger.info(f"Created custom template: {template_spec.template_id}")
        return template_spec.template_id
    
    def _create_cache_key(self, task_config: TaskConfig, model_profile: ModelProfile, 
                         task_data: Optional[Dict[str, Any]]) -> str:
        """Create cache key for prompt"""
        
        key_data = {
            "task_id": task_config.task_id,
            "model_id": model_profile.model_id,
            "task_type": task_config.task_type,
            "domain": task_config.domain
        }
        
        if task_data:
            # Include hash of task data for uniqueness
            task_data_str = json.dumps(task_data, sort_keys=True)
            key_data["data_hash"] = hashlib.md5(task_data_str.encode()).hexdigest()[:8]
        
        key_str = json.dumps(key_data, sort_keys=True)
        return hashlib.md5(key_str.encode()).hexdigest()
    
    def _select_base_template(self, task_config: TaskConfig) -> str:
        """Select appropriate base template for task"""
        
        # Priority order: domain-specific > multi-turn > code > single-turn
        if task_config.domain in ["quantitative_finance", "cybersecurity"]:
            return self.base_templates["domain_specific_base"]
        elif task_config.requires_multi_turn:
            return self.base_templates["multi_turn_base"]
        elif task_config.requires_code_execution:
            return self.base_templates["code_task_base"]
        else:
            return self.base_templates["single_turn_base"]
    
    def _prepare_template_variables(self, task_config: TaskConfig, 
                                  context_data: Dict[str, Any], 
                                  task_data: Dict[str, Any]) -> Dict[str, Any]:
        """Prepare variables for template rendering"""
        
        variables = {
            "task_description": task_data.get("description", "Complete the given task"),
            "task_type": task_config.task_type,
            "domain": task_config.domain,
            "language": task_config.language or "python",
            **context_data,
            **task_data
        }
        
        return variables
    
    def get_prompt_effectiveness_score(self, prompt_id: str, 
                                     performance_metrics: Dict[str, float]) -> float:
        """Calculate prompt effectiveness score"""
        
        # Weighted scoring based on different metrics
        weights = {
            "accuracy": 0.4,
            "efficiency": 0.2,
            "clarity": 0.2,
            "completeness": 0.2
        }
        
        total_score = 0.0
        total_weight = 0.0
        
        for metric, value in performance_metrics.items():
            if metric in weights:
                total_score += value * weights[metric]
                total_weight += weights[metric]
        
        if total_weight > 0:
            return total_score / total_weight
        else:
            return 0.0
    
    def clear_cache(self) -> None:
        """Clear prompt cache"""
        self.prompt_cache.clear()
        logger.info("Prompt cache cleared")
    
    def get_cache_stats(self) -> Dict[str, Any]:
        """Get cache statistics"""
        return {
            "cache_size": len(self.prompt_cache),
            "active_ab_tests": len(self.ab_test_manager.active_tests),
            "completed_ab_tests": len(self.ab_test_manager.completed_tests),
            "available_templates": len(self.base_templates)
        }


# Factory function for easy instantiation
def create_prompt_engine(template_dir: Optional[Path] = None) -> PromptEngine:
    """Create and configure a PromptEngine instance"""
    return PromptEngine(template_dir)


# Example usage and testing
if __name__ == "__main__":
    # Example usage
    engine = create_prompt_engine()
    
    # Create example model profile
    model_profile = ModelProfile(
        model_id="gpt-4",
        model_family="openai",
        context_window=8192,
        supports_system_messages=True,
        supports_function_calling=True,
        supports_multimodal=False,
        preferred_style=PromptStyle.DIRECT_IMPERATIVE,
        preferred_reasoning=ReasoningStyle.STEP_BY_STEP,
        preferred_format=OutputFormat.STRUCTURED_JSON,
        token_efficiency_factor=0.9
    )
    
    # Create example task config
    task_config = TaskConfig(
        task_id="code_completion_001",
        task_type="code_completion",
        scenario_type="single_turn",
        domain="programming",
        difficulty_level="intermediate",
        language="python",
        requires_code_execution=True
    )
    
    # Generate optimized prompt
    task_data = {
        "description": "Complete the following Python function",
        "code_context": "def fibonacci(n):\n    # Complete this function",
        "examples": ["fibonacci(5) should return 5", "fibonacci(10) should return 55"]
    }
    
    optimized_prompt = engine.generate_prompt(task_config, model_profile, task_data)
    
    print("Generated Prompt:")
    print("=" * 50)
    print(optimized_prompt.prompt_text)
    print("=" * 50)
    print(f"Context Mode: {optimized_prompt.context_mode}")
    print(f"Estimated Tokens: {optimized_prompt.estimated_tokens}")
    print(f"Optimization Score: {optimized_prompt.optimization_score:.3f}")