import asyncio
from backend.tools.mcp_registry import MCPTool, system_registry
from backend.core.security import SafetyValidator

validator = SafetyValidator()

async def execute_shell_command(command: str) -> dict:
    """Executes a shell command after validating it securely."""
    
    is_safe, message = validator.validate_command(command)
    
    if not is_safe:
        return {"error": "SECURITY BLOCK", "reason": message}
        
    process = await asyncio.create_subprocess_shell(
        command,
        stdout=asyncio.subprocess.PIPE,
        stderr=asyncio.subprocess.PIPE
    )
    
    stdout, stderr = await process.communicate()
    
    return {
        "status": "success",
        "stdout": stdout.decode() if stdout else "",
        "stderr": stderr.decode() if stderr else "",
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
