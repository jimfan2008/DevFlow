with open('/home/jim/DevFlow/test_system_monitor_dashboard.py', 'rb') as f:
    raw = f.read()

# Check for em dash U+2014 in unicode
em_dash_bytes = b'\xe2\x80\x94'
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
    context = raw[max(0,pos-15):pos+15]
    print(f"EM DASH U+2014 at byte {pos}, line {line_num}")
    print(f"  Context: {context!r}")

# Check for replacement char
repl_bytes = b'\xef\xbf\xbd'  # U+FFFD in UTF-8
positions2 = []
start = 0
while True:
    pos = raw.find(repl_bytes, start)
    if pos == -1:
        break
    positions2.append(pos)
    start = pos + 1

for pos in positions2:
    line_num = raw[:pos].count(b'\n') + 1
    context = raw[max(0,pos-15):pos+15]
    print(f"REPLACEMENT CHAR U+FFFD at byte {pos}, line {line_num}")
    print(f"  Context: {context!r}")

# Check for other Unicode dash-like chars
for name, byte_seq in [
    ("U+2013 EN DASH", b'\xe2\x80\x93'),
    ("U+2212 MINUS", b'\xe2\x88\x92'),
    ("U+FF0D FULLWIDTH HYPHEN", b'\xef\xbc\x8d'),
    ("U+2015 HORIZONTAL BAR", b'\xe2\x80\x95'),
]:
    pos = raw.find(byte_seq)
    if pos >= 0:
        line_num = raw[:pos].count(b'\n') + 1
        print(f"{name} found at byte {pos}, line {line_num}")

total_lines = raw.count(b'\n') + 1
print(f"Total lines: {total_lines}")

# Check for BOM
if raw[:3] == b'\xef\xbb\xbf':
    print("BOM found at start of file!")
