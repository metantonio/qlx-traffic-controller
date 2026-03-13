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
    project_name_match = re.search(r"(?i)(?:Project Name|Project Plan):\s*([a-zA-Z0-9_\-\s]+?)(?:\r?\n|$)", last_msg)
    if not project_name_match:
        # Fallback 1: look for "developing [Name] game" or similar phrasings
        project_name_match = re.search(r"(?i)developing\s+([a-zA-Z0-9_\-\s]+)\s+(?:game|app|system|project|software)", last_msg)
    
    # Fallback 2: Check history for successful list_directory calls if naming fails
    audited_path = None
    if not project_name_match:
        for msg in reversed(proc.history):
            if msg.get("role") == "assistant" and msg.get("tool_calls"):
                for tc in msg["tool_calls"]:
                    # Look for list_directory or filesystem_read to the workspace
                    if tc.get("name") in ["list_directory", "filesystem_list"]:
                        args = tc.get("args") or tc.get("arguments") or {}
                        path = args.get("path") or args.get("directory_path")
                        if path and "workspace" in path.lower():
                            audited_path = path
                            logger.info(f"Recovered audited path from history: {audited_path}")
                            break
                if audited_path: break
        
    project_folder = None
    if project_name_match:
        # Normalize: strip, lowercase, and replace spaces/hyphens with underscores
        raw_name = project_name_match.group(1).strip()
        normalized_name = re.sub(r"[\s\-]+", "_", raw_name).lower()
        project_folder = os.path.join("workspace", normalized_name)
    
    # FAIL-SAFE ws_dir logic
    ws_dir = project_folder
    if not ws_dir and audited_path:
        ws_dir = audited_path
        
    if not ws_dir:
        ws_dir = "workspace/default_project"
             
    # Ensure it's absolute relative to the CURRENT WORKING DIRECTORY of the backend
    ws_dir = os.path.abspath(ws_dir)
    os.makedirs(ws_dir, exist_ok=True)
    
    # Windows IO overhead / Race condition protection
    import time
    time.sleep(0.1)

    if not os.path.exists(ws_dir):
        logger.error(f"CRITICAL: Failed to initialize workspace at {ws_dir}")
        raise HTTPException(status_code=500, detail=f"Failed to create workspace directory at {ws_dir}")

    logger.info(f"Workspace verified at {ws_dir}")
    
    def clean_block(text: str) -> str:
        if not text: return ""
        # Remove JSON tool call blocks
        text = re.sub(r"\{[\s\n]*\"name\"[\s\n]*:[\s\n]*\"[^\"]+\"[\s\n\*,]*\"arguments\"[\s\n\*:].*?\}", "", text, flags=re.DOTALL)
        text = re.sub(r"```json.*?```", "", text, flags=re.DOTALL)
        # Remove empty markdown headers or trailing noise
        text = re.sub(r"^(?:#|\*\*)+\s*$", "", text, flags=re.MULTILINE)
        return text.strip()

    # 1. Source of Truth: Look for files on disk FIRST
    plan_path = os.path.join(ws_dir, "PROJECT_PLAN.md")
    arch_path = os.path.join(ws_dir, "ARCHITECTURE.md")
    
    disk_plan = ""
    disk_arch = ""
    
    if os.path.exists(plan_path):
        with open(plan_path, 'r', encoding='utf-8') as f:
            disk_plan = clean_block(f.read())
            if disk_plan: 
                plan_content = disk_plan
                logger.info(f"Loaded valid PROJECT_PLAN from disk at {plan_path}")
            
    if os.path.exists(arch_path):
        with open(arch_path, 'r', encoding='utf-8') as f:
            disk_arch = clean_block(f.read())
            if disk_arch:
                arch_content = disk_arch
                logger.info(f"Loaded valid ARCHITECTURE from disk at {arch_path}")

    # 2. Fallback: Parse from message content if disk files are missing or resulted in empty after cleanup
    if not plan_content or not arch_content:
        blocks = re.findall(r"```(?:markdown)?\n(.*?)\n```", last_msg, re.DOTALL)
        if blocks:
            for block in blocks:
                cleaned_block_content = clean_block(block)
                if not cleaned_block_content: continue
                    
                lower_block = block.lower()
                if not plan_content and ("project plan" in lower_block or "step 1" in lower_block):
                    plan_content = cleaned_block_content
                elif not arch_content and ("architecture" in lower_block or "component" in lower_block):
                    arch_content = cleaned_block_content
                    
            # Final raw fallback (preserving existing logic)
            if not plan_content and blocks:
                plan_content = clean_block(blocks[0])
        
        # Header-based extraction if markdown blocks failed
        if not plan_content:
            plan_match = re.search(r"(?is)(?:#|\*\*)\s*(?:Step\s+1|Plan|Implementation|Requirements|Developing).*?(?=(?:#|\*\*)\s*Architecture|(?:\n\s*Conclusion)|$)", last_msg)
            if plan_match:
                plan_content = clean_block(plan_match.group(0))
                
        if not arch_content:
            arch_match = re.search(r"(?is)(?:#|\*\*)\s*(?:Architecture|Structure).*?(?=(?:\n\s*Conclusion)|$)", last_msg)
            if arch_match:
                arch_content = clean_block(arch_match.group(0))

    # 3. Final Fallback: if STILL empty, use the whole message as plan base
    if not plan_content:
        plan_content = clean_block(last_msg)
    
    if not arch_content:
        # If no architecture was found, we don't want to leave it empty if there's info in the plan
        arch_content = "See PROJECT_PLAN.md for structure."

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
ORIGINAL_GOAL: '{proc.original_request or "N/A"}'
CURRENT_WD: '{ws_dir}'

### PROJECT SNAPSHOT (CURRENT FILES)
{project_snapshot}

### PROJECT GUIDELINES
PROJECT_PLAN:
{plan_content}

ARCHITECTURE:
{arch_content}

### ASSIGNMENT
Task: {task_hint}
(Requirement: Use your tools to implement this specific task. Look at the existing files in SNAPSHOT before creating new ones.)
""",
        limits=ResourceLimits(allowed_tools=resolved_tools),
        working_directory=ws_dir,
        original_request=proc.original_request
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
