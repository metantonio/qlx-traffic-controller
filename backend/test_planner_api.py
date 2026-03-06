import urllib.request
import urllib.error
import json
import time
import os

BASE_URL = "http://127.0.0.1:8000/api"

def request(method, endpoint, data=None):
    url = f"{BASE_URL}{endpoint}"
    req = urllib.request.Request(url, method=method)
    if data:
        json_data = json.dumps(data).encode('utf-8')
        req.add_header('Content-Type', 'application/json')
        req.data = json_data
    
    try:
        with urllib.request.urlopen(req) as response:
            return json.loads(response.read().decode())
    except urllib.error.HTTPError as e:
        print(f"HTTPError {e.code}: {e.read().decode()}")
        raise

def run_test():
    try:
        request("DELETE", "/agents/custom/creator_txt_agent")
    except Exception:
        pass
        
    summary_file = "c:/Repositorios/qlx-traffic-controller/workspace/summary_batch_processor.txt"
    try:
        if os.path.exists(summary_file):
            os.remove(summary_file)
    except Exception:
        pass
    
    print("1. Creating specialized creator_txt_agent...")
    txt_agent = {
        "id": "creator_txt_agent",
        "name": "TXT Document Creator",
        "description": "Creates or appends text summaries to files. Excellent at formatting summaries.",
        "static_tools": ["shell_execute", "filesystem_append"],
        "mcp_servers": []
    }
    request("POST", "/agents/custom", txt_agent)

    try:
        request("DELETE", "/workflows/planner_test_wf")
    except Exception:
        pass

    print("2. Creating Planner Dynamic Workflow...")
    wf = {
        "id": "planner_test_wf",
        "name": "Planner Dynamic Workflow",
        "description": "A planner dynamically picks agents to read and summarize files.",
        "variables": ["file_path", "filename"],
        "steps": [
            {
                "agent_id": "kernel_agent",
                "task_template": (
                    "You are a Planner Agent. First, use `list_available_agents` tool to see who is available. "
                    "Next, you must plan the next two steps for the file: {{file_path}}. "
                    "Decide on an agent to physically read the file (hint: kernel_agent can do it) and "
                    "an agent to write the summary of the file (hint: look for a txt creator agent). "
                    "After deciding, use `set_pipeline_variable` tool TWICE: "
                    "1. key='reader_agent', value=<your choice for reading> "
                    "2. key='writer_agent', value=<your choice for writing>"
                )
            },
            {
                "agent_id": "{{reader_agent}}",
                "task_template": "Read the contents of the file located at: {{file_path}}. Your sole job is to output the content so the next agent can summarize it."
            },
            {
                "agent_id": "{{writer_agent}}",
                "task_template": (
                    "Take the previous conversation context which contains the file contents. "
                    "Summarize those contents. Then, using the `filesystem_append` tool, append the summary inside a new line to the file: "
                    "c:/Repositorios/qlx-traffic-controller/workspace/summary_batch_processor.txt "
                    "Format it nicely indicating the source file: {{filename}}."
                )
            }
        ]
    }
    request("POST", "/workflows", wf)

    print("3. Starting batch job...")
    test_folder = os.path.abspath(os.path.join(os.path.dirname(__file__), "data", "test_batch_folder")).replace("\\", "/")
    workspace_folder = os.path.abspath(os.path.join(os.path.dirname(__file__), "..", "workspace")).replace("\\", "/")
    os.makedirs(test_folder, exist_ok=True)
    os.makedirs(workspace_folder, exist_ok=True)

    batch_payload = {
        "folder_path": test_folder,
        "workflow_id": "planner_test_wf",
        "variables": {}
    }
    res = request("POST", "/batch", batch_payload)
    job_id = res["job_id"]
    print(f"Batch started with ID: {job_id}")

    print("4. Polling for completion...")
    while True:
        status = request("GET", f"/batch/{job_id}")
        print(f"Batch {job_id} status: {status.get('status')} ({status.get('processed_files')}/{status.get('total_files')})")
        if status.get('status') in ('completed', 'failed'):
            break
        time.sleep(5)
        
    print("Test finished. Please check workspace/summary_batch_processor.txt")

if __name__ == "__main__":
    run_test()
