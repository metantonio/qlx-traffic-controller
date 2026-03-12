from fastapi import APIRouter, HTTPException, Depends
from sqlalchemy.orm import Session
from backend.core.database import get_db
from backend.kernel.process import system_process_table, AIProcess, ResourceLimits
from backend.kernel.scheduler import system_scheduler, Priority
from backend.kernel.agent_manager import agent_manager
from backend.core.logger import get_kernel_logger
import re

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

    # ORCHESTRATION STRATEGY 1: Detect "Permission Loop" (Asking to save files)
    if "would you like me to" in last_msg.lower() and ("create" in last_msg.lower() or "save" in last_msg.lower()) and "md" in last_msg.lower():
        logger.info(f"Detected permission loop for {pid}. Re-triggering architect with auto-confirm.")
        # We re-trigger the SAME process but add a system hint to force execution
        proc.task_description += "\n\n[SYSTEM ACTION: USER CLICKED PROCEED. SAVE THE FILES NOW USING TOOLS.]"
        proc.state = Priority.MEDIUM # Actually we need to re-submit
        await system_scheduler.submit(proc, Priority.HIGH)
        return {
            "status": "success",
            "action": "re_triggered",
            "message": "Forced Architect to execute plan."
        }

    # ORCHESTRATION STRATEGY 2: delegation
    specialists = ["backend_developer", "frontend_developer", "qa_tester"]
    target_agent = None
    
    for s in specialists:
        if s in last_msg.lower():
            target_agent = s
            break
            
    if not target_agent:
        # Fallback to first developer found if any
        if "backend" in last_msg.lower(): target_agent = "backend_developer"
        elif "frontend" in last_msg.lower(): target_agent = "frontend_developer"
        elif "qa" in last_msg.lower() or "test" in last_msg.lower(): target_agent = "qa_tester"

    if not target_agent:
        raise HTTPException(status_code=422, detail="Could not identify a clear next step or agent from the conversation.")

    # Try to extract a task snippet
    # e.g., "Step 1: Set up the project structure" -> "Set up the project structure"
    task_hint = "Execute next step from project plan"
    plan_match = re.search(r"(?:Step|Task)\s*1[:.]?\s*(.*)", last_msg, re.IGNORECASE)
    if plan_match:
        task_hint = plan_match.group(1).strip()
    elif "delegate" in last_msg.lower():
        # Look for sentences containing 'delegate' and 'to'
        delegate_match = re.search(r"delegate.*to.*(?:the\s+)?(\w+ developer|qa tester).*", last_msg, re.IGNORECASE)
        if delegate_match:
            task_hint = f"Proceed with delegation as suggested: {delegate_match.group(0)}"

    logger.info(f"Proceeding from {pid} to {target_agent} with task hint: {task_hint}")

    # Spawn the next process
    custom_agent = agent_manager.get_agent(target_agent)
    if not custom_agent:
         raise HTTPException(status_code=404, detail=f"Target agent {target_agent} not found")

    resolved_tools = custom_agent.static_tools + [f"mcp:{s}" for s in custom_agent.mcp_servers]
    
    new_proc = AIProcess(
        agent_name=target_agent,
        task_description=f"Task from Architect: {task_hint}\n\nContext from Plan: {last_msg[:500]}...",
        limits=ResourceLimits(allowed_tools=resolved_tools),
        working_directory=custom_agent.working_directory
    )
    
    # Inject history so the sub-agent knows what happened
    new_proc.memory_context["initial_history"] = proc.history
    
    # LLM Settings from parent if available
    new_proc.memory_context["llm_provider"] = proc.memory_context.get("llm_provider")
    new_proc.memory_context["llm_model"] = proc.memory_context.get("llm_model")
    
    await system_scheduler.submit(new_proc, Priority.MEDIUM)
    
    return {
        "status": "success", 
        "target": target_agent, 
        "new_pid": new_proc.pid,
        "hint": task_hint
    }
