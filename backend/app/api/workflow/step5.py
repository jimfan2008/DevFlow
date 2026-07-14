from app.api.workflow.core import (
    router, _get_engine, logger, APIResponse, Depends, get_db,
    get_current_user, Session, Body, Request, HTTPException,
    BaseModel, Optional, asyncio, os, settings, Step5ChatRequest,
    DocsListRequest, Step3InspectRequest, QAResultRequest,
    ENV_SETUP_DIMENSIONS,
)
from app.services.doc_sharder import (
    get_shard_config, load_all_chapters, load_single_chapter,
    save_chapter, build_cacheable_chapter_summaries, ShardRetriever,
)


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
            project_slug=project.slug if project.slug else project_id,
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
    failed_keys: list = None,
) -> dict:
    import json as _json, re as _re, asyncio as _asyncio
    from app.api.ws.step3_qa import _inspect_via_subagent
    from app.api.ws.step4_progress import broadcast
    active_dims = [d for d in ENV_SETUP_DIMENSIONS if not failed_keys or d["key"] in failed_keys]
    dims_json = str([{'检验项目': d['label'], '检验标准': d['description'], '检验维': d['key']} for d in active_dims])
    dim_keys = [d["key"] for d in active_dims]
    dim_template = ",\n".join(f'  {{"key": "{d["key"]}", "score": 100, "deduction": "", "passed": true/false, "detail": "具体检验意见..."}}' for d in active_dims)
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
        focus_hint_str = f"\n⚠️ FOCUS: This round ONLY re-inspects the following {len(active_dims)} items that failed previously: {[d['label'] for d in active_dims]}\nDo NOT inspect any other items. Scope expansion is strictly prohibited.\n" if failed_keys else ""
        insp_prompt = (
            f"You are a JSON-only API. Your entire response MUST be a single, "
            f"valid JSON array — nothing else.\n\n"
            f"Role: 专业的环境配置 QA 检验员（后荣）\n\n"
            f"=== 检验项目与标准 ===\n{dims_json}\n\n"
            f"=== 文档路径 ===\n{doc_path}\n\n"
             f"Task: 读取该文档文件，严格逐项检验是否满足上述标准。\n"
             f"注意：文档文件位于上述路径，请直接读取文件进行完整检验。\n\n"
             f"SCORING RULE: Each dimension starts at 100 points. Deduct points for defects "
             f"(minor: 5-10, moderate: 15-20, severe: 25-30). "
             f"Dimension passes if score >= 90. Overall pass requires average score > 90.\n\n"
            f"=== OUTPUT FORMAT (STRICT) ===\n"
            f"Output ONLY a JSON array with exactly {len(active_dims)} objects. "
             f"Each object has 5 fields:\n"
             f"  key: string (must be one of: {', '.join(dim_keys)})\n"
             f"  score: integer (0-100, start from 100, deduct points for defects)\n"
             f"  deduction: string (reason for point deduction)\n"
             f"  passed: boolean (true if score >= 90)\n"
             f"  detail: string (your inspection comments)\n\n"
            f"Template:\n[\n"
            f"{dim_template}\n]\n\n"
             f"{focus_hint_str}"
             f"CONVERGENCE RULE:\n"
             f"The inspection report MUST focus ONLY on non-conforming items. "
             f"Clearly indicate what specific issues need to be fixed and the direction of modification. "
             f"Downstream agents will ONLY modify non-conforming items based on your report. "
             f"Do NOT request changes to items that have already passed. "
             f"Scope expansion is strictly prohibited.\n\n"
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
            f"Now output the JSON array:"
        )
        qa_r = await _inspect_via_subagent(prompt=insp_prompt, max_retries=max_retries)
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
            scores = [int(r.get("score", 100)) for r in parsed]
            avg_score = sum(scores) / len(scores)
            failed_details = [r.get("detail", "") for r in parsed if int(r.get("score", 100)) < 90]
            return {"passed": avg_score > 90, "score": avg_score, "total_score": sum(scores), "max_score": len(scores) * 100, "detail": "", "failed_details": failed_details, "results": parsed}

        logger.error(f"hourong 检验 JSON 解析失败 (attempt {attempt}/{max_retries}): {qa_r[:500]}")
        if attempt < max_retries:
            await broadcast(project_id, {"type": "step5", "message": f"⚠️ hourong 返回了无法解析的检验报告，正在重试（第{attempt}次）"})
            continue
        return {"detail": "后荣返回了无法解析的检验报告"}
    return {"detail": "后荣检验失败"}


# ── 文档分片支持 ──
CHAPTER_MARKER_START = "<!-- CHAPTER:"
CHAPTER_MARKER_END = "-->"

_DIMENSION_TO_CHAPTER = {
    "environment_availability": ["repo", "framework"],
    "config_correctness": ["framework", "database_init", "cicd"],
    "dependency_completeness": ["dependencies"],
}


def _split_chapters(full_text: str) -> dict:
    import re
    chapters = {}
    pattern = re.compile(
        rf'{re.escape(CHAPTER_MARKER_START)}\s*(\w+)\s*{re.escape(CHAPTER_MARKER_END)}'
        r'([\s\S]*?)(?='
        rf'{re.escape(CHAPTER_MARKER_START)}|\Z)'
    )
    for m in pattern.finditer(full_text):
        key = m.group(1)
        content = m.group(2).strip()
        if content:
            chapters[key] = content
    return chapters


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

                doc_type = "ENV"
                shard_config = get_shard_config(doc_type)

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
                start_round = 1
                if resume and prev:
                    saved_round = prev.get("current_fix_round", 0)
                    saved_convergence = prev.get("convergence", [])
                    if saved_round > 0:
                        start_round = saved_round + 1
                        convergence_log = list(saved_convergence)
                        await broadcast(project_id, {"type": "step5", "message": f"♻️ 续跑：从第{start_round}轮继续"})
                for fix_round in range(start_round, 11):
                    nv = max_ver + fix_round
                    gen_path = os.path.join(docs_dir, f"{slug}_env_V{nv}.md")
                    await broadcast(project_id, {"type": "step5", "message": f"🔧 后富正在{'修复' if fix_round > 1 else '生成'}开发环境配置（第{fix_round}轮）..."})
                    feedback = ""
                    if fix_round > 1 and convergence_log:
                        last = convergence_log[-1]
                        failed = last.get("failed_details", [])
                        feedback = "需要修正的问题（只修复这些问题，禁止扩大范围）：\n" + "\n".join(f"- {d}" for d in failed if d)

                    is_initial_round = (not feedback or fix_round == start_round)
                    if is_initial_round:
                        chapter_instructions = "\n".join(
                            f"{CHAPTER_MARKER_START} {ch['key']} {CHAPTER_MARKER_END}\n{ch['title']}：{ch['instruction']}"
                            for ch in shard_config
                        )
                        prompt_lines = [
                            "你是资深CI/CD工程师后富（HouFu），负责建立软件开发环境。\n",
                            f"=== 需求文档（SRS）===\n{requirement}\n\n",
                            f"=== 架构设计文档 ===\n{design_doc}\n\n",
                            "=== 章节要求 ===\n"
                            "请按以下章节组织输出，每个章节用标记包裹：\n\n"
                            f"{chapter_instructions}\n\n",
                            f"请根据上述需求说明书和架构设计文档，建立完整的开发环境，并将完整内容保存到：{gen_path}\n"
                            "要求：1.代码仓库初始化 2.开发框架搭建 3.依赖配置 4.数据库初始化\n"
                            "5.CI/CD流水线配置\n"
                            "章节要求：每个章节用 <!-- CHAPTER: key --> 标记包裹\n"
                            "不要输出推理过程。"
                        ]
                        prompt = "\n".join(prompt_lines)
                        client = GatewayClient(profile_name="houfu", timeout=1200)
                        chunks = []
                        async for chunk in client.chat_isolated(
                            messages=[{"role": "user", "content": prompt}],
                            project_id=project_id, project_name=proj_name, project_description=proj_desc,
                            core_goal=core_goal, agent_name="后富（HouFu）CI/CD工程师-环境生成",
                            stream=True, max_tokens=64000,
                            project_slug=slug,
                        ):
                            if chunk.strip():
                                chunks.append(chunk)
                                await broadcast(project_id, {"type": "step5", "content": chunk})

                        if os.path.exists(gen_path):
                            with open(gen_path, "r", encoding="utf-8") as f:
                                content = f.read()
                        else:
                            content = "".join(chunks).strip()

                        chapters = _split_chapters(content)
                        for key, chapter_content in chapters.items():
                            save_chapter(doc_type, key, chapter_content, docs_dir, slug)

                        if not content.strip():
                            await broadcast(project_id, {"type": "step5", "message": "❌ 后富未生成有效内容，重试"})
                            continue
                        with open(gen_path, "w", encoding="utf-8") as f:
                            f.write(content)
                    else:
                        last_results = convergence_log[-1].get("results", [])
                        failed_dims = [r.get("key", "") for r in last_results if int(r.get("score", 100)) < 90]
                        failed_chapters = set()
                        for dim_key in failed_dims:
                            for ch_key in _DIMENSION_TO_CHAPTER.get(dim_key, []):
                                failed_chapters.add(ch_key)
                        if not failed_chapters:
                            failed_chapters = {ch["key"] for ch in shard_config}

                        retriever = ShardRetriever(docs_dir, slug, doc_type)
                        cacheable_parts = build_cacheable_chapter_summaries(doc_type, docs_dir, slug)

                        reassembled_parts = []
                        for ch in shard_config:
                            if ch["key"] in failed_chapters:
                                await broadcast(project_id, {"type": "step5", "message": f"🔧 后富正在修复章节：{ch['title']}（{ch['key']}）..."})
                                context_prompt = retriever.build_context_prompt(
                                    ch["instruction"], doc_type, top_k=2, exclude_key=ch["key"]
                                )
                                ch_prompt_lines = [
                                    "你是资深CI/CD工程师后富（HouFu），负责建立软件开发环境。\n",
                                    f"=== 需求文档（SRS）===\n{requirement}\n\n",
                                    f"=== 架构设计文档 ===\n{design_doc}\n\n",
                                    f"=== 上次检验未通过项 ===\n{feedback}\n\n",
                                    f"=== 当前需修复章节 ===\n"
                                    f"{CHAPTER_MARKER_START} {ch['key']} {CHAPTER_MARKER_END}\n"
                                    f"章节：{ch['title']}\n"
                                    f"内容要求：{ch['instruction']}\n\n",
                                ]
                                if context_prompt:
                                    ch_prompt_lines.append(f"=== 相关章节参考 ===\n{context_prompt}\n\n")
                                ch_prompt_lines.append(
                                    f"请只针对以上章节进行重写和修复，输出时使用 {CHAPTER_MARKER_START} {ch['key']} {CHAPTER_MARKER_END} 标记包裹。\n不要输出推理过程。"
                                )
                                ch_prompt = "\n".join(ch_prompt_lines)
                                ch_client = GatewayClient(profile_name="houfu", timeout=1200)
                                ch_chunks = []
                                async for chunk in ch_client.chat_isolated(
                                    messages=[{"role": "user", "content": ch_prompt}],
                                    project_id=project_id, project_name=proj_name, project_description=proj_desc,
                                    core_goal=core_goal, agent_name="后富（HouFu）CI/CD工程师-环境修复",
                                    stream=True, max_tokens=32000,
                                    cacheable_system_parts=cacheable_parts,
                                    project_slug=slug,
                                ):
                                    if chunk.strip():
                                        ch_chunks.append(chunk)
                                raw_ch_content = "".join(ch_chunks).strip()
                                ch_chapters = _split_chapters(raw_ch_content)
                                if ch["key"] in ch_chapters:
                                    chapter_content = ch_chapters[ch["key"]]
                                else:
                                    chapter_content = raw_ch_content
                                save_chapter(doc_type, ch["key"], chapter_content, docs_dir, slug)
                                reassembled_parts.append(
                                    f"{CHAPTER_MARKER_START} {ch['key']} {CHAPTER_MARKER_END}\n{chapter_content}"
                                )
                            else:
                                existing_ch_content = load_single_chapter(doc_type, ch["key"], docs_dir, slug)
                                if existing_ch_content:
                                    reassembled_parts.append(
                                        f"{CHAPTER_MARKER_START} {ch['key']} {CHAPTER_MARKER_END}\n{existing_ch_content}"
                                    )
                        content = "\n\n".join(reassembled_parts)
                        with open(gen_path, "w", encoding="utf-8") as f:
                            f.write(content)

                    if not content.strip():
                        await broadcast(project_id, {"type": "step5", "message": "❌ 后富未生成有效内容，重试"})
                        continue
                    final_path, final_content = gen_path, content
                    bg_engine.save_step5_artifacts({"env_info": content, "doc_path": gen_path, "status": "generating", "current_fix_round": fix_round, "convergence": convergence_log})

                    # hourong 检验
                    await broadcast(project_id, {"type": "step5", "message": f"🔍 hourong 正在检验开发环境配置（文件：{gen_path}）"})
                    failed_keys = []
                    if fix_round > 1 and convergence_log:
                        last_results = convergence_log[-1].get("results", [])
                        if last_results:
                            failed_keys = [r.get("key", "") for r in last_results if int(r.get("score", 100)) < 90]
                    qa_result = await _inspect_env_doc(project_id, gen_path, project_name=proj_name, project_description=proj_desc, core_goal=core_goal, failed_keys=failed_keys if failed_keys else None)
                    convergence_log.append({"round": fix_round, "detail": qa_result.get("detail", ""), "passed": qa_result.get("passed", False), "failed_details": qa_result.get("failed_details", []), "results": qa_result.get("results", [])})
                    if qa_result.get("passed"):
                        await broadcast(project_id, {"type": "step5", "message": f"✅ 开发环境配置已通过 hourong 检验（共{fix_round}轮）"})
                        bg_engine.save_step5_artifacts({"env_info": content, "doc_path": gen_path, "convergence": convergence_log, "status": "done", "qa_passed": True, "message": "✅ 开发环境建立完成"})
                        bg_engine.complete_step(5)
                        await broadcast(project_id, {"type": "done", "message": "✅ 开发环境已建立完毕"})
                        return
                    await broadcast(project_id, {"type": "step5", "message": f"⚠️ 未通过，进入修复"})

                await broadcast(project_id, {"type": "error", "message": "❌ 经10轮仍未通过检验"})
                bg_engine.save_step5_artifacts({"env_info": final_content, "doc_path": final_path, "convergence": convergence_log, "status": "error"})
                bg_engine.reset_step(5)
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
    from app.api.ws.step3_qa import _inspect_via_subagent
    from datetime import datetime, timezone
    import json as _json
    content, focus_items = body.content, body.focus_items
    if not content or len(content.strip()) < 20:
        return APIResponse(code=0, data={"passed": False, "message": "环境配置内容过短", "dimensions": [{"key": d["key"], "passed": False} for d in ENV_SETUP_DIMENSIONS]})
    active_dims = [d for d in ENV_SETUP_DIMENSIONS if not focus_items or d["key"] in focus_items]
    dims_json = _json.dumps([{'检验项目': d['label'], '检验标准': d['description']} for d in active_dims], ensure_ascii=False, indent=2)
    focus_hint = f"\n⚠️ 本次只需重新检验以下 {len(active_dims)} 项：{[d['label'] for d in active_dims]}\n请只针对这些项目做出通过/不通过判定。" if focus_items else ""
    convergence_hint = "\n⚠️ 收敛性要求：检验报告必须聚焦于不合格项，明确指出不合格项的问题和修改方向。后续Agent将只修改不合格项，禁止扩大范围。已合格项目不得提出修改要求。"
    scoring_hint = "\n评分规则：每个维度起始100分，每发现一个缺陷扣减相应分数（轻微缺陷扣5-10分，一般缺陷扣15-20分，严重缺陷扣25-30分）。维度得分≥90则该维度passed为true。所有维度平均分>90分为整体合格。"
    prompt = (f"你是一个专业的环境配置QA检验员（后荣）。请严格检验以下开发环境配置。\n\n=== 环境配置 ===\n{content}\n\n=== 检验项目与标准 ===\n{dims_json}\n{focus_hint}\n{convergence_hint}\n{scoring_hint}\n直接输出 JSON 数组，不要包含其他说明文字：\n[\n" + ",\n".join(f'  {{"key": "{d["key"]}", "score": 100, "deduction": "", "passed": true/false, "detail": "具体检验意见..."}}' for d in active_dims) + "\n]")
    try:
        reply = await _inspect_via_subagent(prompt=prompt, max_retries=3)
        if not reply:
            raise ValueError("后荣未返回检验结果")
        parsed_list = _json.loads(reply)
        if not isinstance(parsed_list, list):
            raise ValueError("返回结果不是数组")
    except Exception as e:
        logger.error(f"后荣检验开发环境失败: {e}")
        return APIResponse(code=0, data={"passed": False, "message": "检验过程出错", "dimensions": [{"key": d["key"], "passed": False} for d in active_dims]})
    results = []
    for dim in active_dims:
        matched = next((r for r in parsed_list if r.get("key") == dim["key"]), None)
        results.append({"key": dim["key"], "label": dim["label"], "description": dim["description"], "score": int(matched.get("score", 100)) if matched else 0, "passed": int(matched.get("score", 100)) >= 90 if matched else False, "detail": matched.get("detail", "未返回该维度检验结果") if matched else "后荣未返回该维度的检验结果"})
    avg_score = sum(r.get("score", 0) for r in results) / len(results) if results else 0
    all_passed = avg_score > 90
    # 持久化：保存检验结果到 DB
    engine = _get_engine(project_id, db)
    engine.save_step5_artifacts({
        "inspect_result": {"passed": all_passed, "avg_score": avg_score, "dimensions": results, "inspected_at": datetime.now(timezone.utc).isoformat()},
        "qa_passed": all_passed, "qa_checked": True,
    })
    return APIResponse(code=0, data={"passed": all_passed, "score": avg_score, "message": "所有检验项目均通过 ✅" if all_passed else "部分检验项目未通过", "dimensions": results})


@router.post("/{project_id}/step5/qa")
def qa_step5(project_id: str, body: QAResultRequest, db: Session = Depends(get_db), current_user=Depends(get_current_user)):
    from datetime import datetime, timezone
    engine = _get_engine(project_id, db)
    now_iso = datetime.now(timezone.utc).isoformat()
    if body.result == "passed":
        result = engine.pass_qa(5)
        engine.save_step5_artifacts({"qa_passed": True, "qa_status": "passed", "qa_checked_at": now_iso})
    else:
        result = engine.fail_qa(5, reason=body.reason or "", suggestions=body.suggestions)
        engine.save_step5_artifacts({"qa_passed": False, "qa_status": "failed", "qa_checked_at": now_iso, "qa_fail_reason": body.reason, "qa_suggestions": body.suggestions})
    return APIResponse(code=0, data={"message": f"第五步QA检验{'通过' if body.result == 'passed' else '未通过'}", "qa": result})