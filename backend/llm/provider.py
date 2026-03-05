from langchain_ollama import ChatOllama
from langchain_core.messages import HumanMessage, SystemMessage, AIMessage, ToolMessage
from langchain_core.tools import BaseTool
from backend.core.config import settings
import logging
import json
import re

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

    def _parse_text_tool_call(self, content: str, tool_names: set) -> tuple | None:
        """
        Parse tool calls from text in all 3 formats local LLMs produce:
          A) JSON: {"name": "tool", "arguments": {"arg": "val"}}
          B) JSON: {"tool": "tool", "input": "val"}
          C) Python: tool_name("val")
        Returns (tool_name, raw_arg_value_or_dict) or None.
        """
        # Format A & B: JSON block
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
        
        # Format C: Python function call
        for tool_name in tool_names:
            match = re.search(rf'{re.escape(tool_name)}\(["\'](.+?)["\']\)', content)
            if match:
                logger.info(f"Detected Python-style call: {tool_name}('{match.group(1)}')")
                return (tool_name, match.group(1))
        
        return None

    async def aexecute_agent(self, system_prompt: str, user_prompt: str, tools: list[BaseTool], source_pid: str = "kernel") -> str:
        """
        Unified agent loop that works with any LangChain BaseTool objects.
        Handles native tool_calls (PATH 1) and text JSON/Python tool calls (PATH 2).
        
        Args:
            tools: List of BaseTool (from MCP server, StructuredTool, etc.)
            source_pid: The PID of the calling process for logging/telemetry.
        """
        from backend.kernel.memory_bus import system_memory_bus, MessagePayload
        
        tool_map = {t.name: t for t in tools}
        tool_names = set(tool_map.keys())
        
        llm_with_tools = self._client.bind_tools(tools) if tools else self._client
        
        # Inject tool descriptions ONLY if tools are available
        if tools:
            tool_desc = "\n".join([f"- {t.name}: {t.description}" for t in tools])
            capability_block = (
                f"You have access to the following real system tools:\n{tool_desc}\n\n"
                "USE A TOOL when the task requires filesystem or shell interaction. \n"
                "Do not say you cannot do something if a tool can help."
            )
        else:
            capability_block = (
                "NO TOOLS ARE CURRENTLY AUTHORIZED for this session. \n"
                "You must perform the task using only your internal knowledge. \n"
                "If you need tools to complete the task, inform the user they are missing."
            )
            
        full_system = f"{system_prompt}\n\n{capability_block}"
        
        messages = [
            SystemMessage(content=full_system),
            HumanMessage(content=user_prompt)
        ]
        
        for iteration in range(5):
            response = await llm_with_tools.ainvoke(messages)
            messages.append(response)
            content = response.content or ""
            
            # --- PATH 1: Native tool_calls ---
            if response.tool_calls:
                for tc in response.tool_calls:
                    tool_name = tc["name"]
                    tool_args = tc.get("args", {})
                    tool_call_id = tc["id"]
                    
                    logger.info(f"[{source_pid}][Native] Iter {iteration+1}: {tool_name}({tool_args})")
                    
                    # Emit event to memory bus
                    await system_memory_bus.publish(MessagePayload(
                        source_pid=source_pid,
                        target_pid="BROADCAST",
                        event_type="tool_requested",
                        data={"tool": tool_name, "arguments": tool_args}
                    ))
                    
                    if tool_name not in tool_map:
                        result_str = f"Error: tool '{tool_name}' not found."
                    else:
                        try:
                            # arun() handles async properly for all BaseTool subclasses
                            result = await tool_map[tool_name].arun(tool_args)
                            result_str = self._format_tool_result(result)
                            logger.info(f"Tool '{tool_name}' result: {result_str[:300]}")
                        except Exception as e:
                            result_str = f"Tool error: {str(e)}"
                            logger.error(result_str)
                    
                    messages.append(ToolMessage(content=result_str, tool_call_id=tool_call_id))
                continue
            
            # --- PATH 2: Text JSON or Python-style tool call ---
            parsed = self._parse_text_tool_call(content, tool_names)
            if parsed:
                tool_name, raw_args = parsed
                tool = tool_map[tool_name]
                
                # Normalize args to dict using tool schema's first field
                if isinstance(raw_args, dict):
                    kwargs = raw_args
                else:
                    schema = getattr(tool, "args_schema", None)
                    first_field = (
                        list(schema.model_fields.keys())[0]
                        if schema and hasattr(schema, "model_fields") and schema.model_fields
                        else "input"
                    )
                    kwargs = {first_field: str(raw_args)}
                
                logger.info(f"[{source_pid}][Text] Iter {iteration+1}: {tool_name}({kwargs})")
                
                # Emit event to memory bus
                await system_memory_bus.publish(MessagePayload(
                    source_pid=source_pid,
                    target_pid="BROADCAST",
                    event_type="tool_requested",
                    data={"tool": tool_name, "arguments": kwargs}
                ))

                try:
                    result = await tool.arun(kwargs)
                    result_str = self._format_tool_result(result)
                    logger.info(f"Tool '{tool_name}' result: {result_str[:300]}")
                except Exception as e:
                    result_str = f"Tool error: {str(e)}"
                    logger.error(result_str)
                
                # Direct summarization — avoids qwen confusion with multi-turn HumanMessages
                summary_prompt = (
                    f"Task: {user_prompt}\n\n"
                    f"The tool '{tool_name}' returned:\n---\n{result_str}\n---\n\n"
                    "Provide a clear, helpful answer to the task based on this output."
                )
                logger.info("Requesting direct summary from model...")
                summary = await self._client.ainvoke([
                    SystemMessage(content=full_system),
                    HumanMessage(content=summary_prompt)
                ])
                return summary.content or result_str
            
            # --- PATH 3: Final answer (no tool call) ---
            logger.info(f"Agent done after {iteration + 1} iteration(s).")
            return content or "Agent completed with no output."
        
        logger.warning("Agent hit max iterations.")
        messages.append(HumanMessage(content="Summarize your findings based on the tool results."))
        final = await self._client.ainvoke(messages)
        return final.content or "Agent reached iteration limit."

    def _format_tool_result(self, result: any) -> str:
        """
        Helper to format complex tool results into clean strings for the model.
        Handles:
          - Dicts (like shell_execute results) -> returns stdout
          - Lists of TextContent (MCP official server) -> returns joined text
          - Base types -> returns str()
        """
        if isinstance(result, dict):
            # For shell_execute: extract stdout
            if "stdout" in result:
                return result["stdout"]
            return json.dumps(result, indent=2)
            
        if isinstance(result, list):
            # For official MCP server results: [TextContent(text='...'), ...]
            texts = []
            for item in result:
                if hasattr(item, "text"):
                    texts.append(item.text)
                elif isinstance(item, dict) and "text" in item:
                    texts.append(item["text"])
                else:
                    texts.append(str(item))
            return "\n".join(texts)
            
        return str(result)
