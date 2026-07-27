with open('/home/jim/DevFlow/test_tdd_0016_devflow.py', 'rb') as f:
    raw = f.read()
text = raw.decode('utf-8')
lines = text.split('\n')
print(f"Total lines: {len(lines)}")
for i, ch in enumerate(text):
    code = ord(ch)
    if code > 127:
        line_num = text[:i].count('\n') + 1
        col = i - (text[:i].rfind('\n') if '\n' in text[:i] else -1)
        context_start = max(0, i - 15)
        context_end = min(len(text), i + 15)
        context = repr(text[context_start:context_end])
        print(f"Line {line_num}, col {col}: U+{code:04X} ('{ch}') context={context}")
