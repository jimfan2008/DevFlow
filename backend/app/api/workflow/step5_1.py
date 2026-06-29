from app.api.workflow.core import (
    router, _get_engine, logger, APIResponse, Depends, get_db,
    get_current_user, Session, Body, Request, HTTPException,
    BaseModel, Optional, asyncio, os, settings, Step5ChatRequest,
    DocsListRequest, Step3InspectRequest, QAResultRequest,
    ENV_SETUP_DIMENSIONS, _wf_engines, WorkflowEngine,
)
import glob


@router.post("/{project_id}/step5_1/chat")
async def step5_1_chat(project_id: str, body: Step5ChatRequest,
                      db: Session = Depends(get_db),
                      current_user=Depends(get_current_user)):
    """与后富（HouFu）对话 - 环境配置文件生成"""
    logger.info(f"Step5_1 chat: project_id={project_id}")
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


# ── hourong 检验环境配置文件 ──

async def _inspect_env_config(
    project_id: str, doc_path: str,
    project_name: str = "", project_description: str = "",
    core_goal: str = "", agent_label: str = "", max_retries: int = 3,
) -> dict:
    import json as _json, re as _re, asyncio as _asyncio
    from app.services.gateway_client import GatewayClient
    from app.api.ws.step5_progress import broadcast
    dims_json = str([{'检验项目': d['label'], '检验标准': d['description'], '检验维': d['key']} for d in ENV_SETUP_DIMENSIONS])
    dim_keys = [d["key"] for d in ENV_SETUP_DIMENSIONS]
    dim_template = ",\n".join(f'  {{"key": "{d["key"]}", "passed": true/false, "detail": "具体检验意见..."}}' for d in ENV_SETUP_DIMENSIONS)
    for attempt in range(1, max_retries + 1):
        if attempt > 1:
            await _asyncio.sleep(2)
            await broadcast(project_id, {"type": "progress", "message": f"🔄 hourong 第{attempt}次重新检验环境配置文件..."})
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
            f"Role: 专业的环境配置文件 QA 检验员（后荣）\n\n"
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
            f"7. The array must contain exactly {len(ENV_SETUP_DIMENSIONS)} objects, one per dimension.\n"
            f"8. Ensure all string values use double quotes and are properly escaped.\n"
            f"9. The JSON must parse successfully without any modifications.\n"
            f"10. After generating the JSON, verify it is valid before outputting.\n"
            f"{retry_pressure}"
            f"Now output the JSON array:"
        )
        qa_cli = GatewayClient(profile_name="hourong", timeout=180)
        qa_chunks = []
        async for chunk in qa_cli.chat_isolated(
            messages=[{"role": "user", "content": insp_prompt}],
            project_id=project_id, project_name=project_name, project_description=project_description,
            core_goal=core_goal, agent_name=agent_label or "后荣-环境配置文件QA检验员",
            stream=True, max_tokens=8192,
        ):
            qa_chunks.append(chunk)
        qa_r = "".join(qa_chunks).strip()
        if not qa_r:
            if attempt < max_retries:
                await broadcast(project_id, {"type": "progress", "message": f"⚠️ hourong 未返回检验结果，正在重试（第{attempt}次）"})
                continue
            return {"detail": f"后荣{max_retries}次均未返回检验结果（空响应）"}

        # Robust JSON extraction
        _lt, _gt = chr(60), chr(62)
        _think_open = rf'{_lt}(?:thinking|think|analysis){_gt}'
        _think_close = rf'{_lt}/(?:thinking|think|analysis){_gt}'
        qa_r = _re.sub(rf'(?:{_think_open})[\s\S]*?(?:{_think_close})', '', qa_r)

        candidates = []
        fenced = _re.findall(r'```(?:json)?\s*\n?(.*?)\n?```', qa_r, _re.DOTALL)
        for fc in fenced:
            s = fc.strip()
            if s:
                candidates.append(s)
        bs = qa_r.find('[')
        be = qa_r.rfind(']')
        if bs != -1 and be != -1 and be > bs:
            candidates.append(qa_r[bs:be+1])
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
            return {"passed": all_passed, "detail": "", "failed_details": failed_details, "results": parsed}

        logger.error(f"hourong 检验 JSON 解析失败 (attempt {attempt}/{max_retries}): {qa_r[:500]}")
        if attempt < max_retries:
            await broadcast(project_id, {"type": "progress", "message": f"⚠️ hourong 返回了无法解析的检验报告，正在重试（第{attempt}次）"})
            continue
        return {"detail": "后荣返回了无法解析的检验报告"}
    return {"detail": "后荣检验失败"}


# ── 生成环境配置文件 ──

@router.post("/{project_id}/step5_1/execute")
async def execute_step5_1_async(project_id: str, db: Session = Depends(get_db), current_user=Depends(get_current_user), resume: bool = False):
    """异步启动第五步第一阶段：后富生成环境配置文件，hourong 自动检验+收敛修复"""
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
        return APIResponse(code=1, message=f"无法开始步骤5_1: {str(e)[:200]}")
    step3 = engine.get_step3_artifacts() or {}
    requirement = (step3.get("doc_content") or step3.get("content") or step3.get("requirement") or step3.get("srs") or "")
    step4 = engine.get_step4_artifacts() or {}
    design_doc = step4.get("design_doc") or ""
    step2 = engine.get_step2_artifacts() or {}
    core_goal = step2.get("confirmed_goal") or step2.get("core_goal") or ""
    srs_path = step3.get("doc_path") or step3.get("file_path") or ""
    doc_paths = step4.get("doc_paths", {})
    engine.save_step5_artifacts({"status": "generating", "message": "📝 后富正在生成环境配置文件..."})

    async def _generate():
        import time as _time
        from app.services.gateway_client import GatewayClient
        fix_round = 0
        convergence_log = []
        try:
            from app.database import SessionLocal
            from app.models.project import Project
            from app.api.ws.step5_progress import broadcast
            bg_db = SessionLocal()
            try:
                bg_engine = WorkflowEngine(project_id=project_id, db=bg_db)
                proj = bg_db.query(Project).filter(Project.id == project_id).first()
                slug = proj.slug if proj else project_id.replace("-", "")
                docs_dir = os.path.join(settings.PROJECTS_BASE_DIR, slug, "docs")
                os.makedirs(docs_dir, exist_ok=True)
                proj_name = proj.name if proj else ""
                proj_desc = proj.description or ""

                # 续跑：恢复上次进度
                prev = existing if resume else {}
                saved_fix_round = prev.get("fix_round", 0)
                saved_convergence = prev.get("convergence", [])

                if resume and prev.get("qa_passed") and prev.get("doc_path") and os.path.exists(prev["doc_path"]):
                    await broadcast(project_id, {"type": "progress", "message": "♻️ 续跑：环境配置文件已通过检验，跳过"})
                    bg_engine.save_step5_artifacts({**prev, "status": "done", "message": "♻️ 续跑：环境配置文件已通过"})
                    bg_engine.complete_step(5)
                    await broadcast(project_id, {"type": "done", "message": "✅ 环境配置文件已通过检验（续跑）"})
                    return

                # 续跑：如果上次中断在生成中，从上次的轮次继续
                if resume and saved_fix_round > 0 and not prev.get("qa_passed"):
                    await broadcast(project_id, {"type": "progress", "message": f"♻️ 续跑：从第{saved_fix_round}轮之后继续"})
                    fix_round = saved_fix_round
                    convergence_log = saved_convergence

                max_ver = 0
                for f in glob.glob(os.path.join(docs_dir, f"{slug}_env_V*.md")):
                    import re as _re
                    m = _re.search(r'V(\d+)', os.path.basename(f))
                    if m:
                        max_ver = max(max_ver, int(m.group(1)))

                final_path, final_content = "", ""
                while True:
                    fix_round += 1
                    nv = max_ver + fix_round
                    gen_path = os.path.join(docs_dir, f"{slug}_env_V{nv}.md")

                    # ── 持久化：记录当前轮次 ──
                    bg_engine.save_step5_artifacts({
                        "status": "generating",
                        "message": f"📝 后富正在{'修复' if fix_round > 1 else '生成'}环境配置文件（第{fix_round}轮）...",
                        "fix_round": fix_round,
                        "convergence": convergence_log,
                        "phase": "generating",
                    })
                    await broadcast(project_id, {"type": "progress", "message": f"📝 后富正在{'修复' if fix_round > 1 else '生成'}环境配置文件（第{fix_round}轮）..."})

                    feedback = ""
                    if fix_round > 1 and convergence_log:
                        last = convergence_log[-1]
                        failed = last.get("failed_details", [])
                        feedback = "需要修正的问题（只修复这些问题，禁止扩大范围）：\n" + "\n".join(f"- {d}" for d in failed if d)
                        await broadcast(project_id, {"type": "progress", "message": f"📋 hourong检验报告已发送给后富，正在修复..."})

                    # 如果doc_paths为空，尝试从文件系统扫描设计文档
                    t_doc_start = _time.time()
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
                    t_doc_end = _time.time()
                    doc_read_time = round(t_doc_end - t_doc_start, 2)

                    prompt_lines = [
                        f"项目名称：{proj_name}",
                        f"核心目标：{core_goal}",
                        "",
                        "你是资深CI/CD工程师后富（HouFu），负责生成环境配置文件。",
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
                        "【任务 - 仅生成环境配置文件】",
                        "根据以上文档，生成一份标准完整的环境配置文件。",
                        "⚠️ 注意：本步骤只生成配置文件，不要执行任何搭建操作！",
                        f"请将环境配置文件保存到文件：{gen_path}",
                        "",
                        "【断点续做规则 - 必须遵守】",
                        "1. 每个子步骤有任何进展，必须立即持久化保存状态到文件",
                        "2. 每次执行前，必须先检查该文件路径是否已有已保存的内容",
                        "3. 若有已保存状态，必须从最新状态继续执行，不得重复已完成的工作",
                        "4. 保存格式：每个子步骤完成后，在文件末尾追加一行 `<!-- STEP_DONE: 步骤名 -->` 作为完成标记",
                        "",
                        "【输出格式要求】",
                        "环境配置文件必须包含以下章节：",
                        "# 开发环境配置文档",
                        "## 1. 环境概述（项目技术栈、运行环境要求）",
                        "## 2. 依赖安装（前端/后端依赖包列表及安装命令）",
                        "## 3. 数据库配置（数据库类型、连接信息、初始化SQL）",
                        "## 4. 环境变量（所有必需的环境变量及说明）",
                        "## 5. Docker配置（docker-compose.yml配置）",
                        "## 6. CI/CD配置（构建、测试、部署流水线配置）",
                        "## 7. 本地开发指南（开发者快速启动步骤）",
                        "",
                        "【重要】",
                        "1. 配置文件必须完整、准确，可供后续步骤直接执行",
                        "2. 不要输出思考过程",
                        "3. 不要执行任何搭建命令，只输出配置文件",
                    ]
                    if feedback:
                        prev_path = os.path.join(docs_dir, f"{slug}_env_V{nv-1}.md")
                        prompt_lines.insert(18, "")
                        prompt_lines.insert(19, "=== 上次检验未通过项 ===")
                        prompt_lines.insert(20, feedback)
                        prompt_lines.insert(21, "")
                        prompt_lines.insert(22, "【修复要求】")
                        prompt_lines.insert(23, f"1. 读取现有文档内容{prev_path}")
                        prompt_lines.insert(24, "2. 只修改上述未通过项")
                        prompt_lines.insert(25, "3. 保持文档其他部分不变")
                        prompt_lines.insert(26, f"4. 将修改后的完整文档保存到文件：{gen_path}")
                    prompt = "\n".join(prompt_lines)

                    # ── 持久化：开始调用houfu ──
                    bg_engine.save_step5_artifacts({
                        "status": "generating",
                        "message": f"📤 正在调用后富生成配置文件（第{fix_round}轮）...",
                        "fix_round": fix_round,
                        "convergence": convergence_log,
                        "phase": "calling_houfu",
                    })

                    await broadcast(project_id, {"type": "prompt", "prompt": prompt, "round": fix_round})
                    client = GatewayClient(profile_name="houfu", timeout=1200)
                    chunks = []
                    t_llm_start = _time.time()
                    t_first_chunk = None
                    async for chunk in client.chat_completions(
                        messages=[{"role": "user", "content": prompt}],
                        stream=True, max_tokens=64000,
                    ):
                        if chunk.strip():
                            if t_first_chunk is None:
                                t_first_chunk = _time.time()
                            chunks.append(chunk)
                            await broadcast(project_id, {"type": "progress", "content": chunk, "timestamp": _time.time()})
                    t_llm_end = _time.time()
                    llm_prefill_time = round(t_first_chunk - t_llm_start, 2) if t_first_chunk else 0
                    llm_decode_time = round(t_llm_end - t_first_chunk, 2) if t_first_chunk else round(t_llm_end - t_llm_start, 2)

                    # 读取或保存文件
                    t_io_start = _time.time()
                    if os.path.exists(gen_path):
                        with open(gen_path, "r", encoding="utf-8") as f:
                            content = f.read()
                    else:
                        content = "".join(chunks).strip()
                        with open(gen_path, "w", encoding="utf-8") as f:
                            f.write(content)
                    t_io_end = _time.time()
                    io_write_time = round(t_io_end - t_io_start, 2)

                    if not content.strip():
                        # ── 持久化：空内容，记录后重试 ──
                        bg_engine.save_step5_artifacts({
                            "status": "generating",
                            "message": "❌ 后富未生成有效内容，重试",
                            "fix_round": fix_round,
                            "convergence": convergence_log,
                            "phase": "empty_content",
                        })
                        await broadcast(project_id, {"type": "progress", "message": "❌ 后富未生成有效内容，重试"})
                        continue

                    final_path, final_content = gen_path, content

                    # ── 持久化：内容已生成，准备检验 ──
                    bg_engine.save_step5_artifacts({
                        "env_info": content,
                        "doc_path": gen_path,
                        "status": "generating",
                        "message": f"📝 配置文件已生成（第{fix_round}轮），准备QA检验",
                        "fix_round": fix_round,
                        "convergence": convergence_log,
                        "phase": "qa_pending",
                    })

                    # hourong 检验
                    # ── 持久化：开始检验 ──
                    bg_engine.save_step5_artifacts({
                        "env_info": content,
                        "doc_path": gen_path,
                        "status": "generating",
                        "message": f"🔍 hourong 正在检验环境配置文件（第{fix_round}轮）...",
                        "fix_round": fix_round,
                        "convergence": convergence_log,
                        "phase": "qa_inspecting",
                    })
                    await broadcast(project_id, {"type": "progress", "message": f"🔍 hourong 正在检验环境配置文件（文件：{gen_path}）"})

                    t_val_start = _time.time()
                    qa_result = await _inspect_env_config(project_id, gen_path, project_name=proj_name, project_description=proj_desc, core_goal=core_goal)
                    t_val_end = _time.time()
                    validation_time = round(t_val_end - t_val_start, 2)

                    # ── 持久化：检验完成，记录结果 ──
                    convergence_log.append({"round": fix_round, "detail": qa_result.get("detail", ""), "passed": qa_result.get("passed", False), "failed_details": qa_result.get("failed_details", [])})

                    # ── 计时统计 ──
                    total_time = round(doc_read_time + llm_prefill_time + llm_decode_time + io_write_time + validation_time, 2)
                    timings = {
                        "doc_read": doc_read_time,
                        "llm_prefill": llm_prefill_time,
                        "llm_decode": llm_decode_time,
                        "io_write": io_write_time,
                        "validation": validation_time,
                        "total": total_time,
                    }
                    bottleneck = max(timings, key=timings.get)
                    bottleneck_label = {"doc_read": "读取文档", "llm_prefill": "LLM Prefill", "llm_decode": "LLM Decode", "io_write": "IO写入", "validation": "校验"}.get(bottleneck, bottleneck)
                    timing_msg = (
                        f"⏱️ 第{fix_round}轮耗时：读取文档 {doc_read_time}s"
                        f" | LLM Prefill {llm_prefill_time}s"
                        f" | LLM Decode {llm_decode_time}s"
                        f" | IO写入 {io_write_time}s"
                        f" | 校验 {validation_time}s"
                        f" | 总计 {total_time}s"
                        f" | 瓶颈: {bottleneck_label}({timings[bottleneck]}s)"
                    )
                    await broadcast(project_id, {"type": "timing", "message": timing_msg, "timing": timings, "bottleneck": bottleneck})

                    bg_engine.save_step5_artifacts({
                        "env_info": content,
                        "doc_path": gen_path,
                        "convergence": convergence_log,
                        "status": "generating",
                        "message": f"第{fix_round}轮QA结果已保存",
                        "fix_round": fix_round,
                        "phase": "qa_done",
                    })

                    if qa_result.get("passed"):
                        # ── 持久化：通过 ──
                        bg_engine.save_step5_artifacts({
                            "env_info": content,
                            "doc_path": gen_path,
                            "convergence": convergence_log,
                            "status": "done",
                            "qa_passed": True,
                            "message": "✅ 环境配置文件生成完成",
                            "fix_round": fix_round,
                            "phase": "completed",
                        })
                        bg_engine.complete_step(5)
                        await broadcast(project_id, {"type": "progress", "message": f"✅ 环境配置文件已通过 hourong 检验（共{fix_round}轮）"})
                        await broadcast(project_id, {"type": "done", "message": "✅ 环境配置文件已通过检验"})
                        return

                    # ── 持久化：未通过，准备修复 ──
                    bg_engine.save_step5_artifacts({
                        "env_info": content,
                        "doc_path": gen_path,
                        "convergence": convergence_log,
                        "status": "generating",
                        "message": f"⚠️ 第{fix_round}轮未通过，准备修复",
                        "fix_round": fix_round,
                        "phase": "fixing",
                    })
                    await broadcast(project_id, {"type": "progress", "message": f"⚠️ 未通过，进入修复"})

                await broadcast(project_id, {"type": "progress", "message": f"🔄 第{fix_round}轮未通过，自动退回重做..."})
            except Exception as e:
                logger.error(f"Step5_1: {e}", exc_info=True)
                try:
                    bg_engine = WorkflowEngine(project_id=project_id, db=bg_db)
                    bg_engine.save_step5_artifacts({
                        "status": "error",
                        "message": f"失败: {str(e)[:200]}",
                        "fix_round": fix_round,
                        "convergence": convergence_log,
                    })
                    bg_engine.reset_step(5)
                except Exception:
                    pass
            finally:
                bg_db.close()
        except Exception as e:
            logger.error(f"Step5_1 fatal: {e}")
        finally:
            from app.services.haimei_executor import HaimeiStepExecutor
            HaimeiStepExecutor._tasks.pop(f"{project_id}:step5", None)

    task = _asyncio.create_task(_generate())
    from app.services.haimei_executor import HaimeiStepExecutor
    HaimeiStepExecutor._tasks[f"{project_id}:step5"] = task
    return APIResponse(code=0, data={"message": "步骤5_1已启动，后富正在生成环境配置文件", "status": "generating"})


@router.post("/{project_id}/step5_1/reset")
def reset_step5_1(project_id: str, db: Session = Depends(get_db), current_user=Depends(get_current_user)):
    engine = _get_engine(project_id, db)
    engine.reset_step(5)
    _wf_engines.pop(project_id, None)
    return APIResponse(code=0, data={"message": "步骤5_1已重置"})


@router.get("/{project_id}/step5_1/status")
def get_step5_1_status(project_id: str, db: Session = Depends(get_db), current_user=Depends(get_current_user)):
    engine = _get_engine(project_id, db)
    return APIResponse(code=0, data=engine.get_step5_artifacts())


@router.post("/{project_id}/step5_1/artifacts")
def save_step5_1_artifacts_route(project_id: str, body: dict = Body(...), db: Session = Depends(get_db), current_user=Depends(get_current_user)):
    engine = _get_engine(project_id, db)
    engine.save_step5_artifacts(body)
    return APIResponse(code=0, data={"message": "步骤5_1状态已保存"})


@router.post("/{project_id}/step5_1/qa")
def qa_step5_1(project_id: str, body: QAResultRequest, db: Session = Depends(get_db), current_user=Depends(get_current_user)):
    engine = _get_engine(project_id, db)
    if body.result == "passed":
        result = engine.pass_qa(5)
    else:
        result = engine.fail_qa(5, reason=body.reason or "", suggestions=body.suggestions)
    return APIResponse(code=0, data={"message": f"步骤5_1 QA检验{'通过' if body.result == 'passed' else '未通过'}", "qa": result})
