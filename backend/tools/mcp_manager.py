
import os
import json
import logging
import time
from typing import Dict, Any, List, Optional
from langchain_mcp_adapters.client import MultiServerMCPClient

logger = logging.getLogger("AgentOS.MCP.Manager")

class MCPManager:
    def __init__(self, config_path: str):
        self.config_path = config_path
        self._cache = None
        self._cache_time = 0
        self._ttl = 300  # 5 minutes
        self._ensure_config_exists()
        self._fix_mcp_paths()

    def _fix_mcp_paths(self):
        """Fixes the filesystem MCP paths to be absolute and cross-platform."""
        config = self.load_config()
        if "filesystem" in config:
            # Get the project root directory (two levels up from this file)
            project_root = os.path.abspath(os.path.join(os.path.dirname(__file__), "..", ".."))
            workspace_dir = os.path.join(project_root, "workspace")
            
            # Ensure the workspace directory exists
            os.makedirs(workspace_dir, exist_ok=True)
            
            # Update args with absolute paths
            config["filesystem"]["args"] = [
                "-y",
                "@modelcontextprotocol/server-filesystem",
                workspace_dir,
                project_root
            ]
            self.save_config(config)
            logger.info(f"Updated filesystem MCP paths: {workspace_dir}, {project_root}")

    def _ensure_config_exists(self):
        os.makedirs(os.path.dirname(self.config_path), exist_ok=True)
        if not os.path.exists(self.config_path):
            with open(self.config_path, 'w') as f:
                json.dump({}, f)

    def load_config(self) -> Dict[str, Any]:
        try:
            with open(self.config_path, 'r') as f:
                return json.load(f)
        except Exception as e:
            logger.error(f"Failed to load MCP config: {e}")
            return {}

    def save_config(self, config: Dict[str, Any]):
        try:
            with open(self.config_path, 'w') as f:
                json.dump(config, f, indent=4)
            self._cache = None  # Invalidate cache
        except Exception as e:
            logger.error(f"Failed to save MCP config: {e}")

    async def get_all_tools(self) -> list:
        now = time.time()
        if self._cache is not None and (now - self._cache_time) < self._ttl:
            return self._cache

        config = self.load_config()
        enabled_servers = {
            k: {
                "command": v["command"],
                "args": v["args"],
                "transport": v.get("transport", "stdio"),
                "env": v.get("env")
            }
            for k, v in config.items() if v.get("enabled", True)
        }

        if not enabled_servers:
            return []

        client = MultiServerMCPClient(enabled_servers)
        try:
            all_tools = await client.get_tools()
            self._cache = all_tools
            self._cache_time = now
            return all_tools
        except Exception as e:
            logger.error(f"Error fetching tools from MCP servers: {e}")
            return self._cache if self._cache else []

    def add_server(self, id: str, name: str, command: str, args: List[str], env: Optional[Dict] = None):
        config = self.load_config()
        config[id] = {
            "name": name,
            "command": command,
            "args": args,
            "transport": "stdio",
            "env": env,
            "enabled": True
        }
        self.save_config(config)

    def remove_server(self, id: str):
        config = self.load_config()
        if id in config:
            del config[id]
            self.save_config(config)

    def list_servers(self) -> List[Dict[str, Any]]:
        config = self.load_config()
        return [{"id": k, **v} for k, v in config.items()]

# Singleton instance
mcp_manager = MCPManager(os.path.join(os.path.dirname(__file__), "..", "data", "mcp_servers.json"))
