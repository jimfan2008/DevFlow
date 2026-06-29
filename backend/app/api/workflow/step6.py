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
    from app.services.gateway_client import GatewayClient
    import json as _json
    content, focus_items = body.content, body.focus_items
    if not content or len(content.strip()) < 20:
        return APIResponse(code=0, data={"passed": False, "dimensions": [{"key": d["key"], "passed": False} for d in TDD_PLAN_DIMENSIONS]})
    active_dims = [d for d in TDD_PLAN_DIMENSIONS if not focus_items or d["key"] in focus_items]
    dims_json = _json.dumps([{'检验项目': d['label'], '检验标准': d['description']} for d in active_dims], ensure_ascii=False, indent=2)
    focus_hint = f"\n⚠️ 本次只检验：{[d['label'] for d in active_dims]}" if focus_items else ""
    convergence_hint = "\n⚠️ 收敛性要求：检验报告必须聚焦于不合格项，明确指出不合格项的问题和修改方向。后续Agent将只修改不合格项，禁止扩大范围。已合格项目不得提出修改要求。"
    prompt = f"你是一个专业的测试计划QA检验员（后荣）。请严格检验以下TDD测试用例编写计划。\n\n=== TDD计划 ===\n{content}\n\n=== 检验项目与标准 ===\n{dims_json}\n{focus_hint}\n{convergence_hint}\n\n直接输出 JSON 数组：\n[\n" + ",\n".join(f'  {{"key": "{d["key"]}", "passed": true/false, "detail": "..."}}' for d in active_dims) + "\n]"
    try:
        client = GatewayClient(profile_name="hourong", timeout=120)
        chunks = []
        async for chunk in client.chat_completions(messages=[{"role": "user", "content": prompt}], stream=False, max_tokens=2000):
            chunks.append(chunk)
        reply = "".join(chunks).strip()
        if not reply: raise ValueError("后荣未返回")
        parsed = _json.loads(reply)
        if not isinstance(parsed, list): raise ValueError("不是数组")
    except Exception as e:
        return APIResponse(code=0, data={"passed": False, "dimensions": [{"key": d["key"], "passed": False} for d in active_dims]})
    results = []
    for dim in active_dims:
        m = next((r for r in parsed if r.get("key") == dim["key"]), None)
        results.append({"key": dim["key"], "label": dim["label"], "passed": bool(m.get("passed", False)) if m else False, "detail": m.get("detail", "") if m else ""})
    return APIResponse(code=0, data={"passed": all(r["passed"] for r in results), "dimensions": results})


@router.post("/{project_id}/step6/qa")
def qa_step6(project_id: str, body: QAResultRequest, db: Session = Depends(get_db), current_user=Depends(get_current_user)):
    engine = _get_engine(project_id, db)
    if body.result == "passed":
        result = engine.pass_qa(6)
    else:
        result = engine.fail_qa(6, reason=body.reason or "", suggestions=body.suggestions)
    return APIResponse(code=0, data={"message": f"第六步QA{'通过' if body.result == 'passed' else '未通过'}", "qa": result})