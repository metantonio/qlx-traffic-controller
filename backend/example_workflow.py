import asyncio
from backend.core.orchestrator import AIControlTower
from backend.agents.specialized import DocumentAgent
from backend.tools.filesystem import filesystem_read_tool
import logging

logging.basicConfig(level=logging.INFO)

async def main():
    print("--- Initializing AI Control Tower ---")
    tower = AIControlTower()
    
    print("\n--- Registering Agents ---")
    doc_agent = DocumentAgent()
    tower.register_agent("document_agent", doc_agent)
    print(f"Registered {doc_agent.name} with capabilities: {doc_agent.allowed_tools}")
    
    print("\n--- Simulating User Task ---")
    task = "Analyze PDF in the workspace"
    await tower.submit_task(task)
    
    print("\n--- Simulating Agent Tool Usage ---")
    # Agent tries to read a file
    response = await tower.execute_tool_request(
        agent_name="document_agent",
        tool_name="filesystem_read",
        arguments={"filepath": "./workspace/test.txt"}
    )
    print(f"Tool execution response: {response}")
    
    print("\n--- Simulating Security Malicious Request ---")
    # Agent tries unauthorized shell tool
    response = await tower.execute_tool_request(
        agent_name="document_agent",
        tool_name="shell_execute",
        arguments={"command": "rm -rf /"}
    )
    print(f"Malicious Tool response: {response}")

if __name__ == "__main__":
    asyncio.run(main())
