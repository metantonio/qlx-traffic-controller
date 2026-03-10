import os
import sys
import json
from typing import List

# Add the project root to sys.path to allow imports from backend
sys.path.append(os.getcwd())

from backend.tools.sharing_manager import sharing_manager
from backend.core.database import SessionLocal
from backend.models.database_models import DbMCPServer

def generate_seed():
    print("Generating seed bundle from current configuration...")
    
    # 1. Collect Agent IDs
    try:
        with open(sharing_manager.agents_path, 'r', encoding='utf-8') as f:
            agents_data = json.load(f)
            agent_ids = list(agents_data.keys())
    except Exception as e:
        print(f"Error loading agents: {e}")
        agent_ids = []

    # 2. Collect Workflow IDs
    try:
        with open(sharing_manager.workflows_path, 'r', encoding='utf-8') as f:
            workflows_data = json.load(f)
            workflow_ids = list(workflows_data.keys())
    except Exception as e:
        print(f"Error loading workflows: {e}")
        workflow_ids = []

    # 3. Collect Skill IDs
    try:
        with open(sharing_manager.skills_path, 'r', encoding='utf-8') as f:
            skills_data = json.load(f)
            skill_ids = list(skills_data.keys())
    except Exception as e:
        print(f"Error loading skills: {e}")
        skill_ids = []

    # 4. Collect Enabled MCP Server IDs from DB
    mcp_ids = []
    try:
        with SessionLocal() as db:
            servers = db.query(DbMCPServer).filter(DbMCPServer.enabled == 1).all()
            mcp_ids = [s.id for s in servers]
    except Exception as e:
        print(f"Error loading MCP servers from DB: {e}")

    # 5. Export using sharing_manager
    bundle = sharing_manager.export_bundle(
        agent_ids=agent_ids,
        workflow_ids=workflow_ids,
        skill_ids=skill_ids,
        mcp_ids=mcp_ids
    )

    # 6. Save to default_bundle.json
    seed_dir = os.path.join("backend", "data", "seed")
    os.makedirs(seed_dir, exist_ok=True)
    seed_path = os.path.join(seed_dir, "default_bundle.json")
    
    with open(seed_path, 'w', encoding='utf-8') as f:
        json.dump(bundle, f, indent=4)
    
    print(f"Successfully generated seed bundle at {seed_path}")
    print(f"Agents: {len(bundle['agents'])}")
    print(f"Workflows: {len(bundle['workflows'])}")
    print(f"Skills: {len(bundle['skills'])}")
    print(f"MCP Servers: {len(bundle['mcp_servers'])}")

if __name__ == "__main__":
    generate_seed()
