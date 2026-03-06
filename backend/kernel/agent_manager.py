import os
import json
from typing import Dict, Any, List, Optional
from pydantic import BaseModel
from backend.core.logger import get_kernel_logger

logger = get_kernel_logger("QLX-TC.Agent.Manager")

class CustomAgent(BaseModel):
    id: str
    name: str
    description: str
    system_prompt: Optional[str] = None
    mcp_servers: List[str] = [] # List of server IDs
    static_tools: List[str] = [] # List of static tool names (eg. shell_execute)
    provider: Optional[str] = None
    model: Optional[str] = None

class AgentManager:
    def __init__(self, config_path: str):
        self.config_path = config_path
        self._ensure_config_exists()

    def _ensure_config_exists(self):
        os.makedirs(os.path.dirname(self.config_path), exist_ok=True)
        if not os.path.exists(self.config_path):
            with open(self.config_path, 'w') as f:
                json.dump({}, f)

    def load_agents(self) -> Dict[str, CustomAgent]:
        try:
            with open(self.config_path, 'r') as f:
                data = json.load(f)
                return {k: CustomAgent(**v) for k, v in data.items()}
        except Exception as e:
            logger.error(f"Failed to load custom agents: {e}")
            return {}

    def save_agents(self, agents: Dict[str, CustomAgent]):
        try:
            with open(self.config_path, 'w') as f:
                json.dump({k: v.model_dump() for k, v in agents.items()}, f, indent=4)
        except Exception as e:
            logger.error(f"Failed to save custom agents: {e}")

    def get_agent(self, agent_id: str) -> Optional[CustomAgent]:
        agents = self.load_agents()
        return agents.get(agent_id)

    def add_agent(self, agent: CustomAgent):
        agents = self.load_agents()
        agents[agent.id] = agent
        self.save_agents(agents)

    def remove_agent(self, agent_id: str):
        agents = self.load_agents()
        if agent_id in agents:
            del agents[agent_id]
            self.save_agents(agents)

    def list_agents(self) -> List[CustomAgent]:
        agents = self.load_agents()
        return list(agents.values())

# Singleton instance
agent_manager = AgentManager(os.path.join(os.path.dirname(__file__), "..", "data", "custom_agents.json"))
