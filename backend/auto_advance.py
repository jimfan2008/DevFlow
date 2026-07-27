import sys
sys.path.insert(0, '/home/jim/DevFlow/backend')
from app.database import SessionLocal
from app.services.workflow_engine import WorkflowEngine

project_ids = [
    ('45935b53-92bc-4a72-8fdf-adebda719acf', 'Aeternova', 'aeternova'),
    ('fe5eae09-6ca1-4029-abbf-fb30e008167b', 'GBM AI Agent HR', 'gbm-ai-agent-hr'),
    ('6e466502-63dc-4b5f-b3e8-a2172308662d', 'DevFlow', 'devflow'),
    ('05d1ed55-21ff-4a82-a190-2bd528cc10e5', 'Legacy-1', None),
    ('a55b0e32-2aa1-4367-b681-59d4aa99eda9', 'Legacy-2', None),
]

for pid, name, slug in project_ids:
    print(f"\n{'='*60}")
    print(f"Processing: {name} (id={pid})")
    print(f"{'='*60}")
    
    db = SessionLocal()
    try:
        engine = WorkflowEngine(project_id=pid, db=db)
        
        # Get current status
        status = engine.get_current_status()
        print(f"  Current status: {status}")
        
        # Try auto-advance
        advance_result = engine.haimei_auto_advance()
        print(f"  Auto-advance result: {advance_result}")
        
        # Check if there's a step that needs mobilization
        agent_statuses = engine.haimei_get_all_agent_statuses()
        if isinstance(agent_statuses, dict):
            for step, info in agent_statuses.items():
                if isinstance(info, dict) and info.get('needs_mobilize'):
                    print(f"  Step {step} needs mobilization")
                    mobilize = engine.haimei_mobilize_agent(step_number=int(step))
                    print(f"  Mobilize result: {mobilize}")
        
        # Check new status
        new_status = engine.get_current_status()
        print(f"  New status after advance: {new_status}")
        
    except Exception as e:
        import traceback
        print(f"  ERROR: {type(e).__name__}: {e}")
        traceback.print_exc()
    finally:
        db.close()

print("\n\n=== ALL PROJECTS PROCESSED ===")
