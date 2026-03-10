import asyncio
import logging
import sys
import os

# Set up logging to stdout
logging.basicConfig(level=logging.INFO)

# Ensure backend is in path
sys.path.append(os.getcwd())

from backend.tools.mcp_manager import mcp_manager

async def main():
    print("Fetching tools from enabled MCP servers...")
    try:
        tools = await mcp_manager.get_all_tools()
        print(f"Loaded {len(tools)} tools:")
        for t in tools:
            print(f" - {t.name}")
    except Exception as e:
        print(f"Error: {e}")

if __name__ == "__main__":
    asyncio.run(main())
