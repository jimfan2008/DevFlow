from app.api.workflow.core import (
    router, _get_engine, logger, APIResponse, Depends, get_db,
    get_current_user, Session, Body, Request, HTTPException,
    BaseModel, Optional, asyncio, os, settings, Step3InspectRequest, QAResultRequest,
    DocsListRequest, TDD_PLAN_DIMENSIONS, TDD_TESTCASE_DIMENSIONS,
    _wf_engines, WorkflowEngine,
)

# TDD_PLAN_DIMENSIONS re-exported for use by step6_qa etc.
# Actual execution is now WS-driven in step6_progress, matching step5's architecture


@router.post("/{project_id}/step6/execute")
async def execute_step6_async(project_id: str,
                              db: Session = Depends(get_db),
                              current_user=Depends(get_current_user),
                              resume: bool = False):
    """启动第六步（触发式入口，实际执行走 WS handler，和 step5 一致）"""
    try:
        engine = _get_engine(project_id, db)
        step6_row = engine._get_step_row(6)
        if not resume and step6_row and step6_row.status == "in_progress":
            engine.reset_step(6)
            engine = WorkflowEngine(project_id=project_id, db=db)
            _wf_engines[project_id] = engine
        engine.advance_step(6)
        engine.save_step6_artifacts({"status": "generating", "message": "📋 海梅正在制订TDD测试用例编写计划..."})
    except Exception as e:
        return APIResponse(code=1, message=f"无法开始步骤6: {str(e)[:200]}")
    return APIResponse(code=0, data={"message": "第六步已启动", "status": "generating"})


@router.post("/{project_id}/step6/reset")
def reset_step6(project_id: str, db: Session = Depends(get_db), current_user=Depends(get_current_user)):
    engine = _get_engine(project_id, db)
    engine.reset_step(6)
    _wf_engines.pop(project_id, None)
    return APIResponse(code=0, data={"message": "第六步已重置"})


# ── 保留原有路由 ──

@router.get("/{project_id}/step6/status")
def get_step6_status(project_id: str, db: Session = Depends(get_db), current_user=Depends(get_current_user)):
    engine = _get_engine(project_id, db)
    return APIResponse(code=0, data=engine.get_step6_artifacts())

@router.post("/{project_id}/step6/artifacts")
def save_step6_artifacts_route(project_id: str, body: dict = Body(...), db: Session = Depends(get_db), current_user=Depends(get_current_user)):
    engine = _get_engine(project_id, db)
    engine.save_step6_artifacts(body)
    return APIResponse(code=0, data={"message": "步骤6状态已保存"})


@router.post("/{project_id}/step6/save-doc")
def save_step6_doc(project_id: str, body: Step3InspectRequest, db: Session = Depends(get_db), current_user=Depends(get_current_user)):
    from datetime import datetime
    from app.services.workflow_engine import WorkflowEngine
    from app.models.repo import Repo
    local_dir = body.save_path or os.path.join(os.getcwd(), "docs", "plan")
    os.makedirs(local_dir, exist_ok=True)
    local_filename = body.filename or f"tdd-plan-{datetime.now().strftime('%Y%m%d%H%M%S')}.md"
    local_path = os.path.join(local_dir, local_filename)
    with open(local_path, "w", encoding="utf-8") as f: f.write(body.content)
    engine = WorkflowEngine(project_id=project_id, db=db)
    engine.save_step6_artifacts({"tdd_plan": body.content, "filename": local_filename, "local_path": local_path, "saved_at": datetime.now().isoformat()})
    repo = db.query(Repo).filter(Repo.project_id == project_id).first()
    if not repo:
        return APIResponse(code=0, data={"message": "已保存", "local_path": local_path})
    from app.services.gitea_client import gitea_client
    try:
        filepath = f"docs/plan/tdd-plan-{datetime.now().strftime('%Y%m%d%H%M%S')}.md"
        result = asyncio.run(gitea_client.create_file(owner=settings.GITEA_ADMIN_USER, repo=repo.name, filepath=filepath, content=body.content, message="TDD plan", branch="main"))
        return APIResponse(code=0, data={"message": "已保存", "local_path": local_path, "filepath": filepath})
    except Exception as e:
        return APIResponse(code=0, data={"message": f"已保存到本地（Gitea失败: {e}）", "local_path": local_path})


@router.post("/{project_id}/step6/list-docs")
def list_step6_docs(project_id: str, body: DocsListRequest, current_user=Depends(get_current_user)):
    import glob
    docs_path = body.path
    if not docs_path or not os.path.isdir(docs_path):
        return APIResponse(code=0, data={"files": []})
    files = [{"name": os.path.basename(f), "path": f, "content": open(f, "r", encoding="utf-8").read()} for f in sorted(glob.glob(os.path.join(docs_path, "*.md")))]
    return APIResponse(code=0, data={"files": files})


@router.post("/{project_id}/step6/inspect")
async def inspect_step6_tdd_plan(project_id: str, body: Step3InspectRequest, db: Session = Depends(get_db), current_user=Depends(get_current_user)):
    from app.api.ws.step3_qa import _inspect_via_subagent
    import json as _json
    content, focus_items = body.content, body.focus_items
    if not content or len(content.strip()) < 20:
        return APIResponse(code=0, data={"passed": False, "dimensions": [{"key": d["key"], "passed": False} for d in TDD_PLAN_DIMENSIONS]})
    active_dims = [d for d in TDD_PLAN_DIMENSIONS if not focus_items or d["key"] in focus_items]
    dims_json = _json.dumps([{'检验项目': d['label'], '检验标准': d['description']} for d in active_dims], ensure_ascii=False, indent=2)
    focus_hint = f"\n⚠️ 本次只检验：{[d['label'] for d in active_dims]}" if focus_items else ""
    convergence_hint = "\n⚠️ 收敛性要求：检验报告必须聚焦于不合格项，明确指出不合格项的问题和修改方向。后续Agent将只修改不合格项，禁止扩大范围。已合格项目不得提出修改要求。"
    scoring_hint = "\n评分规则：每个维度起始100分，每发现一个缺陷扣减相应分数（轻微缺陷扣5-10分，一般缺陷扣15-20分，严重缺陷扣25-30分）。维度得分≥90则该维度passed为true。所有维度平均分>90分为整体合格。"
    prompt = f"你是一个专业的测试计划QA检验员（后荣）。请严格检验以下TDD测试用例编写计划。\n\n=== TDD计划 ===\n{content}\n\n=== 检验项目与标准 ===\n{dims_json}\n{focus_hint}\n{convergence_hint}\n{scoring_hint}\n\n直接输出 JSON 数组：\n[\n" + ",\n".join(f'  {{"key": "{d["key"]}", "score": 100, "deduction": "", "passed": true/false, "detail": "..."}}' for d in active_dims) + "\n]"
    try:
        reply = await _inspect_via_subagent(prompt=prompt, max_retries=3)
        if not reply: raise ValueError("后荣未返回")
        parsed = _json.loads(reply)
        if not isinstance(parsed, list): raise ValueError("不是数组")
    except Exception as e:
        return APIResponse(code=0, data={"passed": False, "dimensions": [{"key": d["key"], "passed": False} for d in active_dims]})
    results = []
    for dim in active_dims:
        m = next((r for r in parsed if r.get("key") == dim["key"]), None)
        dim_score = int(m.get("score", 100)) if m else 0
        results.append({"key": dim["key"], "label": dim["label"], "score": dim_score, "passed": dim_score >= 90, "detail": m.get("detail", "") if m else ""})
    avg_score = sum(r.get("score", 0) for r in results) / len(results) if results else 0
    all_passed = avg_score > 90
    _engine = _get_engine(project_id, db)
    _engine.save_step6_artifacts({
        "inspect_result": {"passed": all_passed, "avg_score": avg_score, "dimensions": results, "inspected_at": __import__('datetime').datetime.now(__import__('datetime').timezone.utc).isoformat()},
        "qa_passed": all_passed, "qa_checked": True,
    })
    return APIResponse(code=0, data={"passed": avg_score > 90, "score": avg_score, "dimensions": results})


@router.get("/{project_id}/step6/test-cases")
def list_tdd_test_cases(project_id: str, round_number: int = None, db: Session = Depends(get_db), current_user=Depends(get_current_user)):
    from app.models.tdd_test_case import TDDTestCase
    q = db.query(TDDTestCase).filter(TDDTestCase.project_id == project_id)
    if round_number:
        q = q.filter(TDDTestCase.round_number == round_number)
    cases = q.order_by(TDDTestCase.round_number.desc(), TDDTestCase.case_index).all()
    return APIResponse(code=0, data={"test_cases": [c.to_dict() for c in cases]})


@router.get("/{project_id}/step6/test-cases/summary")
def list_tdd_test_cases_summary(project_id: str, db: Session = Depends(get_db), current_user=Depends(get_current_user)):
    from app.models.tdd_test_case import TDDTestCase
    from sqlalchemy import func
    rows = db.query(
        TDDTestCase.round_number,
        func.count(TDDTestCase.id).label("total"),
        func.sum(TDDTestCase.qa_status == "passed").label("passed"),
        func.sum(TDDTestCase.qa_status == "failed").label("failed"),
    ).filter(
        TDDTestCase.project_id == project_id
    ).group_by(TDDTestCase.round_number).order_by(TDDTestCase.round_number.desc()).all()
    result = []
    for r in rows:
        result.append({
            "round_number": r.round_number,
            "total": r.total,
            "passed": r.passed or 0,
            "failed": r.failed or 0,
        })
    return APIResponse(code=0, data={"rounds": result})


@router.post("/{project_id}/step6/qa")
def qa_step6(project_id: str, body: QAResultRequest, db: Session = Depends(get_db), current_user=Depends(get_current_user)):
    from datetime import datetime, timezone
    engine = _get_engine(project_id, db)
    now_iso = datetime.now(timezone.utc).isoformat()
    if body.result == "passed":
        result = engine.pass_qa(6)
        engine.save_step6_artifacts({"qa_passed": True, "qa_status": "passed", "qa_checked_at": now_iso})
    else:
        result = engine.fail_qa(6, reason=body.reason or "", suggestions=body.suggestions)
        engine.save_step6_artifacts({"qa_passed": False, "qa_status": "failed", "qa_checked_at": now_iso, "qa_fail_reason": body.reason, "qa_suggestions": body.suggestions})
    return APIResponse(code=0, data={"message": f"第六步QA{'通过' if body.result == 'passed' else '未通过'}", "qa": result})