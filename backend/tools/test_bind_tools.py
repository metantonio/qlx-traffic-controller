import asyncio
import logging
import sys
import os

logging.basicConfig(level=logging.INFO)
sys.path.append(os.getcwd())

from langchain_mcp_adapters.client import MultiServerMCPClient
from langchain_ollama import ChatOllama

async def test_binding():
    try:
        command = "npx.cmd" if os.name == "nt" else "npx"
        client = MultiServerMCPClient({
            "wikipedia": {
                "command": command,
                "args": ["-y", "wikipedia-mcp"],
                "transport": "stdio"
            }
        })
        tools = await client.get_tools()
        print(f"Got {len(tools)} tools from MCP.")
        
        llm = ChatOllama(model="qwen2.5-coder:7b", base_url="http://127.0.0.1:11434")
        print("Binding tools to Ollama...")
        llm_with_tools = llm.bind_tools(tools)
        print("✅ Successfully bound tools.")
    except Exception as e:
        import traceback
        print(f"❌ Error binding tools: {e}")
        traceback.print_exc()

if __name__ == "__main__":
    asyncio.run(test_binding())
