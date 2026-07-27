with open('/home/jim/DevFlow/test_tdd_0016_devflow.py', 'rb') as f:
    data = f.read()
lines = data.split(b'\n')
print(f"Total lines: {len(lines)}")
for i, line in enumerate(lines):
    for j, byte in enumerate(line):
        if byte > 127:
            if byte >= 0xe0 and j+2 < len(line):
                seq = line[j:j+3]
                try:
                    char = seq.decode('utf-8')
                    print(f"Line {i+1}, col {j+1}: non-ASCII '{char}' U+{ord(char):04X} context: ...{line[max(0,j-10):j+10].decode('utf-8', errors='replace')}...")
                except:
                    pass
            elif byte >= 0xc0 and j+1 < len(line):
                seq = line[j:j+2]
                try:
                    char = seq.decode('utf-8')
                    print(f"Line {i+1}, col {j+1}: non-ASCII '{char}' U+{ord(char):04X} context: ...{line[max(0,j-10):j+10].decode('utf-8', errors='replace')}...")
                except:
                    pass
