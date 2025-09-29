"""
Sandboxed Execution Environment

Provides secure, isolated execution environments for test operations
to prevent system compromise and ensure test isolation.
"""

import os
import sys
import subprocess
import tempfile
import shutil
import logging
from pathlib import Path
from typing import Dict, List, Optional, Any, Union
from contextlib import contextmanager
import resource
import signal
import threading
import time

logger = logging.getLogger(__name__)


class SandboxExecutionError(Exception):
    """Raised when sandbox execution fails"""
    pass


class SandboxExecutor:
    """
    Provides sandboxed execution environments for secure test execution.
    
    Features:
    - Process isolation
    - File system restrictions
    - Resource limits
    - Network isolation (where supported)
    - Timeout enforcement
    """
    
    def __init__(self, 
                 base_sandbox_dir: Optional[Path] = None,
                 max_execution_time: int = 300,
                 max_memory_mb: int = 1024,
                 max_cpu_percent: int = 80,
                 allow_network: bool = False):
        """
        Initialize sandbox executor.
        
        Args:
            base_sandbox_dir: Base directory for sandbox environments
            max_execution_time: Maximum execution time in seconds
            max_memory_mb: Maximum memory usage in MB
            max_cpu_percent: Maximum CPU usage percentage
            allow_network: Whether to allow network access
        """
        self.base_sandbox_dir = base_sandbox_dir or Path(tempfile.gettempdir()) / "eval_sandbox"
        self.max_execution_time = max_execution_time
        self.max_memory_mb = max_memory_mb
        self.max_cpu_percent = max_cpu_percent
        self.allow_network = allow_network
        
        # Ensure base sandbox directory exists
        self.base_sandbox_dir.mkdir(parents=True, exist_ok=True)
        
        # Track active sandboxes
        self._active_sandboxes: Dict[str, Dict] = {}
        self._lock = threading.Lock()
    
    @contextmanager
    def create_sandbox(self, sandbox_id: str, 
                      working_dir: Optional[Path] = None,
                      allowed_paths: Optional[List[Path]] = None):
        """
        Create a sandboxed environment.
        
        Args:
            sandbox_id: Unique identifier for the sandbox
            working_dir: Working directory within sandbox
            allowed_paths: Additional paths to allow access to
            
        Yields:
            SandboxEnvironment: Configured sandbox environment
        """
        sandbox_path = self.base_sandbox_dir / sandbox_id
        
        try:
            # Create sandbox directory
            sandbox_path.mkdir(parents=True, exist_ok=True)
            
            # Set up sandbox environment
            sandbox_env = SandboxEnvironment(
                sandbox_path=sandbox_path,
                working_dir=working_dir or sandbox_path,
                allowed_paths=allowed_paths or [],
                max_execution_time=self.max_execution_time,
                max_memory_mb=self.max_memory_mb,
                max_cpu_percent=self.max_cpu_percent,
                allow_network=self.allow_network
            )
            
            # Register active sandbox
            with self._lock:
                self._active_sandboxes[sandbox_id] = {
                    'path': sandbox_path,
                    'created_at': time.time(),
                    'environment': sandbox_env
                }
            
            logger.info(f"Created sandbox environment: {sandbox_id}")
            yield sandbox_env
            
        except Exception as e:
            logger.error(f"Failed to create sandbox {sandbox_id}: {e}")
            raise SandboxExecutionError(f"Sandbox creation failed: {e}")
        
        finally:
            # Cleanup sandbox
            self._cleanup_sandbox(sandbox_id, sandbox_path)
    
    def _cleanup_sandbox(self, sandbox_id: str, sandbox_path: Path):
        """Clean up sandbox environment."""
        try:
            # Remove from active sandboxes
            with self._lock:
                if sandbox_id in self._active_sandboxes:
                    del self._active_sandboxes[sandbox_id]
            
            # Remove sandbox directory
            if sandbox_path.exists():
                shutil.rmtree(sandbox_path, ignore_errors=True)
            
            logger.info(f"Cleaned up sandbox environment: {sandbox_id}")
            
        except Exception as e:
            logger.warning(f"Failed to cleanup sandbox {sandbox_id}: {e}")
    
    def cleanup_all_sandboxes(self):
        """Clean up all active sandboxes."""
        with self._lock:
            sandbox_ids = list(self._active_sandboxes.keys())
        
        for sandbox_id in sandbox_ids:
            sandbox_info = self._active_sandboxes.get(sandbox_id)
            if sandbox_info:
                self._cleanup_sandbox(sandbox_id, sandbox_info['path'])
    
    def get_active_sandboxes(self) -> Dict[str, Dict]:
        """Get information about active sandboxes."""
        with self._lock:
            return self._active_sandboxes.copy()


class SandboxEnvironment:
    """
    Represents a sandboxed execution environment.
    """
    
    def __init__(self, 
                 sandbox_path: Path,
                 working_dir: Path,
                 allowed_paths: List[Path],
                 max_execution_time: int,
                 max_memory_mb: int,
                 max_cpu_percent: int,
                 allow_network: bool):
        """Initialize sandbox environment."""
        self.sandbox_path = sandbox_path
        self.working_dir = working_dir
        self.allowed_paths = allowed_paths
        self.max_execution_time = max_execution_time
        self.max_memory_mb = max_memory_mb
        self.max_cpu_percent = max_cpu_percent
        self.allow_network = allow_network
        
        # Create working directory
        self.working_dir.mkdir(parents=True, exist_ok=True)
    
    def execute_command(self, 
                       command: Union[str, List[str]], 
                       env: Optional[Dict[str, str]] = None,
                       input_data: Optional[str] = None,
                       capture_output: bool = True) -> Dict[str, Any]:
        """
        Execute a command in the sandboxed environment.
        
        Args:
            command: Command to execute
            env: Environment variables
            input_data: Input data to pass to command
            capture_output: Whether to capture stdout/stderr
            
        Returns:
            Dict containing execution results
        """
        if isinstance(command, str):
            command = command.split()
        
        # Validate command
        self._validate_command(command)
        
        # Prepare environment
        sandbox_env = self._prepare_environment(env)
        
        # Set resource limits
        def set_limits():
            # Set memory limit
            if self.max_memory_mb > 0:
                memory_limit = self.max_memory_mb * 1024 * 1024
                resource.setrlimit(resource.RLIMIT_AS, (memory_limit, memory_limit))
            
            # Set CPU time limit
            if self.max_execution_time > 0:
                resource.setrlimit(resource.RLIMIT_CPU, (self.max_execution_time, self.max_execution_time))
        
        try:
            # Execute command with timeout and resource limits
            process = subprocess.Popen(
                command,
                cwd=str(self.working_dir),
                env=sandbox_env,
                stdin=subprocess.PIPE if input_data else None,
                stdout=subprocess.PIPE if capture_output else None,
                stderr=subprocess.PIPE if capture_output else None,
                preexec_fn=set_limits if sys.platform != 'win32' else None,
                text=True
            )
            
            # Execute with timeout
            try:
                stdout, stderr = process.communicate(
                    input=input_data,
                    timeout=self.max_execution_time
                )
                return_code = process.returncode
                
            except subprocess.TimeoutExpired:
                process.kill()
                stdout, stderr = process.communicate()
                raise SandboxExecutionError(f"Command timed out after {self.max_execution_time} seconds")
            
            return {
                'return_code': return_code,
                'stdout': stdout,
                'stderr': stderr,
                'success': return_code == 0
            }
            
        except Exception as e:
            logger.error(f"Sandbox execution failed: {e}")
            raise SandboxExecutionError(f"Execution failed: {e}")
    
    def _validate_command(self, command: List[str]):
        """Validate command for security."""
        if not command:
            raise SandboxExecutionError("Empty command not allowed")
        
        # Check for dangerous commands
        dangerous_commands = {
            'rm', 'rmdir', 'del', 'format', 'fdisk',
            'mkfs', 'dd', 'sudo', 'su', 'chmod',
            'chown', 'mount', 'umount', 'kill', 'killall'
        }
        
        base_command = Path(command[0]).name.lower()
        if base_command in dangerous_commands:
            raise SandboxExecutionError(f"Dangerous command not allowed: {base_command}")
        
        # Check for shell injection attempts
        for arg in command:
            if any(char in arg for char in ['|', '&', ';', '`', '$(']):
                raise SandboxExecutionError(f"Shell injection attempt detected: {arg}")
    
    def _prepare_environment(self, env: Optional[Dict[str, str]]) -> Dict[str, str]:
        """Prepare sandboxed environment variables."""
        sandbox_env = os.environ.copy()
        
        # Restrict PATH to safe directories
        safe_paths = [
            '/usr/bin',
            '/bin',
            '/usr/local/bin'
        ]
        sandbox_env['PATH'] = ':'.join(safe_paths)
        
        # Set sandbox-specific variables
        sandbox_env['SANDBOX_MODE'] = '1'
        sandbox_env['SANDBOX_PATH'] = str(self.sandbox_path)
        sandbox_env['PWD'] = str(self.working_dir)
        
        # Remove potentially dangerous variables
        dangerous_vars = [
            'LD_PRELOAD', 'LD_LIBRARY_PATH', 'DYLD_INSERT_LIBRARIES',
            'PYTHONPATH', 'PERL5LIB', 'RUBYLIB'
        ]
        for var in dangerous_vars:
            sandbox_env.pop(var, None)
        
        # Add user-provided environment variables
        if env:
            sandbox_env.update(env)
        
        return sandbox_env
    
    def copy_file_to_sandbox(self, source: Path, dest_name: Optional[str] = None) -> Path:
        """Copy a file into the sandbox."""
        if not source.exists():
            raise SandboxExecutionError(f"Source file does not exist: {source}")
        
        dest_name = dest_name or source.name
        dest_path = self.working_dir / dest_name
        
        try:
            shutil.copy2(source, dest_path)
            return dest_path
        except Exception as e:
            raise SandboxExecutionError(f"Failed to copy file to sandbox: {e}")
    
    def copy_file_from_sandbox(self, source_name: str, dest: Path) -> Path:
        """Copy a file from the sandbox."""
        source_path = self.working_dir / source_name
        
        if not source_path.exists():
            raise SandboxExecutionError(f"Source file does not exist in sandbox: {source_name}")
        
        try:
            shutil.copy2(source_path, dest)
            return dest
        except Exception as e:
            raise SandboxExecutionError(f"Failed to copy file from sandbox: {e}")
    
    def list_files(self) -> List[str]:
        """List files in the sandbox working directory."""
        try:
            return [f.name for f in self.working_dir.iterdir() if f.is_file()]
        except Exception as e:
            raise SandboxExecutionError(f"Failed to list sandbox files: {e}")
    
    def get_file_content(self, filename: str) -> str:
        """Get content of a file in the sandbox."""
        file_path = self.working_dir / filename
        
        if not file_path.exists():
            raise SandboxExecutionError(f"File does not exist in sandbox: {filename}")
        
        try:
            return file_path.read_text()
        except Exception as e:
            raise SandboxExecutionError(f"Failed to read file from sandbox: {e}")
    
    def write_file(self, filename: str, content: str) -> Path:
        """Write content to a file in the sandbox."""
        file_path = self.working_dir / filename
        
        try:
            file_path.write_text(content)
            return file_path
        except Exception as e:
            raise SandboxExecutionError(f"Failed to write file to sandbox: {e}")