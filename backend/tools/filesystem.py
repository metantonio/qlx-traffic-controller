import os
import asyncio
from pydantic import BaseModel, Field
from backend.tools.mcp_registry import MCPTool, system_registry

_file_locks = {}

def get_file_lock(filepath: str) -> asyncio.Lock:
    abs_path = os.path.abspath(filepath)
    if abs_path not in _file_locks:
        _file_locks[abs_path] = asyncio.Lock()
    return _file_locks[abs_path]

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

async def append_to_file(filepath: str, content: str) -> str:
    """Appends text to a file safely. Creates the file if it doesn't exist."""
    print(f"Appending to {filepath}")
    os.makedirs(os.path.dirname(os.path.abspath(filepath)), exist_ok=True)
    lock = get_file_lock(filepath)
    try:
        async with lock:
            with open(filepath, 'a', encoding='utf-8') as f:
                f.write(content + "\n")
        return f"Successfully appended content to {filepath}."
    except Exception as e:
        return f"Error appending to file: {e}"

filesystem_append_tool = MCPTool(
    name="filesystem_append",
    description="Appends text content to a specified file. If the file does not exist, it will be created. Use this when you need to add to a single log or summary file incrementally.",
    parameters={
        "filepath": {"type": "string", "description": "Absolute path to the file"},
        "content" : {"type": "string", "description": "The text content to append to the file"}
    },
    handler=append_to_file
)

system_registry.register(filesystem_append_tool)
