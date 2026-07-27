with open('/home/jim/DevFlow/test_agent_swarm_monitoring.py', 'r', encoding='utf-8') as f:
    lines = f.readlines()
print(f"Total lines: {len(lines)}")
for i in range(1295, min(1310, len(lines))):
    line = lines[i]
    has_em = '\u2014' in line
    marker = " <-- EM DASH" if has_em else ""
    print(f"Line {i+1}: {repr(line[:120])}{marker}")
