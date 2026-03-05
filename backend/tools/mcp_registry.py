from typing import List, Dict, Callable, Any
from langchain.tools import Tool
import asyncio

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
        
    def to_langchain_tool(self) -> Tool:
        """Converts the MCPTool to a native LangChain Tool structure."""
        
        # LangChain tools expect synchronous calls by default in this context
        # We wrap the asyncio handler in a synchronous runner
        def sync_wrapper(tool_input: str) -> str:
            # Simple assumption: for now, shell and fs tools take a single primary param
            first_param = list(self.parameters.keys())[0] if self.parameters else "input"
            coro = self.execute(**{first_param: tool_input})
            
            try:
                loop = asyncio.get_event_loop()
                if loop.is_running():
                    # Running inside an active loop (e.g. FastAPI)
                    # For safety in nested loops, we might need nest_asyncio or running as an ainvoke task
                    import nest_asyncio
                    nest_asyncio.apply()
                    return str(loop.run_until_complete(coro))
                else:
                    return str(asyncio.run(coro))
            except Exception as e:
                return f"Error executing tool {self.name}: {str(e)}"

        return Tool(
            name=self.name,
            description=f"{self.description} Usage params: {list(self.parameters.keys())}",
            func=sync_wrapper
        )

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
