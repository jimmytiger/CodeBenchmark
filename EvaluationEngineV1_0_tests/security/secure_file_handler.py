"""
Secure File Handler

Provides secure file operations with proper access controls,
temporary file management, and path validation.
"""

import os
import tempfile
import shutil
import hashlib
import logging
from pathlib import Path
from typing import Dict, List, Optional, Union, BinaryIO, TextIO, Any
from contextlib import contextmanager
import threading
import time
from dataclasses import dataclass
import stat

logger = logging.getLogger(__name__)


@dataclass
class FileAccessPolicy:
    """File access policy configuration."""
    allowed_extensions: set = None
    blocked_extensions: set = None
    allowed_paths: set = None
    blocked_paths: set = None
    max_file_size: int = 100 * 1024 * 1024  # 100MB
    max_total_size: int = 1024 * 1024 * 1024  # 1GB
    allow_executable: bool = False
    allow_symlinks: bool = False
    require_safe_names: bool = True


class SecureFileError(Exception):
    """Raised when secure file operations fail."""
    pass


class SecureFileHandler:
    """
    Provides secure file operations with access controls and validation.
    
    Features:
    - Path traversal prevention
    - File type validation
    - Size limits enforcement
    - Secure temporary file handling
    - Access logging and auditing
    - Automatic cleanup
    """
    
    # Dangerous file extensions
    DANGEROUS_EXTENSIONS = {
        '.exe', '.bat', '.cmd', '.com', '.pif', '.scr', '.vbs', '.js',
        '.jar', '.app', '.deb', '.rpm', '.dmg', '.pkg', '.msi',
        '.sh', '.bash', '.zsh', '.fish', '.ps1', '.psm1'
    }
    
    # Safe file extensions for testing
    SAFE_EXTENSIONS = {
        '.txt', '.md', '.json', '.yaml', '.yml', '.xml', '.csv',
        '.py', '.js', '.html', '.css', '.sql', '.log', '.conf',
        '.ini', '.cfg', '.properties', '.toml'
    }
    
    def __init__(self, 
                 base_dir: Optional[Path] = None,
                 policy: Optional[FileAccessPolicy] = None):
        """
        Initialize secure file handler.
        
        Args:
            base_dir: Base directory for file operations
            policy: File access policy (uses default if None)
        """
        self.base_dir = base_dir or Path(tempfile.gettempdir()) / "secure_files"
        self.policy = policy or self._create_default_policy()
        
        # Ensure base directory exists and is secure
        self._setup_base_directory()
        
        # Track temporary files and directories
        self.temp_files: Dict[str, Path] = {}
        self.temp_dirs: Dict[str, Path] = {}
        self._lock = threading.Lock()
        
        # Access log
        self.access_log: List[Dict] = []
    
    def _create_default_policy(self) -> FileAccessPolicy:
        """Create default file access policy."""
        return FileAccessPolicy(
            allowed_extensions=self.SAFE_EXTENSIONS.copy(),
            blocked_extensions=self.DANGEROUS_EXTENSIONS.copy(),
            allowed_paths={str(self.base_dir)},
            blocked_paths={'/etc', '/var', '/sys', '/proc', '/dev', '/root', '/boot'},
            max_file_size=100 * 1024 * 1024,  # 100MB
            max_total_size=1024 * 1024 * 1024,  # 1GB
            allow_executable=False,
            allow_symlinks=False,
            require_safe_names=True
        )
    
    def _setup_base_directory(self):
        """Set up base directory with secure permissions."""
        try:
            self.base_dir.mkdir(parents=True, exist_ok=True)
            
            # Set secure permissions (owner read/write/execute only)
            if hasattr(os, 'chmod'):
                os.chmod(self.base_dir, stat.S_IRWXU)
            
            logger.info(f"Secure file handler initialized with base dir: {self.base_dir}")
            
        except Exception as e:
            raise SecureFileError(f"Failed to setup base directory: {e}")
    
    def validate_path(self, path: Union[str, Path]) -> Path:
        """
        Validate and normalize file path.
        
        Args:
            path: Path to validate
            
        Returns:
            Validated and normalized path
            
        Raises:
            SecureFileError: If path validation fails
        """
        path = Path(path).resolve()
        
        # Check for path traversal
        try:
            # Ensure path is within allowed directories
            if self.policy.allowed_paths:
                allowed = any(
                    str(path).startswith(str(Path(allowed_path).resolve()))
                    for allowed_path in self.policy.allowed_paths
                )
                if not allowed:
                    raise SecureFileError(f"Path not in allowed directories: {path}")
            
            # Check blocked paths
            if self.policy.blocked_paths:
                for blocked_path in self.policy.blocked_paths:
                    if str(path).startswith(str(Path(blocked_path).resolve())):
                        raise SecureFileError(f"Path in blocked directory: {path}")
            
        except Exception as e:
            raise SecureFileError(f"Path validation failed: {e}")
        
        # Validate filename
        if self.policy.require_safe_names:
            self._validate_filename(path.name)
        
        # Validate file extension
        self._validate_extension(path.suffix.lower())
        
        return path
    
    def _validate_filename(self, filename: str):
        """Validate filename for security."""
        if not filename or filename in {'.', '..'}:
            raise SecureFileError(f"Invalid filename: {filename}")
        
        # Check for dangerous characters
        dangerous_chars = {'<', '>', ':', '"', '|', '?', '*', '\0'}
        if any(char in filename for char in dangerous_chars):
            raise SecureFileError(f"Filename contains dangerous characters: {filename}")
        
        # Check for control characters
        if any(ord(char) < 32 for char in filename):
            raise SecureFileError(f"Filename contains control characters: {filename}")
        
        # Check length
        if len(filename) > 255:
            raise SecureFileError(f"Filename too long: {len(filename)} > 255")
    
    def _validate_extension(self, extension: str):
        """Validate file extension."""
        if self.policy.blocked_extensions and extension in self.policy.blocked_extensions:
            raise SecureFileError(f"Blocked file extension: {extension}")
        
        if self.policy.allowed_extensions and extension not in self.policy.allowed_extensions:
            raise SecureFileError(f"File extension not allowed: {extension}")
    
    def _validate_file_size(self, file_path: Path):
        """Validate file size against policy."""
        if not file_path.exists():
            return
        
        file_size = file_path.stat().st_size
        
        if file_size > self.policy.max_file_size:
            raise SecureFileError(
                f"File too large: {file_size} > {self.policy.max_file_size}"
            )
    
    def _validate_file_permissions(self, file_path: Path):
        """Validate file permissions."""
        if not file_path.exists():
            return
        
        file_stat = file_path.stat()
        
        # Check if file is executable
        if not self.policy.allow_executable:
            if file_stat.st_mode & (stat.S_IXUSR | stat.S_IXGRP | stat.S_IXOTH):
                raise SecureFileError(f"Executable files not allowed: {file_path}")
        
        # Check if file is a symlink
        if not self.policy.allow_symlinks and file_path.is_symlink():
            raise SecureFileError(f"Symbolic links not allowed: {file_path}")
    
    def _log_access(self, operation: str, path: Path, success: bool, details: Optional[Dict] = None):
        """Log file access operation."""
        log_entry = {
            'timestamp': time.time(),
            'operation': operation,
            'path': str(path),
            'success': success,
            'details': details or {}
        }
        
        self.access_log.append(log_entry)
        
        # Keep only last 1000 entries
        if len(self.access_log) > 1000:
            self.access_log = self.access_log[-1000:]
    
    @contextmanager
    def create_temp_file(self, 
                        suffix: str = '.tmp',
                        prefix: str = 'secure_',
                        content: Optional[Union[str, bytes]] = None,
                        text_mode: bool = True) -> Path:
        """
        Create a secure temporary file.
        
        Args:
            suffix: File suffix
            prefix: File prefix
            content: Initial file content
            text_mode: Whether to open in text mode
            
        Yields:
            Path to temporary file
        """
        # Validate suffix
        self._validate_extension(suffix)
        
        temp_file = None
        temp_path = None
        
        try:
            # Create temporary file in secure directory
            temp_file = tempfile.NamedTemporaryFile(
                suffix=suffix,
                prefix=prefix,
                dir=self.base_dir,
                delete=False,
                mode='w' if text_mode else 'wb'
            )
            
            temp_path = Path(temp_file.name)
            
            # Write initial content if provided
            if content is not None:
                temp_file.write(content)
                temp_file.flush()
            
            temp_file.close()
            
            # Set secure permissions
            if hasattr(os, 'chmod'):
                os.chmod(temp_path, stat.S_IRUSR | stat.S_IWUSR)
            
            # Track temporary file
            temp_id = hashlib.md5(str(temp_path).encode()).hexdigest()
            with self._lock:
                self.temp_files[temp_id] = temp_path
            
            self._log_access('create_temp_file', temp_path, True)
            logger.debug(f"Created temporary file: {temp_path}")
            
            yield temp_path
            
        except Exception as e:
            self._log_access('create_temp_file', temp_path or Path('unknown'), False, {'error': str(e)})
            raise SecureFileError(f"Failed to create temporary file: {e}")
        
        finally:
            # Cleanup temporary file
            if temp_path and temp_path.exists():
                try:
                    temp_path.unlink()
                    
                    # Remove from tracking
                    temp_id = hashlib.md5(str(temp_path).encode()).hexdigest()
                    with self._lock:
                        self.temp_files.pop(temp_id, None)
                    
                    logger.debug(f"Cleaned up temporary file: {temp_path}")
                    
                except Exception as e:
                    logger.warning(f"Failed to cleanup temporary file {temp_path}: {e}")
    
    @contextmanager
    def create_temp_dir(self, 
                       suffix: str = '',
                       prefix: str = 'secure_dir_') -> Path:
        """
        Create a secure temporary directory.
        
        Args:
            suffix: Directory suffix
            prefix: Directory prefix
            
        Yields:
            Path to temporary directory
        """
        temp_dir = None
        
        try:
            # Create temporary directory in secure location
            temp_dir = Path(tempfile.mkdtemp(
                suffix=suffix,
                prefix=prefix,
                dir=self.base_dir
            ))
            
            # Set secure permissions
            if hasattr(os, 'chmod'):
                os.chmod(temp_dir, stat.S_IRWXU)
            
            # Track temporary directory
            temp_id = hashlib.md5(str(temp_dir).encode()).hexdigest()
            with self._lock:
                self.temp_dirs[temp_id] = temp_dir
            
            self._log_access('create_temp_dir', temp_dir, True)
            logger.debug(f"Created temporary directory: {temp_dir}")
            
            yield temp_dir
            
        except Exception as e:
            self._log_access('create_temp_dir', temp_dir or Path('unknown'), False, {'error': str(e)})
            raise SecureFileError(f"Failed to create temporary directory: {e}")
        
        finally:
            # Cleanup temporary directory
            if temp_dir and temp_dir.exists():
                try:
                    shutil.rmtree(temp_dir)
                    
                    # Remove from tracking
                    temp_id = hashlib.md5(str(temp_dir).encode()).hexdigest()
                    with self._lock:
                        self.temp_dirs.pop(temp_id, None)
                    
                    logger.debug(f"Cleaned up temporary directory: {temp_dir}")
                    
                except Exception as e:
                    logger.warning(f"Failed to cleanup temporary directory {temp_dir}: {e}")
    
    def safe_read_file(self, file_path: Union[str, Path], 
                      text_mode: bool = True,
                      encoding: str = 'utf-8') -> Union[str, bytes]:
        """
        Safely read file content.
        
        Args:
            file_path: Path to file
            text_mode: Whether to read in text mode
            encoding: Text encoding (for text mode)
            
        Returns:
            File content
        """
        validated_path = self.validate_path(file_path)
        
        try:
            # Validate file
            self._validate_file_size(validated_path)
            self._validate_file_permissions(validated_path)
            
            # Read file
            if text_mode:
                content = validated_path.read_text(encoding=encoding)
            else:
                content = validated_path.read_bytes()
            
            self._log_access('read_file', validated_path, True, {
                'size': len(content),
                'text_mode': text_mode
            })
            
            return content
            
        except Exception as e:
            self._log_access('read_file', validated_path, False, {'error': str(e)})
            raise SecureFileError(f"Failed to read file {validated_path}: {e}")
    
    def safe_write_file(self, file_path: Union[str, Path], 
                       content: Union[str, bytes],
                       text_mode: bool = True,
                       encoding: str = 'utf-8',
                       create_dirs: bool = True) -> Path:
        """
        Safely write file content.
        
        Args:
            file_path: Path to file
            content: Content to write
            text_mode: Whether to write in text mode
            encoding: Text encoding (for text mode)
            create_dirs: Whether to create parent directories
            
        Returns:
            Path to written file
        """
        validated_path = self.validate_path(file_path)
        
        try:
            # Create parent directories if needed
            if create_dirs:
                validated_path.parent.mkdir(parents=True, exist_ok=True)
            
            # Check content size
            content_size = len(content.encode() if isinstance(content, str) else content)
            if content_size > self.policy.max_file_size:
                raise SecureFileError(f"Content too large: {content_size} > {self.policy.max_file_size}")
            
            # Write file
            if text_mode:
                validated_path.write_text(content, encoding=encoding)
            else:
                validated_path.write_bytes(content)
            
            # Set secure permissions
            if hasattr(os, 'chmod'):
                os.chmod(validated_path, stat.S_IRUSR | stat.S_IWUSR)
            
            self._log_access('write_file', validated_path, True, {
                'size': content_size,
                'text_mode': text_mode
            })
            
            return validated_path
            
        except Exception as e:
            self._log_access('write_file', validated_path, False, {'error': str(e)})
            raise SecureFileError(f"Failed to write file {validated_path}: {e}")
    
    def safe_copy_file(self, src_path: Union[str, Path], 
                      dst_path: Union[str, Path],
                      preserve_metadata: bool = False) -> Path:
        """
        Safely copy file.
        
        Args:
            src_path: Source file path
            dst_path: Destination file path
            preserve_metadata: Whether to preserve file metadata
            
        Returns:
            Path to copied file
        """
        validated_src = self.validate_path(src_path)
        validated_dst = self.validate_path(dst_path)
        
        try:
            # Validate source file
            self._validate_file_size(validated_src)
            self._validate_file_permissions(validated_src)
            
            # Create destination directory if needed
            validated_dst.parent.mkdir(parents=True, exist_ok=True)
            
            # Copy file
            if preserve_metadata:
                shutil.copy2(validated_src, validated_dst)
            else:
                shutil.copy(validated_src, validated_dst)
            
            # Set secure permissions on destination
            if hasattr(os, 'chmod'):
                os.chmod(validated_dst, stat.S_IRUSR | stat.S_IWUSR)
            
            self._log_access('copy_file', validated_dst, True, {
                'source': str(validated_src),
                'preserve_metadata': preserve_metadata
            })
            
            return validated_dst
            
        except Exception as e:
            self._log_access('copy_file', validated_dst, False, {
                'source': str(validated_src),
                'error': str(e)
            })
            raise SecureFileError(f"Failed to copy file {validated_src} to {validated_dst}: {e}")
    
    def safe_delete_file(self, file_path: Union[str, Path]) -> bool:
        """
        Safely delete file.
        
        Args:
            file_path: Path to file to delete
            
        Returns:
            True if file was deleted
        """
        validated_path = self.validate_path(file_path)
        
        try:
            if validated_path.exists():
                validated_path.unlink()
                deleted = True
            else:
                deleted = False
            
            self._log_access('delete_file', validated_path, True, {'existed': deleted})
            return deleted
            
        except Exception as e:
            self._log_access('delete_file', validated_path, False, {'error': str(e)})
            raise SecureFileError(f"Failed to delete file {validated_path}: {e}")
    
    def cleanup_temp_files(self):
        """Clean up all tracked temporary files and directories."""
        with self._lock:
            # Clean up temporary files
            for temp_id, temp_path in list(self.temp_files.items()):
                try:
                    if temp_path.exists():
                        temp_path.unlink()
                    del self.temp_files[temp_id]
                except Exception as e:
                    logger.warning(f"Failed to cleanup temp file {temp_path}: {e}")
            
            # Clean up temporary directories
            for temp_id, temp_dir in list(self.temp_dirs.items()):
                try:
                    if temp_dir.exists():
                        shutil.rmtree(temp_dir)
                    del self.temp_dirs[temp_id]
                except Exception as e:
                    logger.warning(f"Failed to cleanup temp directory {temp_dir}: {e}")
        
        logger.info("Cleaned up all temporary files and directories")
    
    def get_access_log(self, limit: int = 100) -> List[Dict]:
        """Get recent file access log entries."""
        return self.access_log[-limit:]
    
    def get_temp_file_count(self) -> int:
        """Get count of tracked temporary files."""
        with self._lock:
            return len(self.temp_files) + len(self.temp_dirs)
    
    def calculate_checksum(self, file_path: Union[str, Path], 
                          algorithm: str = 'sha256') -> str:
        """
        Calculate file checksum.
        
        Args:
            file_path: Path to file
            algorithm: Hash algorithm (md5, sha1, sha256, etc.)
            
        Returns:
            Hexadecimal checksum string
        """
        validated_path = self.validate_path(file_path)
        
        try:
            hash_obj = hashlib.new(algorithm)
            
            with open(validated_path, 'rb') as f:
                for chunk in iter(lambda: f.read(4096), b""):
                    hash_obj.update(chunk)
            
            checksum = hash_obj.hexdigest()
            
            self._log_access('calculate_checksum', validated_path, True, {
                'algorithm': algorithm,
                'checksum': checksum
            })
            
            return checksum
            
        except Exception as e:
            self._log_access('calculate_checksum', validated_path, False, {'error': str(e)})
            raise SecureFileError(f"Failed to calculate checksum for {validated_path}: {e}")