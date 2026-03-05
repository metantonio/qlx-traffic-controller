from langchain_ollama import ChatOllama
from langchain_core.messages import HumanMessage, SystemMessage, AIMessage, ToolMessage
from langchain_core.tools import BaseTool
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
        Manual ReAct loop using only stable langchain-core primitives.
        Compatible with langchain-core 0.3.x + langchain-ollama.
        """
        tool_map = {t.name: t for t in tools}
        
        # Build a tool schema description for the system prompt
        tool_descriptions = "\n".join([
            f"- {t.name}: {t.description}" for t in tools
        ])
        
        full_system = (
            f"{system_prompt}\n\n"
            "You have access to the following tools:\n"
            f"{tool_descriptions}\n\n"
            "To use a tool, respond ONLY with a JSON block in this format:\n"
            '{"tool": "<tool_name>", "input": "<argument>"}\n'
            "After receiving the tool result, continue reasoning and provide a Final Answer.\n"
            "When you have enough information, respond with:\n"
            "Final Answer: <your answer here>"
        )
        
        messages = [
            SystemMessage(content=full_system),
            HumanMessage(content=user_prompt)
        ]
        
        for iteration in range(5):  # Max 5 ReAct iterations
            response = await self._client.ainvoke(messages)
            content = response.content.strip()
            
            logger.debug(f"Agent iteration {iteration+1}: {content[:200]}")
            
            # Check for Final Answer
            if "Final Answer:" in content:
                final = content.split("Final Answer:", 1)[-1].strip()
                logger.info(f"Agent produced final answer after {iteration+1} iterations.")
                return final
            
            # Check for a tool call (JSON block)
            try:
                # Try to parse a JSON tool call from the response
                json_start = content.find("{")
                json_end = content.rfind("}") + 1
                if json_start != -1 and json_end > json_start:
                    tool_call = json.loads(content[json_start:json_end])
                    tool_name = tool_call.get("tool")
                    tool_input = tool_call.get("input", "")
                    
                    if tool_name and tool_name in tool_map:
                        logger.info(f"Agent invoking tool: {tool_name}({tool_input!r})")
                        tool_result = tool_map[tool_name].run(tool_input)
                        
                        # Append assistant message + tool result to conversation
                        messages.append(AIMessage(content=content))
                        messages.append(HumanMessage(content=f"Tool result for {tool_name}:\n{tool_result}"))
                        continue  # Next iteration
            except (json.JSONDecodeError, KeyError):
                pass
            
            # No tool call detected and no Final Answer — treat content as answer
            logger.info("Agent returned answer without explicit Final Answer marker.")
            return content
        
        # Exhausted iterations — return last response
        last_content = messages[-1].content if messages else "No response from agent."
        logger.warning("Agent reached max iterations without Final Answer.")
        return last_content
