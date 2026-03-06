from typing import Optional, Any
from langchain_ollama import ChatOllama
from langchain_core.messages import HumanMessage, SystemMessage, AIMessage, ToolMessage
from langchain_core.tools import BaseTool
from backend.core.config import settings
import logging
import json
import re

from contextvars import ContextVar

logger = logging.getLogger("QLX-TC.LLMProvider")

# Global context to track which process is calling a tool
current_pid = ContextVar("current_pid", default="kernel")


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
            try:
                from langchain_anthropic import ChatAnthropic
                return ChatAnthropic(
                    model=self.model, 
                    anthropic_api_key=settings.ANTHROPIC_API_KEY,
                    timeout=None,
                    stop=None
                )
            except ImportError:
                raise ImportError("langchain-anthropic is not installed. Please run 'pip install langchain-anthropic'")
            
        elif self.provider == "google":
            if not settings.GOOGLE_API_KEY:
                raise ValueError("GOOGLE_API_KEY not found in settings")
            try:
                from langchain_google_genai import ChatGoogleGenerativeAI
                return ChatGoogleGenerativeAI(
                    model=self.model, 
                    google_api_key=settings.GOOGLE_API_KEY
                )
            except ImportError:
                raise ImportError("langchain-google-genai is not installed. Please run 'pip install langchain-google-genai'")
            
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

    def _parse_text_tool_calls(self, content: str, tool_names: set) -> list[tuple]:
        """
        Parse all tool calls from text. Handles multiple JSON blocks (objects or lists).
        """
        calls = []
        
        # 1. Extract JSON blocks
        # We look for both { (objects) and [ (lists)
        for match in re.finditer(r'\{|\[', content):
            start = match.start()
            for end in range(len(content), start + 1, -1):
                char = content[end-1]
                if char not in ('}', ']'):
                    continue
                
                try:
                    candidate = content[start:end]
                    # Clean comments
                    candidate_clean = re.sub(r'//.*$', '', candidate, flags=re.MULTILINE)
                    
                    parsed = json.loads(candidate_clean)
                    
                    # Handle single object
                    if isinstance(parsed, dict):
                        call = self._extract_call_from_dict(parsed, tool_names)
                        if call:
                            calls.append(call)
                            break # Found valid block starting here
                            
                    # Handle list of objects
                    elif isinstance(parsed, list):
                        found_in_list = False
                        for item in parsed:
                            if isinstance(item, dict):
                                call = self._extract_call_from_dict(item, tool_names)
                                if call:
                                    calls.append(call)
                                    found_in_list = True
                        if found_in_list:
                            break
                            
                except (json.JSONDecodeError, ValueError):
                    continue
        
        # 2. Fallback for Python-style calls if no JSON found
        if not calls:
            for tool_name in tool_names:
                for match in re.finditer(rf'{re.escape(tool_name)}\(["\'](.+?)["\']\)', content):
                    calls.append((tool_name, match.group(1)))
        
        return calls

    def _extract_call_from_dict(self, d: dict, tool_names: set) -> Optional[tuple]:
        """Helper to extract (name, args) from a suspected tool call dict."""
        # OpenAI/Standard format
        if "name" in d and d["name"] in tool_names:
            args = d.get("arguments", d.get("args", {}))
            return (d["name"], args if isinstance(args, dict) else {"input": str(args)})
        # Alternative format
        elif "tool" in d and d["tool"] in tool_names:
            return (d["tool"], d.get("input", {}))
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
                        token = current_pid.set(source_pid)
                        try:
                            result = await tool_map[tool_name].arun(tool_args)
                            result_str = self._format_tool_result(result)
                        except Exception as e:
                            result_str = f"Tool error: {str(e)}"
                        finally:
                            current_pid.reset(token)
                    
                    messages.append(ToolMessage(content=result_str, tool_call_id=tool_call_id))
                continue
            
            # Text based fallback for Ollama
            if self.provider == "ollama":
                parsed_calls = self._parse_text_tool_calls(content, tool_names)
                if parsed_calls:
                    for tool_name, tool_args in parsed_calls:
                        tool = tool_map[tool_name]
                        kwargs = tool_args if isinstance(tool_args, dict) else {"input": str(tool_args)}
                        
                        logger.info(f"[{source_pid}][Text-Fallback] Iter {iteration+1}: {tool_name}({kwargs})")
                        await system_memory_bus.publish(MessagePayload(
                            source_pid=source_pid, target_pid="BROADCAST",
                            event_type="tool_requested", data={"tool": tool_name, "arguments": kwargs}
                        ))

                        try:
                            token = current_pid.set(source_pid)
                            result = await tool.arun(kwargs)
                            result_str = self._format_tool_result(result)
                        except Exception as e:
                            result_str = f"Tool error: {str(e)}"
                        finally:
                            current_pid.reset(token)
                        
                        pseudo_id = f"text_to_tool_{iteration}_{tool_name}"
                        # Ensure we don't overwrite tool_calls if something else set it, but here it should be empty
                        if not response.tool_calls:
                            response.tool_calls = []
                        response.tool_calls.append({"name": tool_name, "args": kwargs, "id": pseudo_id})
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
