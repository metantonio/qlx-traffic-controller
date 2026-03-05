from fastapi import FastAPI, WebSocket, WebSocketDisconnect
from fastapi.middleware.cors import CORSMiddleware
from typing import List
import os
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
import backend.tools.memory

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
        if websocket in self.active_connections:
            self.active_connections.remove(websocket)

    async def broadcast(self, message: dict):
        for connection in self.active_connections:
            try:
                await connection.send_json(message)
            except:
                pass

manager = ConnectionManager()

@app.get("/api/processes")
async def list_processes():
    processes = system_process_table.list_all()
    return [{
        "pid": p.pid,
        "agent_name": p.agent_name,
        "task": p.task_description,
        "state": p.state.value,
        "metrics": p.metrics
    } for p in processes]

@app.get("/api/tools")
async def list_tools():
    from backend.tools.mcp_registry import system_registry
    tools = system_registry.list_tools()
    
    custom_tools = []
    for tool in tools:
        custom_tools.append({
            "name": tool.name,
            "description": tool.description,
            "schema": tool.args_schema.model_json_schema() if hasattr(tool, "args_schema") and tool.args_schema else {}
        })
    return custom_tools

@app.get("/api/llm/models")
async def list_llm_models():
    """Returns supported providers and common models."""
    return [
        {
            "provider": "ollama",
            "name": "Ollama (Local)",
            "models": ["qwen2.5-coder:7b", "llama3.1", "mistral", "codellama"],
            "configured": True
        },
        {
            "provider": "anthropic",
            "name": "Anthropic Claude",
            "models": ["claude-3-5-sonnet-20240620", "claude-3-opus-20240229", "claude-3-haiku-20240307"],
            "configured": bool(settings.ANTHROPIC_API_KEY)
        },
        {
            "provider": "google",
            "name": "Google Gemini",
            "models": ["gemini-1.5-pro", "gemini-1.5-flash", "gemini-3.1-pro-preview", "gemini-2.5-flash"],
            "configured": bool(settings.GOOGLE_API_KEY)
        }
    ]

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

@app.get("/api/memory")
async def get_knowledge_graph():
    memory_path = os.path.abspath(os.path.join(os.path.dirname(__file__), "..", "data", "memory.json"))
    if not os.path.exists(memory_path):
        return {"entities": [], "relations": []}
    
    try:
        with open(memory_path, 'r', encoding='utf-8') as f:
            return json.load(f)
    except Exception as e:
        logger.error(f"Failed to read memory.json: {e}")
        return {"entities": [], "relations": []}

@app.websocket("/ws")
async def websocket_endpoint(websocket: WebSocket):
    await manager.connect(websocket)
    try:
        async def bridge_to_ws(msg: MessagePayload):
            await websocket.send_json({
                "type": msg.event_type,
                "source": msg.source_pid or "kernel",
                "payload": msg.data,
                "target": msg.target_pid,
                "timestamp": msg.timestamp
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
                    
                    allowed_tools = msg.get("allowed_tools")
                    if allowed_tools is None:
                        allowed_tools = ["shell_execute", "filesystem_read"]
                    
                    parent_pid = msg.get("parent_pid")
                    initial_history = msg.get("initial_history")
                    
                    if parent_pid and not initial_history:
                        parent = system_process_table.get(parent_pid)
                        if parent:
                            initial_history = parent.history
                    
                    # LLM Overrides
                    llm_provider = msg.get("provider")
                    llm_model = msg.get("model")
                    
                    proc = AIProcess(
                        agent_name=agent_name,
                        task_description=task_text,
                        limits=ResourceLimits(allowed_tools=allowed_tools)
                    )
                    
                    if initial_history:
                        proc.memory_context["initial_history"] = initial_history
                    
                    # Store LLM overrides in memory_context for scheduler
                    if llm_provider: proc.memory_context["llm_provider"] = llm_provider
                    if llm_model: proc.memory_context["llm_model"] = llm_model
                        
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
