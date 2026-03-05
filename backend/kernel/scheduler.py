import asyncio
import logging
from enum import IntEnum
from typing import Dict, List
from backend.kernel.process import AIProcess, ProcessState, system_process_table
from backend.kernel.memory_bus import system_memory_bus, MessagePayload

logger = logging.getLogger("TrafficController.Kernel.Scheduler")

class Priority(IntEnum):
    HIGH = 1
    MEDIUM = 2
    LOW = 3

class TaskScheduler:
    """Manages the execution queues for AI processes."""
    
    def __init__(self, max_concurrent: int = 3):
        self.max_concurrent = max_concurrent
        self.queues: Dict[Priority, asyncio.Queue] = {
            Priority.HIGH: asyncio.Queue(),
            Priority.MEDIUM: asyncio.Queue(),
            Priority.LOW: asyncio.Queue()
        }
        self.active_processes: List[AIProcess] = []
        self._running = False
        
    async def submit(self, process: AIProcess, priority: Priority = Priority.MEDIUM):
        """Submit a new process to the appropriate queue."""
        system_process_table.register(process)
        process.state = ProcessState.QUEUED
        await self.queues[priority].put(process)
        logger.info(f"Process {process.pid} ({process.agent_name}) queued at {priority.name} priority.")
        
    async def start_scheduler(self):
        self._running = True
        logger.info("Task Scheduler started.")
        while self._running:
            await self._dispatch()
            await self._broadcast_metrics()
            await asyncio.sleep(0.5)  # Tick rate
            
    async def _broadcast_metrics(self):
        """Send state to dashboard htop UI."""
        queues_state = {
            "HIGH": self.queues[Priority.HIGH].qsize(),
            "MEDIUM": self.queues[Priority.MEDIUM].qsize(),
            "LOW": self.queues[Priority.LOW].qsize()
        }
        
        procs_list = []
        for pid, proc in system_process_table.processes.items():
            procs_list.append({
                "pid": proc.pid,
                "agent": proc.agent_name,
                "state": proc.state.value,
                "mem": f"{proc.metrics['tokens_used']} Tk",
                "cpu": "100%" if proc.state == ProcessState.RUNNING else "0%"
            })
            
        await system_memory_bus.publish(MessagePayload(
            source_pid="kernel",
            target_pid="BROADCAST",
            event_type="system_metrics",
            data={"queues": queues_state, "processes": procs_list, "active_count": len(self.active_processes)}
        ))
            
    def stop_scheduler(self):
        self._running = False
        
    async def _dispatch(self):
        """Pulls processes from queues based on priority and concurrency limits."""
        # Cleanup completed/failed processes from active list
        self.active_processes = [p for p in self.active_processes if p.state == ProcessState.RUNNING]
        
        if len(self.active_processes) >= self.max_concurrent:
            return  # Sytem at capacity
            
        # Try High -> Medium -> Low
        for prio in [Priority.HIGH, Priority.MEDIUM, Priority.LOW]:
            try:
                # Check if we have room before fetching
                if len(self.active_processes) >= self.max_concurrent:
                    break
                    
                process: AIProcess = self.queues[prio].get_nowait()
                process.start()
                self.active_processes.append(process)
                logger.info(f"Dispatched Process {process.pid} ({process.agent_name})")
                
                # Mock execution bridge - in reality this triggers the Agent loop
                asyncio.create_task(self._mock_execute(process))
                
            except asyncio.QueueEmpty:
                continue

    async def _mock_execute(self, process: AIProcess):
        """Temporary mock wrapper for process execution simulation."""
        try:
            # Simulate work
            await asyncio.sleep(2)
            if not process.check_limits():
                process.fail("Resource limits exceeded")
                logger.warning(f"Process {process.pid} failed: Resources exceeded.")
            else:
                process.complete()
                logger.info(f"Process {process.pid} completed successfully.")
        except Exception as e:
            process.fail(str(e))

# Global system scheduler
system_scheduler = TaskScheduler()
