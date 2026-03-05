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
        self.history: List[Dict[str, Any]] = []  # Added for conversation persistence

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

from backend.core.database import SessionLocal, init_db
from backend.models.database_models import DbProcess, DbMessage

class ProcessTable:
    """System-wide tracker for all active and historical AI processes (backed by SQLite)."""
    def __init__(self):
        self.processes: Dict[str, AIProcess] = {}
        init_db() # Ensure tables exist
        
    def register(self, process: AIProcess):
        self.processes[process.pid] = process
        # Persist to DB
        with SessionLocal() as db:
            db_proc = DbProcess(
                pid=process.pid,
                agent_name=process.agent_name,
                task_description=process.task_description,
                state=process.state.value,
                resource_limits=process.resource_limits.model_dump(),
                tokens_used=process.metrics["tokens_used"],
                tools_called=process.metrics["tools_called"],
                start_time=process.metrics["start_time"],
                end_time=process.metrics["end_time"]
            )
            db.merge(db_proc)
            db.commit()
            
            # Persist history
            if process.history:
                # Clear existing messages for this process to avoid duplicates during sync
                db.query(DbMessage).filter(DbMessage.process_id == process.pid).delete()
                for m in process.history:
                    db_msg = DbMessage(
                        process_id=process.pid,
                        role=m["role"],
                        content=m["content"],
                        tool_calls=m.get("tool_calls"),
                        tool_call_id=m.get("tool_call_id")
                    )
                    db.add(db_msg)
                db.commit()

    def sync_history(self, pid: str, history: List[Dict]):
        """Specialized method to sync only history."""
        with SessionLocal() as db:
            db.query(DbMessage).filter(DbMessage.process_id == pid).delete()
            for m in history:
                db_msg = DbMessage(
                    process_id=pid,
                    role=m["role"],
                    content=m["content"],
                    tool_calls=m.get("tool_calls"),
                    tool_call_id=m.get("tool_call_id")
                )
                db.add(db_msg)
            db.commit()

    def update_state(self, process: AIProcess):
        """Update DB with current process state/metrics."""
        with SessionLocal() as db:
            db_proc = db.query(DbProcess).filter(DbProcess.pid == process.pid).first()
            if db_proc:
                db_proc.state = process.state.value
                db_proc.tokens_used = process.metrics["tokens_used"]
                db_proc.tools_called = process.metrics["tools_called"]
                db_proc.start_time = process.metrics["start_time"]
                db_proc.end_time = process.metrics["end_time"]
                db.commit()

    def add_message(self, pid: str, role: str, content: str, tool_calls: list = None, tool_call_id: str = None):
        """Add a message to the database for a specific process."""
        with SessionLocal() as db:
            db_msg = DbMessage(
                process_id=pid,
                role=role,
                content=content,
                tool_calls=tool_calls,
                tool_call_id=tool_call_id
            )
            db.add(db_msg)
            db.commit()

    def get(self, pid: str) -> Optional[AIProcess]:
        # Check memory first
        if pid in self.processes:
            return self.processes[pid]
            
        # Check DB
        with SessionLocal() as db:
            db_proc = db.query(DbProcess).filter(DbProcess.pid == pid).first()
            if db_proc:
                # Reconstruct AIProcess
                limits = ResourceLimits(**db_proc.resource_limits)
                proc = AIProcess(db_proc.agent_name, db_proc.task_description, limits)
                proc.pid = db_proc.pid
                proc.state = ProcessState(db_proc.state)
                proc.metrics = {
                    "tokens_used": db_proc.tokens_used,
                    "tools_called": db_proc.tools_called,
                    "start_time": db_proc.start_time,
                    "end_time": db_proc.end_time
                }
                # Load history from messages table
                proc.history = [
                    {
                        "role": m.role,
                        "content": m.content,
                        "tool_calls": m.tool_calls,
                        "tool_call_id": m.tool_call_id
                    } for m in db_proc.messages
                ]
                self.processes[pid] = proc
                return proc
        return None

# Global process table mapping
system_process_table = ProcessTable()

# Global process table mapping
system_process_table = ProcessTable()
