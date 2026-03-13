import os
import shutil
import time
from backend.kernel.supervisor import system_supervisor

def test_supervisor():
    test_dir = os.path.abspath("workspace/test_supervisor_dir")
    if os.path.exists(test_dir):
        shutil.rmtree(test_dir)
    os.makedirs(test_dir)
    
    pid = "test_pid_123"
    
    print(f"--- Phase 1: Initial Snapshot ---")
    system_supervisor.take_snapshot(pid, test_dir)
    
    print(f"--- Phase 2: Validate No Changes ---")
    is_valid, msg = system_supervisor.validate_completion(pid, test_dir)
    print(f"Result: {is_valid}, Msg: {msg}")
    assert is_valid is False
    
    print(f"\n--- Phase 3: Add Irrelevant Change (README.md) ---")
    with open(os.path.join(test_dir, "README.md"), "w") as f:
        f.write("# Test Project")
    
    is_valid, msg = system_supervisor.validate_completion(pid, test_dir)
    print(f"Result: {is_valid}, Msg: {msg}")
    assert is_valid is False
    assert "REJECTED: You only updated documentation" in msg

    print(f"\n--- Phase 4: Add Relevant Change (script.py) ---")
    with open(os.path.join(test_dir, "script.py"), "w") as f:
        f.write("print('hello world')")
    
    is_valid, msg = system_supervisor.validate_completion(pid, test_dir)
    print(f"Result: {is_valid}, Msg: {msg}")
    assert is_valid is True
    assert "Verified: 1 new files" in msg

    print(f"\n--- Phase 5: Modify Relevant File ---")
    # Take a new snapshot to simulate starting a new task with existing code
    system_supervisor.take_snapshot(pid, test_dir)
    
    time.sleep(1.1) # Ensure mtime changes
    with open(os.path.join(test_dir, "script.py"), "a") as f:
        f.write("\n# Additional comment")
        
    is_valid, msg = system_supervisor.validate_completion(pid, test_dir)
    print(f"Result: {is_valid}, Msg: {msg}")
    assert is_valid is True
    assert "modified files" in msg

    print(f"\n--- Phase 6: Test Anti-Placeholder Rejection ---")
    with open(os.path.join(test_dir, "script.py"), "w") as f:
        f.write("def logic():\n    # TODO: implement later\n    pass")
    
    is_valid, msg = system_supervisor.validate_completion(pid, test_dir)
    print(f"Result: {is_valid}, Msg: {msg}")
    assert is_valid is False
    assert "REJECTED" in msg and "placeholders" in msg

    print("\nALL RELIABILITY TESTS PASSED!")

if __name__ == "__main__":
    test_supervisor()
