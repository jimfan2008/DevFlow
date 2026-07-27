target = '/home/jim/DevFlow/tests/test_cases/test_tdd_0016_devflow.py'
with open(target, 'rb') as f:
    raw = f.read()
lines = raw.split(b'\n')
print(f"Total lines: {len(lines)}")
# Check for U+2026
pos = 0
found = 0
while True:
    pos = raw.find(b'\xe2\x80\xa6', pos)
    if pos == -1:
        break
    line_num = raw[:pos].count(b'\n') + 1
    context_start = max(0, pos - 20)
    context_end = min(len(raw), pos + 20)
    context = raw[context_start:context_end]
    print(f"FOUND U+2026 at byte {pos}, line {line_num}: context={context!r}")
    found += 1
    pos += 1
if found == 0:
    print("No U+2026 found.")
else:
    print(f"Total U+2026 occurrences: {found}")
# Also check for other non-ASCII
text = raw.decode('utf-8')
for i, ch in enumerate(text):
    if ord(ch) > 127:
        line = text[:i].count('\n') + 1
        print(f"Non-ASCII U+{ord(ch):04X} at line {line}, char index {i}")
        if found > 5:
            print("... (more found)")
            break
