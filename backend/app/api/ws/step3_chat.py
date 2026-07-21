import json
import os
import asyncio
import logging
import re as _re
import sys
import tempfile
from datetime import datetime, timezone
from fastapi import APIRouter, WebSocket, WebSocketDisconnect, Query
from app.api.ws.auth import verify_token
from app.models.project import Project
from app.services.gateway_client import GatewayClient
from app.services.workflow_engine import WorkflowEngine
from app.models.workflow_step import WorkflowStep
from app.services.doc_sharder import save_chapter, get_shard_config, load_all_chapters
from app.config import settings

logger = logging.getLogger(__name__)

router = APIRouter()

CHAPTER_MARKER_RE = _re.compile(
    r'<!--\s*CHAPTER:\s*([\w.-]+)\s*-->([\s\S]*?)(?=<!--\s*CHAPTER:|\Z)'
)

BRAINSTORMING_QUESTIONNAIRE_PROMPT = (
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
    "!!! 整个表单必须用 <div style=\"width:700px;max-width:100%;box-sizing:border-box;overflow-x:auto;\"> 包裹，禁止超出此宽度 !!!\n"
    "每个问题使用 <div class=\"brain-q\" data-qid=\"q??\"> 包裹，data-qid 从 q01 开始严格递增。\n"
    "!!! 禁止生成任何内容重复的问题 !!! 每个问题的文本必须完全不同，覆盖不同方面。\n"
    "!!! 禁止生成任何选项雷同的问题 !!! 每个问题的选项必须针对该问题专门设计。\n"
    "检查清单（输出前逐一核对）：\n"
    "- 问题内容是否有两句以上意思相同或相近？→ 删除重复\n"
    "- 选项是否有两组以上雷同？→ 重新设计差异化选项\n"
    "- 不同 data-qid 的问题是否覆盖了不同方面？→ 每个方面的题目角度必须不同\n\n"
    "- 允许多选或用户可填写自由回答\n\n"
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
    "每个章节用 <!-- CHAPTER: key --> 包裹。\n"
    "章节划分：\n"
    "- overview: 项目概述（背景、目标、范围、术语表）\n"
    "- functional: 功能需求（按功能模块划分，至少15条需求，编号 SRS-FUNC-*）\n"
    "- non_functional: 非功能需求（编号 SRS-NFR-*）\n"
    "- constraints: 约束条件\n"
    "- glossary: 术语表（至少10个术语）\n\n"
    "禁止使用模糊词汇（用户友好、高效快速、支持、可能等），每个需求必须包含验收标准。\n"
    "SRS 输出完毕后，再输出索引章节：\n"
    "<!-- CHAPTER: index -->\n"
    "# SRS 分片索引表\n"
    "| 分片名 | 内容摘要 |\n"
    "|--------|---------|\n"
    "| overview | 项目概述、目标、范围、术语 |\n"
    "| functional | 功能需求 |\n"
    "| non_functional | 非功能需求 |\n"
    "| constraints | 约束条件 |\n"
    "| glossary | 术语表 |\n"
    "<!-- CHAPTER: end -->\n\n"
    "生成SRS时只输出文档正文，不要包含分析/对话文字。\n"
    "禁止在章节内容中包含工作日志、文件路径、文件名、章节标记等任何非正文信息。"
)

SRS_GENERATION_PROMPT = (
    "===== 任务 =====\n"
    "你是一位资深软件需求分析师。根据以下需求调研问卷答案，生成一份高质量的软件需求规格说明书（SRS）。\n"
    "你的输出将被直接保存为正式需求文档，交付开发团队和测试团队使用。\n"
    "这是一份正式文档，不是对话——禁止输出任何对话、思考过程、工作日志或说明文字，只输出文档正文。\n\n"
    "===== 问卷答案 =====\n"
    "{answers_text}\n\n"
    "===== 质量标准 =====\n"
    "每个需求必须同时满足以下5条标准：\n"
    "1. 具体性：使用精确数字、明确逻辑、可验证的表述，禁止模糊语言\n"
    "2. 完整性：每个功能写明触发条件、输入、处理逻辑、输出、异常处理\n"
    "3. 一致性：同一事物使用统一术语，前后不矛盾\n"
    "4. 可测试性：每个需求本身包含验收标准，测试团队可据此编写测试用例\n"
    "5. 可追溯性：每个需求有唯一编号（SRS-FUNC-XXX / SRS-NFR-XXX）\n\n"
    "禁止使用的模糊词汇（违者扣分）：用户友好、高效快速、足够好、适当的、必要时、尽可能、\n"
    "支持（单独使用）、应能、可以、可能、合理的、正确的、合适的\n\n"
    "===== 各章节详细要求 =====\n\n"
    "<!-- CHAPTER: overview -->\n"
    "【项目概述】必须包含以下子节：\n"
    "## 1.1 项目背景\n"
    "  - 当前面临的问题或市场机遇\n"
    "  - 为什么要做这个项目\n"
    "## 1.2 业务目标\n"
    "  - 3-5个可量化的业务目标（例如：将订单处理时间从平均5分钟缩短到30秒以内）\n"
    "## 1.3 项目范围\n"
    "  - 包含的功能列表：列出主要功能模块\n"
    "  - 不包含的功能列表：明确排除的功能\n"
    "## 1.4 目标用户\n"
    "  - 用户角色：至少列出3个角色，每个角色说明核心需求\n"
    "## 1.5 术语表\n"
    "  - 至少5个关键术语的定义\n\n"
    "<!-- CHAPTER: functional -->\n"
    "【功能需求】按功能模块组织，每个模块使用二级标题（## 模块名称）。\n"
    "每个功能需求的格式严格如下：\n\n"
    "### SRS-FUNC-001 - 需求名称\n"
    "- **描述**：一句话说明该功能\n"
    "- **优先级**：Must / Should / Could / Won't（仅选一个）\n"
    "- **触发条件**：什么情况下执行本功能\n"
    "- **前置条件**：必须已满足的条件（若无则写“无”）\n"
    "- **基本流程**：\n"
    "  1. 步骤一\n"
    "  2. 步骤二\n"
    "  3. 步骤三\n"
    "- **扩展流程**：\n"
    "  1. 异常情况一：处理方式\n"
    "  2. 异常情况二：处理方式\n"
    "- **验收标准**（至少2条，可测试）：\n"
    "  1. 条件一\n"
    "  2. 条件二\n\n"
    "数量要求：\n"
    "- 至少生成15个功能需求\n"
    "- 分属于3-5个功能模块\n"
    "- 每个模块至少3个需求\n"
    "- 优先级 Must 的需求不少于总数的一半\n\n"
    "<!-- CHAPTER: non_functional -->\n"
    "【非功能需求】每个需求的格式如下：\n\n"
    "### SRS-NFR-001 - 需求名称\n"
    "- **描述**：具体指标说明\n"
    "- **度量方法**：如何验证该指标是否达标\n"
    "- **目标值**：具体的数字指标\n\n"
    "必须覆盖以下类别（每类至少1条）：\n"
    "1. 性能：页面响应时间<=X秒，支持Y并发用户，吞吐量Z req/s\n"
    "2. 安全：认证方式（JWT/OAuth/SSO）、权限模型（RBAC/ABAC）、数据加密（TLS 1.3+）、审计日志\n"
    "3. 可用性：系统可用时间>=99.X%，RTO<=X小时，RPO<=X分钟\n"
    "4. 可维护性：容器化部署、结构化日志（JSON格式）、健康检查端点、Prometheus指标\n"
    "5. 兼容性：支持的浏览器/设备列表、数据导入导出格式\n\n"
    "<!-- CHAPTER: constraints -->\n"
    "【约束条件】必须包含以下类别：\n"
    "1. 技术栈约束：编程语言、框架、数据库、基础设施、CI/CD工具链\n"
    "2. 时间约束：里程碑节点、各阶段交付日期\n"
    "3. 预算约束：可用资源（人力、服务器等）\n"
    "4. 法律/合规约束：GDPR、等保等级、数据本地化要求\n"
    "5. 集成约束：需要对接的外部系统名称及接口协议（REST/gRPC/WebSocket等）\n\n"
    "<!-- CHAPTER: glossary -->\n"
    "【术语表】至少10个术语，格式如下：\n"
    "| 术语 | 英文名 | 定义 |\n"
    "|------|--------|------|\n"
    "| 订单 | Order | 用户提交的包含商品和支付信息的交易记录 |\n"
    "| ... | ... | ... |\n\n"
    "最后输出索引章节：\n"
    "<!-- CHAPTER: index -->\n"
    "# SRS 分片索引表\n"
    "| 分片名 | 内容摘要 |\n"
    "|--------|---------|\n"
    "| overview | 项目概述、目标、范围、术语 |\n"
    "| functional | 功能需求（SRS-FUNC-*，共N条） |\n"
    "| non_functional | 非功能需求（SRS-NFR-*，共N条） |\n"
    "| constraints | 约束条件 |\n"
    "| glossary | 术语表（共N个术语） |\n"
    "<!-- CHAPTER: end -->\n\n"
    "===== 格式禁令 =====\n"
    "1. 禁止输出任何对话内容、思考过程、工作日志、分析文字\n"
    "2. 禁止输出```json、```html、```markdown 等代码块标记\n"
    "3. 禁止输出「以下是xxx章节」「路径：xxx」「根据以上分析」等过渡性文字\n"
    "4. 禁止在章节内容中包含文件路径、文件名、分片名等元信息\n"
    "5. 每个 CHAPTER 之间的内容只包含正式的Markdown文档正文\n"
    "6. 违反以上任何一条将导致输出被丢弃，必须重新生成\n"
)


def _strip_thinking(text: str) -> str:
    """去除模型输出的 thinking/reasoning 前缀内容"""
    text = _re.sub(r'^.*?<think>.*?</think>\s*', '', text, flags=_re.DOTALL)
    text = _re.sub(r'^.*?<antThink>.*?</antThink>\s*', '', text, flags=_re.DOTALL)
    first = _re.search(r'<!--\s*CHAPTER:', text)
    if first and first.start() > 0:
        text = text[first.start():]
    return text.strip()


def _split_chapters(full_text: str) -> dict:
    chapters = {}
    for m in CHAPTER_MARKER_RE.finditer(full_text):
        key = m.group(1).strip()
        raw = m.group(2)
        content = _clean_chapter_content(raw)
        if content:
            chapters[key] = content
    return chapters


def _extract_html(text: str) -> str:
    m = _re.search(r'```html\s*([\s\S]*?)```', text)
    if m:
        html = m.group(1).strip()
    else:
        html = text.strip()
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


def _refs_exist(project_docs_dir: str) -> bool:
    """检查 refs 目录是否有文件"""
    refs_dir = os.path.join(project_docs_dir, "refs")
    if not os.path.isdir(refs_dir):
        return False
    files = [f for f in os.listdir(refs_dir) if os.path.isfile(os.path.join(refs_dir, f))]
    return len(files) > 0


def _clean_chapter_content(content: str) -> str:
    """清洗分片内容：去除噪音、无效片段"""
    CLOSING_TAG_RE = _re.compile(r'<!--\s*CHAPTER:\s*-->\s*')
    FENCE_RE = _re.compile(r'^```[\w]*\s*$', _re.MULTILINE)
    content = CLOSING_TAG_RE.sub('', content)
    content = FENCE_RE.sub('', content)
    return content.strip()


def _save_sharded_srs(full_srs: str, project_slug: str, project_docs_dir: str) -> dict:
    chapters = _split_chapters(full_srs)
    if "index" in chapters:
        del chapters["index"]
    saved_files = {}
    os.makedirs(project_docs_dir, exist_ok=True)

    if not chapters:
        cleaned = _clean_chapter_content(full_srs)
        if len(cleaned) < 50:
            return {
                "saved_files": {},
                "index_path": "",
                "index_content": "",
                "chapter_count": 0,
                "error": "内容过短，无法生成有效分片",
            }
        fpath = os.path.join(project_docs_dir, f"{project_slug}_SRS_full.md")
        with open(fpath, "w", encoding="utf-8") as f:
            f.write(cleaned)
        saved_files["full"] = fpath
        index_path = ""
        index_content = ""
        chapter_count = 0
    else:
        for ch_key, ch_content in chapters.items():
            ch_content = _clean_chapter_content(ch_content)
            if len(ch_content) < 20:
                continue
            fpath = save_chapter("SRS", ch_key, ch_content, project_docs_dir, project_slug)
            saved_files[ch_key] = fpath

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
        with open(index_path, "w", encoding="utf-8") as f:
            f.write(index_content)
        chapter_count = len(chapters)

    return {
        "saved_files": saved_files,
        "index_path": index_path,
        "index_content": index_content,
        "chapter_count": chapter_count,
    }


async def _call_subagent(messages: list, profile_name: str = "houxing", timeout: int = 600, max_tokens: int = 32000, temperature: float = 0.3, direct: bool = True) -> str:
    """调用子Agent（一次性返回，不流式）
    direct=True 时绕过 hermes 网关直接调用底层 LLM
    """
    client = GatewayClient(profile_name=profile_name, timeout=timeout)
    chunks = []
    method = client.direct_chat_completions if direct else client.chat_completions
    async for chunk in method(messages=messages, stream=True, max_tokens=max_tokens, temperature=temperature):
        if chunk.strip():
            chunks.append(chunk)
    return "".join(chunks)


async def _generate_srs_via_subagent(
    answers: dict,
    output_path: str,
    websocket,
    profile_name: str = "houxing",
    timeout: int = 600,
    core_goal: str = "",
    refs_dir: str = "",
) -> str:
    """通过 delegate_task（直接异步子进程调用脚本）生成SRS文档。

    1. 将答案和SRS生成提示词保存到临时文件
    2. 异步执行 scripts/generate_srs.py 脚本
    3. 脚本调用LLM生成SRS并保存到文件
    4. 返回文件路径

    HouXing只负责对话和接收路径，不参与文件写入或LLM调用。
    """
    BASE_DIR = os.path.dirname(os.path.dirname(os.path.dirname(os.path.dirname(os.path.abspath(__file__)))))
    script_path = os.path.join(BASE_DIR, "scripts", "generate_srs.py")

    if not os.path.exists(script_path):
        raise FileNotFoundError(f"SRS生成脚本不存在: {script_path}")

    with tempfile.NamedTemporaryFile(
        mode="w", suffix=".json", delete=False, encoding="utf-8"
    ) as af:
        json.dump(answers, af, ensure_ascii=False, indent=2)
        answers_path = af.name

    with tempfile.NamedTemporaryFile(
        mode="w", suffix=".txt", delete=False, encoding="utf-8"
    ) as pf:
        pf.write(SRS_GENERATION_PROMPT)
        prompt_path = pf.name

    try:
        os.makedirs(os.path.dirname(output_path), exist_ok=True)

        await websocket.send_json({
            "type": "subagent_status",
            "data": {"status": "generating", "message": "🧠 delegate_task 正在执行SRS生成脚本..."},
        })

        args = [
            sys.executable or "python3",
            script_path,
            "--input-answers", answers_path,
            "--output-path", output_path,
            "--prompt-file", prompt_path,
        ]
        if core_goal:
            args.extend(["--core-goal", core_goal])
        if refs_dir and os.path.isdir(refs_dir):
            args.extend(["--refs-dir", refs_dir])

        proc = await asyncio.create_subprocess_exec(
            *args,
            stdout=asyncio.subprocess.PIPE,
            stderr=asyncio.subprocess.PIPE,
        )

        stdout, stderr = await asyncio.wait_for(proc.communicate(), timeout=timeout)

        if proc.returncode != 0:
            err_text = stderr.decode("utf-8", errors="replace")[:500]
            raise RuntimeError(f"脚本退出码 {proc.returncode}: {err_text}")

        output_text = stdout.decode("utf-8", errors="replace").strip()
        logger.info(f"generate_srs.py 输出: {output_text[:300]}")

        if os.path.exists(output_path) and os.path.getsize(output_path) > 50:
            await websocket.send_json({
                "type": "subagent_status",
                "data": {"status": "done", "message": f"✅ delegate_task 已完成，SRS保存至{output_path}"},
            })
            return output_path

        # 尝试解析脚本的JSON输出获取错误信息
        try:
            result = json.loads(output_text)
            raise RuntimeError(result.get("message", output_text[:200]))
        except json.JSONDecodeError:
            raise RuntimeError(f"脚本未生成有效SRS文件，输出: {output_text[:200]}")
    finally:
        for p in [answers_path, prompt_path]:
            try:
                os.unlink(p)
            except Exception:
                pass


async def _call_subagent_with_progress(
    messages: list,
    websocket,
    profile_name: str = "houxing",
    timeout: int = 600,
    max_tokens: int = 32000,
    temperature: float = 0.3,
    direct: bool = True,
) -> str:
    """调用子Agent，通过WebSocket发送进度状态
    direct=True 时绕过 hermes 网关直接调用底层 LLM，避免 agent 循环注入对话前缀
    """
    client = GatewayClient(profile_name=profile_name, timeout=timeout)
    chunks = []
    chunk_count = 0
    method = client.direct_chat_completions if direct else client.chat_completions

    async for chunk in method(messages=messages, stream=True, max_tokens=max_tokens, temperature=temperature):
        if chunk.strip():
            chunks.append(chunk)
            chunk_count += 1
            if chunk_count == 1:
                await websocket.send_json({
                    "type": "subagent_status",
                    "data": {"status": "generating", "message": "🧠 子Agent已启动，正在分析问卷答案并生成SRS文档..."},
                })
            elif chunk_count % 15 == 0:
                progress = min(chunk_count * 2, 90)
                char_count = len("".join(chunks))
                await websocket.send_json({
                    "type": "subagent_progress",
                    "data": {"progress": progress, "message": f"📝 子Agent正在生成SRS文档（已生成 {char_count} 字符）..."},
                })

    await websocket.send_json({
        "type": "subagent_status",
        "data": {"status": "done", "message": "✅ 子Agent已完成SRS文档生成"},
    })
    return "".join(chunks)


async def _modify_srs_via_subagent(
    user_message: str,
    all_ch: dict,
    project_slug: str,
    project_docs_dir: str,
    saved_messages: list,
    core_goal: str,
    srs_full_path: str = "",
) -> dict:
    """通过子Agent修改SRS文档，返回修改结果"""
    srs_context_parts = []
    if all_ch:
        for key, data in all_ch.items():
            if data.get("content"):
                srs_context_parts.append(
                    f"<!-- CHAPTER: {key} -->\n{data['content']}"
                )
    # 无分片时回退到完整文档
    if not srs_context_parts and srs_full_path and os.path.exists(srs_full_path):
        try:
            with open(srs_full_path, "r", encoding="utf-8") as f:
                srs_context_parts.append(f.read())
        except Exception:
            pass
    srs_context = "\n\n".join(srs_context_parts)

    system_prompt = (
        "你是一个软件需求分析师（后兴）。用户希望对已生成的SRS需求文档进行修改或补充。\n"
        "请根据用户的要求修改文档。\n\n"
        "当前SRS文档内容如下（用 <!-- CHAPTER: key --> 标记了各个章节分片）：\n"
        f"{srs_context}\n\n"
        "输出要求：\n"
        "1. 如果用户要求修改，请输出修改后的完整章节内容，用 <!-- CHAPTER: key --> 包裹\n"
        "2. 只修改用户指出的部分，其他章节保持不变\n"
        "3. 如果用户只是询问问题，正常回答即可（不需要输出章节标记）\n"
        "4. 如果输出章节内容，最后输出索引章节 <!-- CHAPTER: index -->"
    )

    system_parts = []
    if core_goal:
        system_parts.append(f"[项目核心目标]\n{core_goal}")
    system_parts.append(system_prompt)
    messages = [
        {"role": "system", "content": "\n\n".join(system_parts)},
        {"role": "user", "content": user_message},
    ]

    full_reply = await _call_subagent(messages, timeout=300, max_tokens=32000, temperature=0.3)

    result = {
        "full_reply": full_reply,
        "summary": full_reply[:2000],
        "has_chapters": False,
        "shard_result": None,
    }

    chapters = _split_chapters(full_reply)
    if chapters:
        shard_result = _save_sharded_srs(full_reply, project_slug, project_docs_dir)
        result["has_chapters"] = True
        result["shard_result"] = shard_result

    return result


@router.websocket("/step3/chat/{project_id}")
async def step3_chat_ws(websocket: WebSocket, project_id: str, token: str = Query(...)):
    """
    WebSocket for HouXing step3 — new flow:

      check_docs_upload (要求上传文档)
            ↓
      generate_questionnaire (基于文档的头脑风暴问卷)
            ↓
      submit_answers (问卷答案 → delegate_task 子Agent生成SRS)
            ↓
      chat (迭代修改，有SRS时走子Agent)
            ↓
      request_qa (提交QA检验)
    """
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

        while True:
            data = await websocket.receive_text()
            payload = json.loads(data)
            action = payload.get("action", "")

            # ================================================================
            # 0. start — 返回当前阶段状态
            # ================================================================
            if action == "start":
                # 如果 step3 已经是 qa_review 状态，禁止进入 chat 页面，直接跳转到 QA
                step3_row = db.query(WorkflowStep).filter(
                    WorkflowStep.project_id == project_id,
                    WorkflowStep.step_number == 3,
                ).first()
                if step3_row and step3_row.status == "qa_review":
                    await websocket.send_json({
                        "type": "enter_qa",
                        "data": {
                            "redirect_url": f"/step3/{project_id}/qa",
                            "message": "步骤3已完成，正在进入QA检验阶段...",
                        },
                    })
                    continue

                phase = cp.get("phase", "initial")
                has_docs = _refs_exist(project_docs_dir)
                has_questionnaire = cp.get("questionnaire_generated", False)
                has_srs = cp.get("srs_generated", False)
                has_answers = cp.get("answers_submitted", False)

                await websocket.send_json({
                    "type": "status",
                    "data": {
                        "phase": phase,
                        "docs_uploaded": has_docs,
                        "questionnaire_generated": has_questionnaire,
                        "srs_generated": has_srs,
                        "answers_submitted": has_answers,
                        "questionnaire_html": cp.get("questionnaire_html", "") if has_questionnaire else "",
                        "question_count": cp.get("question_count", 0),
                    }
                })
                continue

            # ================================================================
            # 1. check_docs_upload — 检查是否已上传文档
            # ================================================================
            if action == "check_docs_upload":
                has_docs = _refs_exist(project_docs_dir)
                await websocket.send_json({
                    "type": "docs_status",
                    "data": {"uploaded": has_docs},
                })
                continue

            # ================================================================
            # 2. generate_questionnaire — 基于参考文档用头脑风暴方式生成问卷
            # ================================================================
            if action == "generate_questionnaire":
                if not _refs_exist(project_docs_dir):
                    await websocket.send_json({
                        "type": "error",
                        "message": "请先上传相关参考文档后再生成问卷",
                    })
                    continue

                if cp.get("answers_submitted") or cp.get("srs_generated"):
                    await websocket.send_json({
                        "type": "error",
                        "message": "问卷已提交，不可重新生成问卷",
                    })
                    continue

                if cp.get("questionnaire_generated"):
                    if cp.get("questionnaire_html"):
                        await websocket.send_json({
                            "type": "questionnaire",
                            "content": cp["questionnaire_html"],
                            "question_count": cp.get("question_count", 0),
                        })
                    else:
                        await websocket.send_json({
                            "type": "error",
                            "message": "问卷已生成但内容不可用（HTML为空），如需重新生成请重置项目",
                        })
                    continue

                refs_text = _load_refs_text(project_docs_dir)
                system_parts = []
                if core_goal:
                    system_parts.append(f"[项目核心目标]\n{core_goal}")
                sys_content = BRAINSTORMING_QUESTIONNAIRE_PROMPT
                if refs_text:
                    sys_content += (
                        "\n\n===== 参考文档 =====\n"
                        "用户上传了以下参考文档，请仔细阅读并结合这些文档的内容来设计调研问题：\n\n"
                        f"{refs_text}\n\n"
                        "注意：问题应基于这些文档中的真实信息，不要凭空假设。"
                    )
                system_parts.append(sys_content)
                messages = [
                    {"role": "system", "content": "\n\n".join(system_parts)},
                    {"role": "user", "content": "请根据项目核心目标和参考文档生成需求调研问卷。"},
                ]

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

                    questionnaire_file = os.path.join(project_docs_dir, f"{project_slug}_questionnaire.html")
                    try:
                        with open(questionnaire_file, "w", encoding="utf-8") as f:
                            f.write(html_form)
                    except Exception as e:
                        logger.warning(f"保存问卷文件失败: {e}")
                        questionnaire_file = ""

                    raw_reply_file = os.path.join(project_docs_dir, f"{project_slug}_questionnaire_raw.md")
                    try:
                        with open(raw_reply_file, "w", encoding="utf-8") as f:
                            f.write(full_reply)
                    except Exception as e:
                        logger.warning(f"保存原始AI回复失败: {e}")
                        raw_reply_file = ""

                    cp["phase"] = "questionnaire_ready"
                    cp["questionnaire_generated"] = True
                    cp["questionnaire_html"] = html_form
                    cp["question_count"] = q_count
                    cp["questionnaire_file"] = questionnaire_file
                    cp["questionnaire_raw_file"] = raw_reply_file
                    try:
                        engine.save_step3_artifacts({"chat_checkpoint": dict(cp)})
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

            # ================================================================
            # 3. submit_answers — 提交问卷答案 → delegate_task 子Agent生成SRS
            # ================================================================
            if action == "submit_answers":
                answers = payload.get("answers", {})
                if not answers:
                    await websocket.send_json({"type": "error", "message": "答案为空"})
                    continue

                answers_text = json.dumps(answers, ensure_ascii=False, indent=2)
                artifacts = engine.get_step3_artifacts() or {}
                saved_messages = artifacts.get("chat_messages", [])

                # 立即保存答案和提交状态到数据库
                cp["answers_submitted"] = True
                cp["answers"] = answers
                cp["phase"] = "generating_srs"
                saved_messages.append({
                    "role": "user",
                    "content": f"用户提交了需求调研问卷答案：\n{answers_text}",
                    "saved_at": datetime.now(timezone.utc).isoformat(),
                })
                try:
                    engine.save_step3_artifacts({
                        "chat_messages": saved_messages,
                        "chat_checkpoint": dict(cp),
                    })
                except Exception as cp_e:
                    logger.warning(f"保存问卷答案到数据库失败: {cp_e}")

                try:
                    # delegate_task 子Agent执行脚本生成SRS文档
                    # HouXing 只负责对话，不参与文件写入或LLM调用
                    srs_full_path = os.path.join(project_docs_dir, f"{project_slug}_SRS_full.md")
                    refs_dir = os.path.join(project_docs_dir, "refs") if os.path.isdir(os.path.join(project_docs_dir, "refs")) else ""
                    srs_full_path = await _generate_srs_via_subagent(
                        answers=answers,
                        output_path=srs_full_path,
                        websocket=websocket,
                        timeout=600,
                        core_goal=core_goal or "",
                        refs_dir=refs_dir,
                    )

                    srs_summary = f"✅ delegate_task 子Agent已生成SRS文档，保存至{srs_full_path}"
                    saved_messages.append({
                        "role": "assistant",
                        "content": srs_summary,
                        "saved_at": datetime.now(timezone.utc).isoformat(),
                    })

                    cp["phase"] = "srs_ready"
                    cp["srs_generated"] = True
                    cp["srs_full_path"] = srs_full_path
                    try:
                        engine.save_step3_artifacts({
                            "chat_messages": saved_messages,
                            "srs_full_path": srs_full_path,
                            "chat_checkpoint": dict(cp),
                        })
                    except Exception as artifact_e:
                        logger.warning(f"保存SRS文档路径到数据库失败: {artifact_e}")

                    await websocket.send_json({
                        "type": "srs_generated",
                        "data": {"path": srs_full_path},
                    })

                    await websocket.send_json({"type": "done"})
                except Exception as e:
                    logger.error(f"子Agent生成SRS失败: {e}")
                    cp["phase"] = "srs_failed"
                    try:
                        engine.save_step3_artifacts({
                            "chat_checkpoint": dict(cp),
                        })
                    except Exception:
                        pass
                    try:
                        await websocket.send_json({"type": "error", "message": f"子Agent生成SRS失败：{str(e)[:200]}"})
                    except Exception:
                        pass
                continue

            # ================================================================
            # 4. chat — 用户对话
            #    有SRS时 → delegate_task 子Agent修改
            #    无SRS时 → 普通流式对话（问卷阶段咨询）
            # ================================================================
            if action == "chat":
                user_message = payload.get("message", "").strip()
                history = payload.get("history", [])
                if not user_message:
                    await websocket.send_json({"type": "error", "message": "消息为空"})
                    continue

                artifacts = engine.get_step3_artifacts() or {}
                saved_messages = artifacts.get("chat_messages", [])
                saved_messages.append({
                    "role": "user",
                    "content": user_message,
                    "saved_at": datetime.now(timezone.utc).isoformat(),
                })
                engine.save_step3_artifacts({
                    "chat_messages": saved_messages,
                    "current_phase": "chatting",
                    "last_activity_at": datetime.now(timezone.utc).isoformat(),
                })

                all_ch = load_all_chapters("SRS", project_docs_dir, project_slug)
                has_srs = any(v.get("content") for v in all_ch.values())

                if has_srs:
                    # SRS已存在 → 走子Agent修改
                    try:
                        srs_full_path = cp.get("srs_full_path", "")
                        mod_result = await _modify_srs_via_subagent(
                            user_message=user_message,
                            all_ch=all_ch,
                            project_slug=project_slug,
                            project_docs_dir=project_docs_dir,
                            saved_messages=saved_messages,
                            core_goal=core_goal,
                            srs_full_path=srs_full_path,
                        )

                        full_reply = mod_result["full_reply"]

                        saved_messages.append({
                            "role": "assistant",
                            "content": mod_result["summary"],
                            "full_length": len(full_reply),
                            "saved_at": datetime.now(timezone.utc).isoformat(),
                        })

                        chat_log_dir = os.path.join(project_docs_dir, "chat_logs")
                        os.makedirs(chat_log_dir, exist_ok=True)
                        chat_log_file = os.path.join(
                            chat_log_dir,
                            f"chat_{datetime.now(timezone.utc).strftime('%Y%m%d_%H%M%S')}.md"
                        )
                        with open(chat_log_file, "w", encoding="utf-8") as f:
                            f.write(full_reply)

                        save_data = {
                            "chat_messages": saved_messages,
                            "last_reply": mod_result["summary"],
                            "last_reply_at": datetime.now(timezone.utc).isoformat(),
                        }
                        if mod_result["has_chapters"]:
                            sr = mod_result["shard_result"]
                            save_data["shard_index"] = sr.get("saved_files", {})
                            save_data["shard_index_path"] = sr.get("index_path", "")
                            save_data["shard_index_content"] = sr.get("index_content", "")
                            try:
                                engine.save_step3_artifacts(save_data)
                            except Exception as artifact_e:
                                logger.warning(f"保存修改后的分片到数据库失败: {artifact_e}")
                            await websocket.send_json({
                                "type": "shards_updated",
                                "data": sr,
                            })
                        else:
                            try:
                                engine.save_step3_artifacts(save_data)
                            except Exception as e:
                                logger.warning(f"保存聊天记录到数据库失败: {e}")

                        # 未分段回复通过chunk类型发送
                        if not mod_result["has_chapters"]:
                            # 发送前2000字符作为可见回复
                            visible = full_reply[:2000]
                            await websocket.send_json({"type": "chunk", "content": visible})

                        await websocket.send_json({"type": "done"})
                    except WebSocketDisconnect:
                        raise
                    except Exception as e:
                        logger.error(f"子Agent修改SRS失败: {e}")
                        try:
                            await websocket.send_json({"type": "error", "message": f"子Agent处理失败：{str(e)[:200]}"})
                        except Exception:
                            pass
                else:
                    # 无SRS → 普通流式对话（问卷阶段）
                    refs_text = _load_refs_text(project_docs_dir)
                    system_parts = []
                    if core_goal:
                        system_parts.append(f"[项目核心目标]\n{core_goal}")
                    sys = "你是一个软件需求分析师（后兴）。"
                    if refs_text:
                        sys += f"用户上传了以下参考文档，请结合这些文档内容回答用户的问题：\n\n{refs_text}\n\n"
                    sys += "请回答用户关于需求调研的问题。"
                    system_parts.append(sys)
                    messages = [{"role": "system", "content": "\n\n".join(system_parts)}]
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

                        saved_messages.append({
                            "role": "assistant",
                            "content": full_reply[:2000],
                            "full_length": len(full_reply),
                            "saved_at": datetime.now(timezone.utc).isoformat(),
                        })

                        chat_log_dir = os.path.join(project_docs_dir, "chat_logs")
                        os.makedirs(chat_log_dir, exist_ok=True)
                        chat_log_file = os.path.join(
                            chat_log_dir,
                            f"chat_{datetime.now(timezone.utc).strftime('%Y%m%d_%H%M%S')}.md"
                        )
                        with open(chat_log_file, "w", encoding="utf-8") as f:
                            f.write(full_reply)

                        chapters = _split_chapters(full_reply)
                        save_data = {
                            "chat_messages": saved_messages,
                            "last_reply": full_reply[:2000],
                            "last_reply_at": datetime.now(timezone.utc).isoformat(),
                        }
                        if chapters:
                            shard_result = _save_sharded_srs(full_reply, project_slug, project_docs_dir)
                            save_data["shard_index"] = shard_result.get("saved_files", {})
                            save_data["shard_index_path"] = shard_result.get("index_path", "")
                            save_data["shard_index_content"] = shard_result.get("index_content", "")
                            try:
                                engine.save_step3_artifacts(save_data)
                            except Exception as artifact_e:
                                logger.warning(f"保存分片索引到数据库失败: {artifact_e}")
                            await websocket.send_json({
                                "type": "shards_updated",
                                "data": shard_result,
                            })
                        else:
                            try:
                                engine.save_step3_artifacts(save_data)
                            except Exception as e:
                                logger.warning(f"保存聊天记录到数据库失败: {e}")

                        await websocket.send_json({"type": "done"})
                    except WebSocketDisconnect:
                        raise
                    except Exception as e:
                        logger.error(f"HouXing chat failed: {e}")
                        try:
                            await websocket.send_json({"type": "error", "message": str(e)})
                        except Exception:
                            pass
                continue

            # ================================================================
            # 5. request_qa — 用户认为满意，提交QA检验
            # ================================================================
            if action == "request_qa":
                has_srs = cp.get("srs_generated", False)
                if not has_srs:
                    await websocket.send_json({
                        "type": "error",
                        "message": "SRS需求文档尚未生成，无法提交QA检验",
                    })
                    continue

                try:
                    # 保存当前聊天断点到DB
                    engine.save_step3_artifacts({"chat_checkpoint": dict(cp)})

                    # 拆分完整SRS为分片文件
                    srs_full_path = cp.get("srs_full_path", "")
                    shard_result = {}
                    if srs_full_path and os.path.exists(srs_full_path):
                        with open(srs_full_path, "r", encoding="utf-8") as f:
                            full_srs_content = f.read()
                        shard_result = _save_sharded_srs(full_srs_content, project_slug, project_docs_dir)
                        if shard_result.get("chapter_count", 0) > 0:
                            cp["sharded"] = True
                            engine.save_step3_artifacts({
                                "shard_index": shard_result.get("saved_files", {}),
                                "shard_index_path": shard_result.get("index_path", ""),
                                "shard_index_content": shard_result.get("index_content", ""),
                                "chat_checkpoint": dict(cp),
                            })

                    # 保存QA上下文到 project_steps/qa_records 目录（持久化存储）
                    project_dir = os.path.join(settings.PROJECTS_BASE_DIR, project_slug)
                    qa_records_dir = os.path.join(project_dir, "project_steps", "qa_records")
                    os.makedirs(qa_records_dir, exist_ok=True)

                    qa_context = {
                        "status": "pending",
                        "triggered_at": datetime.now(timezone.utc).isoformat(),
                        "output_path": srs_full_path or "",
                        "shard_index_path": shard_result.get("index_path", ""),
                        "project_slug": project_slug,
                        "project_docs_dir": project_docs_dir,
                    }
                    qa_context_file = os.path.join(
                        qa_records_dir,
                        f"qa_context_{datetime.now(timezone.utc).strftime('%Y%m%d_%H%M%S')}.json",
                    )
                    with open(qa_context_file, "w", encoding="utf-8") as f:
                        json.dump(qa_context, f, ensure_ascii=False, indent=2)

                    # 设置步骤3状态为 qa_review（触发路由守卫自动跳转到 Step3Qa 页面）
                    step3_row = db.query(WorkflowStep).filter(
                        WorkflowStep.project_id == project_id,
                        WorkflowStep.step_number == 3,
                    ).first()
                    if step3_row:
                        step3_row.status = "qa_review"
                        db.commit()
                        logger.info(f"步骤3状态已设置为qa_review (project={project_id})")

                    # 发送跳转消息到前端
                    await websocket.send_json({
                        "type": "enter_qa",
                        "data": {
                            "redirect_url": f"/step3/{project_id}/qa",
                            "message": "需求文档已就绪 ✅ 正在进入QA检验阶段...",
                        },
                    })
                except Exception as e:
                    logger.error(f"进入QA检验阶段失败: {e}", exc_info=True)
                    try:
                        await websocket.send_json({"type": "error", "message": f"进入QA检验阶段失败：{str(e)[:200]}"})
                    except Exception:
                        pass
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
