"""
API Gateway for AI Evaluation Engine

Provides FastAPI-based REST endpoints for evaluation management,
task management, and results analysis.
"""

from fastapi import FastAPI, HTTPException, Depends, Query, Path
from fastapi.middleware.cors import CORSMiddleware
from fastapi.security import HTTPBearer, HTTPAuthorizationCredentials
from fastapi.responses import JSONResponse
from typing import List, Dict, Any, Optional
import uvicorn
import logging
from datetime import datetime
from pydantic import BaseModel, Field
import asyncio
from contextlib import asynccontextmanager

from ..core.unified_framework import UnifiedEvaluationFramework
from ..core.task_registration import TaskRegistry
from ..core.advanced_model_config import AdvancedModelConfigurationManager
from ..core.analysis_engine import AnalysisEngine
from .models import *
from .auth import AuthManager
from .websocket import WebSocketManager

logger = logging.getLogger(__name__)


class APIGateway:
    """
    Main API Gateway class that provides REST endpoints for the evaluation engine.
    
    Implements requirement 11.1: REST API endpoints for evaluation management,
    task management, and results analysis with validation.
    """
    
    def __init__(self, 
                 evaluation_framework: UnifiedEvaluationFramework,
                 task_registry: TaskRegistry,
                 model_config_manager: AdvancedModelConfigurationManager,
                 analysis_engine: AnalysisEngine):
        self.evaluation_framework = evaluation_framework
        self.task_registry = task_registry
        self.model_config_manager = model_config_manager
        self.analysis_engine = analysis_engine
        self.auth_manager = AuthManager()
        self.websocket_manager = WebSocketManager()
        
        # Initialize FastAPI app
        self.app = self._create_app()
        self._setup_routes()
        self._setup_middleware()
        
        # Track active evaluations
        self.active_evaluations: Dict[str, Dict[str, Any]] = {}
        
    def _create_app(self) -> FastAPI:
        """Create and configure FastAPI application."""
        
        @asynccontextmanager
        async def lifespan(app: FastAPI):
            # Startup
            logger.info("Starting API Gateway...")
            yield
            # Shutdown
            logger.info("Shutting down API Gateway...")
            await self._cleanup_active_evaluations()
        
        app = FastAPI(
            title="AI Evaluation Engine API",
            description="Comprehensive API for AI model evaluation and analysis",
            version="1.0.0",
            docs_url="/docs",
            redoc_url="/redoc",
            openapi_url="/openapi.json",
            lifespan=lifespan
        )
        
        return app
    
    def _setup_middleware(self):
        """Setup CORS and other middleware."""
        self.app.add_middleware(
            CORSMiddleware,
            allow_origins=["*"],  # Configure appropriately for production
            allow_credentials=True,
            allow_methods=["*"],
            allow_headers=["*"],
        )
    
    def _setup_routes(self):
        """Setup all API routes."""
        
        # Health check endpoint
        @self.app.get("/health", tags=["System"])
        async def health_check():
            """System health check endpoint."""
            return {
                "status": "healthy",
                "timestamp": datetime.utcnow().isoformat(),
                "version": "1.0.0",
                "active_evaluations": len(self.active_evaluations)
            }
        
        # Authentication Endpoints
        @self.app.post("/auth/login", response_model=AuthToken, tags=["Authentication"])
        async def login(credentials: LoginRequest):
            """
            User login endpoint.
            
            Returns JWT access token and refresh token for authenticated requests.
            """
            try:
                # Authenticate user
                auth_token = self.auth_manager.login(credentials.username, credentials.password)
                
                if not auth_token:
                    raise HTTPException(
                        status_code=401, 
                        detail="Invalid username or password"
                    )
                
                return auth_token
                
            except HTTPException:
                raise
            except Exception as e:
                logger.error(f"Login error: {str(e)}")
                raise HTTPException(status_code=500, detail="Internal server error")
        
        @self.app.post("/auth/refresh", tags=["Authentication"])
        async def refresh_token(refresh_request: RefreshTokenRequest):
            """
            Refresh access token using refresh token.
            """
            try:
                new_access_token = self.auth_manager.refresh_access_token(refresh_request.refresh_token)
                
                if not new_access_token:
                    raise HTTPException(status_code=401, detail="Invalid refresh token")
                
                return {
                    "access_token": new_access_token,
                    "token_type": "bearer",
                    "expires_in": int(self.auth_manager.token_expiry.total_seconds())
                }
                
            except HTTPException:
                raise
            except Exception as e:
                logger.error(f"Token refresh error: {str(e)}")
                raise HTTPException(status_code=500, detail="Internal server error")
        
        @self.app.post("/auth/logout", tags=["Authentication"])
        async def logout(
            logout_request: LogoutRequest,
            auth: HTTPAuthorizationCredentials = Depends(HTTPBearer())
        ):
            """
            Logout user and invalidate refresh token.
            """
            try:
                # Validate current token
                user = await self.auth_manager.validate_token(auth.credentials)
                if not user:
                    raise HTTPException(status_code=401, detail="Invalid token")
                
                # Logout
                success = self.auth_manager.logout(logout_request.refresh_token)
                
                return {"message": "Logged out successfully", "success": success}
                
            except HTTPException:
                raise
            except Exception as e:
                logger.error(f"Logout error: {str(e)}")
                raise HTTPException(status_code=500, detail="Internal server error")
        
        # Evaluation Management Endpoints
        @self.app.post("/evaluations", response_model=EvaluationResponse, tags=["Evaluations"])
        async def create_evaluation(
            request: EvaluationRequest,
            auth: HTTPAuthorizationCredentials = Depends(HTTPBearer())
        ):
            """
            Create a new evaluation.
            
            Implements requirement 11.1: Evaluation management endpoints.
            """
            try:
                # Validate authentication
                user = await self.auth_manager.validate_token(auth.credentials)
                if not user:
                    raise HTTPException(status_code=401, detail="Invalid authentication")
                
                # Validate request
                validation_result = await self._validate_evaluation_request(request)
                if not validation_result.is_valid:
                    raise HTTPException(status_code=400, detail=validation_result.errors)
                
                # Create evaluation
                evaluation_id = await self._create_evaluation(request, user)
                
                # Start evaluation asynchronously
                asyncio.create_task(self._run_evaluation(evaluation_id, request))
                
                return EvaluationResponse(
                    evaluation_id=evaluation_id,
                    status="created",
                    message="Evaluation created successfully",
                    created_at=datetime.utcnow()
                )
                
            except Exception as e:
                logger.error(f"Error creating evaluation: {str(e)}")
                raise HTTPException(status_code=500, detail=str(e))
        
        @self.app.get("/evaluations/{evaluation_id}", response_model=EvaluationStatus, tags=["Evaluations"])
        async def get_evaluation_status(
            evaluation_id: str = Path(..., description="Evaluation ID"),
            auth: HTTPAuthorizationCredentials = Depends(HTTPBearer())
        ):
            """
            Get evaluation status and progress.
            
            Implements requirement 11.1: Evaluation monitoring endpoints.
            """
            try:
                # Validate authentication
                user = await self.auth_manager.validate_token(auth.credentials)
                if not user:
                    raise HTTPException(status_code=401, detail="Invalid authentication")
                
                # Check if evaluation exists
                if evaluation_id not in self.active_evaluations:
                    raise HTTPException(status_code=404, detail="Evaluation not found")
                
                evaluation = self.active_evaluations[evaluation_id]
                
                return EvaluationStatus(
                    evaluation_id=evaluation_id,
                    status=evaluation["status"],
                    progress=evaluation.get("progress", 0.0),
                    current_task=evaluation.get("current_task"),
                    completed_tasks=evaluation.get("completed_tasks", 0),
                    total_tasks=evaluation.get("total_tasks", 0),
                    start_time=evaluation.get("start_time"),
                    estimated_completion=evaluation.get("estimated_completion"),
                    error_message=evaluation.get("error_message")
                )
                
            except HTTPException:
                raise
            except Exception as e:
                logger.error(f"Error getting evaluation status: {str(e)}")
                raise HTTPException(status_code=500, detail=str(e))
        
        @self.app.delete("/evaluations/{evaluation_id}", tags=["Evaluations"])
        async def cancel_evaluation(
            evaluation_id: str = Path(..., description="Evaluation ID"),
            auth: HTTPAuthorizationCredentials = Depends(HTTPBearer())
        ):
            """
            Cancel a running evaluation.
            
            Implements requirement 11.1: Evaluation cancellation endpoints.
            """
            try:
                # Validate authentication
                user = await self.auth_manager.validate_token(auth.credentials)
                if not user:
                    raise HTTPException(status_code=401, detail="Invalid authentication")
                
                # Check if evaluation exists
                if evaluation_id not in self.active_evaluations:
                    raise HTTPException(status_code=404, detail="Evaluation not found")
                
                # Cancel evaluation
                await self._cancel_evaluation(evaluation_id)
                
                return {"message": "Evaluation cancelled successfully"}
                
            except HTTPException:
                raise
            except Exception as e:
                logger.error(f"Error cancelling evaluation: {str(e)}")
                raise HTTPException(status_code=500, detail=str(e))
        
        # Task Management Endpoints
        @self.app.get("/tasks", response_model=List[TaskInfo], tags=["Tasks"])
        async def list_tasks(
            category: Optional[str] = Query(None, description="Filter by task category"),
            difficulty: Optional[str] = Query(None, description="Filter by difficulty level"),
            language: Optional[str] = Query(None, description="Filter by programming language"),
            limit: int = Query(50, ge=1, le=1000, description="Maximum number of tasks to return"),
            offset: int = Query(0, ge=0, description="Number of tasks to skip"),
            auth: HTTPAuthorizationCredentials = Depends(HTTPBearer())
        ):
            """
            List available evaluation tasks with filtering and pagination.
            
            Implements requirement 11.1: Task management APIs with validation.
            """
            try:
                # Validate authentication
                user = await self.auth_manager.validate_token(auth.credentials)
                if not user:
                    raise HTTPException(status_code=401, detail="Invalid authentication")
                
                # Get tasks with filters
                tasks = await self._get_tasks(
                    category=category,
                    difficulty=difficulty,
                    language=language,
                    limit=limit,
                    offset=offset
                )
                
                return tasks
                
            except HTTPException:
                raise
            except Exception as e:
                logger.error(f"Error listing tasks: {str(e)}")
                raise HTTPException(status_code=500, detail=str(e))
        
        @self.app.get("/tasks/{task_id}", response_model=TaskDetail, tags=["Tasks"])
        async def get_task_detail(
            task_id: str = Path(..., description="Task ID"),
            auth: HTTPAuthorizationCredentials = Depends(HTTPBearer())
        ):
            """
            Get detailed information about a specific task.
            
            Implements requirement 11.1: Task management endpoints.
            """
            try:
                # Validate authentication
                user = await self.auth_manager.validate_token(auth.credentials)
                if not user:
                    raise HTTPException(status_code=401, detail="Invalid authentication")
                
                # Get task detail
                task_detail = await self._get_task_detail(task_id)
                if not task_detail:
                    raise HTTPException(status_code=404, detail="Task not found")
                
                return task_detail
                
            except HTTPException:
                raise
            except Exception as e:
                logger.error(f"Error getting task detail: {str(e)}")
                raise HTTPException(status_code=500, detail=str(e))
        
        # Model Configuration Endpoints
        @self.app.get("/models", response_model=List[ModelInfo], tags=["Models"])
        async def list_models(
            provider: Optional[str] = Query(None, description="Filter by model provider"),
            auth: HTTPAuthorizationCredentials = Depends(HTTPBearer())
        ):
            """
            List available model configurations.
            
            Implements requirement 11.1: Model configuration APIs.
            """
            try:
                # Validate authentication
                user = await self.auth_manager.validate_token(auth.credentials)
                if not user:
                    raise HTTPException(status_code=401, detail="Invalid authentication")
                
                # Get available models
                models = await self._get_available_models(provider)
                
                return models
                
            except HTTPException:
                raise
            except Exception as e:
                logger.error(f"Error listing models: {str(e)}")
                raise HTTPException(status_code=500, detail=str(e))
        
        @self.app.post("/models/{model_id}/validate", tags=["Models"])
        async def validate_model_config(
            model_id: str = Path(..., description="Model ID"),
            config: ModelConfigRequest = None,
            auth: HTTPAuthorizationCredentials = Depends(HTTPBearer())
        ):
            """
            Validate model configuration.
            
            Implements requirement 11.1: Model configuration validation.
            """
            try:
                # Validate authentication
                user = await self.auth_manager.validate_token(auth.credentials)
                if not user:
                    raise HTTPException(status_code=401, detail="Invalid authentication")
                
                # Validate model configuration
                validation_result = await self._validate_model_config(model_id, config)
                
                return {
                    "is_valid": validation_result.is_valid,
                    "errors": validation_result.errors,
                    "warnings": validation_result.warnings
                }
                
            except HTTPException:
                raise
            except Exception as e:
                logger.error(f"Error validating model config: {str(e)}")
                raise HTTPException(status_code=500, detail=str(e))
        
        # Results and Analytics Endpoints
        @self.app.get("/results/{evaluation_id}", response_model=EvaluationResults, tags=["Results"])
        async def get_evaluation_results(
            evaluation_id: str = Path(..., description="Evaluation ID"),
            include_details: bool = Query(False, description="Include detailed results"),
            auth: HTTPAuthorizationCredentials = Depends(HTTPBearer())
        ):
            """
            Get evaluation results with filtering and analysis.
            
            Implements requirement 11.1: Results and analytics endpoints.
            """
            try:
                # Validate authentication
                user = await self.auth_manager.validate_token(auth.credentials)
                if not user:
                    raise HTTPException(status_code=401, detail="Invalid authentication")
                
                # Get evaluation results
                results = await self._get_evaluation_results(evaluation_id, include_details)
                if not results:
                    raise HTTPException(status_code=404, detail="Results not found")
                
                return results
                
            except HTTPException:
                raise
            except Exception as e:
                logger.error(f"Error getting evaluation results: {str(e)}")
                raise HTTPException(status_code=500, detail=str(e))
        
        @self.app.get("/analytics/summary", response_model=AnalyticsSummary, tags=["Analytics"])
        async def get_analytics_summary(
            start_date: Optional[str] = Query(None, description="Start date (ISO format)"),
            end_date: Optional[str] = Query(None, description="End date (ISO format)"),
            model_ids: Optional[List[str]] = Query(None, description="Filter by model IDs"),
            task_categories: Optional[List[str]] = Query(None, description="Filter by task categories"),
            auth: HTTPAuthorizationCredentials = Depends(HTTPBearer())
        ):
            """
            Get analytics summary with filtering.
            
            Implements requirement 11.1: Analytics endpoints with filtering.
            """
            try:
                # Validate authentication
                user = await self.auth_manager.validate_token(auth.credentials)
                if not user:
                    raise HTTPException(status_code=401, detail="Invalid authentication")
                
                # Get analytics summary
                summary = await self._get_analytics_summary(
                    start_date=start_date,
                    end_date=end_date,
                    model_ids=model_ids,
                    task_categories=task_categories
                )
                
                return summary
                
            except HTTPException:
                raise
            except Exception as e:
                logger.error(f"Error getting analytics summary: {str(e)}")
                raise HTTPException(status_code=500, detail=str(e))
        
        @self.app.get("/analytics/compare", response_model=ComparisonReport, tags=["Analytics"])
        async def compare_models(
            model_ids: List[str] = Query(..., description="Model IDs to compare"),
            task_categories: Optional[List[str]] = Query(None, description="Filter by task categories"),
            metrics: Optional[List[str]] = Query(None, description="Specific metrics to compare"),
            auth: HTTPAuthorizationCredentials = Depends(HTTPBearer())
        ):
            """
            Compare model performance across tasks and metrics.
            
            Implements requirement 11.1: Comparative analysis endpoints.
            """
            try:
                # Validate authentication
                user = await self.auth_manager.validate_token(auth.credentials)
                if not user:
                    raise HTTPException(status_code=401, detail="Invalid authentication")
                
                # Validate input
                if len(model_ids) < 2:
                    raise HTTPException(status_code=400, detail="At least 2 models required for comparison")
                
                # Get comparison report
                comparison = await self._compare_models(
                    model_ids=model_ids,
                    task_categories=task_categories,
                    metrics=metrics
                )
                
                return comparison
                
            except HTTPException:
                raise
            except Exception as e:
                logger.error(f"Error comparing models: {str(e)}")
                raise HTTPException(status_code=500, detail=str(e))
    
    async def _validate_evaluation_request(self, request: EvaluationRequest) -> ValidationResult:
        """Validate evaluation request parameters."""
        errors = []
        
        # Validate model ID
        if not await self._is_valid_model(request.model_id):
            errors.append(f"Invalid model ID: {request.model_id}")
        
        # Validate task IDs
        for task_id in request.task_ids:
            if not await self._is_valid_task(task_id):
                errors.append(f"Invalid task ID: {task_id}")
        
        # Validate configuration
        if request.configuration:
            config_errors = await self._validate_configuration(request.configuration)
            errors.extend(config_errors)
        
        return ValidationResult(is_valid=len(errors) == 0, errors=errors)
    
    async def _create_evaluation(self, request: EvaluationRequest, user: Dict[str, Any]) -> str:
        """Create a new evaluation and return its ID."""
        import uuid
        
        evaluation_id = str(uuid.uuid4())
        
        # Store evaluation metadata
        self.active_evaluations[evaluation_id] = {
            "status": "created",
            "user_id": user["user_id"],
            "model_id": request.model_id,
            "task_ids": request.task_ids,
            "configuration": request.configuration,
            "created_at": datetime.utcnow(),
            "progress": 0.0,
            "total_tasks": len(request.task_ids),
            "completed_tasks": 0
        }
        
        return evaluation_id
    
    async def _run_evaluation(self, evaluation_id: str, request: EvaluationRequest):
        """Run evaluation asynchronously."""
        try:
            # Update status
            self.active_evaluations[evaluation_id]["status"] = "running"
            self.active_evaluations[evaluation_id]["start_time"] = datetime.utcnow()
            
            # Notify WebSocket clients
            await self.websocket_manager.broadcast_evaluation_update(evaluation_id, {
                "status": "running",
                "message": "Evaluation started"
            })
            
            # Run evaluation using the unified framework
            results = await self.evaluation_framework.run_evaluation_async(
                model_id=request.model_id,
                task_ids=request.task_ids,
                configuration=request.configuration,
                progress_callback=lambda progress: self._update_evaluation_progress(evaluation_id, progress)
            )
            
            # Store results
            self.active_evaluations[evaluation_id]["results"] = results
            self.active_evaluations[evaluation_id]["status"] = "completed"
            self.active_evaluations[evaluation_id]["completed_at"] = datetime.utcnow()
            
            # Notify completion
            await self.websocket_manager.broadcast_evaluation_update(evaluation_id, {
                "status": "completed",
                "message": "Evaluation completed successfully"
            })
            
        except Exception as e:
            logger.error(f"Error running evaluation {evaluation_id}: {str(e)}")
            
            # Update error status
            self.active_evaluations[evaluation_id]["status"] = "failed"
            self.active_evaluations[evaluation_id]["error_message"] = str(e)
            
            # Notify error
            await self.websocket_manager.broadcast_evaluation_update(evaluation_id, {
                "status": "failed",
                "message": f"Evaluation failed: {str(e)}"
            })
    
    async def _update_evaluation_progress(self, evaluation_id: str, progress: float):
        """Update evaluation progress."""
        if evaluation_id in self.active_evaluations:
            self.active_evaluations[evaluation_id]["progress"] = progress
            
            # Broadcast progress update
            await self.websocket_manager.broadcast_evaluation_update(evaluation_id, {
                "progress": progress
            })
    
    async def _cancel_evaluation(self, evaluation_id: str):
        """Cancel a running evaluation."""
        if evaluation_id in self.active_evaluations:
            self.active_evaluations[evaluation_id]["status"] = "cancelled"
            self.active_evaluations[evaluation_id]["cancelled_at"] = datetime.utcnow()
            
            # Notify cancellation
            await self.websocket_manager.broadcast_evaluation_update(evaluation_id, {
                "status": "cancelled",
                "message": "Evaluation cancelled by user"
            })
    
    async def _cleanup_active_evaluations(self):
        """Cleanup active evaluations on shutdown."""
        for evaluation_id in list(self.active_evaluations.keys()):
            if self.active_evaluations[evaluation_id]["status"] in ["running", "created"]:
                await self._cancel_evaluation(evaluation_id)
    
    # Helper methods for data retrieval
    async def _get_tasks(self, category: Optional[str], difficulty: Optional[str], 
                        language: Optional[str], limit: int, offset: int) -> List[TaskInfo]:
        """Get filtered list of tasks."""
        # Implementation would integrate with task registry
        # This is a placeholder implementation
        return []
    
    async def _get_task_detail(self, task_id: str) -> Optional[TaskDetail]:
        """Get detailed task information."""
        # Implementation would integrate with task registry
        return None
    
    async def _get_available_models(self, provider: Optional[str]) -> List[ModelInfo]:
        """Get available model configurations."""
        # Implementation would integrate with model configuration manager
        return []
    
    async def _validate_model_config(self, model_id: str, config: Optional[ModelConfigRequest]) -> ValidationResult:
        """Validate model configuration."""
        return ValidationResult(is_valid=True, errors=[])
    
    async def _get_evaluation_results(self, evaluation_id: str, include_details: bool) -> Optional[EvaluationResults]:
        """Get evaluation results."""
        if evaluation_id not in self.active_evaluations:
            return None
        
        evaluation = self.active_evaluations[evaluation_id]
        if evaluation["status"] != "completed":
            return None
        
        # Return results (placeholder implementation)
        return EvaluationResults(
            evaluation_id=evaluation_id,
            model_id=evaluation["model_id"],
            task_results=[],
            summary_metrics={},
            completed_at=evaluation.get("completed_at")
        )
    
    async def _get_analytics_summary(self, start_date: Optional[str], end_date: Optional[str],
                                   model_ids: Optional[List[str]], task_categories: Optional[List[str]]) -> AnalyticsSummary:
        """Get analytics summary."""
        # Implementation would integrate with analysis engine
        return AnalyticsSummary(
            total_evaluations=0,
            total_tasks_executed=0,
            average_performance=0.0,
            top_performing_models=[],
            performance_trends={}
        )
    
    async def _compare_models(self, model_ids: List[str], task_categories: Optional[List[str]],
                            metrics: Optional[List[str]]) -> ComparisonReport:
        """Compare model performance."""
        # Implementation would integrate with analysis engine
        return ComparisonReport(
            model_ids=model_ids,
            comparison_metrics={},
            statistical_significance={},
            recommendations=[]
        )
    
    # Validation helper methods
    async def _is_valid_model(self, model_id: str) -> bool:
        """Check if model ID is valid."""
        return True  # Placeholder
    
    async def _is_valid_task(self, task_id: str) -> bool:
        """Check if task ID is valid."""
        return True  # Placeholder
    
    async def _validate_configuration(self, configuration: Dict[str, Any]) -> List[str]:
        """Validate configuration parameters."""
        return []  # Placeholder
    
    def run(self, host: str = "0.0.0.0", port: int = 8000, **kwargs):
        """Run the API server."""
        uvicorn.run(self.app, host=host, port=port, **kwargs)


class ValidationResult:
    """Result of validation operations."""
    
    def __init__(self, is_valid: bool, errors: List[str], warnings: Optional[List[str]] = None):
        self.is_valid = is_valid
        self.errors = errors
        self.warnings = warnings or []