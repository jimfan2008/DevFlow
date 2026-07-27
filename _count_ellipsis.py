import os
target = '/home/jim/DevFlow'
for root, dirs, files in os.walk(target):
    if '.venv' in root or '__pycache__' in root:
        continue
    for fn in files:
        if fn.endswith('.py') and ('test_' in fn or 'tdd_' in fn):
            path = os.path.join(root, fn)
            try:
                with open(path, 'r', encoding='utf-8') as f:
                    content = f.read()
                for i, ch in enumerate(content):
                    if ord(ch) == 0x2026:
                        line = content[:i].count('\n') + 1
                        print(f"U+2026 in {path} at line {line}")
                lines = content.count('\n') + 1
                if lines >= 250:
                    print(f"  {path}: {lines} lines")
            except Exception as e:
                print(f"Error reading {path}: {e}")
