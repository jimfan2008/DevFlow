# 交付与通知服务 - 项目完成交付、进度通知、多渠道推送
from __future__ import annotations

import json
import logging
import uuid
from datetime import datetime, timezone
from typing import Optional

from sqlalchemy.orm import Session
from app.models.notification import InboxItem
from app.models.user import User
from app.models.project import Project

logger = logging.getLogger("devflow.delivery")


class DeliveryService:
    def __init__(self, db: Session):
        self.db = db

    # ── 进度通知 ─────────────────────────────────────────

    def notify_progress(self, user_id: str, project_id: str, title: str, content: str) -> InboxItem:
        """向用户发送关键节点进度通知。"""
        item = InboxItem(
            id=str(uuid.uuid4()),
            user_id=user_id,
            task_id=None,
            type="progress",
            title=title,
            content=content,
            is_read=False,
            metadata_json=json.dumps({"project_id": project_id, "notified_at": datetime.now(timezone.utc).isoformat()}),
        )
        self.db.add(item)
        self.db.commit()
        self.db.refresh(item)
        return item

    def notify_acceptance_result(self, user_id: str, task_title: str, passed: bool, detail: str) -> InboxItem:
        """通知用户任务验收结果。"""
        result = "通过" if passed else "驳回"
        item = InboxItem(
            id=str(uuid.uuid4()),
            user_id=user_id,
            task_id=None,
            type="acceptance",
            title=f"任务验收{result}: {task_title}",
            content=detail,
            is_read=False,
            metadata_json=json.dumps({"passed": passed, "task_title": task_title}),
        )
        self.db.add(item)
        self.db.commit()
        self.db.refresh(item)
        return item

    # ── 项目完成交付 ────────────────────────────────────

    def complete_project(self, project_id: str) -> dict:
        """标记项目为已完成，生成交付报告。"""
        project = self.db.query(Project).filter(Project.id == project_id).first()
        if not project:
            raise ValueError(f"Project {project_id} not found")

        now = datetime.now(timezone.utc)
        project.deleted_at = None  # 确保未删除
        project.updated_at = now

        delivery_report = {
            "project_id": project_id,
            "project_name": project.name,
            "completed_at": now.isoformat(),
            "status": "completed",
            "summary": f"项目 '{project.name}' 已完成所有开发任务",
        }

        # 通知项目创建者
        if project.creator_id:
            self.notify_completion(project.creator_id, project_id, project.name)

        self.db.commit()
        return delivery_report

    def notify_completion(self, user_id: str, project_id: str, project_name: str) -> InboxItem:
        """向用户发送项目完成通知。"""
        item = InboxItem(
            id=str(uuid.uuid4()),
            user_id=user_id,
            task_id=None,
            type="project_complete",
            title=f"项目完成: {project_name}",
            content=f"项目 '{project_name}' 已全部完成，请查看最终交付报告。",
            is_read=False,
            metadata_json=json.dumps({
                "project_id": project_id,
                "project_name": project_name,
                "completed_at": datetime.now(timezone.utc).isoformat(),
            }),
        )
        self.db.add(item)
        self.db.commit()
        self.db.refresh(item)
        return item

    # ── 里程碑通知 ──────────────────────────────────────

    NOTIFICATION_NODES = {
        "requirement_confirmed": "需求确认完成",
        "decomposition_done": "任务拆解完成",
        "core_delivery": "核心任务交付",
        "acceptance_rejected": "验收驳回",
        "half_progress": "整体进度过半",
    }

    def notify_milestone(self, user_id: str, project_id: str, milestone: str, extra: Optional[dict] = None) -> Optional[InboxItem]:
        """发送里程碑通知。"""
        if milestone not in self.NOTIFICATION_NODES:
            logger.warning("Unknown milestone: %s", milestone)
            return None

        title = self.NOTIFICATION_NODES[milestone]
        content = extra.get("detail", f"项目里程碑 '{title}' 已达成") if extra else f"项目里程碑 '{title}' 已达成"

        return self.notify_progress(user_id, project_id, f"里程碑: {title}", content)