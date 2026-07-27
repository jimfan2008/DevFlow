#!/usr/bin/env python3
"""DevFlow auto-advance script for Haimei cron job."""
import sys
sys.path.insert(0, '/home/jim/DevFlow/backend')
from app.database import SessionLocal
from app.services.workflow_engine import WorkflowEngine

def advance_project(project_id, name, target_step):
    db = SessionLocal()
    engine = WorkflowEngine(project_id=project_id, db=db)
    
    print(f"\n{'='*60}")
    print(f"Project: {name} (id={project_id})")
    print(f"{'='*60}")
    
    status = engine.get_current_status()
    print(f"Current status: {status}")
    
    # Auto advance
    print("\n--- Auto advance ---")
    result = engine.haimei_auto_advance()
    print(f"Auto advance result: {result}")
    
    # Mobilize agent
    print(f"\n--- Mobilize step {target_step} ---")
    try:
        mobilize = engine.haimei_mobilize_agent(step_number=target_step)
        print(f"Mobilize result: {mobilize}")
    except Exception as e:
        print(f"Mobilize error: {e}")
        import traceback
        traceback.print_exc()
    
    # Check new status
    status2 = engine.get_current_status()
    print(f"\nFinal status: {status2}")
    
    db.close()
    return status2

# Projects to advance
projects = [
    ('6e466502-63dc-4b5f-b3e8-a2172308662d', 'DevFlow', 9),
    ('45935b53-92bc-4a72-8fdf-adebda719acf', 'Aeternova', 10),
    ('fe5eae09-6ca1-4029-abbf-fb30e008167b', 'GBM AI Agent HR', 10),
]

for pid, pname, step in projects:
    try:
        advance_project(pid, pname, step)
    except Exception as e:
        print(f"ERROR advancing {pname}: {e}")
        import traceback
        traceback.print_exc()

print("\n=== All projects processed ===")
