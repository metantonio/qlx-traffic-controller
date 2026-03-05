import logging
from typing import Dict, Any, List
from backend.kernel.process import AIProcess
from backend.kernel.sandbox import AISandbox, SandboxException
from backend.tools.mcp_registry import system_registry

logger = logging.getLogger("TrafficController.Kernel.ToolRouter")

class ToolExecutionRouter:
    """Routes tool execution requests, enforcing quotas and capabilities."""
    
    def __init__(self):
        self.registry = system_registry
        
    async def route_request(self, process: AIProcess, tool_name: str, arguments: Dict[str, Any]) -> Dict[str, Any]:
        """Validates bounds and routes a tool request into the process sandbox."""
        
        # 1. Does the tool exist?
        tool = self.registry.get_tool(tool_name)
        if not tool:
            return {"error": "Tool Not Found", "reason": f"Tool '{tool_name}' is not registered in the system."}
            
        # 2. Check process limits BEFORE execution
        if not process.check_limits():
            process.fail("Resource Exhaustion")
            return {"error": "Resource Limits Reached", "reason": "Process has consumed its allocated tokens or runtime."}
            
        # 3. Create Sandbox instance
        sandbox = AISandbox(process)
        
        # 4. Special internal routing: if it's a shell command, the sandbox handles strict capability matching natively
        if tool_name == "shell_execute":
            # Delegate entirely to sandbox isolated execution
            return await sandbox.execute_shell_command(arguments.get("command", ""))
            
        # 5. Generic tool routing (Requires specific explicit capabilities matching the tool name)
        # For example, to use "filesystem_read" tool, you need the "filesystem.read" capability.
        # We derive the required capability loosely from the tool name for this prototype.
        required_cap = tool_name.replace("_", ".")
        from backend.kernel.capabilities import system_enforcer
        if not system_enforcer.check_capability(process.capabilities, required_cap):
             logger.warning(f"ROUTER BLOCK [PID:{process.pid}]: Lacks '{required_cap}' for tool '{tool_name}'")
             return {"error": "Capability Block", "reason": f"Process does not hold the capability: {required_cap}"}
             
        # Increment quota and execute safely
        process.metrics["tools_called"] += 1
        try:
            result = await tool.execute(**arguments)
            return {"status": "success", "result": result}
        except Exception as e:
            logger.error(f"ROUTER EXECUTION ERROR [PID:{process.pid}]: {e}")
            return {"error": "Tool Execution Failed", "reason": str(e)}

system_tool_router = ToolExecutionRouter()
