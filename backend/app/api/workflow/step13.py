import glob
from app.api.workflow.core import (
    router, _get_engine, logger, APIResponse, Depends, get_db,
    get_current_user, Session, Body, Request, HTTPException,
    BaseModel, Optional, asyncio, os, settings, Step3InspectRequest,
    DEPLOY_PROD_DIMENSIONS, Step13ChatRequest, _wf_engines, WorkflowEngine,
)


@router.post("/{project_id}/step13/chat")
async def step13_chat(project_id: str, body: Step13ChatRequest,
                      db: Session = Depends(get_db), current_user=Depends(get_current_user)):
    """后富（HouFu）对话 - 项目隔离"""
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
        client = GatewayClient(profile_name="houfu", timeout=1200)
        reply_chunks = []
        async for chunk in client.chat_isolated(messages=messages, project_id=project_id, project_name=project.name, project_description=project.description or "", core_goal=core_goal, agent_name="后富（HouFu）CI/CD工程师", stream=False):
            reply_chunks.append(chunk)
        reply = "".join(reply_chunks)
        if not reply or len(reply.strip()) < 5:
            return APIResponse(code=1, message="后富未生成有效回复", data=None)
        return APIResponse(code=0, message="success", data={"reply": reply})
    except HTTPException:
        raise
    except Exception as e:
        logger.error(f"Step13 chat: {e}")
        return APIResponse(code=1, message="与后富对话失败", data=None)


async def _inspect_deploy_prod(project_id: str, doc_path: str, project_name: str = "", project_description: str = "", core_goal: str = "", agent_label: str = "", max_retries: int = 3) -> dict:
    import json as _json, asyncio as _asyncio
    from app.services.gateway_client import GatewayClient
    from app.api.ws.step4_progress import broadcast
    dims_json = str([{'检验项目': d['label'], '检验标准': d['description'], '检验维': d['key']} for d in DEPLOY_PROD_DIMENSIONS])
    for attempt in range(1, max_retries + 1):
        if attempt > 1:
            await _asyncio.sleep(2)
            await broadcast(project_id, {"type": "step13", "message": f"🔄 hourong 第{attempt}次重新检验生产部署..."})
        insp_prompt = f"你是一个专业的部署QA检验员（后荣）。请严格检验以下生产环境部署报告。\n\n=== 检验项目与标准 ===\n{dims_json}\n\n=== 文档路径 ===\n{doc_path}\n\n请读取该文档文件，严格逐项检验。\n⚠️ 收敛性要求：检验报告必须聚焦于不合格项，明确指出不合格项的问题和修改方向。后续Agent将只修改不合格项，禁止扩大范围。已合格项目不得提出修改要求。\n只输出 JSON 数组:\n" + ",\n".join(f'  {{"key": "{d["key"]}", "passed": true/false, "detail": "具体检验意见..."}}' for d in DEPLOY_PROD_DIMENSIONS)
        qa_cli = GatewayClient(profile_name="hourong", timeout=180)
        qa_chunks = []
        async for chunk in qa_cli.chat_isolated(messages=[{"role": "user", "content": insp_prompt}], project_id=project_id, project_name=project_name, project_description=project_description, core_goal=core_goal, agent_name=agent_label or "后荣-生产部署QA检验员", stream=True, max_tokens=8192):
            qa_chunks.append(chunk)
        qa_r = "".join(qa_chunks).strip()
        if not qa_r:
            if attempt < max_retries:
                await broadcast(project_id, {"type": "step13", "message": f"⚠️ hourong 未返回，重试（第{attempt}次）"})
                continue
            return {"detail": f"后荣{max_retries}次均未返回"}
        brace_s, brace_e = qa_r.find('['), qa_r.rfind(']') + 1
        if brace_s != -1 and brace_e > brace_s:
            qa_r = qa_r[brace_s:brace_e]
        try:
            parsed = _json.loads(qa_r)
        except Exception:
            if attempt < max_retries:
                await broadcast(project_id, {"type": "step13", "message": f"⚠️ hourong 格式异常，重试（第{attempt}次）"})
                continue
            return {"detail": "后荣未返回检验结果"}
        if isinstance(parsed, list) and parsed:
            return {"passed": all(bool(r.get("passed")) for r in parsed), "detail": "", "failed_details": [r.get("detail", "") for r in parsed if not r.get("passed")], "results": parsed}
        if attempt < max_retries:
            await broadcast(project_id, {"type": "step13", "message": f"⚠️ hourong 格式异常，重试（第{attempt}次）"})
            continue
        return {"detail": "后荣未返回检验结果"}
    return {"detail": "后荣检验失败"}


@router.post("/{project_id}/step13/execute")
async def execute_step13_async(project_id: str, db: Session = Depends(get_db), current_user=Depends(get_current_user), resume: bool = False):
    """异步启动第十三步：后富部署到生产环境，hourong 自动检验+收敛修复"""
    import asyncio as _asyncio
    try:
        engine = _get_engine(project_id, db)
        if resume:
            existing = engine.get_step13_artifacts() or {}
        else:
            step13_row = engine._get_step_row(13)
            if step13_row and step13_row.status == "in_progress":
                engine.reset_step(13)
                engine = WorkflowEngine(project_id=project_id, db=db)
                _wf_engines[project_id] = engine
            engine.advance_step(13)
            existing = {}
    except Exception as e:
        return APIResponse(code=1, message=f"无法开始步骤13: {str(e)[:200]}")
    step9 = engine.get_step9_artifacts() or {}
    code = step9.get("code") or step9.get("content") or ""
    step11 = engine.get_step11_artifacts() or {}
    test_report = step11.get("test_report") or step11.get("report") or ""
    step12 = engine.get_step12_artifacts() or {}
    security_report = step12.get("security_report") or step12.get("report") or ""
    step2 = engine.get_step2_artifacts() or {}
    core_goal = step2.get("confirmed_goal") or step2.get("core_goal") or ""
    engine.save_step13_artifacts({"status": "generating", "message": "🚀 后富正在部署到生产环境..."})

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
                    await broadcast(project_id, {"type": "step13", "message": "♻️ 续跑：生产部署已通过检验，跳过"})
                    bg_engine.save_step13_artifacts({**prev, "status": "done", "message": "♻️ 续跑：生产部署已通过"})
                    bg_engine.complete_step(13)
                    await broadcast(project_id, {"type": "done", "message": "✅ 生产部署已完成（续跑）"})
                    return

                max_ver = 0
                for f in glob.glob(os.path.join(docs_dir, f"{slug}_deployprod_V*.md")):
                    import re as _re
                    m = _re.search(r'V(\d+)', os.path.basename(f))
                    if m:
                        max_ver = max(max_ver, int(m.group(1)))
                convergence_log, final_path, final_content = [], "", ""
                for fix_round in range(1, 11):
                    nv = max_ver + fix_round
                    gen_path = os.path.join(docs_dir, f"{slug}_deployprod_V{nv}.md")
                    await broadcast(project_id, {"type": "step13", "message": f"🚀 后富正在{'修复' if fix_round > 1 else '部署'}生产环境（第{fix_round}轮）..."})
                    feedback = ""
                    if fix_round > 1 and convergence_log:
                        failed = convergence_log[-1].get("failed_details", [])
                        feedback = "需要修正的问题（只修复这些问题，禁止扩大范围）：\n" + "\n".join(f"- {d}" for d in failed if d)
                    prompt = (
                        "你是资深CI/CD工程师后富（HouFu），负责将代码部署到生产环境。\n\n"
                        f"=== 功能代码 ===\n{code}\n\n=== 测试报告 ===\n{str(test_report)}\n\n"
                        f"=== 安全审计报告 ===\n{str(security_report)}\n\n"
                        + (f"=== 上次检验未通过项 ===\n{feedback}\n只针对不合格项修改，不要扩大修改范围。\n\n" if feedback else "")
                        + f"请将部署报告保存到：{gen_path}\n要求：1.准备生产环境 2.零停机部署策略\n3.配置生产环境变量和数据库 4.灰度发布和验证\n5.输出部署日志和回滚方案\n不要输出推理过程。"
                    )
                    client = GatewayClient(profile_name="houfu", timeout=3600)
                    chunks = []
                    async for chunk in client.chat_isolated(messages=[{"role": "user", "content": prompt}], project_id=project_id, project_name=proj_name, project_description=proj_desc, core_goal=core_goal, agent_name="后富（HouFu）-生产环境部署", stream=True, max_tokens=64000):
                        if chunk.strip():
                            chunks.append(chunk)
                            await broadcast(project_id, {"type": "step13", "content": chunk})
                    if os.path.exists(gen_path):
                        content = open(gen_path, "r", encoding="utf-8").read()
                    else:
                        content = "".join(chunks).strip()
                        with open(gen_path, "w", encoding="utf-8") as f:
                            f.write(content)
                    if not content.strip():
                        await broadcast(project_id, {"type": "step13", "message": "❌ 后富未生成有效内容，重试"})
                        continue
                    final_path, final_content = gen_path, content
                    bg_engine.save_step13_artifacts({"deployment_log": content, "doc_path": gen_path, "status": "generating"})
                    await broadcast(project_id, {"type": "step13", "message": f"🔍 hourong 正在检验生产部署（文件：{gen_path}）"})
                    qa_result = await _inspect_deploy_prod(project_id, gen_path, project_name=proj_name, project_description=proj_desc, core_goal=core_goal)
                    convergence_log.append({"round": fix_round, "detail": qa_result.get("detail", ""), "passed": qa_result.get("passed", False), "failed_details": qa_result.get("failed_details", [])})
                    if qa_result.get("passed"):
                        await broadcast(project_id, {"type": "step13", "message": f"✅ 生产部署已通过 hourong 检验（共{fix_round}轮）"})
                        bg_engine.save_step13_artifacts({"deployment_log": content, "doc_path": gen_path, "convergence": convergence_log, "status": "done", "qa_passed": True, "message": "✅ 生产部署完成"})
                        bg_engine.complete_step(13)
                        await broadcast(project_id, {"type": "done", "message": "✅ 生产部署已完成"})
                        return
                    await broadcast(project_id, {"type": "step13", "message": f"⚠️ 未通过，修复中"})
                await broadcast(project_id, {"type": "error", "message": "❌ 经10轮仍未通过检验"})
                bg_engine.save_step13_artifacts({"deployment_log": final_content, "doc_path": final_path, "convergence": convergence_log, "status": "error"})
                bg_engine.reset_step(13)
            except Exception as e:
                logger.error(f"Step13: {e}")
                try:
                    bg_engine = WorkflowEngine(project_id=project_id, db=bg_db)
                    bg_engine.save_step13_artifacts({"status": "error", "message": f"失败: {str(e)[:200]}"})
                    bg_engine.reset_step(13)
                except Exception:
                    pass
            finally:
                bg_db.close()
        except Exception as e:
            logger.error(f"Step13 fatal: {e}")
    _asyncio.create_task(_generate())
    return APIResponse(code=0, data={"message": "第十三步已启动", "status": "generating"})


@router.post("/{project_id}/step13/reset")
def reset_step13(project_id: str, db: Session = Depends(get_db), current_user=Depends(get_current_user)):
    engine = _get_engine(project_id, db)
    engine.reset_step(13)
    _wf_engines.pop(project_id, None)
    return APIResponse(code=0, data={"message": "第十三步已重置"})


@router.get("/{project_id}/step13/status")
def get_step13_status(project_id: str, db: Session = Depends(get_db), current_user=Depends(get_current_user)):
    engine = _get_engine(project_id, db)
    return APIResponse(code=0, data=engine.get_step13_artifacts())


@router.post("/{project_id}/step13/artifacts")
def save_step13_artifacts_route(project_id: str, body: dict = Body(...), db: Session = Depends(get_db), current_user=Depends(get_current_user)):
    engine = _get_engine(project_id, db)
    engine.save_step13_artifacts(body)
    return APIResponse(code=0, data={"message": "步骤13状态已保存"})


@router.post("/{project_id}/step13/inspect")
async def inspect_step13(project_id: str, body: Step3InspectRequest, db: Session = Depends(get_db), current_user=Depends(get_current_user)):
    from app.services.gateway_client import GatewayClient
    import json as _json
    content, focus_items = body.content, body.focus_items
    if not content or len(content.strip()) < 20:
        return APIResponse(code=0, data={"passed": False, "dimensions": [{"key": d["key"], "passed": False} for d in DEPLOY_PROD_DIMENSIONS]})
    active_dims = [d for d in DEPLOY_PROD_DIMENSIONS if not focus_items or d["key"] in focus_items]
    dims_json = _json.dumps([{'检验项目': d['label'], '检验标准': d['description']} for d in active_dims], ensure_ascii=False, indent=2)
    focus_hint = f"\n⚠️ 本次只检验：{[d['label'] for d in active_dims]}" if focus_items else ""
    convergence_hint = "\n⚠️ 收敛性要求：检验报告必须聚焦于不合格项，明确指出不合格项的问题和修改方向。后续Agent将只修改不合格项，禁止扩大范围。已合格项目不得提出修改要求。"
    prompt = f"你是一个专业的部署QA检验员（后荣）。\n\n=== 部署报告 ===\n{content}\n\n=== 检验项目 ===\n{dims_json}\n{focus_hint}\n{convergence_hint}\n\n直接输出 JSON 数组：\n[\n" + ",\n".join(f'  {{"key": "{d["key"]}", "passed": true/false, "detail": "..."}}' for d in active_dims) + "\n]"
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
        return APIResponse(code=0, data={"passed": False, "dimensions": [{"key": d["key"], "passed": False} for d in DEPLOY_PROD_DIMENSIONS]})
    results = []
    for dim in active_dims:
        m = next((r for r in parsed if r.get("key") == dim["key"]), None)
        results.append({"key": dim["key"], "label": dim["label"], "passed": bool(m.get("passed", False)) if m else False, "detail": m.get("detail", "") if m else ""})
    return APIResponse(code=0, data={"passed": all(r["passed"] for r in results), "dimensions": results})
