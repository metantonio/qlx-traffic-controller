import asyncio
from typing import Dict

class CommandApprovalManager:
    def __init__(self):
        self.pending_approvals: Dict[str, asyncio.Future] = {}
        self.broadcast_callback = None
        
    def register_broadcaster(self, cb):
        self.broadcast_callback = cb
        
    async def request_approval(self, command: str, pid: str) -> bool:
        import uuid
        approval_id = str(uuid.uuid4())
        
        loop = asyncio.get_running_loop()
        future = loop.create_future()
        self.pending_approvals[approval_id] = future
        
        if self.broadcast_callback:
            # We must await the callback if it's an async function
            if asyncio.iscoroutinefunction(self.broadcast_callback):
                await self.broadcast_callback({
                    "action": "command_approval_requested",
                    "approval_id": approval_id,
                    "command": command,
                    "pid": pid
                })
            else:
                self.broadcast_callback({
                    "action": "command_approval_requested",
                    "approval_id": approval_id,
                    "command": command,
                    "pid": pid
                })
            
        try:
            # Wait with a timeout (e.g. 5 minutes)
            approved = await asyncio.wait_for(future, timeout=300.0)
            return approved
        except asyncio.TimeoutError:
            return False
        finally:
            self.pending_approvals.pop(approval_id, None)
            
    def resolve_approval(self, approval_id: str, approved: bool):
        if approval_id in self.pending_approvals:
            future = self.pending_approvals[approval_id]
            if not future.done():
                future.set_result(approved)

command_approval_manager = CommandApprovalManager()
