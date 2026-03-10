import re

candidate = '{"name": "fetch", "arguments": {"url": "https://example.com"}}'

print("Match r'//.*$':")
print(repr(re.sub(r'//.*$', '', candidate, flags=re.MULTILINE)))

print("Match r'(?<!:)//.*$':")
print(repr(re.sub(r'(?<!:)//.*$', '', candidate, flags=re.MULTILINE)))

# What about the loop in the provider?
print("Original code approach:")
for start in range(len(candidate)):
    for end in range(len(candidate), start+1, -1):
        if candidate[start] == '{' and candidate[end-1] == '}':
            subc = candidate[start:end]
            subc_clean = re.sub(r'(?<!:)//.*$', '', subc, flags=re.MULTILINE)
            # print(f"[{start}:{end}] clean={repr(subc_clean)}")
            if len(subc) == len(candidate):
                print(f"FULL MATCH clean={repr(subc_clean)}")

