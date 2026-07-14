#!/usr/bin/env python3
"""触发 Step 4 执行 - 后旺架构设计"""
import sys
sys.path.insert(0, '/home/jim/DevFlow/backend')

from app.database import SessionLocal
from app.services.workflow_engine import WorkflowEngine
import sqlite3, json

# 获取所有项目
conn = sqlite3.connect('/home/jim/DevFlow/backend/devflow.db')
conn.row_factory = sqlite3.Row
c = conn.cursor()
c.execute('SELECT id, name, slug FROM projects')
projects = c.fetchall()
conn.close()

for p in projects:
    pid = p['id']
    name = p['name']
    slug = p['slug']
    
    print(f"\n{'='*60}")
    print(f"触发 Step 4: {name} (slug: {slug})")
    print(f"{'='*60}")
    
    db = SessionLocal()
    try:
        engine = WorkflowEngine(project_id=pid, db=db)
        
        # 先检查 Step 4 当前状态
        c = db.execute('SELECT status, output_artifacts FROM workflow_steps WHERE project_id=? AND step_number=4', (pid,))
        row = c.fetchone()
        if row:
            print(f"  当前 Step 4 状态: {row[0]}")
            artifacts = row[1]
            print(f"  当前产出物: {artifacts[:200] if artifacts else 'null'}...")
        
        # 尝试调动 Agent
        mobilize_result = engine.haimei_mobilize_agent(step_number=4)
        print(f"  调动 Agent 结果: {mobilize_result}")
        
        # 尝试执行 Step 4
        # 查看 WorkflowEngine 有哪些 Step 4 相关方法
        methods = [m for m in dir(engine) if 'step4' in m.lower() or 'step_4' in m.lower()]
        print(f"  Step 4 相关方法: {methods}")
        
        if 'execute_step4' in methods:
            result = engine.execute_step4()
            print(f"  execute_step4 结果: {result}")
        elif 'run_step4' in methods:
            result = engine.run_step4()
            print(f"  run_step4 结果: {result}")
        else:
            print(f"  没有找到 Step 4 执行方法，尝试监督")
            supervise_methods = [m for m in dir(engine) if 'supervise' in m.lower()]
            print(f"  监督方法: {supervise_methods}")
        
    except Exception as e:
        print(f"  错误: {e}")
        import traceback
        traceback.print_exc()
    finally:
        db.close()

print("\n" + "="*60)
print("Step 4 触发完成")
print("="*60)
