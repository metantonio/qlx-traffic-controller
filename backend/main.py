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
from backend.kernel.process import system_process_table
from backend.kernel.memory_bus import system_memory_bus, MessagePayload
from backend.kernel.agent_manager import CustomAgent, agent_manager
from backend.kernel.workflow_manager import Workflow, workflow_manager
from backend.kernel.workflow_orchestrator import workflow_orchestrator
from backend.models.database_models import DbProcess, DbMessage
from backend.core.database import SessionLocal
from sqlalchemy import desc

# Force tool registry load
import backend.tools.shell
import backend.tools.filesystem
import backend.tools.memory

logger = get_kernel_logger("QLX-TC.Main")

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
    from backend.tools.mcp_manager import mcp_manager
    
    # 1. Static tools from registry (these are dicts)
    static_tools = system_registry.list_tools()
    
    # 2. Dynamic tools from all configured MCP servers
    dynamic_tools = await mcp_manager.get_all_tools()
    
    results = []
    
    # Add static tools
    for tool in static_tools:
        results.append({
            "name": tool["name"],
            "description": tool["description"],
            "schema": tool.get("parameters", {})
        })
        
    # Add dynamic tools
    for tool in dynamic_tools:
        schema = {}
        if hasattr(tool, "args_schema") and tool.args_schema:
            if hasattr(tool.args_schema, "model_json_schema"):
                schema = tool.args_schema.model_json_schema()
            elif hasattr(tool.args_schema, "schema"):
                schema = tool.args_schema.schema()
            else:
                schema = str(tool.args_schema)
        
        results.append({
            "name": tool.name,
            "description": tool.description,
            "schema": schema
        })
        
    return results

@app.get("/api/mcp/servers")
async def list_mcp_servers():
    from backend.tools.mcp_manager import mcp_manager
    return mcp_manager.list_servers()

@app.post("/api/mcp/servers")
async def add_mcp_server(data: dict):
    from backend.tools.mcp_manager import mcp_manager
    mcp_manager.add_server(
        id=data["id"],
        name=data["name"],
        command=data["command"],
        args=data["args"],
        env=data.get("env")
    )
    return {"status": "success"}

@app.delete("/api/mcp/servers/{server_id}")
async def remove_mcp_server(server_id: str):
    from backend.tools.mcp_manager import mcp_manager
    mcp_manager.remove_server(server_id)
    return {"status": "success"}

@app.get("/api/agents/custom")
async def list_custom_agents():
    from backend.kernel.agent_manager import agent_manager
    return agent_manager.list_agents()

@app.post("/api/agents/custom")
async def add_custom_agent(data: dict):
    from backend.kernel.agent_manager import agent_manager, CustomAgent
    agent = CustomAgent(**data)
    agent_manager.add_agent(agent)
    return {"status": "success"}

@app.delete("/api/agents/custom/{agent_id}")
async def remove_custom_agent(agent_id: str):
    from backend.kernel.agent_manager import agent_manager
    agent_manager.remove_agent(agent_id)
    return {"status": "success"}

@app.get("/api/workflows")
async def list_workflows():
    return workflow_manager.list_workflows()

@app.post("/api/workflows")
async def create_workflow(workflow: Workflow):
    workflow_manager.add_workflow(workflow)
    return {"status": "success"}

@app.delete("/api/workflows/{id}")
async def delete_workflow(id: str):
    workflow_manager.remove_workflow(id)
    return {"status": "success"}

# --- BATCH PROCESSING ENDPOINTS ---
from backend.kernel.batch_orchestrator import batch_orchestrator

@app.post("/api/batch")
async def create_batch_job(data: dict):
    folder_path = data.get("folder_path")
    workflow_id = data.get("workflow_id")
    variables = data.get("variables", {})
    
    if not folder_path or not workflow_id:
        return {"error": "folder_path and workflow_id are required"}
        
    try:
        job_id = await batch_orchestrator.start_batch(folder_path, workflow_id, variables)
        return {"status": "success", "job_id": job_id}
    except Exception as e:
        logger.error(f"Failed to start batch job: {e}")
        return {"error": str(e)}

@app.get("/api/batch/{job_id}")
async def get_batch_status(job_id: str):
    status = batch_orchestrator.get_job_status(job_id)
    if not status:
        return {"error": "Batch job not found"}
    return status

@app.get("/api/batch")
async def list_batch_jobs():
    return [batch_orchestrator.get_job_status(job.id) for job in batch_orchestrator.active_jobs.values() if job]


import ollama

@app.get("/api/llm/models")
async def list_llm_models():
    """Returns supported providers and common models."""
    ollama_models = []
    ollama_configured = True
    ollama_error = None
    
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
        ollama_configured = False
        ollama_error = "Ollama is not running. Showing fallback models."

    return [
        {
            "provider": "ollama",
            "name": "Ollama (Local)",
            "models": ollama_models,
            "configured": ollama_configured,
            "error": ollama_error
        },
        {
            "provider": "anthropic",
            "name": "Anthropic Claude",
            "models": ["claude-4-6-sonnet-20260220", "claude-3-5-sonnet-20240620", "claude-3-opus-20240229", "claude-3-haiku-20240307"],
            "configured": bool(settings.ANTHROPIC_API_KEY)
        },
        {
            "provider": "google",
            "name": "Google Gemini",
            "models": ["gemini-3.1-pro", "gemini-2.5-flash", "gemini-3-flash"],
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

@app.get("/api/history")
async def get_process_history(page: int = 1, page_size: int = 10):
    """Returns a paginated list of historical processes."""
    skip = (page - 1) * page_size
    with SessionLocal() as db:
        # Get total count for pagination
        total_count = db.query(DbProcess).count()
        
        # Get paginated results ordered by creation time
        db_processes = db.query(DbProcess).order_by(desc(DbProcess.created_at)).offset(skip).limit(page_size).all()
        
        history = []
        for p in db_processes:
            history.append({
                "pid": p.pid,
                "agent_name": p.agent_name,
                "task": p.task_description,
                "state": p.state,
                "created_at": p.created_at.isoformat() if p.created_at else None,
                "metrics": {
                    "tokens_used": p.tokens_used,
                    "tools_called": p.tools_called,
                    "start_time": p.start_time,
                    "end_time": p.end_time
                }
            })
            
        return {
            "total": total_count,
            "page": page,
            "page_size": page_size,
            "items": history
        }

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
                action = msg.get("action")

                if action == "spawn_workflow":
                    workflow_id = msg.get("workflow_id")
                    variables = msg.get("variables", {})
                    try:
                        execution_id = await workflow_orchestrator.start_workflow(workflow_id, variables)
                        await websocket.send_json({"type": "info", "message": f"Workflow {execution_id} started."})
                    except Exception as e:
                        logger.error(f"Failed to start workflow: {e}")
                        await websocket.send_json({"type": "error", "message": str(e)})
                    continue

                if action == "spawn":
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
                    
                    # Custom Agent resolution
                    from backend.kernel.agent_manager import agent_manager
                    custom_agent = agent_manager.get_agent(agent_name)
                    
                    resolved_tools = allowed_tools
                    system_prompt_override = None

                    if custom_agent:
                        resolved_tools = custom_agent.static_tools + [f"mcp:{s}" for s in custom_agent.mcp_servers]
                        system_prompt_override = custom_agent.system_prompt
                        
                        if not llm_provider and custom_agent.provider:
                            llm_provider = custom_agent.provider
                        if not llm_model and custom_agent.model:
                            llm_model = custom_agent.model
                            
                        logger.info(f"Using Custom Agent: {custom_agent.name} with tools {resolved_tools}, LLM={llm_provider}/{llm_model}")
                    
                    proc = AIProcess(
                        agent_name=agent_name,
                        task_description=task_text,
                        limits=ResourceLimits(allowed_tools=resolved_tools)
                    )
                    
                    if system_prompt_override:
                        proc.memory_context["system_prompt"] = system_prompt_override
                    
                    if initial_history:
                        proc.memory_context["initial_history"] = initial_history
                    
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
