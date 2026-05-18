from fastapi import APIRouter, HTTPException, Depends
from typing import List
from sqlalchemy.orm import Session
from app.database import get_db
from app.schemas.group import (
    GroupCreate, GroupUpdate, GroupResponse,
    AddMemberRequest, SetHostRequest,
    SendMessageRequest,
    MeetingOutcomeResponse, GroupTaskResponse
)
from app.services.group_service import GroupService

router = APIRouter(prefix="/api/groups", tags=["groups"])


@router.get("/", response_model=List[dict])
async def list_groups(db: Session = Depends(get_db)):
    """获取所有群组"""
    try:
        service = GroupService(db)
        groups = service.get_all_groups()
        return [g.to_dict() for g in groups]
    except Exception as e:
        raise HTTPException(status_code=500, detail=f"Failed to get groups: {str(e)}")


@router.post("/", response_model=dict)
async def create_group(request: GroupCreate, db: Session = Depends(get_db)):
    """创建新群组"""
    try:
        service = GroupService(db)
        group = service.create_group(
            name=request.name,
            description=request.description,
            members=request.members
        )
        return group.to_dict()
    except Exception as e:
        raise HTTPException(status_code=500, detail=f"Failed to create group: {str(e)}")


@router.get("/{group_id}", response_model=dict)
async def get_group(group_id: str, db: Session = Depends(get_db)):
    """获取群组详情"""
    service = GroupService(db)
    group = service.get_group(group_id)
    if not group:
        raise HTTPException(status_code=404, detail="Group not found")
    return group.to_dict()


@router.put("/{group_id}", response_model=dict)
async def update_group(group_id: str, request: GroupUpdate, db: Session = Depends(get_db)):
    """更新群组信息"""
    service = GroupService(db)
    update_data = request.model_dump(exclude_none=True)
    group = service.update_group(group_id, **update_data)
    if not group:
        raise HTTPException(status_code=404, detail="Group not found")
    return group.to_dict()


@router.delete("/{group_id}")
async def delete_group(group_id: str, db: Session = Depends(get_db)):
    """删除群组"""
    service = GroupService(db)
    success = service.delete_group(group_id)
    if not success:
        raise HTTPException(status_code=404, detail="Group not found")
    return {"message": "Group deleted successfully"}


@router.post("/{group_id}/members", response_model=dict)
async def add_member(group_id: str, request: AddMemberRequest, db: Session = Depends(get_db)):
    """添加成员到群组"""
    service = GroupService(db)
    group = service.add_member(group_id, request.profile_name)
    if not group:
        raise HTTPException(status_code=404, detail="Group not found")
    return group.to_dict()


@router.delete("/{group_id}/members/{profile_name}", response_model=dict)
async def remove_member(group_id: str, profile_name: str, db: Session = Depends(get_db)):
    """从群组移除成员"""
    service = GroupService(db)
    group = service.remove_member(group_id, profile_name)
    if not group:
        raise HTTPException(status_code=404, detail="Group not found")
    return group.to_dict()


@router.post("/{group_id}/host", response_model=dict)
async def set_host_agent(group_id: str, request: SetHostRequest, db: Session = Depends(get_db)):
    """设置主持 agent"""
    service = GroupService(db)
    group = service.update_group(group_id, host_agent=request.host_agent)
    if not group:
        raise HTTPException(status_code=404, detail="Group not found")
    return group.to_dict()


@router.get("/{group_id}/outcomes")
async def get_meeting_outcomes(group_id: str, db: Session = Depends(get_db)):
    """获取群组的会议结果"""
    service = GroupService(db)
    outcomes = service.get_meeting_outcomes(group_id)
    return [o.to_dict() for o in outcomes]


@router.get("/{group_id}/messages")
async def get_group_messages(group_id: str, limit: int = 200, db: Session = Depends(get_db)):
    """获取群组历史消息"""
    service = GroupService(db)
    messages = service.get_messages(group_id, limit=limit)
    return [m.to_dict() for m in messages]


@router.get("/{group_id}/tasks")
async def get_group_tasks(group_id: str, db: Session = Depends(get_db)):
    """获取群组的待办任务"""
    service = GroupService(db)
    tasks = service.get_pending_tasks()
    return [t.to_dict() for t in tasks if t.group_id == group_id]


@router.put("/tasks/{task_id}/status")
async def update_task_status(task_id: str, status: str, result: str = "", db: Session = Depends(get_db)):
    """更新任务状态"""
    service = GroupService(db)
    task = service.update_task_status(task_id, status, result)
    if not task:
        raise HTTPException(status_code=404, detail="Task not found")
    return {"message": "Task status updated"}


@router.get("/tasks/pending")
async def get_pending_tasks(assignee: str = None, db: Session = Depends(get_db)):
    """获取待办任务，可按负责人筛选"""
    service = GroupService(db)
    tasks = service.get_pending_tasks(assignee=assignee)
    return [t.to_dict() for t in tasks]
