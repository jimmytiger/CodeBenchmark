"""
Test Data Generator for Integration Testing

This module generates comprehensive test data and validation scenarios
for testing the multi-turn evaluation engine.

Requirements: 10.1, 10.2, 10.3, 10.4, 10.5
"""

import json
import random
import string
import tempfile
from pathlib import Path
from typing import Dict, List, Any, Optional, Tuple
from datetime import datetime, timedelta
from dataclasses import asdict

from ..core.data_models import (
    EvaluationConfig, TaskConfig, ModelConfig, MultiTurnConfig,
    EvaluationResult, TurnResult, AggregatedMetrics,
    FeedbackConfig, SafetyConfig
)


class TestDataGenerator:
    """Generate test data for various evaluation scenarios."""
    
    def __init__(self, seed: int = 42):
        """Initialize with random seed for reproducible test data."""
        random.seed(seed)
        self.seed = seed
    
    def generate_model_config(self, 
                            model_id: Optional[str] = None,
                            model_type: Optional[str] = None) -> ModelConfig:
        """Generate a random model configuration."""
        if model_id is None:
            model_id = f"model_{self._random_string(8)}"
        
        if model_type is None:
            model_type = random.choice(["openai", "huggingface", "anthropic", "mock"])
        
        parameters = {}
        if model_type == "openai":
            parameters = {
                "model": random.choice(["gpt-3.5-turbo", "gpt-4", "gpt-4-turbo"]),
                "temperature": round(random.uniform(0.0, 1.0), 2),
                "max_tokens": random.choice([1000, 2000, 4000])
            }
        elif model_type == "huggingface":
            parameters = {
                "pretrained": random.choice([
                    "microsoft/DialoGPT-medium",
                    "microsoft/CodeBERT-base",
                    "codellama/CodeLlama-7b-hf"
                ]),
                "device": random.choice(["cpu", "cuda", "auto"]),
                "torch_dtype": random.choice(["float16", "float32"])
            }
        elif model_type == "anthropic":
            parameters = {
                "model": random.choice(["claude-3-sonnet", "claude-3-haiku"]),
                "max_tokens": random.choice([1000, 4000, 8000])
            }
        else:  # mock
            parameters = {
                "response_delay": round(random.uniform(0.1, 2.0), 2),
                "success_rate": round(random.uniform(0.7, 1.0), 2)
            }
        
        return ModelConfig(
            model_id=model_id,
            model_type=model_type,
            parameters=parameters,
            device=random.choice(["auto", "cpu", "cuda"])
        )
    
    def generate_task_config(self,
                           task_id: Optional[str] = None,
                           task_type: Optional[str] = None,
                           model_ref: Optional[str] = None) -> TaskConfig:
        """Generate a random task configuration."""
        if task_id is None:
            task_id = f"task_{self._random_string(8)}"
        
        if task_type is None:
            task_type = random.choice(["single_turn", "multi_turn"])
        
        if model_ref is None:
            model_ref = f"model_{self._random_string(8)}"
        
        parameters = {}
        if task_type == "single_turn":
            parameters = {
                "num_fewshot": random.choice([0, 1, 3, 5]),
                "batch_size": random.choice([1, 4, 8, 16]),
                "limit": random.choice([None, 10, 50, 100])
            }
        else:  # multi_turn
            parameters = {
                "max_turns": random.choice([5, 10, 15, 20]),
                "timeout": random.choice([300, 600, 1200, 3600]),
                "enable_recovery": random.choice([True, False])
            }
        
        return TaskConfig(
            task_id=task_id,
            task_type=task_type,
            model_ref=model_ref,
            parameters=parameters,
            timeout=random.choice([300, 600, 1200, 3600]),
            max_retries=random.choice([0, 1, 3, 5])
        )
    
    def generate_evaluation_config(self,
                                 num_models: int = 3,
                                 num_tasks: int = 5) -> EvaluationConfig:
        """Generate a complete evaluation configuration."""
        # Generate models
        models = {}
        model_ids = []
        for i in range(num_models):
            model_config = self.generate_model_config()
            models[model_config.model_id] = model_config
            model_ids.append(model_config.model_id)
        
        # Generate tasks
        tasks = []
        for i in range(num_tasks):
            model_ref = random.choice(model_ids)
            task_config = self.generate_task_config(model_ref=model_ref)
            tasks.append(task_config)
        
        # Generate multi-turn config
        multi_turn_config = MultiTurnConfig(
            max_turns=random.choice([5, 10, 15]),
            conversation_timeout=random.choice([600, 1200, 3600]),
            enable_context_retention=random.choice([True, False]),
            termination_conditions=random.sample(
                ["success", "max_turns", "timeout", "safety_violation", "error"],
                k=random.choice([2, 3, 4])
            ),
            feedback_config=FeedbackConfig(
                max_feedback_length=random.choice([5000, 10000, 20000]),
                context_strategy=random.choice(["full", "adaptive", "minimal"]),
                enable_stack_summarization=random.choice([True, False])
            ),
            safety_config=SafetyConfig(
                allowed_tools=random.sample(
                    ["python", "bash", "git", "curl", "wget", "ssh"],
                    k=random.choice([2, 3, 4])
                ),
                max_execution_time=random.choice([60, 120, 300]),
                enable_sandboxing=random.choice([True, False])
            )
        )
        
        # Generate evaluation settings
        evaluation_settings = {
            "output_directory": f"./results_{self._random_string(6)}",
            "save_samples": random.choice([True, False]),
            "enable_caching": random.choice([True, False]),
            "sample_limit": random.choice([None, 10, 50, 100]),
            "parallel_execution": random.choice([True, False]),
            "max_workers": random.choice([1, 2, 4, 8])
        }
        
        return EvaluationConfig(
            models=models,
            tasks=tasks,
            evaluation_settings=evaluation_settings,
            multi_turn_config=multi_turn_config,
            metadata={
                "generated_at": datetime.now().isoformat(),
                "generator_seed": self.seed,
                "version": "1.0"
            }
        )
    
    def generate_turn_result(self, turn: int) -> TurnResult:
        """Generate a random turn result."""
        return TurnResult(
            turn=turn,
            action=f"action_{turn}_{self._random_string(6)}",
            observation=f"observation_{turn}_{self._random_string(10)}",
            reward=round(random.uniform(0.0, 1.0), 3),
            done=random.choice([True, False]) if turn > 3 else False,
            info={
                "step": turn,
                "execution_time": round(random.uniform(0.5, 5.0), 3),
                "tokens_used": random.randint(50, 500),
                "files_modified": random.choice([0, 1, 2, 3]),
                "commands_executed": random.choice([1, 2, 3, 4])
            },
            execution_time=round(random.uniform(0.5, 5.0), 3),
            tokens_used=random.randint(50, 500),
            cost=round(random.uniform(0.001, 0.05), 4),
            safety_violations=[],
            recovery_attempts=random.choice([0, 0, 0, 1, 2])  # Mostly 0
        )
    
    def generate_aggregated_metrics(self) -> AggregatedMetrics:
        """Generate random aggregated metrics."""
        return AggregatedMetrics(
            resolved_percentage=round(random.uniform(0.3, 0.95), 3),
            recall=round(random.uniform(0.2, 0.9), 3),
            mrr=round(random.uniform(0.1, 0.8), 3),
            avg_turns=round(random.uniform(1.0, 10.0), 2),
            avg_steps=round(random.uniform(3.0, 25.0), 2),
            redundancy_rate=round(random.uniform(0.0, 0.3), 3),
            edit_churn=round(random.uniform(0.0, 5.0), 2),
            files_touched=random.randint(0, 10),
            recovery_rate=round(random.uniform(0.5, 1.0), 3),
            stability_score=round(random.uniform(0.6, 1.0), 3),
            wall_time_per_solved=round(random.uniform(10.0, 300.0), 2),
            tokens_per_solved=random.randint(100, 5000),
            cost_per_solved=round(random.uniform(0.01, 1.0), 4),
            safety_incidents=random.choice([0, 0, 0, 1, 2]),  # Mostly 0
            policy_violations=random.choice([0, 0, 0, 1])  # Mostly 0
        )
    
    def generate_evaluation_result(self,
                                 task_id: Optional[str] = None,
                                 model_id: Optional[str] = None,
                                 num_turns: Optional[int] = None) -> EvaluationResult:
        """Generate a random evaluation result."""
        if task_id is None:
            task_id = f"task_{self._random_string(8)}"
        
        if model_id is None:
            model_id = f"model_{self._random_string(8)}"
        
        if num_turns is None:
            num_turns = random.randint(1, 10)
        
        # Generate turn results
        turn_results = []
        for turn in range(1, num_turns + 1):
            turn_result = self.generate_turn_result(turn)
            turn_results.append(turn_result)
        
        # Determine success based on last turn
        success = turn_results[-1].done and turn_results[-1].reward > 0.5
        
        return EvaluationResult(
            evaluation_id=f"eval_{self._random_string(12)}",
            task_id=task_id,
            model_id=model_id,
            start_time=datetime.now() - timedelta(minutes=random.randint(5, 60)),
            end_time=datetime.now(),
            success=success,
            total_turns=num_turns,
            turn_results=turn_results,
            aggregated_metrics=self.generate_aggregated_metrics(),
            metadata={
                "environment": "test",
                "generated": True,
                "seed": self.seed
            }
        )
    
    def generate_legacy_config(self) -> Dict[str, Any]:
        """Generate a legacy-style configuration."""
        return {
            'model': random.choice(['hf', 'openai', 'anthropic']),
            'model_args': {
                'pretrained': random.choice([
                    'gpt2', 'microsoft/DialoGPT-medium', 'codellama/CodeLlama-7b-hf'
                ]),
                'device': random.choice(['cpu', 'cuda', 'auto']),
                'temperature': round(random.uniform(0.0, 1.0), 2)
            },
            'tasks': ','.join([
                random.choice(['hellaswag', 'arc_easy', 'arc_challenge']),
                random.choice(['winogrande', 'piqa', 'boolq']),
                random.choice(['swe_bench_lite', 'intercode_python'])
            ]),
            'num_fewshot': random.choice([0, 1, 3, 5]),
            'batch_size': random.choice([1, 4, 8, 16]),
            'output_path': f'./results_{self._random_string(6)}',
            'log_samples': random.choice([True, False]),
            'use_cache': random.choice([True, False]),
            'device': random.choice(['cpu', 'cuda', 'auto']),
            'limit': random.choice([None, 10, 50, 100])
        }
    
    def _random_string(self, length: int) -> str:
        """Generate a random string of given length."""
        return ''.join(random.choices(string.ascii_lowercase + string.digits, k=length))


class TestScenarioGenerator:
    """Generate specific test scenarios for validation."""
    
    def __init__(self):
        self.generator = TestDataGenerator()
    
    def generate_single_turn_scenario(self) -> Tuple[EvaluationConfig, List[str]]:
        """Generate a single-turn evaluation scenario."""
        # Create models
        models = {
            "gpt2": ModelConfig(
                model_id="gpt2",
                model_type="huggingface",
                parameters={"pretrained": "gpt2", "device": "cpu"}
            ),
            "mock_model": ModelConfig(
                model_id="mock_model",
                model_type="mock",
                parameters={"success_rate": 0.8}
            )
        }
        
        # Create single-turn tasks
        tasks = [
            TaskConfig(
                task_id="hellaswag",
                task_type="single_turn",
                model_ref="gpt2",
                parameters={"num_fewshot": 5, "batch_size": 8}
            ),
            TaskConfig(
                task_id="arc_easy",
                task_type="single_turn",
                model_ref="mock_model",
                parameters={"num_fewshot": 0, "batch_size": 1}
            )
        ]
        
        config = EvaluationConfig(
            models=models,
            tasks=tasks,
            evaluation_settings={
                "output_directory": "./single_turn_results",
                "save_samples": True
            }
        )
        
        expected_tasks = ["hellaswag", "arc_easy"]
        return config, expected_tasks
    
    def generate_multi_turn_scenario(self) -> Tuple[EvaluationConfig, List[str]]:
        """Generate a multi-turn evaluation scenario."""
        # Create models
        models = {
            "gpt4": ModelConfig(
                model_id="gpt4",
                model_type="openai",
                parameters={"model": "gpt-4", "temperature": 0.7}
            )
        }
        
        # Create multi-turn tasks
        tasks = [
            TaskConfig(
                task_id="swe_bench_lite",
                task_type="multi_turn",
                model_ref="gpt4",
                parameters={"max_turns": 10, "timeout": 1800}
            ),
            TaskConfig(
                task_id="intercode_python",
                task_type="multi_turn",
                model_ref="gpt4",
                parameters={"max_turns": 5, "timeout": 600}
            )
        ]
        
        # Multi-turn configuration
        multi_turn_config = MultiTurnConfig(
            max_turns=15,
            conversation_timeout=3600,
            enable_context_retention=True,
            termination_conditions=["success", "max_turns", "timeout"],
            feedback_config=FeedbackConfig(
                max_feedback_length=10000,
                context_strategy="adaptive",
                enable_stack_summarization=True
            ),
            safety_config=SafetyConfig(
                allowed_tools=["python", "bash", "git"],
                max_execution_time=300,
                enable_sandboxing=True
            )
        )
        
        config = EvaluationConfig(
            models=models,
            tasks=tasks,
            multi_turn_config=multi_turn_config,
            evaluation_settings={
                "output_directory": "./multi_turn_results",
                "save_samples": True,
                "enable_caching": False
            }
        )
        
        expected_tasks = ["swe_bench_lite", "intercode_python"]
        return config, expected_tasks
    
    def generate_mixed_scenario(self) -> Tuple[EvaluationConfig, Dict[str, List[str]]]:
        """Generate a mixed single-turn and multi-turn scenario."""
        # Create models
        models = {
            "gpt35": ModelConfig(
                model_id="gpt35",
                model_type="openai",
                parameters={"model": "gpt-3.5-turbo"}
            ),
            "claude": ModelConfig(
                model_id="claude",
                model_type="anthropic",
                parameters={"model": "claude-3-sonnet"}
            )
        }
        
        # Create mixed tasks
        tasks = [
            # Single-turn tasks
            TaskConfig(
                task_id="hellaswag",
                task_type="single_turn",
                model_ref="gpt35",
                parameters={"num_fewshot": 3}
            ),
            TaskConfig(
                task_id="winogrande",
                task_type="single_turn",
                model_ref="claude",
                parameters={"num_fewshot": 5}
            ),
            # Multi-turn tasks
            TaskConfig(
                task_id="swe_bench_lite",
                task_type="multi_turn",
                model_ref="gpt35",
                parameters={"max_turns": 8}
            ),
            TaskConfig(
                task_id="convcode_bench",
                task_type="multi_turn",
                model_ref="claude",
                parameters={"max_turns": 12}
            )
        ]
        
        config = EvaluationConfig(
            models=models,
            tasks=tasks,
            multi_turn_config=MultiTurnConfig(),
            evaluation_settings={
                "output_directory": "./mixed_results",
                "parallel_execution": True,
                "max_workers": 2
            }
        )
        
        expected_tasks = {
            "single_turn": ["hellaswag", "winogrande"],
            "multi_turn": ["swe_bench_lite", "convcode_bench"]
        }
        return config, expected_tasks
    
    def generate_error_scenarios(self) -> List[Tuple[str, EvaluationConfig, str]]:
        """Generate scenarios that should produce specific errors."""
        scenarios = []
        
        # Scenario 1: Empty models
        config1 = EvaluationConfig(
            models={},
            tasks=[TaskConfig(
                task_id="test",
                task_type="single_turn",
                model_ref="nonexistent"
            )]
        )
        scenarios.append(("empty_models", config1, "At least one model must be configured"))
        
        # Scenario 2: Empty tasks
        config2 = EvaluationConfig(
            models={"test": ModelConfig(model_id="test", model_type="mock")},
            tasks=[]
        )
        scenarios.append(("empty_tasks", config2, "At least one task must be configured"))
        
        # Scenario 3: Invalid model reference
        config3 = EvaluationConfig(
            models={"model1": ModelConfig(model_id="model1", model_type="mock")},
            tasks=[TaskConfig(
                task_id="test",
                task_type="single_turn",
                model_ref="nonexistent_model"
            )]
        )
        scenarios.append(("invalid_model_ref", config3, "references unknown model"))
        
        # Scenario 4: Invalid task type
        try:
            config4 = EvaluationConfig(
                models={"model1": ModelConfig(model_id="model1", model_type="mock")},
                tasks=[TaskConfig(
                    task_id="test",
                    task_type="invalid_type",
                    model_ref="model1"
                )]
            )
            scenarios.append(("invalid_task_type", config4, "task_type must be"))
        except ValueError:
            # This might fail at creation time, which is also valid
            pass
        
        return scenarios
    
    def save_test_data_to_files(self, output_dir: str) -> Dict[str, str]:
        """Save generated test data to files for use in tests."""
        output_path = Path(output_dir)
        output_path.mkdir(parents=True, exist_ok=True)
        
        files_created = {}
        
        # Generate and save configurations
        for i in range(5):
            config = self.generator.generate_evaluation_config()
            config_file = output_path / f"test_config_{i}.json"
            
            # Convert to serializable format
            config_dict = {
                "models": {k: {
                    "model_id": v.model_id,
                    "model_type": v.model_type,
                    "parameters": v.parameters,
                    "device": v.device
                } for k, v in config.models.items()},
                "tasks": [{
                    "task_id": t.task_id,
                    "task_type": t.task_type,
                    "model_ref": t.model_ref,
                    "parameters": t.parameters,
                    "timeout": t.timeout,
                    "max_retries": t.max_retries
                } for t in config.tasks],
                "evaluation_settings": config.evaluation_settings,
                "metadata": config.metadata
            }
            
            with open(config_file, 'w') as f:
                json.dump(config_dict, f, indent=2)
            
            files_created[f"config_{i}"] = str(config_file)
        
        # Generate and save legacy configurations
        for i in range(3):
            legacy_config = self.generator.generate_legacy_config()
            legacy_file = output_path / f"legacy_config_{i}.json"
            
            with open(legacy_file, 'w') as f:
                json.dump(legacy_config, f, indent=2)
            
            files_created[f"legacy_config_{i}"] = str(legacy_file)
        
        # Generate and save evaluation results
        for i in range(3):
            result = self.generator.generate_evaluation_result()
            result_file = output_path / f"test_result_{i}.json"
            
            # Convert to serializable format
            result_dict = {
                "evaluation_id": result.evaluation_id,
                "task_id": result.task_id,
                "model_id": result.model_id,
                "start_time": result.start_time.isoformat(),
                "end_time": result.end_time.isoformat(),
                "success": result.success,
                "total_turns": result.total_turns,
                "turn_results": [tr.to_dict() for tr in result.turn_results],
                "aggregated_metrics": asdict(result.aggregated_metrics),
                "metadata": result.metadata
            }
            
            with open(result_file, 'w') as f:
                json.dump(result_dict, f, indent=2)
            
            files_created[f"result_{i}"] = str(result_file)
        
        return files_created


if __name__ == '__main__':
    # Generate test data for manual inspection
    generator = TestDataGenerator()
    scenario_generator = TestScenarioGenerator()
    
    print("Generating test data...")
    
    # Generate sample configurations
    config = generator.generate_evaluation_config(num_models=2, num_tasks=4)
    print(f"Generated config with {len(config.models)} models and {len(config.tasks)} tasks")
    
    # Generate scenarios
    single_turn_config, single_turn_tasks = scenario_generator.generate_single_turn_scenario()
    print(f"Single-turn scenario: {single_turn_tasks}")
    
    multi_turn_config, multi_turn_tasks = scenario_generator.generate_multi_turn_scenario()
    print(f"Multi-turn scenario: {multi_turn_tasks}")
    
    mixed_config, mixed_tasks = scenario_generator.generate_mixed_scenario()
    print(f"Mixed scenario: {mixed_tasks}")
    
    # Generate error scenarios
    error_scenarios = scenario_generator.generate_error_scenarios()
    print(f"Generated {len(error_scenarios)} error scenarios")
    
    # Save to temporary directory
    with tempfile.TemporaryDirectory() as temp_dir:
        files = scenario_generator.save_test_data_to_files(temp_dir)
        print(f"Saved {len(files)} test data files to {temp_dir}")
        for name, path in files.items():
            print(f"  {name}: {path}")
    
    print("Test data generation complete!")