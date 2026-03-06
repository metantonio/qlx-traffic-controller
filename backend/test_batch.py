import requests
import time

BASE_URL = "http://localhost:8000/api"

# 1. Create a Workflow
workflow_data = {
    "id": "batch_test_wf",
    "name": "Batch Test Workflow",
    "description": "Tests batch processing",
    "steps": [
        {
            "agent_id": "kernel",
            "task_template": "Read the file {{file_path}} and summarize its contents. The filename is {{filename}}."
        }
    ],
    "variables": ["file_path", "filename"]
}

print("Creating workflow...")
response = requests.post(f"{BASE_URL}/workflows", json=workflow_data)
print(response.json())

# 2. Start Batch Job
print("\nStarting batch job...")
batch_request = {
    "folder_path": "c:/Repositorios/qlx-traffic-controller/backend/data/test_batch_folder",
    "workflow_id": "batch_test_wf",
    "variables": {}
}

response = requests.post(f"{BASE_URL}/batch", json=batch_request)
print(response.json())

job_id = response.json().get("job_id")

if job_id:
    # 3. Poll Status
    print(f"\nPolling status for job {job_id}...")
    for _ in range(10):
        time.sleep(2)
        res = requests.get(f"{BASE_URL}/batch/{job_id}")
        data = res.json()
        print(f"Status: {data['status']} | Progress: {data['processed_files']}/{data['total_files']}")
        if data['status'] == 'completed':
            print("Batch job finished!")
            break
