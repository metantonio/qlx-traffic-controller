
import os
import sys
import json
import time

sys.path.append(os.getcwd())
from backend.kernel.agent_manager import agent_manager, CustomAgent

def test_delayed_persistence():
    agent_id = "persistence-test-agent"
    timestamp = str(time.time())
    
    print(f"Creating/Updating agent {agent_id} with timestamp {timestamp}...")
    agent = CustomAgent(
        id=agent_id,
        name="Persistence Test",
        description=f"Persistent since {timestamp}",
        system_prompt="Test"
    )
    agent_manager.add_agent(agent)
    
    # Wait 5 seconds
    print("Waiting 5 seconds for any potential background sync/overwrite...")
    time.sleep(5)
    
    print("Reloading...")
    new_agents = agent_manager.load_agents()
    if agent_id in new_agents:
        if new_agents[agent_id].description == agent.description:
            print("SUCCESS: Data is still correct after delay.")
        else:
            print(f"FAILURE: Data CHANGED! Expected {agent.description}, found {new_agents[agent_id].description}")
    else:
        print("FAILURE: Agent DISAPPEARED after delay.")

if __name__ == "__main__":
    test_delayed_persistence()
