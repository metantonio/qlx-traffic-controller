import uuid
import time
from enum import Enum
from typing import List, Dict, Any, Optional
from pydantic import BaseModel

class ProcessState(Enum):
    QUEUED = "queued"
    RUNNING = "running"
    PAUSED = "paused"
    COMPLETED = "completed"
    FAILED = "failed"
    TERMINATED = "terminated"

class ResourceLimits(BaseModel):
    max_runtime_sec: int = 600
    max_tokens: int = 100000
    allowed_tools: List[str] = []

class AIProcess:
    """Represents an isolated AI agent execution context."""
    
    def __init__(self, agent_name: str, task_description: str, limits: ResourceLimits):
        self.pid = str(uuid.uuid4())[:8]  # Short PID for readability
        self.agent_name = agent_name
        self.task_description = task_description
        self.state = ProcessState.QUEUED
        
        self.resource_limits = limits
        self.capabilities: List[str] = []
        
        self.metrics = {
            "tokens_used": 0,
            "tools_called": 0,
            "start_time": None,
            "end_time": None
        }
        self.memory_context: Dict[str, Any] = {}

    def start(self):
        self.state = ProcessState.RUNNING
        self.metrics["start_time"] = time.time()
        
    def complete(self):
        self.state = ProcessState.COMPLETED
        self.metrics["end_time"] = time.time()
        
    def fail(self, reason: str):
        self.state = ProcessState.FAILED
        self.metrics["end_time"] = time.time()
        self.memory_context["failure_reason"] = reason

    def check_limits(self) -> bool:
        """Returns True if within limits, False if exceeded."""
        if self.metrics["start_time"]:
            runtime = time.time() - self.metrics["start_time"]
            if runtime > self.resource_limits.max_runtime_sec:
                return False
        if self.metrics["tokens_used"] > self.resource_limits.max_tokens:
            return False
        return True

class ProcessTable:
    """System-wide tracker for all active and historical AI processes."""
    def __init__(self):
        self.processes: Dict[str, AIProcess] = {}
        
    def register(self, process: AIProcess):
        self.processes[process.pid] = process
        
    def get(self, pid: str) -> Optional[AIProcess]:
        return self.processes.get(pid)

# Global process table mapping
system_process_table = ProcessTable()
