from typing import List, Dict, Callable, Any

class MCPTool:
    """Represents a capability accessible by an Agent via the Model Context Protocol."""
    
    def __init__(self, name: str, description: str, parameters: Dict[str, Any], handler: Callable):
        self.name = name
        self.description = description
        self.parameters = parameters
        self._handler = handler
        
    async def execute(self, **kwargs) -> Any:
        # Here we could potentially add pre-execution hooks or logging
        return await self._handler(**kwargs)

class ToolRegistry:
    """Central registry of all tools available to the system."""
    
    def __init__(self):
        self._tools: Dict[str, MCPTool] = {}
        
    def register(self, tool: MCPTool):
        self._tools[tool.name] = tool
        
    def get_tool(self, name: str) -> MCPTool:
        return self._tools.get(name)

    def list_tools(self) -> List[Dict[str, Any]]:
        return [
            {
                "name": tool.name, 
                "description": tool.description, 
                "parameters": tool.parameters
            } for tool in self._tools.values()
        ]

# Global registry
system_registry = ToolRegistry()
