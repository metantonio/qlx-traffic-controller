from backend.tools.mcp_registry import MCPTool, system_registry

async def memory_placeholder(**kwargs):
    """This is a placeholder tool. Real memory tools are loaded by the scheduler."""
    return "This tool is a placeholder. If you see this, the scheduler failed to swap it with real MCP tools."

memory_tool = MCPTool(
    name="memory_access",
    description="Enables Knowledge Graph memory. Allows creating entities, relations, and searching through past logs.",
    parameters={},
    handler=memory_placeholder
)

system_registry.register(memory_tool)
