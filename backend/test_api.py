#!/usr/bin/env python3
"""测试 API 端点"""
import sys, json, urllib.request, urllib.error
sys.path.insert(0, '/home/jim/DevFlow/backend')

import jwt
from datetime import datetime, timedelta, timezone
from app.config import settings

def get_token():
    # verify_token 使用 settings.SECRET_KEY，不是 JWT_SECRET！
    # 并且必须包含 "type": "access"
    # sub 应该是用户 UUID
    import sqlite3
    conn = sqlite3.connect('/home/jim/DevFlow/backend/devflow.db')
    conn.row_factory = sqlite3.Row
    c = conn.cursor()
    c.execute('SELECT id FROM users WHERE username="human_1780395974710"')
    row = c.fetchone()
    conn.close()
    user_id = row['id'] if row else "human_1780395974710"
    
    payload = {
        "sub": user_id,
        "type": "access",
        "iat": datetime.now(timezone.utc),
        "exp": datetime.now(timezone.utc) + timedelta(hours=24)
    }
    return jwt.encode(payload, settings.SECRET_KEY, algorithm=settings.JWT_ALGORITHM)

def test_endpoint(url, method="POST"):
    token = get_token()
    headers = {
        "Authorization": f"Bearer {token}",
        "Content-Type": "application/json"
    }
    data = b'{}' if method == "POST" else None
    req = urllib.request.Request(url, data=data, headers=headers, method=method)
    try:
        resp = urllib.request.urlopen(req, timeout=30)
        body = resp.read()
        print(f"  [{resp.status}] {body.decode()[:300]}")
    except urllib.error.HTTPError as e:
        body = e.read()
        print(f"  [{e.code}] {body.decode()[:300]}")
    except Exception as e:
        print(f"  [ERROR] {e}")

# 测试
project_ids = {
    "Aeternova": "45935b53-92bc-4a72-8fdf-adebda719acf",
    "GBM": "fe5eae09-6ca1-4029-abbf-fb30e008167b",
    "DevFlow": "6e466502-63dc-4b5f-b3e8-a2172308662d"
}

# 先测试 status 端点（GET）
print("=== 测试 status 端点 (GET) ===")
for name, pid in project_ids.items():
    print(f"\n{name}:")
    test_endpoint(f"http://localhost:8000/api/v1/workflow/{pid}/status", "GET")

# 测试 step9 execute 端点（POST）
print("\n=== 测试 step9 execute 端点 (POST) ===")
for name, pid in project_ids.items():
    print(f"\n{name}:")
    test_endpoint(f"http://localhost:8000/api/v1/workflow/{pid}/step9/execute", "POST")

# 测试 step10 execute 端点（POST）
print("\n=== 测试 step10 execute 端点 (POST) ===")
for name, pid in project_ids.items():
    print(f"\n{name}:")
    test_endpoint(f"http://localhost:8000/api/v1/workflow/{pid}/step10/execute", "POST")
