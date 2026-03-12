import os
import asyncio
from pydantic import BaseModel, Field
from backend.tools.mcp_registry import MCPTool, system_registry
from backend.core.database import SessionLocal
from backend.models.database_models import DbAllowedDirectory
from backend.core.logger import get_kernel_logger

logger = get_kernel_logger("QLX-TC.Tools.Filesystem")

_file_locks = {}

def detect_placeholder_path(path: str) -> bool:
    """Detects if a path contains common AI hallucinations/placeholders."""
    placeholders = [
        "/path/to/", "path/to/your", "<project_name>", "[your-app]", 
        "{project_name}", "your-username", "example.com", "YOUR_API_KEY",
        "react-project", "my-app", "myapp", "[agent_workspace]"
    ]
    path_low = path.lower()
    return any(p.lower() in path_low for p in placeholders)

def get_placeholder_error(path: str) -> str:
    """Returns a corrective error message for hallucinated paths."""
    pid = "unknown"
    msg = f"ERROR: You used a placeholder path '{path}'. This is forbidden.\n"
    try:
        from backend.core.context import current_pid
        from backend.kernel.process import system_process_table
        pid = current_pid.get()
        if pid and pid != "kernel":
            proc = system_process_table.processes.get(pid)
            if proc and proc.working_directory:
                msg += f"Your ACTUAL working directory is: {proc.working_directory}\n"
                msg += "You MUST use real paths relative to this directory. Do not guess paths."
    except Exception:
        pass
    return msg

def _resolve_path(filepath: str) -> str:
    """Resolves relative paths against the current process's working_directory if set."""
    pid = None
    try:
        from backend.core.context import current_pid
        from backend.kernel.process import system_process_table
        pid = current_pid.get()
        if pid and pid != "kernel":
            proc = system_process_table.processes.get(pid)
            if proc and proc.working_directory:
                target = os.path.join(proc.working_directory, filepath)
                logger.info(f"[{pid}] Resolved '{filepath}' to '{target}' (WD: {proc.working_directory})")
                return target
    except Exception as e:
        logger.error(f"Error in _resolve_path for pid {pid}: {e}")
        
    return filepath

def is_path_allowed(filepath: str) -> bool:
    """Verifies if the path is within the project root OR a user-allowed directory OR the process working directory."""
    abs_path = os.path.abspath(filepath)
    pid = None
    
    # 1. Check Global Whitelist (Security Boundary) FIRST
    # If the user explicitly whitelisted a path, it should be accessible system-wide.
    try:
        with SessionLocal() as db:
            allowed = db.query(DbAllowedDirectory).all()
            for entry in allowed:
                norm_allowed = os.path.normcase(os.path.abspath(entry.path))
                p_target = os.path.normcase(abs_path)
                
                if p_target.startswith(norm_allowed):
                    try:
                        if os.path.commonpath([p_target, norm_allowed]) == norm_allowed:
                            return True
                    except ValueError:
                        pass
    except Exception as e:
        logger.error(f"Error checking global whitelist: {e}")

    # 2. Specialist Agent Restriction (Sandbox)
    # If not in global whitelist, specialist agents are strictly limited to their assigned working_directory.
    try:
        from backend.core.context import current_pid
        from backend.kernel.process import system_process_table
        pid = current_pid.get()
        
        if pid and pid != "kernel":
            proc = system_process_table.processes.get(pid)
            if proc and proc.working_directory:
                norm_wd = os.path.normcase(os.path.abspath(proc.working_directory))
                p_target = os.path.normcase(abs_path)
                
                if p_target.startswith(norm_wd):
                    try:
                        if os.path.commonpath([p_target, norm_wd]) == norm_wd:
                            return True
                    except ValueError:
                        pass
                
                logger.warning(f"[{pid}] BLOCKED access outside sandbox (WD check failed): {abs_path}")
                return False
    except Exception as e:
        logger.error(f"Error in specialist sandbox check: {e}")
    
    # 3. Base directory (project root) - ONLY for explicit 'kernel' or unknown system processes
    project_root = os.path.normcase(os.path.dirname(os.path.dirname(os.path.dirname(os.path.abspath(__file__)))))
    p_target = os.path.normcase(abs_path)
    
    if pid == "kernel":
        if p_target.startswith(project_root):
            try:
                if os.path.commonpath([p_target, project_root]) == project_root:
                    return True
            except ValueError:
                pass
        
        logger.warning(f"[kernel] BLOCKED access outside project root: {abs_path}")
        return False
        
    # 4. Fallback: Identify unidentified processes attempting root access
    if p_target.startswith(project_root):
        logger.error(f"[SYSTEM-FAULT][{pid}] ACCESS DENIED: Unidentified process attempted root access: {abs_path}")
        return False
        
    return False

def get_file_lock(filepath: str) -> asyncio.Lock:
    abs_path = os.path.abspath(filepath)
    if abs_path not in _file_locks:
        _file_locks[abs_path] = asyncio.Lock()
    return _file_locks[abs_path]

async def filesystem_read(path: str) -> str:
    """Reads a file and returns its content. Supports global fallback to 'workspace'."""
    if detect_placeholder_path(path):
        return get_placeholder_error(path)
        
    resolved_path = _resolve_path(path)
    
    # 1. Primary check (Current Agent WD)
    if os.path.exists(resolved_path) and os.path.isfile(resolved_path):
        if not is_path_allowed(resolved_path):
             return f"Permission Error: Path '{resolved_path}' is unauthorized."
        try:
            with open(resolved_path, "r", encoding="utf-8") as f:
                return f.read()
        except Exception as e:
            return f"Error reading file {path}: {str(e)}"
    
    # 2. MONOREPO FALLBACK: Check the root 'workspace' if file not found locally
    if not os.path.isabs(path):
        # We assume the project root is 3 levels up from this file (backend/tools/filesystem.py)
        project_root = os.path.dirname(os.path.dirname(os.path.dirname(os.path.abspath(__file__))))
        root_ws = os.path.join(project_root, "workspace")
        fallback_path = os.path.join(root_ws, path)
        
        if os.path.exists(fallback_path) and os.path.isfile(fallback_path):
            if not is_path_allowed(fallback_path):
                 return f"Permission Error: Fallback path '{fallback_path}' is unauthorized."
            try:
                with open(fallback_path, "r", encoding="utf-8") as f:
                    return f.read()
            except Exception:
                pass 
                
    return f"Error: File '{path}' not found in agent directory or root workspace."

filesystem_read_tool = MCPTool(
    name="filesystem_read",
    description="Reads contents of a specified file. Attempts to read from the current agent's working directory first. If not found and the path is relative, it then attempts to read from the root 'workspace/' folder.",
    parameters={
        "path": {"type": "string", "description": "Absolute or relative path to the file to read"}
    },
    handler=filesystem_read
)

async def list_directory_tool_handler(path: str) -> str:
    """Lists files and directories in a path."""
    if detect_placeholder_path(path):
        return get_placeholder_error(path)
        
    path = _resolve_path(path)
    if not is_path_allowed(path):
        return f"Permission Error: directory '{path}' is outside of permitted boundaries."

    if not os.path.isdir(path):
        return f"Error: {path} is not a directory."
    
    try:
        items = os.listdir(path)
        result = []
        for item in items:
            full_path = os.path.join(path, item)
            if os.path.isdir(full_path):
                result.append(f"[DIR] {item}")
            else:
                result.append(f"[FILE] {item}")
        return "\n".join(result) if result else "No files found."
    except Exception as e:
        return f"Error listing directory: {e}"

async def list_directory_with_sizes(path: str) -> str:
    """Lists files in a directory with their sizes."""
    if detect_placeholder_path(path):
        return get_placeholder_error(path)
        
    path = _resolve_path(path)
    if not is_path_allowed(path):
         return f"Permission Error: Path '{path}' is unauthorized."
    
    if not os.path.isdir(path):
        return f"Error: '{path}' is not a directory."
        
    try:
        lines = []
        for f in os.listdir(path):
            full_path = os.path.join(path, f)
            if os.path.isdir(full_path):
                lines.append(f"[DIR] {f}")
            else:
                size = os.path.getsize(full_path)
                lines.append(f"[FILE] {f} {size} B")
        return "\n".join(lines) if lines else "No files found."
    except Exception as e:
        return f"Error listing directory: {e}"

filesystem_list_tool = MCPTool(
    name="filesystem_list",
    description="Lists items in a directory.",
    parameters={"path": {"type": "string", "description": "Path to list"}},
    handler=list_directory_tool_handler
)

list_directory_tool = MCPTool(
    name="list_directory",
    description="Lists all files and directories in a specified directory.",
    parameters={"path": {"type": "string", "description": "Path to the directory"}},
    handler=list_directory_tool_handler
)

list_directory_sizes_tool = MCPTool(
    name="list_directory_with_sizes",
    description="Lists all files in a directory with their sizes in bytes.",
    parameters={"path": {"type": "string", "description": "Path to the directory"}},
    handler=list_directory_with_sizes
)

system_registry.register(filesystem_read_tool)
system_registry.register(filesystem_list_tool)
system_registry.register(list_directory_tool)
system_registry.register(list_directory_sizes_tool)

async def append_to_file(filepath: str, content: str) -> str:
    """Appends text to a file safely. Creates the file if it doesn't exist."""
    if detect_placeholder_path(filepath):
        return get_placeholder_error(filepath)
        
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
    if detect_placeholder_path(filepath):
        return get_placeholder_error(filepath)
        
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

async def create_directory(path: str) -> str:
    """Creates a new directory in the agent workspace."""
    if detect_placeholder_path(path):
        return get_placeholder_error(path)
        
    resolved_path = _resolve_path(path)
    if not is_path_allowed(resolved_path):
        return f"Permission Error: Path '{resolved_path}' is unauthorized."
    
    try:
        os.makedirs(resolved_path, exist_ok=True)
        logger.info(f"Successfully created directory: {resolved_path}")
        return f"Successfully created directory: {path}"
    except Exception as e:
        return f"Error creating directory: {e}"

create_directory_tool = MCPTool(
    name="create_directory",
    description="Creates a new directory. Automatically handles relative paths within the agent's project folder.",
    parameters={"path": {"type": "string", "description": "Path of the directory to create"}},
    handler=create_directory
)

filesystem_create_dir_tool = MCPTool(
    name="filesystem_create_directory",
    description="Alias for create_directory.",
    parameters={"path": {"type": "string", "description": "Path of the directory to create"}},
    handler=create_directory
)

read_file_tool = MCPTool(
    name="read_file",
    description="Reads a file. Same as filesystem_read.",
    parameters={"path": {"type": "string", "description": "Path to the file"}},
    handler=filesystem_read
)

filesystem_write_tool_alias1 = MCPTool(
    name="write_file",
    description="Alias for filesystem_write.",
    parameters={
        "filepath": {"type": "string", "description": "Absolute path to the file"},
        "content" : {"type": "string", "description": "The full text content to write"}
    },
    handler=write_file_safe
)

filesystem_write_tool_alias2 = MCPTool(
    name="write_file_safe",
    description="Alias for filesystem_write.",
    parameters={
        "filepath": {"type": "string", "description": "Absolute path to the file"},
        "content" : {"type": "string", "description": "The full text content to write"}
    },
    handler=write_file_safe
)

system_registry.register(create_directory_tool)
system_registry.register(filesystem_create_dir_tool)
system_registry.register(read_file_tool)
system_registry.register(filesystem_append_tool)
system_registry.register(filesystem_write_tool)
system_registry.register(filesystem_write_tool_alias1)
system_registry.register(filesystem_write_tool_alias2)
