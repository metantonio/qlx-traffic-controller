import shlex
import os
import logging
from typing import List, Tuple

logger = logging.getLogger("TrafficController.Kernel.Capabilities")

class Capability:
    FILESYSTEM_READ = "filesystem.read"
    FILESYSTEM_WRITE = "filesystem.write"
    DOCUMENT_PARSE = "document.parse"
    WEB_SEARCH = "web.search"
    SHELL_EXECUTE_SAFE = "shell.execute.safe"
    DATABASE_QUERY = "database.query"

class CapabilityEnforcer:
    """Enforces fine-grained capabilities instead of global permissions."""
    
    FORBIDDEN_SHELL_COMMANDS = {
        "rm", "sudo", "del", "shutdown", "reboot", "mkfs", "dd", "chmod", "format", "mv", "cp"
    }
    
    FORBIDDEN_SHELL_FLAGS = {
        "-rf", "--force", "-R", "--recursive"
    }

    def __init__(self, allowed_directories: List[str] = None):
        self.allowed_directories = allowed_directories or [os.path.abspath("./workspace")]
        for d in self.allowed_directories:
            os.makedirs(d, exist_ok=True)

    def check_capability(self, agent_capabilities: List[str], required_capability: str) -> bool:
        """Verifies if the agent holds the necessary capability."""
        if required_capability not in agent_capabilities:
            logger.error(f"SECURITY ALERT: Agent lacks required capability: {required_capability}")
            return False
        return True

    def validate_shell_command(self, agent_capabilities: List[str], command_line: str) -> Tuple[bool, str]:
        """Validates a command ensuring the agent has the shell capability AND it's not destructive."""
        if not self.check_capability(agent_capabilities, Capability.SHELL_EXECUTE_SAFE):
            return False, f"Missing capability: {Capability.SHELL_EXECUTE_SAFE}"
            
        try:
            tokens = shlex.split(command_line)
        except ValueError as e:
            return False, f"Malformed command string: {str(e)}"

        if not tokens:
            return False, "Empty command"
            
        base_cmd = tokens[0].lower()
        if base_cmd in self.FORBIDDEN_SHELL_COMMANDS:
            return False, f"Command '{base_cmd}' is completely forbidden by the kernel security policy."
            
        for token in tokens[1:]:
            if token in self.FORBIDDEN_SHELL_FLAGS:
                return False, f"Flag '{token}' is forbidden."
                
        return True, "Safe"

    def validate_path_access(self, agent_capabilities: List[str], target_path: str, is_write: bool = False) -> Tuple[bool, str]:
        """Verifies path boundary and read/write capabilities."""
        required = Capability.FILESYSTEM_WRITE if is_write else Capability.FILESYSTEM_READ
        if not self.check_capability(agent_capabilities, required):
            return False, f"Missing capability: {required}"

        abs_target = os.path.abspath(target_path)
        for allowed_dir in self.allowed_directories:
            if abs_target.startswith(os.path.abspath(allowed_dir)):
                return True, "Safe"
                
        return False, f"Out-of-bounds path access: {target_path} is not in allowed directories."

# Global enforcer
system_enforcer = CapabilityEnforcer()
