import asyncio
import logging
from typing import Dict, Any
from backend.kernel.process import AIProcess
from backend.kernel.capabilities import system_enforcer

logger = logging.getLogger("TrafficController.Kernel.Sandbox")

class SandboxException(Exception):
    pass

class AISandbox:
    """
    The secure execution boundary for an AIProcess.
    All tool routing and command execution requested by the agent MUST occur inside this context.
    Provides isolation and capability mapping.
    """
    def __init__(self, process: AIProcess):
        self.process = process
        self.active_subprocesses = []
        
    async def execute_shell_command(self, command: str) -> Dict[str, Any]:
        """Evaluates capability and executes shell if permitted by the kernel policy."""
        # 1. Kernel Capability Check
        is_safe, message = system_enforcer.validate_shell_command(
            self.process.capabilities, 
            command
        )
        
        if not is_safe:
            logger.warning(f"SANDBOX BLOCK [PID:{self.process.pid}]: Shell execution denied. Reason: {message}")
            return {"error": "Kernel Security Block", "reason": message}
            
        # 2. Add to Metrics/Quotas
        self.process.metrics["tools_called"] += 1
        if not self.process.check_limits():
            raise SandboxException("Process hit resource limits during tool execution")
            
        # 3. Native isolated execution
        try:
            logger.info(f"SANDBOX EXECUTE [PID:{self.process.pid}]: {command}")
            subproc = await asyncio.create_subprocess_shell(
                command,
                stdout=asyncio.subprocess.PIPE,
                stderr=asyncio.subprocess.PIPE
            )
            self.active_subprocesses.append(subproc)
            
            # Using wait_for to enforce strict capability timeouts (placeholder max 30s)
            stdout, stderr = await asyncio.wait_for(subproc.communicate(), timeout=30.0)
            self.active_subprocesses.remove(subproc)
            
            return {
                "status": "success",
                "stdout": stdout.decode() if stdout else "",
                "stderr": stderr.decode() if stderr else "",
                "exit_code": subproc.returncode
            }
        except asyncio.TimeoutError:
            subproc.kill()
            self.active_subprocesses.remove(subproc)
            return {"error": "Execution Timeout", "reason": "Shell command exceeded sandbox limits"}
        except Exception as e:
            return {"error": "Sandbox Execution Error", "reason": str(e)}

    def cleanup(self):
        """Kills any dangling subprocesses attached to this agent process sandbox upon termination."""
        for proc in self.active_subprocesses:
            try:
                if proc.returncode is None:
                    proc.kill()
            except Exception:
                pass
        self.active_subprocesses = []
