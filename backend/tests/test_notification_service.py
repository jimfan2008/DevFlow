"""v4.0 Notification Service Tests - 通知与交付（SRS 3.8）"""
import pytest
import uuid
from datetime import datetime, timezone
from app.services.notification_service import NotificationService
from app.models.notification import Notification
from app.models.user import User
from app.models.enums import NotificationChannel
from app.utils.security import get_password_hash


class TestNotificationCreate:
    """通知创建测试"""

    def test_create_notification_success(self, db_session):
        user = User(id=str(uuid.uuid4()), username="test", email="test@test.com",
                    password_hash=get_password_hash("test123"))
        db_session.add(user)
        db_session.commit()

        svc = NotificationService(db_session)
        n = svc.create_notification(
            user_id=user.id, type="progress", title="项目进展",
            content="Step 3 已完成", project_id="proj-1",
        )
        assert n.title == "项目进展"
        assert n.content == "Step 3 已完成"
        assert n.type == "progress"
        assert n.is_read is False
        assert n.channel == "platform"

    def test_create_notification_default_channel(self, db_session):
        user = User(id=str(uuid.uuid4()), username="test2", email="test2@test.com",
                    password_hash=get_password_hash("test123"))
        db_session.add(user)
        db_session.commit()

        svc = NotificationService(db_session)
        n = svc.create_notification(
            user_id=user.id, type="complete", title="完成",
            content="项目完成",
        )
        assert n.channel == "platform"

    def test_create_notification_without_project(self, db_session):
        user = User(id=str(uuid.uuid4()), username="test3", email="test3@test.com",
                    password_hash=get_password_hash("test123"))
        db_session.add(user)
        db_session.commit()

        svc = NotificationService(db_session)
        n = svc.create_notification(
            user_id=user.id, type="error", title="错误",
            content="部署失败",
        )
        assert n.project_id is None

    def test_notification_has_timestamp(self, db_session):
        user = User(id=str(uuid.uuid4()), username="test4", email="test4@test.com",
                    password_hash=get_password_hash("test123"))
        db_session.add(user)
        db_session.commit()

        svc = NotificationService(db_session)
        n = svc.create_notification(user.id, "info", "测试", "内容")
        assert n.created_at is not None


class TestNotificationMultiChannel:
    """多渠道通知测试"""

    def test_send_multi_channel_platform_only(self, db_session):
        user = User(id=str(uuid.uuid4()), username="multi1", email="m1@test.com",
                    password_hash=get_password_hash("test123"))
        db_session.add(user)
        db_session.commit()

        svc = NotificationService(db_session)
        results = svc.send_multi_channel(
            user_id=user.id, type="progress", title="测试",
            content="多渠道测试",
            channels=["platform"],
        )
        assert len(results) == 1
        assert results[0].channel == "platform"

    def test_send_multi_channel_all_channels(self, db_session):
        user = User(id=str(uuid.uuid4()), username="multi2", email="m2@test.com",
                    password_hash=get_password_hash("test123"))
        db_session.add(user)
        db_session.commit()

        svc = NotificationService(db_session)
        results = svc.send_multi_channel(
            user_id=user.id, type="complete", title="完成",
            content="项目已部署",
            channels=["platform", "email"],
        )
        assert len(results) == 2
        channels = [n.channel for n in results]
        assert "platform" in channels
        assert "email" in channels

    def test_send_multi_channel_default_to_platform(self, db_session):
        user = User(id=str(uuid.uuid4()), username="multi3", email="m3@test.com",
                    password_hash=get_password_hash("test123"))
        db_session.add(user)
        db_session.commit()

        svc = NotificationService(db_session)
        results = svc.send_multi_channel(
            user_id=user.id, type="info", title="信息",
            content="默认通道",
        )
        assert len(results) == 1
        assert results[0].channel == "platform"

    def test_send_multi_channel_with_project(self, db_session):
        user = User(id=str(uuid.uuid4()), username="multi4", email="m4@test.com",
                    password_hash=get_password_hash("test123"))
        db_session.add(user)
        db_session.commit()

        svc = NotificationService(db_session)
        results = svc.send_multi_channel(
            user_id=user.id, type="error", title="错误",
            content="部署失败", project_id="proj-1",
            channels=["platform", "email"],
        )
        for n in results:
            assert n.project_id == "proj-1"


class TestNotificationProjectLifecycle:
    """项目生命周期通知测试"""

    def test_notify_requirement_confirmed(self, db_session):
        user = User(id=str(uuid.uuid4()), username="life1", email="l1@test.com",
                    password_hash=get_password_hash("test123"))
        db_session.add(user)
        db_session.commit()

        svc = NotificationService(db_session)
        results = svc.notify_requirement_confirmed(
            project_id="proj-1", user_id=user.id, project_name="电商平台",
        )
        assert len(results) >= 1
        n = results[0]
        assert n.type == "requirement_confirmed"
        assert "电商平台" in n.title

    def test_notify_task_decomposed(self, db_session):
        user = User(id=str(uuid.uuid4()), username="life2", email="l2@test.com",
                    password_hash=get_password_hash("test123"))
        db_session.add(user)
        db_session.commit()

        svc = NotificationService(db_session)
        results = svc.notify_task_decomposed(
            project_id="proj-1", user_id=user.id, task_count=6,
        )
        assert len(results) >= 1
        assert "6" in results[0].content

    def test_notify_task_assigned(self, db_session):
        user = User(id=str(uuid.uuid4()), username="life3", email="l3@test.com",
                    password_hash=get_password_hash("test123"))
        db_session.add(user)
        db_session.commit()

        svc = NotificationService(db_session)
        n = svc.notify_task_assigned(
            task_id="task-1", agent_name="后发", task_name="用户模块编码",
            user_id=user.id, project_id="proj-1",
        )
        assert n.type == "task_assigned"
        assert "后发" in n.content
        assert "用户模块" in n.content

    def test_notify_task_completed(self, db_session):
        user = User(id=str(uuid.uuid4()), username="life4", email="l4@test.com",
                    password_hash=get_password_hash("test123"))
        db_session.add(user)
        db_session.commit()

        svc = NotificationService(db_session)
        n = svc.create_notification(
            user_id=user.id, type="task_completed", title="任务完成: 用户模块",
            content="任务 '用户模块' 已完成", project_id="proj-1",
        )
        assert n.type == "task_completed"
        assert "完成" in n.content

    def test_notify_project_completed(self, db_session):
        user = User(id=str(uuid.uuid4()), username="life5", email="l5@test.com",
                    password_hash=get_password_hash("test123"))
        db_session.add(user)
        db_session.commit()

        svc = NotificationService(db_session)
        results = svc.notify_project_completed(
            project_id="proj-1", user_id=user.id, project_name="电商平台",
        )
        assert len(results) >= 1
        n = results[0]
        assert n.type == "project_completed"

    def test_notify_error(self, db_session):
        user = User(id=str(uuid.uuid4()), username="life6", email="l6@test.com",
                    password_hash=get_password_hash("test123"))
        db_session.add(user)
        db_session.commit()

        svc = NotificationService(db_session)
        n = svc.create_notification(
            user_id=user.id, type="deploy_failed", title="部署失败",
            content="错误: 数据库连接超时", project_id="proj-1",
        )
        assert n.type == "deploy_failed"
        assert "数据库" in n.content


class TestNotificationReadStatus:
    """通知已读状态测试"""

    def test_new_notification_unread(self, db_session):
        user = User(id=str(uuid.uuid4()), username="read1", email="r1@test.com",
                    password_hash=get_password_hash("test123"))
        db_session.add(user)
        db_session.commit()

        svc = NotificationService(db_session)
        n = svc.create_notification(user.id, "info", "测试", "内容")
        assert n.is_read is False

    def test_mark_as_read(self, db_session):
        user = User(id=str(uuid.uuid4()), username="read2", email="r2@test.com",
                    password_hash=get_password_hash("test123"))
        db_session.add(user)
        db_session.commit()

        svc = NotificationService(db_session)
        n = svc.create_notification(user.id, "info", "测试", "内容")
        marked = svc.mark_as_read(n.id)
        assert marked.is_read is True

    def test_mark_as_read_not_found(self, db_session):
        svc = NotificationService(db_session)
        result = svc.mark_as_read("nonexistent")
        assert result is None

    def test_get_unread_count(self, db_session):
        user = User(id=str(uuid.uuid4()), username="read3", email="r3@test.com",
                    password_hash=get_password_hash("test123"))
        db_session.add(user)
        db_session.commit()

        svc = NotificationService(db_session)
        svc.create_notification(user.id, "info", "n1", "c1")
        svc.create_notification(user.id, "progress", "n2", "c2")

        count = svc.get_unread_count(user.id)
        assert count == 2

        all_n = db_session.query(Notification).filter(
            Notification.user_id == user.id
        ).all()
        all_n[0].is_read = True
        db_session.commit()

        count_after = svc.get_unread_count(user.id)
        assert count_after == 1

    def test_get_user_notifications(self, db_session):
        user = User(id=str(uuid.uuid4()), username="read4", email="r4@test.com",
                    password_hash=get_password_hash("test123"))
        db_session.add(user)
        db_session.commit()

        svc = NotificationService(db_session)
        svc.create_notification(user.id, "info", "通知1", "内容1")
        svc.create_notification(user.id, "progress", "通知2", "内容2")

        all_n = svc.get_notifications(user.id)
        assert len(all_n) == 2

    def test_get_notifications_filter_by_read(self, db_session):
        user = User(id=str(uuid.uuid4()), username="read5", email="r5@test.com",
                    password_hash=get_password_hash("test123"))
        db_session.add(user)
        db_session.commit()

        svc = NotificationService(db_session)
        svc.create_notification(user.id, "info", "n1", "c1")
        n2 = svc.create_notification(user.id, "progress", "n2", "c2")
        svc.mark_as_read(n2.id)

        unread = svc.get_notifications(user.id, is_read=False)
        assert len(unread) == 1

        read = svc.get_notifications(user.id, is_read=True)
        assert len(read) == 1

    def test_get_notifications_filter_by_project(self, db_session):
        user = User(id=str(uuid.uuid4()), username="read6", email="r6@test.com",
                    password_hash=get_password_hash("test123"))
        db_session.add(user)
        db_session.commit()

        svc = NotificationService(db_session)
        svc.create_notification(user.id, "info", "n1", "c1", project_id="proj-a")
        svc.create_notification(user.id, "progress", "n2", "c2", project_id="proj-b")

        filtered = svc.get_notifications(user.id, project_id="proj-a")
        assert len(filtered) == 1

    def test_mark_all_as_read(self, db_session):
        user = User(id=str(uuid.uuid4()), username="read7", email="r7@test.com",
                    password_hash=get_password_hash("test123"))
        db_session.add(user)
        db_session.commit()

        svc = NotificationService(db_session)
        svc.create_notification(user.id, "info", "n1", "c1")
        svc.create_notification(user.id, "progress", "n2", "c2")
        svc.create_notification(user.id, "error", "n3", "c3")

        count = svc.mark_all_as_read(user.id)
        assert count == 3

        unread = svc.get_unread_count(user.id)
        assert unread == 0
