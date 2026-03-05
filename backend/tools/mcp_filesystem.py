"""
MCP Filesystem Bridge
=====================
Connects to the official Anthropic MCP filesystem server
(@modelcontextprotocol/server-filesystem) using MultiServerMCPClient.

This approach allows the client to automatically manage session lifecycles
on each tool call, which is much more robust than manual session management.
"""

import os
import logging
from typing import List
from langchain_mcp_adapters.client import MultiServerMCPClient

logger = logging.getLogger("AgentOS.MCP.Filesystem")

# Default allowed directories
_DEFAULT_ALLOWED = [
    os.path.abspath(os.path.join(os.path.dirname(__file__), "..", "..", "workspace")),
    os.path.abspath(os.path.join(os.path.dirname(__file__), "..", "..")),  # project root
]


async def get_mcp_filesystem_tools(allowed_directories: List[str] = None) -> list:
    """
    Returns filesystem tools from the official MCP server.
    Uses MultiServerMCPClient to provide tools that handle their own session lifecycle.
    """
    dirs = allowed_directories or _DEFAULT_ALLOWED
    for d in dirs:
        os.makedirs(d, exist_ok=True)

    # Note: MultiServerMCPClient will start a new session for each tool invocation.
    client = MultiServerMCPClient(
        {
            "filesystem": {
                "command": "npx",
                "args": ["-y", "@modelcontextprotocol/server-filesystem"] + dirs,
                "transport": "stdio",
            }
        }
    )

    try:
        # get_tools returns a list of BaseTool objects
        tools = await client.get_tools()
        logger.info(f"MCP filesystem tools loaded: {[t.name for t in tools]}")
        return tools
    except Exception as e:
        logger.error(f"Failed to load MCP filesystem tools: {e}")
        return []
