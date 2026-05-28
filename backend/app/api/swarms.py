"""v4.0 - Agent 蜂群 API"""
from fastapi import APIRouter, HTTPException
from typing import Optional
from pydantic import BaseModel
from app.services.swarm_service import SwarmService

router = APIRouter(redirect_slashes=False)


class CreateSwarmRequest(BaseModel):
    project_id: str
    name: str
    purpose: str
    step_number: int
    manager_role: str


class AddMemberRequest(BaseModel):
    agent_type: str
    agent_id: str


class DispatchTasksRequest(BaseModel):
    tasks: list[dict]


_swarm_service = SwarmService()


@router.post("")
def create_swarm(body: CreateSwarmRequest):
    swarm = _swarm_service.create_swarm(
        project_id=body.project_id,
        name=body.name,
        purpose=body.purpose,
        step_number=body.step_number,
        manager_role=body.manager_role,
    )
    return {"message": "Agent蜂群创建成功", "swarm": swarm}


@router.get("/{swarm_id}")
def get_swarm(swarm_id: int):
    swarm = _swarm_service.get_swarm(swarm_id)
    if swarm is None:
        raise HTTPException(status_code=404, detail="蜂群不存在")
    return swarm


@router.post("/{swarm_id}/members")
def add_member(swarm_id: int, body: AddMemberRequest):
    swarm = _swarm_service.add_member(
        swarm_id=swarm_id,
        agent_type=body.agent_type,
        agent_id=body.agent_id,
    )
    return {"message": "成员已添加到蜂群", "swarm": swarm}


@router.delete("/{swarm_id}/members/{agent_id}")
def remove_member(swarm_id: int, agent_id: str):
    swarm = _swarm_service.remove_member(swarm_id=swarm_id, agent_id=agent_id)
    return {"message": "成员已从蜂群移除", "swarm": swarm}


@router.post("/{swarm_id}/dispatch")
def dispatch_tasks(swarm_id: int, body: DispatchTasksRequest):
    assignments = _swarm_service.dispatch_tasks(swarm_id=swarm_id, tasks=body.tasks)
    return {"message": "任务分发完成", "assignments": assignments}


@router.get("/{swarm_id}/progress")
def get_swarm_progress(swarm_id: int):
    progress = _swarm_service.get_progress(swarm_id=swarm_id)
    return progress


@router.delete("/{swarm_id}")
def disband_swarm(swarm_id: int):
    swarm = _swarm_service.disband_swarm(swarm_id=swarm_id)
    return {"message": "蜂群已解散", "swarm": swarm}