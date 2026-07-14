#!/usr/bin/env python3
"""
DevFlow 定时监控与自动推进脚本
每 2 小时由 cron job 调用，收集项目状态供 agent 分析
"""

import sys
import json
import os
import subprocess
from datetime import datetime

sys.path.insert(0, '/home/jim/DevFlow/backend')
os.chdir('/home/jim/DevFlow/backend')

import sqlite3

DB_PATH = '/home/jim/DevFlow/backend/devflow.db'

def get_db():
    conn = sqlite3.connect(DB_PATH)
    conn.row_factory = sqlite3.Row
    return conn

def check_uvicorn():
    """检查 DevFlow 后端是否存活"""
    try:
        result = subprocess.run(
            ['curl', '-s', '-o', '/dev/null', '-w', '%{http_code}', 'http://localhost:8000/docs'],
            capture_output=True, text=True, timeout=5
        )
        return result.stdout.strip() == '200'
    except:
        return False

def check_uvicorn_pids():
    """获取 uvicorn 进程信息"""
    try:
        result = subprocess.run(
            ['ps', 'aux'], capture_output=True, text=True
        )
        pids = []
        for line in result.stdout.split('\n'):
            if 'uvicorn' in line and 'app.main:app' in line and 'grep' not in line:
                parts = line.split()
                if len(parts) > 1:
                    pids.append({'pid': parts[1], 'cmd': line})
        return pids
    except:
        return []

def main():
    result = {
        "timestamp": datetime.now().isoformat(),
        "uvicorn_alive": False,
        "uvicorn_pids": [],
        "projects": [],
        "completed_count": 0,
        "total_count": 0,
        "needs_restart": False,
        "action_items": []
    }

    # 检查后端服务
    result["uvicorn_alive"] = check_uvicorn()
    result["uvicorn_pids"] = check_uvicorn_pids()
    if not result["uvicorn_alive"]:
        result["needs_restart"] = True
        result["action_items"].append("DevFlow 后端服务未响应，需要重启")

    conn = get_db()
    c = conn.cursor()

    c.execute('SELECT id, name, slug, status, current_step FROM projects')
    projects = c.fetchall()
    result["total_count"] = len(projects)

    for p in projects:
        project_info = {
            "id": p["id"],
            "name": p["name"],
            "slug": p["slug"],
            "status": p["status"],
            "current_step": p["current_step"],
            "steps": [],
            "needs_mobilize": False,
            "mobilize_step": None,
            "is_completed": p["status"] == "completed",
            "action_needed": None
        }

        if project_info["is_completed"]:
            result["completed_count"] += 1

        c.execute('''
            SELECT step_number, step_name, executor_agent_id, status,
                   started_at, completed_at,
                   CASE WHEN output_artifacts IS NOT NULL THEN 1 ELSE 0 END as has_artifacts
            FROM workflow_steps
            WHERE project_id = ?
            ORDER BY step_number
        ''', (p["id"],))

        steps = c.fetchall()
        prev_completed = True

        for s in steps:
            step_info = {
                "step_number": s["step_number"],
                "step_name": s["step_name"],
                "status": s["status"],
                "executor": s["executor_agent_id"],
                "has_artifacts": bool(s["has_artifacts"]),
            }
            project_info["steps"].append(step_info)

            if s["status"] == "completed":
                prev_completed = True
            elif s["status"] == "in_progress":
                prev_completed = False
            elif s["status"] == "failed":
                prev_completed = False
                project_info["action_needed"] = f"Step {s['step_number']} 失败，需要重启"
                result["action_items"].append(f"{p['name']}: Step {s['step_number']} 失败")
            elif s["status"] == "pending" and prev_completed:
                project_info["needs_mobilize"] = True
                project_info["mobilize_step"] = s["step_number"]
                prev_completed = False

        result["projects"].append(project_info)

    conn.close()

    # 输出 JSON
    print("===DEVFLOW_STATUS_JSON===")
    print(json.dumps(result, ensure_ascii=False, indent=2))
    print("===END_JSON===")

    # 人类可读摘要
    print("\n=== 项目状态摘要 ===")
    for p in result["projects"]:
        icon = "✅" if p["is_completed"] else ("🚀" if p["needs_mobilize"] else "⏳")
        if p["is_completed"]:
            print(f"  {icon} {p['name']} - 已完成")
        elif p["needs_mobilize"]:
            step_name = next((s['step_name'] for s in p['steps'] if s['step_number'] == p['mobilize_step']), '')
            print(f"  {icon} {p['name']} - 可推进到 Step {p['mobilize_step']} ({step_name})")
        else:
            in_prog = [s for s in p["steps"] if s["status"] == "in_progress"]
            if in_prog:
                print(f"  {icon} {p['name']} - Step {in_prog[0]['step_number']} 进行中")
            else:
                print(f"  {icon} {p['name']} - 当前 Step {p['current_step']}")

    if result["needs_restart"]:
        print("\n[ALERT] DevFlow 后端需要重启！")
    if result["action_items"]:
        print("\n[待处理事项]")
        for item in result["action_items"]:
            print(f"  - {item}")

    return 0

if __name__ == '__main__':
    sys.exit(main())
