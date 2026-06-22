from app.api.workflow.core import (
    router, _get_engine, logger, APIResponse, Depends, get_db,
    get_current_user, Session, Body, Request, HTTPException,
    BaseModel, Optional, asyncio, os, settings,
)

@router.post("/{project_id}/step15/execute")
async def execute_step15_async(project_id: str, db: Session = Depends(get_db), current_user=Depends(get_current_user)):
    """异步启动第十五步：海梅生成项目交付报告（约20分钟），立即返回"""
    from app.services.gateway_client import GatewayClient
    import asyncio as _asyncio
    try:
        engine = _get_engine(project_id, db)
        engine.advance_step(15)
    except Exception as e:
        return APIResponse(code=1, message=f"无法开始步骤15: {str(e)[:200]}")
    step3 = engine.get_step3_artifacts() or {}
    step4 = engine.get_step4_artifacts() or {}
    step9 = engine.get_step9_artifacts() or {}
    step11 = engine.get_step11_artifacts() or {}
    step12 = engine.get_step12_artifacts() or {}
    step13 = engine.get_step13_artifacts() or {}
    step14 = engine.get_step14_artifacts() or {}
    engine.save_step15_artifacts({"status": "generating", "message": "📊 海梅正在生成项目交付报告..."})

    async def _generate():
        try:
            from app.database import SessionLocal
            from app.services.workflow_engine import WorkflowEngine
            from app.api.ws.step4_progress import broadcast
            bg_db = SessionLocal()
            try:
                bg_engine = WorkflowEngine(project_id=project_id, db=bg_db)
                await broadcast(project_id, {"type": "stage", "message": "📖 海梅正在汇总所有项目产出..."})
                await broadcast(project_id, {"type": "stage", "message": "📊 海梅正在生成项目交付报告..."})
                prompt_lines = ["你是资深项目经理海梅（HaiMei），负责生成项目交付报告。\n"]
                if step3:
                    prompt_lines.append(f"=== 需求文档摘要 ===\n{str(step3.get('doc_content', '')[:500])}\n\n")
                if step4:
                    prompt_lines.append(f"=== 架构设计摘要 ===\n{str(step4.get('design_doc', '')[:500])}\n\n")
                if step9:
                    prompt_lines.append(f"=== 功能代码摘要 ===\n{str(step9.get('code', '')[:500])}\n\n")
                if step11:
                    prompt_lines.append(f"=== 测试报告摘要 ===\n{str(step11.get('test_report', '')[:500])}\n\n")
                if step12:
                    prompt_lines.append(f"=== 安全审计报告摘要 ===\n{str(step12.get('security_report', '')[:500])}\n\n")
                if step13:
                    prompt_lines.append(f"=== 部署日志摘要 ===\n{str(step13.get('deployment_log', '')[:500])}\n\n")
                if step14:
                    prompt_lines.append(f"=== 项目文档摘要 ===\n{str(step14.get('documentation', '')[:500])}\n\n")
                prompt_lines.append(
                    "请生成完整的项目交付报告，包括：\n"
                    "1. 项目完成状态（所有步骤的完成状态）\n"
                    "2. 功能交付清单（实现的功能列表）\n"
                    "3. 测试结果摘要（测试覆盖率、通过率、缺陷清单）\n"
                    "4. 安全审计结果（漏洞修复情况、合规达标情况）\n"
                    "5. 部署访问地址（生产环境URL）\n"
                    "6. 文档下载链接（各类文档的路径）\n\n"
                    "直接输出交付报告。"
                )
                prompt = "\n".join(prompt_lines)
                full_reply = []
                client = GatewayClient(profile_name="haimei", timeout=2700)
                async for chunk in client.chat_completions(messages=[{"role": "user", "content": prompt}], stream=True, max_tokens=16384):
                    full_reply.append(chunk)
                    if len(full_reply) % 10 == 0:
                        await broadcast(project_id, {"type": "progress", "message": f"📊 海梅持续生成报告中...（已生成 {len(''.join(full_reply))} 字符）"})
                reply = "".join(full_reply).strip()
                if reply and len(reply) >= 50:
                    artifacts = {"delivery_report": reply, "status": "done", "message": "✅ 项目交付报告生成完成"}
                    bg_engine.save_step15_artifacts(artifacts)
                    bg_engine.complete_step(15)
                    await broadcast(project_id, {"type": "done", "message": "✅ 项目交付报告已生成完毕"})
                else:
                    bg_engine.save_step15_artifacts({"status": "error", "message": "❌ 海梅未生成有效报告"})
                    bg_engine.reset_step(15)
                    await broadcast(project_id, {"type": "error", "message": "❌ 海梅未生成有效报告"})
            except Exception as e:
                logger.error(f"HaiMei background delivery report failed: {e}")
                try:
                    bg_engine = WorkflowEngine(project_id=project_id, db=bg_db)
                    bg_engine.save_step15_artifacts({"status": "error", "message": f"❌ 海梅报告生成失败: {str(e)[:200]}"})
                    bg_engine.reset_step(15)
                except Exception: pass
            finally:
                bg_db.close()
        except Exception as e:
            logger.error(f"HaiMei background task fatal: {e}")

    _asyncio.create_task(_generate())
    return APIResponse(code=0, data={"message": "第十五步已启动，海梅正在生成项目交付报告（约20分钟）", "status": "generating"})


@router.get("/{project_id}/step15/status")
def get_step15_status(project_id: str, db: Session = Depends(get_db), current_user=Depends(get_current_user)):
    engine = _get_engine(project_id, db)
    return APIResponse(code=0, data=engine.get_step15_artifacts())


@router.post("/{project_id}/step15/artifacts")
def save_step15_artifacts(project_id: str, body: dict = Body(...), db: Session = Depends(get_db), current_user=Depends(get_current_user)):
    engine = _get_engine(project_id, db)
    engine.save_step15_artifacts(body)
    return APIResponse(code=0, data={"message": "步骤15状态已保存"})


@router.get("/{project_id}/step15/report")
def get_step15_report(project_id: str, db: Session = Depends(get_db), current_user=Depends(get_current_user)):
    """返回完整的项目交付报告"""
    engine = _get_engine(project_id, db)
    artifacts = engine.get_step15_artifacts()
    if not artifacts:
        return APIResponse(code=0, data={"message": "尚未生成项目交付报告，请先执行步骤15"})
    report = artifacts.get("delivery_report", "")
    if not report:
        return APIResponse(code=0, data={"message": "项目交付报告为空"})
    return APIResponse(code=0, data={"delivery_report": report})


# ==================== Step 16: 用户满意度确认与迭代 ====================

