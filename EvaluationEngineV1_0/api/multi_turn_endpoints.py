"""
Multi-Turn Evaluation API Endpoints

Provides REST API endpoints for multi-turn evaluation orchestration,
monitoring, and control.
"""

from fastapi import APIRouter, Depends, HTTPException, Query, Path, BackgroundTasks
from fastapi.security import HTTPBearer
from typing import List, Dict, Any, Optional
import logging
import asyncio
from datetime import datetime, timedelta

from .models import (
    MultiTurnEvaluationRequest, MultiTurnEvaluationResponse, MultiTurnEvaluationStatus,
    MultiTurnEvaluationStatusResponse, MultiTurnEvaluationResults, TurnExecutionRequest, 
    EvaluationControlRequest, FeedbackConfigRequest, SafetyConfigRequest, TurnResult, 
    MultiTurnTaskResult, OrchestratorStatus, MetricsSnapshot, ErrorResponse, PaginatedResponse, 
    FeedbackStrategy, SafetyLevel, TerminationReason
)
from ..core.orchestrator import MultiTurnOrchestrator
from ..core.data_models import MultiTurnConfig, FeedbackConfig, SafetyConfig
from ..core.unified_task_registry import UnifiedTaskRegistry
from ..core.metrics_engine import MetricsEngine
from ..core.exceptions import EvaluationError, SafetyViolationError

logger = logging.getLogger(__name__)

# Create router
router = APIRouter(prefix="/multi-turn", tags=["Multi-Turn Evaluation"])

# Security scheme
security = HTTPBearer()

# Global components (would be injected in production)
orchestrator = None
task_registry = None
metrics_engine = None
active_evaluations: Dict[str, Dict[str, Any]] = {}


def get_orchestrator() -> MultiTurnOrchestrator:
    """Get orchestrator instance."""
    global orchestrator
    if orchestrator is None:
        from ..core.policy_engine import PolicyEngine
        from ..core.feedback_processor import FeedbackProcessor
        from ..core.safety_guard import SafetyGuard
        from ..core.metrics_engine import MetricsEngine
        
        policy_engine = PolicyEngine()
        feedback_processor = FeedbackProcessor(FeedbackConfig())
        safety_guard = SafetyGuard(SafetyConfig())
        metrics_engine = MetricsEngine()
        
        orchestrator = MultiTurnOrchestrator(
            policy_engine=policy_engine,
            feedback_processor=feedback_processor,
            safety_guard=safety_guard,
            metrics_engine=metrics_engine
        )
    return orchestrator


def get_task_registry() -> UnifiedTaskRegistry:
    """Get task registry instance."""
    global task_registry
    if task_registry is None:
        task_registry = UnifiedTaskRegistry()
    return task_registry


def get_metrics_engine() -> MetricsEngine:
    """Get metrics engine instance."""
    global metrics_engine
    if metrics_engine is None:
        metrics_engine = MetricsEngine()
    return metrics_engine


# Authentication dependency (placeholder)
async def get_current_user(token: str = Depends(security)):
    """Get current authenticated user."""
    # This would implement actual JWT token validation
    return {"user_id": "user_123", "username": "test_user", "roles": ["user"]}


async def require_admin(current_user: dict = Depends(get_current_user)):
    """Require admin role."""
    if "admin" not in current_user.get("roles", []):
        raise HTTPException(status_code=403, detail="Admin access required")
    return current_user


# Multi-Turn Evaluation Endpoints

@router.post("/evaluations", response_model=MultiTurnEvaluationResponse)
async def create_multi_turn_evaluation(
    request: MultiTurnEvaluationRequest,
    background_tasks: BackgroundTasks,
    current_user: dict = Depends(get_current_user)
):
    """
    Create a new multi-turn evaluation.
    
    Implements requirement 9.1: REST API endpoints for multi-turn evaluation.
    """
    try:
        # Generate evaluation ID
        evaluation_id = f"mt_eval_{datetime.utcnow().strftime('%Y%m%d_%H%M%S')}_{current_user['user_id']}"
        
        # Validate tasks
        registry = get_task_registry()
        for task_id in request.task_ids:
            if not registry.has_task(task_id):
                raise HTTPException(status_code=400, detail=f"Task not found: {task_id}")
            
            # Ensure task is multi-turn
            task_type = registry.get_task_type(task_id)
            if task_type != "multi_turn":
                raise HTTPException(status_code=400, detail=f"Task {task_id} is not a multi-turn task")
        
        # Create evaluation configuration
        config = MultiTurnConfig(
            max_turns=request.max_turns,
            conversation_timeout=request.timeout_seconds,
            enable_context_retention=request.enable_context_retention,
            termination_conditions=["success", "max_turns", "timeout", "safety_violation"],
            feedback_config=FeedbackConfig(
                context_strategy=request.feedback_strategy.value,
                max_feedback_length=10000 if request.feedback_strategy == FeedbackStrategy.FULL else 5000
            ),
            safety_config=SafetyConfig(
                allowed_tools=["python", "bash", "git"] if request.safety_level != SafetyLevel.STRICT else ["python"],
                enable_sandboxing=True,
                max_execution_time=300 if request.safety_level == SafetyLevel.STRICT else 600
            )
        )
        
        # Store evaluation metadata
        active_evaluations[evaluation_id] = {
            "id": evaluation_id,
            "model_id": request.model_id,
            "task_ids": request.task_ids,
            "config": config,
            "status": MultiTurnEvaluationStatus.CREATED,
            "created_at": datetime.utcnow(),
            "created_by": current_user["user_id"],
            "metadata": request.metadata or {},
            "progress": 0.0,
            "current_task": None,
            "current_turn": None,
            "completed_tasks": 0,
            "total_tasks": len(request.task_ids),
            "safety_incidents": 0,
            "total_turns_executed": 0
        }
        
        # Start evaluation in background
        background_tasks.add_task(
            _execute_multi_turn_evaluation,
            evaluation_id,
            request.model_id,
            request.task_ids,
            config
        )
        
        # Calculate estimated duration
        estimated_duration = len(request.task_ids) * request.max_turns * 30  # 30 seconds per turn estimate
        
        return MultiTurnEvaluationResponse(
            evaluation_id=evaluation_id,
            status=MultiTurnEvaluationStatus.CREATED,
            message="Multi-turn evaluation created successfully",
            created_at=datetime.utcnow(),
            estimated_duration=estimated_duration,
            websocket_url=f"/ws/multi-turn/{evaluation_id}"
        )
        
    except HTTPException:
        raise
    except Exception as e:
        logger.error(f"Error creating multi-turn evaluation: {str(e)}")
        raise HTTPException(status_code=500, detail="Failed to create evaluation")


@router.get("/evaluations/{evaluation_id}/status", response_model=MultiTurnEvaluationStatusResponse)
async def get_evaluation_status(
    evaluation_id: str = Path(..., description="Evaluation ID"),
    current_user: dict = Depends(get_current_user)
):
    """
    Get multi-turn evaluation status.
    
    Implements requirement 9.1: Orchestrator control and monitoring endpoints.
    """
    try:
        if evaluation_id not in active_evaluations:
            raise HTTPException(status_code=404, detail="Evaluation not found")
        
        eval_data = active_evaluations[evaluation_id]
        
        # Calculate estimated completion
        estimated_completion = None
        if eval_data["status"] == MultiTurnEvaluationStatus.RUNNING and eval_data["progress"] > 0:
            elapsed = (datetime.utcnow() - eval_data["created_at"]).total_seconds()
            estimated_total = elapsed / eval_data["progress"]
            estimated_completion = eval_data["created_at"] + timedelta(seconds=estimated_total)
        
        return MultiTurnEvaluationStatusResponse(
            evaluation_id=evaluation_id,
            status=eval_data["status"],
            progress=eval_data["progress"],
            current_task=eval_data["current_task"],
            current_turn=eval_data["current_turn"],
            completed_tasks=eval_data["completed_tasks"],
            total_tasks=eval_data["total_tasks"],
            start_time=eval_data.get("start_time"),
            estimated_completion=estimated_completion,
            error_message=eval_data.get("error_message"),
            safety_incidents=eval_data["safety_incidents"],
            total_turns_executed=eval_data["total_turns_executed"]
        )
        
    except HTTPException:
        raise
    except Exception as e:
        logger.error(f"Error getting evaluation status: {str(e)}")
        raise HTTPException(status_code=500, detail="Failed to get evaluation status")


@router.get("/evaluations/{evaluation_id}/results", response_model=MultiTurnEvaluationResults)
async def get_evaluation_results(
    evaluation_id: str = Path(..., description="Evaluation ID"),
    current_user: dict = Depends(get_current_user)
):
    """
    Get multi-turn evaluation results.
    
    Implements requirement 9.1: Results retrieval endpoints.
    """
    try:
        if evaluation_id not in active_evaluations:
            raise HTTPException(status_code=404, detail="Evaluation not found")
        
        eval_data = active_evaluations[evaluation_id]
        
        if eval_data["status"] not in [MultiTurnEvaluationStatus.COMPLETED, MultiTurnEvaluationStatus.FAILED]:
            raise HTTPException(status_code=400, detail="Evaluation not completed")
        
        # Get results from storage (placeholder implementation)
        results = eval_data.get("results", {})
        
        return MultiTurnEvaluationResults(
            evaluation_id=evaluation_id,
            model_id=eval_data["model_id"],
            task_results=results.get("task_results", []),
            aggregated_metrics=results.get("aggregated_metrics", {}),
            overall_success_rate=results.get("overall_success_rate", 0.0),
            average_turns_per_task=results.get("average_turns_per_task", 0.0),
            total_execution_time=results.get("total_execution_time", 0.0),
            total_tokens=results.get("total_tokens", 0),
            total_cost=results.get("total_cost", 0.0),
            safety_summary=results.get("safety_summary", {}),
            completed_at=eval_data.get("completed_at", datetime.utcnow())
        )
        
    except HTTPException:
        raise
    except Exception as e:
        logger.error(f"Error getting evaluation results: {str(e)}")
        raise HTTPException(status_code=500, detail="Failed to get evaluation results")


@router.post("/evaluations/{evaluation_id}/control")
async def control_evaluation(
    evaluation_id: str = Path(..., description="Evaluation ID"),
    request: EvaluationControlRequest = ...,
    current_user: dict = Depends(get_current_user)
):
    """
    Control multi-turn evaluation (pause, resume, cancel, terminate).
    
    Implements requirement 9.1: Orchestrator control endpoints.
    """
    try:
        if evaluation_id not in active_evaluations:
            raise HTTPException(status_code=404, detail="Evaluation not found")
        
        eval_data = active_evaluations[evaluation_id]
        current_status = eval_data["status"]
        
        # Validate control action
        valid_actions = {
            "pause": [MultiTurnEvaluationStatus.RUNNING],
            "resume": [MultiTurnEvaluationStatus.PAUSED],
            "cancel": [MultiTurnEvaluationStatus.CREATED, MultiTurnEvaluationStatus.RUNNING, MultiTurnEvaluationStatus.PAUSED],
            "terminate": [MultiTurnEvaluationStatus.RUNNING, MultiTurnEvaluationStatus.PAUSED]
        }
        
        if request.action not in valid_actions:
            raise HTTPException(status_code=400, detail=f"Invalid action: {request.action}")
        
        if current_status not in valid_actions[request.action]:
            raise HTTPException(
                status_code=400, 
                detail=f"Cannot {request.action} evaluation in {current_status} status"
            )
        
        # Execute control action
        if request.action == "pause":
            eval_data["status"] = MultiTurnEvaluationStatus.PAUSED
            eval_data["paused_at"] = datetime.utcnow()
            eval_data["pause_reason"] = request.reason
            
        elif request.action == "resume":
            eval_data["status"] = MultiTurnEvaluationStatus.RUNNING
            eval_data["resumed_at"] = datetime.utcnow()
            
        elif request.action == "cancel":
            eval_data["status"] = MultiTurnEvaluationStatus.CANCELLED
            eval_data["cancelled_at"] = datetime.utcnow()
            eval_data["cancellation_reason"] = request.reason
            
        elif request.action == "terminate":
            eval_data["status"] = MultiTurnEvaluationStatus.TERMINATED
            eval_data["terminated_at"] = datetime.utcnow()
            eval_data["termination_reason"] = request.reason
        
        logger.info(f"Evaluation {evaluation_id} {request.action}ed by user {current_user['user_id']}")
        
        return {
            "message": f"Evaluation {request.action}ed successfully",
            "evaluation_id": evaluation_id,
            "new_status": eval_data["status"],
            "timestamp": datetime.utcnow()
        }
        
    except HTTPException:
        raise
    except Exception as e:
        logger.error(f"Error controlling evaluation: {str(e)}")
        raise HTTPException(status_code=500, detail="Failed to control evaluation")


@router.get("/evaluations", response_model=PaginatedResponse)
async def list_evaluations(
    page: int = Query(1, ge=1, description="Page number"),
    page_size: int = Query(20, ge=1, le=100, description="Items per page"),
    status: Optional[MultiTurnEvaluationStatus] = Query(None, description="Filter by status"),
    model_id: Optional[str] = Query(None, description="Filter by model ID"),
    current_user: dict = Depends(get_current_user)
):
    """
    List multi-turn evaluations with pagination and filtering.
    
    Implements requirement 9.1: Evaluation listing and filtering.
    """
    try:
        # Filter evaluations
        filtered_evaluations = []
        for eval_id, eval_data in active_evaluations.items():
            # Apply filters
            if status and eval_data["status"] != status:
                continue
            if model_id and eval_data["model_id"] != model_id:
                continue
            
            # Check user access (users can only see their own evaluations unless admin)
            if "admin" not in current_user.get("roles", []) and eval_data["created_by"] != current_user["user_id"]:
                continue
            
            filtered_evaluations.append({
                "evaluation_id": eval_id,
                "model_id": eval_data["model_id"],
                "status": eval_data["status"],
                "progress": eval_data["progress"],
                "created_at": eval_data["created_at"],
                "completed_tasks": eval_data["completed_tasks"],
                "total_tasks": eval_data["total_tasks"],
                "safety_incidents": eval_data["safety_incidents"]
            })
        
        # Sort by creation time (newest first)
        filtered_evaluations.sort(key=lambda x: x["created_at"], reverse=True)
        
        # Paginate
        total = len(filtered_evaluations)
        start_idx = (page - 1) * page_size
        end_idx = start_idx + page_size
        items = filtered_evaluations[start_idx:end_idx]
        
        return PaginatedResponse(
            items=items,
            total=total,
            page=page,
            page_size=page_size,
            has_next=end_idx < total,
            has_previous=page > 1
        )
        
    except Exception as e:
        logger.error(f"Error listing evaluations: {str(e)}")
        raise HTTPException(status_code=500, detail="Failed to list evaluations")


@router.get("/orchestrator/status", response_model=OrchestratorStatus)
async def get_orchestrator_status(
    current_user: dict = Depends(get_current_user)
):
    """
    Get orchestrator status and metrics.
    
    Implements requirement 9.1: Orchestrator monitoring endpoints.
    """
    try:
        # Calculate status metrics
        active_count = sum(1 for eval_data in active_evaluations.values() 
                          if eval_data["status"] == MultiTurnEvaluationStatus.RUNNING)
        
        queued_count = sum(1 for eval_data in active_evaluations.values() 
                          if eval_data["status"] == MultiTurnEvaluationStatus.CREATED)
        
        today = datetime.utcnow().date()
        today_evaluations = sum(1 for eval_data in active_evaluations.values() 
                               if eval_data["created_at"].date() == today)
        
        # Calculate average execution time for completed evaluations
        completed_evaluations = [eval_data for eval_data in active_evaluations.values() 
                               if eval_data["status"] == MultiTurnEvaluationStatus.COMPLETED]
        
        avg_execution_time = 0.0
        if completed_evaluations:
            total_time = sum((eval_data.get("completed_at", datetime.utcnow()) - 
                            eval_data["created_at"]).total_seconds() 
                           for eval_data in completed_evaluations)
            avg_execution_time = total_time / len(completed_evaluations)
        
        # Calculate safety incidents today
        safety_incidents_today = sum(eval_data["safety_incidents"] 
                                   for eval_data in active_evaluations.values() 
                                   if eval_data["created_at"].date() == today)
        
        # Get resource usage (placeholder)
        import psutil
        resource_usage = {
            "cpu_percent": psutil.cpu_percent(),
            "memory_percent": psutil.virtual_memory().percent,
            "disk_percent": psutil.disk_usage('/').percent
        }
        
        return OrchestratorStatus(
            active_evaluations=active_count,
            queued_evaluations=queued_count,
            total_evaluations_today=today_evaluations,
            average_execution_time=avg_execution_time,
            resource_usage=resource_usage,
            safety_incidents_today=safety_incidents_today
        )
        
    except Exception as e:
        logger.error(f"Error getting orchestrator status: {str(e)}")
        raise HTTPException(status_code=500, detail="Failed to get orchestrator status")


@router.get("/metrics/snapshot", response_model=MetricsSnapshot)
async def get_metrics_snapshot(
    evaluation_id: Optional[str] = Query(None, description="Specific evaluation ID"),
    current_user: dict = Depends(get_current_user)
):
    """
    Get current metrics snapshot.
    
    Implements requirement 9.1: Metrics monitoring endpoints.
    """
    try:
        metrics_engine = get_metrics_engine()
        
        if evaluation_id:
            # Get metrics for specific evaluation
            if evaluation_id not in active_evaluations:
                raise HTTPException(status_code=404, detail="Evaluation not found")
            
            # This would get actual metrics from the metrics engine
            # For now, return placeholder data
            snapshot_data = {
                "task_success_metrics": {"resolved_percentage": 0.75, "recall": 0.68, "mrr": 0.82},
                "efficiency_metrics": {"avg_turns": 5.2, "avg_steps": 12.8, "redundancy_rate": 0.15},
                "repair_quality_metrics": {"edit_churn": 2.3, "files_touched": 3.1},
                "robustness_metrics": {"recovery_rate": 0.85, "stability_score": 0.92},
                "cost_metrics": {"wall_time_per_solved": 45.6, "tokens_per_solved": 1250.0, "cost_per_solved": 0.025},
                "safety_metrics": {"safety_incidents": 0, "policy_violations": 0}
            }
        else:
            # Get aggregated metrics across all evaluations
            snapshot_data = {
                "task_success_metrics": {"resolved_percentage": 0.72, "recall": 0.65, "mrr": 0.79},
                "efficiency_metrics": {"avg_turns": 5.8, "avg_steps": 14.2, "redundancy_rate": 0.18},
                "repair_quality_metrics": {"edit_churn": 2.7, "files_touched": 3.5},
                "robustness_metrics": {"recovery_rate": 0.81, "stability_score": 0.88},
                "cost_metrics": {"wall_time_per_solved": 52.3, "tokens_per_solved": 1380.0, "cost_per_solved": 0.028},
                "safety_metrics": {"safety_incidents": 2, "policy_violations": 1}
            }
        
        return MetricsSnapshot(**snapshot_data)
        
    except HTTPException:
        raise
    except Exception as e:
        logger.error(f"Error getting metrics snapshot: {str(e)}")
        raise HTTPException(status_code=500, detail="Failed to get metrics snapshot")


# Admin-only endpoints

@router.delete("/evaluations/{evaluation_id}", dependencies=[Depends(require_admin)])
async def delete_evaluation(
    evaluation_id: str = Path(..., description="Evaluation ID"),
    current_user: dict = Depends(require_admin)
):
    """
    Delete an evaluation (admin only).
    
    Implements requirement 9.1: Administrative control endpoints.
    """
    try:
        if evaluation_id not in active_evaluations:
            raise HTTPException(status_code=404, detail="Evaluation not found")
        
        eval_data = active_evaluations[evaluation_id]
        
        # Can only delete completed, failed, or cancelled evaluations
        if eval_data["status"] in [MultiTurnEvaluationStatus.RUNNING, MultiTurnEvaluationStatus.CREATED]:
            raise HTTPException(status_code=400, detail="Cannot delete active evaluation")
        
        # Delete evaluation
        del active_evaluations[evaluation_id]
        
        logger.info(f"Evaluation {evaluation_id} deleted by admin {current_user['user_id']}")
        
        return {
            "message": "Evaluation deleted successfully",
            "evaluation_id": evaluation_id,
            "deleted_at": datetime.utcnow()
        }
        
    except HTTPException:
        raise
    except Exception as e:
        logger.error(f"Error deleting evaluation: {str(e)}")
        raise HTTPException(status_code=500, detail="Failed to delete evaluation")


@router.post("/system/cleanup", dependencies=[Depends(require_admin)])
async def cleanup_system(
    older_than_days: int = Query(7, ge=1, description="Delete evaluations older than N days"),
    current_user: dict = Depends(require_admin)
):
    """
    Cleanup old evaluations (admin only).
    
    Implements requirement 9.1: System maintenance endpoints.
    """
    try:
        cutoff_date = datetime.utcnow() - timedelta(days=older_than_days)
        
        # Find evaluations to delete
        to_delete = []
        for eval_id, eval_data in active_evaluations.items():
            if (eval_data["created_at"] < cutoff_date and 
                eval_data["status"] in [MultiTurnEvaluationStatus.COMPLETED, 
                                       MultiTurnEvaluationStatus.FAILED, 
                                       MultiTurnEvaluationStatus.CANCELLED]):
                to_delete.append(eval_id)
        
        # Delete evaluations
        for eval_id in to_delete:
            del active_evaluations[eval_id]
        
        logger.info(f"Cleaned up {len(to_delete)} evaluations older than {older_than_days} days")
        
        return {
            "message": f"Cleaned up {len(to_delete)} evaluations",
            "deleted_count": len(to_delete),
            "cutoff_date": cutoff_date,
            "cleaned_at": datetime.utcnow()
        }
        
    except Exception as e:
        logger.error(f"Error during system cleanup: {str(e)}")
        raise HTTPException(status_code=500, detail="Failed to cleanup system")


# Background task for executing evaluations
async def _execute_multi_turn_evaluation(
    evaluation_id: str,
    model_id: str,
    task_ids: List[str],
    config: MultiTurnConfig
):
    """Execute multi-turn evaluation in background."""
    try:
        eval_data = active_evaluations[evaluation_id]
        eval_data["status"] = MultiTurnEvaluationStatus.INITIALIZING
        eval_data["start_time"] = datetime.utcnow()
        
        orchestrator = get_orchestrator()
        task_registry = get_task_registry()
        
        # Initialize results storage
        task_results = []
        total_tokens = 0
        total_cost = 0.0
        safety_incidents = 0
        
        eval_data["status"] = MultiTurnEvaluationStatus.RUNNING
        
        # Execute each task
        for i, task_id in enumerate(task_ids):
            eval_data["current_task"] = task_id
            eval_data["current_turn"] = 1
            
            try:
                # Create task instance
                task = task_registry.create_task_instance(task_id, {})
                
                # Execute multi-turn task (placeholder implementation)
                # In real implementation, this would use the orchestrator
                task_result = {
                    "task_id": task_id,
                    "status": "completed",
                    "success": True,
                    "total_turns": 5,
                    "turn_results": [],
                    "termination_reason": TerminationReason.SUCCESS,
                    "final_metrics": {"success_rate": 1.0, "efficiency": 0.8},
                    "execution_time": 120.0,
                    "total_tokens": 500,
                    "total_cost": 0.01
                }
                
                task_results.append(task_result)
                total_tokens += task_result["total_tokens"]
                total_cost += task_result["total_cost"]
                
                eval_data["completed_tasks"] = i + 1
                eval_data["progress"] = (i + 1) / len(task_ids)
                eval_data["total_turns_executed"] += task_result["total_turns"]
                
                # Simulate some processing time
                await asyncio.sleep(1)
                
            except Exception as task_error:
                logger.error(f"Error executing task {task_id}: {str(task_error)}")
                task_result = {
                    "task_id": task_id,
                    "status": "failed",
                    "success": False,
                    "total_turns": 0,
                    "turn_results": [],
                    "termination_reason": TerminationReason.ERROR,
                    "final_metrics": {},
                    "execution_time": 0.0,
                    "total_tokens": 0,
                    "total_cost": 0.0
                }
                task_results.append(task_result)
        
        # Calculate final results
        successful_tasks = sum(1 for result in task_results if result["success"])
        overall_success_rate = successful_tasks / len(task_results) if task_results else 0.0
        average_turns = sum(result["total_turns"] for result in task_results) / len(task_results) if task_results else 0.0
        total_execution_time = (datetime.utcnow() - eval_data["start_time"]).total_seconds()
        
        # Store results
        eval_data["results"] = {
            "task_results": task_results,
            "aggregated_metrics": {
                "overall_success_rate": overall_success_rate,
                "total_tasks": len(task_results),
                "successful_tasks": successful_tasks,
                "failed_tasks": len(task_results) - successful_tasks
            },
            "overall_success_rate": overall_success_rate,
            "average_turns_per_task": average_turns,
            "total_execution_time": total_execution_time,
            "total_tokens": total_tokens,
            "total_cost": total_cost,
            "safety_summary": {"total_incidents": safety_incidents}
        }
        
        eval_data["status"] = MultiTurnEvaluationStatus.COMPLETED
        eval_data["completed_at"] = datetime.utcnow()
        eval_data["progress"] = 1.0
        
        logger.info(f"Multi-turn evaluation {evaluation_id} completed successfully")
        
    except Exception as e:
        logger.error(f"Error executing multi-turn evaluation {evaluation_id}: {str(e)}")
        eval_data["status"] = MultiTurnEvaluationStatus.FAILED
        eval_data["error_message"] = str(e)
        eval_data["failed_at"] = datetime.utcnow()