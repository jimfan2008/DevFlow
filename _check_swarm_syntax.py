import ast
with open('/home/jim/DevFlow/test_agent_swarm_monitoring.py', 'r', encoding='utf-8') as f:
    content = f.read()
try:
    ast.parse(content, filename='test_agent_swarm_monitoring.py')
    print("SYNTAX OK")
except SyntaxError as e:
    print(f"SYNTAX ERROR at line {e.lineno}: {e.msg}")
    lines = content.split('\n')
    for i in range(max(0, e.lineno-3), min(len(lines), e.lineno+2)):
        marker = " >>>" if i+1 == e.lineno else "    "
        print(f"{marker} {i+1}: {lines[i]!r}")
