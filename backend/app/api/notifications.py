from fastapi import APIRouter, Depends, HTTPException
from sqlalchemy.orm import Session
from typing import Optional
from app.database import get_db
from app.api.deps import get_current_user
from app.models.user import User
from app.services.notification_service import NotificationService
from app.schemas.notification import NotificationCreate

router = APIRouter(redirect_slashes=False)


@router.get("", response_model=dict)
def list_notifications(
    is_read: Optional[bool] = None,
    project_id: Optional[str] = None,
    limit: int = 50,
    db: Session = Depends(get_db),
    current_user: User = Depends(get_current_user),
):
    svc = NotificationService(db)
    notifications = svc.get_notifications(current_user.id, is_read=is_read, project_id=project_id, limit=limit)
    unread_count = svc.get_unread_count(current_user.id)
    return {
        "code": 0,
        "message": "success",
        "data": {
            "notifications": [n.to_dict() for n in notifications],
            "total": len(notifications),
            "unread_count": unread_count,
        },
    }


@router.post("", response_model=dict)
def create_notification(
    data: NotificationCreate,
    db: Session = Depends(get_db),
    current_user: User = Depends(get_current_user),
):
    svc = NotificationService(db)
    notification = svc.create_notification(
        user_id=data.user_id,
        type=data.type,
        title=data.title,
        content=data.content,
        project_id=data.project_id,
        channel=data.channel,
    )
    return {"code": 0, "message": "success", "data": {"notification": notification.to_dict()}}


@router.put("/{notification_id}/read", response_model=dict)
def mark_as_read(
    notification_id: str,
    db: Session = Depends(get_db),
    current_user: User = Depends(get_current_user),
):
    svc = NotificationService(db)
    notification = svc.mark_as_read(notification_id)
    if not notification:
        raise HTTPException(status_code=404, detail="Notification not found")
    return {"code": 0, "message": "success"}


@router.put("/read-all", response_model=dict)
def mark_all_as_read(
    db: Session = Depends(get_db),
    current_user: User = Depends(get_current_user),
):
    svc = NotificationService(db)
    count = svc.mark_all_as_read(current_user.id)
    return {"code": 0, "message": "success", "data": {"marked_count": count}}


@router.get("/unread-count", response_model=dict)
def get_unread_count(
    db: Session = Depends(get_db),
    current_user: User = Depends(get_current_user),
):
    svc = NotificationService(db)
    count = svc.get_unread_count(current_user.id)
    return {"code": 0, "message": "success", "data": {"unread_count": count}}
