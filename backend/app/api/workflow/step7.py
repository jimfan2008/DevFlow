from app.api.workflow.core import (
    router, _get_engine, logger, APIResponse, Depends, get_db,
    get_current_user, Session, Body, Request, HTTPException,
    BaseModel, Optional, asyncio, os, settings, Step3InspectRequest, QAResultRequest,
    TDD_TESTCASE_DIMENSIONS, Step7ChatRequest, _wf_engines, WorkflowEngine,
)
from app.services.gateway_client import GatewayClient
from app.api.ws.step7_progress import broadcast
from app.api.ws.step3_qa import _inspect_via_subagent


@router.post("/{project_id}/step7/chat")
async def step7_chat(project_id: str, body: Step7ChatRequest,
                     db: Session = Depends(get_db), current_user=Depends(get_current_user)):
    """后发（HouFa）对话 - 项目隔离"""
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
        async for chunk in client.chat_isolated(messages=messages, project_id=project_id, project_name=project.name, project_description=project.description or "", core_goal=core_goal, agent_name="后发（HouFa）程序员", stream=False, project_slug=project.slug if project.slug else project_id):
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
    dims_json = str([{'检验项目': d['label'], '检验标准': d['description'], '检验维': d['key']} for d in TDD_TESTCASE_DIMENSIONS])
    for attempt in range(1, max_retries + 1):
        if attempt > 1:
            await _asyncio.sleep(2)
            await broadcast(project_id, {"type": "step7", "message": f"🔄 hourong 第{attempt}次重新检验TDD用例..."})
        insp_prompt = f"你是一个专业的TDD测试用例QA检验员（后荣）。请严格检验以下测试用例。\n\n=== 检验项目与标准 ===\n{dims_json}\n\n=== 文档路径 ===\n{doc_path}\n\n请读取该文档文件，严格逐项检验。\n⚠️ 收敛性要求：检验报告必须聚焦于不合格项，明确指出不合格项的问题和修改方向。后续Agent将只修改不合格项，禁止扩大范围。已合格项目不得提出修改要求。\n评分规则：每个检验维起始100分，每发现一个缺陷扣减相应分数（轻微缺陷扣5-10分，一般缺陷扣15-20分，严重缺陷扣25-30分）。维度得分≥90则该维度passed为true。所有维度平均分>90分为整体合格。\n只输出 JSON 数组，不要有其他文字:\n" + ",\n".join(f'  {{"key": "{d["key"]}", "score": 100, "deduction": "", "passed": true/false, "detail": "具体检验意见..."}}' for d in TDD_TESTCASE_DIMENSIONS)
        qa_r = await _inspect_via_subagent(prompt=insp_prompt, max_retries=max_retries)
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
            scores = [int(r.get("score", 100)) for r in parsed]
            avg_score = sum(scores) / len(scores)
            return {"passed": avg_score > 90, "score": avg_score, "total_score": sum(scores), "max_score": len(scores) * 100, "detail": "", "failed_details": [r.get("detail", "") for r in parsed if int(r.get("score", 100)) < 90], "results": parsed}
        if attempt < max_retries:
            await broadcast(project_id, {"type": "step7", "message": f"⚠️ hourong 格式异常，重试（第{attempt}次）"})
            continue
        return {"detail": "后荣未返回检验结果"}
    return {"detail": "后荣检验失败"}


def _load_tdd_cases_from_db(bg_db, project_id: str) -> tuple[list[dict], str]:
    """从数据库加载所有轮次的TDD测试用例，按case_id去重保留最新版本"""
    from app.models.tdd_test_case import TDDTestCase
    from sqlalchemy import func

    all_cases = bg_db.query(TDDTestCase).filter(
        TDDTestCase.project_id == project_id,
    ).order_by(TDDTestCase.round_number.desc(), TDDTestCase.case_index).all()

    if not all_cases:
        return [], ""

    seen = {}
    for c in all_cases:
        cid = c.case_id
        if cid not in seen:
            seen[cid] = c.to_dict()

    cases_data = list(seen.values())
    import json as _j
    cases_json = _j.dumps(cases_data, ensure_ascii=False, indent=2)
    return cases_data, cases_json


def _parse_priority(p: str) -> int:
    if not p:
        return 2
    p = p.upper().strip()
    if "P0" in p:
        return 0
    if "P1" in p:
        return 1
    if "P2" in p:
        return 2
    if "P3" in p:
        return 3
    return 2


async def run_step7_swarm(
    project_id: str,
    requirement: str,
    design_doc: str,
    core_goal: str,
    proj_name: str = "",
    proj_desc: str = "",
    existing: dict = None,
    resume: bool = False,
    requirement_path: str = "",
):
    """蜂群并行TDD测试用例生成（共享内部逻辑，同时供HTTP端点和海梅调度使用）"""
    import random, json, re, httpx
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

        # ── 补全前置步骤（如缺失） ──
        if not design_doc and requirement:
            await broadcast(project_id, {"type": "step7", "message": "📄 架构设计缺失，正在自动生成..."})
            req_ref = f"\n\n=== 需求文档路径 ===\n{requirement_path}\n" if requirement_path else ""
            try:
                dd_client = GatewayClient(profile_name="houfa", timeout=300)
                dd_prompt = f"你是资深架构师后旺（HouWang）。{req_ref}请阅读需求文档（如果提供了路径），输出一份简洁的架构设计文档。\n\n输出设计文档，包含：1.整体架构 2.模块划分 3.数据流 4.关键技术选型"
                dd_chunks = []
                async for chunk in dd_client.chat_isolated(messages=[{"role": "user", "content": dd_prompt}], project_id=project_id, project_name=proj_name, project_description=proj_desc, core_goal=core_goal, agent_name="后旺-架构设计自动补全", stream=False, max_tokens=8000, project_slug=slug):
                    dd_chunks.append(chunk)
                design_doc = "".join(dd_chunks).strip()
                bg_engine.save_step4_artifacts({"design_doc": design_doc, "auto_generated": True})
                await broadcast(project_id, {"type": "step7", "message": "📄 架构设计已自动生成"})
            except Exception as e:
                logger.warning(f"Auto-generate design_doc failed: {e}")
                design_doc = f"基于需求的架构设计{req_ref}"

        # ── Step 1: 从数据库读取TDD测试用例计划，重建计划文本 ──
        await broadcast(project_id, {"type": "step7", "message": "📋 从数据库读取TDD测试用例计划..."})
        db_cases, db_cases_json = _load_tdd_cases_from_db(bg_db, project_id)
        if not db_cases:
            await broadcast(project_id, {"type": "step7", "message": "📋 数据库无TDD测试用例，根据需求自动生成..."})
            try:
                tp_client = GatewayClient(profile_name="houfa", timeout=1200)
                req_ref = f"\n\n=== 需求文档路径 ===\n{requirement_path}\n" if requirement_path else ""
                tp_prompt = f"你是资深测试工程师海梅（HaiMei）。{req_ref}请阅读需求文档（如果提供了路径），基于以下架构设计，输出一份TDD测试用例计划。\n\n=== 架构 ===\n{design_doc}\n\n输出TDD计划，列出需要编写的测试用例类型和覆盖范围。"
                tp_chunks = []
                async for chunk in tp_client.chat_isolated(
                    messages=[{"role": "user", "content": tp_prompt}],
                    project_id=project_id, project_name=proj_name, project_description=proj_desc,
                    core_goal=core_goal, agent_name="海梅-TDD计划自动补全", stream=False, max_tokens=8000,
                    project_slug=slug,
                ):
                    tp_chunks.append(chunk)
                tdd_plan_content = "".join(tp_chunks).strip()
                await broadcast(project_id, {"type": "step7", "message": "📋 TDD计划已自动生成"})
            except Exception as e:
                err_msg = f"自动生成TDD计划失败: {str(e)[:200]}"
                logger.error(err_msg)
                bg_engine.save_step7_artifacts({"status": "error", "message": err_msg})
                await broadcast(project_id, {"type": "error", "message": f"❌ {err_msg}"})
                return
        else:
            lines = ["# TDD测试用例计划\n", f"## 总览\n\n共 {len(db_cases)} 个测试用例\n"]
            for c in db_cases:
                lines.append(f"\n### [{c.get('case_id','')}] {c.get('title','')}\n")
                lines.append(f"- **描述**: {c.get('description','无')}\n")
                lines.append(f"- **前置条件**: {c.get('precondition','无')}\n")
                lines.append(f"- **测试步骤**: {c.get('test_steps','无')}\n")
                lines.append(f"- **预期结果**: {c.get('expected_result','无')}\n")
                lines.append(f"- **优先级**: {c.get('priority','P2')}\n")
                lines.append(f"- **分类**: {c.get('category','无')}\n")
            tdd_plan_content = "\n".join(lines)
            await broadcast(project_id, {"type": "step7", "message": f"📋 从数据库加载 {len(db_cases)} 个TDD测试用例"})

        # 将TDD计划推送到前端展示
        await broadcast(project_id, {"type": "tdd_plan", "content": tdd_plan_content, "message": "📄 TDD计划已获取"})

        # ── Step 2: houfa按一个测试用例一个任务的方式转换为TODO LIST ──
        await broadcast(project_id, {"type": "step7", "message": "🤖 houfa正在将TDD计划转换为TODO LIST..."})

        async def _extract_json_array(text: str) -> list | None:
            import re as _re
            candidates = []
            # 策略1: 代码块提取
            fenced = _re.findall(r'```(?:json)?\s*\n?(.*?)\n?```', text, _re.DOTALL)
            for fc in fenced:
                s = fc.strip()
                if s.startswith('['):
                    candidates.append(s)
            # 策略2: 直接花括号/方括号提取
            bs = text.find('[')
            be = text.rfind(']') + 1
            if bs != -1 and be > bs:
                candidates.append(text[bs:be])
            # 策略3: 剥离空格后试试
            stripped = text.strip()
            if stripped.startswith('['):
                candidates.append(stripped)
            candidates.append(text)
            for c in candidates:
                # 去尾逗号
                c = _re.sub(r',\s*([\]}])', r'\1', c)
                try:
                    parsed = json.loads(c)
                    if isinstance(parsed, list) and len(parsed) > 0 and all(isinstance(x, dict) for x in parsed):
                        return parsed
                except Exception:
                    continue
            return None

        async def _fallback_split_tasks(plan_text: str) -> list:
            rows = []
            for line in plan_text.split('\n'):
                line = line.strip()
                if line.startswith('### ['):
                    import re as _re
                    m = _re.match(r'### \[([^\]]+)\]\s*(.*)', line)
                    if m:
                        case_id = m.group(1)
                        title = m.group(2)
                        rows.append({"name": title or f"用例{case_id}", "description": "", "acceptance_criteria": ""})
            return rows

        subtasks = []
        for conv_attempt in range(1, 4):
            try:
                houfa_client = GatewayClient(profile_name="houfa", timeout=600)
                convert_prompt = (
                    "你是资深测试工程师后发（HouFa）。请将以下TDD测试用例编写计划，按一个测试用例一个任务的方式，"
                    "转换为TODO LIST。\n\n"
                    f"=== TDD计划 ===\n{tdd_plan_content[:12000]}\n\n"
                    "输出格式为JSON数组，每个元素包含：\n"
                    '{"name": "测试用例名称", "description": "测试步骤描述", "acceptance_criteria": "验收标准"}\n'
                    "示例：\n"
                    '[{"name": "用户登录测试", "description": "测试用户使用正确密码登录", "acceptance_criteria": "登录成功并跳转到首页"},'
                    '{"name": "注册验证测试", "description": "测试使用无效邮箱注册", "acceptance_criteria": "提示邮箱格式错误"}]\n'
                    "只输出JSON数组，不要任何其他文字。"
                )
                convert_chunks = []
                async for chunk in houfa_client.chat_isolated(
                    messages=[{"role": "user", "content": convert_prompt}],
                    project_id=project_id, project_name=proj_name, project_description=proj_desc,
                    core_goal=core_goal, agent_name="后发-TDD计划转换", stream=False, max_tokens=12000,
                    project_slug=slug,
                ):
                    convert_chunks.append(chunk)
                convert_reply = "".join(convert_chunks).strip()
                parsed = await _extract_json_array(convert_reply)
                if parsed:
                    subtasks = parsed
                    await broadcast(project_id, {"type": "step7", "message": f"✅ houfa第{conv_attempt}次转换成功，共{len(subtasks)}个任务"})
                    break
                else:
                    logger.warning(f"houfa转换TDD计划第{conv_attempt}次: 无法解析JSON, 原始回复前300字: {convert_reply[:300]}")
                    raise ValueError("houfa未返回合法JSON数组")
            except Exception as e:
                logger.warning(f"houfa转换TDD计划第{conv_attempt}次失败: {e}")
                if conv_attempt < 3:
                    await broadcast(project_id, {"type": "step7", "message": f"🔄 houfa转换失败（第{conv_attempt}次），正在重试..."})
                    import asyncio as _asyncio
                    await _asyncio.sleep(2)
                else:
                    await broadcast(project_id, {"type": "step7", "message": "⚠️ houfa 3次均未能生成TODO LIST，使用文本回退方案..."})
                    subtasks = await _fallback_split_tasks(tdd_plan_content)
                    if subtasks:
                        await broadcast(project_id, {"type": "step7", "message": f"✅ 文本回退方案成功，共{len(subtasks)}个任务"})
                        break
                    else:
                        err_msg = "houfa 3次尝试均未能生成TODO LIST且文本回退也失败"
                        logger.error(err_msg)
                        bg_engine.save_step7_artifacts({"status": "error", "message": err_msg})
                        await broadcast(project_id, {"type": "error", "message": f"❌ {err_msg}"})
                        return

        if not subtasks:
            await broadcast(project_id, {"type": "step7", "message": "⚠️ TODO LIST为空，使用文本回退方案..."})
            subtasks = await _fallback_split_tasks(tdd_plan_content)
            if not subtasks:
                err_msg = "无法生成TODO LIST：TDD计划中未找到任何测试用例"
                bg_engine.save_step7_artifacts({"status": "error", "message": err_msg})
                await broadcast(project_id, {"type": "error", "message": f"❌ {err_msg}"})
                return

        subtask_names = [st.get("name", f"用例{i+1}") for i, st in enumerate(subtasks)]
        await broadcast(project_id, {"type": "step7", "subtask_names": subtask_names, "message": f"📋 TODO LIST已生成：{len(subtasks)} 个测试用例任务"})

        # ── 并行参数 ──
        PARALLEL_WRITERS = 5
        PARALLEL_TESTERS = 2

        # ── Step 2: 获取编程Agent，按偏好排序（PI > OpenCode > 其他; Reasonix > Claude Code > 其他） ──
        writer_agents = SwarmService.get_preferred_writer_agents(bg_db)
        tester_agents = SwarmService.get_preferred_tester_agents(bg_db)
        if not writer_agents:
            bg_engine.save_step7_artifacts({"status": "error", "message": "❌ 没有可用的编写Agent（请注册PI/OpenCode等编程Agent）"})
            await broadcast(project_id, {"type": "error", "message": "❌ 没有可用的编写Agent"})
            return
        if not tester_agents:
            bg_engine.save_step7_artifacts({"status": "error", "message": "❌ 没有可用的测试Agent（请注册Reasonix/Claude Code等测试Agent）"})
            await broadcast(project_id, {"type": "error", "message": "❌ 没有可用的测试Agent"})
            return

        for wa in writer_agents:
            await broadcast(project_id, {"type": "agent_online", "name": wa.name, "role": "writer", "agent_type": wa.agent_type})
        for ta in tester_agents:
            await broadcast(project_id, {"type": "agent_online", "name": ta.name, "role": "tester", "agent_type": ta.agent_type})
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

        # ── Step 4: 通用Agent调用辅助函数 ──
        async def _call_agent(agent, prompt_text, timeout=600):
            cfg = agent.config or {}
            api_key = cfg.get("api_key") or cfg.get("apiKey")
            model = cfg.get("model") or "default"

            cli_cmd = cfg.get("cli_command") or agent.api_endpoint
            if cli_cmd and not cli_cmd.startswith("http"):
                import shlex
                prompt_quoted = shlex.quote(prompt_text)
                if "{prompt}" in cli_cmd:
                    full_cmd = cli_cmd.replace("{prompt}", prompt_quoted)
                else:
                    full_cmd = f"{cli_cmd} {prompt_quoted}"
                cmd_parts = shlex.split(full_cmd)
                for attempt in range(1, 4):
                    try:
                        proc = await asyncio.create_subprocess_exec(
                            *cmd_parts,
                            stdout=asyncio.subprocess.PIPE,
                            stderr=asyncio.subprocess.PIPE,
                        )
                        out_bytes, err_bytes = await asyncio.wait_for(
                            proc.communicate(), timeout=timeout,
                        )
                        if proc.returncode == 0:
                            text = out_bytes.decode().strip() if out_bytes else ""
                            if text:
                                logger.info(f"Step7 agent {agent.name} responded via CLI: {cli_cmd}")
                                return text
                        else:
                            err = (err_bytes.decode().strip() if err_bytes else "")[:500]
                            logger.warning(f"Step7 agent {agent.name} CLI exit {proc.returncode} (attempt {attempt}/3): {err}")
                    except asyncio.TimeoutError:
                        logger.warning(f"Step7 agent {agent.name} CLI timeout (attempt {attempt}/3)")
                    except Exception as e:
                        logger.warning(f"Step7 agent {agent.name} CLI error (attempt {attempt}/3): {e}")
                    await asyncio.sleep(2 ** attempt)
                logger.error(f"Step7 agent {agent.name} CLI all attempts failed")
                return ""

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

            profile = agent.role_name or agent.name or agent.agent_type
            try:
                gc = GatewayClient(profile_name=profile, timeout=timeout)
                gc_chunks = []
                async for chunk in gc.chat_isolated(
                    messages=[{"role": "user", "content": prompt_text}],
                    project_id=project_id, project_name=proj_name, project_description=proj_desc,
                    core_goal=core_goal, agent_name=agent.name, stream=False, max_tokens=32000,
                    project_slug=slug,
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

        # ── Step 5: 并行生成代码（Phase 1） ──
        all_results = []
        rlock = asyncio.Lock()

        async def _save_subtask_result(result: dict):
            try:
                cur = bg_engine.get_step7_artifacts() or {}
                saved_results = cur.get("subtask_results", [])
                found = False
                for i, sr in enumerate(saved_results):
                    if sr.get("index") == result.get("index"):
                        saved_results[i] = result
                        found = True
                        break
                if not found:
                    saved_results.append(result)
                cur["subtask_results"] = saved_results
                bg_engine.save_step7_artifacts(cur)
            except Exception as e:
                logger.warning(f"Step7 save subtask result failed: {e}")

        writer_idx = 0
        sem_writer = asyncio.Semaphore(PARALLEL_WRITERS)

        async def _generate_one(st, idx):
            nonlocal writer_idx
            sname = st.get("name", f"用例{idx}")
            sdesc = st.get("description", "")
            sacc = st.get("acceptance_criteria", "")
            file_path = os.path.join(docs_dir, f"{slug}_tdctask_{idx:04d}.md")
            async with sem_writer:
                for attempt in range(1, 6):
                    wi = writer_idx % len(writer_agents)
                    writer_idx += 1
                    writer = writer_agents[wi]
                    await broadcast(project_id, {"type": "step7", "message": f"✍️ [{sname}] {writer.name} 编写（第{attempt}轮）..."})
                    fb = ""
                    if attempt > 1 and st.get("last_feedback"):
                        fb = f"\n\n=== 上次反馈（仅修复这些问题）===\n{st['last_feedback']}"
                    req_ref = f"=== 需求文档路径 ===\n{requirement_path}\n" if requirement_path else ""
                    wp = (
                        f"你{writer.name}，负责编写TDD测试用例代码。\n\n"
                        f"{req_ref}=== 架构 ===\n{design_doc[:2000]}\n"
                        f"=== 测试用例 ===\n名称：{sname}\n描述：{sdesc}\n验收标准：{sacc}\n"
                        f"直接输出完整测试代码（含import）。不要推理过程。{fb}"
                    )
                    await broadcast(project_id, {"type": "step7", "message": f"📝 [{sname}] → {writer.name} 提示词", "prompt": wp, "agent": writer.name, "subtask": sname})
                    code = await _call_agent(writer, wp)
                    if code.strip():
                        await broadcast(project_id, {"type": "agent_response", "subtask": sname, "role": "writer", "response": code[:2000]})
                    if not code.strip():
                        st["last_feedback"] = "编写Agent未生成有效代码"
                        continue
                    with open(file_path, "w") as f:
                        f.write(code)
                    async with rlock:
                        result = {"name": sname, "index": idx, "status": "generated", "file_path": file_path, "attempts": attempt, "writer": writer.name, "code": code[:500]}
                        all_results.append(result)
                    await broadcast(project_id, {"type": "step7", "message": f"📦 [{sname}] {writer.name} 代码已生成（第{attempt}轮），等待测试..."})
                    return
                async with rlock:
                    result = {"name": sname, "index": idx, "status": "failed", "file_path": file_path, "attempts": 5}
                    all_results.append(result)
                await _save_subtask_result(result)
                await broadcast(project_id, {"type": "step7", "message": f"❌ [{sname}] 5轮编写均失败"})

        # 断点续跑（仅加载已完成结果，跳过已完成的子任务）
        if resume:
            saved = bg_engine.get_step7_artifacts().get("subtask_results", [])
            for sr in saved:
                idx = sr.get("index", 0)
                if idx > 0 and idx <= len(subtasks):
                    all_results.append(sr)
            if saved:
                await broadcast(project_id, {"type": "step7", "message": f"♻️ 续跑：已加载 {len(saved)} 个已完成子任务结果"})
                completed_indices = {sr.get("index", 0) for sr in saved}
                subtasks = [st for i, st in enumerate(subtasks) if (i + 1) not in completed_indices]
                if not subtasks:
                    await broadcast(project_id, {"type": "step7", "message": "♻️ 续跑：所有子任务已完成，跳过蜂群执行"})

        # 并行启动所有子任务的代码生成（Semaphore 控制最多 PARALLEL_WRITERS 个并发）
        await broadcast(project_id, {"type": "step7", "message": f"🚀 并行启动 {len(subtasks)} 个子任务的代码生成（最多 {PARALLEL_WRITERS} 个并发）..."})
        gen_tasks = [_generate_one(st, i + 1) for i, st in enumerate(subtasks)]
        await asyncio.gather(*gen_tasks)
        generated = [r for r in all_results if r["status"] == "generated"]
        gen_failed = [r for r in all_results if r["status"] == "failed"]
        await broadcast(project_id, {"type": "step7", "message": f"📊 代码生成完成：{len(generated)}个成功 / {len(gen_failed)}个失败"})

        # ── Step 6: 并行测试代码（Phase 2：用 Reasonix/Claude Code 测试已生成的代码） ──
        if not generated:
            await broadcast(project_id, {"type": "step7", "message": "⚠️ 没有已生成的代码需要测试"})
        else:
            sem_tester = asyncio.Semaphore(PARALLEL_TESTERS)
            tester_idx = 0

            async def _test_one(result):
                nonlocal tester_idx
                sname = result["name"]
                idx = result["index"]
                file_path = result["file_path"]
                async with sem_tester:
                    if not file_path or not os.path.exists(file_path):
                        async with rlock:
                            result["status"] = "failed"
                            result["test_error"] = "代码文件不存在"
                        return
                    try:
                        with open(file_path, "r") as f:
                            code = f.read()
                    except Exception:
                        async with rlock:
                            result["status"] = "failed"
                            result["test_error"] = "无法读取代码文件"
                        return

                    for attempt in range(1, 4):
                        ti = tester_idx % len(tester_agents)
                        tester_idx += 1
                        tester = tester_agents[ti]
                        await broadcast(project_id, {"type": "step7", "message": f"🧪 [{sname}] {tester.name} 测试（第{attempt}轮）..."})
                        tp = (
                            f"你{tester.name}，负责测试TDD测试用例代码。\n\n"
                            f"=== 测试用例 ===\n名称：{sname}\n"
                            f"=== 测试代码路径 ===\n{file_path}\n"
                            f"=== 测试代码 ===\n{code}\n\n"
                            "请执行以下检验：\n"
                            "1. 语法正确性——代码是否能通过编译/解释\n"
                            "2. 逻辑正确性——测试逻辑是否覆盖验收标准\n"
                            "3. 边界覆盖——是否有边界值测试\n"
                            "4. 可独立运行——测试用例是否可独立执行\n"
                            "逐项评分（0-100），评分≥90为通过。\n"
                            "先输出 PASS 或 FAIL，再给出详细评分。"
                        )
                        test_reply = await _call_agent(tester, tp)
                        if test_reply.strip():
                            passed = "PASS" in test_reply.upper() and "FAIL" not in test_reply.upper()
                            async with rlock:
                                result["status"] = "passed" if passed else "failed"
                                result["test_agent"] = tester.name
                                result["test_report"] = test_reply[:1000]
                                result["test_attempts"] = attempt
                            if passed:
                                await broadcast(project_id, {"type": "step7", "message": f"✅ [{sname}] {tester.name} 测试通过（第{attempt}轮）"})
                                return
                            else:
                                await broadcast(project_id, {"type": "step7", "message": f"⚠️ [{sname}] {tester.name} 测试未通过（第{attempt}轮）"})
                                continue
                        else:
                            await broadcast(project_id, {"type": "step7", "message": f"⚠️ [{sname}] {tester.name} 未返回有效结果，重试..."})

                    async with rlock:
                        result["status"] = "failed"
                        result["test_error"] = "3轮测试均未通过"
                    await broadcast(project_id, {"type": "step7", "message": f"❌ [{sname}] 3轮测试均未通过"})

            await broadcast(project_id, {"type": "step7", "message": f"🧪 并行测试 {len(generated)} 个已生成的代码（最多 {PARALLEL_TESTERS} 个并发）..."})
            test_tasks = [_test_one(r) for r in generated]
            await asyncio.gather(*test_tasks)

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
        err_msg = str(e)[:200]
        try:
            await broadcast(project_id, {"type": "error", "message": f"❌ 蜂群执行异常: {err_msg}"})
        except Exception:
            pass
        try:
            bg_engine = WorkflowEngine(project_id=project_id, db=bg_db)
            bg_engine.save_step7_artifacts({"status": "error", "message": f"失败: {err_msg}"})
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
    requirement_path = step3.get("local_path") or step3.get("filepath") or ""
    step2 = engine.get_step2_artifacts() or {}
    core_goal = step2.get("confirmed_goal") or step2.get("core_goal") or ""
    # If previous steps missing, auto-generate from requirement
    step4 = engine.get_step4_artifacts() or {}
    design_doc = step4.get("design_doc") or ""
    if not design_doc and requirement:
        req_ref = f"\n需求文档路径: {requirement_path}" if requirement_path else ""
        design_doc = f"基于需求自动生成架构设计{req_ref}"
    engine.save_step7_artifacts({"status": "generating", "message": "🐝 后发正在组建蜂群并行编写TDD测试用例..."})

    async def _generate():
        await run_step7_swarm(
            project_id=project_id,
            requirement=requirement,
            design_doc=design_doc,
            core_goal=core_goal,
            existing=existing if resume else None,
            resume=resume,
            requirement_path=requirement_path,
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
    import json as _json
    content, focus_items = body.content, body.focus_items
    if not content or len(content.strip()) < 20:
        return APIResponse(code=0, data={"passed": False, "dimensions": [{"key": d["key"], "passed": False} for d in TDD_TESTCASE_DIMENSIONS]})
    active_dims = [d for d in TDD_TESTCASE_DIMENSIONS if not focus_items or d["key"] in focus_items]
    dims_json = _json.dumps([{'检验项目': d['label'], '检验标准': d['description']} for d in active_dims], ensure_ascii=False, indent=2)
    focus_hint = f"\n⚠️ 本次只检验：{[d['label'] for d in active_dims]}" if focus_items else ""
    convergence_hint = "\n⚠️ 收敛性要求：检验报告必须聚焦于不合格项，明确指出不合格项的问题和修改方向。后续Agent将只修改不合格项，禁止扩大范围。已合格项目不得提出修改要求。"
    scoring_hint = "\n评分规则：每个维度起始100分，每发现一个缺陷扣减相应分数（轻微缺陷扣5-10分，一般缺陷扣15-20分，严重缺陷扣25-30分）。维度得分≥90则该维度passed为true。所有维度平均分>90分为整体合格。"
    prompt = f"你是一个专业的TDD测试用例QA检验员（后荣）。\n\n=== TDD用例 ===\n{content}\n\n=== 检验项目 ===\n{dims_json}\n{focus_hint}\n{convergence_hint}\n{scoring_hint}\n\n直接输出 JSON 数组：\n[\n" + ",\n".join(f'  {{"key": "{d["key"]}", "score": 100, "deduction": "", "passed": true/false, "detail": "..."}}' for d in active_dims) + "\n]"
    try:
        reply = await _inspect_via_subagent(prompt=prompt, max_retries=3)
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
        results.append({"key": dim["key"], "label": dim["label"], "score": int(m.get("score", 100)) if m else 0, "passed": int(m.get("score", 100)) >= 90 if m else False, "detail": m.get("detail", "") if m else ""})
    avg_score = sum(r.get("score", 0) for r in results) / len(results) if results else 0
    all_passed = avg_score > 90
    _engine = _get_engine(project_id, db)
    _engine.save_step7_artifacts({
        "inspect_result": {"passed": all_passed, "avg_score": avg_score, "dimensions": results, "inspected_at": __import__('datetime').datetime.now(__import__('datetime').timezone.utc).isoformat()},
        "qa_passed": all_passed, "qa_checked": True,
    })
    return APIResponse(code=0, data={"passed": avg_score > 90, "score": avg_score, "dimensions": results})


@router.post("/{project_id}/step7/qa")
def qa_step7(project_id: str, body: QAResultRequest, db: Session = Depends(get_db), current_user=Depends(get_current_user)):
    from datetime import datetime, timezone
    engine = _get_engine(project_id, db)
    now_iso = datetime.now(timezone.utc).isoformat()
    if body.result == "passed":
        result = engine.pass_qa(7)
        engine.save_step7_artifacts({"qa_passed": True, "qa_status": "passed", "qa_checked_at": now_iso})
    else:
        result = engine.fail_qa(7, reason=body.reason or "", suggestions=body.suggestions)
        engine.save_step7_artifacts({"qa_passed": False, "qa_status": "failed", "qa_checked_at": now_iso, "qa_fail_reason": body.reason, "qa_suggestions": body.suggestions})
    return APIResponse(code=0, data={"message": f"第七步QA{'通过' if body.result == 'passed' else '未通过'}", "qa": result})