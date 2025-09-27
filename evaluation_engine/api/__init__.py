"""
API Gateway and Integration Layer for AI Evaluation Engine

This module provides REST API endpoints and real-time communication
interfaces for the evaluation engine.
"""

# Import only core components that don't require external dependencies
from .auth import AuthManager

__all__ = [
    'AuthManager'
]

# Optional imports that require external dependencies
try:
    from .gateway import APIGateway
    from .endpoints import router
    from .websocket import WebSocketManager
    __all__.extend(['APIGateway', 'router', 'WebSocketManager'])
except ImportError:
    # FastAPI and other dependencies not available
    pass