import re
import json

def _parse_text_tool_calls(content: str, tool_names: set) -> list[tuple]:
    calls = []
    print(f"Content: {content}")
    for match in re.finditer(r'\{|\[', content):
        start = match.start()
        print(f"Start at: {start}")
        for end in range(len(content), start + 1, -1):
            char = content[end-1]
            if char not in ('}', ']'):
                continue
            try:
                candidate = content[start:end]
                # print(f"Trying: {candidate}") # uncomment to see everything
                candidate_clean = re.sub(r'(?<!:)//.*, '', candidate, flags=re.MULTILINE)
                parsed = json.loads(candidate_clean)
                print(f"Success: {parsed}")
                break
            except Exception as e:
                print(f"Fail: {e} on {candidate}")
    return calls

content = 'Assistant wrote: {"name": "fetch", "arguments": {"url": "https://example.com"}}'
_parse_text_tool_calls(content, {"fetch"})
