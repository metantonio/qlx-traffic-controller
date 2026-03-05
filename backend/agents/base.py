from typing import List, Dict, Any, Callable
import uuid

class BaseAgent:
    """Base class defining identity, role, and capabilities for an AI Agent."""
    
    def __init__(self, name: str, role: str, system_prompt: str, allowed_tools: List[str] = None):
        self.id = str(uuid.uuid4())
        self.name = name
        self.role = role
        self.system_prompt = system_prompt
        self.allowed_tools = allowed_tools or []
        self.metadata = {}
        
    def to_dict(self):
        return {
            "id": self.id,
            "name": self.name,
            "role": self.role,
            "allowed_tools": self.allowed_tools
        }

    async def execute_task(self, task_input: str, orchestrator_callback: Callable):
        """Execute a general workflow, implemented by subclasses."""
        raise NotImplementedError("Subclasses must implement execute_task")

class AgentRegistry:
    """Central registry to manage all active system agents."""
    
    def __init__(self):
        self._agents: Dict[str, BaseAgent] = {}
        
    def register(self, agent: BaseAgent):
        self._agents[agent.name] = agent
        
    def list_agents(self) -> List[Dict]:
        return [a.to_dict() for a in self._agents.values()]
        
    def get_agent(self, name: str) -> BaseAgent:
        return self._agents.get(name)
