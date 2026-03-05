import logging
import asyncio
from typing import List
from backend.kernel.memory_bus import system_memory_bus, MessagePayload
from backend.kernel.scheduler import system_scheduler, Priority
from backend.kernel.process import AIProcess, ResourceLimits

logger = logging.getLogger("TrafficController.Kernel.Workflow")

class WorkflowPipeline:
    """Manages chaining processes together using the Memory Bus."""
    
    def __init__(self, name: str, stages: List[str]):
        """stages: A list of agent roles/names defining the pipeline."""
        self.name = name
        self.stages = stages
        
    async def trigger(self, initial_data: dict):
        """Start the pipeline."""
        if not self.stages:
            return
            
        first_agent = self.stages[0]
        logger.info(f"WORKFLOW: Starting {self.name} -> Spawning {first_agent}")
        await self._spawn_stage(first_agent, initial_data, stage_idx=0)
        
    async def _spawn_stage(self, agent_name: str, data: dict, stage_idx: int):
        # Create limits
        limits = ResourceLimits(max_runtime_sec=300, max_tokens=50000)
        
        # Spawn the process
        proc = AIProcess(
            agent_name=agent_name, 
            task_description=f"Workflow Stage {stage_idx}: {self.name}",
            limits=limits
        )
        # Give some mock capabilities to the workflow processes
        proc.capabilities = ["filesystem.read", "document.parse"]
        
        # Attach listener to know when it finishes
        async def on_process_complete(msg: MessagePayload):
            if msg.source_pid == proc.pid and msg.event_type == "process_completed":
                logger.info(f"WORKFLOW: Stage {stage_idx} ({proc.agent_name}) completed.")
                # Trigger next stage if exists
                next_idx = stage_idx + 1
                if next_idx < len(self.stages):
                    next_agent = self.stages[next_idx]
                    await self._spawn_stage(next_agent, msg.data, next_idx)
                else:
                    logger.info(f"WORKFLOW: Pipeline {self.name} fully completed.")
                    
        # Setup listener
        system_memory_bus.subscribe("process_completed", on_process_complete)
        
        # Inject context and queue it
        proc.memory_context["workflow_data"] = data
        await system_scheduler.submit(proc, priority=Priority.MEDIUM)
