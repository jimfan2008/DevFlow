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
    last_defects_detail: str = "",
    last_fixed_paths: str = "",
) -> bool:
    from app.services.workflow_engine import WorkflowEngine
    from app.models.workflow_step import WorkflowStep
    import time
    cp = {
        "step": step,
        "attempt": attempt,
        "results": results or [],
        "content": content,
        "last_save_path": last_save_path,
        "last_defects_detail": last_defects_detail,
        "last_fixed_paths": last_fixed_paths,
    }
    for retry in range(3):
        try:
            engine = WorkflowEngine(project_id, db)
            engine.save_step3_artifacts({"qa_checkpoint": cp})
            # 立即验证回读
            verify = db.query(WorkflowStep).filter(
                WorkflowStep.project_id == project_id,
                WorkflowStep.step_number == 3,
            ).first()
            if verify and verify.output_artifacts:
                saved = verify.output_artifacts.get("qa_checkpoint", {})
                if isinstance(saved, dict) and saved.get("step") == step:
                    return True
                logger.warning(f"QA断点回读验证不一致: 期望step={step}, 实际={saved.get('step')}")
            else:
                logger.warning("QA断点回读: 找不到step3行或output_artifacts为空")
        except Exception as e:
            logger.error(f"保存QA断点失败(第{retry+1}次): {e}", exc_info=True)
        time.sleep(0.5)
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
                docs_path = payload.get("docs_path", "")

                # 检查是否全部已通过：禁止重新检验
                cp = _load_qa_checkpoint(project_id, db)
                if cp and cp.get("results"):
                    all_passed = all(r.get("passed", False) for r in cp.get("results", []))
                    passed_keys = {r["key"] for r in cp["results"] if r.get("passed", False)}
                    if all_passed and len(passed_keys) >= len(SUB_STEPS):
                        await websocket.send_json({
                            "type": "progress",
                            "content": "\n ⚠️ 全部4个子步骤已检验通过，无需重新检验。正在推进到下一步...\n"
                        })
                        await _save_final_and_advance(
                            websocket, cp.get("content", ""), project_slug,
                            project_docs_dir, project_id, db, cp["results"]
                        )
                        break

                # 以 checkpoint 中保存的内容为准（已通过步骤可能修改了文档）
                checkpoint_content = cp.get("content", "") if cp else ""
                content = payload.get("content", "")
                if checkpoint_content and len(checkpoint_content.strip()) >= 20:
                    content = checkpoint_content
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
            "score": int(first.get("score", first.get("得分", 0))),
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


async def _call_hourong(websocket, prompt, timeout=1800, system_message=None, prev_reply=None, follow_up=None, save_dir=None):
    from .step3_qa_1 import delegate_task, _fix_json_llm
    import os, json, tempfile

    if not save_dir:
        save_dir = tempfile.gettempdir()
    os.makedirs(save_dir, exist_ok=True)

    report_filename = f"hourong_report_{os.urandom(4).hex()}.json"
    save_path = os.path.join(save_dir, report_filename)

    combined_prompt = prompt
    if system_message:
        combined_prompt = f"【角色说明】\n{system_message}\n\n【检验内容】\n{prompt}"
    if prev_reply:
        combined_prompt += f"\n\n【上一轮回复】\n{prev_reply}"
    if follow_up:
        combined_prompt += f"\n\n【格式要求】\n{follow_up}"

    task = json.dumps({"save_path": save_path, "task": combined_prompt}, ensure_ascii=False)

    logger.info(f"hourong 委托子agent检验，保存路径: {save_path}")
    results = await delegate_task(
        tasks=[task],
        wait_all=True, timeout=timeout,
        max_concurrent=1, websocket=websocket,
        profile_name="hourong",
    )

    result = results[0] if results else ""
    if result.startswith("[子Agent"):
        logger.error(f"hourong子agent调用失败: {result}")
        await websocket.send_json({"type": "progress", "content": f"\n⚠️ hourong子agent调用失败: {result}\n"})
        return ""

    if result and os.path.exists(result):
        try:
            with open(result, "r", encoding="utf-8") as f:
                report_content = f.read()
            try:
                parsed = json.loads(report_content)
            except json.JSONDecodeError:
                from .step3_qa_1 import _fix_json_llm
                fixed = _fix_json_llm(report_content)
                try:
                    parsed = json.loads(fixed)
                    with open(result, "w", encoding="utf-8") as f:
                        f.write(fixed)
                    report_content = fixed
                    logger.info(f"hourong 子agent报告通过JSON修复成功: {result}")
                except json.JSONDecodeError:
                    logger.warning(f"hourong 子Agent JSON 修复失败，返回空触发调用方重试: {result}")
                    await websocket.send_json({"type": "progress", "content": f"\n⚠️ hourong子Agent返回内容无法解析为JSON，要求重新输出\n"})
                    return ""
            if not isinstance(parsed, dict) or not any(k in parsed for k in ("维度", "report_type", "判定结果", "评定", "dimension_key", "dimension_label")):
                logger.warning(f"hourong 子agent返回的报告缺少必要字段: {result}")
                await websocket.send_json({"type": "progress", "content": f"\n⚠️ hourong 子agent返回的JSON缺少必要字段，要求重新输出\n"})
                return ""
            logger.info(f"hourong 子agent检验报告已保存: {result}")
            await websocket.send_json({"type": "progress", "content": result})
            return result
        except (json.JSONDecodeError, Exception) as e:
            logger.error(f"hourong 子agent返回的报告不是合法JSON: {result}, {e}")
            snippet = report_content[:300] if isinstance(report_content, str) else str(e)
            logger.warning(f"hourong 子agent报告内容(前300): {repr(snippet)}")
            await websocket.send_json({"type": "progress", "content": f"\n⚠️ hourong 子agent返回的报告不是合法JSON，要求重新输出\n"})
            return ""

    logger.warning(f"hourong 子agent返回路径无效: {result}")
    return ""


def _load_qa_report(report_path: str) -> dict:
    if not report_path or not os.path.exists(report_path):
        logger.warning(f"检验报告文件不存在: {report_path}")
        return {}
    try:
        with open(report_path, "r", encoding="utf-8") as f:
            data = _json.loads(f.read())
        if isinstance(data, dict):
            return data
        if isinstance(data, list):
            return {"results": data}
        return {}
    except Exception as e:
        logger.warning(f"读取检验报告失败: {report_path}, {e}")
        return {}


def _report_to_result(report: dict, dim_key: str = "", dim_label: str = "") -> dict:
    if not report:
        return {}
    score = report.get("得分") or report.get("score") or 0
    passed_str = report.get("判定结果") or report.get("passed", True)
    if isinstance(passed_str, str):
        passed = passed_str in ("通过", "合格")
    else:
        passed = bool(passed_str)
    return {
        "key": report.get("dimension_key") or report.get("维度") or dim_key,
        "label": report.get("dimension_label") or report.get("维度") or dim_label,
        "score": int(score),
        "passed": passed,
        "detail": report.get("summary") or report.get("detail") or "",
        "deduction": "" if passed else f"得分{score}，满分100，扣{100 - int(score)}分",
    }


async def _inspect_via_subagent(
    prompt: str,
    save_dir: str = "",
    max_retries: int = 3,
) -> str:
    """通过 delegate_task 子 agent 调用 hourong 检验，返回原始响应文本。

    所有 workflow 中的 _inspect_* 函数统一使用此接口替代直接 GatewayClient 调用。
    save_dir 指定检验报告保存目录（应指向项目 qa_reports 目录），
    子 agent 返回报告文件的完整路径，调用方可通过该路径追踪检验记录。
    """
    from .step3_qa_1 import delegate_task
    import os, json, tempfile, asyncio

    if not save_dir:
        save_dir = tempfile.gettempdir()
    os.makedirs(save_dir, exist_ok=True)

    last_result = ""
    for attempt in range(1, max_retries + 1):
        report_path = os.path.join(save_dir, f"hourong_subagent_{os.urandom(4).hex()}.json")
        task = json.dumps({"save_path": report_path, "task": prompt}, ensure_ascii=False)

        results = await delegate_task(
            tasks=[task],
            wait_all=True, timeout=180,
            max_concurrent=1,
            profile_name="hourong",
        )

        result = results[0] if results else ""
        last_result = result

        if result and not result.startswith("[子Agent"):
            # result 应为报告文件的完整路径，等待文件就绪后读取
            file_path = result.strip()
            for _ in range(5):
                if os.path.exists(file_path):
                    try:
                        with open(file_path, "r", encoding="utf-8") as f:
                            content = f.read().strip()
                        if content and len(content) > 10:
                            logger.info(f"hourong检验报告已保存到: {file_path}")
                            return content
                    except Exception:
                        pass
                await asyncio.sleep(0.5)

        if attempt >= max_retries:
            logger.error(f"hourong子agent检验失败({max_retries}次): {last_result}")
            return ""

    return ""


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
                    score = r.get("score", 0)
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
                "qa_passed": True,
                "qa_checked": True,
                "qa_sub_steps": [s["key"] for s in SUB_STEPS],
            }
            engine.complete_step(3, artifacts=artifacts_payload)
            engine.pass_qa(3)
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

    # 根据 all_results 双重保护：已完成且通过的子步骤绝不重跑
    passed_step_keys = {r["key"] for r in all_results if r.get("passed", False)}

    # 如果全部4个子步骤已通过，禁止重新检验，直接推进
    if len(passed_step_keys) >= len(SUB_STEPS):
        await websocket.send_json({
            "type": "progress",
            "content": "\n ✅ 全部4个子步骤已通过，跳过重复检验，直接推进到第4步\n"
        })
        _clear_qa_checkpoint(project_id, db)
        await _save_final_and_advance(websocket, current_content, project_slug, project_docs_dir, project_id, db, all_results)
        await websocket.close()
        return

    for idx, sub_step in enumerate(SUB_STEPS):
        if idx < resume_step:
            continue

        sk = sub_step["key"]
        if sk in passed_step_keys:
            await websocket.send_json({
                "type": "progress",
                "content": f"\n ⏭️ 子步骤{sub_step['step']}【{sub_step['label']}】已在之前通过，跳过\n"
            })
            continue

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

        # 每步完成后立即保存综合状态（无论通过/失败）
        # 注意：不依赖 _load_qa_checkpoint，直接用当前数据保存
        if project_id and db:
            save_ok = _save_qa_checkpoint(
                project_id, db,
                step=idx + 1 if passed else idx,
                attempt=1,
                results=list(all_results or []),
                content=current_content or "",
            )
            if not save_ok:
                logger.error(f"子步骤{idx+1}【{sub_step['label']}】检查点保存失败")

        if not passed:
            await websocket.send_json({
                "type": "progress",
                "content": f"\n  子步骤{sub_step['step']}【{sub_step['label']}】检验未通过，流程终止\n"
            })
            await websocket.close()
            return

        if project_id and db:
            passed_step_keys.add(sk)
            await websocket.send_json({
                "type": "progress",
                "content": f"\n ✅ 子步骤{idx+1}【{sub_step['label']}】已通过，状态已保存，推进到下一步\n"
            })

    _clear_qa_checkpoint(project_id, db)
    await _save_final_and_advance(
        websocket, current_content, project_slug, project_docs_dir,
        project_id, db, all_results,
    )
    await websocket.close()
