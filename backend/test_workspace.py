import os
import sys
import asyncio
from backend.kernel.agent_manager import agent_manager, CustomAgent
from backend.tools.agent_tools import delegate_to_agent
from backend.kernel.process import system_process_table

async def main():
    test_dir = os.path.join(os.getcwd(), "workspace", "test_dir")
    os.makedirs(test_dir, exist_ok=True)
    
    # 1. Create Test Agent
    agent = CustomAgent(
        id="workspace_tester",
        name="Workspace Tester",
        description="Tests workspace isolation",
        system_prompt="Execute exactly the shell commands requested.",
        static_tools=["shell_execute", "filesystem_write", "filesystem_read"],
        working_directory=test_dir
    )
    agent_manager.add_agent(agent)
    print(f"Agent loaded. Working dir: {agent.working_directory}")
    
    # 2. Delegate a task: write shell directly
    res = await delegate_to_agent("workspace_tester", "Use shell_execute to run exactly this command: echo hello > test.txt")
    
    print("\nOrchestrator Result:")
    print(res)
    
    # 3. Verify file location
    correct_path = os.path.join(test_dir, "test.txt")
    wrong_path = os.path.join(os.getcwd(), "test.txt")
    
    if os.path.exists(correct_path):
        print(f"\nSUCCESS: test.txt found in {correct_path}")
        with open(correct_path, "r") as f:
            print("Content:", f.read())
    else:
        print(f"\nFAIL: test.txt NOT found in {correct_path}")
        
    if os.path.exists(wrong_path):
        print(f"FAIL: test.txt incorrectly found in project root: {wrong_path}")
    else:
        print(f"SUCCESS: test.txt not in project root.")

if __name__ == "__main__":
    asyncio.run(main())
