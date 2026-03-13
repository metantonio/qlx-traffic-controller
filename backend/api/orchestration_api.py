from fastapi import APIRouter, HTTPException, Depends
from sqlalchemy.orm import Session
from backend.core.database import get_db
from backend.kernel.process import system_process_table, AIProcess, ResourceLimits
from backend.kernel.scheduler import system_scheduler, Priority
from backend.kernel.agent_manager import agent_manager
from backend.core.logger import get_kernel_logger
import re
import os
import json

logger = get_kernel_logger("QLX-TC.Orchestration")

router = APIRouter(prefix="/api/processes", tags=["orchestration"])

def get_project_snapshot(startpath: str) -> str:
    """Generates a recursive string representation of the project structure."""
    snapshot = []
    for root, dirs, files in os.walk(startpath):
        # Skip common folders to keep context small
        dirs[:] = [d for d in dirs if d not in ['.git', '__pycache__', 'node_modules', 'venv', '.agents']]
        
        level = root.replace(startpath, '').count(os.sep)
        indent = ' ' * 4 * level
        snapshot.append(f"{indent}{os.path.basename(root)}/")
        subindent = ' ' * 4 * (level + 1)
        for f in files:
            snapshot.append(f"{subindent}{f}")
    return "\n".join(snapshot)

@router.post("/{pid}/proceed")
async def proceed_with_plan(pid: str):
    """
    Analyzes the last message of a process (typically Architect) 
    and triggers the first suggested delegation step.
    """
    proc = system_process_table.get(pid)
    if not proc:
        raise HTTPException(status_code=404, detail="Process not found")
    
    if not proc.history:
        raise HTTPException(status_code=400, detail="No history found to proceed from")
        
    last_msg = None
    for msg in reversed(proc.history):
        if msg["role"] == "assistant":
            last_msg = msg["content"]
            break
            
    if not last_msg:
        raise HTTPException(status_code=400, detail="No assistant message found to parse")

    # DYNAMIC PROJECT DETECTION
    # We try to find a project name to avoid cluttering the Architect's home or root workspace
    # Support spaces and capture common phrasings
    project_name_match = re.search(r"(?i)Project Name:\s*([a-zA-Z0-9_\-\s]+)", last_msg)
    if not project_name_match:
        # Fallback: look for "developing [Name] game" or similar phrasings
        project_name_match = re.search(r"(?i)developing\s+([a-zA-Z0-9_\-\s]+)\s+(?:game|app|system|project|software)", last_msg)
        
    project_folder = None
    if project_name_match:
        # Normalize: strip, lowercase, and replace spaces/hyphens with underscores
        raw_name = project_name_match.group(1).strip()
        normalized_name = re.sub(r"[\s\-]+", "_", raw_name).lower()
        project_folder = os.path.join("workspace", normalized_name)
    
    # FAIL-SAFE ws_dir logic
    ws_dir = project_folder
    if not ws_dir:
        ws_dir = "workspace/default_project"
             
    # Ensure it's absolute relative to the CURRENT WORKING DIRECTORY of the backend
    ws_dir = os.path.abspath(ws_dir)
    os.makedirs(ws_dir, exist_ok=True)
    
    if not os.path.exists(ws_dir):
        logger.error(f"CRITICAL: Failed to initialize workspace at {ws_dir}")
        raise HTTPException(status_code=500, detail=f"Failed to create workspace directory at {ws_dir}")

    logger.info(f"Workspace verified at {ws_dir}")
    
    plan_content = ""
    arch_content = ""
    
    # 1. Look for explicit Markdown blocks FIRST (Highest Signal)
    blocks = re.findall(r"```(?:markdown)?\n(.*?)\n```", last_msg, re.DOTALL)
    if blocks:
        for block in blocks:
            lower_block = block.lower()
            if "project plan" in lower_block or "step 1" in lower_block:
                plan_content = block.strip()
            elif "architecture" in lower_block or "component" in lower_block:
                arch_content = block.strip()
                
        # Fallback if roles weren't identified in blocks
        if not plan_content and blocks:
            plan_content = blocks[0].strip()
        if not arch_content and len(blocks) > 1:
            arch_content = blocks[1].strip()

    # 2. If no markdown blocks, try header-based extraction (Mid Signal)
    if not plan_content:
        # Match from "Step 1" or "Project Plan" or "Requirements" until Architecture or end
        # We use a broad lookahead to avoid cutting off at words like 'architecture' in lowercase narrative
        plan_match = re.search(r"(?is)(?:#|\*\*)\s*(?:Step\s+1|Plan|Implementation|Requirements|Developing).*?(?=(?:#|\*\*)\s*Architecture|(?:\n\s*Conclusion)|$)", last_msg)
        if plan_match:
            plan_content = plan_match.group(0).strip()
            
    if not arch_content:
        # Match from "Architecture" header until next header or end
        arch_match = re.search(r"(?is)(?:#|\*\*)\s*(?:Architecture|Structure).*?(?=(?:\n\s*Conclusion)|$)", last_msg)
        if arch_match:
            arch_content = arch_match.group(0).strip()

    # 3. Final Fallback: if STILL empty, use the whole message as plan base
    if not plan_content:
        plan_content = last_msg.strip()

    # Save files directly to avoid empty files
    if plan_content and len(plan_content) > 10: # Only save if we found actual content
        plan_path = os.path.join(ws_dir, "PROJECT_PLAN.md")
        with open(plan_path, 'w', encoding='utf-8') as f:
            f.write(plan_content)
        logger.info(f"Fail-safe: Saved PROJECT_PLAN.md to {plan_path}")

    if arch_content and len(arch_content) > 10:
        arch_path = os.path.join(ws_dir, "ARCHITECTURE.md")
        with open(arch_path, 'w', encoding='utf-8') as f:
            f.write(arch_content)
        logger.info(f"Fail-safe: Saved ARCHITECTURE.md to {arch_path}")

    # Identify target specialist
    # Use keyword analysis for smarter defaults
    specialists = ["backend_developer", "frontend_developer", "qa_tester"]
    target_agent = None
    
    # 1. Look for explicit mentions of agent IDs
    for s in specialists:
        if s in last_msg.lower():
            target_agent = s
            break
            
    # 2. Keyword-based inference if no specific agent was mentioned
    if not target_agent:
        low_msg = last_msg.lower()
        frontend_keywords = ["frontend", "ui", "style", "css", "html", "react", "game", "canvas", "graphic", "display", "screen", "frontend_developer"]
        backend_keywords = ["backend", "api", "database", "model", "schema", "server", "python", "fastapi", "logic", "route", "backend_developer"]
        
        # Check for UI/Frontend signals
        if any(k in low_msg for k in frontend_keywords):
            target_agent = "frontend_developer"
        elif any(k in low_msg for k in backend_keywords):
            target_agent = "backend_developer"
        elif "test" in low_msg or "qa" in low_msg:
            target_agent = "qa_tester"
        else:
            # Default fallback
            target_agent = "backend_developer"

    task_hint = "Implement the first step of the project plan."
    plan_match = re.search(r"(?:Step|Task)\s*1[:.]?\s*(.*)", last_msg, re.IGNORECASE)
    if plan_match:
        task_hint = plan_match.group(1).strip()

    # Spawn the next process
    custom_agent = agent_manager.get_agent(target_agent)
    if not custom_agent:
         raise HTTPException(status_code=404, detail=f"Target agent {target_agent} not found")

    resolved_tools = custom_agent.static_tools + [f"mcp:{s}" for s in custom_agent.mcp_servers]
    
    project_snapshot = get_project_snapshot(ws_dir)

    new_proc = AIProcess(
        agent_name=target_agent,
        task_description=f"""### ENVIRONMENT METADATA (MANDATORY)
PROJECT_DIR: '{ws_dir}'
PROJECT_NAME: '{normalized_name if project_name_match else "default_project"}'
CURRENT_WD: '{ws_dir}'

### PROJECT SNAPSHOT (CURRENT FILES)
{project_snapshot}

### ASSIGNMENT
Task: {task_hint}

### WORKFLOW INSTRUCTIONS
1. Read `PROJECT_PLAN.md` in '{ws_dir}'. 
2. implement the logical component described in the plan. 
3. If core files (index.html, package.json, etc.) are missing in the project folder, you MUST create them.
4. ONLY operate within '{ws_dir}'. Generic placeholders like '/path/to/your/...' are FORBIDDEN and will trigger a system error.
""",
        limits=ResourceLimits(allowed_tools=resolved_tools),
        working_directory=ws_dir # Specialists MUST work in the project folder
    )
    
    new_proc.memory_context["initial_history"] = proc.history
    new_proc.memory_context["llm_provider"] = proc.memory_context.get("llm_provider")
    new_proc.memory_context["llm_model"] = proc.memory_context.get("llm_model")
    
    # Mark parent as proceeded to hide button in UI
    proc.has_proceeded = True
    system_process_table.register(proc)
    
    await system_scheduler.submit(new_proc, Priority.MEDIUM)
    
    return {
        "status": "success", 
        "target": target_agent, 
        "new_pid": new_proc.pid,
        "hint": task_hint
    }

@router.get("/pending")
async def get_pending_plans():
    """Returns a count or list of processes that have a pending plan."""
    pending = []
    for pid, proc in system_process_table.processes.items():
        if proc.agent_name == "software_architect" and not proc.has_proceeded:
            pending.append({
                "pid": proc.pid,
                "agent": proc.agent_name,
                "task": proc.task_description
            })
    return {"pending": pending, "count": len(pending)}
