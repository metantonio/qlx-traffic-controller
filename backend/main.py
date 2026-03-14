import sys
import asyncio

if sys.platform == 'win32':
    asyncio.set_event_loop_policy(asyncio.WindowsProactorEventLoopPolicy())

import os
import json
import logging

from fastapi import FastAPI, WebSocket, WebSocketDisconnect, Depends, HTTPException
from fastapi.middleware.cors import CORSMiddleware
from fastapi.staticfiles import StaticFiles
from sqlalchemy.orm import Session
from typing import List

from backend.core.config import settings
from backend.core.logger import get_kernel_logger
from backend.kernel.scheduler import system_scheduler, Priority
from backend.kernel.process import AIProcess, ResourceLimits, system_process_table
from backend.kernel.memory_bus import system_memory_bus, MessagePayload
from backend.kernel.agent_manager import CustomAgent, agent_manager
from backend.core.command_approvals import command_approval_manager
from backend.kernel.workflow_manager import Workflow, workflow_manager
from backend.kernel.workflow_orchestrator import workflow_orchestrator
from backend.kernel.mission_control import mission_control
from backend.models.database_models import DbProcess, DbMessage
from backend.core.database import SessionLocal, get_db, init_db
from sqlalchemy import desc
from contextlib import asynccontextmanager
from backend.api import orchestration_api

# Force tool registry load
import backend.tools.shell
import backend.tools.filesystem
import backend.tools.memory
import backend.tools.pipeline_tools
import backend.tools.agent_tools
from backend.tools.sharing_manager import sharing_manager
from backend.tools.mcp_manager import mcp_manager
import backend.tools.vision_tools
import backend.tools.desktop_tools

logger = get_kernel_logger("QLX-TC.Main")

def bootstrap_system():
    """Seeds the system with default configuration on first run."""
    try:
        # Define 'emptiness' criteria
        agents_path = "backend/data/custom_agents.json"
        has_agents = os.path.exists(agents_path) and os.path.getsize(agents_path) > 2
        
        mcp_servers = mcp_manager.list_servers()
        has_mcps = len(mcp_servers) > 0
        
        if not has_agents and not has_mcps:
            seed_path = "backend/data/seed/default_bundle.json"
            if os.path.exists(seed_path):
                logger.info("Fresh installation detected. Bootstrapping base configuration...")
                with open(seed_path, 'r') as f:
                    bundle = json.load(f)
                
                # Import with no overrides (seed should only contain tools that don't STRICTLY require keys to be initialized, 
                # or rely on the user to configure them later via the UI)
                results = sharing_manager.import_bundle(bundle, overrides={})
                logger.info(f"Bootstrap complete: {results}")
            else:
                logger.warning("Fresh installation detected but no seed bundle found at %s", seed_path)
    except Exception as e:
        logger.error(f"Error during bootstrap: {str(e)}")

KERNEL_SYSTEM_PROMPT = """You are the QLX-TC Orchestrator (Kernel). 
Your role is to manage the system and delegate complex tasks to specialized agents or skills.

### DOMAIN AUTHORITY RULES:
1. You MUST prioritize specialized agents over your own tools for domain-specific work.
2. For FRONTEND/UI (React, CSS, HTML, Game logic), delegate to 'frontend_developer'.
3. For BACKEND/API (FastAPI, Python logic, Database schema), delegate to 'backend_developer'.
4. For TESTING or code verification, delegate to 'qa_tester'.
5. For ARCHITECTURE/PLANNING of a new feature, delegate to 'software_architect'.

CRITICAL INSTRUCTIONS:
1. You DO NOT have direct access to desktop tools (screenshots, window management, etc.). 
2. For ANYTHING related to the screen, vision, or desktop interaction, you MUST use 'list_available_agents' to find the 'desktop_controller' and then 'delegate_to_agent' to perform the task.
3. For OCR or text extraction from images, delegate to 'OCR_Agent'.
4. If you aren't sure which agent to use, always call 'list_available_agents' first.

Always be concise and professional. You act as the brain of the operation."""

@asynccontextmanager
async def lifespan(app: FastAPI):
    logger.info("Kernel starting up...")
    # 1. Initialize Database and apply migrations
    init_db()
    logger.info("Database initialized and migrations applied.")
    
    # 2. Start the task scheduler in the background
    scheduler_task = asyncio.create_task(system_scheduler.start_scheduler())
    logger.info("Background Task Scheduler initialized.")
    
    # 3. Bootstrap if empty
    bootstrap_system()
    
    yield
    
    # Shutdown logic if needed
    # scheduler_task.cancel()

app = FastAPI(title="AI Control Tower API", version="0.1.0", lifespan=lifespan)

app.add_middleware(
    CORSMiddleware,
    allow_origins=settings.CORS_ORIGINS.split(","),
    allow_credentials=True,
    allow_methods=["*"],
    allow_headers=["*"],
)

# Include Routers
app.include_router(orchestration_api.router)

# Serve screenshots as static files
SCREENSHOTS_DIR = os.path.abspath(os.path.join(os.path.dirname(__file__), "data", "screenshots"))
os.makedirs(SCREENSHOTS_DIR, exist_ok=True)
app.mount("/api/screenshots", StaticFiles(directory=SCREENSHOTS_DIR), name="screenshots")

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
command_approval_manager.register_broadcaster(manager.broadcast)

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
            "schema": tool.get("parameters", {}),
            "source": "static",
            "restricted": tool.get("restricted", False)
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
            "schema": schema,
            "source": "mcp",
            "restricted": False # MCP tools are not restricted by this specific mechanism yet
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
    return {"status": "ok"}

@app.post("/api/mcp/servers/{server_id}/toggle")
async def toggle_mcp_server(server_id: str, data: dict):
    from backend.tools.mcp_manager import mcp_manager
    enabled = data.get("enabled", True)
    mcp_manager.toggle_server(server_id, enabled)
    return {"status": "ok", "enabled": enabled}

@app.post("/api/store/refresh")
async def refresh_mcp_store(payload: dict = None):
    from backend.tools.mcp_manager import mcp_manager
    url = payload.get("url") if payload else None
    
    # Refresh MCP Servers (GitHub)
    mcp_success, mcp_msg = mcp_manager.refresh_store(url) if url else mcp_manager.refresh_store()
    
    # Refresh Skills (ClawHub)
    claw_success, claw_msg = mcp_manager.refresh_clawhub_skills()
    
    if not mcp_success and not claw_success:
        raise HTTPException(status_code=500, detail=f"Refresh failed. MCP: {mcp_msg}, ClawHub: {claw_msg}")
        
    return {
        "status": "ok", 
        "mcp": mcp_msg,
        "clawhub": claw_msg
    }

# --- STORE ENDPOINTS ---

@app.get("/api/store/mcp")
async def list_mcp_store():
    from backend.tools.mcp_manager import mcp_manager
    store = mcp_manager.load_store()
    return store.get("mcp", {})

@app.get("/api/store/skills")
async def list_skills_store(page: int = 1, page_size: int = 15):
    from backend.tools.mcp_manager import mcp_manager
    # If page > 1, always fetch from live ClawHub
    if page > 1:
        return mcp_manager.fetch_clawhub_page(page, page_size)
    
    # For page 1, try to return cached data but also check if we need to refresh
    store = mcp_manager.load_store()
    cached_skills = store.get("skills", {})
    
    if not cached_skills:
        return mcp_manager.fetch_clawhub_page(page, page_size)
    
    return {
        "items": cached_skills,
        "total": len(cached_skills),
        "pages": 1,
        "current_page": 1
    }

@app.get("/api/store/search")
async def search_skills_store(q: str):
    import requests
    try:
        url = f"https://clawhub.ai/api/v1/search?q={q}"
        response = requests.get(url, timeout=5)
        if response.status_code == 200:
            return response.json()
        return {"results": []}
    except Exception as e:
        logger.error(f"ClawHub search error: {e}")
        return {"results": []}

@app.post("/api/store/install")
async def install_from_store(data: dict):
    from backend.tools.mcp_manager import mcp_manager
    server_id = data.get("server_id")
    overrides = data.get("overrides")
    
    if not server_id:
        return {"error": "server_id is required"}
        
    try:
        mcp_manager.install_from_store(server_id, overrides)
        return {"status": "success"}
    except Exception as e:
        logger.error(f"Failed to install from store: {e}")
        return {"error": str(e)}

@app.post("/api/store/install-skill")
async def install_skill_from_store(data: dict):
    from backend.kernel.skill_installer import download_and_install_skill, SkillInstallationError
    slug = data.get("slug")
    version = data.get("version")
    
    if not slug:
        raise HTTPException(status_code=400, detail="slug is required")
        
    try:
        agent = download_and_install_skill(slug, version)
        return {"status": "success", "agent_id": agent.id}
    except SkillInstallationError as e:
        logger.error(f"Failed to install skill: {e}")
        raise HTTPException(status_code=400, detail=str(e))
    except Exception as e:
        logger.error(f"Unexpected error installing skill: {e}")
        raise HTTPException(status_code=500, detail=f"An unexpected error occurred: {str(e)}")

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

@app.put("/api/agents/custom/{agent_id}")
async def update_custom_agent(agent_id: str, data: dict):
    from backend.kernel.agent_manager import agent_manager, CustomAgent
    # Ensure ID in payload matches URL
    data["id"] = agent_id
    agent = CustomAgent(**data)
    agent_manager.add_agent(agent) # add_agent in manager is actually an upsert
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

@app.put("/api/workflows/{id}")
async def update_workflow(id: str, workflow: Workflow):
    # Ensure ID in payload matches URL
    workflow.id = id
    workflow_manager.add_workflow(workflow) # add_workflow is an upsert
    return {"status": "success"}

# --- SHARING ENDPOINTS ---

@app.post("/api/share/export")
async def export_bundle(data: dict):
    from backend.tools.sharing_manager import sharing_manager
    agent_ids = data.get("agent_ids", [])
    workflow_ids = data.get("workflow_ids", [])
    mcp_ids = data.get("mcp_ids", [])
    
    try:
        bundle = sharing_manager.export_bundle(agent_ids, workflow_ids, mcp_ids)
        return bundle
    except Exception as e:
        logger.error(f"Export failed: {e}")
        return {"error": str(e)}

@app.post("/api/share/import")
async def import_bundle(data: dict):
    from backend.tools.sharing_manager import sharing_manager
    bundle = data.get("bundle")
    overrides = data.get("overrides")
    
    if not bundle:
        return {"error": "bundle is required"}
        
    try:
        results = sharing_manager.import_bundle(bundle, overrides)
        return {"status": "success", "results": results}
    except Exception as e:
        logger.error(f"Import failed: {e}")
        return {"error": str(e)}

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

@app.delete("/api/batch/{job_id}")
async def stop_batch_job(job_id: str):
    await batch_orchestrator.stop_batch(job_id)
    return {"status": "success"}


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

@app.get("/api/settings")
async def get_system_settings():
    from backend.kernel.settings_manager import settings_manager
    return settings_manager.get_all()

@app.get("/api/settings/directories")
async def get_allowed_directories(db: Session = Depends(get_db)):
    from backend.models.database_models import DbAllowedDirectory
    dirs = db.query(DbAllowedDirectory).all()
    return [{"id": d.id, "path": d.path, "description": d.description} for d in dirs]

@app.post("/api/settings/directories")
async def add_allowed_directory(data: dict, db: Session = Depends(get_db)):
    from backend.models.database_models import DbAllowedDirectory
    path = data.get("path")
    if not path:
        return {"error": "Path is required"}
    
    # Check if already exists
    existing = db.query(DbAllowedDirectory).filter(DbAllowedDirectory.path == path).first()
    if existing:
        return {"error": "Directory already allowed"}

    new_dir = DbAllowedDirectory(path=path, description=data.get("description", ""))
    db.add(new_dir)
    db.commit()
    return {"status": "success", "id": new_dir.id}

@app.delete("/api/settings/directories/{id}")
async def remove_allowed_directory(id: int, db: Session = Depends(get_db)):
    from backend.models.database_models import DbAllowedDirectory
    db_dir = db.query(DbAllowedDirectory).filter(DbAllowedDirectory.id == id).first()
    if not db_dir:
        return {"error": "Directory not found"}
    db.delete(db_dir)
    db.commit()
    return {"status": "success"}

@app.put("/api/settings")
async def update_system_settings(data: dict):
    from backend.kernel.settings_manager import settings_manager
    for key, value in data.items():
        settings_manager.update(key, value)
    return {"status": "success"}

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
        "has_proceeded": proc.has_proceeded,
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
                "created_at": p.created_at.isoformat() + "Z" if p.created_at else None,
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

@app.delete("/api/history/{pid}")
async def delete_process_history(pid: str):
    """Deletes a process and its messages from the database."""
    with SessionLocal() as db:
        db_proc = db.query(DbProcess).filter(DbProcess.pid == pid).first()
        if not db_proc:
            return {"error": "Process not found in history"}
        
        db.delete(db_proc)
        db.commit()
    
    # Also remove from memory if present
    system_process_table.remove(pid)
    return {"status": "success"}

@app.delete("/api/history")
async def clear_all_history():
    """Wipes the entire process and message history from the database."""
    with SessionLocal() as db:
        # Cascade delete is configured, so deleting processes will delete messages
        db.query(DbProcess).delete()
        db.commit()
    
    # Clear memory lookup
    system_process_table.processes.clear()
    return {"status": "success"}

@app.delete("/api/processes/{pid}")
async def dismiss_process(pid: str):
    """Removes a finished process from the active threads list (memory only)."""
    proc = system_process_table.get(pid)
    if not proc:
        return {"error": "Process not found"}
    
    from backend.kernel.process import ProcessState
    if proc.state == ProcessState.RUNNING:
        return {"error": "Cannot dismiss a running process. Stop it first."}
    
    system_process_table.remove(pid)
    return {"status": "success"}

@app.delete("/api/processes")
async def clear_finished_processes():
    """Removes all completed/failed processes from the active memory list."""
    system_process_table.clear_all_finished()
    return {"status": "success"}

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

                if action == "start_mission":
                    task = msg.get("task")
                    ws_dir = msg.get("working_directory")
                    try:
                        mission_id = await mission_control.start_mission(task, ws_dir)
                        await websocket.send_json({"type": "info", "message": f"Mission {mission_id} started."})
                    except Exception as e:
                        logger.error(f"Failed to start mission: {e}")
                        await websocket.send_json({"type": "error", "message": str(e)})
                    continue

                if action == "command_approval_response":
                    approval_id = msg.get("approval_id")
                    approved = msg.get("approved", False)
                    command_approval_manager.resolve_approval(approval_id, approved)
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
                    
                    # Capture the session selection for persistent fallback
                    session_provider = llm_provider
                    session_model = llm_model
                    
                    # Custom Agent resolution
                    resolved_tools = allowed_tools
                    system_prompt_override = None
                    working_directory = None
                    initial_history = None
                    
                    # Resolve Tool Limitations based on Agent Profile
                    if agent_name.lower() != "kernel" and agent_name.lower() != "kernel_agent":
                        custom_agent = agent_manager.get_agent(agent_name)
                        if not custom_agent:
                            await websocket.send_json({"type": "error", "message": f"Agent {agent_name} not found"})
                            continue
                        
                        resolved_tools = custom_agent.static_tools + [f"mcp:{s}" for s in custom_agent.mcp_servers]
                        system_prompt_override = custom_agent.system_prompt
                        working_directory = custom_agent.working_directory
                        
                        # Priority: 1. Agent definition, 2. Global session selection
                        if custom_agent.provider:
                            llm_provider = custom_agent.provider
                        if custom_agent.model:
                            llm_model = custom_agent.model
                            
                        logger.info(f"Using Custom Agent: {custom_agent.name} with tools {resolved_tools}")
                    elif agent_name.lower() in ["kernel", "kernel_agent"]:
                        # Kernel Orchestrator: Dynamically inherit all system tools + delegation
                        from backend.tools.mcp_registry import system_registry
                        from backend.tools.mcp_manager import mcp_manager
                        
                        # 1. All static tools from the registry (excluding restricted ones)
                        static_names = [t["name"] for t in system_registry.list_tools() if not t.get("restricted")]
                        
                        # 2. All enabled MCP servers
                        mcp_names = [f"mcp:{s['id']}" for s in mcp_manager.list_servers() if s.get("enabled", True)]
                        
                        resolved_tools = static_names + mcp_names
                        
                        # Ensure delegation tools are included if not already (safety)
                        for essential in ["delegate_to_agent", "list_available_agents"]:
                            if essential not in resolved_tools:
                                resolved_tools.append(essential)
                                
                        system_prompt_override = KERNEL_SYSTEM_PROMPT
                        logger.info(f"Using Orchestrator Kernel: dynamically resolved {len(resolved_tools)} tools")
                    
                    # Goal Anchoring
                    original_request = msg.get("original_request") or task_text
                    
                    proc = AIProcess(
                        agent_name=agent_name,
                        task_description=task_text,
                        limits=ResourceLimits(allowed_tools=resolved_tools),
                        working_directory=working_directory,
                        original_request=original_request
                    )
                    
                    from backend.kernel.skill_injector import inject_skills_into_prompt
                    if system_prompt_override:
                        assigned_skills = custom_agent.skills if 'custom_agent' in locals() and custom_agent else None
                        proc.memory_context["system_prompt"] = inject_skills_into_prompt(system_prompt_override, working_directory, assigned_skills)
                    
                    if initial_history:
                        proc.memory_context["initial_history"] = initial_history
                    
                    if llm_provider: proc.memory_context["llm_provider"] = llm_provider
                    if llm_model: proc.memory_context["llm_model"] = llm_model
                    if session_provider: proc.memory_context["llm_session_provider"] = session_provider
                    if session_model: proc.memory_context["llm_session_model"] = session_model
                    
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
    if sys.platform == 'win32':
        asyncio.set_event_loop_policy(asyncio.WindowsProactorEventLoopPolicy())
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
