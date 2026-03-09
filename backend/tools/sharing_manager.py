import json
import os
import time
from typing import List, Dict, Any, Optional
from backend.tools.mcp_manager import mcp_manager
from backend.core.database import SessionLocal
from backend.models.database_models import DbMCPServer

class SharingManager:
    def __init__(self, agents_path: str, workflows_path: str):
        self.agents_path = agents_path
        self.workflows_path = workflows_path

    def _load_json(self, path: str) -> Dict:
        if os.path.exists(path):
            with open(path, 'r', encoding='utf-8') as f:
                return json.load(f)
        return {}

    def _save_json(self, path: str, data: Dict):
        with open(path, 'w', encoding='utf-8') as f:
            json.dump(data, f, indent=4)

    def export_bundle(self, agent_ids: List[str] = None, workflow_ids: List[str] = None, mcp_ids: List[str] = None) -> Dict[str, Any]:
        bundle = {
            "version": "1.0",
            "timestamp": time.time(),
            "agents": [],
            "workflows": [],
            "mcp_servers": []
        }

        # 1. Export Agents
        if agent_ids:
            all_agents = self._load_json(self.agents_path)
            for aid in agent_ids:
                if aid in all_agents:
                    agent_data = all_agents[aid].copy()
                    bundle["agents"].append(agent_data)
                    # Automatically track required MCP servers
                    for mcp_id in agent_data.get("mcp_servers", []):
                        if not mcp_ids: mcp_ids = []
                        if mcp_id not in mcp_ids:
                            mcp_ids.append(mcp_id)

        # 2. Export Workflows
        if workflow_ids:
            all_workflows = self._load_json(self.workflows_path)
            for wid in workflow_ids:
                if wid in all_workflows:
                    bundle["workflows"].append(all_workflows[wid])

        # 3. Export MCP Servers (Sanitized)
        if mcp_ids:
            with SessionLocal() as db:
                for mid in mcp_ids:
                    server = db.query(DbMCPServer).filter(DbMCPServer.id == mid).first()
                    if server:
                        # SANITIZATION: Never export env_encrypted
                        server_data = {
                            "id": server.id,
                            "name": server.name,
                            "command": server.command,
                            "args": server.args,
                            "transport": server.transport,
                            "enabled": bool(server.enabled),
                            "env_schema": {} # Could potentially extract keys from args placeholders
                        }
                        
                        # Identify required keys from args placeholders (e.g. YOUR_OPENAI_KEY)
                        for arg in server.args:
                            if "YOUR_" in arg:
                                key_name = arg.split("YOUR_")[-1].split("_")[0] # Rough extraction
                                server_data["env_schema"][key_name] = "Required API Key/Token"
                        
                        bundle["mcp_servers"].append(server_data)

        return bundle

    def import_bundle(self, bundle: Dict[str, Any], overrides: Dict[str, Any] = None) -> Dict[str, Any]:
        results = {"agents": 0, "workflows": 0, "mcp_servers": 0}
        
        # 1. Import MCP Servers first (Dependencies)
        for s_data in bundle.get("mcp_servers", []):
            # Apply overrides to args if provided
            final_args = s_data["args"]
            final_env = {}
            if overrides:
                new_args = []
                for arg in final_args:
                    new_arg = arg
                    for key, val in overrides.items():
                        placeholder = f"YOUR_{key.upper()}_KEY"
                        if placeholder in new_arg:
                            new_arg = new_arg.replace(placeholder, val)
                        elif key.upper() in new_arg and ("YOUR_" in new_arg or "TOKEN" in new_arg):
                            new_arg = val
                        
                        # Also track as env var if it looks like a key
                        if key.upper() in ["API_KEY", "TOKEN", "SECRET", "PASSWORD"]:
                            final_env[key.upper()] = val
                    new_args.append(new_arg)
                final_args = new_args

            mcp_manager.add_server(
                id=s_data["id"],
                name=s_data["name"],
                command=s_data["command"],
                args=final_args,
                env=final_env if final_env else None
            )
            results["mcp_servers"] += 1

        # 2. Import Agents
        if bundle.get("agents"):
            all_agents = self._load_json(self.agents_path)
            for agent in bundle["agents"]:
                all_agents[agent["id"]] = agent
                results["agents"] += 1
            self._save_json(self.agents_path, all_agents)

        # 3. Import Workflows
        if bundle.get("workflows"):
            all_workflows = self._load_json(self.workflows_path)
            for workflow in bundle["workflows"]:
                all_workflows[workflow["id"]] = workflow
                results["workflows"] += 1
            self._save_json(self.workflows_path, all_workflows)

        return results

# Singleton
sharing_manager = SharingManager(
    agents_path=os.path.join(os.path.dirname(__file__), "..", "data", "custom_agents.json"),
    workflows_path=os.path.join(os.path.dirname(__file__), "..", "data", "workflows.json")
)
