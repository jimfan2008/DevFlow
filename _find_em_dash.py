with open('/home/jim/DevFlow/test_system_monitor_dashboard.py', 'r') as f:
    lines = f.readlines()
for i, line in enumerate(lines, 1):
    for j, ch in enumerate(line):
        if ord(ch) == 0x2014:
            print(f"Line {i}, col {j}: EM DASH U+2014 found. Context: {repr(line[max(0,j-5):j+5])}")
        if ord(ch) == 0x2015:
            print(f"Line {i}, col {j}: HORIZONTAL BAR U+2015 found. Context: {repr(line[max(0,j-5):j+5])}")
        if ch == '\ufffd':
            print(f"Line {i}, col {j}: REPLACEMENT CHAR U+FFFD found. Context: {repr(line[max(0,j-5):j+5])}")
print(f"Total lines: {len(lines)}")
print(f"Line 326: {repr(lines[325] if len(lines) >= 326 else 'N/A')}")
print(f"Line 325: {repr(lines[324] if len(lines) >= 325 else 'N/A')}")
print(f"Line 327: {repr(lines[326] if len(lines) >= 327 else 'N/A')}")
