import glob
from app.api.workflow.core import (
    router, _get_engine, logger, APIResponse, Depends, get_db,
    get_current_user, Session, Body, Request, HTTPException,
    BaseModel, Optional, asyncio, os, settings, Step3InspectRequest, QAResultRequest, DocsListRequest,
    DOC_INSPECTION_DIMENSIONS, Step14ChatRequest, _wf_engines, WorkflowEngine,
)


@router.post("/{project_id}/step14/chat")
async def step14_chat(project_id: str, body: Step14ChatRequest,
                      db: Session = Depends(get_db), current_user=Depends(get_current_user)):
    """后贵（HouGui）对话 - 项目隔离"""
    from app.services.gateway_client import GatewayClient
    from app.models.project import Project
    try:
        engine = _get_engine(project_id, db)
        step2 = engine.get_step2_artifacts()
        core_goal = step2.get("confirmed_goal") or step2.get("core_goal") or ""
        project = db.query(Project).filter(Project.id == project_id).first()
        if not project:
            raise HTTPException(status_code=404, detail="Project not found")
        messages = body.messages + [{"role": "user", "content": body.message}]
        client = GatewayClient(profile_name="hougui", timeout=1200)
        reply_chunks = []
        async for chunk in client.chat_isolated(messages=messages, project_id=project_id, project_name=project.name, project_description=project.description or "", core_goal=core_goal, agent_name="后贵（HouGui）文档管理员", stream=False):
            reply_chunks.append(chunk)
        reply = "".join(reply_chunks)
        if not reply or len(reply.strip()) < 5:
            return APIResponse(code=1, message="后贵未生成有效回复", data=None)
        return APIResponse(code=0, message="success", data={"reply": reply})
    except HTTPException:
        raise
    except Exception as e:
        logger.error(f"Step14 chat: {e}")
        return APIResponse(code=1, message="与后贵对话失败", data=None)


async def _inspect_doc(project_id: str, doc_path: str, project_name: str = "", project_description: str = "", core_goal: str = "", agent_label: str = "", max_retries: int = 3, failed_keys: list = None) -> dict:
    import json as _json, asyncio as _asyncio
    from app.services.gateway_client import GatewayClient
    from app.api.ws.step4_progress import broadcast
    active_dims = [d for d in DOC_INSPECTION_DIMENSIONS if not failed_keys or d["key"] in failed_keys]
    dims_json = str([{'检验项目': d['label'], '检验标准': d['description'], '检验维': d['key']} for d in active_dims])
    for attempt in range(1, max_retries + 1):
        if attempt > 1:
            await _asyncio.sleep(2)
            await broadcast(project_id, {"type": "step14", "message": f"🔄 hourong 第{attempt}次重新检验项目文档..."})
        focus_hint = f"\n⚠️ 本次只需重新检验以下 {len(active_dims)} 项（上一轮不合格项）：{[d['label'] for d in active_dims]}\n请只针对这些项目做出通过/不通过判定，禁止扩大检验范围。" if failed_keys else ""
        insp_prompt = f"你是一个专业的文档QA检验员（后荣）。请严格检验以下项目文档。\n\n=== 检验项目与标准 ===\n{dims_json}\n{focus_hint}\n\n=== 文档路径 ===\n{doc_path}\n\n请读取该文档文件，严格逐项检验。\n⚠️ 收敛性要求：检验报告必须聚焦于不合格项，明确指出不合格项的问题和修改方向。后续Agent将只修改不合格项，禁止扩大范围。已合格项目不得提出修改要求。\n评分规则：每个检验维起始100分，每发现一个缺陷扣减相应分数（轻微缺陷扣5-10分，一般缺陷扣15-20分，严重缺陷扣25-30分）。维度得分≥90则该维度passed为true。所有维度平均分>90分为整体合格。\n只输出 JSON 数组:\n" + ",\n".join(f'  {{"key": "{d["key"]}", "score": 100, "deduction": "", "passed": true/false, "detail": "具体检验意见..."}}' for d in active_dims)
        qa_cli = GatewayClient(profile_name="hourong", timeout=180)
        qa_chunks = []
        async for chunk in qa_cli.chat_isolated(messages=[{"role": "user", "content": insp_prompt}], project_id=project_id, project_name=project_name, project_description=project_description, core_goal=core_goal, agent_name=agent_label or "后荣-项目文档QA检验员", stream=True, max_tokens=8192):
            qa_chunks.append(chunk)
        qa_r = "".join(qa_chunks).strip()
        if not qa_r:
            if attempt < max_retries:
                await broadcast(project_id, {"type": "step14", "message": f"⚠️ hourong 未返回，重试（第{attempt}次）"})
                continue
            return {"detail": f"后荣{max_retries}次均未返回"}
        brace_s, brace_e = qa_r.find('['), qa_r.rfind(']') + 1
        if brace_s != -1 and brace_e > brace_s:
            qa_r = qa_r[brace_s:brace_e]
        try:
            parsed = _json.loads(qa_r)
        except Exception:
            if attempt < max_retries:
                await broadcast(project_id, {"type": "step14", "message": f"⚠️ hourong 格式异常，重试（第{attempt}次）"})
                continue
            return {"detail": "后荣未返回检验结果"}
        if isinstance(parsed, list) and parsed:
            scores = [int(r.get("score", 100)) for r in parsed]
            avg_score = sum(scores) / len(scores)
            return {"passed": avg_score > 90, "score": avg_score, "total_score": sum(scores), "max_score": len(scores) * 100, "detail": "", "failed_details": [r.get("detail", "") for r in parsed if int(r.get("score", 100)) < 90], "results": parsed}
        if attempt < max_retries:
            await broadcast(project_id, {"type": "step14", "message": f"⚠️ hourong 格式异常，重试（第{attempt}次）"})
            continue
        return {"detail": "后荣未返回检验结果"}
    return {"detail": "后荣检验失败"}


@router.post("/{project_id}/step14/execute")
async def execute_step14_async(project_id: str, db: Session = Depends(get_db), current_user=Depends(get_current_user), resume: bool = False):
    """异步启动第十四步：后贵完善项目文档，hourong 自动检验+收敛修复"""
    import asyncio as _asyncio
    try:
        engine = _get_engine(project_id, db)
        if resume:
            existing = engine.get_step14_artifacts() or {}
        else:
            step14_row = engine._get_step_row(14)
            if step14_row and step14_row.status == "in_progress":
                engine.reset_step(14)
                engine = WorkflowEngine(project_id=project_id, db=db)
                _wf_engines[project_id] = engine
            engine.advance_step(14)
            existing = {}
    except Exception as e:
        return APIResponse(code=1, message=f"无法开始步骤14: {str(e)[:200]}")
    step3 = engine.get_step3_artifacts() or {}
    requirement = (step3.get("doc_content") or step3.get("content") or step3.get("requirement") or step3.get("srs") or "")
    step4 = engine.get_step4_artifacts() or {}
    design_doc = step4.get("design_doc") or ""
    step9 = engine.get_step9_artifacts() or {}
    code = step9.get("code") or step9.get("content") or ""
    step11 = engine.get_step11_artifacts() or {}
    test_report = step11.get("test_report") or step11.get("report") or ""
    step12 = engine.get_step12_artifacts() or {}
    security_report = step12.get("security_report") or step12.get("report") or ""
    step2 = engine.get_step2_artifacts() or {}
    core_goal = step2.get("confirmed_goal") or step2.get("core_goal") or ""
    engine.save_step14_artifacts({"status": "generating", "message": "📖 后贵正在完善项目文档..."})

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
                    await broadcast(project_id, {"type": "step14", "message": "♻️ 续跑：项目文档已通过检验，跳过"})
                    bg_engine.save_step14_artifacts({**prev, "status": "done", "message": "♻️ 续跑：项目文档已通过"})
                    bg_engine.complete_step(14)
                    await broadcast(project_id, {"type": "done", "message": "✅ 项目文档已完成（续跑）"})
                    return

                max_ver = 0
                for f in glob.glob(os.path.join(docs_dir, f"{slug}_projectdoc_V*.md")):
                    import re as _re
                    m = _re.search(r'V(\d+)', os.path.basename(f))
                    if m:
                        max_ver = max(max_ver, int(m.group(1)))
                convergence_log, final_path, final_content = [], "", ""
                start_round = 1
                if resume and prev:
                    saved_round = prev.get("current_fix_round", 0)
                    saved_convergence = prev.get("convergence", [])
                    if saved_round > 0:
                        start_round = saved_round + 1
                        convergence_log = list(saved_convergence)
                        await broadcast(project_id, {"type": "step14", "message": f"♻️ 续跑：从第{start_round}轮继续"})
                for fix_round in range(start_round, 11):
                    nv = max_ver + fix_round
                    gen_path = os.path.join(docs_dir, f"{slug}_projectdoc_V{nv}.md")
                    await broadcast(project_id, {"type": "step14", "message": f"📖 后贵正在{'修复' if fix_round > 1 else '完善'}项目文档（第{fix_round}轮）..."})
                    feedback = ""
                    if fix_round > 1 and convergence_log:
                        failed = convergence_log[-1].get("failed_details", [])
                        feedback = "需要修正的问题（只修复这些问题，禁止扩大范围）：\n" + "\n".join(f"- {d}" for d in failed if d)
                    prompt = (
                        "你是资深文档管理员后贵（HouGui），负责完善项目文档。\n\n"
                        f"=== 需求文档 ===\n{requirement}\n\n=== 架构设计文档 ===\n{design_doc}\n\n"
                        f"=== 功能代码 ===\n{code}\n\n=== 测试报告 ===\n{str(test_report)}\n\n"
                        f"=== 安全审计报告 ===\n{str(security_report)}\n\n"
                        + (f"=== 上次检验未通过项 ===\n{feedback}\n只针对不合格项修改，不要扩大修改范围。\n\n" if feedback else "")
                        + f"请将完整文档保存到：{gen_path}\n要求：1.部署手册 2.操作手册\n3.API文档 4.用户手册\n5.保证所有文档之间的一致性\n不要输出推理过程。"
                    )
                    client = GatewayClient(profile_name="hougui", timeout=3600)
                    chunks = []
                    async for chunk in client.chat_isolated(messages=[{"role": "user", "content": prompt}], project_id=project_id, project_name=proj_name, project_description=proj_desc, core_goal=core_goal, agent_name="后贵（HouGui）-项目文档", stream=True, max_tokens=64000):
                        if chunk.strip():
                            chunks.append(chunk)
                            await broadcast(project_id, {"type": "step14", "content": chunk})
                    if os.path.exists(gen_path):
                        content = open(gen_path, "r", encoding="utf-8").read()
                    else:
                        content = "".join(chunks).strip()
                        with open(gen_path, "w", encoding="utf-8") as f:
                            f.write(content)
                    if not content.strip():
                        await broadcast(project_id, {"type": "step14", "message": "❌ 后贵未生成有效内容，重试"})
                        continue
                    final_path, final_content = gen_path, content
                    bg_engine.save_step14_artifacts({"documentation": content, "doc_path": gen_path, "status": "generating", "current_fix_round": fix_round, "convergence": convergence_log})
                    await broadcast(project_id, {"type": "step14", "message": f"🔍 hourong 正在检验项目文档（文件：{gen_path}）"})
                    failed_keys = []
                    if fix_round > 1 and convergence_log:
                        last_results = convergence_log[-1].get("results", [])
                        if last_results:
                            failed_keys = [r.get("key", "") for r in last_results if int(r.get("score", 100)) < 90]
                    qa_result = await _inspect_doc(project_id, gen_path, project_name=proj_name, project_description=proj_desc, core_goal=core_goal, failed_keys=failed_keys if failed_keys else None)
                    convergence_log.append({"round": fix_round, "detail": qa_result.get("detail", ""), "passed": qa_result.get("passed", False), "failed_details": qa_result.get("failed_details", []), "results": qa_result.get("results", [])})
                    if qa_result.get("passed"):
                        await broadcast(project_id, {"type": "step14", "message": f"✅ 项目文档已通过 hourong 检验（共{fix_round}轮）"})
                        bg_engine.save_step14_artifacts({"documentation": content, "doc_path": gen_path, "convergence": convergence_log, "status": "done", "qa_passed": True, "message": "✅ 项目文档完善完成"})
                        bg_engine.complete_step(14)
                        await broadcast(project_id, {"type": "done", "message": "✅ 项目文档已完成"})
                        return
                    await broadcast(project_id, {"type": "step14", "message": f"⚠️ 未通过，修复中"})
                await broadcast(project_id, {"type": "error", "message": "❌ 经10轮仍未通过检验"})
                bg_engine.save_step14_artifacts({"documentation": final_content, "doc_path": final_path, "convergence": convergence_log, "status": "error"})
                bg_engine.reset_step(14)
            except Exception as e:
                logger.error(f"Step14: {e}")
                try:
                    bg_engine = WorkflowEngine(project_id=project_id, db=bg_db)
                    bg_engine.save_step14_artifacts({"status": "error", "message": f"失败: {str(e)[:200]}"})
                    bg_engine.reset_step(14)
                except Exception:
                    pass
            finally:
                bg_db.close()
        except Exception as e:
            logger.error(f"Step14 fatal: {e}")
    _asyncio.create_task(_generate())
    return APIResponse(code=0, data={"message": "第十四步已启动", "status": "generating"})


@router.post("/{project_id}/step14/reset")
def reset_step14(project_id: str, db: Session = Depends(get_db), current_user=Depends(get_current_user)):
    engine = _get_engine(project_id, db)
    engine.reset_step(14)
    _wf_engines.pop(project_id, None)
    return APIResponse(code=0, data={"message": "第十四步已重置"})


@router.get("/{project_id}/step14/status")
def get_step14_status(project_id: str, db: Session = Depends(get_db), current_user=Depends(get_current_user)):
    engine = _get_engine(project_id, db)
    return APIResponse(code=0, data=engine.get_step14_artifacts())


@router.post("/{project_id}/step14/artifacts")
def save_step14_artifacts_route(project_id: str, body: dict = Body(...), db: Session = Depends(get_db), current_user=Depends(get_current_user)):
    engine = _get_engine(project_id, db)
    engine.save_step14_artifacts(body)
    return APIResponse(code=0, data={"message": "步骤14状态已保存"})


@router.post("/{project_id}/step14/save-doc")
def save_step14_doc(project_id: str, body: Step3InspectRequest, db: Session = Depends(get_db), current_user=Depends(get_current_user)):
    """保存项目文档到本地和代码库"""
    from datetime import datetime
    from app.services.workflow_engine import WorkflowEngine
    from app.models.repo import Repo
    from app.services.gitea_client import gitea_client
    local_dir = body.save_path or os.path.join(os.getcwd(), "docs", "doc")
    os.makedirs(local_dir, exist_ok=True)
    local_filename = body.filename or f"doc-{datetime.now().strftime('%Y%m%d%H%M%S')}.md"
    local_path = os.path.join(local_dir, local_filename)
    with open(local_path, "w", encoding="utf-8") as f:
        f.write(body.content)
    engine = WorkflowEngine(project_id=project_id, db=db)
    engine.save_step14_artifacts({"documentation": body.content, "filename": local_filename, "local_path": local_path, "saved_at": datetime.now().isoformat()})
    repo = db.query(Repo).filter(Repo.project_id == project_id).first()
    if not repo:
        return APIResponse(code=0, data={"message": "已保存", "local_path": local_path})
    try:
        filepath = f"docs/doc/doc-{datetime.now().strftime('%Y%m%d%H%M%S')}.md"
        result = asyncio.run(gitea_client.create_file(owner=settings.GITEA_ADMIN_USER, repo=repo.name, filepath=filepath, content=body.content, message="Project doc", branch="main"))
        return APIResponse(code=0, data={"message": "已保存", "local_path": local_path, "filepath": filepath})
    except Exception as e:
        return APIResponse(code=0, data={"message": f"本地已保存（Gitea失败）", "local_path": local_path})


@router.post("/{project_id}/step14/list-docs")
def list_step14_docs(project_id: str, body: DocsListRequest, current_user=Depends(get_current_user)):
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


@router.post("/{project_id}/step14/inspect")
async def inspect_step14(project_id: str, body: Step3InspectRequest, db: Session = Depends(get_db), current_user=Depends(get_current_user)):
    from app.services.gateway_client import GatewayClient
    import json as _json
    content, focus_items = body.content, body.focus_items
    if not content or len(content.strip()) < 20:
        return APIResponse(code=0, data={"passed": False, "dimensions": [{"key": d["key"], "passed": False} for d in DOC_INSPECTION_DIMENSIONS]})
    active_dims = [d for d in DOC_INSPECTION_DIMENSIONS if not focus_items or d["key"] in focus_items]
    dims_json = _json.dumps([{'检验项目': d['label'], '检验标准': d['description']} for d in active_dims], ensure_ascii=False, indent=2)
    focus_hint = f"\n⚠️ 本次只检验：{[d['label'] for d in active_dims]}" if focus_items else ""
    convergence_hint = "\n⚠️ 收敛性要求：检验报告必须聚焦于不合格项，明确指出不合格项的问题和修改方向。后续Agent将只修改不合格项，禁止扩大范围。已合格项目不得提出修改要求。"
    scoring_hint = "\n评分规则：每个维度起始100分，每发现一个缺陷扣减相应分数（轻微缺陷扣5-10分，一般缺陷扣15-20分，严重缺陷扣25-30分）。维度得分≥90则该维度passed为true。所有维度平均分>90分为整体合格。"
    prompt = f"你是一个专业的文档QA检验员（后荣）。\n\n=== 项目文档 ===\n{content}\n\n=== 检验项目 ===\n{dims_json}\n{focus_hint}\n{convergence_hint}\n{scoring_hint}\n\n直接输出 JSON 数组：\n[\n" + ",\n".join(f'  {{"key": "{d["key"]}", "score": 100, "deduction": "", "passed": true/false, "detail": "..."}}' for d in active_dims) + "\n]"
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
        return APIResponse(code=0, data={"passed": False, "dimensions": [{"key": d["key"], "passed": False} for d in DOC_INSPECTION_DIMENSIONS]})
    results = []
    for dim in active_dims:
        m = next((r for r in parsed if r.get("key") == dim["key"]), None)
        results.append({"key": dim["key"], "label": dim["label"], "score": int(m.get("score", 100)) if m else 0, "passed": int(m.get("score", 100)) >= 90 if m else False, "detail": m.get("detail", "") if m else ""})
    avg_score = sum(r.get("score", 0) for r in results) / len(results) if results else 0
    all_passed = avg_score > 90
    _engine = _get_engine(project_id, db)
    _engine.save_step14_artifacts({
        "inspect_result": {"passed": all_passed, "avg_score": avg_score, "dimensions": results, "inspected_at": __import__('datetime').datetime.now(__import__('datetime').timezone.utc).isoformat()},
        "qa_passed": all_passed, "qa_checked": True,
    })
    return APIResponse(code=0, data={"passed": avg_score > 90, "score": avg_score, "dimensions": results})


@router.post("/{project_id}/step14/qa")
def qa_step14(project_id: str, body: QAResultRequest, db: Session = Depends(get_db), current_user=Depends(get_current_user)):
    from datetime import datetime, timezone
    engine = _get_engine(project_id, db)
    now_iso = datetime.now(timezone.utc).isoformat()
    if body.result == "passed":
        result = engine.pass_qa(14)
        engine.save_step14_artifacts({"qa_passed": True, "qa_status": "passed", "qa_checked_at": now_iso})
    else:
        result = engine.fail_qa(14, reason=body.reason or "", suggestions=body.suggestions)
        engine.save_step14_artifacts({"qa_passed": False, "qa_status": "failed", "qa_checked_at": now_iso, "qa_fail_reason": body.reason, "qa_suggestions": body.suggestions})
    return APIResponse(code=0, data={"message": f"第十四步QA{'通过' if body.result == 'passed' else '未通过'}", "qa": result})
