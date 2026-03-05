from fastapi import FastAPI, WebSocket, WebSocketDisconnect
from fastapi.middleware.cors import CORSMiddleware
from typing import List
import json
import logging
import asyncio
from backend.core.config import settings
from backend.core.logger import get_kernel_logger
from backend.kernel.scheduler import system_scheduler, Priority
from backend.kernel.memory_bus import system_memory_bus, MessagePayload
from backend.kernel.process import AIProcess, ResourceLimits, system_process_table

# Force tool registry load
import backend.tools.shell
import backend.tools.filesystem

logger = get_kernel_logger("AgentOS.Main")

app = FastAPI(title="AI Control Tower API", version="0.1.0")

app.add_middleware(
    CORSMiddleware,
    allow_origins=settings.CORS_ORIGINS.split(","),
    allow_credentials=True,
    allow_methods=["*"],
    allow_headers=["*"],
)

class ConnectionManager:
    def __init__(self):
        self.active_connections: List[WebSocket] = []

    async def connect(self, websocket: WebSocket):
        await websocket.accept()
        self.active_connections.append(websocket)

    def disconnect(self, websocket: WebSocket):
        self.active_connections.remove(websocket)

    async def broadcast(self, message: dict):
        text = json.dumps(message)
        for connection in self.active_connections:
            await connection.send_text(text)

manager = ConnectionManager()

@app.on_event("startup")
async def startup_event():
    logger.info("Starting AI Kernel subsystems...")
    asyncio.create_task(system_scheduler.start_scheduler())
    
    # Bridge the Kernel Memory Bus to WebSockets
    async def bridge_to_ws(msg: MessagePayload):
        # Format for backward compatibility with the Dashboard components
        await manager.broadcast({
            "type": msg.event_type,
            "source": msg.source_pid or "kernel",
            "payload": msg.data,
            "target": msg.target_pid
        })
    system_memory_bus.subscribe("*", bridge_to_ws)

@app.on_event("shutdown")
async def shutdown_event():
    system_scheduler.stop_scheduler()

@app.get("/health")
async def health_check():
    return {"status": "ok", "message": "AgentOS Kernel is running securely."}
    
@app.get("/api/processes")
async def list_processes():
    return {pid: proc.__dict__ for pid, proc in system_process_table.processes.items()}

@app.get("/api/tools")
async def list_tools():
    """Returns a list of all available tools in the system."""
    from backend.tools.mcp_registry import system_registry
    from backend.tools.mcp_filesystem import get_mcp_filesystem_tools
    
    # Custom tools
    custom_tools = system_registry.list_tools()
    
    return custom_tools

@app.get("/api/processes/{pid}")
async def get_process_details(pid: str):
    proc = system_process_table.get(pid)
    if not proc:
        return {"error": "Process not found"}
    
    return {
        "pid": proc.pid,
        "agent_name": proc.agent_name,
        "task": proc.task_description,
        "state": proc.state.value,
        "history": proc.history,
        "metrics": proc.metrics,
        "allowed_tools": proc.resource_limits.allowed_tools
    }

@app.websocket("/ws")
async def websocket_endpoint(websocket: WebSocket):
    await manager.connect(websocket)
    try:
        # Bridge the Kernel Memory Bus to this specific WebSocket
        async def bridge_to_ws(msg: MessagePayload):
            await websocket.send_json({
                "type": msg.event_type,
                "source": msg.source_pid or "kernel",
                "payload": msg.data,
                "target": msg.target_pid,
                "timestamp": msg.timestamp # Include real timestamp
            })
        
        system_memory_bus.subscribe("*", bridge_to_ws)

        while True:
            data = await websocket.receive_text()
            logger.info(f"Dashboard WS message: {data}")
            try:
                msg = json.loads(data)
                if msg.get("action") == "spawn":
                    agent_name = msg.get("agent_name", "test_agent")
                    task_text = msg.get("task", "Simulated WS Task")
                    
                    # Robust handling: only default if key is missing or None
                    allowed_tools = msg.get("allowed_tools")
                    if allowed_tools is None:
                        allowed_tools = ["shell_execute", "filesystem_read"]
                    
                    # Conversation Resumption logic
                    parent_pid = msg.get("parent_pid")
                    initial_history = msg.get("initial_history")
                    
                    if parent_pid and not initial_history:
                        parent = system_process_table.get(parent_pid)
                        if parent:
                            initial_history = parent.history
                    
                    proc = AIProcess(
                        agent_name=agent_name,
                        task_description=task_text,
                        limits=ResourceLimits(allowed_tools=allowed_tools)
                    )
                    
                    # Pass initial history into memory context for scheduler to pick up
                    if initial_history:
                        proc.memory_context["initial_history"] = initial_history
                        
                    await system_scheduler.submit(proc, Priority.MEDIUM)
                    await websocket.send_json({"type": "info", "message": f"Spawned {proc.pid}: {task_text[:20]}..."})
            except Exception as e:
                logger.error(f"Failed to process WS command: {e}")

    except WebSocketDisconnect:
        manager.disconnect(websocket)
        logger.info("Dashboard disconnected")

if __name__ == "__main__":
    import uvicorn
    uvicorn.run("main:app", host=settings.API_HOST, port=settings.API_PORT, reload=True)
