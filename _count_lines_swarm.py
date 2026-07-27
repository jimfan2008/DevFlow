with open('/home/jim/DevFlow/test_agent_swarm_monitoring.py', 'r', encoding='utf-8') as f:
    lines = f.readlines()
print(f"Total lines: {len(lines)}")
for i, line in enumerate(lines):
    if any(ord(c) > 127 for c in line):
        print(f"Line {i+1}: non-ASCII char found: {repr(line[:100])}")
