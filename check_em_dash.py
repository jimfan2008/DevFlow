import ast
with open('/home/jim/DevFlow/backend/tests/test_add_group_member.py', 'r') as f:
    source = f.read()

# Check for em dash U+2014
for i, ch in enumerate(source):
    if ord(ch) == 0x2014:
        line = source[:i].count('\n') + 1
        print(f"EM DASH found at position {i}, line {line}")
    if ord(ch) == 0x2013:
        line = source[:i].count('\n') + 1
        print(f"EN DASH found at position {i}, line {line}")

# Check other potentially problematic Unicode
for i, ch in enumerate(source):
    if ord(ch) > 127 and ord(ch) not in range(0x4E00, 0x9FFF+1) and ord(ch) not in range(0x3000, 0x303F+1) and ord(ch) not in range(0xFF00, 0xFFEF+1):
        line = source[:i].count('\n') + 1
        context = source[max(0,i-5):i+5]
        print(f"Non-ASCII non-CJK char U+{ord(ch):04X} at line {line}: ...{repr(context)}...")

# Syntax check
try:
    ast.parse(source)
    print("SYNTAX CHECK: PASSED")
except SyntaxError as e:
    print(f"SYNTAX CHECK: FAILED - {e}")

# Count lines
print(f"Total lines: {source.count(chr(10)) + 1}")
