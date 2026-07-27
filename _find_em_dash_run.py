with open('/home/jim/DevFlow/test_agent_swarm_monitoring.py', 'r', encoding='utf-8') as f:
    content = f.read()
lines = content.split('\n')
print(f"Total lines: {len(lines)}")
for i, line in enumerate(lines):
    if '\u2014' in line or '\u2013' in line or '\u2015' in line or '\u2018' in line or '\u2019' in line or '\u201c' in line or '\u201d' in line:
        print(f"Line {i+1}: {repr(line[:120])}")
