"""
Security Utilities

Collection of security utility functions and helpers for the
evaluation engine testing framework.
"""

import os
import re
import hashlib
import secrets
import logging
from typing import Dict, List, Optional, Any, Tuple, Union
from pathlib import Path
import subprocess
import tempfile
import shutil
from datetime import datetime, timedelta

logger = logging.getLogger(__name__)


class SecurityUtils:
    """Collection of security utility functions."""
    
    @staticmethod
    def generate_secure_token(length: int = 32) -> str:
        """
        Generate a cryptographically secure random token.
        
        Args:
            length: Token length in bytes
            
        Returns:
            URL-safe base64 encoded token
        """
        return secrets.token_urlsafe(length)
    
    @staticmethod
    def generate_api_key_pair() -> Tuple[str, str]:
        """
        Generate an API key ID and secret pair.
        
        Returns:
            Tuple of (key_id, key_secret)
        """
        key_id = secrets.token_urlsafe(16)
        key_secret = secrets.token_urlsafe(32)
        return key_id, key_secret
    
    @staticmethod
    def hash_password(password: str, salt: Optional[str] = None) -> Tuple[str, str]:
        """
        Hash a password with salt using PBKDF2.
        
        Args:
            password: Password to hash
            salt: Optional salt (generated if None)
            
        Returns:
            Tuple of (hashed_password, salt)
        """
        if salt is None:
            salt = secrets.token_hex(16)
        
        # Use PBKDF2 with SHA256
        hashed = hashlib.pbkdf2_hmac('sha256', password.encode(), salt.encode(), 100000)
        return hashed.hex(), salt
    
    @staticmethod
    def verify_password(password: str, hashed_password: str, salt: str) -> bool:
        """
        Verify a password against its hash.
        
        Args:
            password: Password to verify
            hashed_password: Stored password hash
            salt: Password salt
            
        Returns:
            True if password matches
        """
        test_hash, _ = SecurityUtils.hash_password(password, salt)
        return secrets.compare_digest(test_hash, hashed_password)
    
    @staticmethod
    def sanitize_filename(filename: str) -> str:
        """
        Sanitize a filename for safe use.
        
        Args:
            filename: Original filename
            
        Returns:
            Sanitized filename
        """
        # Remove or replace dangerous characters
        sanitized = re.sub(r'[<>:"/\\|?*\x00-\x1f]', '_', filename)
        
        # Remove leading/trailing dots and spaces
        sanitized = sanitized.strip('. ')
        
        # Limit length
        if len(sanitized) > 255:
            name, ext = os.path.splitext(sanitized)
            sanitized = name[:255-len(ext)] + ext
        
        # Ensure not empty
        if not sanitized:
            sanitized = 'unnamed_file'
        
        return sanitized
    
    @staticmethod
    def validate_path_safety(path: Union[str, Path], allowed_roots: List[Path]) -> bool:
        """
        Validate that a path is safe and within allowed roots.
        
        Args:
            path: Path to validate
            allowed_roots: List of allowed root directories
            
        Returns:
            True if path is safe
        """
        try:
            path = Path(path).resolve()
            
            # Check if path is within any allowed root
            for root in allowed_roots:
                root = Path(root).resolve()
                try:
                    path.relative_to(root)
                    return True
                except ValueError:
                    continue
            
            return False
            
        except Exception:
            return False
    
    @staticmethod
    def detect_shell_injection(command: str) -> List[str]:
        """
        Detect potential shell injection patterns in a command.
        
        Args:
            command: Command string to analyze
            
        Returns:
            List of detected injection patterns
        """
        patterns = []
        
        # Common injection patterns
        injection_indicators = [
            (r';\s*rm\s+', 'Command chaining with rm'),
            (r'&&\s*rm\s+', 'Conditional execution with rm'),
            (r'\|\s*sh\s*', 'Pipe to shell'),
            (r'`[^`]*`', 'Command substitution (backticks)'),
            (r'\$\([^)]*\)', 'Command substitution ($())'),
            (r'>\s*/dev/', 'Writing to device files'),
            (r'<\s*/dev/', 'Reading from device files'),
            (r';\s*wget\s+', 'Command chaining with wget'),
            (r';\s*curl\s+', 'Command chaining with curl'),
            (r'\|\s*nc\s+', 'Pipe to netcat'),
            (r'eval\s*\(', 'Eval function call'),
            (r'exec\s*\(', 'Exec function call')
        ]
        
        for pattern, description in injection_indicators:
            if re.search(pattern, command, re.IGNORECASE):
                patterns.append(description)
        
        return patterns
    
    @staticmethod
    def calculate_file_hash(file_path: Union[str, Path], algorithm: str = 'sha256') -> str:
        """
        Calculate hash of a file.
        
        Args:
            file_path: Path to file
            algorithm: Hash algorithm (md5, sha1, sha256, etc.)
            
        Returns:
            Hexadecimal hash string
        """
        hash_obj = hashlib.new(algorithm)
        
        with open(file_path, 'rb') as f:
            for chunk in iter(lambda: f.read(4096), b""):
                hash_obj.update(chunk)
        
        return hash_obj.hexdigest()
    
    @staticmethod
    def secure_delete_file(file_path: Union[str, Path], passes: int = 3) -> bool:
        """
        Securely delete a file by overwriting it multiple times.
        
        Args:
            file_path: Path to file to delete
            passes: Number of overwrite passes
            
        Returns:
            True if file was securely deleted
        """
        try:
            file_path = Path(file_path)
            
            if not file_path.exists():
                return True
            
            file_size = file_path.stat().st_size
            
            # Overwrite file multiple times
            with open(file_path, 'r+b') as f:
                for _ in range(passes):
                    f.seek(0)
                    f.write(secrets.token_bytes(file_size))
                    f.flush()
                    os.fsync(f.fileno())
            
            # Finally delete the file
            file_path.unlink()
            return True
            
        except Exception as e:
            logger.error(f"Secure delete failed for {file_path}: {e}")
            return False
    
    @staticmethod
    def create_secure_temp_dir(prefix: str = 'secure_', suffix: str = '') -> Path:
        """
        Create a secure temporary directory with restricted permissions.
        
        Args:
            prefix: Directory name prefix
            suffix: Directory name suffix
            
        Returns:
            Path to created directory
        """
        temp_dir = Path(tempfile.mkdtemp(prefix=prefix, suffix=suffix))
        
        # Set restrictive permissions (owner only)
        if hasattr(os, 'chmod'):
            os.chmod(temp_dir, 0o700)
        
        return temp_dir
    
    @staticmethod
    def validate_environment_variables(env_vars: Dict[str, str]) -> List[str]:
        """
        Validate environment variables for security issues.
        
        Args:
            env_vars: Environment variables to validate
            
        Returns:
            List of security warnings
        """
        warnings = []
        
        # Dangerous environment variables
        dangerous_vars = {
            'LD_PRELOAD': 'Can be used to inject malicious libraries',
            'LD_LIBRARY_PATH': 'Can redirect library loading',
            'DYLD_INSERT_LIBRARIES': 'macOS library injection',
            'PATH': 'Can redirect command execution',
            'PYTHONPATH': 'Can inject malicious Python modules',
            'PERL5LIB': 'Can inject malicious Perl modules',
            'RUBYLIB': 'Can inject malicious Ruby modules'
        }
        
        for var_name, var_value in env_vars.items():
            if var_name in dangerous_vars:
                warnings.append(f"{var_name}: {dangerous_vars[var_name]}")
            
            # Check for suspicious values
            if any(char in var_value for char in ['|', '&', ';', '`', '$(']):
                warnings.append(f"{var_name} contains suspicious characters")
        
        return warnings
    
    @staticmethod
    def check_system_security() -> Dict[str, Any]:
        """
        Check system security configuration.
        
        Returns:
            Dictionary with security check results
        """
        results = {
            'timestamp': datetime.now().isoformat(),
            'checks': {},
            'warnings': [],
            'recommendations': []
        }
        
        # Check if running as root
        if os.getuid() == 0 if hasattr(os, 'getuid') else False:
            results['warnings'].append('Running as root user')
            results['recommendations'].append('Run with non-privileged user account')
        
        # Check temporary directory permissions
        temp_dir = Path(tempfile.gettempdir())
        if temp_dir.exists():
            stat_info = temp_dir.stat()
            if stat_info.st_mode & 0o002:  # World writable
                results['warnings'].append('Temporary directory is world-writable')
                results['recommendations'].append('Secure temporary directory permissions')
        
        # Check available security tools
        security_tools = ['chroot', 'unshare', 'firejail', 'bubblewrap']
        available_tools = []
        
        for tool in security_tools:
            if shutil.which(tool):
                available_tools.append(tool)
        
        results['checks']['available_security_tools'] = available_tools
        
        if not available_tools:
            results['warnings'].append('No additional security tools available')
            results['recommendations'].append('Install security tools like firejail or bubblewrap')
        
        # Check system limits
        try:
            import resource
            
            # Check memory limit
            mem_limit = resource.getrlimit(resource.RLIMIT_AS)
            results['checks']['memory_limit'] = mem_limit
            
            # Check file descriptor limit
            fd_limit = resource.getrlimit(resource.RLIMIT_NOFILE)
            results['checks']['file_descriptor_limit'] = fd_limit
            
            # Check process limit
            proc_limit = resource.getrlimit(resource.RLIMIT_NPROC)
            results['checks']['process_limit'] = proc_limit
            
        except ImportError:
            results['warnings'].append('Resource module not available')
        
        return results
    
    @staticmethod
    def generate_security_report(security_events: List[Dict[str, Any]]) -> str:
        """
        Generate a security report from events.
        
        Args:
            security_events: List of security events
            
        Returns:
            Formatted security report
        """
        report_lines = [
            "SECURITY REPORT",
            "=" * 50,
            f"Generated: {datetime.now().isoformat()}",
            f"Total Events: {len(security_events)}",
            ""
        ]
        
        if not security_events:
            report_lines.append("No security events recorded.")
            return "\n".join(report_lines)
        
        # Categorize events
        event_types = {}
        for event in security_events:
            event_type = event.get('event_type', 'unknown')
            if event_type not in event_types:
                event_types[event_type] = []
            event_types[event_type].append(event)
        
        # Summary by type
        report_lines.extend([
            "EVENT SUMMARY BY TYPE:",
            "-" * 30
        ])
        
        for event_type, events in sorted(event_types.items()):
            report_lines.append(f"{event_type}: {len(events)}")
        
        report_lines.append("")
        
        # Recent critical events
        critical_events = [
            event for event in security_events
            if event.get('severity') in ['HIGH', 'CRITICAL'] or
            event.get('event_type', '').endswith('_violation')
        ]
        
        if critical_events:
            report_lines.extend([
                "CRITICAL EVENTS:",
                "-" * 20
            ])
            
            for event in critical_events[-10:]:  # Last 10 critical events
                timestamp = event.get('timestamp', 'Unknown')
                event_type = event.get('event_type', 'Unknown')
                details = event.get('details', {})
                
                report_lines.append(f"[{timestamp}] {event_type}")
                if details:
                    for key, value in details.items():
                        report_lines.append(f"  {key}: {value}")
                report_lines.append("")
        
        # Recommendations
        recommendations = SecurityUtils._generate_recommendations(security_events)
        if recommendations:
            report_lines.extend([
                "SECURITY RECOMMENDATIONS:",
                "-" * 30
            ])
            for i, rec in enumerate(recommendations, 1):
                report_lines.append(f"{i}. {rec}")
        
        return "\n".join(report_lines)
    
    @staticmethod
    def _generate_recommendations(security_events: List[Dict[str, Any]]) -> List[str]:
        """Generate security recommendations based on events."""
        recommendations = []
        
        # Count violation types
        violation_counts = {}
        for event in security_events:
            if event.get('event_type', '').endswith('_violation'):
                violation_type = event['event_type']
                violation_counts[violation_type] = violation_counts.get(violation_type, 0) + 1
        
        # Generate recommendations based on violations
        if violation_counts.get('command_validation_violation', 0) > 5:
            recommendations.append("Review and strengthen command validation policies")
        
        if violation_counts.get('resource_limit_violation', 0) > 3:
            recommendations.append("Adjust resource limits to prevent frequent violations")
        
        if violation_counts.get('file_access_violation', 0) > 2:
            recommendations.append("Review file access policies and permissions")
        
        if violation_counts.get('api_authentication_violation', 0) > 5:
            recommendations.append("Implement stronger API authentication measures")
        
        # Check for patterns
        recent_events = [
            event for event in security_events
            if 'timestamp' in event and
            datetime.fromisoformat(event['timestamp']) > datetime.now() - timedelta(hours=1)
        ]
        
        if len(recent_events) > 20:
            recommendations.append("High security event frequency - investigate potential attacks")
        
        if not recommendations:
            recommendations.append("Security posture appears good - continue monitoring")
        
        return recommendations
    
    @staticmethod
    def create_security_context() -> Dict[str, Any]:
        """
        Create a security context with current system information.
        
        Returns:
            Security context dictionary
        """
        context = {
            'timestamp': datetime.now().isoformat(),
            'process_id': os.getpid(),
            'user_id': os.getuid() if hasattr(os, 'getuid') else None,
            'group_id': os.getgid() if hasattr(os, 'getgid') else None,
            'working_directory': str(Path.cwd()),
            'temp_directory': tempfile.gettempdir(),
            'environment_variables': dict(os.environ),
            'system_info': {}
        }
        
        # Add system information
        try:
            import platform
            context['system_info'] = {
                'system': platform.system(),
                'release': platform.release(),
                'version': platform.version(),
                'machine': platform.machine(),
                'processor': platform.processor()
            }
        except ImportError:
            pass
        
        return context


class SecurityContextManager:
    """Context manager for security operations."""
    
    def __init__(self, operation_name: str, security_manager=None):
        """
        Initialize security context manager.
        
        Args:
            operation_name: Name of the operation
            security_manager: Optional security manager instance
        """
        self.operation_name = operation_name
        self.security_manager = security_manager
        self.start_time = None
        self.context = None
    
    def __enter__(self):
        """Enter security context."""
        self.start_time = datetime.now()
        self.context = SecurityUtils.create_security_context()
        
        logger.info(f"Starting secure operation: {self.operation_name}")
        
        if self.security_manager:
            # Record security event
            self.security_manager._log_security_event('operation_started', {
                'operation_name': self.operation_name,
                'context': self.context
            })
        
        return self.context
    
    def __exit__(self, exc_type, exc_val, exc_tb):
        """Exit security context."""
        end_time = datetime.now()
        duration = (end_time - self.start_time).total_seconds()
        
        if exc_type is None:
            logger.info(f"Secure operation completed: {self.operation_name} ({duration:.2f}s)")
            
            if self.security_manager:
                self.security_manager._log_security_event('operation_completed', {
                    'operation_name': self.operation_name,
                    'duration': duration,
                    'success': True
                })
        else:
            logger.error(f"Secure operation failed: {self.operation_name} - {exc_val}")
            
            if self.security_manager:
                self.security_manager._log_security_event('operation_failed', {
                    'operation_name': self.operation_name,
                    'duration': duration,
                    'error': str(exc_val),
                    'success': False
                })