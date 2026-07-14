import json as _json
import os
import glob
import re as _re
import logging
import httpx
from typing import Dict, List
from fastapi import APIRouter, WebSocket, WebSocketDisconnect, Query

from app.utils.hermes_fs import read_profile_config as _read_profile_config
from app.api.ws.auth import verify_token
from app.api.ws.step3_qa_1 import delegate_task
from app.services.workflow_engine import WorkflowEngine
from app.services.gateway_client import GatewayClient
from app.models.project import Project
from app.config import settings

logger = logging.getLogger(__name__)

router = APIRouter()

_active_connections: Dict[str, List[WebSocket]] = {}

def _validate_tdd_cases(cases: list[dict]) -> list[dict]:
    validated = []
    for i, c in enumerate(cases):
        validated.append({
            "case_index": i,
            "case_id": c.get("case_id", f"TC-{i+1:03d}"),
            "title": c.get("title", ""),
            "description": c.get("description", ""),
            "precondition": c.get("precondition", ""),
            "test_steps": c.get("test_steps", ""),
            "expected_result": c.get("expected_result", ""),
            "priority": c.get("priority", "P2"),
            "category": c.get("category", ""),
            "source_section": c.get("source_section", ""),
        })
    return validated


def _save_tdd_cases_to_db(db, project_id, workflow_step_id, round_number, cases: list[dict]):
    from app.models.tdd_test_case import TDDTestCase
    db.query(TDDTestCase).filter(
        TDDTestCase.project_id == project_id,
        TDDTestCase.round_number == round_number,
    ).delete()
    saved = []
    for case in cases:
        record = TDDTestCase(
            project_id=project_id,
            workflow_step_id=workflow_step_id,
            round_number=round_number,
            case_index=case["case_index"],
            case_id=case["case_id"],
            title=case["title"],
            description=case.get("description", ""),
            precondition=case.get("precondition", ""),
            test_steps=case.get("test_steps", ""),
            expected_result=case.get("expected_result", ""),
            priority=case.get("priority", "P2"),
            category=case.get("category", ""),
            source_section=case.get("source_section", ""),
            qa_status="pending",
        )
        db.add(record)
        saved.append(record)
    db.commit()
    return saved


def _get_tdd_cases(db, project_id, round_number):
    from app.models.tdd_test_case import TDDTestCase
    return db.query(TDDTestCase).filter(
        TDDTestCase.project_id == project_id,
        TDDTestCase.round_number == round_number,
    ).order_by(TDDTestCase.case_index).all()


def _get_failed_tdd_cases(db, project_id, round_number):
    from app.models.tdd_test_case import TDDTestCase
    return db.query(TDDTestCase).filter(
        TDDTestCase.project_id == project_id,
        TDDTestCase.round_number == round_number,
        TDDTestCase.qa_status == "failed",
    ).order_by(TDDTestCase.case_index).all()


async def _call_hourong_inspect(prompt: str, save_dir: str = "", max_retries: int = 3) -> str:
    """step6 专用：委托子agent调用 hourong 逐行检验 TDD 测试用例，返回 JSON 文本。"""
    import asyncio, tempfile
    if not save_dir:
        save_dir = tempfile.gettempdir()
    os.makedirs(save_dir, exist_ok=True)

    for attempt in range(1, max_retries + 1):
        report_path = os.path.join(save_dir, f"tdd_hourong_{os.urandom(4).hex()}.json")
        task = _json.dumps({"save_path": report_path, "task": prompt}, ensure_ascii=False)

        results = await delegate_task(
            tasks=[task],
            wait_all=True, timeout=300,
            max_concurrent=1,
            profile_name="hourong",
        )

        result = results[0] if results else ""
        if result and not result.startswith("[子Agent") and os.path.exists(result):
            for _ in range(5):
                try:
                    with open(result, "r", encoding="utf-8") as f:
                        content = f.read().strip()
                    if content and len(content) > 10:
                        return content
                except Exception:
                    pass
                await asyncio.sleep(0.5)

        if attempt >= max_retries:
            logger.error(f"hourong TDD 检验失败({max_retries}次): {result}")
            return ""

    return ""


async def _inspect_tdd_cases_db(
    db, websocket: WebSocket, project_id: str,
    round_number: int, project_name: str = "", project_description: str = "",
    core_goal: str = "", agent_label: str = "", max_retries: int = 3,
    failed_case_ids: list = None, save_dir: str = "",
) -> dict:
    import asyncio as _asyncio
    import math
    from app.models.tdd_test_case import TDDTestCase

    cases = _get_tdd_cases(db, project_id, round_number)
    if not cases:
        return {"passed": False, "detail": "数据库中没有测试用例", "failed_details": [], "results": [],
                "total_cases": 0, "passed_cases": 0, "failed_cases": 0}

    if failed_case_ids:
        active_cases = [c for c in cases if c.case_id in failed_case_ids]
    else:
        active_cases = cases

    if not active_cases:
        return {"passed": True, "detail": "没有需要检验的用例", "failed_details": [], "results": [],
                "total_cases": len(cases), "passed_cases": len(cases), "failed_cases": 0}

    # 将 active_cases 分成最多5个分片
    n_agents = min(5, len(active_cases))
    chunk_size = math.ceil(len(active_cases) / n_agents) if n_agents > 0 else len(active_cases)
    chunks = [active_cases[i:i + chunk_size] for i in range(0, len(active_cases), chunk_size)]

    focus_hint = ""
    if failed_case_ids:
        focus_hint = f"\n⚠️ 本次只检验以下 {len(active_cases)} 个不合格用例：{failed_case_ids}\n请只针对这些用例做出判定，禁止扩大范围。"

    from app.services.gateway_client import GatewayClient as _GatewayClient

    # 构建所有分片的检验 prompt
    prompts = []
    for chunk in chunks:
        cases_json = _json.dumps([
            {
                "用例编号": c.case_id,
                "标题": c.title,
                "描述": c.description or "",
                "前置条件": c.precondition or "",
                "测试步骤": c.test_steps or "",
                "预期结果": c.expected_result or "",
                "优先级": c.priority or "P2",
                "分类": c.category or "",
            }
            for c in chunk
        ], ensure_ascii=False, indent=2)

        insp_prompt = (
            "你是一个专业的TDD PLAN QA检验员（后荣）。请逐行检验以下测试用例。\n\n"
            "检验标准：\n"
            "1. 原子性：每个用例是否最小原子化，不包含多个独立测试场景\n"
            "2. 可验证性：预期结果是否明确可量化\n"
            "3. 可行性：测试步骤在技术上是否可执行\n"
            "4. 完整性：描述、前置条件、测试步骤、预期结果是否完整\n"
            "5. 优先级标注是否合理\n"
            f"{focus_hint}\n"
            "=== 测试用例数据（从数据库读取）===\n"
            f"{cases_json}\n\n"
            "评分规则：每个用例起始100分。\n"
            "- 轻微问题扣5-10分（如措辞不精确）\n"
            "- 一般问题扣15-20分（如步骤不完整、预期结果不明确）\n"
            "- 严重问题扣25-30分（如用例不可执行、违背原子性）\n"
            "得分≥90则用例合格。\n"
            "===== 输出规则（严格执行，违者重罚）=====\n"
            "1. 禁止任何思考过程、推理、解释、注释、额外文字\n"
            "2. 只输出JSON对象，不要 markdown 代码块标记\n"
            "3. 输出格式：{\"results\": [对每个用例一个对象]}\n"
            "4. 每个用例对象包含 case_id, score(整数), passed(bool), feedback(字符串), detail(字符串) 五个字段\n"
            "严格按照下面的格式（只修改 score、passed、feedback、detail 四个字段的值）：\n"
            "{\"results\": [\n"
            + ",\n".join(
                f'  {{"case_id": "{c.case_id}", "score": 100, "passed": true, "feedback": "检验意见", "detail": "修改建议"}}'
                for c in chunk
            ) + "\n"
            "]}"
        )
        prompts.append(insp_prompt)

    await broadcast(project_id, {"type": "progress", "message": f"🔍 hourong {len(chunks)}个子agent并行检验 {len(active_cases)} 个测试用例..."})
    logger.info(f"Step6 hourong: 开始并行检验 {len(active_cases)} 个用例, {len(chunks)} 个分片")

    import datetime
    start_ts = datetime.datetime.now(datetime.timezone.utc)

    # 直连小时荣模型（绕过 hermes 网关，网关会加 17K+ system prompt 导致超时）
    _gc = _GatewayClient(profile_name="hourong", timeout=600)

    # 读取小时荣模型配置
    _hr_config = _read_profile_config("hourong") or {}
    _hr_model = _hr_config.get("model", {}).get("default", "Qwen3.6-27B-AWQ-INT4")
    _hr_base = _hr_config.get("model", {}).get("base_url", "http://10.34.1.96:8000/v1")
    _hr_key = _hr_config.get("model", {}).get("api_key", "gbm_cq_vllm")
    _hr_url = f"{_hr_base.rstrip('/')}/chat/completions"

    async def _direct_call_one(chunk_idx: int, prompt: str) -> str:
        try:
            _payload = {
                "model": _hr_model,
                "messages": [
                    {"role": "system", "content": "你只输出JSON，不要任何思考过程。"},
                    {"role": "user", "content": prompt},
                ],
                "max_tokens": 8192,
                "stream": True,
                "temperature": 0.3,
                "response_format": {"type": "json_object"},
            }
            _headers = {
                "Content-Type": "application/json",
                "Authorization": f"Bearer {_hr_key}",
            }
            result_text = ""
            async with httpx.AsyncClient(timeout=600) as _client:
                async with _client.stream("POST", _hr_url, headers=_headers, json=_payload) as _resp:
                    if _resp.status_code != 200:
                        _err = await _resp.aread()
                        logger.error(f"Step6 hourong 分片{chunk_idx+1} HTTP {_resp.status_code}: {_err.decode()[:200]}")
                        return ""
                    async for _line in _resp.aiter_lines():
                        if _line.startswith("data: "):
                            _d = _line[6:]
                            if _d == "[DONE]":
                                break
                            try:
                                _chunk = _json.loads(_d)
                                _content = _chunk.get("choices", [{}])[0].get("delta", {}).get("content", "")
                                if _content:
                                    result_text += _content
                            except _json.JSONDecodeError:
                                pass
            return result_text
        except Exception as e:
            logger.error(f"Step6 hourong 分片{chunk_idx+1} 直连调用失败: {e}")
            return ""

    coros = [_direct_call_one(i, p) for i, p in enumerate(prompts)]
    raw_results = list(await _asyncio.gather(*coros))

    elapsed = (datetime.datetime.now(datetime.timezone.utc) - start_ts).total_seconds()
    logger.info(f"Step6 hourong: 并行检验完成, 耗时 {elapsed:.1f}s, {sum(1 for r in raw_results if r)}/{len(raw_results)} 分片成功")

    # 记录每个分片结果
    for idx, rr in enumerate(raw_results):
        if rr:
            logger.info(f"Step6 hourong 分片{idx+1} 结果前200字: {rr[:200]}")
        else:
            logger.warning(f"Step6 hourong 分片{idx+1} 无结果")

    # 收集+广播+保存所有结果
    all_parsed = []
    all_passed = True
    failed_details = []
    results = []
    saved_case_ids = set()

    for qa_content in raw_results:
        if not qa_content:
            continue

        # 鲁棒 JSON 提取：先尝试从完整 JSON 对象取 results 数组
        parsed_chunk = None
        try:
            _full = _json.loads(qa_content)
            if isinstance(_full, dict):
                _arr = _full.get("results") or _full.get("cases") or _full.get("case_ids") or _full.get("items")
                if isinstance(_arr, list):
                    parsed_chunk = _arr
        except Exception:
            pass

        # 兜底：从第一个 [ 开始逐次尝试到每个 ]
        if not parsed_chunk:
            start = qa_content.find('[')
            if start != -1:
                for end in range(start + 1, len(qa_content)):
                    if qa_content[end] == ']':
                        candidate = qa_content[start:end + 1]
                        try:
                            parsed = _json.loads(candidate)
                            if isinstance(parsed, list):
                                parsed_chunk = parsed
                                break
                        except Exception:
                            pass
        if not parsed_chunk:
            logger.warning(f"Step6 hourong 分片无法解析JSON: {qa_content[:300]}")
            continue

        logger.info(f"Step6 hourong 分片结果: {len(parsed_chunk)} 个用例")
        for item in parsed_chunk:
            cid = item.get("case_id", "")
            if cid in saved_case_ids:
                continue
            saved_case_ids.add(cid)
            score = int(item.get("score", 100))
            passed = item.get("passed", score >= 90)
            if isinstance(passed, str):
                passed = passed.lower() == "true"
            case_passed = passed and score >= 90

            await broadcast(project_id, {
                "type": "case_result",
                "case_id": cid,
                "title": item.get("title", ""),
                "passed": case_passed,
                "score": score,
                "feedback": item.get("feedback", ""),
            })

            if not case_passed:
                all_passed = False
                failed_details.append(item.get("feedback", f"用例{cid}不合格"))

            db.query(TDDTestCase).filter(
                TDDTestCase.project_id == project_id,
                TDDTestCase.round_number == round_number,
                TDDTestCase.case_id == cid,
            ).update({
                "qa_status": "passed" if case_passed else "failed",
                "qa_score": score,
                "qa_feedback": item.get("feedback", ""),
                "qa_detail": item.get("detail", ""),
            })
            results.append({"case_id": cid, "score": score, "passed": case_passed, "feedback": item.get("feedback", "")})

        db.commit()
        all_parsed.extend(parsed_chunk)

    logger.info(f"Step6 hourong 检验汇总: {len(all_parsed)} 条结果, all_passed={all_passed}")
    if not all_parsed:
        return {"passed": False, "detail": "所有分片检验均无结果", "failed_details": [], "results": [],
                "total_cases": len(cases), "passed_cases": 0, "failed_cases": 0}

    scores = [r["score"] for r in results]
    avg_score = sum(scores) / len(scores) if scores else 0
    return {
        "passed": all_passed,
        "score": avg_score,
        "total_score": sum(scores),
        "max_score": len(scores) * 100,
        "detail": "",
        "failed_details": failed_details,
        "results": results,
        "total_cases": len(cases),
        "passed_cases": sum(1 for r in results if r["passed"]),
        "failed_cases": sum(1 for r in results if not r["passed"]),
    }

async def _build_tdd_plan_text(final_cases: list) -> str:
    lines = ["# TDD测试用例计划\n", f"## 总览\n\n共 {len(final_cases)} 个测试用例\n"]
    for fc in final_cases:
        lines.append(f"\n### [{fc.case_id}] {fc.title}\n")
        lines.append(f"- **描述**: {fc.description or '无'}\n")
        lines.append(f"- **前置条件**: {fc.precondition or '无'}\n")
        lines.append(f"- **测试步骤**: {fc.test_steps or '无'}\n")
        lines.append(f"- **预期结果**: {fc.expected_result or '无'}\n")
        lines.append(f"- **优先级**: {fc.priority or 'P2'}\n")
        lines.append(f"- **分类**: {fc.category or '无'}\n")
    return "\n".join(lines)


def _save_tdd_plan_handoff(slug: str, docs_dir: str, round_number: int, tdd_plan_text: str) -> str:
    filename = f"{slug}_TDD_PLAN_V{round_number}.md"
    filepath = os.path.join(docs_dir, filename)
    os.makedirs(docs_dir, exist_ok=True)
    with open(filepath, "w", encoding="utf-8") as f:
        f.write(tdd_plan_text)
    logger.info(f"Step6 handoff TDD PLAN saved: {filepath} ({len(tdd_plan_text)} chars)")
    return filepath


async def broadcast(project_id: str, message: dict):
    dead: List[WebSocket] = []
    for ws in _active_connections.get(project_id, []):
        try:
            await ws.send_json(message)
        except Exception:
            dead.append(ws)
    if dead:
        _active_connections[project_id] = [
            ws for ws in _active_connections.get(project_id, [])
            if ws not in dead
        ]





async def _run_step6(websocket: WebSocket, project_id: str, db) -> bool:
    """执行步骤6：海梅直接输出JSON测试用例到数据库，hourong逐行检验+收敛修复"""
    import asyncio as _asyncio

    if websocket not in _active_connections.get(project_id, []):
        _active_connections.setdefault(project_id, []).append(websocket)

    try:
        engine = WorkflowEngine(project_id=project_id, db=db)
        engine.advance_step(6)

        step3 = engine.get_step3_artifacts() or {}
        requirement = (step3.get("doc_content") or step3.get("content") or step3.get("requirement") or step3.get("srs") or "")
        step4 = engine.get_step4_artifacts() or {}
        design_doc = step4.get("design_doc") or ""
        step5 = engine.get_step5_artifacts() or {}
        env_info = step5.get("env_info") or step5.get("environment") or ""
        step2 = engine.get_step2_artifacts() or {}
        core_goal = step2.get("confirmed_goal") or step2.get("core_goal") or ""

        engine.save_step6_artifacts({"status": "generating", "message": "📋 海梅正在制订TDD PLAN..."})
        await broadcast(project_id, {"type": "progress", "message": "📋 海梅正在制订TDD PLAN..."})

        proj = db.query(Project).filter(Project.id == project_id).first()
        if not proj:
            await broadcast(project_id, {"type": "error", "message": "Project not found"})
            return True
        slug = proj.slug or project_id.replace("-", "")
        docs_dir = os.path.join(settings.PROJECTS_BASE_DIR, slug, "docs")
        os.makedirs(docs_dir, exist_ok=True)
        qa_reports_dir = os.path.join(docs_dir, "qa_reports")
        os.makedirs(qa_reports_dir, exist_ok=True)
        proj_name = proj.name
        proj_desc = proj.description or ""

        existing = engine.get_step6_artifacts() or {}
        if existing.get("qa_passed"):
            engine.save_step6_artifacts({**existing, "status": "done", "message": "♻️ 续跑：TDD PLAN已通过检验，跳过"})
            engine.complete_step(6, artifacts={**engine.get_step6_artifacts(), "qa_passed": True})
            await broadcast(project_id, {"type": "done", "message": "✅ TDD PLAN已生成（续跑）"})
            return True

        # 检查数据库中是否已有 TDD 测试用例（防止 haimei 重复生成）
        from app.models.tdd_test_case import TDDTestCase
        from sqlalchemy import func
        db_stats = db.query(
            func.max(TDDTestCase.round_number).label("max_round"),
            func.count(TDDTestCase.id).label("total"),
        ).filter(
            TDDTestCase.project_id == project_id
        ).first()
        existing_case_count = db_stats.total if db_stats else 0
        existing_max_round = db_stats.max_round if db_stats and db_stats.max_round else 0

        convergence_log = list(existing.get("convergence", []))
        init_failed_case_ids = []  # 从 hourong 检验结果中收集的不合格用例

        if existing_case_count > 0:
            await broadcast(project_id, {"type": "progress", "message": f"♻️ 数据库中已有 {existing_case_count} 个 TDD 测试用例（最高第 {existing_max_round} 轮），跳过 haimei 生成，直接交由 hourong 检验..."})

            # 直接由 hourong 检验数据库中已有的用例
            qa_result = await _inspect_tdd_cases_db(
                db, websocket, project_id, existing_max_round,
                project_name=proj_name, project_description=proj_desc,
                core_goal=core_goal,
                save_dir=qa_reports_dir,
            )

            def _hourong_timeout(r: dict) -> bool:
                return "passed" in r and not r.get("passed") and not r.get("results") and r.get("total_cases", 0) > 0

            hr_retry = 0
            while hr_retry < 3 and ("passed" not in qa_result or _hourong_timeout(qa_result)):
                hr_retry += 1
                logger.warning(f"Step6 hourong 检验超时或无结果（第{hr_retry}次重试）")
                await broadcast(project_id, {"type": "progress", "message": f"⚠️ hourong 检验超时，第{hr_retry}次重新检验..."})
                qa_result = await _inspect_tdd_cases_db(
                    db, websocket, project_id, existing_max_round,
                    project_name=proj_name, project_description=proj_desc,
                    core_goal=core_goal,
                    save_dir=qa_reports_dir,
                )

            if hr_retry >= 3:
                await broadcast(project_id, {"type": "error", "message": "❌ hourong连续3次检验均超时或无结果，终止步骤6"})
                engine.reset_step(6)
                return True

            passed_count = qa_result.get("passed_cases", 0)
            failed_count = qa_result.get("failed_cases", 0)
            total_count = qa_result.get("total_cases", 0)

            if qa_result.get("passed"):
                await broadcast(project_id, {"type": "progress", "message": f"✅ hourong 检验通过（{passed_count}/{total_count} 个用例合格）"})
                    # 全部通过 → 生成 TDD 计划文本，标记完成
                final_cases = _get_tdd_cases(db, project_id, existing_max_round)
                tdd_plan_text = _build_tdd_plan_text(final_cases) if final_cases else ""
                handoff_path = _save_tdd_plan_handoff(slug, docs_dir, existing_max_round, tdd_plan_text) if tdd_plan_text else ""
                engine.save_step6_artifacts({
                    **existing, "qa_passed": True, "status": "done",
                    "tdd_plan": tdd_plan_text,
                    "handoff_path": handoff_path,
                    "current_fix_round": existing_max_round,
                    "message": f"✅ {existing_case_count}个用例全部通过（从数据库恢复）",
                })
                engine.complete_step(6, artifacts={**engine.get_step6_artifacts(), "qa_passed": True})
                await broadcast(project_id, {"type": "done", "message": f"✅ TDD PLAN已生成，{total_count}个用例全部通过（从数据库恢复）"})
                return True

            # DB中真的没有用例 → 视为通过
            if existing_case_count == 0:
                engine.save_step6_artifacts({
                    **existing, "qa_passed": True, "status": "done",
                    "current_fix_round": existing_max_round,
                    "message": "✅ 没有需检验的用例",
                })
                engine.complete_step(6, artifacts={**engine.get_step6_artifacts(), "qa_passed": True})
                await broadcast(project_id, {"type": "done", "message": "✅ TDD PLAN已生成，没有需检验的用例"})
                return True

            # 有不合格用例 → 记录失败项，进入收敛修复循环
            await broadcast(project_id, {"type": "progress", "message": f"⚠️ hourong 检验发现 {failed_count}/{total_count} 个不合格用例，进入修复循环..."})
            results_list = qa_result.get("results", [])
            init_failed_case_ids = [r.get("case_id", "") for r in results_list if not r.get("passed", False)]

            # 将本次检验结果写入 convergence_log，供后续循环使用
            convergence_log.append({
                "round": existing_max_round,
                "detail": qa_result.get("detail", ""),
                "passed": qa_result.get("passed", False),
                "failed_details": qa_result.get("failed_details", []),
                "results": results_list,
                "total_cases": total_count,
                "passed_cases": passed_count,
                "failed_cases": failed_count,
            })

            saved_round = existing_max_round
        else:
            # TDD PLAN 已存在但 qa_passed 未标记 → 检查收敛记录，完成步骤
            if existing.get("tdd_plan") and convergence_log:
                last_entry = convergence_log[-1] if convergence_log else {}
                if last_entry.get("passed"):
                    engine.save_step6_artifacts({**existing, "qa_passed": True, "status": "done", "message": "♻️ TDD计划已存在且检验通过"})
                    engine.complete_step(6, artifacts={**engine.get_step6_artifacts(), "qa_passed": True})
                    await broadcast(project_id, {"type": "done", "message": "✅ TDD PLAN已生成（TDD计划已存在）"})
                    return True

            # 断点续做：从 DB 恢复已完成轮次
            saved_round = existing.get("current_fix_round", 0)
            if saved_round > 0 and convergence_log:
                await broadcast(project_id, {"type": "progress", "message": f"♻️ 检测到已有进度（已完成 {saved_round} 轮），从第 {saved_round + 1} 轮继续..."})
            else:
                saved_round = 0

        srs_path = step3.get("doc_path") or step3.get("file_path") or ""
        if not srs_path or not os.path.exists(srs_path):
            max_sv = 0
            for f in glob.glob(os.path.join(docs_dir, f"{slug}_SRS_V*.md")):
                m = _re.search(r'V(\d+)', os.path.basename(f))
                if m: max_sv = max(max_sv, int(m.group(1)))
            if max_sv > 0:
                srs_path = os.path.join(docs_dir, f"{slug}_SRS_V{max_sv}.md")

        design_path = ""
        design_doc_paths = step4.get("doc_paths", {})
        if isinstance(design_doc_paths, dict):
            design_path = design_doc_paths.get('arch_reasonableness', '') or design_doc_paths.get('architecture', '')
        if not design_path or not os.path.exists(design_path):
            max_dv = 0
            for f in glob.glob(os.path.join(docs_dir, f"{slug}_ARCHITECTURE_V*.md")):
                m = _re.search(r'V(\d+)', os.path.basename(f))
                if m: max_dv = max(max_dv, int(m.group(1)))
            if max_dv > 0:
                design_path = os.path.join(docs_dir, f"{slug}_ARCHITECTURE_V{max_dv}.md")

        env_path = ""
        if env_info:
            max_ev = 0
            for f in glob.glob(os.path.join(docs_dir, f"{slug}_ENV_V*.md")):
                m = _re.search(r'V(\d+)', os.path.basename(f))
                if m: max_ev = max(max_ev, int(m.group(1)))
            if max_ev > 0:
                env_path = os.path.join(docs_dir, f"{slug}_ENV_V{max_ev}.md")

        step6_row = engine._get_step_row(6)
        wf_step_id = step6_row.id if step6_row else None

        start_round = saved_round + 1
        for fix_round in range(start_round, 11):
            await broadcast(project_id, {"type": "progress", "message": f"📋 海梅正在{'修复不合格用例' if fix_round > 1 else '生成'}TDD测试用例（第{fix_round}轮）..."})

            feedback = ""
            failed_case_ids = []
            if fix_round > 1 and convergence_log:
                last = convergence_log[-1]
                results = last.get("results", [])
                failed_results = [r for r in results if not r.get("passed", True)]
                failed_case_ids = [r.get("case_id", "") for r in failed_results]

                if failed_case_ids:
                    failed_cases_from_db = _get_failed_tdd_cases(db, project_id, fix_round - 1)
                    case_lines = []
                    for fc in failed_cases_from_db:
                        case_lines.append(
                            f"  - [{fc.case_id}] {fc.title}\n"
                            f"    反馈：{fc.qa_feedback or '无'}\n"
                            f"    修改建议：{fc.qa_detail or '无'}"
                        )
                    if case_lines:
                        feedback = "需要修正的问题（只修复以下不合格用例，禁止扩大范围）：\n" + "\n\n".join(case_lines)

            prompt_lines = [
                "你是资深项目经理海梅（HaiMei），负责制订TDD测试用例。\n",
            ]
            if srs_path:
                prompt_lines.append(f"请读取需求文档（SRS）：{srs_path}\n\n")
            if design_path:
                prompt_lines.append(f"请读取架构设计文档：{design_path}\n\n")
            if env_path:
                prompt_lines.append(f"请读取开发环境信息：{env_path}\n\n")

            if fix_round > 1:
                prompt_lines.append(
                    "=== 任务：只修复不合格用例 ===\n"
                    "以下是用例检验中发现的缺陷，请逐条修正并输出JSON数组。\n"
                    "不要包含已合格的用例，只输出需要修复的用例。\n\n"
                    f"{feedback}\n\n"
                )
                prompt_lines.append(
                    "输出格式（JSON数组，每个对象代表一个修复后的用例）：\n"
                    '[\n'
                    '  {\n'
                    '    "case_id": "TC-001",\n'
                    '    "title": "测试用例标题",\n'
                    '    "description": "用例描述",\n'
                    '    "precondition": "前置条件",\n'
                    '    "test_steps": "1. 步骤1\\n2. 步骤2",\n'
                    '    "expected_result": "预期结果",\n'
                    '    "priority": "P0/P1/P2/P3",\n'
                    '    "category": "功能测试/性能测试/安全测试/...",\n'
                    '    "source_section": "对应需求章节"\n'
                    '  }\n'
                    ']\n'
                )
            else:
                if feedback:
                    prompt_lines.append(f"=== 上次检验未通过项 ===\n{feedback}\n\n")
                prompt_lines.append(
                    "要求：\n"
                    "1. 每个测试用例最小原子化\n"
                    "2. 每个测试用例有明确可量化的验收标准\n"
                    "3. 覆盖所有功能和非功能需求\n"
                    "4. 标注优先级和执行顺序\n"
                    "5. 包含前置条件、测试步骤、预期结果\n"
                    "只输出 JSON 数组，不要有其他文字：\n"
                    '[\n'
                    '  {\n'
                    '    "case_id": "TC-001",\n'
                    '    "title": "测试用例标题",\n'
                    '    "description": "用例描述",\n'
                    '    "precondition": "前置条件",\n'
                    '    "test_steps": "1. 步骤1\\n2. 步骤2",\n'
                    '    "expected_result": "预期结果",\n'
                    '    "priority": "P0/P1/P2/P3",\n'
                    '    "category": "功能测试/性能测试/安全测试/...",\n'
                    '    "source_section": "对应需求章节"\n'
                    '  }\n'
                    ']\n'
                )
            prompt = "\n".join(prompt_lines)

            await broadcast(project_id, {"type": "prompt", "prompt": prompt, "round": fix_round, "total_rounds": 10})

            client = GatewayClient(profile_name="haimei", timeout=3600)
            chunks = []
            try:
                async for chunk in client.chat_isolated(
                    messages=[{"role": "user", "content": prompt}],
                    project_id=project_id, project_name=proj_name, project_description=proj_desc,
                    core_goal=core_goal, agent_name="海梅（HaiMei）-TDD PLAN生成",
                    stream=True, max_tokens=64000,
                    project_slug=slug,
                ):
                    if chunk.strip():
                        chunks.append(chunk)
                        await broadcast(project_id, {"type": "content", "content": chunk})
            except Exception as e:
                logger.error(f"Step6 haimei调用失败: {e}", exc_info=True)
                await broadcast(project_id, {"type": "error", "message": f"❌ 海梅执行失败: {str(e)[:100]}"})
                engine.reset_step(6)
                return True

            raw = "".join(chunks).strip()
            brace_s = raw.find('[')
            brace_e = raw.rfind(']') + 1
            if brace_s != -1 and brace_e > brace_s:
                json_str = raw[brace_s:brace_e]
            else:
                json_str = raw

            try:
                cases_json = _json.loads(json_str)
            except Exception:
                await broadcast(project_id, {"type": "progress", "message": "⚠️ 海梅输出不是有效JSON数组，重试"})
                continue

            if not isinstance(cases_json, list) or len(cases_json) == 0:
                await broadcast(project_id, {"type": "progress", "message": "⚠️ 海梅未生成有效测试用例，重试"})
                continue

            validated_cases = _validate_tdd_cases(cases_json)

            if fix_round > 1:
                prev_cases = _get_tdd_cases(db, project_id, fix_round - 1)
                passed_prev = [c for c in prev_cases if c.qa_status == "passed"]
                existing_ids = {c["case_id"] for c in validated_cases}
                for c in passed_prev:
                    if c.case_id not in existing_ids:
                        validated_cases.append({
                            "case_id": c.case_id,
                            "title": c.title,
                            "description": c.description or "",
                            "precondition": c.precondition or "",
                            "test_steps": c.test_steps or "",
                            "expected_result": c.expected_result or "",
                            "priority": c.priority or "P2",
                            "category": c.category or "",
                            "source_section": c.source_section or "",
                        })
                validated_cases.sort(key=lambda x: x.get("case_id", ""))

            _save_tdd_cases_to_db(db, project_id, wf_step_id, fix_round, validated_cases)
            await broadcast(project_id, {"type": "progress", "message": f"✅ 已将 {len(validated_cases)} 个测试用例保存到数据库（第{fix_round}轮）"})

            engine.save_step6_artifacts({"status": "generating", "current_fix_round": fix_round, "message": f"第{fix_round}轮：{len(validated_cases)}个用例已保存"})

            await broadcast(project_id, {"type": "progress", "message": f"🔍 hourong 正在从数据库逐行检验TDD测试用例（第{fix_round}轮）"})
            qa_result = await _inspect_tdd_cases_db(
                db, websocket, project_id, fix_round,
                project_name=proj_name, project_description=proj_desc,
                core_goal=core_goal,
                failed_case_ids=failed_case_ids if failed_case_ids else None,
                save_dir=qa_reports_dir,
            )

            hr_retry = 0
            while "passed" not in qa_result and hr_retry < 3:
                hr_retry += 1
                await broadcast(project_id, {"type": "progress", "message": f"⚠️ hourong未生成有效检验报告，第{hr_retry}次重新检验..."})
                qa_result = await _inspect_tdd_cases_db(
                    db, websocket, project_id, fix_round,
                    project_name=proj_name, project_description=proj_desc,
                    core_goal=core_goal,
                    failed_case_ids=failed_case_ids if failed_case_ids else None,
                    save_dir=qa_reports_dir,
                )

            convergence_log.append({
                "round": fix_round,
                "detail": qa_result.get("detail", ""),
                "passed": qa_result.get("passed", False),
                "failed_details": qa_result.get("failed_details", []),
                "results": qa_result.get("results", []),
                "total_cases": qa_result.get("total_cases", 0),
                "passed_cases": qa_result.get("passed_cases", 0),
                "failed_cases": qa_result.get("failed_cases", 0),
            })

            # 持久化：每轮结束后保存完整进度到 DB，支持断点续做
            engine.save_step6_artifacts({
                "status": "generating",
                "current_fix_round": fix_round,
                "convergence": convergence_log,
                "message": f"第{fix_round}轮完成：{qa_result.get('passed_cases', 0)}/{qa_result.get('total_cases', 0)} 个用例通过",
                "last_updated_at": __import__('datetime').datetime.now(__import__('datetime').timezone.utc).isoformat(),
            })

            if "passed" not in qa_result:
                await broadcast(project_id, {"type": "error", "message": "❌ hourong多次无法生成有效检验报告，终止步骤"})
                break

            passed_count = qa_result.get("passed_cases", 0)
            failed_count = qa_result.get("failed_cases", 0)
            total_count = qa_result.get("total_cases", 0)
            if qa_result.get("passed"):
                await broadcast(project_id, {"type": "progress", "message": f"✅ 全部 {total_count} 个测试用例已通过 hourong 逐行检验（共{fix_round}轮）"})
                # 从DB读取最终通过用例，生成TDD计划文本 + 交接文件
                final_cases = _get_tdd_cases(db, project_id, fix_round)
                tdd_plan_text = _build_tdd_plan_text(final_cases) if final_cases else ""
                handoff_path = _save_tdd_plan_handoff(slug, docs_dir, fix_round, tdd_plan_text) if tdd_plan_text else ""
                engine.save_step6_artifacts({
                    "convergence": convergence_log, "status": "done", "qa_passed": True,
                    "message": f"✅ {total_count}个用例全部通过",
                    "tdd_plan": tdd_plan_text, "handoff_path": handoff_path,
                })
                engine.complete_step(6, artifacts={**engine.get_step6_artifacts(), "qa_passed": True})
                await broadcast(project_id, {"type": "done", "message": f"✅ TDD PLAN已生成，{total_count}个用例全部通过"})
                return True

            await broadcast(project_id, {"type": "progress", "message": f"⚠️ {failed_count}/{total_count} 个用例未通过（通过率 {passed_count}/{total_count}），正在逐行修复不合格用例..."})

        last_log = convergence_log[-1] if convergence_log else {}
        total_cases = last_log.get("total_cases", 0)
        failed_cases = last_log.get("failed_cases", 0)
        passed_cases = last_log.get("passed_cases", 0)
        await broadcast(project_id, {"type": "progress", "message": f"❌ 经10轮仍未通过检验（通过 {passed_cases}/{total_cases} 个用例，{failed_cases} 个仍不合格）"})
        await broadcast(project_id, {"type": "error", "message": f"❌ 经10轮仍未通过检验（{failed_cases} 个用例不合格）"})
        engine.save_step6_artifacts({"convergence": convergence_log, "status": "error"})
        engine.reset_step(6)
        return True

    except Exception as e:
        logger.error(f"Step6 execution error: {e}", exc_info=True)
        try:
            err_engine = WorkflowEngine(project_id=project_id, db=db)
            err_engine.reset_step(6)
        except Exception:
            pass
        await broadcast(project_id, {"type": "error", "message": f"❌ 步骤6失败: {str(e)[:200]}"})
        return True


@router.websocket("/step6/progress/{project_id}")
async def step6_progress_ws(websocket: WebSocket, project_id: str,
                            token: str = Query(...)):
    await websocket.accept()
    from app.database import SessionLocal
    db = SessionLocal()
    try:
        user = await verify_token(token, db)
        if not user:
            await websocket.send_json({"type": "error", "message": "Invalid token"})
            await websocket.close()
            return

        _active_connections.setdefault(project_id, []).append(websocket)
        try:
            while True:
                data = await websocket.receive_text()
                logger.info(f"Step6 WS received: {data}")
                payload = _json.loads(data)
                action = payload.get("action", "")
                logger.info(f"Step6 action: {action}")

                if action == "execute":
                    logger.info(f"Step6: Starting _run_step6 for project {project_id}")
                    should_close = await _run_step6(websocket, project_id, db)
                    logger.info(f"Step6: _run_step6 completed for project {project_id}")
                    if should_close:
                        break

                elif action == "subscribe":
                    logger.info(f"Step6: Subscribed for project {project_id}")
                    await websocket.send_json({"type": "subscribed", "message": "已订阅实时状态"})

                elif action == "ping":
                    await websocket.send_json({"type": "pong"})

        except WebSocketDisconnect:
            pass
        finally:
            conns = _active_connections.get(project_id, [])
            if websocket in conns:
                conns.remove(websocket)
    except Exception as e:
        logger.error(f"Step6 WS error: {e}", exc_info=True)
        try:
            await websocket.send_json({"type": "error", "message": str(e)})
        except Exception:
            pass
    finally:
        db.close()
