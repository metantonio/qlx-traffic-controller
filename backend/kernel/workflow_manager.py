import os
import json
from typing import Dict, Any, List, Optional
from pydantic import BaseModel
from backend.core.logger import get_kernel_logger

logger = get_kernel_logger("AgentOS.Workflow.Manager")

class WorkflowStep(BaseModel):
    agent_id: str
    task_template: str

class Workflow(BaseModel):
    id: str
    name: str
    description: str
    steps: List[WorkflowStep]
    variables: List[str] = [] # e.g. ["folder", "file"]

class WorkflowManager:
    def __init__(self, config_path: str):
        self.config_path = config_path
        self._ensure_config_exists()

    def _ensure_config_exists(self):
        os.makedirs(os.path.dirname(self.config_path), exist_ok=True)
        if not os.path.exists(self.config_path):
            with open(self.config_path, 'w') as f:
                json.dump({}, f)

    def load_workflows(self) -> Dict[str, Workflow]:
        try:
            if not os.path.exists(self.config_path):
                return {}
            with open(self.config_path, 'r') as f:
                data = json.load(f)
                return {k: Workflow(**v) for k, v in data.items()}
        except Exception as e:
            logger.error(f"Failed to load workflows: {e}")
            return {}

    def save_workflows(self, workflows: Dict[str, Workflow]):
        try:
            with open(self.config_path, 'w') as f:
                json.dump({k: v.model_dump() for k, v in workflows.items()}, f, indent=4)
        except Exception as e:
            logger.error(f"Failed to save workflows: {e}")

    def get_workflow(self, workflow_id: str) -> Optional[Workflow]:
        workflows = self.load_workflows()
        return workflows.get(workflow_id)

    def add_workflow(self, workflow: Workflow):
        workflows = self.load_workflows()
        workflows[workflow.id] = workflow
        self.save_workflows(workflows)

    def remove_workflow(self, workflow_id: str):
        workflows = self.load_workflows()
        if workflow_id in workflows:
            del workflows[workflow_id]
            self.save_workflows(workflows)

    def list_workflows(self) -> List[Workflow]:
        workflows = self.load_workflows()
        return list(workflows.values())

# Singleton instance
workflow_manager = WorkflowManager(os.path.join(os.path.dirname(__file__), "..", "data", "workflows.json"))
