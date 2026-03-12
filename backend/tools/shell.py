import asyncio
from backend.tools.mcp_registry import MCPTool, system_registry
from backend.core.security import SafetyValidator
from backend.core.logger import get_kernel_logger
import shlex

logger = get_kernel_logger("QLX-TC.Tools.Shell")

validator = SafetyValidator()

def needs_approval(command: str) -> bool:
    try:
        tokens = shlex.split(command)
    except Exception:
        return True # Better safe than sorry on malformed commands
        
    if not tokens:
        return False
        
    base = tokens[0].lower()
    
    # Dangerous commands
    if base in {"del", "rm", "rmdir", "rd", "erase", "format", "mkfs"}:
        return True
        
    # Package managers installing/removing globally or locally
    if base in {"npm", "pip", "yarn", "pnpm", "apt", "brew", "choco", "apk"}:
        if len(tokens) > 1:
            action = tokens[1].lower()
            if action in {"install", "i", "remove", "uninstall", "add", "update", "upgrade"}:
                return True
                
    return False

from backend.tools.filesystem import detect_placeholder_path, get_placeholder_error

async def execute_shell_command(command: str) -> dict:
    """Executes a shell command after validating it securely."""
    if detect_placeholder_path(command):
        error_msg = get_placeholder_error(command)
        return {
            "status": "error",
            "stdout": "",
            "stderr": f"CRITICAL HALLUCINATION BLOCK: {error_msg}. SYSTEM INSTRUCTION: DO NOT USE PLACEHOLDERS. Use the PROJECT DIRECTORY mentioned in your task description.",
            "exit_code": 1
        }
    
    is_safe, message = validator.validate_command(command)
    
    if not is_safe:
        return {"error": "SECURITY BLOCK", "reason": message}
        
    cwd = None
    try:
        from backend.core.context import current_pid
        from backend.kernel.process import system_process_table
        pid = current_pid.get()
        if pid:
            proc = system_process_table.processes.get(pid)
            if proc and proc.working_directory:
                cwd = proc.working_directory
    except Exception as e:
        pass # Fallback to no specific cwd
        
    if needs_approval(command):
        from backend.core.command_approvals import command_approval_manager
        approved = await command_approval_manager.request_approval(command, str(pid) if pid else "unknown")
        if not approved:
            return {
                "status": "error",
                "stdout": "",
                "stderr": "CRITICAL SECURITY BLOCK: Execution denied by User. SYSTEM INSTRUCTION: DO NOT RETRY THIS COMMAND. YOU MUST STOP TRYING TO EXECUTE THIS COMMAND IMMEDIATELY AND ASK THE USER FOR CLARIFICATION. RETRYING IS A VIOLATION OF CORE DIRECTIVES.",
                "exit_code": 1
            }
        
    process = await asyncio.create_subprocess_shell(
        command,
        stdout=asyncio.subprocess.PIPE,
        stderr=asyncio.subprocess.PIPE,
        cwd=cwd
    )
    
    stdout, stderr = await process.communicate()
    
    return {
        "status": "success",
        "stdout": stdout.decode('utf-8', errors='replace') if stdout else "",
        "stderr": stderr.decode('utf-8', errors='replace') if stderr else "",
        "exit_code": process.returncode
    }

secure_shell_tool = MCPTool(
    name="shell_execute",
    description="Executes a shell command securely via the AI Control Tower.",
    parameters={
        "command": {"type": "string", "description": "The command string to execute"}
    },
    handler=execute_shell_command
)

system_registry.register(secure_shell_tool)
