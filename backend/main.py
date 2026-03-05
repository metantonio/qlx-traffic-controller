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

@app.on_event("startup")
async def startup_event():
    # Start the task scheduler in the background
    asyncio.create_task(system_scheduler.start_scheduler())
    logger.info("Background Task Scheduler initialized.")

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
    from backend.tools.mcp_filesystem import get_mcp_filesystem_tools
    from backend.tools.mcp_memory import get_mcp_memory_tools
    
    # 1. Static tools from registry (these are dicts)
    static_tools = system_registry.list_tools()
    
    # 2. Dynamic tools from MCP servers (these are BaseTool objects)
    fs_tools = await get_mcp_filesystem_tools()
    mem_tools = await get_mcp_memory_tools()
    
    custom_tools = []
    
    # Add static tools
    for tool in static_tools:
        custom_tools.append({
            "name": tool["name"],
            "description": tool["description"],
            "schema": tool.get("parameters", {})
        })
        
    # Add dynamic tools
    for tool in fs_tools + mem_tools:
        schema = {}
        if hasattr(tool, "args_schema") and tool.args_schema:
            if hasattr(tool.args_schema, "model_json_schema"):
                schema = tool.args_schema.model_json_schema()
            else:
                schema = tool.args_schema # already a dict or fallback
                
        custom_tools.append({
            "name": tool.name,
            "description": tool.description,
            "schema": schema
        })
        
    return custom_tools

import ollama

@app.get("/api/llm/models")
async def list_llm_models():
    """Returns supported providers and common models."""
    ollama_models = []
    try:
        # Fetch local models from Ollama
        response = ollama.list()
        # Newer versions of ollama-python return an object with a 'models' attribute
        ollama_models = [m.model for m in response.models]
        
        # Promote qwen2.5-coder:7b to default if exists
        target = "qwen2.5-coder:7b"
        if target in ollama_models:
            ollama_models.remove(target)
            ollama_models.insert(0, target)
            
    except Exception as e:
        logger.error(f"Failed to fetch local Ollama models: {e}")
        # Fallback to defaults if Ollama is unreachable
        ollama_models = ["qwen2.5-coder:7b", "llama3.1", "mistral"]

    return [
        {
            "provider": "ollama",
            "name": "Ollama (Local)",
            "models": ollama_models,
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

def check_port(host: str, port: int):
    import socket
    with socket.socket(socket.AF_INET, socket.SOCK_STREAM) as s:
        try:
            s.bind((host, port))
        except socket.error:
            logger.error(f"PORT CONFLICT: Port {port} is already in use by another process.")
            logger.error(f"Common culprits: Edge browser, another instance of this app, or a zombie python process.")
            logger.error(f"Please close the conflicting application and restart.")
            return False
    return True

if __name__ == "__main__":
    import uvicorn
    # 1. Diagnostic check for port availability
    if not check_port(settings.API_HOST, settings.API_PORT):
        # We don't exit to allow uvicorn to show its own error, but we log the warning
        print("\n" + "!"*60)
        print(f"CRITICAL: PORT {settings.API_PORT} IS ALREADY IN USE.")
        print("Please close Edge or other processes using this port.")
        print("!"*60 + "\n")

    # 2. Use full module path if run from project root, otherwise local
    module = "backend.main:app" if os.path.exists("backend/main.py") else "main:app"
    uvicorn.run(module, host=settings.API_HOST, port=settings.API_PORT, reload=True)
