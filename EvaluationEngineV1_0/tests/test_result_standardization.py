"""
Tests for result standardization system.

This module contains comprehensive tests for the result standardization
capabilities including conversion accuracy, validation, and error handling.
"""

import pytest
from datetime import datetime, timedelta
from typing import Dict, Any
import uuid

from EvaluationEngineV1_0.core.result_standardization import (
    ResultStandardizer, ResultConverter, ConversionContext, ResultFormat,
    ValidationLevel, StandardizedResultConverter, EvaluationResultConverter,
    DictResultConverter, standardize_result, get_result_standardizer
)
from EvaluationEngineV1_0.core.data_models import (
    EvaluationResult, AggregatedMetrics, StandardizedOutput, TurnResult,
    TerminationReason
)
from EvaluationEngineV1_0.core.adapters import StandardizedResult
from EvaluationEngineV1_0.core.exceptions import ConversionError, ValidationError


class TestConversionContext:
    """Test ConversionContext functionality."""
    
    def test_context_creation(self):
        """Test basic context creation."""
        context = ConversionContext(
            source_adapter="test_adapter",
            target_format=ResultFormat.STANDARDIZED_OUTPUT
        )
        
        assert context.source_adapter == "test_adapter"
        assert context.target_format == ResultFormat.STANDARDIZED_OUTPUT
        assert context.validation_level == ValidationLevel.MODERATE
        assert context.preserve_raw_data is True
        assert isinstance(context.metadata, dict)
    
    def test_context_with_metadata(self):
        """Test context creation with metadata."""
        metadata = {"run_id": "test_run", "model_id": "test_model"}
        context = ConversionContext(
            source_adapter="test_adapter",
            target_format=ResultFormat.EVALUATION_RESULT,
            validation_level=ValidationLevel.STRICT,
            preserve_raw_data=False,
            metadata=metadata
        )
        
        assert context.validation_level == ValidationLevel.STRICT
        assert context.preserve_raw_data is False
        assert context.metadata == metadata


class TestStandardizedResultConverter:
    """Test StandardizedResultConverter functionality."""
    
    def setup_method(self):
        """Set up test fixtures."""
        self.converter = StandardizedResultConverter()
        self.context = ConversionContext(
            source_adapter="test_adapter",
            target_format=ResultFormat.STANDARDIZED_OUTPUT,
            metadata={"run_id": "test_run", "sample_id": "test_sample"}
        )
    
    def test_can_convert_standardized_result(self):
        """Test converter can identify StandardizedResult objects."""
        result = StandardizedResult(
            task_id="test_task",
            adapter_name="test_adapter",
            success=True,
            score=0.8,
            execution_time=10.5,
            turns=3,
            tokens_used=100,
            cost=0.05,
            metadata={},
            raw_result={}
        )
        
        assert self.converter.can_convert(result, self.context) is True
        assert self.converter.can_convert("not_a_result", self.context) is False
        assert self.converter.can_convert({}, self.context) is False
    
    def test_convert_to_standardized_output(self):
        """Test conversion to StandardizedOutput."""
        metadata = {
            "steps": 5,
            "token_in": 50,
            "files_touched": 2,
            "edit_added": 10,
            "edit_deleted": 5,
            "redundancy_rate": 0.1,
            "recovered": True,
            "safety_incidents": 0,
            "notes": "Test conversion"
        }
        
        source_result = StandardizedResult(
            task_id="test_task",
            adapter_name="test_adapter",
            success=True,
            score=0.8,
            execution_time=10.5,
            turns=3,
            tokens_used=100,
            cost=0.05,
            metadata=metadata,
            raw_result={}
        )
        
        output = self.converter.convert_to_standardized_output(source_result, self.context)
        
        assert isinstance(output, StandardizedOutput)
        assert output.run_id == "test_run"
        assert output.task_id == "test_task"
        assert output.sample_id == "test_sample"
        assert output.success is True
        assert output.turns == 3
        assert output.steps == 5
        assert output.wall_time_s == 10.5
        assert output.token_in == 50
        assert output.token_out == 100
        assert output.cost_usd == 0.05
        assert output.files_touched == 2
        assert output.edit_added == 10
        assert output.edit_deleted == 5
        assert output.redundancy_rate == 0.1
        assert output.recovered is True
        assert output.safety_incidents == 0
        assert output.notes == "Test conversion"
    
    def test_convert_to_evaluation_result(self):
        """Test conversion to EvaluationResult."""
        source_result = StandardizedResult(
            task_id="test_task",
            adapter_name="test_adapter",
            success=True,
            score=0.8,
            execution_time=10.5,
            turns=3,
            tokens_used=100,
            cost=0.05,
            metadata={"files_touched": 2},
            raw_result={}
        )
        
        context = ConversionContext(
            source_adapter="test_adapter",
            target_format=ResultFormat.EVALUATION_RESULT,
            metadata={"evaluation_id": "test_eval", "model_id": "test_model"}
        )
        
        result = self.converter.convert_to_evaluation_result(source_result, context)
        
        assert isinstance(result, EvaluationResult)
        assert result.evaluation_id == "test_eval"
        assert result.task_id == "test_task"
        assert result.model_id == "test_model"
        assert result.success is True
        assert result.total_turns == 3
        assert result.final_metrics == {"score": 0.8}
        assert result.aggregated_metrics.resolved_percentage == 100.0
        assert result.aggregated_metrics.files_touched == 2
        assert result.termination_reason == TerminationReason.SUCCESS
    
    def test_conversion_error_handling(self):
        """Test error handling during conversion."""
        # Create malformed result
        source_result = StandardizedResult(
            task_id="test_task",
            adapter_name="test_adapter",
            success=True,
            score=0.8,
            execution_time=10.5,
            turns=3,
            tokens_used=100,
            cost=0.05,
            metadata=None,  # This could cause issues
            raw_result={}
        )
        
        # Should handle None metadata gracefully
        output = self.converter.convert_to_standardized_output(source_result, self.context)
        assert isinstance(output, StandardizedOutput)
        assert output.files_touched == 0  # Default value


class TestEvaluationResultConverter:
    """Test EvaluationResultConverter functionality."""
    
    def setup_method(self):
        """Set up test fixtures."""
        self.converter = EvaluationResultConverter()
        self.context = ConversionContext(
            source_adapter="test_adapter",
            target_format=ResultFormat.STANDARDIZED_OUTPUT
        )
    
    def test_can_convert_evaluation_result(self):
        """Test converter can identify EvaluationResult objects."""
        result = EvaluationResult(
            evaluation_id="test_eval",
            task_id="test_task",
            model_id="test_model",
            start_time=datetime.now(),
            end_time=datetime.now(),
            success=True,
            total_turns=3,
            turn_results=[],
            final_metrics={},
            aggregated_metrics=AggregatedMetrics(),
            termination_reason=TerminationReason.SUCCESS
        )
        
        assert self.converter.can_convert(result, self.context) is True
        assert self.converter.can_convert("not_a_result", self.context) is False
    
    def test_convert_to_standardized_output(self):
        """Test conversion to StandardizedOutput."""
        start_time = datetime.now()
        end_time = start_time + timedelta(seconds=10)
        
        turn_results = [
            TurnResult(
                turn=1,
                action="action1",
                observation="obs1",
                reward=0.5,
                done=False,
                info={},
                execution_time=3.0,
                tokens_used=30,
                cost=0.01
            ),
            TurnResult(
                turn=2,
                action="action2",
                observation="obs2",
                reward=1.0,
                done=True,
                info={},
                execution_time=7.0,
                tokens_used=70,
                cost=0.04
            )
        ]
        
        aggregated_metrics = AggregatedMetrics(
            files_touched=3,
            edit_churn=20.0,
            redundancy_rate=0.15,
            recovery_rate=0.8,
            safety_incidents=1
        )
        
        source_result = EvaluationResult(
            evaluation_id="test_eval",
            task_id="test_task",
            model_id="test_model",
            start_time=start_time,
            end_time=end_time,
            success=True,
            total_turns=2,
            turn_results=turn_results,
            final_metrics={"accuracy": 0.9},
            aggregated_metrics=aggregated_metrics,
            termination_reason=TerminationReason.SUCCESS,
            metadata={"notes": "Test evaluation"}
        )
        
        output = self.converter.convert_to_standardized_output(source_result, self.context)
        
        assert isinstance(output, StandardizedOutput)
        assert output.task_id == "test_task"
        assert output.success is True
        assert output.turns == 2
        assert output.steps == 2  # Number of actions
        assert output.wall_time_s == 10.0
        assert output.token_in == 100  # Sum of tokens_used
        assert output.token_out == 100
        assert output.cost_usd == 0.05  # Sum of costs
        assert output.files_touched == 3
        assert output.edit_added == 10  # Half of edit_churn
        assert output.edit_deleted == 10
        assert output.redundancy_rate == 0.15
        assert output.recovered is True  # recovery_rate > 0
        assert output.safety_incidents == 1
        assert output.notes == "Test evaluation"
    
    def test_convert_to_evaluation_result_passthrough(self):
        """Test that EvaluationResult is returned as-is."""
        source_result = EvaluationResult(
            evaluation_id="test_eval",
            task_id="test_task",
            model_id="test_model",
            start_time=datetime.now(),
            end_time=datetime.now(),
            success=True,
            total_turns=1,
            turn_results=[],
            final_metrics={},
            aggregated_metrics=AggregatedMetrics(),
            termination_reason=TerminationReason.SUCCESS
        )
        
        result = self.converter.convert_to_evaluation_result(source_result, self.context)
        assert result is source_result  # Should be the same object


class TestDictResultConverter:
    """Test DictResultConverter functionality."""
    
    def setup_method(self):
        """Set up test fixtures."""
        self.converter = DictResultConverter()
        self.context = ConversionContext(
            source_adapter="test_adapter",
            target_format=ResultFormat.STANDARDIZED_OUTPUT,
            metadata={"run_id": "test_run"}
        )
    
    def test_can_convert_dict_result(self):
        """Test converter can identify valid dictionary results."""
        valid_dict = {"task_id": "test", "success": True}
        invalid_dict = {"task_id": "test"}  # Missing success
        not_dict = "not_a_dict"
        
        assert self.converter.can_convert(valid_dict, self.context) is True
        assert self.converter.can_convert(invalid_dict, self.context) is False
        assert self.converter.can_convert(not_dict, self.context) is False
    
    def test_convert_minimal_dict_to_standardized_output(self):
        """Test conversion of minimal dictionary to StandardizedOutput."""
        source_result = {
            "task_id": "test_task",
            "success": True
        }
        
        output = self.converter.convert_to_standardized_output(source_result, self.context)
        
        assert isinstance(output, StandardizedOutput)
        assert output.run_id == "test_run"
        assert output.task_id == "test_task"
        assert output.sample_id == "test_task"  # Defaults to task_id
        assert output.success is True
        assert output.turns == 1  # Default
        assert output.steps == 1  # Default
        assert output.wall_time_s == 0.0  # Default
        assert output.token_in == 0  # Default
        assert output.token_out == 0  # Default
        assert output.cost_usd == 0.0  # Default
    
    def test_convert_full_dict_to_standardized_output(self):
        """Test conversion of complete dictionary to StandardizedOutput."""
        timestamp = datetime.now().isoformat()
        source_result = {
            "task_id": "test_task",
            "sample_id": "test_sample",
            "success": True,
            "turns": 3,
            "steps": 5,
            "execution_time": 15.5,
            "token_in": 80,
            "token_out": 120,
            "cost": 0.08,
            "files_touched": 4,
            "edit_added": 15,
            "edit_deleted": 8,
            "redundancy_rate": 0.2,
            "recovered": True,
            "safety_incidents": 0,
            "notes": "Full test",
            "timestamp": timestamp
        }
        
        output = self.converter.convert_to_standardized_output(source_result, self.context)
        
        assert output.task_id == "test_task"
        assert output.sample_id == "test_sample"
        assert output.success is True
        assert output.turns == 3
        assert output.steps == 5
        assert output.wall_time_s == 15.5
        assert output.token_in == 80
        assert output.token_out == 120
        assert output.cost_usd == 0.08
        assert output.files_touched == 4
        assert output.edit_added == 15
        assert output.edit_deleted == 8
        assert output.redundancy_rate == 0.2
        assert output.recovered is True
        assert output.safety_incidents == 0
        assert output.notes == "Full test"
        assert output.timestamp == datetime.fromisoformat(timestamp)
    
    def test_convert_dict_to_evaluation_result(self):
        """Test conversion of dictionary to EvaluationResult."""
        source_result = {
            "task_id": "test_task",
            "success": True,
            "turns": 2,
            "execution_time": 10.0,
            "token_out": 100,
            "cost": 0.05,
            "files_touched": 2,
            "edit_added": 5,
            "edit_deleted": 3,
            "redundancy_rate": 0.1,
            "recovered": True,
            "safety_incidents": 0,
            "turn_0_action": "first_action",
            "turn_0_observation": "first_obs",
            "turn_1_action": "second_action",
            "turn_1_observation": "second_obs"
        }
        
        context = ConversionContext(
            source_adapter="test_adapter",
            target_format=ResultFormat.EVALUATION_RESULT,
            metadata={"evaluation_id": "test_eval", "model_id": "test_model"}
        )
        
        result = self.converter.convert_to_evaluation_result(source_result, context)
        
        assert isinstance(result, EvaluationResult)
        assert result.evaluation_id == "test_eval"
        assert result.task_id == "test_task"
        assert result.model_id == "test_model"
        assert result.success is True
        assert result.total_turns == 2
        assert len(result.turn_results) == 2
        assert result.turn_results[0].action == "first_action"
        assert result.turn_results[0].observation == "first_obs"
        assert result.turn_results[1].action == "second_action"
        assert result.turn_results[1].observation == "second_obs"
        assert result.aggregated_metrics.resolved_percentage == 100.0
        assert result.aggregated_metrics.files_touched == 2
        assert result.aggregated_metrics.edit_churn == 8.0  # edit_added + edit_deleted


class TestResultStandardizer:
    """Test ResultStandardizer functionality."""
    
    def setup_method(self):
        """Set up test fixtures."""
        self.standardizer = ResultStandardizer()
    
    def test_initialization(self):
        """Test standardizer initialization."""
        assert len(self.standardizer._converters) == 3  # Default converters
        assert any(isinstance(c, StandardizedResultConverter) for c in self.standardizer._converters)
        assert any(isinstance(c, EvaluationResultConverter) for c in self.standardizer._converters)
        assert any(isinstance(c, DictResultConverter) for c in self.standardizer._converters)
    
    def test_register_converter(self):
        """Test converter registration."""
        class CustomConverter(ResultConverter):
            def can_convert(self, source_result, context):
                return False
            def convert_to_standardized_output(self, source_result, context):
                pass
            def convert_to_evaluation_result(self, source_result, context):
                pass
        
        initial_count = len(self.standardizer._converters)
        custom_converter = CustomConverter()
        self.standardizer.register_converter(custom_converter)
        
        assert len(self.standardizer._converters) == initial_count + 1
        assert custom_converter in self.standardizer._converters
    
    def test_find_converter(self):
        """Test converter discovery."""
        # Test with StandardizedResult
        standardized_result = StandardizedResult(
            task_id="test", adapter_name="test", success=True, score=0.8,
            execution_time=10.0, turns=1, tokens_used=50, cost=0.02,
            metadata={}, raw_result={}
        )
        context = ConversionContext("test", ResultFormat.STANDARDIZED_OUTPUT)
        
        converter = self.standardizer.find_converter(standardized_result, context)
        assert isinstance(converter, StandardizedResultConverter)
        
        # Test with dictionary
        dict_result = {"task_id": "test", "success": True}
        converter = self.standardizer.find_converter(dict_result, context)
        assert isinstance(converter, DictResultConverter)
        
        # Test with unsupported type
        unsupported_result = "unsupported"
        converter = self.standardizer.find_converter(unsupported_result, context)
        assert converter is None
    
    def test_standardize_result_success(self):
        """Test successful result standardization."""
        source_result = {"task_id": "test_task", "success": True, "turns": 2}
        context = ConversionContext(
            source_adapter="test_adapter",
            target_format=ResultFormat.STANDARDIZED_OUTPUT,
            validation_level=ValidationLevel.MODERATE
        )
        
        result = self.standardizer.standardize_result(source_result, context)
        
        assert isinstance(result, StandardizedOutput)
        assert result.task_id == "test_task"
        assert result.success is True
        assert result.turns == 2
    
    def test_standardize_result_no_converter(self):
        """Test standardization with no suitable converter."""
        source_result = "unsupported_type"
        context = ConversionContext(
            source_adapter="test_adapter",
            target_format=ResultFormat.STANDARDIZED_OUTPUT
        )
        
        with pytest.raises(ConversionError, match="No converter found"):
            self.standardizer.standardize_result(source_result, context)
    
    def test_batch_standardize_success(self):
        """Test successful batch standardization."""
        source_results = [
            {"task_id": "task1", "success": True},
            {"task_id": "task2", "success": False},
            {"task_id": "task3", "success": True, "turns": 3}
        ]
        context = ConversionContext(
            source_adapter="test_adapter",
            target_format=ResultFormat.STANDARDIZED_OUTPUT
        )
        
        results = self.standardizer.batch_standardize(source_results, context)
        
        assert len(results) == 3
        assert all(isinstance(r, StandardizedOutput) for r in results)
        assert results[0].task_id == "task1"
        assert results[1].task_id == "task2"
        assert results[2].task_id == "task3"
        assert results[0].success is True
        assert results[1].success is False
        assert results[2].turns == 3
    
    def test_batch_standardize_with_errors(self):
        """Test batch standardization with some errors."""
        source_results = [
            {"task_id": "task1", "success": True},
            "unsupported_type",  # This will fail
            {"task_id": "task3", "success": True}
        ]
        context = ConversionContext(
            source_adapter="test_adapter",
            target_format=ResultFormat.STANDARDIZED_OUTPUT
        )
        
        with pytest.raises(ConversionError, match="Batch conversion failed"):
            self.standardizer.batch_standardize(source_results, context)
    
    def test_validate_schema_compliance_standardized_output(self):
        """Test schema validation for StandardizedOutput."""
        # Valid output
        valid_output = StandardizedOutput(
            run_id="test_run",
            task_id="test_task",
            sample_id="test_sample",
            success=True,
            turns=2,
            steps=3,
            wall_time_s=10.5,
            token_in=50,
            token_out=75,
            cost_usd=0.05,
            files_touched=1,
            edit_added=5,
            edit_deleted=2,
            redundancy_rate=0.1,
            recovered=False,
            safety_incidents=0
        )
        
        assert self.standardizer.validate_schema_compliance(valid_output) is True
        
        # Test strict validation
        assert self.standardizer.validate_schema_compliance(
            valid_output, ValidationLevel.STRICT
        ) is True
    
    def test_validate_schema_compliance_evaluation_result(self):
        """Test schema validation for EvaluationResult."""
        # Create turn results that match total_turns
        turn_results = [
            TurnResult(
                turn=1,
                action="action1",
                observation="obs1",
                reward=0.5,
                done=False,
                info={},
                execution_time=5.0
            ),
            TurnResult(
                turn=2,
                action="action2",
                observation="obs2",
                reward=1.0,
                done=True,
                info={},
                execution_time=5.0
            )
        ]
        
        valid_result = EvaluationResult(
            evaluation_id="test_eval",
            task_id="test_task",
            model_id="test_model",
            start_time=datetime.now(),
            end_time=datetime.now() + timedelta(seconds=10),
            success=True,
            total_turns=2,
            turn_results=turn_results,  # Now matches total_turns
            final_metrics={},
            aggregated_metrics=AggregatedMetrics(resolved_percentage=100.0),
            termination_reason=TerminationReason.SUCCESS
        )
        
        assert self.standardizer.validate_schema_compliance(valid_result) is True
    
    def test_validation_errors(self):
        """Test validation error handling."""
        # Invalid StandardizedOutput (empty required fields)
        invalid_output = StandardizedOutput(
            run_id="",  # Empty run_id should fail
            task_id="test_task",
            sample_id="test_sample",
            success=True,
            turns=1,
            steps=1,
            wall_time_s=10.0,
            token_in=0,
            token_out=0,
            cost_usd=0.0,
            files_touched=0,
            edit_added=0,
            edit_deleted=0,
            redundancy_rate=0.0,
            recovered=False,
            safety_incidents=0
        )
        
        with pytest.raises(ValidationError):
            self.standardizer.validate_schema_compliance(invalid_output)
    
    def test_get_conversion_statistics(self):
        """Test conversion statistics."""
        stats = self.standardizer.get_conversion_statistics()
        
        assert "registered_converters" in stats
        assert "converter_types" in stats
        assert stats["registered_converters"] == 3
        assert len(stats["converter_types"]) == 3


class TestGlobalFunctions:
    """Test global convenience functions."""
    
    def test_get_result_standardizer(self):
        """Test global standardizer access."""
        standardizer = get_result_standardizer()
        assert isinstance(standardizer, ResultStandardizer)
        
        # Should return the same instance
        standardizer2 = get_result_standardizer()
        assert standardizer is standardizer2
    
    def test_standardize_result_convenience(self):
        """Test convenience function for result standardization."""
        source_result = {"task_id": "test_task", "success": True}
        
        result = standardize_result(
            source_result=source_result,
            target_format=ResultFormat.STANDARDIZED_OUTPUT,
            source_adapter="test_adapter",
            run_id="test_run"
        )
        
        assert isinstance(result, StandardizedOutput)
        assert result.task_id == "test_task"
        assert result.success is True


class TestErrorHandling:
    """Test error handling scenarios."""
    
    def test_conversion_error_propagation(self):
        """Test that conversion errors are properly propagated."""
        class FailingConverter(ResultConverter):
            def can_convert(self, source_result, context):
                return True
            
            def convert_to_standardized_output(self, source_result, context):
                raise ValueError("Conversion failed")
            
            def convert_to_evaluation_result(self, source_result, context):
                raise ValueError("Conversion failed")
        
        standardizer = ResultStandardizer()
        # Clear existing converters and add only the failing one
        standardizer._converters = [FailingConverter()]
        
        context = ConversionContext("test", ResultFormat.STANDARDIZED_OUTPUT)
        
        with pytest.raises(ValueError, match="Conversion failed"):
            standardizer.standardize_result("test", context)
    
    def test_validation_error_handling(self):
        """Test validation error handling."""
        # Create invalid StandardizedOutput
        invalid_output = StandardizedOutput(
            run_id="test",
            task_id="test",
            sample_id="test",
            success=True,
            turns=-1,  # Invalid: negative turns
            steps=1,
            wall_time_s=10.0,
            token_in=0,
            token_out=0,
            cost_usd=0.0,
            files_touched=0,
            edit_added=0,
            edit_deleted=0,
            redundancy_rate=0.0,
            recovered=False,
            safety_incidents=0
        )
        
        standardizer = ResultStandardizer()
        
        with pytest.raises(ValidationError):
            standardizer.validate_schema_compliance(
                invalid_output, ValidationLevel.STRICT
            )


if __name__ == "__main__":
    pytest.main([__file__])