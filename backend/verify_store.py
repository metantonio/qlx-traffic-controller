import requests
import json
import os

BASE_URL = "http://127.0.0.1:8000/api"

def test_store():
    print("--- Testing MCP Store Listing ---")
    try:
        res = requests.get(f"{BASE_URL}/store/mcp")
        res.raise_for_status()
        mcp_store = res.json()
        print(f"Found {len(mcp_store)} items in MCP store.")
        print(f"Sample: {list(mcp_store.keys())[:2]}")
    except Exception as e:
        print(f"MCP Store List Failed: {e}")

    print("\n--- Testing Skills Store Listing ---")
    try:
        res = requests.get(f"{BASE_URL}/store/skills")
        res.raise_for_status()
        skills_store = res.json()
        print(f"Found {len(skills_store)} items in Skills store.")
        print(f"Sample: {list(skills_store.keys())[:2]}")
    except Exception as e:
        print(f"Skills Store List Failed: {e}")

    print("\n--- Testing One-Click Install (Wikipedia) ---")
    try:
        # Wikipedia doesn't require keys
        res = requests.post(f"{BASE_URL}/store/install", json={"server_id": "wikipedia"})
        res.raise_for_status()
        print("Install Wikipedia: SUCCESS")
        
        # Verify it's in the servers list
        res = requests.get(f"{BASE_URL}/mcp/servers")
        servers = res.json()
        if any(s['id'] == 'wikipedia' for s in servers):
            print("Verification: Wikipedia is now in Active Bridges!")
        else:
            print("Verification: FAILED - Wikipedia not found in active servers.")
            
    except Exception as e:
        print(f"Install Test Failed: {e}")

if __name__ == "__main__":
    test_store()
