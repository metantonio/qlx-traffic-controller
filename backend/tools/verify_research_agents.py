import asyncio
import sys
import os

# Ensure backend is in path
sys.path.append(os.getcwd())

from backend.kernel.process import AIProcess, ResourceLimits
from backend.kernel.scheduler import system_scheduler

async def verify_research():
    print("\n--- Verifying Omni-Scholar Research Capability ---")
    
    # We explicitly give it ONLY fetch and require it to output a json tool call
    proc = AIProcess(
        agent_name="omni_scholar",
        task_description="Summarize https://example.com . You MUST use the fetch tool. Output EXACTLY this JSON block and nothing else:\n{\"name\": \"fetch\", \"arguments\": {\"url\": \"https://example.com\"}}",
        limits=ResourceLimits(allowed_tools=["mcp:fetch"])
    )
    
    print(f"Spawning process {proc.pid}...")
    try:
        await system_scheduler._execute_process(proc)
        print(f"Process completed with state: {proc.state}")
        
        found_tool = False
        for msg in proc.history:
            print(f"MSG ROLE: {msg.get('role')} CONTENT: {msg.get('content')[:50] if msg.get('content') else 'None'}")
            if msg.get("role") == "tool":
                print(f"✅ Executed tool successfully! Result snippet: {msg['content'][:150]}...")
                found_tool = True
        if not found_tool:
            print("❌ No tool was executed! Checking assistant messages...")
            for msg in proc.history:
                if msg.get("role") == "assistant":
                    print(f"Assistant wrote: {msg['content'][:200]}")
    except Exception as e:
        print(f"❌ Verification failed: {e}")

if __name__ == "__main__":
    asyncio.run(verify_research())
