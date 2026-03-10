import os

log_file = os.path.join(os.path.dirname(__file__), "..", "logs", "kernel.log")
try:
    with open(log_file, "r", encoding="utf-8") as f:
        lines = f.readlines()
        for line in lines[-200:]:
            print(line, end="")
except Exception as e:
    print(f"Error reading log: {e}")
