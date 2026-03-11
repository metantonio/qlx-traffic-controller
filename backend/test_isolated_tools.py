import asyncio
import os
import sys

# Mock current_pid and process table
from backend.llm.provider import current_pid
from backend.kernel.process import system_process_table, AIProcess, ResourceLimits
from backend.tools.shell import execute_shell_command
from backend.tools.filesystem import append_to_file

async def main():
    test_dir = os.path.join(os.getcwd(), "workspace", "test_mock")
    os.makedirs(test_dir, exist_ok=True)
    
    # 1. Create a fake process
    proc = AIProcess("mock_agent", "Test", ResourceLimits())
    proc.working_directory = test_dir
    system_process_table.register(proc)
    
    # Set the token
    token = current_pid.set(proc.pid)
    
    try:
        print(f"Executing in PID {proc.pid} with WD {proc.working_directory}")
        # Test Shell
        res = await execute_shell_command("echo hello_world > direct_test.txt")
        print("Shell Result:", res)
        
        # Test Filesystem
        res2 = await append_to_file("direct_fs.txt", "hello_fs")
        print("Filesystem Result:", res2)
        
        # Verify
        if os.path.exists(os.path.join(test_dir, "direct_test.txt")):
            print("SUCCESS: Shell test file created in workspace.")
        else:
            print("FAIL: Shell test file NOT in workspace.")
            
        if os.path.exists(os.path.join(test_dir, "direct_fs.txt")):
            print("SUCCESS: FS test file created in workspace.")
        else:
            print("FAIL: FS test file NOT in workspace.")
            
    finally:
        current_pid.reset(token)

if __name__ == "__main__":
    asyncio.run(main())
