#!/usr/bin/env python3
"""DevFlow 项目自动推进脚本"""
import sys
sys.path.insert(0, '/home/jim/DevFlow/backend')

from app.database import SessionLocal
from app.services.workflow_engine import WorkflowEngine
import sqlite3

# 获取所有项目
conn = sqlite3.connect('/home/jim/DevFlow/devflow.db')
conn.row_factory = sqlite3.Row
c = conn.cursor()
c.execute('SELECT id, name, slug, current_step, status FROM projects')
projects = c.fetchall()
conn.close()

for p in projects:
    pid = p['id']
    name = p['name']
    slug = p['slug']
    current_step = p['current_step']
    status = p['status']
    
    print(f"\n{'='*60}")
    print(f"推进项目: {name} (slug: {slug}, 当前步骤: {current_step}, 状态: {status})")
    print(f"{'='*60}")
    
    db = SessionLocal()
    try:
        engine = WorkflowEngine(project_id=pid, db=db)
        
        # 获取当前状态
        status_info = engine.get_current_status()
        print(f"  当前状态: {status_info}")
        
        # 尝试自动推进
        result = engine.haimei_auto_advance()
        print(f"  自动推进结果: {result}")
        
        # 检查推进后的状态
        new_status = engine.get_current_status()
        print(f"  推进后状态: {new_status}")
        
    except Exception as e:
        print(f"  错误: {e}")
        import traceback
        traceback.print_exc()
    finally:
        db.close()

print("\n" + "="*60)
print("所有项目推进完成")
print("="*60)
