import ast

with open('/home/jim/DevFlow/test_project_monitor_panel_v2.py', 'rb') as f:
    raw = f.read()

# Check for em dash U+2014 in the raw bytes
em_dash_bytes = b'\xe2\x80\x94'  # UTF-8 encoding of U+2014
positions = []
start = 0
while True:
    pos = raw.find(em_dash_bytes, start)
    if pos == -1:
        break
    positions.append(pos)
    start = pos + 1

for pos in positions:
    line_num = raw[:pos].count(b'\n') + 1
    context = raw[max(0,pos-10):pos+10]
    print(f"EM DASH U+2014 found at byte {pos}, line {line_num}")
    print(f"  Context: {context!r}")

if not positions:
    print("No em dash U+2014 found in the file.")
else:
    print(f"\nTotal em dashes found: {len(positions)}")

# Also check for horizontal bar U+2015
horz_bar_bytes = b'\xe2\x80\x95'
positions2 = []
start = 0
while True:
    pos = raw.find(horz_bar_bytes, start)
    if pos == -1:
        break
    positions2.append(pos)
    start = pos + 1

for pos in positions2:
    line_num = raw[:pos].count(b'\n') + 1
    context = raw[max(0,pos-10):pos+10]
    print(f"HORIZONTAL BAR U+2015 found at byte {pos}, line {line_num}")
    print(f"  Context: {context!r}")

# Now try syntax check
try:
    source = raw.decode('utf-8')
    ast.parse(source, filename='test_project_monitor_panel_v2.py')
    print("\nSYNTAX CHECK: PASSED")
except SyntaxError as e:
    print(f"\nSYNTAX ERROR at line {e.lineno}: {e.msg}")
    if e.text:
        print(f"  Text: {e.text!r}")

total_lines = raw.count(b'\n') + 1
print(f"\nTotal lines in file: {total_lines}")
