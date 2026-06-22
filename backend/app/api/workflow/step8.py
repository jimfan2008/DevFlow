import glob
from app.api.workflow.core import (
    router, _get_engine, logger, APIResponse, Depends, get_db,
    get_current_user, Session, Body, Request, HTTPException,
    BaseModel, Optional, asyncio, os, settings, Step3InspectRequest, QAResultRequest, DocsListRequest,
    CODE_PLAN_DIMENSIONS, _wf_engines, WorkflowEngine,
)

async def _inspect_code_plan(project_id: str, doc_path: str, project_name: str = "", project_description: str = "", core_goal: str = "", agent_label: str = "", max_retries: int = 3) -> dict:
    import json as _json, asyncio as _asyncio
    from app.services.gateway_client import GatewayClient
    from app.api.ws.step4_progress import broadcast
    dims_json = str([{'检验项目': d['label'], '检验标准': d['description'], '检验维': d['key']} for d in CODE_PLAN_DIMENSIONS])
    for attempt in range(1, max_retries + 1):
        if attempt > 1:
            await _asyncio.sleep(2)
            await broadcast(project_id, {"type": "step8", "message": f"🔄 hourong 第{attempt}次检验编码计划..."})
        insp_prompt = f"你是一个专业的代码计划QA检验员（后荣）。请严格检验以下代码编写计划。\n\n=== 检验项目与标准 ===\n{dims_json}\n\n=== 文档路径 ===\n{doc_path}\n\n请读取该文档文件，严格逐项检验。\n只输出 JSON 数组:\n" + ",\n".join(f'  {{"key": "{d["key"]}", "passed": true/false, "detail": "具体检验意见..."}}' for d in CODE_PLAN_DIMENSIONS)
        qa_cli = GatewayClient(profile_name="hourong", timeout=180)
        qa_chunks = []
        async for chunk in qa_cli.chat_isolated(messages=[{"role": "user", "content": insp_prompt}], project_id=project_id, project_name=project_name, project_description=project_description, core_goal=core_goal, agent_name=agent_label or "后荣-编码计划QA检验员", stream=True, max_tokens=8192):
            qa_chunks.append(chunk)
        qa_r = "".join(qa_chunks).strip()
        if not qa_r:
            if attempt < max_retries:
                await broadcast(project_id, {"type": "step8", "message": f"⚠️ 未返回，重试（第{attempt}次）"})
                continue
            return {"detail": f"后荣{max_retries}次均未返回"}
        brace_s, brace_e = qa_r.find('['), qa_r.rfind(']') + 1
        if brace_s != -1 and brace_e > brace_s:
            qa_r = qa_r[brace_s:brace_e]
        try:
            parsed = _json.loads(qa_r)
        except Exception:
            if attempt < max_retries:
                await broadcast(project_id, {"type": "step8", "message": f"⚠️ 格式异常，重试（第{attempt}次）"})
                continue
            return {"detail": "后荣未返回检验结果"}
        if isinstance(parsed, list) and parsed:
            return {"passed": all(bool(r.get("passed")) for r in parsed), "detail": "", "failed_details": [r.get("detail", "") for r in parsed if not r.get("passed")], "results": parsed}
        if attempt < max_retries:
            await broadcast(project_id, {"type": "step8", "message": f"⚠️ 格式异常，重试（第{attempt}次）"})
            continue
        return {"detail": "后荣未返回检验结果"}
    return {"detail": "后荣检验失败"}


@router.post("/{project_id}/step8/execute")
async def execute_step8_async(project_id: str, db: Session = Depends(get_db), current_user=Depends(get_current_user), resume: bool = False):
    from app.services.workflow_engine import WorkflowEngine
    import asyncio as _asyncio
    try:
        engine = _get_engine(project_id, db)
        if resume:
            existing = engine.get_step8_artifacts() or {}
        else:
            row = engine._get_step_row(8)
            if row and row.status == "in_progress":
                engine.reset_step(8)
                engine = WorkflowEngine(project_id=project_id, db=db)
                _wf_engines[project_id] = engine
            engine.advance_step(8)
            existing = {}
    except Exception as e:
        return APIResponse(code=1, message=f"无法开始步骤8: {str(e)[:200]}")
    step3 = engine.get_step3_artifacts() or {}
    requirement = (step3.get("doc_content") or step3.get("content") or step3.get("requirement") or step3.get("srs") or "")
    step4 = engine.get_step4_artifacts() or {}
    design_doc = step4.get("design_doc") or ""
    step7 = engine.get_step7_artifacts() or {}
    tdd_cases = step7.get("tdd_cases") or step7.get("test_cases") or ""
    step2 = engine.get_step2_artifacts() or {}
    core_goal = step2.get("confirmed_goal") or step2.get("core_goal") or ""
    engine.save_step8_artifacts({"status": "generating", "message": "📐 海梅正在制订代码编写计划..."})

    async def _generate():
        try:
            from app.database import SessionLocal
            from app.models.project import Project
            from app.api.ws.step4_progress import broadcast
            bg_db = SessionLocal()
            try:
                bg_engine = WorkflowEngine(project_id=project_id, db=bg_db)
                proj = bg_db.query(Project).filter(Project.id == project_id).first()
                slug = proj.slug if proj else project_id.replace("-", "")
                docs_dir = os.path.join(settings.PROJECTS_BASE_DIR, slug, "docs")
                os.makedirs(docs_dir, exist_ok=True)
                proj_name = proj.name if proj else ""
                proj_desc = proj.description or ""
                prev = existing if resume else {}
                if resume and prev.get("qa_passed") and prev.get("doc_path") and os.path.exists(prev["doc_path"]):
                    await broadcast(project_id, {"type": "step8", "message": "♻️ 续跑：编码计划已通过，跳过"})
                    bg_engine.save_step8_artifacts({**prev, "status": "done", "message": "♻️ 续跑：编码计划已通过"})
                    bg_engine.complete_step(8)
                    await broadcast(project_id, {"type": "done", "message": "✅ 编码计划已生成（续跑）"})
                    return
                max_ver = 0
                for f in glob.glob(os.path.join(docs_dir, f"{slug}_codeplan_V*.md")):
                    import re as _re
                    m = _re.search(r'V(\d+)', os.path.basename(f))
                    if m:
                        max_ver = max(max_ver, int(m.group(1)))
                convergence_log, final_path, final_content = [], "", ""
                for fix_round in range(1, 11):
                    nv = max_ver + fix_round
                    gen_path = os.path.join(docs_dir, f"{slug}_codeplan_V{nv}.md")
                    await broadcast(project_id, {"type": "step8", "message": f"📐 海梅正在{'修复' if fix_round > 1 else '制订'}编码计划（第{fix_round}轮）..."})
                    feedback = ""
                    if fix_round > 1 and convergence_log:
                        failed = convergence_log[-1].get("failed_details", [])
                        feedback = "需要修正的问题（只修复这些问题，禁止扩大范围）：\n" + "\n".join(f"- {d}" for d in failed if d)
                    prompt = (
                        "你是资深项目经理海梅（HaiMei），负责制订代码编写计划和任务依赖图。\n\n"
                        f"=== 需求文档 ===\n{requirement}\n\n=== 架构设计文档 ===\n{design_doc}\n\n"
                        f"=== TDD测试用例 ===\n{str(tdd_cases)}\n\n"
                        + (f"=== 上次检验未通过项 ===\n{feedback}\n只针对不合格项修改，不要扩大修改范围。\n\n" if feedback else "")
                        + f"请将完整计划保存到：{gen_path}\n要求：1.每个任务最小原子化 2.每个任务有TDD测试用例一一对应\n3.画出任务依赖图（标注前置依赖和执行顺序） 4.标注每个任务的优先级和预计工时\n不要输出推理过程。"
                    )
                    client = GatewayClient(profile_name="haimei", timeout=5400)
                    chunks = []
                    async for chunk in client.chat_isolated(messages=[{"role": "user", "content": prompt}], project_id=project_id, project_name=proj_name, project_description=proj_desc, core_goal=core_goal, agent_name="海梅（HaiMei）-编码计划制订", stream=True, max_tokens=64000):
                        if chunk.strip():
                            chunks.append(chunk)
                            await broadcast(project_id, {"type": "step8", "content": chunk})
                    if os.path.exists(gen_path):
                        content = open(gen_path, "r", encoding="utf-8").read()
                    else:
                        content = "".join(chunks).strip()
                        with open(gen_path, "w", encoding="utf-8") as f:
                            f.write(content)
                    if not content.strip():
                        await broadcast(project_id, {"type": "step8", "message": "❌ 海梅未生成有效内容，重试"})
                        continue
                    final_path, final_content = gen_path, content
                    bg_engine.save_step8_artifacts({"code_plan": content, "doc_path": gen_path, "status": "generating"})
                    await broadcast(project_id, {"type": "step8", "message": f"🔍 hourong 正在检验编码计划（文件：{gen_path}）"})
                    qa_result = await _inspect_code_plan(project_id, gen_path, project_name=proj_name, project_description=proj_desc, core_goal=core_goal)
                    convergence_log.append({"round": fix_round, "detail": qa_result.get("detail", ""), "passed": qa_result.get("passed", False), "failed_details": qa_result.get("failed_details", [])})
                    if qa_result.get("passed"):
                        await broadcast(project_id, {"type": "step8", "message": f"✅ 编码计划已通过 hourong 检验（共{fix_round}轮）"})
                        bg_engine.save_step8_artifacts({"code_plan": content, "doc_path": gen_path, "convergence": convergence_log, "status": "done", "qa_passed": True, "message": "✅ 编码计划制订完成"})
                        bg_engine.complete_step(8)
                        await broadcast(project_id, {"type": "done", "message": "✅ 编码计划已生成"})
                        return
                    await broadcast(project_id, {"type": "step8", "message": f"⚠️ 未通过，修复中"})
                await broadcast(project_id, {"type": "error", "message": "❌ 经10轮仍未通过检验"})
                bg_engine.save_step8_artifacts({"code_plan": final_content, "doc_path": final_path, "convergence": convergence_log, "status": "error"})
                bg_engine.reset_step(8)
            except Exception as e:
                logger.error(f"Step8: {e}")
                try:
                    bg_engine = WorkflowEngine(project_id=project_id, db=bg_db)
                    bg_engine.save_step8_artifacts({"status": "error", "message": f"失败: {str(e)[:200]}"})
                    bg_engine.reset_step(8)
                except Exception:
                    pass
            finally:
                bg_db.close()
        except Exception as e:
            logger.error(f"Step8 fatal: {e}")
    _asyncio.create_task(_generate())
    return APIResponse(code=0, data={"message": "第八步已启动", "status": "generating"})


@router.post("/{project_id}/step8/reset")
def reset_step8(project_id: str, db: Session = Depends(get_db), current_user=Depends(get_current_user)):
    engine = _get_engine(project_id, db)
    engine.reset_step(8)
    _wf_engines.pop(project_id, None)
    return APIResponse(code=0, data={"message": "第八步已重置"})


@router.get("/{project_id}/step8/status")
def get_step8_status(project_id: str, db: Session = Depends(get_db), current_user=Depends(get_current_user)):
    engine = _get_engine(project_id, db)
    return APIResponse(code=0, data=engine.get_step8_artifacts())


@router.post("/{project_id}/step8/artifacts")
def save_step8_artifacts_route(project_id: str, body: dict = Body(...), db: Session = Depends(get_db), current_user=Depends(get_current_user)):
    engine = _get_engine(project_id, db)
    engine.save_step8_artifacts(body)
    return APIResponse(code=0, data={"message": "步骤8状态已保存"})


@router.post("/{project_id}/step8/save-doc")
def save_step8_doc(project_id: str, body: Step3InspectRequest, db: Session = Depends(get_db), current_user=Depends(get_current_user)):
    """保存编码计划到本地和代码库"""
    from datetime import datetime
    from app.services.workflow_engine import WorkflowEngine
    from app.models.repo import Repo
    from app.services.gitea_client import gitea_client
    local_dir = body.save_path or os.path.join(os.getcwd(), "docs", "plan")
    os.makedirs(local_dir, exist_ok=True)
    local_filename = body.filename or f"code-plan-{datetime.now().strftime('%Y%m%d%H%M%S')}.md"
    local_path = os.path.join(local_dir, local_filename)
    with open(local_path, "w", encoding="utf-8") as f:
        f.write(body.content)
    engine = WorkflowEngine(project_id=project_id, db=db)
    engine.save_step8_artifacts({"code_plan": body.content, "filename": local_filename, "local_path": local_path, "saved_at": datetime.now().isoformat()})
    repo = db.query(Repo).filter(Repo.project_id == project_id).first()
    if not repo:
        return APIResponse(code=0, data={"message": "已保存", "local_path": local_path})
    try:
        filepath = f"docs/plan/code-plan-{datetime.now().strftime('%Y%m%d%H%M%S')}.md"
        result = asyncio.run(gitea_client.create_file(owner=settings.GITEA_ADMIN_USER, repo=repo.name, filepath=filepath, content=body.content, message="Code plan", branch="main"))
        return APIResponse(code=0, data={"message": "已保存", "local_path": local_path, "filepath": filepath})
    except Exception as e:
        return APIResponse(code=0, data={"message": f"本地已保存（Gitea失败）", "local_path": local_path})


@router.post("/{project_id}/step8/list-docs")
def list_step8_docs(project_id: str, body: DocsListRequest, current_user=Depends(get_current_user)):
    import glob as _glob
    docs_path = body.path
    if not docs_path or not os.path.isdir(docs_path):
        return APIResponse(code=0, data={"files": []})
    files = []
    for f in sorted(_glob.glob(os.path.join(docs_path, "*.md"))):
        try:
            content = open(f, "r", encoding="utf-8").read()
            files.append({"name": os.path.basename(f), "path": f, "content": content})
        except Exception:
            files.append({"name": os.path.basename(f), "path": f, "content": ""})
    return APIResponse(code=0, data={"files": files})


@router.post("/{project_id}/step8/inspect")
async def inspect_step8(project_id: str, body: Step3InspectRequest, db: Session = Depends(get_db), current_user=Depends(get_current_user)):
    from app.services.gateway_client import GatewayClient
    import json as _json
    content, focus_items = body.content, body.focus_items
    if not content or len(content.strip()) < 20:
        return APIResponse(code=0, data={"passed": False, "dimensions": [{"key": d["key"], "passed": False} for d in CODE_PLAN_DIMENSIONS]})
    active_dims = [d for d in CODE_PLAN_DIMENSIONS if not focus_items or d["key"] in focus_items]
    dims_json = _json.dumps([{'检验项目': d['label'], '检验标准': d['description']} for d in active_dims], ensure_ascii=False, indent=2)
    focus_hint = f"\n⚠️ 本次只检验：{[d['label'] for d in active_dims]}" if focus_items else ""
    prompt = f"你是一个专业的代码计划QA检验员（后荣）。\n\n=== 编码计划 ===\n{content}\n\n=== 检验项目 ===\n{dims_json}\n{focus_hint}\n\n直接输出 JSON 数组：\n[\n" + ",\n".join(f'  {{"key": "{d["key"]}", "passed": true/false, "detail": "..."}}' for d in active_dims) + "\n]"
    try:
        client = GatewayClient(profile_name="hourong", timeout=120)
        chunks = []
        async for chunk in client.chat_completions(messages=[{"role": "user", "content": prompt}], stream=False, max_tokens=2000):
            chunks.append(chunk)
        reply = "".join(chunks).strip()
        if not reply:
            raise ValueError("后荣未返回")
        parsed = _json.loads(reply)
        if not isinstance(parsed, list):
            raise ValueError("不是数组")
    except Exception:
        return APIResponse(code=0, data={"passed": False, "dimensions": [{"key": d["key"], "passed": False} for d in active_dims]})
    results = []
    for dim in active_dims:
        m = next((r for r in parsed if r.get("key") == dim["key"]), None)
        results.append({"key": dim["key"], "label": dim["label"], "passed": bool(m.get("passed", False)) if m else False, "detail": m.get("detail", "") if m else ""})
    return APIResponse(code=0, data={"passed": all(r["passed"] for r in results), "dimensions": results})


@router.post("/{project_id}/step8/qa")
def qa_step8(project_id: str, body: QAResultRequest, db: Session = Depends(get_db), current_user=Depends(get_current_user)):
    engine = _get_engine(project_id, db)
    if body.result == "passed":
        result = engine.pass_qa(8)
    else:
        result = engine.fail_qa(8, reason=body.reason or "", suggestions=body.suggestions)
    return APIResponse(code=0, data={"message": f"第八步QA{'通过' if body.result == 'passed' else '未通过'}", "qa": result})