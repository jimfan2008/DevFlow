"""严重级别告警通知范围 - TDD 测试用例

验证严重级别告警自动通知系统管理员和项目负责人
验收标准：
  1. 通知接收人包含系统管理员和项目负责人
  2. 通知在 ≤30 秒内送达
"""

import time
import uuid
from datetime import datetime, timezone
from typing import Optional, List
from enum import Enum

import pytest
from unittest.mock import MagicMock, patch

from pydantic import BaseModel, Field


# ============================================================
# 领域模型
# ============================================================

class AlertSeverity(str, Enum):
    """告警严重级别"""
    info = "info"
    warning = "warning"
    major = "major"
    critical = "critical"


class NotificationChannel(str, Enum):
    """通知通道"""
    platform = "platform"
    email = "email"
    sms = "sms"


class UserRole(str, Enum):
    system_admin = "system_admin"
    project_manager = "project_manager"
    developer = "developer"
    viewer = "viewer"


class User(BaseModel):
    id: str
    username: str
    email: str
    role: UserRole

    @classmethod
    def create_system_admin(cls):
        return cls(
            id=str(uuid.uuid4()),
            username="sys_admin",
            email="admin@example.com",
            role=UserRole.system_admin,
        )

    @classmethod
    def create_project_manager(cls):
        return cls(
            id=str(uuid.uuid4()),
            username="pm_001",
            email="pm@example.com",
            role=UserRole.project_manager,
        )


class Notification(BaseModel):
    id: str
    user_id: str
    alert_id: str
    title: str
    content: str
    channel: str = "platform"
    is_read: bool = False
    created_at: datetime

    @classmethod
    def create(cls, user_id: str, alert_id: str, title: str, content: str, channel: str = "platform"):
        return cls(
            id=str(uuid.uuid4()),
            user_id=user_id,
            alert_id=alert_id,
            title=title,
            content=content,
            channel=channel,
            is_read=False,
            created_at=datetime.now(timezone.utc),
        )


class Alert(BaseModel):
    id: str
    project_id: Optional[str] = None
    severity: AlertSeverity
    title: str
    message: str
    source: str = "system"
    created_at: datetime

    @classmethod
    def create(cls, severity: AlertSeverity, title: str, message: str, project_id: Optional[str] = None):
        return cls(
            id=str(uuid.uuid4()),
            project_id=project_id,
            severity=severity,
            title=title,
            message=message,
            source="system",
            created_at=datetime.now(timezone.utc),
        )


# ============================================================
# 内存存储
# ============================================================

class InMemoryStore:
    """内存存储，模拟数据库"""

    def __init__(self):
        self.users: dict[str, User] = {}
        self.alerts: dict[str, Alert] = {}
        self.notifications: dict[str, Notification] = {}

    def add_user(self, user: User):
        self.users[user.id] = user

    def add_alert(self, alert: Alert):
        self.alerts[alert.id] = alert

    def add_notification(self, notification: Notification):
        self.notifications[notification.id] = notification

    def get_user(self, user_id: str) -> Optional[User]:
        return self.users.get(user_id)

    def get_users_by_role(self, role: UserRole) -> List[User]:
        return [u for u in self.users.values() if u.role == role]

    def get_notifications_for_user(self, user_id: str) -> List[Notification]:
        return [n for n in self.notifications.values() if n.user_id == user_id]

    def get_all_notifications(self) -> List[Notification]:
        return list(self.notifications.values())

    def clear(self):
        self.users.clear()
        self.alerts.clear()
        self.notifications.clear()


# ============================================================
# 告警通知服务
# ============================================================

class AlertNotificationService:
    """
    告警通知服务：根据告警严重级别，自动路由通知给对应的接收人。

    路由规则：
      - critical（严重）：系统管理员 + 项目负责人
      - major（主要）：项目负责人
      - warning（警告）：项目负责人（仅平台通道）
      - info（信息）：不自动通知
    """

    _ROUTING_RULES: dict[AlertSeverity, tuple] = {
        AlertSeverity.critical: (
            UserRole.system_admin,
            UserRole.project_manager,
        ),
        AlertSeverity.major: (
            UserRole.project_manager,
        ),
        AlertSeverity.warning: (
            UserRole.project_manager,
        ),
        AlertSeverity.info: (),
    }

    _CHANNEL_RULES: dict[AlertSeverity, List[NotificationChannel]] = {
        AlertSeverity.critical: [NotificationChannel.platform, NotificationChannel.email, NotificationChannel.sms],
        AlertSeverity.major: [NotificationChannel.platform, NotificationChannel.email],
        AlertSeverity.warning: [NotificationChannel.platform],
        AlertSeverity.info: [],
    }

    def __init__(self, store: InMemoryStore):
        self.store = store

    def dispatch_alert(self, alert: Alert) -> List[Notification]:
        """
        根据告警严重级别分发通知。
        返回生成的通知列表。
        """
        self.store.add_alert(alert)

        target_roles = self._ROUTING_RULES.get(alert.severity, ())
        channels = self._CHANNEL_RULES.get(alert.severity, [])

        if not target_roles or not channels:
            return []

        notifications = []
        for role in target_roles:
            users = self.store.get_users_by_role(role)
            for user in users:
                for channel in channels:
                    title = self._build_title(alert, role)
                    content = self._build_content(alert)
                    notification = Notification.create(
                        user_id=user.id,
                        alert_id=alert.id,
                        title=title,
                        content=content,
                        channel=channel.value,
                    )
                    self.store.add_notification(notification)
                    notifications.append(notification)

        return notifications

    def _build_title(self, alert: Alert, role: UserRole) -> str:
        role_label = "系统管理员" if role == UserRole.system_admin else "项目负责人"
        severity_label = {
            AlertSeverity.critical: "【严重】",
            AlertSeverity.major: "【主要】",
            AlertSeverity.warning: "【警告】",
            AlertSeverity.info: "【信息】",
        }.get(alert.severity, "")
        return f"[通知-{role_label}] {severity_label}{alert.title}"

    def _build_content(self, alert: Alert) -> str:
        return f"告警内容：{alert.message}"


# ============================================================
# Fixtures
# ============================================================

@pytest.fixture
def store():
    """每次测试前创建干净的存储"""
    s = InMemoryStore()
    yield s
    s.clear()


@pytest.fixture
def sys_admin(store):
    """创建系统管理员"""
    user = User.create_system_admin()
    store.add_user(user)
    return user


@pytest.fixture
def project_manager(store):
    """创建项目负责人"""
    user = User.create_project_manager()
    store.add_user(user)
    return user


@pytest.fixture
def service(store):
    """创建告警通知服务"""
    return AlertNotificationService(store)


@pytest.fixture
def critical_alert():
    """创建严重级别告警"""
    return Alert.create(
        severity=AlertSeverity.critical,
        title="数据库连接池耗尽",
        message="主数据库连接池已耗尽，当前活跃连接数: 200/200",
        project_id="proj-001",
    )


# ============================================================
# 测试用例
# ============================================================

class TestCriticalAlertNotifications:
    """严重级别告警通知范围"""

    def test_critical_alert_notifies_system_admin(self, service, sys_admin, critical_alert):
        """严重级别告警 → 系统管理员收到通知"""
        notifications = service.dispatch_alert(critical_alert)

        admin_notifications = [n for n in notifications if n.user_id == sys_admin.id]
        assert len(admin_notifications) > 0, "系统管理员未收到任何通知"

        for n in admin_notifications:
            assert n.alert_id == critical_alert.id
            assert "系统管理员" in n.title
            assert critical_alert.title in n.title

    def test_critical_alert_notifies_project_manager(self, service, project_manager, critical_alert):
        """严重级别告警 → 项目负责人收到通知"""
        notifications = service.dispatch_alert(critical_alert)

        pm_notifications = [n for n in notifications if n.user_id == project_manager.id]
        assert len(pm_notifications) > 0, "项目负责人未收到任何通知"

        for n in pm_notifications:
            assert n.alert_id == critical_alert.id
            assert "项目负责人" in n.title
            assert critical_alert.title in n.title

    def test_critical_alert_recipients_include_both_roles(self, service, sys_admin, project_manager, critical_alert):
        """验收标准 1：通知接收人包含系统管理员和项目负责人"""
        notifications = service.dispatch_alert(critical_alert)

        recipient_ids = set(n.user_id for n in notifications)
        assert sys_admin.id in recipient_ids, "通知接收人中缺少系统管理员"
        assert project_manager.id in recipient_ids, "通知接收人中缺少项目负责人"

    def test_critical_alert_delivery_within_30_seconds(self, service, sys_admin, project_manager, critical_alert):
        """验收标准 2：通知在 ≤30 秒内送达"""
        start = time.monotonic()
        notifications = service.dispatch_alert(critical_alert)
        elapsed_seconds = time.monotonic() - start

        assert elapsed_seconds <= 30.0, f"通知分发耗时 {elapsed_seconds:.3f} 秒，超过 30 秒上限"
        assert len(notifications) > 0, "未生成任何通知"

    def test_critical_alert_uses_all_channels(self, service, sys_admin, critical_alert):
        """严重级别告警 → 使用所有通知通道（平台 + 邮件 + 短信）"""
        notifications = service.dispatch_alert(critical_alert)

        admin_notifications = [n for n in notifications if n.user_id == sys_admin.id]
        channels = set(n.channel for n in admin_notifications)

        assert NotificationChannel.platform.value in channels
        assert NotificationChannel.email.value in channels
        assert NotificationChannel.sms.value in channels

    def test_critical_alert_contains_alert_message(self, service, sys_admin, project_manager, critical_alert):
        """严重级别告警 → 通知内容包含告警详情"""
        notifications = service.dispatch_alert(critical_alert)

        for n in notifications:
            assert critical_alert.message in n.content, "通知内容缺少告警详情"

    def test_critical_alert_marked_as_unread(self, service, sys_admin, critical_alert):
        """严重级别告警 → 通知默认为未读"""
        notifications = service.dispatch_alert(critical_alert)

        for n in notifications:
            assert n.is_read is False

    def test_critical_alert_has_timestamp(self, service, sys_admin, critical_alert):
        """严重级别告警 → 通知带有创建时间戳"""
        notifications = service.dispatch_alert(critical_alert)

        for n in notifications:
            assert n.created_at is not None
            assert n.created_at.tzinfo is not None

    def test_critical_alert_with_multiple_admins(self, store, service, project_manager, critical_alert):
        """多个系统管理员 → 每个都收到通知"""
        admin1 = User.create_system_admin()
        admin2 = User.create_system_admin()
        store.add_user(admin1)
        store.add_user(admin2)

        notifications = service.dispatch_alert(critical_alert)

        admin1_notifs = [n for n in notifications if n.user_id == admin1.id]
        admin2_notifs = [n for n in notifications if n.user_id == admin2.id]

        assert len(admin1_notifs) > 0, "第一个系统管理员未收到通知"
        assert len(admin2_notifs) > 0, "第二个系统管理员未收到通知"

    def test_critical_alert_notification_has_severity_label(self, service, sys_admin, critical_alert):
        """严重级别告警 → 通知标题包含严重级别标记"""
        notifications = service.dispatch_alert(critical_alert)

        admin_notifications = [n for n in notifications if n.user_id == sys_admin.id]
        for n in admin_notifications:
            assert "严重" in n.title, f"通知标题缺少严重级别标记: {n.title}"


class TestNonCriticalAlertNotifications:
    """非严重级别告警不应通知系统管理员"""

    def test_major_alert_notifies_only_project_manager(self, store, service, sys_admin, project_manager):
        """主要级别告警 → 只通知项目负责人，不通知系统管理员"""
        alert = Alert.create(
            severity=AlertSeverity.major,
            title="CPU 使用率过高",
            message="CPU 使用率达到 90%",
        )

        notifications = service.dispatch_alert(alert)
        recipient_ids = set(n.user_id for n in notifications)

        assert project_manager.id in recipient_ids
        assert sys_admin.id not in recipient_ids

    def test_warning_alert_notifies_only_project_manager(self, store, service, sys_admin, project_manager):
        """警告级别告警 → 只通知项目负责人，不通知系统管理员"""
        alert = Alert.create(
            severity=AlertSeverity.warning,
            title="磁盘空间不足",
            message="磁盘剩余空间低于 20%",
        )

        notifications = service.dispatch_alert(alert)
        recipient_ids = set(n.user_id for n in notifications)

        assert project_manager.id in recipient_ids
        assert sys_admin.id not in recipient_ids

    def test_info_alert_no_auto_notification(self, store, service, sys_admin, project_manager):
        """信息级别告警 → 不自动发送通知"""
        alert = Alert.create(
            severity=AlertSeverity.info,
            title="系统状态正常",
            message="所有服务运行正常",
        )

        notifications = service.dispatch_alert(alert)
        assert len(notifications) == 0

    def test_major_alert_uses_platform_and_email(self, store, service, project_manager):
        """主要级别告警 → 使用平台 + 邮件通道"""
        alert = Alert.create(
            severity=AlertSeverity.major,
            title="内存使用率过高",
            message="内存使用率达到 85%",
        )

        notifications = service.dispatch_alert(alert)
        pm_notifications = [n for n in notifications if n.user_id == project_manager.id]
        channels = set(n.channel for n in pm_notifications)

        assert NotificationChannel.platform.value in channels
        assert NotificationChannel.email.value in channels
        assert NotificationChannel.sms.value not in channels


class TestPerformance:
    """性能测试"""

    def test_dispatch_100_critical_alerts_within_30_seconds(self, store, service, sys_admin, project_manager):
        """批量分发 100 条严重告警，总耗时 ≤ 30 秒"""
        start = time.monotonic()

        total_notifications = 0
        for i in range(100):
            alert = Alert.create(
                severity=AlertSeverity.critical,
                title=f"告警-{i}",
                message=f"第 {i} 条严重告警",
            )
            notifications = service.dispatch_alert(alert)
            total_notifications += len(notifications)

        elapsed_seconds = time.monotonic() - start
        assert elapsed_seconds <= 30.0, f"100 条告警分发耗时 {elapsed_seconds:.3f} 秒，超过 30 秒"
        assert total_notifications >= 200, f"预期至少 200 条通知，实际 {total_notifications}"  # 100 alerts × 2 roles × min 1 channel


class TestEdgeCases:
    """边界情况"""

    def test_critical_alert_no_matching_users(self, store, service):
        """严重级别告警 → 没有匹配的用户 → 不报错，返回空列表"""
        alert = Alert.create(
            severity=AlertSeverity.critical,
            title="服务宕机",
            message="核心服务无响应",
        )

        notifications = service.dispatch_alert(alert)
        assert len(notifications) == 0

    def test_critical_alert_still_created_in_store(self, store, service):
        """严重级别告警 → 即使没有匹配用户，告警仍被存入存储"""
        alert = Alert.create(
            severity=AlertSeverity.critical,
            title="测试告警",
            message="测试内容",
        )

        service.dispatch_alert(alert)
        assert alert.id in store.alerts


if __name__ == "__main__":
    pytest.main([__file__, "-v"])
