import asyncio
import logging
import uuid
from typing import Dict, Any, List, Optional
from backend.kernel.workflow_manager import Workflow, workflow_manager
from backend.kernel.agent_manager import agent_manager
from backend.kernel.process import AIProcess, ResourceLimits, system_process_table
from backend.kernel.scheduler import system_scheduler, Priority
from backend.kernel.memory_bus import system_memory_bus, MessagePayload

logger = logging.getLogger("AgentOS.Workflow.Orchestrator")

class WorkflowExecution:
    def __init__(self, workflow: Workflow, variables: Dict[str, str]):
        self.id = str(uuid.uuid4())
        self.workflow = workflow
        self.variables = variables
        self.current_step_index = 0
        self.cumulative_history = []
        self.active_process_pids = []

class WorkflowOrchestrator:
    def __init__(self):
        self.active_executions: Dict[str, WorkflowExecution] = {}
        # Subscribe to agent outputs to trigger next steps
        system_memory_bus.subscribe("agent_output", self._handle_step_completion)

    async def start_workflow(self, workflow_id: str, variables: Dict[str, str]) -> str:
        workflow = workflow_manager.get_workflow(workflow_id)
        if not workflow:
            raise ValueError(f"Workflow {workflow_id} not found")

        execution = WorkflowExecution(workflow, variables)
        self.active_executions[execution.id] = execution
        
        logger.info(f"Starting Workflow {workflow.name} ({execution.id})")
        await self._run_current_step(execution)
        return execution.id

    async def _run_current_step(self, execution: WorkflowExecution):
        if execution.current_step_index >= len(execution.workflow.steps):
            logger.info(f"Workflow {execution.workflow.name} ({execution.id}) completed.")
            # Notify cleanup if needed
            del self.active_executions[execution.id]
            return

        step = execution.workflow.steps[execution.current_step_index]
        
        # Substitute variables in task template
        task_text = step.task_template
        for var, val in execution.variables.items():
            task_text = task_text.replace(f"{{{{{var}}}}}", val)

        # Resolve agent
        agent_name = step.agent_id
        custom_agent = agent_manager.get_agent(agent_name)
        
        resolved_tools = ["shell_execute", "filesystem_read"] # Defaults
        system_prompt_override = None
        llm_provider = None
        llm_model = None

        if custom_agent:
            resolved_tools = custom_agent.static_tools + [f"mcp:{s}" for s in custom_agent.mcp_servers]
            system_prompt_override = custom_agent.system_prompt
            llm_provider = custom_agent.provider
            llm_model = custom_agent.model

        # Create process
        proc = AIProcess(
            agent_name=agent_name,
            task_description=task_text,
            limits=ResourceLimits(allowed_tools=resolved_tools)
        )
        
        # Pass orchestration metadata in memory_context so we can track it
        proc.memory_context["workflow_id"] = execution.id
        proc.memory_context["workflow_step"] = execution.current_step_index
        
        if system_prompt_override:
            proc.memory_context["system_prompt"] = system_prompt_override
        
        # Pass cumulative history from previous steps
        if execution.cumulative_history:
            proc.memory_context["initial_history"] = execution.cumulative_history

        if llm_provider: proc.memory_context["llm_provider"] = llm_provider
        if llm_model: proc.memory_context["llm_model"] = llm_model

        await system_scheduler.submit(proc, Priority.MEDIUM)
        execution.active_process_pids.append(proc.pid)
        logger.info(f"Workflow {execution.id} spawned step {execution.current_step_index}: {proc.pid}")

    async def _handle_step_completion(self, msg: MessagePayload):
        source_pid = msg.source_pid
        # Check if this process belongs to an active workflow
        proc = system_process_table.get(source_pid)
        if not proc: return

        workflow_id = proc.memory_context.get("workflow_id")
        if not workflow_id or workflow_id not in self.active_executions:
            return

        execution = self.active_executions[workflow_id]
        
        # Ensure we are responding to the *correct* current step to avoid race conditions 
        # (though unlikely in a sequential flow)
        step_index = proc.memory_context.get("workflow_step")
        if step_index != execution.current_step_index:
            return

        logger.info(f"Workflow {workflow_id} step {step_index} ({source_pid}) finished. Advancing...")
        
        # Accumulate history for the next step
        # Note: AIProcess.history contains the full conversation. 
        # We take the latest state to pass it forward.
        execution.cumulative_history = proc.history
        
        # Advance
        execution.current_step_index += 1
        await self._run_current_step(execution)

# Global system orchestrator
workflow_orchestrator = WorkflowOrchestrator()
