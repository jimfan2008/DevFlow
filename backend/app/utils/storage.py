#!/usr/bin/env python3
"""文件存储工具"""
import os
import uuid
from pathlib import Path


ATTACHMENT_DIR = Path("/tmp/attachments")


def ensure_attachment_dir(task_id: str) -> Path:
    """确保附件目录存在"""
    task_dir = ATTACHMENT_DIR / str(task_id)
    task_dir.mkdir(parents=True, exist_ok=True)
    return task_dir


def save_file(file, task_id: str, filename: str) -> str:
    """保存文件到本地存储"""
    task_dir = ensure_attachment_dir(task_id)
    file_path = task_dir / filename
    with open(file_path, "wb") as f:
        f.write(file.read())
    return str(file_path)


def get_file_url(file_path: str) -> str:
    """获取文件 URL"""
    relative = os.path.relpath(file_path, ATTACHMENT_DIR)
    return f"/api/files/{relative}"


def delete_file(file_path: str) -> bool:
    """删除文件"""
    try:
        os.remove(file_path)
        return True
    except FileNotFoundError:
        return False
