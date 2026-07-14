from fastapi import APIRouter, HTTPException, Depends
from typing import List, Optional, Dict, Any
from sqlalchemy.orm import Session
from pydantic import BaseModel
from app.database import get_db
from app.api.deps import get_current_user
from app.schemas.group import (
    GroupCreate, GroupUpdate, GroupResponse,
    AddMemberRequest, SetHostRequest,
    MeetingOutcomeResponse, GroupTaskResponse
)
from app.services.group_service import GroupService
from app.services.chat_store import chat_store

router = APIRouter(prefix="/api/groups", tags=["groups"], redirect_slashes=False)


@router.get("", response_model=dict)
async def list_groups(db: Session = Depends(get_db), current_user=Depends(get_current_user)):
    try:
        service = GroupService(db)
        groups = service.get_all_groups()
        return {"code": 0, "message": "success", "data": {"groups": [g.to_dict() for g in groups], "total": len(groups)}}
    except Exception as e:
        raise HTTPException(status_code=500, detail=f"Failed to get groups: {str(e)}")


@router.post("", response_model=dict)
async def create_group(request: GroupCreate, db: Session = Depends(get_db), current_user=Depends(get_current_user)):
    """创建新群组"""
    try:
        service = GroupService(db)
        group = service.create_group(
            name=request.name,
            description=request.description,
            members=request.members,
            project_id=request.project_id
        )
        # 同步到 chat_store (SQLite) 供 WebSocket 使用
        try:
            chat_store.create_group(
                group_id=group.id,
                name=group.name,
                description=group.description or "",
                members=group.members or []
            )
        except Exception as sync_err:
            import logging
            logging.getLogger(__name__).warning(f"Failed to sync group to chat_store: {sync_err}")
        return {"code": 0, "message": "success", "data": group.to_dict()}
    except Exception as e:
        raise HTTPException(status_code=500, detail=f"Failed to create group: {str(e)}")


@router.get("/{group_id}", response_model=dict)
async def get_group(group_id: str, db: Session = Depends(get_db), current_user=Depends(get_current_user)):
    service = GroupService(db)
    group = service.get_group(group_id)
    if not group:
        raise HTTPException(status_code=404, detail="Group not found")
    return {"code": 0, "message": "success", "data": {"group": group.to_dict()}}


@router.put("/{group_id}", response_model=dict)
async def update_group(group_id: str, request: GroupUpdate, db: Session = Depends(get_db)):
    """更新群组信息"""
    service = GroupService(db)
    update_data = request.model_dump(exclude_none=True)
    group = service.update_group(group_id, **update_data)
    if not group:
        raise HTTPException(status_code=404, detail="Group not found")
    # 同步到 chat_store
    try:
        chat_store.update_group(group_id, **update_data)
    except Exception as sync_err:
        import logging
        logging.getLogger(__name__).warning(f"Failed to sync group update to chat_store: {sync_err}")
    return {"code": 0, "message": "success", "data": group.to_dict()}


@router.delete("/{group_id}")
async def delete_group(group_id: str, db: Session = Depends(get_db)):
    service = GroupService(db)
    success = service.delete_group(group_id)
    if not success:
        raise HTTPException(status_code=404, detail="Group not found")
    # 同步删除 chat_store 中的群
    try:
        chat_store.delete_group(group_id)
    except Exception as sync_err:
        import logging
        logging.getLogger(__name__).warning(f"Failed to sync group delete to chat_store: {sync_err}")
    return {"code": 0, "message": "success", "data": None}


@router.post("/{group_id}/members", response_model=dict)
async def add_member(group_id: str, request: AddMemberRequest, db: Session = Depends(get_db)):
    service = GroupService(db)
    group = service.add_member(group_id, request.profile_name)
    if not group:
        raise HTTPException(status_code=404, detail="Group not found")
    # 同步到 chat_store
    try:
        chat_store.add_member(group_id, request.profile_name)
    except Exception as sync_err:
        import logging
        logging.getLogger(__name__).warning(f"Failed to sync member to chat_store: {sync_err}")
    return {"code": 0, "message": "success", "data": group.to_dict()}


@router.delete("/{group_id}/members/{profile_name}", response_model=dict)
async def remove_member(group_id: str, profile_name: str, db: Session = Depends(get_db)):
    service = GroupService(db)
    group = service.remove_member(group_id, profile_name)
    if not group:
        raise HTTPException(status_code=404, detail="Group not found")
    # 同步到 chat_store
    try:
        chat_store.remove_member(group_id, profile_name)
    except Exception as sync_err:
        import logging
        logging.getLogger(__name__).warning(f"Failed to sync member removal to chat_store: {sync_err}")
    return {"code": 0, "message": "success", "data": group.to_dict()}


@router.post("/{group_id}/host", response_model=dict)
async def set_host_agent(group_id: str, request: SetHostRequest, db: Session = Depends(get_db)):
    service = GroupService(db)
    group = service.update_group(group_id, host_agent=request.host_agent)
    if not group:
        raise HTTPException(status_code=404, detail="Group not found")
    return {"code": 0, "message": "success", "data": group.to_dict()}


@router.get("/{group_id}/outcomes")
async def get_meeting_outcomes(group_id: str, db: Session = Depends(get_db)):
    service = GroupService(db)
    outcomes = service.get_meeting_outcomes(group_id)
    return {"code": 0, "message": "success", "data": {"outcomes": [o.to_dict() for o in outcomes]}}


@router.get("/{group_id}/messages")
async def get_group_messages(group_id: str, limit: int = 200, db: Session = Depends(get_db), current_user=Depends(get_current_user)):
    service = GroupService(db)
    messages = service.get_messages(group_id, limit=limit)
    return {"code": 0, "message": "success", "data": {"messages": [m.to_dict() for m in messages]}}


@router.get("/{group_id}/ws-messages")
async def get_ws_messages(group_id: str, limit: int = 30, offset: int = 0):
    messages = chat_store.get_messages(group_id, limit=limit, offset=offset)
    total = chat_store.count_messages(group_id)
    return {"code": 0, "message": "success", "data": {"messages": messages, "total": total}}


class StartMeetingRequest(BaseModel):
    topic: str = "技术方案评审"
    host_agent: str = "Hermes"
    meeting_type: str = "tech_solution"
    pre_materials: Optional[List[str]] = None
    rules: Optional[Dict[str, Any]] = None


@router.post("/{group_id}/meeting/start")
async def start_meeting(
    group_id: str,
    request: StartMeetingRequest,
    db: Session = Depends(get_db),
    current_user=Depends(get_current_user)
):
    """启动会议"""
    from app.services.meeting_service import MeetingService
    svc = MeetingService(db)
    try:
        group = svc.start_meeting(
            group_id=group_id,
            topic=request.topic,
            host_agent_name=request.host_agent,
            meeting_type=request.meeting_type,
            pre_materials=request.pre_materials,
            rules=request.rules,
        )
        return {"code": 0, "message": "success", "data": {"group_id": group.id, "mode": group.mode}}
    except ValueError as e:
        error_detail = str(e)
        if "MEETING_001" in error_detail:
            raise HTTPException(status_code=409, detail=error_detail)
        if "MEETING_002" in error_detail:
            raise HTTPException(status_code=400, detail=error_detail)
        raise HTTPException(status_code=400, detail=error_detail)


@router.get("/{group_id}/tasks")
async def get_group_tasks(group_id: str, db: Session = Depends(get_db), current_user=Depends(get_current_user)):
    service = GroupService(db)
    tasks = service.get_pending_tasks()
    return {"code": 0, "message": "success", "data": {"tasks": [t.to_dict() for t in tasks if t.group_id == group_id]}}


@router.put("/tasks/{task_id}/status")
async def update_task_status(task_id: str, status: str, result: str = "", db: Session = Depends(get_db)):
    service = GroupService(db)
    task = service.update_task_status(task_id, status, result)
    if not task:
        raise HTTPException(status_code=404, detail="Task not found")
    return {"code": 0, "message": "success", "data": task.to_dict()}


@router.get("/tasks/pending")
async def get_pending_tasks(assignee: str = None, db: Session = Depends(get_db)):
    service = GroupService(db)
    tasks = service.get_pending_tasks(assignee=assignee)
    return {"code": 0, "message": "success", "data": {"tasks": [t.to_dict() for t in tasks]}}
