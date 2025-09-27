"""
Authentication and Authorization Manager

Implements JWT-based authentication and role-based access control
for the API Gateway.
"""

import jwt
import bcrypt
from datetime import datetime, timedelta
from typing import Dict, Any, Optional, List
import logging
from fastapi import HTTPException, status
from fastapi.security import HTTPBearer, HTTPAuthorizationCredentials
import secrets
import hashlib

from .models import UserInfo, AuthToken

logger = logging.getLogger(__name__)


class AuthManager:
    """
    Authentication and authorization manager.
    
    Implements requirement 11.4: Authentication and authorization 
    with JWT and role-based access control.
    """
    
    def __init__(self, secret_key: Optional[str] = None, algorithm: str = "HS256"):
        self.secret_key = secret_key or self._generate_secret_key()
        self.algorithm = algorithm
        self.token_expiry = timedelta(hours=24)
        self.refresh_token_expiry = timedelta(days=7)
        
        # In-memory user store (replace with database in production)
        self.users: Dict[str, Dict[str, Any]] = {}
        self.refresh_tokens: Dict[str, str] = {}  # refresh_token -> user_id
        
        # Role-based permissions
        self.role_permissions = {
            "admin": [
                "evaluation:create", "evaluation:read", "evaluation:cancel",
                "task:read", "model:read", "model:configure",
                "analytics:read", "user:manage", "system:monitor"
            ],
            "evaluator": [
                "evaluation:create", "evaluation:read", "evaluation:cancel",
                "task:read", "model:read", "analytics:read"
            ],
            "viewer": [
                "evaluation:read", "task:read", "model:read", "analytics:read"
            ],
            "api_user": [
                "evaluation:create", "evaluation:read", "task:read", "model:read"
            ]
        }
        
        # Create default admin user
        self._create_default_users()
    
    def _generate_secret_key(self) -> str:
        """Generate a secure secret key."""
        return secrets.token_urlsafe(32)
    
    def _create_default_users(self):
        """Create default users for testing."""
        # Admin user
        self.create_user(
            username="admin",
            email="admin@example.com",
            password="admin123",
            roles=["admin"]
        )
        
        # Evaluator user
        self.create_user(
            username="evaluator",
            email="evaluator@example.com",
            password="eval123",
            roles=["evaluator"]
        )
    
    def create_user(self, username: str, email: str, password: str, 
                   roles: List[str]) -> str:
        """Create a new user."""
        user_id = hashlib.sha256(f"{username}{email}".encode()).hexdigest()[:16]
        
        # Hash password
        password_hash = bcrypt.hashpw(password.encode('utf-8'), bcrypt.gensalt())
        
        # Calculate permissions from roles
        permissions = set()
        for role in roles:
            if role in self.role_permissions:
                permissions.update(self.role_permissions[role])
        
        self.users[user_id] = {
            "user_id": user_id,
            "username": username,
            "email": email,
            "password_hash": password_hash,
            "roles": roles,
            "permissions": list(permissions),
            "created_at": datetime.utcnow(),
            "last_login": None,
            "is_active": True
        }
        
        logger.info(f"Created user: {username} with roles: {roles}")
        return user_id
    
    def authenticate_user(self, username: str, password: str) -> Optional[Dict[str, Any]]:
        """Authenticate user with username and password."""
        # Find user by username
        user = None
        for user_data in self.users.values():
            if user_data["username"] == username and user_data["is_active"]:
                user = user_data
                break
        
        if not user:
            return None
        
        # Verify password
        if not bcrypt.checkpw(password.encode('utf-8'), user["password_hash"]):
            return None
        
        # Update last login
        user["last_login"] = datetime.utcnow()
        
        return user
    
    def create_access_token(self, user: Dict[str, Any]) -> str:
        """Create JWT access token."""
        payload = {
            "user_id": user["user_id"],
            "username": user["username"],
            "roles": user["roles"],
            "permissions": user["permissions"],
            "exp": datetime.utcnow() + self.token_expiry,
            "iat": datetime.utcnow(),
            "type": "access"
        }
        
        return jwt.encode(payload, self.secret_key, algorithm=self.algorithm)
    
    def create_refresh_token(self, user: Dict[str, Any]) -> str:
        """Create refresh token."""
        refresh_token = secrets.token_urlsafe(32)
        
        # Store refresh token
        self.refresh_tokens[refresh_token] = user["user_id"]
        
        return refresh_token
    
    def login(self, username: str, password: str) -> Optional[AuthToken]:
        """Login user and return authentication token."""
        user = self.authenticate_user(username, password)
        if not user:
            return None
        
        # Create tokens
        access_token = self.create_access_token(user)
        refresh_token = self.create_refresh_token(user)
        
        # Create user info
        user_info = UserInfo(
            user_id=user["user_id"],
            username=user["username"],
            email=user["email"],
            roles=user["roles"],
            permissions=user["permissions"],
            created_at=user["created_at"],
            last_login=user["last_login"]
        )
        
        return AuthToken(
            access_token=access_token,
            token_type="bearer",
            expires_in=int(self.token_expiry.total_seconds()),
            refresh_token=refresh_token,
            user_info=user_info
        )
    
    async def validate_token(self, token: str) -> Optional[Dict[str, Any]]:
        """Validate JWT token and return user information."""
        try:
            # Decode token
            payload = jwt.decode(token, self.secret_key, algorithms=[self.algorithm])
            
            # Check token type
            if payload.get("type") != "access":
                return None
            
            # Check expiration
            if datetime.utcnow() > datetime.fromtimestamp(payload["exp"]):
                return None
            
            # Get user
            user_id = payload["user_id"]
            if user_id not in self.users:
                return None
            
            user = self.users[user_id]
            if not user["is_active"]:
                return None
            
            return {
                "user_id": user_id,
                "username": user["username"],
                "roles": user["roles"],
                "permissions": user["permissions"]
            }
            
        except jwt.InvalidTokenError:
            return None
        except Exception as e:
            logger.error(f"Error validating token: {str(e)}")
            return None
    
    def refresh_access_token(self, refresh_token: str) -> Optional[str]:
        """Refresh access token using refresh token."""
        if refresh_token not in self.refresh_tokens:
            return None
        
        user_id = self.refresh_tokens[refresh_token]
        if user_id not in self.users:
            return None
        
        user = self.users[user_id]
        if not user["is_active"]:
            return None
        
        # Create new access token
        return self.create_access_token(user)
    
    def logout(self, refresh_token: str) -> bool:
        """Logout user by invalidating refresh token."""
        if refresh_token in self.refresh_tokens:
            del self.refresh_tokens[refresh_token]
            return True
        return False
    
    def check_permission(self, user: Dict[str, Any], permission: str) -> bool:
        """Check if user has specific permission."""
        return permission in user.get("permissions", [])
    
    def require_permission(self, permission: str):
        """Decorator to require specific permission."""
        def decorator(func):
            async def wrapper(*args, **kwargs):
                # Extract user from kwargs (assumes user is passed as parameter)
                user = kwargs.get("current_user")
                if not user or not self.check_permission(user, permission):
                    raise HTTPException(
                        status_code=status.HTTP_403_FORBIDDEN,
                        detail=f"Permission required: {permission}"
                    )
                return await func(*args, **kwargs)
            return wrapper
        return decorator
    
    def get_user_info(self, user_id: str) -> Optional[UserInfo]:
        """Get user information by ID."""
        if user_id not in self.users:
            return None
        
        user = self.users[user_id]
        return UserInfo(
            user_id=user["user_id"],
            username=user["username"],
            email=user["email"],
            roles=user["roles"],
            permissions=user["permissions"],
            created_at=user["created_at"],
            last_login=user["last_login"]
        )
    
    def update_user_roles(self, user_id: str, roles: List[str]) -> bool:
        """Update user roles and recalculate permissions."""
        if user_id not in self.users:
            return False
        
        # Calculate new permissions
        permissions = set()
        for role in roles:
            if role in self.role_permissions:
                permissions.update(self.role_permissions[role])
        
        # Update user
        self.users[user_id]["roles"] = roles
        self.users[user_id]["permissions"] = list(permissions)
        
        logger.info(f"Updated roles for user {user_id}: {roles}")
        return True
    
    def deactivate_user(self, user_id: str) -> bool:
        """Deactivate user account."""
        if user_id not in self.users:
            return False
        
        self.users[user_id]["is_active"] = False
        
        # Invalidate all refresh tokens for this user
        tokens_to_remove = [
            token for token, uid in self.refresh_tokens.items() 
            if uid == user_id
        ]
        for token in tokens_to_remove:
            del self.refresh_tokens[token]
        
        logger.info(f"Deactivated user: {user_id}")
        return True
    
    def get_all_users(self) -> List[UserInfo]:
        """Get all users (admin only)."""
        return [
            UserInfo(
                user_id=user["user_id"],
                username=user["username"],
                email=user["email"],
                roles=user["roles"],
                permissions=user["permissions"],
                created_at=user["created_at"],
                last_login=user["last_login"]
            )
            for user in self.users.values()
            if user["is_active"]
        ]


class PermissionChecker:
    """Helper class for checking permissions in route handlers."""
    
    def __init__(self, auth_manager: AuthManager):
        self.auth_manager = auth_manager
    
    def require_permission(self, permission: str):
        """Dependency to require specific permission."""
        async def check_permission(
            credentials: HTTPAuthorizationCredentials = Depends(HTTPBearer())
        ):
            user = await self.auth_manager.validate_token(credentials.credentials)
            if not user:
                raise HTTPException(
                    status_code=status.HTTP_401_UNAUTHORIZED,
                    detail="Invalid authentication credentials"
                )
            
            if not self.auth_manager.check_permission(user, permission):
                raise HTTPException(
                    status_code=status.HTTP_403_FORBIDDEN,
                    detail=f"Permission required: {permission}"
                )
            
            return user
        
        return check_permission
    
    def require_role(self, role: str):
        """Dependency to require specific role."""
        async def check_role(
            credentials: HTTPAuthorizationCredentials = Depends(HTTPBearer())
        ):
            user = await self.auth_manager.validate_token(credentials.credentials)
            if not user:
                raise HTTPException(
                    status_code=status.HTTP_401_UNAUTHORIZED,
                    detail="Invalid authentication credentials"
                )
            
            if role not in user.get("roles", []):
                raise HTTPException(
                    status_code=status.HTTP_403_FORBIDDEN,
                    detail=f"Role required: {role}"
                )
            
            return user
        
        return check_role