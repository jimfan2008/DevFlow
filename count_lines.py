with open('/home/jim/DevFlow/backend/tests/test_add_group_member.py', 'r') as f:
    lines = f.readlines()
print(f"Total lines: {len(lines)}")
# Show lines around 294
for i in range(290, min(300, len(lines))):
    line_num = i + 1
    line = lines[i]
    has_em = '\u2014' in line
    has_en = '\u2013' in line
    marker = " <-- EM DASH!" if has_em else " <-- EN DASH!" if has_en else ""
    print(f"Line {line_num}: {repr(line[:80])}{marker}")
