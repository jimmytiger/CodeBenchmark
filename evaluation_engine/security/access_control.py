"""
Role-Based Access Control and Data Privacy Enforcement

Provides comprehensive access control mechanisms with role-based permissions.
"""

import asyncio
import json
import logging
from datetime import datetime, timedelta
from typing import Dict, List, Optional, Any, Set, Union
from dataclasses import dataclass, asdict
from pathlib import Path
from enum import Enum
import hashlib
import secrets
from functools import wraps
import jwt

logger = logging.getLogger(__name__)

class Permission(Enum):
    """System permissions"""
    # Evaluation permissions
    CREATE_EVALUATION = "create_evaluation"
    VIEW_EVALUATION = "view_evaluation"
    MODIFY_EVALUATION = "modify_evaluation"
    DELETE_EVALUATION = "delete_evaluation"
    
    # Task permissions
    CREATE_TASK = "create_task"
    VIEW_TASK = "view_task"
    MODIFY_TASK = "modify_task"
    DELETE_TASK = "delete_task"
    EXECUTE_TASK = "execute_task"
    
    # Model permissions
    VIEW_MODEL_CONFIG = "view_model_config"
    MODIFY_MODEL_CONFIG = "modify_model_config"
    USE_MODEL = "use_model"
    
    # Data permissions
    VIEW_DATA = "view_data"
    MODIFY_DATA = "modify_data"
    DELETE_DATA = "delete_data"
    EXPORT_DATA = "export_data"
    
    # Security permissions
    VIEW_SECURITY_LOGS = "view_security_logs"
    MODIFY_SECURITY_CONFIG = "modify_security_config"
    VIEW_AUDIT_LOGS = "view_audit_logs"
    
    # Admin permissions
    MANAGE_USERS = "manage_users"
    MANAGE_ROLES = "manage_roles"
    SYSTEM_ADMIN = "system_admin"
    
    # Compliance permissions
    VIEW_COMPLIANCE_REPORTS = "view_compliance_reports"
    MANAGE_COMPLIANCE = "manage_compliance"

class ResourceType(Enum):
    """Resource types for access control"""
    EVALUATION = "evaluation"
    TASK = "task"
    MODEL = "model"
    DATASET = "dataset"
    RESULT = "result"
    SECURITY_LOG = "security_log"
    AUDIT_LOG = "audit_log"
    USER = "user"
    ROLE = "role"
    SYSTEM = "system"

@dataclass
class Role:
    """Represents a user role with permissions"""
    role_id: str
    name: str
    description: str
    permissions: Set[Permission]
    created_at: datetime
    updated_at: datetime
    is_active: bool = True
    metadata: Dict[str, Any] = None
    
    def __post_init__(self):
        if self.metadata is None:
            self.metadata = {}

@dataclass
class User:
    """Represents a system user"""
    user_id: str
    username: str
    email: str
    roles: Set[str]  # Role IDs
    created_at: datetime
    last_login: Optional[datetime] = None
    is_active: bool = True
    password_hash: Optional[str] = None
    api_key: Optional[str] = None
    session_timeout: int = 3600  # seconds
    metadata: Dict[str, Any] = None
    
    def __post_init__(self):
        if self.metadata is None:
            self.metadata = {}

@dataclass
class Session:
    """Represents a user session"""
    session_id: str
    user_id: str
    created_at: datetime
    expires_at: datetime
    ip_address: Optional[str] = None
    user_agent: Optional[str] = None
    is_active: bool = True
    metadata: Dict[str, Any] = None
    
    def __post_init__(self):
        if self.metadata is None:
            self.metadata = {}

@dataclass
class AccessRequest:
    """Represents an access request"""
    request_id: str
    user_id: str
    resource_type: ResourceType
    resource_id: str
    permission: Permission
    timestamp: datetime
    ip_address: Optional[str] = None
    user_agent: Optional[str] = None
    context: Dict[str, Any] = None
    
    def __post_init__(self):
        if self.context is None:
            self.context = {}
        if not self.request_id:
            self.request_id = hashlib.sha256(
                f"{self.user_id}{self.resource_type.value}{self.resource_id}{self.permission.value}{self.timestamp}".encode()
            ).hexdigest()[:16]

class PasswordManager:
    """Secure password management"""
    
    @staticmethod
    def hash_password(password: str) -> str:
        """Hash password using bcrypt"""
        import bcrypt
        return bcrypt.hashpw(password.encode('utf-8'), bcrypt.gensalt()).decode('utf-8')
    
    @staticmethod
    def verify_password(password: str, password_hash: str) -> bool:
        """Verify password against hash"""
        import bcrypt
        return bcrypt.checkpw(password.encode('utf-8'), password_hash.encode('utf-8'))
    
    @staticmethod
    def generate_api_key() -> str:
        """Generate secure API key"""
        return secrets.token_urlsafe(32)

class JWTManager:
    """JWT token management"""
    
    def __init__(self, secret_key: str, algorithm: str = "HS256"):
        self.secret_key = secret_key
        self.algorithm = algorithm
    
    def create_token(self, user_id: str, roles: List[str], 
                    expires_in: int = 3600) -> str:
        """Create JWT token"""
        payload = {
            'user_id': user_id,
            'roles': roles,
            'iat': datetime.utcnow(),
            'exp': datetime.utcnow() + timedelta(seconds=expires_in)
        }
        
        return jwt.encode(payload, self.secret_key, algorithm=self.algorithm)
    
    def verify_token(self, token: str) -> Optional[Dict[str, Any]]:
        """Verify and decode JWT token"""
        try:
            payload = jwt.decode(token, self.secret_key, algorithms=[self.algorithm])
            return payload
        except jwt.ExpiredSignatureError:
            logger.warning("JWT token expired")
            return None
        except jwt.InvalidTokenError:
            logger.warning("Invalid JWT token")
            return None

class AccessControlManager:
    """Role-based access control and data privacy enforcement system"""
    
    def __init__(self, config: Optional[Dict[str, Any]] = None):
        self.config = config or {}
        
        # Storage
        self.users: Dict[str, User] = {}
        self.roles: Dict[str, Role] = {}
        self.sessions: Dict[str, Session] = {}
        self.access_requests: List[AccessRequest] = []
        
        # Security components
        self.password_manager = PasswordManager()
        self.jwt_manager = JWTManager(
            secret_key=self.config.get('jwt_secret', secrets.token_urlsafe(32))
        )
        
        # Configuration
        self.session_timeout = self.config.get('session_timeout', 3600)
        self.max_login_attempts = self.config.get('max_login_attempts', 5)
        self.login_attempts: Dict[str, List[datetime]] = {}
        
        # Initialize default roles
        self._initialize_default_roles()
        
        # Cleanup task
        self.cleanup_task: Optional[asyncio.Task] = None
        self.is_running = False
    
    def _initialize_default_roles(self):
        """Initialize default system roles"""
        default_roles = [
            Role(
                role_id="admin",
                name="Administrator",
                description="Full system access",
                permissions={
                    Permission.SYSTEM_ADMIN,
                    Permission.MANAGE_USERS,
                    Permission.MANAGE_ROLES,
                    Permission.CREATE_EVALUATION,
                    Permission.VIEW_EVALUATION,
                    Permission.MODIFY_EVALUATION,
                    Permission.DELETE_EVALUATION,
                    Permission.CREATE_TASK,
                    Permission.VIEW_TASK,
                    Permission.MODIFY_TASK,
                    Permission.DELETE_TASK,
                    Permission.EXECUTE_TASK,
                    Permission.VIEW_MODEL_CONFIG,
                    Permission.MODIFY_MODEL_CONFIG,
                    Permission.USE_MODEL,
                    Permission.VIEW_DATA,
                    Permission.MODIFY_DATA,
                    Permission.DELETE_DATA,
                    Permission.EXPORT_DATA,
                    Permission.VIEW_SECURITY_LOGS,
                    Permission.MODIFY_SECURITY_CONFIG,
                    Permission.VIEW_AUDIT_LOGS,
                    Permission.VIEW_COMPLIANCE_REPORTS,
                    Permission.MANAGE_COMPLIANCE
                },
                created_at=datetime.utcnow(),
                updated_at=datetime.utcnow()
            ),
            Role(
                role_id="evaluator",
                name="Evaluator",
                description="Can create and run evaluations",
                permissions={
                    Permission.CREATE_EVALUATION,
                    Permission.VIEW_EVALUATION,
                    Permission.MODIFY_EVALUATION,
                    Permission.VIEW_TASK,
                    Permission.EXECUTE_TASK,
                    Permission.USE_MODEL,
                    Permission.VIEW_DATA,
                    Permission.EXPORT_DATA
                },
                created_at=datetime.utcnow(),
                updated_at=datetime.utcnow()
            ),
            Role(
                role_id="viewer",
                name="Viewer",
                description="Read-only access to evaluations and results",
                permissions={
                    Permission.VIEW_EVALUATION,
                    Permission.VIEW_TASK,
                    Permission.VIEW_DATA
                },
                created_at=datetime.utcnow(),
                updated_at=datetime.utcnow()
            ),
            Role(
                role_id="security_analyst",
                name="Security Analyst",
                description="Access to security and audit logs",
                permissions={
                    Permission.VIEW_SECURITY_LOGS,
                    Permission.VIEW_AUDIT_LOGS,
                    Permission.VIEW_COMPLIANCE_REPORTS
                },
                created_at=datetime.utcnow(),
                updated_at=datetime.utcnow()
            )
        ]
        
        for role in default_roles:
            self.roles[role.role_id] = role
        
        logger.info(f"Initialized {len(default_roles)} default roles")
    
    async def start_cleanup(self):
        """Start session cleanup task"""
        if self.is_running:
            return
        
        self.is_running = True
        self.cleanup_task = asyncio.create_task(self._cleanup_loop())
        logger.info("Started access control cleanup")
    
    async def stop_cleanup(self):
        """Stop session cleanup task"""
        self.is_running = False
        if self.cleanup_task:
            self.cleanup_task.cancel()
            try:
                await self.cleanup_task
            except asyncio.CancelledError:
                pass
        logger.info("Stopped access control cleanup")
    
    async def _cleanup_loop(self):
        """Cleanup expired sessions and old access requests"""
        while self.is_running:
            try:
                current_time = datetime.utcnow()
                
                # Clean up expired sessions
                expired_sessions = [
                    session_id for session_id, session in self.sessions.items()
                    if session.expires_at < current_time
                ]
                
                for session_id in expired_sessions:
                    del self.sessions[session_id]
                
                if expired_sessions:
                    logger.info(f"Cleaned up {len(expired_sessions)} expired sessions")
                
                # Clean up old access requests (keep for 30 days)
                cutoff_time = current_time - timedelta(days=30)
                self.access_requests = [
                    req for req in self.access_requests
                    if req.timestamp > cutoff_time
                ]
                
                # Clean up old login attempts (keep for 1 hour)
                attempt_cutoff = current_time - timedelta(hours=1)
                for user_id in list(self.login_attempts.keys()):
                    self.login_attempts[user_id] = [
                        attempt for attempt in self.login_attempts[user_id]
                        if attempt > attempt_cutoff
                    ]
                    if not self.login_attempts[user_id]:
                        del self.login_attempts[user_id]
                
                await asyncio.sleep(300)  # Clean up every 5 minutes
                
            except asyncio.CancelledError:
                break
            except Exception as e:
                logger.error(f"Error in cleanup loop: {e}")
                await asyncio.sleep(60)
    
    def create_user(self, username: str, email: str, password: str,
                   roles: List[str]) -> str:
        """Create new user"""
        # Validate roles exist
        for role_id in roles:
            if role_id not in self.roles:
                raise ValueError(f"Role {role_id} does not exist")
        
        user_id = hashlib.sha256(f"{username}{email}{datetime.utcnow()}".encode()).hexdigest()[:16]
        
        user = User(
            user_id=user_id,
            username=username,
            email=email,
            roles=set(roles),
            created_at=datetime.utcnow(),
            password_hash=self.password_manager.hash_password(password),
            api_key=self.password_manager.generate_api_key()
        )
        
        self.users[user_id] = user
        logger.info(f"Created user: {username} ({user_id})")
        return user_id
    
    def authenticate_user(self, username: str, password: str,
                         ip_address: Optional[str] = None) -> Optional[str]:
        """Authenticate user and create session"""
        # Check for rate limiting
        if self._is_rate_limited(username, ip_address):
            logger.warning(f"Rate limited login attempt for {username} from {ip_address}")
            return None
        
        # Find user by username
        user = None
        for u in self.users.values():
            if u.username == username and u.is_active:
                user = u
                break
        
        if not user:
            self._record_failed_attempt(username, ip_address)
            return None
        
        # Verify password
        if not self.password_manager.verify_password(password, user.password_hash):
            self._record_failed_attempt(username, ip_address)
            return None
        
        # Create session
        session_id = secrets.token_urlsafe(32)
        session = Session(
            session_id=session_id,
            user_id=user.user_id,
            created_at=datetime.utcnow(),
            expires_at=datetime.utcnow() + timedelta(seconds=self.session_timeout),
            ip_address=ip_address
        )
        
        self.sessions[session_id] = session
        user.last_login = datetime.utcnow()
        
        # Clear failed attempts
        if username in self.login_attempts:
            del self.login_attempts[username]
        
        logger.info(f"User authenticated: {username} ({user.user_id})")
        return session_id
    
    def authenticate_api_key(self, api_key: str) -> Optional[str]:
        """Authenticate using API key"""
        for user in self.users.values():
            if user.api_key == api_key and user.is_active:
                # Create session for API key authentication
                session_id = secrets.token_urlsafe(32)
                session = Session(
                    session_id=session_id,
                    user_id=user.user_id,
                    created_at=datetime.utcnow(),
                    expires_at=datetime.utcnow() + timedelta(seconds=self.session_timeout)
                )
                
                self.sessions[session_id] = session
                logger.info(f"API key authenticated: {user.username} ({user.user_id})")
                return session_id
        
        return None
    
    def _is_rate_limited(self, username: str, ip_address: Optional[str]) -> bool:
        """Check if user/IP is rate limited"""
        current_time = datetime.utcnow()
        cutoff_time = current_time - timedelta(minutes=15)  # 15-minute window
        
        # Check username attempts
        if username in self.login_attempts:
            recent_attempts = [
                attempt for attempt in self.login_attempts[username]
                if attempt > cutoff_time
            ]
            if len(recent_attempts) >= self.max_login_attempts:
                return True
        
        return False
    
    def _record_failed_attempt(self, username: str, ip_address: Optional[str]):
        """Record failed login attempt"""
        if username not in self.login_attempts:
            self.login_attempts[username] = []
        
        self.login_attempts[username].append(datetime.utcnow())
        logger.warning(f"Failed login attempt: {username} from {ip_address}")
    
    def logout_user(self, session_id: str) -> bool:
        """Logout user by invalidating session"""
        if session_id in self.sessions:
            session = self.sessions[session_id]
            session.is_active = False
            del self.sessions[session_id]
            logger.info(f"User logged out: session {session_id}")
            return True
        return False
    
    def get_user_from_session(self, session_id: str) -> Optional[User]:
        """Get user from session ID"""
        session = self.sessions.get(session_id)
        if not session or not session.is_active:
            return None
        
        if session.expires_at < datetime.utcnow():
            # Session expired
            del self.sessions[session_id]
            return None
        
        return self.users.get(session.user_id)
    
    def has_permission(self, user_id: str, permission: Permission,
                      resource_type: Optional[ResourceType] = None,
                      resource_id: Optional[str] = None) -> bool:
        """Check if user has specific permission"""
        user = self.users.get(user_id)
        if not user or not user.is_active:
            return False
        
        # Get all permissions for user's roles
        user_permissions = set()
        for role_id in user.roles:
            role = self.roles.get(role_id)
            if role and role.is_active:
                user_permissions.update(role.permissions)
        
        # Check if user has the required permission
        has_perm = permission in user_permissions
        
        # Log access request
        self._log_access_request(user_id, permission, resource_type, resource_id, has_perm)
        
        return has_perm
    
    def _log_access_request(self, user_id: str, permission: Permission,
                           resource_type: Optional[ResourceType],
                           resource_id: Optional[str], granted: bool):
        """Log access request for audit purposes"""
        request = AccessRequest(
            request_id="",
            user_id=user_id,
            resource_type=resource_type or ResourceType.SYSTEM,
            resource_id=resource_id or "system",
            permission=permission,
            timestamp=datetime.utcnow(),
            context={'granted': granted}
        )
        
        self.access_requests.append(request)
        
        # Keep only last 10000 requests in memory
        if len(self.access_requests) > 10000:
            self.access_requests = self.access_requests[-10000:]
    
    def require_permission(self, permission: Permission,
                          resource_type: Optional[ResourceType] = None,
                          resource_id: Optional[str] = None):
        """Decorator to require specific permission"""
        def decorator(func):
            @wraps(func)
            async def wrapper(*args, **kwargs):
                # Extract user_id from kwargs or session
                user_id = kwargs.get('user_id')
                session_id = kwargs.get('session_id')
                
                if not user_id and session_id:
                    user = self.get_user_from_session(session_id)
                    user_id = user.user_id if user else None
                
                if not user_id:
                    raise PermissionError("Authentication required")
                
                if not self.has_permission(user_id, permission, resource_type, resource_id):
                    raise PermissionError(f"Permission denied: {permission.value}")
                
                return await func(*args, **kwargs)
            return wrapper
        return decorator
    
    def create_role(self, name: str, description: str,
                   permissions: List[Permission]) -> str:
        """Create new role"""
        role_id = hashlib.sha256(f"{name}{datetime.utcnow()}".encode()).hexdigest()[:16]
        
        role = Role(
            role_id=role_id,
            name=name,
            description=description,
            permissions=set(permissions),
            created_at=datetime.utcnow(),
            updated_at=datetime.utcnow()
        )
        
        self.roles[role_id] = role
        logger.info(f"Created role: {name} ({role_id})")
        return role_id
    
    def assign_role(self, user_id: str, role_id: str) -> bool:
        """Assign role to user"""
        user = self.users.get(user_id)
        role = self.roles.get(role_id)
        
        if not user or not role:
            return False
        
        user.roles.add(role_id)
        logger.info(f"Assigned role {role_id} to user {user_id}")
        return True
    
    def revoke_role(self, user_id: str, role_id: str) -> bool:
        """Revoke role from user"""
        user = self.users.get(user_id)
        
        if not user or role_id not in user.roles:
            return False
        
        user.roles.remove(role_id)
        logger.info(f"Revoked role {role_id} from user {user_id}")
        return True
    
    def get_user_permissions(self, user_id: str) -> Set[Permission]:
        """Get all permissions for a user"""
        user = self.users.get(user_id)
        if not user:
            return set()
        
        permissions = set()
        for role_id in user.roles:
            role = self.roles.get(role_id)
            if role and role.is_active:
                permissions.update(role.permissions)
        
        return permissions
    
    def list_users(self, active_only: bool = True) -> List[User]:
        """List all users"""
        users = list(self.users.values())
        if active_only:
            users = [u for u in users if u.is_active]
        return users
    
    def list_roles(self, active_only: bool = True) -> List[Role]:
        """List all roles"""
        roles = list(self.roles.values())
        if active_only:
            roles = [r for r in roles if r.is_active]
        return roles
    
    def get_access_audit(self, user_id: Optional[str] = None,
                        start_time: Optional[datetime] = None,
                        end_time: Optional[datetime] = None,
                        limit: int = 1000) -> List[AccessRequest]:
        """Get access audit trail"""
        requests = self.access_requests.copy()
        
        # Apply filters
        if user_id:
            requests = [r for r in requests if r.user_id == user_id]
        
        if start_time:
            requests = [r for r in requests if r.timestamp >= start_time]
        
        if end_time:
            requests = [r for r in requests if r.timestamp <= end_time]
        
        # Sort by timestamp (newest first) and limit
        requests.sort(key=lambda x: x.timestamp, reverse=True)
        return requests[:limit]
    
    def generate_access_report(self, start_time: Optional[datetime] = None,
                              end_time: Optional[datetime] = None) -> Dict[str, Any]:
        """Generate access control report"""
        if end_time is None:
            end_time = datetime.utcnow()
        if start_time is None:
            start_time = end_time - timedelta(days=30)
        
        # Get access requests in time range
        requests = self.get_access_audit(start_time=start_time, end_time=end_time, limit=None)
        
        report = {
            'report_period': {
                'start': start_time.isoformat(),
                'end': end_time.isoformat()
            },
            'generated_at': datetime.utcnow().isoformat(),
            'total_requests': len(requests),
            'granted_requests': len([r for r in requests if r.context.get('granted', False)]),
            'denied_requests': len([r for r in requests if not r.context.get('granted', False)]),
            'unique_users': len(set(r.user_id for r in requests)),
            'requests_by_permission': {},
            'requests_by_user': {},
            'requests_by_resource_type': {}
        }
        
        # Count by permission
        for request in requests:
            perm = request.permission.value
            if perm not in report['requests_by_permission']:
                report['requests_by_permission'][perm] = {'total': 0, 'granted': 0, 'denied': 0}
            
            report['requests_by_permission'][perm]['total'] += 1
            if request.context.get('granted', False):
                report['requests_by_permission'][perm]['granted'] += 1
            else:
                report['requests_by_permission'][perm]['denied'] += 1
        
        # Count by user
        for request in requests:
            user_id = request.user_id
            if user_id not in report['requests_by_user']:
                report['requests_by_user'][user_id] = {'total': 0, 'granted': 0, 'denied': 0}
            
            report['requests_by_user'][user_id]['total'] += 1
            if request.context.get('granted', False):
                report['requests_by_user'][user_id]['granted'] += 1
            else:
                report['requests_by_user'][user_id]['denied'] += 1
        
        # Count by resource type
        for request in requests:
            resource_type = request.resource_type.value
            if resource_type not in report['requests_by_resource_type']:
                report['requests_by_resource_type'][resource_type] = {'total': 0, 'granted': 0, 'denied': 0}
            
            report['requests_by_resource_type'][resource_type]['total'] += 1
            if request.context.get('granted', False):
                report['requests_by_resource_type'][resource_type]['granted'] += 1
            else:
                report['requests_by_resource_type'][resource_type]['denied'] += 1
        
        return report
    
    def get_system_status(self) -> Dict[str, Any]:
        """Get access control system status"""
        active_sessions = len([s for s in self.sessions.values() if s.is_active])
        
        return {
            'status': 'active' if self.is_running else 'stopped',
            'total_users': len(self.users),
            'active_users': len([u for u in self.users.values() if u.is_active]),
            'total_roles': len(self.roles),
            'active_roles': len([r for r in self.roles.values() if r.is_active]),
            'active_sessions': active_sessions,
            'total_access_requests': len(self.access_requests),
            'session_timeout': self.session_timeout,
            'max_login_attempts': self.max_login_attempts
        }