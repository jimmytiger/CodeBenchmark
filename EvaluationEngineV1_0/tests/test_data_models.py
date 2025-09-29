"""
Unit tests for core data models.

This module tests all data models including validation, serialization,
and configuration handling.
"""

import json
import pytest
from datetime import datetime, timedelta
from typing import Dict, Any

from EvaluationEngineV1_0.core.data_models import (
    TerminationReason,
    ContextStrategy,
    ProcessedFeedback,
    EvaluationResult,
    AggregatedMetrics,
    StandardizedOutput,
    FeedbackConfig,
    SafetyConfig,
    MultiTurnConfig,
    TurnResult,
    DataValidator
)


class TestTerminationReason:
    """Test TerminationReason enum."""
    
    def test_all_values(self):
        """Test all enum values are accessible."""
        assert TerminationReason.SUCCESS.value == "success"
        assert TerminationReason.MAX_TURNS.value == "max_turns"
        assert TerminationReason.TIMEOUT.value == "timeout"
        assert TerminationReason.SAFETY_VIOLATION.value == "safety_violation"
        assert TerminationReason.ERROR.value == "error"
        assert TerminationReason.USER_REQUESTED.value == "user_requested"


class TestContextStrategy:
    """Test ContextStrategy enum."""
    
    def test_all_values(self):
        """Test all enum values are accessible."""
        assert ContextStrategy.FULL.value == "full"
        assert ContextStrategy.ADAPTIVE.value == "adaptive"
        assert ContextStrategy.MINIMAL.value == "minimal"
        assert ContextStrategy.SLIDING_WINDOW.value == "sliding_window"


class TestProcessedFeedback:
    """Test ProcessedFeedback data model."""
    
    def test_creation(self):
        """Test basic creation."""
        original = {"stdout": "test output"}
        filtered = {"stdout": "test output"}
        contextualized = {"stdout": "test output", "context": "added"}
        final = {"stdout": "test output", "context": "added", "summary": "final"}
        
        feedback = ProcessedFeedback(
            original=original,
            filtered=filtered,
            contextualized=contextualized,
            final=final,
            processing_time=0.5,
            truncated=True
        )
        
        assert feedback.original == original
        assert feedback.filtered == filtered
        assert feedback.contextualized == contextualized
        assert feedback.final == final
        assert feedback.processing_time == 0.5
        assert feedback.truncated is True
        assert isinstance(feedback.timestamp, datetime)
    
    def test_default_values(self):
        """Test default values are set correctly."""
        feedback = ProcessedFeedback(
            original={},
            filtered={},
            contextualized={},
            final={}
        )
        
        assert feedback.processing_time == 0.0
        assert feedback.truncated is False
        assert isinstance(feedback.timestamp, datetime)


class TestAggregatedMetrics:
    """Test AggregatedMetrics data model."""
    
    def test_creation_with_defaults(self):
        """Test creation with default values."""
        metrics = AggregatedMetrics()
        
        # Task Success Metrics
        assert metrics.resolved_percentage == 0.0
        assert metrics.recall == 0.0
        assert metrics.mrr == 0.0
        
        # Efficiency Metrics
        assert metrics.avg_turns == 0.0
        assert metrics.avg_steps == 0.0
        assert metrics.redundancy_rate == 0.0
        
        # Repair Quality Metrics
        assert metrics.edit_churn == 0.0
        assert metrics.files_touched == 0
        
        # Robustness Metrics
        assert metrics.recovery_rate == 0.0
        assert metrics.stability_score == 0.0
        
        # Cost Metrics
        assert metrics.wall_time_per_solved == 0.0
        assert metrics.tokens_per_solved == 0
        assert metrics.cost_per_solved == 0.0
        
        # Safety Metrics
        assert metrics.safety_incidents == 0
        assert metrics.policy_violations == 0
    
    def test_creation_with_values(self):
        """Test creation with specific values."""
        metrics = AggregatedMetrics(
            resolved_percentage=85.5,
            recall=0.92,
            mrr=0.78,
            avg_turns=3.2,
            avg_steps=12.5,
            redundancy_rate=0.15,
            edit_churn=2.3,
            files_touched=5,
            recovery_rate=0.88,
            stability_score=0.95,
            wall_time_per_solved=45.2,
            tokens_per_solved=1250,
            cost_per_solved=0.025,
            safety_incidents=1,
            policy_violations=0
        )
        
        assert metrics.resolved_percentage == 85.5
        assert metrics.recall == 0.92
        assert metrics.mrr == 0.78
        assert metrics.avg_turns == 3.2
        assert metrics.avg_steps == 12.5
        assert metrics.redundancy_rate == 0.15
        assert metrics.edit_churn == 2.3
        assert metrics.files_touched == 5
        assert metrics.recovery_rate == 0.88
        assert metrics.stability_score == 0.95
        assert metrics.wall_time_per_solved == 45.2
        assert metrics.tokens_per_solved == 1250
        assert metrics.cost_per_solved == 0.025
        assert metrics.safety_incidents == 1
        assert metrics.policy_violations == 0
    
    def test_to_dict(self):
        """Test conversion to dictionary."""
        metrics = AggregatedMetrics(
            resolved_percentage=85.5,
            recall=0.92,
            files_touched=5,
            safety_incidents=1
        )
        
        result = metrics.to_dict()
        
        assert isinstance(result, dict)
        assert result['resolved_percentage'] == 85.5
        assert result['recall'] == 0.92
        assert result['files_touched'] == 5
        assert result['safety_incidents'] == 1
        assert len(result) == 15  # All metrics included
    
    def test_from_dict(self):
        """Test creation from dictionary."""
        data = {
            'resolved_percentage': 85.5,
            'recall': 0.92,
            'mrr': 0.78,
            'avg_turns': 3.2,
            'avg_steps': 12.5,
            'redundancy_rate': 0.15,
            'edit_churn': 2.3,
            'files_touched': 5,
            'recovery_rate': 0.88,
            'stability_score': 0.95,
            'wall_time_per_solved': 45.2,
            'tokens_per_solved': 1250,
            'cost_per_solved': 0.025,
            'safety_incidents': 1,
            'policy_violations': 0
        }
        
        metrics = AggregatedMetrics.from_dict(data)
        
        assert metrics.resolved_percentage == 85.5
        assert metrics.recall == 0.92
        assert metrics.files_touched == 5
        assert metrics.safety_incidents == 1


class TestEvaluationResult:
    """Test EvaluationResult data model."""
    
    def test_creation(self):
        """Test basic creation."""
        start_time = datetime.now()
        end_time = start_time + timedelta(seconds=30)
        
        turn_results = [
            TurnResult(
                turn=1,
                action="test_action",
                observation="test_obs",
                reward=0.5,
                done=False,
                info={},
                execution_time=5.0
            )
        ]
        
        metrics = AggregatedMetrics(resolved_percentage=100.0)
        
        result = EvaluationResult(
            evaluation_id="eval_123",
            task_id="task_456",
            model_id="model_789",
            start_time=start_time,
            end_time=end_time,
            success=True,
            total_turns=1,
            turn_results=turn_results,
            final_metrics={"score": 0.85},
            aggregated_metrics=metrics,
            termination_reason=TerminationReason.SUCCESS
        )
        
        assert result.evaluation_id == "eval_123"
        assert result.task_id == "task_456"
        assert result.model_id == "model_789"
        assert result.start_time == start_time
        assert result.end_time == end_time
        assert result.success is True
        assert result.total_turns == 1
        assert len(result.turn_results) == 1
        assert result.final_metrics == {"score": 0.85}
        assert result.aggregated_metrics == metrics
        assert result.termination_reason == TerminationReason.SUCCESS
    
    def test_duration_property(self):
        """Test duration calculation."""
        start_time = datetime.now()
        end_time = start_time + timedelta(seconds=45)
        
        result = EvaluationResult(
            evaluation_id="eval_123",
            task_id="task_456",
            model_id="model_789",
            start_time=start_time,
            end_time=end_time,
            success=True,
            total_turns=1,
            turn_results=[],
            final_metrics={},
            aggregated_metrics=AggregatedMetrics(),
            termination_reason=TerminationReason.SUCCESS
        )
        
        assert result.duration == 45.0
    
    def test_to_dict(self):
        """Test conversion to dictionary."""
        start_time = datetime.now()
        end_time = start_time + timedelta(seconds=30)
        
        result = EvaluationResult(
            evaluation_id="eval_123",
            task_id="task_456",
            model_id="model_789",
            start_time=start_time,
            end_time=end_time,
            success=True,
            total_turns=1,
            turn_results=[],
            final_metrics={"score": 0.85},
            aggregated_metrics=AggregatedMetrics(),
            termination_reason=TerminationReason.SUCCESS
        )
        
        result_dict = result.to_dict()
        
        assert isinstance(result_dict, dict)
        assert result_dict['evaluation_id'] == "eval_123"
        assert result_dict['task_id'] == "task_456"
        assert result_dict['model_id'] == "model_789"
        assert result_dict['success'] is True
        assert result_dict['total_turns'] == 1
        assert result_dict['duration'] == 30.0
        assert result_dict['termination_reason'] == "success"
        assert 'aggregated_metrics' in result_dict
    
    def test_to_json(self):
        """Test JSON serialization."""
        start_time = datetime.now()
        end_time = start_time + timedelta(seconds=30)
        
        result = EvaluationResult(
            evaluation_id="eval_123",
            task_id="task_456",
            model_id="model_789",
            start_time=start_time,
            end_time=end_time,
            success=True,
            total_turns=1,
            turn_results=[],
            final_metrics={"score": 0.85},
            aggregated_metrics=AggregatedMetrics(),
            termination_reason=TerminationReason.SUCCESS
        )
        
        json_str = result.to_json()
        
        assert isinstance(json_str, str)
        parsed = json.loads(json_str)
        assert parsed['evaluation_id'] == "eval_123"
        assert parsed['success'] is True


class TestStandardizedOutput:
    """Test StandardizedOutput data model."""
    
    def test_creation(self):
        """Test basic creation."""
        output = StandardizedOutput(
            run_id="run_123",
            task_id="task_456",
            sample_id="sample_789",
            success=True,
            turns=3,
            steps=15,
            wall_time_s=45.2,
            token_in=500,
            token_out=200,
            cost_usd=0.025,
            files_touched=2,
            edit_added=50,
            edit_deleted=10,
            redundancy_rate=0.15,
            recovered=True,
            safety_incidents=0,
            notes="Test completed successfully"
        )
        
        assert output.run_id == "run_123"
        assert output.task_id == "task_456"
        assert output.sample_id == "sample_789"
        assert output.success is True
        assert output.turns == 3
        assert output.steps == 15
        assert output.wall_time_s == 45.2
        assert output.token_in == 500
        assert output.token_out == 200
        assert output.cost_usd == 0.025
        assert output.files_touched == 2
        assert output.edit_added == 50
        assert output.edit_deleted == 10
        assert output.redundancy_rate == 0.15
        assert output.recovered is True
        assert output.safety_incidents == 0
        assert output.notes == "Test completed successfully"
        assert isinstance(output.timestamp, datetime)
    
    def test_csv_headers(self):
        """Test CSV headers."""
        headers = StandardizedOutput.csv_headers()
        
        expected_headers = [
            'run_id', 'task_id', 'sample_id', 'success', 'turns', 'steps',
            'wall_time_s', 'token_in', 'token_out', 'cost_usd', 'files_touched',
            'edit_added', 'edit_deleted', 'redundancy_rate', 'recovered',
            'safety_incidents', 'notes', 'timestamp'
        ]
        
        assert headers == expected_headers
    
    def test_to_csv_row(self):
        """Test CSV row conversion."""
        output = StandardizedOutput(
            run_id="run_123",
            task_id="task_456",
            sample_id="sample_789",
            success=True,
            turns=3,
            steps=15,
            wall_time_s=45.2,
            token_in=500,
            token_out=200,
            cost_usd=0.025,
            files_touched=2,
            edit_added=50,
            edit_deleted=10,
            redundancy_rate=0.15,
            recovered=True,
            safety_incidents=0,
            notes="Test note"
        )
        
        row = output.to_csv_row()
        
        assert len(row) == 18  # All fields including timestamp
        assert row[0] == "run_123"
        assert row[1] == "task_456"
        assert row[2] == "sample_789"
        assert row[3] == "True"
        assert row[4] == "3"
        assert row[5] == "15"
        assert row[6] == "45.2"
        assert row[16] == "Test note"
    
    def test_to_dict(self):
        """Test dictionary conversion."""
        output = StandardizedOutput(
            run_id="run_123",
            task_id="task_456",
            sample_id="sample_789",
            success=True,
            turns=3,
            steps=15,
            wall_time_s=45.2,
            token_in=500,
            token_out=200,
            cost_usd=0.025,
            files_touched=2,
            edit_added=50,
            edit_deleted=10,
            redundancy_rate=0.15,
            recovered=True,
            safety_incidents=0
        )
        
        result = output.to_dict()
        
        assert isinstance(result, dict)
        assert result['run_id'] == "run_123"
        assert result['success'] is True
        assert result['turns'] == 3
        assert 'timestamp' in result


class TestFeedbackConfig:
    """Test FeedbackConfig data model."""
    
    def test_creation_with_defaults(self):
        """Test creation with default values."""
        config = FeedbackConfig()
        
        assert config.max_feedback_length == 10000
        assert config.context_strategy == ContextStrategy.ADAPTIVE
        assert config.max_context_length == 50000
        assert config.enable_stack_summarization is True
        assert config.enable_file_context is True
        assert config.top_k_assertions == 5
        assert config.truncation_strategy == "intelligent"
        assert config.preserve_error_info is True
    
    def test_creation_with_values(self):
        """Test creation with specific values."""
        config = FeedbackConfig(
            max_feedback_length=5000,
            context_strategy=ContextStrategy.MINIMAL,
            max_context_length=25000,
            enable_stack_summarization=False,
            enable_file_context=False,
            top_k_assertions=3,
            truncation_strategy="tail",
            preserve_error_info=False
        )
        
        assert config.max_feedback_length == 5000
        assert config.context_strategy == ContextStrategy.MINIMAL
        assert config.max_context_length == 25000
        assert config.enable_stack_summarization is False
        assert config.enable_file_context is False
        assert config.top_k_assertions == 3
        assert config.truncation_strategy == "tail"
        assert config.preserve_error_info is False
    
    def test_validation_success(self):
        """Test successful validation."""
        config = FeedbackConfig()
        assert config.validate() is True
    
    def test_validation_failures(self):
        """Test validation failures."""
        # Test negative max_feedback_length
        with pytest.raises(ValueError, match="max_feedback_length must be positive"):
            config = FeedbackConfig(max_feedback_length=-1)
            config.validate()
        
        # Test negative max_context_length
        with pytest.raises(ValueError, match="max_context_length must be positive"):
            config = FeedbackConfig(max_context_length=-1)
            config.validate()
        
        # Test negative top_k_assertions
        with pytest.raises(ValueError, match="top_k_assertions must be positive"):
            config = FeedbackConfig(top_k_assertions=-1)
            config.validate()
        
        # Test invalid truncation_strategy
        with pytest.raises(ValueError, match="Invalid truncation_strategy"):
            config = FeedbackConfig(truncation_strategy="invalid")
            config.validate()


class TestSafetyConfig:
    """Test SafetyConfig data model."""
    
    def test_creation_with_defaults(self):
        """Test creation with default values."""
        config = SafetyConfig()
        
        assert config.allowed_tools == ["python", "bash", "git"]
        assert config.enable_sandboxing is True
        assert config.max_execution_time == 300
        assert config.max_memory_mb == 1024
        assert config.max_disk_mb == 1024
        assert config.network_access is False
        assert config.file_system_access == "restricted"
        
        # Check default resource limits
        assert "max_processes" in config.resource_limits
        assert "max_open_files" in config.resource_limits
        assert "max_cpu_percent" in config.resource_limits
        
        # Check default dangerous patterns
        assert len(config.dangerous_patterns) > 0
        assert any("rm" in pattern for pattern in config.dangerous_patterns)
    
    def test_creation_with_values(self):
        """Test creation with specific values."""
        config = SafetyConfig(
            allowed_tools=["python"],
            resource_limits={"custom": "limit"},
            dangerous_patterns=["custom_pattern"],
            enable_sandboxing=False,
            max_execution_time=600,
            max_memory_mb=2048,
            max_disk_mb=2048,
            network_access=True,
            file_system_access="full"
        )
        
        assert config.allowed_tools == ["python"]
        assert config.resource_limits == {"custom": "limit"}
        assert config.dangerous_patterns == ["custom_pattern"]
        assert config.enable_sandboxing is False
        assert config.max_execution_time == 600
        assert config.max_memory_mb == 2048
        assert config.max_disk_mb == 2048
        assert config.network_access is True
        assert config.file_system_access == "full"
    
    def test_validation_success(self):
        """Test successful validation."""
        config = SafetyConfig()
        assert config.validate() is True
    
    def test_validation_failures(self):
        """Test validation failures."""
        # Test negative max_execution_time
        with pytest.raises(ValueError, match="max_execution_time must be positive"):
            config = SafetyConfig(max_execution_time=-1)
            config.validate()
        
        # Test negative max_memory_mb
        with pytest.raises(ValueError, match="max_memory_mb must be positive"):
            config = SafetyConfig(max_memory_mb=-1)
            config.validate()
        
        # Test negative max_disk_mb
        with pytest.raises(ValueError, match="max_disk_mb must be positive"):
            config = SafetyConfig(max_disk_mb=-1)
            config.validate()
        
        # Test invalid file_system_access
        with pytest.raises(ValueError, match="Invalid file_system_access value"):
            config = SafetyConfig(file_system_access="invalid")
            config.validate()


class TestMultiTurnConfig:
    """Test MultiTurnConfig data model."""
    
    def test_creation_with_defaults(self):
        """Test creation with default values."""
        config = MultiTurnConfig()
        
        assert config.max_turns == 10
        assert config.conversation_timeout == 3600
        assert config.enable_context_retention is True
        assert config.termination_conditions == ["success", "max_turns", "timeout"]
        assert isinstance(config.feedback_config, FeedbackConfig)
        assert isinstance(config.safety_config, SafetyConfig)
        assert config.enable_recovery is True
        assert config.recovery_max_attempts == 3
    
    def test_creation_with_values(self):
        """Test creation with specific values."""
        feedback_config = FeedbackConfig(max_feedback_length=5000)
        safety_config = SafetyConfig(max_execution_time=600)
        
        config = MultiTurnConfig(
            max_turns=5,
            conversation_timeout=1800,
            enable_context_retention=False,
            termination_conditions=["success", "error"],
            feedback_config=feedback_config,
            safety_config=safety_config,
            enable_recovery=False,
            recovery_max_attempts=1
        )
        
        assert config.max_turns == 5
        assert config.conversation_timeout == 1800
        assert config.enable_context_retention is False
        assert config.termination_conditions == ["success", "error"]
        assert config.feedback_config == feedback_config
        assert config.safety_config == safety_config
        assert config.enable_recovery is False
        assert config.recovery_max_attempts == 1
    
    def test_validation_success(self):
        """Test successful validation."""
        config = MultiTurnConfig()
        assert config.validate() is True
    
    def test_validation_failures(self):
        """Test validation failures."""
        # Test negative max_turns
        with pytest.raises(ValueError, match="max_turns must be positive"):
            config = MultiTurnConfig(max_turns=-1)
            config.validate()
        
        # Test negative conversation_timeout
        with pytest.raises(ValueError, match="conversation_timeout must be positive"):
            config = MultiTurnConfig(conversation_timeout=-1)
            config.validate()
        
        # Test negative recovery_max_attempts
        with pytest.raises(ValueError, match="recovery_max_attempts must be non-negative"):
            config = MultiTurnConfig(recovery_max_attempts=-1)
            config.validate()
        
        # Test invalid termination condition
        with pytest.raises(ValueError, match="Invalid termination condition"):
            config = MultiTurnConfig(termination_conditions=["invalid_condition"])
            config.validate()


class TestTurnResult:
    """Test enhanced TurnResult data model."""
    
    def test_creation(self):
        """Test basic creation."""
        processed_feedback = ProcessedFeedback(
            original={},
            filtered={},
            contextualized={},
            final={}
        )
        
        result = TurnResult(
            turn=1,
            action="test_action",
            observation="test_observation",
            reward=0.5,
            done=False,
            info={"key": "value"},
            execution_time=2.5,
            processed_feedback=processed_feedback,
            tokens_used=100,
            cost=0.01,
            safety_violations=["violation1"],
            recovery_attempts=1
        )
        
        assert result.turn == 1
        assert result.action == "test_action"
        assert result.observation == "test_observation"
        assert result.reward == 0.5
        assert result.done is False
        assert result.info == {"key": "value"}
        assert result.execution_time == 2.5
        assert result.processed_feedback == processed_feedback
        assert result.tokens_used == 100
        assert result.cost == 0.01
        assert result.safety_violations == ["violation1"]
        assert result.recovery_attempts == 1
        assert isinstance(result.timestamp, datetime)
    
    def test_default_values(self):
        """Test default values."""
        result = TurnResult(
            turn=1,
            action="test",
            observation="test",
            reward=0.0,
            done=False,
            info={},
            execution_time=1.0
        )
        
        assert result.processed_feedback is None
        assert result.tokens_used == 0
        assert result.cost == 0.0
        assert result.safety_violations == []
        assert result.recovery_attempts == 0
        assert isinstance(result.timestamp, datetime)
    
    def test_to_dict(self):
        """Test dictionary conversion."""
        result = TurnResult(
            turn=1,
            action="test_action",
            observation="test_observation",
            reward=0.5,
            done=False,
            info={"key": "value"},
            execution_time=2.5,
            tokens_used=100,
            cost=0.01,
            safety_violations=["violation1"],
            recovery_attempts=1
        )
        
        result_dict = result.to_dict()
        
        assert isinstance(result_dict, dict)
        assert result_dict['turn'] == 1
        assert result_dict['action'] == "test_action"
        assert result_dict['observation'] == "test_observation"
        assert result_dict['reward'] == 0.5
        assert result_dict['done'] is False
        assert result_dict['info'] == {"key": "value"}
        assert result_dict['execution_time'] == 2.5
        assert result_dict['tokens_used'] == 100
        assert result_dict['cost'] == 0.01
        assert result_dict['safety_violations'] == ["violation1"]
        assert result_dict['recovery_attempts'] == 1
        assert 'timestamp' in result_dict


class TestDataValidator:
    """Test DataValidator utility class."""
    
    def test_validate_evaluation_result_success(self):
        """Test successful evaluation result validation."""
        start_time = datetime.now()
        end_time = start_time + timedelta(seconds=30)
        
        turn_results = [
            TurnResult(
                turn=1,
                action="test",
                observation="test",
                reward=0.5,
                done=True,
                info={},
                execution_time=1.0
            )
        ]
        
        result = EvaluationResult(
            evaluation_id="eval_123",
            task_id="task_456",
            model_id="model_789",
            start_time=start_time,
            end_time=end_time,
            success=True,
            total_turns=1,
            turn_results=turn_results,
            final_metrics={},
            aggregated_metrics=AggregatedMetrics(),
            termination_reason=TerminationReason.SUCCESS
        )
        
        assert DataValidator.validate_evaluation_result(result) is True
    
    def test_validate_evaluation_result_failures(self):
        """Test evaluation result validation failures."""
        start_time = datetime.now()
        end_time = start_time + timedelta(seconds=30)
        
        # Test empty evaluation_id
        with pytest.raises(ValueError, match="evaluation_id cannot be empty"):
            result = EvaluationResult(
                evaluation_id="",
                task_id="task_456",
                model_id="model_789",
                start_time=start_time,
                end_time=end_time,
                success=True,
                total_turns=0,
                turn_results=[],
                final_metrics={},
                aggregated_metrics=AggregatedMetrics(),
                termination_reason=TerminationReason.SUCCESS
            )
            DataValidator.validate_evaluation_result(result)
        
        # Test start_time after end_time
        with pytest.raises(ValueError, match="start_time cannot be after end_time"):
            result = EvaluationResult(
                evaluation_id="eval_123",
                task_id="task_456",
                model_id="model_789",
                start_time=end_time,
                end_time=start_time,
                success=True,
                total_turns=0,
                turn_results=[],
                final_metrics={},
                aggregated_metrics=AggregatedMetrics(),
                termination_reason=TerminationReason.SUCCESS
            )
            DataValidator.validate_evaluation_result(result)
        
        # Test negative total_turns
        with pytest.raises(ValueError, match="total_turns cannot be negative"):
            result = EvaluationResult(
                evaluation_id="eval_123",
                task_id="task_456",
                model_id="model_789",
                start_time=start_time,
                end_time=end_time,
                success=True,
                total_turns=-1,
                turn_results=[],
                final_metrics={},
                aggregated_metrics=AggregatedMetrics(),
                termination_reason=TerminationReason.SUCCESS
            )
            DataValidator.validate_evaluation_result(result)
    
    def test_validate_standardized_output_success(self):
        """Test successful standardized output validation."""
        output = StandardizedOutput(
            run_id="run_123",
            task_id="task_456",
            sample_id="sample_789",
            success=True,
            turns=3,
            steps=15,
            wall_time_s=45.2,
            token_in=500,
            token_out=200,
            cost_usd=0.025,
            files_touched=2,
            edit_added=50,
            edit_deleted=10,
            redundancy_rate=0.15,
            recovered=True,
            safety_incidents=0
        )
        
        assert DataValidator.validate_standardized_output(output) is True
    
    def test_validate_standardized_output_failures(self):
        """Test standardized output validation failures."""
        # Test empty run_id
        with pytest.raises(ValueError, match="run_id cannot be empty"):
            output = StandardizedOutput(
                run_id="",
                task_id="task_456",
                sample_id="sample_789",
                success=True,
                turns=3,
                steps=15,
                wall_time_s=45.2,
                token_in=500,
                token_out=200,
                cost_usd=0.025,
                files_touched=2,
                edit_added=50,
                edit_deleted=10,
                redundancy_rate=0.15,
                recovered=True,
                safety_incidents=0
            )
            DataValidator.validate_standardized_output(output)
        
        # Test negative turns
        with pytest.raises(ValueError, match="turns cannot be negative"):
            output = StandardizedOutput(
                run_id="run_123",
                task_id="task_456",
                sample_id="sample_789",
                success=True,
                turns=-1,
                steps=15,
                wall_time_s=45.2,
                token_in=500,
                token_out=200,
                cost_usd=0.025,
                files_touched=2,
                edit_added=50,
                edit_deleted=10,
                redundancy_rate=0.15,
                recovered=True,
                safety_incidents=0
            )
            DataValidator.validate_standardized_output(output)
        
        # Test negative cost
        with pytest.raises(ValueError, match="cost_usd cannot be negative"):
            output = StandardizedOutput(
                run_id="run_123",
                task_id="task_456",
                sample_id="sample_789",
                success=True,
                turns=3,
                steps=15,
                wall_time_s=45.2,
                token_in=500,
                token_out=200,
                cost_usd=-0.025,
                files_touched=2,
                edit_added=50,
                edit_deleted=10,
                redundancy_rate=0.15,
                recovered=True,
                safety_incidents=0
            )
            DataValidator.validate_standardized_output(output)


if __name__ == "__main__":
    pytest.main([__file__])