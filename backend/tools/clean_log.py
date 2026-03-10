content = open('backend/tools/full_verify2.log', encoding='utf-16le', errors='ignore').read()
clean_lines = []
for line in content.split('\n')[-30:]:
    clean_line = line.replace('\u274c', '[FAIL]').replace('\u2705', '[SUCCESS]')
    # just basic ascii
    clean_line = clean_line.encode('ascii', 'ignore').decode('ascii')
    clean_lines.append(clean_line)

with open('backend/tools/clean_verify.log', 'w', encoding='utf-8') as f:
    f.write('\n'.join(clean_lines))
