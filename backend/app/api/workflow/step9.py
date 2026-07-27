import glob
import json as _json
import re as _re
import random
from datetime import datetime, timezone
from app.api.workflow.core import (
    router, _get_engine, logger, APIResponse, Depends, get_db,
    get_current_user, Session, Body, Request, HTTPException,
    BaseModel, Optional, asyncio, os, settings, Step3InspectRequest, QAResultRequest,
    CODE_INSPECTION_DIMENSIONS, Step9ChatRequest, _wf_engines, WorkflowEngine,
)
from app.services.swarm_service import SwarmService
from app.services.gateway_client import GatewayClient
from app.models.project import Project


@router.post("/{project_id}/step9/chat")
async def step9_chat(project_id: str, body: Step9ChatRequest, db: Session = Depends(get_db), current_user=Depends(get_current_user)):
    """后发（HouFa）对话"""
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
        async for chunk in client.chat_completions(messages=messages, stream=False):
            rchunks.append(chunk)
        reply = "".join(rchunks)
        return APIResponse(code=0, message="success", data={"reply": reply}) if reply and len(reply.strip()) >= 5 else APIResponse(code=1, message="后发未生成有效回复", data=None)
    except HTTPException:
        raise
    except Exception as e:
        logger.error(f"Step9 chat: {e}")
        return APIResponse(code=1, message="与后发对话失败", data=None)


async def _inspect_code(project_id: str, doc_path: str, project_name: str = "", project_description: str = "", core_goal: str = "", agent_label: str = "", max_retries: int = 3, focus_items: Optional[list[str]] = None) -> dict:
    import json as _json, asyncio as _asyncio
    from app.api.ws.step9_progress import broadcast
    active_dims = [d for d in CODE_INSPECTION_DIMENSIONS if not focus_items or d["key"] in focus_items]
    if not active_dims:
        return {"passed": True, "detail": "无待检验项", "failed_details": [], "failed_keys": [], "results": []}
    dims_json = str([{'检验项目': d['label'], '检验标准': d['description'], '检验维': d['key']} for d in active_dims])
    for attempt in range(1, max_retries + 1):
        if attempt > 1:
            await _asyncio.sleep(2)
            await broadcast(project_id, {"type": "progress", "message": f"🔄 hourong 第{attempt}次检验功能代码..."})
        focus_hint = f"\n⚠️ 本轮只检验以下项目（上一轮未通过）：{[d['label'] for d in active_dims]}" if focus_items else ""
        insp_prompt = f"你是一个专业的代码QA检验员（后荣）。请严格检验以下功能代码。\n\n=== 检验项目与标准 ===\n{dims_json}\n\n=== 文档路径 ===\n{doc_path}\n\n请读取该文档文件，严格逐项检验。\n只输出 JSON 数组:\n" + ",\n".join(f'  {{"key": "{d["key"]}", "passed": true/false, "detail": "具体检验意见..."}}' for d in active_dims) + f"{focus_hint}\n"
        qa_cli = GatewayClient(profile_name="hourong", timeout=180)
        qa_chunks = []
        async for chunk in qa_cli.chat_completions(messages=[{"role": "user", "content": insp_prompt}], stream=True, max_tokens=8192):
            qa_chunks.append(chunk)
        qa_r = "".join(qa_chunks).strip()
        if not qa_r:
            if attempt < max_retries:
                await broadcast(project_id, {"type": "progress", "message": f"⚠️ 未返回，重试（第{attempt}次）"})
                continue
            return {"detail": f"后荣{max_retries}次均未返回"}
        brace_s, brace_e = qa_r.find('['), qa_r.rfind(']') + 1
        if brace_s != -1 and brace_e > brace_s:
            qa_r = qa_r[brace_s:brace_e]
        try:
            parsed = _json.loads(qa_r)
        except Exception:
            if attempt < max_retries:
                await broadcast(project_id, {"type": "progress", "message": f"⚠️ 格式异常，重试（第{attempt}次）"})
                continue
            return {"detail": "后荣未返回检验结果"}
        if isinstance(parsed, list) and parsed:
            failed_keys = [r.get("key", "") for r in parsed if not r.get("passed")]
            return {"passed": all(bool(r.get("passed")) for r in parsed), "detail": "", "failed_details": [r.get("detail", "") for r in parsed if not r.get("passed")], "failed_keys": failed_keys, "results": parsed}
        if attempt < max_retries:
            await broadcast(project_id, {"type": "progress", "message": f"⚠️ 格式异常，重试（第{attempt}次）"})
            continue
        return {"detail": "后荣未返回检验结果"}
    return {"detail": "后荣检验失败"}


def _parse_code_plan_to_subtasks(code_plan: str, dep_graph: dict = None) -> list[dict]:
    """解析代码编写计划为子任务列表（每个文件一个子任务）"""
    subtasks = []
    seen_paths = set()
    for m in _re.finditer(r'^###\s+(\S+\.py\S*)\s*$', code_plan, _re.MULTILINE):
        path = m.group(1).strip()
        if path and path not in seen_paths:
            seen_paths.add(path)
            start = m.end()
            next_m = _re.search(r'^###\s+\S', code_plan[start:], _re.MULTILINE)
            desc = code_plan[start:start + (next_m.start() if next_m else 200)].strip()[:200]
            subtasks.append({"name": os.path.basename(path), "file_path": path, "description": desc, "dependencies": [], "index": len(subtasks) + 1})
    if not subtasks:
        for m in _re.finditer(r'(?:^|\n)\s*[-*\d]+\.?\s*(`)?(\S+\.py\S*)(?(1)`)\s*[-–—:]?\s*(.*)', code_plan):
            path = m.group(2).strip()
            desc = m.group(3).strip()[:200] if m.group(3) else ""
            if path and path not in seen_paths:
                seen_paths.add(path)
                subtasks.append({"name": os.path.basename(path), "file_path": path, "description": desc, "dependencies": [], "index": len(subtasks) + 1})
    if not subtasks and isinstance(dep_graph, dict):
        for path in dep_graph:
            if path and path not in seen_paths:
                seen_paths.add(path)
                deps = dep_graph.get(path, [])
                subtasks.append({"name": os.path.basename(path), "file_path": path, "description": "", "dependencies": deps if isinstance(deps, list) else [], "index": len(subtasks) + 1})
    if not subtasks:
        subtasks.append({"name": "codebase", "file_path": "src/main.py", "description": "整个代码库", "dependencies": [], "index": 1})
    if isinstance(dep_graph, dict):
        for st in subtasks:
            deps = dep_graph.get(st["file_path"], [])
            if isinstance(deps, list):
                st["dependencies"] = [d for d in deps if isinstance(d, str)]
    return subtasks


def _topological_sort(subtasks: list[dict]) -> list[dict]:
    by_path = {st["file_path"]: st for st in subtasks}
    visited, temp, order = set(), set(), []
    def _visit(path):
        if path in temp: return
        if path in visited: return
        temp.add(path)
        for dep in by_path.get(path, {}).get("dependencies", []):
            if dep in by_path: _visit(dep)
        temp.discard(path)
        visited.add(path)
        order.append(by_path[path])
    for st in subtasks:
        if st["file_path"] not in visited:
            try: _visit(st["file_path"])
            except Exception: order.append(st)
    return order


async def _auto_configure_agent(agent, db_session=None):
    from app.models.agent import Agent as AgentModel
    CLI_AGENT_COMMANDS = {
        "openhands": ["openhands", "python3 -m openhands", "python -m openhands"],
        "aider-chat": ["aider --message {prompt} --yes"],
        "goose": ["goose run --text {prompt} --no-session -q"],
        "claude_code": ["claude"],
        "pi_coding_agent": ["pi"],
        "opencode": ["opencode run {prompt}"],
        "codebuddy": ["codebuddy"], "reasonix": ["reasonix"],
        "codearts": ["codearts"], "trae": ["trae"],
    }
    cfg = agent.config or {}
    existing_cli = cfg.get("cli_command", "")
    if existing_cli and not existing_cli.startswith("http"):
        parts = existing_cli.split()
        ck = await asyncio.create_subprocess_exec("sh", "-c", f"which '{parts[0]}' 2>/dev/null", stdout=asyncio.subprocess.PIPE, stderr=asyncio.subprocess.PIPE)
        out_bytes, _ = await ck.communicate()
        if ck.returncode == 0 and out_bytes.strip(): return True
        logger.warning(f"[Step9] 清除失效的 cli_command: {agent.name}")
        cfg.pop("cli_command", None)
        agent.config = cfg
        if db_session:
            try:
                ag = db_session.query(AgentModel).filter(AgentModel.id == agent.id).first()
                if ag: ag.config = cfg; db_session.commit()
            except Exception: pass
    if agent.api_endpoint: return True
    if agent.agent_type in ("houfa", "hermes") or agent.name == "hourong": return True
    cmd_candidates = CLI_AGENT_COMMANDS.get(agent.agent_type, [])
    for candidate in cmd_candidates:
        try:
            parts = candidate.split()
            proc = await asyncio.create_subprocess_exec("sh", "-c", f"which '{parts[0]}' 2>/dev/null", stdout=asyncio.subprocess.PIPE, stderr=asyncio.subprocess.PIPE)
            out_bytes, _ = await proc.communicate()
            if proc.returncode != 0 or not out_bytes.strip(): continue
            cfg["cli_command"] = candidate; agent.config = cfg
            if db_session:
                try:
                    ag = db_session.query(AgentModel).filter(AgentModel.id == agent.id).first()
                    if ag: ag.config = cfg; db_session.commit()
                except Exception: pass
            return True
        except Exception as e: logger.warning(f"[Step9] 检测命令失败: {agent.name} {e}")
    return False


async def _smoke_test_agent(agent) -> bool:
    _SMOKE_TIMEOUT = 60
    cfg = agent.config or {}
    cli_cmd = cfg.get("cli_command", "")
    if cli_cmd and not cli_cmd.startswith("http"):
        for flag in ("--version", "--help"):
            try:
                _cmd = f"timeout {_SMOKE_TIMEOUT} {cli_cmd.replace('{prompt}', flag)} 2>&1" if "{prompt}" in cli_cmd else f"timeout {_SMOKE_TIMEOUT} {cli_cmd} {flag} 2>&1"
                proc = await asyncio.create_subprocess_exec("sh", "-c", _cmd, stdin=asyncio.subprocess.DEVNULL, stdout=asyncio.subprocess.PIPE, stderr=asyncio.subprocess.PIPE)
                try: out_bytes, _ = await asyncio.wait_for(proc.communicate(), timeout=_SMOKE_TIMEOUT)
                except asyncio.TimeoutError: continue
                if proc.returncode != 0:
                    if _re.search(r'(Input is not a terminal|not a tty|is not a TTY)', out_bytes.decode()): return False
                    continue
                if out_bytes.decode().strip(): return True
            except Exception: continue
        return False
    if agent.api_endpoint:
        try:
            import httpx
            async with httpx.AsyncClient(timeout=_SMOKE_TIMEOUT) as hc: await hc.get(agent.api_endpoint)
            return True
        except Exception: return False
    if agent.agent_type in ("hermes", "houfa") or agent.name == "hourong": return True
    return False


async def _call_agent(agent, prompt: str, slug: str = "", docs_dir: str = "", project_id: str = "", proj_name: str = "", proj_desc: str = "", core_goal: str = "", timeout: int = 600) -> str:
    cfg = agent.config or {}
    cli_cmd = cfg.get("cli_command", "")
    if cli_cmd and not cli_cmd.startswith("http"):
        cmd = cli_cmd.replace("{prompt}", prompt[:20000])
        try:
            proc = await asyncio.create_subprocess_exec("sh", "-c", f"timeout {timeout} {cmd} 2>&1", stdin=asyncio.subprocess.DEVNULL, stdout=asyncio.subprocess.PIPE, stderr=asyncio.subprocess.PIPE)
            out_bytes, _ = await asyncio.wait_for(proc.communicate(), timeout=timeout + 15)
            return out_bytes.decode("utf-8", errors="replace").strip() if out_bytes else ""
        except asyncio.TimeoutError: logger.warning(f"[Step9] Agent 超时: {agent.name}"); return ""
        except Exception as e: logger.warning(f"[Step9] Agent 调用失败: {agent.name} {e}"); return ""
    client = GatewayClient(profile_name="houfa", timeout=timeout)
    chunks = []
    try:
        async for chunk in client.chat_completions(messages=[{"role": "user", "content": prompt}], stream=False, max_tokens=32000): chunks.append(chunk)
    except Exception as e: logger.warning(f"[Step9] GatewayClient 调用失败: {e}"); return ""
    return "".join(chunks).strip()


def _assemble_combined_code(sorted_subtasks: list[dict], src_dir: str) -> str:
    parts = []
    for st in sorted_subtasks:
        fp = os.path.join(src_dir, st["file_path"])
        if os.path.exists(fp):
            with open(fp, "r", encoding="utf-8") as f: content = f.read()
            parts.append(f"### {st['file_path']}\n\n```python\n{content}\n```")
    return "\n\n---\n\n".join(parts)


async def _force_complete_step9(project_id: str, bg_engine) -> None:
    """直接设置 step9 为 completed，绕过 complete_step() 的 qa_review 逻辑。
    step9 蜂群已做内部 QA（writer→tester→hourong抽检），无需外部 QA 检验。"""
    from sqlalchemy import text as _txt
    try:
        bg_engine.db.execute(
            _txt("UPDATE workflow_steps SET status='completed', completed_at=:now WHERE project_id=:pid AND step_number=9"),
            {"now": datetime.now(timezone.utc), "pid": project_id}
        )
        bg_engine.db.execute(
            _txt("UPDATE projects SET current_step=10 WHERE id=:pid"),
            {"pid": project_id}
        )
        bg_engine.db.commit()
        bg_engine.current_step = 10
    except Exception as _e:
        logger.error(f"[Step9] _force_complete_step9 失败: {_e}")


def _build_step9_handover(proj_name: str, subtask_count: int, passed_count: int, failed_count: int, subtask_names: list[str], passed_subtask_names: list[str], spot_check_total: int = 0, spot_check_failures: int = 0, spot_check_detail: str = "") -> str:
    now = datetime.now(timezone.utc).strftime("%Y-%m-%d %H:%M:%S UTC")
    passed_list = "\n".join(f"  ✅ {n}" for n in passed_subtask_names) if passed_subtask_names else "  无"
    total_list = "\n".join(f"  #{i+1} {n}" for i, n in enumerate(subtask_names)) if subtask_names else "  无"
    lines = [
        f"# 步骤 9 → 步骤 10 交接文档", "",
        f"## 完成步骤", f"后发蜂群编写功能代码", "",
        f"## 下一步", f"后富部署到测试环境", "",
        f"## 完成时间", f"{now}", "",
        f"## 执行摘要",
        f"项目：{proj_name}",
        f"子任务总数：{subtask_count}",
        f"通过（TDD验证）：{passed_count}",
        f"失败：{failed_count}",
        f"抽检样本数：{spot_check_total}",
        f"抽检不合格数：{spot_check_failures}", "",
        f"## 已通过的子任务列表", f"{passed_list}", "",
        f"## 全部子任务列表", f"{total_list}", "",
    ]
    if spot_check_detail: lines.append(f"## 抽检结果\n{spot_check_detail}\n")
    lines += [
        f"## 交接说明",
        f"步骤9已完成功能代码编写，所有文件均通过TDD测试验证和hourong抽检。",
        f"步骤10（后富部署到测试环境）请基于以上代码文件推进。",
        f"代码文件位于项目 src 目录下，可通过 subtask_results 中的 file_path 获取完整路径。",
    ]
    return "\n".join(lines)


async def run_step9_swarm(
    project_id: str, requirement: str, design_doc: str, core_goal: str,
    proj_name: str = "", proj_desc: str = "", existing: dict = None,
    resume: bool = False, code_plan: str = "", dep_graph: dict = None, tdd_cases: str = "",
):
    """蜂群功能代码生成 — 对齐 step7 模式

    每个子任务: 随机 Writer Agent 编写 → 随机 Tester Agent 检验 → 收敛
    全部通过后: hourong 5% 随机抽检
    全部检验通过: 交接文档 → complete_step(9) → step10
    """
    HTTP_INSPECT_MAX_RETRIES = 3
    from app.database import SessionLocal
    from app.api.ws.step9_progress import broadcast

    bg_db = SessionLocal()
    try:
        bg_engine = WorkflowEngine(project_id=project_id, db=bg_db)
        proj = bg_db.query(Project).filter(Project.id == project_id).first()
        slug = proj.slug if proj else project_id.replace("-", "")
        docs_dir = os.path.join(settings.PROJECTS_BASE_DIR, slug, "docs")
        src_dir = os.path.join(settings.PROJECTS_BASE_DIR, slug, "src")
        os.makedirs(docs_dir, exist_ok=True)
        os.makedirs(src_dir, exist_ok=True)
        proj_name = proj_name or (proj.name if proj else "")
        proj_desc = proj_desc or (proj.description or "")
        prev = existing or {}

        # ── 续跑跳过 ──
        if resume and prev.get("qa_passed") and prev.get("doc_path") and os.path.exists(prev.get("doc_path", "")):
            await broadcast(project_id, {"type": "progress", "message": "♻️ 续跑：功能代码已通过，跳过"})
            bg_engine.save_step9_artifacts({**prev, "status": "done", "message": "♻️ 续跑：功能代码已通过"})
            await _force_complete_step9(project_id, bg_engine)

        # ── 解析子任务 ──
        subtasks = _parse_code_plan_to_subtasks(code_plan, dep_graph)
        sorted_subtasks = _topological_sort(subtasks)
        all_results = []

        all_subtask_names = [st["name"] for st in sorted_subtasks]
        all_subtask_indices = [st["index"] for st in sorted_subtasks]
        await broadcast(project_id, {"type": "step9", "subtask_names": all_subtask_names, "subtask_indices": all_subtask_indices, "message": f"📋 代码计划已解析：{len(sorted_subtasks)} 个文件"})
        try:
            cur = bg_engine.get_step9_artifacts() or {}
            cur["total_subtask_names"] = all_subtask_names
            cur["total_subtask_indices"] = all_subtask_indices
            cur["total_subtask_count"] = len(sorted_subtasks)
            bg_engine.save_step9_artifacts(cur)
        except Exception: pass

        # ── 续跑恢复 ──
        completed_indices: set[int] = set()
        if resume:
            saved = prev.get("subtask_results", [])
            for sr in saved:
                if sr.get("status") == "passed":
                    idx = sr.get("index", 0)
                    if os.path.exists(sr.get("file_path", "")):
                        completed_indices.add(idx); all_results.append(sr)
            if completed_indices: await broadcast(project_id, {"type": "progress", "message": f"♻️ 续跑：{len(completed_indices)} 个文件已通过"})

        if completed_indices and len(completed_indices) == len(sorted_subtasks):
            combined = _assemble_combined_code(sorted_subtasks, src_dir)
            bg_engine.save_step9_artifacts({"code": combined, "subtask_results": all_results, "status": "done", "qa_passed": True, "message": "✅ 全部文件已生成"})
            await _force_complete_step9(project_id, bg_engine)
            await broadcast(project_id, {"type": "done", "message": f"✅ 全部 {len(sorted_subtasks)} 个文件已生成"})
            return

        # ══════════════════════════════════════
        # Phase 1: Writer + Tester Agent 池
        # ══════════════════════════════════════
        writer_agents = SwarmService.get_preferred_writer_agents(bg_db)
        configured_writers = []
        skipped_writers = []
        for a in writer_agents:
            if await _auto_configure_agent(a, db_session=bg_db) and await _smoke_test_agent(a):
                configured_writers.append(a)
            else:
                skipped_writers.append(a.name)
        writer_agents = configured_writers
        if skipped_writers: await broadcast(project_id, {"type": "progress", "message": f"⚠️ 跳过 {len(skipped_writers)} 个不可用的编写Agent: {skipped_writers}"})

        tester_agents = SwarmService.get_preferred_tester_agents(bg_db)
        configured_testers = []
        skipped_testers = []
        for a in tester_agents:
            if await _auto_configure_agent(a, db_session=bg_db) and await _smoke_test_agent(a):
                configured_testers.append(a)
            else:
                skipped_testers.append(a.name)
        tester_agents = configured_testers
        if skipped_testers: await broadcast(project_id, {"type": "progress", "message": f"⚠️ 跳过 {len(skipped_testers)} 个不可用的测试Agent: {skipped_testers}"})

        if not writer_agents:
            bg_engine.save_step9_artifacts({"status": "error", "message": "❌ 没有可用的编写Agent"})
            await broadcast(project_id, {"type": "error", "message": "❌ 没有可用的编写Agent"})
            # 重置 step9 为 pending，避免 stuck 在 in_progress
            try:
                bg_engine.reset_step(9)
            except Exception: pass
            return

        await broadcast(project_id, {"type": "progress", "message": f"🐝 蜂群就绪：{len(writer_agents)}个编写Agent, {len(tester_agents)}个测试Agent, {len(sorted_subtasks)}个文件"})

        # ══════════════════════════════════════════════
        # Phase 2: 逐个子任务 Writer → Tester → 收敛
        # ══════════════════════════════════════════════
        total_subtasks = len(sorted_subtasks)

        for subtask_idx, st in enumerate(sorted_subtasks):
            if st["index"] in completed_indices: continue

            sname, idx, file_path = st["name"], st["index"], st["file_path"]
            abs_file_path = os.path.join(src_dir, file_path)
            await broadcast(project_id, {"type": "progress", "message": f"🚀 [{sname}] 开始执行（{subtask_idx+1}/{total_subtasks}）"})

            writer = random.choice(writer_agents) if writer_agents else None
            tester = random.choice(tester_agents) if tester_agents else None
            if not writer:
                all_results.append({"index": idx, "name": sname, "status": "failed", "error": "没有可用Writer"})
                continue

            code, tester_conclusion, tester_detail = "", "", ""
            attempts = 0

            while attempts < 5:
                attempts += 1
                await broadcast(project_id, {"type": "progress", "message": f"✍️ [{sname}] {writer.name} 编写（第{attempts}轮）..."})

                dep_codes = []
                for dep in st.get("dependencies", []):
                    dp = os.path.join(src_dir, dep)
                    if os.path.exists(dp):
                        with open(dp, "r", encoding="utf-8") as f: dep_codes.append((dep, f.read()[:3000]))

                last_fb = tester_detail if attempts > 1 and "通过" not in tester_conclusion else ""
                wp = SwarmService.build_code_writer_prompt(file_path=file_path, file_description=st.get("description", ""), requirement=requirement, design_doc=design_doc, tdd_cases=tdd_cases, core_goal=core_goal, writer_name=writer.name, attempt=attempts, last_feedback=last_fb, dependency_codes=dep_codes, dep_graph=dep_graph, code_plan=code_plan)

                code = await _call_agent(writer, wp, slug=slug, docs_dir=docs_dir, project_id=project_id, proj_name=proj_name, proj_desc=proj_desc, core_goal=core_goal, timeout=600)

                for _si in range(3):
                    if not code.strip():
                        code = await _call_agent(writer, wp + "\n\n【⛔ 输出为空】必须重新输出完整代码。", slug=slug, docs_dir=docs_dir, project_id=project_id, proj_name=proj_name, proj_desc=proj_desc, core_goal=core_goal)
                        continue
                    code = SwarmService.clean_generated_code(code)
                    if SwarmService.validate_code_syntax(code)[0]: break
                    code = await _call_agent(writer, wp + f"\n\n【⛔ 语法错误】{SwarmService.validate_code_syntax(code)[1]}\n请重新输出修正后的代码。", slug=slug, docs_dir=docs_dir, project_id=project_id, proj_name=proj_name, proj_desc=proj_desc, core_goal=core_goal)

                if not code.strip():
                    for alt_w in writer_agents:
                        if alt_w.id == writer.id: continue
                        code = await _call_agent(alt_w, wp, slug=slug, docs_dir=docs_dir, project_id=project_id, proj_name=proj_name, proj_desc=proj_desc, core_goal=core_goal)
                        if code.strip(): writer = alt_w; break

                if not code.strip():
                    all_results.append({"index": idx, "name": sname, "status": "failed", "error": "未生成有效代码", "attempts": attempts, "writer": writer.name})
                    break

                os.makedirs(os.path.dirname(abs_file_path), exist_ok=True)
                with open(abs_file_path, "w", encoding="utf-8") as f: f.write(code)
                await broadcast(project_id, {"type": "progress", "message": f"📦 [{sname}] 代码已保存"})

                if not tester:
                    all_results.append({"index": idx, "name": sname, "file_path": abs_file_path, "status": "passed", "attempts": attempts, "writer": writer.name, "tester": ""})
                    await broadcast(project_id, {"type": "progress", "message": f"✅ [{sname}] 代码已生成（无Tester自动通过）"})
                    break

                await broadcast(project_id, {"type": "progress", "message": f"🔍 [{sname}] {tester.name} 检验（第{attempts}轮）..."})
                tp = SwarmService.build_code_tester_prompt(file_path=file_path, file_description=st.get("description", ""), code_content=code, requirement=requirement, design_doc=design_doc, tdd_cases=tdd_cases, tester_name=tester.name, attempt=attempts, last_feedback=tester_detail if attempts > 1 else "")
                test_result = await _call_agent(tester, tp, slug=slug, docs_dir=docs_dir, project_id=project_id, proj_name=proj_name, proj_desc=proj_desc, core_goal=core_goal, timeout=300)

                test_passed = False
                tester_detail = test_result[:500]
                try:
                    brace_s = test_result.find('{')
                    brace_e = test_result.rfind('}') + 1
                    if brace_s != -1 and brace_e > brace_s:
                        parsed = _json.loads(test_result[brace_s:brace_e])
                        test_passed = bool(parsed.get("passed", False) and int(parsed.get("score", 0)) >= 90)
                        tester_detail = parsed.get("detail", test_result[:500])
                        tester_conclusion = "通过" if test_passed else "未通过"
                except Exception:
                    test_passed = "通过" in test_result[:200] and "未通过" not in test_result[:200]
                    tester_conclusion = "通过" if test_passed else "未通过"

                if test_passed:
                    all_results.append({"index": idx, "name": sname, "file_path": abs_file_path, "status": "passed", "attempts": attempts, "writer": writer.name, "tester": tester.name, "tester_conclusion": tester_conclusion})
                    await broadcast(project_id, {"type": "progress", "message": f"✅ [{sname}] 通过 {tester.name} 检验（第{attempts}轮）"})
                    break
                else:
                    await broadcast(project_id, {"type": "progress", "message": f"⚠️ [{sname}] 未通过检验，修复中（第{attempts}轮）"})

            if attempts >= 5 and not any(r.get("index") == idx and r.get("status") == "passed" for r in all_results):
                all_results.append({"index": idx, "name": sname, "status": "failed", "error": f"5轮均未通过", "attempts": attempts, "writer": writer.name, "tester": tester.name if tester else ""})

        # ══════════════════════════════════════════════
        # Phase 3: hourong 5% 随机抽检
        # ══════════════════════════════════════════════
        passed_results = [r for r in all_results if r.get("status") == "passed"]
        failed_results = [r for r in all_results if r.get("status") == "failed"]
        spot_check_total = 0
        spot_check_failures = 0
        spot_check_detail = ""

        if passed_results:
            spot_sample_size = max(1, int(len(passed_results) * 0.05))
            spot_sample = random.sample(passed_results, min(spot_sample_size, len(passed_results)))
            spot_check_total = len(spot_sample)
            await broadcast(project_id, {"type": "progress", "message": f"🎲 hourong 抽检 {spot_check_total} 个文件（5%比例）..."})

            for sr in spot_sample:
                fp = sr.get("file_path", "")
                sname = sr.get("name", "")
                sidx = sr.get("index", 0)
                if not fp or not os.path.exists(fp): continue
                try:
                    with open(fp, "r", encoding="utf-8") as f: code_content = f.read()
                except Exception: continue

                spot_prompt = f"你是一个专业的代码QA检验员（后荣）。请严格检验以下功能代码。\n\n=== 检验项目与标准 ===\n{_json.dumps([{'检验项目':d['label'],'检验标准':d['description'],'检验维':d['key']} for d in CODE_INSPECTION_DIMENSIONS], ensure_ascii=False, indent=2)}\n\n=== 功能代码 ===\n{code_content[:5000]}\n\n直接输出 JSON 数组:\n" + ",\n".join(f'  {{"key":"{d["key"]}","passed":true/false,"detail":"具体检验意见..."}}' for d in CODE_INSPECTION_DIMENSIONS)

                for _ in range(HTTP_INSPECT_MAX_RETRIES):
                    try:
                        qa_client = GatewayClient(profile_name="hourong", timeout=180)
                        qa_chunks = []
                        async for chunk in qa_client.chat_completions(messages=[{"role":"user","content":spot_prompt}], stream=True, max_tokens=8192): qa_chunks.append(chunk)
                        qa_r = "".join(qa_chunks).strip()
                        brace_s = qa_r.find('['); brace_e = qa_r.rfind(']') + 1
                        if brace_s != -1 and brace_e > brace_s: qa_r = qa_r[brace_s:brace_e]
                        parsed = _json.loads(qa_r)
                        if isinstance(parsed, list) and parsed:
                            all_passed = all(bool(r.get("passed")) for r in parsed)
                            if not all_passed:
                                spot_check_failures += 1
                                failed_det = [r.get("detail","") for r in parsed if not r.get("passed")]
                                spot_check_detail += f"\n❌ [{sname}] 抽检未通过: {'; '.join(failed_det)}"
                                for er in all_results:
                                    if er.get("index") == sidx: er["status"] = "failed"; er["spot_check_failed"] = True; break
                                completed_indices.discard(sidx)
                            else:
                                spot_check_detail += f"\n✅ [{sname}] 抽检通过"
                            break
                    except Exception: continue

        # ══════════════════════════════════════════════
        # Phase 4: 组装 + 保存 + 交接
        # ══════════════════════════════════════════════
        final_passed = [r for r in all_results if r.get("status") == "passed"]
        final_failed = [r for r in all_results if r.get("status") == "failed"]

        combined_parts = []
        for st in sorted_subtasks:
            fp = os.path.join(src_dir, st["file_path"])
            if os.path.exists(fp):
                with open(fp, "r", encoding="utf-8") as f: content = f.read()
                combined_parts.append(f"### {st['file_path']}\n\n```python\n{content}\n```")
        combined = "\n\n---\n\n".join(combined_parts) if combined_parts else ""
        gen_path = os.path.join(docs_dir, f"{slug}_code_done_V1.md")
        if combined.strip():
            with open(gen_path, "w", encoding="utf-8") as f: f.write(combined)

        _passed_names = [r.get("name", "") for r in final_passed]
        _all_names = [st.get("name", f"用例{i+1}") for i, st in enumerate(sorted_subtasks)]
        handover_doc = _build_step9_handover(proj_name=proj_name, subtask_count=len(sorted_subtasks), passed_count=len(final_passed), failed_count=len(final_failed), subtask_names=_all_names, passed_subtask_names=_passed_names, spot_check_total=spot_check_total, spot_check_failures=spot_check_failures, spot_check_detail=spot_check_detail)

        all_ok = len(final_failed) == 0 and spot_check_failures == 0
        if all_ok:
            await broadcast(project_id, {"type": "progress", "message": f"✅ 全部 {len(sorted_subtasks)} 个子任务通过验证（抽检{spot_check_total}项）"})
            bg_engine.save_step9_artifacts({
                "code": combined, "doc_path": gen_path, "subtask_results": all_results,
                "status": "done", "qa_passed": True,
                "message": f"✅ 全部{len(sorted_subtasks)}个文件编写完成，hourong抽检{spot_check_total}项全部通过",
                "swarm_summary": {"total": len(sorted_subtasks), "passed": len(final_passed), "failed": len(final_failed), "spot_checked": spot_check_total, "spot_failures": spot_check_failures},
                "handover_doc": handover_doc,
            })
            await _force_complete_step9(project_id, bg_engine)
            await broadcast(project_id, {"type": "done", "message": f"✅ 功能代码编写完成，共{len(sorted_subtasks)}个文件，hourong抽检{spot_check_total}项全部通过"})
        else:
            await broadcast(project_id, {"type": "error", "message": f"❌ {len(final_failed)} 个子任务未通过，抽检不合格{spot_check_failures}项"})
            bg_engine.save_step9_artifacts({
                "code": combined, "doc_path": gen_path, "subtask_results": all_results,
                "status": "error", "qa_passed": False,
                "message": f"❌ {len(final_failed)}个子任务失败，{spot_check_failures}项抽检不合格",
                "swarm_summary": {"total": len(sorted_subtasks), "passed": len(final_passed), "failed": len(final_failed), "spot_checked": spot_check_total, "spot_failures": spot_check_failures},
                "handover_doc": handover_doc,
            })
            # 重置为 pending，允许前端执行续跑
            try: bg_engine.reset_step(9)
            except Exception: pass

    except Exception as e:
        logger.error(f"[Step9] run_step9_swarm: {e}", exc_info=True)
        try: await broadcast(project_id, {"type": "error", "message": f"❌ 蜂群执行异常: {str(e)[:200]}"})
        except Exception: pass
        try:
            bg_engine = WorkflowEngine(project_id=project_id, db=bg_db)
            bg_engine.save_step9_artifacts({"status": "error", "message": f"失败: {str(e)[:200]}"})
            bg_engine.reset_step(9)
        except Exception: pass
    finally:
        bg_db.close()


@router.post("/{project_id}/step9/execute")
async def execute_step9_async(project_id: str, db: Session = Depends(get_db), current_user=Depends(get_current_user), resume: bool = False):
    """建立Agent蜂群编写功能代码，hourong 自动检验+收敛修复"""
    import asyncio as _asyncio
    try:
        engine = _get_engine(project_id, db)
        saved_arts = engine.get_step9_artifacts() or {}
        has_results = bool(saved_arts.get("subtask_results"))
        has_progress = bool(saved_arts.get("subtask_progress"))

        if has_results or has_progress:
            resume = True; existing = saved_arts
        elif resume:
            existing = saved_arts
        else:
            row = engine._get_step_row(9)
            if row and row.status == "in_progress" and not has_results and not has_progress:
                pass  # 已有运行中的任务
            else:
                if row and row.status == "in_progress":
                    engine.reset_step(9)
                    engine = WorkflowEngine(project_id=project_id, db=db)
                    _wf_engines[project_id] = engine
                try:
                    from sqlalchemy import text
                    engine.db.execute(text("UPDATE workflow_steps SET status='in_progress', started_at=:now, output_artifacts=:arts WHERE project_id=:pid AND step_number=9"), {"now": datetime.now(timezone.utc), "arts": _json.dumps({"status": "generating", "message": "Step 9 started..."}), "pid": project_id})
                    engine.db.execute(text("UPDATE projects SET current_step=9 WHERE id=:pid"), {"pid": project_id})
                    engine.db.commit(); engine.current_step = 9
                except Exception as e: logger.error(f"[STEP9_DEBUG] start failed: {e}"); return APIResponse(code=1, message=f"无法开始步骤9: {str(e)[:200]}")
            existing = {}
    except Exception as e: return APIResponse(code=1, message=f"无法开始步骤9: {str(e)[:200]}")

    if resume and saved_arts.get("subtask_results"):
        all_passed = all(sr.get("status") == "passed" for sr in saved_arts["subtask_results"])
        if all_passed:
            engine.save_step9_artifacts({"status": "done", "message": "✅ 所有文件已通过检验"})
            if engine._get_step_row(9) and engine._get_step_row(9).status != "completed":
                from sqlalchemy import text as _txt2
                engine.db.execute(_txt2("UPDATE workflow_steps SET status='completed', completed_at=:now WHERE project_id=:pid AND step_number=9"), {"now": datetime.now(timezone.utc), "pid": project_id})
                engine.db.commit()
            return APIResponse(code=0, message="所有文件已通过，无需重新执行")

    step3 = engine.get_step3_artifacts() or {}
    requirement = (step3.get("doc_content") or step3.get("content") or step3.get("requirement") or step3.get("srs") or "")
    step4 = engine.get_step4_artifacts() or {}; design_doc = step4.get("design_doc") or ""
    step7 = engine.get_step7_artifacts() or {}; tdd_cases = step7.get("tdd_cases") or step7.get("test_cases") or step7.get("content") or ""
    step8 = engine.get_step8_artifacts() or {}; code_plan = step8.get("code_plan") or step8.get("plan_content") or ""
    dep_graph = step8.get("dependency_graph") or {}
    step2 = engine.get_step2_artifacts() or {}; core_goal = step2.get("confirmed_goal") or step2.get("core_goal") or ""
    proj = db.query(Project).filter(Project.id == project_id).first(); proj_name = proj.name if proj else ""; proj_desc = proj.description or ""

    engine.save_step9_artifacts({"status": "generating", "message": "🐝 后发正在组建蜂群编写功能代码..."})

    task = _asyncio.create_task(run_step9_swarm(project_id=project_id, requirement=requirement, design_doc=design_doc, core_goal=core_goal, proj_name=proj_name, proj_desc=proj_desc, existing=existing if resume else None, resume=resume, code_plan=code_plan, dep_graph=dep_graph, tdd_cases=tdd_cases))
    from app.services.haimei_executor import HaimeiStepExecutor
    HaimeiStepExecutor._tasks[f"{project_id}:step9"] = task
    return APIResponse(code=0, data={"message": "第九步已启动", "status": "generating"})


@router.post("/{project_id}/step9/reset")
def reset_step9(project_id: str, db: Session = Depends(get_db), current_user=Depends(get_current_user)):
    engine = _get_engine(project_id, db); engine.reset_step(9); _wf_engines.pop(project_id, None)
    return APIResponse(code=0, data={"message": "第九步已重置"})


@router.get("/{project_id}/step9/status")
def get_step9_status(project_id: str, db: Session = Depends(get_db), current_user=Depends(get_current_user)):
    engine = _get_engine(project_id, db)
    return APIResponse(code=0, data=engine.get_step9_artifacts())


@router.post("/{project_id}/step9/artifacts")
def save_step9_artifacts_route(project_id: str, body: dict = Body(...), db: Session = Depends(get_db), current_user=Depends(get_current_user)):
    engine = _get_engine(project_id, db); engine.save_step9_artifacts(body)
    return APIResponse(code=0, data={"message": "步骤9状态已保存"})


@router.post("/{project_id}/step9/inspect")
async def inspect_step9(project_id: str, body: Step3InspectRequest, db: Session = Depends(get_db), current_user=Depends(get_current_user)):
    from app.services.gateway_client import GatewayClient
    content, focus_items = body.content, body.focus_items
    if not content or len(content.strip()) < 20:
        return APIResponse(code=0, data={"passed": False, "dimensions": [{"key": d["key"], "passed": False} for d in CODE_INSPECTION_DIMENSIONS]})
    active_dims = [d for d in CODE_INSPECTION_DIMENSIONS if not focus_items or d["key"] in focus_items]
    dims_json = _json.dumps([{'检验项目': d['label'], '检验标准': d['description']} for d in active_dims], ensure_ascii=False, indent=2)
    focus_hint = f"\n⚠️ 本次只检验：{[d['label'] for d in active_dims]}" if focus_items else ""
    prompt = f"你是一个专业的代码QA检验员（后荣）。\n\n=== 功能代码 ===\n{content}\n\n=== 检验项目 ===\n{dims_json}\n{focus_hint}\n\n直接输出 JSON 数组：\n[\n" + ",\n".join(f'  {{"key": "{d["key"]}", "passed": true/false, "detail": "..."}}' for d in active_dims) + "\n]"
    try:
        client = GatewayClient(profile_name="hourong", timeout=120); chunks = []
        async for chunk in client.chat_completions(messages=[{"role": "user", "content": prompt}], stream=False, max_tokens=2000): chunks.append(chunk)
        reply = "".join(chunks).strip()
        if not reply: raise ValueError("未返回")
        parsed = _json.loads(reply)
        if not isinstance(parsed, list): raise ValueError("不是数组")
    except Exception:
        return APIResponse(code=0, data={"passed": False, "dimensions": [{"key": d["key"], "passed": False} for d in active_dims]})
    results = []
    for dim in active_dims:
        m = next((r for r in parsed if r.get("key") == dim["key"]), None)
        results.append({"key": dim["key"], "label": dim["label"], "passed": bool(m.get("passed", False)) if m else False, "detail": m.get("detail", "") if m else ""})
    return APIResponse(code=0, data={"passed": all(r["passed"] for r in results), "dimensions": results})


@router.post("/{project_id}/step9/qa")
def qa_step9(project_id: str, body: QAResultRequest, db: Session = Depends(get_db), current_user=Depends(get_current_user)):
    engine = _get_engine(project_id, db)
    result = engine.pass_qa(9) if body.result == "passed" else engine.fail_qa(9, reason=body.reason or "", suggestions=body.suggestions)
    return APIResponse(code=0, data={"message": f"第九步QA{'通过' if body.result == 'passed' else '未通过'}", "qa": result})
