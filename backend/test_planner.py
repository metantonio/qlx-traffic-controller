import asyncio
import os
import sys

sys.path.insert(0, os.path.abspath(os.path.join(os.path.dirname(__file__), '..')))

from backend.kernel.workflow_manager import workflow_manager, Workflow, WorkflowStep
from backend.kernel.agent_manager import agent_manager, CustomAgent
from backend.kernel.batch_orchestrator import batch_orchestrator
from backend.core.logger import get_kernel_logger

logger = get_kernel_logger("QLX-TC.Test.Planner")

async def run_test():
    # 1. Create the specialized txt creator agent
    txt_agent = CustomAgent(
        id="creator_txt_agent",
        name="TXT Document Creator",
        description="Creates or appends text summaries to files. Excellent at formatting summaries.",
        static_tools=["shell_execute", "filesystem_read"],
        provider="ollama",
        model="qwen2.5-coder:7b"
    )
    agent_manager.add_agent(txt_agent)
    logger.info("Created creator_txt_agent.")

    # 2. Define the workflow
    wf_name = "planner_test_wf"
    wf = Workflow(
        id=wf_name,
        name="Planner Dynamic Workflow",
        description="A planner dynamically picks agents to read and summarize files.",
        variables=["file_path", "filename"],
        steps=[
            # Step 1: PLANNER
            WorkflowStep(
                agent_id="kernel_agent",
                task_template=(
                    "You are a Planner Agent. First, use `list_available_agents` to see who is available. "
                    "Next, you must plan the next two steps for the file: {{file_path}}. "
                    "Decide on an agent to physically read the file (hint: kernel_agent can do it) and "
                    "an agent to write the summary of the file (hint: look for a txt creator agent). "
                    "After deciding, use `set_pipeline_variable` TWICE: "
                    "1. key='reader_agent', value=<your choice for reading> "
                    "2. key='writer_agent', value=<your choice for writing>"
                )
            ),
            # Step 2: DYNAMIC READER
            WorkflowStep(
                agent_id="{{reader_agent}}",
                task_template="Read the contents of the file located at: {{file_path}}. Your sole job is to output the content so the next agent can summarize it."
            ),
            # Step 3: DYNAMIC WRITER
            WorkflowStep(
                agent_id="{{writer_agent}}",
                task_template=(
                    "Take the previous conversation context which contains the file contents. "
                    "Summarize those contents. Then, append the summary inside a new line to the file: "
                    "c:/Repositorios/qlx-traffic-controller/workspace/summary_batch_processor.txt "
                    "If the file doesn't exist, create it. "
                    "Do NOT overwrite the file, append to it. Format it nicely indicating the source file: {{filename}}."
                )
            )
        ]
    )
    workflow_manager.add_workflow(wf)
    logger.info("Added planner test workflow.")

    # 3. Setup batch folder
    test_folder = os.path.abspath(os.path.join(os.path.dirname(__file__), "data", "test_batch_folder"))
    workspace_folder = os.path.abspath(os.path.join(os.path.dirname(__file__), "..", "workspace"))
    os.makedirs(test_folder, exist_ok=True)
    os.makedirs(workspace_folder, exist_ok=True)
    
    # 4. Start batch
    logger.info(f"Starting batch job on {test_folder}...")
    job_id = await batch_orchestrator.start_batch(test_folder, wf_name, {})

    # 5. Monitor
    while True:
        status = batch_orchestrator.get_job_status(job_id)
        logger.info(f"Batch {job_id} status: {status['status']} ({status['processed_files']}/{status['total_files']})")
        if status['status'] in ('completed', 'failed'):
            break
        await asyncio.sleep(5)
        
    logger.info("Test finished. Please check workspace/summary_batch_processor.txt")

if __name__ == "__main__":
    asyncio.run(run_test())
