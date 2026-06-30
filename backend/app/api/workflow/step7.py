from app.api.workflow.core import (
    router, _get_engine, logger, APIResponse, Depends, get_db,
    get_current_user, Session, Body, Request, HTTPException,
    BaseModel, Optional, asyncio, os, settings, Step3InspectRequest, QAResultRequest,
    TDD_TESTCASE_DIMENSIONS, Step7ChatRequest, _wf_engines, WorkflowEngine,
)


@router.post("/{project_id}/step7/chat")
async def step7_chat(project_id: str, body: Step7ChatRequest,
                     db: Session = Depends(get_db), current_user=Depends(get_current_user)):
    """后发（HouFa）对话 - 项目隔离"""
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
        reply_chunks = []
        async for chunk in client.chat_isolated(messages=messages, project_id=project_id, project_name=project.name, project_description=project.description or "", core_goal=core_goal, agent_name="后发（HouFa）程序员", stream=False):
            reply_chunks.append(chunk)
        reply = "".join(reply_chunks)
        if not reply or len(reply.strip()) < 5:
            return APIResponse(code=1, message="后发未生成有效回复", data=None)
        return APIResponse(code=0, message="success", data={"reply": reply})
    except HTTPException:
        raise
    except Exception as e:
        logger.error(f"Step7 chat: {e}")
        return APIResponse(code=1, message="与后发对话失败", data=None)


async def _inspect_tdd_cases(project_id: str, doc_path: str, project_name: str = "", project_description: str = "", core_goal: str = "", agent_label: str = "", max_retries: int = 3) -> dict:
    import json as _json, asyncio as _asyncio
    from app.services.gateway_client import GatewayClient
    from app.api.ws.step4_progress import broadcast
    dims_json = str([{'检验项目': d['label'], '检验标准': d['description'], '检验维': d['key']} for d in TDD_TESTCASE_DIMENSIONS])
    for attempt in range(1, max_retries + 1):
        if attempt > 1:
            await _asyncio.sleep(2)
            await broadcast(project_id, {"type": "step7", "message": f"🔄 hourong 第{attempt}次重新检验TDD用例..."})
        insp_prompt = f"你是一个专业的TDD测试用例QA检验员（后荣）。请严格检验以下测试用例。\n\n=== 检验项目与标准 ===\n{dims_json}\n\n=== 文档路径 ===\n{doc_path}\n\n请读取该文档文件，严格逐项检验。\n⚠️ 收敛性要求：检验报告必须聚焦于不合格项，明确指出不合格项的问题和修改方向。后续Agent将只修改不合格项，禁止扩大范围。已合格项目不得提出修改要求。\n只输出 JSON 数组，不要有其他文字:\n" + ",\n".join(f'  {{"key": "{d["key"]}", "passed": true/false, "detail": "具体检验意见..."}}' for d in TDD_TESTCASE_DIMENSIONS)
        qa_cli = GatewayClient(profile_name="hourong", timeout=180)
        qa_chunks = []
        async for chunk in qa_cli.chat_isolated(messages=[{"role": "user", "content": insp_prompt}], project_id=project_id, project_name=project_name, project_description=project_description, core_goal=core_goal, agent_name=agent_label or "后荣-TDD用例QA检验员", stream=True, max_tokens=8192):
            qa_chunks.append(chunk)
        qa_r = "".join(qa_chunks).strip()
        if not qa_r:
            if attempt < max_retries:
                await broadcast(project_id, {"type": "step7", "message": f"⚠️ hourong 未返回，重试（第{attempt}次）"})
                continue
            return {"detail": f"后荣{max_retries}次均未返回"}
        brace_s, brace_e = qa_r.find('['), qa_r.rfind(']') + 1
        if brace_s != -1 and brace_e > brace_s:
            qa_r = qa_r[brace_s:brace_e]
        try:
            parsed = _json.loads(qa_r)
        except Exception:
            if attempt < max_retries:
                await broadcast(project_id, {"type": "step7", "message": f"⚠️ hourong 格式异常，重试（第{attempt}次）"})
                continue
            return {"detail": "后荣未返回检验结果"}
        if isinstance(parsed, list) and parsed:
            return {"passed": all(bool(r.get("passed")) for r in parsed), "detail": "", "failed_details": [r.get("detail", "") for r in parsed if not r.get("passed")], "results": parsed}
        if attempt < max_retries:
            await broadcast(project_id, {"type": "step7", "message": f"⚠️ hourong 格式异常，重试（第{attempt}次）"})
            continue
        return {"detail": "后荣未返回检验结果"}
    return {"detail": "后荣检验失败"}


async def run_step7_swarm(
    project_id: str,
    requirement: str,
    design_doc: str,
    tdd_plan: str,
    core_goal: str,
    proj_name: str = "",
    proj_desc: str = "",
    existing: dict = None,
    resume: bool = False,
):
    """蜂群并行TDD测试用例生成（共享内部逻辑，同时供HTTP端点和海梅调度使用）"""
    import random, json, re, httpx
    from app.api.ws.step4_progress import broadcast
    from app.services.swarm_service import SwarmService
    from app.database import SessionLocal
    from app.models.project import Project

    bg_db = SessionLocal()
    try:
        bg_engine = WorkflowEngine(project_id=project_id, db=bg_db)
        proj = bg_db.query(Project).filter(Project.id == project_id).first()
        slug = proj.slug if proj else project_id.replace("-", "")
        docs_dir = os.path.join(settings.PROJECTS_BASE_DIR, slug, "docs")
        os.makedirs(docs_dir, exist_ok=True)
        proj_name = proj_name or (proj.name if proj else "")
        proj_desc = proj_desc or (proj.description or "")

        prev = existing or {}
        if resume and prev.get("qa_passed") and prev.get("tdd_cases"):
            await broadcast(project_id, {"type": "step7", "message": "♻️ 续跑：TDD用例已通过检验，跳过"})
            bg_engine.save_step7_artifacts({**prev, "status": "done", "message": "♻️ 续跑：TDD用例已通过"})
            bg_engine.complete_step(7)
            await broadcast(project_id, {"type": "done", "message": "✅ TDD用例已生成（续跑）"})
            return

        # ── Step 1: 后发解析TDD计划 → 原子测试用例任务清单 ──
        await broadcast(project_id, {"type": "step7", "message": "🧠 后发正在解析TDD计划，拆分为原子测试用例任务..."})
        parse_prompt = (
            "你是资深程序员后发（HouFa），负责将TDD测试用例计划拆分为原子测试用例任务。\n\n"
            f"=== 需求文档 ===\n{requirement}\n\n=== 架构设计 ===\n{design_doc}\n\n"
            f"=== TDD计划 ===\n{tdd_plan}\n\n"
            "请将上述TDD计划拆分为多个独立的原子测试用例任务。\n"
            "每个测试用例必须：1.最小原子化（只测一个功能点）2.有明确可量化的验收标准\n"
            "3.包含测试用例名称、描述、验收标准、所属模块\n"
            '只输出 JSON 数组，不要其他文字：\n'
            '[\n  {"name": "...", "description": "...", "acceptance_criteria": "...", "priority": 1, "module": "..."}\n]'
        )
        parse_client = GatewayClient(profile_name="houfa", timeout=300)
        parse_chunks = []
        async for chunk in parse_client.chat_isolated(
            messages=[{"role": "user", "content": parse_prompt}],
            project_id=project_id, project_name=proj_name, project_description=proj_desc,
            core_goal=core_goal, agent_name="后发-TDD任务解析", stream=False, max_tokens=16000,
        ):
            parse_chunks.append(chunk)
        parse_raw = "".join(parse_chunks).strip()
        bs = parse_raw.find('[')
        be = parse_raw.rfind(']') + 1
        if bs != -1 and be > bs:
            parse_raw = parse_raw[bs:be]
        try:
            subtasks = json.loads(parse_raw)
            if not isinstance(subtasks, list) or len(subtasks) == 0:
                raise ValueError
        except Exception:
            bg_engine.save_step7_artifacts({"status": "error", "message": "❌ TDD计划解析失败"})
            await broadcast(project_id, {"type": "error", "message": "❌ 后发解析TDD计划失败"})
            return

        await broadcast(project_id, {"type": "step7", "message": f"📋 TDD计划已拆分为 {len(subtasks)} 个原子测试用例"})

        # ── Step 2: 从DB获取在线Agent ──
        writer_agents = SwarmService.get_online_writer_agents(bg_db)
        tester_agents = SwarmService.get_online_tester_agents(bg_db)
        if not writer_agents:
            bg_engine.save_step7_artifacts({"status": "error", "message": "❌ 没有可用的编写Agent"})
            await broadcast(project_id, {"type": "error", "message": "❌ 没有可用的编写Agent"})
            return
        if not tester_agents:
            bg_engine.save_step7_artifacts({"status": "error", "message": "❌ 没有可用的测试Agent"})
            await broadcast(project_id, {"type": "error", "message": "❌ 没有可用的测试Agent"})
            return

        await broadcast(project_id, {"type": "step7", "message": f"🐝 蜂群就绪：{len(writer_agents)}个编写Agent + {len(tester_agents)}个测试Agent, {len(subtasks)}个子任务"})

        # ── Step 3: 创建蜂群 ──
        swarm_svc = SwarmService()
        swarm = swarm_svc.create_swarm(
            project_id=project_id,
            name=f"TDD-Swarm-{slug[:8]}",
            purpose="code_writing",
            step_number=7,
            manager_role="houfa",
        )
        for wa in writer_agents:
            try:
                swarm_svc.add_member(swarm["id"], wa.agent_type, wa.id)
            except ValueError:
                pass

        # ── Step 4: 通用Agent调用辅助函数（自动对接第3方编程Agent） ──
        async def _call_agent(agent, prompt_text, timeout=600):
            cfg = agent.config or {}
            api_key = cfg.get("api_key") or cfg.get("apiKey")
            model = cfg.get("model") or "default"

            # 路径1: 直接通过 OpenAI 兼容 API 调用（支持 Claude Code / Codex / Pi / Opencode / Reasonix 等）
            if agent.api_endpoint:
                ep = agent.api_endpoint.rstrip("/")
                headers = {"Content-Type": "application/json"}
                if api_key:
                    headers["Authorization"] = f"Bearer {api_key}"

                last_err = None
                for attempt in range(1, 4):
                    try:
                        async with httpx.AsyncClient(timeout=httpx.Timeout(timeout)) as hc:
                            resp = await hc.post(
                                f"{ep}/v1/chat/completions",
                                headers=headers,
                                json={
                                    "model": model,
                                    "messages": [{"role": "user", "content": prompt_text}],
                                    "max_tokens": 32000,
                                    "temperature": 0.7,
                                },
                            )
                            if resp.status_code == 401:
                                logger.warning(f"Step7 agent {agent.name} ({agent.agent_type}) API key rejected at {ep}")
                                break
                            resp.raise_for_status()
                            content = resp.json().get("choices", [{}])[0].get("message", {}).get("content", "")
                            if content.strip():
                                logger.info(f"Step7 agent {agent.name} ({agent.agent_type}) responded via {ep}")
                                return content
                    except httpx.TimeoutException as e:
                        last_err = e
                        logger.warning(f"Step7 agent {agent.name} timeout (attempt {attempt}/3): {ep}")
                        await asyncio.sleep(2 ** attempt)
                    except httpx.ConnectError as e:
                        last_err = e
                        logger.warning(f"Step7 agent {agent.name} unreachable (attempt {attempt}/3): {ep}")
                        await asyncio.sleep(2 ** attempt)
                    except Exception as e:
                        last_err = e
                        logger.warning(f"Step7 agent {agent.name} error (attempt {attempt}/3): {e}")
                        await asyncio.sleep(2 ** attempt)

                if last_err:
                    logger.info(f"Step7 agent {agent.name} direct API failed after 3 attempts, falling back to GatewayClient")

            # 路径2: 通过 Hermes Gateway 调用（使用 role_name 或 agent_type 作为 profile）
            profile = agent.role_name or agent.agent_type
            try:
                gc = GatewayClient(profile_name=profile, timeout=timeout)
                gc_chunks = []
                async for chunk in gc.chat_isolated(
                    messages=[{"role": "user", "content": prompt_text}],
                    project_id=project_id, project_name=proj_name, project_description=proj_desc,
                    core_goal=core_goal, agent_name=agent.name, stream=False, max_tokens=32000,
                ):
                    gc_chunks.append(chunk)
                reply = "".join(gc_chunks)
                if reply.strip():
                    logger.info(f"Step7 agent {agent.name} responded via GatewayClient profile={profile}")
                    return reply
            except Exception as e:
                logger.warning(f"Step7 agent {agent.name} GatewayClient failed: {e}")

            logger.error(f"Step7 agent {agent.name} ({agent.agent_type}) all call paths failed")
            return ""

        # ── Step 5: 并行执行子任务 ──
        sem = asyncio.Semaphore(min(12, len(subtasks)))
        writer_idx = 0
        tester_idx = 0
        wlock = asyncio.Lock()
        tlock = asyncio.Lock()
        all_results = []
        rlock = asyncio.Lock()

        async def _run_subtask(st, idx):
            nonlocal writer_idx, tester_idx
            async with sem:
                sname = st.get("name", f"用例{idx}")
                sdesc = st.get("description", "")
                sacc = st.get("acceptance_criteria", "")
                file_path = os.path.join(docs_dir, f"{slug}_tdctask_{idx:04d}.md")
                try:
                    for attempt in range(1, 6):
                        async with wlock:
                            wi = writer_idx % len(writer_agents)
                            writer_idx += 1
                        writer = writer_agents[wi]

                        await broadcast(project_id, {"type": "step7", "message": f"✍️ [{sname}] {writer.name} 编写（第{attempt}轮）..."})

                        fb = ""
                        if attempt > 1 and st.get("last_feedback"):
                            fb = f"\n\n=== 上次测试反馈（仅修复这些问题）===\n{st['last_feedback']}"

                        wp = (
                            f"你{writer.name}，负责编写TDD测试用例代码。\n\n"
                            f"=== 需求 ===\n{requirement[:3000]}\n=== 架构 ===\n{design_doc[:2000]}\n"
                            f"=== 测试用例 ===\n名称：{sname}\n描述：{sdesc}\n验收标准：{sacc}\n"
                            f"直接输出完整测试代码（含import）。不要推理过程。{fb}"
                        )
                        code = await _call_agent(writer, wp)
                        if not code.strip():
                            continue

                        with open(file_path, "w") as f:
                            f.write(code)

                        async with tlock:
                            ti = tester_idx % len(tester_agents)
                            tester_idx += 1
                        tester = tester_agents[ti]

                        await broadcast(project_id, {"type": "step7", "message": f"🔍 [{sname}] {tester.name} 验证中..."})

                        tp = (
                            f"你{tester.name}，负责验证TDD测试用例代码。\n\n"
                            f"=== 验收标准 ===\n{sacc}\n=== 测试代码 ===\n{code}\n\n"
                            "严格验证：语法正确性、逻辑是否符合验收标准、边界覆盖、可独立运行。\n"
                            "第一行输出 PASS 或 FAIL，然后详细说明问题。"
                        )
                        tr = await _call_agent(tester, tp)

                        if tr.strip().startswith("PASS"):
                            async with rlock:
                                all_results.append({"name": sname, "index": idx, "status": "passed", "file_path": file_path, "attempts": attempt, "writer": writer.name, "tester": tester.name})
                            await broadcast(project_id, {"type": "step7", "message": f"✅ [{sname}] 通过（第{attempt}轮）"})
                            return
                        else:
                            st["last_feedback"] = tr
                            await broadcast(project_id, {"type": "step7", "message": f"⚠️ [{sname}] 未通过（第{attempt}轮）"})

                    async with rlock:
                        all_results.append({"name": sname, "index": idx, "status": "failed", "file_path": file_path, "attempts": 5})
                    await broadcast(project_id, {"type": "step7", "message": f"❌ [{sname}] 5轮均未通过"})
                except Exception as e:
                    logger.error(f"Step7 subtask {idx} ({sname}) exception: {e}")
                    async with rlock:
                        all_results.append({"name": sname, "index": idx, "status": "failed", "file_path": "", "attempts": 5, "error": str(e)[:200]})
                    await broadcast(project_id, {"type": "step7", "message": f"💥 [{sname}] 执行异常: {str(e)[:100]}"})

        await asyncio.gather(*[_run_subtask(st, i + 1) for i, st in enumerate(subtasks)])

        passed = [r for r in all_results if r["status"] == "passed"]
        failed_ = [r for r in all_results if r["status"] == "failed"]
        await broadcast(project_id, {"type": "step7", "message": f"📊 子任务完成：{len(passed)}通过 / {len(failed_)}失败"})

        # ── Step 6: hourong 1% 随机抽检 ──
        spot_checked = []
        if passed:
            sample_size = max(1, len(passed) // 100)
            sampled = random.sample(passed, min(sample_size, len(passed)))
            for s in sampled:
                if os.path.exists(s["file_path"]):
                    insp = await _inspect_tdd_cases(
                        project_id, s["file_path"],
                        project_name=proj_name, project_description=proj_desc, core_goal=core_goal,
                    )
                    if insp.get("passed"):
                        spot_checked.append({**s, "spot_check": "passed"})
                    else:
                        spot_checked.append({**s, "spot_check": "failed", "detail": insp.get("detail", "")})
                else:
                    spot_checked.append({**s, "spot_check": "skipped"})

        spot_failures = [s for s in spot_checked if s.get("spot_check") == "failed"]

        # ── Step 7: 汇总保存 ──
        combined = "\n\n---\n\n".join(
            f"# {r['name']}\n\n{open(r['file_path']).read()}"
            if r.get("file_path") and os.path.exists(r["file_path"]) else f"# {r['name']}\n\n(失败)"
            for r in all_results
        )
        final_ok = len(failed_) == 0 and len(spot_failures) == 0
        final_msg = (
            f"✅ TDD蜂群编写完成：{len(passed)}通过/{len(failed_)}失败"
            + (f"，抽检{len(spot_failures)}项不合格" if spot_failures else "，抽检全部合格")
        )

        bg_engine.save_step7_artifacts({
            "swarm_summary": {"total": len(subtasks), "passed": len(passed), "failed": len(failed_), "spot_checked": len(spot_checked), "spot_failures": len(spot_failures)},
            "subtask_results": all_results,
            "spot_check_results": spot_checked,
            "tdd_cases": combined,
            "status": "done" if final_ok else "error",
            "message": final_msg,
            "qa_passed": final_ok,
        })

        if final_ok:
            bg_engine.complete_step(7)
            await broadcast(project_id, {"type": "done", "message": final_msg})
        else:
            bg_engine.reset_step(7)
            await broadcast(project_id, {"type": "error", "message": f"❌ {len(failed_)}个子任务失败，{len(spot_failures)}个抽检不合格"})

    except Exception as e:
        logger.error(f"Step7: {e}")
        try:
            bg_engine = WorkflowEngine(project_id=project_id, db=bg_db)
            bg_engine.save_step7_artifacts({"status": "error", "message": f"失败: {str(e)[:200]}"})
            bg_engine.reset_step(7)
        except Exception:
            pass
    finally:
        bg_db.close()


@router.post("/{project_id}/step7/execute")
async def execute_step7_async(project_id: str, db: Session = Depends(get_db), current_user=Depends(get_current_user), resume: bool = False):
    """异步启动第七步：后发蜂群并行编写TDD测试用例，hourong 1%抽检"""
    import asyncio as _asyncio
    try:
        engine = _get_engine(project_id, db)
        if resume:
            existing = engine.get_step7_artifacts() or {}
        else:
            step7_row = engine._get_step_row(7)
            if step7_row and step7_row.status == "in_progress":
                engine.reset_step(7)
                engine = WorkflowEngine(project_id=project_id, db=db)
                _wf_engines[project_id] = engine
            engine.advance_step(7)
            existing = {}
    except Exception as e:
        return APIResponse(code=1, message=f"无法开始步骤7: {str(e)[:200]}")
    step3 = engine.get_step3_artifacts() or {}
    requirement = (step3.get("doc_content") or step3.get("content") or step3.get("requirement") or step3.get("srs") or "")
    step4 = engine.get_step4_artifacts() or {}
    design_doc = step4.get("design_doc") or ""
    step6 = engine.get_step6_artifacts() or {}
    tdd_plan = step6.get("tdd_plan") or step6.get("plan_content") or ""
    step2 = engine.get_step2_artifacts() or {}
    core_goal = step2.get("confirmed_goal") or step2.get("core_goal") or ""
    engine.save_step7_artifacts({"status": "generating", "message": "🐝 后发正在组建蜂群并行编写TDD测试用例..."})

    async def _generate():
        await run_step7_swarm(
            project_id=project_id,
            requirement=requirement,
            design_doc=design_doc,
            tdd_plan=tdd_plan,
            core_goal=core_goal,
            existing=existing if resume else None,
            resume=resume,
        )
    _asyncio.create_task(_generate())
    return APIResponse(code=0, data={"message": "第七步已启动", "status": "generating"})


@router.post("/{project_id}/step7/reset")
def reset_step7(project_id: str, db: Session = Depends(get_db), current_user=Depends(get_current_user)):
    engine = _get_engine(project_id, db)
    engine.reset_step(7)
    _wf_engines.pop(project_id, None)
    return APIResponse(code=0, data={"message": "第七步已重置"})


@router.get("/{project_id}/step7/status")
def get_step7_status(project_id: str, db: Session = Depends(get_db), current_user=Depends(get_current_user)):
    engine = _get_engine(project_id, db)
    return APIResponse(code=0, data=engine.get_step7_artifacts())


@router.post("/{project_id}/step7/artifacts")
def save_step7_artifacts_route(project_id: str, body: dict = Body(...), db: Session = Depends(get_db), current_user=Depends(get_current_user)):
    engine = _get_engine(project_id, db)
    engine.save_step7_artifacts(body)
    return APIResponse(code=0, data={"message": "步骤7状态已保存"})


@router.post("/{project_id}/step7/inspect")
async def inspect_step7(project_id: str, body: Step3InspectRequest, db: Session = Depends(get_db), current_user=Depends(get_current_user)):
    from app.services.gateway_client import GatewayClient
    import json as _json
    content, focus_items = body.content, body.focus_items
    if not content or len(content.strip()) < 20:
        return APIResponse(code=0, data={"passed": False, "dimensions": [{"key": d["key"], "passed": False} for d in TDD_TESTCASE_DIMENSIONS]})
    active_dims = [d for d in TDD_TESTCASE_DIMENSIONS if not focus_items or d["key"] in focus_items]
    dims_json = _json.dumps([{'检验项目': d['label'], '检验标准': d['description']} for d in active_dims], ensure_ascii=False, indent=2)
    focus_hint = f"\n⚠️ 本次只检验：{[d['label'] for d in active_dims]}" if focus_items else ""
    convergence_hint = "\n⚠️ 收敛性要求：检验报告必须聚焦于不合格项，明确指出不合格项的问题和修改方向。后续Agent将只修改不合格项，禁止扩大范围。已合格项目不得提出修改要求。"
    prompt = f"你是一个专业的TDD测试用例QA检验员（后荣）。\n\n=== TDD用例 ===\n{content}\n\n=== 检验项目 ===\n{dims_json}\n{focus_hint}\n{convergence_hint}\n\n直接输出 JSON 数组：\n[\n" + ",\n".join(f'  {{"key": "{d["key"]}", "passed": true/false, "detail": "..."}}' for d in active_dims) + "\n]"
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


@router.post("/{project_id}/step7/qa")
def qa_step7(project_id: str, body: QAResultRequest, db: Session = Depends(get_db), current_user=Depends(get_current_user)):
    engine = _get_engine(project_id, db)
    if body.result == "passed":
        result = engine.pass_qa(7)
    else:
        result = engine.fail_qa(7, reason=body.reason or "", suggestions=body.suggestions)
    return APIResponse(code=0, data={"message": f"第七步QA{'通过' if body.result == 'passed' else '未通过'}", "qa": result})