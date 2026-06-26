from app.api.workflow.core import (
    router, _get_engine, logger, APIResponse, Depends, get_db,
    get_current_user, Session, Body, Request, HTTPException,
    BaseModel, Optional, asyncio, os, settings,
    Step3InspectRequest, Step5ChatRequest, QAResultRequest,
    DocsListRequest, ARCH_DESIGN_DIMENSIONS, _wf_engines, WorkflowEngine,
)

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
    dim_key: str, retry_pressure: str = "",
) -> str:
    """构建 hourong 检验提示词（含标准 + 格式化报告要求）"""
    import json as _json
    dim_label = dim["label"]
    dim_desc = dim["description"]

    std_items = "\n".join(
        f"  {i+1}. [{s['weight'].upper()}] {s['name']}：{s['description']}"
        for i, s in enumerate(standards)
    )

    return (
        f"You are a JSON-only API. Your entire response MUST be a single, "
        f"valid JSON object — nothing else.\n\n"
        f"Role: 专业的设计方案 QA 检验员（后荣 / HouRong）\n\n"
        f"=== 检验项目 ===\n"
        f"{dim_label}（{dim_desc}）\n\n"
        f"=== 文档路径 ===\n"
        f"{doc_path}\n\n"
        f"Task: 读取该文档文件，严格对照以下检验标准逐项评分并输出格式化检验报告。\n"
        f"注意：文档文件位于上述路径，请直接读取文件进行完整检验。\n\n"
        f"=== 检验标准与权重 ===\n"
        f"{std_items}\n\n"
        f"=== 评分规则 ===\n"
        f"每项标准按1-5分评分：\n"
        f"  5 = 完全符合（无可挑剔）\n"
        f"  4 = 良好（有小瑕疵但不影响）\n"
        f"  3 = 合格（基本满足，需要改进）\n"
        f"  2 = 不足（有明显缺陷）\n"
        f"  1 = 严重不达标（基本未涉及）\n\n"
        f"=== 判定规则 ===\n"
        f"- 存在任意 critical 权重项评分 < 3 → passed = false\n"
        f"- 存在 2 项及以上 major 权重项评分 < 3 → passed = false\n"
        f"- 其余情况 → passed = true\n\n"
        f"=== OUTPUT JSON FORMAT (STRICT) ===\n"
        f'Output ONLY a JSON object with the following structure:\n'
        f'{{\n'
        f'  "key": "{dim_key}",\n'
        f'  "passed": true/false,\n'
        f'  "detail": "格式化的检验报告文本（见下方要求）",\n'
        f'  "report": {{\n'
        f'    "standards": [\n'
        f'      {{\n'
        f'        "name": "标准名称",\n'
        f'        "score": 1-5,\n'
        f'        "severity": "critical"/"major",\n'
        f'        "comment": "评分说明",\n'
        f'        "issue": "发现的问题（无则留空）"\n'
        f'      }}\n'
        f'    ],\n'
        f'    "overall_score": 3.5,\n'
        f'    "summary": "检验总结",\n'
        f'    "problems": [\n'
        f'      {{"severity": "critical"/"major"/"minor", "description": "问题描述"}}\n'
        f'    ],\n'
        f'    "recommendations": ["改进建议1", "改进建议2"]\n'
        f'  }}\n'
        f'}}\n\n'
        f"=== detail 字段格式要求 ===\n"
        f"detail 字段必须是一个格式化的文本报告，包含以下内容：\n"
        f"1. 报告标题（后荣设计文档检验报告）\n"
        f"2. 检验项目名称\n"
        f"3. 各标准逐项评分（名称、评分、说明）\n"
        f"4. 发现的全部问题列表（含严重程度标记）\n"
        f"5. 总体评分和判定结果\n"
        f"6. 改进建议\n\n"
        f"Example detail format:\n"
        f"========================================\n"
        f"后荣（HouRong）设计文档检验报告\n"
        f"========================================\n"
        f"检验项目: {dim_label}\n"
        f"\n"
        f"【逐项评分】\n"
        f"1. 完整性 [critical] — 评分: 4/5\n"
        f"   说明: 覆盖了主要功能需求\n"
        f"   问题: 非功能需求未充分说明\n"
        f"2. 合理性 [critical] — 评分: 2/5\n"
        f"   说明: 模块划分不够清晰\n"
        f"   问题: 用户模块和订单模块职责重叠\n"
        f"\n"
        f"【问题清单】\n"
        f"- [critical] 模块划分不清晰 — 用户模块和订单模块职责重叠\n"
        f"- [major] 可扩展性不足 — 未考虑未来扩展\n"
        f"\n"
        f"【综合评定】\n"
        f"总体评分: 3.2/5\n"
        f"判定: ❌ 未通过（存在critical项评分<3）\n"
        f"\n"
        f"【改进建议】\n"
        f"1. 重新定义模块边界，明确各模块职责\n"
        f"2. 补充非功能需求覆盖说明\n"
        f"3. 增加扩展性设计\n"
        f"========================================\n\n"
        f"CRITICAL RULES:\n"
        f"1. The JSON object must be the ONLY content in your response.\n"
        f"2. Do NOT include any text before or after the JSON object.\n"
        f"3. Do NOT use markdown code fences (```json ... ```).\n"
        f"4. Do NOT include thinking, reasoning, analysis, or explanation.\n"
        f"5. Do NOT include file content, tool calls, or tool results.\n"
        f"6. Do NOT include greetings, apologies, or any conversational text.\n"
        f"7. Ensure all string values use double quotes and are properly escaped.\n"
        f"8. The JSON must parse successfully without any modifications.\n"
        f"9. After generating the JSON, verify it is valid before outputting.\n"
        f"10. The detail field must contain the full formatted report text.\n"
        f"{retry_pressure}"
        f"Now output the JSON object:"
    )


async def _inspect_doc(
    project_id: str, doc_path: str, dim: dict,
    project_name: str = "", project_description: str = "",
    core_goal: str = "", agent_label: str = "",
    max_retries: int = 3, standards: list = None,
) -> dict:
    """调用 hourong-{doc_type} 对单份文档进行 QA 检验（项目会话隔离）
    将文档路径告知 hourong 让 Agent 自行读取文件，避免在大文档上 context 溢出。
    若 hourong 未返回有效检验报告（空响应/无法解析），自动重试最多 max_retries 次，
    禁止将 hourong 的异常直接当作"检验不通过"传给 houwang 重新生成。
    """
    import json as _json, re as _re, asyncio as _asyncio
    from app.services.gateway_client import GatewayClient
    from app.api.ws.step4_progress import broadcast

    dim_key = dim["key"]
    dim_label = dim["label"]

    for attempt in range(1, max_retries + 1):
        if attempt > 1:
            await _asyncio.sleep(2)
            await broadcast(project_id, {
                "type": "stage",
                "message": f"🔄 hourong 正在第{attempt}次重新检验{dim_label}...",
                "subflow": dim_key,
            })

        # 重试时追加"上次输出无效"批评，强化 JSON 约束
        retry_pressure = ""
        if attempt > 1:
            retry_pressure = (
                f"\n\n⚠️ 你上一次输出包含了无法解析的内容。"
                f"你必须输出一个合法的 JSON 对象，不能再包含其他文字、推理、分析、"
                f"文件内容、工具调用结果或任何解释性说明！\n"
            )

        insp_prompt = _build_inspect_prompt(
            doc_path=doc_path, dim=dim, standards=standards or [],
            dim_key=dim_key, retry_pressure=retry_pressure,
        )
        qa_cli = GatewayClient(profile_name="hourong", timeout=180)
        qa_chunks = []
        async for chunk in qa_cli.chat_isolated(
            messages=[{"role": "user", "content": insp_prompt}],
            project_id=project_id,
            project_name=project_name,
            project_description=project_description,
            core_goal=core_goal,
            agent_name=agent_label or f"后荣-{dim_key} QA检验员",
            stream=True, max_tokens=4096,
        ):
            qa_chunks.append(chunk)
        qa_r = "".join(qa_chunks).strip()

        if not qa_r:
            if attempt < max_retries:
                await broadcast(project_id, {
                    "type": "stage",
                    "message": f"⚠️ hourong 未返回{dim_label}的检验结果（空响应），正在重试（第{attempt}次）",
                    "subflow": dim_key,
                })
                continue
            return {"key": dim_key, "passed": False, "detail": f"后荣{max_retries}次均未返回检验结果（空响应）"}

        # Extract JSON from LLM response — robust multi-strategy extraction
        _re = __import__('re')
        single = {}

        # Strategy 0: Strip thinking/analysis tags (various formats)
        _lt, _gt = chr(60), chr(62)
        _think_open = rf'{_lt}(?:thinking|think|analysis){_gt}'
        _think_close = rf'{_lt}/(?:thinking|think|analysis){_gt}'
        qa_r = _re.sub(rf'(?:{_think_open})[\s\S]*?(?:{_think_close})', '', qa_r)

        # Collect candidates for parsing
        candidates = []

        # Strategy 1: Strip markdown code fences
        fenced = _re.findall(r'```(?:json)?\s*\n?(.*?)\n?```', qa_r, _re.DOTALL)
        for fc in fenced:
            stripped = fc.strip()
            if stripped:
                candidates.append(stripped)

        # Strategy 2: Brace extraction (first { to last })
        brace_start = qa_r.find('{')
        brace_end = qa_r.rfind('}')
        if brace_start != -1 and brace_end != -1 and brace_end > brace_start:
            brace_extracted = qa_r[brace_start:brace_end + 1]
            candidates.append(brace_extracted)

        # Strategy 3: Find JSON-like pattern via regex
        json_like = _re.findall(r'\{[^{}]*(?:\{[^{}]*\}[^{}]*)*\}', qa_r)
        for jl in json_like:
            if len(jl) > 10:
                candidates.append(jl)

        # Strategy 4: Strip non-JSON prefix/suffix
        stripped = qa_r.strip()
        bs2 = stripped.find('{')
        if bs2 > 0:
            candidates.append(stripped[bs2:])
        stripped2 = qa_r.strip()
        be2 = stripped2.rfind('}')
        if be2 >= 0 and be2 < len(stripped2) - 1:
            candidates.append(stripped2[:be2 + 1])

        # Strategy 5: Full string (for pure JSON responses)
        candidates.append(qa_r)

        def _repair_json(text):
            """Fix common JSON formatting issues in LLM output."""
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
            logger.error(f"hourong JSON 解析失败 (attempt {attempt}/{max_retries}): {qa_r[:500]}")
            if attempt < max_retries:
                await broadcast(project_id, {
                    "type": "stage",
                    "message": f"⚠️ hourong 返回了{dim_label}无法解析的检验报告，正在重试（第{attempt}次）",
                    "subflow": dim_key,
                })
                continue
            logger.warning(f"hourong 返回无法解析 (已重试{max_retries}次): {qa_r[:300]}")
            return {"key": dim_key, "passed": False, "detail": "后荣返回了无法解析的检验报告"}

        overall_passed = bool(single.get("passed", False))
        detail_text = single.get("detail", "未返回检验意见")
        return {
            "key": dim_key,
            "passed": overall_passed,
            "detail": detail_text,
        }

    return {"key": dim_key, "passed": False, "detail": "后荣检验失败"}


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
            # 现有不合格，houwang 修复
            await broadcast(project_id, {
                "type": "stage",
                "message": f"📝 {label}：现有文档 V{max_ver} 未通过（{result.get('detail','')[:120]}），houwang 基于此版本更新",
                "subflow": dim["key"],
            })
            convergence_log.append({"round": 0, "detail": result["detail"]})

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
            change_hint = ""
            if len(convergence_log) >= 2:
                prev_detail = convergence_log[-2]["detail"]
                if len(fix_detail) < len(prev_detail) * 0.5:
                    change_hint = "（较上一轮检验意见长度减少超50%，收敛趋势良好，继续改进即可）"
                elif fix_detail == prev_detail:
                    change_hint = "（本轮与上轮检验意见相同——请确保已实际修复所有指出的问题，不要遗漏）"
            prompt = (
                f"你是资深软件架构师后旺（HouWang），代号 {houwang_role}，专门负责{label}。\n\n"
                f"后荣（HouRong）检验发现以下问题需要修改：\n\n"
                f"=== 当前已有文档 ===\n{current_content[:5000]}\n\n"
                f"=== 后荣最新检验意见 ===\n{fix_detail}\n\n"
                f"{change_hint}\n"
                f"=== 需求文档（供参考）===\n{requirement[:3000]}\n\n"
                f"请根据后荣的意见严格修正文档，并将修正后的完整文档保存到：{gen_path}\n"
                "要求：\n"
                "1. 只针对后荣指出的不合格项修改，禁止扩大修改范围，禁止添加新功能\n"
                "2. 文档必须是独立完整的 Markdown 文件\n"
                "3. 不要包含推理过程\n"
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

        # ── hourong 检验 ──
        await broadcast(project_id, {
            "type": "stage",
            "message": f"🔍 hourong-{doc_type} 正在检验{label}...（文件：{current_path}）",
            "subflow": dim["key"],
        })
        result = await _inspect_doc(
            project_id, current_path or "", dim,
            project_name=project_name, project_description=project_description,
            core_goal=core_goal, agent_label=hourong_label,
            standards=cfg.get("standards", []),
        )

        convergence_log.append({"round": fix_round, "detail": result.get("detail", ""), "passed": result["passed"]})

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
    from app.services.gateway_client import GatewayClient
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

    cli = GatewayClient(profile_name="hourong", timeout=300)
    chunks = []
    async for chunk in cli.chat_isolated(
        messages=[{"role": "user", "content": prompt}],
        project_id=project_id,
        project_name=project_name,
        project_description=project_description,
        core_goal=core_goal,
        agent_name="后荣（HouRong）- 跨文档一致性检验员",
        stream=True, max_tokens=4096,
    ):
        chunks.append(chunk)
    resp = "".join(chunks).strip()

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
            f"=== 当前文档 ===\n{content[:5000]}\n\n"
            f"=== 需求文档（供参考）===\n{requirement[:3000]}\n\n"
            f"请根据一致性检验意见严格修正文档，确保与其他设计文档对应一致，"
            f"并将修正后的完整文档保存到：{gen_path}\n"
            "要求：\n"
            "1. 只针对一致性问题修改，禁止扩大修改范围\n"
            "2. 文档必须是独立完整的 Markdown 文件\n"
            "3. 不要包含推理过程"
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

        # hourong 个体检验
        await broadcast(project_id, {
            "type": "stage",
            "message": f"🔍 hourong-{doc_type} 正在重新检验{label}的一致性修复...（文件：{path}）",
            "subflow": dim["key"],
        })
        result = await _inspect_doc(
            project_id, path or "", dim,
            project_name=project_name, project_description=project_description,
            core_goal=core_goal, agent_label=hourong_label,
            standards=cfg.get("standards", []),
        )
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
    from app.services.gateway_client import GatewayClient
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
        pair_descs.append(f"- {pair['name']}：{a_label}与{b_label}之间的关键约定（API接口、数据模型、组件名、字段名等）是否一致\n")
        pair_items.append(
            '    {\n'
            f'      "name": "{pair["name"]}",\n'
            '      "passed": true/false,\n'
            '      "issue": "具体不一致的描述（如无问题留空）",\n'
            f'      "affected_docs": ["{pair["a"]}", "{pair["b"]}"]\n'
            '    }'
        )

    prompt = (
        "你是一个跨文档一致性检验专家（后荣）。以下设计文档属于同一个项目：\n\n"
        f"{chr(10).join(doc_sections)}\n\n"
        "请依次读取以上文档文件，然后逐项检查以下配对的一致性/对应性：\n"
        f"{''.join(pair_descs)}\n"
        "仅输出以下JSON对象，不要有其他文字：\n"
        '{\n'
        '  "passed": true/false,\n'
        '  "pairs": [\n'
        f"{',\n'.join(pair_items)}\n"
        '  ],\n'
        '  "summary": "一致性检验总结"\n'
        '}'
    )

    await broadcast(project_id, {
        "type": "stage",
        "message": "🔍 hourong 正在对已完成的文档进行增量一致性检验...",
    })

    cli = GatewayClient(profile_name="hourong", timeout=300)
    chunks = []
    async for chunk in cli.chat_isolated(
        messages=[{"role": "user", "content": prompt}],
        project_id=project_id,
        project_name=project_name,
        project_description=project_description,
        core_goal=core_goal,
        agent_name="后荣（HouRong）- 跨文档增量一致性检验员",
        stream=True, max_tokens=4096,
    ):
        chunks.append(chunk)
    resp = "".join(chunks).strip()

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
    """异步启动第4步架构设计（4个子步骤串行执行），立即返回
    resume=True: 续跑模式，跳过已通过检验的子步骤，只重跑未通过/失败的
    """
    from app.services.gateway_client import GatewayClient
    import asyncio as _asyncio

    try:
        engine = _get_engine(project_id, db)

        if resume:
            existing = engine.get_step4_artifacts() or {}
        else:
            step4_row = engine._get_step_row(4)
            if step4_row and step4_row.status == "in_progress":
                engine.reset_step(4)
                engine = WorkflowEngine(project_id=project_id, db=db)
                _wf_engines[project_id] = engine
            engine.advance_step(4)
            existing = {}
    except Exception as e:
        return APIResponse(code=1, message=f"无法开始步骤4: {str(e)[:200]}")

    step3 = engine.get_step3_artifacts() or {}
    requirement = (step3.get("doc_content") or step3.get("content") or
                   step3.get("requirement") or step3.get("srs") or "")

    if not requirement:
        if not resume:
            engine.reset_step(4)
        return APIResponse(code=1, message="未找到 Step3 需求文档，请先完成需求分析")

    _existing_artifacts = engine.get_step4_artifacts() or {}
    engine.save_step4_artifacts({
        **_existing_artifacts,
        "status": "generating",
        "message": "🚀 4个子步骤串行启动——step4_1→架构→step4_2→前端→step4_3→后端→step4_4→数据库",
    })

    # ── 4个子步骤定义（串行） ──
    SUB_STEP_DEFS = [
        {
            "step_label": "step4_1",
            "cfg": SUB_FLOW_CONFIGS[0],
            "consistency_pairs": [],
        },
        {
            "step_label": "step4_2",
            "cfg": SUB_FLOW_CONFIGS[1],
            "consistency_pairs": [
                {"name": "架构设计←→前端设计", "a": "arch_reasonableness", "b": "frontend_feasibility"},
            ],
        },
        {
            "step_label": "step4_3",
            "cfg": SUB_FLOW_CONFIGS[2],
            "consistency_pairs": [
                {"name": "架构设计←→后端设计", "a": "arch_reasonableness", "b": "backend_feasibility"},
                {"name": "前端设计←→后端设计", "a": "frontend_feasibility", "b": "backend_feasibility"},
            ],
        },
        {
            "step_label": "step4_4",
            "cfg": SUB_FLOW_CONFIGS[3],
            "consistency_pairs": [
                {"name": "后端设计←→数据库设计", "a": "backend_feasibility", "b": "database_design"},
            ],
        },
    ]

    async def _generate():
        """后台任务：4个子步骤串行执行"""
        try:
            from app.database import SessionLocal
            from app.services.workflow_engine import WorkflowEngine
            from app.api.ws.step4_progress import broadcast

            bg_db = SessionLocal()
            try:
                bg_engine = WorkflowEngine(project_id=project_id, db=bg_db)

                step3 = bg_engine.get_step3_artifacts() or {}
                doc_path = step3.get("doc_path", "")

                from app.config import settings as _settings
                from app.models.project import Project as _Project
                import os as _os

                proj = bg_db.query(_Project).filter(_Project.id == project_id).first()
                slug = proj.slug if proj else project_id.replace("-", "")
                docs_dir = _os.path.join(_settings.PROJECTS_BASE_DIR, slug, "docs")
                _os.makedirs(docs_dir, exist_ok=True)

                step2 = bg_engine.get_step2_artifacts() or {}
                core_goal = step2.get("confirmed_goal") or step2.get("core_goal") or ""
                proj_name = proj.name if proj else ""
                proj_desc = proj.description or ""

                # ── 续跑检测 ──
                existing_sub_results = (bg_engine.get_step4_artifacts() or {}).get("sub_flow_results", [])
                passed_keys = {r["key"] for r in existing_sub_results if r.get("passed")}
                existing_doc_paths = (bg_engine.get_step4_artifacts() or {}).get("doc_paths", {})

                all_results = []
                doc_paths_map = dict(existing_doc_paths)
                all_passed = True

                for sub in SUB_STEP_DEFS:
                    cfg = sub["cfg"]
                    step_label = sub["step_label"]
                    dim_key = cfg["dim"]["key"]

                    if dim_key in passed_keys:
                        preserved = next((r for r in existing_sub_results if r["key"] == dim_key), None)
                        if preserved:
                            all_results.append(preserved)
                            doc_paths_map[dim_key] = existing_doc_paths.get(dim_key, "")
                        await broadcast(project_id, {
                            "type": "stage",
                            "message": f"♻️ {step_label}: {cfg['label']}已通过，跳过",
                            "subflow": dim_key,
                        })
                        continue

                    await broadcast(project_id, {
                        "type": "stage",
                        "message": f"🚀 {step_label}: houwang开始生成{cfg['label']}...",
                        "subflow": dim_key,
                    })

                    # 1. houwang生成 + hourong检验
                    result = await _run_doc_sub_flow(
                        project_id=project_id, slug=slug, docs_dir=docs_dir,
                        cfg=cfg, requirement=requirement,
                        project_name=proj_name, project_description=proj_desc,
                        core_goal=core_goal,
                    )

                    all_results.append(result)
                    if result.get("path"):
                        doc_paths_map[dim_key] = result["path"]

                    bg_engine.save_step4_artifacts({
                        "sub_flow_results": [
                            {"key": r["key"], "label": r.get("label", ""), "passed": r.get("passed", False),
                             "rounds": r.get("rounds", 0), "convergence": r.get("convergence", [])}
                            for r in all_results
                        ],
                        "doc_paths": doc_paths_map,
                        "message": f"{step_label}: {cfg['label']} {'通过' if result['passed'] else '未通过'} hourong检验",
                    })

                    if not result["passed"]:
                        all_passed = False
                        await broadcast(project_id, {
                            "type": "stage",
                            "message": f"❌ {step_label}: {cfg['label']}未通过hourong检验，终止后续子步骤",
                            "subflow": dim_key,
                        })
                        break

                    # 2. 增量一致性检验
                    if sub["consistency_pairs"]:
                        docs_map = {}
                        for ar in all_results:
                            if ar.get("path", "").strip():
                                docs_map[ar["key"]] = ar["path"]

                        for ar in all_results:
                            if not ar.get("content", "").strip() and ar.get("path", ""):
                                try:
                                    with open(ar["path"], "r", encoding="utf-8") as f:
                                        ar["content"] = f.read()
                                except Exception:
                                    pass

                        MAX_CONSISTENCY_ROUNDS = 3
                        consistency_passed = False

                        for cc_round in range(1, MAX_CONSISTENCY_ROUNDS + 1):
                            await broadcast(project_id, {
                                "type": "stage",
                                "message": f"🔄 {step_label}: 跨文档一致性检验第{cc_round}轮——{len(sub['consistency_pairs'])}对一致性",
                                "subflow": dim_key,
                            })

                            check_result = await _check_consistency_pairs(
                                project_id=project_id,
                                docs_map=docs_map,
                                pairs=sub["consistency_pairs"],
                                project_name=proj_name,
                                project_description=proj_desc,
                                core_goal=core_goal,
                            )

                            if check_result["passed"]:
                                consistency_passed = True
                                await broadcast(project_id, {
                                    "type": "stage",
                                    "message": f"✅ {step_label}: 跨文档一致性检验通过（第{cc_round}轮）",
                                    "subflow": dim_key,
                                })
                                break

                            feedback_parts = []
                            for pair in check_result.get("pairs", []):
                                if not pair.get("passed", True) and dim_key in pair.get("affected_docs", []):
                                    feedback_parts.append(f"{pair['name']}: {pair['issue']}")

                            if not feedback_parts:
                                consistency_passed = True
                                break

                            feedback = "\n".join(feedback_parts)
                            await broadcast(project_id, {
                                "type": "stage",
                                "message": f"🔄 {step_label}: houwang根据一致性反馈修复{cfg['label']}（第{cc_round}轮）",
                                "subflow": dim_key,
                            })

                            fix_result = await _fix_doc_from_consistency_feedback(
                                project_id=project_id, slug=slug, docs_dir=docs_dir,
                                cfg=cfg, requirement=requirement,
                                current_content=result.get("content", ""),
                                consistency_feedback=feedback,
                                project_name=proj_name, project_description=proj_desc,
                                core_goal=core_goal,
                            )

                            result = fix_result
                            if fix_result.get("path"):
                                doc_paths_map[dim_key] = fix_result["path"]

                            if fix_result["passed"]:
                                consistency_passed = True
                                await broadcast(project_id, {
                                    "type": "stage",
                                    "message": f"✅ {step_label}: 一致性修复后通过检验",
                                    "subflow": dim_key,
                                })
                                break

                        if not consistency_passed:
                            all_passed = False
                            await broadcast(project_id, {
                                "type": "stage",
                                "message": f"❌ {step_label}: {cfg['label']}一致性检验未通过，终止后续子步骤",
                                "subflow": dim_key,
                            })
                            break

                # ── 汇总结果 ──
                design_parts = []
                final_paths = {}
                for r in all_results:
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
                passed_count = sum(1 for r in all_results if r.get("passed"))
                sub_flow_detail = "; ".join(
                    f"{r.get('label', '')}: {'✅' if r.get('passed') else '❌'}({r.get('rounds', 0)}轮)"
                    for r in all_results
                )

                if full_design and len(full_design) >= 50:
                    artifacts = {
                        "design_doc": full_design,
                        "requirement_source": requirement[:200],
                        "status": "done",
                        "message": f"✅ 架构设计完成（{passed_count}/4 通过）\n{sub_flow_detail}",
                        "docs_dir": docs_dir,
                        "doc_paths": final_paths,
                        "sub_flow_results": [
                            {
                                "key": r.get("key", ""), "label": r.get("label", ""),
                                "passed": r.get("passed", False), "rounds": r.get("rounds", 0),
                                "convergence": r.get("convergence", []),
                            }
                            for r in all_results
                        ],
                    }
                    if doc_path:
                        artifacts["requirement_doc_path"] = doc_path

                    if all_passed:
                        bg_engine.save_step4_artifacts({**artifacts, "qa_passed": True, "qa_checked": True})
                        bg_engine.complete_step(4)
                        bg_engine.pass_qa(4)
                        await broadcast(project_id, {
                            "type": "done",
                            "message": f"✅ 全部4个子步骤通过hourong QA检验与跨文档一致性检验，已推进至第5步",
                        })
                    else:
                        bg_engine.save_step4_artifacts({
                            **artifacts, "qa_passed": False, "qa_checked": True, "status": "qa_failed",
                        })
                        await broadcast(project_id, {
                            "type": "done",
                            "message": f"⚠️ {4 - passed_count} 份文档未通过检验\n{sub_flow_detail}",
                        })
                else:
                    bg_engine.save_step4_artifacts({
                        "status": "error",
                        "message": "❌ 子步骤未生成有效设计文档",
                    })
                    bg_engine.reset_step(4)
                    await broadcast(project_id, {"type": "error", "message": "❌ 子步骤未生成有效设计文档"})
            except Exception as e:
                logger.error(f"Step4 sequential sub-steps failed: {e}")
                try:
                    bg_engine = WorkflowEngine(project_id=project_id, db=bg_db)
                    bg_engine.save_step4_artifacts({
                        "status": "error",
                        "message": f"❌ 串行子步骤执行失败: {str(e)[:200]}",
                    })
                    bg_engine.reset_step(4)
                except Exception:
                    pass
                try:
                    await broadcast(project_id, {"type": "error", "message": f"❌ 串行子步骤执行失败: {str(e)[:200]}"})
                except Exception:
                    pass
            finally:
                bg_db.close()
        except Exception as e:
            logger.error(f"Step4 background task fatal: {e}")

    task = _asyncio.create_task(_generate())

    sub_flow_results = existing.get("sub_flow_results", []) if resume else []
    response_data = {
        "message": "第四步已启动，4个子步骤串行执行（step4_1→架构→step4_2→前端→step4_3→后端→step4_4→数据库）",
        "status": "generating",
    }
    if resume and sub_flow_results:
        response_data["sub_flow_results"] = [
            {"key": r["key"], "label": r.get("label", ""), "passed": r.get("passed", False)}
            for r in sub_flow_results
        ]
    return APIResponse(code=0, data=response_data)


class Step4ChatRequest(BaseModel):
    message: str
    messages: list = []


@router.post("/{project_id}/step4/chat")
async def step4_chat(project_id: str, body: Step4ChatRequest,
                     db: Session = Depends(get_db),
                     current_user=Depends(get_current_user)):
    """与后旺（HouWang）架构师对话 - 使用项目隔离模式"""
    logger.info(f"Step4 chat: project_id={project_id}, message={body.message[:50]}")
    from app.services.gateway_client import GatewayClient
    from app.models.project import Project

    try:
        engine = _get_engine(project_id, db)
        step4 = engine.get_step4_artifacts()
        design_context = (step4 or {}).get("design_doc", "")

        # 加载项目信息
        project = db.query(Project).filter(Project.id == project_id).first()
        if not project:
            raise HTTPException(status_code=404, detail="Project not found")

        # 加载核心目标（步骤2产物）
        step2 = engine.get_step2_artifacts()
        core_goal = step2.get("confirmed_goal") or step2.get("core_goal") or ""

        messages = body.messages + [{"role": "user", "content": body.message}]

        # 使用项目隔离模式
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
        ):
            reply_chunks.append(chunk)
        reply = "".join(reply_chunks)
        if not reply or len(reply.strip()) < 5:
            return APIResponse(code=1, message="后旺未生成有效回复", data=None)
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

    from app.services.gateway_client import GatewayClient
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
        client = GatewayClient(profile_name="hourong", timeout=180)
        chunks = []
        async for chunk in client.chat_completions(
            messages=[{"role": "user", "content": prompt}],
            stream=False, max_tokens=4096,
        ):
            chunks.append(chunk)
        reply = "".join(chunks).strip()
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
            "passed": bool(matched.get("passed", False)) if matched else False,
            "score": matched.get("score", None) if matched else None,
            "detail": matched.get("detail", "未返回该维度检验结果") if matched else "后荣未返回该维度的检验结果",
        })

    all_passed = all(r["passed"] for r in results)
    return APIResponse(code=0, data={
        "passed": all_passed,
        "message": "所有检验项目均通过 ✅" if all_passed else "部分检验项目未通过",
        "dimensions": results,
    })


@router.post("/{project_id}/step4/qa")
def qa_step4(project_id: str, body: QAResultRequest,
             db: Session = Depends(get_db),
             current_user=Depends(get_current_user)):
    engine = _get_engine(project_id, db)
    if body.result == "passed":
        result = engine.pass_qa(4)
    else:
        result = engine.fail_qa(4, reason=body.reason or "", suggestions=body.suggestions)
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

