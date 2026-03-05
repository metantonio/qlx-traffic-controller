
import sys
import os
sys.path.append(os.getcwd())

try:
    from backend.main import app
    print("Backend imports OK")
except Exception as e:
    print(f"Backend import failed: {e}")
    import traceback
    traceback.print_exc()
