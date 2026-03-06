import asyncio
import logging
import uuid
import os
from typing import Dict, Any, List, Optional
from backend.core.logger import get_kernel_logger
from backend.kernel.workflow_orchestrator import workflow_orchestrator
from backend.kernel.memory_bus import system_memory_bus, MessagePayload

logger = get_kernel_logger("QLX-TC.Batch.Orchestrator")

class BatchJob:
    def __init__(self, folder_path: str, workflow_id: str, variables: Dict[str, str]):
        self.id = str(uuid.uuid4())
        self.folder_path = folder_path
        self.workflow_id = workflow_id
        self.extra_variables = variables
        self.total_files = 0
        self.processed_files = 0
        self.workflow_execution_ids = []
        self.status = "pending"

class BatchOrchestrator:
    def __init__(self):
        self.active_jobs: Dict[str, BatchJob] = {}
        # We could also subscribe to workflow completion to track batch progress
        system_memory_bus.subscribe("workflow_progress", self._handle_workflow_progress)

    async def start_batch(self, folder_path: str, workflow_id: str, variables: Dict[str, str] = None) -> str:
        if not os.path.isdir(folder_path):
            raise ValueError(f"Path {folder_path} is not a valid directory.")

        job = BatchJob(folder_path, workflow_id, variables or {})
        self.active_jobs[job.id] = job
        
        files = [f for f in os.listdir(folder_path) if os.path.isfile(os.path.join(folder_path, f))]
        job.total_files = len(files)
        job.status = "running"
        
        logger.info(f"Starting Batch Job {job.id} for folder {folder_path} ({job.total_files} files)")

        # In a real system, we might want to limit concurrency here
        for filename in files:
            file_path = os.path.join(folder_path, filename)
            
            # Prepare variables for this specific file
            instance_vars = job.extra_variables.copy()
            instance_vars["file_path"] = file_path
            instance_vars["filename"] = filename
            
            try:
                execution_id = await workflow_orchestrator.start_workflow(workflow_id, instance_vars)
                job.workflow_execution_ids.append(execution_id)
                logger.debug(f"Spawned workflow {execution_id} for file {filename}")
            except Exception as e:
                logger.error(f"Failed to start workflow for file {filename} in batch {job.id}: {e}")

        return job.id

    async def _handle_workflow_progress(self, msg: MessagePayload):
        data = msg.data
        if data.get("status") == "completed":
            workflow_id = data.get("workflow_id")
            
            # Find which batch this workflow belongs to
            for job in self.active_jobs.values():
                if workflow_id in job.workflow_execution_ids:
                    job.processed_files += 1
                    logger.info(f"Batch {job.id}: Progress {job.processed_files}/{job.total_files}")
                    
                    if job.processed_files >= job.total_files:
                        job.status = "completed"
                        logger.info(f"Batch Job {job.id} COMPLETED.")
                        # Notify system
                        await system_memory_bus.publish(MessagePayload(
                            source_pid="kernel",
                            target_pid="BROADCAST",
                            event_type="batch_progress",
                            data={
                                "batch_id": job.id,
                                "status": "completed",
                                "total_files": job.total_files
                            }
                        ))
                    break

    def get_job_status(self, job_id: str) -> Optional[Dict[str, Any]]:
        job = self.active_jobs.get(job_id)
        if not job: return None
        return {
            "id": job.id,
            "folder": job.folder_path,
            "workflow_id": job.workflow_id,
            "total_files": job.total_files,
            "processed_files": job.processed_files,
            "status": job.status
        }

# Global singleton
batch_orchestrator = BatchOrchestrator()
