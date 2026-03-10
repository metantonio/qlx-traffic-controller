
import os
import sys
import json
import logging

# Setup logging to see what bootstrap does
logging.basicConfig(level=logging.INFO)

sys.path.append(os.getcwd())
from backend.main import bootstrap_system

def test_bootstrap_wipe():
    agents_path = "backend/data/custom_agents.json"
    
    # Backup
    with open(agents_path, 'r') as f:
        original_content = f.read()
    
    try:
        print("Emptying custom_agents.json to {} (size 2)...")
        with open(agents_path, 'w') as f:
            f.write("{}")
        
        print(f"File size: {os.path.getsize(agents_path)}")
        
        print("Running bootstrap_system...")
        # Note: bootstrap_system ALSO checks has_mcps in DB. 
        # If DB is not empty, it won't run the import.
        # But let's see if it logs anything.
        bootstrap_system()
        
        with open(agents_path, 'r') as f:
            new_content = f.read()
        
        if new_content == "{}":
            print("BOOTSTRAP: Did NOT overwrite (good, because DB probably not empty).")
        else:
            print("BOOTSTRAP: OVERWROTE file (expected if system thought it was fresh).")
            
    finally:
        # Restore
        with open(agents_path, 'w') as f:
            f.write(original_content)
        print("Restored original agents.")

if __name__ == "__main__":
    test_bootstrap_wipe()
