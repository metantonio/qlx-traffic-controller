import os
import time
import hashlib
from typing import Dict, List, Optional, Set
from backend.core.logger import get_kernel_logger

logger = get_kernel_logger("QLX-TC.Kernel.Supervisor")

class WorkspaceSnapshot:
    def __init__(self, ws_dir: str):
        self.ws_dir = ws_dir
        self.timestamp = time.time()
        self.files: Dict[str, float] = {}  # path -> mtime
        self.capture()

    def capture(self):
        if not os.path.exists(self.ws_dir):
            return
        
        for root, _, filenames in os.walk(self.ws_dir):
            # Skip common noise directories
            if any(part in root.split(os.sep) for part in [".git", "node_modules", "__pycache__", "venv"]):
                continue
                
            for f in filenames:
                file_path = os.path.join(root, f)
                try:
                    self.files[file_path] = os.path.getmtime(file_path)
                except (OSError, PermissionError):
                    continue

class Supervisor:
    """Truth-layer validator that ensures agents make physical changes to the workspace."""
    
    def __init__(self):
        self.snapshots: Dict[str, WorkspaceSnapshot] = {} # pid -> snapshot

    def take_snapshot(self, pid: str, ws_dir: str):
        """Captures the initial state of the workspace for a process."""
        if not ws_dir:
            return
        self.snapshots[pid] = WorkspaceSnapshot(ws_dir)
        logger.info(f"Snapshot captured for process {pid} at {ws_dir}")

    def validate_completion(self, pid: str, ws_dir: str, agent_name: Optional[str] = None) -> (bool, str):
        """
        Validates if the agent actually changed anything.
        Returns (is_valid, reason_or_error)
        """
        if pid not in self.snapshots:
            # If no snapshot exists, we can't strictly validate mtime, 
            # but we can check if anything exists at all.
            logger.warning(f"No initial snapshot found for {pid}. Skipping mtime check.")
            return True, "Success (Validation skipped - no initial snapshot)"

        initial = self.snapshots[pid]
        current = WorkspaceSnapshot(ws_dir)
        
        changed_files = []
        new_files = []
        
        all_changed = []
        for path, mtime in current.files.items():
            if path not in initial.files:
                new_files.append(path)
                all_changed.append(path)
            elif mtime > initial.files[path]:
                changed_files.append(path)
                all_changed.append(path)

        # Remove ignored files from count (logs, plans, etc. should count as progress but not code completeness)
        relevant_new = [f for f in new_files if not f.endswith((".md", ".json", ".log", ".txt"))]
        relevant_changed = [f for f in changed_files if not f.endswith((".md", ".json", ".log", ".txt"))]

        total_relevant = len(relevant_new) + len(relevant_changed)
        
        # INTEGRITY GATE: Anti-Placeholder check
        for fpath in relevant_new + relevant_changed:
            try:
                with open(fpath, "r", encoding="utf-8") as f:
                    content = f.read()
                    placeholders = ["TODO", "FIXME", "Insert logic here", "implement later", "// ..."]
                    for p in placeholders:
                        if p.lower() in content.lower():
                            return False, f"REJECTED: File {os.path.basename(fpath)} contains placeholders ('{p}'). Implementation must be complete."
            except:
                continue

        if total_relevant > 0:
            logger.info(f"Process {pid} verified: {len(relevant_new)} new and {len(relevant_changed)} changed relevant files.")
            return True, f"Verified: {len(relevant_new)} new files, {len(relevant_changed)} modified files."

        # SPECIAL CASE: Software Architect is allowed to only update documentation
        if agent_name == "software_architect" and len(all_changed) > 0:
            return True, f"Verified (Architect): Updated {len(all_changed)} plan/architecture files."

        # If zero relevant code changes, check if they at least updated the plan/metadata
        if len(all_changed) > 0:
            return False, "REJECTED: You only updated documentation or metadata. You MUST implement actual functional logic in code files (e.g., .js, .ts, .py) to complete this task."

        return False, "REJECTED: No file changes detected in the workspace. You must actually write code using 'filesystem_write' or 'shell_execute' before calling task_complete."

system_supervisor = Supervisor()
