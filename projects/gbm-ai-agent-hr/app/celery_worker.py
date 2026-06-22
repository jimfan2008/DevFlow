"""
GBM AI Agent HR - Celery 异步任务配置
"""
import os
from datetime import timedelta
from celery import Celery
from celery.schedules import crontab

# 从环境变量读取配置
broker_url = os.getenv(
    "CELERY_BROKER_URL",
    "amqp://guest:guest@rabbitmq:5672//",
)
result_backend = os.getenv(
    "CELERY_RESULT_BACKEND",
    "redis://:redis_password_dev@redis:6379/1",
)

# 创建 Celery 应用
celery_app = Celery(
    "gbm_hr",
    broker=broker_url,
    backend=result_backend,
)

# Celery 配置
celery_app.conf.update(
    # 任务序列化
    task_serializer="json",
    accept_content=["json"],
    result_serializer="json",

    # 时区
    timezone="Asia/Shanghai",
    enable_utc=True,

    # 并发配置
    worker_concurrency=4,
    worker_prefetch_multiplier=1,

    # 任务超时
    task_time_limit=300,        # 硬超时 5 分钟
    task_soft_time_limit=240,   # 软超时 4 分钟

    # 重试策略
    task_acks_late=True,
    task_reject_on_worker_lost=True,

    # 结果过期
    result_expires=3600,

    # 任务路由
    task_routes={
        "app.agent.recruitment.*": {"queue": "recruitment"},
        "app.agent.onboarding.*": {"queue": "onboarding"},
        "app.agent.training.*": {"queue": "training"},
        "app.agent.attendance.*": {"queue": "attendance"},
        "app.agent.payroll.*": {"queue": "payroll"},
        "app.agent.performance.*": {"queue": "performance"},
        "app.agent.rpa.*": {"queue": "rpa"},
        "app.agent.ocr.*": {"queue": "ocr"},
    },

    # Beat 定时任务调度
    beat_schedule={
        # 简历自动抓取 - 每 15 分钟
        "resume-fetch": {
            "task": "app.agent.recruitment.fetch_resumes",
            "schedule": timedelta(minutes=15),
        },
        # 薪资核算 - 每月 25 日凌晨 2:00
        "payroll-calculation": {
            "task": "app.agent.payroll.calculate_monthly_payroll",
            "schedule": crontab(hour=2, minute=0, day_of_month=25),
        },
        # 证书到期检查 - 每天早上 8:00
        "certificate-expiry-check": {
            "task": "app.agent.certificate.check_expiry",
            "schedule": crontab(hour=8, minute=0),
        },
        # 考勤数据同步 - 每小时
        "attendance-sync": {
            "task": "app.agent.attendance.sync_attendance_data",
            "schedule": timedelta(hours=1),
        },
        # 简历定期评分 - 每 30 分钟
        "resume-scoring": {
            "task": "app.agent.recruitment.score_pending_resumes",
            "schedule": timedelta(minutes=30),
        },
        # 试用期到期提醒 - 每天 9:00
        "probation-reminder": {
            "task": "app.agent.onboarding.check_probation_expiry",
            "schedule": crontab(hour=9, minute=0),
        },
        # 工资条发送 - 每月 28 日 10:00
        "payslip-send": {
            "task": "app.agent.payroll.send_payslips",
            "schedule": crontab(hour=10, minute=0, day_of_month=28),
        },
        # 培训签到统计 - 每 10 分钟
        "training-checkin-stats": {
            "task": "app.agent.training.update_checkin_stats",
            "schedule": timedelta(minutes=10),
        },
        # 日报生成 - 每天 18:00
        "daily-report": {
            "task": "app.services.notification_service.generate_daily_report",
            "schedule": crontab(hour=18, minute=0),
        },
        # 数据备份检查 - 每周日凌晨 3:00
        "backup-check": {
            "task": "app.services.audit_service.check_backup_status",
            "schedule": crontab(hour=3, minute=0, day_of_week=0),
        },
    },
)

# 自动发现任务
celery_app.autodiscover_tasks(
    ["app.agent", "app.services"],
    related_name="tasks",
)
