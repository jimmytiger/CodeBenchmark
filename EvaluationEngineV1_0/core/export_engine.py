"""
Export engine for multi-turn evaluation results.

This module provides comprehensive export capabilities supporting multiple formats
including CSV, JSON, PDF, and Excel with configurable templates and baseline
configurations for cross-benchmark comparison.
"""

from abc import ABC, abstractmethod
from dataclasses import dataclass, field
from datetime import datetime
from enum import Enum
from pathlib import Path
from typing import Any, Dict, List, Optional, Union, IO
import csv
import json
import logging
import os
import tempfile
import uuid

try:
    import pandas as pd
    PANDAS_AVAILABLE = True
except ImportError:
    PANDAS_AVAILABLE = False

try:
    from reportlab.lib import colors
    from reportlab.lib.pagesizes import letter, A4
    from reportlab.platypus import SimpleDocTemplate, Table, TableStyle, Paragraph, Spacer
    from reportlab.lib.styles import getSampleStyleSheet, ParagraphStyle
    from reportlab.lib.units import inch
    REPORTLAB_AVAILABLE = True
except ImportError:
    REPORTLAB_AVAILABLE = False

from .data_models import EvaluationResult, AggregatedMetrics, StandardizedOutput
from .result_standardization import ResultStandardizer, ConversionContext, ResultFormat, ValidationLevel
from .exceptions import ConfigurationError, ValidationError


class ExportFormat(Enum):
    """Supported export formats."""
    CSV = "csv"
    JSON = "json"
    PDF = "pdf"
    EXCEL = "excel"
    HTML = "html"


class BaselineConfiguration(Enum):
    """Predefined baseline configurations."""
    REGRESSION = "regression"      # Basic regression testing
    MID_FIDELITY = "mid_fidelity"  # Balanced evaluation
    MILESTONE = "milestone"        # Comprehensive milestone evaluation


@dataclass
class ExportTemplate:
    """Template configuration for exports.
    
    Attributes:
        name: Template name
        description: Template description
        fields: List of fields to include in export
        field_mappings: Custom field name mappings
        filters: Data filters to apply
        sorting: Sorting configuration
        grouping: Grouping configuration
        aggregations: Aggregation functions to apply
        formatting: Field formatting options
    """
    name: str
    description: str
    fields: List[str]
    field_mappings: Dict[str, str] = field(default_factory=dict)
    filters: Dict[str, Any] = field(default_factory=dict)
    sorting: List[Dict[str, str]] = field(default_factory=list)
    grouping: List[str] = field(default_factory=list)
    aggregations: Dict[str, str] = field(default_factory=dict)
    formatting: Dict[str, Dict[str, Any]] = field(default_factory=dict)


@dataclass
class ExportConfiguration:
    """Configuration for export operations.
    
    Attributes:
        format: Export format
        template: Export template to use
        output_path: Output file path
        include_metadata: Whether to include metadata
        include_raw_data: Whether to include raw data
        validation_level: Validation level for exported data
        compression: Whether to compress output
        encoding: Text encoding for output
    """
    format: ExportFormat
    template: Optional[ExportTemplate] = None
    output_path: Optional[str] = None
    include_metadata: bool = True
    include_raw_data: bool = False
    validation_level: ValidationLevel = ValidationLevel.MODERATE
    compression: bool = False
    encoding: str = "utf-8"


class ExportHandler(ABC):
    """Abstract base class for format-specific export handlers."""
    
    @abstractmethod
    def can_handle(self, format: ExportFormat) -> bool:
        """Check if this handler can handle the specified format.
        
        Args:
            format: Export format to check
            
        Returns:
            True if handler can handle the format
        """
        pass
    
    @abstractmethod
    def export(
        self, 
        data: List[Dict[str, Any]], 
        config: ExportConfiguration
    ) -> str:
        """Export data in the specified format.
        
        Args:
            data: Data to export
            config: Export configuration
            
        Returns:
            Path to exported file
            
        Raises:
            ConfigurationError: If configuration is invalid
            ValidationError: If data validation fails
        """
        pass
    
    def validate_dependencies(self) -> bool:
        """Validate that required dependencies are available.
        
        Returns:
            True if dependencies are available
        """
        return True


class CSVExportHandler(ExportHandler):
    """Handler for CSV export format."""
    
    def can_handle(self, format: ExportFormat) -> bool:
        """Check if this handler can handle CSV format."""
        return format == ExportFormat.CSV
    
    def export(
        self, 
        data: List[Dict[str, Any]], 
        config: ExportConfiguration
    ) -> str:
        """Export data to CSV format."""
        if not data:
            raise ValidationError("No data to export")
        
        # Determine output path
        output_path = config.output_path or self._generate_output_path("csv")
        
        # Apply template if specified
        if config.template:
            data = self._apply_template(data, config.template)
        
        # Write CSV file
        with open(output_path, 'w', newline='', encoding=config.encoding) as csvfile:
            if data:
                fieldnames = list(data[0].keys())
                writer = csv.DictWriter(csvfile, fieldnames=fieldnames)
                writer.writeheader()
                writer.writerows(data)
        
        return output_path
    
    def _apply_template(self, data: List[Dict[str, Any]], template: ExportTemplate) -> List[Dict[str, Any]]:
        """Apply template configuration to data."""
        processed_data = []
        
        for row in data:
            # Apply field filtering
            if template.fields:
                filtered_row = {field: row.get(field, '') for field in template.fields}
            else:
                filtered_row = row.copy()
            
            # Apply field mappings
            if template.field_mappings:
                mapped_row = {}
                for old_field, new_field in template.field_mappings.items():
                    if old_field in filtered_row:
                        mapped_row[new_field] = filtered_row[old_field]
                    else:
                        mapped_row[new_field] = filtered_row.get(old_field, '')
                # Add unmapped fields
                for field, value in filtered_row.items():
                    if field not in template.field_mappings:
                        mapped_row[field] = value
                filtered_row = mapped_row
            
            # Apply filters
            if template.filters:
                include_row = True
                for field, filter_value in template.filters.items():
                    if field in filtered_row:
                        if isinstance(filter_value, dict):
                            # Complex filter
                            if 'equals' in filter_value and filtered_row[field] != filter_value['equals']:
                                include_row = False
                                break
                            if 'contains' in filter_value and filter_value['contains'] not in str(filtered_row[field]):
                                include_row = False
                                break
                        else:
                            # Simple equality filter
                            if filtered_row[field] != filter_value:
                                include_row = False
                                break
                
                if include_row:
                    processed_data.append(filtered_row)
            else:
                processed_data.append(filtered_row)
        
        # Apply sorting
        if template.sorting:
            for sort_config in reversed(template.sorting):  # Apply in reverse order
                field = sort_config.get('field')
                reverse = sort_config.get('order', 'asc').lower() == 'desc'
                if field:
                    processed_data.sort(key=lambda x: x.get(field, ''), reverse=reverse)
        
        return processed_data
    
    def _generate_output_path(self, extension: str) -> str:
        """Generate a unique output path."""
        timestamp = datetime.now().strftime("%Y%m%d_%H%M%S")
        filename = f"evaluation_results_{timestamp}.{extension}"
        return os.path.join(tempfile.gettempdir(), filename)


class JSONExportHandler(ExportHandler):
    """Handler for JSON export format."""
    
    def can_handle(self, format: ExportFormat) -> bool:
        """Check if this handler can handle JSON format."""
        return format == ExportFormat.JSON
    
    def export(
        self, 
        data: List[Dict[str, Any]], 
        config: ExportConfiguration
    ) -> str:
        """Export data to JSON format."""
        if not data:
            raise ValidationError("No data to export")
        
        # Determine output path
        output_path = config.output_path or self._generate_output_path("json")
        
        # Apply template if specified
        if config.template:
            data = self._apply_template(data, config.template)
        
        # Prepare export data
        export_data = {
            "metadata": {
                "export_timestamp": datetime.now().isoformat(),
                "record_count": len(data),
                "format_version": "1.0"
            },
            "results": data
        }
        
        if config.include_metadata and config.template:
            export_data["metadata"]["template"] = {
                "name": config.template.name,
                "description": config.template.description
            }
        
        # Write JSON file
        with open(output_path, 'w', encoding=config.encoding) as jsonfile:
            json.dump(export_data, jsonfile, indent=2, default=str)
        
        return output_path
    
    def _apply_template(self, data: List[Dict[str, Any]], template: ExportTemplate) -> List[Dict[str, Any]]:
        """Apply template configuration to data (reuse CSV logic)."""
        csv_handler = CSVExportHandler()
        return csv_handler._apply_template(data, template)
    
    def _generate_output_path(self, extension: str) -> str:
        """Generate a unique output path."""
        timestamp = datetime.now().strftime("%Y%m%d_%H%M%S")
        filename = f"evaluation_results_{timestamp}.{extension}"
        return os.path.join(tempfile.gettempdir(), filename)


class ExcelExportHandler(ExportHandler):
    """Handler for Excel export format."""
    
    def can_handle(self, format: ExportFormat) -> bool:
        """Check if this handler can handle Excel format."""
        return format == ExportFormat.EXCEL
    
    def validate_dependencies(self) -> bool:
        """Validate that pandas is available for Excel export."""
        return PANDAS_AVAILABLE
    
    def export(
        self, 
        data: List[Dict[str, Any]], 
        config: ExportConfiguration
    ) -> str:
        """Export data to Excel format."""
        if not self.validate_dependencies():
            raise ConfigurationError("pandas is required for Excel export")
        
        if not data:
            raise ValidationError("No data to export")
        
        # Determine output path
        output_path = config.output_path or self._generate_output_path("xlsx")
        
        # Apply template if specified
        if config.template:
            data = self._apply_template(data, config.template)
        
        # Create DataFrame
        df = pd.DataFrame(data)
        
        # Write Excel file
        with pd.ExcelWriter(output_path, engine='openpyxl') as writer:
            df.to_excel(writer, sheet_name='Results', index=False)
            
            # Add metadata sheet if requested
            if config.include_metadata:
                metadata_df = pd.DataFrame([
                    {"Property": "Export Timestamp", "Value": datetime.now().isoformat()},
                    {"Property": "Record Count", "Value": len(data)},
                    {"Property": "Format Version", "Value": "1.0"}
                ])
                if config.template:
                    metadata_df = pd.concat([metadata_df, pd.DataFrame([
                        {"Property": "Template Name", "Value": config.template.name},
                        {"Property": "Template Description", "Value": config.template.description}
                    ])], ignore_index=True)
                
                metadata_df.to_excel(writer, sheet_name='Metadata', index=False)
        
        return output_path
    
    def _apply_template(self, data: List[Dict[str, Any]], template: ExportTemplate) -> List[Dict[str, Any]]:
        """Apply template configuration to data (reuse CSV logic)."""
        csv_handler = CSVExportHandler()
        return csv_handler._apply_template(data, template)
    
    def _generate_output_path(self, extension: str) -> str:
        """Generate a unique output path."""
        timestamp = datetime.now().strftime("%Y%m%d_%H%M%S")
        filename = f"evaluation_results_{timestamp}.{extension}"
        return os.path.join(tempfile.gettempdir(), filename)


class PDFExportHandler(ExportHandler):
    """Handler for PDF export format."""
    
    def can_handle(self, format: ExportFormat) -> bool:
        """Check if this handler can handle PDF format."""
        return format == ExportFormat.PDF
    
    def validate_dependencies(self) -> bool:
        """Validate that reportlab is available for PDF export."""
        return REPORTLAB_AVAILABLE
    
    def export(
        self, 
        data: List[Dict[str, Any]], 
        config: ExportConfiguration
    ) -> str:
        """Export data to PDF format."""
        if not self.validate_dependencies():
            raise ConfigurationError("reportlab is required for PDF export")
        
        if not data:
            raise ValidationError("No data to export")
        
        # Determine output path
        output_path = config.output_path or self._generate_output_path("pdf")
        
        # Apply template if specified
        if config.template:
            data = self._apply_template(data, config.template)
        
        # Create PDF document
        doc = SimpleDocTemplate(output_path, pagesize=A4)
        story = []
        styles = getSampleStyleSheet()
        
        # Add title
        title_style = ParagraphStyle(
            'CustomTitle',
            parent=styles['Heading1'],
            fontSize=16,
            spaceAfter=30,
        )
        story.append(Paragraph("Evaluation Results Report", title_style))
        story.append(Spacer(1, 12))
        
        # Add metadata if requested
        if config.include_metadata:
            story.append(Paragraph("Report Metadata", styles['Heading2']))
            metadata_data = [
                ["Property", "Value"],
                ["Export Timestamp", datetime.now().strftime("%Y-%m-%d %H:%M:%S")],
                ["Record Count", str(len(data))],
                ["Format Version", "1.0"]
            ]
            if config.template:
                metadata_data.extend([
                    ["Template Name", config.template.name],
                    ["Template Description", config.template.description]
                ])
            
            metadata_table = Table(metadata_data)
            metadata_table.setStyle(TableStyle([
                ('BACKGROUND', (0, 0), (-1, 0), colors.grey),
                ('TEXTCOLOR', (0, 0), (-1, 0), colors.whitesmoke),
                ('ALIGN', (0, 0), (-1, -1), 'LEFT'),
                ('FONTNAME', (0, 0), (-1, 0), 'Helvetica-Bold'),
                ('FONTSIZE', (0, 0), (-1, 0), 12),
                ('BOTTOMPADDING', (0, 0), (-1, 0), 12),
                ('BACKGROUND', (0, 1), (-1, -1), colors.beige),
                ('GRID', (0, 0), (-1, -1), 1, colors.black)
            ]))
            story.append(metadata_table)
            story.append(Spacer(1, 20))
        
        # Add results table
        if data:
            story.append(Paragraph("Results", styles['Heading2']))
            
            # Prepare table data
            headers = list(data[0].keys())
            table_data = [headers]
            
            for row in data[:50]:  # Limit to first 50 rows for PDF
                table_data.append([str(row.get(header, '')) for header in headers])
            
            # Create table
            results_table = Table(table_data)
            results_table.setStyle(TableStyle([
                ('BACKGROUND', (0, 0), (-1, 0), colors.grey),
                ('TEXTCOLOR', (0, 0), (-1, 0), colors.whitesmoke),
                ('ALIGN', (0, 0), (-1, -1), 'LEFT'),
                ('FONTNAME', (0, 0), (-1, 0), 'Helvetica-Bold'),
                ('FONTSIZE', (0, 0), (-1, 0), 10),
                ('BOTTOMPADDING', (0, 0), (-1, 0), 12),
                ('BACKGROUND', (0, 1), (-1, -1), colors.beige),
                ('GRID', (0, 0), (-1, -1), 1, colors.black),
                ('FONTSIZE', (0, 1), (-1, -1), 8),
            ]))
            story.append(results_table)
            
            if len(data) > 50:
                story.append(Spacer(1, 12))
                story.append(Paragraph(f"Note: Only first 50 of {len(data)} records shown in PDF. Use CSV or Excel for complete data.", styles['Normal']))
        
        # Build PDF
        doc.build(story)
        
        return output_path
    
    def _apply_template(self, data: List[Dict[str, Any]], template: ExportTemplate) -> List[Dict[str, Any]]:
        """Apply template configuration to data (reuse CSV logic)."""
        csv_handler = CSVExportHandler()
        return csv_handler._apply_template(data, template)
    
    def _generate_output_path(self, extension: str) -> str:
        """Generate a unique output path."""
        timestamp = datetime.now().strftime("%Y%m%d_%H%M%S")
        filename = f"evaluation_results_{timestamp}.{extension}"
        return os.path.join(tempfile.gettempdir(), filename)


class ExportEngine:
    """Main export engine for multi-turn evaluation results.
    
    This class orchestrates the export of evaluation results to multiple formats
    with configurable templates and baseline configurations.
    """
    
    def __init__(self):
        """Initialize the export engine."""
        self._handlers: List[ExportHandler] = []
        self._templates: Dict[str, ExportTemplate] = {}
        self._baseline_configs: Dict[BaselineConfiguration, ExportTemplate] = {}
        self._logger = logging.getLogger(f"{self.__class__.__module__}.{self.__class__.__name__}")
        self._standardizer = ResultStandardizer()
        
        # Register default handlers
        self._register_default_handlers()
        
        # Register default templates
        self._register_default_templates()
        
        # Register baseline configurations
        self._register_baseline_configurations()
    
    def _register_default_handlers(self) -> None:
        """Register default export handlers."""
        self.register_handler(CSVExportHandler())
        self.register_handler(JSONExportHandler())
        self.register_handler(ExcelExportHandler())
        self.register_handler(PDFExportHandler())
    
    def _register_default_templates(self) -> None:
        """Register default export templates."""
        # Standard template with all fields
        standard_template = ExportTemplate(
            name="standard",
            description="Standard template with all available fields",
            fields=[
                "run_id", "task_id", "sample_id", "success", "turns", "steps",
                "wall_time_s", "token_in", "token_out", "cost_usd", "files_touched",
                "edit_added", "edit_deleted", "redundancy_rate", "recovered",
                "safety_incidents", "notes", "timestamp"
            ]
        )
        self.register_template(standard_template)
        
        # Summary template with key metrics only
        summary_template = ExportTemplate(
            name="summary",
            description="Summary template with key metrics only",
            fields=[
                "task_id", "success", "turns", "wall_time_s", "cost_usd", "safety_incidents"
            ],
            field_mappings={
                "wall_time_s": "duration_seconds",
                "cost_usd": "cost_dollars"
            }
        )
        self.register_template(summary_template)
        
        # Performance template focused on efficiency metrics
        performance_template = ExportTemplate(
            name="performance",
            description="Performance-focused template",
            fields=[
                "task_id", "success", "turns", "steps", "wall_time_s", "token_in",
                "token_out", "redundancy_rate", "timestamp"
            ],
            sorting=[{"field": "wall_time_s", "order": "asc"}]
        )
        self.register_template(performance_template)
        
        # Safety template focused on safety metrics
        safety_template = ExportTemplate(
            name="safety",
            description="Safety-focused template",
            fields=[
                "task_id", "success", "safety_incidents", "recovered", "notes", "timestamp"
            ],
            filters={"safety_incidents": {"greater_than": 0}},
            sorting=[{"field": "safety_incidents", "order": "desc"}]
        )
        self.register_template(safety_template)
    
    def _register_baseline_configurations(self) -> None:
        """Register predefined baseline configurations."""
        # Regression baseline - minimal fields for quick regression testing
        regression_template = ExportTemplate(
            name="regression_baseline",
            description="Baseline configuration for regression testing",
            fields=["task_id", "success", "turns", "wall_time_s"],
            sorting=[{"field": "task_id", "order": "asc"}]
        )
        self._baseline_configs[BaselineConfiguration.REGRESSION] = regression_template
        
        # Mid-fidelity baseline - balanced evaluation
        mid_fidelity_template = ExportTemplate(
            name="mid_fidelity_baseline",
            description="Baseline configuration for mid-fidelity evaluation",
            fields=[
                "task_id", "success", "turns", "steps", "wall_time_s", 
                "cost_usd", "files_touched", "safety_incidents"
            ],
            sorting=[{"field": "success", "order": "desc"}, {"field": "wall_time_s", "order": "asc"}]
        )
        self._baseline_configs[BaselineConfiguration.MID_FIDELITY] = mid_fidelity_template
        
        # Milestone baseline - comprehensive evaluation
        milestone_template = ExportTemplate(
            name="milestone_baseline",
            description="Baseline configuration for milestone evaluation",
            fields=[
                "run_id", "task_id", "sample_id", "success", "turns", "steps",
                "wall_time_s", "token_in", "token_out", "cost_usd", "files_touched",
                "edit_added", "edit_deleted", "redundancy_rate", "recovered",
                "safety_incidents", "notes", "timestamp"
            ],
            sorting=[
                {"field": "success", "order": "desc"},
                {"field": "cost_usd", "order": "asc"},
                {"field": "wall_time_s", "order": "asc"}
            ]
        )
        self._baseline_configs[BaselineConfiguration.MILESTONE] = milestone_template
    
    def register_handler(self, handler: ExportHandler) -> None:
        """Register an export handler.
        
        Args:
            handler: Export handler to register
        """
        self._handlers.append(handler)
        self._logger.info(f"Registered export handler: {handler.__class__.__name__}")
    
    def register_template(self, template: ExportTemplate) -> None:
        """Register an export template.
        
        Args:
            template: Export template to register
        """
        self._templates[template.name] = template
        self._logger.info(f"Registered export template: {template.name}")
    
    def get_template(self, name: str) -> Optional[ExportTemplate]:
        """Get an export template by name.
        
        Args:
            name: Template name
            
        Returns:
            Export template or None if not found
        """
        return self._templates.get(name)
    
    def get_baseline_template(self, baseline: BaselineConfiguration) -> ExportTemplate:
        """Get a baseline configuration template.
        
        Args:
            baseline: Baseline configuration
            
        Returns:
            Export template for the baseline
        """
        return self._baseline_configs[baseline]
    
    def list_templates(self) -> List[str]:
        """List all available template names.
        
        Returns:
            List of template names
        """
        return list(self._templates.keys())
    
    def list_supported_formats(self) -> List[ExportFormat]:
        """List all supported export formats.
        
        Returns:
            List of supported formats
        """
        supported_formats = []
        for format in ExportFormat:
            if self._find_handler(format):
                supported_formats.append(format)
        return supported_formats
    
    def export_results(
        self,
        results: List[Union[EvaluationResult, StandardizedOutput, Dict[str, Any]]],
        config: ExportConfiguration
    ) -> str:
        """Export evaluation results to the specified format.
        
        Args:
            results: List of results to export
            config: Export configuration
            
        Returns:
            Path to exported file
            
        Raises:
            ConfigurationError: If configuration is invalid
            ValidationError: If data validation fails
        """
        if not results:
            raise ValidationError("No results to export")
        
        # Find appropriate handler
        handler = self._find_handler(config.format)
        if not handler:
            raise ConfigurationError(f"No handler available for format: {config.format}")
        
        # Validate handler dependencies
        if not handler.validate_dependencies():
            raise ConfigurationError(f"Missing dependencies for format: {config.format}")
        
        # Standardize results to dictionary format
        standardized_data = self._standardize_results(results)
        
        # Apply template if specified
        if config.template:
            self._logger.info(f"Applying template: {config.template.name}")
        
        # Export data
        try:
            output_path = handler.export(standardized_data, config)
            self._logger.info(f"Successfully exported {len(standardized_data)} results to {output_path}")
            return output_path
        except Exception as e:
            self._logger.error(f"Export failed: {e}")
            raise
    
    def export_with_baseline(
        self,
        results: List[Union[EvaluationResult, StandardizedOutput, Dict[str, Any]]],
        baseline: BaselineConfiguration,
        format: ExportFormat,
        output_path: Optional[str] = None
    ) -> str:
        """Export results using a predefined baseline configuration.
        
        Args:
            results: List of results to export
            baseline: Baseline configuration to use
            format: Export format
            output_path: Optional output path
            
        Returns:
            Path to exported file
        """
        template = self.get_baseline_template(baseline)
        config = ExportConfiguration(
            format=format,
            template=template,
            output_path=output_path
        )
        
        return self.export_results(results, config)
    
    def _find_handler(self, format: ExportFormat) -> Optional[ExportHandler]:
        """Find a handler for the specified format.
        
        Args:
            format: Export format
            
        Returns:
            Export handler or None if not found
        """
        for handler in self._handlers:
            if handler.can_handle(format):
                return handler
        return None
    
    def _standardize_results(
        self,
        results: List[Union[EvaluationResult, StandardizedOutput, Dict[str, Any]]]
    ) -> List[Dict[str, Any]]:
        """Standardize results to dictionary format for export.
        
        Args:
            results: List of results to standardize
            
        Returns:
            List of standardized dictionaries
        """
        standardized_data = []
        
        for result in results:
            if isinstance(result, dict):
                # Already a dictionary
                standardized_data.append(result)
            elif isinstance(result, StandardizedOutput):
                # Convert StandardizedOutput to dictionary
                standardized_data.append(result.to_dict())
            elif isinstance(result, EvaluationResult):
                # Convert EvaluationResult to StandardizedOutput then to dictionary
                context = ConversionContext(
                    source_adapter="export_engine",
                    target_format=ResultFormat.STANDARDIZED_OUTPUT,
                    validation_level=ValidationLevel.LENIENT
                )
                standardized_output = self._standardizer.standardize_result(result, context)
                standardized_data.append(standardized_output.to_dict())
            else:
                # Try to convert using standardizer
                try:
                    context = ConversionContext(
                        source_adapter="export_engine",
                        target_format=ResultFormat.STANDARDIZED_OUTPUT,
                        validation_level=ValidationLevel.LENIENT
                    )
                    standardized_output = self._standardizer.standardize_result(result, context)
                    standardized_data.append(standardized_output.to_dict())
                except Exception as e:
                    self._logger.warning(f"Failed to standardize result: {e}")
                    # Skip this result
                    continue
        
        return standardized_data
    
    def get_export_statistics(self) -> Dict[str, Any]:
        """Get statistics about the export engine.
        
        Returns:
            Dictionary with export statistics
        """
        return {
            "registered_handlers": len(self._handlers),
            "handler_types": [handler.__class__.__name__ for handler in self._handlers],
            "registered_templates": len(self._templates),
            "template_names": list(self._templates.keys()),
            "supported_formats": [format.value for format in self.list_supported_formats()],
            "baseline_configurations": [baseline.value for baseline in BaselineConfiguration]
        }


# Global export engine instance
_global_export_engine = ExportEngine()


def get_export_engine() -> ExportEngine:
    """Get the global export engine instance.
    
    Returns:
        Global ExportEngine instance
    """
    return _global_export_engine


def export_results(
    results: List[Union[EvaluationResult, StandardizedOutput, Dict[str, Any]]],
    format: ExportFormat,
    template_name: Optional[str] = None,
    output_path: Optional[str] = None,
    **config_kwargs
) -> str:
    """Convenience function to export results using the global export engine.
    
    Args:
        results: List of results to export
        format: Export format
        template_name: Optional template name
        output_path: Optional output path
        **config_kwargs: Additional configuration options
        
    Returns:
        Path to exported file
    """
    engine = get_export_engine()
    
    template = None
    if template_name:
        template = engine.get_template(template_name)
        if not template:
            raise ConfigurationError(f"Template not found: {template_name}")
    
    config = ExportConfiguration(
        format=format,
        template=template,
        output_path=output_path,
        **config_kwargs
    )
    
    return engine.export_results(results, config)


def export_with_baseline(
    results: List[Union[EvaluationResult, StandardizedOutput, Dict[str, Any]]],
    baseline: BaselineConfiguration,
    format: ExportFormat,
    output_path: Optional[str] = None
) -> str:
    """Convenience function to export results with baseline configuration.
    
    Args:
        results: List of results to export
        baseline: Baseline configuration
        format: Export format
        output_path: Optional output path
        
    Returns:
        Path to exported file
    """
    engine = get_export_engine()
    return engine.export_with_baseline(results, baseline, format, output_path)