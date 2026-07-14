#!/usr/bin/env python3
import sys, sqlite3, json, os, glob
sys.path.insert(0, '/home/jim/DevFlow/backend')
conn = sqlite3.connect('/home/jim/DevFlow/backend/devflow.db')
conn.row_factory = sqlite3.Row
c = conn.cursor()

# 获取所有项目
c.execute('SELECT id, name, slug, status, current_step FROM projects')
projects = c.fetchall()

for p in projects:
    pid = p['id']
    print(f"\n=== {p['name']} (slug: {p['slug']}, 步骤: {p['current_step']}, 状态: {p['status']}) ===")
    c.execute('SELECT step_number, step_name, status, executor_agent_id FROM workflow_steps WHERE project_id=? ORDER BY step_number', (pid,))
    for s in c.fetchall():
        icon = {'completed':'✅','in_progress':'▶','pending':'⏸','failed':'❌','qa_review':'🔍'}.get(s['status'],s['status'])
        if s['status'] != 'completed':
            print(f"  Step {s['step_number']:2d} [{icon}] {s['status']:15s} Agent: {s['executor_agent_id']:20s} | {s['step_name']}")
    
    # 检查磁盘文档
    doc_dir = f"/home/jim/DevFlow/projects/{p['slug']}/docs"
    if os.path.exists(doc_dir):
        files = glob.glob(f"{doc_dir}/*.md")
        if files:
            print(f"  文档: {len(files)} 个文件")
            for f in sorted(files)[-5:]:
                print(f"    {os.path.basename(f)}")
        else:
            print(f"  文档: 空目录")
    else:
        print(f"  文档: 目录不存在")

conn.close()
