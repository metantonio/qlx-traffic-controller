import os
import asyncio
from pydantic import BaseModel, Field
from backend.tools.mcp_registry import MCPTool, system_registry
from backend.core.database import SessionLocal
from backend.models.database_models import DbAllowedDirectory

_file_locks = {}

def _resolve_path(filepath: str) -> str:
    """Resolves relative paths against the current process's working_directory if set."""
    # Hallucination Guard: If the agent provides a Linux-style path on Windows, strip it.
    if os.name == 'nt':
        # common patterns used by LLMs in their training data or sandbox environments
        hallucinated_prefixes = ["/home/user/projects/", "/mnt/data/", "/app/", "/workspace/"]
        for prefix in hallucinated_prefixes:
            if filepath.startswith(prefix):
                filepath = filepath[len(prefix):]
                break

    if os.path.isabs(filepath):
        return filepath
        
    try:
        from backend.llm.provider import current_pid
        from backend.kernel.process import system_process_table
        pid = current_pid.get()
        if pid:
            proc = system_process_table.processes.get(pid)
            if proc and proc.working_directory:
                return os.path.join(proc.working_directory, filepath)
    except Exception:
        pass
        
    return filepath

def is_path_allowed(filepath: str) -> bool:
    """Verifies if the path is within the project root OR a user-allowed directory OR the process working directory."""
    abs_path = os.path.abspath(filepath)
    
    # 0. Check current process working directory
    try:
        from backend.llm.provider import current_pid
        from backend.kernel.process import system_process_table
        pid = current_pid.get()
        if pid:
            proc = system_process_table.processes.get(pid)
            if proc and proc.working_directory:
                norm_wd = os.path.abspath(proc.working_directory)
                if abs_path.startswith(norm_wd):
                    return True
    except Exception:
        pass
    
    # 1. Base directory (project root: where backend/ is)
    # filesystem.py is in backend/tools/
    project_root = os.path.dirname(os.path.dirname(os.path.dirname(os.path.abspath(__file__))))
    if abs_path.startswith(project_root):
        return True
        
    # 2. Check Database for custom allowed directories
    try:
        with SessionLocal() as db:
            allowed = db.query(DbAllowedDirectory).all()
            for entry in allowed:
                norm_allowed = os.path.abspath(entry.path)
                if abs_path.startswith(norm_allowed):
                    return True
    except Exception as e:
        # If DB fails, we default to Project Root only
        pass
        
    return False

def get_file_lock(filepath: str) -> asyncio.Lock:
    abs_path = os.path.abspath(filepath)
    if abs_path not in _file_locks:
        _file_locks[abs_path] = asyncio.Lock()
    return _file_locks[abs_path]

async def read_file(filepath: str) -> str:
    """Basic file reader, ensuring it exists and is allowed."""
    filepath = _resolve_path(filepath)
    if not is_path_allowed(filepath):
        raise PermissionError(f"Access Denied: path '{filepath}' is outside of permitted boundaries.")

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
    """Lists files in a directory if allowed."""
    path = _resolve_path(path)
    if not is_path_allowed(path):
        raise PermissionError(f"Access Denied: directory '{path}' is outside of permitted boundaries.")

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
    filepath = _resolve_path(filepath)
    print(f"Appending to {filepath}")
    
    if not is_path_allowed(filepath):
        return f"Permission Error: Path '{filepath}' is unauthorized."

    os.makedirs(os.path.dirname(os.path.abspath(filepath)), exist_ok=True)
    lock = get_file_lock(filepath)
    try:
        async with lock:
            with open(filepath, 'a', encoding='utf-8') as f:
                f.write(content + "\n")
        return f"Successfully appended content to {filepath}."
    except Exception as e:
        return f"Error appending to file: {e}"

async def write_file_safe(filepath: str, content: str) -> str:
    """Writes/Overwrites text content to a specified file safely. Creates parent directories if needed."""
    filepath = _resolve_path(filepath)
    print(f"Writing to {filepath}")
    
    if not is_path_allowed(filepath):
        return f"Permission Error: Path '{filepath}' is unauthorized."

    os.makedirs(os.path.dirname(os.path.abspath(filepath)), exist_ok=True)
    lock = get_file_lock(filepath)
    try:
        async with lock:
            with open(filepath, 'w', encoding='utf-8') as f:
                f.write(content)
        return f"Successfully wrote content to {filepath}."
    except Exception as e:
        return f"Error writing to file: {e}"

filesystem_append_tool = MCPTool(
    name="filesystem_append",
    description="Appends text content to a specified file. If the file does not exist, it will be created. Use this when you need to add to a single log or summary file incrementally.",
    parameters={
        "filepath": {"type": "string", "description": "Absolute path to the file"},
        "content" : {"type": "string", "description": "The text content to append to the file"}
    },
    handler=append_to_file
)

filesystem_write_tool = MCPTool(
    name="filesystem_write",
    description="Creates or overwrites a file with exact text content. Use this for creating new components or saving full transcripts.",
    parameters={
        "filepath": {"type": "string", "description": "Absolute path to the file"},
        "content" : {"type": "string", "description": "The full text content to write"}
    },
    handler=write_file_safe
)

system_registry.register(filesystem_append_tool)
system_registry.register(filesystem_write_tool)
