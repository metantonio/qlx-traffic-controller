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


import time

# Cache for tools
_FS_TOOLS_CACHE = None
_FS_CACHE_TIME = 0
_CACHE_TTL = 300  # 5 minutes

async def get_mcp_filesystem_tools(allowed_directories: List[str] = None) -> list:
    """
    Returns filesystem tools from the official MCP server.
    Uses MultiServerMCPClient to provide tools that handle their own session lifecycle.
    Caches tools for 5 minutes to avoid frequent npx spawns.
    """
    global _FS_TOOLS_CACHE, _FS_CACHE_TIME
    
    now = time.time()
    if _FS_TOOLS_CACHE is not None and (now - _FS_CACHE_TIME) < _CACHE_TTL:
        return _FS_TOOLS_CACHE

    dirs = allowed_directories or _DEFAULT_ALLOWED
    for d in dirs:
        os.makedirs(d, exist_ok=True)

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
        tools = await client.get_tools()
        logger.info(f"MCP filesystem tools loaded: {[t.name for t in tools]}")
        _FS_TOOLS_CACHE = tools
        _FS_CACHE_TIME = now
        return tools
    except Exception as e:
        logger.error(f"Failed to load MCP filesystem tools: {e}")
        return _FS_TOOLS_CACHE if _FS_TOOLS_CACHE else []
