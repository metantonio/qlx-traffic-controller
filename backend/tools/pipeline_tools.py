from pydantic import BaseModel
from backend.tools.mcp_registry import MCPTool, system_registry
from backend.kernel.memory_bus import system_memory_bus, MessagePayload
from backend.kernel.agent_manager import agent_manager
from backend.llm.provider import current_pid
import logging
from backend.core.logger import get_kernel_logger

logger = get_kernel_logger("QLX-TC.Tools.Pipeline")

async def set_pipeline_variable(key: str, value: str) -> str:
    """Sets a variables in the current workflow pipeline execution context."""
    pid = current_pid.get()
    logger.info(f"Setting pipeline variable: {key} = {value} (called by PID: {pid})")
    
    await system_memory_bus.publish(MessagePayload(
        source_pid=pid,
        target_pid="BROADCAST",
        event_type="set_pipeline_variable",
        data={
            "key": key,
            "value": value
        }
    ))
    return f"Variable '{key}' successfully mapped to '{value}'."

pipeline_variable_tool = MCPTool(
    name="set_pipeline_variable",
    description="Sets a variable in the workflow pipeline that can be used to dynamically change agent routing or skip conditional steps. Useful for routing agents.",
    parameters={
        "key": {
            "type": "string",
            "description": "The name of the variable to set (e.g., 'next_agent' or 'file_type')"
        },
        "value": {
            "type": "string",
            "description": "The value to assign to the variable"
        }
    },
    handler=set_pipeline_variable
)

system_registry.register(pipeline_variable_tool)

async def list_available_agents() -> str:
    """Lists all available specialized agents in the system and their descriptions."""
    agents = agent_manager.list_agents()
    if not agents:
        return "No specialized agents found. Only the default 'kernel_agent' is available."
    
    result = "Available Agents:\n\n"
    for agent in agents:
        result += f"- ID: {agent.id}\n  Name: {agent.name}\n  Description: {agent.description}\n\n"
        
    return result

list_agents_tool = MCPTool(
    name="list_available_agents",
    description="Lists all available specialized agents in the system, their IDs, and what they do. Use this to determine which agent to route a task to.",
    parameters={},
    handler=list_available_agents
)

system_registry.register(list_agents_tool)
