#!/usr/bin/env python3
"""依赖 API 路由"""
from fastapi import APIRouter, Depends
from sqlalchemy.orm import Session
from app.database import get_db
from app.services.dependency_service import DependencyService
from app.api.deps import get_current_user

router = APIRouter()

@router.post("/{task_id}/depend", tags=["dependencies"])
def create_dependency(task_id: str, data: dict, current_user = Depends(get_current_user), db: Session = Depends(get_db)):
    service = DependencyService(db=db)
    try:
        result = service.create_dependency(
            source_task_id=data["source_task_id"],
            target_task_id=data["target_task_id"],
        )
        return {"success": True, "dependency": result}
    except ValueError as e:
        return {"success": False, "error": str(e)}

@router.get("/{task_id}/depend", tags=["dependencies"])
def list_dependencies(task_id: str, current_user = Depends(get_current_user), db: Session = Depends(get_db)):
    service = DependencyService(db=db)
    try:
        return {"success": True, "dependencies": service.get_dependencies(task_id)}
    except ValueError as e:
        return {"success": False, "error": str(e)}

@router.get("/{task_id}/depend/graph", tags=["dependencies"])
def get_dependency_graph(task_id: str, current_user = Depends(get_current_user), db: Session = Depends(get_db)):
    service = DependencyService(db=db)
    try:
        result = service.get_dependency_graph(task_id)
        return {"success": True, **result}
    except ValueError as e:
        return {"success": False, "error": str(e)}

@router.delete("/{task_id}/depend/{target_id}", tags=["dependencies"])
def delete_dependency(task_id: str, target_id: str, current_user = Depends(get_current_user), db: Session = Depends(get_db)):
    service = DependencyService(db=db)
    try:
        service.delete_dependency(task_id, target_id)
        return {"success": True}
    except ValueError as e:
        return {"success": False, "error": str(e)}
