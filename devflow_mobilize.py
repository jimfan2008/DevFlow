import sys, sqlite3, json
sys.path.insert(0, '/home/jim/DevFlow/backend')

# 检查可用的 API 端点
import importlib
import pkgutil
import os

# 查找 API 路由文件
api_dir = '/home/jim/DevFlow/backend/app/api'
if os.path.exists(api_dir):
    print('API 路由文件:')
    for root, dirs, files in os.walk(api_dir):
        for f in files:
            if f.endswith('.py') and not f.startswith('__'):
                path = os.path.join(root, f)
                rel = os.path.relpath(path, api_dir)
                print(f'  {rel}')

# 检查工作流引擎中的方法
from app.services.workflow_engine import WorkflowEngine
methods = [m for m in dir(WorkflowEngine) if not m.startswith('_') and callable(getattr(WorkflowEngine, m, None))]
print(f'\nWorkflowEngine 可用方法 ({len(methods)} 个):')
for m in sorted(methods):
    if 'step' in m.lower() or 'execute' in m.lower() or 'mobilize' in m.lower() or 'advance' in m.lower():
        print(f'  {m}')

# 检查 haimei_mobilize_agent 方法
from app.database import SessionLocal
conn = sqlite3.connect('/home/jim/DevFlow/devflow.db')
conn.row_factory = sqlite3.Row
c = conn.cursor()
c.execute('SELECT id, name, current_step FROM projects')
projects = c.fetchall()

for p in projects:
    pid = p['id']
    name = p['name'] or 'unknown'
    cur_step = p['current_step']
    print(f'\n--- {name} (Step {cur_step}) ---')
    
    db = SessionLocal()
    try:
        engine = WorkflowEngine(project_id=pid, db=db)
        
        # 尝试调动 Agent 执行
        try:
            result = engine.haimei_mobilize_agent(step_number=cur_step)
            print(f'  调动 Agent 结果: {json.dumps(result, ensure_ascii=False, default=str)}')
        except Exception as e:
            print(f'  调动 Agent 异常: {e}')
    except Exception as e:
        print(f'  引擎异常: {e}')
    finally:
        db.close()

conn.close()
