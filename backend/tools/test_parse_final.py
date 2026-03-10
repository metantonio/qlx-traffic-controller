import re
import traceback

content = 'Assistant wrote: {"name": "fetch", "arguments": {"url": "https://example.com"}}'
print("Input content length:", len(content))

for match in re.finditer(r'\{|\[', content):
    start = match.start()
    for end in range(len(content), start + 1, -1):
        char = content[end-1]
        if char not in ('}', ']'):
            continue
        candidate = content[start:end]
        candidate_clean = re.sub(r'(?<!:)//.*$', '', candidate, flags=re.MULTILINE)
        print(f"[{start}:{end}]: candidate='{candidate}' => candidate_clean='{candidate_clean}'")
