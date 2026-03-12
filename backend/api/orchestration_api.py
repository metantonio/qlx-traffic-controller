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
    # If we are an architect but couldn't detect a project, do NOT use proc.working_directory (which is the agent's home)
    # Use "workspace/default_project" so specialist work doesn't pollute the architect's home.
    ws_dir = project_folder
    if not ws_dir:
        if proc.agent_name == "software_architect":
             ws_dir = os.path.join("workspace", "default_project")
        else:
             ws_dir = proc.working_directory or "workspace"
             
    os.makedirs(ws_dir, exist_ok=True)
    
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
        # Match from "Project Plan" header until the next major header (Architecture, etc) or end
        plan_match = re.search(r"(?i)(?:#|\*\*)\s*Project Plan\s*(?:#|\*\*|:)?(.*?)(?=(?:#|\*\*)\s*Architecture|#|\*\*|$)", last_msg, re.DOTALL)
        if plan_match:
            plan_content = plan_match.group(1).strip()
            
    if not arch_content:
        # Match from "Architecture" header until next header or end
        arch_match = re.search(r"(?i)(?:#|\*\*)\s*Architecture\s*(?:#|\*\*|:)?(.*?)(?=(?:#|\*\*)\s*Conclusion|#|\*\*|$)", last_msg, re.DOTALL)
        if arch_match:
            arch_content = arch_match.group(1).strip()

    # 3. Final Fallback: if STILL empty, use the splitting logic but only as a last resort and with more caution
    if not plan_content and ("project plan" in last_msg.lower()):
        plan_parts = re.split(r"(?i)#+\s*Architecture", last_msg)
        plan_content = re.sub(r"(?i).*project plan.*", "", plan_parts[0], count=1).strip()

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
    specialists = ["backend_developer", "frontend_developer", "qa_tester"]
    target_agent = None
    
    for s in specialists:
        if s in last_msg.lower():
            target_agent = s
            break
            
    if not target_agent:
        # Fallback logic for common roles
        if "backend" in last_msg.lower(): target_agent = "backend_developer"
        elif "frontend" in last_msg.lower(): target_agent = "frontend_developer"
        elif "qa" in last_msg.lower(): target_agent = "qa_tester"
        else: target_agent = "backend_developer" # Default to backend for setup

    task_hint = "Implement the first step of the project plan."
    plan_match = re.search(r"(?:Step|Task)\s*1[:.]?\s*(.*)", last_msg, re.IGNORECASE)
    if plan_match:
        task_hint = plan_match.group(1).strip()

    # Spawn the next process
    custom_agent = agent_manager.get_agent(target_agent)
    if not custom_agent:
         raise HTTPException(status_code=404, detail=f"Target agent {target_agent} not found")

    resolved_tools = custom_agent.static_tools + [f"mcp:{s}" for s in custom_agent.mcp_servers]
    
    new_proc = AIProcess(
        agent_name=target_agent,
        task_description=f"Automated Proceed from Architect.\n\nTask: {task_hint}\n\nProject Directory: '{ws_dir}'. Read PROJECT_PLAN.md from this directory to start.",
        limits=ResourceLimits(allowed_tools=resolved_tools),
        working_directory=ws_dir # Specialists MUST work in the project folder
    )
    
    new_proc.memory_context["initial_history"] = proc.history
    new_proc.memory_context["llm_provider"] = proc.memory_context.get("llm_provider")
    new_proc.memory_context["llm_model"] = proc.memory_context.get("llm_model")
    
    await system_scheduler.submit(new_proc, Priority.MEDIUM)
    
    return {
        "status": "success", 
        "target": target_agent, 
        "new_pid": new_proc.pid,
        "hint": task_hint
    }
