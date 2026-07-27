import ast, sys
with open('/home/jim/DevFlow/tests/test_cases/test_tdd_0016_devflow.py', 'rb') as f:
    raw = f.read()
# Check for U+2014 em-dash
if b'\xe2\x80\x94' in raw:
    lines = raw.decode('utf-8').split('\n')
    for i, line in enumerate(lines, 1):
        if '\u2014' in line:
            print(f"EM-DASH found at line {i}: {line!r}")
    sys.exit(1)
print("No em-dash found.")
try:
    ast.parse(raw.decode('utf-8'), filename='test_tdd_0016_devflow.py')
    print("SYNTAX OK")
except SyntaxError as e:
    print(f"SYNTAX ERROR at line {e.lineno}: {e.msg}")
    sys.exit(1)
