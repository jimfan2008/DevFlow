import ast
with open('/home/jim/DevFlow/test_alert_escalation_level2.py', 'rb') as f:
    raw = f.read()
for i, b in enumerate(raw):
    if b == 0x94 or b == 0x97 or b == 0x80:
        line = raw[:i].count(b'\n') + 1
        print(f"WINDOWS-1252 smart quote/em-dash byte {b:#x} at offset {i}, line {line}")
    if b == 0xE2 and i+2 < len(raw) and raw[i+1] == 0x80 and raw[i+2] in (0x94, 0x93, 0x99):
        line_num = raw[:i].count(b'\n') + 1
        print(f"UTF-8 em-dash/en-dash at offset {i}, line {line_num}")
try:
    tree = ast.parse(raw.decode('utf-8'))
    print(f"SYNTAX OK - {len(tree.body)} top-level nodes")
except SyntaxError as e:
    print(f"SYNTAX ERROR line {e.lineno}: {e.msg}")
