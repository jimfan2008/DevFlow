from app.api.workflow.core import (
    router, _get_engine, logger, APIResponse, Depends, get_db,
    get_current_user, Session, Body, asyncio, settings,
    UserSatisfactionRequest,
)

@router.get("/{project_id}/step16/status")
def get_step16_status(project_id: str, db: Session = Depends(get_db), current_user=Depends(get_current_user)):
    engine = _get_engine(project_id, db)
    return APIResponse(code=0, data=engine.get_step16_artifacts())


@router.post("/{project_id}/step16/artifacts")
def save_step16_artifacts(project_id: str, body: dict = Body(...), db: Session = Depends(get_db), current_user=Depends(get_current_user)):
    engine = _get_engine(project_id, db)
    engine.save_step16_artifacts(body)
    return APIResponse(code=0, data={"message": "步骤16状态已保存"})


@router.post("/{project_id}/step16/tag")
def create_release_tag(project_id: str, db: Session = Depends(get_db), current_user=Depends(get_current_user)):
    """在Gitea代码库中打版本标签"""
    from app.models.repo import Repo
    repo = db.query(Repo).filter(Repo.project_id == project_id).first()
    if not repo:
        return APIResponse(code=1, message="未找到项目代码库")
    from app.services.gitea_client import gitea_client
    try:
        owner = settings.GITEA_ADMIN_USER
        tag_name = f"v1.0.0-{project_id[:8]}"
        result = asyncio.run(gitea_client.create_tag(owner=owner, repo=repo.name, tag_name=tag_name, branch="main"))
        return APIResponse(code=0, data={"message": f"版本标签 {tag_name} 已创建", "tag": tag_name})
    except Exception as e:
        logger.error(f"创建版本标签失败: {e}")
        return APIResponse(code=1, message=f"创建版本标签失败: {str(e)[:200]}")


@router.post("/{project_id}/step16")
def execute_step16(project_id: str, body: UserSatisfactionRequest,
                   db: Session = Depends(get_db),
                   current_user=Depends(get_current_user)):
    engine = _get_engine(project_id, db)
    if body.satisfied:
        engine.advance_step(16)
        step = engine.complete_step(16)
        return APIResponse(code=0, data={"message": "项目完成！用户确认满意，项目结束", "step": step})
    else:
        result = engine.user_dissatisfied(feedback=body.feedback or "用户不满意")
        return APIResponse(code=0, data={"message": "用户不满意，回到第三步重新迭代", "iteration": result})
