from backend.agents.base import BaseAgent
from typing import Callable

class DocumentAgent(BaseAgent):
    def __init__(self):
        super().__init__(
            name="document_agent",
            role="Document Analyzer",
            system_prompt="You are a document analysis agent. You extract insights, summarize text, and index knowledge from files.",
            allowed_tools=["filesystem_read", "pdf_parse", "knowledge_index"]
        )
        
    async def execute_task(self, task_input: str, orchestrator_callback: Callable):
        # Implementation via LangGraph / native Langchain logic
        # For now, placeholder for LLM execution logic
        return {"status": "success", "result": f"Document analyzed correctly for '{task_input}'"}
        
class SystemAssistantAgent(BaseAgent):
    def __init__(self):
        super().__init__(
            name="system_assistant",
            role="General Automation",
            system_prompt="You are a system assistant capable of general automation tasks.",
            allowed_tools=["filesystem_read", "shell_execute"]
        )
        
    async def execute_task(self, task_input: str, orchestrator_callback: Callable):
        return {"status": "success", "result": "System Assistant processed request"}
