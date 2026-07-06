import glob
from app.api.workflow.core import (
    router, _get_engine, logger, APIResponse, Depends, get_db,
    get_current_user, Session, Body, Request, HTTPException,
    BaseModel, Optional, asyncio, os, settings, Step3InspectRequest, QAResultRequest,
    CODE_INSPECTION_DIMENSIONS, Step9ChatRequest, _wf_engines, WorkflowEngine,
)


@router.post("/{project_id}/step9/chat")
async def step9_chat(project_id: str, body: Step9ChatRequest, db: Session = Depends(get_db), current_user=Depends(get_current_user)):
    """后发（HouFa）对话"""
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
        client = GatewayClient(profile_name="houfa", timeout=1200)
        rchunks = []
        async for chunk in client.chat_isolated(messages=messages, project_id=project_id, project_name=project.name, project_description=project.description or "", core_goal=core_goal, agent_name="后发（HouFa）程序员", stream=False):
            rchunks.append(chunk)
        reply = "".join(rchunks)
        return APIResponse(code=0, message="success", data={"reply": reply}) if reply and len(reply.strip()) >= 5 else APIResponse(code=1, message="后发未生成有效回复", data=None)
    except HTTPException:
        raise
    except Exception as e:
        logger.error(f"Step9 chat: {e}")
        return APIResponse(code=1, message="与后发对话失败", data=None)


async def _inspect_code(project_id: str, doc_path: str, project_name: str = "", project_description: str = "", core_goal: str = "", agent_label: str = "", max_retries: int = 3, failed_keys: list = None) -> dict:
    import json as _json, asyncio as _asyncio
    from app.services.gateway_client import GatewayClient
    from app.api.ws.step4_progress import broadcast
    active_dims = [d for d in CODE_INSPECTION_DIMENSIONS if not failed_keys or d["key"] in failed_keys]
    dims_json = str([{'检验项目': d['label'], '检验标准': d['description'], '检验维': d['key']} for d in active_dims])
    for attempt in range(1, max_retries + 1):
        if attempt > 1:
            await _asyncio.sleep(2)
            await broadcast(project_id, {"type": "step9", "message": f"🔄 hourong 第{attempt}次检验功能代码..."})
        focus_hint = f"\n⚠️ 本次只需重新检验以下 {len(active_dims)} 项（上一轮不合格项）：{[d['label'] for d in active_dims]}\n请只针对这些项目做出通过/不通过判定，禁止扩大检验范围。" if failed_keys else ""
        insp_prompt = f"你是一个专业的代码QA检验员（后荣）。请严格检验以下功能代码。\n\n=== 检验项目与标准 ===\n{dims_json}\n{focus_hint}\n\n=== 文档路径 ===\n{doc_path}\n\n请读取该文档文件，严格逐项检验。\n⚠️ 收敛性要求：检验报告必须聚焦于不合格项，明确指出不合格项的问题和修改方向。后续Agent将只修改不合格项，禁止扩大范围。已合格项目不得提出修改要求。\n评分规则：每个检验维起始100分，每发现一个缺陷扣减相应分数（轻微缺陷扣5-10分，一般缺陷扣15-20分，严重缺陷扣25-30分）。维度得分≥90则该维度passed为true。所有维度平均分>90分为整体合格。\n只输出 JSON 数组:\n" + ",\n".join(f'  {{"key": "{d["key"]}", "score": 100, "deduction": "", "passed": true/false, "detail": "具体检验意见..."}}' for d in active_dims)
        qa_cli = GatewayClient(profile_name="hourong", timeout=180)
        qa_chunks = []
        async for chunk in qa_cli.chat_isolated(messages=[{"role": "user", "content": insp_prompt}], project_id=project_id, project_name=project_name, project_description=project_description, core_goal=core_goal, agent_name=agent_label or "后荣-代码QA检验员", stream=True, max_tokens=8192):
            qa_chunks.append(chunk)
        qa_r = "".join(qa_chunks).strip()
        if not qa_r:
            if attempt < max_retries:
                await broadcast(project_id, {"type": "step9", "message": f"⚠️ 未返回，重试（第{attempt}次）"})
                continue
            return {"detail": f"后荣{max_retries}次均未返回"}
        brace_s, brace_e = qa_r.find('['), qa_r.rfind(']') + 1
        if brace_s != -1 and brace_e > brace_s:
            qa_r = qa_r[brace_s:brace_e]
        try:
            parsed = _json.loads(qa_r)
        except Exception:
            if attempt < max_retries:
                await broadcast(project_id, {"type": "step9", "message": f"⚠️ 格式异常，重试（第{attempt}次）"})
                continue
            return {"detail": "后荣未返回检验结果"}
        if isinstance(parsed, list) and parsed:
            scores = [int(r.get("score", 100)) for r in parsed]
            avg_score = sum(scores) / len(scores)
            return {"passed": avg_score > 90, "score": avg_score, "total_score": sum(scores), "max_score": len(scores) * 100, "detail": "", "failed_details": [r.get("detail", "") for r in parsed if int(r.get("score", 100)) < 90], "results": parsed}
        if attempt < max_retries:
            await broadcast(project_id, {"type": "step9", "message": f"⚠️ 格式异常，重试（第{attempt}次）"})
            continue
        return {"detail": "后荣未返回检验结果"}
    return {"detail": "后荣检验失败"}


@router.post("/{project_id}/step9/execute")
async def execute_step9_async(project_id: str, db: Session = Depends(get_db), current_user=Depends(get_current_user), resume: bool = False):
    """建立Agent蜂群编写功能代码，hourong 自动检验+收敛修复"""
    import asyncio as _asyncio
    try:
        engine = _get_engine(project_id, db)
        if resume:
            existing = engine.get_step9_artifacts() or {}
        else:
            row = engine._get_step_row(9)
            if row and row.status == "in_progress":
                engine.reset_step(9)
                engine = WorkflowEngine(project_id=project_id, db=db)
                _wf_engines[project_id] = engine
            engine.advance_step(9)
            existing = {}
    except Exception as e:
        return APIResponse(code=1, message=f"无法开始步骤9: {str(e)[:200]}")
    step3 = engine.get_step3_artifacts() or {}
    requirement = (step3.get("doc_content") or step3.get("content") or step3.get("requirement") or step3.get("srs") or "")
    step4 = engine.get_step4_artifacts() or {}
    design_doc = step4.get("design_doc") or ""
    step6 = engine.get_step6_artifacts() or {}
    step7 = engine.get_step7_artifacts() or {}
    tdd_cases = step7.get("tdd_cases") or step7.get("test_cases") or step7.get("content") or ""
    step8 = engine.get_step8_artifacts() or {}
    code_plan = step8.get("code_plan") or step8.get("plan_content") or ""
    dep_graph = step8.get("dependency_graph") or {}
    step2 = engine.get_step2_artifacts() or {}
    core_goal = step2.get("confirmed_goal") or step2.get("core_goal") or ""
    engine.save_step9_artifacts({"status": "generating", "message": "💻 后发正在建立蜂群编写功能代码..."})

    async def _generate():
        try:
            from app.database import SessionLocal
            from app.models.project import Project
            from app.api.ws.step4_progress import broadcast
            import json as _json
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
                    await broadcast(project_id, {"type": "step9", "message": "♻️ 续跑：功能代码已通过，跳过"})
                    bg_engine.save_step9_artifacts({**prev, "status": "done", "message": "♻️ 续跑：功能代码已通过"})
                    bg_engine.complete_step(9)
                    await broadcast(project_id, {"type": "done", "message": "✅ 功能代码已生成（续跑）"})
                    return
                max_ver = 0
                for f in glob.glob(os.path.join(docs_dir, f"{slug}_code_V*.md")):
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
                        await broadcast(project_id, {"type": "step9", "message": f"♻️ 续跑：从第{start_round}轮继续"})
                for fix_round in range(start_round, 11):
                    nv = max_ver + fix_round
                    gen_path = os.path.join(docs_dir, f"{slug}_code_V{nv}.md")
                    await broadcast(project_id, {"type": "step9", "message": f"💻 后发正在{'修复' if fix_round > 1 else '编写'}功能代码（第{fix_round}轮）..."})
                    feedback = ""
                    if fix_round > 1 and convergence_log:
                        failed = convergence_log[-1].get("failed_details", [])
                        feedback = "需要修正的问题（只修复这些问题，禁止扩大范围）：\n" + "\n".join(f"- {d}" for d in failed if d)
                    dep_str = _json.dumps(dep_graph, ensure_ascii=False) if isinstance(dep_graph, dict) else str(dep_graph)
                    prompt = (
                        "你是资深程序员后发（HouFa），负责建立Agent蜂群编写功能代码。\n\n"
                        f"=== 需求文档 ===\n{requirement}\n\n=== 架构设计文档 ===\n{design_doc}\n\n"
                        f"=== 代码编写计划 ===\n{str(code_plan)}\n\n=== 任务依赖图 ===\n{str(dep_str)}\n\n"
                        f"=== TDD测试用例 ===\n{tdd_cases}\n\n"
                        + (f"=== 上次检验未通过项 ===\n{feedback}\n只针对不合格项修改，不要扩大修改范围。\n\n" if feedback else "")
                        + f"请将完整代码保存到：{gen_path}\n要求：1.按依赖图拓扑顺序 2.先写TDD测试再写实现\n3.符合架构设计的技术选型 4.每个函数/类有清晰注释\n5.直接输出代码文件内容，标注文件路径\n不要输出推理过程。"
                    )
                    client = GatewayClient(profile_name="houfa", timeout=10800)
                    chunks = []
                    async for chunk in client.chat_isolated(messages=[{"role": "user", "content": prompt}], project_id=project_id, project_name=proj_name, project_description=proj_desc, core_goal=core_goal, agent_name="后发（HouFa）-功能代码编写", stream=True, max_tokens=64000):
                        if chunk.strip():
                            chunks.append(chunk)
                            await broadcast(project_id, {"type": "step9", "content": chunk})
                    if os.path.exists(gen_path):
                        content = open(gen_path, "r", encoding="utf-8").read()
                    else:
                        content = "".join(chunks).strip()
                        with open(gen_path, "w", encoding="utf-8") as f:
                            f.write(content)
                    if not content.strip():
                        await broadcast(project_id, {"type": "step9", "message": "❌ 后发未生成有效内容，重试"})
                        continue
                    final_path, final_content = gen_path, content
                    bg_engine.save_step9_artifacts({"code": content, "doc_path": gen_path, "status": "generating", "current_fix_round": fix_round, "convergence": convergence_log})
                    await broadcast(project_id, {"type": "step9", "message": f"🔍 hourong 正在检验功能代码（文件：{gen_path}）"})
                    failed_keys = []
                    if fix_round > 1 and convergence_log:
                        last_results = convergence_log[-1].get("results", [])
                        if last_results:
                            failed_keys = [r.get("key", "") for r in last_results if int(r.get("score", 100)) < 90]
                    qa_result = await _inspect_code(project_id, gen_path, project_name=proj_name, project_description=proj_desc, core_goal=core_goal, failed_keys=failed_keys if failed_keys else None)
                    convergence_log.append({"round": fix_round, "detail": qa_result.get("detail", ""), "passed": qa_result.get("passed", False), "failed_details": qa_result.get("failed_details", []), "results": qa_result.get("results", [])})
                    if qa_result.get("passed"):
                        await broadcast(project_id, {"type": "step9", "message": f"✅ 功能代码已通过 hourong 检验（共{fix_round}轮）"})
                        bg_engine.save_step9_artifacts({"code": content, "doc_path": gen_path, "convergence": convergence_log, "status": "done", "qa_passed": True, "message": "✅ 功能代码编写完成"})
                        bg_engine.complete_step(9)
                        await broadcast(project_id, {"type": "done", "message": "✅ 功能代码已生成"})
                        return
                    await broadcast(project_id, {"type": "step9", "message": f"⚠️ 未通过，修复中"})
                await broadcast(project_id, {"type": "error", "message": "❌ 经10轮仍未通过检验"})
                bg_engine.save_step9_artifacts({"code": final_content, "doc_path": final_path, "convergence": convergence_log, "status": "error"})
                bg_engine.reset_step(9)
            except Exception as e:
                logger.error(f"Step9: {e}")
                try:
                    bg_engine = WorkflowEngine(project_id=project_id, db=bg_db)
                    bg_engine.save_step9_artifacts({"status": "error", "message": f"失败: {str(e)[:200]}"})
                    bg_engine.reset_step(9)
                except Exception:
                    pass
            finally:
                bg_db.close()
        except Exception as e:
            logger.error(f"Step9 fatal: {e}")
    _asyncio.create_task(_generate())
    return APIResponse(code=0, data={"message": "第九步已启动", "status": "generating"})


@router.post("/{project_id}/step9/reset")
def reset_step9(project_id: str, db: Session = Depends(get_db), current_user=Depends(get_current_user)):
    engine = _get_engine(project_id, db)
    engine.reset_step(9)
    _wf_engines.pop(project_id, None)
    return APIResponse(code=0, data={"message": "第九步已重置"})


@router.get("/{project_id}/step9/status")
def get_step9_status(project_id: str, db: Session = Depends(get_db), current_user=Depends(get_current_user)):
    engine = _get_engine(project_id, db)
    return APIResponse(code=0, data=engine.get_step9_artifacts())


@router.post("/{project_id}/step9/artifacts")
def save_step9_artifacts_route(project_id: str, body: dict = Body(...), db: Session = Depends(get_db), current_user=Depends(get_current_user)):
    engine = _get_engine(project_id, db)
    engine.save_step9_artifacts(body)
    return APIResponse(code=0, data={"message": "步骤9状态已保存"})


@router.post("/{project_id}/step9/inspect")
async def inspect_step9(project_id: str, body: Step3InspectRequest, db: Session = Depends(get_db), current_user=Depends(get_current_user)):
    from app.services.gateway_client import GatewayClient
    import json as _json
    content, focus_items = body.content, body.focus_items
    if not content or len(content.strip()) < 20:
        return APIResponse(code=0, data={"passed": False, "dimensions": [{"key": d["key"], "passed": False} for d in CODE_INSPECTION_DIMENSIONS]})
    active_dims = [d for d in CODE_INSPECTION_DIMENSIONS if not focus_items or d["key"] in focus_items]
    dims_json = _json.dumps([{'检验项目': d['label'], '检验标准': d['description']} for d in active_dims], ensure_ascii=False, indent=2)
    focus_hint = f"\n⚠️ 本次只检验：{[d['label'] for d in active_dims]}" if focus_items else ""
    convergence_hint = "\n⚠️ 收敛性要求：检验报告必须聚焦于不合格项，明确指出不合格项的问题和修改方向。后续Agent将只修改不合格项，禁止扩大范围。已合格项目不得提出修改要求。"
    scoring_hint = "\n评分规则：每个维度起始100分，每发现一个缺陷扣减相应分数（轻微缺陷扣5-10分，一般缺陷扣15-20分，严重缺陷扣25-30分）。维度得分≥90则该维度passed为true。所有维度平均分>90分为整体合格。"
    prompt = f"你是一个专业的代码QA检验员（后荣）。\n\n=== 功能代码 ===\n{content}\n\n=== 检验项目 ===\n{dims_json}\n{focus_hint}\n{convergence_hint}\n{scoring_hint}\n\n直接输出 JSON 数组：\n[\n" + ",\n".join(f'  {{"key": "{d["key"]}", "score": 100, "deduction": "", "passed": true/false, "detail": "..."}}' for d in active_dims) + "\n]"
    try:
        client = GatewayClient(profile_name="hourong", timeout=120)
        chunks = []
        async for chunk in client.chat_completions(messages=[{"role": "user", "content": prompt}], stream=False, max_tokens=2000):
            chunks.append(chunk)
        reply = "".join(chunks).strip()
        if not reply:
            raise ValueError("未返回")
        parsed = _json.loads(reply)
        if not isinstance(parsed, list):
            raise ValueError("不是数组")
    except Exception:
        return APIResponse(code=0, data={"passed": False, "dimensions": [{"key": d["key"], "passed": False} for d in active_dims]})
    results = []
    for dim in active_dims:
        m = next((r for r in parsed if r.get("key") == dim["key"]), None)
        results.append({"key": dim["key"], "label": dim["label"], "score": int(m.get("score", 100)) if m else 0, "passed": int(m.get("score", 100)) >= 90 if m else False, "detail": m.get("detail", "") if m else ""})
    avg_score = sum(r.get("score", 0) for r in results) / len(results) if results else 0
    all_passed = avg_score > 90
    _engine = _get_engine(project_id, db)
    _engine.save_step9_artifacts({
        "inspect_result": {"passed": all_passed, "avg_score": avg_score, "dimensions": results, "inspected_at": __import__('datetime').datetime.now(__import__('datetime').timezone.utc).isoformat()},
        "qa_passed": all_passed, "qa_checked": True,
    })
    return APIResponse(code=0, data={"passed": avg_score > 90, "score": avg_score, "dimensions": results})


@router.post("/{project_id}/step9/qa")
def qa_step9(project_id: str, body: QAResultRequest, db: Session = Depends(get_db), current_user=Depends(get_current_user)):
    from datetime import datetime, timezone
    engine = _get_engine(project_id, db)
    now_iso = datetime.now(timezone.utc).isoformat()
    if body.result == "passed":
        result = engine.pass_qa(9)
        engine.save_step9_artifacts({"qa_passed": True, "qa_status": "passed", "qa_checked_at": now_iso})
    else:
        result = engine.fail_qa(9, reason=body.reason or "", suggestions=body.suggestions)
        engine.save_step9_artifacts({"qa_passed": False, "qa_status": "failed", "qa_checked_at": now_iso, "qa_fail_reason": body.reason, "qa_suggestions": body.suggestions})
    return APIResponse(code=0, data={"message": f"第九步QA{'通过' if body.result == 'passed' else '未通过'}", "qa": result})