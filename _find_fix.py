import sys

targets = [
    '/home/jim/DevFlow/test_system_monitor_dashboard.py',
    '/home/jim/DevFlow/test_project_monitor_panel_v2.py',
    '/home/jim/DevFlow/test_project_monitor_panel.py',
]

for fpath in targets:
    try:
        with open(fpath, 'rb') as f:
            raw = f.read()
    except FileNotFoundError:
        print(f"NOT FOUND: {fpath}")
        continue
    
    # Find em dash U+2014 (\xe2\x80\x94)
    total = 0
    pos = 0
    while True:
        pos = raw.find(b'\xe2\x80\x94', pos)
        if pos == -1:
            break
        line_num = raw[:pos].count(b'\n') + 1
        context_start = max(0, pos - 20)
        context_end = min(len(raw), pos + 20)
        context = raw[context_start:context_end]
        print(f"{fpath}: EM DASH U+2014 at byte {pos}, line {line_num}")
        print(f"  Context: {context!r}")
        total += 1
        pos += 1
    
    # Also find U+FFFD (replacement chars)
    pos = 0
    while True:
        pos = raw.find(b'\xef\xbf\xbd', pos)
        if pos == -1:
            break
        line_num = raw[:pos].count(b'\n') + 1
        context_start = max(0, pos - 20)
        context_end = min(len(raw), pos + 20)
        context = raw[context_start:context_end]
        print(f"{fpath}: U+FFFD at byte {pos}, line {line_num}")
        print(f"  Context: {context!r}")
        total += 1
        pos += 1
    
    total_lines = raw.count(b'\n') + 1
    print(f"{fpath}: {total_lines} lines, {total} issues found")
    print()
