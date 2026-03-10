import asyncio
import logging
import sys
import os

# Set up logging to stdout
logging.basicConfig(level=logging.INFO)

# Ensure backend is in path
sys.path.append(os.getcwd())

from langchain_mcp_adapters.client import MultiServerMCPClient

async def main():
    print("Testing wikipedia server...")
    try:
        config = {
            "wikipedia": {
                "command": "npx",
                "args": ["-y", "@modelcontextprotocol/server-wikipedia"],
                "transport": "stdio"
            }
        }
        client = MultiServerMCPClient(config)
        tools = await client.get_tools()
        print(f"Success! Found {len(tools)} tools:")
        for t in tools:
            print(f" - {t.name}")
    except Exception as e:
        print(f"Error: {e}")

if __name__ == "__main__":
    asyncio.run(main())
