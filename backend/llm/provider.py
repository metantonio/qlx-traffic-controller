from langchain_ollama import ChatOllama
from langchain_anthropic import ChatAnthropic
from langchain_google_genai import ChatGoogleGenerativeAI
from langchain_core.messages import HumanMessage, SystemMessage, AIMessage, ToolMessage
from langchain_core.tools import BaseTool
from backend.core.config import settings
import logging
import json
import re

logger = logging.getLogger("QLX-TC.LLMProvider")


class LLMProvider:
    """Abstraction layer for language models."""
    
    def __init__(self, provider: str = None, model: str = None):
        self.provider = provider or settings.DEFAULT_PROVIDER
        self.model = model or settings.DEFAULT_MODEL
        self._client = self._initialize_client()
        
    def _initialize_client(self):
        logger.info(f"Initializing LLM Client: {self.provider} / {self.model}")
        
        if self.provider == "ollama":
            return ChatOllama(model=self.model, base_url=settings.OLLAMA_BASE_URL)
            
        elif self.provider == "anthropic":
            if not settings.ANTHROPIC_API_KEY:
                raise ValueError("ANTHROPIC_API_KEY not found in settings")
            return ChatAnthropic(
                model=self.model, 
                anthropic_api_key=settings.ANTHROPIC_API_KEY,
                timeout=None,
                stop=None
            )
            
        elif self.provider == "google":
            if not settings.GOOGLE_API_KEY:
                raise ValueError("GOOGLE_API_KEY not found in settings")
            return ChatGoogleGenerativeAI(
                model=self.model, 
                google_api_key=settings.GOOGLE_API_KEY
            )
            
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

    def _parse_text_tool_call(self, content: str, tool_names: set) -> tuple | None:
        """
        Parse tool calls from text in all 3 formats local LLMs produce.
        """
        try:
            start = content.find("{")
            end = content.rfind("}") + 1
            if start != -1 and end > start:
                parsed = json.loads(content[start:end])
                if "name" in parsed and parsed["name"] in tool_names:
                    args = parsed.get("arguments", parsed.get("args", {}))
                    return (parsed["name"], args if isinstance(args, dict) else {"input": str(args)})
                if "tool" in parsed and parsed["tool"] in tool_names:
                    return (parsed["tool"], parsed.get("input", ""))
        except (json.JSONDecodeError, KeyError, IndexError):
            pass
        
        for tool_name in tool_names:
            match = re.search(rf'{re.escape(tool_name)}\(["\'](.+?)["\']\)', content)
            if match:
                logger.info(f"Detected Python-style call: {tool_name}('{match.group(1)}')")
                return (tool_name, match.group(1))
        
        return None

    async def aexecute_agent(
        self, 
        system_prompt: str, 
        user_prompt: str, 
        tools: list[BaseTool], 
        source_pid: str = "kernel",
        initial_history: list[dict] = None
    ) -> tuple[str, list[dict]]:
        """
        Unified agent loop that works with any LangChain BaseTool objects.
        """
        from backend.kernel.memory_bus import system_memory_bus, MessagePayload
        
        tool_map = {t.name: t for t in tools}
        tool_names = set(tool_map.keys())
        
        # Anthropic/Google handle tool binding slightly differently but bind_tools is standard in LangChain
        llm_with_tools = self._client.bind_tools(tools) if tools else self._client
        
        if tools:
            tool_desc = "\n".join([f"- {t.name}: {t.description}" for t in tools])
            capability_block = (
                f"You have access to the following real system tools:\n{tool_desc}\n\n"
                "USE A TOOL when the task requires filesystem or shell interaction. \n"
                "Do not say you cannot do something if a tool can help."
            )
        else:
            capability_block = "NO TOOLS ARE CURRENTLY AUTHORIZED for this session."
            
        full_system = f"{system_prompt}\n\n{capability_block}"
        
        # Build message history
        messages = []
        if initial_history:
            for m in initial_history:
                role = m.get("role")
                content = m.get("content")
                if role == "system": continue 
                elif role == "user": messages.append(HumanMessage(content=content))
                elif role == "assistant": 
                    tc = m.get("tool_calls")
                    messages.append(AIMessage(content=content, tool_calls=tc or []))
                elif role == "tool":
                    messages.append(ToolMessage(content=content, tool_call_id=m.get("tool_call_id")))
            
            messages.insert(0, SystemMessage(content=full_system))
            if user_prompt and (not messages or messages[-1].content != user_prompt):
                messages.append(HumanMessage(content=user_prompt))
        else:
            messages = [
                SystemMessage(content=full_system),
                HumanMessage(content=user_prompt)
            ]
        
        def _msgs_to_dicts(msgs):
            dicts = []
            for m in msgs:
                if isinstance(m, SystemMessage): dicts.append({"role": "system", "content": m.content})
                elif isinstance(m, HumanMessage): dicts.append({"role": "user", "content": m.content})
                elif isinstance(m, AIMessage): 
                    dicts.append({
                        "role": "assistant", 
                        "content": m.content,
                        "tool_calls": getattr(m, "tool_calls", [])
                    })
                elif isinstance(m, ToolMessage): 
                    dicts.append({
                        "role": "tool", 
                        "content": m.content, 
                        "tool_call_id": m.tool_call_id
                    })
            return dicts

        for iteration in range(10): # Increased iteration count for more complex tasks
            response = await llm_with_tools.ainvoke(messages)
            messages.append(response)
            content = response.content or ""
            
            if response.tool_calls:
                for tc in response.tool_calls:
                    tool_name = tc["name"]
                    tool_args = tc.get("args", {})
                    tool_call_id = tc["id"]
                    
                    logger.info(f"[{source_pid}][Native] Iter {iteration+1}: {tool_name}({tool_args})")
                    
                    await system_memory_bus.publish(MessagePayload(
                        source_pid=source_pid, target_pid="BROADCAST",
                        event_type="tool_requested", data={"tool": tool_name, "arguments": tool_args}
                    ))
                    
                    if tool_name not in tool_map:
                        result_str = f"Error: tool '{tool_name}' not found."
                    else:
                        try:
                            result = await tool_map[tool_name].arun(tool_args)
                            result_str = self._format_tool_result(result)
                        except Exception as e:
                            result_str = f"Tool error: {str(e)}"
                    
                    messages.append(ToolMessage(content=result_str, tool_call_id=tool_call_id))
                continue
            
            # Text based fallback for Ollama
            if self.provider == "ollama":
                parsed = self._parse_text_tool_call(content, tool_names)
                if parsed:
                    tool_name, raw_args = parsed
                    tool = tool_map[tool_name]
                    kwargs = raw_args if isinstance(raw_args, dict) else {"input": str(raw_args)}
                    
                    logger.info(f"[{source_pid}][Text] Iter {iteration+1}: {tool_name}({kwargs})")
                    await system_memory_bus.publish(MessagePayload(
                        source_pid=source_pid, target_pid="BROADCAST",
                        event_type="tool_requested", data={"tool": tool_name, "arguments": kwargs}
                    ))

                    try:
                        result = await tool.arun(kwargs)
                        result_str = self._format_tool_result(result)
                    except Exception as e:
                        result_str = f"Tool error: {str(e)}"
                    
                    pseudo_id = f"text_to_tool_{iteration}"
                    messages[-1].tool_calls = [{"name": tool_name, "args": kwargs, "id": pseudo_id}]
                    messages.append(ToolMessage(content=result_str, tool_call_id=pseudo_id))
                    continue # Continue to let it summarize or use more tools

            return content or "Agent completed.", _msgs_to_dicts(messages)
        
        return "Max iterations hit.", _msgs_to_dicts(messages)

    def _format_tool_result(self, result: any) -> str:
        if isinstance(result, dict):
            if "stdout" in result: return result["stdout"]
            return json.dumps(result, indent=2)
        if isinstance(result, list):
            texts = []
            for item in result:
                if hasattr(item, "text"): texts.append(item.text)
                elif isinstance(item, dict) and "text" in item: texts.append(item["text"])
                else: texts.append(str(item))
            return "\n".join(texts)
        return str(result)
