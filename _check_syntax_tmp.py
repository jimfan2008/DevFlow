import ast, sys
with open('/home/jim/DevFlow/test_system_monitor_dashboard.py', 'r') as f:
    source = f.read()
lines = source.split('\n')
print(f"Total lines: {len(lines)}")
try:
    ast.parse(source)
    print("SYNTAX: PASSED")
except SyntaxError as e:
    print(f"SYNTAX ERROR: {e}")
    sys.exit(1)
