import asyncio
import json as _json
import logging
import os

logger = logging.getLogger(__name__)

from app.services.gateway_client import GatewayClient

SUB_STEP = {
    "step": 1,
    "key": "completeness",
    "label": "完整性",
    "description": "需求文档是否覆盖了所有必要的功能和非功能需求",
}

HOURONG_SYSTEM_MSG = (
    "你是后荣（HouRong），是软件需求 QA 检验员。\n"
    "本次你的职责是**只检验「完整性」这一个维度**，检验需求文档是否覆盖了所有必要的功能和非功能需求。\n"
    "\n"
    "===== ⚠️ 强制JSON格式（系统将拒绝任何非JSON输出）=====\n"
    "你**只能**输出一个严格合法的JSON对象，禁止包含任何其他字符（包括分析过程、思考过程、说明、注释、代码块标记 ```json 等）。\n"
    "输出内容的第1个字符必须是 {，最后1个字符必须是 }。如果输出包含任何非JSON内容，系统将直接拒绝整个回复。\n"
    "规则：\n"
    "- 所有字符串必须使用双引号 \"，禁止单引号\n"
    "- 禁止末尾逗号（如 \"key\": \"value\", } 中的逗号）\n"
    "- 禁止注释（// 或 /* */）\n"
    "- 禁止 ```json、``` 等任何markdown代码块标记\n"
    "- 布尔值必须使用 true/false（小写），数字不使用引号\n"
    "- 必须能通过 Python json.loads() 直接解析\n\n"
    "===== 输出JSON格式（必须严格遵守）=====\n"
    '{\n'
    '  "维度": "完整性",\n'
    '  "判定结果": "通过/未通过",\n'
    '  "得分": <0-100>,\n'
    '  "不合格章节": [\n'
    '    {\n'
    '      "分片文件": "<!-- PATH:... -->中的完整文件路径",\n'
    '      "不合格项数": <N>,\n'
    '      "项": [\n'
    '        {"理由": "不合格的具体原因", "证据": "（必须有 [chapter:key]）", "改善方向": "如何修改"}\n'
    '      ]\n'
    '    }\n'
    '  ]\n'
    '}\n'
    "如果没有不合格项，\"不合格章节\" 请设为 []。\n"
    "每个不合格项的「证据」字段必须以 [chapter:key] 开头，指明该问题所属的分片。\n"
    "「改善方向」必须明确指导后兴如何修改。\n\n"
    "===== 收敛性规则（必须严格执行）=====\n"
    "1. 首次检验按标准逐项检查，发现问题如实报告。\n"
    "2. 复检（第2轮起）必须对照上一轮的不合格项清单逐项确认修复情况：\n"
    "   - 已修复且修复质量合格 → 不再列为不合格项，不扣分。\n"
    "   - 未修复或修复不充分 → 继续指出，但已在上一轮扣过的分数不再重复扣。\n"
    "   - 仅本轮新发现的不合格项才是本轮扣分依据。\n"
    "3. 收敛目标：每轮不合格项应减少，得分应上升。若所有不合格项均已修复，得分必须为100、评定必须为「通过」。\n"
    "4. 严禁将上一轮已指出的不合格项在本轮重复报告（除非确认确实未修复）。\n"
    "后续Agent将严格根据你的检验报告只修改不合格项，禁止扩大修改范围。\n\n"
    "===== 分片标识要求（重要）=====\n"
    "需求文档内容中已用 <!-- CHAPTER:key --> 标记划分了各个分片（章节），\n"
    "并在每个分片开头标注了 <!-- PATH:完整文件路径 -->。\n"
    "「不合格章节」中每个条目的「分片文件」字段，必须填写对应分片的 <!-- PATH:... --> 中的完整文件路径，而不是 shard_key。\n"
    "请严格执行。\n"
    "对于每个不合格项，其「证据」字段中必须包含该不合格项所在分片的 key，"
    "格式为 [chapter:key]，例如 [chapter:overview] 或 [chapter:functional]。\n"
    "如果同一不合格项涉及多个分片，列出所有相关分片key：例如 [chapter:overview][chapter:functional]。\n"
    "这是后续修复Agent定位修改范围的核心依据，请严格执行。"
)


async def run_completeness(
    websocket,
    current_content: str,
    project_slug: str,
    project_docs_dir: str,
    project_id: str = "",
    db=None,
    all_results: list = None,
) -> tuple:
    from .step3_qa import (
        _load_qa_checkpoint, _save_qa_checkpoint,
        _build_annotated_content, _call_hourong,
        _load_qa_report, _report_to_result,
        _get_next_version, logger,
        SUB_STEPS,
    )
    from app.services.doc_sharder import (
        load_all_chapters, get_shard_config, ShardRetriever,
    )

    MAX_FIX_ATTEMPTS = 5
    dim_key = SUB_STEP["key"]
    dim_label = SUB_STEP["label"]
    dim_desc = SUB_STEP["description"]
    content = current_content
    last_save_path = ""
    project_tmp_dir = os.path.join(os.path.dirname(project_docs_dir), "tmp")

    # 防重入检查：如果 all_results 中已有本维度的通过记录，直接返回
    if all_results:
        for r in all_results:
            if r.get("key") == dim_key and r.get("passed", False):
                await websocket.send_json({
                    "type": "progress",
                    "content": f"\n ⏭️ 子步骤{SUB_STEP['step']}【{dim_label}】已在之前通过，跳过\n"
                })
                return True, content, r

    resume_attempt = 1
    exhausted_resume = False
    last_defects_detail = ""
    last_fixed_paths = ""
    if project_id and db:
        checkpoint = _load_qa_checkpoint(project_id, db)
        if checkpoint.get("exhausted") and checkpoint.get("step") == SUB_STEP["step"] - 1:
            exhausted_resume = True
            if checkpoint.get("content"):
                content = checkpoint["content"]
            if checkpoint.get("last_save_path"):
                last_save_path = checkpoint["last_save_path"]
            if checkpoint.get("last_defects_detail"):
                last_defects_detail = checkpoint["last_defects_detail"]
            if checkpoint.get("last_fixed_paths"):
                last_fixed_paths = checkpoint["last_fixed_paths"]
            await websocket.send_json({
                "type": "progress",
                "content": f"\n ⏩ 检测到上次5轮未通过的保存状态，从保存的分片文件和检验报告继续复检\n"
            })
        elif checkpoint.get("step") == SUB_STEP["step"] - 1:
            resume_attempt = checkpoint.get("attempt", 1)
            if checkpoint.get("content"):
                content = checkpoint["content"]
            if checkpoint.get("last_save_path"):
                last_save_path = checkpoint["last_save_path"]
            if checkpoint.get("last_defects_detail"):
                last_defects_detail = checkpoint["last_defects_detail"]
            if checkpoint.get("last_fixed_paths"):
                last_fixed_paths = checkpoint["last_fixed_paths"]
            if resume_attempt > 1:
                await websocket.send_json({
                    "type": "progress",
                    "content": f"\n ⏩ 子步骤{SUB_STEP['step']}从第{resume_attempt}轮检验恢复\n"
                })

    for attempt in range(1, MAX_FIX_ATTEMPTS + 1):
        sep = "=" * 30
        await websocket.send_json({
            "type": "progress",
            "content": f"\n{sep}\n 子步骤{SUB_STEP['step']} {dim_label} - 第{attempt}轮检验\n{sep}\n"
        })
        await asyncio.sleep(0.2)

        doc_source = f"文件: {last_save_path}\n\n" if last_save_path else ""

        annotated = _build_annotated_content(project_docs_dir, project_slug)

        if attempt == 1:
            display_content = annotated if annotated else content
            chapter_note = (
                "\n\n===== 分片标记说明 =====\n"
                "以上需求文档中已使用 <!-- CHAPTER:key --> 划分了各个分片（章节）。\n"
                "每个不合格项的「证据」字段必须标注所属分片key，格式 [chapter:key]，"
                "例如 [chapter:overview] 或 [chapter:functional]。这是定位修改范围的核心依据。\n"
            ) if annotated else ""

            inspect_prompt = (
                doc_source + "=== 需求文档 ===\n"
                + display_content + chapter_note + "\n\n"
                + "=== 检验维度 ===\n"
                + f"本次只检验【{dim_label}】这一项。\n"
                + f"检验标准：{dim_desc}\n\n"
                + "请严格按此标准给出通过/不通过判定。\n\n"
                + "评分规则：\n"
                + "- 起始100分。\n"
                + "- 每发现一个缺陷扣减相应分数（轻微扣5-10分，一般扣15-20分，严重扣25-30分）。得分>=90则通过。\n"
            )
        else:
            modified_content_parts = []
            if last_fixed_paths:
                for fp_str in last_fixed_paths.split("\n"):
                    fp = fp_str.strip()
                    if fp and os.path.exists(fp):
                        try:
                            with open(fp, "r", encoding="utf-8") as f:
                                c = f.read()
                            if c.strip():
                                modified_content_parts.append(c)
                        except Exception:
                            pass
            modified_content = "\n\n".join(modified_content_parts) if modified_content_parts else "(无具体修改的分片文件记录)"
            prev_report = raw_reply_content if raw_reply_content else (last_defects_detail or "(无上一轮检验记录)")

            inspect_prompt = (
                f"=== 第{attempt}轮复检 – 仅验证上一轮不合格项是否已修复 ===\n"
                + f"本次只检验【{dim_label}】这一个维度。\n\n"
                + "⚠️ 禁止扩大检验范围！仅检查上一轮报告中列出的不合格项是否已修复，不要检查新内容。\n\n"
                + "===== 上一轮检验报告（不合格项清单）=====\n"
                + f"{prev_report}\n\n"
                + "===== 后兴修改后的分片内容（仅需检查这些分片）=====\n"
                + f"{modified_content}\n\n"
                + "===== 复检规则（严格执行）=====\n"
                + "1. 逐项检查上一轮报告中的每个不合格项是否已修复。\n"
                + "2. 已修复且合格 → 不计入本轮不合格项，不扣分。\n"
                + "3. 未修复或修复不充分 → 继续指出，但已在上一轮扣过的分数不再重复扣。\n"
                + "4. ⛔ 仅检查上一轮报告中列出的不合格项！禁止检查新内容，禁止提出新问题。\n"
                + "5. 如果上一轮所有不合格项均已修复 → 得分100，判定为「通过」，不合格章节为[]\n"
                + "6. 收敛目标：不合格项必须逐轮减少。若全部修复，直接判定通过。\n"
            )

        inspect_prompt += (
            "\n\n===== ⚠️ 强制JSON格式（系统将拒绝任何非JSON输出）=====\n"
            + "你**只能**输出一个严格合法的JSON对象（不是数组），禁止包含任何其他文字。\n"
            + "输出内容的第1个字符必须是 {，最后1个字符必须是 }。如果输出包含任何非JSON内容，系统将直接拒绝整个回复。\n"
            + "规则：\n"
            + "- 所有字符串必须使用双引号\"\n"
            + "- 禁止末尾逗号\n"
            + "- 禁止注释（// 或 /* */）\n"
            + "- 禁止 ```json、``` 等任何代码块标记\n"
            + "- 输出的第一和最后一个字符必须是 { 和 }\n"
            + "- 必须能通过 Python json.loads() 直接解析\n\n"
            + "必须使用的JSON格式：\n"
            + '{"维度": "' + dim_label + '", '
            + '"判定结果": "通过/未通过", '
            + '"得分": <0-100>,\n'
            + ' "不合格章节": [\n'
            + '    {"分片文件": "<shard_key>", "不合格项数": <N>, '
            + '"项": [{"理由": "不合格描述", "证据": "（必须有 [chapter:key]）", "改善方向": "如何修改"}]}\n'
            + '  ]}\n'
            + '如果没有不合格项，"不合格章节" 请设为 []。\n'
            + '注意：每个不合格项的「证据」字段必须以 [chapter:key] 开头。\n'
            + '「理由」明确指出不合格的原因，「改善方向」必须明确指导修复方法。'
        )

        await websocket.send_json({
            "type": "progress",
            "content": f"\n 后荣检验【{dim_label}】...\n"
        })

        report_path = ""
        raw_reply_content = ""
        result = None
        result_data = {}
        for hr_attempt in range(6):
            if hr_attempt == 0:
                report_path = await _call_hourong(
                    websocket, inspect_prompt,
                    system_message=HOURONG_SYSTEM_MSG,
                    save_dir=project_docs_dir,
                )
            else:
                report_path = await _call_hourong(
                    websocket, inspect_prompt,
                    system_message=HOURONG_SYSTEM_MSG,
                    prev_reply=raw_reply_content,
                    follow_up="⚠️ 强制JSON格式：你只能输出一个严格合法的JSON对象，禁止任何其他文字。输出的第1个字符必须是 {，最后1个字符必须是 }。禁止 ```json、``` 等代码块标记。禁止注释。必须能通过 Python json.loads() 直接解析。",
                    save_dir=project_docs_dir,
                )

            if not report_path:
                logger.warning(f"hourong返回空路径(第{hr_attempt+1}次)")
                await websocket.send_json({
                    "type": "progress",
                    "content": f"\n⚠️ hourong第{hr_attempt+1}次返回空结果，要求重新检验\n"
                })
                continue

            try:
                with open(report_path, "r", encoding="utf-8") as f:
                    raw_reply_content = f.read()
            except Exception:
                raw_reply_content = ""

            report = _load_qa_report(report_path)
            if report and isinstance(report, dict):
                has_dim = any(k in report for k in ("维度", "dimension_key", "dimension_label"))
                has_result = any(k in report for k in ("得分", "score", "判定结果", "passed", "不合格章节", "defect_chapters"))
                if has_dim and has_result:
                    result = _report_to_result(report, dim_key, dim_label)
                    if not result.get("key") and report:
                        result["key"] = dim_key
                    break
            logger.warning(f"hourong返回格式异常(第{hr_attempt+1}次): {raw_reply_content[:200]}")
            await websocket.send_json({
                "type": "progress",
                "content": f"\n⚠️ hourong第{hr_attempt+1}次返回格式不合法，要求重新输出标准JSON\n"
            })

        if not result:
            if raw_reply_content:
                try:
                    result_data = json.loads(raw_reply_content)
                except Exception:
                    result_data = {}
                if not result_data:
                    try:
                        fixed = _fix_json_llm(raw_reply_content)
                        result_data = json.loads(fixed)
                    except Exception:
                        import re as _re
                        result_data = {}
                        score_m = _re.search(r'["\']?(?:得分|score)["\']?\s*[:：]\s*(\d+)', raw_reply_content)
                        if score_m:
                            result_data["得分"] = int(score_m.group(1))
                        result_m = _re.search(r'["\']?(?:判定结果|passed)["\']?\s*[:：]\s*["\']?(通过|未通过|合格|不合格|true|false)["\']?', raw_reply_content)
                        if result_m:
                            v = result_m.group(1)
                            result_data["判定结果"] = "通过" if v in ("通过", "合格", "true") else "未通过"
                        dim_m = _re.search(r'["\']?(?:维度|label|dimension_label)["\']?\s*[:：]\s*["\']?([^"\']+)["\']?', raw_reply_content)
                        if dim_m:
                            result_data["维度"] = dim_m.group(1).strip()
            if result_data and isinstance(result_data, dict):
                dim_label = result_data.get("dimension_label") or result_data.get("维度") or dim_label
                score = int(result_data.get("score", result_data.get("得分", 0)))
                passed = bool(result_data.get("passed", result_data.get("判定结果", "合格") in ("通过", "合格")))
                defects = result_data.get("defect_chapters", result_data.get("不合格章节", []))
                detail_parts = []
                if isinstance(defects, list):
                    for ch in defects:
                        sf = ch.get("shard_file", ch.get("分片文件", ""))
                        items = ch.get("defects", ch.get("项", []))
                        if isinstance(items, list) and items:
                            shard_lines = []
                            for df in items:
                                reason = df.get("reason", df.get("理由", ""))
                                evidence = df.get("evidence", df.get("证据", ""))
                                fix_dir = df.get("fix_direction", df.get("改善方向", ""))
                                shard_lines.append(f"不合格的理由：{reason}；证据：{evidence}；改善方向：{fix_dir}")
                            detail_parts.append(f"分片文件{sf}：{len(items)}项不合格，{'；'.join(shard_lines)}")
                detail = "\n\n".join(detail_parts) if detail_parts else result_data.get("summary", "")
                from .step3_qa import _DIMENSION_LABEL_TO_KEY
                result = {
                    "key": _DIMENSION_LABEL_TO_KEY.get(dim_label, dim_label),
                    "label": dim_label,
                    "score": score,
                    "passed": passed,
                    "detail": detail,
                    "deduction": "" if passed else f"得分{score}，满分100，扣{100 - score}分",
                }

            if not result:
                await websocket.send_json({
                    "type": "error",
                    "message": f"后荣未能返回 {dim_label} 的合法检验结果，请检查后荣 agent 状态"
                })
                return False, content, None

        dim_score = int(result.get("score", 0))
        result_passed = result.get("passed", True)
        passed = result_passed and (dim_score >= 90)
        detail = result.get("detail", "")
        last_defects_detail = detail

        if passed:
            completed_results = list(all_results or [])
            completed_results.append({
                "key": dim_key, "label": dim_label,
                "score": dim_score, "passed": True, "detail": detail,
            })

            if project_id and db:
                cp_ok = _save_qa_checkpoint(
                    project_id, db,
                    step=SUB_STEP["step"], attempt=attempt,
                    results=completed_results,
                    content=content, last_save_path=last_save_path,
                )
                if not cp_ok:
                    await websocket.send_json({
                        "type": "error",
                        "message": f"断点保存失败，无法通过子步骤{SUB_STEP['step']}【{dim_label}】",
                    })
                    return False, content, None

            await websocket.send_json({
                "type": "sub_step_passed",
                "data": {
                    "step": SUB_STEP["step"],
                    "key": dim_key,
                    "label": dim_label,
                    "score": dim_score,
                    "detail": detail,
                    "next_step": SUB_STEP["step"] + 1,
                    "total_steps": len(SUB_STEPS),
                }
            })
            await websocket.send_json({
                "type": "progress",
                "content": f"\n ✅ 子步骤{SUB_STEP['step']}【{dim_label}】检验通过！（得分：{dim_score}）\n"
            })
            return True, content, result

        await websocket.send_json({
            "type": "progress",
            "content": f"\n ❌ 子步骤{SUB_STEP['step']}【{dim_label}】未通过（得分：{dim_score}）\n"
        })

        all_ch = load_all_chapters("SRS", project_docs_dir, project_slug)

        # 文件路径 → shard_key 反向映射（hourong 输出的「分片文件」是完整路径）
        path_to_key = {}
        for ch_key, ch_data in all_ch.items():
            fp = ch_data.get("path", "")
            if fp:
                path_to_key[fp] = ch_key

        # 从 hourong 检验报告提取分片缺陷映射（支持标准格式和旧格式）
        shard_fix_map = {}
        try:
            raw_for_fix = _json.loads(raw_reply_content) if raw_reply_content else {}
            if isinstance(raw_for_fix, dict):
                chapters = raw_for_fix.get("defect_chapters", raw_for_fix.get("不合格章节", []))
                for ch_entry in chapters if isinstance(chapters, list) else []:
                    sk_or_path = ch_entry.get("shard_file", ch_entry.get("分片文件", ""))
                    items = ch_entry.get("defects", ch_entry.get("项", []))
                    if not sk_or_path or not isinstance(items, list):
                        continue
                    sk = path_to_key.get(sk_or_path, sk_or_path)
                    shard_fix_map[sk] = items
        except Exception:
            pass

        failed_chapter_keys = set(shard_fix_map.keys())

        if not failed_chapter_keys:
            detail_lower = detail.lower()
            for ch_key, ch_data in all_ch.items():
                title = ch_data.get("title", "")
                if title.lower() in detail_lower or ch_key.lower() in detail_lower:
                    failed_chapter_keys.add(ch_key)

        if not failed_chapter_keys:
            srs_config = get_shard_config("SRS")
            for ch in srs_config:
                if dim_label in ch["title"]:
                    failed_chapter_keys.add(ch["key"])

        if not failed_chapter_keys:
            failed_chapter_keys = {ch["key"] for ch in get_shard_config("SRS")}

        srs_config = get_shard_config("SRS")
        defects_per_shard = {}
        for sk in failed_chapter_keys:
            defects = shard_fix_map.get(sk, [])
            if defects:
                mapped = []
                for df in defects:
                    mapped.append({
                        "问题": df.get("理由", ""),
                        "修改方向": df.get("改善方向", ""),
                        "证据": df.get("证据", ""),
                    })
                defects_per_shard[sk] = mapped
            else:
                defects_per_shard[sk] = [{"问题": "该分片内容存在不合格项", "修改方向": "请根据检验意见修改", "证据": ""}]

        failed_shards_info = []
        for sk in sorted(failed_chapter_keys):
            shard_cfg = next((c for c in srs_config if c["key"] == sk), {})
            shard_defects = defects_per_shard.get(sk, [{"问题": "该分片内容存在不合格项", "修改方向": "请根据检验意见修改", "证据": ""}])
            failed_shards_info.append({
                "key": sk,
                "title": shard_cfg.get("title", sk),
                "defects": shard_defects,
            })

        passed_label = "通过" if dim_score >= 90 else "未通过"
        report_lines = [f"检验维度：{dim_label}", f"判定结果：{passed_label}", f"得分：{dim_score}分"]
        if not (dim_score >= 90):
            report_lines.append("不合格章节：")
            for fs in failed_shards_info:
                sh_key = fs.get("key", "unknown")
                ch_data = all_ch.get(sh_key, {})
                full_path = ch_data.get("path", sh_key)
                defects = fs.get("defects", [])
                if defects:
                    shard_defect_lines = []
                    for df in defects:
                        reason = df.get("问题") or df.get("描述") or "未说明"
                        evidence = df.get("证据") or ""
                        fix_dir = df.get("修改方向") or ""
                        shard_defect_lines.append(
                            f"不合格的理由：{reason}；证据：{evidence}；改善方向：{fix_dir}"
                        )
                    report_lines.append(
                        f"    分片文件{full_path}：{len(defects)}项不合格，{'；'.join(shard_defect_lines)}"
                    )
                else:
                    report_lines.append(f"    分片文件{full_path}：存在不合格项")
        shard_file_defects_report = "\n".join(report_lines)

        await websocket.send_json({
            "type": "sub_step_failed",
            "data": {
                "step": SUB_STEP["step"],
                "key": dim_key,
                "label": dim_label,
                "score": dim_score,
                "detail": detail,
                "shard_file_defects": shard_file_defects_report,
                "attempt": attempt,
                "failed_shards": failed_shards_info,
            }
        })

        await asyncio.sleep(0.3)
        await websocket.send_json({
            "type": "progress",
            "content": f"\n 后荣检验报告：\n{raw_reply_content}\n\n"
        })

        if project_id and db:
            _save_qa_checkpoint(
                project_id, db,
                step=SUB_STEP["step"] - 1, attempt=attempt,
                results=list(all_results or []),
                content=content, last_save_path=last_save_path,
                last_defects_detail=last_defects_detail,
                last_fixed_paths=last_fixed_paths,
            )

        version = await _get_next_version(project_docs_dir, project_slug)
        failed_summary = f"- {dim_label}（得分:{dim_score}）: {detail[:600]}"

        await websocket.send_json({
            "type": "progress",
            "content": f"  识别出 {len(failed_chapter_keys)} 个不合格分片: {', '.join(sorted(failed_chapter_keys))}\n"
        })

        await websocket.send_json({
            "type": "progress",
            "content": f"  🚀 调度houxing为 {len(failed_chapter_keys)} 个分片统一生成修复任务（并行分派至最多10个子Agent）...\n"
        })

        all_tasks = await houxing_plan_tasks(
            detail=raw_reply_content, all_ch=all_ch,
            project_docs_dir=project_docs_dir, project_slug=project_slug,
            report_path=report_path, tmp_dir=project_tmp_dir,
            defect_keys=failed_chapter_keys,
        )

        merged = {}
        for t in all_tasks:
            sk = t.get("chapter", "")
            if not sk:
                continue
            if sk in merged:
                existing = merged[sk]
                p = t.get("问题", "")
                f = t.get("改善方向", "")
                if p and p not in existing.get("问题", ""):
                    existing["问题"] += "\n" + p
                if f and f not in existing.get("改善方向", ""):
                    existing["改善方向"] += "\n" + f
            else:
                merged[sk] = dict(t)
        all_tasks = list(merged.values())

        if not all_tasks:
            await websocket.send_json({
                "type": "progress",
                "content": "  ⚠️ 后兴未能生成任何修复任务\n"
            })
            return False, content, result

        await websocket.send_json({
            "type": "progress",
            "content": f"  📋 后兴输出 {len(all_tasks)} 条修复指令:\n" +
                "\n".join(f"    {i+1}. [{t.get('chapter','?')}] {t.get('问题','')[:80]}"
                         for i, t in enumerate(all_tasks)) + "\n"
        })

        ctx_map = {}
        full_tasks = []
        for t in all_tasks:
            sk = t.get("chapter", "")
            ch_data = all_ch.get(sk, {})
            ctx = f"分片文件: {ch_data.get('path', sk)}\n\n当前内容:\n{ch_data.get('content', '')[:4000]}"
            ctx_map[sk] = ctx
            full_tasks.append(f"{_json.dumps(t, ensure_ascii=False)}\n\n上下文:\n{ctx}")

        await websocket.send_json({
            "type": "progress",
            "content": f"  🚀 delegate_task 并行 {len(full_tasks)} 个子Agent（max_concurrent=10）...\n"
        })

        sub_results = await delegate_task(
            tasks=full_tasks, wait_all=True, timeout=1800, max_concurrent=10, websocket=websocket,
            tmp_dir=project_tmp_dir,
        )

        await websocket.send_json({
            "type": "progress",
            "content": f"  ✅ {len(full_tasks)} 个子Agent并行修复完成\n"
        })

        fixed_shard_paths = []
        for t, result_str in zip(all_tasks, sub_results):
            sk = t.get("chapter", "")
            shard_path = all_ch.get(sk, {}).get("path", "")

            # 子Agent 返回异常或超时 → 重试
            if not result_str or result_str.startswith("[子Agent异常]") or result_str.startswith("[子Agent超时]") or result_str.startswith("[子Agent无法完成]"):
                error_detail = result_str if result_str else "无返回"
                await websocket.send_json({
                    "type": "progress",
                    "content": f"  ⚠️ 子Agent返回异常 [{sk}]: {error_detail[:100]}，开始重试\n"
                })
                success = False
                for retry in range(3):
                    retry_ctx = ctx_map.get(sk, "")
                    retry_task = _build_retry_task(t, retry_ctx, retry, reason=f"上一次失败原因: {error_detail}")
                    retry_results = await delegate_task(
                        tasks=[retry_task],
                        wait_all=True, timeout=1800, max_concurrent=1, websocket=websocket,
                        tmp_dir=project_tmp_dir,
                    )
                    result_str = retry_results[0] if retry_results else ""
                    if result_str and not result_str.startswith("[子Agent异常]") and not result_str.startswith("[子Agent超时]") and not result_str.startswith("[子Agent无法完成]"):
                        valid, vreason, _ = _validate_shard_content(_resolve_result(result_str), sk)
                        if valid:
                            success = True
                            break
                        await websocket.send_json({
                            "type": "progress",
                            "content": f"  ⚠️ 子Agent第{retry+1}次重试内容验证失败 [{sk}]: {vreason}\n"
                        })
                    else:
                        await websocket.send_json({
                            "type": "progress",
                            "content": f"  ⚠️ 子Agent第{retry+1}次重试仍异常 [{sk}]\n"
                        })
                    # 清理临时文件（原始正式文件不碰）
                    if result_str and result_str.endswith('.tmp') and os.path.exists(result_str):
                        os.remove(result_str)
                if not success:
                    await websocket.send_json({
                        "type": "progress",
                        "content": f"  ❌ 子Agent重试3次仍无法生成有效内容，跳过 [{sk}]\n"
                    })
                    continue

            # 正常结果 → 验证内容质量
            valid, vreason, _ = _validate_shard_content(_resolve_result(result_str), sk)
            if not valid:
                await websocket.send_json({
                    "type": "progress",
                    "content": f"  ⚠️ 子Agent返回内容验证失败 [{sk}]: {vreason}，重新生成\n"
                })
                for retry in range(3):
                    retry_ctx = ctx_map.get(sk, "")
                    retry_task = _build_retry_task(t, retry_ctx, retry, reason=vreason)
                    retry_results = await delegate_task(
                        tasks=[retry_task],
                        wait_all=True, timeout=1800, max_concurrent=1, websocket=websocket,
                        tmp_dir=project_tmp_dir,
                    )
                    result_str = retry_results[0] if retry_results else ""
                    if result_str and not result_str.startswith("[子Agent异常]") and not result_str.startswith("[子Agent超时]") and not result_str.startswith("[子Agent无法完成]"):
                        valid2, vreason2, _ = _validate_shard_content(_resolve_result(result_str), sk)
                        if valid2:
                            break
                        await websocket.send_json({
                            "type": "progress",
                            "content": f"  ⚠️ 子Agent第{retry+1}次重试内容验证失败 [{sk}]: {vreason2}\n"
                        })
                    else:
                        await websocket.send_json({
                            "type": "progress",
                            "content": f"  ⚠️ 子Agent第{retry+1}次重试仍缺少 chapter 标记 [{sk}]\n"
                        })
                    # 清理临时文件（原始正式文件不碰）
                    if result_str and result_str.endswith('.tmp') and os.path.exists(result_str):
                        os.remove(result_str)
                else:
                    if result_str and result_str.endswith('.tmp') and os.path.exists(result_str):
                        os.remove(result_str)
                    await websocket.send_json({
                        "type": "progress",
                        "content": f"  ❌ 子Agent重试3次仍无法生成有效内容，跳过 [{sk}]\n"
                    })
                    continue

            # 验证通过：临时文件 → 正式文件（原子重命名，不触碰原有文件）
            if result_str and result_str.endswith('.tmp') and shard_path:
                if os.path.exists(result_str):
                    os.rename(result_str, shard_path)
            elif result_str and result_str.endswith('.tmp') and os.path.exists(result_str):
                os.remove(result_str)

            if shard_path:
                fixed_shard_paths.append(shard_path)
            await websocket.send_json({
                "type": "progress",
                "content": f"  ✅ 分片 [{sk}] 已修复并保存（{shard_path}）\n"
            })

        await websocket.send_json({
            "type": "progress",
            "content": f"  ✅ {len(fixed_shard_paths)} 个分片修复完成\n"
        })

        await websocket.send_json({
            "type": "progress",
            "content": f"  ✅ 全部 {len(failed_chapter_keys)} 个不合格分片并行修复完成，已分别保存到对应分片文件\n"
        })

        all_ch = load_all_chapters("SRS", project_docs_dir, project_slug)
        parts = [v["content"] for v in all_ch.values() if v.get("content")]
        content = "\n\n".join(parts)

        # 立即更新分片索引表
        index_lines = [
            "# SRS 分片索引表",
            "",
            "| 分片名 | 文件路径 | 内容摘要 |",
            "|--------|---------|---------|",
        ]
        for key, data in all_ch.items():
            if data.get("content"):
                summary = data["content"][:80].replace("\n", " ") + "..."
                index_lines.append(f"| {key} | {data['path']} | {summary} |")
        index_content = "\n".join(index_lines)
        index_path = os.path.join(project_docs_dir, f"{project_slug}_SRS_INDEX.md")
        os.makedirs(project_docs_dir, exist_ok=True)
        with open(index_path, "w", encoding="utf-8") as f:
            f.write(index_content)

        save_path = project_docs_dir
        last_save_path = save_path
        fixed_paths_str = "\n".join(fixed_shard_paths) if fixed_shard_paths else ""
        last_fixed_paths = fixed_paths_str

        if project_id and db:
            _save_qa_checkpoint(
                project_id, db,
                step=SUB_STEP["step"] - 1, attempt=attempt + 1,
                results=list(all_results or []),
                content=content, last_save_path=last_save_path,
                last_defects_detail=last_defects_detail,
                last_fixed_paths=last_fixed_paths,
            )

        await websocket.send_json({
            "type": "progress",
            "content": f"\n 后兴已将修复后的文档保存至：\n{fixed_paths_str}\n\n分片索引表已更新：{index_path}\n请后荣针对以上文件和最新的分片索引表复检【{dim_label}】。\n"
        })
        await asyncio.sleep(0.3)

    await websocket.send_json({
        "type": "progress",
        "content": f"\n  子步骤{SUB_STEP['step']}【{dim_label}】经过 {MAX_FIX_ATTEMPTS} 轮修复仍未通过，已保存当前状态\n"
    })
    if project_id and db:
        _save_qa_checkpoint(
            project_id, db,
                step=SUB_STEP["step"] - 1, attempt=MAX_FIX_ATTEMPTS,
            results=list(all_results or []),
            content=content, last_save_path=last_save_path,
            last_defects_detail=last_defects_detail,
            last_fixed_paths=last_fixed_paths,
        )
        cp = _load_qa_checkpoint(project_id, db)
        cp["exhausted"] = True
        from app.services.workflow_engine import WorkflowEngine
        engine = WorkflowEngine(project_id, db)
        engine.save_step3_artifacts({"qa_checkpoint": cp})
    return False, content, result


class HermesRuntime:
    def __init__(self, tmp_dir: str = ""):
        self._gateway = None
        self.tmp_dir = tmp_dir

    async def load_profile(self, profile_name: str):
        self._gateway = GatewayClient(profile_name=profile_name, timeout=600)

    async def chat(self, prompt: str, max_tokens: int = 2000) -> str:
        chunks = []
        async for chunk in self._gateway.chat_completions(
            messages=[{"role": "user", "content": prompt}],
            stream=False, max_tokens=max_tokens,
        ):
            if chunk.strip():
                chunks.append(chunk)
        reply = "".join(chunks).strip()
        return reply

    async def shutdown(self):
        self._gateway = None


def _resolve_result(result_str: str) -> str:
    if result_str and not result_str.startswith("[子Agent") and os.path.exists(result_str):
        try:
            with open(result_str, "r", encoding="utf-8") as f:
                return f.read()
        except Exception:
            return result_str
    return result_str


async def delegate_task(
    tasks: list,
    wait_all: bool = True,
    timeout: int = 1800,
    max_concurrent: int = 10,
    websocket=None,
    profile_name: str = "houxing",
    tmp_dir: str = "",
) -> list:
    sem = asyncio.Semaphore(max_concurrent)
    task_timeout = min(timeout, 1800)
    shared_client = GatewayClient(profile_name=profile_name, timeout=task_timeout)

    async def _run_one(task_desc: str) -> str:
        import json as _j
        import os
        import re as _re2
        save_path = ""
        task_info = task_desc
        is_inspection = profile_name == "hourong"
        try:
            start = task_desc.find('{')
            end = task_desc.rfind('}')
            if start != -1 and end != -1:
                parsed = _j.loads(task_desc[start:end+1])
                if isinstance(parsed, dict):
                    if is_inspection:
                        save_path = parsed.get("save_path", "")
                        task_info = parsed.get("task", task_desc)
                    else:
                        path = parsed.get("分片文件文件", "")
                        chapter = parsed.get("chapter", "")
                        problem = parsed.get("问题", "")
                        fix_dir = parsed.get("改善方向", "")
                        retry_reason = parsed.get("重试原因", "")
                        save_path = path
                        task_info = f"分片文件: {path}\n章节: {chapter}\n问题: {problem}\n改善方向: {fix_dir}"
                        if retry_reason:
                            task_info += f"\n\n⚠️ 上一次重试失败原因:\n{retry_reason}"
                        # 从 task_desc 中提取当前分片内容并拼入 prompt
                        ctx_match = _re2.search(r'\n当前内容:\n(.+?)(?:\n=====|\Z)', task_desc, _re2.DOTALL)
                        if ctx_match:
                            shard_content = ctx_match.group(1).strip()[:4000]
                            task_info += f"\n\n===== 当前分片内容 =====\n{shard_content}"
        except Exception:
            pass
        if is_inspection:
            prompt = f"{task_info}"
        else:
            prompt = (
                "你是一个文档修复子Agent。任务指令是一个JSON对象，只读取JSON字段中的内容，忽略所有非JSON的文字。\n"
                f"===== 修复任务 =====\n{task_info}\n\n"
                "===== 输出格式（严格遵守）=====\n"
                '只输出一个JSON对象，格式：{"content": "修改后的完整文档正文"}\n'
                "禁止输出任何非JSON文字、思考过程、或代码块标记 ```json/```。\n\n"
                "===== content 字段内容要求（严格遵守）=====\n"
                "1. content 的**第1个字符**必须是 \"<!--\"，紧接着是原始的 CHAPTER 标记（例如 <!-- CHAPTER:overview -->），然后是换行。\n"
                "2. 紧接着必须是原始的 <!-- PATH:完整文件路径 --> 标记（如果原分片有的话）。\n"
                "3. **紧接着必须有一个 markdown 标题行（以 # 开头）**，例如 `# 概述`。内容必须包含至少一个 `# ` 标题。\n"
                "4. 标题行和分节结构必须保留，原有的大纲不会改变。\n"
                "5. 只修改不合格项涉及的部分，其他所有段落逐字保留原文，一字不改。\n"
                "6. 最终正文（不含标记）至少200字，禁止敷衍成一句空话。\n"
                "7. 禁止输出重复的段落、乱码、测试占位符。\n"
                "8. 禁止在 content 开头添加除 chapter/path 标记和标题以外的任何文字。\n"
                "如果无法遵循以上要求，请返回 {\"error\": \"无法完成\"} 而不是伪造内容。\n"
            )
        async with sem:
            try:
                mt = 8192 if is_inspection else 4000
                result = await asyncio.wait_for(
                    _do_subagent_call(shared_client, prompt, websocket, max_tokens=mt, is_inspection=is_inspection, tmp_dir=tmp_dir),
                    timeout=task_timeout,
                )
                if result and not result.startswith("[子Agent"):
                    if save_path:
                        if not is_inspection:
                            valid, reason, cleaned = _validate_shard_content(result, chapter)
                            if not valid:
                                return f"[子Agent异常] 内容验证失败: {reason}"
                            result = cleaned
                        try:
                            tmp_path = save_path + ".tmp"
                            os.makedirs(os.path.dirname(save_path), exist_ok=True)
                            with open(tmp_path, "w", encoding="utf-8") as f:
                                f.write(result)
                        except Exception as e:
                            return f"[子Agent异常] 保存临时文件失败: {str(e)}"
                        if is_inspection:
                            os.replace(tmp_path, save_path)
                        if not is_inspection:
                            try:
                                with open(tmp_path, "r", encoding="utf-8") as f:
                                    read_back = f.read()
                                if read_back != result:
                                    if os.path.exists(tmp_path):
                                        os.remove(tmp_path)
                                    return "[子Agent异常] 回读内容不一致，文件可能损坏"
                                if read_back.strip() == "\n":
                                    if os.path.exists(tmp_path):
                                        os.remove(tmp_path)
                                    return "[子Agent异常] 保存的内容为空"
                            except Exception as e:
                                return f"[子Agent异常] 回读验证失败: {str(e)}"
                    if is_inspection:
                        if save_path and os.path.exists(save_path):
                            return save_path
                        return "[子Agent异常] 检验报告保存失败"
                    if save_path:
                        return tmp_path
                    return result
                elif is_inspection:
                    return "[子Agent异常] 子Agent返回无效结果"
                return result
            except asyncio.TimeoutError:
                return "[子Agent超时]"
            except Exception as e:
                return f"[子Agent异常] {str(e)}"

    async def _do_subagent_call(client: GatewayClient, prompt: str, ws, max_tokens: int = 4000, is_inspection: bool = False, tmp_dir: str = "") -> str:
        import os
        messages = []
        if is_inspection:
            # 角色定义已在 user prompt 的 HOURONG_SYSTEM_MSG 中，此处不重复以防冲突
            pass
        else:
            messages.append({"role": "system", "content": "你是一个需求文档修复专家。强制要求：只输出一个严格合法的JSON对象 {\"content\": \"...\"}，禁止任何非JSON文字。content 必须以 <!-- CHAPTER:key --> 开头，紧接着 `# ` markdown标题，保留原有结构，只改不合格项。如无法完成请输出 {\"error\": \"无法完成\"}。"})
        messages.append({"role": "user", "content": prompt})
        chunks = []
        async for chunk in client.chat_completions(
            messages=messages,
            stream=True, max_tokens=max_tokens,
        ):
            if chunk.strip():
                chunks.append(chunk)
        raw = "".join(chunks).strip()
        result = _clean_output(raw, is_inspection=is_inspection)
        base = tmp_dir if tmp_dir else "/tmp"
        os.makedirs(base, exist_ok=True)
        filepath = os.path.join(base, f"agent_{os.urandom(4).hex()}.json")
        with open(filepath, "w", encoding="utf-8") as f:
            f.write(raw)
        return result

    coros = [_run_one(t) for t in tasks]
    results = await asyncio.gather(*coros, return_exceptions=True)
    return [r if isinstance(r, str) else f"[子Agent异常] {str(r)}" for r in results]


async def houxing_plan_tasks(detail: str, all_ch: dict, project_docs_dir: str, project_slug: str, report_path: str = "", tmp_dir: str = "", defect_keys: set = None) -> list:
    """后兴读取hourong报告，为所有不合格分片生成修复任务。一次调用返回全部任务。"""
    if defect_keys is None:
        defect_keys = set()
    if report_path and os.path.exists(report_path):
        try:
            with open(report_path, "r", encoding="utf-8") as f:
                detail = f.read()
        except Exception:
            pass

    shard_lines = []
    for sk, data in all_ch.items():
        if sk in defect_keys and data.get("content"):
            fp = data.get("path", sk)
            shard_lines.append(f"  [分片: {sk}] 文件: {fp}")
    shard_summary = "\n".join(shard_lines)

    runtime = HermesRuntime(tmp_dir=tmp_dir)
    await runtime.load_profile("houxing")
    try:
        prompt = (
            "你是后兴。读取后荣检验报告的JSON，为每个不合格分片生成一条JSON修复任务。\n"
            f"不合格分片列表（共{len(defect_keys)}个）：\n"
            f"{shard_summary}\n\n"
            "只输出JSON数组，不要任何其他文字。\n"
            'JSON格式：[{"分片文件文件": "path", "chapter": "key", "问题": "...", "改善方向": "..."}, ...]\n\n'
            "重要：输出的任务数量必须等于不合格分片数量，每个分片只生成一条任务。\n\n"
            "===== 后荣检验报告JSON =====\n"
            f"{detail}\n"
        )
        reply = await runtime.chat(prompt, max_tokens=4000)
    except Exception:
        reply = ""
    finally:
        await runtime.shutdown()

    tasks = _parse_task_json(reply)
    if tasks:
        return tasks
    return [{"分片文件文件": data.get("path", sk), "chapter": sk, "问题": detail[:300], "改善方向": "根据检验报告修复"}
            for sk, data in all_ch.items() if sk in defect_keys and data.get("content")]


def _build_retry_task(task: dict, ctx: str, retry_index: int, reason: str = "") -> str:
    """逐轮加强的重试任务，防止子Agent重复生成同样的垃圾内容。"""
    import json as _j

    task_with_reason = dict(task)
    if reason:
        task_with_reason["重试原因"] = reason
    base = _j.dumps(task_with_reason, ensure_ascii=False)
    lines = [f"{base}\n\n上下文:\n{ctx}"]

    crisis_rules = [
        # retry 0: 温和提醒
        "\n\n===== 返工原因 =====\n"
        f"你的上一次输出被拒绝了，原因是：{reason}\n"
        "请仔细阅读上下文中的原始分片内容，严格按照修复指令修改。\n"
        "务必保留 <!-- CHAPTER: --> 和 <!-- PATH: --> 标记，保留所有标题结构，只修改不合格部分。",

        # retry 1: 严厉警告
        "\n\n===== ⚠️ 第2次返工 ⚠️ =====\n"
        f"上两次输出均被拒绝。拒绝原因：{reason}\n"
        "你的输出必须：\n"
        "1. 第1个字符是 '<'，紧接着是 '<!-- CHAPTER:分片key -->'，然后是换行\n"
        "2. 接着是 '<!-- PATH:完整文件路径 -->'（如果原分片有的话），然后是换行\n"
        "3. 然后是原始分片的标题和内容结构\n"
        "4. 只修改不合格项涉及的段落，其余逐字保留原文\n"
        "5. 正文至少200字\n"
        "禁止：乱码、重复段落、测试占位符、只有标记没有正文、改变原有大纲结构。",

        # retry 2: 最终通牒
        "\n\n===== 🚨 最后一次机会 🚨 =====\n"
        f"前三次全部失败！失败原因：{reason}\n"
        "现在你必须严格遵守以下格式，不得有任何偏差：\n"
        "输出 = {\"content\": \"<!-- CHAPTER:X -->\\n<!-- PATH:Y -->\\n# 原始标题\\n\\n具体正文内容...\"}\n"
        "正文必须包含：至少一个 ## 二级标题、至少3段正文、至少200字。\n"
        "如果你实在无法完成，请返回 {\"error\": \"无法完成\"}，不要编造垃圾内容。",
    ]

    idx = min(retry_index, len(crisis_rules) - 1)
    lines.append(crisis_rules[idx])

    return "\n".join(lines)


def _validate_shard_content(content: str, shard_key: str = "") -> tuple:
    """验证分片内容是否有效。返回 (is_valid, reason, cleaned_content)。"""
    import re

    if not content or not isinstance(content, str):
        return False, "内容为空或类型错误", content

    content = content.strip()

    if len(content) < 50:
        return False, f"内容过短（{len(content)}字符），疑似垃圾内容", content

    has_chapter = bool(re.search(r'<!--\s*CHAPTER\s*:', content))
    if not has_chapter:
        return False, "缺少 <!-- CHAPTER: --> 标记", content

    if len(content) < 200 and has_chapter:
        marker_end = content.find("-->")
        if marker_end != -1:
            body = content[marker_end+3:].strip()
            if len(body) < 30:
                return False, f"内容仅含 chapter 标记而无实质正文（正文仅{len(body)}字符）", content

    has_header = bool(re.search(r'^#{1,6}\s+', content, re.MULTILINE))
    if not has_header:
        import re as _re3
        if not shard_key:
            # 从 CHAPTER 标记自动提取 shard_key
            m = _re3.search(r'<!--\s*CHAPTER\s*:\s*([\w-]+)\s*-->', content)
            shard_key = m.group(1) if m else "标题"
        # 自动插入标题，确保内容通过验证
        fixed = _re3.sub(
            r'(<!--\s*CHAPTER\s*:\s*[\w-]+\s*-->\s*(?:<!--\s*PATH\s*:.*?-->\s*)?)',
            lambda m: m.group(1) + '\n# ' + shard_key,
            content,
            count=1,
        )
        if fixed != content:
            return True, "已自动添加标题", fixed
        return False, "缺少markdown标题（至少需要一个 # 标题）", content

    garbled_patterns = [
        r'(.)\1{30,}',
        r'(乱七八糟|胡言乱语|测试内容|占位符|placeholder)\s*$',
    ]
    for pat in garbled_patterns:
        if re.search(pat, content):
            return False, f"内容疑似垃圾：匹配模式「{pat}」", content

    if content.count("<!-- CHAPTER:") > 3:
        return False, "包含过多 chapter 标记，疑似拼接多个分片", content

    return True, "ok", content


def _parse_task_json(text: str) -> list:
    import json as _j
    if not text or not text.strip():
        return []
    text = text.strip()
    start = text.find('[')
    end = text.rfind(']')
    if start != -1 and end != -1 and start < end:
        try:
            data = _j.loads(text[start:end+1])
            if isinstance(data, list):
                return data
        except Exception:
            pass
    return []


async def houxing_verify_result(
    original_content: str, fixed_content: str, shard_key: str
) -> dict:
    if fixed_content == original_content:
        return {"changed": False, "reason": "内容无变化"}
    return {"changed": True, "reason": "已确认修改"}


def _fix_json_llm(raw: str) -> str:
    """修复LLM输出中常见的JSON格式错误，尽力返回合法JSON字符串"""
    if not raw or not raw.strip():
        return ""
    import json as _j
    import re

    text = raw.strip()

    lines = text.split("\n")
    clean_lines = [l for l in lines if not l.strip().startswith("```")]
    text = "\n".join(clean_lines).strip()

    # 遍历每个 { 位置，找到匹配的 }，逐块尝试提取合法 JSON
    def _try_parse(s: str) -> str | None:
        for step in [
            lambda x: x,
            lambda x: x.replace(": True", ":true").replace(": False", ":false").replace(": None", ":null")
                       .replace(":True", ":true").replace(":False", ":false").replace(":None", ":null"),
            lambda x: re.sub(r',\s*}', '}', x),
            lambda x: re.sub(r',\s*]', ']', x),
        ]:
            fixed = step(s)
            fixed = re.sub(r"'(维度|判定结果|得分|不合格章节|分片文件|不合格项数|项|理由|证据|改善方向|报告类型|报告版本|维度键|维度标签|总结|是否通过|不合格章节列表|分片|缺陷|修复方向|章节键|缺陷数)'", r'"\1"', fixed)
            fixed = fixed.replace("\r", "\\r")
            fixed = fixed.replace('\ufeff', '')
            fixed = re.sub(r'[\x00-\x08\x0b\x0c\x0e-\x1f]', '', fixed)
            try:
                _j.loads(fixed)
                return fixed
            except Exception:
                continue
        return None

    brace_starts = [i for i, c in enumerate(text) if c == '{']
    for start in brace_starts:
        depth = 0
        for end in range(start, len(text)):
            c = text[end]
            if c == '{':
                depth += 1
            elif c == '}':
                depth -= 1
                if depth == 0:
                    result = _try_parse(text[start:end + 1])
                    if result is not None:
                        return result
                    break

    # 兜底：raw_decode 直接解析（跳过外层非 JSON 文本）
    for start in brace_starts:
        try:
            obj, _ = _j.JSONDecoder().raw_decode(text, start)
            return _j.dumps(obj, ensure_ascii=False)
        except Exception:
            continue

    return text


def _clean_output(raw: str, is_inspection: bool = False) -> str:
    if not raw or not raw.strip():
        return ""
    import json as _j
    fixed = _fix_json_llm(raw)
    if not fixed:
        return raw.strip() if raw.strip().startswith("<!-- CHAPTER:") else ""
    if is_inspection:
        try:
            _j.loads(fixed)
            return fixed
        except Exception:
            logger.warning(f"hourong 子Agent JSON 解析失败，返回原始内容供 _call_hourong 二次修复")
            return fixed
    # 非检验模式：从 JSON 提取 content 字段
    try:
        data = _j.loads(fixed)
        if isinstance(data, dict):
            error_msg = data.get("error", "")
            if error_msg:
                logger.warning(f"子Agent返回error: {error_msg}")
                return f"[子Agent无法完成] {error_msg}"
            c = data.get("content") or data.get("document") or data.get("body") or data.get("修改后的内容") or data.get("result") or data.get("output") or data.get("正文") or data.get("修复后内容")
            if c and isinstance(c, str) and c.strip():
                return c.strip()
            # 兜底：找任意长字符串值（>=50字且以 <!-- 开头）
            for v in data.values():
                if isinstance(v, str) and len(v) >= 50 and v.strip().startswith("<!--"):
                    return v.strip()
            return ""
    except Exception:
        pass
    # JSON 解析完全失败，最终回退：如果 raw 看起来像非 JSON 的纯文本，检查是否以 chapter 标记开头
    raw_stripped = raw.strip()
    if raw_stripped.startswith("<!-- CHAPTER:") and len(raw_stripped) > 50:
        return raw_stripped
    return ""



