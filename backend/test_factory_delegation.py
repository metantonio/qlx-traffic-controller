import asyncio
import sys
import os

# Add the project root to sys.path
sys.path.append(os.getcwd())

from backend.tools.agent_tools import list_available_agents
from backend.kernel.process import AIProcess, ResourceLimits, system_process_table
from backend.llm.provider import current_pid

async def test_filtering():
    print("--- Testing list_available_agents filtering ---")
    
    # 1. Test as generic agent
    generic_proc = AIProcess(agent_name="generic_agent", task_description="test", limits=ResourceLimits())
    system_process_table.register(generic_proc)
    
    token = current_pid.set(generic_proc.pid)
    try:
        result_generic = await list_available_agents()
        print("\n[Generic Agent Result]:")
        print(result_generic)
        # Should contain creator_txt_agent
        assert "creator_txt_agent" in result_generic
    finally:
        current_pid.reset(token)

    # 2. Test as software_architect
    architect_proc = AIProcess(agent_name="software_architect", task_description="plan", limits=ResourceLimits())
    system_process_table.register(architect_proc)
    
    token = current_pid.set(architect_proc.pid)
    try:
        result_architect = await list_available_agents()
        print("\n[Software Architect Result]:")
        print(result_architect)
        # Should NOT contain creator_txt_agent
        assert "creator_txt_agent" not in result_architect
        assert "frontend_developer" in result_architect
        assert "Note: As the Architect" in result_architect
    finally:
        current_pid.reset(token)
    
    print("\n✅ Filtering verification SUCCESSFUL.")

if __name__ == "__main__":
    asyncio.run(test_filtering())
