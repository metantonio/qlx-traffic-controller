import os
import sys
import json

# Add the backend directory to the sys.path
backend_dir = r"c:\Repositorios\qlx-traffic-controller\backend"
if backend_dir not in sys.path:
    sys.path.append(backend_dir)

from tools.mcp_manager import MCPManager

def verify_fix():
    config_path = os.path.join(backend_dir, "data", "mcp_servers.json")
    
    # Initialize MCPManager which should trigger _fix_mcp_paths
    manager = MCPManager(config_path)
    
    # Check the file content
    with open(config_path, 'r') as f:
        config = json.load(f)
        
    print(f"Current Config: {json.dumps(config, indent=4)}")
    
    if "filesystem" in config:
        args = config["filesystem"]["args"]
        print(f"Filesystem Args: {args}")
        # Verify paths are absolute and point to the current project
        project_root = os.path.abspath(os.path.join(backend_dir, ".."))
        workspace_dir = os.path.join(project_root, "workspace")
        
        if args[2] == workspace_dir and args[3] == project_root:
            print("SUCCESS: Paths are correctly updated!")
        else:
            print(f"FAILURE: Paths do not match expected root. Expected: {workspace_dir}, {project_root}")
    else:
        print("FAILURE: 'filesystem' key not found in config.")

if __name__ == "__main__":
    verify_fix()
