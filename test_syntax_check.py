import ast
with open('/home/jim/DevFlow/test_unauthenticated_access_protected_api_tdd.py', 'r') as f:
    source = f.read()
lines = source.split('\n')
print(f"Total lines: {len(lines)}")
try:
    ast.parse(source)
    print("SYNTAX: PASSED")
except SyntaxError as e:
    print(f"SYNTAX ERROR: {e}")
