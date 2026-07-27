import ast, sys
with open('/home/jim/DevFlow/test_notification_multichannel.py', 'rb') as f:
    raw = f.read()
print(f"File size: {len(raw)} bytes")
has_em_dash = b'\xe2\x80\x94' in raw
print(f"Contains em dash (U+2014): {has_em_dash}")
try:
    ast.parse(raw.decode('utf-8'), filename='test_notification_multichannel.py')
    print("SYNTAX OK")
except SyntaxError as e:
    print(f"SYNTAX ERROR at line {e.lineno}: {e.msg}")
    sys.exit(1)
