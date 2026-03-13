import os
import asyncio
from typing import Dict, Set
from backend.core.logger import get_kernel_logger

logger = get_kernel_logger("QLX-TC.Kernel.LockManager")

class WorkspaceLockManager:
    """
    Manages access to workspace directories to prevent concurrent agents
    from corrupting the same project.
    """
    def __init__(self):
        self.locks: Dict[str, asyncio.Lock] = {}
        self.active_paths: Dict[str, str] = {} # path -> pid

    def _normalize_path(self, path: str) -> str:
        """Normalize path to ensure consistency."""
        return os.path.abspath(path).lower()

    async def acquire(self, pid: str, path: str):
        """
        Acquires a lock for a specific workspace path. 
        If the path is already locked, waits until it's free.
        """
        if not path:
            return
            
        norm_path = self._normalize_path(path)
        
        if norm_path not in self.locks:
            self.locks[norm_path] = asyncio.Lock()
            
        logger.info(f"Process {pid} waiting for lock on {norm_path}")
        await self.locks[norm_path].acquire()
        self.active_paths[norm_path] = pid
        logger.info(f"Process {pid} acquired lock on {norm_path}")

    def release(self, pid: str, path: str):
        """Releases the lock for a workspace path."""
        if not path:
            return
            
        norm_path = self._normalize_path(path)
        
        if norm_path in self.locks and self.active_paths.get(norm_path) == pid:
            self.locks[norm_path].release()
            del self.active_paths[norm_path]
            logger.info(f"Process {pid} released lock on {norm_path}")
        else:
            logger.warning(f"Process {pid} attempted to release lock it doesn't hold for {norm_path}")

system_lock_manager = WorkspaceLockManager()
