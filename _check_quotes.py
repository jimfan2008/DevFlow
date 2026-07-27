with open('/home/jim/DevFlow/test_system_monitor_dashboard.py', 'rb') as f:
    first_line = f.readline().rstrip(b'\n')
print('Hex:', first_line.hex())
print('Repr:', repr(first_line))
# Check for curly quotes
for i, b in enumerate(first_line):
    if b > 127:
        print(f'  Byte {i}: 0x{b:02x}')
