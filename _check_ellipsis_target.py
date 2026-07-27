target = '/home/jim/DevFlow/tests/test_cases/test_tdd_0016_devflow.py'
with open(target, 'rb') as f:
    raw = f.read()
lines = raw.split(b'\n')
total_lines = len(lines)
print(f"Total lines: {total_lines}")
# Check for U+2026 (…)
pos = 0
found = 0
while True:
    pos = raw.find(b'\xe2\x80\xa6', pos)
    if pos == -1:
        break
    line_num = raw[:pos].count(b'\n') + 1
    context_start = max(0, pos - 15)
    context_end = min(len(raw), pos + 15)
    context = raw[context_start:context_end]
    print(f"U+2026 at byte {pos}, line {line_num}: context={context!r}")
    found += 1
    pos += 1
if found == 0:
    print("No U+2026 found.")
# Also check for any non-ASCII chars
for i, ch in enumerate(raw.decode('utf-8')):
    if ord(ch) > 127:
        print(f"Non-ASCII U+{ord(ch):04X} at char index {i}")
        break
else:
    print("No non-ASCII chars found.")
