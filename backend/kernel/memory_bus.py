import asyncio
import logging
from typing import Dict, List, Callable, Any
from pydantic import BaseModel
import time

logger = logging.getLogger("QLX-TC.Kernel.MemoryBus")

class MessagePayload(BaseModel):
    source_pid: str
    target_pid: str  # Can be "BROADCAST" or specific agent name like "document_agent"
    event_type: str
    data: Dict[str, Any]
    timestamp: float = 0.0

class MemoryBus:
    """Shared memory and event bus for Inter-Process Communication between agents."""
    
    def __init__(self):
        self._subscribers: Dict[str, List[Callable]] = {}
        self._message_history: List[MessagePayload] = []

    def subscribe(self, event_type: str, callback: Callable):
        """Register a callback for a specific event type."""
        if event_type not in self._subscribers:
            self._subscribers[event_type] = []
        self._subscribers[event_type].append(callback)

    async def publish(self, message: MessagePayload):
        """Publish a message onto the memory bus."""
        message.timestamp = time.time()
        self._message_history.append(message)
        
        logger.info(f"BUS: [{message.event_type}] from {message.source_pid} -> {message.target_pid}")
        
        # Route to subscribers of this event type
        if message.event_type in self._subscribers:
            for callback in self._subscribers[message.event_type]:
                try:
                    await callback(message)
                except Exception as e:
                    logger.error(f"Error executing memory bus callback: {e}")
                    
        # System-wide wildcard subscribers (like the Observer dashboard)
        if "*" in self._subscribers:
            for callback in self._subscribers["*"]:
                try:
                    await callback(message)
                except Exception as e:
                    pass

# Global Memory Bus
system_memory_bus = MemoryBus()
