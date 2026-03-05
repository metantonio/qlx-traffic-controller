import os
import logging
from typing import List
from langchain_mcp_adapters.client import MultiServerMCPClient

logger = logging.getLogger("AgentOS.MCP.Memory")

# Knowledge Graph persistence path
MEMORY_FILE = os.path.abspath(os.path.join(os.path.dirname(__file__), "..", "..", "data", "memory.json"))

import time

# Cache for tools
_MEM_TOOLS_CACHE = None
_MEM_CACHE_TIME = 0
_CACHE_TTL = 300  # 5 minutes

async def get_mcp_memory_tools() -> list:
    """
    Returns knowledge graph memory tools from the official MCP server.
    Uses MultiServerMCPClient to provide tools that handle their own session lifecycle.
    Caches tools for 5 minutes to avoid frequent npx spawns.
    """
    global _MEM_TOOLS_CACHE, _MEM_CACHE_TIME
    
    now = time.time()
    if _MEM_TOOLS_CACHE is not None and (now - _MEM_CACHE_TIME) < _CACHE_TTL:
        return _MEM_TOOLS_CACHE

    # Ensure data directory exists for memory.json
    os.makedirs(os.path.dirname(MEMORY_FILE), exist_ok=True)

    client = MultiServerMCPClient(
        {
            "memory": {
                "command": "npx",
                "args": ["-y", "@modelcontextprotocol/server-memory"],
                "env": {
                    # The memory server uses a file to persist the graph
                    "MEMORY_FILE_PATH": MEMORY_FILE
                },
                "transport": "stdio",
            }
        }
    )

    try:
        tools = await client.get_tools()
        logger.info(f"MCP memory tools loaded: {[t.name for t in tools]}")
        _MEM_TOOLS_CACHE = tools
        _MEM_CACHE_TIME = now
        return tools
    except Exception as e:
        logger.error(f"Failed to load MCP memory tools: {e}")
        return _MEM_TOOLS_CACHE if _MEM_TOOLS_CACHE else []
