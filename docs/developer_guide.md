# Developer Guide: Extending the AI Evaluation Engine

## Overview

This guide provides comprehensive documentation for developers who want to extend the AI Evaluation Engine by adding new tasks, model adapters, metrics, or other components. The system is built with extensibility in mind, following plugin architecture patterns.

## Architecture Overview

### Core Components

```
┌─────────────────────────────────────────────────────────────────┐
│                    Extension Points                             │
├─────────────────────────────────────────────────────────────────┤
│  Custom Tasks   │  Model Adapters │  Custom Metrics │ Plugins  │
├─────────────────────────────────────────────────────────────────┤
│                    Core Engine Layer                            │
│    Task Registry │  Model Manager  │ Metrics Engine │ Executor  │
├─────────────────────────────────────────────────────────────────┤
│                    lm-evaluation-harness                        │
│     Base Classes │   Interfaces    │   Utilities     │ Registry │
└─────────────────────────────────────────────────────────────────┘
```

### Extension Points

1. **Task Extensions**: Add new evaluation scenarios
2. **Model Adapters**: Support new model backends
3. **Custom Metrics**: Implement domain-specific metrics
4. **Plugins**: Add new functionality modules
5. **Data Loaders**: Support new data formats
6. **Execution Environments**: Add new runtime environments

## Adding New Tasks

### Single-Turn Task Implementation

#### Step 1: Create Task Directory Structure

```bash
mkdir -p lm_eval/tasks/single_turn_scenarios/my_new_task
cd lm_eval/tasks/single_turn_scenarios/my_new_task
```

Create the following files:
- `__init__.py` - Task registration
- `my_new_task.py` - Task implementation
- `problems.jsonl` - Dataset
- `config.yml` - Task configuration

#### Step 2: Implement Task Class

```python
# lm_eval/tasks/single_turn_scenarios/my_new_task/my_new_task.py

from lm_eval.api.task import Task
from lm_eval.api.registry import register_task
from evaluation_engine.core.extended_tasks import AdvancedTask
from evaluation_engine.core.metrics_engine import MetricsEngine
import json

@register_task("single_turn_scenarios_my_new_task")
class MyNewTask(AdvancedTask):
    """
    Custom task for evaluating [specific capability].
    
    This task assesses the model's ability to [describe capability].
    """
    
    VERSION = 1.0
    DATASET_PATH = "problems.jsonl"
    DATASET_NAME = "my_new_task"
    
    def __init__(self, config=None):
        super().__init__(config)
        self.metrics_engine = MetricsEngine()
        
    def has_training_docs(self):
        return False
        
    def has_validation_docs(self):
        return False
        
    def has_test_docs(self):
        return True
        
    def test_docs(self):
        """Load test documents from dataset."""
        return self.dataset["test"]
        
    def doc_to_text(self, doc):
        """Convert document to input text for the model."""
        # Extract the prompt/question from the document
        context = doc.get("context", "")
        question = doc["question"]
        
        if context:
            return f"Context: {context}\n\nQuestion: {question}\n\nAnswer:"
        else:
            return f"Question: {question}\n\nAnswer:"
            
    def doc_to_target(self, doc):
        """Extract the expected answer/target from document."""
        return doc["expected_answer"]
        
    def construct_requests(self, doc, ctx, **kwargs):
        """Construct the request for the model."""
        prompt = self.doc_to_text(doc)
        return [
            {
                "request_type": "generate_until",
                "arguments": {
                    "prompt": prompt,
                    "until": ["\n\n", "Question:", "Context:"],
                    "max_tokens": 512,
                    "temperature": 0.0
                }
            }
        ]
        
    def process_results(self, doc, results):
        """Process model results and calculate metrics."""
        model_output = results[0].strip()
        expected_answer = self.doc_to_target(doc)
        
        # Calculate various metrics
        metrics = {}
        
        # Exact match
        metrics["exact_match"] = float(
            model_output.lower().strip() == expected_answer.lower().strip()
        )
        
        # Custom domain-specific metrics
        metrics.update(self._calculate_custom_metrics(doc, model_output, expected_answer))
        
        return {
            "exact_match": metrics["exact_match"],
            "custom_score": metrics.get("custom_score", 0.0),
            "model_output": model_output,
            "expected_answer": expected_answer
        }
        
    def _calculate_custom_metrics(self, doc, model_output, expected_answer):
        """Calculate domain-specific metrics."""
        metrics = {}
        
        # Example: Calculate semantic similarity
        if hasattr(self.metrics_engine, 'calculate_semantic_similarity'):
            metrics["semantic_similarity"] = self.metrics_engine.calculate_semantic_similarity(
                model_output, expected_answer
            )
            
        # Example: Calculate task-specific quality score
        metrics["custom_score"] = self._calculate_quality_score(doc, model_output)
        
        return metrics
        
    def _calculate_quality_score(self, doc, model_output):
        """Calculate a custom quality score for this task."""
        # Implement your custom scoring logic here
        score = 0.0
        
        # Example scoring criteria
        if len(model_output.strip()) > 0:
            score += 0.2  # Non-empty response
            
        if any(keyword in model_output.lower() for keyword in doc.get("required_keywords", [])):
            score += 0.3  # Contains required keywords
            
        # Add more scoring criteria as needed
        
        return min(score, 1.0)
        
    def aggregation(self):
        """Define how to aggregate results across all examples."""
        return {
            "exact_match": ["mean"],
            "custom_score": ["mean", "std"],
            "semantic_similarity": ["mean"]
        }
        
    def higher_is_better(self):
        """Define which metrics are better when higher."""
        return {
            "exact_match": True,
            "custom_score": True,
            "semantic_similarity": True
        }
```

#### Step 3: Create Dataset

```jsonl
# lm_eval/tasks/single_turn_scenarios/my_new_task/problems.jsonl
{"question": "What is the capital of France?", "expected_answer": "Paris", "context": "", "required_keywords": ["paris", "france"], "difficulty": "easy"}
{"question": "Explain the concept of recursion in programming.", "expected_answer": "Recursion is a programming technique where a function calls itself to solve smaller instances of the same problem.", "context": "Programming concepts", "required_keywords": ["function", "calls", "itself"], "difficulty": "medium"}
{"question": "Calculate the derivative of x^2 + 3x + 2", "expected_answer": "2x + 3", "context": "Calculus", "required_keywords": ["derivative", "2x", "3"], "difficulty": "medium"}
```

#### Step 4: Task Configuration

```yaml
# lm_eval/tasks/single_turn_scenarios/my_new_task/config.yml
task_name: "my_new_task"
task_type: "single_turn"
description: "Evaluate model's ability to [describe capability]"
version: 1.0

dataset:
  path: "problems.jsonl"
  format: "jsonl"
  size: 100

metrics:
  primary:
    - "exact_match"
    - "custom_score"
  secondary:
    - "semantic_similarity"

evaluation_config:
  context_modes: ["no_context", "minimal_context", "full_context"]
  languages: ["en"]
  difficulty_levels: ["easy", "medium", "hard"]
  
prompt_templates:
  default: |
    {context}
    
    Question: {question}
    
    Answer:
  
  with_examples: |
    Here are some examples:
    {examples}
    
    {context}
    
    Question: {question}
    
    Answer:
```

#### Step 5: Register Task

```python
# lm_eval/tasks/single_turn_scenarios/my_new_task/__init__.py

from .my_new_task import MyNewTask

# Task is automatically registered via the @register_task decorator
```

### Multi-Turn Task Implementation

#### Step 1: Create Multi-Turn Task Structure

```python
# lm_eval/tasks/multi_turn_scenarios/my_conversation_task/my_conversation_task.py

from evaluation_engine.core.extended_tasks import MultiTurnTask
from lm_eval.api.registry import register_task
import yaml

@register_task("multi_turn_scenarios_my_conversation_task")
class MyConversationTask(MultiTurnTask):
    """
    Multi-turn conversation task for [specific domain].
    """
    
    VERSION = 1.0
    DATASET_PATH = "scenarios.jsonl"
    TURN_CONFIG_PATH = "turn_configs.yml"
    
    def __init__(self, config=None):
        super().__init__(config)
        self.load_turn_configurations()
        
    def load_turn_configurations(self):
        """Load turn-specific configurations."""
        with open(self.TURN_CONFIG_PATH, 'r') as f:
            self.turn_configs = yaml.safe_load(f)
            
    def test_docs(self):
        """Load conversation scenarios."""
        return self.dataset["test"]
        
    def get_conversation_flow(self, doc):
        """Define the conversation flow for this scenario."""
        scenario_type = doc.get("scenario_type", "default")
        return self.turn_configs.get(scenario_type, self.turn_configs["default"])
        
    def process_turn(self, doc, turn_config, conversation_history, turn_index):
        """Process a single turn in the conversation."""
        
        # Build context from conversation history
        context = self.build_conversation_context(conversation_history)
        
        # Generate prompt for this turn
        prompt = self.generate_turn_prompt(doc, turn_config, context, turn_index)
        
        # Get model response
        response = self.get_model_response(prompt, turn_config)
        
        # Evaluate turn
        turn_metrics = self.evaluate_turn(doc, turn_config, response, conversation_history)
        
        return {
            "turn_index": turn_index,
            "prompt": prompt,
            "response": response,
            "metrics": turn_metrics
        }
        
    def generate_turn_prompt(self, doc, turn_config, context, turn_index):
        """Generate prompt for a specific turn."""
        template = turn_config.get("prompt_template", "")
        
        # Fill in template variables
        prompt = template.format(
            context=context,
            scenario=doc.get("scenario_description", ""),
            turn_index=turn_index,
            **doc.get("variables", {})
        )
        
        return prompt
        
    def evaluate_turn(self, doc, turn_config, response, conversation_history):
        """Evaluate a single turn's response."""
        metrics = {}
        
        # Standard turn metrics
        metrics["response_length"] = len(response.split())
        metrics["relevance_score"] = self.calculate_relevance(response, doc)
        
        # Turn-specific metrics
        for metric_name in turn_config.get("evaluation_metrics", []):
            if hasattr(self, f"calculate_{metric_name}"):
                metrics[metric_name] = getattr(self, f"calculate_{metric_name}")(
                    response, doc, conversation_history
                )
                
        return metrics
        
    def evaluate_conversation(self, doc, conversation_turns):
        """Evaluate the entire conversation."""
        conversation_metrics = {}
        
        # Aggregate turn metrics
        turn_metrics = [turn["metrics"] for turn in conversation_turns]
        conversation_metrics.update(self.aggregate_turn_metrics(turn_metrics))
        
        # Conversation-level metrics
        conversation_metrics["context_retention"] = self.calculate_context_retention(
            conversation_turns
        )
        conversation_metrics["goal_achievement"] = self.calculate_goal_achievement(
            doc, conversation_turns
        )
        conversation_metrics["coherence_score"] = self.calculate_coherence(
            conversation_turns
        )
        
        return conversation_metrics
        
    def calculate_context_retention(self, conversation_turns):
        """Calculate how well context is retained across turns."""
        # Implement context retention calculation
        return 0.8  # Placeholder
        
    def calculate_goal_achievement(self, doc, conversation_turns):
        """Calculate how well the conversation achieved its goals."""
        # Implement goal achievement calculation
        return 0.7  # Placeholder
        
    def calculate_coherence(self, conversation_turns):
        """Calculate conversation coherence score."""
        # Implement coherence calculation
        return 0.9  # Placeholder
```

#### Step 2: Turn Configuration

```yaml
# lm_eval/tasks/multi_turn_scenarios/my_conversation_task/turn_configs.yml

default:
  max_turns: 5
  conversation_timeout: 300
  
  turns:
    - turn_id: "introduction"
      role: "assistant"
      prompt_template: |
        Welcome to {scenario}. I'm here to help you with {task_description}.
        
        Let's start by understanding your specific needs. What would you like to focus on?
      
      evaluation_metrics:
        - "engagement_quality"
        - "clarity_score"
      
      config:
        temperature: 0.7
        max_tokens: 200
        
    - turn_id: "analysis"
      role: "assistant"
      depends_on: ["introduction"]
      prompt_template: |
        Based on your input: "{user_input}"
        
        Let me analyze this and provide recommendations...
      
      evaluation_metrics:
        - "analysis_depth"
        - "recommendation_quality"
      
      config:
        temperature: 0.5
        max_tokens: 500
        
    - turn_id: "refinement"
      role: "assistant"
      depends_on: ["analysis"]
      optional: true
      prompt_template: |
        I see you have additional questions about {topic}.
        
        Let me provide more detailed information...
      
      evaluation_metrics:
        - "detail_level"
        - "accuracy"

specialized_scenario:
  max_turns: 8
  conversation_timeout: 600
  
  turns:
    - turn_id: "deep_analysis"
      role: "assistant"
      prompt_template: |
        For this specialized scenario, I need to conduct a thorough analysis...
      
      evaluation_metrics:
        - "technical_accuracy"
        - "depth_of_analysis"
```

## Adding Model Adapters

### Custom Model Adapter Implementation

```python
# evaluation_engine/core/custom_model_adapter.py

from evaluation_engine.core.model_adapters import ModelAdapter
from evaluation_engine.core.advanced_model_config import ModelConfiguration
import requests
import json

class CustomModelAdapter(ModelAdapter):
    """
    Adapter for custom model backend.
    """
    
    def __init__(self, config: ModelConfiguration):
        super().__init__(config)
        self.api_endpoint = config.get("api_endpoint")
        self.api_key = config.get("api_key")
        self.model_name = config.get("model_name")
        
    def get_model_info(self):
        """Return model information."""
        return {
            "model_id": f"custom/{self.model_name}",
            "model_type": "custom",
            "provider": "custom_provider",
            "capabilities": ["text_generation", "code_generation"],
            "context_length": 4096,
            "supports_streaming": True
        }
        
    def generate_response(self, prompt: str, config: dict = None) -> dict:
        """Generate response from the custom model."""
        
        # Prepare request
        request_data = {
            "model": self.model_name,
            "prompt": prompt,
            "max_tokens": config.get("max_tokens", 1024),
            "temperature": config.get("temperature", 0.7),
            "top_p": config.get("top_p", 1.0),
            "stop": config.get("stop", [])
        }
        
        headers = {
            "Authorization": f"Bearer {self.api_key}",
            "Content-Type": "application/json"
        }
        
        try:
            # Make API request
            response = requests.post(
                f"{self.api_endpoint}/generate",
                headers=headers,
                json=request_data,
                timeout=30
            )
            response.raise_for_status()
            
            result = response.json()
            
            return {
                "text": result["choices"][0]["text"],
                "usage": {
                    "prompt_tokens": result.get("usage", {}).get("prompt_tokens", 0),
                    "completion_tokens": result.get("usage", {}).get("completion_tokens", 0),
                    "total_tokens": result.get("usage", {}).get("total_tokens", 0)
                },
                "model": self.model_name,
                "finish_reason": result["choices"][0].get("finish_reason", "stop")
            }
            
        except requests.exceptions.RequestException as e:
            raise Exception(f"Custom model API error: {str(e)}")
            
    def get_default_config(self):
        """Return default configuration for this model."""
        return {
            "temperature": 0.7,
            "max_tokens": 1024,
            "top_p": 1.0,
            "frequency_penalty": 0.0,
            "presence_penalty": 0.0
        }
        
    def validate_config(self, config: dict):
        """Validate model configuration."""
        required_fields = ["api_endpoint", "api_key", "model_name"]
        
        for field in required_fields:
            if field not in config:
                return {
                    "valid": False,
                    "error": f"Missing required field: {field}"
                }
                
        # Validate parameter ranges
        if "temperature" in config:
            if not 0 <= config["temperature"] <= 2:
                return {
                    "valid": False,
                    "error": "Temperature must be between 0 and 2"
                }
                
        return {"valid": True}
        
    def estimate_cost(self, prompt_tokens: int, completion_tokens: int):
        """Estimate cost for the request."""
        # Implement cost calculation based on your pricing model
        prompt_cost = prompt_tokens * 0.0001  # Example: $0.0001 per token
        completion_cost = completion_tokens * 0.0002
        
        return {
            "prompt_cost": prompt_cost,
            "completion_cost": completion_cost,
            "total_cost": prompt_cost + completion_cost,
            "currency": "USD"
        }
        
    def get_rate_limits(self):
        """Return rate limit information."""
        return {
            "requests_per_minute": 60,
            "tokens_per_minute": 90000,
            "requests_per_day": 10000
        }
```

### Register Model Adapter

```python
# evaluation_engine/core/concrete_model_adapters.py

from .custom_model_adapter import CustomModelAdapter

# Register the adapter
MODEL_ADAPTERS = {
    # ... existing adapters ...
    "custom": CustomModelAdapter,
}

def get_model_adapter(model_type: str, config: ModelConfiguration):
    """Get appropriate model adapter for the given type."""
    if model_type not in MODEL_ADAPTERS:
        raise ValueError(f"Unsupported model type: {model_type}")
        
    return MODEL_ADAPTERS[model_type](config)
```

## Adding Custom Metrics

### Custom Metric Implementation

```python
# evaluation_engine/core/custom_metrics.py

from evaluation_engine.core.metrics_engine import MetricsEngine
from typing import List, Dict, Any
import numpy as np
from sklearn.metrics.pairwise import cosine_similarity
import re

class CustomMetricsEngine(MetricsEngine):
    """
    Extended metrics engine with custom domain-specific metrics.
    """
    
    def __init__(self):
        super().__init__()
        self.register_custom_metrics()
        
    def register_custom_metrics(self):
        """Register custom metrics."""
        self.custom_metrics = {
            "domain_expertise_score": self.calculate_domain_expertise,
            "technical_accuracy": self.calculate_technical_accuracy,
            "code_security_score": self.calculate_code_security,
            "financial_reasoning": self.calculate_financial_reasoning,
            "conversation_flow": self.calculate_conversation_flow
        }
        
    def calculate_domain_expertise(self, response: str, reference: str, domain: str) -> float:
        """
        Calculate domain expertise score based on terminology usage and accuracy.
        """
        domain_terms = self.get_domain_terminology(domain)
        
        # Count domain-specific terms used correctly
        correct_terms = 0
        total_terms = len(domain_terms)
        
        for term in domain_terms:
            if term.lower() in response.lower():
                # Check if term is used in correct context
                if self.validate_term_usage(term, response, domain):
                    correct_terms += 1
                    
        expertise_score = correct_terms / total_terms if total_terms > 0 else 0.0
        
        # Adjust score based on overall response quality
        quality_multiplier = self.assess_response_quality(response, reference)
        
        return min(expertise_score * quality_multiplier, 1.0)
        
    def calculate_technical_accuracy(self, response: str, reference: str, context: Dict) -> float:
        """
        Calculate technical accuracy for code or technical content.
        """
        accuracy_score = 0.0
        
        # Check for syntax errors (if code)
        if self.is_code_content(response):
            if self.validate_syntax(response, context.get("language", "python")):
                accuracy_score += 0.3
                
        # Check for logical correctness
        if self.validate_logic(response, reference):
            accuracy_score += 0.4
            
        # Check for best practices
        if self.check_best_practices(response, context):
            accuracy_score += 0.3
            
        return accuracy_score
        
    def calculate_code_security_score(self, code: str, language: str = "python") -> float:
        """
        Calculate security score for code snippets.
        """
        security_issues = []
        security_score = 1.0
        
        # Common security patterns to check
        security_patterns = {
            "sql_injection": r"(SELECT|INSERT|UPDATE|DELETE).*\+.*['\"]",
            "command_injection": r"(os\.system|subprocess\.call|exec|eval)\s*\(",
            "hardcoded_secrets": r"(password|api_key|secret)\s*=\s*['\"][^'\"]+['\"]",
            "unsafe_deserialization": r"(pickle\.loads|yaml\.load)\s*\(",
            "path_traversal": r"\.\./",
        }
        
        for issue_type, pattern in security_patterns.items():
            if re.search(pattern, code, re.IGNORECASE):
                security_issues.append(issue_type)
                security_score -= 0.2
                
        return max(security_score, 0.0)
        
    def calculate_financial_reasoning(self, response: str, context: Dict) -> float:
        """
        Calculate financial reasoning quality for quantitative finance tasks.
        """
        reasoning_score = 0.0
        
        # Check for key financial concepts
        financial_concepts = [
            "risk", "return", "volatility", "correlation", "diversification",
            "sharpe ratio", "alpha", "beta", "portfolio", "hedge"
        ]
        
        concept_coverage = sum(
            1 for concept in financial_concepts 
            if concept in response.lower()
        ) / len(financial_concepts)
        
        reasoning_score += concept_coverage * 0.3
        
        # Check for quantitative analysis
        if self.contains_quantitative_analysis(response):
            reasoning_score += 0.3
            
        # Check for risk considerations
        if self.mentions_risk_factors(response):
            reasoning_score += 0.2
            
        # Check for practical implementation
        if self.includes_implementation_details(response):
            reasoning_score += 0.2
            
        return reasoning_score
        
    def calculate_conversation_flow(self, conversation_turns: List[Dict]) -> float:
        """
        Calculate conversation flow quality for multi-turn scenarios.
        """
        if len(conversation_turns) < 2:
            return 0.0
            
        flow_score = 0.0
        
        # Check topic consistency
        topic_consistency = self.calculate_topic_consistency(conversation_turns)
        flow_score += topic_consistency * 0.4
        
        # Check response relevance
        relevance_score = self.calculate_response_relevance(conversation_turns)
        flow_score += relevance_score * 0.3
        
        # Check progression quality
        progression_score = self.calculate_progression_quality(conversation_turns)
        flow_score += progression_score * 0.3
        
        return flow_score
        
    # Helper methods
    
    def get_domain_terminology(self, domain: str) -> List[str]:
        """Get domain-specific terminology."""
        domain_terms = {
            "finance": [
                "portfolio", "risk", "return", "volatility", "correlation",
                "diversification", "alpha", "beta", "sharpe ratio", "var"
            ],
            "programming": [
                "algorithm", "complexity", "optimization", "refactoring",
                "debugging", "testing", "deployment", "scalability"
            ],
            "machine_learning": [
                "model", "training", "validation", "overfitting", "feature",
                "accuracy", "precision", "recall", "cross-validation"
            ]
        }
        
        return domain_terms.get(domain, [])
        
    def validate_term_usage(self, term: str, response: str, domain: str) -> bool:
        """Validate if a term is used correctly in context."""
        # Simplified validation - in practice, this would be more sophisticated
        term_context = self.extract_term_context(term, response)
        return len(term_context) > 10  # Basic check for meaningful context
        
    def extract_term_context(self, term: str, text: str) -> str:
        """Extract context around a term."""
        import re
        pattern = rf".{{0,50}}{re.escape(term)}.{{0,50}}"
        match = re.search(pattern, text, re.IGNORECASE)
        return match.group(0) if match else ""
        
    def is_code_content(self, content: str) -> bool:
        """Check if content appears to be code."""
        code_indicators = [
            "def ", "class ", "import ", "from ", "if ", "for ", "while ",
            "{", "}", "(", ")", "=", "==", "!=", "<=", ">="
        ]
        
        return any(indicator in content for indicator in code_indicators)
        
    def validate_syntax(self, code: str, language: str) -> bool:
        """Validate code syntax."""
        try:
            if language.lower() == "python":
                compile(code, '<string>', 'exec')
                return True
        except SyntaxError:
            return False
        except:
            pass
            
        return False  # Conservative approach for other languages
        
    def validate_logic(self, response: str, reference: str) -> bool:
        """Validate logical correctness."""
        # Simplified logic validation
        # In practice, this would involve more sophisticated analysis
        return len(response.strip()) > 0 and "error" not in response.lower()
        
    def check_best_practices(self, response: str, context: Dict) -> bool:
        """Check for best practices."""
        # Simplified best practices check
        best_practices = [
            "documentation", "error handling", "validation", "testing"
        ]
        
        return any(practice in response.lower() for practice in best_practices)
```

### Register Custom Metrics

```python
# evaluation_engine/core/metrics_engine.py

from .custom_metrics import CustomMetricsEngine

class MetricsEngine:
    def __init__(self):
        self.custom_engine = CustomMetricsEngine()
        
    def calculate_metric(self, metric_name: str, *args, **kwargs):
        """Calculate a specific metric."""
        if hasattr(self.custom_engine, f"calculate_{metric_name}"):
            return getattr(self.custom_engine, f"calculate_{metric_name}")(*args, **kwargs)
        elif metric_name in self.custom_engine.custom_metrics:
            return self.custom_engine.custom_metrics[metric_name](*args, **kwargs)
        else:
            raise ValueError(f"Unknown metric: {metric_name}")
```

## Creating Plugins

### Plugin Architecture

```python
# evaluation_engine/plugins/base_plugin.py

from abc import ABC, abstractmethod
from typing import Dict, Any, List

class BasePlugin(ABC):
    """
    Base class for all evaluation engine plugins.
    """
    
    def __init__(self, config: Dict[str, Any] = None):
        self.config = config or {}
        self.name = self.__class__.__name__
        self.version = "1.0.0"
        
    @abstractmethod
    def initialize(self) -> bool:
        """Initialize the plugin. Return True if successful."""
        pass
        
    @abstractmethod
    def get_capabilities(self) -> List[str]:
        """Return list of capabilities this plugin provides."""
        pass
        
    @abstractmethod
    def process(self, data: Any, context: Dict[str, Any]) -> Any:
        """Process data with this plugin."""
        pass
        
    def cleanup(self):
        """Cleanup resources when plugin is unloaded."""
        pass
        
    def get_config_schema(self) -> Dict[str, Any]:
        """Return configuration schema for this plugin."""
        return {}
        
    def validate_config(self, config: Dict[str, Any]) -> bool:
        """Validate plugin configuration."""
        return True
```

### Example Plugin Implementation

```python
# evaluation_engine/plugins/code_analysis_plugin.py

from .base_plugin import BasePlugin
from typing import Dict, Any, List
import ast
import subprocess
import tempfile
import os

class CodeAnalysisPlugin(BasePlugin):
    """
    Plugin for advanced code analysis and quality assessment.
    """
    
    def __init__(self, config: Dict[str, Any] = None):
        super().__init__(config)
        self.supported_languages = ["python", "javascript", "java"]
        self.analysis_tools = {}
        
    def initialize(self) -> bool:
        """Initialize code analysis tools."""
        try:
            # Initialize Python analysis tools
            self.analysis_tools["python"] = {
                "ast_parser": ast,
                "linter": "pylint",
                "formatter": "black"
            }
            
            # Check if external tools are available
            self._check_external_tools()
            
            return True
        except Exception as e:
            print(f"Failed to initialize CodeAnalysisPlugin: {e}")
            return False
            
    def get_capabilities(self) -> List[str]:
        """Return plugin capabilities."""
        return [
            "syntax_analysis",
            "complexity_analysis", 
            "style_analysis",
            "security_analysis",
            "performance_analysis"
        ]
        
    def process(self, data: Any, context: Dict[str, Any]) -> Any:
        """Analyze code and return quality metrics."""
        code = data.get("code", "")
        language = context.get("language", "python")
        
        if language not in self.supported_languages:
            return {"error": f"Unsupported language: {language}"}
            
        analysis_results = {}
        
        # Syntax analysis
        analysis_results["syntax"] = self._analyze_syntax(code, language)
        
        # Complexity analysis
        analysis_results["complexity"] = self._analyze_complexity(code, language)
        
        # Style analysis
        analysis_results["style"] = self._analyze_style(code, language)
        
        # Security analysis
        analysis_results["security"] = self._analyze_security(code, language)
        
        # Performance analysis
        analysis_results["performance"] = self._analyze_performance(code, language)
        
        return analysis_results
        
    def _analyze_syntax(self, code: str, language: str) -> Dict[str, Any]:
        """Analyze code syntax."""
        if language == "python":
            try:
                ast.parse(code)
                return {"valid": True, "errors": []}
            except SyntaxError as e:
                return {
                    "valid": False,
                    "errors": [{"line": e.lineno, "message": str(e)}]
                }
        
        return {"valid": True, "errors": []}  # Placeholder for other languages
        
    def _analyze_complexity(self, code: str, language: str) -> Dict[str, Any]:
        """Analyze code complexity."""
        if language == "python":
            try:
                tree = ast.parse(code)
                complexity_analyzer = PythonComplexityAnalyzer()
                return complexity_analyzer.analyze(tree)
            except:
                return {"cyclomatic_complexity": 0, "cognitive_complexity": 0}
                
        return {"cyclomatic_complexity": 0, "cognitive_complexity": 0}
        
    def _analyze_style(self, code: str, language: str) -> Dict[str, Any]:
        """Analyze code style."""
        style_issues = []
        
        if language == "python":
            # Check basic Python style guidelines
            lines = code.split('\n')
            
            for i, line in enumerate(lines, 1):
                # Line length check
                if len(line) > 88:
                    style_issues.append({
                        "line": i,
                        "type": "line_too_long",
                        "message": f"Line too long ({len(line)} > 88 characters)"
                    })
                    
                # Indentation check (simplified)
                if line.startswith(' ') and not line.startswith('    '):
                    if len(line) - len(line.lstrip()) % 4 != 0:
                        style_issues.append({
                            "line": i,
                            "type": "indentation",
                            "message": "Inconsistent indentation"
                        })
                        
        return {
            "issues": style_issues,
            "score": max(0, 1.0 - len(style_issues) * 0.1)
        }
        
    def _analyze_security(self, code: str, language: str) -> Dict[str, Any]:
        """Analyze code for security issues."""
        security_issues = []
        
        if language == "python":
            # Check for common security anti-patterns
            dangerous_patterns = [
                ("eval(", "Use of eval() is dangerous"),
                ("exec(", "Use of exec() is dangerous"),
                ("os.system(", "Use of os.system() can lead to command injection"),
                ("subprocess.call(", "Unsafe subprocess usage"),
                ("pickle.loads(", "Unsafe deserialization"),
            ]
            
            for pattern, message in dangerous_patterns:
                if pattern in code:
                    security_issues.append({
                        "type": "dangerous_function",
                        "pattern": pattern,
                        "message": message
                    })
                    
        return {
            "issues": security_issues,
            "score": max(0, 1.0 - len(security_issues) * 0.2)
        }
        
    def _analyze_performance(self, code: str, language: str) -> Dict[str, Any]:
        """Analyze code for performance issues."""
        performance_issues = []
        
        if language == "python":
            # Check for common performance anti-patterns
            if "for" in code and "append" in code:
                if code.count("append") > 5:
                    performance_issues.append({
                        "type": "inefficient_loop",
                        "message": "Consider using list comprehension"
                    })
                    
            if "+" in code and "str" in code:
                performance_issues.append({
                    "type": "string_concatenation",
                    "message": "Consider using join() for string concatenation"
                })
                
        return {
            "issues": performance_issues,
            "score": max(0, 1.0 - len(performance_issues) * 0.15)
        }
        
    def _check_external_tools(self):
        """Check availability of external analysis tools."""
        tools_to_check = ["pylint", "black", "mypy"]
        
        for tool in tools_to_check:
            try:
                subprocess.run([tool, "--version"], 
                             capture_output=True, check=True)
                print(f"✓ {tool} is available")
            except (subprocess.CalledProcessError, FileNotFoundError):
                print(f"✗ {tool} is not available")

class PythonComplexityAnalyzer(ast.NodeVisitor):
    """AST visitor for calculating Python code complexity."""
    
    def __init__(self):
        self.cyclomatic_complexity = 1  # Base complexity
        self.cognitive_complexity = 0
        
    def analyze(self, tree):
        """Analyze AST tree and return complexity metrics."""
        self.visit(tree)
        return {
            "cyclomatic_complexity": self.cyclomatic_complexity,
            "cognitive_complexity": self.cognitive_complexity
        }
        
    def visit_If(self, node):
        self.cyclomatic_complexity += 1
        self.cognitive_complexity += 1
        self.generic_visit(node)
        
    def visit_While(self, node):
        self.cyclomatic_complexity += 1
        self.cognitive_complexity += 1
        self.generic_visit(node)
        
    def visit_For(self, node):
        self.cyclomatic_complexity += 1
        self.cognitive_complexity += 1
        self.generic_visit(node)
```

### Plugin Registration

```python
# evaluation_engine/plugins/plugin_manager.py

from typing import Dict, List, Type
from .base_plugin import BasePlugin
from .code_analysis_plugin import CodeAnalysisPlugin

class PluginManager:
    """
    Manages plugin registration and lifecycle.
    """
    
    def __init__(self):
        self.plugins: Dict[str, BasePlugin] = {}
        self.plugin_registry: Dict[str, Type[BasePlugin]] = {
            "code_analysis": CodeAnalysisPlugin,
        }
        
    def register_plugin(self, name: str, plugin_class: Type[BasePlugin]):
        """Register a new plugin class."""
        self.plugin_registry[name] = plugin_class
        
    def load_plugin(self, name: str, config: Dict = None) -> bool:
        """Load and initialize a plugin."""
        if name not in self.plugin_registry:
            raise ValueError(f"Unknown plugin: {name}")
            
        plugin_class = self.plugin_registry[name]
        plugin_instance = plugin_class(config)
        
        if plugin_instance.initialize():
            self.plugins[name] = plugin_instance
            return True
        else:
            return False
            
    def unload_plugin(self, name: str):
        """Unload a plugin."""
        if name in self.plugins:
            self.plugins[name].cleanup()
            del self.plugins[name]
            
    def get_plugin(self, name: str) -> BasePlugin:
        """Get a loaded plugin."""
        return self.plugins.get(name)
        
    def list_available_plugins(self) -> List[str]:
        """List all available plugins."""
        return list(self.plugin_registry.keys())
        
    def list_loaded_plugins(self) -> List[str]:
        """List all loaded plugins."""
        return list(self.plugins.keys())
```

## Testing Extensions

### Unit Testing Framework

```python
# tests/test_custom_task.py

import pytest
from lm_eval.tasks.single_turn_scenarios.my_new_task.my_new_task import MyNewTask

class TestMyNewTask:
    """Test suite for custom task implementation."""
    
    def setup_method(self):
        """Set up test fixtures."""
        self.task = MyNewTask()
        self.sample_doc = {
            "question": "What is the capital of France?",
            "expected_answer": "Paris",
            "context": "",
            "required_keywords": ["paris", "france"],
            "difficulty": "easy"
        }
        
    def test_doc_to_text(self):
        """Test document to text conversion."""
        text = self.task.doc_to_text(self.sample_doc)
        assert "What is the capital of France?" in text
        assert "Answer:" in text
        
    def test_doc_to_target(self):
        """Test target extraction."""
        target = self.task.doc_to_target(self.sample_doc)
        assert target == "Paris"
        
    def test_process_results_exact_match(self):
        """Test result processing with exact match."""
        results = ["Paris"]
        processed = self.task.process_results(self.sample_doc, results)
        
        assert processed["exact_match"] == 1.0
        assert processed["model_output"] == "Paris"
        assert processed["expected_answer"] == "Paris"
        
    def test_process_results_no_match(self):
        """Test result processing with no match."""
        results = ["London"]
        processed = self.task.process_results(self.sample_doc, results)
        
        assert processed["exact_match"] == 0.0
        assert processed["model_output"] == "London"
        
    def test_custom_quality_score(self):
        """Test custom quality scoring."""
        # Test with good response
        good_response = "Paris is the capital of France"
        score = self.task._calculate_quality_score(self.sample_doc, good_response)
        assert score > 0.5
        
        # Test with empty response
        empty_response = ""
        score = self.task._calculate_quality_score(self.sample_doc, empty_response)
        assert score < 0.5
        
    def test_aggregation_config(self):
        """Test aggregation configuration."""
        agg_config = self.task.aggregation()
        assert "exact_match" in agg_config
        assert "mean" in agg_config["exact_match"]
        
    def test_higher_is_better_config(self):
        """Test higher-is-better configuration."""
        hib_config = self.task.higher_is_better()
        assert hib_config["exact_match"] is True
        assert hib_config["custom_score"] is True
```

### Integration Testing

```python
# tests/test_integration.py

import pytest
from evaluation_engine import EvaluationClient
from evaluation_engine.core.model_adapters import get_model_adapter
from evaluation_engine.core.advanced_model_config import ModelConfiguration

class TestIntegration:
    """Integration tests for custom extensions."""
    
    def setup_method(self):
        """Set up integration test environment."""
        self.client = EvaluationClient(
            base_url="http://localhost:8000",
            api_key="test-key"
        )
        
    @pytest.mark.integration
    def test_custom_task_evaluation(self):
        """Test evaluation with custom task."""
        evaluation = self.client.create_evaluation(
            models=[{
                "model_id": "openai/gpt-3.5-turbo",
                "model_type": "openai",
                "config": {"temperature": 0.0}
            }],
            tasks=["single_turn_scenarios_my_new_task"]
        )
        
        assert evaluation.id is not None
        assert evaluation.status in ["queued", "running"]
        
    @pytest.mark.integration
    def test_custom_model_adapter(self):
        """Test custom model adapter."""
        config = ModelConfiguration({
            "api_endpoint": "http://localhost:8080",
            "api_key": "test-key",
            "model_name": "custom-model"
        })
        
        adapter = get_model_adapter("custom", config)
        assert adapter is not None
        
        model_info = adapter.get_model_info()
        assert model_info["model_type"] == "custom"
        
    @pytest.mark.integration
    def test_plugin_loading(self):
        """Test plugin loading and usage."""
        from evaluation_engine.plugins.plugin_manager import PluginManager
        
        manager = PluginManager()
        success = manager.load_plugin("code_analysis")
        assert success is True
        
        plugin = manager.get_plugin("code_analysis")
        assert plugin is not None
        
        # Test plugin functionality
        result = plugin.process(
            {"code": "def hello(): print('Hello, World!')"},
            {"language": "python"}
        )
        
        assert "syntax" in result
        assert result["syntax"]["valid"] is True
```

## Best Practices

### Code Organization

1. **Modular Design**: Keep extensions modular and loosely coupled
2. **Clear Interfaces**: Define clear interfaces for extensibility
3. **Documentation**: Document all extension points and APIs
4. **Testing**: Provide comprehensive test coverage
5. **Configuration**: Use configuration files for customization

### Performance Considerations

1. **Lazy Loading**: Load extensions only when needed
2. **Caching**: Cache expensive computations
3. **Async Processing**: Use async patterns for I/O operations
4. **Resource Management**: Properly manage resources and cleanup

### Security Guidelines

1. **Input Validation**: Validate all inputs from extensions
2. **Sandboxing**: Run untrusted code in sandboxed environments
3. **Access Control**: Implement proper access controls
4. **Audit Logging**: Log all extension activities

This developer guide provides comprehensive documentation for extending the AI Evaluation Engine with custom tasks, model adapters, metrics, and plugins.