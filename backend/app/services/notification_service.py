from __future__ import annotations

import uuid
import logging
from datetime import datetime, timezone
from typing import Optional, List

from sqlalchemy.orm import Session
from sqlalchemy import and_
from app.models.notification import Notification
from app.models.enums import NotificationChannel

logger = logging.getLogger("devflow.notification")


class NotificationService:
    def __init__(self, db: Session):
        self.db = db

    def create_notification(self, user_id: str, type: str, title: str, content: str,
                            project_id: str = None, channel: str = "platform") -> Notification:
        notification = Notification(
            id=str(uuid.uuid4()),
            user_id=user_id,
            project_id=project_id,
            type=type,
            title=title,
            content=content,
            channel=channel,
            is_read=False,
        )
        self.db.add(notification)
        self.db.commit()
        self.db.refresh(notification)
        return notification

    def send_multi_channel(self, user_id: str, type: str, title: str, content: str,
                           project_id: str = None,
                           channels: List[str] = None) -> List[Notification]:
        if channels is None:
            channels = [NotificationChannel.platform.value]

        results = []
        for channel in channels:
            n = self.create_notification(
                user_id=user_id, type=type, title=title, content=content,
                project_id=project_id, channel=channel,
            )
            results.append(n)

            if channel == NotificationChannel.email.value:
                logger.info(f"Email notification sent to user {user_id}: {title}")
            elif channel == NotificationChannel.sms.value:
                logger.info(f"SMS notification sent to user {user_id}: {title}")

        return results

    def notify_requirement_confirmed(self, project_id: str, user_id: str, project_name: str):
        return self.send_multi_channel(
            user_id=user_id, type="requirement_confirmed",
            title=f"需求已确认: {project_name}",
            content=f"项目 '{project_name}' 的需求已确认锁定，将开始任务拆解",
            project_id=project_id,
        )

    def notify_task_decomposed(self, project_id: str, user_id: str, task_count: int):
        return self.send_multi_channel(
            user_id=user_id, type="task_decomposed",
            title="任务拆解完成",
            content=f"项目任务已自动拆解为 {task_count} 个子任务",
            project_id=project_id,
        )

    def notify_task_assigned(self, task_id: str, agent_name: str, task_name: str,
                             user_id: str = None, project_id: str = None):
        if user_id:
            return self.create_notification(
                user_id=user_id, type="task_assigned",
                title=f"任务已分配: {task_name}",
                content=f"任务 '{task_name}' 已通过Skill层分配给 {agent_name}",
                project_id=project_id, channel="platform",
            )
        return None

    def notify_acceptance_result(self, task_id: str, task_name: str, passed: bool,
                                 user_id: str, project_id: str = None,
                                 detail: str = ""):
        result_text = "通过" if passed else "驳回"
        channels = [NotificationChannel.platform.value]
        if not passed:
            channels.append(NotificationChannel.email.value)
        return self.send_multi_channel(
            user_id=user_id, type="acceptance_result",
            title=f"任务验收{result_text}: {task_name}",
            content=detail or f"任务 '{task_name}' 验收{result_text}",
            project_id=project_id, channels=channels,
        )

    def notify_project_completed(self, project_id: str, user_id: str, project_name: str):
        return self.send_multi_channel(
            user_id=user_id, type="project_completed",
            title=f"项目完成: {project_name}",
            content=f"项目 '{project_name}' 已全部完成，请查看最终交付报告",
            project_id=project_id,
            channels=[NotificationChannel.platform.value, NotificationChannel.email.value],
        )

    def notify_rejection_escalation(self, task_id: str, task_name: str,
                                    rejection_count: int, user_id: str,
                                    project_id: str = None):
        return self.send_multi_channel(
            user_id=user_id, type="rejection_escalation",
            title=f"任务连续驳回升级: {task_name}",
            content=f"任务 '{task_name}' 已连续被驳回 {rejection_count} 次，请人工介入",
            project_id=project_id,
            channels=[NotificationChannel.platform.value, NotificationChannel.email.value, NotificationChannel.sms.value],
        )

    def get_notifications(self, user_id: str, is_read: bool = None,
                          project_id: str = None, limit: int = 50) -> List[Notification]:
        query = self.db.query(Notification).filter(Notification.user_id == user_id)
        if is_read is not None:
            query = query.filter(Notification.is_read == is_read)
        if project_id:
            query = query.filter(Notification.project_id == project_id)
        return query.order_by(Notification.created_at.desc()).limit(limit).all()

    def mark_as_read(self, notification_id: str) -> Optional[Notification]:
        n = self.db.query(Notification).filter(Notification.id == notification_id).first()
        if not n:
            return None
        n.is_read = True
        self.db.commit()
        self.db.refresh(n)
        return n

    def mark_all_as_read(self, user_id: str) -> int:
        result = self.db.query(Notification).filter(
            and_(Notification.user_id == user_id, Notification.is_read == False)
        ).update({"is_read": True})
        self.db.commit()
        return result

    def get_unread_count(self, user_id: str) -> int:
        return self.db.query(Notification).filter(
            and_(Notification.user_id == user_id, Notification.is_read == False)
        ).count()
