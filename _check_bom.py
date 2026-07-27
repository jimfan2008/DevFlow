# Check files for BOM
files = [
    '/home/jim/DevFlow/test_system_monitor_dashboard.py',
    '/home/jim/DevFlow/backend/tests/test_tdd_system_monitor_panel.py',
]
for f in files:
    with open(f, 'rb') as fh:
        raw = fh.read(10)
        print(f"File: {f}")
        print(f"  First 10 bytes hex: {raw.hex()}")
        print(f"  First 10 bytes: {raw!r}")
        if raw[:3] == b'\xef\xbb\xbf':
            print("  *** HAS UTF-8 BOM ***")
        elif raw[:2] == b'\xff\xfe':
            print("  *** HAS UTF-16 LE BOM ***")
        elif raw[:2] == b'\xfe\xff':
            print("  *** HAS UTF-16 BE BOM ***")
        else:
            print("  No BOM detected")
        print()
