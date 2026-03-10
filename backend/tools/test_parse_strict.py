import json
import re

def _parse_text_tool_calls_new(content: str, tool_names: set) -> list[tuple]:
    calls = []
    
    # 1. Strip markdown fences if present
    content = re.sub(r'```json\n', '', content)
    content = re.sub(r'```\n?', '', content)
    
    # 2. Find all starting braces
    for start in range(len(content)):
        if content[start] not in ('{', '['): continue
            
        # 3. Try to parse by finding matching closing brace
        # We try every possible end brace from the back
        for end in range(len(content), start + 1, -1):
            if content[end-1] not in ('}', ']'): continue
                
            candidate = content[start:end]
            try:
                # We do NOT do any aggressive comment stripping here, 
                # because it ruins URLs and LLM JSON is usually valid anyway
                parsed = json.loads(candidate)
                
                # Verify format
                if isinstance(parsed, dict):
                    # OpenAI/Standard format
                    if "name" in parsed and parsed["name"] in tool_names:
                        args = parsed.get("arguments", parsed.get("args", {}))
                        calls.append((parsed["name"], args if isinstance(args, dict) else {"input": str(args)}))
                        return calls # Stop on first valid
                    # Alternative format
                    elif "tool" in parsed and parsed["tool"] in tool_names:
                        calls.append((parsed["tool"], parsed.get("input", {})))
                        return calls
                elif isinstance(parsed, list):
                    for item in parsed:
                        if isinstance(item, dict) and "name" in item and item["name"] in tool_names:
                            args = item.get("arguments", item.get("args", {}))
                            calls.append((item["name"], args if isinstance(args, dict) else {"input": str(args)}))
                    if calls: return calls
            except json.JSONDecodeError:
                pass
                
    return calls

test_content = 'Assistant wrote: {"name": "fetch", "arguments": {"url": "https://example.com"}} ...'
print(_parse_text_tool_calls_new(test_content, {"fetch"}))
