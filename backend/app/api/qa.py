"""v4.0 - QA 门控 API"""
from fastapi import APIRouter
from typing import Optional
from pydantic import BaseModel
from app.services.qa_gate_service import QAGateService

router = APIRouter(redirect_slashes=False)


class InspectRequest(BaseModel):
    artifact_type: str
    project_id: str
    workflow_step_id: int
    result: str = "passed"
    reason: Optional[str] = None
    suggestions: Optional[list[str]] = None


class RollbackRequest(BaseModel):
    task_id: str
    project_id: str
    workflow_step_id: int
    reason: str
    suggestions: Optional[list[str]] = None


_qa_service = QAGateService()


@router.post("/inspect")
def inspect_artifact(body: InspectRequest):
    record = _qa_service.inspect(
        artifact_type=body.artifact_type,
        project_id=body.project_id,
        workflow_step_id=body.workflow_step_id,
        result=body.result,
        reason=body.reason,
        suggestions=body.suggestions,
    )
    return {"message": "QA检验完成", "record": record}


@router.get("/{project_id}/records")
def get_qa_records(project_id: str):
    records = _qa_service.get_all_records(project_id=project_id)
    return {"project_id": project_id, "total": len(records), "records": records}


@router.post("/rollback")
def rollback_task(body: RollbackRequest):
    record = _qa_service.rollback(
        task_id=body.task_id,
        project_id=body.project_id,
        workflow_step_id=body.workflow_step_id,
        reason=body.reason,
        suggestions=body.suggestions,
    )
    return {"message": "任务已退回重做", "record": record}


@router.get("/status")
def get_inspection_status(task_id: Optional[str] = None, step_id: Optional[int] = None):
    status = _qa_service.get_inspection_status(task_id=task_id, step_id=step_id)
    return status