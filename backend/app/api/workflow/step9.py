import glob
import json as _json
import random
import re as _re
import time as _time
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
        rchunks = []
        async for chunk in client.chat_isolated(messages=messages, project_id=project_id, project_name=project.name, project_description=project.description or "", core_goal=core_goal, agent_name="后发（HouFa）程序员", stream=False, project_slug=project.slug if project.slug else project_id):
            rchunks.append(chunk)
        reply = "".join(rchunks)
        return APIResponse(code=0, message="success", data={"reply": reply}) if reply and len(reply.strip()) >= 5 else APIResponse(code=1, message="后发未生成有效回复", data=None)
    except HTTPException:
        raise
    except Exception as e:
        logger.error(f"Step9 chat: {e}")
        return APIResponse(code=1, message="与后发对话失败", data=None)


async def _inspect_code(project_id: str, doc_path: str, project_name: str = "", project_description: str = "", core_goal: str = "", agent_label: str = "", max_retries: int = 3, failed_keys: list = None) -> dict:
    import json as _json, asyncio as _asyncio
    from app.api.ws.step4_progress import broadcast
    from app.api.ws.step3_qa import _inspect_via_subagent
    active_dims = [d for d in CODE_INSPECTION_DIMENSIONS if not failed_keys or d["key"] in failed_keys]
    dims_json = str([{'检验项目': d['label'], '检验标准': d['description'], '检验维': d['key']} for d in active_dims])
    for attempt in range(1, max_retries + 1):
        if attempt > 1:
            await _asyncio.sleep(2)
            await broadcast(project_id, {"type": "step9", "message": f"🔄 hourong 第{attempt}次检验功能代码..."})
        focus_hint = f"\n⚠️ 本次只需重新检验以下 {len(active_dims)} 项（上一轮不合格项）：{[d['label'] for d in active_dims]}\n请只针对这些项目做出通过/不通过判定，禁止扩大检验范围。" if failed_keys else ""
        insp_prompt = f"你是一个专业的代码QA检验员（后荣）。请严格检验以下功能代码。\n\n=== 检验项目与标准 ===\n{dims_json}\n{focus_hint}\n\n=== 文档路径 ===\n{doc_path}\n\n请读取该文档文件，严格逐项检验。\n⚠️ 收敛性要求：检验报告必须聚焦于不合格项，明确指出不合格项的问题和修改方向。后续Agent将只修改不合格项，禁止扩大范围。已合格项目不得提出修改要求。\n评分规则：每个检验维起始100分，每发现一个缺陷扣减相应分数（轻微缺陷扣5-10分，一般缺陷扣15-20分，严重缺陷扣25-30分）。维度得分≥90则该维度passed为true。所有维度平均分>90分为整体合格。\n只输出 JSON 数组:\n" + ",\n".join(f'  {{"key": "{d["key"]}", "score": 100, "deduction": "", "passed": true/false, "detail": "具体检验意见..."}}' for d in active_dims)
        qa_r = await _inspect_via_subagent(prompt=insp_prompt, max_retries=max_retries)
        if not qa_r:
            if attempt < max_retries:
                await broadcast(project_id, {"type": "step9", "message": f"⚠️ 未返回，重试（第{attempt}次）"})
                continue
            return {"detail": f"后荣{max_retries}次均未返回"}
        brace_s, brace_e = qa_r.find('['), qa_r.rfind(']') + 1
        if brace_s != -1 and brace_e > brace_s:
            qa_r = qa_r[brace_s:brace_e]
        try:
            parsed = _json.loads(qa_r)
        except Exception:
            if attempt < max_retries:
                await broadcast(project_id, {"type": "step9", "message": f"⚠️ 格式异常，重试（第{attempt}次）"})
                continue
            return {"detail": "后荣未返回检验结果"}
        if isinstance(parsed, list) and parsed:
            scores = [int(r.get("score", 100)) for r in parsed]
            avg_score = sum(scores) / len(scores)
            return {"passed": avg_score > 90, "score": avg_score, "total_score": sum(scores), "max_score": len(scores) * 100, "detail": "", "failed_details": [r.get("detail", "") for r in parsed if int(r.get("score", 100)) < 90], "results": parsed}
        if attempt < max_retries:
            await broadcast(project_id, {"type": "step9", "message": f"⚠️ 格式异常，重试（第{attempt}次）"})
            continue
        return {"detail": "后荣未返回检验结果"}
    return {"detail": "后荣检验失败"}


def _parse_code_plan_to_subtasks(code_plan: str, dep_graph: dict = None) -> list[dict]:
    """Parse the code plan text into a list of subtasks (one per source file).

    Each subtask: {"name", "file_path", "description", "dependencies": [], "index"}
    If parsing fails, returns a single subtask for the entire codebase.
    """
    subtasks = []
    seen_paths = set()

    # Strategy 1: extract file paths from markdown headers (### path/to/file.py)
    for m in _re.finditer(r'^###\s+(\S+\.py\S*)\s*$', code_plan, _re.MULTILINE):
        path = m.group(1).strip()
        if path and path not in seen_paths:
            seen_paths.add(path)
            # Find the content after this header until the next header
            start = m.end()
            next_m = _re.search(r'^###\s+\S', code_plan[start:], _re.MULTILINE)
            desc = code_plan[start:start + (next_m.start() if next_m else 200)].strip()[:200]
            subtasks.append({
                "name": os.path.basename(path),
                "file_path": path,
                "description": desc,
                "dependencies": [],
                "index": len(subtasks) + 1,
            })

    # Strategy 2: extract from numbered lists or bullet points with file paths
    if not subtasks:
        for m in _re.finditer(r'(?:^|\n)\s*[-*\d]+\.?\s*(`)?(\S+\.py\S*)(?(1)`)\s*[-–—:]?\s*(.*)', code_plan):
            path = m.group(2).strip()
            desc = m.group(3).strip()[:200] if m.group(3) else ""
            if path and path not in seen_paths:
                seen_paths.add(path)
                subtasks.append({
                    "name": os.path.basename(path),
                    "file_path": path,
                    "description": desc,
                    "dependencies": [],
                    "index": len(subtasks) + 1,
                })

    # Strategy 3: extract from dep_graph directly if it's structured
    if not subtasks and isinstance(dep_graph, dict):
        for path in dep_graph:
            if path and path not in seen_paths:
                seen_paths.add(path)
                deps = dep_graph.get(path, [])
                if isinstance(deps, list):
                    deps = [d for d in deps if isinstance(d, str)]
                else:
                    deps = []
                subtasks.append({
                    "name": os.path.basename(path),
                    "file_path": path,
                    "description": "",
                    "dependencies": deps,
                    "index": len(subtasks) + 1,
                })

    # Fallback: single monolithic subtask
    if not subtasks:
        subtasks.append({
            "name": "codebase",
            "file_path": "src/main.py",
            "description": "Entire codebase",
            "dependencies": [],
            "index": 1,
        })

    # Apply dep_graph dependencies
    if isinstance(dep_graph, dict):
        for st in subtasks:
            deps = dep_graph.get(st["file_path"], [])
            if isinstance(deps, list):
                st["dependencies"] = [d for d in deps if isinstance(d, str)]

    return subtasks


def _topological_sort(subtasks: list[dict]) -> list[dict]:
    """Topological sort by dependency graph. Detects cycles."""
    by_path = {st["file_path"]: st for st in subtasks}
    visited = set()
    temp = set()
    order = []

    def _visit(path):
        if path in temp:
            logger.warning(f"[Step9] 依赖循环检测: {path}")
            return
        if path in visited:
            return
        temp.add(path)
        for dep in by_path.get(path, {}).get("dependencies", []):
            if dep in by_path:
                _visit(dep)
        temp.discard(path)
        visited.add(path)
        order.append(by_path[path])

    for st in subtasks:
        if st["file_path"] not in visited:
            try:
                _visit(st["file_path"])
            except Exception as e:
                logger.warning(f"[Step9] 拓扑排序异常: {e}")
                order.append(st)

    return order


async def _save_subtask_result(result: dict, bg_engine, rlock: asyncio.Lock):
    """Atomically update subtask_results in step9 artifacts."""
    try:
        async with rlock:
            cur = bg_engine.get_step9_artifacts() or {}
            saved = cur.get("subtask_results", [])
            found = False
            for i, sr in enumerate(saved):
                if sr.get("index") == result.get("index"):
                    saved[i] = result
                    found = True
                    break
            if not found:
                saved.append(result)
            cur["subtask_results"] = saved
            bg_engine.save_step9_artifacts(cur)
    except Exception as e:
        logger.warning(f"[Step9] save subtask result failed: {e}")


async def _save_subtask_progress(idx: int, sname: str, progress: dict, bg_engine, rlock: asyncio.Lock):
    """Atomically update subtask_progress in step9 artifacts."""
    try:
        async with rlock:
            cur = bg_engine.get_step9_artifacts() or {}
            sp = cur.get("subtask_progress", {})
            sp[str(idx)] = {**sp.get(str(idx), {}), **progress, "name": sname, "index": idx, "updated_at": _time.time()}
            cur["subtask_progress"] = sp
            bg_engine.save_step9_artifacts(cur)
    except Exception as e:
        logger.warning(f"[Step9] save subtask progress failed: {e}")


async def run_step9_swarm(
    project_id: str,
    requirement: str,
    design_doc: str,
    core_goal: str,
    proj_name: str = "",
    proj_desc: str = "",
    existing: dict = None,
    resume: bool = False,
    code_plan: str = "",
    dep_graph: dict = None,
    tdd_cases: str = "",
):
    """蜂群并行功能代码生成（参考 step7 的多Agent模式）

    Phase 0: 读取 artifacts，解析子任务
    Phase 1: 获取 Writer Agent 池，自动配置 + 烟雾测试
    Phase 2: 按依赖顺序逐个生成文件
    Phase 3: 组装完整 {slug}_code_V{n}.md
    Phase 4: hourong 检验 + 收敛循环（最多10轮）
    Phase 5: 保存 artifacts + complete_step
    """
    from app.database import SessionLocal
    from app.models.project import Project
    from app.api.ws.step4_progress import broadcast

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

        # ── 续跑：已通过则跳过 ──
        if resume and prev.get("qa_passed") and prev.get("doc_path") and os.path.exists(prev.get("doc_path", "")):
            await broadcast(project_id, {"type": "step9", "message": "♻️ 续跑：功能代码已通过，跳过"})
            bg_engine.save_step9_artifacts({**prev, "status": "done", "message": "♻️ 续跑：功能代码已通过"})
            bg_engine.complete_step(9)
            await broadcast(project_id, {"type": "done", "message": "✅ 功能代码已生成（续跑）"})
            return

        # ── 解析子任务 ──
        subtasks = _parse_code_plan_to_subtasks(code_plan, dep_graph)
        sorted_subtasks = _topological_sort(subtasks)
        all_results = []

        await broadcast(project_id, {"type": "step9", "subtask_names": [st["name"] for st in sorted_subtasks], "subtask_indices": [st["index"] for st in sorted_subtasks], "message": f"📋 代码计划已解析：{len(sorted_subtasks)} 个文件"})

        # ── 续跑：恢复已通过子任务 ──
        passed_indices_from_prev = set()
        if resume:
            saved = prev.get("subtask_results", [])
            for sr in saved:
                if sr.get("status") == "passed":
                    idx = sr.get("index", 0)
                    fp = sr.get("file_path", "")
                    if os.path.exists(fp):
                        passed_indices_from_prev.add(idx)
                        all_results.append(sr)
            if passed_indices_from_prev:
                await broadcast(project_id, {"type": "step9", "message": f"♻️ 续跑：{len(passed_indices_from_prev)} 个文件已通过"})

        # ── 全部已通过 ──
        if passed_indices_from_prev and len(passed_indices_from_prev) == len(sorted_subtasks):
            await broadcast(project_id, {"type": "step9", "message": f"✅ 全部 {len(sorted_subtasks)} 个文件已生成（从历史恢复）"})
            combined = _assemble_combined_code(sorted_subtasks, src_dir)
            bg_engine.save_step9_artifacts({
                "code": combined, "subtask_results": all_results,
                "status": "done", "qa_passed": True,
                "message": "✅ 全部文件已生成",
            })
            bg_engine.complete_step(9)
            await broadcast(project_id, {"type": "done", "message": f"✅ 全部 {len(sorted_subtasks)} 个文件已生成"})
            return

        # ── Phase 1: 获取 Writer Agent 池 ──
        writer_agents = SwarmService.get_preferred_writer_agents(bg_db)
        configured_writers = []
        skipped_writers = []
        for a in writer_agents:
            from app.services.agent_utils import auto_configure_agent, smoke_test_agent
            if await auto_configure_agent(a, db_session=bg_db) and await smoke_test_agent(a):
                configured_writers.append(a)
            else:
                skipped_writers.append(a.name)
        writer_agents = configured_writers
        if skipped_writers:
            logger.warning(f"[Step9] 跳过 {len(skipped_writers)} 个不可用的编写Agent: {skipped_writers}")
            await broadcast(project_id, {"type": "step9", "message": f"⚠️ 跳过 {len(skipped_writers)} 个不可用的编写Agent: {skipped_writers}"})

        if not writer_agents:
            bg_engine.save_step9_artifacts({"status": "error", "message": "❌ 没有可用的编写Agent"})
            await broadcast(project_id, {"type": "error", "message": "❌ 没有可用的编写Agent"})
            return

        # ── 广播 Agent 就绪 ──
        for wa in writer_agents:
            await broadcast(project_id, {"type": "agent_online", "name": wa.name, "role": "writer", "agent_type": wa.agent_type})
        await broadcast(project_id, {"type": "step9", "message": f"🐝 蜂群就绪：{len(writer_agents)}个编写Agent, {len(sorted_subtasks)}个文件"})

        # ── 创建蜂群 ──
        swarm_svc = SwarmService()
        swarm_svc.create_swarm(
            project_id=project_id,
            name=f"Code-Swarm-{slug[:8]}",
            purpose="code_writing",
            step_number=9,
            manager_role="houfa",
        )

        # ── Phase 2: 依赖顺序生成文件 ──
        rlock = asyncio.Lock()
        convergence_log = []
        max_ver = 0
        for f in glob.glob(os.path.join(docs_dir, f"{slug}_code_V*.md")):
            m = _re.search(r'V(\d+)', os.path.basename(f))
            if m:
                max_ver = max(max_ver, int(m.group(1)))

        # 收敛循环
        start_round = 1
        if resume and prev:
            saved_round = prev.get("current_fix_round", 0)
            saved_convergence = prev.get("convergence", [])
            if saved_round > 0:
                start_round = saved_round + 1
                convergence_log = list(saved_convergence)

        for fix_round in range(start_round, 11):
            nv = max_ver + fix_round
            gen_path = os.path.join(docs_dir, f"{slug}_code_V{nv}.md")
            feedback = ""
            if fix_round > 1 and convergence_log:
                failed = convergence_log[-1].get("failed_details", [])
                feedback = "需要修正的问题（只修复这些问题）：\n" + "\n".join(f"- {d}" for d in failed if d)

            await broadcast(project_id, {"type": "step9", "message": f"💻 蜂群正在{'修复' if fix_round > 1 else '生成'}代码（第{fix_round}轮）..."})

            # ── 按依赖顺序处理子任务 ──
            subtasks_to_process = [st for st in sorted_subtasks if st["index"] not in passed_indices_from_prev]
            generated_code_map = {}  # path → code

            async def _process_one_subtask(st: dict) -> dict:
                """Process a single file subtask: write → self-check → save."""
                writer = random.choice(writer_agents) if writer_agents else None
                if not writer:
                    return {"index": st["index"], "name": st["name"], "status": "failed", "error": "No writer available"}

                sname = st["name"]
                idx = st["index"]
                file_path = st["file_path"]
                abs_file_path = os.path.join(src_dir, file_path)

                await broadcast(project_id, {"type": "step9", "message": f"✍️ [{sname}] {writer.name} 编写..."})

                # Build prompt with dependency code context
                dep_codes = []
                for dep in st.get("dependencies", []):
                    if dep in generated_code_map:
                        dep_codes.append((dep, generated_code_map[dep]))

                wp = SwarmService.build_code_writer_prompt(
                    file_path=file_path,
                    file_description=st.get("description", ""),
                    requirement=requirement,
                    design_doc=design_doc,
                    tdd_cases=tdd_cases,
                    core_goal=core_goal,
                    writer_name=writer.name,
                    attempt=fix_round,
                    last_feedback=feedback,
                    dependency_codes=dep_codes,
                    dep_graph=dep_graph,
                    code_plan=code_plan,
                )

                from app.services.agent_utils import call_agent as _call_agent
                code = await _call_agent(
                    writer, wp,
                    slug=slug, docs_dir=docs_dir,
                    project_id=project_id, proj_name=proj_name,
                    proj_desc=proj_desc, core_goal=core_goal,
                    timeout=600,
                )

                # Self-check: clean and validate syntax
                _SELF_CHECK_MAX = 3
                for _si in range(_SELF_CHECK_MAX):
                    if not code.strip():
                        code = await _call_agent(
                            writer, wp + "\n\n【⛔ 输出为空】必须重新输出完整的 Python 代码。",
                            slug=slug, docs_dir=docs_dir,
                            project_id=project_id, proj_name=proj_name,
                            proj_desc=proj_desc, core_goal=core_goal,
                        )
                        continue
                    code = SwarmService.clean_generated_code(code)
                    syntax_ok, err = SwarmService.validate_code_syntax(code)
                    if syntax_ok:
                        break
                    code = await _call_agent(
                        writer, wp + f"\n\n【⛔ 语法错误】{err}\n请重新输出修正后的代码。",
                        slug=slug, docs_dir=docs_dir,
                        project_id=project_id, proj_name=proj_name,
                        proj_desc=proj_desc, core_goal=core_goal,
                    )

                if not code.strip():
                    # Try fallback writer
                    for alt_w in writer_agents:
                        if alt_w.id == writer.id:
                            continue
                        code = await _call_agent(
                            alt_w, wp,
                            slug=slug, docs_dir=docs_dir,
                            project_id=project_id, proj_name=proj_name,
                            proj_desc=proj_desc, core_goal=core_goal,
                        )
                        if code.strip():
                            writer = alt_w
                            break

                if code.strip():
                    os.makedirs(os.path.dirname(abs_file_path), exist_ok=True)
                    with open(abs_file_path, "w", encoding="utf-8") as f:
                        f.write(code)
                    generated_code_map[file_path] = code
                    await broadcast(project_id, {"type": "step9", "message": f"📦 [{sname}] 已保存至 {file_path}"})
                    return {"index": idx, "name": sname, "file_path": abs_file_path, "status": "done", "writer": writer.name}

                return {"index": idx, "name": sname, "status": "failed", "error": "No code generated"}

            processed = []
            for st in subtasks_to_process:
                result = await _process_one_subtask(st)
                processed.append(result)
                all_results.append(result)

            # ── Phase 3: 组装完整代码文件 ──
            combined_parts = []
            for st in sorted_subtasks:
                fp = os.path.join(src_dir, st["file_path"])
                if os.path.exists(fp):
                    with open(fp, "r", encoding="utf-8") as f:
                        content = f.read()
                    combined_parts.append(f"### {st['file_path']}\n\n```python\n{content}\n```")
            combined = "\n\n".join(combined_parts) if combined_parts else "".join(generated_code_map.values())

            if combined.strip():
                with open(gen_path, "w", encoding="utf-8") as f:
                    f.write(combined)

            bg_engine.save_step9_artifacts({
                "code": combined, "doc_path": gen_path,
                "subtask_results": all_results,
                "status": "generating",
                "current_fix_round": fix_round,
                "convergence": convergence_log,
            })

            # ── Phase 4: hourong 检验 ──
            await broadcast(project_id, {"type": "step9", "message": f"🔍 hourong 正在检验功能代码..."})
            failed_keys = []
            if fix_round > 1 and convergence_log:
                last_results = convergence_log[-1].get("results", [])
                if last_results:
                    failed_keys = [r.get("key", "") for r in last_results if int(r.get("score", 100)) < 90]

            qa_result = await _inspect_code(
                project_id, gen_path,
                project_name=proj_name, project_description=proj_desc,
                core_goal=core_goal,
                failed_keys=failed_keys if failed_keys else None,
            )
            convergence_log.append({
                "round": fix_round,
                "detail": qa_result.get("detail", ""),
                "passed": qa_result.get("passed", False),
                "failed_details": qa_result.get("failed_details", []),
                "results": qa_result.get("results", []),
            })

            if qa_result.get("passed"):
                await broadcast(project_id, {"type": "step9", "message": f"✅ 功能代码已通过 hourong 检验（共{fix_round}轮）"})
                bg_engine.save_step9_artifacts({
                    "code": combined, "doc_path": gen_path,
                    "subtask_results": all_results,
                    "convergence": convergence_log,
                    "status": "done", "qa_passed": True,
                    "message": "✅ 功能代码编写完成",
                })
                bg_engine.complete_step(9)
                await broadcast(project_id, {"type": "done", "message": "✅ 功能代码已生成"})
                return

            await broadcast(project_id, {"type": "step9", "message": f"⚠️ 未通过，修复中（第{fix_round}轮）"})

        # ── 10轮均未通过 ──
        await broadcast(project_id, {"type": "error", "message": "❌ 经10轮仍未通过检验"})
        # 不再 reset_step(9)，保留已通过子任务的状态，前端可查看进度后决定是否续跑
        bg_engine.save_step9_artifacts({
            "code": "", "doc_path": gen_path if 'gen_path' in dir() else "",
            "convergence": convergence_log,
            "subtask_results": all_results,
            "status": "error",
            "message": "❌ 经10轮仍未通过检验，保留现有进度以便续跑",
        })

    except Exception as e:
        logger.error(f"[Step9] run_step9_swarm: {e}")
        try:
            await broadcast(project_id, {"type": "error", "message": f"❌ 蜂群执行异常: {str(e)[:200]}"})
        except Exception:
            pass
        try:
            bg_engine = WorkflowEngine(project_id=project_id, db=bg_db)
            bg_engine.save_step9_artifacts({"status": "error", "message": f"失败: {str(e)[:200]}"})
            bg_engine.reset_step(9)
        except Exception:
            pass
    finally:
        bg_db.close()


async def execute_step9_async(project_id: str, db: Session = Depends(get_db), current_user=Depends(get_current_user), resume: bool = False):
    """建立Agent蜂群编写功能代码，hourong 自动检验+收敛修复"""
    import asyncio as _asyncio
    try:
        engine = _get_engine(project_id, db)
        saved_arts = engine.get_step9_artifacts() or {}
        has_results = bool(saved_arts.get("subtask_results"))
        has_progress = bool(saved_arts.get("subtask_progress"))
        if has_results or has_progress:
            resume = True
            existing = saved_arts
        elif resume:
            existing = saved_arts
        else:
            row = engine._get_step_row(9)
            if row and row.status == "in_progress":
                engine.reset_step(9)
                engine = WorkflowEngine(project_id=project_id, db=db)
                _wf_engines[project_id] = engine
            engine.advance_step(9)
            existing = {}
    except Exception as e:
        return APIResponse(code=1, message=f"无法开始步骤9: {str(e)[:200]}")

    # ── 所有子任务已通过则跳过 ──
    if resume and saved_arts.get("subtask_results"):
        all_passed = all(sr.get("status") == "passed" for sr in saved_arts["subtask_results"])
        if all_passed:
            engine.save_step9_artifacts({"status": "done", "message": "✅ 所有文件已通过检验"})
            if engine._get_step_row(9) and engine._get_step_row(9).status != "completed":
                engine.complete_step(9)
            return APIResponse(code=0, message="所有文件已通过，无需重新执行")

    step3 = engine.get_step3_artifacts() or {}
    requirement = (step3.get("doc_content") or step3.get("content") or step3.get("requirement") or step3.get("srs") or "")
    step4 = engine.get_step4_artifacts() or {}
    design_doc = step4.get("design_doc") or ""
    step7 = engine.get_step7_artifacts() or {}
    tdd_cases = step7.get("tdd_cases") or step7.get("test_cases") or step7.get("content") or ""
    step8 = engine.get_step8_artifacts() or {}
    code_plan = step8.get("code_plan") or step8.get("plan_content") or ""
    dep_graph = step8.get("dependency_graph") or {}
    step2 = engine.get_step2_artifacts() or {}
    core_goal = step2.get("confirmed_goal") or step2.get("core_goal") or ""
    proj = db.query(Project).filter(Project.id == project_id).first()
    proj_name = proj.name if proj else ""
    proj_desc = proj.description or ""
    engine.save_step9_artifacts({"status": "generating", "message": "🐝 后发正在组建蜂群编写功能代码..."})

    async def _generate():
        await run_step9_swarm(
            project_id=project_id,
            requirement=requirement,
            design_doc=design_doc,
            core_goal=core_goal,
            proj_name=proj_name,
            proj_desc=proj_desc,
            existing=existing if resume else None,
            resume=resume,
            code_plan=code_plan,
            dep_graph=dep_graph,
            tdd_cases=tdd_cases,
        )
    _asyncio.create_task(_generate())
    return APIResponse(code=0, data={"message": "第九步已启动", "status": "generating"})


@router.post("/{project_id}/step9/reset")
def reset_step9(project_id: str, db: Session = Depends(get_db), current_user=Depends(get_current_user)):
    engine = _get_engine(project_id, db)
    engine.reset_step(9)
    _wf_engines.pop(project_id, None)
    return APIResponse(code=0, data={"message": "第九步已重置"})


@router.get("/{project_id}/step9/status")
def get_step9_status(project_id: str, db: Session = Depends(get_db), current_user=Depends(get_current_user)):
    engine = _get_engine(project_id, db)
    return APIResponse(code=0, data=engine.get_step9_artifacts())


@router.post("/{project_id}/step9/artifacts")
def save_step9_artifacts_route(project_id: str, body: dict = Body(...), db: Session = Depends(get_db), current_user=Depends(get_current_user)):
    engine = _get_engine(project_id, db)
    engine.save_step9_artifacts(body)
    return APIResponse(code=0, data={"message": "步骤9状态已保存"})


@router.post("/{project_id}/step9/inspect")
async def inspect_step9(project_id: str, body: Step3InspectRequest, db: Session = Depends(get_db), current_user=Depends(get_current_user)):
    from app.api.ws.step3_qa import _inspect_via_subagent
    import json as _json
    content, focus_items = body.content, body.focus_items
    if not content or len(content.strip()) < 20:
        return APIResponse(code=0, data={"passed": False, "dimensions": [{"key": d["key"], "passed": False} for d in CODE_INSPECTION_DIMENSIONS]})
    active_dims = [d for d in CODE_INSPECTION_DIMENSIONS if not focus_items or d["key"] in focus_items]
    dims_json = _json.dumps([{'检验项目': d['label'], '检验标准': d['description']} for d in active_dims], ensure_ascii=False, indent=2)
    focus_hint = f"\n⚠️ 本次只检验：{[d['label'] for d in active_dims]}" if focus_items else ""
    convergence_hint = "\n⚠️ 收敛性要求：检验报告必须聚焦于不合格项，明确指出不合格项的问题和修改方向。后续Agent将只修改不合格项，禁止扩大范围。已合格项目不得提出修改要求。"
    scoring_hint = "\n评分规则：每个维度起始100分，每发现一个缺陷扣减相应分数（轻微缺陷扣5-10分，一般缺陷扣15-20分，严重缺陷扣25-30分）。维度得分≥90则该维度passed为true。所有维度平均分>90分为整体合格。"
    prompt = f"你是一个专业的代码QA检验员（后荣）。\n\n=== 功能代码 ===\n{content}\n\n=== 检验项目 ===\n{dims_json}\n{focus_hint}\n{convergence_hint}\n{scoring_hint}\n\n直接输出 JSON 数组：\n[\n" + ",\n".join(f'  {{"key": "{d["key"]}", "score": 100, "deduction": "", "passed": true/false, "detail": "..."}}' for d in active_dims) + "\n]"
    try:
        reply = await _inspect_via_subagent(prompt=prompt, max_retries=3)
        if not reply:
            raise ValueError("未返回")
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
    _engine.save_step9_artifacts({
        "inspect_result": {"passed": all_passed, "avg_score": avg_score, "dimensions": results, "inspected_at": __import__('datetime').datetime.now(__import__('datetime').timezone.utc).isoformat()},
        "qa_passed": all_passed, "qa_checked": True,
    })
    return APIResponse(code=0, data={"passed": avg_score > 90, "score": avg_score, "dimensions": results})


@router.post("/{project_id}/step9/qa")
def qa_step9(project_id: str, body: QAResultRequest, db: Session = Depends(get_db), current_user=Depends(get_current_user)):
    from datetime import datetime, timezone
    engine = _get_engine(project_id, db)
    now_iso = datetime.now(timezone.utc).isoformat()
    if body.result == "passed":
        result = engine.pass_qa(9)
        engine.save_step9_artifacts({"qa_passed": True, "qa_status": "passed", "qa_checked_at": now_iso})
    else:
        result = engine.fail_qa(9, reason=body.reason or "", suggestions=body.suggestions)
        engine.save_step9_artifacts({"qa_passed": False, "qa_status": "failed", "qa_checked_at": now_iso, "qa_fail_reason": body.reason, "qa_suggestions": body.suggestions})
    return APIResponse(code=0, data={"message": f"第九步QA{'通过' if body.result == 'passed' else '未通过'}", "qa": result})