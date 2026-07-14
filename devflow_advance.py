import sys, sqlite3
sys.path.insert(0, '/home/jim/DevFlow/backend')
from app.database import SessionLocal
from app.services.workflow_engine import WorkflowEngine

conn = sqlite3.connect('/home/jim/DevFlow/backend/devflow.db')
conn.row_factory = sqlite3.Row
c = conn.cursor()
c.execute('SELECT id, name, current_step FROM projects')
projects = c.fetchall()

for p in projects:
    pid = p['id']
    name = p['name'] or 'unknown'
    cur_step = p['current_step']
    print(f'\n--- {name} (pid={pid}, current_step={cur_step}) ---')
    
    db = SessionLocal()
    try:
        engine = WorkflowEngine(project_id=pid, db=db)
        
        # 尝试强制重启卡住的步骤
        try:
            result = engine.haimei_force_restart_step(step_number=cur_step)
            print(f'  强制重启 Step {cur_step} 结果: {result}')
        except Exception as e:
            print(f'  强制重启异常: {e}')
        
        # 再尝试自动推进
        try:
            result = engine.haimei_auto_advance()
            print(f'  自动推进结果: {result}')
        except Exception as e:
            print(f'  自动推进异常: {e}')
    except Exception as e:
        print(f'  引擎异常: {e}')
    finally:
        db.close()

conn.close()
