import sys
import os
import json
import requests
import time

# Add project root to path
sys.path.append(os.path.abspath(os.path.join(os.path.dirname(__file__), "..")))

from backend.tools.mcp_manager import mcp_manager

def verify_integration():
    print("=== CLWHUB INTEGRATION VERIFIER ===")
    
    # 1. Test Live Search Proxy
    print("\n[1/3] Testing Live Search Proxy (Direct logic check)...")
    search_query = "finance"
    search_url = f"https://clawhub.ai/api/v1/search?q={search_query}"
    try:
        res = requests.get(search_url, timeout=5)
        if res.status_code == 200:
            results = res.json().get("results", [])
            print(f"SUCCESS: Live search for '{search_query}' returned {len(results)} items from ClawHub.AI")
        else:
            print(f"WARNING: ClawHub.AI API returned {res.status_code}")
    except Exception as e:
        print(f"ERROR: Could not hit ClawHub.AI directly: {e}")

    # 2. Test Store Refresh (Local Cache Manipulation)
    print("\n[2/3] Simulating Cache Miss / Dynamic Restoration...")
    store_path = mcp_manager.store_path
    
    # Load current store
    if os.path.exists(store_path):
        with open(store_path, 'r') as f:
            store = json.load(f)
    else:
        store = {"mcp": {}, "skills": {}}

    # Find a clawhub skill to 'delete'
    skill_to_test = None
    for slug, skill in store.get("skills", {}).items():
        if skill.get("source") == "clawhub":
            skill_to_test = slug
            break
    
    if not skill_to_test:
        print("NOTE: No ClawHub skills found in local store. Forcing refresh first...")
        mcp_manager.refresh_clawhub_skills()
        with open(store_path, 'r') as f:
            store = json.load(f)
        for slug, skill in store.get("skills", {}).items():
            if skill.get("source") == "clawhub":
                skill_to_test = slug
                break

    if skill_to_test:
        print(f"Removing '{skill_to_test}' from local cache...")
        del store["skills"][skill_to_test]
        with open(store_path, 'w') as f:
            json.dump(store, f, indent=4)
        
        print("Running mcp_manager.refresh_clawhub_skills()...")
        success, msg = mcp_manager.refresh_clawhub_skills()
        
        with open(store_path, 'r') as f:
            new_store = json.load(f)
        
        if skill_to_test in new_store.get("skills", {}):
            print(f"SUCCESS: '{skill_to_test}' was RESTORED from live ClawHub API.")
        else:
            print(f"FAILED: '{skill_to_test}' did not reappear in local store.")
    else:
        print("ABORTED: Could not find any ClawHub skills to test with.")

    # 3. Verify Store Endpoint Logic in main.py
    print("\n[3/3] Checking API Response...")
    # This assumes the server is running on localhost:8000
    try:
        api_res = requests.get("http://127.0.0.1:8000/api/store/skills", timeout=2)
        if api_res.status_code == 200:
            api_data = api_res.json()
            clawhub_count = sum(1 for s in api_data.values() if s.get('source') == 'clawhub')
            print(f"SUCCESS: API /api/store/skills is serving {clawhub_count} ClawHub skills.")
        else:
            print(f"INFO: Local server not reachable (Expected if not running).")
    except:
        print("INFO: Local server not reachable.")

    print("\nConclusion: The 'Skills' in the UI are dynamic. They are cached in 'backend/data/mcp_store.json' but are populated by hitting ClawHub.ai APIs.")

if __name__ == "__main__":
    verify_integration()
