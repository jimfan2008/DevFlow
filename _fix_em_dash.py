with open('/home/jim/DevFlow/test_system_monitor_dashboard.py', 'r', encoding='utf-8') as f:
    content = f.read()

# Find all em dashes
for i, ch in enumerate(content):
    if ord(ch) == 0x2014:
        line = content[:i].count('\n') + 1
        context = content[max(0,i-10):i+10]
        print(f"EM DASH U+2014 at line {line}, pos {i}: ...{repr(context)}...")

# Replace em dash with regular hyphen
fixed = content.replace('\u2014', '-')
fixed = content.replace('\u2015', '-')
fixed = content.replace('\u2013', '-')

with open('/home/jim/DevFlow/test_system_monitor_dashboard.py', 'w', encoding='utf-8') as f:
    f.write(fixed)

print("Fixed file written")

# Verify syntax
import ast
try:
    ast.parse(fixed, filename='test_system_monitor_dashboard.py')
    print("SYNTAX OK")
except SyntaxError as e:
    print(f"SYNTAX ERROR at line {e.lineno}: {e.msg}")
    # Show the problematic line
    lines = fixed.split('\n')
    if e.lineno and e.lineno <= len(lines):
        print(f"Problem line: {repr(lines[e.lineno-1])}")
