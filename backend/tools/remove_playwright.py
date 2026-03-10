import json
import os
import sys

# Ensure backend is in path
sys.path.append(os.getcwd())

agents_file = "backend/data/custom_agents.json"
try:
    with open(agents_file, "r", encoding="utf-8") as f:
        data = json.load(f)
        
    for agent in data:
        if "playwright" in agent.get("mcp_servers", []):
            agent["mcp_servers"].remove("playwright")
            print(f"Removed playwright from {agent.get('name')}")
            
    with open(agents_file, "w", encoding="utf-8") as f:
        json.dump(data, f, indent=4)
        
except Exception as e:
    print(f"Failed to fix custom agents: {e}")
