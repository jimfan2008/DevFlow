import asyncio
import json as _json
import os

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
    "必须快速且直接输出检验报告，必须输出一个严格合法的 JSON 对象作为最终回答，不要包含任何其他文字。\n"
    "JSON 格式如下：\n"
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
    "⚠️ 收敛性规则（必须严格执行）：\n"
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
        _build_annotated_content, _call_hourong, _extract_json_result,
        _normalize_inspection_results, _get_next_version, logger,
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
            + f"- 首次检验（第1轮）：每发现一个缺陷扣减相应分数（轻微扣5-10分，一般扣15-20分，严重扣25-30分）。得分>=90则通过。\n"
            + f"- 复检（第{attempt}轮）：仅对本轮**新发现**的不合格项扣分。已在上轮指出且已修复的不合格项不重复扣分。\n"
            + "  如果上一轮的所有不合格项均已修复且无新问题，得分必须为100分（通过）。\n"
            + "  得分>=90则通过。\n\n"
        )

        if attempt > 1 and last_defects_detail:
            inspect_prompt += (
                "=== 收敛性检查（严格遵循）===\n"
                f"这是第{attempt}轮复检。以下列出第{attempt - 1}轮发现的不合格项，请逐项严格判定：\n"
                "1. 逐项检查每个不合格项是否已修复。\n"
                "2. 已修复且合格 → 不计入本轮不合格项，不扣分。\n"
                "3. 未修复或修复不充分 → 继续指出，但已在上一轮扣过的分数不再重复扣。\n"
                "4. 仅本轮新发现的问题才作为新的不合格项扣分。\n"
                "5. 如果所有不合格项均已修复，得分必须为100，评定为「合格」，不合格项为[]。\n\n"
                "上一轮不合格项：\n"
                + last_defects_detail + "\n\n"
                + "后兴已对以下分片文件进行了修改（重点检验）：\n"
                + (last_fixed_paths + "\n\n" if last_fixed_paths else "（无明确分片记录，请检查完整文档）\n\n")
                + "收敛目标：不合格项必须逐轮减少。若全部修复，请直接判定通过。\n\n"
            )

        inspect_prompt += (
            "!!! 你必须输出一个合法的 JSON 对象（不是数组），不要包含任何其他文字。!!!\n"
            + "JSON格式：\n"
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

        raw_reply = ""
        result_data = {}
        result = None
        prev_reply = ""
        json_format = (
            '{"维度": "' + dim_label + '", "得分": <0-100>, "评定": "合格/不合格",'
            ' "不合格项": [{"问题": "...", "修改方向": "...", "证据": "（必须有 [chapter:key]）"}]}'
        )
        for hr_attempt in range(6):
            if hr_attempt == 0:
                reply = await _call_hourong(websocket, inspect_prompt, system_message=HOURONG_SYSTEM_MSG)
            else:
                reply = await _call_hourong(
                    websocket, inspect_prompt,
                    system_message=HOURONG_SYSTEM_MSG,
                    prev_reply=prev_reply,
                    follow_up="你刚才返回的内容不包含合法JSON。请只输出JSON格式，不要任何其他文字。检验结果不变，只改格式。格式：\n" + json_format,
                )
            prev_reply = reply
            raw_reply = reply
            parsed = _extract_json_result(reply)
            normalized = _normalize_inspection_results(parsed)
            if normalized and normalized[0].get("key"):
                result = normalized[0]
                break
            logger.warning(f"hourong返回格式异常(第{hr_attempt+1}次): {reply[:200]}")
            await websocket.send_json({
                "type": "progress",
                "content": f"\n⚠️ hourong第{hr_attempt+1}次返回格式不合法，要求重输出JSON\n"
            })

        if not result:
            if result_data:
                dim_label = (result_data.get("维度") or result_data.get("维 度") or dim_label)
                score_str = (result_data.get("得分") or result_data.get("分数") or result_data.get("score") or "100")
                try:
                    score = int(float(str(score_str)))
                except (ValueError, TypeError):
                    score = 100
                passed_str = str(result_data.get("判定结果") or result_data.get("评定") or result_data.get("结果") or result_data.get("passed") or "合格")
                passed = passed_str in ("通过", "合格", "true", "True", "pass", "PASS")
                defects = result_data.get("不合格章节") or result_data.get("不合格项") or result_data.get("缺陷") or result_data.get("issues") or []
                detail_parts = []
                if isinstance(defects, list):
                    for d in defects:
                        if isinstance(d, dict):
                            if "项" in d:
                                shard_file = d.get("分片文件", "")
                                items = d.get("项", [])
                                if isinstance(items, list):
                                    shard_lines = []
                                    for df_item in items:
                                        reason = df_item.get("理由") or ""
                                        evidence = df_item.get("证据") or df_item.get("位置") or ""
                                        fix_dir = df_item.get("改善方向") or df_item.get("修改方向") or df_item.get("建议") or ""
                                        shard_lines.append(f"不合格的理由：{reason}；证据：{evidence}；改善方向：{fix_dir}")
                                    if shard_lines:
                                        detail_parts.append(f"分片文件{shard_file}：{len(items)}项不合格，{'；'.join(shard_lines)}")
                                continue
                            p = d.get("问题") or d.get("描述") or ""
                            f = d.get("修改方向") or d.get("建议") or ""
                            e = d.get("证据") or d.get("位置") or ""
                            parts = [p, f"修改方向：{f}" if f else "", f"证据：{e}" if e else ""]
                            detail_parts.append(" ".join(p for p in parts if p))
                detail = "\n\n".join(detail_parts) if detail_parts else ""
                from .step3_qa import _DIMENSION_LABEL_TO_KEY
                result = {
                    "key": _DIMENSION_LABEL_TO_KEY.get(dim_label, dim_label),
                    "label": dim_label,
                    "score": score,
                    "passed": passed,
                    "detail": detail,
                    "deduction": "" if passed else f"得分{score}，满分100，扣{100 - score}分",
                }
            else:
                await websocket.send_json({
                    "type": "error",
                    "message": f"后荣未能返回 {dim_label} 的合法检验结果，请检查后荣 agent 状态"
                })
                return False, content, None

        if not result:
            await websocket.send_json({
                "type": "error",
                "message": f"后荣连续3次未能返回 {dim_label} 的检验结果"
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

        # 从 hourong JSON 的「不合格章节」提取权威的分片缺陷映射
        shard_fix_map = {}
        try:
            raw_for_fix = _json.loads(raw_reply)
            if isinstance(raw_for_fix, dict):
                raw_for_fix = [raw_for_fix]
            for item in raw_for_fix if isinstance(raw_for_fix, list) else []:
                chapters = item.get("不合格章节", [])
                if isinstance(chapters, list):
                    for ch_entry in chapters:
                        sk_or_path = ch_entry.get("分片文件", "")
                        items = ch_entry.get("项", [])
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
            "content": f"\n 后荣检验报告：\n{raw_reply}\n\n"
        })

        if project_id and db:
            _save_qa_checkpoint(
                project_id, db,
                step=SUB_STEP["step"] - 1, attempt=attempt,
                results=list(all_results or []),
                content=content, last_save_path=last_save_path,
            )

        version = await _get_next_version(project_docs_dir, project_slug)
        failed_summary = f"- {dim_label}（得分:{dim_score}）: {detail[:600]}"

        await websocket.send_json({
            "type": "progress",
            "content": f"  识别出 {len(failed_chapter_keys)} 个不合格分片: {', '.join(sorted(failed_chapter_keys))}\n"
        })

        async def _fix_one_shard(shard_key: str, shard_defects: list = None) -> tuple:
            ch_data = all_ch.get(shard_key, {})
            if not ch_data or not ch_data.get("content"):
                return (shard_key, "")
            shard_path = ch_data.get("path", shard_key)
            original_content = ch_data['content']

            await websocket.send_json({
                "type": "progress",
                "content": f"\n  🤖 后兴读取hourong检验报告 [{shard_key}]\n  文件: {shard_path}\n"
            })

            subtasks = await houxing_plan_tasks(
                detail=detail, shard_content=original_content, shard_key=shard_key, shard_path=shard_path,
            )

            await websocket.send_json({
                "type": "progress",
                "content": f"  📋 后兴输出 {len(subtasks)} 条修复指令:\n" +
                    "\n".join(f"    {i+1}. {t[:80]}" for i, t in enumerate(subtasks)) + "\n"
            })

            context_with_content = f"分片文件: {shard_path}\n\n当前内容:\n{original_content[:4000]}"
            full_tasks = [f"{t}\n\n上下文:\n{context_with_content}" for t in subtasks]

            await websocket.send_json({
                "type": "progress",
                "content": f"  🚀 delegate_task 并行 {len(full_tasks)} 个子Agent...\n"
            })

            for fix_round in range(3):
                sub_results = await delegate_task(
                    tasks=full_tasks,
                    wait_all=True, timeout=600, max_concurrent=10,
                )

                current_content = original_content
                for r in reversed(sub_results):
                    if r and not r.startswith("[子Agent异常]") and r != original_content:
                        current_content = r
                        break

                if current_content != original_content and current_content:
                    if not current_content.startswith("<!-- CHAPTER:"):
                        await websocket.send_json({
                            "type": "progress",
                            "content": f"  ⚠️ 子Agent返回内容缺少「<!-- CHAPTER:」标记，要求重新生成 [{shard_key}]\n"
                        })
                        current_content = original_content

                if current_content != original_content:
                    break

                await websocket.send_json({
                    "type": "progress",
                    "content": f"  🔄 子agent未修改内容，第{fix_round+1}次重试 [{shard_key}]\n"
                })

            if current_content == original_content:
                await websocket.send_json({
                    "type": "progress",
                    "content": f"  ⚠️ 分片内容无变化 [{shard_key}]\n"
                })
                return (shard_key, "")

            await websocket.send_json({
                "type": "progress",
                "content": f"  ✅ {len(subtasks)} 个子Agent完成 [{shard_key}]\n"
            })

            return (shard_key, current_content)

        await websocket.send_json({
            "type": "progress",
            "content": f"  🚀 调度houxing为 {len(failed_chapter_keys)} 个分片统一生成修复任务...\n"
        })

        all_tasks = await houxing_plan_tasks(
            detail=detail, all_ch=all_ch,
            project_docs_dir=project_docs_dir, project_slug=project_slug,
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

        full_tasks = []
        for t in all_tasks:
            sk = t.get("chapter", "")
            ch_data = all_ch.get(sk, {})
            ctx = f"分片文件: {ch_data.get('path', sk)}\n\n当前内容:\n{ch_data.get('content', '')[:4000]}"
            full_tasks.append(f"{_json.dumps(t, ensure_ascii=False)}\n\n上下文:\n{ctx}")

        await websocket.send_json({
            "type": "progress",
            "content": f"  🚀 delegate_task 并行 {len(full_tasks)} 个子Agent...\n"
        })

        sub_results = await delegate_task(
            tasks=full_tasks, wait_all=True, timeout=600, max_concurrent=10, websocket=websocket,
        )

        fixed_shard_paths = []
        for t, result_str in zip(all_tasks, sub_results):
            sk = t.get("chapter", "")
            if not result_str or result_str.startswith("[子Agent异常]") or result_str.startswith("[子Agent超时]"):
                continue

            shard_path = all_ch.get(sk, {}).get("path", "")

            if not result_str.startswith("<!-- CHAPTER:"):
                await websocket.send_json({
                    "type": "progress",
                    "content": f"  ⚠️ 子Agent返回内容缺少「<!-- CHAPTER:」标记，删除无效文件重新生成 [{sk}]\n"
                })
                if shard_path and os.path.exists(shard_path):
                    os.remove(shard_path)
                for retry in range(3):
                    retry_results = await delegate_task(
                        tasks=[_json.dumps(t, ensure_ascii=False)],
                        wait_all=True, timeout=600, max_concurrent=1, websocket=websocket,
                    )
                    result_str = retry_results[0] if retry_results else ""
                    if result_str and not result_str.startswith("[子Agent异常]") and not result_str.startswith("[子Agent超时]"):
                        if result_str.startswith("<!-- CHAPTER:"):
                            break
                    if shard_path and os.path.exists(shard_path):
                        os.remove(shard_path)
                    await websocket.send_json({
                        "type": "progress",
                        "content": f"  ⚠️ 子Agent第{retry+1}次重试仍缺少 chapter 标记 [{sk}]\n"
                    })
                else:
                    await websocket.send_json({
                        "type": "progress",
                        "content": f"  ❌ 子Agent重试3次仍无法生成有效内容，跳过 [{sk}]\n"
                    })
                    continue

            if result_str == all_ch.get(sk, {}).get("content", ""):
                await websocket.send_json({
                    "type": "progress",
                    "content": f"  ⚠️ 分片无变化 [{sk}]\n"
                })
                continue

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
            "content": f"  ✅ 全部 {len(failed_chapter_keys)} 个不合格分片修复完成，已分别保存到对应分片文件\n"
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
        )
        cp = _load_qa_checkpoint(project_id, db)
        cp["exhausted"] = True
        cp["last_defects_detail"] = last_defects_detail
        cp["last_fixed_paths"] = last_fixed_paths
        from app.services.workflow_engine import WorkflowEngine
        engine = WorkflowEngine(project_id, db)
        engine.save_step3_artifacts({"qa_checkpoint": cp})
    return False, content, result


class HermesRuntime:
    def __init__(self):
        self._gateway = None

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
        import tempfile, os
        filepath = os.path.join(tempfile.gettempdir(), f"houxing_{os.urandom(4).hex()}.json")
        with open(filepath, "w", encoding="utf-8") as f:
            f.write(reply)
        return reply

    async def shutdown(self):
        self._gateway = None


async def delegate_task(
    tasks: list,
    wait_all: bool = True,
    timeout: int = 600,
    max_concurrent: int = 10,
    websocket=None,
) -> list:
    sem = asyncio.Semaphore(max_concurrent)
    task_timeout = min(timeout, 1200)
    shared_client = GatewayClient(profile_name="houxing", timeout=task_timeout)

    async def _run_one(task_desc: str) -> str:
        import json as _j
        import tempfile, os
        save_path = ""
        task_info = task_desc
        try:
            start = task_desc.find('{')
            end = task_desc.rfind('}')
            if start != -1 and end != -1:
                parsed = _j.loads(task_desc[start:end+1])
                if isinstance(parsed, dict):
                    path = parsed.get("分片文件文件", "")
                    chapter = parsed.get("chapter", "")
                    problem = parsed.get("问题", "")
                    fix_dir = parsed.get("改善方向", "")
                    save_path = path
                    task_info = f"分片文件: {path}\n章节: {chapter}\n问题: {problem}\n改善方向: {fix_dir}"
        except Exception:
            pass
        prompt = (
            "你是一个文档修复子Agent。任务指令是一个JSON对象，只读取JSON字段中的内容，忽略所有非JSON的文字。\n"
            f"===== 修复任务 =====\n{task_info}\n\n"
            "===== 输出格式 =====\n"
            '输出JSON: {"content": "修改后的完整文档正文"}\n'
            "只输出JSON，不要任何其他文字。\n"
        )
        async with sem:
            try:
                result = await asyncio.wait_for(
                    _do_subagent_call(shared_client, prompt, websocket),
                    timeout=task_timeout,
                )
                if result and not result.startswith("[子Agent") and save_path:
                    os.makedirs(os.path.dirname(save_path), exist_ok=True)
                    with open(save_path, "w", encoding="utf-8") as f:
                        f.write(result)
                return result
            except asyncio.TimeoutError:
                return "[子Agent超时]"
            except Exception as e:
                return f"[子Agent异常] {str(e)}"

    async def _do_subagent_call(client: GatewayClient, prompt: str, ws) -> str:
        import tempfile, os
        chunks = []
        async for chunk in client.chat_completions(
            messages=[{"role": "user", "content": prompt}],
            stream=True, max_tokens=4000,
        ):
            if chunk.strip():
                chunks.append(chunk)
        raw = "".join(chunks).strip()
        result = _clean_output(raw)
        filepath = os.path.join(tempfile.gettempdir(), f"agent_{os.urandom(4).hex()}.json")
        with open(filepath, "w", encoding="utf-8") as f:
            f.write(raw)
        if ws:
            await ws.send_json({"type": "houxing_chunk", "content": filepath})
        return result

    coros = [_run_one(t) for t in tasks]
    results = await asyncio.gather(*coros, return_exceptions=True)
    return [r if isinstance(r, str) else f"[子Agent异常] {str(r)}" for r in results]


async def houxing_plan_tasks(detail: str, all_ch: dict, project_docs_dir: str, project_slug: str) -> list:
    """后兴读取hourong报告，为所有不合格分片生成修复任务。一次调用返回全部任务。"""
    shard_lines = []
    for sk, data in all_ch.items():
        if data.get("content"):
            fp = data.get("path", sk)
            shard_lines.append(f"  [分片: {sk}] 文件: {fp}")
    shard_summary = "\n".join(shard_lines)

    runtime = HermesRuntime()
    await runtime.load_profile("houxing")
    try:
        prompt = (
            "你是后兴。读取后荣检验报告的JSON，为每个不合格分片生成一条JSON修复任务。\n"
            "分片列表：\n"
            f"{shard_summary}\n\n"
            "只输出JSON数组，不要任何其他文字。\n"
            'JSON格式：[{"分片文件文件": "path", "chapter": "key", "问题": "...", "改善方向": "..."}, ...]\n\n'
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
            for sk, data in all_ch.items() if data.get("content")]


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


def _clean_output(raw: str) -> str:
    if not raw or not raw.strip():
        return ""
    text = raw.strip()
    start = text.find('{')
    end = text.rfind('}')
    if start != -1 and end != -1 and start < end:
        try:
            import json as _j
            data = _j.loads(text[start:end+1])
            if isinstance(data, dict):
                c = data.get("content") or data.get("document") or data.get("body") or data.get("修改后的内容") or data.get("result") or data.get("output")
                if c and isinstance(c, str) and c.strip():
                    return c.strip()
        except Exception:
            pass
    return text



