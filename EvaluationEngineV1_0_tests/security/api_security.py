"""
API Security

Provides authentication, authorization, and rate limiting
for API endpoints to ensure secure access control.
"""

import time
import hmac
import hashlib
import secrets
import logging
from typing import Dict, Optional, List, Callable, Any, Tuple
from dataclasses import dataclass, field
from datetime import datetime, timedelta
from collections import defaultdict
import threading
import jwt
from functools import wraps

logger = logging.getLogger(__name__)


@dataclass
class APIKey:
    """API key configuration."""
    key_id: str
    key_secret: str
    name: str
    permissions: List[str] = field(default_factory=list)
    rate_limit: Optional[int] = None  # requests per minute
    expires_at: Optional[datetime] = None
    created_at: datetime = field(default_factory=datetime.now)
    last_used: Optional[datetime] = None
    is_active: bool = True


@dataclass
class RateLimitConfig:
    """Rate limiting configuration."""
    requests_per_minute: int = 60
    requests_per_hour: int = 1000
    requests_per_day: int = 10000
    burst_limit: int = 10
    window_size: int = 60  # seconds


class AuthenticationError(Exception):
    """Raised when authentication fails."""
    pass


class AuthorizationError(Exception):
    """Raised when authorization fails."""
    pass


class RateLimitExceeded(Exception):
    """Raised when rate limit is exceeded."""
    pass


class APIAuthenticator:
    """
    Handles API authentication and authorization.
    
    Features:
    - API key authentication
    - JWT token authentication
    - Permission-based authorization
    - Key management and rotation
    - Audit logging
    """
    
    def __init__(self, secret_key: Optional[str] = None):
        """
        Initialize API authenticator.
        
        Args:
            secret_key: Secret key for JWT signing (generated if None)
        """
        self.secret_key = secret_key or secrets.token_urlsafe(32)
        self.api_keys: Dict[str, APIKey] = {}
        self.jwt_algorithm = 'HS256'
        self.jwt_expiry_hours = 24
        self._lock = threading.Lock()
        
        # Audit log
        self.audit_log: List[Dict] = []
    
    def generate_api_key(self, 
                        name: str, 
                        permissions: Optional[List[str]] = None,
                        rate_limit: Optional[int] = None,
                        expires_in_days: Optional[int] = None) -> APIKey:
        """
        Generate a new API key.
        
        Args:
            name: Human-readable name for the key
            permissions: List of permissions for the key
            rate_limit: Rate limit for this key (requests per minute)
            expires_in_days: Expiry in days (None for no expiry)
            
        Returns:
            Generated API key
        """
        key_id = secrets.token_urlsafe(16)
        key_secret = secrets.token_urlsafe(32)
        
        expires_at = None
        if expires_in_days:
            expires_at = datetime.now() + timedelta(days=expires_in_days)
        
        api_key = APIKey(
            key_id=key_id,
            key_secret=key_secret,
            name=name,
            permissions=permissions or [],
            rate_limit=rate_limit,
            expires_at=expires_at
        )
        
        with self._lock:
            self.api_keys[key_id] = api_key
        
        self._log_audit_event('api_key_generated', {
            'key_id': key_id,
            'name': name,
            'permissions': permissions
        })
        
        logger.info(f"Generated API key: {key_id} for {name}")
        return api_key
    
    def authenticate_api_key(self, key_id: str, key_secret: str) -> APIKey:
        """
        Authenticate using API key.
        
        Args:
            key_id: API key ID
            key_secret: API key secret
            
        Returns:
            Authenticated API key
            
        Raises:
            AuthenticationError: If authentication fails
        """
        with self._lock:
            api_key = self.api_keys.get(key_id)
        
        if not api_key:
            self._log_audit_event('auth_failed', {'key_id': key_id, 'reason': 'key_not_found'})
            raise AuthenticationError(f"Invalid API key ID: {key_id}")
        
        if not api_key.is_active:
            self._log_audit_event('auth_failed', {'key_id': key_id, 'reason': 'key_inactive'})
            raise AuthenticationError(f"API key is inactive: {key_id}")
        
        if api_key.expires_at and datetime.now() > api_key.expires_at:
            self._log_audit_event('auth_failed', {'key_id': key_id, 'reason': 'key_expired'})
            raise AuthenticationError(f"API key expired: {key_id}")
        
        # Verify secret using constant-time comparison
        if not hmac.compare_digest(api_key.key_secret, key_secret):
            self._log_audit_event('auth_failed', {'key_id': key_id, 'reason': 'invalid_secret'})
            raise AuthenticationError(f"Invalid API key secret: {key_id}")
        
        # Update last used timestamp
        api_key.last_used = datetime.now()
        
        self._log_audit_event('auth_success', {'key_id': key_id})
        logger.debug(f"API key authenticated: {key_id}")
        return api_key
    
    def generate_jwt_token(self, 
                          user_id: str, 
                          permissions: Optional[List[str]] = None,
                          expires_in_hours: Optional[int] = None) -> str:
        """
        Generate JWT token.
        
        Args:
            user_id: User identifier
            permissions: User permissions
            expires_in_hours: Token expiry in hours
            
        Returns:
            JWT token string
        """
        expires_in = expires_in_hours or self.jwt_expiry_hours
        exp_time = datetime.now() + timedelta(hours=expires_in)
        
        payload = {
            'user_id': user_id,
            'permissions': permissions or [],
            'exp': int(exp_time.timestamp()),
            'iat': int(datetime.now().timestamp()),
            'jti': secrets.token_urlsafe(16)  # JWT ID for revocation
        }
        
        token = jwt.encode(payload, self.secret_key, algorithm=self.jwt_algorithm)
        
        self._log_audit_event('jwt_generated', {
            'user_id': user_id,
            'permissions': permissions,
            'expires_at': exp_time.isoformat()
        })
        
        logger.info(f"Generated JWT token for user: {user_id}")
        return token
    
    def authenticate_jwt_token(self, token: str) -> Dict[str, Any]:
        """
        Authenticate JWT token.
        
        Args:
            token: JWT token string
            
        Returns:
            Decoded token payload
            
        Raises:
            AuthenticationError: If authentication fails
        """
        try:
            payload = jwt.decode(token, self.secret_key, algorithms=[self.jwt_algorithm])
            
            self._log_audit_event('jwt_auth_success', {
                'user_id': payload.get('user_id'),
                'jti': payload.get('jti')
            })
            
            return payload
            
        except jwt.ExpiredSignatureError:
            self._log_audit_event('jwt_auth_failed', {'reason': 'token_expired'})
            raise AuthenticationError("JWT token expired")
        
        except jwt.InvalidTokenError as e:
            self._log_audit_event('jwt_auth_failed', {'reason': 'invalid_token', 'error': str(e)})
            raise AuthenticationError(f"Invalid JWT token: {e}")
    
    def check_permission(self, permissions: List[str], required_permission: str) -> bool:
        """
        Check if user has required permission.
        
        Args:
            permissions: User's permissions
            required_permission: Required permission
            
        Returns:
            True if user has permission
        """
        # Admin permission grants all access
        if 'admin' in permissions:
            return True
        
        # Check for specific permission
        if required_permission in permissions:
            return True
        
        # Check for wildcard permissions
        for perm in permissions:
            if perm.endswith('*') and required_permission.startswith(perm[:-1]):
                return True
        
        return False
    
    def require_permission(self, required_permission: str):
        """
        Decorator to require specific permission.
        
        Args:
            required_permission: Required permission string
        """
        def decorator(func):
            @wraps(func)
            def wrapper(*args, **kwargs):
                # Extract permissions from context (implementation specific)
                # This would typically be done via request context
                permissions = kwargs.get('_permissions', [])
                
                if not self.check_permission(permissions, required_permission):
                    self._log_audit_event('authorization_failed', {
                        'required_permission': required_permission,
                        'user_permissions': permissions
                    })
                    raise AuthorizationError(f"Permission required: {required_permission}")
                
                return func(*args, **kwargs)
            return wrapper
        return decorator
    
    def revoke_api_key(self, key_id: str):
        """Revoke an API key."""
        with self._lock:
            if key_id in self.api_keys:
                self.api_keys[key_id].is_active = False
                self._log_audit_event('api_key_revoked', {'key_id': key_id})
                logger.info(f"Revoked API key: {key_id}")
    
    def list_api_keys(self) -> List[Dict[str, Any]]:
        """List all API keys (without secrets)."""
        with self._lock:
            return [
                {
                    'key_id': key.key_id,
                    'name': key.name,
                    'permissions': key.permissions,
                    'rate_limit': key.rate_limit,
                    'expires_at': key.expires_at.isoformat() if key.expires_at else None,
                    'created_at': key.created_at.isoformat(),
                    'last_used': key.last_used.isoformat() if key.last_used else None,
                    'is_active': key.is_active
                }
                for key in self.api_keys.values()
            ]
    
    def _log_audit_event(self, event_type: str, details: Dict[str, Any]):
        """Log audit event."""
        audit_entry = {
            'timestamp': datetime.now().isoformat(),
            'event_type': event_type,
            'details': details
        }
        
        self.audit_log.append(audit_entry)
        
        # Keep only last 1000 entries
        if len(self.audit_log) > 1000:
            self.audit_log = self.audit_log[-1000:]
    
    def get_audit_log(self, limit: int = 100) -> List[Dict[str, Any]]:
        """Get recent audit log entries."""
        return self.audit_log[-limit:]


class RateLimiter:
    """
    Implements rate limiting for API endpoints.
    
    Features:
    - Multiple time window support
    - Per-key rate limiting
    - Burst protection
    - Sliding window algorithm
    - Rate limit headers
    """
    
    def __init__(self, default_config: Optional[RateLimitConfig] = None):
        """
        Initialize rate limiter.
        
        Args:
            default_config: Default rate limit configuration
        """
        self.default_config = default_config or RateLimitConfig()
        self.request_history: Dict[str, List[float]] = defaultdict(list)
        self.custom_limits: Dict[str, RateLimitConfig] = {}
        self._lock = threading.Lock()
    
    def set_custom_limit(self, key: str, config: RateLimitConfig):
        """Set custom rate limit for a specific key."""
        with self._lock:
            self.custom_limits[key] = config
        logger.info(f"Set custom rate limit for {key}: {config.requests_per_minute}/min")
    
    def check_rate_limit(self, key: str, endpoint: Optional[str] = None) -> Tuple[bool, Dict[str, Any]]:
        """
        Check if request is within rate limits.
        
        Args:
            key: Rate limiting key (e.g., API key ID, IP address)
            endpoint: Optional endpoint identifier
            
        Returns:
            Tuple of (allowed, rate_limit_info)
        """
        current_time = time.time()
        rate_key = f"{key}:{endpoint}" if endpoint else key
        
        # Get rate limit configuration
        config = self.custom_limits.get(key, self.default_config)
        
        with self._lock:
            # Clean old requests
            self._clean_old_requests(rate_key, current_time)
            
            # Get request history
            requests = self.request_history[rate_key]
            
            # Check different time windows
            minute_requests = self._count_requests_in_window(requests, current_time, 60)
            hour_requests = self._count_requests_in_window(requests, current_time, 3600)
            day_requests = self._count_requests_in_window(requests, current_time, 86400)
            
            # Check limits
            if minute_requests >= config.requests_per_minute:
                return False, self._get_rate_limit_info(config, minute_requests, hour_requests, day_requests, 'minute')
            
            if hour_requests >= config.requests_per_hour:
                return False, self._get_rate_limit_info(config, minute_requests, hour_requests, day_requests, 'hour')
            
            if day_requests >= config.requests_per_day:
                return False, self._get_rate_limit_info(config, minute_requests, hour_requests, day_requests, 'day')
            
            # Check burst limit
            recent_requests = self._count_requests_in_window(requests, current_time, config.window_size)
            if recent_requests >= config.burst_limit:
                return False, self._get_rate_limit_info(config, minute_requests, hour_requests, day_requests, 'burst')
            
            # Record this request
            requests.append(current_time)
            
            return True, self._get_rate_limit_info(config, minute_requests + 1, hour_requests + 1, day_requests + 1)
    
    def _clean_old_requests(self, key: str, current_time: float):
        """Remove old requests from history."""
        # Keep requests from last 24 hours
        cutoff_time = current_time - 86400
        self.request_history[key] = [
            req_time for req_time in self.request_history[key]
            if req_time > cutoff_time
        ]
    
    def _count_requests_in_window(self, requests: List[float], current_time: float, window_seconds: int) -> int:
        """Count requests in time window."""
        cutoff_time = current_time - window_seconds
        return sum(1 for req_time in requests if req_time > cutoff_time)
    
    def _get_rate_limit_info(self, 
                           config: RateLimitConfig, 
                           minute_requests: int, 
                           hour_requests: int, 
                           day_requests: int,
                           limit_type: Optional[str] = None) -> Dict[str, Any]:
        """Get rate limit information for headers."""
        return {
            'limit_minute': config.requests_per_minute,
            'limit_hour': config.requests_per_hour,
            'limit_day': config.requests_per_day,
            'remaining_minute': max(0, config.requests_per_minute - minute_requests),
            'remaining_hour': max(0, config.requests_per_hour - hour_requests),
            'remaining_day': max(0, config.requests_per_day - day_requests),
            'reset_minute': int(time.time()) + 60,
            'reset_hour': int(time.time()) + 3600,
            'reset_day': int(time.time()) + 86400,
            'limit_type': limit_type
        }
    
    def rate_limit_decorator(self, key_extractor: Callable = None, endpoint: str = None):
        """
        Decorator for rate limiting functions.
        
        Args:
            key_extractor: Function to extract rate limiting key from arguments
            endpoint: Endpoint identifier
        """
        def decorator(func):
            @wraps(func)
            def wrapper(*args, **kwargs):
                # Extract rate limiting key
                if key_extractor:
                    key = key_extractor(*args, **kwargs)
                else:
                    key = kwargs.get('api_key_id', 'default')
                
                # Check rate limit
                allowed, rate_info = self.check_rate_limit(key, endpoint)
                
                if not allowed:
                    raise RateLimitExceeded(
                        f"Rate limit exceeded for {key}. "
                        f"Limit type: {rate_info.get('limit_type', 'unknown')}"
                    )
                
                # Add rate limit info to response context
                kwargs['_rate_limit_info'] = rate_info
                
                return func(*args, **kwargs)
            return wrapper
        return decorator
    
    def get_rate_limit_status(self, key: str) -> Dict[str, Any]:
        """Get current rate limit status for a key."""
        current_time = time.time()
        config = self.custom_limits.get(key, self.default_config)
        
        with self._lock:
            self._clean_old_requests(key, current_time)
            requests = self.request_history[key]
            
            minute_requests = self._count_requests_in_window(requests, current_time, 60)
            hour_requests = self._count_requests_in_window(requests, current_time, 3600)
            day_requests = self._count_requests_in_window(requests, current_time, 86400)
            
            return self._get_rate_limit_info(config, minute_requests, hour_requests, day_requests)
    
    def reset_rate_limit(self, key: str):
        """Reset rate limit for a specific key."""
        with self._lock:
            if key in self.request_history:
                del self.request_history[key]
        logger.info(f"Reset rate limit for key: {key}")
    
    def get_all_rate_limits(self) -> Dict[str, Dict[str, Any]]:
        """Get rate limit status for all keys."""
        with self._lock:
            return {
                key: self.get_rate_limit_status(key)
                for key in self.request_history.keys()
            }