#!/usr/bin/env python3
"""DevFlow 项目经理 - 修复卡住的步骤并触发执行"""
import sys, json, urllib.request, urllib.error, time
sys.path.insert(0, '/home/jim/DevFlow/backend')

import jwt, sqlite3
from datetime import datetime, timedelta, timezone

SECRET_KEY = 'devflow-secret-key'
DB_PATH = '/home/jim/DevFlow/devflow.db'

def get_token():
    conn = sqlite3.connect(DB_PATH)
    conn.row_factory = sqlite3.Row
    c = conn.cursor()
    c.execute('SELECT id FROM users LIMIT 1')
    user = c.fetchone()
    conn.close()
    user_id = user['id'] if user else '18532d90-a239-422d-8f05-45630196ee2b'
    payload = {
        "sub": user_id,
        "type": "access",
        "iat": datetime.now(timezone.utc),
        "exp": datetime.now(timezone.utc) + timedelta(hours=24)
    }
    return jwt.encode(payload, SECRET_KEY, algorithm="HS256")

def api_call(url, method="POST", body=None):
    token = get_token()
    headers = {
        "Authorization": f"Bearer {token}",
        "Content-Type": "application/json"
    }
    data = json.dumps(body or {}).encode() if body is not None else None
    req = urllib.request.Request(url, data=data, headers=headers, method=method)
    try:
        resp = urllib.request.urlopen(req, timeout=60)
        return resp.status, json.loads(resp.read())
    except urllib.error.HTTPError as e:
        body_text = e.read().decode()
        try:
            return e.code, json.loads(body_text)
        except:
            return e.code, body_text

def restart_step(pid, step_num):
    """使用 haimei 通用重启端点"""
    url = f"http://localhost:8000/api/v1/workflow/{pid}/haimei/step/{step_num}/restart"
    code, resp = api_call(url, "POST")
    return code, resp

def execute_step(pid, step_num):
    """触发步骤执行 - Step 2/3 使用 /step{N}，Step 4+ 使用 /step{N}/execute"""
    if step_num in (2, 3):
        url = f"http://localhost:8000/api/v1/workflow/{pid}/step{step_num}"
    else:
        url = f"http://localhost:8000/api/v1/workflow/{pid}/step{step_num}/execute"
    code, resp = api_call(url, "POST")
    return code, resp

def check_step_prerequisites(pid, step_num):
    """检查步骤的前置条件（磁盘文件是否存在）"""
    import os, glob
    c = sqlite3.connect(DB_PATH).cursor()
    c.execute('SELECT slug FROM projects WHERE id=?', (pid,))
    row = c.fetchone()
    slug = row[0] if row else pid
    conn = sqlite3.connect(DB_PATH)
    conn.close()

    docs_dir = f"/home/jim/DevFlow/projects/{slug}/docs"
    os.makedirs(docs_dir, exist_ok=True)

    # 检查关键前置文件
    checks = {
        4: lambda: bool(glob.glob(f"{docs_dir}/*_SRS_V*.md")),  # Step 4 需要 SRS
        5: lambda: bool(glob.glob(f"{docs_dir}/*_design_V*.md")),  # Step 5 需要设计文档
        6: lambda: bool(glob.glob(f"{docs_dir}/*_design_V*.md")),  # Step 6 需要设计文档
    }
    checker = checks.get(step_num)
    if checker:
        return checker()
    return True

def main():
    print("=" * 60)
    print("DevFlow 项目经理 - 步骤执行修复器 (v2)")
    print("=" * 60)
    
    conn = sqlite3.connect(DB_PATH)
    conn.row_factory = sqlite3.Row
    c = conn.cursor()
    
    c.execute('SELECT id, name, slug, current_step FROM projects')
    projects = list(c.fetchall())
    
    now = datetime.now(timezone.utc)
    
    for p in projects:
        pid = p['id']
        pname = p['name']
        pstep = p['current_step']
        print(f"\n--- 项目: {pname} (slug={p['slug']}, 当前步骤={pstep}) ---")
        
        # 获取当前步骤状态
        c.execute('SELECT step_number, status, started_at FROM workflow_steps WHERE project_id=? AND step_number=?', (pid, pstep))
        step = c.fetchone()
        
        if not step:
            print(f"  错误：找不到 Step {pstep}")
            continue
            
        step_num = step['step_number']
        step_status = step['status']
        step_started = str(step['started_at'])[:19] if step['started_at'] else 'None'
        
        print(f"  当前步骤: Step {step_num} = {step_status} (started={step_started})")
        
        if step_status == 'in_progress':
            # 检查是否卡住
            try:
                started_dt = datetime.fromisoformat(step_started.replace('Z', '+00:00'))
                if started_dt.tzinfo is None:
                    started_dt = started_dt.replace(tzinfo=timezone.utc)
            except:
                started_dt = now
            elapsed = now - started_dt
            hours = elapsed.total_seconds() / 3600
            
            if hours > 2:
                print(f"  ⚠️ 步骤卡住（已运行 {hours:.1f} 小时）")
                print(f"  → 使用 haimei 重启 Step {step_num}")
                code, resp = restart_step(pid, step_num)
                print(f"  重启结果: [{code}] {str(resp)[:200]}")
                
                if code == 200 and resp.get('code') == 0:
                    time.sleep(2)
                    print(f"  → 触发 Step {step_num} 执行")
                    code2, resp2 = execute_step(pid, step_num)
                    print(f"  执行结果: [{code2}] {str(resp2)[:200]}")
            else:
                print(f"  运行 {hours:.1f} 小时 - 可能仍在执行中")
        
        elif step_status == 'pending':
            # 检查前一步是否完成
            c.execute('SELECT step_number, status FROM workflow_steps WHERE project_id=? AND step_number=?', (pid, step_num - 1))
            prev = c.fetchone()
            
            if prev and prev['status'] == 'completed':
                print(f"  → 触发 Step {step_num} 执行")
                code, resp = execute_step(pid, step_num)
                print(f"  执行结果: [{code}] {str(resp)[:200]}")
            else:
                print(f"  等待中 (前一步 Step {step_num-1} 状态: {prev['status'] if prev else 'N/A'})")
    
    conn.close()
    print("\n" + "=" * 60)
    print("执行完毕")

if __name__ == "__main__":
    main()
