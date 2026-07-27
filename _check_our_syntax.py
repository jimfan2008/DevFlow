import ast, sys
with open('/home/jim/DevFlow/test_agent_swarm_monitoring.py', 'rb') as f:
    raw = f.read()
# Check for non-ASCII chars
for i, b in enumerate(raw):
    if b >= 128:
        context = raw[max(0,i-5):i+6]
        print(f"Non-ASCII byte at {i}: {hex(b)}, context: {context!r}")
try:
    ast.parse(raw.decode('utf-8'), filename='test_agent_swarm_monitoring.py')
    print("SYNTAX OK")
except SyntaxError as e:
    print(f"SYNTAX ERROR at line {e.lineno}: {e.msg}")
    sys.exit(1)
