import json as _json
import asyncio
import os
import re as _re
import logging
from typing import List
from fastapi import APIRouter, WebSocket, WebSocketDisconnect, Query

from app.api.ws.auth import verify_token
from app.models.project import Project
from app.services.gateway_client import GatewayClient
from app.config import settings
from app.services.doc_sharder import (
    get_shard_config, load_all_chapters, load_single_chapter,
    save_chapter, build_cacheable_chapter_summaries, ShardRetriever,
)

from .step3_qa_1 import run_completeness
from .step3_qa_2 import run_consistency
from .step3_qa_3 import run_verifiability
from .step3_qa_4 import run_unambiguity

CHAPTER_MARKER_START = "<!-- CHAPTER:"
CHAPTER_MARKER_END = "-->"


def _split_chapters(full_text: str) -> dict:
    chapters = {}
    pattern = _re.compile(
        rf'{_re.escape(CHAPTER_MARKER_START)}\s*([\w.]+)\s*{_re.escape(CHAPTER_MARKER_END)}'
        r'([\s\S]*?)(?='
        rf'{_re.escape(CHAPTER_MARKER_START)}|\Z)'
    )
    for m in pattern.finditer(full_text):
        key = m.group(1)
        content = m.group(2).strip()
        if content:
            chapters[key] = content
    return chapters

logger = logging.getLogger(__name__)

router = APIRouter()


def _load_qa_checkpoint(project_id: str, db) -> dict:
    from app.services.workflow_engine import WorkflowEngine
    engine = WorkflowEngine(project_id, db)
    artifacts = engine.get_step3_artifacts()
    cp = artifacts.get("qa_checkpoint")
    if cp and isinstance(cp, dict):
        return cp
    return {}


def _save_qa_checkpoint(
    project_id: str, db,
    step: int = 0, attempt: int = 0,
    results: list = None,
    content: str = "",
    last_save_path: str = "",
) -> bool:
    from app.services.workflow_engine import WorkflowEngine
    cp = {
        "step": step,
        "attempt": attempt,
        "results": results or [],
        "content": content,
        "last_save_path": last_save_path,
    }
    try:
        engine = WorkflowEngine(project_id, db)
        engine.save_step3_artifacts({"qa_checkpoint": cp})
        return True
    except Exception as e:
        logger.error(f"保存QA断点失败: {e}", exc_info=True)
        return False


def _clear_qa_checkpoint(project_id: str, db):
    _save_qa_checkpoint(project_id, db, step=4)


@router.websocket("/step3/qa/{project_id}")
async def step3_qa_ws(websocket: WebSocket, project_id: str, token: str = Query(...)):
    """QA phase WebSocket — hourong autonomously inspects, communicates with houxing, loop until pass."""
    await websocket.accept()

    from app.database import SessionLocal
    db = SessionLocal()
    try:
        user = await verify_token(token, db)
        if not user:
            await websocket.send_json({"type": "error", "message": "Invalid token"})
            await websocket.close()
            return

        project = db.query(Project).filter(Project.id == project_id).first()
        project_slug = project.slug if project else "unknown"
        project_docs_dir = os.path.join(settings.PROJECTS_BASE_DIR, project_slug, "docs")

        while True:
            data = await websocket.receive_text()
            payload = _json.loads(data)
            action = payload.get("action", "")

            if action == "inspect":
                content = payload.get("content", "")
                docs_path = payload.get("docs_path", "")
                if not content or len(content.strip()) < 20:
                    await websocket.send_json({"type": "error", "message": "文档内容过短"})
                    continue

                websocket._current_payload = payload
                await _run_qa_loop(websocket, content, project_slug, docs_path, project_id, db, project_docs_dir)
                websocket._current_payload = {}
                break

            elif action == "checkpoint":
                cp = _load_qa_checkpoint(project_id, db)
                await websocket.send_json({"type": "checkpoint", "data": cp})

            elif action == "ping":
                await websocket.send_json({"type": "pong"})

    except WebSocketDisconnect:
        pass
    except Exception as e:
        logger.error(f"QA WebSocket error: {e}", exc_info=True)
        try:
            await websocket.send_json({"type": "error", "message": str(e)})
        except Exception:
            pass
    finally:
        db.close()


async def _get_next_version(docs_path: str, project_slug: str) -> int:
    import glob
    pattern = os.path.join(docs_path, f"{project_slug}_SRS_V*.md")
    max_ver = 0
    for f in glob.glob(pattern):
        basename = os.path.basename(f)
        try:
            ver_str = basename.replace(f"{project_slug}_SRS_V", "").replace(".md", "")
            ver = int(ver_str)
            max_ver = max(max_ver, ver)
        except ValueError:
            continue
    return max_ver + 1


def _extract_json_result(text: str) -> list:
    text = text.strip()
    m = _re.search(r'```(?:json)?\s*([\s\S]*?)```', text)
    if m:
        text = m.group(1).strip()

    for candidate_text in [text, _re.sub(r'^[^{[]+', '', text), _re.sub(r'[^}\]]+$', '', text)]:
        try:
            parsed = _json.loads(candidate_text)
            if isinstance(parsed, list):
                return parsed
            if isinstance(parsed, dict):
                return [parsed]
        except Exception as e:
            logger.debug(f"_extract_json_result parse failed ({type(e).__name__}: {e}), candidate[:200]={candidate_text[:200]}")
            pass

    brace_starts = [i for i, c in enumerate(text) if c == '{']
    for start in reversed(brace_starts):
        depth = 0
        for end in range(start, len(text)):
            c = text[end]
            if c == '{':
                depth += 1
            elif c == '}':
                depth -= 1
                if depth == 0:
                    candidate = text[start:end + 1]
                    try:
                        parsed = _json.loads(candidate)
                        if isinstance(parsed, dict):
                            return [parsed]
                        if isinstance(parsed, list):
                            return parsed
                    except Exception:
                        pass
                    break

    bracket_starts = [i for i, c in enumerate(text) if c == '[']
    for start in reversed(bracket_starts):
        depth = 0
        for end in range(start, len(text)):
            c = text[end]
            if c == '[':
                depth += 1
            elif c == ']':
                depth -= 1
                if depth == 0:
                    candidate = text[start:end + 1]
                    try:
                        parsed = _json.loads(candidate)
                        if isinstance(parsed, list):
                            return parsed
                    except Exception:
                        pass
                    break

    return []


_DIMENSION_LABEL_TO_KEY = {
    "完整性": "completeness",
    "一致性": "consistency",
    "可验证性": "verifiability",
    "无歧义性": "unambiguity",
}
_DIMENSION_KEY_TO_LABEL = {v: k for k, v in _DIMENSION_LABEL_TO_KEY.items()}


def _normalize_inspection_results(parsed: list) -> list:
    if not parsed:
        return []

    first = parsed[0]

    has_chinese_dim = any(k in first for k in ("维度", "维 度", "检验维度", "检查项"))
    is_english_format = any(k in first for k in ("key", "dimension", "dim_key"))

    if not has_chinese_dim and not is_english_format:
        if "key" in first:
            is_english_format = True

    if is_english_format:
        result = {
            "key": first.get("key", first.get("dimension", "")),
            "label": (first.get("label", "") or
                      _DIMENSION_KEY_TO_LABEL.get(first.get("key", ""), first.get("key", ""))),
            "score": int(first.get("score", first.get("得分", 100))),
            "passed": bool(first.get("passed", first.get("pass", first.get("合格", True)))),
            "detail": (first.get("detail", "") or first.get("details", "") or first.get("comment", "")),
            "deduction": first.get("deduction", ""),
        }
        return [result] if result["key"] else []

    results = []
    for item in parsed:
        dim_label = (item.get("维度") or item.get("维 度") or
                     item.get("检验维度") or item.get("检查项") or "")
        dim_key = _DIMENSION_LABEL_TO_KEY.get(dim_label, dim_label)

        score_str = (item.get("得分") or item.get("分数") or
                     item.get("评分") or item.get("score") or "100")
        try:
            score = int(float(str(score_str)))
        except (ValueError, TypeError):
            score = 100

        passed_str = str(item.get("判定结果") or item.get("评定") or item.get("结果") or
                         item.get("结论") or item.get("passed") or "合格")
        passed = passed_str in ("通过", "合格", "通过", "true", "True", "pass", "PASS")

        defects = (item.get("不合格章节") or item.get("不合格项") or item.get("缺陷") or
                   item.get("问题") or item.get("issues") or item.get("items") or [])

        detail_parts = []
        if isinstance(defects, list) and defects:
            for d in defects:
                if isinstance(d, str):
                    detail_parts.append(d)
                    continue
                if not isinstance(d, dict):
                    continue
                if "项" in d:
                    shard_file = d.get("分片文件", "")
                    items = d.get("项", [])
                    if not isinstance(items, list):
                        continue
                    shard_lines = []
                    for idx, df_item in enumerate(items, 1):
                        reason = df_item.get("理由") or ""
                        evidence = df_item.get("证据") or df_item.get("位置") or ""
                        fix_dir = df_item.get("改善方向") or df_item.get("修改方向") or df_item.get("建议") or ""
                        shard_lines.append(
                            f"不合格的理由：{reason}；证据：{evidence}；改善方向：{fix_dir}"
                        )
                    if shard_lines:
                        detail_lines = "; ".join(shard_lines)
                        detail_parts.append(f"分片文件{shard_file}：{len(items)}项不合格，{detail_lines}")
                    continue
                defect_id = (d.get("缺陷编号") or d.get("编号") or d.get("id") or "")
                severity = (d.get("严重级别") or d.get("级别") or d.get("severity") or "")
                problem = (d.get("问题") or d.get("描述") or d.get("issue") or d.get("problem") or "")
                fix_dir = (d.get("修改方向") or d.get("建议") or d.get("fix") or "")
                evidence = (d.get("证据") or d.get("位置") or d.get("evidence") or "")
                parts = []
                if defect_id:
                    parts.append(f"[{defect_id}]")
                if severity:
                    parts.append(f"({severity})")
                if problem:
                    parts.append(f"{problem}。")
                if fix_dir:
                    parts.append(f"修改方向：{fix_dir}。")
                if evidence:
                    parts.append(f"证据：{evidence}")
                detail_parts.append(" ".join(parts))

        detail = "\n\n".join(detail_parts) if detail_parts else (
            item.get("detail") or item.get("details") or item.get("意见") or "")

        deduction = ""
        if not passed:
            deduction = f"得分{score}，满分100，扣{100 - score}分"

        results.append({
            "key": dim_key,
            "label": dim_label,
            "score": score,
            "passed": passed,
            "detail": detail,
            "deduction": deduction,
        })

    return results


HOURONG_SYSTEM_MSG = (
    "你是后荣（HouRong），DevFlow 平台的软件需求 QA 检验员。\n"
    "你严格按照 SRS 标准的 4 个维度（完整性、一致性、可验证性、无歧义性）检验需求文档。\n"
    "你可以先思考分析，但最终必须输出一个严格合法的 JSON 数组作为最终回答。\n"
    "JSON 数组必须包含全部 4 个维度的检验结果，不得遗漏、合并或替换任何维度。\n"
    "JSON 中每个元素的 field 名可以是中文（维度、得分、评定、不合格项）或英文（key、score、passed、detail）格式，"
    "两种格式均支持。推荐使用中文格式以获得更好的可读性。\n"
    "⚠️ 收敛性要求：你的检验报告必须聚焦于不合格项，明确指出每个不合格项的问题（问题）、修改方向（修改方向）和证据（证据）。"
    "后续Agent将严格根据你的检验报告只修改不合格项，禁止扩大修改范围。"
    "请勿对已合格维度提出修改要求。\n\n"
    "===== 分片标识要求（重要）=====\n"
    "需求文档内容中已用 <!-- CHAPTER:key --> 标记划分了各个分片（章节）。\n"
    "对于每个不合格项，其「证据」字段中必须包含该不合格项所在分片的 key，"
    "格式为 [chapter:key]，例如 [chapter:overview] 或 [chapter:functional]。\n"
    "如果同一不合格项涉及多个分片，列出所有相关分片key：例如 [chapter:overview][chapter:functional]。\n"
    "这是后续修复Agent定位修改范围的核心依据，请严格执行。"
)


async def _call_hourong(websocket, prompt, timeout=180, system_message=None, prev_reply=None, follow_up=None):
    client = GatewayClient(profile_name="hourong", timeout=timeout)
    collected = []
    messages = []
    if system_message:
        messages.append({"role": "system", "content": system_message})
    messages.append({"role": "user", "content": prompt})
    if prev_reply:
        messages.append({"role": "assistant", "content": prev_reply})
    if follow_up:
        messages.append({"role": "user", "content": follow_up})
    try:
        async for chunk in client.chat_completions(
            messages=messages,
            stream=True, max_tokens=8192,
        ):
            if chunk.strip():
                collected.append(chunk)
    except Exception as e:
        logger.error(f"hourong call failed: {e}")
        await websocket.send_json({"type": "progress", "content": f"\n⚠️ hourong调用失败: {e}\n"})
        return ""
    reply = "".join(collected).strip()
    logger.info(f"hourong reply (first 500 chars): {reply[:500]}")
    import tempfile, os
    filepath = os.path.join(tempfile.gettempdir(), f"hourong_{os.urandom(4).hex()}.json")
    with open(filepath, "w", encoding="utf-8") as f:
        f.write(reply)
    await websocket.send_json({"type": "progress", "content": filepath})
    return reply


SUB_STEPS = [
    {"step": 1, "key": "completeness", "label": "完整性",
     "description": "需求文档是否覆盖了所有必要的功能和非功能需求"},
    {"step": 2, "key": "consistency", "label": "一致性",
     "description": "文档内容前后是否一致，术语定义是否统一"},
    {"step": 3, "key": "verifiability", "label": "可验证性",
     "description": "每个需求是否可量化、可测试、可验证"},
    {"step": 4, "key": "unambiguity", "label": "无歧义性",
     "description": "需求描述是否清晰明确，不存在二义性理解"},
]

_SUB_RUNNERS = [
    run_completeness,
    run_consistency,
    run_verifiability,
    run_unambiguity,
]


def _build_annotated_content(project_docs_dir: str, project_slug: str) -> str:
    from app.services.doc_sharder import load_all_chapters
    all_ch = load_all_chapters("SRS", project_docs_dir, project_slug)
    parts = []
    has_content = False
    for key, data in all_ch.items():
        if not data.get("content"):
            continue
        has_content = True
        parts.append(f"<!-- CHAPTER:{key} -->\n<!-- PATH:{data['path']} -->\n{data['content']}\n<!-- END CHAPTER:{key} -->")
    if not has_content:
        return ""
    return "\n\n".join(parts)


async def _save_final_and_advance(
    websocket: WebSocket,
    current_content: str,
    project_slug: str,
    project_docs_dir: str,
    project_id: str,
    db,
    all_results: list,
    attempt: int = 1,
):
    from app.services.workflow_engine import WorkflowEngine
    from app.services.doc_sharder import load_all_chapters

    await websocket.send_json({"type": "progress", "content": "\n ✅ 全部4个子步骤检验通过！\n"})
    await websocket.send_json({"type": "progress", "content": "\n 保存最终通过的需求文档...\n"})

    try:
        version = await _get_next_version(project_docs_dir, project_slug)
        all_ch = load_all_chapters("SRS", project_docs_dir, project_slug)
        parts = [v["content"] for v in all_ch.values() if v.get("content")]
        combined = "\n\n".join(parts)
        save_path = os.path.join(project_docs_dir, f"{project_slug}_SRS_V{version}.md")
        with open(save_path, "w", encoding="utf-8") as f:
            f.write(combined)
    except Exception:
        version = await _get_next_version(project_docs_dir, project_slug)
        save_path = os.path.join(project_docs_dir, f"{project_slug}_SRS_V{version}.md")
        with open(save_path, "w", encoding="utf-8") as f:
            f.write(current_content)

    await websocket.send_json({
        "type": "progress",
        "content": f"\n 📦 最终交付版已保存至: {save_path}（各分片仍独立保存在对应文件）\n"
    })

    if db and project_id:
        await websocket.send_json({"type": "progress", "content": "\n 保存状态并推进到第4步...\n"})
        try:
            engine = WorkflowEngine(project_id, db)
            handover_path = ""
            handover_content = ""

            try:
                import glob as _glob
                handover_lines = [
                    "# Step3 → Step4 交接文档\n",
                    f"## 项目信息\n- 项目: {project_slug}",
                    f"- 最终 SRS 文档: {save_path}\n",
                    "## 4子步骤QA检验结果\n",
                ]
                for r in all_results:
                    key = r.get("key", "")
                    label = next((s["label"] for s in SUB_STEPS if s["key"] == key), key)
                    score = r.get("score", 100)
                    detail = (r.get("detail", "") or "")[:200]
                    handover_lines.append(f"- ✅ {label}（得分:{score}）: {detail}")
                handover_lines.append(
                    f"\n## 交接说明\n后荣已完成 Step3 全部4个子步骤的 QA 检验。\n"
                    f"后旺请基于以上 SRS 需求文档推进 Step4 架构设计。\n"
                )
                handover_content = "\n".join(handover_lines)

                pattern = os.path.join(project_docs_dir, f"{project_slug}_HANDOVER_S3_S4_V*.md")
                max_hv = 0
                for f in _glob.glob(pattern):
                    try:
                        v = int(os.path.basename(f).replace(f"{project_slug}_HANDOVER_S3_S4_V", "").replace(".md", ""))
                        max_hv = max(max_hv, v)
                    except ValueError:
                        continue
                hv = max_hv + 1
                handover_filename = f"{project_slug}_HANDOVER_S3_S4_V{hv}.md"
                os.makedirs(project_docs_dir, exist_ok=True)
                handover_path = os.path.join(project_docs_dir, handover_filename)
                with open(handover_path, "w", encoding="utf-8") as f:
                    f.write(handover_content)
                await websocket.send_json({
                    "type": "progress",
                    "content": f"\n 交接文档已保存至: {handover_path}\n"
                })
            except Exception:
                pass

            artifacts_payload = {
                "doc_content": current_content,
                "srs": current_content,
                "doc_path": save_path,
                "handover_path": handover_path,
                "handover_doc": handover_content,
                "qa_inspections": all_results,
                "qa_checked": True,
                "qa_sub_steps": [s["key"] for s in SUB_STEPS],
            }
            engine.complete_step(3, artifacts=artifacts_payload)
            engine.pass_qa(3)
            engine.save_step3_artifacts({
                "doc_content": current_content,
                "srs": current_content,
                "doc_path": save_path,
                "handover_path": handover_path,
                "handover_doc": handover_content,
                "qa_passed": True,
                "qa_checked": True,
                "qa_sub_steps": [s["key"] for s in SUB_STEPS],
            })
            await websocket.send_json({
                "type": "progress",
                "content": f"\n  全部检验通过！步骤已推进至第4步（后旺架构设计）\n"
            })
            await websocket.send_json({
                "type": "step_complete",
                "next_step": 4,
                "next_step_name": "后旺架构设计",
            })
        except Exception as e:
            logger.error(f"推进工作流失败: {e}", exc_info=True)
            await websocket.send_json({
                "type": "progress",
                "content": f"\n  推进工作流失败: {e}\n"
            })


async def _run_qa_loop(
    websocket: WebSocket,
    content: str,
    project_slug: str,
    docs_path: str,
    project_id: str = "",
    db=None,
    project_docs_dir: str = "",
):
    from app.services.doc_sharder import load_all_chapters

    if hasattr(websocket, '_current_payload'):
        raw = getattr(websocket, '_current_payload', None)
        index_path = ""
        if isinstance(raw, dict):
            index_path = raw.get("index_path", "") or ""
        elif hasattr(raw, 'get') and callable(raw.get):
            try:
                val = raw.get("index_path", "")
                index_path = str(val) if val and isinstance(val, str) else ""
            except Exception:
                index_path = ""
        else:
            index_path = ""
        if index_path and os.path.exists(index_path):
            try:
                all_ch = load_all_chapters("SRS", project_docs_dir, project_slug)
                parts = [v["content"] for v in all_ch.values() if v.get("content")]
                if parts:
                    content = "\n\n".join(parts)
                    await websocket.send_json({
                        "type": "progress",
                        "content": f"\n  从 {len(parts)} 个分片文件加载内容\n"
                    })
            except Exception as e:
                await websocket.send_json({
                    "type": "progress",
                    "content": f"\n  加载分片文件失败: {e}，使用原始内容\n"
                })

    current_content = content
    all_results = []

    checkpoint = _load_qa_checkpoint(project_id, db) if project_id and db else {}
    resume_step = checkpoint.get("step", 0)
    if resume_step > 0:
        all_results = list(checkpoint.get("results", []))
        if checkpoint.get("content"):
            current_content = checkpoint["content"]
        await websocket.send_json({
            "type": "progress",
            "content": f"\n ⏩ 检测到断点，从子步骤{resume_step + 1}恢复（已完成{resume_step}个步骤）\n"
        })

    for idx, sub_step in enumerate(SUB_STEPS):
        if idx < resume_step:
            continue

        if project_id and db:
            _save_qa_checkpoint(
                project_id, db,
                step=idx, attempt=1,
                results=all_results,
                content=current_content,
            )

        await websocket.send_json({
            "type": "sub_step_start",
            "data": {
                "step": sub_step["step"],
                "key": sub_step["key"],
                "label": sub_step["label"],
                "description": sub_step["description"],
                "total_steps": len(SUB_STEPS),
            }
        })

        runner = _SUB_RUNNERS[idx]
        logger.info(f"第3步QA: 开始子步骤{idx+1}/{len(SUB_STEPS)} {sub_step['label']}")
        passed, current_content, result = await runner(
            websocket, current_content, project_slug, project_docs_dir,
            project_id, db, all_results,
        )
        logger.info(f"第3步QA: 子步骤{idx+1}/{len(SUB_STEPS)} {sub_step['label']} 结果: passed={passed}, has_result={result is not None}")
        if result:
            all_results.append(result)

        if not passed:
            await websocket.send_json({
                "type": "progress",
                "content": f"\n  子步骤{sub_step['step']}【{sub_step['label']}】检验未通过，流程终止\n"
            })
            await websocket.close()
            return

    _clear_qa_checkpoint(project_id, db)
    await _save_final_and_advance(
        websocket, current_content, project_slug, project_docs_dir,
        project_id, db, all_results,
    )
    await websocket.close()
