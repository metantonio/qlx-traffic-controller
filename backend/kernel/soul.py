import os
from typing import Optional
from backend.core.logger import get_kernel_logger

logger = get_kernel_logger("QLX-TC.Kernel.Soul")

class SoulManager:
    """
    Manages persistent project-level memory through a '.agents/soul.md' file.
    This file stores learnings, conventions, and state that persists across sessions.
    """
    
    def get_soul_path(self, ws_dir: str) -> Optional[str]:
        if not ws_dir or not os.path.exists(ws_dir):
            return None
        
        agents_dir = os.path.join(ws_dir, ".agents")
        if not os.path.exists(agents_dir):
            try:
                os.makedirs(agents_dir, exist_ok=True)
            except:
                return None
                
        return os.path.join(agents_dir, "soul.md")

    def read_soul(self, ws_dir: str) -> str:
        """Reads the soul file and returns it as a formatted block."""
        path = self.get_soul_path(ws_dir)
        if path and os.path.exists(path):
            try:
                with open(path, "r", encoding="utf-8") as f:
                    content = f.read().strip()
                    if content:
                        return f"### PROJECT SOUL (Continuous Memory)\n{content}\n\n"
            except Exception as e:
                logger.error(f"Error reading soul from {path}: {str(e)}")
        return ""

    def update_soul(self, ws_dir: str, new_learnings: str):
        """Appends or updates the soul file with new insights."""
        path = self.get_soul_path(ws_dir)
        if not path:
            return
            
        try:
            # We use an LLM or simple append logic to keep it clean.
            # For now, we'll just ensure the file exists and has a header.
            mode = "a" if os.path.exists(path) else "w"
            with open(path, mode, encoding="utf-8") as f:
                if mode == "w":
                    f.write("# Project Soul: Continuous Memory\n\n")
                f.write(f"## Update ({os.path.basename(ws_dir)})\n{new_learnings}\n\n")
            logger.info(f"Updated soul at {path}")
        except Exception as e:
            logger.error(f"Error updating soul at {path}: {str(e)}")

system_soul_manager = SoulManager()
