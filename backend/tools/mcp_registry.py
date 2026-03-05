from typing import List, Dict, Callable, Any, Type
from langchain_core.tools import StructuredTool
from pydantic import BaseModel, Field, create_model
import asyncio


class MCPTool:
    """Represents a capability accessible by an Agent via the Model Context Protocol."""
    
    def __init__(self, name: str, description: str, parameters: Dict[str, Any], handler: Callable):
        self.name = name
        self.description = description
        self.parameters = parameters
        self._handler = handler
        
    async def execute(self, **kwargs) -> Any:
        return await self._handler(**kwargs)
        
    def _build_args_schema(self) -> Type[BaseModel]:
        """
        Dynamically build a Pydantic model from the MCP parameter spec.
        This is what LangChain passes to bind_tools() so the model knows parameter names.
        """
        fields = {}
        for param_name, param_info in self.parameters.items():
            description = param_info.get("description", param_name)
            fields[param_name] = (str, Field(..., description=description))
        return create_model(f"{self.name}_schema", **fields)
        
    def to_langchain_tool(self) -> StructuredTool:
        """Converts the MCPTool to a StructuredTool with proper schema for bind_tools()."""
        
        # Capture reference to self
        mcp_self = self
        args_schema = self._build_args_schema()
        
        def sync_wrapper(**kwargs) -> str:
            """Sync wrapper that runs the async handler correctly inside an active asyncio loop."""
            coro = mcp_self.execute(**kwargs)
            try:
                import nest_asyncio  # lazy import — avoids startup failure if not installed
                nest_asyncio.apply()
                loop = asyncio.get_event_loop()
                return str(loop.run_until_complete(coro))
            except Exception as e:
                return f"Error executing tool {mcp_self.name}: {str(e)}"

        return StructuredTool.from_function(
            name=self.name,
            description=self.description,
            func=sync_wrapper,
            args_schema=args_schema,
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
