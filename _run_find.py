with open('/home/jim/DevFlow/test_agent_swarm_monitoring.py', 'rb') as f:
    data = f.read()
lines = data.split(b'\n')
print(f"Total lines: {len(lines)}")
line280 = lines[279] if len(lines) >= 280 else b'N/A'
print(f"Line 280: {line280}")
print(f"Line 280 hex: {line280.hex()}")
print(f"Line 280 repr: {repr(line280.decode('utf-8', errors='replace'))}")
for j, ch in enumerate(line280):
    if ch > 127:
        print(f"  col {j}: byte {hex(ch)}")
