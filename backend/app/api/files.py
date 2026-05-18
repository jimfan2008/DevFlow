#!/usr/bin/env python3
"""
DevFlow 文件上传 API 路由
"""
from fastapi import APIRouter, Depends, HTTPException, UploadFile, File, Form
from fastapi.responses import FileResponse
from sqlalchemy.orm import Session
from datetime import datetime, timezone
import uuid
import os
import shutil

from app.database import get_db
from app.api.deps import get_current_user
from app.config import get_settings

router = APIRouter()
settings = get_settings()


@router.post("/{task_id}/upload")
async def upload_file(
    task_id: str,
    file: UploadFile = File(...),
    current_user=Depends(get_current_user),
    db: Session = Depends(get_db),
):
    """上传文件附件到任务"""
    # 验证文件大小
    if file.size and file.size > settings.MAX_UPLOAD_SIZE:
        raise HTTPException(
            status_code=413,
            detail=f"File size exceeds maximum allowed size of {settings.MAX_UPLOAD_SIZE / 1024 / 1024}MB"
        )

    # 创建上传目录
    upload_dir = os.path.join(settings.UPLOAD_DIR, task_id)
    os.makedirs(upload_dir, exist_ok=True)

    # 生成唯一文件名
    original_name = file.filename or str(uuid.uuid4())
    ext = os.path.splitext(original_name)[1]
    unique_name = f"{uuid.uuid4()}{ext}"
    file_path = os.path.join(upload_dir, unique_name)

    # 保存文件
    try:
        content = await file.read()
        with open(file_path, "wb") as f:
            f.write(content)
    except Exception as e:
        raise HTTPException(status_code=500, detail=f"Failed to save file: {str(e)}")

    # 记录附件到数据库
    from app.models.attachment import Attachment
    attachment = Attachment(
        id=str(uuid.uuid4()),
        task_id=task_id,
        name=original_name,
        file_path=file_path,
        file_url=f"/api/files/{task_id}/{unique_name}",
        size=file.size or 0,
        type=file.content_type or "application/octet-stream",
        uploaded_by=current_user.id,
        created_at=datetime.now(timezone.utc),
    )
    db.add(attachment)
    db.commit()
    db.refresh(attachment)

    return {
        "success": True,
        "attachment": attachment.to_dict(),
        "download_url": f"/api/files/{task_id}/{unique_name}",
    }


@router.get("/{task_id}/{filename}")
async def serve_file(task_id: str, filename: str):
    """提供附件文件下载"""
    upload_dir = os.path.join(settings.UPLOAD_DIR, task_id)
    file_path = os.path.join(upload_dir, filename)

    if not os.path.exists(file_path):
        raise HTTPException(status_code=404, detail="File not found")

    return FileResponse(file_path)


@router.delete("/{task_id}/{filename}")
async def delete_file(
    task_id: str,
    filename: str,
    current_user=Depends(get_current_user),
    db: Session = Depends(get_db),
):
    """删除附件文件"""
    from app.models.attachment import Attachment
    upload_dir = os.path.join(settings.UPLOAD_DIR, task_id)
    file_path = os.path.join(upload_dir, filename)

    # 查找附件记录
    attachment = db.query(Attachment).filter(
        Attachment.task_id == task_id,
        Attachment.file_path == file_path,
    ).first()

    if not attachment:
        raise HTTPException(status_code=404, detail="Attachment not found")

    # 删除文件
    try:
        if os.path.exists(file_path):
            os.remove(file_path)
    except Exception as e:
        raise HTTPException(status_code=500, detail=f"Failed to delete file: {str(e)}")

    # 删除数据库记录
    db.delete(attachment)
    db.commit()

    return {"success": True, "message": "File deleted successfully"}
