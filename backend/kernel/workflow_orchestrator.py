import asyncio
import logging
import uuid
from typing import Dict, Any, List, Optional
from backend.core.logger import get_kernel_logger
from backend.kernel.workflow_manager import Workflow, workflow_manager
from backend.kernel.agent_manager import agent_manager
from backend.kernel.process import AIProcess, ResourceLimits, system_process_table
from backend.kernel.scheduler import system_scheduler, Priority
from backend.kernel.memory_bus import system_memory_bus, MessagePayload

logger = get_kernel_logger("QLX-TC.Workflow.Orchestrator")

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
            logger.info(f"Workflow {execution.workflow.name} ({execution.id}) COMPLETED successfully.")
            if execution.id in self.active_executions:
                del self.active_executions[execution.id]
            return

        step = execution.workflow.steps[execution.current_step_index]
        logger.info(f"Running Workflow {execution.id} - Step {execution.current_step_index + 1}/{len(execution.workflow.steps)}")
        
        # Substitute variables in task template
        task_text = step.task_template
        for var, val in execution.variables.items():
            placeholder = f"{{{{{var}}}}}"
            if placeholder in task_text:
                task_text = task_text.replace(placeholder, val)
                logger.debug(f"Substituted variable {var} in step {execution.current_step_index}")

        # Resolve agent
        agent_name = step.agent_id
        custom_agent = agent_manager.get_agent(agent_name)
        
        # Default tools for kernel agent or if custom agent not found
        resolved_tools = ["shell_execute", "filesystem_read"]
        system_prompt_override = None
        llm_provider = None
        llm_model = None

        if custom_agent:
            logger.info(f"Step {execution.current_step_index} using Custom Agent: {custom_agent.name}")
            resolved_tools = custom_agent.static_tools + [f"mcp:{s}" for s in custom_agent.mcp_servers]
            system_prompt_override = custom_agent.system_prompt
            llm_provider = custom_agent.provider
            llm_model = custom_agent.model
        else:
            logger.info(f"Step {execution.current_step_index} using Default Agent: {agent_name}")

        # Create process
        try:
            proc = AIProcess(
                agent_name=agent_name,
                task_description=task_text,
                limits=ResourceLimits(allowed_tools=resolved_tools)
            )
            
            # Pass orchestration metadata
            proc.memory_context["workflow_id"] = execution.id
            proc.memory_context["workflow_step"] = execution.current_step_index
            
            if system_prompt_override:
                proc.memory_context["system_prompt"] = system_prompt_override
            
            if execution.cumulative_history:
                proc.memory_context["initial_history"] = execution.cumulative_history

            if llm_provider: proc.memory_context["llm_provider"] = llm_provider
            if llm_model: proc.memory_context["llm_model"] = llm_model

            logger.info(f"Submitting Process {proc.pid} for Workflow {execution.id}, Step {execution.current_step_index}")
            await system_scheduler.submit(proc, Priority.MEDIUM)
            execution.active_process_pids.append(proc.pid)

            # Broadcast progress
            await system_memory_bus.publish(MessagePayload(
                source_pid="kernel",
                target_pid="BROADCAST",
                event_type="workflow_progress",
                data={
                    "workflow_id": execution.id,
                    "step_index": execution.current_step_index,
                    "total_steps": len(execution.workflow.steps),
                    "status": "step_started",
                    "pid": proc.pid,
                    "workflow_name": execution.workflow.name
                }
            ))

        except Exception as e:
            logger.error(f"FAILED to spawn step {execution.current_step_index} for workflow {execution.id}: {e}")
            if execution.id in self.active_executions:
                del self.active_executions[execution.id]

    async def _handle_step_completion(self, msg: MessagePayload):
        source_pid = msg.source_pid
        # Check if this process belongs to an active workflow
        proc = system_process_table.get(source_pid)
        if not proc: return

        workflow_id = proc.memory_context.get("workflow_id")
        if not workflow_id or workflow_id not in self.active_executions:
            return

        execution = self.active_executions[workflow_id]
        
        # Ensure we are responding to the *correct* current step
        step_index = proc.memory_context.get("workflow_step")
        if step_index != execution.current_step_index:
            return

        logger.info(f"Workflow {workflow_id} step {step_index} ({source_pid}) finished. Advancing...")
        
        # Accumulate history for the next step
        # Note: AIProcess.history contains the full conversation. 
        # We take the latest state to pass it forward.
        execution.cumulative_history = proc.history
        
        # Broadcast step completion
        await system_memory_bus.publish(MessagePayload(
            source_pid="kernel",
            target_pid="BROADCAST",
            event_type="workflow_progress",
            data={
                "workflow_id": execution.id,
                "step_index": execution.current_step_index,
                "status": "step_completed",
                "pid": source_pid
            }
        ))

        # Advance
        execution.current_step_index += 1
        
        if execution.current_step_index >= len(execution.workflow.steps):
            logger.info(f"Workflow {execution.workflow.name} ({execution.id}) COMPLETED successfully.")
            await system_memory_bus.publish(MessagePayload(
                source_pid="kernel",
                target_pid="BROADCAST",
                event_type="workflow_progress",
                data={
                    "workflow_id": execution.id,
                    "status": "completed",
                    "workflow_name": execution.workflow.name
                }
            ))
            del self.active_executions[execution.id]
        else:
            await self._run_current_step(execution)

# Global system orchestrator
workflow_orchestrator = WorkflowOrchestrator()
