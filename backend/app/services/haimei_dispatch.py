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
    """海梅调度步骤4：后旺串行执行4个子步骤（架构→前端→后端→数据库）"""
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
    """步骤4的核心逻辑 - 4个子步骤串行执行：
       step4_1: houwang1→架构设计→hourong1检验
       step4_2: houwang2→前端设计→hourong2检验→校验架构-前端一致性
       step4_3: houwang3→后端设计→hourong3检验→校验架构-后端、前端-后端一致性
       step4_4: houwang4→数据库设计→hourong4检验→校验后端-数据库一致性
    """
    from app.database import SessionLocal
    from app.api.ws.step4_progress import broadcast
    from app.models.project import Project as _Project

    from app.api.workflow.step4 import (
        SUB_FLOW_CONFIGS, _run_doc_sub_flow,
        _check_consistency_pairs, _fix_doc_from_consistency_feedback,
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
        "message": "🚀 海梅已调度4个子步骤串行执行——step4_1→架构→step4_2→前端→step4_3→后端→step4_4→数据库",
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

    # ── 续跑检测 ──
    existing_sub_results = (engine.get_step4_artifacts() or {}).get("sub_flow_results", [])
    passed_keys = {r["key"] for r in existing_sub_results if r.get("passed")}
    existing_doc_paths = (engine.get_step4_artifacts() or {}).get("doc_paths", {})

    all_results = []
    doc_paths_map = dict(existing_doc_paths)
    all_passed = True

    for sub in SUB_STEP_DEFS:
        cfg = sub["cfg"]
        step_label = sub["step_label"]
        dim_key = cfg["dim"]["key"]

        # 续跑跳过已通过项
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

        # 1. houwang生成 + hourong检验（复用现有子流程函数）
        result = await _run_doc_sub_flow(
            project_id=project_id, slug=slug, docs_dir=docs_dir,
            cfg=cfg, requirement=requirement,
            project_name=proj_name, project_description=proj_desc,
            core_goal=core_goal,
        )

        all_results.append(result)
        if result.get("path"):
            doc_paths_map[dim_key] = result["path"]

        engine.save_step4_artifacts({
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
            engine.save_step4_artifacts({**artifacts, "qa_passed": True, "qa_checked": True})
            engine.complete_step(4)
            engine.pass_qa(4)
            await broadcast(project_id, {
                "type": "done",
                "message": f"✅ 全部4个子步骤通过hourong QA检验与跨文档一致性检验，已推进至第5步",
            })
        else:
            engine.save_step4_artifacts({
                **artifacts, "qa_passed": False, "qa_checked": True, "status": "qa_failed",
            })
            await broadcast(project_id, {
                "type": "done",
                "message": f"⚠️ {4 - passed_count} 份文档未通过检验\n{sub_flow_detail}",
            })
    else:
        engine.save_step4_artifacts({
            "status": "error",
            "message": "❌ 未生成有效设计文档",
        })
        engine.reset_step(4)
        await broadcast(project_id, {"type": "error", "message": "❌ 未生成有效设计文档"})


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

    # 获取项目 slug 用于构建输出目录
    from app.models.project import Project as _Project
    proj = engine._db.query(_Project).filter(_Project.id == project_id).first()
    _slug = proj.slug if proj else project_id.replace("-", "")
    _docs_dir = os.path.join(settings.PROJECTS_BASE_DIR, _slug, settings.PROJECT_DOCS_SUBDIR)
    _tmp_dir = os.path.join(settings.PROJECTS_BASE_DIR, _slug, settings.PROJECT_TMP_SUBDIR)
    prompt_lines.append(
        f"【文件输出目录规则 - 必须遵守】\n"
        f"你生成的所有文件必须保存到以下指定目录：\n"
        f"  - 文档目录（正式产出物）: {_docs_dir}\n"
        f"  - 临时目录（中间产物）: {_tmp_dir}\n"
        f"不要将文件保存到当前工作目录或其他位置。\n\n"
    )

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
    "你是项目经理海梅（HaiMei），负责制订TDD测试用例编写计划。\n"
    "请根据需求文档和架构设计文档，制定完整的TDD测试用例编写计划，包括：\n"
    "1. 测试用例分类（单元/集成/端到端）\n"
    "2. 每个模块的测试覆盖目标\n"
    "3. 测试优先级和执行顺序\n"
    "4. 测试工具和技术栈选择"
)

_STEP7_PROMPT = (
    "你是资深程序员后发（HouFa），负责编写TDD测试用例。\n"
    "请根据TDD测试用例编写计划，建立Agent蜂群编写完整的TDD测试用例：\n"
    "1. 每个测试用例最小原子化\n"
    "2. 每个测试用例有明确可量化的验收标准\n"
    "3. 按照计划中的优先级和执行顺序编写"
)

_STEP8_PROMPT = (
    "你是项目经理海梅（HaiMei），负责制订代码编写计划。\n"
    "请根据需求文档、架构设计文档和TDD测试用例，制定代码编写计划，包括：\n"
    "1. 模块划分和依赖关系图\n"
    "2. 每个模块的代码编写顺序和优先级\n"
    "3. Agent蜂群任务分配方案\n"
    "4. 预计工期和风险点"
)

_STEP9_PROMPT = (
    "你是资深程序员后发（HouFa），负责编写功能代码。\n"
    "请根据代码编写计划、需求文档、架构设计和TDD测试用例，编写完整的功能代码：\n"
    "1. 严格按照测试优先原则\n"
    "2. 每个模块独立完整\n"
    "3. 代码注释清晰，符合编码规范"
)

_STEP10_PROMPT = (
    "你是资深CI/CD工程师后富（HouFu），负责部署代码到测试环境。\n"
    "请将功能代码部署到测试环境，包括：\n"
    "1. 环境变量配置\n"
    "2. 数据库部署\n"
    "3. 服务启动和验证\n"
    "4. 部署日志记录"
)

_STEP11_PROMPT = (
    "你是资深测试工程师后达（HouDa），负责对功能进行全面的测试。\n"
    "请对已部署的功能进行全面测试，包括：\n"
    "1. 功能测试\n"
    "2. 集成测试\n"
    "3. 性能测试\n"
    "4. 测试报告和缺陷记录"
)

_STEP12_PROMPT = (
    "你是安全审计员后华（HouHua），负责执行安全审计。\n"
    "请对功能代码和架构设计进行安全审计，包括：\n"
    "1. 代码安全审计\n"
    "2. 依赖安全分析\n"
    "3. 配置安全检查\n"
    "4. 渗透测试建议"
)

_STEP13_PROMPT = (
    "你是资深CI/CD工程师后富（HouFu），负责部署代码到生产环境。\n"
    "请将通过测试的代码部署到生产环境，包括：\n"
    "1. 生产环境准备\n"
    "2. 代码部署\n"
    "3. 灰度发布策略\n"
    "4. 部署验证和监控"
)

_STEP14_PROMPT = (
    "你是文档管理员后贵（HouGui），负责完善项目文档。\n"
    "请根据项目全流程产出，完善项目文档，包括：\n"
    "1. 用户文档\n"
    "2. 运维文档\n"
    "3. 部署指南\n"
    "4. 项目总结"
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
    import importlib as _importlib
    try:
        ws_mod = _importlib.import_module(f"app.api.ws.step{step_number}_progress")
        broadcast = ws_mod.broadcast
    except (ImportError, AttributeError):
        from app.api.ws.step4_progress import broadcast
    from app.services.gateway_client import GatewayClient

    config = STEP_CONFIGS.get(step_number)
    if not config:
        logger.warning(f"步骤{step_number}没有配置")
        return

    profile_name, prompt_template, artifact_key, initial_msg = config

    # 收集前置产物上下文
    prompt_lines = [prompt_template, "\n"]

    # 获取项目 slug 用于构建输出目录
    from app.models.project import Project as _Project
    from sqlalchemy.orm import Session as _Session
    proj = engine._db.query(_Project).filter(_Project.id == project_id).first()
    _slug = proj.slug if proj else project_id.replace("-", "")
    _docs_dir = os.path.join(settings.PROJECTS_BASE_DIR, _slug, settings.PROJECT_DOCS_SUBDIR)
    _tmp_dir = os.path.join(settings.PROJECTS_BASE_DIR, _slug, settings.PROJECT_TMP_SUBDIR)
    prompt_lines.append(
        f"【文件输出目录规则 - 必须遵守】\n"
        f"你生成的所有文件必须保存到以下指定目录：\n"
        f"  - 文档目录（正式产出物）: {_docs_dir}\n"
        f"  - 临时目录（中间产物）: {_tmp_dir}\n"
        f"不要将文件保存到当前工作目录或其他位置。\n"
    )

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
        if chunk.strip():
            await broadcast(project_id, {"type": "content", "content": chunk})

    reply = "".join(full_reply).strip()
    if reply and len(reply) >= 50:
        artifacts = {
            artifact_key: reply,
            "status": "done",
            "message": f"✅ 步骤{step_number}执行完成",
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


# Dispatch function aliases for HaimeiStepExecutor
dispatch_step6 = lambda pid, eng: dispatch_generic_step(pid, eng, 6)

async def dispatch_step7(project_id: str, engine) -> None:
    """后发蜂群并行TDD测试用例（绕过通用调度，使用新的蜂群并行逻辑）"""
    from app.api.workflow.step7 import run_step7_swarm
    logger.info("Haimei dispatching step7 with swarm parallel flow")
    step3 = engine.get_step3_artifacts() or {}
    requirement = (step3.get("doc_content") or step3.get("content") or step3.get("requirement") or step3.get("srs") or "")
    requirement_path = step3.get("local_path") or step3.get("filepath") or ""
    step4 = engine.get_step4_artifacts() or {}
    design_doc = step4.get("design_doc") or ""
    step2 = engine.get_step2_artifacts() or {}
    core_goal = step2.get("confirmed_goal") or step2.get("core_goal") or ""
    await run_step7_swarm(
        project_id=project_id,
        requirement=requirement,
        design_doc=design_doc,
        core_goal=core_goal,
        requirement_path=requirement_path,
    )

dispatch_step8 = lambda pid, eng: dispatch_generic_step(pid, eng, 8)
dispatch_step9 = lambda pid, eng: dispatch_generic_step(pid, eng, 9)
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
