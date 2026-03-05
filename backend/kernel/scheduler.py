import asyncio
import logging
from enum import IntEnum
from typing import Dict, List
from backend.core.logger import get_kernel_logger
from backend.kernel.process import AIProcess, ProcessState, system_process_table
from backend.kernel.memory_bus import system_memory_bus, MessagePayload
from backend.llm.provider import LLMProvider
from backend.tools.mcp_registry import system_registry
from backend.tools.mcp_manager import mcp_manager

logger = get_kernel_logger("AgentOS.Kernel.Scheduler")

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
                
                # Actual LLM Sandbox execution bridge
                asyncio.create_task(self._execute_process(process))
                
            except asyncio.QueueEmpty:
                continue

    async def _execute_process(self, process: AIProcess):
        """Asynchronously executes the AI process using local LLM inference."""
        try:
            llm = LLMProvider() # Adheres to DEFAULT_MODEL in .env automatically
            
            default_prompt = (
                "You are an AI Kernel Agent with access to real system tools. "
                "Use the provided tools whenever the user task requires executing commands, reading files, or interacting with the system. "
                "Always prefer using a tool over guessing. After using a tool, provide a clear summary of the results."
            )
            system_prompt = process.memory_context.get("system_prompt", default_prompt)
            
            # 1. Static tools from Custom Registry (shell, etc.)
            custom_tools = []
            allowed_tool_names = process.resource_limits.allowed_tools or []
            
            static_tool_names = [n for n in allowed_tool_names 
                                if n not in ["filesystem_read", "memory_access"] and not n.startswith("mcp:")]
            
            for tool_name in static_tool_names:
                mcp_t = system_registry.get_tool(tool_name)
                if mcp_t:
                    custom_tools.append(mcp_t.to_langchain_tool())
            
            # 2. Dynamic tools from Configured MCP Servers
            dynamic_mcp_tools = []
            
            # Collect specific MCP servers to load
            target_mcp_servers = [n.split("mcp:")[1] for n in allowed_tool_names if n.startswith("mcp:")]
            
            # Support legacy tags by mapping to known server IDs
            if "filesystem_read" in allowed_tool_names:
                target_mcp_servers.append("filesystem")
            if "memory_access" in allowed_tool_names:
                target_mcp_servers.append("memory")

            if target_mcp_servers:
                try:
                    # Filter: if it's a legacy tool, we allow it specifically.
                    # As we move to more dynamic MCPs, we might want a more granular allowed_tools check.
                    # For now, we fetch ALL and filter if target_mcp_servers is specified?
                    # Actually, MCPManager should support server-specific fetching.
                    # But for now, get_all_tools uses a multi-client. 
                    # Let's see if we can filter by server in the client.
                    
                    config = mcp_manager.load_config()
                    enabled_for_agent = {
                        s_id: config[s_id] for s_id in target_mcp_servers if s_id in config and config[s_id].get("enabled", True)
                    }
                    
                    if enabled_for_agent:
                        from langchain_mcp_adapters.client import MultiServerMCPClient
                        client = MultiServerMCPClient({
                            k: {
                                "command": v["command"],
                                "args": v["args"],
                                "transport": v.get("transport", "stdio"),
                                "env": v.get("env")
                            } for k, v in enabled_for_agent.items()
                        })
                        dynamic_mcp_tools = await client.get_tools()
                        logger.info(f"Loaded {len(dynamic_mcp_tools)} tools from servers: {list(enabled_for_agent.keys())}")
                except Exception as e:
                    logger.warning(f"Could not load dynamic MCP tools for agent: {e}")
            
            all_tools = custom_tools + dynamic_mcp_tools
            
            provider_override = process.memory_context.get("llm_provider")
            model_override = process.memory_context.get("llm_model")
            
            llm = LLMProvider(provider=provider_override, model=model_override)
            
            # 4. Agent Execution Loop
            initial_history = process.memory_context.get("initial_history")
            
            process.start()
            system_process_table.update_state(process)
            
            if all_tools:
                logger.info(f"Process {process.pid} running with tools: {[t.name for t in all_tools]}")
                response_text, history = await llm.aexecute_agent(
                    system_prompt=system_prompt,
                    user_prompt=process.task_description,
                    tools=all_tools,  # unified BaseTool list
                    source_pid=process.pid, # Link to this process for logs
                    initial_history=initial_history
                )
                process.history = history
            else:
                logger.info(f"Process {process.pid} running with NO TOOLS.")
                response_text, history = await llm.aexecute_agent(
                    system_prompt=system_prompt,
                    user_prompt=process.task_description,
                    tools=[],
                    source_pid=process.pid,
                    initial_history=initial_history
                )
                process.history = history
            
            # Persist history back to DB
            for msg in process.history:
                # Basic check to avoid duplicates if initial history was already there?
                # Actually, simple way is to clear and re-add or just add new ones.
                # Since AIProcess.history is the full list, let's just use it to sync.
                # For simplicity, I'll just save the whole thing in ProcessTable.sync_history(pid, history)
                pass # I'll add sync_history to ProcessTable
            
            # Mocking token consumption based on response length for testing limits
            process.metrics["tokens_used"] = len(response_text.split())
            
            if not process.check_limits():
                process.fail("Resource limits exceeded during inference")
                logger.warning(f"Process {process.pid} failed: Resources exceeded.")
            else:
                process.complete()
                logger.info(f"Process {process.pid} completed successfully.")
            
            # SYNC TO DB
            system_process_table.register(process) # register handles both create and update (merge)
            # Re-registering also saves history if I update register to handle it
            
            # Emit Output to system message bus for Frontend
            await system_memory_bus.publish(MessagePayload(
                source_pid=process.pid,
                target_pid="BROADCAST",
                event_type="agent_output",
                data={
                    "task": process.task_description, 
                    "response": response_text,
                    "used_tools": [t.name for t in all_tools] if all_tools else []
                }
            ))
                
        except Exception as e:
            process.fail(str(e))
            logger.error(f"Process {process.pid} encountered fatal error: {str(e)}")

# Global system scheduler
system_scheduler = TaskScheduler()
