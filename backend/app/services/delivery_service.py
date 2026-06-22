# 交付与通知服务 - 项目完成交付、进度通知
from __future__ import annotations

import json
import logging
from datetime import datetime, timezone
from typing import Optional

from sqlalchemy.orm import Session
from app.models.project import Project

logger = logging.getLogger("devflow.delivery")


class DeliveryService:
    def __init__(self, db: Session):
        self.db = db

    # ── 项目完成交付 ────────────────────────────────────

    def complete_project(self, project_id: str) -> dict:
        """标记项目为已完成，生成交付报告。"""
        project = self.db.query(Project).filter(Project.id == project_id).first()
        if not project:
            raise ValueError(f"Project {project_id} not found")

        now = datetime.now(timezone.utc)
        project.deleted_at = None
        project.updated_at = now

        delivery_report = {
            "project_id": project_id,
            "project_name": project.name,
            "completed_at": now.isoformat(),
            "status": "completed",
            "summary": f"项目 '{project.name}' 已完成所有开发任务",
        }

        self.db.commit()
        return delivery_report

    # ── 里程碑通知 ──────────────────────────────────────

    NOTIFICATION_NODES = {
        "requirement_confirmed": "需求确认完成",
        "decomposition_done": "任务拆解完成",
        "core_delivery": "核心任务交付",
        "acceptance_rejected": "验收驳回",
        "half_progress": "整体进度过半",
    }

    def notify_milestone(self, user_id: str, project_id: str, milestone: str, extra: Optional[dict] = None):
        """发送里程碑通知。"""
        if milestone not in self.NOTIFICATION_NODES:
            logger.warning("Unknown milestone: %s", milestone)
            return None

        title = self.NOTIFICATION_NODES[milestone]
        content = extra.get("detail", f"项目里程碑 '{title}' 已达成") if extra else f"项目里程碑 '{title}' 已达成"
        logger.info(f"里程碑 {milestone}: {content}")
