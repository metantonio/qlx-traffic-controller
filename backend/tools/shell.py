import asyncio
from typing import Tuple, Dict
import re
import sys
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

from backend.tools.filesystem import detect_placeholder_path, get_placeholder_error, is_file_forbidden

def filter_shell_command(command: str) -> Tuple[bool, str]:
    """Provides shell-level filtering for sensitive files and operations."""
    # 1. Block access to forbidden files via shell (cat, tail, nano, echo >>)
    low_cmd = command.lower()
    from backend.tools.filesystem import FORBIDDEN_FILENAMES
    for forbidden in FORBIDDEN_FILENAMES:
        if forbidden in low_cmd:
            # We check if it looks like a file path or direct mention
            # Using regex or simple check for now
            if re.search(fr"\b{re.escape(forbidden)}\b", low_cmd):
                return False, f"SECURITY ERROR: Interactive access to '{forbidden}' is forbidden via shell."

    # 2. Block environment manipulation
    forbidden_tokens = {"export", "set", "env", "unset", "alias", "source", "."}
    try:
        tokens = shlex.split(command)
        if tokens and tokens[0].lower() in forbidden_tokens:
            return False, f"SECURITY ERROR: Environment manipulation command '{tokens[0]}' is forbidden."
    except Exception:
        pass

    # 3. Block nested shell execution/eval
    if "eval" in low_cmd or "exec" in low_cmd:
        return False, "SECURITY ERROR: Eval/Exec patterns are forbidden."

    return True, ""

def get_safe_env() -> Dict[str, str]:
    """Returns a scrubbed environment for sub-processes."""
    import os
    # whitelist approach is safer
    safe_keys = {
        "PATH", "SystemRoot", "SystemDrive", "TEMP", "TMP", 
        "USERPROFILE", "USERNAME", "COMPUTERNAME", "LANG", "LC_ALL"
    }
    env = {k: v for k, v in os.environ.items() if k in safe_keys}
    
    # 2. SANITIZE PATH: Remove '.' and relative paths to prevent binary squatting
    if "PATH" in env:
        path_sep = ";" if os.name == "nt" else ":"
        paths = env["PATH"].split(path_sep)
        # Remove empty strings, '.', and any path that doesn't start with a drive letter or /
        safe_paths = [p for p in paths if p and p != "." and os.path.isabs(p)]
        env["PATH"] = path_sep.join(safe_paths)

    # 3. Strictly remove dangerous vars
    blacklisted_vars = {"NODE_OPTIONS", "PYTHONPATH", "PYTHONHOME", "AWS_ACCESS_KEY_ID", "AWS_SECRET_ACCESS_KEY"}
    for var in blacklisted_vars:
        env.pop(var, None)
        
    return env

async def execute_shell_command(command: str) -> dict:
    """Executes a shell command after validating it securely."""
    loop = asyncio.get_running_loop()
    loop_type = type(loop).__name__
    logger.info(f"DEBUG: execute_shell_command loop type: {loop_type}")

    # CRITICAL: On Windows, we MUST use ProactorEventLoop for subprocesses
    if sys.platform == 'win32' and loop_type != 'ProactorEventLoop':
        logger.error(f"Incompatible event loop detected: {loop_type}. Subprocesses will fail.")
        return {
            "status": "error",
            "stdout": "",
            "stderr": f"SYSTEM CONFIGURATION ERROR: The system is using {loop_type} instead of ProactorEventLoop on Windows. "
                      "Asynchronous subprocesses are not supported in this mode. Please restart the backend.",
            "exit_code": 1
        }
    
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
    
    is_shell_safe, shell_error = filter_shell_command(command)
    if not is_shell_safe:
        return {"error": "SECURITY BLOCK", "reason": shell_error}
        
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
        cwd=cwd,
        env=get_safe_env()
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
