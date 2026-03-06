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
        print(f"DEBUG: Executing tool {self.name} with handler {self._handler}")
        try:
            return await self._handler(**kwargs)
        except Exception as e:
            import traceback
            tb = traceback.format_exc()
            logger.error(f"TOOL EXECUTION ERROR ({self.name}):\n{tb}")
            return f"Error executing tool {self.name}: {str(e)}"
        
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
        
        args_schema = self._build_args_schema()
        
        return StructuredTool.from_function(
            name=self.name,
            description=self.description,
            coroutine=self.execute, # Use the async execute method
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
