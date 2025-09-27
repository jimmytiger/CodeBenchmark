"""
API Server for AI Evaluation Engine

Main server application that integrates all API components including
REST endpoints, WebSocket communication, authentication, and notifications.
"""

import asyncio
import logging
import signal
import sys
from contextlib import asynccontextmanager
from typing import Optional

import uvicorn
from fastapi import FastAPI, Request, HTTPException
from fastapi.middleware.cors import CORSMiddleware
from fastapi.middleware.trustedhost import TrustedHostMiddleware
from fastapi.responses import JSONResponse
from fastapi.exception_handlers import http_exception_handler
import time

from .gateway import APIGateway
from .endpoints import router
from .auth import AuthManager
from .websocket import WebSocketManager
from .notifications import NotificationManager
from ..core.unified_framework import UnifiedEvaluationFramework
from ..core.task_registration import TaskRegistry
from ..core.advanced_model_config import AdvancedModelConfigurationManager
from ..core.analysis_engine import AnalysisEngine

logger = logging.getLogger(__name__)


class APIServer:
    """
    Main API server for the AI Evaluation Engine.
    
    Integrates all API components and provides a complete REST API
    and WebSocket interface for the evaluation engine.
    """
    
    def __init__(self, 
                 host: str = "0.0.0.0",
                 port: int = 8000,
                 debug: bool = False,
                 cors_origins: Optional[list] = None,
                 trusted_hosts: Optional[list] = None):
        
        self.host = host
        self.port = port
        self.debug = debug
        self.cors_origins = cors_origins or ["*"]
        self.trusted_hosts = trusted_hosts or ["*"]
        
        # Initialize core components
        self.evaluation_framework = UnifiedEvaluationFramework()
        self.task_registry = TaskRegistry()
        self.model_config_manager = AdvancedModelConfigurationManager()
        self.analysis_engine = AnalysisEngine()
        
        # Initialize API components
        self.auth_manager = AuthManager()
        self.websocket_manager = WebSocketManager(self.auth_manager)
        self.notification_manager = NotificationManager(self.websocket_manager)
        
        # Initialize API Gateway
        self.api_gateway = APIGateway(
            evaluation_framework=self.evaluation_framework,
            task_registry=self.task_registry,
            model_config_manager=self.model_config_manager,
            analysis_engine=self.analysis_engine
        )
        
        # Create FastAPI app
        self.app = self._create_app()
        
        # Setup signal handlers
        self._setup_signal_handlers()
    
    def _create_app(self) -> FastAPI:
        """Create and configure FastAPI application."""
        
        @asynccontextmanager
        async def lifespan(app: FastAPI):
            # Startup
            logger.info("Starting AI Evaluation Engine API Server...")
            await self._startup()
            yield
            # Shutdown
            logger.info("Shutting down AI Evaluation Engine API Server...")
            await self._shutdown()
        
        app = FastAPI(
            title="AI Evaluation Engine API",
            description="""
            Comprehensive API for AI model evaluation and analysis.
            
            This API provides endpoints for:
            - Creating and managing evaluations
            - Real-time progress monitoring via WebSocket
            - Task and model management
            - Results analysis and visualization
            - User authentication and authorization
            
            ## Authentication
            
            Most endpoints require authentication using JWT tokens.
            Use the `/auth/login` endpoint to obtain a token.
            
            ## WebSocket
            
            Connect to `/ws?token=YOUR_TOKEN` for real-time updates.
            
            ## Rate Limiting
            
            API requests are rate-limited to ensure fair usage.
            """,
            version="1.0.0",
            docs_url="/docs",
            redoc_url="/redoc",
            openapi_url="/openapi.json",
            lifespan=lifespan
        )
        
        # Add middleware
        self._setup_middleware(app)
        
        # Add exception handlers
        self._setup_exception_handlers(app)
        
        # Include routers
        app.include_router(router, prefix="/api/v1")
        
        # Add custom routes
        self._add_custom_routes(app)
        
        return app
    
    def _setup_middleware(self, app: FastAPI):
        """Setup middleware for the FastAPI app."""
        
        # CORS middleware
        app.add_middleware(
            CORSMiddleware,
            allow_origins=self.cors_origins,
            allow_credentials=True,
            allow_methods=["*"],
            allow_headers=["*"],
        )
        
        # Trusted host middleware
        if self.trusted_hosts != ["*"]:
            app.add_middleware(
                TrustedHostMiddleware,
                allowed_hosts=self.trusted_hosts
            )
        
        # Request timing middleware
        @app.middleware("http")
        async def add_process_time_header(request: Request, call_next):
            start_time = time.time()
            response = await call_next(request)
            process_time = time.time() - start_time
            response.headers["X-Process-Time"] = str(process_time)
            return response
        
        # Request logging middleware
        @app.middleware("http")
        async def log_requests(request: Request, call_next):
            start_time = time.time()
            
            # Log request
            logger.info(f"Request: {request.method} {request.url}")
            
            response = await call_next(request)
            
            # Log response
            process_time = time.time() - start_time
            logger.info(f"Response: {response.status_code} ({process_time:.3f}s)")
            
            return response
    
    def _setup_exception_handlers(self, app: FastAPI):
        """Setup custom exception handlers."""
        
        @app.exception_handler(HTTPException)
        async def custom_http_exception_handler(request: Request, exc: HTTPException):
            """Custom HTTP exception handler with logging."""
            logger.warning(f"HTTP {exc.status_code}: {exc.detail} - {request.method} {request.url}")
            return await http_exception_handler(request, exc)
        
        @app.exception_handler(Exception)
        async def general_exception_handler(request: Request, exc: Exception):
            """General exception handler for unhandled exceptions."""
            logger.error(f"Unhandled exception: {str(exc)} - {request.method} {request.url}", exc_info=True)
            return JSONResponse(
                status_code=500,
                content={
                    "error": "Internal Server Error",
                    "message": "An unexpected error occurred",
                    "request_id": getattr(request.state, "request_id", None)
                }
            )
    
    def _add_custom_routes(self, app: FastAPI):
        """Add custom routes to the app."""
        
        @app.get("/")
        async def root():
            """Root endpoint with API information."""
            return {
                "name": "AI Evaluation Engine API",
                "version": "1.0.0",
                "status": "running",
                "docs": "/docs",
                "redoc": "/redoc",
                "openapi": "/openapi.json",
                "websocket": "/ws"
            }
        
        @app.get("/health")
        async def health_check():
            """Health check endpoint."""
            return {
                "status": "healthy",
                "timestamp": time.time(),
                "components": {
                    "api_gateway": "healthy",
                    "websocket_manager": "healthy",
                    "notification_manager": "healthy",
                    "auth_manager": "healthy"
                }
            }
        
        @app.get("/metrics")
        async def get_metrics():
            """Get basic API metrics."""
            return {
                "active_connections": self.websocket_manager.connection_manager.get_connection_count(),
                "total_users": len(self.auth_manager.users),
                "active_evaluations": len(self.api_gateway.active_evaluations),
                "notification_queue_size": self.notification_manager.notification_queue.qsize()
            }
    
    async def _startup(self):
        """Startup tasks."""
        try:
            # Start notification manager
            await self.notification_manager.start()
            
            # Configure notification channels
            self._configure_notification_channels()
            
            # Initialize core components
            await self._initialize_core_components()
            
            logger.info(f"API Server started successfully on {self.host}:{self.port}")
            
        except Exception as e:
            logger.error(f"Failed to start API server: {str(e)}")
            raise
    
    async def _shutdown(self):
        """Shutdown tasks."""
        try:
            # Stop notification manager
            await self.notification_manager.stop()
            
            # Stop WebSocket monitoring
            await self.websocket_manager.stop_system_monitoring()
            
            # Cleanup active evaluations
            await self.api_gateway._cleanup_active_evaluations()
            
            logger.info("API Server shutdown completed")
            
        except Exception as e:
            logger.error(f"Error during shutdown: {str(e)}")
    
    def _configure_notification_channels(self):
        """Configure notification channels."""
        # Configure email channel (if SMTP settings are available)
        try:
            import os
            smtp_host = os.getenv("SMTP_HOST")
            smtp_port = int(os.getenv("SMTP_PORT", "587"))
            smtp_username = os.getenv("SMTP_USERNAME")
            smtp_password = os.getenv("SMTP_PASSWORD")
            from_email = os.getenv("FROM_EMAIL")
            
            if all([smtp_host, smtp_username, smtp_password, from_email]):
                self.notification_manager.configure_email_channel(
                    smtp_host, smtp_port, smtp_username, smtp_password, from_email
                )
                logger.info("Email notification channel configured")
            else:
                logger.info("Email notification channel not configured (missing SMTP settings)")
                
        except Exception as e:
            logger.warning(f"Failed to configure email channel: {str(e)}")
        
        # Configure webhook channel
        self.notification_manager.configure_webhook_channel()
    
    async def _initialize_core_components(self):
        """Initialize core evaluation components."""
        try:
            # Initialize task registry
            await self.task_registry.initialize()
            
            # Initialize model configuration manager
            await self.model_config_manager.initialize()
            
            # Initialize analysis engine
            await self.analysis_engine.initialize()
            
            logger.info("Core components initialized successfully")
            
        except Exception as e:
            logger.error(f"Failed to initialize core components: {str(e)}")
            raise
    
    def _setup_signal_handlers(self):
        """Setup signal handlers for graceful shutdown."""
        def signal_handler(signum, frame):
            logger.info(f"Received signal {signum}, initiating graceful shutdown...")
            sys.exit(0)
        
        signal.signal(signal.SIGINT, signal_handler)
        signal.signal(signal.SIGTERM, signal_handler)
    
    def run(self, **kwargs):
        """Run the API server."""
        # Merge kwargs with instance settings
        config = {
            "host": self.host,
            "port": self.port,
            "debug": self.debug,
            "log_level": "debug" if self.debug else "info",
            "access_log": True,
            "reload": self.debug,
            **kwargs
        }
        
        logger.info(f"Starting API server with config: {config}")
        uvicorn.run(self.app, **config)
    
    async def run_async(self, **kwargs):
        """Run the API server asynchronously."""
        config = uvicorn.Config(
            self.app,
            host=self.host,
            port=self.port,
            log_level="debug" if self.debug else "info",
            **kwargs
        )
        
        server = uvicorn.Server(config)
        await server.serve()


def create_app(config: Optional[dict] = None) -> FastAPI:
    """Factory function to create FastAPI app."""
    config = config or {}
    
    server = APIServer(
        host=config.get("host", "0.0.0.0"),
        port=config.get("port", 8000),
        debug=config.get("debug", False),
        cors_origins=config.get("cors_origins"),
        trusted_hosts=config.get("trusted_hosts")
    )
    
    return server.app


def main():
    """Main entry point for running the API server."""
    import argparse
    import os
    
    parser = argparse.ArgumentParser(description="AI Evaluation Engine API Server")
    parser.add_argument("--host", default="0.0.0.0", help="Host to bind to")
    parser.add_argument("--port", type=int, default=8000, help="Port to bind to")
    parser.add_argument("--debug", action="store_true", help="Enable debug mode")
    parser.add_argument("--reload", action="store_true", help="Enable auto-reload")
    parser.add_argument("--log-level", default="info", help="Log level")
    
    args = parser.parse_args()
    
    # Setup logging
    logging.basicConfig(
        level=getattr(logging, args.log_level.upper()),
        format="%(asctime)s - %(name)s - %(levelname)s - %(message)s"
    )
    
    # Create and run server
    server = APIServer(
        host=args.host,
        port=args.port,
        debug=args.debug
    )
    
    server.run(
        reload=args.reload,
        log_level=args.log_level
    )


if __name__ == "__main__":
    main()