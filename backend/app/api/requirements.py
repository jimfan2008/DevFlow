# 需求协同 API - SRS §3.1
from fastapi import APIRouter, Depends, HTTPException
from sqlalchemy.orm import Session
from app.database import get_db
from app.api.deps import get_current_user
from app.services.hermes_service import HermesService
from app.services.llm_client import HermesUnavailableError as LLMUnavailable
from app.models.requirement import Requirement
from app.models.project import Project
from app.schemas.requirement import (
    RequirementConfirm,
    ClarificationAnswer,
)
from app.models.user import User

import uuid
from datetime import datetime, timezone
from typing import Optional
from pydantic import BaseModel

router = APIRouter()


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


@router.post("/chat", response_model=dict)
async def hermes_requirement_chat(
    data: HermesChatRequest,
    db: Session = Depends(get_db),
    current_user: User = Depends(get_current_user),
):
    """SRS §3.1.2 - Hermes主动与用户聊天确认需求"""
    hermes = HermesService(db=db, user_id=current_user.id)

    project = None
    if data.project_id:
        project = db.query(Project).filter(Project.id == data.project_id).first()
    elif data.task_id:
        from app.models.task import Task
        task = db.query(Task).filter(Task.id == data.task_id).first()
        if task:
            project = db.query(Project).filter(Project.id == task.board_id).first() if hasattr(task, 'board_id') else None

    # 空消息或介绍请求
    if not data.message or not data.message.strip() or data.message.strip() == "介绍":
        result = hermes.chat_intro()
    else:
        project_context = project.name if project else None
        result = hermes.chat(data.message, project_context=project_context)

    # 如果有项目上下文且有需求文档，尝试将其关联
    req_content = None
    if project:
        from app.models.requirement import Requirement as ReqModel
        existing_req = db.query(ReqModel).filter(
            ReqModel.project_id == project.id,
        ).order_by(ReqModel.version.desc()).first()
        if existing_req:
            req_content = existing_req.content

    return {
        "code": 0,
        "message": "success",
        "data": {
            "reply": result.get("reply", ""),
            "questions": result.get("questions", []),
            "snapshot": result.get("snapshot", {}),
            "phase": result.get("phase", "initial"),
            "project_id": data.project_id,
            "task_id": data.task_id,
            "existing_requirement": req_content,
        },
    }