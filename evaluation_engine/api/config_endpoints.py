"""
Configuration-driven evaluation API endpoints.

Provides REST API endpoints for configuration upload, validation, execution,
and result management for configuration-driven evaluations.
"""

import asyncio
import logging
import uuid
import json
import tempfile
import os
from datetime import datetime, timedelta
from typing import List, Dict, Any, Optional
from pathlib import Path

from fastapi import APIRouter, Depends, HTTPException, Query, Path as PathParam, UploadFile, File, BackgroundTasks
from fastapi.security import HTTPBearer
from fastapi.responses import FileResponse, StreamingResponse
import yaml

from .config_models import *
from .auth import AuthManager, PermissionChecker
from ..config.evaluator import ConfigDrivenEvaluator, ConfigDrivenEvaluationResult
from ..config.parser import ConfigParser
from ..config.validator import ConfigValidator
from ..config.models import EvaluationConfig

logger = logging.getLogger(__name__)

# Create router
router = APIRouter(prefix="/config", tags=["Configuration"])

# Initialize components
auth_manager = AuthManager()
permission_checker = PermissionChecker(auth_manager)
security = HTTPBearer()

# Global storage for configurations and executions (in production, use database)
_configurations: Dict[str, Dict[str, Any]] = {}
_executions: Dict[str, Dict[str, Any]] = {}
_exports: Dict[str, Dict[str, Any]] = {}

# Configuration evaluator instance
_config_evaluator = ConfigDrivenEvaluator()


# Configuration Management Endpoints
@router.post("/upload", response_model=ConfigUploadResponse)
async def upload_configuration(
    request: ConfigUploadRequest,
    current_user: dict = Depends(permission_checker.require_permission("config:create"))
):
    """
    Upload and validate a configuration file.
    
    Implements requirement 1.1: Configuration file upload and validation interface.
    """
    try:
        # Generate unique configuration ID
        config_id = str(uuid.uuid4())
        
        # Parse and validate configuration
        parser = ConfigParser()
        validator = ConfigValidator()
        
        # Create temporary file for parsing
        with tempfile.NamedTemporaryFile(mode='w', suffix=f'.{request.format.value}', delete=False) as temp_file:
            temp_file.write(request.config_content)
            temp_path = temp_file.name
        
        try:
            # Parse configuration
            config = parser.parse_config(temp_path)
            
            # Validate configuration
            validation_result = validator.validate_config(config)
            
            # Create validation response
            validation_response = ConfigValidationResponse(
                is_valid=validation_result.is_valid,
                status=ConfigValidationStatus.VALID if validation_result.is_valid else ConfigValidationStatus.INVALID,
                errors=[
                    ConfigValidationError(
                        type=error.type,
                        message=error.message,
                        severity=error.severity.value,
                        location=error.location,
                        suggestion=error.suggestion
                    ) for error in validation_result.errors
                ],
                warnings=[
                    ConfigValidationError(
                        type=warning.type,
                        message=warning.message,
                        severity=warning.severity.value,
                        location=warning.location,
                        suggestion=warning.suggestion
                    ) for warning in validation_result.warnings
                ],
                task_count=len(config.tasks),
                model_count=len(config.models),
                estimated_duration=_estimate_execution_duration(config)
            )
            
            # Store configuration
            config_data = {
                "config_id": config_id,
                "name": request.name or config.metadata.name,
                "description": request.description or config.metadata.description,
                "format": request.format,
                "content": request.config_content,
                "uploaded_at": datetime.utcnow(),
                "uploaded_by": current_user.get("user_id"),
                "size_bytes": len(request.config_content.encode('utf-8')),
                "validation": validation_response,
                "config_object": config,
                "is_valid": validation_result.is_valid
            }
            
            _configurations[config_id] = config_data
            
            logger.info(f"Configuration uploaded successfully: {config_id}")
            
            return ConfigUploadResponse(
                config_id=config_id,
                name=config_data["name"],
                format=request.format,
                validation=validation_response,
                uploaded_at=config_data["uploaded_at"],
                size_bytes=config_data["size_bytes"]
            )
            
        finally:
            # Clean up temporary file
            os.unlink(temp_path)
            
    except Exception as e:
        logger.error(f"Configuration upload failed: {str(e)}")
        raise HTTPException(status_code=400, detail=f"Configuration upload failed: {str(e)}")


@router.post("/upload-file", response_model=ConfigUploadResponse)
async def upload_configuration_file(
    file: UploadFile = File(...),
    name: Optional[str] = None,
    description: Optional[str] = None,
    current_user: dict = Depends(permission_checker.require_permission("config:create"))
):
    """
    Upload configuration from file.
    
    Implements requirement 1.1: Configuration file upload interface.
    """
    try:
        # Determine format from file extension
        file_extension = Path(file.filename).suffix.lower()
        if file_extension == '.yaml' or file_extension == '.yml':
            format_type = ConfigFormat.YAML
        elif file_extension == '.json':
            format_type = ConfigFormat.JSON
        else:
            raise HTTPException(status_code=400, detail="Unsupported file format. Use .yaml, .yml, or .json")
        
        # Read file content
        content = await file.read()
        config_content = content.decode('utf-8')
        
        # Create upload request
        upload_request = ConfigUploadRequest(
            config_content=config_content,
            format=format_type,
            name=name or Path(file.filename).stem,
            description=description
        )
        
        # Use existing upload logic
        return await upload_configuration(upload_request, current_user)
        
    except HTTPException:
        raise
    except Exception as e:
        logger.error(f"File upload failed: {str(e)}")
        raise HTTPException(status_code=400, detail=f"File upload failed: {str(e)}")


@router.post("/validate", response_model=ConfigValidationResponse)
async def validate_configuration(
    request: ConfigValidationRequest,
    current_user: dict = Depends(permission_checker.require_permission("config:read"))
):
    """
    Validate configuration without uploading.
    
    Implements requirement 1.1: Configuration validation interface.
    """
    try:
        parser = ConfigParser()
        validator = ConfigValidator()
        
        # Create temporary file for parsing
        with tempfile.NamedTemporaryFile(mode='w', suffix=f'.{request.format.value}', delete=False) as temp_file:
            temp_file.write(request.config_content)
            temp_path = temp_file.name
        
        try:
            # Parse configuration
            config = parser.parse_config(temp_path)
            
            # Validate configuration
            validation_result = validator.validate_config(config)
            
            return ConfigValidationResponse(
                is_valid=validation_result.is_valid,
                status=ConfigValidationStatus.VALID if validation_result.is_valid else ConfigValidationStatus.INVALID,
                errors=[
                    ConfigValidationError(
                        type=error.type,
                        message=error.message,
                        severity=error.severity.value,
                        location=error.location,
                        suggestion=error.suggestion
                    ) for error in validation_result.errors
                ],
                warnings=[
                    ConfigValidationError(
                        type=warning.type,
                        message=warning.message,
                        severity=warning.severity.value,
                        location=warning.location,
                        suggestion=warning.suggestion
                    ) for warning in validation_result.warnings
                ],
                task_count=len(config.tasks),
                model_count=len(config.models),
                estimated_duration=_estimate_execution_duration(config)
            )
            
        finally:
            # Clean up temporary file
            os.unlink(temp_path)
            
    except Exception as e:
        logger.error(f"Configuration validation failed: {str(e)}")
        raise HTTPException(status_code=400, detail=f"Configuration validation failed: {str(e)}")


@router.get("/", response_model=ConfigListResponse)
async def list_configurations(
    page: int = Query(1, ge=1, description="Page number"),
    page_size: int = Query(20, ge=1, le=100, description="Items per page"),
    current_user: dict = Depends(permission_checker.require_permission("config:read"))
):
    """
    List uploaded configurations.
    
    Implements requirement 1.1: Configuration management interface.
    """
    try:
        # Get all configurations
        all_configs = list(_configurations.values())
        
        # Sort by upload time (newest first)
        all_configs.sort(key=lambda x: x["uploaded_at"], reverse=True)
        
        # Paginate
        total = len(all_configs)
        start_idx = (page - 1) * page_size
        end_idx = start_idx + page_size
        page_configs = all_configs[start_idx:end_idx]
        
        # Convert to response format
        config_infos = []
        for config_data in page_configs:
            config_infos.append(ConfigInfo(
                config_id=config_data["config_id"],
                name=config_data["name"],
                description=config_data["description"],
                format=config_data["format"],
                uploaded_at=config_data["uploaded_at"],
                size_bytes=config_data["size_bytes"],
                is_valid=config_data["is_valid"],
                task_count=config_data["validation"].task_count or 0,
                model_count=config_data["validation"].model_count or 0
            ))
        
        return ConfigListResponse(
            configurations=config_infos,
            total=total,
            page=page,
            page_size=page_size,
            has_next=end_idx < total,
            has_previous=page > 1
        )
        
    except Exception as e:
        logger.error(f"Failed to list configurations: {str(e)}")
        raise HTTPException(status_code=500, detail="Failed to list configurations")


@router.get("/{config_id}", response_model=ConfigDetail)
async def get_configuration(
    config_id: str = PathParam(..., description="Configuration ID"),
    current_user: dict = Depends(permission_checker.require_permission("config:read"))
):
    """
    Get configuration details.
    
    Implements requirement 1.1: Configuration retrieval interface.
    """
    try:
        if config_id not in _configurations:
            raise HTTPException(status_code=404, detail="Configuration not found")
        
        config_data = _configurations[config_id]
        config_obj = config_data["config_object"]
        
        return ConfigDetail(
            config_id=config_data["config_id"],
            name=config_data["name"],
            description=config_data["description"],
            format=config_data["format"],
            uploaded_at=config_data["uploaded_at"],
            size_bytes=config_data["size_bytes"],
            is_valid=config_data["is_valid"],
            task_count=len(config_obj.tasks),
            model_count=len(config_obj.models),
            content=config_data["content"],
            validation=config_data["validation"],
            metadata={
                "name": config_obj.metadata.name,
                "version": config_obj.metadata.version,
                "author": config_obj.metadata.author,
                "description": config_obj.metadata.description
            },
            tasks=[
                {
                    "name": task.name,
                    "description": task.description,
                    "model_ref": task.model_ref,
                    "task_name": task.task_name,
                    "depends_on": task.depends_on
                } for task in config_obj.tasks
            ],
            models={
                name: {
                    "name": model.name,
                    "type": model.type,
                    "model_name": model.model_name,
                    "parameters": model.parameters
                } for name, model in config_obj.models.items()
            }
        )
        
    except HTTPException:
        raise
    except Exception as e:
        logger.error(f"Failed to get configuration: {str(e)}")
        raise HTTPException(status_code=500, detail="Failed to get configuration")


@router.delete("/{config_id}")
async def delete_configuration(
    config_id: str = PathParam(..., description="Configuration ID"),
    current_user: dict = Depends(permission_checker.require_permission("config:delete"))
):
    """
    Delete configuration.
    
    Implements requirement 1.1: Configuration management interface.
    """
    try:
        if config_id not in _configurations:
            raise HTTPException(status_code=404, detail="Configuration not found")
        
        # Check if configuration is being used in active executions
        active_executions = [
            exec_data for exec_data in _executions.values()
            if exec_data.get("config_id") == config_id and 
               exec_data.get("status") in [ConfigEvaluationStatus.RUNNING, ConfigEvaluationStatus.VALIDATING, ConfigEvaluationStatus.BUILDING]
        ]
        
        if active_executions:
            raise HTTPException(
                status_code=409, 
                detail="Cannot delete configuration with active executions"
            )
        
        del _configurations[config_id]
        logger.info(f"Configuration deleted: {config_id}")
        
        return {"message": "Configuration deleted successfully"}
        
    except HTTPException:
        raise
    except Exception as e:
        logger.error(f"Failed to delete configuration: {str(e)}")
        raise HTTPException(status_code=500, detail="Failed to delete configuration")


# Execution Endpoints
@router.post("/execute", response_model=ConfigExecutionResponse)
async def execute_configuration(
    request: ConfigExecutionRequest,
    background_tasks: BackgroundTasks,
    current_user: dict = Depends(permission_checker.require_permission("config:execute"))
):
    """
    Execute configuration-driven evaluation.
    
    Implements requirement 1.1: Configuration execution interface.
    """
    try:
        # Generate unique evaluation ID
        evaluation_id = str(uuid.uuid4())
        
        # Determine configuration source
        config_obj = None
        config_id = None
        
        if request.config_id:
            # Use uploaded configuration
            if request.config_id not in _configurations:
                raise HTTPException(status_code=404, detail="Configuration not found")
            
            config_data = _configurations[request.config_id]
            if not config_data["is_valid"]:
                raise HTTPException(status_code=400, detail="Configuration is not valid")
            
            config_obj = config_data["config_object"]
            config_id = request.config_id
            
        else:
            # Use inline configuration
            parser = ConfigParser()
            
            # Create temporary file for parsing
            with tempfile.NamedTemporaryFile(mode='w', suffix=f'.{request.format.value}', delete=False) as temp_file:
                temp_file.write(request.config_content)
                temp_path = temp_file.name
            
            try:
                config_obj = parser.parse_config(temp_path)
            finally:
                os.unlink(temp_path)
        
        # Create execution record
        execution_data = {
            "evaluation_id": evaluation_id,
            "config_id": config_id,
            "status": ConfigEvaluationStatus.CREATED,
            "created_at": datetime.utcnow(),
            "created_by": current_user.get("user_id"),
            "task_filter": request.task_filter,
            "parameter_overrides": request.parameter_overrides,
            "fail_fast": request.fail_fast,
            "dry_run": request.dry_run,
            "task_count": len(config_obj.tasks),
            "progress": 0.0,
            "task_details": []
        }
        
        _executions[evaluation_id] = execution_data
        
        # Start execution in background
        background_tasks.add_task(
            _execute_configuration_background,
            evaluation_id,
            config_obj,
            request.task_filter,
            request.parameter_overrides,
            request.fail_fast,
            request.dry_run
        )
        
        logger.info(f"Configuration execution started: {evaluation_id}")
        
        return ConfigExecutionResponse(
            evaluation_id=evaluation_id,
            config_id=config_id,
            status=ConfigEvaluationStatus.CREATED,
            message="Evaluation started successfully",
            created_at=execution_data["created_at"],
            estimated_completion=_estimate_completion_time(config_obj, request.dry_run),
            task_count=len(config_obj.tasks),
            dry_run=request.dry_run
        )
        
    except HTTPException:
        raise
    except Exception as e:
        logger.error(f"Configuration execution failed: {str(e)}")
        raise HTTPException(status_code=400, detail=f"Configuration execution failed: {str(e)}")


@router.get("/executions", response_model=ConfigExecutionListResponse)
async def list_executions(
    page: int = Query(1, ge=1, description="Page number"),
    page_size: int = Query(20, ge=1, le=100, description="Items per page"),
    status: Optional[ConfigEvaluationStatus] = Query(None, description="Filter by status"),
    current_user: dict = Depends(permission_checker.require_permission("config:read"))
):
    """
    List configuration executions.
    
    Implements requirement 1.1: Execution management interface.
    """
    try:
        # Get all executions
        all_executions = list(_executions.values())
        
        # Filter by status if specified
        if status:
            all_executions = [exec_data for exec_data in all_executions if exec_data["status"] == status]
        
        # Sort by creation time (newest first)
        all_executions.sort(key=lambda x: x["created_at"], reverse=True)
        
        # Paginate
        total = len(all_executions)
        start_idx = (page - 1) * page_size
        end_idx = start_idx + page_size
        page_executions = all_executions[start_idx:end_idx]
        
        # Convert to response format
        execution_statuses = []
        for exec_data in page_executions:
            execution_statuses.append(_create_execution_status(exec_data))
        
        return ConfigExecutionListResponse(
            executions=execution_statuses,
            total=total,
            page=page,
            page_size=page_size,
            has_next=end_idx < total,
            has_previous=page > 1
        )
        
    except Exception as e:
        logger.error(f"Failed to list executions: {str(e)}")
        raise HTTPException(status_code=500, detail="Failed to list executions")


@router.get("/executions/{evaluation_id}", response_model=ConfigExecutionStatus)
async def get_execution_status(
    evaluation_id: str = PathParam(..., description="Evaluation ID"),
    current_user: dict = Depends(permission_checker.require_permission("config:read"))
):
    """
    Get execution status.
    
    Implements requirement 1.1: Task status query interface.
    """
    try:
        if evaluation_id not in _executions:
            raise HTTPException(status_code=404, detail="Execution not found")
        
        execution_data = _executions[evaluation_id]
        return _create_execution_status(execution_data)
        
    except HTTPException:
        raise
    except Exception as e:
        logger.error(f"Failed to get execution status: {str(e)}")
        raise HTTPException(status_code=500, detail="Failed to get execution status")


@router.get("/executions/{evaluation_id}/results", response_model=ConfigExecutionResults)
async def get_execution_results(
    evaluation_id: str = PathParam(..., description="Evaluation ID"),
    current_user: dict = Depends(permission_checker.require_permission("config:read"))
):
    """
    Get execution results.
    
    Implements requirement 1.1: Result retrieval interface.
    """
    try:
        if evaluation_id not in _executions:
            raise HTTPException(status_code=404, detail="Execution not found")
        
        execution_data = _executions[evaluation_id]
        
        if execution_data["status"] not in [ConfigEvaluationStatus.COMPLETED, ConfigEvaluationStatus.FAILED]:
            raise HTTPException(status_code=409, detail="Execution not completed")
        
        # Get results from execution data
        result_data = execution_data.get("result_data", {})
        
        return ConfigExecutionResults(
            evaluation_id=evaluation_id,
            config_id=execution_data.get("config_id"),
            config_metadata=result_data.get("config_metadata", {}),
            status=execution_data["status"],
            start_time=execution_data.get("start_time", execution_data["created_at"]),
            end_time=execution_data.get("end_time", execution_data["created_at"]),
            total_execution_time=result_data.get("total_execution_time", 0.0),
            total_tasks=execution_data["task_count"],
            completed_tasks=result_data.get("completed_tasks", 0),
            failed_tasks=result_data.get("failed_tasks", 0),
            skipped_tasks=result_data.get("skipped_tasks", 0),
            success_rate=result_data.get("success_rate", 0.0),
            task_results=result_data.get("task_results", {}),
            task_summaries=result_data.get("task_summaries", {}),
            execution_order=result_data.get("execution_order", []),
            validation_errors=result_data.get("validation_errors", []),
            validation_warnings=result_data.get("validation_warnings", []),
            export_formats=["json", "csv", "xlsx"],
            download_urls={}  # Would be populated with actual download URLs
        )
        
    except HTTPException:
        raise
    except Exception as e:
        logger.error(f"Failed to get execution results: {str(e)}")
        raise HTTPException(status_code=500, detail="Failed to get execution results")


@router.post("/executions/{evaluation_id}/cancel")
async def cancel_execution(
    evaluation_id: str = PathParam(..., description="Evaluation ID"),
    current_user: dict = Depends(permission_checker.require_permission("config:execute"))
):
    """
    Cancel running execution.
    
    Implements requirement 1.1: Execution control interface.
    """
    try:
        if evaluation_id not in _executions:
            raise HTTPException(status_code=404, detail="Execution not found")
        
        execution_data = _executions[evaluation_id]
        
        if execution_data["status"] not in [ConfigEvaluationStatus.RUNNING, ConfigEvaluationStatus.VALIDATING, ConfigEvaluationStatus.BUILDING]:
            raise HTTPException(status_code=409, detail="Execution cannot be cancelled")
        
        # Update status
        execution_data["status"] = ConfigEvaluationStatus.CANCELLED
        execution_data["end_time"] = datetime.utcnow()
        execution_data["error_message"] = "Execution cancelled by user"
        
        logger.info(f"Execution cancelled: {evaluation_id}")
        
        return {"message": "Execution cancelled successfully"}
        
    except HTTPException:
        raise
    except Exception as e:
        logger.error(f"Failed to cancel execution: {str(e)}")
        raise HTTPException(status_code=500, detail="Failed to cancel execution")


# Export Endpoints
@router.post("/executions/{evaluation_id}/export", response_model=ConfigExportResponse)
async def export_execution_results(
    request: ConfigExportRequest,
    background_tasks: BackgroundTasks,
    evaluation_id: str = PathParam(..., description="Evaluation ID"),
    current_user: dict = Depends(permission_checker.require_permission("config:read"))
):
    """
    Export execution results.
    
    Implements requirement 1.1: Result export interface.
    """
    try:
        if evaluation_id not in _executions:
            raise HTTPException(status_code=404, detail="Execution not found")
        
        execution_data = _executions[evaluation_id]
        
        if execution_data["status"] != ConfigEvaluationStatus.COMPLETED:
            raise HTTPException(status_code=409, detail="Execution not completed")
        
        # Generate export ID
        export_id = str(uuid.uuid4())
        
        # Create export record
        export_data = {
            "export_id": export_id,
            "evaluation_id": evaluation_id,
            "format": request.format,
            "status": "processing",
            "created_at": datetime.utcnow(),
            "created_by": current_user.get("user_id"),
            "include_raw_results": request.include_raw_results,
            "include_config": request.include_config
        }
        
        _exports[export_id] = export_data
        
        # Start export in background
        background_tasks.add_task(
            _export_results_background,
            export_id,
            execution_data,
            request
        )
        
        return ConfigExportResponse(
            export_id=export_id,
            evaluation_id=evaluation_id,
            format=request.format,
            status="processing",
            created_at=export_data["created_at"],
            estimated_completion=datetime.utcnow() + timedelta(minutes=5)
        )
        
    except HTTPException:
        raise
    except Exception as e:
        logger.error(f"Failed to start export: {str(e)}")
        raise HTTPException(status_code=500, detail="Failed to start export")


@router.get("/exports/{export_id}/status", response_model=ConfigExportResponse)
async def get_export_status(
    export_id: str = PathParam(..., description="Export ID"),
    current_user: dict = Depends(permission_checker.require_permission("config:read"))
):
    """
    Get export status.
    
    Implements requirement 1.1: Export status tracking.
    """
    try:
        if export_id not in _exports:
            raise HTTPException(status_code=404, detail="Export not found")
        
        export_data = _exports[export_id]
        
        return ConfigExportResponse(
            export_id=export_id,
            evaluation_id=export_data["evaluation_id"],
            format=export_data["format"],
            status=export_data["status"],
            created_at=export_data["created_at"],
            estimated_completion=export_data.get("estimated_completion"),
            download_url=export_data.get("download_url"),
            file_size=export_data.get("file_size"),
            expires_at=export_data.get("expires_at")
        )
        
    except HTTPException:
        raise
    except Exception as e:
        logger.error(f"Failed to get export status: {str(e)}")
        raise HTTPException(status_code=500, detail="Failed to get export status")


@router.get("/exports/{export_id}/download")
async def download_export(
    export_id: str = PathParam(..., description="Export ID"),
    current_user: dict = Depends(permission_checker.require_permission("config:read"))
):
    """
    Download exported results.
    
    Implements requirement 1.1: Result download interface.
    """
    try:
        if export_id not in _exports:
            raise HTTPException(status_code=404, detail="Export not found")
        
        export_data = _exports[export_id]
        
        if export_data["status"] != "completed":
            raise HTTPException(status_code=409, detail="Export not completed")
        
        file_path = export_data.get("file_path")
        if not file_path or not os.path.exists(file_path):
            raise HTTPException(status_code=404, detail="Export file not found")
        
        # Return file response
        filename = f"evaluation_{export_data['evaluation_id']}.{export_data['format']}"
        return FileResponse(
            path=file_path,
            filename=filename,
            media_type="application/octet-stream"
        )
        
    except HTTPException:
        raise
    except Exception as e:
        logger.error(f"Failed to download export: {str(e)}")
        raise HTTPException(status_code=500, detail="Failed to download export")


# Utility Functions
def _estimate_execution_duration(config: EvaluationConfig) -> int:
    """Estimate execution duration in seconds."""
    # Simple estimation based on task count and complexity
    base_time_per_task = 60  # 1 minute per task
    return len(config.tasks) * base_time_per_task


def _estimate_completion_time(config: EvaluationConfig, dry_run: bool) -> datetime:
    """Estimate completion time."""
    if dry_run:
        return datetime.utcnow() + timedelta(seconds=30)
    
    duration = _estimate_execution_duration(config)
    return datetime.utcnow() + timedelta(seconds=duration)


def _create_execution_status(execution_data: Dict[str, Any]) -> ConfigExecutionStatus:
    """Create execution status response from execution data."""
    task_details = []
    for task_detail in execution_data.get("task_details", []):
        task_details.append(TaskExecutionInfo(
            task_name=task_detail["task_name"],
            status=task_detail["status"],
            progress=task_detail.get("progress", 0.0),
            start_time=task_detail.get("start_time"),
            end_time=task_detail.get("end_time"),
            execution_time=task_detail.get("execution_time"),
            error_message=task_detail.get("error_message"),
            metrics_summary=task_detail.get("metrics_summary")
        ))
    
    # Calculate task counts
    completed_tasks = len([t for t in task_details if t.status == TaskExecutionStatus.COMPLETED])
    failed_tasks = len([t for t in task_details if t.status == TaskExecutionStatus.FAILED])
    running_tasks = len([t for t in task_details if t.status == TaskExecutionStatus.RUNNING])
    pending_tasks = execution_data["task_count"] - completed_tasks - failed_tasks - running_tasks
    
    return ConfigExecutionStatus(
        evaluation_id=execution_data["evaluation_id"],
        config_id=execution_data.get("config_id"),
        status=execution_data["status"],
        progress=execution_data.get("progress", 0.0),
        start_time=execution_data.get("start_time"),
        end_time=execution_data.get("end_time"),
        execution_time=execution_data.get("execution_time"),
        total_tasks=execution_data["task_count"],
        completed_tasks=completed_tasks,
        failed_tasks=failed_tasks,
        running_tasks=running_tasks,
        pending_tasks=pending_tasks,
        current_task=execution_data.get("current_task"),
        task_details=task_details,
        error_message=execution_data.get("error_message"),
        dry_run=execution_data.get("dry_run", False),
        fail_fast=execution_data.get("fail_fast", False)
    )


async def _execute_configuration_background(
    evaluation_id: str,
    config: EvaluationConfig,
    task_filter: Optional[List[str]],
    parameter_overrides: Optional[Dict[str, Any]],
    fail_fast: bool,
    dry_run: bool
):
    """Execute configuration in background."""
    try:
        execution_data = _executions[evaluation_id]
        
        # Update status
        execution_data["status"] = ConfigEvaluationStatus.RUNNING
        execution_data["start_time"] = datetime.utcnow()
        
        # Execute using config evaluator
        if config.metadata.name:
            # Create temporary config file for evaluator
            with tempfile.NamedTemporaryFile(mode='w', suffix='.yaml', delete=False) as temp_file:
                yaml.dump(config.__dict__, temp_file, default_flow_style=False)
                temp_path = temp_file.name
            
            try:
                result = _config_evaluator.run_from_config(
                    temp_path,
                    task_filter=task_filter,
                    parameter_overrides=parameter_overrides,
                    fail_fast=fail_fast,
                    dry_run=dry_run
                )
                
                # Update execution with results
                execution_data["status"] = ConfigEvaluationStatus.COMPLETED
                execution_data["end_time"] = result.end_time
                execution_data["execution_time"] = result.total_execution_time
                execution_data["progress"] = 1.0
                execution_data["result_data"] = result.to_dict()
                
            finally:
                os.unlink(temp_path)
        else:
            # Use dictionary-based execution
            result = _config_evaluator.run_from_config_dict(
                config.__dict__,
                task_filter=task_filter,
                parameter_overrides=parameter_overrides,
                fail_fast=fail_fast,
                dry_run=dry_run
            )
            
            # Update execution with results
            execution_data["status"] = ConfigEvaluationStatus.COMPLETED
            execution_data["end_time"] = result.end_time
            execution_data["execution_time"] = result.total_execution_time
            execution_data["progress"] = 1.0
            execution_data["result_data"] = result.to_dict()
        
        logger.info(f"Configuration execution completed: {evaluation_id}")
        
    except Exception as e:
        logger.error(f"Configuration execution failed: {evaluation_id}: {str(e)}")
        
        # Update execution with error
        execution_data = _executions[evaluation_id]
        execution_data["status"] = ConfigEvaluationStatus.FAILED
        execution_data["end_time"] = datetime.utcnow()
        execution_data["error_message"] = str(e)


async def _export_results_background(
    export_id: str,
    execution_data: Dict[str, Any],
    request: ConfigExportRequest
):
    """Export results in background."""
    try:
        export_data = _exports[export_id]
        
        # Simulate export processing
        await asyncio.sleep(2)  # Simulate processing time
        
        # Create export file (simplified implementation)
        export_dir = tempfile.mkdtemp()
        filename = f"evaluation_{request.evaluation_id}.{request.format}"
        file_path = os.path.join(export_dir, filename)
        
        result_data = execution_data.get("result_data", {})
        
        if request.format == "json":
            with open(file_path, 'w') as f:
                json.dump(result_data, f, indent=2, default=str)
        elif request.format == "csv":
            # Simplified CSV export
            import csv
            with open(file_path, 'w', newline='') as f:
                writer = csv.writer(f)
                writer.writerow(["Task", "Status", "Execution Time", "Success Rate"])
                for task_name, task_summary in result_data.get("task_summaries", {}).items():
                    writer.writerow([
                        task_name,
                        task_summary.get("status", "unknown"),
                        task_summary.get("execution_time", 0),
                        result_data.get("success_rate", 0)
                    ])
        
        # Update export data
        export_data["status"] = "completed"
        export_data["file_path"] = file_path
        export_data["file_size"] = os.path.getsize(file_path)
        export_data["download_url"] = f"/api/v1/config/exports/{export_id}/download"
        export_data["expires_at"] = datetime.utcnow() + timedelta(hours=24)
        
        logger.info(f"Export completed: {export_id}")
        
    except Exception as e:
        logger.error(f"Export failed: {export_id}: {str(e)}")
        
        # Update export with error
        export_data = _exports[export_id]
        export_data["status"] = "failed"
        export_data["error_message"] = str(e)