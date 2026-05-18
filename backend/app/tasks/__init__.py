#!/usr/bin/env python3
"""
DevFlow Celery 异步任务 - 到期提醒、通知、状态变更联动
"""
from celery import Celery
from datetime import datetime, timezone, timedelta
from app.config import settings

celery_app = Celery(
    "devflow_tasks",
    broker=settings.CELERY_BROKER_URL,
    backend=settings.CELERY_RESULT_BACKEND,
)

celery_app.conf.update(
    task_serializer=settings.CELERY_TASK_SERIALIZER,
    result_serializer=settings.CELERY_RESULT_SERIALIZER,
    accept_content=settings.CELERY_ACCEPT_CONTENT,
    timezone="UTC",
    enable_utc=True,
    beat_schedule={
        "check-task-due-reminders": {
            "task": "devflow_tasks.check_due_reminders",
            "schedule": 3600.0,
        },
        "cleanup-expired-sessions": {
            "task": "devflow_tasks.cleanup_expired_sessions",
            "schedule": 86400.0,
        },
        "profile-scan-task": {
            "task": "devflow_tasks.profile_scan_task",
            "schedule": 300.0,
        },
        "check-agent-health-task": {
            "task": "devflow_tasks.check_agent_health_task",
            "schedule": 60.0,
        },
        "skill-discover-task": {
            "task": "devflow_tasks.skill_discover_task",
            "schedule": 30.0,
        },
    },
)


@celery_app.task(bind=True, name="devflow_tasks.check_due_reminders")
def check_due_reminders(self):
    """检查待办任务的到期提醒，创建收件箱通知"""
    try:
        from app.database import SessionLocal
        from app.models.task import Task
        from app.models.notification import InboxItem

        db = SessionLocal()
        now = datetime.now(timezone.utc)
        tasks = db.query(Task).filter(
            Task.status != "done",
            Task.due_date.isnot(None),
        ).all()

        reminders_created = 0
        for task in tasks:
            if not task.due_date:
                continue
            days_remaining = (task.due_date - now).days

            # 根据天数确定提醒级别
            if days_remaining <= 0:
                reminder_level = "urgent"
            elif days_remaining <= 1:
                reminder_level = "soon"
            elif days_remaining <= 3:
                reminder_level = "upcoming"
            else:
                continue

            # 检查是否已经为该任务和该级别创建过提醒
            existing = db.query(InboxItem).filter(
                InboxItem.task_id == task.id,
                InboxItem.type == "reminder",
                InboxItem.metadata_json.like(f'%"reminder_level": "%{reminder_level}%"'),
            ).first()

            if not existing and task.assignee_id:
                item = InboxItem(
                    id=f"reminder-{task.id}-{reminder_level}",
                    user_id=task.assignee_id,
                    task_id=task.id,
                    type="reminder",
                    title=f"到期提醒: {task.title}",
                    content=f"任务 '{task.title}' 将在 {days_remaining} 天后到期",
                    is_read=False,
                    metadata_json=f'{{"reminder_level": "{reminder_level}", "days_remaining": {days_remaining}}}',
                    created_at=now,
                )
                db.add(item)
                reminders_created += 1

        db.commit()
        db.close()
        return {"reminders_created": reminders_created}
    except Exception as e:
        return {"error": str(e), "reminders_created": 0}


@celery_app.task(bind=True, name="devflow_tasks.cleanup_expired_sessions")
def cleanup_expired_sessions(self):
    """清理过期的 JWT 会话（如果有 Redis 会话黑名单）"""
    try:
        # MVP 阶段暂不实现会话黑名单
        # 生产环境可以在此实现 Redis 会话管理
        return {"cleaned_sessions": 0, "message": "Session cleanup not implemented in MVP"}
    except Exception as e:
        return {"error": str(e)}


@celery_app.task(bind=True, name="devflow_tasks.send_email_notification")
def send_email_notification(self, recipient: str, subject: str, body: str):
    """发送邮件通知（MVP 阶段为占位实现）"""
    # 生产环境需要配置 SMTP 并实现真实发送
    return {
        "recipient": recipient,
        "subject": subject,
        "sent": False,
        "message": "Email sending not implemented in MVP - configure SMTP first",
    }


@celery_app.task(bind=True, name="devflow_tasks.aggregate_workload_data")
def aggregate_workload_data(self, board_id: str, days: int = 7):
    """聚合工作负载数据（定时分析任务）"""
    try:
        from app.database import SessionLocal
        from app.models.task import Task
        from app.models.board import Board

        db = SessionLocal()
        board = db.query(Board).filter(Board.id == board_id).first()
        if not board:
            return {"error": "Board not found"}

        start_date = datetime.now(timezone.utc) - timedelta(days=days)
        tasks = db.query(Task).filter(
            Task.board_id == board_id,
            Task.created_at >= start_date,
        ).all()

        trend = {}
        for task in tasks:
            if task.created_at:
                day_key = task.created_at.strftime("%Y-%m-%d")
                if day_key not in trend:
                    trend[day_key] = {"created": 0, "completed": 0}
                trend[day_key]["created"] += 1
                if task.status == "done":
                    trend[day_key]["completed"] += 1

        db.close()
        return {"board_id": board_id, "trend": trend}
    except Exception as e:
        return {"error": str(e)}


# ═══════════════════════════════════════════════════════
# SRS §3.2 自动任务拆解任务
# ═══════════════════════════════════════════════════════

@celery_app.task(bind=True, name="devflow_tasks.decompose_requirements")
def decompose_requirements(self, project_id: str, requirement_content: str):
    """根据需求内容自动拆解任务 (SRS §3.2.1)"""
    try:
        from app.database import SessionLocal
        from app.services.decomposition_service import DecompositionService

        db = SessionLocal()
        service = DecompositionService(db)
        tasks = service.decompose(project_id, requirement_content)
        service.apply_priorities(tasks, project_id)
        db.close()
        return {
            "project_id": project_id,
            "tasks_count": len(tasks),
            "tasks": [{"title": t["title"], "type": t["type"], "priority": t["priority"]} for t in tasks],
        }
    except Exception as e:
        return {"error": str(e)}


# ═══════════════════════════════════════════════════════
# SRS §3.3 Agent 调度任务
# ═══════════════════════════════════════════════════════

@celery_app.task(bind=True, name="devflow_tasks.auto_assign_agent")
def auto_assign_agent(self, task_id: str, retry_count: int = 3):
    """自动匹配并分配 Agent (SRS §3.3.1)，失败时重试。"""
    try:
        from app.database import SessionLocal
        from app.services.agent_scheduler_service import AgentSchedulerService

        db = SessionLocal()
        scheduler = AgentSchedulerService(db)
        execution = scheduler.auto_assign(task_id)
        db.close()

        if execution:
            return {"task_id": task_id, "execution_id": execution.id, "status": "assigned"}
        elif retry_count > 0:
            self.retry(countdown=30, max_retries=retry_count)
        else:
            return {"task_id": task_id, "status": "no_agent_available"}
    except Exception as e:
        return {"error": str(e)}


# ═══════════════════════════════════════════════════════
# SRS §3.4 成果自动验收任务
# ═══════════════════════════════════════════════════════

@celery_app.task(bind=True, name="devflow_tasks.verify_delivery")
def verify_delivery(self, execution_id: str):
    """自动验收任务交付成果 (SRS §3.4.1)"""
    try:
        from app.database import SessionLocal
        from app.services.acceptance_service import AcceptanceService

        db = SessionLocal()
        acceptance = AcceptanceService(db)
        result = acceptance.verify_delivery(execution_id)
        db.close()
        return {
            "execution_id": execution_id,
            "result": result["result"],
            "checks_passed": all(c["passed"] for c in result["checks"].values()),
        }
    except Exception as e:
        return {"error": str(e)}


# ═══════════════════════════════════════════════════════
# SRS §3.5 通知推送任务
# ═══════════════════════════════════════════════════════

@celery_app.task(bind=True, name="devflow_tasks.send_project_notification")
def send_project_notification(self, user_id: str, project_id: str, title: str, content: str):
    """异步发送项目通知 (SRS §3.5.1)"""
    try:
        from app.database import SessionLocal
        from app.services.delivery_service import DeliveryService

        db = SessionLocal()
        delivery = DeliveryService(db)
        item = delivery.notify_progress(user_id, project_id, title, content)
        db.close()
        return {"notification_id": item.id, "sent": True}
    except Exception as e:
        return {"error": str(e)}


@celery_app.task(bind=True, name="devflow_tasks.finalize_project")
def finalize_project(self, project_id: str):
    """执行项目最终验收并完成 (SRS §3.4.2 + §3.5.2)"""
    try:
        from app.database import SessionLocal
        from app.services.acceptance_service import AcceptanceService
        from app.services.delivery_service import DeliveryService

        db = SessionLocal()
        acceptance = AcceptanceService(db)
        delivery = DeliveryService(db)

        final_result = acceptance.final_acceptance(project_id)
        if final_result["passed"]:
            report = delivery.complete_project(project_id)
            db.close()
            return {"project_id": project_id, "status": "completed", "report": report}
        else:
            db.close()
            return {
                "project_id": project_id,
                "status": "blocked",
                "pending": final_result["pending_tasks"],
                "rejected": final_result["rejected_tasks"],
            }
    except Exception as e:
        return {"error": str(e)}


@celery_app.task(bind=True, name="devflow_tasks.profile_scan_task")
def profile_scan_task(self):
    try:
        import asyncio
        from app.database import sync_session_maker
        from app.services.profile_sync import sync_profiles_to_db

        db = sync_session_maker()
        try:
            result = asyncio.run(sync_profiles_to_db(db))
            return result
        finally:
            db.close()
    except Exception as e:
        return {"error": str(e)}


@celery_app.task(bind=True, name="devflow_tasks.check_agent_health_task")
def check_agent_health_task(self):
    try:
        import asyncio
        from app.database import sync_session_maker
        from app.services.profile_sync import update_agent_online_status

        db = sync_session_maker()
        try:
            result = asyncio.run(update_agent_online_status(db))
            return result
        finally:
            db.close()
    except Exception as e:
        return {"error": str(e)}


@celery_app.task(bind=True, name="devflow_tasks.skill_discover_task")
def skill_discover_task(self):
    try:
        import asyncio
        from app.database import sync_session_maker
        from app.services.skill_scheduler import SkillSchedulerService

        db = sync_session_maker()
        try:
            service = SkillSchedulerService(db)
            result = asyncio.run(service.discover_coding_agents())
            return result
        finally:
            db.close()
    except Exception as e:
        return {"error": str(e)}
