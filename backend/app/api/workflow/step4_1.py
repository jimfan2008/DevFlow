from app.api.workflow.core import (
    router, _get_engine, logger, APIResponse, Depends, get_db,
    get_current_user, Session, Body, Request, HTTPException,
    BaseModel, Optional, asyncio, os, settings, _wf_engines, WorkflowEngine,
)
from app.api.workflow.step4 import (
    SUB_FLOW_CONFIGS, _run_doc_sub_flow,
)
from app.api.ws.step4_progress import broadcast


async def run_sub_step_4_1(
    project_id: str, slug: str, docs_dir: str,
    requirement: str, project_name: str, project_description: str,
    core_goal: str,
) -> dict:
    """子步骤4_1：架构设计文档生成+hourong检验收敛（无一致性检验）"""
    cfg = SUB_FLOW_CONFIGS[0]
    dim_key = cfg["dim"]["key"]

    await broadcast(project_id, {
        "type": "stage",
        "message": f"🚀 step4_1: houwang开始生成{cfg['label']}...",
        "subflow": dim_key,
    })

    result = await _run_doc_sub_flow(
        project_id=project_id, slug=slug, docs_dir=docs_dir,
        cfg=cfg, requirement=requirement,
        project_name=project_name, project_description=project_description,
        core_goal=core_goal,
    )
    return result


@router.post("/{project_id}/step4_1/execute")
async def execute_step4_1(project_id: str,
                          db: Session = Depends(get_db),
                          current_user=Depends(get_current_user)):
    """异步启动 step4_1：架构设计文档生成+hourong 检验收敛"""
    import asyncio as _asyncio
    from app.database import SessionLocal
    from app.models.project import Project

    try:
        engine = _get_engine(project_id, db)
    except Exception as e:
        return APIResponse(code=1, message=f"无法开始步骤4_1: {str(e)[:200]}")

    step3 = engine.get_step3_artifacts() or {}
    requirement = (step3.get("doc_content") or step3.get("content") or
                   step3.get("requirement") or step3.get("srs") or "")
    if not requirement:
        return APIResponse(code=1, message="未找到 Step3 需求文档，请先完成需求分析")

    step2 = engine.get_step2_artifacts() or {}
    core_goal = step2.get("confirmed_goal") or step2.get("core_goal") or ""

    proj = db.query(Project).filter(Project.id == project_id).first()
    if not proj:
        return APIResponse(code=1, message="项目不存在")
    slug = proj.slug if proj.slug else project_id.replace("-", "")
    proj_name = proj.name or ""
    proj_desc = proj.description or ""
    docs_dir = os.path.join(settings.PROJECTS_BASE_DIR, slug, "docs")
    os.makedirs(docs_dir, exist_ok=True)

    async def _task():
        try:
            bg_db = SessionLocal()
            try:
                result = await run_sub_step_4_1(
                    project_id=project_id, slug=slug, docs_dir=docs_dir,
                    requirement=requirement, project_name=proj_name,
                    project_description=proj_desc, core_goal=core_goal,
                )
                bg_engine = WorkflowEngine(project_id=project_id, db=bg_db)
                bg_engine.save_step4_artifacts({
                    "step4_1_result": {
                        "key": result["key"], "label": result.get("label", ""),
                        "path": result.get("path", ""), "passed": result["passed"],
                        "rounds": result.get("rounds", 0),
                        "convergence": result.get("convergence", []),
                    },
                    "message": f"step4_1: {result.get('label', '')} {'通过' if result['passed'] else '未通过'} hourong检验",
                })
                await broadcast(project_id, {
                    "type": "done" if result["passed"] else "error",
                    "message": f"step4_1: 架构设计{'通过✅' if result['passed'] else '未通过❌'}",
                })
            except Exception as e:
                logger.error(f"step4_1 task failed: {e}")
                try:
                    eng = WorkflowEngine(project_id=project_id, db=bg_db)
                    eng.save_step4_artifacts({"step4_1_error": str(e)[:200]})
                except Exception:
                    pass
                await broadcast(project_id, {"type": "error", "message": f"step4_1 失败: {str(e)[:200]}"})
            finally:
                bg_db.close()
        except Exception as e:
            logger.error(f"step4_1 fatal: {e}")

    _asyncio.create_task(_task())
    return APIResponse(code=0, data={
        "message": "step4_1 已启动：架构设计文档生成中",
        "status": "generating",
    })
