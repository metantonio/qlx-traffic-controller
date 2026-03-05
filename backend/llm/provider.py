from langchain_ollama import ChatOllama
from langchain_core.messages import HumanMessage, SystemMessage, AIMessage, ToolMessage
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

    def _parse_text_tool_call(self, content: str, tool_names: set) -> tuple | None:
        """
        Parse a JSON tool call from text content.
        Returns (tool_name, args_dict) or None.
        """
        try:
            start = content.find("{")
            end = content.rfind("}") + 1
            if start == -1 or end <= start:
                return None
            
            parsed = json.loads(content[start:end])
            
            # Format A: {"name": "shell_execute", "arguments": {"command": "dir"}}
            if "name" in parsed and parsed["name"] in tool_names:
                args = parsed.get("arguments", parsed.get("args", {}))
                if not isinstance(args, dict):
                    args = {"input": str(args)}
                return (parsed["name"], args)
            
            # Format B: {"tool": "shell_execute", "input": "dir"}
            if "tool" in parsed and parsed["tool"] in tool_names:
                raw_input = parsed.get("input", "")
                return (parsed["tool"], raw_input)  # caller resolves param name
                
        except (json.JSONDecodeError, KeyError, IndexError, AttributeError):
            pass
        return None

    async def aexecute_agent(self, system_prompt: str, user_prompt: str, mcp_tools: list) -> str:
        """
        Dual-mode async agent loop using MCPTool objects.
        Calls tool.execute() directly (async) — no sync wrapper, no nested loop issues.
        Compatible with any Ollama model that supports bind_tools OR text JSON output.
        
        Args:
            mcp_tools: List of MCPTool instances from the system registry.
        """
        # Build two maps: LangChain tools for bind_tools (schema), MCPTool for execution
        lc_tools = [t.to_langchain_tool() for t in mcp_tools]
        exec_map = {t.name: t for t in mcp_tools}  # MCPTool objects
        tool_names = set(exec_map.keys())
        
        llm_with_tools = self._client.bind_tools(lc_tools) if lc_tools else self._client
        
        # Inject tool descriptions into the system message so the model KNOWS it has tools
        tool_desc = "\n".join([f"- {t.name}: {t.description}" for t in mcp_tools])
        full_system = (
            f"{system_prompt}\n\n"
            f"You have access to the following real system tools:\n{tool_desc}\n\n"
            "When the task requires interacting with the system, reading files, or running commands, "
            "USE A TOOL. Do not say you cannot do something if a tool can help."
        )
        
        messages = [
            SystemMessage(content=full_system),
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
                    
                    logger.info(f"[Native] Iter {iteration+1}: {tool_name}({tool_args})")
                    
                    if tool_name not in exec_map:
                        result = f"Error: tool '{tool_name}' not found in registry."
                    else:
                        try:
                            # Await the async execute directly — no sync wrapper needed
                            result = await exec_map[tool_name].execute(**tool_args)
                            logger.info(f"Tool '{tool_name}' result: {str(result)[:300]}")
                        except Exception as e:
                            result = f"Tool error: {str(e)}"
                            logger.error(result)
                    
                    messages.append(ToolMessage(content=str(result), tool_call_id=tool_call_id))
                continue  # get final answer in next iteration
            
            # --- PATH 2: Text JSON tool call in content ---
            parsed = self._parse_text_tool_call(content, tool_names)
            if parsed:
                tool_name, raw_args = parsed
                mcp_tool = exec_map[tool_name]
                
                # Resolve arg name: use the first parameter key from the tool's own spec
                if isinstance(raw_args, dict):
                    kwargs = raw_args
                else:
                    first_param = list(mcp_tool.parameters.keys())[0] if mcp_tool.parameters else "input"
                    kwargs = {first_param: str(raw_args)}
                
                logger.info(f"[Text JSON] Iter {iteration+1}: {tool_name}({kwargs})")
                try:
                    result = await mcp_tool.execute(**kwargs)
                    logger.info(f"Tool '{tool_name}' result: {str(result)[:300]}")
                except Exception as e:
                    result = f"Tool error: {str(e)}"
                    logger.error(result)
                
                messages.append(HumanMessage(
                    content=f"Tool '{tool_name}' returned:\n{result}\n\nNow answer the original question using this information."
                ))
                continue
            
            # --- PATH 3: Final answer ---
            logger.info(f"Agent finished after {iteration + 1} iterations.")
            return content or "Agent completed with no text output."
        
        # Exhausted iterations — request final summary
        logger.warning("Agent hit max iterations, requesting summary.")
        messages.append(HumanMessage(content="Please summarize your findings based on the tool results above."))
        final = await self._client.ainvoke(messages)
        return final.content or "Agent reached iteration limit."
