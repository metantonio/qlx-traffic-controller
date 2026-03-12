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

    # FAIL-SAFE: Extract and Save Documentation if Architect hasn't done it
    # We look for Markdown sections or the words "PROJECT_PLAN.md" etc.
    ws_dir = proc.working_directory or "workspace"
    os.makedirs(ws_dir, exist_ok=True)
    
    plan_content = ""
    arch_content = ""
    
    # Simple extraction logic: find sections or content between header hints
    if "project plan" in last_msg.lower():
        # Try to extract from "Project Plan" to "Architecture" or end
        plan_part = re.split(r"(?i)architecture", last_msg)[0]
        plan_content = plan_part.strip()
    
    if "architecture" in last_msg.lower():
        arch_parts = re.split(r"(?i)architecture", last_msg)
        if len(arch_parts) > 1:
            arch_content = arch_parts[1].split("Conclusion")[0].strip()

    # Save files directly to avoid empty files
    if plan_content:
        plan_path = os.path.join(ws_dir, "PROJECT_PLAN.md")
        with open(plan_path, 'w', encoding='utf-8') as f:
            f.write(plan_content)
        logger.info(f"Fail-safe: Saved PROJECT_PLAN.md to {plan_path}")

    if arch_content:
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
        task_description=f"Automated Proceed from Architect.\n\nTask: {task_hint}\n\nDocumentation has been saved to '{ws_dir}'. Read PROJECT_PLAN.md to start.",
        limits=ResourceLimits(allowed_tools=resolved_tools),
        working_directory=custom_agent.working_directory or ws_dir
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
