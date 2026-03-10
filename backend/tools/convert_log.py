try:
    with open('backend/tools/verify_final.txt', 'r', encoding='utf-16le', errors='ignore') as f:
        content = f.read()
except:
    with open('backend/tools/verify_final.txt', 'r', encoding='utf-8', errors='ignore') as f:
        content = f.read()

lines = content.split('\n')[-60:]
ascii_lines = [line.encode('ascii', 'ignore').decode('ascii') for line in lines]
with open('backend/tools/ascii_log.txt', 'w', encoding='utf-8') as f:
    f.write('\n'.join(ascii_lines))
