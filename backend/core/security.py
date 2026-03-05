import re
import os
import shlex
from typing import List, Dict, Any, Tuple
import logging

logger = logging.getLogger("TrafficController.Security")

class SecurityException(Exception):
    pass

class SafetyValidator:
    """Validates commands and actions to ensure they obey strict safety boundaries."""
    
    FORBIDDEN_COMMANDS = {
        "rm", "sudo", "del", "shutdown", "reboot", "mkfs", "dd", "chmod", "format", "mv", "cp"
    }

    FORBIDDEN_FLAGS = {
        "-rf", "--force", "-R", "--recursive"
    }
    
    def __init__(self, allowed_directories: List[str] = None):
        self.allowed_directories = allowed_directories or [os.path.abspath("./workspace")]
        # Ensure workspace exists
        for d in self.allowed_directories:
            os.makedirs(d, exist_ok=True)

    def validate_command(self, command_line: str) -> Tuple[bool, str]:
        """Validates a command against forbidden lists."""
        if not command_line or not command_line.strip():
            return False, "Empty command"
            
        try:
            tokens = shlex.split(command_line)
        except ValueError as e:
            return False, f"Malfromed command string: {str(e)}"

        if not tokens:
            return False, "No valid command tokens found"

        base_cmd = tokens[0].lower()
        
        # 1. Check forbidden base commands
        if base_cmd in self.FORBIDDEN_COMMANDS:
            logger.warning(f"SECURITY ALERT: Blocked forbidden command execution: {base_cmd}")
            return False, f"Command '{base_cmd}' is completely forbidden by the security policy."
            
        # 2. Check forbidden flags
        for token in tokens[1:]:
            if token in self.FORBIDDEN_FLAGS:
                logger.warning(f"SECURITY ALERT: Blocked forbidden flag: {token} in {base_cmd}")
                return False, f"Flag '{token}' is forbidden."

        return True, "Command passed security checks"

    def validate_path_access(self, target_path: str) -> bool:
        """Ensures the target path is within allowed directories (no directory traversal)."""
        abs_target = os.path.abspath(target_path)
        for allowed_dir in self.allowed_directories:
            if abs_target.startswith(os.path.abspath(allowed_dir)):
                return True
                
        logger.warning(f"SECURITY ALERT: Blocked out-of-bounds path access: {target_path}")
        return False
