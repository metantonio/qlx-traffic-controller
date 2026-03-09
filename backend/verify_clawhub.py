
import sys
import os
import json
import asyncio

# Add project root to path
sys.path.append(os.path.abspath(os.path.join(os.path.dirname(__file__), "..")))

from backend.tools.mcp_manager import mcp_manager

def test_refresh():
    print("Testing ClawHub Refresh...")
    success, message = mcp_manager.refresh_clawhub_skills()
    print(f"Success: {success}")
    print(f"Message: {message}")
    
    if success:
        store = mcp_manager.load_store()
        skills = store.get("skills", {})
        print(f"Found {len(skills)} skills in store.")
        if len(skills) > 0:
            first_skill = list(skills.values())[0]
            print(f"Sample skill: {first_skill['name']} ({first_skill['source']})")

if __name__ == "__main__":
    test_refresh()
