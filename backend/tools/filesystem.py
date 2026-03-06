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

async def list_directory(path: str) -> list[str]:
    """Lists files in a directory."""
    if not os.path.isdir(path):
        raise NotADirectoryError(f"{path} is not a directory.")
    return [os.path.join(path, f) for f in os.listdir(path) if os.path.isfile(os.path.join(path, f))]

filesystem_list_tool = MCPTool(
    name="filesystem_list",
    description="Lists all files in a specified directory.",
    parameters={
        "path": {"type": "string", "description": "Absolute path to the directory"}
    },
    handler=list_directory
)

system_registry.register(filesystem_read_tool)
system_registry.register(filesystem_list_tool)
