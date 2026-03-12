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

logger = get_kernel_logger("QLX-TC.Tools.Agents")

async def delegate_to_agent(agent_id: str, task: str) -> str:
    """Delegates a specific sub-task to another specialized agent or skill."""
    pid = current_pid.get()
    logger.info(f"Agent {pid} delegating to {agent_id}: {task}")
    
    agent = agent_manager.get_agent(agent_id)
    if not agent and agent_id.lower() != "kernel":
        return f"Error: Agent or Skill '{agent_id}' not found. Use list_available_agents to see what exists."
    
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
    
    new_proc = AIProcess(
        agent_name=agent_id,
        task_description=task,
        limits=ResourceLimits(allowed_tools=resolved_tools),
        working_directory=working_directory
    )
    
    from backend.kernel.skill_injector import inject_skills_into_prompt
    if system_prompt:
        assigned_skills = agent.skills if agent else None
        new_proc.memory_context["system_prompt"] = inject_skills_into_prompt(system_prompt, working_directory, assigned_skills)
    if provider:
        new_proc.memory_context["llm_provider"] = provider
    if model:
        new_proc.memory_context["llm_model"] = model
    
    from backend.kernel.process import system_process_table
    parent_proc = system_process_table.get(pid) if pid else None
    if parent_proc and parent_proc.history:
        new_proc.memory_context["initial_history"] = parent_proc.history
        # Carry over provider settings for consistency
        new_proc.memory_context["llm_session_provider"] = parent_proc.memory_context.get("llm_session_provider")
        new_proc.memory_context["llm_session_model"] = parent_proc.memory_context.get("llm_session_model")
    
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
        result += f"- {agent.id}: {agent.name} ({agent.description})\n"
    
    if authorized_ids:
        result += "\nNote: As the Architect, your view is focused on the core development assembly line."
    
    return result

list_agents_tool = MCPTool(
    name="list_available_agents",
    description="Returns a list of all specialized agents and skills that you can delegate tasks to.",
    parameters={},
    handler=list_available_agents
)

system_registry.register(delegate_tool)
system_registry.register(list_agents_tool)
