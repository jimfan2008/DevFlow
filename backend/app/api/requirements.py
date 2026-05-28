# 需求协同 API - SRS §3.1
from fastapi import APIRouter, Depends, HTTPException
from fastapi.responses import StreamingResponse
from sqlalchemy.orm import Session
from app.database import get_db
from app.api.deps import get_current_user
from app.services.hermes.hermes_chat import HermesChatService
from app.services.hermes.hermes_api_client import HermesAPIClient
from app.services.hermes.hermes_session import HermesSessionManager
from app.services.hermes.types import SSEEvent, HermesAPIError
from app.models.requirement import Requirement
from app.models.project import Project
from app.models.agent import Agent
from app.schemas.requirement import (
    RequirementConfirm,
    ClarificationAnswer,
)
from app.models.user import User

import uuid
import logging
from datetime import datetime, timezone
from typing import Optional, List, Dict, Any
from pydantic import BaseModel

logger = logging.getLogger("devflow.hermes")
router = APIRouter(redirect_slashes=False)


@router.put("/{project_id}/requirements", response_model=dict)
def submit_requirement(
    project_id: str,
    data: dict,
    db: Session = Depends(get_db),
    current_user: User = Depends(get_current_user),
):
    """SRS §3.1.1 - 提交/更新项目需求"""
    project = db.query(Project).filter(Project.id == project_id).first()
    if not project:
        raise HTTPException(status_code=404, detail="Project not found")

    content = data.get("content") or data.get("requirements")
    if not content or (isinstance(content, str) and not content.strip()):
        raise HTTPException(status_code=400, detail="content or requirements field is required")

    existing = db.query(Requirement).filter(
        Requirement.project_id == project_id,
        Requirement.is_locked == False,
    ).first()

    if existing:
        existing.content = content
        existing.version += 1
        existing.updated_at = datetime.now(timezone.utc)
        req = existing
    else:
        req = Requirement(
            id=str(uuid.uuid4()),
            project_id=project_id,
            content=content,
            version=1,
        )
        db.add(req)

    db.commit()
    db.refresh(req)
    return {"code": 0, "message": "success", "data": {"requirement": req.to_dict()}}


@router.get("/{project_id}/requirements", response_model=dict)
def get_requirement(
    project_id: str,
    db: Session = Depends(get_db),
    current_user: User = Depends(get_current_user),
):
    """获取项目当前需求文档"""
    req = db.query(Requirement).filter(
        Requirement.project_id == project_id,
    ).order_by(Requirement.version.desc()).first()
    if not req:
        return {"code": 0, "message": "success", "data": {"requirement": None}}
    return {"code": 0, "message": "success", "data": {"requirement": req.to_dict()}}


@router.post("/{project_id}/requirements/clarify", response_model=dict)
def clarify_requirements(
    project_id: str,
    data: ClarificationAnswer,
    db: Session = Depends(get_db),
    current_user: User = Depends(get_current_user),
):
    """SRS §3.1.2 - Hermes Agent 需求澄清，生成结构化需求文档"""
    project = db.query(Project).filter(Project.id == project_id).first()
    if not project:
        raise HTTPException(status_code=404, detail="Project not found")

    hermes = HermesService(db=db, user_id=current_user.id)
    existing_req = db.query(Requirement).filter(
        Requirement.project_id == project_id,
    ).order_by(Requirement.version.desc()).first()

    try:
        doc = hermes.generate_structured_doc(
            raw_content=existing_req.content if existing_req else "",
            clarification_answers=data.model_dump(),
        )
    except LLMUnavailable as e:
        raise HTTPException(status_code=503, detail=str(e))

    return {
        "code": 0,
        "message": "success",
        "data": {"document": doc},
    }


@router.post("/{project_id}/requirements/confirm", response_model=dict)
def confirm_requirements(
    project_id: str,
    data: Optional[RequirementConfirm] = None,
    db: Session = Depends(get_db),
    current_user: User = Depends(get_current_user),
):
    """SRS §3.1.3 - 需求确认与锁定"""
    confirmed = data.confirmed if data else True
    if not confirmed:
        raise HTTPException(status_code=400, detail="Confirmation must be true")

    req = db.query(Requirement).filter(
        Requirement.project_id == project_id,
        Requirement.is_locked == False,
    ).order_by(Requirement.version.desc()).first()

    if not req:
        raise HTTPException(status_code=404, detail="No unlocked requirement found")

    req.is_locked = True
    req.confirmed_at = datetime.now(timezone.utc)
    db.commit()
    db.refresh(req)

    return {
        "code": 0,
        "message": "success",
        "data": {
            "requirement": req.to_dict(),
            "message": "需求已确认锁定，将开始任务拆解流程",
        },
    }


class HermesChatRequest(BaseModel):
    message: str
    project_id: Optional[str] = None
    task_id: Optional[str] = None


class HermesChatResponse(BaseModel):
    reply: str
    questions: list[str] = []


def _resolve_hermes_agent(db: Session, profile_name: str = None) -> Optional[Agent]:
    if profile_name:
        agent = db.query(Agent).filter(Agent.name == profile_name, Agent.agent_type == "hermes").first()
        if agent:
            return agent
    agent = db.query(Agent).filter(Agent.agent_type == "hermes", Agent.status == "online").first()
    return agent


def _build_requirements_chat_prompt(message: str, project: Optional[Project] = None) -> str:
    context = ""
    if project:
        context = f"\n当前项目：{project.name}"

    if message.strip() == "介绍" or not message.strip():
        return (
            "用户正在打开需求管理页面。请用中文写一段热情友好的自我介绍，说明你叫 Hermes，"
            "是一个 AI 项目经理，可以帮用户梳理需求、分析模糊点、生成需求文档、拆解任务。"
            "最后引导用户描述他们的项目想法。控制在 150 字以内。"
            f"{context}"
        )

    return (
        f"用户消息：{message}{context}\n\n"
        f"请分析用户的需求描述，返回 JSON 格式：\n"
        f"{{\n"
        f'  "reply": "你的回复（自然的中文对话，分析需求的要点和问题）",\n'
        f'  "fuzzy_points": ["需要进一步明确的点1", "点2"],\n'
        f'  "phase": "initial|discussing|summarizing",\n'
        f'  "summary": {{"项目类型": "...", "技术栈": ["..."], "功能": ["..."]}}\n'
        f"}}\n\n"
        f"phase 说明：initial=刚开始讨论, discussing=正在分析需求细节, summarizing=信息已充足可提交"
    )


def _parse_hermes_response(resp_text: str) -> Dict[str, Any]:
    import json as json_mod
    try:
        result = json_mod.loads(resp_text)
        reply = result.get("reply", resp_text)
        fuzzy = result.get("fuzzy_points", [])
        phase = result.get("phase", "discussing")
        summary = result.get("summary", {})

        if not reply:
            reply = resp_text

        questions = fuzzy[:5] if fuzzy else []
        if phase == "summarizing" and not questions:
            questions = ["提交需求并生成文档", "我还想补充一些细节"]

        return {
            "reply": reply,
            "questions": questions,
            "snapshot": summary,
            "phase": phase,
        }
    except (json_mod.JSONDecodeError, TypeError):
        return {
            "reply": resp_text,
            "questions": [],
            "snapshot": {},
            "phase": "discussing",
        }


def _get_default_intro_result() -> Dict[str, Any]:
    return {
        "reply": (
            "你好！我是 **Hermes**，你的 AI 项目经理 🤖\n\n"
            "我可以帮你：\n"
            "• 💡 梳理和分析项目需求\n"
            "• 📋 生成标准化需求文档\n"
            "• 🔍 发现需求中的模糊点和遗漏\n"
            "• 📊 将需求拆解为可执行的任务\n\n"
            "请描述你的项目想法，我会一步步引导你完善需求！"
        ),
        "questions": ["我想开发一个电商平台", "我需要一个企业管理系统", "我想做一个移动端App"],
        "snapshot": {},
        "phase": "initial",
    }


@router.get("/chat/test", dependencies=[])
async def test_chat_endpoint():
    """Test endpoint to verify routing"""
    logger.info("test_chat_endpoint called")
    return {"code": 0, "message": "success", "data": "Test endpoint works"}

@router.post("/chat", response_model=dict)
async def hermes_requirement_chat(
    data: HermesChatRequest,
    db: Session = Depends(get_db),
    current_user: User = Depends(get_current_user),
):
    """SRS §3.1.2 - Hermes 需求对话 - 通过 Hermes API Server (model=hermes-agent) 走完整 agent 流程"""
    logger.info(f"hermes_requirement_chat: message={data.message[:50] if data.message else 'empty'}")

    project = None
    if data.project_id:
        project = db.query(Project).filter(Project.id == data.project_id).first()
    elif data.task_id:
        from app.models.task import Task
        task = db.query(Task).filter(Task.id == data.task_id).first()
        if task:
            project = db.query(Project).filter(Project.id == task.board_id).first() if hasattr(task, 'board_id') else None

    from app.config import settings
    api = HermesAPIClient(
        base_url=settings.HERMES_API_BASE,
        api_key=settings.HERMES_API_KEY,
        model=settings.HERMES_MODEL,
    )
    project_context = f"\n当前项目：{project.name}" if project else ""
    is_intro = not data.message or not data.message.strip() or data.message.strip() == "介绍"

    try:
        if is_intro:
            prompt = "用户刚进入需求管理页面。请用中文简短自我介绍（150字以内），说明你能帮用户梳理需求、分析模糊点、生成文档、拆解任务。最后引导用户描述项目想法。"
        else:
            prompt = f"用户说：{data.message}{project_context}\n\n请分析用户的需求，指出模糊点和需要进一步明确的地方，给出你的专业建议。只用中文回复。"

        result = await api.chat_completions(
            messages=[{"role": "user", "content": prompt}],
            model=settings.HERMES_MODEL,
            max_tokens=800,
            temperature=0.7,
        )
        reply = result.content or ""

        from app.services.hermes.hermes_chat import strip_thinking_process
        reply = strip_thinking_process(reply)
        if not reply or len(reply.strip()) < 10:
            reply = "我分析了你的需求。请提供更多细节，比如项目类型、目标用户、核心功能等。"

    except HermesAPIError as e:
        logger.warning(f"Hermes API error: {e}")
        reply = f"暂时无法连接 Hermes Agent（{e}），请稍后重试。"
    except Exception as e:
        logger.error(f"Chat failed: {e}")
        reply = "对话出错，请稍后重试。"

    fuzzy_points = []
    for line in reply.split('\n'):
        s = line.strip()
        if s and any(k in s for k in ['？', '?', '是否', '还是', '哪种', '多少', '什么', '明确', '确认']):
            import re as _re
            s = _re.sub(r'^[-*•]\s*', '', s)
            s = _re.sub(r'^\d+\.\s*', '', s)
            if len(s) > 5:
                fuzzy_points.append(s)

    if any(k in reply for k in ['提交', '总结', '梳理完毕']):
        phase = "summarizing"
    elif len(data.message or "") > 80 or any(k in reply for k in ['深入', '详细']):
        phase = "discussing"
    else:
        phase = "initial"

    req_content = None
    if project:
        from app.models.requirement import Requirement as ReqModel
        existing_req = db.query(ReqModel).filter(ReqModel.project_id == project.id).order_by(ReqModel.version.desc()).first()
        if existing_req:
            req_content = existing_req.content

    return {
        "code": 0,
        "message": "success",
        "data": {
            "reply": reply,
            "questions": fuzzy_points[:5] if fuzzy_points else [],
            "snapshot": {},
            "phase": phase,
            "project_id": data.project_id,
            "task_id": data.task_id,
            "existing_requirement": req_content,
            "agent_id": None,
            "agent_name": "hermes-agent",
        },
    }