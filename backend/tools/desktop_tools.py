import os
import time
import logging
import base64
from datetime import datetime
from typing import List, Dict, Any
import mss
import mss.tools
from PIL import Image
import win32gui
import win32process
import win32con
from backend.tools.mcp_registry import MCPTool, system_registry

logger = logging.getLogger("QLX-TC.Tools.Desktop")

# Ensure screenshots directory exists
SCREENSHOTS_DIR = os.path.abspath(os.path.join(os.path.dirname(__file__), "..", "data", "screenshots"))
os.makedirs(SCREENSHOTS_DIR, exist_ok=True)

async def take_system_screenshot(monitor_index: int = 1) -> Dict[str, Any]:
    """
    Captures a screenshot of the specified monitor.
    Args:
        monitor_index: Index of the monitor to capture (1 is primary).
    """
    try:
        with mss.mss() as sct:
            if monitor_index > len(sct.monitors) - 1:
                return {"error": f"Monitor index {monitor_index} out of range. Max monitors: {len(sct.monitors) - 1}"}
            
            monitor = sct.monitors[monitor_index]
            timestamp = datetime.now().strftime("%Y%m%d_%H%M%S")
            filename = f"screenshot_{timestamp}.png"
            filepath = os.path.join(SCREENSHOTS_DIR, filename)
            
            # Capture the screen
            sct_img = sct.grab(monitor)
            mss.tools.to_png(sct_img.rgb, sct_img.size, output=filepath)
            
            logger.info(f"Screenshot saved to {filepath}")
            
            preview_url = f"/api/screenshots/{filename}"
            
            return {
                "status": "success",
                "file_path": filepath,
                "preview_url": preview_url,
                "filename": filename,
                "monitor": monitor_index,
                "resolution": f"{monitor['width']}x{monitor['height']}",
                "message": f"Screenshot captured. Preview: ![Screenshot]({preview_url})"
            }
    except Exception as e:
        logger.error(f"Error taking screenshot: {str(e)}")
        return {"error": str(e)}

async def list_desktop_windows() -> Dict[str, Any]:
    """Lists all visible windows with their titles and PIDs."""
    windows = []
    
    def enum_handler(hwnd, ctx):
        if win32gui.IsWindowVisible(hwnd):
            title = win32gui.GetWindowText(hwnd)
            if title:
                _, pid = win32process.GetWindowThreadProcessId(hwnd)
                windows.append({
                    "title": title,
                    "pid": pid,
                    "hwnd": hwnd
                })
    
    try:
        win32gui.EnumWindows(enum_handler, None)
        return {"status": "success", "windows": windows}
    except Exception as e:
        return {"error": str(e)}

async def focus_desktop_window(window_title: str) -> Dict[str, Any]:
    """
    Brings a window with a matching title to the foreground.
    Args:
        window_title: Partial or full title of the window to focus.
    """
    target_hwnd = None
    
    def enum_handler(hwnd, ctx):
        nonlocal target_hwnd
        if win32gui.IsWindowVisible(hwnd):
            title = win32gui.GetWindowText(hwnd)
            if window_title.lower() in title.lower():
                target_hwnd = hwnd
                return False # Stop enumeration
        return True

    try:
        win32gui.EnumWindows(enum_handler, None)
        
        if target_hwnd:
            # If minimized, restore it
            if win32gui.IsIconic(target_hwnd):
                win32gui.ShowWindow(target_hwnd, win32con.SW_RESTORE)
            
            win32gui.SetForegroundWindow(target_hwnd)
            return {"status": "success", "message": f"Focused window: {win32gui.GetWindowText(target_hwnd)}"}
        else:
            return {"error": f"No window found matching '{window_title}'"}
    except Exception as e:
        return {"error": str(e)}

# Tool Definitions
screenshot_tool = MCPTool(
    name="take_system_screenshot",
    description="Captures a full screenshot of the desktop. Use this to see what is currently on the user's screen.",
    parameters={
        "monitor_index": {"type": "integer", "description": "Optional: Index of the monitor to capture (default: 1)", "default": 1}
    },
    handler=take_system_screenshot
)

list_windows_tool = MCPTool(
    name="list_desktop_windows",
    description="Lists all open and visible application windows on the desktop.",
    parameters={},
    handler=list_desktop_windows
)

focus_window_tool = MCPTool(
    name="focus_desktop_window",
    description="Brings a specific application window to the foreground by its title. Use this before taking a screenshot if you want to see a specific app.",
    parameters={
        "window_title": {"type": "string", "description": "Title (or part of it) of the window to focus"}
    },
    handler=focus_desktop_window
)

# Registration

async def run_desktop_app(app_path: str) -> dict:
    """Launches a desktop application or opens a file/folder."""
    try:
        # On Windows, os.startfile is the safest way to launch GUI apps as if they were double-clicked
        if hasattr(os, 'startfile'):
            os.startfile(app_path)
        else:
            # Fallback for other systems (though we focus on Windows here)
            import subprocess
            subprocess.Popen([app_path], shell=True if os.name == 'nt' else False)
            
        return {
            "status": "success",
            "message": f"Successfully requested to start: {app_path}"
        }
    except Exception as e:
        logger.error(f"Error starting application {app_path}: {str(e)}")
        return {
            "status": "error",
            "message": f"Failed to start {app_path}: {str(e)}"
        }

run_app_tool = MCPTool(
    name="run_desktop_app",
    description="Launches a desktop application, opens a file, or opens a folder using the system association.",
    parameters={
        "app_path": {
            "type": "string",
            "description": "The full path to the executable, a common name like 'notepad', or a file/folder path."
        }
    },
    handler=run_desktop_app
)

system_registry.register(screenshot_tool)
system_registry.register(list_windows_tool)
system_registry.register(focus_window_tool)
system_registry.register(run_app_tool)
