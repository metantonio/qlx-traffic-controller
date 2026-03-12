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
    project_name_match = re.search(r"(?i)Project Name:\s*([a-zA-Z0-9_-]+)", last_msg)
    if not project_name_match:
        # Fallback: look for "developing [Name] game" or similar
        project_name_match = re.search(r"(?i)developing\s+([a-zA-Z0-9_-]+)\s+game", last_msg)
        
    project_folder = None
    if project_name_match:
        project_name = project_name_match.group(1).lower().replace(" ", "_")
        project_folder = os.path.join("workspace", project_name)
    
    # FAIL-SAFE ws_dir logic
    ws_dir = project_folder or proc.working_directory or "workspace"
    os.makedirs(ws_dir, exist_ok=True)
    
    plan_content = ""
    arch_content = ""
    
    # Simple extraction logic: find sections or content between header hints
    if "project plan" in last_msg.lower() or "PROJECT_PLAN.md" in last_msg:
        # Try to extract from "Project Plan" to "Architecture" or end
        plan_part = re.split(r"(?i)architecture", last_msg)[0]
        # Clean up common lead-ins
        plan_part = re.sub(r"(?i).*project plan.*", "", plan_part, count=1)
        plan_content = plan_part.strip()
    
    # Robust fallback: Find ANY markdown block if no headers matched
    if not plan_content:
        blocks = re.findall(r"```(?:markdown)?\n(.*?)\n```", last_msg, re.DOTALL)
        if blocks:
            # If multiple blocks, first is likely plan, second is arch
            plan_content = blocks[0].strip()
            if len(blocks) > 1:
                arch_content = blocks[1].strip()

    if "architecture" in last_msg.lower() or "ARCHITECTURE.md" in last_msg:
        arch_parts = re.split(r"(?i)architecture", last_msg)
        if len(arch_parts) > 1:
            arch_content = arch_parts[1].split("Conclusion")[0].strip()
            # Clean up common lead-ins
            arch_content = re.sub(r"(?i)^.*architecture.*", "", arch_content, count=1)

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
