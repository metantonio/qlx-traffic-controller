from typing import Dict, Any, Optional
from backend.tools.mcp_registry import MCPTool, system_registry
from backend.kernel.scheduler import system_scheduler, Priority
from backend.kernel.process import AIProcess, ResourceLimits, ProcessState
from backend.kernel.agent_manager import agent_manager
from backend.llm.provider import current_pid
import logging
import asyncio
import time
from backend.core.logger import get_kernel_logger
from backend.kernel.supervisor import system_supervisor
from backend.kernel.soul import system_soul_manager

logger = get_kernel_logger("QLX-TC.Tools.Agents")

async def delegate_to_agent(agent_id: str, task: str) -> str:
    """Delegates a specific sub-task to another specialized agent or skill."""
    pid = current_pid.get()
    logger.info(f"Agent {pid} delegating to {agent_id}: {task}")
    
    agent = agent_manager.get_agent(agent_id)
    if not agent and agent_id.lower() != "kernel":
        available = agent_manager.list_agents()
        ids = [a.id for a in available]
        return f"Error: Agent or Skill '{agent_id}' not found. Valid IDs: {', '.join(ids)}. STOP hallucinating and use one of these."
    
    # Construction of the new process
    # If it's a custom agent, we resolve its tools
    resolved_tools = ["shell_execute", "filesystem_read"]
    system_prompt = None
    provider = None
    model = None
    working_directory = None
    
    if agent:
        resolved_tools = agent.static_tools + [f"mcp:{s}" for s in agent.mcp_servers]
        system_prompt = agent.system_prompt
        provider = agent.provider
        model = agent.model
        working_directory = agent.working_directory
    
    from backend.kernel.process import system_process_table
    parent_proc = system_process_table.get(pid) if pid else None

    # WD Inheritance Logic:
    # 1. Favor explicitly provided 'working_directory' in agent config
    # 2. BUT, if parent is already in a specific 'workspace/project' folder, 
    #    inherit that project root as the context for the delegation.
    effective_wd = working_directory
    if parent_proc and parent_proc.working_directory:
        # If parent is in a sub-workspace (like a project folder), and 
        # the current default is just a generic home, prefer the parent's project context.
        parent_wd = parent_proc.working_directory
        if "workspace/" in parent_wd.lower() and parent_wd != "workspace":
            # If the child agent doesn't have a specific isolated home, 
            # or if its home is just a top-level category, inherit the project folder.
            if not effective_wd or effective_wd in ["workspace", "workspace/frontend", "workspace/backend", "workspace/qa_tester"]:
                effective_wd = parent_wd

    new_proc = AIProcess(
        agent_name=agent_id,
        task_description=f"{system_soul_manager.read_soul(effective_wd or (parent_proc.working_directory if parent_proc else None))}\n{task}",
        limits=ResourceLimits(allowed_tools=resolved_tools),
        working_directory=effective_wd,
        original_request=parent_proc.original_request if parent_proc else None
    )
    
    from backend.kernel.skill_injector import inject_skills_into_prompt
    if system_prompt:
        assigned_skills = agent.skills if agent else None
        # Anchoring the goal in the system prompt via skill injection or direct append
        base_prompt = inject_skills_into_prompt(system_prompt, working_directory, assigned_skills)
        if parent_proc and parent_proc.original_request:
            base_prompt = f"### ORIGINAL USER REQUEST (GOAL ANCHOR):\n{parent_proc.original_request}\n\n{base_prompt}"
        new_proc.memory_context["system_prompt"] = base_prompt
    
    if provider:
        new_proc.memory_context["llm_provider"] = provider
    if model:
        new_proc.memory_context["llm_model"] = model
        
    if parent_proc and parent_proc.history:
        new_proc.memory_context["initial_history"] = parent_proc.history
        # Carry over provider settings for consistency
        new_proc.memory_context["llm_session_provider"] = parent_proc.memory_context.get("llm_session_provider")
        new_proc.memory_context["llm_session_model"] = parent_proc.memory_context.get("llm_session_model")
    
    # --- ARCHITECT APPROVAL GATE ---
    if parent_proc and parent_proc.agent_name == "software_architect":
        if not parent_proc.has_proceeded:
            logger.warning(f"Architect {pid} attempted auto-delegation before plan approval. Blocking.")
            return "ERROR: Delegation blocked. You must FIRST present your PLAN and ARCHITECTURE to the user in a chat message. Do NOT call delegate_to_agent until the user has clicked 'Proceed' in the UI. For now, just describe what you plan to do, write the plan/arch files, and then wait for user feedback."
    
    # Capture initial snapshot for the new process for physical validation
    system_supervisor.take_snapshot(new_proc.pid, working_directory or new_proc.working_directory)
    
    await system_scheduler.submit(new_proc, Priority.MEDIUM)
    
    # Wait for completion (Timeout 300s to allow LLM loading)
    start_wait = time.time()
    while new_proc.state in [ProcessState.QUEUED, ProcessState.RUNNING]:
        if time.time() - start_wait > 300:
            return f"Delegation Timeout: Agent {agent_id} is taking too long. Ongoing PID: {new_proc.pid}."
        await asyncio.sleep(1)
    
    if new_proc.state == ProcessState.COMPLETED:
        # Fetch the last message from the delegated process history
        if new_proc.history:
            last_msg = new_proc.history[-1]
            return f"Result from {agent_id}:\n\n{last_msg['content']}"
        return f"Agent {agent_id} completed but returned no content."
    else:
        reason = new_proc.memory_context.get("failure_reason", "Unknown error")
        return f"Agent {agent_id} failed: {reason}"

delegate_tool = MCPTool(
    name="delegate_to_agent",
    description="Delegates a sub-task to a specialized agent or skill by ID. ALWAYS use 'list_available_agents' FIRST to get the correct valid IDs. Use this when you need specific expertise that you do not want to handle directly.",
    parameters={
        "agent_id": {
            "type": "string",
            "description": "The ID of the specialized agent or skill to use."
        },
        "task": {
            "type": "string",
            "description": "The specific task or prompt to send to the specialized agent."
        }
    },
    handler=delegate_to_agent
)

async def list_available_agents() -> str:
    """Lists all available specialized agents and skills currently installed."""
    from backend.kernel.process import system_process_table
    pid = current_pid.get()
    current_proc = system_process_table.get(pid) if pid else None
    
    agents = agent_manager.list_agents()
    if not agents:
        return "No specialized agents or skills found."
    
    # Filtering logic for Software Architect focus
    authorized_ids = None
    if current_proc and current_proc.agent_name == "software_architect":
        authorized_ids = ["frontend_developer", "backend_developer", "qa_tester"]
        # Filter for only authorized specialists
        agents = [a for a in agents if a.id in authorized_ids]
    
    result = "Available Specialized Agents & Skills:\n"
    for agent in agents:
        skills_str = f", Skills: {', '.join(agent.skills)}" if agent.skills else ""
        result += f"- {agent.id}: {agent.name} ({agent.description}{skills_str})\n"
    
    if authorized_ids:
        result += "\nNote: As the Architect, your view is focused on the core development assembly line."
    
    return result

list_agents_tool = MCPTool(
    name="list_available_agents",
    description="Returns a list of all specialized agents and skills that you can delegate tasks to.",
    parameters={},
    handler=list_available_agents
)

async def task_complete(reason: str = "Task finished successfully.") -> str:
    """Signals that the agent has completed its assigned task and is ready to exit."""
    pid = current_pid.get()
    from backend.kernel.process import system_process_table, ProcessState
    proc = system_process_table.get(pid)
    if proc:
        # SUPERVISOR GATE: Physical truth check
        is_valid, validation_msg = system_supervisor.validate_completion(pid, proc.working_directory)
        if not is_valid:
            # Reflection Loop Layer
            retries = proc.memory_context.get("completion_retries", 0)
            if retries < 3:
                proc.memory_context["completion_retries"] = retries + 1
                logger.warning(f"Process {pid} ({proc.agent_name}) completion rejected (Attempt {retries+1}): {validation_msg}")
                return (
                    f"{validation_msg}\n\n"
                    "### AUTONOMOUS REFLECTION REQUIRED\n"
                    "Your task completion was REJECTED by the Supervisor Kernel truth-layer.\n"
                    "Reason: No relevant physical changes detected in the workspace.\n"
                    "ACTION: Reflect on why your previous actions didn't result in code changes. "
                    "Did you forget to call 'filesystem_write'? Did you only update documentation?\n"
                    "Please RETRY your work and ensure you produce physical code output before calling 'task_complete' again."
                )
            
            logger.error(f"Process {pid} ({proc.agent_name}) completion rejected after {retries} retries. Failing.")
            return f"FINAL REJECTION: {validation_msg}. You have failed to produce physical output after multiple attempts. Please explain the blockage to the Architect."

        proc.complete()
        
        # Soul Update: Distill learnings from completion reason
        if proc.working_directory:
            system_soul_manager.update_soul(proc.working_directory, reason)

        logger.info(f"Process {pid} ({proc.agent_name}) signalled completion: {reason} | {validation_msg}")
        return f"TASK_COMPLETE: {reason} | {validation_msg}"
    return "Error: Process not found."

task_complete_tool = MCPTool(
    name="task_complete",
    description="Signals that you have finished your assigned task. CALL THIS TOOL as your FINAL ACTION. Do NOT output a concluding message after this.",
    parameters={
        "reason": {
            "type": "string",
            "description": "Short summary of what was accomplished."
        }
    },
    handler=task_complete
)

system_registry.register(task_complete_tool)
system_registry.register(delegate_tool)
system_registry.register(list_agents_tool)
