import sys, sqlite3
sys.path.insert(0, '/home/jim/DevFlow/backend')
conn = sqlite3.connect('/home/jim/DevFlow/backend/devflow.db')
conn.row_factory = sqlite3.Row
c = conn.cursor()

c.execute('SELECT id, name, slug, current_step FROM projects')
projects = c.fetchall()

for p in projects:
    pid = p['id']
    name = p['name'] or 'unknown'
    slug = p['slug'] or 'unknown'
    cur_step = p['current_step']
    print(f'\n=== {name} (slug={slug}, current_step={cur_step}) ===')
    c.execute('SELECT step_number, step_name, status FROM workflow_steps WHERE project_id=? AND step_number>=? ORDER BY step_number', (pid, cur_step - 1))
    for s in c.fetchall():
        icon = {'completed':'✅','in_progress':'▶','pending':'⏸','failed':'❌','qa_review':'🔍'}.get(s['status'], '?')
        print(f'  Step {s["step_number"]:>2} [{icon}] {s["status"]:12s} | {s["step_name"][:30]}')

conn.close()
