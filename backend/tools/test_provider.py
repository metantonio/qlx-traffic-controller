import asyncio
import sys
import os

# Ensure backend is in path
sys.path.append(os.getcwd())

from backend.llm.provider import LLMProvider

# Mock a tool
class MockTool:
    def __init__(self, name, description):
        self.name = name
        self.description = description
    
    async def ainvoke(self, args):
        return f"Mock tool {self.name} executed with {args}"

async def test_provider():
    llm = LLMProvider(provider="ollama", model="qwen2.5-coder:7b")
    
    # Force it to think it has a fetch tool
    tools = [MockTool("fetch", "Fetch a URL")]
    
    system_prompt = "You are a helpful assistant."
    user_prompt = "Summarize https://example.com. Output EXACTLY this JSON block:\n{\"name\": \"fetch\", \"arguments\": {\"url\": \"https://example.com\"}}"
    
    print("Calling aexecute_agent...")
    res_text, messages = await llm.aexecute_agent(
        system_prompt=system_prompt,
        user_prompt=user_prompt,
        tools=tools
    )
    
    print(f"\nResult text: {res_text}")
    print("\nMessages sequence:")
    for m in messages:
        print(f"{m.get('role', 'unknown')}: {m.get('content', '')[:100]} | tools: {m.get('tool_calls', 'None')}")

if __name__ == "__main__":
    asyncio.run(test_provider())
