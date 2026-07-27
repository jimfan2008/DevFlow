"""
Haimei Dispatch - 海梅自主调度引擎
每个 dispatch_{step} 函数包含步骤的完整执行逻辑（提取自 step{N}.py 的 _generate），
让海梅在 haimei_auto_advance 中自主触发各步骤执行。
"""
from __future__ import annotations

import asyncio
import logging
import os
import re
from typing import Any, Dict, List

from app.services.workflow_engine import WorkflowEngine
from app.config import settings

logger = logging.getLogger("devflow.haimei.dispatch")


async def _dispatch_internal(
    project_id: str,
    engine: WorkflowEngine,
    step_number: int,
    profile_name: str,
    initial_msg: str,
    artifacts_key: str,
    build_prompt_fn,
    post_process_fn=None,
    expected_artifacts_keys: List[str] = None,
):
    """通用异步执行框架：读取前置产物 → 构造 prompt → 调用 Agent → 保存结果 → 完成步骤"""
    from app.services.gateway_client import GatewayClient
    from app.api.ws.step4_progress import broadcast

    engine.save_step_artifacts(step_number, {"status": "generating", "message": initial_msg})

    await broadcast(project_id, {"type": "stage", "message": initial_msg})

    prompt_lines = build_prompt_fn(engine, project_id)
    prompt = "\n".join(prompt_lines)

    full_reply: List[str] = []
    timeout = 3600
    client = GatewayClient(profile_name=profile_name, timeout=timeout)

    async for chunk in client.chat_completions(
        messages=[{"role": "user", "content": prompt}],
        stream=True,
        max_tokens=65536,
    ):
        full_reply.append(chunk)
        if len(full_reply) % 20 == 0:
            char_count = len("".join(full_reply))
            await broadcast(project_id, {
                "type": "progress",
                "message": f"⏳ {profile_name} 正在执行中...（已生成 {char_count} 字符）",
            })

    reply = "".join(full_reply).strip()

    if reply and len(reply) >= 50:
        # 默认保存策略
        save_keys = expected_artifacts_keys or [artifacts_key]
        artifacts = {
            key: reply for key in save_keys
        }
        artifacts["status"] = "done"
        artifacts["message"] = f"✅ 步骤{step_number}执行完成"

        if post_process_fn:
            artifacts = await post_process_fn(reply, artifacts, engine, project_id)

        engine.save_step_artifacts(step_number, artifacts)
        engine.complete_step(step_number)
        await broadcast(project_id, {"type": "done", "message": artifacts["message"]})
    else:
        engine.save_step_artifacts(step_number, {
            "status": "error",
            "message": f"❌ Agent {profile_name} 未生成有效内容",
        })
        engine.reset_step(step_number)
        await broadcast(project_id, {"type": "error", "message": f"❌ Agent {profile_name} 未生成有效内容"})


# ============================================================
# Step 4: 后旺架构设计
# ============================================================

async def dispatch_step4(project_id: str, engine: WorkflowEngine) -> None:
    """海梅调度步骤4：后旺并行执行4个子流程（架构/前端/后端/数据库）"""
    from app.database import SessionLocal
    from app.api.ws.step4_progress import broadcast

    bg_db = SessionLocal()
    try:
        bg_engine = WorkflowEngine(project_id=project_id, db=bg_db)
        await _dispatch_step4_internal(project_id, bg_engine)
    except Exception as e:
        logger.error(f"Step4 dispatch failed: {e}", exc_info=True)
    finally:
        bg_db.close()


async def _dispatch_step4_internal(project_id: str, engine: WorkflowEngine) -> None:
    """步骤4的核心逻辑（从 step4.py 的 execute_step4 提取）"""
    from app.database import SessionLocal
    from app.api.ws.step4_progress import broadcast
    from app.models.project import Project as _Project

    # 复用 step4.py 中的辅助函数和新子步骤函数
    from app.api.workflow.step4 import (
        SUB_FLOW_CONFIGS,
        _sub_step4_1, _sub_step4_2, _sub_step4_3, _sub_step4_4,
        _save_sub_result, _SubStepError,
    )

    step3 = engine.get_step3_artifacts() or {}
    requirement = (
        step3.get("doc_content") or step3.get("content") or
        step3.get("requirement") or step3.get("srs") or ""
    )

    if not requirement:
        logger.error("Step4: 未找到 Step3 需求文档")
        engine.reset_step(4)
        await broadcast(project_id, {"type": "error", "message": "❌ 未找到 Step3 需求文档"})
        return

    _existing = engine.get_step4_artifacts() or {}
    engine.save_step4_artifacts({
        **_existing,
        "status": "generating",
        "message": "🚀 海梅已调度4个子步骤串行——step4_1(架构)→step4_2(前端)→step4_3(后端)→step4_4(数据库)...",
    })

    doc_path = step3.get("doc_path", "")
    proj = engine.db.query(_Project).filter(_Project.id == project_id).first()
    slug = proj.slug if proj else project_id.replace("-", "")
    docs_dir = os.path.join(settings.PROJECTS_BASE_DIR, slug, "docs")
    os.makedirs(docs_dir, exist_ok=True)

    step2 = engine.get_step2_artifacts() or {}
    core_goal = step2.get("confirmed_goal") or step2.get("core_goal") or ""
    proj_name = proj.name if proj else ""
    proj_desc = proj.description or ""

    # ── 续跑检测 ──
    existing_sub_results = (engine.get_step4_artifacts() or {}).get("sub_flow_results", [])
    passed_keys = {r["key"] for r in existing_sub_results if r.get("passed")}

    await broadcast(project_id, {"type": "stage", "message": "📖 后旺正在读取需求文档..."})

    all_results = []
    try:
        # ── step4_1: 架构设计 ──
        if "arch_reasonableness" in passed_keys:
            await broadcast(project_id, {"type": "stage", "message": "♻️ step4_1(架构设计) 上次已通过，跳过"})
            arch_result = next((r for r in existing_sub_results if r["key"] == "arch_reasonableness"), {})
        else:
            arch_result = await _sub_step4_1(
                project_id, slug, docs_dir, requirement, doc_path,
                proj_name, proj_desc, core_goal, engine, engine.db,
            )
            if not arch_result.get("passed"):
                raise _SubStepError("step4_1 未通过", arch_result)
        all_results.append(arch_result)

        # ── step4_2: 前端设计 ──
        if "frontend_feasibility" in passed_keys:
            await broadcast(project_id, {"type": "stage", "message": "♻️ step4_2(前端设计) 上次已通过，跳过"})
            frontend_result = next((r for r in existing_sub_results if r["key"] == "frontend_feasibility"), {})
        else:
            frontend_result = await _sub_step4_2(
                project_id, slug, docs_dir, requirement, doc_path,
                proj_name, proj_desc, core_goal, engine, engine.db,
                arch_result,
            )
            if not frontend_result.get("passed"):
                raise _SubStepError("step4_2 未通过", frontend_result)
        all_results.append(frontend_result)

        # ── step4_3: 后端设计 ──
        if "backend_feasibility" in passed_keys:
            await broadcast(project_id, {"type": "stage", "message": "♻️ step4_3(后端设计) 上次已通过，跳过"})
            backend_result = next((r for r in existing_sub_results if r["key"] == "backend_feasibility"), {})
        else:
            backend_result = await _sub_step4_3(
                project_id, slug, docs_dir, requirement, doc_path,
                proj_name, proj_desc, core_goal, engine, engine.db,
                arch_result, frontend_result,
            )
            if not backend_result.get("passed"):
                raise _SubStepError("step4_3 未通过", backend_result)
        all_results.append(backend_result)

        # ── step4_4: 数据库设计 ──
        if "database_design" in passed_keys:
            await broadcast(project_id, {"type": "stage", "message": "♻️ step4_4(数据库设计) 上次已通过，跳过"})
            db_result = next((r for r in existing_sub_results if r["key"] == "database_design"), {})
        else:
            db_result = await _sub_step4_4(
                project_id, slug, docs_dir, requirement, doc_path,
                proj_name, proj_desc, core_goal, engine, engine.db,
                backend_result,
            )
            if not db_result.get("passed"):
                raise _SubStepError("step4_4 未通过", db_result)
        all_results.append(db_result)

        # ── 全部通过 → 保存交接文档 → 推进到 step5 ──
        design_parts = []
        doc_paths = {}
        for r in all_results:
            content = r.get("content", "")
            if not content.strip() and r.get("path", ""):
                try:
                    with open(r["path"], "r", encoding="utf-8") as _f:
                        content = _f.read()
                except Exception:
                    pass
            if content.strip():
                design_parts.append(f"# {r['label']}\n\n{content}")
                doc_paths[r["key"]] = r.get("path", "")

        full_design = "\n\n---\n\n".join(design_parts) if design_parts else ""
        passed_count = sum(1 for r in all_results if r.get("passed"))
        sub_flow_detail = "; ".join(
            f"{r['label']}: {'✅' if r.get('passed') else '❌'}({r.get('rounds', 0)}轮)"
            for r in all_results
        )

        if full_design and len(full_design) >= 50:
            artifacts = {
                "design_doc": full_design,
                "requirement_source": requirement[:200],
                "status": "done",
                "message": f"✅ Step4 全部完成（{passed_count}/4 通过）\n{sub_flow_detail}",
                "docs_dir": docs_dir,
                "doc_paths": doc_paths,
                "sub_flow_results": [
                    {
                        "key": r["key"], "label": r["label"],
                        "passed": r.get("passed", False),
                        "rounds": r.get("rounds", 0),
                        "convergence": r.get("convergence", []),
                    }
                    for r in all_results
                ],
                "qa_passed": True,
                "qa_checked": True,
            }
            if doc_path:
                artifacts["requirement_doc_path"] = doc_path

            engine.save_step4_artifacts(artifacts)
            engine.complete_step(4)
            engine.pass_qa(4)
            engine.db.commit()
            engine.advance_step(5)
            engine.db.commit()
            await broadcast(project_id, {
                "type": "done",
                "message": f"✅ Step4 全部 4 个子步骤通过 houwang→hourong 检验与一致性检验，交接文档已保存，已自动推进至第5步\n{sub_flow_detail}",
            })
        else:
            engine.save_step4_artifacts({
                "status": "error",
                "message": "❌ 子步骤未生成有效设计文档，请重新执行",
            })
            engine.reset_step(4)
            await broadcast(project_id, {"type": "error", "message": "❌ 子步骤未生成有效设计文档，请重新执行"})

    except _SubStepError as e:
        failed_result = e.result
        engine.save_step4_artifacts({
            "status": "qa_failed",
            "qa_passed": False,
            "qa_checked": True,
            "message": f"⚠️ {e.message}: {failed_result.get('label', '')} 未通过检验",
        })
        await broadcast(project_id, {
            "type": "done",
            "message": f"⚠️ {e.message}，请修复后重试或续跑",
        })


# ============================================================
# Step 5: 后富建立开发环境
# ============================================================

async def dispatch_step5(project_id: str, engine: WorkflowEngine) -> None:
    """海梅调度步骤5：后富建立开发环境"""
    from app.api.ws.step5_progress import broadcast
    from app.services.gateway_client import GatewayClient

    step3 = engine.get_step3_artifacts() or {}
    requirement = (
        step3.get("doc_content") or step3.get("content") or
        step3.get("requirement") or step3.get("srs") or ""
    )
    step4 = engine.get_step4_artifacts() or {}
    design_doc = step4.get("design_doc") or ""

    engine.save_step5_artifacts({"status": "generating", "message": "🔧 海梅已调度后富建立开发环境..."})
    await broadcast(project_id, {"type": "stage", "message": "📖 后富正在读取需求说明书和设计文档..."})

    prompt_lines = ["你是资深CI/CD工程师后富（HouFu），负责建立软件开发环境。\n"]
    if requirement:
        prompt_lines.append(f"=== 需求文档（SRS）===\n{requirement[:2000]}\n\n")
    if design_doc:
        prompt_lines.append(f"=== 架构设计文档 ===\n{design_doc[:3000]}\n\n")
    prompt_lines.append(
        "请根据上述文档建立完整的开发环境，包括：\n"
        "1. 代码仓库初始化（Git仓库结构、分支策略）\n"
        "2. 开发框架搭建（前端/后端框架配置）\n"
        "3. 依赖配置（package.json/requirements.txt/pom.xml等）\n"
        "4. 数据库初始化（DDL脚本、初始数据）\n"
        "5. CI/CD流水线配置（Docker、Docker Compose、CI/CD）"
    )
    prompt = "\n".join(prompt_lines)

    full_reply = []
    client = GatewayClient(profile_name="houfu", timeout=1800)
    async for chunk in client.chat_completions(
        messages=[{"role": "user", "content": prompt}], stream=True, max_tokens=65536
    ):
        full_reply.append(chunk)
        if len(full_reply) % 20 == 0:
            await broadcast(project_id, {
                "type": "progress",
                "message": f"🔧 后富持续建立环境中...（已生成 {len(''.join(full_reply))} 字符）",
            })

    reply = "".join(full_reply).strip()
    if reply and len(reply) >= 50:
        engine.save_step5_artifacts({
            "env_info": reply,
            "requirement_source": requirement[:200],
            "design_source": design_doc[:200],
            "status": "done",
            "message": "✅ 开发环境建立完成",
        })
        engine.complete_step(5)
        await broadcast(project_id, {"type": "done", "message": "✅ 开发环境已建立，等待 QA 检验"})
    else:
        engine.save_step5_artifacts({"status": "error", "message": "❌ 后富未生成有效环境配置"})
        engine.reset_step(5)
        await broadcast(project_id, {"type": "error", "message": "❌ 后富未生成有效环境配置"})


# ============================================================
# Steps 6-14: 使用通用框架
# ============================================================

_STEP6_PROMPT = (
    "你是资深项目经理海梅（HaiMei），负责制订TDD测试用例编写计划。\n"
    "请根据需求文档和架构设计文档，制定完整的TDD测试用例编写计划。\n\n"
    "【要求】\n"
    "1. 每个测试用例必须是最小原子化的（不可再分）\n"
    "2. 每个测试用例必须有明确的、可量化的验收标准\n"
    "3. 测试用例必须覆盖所有功能需求和非功能需求\n"
    "4. 标注每个用例的优先级（P0/P1/P2）和执行顺序\n"
    "5. 按模块分类组织测试用例\n"
    "6. 明确每个用例的测试类型（单元/集成/端到端）\n"
    "直接输出计划内容，不需要输出思考过程。"
)

_STEP7_PROMPT = (
    "你是资深程序员后发（HouFa），负责建立Agent蜂群编写TDD测试用例。\n"
    "请根据TDD测试用例编写计划，建立Agent蜂群编写完整的TDD测试用例。\n\n"
    "【要求】\n"
    "1. 每个测试用例必须是最小原子化的（不可再分）\n"
    "2. 每个测试用例必须有明确的、可量化的验收标准\n"
    "3. 测试用例必须覆盖所有功能需求\n"
    "4. 按照计划中的优先级和执行顺序编写\n"
    "5. 每个测试用例必须能独立运行和验证\n"
    "直接输出测试用例代码，不需要输出思考过程。"
)

_STEP8_PROMPT = (
    "你是项目经理海梅（HaiMei），负责制订代码编写计划。\n"
    "请根据需求文档、架构设计文档和TDD测试用例，制订完整的代码编写计划。\n\n"
    "【要求】\n"
    "1. 每个代码编写任务必须是最小原子化的（不可再分）\n"
    "2. 每个任务必须与对应的TDD测试用例一一关联\n"
    "3. 有依赖关系的任务必须按照依赖关系画出任务依赖图\n"
    "4. 标注每个任务的优先级和执行顺序\n"
    "5. 标注每个任务的负责Agent\n"
    "直接输出计划内容，不需要输出思考过程。"
)

_STEP9_PROMPT = (
    "你是资深程序员后发（HouFa），负责建立Agent蜂群编写功能代码。\n"
    "请根据代码编写计划、需求文档、架构设计和TDD测试用例，编写完整的功能代码。\n\n"
    "【要求】\n"
    "1. 严格按照任务依赖图顺序执行\n"
    "2. 有依赖关系的任务，前置任务完成后再执行后继任务\n"
    "3. 每个模块独立完整，代码注释清晰\n"
    "4. 所有代码必须通过对应的TDD测试用例\n"
    "5. 遵循编码规范和最佳实践\n"
    "直接输出功能代码，不需要输出思考过程。"
)

_STEP10_PROMPT = (
    "你是资深CI/CD工程师后富（HouFu），负责将代码部署到测试环境。\n"
    "请根据代码库中的全部代码，部署到测试环境。\n\n"
    "【要求】\n"
    "1. 配置测试环境变量和依赖\n"
    "2. 部署数据库并执行迁移脚本\n"
    "3. 部署应用服务并验证启动成功\n"
    "4. 记录完整的部署日志\n"
    "5. 验证部署成功后应用可正常访问\n"
    "直接输出部署日志和环境配置，不需要输出思考过程。"
)

_STEP11_PROMPT = (
    "你是资深测试工程师后达（HouDa），负责执行全面测试。\n"
    "请对测试环境中的应用和TDD测试用例执行全面测试。\n\n"
    "【要求】\n"
    "1. 执行单元测试、模块测试、集成测试\n"
    "2. 前端实操验证（必须实际操作验证，不能仅靠后端测试）\n"
    "3. 生成完整的测试报告，包括测试覆盖率、通过率、缺陷记录\n"
    "4. 记录每个缺陷的严重程度（致命/严重/一般/轻微）\n"
    "直接输出测试报告，不需要输出思考过程。"
)

_STEP12_PROMPT = (
    "你是安全审计员后华（HouHua），负责执行安全审计。\n"
    "请对代码库中的全部代码和架构设计进行安全审计。\n\n"
    "【要求】\n"
    "1. 代码安全审计：检查常见安全漏洞（SQL注入、XSS、CSRF等）\n"
    "2. 依赖安全分析：检查第三方依赖是否存在已知安全漏洞\n"
    "3. 配置安全检查：检查环境配置、密钥管理是否安全\n"
    "4. 渗透测试建议：提供渗透测试方案和建议\n"
    "5. 发现的高危漏洞必须记录修复方案\n"
    "直接输出安全审计报告，不需要输出思考过程。"
)

_STEP13_PROMPT = (
    "你是资深CI/CD工程师后富（HouFu），负责将代码部署到生产环境。\n"
    "请将通过全部测试和安全审计的代码部署到生产环境。\n\n"
    "【要求】\n"
    "1. 配置生产环境变量和依赖\n"
    "2. 执行数据库迁移\n"
    "3. 部署应用服务，配置灰度发布策略\n"
    "4. 验证部署成功，应用可正常使用\n"
    "5. 配置生产环境监控和告警\n"
    "直接输出部署日志和生产环境配置，不需要输出思考过程。"
)

_STEP14_PROMPT = (
    "你是文档管理员后贵（HouGui），负责完善项目文档。\n"
    "请根据项目全流程产出，完善整个项目的文档。\n\n"
    "【要求】\n"
    "1. 用户文档：使用手册、功能介绍\n"
    "2. 运维文档：部署手册、运维指南\n"
    "3. API文档：接口说明、调用示例\n"
    "4. 保证所有文档之间的一致性\n"
    "5. 代码有修改的地方，文档必须同步更新\n"
    "直接输出文档内容，不需要输出思考过程。"
)

_STEP15_PROMPT = (
    "你是项目经理海梅（HaiMei），负责报告交付成果。\n"
    "请汇总项目全流程交付成果，生成交付报告，包括：\n"
    "1. 项目概述\n"
    "2. 交付清单\n"
    "3. 质量保证\n"
    "4. 后续建议"
)

# Map step number to (profile_name, prompt, artifact_key, initial_msg)
STEP_CONFIGS: Dict[int, tuple] = {
    6: ("haimei", _STEP6_PROMPT, "tdd_plan", "📋 海梅正在制订TDD测试用例计划..."),
    7: ("houfa", _STEP7_PROMPT, "tdd_cases", "🐝 后发正在建立蜂群编写TDD测试用例..."),
    8: ("haimei", _STEP8_PROMPT, "code_plan", "📋 海梅正在制订代码编写计划..."),
    9: ("houfa", _STEP9_PROMPT, "code", "🐝 后发正在建立蜂群编写功能代码..."),
    10: ("houfu", _STEP10_PROMPT, "deployment_log", "🚀 后富正在部署代码到测试环境..."),
    11: ("houda", _STEP11_PROMPT, "test_report", "🐝 后达正在执行全面测试..."),
    12: ("houhua", _STEP12_PROMPT, "security_report", "🔒 后华正在执行安全审计..."),
    13: ("houfu", _STEP13_PROMPT, "production_log", "🚀 后富正在部署代码到生产环境..."),
    14: ("hougui", _STEP14_PROMPT, "project_docs", "📝 后贵正在完善项目文档..."),
    15: ("haimei", _STEP15_PROMPT, "delivery_report", "📊 海梅正在汇总交付成果..."),
}


async def dispatch_step_n(project_id: str, engine: WorkflowEngine, step_number: int) -> None:
    """通用步骤执行调度器（适用于 6-15 的简单 Agent 执行步骤）"""
    from app.api.ws.step4_progress import broadcast
    from app.services.gateway_client import GatewayClient

    config = STEP_CONFIGS.get(step_number)
    if not config:
        logger.warning(f"步骤{step_number}没有配置")
        return

    profile_name, prompt_template, artifact_key, initial_msg = config

    # 收集前置产物上下文
    prompt_lines = [prompt_template, "\n"]

    step3 = engine.get_step3_artifacts() or {}
    requirement = (
        step3.get("doc_content") or step3.get("content") or
        step3.get("requirement") or step3.get("srs") or ""
    )
    if requirement:
        prompt_lines.append(f"=== 需求文档 ===\n{requirement[:2000]}\n\n")

    step4 = engine.get_step4_artifacts() or {}
    design_doc = step4.get("design_doc") or ""
    if design_doc:
        prompt_lines.append(f"=== 架构设计文档 ===\n{design_doc[:2000]}\n\n")

    # 收集上游步骤产物
    for prev_step in range(2, step_number):
        getter = getattr(engine, f"get_step{prev_step}_artifacts", None)
        if getter:
            prev_artifacts = getter() or {}
            for key in ("tdd_plan", "code_plan", "tdd_cases", "code",
                         "env_info", "test_report", "security_report", "deployment_log",
                         "production_log", "delivery_report"):
                val = prev_artifacts.get(key)
                if val and step_number > prev_step:
                    label = f"步骤{prev_step} - {key}"
                    if isinstance(val, str) and len(val) > 50:
                        prompt_lines.append(f"=== {label} ===\n{val[:2000]}\n\n")
                    elif isinstance(val, (dict, list)):
                        import json
                        prompt_lines.append(f"=== {label} ===\n{json.dumps(val, ensure_ascii=False, indent=2)[:2000]}\n\n")

    prompt = "\n".join(prompt_lines)

    engine.save_step_artifacts(step_number, {"status": "generating", "message": initial_msg})
    await broadcast(project_id, {"type": "stage", "message": initial_msg})

    timeout = {4: 2700, 5: 1800, 9: 3600, 11: 3600, 12: 3000, 14: 3000}.get(step_number, 1800)
    full_reply = []
    client = GatewayClient(profile_name=profile_name, timeout=timeout)

    async for chunk in client.chat_completions(
        messages=[{"role": "user", "content": prompt}], stream=True, max_tokens=65536
    ):
        full_reply.append(chunk)
        if len(full_reply) % 20 == 0:
            await broadcast(project_id, {
                "type": "progress",
                "message": f"⏳ Agent {profile_name} 执行中...（已生成 {len(''.join(full_reply))} 字符）",
            })

    reply = "".join(full_reply).strip()
    if reply and len(reply) >= 50:
        artifacts = {
            artifact_key: reply,
            "status": "done",
            "message": f"✅ 步骤{step_number}执行完成",
            "handover_doc_path": f"step{step_number}://{artifact_key}",
        }
        engine.save_step_artifacts(step_number, artifacts)
        engine.complete_step(step_number)
        await broadcast(project_id, {"type": "done", "message": f"✅ 步骤{step_number}完成，等待 QA 检验"})
    else:
        engine.save_step_artifacts(step_number, {
            "status": "error",
            "message": f"❌ Agent {profile_name} 未生成有效内容",
        })
        engine.reset_step(step_number)
        await broadcast(project_id, {"type": "error", "message": f"❌ Agent {profile_name} 未生成有效内容"})


async def dispatch_step9(project_id: str, engine: WorkflowEngine) -> None:
    """海梅调度步骤9：后发蜂群编写功能代码（调用 step9 的 swarm 引擎）"""
    from app.api.ws.step9_progress import broadcast
    from app.models.project import Project as _Project

    bg_db = None
    try:
        from app.database import SessionLocal
        bg_db = SessionLocal()
        bg_engine = WorkflowEngine(project_id=project_id, db=bg_db)

        # 收集前置产物
        step3 = bg_engine.get_step3_artifacts() or {}
        requirement = (
            step3.get("doc_content") or step3.get("content") or
            step3.get("requirement") or step3.get("srs") or ""
        )
        step4 = bg_engine.get_step4_artifacts() or {}
        design_doc = step4.get("design_doc") or ""
        step7 = bg_engine.get_step7_artifacts() or {}
        tdd_cases = step7.get("tdd_cases") or step7.get("test_cases") or step7.get("content") or ""
        step8 = bg_engine.get_step8_artifacts() or {}
        code_plan = step8.get("code_plan") or step8.get("plan_content") or ""
        dep_graph = step8.get("dependency_graph") or {}
        step2 = bg_engine.get_step2_artifacts() or {}
        core_goal = step2.get("confirmed_goal") or step2.get("core_goal") or ""

        proj = bg_db.query(_Project).filter(_Project.id == project_id).first()
        proj_name = proj.name if proj else ""
        proj_desc = proj.description or ""

        # 调用 step9 蜂群引擎
        from app.api.workflow.step9 import run_step9_swarm
        await run_step9_swarm(
            project_id=project_id,
            requirement=requirement,
            design_doc=design_doc,
            core_goal=core_goal,
            proj_name=proj_name,
            proj_desc=proj_desc,
            existing=None,
            resume=False,
            code_plan=code_plan,
            dep_graph=dep_graph,
            tdd_cases=tdd_cases,
        )
    except Exception as e:
        logger.error(f"[HAIMEI_DISPATCH] dispatch_step9 失败: {e}", exc_info=True)
        try:
            await broadcast(project_id, {"type": "error", "message": f"❌ 海梅调度step9失败: {str(e)[:200]}"})
        except Exception:
            pass
    finally:
        if bg_db:
            bg_db.close()


# Dispatch function aliases for HaimeiStepExecutor
dispatch_step6 = lambda pid, eng: dispatch_generic_step(pid, eng, 6)
dispatch_step7 = lambda pid, eng: dispatch_generic_step(pid, eng, 7)
dispatch_step8 = lambda pid, eng: dispatch_generic_step(pid, eng, 8)
dispatch_step10 = lambda pid, eng: dispatch_generic_step(pid, eng, 10)
dispatch_step11 = lambda pid, eng: dispatch_generic_step(pid, eng, 11)
dispatch_step12 = lambda pid, eng: dispatch_generic_step(pid, eng, 12)
dispatch_step13 = lambda pid, eng: dispatch_generic_step(pid, eng, 13)
dispatch_step14 = lambda pid, eng: dispatch_generic_step(pid, eng, 14)
dispatch_step15 = lambda pid, eng: dispatch_generic_step(pid, eng, 15)


async def dispatch_generic_step(project_id: str, engine: WorkflowEngine, step_number: int) -> None:
    """通用的步骤{N}调度器（步骤6-15）"""
    from app.database import SessionLocal
    bg_db = SessionLocal()
    try:
        bg_engine = WorkflowEngine(project_id=project_id, db=bg_db)
        await dispatch_step_n(project_id, bg_engine, step_number)
    except Exception as e:
        logger.error(f"Step{step_number} dispatch failed: {e}", exc_info=True)
    finally:
        bg_db.close()
