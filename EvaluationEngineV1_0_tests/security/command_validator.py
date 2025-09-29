"""
Command Validator

Provides command validation and sanitization to prevent
malicious command execution and ensure safe operations.
"""

import re
import os
import shlex
import logging
from typing import List, Dict, Set, Optional, Union, Tuple
from pathlib import Path
from dataclasses import dataclass

logger = logging.getLogger(__name__)


@dataclass
class CommandPolicy:
    """Command execution policy configuration."""
    allowed_commands: Set[str]
    blocked_commands: Set[str]
    allowed_paths: Set[str]
    blocked_paths: Set[str]
    allow_shell_operators: bool = False
    allow_environment_vars: bool = True
    allow_file_redirection: bool = False
    allow_pipe_operations: bool = False
    max_command_length: int = 1000
    max_arguments: int = 50


class CommandValidationError(Exception):
    """Raised when command validation fails."""
    pass


class CommandValidator:
    """
    Validates and sanitizes commands before execution to prevent
    security vulnerabilities and malicious operations.
    
    Features:
    - Command whitelist/blacklist validation
    - Path restriction enforcement
    - Shell injection prevention
    - Argument validation and sanitization
    - Environment variable validation
    - File operation restrictions
    """
    
    # Default dangerous commands
    DEFAULT_BLOCKED_COMMANDS = {
        # System modification
        'rm', 'rmdir', 'del', 'erase', 'format', 'fdisk', 'mkfs',
        'dd', 'shred', 'wipe', 'chmod', 'chown', 'chgrp',
        
        # Process control
        'kill', 'killall', 'pkill', 'sudo', 'su', 'doas',
        
        # Network operations
        'wget', 'curl', 'nc', 'netcat', 'telnet', 'ssh', 'scp', 'rsync',
        
        # System information
        'ps', 'top', 'htop', 'lsof', 'netstat', 'ss',
        
        # File system operations
        'mount', 'umount', 'fsck', 'tune2fs', 'resize2fs',
        
        # Archive operations (potentially dangerous)
        'tar', 'zip', 'unzip', 'gzip', 'gunzip',
        
        # Compiler/interpreter access
        'gcc', 'g++', 'clang', 'make', 'cmake', 'ninja',
        
        # Package managers
        'apt', 'yum', 'dnf', 'pacman', 'brew', 'pip', 'npm', 'yarn'
    }
    
    # Default safe commands
    DEFAULT_ALLOWED_COMMANDS = {
        # Basic file operations
        'ls', 'dir', 'cat', 'type', 'head', 'tail', 'less', 'more',
        'find', 'grep', 'awk', 'sed', 'sort', 'uniq', 'wc',
        
        # Text processing
        'echo', 'printf', 'tr', 'cut', 'paste', 'join',
        
        # Python and testing
        'python', 'python3', 'pytest', 'coverage',
        
        # Version control (read-only)
        'git',
        
        # Basic utilities
        'date', 'whoami', 'pwd', 'which', 'whereis', 'file'
    }
    
    # Shell operators and special characters
    SHELL_OPERATORS = {
        '|', '||', '&', '&&', ';', '(', ')', '{', '}',
        '>', '>>', '<', '<<', '`', '$', '*', '?', '[', ']'
    }
    
    def __init__(self, policy: Optional[CommandPolicy] = None):
        """
        Initialize command validator.
        
        Args:
            policy: Command execution policy (uses default if None)
        """
        self.policy = policy or self._create_default_policy()
        
        # Compile regex patterns for efficiency
        self._compile_patterns()
    
    def _create_default_policy(self) -> CommandPolicy:
        """Create default command policy."""
        return CommandPolicy(
            allowed_commands=self.DEFAULT_ALLOWED_COMMANDS.copy(),
            blocked_commands=self.DEFAULT_BLOCKED_COMMANDS.copy(),
            allowed_paths={'/usr/bin', '/bin', '/usr/local/bin', '.'},
            blocked_paths={'/etc', '/var', '/sys', '/proc', '/dev', '/root'},
            allow_shell_operators=False,
            allow_environment_vars=True,
            allow_file_redirection=False,
            allow_pipe_operations=False,
            max_command_length=1000,
            max_arguments=50
        )
    
    def _compile_patterns(self):
        """Compile regex patterns for validation."""
        # Environment variable pattern
        self.env_var_pattern = re.compile(r'\$\{?([A-Za-z_][A-Za-z0-9_]*)\}?')
        
        # File redirection pattern
        self.redirection_pattern = re.compile(r'[<>]+')
        
        # Command substitution pattern
        self.command_sub_pattern = re.compile(r'`[^`]*`|\$\([^)]*\)')
        
        # Suspicious character pattern
        self.suspicious_pattern = re.compile(r'[;&|`$(){}[\]*?<>]')
    
    def validate_command(self, command: Union[str, List[str]]) -> Tuple[List[str], Dict[str, str]]:
        """
        Validate and sanitize a command.
        
        Args:
            command: Command to validate (string or list)
            
        Returns:
            Tuple of (sanitized_command_list, environment_vars)
            
        Raises:
            CommandValidationError: If command validation fails
        """
        # Convert to list if string
        if isinstance(command, str):
            try:
                command_list = shlex.split(command)
            except ValueError as e:
                raise CommandValidationError(f"Invalid command syntax: {e}")
        else:
            command_list = command.copy()
        
        if not command_list:
            raise CommandValidationError("Empty command not allowed")
        
        # Basic validation
        self._validate_command_length(command_list)
        self._validate_argument_count(command_list)
        
        # Extract and validate base command
        base_command = self._extract_base_command(command_list[0])
        self._validate_base_command(base_command)
        
        # Validate command path
        self._validate_command_path(command_list[0])
        
        # Validate arguments
        env_vars = {}
        sanitized_args = []
        
        for i, arg in enumerate(command_list):
            if i == 0:
                sanitized_args.append(arg)  # Keep original command
                continue
            
            # Validate and sanitize argument
            sanitized_arg, arg_env_vars = self._validate_argument(arg)
            sanitized_args.append(sanitized_arg)
            env_vars.update(arg_env_vars)
        
        # Final security checks
        self._perform_security_checks(sanitized_args)
        
        logger.debug(f"Command validated successfully: {sanitized_args}")
        return sanitized_args, env_vars
    
    def _validate_command_length(self, command_list: List[str]):
        """Validate total command length."""
        total_length = sum(len(arg) for arg in command_list)
        if total_length > self.policy.max_command_length:
            raise CommandValidationError(
                f"Command too long: {total_length} > {self.policy.max_command_length}"
            )
    
    def _validate_argument_count(self, command_list: List[str]):
        """Validate number of arguments."""
        if len(command_list) > self.policy.max_arguments:
            raise CommandValidationError(
                f"Too many arguments: {len(command_list)} > {self.policy.max_arguments}"
            )
    
    def _extract_base_command(self, command: str) -> str:
        """Extract base command name from path."""
        return Path(command).name.lower()
    
    def _validate_base_command(self, base_command: str):
        """Validate base command against policy."""
        # Check blocked commands first
        if base_command in self.policy.blocked_commands:
            raise CommandValidationError(f"Blocked command: {base_command}")
        
        # Check allowed commands if whitelist is defined
        if self.policy.allowed_commands and base_command not in self.policy.allowed_commands:
            raise CommandValidationError(f"Command not in allowed list: {base_command}")
    
    def _validate_command_path(self, command: str):
        """Validate command path against policy."""
        command_path = Path(command)
        
        # If absolute path, check against allowed/blocked paths
        if command_path.is_absolute():
            command_dir = str(command_path.parent)
            
            # Check blocked paths
            for blocked_path in self.policy.blocked_paths:
                if command_dir.startswith(blocked_path):
                    raise CommandValidationError(f"Command in blocked path: {command_dir}")
            
            # Check allowed paths if defined
            if self.policy.allowed_paths:
                allowed = any(command_dir.startswith(allowed_path) 
                            for allowed_path in self.policy.allowed_paths)
                if not allowed:
                    raise CommandValidationError(f"Command not in allowed path: {command_dir}")
    
    def _validate_argument(self, arg: str) -> Tuple[str, Dict[str, str]]:
        """
        Validate and sanitize a command argument.
        
        Returns:
            Tuple of (sanitized_argument, extracted_env_vars)
        """
        env_vars = {}
        sanitized_arg = arg
        
        # Check for shell operators
        if not self.policy.allow_shell_operators:
            for operator in self.SHELL_OPERATORS:
                if operator in arg:
                    raise CommandValidationError(f"Shell operator not allowed: {operator}")
        
        # Check for file redirection
        if not self.policy.allow_file_redirection:
            if self.redirection_pattern.search(arg):
                raise CommandValidationError(f"File redirection not allowed: {arg}")
        
        # Check for command substitution
        if self.command_sub_pattern.search(arg):
            raise CommandValidationError(f"Command substitution not allowed: {arg}")
        
        # Handle environment variables
        if self.policy.allow_environment_vars:
            env_matches = self.env_var_pattern.findall(arg)
            for var_name in env_matches:
                # Validate environment variable name
                if not self._is_safe_env_var(var_name):
                    raise CommandValidationError(f"Unsafe environment variable: {var_name}")
                
                # Get environment variable value
                env_value = os.environ.get(var_name, '')
                env_vars[var_name] = env_value
                
                # Replace in argument (optional, for logging)
                # sanitized_arg = sanitized_arg.replace(f'${var_name}', env_value)
        else:
            # Check for environment variables when not allowed
            if self.env_var_pattern.search(arg):
                raise CommandValidationError(f"Environment variables not allowed: {arg}")
        
        # Check for suspicious patterns
        if self.suspicious_pattern.search(arg):
            # Allow some patterns based on policy
            if not (self.policy.allow_shell_operators or 
                   self.policy.allow_file_redirection or 
                   self.policy.allow_pipe_operations):
                raise CommandValidationError(f"Suspicious characters in argument: {arg}")
        
        return sanitized_arg, env_vars
    
    def _is_safe_env_var(self, var_name: str) -> bool:
        """Check if environment variable is safe to use."""
        # Block dangerous environment variables
        dangerous_vars = {
            'LD_PRELOAD', 'LD_LIBRARY_PATH', 'DYLD_INSERT_LIBRARIES',
            'PATH', 'PYTHONPATH', 'PERL5LIB', 'RUBYLIB',
            'IFS', 'PS1', 'PS2', 'PS4'
        }
        
        return var_name.upper() not in dangerous_vars
    
    def _perform_security_checks(self, command_list: List[str]):
        """Perform final security checks on the command."""
        full_command = ' '.join(command_list)
        
        # Check for common injection patterns
        injection_patterns = [
            r';\s*rm\s+',  # Command chaining with rm
            r'&&\s*rm\s+',  # Conditional execution with rm
            r'\|\s*sh\s*',  # Pipe to shell
            r'`.*`',  # Command substitution
            r'\$\(.*\)',  # Command substitution
            r'>\s*/dev/',  # Writing to device files
            r'<\s*/dev/',  # Reading from device files
        ]
        
        for pattern in injection_patterns:
            if re.search(pattern, full_command, re.IGNORECASE):
                raise CommandValidationError(f"Potential injection detected: {pattern}")
    
    def is_command_allowed(self, command: str) -> bool:
        """Check if a command is allowed without full validation."""
        try:
            base_command = self._extract_base_command(command)
            
            # Check blocked commands
            if base_command in self.policy.blocked_commands:
                return False
            
            # Check allowed commands if whitelist exists
            if self.policy.allowed_commands and base_command not in self.policy.allowed_commands:
                return False
            
            return True
            
        except Exception:
            return False
    
    def get_allowed_commands(self) -> Set[str]:
        """Get set of allowed commands."""
        return self.policy.allowed_commands.copy()
    
    def get_blocked_commands(self) -> Set[str]:
        """Get set of blocked commands."""
        return self.policy.blocked_commands.copy()
    
    def add_allowed_command(self, command: str):
        """Add a command to the allowed list."""
        self.policy.allowed_commands.add(command.lower())
        logger.info(f"Added allowed command: {command}")
    
    def add_blocked_command(self, command: str):
        """Add a command to the blocked list."""
        self.policy.blocked_commands.add(command.lower())
        logger.info(f"Added blocked command: {command}")
    
    def remove_allowed_command(self, command: str):
        """Remove a command from the allowed list."""
        self.policy.allowed_commands.discard(command.lower())
        logger.info(f"Removed allowed command: {command}")
    
    def remove_blocked_command(self, command: str):
        """Remove a command from the blocked list."""
        self.policy.blocked_commands.discard(command.lower())
        logger.info(f"Removed blocked command: {command}")
    
    def update_policy(self, **kwargs):
        """Update command policy settings."""
        for key, value in kwargs.items():
            if hasattr(self.policy, key):
                setattr(self.policy, key, value)
                logger.info(f"Updated policy {key}: {value}")
            else:
                logger.warning(f"Unknown policy setting: {key}")
    
    def get_policy_summary(self) -> Dict[str, any]:
        """Get summary of current policy settings."""
        return {
            'allowed_commands_count': len(self.policy.allowed_commands),
            'blocked_commands_count': len(self.policy.blocked_commands),
            'allowed_paths_count': len(self.policy.allowed_paths),
            'blocked_paths_count': len(self.policy.blocked_paths),
            'allow_shell_operators': self.policy.allow_shell_operators,
            'allow_environment_vars': self.policy.allow_environment_vars,
            'allow_file_redirection': self.policy.allow_file_redirection,
            'allow_pipe_operations': self.policy.allow_pipe_operations,
            'max_command_length': self.policy.max_command_length,
            'max_arguments': self.policy.max_arguments
        }