import os
import json
import logging
import time
from typing import Dict, Any, List, Optional
from langchain_mcp_adapters.client import MultiServerMCPClient
from cryptography.fernet import Fernet
from backend.core.database import SessionLocal, init_db
from backend.models.database_models import DbMCPServer
from backend.core.config import settings

logger = logging.getLogger("QLX.MCP.Manager")

class MCPManager:
    def __init__(self, config_path: str):
        self.config_path = config_path
        self._cache = None
        self._cache_time = 0
        self._ttl = 300  # 5 minutes
        self.store_path = os.path.join(os.path.dirname(self.config_path), "mcp_store.json")
        
        # Initialize encryption
        if not settings.ENCRYPTION_KEY:
            logger.warning("ENCRYPTION_KEY not set in .env. MCP secrets will not be encrypted!")
            self.fernet = None
        else:
            try:
                self.fernet = Fernet(settings.ENCRYPTION_KEY.encode())
            except Exception as e:
                logger.error(f"Failed to initialize Fernet with ENCRYPTION_KEY: {e}")
                self.fernet = None

        init_db()
        self._migrate_from_json()
        self._fix_mcp_paths()

    def _encrypt(self, data: dict) -> Optional[str]:
        if not data:
            return None
        if not self.fernet:
            return json.dumps(data)
        return self.fernet.encrypt(json.dumps(data).encode()).decode()

    def _decrypt(self, encrypted_str: Optional[str]) -> dict:
        if not encrypted_str:
            return {}
        if not self.fernet:
            try:
                return json.loads(encrypted_str)
            except:
                return {}
        try:
            decrypted = self.fernet.decrypt(encrypted_str.encode()).decode()
            return json.loads(decrypted)
        except Exception as e:
            # Fallback: maybe it was saved as plain json before encryption was enabled
            try:
                return json.loads(encrypted_str)
            except:
                logger.error(f"Failed to decrypt MCP env: {e}")
                return {}

    def _migrate_from_json(self):
        """Migrates data from mcp_servers.json to the database if the file exists."""
        if not os.path.exists(self.config_path):
            return

        try:
            with open(self.config_path, 'r', encoding='utf-8') as f:
                config = json.load(f)

            if not config:
                return

            with SessionLocal() as db:
                for server_id, data in config.items():
                    # Check if already exists
                    existing = db.query(DbMCPServer).filter(DbMCPServer.id == server_id).first()
                    if not existing:
                        new_server = DbMCPServer(
                            id=server_id,
                            name=data.get("name", server_id),
                            command=data.get("command", ""),
                            args=data.get("args", []),
                            env_encrypted=self._encrypt(data.get("env", {})),
                            enabled=1 if data.get("enabled", True) else 0,
                            transport=data.get("transport", "stdio")
                        )
                        db.add(new_server)
                db.commit()

            # Backup and remove the old file
            bak_path = self.config_path + ".bak"
            if os.path.exists(bak_path):
                os.remove(bak_path)
            os.rename(self.config_path, bak_path)
            logger.info(f"Migrated MCP config from JSON to DB. Original backed up to {bak_path}")
        except Exception as e:
            logger.error(f"Failed to migrate MCP JSON to DB: {e}")

    def refresh_store(self, registry_url: str = "https://raw.githubusercontent.com/modelcontextprotocol/servers/main/index.json"):
        """Fetches and merges external MCP servers into the store."""
        try:
            import requests
            response = requests.get(registry_url, timeout=10)
            if response.status_code == 200:
                external_data = response.json()
                os.makedirs(os.path.dirname(self.store_path), exist_ok=True)
                if not os.path.exists(self.store_path):
                    current_store = {"mcp": {}, "skills": {}}
                else:
                    with open(self.store_path, 'r', encoding='utf-8') as f:
                        current_store = json.load(f)
                
                if "mcp" not in current_store:
                    current_store = {"mcp": current_store, "skills": {}}
                
                for key, value in external_data.items():
                    if key not in current_store["mcp"]:
                        current_store["mcp"][key] = value
                
                with open(self.store_path, 'w', encoding='utf-8') as f:
                    json.dump(current_store, f, indent=4)
                return True, f"Synchronized {len(external_data)} MCP servers."
            return False, f"Registry returned {response.status_code}"
        except Exception as e:
            return False, str(e)

    def refresh_clawhub_skills(self):
        """Fetches skills from ClawHub API."""
        try:
            import requests
            url = "https://clawhub.ai/api/v1/skills"
            response = requests.get(url, timeout=10)
            if response.status_code == 200:
                data = response.json()
                skills = data.get("items", [])
                
                os.makedirs(os.path.dirname(self.store_path), exist_ok=True)
                if not os.path.exists(self.store_path):
                    current_store = {"mcp": {}, "skills": {}}
                else:
                    with open(self.store_path, 'r', encoding='utf-8') as f:
                        current_store = json.load(f)
                
                if "skills" not in current_store:
                    current_store["skills"] = {}
                
                for skill in skills:
                    slug = skill.get("slug")
                    current_store["skills"][slug] = {
                        "name": skill.get("displayName", slug),
                        "description": skill.get("summary", ""),
                        "type": "skill",
                        "source": "clawhub",
                        "metadata": skill
                    }
                
                with open(self.store_path, 'w', encoding='utf-8') as f:
                    json.dump(current_store, f, indent=4)
                return True, f"Synchronized {len(skills)} skills from ClawHub."
            return False, f"ClawHub returned {response.status_code}"
        except Exception as e:
            return False, str(e)

    def fetch_clawhub_page(self, page: int = 1, page_size: int = 15):
        """Fetches a specific page of skills from ClawHub."""
        try:
            import requests
            url = f"https://clawhub.ai/api/v1/skills?page={page}&limit={page_size}"
            response = requests.get(url, timeout=10)
            if response.status_code == 200:
                data = response.json()
                items = data.get("items", [])
                
                results = {}
                for skill in items:
                    slug = skill.get("slug")
                    results[slug] = {
                        "name": skill.get("displayName", slug),
                        "description": skill.get("summary", ""),
                        "type": "skill",
                        "source": "clawhub",
                        "metadata": skill
                    }
                return {
                    "items": results,
                    "total": data.get("total", len(items)),
                    "pages": data.get("pages", 1),
                    "current_page": page
                }
            return {"items": {}, "error": f"ClawHub returned {response.status_code}"}
        except Exception as e:
            logger.error(f"Failed to fetch ClawHub page {page}: {e}")
            return {"items": {}, "error": str(e)}

    def _fix_mcp_paths(self):
        """Fixes MCP server paths in the database."""
        project_root = os.path.abspath(os.path.join(os.path.dirname(__file__), "..", ".."))
        
        with SessionLocal() as db:
            # Filesystem
            fs = db.query(DbMCPServer).filter(DbMCPServer.id == "filesystem").first()
            if fs:
                workspace_dir = os.path.join(project_root, "workspace")
                os.makedirs(workspace_dir, exist_ok=True)
                fs.args = ["-y", "@modelcontextprotocol/server-filesystem", workspace_dir, project_root]
            
            # Excel
            excel = db.query(DbMCPServer).filter(DbMCPServer.id == "excel").first()
            if excel:
                python_exe = "python.exe" if os.name == "nt" else "python"
                venv_path = os.path.join(project_root, "backend", "venv", "Scripts" if os.name == "nt" else "bin", python_exe)
                excel_path = os.path.join(project_root, "backend", "servers", "sv-excel-agent")
                
                excel.command = venv_path
                env = self._decrypt(excel.env_encrypted)
                env["PYTHONPATH"] = excel_path
                excel.env_encrypted = self._encrypt(env)
            
            db.commit()

    async def get_all_tools(self) -> list:
        now = time.time()
        if self._cache is not None and (now - self._cache_time) < self._ttl:
            return self._cache

        with SessionLocal() as db:
            servers = db.query(DbMCPServer).filter(DbMCPServer.enabled == 1).all()
            enabled_servers = [
                {
                    "id": s.id,
                    "command": s.command,
                    "args": s.args,
                    "transport": s.transport,
                    "env": self._decrypt(s.env_encrypted)
                }
                for s in servers
            ]

        if not enabled_servers:
            return []

        from langchain_mcp_adapters.client import MultiServerMCPClient
        
        def fix_command(cmd):
            if os.name == "nt" and cmd == "npx":
                return "npx.cmd"
            return cmd

        all_tools = []
        for server_info in enabled_servers:
            try:
                # Initialize a single-server client for resilience
                server_id = server_info["id"]
                client_config = {
                    server_id: {
                        "command": fix_command(server_info["command"]),
                        "args": server_info["args"],
                        "transport": server_info.get("transport", "stdio"),
                        "env": server_info.get("env")
                    }
                }
                client = MultiServerMCPClient(client_config)
                server_tools = await client.get_tools()
                all_tools.extend(server_tools)
                logger.info(f"Loaded {len(server_tools)} tools from MCP server: {server_id}")
            except Exception as e:
                # Log failure but continue with other servers
                logger.error(f"Failed to load tools from MCP server '{server_info['id']}': {e}")

        if all_tools:
            self._cache = all_tools
            self._cache_time = now
            
        return all_tools if all_tools else (self._cache if self._cache else [])

    def add_server(self, id: str, name: str, command: str, args: List[str], env: Optional[Dict] = None):
        with SessionLocal() as db:
            server = DbMCPServer(
                id=id,
                name=name,
                command=command,
                args=args,
                env_encrypted=self._encrypt(env) if env else None,
                enabled=1,
                transport="stdio"
            )
            db.merge(server)
            db.commit()
            self._cache = None

    def remove_server(self, id: str):
        with SessionLocal() as db:
            db.query(DbMCPServer).filter(DbMCPServer.id == id).delete()
            db.commit()
            self._cache = None

    def toggle_server(self, id: str, enabled: bool):
        with SessionLocal() as db:
            server = db.query(DbMCPServer).filter(DbMCPServer.id == id).first()
            if server:
                server.enabled = 1 if enabled else 0
                db.commit()
                self._cache = None

    def list_servers(self) -> List[Dict[str, Any]]:
        with SessionLocal() as db:
            servers = db.query(DbMCPServer).all()
            return [
                {
                    "id": s.id,
                    "name": s.name,
                    "command": s.command,
                    "args": s.args,
                    "enabled": bool(s.enabled),
                    "transport": s.transport,
                    "env": self._decrypt(s.env_encrypted)
                }
                for s in servers
            ]

    def load_store(self) -> Dict[str, Any]:
        try:
            if os.path.exists(self.store_path):
                with open(self.store_path, 'r', encoding='utf-8') as f:
                    data = json.load(f)
                    if "mcp" in data or "skills" in data:
                        return data
                    return {"mcp": data, "skills": {}}
            return {"mcp": {}, "skills": {}}
        except Exception as e:
            logger.error(f"Failed to load MCP store: {e}")
            return {"mcp": {}, "skills": {}}

    def install_from_store(self, server_id: str, overrides: Optional[Dict] = None):
        store_data = self.load_store()
        mcp_store = store_data.get("mcp", {})
        
        if server_id not in mcp_store:
            raise ValueError(f"Server {server_id} not found in store")
        
        server_data = mcp_store[server_id].copy()
        
        if overrides:
            new_args = []
            final_env = server_data.get("env", {}) or {}
            
            for arg in server_data.get("args", []):
                new_arg = arg
                for key, value in overrides.items():
                    placeholder = f"YOUR_{key.upper()}_KEY"
                    if placeholder in new_arg:
                        new_arg = new_arg.replace(placeholder, value)
                    elif key.upper() in new_arg and ("YOUR_" in new_arg or "TOKEN" in new_arg):
                        new_arg = value
                    
                    # Also handle overrides into ENV if specified in store or by common pattern
                    if key.upper() in ["API_KEY", "TOKEN", "SECRET"]:
                        final_env[key.upper()] = value
                new_args.append(new_arg)
            
            server_data["args"] = new_args
            server_data["env"] = final_env

        self.add_server(
            id=server_id,
            name=server_data["name"],
            command=server_data["command"],
            args=server_data["args"],
            env=server_data.get("env")
        )

# Singleton instance
mcp_manager = MCPManager(os.path.join(os.path.dirname(__file__), "..", "data", "mcp_servers.json"))
