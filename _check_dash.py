import sys
with open('/home/jim/DevFlow/test_agent_swarm_monitoring.py', 'rb') as f:
    raw = f.read()
print(f"File size: {len(raw)} bytes")
# Search for U+2014 (em dash) which is E2 80 94 in UTF-8
pos = 0
found = []
while True:
    idx = raw.find(b'\xe2\x80\x94', pos)
    if idx == -1:
        break
    found.append(idx)
    pos = idx + 1
pos = 0
found2 = []
while True:
    idx = raw.find(b'\xe2\x80\x95', pos)
    if idx == -1:
        break
    found2.append(idx)
    pos = idx + 1

print(f"U+2014 (em dash) found at byte positions: {found}")
print(f"U+2015 (horizontal bar) found at byte positions: {found2}")

# Also check all non-ASCII
text = raw.decode('utf-8')
for i, ch in enumerate(text):
    if ord(ch) > 127:
        print(f"  char at pos {i}: U+{ord(ch):04X} = {repr(ch)}")

# Count lines by splitting
lines = text.split('\n')
print(f"Total lines: {len(lines)}")
# Show line 280
if len(lines) >= 280:
    print(f"Line 280: {repr(lines[279])}")
    for j, ch in enumerate(lines[279]):
        if ord(ch) > 127:
            print(f"  col {j}: U+{ord(ch):04X}")
