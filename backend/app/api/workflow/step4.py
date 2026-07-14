from app.api.workflow.core import (
    router, _get_engine, logger, APIResponse, Depends, get_db,
    get_current_user, Session, Body, Request, HTTPException,
    BaseModel, Optional, asyncio, os, settings,
    Step3InspectRequest, Step5ChatRequest, QAResultRequest,
    DocsListRequest, ARCH_DESIGN_DIMENSIONS, _wf_engines, WorkflowEngine,
)
from app.api.ws.step4_progress import broadcast

@router.post("/{project_id}/step4/artifacts")
def save_step4_artifacts(project_id: str, body: dict = Body(...),
                         db: Session = Depends(get_db),
                         current_user=Depends(get_current_user)):
    engine = _get_engine(project_id, db)
    engine.save_step4_artifacts(body)
    return APIResponse(code=0, data={"message": "步骤4状态已保存"})


@router.get("/{project_id}/step4/status")
def get_step4_status(project_id: str,
                     db: Session = Depends(get_db),
                     current_user=Depends(get_current_user)):
    engine = _get_engine(project_id, db)
    artifacts = engine.get_step4_artifacts()
    return APIResponse(code=0, data=artifacts)


# ── Step4 串行子步骤配置与辅助函数 ──

SUB_FLOW_CONFIGS = [
    {
        "doc_type": "ARCHITECTURE",
        "label": "架构设计文档",
        "dim": {"key": "arch_reasonableness", "label": "架构合理性", "description": "架构设计是否合理，是否满足需求文档中的功能和非功能需求"},
        "gen_instruction": "系统整体架构图描述、分层架构、模块划分、技术栈选型、部署架构",
        "standards": [
            {"name": "完整性", "description": "是否覆盖所有功能和非功能需求", "weight": "critical"},
            {"name": "合理性", "description": "架构分层是否清晰，模块划分是否合理，边界是否明确", "weight": "critical"},
            {"name": "技术选型", "description": "技术栈选择理由是否充分，选型是否适合项目规模和团队能力", "weight": "major"},
            {"name": "可扩展性", "description": "是否考虑了未来功能扩展、性能扩展和团队扩展", "weight": "major"},
            {"name": "部署架构", "description": "部署方案是否完整可行，环境划分、CI/CD、容灾是否提及", "weight": "major"},
        ],
    },
    {
        "doc_type": "FRONTEND",
        "label": "前端设计文档",
        "dim": {"key": "frontend_feasibility", "label": "前端可行性", "description": "前端设计方案是否可行，技术选型是否合理"},
        "gen_instruction": "前端技术栈、组件树、路由设计、状态管理、页面布局",
        "standards": [
            {"name": "技术选型", "description": "前端框架、UI组件库、构建工具选择是否合理，版本是否明确", "weight": "critical"},
            {"name": "组件设计", "description": "组件树层级划分是否合理，复用性和可维护性如何", "weight": "critical"},
            {"name": "路由设计", "description": "路由结构是否完整，是否覆盖所有页面，权限控制方案是否合理", "weight": "major"},
            {"name": "状态管理", "description": "状态管理方案（全局/局部）选择是否合理，数据流向是否清晰", "weight": "major"},
            {"name": "页面布局", "description": "页面布局是否覆盖所有需求中的页面，响应式方案是否考虑", "weight": "major"},
        ],
    },
    {
        "doc_type": "BACKEND",
        "label": "后端设计文档",
        "dim": {"key": "backend_feasibility", "label": "后端可行性", "description": "后端设计方案是否可行，API设计是否合理"},
        "gen_instruction": "后端技术栈、API接口列表、数据流、中间件、安全策略",
        "standards": [
            {"name": "技术选型", "description": "后端语言、框架、数据库、中间件选择是否合理", "weight": "critical"},
            {"name": "API设计", "description": "API接口设计是否RESTful（或一致风格），参数/返回值定义是否完整", "weight": "critical"},
            {"name": "数据流", "description": "数据流向（请求→控制器→服务→数据源）是否清晰，缓存策略是否合理", "weight": "major"},
            {"name": "安全策略", "description": "认证、授权、数据加密、防注入等安全方案是否完整", "weight": "critical"},
            {"name": "可扩展性", "description": "模块化程度如何，是否支持水平扩展，微服务拆分是否合理", "weight": "major"},
        ],
    },
    {
        "doc_type": "DATABASE",
        "label": "数据库设计脚本",
        "dim": {"key": "database_design", "label": "数据库设计", "description": "数据库设计是否规范，ER关系是否清晰"},
        "gen_instruction": "完整SQL DDL脚本（含表结构、索引、外键），以及ER概述",
        "standards": [
            {"name": "规范性", "description": "命名规范（表名、字段名）、数据类型选择是否合理，是否符合范式", "weight": "critical"},
            {"name": "完整性", "description": "是否覆盖所有业务实体，字段定义是否完整（非空、默认值、注释）", "weight": "critical"},
            {"name": "关系设计", "description": "ER关系是否清晰，外键约束是否合理，关联表设计是否规范", "weight": "critical"},
            {"name": "索引设计", "description": "索引是否覆盖常用查询条件，是否避免冗余索引", "weight": "major"},
            {"name": "可维护性", "description": "DDL脚本是否有充分注释，是否支持幂等执行（IF NOT EXISTS等）", "weight": "major"},
        ],
    },
]


def _build_inspect_prompt(
    doc_path: str, dim: dict, standards: list,
    dim_key: str, prev_feedback: str = "",
    chapter_label: str = "",
) -> str:
    """构建 hourong 检验提示词（简洁、严格 JSON 格式）"""
    dim_label = dim["label"]
    dim_desc = dim["description"]

    std_items = "\n".join(
        f"  {i+1}. [{s['weight'].upper()}] {s['name']}：{s['description']}"
        for i, s in enumerate(standards)
    )

    converge_hint = ""
    if prev_feedback:
        converge_hint = (
            f"\n⚠️ 收敛性检查（极其重要）：\n"
            f"上次检验报告指出了以下问题，请逐条核实本次文档是否已修复：\n"
            f"{prev_feedback}\n"
            f"如果问题已修复，不要再重复报告；如果问题未修复，继续报告。\n"
            f"禁止报告与上次相同的问题（如果上次指出的问题已修复）。\n"
            f"禁止对合格项提出新的修改要求。\n"
        )

    chapter_hint = f"\n检验的分片文档：{chapter_label}\n" if chapter_label else ""
    chapter_field = f'  "chapter": "{chapter_label}",\n' if chapter_label else ""
    return (
        "你是一个严格的 JSON-only API。只输出 JSON，禁止任何其他文字。\n\n"
        "角色：专业的设计方案 QA 检验员（后荣 / HouRong）\n\n"
        f"检验项目：{dim_label}（{dim_desc}）\n"
        f"文档路径：{doc_path}\n"
        f"{chapter_hint}"
        f"任务：读取该文档文件，严格逐项对照以下标准检验。\n\n"
        f"检验标准：\n{std_items}\n\n"
        "评分规则：满分100分，扣分制。score≥90 则 passed=true。\n\n"
        "输出格式（严格 JSON 对象）：\n"
        "{\n"
        f'  "key": "{dim_key}",\n'
        f'{chapter_field}'
        '  "score": <0-100>,\n'
        '  "passed": <true/false>,\n'
        '  "detail": "<简要说明不合格项及修改方向，passed=true可留空>"\n'
        "}\n\n"
        f"{converge_hint}"
        "规则：\n"
        "1. 只输出 JSON 对象本身，不要 markdown 代码块，不要任何其他文字\n"
        "2. 不要思考、分析、推理\n"
        "3. passed=false 时 detail 必须说明问题和修改方向\n"
        "4. detail 保持简洁，每条不合格项用1-2句话\n"
        "5. 已合格项不要提修改要求\n"
        "JSON："
    )


async def _inspect_doc(
    project_id: str, doc_path: str, dim: dict,
    project_name: str = "", project_description: str = "",
    core_goal: str = "", agent_label: str = "",
    standards: list = None, prev_feedback: str = "",
    chapter_label: str = "", docs_dir: str = "",
) -> dict:
    """调用 hourong-{doc_type} 对单份文档进行单次 QA 检验（项目会话隔离）。
    将文档路径告知 hourong 让 Agent 自行读取文件，避免在大文档上 context 溢出。
    空响应或无法解析时内部重试最多3次。
    prev_feedback: 上一轮检验意见，用于收敛检测。
    返回 report_path: hourong 原始报告文件的保存路径。
    """
    import json as _json, re as _re, os as _os
    from datetime import datetime
    from app.api.ws.step3_qa import _inspect_via_subagent
    from app.api.ws.step4_progress import broadcast

    dim_key = dim["key"]
    dim_label = dim["label"]
    max_attempts = 3

    # 确保 docs_dir 存在
    if docs_dir:
        _os.makedirs(docs_dir, exist_ok=True)

    for attempt in range(1, max_attempts + 1):
        insp_prompt = _build_inspect_prompt(
            doc_path=doc_path, dim=dim, standards=standards or [],
            dim_key=dim_key, prev_feedback=prev_feedback,
            chapter_label=chapter_label,
        )

        if attempt > 1:
            await broadcast(project_id, {
                "type": "stage",
                "message": f"🔄 {dim_label}：hourong 第{attempt}次重试检验...",
                "subflow": dim_key,
            })

        qa_r = await _inspect_via_subagent(prompt=insp_prompt, max_retries=2)

        if not qa_r:
            if attempt < max_attempts:
                continue
            return {"key": dim_key, "passed": False, "detail": "后荣未返回检验结果（空响应）", "report_path": ""}

        # 保存 hourong 原始报告到文件
        ts = datetime.now().strftime("%Y%m%d_%H%M%S")
        rnd = _os.urandom(2).hex()
        fname = f"hourong_report_{dim_key}_{ts}_{rnd}.txt"
        report_save_path = ""
        if docs_dir:
            report_save_path = _os.path.join(docs_dir, fname)
            try:
                with open(report_save_path, "w", encoding="utf-8") as f:
                    f.write(qa_r)
            except Exception:
                report_save_path = ""

        # Extract JSON from LLM response — multi-strategy extraction
        single = {}

        # Strip thinking/analysis tags
        _lt, _gt = chr(60), chr(62)
        _think_open = rf'{_lt}(?:thinking|think|analysis){_gt}'
        _think_close = rf'{_lt}/(?:thinking|think|analysis){_gt}'
        clean_text = _re.sub(rf'(?:{_think_open})[\s\S]*?(?:{_think_close})', '', qa_r)

        candidates = []

        # Strategy: code fences
        fenced = _re.findall(r'```(?:json)?\s*\n?(.*?)\n?```', clean_text, _re.DOTALL)
        for fc in fenced:
            stripped = fc.strip()
            if stripped:
                candidates.append(stripped)

        # Strategy: brace extraction
        brace_start = clean_text.find('{')
        brace_end = clean_text.rfind('}')
        if brace_start != -1 and brace_end != -1 and brace_end > brace_start:
            candidates.append(clean_text[brace_start:brace_end + 1])

        # Strategy: JSON-like regex
        json_like = _re.findall(r'\{[^{}]*(?:\{[^{}]*\}[^{}]*)*\}', clean_text)
        for jl in json_like:
            if len(jl) > 10:
                candidates.append(jl)

        # Strategy: strip non-JSON prefix/suffix
        stripped = clean_text.strip()
        bs2 = stripped.find('{')
        if bs2 > 0:
            candidates.append(stripped[bs2:])
        be2 = stripped.rfind('}')
        if be2 >= 0 and be2 < len(stripped) - 1:
            candidates.append(stripped[:be2 + 1])

        candidates.append(clean_text)

        def _repair_json(text):
            t = text.strip()
            t = _re.sub(r',\s*([}\]])', r'\1', t)
            try:
                return _json.loads(t)
            except Exception:
                pass
            core = t.lstrip('\n\r\t ')
            while core and core[0] not in '{[":':
                core = core[1:]
            while core and core[-1] not in '}]\n\r\t ':
                core = core[:-1]
            try:
                return _json.loads(core.strip())
            except Exception:
                pass
            return None

        for candidate in candidates:
            try:
                parsed = _json.loads(candidate)
                if isinstance(parsed, dict) and parsed:
                    single = parsed
                    break
            except Exception:
                pass
            repaired = _repair_json(candidate)
            if repaired and isinstance(repaired, dict) and repaired:
                single = repaired
                break

        if not single:
            if attempt < max_attempts:
                await broadcast(project_id, {
                    "type": "stage",
                    "message": f"⚠️ {dim_label}：hourong 返回无法解析的检验报告，第{attempt}次重试",
                    "subflow": dim_key,
                })
                continue
            await broadcast(project_id, {
                "type": "stage",
                "message": f"❌ hourong 返回了{dim_label}无法解析的检验报告。报告已保存到：{report_save_path}",
                "subflow": dim_key,
            })
            return {
                "key": dim_key, "passed": False,
                "detail": f"后荣返回了无法解析的检验报告（{max_attempts}次重试均失败）",
                "raw_response": qa_r[:1000],
                "report_path": report_save_path,
            }

        overall_passed = int(single.get("score", 0)) > 90 or bool(single.get("passed", False))
        detail_text = single.get("detail", "").strip()

        if not overall_passed and (not detail_text or len(detail_text) < 20):
            detail_text = "后荣判定不合格但未返回详细检验意见"

        score = int(single.get("score", 100))
        return {
            "key": dim_key,
            "score": score,
            "passed": overall_passed,
            "detail": detail_text or "检验完成",
            "report_path": report_save_path,
        }

    # 所有尝试都失败
    return {"key": dim_key, "passed": False, "detail": "后荣连续3次未返回检验结果", "report_path": ""}


# ── 文档分片支持 ──
CHAPTER_MARKER_START = "<!-- CHAPTER:"
CHAPTER_MARKER_END = "-->"


def _split_chapters(full_text: str) -> dict:
    import re
    chapters = {}
    pattern = re.compile(
        rf'{re.escape(CHAPTER_MARKER_START)}\s*(\w+)\s*{re.escape(CHAPTER_MARKER_END)}'
        r'([\s\S]*?)(?='
        rf'{re.escape(CHAPTER_MARKER_START)}|\Z)'
    )
    for m in pattern.finditer(full_text):
        key = m.group(1)
        content = m.group(2).strip()
        if content:
            chapters[key] = content
    return chapters


def _build_chapter_prompt(doc_type, label, gen_instruction, requirement, docs_dir, slug):
    from app.services.doc_sharder import get_shard_config, get_chapter_filename
    configs = get_shard_config(doc_type)
    lines = [
        f"你是资深软件架构师后旺（HouWang），专门负责{label}。\n",
        "请根据需求文档，按章节输出完整文档。\n",
        f"=== 需求文档 ===\n{requirement[:5000]}\n\n",
        f"=== 章节要求 ===\n",
    ]
    for ch in configs:
        fpath = get_chapter_filename(doc_type, ch["key"], docs_dir, slug)
        lines.append(
            f"{CHAPTER_MARKER_START} {ch['key']} {CHAPTER_MARKER_END}\n"
            f"章节：{ch['title']}\n"
            f"内容要求：{ch['instruction']}\n"
            f"保存到：{fpath}\n"
        )
    lines.append(
        "\n要求：\n"
        "1. 每个章节用 <!-- CHAPTER: key --> 标记包裹\n"
        "2. 每个章节保存到指定的文件路径\n"
        "3. 章节内容必须是独立的 Markdown 片段\n"
        "4. 不要输出推理过程\n"
    )
    return "\n".join(lines)


async def _run_doc_sub_flow(
    project_id: str, slug: str, docs_dir: str,
    cfg: dict, requirement: str,
    project_name: str = "", project_description: str = "",
    core_goal: str = "",
) -> dict:
    """单个文档子流程：检查已有→houwang生成→hourong检验→收敛循环（项目会话隔离）"""
    import os, glob, re, json as _json
    from app.services.gateway_client import GatewayClient
    from app.api.ws.step4_progress import broadcast

    doc_type = cfg["doc_type"]
    label = cfg["label"]
    dim = cfg["dim"]
    gen_instruction = cfg["gen_instruction"]
    houwang_label = f"后旺-{doc_type}（HouWang-{doc_type}）{label}设计师"
    hourong_label = f"后荣-{doc_type}（HouRong-{doc_type}）{label}QA检验员"

    # 1. 扫描该文档类型的最新已有版本
    latest_path = None
    latest_content = ""
    max_ver = 0
    for f in sorted(glob.glob(os.path.join(docs_dir, f"{slug}_{doc_type}_V*.md"))):
        m = re.search(r'_V(\d+)\.md$', f)
        if m:
            v = int(m.group(1))
            if v > max_ver:
                max_ver = v
                latest_path = f
    if latest_path:
        try:
            with open(latest_path, "r", encoding="utf-8") as fh:
                latest_content = fh.read()
        except Exception:
            pass

    current_content = latest_content
    current_path = latest_path
    convergence_log = []
    max_attempts = 10

    def _result_is_valid(r: dict) -> bool:
        """检查 inspect 结果是否有有效的检验意见"""
        if not r.get("report_path") and not r.get("detail"):
            return False
        detail = r.get("detail", "")
        invalid_phrases = ["未返回检验结果", "无法解析的检验报告", "空响应"]
        if any(p in detail for p in invalid_phrases):
            return False
        return len(detail) >= 10

    def _append_convergence(rnd: int, r: dict):
        """安全追加收敛日志"""
        convergence_log.append({
            "round": rnd,
            "detail": r.get("detail", ""),
            "passed": r.get("passed", False),
            "report_path": r.get("report_path", ""),
        })

    for fix_round in range(1, max_attempts + 1):
        # ── 第一轮：先让 hourong 检验现有文档 ──
        if fix_round == 1 and current_path and os.path.exists(current_path):
            await broadcast(project_id, {
                "type": "stage",
                "message": f"🔍 {label}：已有 V{max_ver}，houwang-{doc_type} 提交至 hourong 检验现有文档...",
                "subflow": dim["key"],
            })
            result = await _inspect_doc(
                project_id, current_path, dim,
                project_name=project_name, project_description=project_description,
                core_goal=core_goal, agent_label=hourong_label,
                standards=cfg.get("standards", []),
                docs_dir=docs_dir,
            )
            if result["passed"]:
                await broadcast(project_id, {
                    "type": "stage",
                    "message": f"✅ {label}：现有文档 V{max_ver} 已通过 hourong 检验，无需重新生成",
                    "subflow": dim["key"],
                })
                return {
                    "key": dim["key"], "label": label,
                    "path": current_path, "content": current_content,
                    "passed": True, "rounds": 0, "convergence": [],
                }
            # 检查 inspect 结果是否有效
            if not _result_is_valid(result):
                await broadcast(project_id, {
                    "type": "stage",
                    "message": f"⚠️ {label}：hourong 未返回有效检验报告，跳过已有文档检验继续执行",
                    "subflow": dim["key"],
                })
                # 不追加 convergence_log，让流程继续到 houwang 首次生成
            else:
                await broadcast(project_id, {
                    "type": "stage",
                    "message": f"📝 {label}：现有文档 V{max_ver} 未通过（{result.get('detail','')[:120]}），houwang 基于此版本更新",
                    "subflow": dim["key"],
                })
                _append_convergence(0, result)

        # ── houwang 生成或修复 ──
        nv = max_ver + fix_round
        gen_path = os.path.join(docs_dir, f"{slug}_{doc_type}_V{nv}.md")

        if fix_round == 1 and not current_content.strip():
            # 首次从零生成（无已有文档）
            houwang_role = f"houwang-{doc_type}"
            prompt = (
                f"你是资深软件架构师后旺（HouWang），代号 {houwang_role}，专门负责{label}。\n\n"
                "请根据以下需求文档，**生成并保存**该文档。\n"
                "请使用你 Agent 的文件写入能力将文档保存到指定路径。\n\n"
                "=== 需求文档 ===\n"
                f"{requirement[:5000]}\n\n"
                f"=== {label}要求 ===\n"
                f"路径：{gen_path}\n"
                f"内容：{gen_instruction}\n\n"
                "要求：\n"
                "1. 文档必须是独立完整的 Markdown 文件\n"
                "2. 保存到文件中的内容必须是纯文档内容，不要包含推理过程\n"
            )
            await broadcast(project_id, {
                "type": "stage",
                "message": f"🏗️ {label}：{houwang_role} 正在从需求生成初始文档...",
                "subflow": dim["key"],
            })
        else:
            # 基于已有文档 + hourong 反馈进行修复
            houwang_role = f"houwang-{doc_type}"
            fix_detail = convergence_log[-1]["detail"] if convergence_log else "需整体改进"
            report_path_hint = ""
            if convergence_log and convergence_log[-1].get("report_path"):
                report_path_hint = (
                    f"\n后荣完整检验报告文件路径（请读取该文件获取完整检验意见）：\n"
                    f"{convergence_log[-1]['report_path']}\n"
                )
            # 将完整检验报告序列化给 houwang，确保它看到结构化结果
            last_result = convergence_log[-1] if convergence_log else {}
            last_result_json = _json.dumps(last_result, ensure_ascii=False, indent=2) if last_result else "{}"
            change_hint = ""
            if len(convergence_log) >= 2:
                prev_detail = convergence_log[-2]["detail"]
                if prev_detail and len(fix_detail or "") < len(prev_detail) * 0.5:
                    change_hint = "（较上一轮检验意见长度减少超50%，收敛趋势良好，继续改进即可）"
                elif prev_detail and fix_detail == prev_detail:
                    change_hint = "（本轮与上轮检验意见相同——请确保已实际修复所有指出的问题，不要遗漏）"
            prompt = (
                f"你是资深软件架构师后旺（HouWang），代号 {houwang_role}，专门负责{label}。\n\n"
                f"后荣（HouRong）的完整检验报告：\n"
                f"```json\n{last_result_json}\n```\n\n"
                f"{report_path_hint}"
                f"=== 当前已有文档 ===\n{current_content[:5000]}\n\n"
                f"=== 后荣详细检验意见 ===\n{fix_detail}\n\n"
                f"{change_hint}\n"
                f"=== 需求文档（供参考）===\n{requirement[:3000]}\n\n"
                "⚠️ 收敛性要求（极其重要）：\n"
                "1. **只**修改后荣报告中指出的不合格项，其他部分一律不变\n"
                "2. 如果后荣说某标准已通过，绝对不要修改相关内容\n"
                "3. 禁止添加新功能、新需求\n"
                "4. 每个修改必须对应一个后荣指出的具体问题\n\n"
                f"将修正后的完整文档保存到：{gen_path}\n"
                "要求：\n"
                "1. 文档必须是独立完整的 Markdown 文件\n"
                "2. 不要包含推理过程\n"
            )
            await broadcast(project_id, {
                "type": "stage",
                "message": f"🔧 {label}：{houwang_role} 正在根据 hourong 检验意见修复（第{fix_round}轮）...",
                "subflow": dim["key"],
            })

        # 调用 houwang（项目会话隔离）
        houwang_cli = GatewayClient(
            profile_name="houwang",
            timeout=2700 if fix_round <= 1 else 1200,
        )
        houwang_chunks = []
        async for chunk in houwang_cli.chat_isolated(
            messages=[{"role": "user", "content": prompt}],
            project_id=project_id,
            project_name=project_name,
            project_description=project_description,
            core_goal=core_goal,
            agent_name=houwang_label,
            stream=True, max_tokens=64000,
            project_slug=slug,
        ):
            if chunk.strip():
                houwang_chunks.append(chunk)
                await broadcast(project_id, {
                    "type": "content",
                    "content": chunk,
                    "subflow": dim["key"],
                })

        # 从磁盘读取修复后的文档（houwang 可能已保存到文件）
        # 如果文件不存在，使用流式输出作为文档内容（防止截断丢失）
        if os.path.exists(gen_path):
            try:
                with open(gen_path, "r", encoding="utf-8") as f:
                    current_content = f.read()
                current_path = gen_path
            except Exception:
                pass
        else:
            streamed = "".join(houwang_chunks).strip()
            if streamed:
                current_content = streamed
                current_path = gen_path
                await broadcast(project_id, {
                    "type": "stage",
                    "message": f"📝 {label}：流式输出已作为文档内容保存（{len(current_content)} 字符）",
                    "subflow": dim["key"],
                })
            else:
                await broadcast(project_id, {
                    "type": "stage",
                    "message": f"⚠️ {label}：{houwang_role} 未保存文件到 {gen_path}，尝试查找最新版本",
                    "subflow": dim["key"],
                })
                for f in sorted(glob.glob(os.path.join(docs_dir, f"{slug}_{doc_type}_V*.md")), reverse=True):
                    try:
                        with open(f, "r", encoding="utf-8") as fh:
                            current_content = fh.read()
                        current_path = f
                        if current_content.strip():
                            break
                    except Exception:
                        pass

        if not current_content.strip():
            await broadcast(project_id, {
                "type": "stage",
                "message": f"❌ {label}：houwang 未能生成有效内容，进入下一轮重试",
                "subflow": dim["key"],
            })
            continue

        # ── hourong 检验（带上轮反馈做收敛） ──
        await broadcast(project_id, {
            "type": "stage",
            "message": f"🔍 hourong-{doc_type} 正在检验{label}...（文件：{current_path}）",
            "subflow": dim["key"],
        })
        prev_fb = convergence_log[-1]["detail"] if convergence_log else ""
        result = await _inspect_doc(
            project_id, current_path or "", dim,
            project_name=project_name, project_description=project_description,
            core_goal=core_goal, agent_label=hourong_label,
            standards=cfg.get("standards", []),
            prev_feedback=prev_fb,
            docs_dir=docs_dir,
        )

        # 检查 inspect 结果是否有效
        if not _result_is_valid(result):
            await broadcast(project_id, {
                "type": "stage",
                "message": f"⚠️ {label}：hourong 第{fix_round}轮未返回有效检验报告，跳过本轮收敛，houwang 将基于最新文档内容继续修复",
                "subflow": dim["key"],
            })
            # 不追加无效结果到 convergence_log，继续下一轮
            continue

        _append_convergence(fix_round, result)

        if result["passed"]:
            await broadcast(project_id, {
                "type": "stage",
                "message": f"✅ {label}：hourong-{doc_type} 检验通过（共{fix_round}轮）",
                "subflow": dim["key"],
            })
            return {
                "key": dim["key"], "label": label,
                "path": current_path, "content": current_content,
                "passed": True, "rounds": fix_round,
                "convergence": convergence_log,
            }
        else:
            prev_count = sum(1 for c in convergence_log[:-1] if not c.get("passed", False))
            if prev_count > 0 and len(convergence_log) >= 3:
                # 检验连续是否收敛：最近3个非通过轮次的 detail 长度是否递减
                non_passing = [c for c in convergence_log if not c.get("passed", False)]
                if len(non_passing) >= 3:
                    lens = [len(c["detail"]) for c in non_passing[-3:]]
                    if lens[-1] >= lens[-2] and lens[-2] >= lens[-3]:
                        await broadcast(project_id, {
                            "type": "stage",
                            "message": f"⚠️ {label}：连续3轮检验意见未收敛（detail长度未递减），houwang 需更彻底地修复问题",
                            "subflow": dim["key"],
                        })

            await broadcast(project_id, {
                "type": "stage",
                "message": f"❌ {label}：hourong-{doc_type} 第{fix_round}轮检验未通过\n📋 意见：{result.get('detail','')[:150]}",
                "subflow": dim["key"],
            })

    # 超出最大尝试次数
    await broadcast(project_id, {
        "type": "stage",
        "message": f"❌ {label}：经过{max_attempts}轮仍未通过 hourong 检验",
        "subflow": dim["key"],
    })
    return {
        "key": dim["key"], "label": label,
        "path": current_path, "content": current_content,
        "passed": False, "rounds": max_attempts,
        "convergence": convergence_log,
    }


# ── 跨文档一致性检验 ──

async def _cross_check_docs(
    project_id: str,
    docs_map: dict,
    project_name: str = "", project_description: str = "",
    core_goal: str = "",
) -> dict:
    """调用 hourong 对4份文档进行跨文档一致性/对应性检验
    docs_map 的 value 为文档文件路径，hourong Agent 自行读取文件。
    """
    from app.api.ws.step3_qa import _inspect_via_subagent
    from app.api.ws.step4_progress import broadcast
    import json as _json

    arch_path = docs_map.get("arch_reasonableness", "")
    frontend_path = docs_map.get("frontend_feasibility", "")
    backend_path = docs_map.get("backend_feasibility", "")
    db_path = docs_map.get("database_design", "")

    prompt = (
        "你是一个跨文档一致性检验专家（后荣）。以下4份设计文档属于同一个项目：\n\n"
        "=== 1. 软件架构设计文档（Architecture Design）===\n"
        f"文件路径：{arch_path}\n\n"
        "=== 2. 软件前端设计文档（Frontend Design）===\n"
        f"文件路径：{frontend_path}\n\n"
        "=== 3. 软件后端设计文档（Backend Design）===\n"
        f"文件路径：{backend_path}\n\n"
        "=== 4. 软件数据库设计脚本（Database Design）===\n"
        f"文件路径：{db_path}\n\n"
        "请依次读取以上4份文档文件，然后逐项检查以下配对的一致性/对应性：\n"
        "1. 架构设计文档 ←→ 前端设计文档：前端技术栈、组件划分、通信方式是否与架构设计一致\n"
        "2. 架构设计文档 ←→ 后端设计文档：后端模块划分、API风格、部署方式是否与架构设计一致\n"
        "3. 前端设计文档 ←→ 后端设计文档：API接口定义、请求/响应数据格式是否在前端和后端文档中一致\n"
        "4. 后端设计文档 ←→ 数据库设计脚本：数据模型、实体名称、字段名、字段类型是否在后端和数据库文档中一致\n\n"
        "仅输出以下JSON对象，不要有其他文字：\n"
        '{\n'
        '  "passed": true/false,\n'
        '  "pairs": [\n'
        '    {\n'
        '      "name": "架构-前端",\n'
        '      "passed": true/false,\n'
        '      "issue": "具体不一致的描述（如无问题留空）",\n'
        '      "affected_docs": ["arch_reasonableness", "frontend_feasibility"]\n'
        '    },\n'
        '    {\n'
        '      "name": "架构-后端",\n'
        '      "passed": true/false,\n'
        '      "issue": "具体不一致的描述",\n'
        '      "affected_docs": ["arch_reasonableness", "backend_feasibility"]\n'
        '    },\n'
        '    {\n'
        '      "name": "前端-后端",\n'
        '      "passed": true/false,\n'
        '      "issue": "具体不一致的描述",\n'
        '      "affected_docs": ["frontend_feasibility", "backend_feasibility"]\n'
        '    },\n'
        '    {\n'
        '      "name": "后端-数据库",\n'
        '      "passed": true/false,\n'
        '      "issue": "具体不一致的描述",\n'
        '      "affected_docs": ["backend_feasibility", "database_design"]\n'
        '    }\n'
        '  ],\n'
        '  "summary": "一致性检验总结"\n'
        '}\n'
        "注意：所有检验仅针对这4份文档之间的一致性/对应性，不检查文档内容与需求的一致性。"
    )

    await broadcast(project_id, {
        "type": "stage",
        "message": "🔍 hourong 正在对4份设计文档进行跨文档一致性检验（架构-前端、架构-后端、前端-后端、后端-数据库）...",
    })

    resp = await _inspect_via_subagent(prompt=prompt, max_retries=3)

    if not resp:
        return {"passed": False, "pairs": [], "summary": "后荣未返回一致性检验结果（空响应）"}

    # Extract JSON from hourong response — try multiple strategies
    _re = __import__('re')
    single = {}
    candidates = []

    # Strategy 1: Strip markdown code fences
    fenced = _re.findall(r'```(?:json)?\s*\n?(.*?)\n?```', resp, _re.DOTALL)
    for fc in fenced:
        candidates.append(fc.strip())

    # Strategy 2: Brace extraction
    brace_start = resp.find('{')
    brace_end = resp.rfind('}')
    if brace_start != -1 and brace_end != -1 and brace_end > brace_start:
        candidates.append(resp[brace_start:brace_end+1])

    # Strategy 3: Full string
    candidates.append(resp)

    for candidate in candidates:
        try:
            parsed = _json.loads(candidate)
            if isinstance(parsed, dict) and parsed:
                single = parsed
                break
        except Exception:
            continue

    if not single:
        logger.warning(f"cross_check_docs 解析失败: {resp[:300]}")
        return {"passed": False, "pairs": [], "summary": "后荣返回结果无法解析"}

    pairs = single.get("pairs", [])
    all_passed = all(p.get("passed", False) for p in pairs) if pairs else False

    for pair in pairs:
        await broadcast(project_id, {
            "type": "stage",
            "message": f"{'✅' if pair.get('passed') else '❌'} {pair.get('name','')}: {pair.get('issue','')[:200]}" if not pair.get('passed') else f"✅ {pair['name']}: 一致",
            "subflow": pair.get("affected_docs", [None])[0] if pair.get("affected_docs") else None,
        })

    return {
        "passed": all_passed,
        "pairs": pairs,
        "summary": single.get("summary", ""),
    }


async def _fix_doc_from_consistency_feedback(
    project_id: str, slug: str, docs_dir: str,
    cfg: dict, requirement: str,
    current_content: str, consistency_feedback: str,
    project_name: str = "", project_description: str = "",
    core_goal: str = "",
    max_attempts: int = 3,
) -> dict:
    """根据一致性检验反馈修复单个文档并通过 hourong 个体检验"""
    import os, glob, re
    from app.services.gateway_client import GatewayClient
    from app.api.ws.step4_progress import broadcast

    doc_type = cfg["doc_type"]
    label = cfg["label"]
    dim = cfg["dim"]
    houwang_label = f"后旺-{doc_type}（HouWang-{doc_type}）{label}设计师"
    hourong_label = f"后荣-{doc_type}（HouRong-{doc_type}）{label}QA检验员"

    max_ver = 0
    for f in sorted(glob.glob(os.path.join(docs_dir, f"{slug}_{doc_type}_V*.md"))):
        m = re.search(r'_V(\d+)\.md$', f)
        if m:
            v = int(m.group(1))
            if v > max_ver:
                max_ver = v

    content = current_content
    path = None
    convergence_log = []

    for attempt in range(1, max_attempts + 1):
        nv = max_ver + attempt
        gen_path = os.path.join(docs_dir, f"{slug}_{doc_type}_V{nv}.md")

        await broadcast(project_id, {
            "type": "stage",
            "message": f"🔧 {label}：houwang 正在根据一致性检验反馈修复一致性问题（第{attempt}轮）...",
            "subflow": dim["key"],
        })

        prompt = (
            f"你是资深软件架构师后旺（HouWang），代号 houwang-{doc_type}，专门负责{label}。\n\n"
            f"跨文档一致性检验发现以下一致性问题需要修正：\n\n"
            f"{consistency_feedback}\n\n"
            f"=== 当前文档（{label}） ===\n{content[:5000]}\n\n"
            f"=== 需求文档（供参考）===\n{requirement[:3000]}\n\n"
            f"请根据一致性检验意见严格修正当前文档（{label}），"
            f"确保与其他设计文档对应一致，"
            f"并将修正后的完整文档保存到：{gen_path}\n"
            "⚠️ 严格限制：\n"
            "1. **只**修改当前文档（{label}）本身，禁止修改其他子步骤的文档\n"
            "2. 只针对一致性问题修改，禁止扩大修改范围\n"
            "3. 文档必须是独立完整的 Markdown 文件\n"
            "4. 不要包含推理过程"
        )

        houwang_cli = GatewayClient(profile_name="houwang", timeout=1200)
        houwang_chunks = []
        async for chunk in houwang_cli.chat_isolated(
            messages=[{"role": "user", "content": prompt}],
            project_id=project_id,
            project_name=project_name,
            project_description=project_description,
            core_goal=core_goal,
            agent_name=houwang_label,
            stream=True, max_tokens=64000,
            project_slug=slug,
        ):
            if chunk.strip():
                houwang_chunks.append(chunk)
                await broadcast(project_id, {
                    "type": "content",
                    "content": chunk,
                    "subflow": dim["key"],
                })

        # 从磁盘读取修复后的文档（houwang 可能已保存到文件）
        # 如果文件不存在，使用流式输出作为修复内容
        if os.path.exists(gen_path):
            try:
                with open(gen_path, "r", encoding="utf-8") as f:
                    content = f.read()
                path = gen_path
            except Exception:
                pass
        else:
            streamed = "".join(houwang_chunks).strip()
            if streamed:
                content = streamed

        if not content.strip():
            await broadcast(project_id, {
                "type": "stage",
                "message": f"⚠️ {label}：houwang 修复后内容为空，重试",
                "subflow": dim["key"],
            })
            continue

        # hourong 个体检验（带上轮反馈做收敛）
        await broadcast(project_id, {
            "type": "stage",
            "message": f"🔍 hourong-{doc_type} 正在重新检验{label}的一致性修复...（文件：{path}）",
            "subflow": dim["key"],
        })
        prev_fb = convergence_log[-1]["detail"] if convergence_log else ""
        result = await _inspect_doc(
            project_id, path or "", dim,
            project_name=project_name, project_description=project_description,
            core_goal=core_goal, agent_label=hourong_label,
            standards=cfg.get("standards", []),
            prev_feedback=prev_fb,
            docs_dir=docs_dir,
        )
        convergence_log.append({"round": attempt, "detail": result.get("detail", ""), "passed": result["passed"], "report_path": result.get("report_path", "")})
        if result["passed"]:
            await broadcast(project_id, {
                "type": "stage",
                "message": f"✅ {label}：hourong 个体检验通过（一致性修复第{attempt}轮）",
                "subflow": dim["key"],
            })
            return {
                "key": dim["key"], "label": label,
                "path": path, "content": content,
                "passed": True, "rounds": attempt,
            }
        else:
            await broadcast(project_id, {
                "type": "stage",
                "message": f"❌ {label}：hourong 个体检验未通过（{result.get('detail','')[:120]}），继续修复",
                "subflow": dim["key"],
            })

    return {
        "key": dim["key"], "label": label,
        "path": path, "content": content,
        "passed": False, "rounds": max_attempts,
    }


# ── 增量一致性检验（按子步骤只检验相关配对） ──

async def _check_consistency_pairs(
    project_id: str,
    docs_map: dict,
    pairs: list,
    project_name: str = "", project_description: str = "",
    core_goal: str = "",
) -> dict:
    """按子步骤增量检验：只检查当前步骤指定的配对"""
    from app.api.ws.step3_qa import _inspect_via_subagent
    from app.api.ws.step4_progress import broadcast
    import json as _json

    doc_sections = []
    doc_labels = {}
    for key, path in docs_map.items():
        cfg = next((c for c in SUB_FLOW_CONFIGS if c["dim"]["key"] == key), None)
        label = cfg["label"] if cfg else key
        doc_labels[key] = label
        doc_sections.append(f"=== {label} ===\n文件路径：{path}")

    pair_items = []
    pair_descs = []
    for pair in pairs:
        a_label = doc_labels.get(pair["a"], pair["a"])
        b_label = doc_labels.get(pair["b"], pair["b"])
        pair_descs.append(f"- {pair['name']}：{a_label}与{b_label}之间的关键约定（API接口、数据模型、组件名、字段名等）是否一致" + "\n")
        _pname = pair["name"]
        _pa = pair["a"]
        _pb = pair["b"]
        pair_items.append(
            '    {\n'
            f'      "name": "{_pname}",\n'
            '      "passed": true/false,\n'
            '      "issue": "具体不一致的描述（如无问题留空）",\n'
            f'      "affected_docs": ["{_pa}", "{_pb}"]\n'
            '    }'
        )

    _nl = chr(10)
    _pairs_json = (_nl + ',' ).join(pair_items)
    prompt = (
        "你是一个跨文档一致性检验专家（后荣）。以下设计文档属于同一个项目：\n\n"
        f"{chr(10).join(doc_sections)}\n\n"
        "请依次读取以上文档文件，然后逐项检查以下配对的一致性/对应性：\n"
        f"{''.join(pair_descs)}\n"
        "仅输出以下JSON对象，不要有其他文字：\n"
        '{\n'
        '  "passed": true/false,\n'
        '  "pairs": [\n'
        f"{_pairs_json}\n"
        '  ],\n'
        '  "summary": "一致性检验总结"\n'
        '}'
    )

    await broadcast(project_id, {
        "type": "stage",
        "message": "🔍 hourong 正在对已完成的文档进行增量一致性检验...",
    })

    resp = await _inspect_via_subagent(prompt=prompt, max_retries=3)

    if not resp:
        return {"passed": False, "pairs": [], "summary": "后荣未返回一致性检验结果（空响应）"}

    _re = __import__('re')
    single = {}
    candidates = []

    fenced = _re.findall(r'```(?:json)?\s*\n?(.*?)\n?```', resp, _re.DOTALL)
    for fc in fenced:
        candidates.append(fc.strip())

    brace_start = resp.find('{')
    brace_end = resp.rfind('}')
    if brace_start != -1 and brace_end != -1 and brace_end > brace_start:
        candidates.append(resp[brace_start:brace_end + 1])

    candidates.append(resp)

    for candidate in candidates:
        try:
            parsed = _json.loads(candidate)
            if isinstance(parsed, dict) and parsed:
                single = parsed
                break
        except Exception:
            continue

    if not single:
        logger.warning(f"_check_consistency_pairs 解析失败: {resp[:300]}")
        return {"passed": False, "pairs": [], "summary": "后荣返回结果无法解析"}

    pairs_result = single.get("pairs", [])
    all_passed = all(p.get("passed", False) for p in pairs_result) if pairs_result else False

    for pair in pairs_result:
        await broadcast(project_id, {
            "type": "stage",
            "message": f"{'✅' if pair.get('passed') else '❌'} {pair.get('name','')}: {pair.get('issue','')[:200]}" if not pair.get('passed') else f"✅ {pair['name']}: 一致",
        })

    return {
        "passed": all_passed,
        "pairs": pairs_result,
        "summary": single.get("summary", ""),
    }


@router.post("/{project_id}/step4/execute")
async def execute_step4(project_id: str,
                        db: Session = Depends(get_db),
                        current_user=Depends(get_current_user),
                        resume: bool = False):
    """异步启动第4步——协调4个子步骤串行执行，聚合设计文档后推进至第5步。
    支持断点续做：自动从数据库读取已有进度，跳过已完成子步骤，从未完成的子步骤继续。
    """
    import asyncio as _asyncio

    try:
        engine = _get_engine(project_id, db)
        existing_artifacts = engine.get_step4_artifacts() or {}
        has_progress = any(
            existing_artifacts.get(k) and existing_artifacts[k].get("passed")
            for k in ["step4_1_result", "step4_2_result", "step4_3_result", "step4_4_result"]
        )
        if resume or has_progress:
            # 断点续做：保留已有成果
            await broadcast(project_id, {
                "type": "stage",
                "message": "♻️ 检测到已有进度，断点续做模式",
            })
        else:
            step4_row = engine._get_step_row(4)
            if step4_row and step4_row.status == "in_progress":
                engine.reset_step(4)
                engine = WorkflowEngine(project_id=project_id, db=db)
                _wf_engines[project_id] = engine
            engine.advance_step(4)
            existing_artifacts = {}
    except Exception as e:
        return APIResponse(code=1, message=f"无法开始步骤4: {str(e)[:200]}")

    step3 = engine.get_step3_artifacts() or {}
    requirement = (step3.get("doc_content") or step3.get("content") or
                   step3.get("requirement") or step3.get("srs") or "")
    if not requirement:
        if not resume and not has_progress:
            engine.reset_step(4)
        return APIResponse(code=1, message="未找到 Step3 需求文档，请先完成需求分析")

    engine.save_step4_artifacts({
        **existing_artifacts,
        "status": "generating",
        "message": "🚀 step4 orchestration: step4_1→架构→step4_2→前端→step4_3→后端→step4_4→数据库",
    })

    # ── 子步骤定义 ──
    SUB_STEP_ORDER = [
        {"step": 1, "key": "step4_1_result", "dim_key": "arch_reasonableness",
         "run_name": "run_sub_step_4_1", "module": "app.api.workflow.step4_1",
         "label": "架构设计"},
        {"step": 2, "key": "step4_2_result", "dim_key": "frontend_feasibility",
         "run_name": "run_sub_step_4_2", "module": "app.api.workflow.step4_2",
         "label": "前端设计"},
        {"step": 3, "key": "step4_3_result", "dim_key": "backend_feasibility",
         "run_name": "run_sub_step_4_3", "module": "app.api.workflow.step4_3",
         "label": "后端设计"},
        {"step": 4, "key": "step4_4_result", "dim_key": "database_design",
         "run_name": "run_sub_step_4_4", "module": "app.api.workflow.step4_4",
         "label": "数据库设计"},
    ]

    async def _run_orchestration():
        """后台任务：串行调用子步骤，汇总后推进至step5"""
        try:
            from app.database import SessionLocal
            from app.api.ws.step4_progress import broadcast
            from app.models.project import Project as _Project

            bg_db = SessionLocal()
            try:
                bg_engine = WorkflowEngine(project_id=project_id, db=bg_db, auto_supervise=False)
                proj = bg_db.query(_Project).filter(_Project.id == project_id).first()
                if not proj:
                    raise Exception("项目不存在")

                slug = proj.slug if proj.slug else project_id.replace("-", "")
                docs_dir = os.path.join(settings.PROJECTS_BASE_DIR, slug, "docs")
                os.makedirs(docs_dir, exist_ok=True)

                step2 = bg_engine.get_step2_artifacts() or {}
                core_goal = step2.get("confirmed_goal") or step2.get("core_goal") or ""
                proj_name = proj.name or ""
                proj_desc = proj.description or ""

                step3 = bg_engine.get_step3_artifacts() or {}
                doc_path = step3.get("doc_path", "")

                all_passed = True
                all_results = {}

                for sub in SUB_STEP_ORDER:
                    step_label = f"step4_{sub['step']}"

                    # 续跑跳过
                    artifacts = bg_engine.get_step4_artifacts() or {}
                    saved = artifacts.get(sub["key"]) or {}
                    if saved.get("passed"):
                        all_results[sub["key"]] = saved
                        await broadcast(project_id, {
                            "type": "stage",
                            "message": f"♻️ {step_label}: {sub['label']}已通过，跳过",
                            "subflow": sub["dim_key"],
                        })
                        continue

                    # ⚠️ 严格串行：启动前确认前一个子步骤已完成
                    if sub["step"] > 1:
                        prev_key = SUB_STEP_ORDER[sub["step"] - 2]["key"]
                        prev_artifact = bg_engine.get_step4_artifacts().get(prev_key) or {}
                        prev_content_key = f"{prev_key}_content"
                        prev_content = bg_engine.get_step4_artifacts().get(prev_content_key, "")
                        if not prev_artifact.get("passed"):
                            err_msg = f"❌ {step_label}: 前序子步骤 {SUB_STEP_ORDER[sub['step'] - 2]['label']} 未通过，禁止启动"
                            await broadcast(project_id, {"type": "error", "message": err_msg, "subflow": sub["dim_key"]})
                            all_passed = False
                            break
                        if not prev_artifact.get("path") and not prev_content:
                            err_msg = f"❌ {step_label}: 前序子步骤的文档成果未保存，禁止启动"
                            await broadcast(project_id, {"type": "error", "message": err_msg, "subflow": sub["dim_key"]})
                            all_passed = False
                            break

                    # 保存当前执行进度到数据库（断点续做用）
                    bg_engine.save_step4_artifacts({
                        "current_step": sub["step"],
                        "current_key": sub["key"],
                        "current_label": sub["label"],
                    })

                    await broadcast(project_id, {
                        "type": "stage",
                        "message": f"🚀 {step_label}: 启动{sub['label']}子步骤...",
                        "subflow": sub["dim_key"],
                    })

                    # 构造前序文档映射（从已有成果中读取 content/path）
                    prev_docs_map = {}
                    if sub["step"] >= 2:
                        for prev_sub in SUB_STEP_ORDER[:sub["step"] - 1]:
                            prev_content_key = f"{prev_sub['key']}_content"
                            prev_content = bg_engine.get_step4_artifacts().get(prev_content_key, "")
                            prev_result = artifacts.get(prev_sub["key"]) or all_results.get(prev_sub["key"]) or {}
                            if prev_result.get("path"):
                                prev_docs_map[prev_sub["dim_key"]] = prev_result["path"]
                            elif prev_content:
                                # 如有 content 但无 path，临时写文件
                                fallback_path = os.path.join(docs_dir, f"{slug}_{prev_sub['dim_key']}_V1.md")
                                with open(fallback_path, "w", encoding="utf-8") as f:
                                    f.write(prev_content)
                                prev_docs_map[prev_sub["dim_key"]] = fallback_path

                    # 动态导入并运行子步骤（await = 串行阻塞）
                    import importlib as _il
                    mod = _il.import_module(sub["module"])
                    run_fn = getattr(mod, sub["run_name"])

                    if sub["step"] == 1:
                        result = await run_fn(
                            project_id=project_id, slug=slug, docs_dir=docs_dir,
                            requirement=requirement, project_name=proj_name,
                            project_description=proj_desc, core_goal=core_goal,
                        )
                    else:
                        result = await run_fn(
                            project_id=project_id, slug=slug, docs_dir=docs_dir,
                            requirement=requirement, project_name=proj_name,
                            project_description=proj_desc, core_goal=core_goal,
                            prev_docs_map=prev_docs_map,
                        )

                    all_results[sub["key"]] = result
                    # 保存完整子步骤成果（含 content/detail/score，供后续子步骤读取）
                    save_data = {
                        "key": result["key"], "label": result.get("label", ""),
                        "path": result.get("path", ""), "passed": result["passed"],
                        "rounds": result.get("rounds", 0),
                        "content": result.get("content", ""),
                        "detail": result.get("detail", ""),
                        "score": result.get("score", 0),
                        "convergence": result.get("convergence", []),
                    }
                    bg_engine.save_step4_artifacts({
                        sub["key"]: save_data,
                        f"{sub['key']}_content": result.get("content", ""),
                        "message": f"{step_label}: {sub['label']} {'通过' if result['passed'] else '未通过'}",
                    })

                    if not result["passed"]:
                        all_passed = False
                        await broadcast(project_id, {
                            "type": "stage",
                            "message": f"❌ {step_label}: {sub['label']}未通过，终止后续子步骤",
                            "subflow": sub["dim_key"],
                        })
                        break

                # ── 汇总结果 ──
                design_parts = []
                final_paths = {}
                step4_1 = all_results.get("step4_1_result") or {}
                step4_2 = all_results.get("step4_2_result") or {}
                step4_3 = all_results.get("step4_3_result") or {}
                step4_4 = all_results.get("step4_4_result") or {}

                for r in [step4_1, step4_2, step4_3, step4_4]:
                    if r and r.get("passed"):
                        content = r.get("content", "")
                        if not content.strip() and r.get("path", ""):
                            try:
                                with open(r["path"], "r", encoding="utf-8") as f:
                                    content = f.read()
                            except Exception:
                                pass
                        if content.strip():
                            design_parts.append(f"# {r.get('label', '')}\n\n{content}")
                            final_paths[r["key"]] = r.get("path", "")

                full_design = "\n\n---\n\n".join(design_parts) if design_parts else ""
                passed_count = sum(1 for r in all_results.values() if r.get("passed"))

                if full_design and len(full_design) >= 50:
                    artifacts = {
                        "design_doc": full_design,
                        "requirement_source": requirement[:200],
                        "status": "done",
                        "message": f"✅ 架构设计完成（{passed_count}/4 通过）",
                        "docs_dir": docs_dir,
                        "doc_paths": final_paths,
                    }
                    if doc_path:
                        artifacts["requirement_doc_path"] = doc_path

                    if all_passed:
                        bg_engine.save_step4_artifacts({**artifacts, "qa_passed": True, "qa_checked": True})
                        bg_engine.complete_step(4, artifacts={**artifacts, "qa_passed": True})
                        await broadcast(project_id, {
                            "type": "done",
                            "message": "✅ 全部4个子步骤通过hourong QA检验与一致性检验，已推进至第5步",
                        })
                    else:
                        bg_engine.save_step4_artifacts({
                            **artifacts, "qa_passed": False, "qa_checked": True, "status": "qa_failed",
                        })
                        await broadcast(project_id, {
                            "type": "done",
                            "message": f"⚠️ {4 - passed_count} 份文档未通过检验",
                        })
                else:
                    bg_engine.save_step4_artifacts({"status": "error", "message": "❌ 子步骤未生成有效设计文档"})
                    bg_engine.reset_step(4)
                    await broadcast(project_id, {"type": "error", "message": "❌ 子步骤未生成有效设计文档"})

            except Exception as e:
                logger.error(f"Step4 orchestration failed: {e}")
                try:
                    eng = WorkflowEngine(project_id=project_id, db=bg_db)
                    eng.save_step4_artifacts({"status": "error", "message": f"❌ 执行失败: {str(e)[:200]}"})
                    eng.reset_step(4)
                except Exception:
                    pass
                try:
                    await broadcast(project_id, {"type": "error", "message": f"❌ 执行失败: {str(e)[:200]}"})
                except Exception:
                    pass
            finally:
                bg_db.close()
        except Exception as e:
            logger.error(f"Step4 orchestration fatal: {e}")

    _asyncio.create_task(_run_orchestration())

    response_data = {
        "message": "第四步已启动，4个子步骤串行执行（架构→前端→后端→数据库）",
        "status": "generating",
    }
    if resume:
        existing_results = engine.get_step4_artifacts().get("step4_1_result") or {}
        if existing_results:
            response_data["resume_info"] = "检测到已有进度，将跳过已通过的子步骤"
    return APIResponse(code=0, data=response_data)


class Step4ChatRequest(BaseModel):
    message: str
    messages: list = []


@router.post("/{project_id}/step4/chat")
async def step4_chat(project_id: str, body: Step4ChatRequest,
                     db: Session = Depends(get_db),
                     current_user=Depends(get_current_user)):
    """与后旺（HouWang）架构师对话 - 使用项目隔离模式
    每次对话后自动持久化消息历史到 DB。
    """
    from datetime import datetime, timezone
    logger.info(f"Step4 chat: project_id={project_id}, message={body.message[:50]}")
    from app.services.gateway_client import GatewayClient
    from app.models.project import Project

    try:
        engine = _get_engine(project_id, db)
        step4 = engine.get_step4_artifacts()
        design_context = (step4 or {}).get("design_doc", "")

        project = db.query(Project).filter(Project.id == project_id).first()
        if not project:
            raise HTTPException(status_code=404, detail="Project not found")

        step2 = engine.get_step2_artifacts()
        core_goal = step2.get("confirmed_goal") or step2.get("core_goal") or ""

        messages = body.messages + [{"role": "user", "content": body.message}]

        # 持久化：保存对话进度到 DB
        saved_msgs = step4.get("chat_messages", [])
        saved_msgs.append({"role": "user", "content": body.message, "saved_at": datetime.now(timezone.utc).isoformat()})
        engine.save_step4_artifacts({
            "chat_messages": saved_msgs,
            "last_activity_at": datetime.now(timezone.utc).isoformat(),
        })

        client = GatewayClient(profile_name="houwang", timeout=1200)
        reply_chunks = []
        async for chunk in client.chat_isolated(
            messages=messages,
            project_id=project_id,
            project_name=project.name,
            project_description=project.description or "",
            core_goal=core_goal,
            agent_name="后旺（HouWang）架构师",
            stream=False,
            project_slug=project.slug if project.slug else project_id,
        ):
            reply_chunks.append(chunk)
        reply = "".join(reply_chunks)
        if not reply or len(reply.strip()) < 5:
            return APIResponse(code=1, message="后旺未生成有效回复", data=None)

        saved_msgs.append({"role": "assistant", "content": reply, "saved_at": datetime.now(timezone.utc).isoformat()})
        engine.save_step4_artifacts({
            "chat_messages": saved_msgs,
            "last_reply": reply,
            "last_reply_at": datetime.now(timezone.utc).isoformat(),
        })
        return APIResponse(code=0, message="success", data={"reply": reply})
    except HTTPException:
        raise
    except Exception as e:
        logger.error(f"HouWang chat failed: {e}")
        return APIResponse(code=1, message="与后旺对话失败，请稍后重试", data=None)


@router.post("/{project_id}/step4/save-doc")
def save_step4_doc(project_id: str, body: Step3InspectRequest,
                   db: Session = Depends(get_db),
                   current_user=Depends(get_current_user)):
    """将设计文档保存到本地和代码库"""
    from datetime import datetime

    local_dir = body.save_path or os.path.join(os.getcwd(), "docs", "design")
    os.makedirs(local_dir, exist_ok=True)
    local_filename = body.filename or f"design-{datetime.now().strftime('%Y%m%d%H%M%S')}.md"
    local_path = os.path.join(local_dir, local_filename)
    try:
        with open(local_path, "w", encoding="utf-8") as f:
            f.write(body.content)
        logger.info(f"设计文档已保存到本地: {local_path}")
    except Exception as e:
        logger.error(f"保存设计文档到本地失败: {e}")

    # 同时保存到 WorkflowEngine 产物（供后续步骤读取）
    engine = WorkflowEngine(project_id=project_id, db=db)
    engine.save_step4_artifacts({
        "design_doc": body.content,
        "filename": body.filename or local_filename,
        "local_path": local_path,
        "saved_at": datetime.now().isoformat(),
    })

    from app.models.repo import Repo
    repo = db.query(Repo).filter(Repo.project_id == project_id).first()
    if not repo:
        return APIResponse(code=0, data={
            "message": "设计文档已保存到本地和引擎产物",
            "local_path": local_path,
        })

    from app.services.gitea_client import gitea_client
    try:
        owner = settings.GITEA_ADMIN_USER
        filepath = body.filename or f"docs/design/design-{datetime.now().strftime('%Y%m%d%H%M%S')}.md"
        result = asyncio.run(gitea_client.create_file(
            owner=owner, repo=repo.name,
            filepath=filepath,
            content=body.content,
            message="docs: 提交架构设计文档",
            branch="main",
        ))
        engine.save_step4_artifacts({"filepath": filepath, "commit": result.get("commit", {})})
        return APIResponse(code=0, data={
            "message": "设计文档已保存到本地、代码库和引擎产物",
            "local_path": local_path,
            "filepath": filepath,
            "commit": result.get("commit", {}),
        })
    except Exception as e:
        logger.error(f"保存设计文档到代码库失败: {e}")
        return APIResponse(code=0, data={
            "message": f"设计文档已保存到本地和引擎产物（保存到代码库失败: {e}）",
            "local_path": local_path,
            "filepath": local_filename,
        })


@router.post("/{project_id}/step4/list-docs")
def list_step4_docs(project_id: str, body: DocsListRequest,
                    current_user=Depends(get_current_user)):
    """从设计文档目录读取文档列表"""
    import glob
    docs_path = body.path
    if not docs_path or not os.path.isdir(docs_path):
        return APIResponse(code=0, data={"files": []})

    files = []
    for f in sorted(glob.glob(os.path.join(docs_path, "*.md"))):
        fname = os.path.basename(f)
        try:
            with open(f, "r", encoding="utf-8") as fh:
                content = fh.read()
            files.append({"name": fname, "path": f, "content": content})
        except Exception as e:
            logger.warning(f"读取设计文档失败 {f}: {e}")
            files.append({"name": fname, "path": f, "content": ""})
    return APIResponse(code=0, data={"files": files})


@router.post("/{project_id}/step4/inspect")
async def inspect_step4_design(project_id: str, body: Step3InspectRequest,
                               db: Session = Depends(get_db),
                               current_user=Depends(get_current_user)):
    """后荣（HouRong）对架构设计方案进行QA检验"""
    content = body.content
    if not content or len(content.strip()) < 20:
        return APIResponse(code=0, data={
            "passed": False, "message": "设计文档内容过短",
            "dimensions": [
                {"key": d["key"], "label": d["label"], "description": d["description"],
                 "passed": False, "detail": "内容不足，无法检验"}
                for d in ARCH_DESIGN_DIMENSIONS
            ],
        })

    from app.api.ws.step3_qa import _inspect_via_subagent
    import json as _json

    # 从 SUB_FLOW_CONFIGS 中提取检验标准
    std_lines = []
    for cfg in SUB_FLOW_CONFIGS:
        dim_key = cfg["dim"]["key"]
        dim_label = cfg["dim"]["label"]
        cfg_standards = cfg.get("standards", [])
        std_lines.append(f"【{dim_label} ({dim_key})】")
        for s in cfg_standards:
            std_lines.append(f"  - [{s['weight'].upper()}] {s['name']}：{s['description']}")
    all_standards = "\n".join(std_lines)

    prompt = (
        "你是一个专业的设计方案QA检验员（后荣 / HouRong）。请严格检验以下设计方案。\n\n"
        "=== 设计方案 ===\n"
        f"{content}\n\n"
        "=== 检验项目与标准 ===\n"
        f"{all_standards}\n\n"
        "=== 评分规则（每项标准1-5分）===\n"
        "5 = 完全符合，4 = 良好，3 = 合格，2 = 不足，1 = 严重不达标\n\n"
        "=== 判定规则 ===\n"
        "- 任意 critical 项评分 < 3 → 该维度 passed = false\n"
        "- 2项及以上 major 项评分 < 3 → 该维度 passed = false\n"
        "- 其余情况 → passed = true\n\n"
        "⚠️ 收敛性要求：检验报告必须聚焦于不合格项，明确指出不合格项的问题和修改方向。"
        "后续Agent将只根据你的检验报告修改不合格项，禁止扩大修改范围。"
        "已合格维度不得提出修改要求。\n\n"
        "直接输出 JSON 数组，不要包含其他说明文字：\n"
        "[\n"
        + ",\n".join(
            f'  {{\n'
            f'    "key": "{d["key"]}",\n'
            f'    "passed": true/false,\n'
            f'    "score": 总体评分(1-5),\n'
            f'    "detail": "格式化的完整检验报告文本，包含逐项评分、问题清单、改进建议"\n'
            f'  }}'
            for d in ARCH_DESIGN_DIMENSIONS
        ) + "\n]"
    )

    try:
        reply = await _inspect_via_subagent(prompt=prompt, max_retries=3)
        if not reply:
            raise ValueError("后荣未返回检验结果")

        # Extract JSON from LLM response — try multiple strategies
        import re as _re
        parsed_list = None

        # Strategy 1: Strip markdown code fences (```json ... ```)
        fenced = _re.findall(r'```(?:json)?\s*\n?(.*?)\n?```', reply, _re.DOTALL)
        for fc in fenced:
            try:
                parsed_list = _json.loads(fc.strip())
                if isinstance(parsed_list, list) and parsed_list:
                    break
            except Exception:
                continue

        # Strategy 2: Brace/bracket extraction
        if parsed_list is None:
            bstart = reply.find('[')
            bend = reply.rfind(']')
            if bstart != -1 and bend != -1 and bend > bstart:
                try:
                    parsed_list = _json.loads(reply[bstart:bend+1])
                except Exception:
                    pass

        # Strategy 3: Full string
        if parsed_list is None:
            try:
                parsed_list = _json.loads(reply)
            except Exception:
                pass

        if parsed_list is None or not isinstance(parsed_list, list):
            raise ValueError("返回结果不是数组")
    except Exception as e:
        logger.error(f"后荣检验设计方案失败: {e}")
        return APIResponse(code=0, data={
            "passed": False, "message": "检验过程出错",
            "dimensions": [
                {"key": d["key"], "label": d["label"], "description": d["description"],
                 "passed": False, "detail": f"检验失败: {str(e)[:80]}"}
                for d in ARCH_DESIGN_DIMENSIONS
            ],
        })

    results = []
    for dim in ARCH_DESIGN_DIMENSIONS:
        matched = next((r for r in parsed_list if r.get("key") == dim["key"]), None)
        results.append({
            "key": dim["key"], "label": dim["label"], "description": dim["description"],
            "passed": int(matched.get("score", 100)) >= 90 if matched else False,
            "score": int(matched.get("score", 100)) if matched else 0,
            "detail": matched.get("detail", "未返回该维度检验结果") if matched else "后荣未返回该维度的检验结果",
        })

    from datetime import datetime, timezone
    avg_score = sum(r.get("score", 0) for r in results) / len(results) if results else 0
    all_passed = avg_score > 90
    # 持久化：保存检验结果到 DB
    engine = _get_engine(project_id, db)
    engine.save_step4_artifacts({
        "inspect_result": {
            "passed": all_passed, "avg_score": avg_score, "dimensions": results,
            "inspected_at": datetime.now(timezone.utc).isoformat(),
        },
        "qa_checked": True, "qa_passed": all_passed,
    })
    return APIResponse(code=0, data={
        "passed": all_passed,
        "score": avg_score,
        "message": "所有检验项目均通过 ✅" if all_passed else "部分检验项目未通过",
        "dimensions": results,
    })


@router.post("/{project_id}/step4/qa")
def qa_step4(project_id: str, body: QAResultRequest,
             db: Session = Depends(get_db),
             current_user=Depends(get_current_user)):
    from datetime import datetime, timezone
    engine = _get_engine(project_id, db)
    now_iso = datetime.now(timezone.utc).isoformat()
    if body.result == "passed":
        result = engine.pass_qa(4)
        engine.save_step4_artifacts({"qa_passed": True, "qa_status": "passed", "qa_checked_at": now_iso})
    else:
        result = engine.fail_qa(4, reason=body.reason or "", suggestions=body.suggestions)
        engine.save_step4_artifacts({"qa_passed": False, "qa_status": "failed", "qa_checked_at": now_iso, "qa_fail_reason": body.reason, "qa_suggestions": body.suggestions})
    return APIResponse(code=0, data={"message": f"第四步QA检验{'通过' if body.result == 'passed' else '未通过'}", "qa": result})


@router.post("/{project_id}/step4/reset")
def reset_step4(project_id: str,
                db: Session = Depends(get_db),
                current_user=Depends(get_current_user)):
    """强制重置第四步为待执行状态（用于恢复中断/卡死，清空产物）"""
    engine = _get_engine(project_id, db)
    engine.reset_step(4)
    engine.save_step4_artifacts({"status": "reset", "message": "第四步已重置"})
    if project_id in _wf_engines:
        _wf_engines[project_id] = WorkflowEngine(project_id=project_id, db=db)
    return APIResponse(code=0, data={"message": "第四步已重置为待执行状态，可以重新开始"})


# ==================== Step 5: 后富建立开发环境 ====================

