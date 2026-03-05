import asyncio
from typing import Dict, Any, List
from backend.core.security import SafetyValidator

class OrchestratorEvent:
    def __init__(self, type: str, source: str, payload: dict):
        self.type = type
        self.source = source
        self.payload = payload

class AIControlTower:
    """Central Orchestrator routing requests between agents, tools, and users."""
    
    def __init__(self):
        self.security = SafetyValidator()
        self.active_agents = {}
        self.event_queue = asyncio.Queue()
        self.subscribers = []  # For WebSocket broadcasting
        
    def register_agent(self, agent_name: str, agent_instance):
        self.active_agents[agent_name] = agent_instance
        
    async def subscribe(self, callback):
        self.subscribers.append(callback)
        
    async def publish_event(self, event: OrchestratorEvent):
        """Publish an event to all subscribers (e.g., dashboard via WS)."""
        for callback in self.subscribers:
            try:
                await callback(event.__dict__)
            except Exception as e:
                pass # Handle disconnected clients
                
    async def submit_task(self, task_description: str, target_agent: str = None) -> str:
        """Submit a task to the queue for processing."""
        await self.publish_event(OrchestratorEvent(
            type="task_received",
            source="user",
            payload={"task": task_description, "target": target_agent}
        ))
        
        # Placeholder for agent routing logic
        return "Task accepted."

    async def execute_tool_request(self, agent_name: str, tool_name: str, arguments: dict):
        """Every tool request from an agent MUST pass through this method."""
        
        await self.publish_event(OrchestratorEvent(
            type="tool_requested",
            source=agent_name,
            payload={"tool": tool_name, "arguments": arguments}
        ))
        
        # 1. Permission check based on agent scope
        agent = self.active_agents.get(agent_name)
        if not agent:
            return {"error": f"Agent {agent_name} not registered"}
            
        if tool_name not in agent.allowed_tools:
            error_msg = f"SECURITY ALERT: Agent {agent_name} attempted to use unauthorized tool {tool_name}"
            await self.publish_event(OrchestratorEvent(type="security_alert", source="orchestrator", payload={"message": error_msg}))
            return {"error": error_msg}
            
        # 2. Invoke the Tool Registry (to be implemented)
        return {"status": "success", "result": f"Executed mock {tool_name}"}
