from app.api.workflow.core import (
    router, _get_engine, logger, APIResponse, Depends, get_db,
    get_current_user, Session, Body, Request, HTTPException,
    BaseModel, Optional, asyncio, os, settings, Step5ChatRequest,
    DocsListRequest, Step3InspectRequest, QAResultRequest,
    ENV_SETUP_DIMENSIONS, _wf_engines, WorkflowEngine,
)
import glob


@router.post("/{project_id}/step5_2/chat")
async def step5_2_chat(project_id: str, body: Step5ChatRequest,
                      db: Session = Depends(get_db),
                      current_user=Depends(get_current_user)):
    """与后富（HouFu）对话 - 环境搭建执行"""
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
        logger.error(f"Step5_2 chat failed: {e}")
        return APIResponse(code=1, message="与后富对话失败", data=None)


# ── hourong 检验环境搭建结果 ──

async def _inspect_env_setup(
    project_id: str, doc_path: str,
    project_name: str = "", project_description: str = "",
    core_goal: str = "", agent_label: str = "", max_retries: int = 3,
    failed_keys: list = None,
) -> dict:
    import json as _json, re as _re, asyncio as _asyncio
    from app.api.ws.step3_qa import _inspect_via_subagent
    from app.api.ws.step5_progress import broadcast
    active_dims = [d for d in ENV_SETUP_DIMENSIONS if not failed_keys or d["key"] in failed_keys]
    dims_json = str([{'检验项目': d['label'], '检验标准': d['description'], '检验维': d['key']} for d in active_dims])
    dim_keys = [d["key"] for d in active_dims]
    dim_template = ",\n".join(f'  {{"key": "{d["key"]}", "score": 100, "deduction": "", "passed": true/false, "detail": "具体检验意见..."}}' for d in active_dims)
    for attempt in range(1, max_retries + 1):
        if attempt > 1:
            await _asyncio.sleep(2)
            await broadcast(project_id, {"type": "progress", "message": f"🔄 hourong 第{attempt}次重新检验环境搭建结果..."})
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
            f"Role: 专业的环境搭建 QA 检验员（后荣）\n\n"
            f"=== 检验项目与标准 ===\n{dims_json}\n\n"
            f"=== 文档路径 ===\n{doc_path}\n\n"
             f"Task: 读取该文档文件，严格逐项检验环境搭建结果是否满足上述标准。\n"
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
                await broadcast(project_id, {"type": "progress", "message": f"⚠️ hourong 未返回检验结果，正在重试（第{attempt}次）"})
                continue
            return {"detail": f"后荣{max_retries}次均未返回检验结果（空响应）"}

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
            scores = [int(r.get("score", 100)) for r in parsed]
            avg_score = sum(scores) / len(scores)
            failed_details = [r.get("detail", "") for r in parsed if int(r.get("score", 100)) < 90]
            return {"passed": avg_score > 90, "score": avg_score, "total_score": sum(scores), "max_score": len(scores) * 100, "detail": "", "failed_details": failed_details, "results": parsed}

        logger.error(f"hourong 检验 JSON 解析失败 (attempt {attempt}/{max_retries}): {qa_r[:500]}")
        if attempt < max_retries:
            await broadcast(project_id, {"type": "progress", "message": f"⚠️ hourong 返回了无法解析的检验报告，正在重试（第{attempt}次）"})
            continue
        return {"detail": "后荣返回了无法解析的检验报告"}
    return {"detail": "后荣检验失败"}


# ── 执行环境搭建 ──

@router.post("/{project_id}/step5_2/execute")
async def execute_step5_2_async(project_id: str, db: Session = Depends(get_db), current_user=Depends(get_current_user), resume: bool = False):
    """异步启动第五步第二阶段：后富根据环境配置文件执行环境搭建，hourong 自动检验+收敛修复"""
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
        return APIResponse(code=1, message=f"无法开始步骤5_2: {str(e)[:200]}")
    step3 = engine.get_step3_artifacts() or {}
    step4 = engine.get_step4_artifacts() or {}
    step2 = engine.get_step2_artifacts() or {}
    core_goal = step2.get("confirmed_goal") or step2.get("core_goal") or ""
    step5_1 = engine.get_step5_artifacts() or {}
    env_config_path = step5_1.get("doc_path") or ""
    engine.save_step5_artifacts({"status": "generating", "message": "🔧 后富正在执行环境搭建..."})

    async def _generate():
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

                if resume and prev.get("qa_passed") and prev.get("setup_doc_path") and os.path.exists(prev["setup_doc_path"]):
                    await broadcast(project_id, {"type": "progress", "message": "♻️ 续跑：环境搭建已通过检验，跳过"})
                    bg_engine.save_step5_artifacts({**prev, "status": "done", "message": "♻️ 续跑：环境搭建已通过"})
                    bg_engine.complete_step(5)
                    await broadcast(project_id, {"type": "done", "message": "✅ 环境搭建已通过检验（续跑）"})
                    return

                # 续跑：如果上次中断在生成中，从上次的轮次继续
                if resume and saved_fix_round > 0 and not prev.get("qa_passed"):
                    await broadcast(project_id, {"type": "progress", "message": f"♻️ 续跑：从第{saved_fix_round}轮之后继续"})
                    fix_round = saved_fix_round
                    convergence_log = saved_convergence

                # 读取环境配置文件内容
                env_config_content = ""
                if env_config_path and os.path.exists(env_config_path):
                    with open(env_config_path, "r", encoding="utf-8") as f:
                        env_config_content = f.read()

                max_ver = 0
                for f in glob.glob(os.path.join(docs_dir, f"{slug}_env_setup_V*.md")):
                    import re as _re
                    m = _re.search(r'V(\d+)', os.path.basename(f))
                    if m:
                        max_ver = max(max_ver, int(m.group(1)))

                final_path, final_content = "", ""
                while True:
                    fix_round += 1
                    nv = max_ver + fix_round
                    gen_path = os.path.join(docs_dir, f"{slug}_env_setup_V{nv}.md")

                    # ── 持久化：记录当前轮次 ──
                    bg_engine.save_step5_artifacts({
                        "status": "generating",
                        "message": f"🔧 后富正在{'修复' if fix_round > 1 else '执行'}环境搭建（第{fix_round}轮）...",
                        "fix_round": fix_round,
                        "convergence": convergence_log,
                        "phase": "executing",
                    })
                    await broadcast(project_id, {"type": "progress", "message": f"🔧 后富正在{'修复' if fix_round > 1 else '执行'}环境搭建（第{fix_round}轮）..."})

                    feedback = ""
                    if fix_round > 1 and convergence_log:
                        last = convergence_log[-1]
                        failed = last.get("failed_details", [])
                        feedback = "需要修正的问题（只修复这些问题，禁止扩大范围）：\n" + "\n".join(f"- {d}" for d in failed if d)
                        await broadcast(project_id, {"type": "progress", "message": f"📋 hourong检验报告已发送给后富，正在修复..."})

                    prompt_lines = [
                        f"项目名称：{proj_name}",
                        f"核心目标：{core_goal}",
                        "",
                        "你是资深CI/CD工程师后富（HouFu），负责根据环境配置文件执行环境搭建。",
                        "",
                        f"【文件输出目录规则 - 必须遵守】",
                        f"你生成的所有文件必须保存到以下指定目录：",
                        f"  - 文档目录（正式产出物）: {docs_dir}",
                        f"  - 临时目录（中间产物）: {os.path.join(settings.PROJECTS_BASE_DIR, slug, settings.PROJECT_TMP_SUBDIR)}",
                        f"当 prompt 中指定了具体文件路径时，必须严格按该路径保存。",
                        f"不要将文件保存到当前工作目录或其他位置。",
                        "",
                        "=== 环境配置文件（step5_1产出） ===",
                        f"文件路径：{env_config_path}",
                        "",
                        "=== 环境配置内容 ===",
                        env_config_content[:3000] if env_config_content else "（未找到配置文件）",
                        "",
                        "【任务 - 仅执行环境搭建】",
                        "根据以上环境配置文件，执行完整的环境搭建，依次完成以下配置：",
                        "2.1. 代码仓库初始化（git init, .gitignore等）",
                        "2.2. 开发框架搭建（项目骨架、目录结构）",
                        "2.3. 依赖管理配置（package.json, requirements.txt等）",
                        "2.4. 数据库初始化（建表脚本、迁移工具配置）",
                        "2.5. CI/CD流水线配置（GitHub Actions, Jenkins等）",
                        "2.6. Docker化配置（Dockerfile, docker-compose.yml）",
                        "",
                        "每完成一项子任务，就保存状态，并回复进展。",
                        f"请将环境搭建报告保存到文件：{gen_path}",
                        "",
                        "【断点续做规则 - 必须遵守】",
                        "1. 每个子步骤有任何进展，必须立即持久化保存状态到文件",
                        "2. 每次执行前，必须先检查该文件路径是否已有已保存的内容",
                        "3. 若有已保存状态，必须从最新状态继续执行，不得重复已完成的工作",
                        "4. 保存格式：每个子步骤完成后，在文件末尾追加一行 `<!-- STEP_DONE: 步骤名 -->` 作为完成标记",
                        "5. 例如完成2.1后追加 `<!-- STEP_DONE: 2.1代码仓库初始化 -->`",
                        "",
                        "【重要】",
                        "1. 严格按照配置文件中的参数执行，不要自行修改配置",
                        "2. 不要输出思考过程",
                        "3. 只执行搭建操作，不要重新生成配置文件",
                    ]
                    if feedback:
                        prompt_lines.insert(18, "")
                        prompt_lines.insert(19, "=== 上次检验未通过项 ===")
                        prompt_lines.insert(20, feedback)
                        prompt_lines.insert(21, "")
                        prompt_lines.insert(22, "【修复要求】")
                        prompt_lines.insert(23, "1. 读取现有搭建报告")
                        prompt_lines.insert(24, "2. 只修改上述未通过项")
                        prompt_lines.insert(25, "3. 保持其他部分不变")
                        prompt_lines.insert(26, "4. 将修改后的完整报告保存到文件")
                    prompt = "\n".join(prompt_lines)

                    # ── 持久化：开始调用houfu ──
                    bg_engine.save_step5_artifacts({
                        "status": "generating",
                        "message": f"📤 正在调用后富执行环境搭建（第{fix_round}轮）...",
                        "fix_round": fix_round,
                        "convergence": convergence_log,
                        "phase": "calling_houfu",
                    })

                    await broadcast(project_id, {"type": "prompt", "prompt": prompt, "round": fix_round})
                    client = GatewayClient(profile_name="houfu", timeout=1200)
                    chunks = []
                    async for chunk in client.chat_completions(
                        messages=[{"role": "user", "content": prompt}],
                        stream=True, max_tokens=64000,
                    ):
                        if chunk.strip():
                            chunks.append(chunk)
                            await broadcast(project_id, {"type": "progress", "content": chunk})

                    if os.path.exists(gen_path):
                        with open(gen_path, "r", encoding="utf-8") as f:
                            content = f.read()
                    else:
                        content = "".join(chunks).strip()
                        with open(gen_path, "w", encoding="utf-8") as f:
                            f.write(content)

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
                        "setup_doc_path": gen_path,
                        "status": "generating",
                        "message": f"📝 搭建报告已生成（第{fix_round}轮），准备QA检验",
                        "fix_round": fix_round,
                        "convergence": convergence_log,
                        "phase": "qa_pending",
                    })

                    # hourong 检验
                    # ── 持久化：开始检验 ──
                    bg_engine.save_step5_artifacts({
                        "env_info": content,
                        "setup_doc_path": gen_path,
                        "status": "generating",
                        "message": f"🔍 hourong 正在检验环境搭建结果（第{fix_round}轮）...",
                        "fix_round": fix_round,
                        "convergence": convergence_log,
                        "phase": "qa_inspecting",
                    })
                    await broadcast(project_id, {"type": "progress", "message": f"🔍 hourong 正在检验环境搭建结果（文件：{gen_path}）"})

                    failed_keys = []
                    if fix_round > 1 and convergence_log:
                        last_results = convergence_log[-1].get("results", [])
                        if last_results:
                            failed_keys = [r.get("key", "") for r in last_results if int(r.get("score", 100)) < 90]
                    qa_result = await _inspect_env_setup(project_id, gen_path, project_name=proj_name, project_description=proj_desc, core_goal=core_goal, failed_keys=failed_keys if failed_keys else None)

                    # ── 持久化：检验完成，记录结果 ──
                    convergence_log.append({"round": fix_round, "detail": qa_result.get("detail", ""), "passed": qa_result.get("passed", False), "failed_details": qa_result.get("failed_details", []), "results": qa_result.get("results", [])})
                    bg_engine.save_step5_artifacts({
                        "env_info": content,
                        "setup_doc_path": gen_path,
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
                            "setup_doc_path": gen_path,
                            "convergence": convergence_log,
                            "status": "done",
                            "qa_passed": True,
                            "message": "✅ 环境搭建完成",
                            "fix_round": fix_round,
                            "phase": "completed",
                        })
                        bg_engine.complete_step(5)
                        await broadcast(project_id, {"type": "progress", "message": f"✅ 环境搭建已通过 hourong 检验（共{fix_round}轮）"})
                        await broadcast(project_id, {"type": "done", "message": "✅ 环境搭建已通过检验"})
                        return

                    # ── 持久化：未通过，准备修复 ──
                    bg_engine.save_step5_artifacts({
                        "env_info": content,
                        "setup_doc_path": gen_path,
                        "convergence": convergence_log,
                        "status": "generating",
                        "message": f"⚠️ 第{fix_round}轮未通过，准备修复",
                        "fix_round": fix_round,
                        "phase": "fixing",
                    })
                    await broadcast(project_id, {"type": "progress", "message": f"⚠️ 未通过，进入修复"})

                await broadcast(project_id, {"type": "progress", "message": f"🔄 第{fix_round}轮未通过，自动退回重做..."})
            except Exception as e:
                logger.error(f"Step5_2: {e}", exc_info=True)
                try:
                    bg_engine = WorkflowEngine(project_id=project_id, db=bg_db)
                    bg_engine.save_step5_artifacts({
                        "status": "error",
                        "message": f"失败: {str(e)[:200]}",
                        "fix_round": fix_round,
                        "convergence": convergence_log,
                    })
                    bg_engine.reset_step(5)
                except Exception as e2:
                    logger.error(f"Step5_2 failed to reset: {e2}", exc_info=True)
            finally:
                bg_db.close()
        except Exception as e:
            logger.error(f"Step5_2 fatal: {e}")
        finally:
            from app.services.haimei_executor import HaimeiStepExecutor
            HaimeiStepExecutor._tasks.pop(f"{project_id}:step5", None)

    task = _asyncio.create_task(_generate())
    from app.services.haimei_executor import HaimeiStepExecutor
    HaimeiStepExecutor._tasks[f"{project_id}:step5"] = task
    return APIResponse(code=0, data={"message": "步骤5_2已启动，后富正在执行环境搭建", "status": "generating"})


@router.post("/{project_id}/step5_2/reset")
def reset_step5_2(project_id: str, db: Session = Depends(get_db), current_user=Depends(get_current_user)):
    engine = _get_engine(project_id, db)
    engine.reset_step(5)
    _wf_engines.pop(project_id, None)
    return APIResponse(code=0, data={"message": "步骤5_2已重置"})


@router.get("/{project_id}/step5_2/status")
def get_step5_2_status(project_id: str, db: Session = Depends(get_db), current_user=Depends(get_current_user)):
    engine = _get_engine(project_id, db)
    return APIResponse(code=0, data=engine.get_step5_artifacts())


@router.post("/{project_id}/step5_2/artifacts")
def save_step5_2_artifacts_route(project_id: str, body: dict = Body(...), db: Session = Depends(get_db), current_user=Depends(get_current_user)):
    engine = _get_engine(project_id, db)
    engine.save_step5_artifacts(body)
    return APIResponse(code=0, data={"message": "步骤5_2状态已保存"})


@router.post("/{project_id}/step5_2/qa")
def qa_step5_2(project_id: str, body: QAResultRequest, db: Session = Depends(get_db), current_user=Depends(get_current_user)):
    engine = _get_engine(project_id, db)
    if body.result == "passed":
        result = engine.pass_qa(5)
    else:
        result = engine.fail_qa(5, reason=body.reason or "", suggestions=body.suggestions)
    return APIResponse(code=0, data={"message": f"步骤5_2 QA检验{'通过' if body.result == 'passed' else '未通过'}", "qa": result})
