from app.api.workflow.core import (
    router, _get_engine, logger, APIResponse, Depends, get_db,
    get_current_user, Session, Body, Request, HTTPException,
    BaseModel, Optional, asyncio, os, settings, _wf_engines, WorkflowEngine,
)
from app.api.workflow.step4 import (
    SUB_FLOW_CONFIGS, _run_doc_sub_flow, _check_consistency_pairs,
    _fix_doc_from_consistency_feedback,
)
from app.api.ws.step4_progress import broadcast


CONSISTENCY_PAIRS = [
    {"name": "架构设计←→后端设计", "a": "arch_reasonableness", "b": "backend_feasibility"},
    {"name": "前端设计←→后端设计", "a": "frontend_feasibility", "b": "backend_feasibility"},
]

MAX_CONSISTENCY_ROUNDS = 3
CURRENT_DIM = "backend_feasibility"


async def run_sub_step_4_3(
    project_id: str, slug: str, docs_dir: str,
    requirement: str, project_name: str, project_description: str,
    core_goal: str,
    prev_docs_map: dict,
) -> dict:
    """子步骤4_3：后端设计生成+hourong检验+架构/前端一致性收敛"""
    cfg = SUB_FLOW_CONFIGS[2]
    dim_key = cfg["dim"]["key"]

    await broadcast(project_id, {
        "type": "stage",
        "message": f"🚀 step4_3: houwang开始生成{cfg['label']}...",
        "subflow": dim_key,
    })

    result = await _run_doc_sub_flow(
        project_id=project_id, slug=slug, docs_dir=docs_dir,
        cfg=cfg, requirement=requirement,
        project_name=project_name, project_description=project_description,
        core_goal=core_goal,
    )

    if not result["passed"]:
        return result

    # ── 一致性检验 + 仅修复当前子步骤文档 ──
    docs_map = {**prev_docs_map, dim_key: result.get("path", "")}
    consistency_passed = False

    for cc_round in range(1, MAX_CONSISTENCY_ROUNDS + 1):
        await broadcast(project_id, {
            "type": "stage",
            "message": f"🔄 step4_3: 跨文档一致性检验第{cc_round}轮",
            "subflow": dim_key,
        })

        check_result = await _check_consistency_pairs(
            project_id=project_id, docs_map=docs_map,
            pairs=CONSISTENCY_PAIRS,
            project_name=project_name, project_description=project_description,
            core_goal=core_goal,
        )

        if check_result["passed"]:
            consistency_passed = True
            await broadcast(project_id, {
                "type": "stage",
                "message": f"✅ step4_3: 跨文档一致性检验通过",
                "subflow": dim_key,
            })
            break

        feedback_parts = []
        for pair in check_result.get("pairs", []):
            if not pair.get("passed", True) and CURRENT_DIM in pair.get("affected_docs", []):
                feedback_parts.append(f"{pair['name']}: {pair['issue']}")

        if not feedback_parts:
            consistency_passed = True
            break

        feedback = "\n".join(feedback_parts)
        await broadcast(project_id, {
            "type": "stage",
            "message": f"🔄 step4_3: houwang根据一致性反馈修复后端设计（第{cc_round}轮）",
            "subflow": dim_key,
        })

        fix_result = await _fix_doc_from_consistency_feedback(
            project_id=project_id, slug=slug, docs_dir=docs_dir,
            cfg=cfg, requirement=requirement,
            current_content=result.get("content", ""),
            consistency_feedback=feedback,
            project_name=project_name, project_description=project_description,
            core_goal=core_goal,
        )

        result = fix_result
        if fix_result.get("path"):
            docs_map[CURRENT_DIM] = fix_result["path"]

        if fix_result["passed"]:
            consistency_passed = True
            await broadcast(project_id, {
                "type": "stage",
                "message": f"✅ step4_3: 一致性修复后通过检验",
                "subflow": dim_key,
            })
            break

    if not consistency_passed:
        result["passed"] = False
        await broadcast(project_id, {
            "type": "stage",
            "message": f"❌ step4_3: 一致性检验未通过",
            "subflow": dim_key,
        })

    return result


@router.post("/{project_id}/step4_3/execute")
async def execute_step4_3(project_id: str,
                          db: Session = Depends(get_db),
                          current_user=Depends(get_current_user)):
    """异步启动 step4_3：后端设计文档生成+hourong 检验+架构/前端一致性收敛"""
    import asyncio as _asyncio
    from app.database import SessionLocal
    from app.models.project import Project

    try:
        engine = _get_engine(project_id, db)
    except Exception as e:
        return APIResponse(code=1, message=f"无法开始步骤4_3: {str(e)[:200]}")

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

    # 检查前序子步骤
    artifacts = engine.get_step4_artifacts() or {}
    step4_1 = artifacts.get("step4_1_result") or {}
    step4_2 = artifacts.get("step4_2_result") or {}
    if not step4_1.get("passed"):
        return APIResponse(code=1, message="step4_1（架构设计）未通过，请先完成 step4_1")
    if not step4_2.get("passed"):
        return APIResponse(code=1, message="step4_2（前端设计）未通过，请先完成 step4_2")

    prev_docs_map = {
        "arch_reasonableness": step4_1.get("path", ""),
        "frontend_feasibility": step4_2.get("path", ""),
    }

    async def _task():
        try:
            bg_db = SessionLocal()
            try:
                result = await run_sub_step_4_3(
                    project_id=project_id, slug=slug, docs_dir=docs_dir,
                    requirement=requirement, project_name=proj_name,
                    project_description=proj_desc, core_goal=core_goal,
                    prev_docs_map=prev_docs_map,
                )
                bg_engine = WorkflowEngine(project_id=project_id, db=bg_db)
                bg_engine.save_step4_artifacts({
                    "step4_3_result": {
                        "key": result["key"], "label": result.get("label", ""),
                        "path": result.get("path", ""), "passed": result["passed"],
                        "rounds": result.get("rounds", 0),
                        "convergence": result.get("convergence", []),
                    },
                    "message": f"step4_3: {result.get('label', '')} {'通过' if result['passed'] else '未通过'} hourong检验",
                })
                await broadcast(project_id, {
                    "type": "done" if result["passed"] else "error",
                    "message": f"step4_3: 后端设计{'通过✅' if result['passed'] else '未通过❌'}",
                })
            except Exception as e:
                logger.error(f"step4_3 task failed: {e}")
                try:
                    eng = WorkflowEngine(project_id=project_id, db=bg_db)
                    eng.save_step4_artifacts({"step4_3_error": str(e)[:200]})
                except Exception:
                    pass
                await broadcast(project_id, {"type": "error", "message": f"step4_3 失败: {str(e)[:200]}"})
            finally:
                bg_db.close()
        except Exception as e:
            logger.error(f"step4_3 fatal: {e}")

    _asyncio.create_task(_task())
    return APIResponse(code=0, data={
        "message": "step4_3 已启动：后端设计文档生成中",
        "status": "generating",
    })
