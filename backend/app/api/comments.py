#!/usr/bin/env python3
"""评论 API 路由"""
from fastapi import APIRouter, Depends
from sqlalchemy.orm import Session
from app.database import get_db
from app.services.comment_service import CommentService
from app.api.deps import get_current_user

router = APIRouter(redirect_slashes=False)

@router.post("/{task_id}/comments", tags=["comments"])
def create_comment(task_id: str, data: dict, current_user = Depends(get_current_user), db: Session = Depends(get_db)):
    service = CommentService(db=db, current_user_id=current_user.id)
    try:
        result = service.create_comment(task_id, data["content"])
        return {"success": True, "comment": result}
    except ValueError as e:
        return {"success": False, "error": str(e)}

@router.get("/{task_id}/comments", tags=["comments"])
def list_comments(task_id: str, current_user = Depends(get_current_user), db: Session = Depends(get_db)):
    service = CommentService(db=db, current_user_id=current_user.id)
    try:
        comments = service.get_comments(task_id)
        return {"success": True, "comments": comments, "total": len(comments)}
    except ValueError as e:
        return {"success": False, "error": str(e)}

@router.delete("/{task_id}/comments/{comment_id}", tags=["comments"])
def delete_comment(task_id: str, comment_id: str, current_user = Depends(get_current_user), db: Session = Depends(get_db)):
    service = CommentService(db=db, current_user_id=current_user.id)
    try:
        service.delete_comment(comment_id)
        return {"success": True}
    except ValueError as e:
        return {"success": False, "error": str(e)}
