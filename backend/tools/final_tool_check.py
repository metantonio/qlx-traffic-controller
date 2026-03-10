import asyncio
import logging
import sys
import os

# Set up logging to stdout
logging.basicConfig(level=logging.ERROR)

# Ensure backend is in path
sys.path.append(os.getcwd())

from langchain_mcp_adapters.client import MultiServerMCPClient

async def test_pkgs():
    pkgs = {
        "wikipedia": "wikipedia-mcp",
        "fetch": "fetch-mcp"
    }
    for name, pkg in pkgs.items():
        print(f"\n--- {name} ({pkg}) ---")
        try:
            client = MultiServerMCPClient({name: {"command": "npx", "args": ["-y", pkg], "transport": "stdio"}})
            tools = await client.get_tools()
            print(f"Tools: {[t.name for t in tools]}")
        except Exception as e:
            print(f"Error: {e}")

if __name__ == "__main__":
    asyncio.run(test_pkgs())
