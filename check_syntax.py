import ast, sys
with open('/home/jim/DevFlow/backend/tests/test_add_group_member.py', 'r') as f:
    source = f.read()
lines = source.split('\n')
print(f"Total lines: {len(lines)}")
# Check for em dash
for i, line in enumerate(lines):
    if '\u2014' in line or '\u2013' in line:
        print(f"Line {i+1}: DASH FOUND: {repr(line[:60])}")
        sys.exit(1)
print("No em dash or en dash found in file")
# Check syntax
try:
    ast.parse(source)
    print("SYNTAX: PASSED")
except SyntaxError as e:
    print(f"SYNTAX ERROR: {e}")
    sys.exit(1)
