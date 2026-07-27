with open('/home/jim/DevFlow/test_system_monitor_dashboard.py', 'rb') as f:
    raw = f.read()
# Find line 326 by counting newlines
lines = raw.split(b'\n')
if len(lines) >= 326:
    line326 = lines[325]
    print(f"Line 326 ({len(line326)} bytes): {line326!r}")
    print(f"Line 326 hex: {line326.hex()}")
    for i, b in enumerate(line326):
        if b > 127:
            print(f"  Byte at {i}: 0x{b:02x}")
    # Try to decode line 326
    try:
        decoded = line326.decode('utf-8')
        print(f"Decoded: {decoded!r}")
        for i, ch in enumerate(decoded):
            if ord(ch) > 127:
                print(f"  Non-ASCII char at {i}: U+{ord(ch):04X} = {ch!r}")
    except UnicodeDecodeError as e:
        print(f"Decode error: {e}")
else:
    print(f"File has {len(lines)} lines, less than 326")
