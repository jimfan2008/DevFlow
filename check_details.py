#!/usr/bin/env python3
import sys, sqlite3
sys.path.insert(0, '/home/jim/DevFlow/backend')
conn = sqlite3.connect('/home/jim/DevFlow/devflow.db')
conn.row_factory = sqlite3.Row
c = conn.cursor()

# 检查所有项目详细信息
c.execute('SELECT id, name, slug, core_goal, review_group_id FROM projects')
for p in c.fetchall():
    pid = p['id']
    print(f"\n=== {p['name']} (slug: {p['slug']}) ===")
    print(f"  core_goal: {p['core_goal'][:100] if p['core_goal'] else 'None'}...")
    print(f"  review_group_id: {p['review_group_id']}")
    
    # 检查 Step 3 产出物
    c.execute('SELECT step_number, status, output_artifacts FROM workflow_steps WHERE project_id=? AND step_number<=4', (pid,))
    for s in c.fetchall():
        artifacts = s['output_artifacts'] or '{}'
        print(f"  Step {s['step_number']}: status={s['status']}, artifacts={artifacts[:200]}")

conn.close()
