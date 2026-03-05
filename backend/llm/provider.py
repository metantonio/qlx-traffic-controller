from langchain_ollama import ChatOllama
from langchain_core.messages import HumanMessage, SystemMessage, AIMessage, ToolMessage
from langchain_core.tools import BaseTool
from langchain_core.tools import tool as lc_tool
from backend.core.config import settings
import logging
import json

logger = logging.getLogger("AgentOS.LLMProvider")


class LLMProvider:
    """Abstraction layer for language models."""
    
    def __init__(self, provider: str = None, model: str = None):
        self.provider = provider or settings.DEFAULT_PROVIDER
        self.model = model or settings.DEFAULT_MODEL
        self._client = self._initialize_client()
        
    def _initialize_client(self):
        if self.provider == "ollama":
            return ChatOllama(model=self.model, base_url=settings.OLLAMA_BASE_URL)
        elif self.provider in ["openai", "anthropic"]:
            raise NotImplementedError(f"Provider {self.provider} support is pending.")
        else:
            raise ValueError(f"Unknown LLM Provider {self.provider}")
            
    def generate(self, system_prompt: str, user_prompt: str) -> str:
        """Synchronous generation."""
        messages = [
            SystemMessage(content=system_prompt),
            HumanMessage(content=user_prompt)
        ]
        response = self._client.invoke(messages)
        return response.content
        
    async def agenerate(self, system_prompt: str, user_prompt: str) -> str:
        """Asynchronous generation (no tools)."""
        messages = [
            SystemMessage(content=system_prompt),
            HumanMessage(content=user_prompt)
        ]
        response = await self._client.ainvoke(messages)
        return response.content

    async def aexecute_agent(self, system_prompt: str, user_prompt: str, tools: list[BaseTool]) -> str:
        """
        Agent loop using Ollama native function calling (bind_tools).
        Works with qwen2.5, llama3, mistral and other tool-capable models.
        """
        tool_map = {t.name: t for t in tools}
        llm_with_tools = self._client.bind_tools(tools)
        
        messages = [
            SystemMessage(content=system_prompt),
            HumanMessage(content=user_prompt)
        ]
        
        for iteration in range(5):  # Max 5 tool call iterations
            response = await llm_with_tools.ainvoke(messages)
            messages.append(response)  # Append AIMessage with possible tool_calls
            
            # If the model made no tool calls, we're done
            if not response.tool_calls:
                logger.info(f"Agent finished after {iteration+1} iterations (no more tool calls).")
                return response.content or "Agent completed with no text output."
            
            # Execute each requested tool call
            for tc in response.tool_calls:
                tool_name = tc["name"]
                tool_args = tc["args"]
                tool_call_id = tc["id"]
                
                logger.info(f"[Iteration {iteration+1}] Agent calling tool: {tool_name}({tool_args})")
                
                if tool_name not in tool_map:
                    result = f"Error: tool '{tool_name}' not found in registry."
                    logger.warning(result)
                else:
                    try:
                        # Tools expect a single string arg; pass the first value
                        first_arg = list(tool_args.values())[0] if tool_args else ""
                        result = tool_map[tool_name].run(first_arg)
                        logger.info(f"Tool '{tool_name}' returned: {str(result)[:200]}")
                    except Exception as e:
                        result = f"Tool execution error: {str(e)}"
                        logger.error(result)
                
                # Append tool result back to message chain
                messages.append(ToolMessage(
                    content=str(result),
                    tool_call_id=tool_call_id
                ))
        
        # Fallback: ask for a final summary after all tool results
        logger.warning("Agent reached max iterations. Requesting final summary.")
        messages.append(HumanMessage(content="Please summarize your findings based on the tool results above."))
        final_response = await llm_with_tools.ainvoke(messages)
        return final_response.content or "Agent reached iteration limit."
