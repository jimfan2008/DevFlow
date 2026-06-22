from app.api.workflow.core import (
    router, _get_engine, logger, APIResponse, Depends, get_db,
    get_current_user, Session, Body, Request, HTTPException,
    BaseModel, Optional, asyncio, os, settings, Step3InspectRequest, QAResultRequest,
    DocsListRequest, TDD_PLAN_DIMENSIONS, TDD_TESTCASE_DIMENSIONS,
    _wf_engines, WorkflowEngine,
)

# ── hourong 检验 + 收敛修复 ──

async def _inspect_tdd_plan(
    project_id: str, doc_path: str,
    project_name: str = "", project_description: str = "",
    core_goal: str = "", agent_label: str = "",
    max_retries: int = 3,
) -> dict:
    import json as _json, asyncio as _asyncio
    from app.services.gateway_client import GatewayClient
    from app.api.ws.step4_progress import broadcast

    dims_json = str([{'检验项目': d['label'], '检验标准': d['description'], '检验维': d['key']} for d in TDD_PLAN_DIMENSIONS])

    for attempt in range(1, max_retries + 1):
        if attempt > 1:
            await _asyncio.sleep(2)
            await broadcast(project_id, {"type": "step6", "message": f"🔄 hourong 正在第{attempt}次重新检验TDD计划..."})

        insp_prompt = (
            "你是一个专业的测试计划QA检验员（后荣）。请严格检验以下TDD测试用例编写计划。\n\n"
            "=== 检验项目与标准 ===\n"
            f"{dims_json}\n\n"
            "=== 文档路径 ===\n"
            f"{doc_path}\n\n"
            "请读取该文档文件，严格逐项检验。\n只输出 JSON 数组，不要有其他文字:\n"
            + ",\n".join(f'  {{"key": "{d["key"]}", "passed": true/false, "detail": "具体检验意见..."}}' for d in TDD_PLAN_DIMENSIONS) + "\n"
        )
        qa_cli = GatewayClient(profile_name="hourong", timeout=180)
        qa_chunks = []
        async for chunk in qa_cli.chat_isolated(
            messages=[{"role": "user", "content": insp_prompt}],
            project_id=project_id, project_name=project_name, project_description=project_description,
            core_goal=core_goal, agent_name=agent_label or "后荣-TDD计划QA检验员",
            stream=True, max_tokens=8192,
        ):
            qa_chunks.append(chunk)
        qa_r = "".join(qa_chunks).strip()

        if not qa_r:
            if attempt < max_retries:
                await broadcast(project_id, {"type": "step6", "message": f"⚠️ hourong 未返回检验结果，重试（第{attempt}次）"})
                continue
            return {"detail": f"后荣{max_retries}次均未返回检验结果"}

        brace_s, brace_e = qa_r.find('['), qa_r.rfind(']') + 1
        if brace_s != -1 and brace_e > brace_s:
            qa_r = qa_r[brace_s:brace_e]
        try:
            parsed = _json.loads(qa_r)
        except Exception:
            if attempt < max_retries:
                await broadcast(project_id, {"type": "step6", "message": f"⚠️ hourong 返回无法解析的报告，重试（第{attempt}次）"})
                continue
            return {"detail": "后荣未返回检验结果"}

        if isinstance(parsed, list) and parsed:
            all_passed = all(bool(r.get("passed")) for r in parsed)
            return {"passed": all_passed, "detail": "", "failed_details": [r.get("detail", "") for r in parsed if not r.get("passed")], "results": parsed}
        if attempt < max_retries:
            await broadcast(project_id, {"type": "step6", "message": f"⚠️ hourong 返回格式异常，重试（第{attempt}次）"})
            continue
        return {"detail": "后荣未返回检验结果"}
    return {"detail": "后荣检验失败"}


@router.post("/{project_id}/step6/execute")
async def execute_step6_async(project_id: str,
                              db: Session = Depends(get_db),
                              current_user=Depends(get_current_user),
                              resume: bool = False):
    """异步启动第六步：海梅制订TDD测试用例编写计划，hourong 自动检验+收敛修复"""
    from app.services.workflow_engine import WorkflowEngine
    import asyncio as _asyncio

    try:
        engine = _get_engine(project_id, db)
        if resume:
            existing = engine.get_step6_artifacts() or {}
        else:
            step6_row = engine._get_step_row(6)
            if step6_row and step6_row.status == "in_progress":
                engine.reset_step(6)
                engine = WorkflowEngine(project_id=project_id, db=db)
                _wf_engines[project_id] = engine
            engine.advance_step(6)
            existing = {}
    except Exception as e:
        return APIResponse(code=1, message=f"无法开始步骤6: {str(e)[:200]}")

    step3 = engine.get_step3_artifacts() or {}
    requirement = (step3.get("doc_content") or step3.get("content") or step3.get("requirement") or step3.get("srs") or "")
    step4 = engine.get_step4_artifacts() or {}
    design_doc = step4.get("design_doc") or ""
    step5 = engine.get_step5_artifacts() or {}
    env_info = step5.get("env_info") or step5.get("environment") or ""
    step2 = engine.get_step2_artifacts() or {}
    core_goal = step2.get("confirmed_goal") or step2.get("core_goal") or ""

    engine.save_step6_artifacts({"status": "generating", "message": "📋 海梅正在制订TDD测试用例编写计划..."})

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

                # 续跑
                prev_artifacts = existing if resume else {}
                if resume and prev_artifacts.get("qa_passed") and os.path.exists(prev_artifacts.get("doc_path", "")):
                    await broadcast(project_id, {"type": "step6", "message": "♻️ 续跑：TDD计划已通过检验，跳过"})
                    bg_engine.save_step6_artifacts({**prev_artifacts, "status": "done", "message": "♻️ 续跑：TDD计划已通过"})
                    bg_engine.complete_step(6)
                    await broadcast(project_id, {"type": "done", "message": "✅ TDD计划已生成（续跑）"})
                    return

                max_ver = 0
                for f in glob.glob(os.path.join(docs_dir, f"{slug}_tddplan_V*.md")):
                    import re as _re
                    m = _re.search(r'V(\d+)', os.path.basename(f))
                    if m: max_ver = max(max_ver, int(m.group(1)))

                convergence_log, final_path, final_content = [], "", ""
                for fix_round in range(1, 11):
                    nv = max_ver + fix_round
                    gen_path = os.path.join(docs_dir, f"{slug}_tddplan_V{nv}.md")
                    await broadcast(project_id, {"type": "step6", "message": f"📋 海梅正在{'修复' if fix_round > 1 else '制订'}TDD计划（第{fix_round}轮）..."})

                    feedback = ""
                    if fix_round > 1 and convergence_log:
                        last = convergence_log[-1]
                        failed = last.get("failed_details", [])
                        feedback = "需要修正的问题（只修复这些问题，禁止扩大范围）：\n" + "\n".join(f"- {d}" for d in failed if d)

                    prompt_lines = [
                        "你是资深项目经理海梅（HaiMei），负责制订TDD测试用例编写计划。\n",
                        f"=== 需求文档（SRS）===\n{requirement}\n\n",
                        f"=== 架构设计文档 ===\n{design_doc}\n\n",
                    ]
                    if env_info:
                        prompt_lines.append(f"=== 开发环境信息 ===\n{env_info[:500]}\n\n")
                    if feedback:
                        prompt_lines.append(f"=== 上次检验未通过项 ===\n{feedback}\n请只针对不合格项修改，不要扩大修改范围。\n\n")
                    prompt_lines.append(
                        f"请将完整计划保存到：{gen_path}\n"
                        "要求：1.每个测试用例最小原子化 2.每个测试用例有明确可量化验收标准\n"
                        "3.覆盖所有功能和非功能需求 4.标注优先级和执行顺序\n不要输出推理过程。"
                    )
                    prompt = "\n".join(prompt_lines)

                    client = GatewayClient(profile_name="haimei", timeout=3600)
                    chunks = []
                    async for chunk in client.chat_isolated(
                        messages=[{"role": "user", "content": prompt}],
                        project_id=project_id, project_name=proj_name, project_description=proj_desc,
                        core_goal=core_goal, agent_name="海梅（HaiMei）-TDD计划制订",
                        stream=True, max_tokens=64000,
                    ):
                        if chunk.strip():
                            chunks.append(chunk)
                            await broadcast(project_id, {"type": "step6", "content": chunk})

                    if os.path.exists(gen_path):
                        with open(gen_path, "r", encoding="utf-8") as f:
                            content = f.read()
                    else:
                        content = "".join(chunks).strip()
                        with open(gen_path, "w", encoding="utf-8") as f:
                            f.write(content)

                    if not content.strip():
                        await broadcast(project_id, {"type": "step6", "message": "❌ 海梅未生成有效内容，重试"})
                        continue
                    final_path, final_content = gen_path, content
                    bg_engine.save_step6_artifacts({"tdd_plan": content, "doc_path": gen_path, "status": "generating"})

                    await broadcast(project_id, {"type": "step6", "message": f"🔍 hourong 正在检验TDD计划（文件：{gen_path}）"})
                    qa_result = await _inspect_tdd_plan(project_id, gen_path, project_name=proj_name, project_description=proj_desc, core_goal=core_goal)
                    convergence_log.append({"round": fix_round, "detail": qa_result.get("detail", ""), "passed": qa_result.get("passed", False), "failed_details": qa_result.get("failed_details", [])})

                    if qa_result.get("passed"):
                        await broadcast(project_id, {"type": "step6", "message": f"✅ TDD计划已通过 hourong 检验（共{fix_round}轮）"})
                        bg_engine.save_step6_artifacts({"tdd_plan": content, "doc_path": gen_path, "convergence": convergence_log, "status": "done", "qa_passed": True, "message": "✅ TDD计划制订完成"})
                        bg_engine.complete_step(6)
                        await broadcast(project_id, {"type": "done", "message": "✅ TDD计划已生成"})
                        return

                    await broadcast(project_id, {"type": "step6", "message": f"⚠️ 未通过：{'；'.join(str(d) for d in qa_result.get('failed_details', ['未知']))[:80]}，修复中"})

                await broadcast(project_id, {"type": "error", "message": "❌ 经10轮仍未通过检验"})
                bg_engine.save_step6_artifacts({"tdd_plan": final_content, "doc_path": final_path, "convergence": convergence_log, "status": "error"})
                bg_engine.reset_step(6)

            except Exception as e:
                logger.error(f"Step6 failed: {e}")
                try:
                    bg_engine = WorkflowEngine(project_id=project_id, db=bg_db)
                    bg_engine.save_step6_artifacts({"status": "error", "message": f"失败: {str(e)[:200]}"})
                    bg_engine.reset_step(6)
                except Exception:
                    pass
            finally:
                bg_db.close()
        except Exception as e:
            logger.error(f"Step6 fatal: {e}")

    _asyncio.create_task(_generate())
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
    prompt = f"你是一个专业的测试计划QA检验员（后荣）。请严格检验以下TDD测试用例编写计划。\n\n=== TDD计划 ===\n{content}\n\n=== 检验项目与标准 ===\n{dims_json}\n{focus_hint}\n\n直接输出 JSON 数组：\n[\n" + ",\n".join(f'  {{"key": "{d["key"]}", "passed": true/false, "detail": "..."}}' for d in active_dims) + "\n]"
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