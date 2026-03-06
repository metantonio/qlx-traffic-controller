import asyncio
import os
import sys

# Ensure backend is in PYTHONPATH
sys.path.insert(0, os.path.abspath(os.path.join(os.path.dirname(__file__), '..')))

from backend.kernel.workflow_manager import workflow_manager, Workflow, WorkflowStep
from backend.kernel.workflow_orchestrator import workflow_orchestrator
from backend.kernel.batch_orchestrator import batch_orchestrator
from backend.core.logger import get_kernel_logger

logger = get_kernel_logger("QLX-TC.Test.Pipeline.Conditions")

async def run_test():
    # 1. Register a test workflow with conditional logic
    wf = Workflow(
        id="test_conditional_routing",
        name="Conditional Routing Test",
        description="Tests dynamic agents and conditional execution.",
        variables=["file_path", "filename"],
        steps=[
            # Step 1: The "Router" Agent uses pipeline_tools to set `file_type`
            # Note: We use the default kernel agent but tell it to use the tool.
            WorkflowStep(
                agent_id="kernel_agent",
                task_template="Analyze the filename '{{filename}}'. If it ends in .txt, use the 'set_pipeline_variable' tool to set 'file_type' to 'text'. Otherwise set it to 'unknown'."
            ),
            # Step 2: Only executes if file_type is text
            WorkflowStep(
                agent_id="kernel_agent",
                task_template="This step should only run for text files. Summarize: {{file_path}}.",
                condition="{{file_type}} == text"
            ),
            # Step 3: Only executes if file_type is unknown
            WorkflowStep(
                agent_id="kernel_agent", 
                task_template="This step should only run for unknown files.",
                condition="{{file_type}} == unknown"
            )
        ]
    )
    workflow_manager.add_workflow(wf)
    logger.info("Added test workflow.")

    # 2. Add some test files
    test_folder = os.path.abspath(os.path.join(os.path.dirname(__file__), "data", "test_batch_folder"))
    os.makedirs(test_folder, exist_ok=True)
    with open(os.path.join(test_folder, "test_file.txt"), 'w') as f:
        f.write("Hello world, this is a text file.")
    with open(os.path.join(test_folder, "test_file.bin"), 'w') as f:
        f.write("BINARY DATA HERE")

    # 3. Start batch
    logger.info("Starting batch job...")
    job_id = await batch_orchestrator.start_batch(test_folder, wf.id, {})

    # 4. Wait for it to complete
    while True:
        status = batch_orchestrator.get_job_status(job_id)
        logger.info(f"Batch {job_id} status: {status['status']} ({status['processed_files']}/{status['total_files']})")
        if status['status'] == 'completed':
            break
        await asyncio.sleep(5)
        
    logger.info("Test completed. Check execution logs to verify conditions were met.")

if __name__ == "__main__":
    asyncio.run(run_test())
