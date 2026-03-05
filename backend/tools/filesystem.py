import os
from pydantic import BaseModel, Field
from backend.tools.mcp_registry import MCPTool, system_registry

async def read_file(filepath: str) -> str:
    """Basic file reader, ensuring it exists."""
    if not os.path.exists(filepath):
        raise FileNotFoundError(f"File {filepath} not found.")
        
    # Later: We can integrate PyMuPDF here for PDFs, pandas for CSV, etc.
    with open(filepath, 'r', encoding='utf-8') as f:
        return f.read()

filesystem_read_tool = MCPTool(
    name="filesystem_read",
    description="Reads contents of a specified file. Currently supports .txt files.",
    parameters={
        "filepath": {"type": "string", "description": "Absolute path to the file to read"}
    },
    handler=read_file
)

system_registry.register(filesystem_read_tool)
