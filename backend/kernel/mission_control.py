import asyncio
import uuid
import logging
from typing import Dict, List, Any, Optional
from backend.kernel.planner import planner_agent
from backend.kernel.process import AIProcess, ResourceLimits, system_process_table, ProcessState
from backend.kernel.scheduler import system_scheduler, Priority
from backend.kernel.memory_bus import system_memory_bus, MessagePayload
from backend.kernel.agent_manager import agent_manager

logger = logging.getLogger("QLX-TC.Kernel.MissionControl")

class Mission:
    def __init__(self, task: str, sequence: List[str], working_directory: Optional[str] = None):
        self.id = str(uuid.uuid4())[:8]
        self.task = task
        self.sequence = sequence
        self.current_index = 0
        self.cumulative_history = []
        self.active_pid: Optional[str] = None
        self.status = "planned"
        self.working_directory = working_directory

class MissionControl:
    """
    Manages the sequential execution of specialist agents based on a Mission Plan.
    Mirrors OpenClaw's sequential specialist chain pattern.
    """
    
    def __init__(self):
        self.active_missions: Dict[str, Mission] = {}
        # Subscribe to agent outputs to trigger the next agent in the sequence
        system_memory_bus.subscribe("agent_output", self._handle_agent_completion)
        logger.info("Mission Control initialized and subscribed to agent_output.")
        
    async def start_mission(self, task: str, working_directory: Optional[str] = None) -> str:
        """Analyze a request, create a plan, and start the first agent."""
        mission = Mission(task, [], working_directory)
        mission.status = "planning"
        self.active_missions[mission.id] = mission
        
        logger.info(f"Initiated Mission {mission.id} - Proceeding to asynchronous planning...")
        
        # Broadcast immediate status so UI shows the mission HUD
        await self._broadcast_mission_update(mission)
        
        # Spawn background planning and execution task
        asyncio.create_task(self._plan_and_execute(mission))
        
        return mission.id

    async def _plan_and_execute(self, mission: Mission):
        """Background task to handle planning and kick off the first specialist."""
        try:
            plan_data = await planner_agent.analyze_request(mission.task)
            mission.sequence = plan_data.get("sequence", [])
            project_name = plan_data.get("project_name")
            
            # Workspace Anchoring: If no WD set, use workspace/{project_name}
            if not mission.working_directory and project_name:
                mission.working_directory = f"workspace/{project_name}"
                logger.info(f"Mission {mission.id} anchored to: {mission.working_directory}")

            logger.info(f"Mission {mission.id} planned. Sequence: {mission.sequence}")
            
            if not mission.sequence:
                logger.error(f"Mission {mission.id} planning failed: empty sequence.")
                mission.status = "failed"
                await self._broadcast_mission_update(mission)
                return

            await self._run_next_step(mission)
        except Exception as e:
            logger.error(f"Mission {mission.id} background error: {e}")
            mission.status = "failed"
            await self._broadcast_mission_update(mission)

    async def _run_next_step(self, mission: Mission):
        """Spawns the next specialist in the sequence."""
        if mission.current_index >= len(mission.sequence):
            logger.info(f"Mission {mission.id} COMPLETED successfully.")
            mission.status = "completed"
            await self._broadcast_mission_update(mission)
            # Cleanup from active tracking
            if mission.id in self.active_missions:
                del self.active_missions[mission.id]
            return

        agent_id = mission.sequence[mission.current_index]
        logger.info(f"Mission {mission.id}: Step {mission.current_index + 1}/{len(mission.sequence)} - Agent: {agent_id}")
        
        # Prepare process
        agent_cfg = agent_manager.get_agent(agent_id)
        if not agent_cfg:
            logger.error(f"Mission {mission.id} failed: Agent {agent_id} not found.")
            mission.status = "failed"
            await self._broadcast_mission_update(mission)
            if mission.id in self.active_missions:
                del self.active_missions[mission.id]
            return

        # Build task description for the specialist
        specialist_task = f"### YOUR CURRENT MISSION TASK:\n{mission.task}\n\n"
        
        if mission.current_index == 0:
             specialist_task += "INSTRUCTIONS: You are the FIRST specialist in this chain. Analyze the environment and begin the work."
        else:
            prev_agent = mission.sequence[mission.current_index - 1]
            specialist_task += f"INSTRUCTIONS: You are the NEXT specialist after '{prev_agent}'. Review the execution history to continue the work and achieve the mission goal."

        # Resource limits
        allowed_tools = agent_cfg.static_tools + [f"mcp:{s}" for s in agent_cfg.mcp_servers]
        limits = ResourceLimits(allowed_tools=allowed_tools)
        
        proc = AIProcess(
            agent_name=agent_id,
            task_description=specialist_task,
            limits=limits,
            working_directory=mission.working_directory,
            original_request=mission.task
        )
        
        # Inject mission metadata for tracking
        proc.memory_context["mission_id"] = mission.id
        proc.memory_context["mission_step"] = mission.current_index
        proc.memory_context["initial_history"] = mission.cumulative_history
        
        # Register in system table
        system_process_table.register(proc)
        
        mission.active_pid = proc.pid
        mission.status = "running"
        
        # Submit to scheduler
        await system_scheduler.submit(proc, Priority.MEDIUM)
        await self._broadcast_mission_update(mission)

    async def _handle_agent_completion(self, msg: MessagePayload):
        """Triggered when an agent finishes its task (published by LLMProvider)."""
        source_pid = msg.source_pid
        proc = system_process_table.get(source_pid)
        if not proc: return

        mission_id = proc.memory_context.get("mission_id")
        if not mission_id or mission_id not in self.active_missions:
            return

        mission = self.active_missions[mission_id]
        
        # Safety check: ensure we are responding to the correct active PID for this mission
        if proc.pid != mission.active_pid:
            return

        logger.info(f"Mission {mission_id}: Agent {proc.agent_name} (PID: {proc.pid}) finished with state: {proc.state.value}")
        
        if proc.state == ProcessState.FAILED:
            logger.error(f"Mission {mission_id} ABORTED due to agent failure.")
            mission.status = "failed"
            await self._broadcast_mission_update(mission)
            if mission.id in self.active_missions:
                del self.active_missions[mission.id]
            return

        # Advance mission: Accumulate history and increment index
        mission.cumulative_history = proc.history
        mission.current_index += 1
        
        # Execute next step
        await self._run_next_step(mission)

    async def _broadcast_mission_update(self, mission: Mission):
        """Emit mission state for the UI via Memory Bus."""
        await system_memory_bus.publish(MessagePayload(
            source_pid="kernel",
            target_pid="BROADCAST",
            event_type="mission_progress",
            data={
                "mission_id": mission.id,
                "status": mission.status,
                "current_index": mission.current_index,
                "total_steps": len(mission.sequence),
                "sequence": mission.sequence,
                "active_pid": mission.active_pid,
                "current_agent": mission.sequence[mission.current_index] if mission.current_index < len(mission.sequence) else "None"
            }
        ))

# Global Mission Control instance for singleton access
mission_control = MissionControl()
