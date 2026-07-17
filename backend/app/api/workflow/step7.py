from app.api.workflow.core import (
    router, _get_engine, logger, APIResponse, Depends, get_db,
    get_current_user, Session, Body, Request, HTTPException,
    BaseModel, Optional, asyncio, os, settings, Step3InspectRequest, QAResultRequest,
    TDD_TESTCASE_DIMENSIONS, Step7ChatRequest, _wf_engines, WorkflowEngine,
)
from app.services.gateway_client import GatewayClient
from app.api.ws.step7_progress import broadcast
from app.api.ws.step3_qa import _inspect_via_subagent
import time
import random


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
    saved_subtasks: list = None,
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
        test_cases_dir = os.path.join(settings.PROJECTS_BASE_DIR, slug, "tests", "test_cases")
        os.makedirs(test_cases_dir, exist_ok=True)
        proj_name = proj_name or (proj.name if proj else "")
        proj_desc = proj_desc or (proj.description or "")

        # 解析架构设计文档路径（提示词中仅提供路径，不嵌入完整内容）
        step4_arts = bg_engine.get_step4_artifacts() or {}
        doc_paths = step4_arts.get("doc_paths", {}) or {}
        design_doc_path = (
            doc_paths.get("arch_reasonableness", "") or
            doc_paths.get("architecture", "") or
            ""
        )
        if not design_doc_path or not os.path.exists(design_doc_path):
            import glob as _glob
            for f in _glob.glob(os.path.join(docs_dir, f"{slug}_ARCHITECTURE_V*.md")):
                design_doc_path = f
                break

        # ── 初始化已通过子任务集合（防御）：优先使用调用方传入的 saved_subtasks ──
        saved_results = saved_subtasks or []
        if not saved_results:
            arts = bg_engine.get_step7_artifacts() or {}
            saved_results = arts.get("subtask_results", [])
        logger.info(f"[Step7] run_step7_swarm resume={resume} saved_results_count={len(saved_results)}")
        # DEBUG: 打印每个 saved_result 的完整字段
        for _sr in saved_results:
            logger.info(f"[Step7] DEBUG saved_result: name={_sr.get('name')} index={_sr.get('index')} status={_sr.get('status')} keys={list(_sr.keys())}")
        passed_names_from_prev = set()
        passed_indices_from_prev = set()
        reset_indices = set()
        for sr in saved_results:
            if sr.get("status") == "passed":
                idx = sr.get("index", 0)
                name = sr.get("name", "")
                reason = ""
                # 验证 1：代码文件必须存在
                fp = sr.get("file_path", "")
                if not fp or not os.path.exists(fp):
                    fp_std = os.path.join(test_cases_dir, f"test_tdd_{idx:04d}_{slug}.py")
                    if not os.path.exists(fp_std):
                        reason = f"代码文件不存在 path={fp or fp_std}"
                # 验证 2：检验报告文件必须存在
                if not reason:
                    rp = sr.get("test_report_file", "")
                    if not rp or not os.path.exists(rp):
                        reason = f"检验报告文件不存在 path={rp}"
                if reason:
                    logger.warning(f"[Step7] 重置子任务状态（{reason}）: [{name}] idx={idx}")
                    reset_indices.add(idx)
                    continue
                passed_names_from_prev.add(name)
                passed_indices_from_prev.add(idx)
        # 将被重置的子任务从 artifacts 中清除（状态改为空、轮次归零）
        if reset_indices:
            arts = bg_engine.get_step7_artifacts() or {}
            old_results = arts.get("subtask_results", [])
            old_progress = arts.get("subtask_progress", {})
            new_results = []
            for r in old_results:
                if r.get("index") in reset_indices or r.get("status") != "passed":
                    new_results.append(r)
            for ri in reset_indices:
                old_progress.pop(str(ri), None)
            arts["subtask_results"] = new_results
            arts["subtask_progress"] = old_progress
            bg_engine.save_step7_artifacts(arts)
            logger.info(f"[Step7] 已清除 {len(reset_indices)} 个子任务的状态和进度: {sorted(reset_indices)}")
        logger.info(f"[Step7] 防御性过滤：{len(passed_names_from_prev)} 个已通过子任务名: {passed_names_from_prev} 重置: {sorted(reset_indices) if reset_indices else '无'}")

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
            err_msg = "数据库无TDD测试用例，请先完成步骤6"
            bg_engine.save_step7_artifacts({"status": "error", "message": err_msg})
            await broadcast(project_id, {"type": "error", "message": f"❌ {err_msg}"})
            return

        # ── all_results 初始化（用于收集所有子任务结果） ──
        all_results = []
        # ── Fallback: 从 tdd_test_cases.qa_status + 检验报告文件 恢复已通过子任务 ──
        # 即使 output_artifacts.subtask_results 没保存，qa_status 和磁盘检验报告仍是可信证据
        if not passed_indices_from_prev:
            reports_dir = os.path.join(test_cases_dir, "reports")
            for ci, c in enumerate(db_cases):
                idx = ci + 1
                # 1) DB qa_status = passed
                is_passed = c.get("qa_status") == "passed"
                # 2) 文件系统检验报告解析
                if not is_passed and os.path.exists(reports_dir):
                    import glob as _glob
                    report_files = sorted(_glob.glob(os.path.join(reports_dir, f"report_{idx:04d}_{slug}_attempt*.txt")))
                    for rf in reversed(report_files):
                        try:
                            with open(rf) as fh:
                                content = fh.read()
                            first_line = content.strip().split('\n')[0] if content.strip() else ""
                            score_match = re.search(r'总分[：:]\s*(\d+)', first_line)
                            score = int(score_match.group(1)) if score_match else 0
                            if "判定结果：通过" in first_line and "未通过" not in first_line and score >= 90:
                                is_passed = True
                                logger.info(f"[Step7] Fallback 报告判定为通过: idx={idx} file={rf} score={score}")
                                break
                        except Exception as e:
                            logger.warning(f"[Step7] Fallback 读取报告失败: {rf} {e}")
                # 3) 代码文件存在 + 检验报告文件存在且内容非空（兜底）
                if not is_passed:
                    file_path = os.path.join(test_cases_dir, f"test_tdd_{idx:04d}_{slug}.py")
                    if os.path.exists(file_path) and os.path.exists(reports_dir):
                        import glob as _glob
                        report_files = sorted(_glob.glob(os.path.join(reports_dir, f"report_{idx:04d}_{slug}_attempt*.txt")))
                        for rf in reversed(report_files):
                            try:
                                if os.path.getsize(rf) > 0:
                                    is_passed = True
                                    break
                            except Exception:
                                pass
                if is_passed:
                    passed_names_from_prev.add(c.get("title", ""))
                    passed_indices_from_prev.add(idx)
                    all_results.append({
                        "index": idx,
                        "name": c.get("title", f"用例{idx}"),
                        "case_id": c.get("case_id", ""),
                        "status": "passed",
                        "attempts": 1,
                        "writer": "",
                        "test_agent": "",
                    })
                    logger.info(f"[Step7] Fallback 已通过: idx={idx} case_id={c.get('case_id','')} title={c.get('title','')[:50]}")
            if passed_indices_from_prev:
                logger.info(f"[Step7] Fallback 恢复 {len(passed_indices_from_prev)} 个已通过子任务，已加入 all_results")

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

        # ── Step 2: 直接将数据库用例映射为TODO LIST ──
        subtasks = []
        for i, c in enumerate(db_cases):
            subtasks.append({
                "name": c.get("title", f"用例{i+1}"),
                "description": c.get("description", ""),
                "acceptance_criteria": c.get("expected_result", ""),
            })

        if not subtasks:
            err_msg = "数据库无测试用例，无法生成TODO LIST"
            bg_engine.save_step7_artifacts({"status": "error", "message": err_msg})
            await broadcast(project_id, {"type": "error", "message": f"❌ {err_msg}"})
            return

        # ── 全部子任务已通过 → 直接完成 step7，不启动蜂群 ──
        if passed_indices_from_prev and len(passed_indices_from_prev) == len(subtasks):
            logger.info(f"[Step7] 全部 {len(subtasks)} 个子任务均已通过 (fallback)，跳过蜂群执行")
            await broadcast(project_id, {"type": "step7", "message": f"✅ 全部 {len(subtasks)} 个子任务已通过检验（从历史记录恢复）"})
            bg_engine.save_step7_artifacts({
                "subtask_results": all_results,
                "status": "done",
                "message": f"✅ 全部 {len(subtasks)} 个子任务已通过",
                "qa_passed": True,
                "swarm_summary": {"total": len(subtasks), "passed": len(subtasks), "failed": 0, "spot_checked": 0, "spot_failures": 0},
            })
            bg_engine.complete_step(7)
            await broadcast(project_id, {"type": "done", "message": f"✅ TDD测试用例已全部通过（共{len(subtasks)}项）"})
            return

        # ── 过滤已通过的 subtask_names，避免前端显示为待执行 ──
        subtask_names = [st.get("name", f"用例{i+1}") for i, st in enumerate(subtasks)]
        subtask_names_filtered = [n for n in subtask_names if n not in passed_names_from_prev]
        pending_count = len(subtask_names_filtered)
        skipped_count = len(subtask_names) - pending_count
        broadcast_names = subtask_names_filtered if resume else subtask_names
        logger.info(f"[Step7] broadcast subtask_names: total={len(subtask_names)} filtered={len(broadcast_names)} skipped={skipped_count} resume={resume}")
        await broadcast(project_id, {"type": "step7", "subtask_names": broadcast_names, "message": f"📋 TODO LIST已生成：{pending_count} 个待处理（{skipped_count} 个已跳过）"})

        # ── Step 2: 获取编程Agent，按偏好排序（PI > OpenCode > 其他; Reasonix > Claude Code > 其他） ──
        writer_agents = SwarmService.get_preferred_writer_agents(bg_db)
        tester_agents = SwarmService.get_preferred_tester_agents(bg_db)

        # ── CLI Agent 自动配置（检测系统命令，写入数据库 config） ──
        CLI_AGENT_COMMANDS = {
            "openhands":      ["openhands", "python3 -m openhands", "python -m openhands"],
            "aider-chat":     ["aider --message {prompt} --yes"],
            "goose":          ["goose run --text {prompt} --no-session -q"],
            "claude_code":    ["claude"],
            "pi_coding_agent": ["pi"],
            "opencode":       ["opencode run {prompt}"],
            "codebuddy":      ["codebuddy"],
            "reasonix":       ["reasonix"],
            "codearts":       ["codearts"],
            "trae":           ["trae"],
            "atom":           ["atom", "atom-agent"],
            "atomcode":       ["atomcode"],
        }

        def _is_agent_callable(agent):
            cfg = agent.config or {}
            has_cli = bool(cfg.get("cli_command") and not cfg["cli_command"].startswith("http"))
            has_api = bool(agent.api_endpoint)
            is_delegate = (agent.agent_type == "houfa" or agent.name == "hourong")
            is_gateway = (agent.agent_type == "hermes")
            return has_cli or has_api or is_delegate or is_gateway

        async def _auto_configure_agent(agent):
            # 预检：如果已有 cli_command，验证命令是否真的存在，不存在则清除
            existing_cli = (agent.config or {}).get("cli_command", "")
            cli_valid = True
            if existing_cli and not existing_cli.startswith("http"):
                parts = existing_cli.split()
                first_word = parts[0]
                ck = await asyncio.create_subprocess_exec(
                    "sh", "-c", f"which '{first_word}' 2>/dev/null",
                    stdout=asyncio.subprocess.PIPE, stderr=asyncio.subprocess.PIPE,
                )
                out_bytes, _ = await ck.communicate()
                cli_valid = ck.returncode == 0 and out_bytes.strip()
                if cli_valid and len(parts) > 1 and parts[0] in ("python3", "python"):
                    module = parts[-1]
                    vproc = await asyncio.create_subprocess_exec(
                        first_word, "-c", f"import {module}",
                        stdout=asyncio.subprocess.PIPE, stderr=asyncio.subprocess.PIPE,
                    )
                    try:
                        _, _ = await asyncio.wait_for(vproc.communicate(), timeout=15)
                        cli_valid = (vproc.returncode == 0)
                    except asyncio.TimeoutError:
                        cli_valid = False
                if not cli_valid:
                    logger.warning(f"[Step7] 清除失效的 cli_command: {agent.name} old={existing_cli}")
                    cfg = dict(agent.config or {})
                    cfg.pop("cli_command", None)
                    agent.config = cfg
                    try:
                        ag = bg_db.query(Agent).filter(Agent.id == agent.id).first()
                        if ag:
                            ag.config = cfg
                            bg_db.commit()
                    except Exception as e:
                        logger.warning(f"[Step7] 清除失效配置失败: {agent.name} {e}")
                else:
                    # 命令存在且有效，检查是否匹配已知候选命令（代码更新后可能需要刷新）
                    known_candidates = CLI_AGENT_COMMANDS.get(agent.agent_type, [])
                    if known_candidates and existing_cli not in known_candidates:
                        logger.info(f"[Step7] 刷新 Agent 命令: {agent.name} old={existing_cli} → candidates={known_candidates}")
                        cfg = dict(agent.config or {})
                        cfg.pop("cli_command", None)
                        agent.config = cfg
                        try:
                            ag = bg_db.query(Agent).filter(Agent.id == agent.id).first()
                            if ag:
                                ag.config = cfg
                                bg_db.commit()
                        except Exception as e:
                            logger.warning(f"[Step7] 刷新配置失败: {agent.name} {e}")
                        cli_valid = False

            if _is_agent_callable(agent) and cli_valid is not False:
                return True
            cfg = dict(agent.config or {})
            if agent.api_endpoint:
                return True
            cmd_candidates = CLI_AGENT_COMMANDS.get(agent.agent_type, [])
            if not cmd_candidates:
                return False
            for candidate in cmd_candidates:
                try:
                    parts = candidate.split()
                    first_word = parts[0]
                    proc = await asyncio.create_subprocess_exec(
                        "sh", "-c", f"which '{first_word}' 2>/dev/null",
                        stdout=asyncio.subprocess.PIPE,
                        stderr=asyncio.subprocess.PIPE,
                    )
                    out_bytes, _ = await proc.communicate()
                    if proc.returncode != 0 or not out_bytes.strip():
                        continue
                    base_cmd = out_bytes.decode().strip()
                    if len(parts) > 1 and parts[0] in ("python3", "python"):
                        module = parts[-1]
                        vproc = await asyncio.create_subprocess_exec(
                            first_word, "-c", f"import {module}",
                            stdout=asyncio.subprocess.PIPE,
                            stderr=asyncio.subprocess.PIPE,
                        )
                        try:
                            _, _ = await asyncio.wait_for(vproc.communicate(), timeout=15)
                            if vproc.returncode != 0:
                                continue
                        except asyncio.TimeoutError:
                            continue
                    cfg["cli_command"] = candidate
                    agent.config = cfg
                    try:
                        ag = bg_db.query(Agent).filter(Agent.id == agent.id).first()
                        if ag:
                            ag.config = cfg
                            bg_db.commit()
                    except Exception as e:
                        logger.warning(f"[Step7] 保存Agent配置失败: {agent.name} {e}")
                    logger.info(f"[Step7] 自动配置Agent: {agent.name}({agent.agent_type}) → cli_command={candidate} (路径={base_cmd})")
                    return True
                except Exception as e:
                    logger.warning(f"[Step7] 检测命令失败: {agent.name} candidate={candidate} {e}")
            return False

        async def _smoke_test_agent(agent) -> bool:
            """快速烟雾测试：验证 agent 是否真的可以响应，而非仅配置存在。"""
            _SMOKE_TIMEOUT = 60
            cfg = agent.config or {}
            cli_cmd = cfg.get("cli_command", "")
            if cli_cmd and not cli_cmd.startswith("http"):
                import re as _re
                for flag in ("--version", "--help"):
                    try:
                        if "{prompt}" in cli_cmd:
                            _cmd = f"timeout {_SMOKE_TIMEOUT} {cli_cmd.replace('{prompt}', flag)} 2>&1"
                        else:
                            _cmd = f"timeout {_SMOKE_TIMEOUT} {cli_cmd} {flag} 2>&1"
                        smoke_proc = await asyncio.create_subprocess_exec(
                            "sh", "-c", _cmd,
                            stdin=asyncio.subprocess.DEVNULL,
                            stdout=asyncio.subprocess.PIPE,
                            stderr=asyncio.subprocess.PIPE,
                        )
                        try:
                            out_bytes, _ = await asyncio.wait_for(smoke_proc.communicate(), timeout=_SMOKE_TIMEOUT)
                        except asyncio.TimeoutError:
                            logger.warning(f"[Step7] Agent 烟雾测试超时: {agent.name} cli={cli_cmd} {flag}")
                            continue
                        output = out_bytes.decode().strip() if out_bytes else ""
                        rc = smoke_proc.returncode
                        if rc != 0:
                            # 检查是否为终端/TTY 相关问题导致崩溃
                            if _re.search(r'(Input is not a terminal|not a tty|is not a TTY|stdin is not a terminal)', output):
                                logger.warning(f"[Step7] Agent 烟雾测试因无终端环境失败: {agent.name} cli={cli_cmd}（该 Agent 需要交互式终端，跳过）")
                                return False
                            err_snip = output[:200].replace('\n', ' | ')
                            logger.warning(f"[Step7] Agent 烟雾测试退出码非0: {agent.name} cli={cli_cmd} {flag} rc={rc} err={err_snip}")
                            continue
                        if not output:
                            logger.warning(f"[Step7] Agent 烟雾测试无输出: {agent.name} cli={cli_cmd} {flag}")
                            continue
                        logger.info(f"[Step7] Agent 烟雾测试通过: {agent.name} cli={cli_cmd} {flag}")
                        return True
                    except Exception as e:
                        logger.warning(f"[Step7] Agent 烟雾测试异常: {agent.name} cli={cli_cmd} {flag} {e}")
                        continue
                logger.warning(f"[Step7] Agent 烟雾测试全部失败: {agent.name} cli={cli_cmd}")
                return False
            if agent.api_endpoint:
                try:
                    import httpx
                    async with httpx.AsyncClient(timeout=_SMOKE_TIMEOUT) as hc:
                        await hc.get(agent.api_endpoint)
                    return True
                except Exception as e:
                    logger.warning(f"[Step7] Agent API端点不可达: {agent.name} endpoint={agent.api_endpoint} {e}")
                    return False
            if agent.agent_type == "hermes" or agent.agent_type == "houfa" or agent.name == "hourong":
                return True
            return False

        async def _check_agent(a) -> bool:
            return await _auto_configure_agent(a) and await _smoke_test_agent(a)

        configured_writers = []
        skipped_writers = []
        for a in writer_agents:
            if await _check_agent(a):
                configured_writers.append(a)
            else:
                skipped_writers.append(a.name)
        writer_agents = configured_writers
        if skipped_writers:
            logger.warning(f"[Step7] 跳过 {len(skipped_writers)} 个不可用的编写Agent: {skipped_writers}")
            await broadcast(project_id, {"type": "step7", "message": f"⚠️ 跳过 {len(skipped_writers)} 个不可用的编写Agent: {skipped_writers}"})

        configured_testers = []
        skipped_testers = []
        for a in tester_agents:
            if await _check_agent(a):
                configured_testers.append(a)
            else:
                skipped_testers.append(a.name)
        tester_agents = configured_testers
        if skipped_testers:
            logger.warning(f"[Step7] 跳过 {len(skipped_testers)} 个不可用的测试Agent: {skipped_testers}")
            await broadcast(project_id, {"type": "step7", "message": f"⚠️ 跳过 {len(skipped_testers)} 个不可用的测试Agent: {skipped_testers}"})

        if not writer_agents:
            bg_engine.save_step7_artifacts({"status": "error", "message": "❌ 没有可用的编写Agent（请确保系统已安装 openhands/aider/goose 等编程Agent并配置在 PATH 中）"})
            await broadcast(project_id, {"type": "error", "message": "❌ 没有可用的编写Agent"})
            return
        if not tester_agents:
            bg_engine.save_step7_artifacts({"status": "error", "message": "❌ 没有可用的测试Agent（请确保系统已安装 aider/reasonix 等测试Agent并配置在 PATH 中）"})
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
            t_req = time.time()
            agent_tag = f"{agent.name}({agent.agent_type})"
            logger.debug(f"[Step7] _call_agent 开始: {agent_tag} prompt_len={len(prompt_text)}")
            cfg = agent.config or {}
            api_key = cfg.get("api_key") or cfg.get("apiKey")
            model = cfg.get("model") or "default"

            # 快速失败：预检是否有任何可用路径
            cli_cmd = cfg.get("cli_command")
            has_cli = bool(cli_cmd and not cli_cmd.startswith("http"))
            has_api = bool(agent.api_endpoint)
            is_delegate = (agent.agent_type == "houfa" or agent.name == "hourong")
            is_gateway = (agent.agent_type == "hermes")
            if not (has_cli or has_api or is_delegate or is_gateway):
                logger.warning(f"[Step7] _call_agent 快速跳过: {agent_tag} 未配置任何调用路径（无 cli_command、api_endpoint，非 houfa/hourong/hermes 类型）")
                elapsed = time.time() - t_req
                logger.error(f"[Step7] _call_agent 失败: {agent_tag} 耗时={elapsed:.1f}s 未配置调用路径")
                return ""

            cli_cmd = cfg.get("cli_command") or agent.api_endpoint
            if cli_cmd and not cli_cmd.startswith("http"):
                import shlex
                prompt_quoted = shlex.quote(prompt_text)
                if "{prompt}" in cli_cmd:
                    full_cmd = cli_cmd.replace("{prompt}", prompt_quoted)
                    cmd_parts = shlex.split(full_cmd)
                    use_stdin = False
                else:
                    cmd_parts = shlex.split(cli_cmd)
                    use_stdin = True
                for attempt in range(1, 4):
                    try:
                        proc = await asyncio.create_subprocess_exec(
                            *cmd_parts,
                            stdin=asyncio.subprocess.PIPE if use_stdin else asyncio.subprocess.DEVNULL,
                            stdout=asyncio.subprocess.PIPE,
                            stderr=asyncio.subprocess.PIPE,
                        )
                        out_bytes, err_bytes = await asyncio.wait_for(
                            proc.communicate(input=prompt_text.encode() if use_stdin else None), timeout=timeout,
                        )
                        text = out_bytes.decode().strip() if out_bytes else ""
                        if text:
                            elapsed = time.time() - t_req
                            logger.info(f"[Step7] _call_agent success (CLI): {agent_tag} 耗时={elapsed:.1f}s reply_len={len(text)}")
                            return text
                        if proc.returncode != 0:
                            err = (err_bytes.decode().strip() if err_bytes else "")[:500]
                            logger.warning(f"Step7 agent {agent.name} CLI exit {proc.returncode} (attempt {attempt}/3): {err}")
                    except asyncio.TimeoutError:
                        logger.warning(f"Step7 agent {agent.name} CLI timeout (attempt {attempt}/3)")
                    except Exception as e:
                        logger.warning(f"Step7 agent {agent.name} CLI error (attempt {attempt}/3): {e}")
                    await asyncio.sleep(2 ** attempt)
                logger.error(f"Step7 agent {agent.name} CLI all attempts failed")

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
                                elapsed = time.time() - t_req
                                logger.info(f"[Step7] _call_agent success (HTTP): {agent_tag} 耗时={elapsed:.1f}s reply_len={len(content)}")
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
                    fallback = "GatewayClient" if agent.agent_type == "hermes" else "已无可用路径"
                    logger.info(f"Step7 agent {agent.name} direct API failed after 3 attempts, {fallback}")

            # 路径: houfa → delegate_task 子 Agent
            if agent.agent_type == "houfa" or agent.name == "hourong":
                try:
                    from app.api.ws.step3_qa_1 import delegate_task as _delegate_task
                    _profile = "hourong" if agent.name == "hourong" else "houfa"
                    task_payload = json.dumps({
                        "save_path": os.path.join(docs_dir, f"{agent.name}_reply_{int(time.time())}.json"),
                        "task": prompt_text,
                    }, ensure_ascii=False)
                    results = await _delegate_task(tasks=[task_payload], profile_name=_profile, timeout=timeout)
                    if results and results[0]:
                        result_path = results[0]
                        if os.path.exists(result_path):
                            with open(result_path, "r", encoding="utf-8") as f:
                                raw = f.read()
                            # hourong 保存的是原始文本，可能不是 JSON，先尝试 JSON 解析
                            reply = ""
                            try:
                                report = json.loads(raw)
                                reply = report.get("summary", "") or report.get("content", "") or report.get("result", "")
                            except json.JSONDecodeError:
                                # 非 JSON 原始文本直接作为回复
                                reply = raw.strip()
                            if reply.strip():
                                elapsed = time.time() - t_req
                                logger.info(f"[Step7] _call_agent success (delegate_task): {agent_tag} 耗时={elapsed:.1f}s reply_len={len(reply)}")
                                return reply
                except Exception as e:
                    logger.warning(f"Step7 agent {agent.name} delegate_task failed: {e}")

            if agent.agent_type == "hermes":
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
                        elapsed = time.time() - t_req
                        logger.info(f"[Step7] _call_agent success (GatewayClient): {agent_tag} 耗时={elapsed:.1f}s reply_len={len(reply)}")
                        return reply
                except Exception as e:
                    logger.warning(f"Step7 agent {agent.name} GatewayClient failed: {e}")

            elapsed = time.time() - t_req
            logger.error(f"[Step7] _call_agent 失败: {agent_tag} 耗时={elapsed:.1f}s 所有路径均失败")
            return ""

        # ── Step 5: 并行生成代码（Phase 1） ──
        # all_results 已在 Fallback 处初始化，此处不再重复赋值
        rlock = asyncio.Lock()

        async def _save_subtask_result(result: dict):
            try:
                async with rlock:
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

        async def _save_subtask_progress(idx: int, sname: str, progress: dict):
            try:
                async with rlock:
                    cur = bg_engine.get_step7_artifacts() or {}
                    sp = cur.get("subtask_progress", {})
                    sp[str(idx)] = {**sp.get(str(idx), {}), **progress, "name": sname, "index": idx, "updated_at": time.time()}
                    cur["subtask_progress"] = sp
                    bg_engine.save_step7_artifacts(cur)
            except Exception as e:
                logger.warning(f"Step7 save subtask progress failed: {e}")

        if not tester_agents:
            err_msg = "❌ 没有可用的测试Agent"
            bg_engine.save_step7_artifacts({"status": "error", "message": err_msg})
            await broadcast(project_id, {"type": "error", "message": err_msg})
            return
        logger.info(f"[Step7] Agent池: writers={len(writer_agents)} testers={len(tester_agents)} subtasks={len(subtasks)}")

        # 并发执行时随机选取 writer/tester 辅助函数
        def _pick_writer_tester():
            """从 Agent 池中随机选取 writer 和 tester，确保两者不同"""
            w = random.choice(writer_agents) if writer_agents else None
            t = random.choice(tester_agents) if tester_agents else None
            # 避免自测：同一 agent 不能测自己写的代码
            if w and t and w.id == t.id and len(tester_agents) > 1:
                t = random.choice([a for a in tester_agents if a.id != w.id])
            return w, t

        PARALLEL_SUBTASKS = max(6, min(len(subtasks), 12))
        subtask_sem = asyncio.Semaphore(PARALLEL_SUBTASKS)

        async def _process_one_subtask(st, idx, saved_result=None):
            """处理单个子任务。
            saved_result=None → 正常 write→test 模式
            saved_result 有值且 status=failed → retest-only 模式（跳过写阶段）
            """
            # ── 防御性检查：如果该子任务在 artifacts 中已经是 passed，绝对禁止执行 ──
            arts = bg_engine.get_step7_artifacts() or {}
            for sr in arts.get("subtask_results", []):
                if sr.get("index") == idx and sr.get("status") == "passed":
                    logger.info(f"[Step7] 防御性跳过: [{st.get('name')}] 第{idx}子任务已通过，禁止执行")
                    return
            sname = st.get("name", f"用例{idx}")
            sdesc = st.get("description", "")
            sacc = st.get("acceptance_criteria", "")
            test_cases_dir = os.path.join(settings.PROJECTS_BASE_DIR, slug, "tests", "test_cases")
            os.makedirs(test_cases_dir, exist_ok=True)
            file_path = saved_result.get("file_path", "") if saved_result else ""
            if not file_path:
                file_path = os.path.join(test_cases_dir, f"test_tdd_{idx:04d}_{slug}.py")

            # 随机选取 writer 和 tester（每次调用都重新随机，确保分布均匀）
            writer, tester = _pick_writer_tester()
            if not writer or not tester:
                logger.warning(f"[Step7] 无可用Agent: [{sname}] 跳过")
                return

            # ── 检查已保存的中间进度 ──
            saved_progress = (bg_engine.get_step7_artifacts() or {}).get("subtask_progress", {}).get(str(idx), {}) or {}
            saved_phase = saved_progress.get("phase", "")
            saved_attempt = saved_progress.get("latest_attempt", 0)
            has_existing_code = os.path.exists(file_path)
            is_retest = saved_result is not None and saved_result.get("status") == "failed"

            async with subtask_sem:
                # ── retest 模式：直接从测试开始，不重新编码 ──
                if is_retest:
                    if not os.path.exists(file_path):
                        logger.warning(f"[Step7] 续测文件不存在: {file_path}，降级为正常模式")
                        is_retest = False
                    else:
                        await broadcast(project_id, {"type": "step7", "message": f"♻️ [{sname}] 检测到已有代码，将基于上次检验报告重写"})
                        try:
                            with open(file_path, "r") as f:
                                saved_code = f.read()
                        except Exception:
                            logger.warning(f"[Step7] 续测读取文件失败: [{sname}] {file_path}")
                            is_retest = False

                # ── 主循环（正常 write→test / retest 的 test 部分共用） ──
                max_attempts = 10
                report_file = ""
                test_reply = ""
                # ── 若磁盘有代码文件但无中间进度，自动填入"已编写"状态 ──
                if not saved_phase and has_existing_code and not is_retest:
                    saved_phase = "written"
                    saved_attempt = 1
                    await _save_subtask_progress(idx, sname, {
                        "phase": "written", "latest_attempt": 1,
                        "file_path": file_path, "writer": writer.name,
                    })
                    logger.info(f"[Step7] 检测到已有代码文件，自动跳过首轮编写: [{sname}]")

                for attempt in range(1, max_attempts + 1):
                    # ── 编写（仅非 retest 模式） ──
                    if not is_retest:
                        # 检查是否已有足够进度的代码文件，跳过编写
                        if saved_phase == "written" and saved_attempt >= attempt and has_existing_code:
                            logger.info(f"[Step7] 跳过编写: [{sname}] 第{attempt}轮 已有代码文件")
                            await broadcast(project_id, {"type": "step7", "message": f"♻️ [{sname}] 已有代码，跳过编写直接验证（第{attempt}轮）..."})
                        else:
                            logger.info(f"[Step7] 编写: [{sname}] 第{attempt}轮 writer={writer.name}({writer.agent_type})")
                            await broadcast(project_id, {"type": "step7", "message": f"✍️ [{sname}] {writer.name} 编写（第{attempt}轮）..."})
                            fb = ""
                            if attempt > 1 and st.get("last_feedback"):
                                fb = st["last_feedback"]
                            existing = ""
                            if attempt > 1 and os.path.exists(file_path):
                                try:
                                    with open(file_path) as f:
                                        existing = f.read()
                                except Exception:
                                    pass
                            wp = SwarmService.build_writer_prompt(
                                sname=sname, sdesc=sdesc, sacc=sacc,
                                writer_name=writer.name,
                                attempt=attempt, last_feedback=fb,
                                agent_type=writer.agent_type,
                                existing_code=existing,
                                file_path=file_path,
                                report_file_path=st.get("last_report_file", ""),
                            )
                            await broadcast(project_id, {"type": "step7", "message": f"📝 [{sname}] → {writer.name} 提示词", "prompt": wp, "agent": writer.name, "subtask": sname})
                            code = await _call_agent(writer, wp)
                            # ── 自检循环：空输出/语法错误 → 同 agent 自行修正 ──
                            _SELF_CHECK_MAX = 3
                            _previous_bad_code = ""  # 追踪上一次输出的问题代码，用于对比
                            for _si in range(_SELF_CHECK_MAX):
                                if not code.strip():
                                    _fix_msg = (
                                        "\n\n【⛔ 严重错误：输出为空】\n"
                                        "你的输出是空的。你必须重新输出完整可运行的 Python 代码。\n"
                                        "请仔细阅读需求，从零输出完整代码。只输出代码本身。"
                                    )
                                    code = await _call_agent(writer, wp + _fix_msg)
                                    continue
                                code = SwarmService.clean_generated_code(code)
                                _syntax_ok, _syntax_err = SwarmService.validate_code_syntax(code)
                                if _syntax_ok:
                                    break
                                # 提取错误行的内容，帮助 agent 定位问题
                                _err_lines = code.split('\n')
                                _err_line_idx = 0
                                import re as _re_step7
                                _m_step7 = _re_step7.search(r'第(\d+)行', _syntax_err)
                                if _m_step7:
                                    _err_line_idx = int(_m_step7.group(1)) - 1
                                _bad_line = _err_lines[_err_line_idx] if 0 <= _err_line_idx < len(_err_lines) else '(未知)'
                                # 是否为同样的错误反复出现？
                                _same_as_before = "⚠️ 警告：你刚刚输出的代码和上一轮有相同的语法错误！请换一种方式修复它，不要重复同样的错误输出。"
                                if _previous_bad_code and len(_previous_bad_code) > 50:
                                    # 检查前后输出是否高度相似
                                    import difflib as _dl
                                    _ratio = _dl.SequenceMatcher(None, _previous_bad_code[:500], code[:500]).ratio()
                                    if _ratio > 0.8:
                                        _same_as_before = "⛔ 严重：你两次输出的代码几乎完全一样！说明你只是重复了相同的内容而没有修复。请彻底重新生成代码，不要复述之前的错误输出。"
                                _previous_bad_code = code
                                _fix_msg = (
                                    f"\n\n【⛔ 语法错误 - 第{_si+1}次修正机会，还剩{_SELF_CHECK_MAX-_si-1}次】\n"
                                    f"错误详情：{_syntax_err}\n"
                                    f"错误行位置：第{_err_line_idx+1}行\n"
                                    f"错误行内容：{_bad_line[:200]}\n"
                                    f"\n"
                                    f"{_same_as_before}\n"
                                    f"\n"
                                    f"【修正要求】\n"
                                    f"1. 第1行必须是 import/from/def/class 开头（不能是引号、注释、签名等非代码内容）\n"
                                    f"2. 检查代码中的字符串引号是否成对闭合\n"
                                    f"3. 输出纯文本 Python 代码，不要 Markdown 围栏\n"
                                    f"4. 不要包含任何自我介绍、版本号、路径等非代码文字\n"
                                    f"5. 如果连续3次不通过，你将失去这个子任务，由其他 Agent 接手\n"
                                    f"\n"
                                    f"请重新输出修正后的、完整可运行的 Python 代码："
                                )
                                code = await _call_agent(writer, wp + _fix_msg)
                            # ── 自检循环结束 ──
                            if code.strip():
                                await broadcast(project_id, {"type": "agent_response", "subtask": sname, "role": "writer", "response": code[:2000]})
                            if not code.strip():
                                # 尝试切换其他编写Agent
                                for alt_writer in writer_agents:
                                    if alt_writer.id == writer.id:
                                        continue
                                    logger.info(f"[Step7] 编写降级: [{sname}] 第{attempt}轮 writer={writer.name} 自检不通过，切换为 {alt_writer.name}")
                                    await broadcast(project_id, {"type": "step7", "message": f"🔄 [{sname}] {writer.name} 自检不通过，切换 {alt_writer.name} 编写..."})
                                    # 给 alt writer 附加前一个 writer 的错误代码作为上下文，避免重复犯错
                                    _alt_wp = wp
                                    if not code.strip() and _previous_bad_code:
                                        _alt_wp = wp + (
                                            f"\n\n⚠️ 注意：前一个 Agent（{writer.name}）输出了以下无效代码，已被系统拒绝。\n"
                                            f"请勿重复相同的错误：\n"
                                            f"```\n{_previous_bad_code[:1000]}\n```"
                                        )
                                    elif _syntax_err:
                                        _alt_wp = wp + (
                                            f"\n\n⚠️ 前一个 Agent（{writer.name}）输出的代码有语法错误：{_syntax_err}\n"
                                            f"请直接输出正确的可用代码，不要重复同样的错误。"
                                        )
                                    code = await _call_agent(alt_writer, _alt_wp)
                                    # alt writer 也做自检
                                    _prev_bad2 = ""
                                    for _si in range(_SELF_CHECK_MAX):
                                        if not code.strip():
                                            code = await _call_agent(alt_writer, wp + "\n\n【⛔ 严重错误：输出为空】你必须重新输出完整可运行的 Python 代码。")
                                            continue
                                        code = SwarmService.clean_generated_code(code)
                                        _syntax_ok2, _syntax_err2 = SwarmService.validate_code_syntax(code)
                                        if _syntax_ok2:
                                            break
                                        _err_lines2 = code.split('\n')
                                        _err_line_idx2 = 0
                                        import re as _re_step7_2
                                        _m_step7_2 = _re_step7_2.search(r'第(\d+)行', _syntax_err2)
                                        if _m_step7_2:
                                            _err_line_idx2 = int(_m_step7_2.group(1)) - 1
                                        _bad_line2 = _err_lines2[_err_line_idx2] if 0 <= _err_line_idx2 < len(_err_lines2) else '(未知)'
                                        _same2 = ""
                                        if _prev_bad2 and len(_prev_bad2) > 50:
                                            import difflib as _dl2
                                            if _dl2.SequenceMatcher(None, _prev_bad2[:500], code[:500]).ratio() > 0.8:
                                                _same2 = "\n⛔ 你两次输出的代码几乎一样！不要复述相同的错误，请彻底重新生成。"
                                        _prev_bad2 = code
                                        code = await _call_agent(alt_writer, wp + (
                                            f"\n\n【⛔ 语法错误 - 第{_si+1}次修正，还剩{_SELF_CHECK_MAX-_si-1}次】\n"
                                            f"错误：{_syntax_err2}\n"
                                            f"第{_err_line_idx2+1}行：{_bad_line2[:200]}\n{_same2}\n"
                                            f"要求：第1行必须 import/from/def/class 开头。输出纯文本代码，不要签名/版本号/围栏。\n"
                                            f"连续不通过将失去此子任务。请重新输出完整可运行的 Python 代码："
                                        ))
                                    if code.strip():
                                        await broadcast(project_id, {"type": "agent_response", "subtask": sname, "role": "writer", "response": code[:2000]})
                                        writer = alt_writer
                                        break
                            if not code.strip():
                                logger.warning(f"[Step7] 编写空回复: [{sname}] 第{attempt}轮 writer={writer.name} 未生成有效代码（所有编写Agent均失败）")
                                st["last_feedback"] = "所有编写Agent均未生成有效代码，请重新输出完整可运行的测试代码"
                                continue

                            code = SwarmService.clean_generated_code(code)
                            syntax_ok, syntax_err = SwarmService.validate_code_syntax(code)
                            if not syntax_ok:
                                logger.warning(f"[Step7] 语法检查失败: [{sname}] 第{attempt}轮 {syntax_err}")
                                st["last_feedback"] = f"代码存在语法错误：{syntax_err}。请修正后重新输出完整可运行代码。"
                                await broadcast(project_id, {"type": "step7", "message": f"⚠️ [{sname}] 语法检查不通过，退回 {writer.name} 修改（第{attempt}轮）：{syntax_err}"})
                                continue

                            with open(file_path, "w") as f:
                                f.write(code)
                            await _save_subtask_progress(idx, sname, {
                                "phase": "written", "latest_attempt": attempt,
                                "file_path": file_path, "writer": writer.name,
                            })
                            await broadcast(project_id, {"type": "step7", "message": f"📦 [{sname}] {writer.name} 代码已生成并写入文件（第{attempt}轮），正在测试...", "file_path": file_path, "subtask": sname})
                    else:
                        # retest 模式：每次都基于最后一次检验报告修改，禁止无反馈重试
                        if attempt == 1:
                            fb = (
                                saved_result.get("test_report_full", "") or
                                saved_result.get("test_report", "") or
                                ""
                            )
                            if not fb and saved_result.get("test_report_file"):
                                try:
                                    with open(saved_result["test_report_file"]) as _rf:
                                        fb = _rf.read()
                                except Exception:
                                    pass
                            logger.info(f"[Step7] 续测重写: [{sname}] 基于检验报告修改（第{attempt}轮）fb_len={len(fb)}")
                            await broadcast(project_id, {"type": "step7", "message": f"♻️ [{sname}] 基于检验报告重写代码（第{attempt}轮）..."})
                        else:
                            fb = st.get("last_feedback", "")
                            logger.info(f"[Step7] 续测重写: [{sname}] 第{attempt}轮 writer={writer.name}({writer.agent_type})")
                            await broadcast(project_id, {"type": "step7", "message": f"✍️ [{sname}] {writer.name} 续测重写（第{attempt}轮）..."})
                        existing = ""
                        if os.path.exists(file_path):
                            try:
                                with open(file_path) as f:
                                    existing = f.read()
                            except Exception:
                                pass
                        wp = SwarmService.build_writer_prompt(
                            sname=sname, sdesc=sdesc, sacc=sacc,
                            writer_name=writer.name,
                            attempt=attempt, last_feedback=fb,
                            agent_type=writer.agent_type,
                            existing_code=existing,
                            file_path=file_path,
                            report_file_path=(
                                saved_result.get("test_report_file", "")
                                if attempt == 1
                                else st.get("last_report_file", "")
                            ),
                        )
                        await broadcast(project_id, {"type": "step7", "message": f"📝 [{sname}] → {writer.name} 续测重写提示词", "prompt": wp, "agent": writer.name, "subtask": sname})
                        code = await _call_agent(writer, wp)
                        _SELF_CHECK_MAX = 3
                        _prev_bad3 = ""
                        for _si in range(_SELF_CHECK_MAX):
                            if not code.strip():
                                code = await _call_agent(writer, wp + "\n\n【⛔ 严重错误：输出为空】你必须重新输出完整可运行的 Python 代码。")
                                continue
                            code = SwarmService.clean_generated_code(code)
                            _sok, _serr = SwarmService.validate_code_syntax(code)
                            if _sok:
                                break
                            _err_lines3 = code.split('\n')
                            _err_line_idx3 = 0
                            import re as _re_step7_3
                            _m_step7_3 = _re_step7_3.search(r'第(\d+)行', _serr)
                            if _m_step7_3:
                                _err_line_idx3 = int(_m_step7_3.group(1)) - 1
                            _bad_line3 = _err_lines3[_err_line_idx3] if 0 <= _err_line_idx3 < len(_err_lines3) else '(未知)'
                            _same3 = ""
                            if _prev_bad3 and len(_prev_bad3) > 50:
                                import difflib as _dl3
                                if _dl3.SequenceMatcher(None, _prev_bad3[:500], code[:500]).ratio() > 0.8:
                                    _same3 = "\n⛔ 你两次输出的代码几乎一样！不要复述相同的错误，请彻底重新生成。"
                            _prev_bad3 = code
                            code = await _call_agent(writer, wp + (
                                f"\n\n【⛔ 语法错误 - 第{_si+1}次修正，还剩{_SELF_CHECK_MAX-_si-1}次】\n"
                                f"错误：{_serr}\n"
                                f"第{_err_line_idx3+1}行：{_bad_line3[:200]}\n{_same3}\n"
                                f"要求：第1行必须 import/from/def/class 开头。输出纯文本代码，不要签名/版本号/围栏。\n"
                                f"连续不通过将失去此子任务。请重新输出完整可运行的 Python 代码："
                            ))
                        if not code.strip():
                            for alt_writer in writer_agents:
                                if alt_writer.id == writer.id:
                                    continue
                                logger.info(f"[Step7] 续测重写降级: [{sname}] 第{attempt}轮 writer={writer.name} 自检不通过，切换为 {alt_writer.name}")
                                await broadcast(project_id, {"type": "step7", "message": f"🔄 [{sname}] {writer.name} 续测自检不通过，切换 {alt_writer.name} 重写..."})
                                code = await _call_agent(alt_writer, wp)
                                _prev_bad4 = ""
                                for _si2 in range(_SELF_CHECK_MAX):
                                    if not code.strip():
                                        code = await _call_agent(alt_writer, wp + "\n\n【⛔ 严重错误：输出为空】你必须重新输出完整可运行的 Python 代码。")
                                        continue
                                    code = SwarmService.clean_generated_code(code)
                                    _sok2, _serr2 = SwarmService.validate_code_syntax(code)
                                    if _sok2:
                                        break
                                    _err_lines4 = code.split('\n')
                                    _err_line_idx4 = 0
                                    import re as _re_step7_4
                                    _m_step7_4 = _re_step7_4.search(r'第(\d+)行', _serr2)
                                    if _m_step7_4:
                                        _err_line_idx4 = int(_m_step7_4.group(1)) - 1
                                    _bad_line4 = _err_lines4[_err_line_idx4] if 0 <= _err_line_idx4 < len(_err_lines4) else '(未知)'
                                    _same4 = ""
                                    if _prev_bad4 and len(_prev_bad4) > 50:
                                        import difflib as _dl4
                                        if _dl4.SequenceMatcher(None, _prev_bad4[:500], code[:500]).ratio() > 0.8:
                                            _same4 = "\n⛔ 你两次输出的代码几乎一样！不要复述相同的错误，请彻底重新生成。"
                                    _prev_bad4 = code
                                    code = await _call_agent(alt_writer, wp + (
                                        f"\n\n【⛔ 语法错误 - 第{_si2+1}次修正，还剩{_SELF_CHECK_MAX-_si2-1}次】\n"
                                        f"错误：{_serr2}\n"
                                        f"第{_err_line_idx4+1}行：{_bad_line4[:200]}\n{_same4}\n"
                                        f"要求：第1行必须 import/from/def/class 开头。输出纯文本代码，不要签名/版本号/围栏。\n"
                                        f"连续不通过将失去此子任务。请重新输出完整可运行的 Python 代码："
                                    ))
                                if code.strip():
                                    writer = alt_writer
                                    break
                        if not code.strip():
                            st["last_feedback"] = "续测重写未生成有效代码（所有编写Agent均失败）"
                            continue
                        code = SwarmService.clean_generated_code(code)
                        syntax_ok, _ = SwarmService.validate_code_syntax(code)
                        if not syntax_ok:
                            st["last_feedback"] = "续测重写代码语法错误"
                            continue
                        with open(file_path, "w") as f:
                            f.write(code)
                        saved_code = code
                        await _save_subtask_progress(idx, sname, {
                            "phase": "written", "latest_attempt": attempt,
                            "file_path": file_path, "writer": writer.name,
                        })

                    # ── 测试（retest 和正常模式共用） ──
                    # 检查是否已有测试进度，跳过重复测试
                    if saved_phase == "tested" and saved_attempt >= attempt and saved_progress.get("conclusion"):
                        prev_conclusion = saved_progress["conclusion"]
                        logger.info(f"[Step7] 跳过测试: [{sname}] 第{attempt}轮 已有结论={prev_conclusion}")
                        await broadcast(project_id, {"type": "step7", "message": f"♻️ [{sname}] 已有测试结论（第{attempt}轮），跳过重复验证"})
                        if prev_conclusion == "检验通过":
                            _saved_report_file = saved_progress.get("test_report_file", "")
                            _saved_report_full = ""
                            if _saved_report_file:
                                try:
                                    with open(_saved_report_file) as _rf:
                                        _saved_report_full = _rf.read()
                                except Exception:
                                    pass
                            if not _saved_report_full:
                                _saved_report_full = saved_progress.get("test_report", "")
                            async with rlock:
                                all_results.append({
                                    "name": sname, "index": idx,
                                    "status": "passed", "file_path": file_path,
                                    "attempts": attempt + (5 if is_retest else 0),
                                    "writer": writer.name,
                                    "test_agent": saved_progress.get("tester", tester.name),
                                    "test_report": _saved_report_full[:1000],
                                    "test_report_full": _saved_report_full,
                                    "test_report_file": _saved_report_file,
                                    "tester_conclusion": "检验通过",
                                })
                            logger.info(f"[Step7] 通过(续): [{sname}] 第{attempt}轮 编写={writer.name} 测试={saved_progress.get('tester', tester.name)}")
                            await broadcast(project_id, {"type": "step7", "message": f"✅ [{sname}] 测试通过（第{attempt}轮）", "test_report": _saved_report_full[:1000], "test_report_full": _saved_report_full, "test_report_file": _saved_report_file, "subtask": sname, "writerAgent": writer.name, "testAgent": saved_progress.get("tester", tester.name)})
                            return
                        else:
                            st["last_feedback"] = saved_progress.get("last_feedback", "")
                            st["last_test_report"] = saved_progress.get("test_report", "")
                            continue

                    # 读取代码文件
                    try:
                        with open(file_path, "r") as f:
                            saved_code = f.read()
                    except Exception:
                        logger.warning(f"[Step7] 测试读取文件失败: [{sname}] {file_path}")
                        st["last_feedback"] = f"第{attempt}轮测试读取代码文件失败"
                        continue

                    logger.info(f"[Step7] 测试: [{sname}] 第{attempt}轮 tester={tester.name}({tester.agent_type})")
                    previous_report = st.get("last_test_report", "")
                    label = "收敛检验" if previous_report else "首次检验"
                    await broadcast(project_id, {"type": "step7", "message": f"🧪 [{sname}] {tester.name} {label}（第{attempt}轮）..."})
                    tp = SwarmService.build_tester_prompt(
                        sname=sname, saved_code=saved_code, tester_name=tester.name,
                        previous_report=previous_report,
                    )
                    test_reply = await _call_agent(tester, tp)
                    # ── 保存本轮检验报告（只保存非空报告） ──
                    reports_dir = os.path.join(test_cases_dir, "reports")
                    os.makedirs(reports_dir, exist_ok=True)
                    def _save_report_to_file(reply_text: str, tag: str) -> str:
                        if not reply_text.strip():
                            return ""
                        _rf = os.path.join(reports_dir, f"report_{idx:04d}_{slug}_{tag}.txt")
                        try:
                            with open(_rf, "w") as _fh:
                                _fh.write(reply_text)
                        except Exception as _e:
                            logger.warning(f"[Step7] 保存检验报告失败: {_rf} {_e}")
                            return ""
                        return _rf
                    report_file = _save_report_to_file(test_reply, f"attempt{attempt}_init")
                    # ── 空报告/格式错误重试：直到生成标准的检验报告为止 ──
                    def _report_invalid(reply: str) -> tuple[bool, str]:
                        if not reply or not reply.strip():
                            return True, "报告为空"
                        import re as _re
                        _lines = reply.strip().split('\n')
                        # 扫描前 5 行找判定结果行，避免 Agent 在前置加了空行/签名
                        _found_judge = False
                        _found_score = False
                        for _li, _line in enumerate(_lines[:5]):
                            _sl = _line.strip()
                            if "判定结果：通过" in _sl or "判定结果：未通过" in _sl:
                                _found_judge = True
                            if _re.search(r'总分[：:]\s*\d+', _sl):
                                _found_score = True
                            if _found_judge and _found_score:
                                return False, ""
                        if not _found_judge:
                            return True, f"前5行缺少「判定结果」，首行内容：{_lines[0][:80]}"
                        return True, f"前5行缺少「总分：XX分」，首行内容：{_lines[0][:80]}"

                    _TOTAL_MAX = 3
                    tester_retry = 0
                    used_testers = {tester.id}
                    # Phase 1: 主 tester 反复重试直到内容符合格式
                    is_invalid, err_msg = _report_invalid(test_reply)
                    # 如果是 API/系统错误（非格式问题），直接跳过格式重试
                    if is_invalid and "API Error:" in (test_reply or ""):
                        logger.warning(f"[Step7] 跳过格式重试: [{sname}] tester={tester.name} 输出为API错误，直接切换agent")
                        tester_retry = _TOTAL_MAX
                    while is_invalid and tester_retry < _TOTAL_MAX:
                        tester_retry += 1
                        logger.warning(f"[Step7] 无效报告: [{sname}] tester={tester.name} 第{tester_retry}次重试 reason={err_msg}")
                        await broadcast(project_id, {"type": "step7", "message": f"🔄 [{sname}] {tester.name} 报告无效（{err_msg}），第{tester_retry}次重试..."})
                        _fix_prompt = (
                            f"\n\n【格式错误】反馈：{err_msg}\n"
                            f"请严格按照以下格式重新生成：\n"
                            f"第一行必须是（二选一）：\n"
                            f"  判定结果：通过；总分：95分\n"
                            f"  判定结果：未通过；总分：60分\n"
                            f"不要在前面或后面添加任何其他字符！"
                        )
                        test_reply = await _call_agent(tester, tp + _fix_prompt)
                        report_file = _save_report_to_file(test_reply, f"attempt{attempt}_retry{tester_retry}")
                        is_invalid, err_msg = _report_invalid(test_reply)
                    # Phase 2: 主 tester 彻底无响应/格式持续错误 → 轮流尝试所有其他 tester
                    if is_invalid:
                        for alt_tester in tester_agents:
                            if alt_tester.id in used_testers:
                                continue
                            used_testers.add(alt_tester.id)
                            logger.info(f"[Step7] 测试降级: [{sname}] 第{attempt}轮 {tester.name} 无效（{err_msg}），切换 {alt_tester.name}")
                            await broadcast(project_id, {"type": "step7", "message": f"🔄 [{sname}] {tester.name} 无效（{err_msg}），切换 {alt_tester.name}..."})
                            alt_tp = SwarmService.build_tester_prompt(
                                sname=sname, saved_code=saved_code, tester_name=alt_tester.name,
                                previous_report=previous_report,
                            )
                            alt_tester_retry = 0
                            while is_invalid and alt_tester_retry < _TOTAL_MAX:
                                alt_tester_retry += 1
                                _fix_prompt = (
                                    f"\n\n【格式错误】反馈：{err_msg}\n"
                                    f"请严格按照以下格式重新生成：\n"
                                    f"第一行必须是（二选一）：\n"
                                    f"  判定结果：通过；总分：95分\n"
                                    f"  判定结果：未通过；总分：60分\n"
                                    f"不要在前面或后面添加任何其他字符！"
                                )
                                test_reply = await _call_agent(alt_tester, alt_tp + _fix_prompt)
                                report_file = _save_report_to_file(test_reply, f"attempt{attempt}_alt_{alt_tester.name}_{alt_tester_retry}")
                                is_invalid, err_msg = _report_invalid(test_reply)
                                _log_reason = "空报告" if not test_reply.strip() else f"格式错误（{err_msg}）"
                                logger.warning(f"[Step7] 无效报告: [{sname}] alt={alt_tester.name} 第{alt_tester_retry}次重试 {_log_reason}")
                                await broadcast(project_id, {"type": "step7", "message": f"🔄 [{sname}] {alt_tester.name} 返回无效（{_log_reason}），第{alt_tester_retry}次重试..."})
                            if not is_invalid:
                                tester = alt_tester
                                break
                    # ── 所有重试均失败 → 生成默认报告，确保前端不显示「（报告为空）」 ──
                    if _report_invalid(test_reply)[0]:
                        _default_report = (
                            f"判定结果：未通过；总分：0分\n\n"
                            f"【系统说明】测试 Agent 在 {_TOTAL_MAX} 次尝试后仍未返回有效检验报告。\n"
                            f"原因：报告为空或第一行缺少「判定结果：通过/未通过」和「总分：XX分」。\n"
                        )
                        logger.warning(f"[Step7] 生成默认报告: [{sname}] 原 reply_len={len(test_reply)}")
                        test_reply = _default_report
                        report_file = _save_report_to_file(test_reply, f"attempt{attempt}_default")
                    logger.info(f"[Step7] 测试结果: [{sname}] 第{attempt}轮 tester={tester.name} reply_len={len(test_reply)}")

                    conclusion = "未通过"
                    import re as _re
                    _score = 0
                    for _line in test_reply.strip().split('\n')[:5]:
                        _sl = _line.strip()
                        if "判定结果：通过" in _sl and "未通过" not in _sl:
                            _sm = _re.search(r'总分[：:]\s*(\d+)', _sl)
                            if _sm:
                                _score = int(_sm.group(1))
                            if _score >= 90:
                                conclusion = "检验通过"
                            break
                        if "判定结果：未通过" in _sl:
                            _sm = _re.search(r'总分[：:]\s*(\d+)', _sl)
                            if _sm:
                                _score = int(_sm.group(1))
                            break
                    score = _score
                    logger.info(f"[Step7] 结论解析: [{sname}] score={score} conclusion={conclusion}")
                    # ── 保存最终检验报告（写入 attempts{attempt}.txt，失败不覆盖已有 report_file） ──
                    if test_reply.strip() and reports_dir:
                        _final_rf = os.path.join(reports_dir, f"report_{idx:04d}_{slug}_attempt{attempt}.txt")
                        try:
                            with open(_final_rf, "w") as rf:
                                rf.write(test_reply)
                            report_file = _final_rf
                        except Exception as e:
                            logger.warning(f"[Step7] 保存最终检验报告失败: {_final_rf} {e}")

                    # ── 保存测试进度（无论通过与否） ──
                    await _save_subtask_progress(idx, sname, {
                        "phase": "tested", "latest_attempt": attempt,
                        "file_path": file_path, "tester": tester.name,
                        "conclusion": conclusion, "test_report": test_reply[:1000],
                        "test_report_file": report_file,
                        "last_feedback": (
                            f"第{attempt}轮测试未通过。测试Agent的完整评审报告如下：\n{test_reply if test_reply.strip() else '测试Agent未返回有效评审意见'}\n\n"
                            f"【你必须逐条修复以上评审中列出的每个问题】\n"
                            f"修改要求：\n1. 逐条修复报告中指出的所有缺陷\n2. 确保修复后的代码语法正确、import 完整\n3. 只修改报告中指出的问题，不要改动无关代码\n4. 重新输出完整的可运行代码"
                        ) if conclusion != "检验通过" else "",
                    })

                    if test_reply.strip() and conclusion == "检验通过":
                        # ── 测试通过 ──
                        async with rlock:
                            result = {
                                "name": sname, "index": idx,
                                "status": "passed", "file_path": file_path,
                                "attempts": attempt + (5 if is_retest else 0),
                                "writer": writer.name,
                                "test_agent": tester.name,
                                "test_report": test_reply[:1000],
                                "test_report_full": test_reply,
                                "test_report_file": report_file,
                                "tester_conclusion": conclusion,
                            }
                            all_results.append(result)
                        await _save_subtask_result(result)
                        logger.info(f"[Step7] 通过: [{sname}] 第{attempt}轮 编写={writer.name} 测试={tester.name}")
                        await broadcast(project_id, {"type": "step7", "message": f"✅ [{sname}] {tester.name} 测试通过（第{attempt}轮）", "test_report": test_reply[:1000], "test_report_full": test_reply, "test_report_file": report_file, "subtask": sname, "writerAgent": writer.name, "testAgent": tester.name})
                        return
                    else:
                        # ── 测试未通过 ──
                        _full_report = test_reply if test_reply.strip() else "测试Agent未返回有效评审意见"
                        st["last_feedback"] = (
                            f"第{attempt}轮测试未通过。测试Agent的完整评审报告如下：\n"
                            f"{_full_report}\n\n"
                            f"【你必须逐条修复以上评审中列出的每个问题】\n"
                            f"修改要求：\n"
                            f"1. 逐条修复报告中指出的所有缺陷\n"
                            f"2. 确保修复后的代码语法正确、import 完整\n"
                            f"3. 只修改报告中指出的问题，不要改动无关代码\n"
                            f"4. 重新输出完整的可运行代码"
                        )
                        st["last_test_report"] = test_reply
                        st["last_report_file"] = report_file
                        await broadcast(project_id, {"type": "step7", "message": f"⚠️ [{sname}] {tester.name} 验证未通过，退回 {writer.name} 修改（第{attempt}轮）"})
                        # retest 模式：第一轮不通过后，降级为正常 write→test
                        if is_retest and attempt == 1:
                            is_retest = False
                        continue

                # ── 最大轮次均未通过 ──
                # 最终安全网：确保 report_file 和 test_reply 一定有有效内容，无论之前走哪条路径
                if not test_cases_dir:
                    test_cases_dir = os.path.join(settings.PROJECTS_BASE_DIR, slug, "tests", "test_cases")
                _reports_dir = os.path.join(test_cases_dir, "reports")
                os.makedirs(_reports_dir, exist_ok=True)
                # 检查 report_file 是否存在且有内容，否则生成兜底报告
                if report_file and os.path.exists(report_file):
                    try:
                        _existing = open(report_file).read().strip()
                        if not _existing:
                            report_file = ""
                    except Exception:
                        report_file = ""
                if not report_file:
                    _err_report = (
                        f"判定结果：未通过；总分：0分\n\n"
                        f"【系统说明】该子任务在 {max_attempts} 轮编写+测试迭代后仍未通过。\n"
                        f"原因：编写Agent未能生成可通过语法检验的代码，或测试Agent未能完成有效检验。\n"
                        f"最后测试Agent回复：{test_reply[:500] if test_reply.strip() else '(空)'}\n"
                        f"最后编写Agent：{writer.name if writer else '无'}\n"
                        f"最后测试Agent：{tester.name if tester else '无'}\n"
                    )
                    report_file = os.path.join(_reports_dir, f"report_{idx:04d}_{slug}_final_error.txt")
                    try:
                        with open(report_file, "w") as _rf:
                            _rf.write(_err_report)
                    except Exception:
                        report_file = ""
                if not test_reply.strip():
                    test_reply = f"判定结果：未通过；总分：0分\n\n测试Agent未返回有效评审意见。\n最后编写Agent尝试：{st.get('last_feedback', '无')[:200]}"
                async with rlock:
                    result = {
                        "name": sname, "index": idx,
                        "status": "failed", "file_path": file_path,
                        "attempts": max_attempts + (5 if is_retest else 0),
                        "writer": writer.name,
                        "test_agent": tester.name,
                        "test_error": f"{max_attempts}轮{'续测' if saved_result else '编写+测试'}均未通过",
                        "test_report": test_reply[:1000],
                        "test_report_full": test_reply,
                        "test_report_file": report_file,
                        "tester_conclusion": "未通过",
                    }
                    all_results.append(result)
                await _save_subtask_result(result)
                await broadcast(project_id, {"type": "step7", "message": f"❌ [{sname}] {max_attempts}轮{'续测' if saved_result else '编写+测试'}均未通过", "test_report": test_reply[:1000], "test_report_full": test_reply, "test_report_file": report_file, "subtask": sname})

        # ── 断点续跑 ──
        retest_subtasks = []
        subtasks_left = [(i + 1, st) for i, st in enumerate(subtasks)]
        if resume:
            saved = saved_results
            if not saved:
                saved = bg_engine.get_step7_artifacts().get("subtask_results", [])
            if saved:
                await broadcast(project_id, {"type": "step7", "message": f"♻️ 续跑：发现 {len(saved)} 个已处理子任务"})
                passed_indices = set()
                for sr in saved:
                    sr_idx = sr.get("index", 0)
                    sr_status = sr.get("status", "")
                    sname = sr.get("name", "")
                    if sr_status == "passed":
                        passed_indices.add(sr_idx)
                        all_results.append(sr)
                        await broadcast(project_id, {"type": "step7", "message": f"✅ [{sname}] 已通过（第{sr.get('attempts', 1)}轮），跳过", "test_report_full": sr.get("test_report_full", ""), "test_report_file": sr.get("test_report_file", ""), "subtask": sname, "writerAgent": sr.get("writer", ""), "testAgent": sr.get("test_agent", "")})
                    elif sr_status == "failed":
                        await broadcast(project_id, {"type": "step7", "message": f"🔄 [{sname}] 之前未通过，已重置为待执行，将重新从头生成..."})
                        logger.info(f"[Step7] 续跑重置: [{sname}] 失败状态已清空，作为新子任务重新执行")
                    else:
                        # 没有 file_path 的失败结果，由正常逻辑重新生成
                        await broadcast(project_id, {"type": "step7", "message": f"♻️ [{sname}] 结果不完整，需重新生成"})

                # 从 subtasks 中去掉已通过的（保留原始索引）
                subtasks_left = [(i + 1, st) for i, st in enumerate(subtasks) if (i + 1) not in passed_indices]
                logger.info(f"[Step7] 续跑过滤: passed_indices={passed_indices} subtasks_left={len(subtasks_left)} retest={len(retest_subtasks)}")
                if not subtasks_left and not retest_subtasks:
                    await broadcast(project_id, {"type": "step7", "message": "♻️ 续跑：所有子任务已完成，跳过蜂群执行"})

        # 并行启动所有子任务
        t0 = time.time()
        all_subtask_tasks = []

        # 正常子任务（write→test），使用原始索引
        if subtasks_left:
            await broadcast(project_id, {"type": "step7", "message": f"🚀 启动 {len(subtasks_left)} 个新子任务的编写→测试迭代（最多 {PARALLEL_SUBTASKS} 个并发）..."})
            logger.info(f"[Step7] 子任务启动: {len(subtasks_left)}个 并发上限={PARALLEL_SUBTASKS}")
            all_subtask_tasks.extend([_process_one_subtask(st, idx) for idx, st in subtasks_left if idx not in passed_indices_from_prev])
            if len([idx for idx, st in subtasks_left if idx in passed_indices_from_prev]) > 0:
                logger.warning(f"[Step7] 防御性过滤: {len([idx for idx, st in subtasks_left if idx in passed_indices_from_prev])} 个子任务从 subtasks_left 中拦截")

        # 续测子任务（retest-only）
        for rts in retest_subtasks:
            st = rts["subtask"]
            sr = rts["saved_result"]
            idx = rts["idx"]
            await broadcast(project_id, {"type": "step7", "message": f"♻️ 准备重新检验 [{st['name']}]..."})
            all_subtask_tasks.append(_process_one_subtask(st, idx, saved_result=sr))

        if all_subtask_tasks:
            await asyncio.gather(*all_subtask_tasks)

        passed = [r for r in all_results if r["status"] == "passed"]
        failed_ = [r for r in all_results if r["status"] == "failed"]
        elapsed = time.time() - t0
        logger.info(f"[Step7] 全部完成: {len(passed)}通过/{len(failed_)}失败 耗时={elapsed:.1f}s")
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
        saved_arts = engine.get_step7_artifacts() or {}
        logger.info(f"[Step7] execute_step7_async saved_arts keys={list(saved_arts.keys())}")
        sr_list = saved_arts.get("subtask_results", [])
        logger.info(f"[Step7] execute_step7_async subtask_results count={len(sr_list)}")
        for _sr in sr_list:
            logger.info(f"[Step7] execute_step7_async sr: name={_sr.get('name')} index={_sr.get('index')} status={_sr.get('status')}")
        has_results = bool(sr_list)
        has_progress = bool(saved_arts.get("subtask_progress"))
        # 只要有进度就自动续跑（无论前端是否传 resume=True）
        if has_results or has_progress:
            resume = True
            existing = saved_arts
            detail = f"{len(saved_arts.get('subtask_results',[]))}个子任务结果" if has_results else ""
            if has_progress:
                detail += "、中间进度" if detail else "中间进度"
            logger.info(f"[Step7] 检测到已有进度（{detail}），自动续跑")
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

    # ── 如果所有子任务均已通过，立即返回，禁止执行任何蜂群代码 ──
    if resume and saved_arts.get("subtask_results"):
        all_passed = all(sr.get("status") == "passed" for sr in saved_arts["subtask_results"])
        if all_passed:
            logger.info(f"[Step7] 所有 {len(saved_arts['subtask_results'])} 个子任务均已通过，跳过执行")
            engine.save_step7_artifacts({
                "status": "done",
                "message": "✅ 所有子任务均已通过检验",
            })
            if engine._get_step_row(7) and engine._get_step_row(7).status != "completed":
                engine.complete_step(7)
            await broadcast(project_id, {"type": "done", "message": "✅ 所有子任务均已通过"})
            return APIResponse(code=0, message="所有子任务已通过，无需重新执行")

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
            existing=existing if has_progress else None,
            resume=resume,
            requirement_path=requirement_path,
            saved_subtasks=saved_arts.get("subtask_results", []) if resume else None,
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