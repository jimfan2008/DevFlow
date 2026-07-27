with open('/home/jim/DevFlow/test_agent_swarm_monitoring.py', 'rb') as f:
    raw = f.read()
print(f"Total bytes: {len(raw)}")
print(f"First 20 bytes hex: {raw[:20].hex()}")
print(f"Last 20 bytes hex: {raw[-20:].hex()}")
lines = raw.split(b'\n')
print(f"Total lines: {len(lines)}")
# Check for em dash
for i, line in enumerate(lines):
    for j in range(len(line)-2):
        if line[j] == 0xe2 and line[j+1] == 0x80 and line[j+2] == 0x94:
            print(f"EM DASH U+2014 at line {i+1}, col {j+1}")
print("Search complete")
