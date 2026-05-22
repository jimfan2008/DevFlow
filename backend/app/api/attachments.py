#!/usr/bin/env python3
"""附件 API 路由"""
from fastapi import APIRouter, Depends
from sqlalchemy.orm import Session
from app.database import get_db
from app.services.attachment_service import AttachmentService
from app.api.deps import get_current_user

router = APIRouter(redirect_slashes=False)

@router.post("/{task_id}/attachments", tags=["attachments"])
def add_attachment(task_id: str, data: dict, current_user = Depends(get_current_user), db: Session = Depends(get_db)):
    service = AttachmentService(db=db, current_user_id=current_user.id)
    try:
        result = service.add_attachment(
            task_id=task_id,
            name=data["name"],
            file_path=f"/tmp/attachments/{task_id}/{data['name']}",
            size=data.get("size", 0),
            type=data.get("type", "application/octet-stream"),
        )
        return {"success": True, "attachment": result}
    except ValueError as e:
        return {"success": False, "error": str(e)}

@router.get("/{task_id}/attachments", tags=["attachments"])
def list_attachments(task_id: str, current_user = Depends(get_current_user), db: Session = Depends(get_db)):
    service = AttachmentService(db=db, current_user_id=current_user.id)
    try:
        attachments = service.get_attachments(task_id)
        return {"success": True, "attachments": attachments, "total": len(attachments)}
    except ValueError as e:
        return {"success": False, "error": str(e)}

@router.delete("/{task_id}/attachments/{attachment_id}", tags=["attachments"])
def delete_attachment(task_id: str, attachment_id: str, current_user = Depends(get_current_user), db: Session = Depends(get_db)):
    service = AttachmentService(db=db, current_user_id=current_user.id)
    try:
        service.delete_attachment(attachment_id)
        return {"success": True}
    except ValueError as e:
        return {"success": False, "error": str(e)}
