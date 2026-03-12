import sqlite3
import json

conn = sqlite3.connect('backend/data/kernel.db')
c = conn.cursor()

# Get the last architect process
c.execute('SELECT pid FROM processes WHERE agent_name = "software_architect" ORDER BY created_at DESC LIMIT 1')
row = c.fetchone()
if row:
    pid = row[0]
    print(f"--- History for Process {pid} ---")
    c.execute('SELECT role, content, tool_calls FROM messages WHERE process_id = ? ORDER BY timestamp ASC', (pid,))
    msgs = c.fetchall()
    for role, content, tool_calls in msgs:
        print(f"[{role}]")
        print(content)
        if tool_calls:
            print(f"TOOL CALLS: {tool_calls}")
        print("-" * 20)
else:
    print("No architect process found.")
conn.close()
