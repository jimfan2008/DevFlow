import json
import os
import asyncio
import logging
import re as _re
from fastapi import APIRouter, WebSocket, WebSocketDisconnect, Query
from app.api.ws.auth import verify_token
from app.models.project import Project
from app.services.gateway_client import GatewayClient
from app.services.workflow_engine import WorkflowEngine
from app.services.doc_sharder import save_chapter, get_shard_config, load_all_chapters
from app.config import settings

logger = logging.getLogger(__name__)

router = APIRouter()

CHAPTER_MARKER_RE = _re.compile(
    r'<!--\s*CHAPTER:\s*([\w.-]+)\s*-->([\s\S]*?)(?=<!--\s*CHAPTER:|\Z)'
)

QUESTIONNAIRE_PROMPT = (
    "你是一个软件需求分析师（后兴），使用头脑风暴法进行需求调研。\n\n"
    "===== 任务 =====\n"
    "一次性生成10~20道选择题（HTML form格式），覆盖以下方面：\n"
    "1. 项目背景与业务目标（1~2题）\n"
    "2. 目标用户与用户特征（1~2题）\n"
    "3. 核心功能需求（3~5题）\n"
    "4. 非功能需求 — 性能、安全、可用性等（2~3题）\n"
    "5. 接口需求 — 外部集成、API对接（1~2题）\n"
    "6. 数据需求 — 数据模型、存储方式（1~2题）\n"
    "7. 约束条件 — 技术栈、预算、时间（1~2题）\n\n"
    "===== 格式要求 =====\n"
    "输出一个完整的HTML表单（用 ```html ... ``` 包裹）。\n"
    "每个问题使用 <div class=\"brain-q\" data-qid=\"q??\"> 包裹，data-qid 从 q01 开始严格递增。\n"
    "!!! 禁止生成任何内容重复的问题 !!! 每个问题的文本必须完全不同，覆盖不同方面。\n"
    "!!! 禁止生成任何选项雷同的问题 !!! 每个问题的选项必须针对该问题专门设计。\n"
    "检查清单（输出前逐一核对）：\n"
    "- 问题内容是否有两句以上意思相同或相近？→ 删除重复\n"
    "- 选项是否有两组以上雷同？→ 重新设计差异化选项\n"
    "- 不同 data-qid 的问题是否覆盖了不同方面？→ 每个方面的题目角度必须不同\n\n"
    "模板（q01 只是例子，实际编号必须按顺序递增）：\n"
    '<div class="brain-q" data-qid="q01">\n'
    '  <p class="brain-q-title">1. 问题标题</p>\n'
    '  <label class="brain-option"><input type="radio" name="q01" value="A"> A. 选项A</label>\n'
    '  <label class="brain-option"><input type="radio" name="q01" value="B"> B. 选项B</label>\n'
    '  <label class="brain-option"><input type="radio" name="q01" value="C"> C. 选项C</label>\n'
    "</div>\n\n"
    "data-qid 从 q01 开始严格递增（q01, q02, q03 ... q20），禁止跳号。每个问题提供 3~5 个选项。\n\n"
    "===== 后续流程 =====\n"
    "用户填写完问卷提交后，你将收到完整的答案（JSON格式）。\n"
    "届时你需要根据这些答案生成完整的软件需求规格说明书（SRS），使用以下格式：\n"
    "每个章节用 <!-- CHAPTER: key --> 和 <!-- CHAPTER: --> 包裹。\n"
    "章节划分：\n"
    "- overview: 项目概述（背景、目标、范围、术语表）\n"
    "- functional: 功能需求（按子功能点拆分为 func-auth, func-data, ...）\n"
    "- non_functional: 非功能需求\n"
    "- constraints: 约束条件\n"
    "- glossary: 术语表\n\n"
    "SRS 输出完毕后，再输出索引章节：\n"
    "<!-- CHAPTER: index -->\n"
    "# SRS 分片索引表\n"
    "| 分片名 | 内容摘要 |\n"
    "|--------|---------|\n"
    "| ... | ... |\n"
    "<!-- CHAPTER: -->\n\n"
    "生成SRS时只输出文档正文，不要包含分析/对话文字。\n"
    "禁止在章节内容中包含工作日志、文件路径、文件名、章节标记等任何非正文信息。"
)

SRS_GENERATION_PROMPT = (
    "你是一个软件需求分析师（后兴）。用户已完成了以下需求调研问卷：\n"
    "{answers_text}\n\n"
    "请根据以上答案，生成完整的软件需求规格说明书（SRS）。\n"
    "每个章节用 <!-- CHAPTER: key --> 包裹。章节内容必须是独立的Markdown片段。\n\n"
    "章节划分：\n"
    "- overview: 项目概述（背景、目标、范围、术语表）\n"
    "- functional: 功能需求（按子功能点动态拆分，如 func-auth、func-report 等，根据实际功能拆）\n"
    "- non_functional: 非功能需求\n"
    "- constraints: 约束条件\n"
    "- glossary: 术语表\n\n"
    "SRS 输出完毕后，再输出索引章节：\n"
    "<!-- CHAPTER: index -->\n"
    "# SRS 分片索引表\n"
    "| 分片名 | 内容摘要 |\n"
    "|--------|---------|\n"
    "| ... | ... |\n"
    "<!-- CHAPTER: -->\n\n"
    "=== 输出规范（严格遵守） ===\n"
    "1. 每个 <!-- CHAPTER: key --> 中的内容必须是纯粹的 Markdown 正文\n"
    "2. 禁止在章节内容中包含：工作日志、文件路径、文件名、分片名、章节标记\n"
    "3. 禁止在章节内容中包含任何说明文字（如「以下是xxx章节」「路径：xxx」等）\n"
    "4. 章节内容只包含需求文档的正式正文\n"
)


def _split_chapters(full_text: str) -> dict:
    chapters = {}
    for m in CHAPTER_MARKER_RE.finditer(full_text):
        key = m.group(1).strip()
        content = m.group(2).strip()
        if content:
            chapters[key] = content
    return chapters


def _extract_html(text: str) -> str:
    m = _re.search(r'```html\s*([\s\S]*?)```', text)
    if m:
        html = m.group(1).strip()
    else:
        html = text.strip()
    # 移除可能导致布局破坏的外层包裹标签
    html = _re.sub(r'</?html>|</?body>|</?head>', '', html, flags=_re.IGNORECASE)
    return html


def _load_refs_text(project_docs_dir: str) -> str:
    """从 docs/refs/ 加载参考文档，返回格式化文本"""
    refs_dir = os.path.join(project_docs_dir, "refs")
    if not os.path.isdir(refs_dir):
        return ""
    ref_parts = []
    for fname in sorted(os.listdir(refs_dir)):
        fpath = os.path.join(refs_dir, fname)
        if os.path.isfile(fpath):
            try:
                with open(fpath, "r", encoding="utf-8", errors="ignore") as fh:
                    content = fh.read()
                if content.strip():
                    ref_parts.append(f"【参考文档: {fname}】\n{content[:8000]}")
            except Exception:
                pass
    if ref_parts:
        return "\n\n---\n\n".join(ref_parts)
    return ""


def _save_sharded_srs(full_srs: str, project_slug: str, project_docs_dir: str) -> dict:
    chapters = _split_chapters(full_srs)
    if "index" in chapters:
        del chapters["index"]
    saved_files = {}
    for ch_key, ch_content in chapters.items():
        fpath = save_chapter("SRS", ch_key, ch_content, project_docs_dir, project_slug)
        saved_files[ch_key] = fpath
    if not chapters:
        default_configs = get_shard_config("SRS")
        for cfg in default_configs:
            save_chapter("SRS", cfg["key"], full_srs[:500], project_docs_dir, project_slug)
            saved_files[cfg["key"]] = os.path.join(
                project_docs_dir, f"{project_slug}_SRS_{cfg['key']}.md"
            )
    index_lines = [
        "# SRS 分片索引表",
        "",
        "| 分片名 | 文件路径 | 内容摘要 |",
        "|--------|---------|---------|",
    ]
    all_ch = load_all_chapters("SRS", project_docs_dir, project_slug)
    for key, data in all_ch.items():
        if data.get("content"):
            summary = data["content"][:80].replace("\n", " ") + "..."
            index_lines.append(f"| {key} | {data['path']} | {summary} |")
    index_content = "\n".join(index_lines)
    index_path = os.path.join(project_docs_dir, f"{project_slug}_SRS_INDEX.md")
    os.makedirs(project_docs_dir, exist_ok=True)
    with open(index_path, "w", encoding="utf-8") as f:
        f.write(index_content)
    return {
        "saved_files": saved_files,
        "index_path": index_path,
        "index_content": index_content,
        "chapter_count": len(chapters),
    }


@router.websocket("/step3/chat/{project_id}")
async def step3_chat_ws(websocket: WebSocket, project_id: str, token: str = Query(...)):
    """WebSocket for HouXing step3 — generates HTML questionnaire → collects answers → generates SRS."""
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
        if not project:
            await websocket.send_json({"type": "error", "message": "Project not found"})
            await websocket.close()
            return

        project_slug = project.slug if project.slug else project_id
        project_docs_dir = os.path.join(settings.PROJECTS_BASE_DIR, project_slug, "docs")
        os.makedirs(project_docs_dir, exist_ok=True)

        engine = WorkflowEngine(project_id, db)
        step2 = engine.get_step2_artifacts()
        core_goal = step2.get("confirmed_goal") or step2.get("core_goal") or ""

        # 从数据库恢复断点
        step3_artifacts = engine.get_step3_artifacts() or {}
        cp = step3_artifacts.get("chat_checkpoint") or {}
        _checkpoint_data = cp  # 保存断点数据，等 start 到达时使用
        questionnaire_generated = False  # 当前会话的生成状态

        while True:
            data = await websocket.receive_text()
            payload = json.loads(data)
            action = payload.get("action", "")

            # 第一阶段：检查断点
            if action in ("start", "questionnaire"):
                # 已经提交过问卷答案 → 不再需要问卷
                if _checkpoint_data.get("answers_submitted") or _checkpoint_data.get("srs_generated"):
                    questionnaire_generated = True
                    await websocket.send_json({"type": "done"})
                    continue

                # 问卷已生成但未提交 → 恢复缓存的问卷
                if _checkpoint_data.get("questionnaire_generated") and _checkpoint_data.get("questionnaire_html"):
                    questionnaire_generated = True
                    await websocket.send_json({
                        "type": "questionnaire",
                        "content": _checkpoint_data["questionnaire_html"],
                        "question_count": _checkpoint_data.get("question_count", 0),
                    })
                    continue

                if questionnaire_generated:
                    await websocket.send_json({"type": "done"})
                    continue
                questionnaire_generated = True
                refs_text = _load_refs_text(project_docs_dir)
                messages = []
                if core_goal:
                    messages.append({"role": "system", "content": f"[项目核心目标]\n{core_goal}"})
                sys_content = QUESTIONNAIRE_PROMPT
                if refs_text:
                    sys_content += f"\n\n用户上传了以下参考文档，请结合这些文档的内容来设计调研问题：\n\n{refs_text}"
                messages.append({"role": "system", "content": sys_content})
                messages.append({"role": "user", "content": "请生成需求调研问卷。"})

                try:
                    async def _generate():
                        client = GatewayClient(profile_name="houxing", timeout=300)
                        reply_chunks = []
                        async for chunk in client.chat_completions(messages=messages, stream=True):
                            if chunk.strip():
                                reply_chunks.append(chunk)
                        return "".join(reply_chunks)

                    full_reply = await asyncio.wait_for(_generate(), timeout=310)
                    if not full_reply.strip():
                        raise ValueError("houxing 返回空内容")
                    html_form = _extract_html(full_reply)
                    if not html_form:
                        html_form = full_reply

                    q_count = len(_re.findall(r'data-qid="q\d+"', html_form))

                    # 保存断点：问卷已生成
                    try:
                        engine.save_step3_artifacts({
                            "chat_checkpoint": {
                                "questionnaire_generated": True,
                                "questionnaire_html": html_form,
                                "question_count": q_count,
                            }
                        })
                    except Exception as cp_e:
                        logger.warning(f"保存问卷断点失败: {cp_e}")

                    await websocket.send_json({
                        "type": "questionnaire",
                        "content": html_form,
                        "question_count": q_count,
                    })
                except asyncio.TimeoutError:
                    logger.error("HouXing generate questionnaire timed out")
                    await websocket.send_json({"type": "error", "message": "后兴生成问卷超时（超过5分钟），请检查后兴Agent状态后重试"})
                except ConnectionError as e:
                    logger.error(f"HouXing gateway connection failed: {e}")
                    await websocket.send_json({"type": "error", "message": f"无法连接到后兴Agent：{e}"})
                except ValueError as e:
                    logger.error(f"HouXing generate questionnaire failed: {e}")
                    await websocket.send_json({"type": "error", "message": str(e)})
                except Exception as e:
                    logger.error(f"HouXing generate questionnaire failed: {e}", exc_info=True)
                    await websocket.send_json({"type": "error", "message": f"后兴生成问卷失败：{str(e)[:200]}"})
                continue

            # 第三阶段：用户对话（问卷阶段/SRS生成后均可）
            if action == "chat":
                user_message = payload.get("message", "").strip()
                history = payload.get("history", [])
                if not user_message:
                    await websocket.send_json({"type": "error", "message": "消息为空"})
                    continue

                # 判断SRS是否已生成（从分片文件判断）
                all_ch = load_all_chapters("SRS", project_docs_dir, project_slug)
                has_srs = any(v.get("content") for v in all_ch.values())

                messages = []
                if core_goal:
                    messages.append({"role": "system", "content": f"[项目核心目标]\n{core_goal}"})

                if has_srs:
                    srs_context_parts = []
                    for key, data in all_ch.items():
                        if data.get("content"):
                            srs_context_parts.append(
                                f"<!-- CHAPTER: {key} -->\n{data['content']}"
                            )
                    srs_context = "\n\n".join(srs_context_parts)
                    messages.append({"role": "system", "content": (
                        "你是一个软件需求分析师（后兴）。用户希望对已生成的SRS需求文档进行修改或补充。\n"
                        "请根据用户的要求修改文档。\n\n"
                        "当前SRS文档内容如下（用 <!-- CHAPTER: key --> 标记了各个章节分片）：\n"
                        f"{srs_context}\n\n"
                        "输出要求：\n"
                        "1. 如果用户要求修改，请输出修改后的完整章节内容，用 <!-- CHAPTER: key --> 包裹\n"
                        "2. 只修改用户指出的部分，其他章节保持不变\n"
                        "3. 如果用户只是询问问题，正常回答即可（不需要输出章节标记）\n"
                        "4. 如果输出章节内容，最后输出索引章节 <!-- CHAPTER: index -->"
                    )})
                else:
                    # 问卷阶段：加载参考文档作为上下文
                    refs_text = _load_refs_text(project_docs_dir)
                    sys = "你是一个软件需求分析师（后兴）。"
                    if refs_text:
                        sys += f"用户上传了以下参考文档，请结合这些文档内容回答用户的问题：\n\n{refs_text}\n\n"
                    sys += "请回答用户关于需求调研的问题。"
                    messages.append({"role": "system", "content": sys})

                messages.extend(history)
                messages.append({"role": "user", "content": user_message})

                try:
                    client = GatewayClient(profile_name="houxing", timeout=300)
                    reply_chunks = []
                    async for chunk in client.chat_completions(messages=messages, stream=True):
                        if chunk.strip():
                            reply_chunks.append(chunk)
                            await websocket.send_json({"type": "chunk", "content": chunk})

                    full_reply = "".join(reply_chunks)

                    # 检测章节标记 → 自动更新分片
                    chapters = _split_chapters(full_reply)
                    if chapters:
                        shard_result = _save_sharded_srs(full_reply, project_slug, project_docs_dir)
                        # 持久化分片索引到数据库
                        try:
                            engine.save_step3_artifacts({
                                "shard_index": shard_result.get("saved_files", {}),
                                "shard_index_path": shard_result.get("index_path", ""),
                                "shard_index_content": shard_result.get("index_content", ""),
                            })
                        except Exception as artifact_e:
                            logger.warning(f"保存分片索引到数据库失败: {artifact_e}")
                        await websocket.send_json({
                            "type": "shards_updated",
                            "data": shard_result,
                        })

                    await websocket.send_json({"type": "done"})
                except Exception as e:
                    logger.error(f"HouXing chat failed: {e}")
                    await websocket.send_json({"type": "error", "message": str(e)})
                continue

            # 第二阶段：接收答案，生成SRS
            if action == "submit_answers":
                answers = payload.get("answers", {})
                if not answers:
                    await websocket.send_json({"type": "error", "message": "答案为空"})
                    continue

                # 立即保存答案和提交状态到数据库（即使SRS生成失败也不丢失）
                answers_text = json.dumps(answers, ensure_ascii=False, indent=2)
                try:
                    engine.save_step3_artifacts({
                        "chat_checkpoint": {
                            "questionnaire_generated": True,
                            "answers_submitted": True,
                            "answers": answers,
                        }
                    })
                except Exception as cp_e:
                    logger.warning(f"保存问卷答案到数据库失败: {cp_e}")

                refs_text = _load_refs_text(project_docs_dir)

                messages = []
                if core_goal:
                    messages.append({"role": "system", "content": f"[项目核心目标]\n{core_goal}"})
                system_msg = "你是一个软件需求分析师（后兴）。根据用户填写的需求调研问卷生成SRS文档。"
                if refs_text:
                    system_msg += f"\n\n用户上传了以下参考文档，请结合这些文档内容生成SRS：\n\n{refs_text}"
                messages.append({"role": "system", "content": system_msg})
                messages.append({"role": "user", "content": SRS_GENERATION_PROMPT.format(answers_text=answers_text)})

                try:
                    client = GatewayClient(profile_name="houxing", timeout=600)
                    reply_chunks = []
                    async for chunk in client.chat_completions(messages=messages, stream=True):
                        if chunk.strip():
                            reply_chunks.append(chunk)
                            await websocket.send_json({"type": "chunk", "content": chunk})

                    full_reply = "".join(reply_chunks)

                    # 自动分片保存
                    chapters = _split_chapters(full_reply)
                    if chapters:
                        shard_result = _save_sharded_srs(full_reply, project_slug, project_docs_dir)
                        # 持久化分片索引 + SRS断点到数据库
                        try:
                            engine.save_step3_artifacts({
                                "shard_index": shard_result.get("saved_files", {}),
                                "shard_index_path": shard_result.get("index_path", ""),
                                "shard_index_content": shard_result.get("index_content", ""),
                                "chat_checkpoint": {
                                    "questionnaire_generated": True,
                                    "srs_generated": True,
                                }
                            })
                        except Exception as artifact_e:
                            logger.warning(f"保存分片索引到数据库失败: {artifact_e}")
                        await websocket.send_json({
                            "type": "shards_saved",
                            "data": shard_result,
                        })

                    await websocket.send_json({"type": "done"})
                except Exception as e:
                    logger.error(f"HouXing generate SRS failed: {e}")
                    await websocket.send_json({"type": "error", "message": str(e)})
                continue

            # 未知action
            await websocket.send_json({"type": "error", "message": f"Unknown action: {action}"})

    except WebSocketDisconnect:
        pass
    except Exception as e:
        logger.error(f"WebSocket error: {e}", exc_info=True)
        try:
            await websocket.send_json({"type": "error", "message": str(e)})
        except Exception:
            pass
    finally:
        db.close()
