import asyncio
import logging
import sys
import os

# Set up logging to stdout
logging.basicConfig(level=logging.INFO)

# Ensure backend is in path
sys.path.append(os.getcwd())

from backend.tools.mcp_manager import mcp_manager
from langchain_mcp_adapters.client import MultiServerMCPClient

async def test_server(s_id, config):
    print(f"\n--- Testing Server: {s_id} ---")
    try:
        client = MultiServerMCPClient({s_id: config})
        tools = await client.get_tools()
        print(f"✅ Success! Found {len(tools)} tools: {[t.name for t in tools]}")
    except Exception as e:
        print(f"❌ Failed: {type(e).__name__}: {e}")

async def main():
    servers = mcp_manager.list_servers()
    enabled_servers = [s for s in servers if s.get("enabled")]
    
    print(f"Found {len(enabled_servers)} enabled servers.")
    
    for s in enabled_servers:
        config = {
            "command": s["command"],
            "args": s["args"],
            "transport": s.get("transport", "stdio"),
            "env": s.get("env")
        }
        await test_server(s["id"], config)

if __name__ == "__main__":
    asyncio.run(main())
