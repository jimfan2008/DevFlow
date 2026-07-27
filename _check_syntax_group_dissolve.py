import ast, sys
with open('/home/jim/DevFlow/test_group_dissolve.py', 'rb') as f:
    raw = f.read()
print(f"First 20 bytes hex: {raw[:20].hex()}")
print(f"First 20 bytes repr: {raw[:20]!r}")
try:
    ast.parse(raw.decode('utf-8'), filename='test_group_dissolve.py')
    print("SYNTAX OK")
except SyntaxError as e:
    print(f"SYNTAX ERROR at line {e.lineno}: {e.msg}")
    sys.exit(1)
