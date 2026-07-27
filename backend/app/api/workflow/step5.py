from app.api.workflow.core import (
    router, _get_engine, logger, APIResponse, Depends, get_db,
    get_current_user, Session, Body, Request, HTTPException,
    BaseModel, Optional, asyncio, os, settings, Step5ChatRequest,
    DocsListRequest, Step3InspectRequest, QAResultRequest,
    ENV_SETUP_DIMENSIONS,
)
import glob


@router.post("/{project_id}/step5/chat")
async def step5_chat(project_id: str, body: Step5ChatRequest,
                     db: Session = Depends(get_db),
                     current_user=Depends(get_current_user)):
    """与后富（HouFu）CI/CD工程师对话 - 使用项目隔离模式"""
    logger.info(f"Step5 chat: project_id={project_id}, message={body.message[:50]}")
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
        async for chunk in client.chat_isolated(
            messages=messages, project_id=project_id, project_name=project.name,
            project_description=project.description or "", core_goal=core_goal,
            agent_name="后富（HouFu）CI/CD工程师", stream=False,
        ):
            reply_chunks.append(chunk)
        reply = "".join(reply_chunks)
        if not reply or len(reply.strip()) < 5:
            return APIResponse(code=1, message="后富未生成有效回复", data=None)
        return APIResponse(code=0, message="success", data={"reply": reply})
    except HTTPException:
        raise
    except Exception as e:
        logger.error(f"HouFu chat failed: {e}")
        return APIResponse(code=1, message="与后富对话失败，请稍后重试", data=None)


# ── hourong 检验 ──

async def _inspect_env_doc(
    project_id: str, doc_path: str,
    project_name: str = "", project_description: str = "",
    core_goal: str = "", agent_label: str = "", max_retries: int = 3,
    focus_items: Optional[list[str]] = None,
) -> dict:
    import json as _json, re as _re, asyncio as _asyncio
    from app.services.gateway_client import GatewayClient
    from app.api.ws.step4_progress import broadcast
    active_dims = [d for d in ENV_SETUP_DIMENSIONS if not focus_items or d["key"] in focus_items]
    if not active_dims:
        return {"passed": True, "detail": "无待检验项", "failed_details": [], "failed_keys": [], "results": []}
    dims_json = str([{'检验项目': d['label'], '检验标准': d['description'], '检验维': d['key']} for d in active_dims])
    dim_keys = [d["key"] for d in active_dims]
    dim_template = ",\n".join(f'  {{"key": "{d["key"]}", "passed": true/false, "detail": "具体检验意见..."}}' for d in active_dims)
    for attempt in range(1, max_retries + 1):
        if attempt > 1:
            await _asyncio.sleep(2)
            await broadcast(project_id, {"type": "step5", "message": f"🔄 hourong 第{attempt}次重新检验开发环境配置..."})
        retry_pressure = ""
        if attempt > 1:
            retry_pressure = (
                f"\n\n⚠️ 你上一次输出包含了无法解析的内容。"
                f"你必须输出一个合法的 JSON 数组，不能再包含其他文字、推理、分析、"
                f"文件内容、工具调用结果或任何解释性说明！\n"
            )
        insp_prompt = (
            f"You are a JSON-only API. Your entire response MUST be a single, "
            f"valid JSON array — nothing else.\n\n"
            f"Role: 专业的环境配置 QA 检验员（后荣）\n\n"
            f"=== 检验项目与标准 ===\n{dims_json}\n\n"
            f"=== 文档路径 ===\n{doc_path}\n\n"
            f"Task: 读取该文档文件，严格逐项检验是否满足上述标准。\n"
            f"注意：文档文件位于上述路径，请直接读取文件进行完整检验。\n\n"
            f"=== OUTPUT FORMAT (STRICT) ===\n"
            f"Output ONLY a JSON array with exactly {len(ENV_SETUP_DIMENSIONS)} objects. "
            f"Each object has 3 fields:\n"
            f"  key: string (must be one of: {', '.join(dim_keys)})\n"
            f"  passed: boolean (true or false)\n"
            f"  detail: string (your inspection comments)\n\n"
            f"Template:\n[\n"
            f"{dim_template}\n]\n\n"
            f"CRITICAL RULES:\n"
            f"1. The JSON array must be the ONLY content in your response.\n"
            f"2. Do NOT include any text before or after the JSON array.\n"
            f"3. Do NOT use markdown code fences (```json ... ```).\n"
            f"4. Do NOT include thinking, reasoning, analysis, or explanation.\n"
            f"5. Do NOT include file content, tool calls, or tool results.\n"
            f"6. Do NOT include greetings, apologies, or any conversational text.\n"
            f"7. The array must contain exactly {len(active_dims)} objects, one per dimension.\n"
            f"8. Ensure all string values use double quotes and are properly escaped.\n"
            f"9. The JSON must parse successfully without any modifications.\n"
            f"10. After generating the JSON, verify it is valid before outputting.\n"
            f"{retry_pressure}"
            f"{'⚠️ 本轮只检验以下项目（上一轮未通过）：' + str([d['label'] for d in active_dims]) if focus_items else ''}\n"
            f"Now output the JSON array:"
        )
        qa_cli = GatewayClient(profile_name="hourong", timeout=180)
        qa_chunks = []
        async for chunk in qa_cli.chat_isolated(
            messages=[{"role": "user", "content": insp_prompt}],
            project_id=project_id, project_name=project_name, project_description=project_description,
            core_goal=core_goal, agent_name=agent_label or "后荣-开发环境QA检验员",
            stream=True, max_tokens=8192,
        ):
            qa_chunks.append(chunk)
        qa_r = "".join(qa_chunks).strip()
        if not qa_r:
            if attempt < max_retries:
                await broadcast(project_id, {"type": "step5", "message": f"⚠️ hourong 未返回检验结果，正在重试（第{attempt}次）"})
                continue
            return {"detail": f"后荣{max_retries}次均未返回检验结果（空响应）"}

        # Robust JSON extraction
        _lt, _gt = chr(60), chr(62)
        _think_open = rf'{_lt}(?:thinking|think|analysis){_gt}'
        _think_close = rf'{_lt}/(?:thinking|think|analysis){_gt}'
        qa_r = _re.sub(rf'(?:{_think_open})[\s\S]*?(?:{_think_close})', '', qa_r)

        candidates = []
        # Strategy 1: Code fences
        fenced = _re.findall(r'```(?:json)?\s*\n?(.*?)\n?```', qa_r, _re.DOTALL)
        for fc in fenced:
            s = fc.strip()
            if s:
                candidates.append(s)
        # Strategy 2: Bracket extraction
        bs = qa_r.find('[')
        be = qa_r.rfind(']')
        if bs != -1 and be != -1 and be > bs:
            candidates.append(qa_r[bs:be+1])
        # Strategy 3: Full string
        candidates.append(qa_r)

        parsed = None
        for candidate in candidates:
            try:
                result = _json.loads(candidate)
                if isinstance(result, list) and result:
                    parsed = result
                    break
            except Exception:
                try:
                    fixed = _re.sub(r',\s*(\]|\})', r'\1', candidate)
                    result = _json.loads(fixed)
                    if isinstance(result, list) and result:
                        parsed = result
                        break
                except Exception:
                    pass

        if parsed:
            all_passed = all(bool(r.get("passed")) for r in parsed)
            failed_details = [r.get("detail", "") for r in parsed if not r.get("passed")]
            failed_keys = [r.get("key", "") for r in parsed if not r.get("passed")]
            return {"passed": all_passed, "detail": "", "failed_details": failed_details, "failed_keys": failed_keys, "results": parsed}

        logger.error(f"hourong 检验 JSON 解析失败 (attempt {attempt}/{max_retries}): {qa_r[:500]}")
        if attempt < max_retries:
            await broadcast(project_id, {"type": "step5", "message": f"⚠️ hourong 返回了无法解析的检验报告，正在重试（第{attempt}次）"})
            continue
        return {"detail": "后荣返回了无法解析的检验报告"}
    return {"detail": "后荣检验失败"}


# ── 生成环境配置 ──

@router.post("/{project_id}/step5/execute")
async def execute_step5_async(project_id: str, db: Session = Depends(get_db), current_user=Depends(get_current_user), resume: bool = False):
    """异步启动第五步：后富建立开发环境，hourong 自动检验+收敛修复"""
    import asyncio as _asyncio
    try:
        engine = _get_engine(project_id, db)
        if resume:
            existing = engine.get_step5_artifacts() or {}
        else:
            step5_row = engine._get_step_row(5)
            if step5_row and step5_row.status == "in_progress":
                engine.reset_step(5)
                engine = WorkflowEngine(project_id=project_id, db=db)
                _wf_engines[project_id] = engine
            engine.advance_step(5)
            existing = {}
    except Exception as e:
        return APIResponse(code=1, message=f"无法开始步骤5: {str(e)[:200]}")
    step3 = engine.get_step3_artifacts() or {}
    requirement = (step3.get("doc_content") or step3.get("content") or step3.get("requirement") or step3.get("srs") or "")
    step4 = engine.get_step4_artifacts() or {}
    design_doc = step4.get("design_doc") or ""
    step2 = engine.get_step2_artifacts() or {}
    core_goal = step2.get("confirmed_goal") or step2.get("core_goal") or ""
    srs_path = step3.get("doc_path") or step3.get("file_path") or ""
    doc_paths = step4.get("doc_paths", {})
    engine.save_step5_artifacts({"status": "generating", "message": "🔧 后富正在建立开发环境..."})

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

                # 续跑
                prev = existing if resume else {}
                if resume and prev.get("qa_passed") and prev.get("doc_path") and os.path.exists(prev["doc_path"]):
                    await broadcast(project_id, {"type": "step5", "message": "♻️ 续跑：环境配置已通过检验，跳过"})
                    bg_engine.save_step5_artifacts({**prev, "status": "done", "message": "♻️ 续跑：环境配置已通过"})
                    bg_engine.complete_step(5)
                    await broadcast(project_id, {"type": "done", "message": "✅ 开发环境已建立完毕（续跑）"})
                    return

                max_ver = 0
                for f in glob.glob(os.path.join(docs_dir, f"{slug}_env_V*.md")):
                    import re as _re
                    m = _re.search(r'V(\d+)', os.path.basename(f))
                    if m:
                        max_ver = max(max_ver, int(m.group(1)))

                convergence_log, final_path, final_content = [], "", ""
                fix_round = 0
                while True:
                    fix_round += 1
                    nv = max_ver + fix_round
                    gen_path = os.path.join(docs_dir, f"{slug}_env_V{nv}.md")
                    await broadcast(project_id, {"type": "step5", "message": f"🔧 后富正在{'修复' if fix_round > 1 else '生成'}开发环境配置（第{fix_round}轮）..."})
                    feedback = ""
                    if fix_round > 1 and convergence_log:
                        last = convergence_log[-1]
                        failed = last.get("failed_details", [])
                        feedback = "需要修正的问题（只修复这些问题，禁止扩大范围）：\n" + "\n".join(f"- {d}" for d in failed if d)
                        await broadcast(project_id, {"type": "step5", "message": f"📋 hourong检验报告已发送给后富，正在修复..."})

                    # 如果doc_paths为空，尝试从文件系统扫描设计文档
                    if not doc_paths or not any(doc_paths.values()):
                        import glob as _glob
                        doc_keys = {
                            'arch_reasonableness': ('ARCHITECTURE', '架构设计'),
                            'frontend_feasibility': ('FRONTEND', '前端设计'),
                            'backend_feasibility': ('BACKEND', '后端设计'),
                            'database_design': ('DATABASE', '数据库设计'),
                        }
                        for key, (doc_type, label) in doc_keys.items():
                            pattern = os.path.join(docs_dir, f"{slug}_{doc_type}_V*.md")
                            matches = _glob.glob(pattern)
                            def _ver(p):
                                try:
                                    return int(os.path.basename(p).replace(f"{slug}_{doc_type}_V","").replace(".md",""))
                                except: return 0
                            matches.sort(key=_ver)
                            if matches:
                                doc_paths[key] = matches[-1]

                    prompt_lines = [
                        f"项目名称：{proj_name}",
                        f"核心目标：{core_goal}",
                        "",
                        "读取需求文档：",
                        srs_path,
                        "",
                        "读取架构设计文档：",
                        doc_paths.get('arch_reasonableness', ''),
                        "",
                        "读取前端设计文档：",
                        doc_paths.get('frontend_feasibility', ''),
                        "",
                        "读取后端设计文档：",
                        doc_paths.get('backend_feasibility', ''),
                        "",
                        "读取数据库设计文档：",
                        doc_paths.get('database_design', ''),
                        "",
                        "【任务】",
                        "根据以上文档，完成以下任务：",
                        f"1.输出标准的环境配置文件，保存到文件：{gen_path}",
                        "2.按环境配置文件，建立完整开发环境，依次完成以下配置：",
                        "2.1. 代码仓库初始化",
                        "2.2. 开发框架搭建",
                        "2.3. 依赖管理配置",
                        "2.4. 数据库初始化",
                        "2.5. CI/CD流水线配置",
                        "2.6. Docker化配置",
                        "",
                        "每完成一项子任务，就保存状态，并回复进展",
                        "",
                        "【断点续做规则 - 必须遵守】",
                        "1. 每个子步骤有任何进展，必须立即持久化保存状态到文件",
                        "2. 每次执行前，必须先检查该文件路径是否已有已保存的内容",
                        "3. 若有已保存状态，必须从最新状态继续执行，不得重复已完成的工作",
                        "4. 保存格式：每个子步骤完成后，在文件末尾追加一行 `<!-- STEP_DONE: 步骤名 -->` 作为完成标记",
                        "",
                        "无需输出思考过程",
                    ]
                    if feedback:
                        prompt_lines.insert(18, "")
                        prompt_lines.insert(19, "=== 上次检验未通过项 ===")
                        prompt_lines.insert(20, feedback)
                        prompt_lines.insert(21, "")
                        prompt_lines.insert(22, "【修复要求】")
                        prompt_lines.insert(23, "1. 读取现有文档内容")
                        prompt_lines.insert(24, "2. 只修改上述未通过项")
                        prompt_lines.insert(25, "3. 保持文档其他部分不变")
                        prompt_lines.insert(26, "4. 将修改后的完整文档保存到文件")
                    prompt = "\n".join(prompt_lines)
                    client = GatewayClient(profile_name="houfu", timeout=1200)
                    chunks = []
                    async for chunk in client.chat_completions(
                        messages=[{"role": "user", "content": prompt}],
                        stream=True, max_tokens=64000,
                    ):
                        if chunk.strip():
                            chunks.append(chunk)
                            await broadcast(project_id, {"type": "step5", "content": chunk})

                    # 读取或保存文件
                    if os.path.exists(gen_path):
                        with open(gen_path, "r", encoding="utf-8") as f:
                            content = f.read()
                    else:
                        content = "".join(chunks).strip()
                        with open(gen_path, "w", encoding="utf-8") as f:
                            f.write(content)

                    if not content.strip():
                        await broadcast(project_id, {"type": "step5", "message": "❌ 后富未生成有效内容，重试"})
                        continue
                    final_path, final_content = gen_path, content
                    bg_engine.save_step5_artifacts({"env_info": content, "doc_path": gen_path, "status": "generating"})

                    # hourong 检验
                    await broadcast(project_id, {"type": "step5", "message": f"🔍 hourong 正在检验开发环境配置（文件：{gen_path}）"})
                    focus_items = []
                    if fix_round > 1 and convergence_log:
                        focus_items = convergence_log[-1].get("failed_keys", [])
                    qa_result = await _inspect_env_doc(project_id, gen_path, project_name=proj_name, project_description=proj_desc, core_goal=core_goal, focus_items=focus_items or None)
                    convergence_log.append({"round": fix_round, "detail": qa_result.get("detail", ""), "passed": qa_result.get("passed", False), "failed_details": qa_result.get("failed_details", []), "failed_keys": qa_result.get("failed_keys", [])})
                    bg_engine.save_step5_artifacts({"env_info": content, "doc_path": gen_path, "convergence": convergence_log, "status": "generating", "message": f"第{fix_round}轮QA结果已保存"})
                    if qa_result.get("passed"):
                        await broadcast(project_id, {"type": "step5", "message": f"✅ 开发环境配置已通过 hourong 检验（共{fix_round}轮）"})
                        bg_engine.save_step5_artifacts({"env_info": content, "doc_path": gen_path, "convergence": convergence_log, "status": "done", "qa_passed": True, "message": "✅ 开发环境建立完成"})
                        bg_engine.complete_step(5)
                        await broadcast(project_id, {"type": "done", "message": "✅ 开发环境已建立完毕"})
                        return
                    await broadcast(project_id, {"type": "step5", "message": f"⚠️ 未通过，进入修复"})

                await broadcast(project_id, {"type": "step5", "message": f"🔄 第{fix_round}轮未通过，自动退回重做..."})
            except Exception as e:
                logger.error(f"Step5: {e}")
                try:
                    bg_engine = WorkflowEngine(project_id=project_id, db=bg_db)
                    bg_engine.save_step5_artifacts({"status": "error", "message": f"失败: {str(e)[:200]}"})
                    bg_engine.reset_step(5)
                except Exception:
                    pass
            finally:
                bg_db.close()
        except Exception as e:
            logger.error(f"Step5 fatal: {e}")

    _asyncio.create_task(_generate())
    return APIResponse(code=0, data={"message": "第五步已启动，后富正在建立开发环境（约20分钟）", "status": "generating"})


@router.post("/{project_id}/step5/reset")
def reset_step5(project_id: str, db: Session = Depends(get_db), current_user=Depends(get_current_user)):
    engine = _get_engine(project_id, db)
    engine.reset_step(5)
    _wf_engines.pop(project_id, None)
    return APIResponse(code=0, data={"message": "第五步已重置"})


@router.get("/{project_id}/step5/status")
def get_step5_status(project_id: str, db: Session = Depends(get_db), current_user=Depends(get_current_user)):
    engine = _get_engine(project_id, db)
    return APIResponse(code=0, data=engine.get_step5_artifacts())


@router.post("/{project_id}/step5/artifacts")
def save_step5_artifacts_route(project_id: str, body: dict = Body(...), db: Session = Depends(get_db), current_user=Depends(get_current_user)):
    engine = _get_engine(project_id, db)
    engine.save_step5_artifacts(body)
    return APIResponse(code=0, data={"message": "步骤5状态已保存"})


@router.post("/{project_id}/step5/save-doc")
def save_step5_doc(project_id: str, body: Step3InspectRequest, db: Session = Depends(get_db), current_user=Depends(get_current_user)):
    """将环境配置文件保存到本地和代码库"""
    from datetime import datetime
    from app.services.workflow_engine import WorkflowEngine
    from app.models.repo import Repo
    from app.services.gitea_client import gitea_client
    local_dir = body.save_path or os.path.join(os.getcwd(), "docs", "env")
    os.makedirs(local_dir, exist_ok=True)
    local_filename = body.filename or f"env-config-{datetime.now().strftime('%Y%m%d%H%M%S')}.md"
    local_path = os.path.join(local_dir, local_filename)
    try:
        with open(local_path, "w", encoding="utf-8") as f:
            f.write(body.content)
        logger.info(f"环境配置已保存到本地: {local_path}")
    except Exception as e:
        logger.error(f"保存环境配置到本地失败: {e}")
    engine = WorkflowEngine(project_id=project_id, db=db)
    engine.save_step5_artifacts({
        "env_info": body.content, "filename": body.filename or local_filename,
        "local_path": local_path, "saved_at": datetime.now().isoformat(),
    })
    repo = db.query(Repo).filter(Repo.project_id == project_id).first()
    if not repo:
        return APIResponse(code=0, data={"message": "环境配置已保存到本地和引擎产物", "local_path": local_path})
    try:
        filepath = body.filename or f"docs/env/env-config-{datetime.now().strftime('%Y%m%d%H%M%S')}.md"
        result = asyncio.run(gitea_client.create_file(owner=settings.GITEA_ADMIN_USER, repo=repo.name, filepath=filepath, content=body.content, message="docs: 提交开发环境配置文件", branch="main"))
        engine.save_step5_artifacts({"filepath": filepath, "commit": result.get("commit", {})})
        return APIResponse(code=0, data={"message": "环境配置已保存到本地、代码库和引擎产物", "local_path": local_path, "filepath": filepath, "commit": result.get("commit", {})})
    except Exception as e:
        logger.error(f"保存环境配置到代码库失败: {e}")
        return APIResponse(code=0, data={"message": f"环境配置已保存到本地和引擎产物（保存到代码库失败: {e}）", "local_path": local_path, "filepath": local_filename})


@router.post("/{project_id}/step5/list-docs")
def list_step5_docs(project_id: str, body: DocsListRequest, current_user=Depends(get_current_user)):
    """从环境配置目录读取文档列表"""
    import glob as _glob
    docs_path = body.path
    if not docs_path or not os.path.isdir(docs_path):
        return APIResponse(code=0, data={"files": []})
    files = []
    for f in sorted(_glob.glob(os.path.join(docs_path, "*.md"))):
        fname = os.path.basename(f)
        try:
            with open(f, "r", encoding="utf-8") as fh:
                content = fh.read()
            files.append({"name": fname, "path": f, "content": content})
        except Exception as e:
            logger.warning(f"读取环境配置失败 {f}: {e}")
            files.append({"name": fname, "path": f, "content": ""})
    return APIResponse(code=0, data={"files": files})


@router.post("/{project_id}/step5/inspect")
async def inspect_step5_env(project_id: str, body: Step3InspectRequest, db: Session = Depends(get_db), current_user=Depends(get_current_user)):
    """后荣（HouRong）对开发环境配置进行QA自动检验"""
    from app.services.gateway_client import GatewayClient
    import json as _json
    content, focus_items = body.content, body.focus_items
    if not content or len(content.strip()) < 20:
        return APIResponse(code=0, data={"passed": False, "message": "环境配置内容过短", "dimensions": [{"key": d["key"], "label": d["label"], "description": d["description"], "passed": False, "detail": "内容不足，无法检验"} for d in ENV_SETUP_DIMENSIONS]})
    active_dims = [d for d in ENV_SETUP_DIMENSIONS if not focus_items or d["key"] in focus_items]
    dims_json = _json.dumps([{'检验项目': d['label'], '检验标准': d['description']} for d in active_dims], ensure_ascii=False, indent=2)
    focus_hint = f"\n⚠️ 本次只需重新检验以下 {len(active_dims)} 项：{[d['label'] for d in active_dims]}\n请只针对这些项目做出通过/不通过判定。" if focus_items else ""
    prompt = (f"你是一个专业的环境配置QA检验员（后荣）。请严格检验以下开发环境配置。\n\n=== 环境配置 ===\n{content}\n\n=== 检验项目与标准 ===\n{dims_json}\n{focus_hint}\n直接输出 JSON 数组，不要包含其他说明文字：\n[\n" + ",\n".join(f'  {{"key": "{d["key"]}", "passed": true/false, "detail": "具体检验意见..."}}' for d in active_dims) + "\n]")
    try:
        client = GatewayClient(profile_name="hourong", timeout=120)
        chunks = []
        async for chunk in client.chat_completions(messages=[{"role": "user", "content": prompt}], stream=False, max_tokens=2000):
            chunks.append(chunk)
        reply = "".join(chunks).strip()
        if not reply:
            raise ValueError("后荣未返回检验结果")
        parsed_list = _json.loads(reply)
        if not isinstance(parsed_list, list):
            raise ValueError("返回结果不是数组")
    except Exception as e:
        logger.error(f"后荣检验开发环境失败: {e}")
        return APIResponse(code=0, data={"passed": False, "message": "检验过程出错", "dimensions": [{"key": d["key"], "label": d["label"], "description": d["description"], "passed": False, "detail": f"检验失败: {str(e)[:80]}"} for d in active_dims]})
    results = []
    for dim in active_dims:
        matched = next((r for r in parsed_list if r.get("key") == dim["key"]), None)
        results.append({"key": dim["key"], "label": dim["label"], "description": dim["description"], "passed": bool(matched.get("passed", False)) if matched else False, "detail": matched.get("detail", "未返回该维度检验结果") if matched else "后荣未返回该维度的检验结果"})
    all_passed = all(r["passed"] for r in results)
    return APIResponse(code=0, data={"passed": all_passed, "message": "所有检验项目均通过 ✅" if all_passed else "部分检验项目未通过", "dimensions": results})


@router.post("/{project_id}/step5/qa")
def qa_step5(project_id: str, body: QAResultRequest, db: Session = Depends(get_db), current_user=Depends(get_current_user)):
    engine = _get_engine(project_id, db)
    if body.result == "passed":
        result = engine.pass_qa(5)
    else:
        result = engine.fail_qa(5, reason=body.reason or "", suggestions=body.suggestions)
    return APIResponse(code=0, data={"message": f"第五步QA检验{'通过' if body.result == 'passed' else '未通过'}", "qa": result})