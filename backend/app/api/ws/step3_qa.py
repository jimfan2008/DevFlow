import json as _json
import asyncio
import os
import re as _re
import logging
from fastapi import APIRouter, WebSocket, WebSocketDisconnect, Query

from app.api.ws.auth import verify_token
from app.models.project import Project
from app.services.gateway_client import GatewayClient
from app.config import settings

logger = logging.getLogger(__name__)

router = APIRouter()


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

                await _run_qa_loop(websocket, content, project_slug, docs_path, project_id, db, project_docs_dir)

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
    """Scan docs folder to find the next version number."""
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


def _extract_json_array(text: str):
    """从 LLM 输出中提取 JSON 数组。处理 markdown 代码块及前导/后置文字。"""
    text = text.strip()
    # 尝试整体解析
    try:
        parsed = _json.loads(text)
        if isinstance(parsed, list):
            return parsed
    except Exception:
        pass

    # 尝试提取 ```json ... ``` 中的内容
    m = _re.search(r'```(?:json)?\s*(\[.*?\])\s*```', text, _re.DOTALL)
    if m:
        try:
            parsed = _json.loads(m.group(1))
            if isinstance(parsed, list):
                return parsed
        except Exception:
            pass

    # 尝试匹配从头到尾的完整 JSON 数组（首 [ 到尾 ]）
    start = text.find('[')
    if start >= 0:
        end = text.rfind(']')
        if end > start:
            candidate = text[start:end + 1]
            try:
                parsed = _json.loads(candidate)
                if isinstance(parsed, list):
                    return parsed
            except Exception:
                pass

    return []


async def _call_hourong(websocket, prompt, timeout=180):
    """Call hourong (LLM) and return full reply text."""
    client = GatewayClient(profile_name="hourong", timeout=timeout)
    collected = []
    try:
        async for chunk in client.chat_completions(
            messages=[{"role": "user", "content": prompt}],
            stream=True, max_tokens=8192,
        ):
            if chunk.strip():
                await websocket.send_json({"type": "progress", "content": chunk})
                collected.append(chunk)
    except Exception as e:
        logger.error(f"hourong call failed: {e}")
        await websocket.send_json({"type": "progress", "content": f"\n⚠️ hourong调用失败: {e}\n"})
        return ""
    reply = "".join(collected).strip()
    logger.info(f"hourong reply (first 500 chars): {reply[:500]}")
    return reply


async def _run_qa_loop(
    websocket: WebSocket,
    content: str,
    project_slug: str,
    docs_path: str,
    project_id: str = "",
    db=None,
    project_docs_dir: str = "",
):
    """hourong inspects → if fail, messages houxing → houxing fixes & saves → hourong re-inspects → loop"""
    from app.api.workflow import SRS_INSPECTION_DIMENSIONS
    from app.services.workflow_engine import WorkflowEngine

    MAX_FIX_ATTEMPTS = 10
    current_content = content
    last_save_path = ""

    def _save_document(doc_content: str) -> str:
        version = 1
        if last_save_path:
            import re as _re
            m = _re.search(r'_V(\d+)\.md$', last_save_path)
            if m:
                version = int(m.group(1)) + 1
        else:
            import glob as _glob
            pattern = os.path.join(project_docs_dir, f"{project_slug}_SRS_V*.md")
            max_ver = 0
            for f in _glob.glob(pattern):
                try:
                    v = int(os.path.basename(f).replace(f"{project_slug}_SRS_V", "").replace(".md", ""))
                    max_ver = max(max_ver, v)
                except ValueError:
                    continue
            version = max_ver + 1

        filename = f"{project_slug}_SRS_V{version}.md"
        os.makedirs(project_docs_dir, exist_ok=True)
        save_path = os.path.join(project_docs_dir, filename)
        with open(save_path, "w", encoding="utf-8") as f:
            f.write(doc_content)
        return save_path

    for attempt in range(1, MAX_FIX_ATTEMPTS + 1):
        await websocket.send_json({
            "type": "progress",
            "content": f"\n{'='*40}\n📋 第 {attempt} 轮检验\n{'='*40}\n"
        })
        await asyncio.sleep(0.2)

        doc_source = f"文件: {last_save_path}\n\n" if last_save_path else ""
        dim_labels = "、".join(d["label"] for d in SRS_INSPECTION_DIMENSIONS)
        inspect_prompt = (
            "你是一个专业的软件需求QA检验员（后荣）。\n\n"
            f"{doc_source}=== 需求文档 ===\n"
            f"{current_content}\n\n"
            "=== 检验维度（必须逐项检验，不可跳过任一维度）===\n"
            f"本次QA检验严格按以下 4 个维度逐项检验：{dim_labels}\n\n"
            + "\n".join(f"  {i+1}. {d['label']}（{d['description']}）"
                        for i, d in enumerate(SRS_INSPECTION_DIMENSIONS)) + "\n\n"
            "你必须依次对上述全部 4 个维度给出通过/不通过判定及具体检验意见。\n"
            "禁止跳过任何维度，禁止合并多个维度。\n\n"
            "只输出一个 JSON 数组，不要有任何其他文字：\n"
            "[\n"
            + ",\n".join(
                f'  {{"key": "{d["key"]}", "passed": true/false, "detail": "具体检验意见"}}'
                for d in SRS_INSPECTION_DIMENSIONS
            ) + "\n]"
        )

        await websocket.send_json({"type": "progress", "content": "\n🔍 后荣开始检验需求文档...\n"})

        # 带补集的 hourong 调用：解析失败则重试一次
        for hr_attempt in range(2):
            reply = await _call_hourong(websocket, inspect_prompt)
            parsed = _extract_json_array(reply)

            # 检查是否包含全部 4 个维度
            missing = [d["key"] for d in SRS_INSPECTION_DIMENSIONS
                       if not any(r.get("key") == d["key"] for r in parsed)]
            if not missing:
                break
            if hr_attempt == 0:
                await websocket.send_json({
                    "type": "progress",
                    "content": f"\n⚠️ 后荣未返回全部维度（缺: {', '.join(missing)}），重新请求...\n"
                })

        results = []
        for dim in SRS_INSPECTION_DIMENSIONS:
            matched = next((r for r in parsed if r.get("key") == dim["key"]), None)
            results.append({
                "key": dim["key"],
                "label": dim["label"],
                "passed": bool(matched.get("passed", False)) if matched else False,
                "detail": matched.get("detail", "未检出") if matched else "后荣未返回该维度结果",
            })

        all_passed = all(r["passed"] for r in results)
        failed_items = [r for r in results if not r["passed"]]

        if all_passed:
            await websocket.send_json({"type": "progress", "content": "\n✅ 所有检验项目均通过！\n"})
            await websocket.send_json({"type": "result", "dimensions": results, "all_passed": True})

            await websocket.send_json({"type": "progress", "content": "\n💾 保存最终通过的需求文档...\n"})
            try:
                save_path = _save_document(current_content)
                await websocket.send_json({
                    "type": "progress",
                    "content": f"\n✅ 最终文档已保存至: {save_path}\n"
                })
            except Exception as e:
                await websocket.send_json({
                    "type": "progress",
                    "content": f"\n⚠️ 保存最终文档失败: {e}\n"
                })

            if db and project_id:
                await websocket.send_json({"type": "progress", "content": "\n⏩ 检验通过，保存状态并推进到下一步...\n"})
                try:
                    engine = WorkflowEngine(project_id, db)

                    # 生成 Step3→Step4 交接文档（同时存入 DB 和文件）
                    handover_path = ""
                    handover_content = ""
                    try:
                        import glob as _glob
                        passed_items = [r for r in results if r["passed"]]
                        handover_content = (
                            f"# Step3 → Step4 交接文档\n\n"
                            f"## 项目信息\n"
                            f"- 项目: {project_slug}\n"
                            f"- QA 检验轮次: 第 {attempt} 轮\n"
                            f"- 最终 SRS 文档: {save_path}\n\n"
                            f"## QA 检验结果\n"
                            f"- 总体结果: ✅ 全部通过\n"
                            f"- 检验维度 ({len(passed_items)}/{len(results)}):\n"
                        )
                        for r in results:
                            status = "✅" if r["passed"] else "❌"
                            handover_content += f"  - {status} {r['label']}: {r['detail']}\n"
                        handover_content += (
                            f"\n## 交接说明\n"
                            f"后荣（HouRong）已完成 Step3 需求文档的 QA 检验，所有维度均通过。\n"
                            f"后旺（HouWang）请基于以上 SRS 需求文档推进 Step4 架构设计。\n"
                        )

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
                            "content": f"\n📋 Step3→Step4 交接文档已保存至: {handover_path}\n"
                        })
                    except Exception as e:
                        logger.warning(f"生成交接文档文件失败: {e}")

                    engine.save_step3_artifacts({
                        "doc_content": current_content,
                        "srs": current_content,
                        "doc_path": save_path,
                        "handover_path": handover_path,
                        "handover_doc": handover_content,
                        "qa_passed": True,
                        "qa_checked": True,
                    })
                    artifacts_payload = {
                        "doc_content": current_content,
                        "srs": current_content,
                        "doc_path": save_path,
                        "handover_path": handover_path,
                        "handover_doc": handover_content,
                        "qa_inspections": results,
                        "qa_passed": True,
                        "qa_checked": True,
                    }
                    engine.complete_step(3, artifacts=artifacts_payload)
                    engine.pass_qa(3)
                    await websocket.send_json({
                        "type": "progress",
                        "content": f"\n✅ 合格需求文档已保存至: {save_path}\n✅ 步骤已推进！可以进入第4步（后旺架构设计）\n"
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
                        "content": f"\n⚠️ 推进工作流失败: {e}\n"
                    })
            await websocket.close()
            return

        await websocket.send_json({"type": "result", "dimensions": results, "all_passed": False})
        await websocket.send_json({
            "type": "progress",
            "content": f"\n⚠️ 发现 {len(failed_items)} 项不合格\n📤 后荣将检验报告发送给后兴，请求修改...\n"
        })
        await asyncio.sleep(0.3)

        inspection_json = _json.dumps(results, ensure_ascii=False, indent=2)
        await websocket.send_json({
            "type": "progress",
            "content": f"\n📋 检验报告（JSON格式）:\n{inspection_json}\n\n"
        })

        version = await _get_next_version(project_docs_dir, project_slug)
        filename = f"{project_slug}_SRS_V{version}.md"
        save_path = os.path.join(project_docs_dir, filename)

        edit_prompt = (
            "你是需求分析专家后兴（HouXing）。\n\n"
            "后荣（HouRong）发来了以下检验报告：\n\n"
            f"{inspection_json}\n\n"
            "以下维度未通过检验，需要修改：\n"
            + "\n".join(f"- {item['label']}: {item['detail']}" for item in failed_items) + "\n\n"
            "当前需求文档：\n\n"
            f"{current_content}\n\n"
            "请分析上述不合格项，对文档进行修改。\n"
            "要求：\n"
            "1. 只修改不合格项涉及的内容，禁止扩大修改\n"
            "2. 禁止添加新功能、新需求\n"
            "3. 必须基于当前需求文档进行修改，修改后的文本必须保持标准需求文档格式\n"
            f"4. **修改完成后，将完整的修改后的 Markdown 需求文档保存到: {save_path}**\n"
            "5. **禁止将推理内容保存到需求文档中**\n"
        )

        await websocket.send_json({
            "type": "progress",
            "content": f"\n🔧 后兴分析不合格项，生成完整修改后文档...\n💾 修改后将自动保存到: {save_path}\n"
        })

        houxing = GatewayClient(profile_name="houxing", timeout=1200)
        edit_chunks = []
        async for chunk in houxing.chat_completions(
            messages=[
                {"role": "user", "content": edit_prompt},
            ],
            stream=True, max_tokens=16000,
        ):
            if chunk.strip():
                await websocket.send_json({"type": "progress", "content": chunk})
                edit_chunks.append(chunk)

        try:
            with open(save_path, "r", encoding="utf-8") as f:
                new_content = f.read()
        except Exception:
            new_content = "".join(edit_chunks).strip()

        await websocket.send_json({
            "type": "progress",
            "content": (
                f"\n📨 后兴给后荣发送消息：\n"
                f"   「后荣，我已根据你的检验报告修改了不合格项，"
                f"最新完整文档已保存至 {save_path}，请针对此文档进行复检。」\n"
            )
        })
        await asyncio.sleep(0.3)

        current_content = new_content
        last_save_path = save_path

    await websocket.send_json({
        "type": "progress",
        "content": f"\n❌ 经过 {MAX_FIX_ATTEMPTS} 轮修复仍未全部通过，请手动修改\n"
    })
