import ast
with open('/home/jim/DevFlow/test_agent_swarm_monitoring.py', 'r', encoding='utf-8') as f:
    content = f.read()

# Find em dashes
for i, ch in enumerate(content):
    if ord(ch) == 0x2014:
        line = content[:i].count('\n') + 1
        ctx = content[max(0,i-10):i+10]
        print(f"EM DASH at line {line} pos {i}: {repr(ctx)}")

# Replace
fixed = content.replace('\u2014', '-')
fixed = fixed.replace('\u2013', '-')
fixed = fixed.replace('\u2015', '-')

with open('/home/jim/DevFlow/test_agent_swarm_monitoring.py', 'w', encoding='utf-8') as f:
    f.write(fixed)

# Verify
try:
    ast.parse(fixed)
    print("SYNTAX OK after fix")
except SyntaxError as e:
    print(f"SYNTAX ERROR after fix: {e}")
