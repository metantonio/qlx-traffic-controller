
import os
import sys
import json
from typing import Optional, List
from pydantic import BaseModel

# Mocking the AgentManager logic to test without full imports if needed, 
# but let's try to use the real ones first.
sys.path.append(os.getcwd())

from backend.kernel.agent_manager import agent_manager, CustomAgent

def test_persistence():
    print("Listing existing agents...")
    agents = agent_manager.list_agents()
    print(f"Count: {len(agents)}")
    
    # Pick one to edit
    if not agents:
        print("No agents to edit. Creating one.")
        agent = CustomAgent(
            id="test-agent",
            name="Test Agent",
            description="Testing persistence",
            system_prompt="You are a test agent."
        )
    else:
        agent = agents[0]
        print(f"Editing agent: {agent.id}")
        agent.description = f"Updated at {os.times().elapsed}"
    
    print(f"Saving agent {agent.id}...")
    agent_manager.add_agent(agent)
    
    print("Reloading agents from disk...")
    # Force a reload by creating a new manager or just calling load_agents if it's not cached
    # The current AgentManager doesn't cache the dictionary itself except in add_agent's local scope
    new_agents = agent_manager.load_agents()
    if agent.id in new_agents:
        updated_agent = new_agents[agent.id]
        print(f"Found agent in reloaded map. Description: {updated_agent.description}")
        if updated_agent.description == agent.description:
            print("SUCCESS: Persistence verified.")
        else:
            print("FAILURE: Description mismatch.")
    else:
        print("FAILURE: Agent not found after reload.")

if __name__ == "__main__":
    test_persistence()
