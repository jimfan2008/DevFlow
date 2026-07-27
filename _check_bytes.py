with open('/home/jim/DevFlow/test_tdd_0016_devflow.py', 'rb') as f:
    data = f.read()
lines = data.split(b'\n')
print(f"Total lines: {len(lines)}")
# Check last few lines for non-ASCII
for i in range(max(0, len(lines)-3), len(lines)):
    line = lines[i]
    print(f"Line {i+1} ({len(line)} bytes): {line!r}")
    for j, b in enumerate(line):
        if b > 127:
            if b >= 0xe0 and j+2 < len(line):
                seq = line[j:j+3]
                try:
                    char = seq.decode('utf-8')
                    print(f"  >>> NON-ASCII at byte {j}: U+{ord(char):04X} ('{char}')")
                except:
                    pass
