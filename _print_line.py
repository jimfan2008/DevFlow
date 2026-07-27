with open('/home/jim/DevFlow/test_agent_swarm_monitoring.py', 'r', encoding='utf-8') as f:
    lines = f.readlines()
for i, line in enumerate(lines[275:285], start=276):
    has_em = '\u2014' in line or '\u2015' in line
    non_ascii = [(j, c, hex(ord(c))) for j, c in enumerate(line) if ord(c) > 127]
    print(f"Line {i}: {repr(line.rstrip())}")
    if non_ascii:
        print(f"  Non-ASCII chars: {non_ascii}")
    if has_em:
        print(f"  *** EM DASH FOUND ***")
