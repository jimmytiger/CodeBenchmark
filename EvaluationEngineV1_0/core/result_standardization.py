"""
Result standardization system for multi-turn evaluation.

This module provides comprehensive result standardization capabilities that convert
results from different adapter types into a unified schema format for cross-benchmark
comparison and analysis.
"""

from abc import ABC, abstractmethod
from dataclasses import dataclass, field
from datetime import datetime
from typing import Any, Dict, List, Optional, Union, Type
from enum import Enum
import json
import logging
import uuid

from .data_models import (
    EvaluationResult, AggregatedMetrics, StandardizedOutput, TurnResult,
    TerminationReason, DataValidator
)
from .adapters import StandardizedResult
from .exceptions import ValidationError, ConversionError


class ResultFormat(Enum):
    """Supported result formats."""
    STANDARDIZED_OUTPUT = "standardized_output"
    EVALUATION_RESULT = "evaluation_result"
    AGGREGATED_METRICS = "aggregated_metrics"
    ADAPTER_RESULT = "adapter_result"


class ValidationLevel(Enum):
    """Validation strictness levels."""
    STRICT = "strict"      # All fields must be valid
    MODERATE = "moderate"  # Required fields must be valid, optional can be missing
    LENIENT = "lenient"    # Only basic structure validation


@dataclass
class ConversionContext:
    """Context information for result conversion.
    
    Attributes:
        source_adapter: Name of the source adapter
        target_format: Target format for conversion
        validation_level: Level of validation to apply
        preserve_raw_data: Whether to preserve original raw data
        metadata: Additional context metadata
    """
    source_adapter: str
    target_format: ResultFormat
    validation_level: ValidationLevel = ValidationLevel.MODERATE
    preserve_raw_data: bool = True
    metadata: Dict[str, Any] = field(default_factory=dict)


class ResultConverter(ABC):
    """Abstract base class for result converters.
    
    Each adapter type should have a corresponding converter that knows how to
    transform its specific result format into standardized formats.
    """
    
    @abstractmethod
    def can_convert(self, source_result: Any, context: ConversionContext) -> bool:
        """Check if this converter can handle the source result.
        
        Args:
            source_result: Result to potentially convert
            context: Conversion context
            
        Returns:
            True if this converter can handle the result
        """
        pass
    
    @abstractmethod
    def convert_to_standardized_output(
        self, 
        source_result: Any, 
        context: ConversionContext
    ) -> StandardizedOutput:
        """Convert source result to StandardizedOutput format.
        
        Args:
            source_result: Source result to convert
            context: Conversion context
            
        Returns:
            StandardizedOutput instance
            
        Raises:
            ConversionError: If conversion fails
        """
        pass
    
    @abstractmethod
    def convert_to_evaluation_result(
        self, 
        source_result: Any, 
        context: ConversionContext
    ) -> EvaluationResult:
        """Convert source result to EvaluationResult format.
        
        Args:
            source_result: Source result to convert
            context: Conversion context
            
        Returns:
            EvaluationResult instance
            
        Raises:
            ConversionError: If conversion fails
        """
        pass
    
    def get_supported_source_types(self) -> List[Type]:
        """Get list of source types this converter supports.
        
        Returns:
            List of supported source types
        """
        return [Any]  # Default to accepting any type


class StandardizedResultConverter(ResultConverter):
    """Converter for StandardizedResult objects from adapters."""
    
    def can_convert(self, source_result: Any, context: ConversionContext) -> bool:
        """Check if source is a StandardizedResult."""
        return isinstance(source_result, StandardizedResult)
    
    def convert_to_standardized_output(
        self, 
        source_result: StandardizedResult, 
        context: ConversionContext
    ) -> StandardizedOutput:
        """Convert StandardizedResult to StandardizedOutput."""
        try:
            # Extract metadata for additional fields
            metadata = source_result.metadata or {}
            
            return StandardizedOutput(
                run_id=context.metadata.get('run_id', str(uuid.uuid4())),
                task_id=source_result.task_id,
                sample_id=context.metadata.get('sample_id', source_result.task_id),
                success=source_result.success,
                turns=source_result.turns,
                steps=metadata.get('steps', source_result.turns),
                wall_time_s=source_result.execution_time,
                token_in=metadata.get('token_in', 0),
                token_out=metadata.get('token_out', source_result.tokens_used),
                cost_usd=source_result.cost,
                files_touched=metadata.get('files_touched', 0),
                edit_added=metadata.get('edit_added', 0),
                edit_deleted=metadata.get('edit_deleted', 0),
                redundancy_rate=metadata.get('redundancy_rate', 0.0),
                recovered=metadata.get('recovered', False),
                safety_incidents=metadata.get('safety_incidents', 0),
                notes=metadata.get('notes', ''),
                timestamp=source_result.timestamp or datetime.now()
            )
        except Exception as e:
            raise ConversionError(f"Failed to convert StandardizedResult: {e}") from e
    
    def convert_to_evaluation_result(
        self, 
        source_result: StandardizedResult, 
        context: ConversionContext
    ) -> EvaluationResult:
        """Convert StandardizedResult to EvaluationResult."""
        try:
            metadata = source_result.metadata or {}
            
            # Create basic aggregated metrics
            aggregated_metrics = AggregatedMetrics(
                resolved_percentage=100.0 if source_result.success else 0.0,
                avg_turns=float(source_result.turns),
                wall_time_per_solved=source_result.execution_time if source_result.success else 0.0,
                tokens_per_solved=source_result.tokens_used if source_result.success else 0,
                cost_per_solved=source_result.cost if source_result.success else 0.0,
                files_touched=metadata.get('files_touched', 0),
                safety_incidents=metadata.get('safety_incidents', 0)
            )
            
            # Create turn results if available
            turn_results = []
            if hasattr(source_result, 'turn_data') and source_result.turn_data:
                for i, turn_data in enumerate(source_result.turn_data):
                    turn_result = TurnResult(
                        turn=i + 1,
                        action=turn_data.get('action', ''),
                        observation=turn_data.get('observation', ''),
                        reward=turn_data.get('reward', 0.0),
                        done=turn_data.get('done', i == len(source_result.turn_data) - 1),
                        info=turn_data.get('info', {}),
                        execution_time=turn_data.get('execution_time', 0.0),
                        tokens_used=turn_data.get('tokens_used', 0),
                        cost=turn_data.get('cost', 0.0)
                    )
                    turn_results.append(turn_result)
            
            return EvaluationResult(
                evaluation_id=context.metadata.get('evaluation_id', str(uuid.uuid4())),
                task_id=source_result.task_id,
                model_id=context.metadata.get('model_id', 'unknown'),
                start_time=source_result.timestamp or datetime.now(),
                end_time=source_result.timestamp or datetime.now(),
                success=source_result.success,
                total_turns=source_result.turns,
                turn_results=turn_results,
                final_metrics={'score': source_result.score},
                aggregated_metrics=aggregated_metrics,
                termination_reason=TerminationReason.SUCCESS if source_result.success else TerminationReason.ERROR,
                metadata=metadata
            )
        except Exception as e:
            raise ConversionError(f"Failed to convert to EvaluationResult: {e}") from e
    
    def get_supported_source_types(self) -> List[Type]:
        """Get supported source types."""
        return [StandardizedResult]


class EvaluationResultConverter(ResultConverter):
    """Converter for EvaluationResult objects."""
    
    def can_convert(self, source_result: Any, context: ConversionContext) -> bool:
        """Check if source is an EvaluationResult."""
        return isinstance(source_result, EvaluationResult)
    
    def convert_to_standardized_output(
        self, 
        source_result: EvaluationResult, 
        context: ConversionContext
    ) -> StandardizedOutput:
        """Convert EvaluationResult to StandardizedOutput."""
        try:
            metrics = source_result.aggregated_metrics
            
            return StandardizedOutput(
                run_id=context.metadata.get('run_id', source_result.evaluation_id),
                task_id=source_result.task_id,
                sample_id=context.metadata.get('sample_id', source_result.task_id),
                success=source_result.success,
                turns=source_result.total_turns,
                steps=sum(1 for tr in source_result.turn_results if tr.action),
                wall_time_s=source_result.duration,
                token_in=sum(tr.tokens_used for tr in source_result.turn_results if hasattr(tr, 'tokens_used')),
                token_out=sum(tr.tokens_used for tr in source_result.turn_results if hasattr(tr, 'tokens_used')),
                cost_usd=sum(tr.cost for tr in source_result.turn_results if hasattr(tr, 'cost')),
                files_touched=metrics.files_touched,
                edit_added=int(metrics.edit_churn / 2) if metrics.edit_churn > 0 else 0,
                edit_deleted=int(metrics.edit_churn / 2) if metrics.edit_churn > 0 else 0,
                redundancy_rate=metrics.redundancy_rate,
                recovered=metrics.recovery_rate > 0,
                safety_incidents=metrics.safety_incidents,
                notes=source_result.metadata.get('notes', ''),
                timestamp=source_result.end_time
            )
        except Exception as e:
            raise ConversionError(f"Failed to convert EvaluationResult: {e}") from e
    
    def convert_to_evaluation_result(
        self, 
        source_result: EvaluationResult, 
        context: ConversionContext
    ) -> EvaluationResult:
        """Return the EvaluationResult as-is (no conversion needed)."""
        return source_result
    
    def get_supported_source_types(self) -> List[Type]:
        """Get supported source types."""
        return [EvaluationResult]


class DictResultConverter(ResultConverter):
    """Converter for dictionary-based results (common from external tools)."""
    
    def can_convert(self, source_result: Any, context: ConversionContext) -> bool:
        """Check if source is a dictionary with required fields."""
        if not isinstance(source_result, dict):
            return False
        
        # Check for minimum required fields
        required_fields = ['task_id', 'success']
        return all(field in source_result for field in required_fields)
    
    def convert_to_standardized_output(
        self, 
        source_result: Dict[str, Any], 
        context: ConversionContext
    ) -> StandardizedOutput:
        """Convert dictionary result to StandardizedOutput."""
        try:
            return StandardizedOutput(
                run_id=context.metadata.get('run_id', str(uuid.uuid4())),
                task_id=source_result['task_id'],
                sample_id=source_result.get('sample_id', source_result['task_id']),
                success=bool(source_result['success']),
                turns=source_result.get('turns', 1),
                steps=source_result.get('steps', source_result.get('turns', 1)),
                wall_time_s=float(source_result.get('execution_time', 0.0)),
                token_in=int(source_result.get('token_in', 0)),
                token_out=int(source_result.get('token_out', 0)),
                cost_usd=float(source_result.get('cost', 0.0)),
                files_touched=int(source_result.get('files_touched', 0)),
                edit_added=int(source_result.get('edit_added', 0)),
                edit_deleted=int(source_result.get('edit_deleted', 0)),
                redundancy_rate=float(source_result.get('redundancy_rate', 0.0)),
                recovered=bool(source_result.get('recovered', False)),
                safety_incidents=int(source_result.get('safety_incidents', 0)),
                notes=str(source_result.get('notes', '')),
                timestamp=datetime.fromisoformat(source_result['timestamp']) if 'timestamp' in source_result else datetime.now()
            )
        except Exception as e:
            raise ConversionError(f"Failed to convert dictionary result: {e}") from e
    
    def convert_to_evaluation_result(
        self, 
        source_result: Dict[str, Any], 
        context: ConversionContext
    ) -> EvaluationResult:
        """Convert dictionary result to EvaluationResult."""
        try:
            # Create aggregated metrics from available data
            aggregated_metrics = AggregatedMetrics(
                resolved_percentage=100.0 if source_result['success'] else 0.0,
                avg_turns=float(source_result.get('turns', 1)),
                wall_time_per_solved=float(source_result.get('execution_time', 0.0)) if source_result['success'] else 0.0,
                tokens_per_solved=int(source_result.get('token_out', 0)) if source_result['success'] else 0,
                cost_per_solved=float(source_result.get('cost', 0.0)) if source_result['success'] else 0.0,
                files_touched=int(source_result.get('files_touched', 0)),
                edit_churn=float(source_result.get('edit_added', 0) + source_result.get('edit_deleted', 0)),
                redundancy_rate=float(source_result.get('redundancy_rate', 0.0)),
                recovery_rate=1.0 if source_result.get('recovered', False) else 0.0,
                safety_incidents=int(source_result.get('safety_incidents', 0))
            )
            
            # Create basic turn results
            turn_results = []
            turns = source_result.get('turns', 1)
            for i in range(turns):
                turn_result = TurnResult(
                    turn=i + 1,
                    action=source_result.get(f'turn_{i}_action', ''),
                    observation=source_result.get(f'turn_{i}_observation', ''),
                    reward=float(source_result.get(f'turn_{i}_reward', 0.0)),
                    done=i == turns - 1,
                    info=source_result.get(f'turn_{i}_info', {}),
                    execution_time=float(source_result.get('execution_time', 0.0)) / turns,
                    tokens_used=int(source_result.get('token_out', 0)) // turns,
                    cost=float(source_result.get('cost', 0.0)) / turns
                )
                turn_results.append(turn_result)
            
            timestamp = datetime.now()
            if 'timestamp' in source_result:
                timestamp = datetime.fromisoformat(source_result['timestamp'])
            
            return EvaluationResult(
                evaluation_id=context.metadata.get('evaluation_id', str(uuid.uuid4())),
                task_id=source_result['task_id'],
                model_id=context.metadata.get('model_id', 'unknown'),
                start_time=timestamp,
                end_time=timestamp,
                success=bool(source_result['success']),
                total_turns=turns,
                turn_results=turn_results,
                final_metrics=source_result.get('metrics', {}),
                aggregated_metrics=aggregated_metrics,
                termination_reason=TerminationReason.SUCCESS if source_result['success'] else TerminationReason.ERROR,
                metadata=source_result.get('metadata', {})
            )
        except Exception as e:
            raise ConversionError(f"Failed to convert dictionary to EvaluationResult: {e}") from e
    
    def get_supported_source_types(self) -> List[Type]:
        """Get supported source types."""
        return [dict]


class ResultStandardizer:
    """Main class for result standardization and conversion.
    
    This class orchestrates the conversion of results from different adapter types
    into standardized formats, with comprehensive validation and error handling.
    """
    
    def __init__(self):
        """Initialize the result standardizer."""
        self._converters: List[ResultConverter] = []
        self._logger = logging.getLogger(f"{self.__class__.__module__}.{self.__class__.__name__}")
        self._validator = DataValidator()
        
        # Register default converters
        self._register_default_converters()
    
    def _register_default_converters(self) -> None:
        """Register default result converters."""
        self.register_converter(StandardizedResultConverter())
        self.register_converter(EvaluationResultConverter())
        self.register_converter(DictResultConverter())
    
    def register_converter(self, converter: ResultConverter) -> None:
        """Register a result converter.
        
        Args:
            converter: ResultConverter instance to register
        """
        self._converters.append(converter)
        self._logger.info(f"Registered converter: {converter.__class__.__name__}")
    
    def find_converter(self, source_result: Any, context: ConversionContext) -> Optional[ResultConverter]:
        """Find a suitable converter for the source result.
        
        Args:
            source_result: Result to find converter for
            context: Conversion context
            
        Returns:
            Suitable converter or None if not found
        """
        for converter in self._converters:
            if converter.can_convert(source_result, context):
                return converter
        return None
    
    def standardize_result(
        self, 
        source_result: Any, 
        context: ConversionContext
    ) -> Union[StandardizedOutput, EvaluationResult]:
        """Standardize a result to the specified target format.
        
        Args:
            source_result: Source result to standardize
            context: Conversion context specifying target format
            
        Returns:
            Standardized result in the target format
            
        Raises:
            ConversionError: If no suitable converter found or conversion fails
            ValidationError: If result validation fails
        """
        # Find suitable converter
        converter = self.find_converter(source_result, context)
        if not converter:
            raise ConversionError(
                f"No converter found for result type {type(source_result)} "
                f"to format {context.target_format}"
            )
        
        try:
            # Perform conversion
            if context.target_format == ResultFormat.STANDARDIZED_OUTPUT:
                result = converter.convert_to_standardized_output(source_result, context)
                
                # Validate result
                if context.validation_level != ValidationLevel.LENIENT:
                    self._validate_standardized_output(result, context.validation_level)
                
                return result
                
            elif context.target_format == ResultFormat.EVALUATION_RESULT:
                result = converter.convert_to_evaluation_result(source_result, context)
                
                # Validate result
                if context.validation_level != ValidationLevel.LENIENT:
                    self._validate_evaluation_result(result, context.validation_level)
                
                return result
                
            else:
                raise ConversionError(f"Unsupported target format: {context.target_format}")
                
        except Exception as e:
            self._logger.error(f"Conversion failed: {e}")
            raise
    
    def batch_standardize(
        self, 
        source_results: List[Any], 
        context: ConversionContext
    ) -> List[Union[StandardizedOutput, EvaluationResult]]:
        """Standardize multiple results in batch.
        
        Args:
            source_results: List of source results to standardize
            context: Conversion context
            
        Returns:
            List of standardized results
            
        Raises:
            ConversionError: If any conversion fails
        """
        standardized_results = []
        errors = []
        
        for i, source_result in enumerate(source_results):
            try:
                result = self.standardize_result(source_result, context)
                standardized_results.append(result)
            except Exception as e:
                error_msg = f"Failed to standardize result {i}: {e}"
                errors.append(error_msg)
                self._logger.error(error_msg)
        
        if errors:
            raise ConversionError(f"Batch conversion failed with {len(errors)} errors: {errors}")
        
        return standardized_results
    
    def validate_schema_compliance(
        self, 
        result: Union[StandardizedOutput, EvaluationResult],
        validation_level: ValidationLevel = ValidationLevel.MODERATE
    ) -> bool:
        """Validate that a result complies with the expected schema.
        
        Args:
            result: Result to validate
            validation_level: Level of validation strictness
            
        Returns:
            True if validation passes
            
        Raises:
            ValidationError: If validation fails
        """
        try:
            if isinstance(result, StandardizedOutput):
                return self._validate_standardized_output(result, validation_level)
            elif isinstance(result, EvaluationResult):
                return self._validate_evaluation_result(result, validation_level)
            else:
                raise ValidationError(f"Unsupported result type for validation: {type(result)}")
        except Exception as e:
            raise ValidationError(f"Schema validation failed: {e}") from e
    
    def _validate_standardized_output(
        self, 
        result: StandardizedOutput, 
        validation_level: ValidationLevel
    ) -> bool:
        """Validate a StandardizedOutput instance."""
        # Use existing validator
        self._validator.validate_standardized_output(result)
        
        # Additional validation based on level
        if validation_level == ValidationLevel.STRICT:
            # Strict validation - all fields must have reasonable values
            if result.wall_time_s < 0:
                raise ValidationError("wall_time_s cannot be negative")
            if result.turns <= 0:
                raise ValidationError("turns must be positive")
            if result.steps < 0:
                raise ValidationError("steps cannot be negative")
            if result.cost_usd < 0:
                raise ValidationError("cost_usd cannot be negative")
            if not (0.0 <= result.redundancy_rate <= 1.0):
                raise ValidationError("redundancy_rate must be between 0.0 and 1.0")
        
        return True
    
    def _validate_evaluation_result(
        self, 
        result: EvaluationResult, 
        validation_level: ValidationLevel
    ) -> bool:
        """Validate an EvaluationResult instance."""
        # Use existing validator
        self._validator.validate_evaluation_result(result)
        
        # Additional validation based on level
        if validation_level == ValidationLevel.STRICT:
            # Validate aggregated metrics
            metrics = result.aggregated_metrics
            if not (0.0 <= metrics.resolved_percentage <= 100.0):
                raise ValidationError("resolved_percentage must be between 0.0 and 100.0")
            if metrics.avg_turns < 0:
                raise ValidationError("avg_turns cannot be negative")
            if metrics.safety_incidents < 0:
                raise ValidationError("safety_incidents cannot be negative")
        
        return True
    
    def get_conversion_statistics(self) -> Dict[str, Any]:
        """Get statistics about conversions performed.
        
        Returns:
            Dictionary with conversion statistics
        """
        return {
            "registered_converters": len(self._converters),
            "converter_types": [converter.__class__.__name__ for converter in self._converters]
        }


# Global standardizer instance
_global_standardizer = ResultStandardizer()


def get_result_standardizer() -> ResultStandardizer:
    """Get the global result standardizer instance.
    
    Returns:
        Global ResultStandardizer instance
    """
    return _global_standardizer


def standardize_result(
    source_result: Any,
    target_format: ResultFormat,
    source_adapter: str,
    validation_level: ValidationLevel = ValidationLevel.MODERATE,
    **context_kwargs
) -> Union[StandardizedOutput, EvaluationResult]:
    """Convenience function to standardize a result using the global standardizer.
    
    Args:
        source_result: Source result to standardize
        target_format: Target format for conversion
        source_adapter: Name of the source adapter
        validation_level: Level of validation to apply
        **context_kwargs: Additional context metadata
        
    Returns:
        Standardized result
    """
    context = ConversionContext(
        source_adapter=source_adapter,
        target_format=target_format,
        validation_level=validation_level,
        metadata=context_kwargs
    )
    
    return _global_standardizer.standardize_result(source_result, context)