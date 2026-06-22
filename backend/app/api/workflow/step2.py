from app.api.workflow.core import (
    router, _get_engine, logger, APIResponse, Depends, get_db,
    get_current_user, Session, CoreGoalRequest, Step2ArtifactsRequest,
)

@router.post("/{project_id}/step2")
def execute_step2(project_id: str, body: CoreGoalRequest,
                  db: Session = Depends(get_db),
                  current_user=Depends(get_current_user)):
    engine = _get_engine(project_id, db)
    engine.advance_step(2)
    step = engine.complete_step(2, artifacts={"core_goal": body.core_goal})
    result = engine.pass_qa(2)
    return APIResponse(code=0, data={
        "message": "第二步完成：核心目标确认与组织架构搭建",
        "step": step,
        "qa": result,
    })


@router.post("/{project_id}/step2/artifacts")
def save_step2_artifacts(project_id: str, body: Step2ArtifactsRequest,
                         db: Session = Depends(get_db),
                         current_user=Depends(get_current_user)):
    engine = _get_engine(project_id, db)
    engine.save_step2_artifacts(body.model_dump())
    return APIResponse(code=0, data={"message": "步骤2状态已保存"})


@router.get("/{project_id}/step2/status")
def get_step2_status(project_id: str,
                     db: Session = Depends(get_db),
                     current_user=Depends(get_current_user)):
    engine = _get_engine(project_id, db)
    artifacts = engine.get_step2_artifacts()
    return APIResponse(code=0, data=artifacts)


