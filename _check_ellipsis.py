import sys
files = [
    '/home/jim/DevFlow/test_unauthenticated_access_protected_api.py',
    '/home/jim/DevFlow/test_unauthenticated_access.py',
    '/home/jim/DevFlow/test_unauthenticated_access_protected_api_tdd.py',
    '/home/jim/DevFlow/test_unauthenticated_access_protected_api_pi1.py',
    '/home/jim/DevFlow/test_unauthorized_access_protected_api.py',
    '/home/jim/DevFlow/test_unauth_access.py',
    '/home/jim/DevFlow/test_unauthenticated_api.py',
    '/home/jim/DevFlow/backend/tests/test_tdd_unauthenticated_access.py',
    '/home/jim/DevFlow/backend/tests/test_tdd_unauthorized_access_protected_api.py',
    '/home/jim/DevFlow/backend/tests/test_tdd_unauthorized_access.py',
    '/home/jim/DevFlow/backend/tests/test_tdd_unauthorized_access_v2.py',
    '/home/jim/DevFlow/backend/tests/test_tdd_unauthorized_access_v3.py',
    '/home/jim/DevFlow/backend/tests/test_tdd_unauthorized_access_v4.py',
    '/home/jim/DevFlow/backend/tests/test_auth_unauthorized.py',
    '/home/jim/DevFlow/tests/test_unauthenticated_access.py',
]
for f in files:
    try:
        with open(f, 'r', encoding='utf-8') as fh:
            content = fh.read()
        lines = content.count('\n') + 1
        has_ellipsis = '\u2026' in content
        if has_ellipsis:
            for i, ch in enumerate(content):
                if ord(ch) == 0x2026:
                    line = content[:i].count('\n') + 1
                    print(f"{f}: U+2026 at line {line}")
        print(f"{f}: {lines} lines, U+2026={'YES' if has_ellipsis else 'no'}")
    except Exception as e:
        print(f"{f}: ERROR - {e}")
