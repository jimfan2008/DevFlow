import json
import asyncio
import logging
from fastapi import APIRouter, WebSocket, WebSocketDisconnect, Query
from app.api.ws.auth import verify_token
from app.models.project import Project
from app.services.gateway_client import GatewayClient
from app.services.workflow_engine import WorkflowEngine

logger = logging.getLogger(__name__)

router = APIRouter()


@router.websocket("/step3/chat/{project_id}")
async def step3_chat_ws(websocket: WebSocket, project_id: str, token: str = Query(...)):
    """WebSocket streaming endpoint for HouXing step3 chat."""
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

        engine = WorkflowEngine(project_id, db)
        step2 = engine.get_step2_artifacts()
        core_goal = step2.get("confirmed_goal") or step2.get("core_goal") or ""

        while True:
            data = await websocket.receive_text()
            payload = json.loads(data)
            user_message = payload.get("message", "").strip()
            history = payload.get("history", [])

            if not user_message:
                user_message = "你好，我们来讨论一下项目的需求。"

            messages = []
            if core_goal:
                messages.append({"role": "system", "content": f"[项目核心目标]\n{core_goal}"})
            messages.append({"role": "system", "content": (
                "你是一个软件需求分析师（后兴）。你的职责是与用户讨论并生成需求文档。\n"
                "当你生成了完整的需求文档后，输出完整的文档正文。\n"
                "注意：生成文档时，只用文档正文内容，不要包含分析/对话/说明文字。\n"
                "完整输出需求文档正文，不要省略任何内容。\n\n"
                "需求文档必须遵循标准格式，包含以下章节：\n"
                "1. 引言（目的、范围、术语定义）\n"
                "2. 项目概述（产品背景、用户特征、业务目标）\n"
                "3. 功能需求（详细的功能描述、输入/输出、处理规则）\n"
                "4. 非功能需求（性能、安全、可用性等）\n"
                "5. 接口需求（外部接口、内部接口）\n"
                "6. 数据需求（数据模型、数据字典）"
            )})
            messages.extend(history)
            messages.append({"role": "user", "content": user_message})

            try:
                client = GatewayClient(profile_name="houxing", timeout=180)
                async for chunk in client.chat_completions(messages=messages, stream=True):
                    if chunk.strip():
                        await websocket.send_json({"type": "chunk", "content": chunk})
                await websocket.send_json({"type": "done"})
            except Exception as e:
                logger.error(f"HouXing chat failed: {e}")
                await websocket.send_json({"type": "error", "message": str(e)})

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
