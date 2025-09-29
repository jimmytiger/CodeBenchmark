# Custom Agent Integration Guide

## Table of Contents

1. [Overview](#overview)
2. [Agent Interface](#agent-interface)
3. [Implementation Examples](#implementation-examples)
4. [Registration and Configuration](#registration-and-configuration)
5. [Testing Custom Agents](#testing-custom-agents)
6. [Advanced Features](#advanced-features)
7. [Best Practices](#best-practices)
8. [Troubleshooting](#troubleshooting)

## Overview

The Multi-Turn Evaluation Engine supports custom agent implementations, allowing you to evaluate your own AI agents alongside standard models. This guide shows how to integrate custom agents into the evaluation framework.

### Key Benefits

- **Standardized Evaluation**: Use the same evaluation framework for all agents
- **Comprehensive Metrics**: Get detailed metrics and analysis for your custom agents
- **Fair Comparison**: Compare custom agents against baseline models
- **Flexible Integration**: Support for various agent architectures and APIs

## Agent Interface

### Base Agent Interface

All custom agents must implement the `CustomAgent` interface:

```python
from abc import ABC, abstractmethod
from typing import Dict, Any, List, Optional
import asyncio

class CustomAgent(ABC):
    """Base interface for custom agent implementations."""
    
    def __init__(self, config: Dict[str, Any]):
        """
        Initialize the agent with configuration.
        
        Args:
            config: Agent-specific configuration dictionary
        """
        self.config = config
        self.conversation_history = []
        self.current_context = {}
    
    @abstractmethod
    async def generate_action(self, 
                            observation: Dict[str, Any], 
                            context: Dict[str, Any]) -> Dict[str, Any]:
        """
        Generate next action based on observation and context.
        
        Args:
            observation: Current environment observation
            context: Evaluation context and history
            
        Returns:
            Dict containing the action to execute
        """
        pass
    
    @abstractmethod
    def reset(self):
        """Reset agent state for new evaluation."""
        pass
    
    @abstractmethod
    def get_agent_info(self) -> Dict[str, Any]:
        """Get agent information and capabilities."""
        pass
    
    # Optional methods with default implementations
    
    def configure(self, config: Dict[str, Any]):
        """Update agent configuration."""
        self.config.update(config)
    
    def get_conversation_history(self) -> List[Dict[str, Any]]:
        """Get conversation history."""
        return self.conversation_history.copy()
    
    def add_to_history(self, entry: Dict[str, Any]):
        """Add entry to conversation history."""
        self.conversation_history.append(entry)
    
    def get_current_context(self) -> Dict[str, Any]:
        """Get current context."""
        return self.current_context.copy()
    
    def update_context(self, updates: Dict[str, Any]):
        """Update current context."""
        self.current_context.update(updates)
```

### Action Format

Actions returned by `generate_action()` must follow this format:

```python
{
    "type": "action_type",  # Required: type of action
    "parameters": {         # Required: action parameters
        "param1": "value1",
        "param2": "value2"
    },
    "reasoning": "...",     # Optional: explanation of the action
    "confidence": 0.85,     # Optional: confidence score (0-1)
    "metadata": {           # Optional: additional metadata
        "strategy": "exploration",
        "priority": "high"
    }
}
```

### Common Action Types

The evaluation engine supports these standard action types:

- `read_file`: Read a file from the environment
- `write_file`: Write content to a file
- `execute_command`: Execute a shell command
- `run_tests`: Run test suites
- `analyze_code`: Perform code analysis
- `search_code`: Search for code patterns
- `ask_question`: Ask clarifying questions (for conversational scenarios)

## Implementation Examples

### Example 1: Simple Rule-Based Agent

```python
from evaluation_engine.agents import CustomAgent
import re

class SimpleRuleBasedAgent(CustomAgent):
    """Simple rule-based agent for demonstration."""
    
    def __init__(self, config: Dict[str, Any]):
        super().__init__(config)
        self.current_strategy = "exploration"
        self.files_read = set()
        self.errors_encountered = []
    
    async def generate_action(self, observation: Dict[str, Any], context: Dict[str, Any]) -> Dict[str, Any]:
        """Generate action based on simple rules."""
        
        # Add to history
        self.add_to_history({
            'type': 'observation',
            'content': observation,
            'timestamp': context.get('timestamp')
        })
        
        # Determine action based on current state
        if self._needs_exploration(observation):
            action = self._generate_exploration_action(observation)
        elif self._needs_implementation(observation):
            action = self._generate_implementation_action(observation)
        elif self._needs_debugging(observation):
            action = self._generate_debugging_action(observation)
        else:
            action = self._generate_verification_action(observation)
        
        # Add action to history
        self.add_to_history({
            'type': 'action',
            'content': action,
            'timestamp': context.get('timestamp')
        })
        
        return action
    
    def _needs_exploration(self, observation: Dict[str, Any]) -> bool:
        """Check if exploration is needed."""
        return (
            'task_description' in observation and 
            len(self.files_read) < 3 and
            'file_list' in observation
        )
    
    def _needs_implementation(self, observation: Dict[str, Any]) -> bool:
        """Check if implementation is needed."""
        return (
            len(self.files_read) >= 2 and
            'implementation_needed' in observation
        )
    
    def _needs_debugging(self, observation: Dict[str, Any]) -> bool:
        """Check if debugging is needed."""
        return (
            'error' in observation or
            'test_failures' in observation
        )
    
    def _generate_exploration_action(self, observation: Dict[str, Any]) -> Dict[str, Any]:
        """Generate exploration action."""
        if 'file_list' in observation:
            # Choose most relevant file to read
            files = observation['file_list']
            target_file = self._select_most_relevant_file(files)
            
            return {
                "type": "read_file",
                "parameters": {
                    "filename": target_file
                },
                "reasoning": f"Reading {target_file} to understand the codebase structure",
                "confidence": 0.8
            }
        else:
            return {
                "type": "execute_command",
                "parameters": {
                    "command": "find . -name '*.py' | head -10"
                },
                "reasoning": "Discovering Python files in the project",
                "confidence": 0.9
            }
    
    def _generate_implementation_action(self, observation: Dict[str, Any]) -> Dict[str, Any]:
        """Generate implementation action."""
        if 'target_file' in observation:
            return {
                "type": "write_file",
                "parameters": {
                    "filename": observation['target_file'],
                    "content": self._generate_code_solution(observation)
                },
                "reasoning": "Implementing solution based on analysis",
                "confidence": 0.7
            }
        else:
            return {
                "type": "analyze_code",
                "parameters": {
                    "analysis_type": "structure"
                },
                "reasoning": "Analyzing code structure to determine implementation approach",
                "confidence": 0.8
            }
    
    def _generate_debugging_action(self, observation: Dict[str, Any]) -> Dict[str, Any]:
        """Generate debugging action."""
        if 'test_failures' in observation:
            return {
                "type": "analyze_code",
                "parameters": {
                    "analysis_type": "test_failures",
                    "failures": observation['test_failures']
                },
                "reasoning": "Analyzing test failures to identify issues",
                "confidence": 0.85
            }
        elif 'error' in observation:
            return {
                "type": "execute_command",
                "parameters": {
                    "command": f"python -c \"import traceback; traceback.print_exc()\""
                },
                "reasoning": "Getting detailed error information",
                "confidence": 0.9
            }
    
    def _generate_verification_action(self, observation: Dict[str, Any]) -> Dict[str, Any]:
        """Generate verification action."""
        return {
            "type": "run_tests",
            "parameters": {
                "test_suite": "all"
            },
            "reasoning": "Running tests to verify solution",
            "confidence": 0.9
        }
    
    def _select_most_relevant_file(self, files: List[str]) -> str:
        """Select most relevant file to read."""
        # Simple heuristic: prefer main files, then test files
        for file in files:
            if file.endswith('main.py') or file.endswith('__init__.py'):
                return file
        
        for file in files:
            if 'test' not in file.lower() and file.endswith('.py'):
                return file
        
        return files[0] if files else "README.md"
    
    def _generate_code_solution(self, observation: Dict[str, Any]) -> str:
        """Generate code solution (simplified)."""
        # This would contain actual code generation logic
        return """
def solution():
    # Generated solution based on analysis
    pass
"""
    
    def reset(self):
        """Reset agent state."""
        self.conversation_history = []
        self.current_context = {}
        self.current_strategy = "exploration"
        self.files_read = set()
        self.errors_encountered = []
    
    def get_agent_info(self) -> Dict[str, Any]:
        """Get agent information."""
        return {
            "name": "SimpleRuleBasedAgent",
            "version": "1.0.0",
            "description": "Simple rule-based agent for multi-turn evaluation",
            "capabilities": [
                "file_reading",
                "code_analysis",
                "test_execution",
                "debugging"
            ],
            "strategies": [
                "exploration",
                "implementation",
                "debugging",
                "verification"
            ]
        }
```

### Example 2: LLM-Powered Agent

```python
import openai
from evaluation_engine.agents import CustomAgent

class LLMPoweredAgent(CustomAgent):
    """Agent powered by a language model API."""
    
    def __init__(self, config: Dict[str, Any]):
        super().__init__(config)
        self.client = openai.OpenAI(api_key=config['api_key'])
        self.model = config.get('model', 'gpt-4')
        self.temperature = config.get('temperature', 0.7)
        self.max_tokens = config.get('max_tokens', 2000)
        self.system_prompt = self._build_system_prompt()
    
    def _build_system_prompt(self) -> str:
        """Build system prompt for the LLM."""
        return """
You are an AI agent participating in a multi-turn evaluation. Your goal is to complete programming tasks through a series of actions.

Available actions:
- read_file: Read a file to understand code structure
- write_file: Write or modify code files
- execute_command: Run shell commands
- run_tests: Execute test suites
- analyze_code: Perform code analysis

For each action, provide:
1. The action type
2. Required parameters
3. Your reasoning
4. Confidence level (0-1)

Be systematic, start with exploration, then implement solutions, and verify with tests.
"""
    
    async def generate_action(self, observation: Dict[str, Any], context: Dict[str, Any]) -> Dict[str, Any]:
        """Generate action using LLM."""
        
        # Build conversation context
        messages = [{"role": "system", "content": self.system_prompt}]
        
        # Add conversation history
        for entry in self.conversation_history[-10:]:  # Last 10 entries
            if entry['type'] == 'observation':
                messages.append({
                    "role": "user",
                    "content": f"Observation: {self._format_observation(entry['content'])}"
                })
            elif entry['type'] == 'action':
                messages.append({
                    "role": "assistant",
                    "content": f"Action: {self._format_action(entry['content'])}"
                })
        
        # Add current observation
        messages.append({
            "role": "user",
            "content": f"Current observation: {self._format_observation(observation)}\n\nWhat action should I take next?"
        })
        
        # Generate response
        try:
            response = await self._call_llm(messages)
            action = self._parse_llm_response(response)
            
            # Add to history
            self.add_to_history({
                'type': 'observation',
                'content': observation,
                'timestamp': context.get('timestamp')
            })
            self.add_to_history({
                'type': 'action',
                'content': action,
                'timestamp': context.get('timestamp')
            })
            
            return action
            
        except Exception as e:
            # Fallback action on error
            return {
                "type": "execute_command",
                "parameters": {"command": "ls -la"},
                "reasoning": f"LLM error: {str(e)}, falling back to basic exploration",
                "confidence": 0.3
            }
    
    async def _call_llm(self, messages: List[Dict[str, str]]) -> str:
        """Call the language model API."""
        response = await self.client.chat.completions.create(
            model=self.model,
            messages=messages,
            temperature=self.temperature,
            max_tokens=self.max_tokens
        )
        return response.choices[0].message.content
    
    def _format_observation(self, observation: Dict[str, Any]) -> str:
        """Format observation for LLM."""
        formatted = []
        for key, value in observation.items():
            if isinstance(value, str) and len(value) > 500:
                value = value[:500] + "... (truncated)"
            formatted.append(f"{key}: {value}")
        return "\n".join(formatted)
    
    def _format_action(self, action: Dict[str, Any]) -> str:
        """Format action for LLM."""
        return f"Type: {action['type']}, Parameters: {action.get('parameters', {})}, Reasoning: {action.get('reasoning', 'N/A')}"
    
    def _parse_llm_response(self, response: str) -> Dict[str, Any]:
        """Parse LLM response into action format."""
        # This would contain more sophisticated parsing logic
        # For now, a simple implementation
        
        lines = response.strip().split('\n')
        action = {
            "type": "execute_command",
            "parameters": {"command": "echo 'parsing error'"},
            "reasoning": "Failed to parse LLM response",
            "confidence": 0.1
        }
        
        # Try to extract action information
        for line in lines:
            if line.startswith("Type:"):
                action["type"] = line.split(":", 1)[1].strip()
            elif line.startswith("Parameters:"):
                # Simple parameter parsing
                params_str = line.split(":", 1)[1].strip()
                try:
                    action["parameters"] = eval(params_str)  # Unsafe, use proper parsing
                except:
                    action["parameters"] = {"command": params_str}
            elif line.startswith("Reasoning:"):
                action["reasoning"] = line.split(":", 1)[1].strip()
            elif line.startswith("Confidence:"):
                try:
                    action["confidence"] = float(line.split(":", 1)[1].strip())
                except:
                    action["confidence"] = 0.5
        
        return action
    
    def reset(self):
        """Reset agent state."""
        self.conversation_history = []
        self.current_context = {}
    
    def get_agent_info(self) -> Dict[str, Any]:
        """Get agent information."""
        return {
            "name": "LLMPoweredAgent",
            "version": "1.0.0",
            "description": f"Agent powered by {self.model}",
            "model": self.model,
            "temperature": self.temperature,
            "max_tokens": self.max_tokens,
            "capabilities": [
                "natural_language_reasoning",
                "code_generation",
                "problem_solving",
                "adaptive_strategy"
            ]
        }
```

### Example 3: Hybrid Agent with Multiple Strategies

```python
from evaluation_engine.agents import CustomAgent
from typing import Dict, Any, List
import random

class HybridAgent(CustomAgent):
    """Hybrid agent combining multiple strategies."""
    
    def __init__(self, config: Dict[str, Any]):
        super().__init__(config)
        self.strategies = {
            'exploration': ExplorationStrategy(),
            'implementation': ImplementationStrategy(),
            'debugging': DebuggingStrategy(),
            'optimization': OptimizationStrategy()
        }
        self.current_strategy = 'exploration'
        self.strategy_history = []
        self.performance_tracker = PerformanceTracker()
    
    async def generate_action(self, observation: Dict[str, Any], context: Dict[str, Any]) -> Dict[str, Any]:
        """Generate action using current strategy."""
        
        # Analyze situation and select strategy
        new_strategy = self._select_strategy(observation, context)
        if new_strategy != self.current_strategy:
            self._switch_strategy(new_strategy)
        
        # Generate action using current strategy
        strategy = self.strategies[self.current_strategy]
        action = await strategy.generate_action(observation, context, self.conversation_history)
        
        # Track performance
        self.performance_tracker.record_action(action, self.current_strategy)
        
        # Update history
        self.add_to_history({
            'type': 'observation',
            'content': observation,
            'strategy': self.current_strategy,
            'timestamp': context.get('timestamp')
        })
        self.add_to_history({
            'type': 'action',
            'content': action,
            'strategy': self.current_strategy,
            'timestamp': context.get('timestamp')
        })
        
        return action
    
    def _select_strategy(self, observation: Dict[str, Any], context: Dict[str, Any]) -> str:
        """Select appropriate strategy based on current situation."""
        
        # Strategy selection logic
        if 'error' in observation or 'test_failures' in observation:
            return 'debugging'
        elif 'task_description' in observation and len(self.conversation_history) < 5:
            return 'exploration'
        elif self._has_sufficient_understanding() and not self._has_implementation():
            return 'implementation'
        elif self._has_working_solution() and context.get('turn_number', 0) > 10:
            return 'optimization'
        else:
            return self.current_strategy
    
    def _switch_strategy(self, new_strategy: str):
        """Switch to new strategy."""
        self.strategy_history.append({
            'from': self.current_strategy,
            'to': new_strategy,
            'turn': len(self.conversation_history)
        })
        self.current_strategy = new_strategy
    
    def _has_sufficient_understanding(self) -> bool:
        """Check if we have sufficient understanding of the task."""
        files_read = sum(1 for entry in self.conversation_history 
                        if entry.get('type') == 'action' and 
                        entry.get('content', {}).get('type') == 'read_file')
        return files_read >= 3
    
    def _has_implementation(self) -> bool:
        """Check if we have attempted implementation."""
        return any(entry.get('type') == 'action' and 
                  entry.get('content', {}).get('type') == 'write_file'
                  for entry in self.conversation_history)
    
    def _has_working_solution(self) -> bool:
        """Check if we have a working solution."""
        # Look for successful test runs
        return any(entry.get('type') == 'observation' and 
                  'test_passed' in entry.get('content', {})
                  for entry in self.conversation_history)
    
    def reset(self):
        """Reset agent state."""
        self.conversation_history = []
        self.current_context = {}
        self.current_strategy = 'exploration'
        self.strategy_history = []
        self.performance_tracker.reset()
        
        # Reset all strategies
        for strategy in self.strategies.values():
            strategy.reset()
    
    def get_agent_info(self) -> Dict[str, Any]:
        """Get agent information."""
        return {
            "name": "HybridAgent",
            "version": "1.0.0",
            "description": "Hybrid agent with multiple adaptive strategies",
            "strategies": list(self.strategies.keys()),
            "current_strategy": self.current_strategy,
            "strategy_history": self.strategy_history,
            "performance_stats": self.performance_tracker.get_stats(),
            "capabilities": [
                "adaptive_strategy_selection",
                "multi_strategy_execution",
                "performance_tracking",
                "context_awareness"
            ]
        }

# Strategy implementations would be separate classes
class ExplorationStrategy:
    """Strategy for exploring and understanding the task."""
    
    async def generate_action(self, observation, context, history):
        # Implementation for exploration actions
        pass
    
    def reset(self):
        pass

class ImplementationStrategy:
    """Strategy for implementing solutions."""
    
    async def generate_action(self, observation, context, history):
        # Implementation for solution actions
        pass
    
    def reset(self):
        pass

# ... other strategy classes
```

## Registration and Configuration

### Registering Custom Agents

```python
from evaluation_engine import register_custom_agent

# Register your custom agent
register_custom_agent(
    agent_name="my_custom_agent",
    agent_class=MyCustomAgent,
    default_config={
        'temperature': 0.7,
        'max_tokens': 2000,
        'strategy': 'adaptive'
    }
)

# Register multiple agents
agents = {
    'rule_based_agent': SimpleRuleBasedAgent,
    'llm_powered_agent': LLMPoweredAgent,
    'hybrid_agent': HybridAgent
}

for name, agent_class in agents.items():
    register_custom_agent(name, agent_class)
```

### Configuration Examples

```yaml
# config.yaml - Using custom agent
model_id: "my_custom_agent"
model_config:
  temperature: 0.5
  max_tokens: 1500
  strategy: "conservative"
  api_key: "your_api_key_here"

task_ids:
  - "swe_bench_lite_001"
  - "intercode_python_001"

max_turns: 15
timeout_seconds: 3600
```

```python
# Python configuration
config = {
    'model_id': 'hybrid_agent',
    'model_config': {
        'strategies': ['exploration', 'implementation', 'debugging'],
        'strategy_switching': True,
        'performance_tracking': True
    },
    'task_ids': ['convcode_bench_001'],
    'max_turns': 20
}
```

## Testing Custom Agents

### Unit Testing

```python
import unittest
from unittest.mock import Mock, patch
from my_custom_agent import MyCustomAgent

class TestMyCustomAgent(unittest.TestCase):
    """Test cases for custom agent."""
    
    def setUp(self):
        """Set up test fixtures."""
        self.config = {
            'temperature': 0.7,
            'max_tokens': 1000
        }
        self.agent = MyCustomAgent(self.config)
    
    def test_agent_initialization(self):
        """Test agent initialization."""
        self.assertIsNotNone(self.agent)
        self.assertEqual(self.agent.config, self.config)
        self.assertEqual(len(self.agent.conversation_history), 0)
    
    async def test_generate_action_exploration(self):
        """Test action generation during exploration phase."""
        observation = {
            'task_description': 'Fix the bug in the code',
            'file_list': ['main.py', 'test.py', 'utils.py']
        }
        context = {'turn_number': 1}
        
        action = await self.agent.generate_action(observation, context)
        
        self.assertIn('type', action)
        self.assertIn('parameters', action)
        self.assertEqual(action['type'], 'read_file')
    
    async def test_generate_action_implementation(self):
        """Test action generation during implementation phase."""
        # Set up agent state for implementation
        self.agent.files_read = {'main.py', 'utils.py'}
        
        observation = {
            'implementation_needed': True,
            'target_file': 'main.py'
        }
        context = {'turn_number': 5}
        
        action = await self.agent.generate_action(observation, context)
        
        self.assertEqual(action['type'], 'write_file')
        self.assertIn('filename', action['parameters'])
    
    def test_reset(self):
        """Test agent reset functionality."""
        # Add some history
        self.agent.add_to_history({'test': 'data'})
        self.agent.update_context({'key': 'value'})
        
        # Reset
        self.agent.reset()
        
        # Verify reset
        self.assertEqual(len(self.agent.conversation_history), 0)
        self.assertEqual(len(self.agent.current_context), 0)
    
    def test_get_agent_info(self):
        """Test agent info retrieval."""
        info = self.agent.get_agent_info()
        
        self.assertIn('name', info)
        self.assertIn('version', info)
        self.assertIn('capabilities', info)

if __name__ == '__main__':
    unittest.main()
```

### Integration Testing

```python
import asyncio
from evaluation_engine.testing import AgentTestFramework

class TestAgentIntegration:
    """Integration tests for custom agent."""
    
    def setUp(self):
        self.test_framework = AgentTestFramework()
        self.agent = MyCustomAgent({'temperature': 0.5})
    
    async def test_swe_bench_integration(self):
        """Test agent with SWE-bench task."""
        task_config = {
            'task_id': 'swe_bench_lite_test_001',
            'max_turns': 10,
            'timeout': 1800
        }
        
        result = await self.test_framework.run_agent_test(
            agent=self.agent,
            task_config=task_config
        )
        
        assert result.success_rate > 0.5
        assert result.avg_turns <= 10
        assert len(result.safety_violations) == 0
    
    async def test_intercode_integration(self):
        """Test agent with InterCode task."""
        task_config = {
            'task_id': 'intercode_python_test_001',
            'max_turns': 8,
            'timeout': 900
        }
        
        result = await self.test_framework.run_agent_test(
            agent=self.agent,
            task_config=task_config
        )
        
        assert result.execution_success_rate > 0.7
        assert result.code_correctness > 0.6
```

### Performance Testing

```python
import time
import psutil
from evaluation_engine.testing import PerformanceTester

class TestAgentPerformance:
    """Performance tests for custom agent."""
    
    def test_response_time(self):
        """Test agent response time."""
        agent = MyCustomAgent({'temperature': 0.7})
        tester = PerformanceTester()
        
        # Test response times
        response_times = []
        for i in range(100):
            start_time = time.time()
            
            observation = {'test': f'observation_{i}'}
            context = {'turn_number': i}
            
            action = asyncio.run(agent.generate_action(observation, context))
            
            response_time = time.time() - start_time
            response_times.append(response_time)
        
        avg_response_time = sum(response_times) / len(response_times)
        assert avg_response_time < 2.0  # Should respond within 2 seconds
    
    def test_memory_usage(self):
        """Test agent memory usage."""
        agent = MyCustomAgent({'temperature': 0.7})
        
        # Measure initial memory
        process = psutil.Process()
        initial_memory = process.memory_info().rss
        
        # Run many actions
        for i in range(1000):
            observation = {'test': f'observation_{i}'}
            context = {'turn_number': i}
            
            asyncio.run(agent.generate_action(observation, context))
        
        # Measure final memory
        final_memory = process.memory_info().rss
        memory_increase = final_memory - initial_memory
        
        # Should not increase memory by more than 100MB
        assert memory_increase < 100 * 1024 * 1024
```

## Advanced Features

### State Persistence

```python
class StatefulAgent(CustomAgent):
    """Agent with persistent state across evaluations."""
    
    def __init__(self, config: Dict[str, Any]):
        super().__init__(config)
        self.state_file = config.get('state_file', 'agent_state.json')
        self.load_state()
    
    def save_state(self):
        """Save agent state to file."""
        state = {
            'conversation_history': self.conversation_history,
            'current_context': self.current_context,
            'learned_patterns': getattr(self, 'learned_patterns', {}),
            'performance_stats': getattr(self, 'performance_stats', {})
        }
        
        with open(self.state_file, 'w') as f:
            json.dump(state, f, indent=2, default=str)
    
    def load_state(self):
        """Load agent state from file."""
        try:
            with open(self.state_file, 'r') as f:
                state = json.load(f)
            
            self.conversation_history = state.get('conversation_history', [])
            self.current_context = state.get('current_context', {})
            self.learned_patterns = state.get('learned_patterns', {})
            self.performance_stats = state.get('performance_stats', {})
        except FileNotFoundError:
            # Initialize with empty state
            pass
    
    def reset(self):
        """Reset but preserve learned knowledge."""
        # Save current performance stats
        self.update_performance_stats()
        
        # Reset conversation state but keep learned patterns
        self.conversation_history = []
        self.current_context = {}
        
        # Save state
        self.save_state()
```

### Learning and Adaptation

```python
class LearningAgent(CustomAgent):
    """Agent that learns from experience."""
    
    def __init__(self, config: Dict[str, Any]):
        super().__init__(config)
        self.success_patterns = {}
        self.failure_patterns = {}
        self.adaptation_rate = config.get('adaptation_rate', 0.1)
    
    async def generate_action(self, observation: Dict[str, Any], context: Dict[str, Any]) -> Dict[str, Any]:
        """Generate action with learning."""
        
        # Check for similar situations in history
        similar_situations = self._find_similar_situations(observation)
        
        if similar_situations:
            # Use learned patterns
            action = self._generate_action_from_patterns(observation, similar_situations)
        else:
            # Use base strategy
            action = await self._generate_base_action(observation, context)
        
        # Record situation-action pair for learning
        self._record_situation_action(observation, action)
        
        return action
    
    def update_from_feedback(self, situation: Dict[str, Any], action: Dict[str, Any], success: bool):
        """Update learning from feedback."""
        situation_key = self._encode_situation(situation)
        action_key = self._encode_action(action)
        
        if success:
            if situation_key not in self.success_patterns:
                self.success_patterns[situation_key] = {}
            
            if action_key not in self.success_patterns[situation_key]:
                self.success_patterns[situation_key][action_key] = 0
            
            self.success_patterns[situation_key][action_key] += self.adaptation_rate
        else:
            if situation_key not in self.failure_patterns:
                self.failure_patterns[situation_key] = {}
            
            if action_key not in self.failure_patterns[situation_key]:
                self.failure_patterns[situation_key][action_key] = 0
            
            self.failure_patterns[situation_key][action_key] += self.adaptation_rate
```

### Multi-Modal Agents

```python
class MultiModalAgent(CustomAgent):
    """Agent that can handle multiple input modalities."""
    
    def __init__(self, config: Dict[str, Any]):
        super().__init__(config)
        self.vision_model = self._initialize_vision_model(config)
        self.text_model = self._initialize_text_model(config)
        self.code_analyzer = self._initialize_code_analyzer(config)
    
    async def generate_action(self, observation: Dict[str, Any], context: Dict[str, Any]) -> Dict[str, Any]:
        """Generate action using multiple modalities."""
        
        # Process different types of input
        text_analysis = await self._analyze_text(observation)
        code_analysis = await self._analyze_code(observation)
        
        if 'image' in observation:
            image_analysis = await self._analyze_image(observation['image'])
        else:
            image_analysis = {}
        
        # Combine analyses
        combined_analysis = self._combine_analyses(text_analysis, code_analysis, image_analysis)
        
        # Generate action based on combined analysis
        action = await self._generate_action_from_analysis(combined_analysis, context)
        
        return action
    
    async def _analyze_text(self, observation: Dict[str, Any]) -> Dict[str, Any]:
        """Analyze textual content."""
        # Implementation for text analysis
        pass
    
    async def _analyze_code(self, observation: Dict[str, Any]) -> Dict[str, Any]:
        """Analyze code content."""
        # Implementation for code analysis
        pass
    
    async def _analyze_image(self, image_data: bytes) -> Dict[str, Any]:
        """Analyze image content."""
        # Implementation for image analysis
        pass
```

## Best Practices

### 1. Error Handling

```python
class RobustAgent(CustomAgent):
    """Agent with comprehensive error handling."""
    
    async def generate_action(self, observation: Dict[str, Any], context: Dict[str, Any]) -> Dict[str, Any]:
        """Generate action with error handling."""
        
        try:
            # Main action generation logic
            action = await self._generate_action_internal(observation, context)
            
            # Validate action
            if not self._validate_action(action):
                raise ValueError("Invalid action generated")
            
            return action
            
        except Exception as e:
            # Log error
            self._log_error(e, observation, context)
            
            # Return safe fallback action
            return self._get_fallback_action(observation, context)
    
    def _validate_action(self, action: Dict[str, Any]) -> bool:
        """Validate action format and content."""
        required_fields = ['type', 'parameters']
        
        if not all(field in action for field in required_fields):
            return False
        
        if not isinstance(action['parameters'], dict):
            return False
        
        return True
    
    def _get_fallback_action(self, observation: Dict[str, Any], context: Dict[str, Any]) -> Dict[str, Any]:
        """Get safe fallback action."""
        return {
            "type": "execute_command",
            "parameters": {"command": "echo 'Agent error, using fallback'"},
            "reasoning": "Fallback action due to agent error",
            "confidence": 0.1
        }
```

### 2. Logging and Monitoring

```python
import logging
from evaluation_engine.monitoring import AgentMonitor

class MonitoredAgent(CustomAgent):
    """Agent with comprehensive logging and monitoring."""
    
    def __init__(self, config: Dict[str, Any]):
        super().__init__(config)
        self.logger = logging.getLogger(f"{self.__class__.__name__}")
        self.monitor = AgentMonitor(agent_name=self.__class__.__name__)
        
        # Set up logging
        self.logger.setLevel(logging.INFO)
        handler = logging.FileHandler(f"{self.__class__.__name__}.log")
        formatter = logging.Formatter('%(asctime)s - %(name)s - %(levelname)s - %(message)s')
        handler.setFormatter(formatter)
        self.logger.addHandler(handler)
    
    async def generate_action(self, observation: Dict[str, Any], context: Dict[str, Any]) -> Dict[str, Any]:
        """Generate action with monitoring."""
        
        start_time = time.time()
        
        try:
            # Log input
            self.logger.info(f"Generating action for turn {context.get('turn_number', 0)}")
            self.logger.debug(f"Observation: {observation}")
            
            # Generate action
            action = await self._generate_action_internal(observation, context)
            
            # Log output
            self.logger.info(f"Generated action: {action['type']}")
            self.logger.debug(f"Full action: {action}")
            
            # Record metrics
            execution_time = time.time() - start_time
            self.monitor.record_action(action, execution_time)
            
            return action
            
        except Exception as e:
            self.logger.error(f"Error generating action: {str(e)}")
            self.monitor.record_error(e)
            raise
```

### 3. Configuration Management

```python
from pydantic import BaseModel, Field
from typing import Optional

class AgentConfig(BaseModel):
    """Configuration model for agents."""
    
    temperature: float = Field(0.7, ge=0.0, le=2.0, description="Sampling temperature")
    max_tokens: int = Field(2000, ge=1, le=8000, description="Maximum tokens per response")
    timeout: int = Field(30, ge=1, le=300, description="Timeout in seconds")
    retry_attempts: int = Field(3, ge=1, le=10, description="Number of retry attempts")
    
    # Strategy configuration
    strategy: str = Field("adaptive", description="Agent strategy")
    exploration_rate: float = Field(0.3, ge=0.0, le=1.0, description="Exploration rate")
    
    # Safety configuration
    enable_safety_checks: bool = Field(True, description="Enable safety checks")
    max_file_size: int = Field(1024*1024, description="Maximum file size to read")
    
    class Config:
        extra = "forbid"  # Prevent additional fields

class ConfigurableAgent(CustomAgent):
    """Agent with structured configuration."""
    
    def __init__(self, config: Dict[str, Any]):
        # Validate configuration
        self.agent_config = AgentConfig(**config)
        super().__init__(config)
    
    def configure(self, config: Dict[str, Any]):
        """Update configuration with validation."""
        new_config = AgentConfig(**{**self.agent_config.dict(), **config})
        self.agent_config = new_config
        self.config.update(config)
```

## Troubleshooting

### Common Issues

1. **Action Format Errors**
   ```python
   # Wrong format
   return "read_file main.py"
   
   # Correct format
   return {
       "type": "read_file",
       "parameters": {"filename": "main.py"}
   }
   ```

2. **Missing Required Methods**
   ```python
   # Must implement all abstract methods
   class MyAgent(CustomAgent):
       async def generate_action(self, observation, context):
           # Implementation required
           pass
       
       def reset(self):
           # Implementation required
           pass
       
       def get_agent_info(self):
           # Implementation required
           pass
   ```

3. **Memory Leaks**
   ```python
   # Clear history periodically
   def _manage_memory(self):
       if len(self.conversation_history) > 1000:
           # Keep only recent history
           self.conversation_history = self.conversation_history[-500:]
   ```

### Debugging Tools

```python
class DebuggableAgent(CustomAgent):
    """Agent with debugging capabilities."""
    
    def __init__(self, config: Dict[str, Any]):
        super().__init__(config)
        self.debug_mode = config.get('debug_mode', False)
        self.action_trace = []
    
    async def generate_action(self, observation: Dict[str, Any], context: Dict[str, Any]) -> Dict[str, Any]:
        """Generate action with debugging."""
        
        if self.debug_mode:
            print(f"DEBUG: Turn {context.get('turn_number', 0)}")
            print(f"DEBUG: Observation keys: {list(observation.keys())}")
            print(f"DEBUG: History length: {len(self.conversation_history)}")
        
        action = await self._generate_action_internal(observation, context)
        
        if self.debug_mode:
            print(f"DEBUG: Generated action: {action['type']}")
            print(f"DEBUG: Action parameters: {action.get('parameters', {})}")
        
        # Record for debugging
        self.action_trace.append({
            'turn': context.get('turn_number', 0),
            'observation_summary': self._summarize_observation(observation),
            'action': action,
            'timestamp': time.time()
        })
        
        return action
    
    def get_debug_info(self) -> Dict[str, Any]:
        """Get debugging information."""
        return {
            'action_trace': self.action_trace,
            'conversation_length': len(self.conversation_history),
            'current_context': self.current_context,
            'agent_config': self.config
        }
```

This comprehensive guide provides everything needed to integrate custom agents into the Multi-Turn Evaluation Engine. Follow the examples and best practices to create robust, efficient, and well-integrated custom agents.