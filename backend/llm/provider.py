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

    def _parse_text_tool_call(self, content: str, tool_map: dict) -> tuple[str, str] | None:
        """
        Try to parse a tool call from text content.
        Handles both {"name":..., "arguments":...} and {"tool":..., "input":...} formats.
        Returns (tool_name, tool_input) or None.
        """
        try:
            # Find the outermost JSON block
            start = content.find("{")
            end = content.rfind("}") + 1
            if start == -1 or end <= start:
                return None
            
            parsed = json.loads(content[start:end])
            
            # Format 1: Ollama native-ish  {"name": "shell_execute", "arguments": {...}}
            if "name" in parsed and parsed["name"] in tool_map:
                args = parsed.get("arguments", parsed.get("args", {}))
                first_val = list(args.values())[0] if isinstance(args, dict) and args else str(args)
                return (parsed["name"], str(first_val))
            
            # Format 2: Text ReAct {"tool": "...", "input": "..."}  
            if "tool" in parsed and parsed["tool"] in tool_map:
                return (parsed["tool"], str(parsed.get("input", "")))
                
        except (json.JSONDecodeError, KeyError, IndexError):
            pass
        return None

    async def aexecute_agent(self, system_prompt: str, user_prompt: str, tools: list[BaseTool]) -> str:
        """
        Dual-mode agent loop:
        1. Tries native Ollama bind_tools() function calling.
        2. Falls back to parsing tool call JSON from text content.
        Compatible with qwen2.5-coder and other Ollama models.
        """
        tool_map = {t.name: t for t in tools}
        llm_with_tools = self._client.bind_tools(tools)
        
        messages = [
            SystemMessage(content=system_prompt),
            HumanMessage(content=user_prompt)
        ]
        
        for iteration in range(5):
            response = await llm_with_tools.ainvoke(messages)
            messages.append(response)
            content = response.content or ""
            
            # --- PATH 1: Native tool_calls (function calling protocol) ---
            if response.tool_calls:
                for tc in response.tool_calls:
                    tool_name = tc["name"]
                    tool_args = tc.get("args", {})
                    tool_call_id = tc["id"]
                    
                    logger.info(f"[Native] Iteration {iteration+1}: calling {tool_name}({tool_args})")
                    
                    if tool_name not in tool_map:
                        result = f"Error: tool '{tool_name}' not found."
                    else:
                        try:
                            first_arg = list(tool_args.values())[0] if tool_args else ""
                            result = tool_map[tool_name].run(first_arg)
                            logger.info(f"Tool '{tool_name}' result: {str(result)[:300]}")
                        except Exception as e:
                            result = f"Tool error: {str(e)}"
                            logger.error(result)
                    
                    messages.append(ToolMessage(content=str(result), tool_call_id=tool_call_id))
                continue  # get final answer in next iteration
            
            # --- PATH 2: Text JSON tool call in content ---
            parsed = self._parse_text_tool_call(content, tool_map)
            if parsed:
                tool_name, tool_input = parsed
                logger.info(f"[Text JSON] Iteration {iteration+1}: calling {tool_name}({tool_input!r})")
                try:
                    result = tool_map[tool_name].run(tool_input)
                    logger.info(f"Tool '{tool_name}' result: {str(result)[:300]}")
                except Exception as e:
                    result = f"Tool error: {str(e)}"
                    logger.error(result)
                
                # Feed result back as a human message (text mode — no ToolMessage)
                messages.append(HumanMessage(
                    content=f"Tool '{tool_name}' result:\n{result}\n\nNow answer the original question using this result."
                ))
                continue
            
            # --- PATH 3: Final answer (no tool call) ---
            logger.info(f"Agent finished after {iteration+1} iterations.")
            return content or "Agent completed with no text output."
        
        # Exhausted iterations — request summary
        logger.warning("Agent reached max iterations. Requesting final summary.")
        messages.append(HumanMessage(content="Summarize your findings based on the tool results above."))
        final = await self._client.ainvoke(messages)
        return final.content or "Agent reached iteration limit without a final answer."
