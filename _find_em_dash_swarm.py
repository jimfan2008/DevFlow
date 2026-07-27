with open('/home/jim/DevFlow/test_agent_swarm_monitoring.py', 'rb') as f:
    data = f.read()
lines = data.split(b'\n')
for i, line in enumerate(lines, 1):
    for j, ch in enumerate(line):
        if ch == 0xe2:
            if j+2 < len(line) and line[j+1] == 0x80 and line[j+2] == 0x94:
                print(f"Line {i}, col {j+1}: U+2014 EM DASH. Context: {line[max(0,j-3):j+6].decode('utf-8', errors='replace')}")
        if ch == 0xe2 and j+2 < len(line) and line[j+1] == 0x80 and line[j+2] == 0x95:
            print(f"Line {i}, col {j+1}: U+2015 HORIZONTAL BAR")
        if ch == 0xef and j+2 < len(line) and line[j+1] == 0xbf and line[j+2] == 0xbd:
            print(f"Line {i}, col {j+1}: U+FFFD REPLACEMENT CHAR")
print(f"Total lines: {len(lines)}")
