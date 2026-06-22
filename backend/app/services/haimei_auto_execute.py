"""
Haimei Auto Execute - 海梅直接调用 step 文件的 _generate 逻辑
绕过旧的 haimei_dispatch.py（chat_completions，无 QA），直接复用 step 文件重写后的逻辑。
"""
from __future__ import annotations
import asyncio
import logging
import os as _os

logger = logging.getLogger("devflow.haimei.auto_execute")

# 内存中跟踪已分发的步骤，防止重复调度
_dispatched_steps: set = set()

# ── 步骤对应的 broadcast 模块（前端连的是独立的 WS 端口） ──
_STEP_BROADCAST_MODULES = {}


def _get_broadcast(step_number: int):
    """获取步骤对应的 WebSocket broadcast 函数"""
    global _STEP_BROADCAST_MODULES
    if step_number not in _STEP_BROADCAST_MODULES:
        module_map = {
            4: "app.api.ws.step4_progress",
            5: "app.api.ws.step5_progress",
            6: "app.api.ws.step6_progress",
            7: "app.api.ws.step7_progress",
            8: "app.api.ws.step8_progress",
        }
        module_name = module_map.get(step_number, "app.api.ws.step4_progress")
        try:
            import importlib
            mod = importlib.import_module(module_name)
            _STEP_BROADCAST_MODULES[step_number] = mod.broadcast
        except Exception as e:
            logger.error(f"加载步骤{step_number}的 broadcast 模块失败: {e}")
            # 回退到 step4_progress
            from app.api.ws.step4_progress import broadcast
            _STEP_BROADCAST_MODULES[step_number] = broadcast
    return _STEP_BROADCAST_MODULES[step_number]


async def auto_dispatch_step(project_id: str, step_number: int, db=None, close_db=False) -> None:
    """海梅直接调度步骤 N 的执行（使用 step 文件的新 _generate 逻辑 + chat_isolated + hourong QA）"""
    from app.database import SessionLocal
    from app.services.workflow_engine import WorkflowEngine
    from app.api.ws.step4_progress import broadcast

    # Step4 和 Step5 由各自独立的 WS 处理器执行，跳过自动调度
    if step_number == 5:
        logger.info(f"步骤5由WS处理器执行，跳过自动调度")
        return

    if db is None:
        db = SessionLocal()
        close_db = True

    try:
        bg_engine = WorkflowEngine(project_id=project_id, db=db)

        # 内存中检查是否已分发，防止重复调用
        dispatch_key = f"{project_id}:{step_number}"
        if dispatch_key in _dispatched_steps:
            logger.info(f"步骤{step_number}已在执行中（dispatch_key={dispatch_key}），跳过重复调度")
            return

        # 禁止重复执行：已完成或已有 done 产物时跳过
        step_row = bg_engine._get_step_row(step_number)
        if step_row:
            if step_row.status == "completed":
                logger.info(f"步骤{step_number}已完成，跳过自动调度")
                return

        # 标记已分发
        _dispatched_steps.add(dispatch_key)

        # 获取步骤 N 的 execute 函数对应的 _generate
        executor = _STEP_EXECUTORS.get(step_number)
        if not executor:
            logger.warning(f"步骤{step_number}没有对应的自动执行器")
            return

        await executor(project_id, bg_engine, db)

    except Exception as e:
        logger.error(f"海梅调度步骤{step_number}执行失败: {e}", exc_info=True)
        try:
            bg_engine.reset_step(step_number)
            logger.info(f"步骤{step_number}已重置为 pending，等待重试")
        except Exception:
            pass
    finally:
        _dispatched_steps.discard(f"{project_id}:{step_number}")
        if close_db:
            db.close()


# ── 步骤执行器注册 ──

_STEP_EXECUTORS: dict[int, callable] = {}


def register_step_executor(step_number: int):
    """装饰器：注册步骤 N 的自动执行函数"""
    def decorator(fn):
        _STEP_EXECUTORS[step_number] = fn
        return fn
    return decorator


# ── 每个步骤一个执行函数 ──

@register_step_executor(4)
async def _auto_step4(project_id: str, engine: WorkflowEngine, db):
    """Step4: houwang 生成4份设计文档，hourong 检验+收敛"""
    # 直接复用 step4.py 的 _run_doc_sub_flow 逻辑
    from app.api.workflow.step4 import _run_doc_sub_flow
    from app.api.workflow.step4 import SUB_FLOW_CONFIGS
    from app.api.ws.step4_progress import broadcast
    import json as _json

    step3 = engine.get_step3_artifacts() or {}
    requirement = (step3.get("doc_content") or step3.get("content") or
                   step3.get("requirement") or step3.get("srs") or "")
    step2 = engine.get_step2_artifacts() or {}
    core_goal = step2.get("confirmed_goal") or step2.get("core_goal") or ""

    from app.models.project import Project
    from app.config import settings
    proj = db.query(Project).filter(Project.id == project_id).first()
    slug = proj.slug if proj else project_id.replace("-", "")
    docs_dir = _os.path.join(settings.PROJECTS_BASE_DIR, slug, "docs")
    _os.makedirs(docs_dir, exist_ok=True)

    proj_name = proj.name if proj else ""
    proj_desc = proj.description or ""

    # --- 检查 Step3 需求是否为空 ---
    if not requirement.strip():
        logger.error("Step4: 未找到 Step3 需求文档内容")
        engine.reset_step(4)
        await broadcast(project_id, {"type": "error", "message": "❌ 未找到 Step3 需求文档，步骤4无法执行"})
        return

    # 跳过已通过的子流程——避免重复执行
    existing_subs = (engine.get_step4_artifacts() or {}).get("sub_flow_results", [])
    passed_keys = {r["key"] for r in existing_subs if r.get("passed")}
    cfgs_to_run = [c for c in SUB_FLOW_CONFIGS if c["dim"]["key"] not in passed_keys]
    if passed_keys:
        await broadcast(project_id, {"type": "stage", "message": f"♻️ 跳过已通过检验的 {len(passed_keys)} 项，只运行 {len(cfgs_to_run)} 项"})
    else:
        await broadcast(project_id, {"type": "stage", "message": "📖 海梅自主启动步骤4：后旺生成设计文档..."})

    tasks = [
        _run_doc_sub_flow(
            project_id=project_id, slug=slug, docs_dir=docs_dir,
            cfg=cfg, requirement=requirement,
            project_name=proj_name, project_description=proj_desc, core_goal=core_goal,
        ) for cfg in cfgs_to_run
    ]
    results = await asyncio.gather(*tasks, return_exceptions=True)

    # 合并已有通过结果与新结果，记录异常信息
    all_results = list(existing_subs)
    error_details = []
    for r in results:
        if isinstance(r, dict):
            all_results.append({
                "key": r["key"], "label": r.get("label", ""),
                "passed": r.get("passed", False),
                "path": r.get("path", ""), "rounds": r.get("rounds", 1),
                "content": r.get("content", ""),  # 保存文档内容供后续步骤读取
            })
        elif isinstance(r, BaseException):
            err_msg = str(r)[:200]
            error_details.append(err_msg)
            logger.error(f"Step4 子流程异常: {err_msg}")

    if error_details:
        await broadcast(project_id, {"type": "progress", "message": f"⚠️ 部分子流程异常: {'; '.join(error_details[:3])}"})

    all_keyed = {r["key"]: r for r in all_results if isinstance(r, dict)}
    all_passed = len(all_keyed) == 4 and all(r.get("passed") for r in all_keyed.values())
    if all_passed:
        # 生成交接文档摘要
        doc_summary = "\n".join(
            f"- {r.get('label','')}: 已通过后荣检验（路径: {r.get('path','')}）"
            for r in all_keyed.values() if r.get("passed")
        )
        handover_content = (
            f"## 步骤4 架构设计完成\n\n"
            f"4份设计文档全部通过后荣QA检验。\n\n"
            f"### 文档清单\n{doc_summary}\n\n"
            f"### 给后富（HouFu）的说明\n"
            f"请读取上述文档，基于需求文档和4份设计文档建立完整的开发环境。"
        )
        engine.save_step4_artifacts({
            "sub_flow_results": list(all_keyed.values()), "status": "done", "qa_passed": True,
            "handover_doc": handover_content,
        })
        engine.complete_step(4)
        engine.pass_qa(4)
        await broadcast(project_id, {"type": "done", "message": "✅ 海梅完成步骤4"})

        # Step4 完成后立即调度 Step5，不等监督循环
        try:
            engine.advance_step(5)
            loop = asyncio.get_running_loop()
            from app.services.haimei_auto_execute import auto_dispatch_step as _dispatch
            loop.create_task(_dispatch(project_id, 5, db))
            logger.info(f"海梅在 Step4 完成后立即调度了 Step5")
        except Exception as e:
            logger.warning(f"Step4→Step5 自动衔接失败: {e}")
    else:
        passed_count = sum(1 for r in all_keyed.values() if r.get("passed"))
        msg = f"❌ {passed_count}/4 子流程通过"
        engine.save_step4_artifacts({"sub_flow_results": list(all_keyed.values()), "status": "error", "message": msg})
        engine.reset_step(4)
        await broadcast(project_id, {"type": "error", "message": msg})


@register_step_executor(5)
async def _auto_step5(project_id: str, engine: WorkflowEngine, db):
    """Step5: houfu 环境搭建 — 单次提示词，不收斂不循环"""
    import os as _os
    from app.services.gateway_client import GatewayClient
    from app.config import settings

    step3 = engine.get_step3_artifacts() or {}
    requirement = (step3.get("doc_content") or step3.get("content") or
                   step3.get("requirement") or step3.get("srs") or "")
    step4 = engine.get_step4_artifacts() or {}
    subs = step4.get("sub_flow_results") or []
    step2 = engine.get_step2_artifacts() or {}
    core_goal = step2.get("confirmed_goal") or step2.get("core_goal") or ""

    design_summary = "\n".join(
        f"=== {doc.get('label', '设计文档')} ===\n{doc.get('content', '')}"
        for doc in subs if doc.get("content")
    )

    from app.models.project import Project
    proj = db.query(Project).filter(Project.id == project_id).first()
    slug = proj.slug if proj else project_id.replace("-", "")
    docs_dir = _os.path.join(settings.PROJECTS_BASE_DIR, slug, "docs")
    _os.makedirs(docs_dir, exist_ok=True)
    gen_path = _os.path.join(docs_dir, f"{slug}_env_V1.md")

    prompt = (
        "你是资深CI/CD工程师后富（HouFu），负责建立软件开发环境。\n\n"
        f"=== 需求文档 ===\n{requirement}\n\n"
        f"=== 设计文档 ===\n{design_summary}\n\n"
        "读取本项目的需求文档和设计文档，建立本项目的开发环境。\n"
        f"请将部署配置保存到：{gen_path}\n"
        "要求：代码仓库初始化、框架搭建、依赖配置、数据库初始化、CI/CD流水线配置\n"
        "不要输出推理过程。"
    )

    houfu = GatewayClient(profile_name="houfu", timeout=1200)
    chunks = []
    try:
        async for chunk in houfu.chat_isolated(
            messages=[{"role": "user", "content": prompt}],
            project_id=project_id, project_name=proj.name if proj else "",
            project_description=proj.description if proj else "", core_goal=core_goal,
            agent_name="后富（HouFu）CI/CD工程师",
            stream=True, max_tokens=64000,
        ):
            if chunk.strip():
                chunks.append(chunk)
    except Exception as e:
        logger.error(f"Step5 houfu调用失败: {e}")
        engine.reset_step(5)
        return

    content = "".join(chunks).strip()
    with open(gen_path, "w", encoding="utf-8") as f:
        f.write(content)

    engine.save_step5_artifacts({
        "env_info": content, "doc_path": gen_path,
        "status": "done", "message": "✅ 开发环境已建立完毕",
    })
    engine.complete_step(5)
    engine.pass_qa(5)
    logger.info(f"Step5 完成，已保存到 {gen_path}")


@register_step_executor(6)
async def _auto_step6(project_id: str, engine: WorkflowEngine, db):
    await _auto_generic_step(project_id, engine, db, 6, "haimei",
        TDD_PLAN_DIMENSIONS, "海梅（HaiMei）-TDD计划制订",
        {
            "name": "tdd_plan",
            "prefix": "tddplan",
            "prompt": lambda ctx: [
                "你是资深项目经理海梅（HaiMei），负责制订TDD测试用例编写计划。\n",
                f"=== 需求文档 ===\n{ctx['requirement']}\n\n",
                f"=== 架构设计文档 ===\n{ctx['design_doc']}\n\n",
                ctx.get("feedback", ""),
                f"请将完整计划保存到：{ctx['gen_path']}\n"
                "要求：每个测试用例最小原子化、有可量化验收标准、覆盖所有需求、标注优先级\n不要输出推理过程。",
            ],
            "inputs": {"step3": "requirement", "step4": "design_doc"},
        }
    )


@register_step_executor(7)
async def _auto_step7(project_id: str, engine: WorkflowEngine, db):
    await _auto_generic_step(project_id, engine, db, 7, "houfa",
        TDD_TESTCASE_DIMENSIONS, "后发（HouFa）-TDD用例编写",
        {
            "name": "tdd_cases",
            "prefix": "tdctest",
            "prompt": lambda ctx: [
                "你是资深程序员后发（HouFa），负责编写完整的TDD测试用例。\n",
                f"=== 需求文档 ===\n{ctx['requirement']}\n\n",
                f"=== 架构设计文档 ===\n{ctx['design_doc']}\n\n",
                f"=== TDD测试用例编写计划 ===\n{ctx['tdd_plan']}\n\n",
                ctx.get("feedback", ""),
                f"请将完整测试用例保存到：{ctx['gen_path']}\n"
                "要求：每个测试用例最小原子化、有可量化验收标准、按计划执行\n不要输出推理过程。",
            ],
            "inputs": {"step3": "requirement", "step4": "design_doc", "step6": "tdd_plan"},
        }
    )


@register_step_executor(8)
async def _auto_step8(project_id: str, engine: WorkflowEngine, db):
    await _auto_generic_step(project_id, engine, db, 8, "haimei",
        CODE_PLAN_DIMENSIONS, "海梅（HaiMei）-编码计划制订",
        {
            "name": "code_plan",
            "prefix": "codeplan",
            "prompt": lambda ctx: [
                "你是资深项目经理海梅（HaiMei），负责制订代码编写计划和任务依赖图。\n",
                f"=== 需求文档 ===\n{ctx['requirement']}\n\n",
                f"=== 架构设计文档 ===\n{ctx['design_doc']}\n\n",
                f"=== TDD测试用例 ===\n{ctx['tdd_cases']}\n\n",
                ctx.get("feedback", ""),
                f"请将完整计划保存到：{ctx['gen_path']}\n"
                "要求：每个任务最小原子化、有TDD用例对应、画出依赖图、标注优先级\n不要输出推理过程。",
            ],
            "inputs": {"step3": "requirement", "step4": "design_doc", "step7": "tdd_cases"},
        }
    )


@register_step_executor(9)
async def _auto_step9(project_id: str, engine: WorkflowEngine, db):
    await _auto_generic_step(project_id, engine, db, 9, "houfa",
        CODE_INSPECTION_DIMENSIONS, "后发（HouFa）-功能代码编写",
        {
            "name": "code",
            "prefix": "code",
            "prompt": lambda ctx: [
                "你是资深程序员后发（HouFa），负责建立Agent蜂群编写功能代码。\n",
                f"=== 需求文档 ===\n{ctx['requirement']}\n\n",
                f"=== 架构设计文档 ===\n{ctx['design_doc']}\n\n",
                f"=== 代码编写计划 ===\n{ctx['code_plan']}\n\n",
                f"=== 任务依赖图 ===\n{ctx['dep_graph']}\n\n",
                f"=== TDD测试用例 ===\n{ctx['tdd_cases']}\n\n",
                ctx.get("feedback", ""),
                f"请将完整代码保存到：{ctx['gen_path']}\n"
                "要求：按依赖拓扑顺序、先TDD后实现、符合架构选型、清晰注释\n不要输出推理过程。",
            ],
            "inputs": {"step3": "requirement", "step4": "design_doc", "step7": "tdd_cases", "step8": ["code_plan", "dep_graph"]},
        }
    )


@register_step_executor(10)
async def _auto_step10(project_id: str, engine: WorkflowEngine, db):
    await _auto_generic_step(project_id, engine, db, 10, "houfu",
        DEPLOY_TEST_DIMENSIONS, "后富（HouFu）-测试环境部署",
        {
            "name": "deployment_log",
            "prefix": "deploytest",
            "prompt": lambda ctx: [
                "你是资深CI/CD工程师后富（HouFu），负责将代码部署到测试环境。\n",
                f"=== 需求文档 ===\n{ctx['requirement']}\n\n",
                f"=== 架构设计文档 ===\n{ctx['design_doc']}\n\n",
                f"=== 开发环境信息 ===\n{ctx['env_info']}\n\n",
                f"=== 功能代码 ===\n{ctx['code']}\n\n",
                ctx.get("feedback", ""),
                f"请将部署报告保存到：{ctx['gen_path']}\n"
                "要求：准备测试环境、配置部署脚本、执行部署并验证\n不要输出推理过程。",
            ],
            "inputs": {"step3": "requirement", "step4": "design_doc", "step5": "env_info", "step9": "code"},
        }
    )


@register_step_executor(11)
async def _auto_step11(project_id: str, engine: WorkflowEngine, db):
    await _auto_generic_step(project_id, engine, db, 11, "houda",
        TEST_INSPECTION_DIMENSIONS, "后达（HouDa）-全面测试",
        {
            "name": "test_report",
            "prefix": "testrep",
            "prompt": lambda ctx: [
                "你是资深测试员后达（HouDa），负责建立Agent蜂群执行全面测试。\n",
                f"=== 需求文档 ===\n{ctx['requirement']}\n\n",
                f"=== 功能代码 ===\n{ctx['code']}\n\n",
                f"=== 测试环境部署日志 ===\n{ctx['deployment_log']}\n\n",
                ctx.get("feedback", ""),
                f"请将测试报告保存到：{ctx['gen_path']}\n"
                "要求：单元测试、模块测试、集成测试、前端验证、缺陷清单\n不要输出推理过程。",
            ],
            "inputs": {"step3": "requirement", "step9": "code", "step10": "deployment_log"},
        }
    )


@register_step_executor(12)
async def _auto_step12(project_id: str, engine: WorkflowEngine, db):
    await _auto_generic_step(project_id, engine, db, 12, "houhua",
        SECURITY_INSPECTION_DIMENSIONS, "后华（HouHua）-安全审计",
        {
            "name": "security_report",
            "prefix": "security",
            "prompt": lambda ctx: [
                "你是资深安全员后华（HouHua），负责执行安全审计。\n",
                f"=== 架构设计文档 ===\n{ctx['design_doc']}\n\n",
                f"=== 功能代码 ===\n{ctx['code']}\n\n",
                ctx.get("feedback", ""),
                f"请将安全审计报告保存到：{ctx['gen_path']}\n"
                "要求：代码审计、合规审查、渗透测试、漏洞修复建议\n不要输出推理过程。",
            ],
            "inputs": {"step4": "design_doc", "step9": "code"},
        }
    )


@register_step_executor(13)
async def _auto_step13(project_id: str, engine: WorkflowEngine, db):
    await _auto_generic_step(project_id, engine, db, 13, "houfu",
        DEPLOY_PROD_DIMENSIONS, "后富（HouFu）-生产环境部署",
        {
            "name": "deployment_log",
            "prefix": "deployprod",
            "prompt": lambda ctx: [
                "你是资深CI/CD工程师后富（HouFu），负责将代码部署到生产环境。\n",
                f"=== 功能代码 ===\n{ctx['code']}\n\n",
                f"=== 测试报告 ===\n{ctx['test_report']}\n\n",
                f"=== 安全审计报告 ===\n{ctx['security_report']}\n\n",
                ctx.get("feedback", ""),
                f"请将部署报告保存到：{ctx['gen_path']}\n"
                "要求：准备生产环境、配置部署脚本、执行部署并验证\n不要输出推理过程。",
            ],
            "inputs": {"step9": "code", "step11": "test_report", "step12": "security_report"},
        }
    )


@register_step_executor(14)
async def _auto_step14(project_id: str, engine: WorkflowEngine, db):
    await _auto_generic_step(project_id, engine, db, 14, "hougui",
        DOC_INSPECTION_DIMENSIONS, "后贵（HouGui）-项目文档",
        {
            "name": "documentation",
            "prefix": "projectdoc",
            "prompt": lambda ctx: [
                "你是资深文档管理员后贵（HouGui），负责完善项目文档。\n",
                f"=== 需求文档 ===\n{ctx['requirement']}\n\n",
                f"=== 架构设计文档 ===\n{ctx['design_doc']}\n\n",
                f"=== 功能代码 ===\n{ctx['code']}\n\n",
                f"=== 测试报告 ===\n{ctx['test_report']}\n\n",
                f"=== 安全审计报告 ===\n{ctx['security_report']}\n\n",
                ctx.get("feedback", ""),
                f"请将完整文档保存到：{ctx['gen_path']}\n"
                "要求：部署手册、操作手册、API文档、用户手册、文档一致性\n不要输出推理过程。",
            ],
            "inputs": {"step3": "requirement", "step4": "design_doc", "step9": "code",
                       "step11": "test_report", "step12": "security_report"},
        }
    )


# ── 通用执行函数（步骤 5-14 共用） ──

async def _auto_generic_step(
    project_id: str, engine: WorkflowEngine, db,
    step_number: int, profile_name: str,
    dimensions: list, agent_name: str,
    config: dict,
) -> None:
    """通用步骤执行：生成→检验→修复收敛循环（仿 step 文件 _generate 逻辑）"""
    import json as _json, asyncio as _asyncio, re as _re, glob as _glob
    from app.services.gateway_client import GatewayClient
    from app.config import settings

    broadcast = _get_broadcast(step_number)
    step_key = config["name"]
    slug = project_id.replace("-", "")
    docs_dir = _os.path.join(settings.PROJECTS_BASE_DIR, slug, "docs")
    _os.makedirs(docs_dir, exist_ok=True)

    # 加载项目信息
    from app.models.project import Project
    proj = db.query(Project).filter(Project.id == project_id).first()
    proj_name = proj.name if proj else ""
    proj_desc = proj.description or ""
    step2 = engine.get_step2_artifacts() or {}
    core_goal = step2.get("confirmed_goal") or step2.get("core_goal") or ""

    # 解析输入
    ctx = {}
    for src_step, keys in config["inputs"].items():
        src_num = int(src_step.replace("step", ""))
        artifacts = engine.get_step_artifacts(src_num) or {}
        if isinstance(keys, list):
            for k in keys:
                ctx[k] = artifacts.get(k, artifacts.get("content", ""))
        elif keys.startswith("step4_"):
            # 特殊处理：从 step4 的 sub_flow_results 提取文档列表
            subs = artifacts.get("sub_flow_results") or []
            ctx[keys] = subs
        else:
            ctx[keys] = artifacts.get(keys, artifacts.get("content", ""))

    # 续跑检查
    existing = engine.get_step_artifacts(step_number) or {}
    if existing.get("qa_passed") and existing.get("doc_path") and _os.path.exists(existing["doc_path"]):
        await broadcast(project_id, {"type": "progress", "message": f"♻️ 续跑：步骤{step_number}已通过，跳过"})
        engine.complete_step(step_number)
        engine.pass_qa(step_number)
        await broadcast(project_id, {"type": "done", "message": f"✅ 步骤{step_number}已完成（续跑）"})
        # 立即启动下一步
        next_n = step_number + 1
        if next_n <= 14:
            try:
                engine.advance_step(next_n)
                loop = _asyncio.get_running_loop()
                loop.create_task(auto_dispatch_step(project_id, next_n, db))
                logger.info(f"续跑完成后立即调度步骤{next_n}")
            except Exception as e:
                logger.warning(f"续跑后步骤{step_number}→{next_n} 衔接失败: {e}")
        return

    # 扫描已有文档版本
    max_ver = 0
    for f in _glob.glob(_os.path.join(docs_dir, f"{slug}_{config['prefix']}_V*.md")):
        m = _re.search(r'V(\d+)', _os.path.basename(f))
        if m:
            max_ver = max(max_ver, int(m.group(1)))

    convergence_log = []
    timeout_map = {5: 1200, 6: 3600, 7: 7200, 8: 5400, 9: 10800, 10: 3600, 11: 10800, 12: 3600, 13: 3600, 14: 3600}
    timeout = timeout_map.get(step_number, 3600)

    # 发送初始化消息
    init_messages = {
        5: "🔧 后富正在建立开发环境...",
    }
    init_msg = init_messages.get(step_number, f"🔧 {agent_name}开始工作...")
    await broadcast(project_id, {"type": "progress", "message": init_msg})

    for fix_round in range(1, 11):
        nv = max_ver + fix_round
        gen_path = _os.path.join(docs_dir, f"{slug}_{config['prefix']}_V{nv}.md")
        ctx["gen_path"] = gen_path
        ctx["requirement"] = ctx.get("requirement", "")
        ctx["design_doc"] = ctx.get("design_doc", "")
        ctx["env_info"] = ctx.get("env_info", "")
        ctx["tdd_plan"] = ctx.get("tdd_plan", "")
        ctx["tdd_cases"] = ctx.get("tdd_cases", "")
        ctx["code_plan"] = ctx.get("code_plan", "")
        ctx["dep_graph"] = _json.dumps(ctx.get("dep_graph", {}), ensure_ascii=False) if isinstance(ctx.get("dep_graph"), dict) else str(ctx.get("dep_graph", ""))
        ctx["code"] = ctx.get("code", "")
        ctx["deployment_log"] = ctx.get("deployment_log", "")
        ctx["test_report"] = ctx.get("test_report", "")
        ctx["security_report"] = ctx.get("security_report", "")

        # 构建反馈
        if fix_round > 1 and convergence_log:
            last = convergence_log[-1]
            failed = last.get("failed_details", [])
            ctx["feedback"] = f"=== 上次检验未通过项 ===\n需要修正的问题（只修复这些问题，禁止扩大范围）：\n" + "\n".join(f"- {d}" for d in failed if d) + "\n\n只针对不合格项修改，不要扩大修改范围。\n\n"
        else:
            ctx["feedback"] = ""

        prompt_text = "\n".join(config["prompt"](ctx))

        await broadcast(project_id, {"type": "progress", "message": f"🔧 {profile_name}正在{'修复' if fix_round > 1 else '生成'}（第{fix_round}轮）..."})

        # 生成
        gen_client = GatewayClient(profile_name=profile_name, timeout=timeout)
        chunks = []
        async for chunk in gen_client.chat_isolated(
            messages=[{"role": "user", "content": prompt_text}],
            project_id=project_id, project_name=proj_name, project_description=proj_desc,
            core_goal=core_goal, agent_name=agent_name,
            stream=True, max_tokens=64000,
        ):
            if chunk.strip():
                chunks.append(chunk)
                await broadcast(project_id, {"type": "progress", "content": chunk})

        # 读取文件
        if _os.path.exists(gen_path):
            content = open(gen_path, "r", encoding="utf-8").read()
        else:
            content = "".join(chunks).strip()
            with open(gen_path, "w", encoding="utf-8") as f:
                f.write(content)

        if not content.strip():
            await broadcast(project_id, {"type": "progress", "message": "❌ 未生成有效内容，重试"})
            continue

        engine.save_step_artifacts(step_number, {step_key: content, "doc_path": gen_path, "status": "generating"})

        # ── hourong 检验（带重试和结构化结果） ──
        await broadcast(project_id, {"type": "progress", "message": f"🔍 后荣正在检验（第{fix_round}轮）"})
        dims_json = str([{'检验项目': d['label'], '检验标准': d['description'], '检验维': d['key']} for d in dimensions])

        parsed = None
        for qa_attempt in range(1, 4):  # 最多重试 3 次
            retry_hint = ""
            if qa_attempt > 1:
                retry_hint = f"\n\n⚠️ 你第{qa_attempt-1}次的输出不是合法JSON数组。只输出 JSON，不要有任何其他文字、推理、解释。\n"

            insp_prompt = (
                f"你是一个专业的QA检验员（后荣）。请严格检验以下内容。\n\n"
                f"=== 检验项目与标准 ===\n{dims_json}\n\n"
                f"=== 文档路径 ===\n{gen_path}\n\n"
                f"请读取该文档文件，严格逐项检验。\n只输出 JSON 数组，不要有其他文字:{retry_hint}\n"
                + ",\n".join(f'  {{"key": "{d["key"]}", "passed": true/false, "detail": "具体检验意见..."}}' for d in dimensions)
            )
            qa_cli = GatewayClient(profile_name="hourong", timeout=180)
            qa_chunks = []
            async for chunk in qa_cli.chat_isolated(
                messages=[{"role": "user", "content": insp_prompt}],
                project_id=project_id, project_name=proj_name, project_description=proj_desc,
                core_goal=core_goal, agent_name=f"后荣-步骤{step_number}QA检验员",
                stream=True, max_tokens=8192,
            ):
                qa_chunks.append(chunk)
            qa_r = "".join(qa_chunks).strip()

            if qa_r:
                brace_s, brace_e = qa_r.find('['), qa_r.rfind(']') + 1
                if brace_s != -1 and brace_e > brace_s:
                    qa_r = qa_r[brace_s:brace_e]
                try:
                    parsed = _json.loads(qa_r)
                    if isinstance(parsed, list) and len(parsed) > 0:
                        break  # 解析成功
                except Exception:
                    parsed = None

            if qa_attempt < 3:
                await broadcast(project_id, {"type": "progress", "message": f"⚠️ 后荣返回了无法解析的检验报告，正在重试（第{qa_attempt}次）"})

        # 发送结构化检验结果给前端
        if isinstance(parsed, list) and parsed:
            await broadcast(project_id, {
                "type": "result",
                "dimensions": [
                    {"key": d.get("key",""), "label": "", "passed": bool(d.get("passed")), "detail": d.get("detail","")}
                    for d in parsed
                ],
                "all_passed": all(bool(r.get("passed")) for r in parsed),
            })

        if isinstance(parsed, list) and parsed:
            all_passed = all(bool(r.get("passed")) for r in parsed)
            failed_details = [r.get("detail", "") for r in parsed if not r.get("passed")]
            convergence_log.append({"round": fix_round, "passed": all_passed, "failed_details": failed_details})

            if all_passed:
                await broadcast(project_id, {"type": "progress", "message": f"✅ 后荣检验全部通过（共{fix_round}轮），后富工作完成"})
                engine.save_step_artifacts(step_number, {step_key: content, "doc_path": gen_path, "convergence": convergence_log, "status": "done", "qa_passed": True, "message": f"✅ 步骤{step_number}完成"})
                engine.complete_step(step_number)
                engine.pass_qa(step_number)
                await broadcast(project_id, {"type": "done", "message": f"✅ 步骤{step_number}已完成"})
                # 立即启动下一步（步骤 4-14 自动串联）
                next_n = step_number + 1
                if next_n <= 14:
                    try:
                        engine.advance_step(next_n)
                        loop = _asyncio.get_running_loop()
                        loop.create_task(auto_dispatch_step(project_id, next_n, db))
                        logger.info(f"步骤{step_number}完成后立即调度步骤{next_n}")
                    except Exception as e:
                        logger.warning(f"步骤{step_number}→{next_n} 衔接失败: {e}")
                return
            else:
                failed_summary = "；".join(failed_details[:3]) if failed_details else "部分检验项目未通过"
                await broadcast(project_id, {"type": "progress", "message": f"⚠️ 后荣检验未通过，问题摘要：{failed_summary[:200]}"})
                await broadcast(project_id, {"type": "progress", "message": f"📝 后荣发来检验报告，需要{agent_name}修改（第{fix_round}轮修复）"})
        else:
            convergence_log.append({"round": fix_round, "passed": False, "failed_details": ["后荣未返回有效的检验报告"]})
            await broadcast(project_id, {"type": "progress", "message": f"⚠️ 后荣未能返回有效的检验报告，{agent_name}将在下一轮重试"})

    await broadcast(project_id, {"type": "error", "message": f"❌ 步骤{step_number}经10轮仍未通过检验"})
    engine.save_step_artifacts(step_number, {"status": "error", "message": "经10轮仍未通过检验"})
    engine.reset_step(step_number)


# 导入检验维度
from app.api.workflow.core import (
    ENV_SETUP_DIMENSIONS,
    TDD_PLAN_DIMENSIONS, TDD_TESTCASE_DIMENSIONS,
    CODE_PLAN_DIMENSIONS,
    CODE_INSPECTION_DIMENSIONS,
    TEST_INSPECTION_DIMENSIONS,
    SECURITY_INSPECTION_DIMENSIONS,
    DOC_INSPECTION_DIMENSIONS,
    DEPLOY_TEST_DIMENSIONS,
    DEPLOY_PROD_DIMENSIONS,
)