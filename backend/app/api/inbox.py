#!/usr/bin/env python3
"""收件箱 API 路由"""
from fastapi import APIRouter, Depends, Query
from sqlalchemy.orm import Session
from app.database import get_db
from app.services.inbox_service import InboxService
from app.api.deps import get_current_user

router = APIRouter(redirect_slashes=False)

@router.get("", tags=["inbox"])
def get_inbox(
    category: str = Query(None),
    filter: str = Query(None),
    page: int = 1,
    per_page: int = 20,
    current_user = Depends(get_current_user),
    db: Session = Depends(get_db),
):
    service = InboxService(db=db, current_user_id=current_user.id)
    try:
        result = service.get_inbox(current_user.id, category or filter, page, per_page)
        return {"success": True, **result}
    except Exception as e:
        return {"success": False, "error": str(e)}

@router.get("/unread/count", tags=["inbox"])
def get_unread_count(current_user = Depends(get_current_user), db: Session = Depends(get_db)):
    service = InboxService(db=db, current_user_id=current_user.id)
    try:
        return {"success": True, **service.get_unread_count(current_user.id)}
    except Exception as e:
        return {"success": False, "error": str(e)}

@router.get("/search", tags=["inbox"])
def search_inbox(q: str, current_user = Depends(get_current_user), db: Session = Depends(get_db)):
    service = InboxService(db=db, current_user_id=current_user.id)
    try:
        return {"success": True, **service.get_search_results(current_user.id, q)}
    except Exception as e:
        return {"success": False, "error": str(e)}

@router.put("/{item_id}/read", tags=["inbox"])
def mark_as_read(item_id: str, current_user = Depends(get_current_user), db: Session = Depends(get_db)):
    service = InboxService(db=db, current_user_id=current_user.id)
    try:
        return {"success": True, "item": service.mark_as_read(item_id)}
    except ValueError as e:
        return {"success": False, "error": str(e)}

@router.put("/all/read", tags=["inbox"])
def mark_all_read(current_user = Depends(get_current_user), db: Session = Depends(get_db)):
    service = InboxService(db=db, current_user_id=current_user.id)
    try:
        return {"success": True, **service.mark_all_as_read(current_user.id)}
    except Exception as e:
        return {"success": False, "error": str(e)}

@router.delete("/{item_id}", tags=["inbox"])
def delete_inbox_item(item_id: str, current_user = Depends(get_current_user), db: Session = Depends(get_db)):
    service = InboxService(db=db, current_user_id=current_user.id)
    try:
        service.db.query(service._import_models()[0]).filter(
            service._import_models()[0].id == item_id,
            service._import_models()[0].user_id == current_user.id
        ).delete()
        service.db.commit()
        return {"success": True}
    except Exception as e:
        return {"success": False, "error": str(e)}

@router.get("/reminders", tags=["inbox"])
def get_reminders(current_user = Depends(get_current_user), db: Session = Depends(get_db)):
    service = InboxService(db=db, current_user_id=current_user.id)
    try:
        return {"success": True, "reminders": service.get_reminders(current_user.id)}
    except Exception as e:
        return {"success": False, "error": str(e)}

@router.post("/watch", tags=["inbox"])
def watch_task(data: dict, current_user = Depends(get_current_user), db: Session = Depends(get_db)):
    service = InboxService(db=db, current_user_id=current_user.id)
    try:
        return service.watch_task(current_user.id, data["task_id"])
    except ValueError as e:
        return {"success": False, "error": str(e)}

@router.put("/preferences", tags=["inbox"])
def update_preferences(data: dict, current_user = Depends(get_current_user), db: Session = Depends(get_db)):
    service = InboxService(db=db, current_user_id=current_user.id)
    try:
        result = service.update_preferences(current_user.id, **{k: v for k, v in data.items() if v is not None})
        return {"success": True, "preferences": result}
    except Exception as e:
        return {"success": False, "error": str(e)}

@router.get("/preferences", tags=["inbox"])
def get_preferences(current_user = Depends(get_current_user), db: Session = Depends(get_db)):
    service = InboxService(db=db, current_user_id=current_user.id)
    try:
        return {"success": True, "preferences": service.get_preferences(current_user.id)}
    except Exception as e:
        return {"success": False, "error": str(e)}
