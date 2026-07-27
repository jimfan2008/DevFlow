import sys
sys.path.insert(0, '/home/jim/DevFlow/backend')
from app.database import SessionLocal
from app.services.workflow_engine import WorkflowEngine

# Force restart stuck legacy projects (Step 2 stuck since June 15)
legacy_projects = [
    ('05d1ed55-21ff-4a82-a190-2bd528cc10e5', 'Legacy-1'),
    ('a55b0e32-2aa1-4367-b681-59d4aa99eda9', 'Legacy-2'),
]

for pid, name in legacy_projects:
    print(f"\n{'='*60}")
    print(f"Forcing restart for: {name} (id={pid})")
    print(f"{'='*60}")
    
    db = SessionLocal()
    try:
        engine = WorkflowEngine(project_id=pid, db=db)
        
        # Force restart step 2
        result = engine.haimei_force_restart_step(step_number=2)
        print(f"  Force restart Step 2: {result}")
        
        # Try auto-advance after restart
        advance = engine.haimei_auto_advance()
        print(f"  Auto-advance: {advance}")
        
        # Status after restart
        status = engine.get_current_status()
        print(f"  Current step after: {status.get('current_step')}")
        
    except Exception as e:
        import traceback
        print(f"  ERROR: {type(e).__name__}: {e}")
        traceback.print_exc()
    finally:
        db.close()

# Try to mobilize agents for stuck in_progress steps
print("\n\n=== Mobilizing agents for stuck projects ===")

active_projects = [
    ('45935b53-92bc-4a72-8fdf-adebda719acf', 'Aeternova', 10),
    ('fe5eae09-6ca1-4029-abbf-fb30e008167b', 'GBM AI Agent HR', 10),
    ('6e466502-63dc-4b5f-b3e8-a2172308662d', 'DevFlow', 9),
]

for pid, name, step in active_projects:
    print(f"\n{'='*60}")
    print(f"Mobilizing for: {name} (Step {step})")
    print(f"{'='*60}")
    
    db = SessionLocal()
    try:
        engine = WorkflowEngine(project_id=pid, db=db)
        
        # Force restart the stuck step
        result = engine.haimei_force_restart_step(step_number=step)
        print(f"  Force restart Step {step}: {result}")
        
        # Mobilize the agent
        mobilize = engine.haimei_mobilize_agent(step_number=step)
        print(f"  Mobilize result: {mobilize}")
        
        # Status after
        status = engine.get_current_status()
        print(f"  New status: {status.get('current_step')}")
        
    except Exception as e:
        import traceback
        print(f"  ERROR: {type(e).__name__}: {e}")
        traceback.print_exc()
    finally:
        db.close()

print("\n\n=== ALL FORCED OPERATIONS COMPLETE ===")
