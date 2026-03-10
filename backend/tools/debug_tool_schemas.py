import asyncio
import logging
import sys
import os
import traceback
import json

# Set up logging
logging.basicConfig(level=logging.INFO)
logger = logging.getLogger("DEBUG_SCHEMA")

# Ensure backend is in path
sys.path.append(os.getcwd())

from langchain_mcp_adapters.client import MultiServerMCPClient

async def debug_schema(name, pkg):
    print(f"\n--- Debugging Schema for {name} ({pkg}) ---")
    try:
        command = "npx.cmd" if os.name == "nt" else "npx"
        client = MultiServerMCPClient({
            name: {
                "command": command,
                "args": ["-y", pkg],
                "transport": "stdio"
            }
        })
        tools = await client.get_tools()
        print(f"✅ Success! Found {len(tools)} tools.")
        for t in tools:
            print(f"\nTool: {t.name}")
            print(f"Description: {t.description}")
            print(f"Args Type: {type(t.args_schema)}")
            try:
                if hasattr(t.args_schema, "schema"):
                    print(f"Schema: {json.dumps(t.args_schema.schema(), indent=2)}")
                else:
                    print(f"Schema (Raw): {t.args_schema}")
            except Exception as schema_err:
                print(f"❌ Error getting schema for {t.name}: {schema_err}")
    except Exception as e:
        print(f"❌ Failed to get tools for {name}: {e}")
        traceback.print_exc()

async def main():
    # Only test the ones we suspect or use
    await debug_schema("wikipedia", "wikipedia-mcp")
    await debug_schema("fetch", "fetch-mcp")

if __name__ == "__main__":
    asyncio.run(main())
