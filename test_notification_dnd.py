"""通知免打扰时段 — TDD 测试用例

验证免打扰时段仅 CRITICAL 级别告警可中断
验收标准：
  1. WARNING 级别不发送通知
  2. CRITICAL 级别正常发送通知
  3. 用户可在个人设置中管理免打扰时段
"""

import uuid
from datetime import datetime, timezone, time as dtime, timedelta
from typing import Optional, List
from enum import Enum

import pytest
from pydantic import BaseModel


# ============================================================
# 领域模型
# ============================================================

class AlertSeverity(str, Enum):
    """告警严重级别"""
    INFO = "info"
    WARNING = "warning"
    CRITICAL = "critical"


class NotificationChannel(str, Enum):
    """通知通道"""
    platform = "platform"
    email = "email"
    sms = "sms"


class DNSSchedule(BaseModel):
    """免打扰时段设置"""
    user_id: str
    enabled: bool = False
    start_time: Optional[dtime] = None
    end_time: Optional[dtime] = None
    timezone_name: str = "Asia/Shanghai"

    def is_active_at(self, moment: datetime) -> bool:
        """判断给定时间点是否处于免打扰时段内。
        支持跨天设置（如 22:00 ~ 08:00）。"""
        if not self.enabled:
            return False
        if self.start_time is None or self.end_time is None:
            return False
        current_time = moment.time()
        start = self.start_time
        end = self.end_time
        if start < end:
            # 普通时段，如 22:00 ~ 23:00
            return start <= current_time < end
        else:
            # 跨天时段，如 22:00 ~ 08:00
            return current_time >= start or current_time < end


class Alert(BaseModel):
    """告警"""
    id: str
    severity: AlertSeverity
    title: str
    message: str
    project_id: Optional[str] = None
    created_at: datetime

    @classmethod
    def create(cls, severity: AlertSeverity, title: str, message: str, project_id: Optional[str] = None) -> "Alert":
        return cls(
            id=str(uuid.uuid4()),
            severity=severity,
            title=title,
            message=message,
            project_id=project_id,
            created_at=datetime.now(timezone.utc),
        )


class Notification(BaseModel):
    """通知"""
    id: str
    user_id: str
    alert_id: str
    severity: AlertSeverity
    title: str
    content: str
    channel: str
    is_read: bool = False
    sent_at: Optional[datetime] = None
    created_at: datetime

    @classmethod
    def create(cls, user_id: str, alert: "Alert", channel: str = "platform") -> "Notification":
        return cls(
            id=str(uuid.uuid4()),
            user_id=user_id,
            alert_id=alert.id,
            severity=alert.severity,
            title=alert.title,
            content=alert.message,
            channel=channel,
            is_read=False,
            sent_at=datetime.now(timezone.utc),
            created_at=datetime.now(timezone.utc),
        )


class UserSettings(BaseModel):
    """用户个人设置"""
    user_id: str
    username: str
    dnd_schedule: DNSSchedule

    @classmethod
    def create(cls, user_id: str, username: str, dnd_enabled: bool = False, dnd_start: Optional[dtime] = None, dnd_end: Optional[dtime] = None) -> "UserSettings":
        return cls(
            user_id=user_id,
            username=username,
            dnd_schedule=DNSSchedule(
                user_id=user_id,
                enabled=dnd_enabled,
                start_time=dnd_start,
                end_time=dnd_end,
            ),
        )





# ============================================================
# 内存存储
# ============================================================

class InMemoryStore:
    """内存存储，模拟数据库"""

    def __init__(self):
        self.users: dict[str, UserSettings] = {}
        self.alerts: dict[str, Alert] = {}
        self.notifications: dict[str, Notification] = {}
        self.suppressed_alerts: List[dict] = []  # 被免打扰拦截的告警

    def add_user(self, user: UserSettings):
        self.users[user.user_id] = user

    def get_user(self, user_id: str) -> Optional[UserSettings]:
        return self.users.get(user_id)

    def update_dnd_schedule(self, user_id: str, enabled: bool, start_time: Optional[dtime], end_time: Optional[dtime]) -> Optional[UserSettings]:
        user = self.users.get(user_id)
        if not user:
            return None
        user.dnd_schedule.enabled = enabled
        user.dnd_schedule.start_time = start_time
        user.dnd_schedule.end_time = end_time
        self.db_commit()
        return user

    def add_alert(self, alert: Alert):
        self.alerts[alert.id] = alert

    def add_notification(self, notification: Notification):
        self.notifications[notification.id] = notification

    def add_suppressed(self, record: dict):
        self.suppressed_alerts.append(record)

    def get_notifications_for_user(self, user_id: str) -> List[Notification]:
        return [n for n in self.notifications.values() if n.user_id == user_id]

    def get_all_notifications(self) -> List[Notification]:
        return list(self.notifications.values())

    def get_suppressed_count(self) -> int:
        return len(self.suppressed_alerts)

    def clear(self):
        self.users.clear()
        self.alerts.clear()
        self.notifications.clear()
        self.suppressed_alerts.clear()


# ============================================================
# 通知服务
# ============================================================

class NotificationService:
    """
    通知服务：根据用户的免打扰设置和告警严重级别，
    决定是否可以发送通知。

    核心规则：
      - 非免打扰时段：所有级别正常发送
      - 免打扰时段：仅 CRITICAL 级别可中断发送
      - 免打扰时段：INFO / WARNING 级别被拦截，记录但不发送
    """

    DND_BYPASS_SEVERITIES = {AlertSeverity.CRITICAL}

    def __init__(self, store: InMemoryStore):
        self.store = store

    def send_alert_notification(self, user_id: str, alert: Alert, channel: str = "platform") -> Optional[Notification]:
        """
        尝试发送告警通知。
        如果命中免打扰且不是 CRITICAL 级别，则返回 None（被拦截）。
        否则创建通知并返回。
        """
        self.store.add_alert(alert)

        user = self.store.get_user(user_id)
        if user is None:
            # 用户不存在，不发送
            return None

        if self._is_suppressed_by_dnd(user.dnd_schedule, alert.severity):
            # 被免打扰拦截
            self.store.add_suppressed({
                "alert_id": alert.id,
                "user_id": user_id,
                "severity": alert.severity.value,
                "reason": "dnd_active_non_critical",
            })
            return None

        notification = Notification.create(user_id=user_id, alert=alert, channel=channel)
        self.store.add_notification(notification)
        return notification

    def send_alert_multi_channel(self, user_id: str, alert: Alert, channels: List[str] = None) -> List[Notification]:
        """多渠道发送告警通知"""
        if channels is None:
            channels = [NotificationChannel.platform.value]

        results = []
        for ch in channels:
            n = self.send_alert_notification(user_id, alert, channel=ch)
            if n:
                results.append(n)
        return results

    @staticmethod
    def _is_suppressed_by_dnd(schedule: DNSSchedule, severity: AlertSeverity) -> bool:
        """判断该告警在免打扰时段是否被拦截"""
        if not schedule.enabled:
            return False
        if schedule.start_time is None or schedule.end_time is None:
            return False
        # CRITICAL 永远可中断免打扰
        if severity in NotificationService.DND_BYPASS_SEVERITIES:
            return False
        return True  # WARNING / INFO 被拦截


class DNDAwareNotificationService(NotificationService):
    """
    时间感知的免打扰通知服务。
    在父类基础上增加「当前时间是否在免打扰时段」的判断。
    """

    def __init__(self, store: InMemoryStore, current_time: Optional[datetime] = None):
        super().__init__(store)
        self._current_time = current_time  # 用于测试注入时间

    def send_alert_notification(self, user_id: str, alert: Alert, channel: str = "platform") -> Optional[Notification]:
        """重写：加入时间判断"""
        self.store.add_alert(alert)

        user = self.store.get_user(user_id)
        if user is None:
            return None

        now = self._current_time or datetime.now(timezone.utc)

        if user.dnd_schedule.is_active_at(now):
            # 当前在免打扰时段
            if self._is_suppressed_by_dnd(user.dnd_schedule, alert.severity):
                self.store.add_suppressed({
                    "alert_id": alert.id,
                    "user_id": user_id,
                    "severity": alert.severity.value,
                    "reason": "dnd_active_non_critical",
                })
                return None

        notification = Notification.create(user_id=user_id, alert=alert, channel=channel)
        self.store.add_notification(notification)
        return notification

    def send_alert_multi_channel(self, user_id: str, alert: Alert, channels: List[str] = None) -> List[Notification]:
        if channels is None:
            channels = [NotificationChannel.platform.value]
        results = []
        for ch in channels:
            n = self.send_alert_notification(user_id, alert, channel=ch)
            if n:
                results.append(n)
        return results


# ============================================================
# 用户设置管理服务
# ============================================================

class UserSettingsService:
    """用户个人设置管理：免打扰时段 CRUD"""

    def __init__(self, store: InMemoryStore):
        self.store = store

    def get_dnd_schedule(self, user_id: str) -> Optional[DNSSchedule]:
        """获取用户的免打扰时段设置"""
        user = self.store.get_user(user_id)
        if not user:
            return None
        return user.dnd_schedule

    def set_dnd_schedule(self, user_id: str, enabled: bool, start_time: Optional[dtime], end_time: Optional[dtime]) -> Optional[DNSSchedule]:
        """设置/更新免打扰时段"""
        user = self.store.get_user(user_id)
        if not user:
            return None
        user.dnd_schedule.enabled = enabled
        user.dnd_schedule.start_time = start_time
        user.dnd_schedule.end_time = end_time
        return user.dnd_schedule

    def disable_dnd(self, user_id: str) -> bool:
        """关闭免打扰"""
        return self.set_dnd_schedule(user_id, False, None, None) is not None

    def enable_dnd(self, user_id: str, start_time: dtime, end_time: dtime) -> bool:
        """开启免打扰时段"""
        return self.set_dnd_schedule(user_id, True, start_time, end_time) is not None


# ============================================================
# Fixtures
# ============================================================

@pytest.fixture
def store():
    s = InMemoryStore()
    yield s
    s.clear()


@pytest.fixture
def user_a(store):
    user = UserSettings.create(user_id="user-001", username="alice", dnd_enabled=False)
    store.add_user(user)
    return user


@pytest.fixture
def notification_service(store):
    return NotificationService(store)


@pytest.fixture
def user_settings_service(store):
    return UserSettingsService(store)


@pytest.fixture
def warning_alert():
    return Alert.create(
        severity=AlertSeverity.WARNING,
        title="磁盘空间不足",
        message="磁盘 /dev/sda1 剩余空间低于 20%",
        project_id="proj-001",
    )


@pytest.fixture
def critical_alert():
    return Alert.create(
        severity=AlertSeverity.CRITICAL,
        title="数据库连接池耗尽",
        message="主数据库连接池已耗尽，活跃连接数: 200/200",
        project_id="proj-001",
    )


@pytest.fixture
def info_alert():
    return Alert.create(
        severity=AlertSeverity.INFO,
        title="系统状态正常",
        message="所有服务运行正常",
    )


# ============================================================
# 测试：WARNING 级别在免打扰时段不发送通知
# ============================================================

class TestWarningSuppressedDuringDND:
    """验收标准 1：WARNING 级别不发送通知（免打扰时段内）"""

    def test_warning_not_sent_when_dnd_enabled(self, store, notification_service, user_a, warning_alert):
        """用户免打扰已开启 → WARNING 告警被拦截，不产生通知"""
        user_a.dnd_schedule.enabled = True
        user_a.dnd_schedule.start_time = dtime(22, 0)
        user_a.dnd_schedule.end_time = dtime(8, 0)

        result = notification_service.send_alert_notification(user_a.user_id, warning_alert)

        assert result is None, "WARNING 级别在免打扰期间不应发送通知"

    def test_warning_suppressed_recorded(self, store, notification_service, user_a, warning_alert):
        """用户免打扰已开启 → WARNING 告警被拦截，记录到 suppressed 列表"""
        user_a.dnd_schedule.enabled = True
        user_a.dnd_schedule.start_time = dtime(22, 0)
        user_a.dnd_schedule.end_time = dtime(8, 0)

        notification_service.send_alert_notification(user_a.user_id, warning_alert)

        assert store.get_suppressed_count() == 1
        record = store.suppressed_alerts[0]
        assert record["severity"] == AlertSeverity.WARNING.value
        assert record["reason"] == "dnd_active_non_critical"

    def test_warning_sent_when_dnd_disabled(self, store, notification_service, user_a, warning_alert):
        """免打扰关闭 → WARNING 正常发送"""
        user_a.dnd_schedule.enabled = False

        result = notification_service.send_alert_notification(user_a.user_id, warning_alert)

        assert result is not None
        assert result.alert_id == warning_alert.id
        assert result.severity == AlertSeverity.WARNING
        assert result.user_id == user_a.user_id

    def test_info_not_sent_when_dnd_enabled(self, store, notification_service, user_a, info_alert):
        """用户免打扰已开启 → INFO 级别也被拦截"""
        user_a.dnd_schedule.enabled = True
        user_a.dnd_schedule.start_time = dtime(22, 0)
        user_a.dnd_schedule.end_time = dtime(8, 0)

        result = notification_service.send_alert_notification(user_a.user_id, info_alert)

        assert result is None, "INFO 级别在免打扰期间不应发送通知"

    def test_warning_not_sent_multi_channel_dnd(self, store, notification_service, user_a, warning_alert):
        """免打扰时段 → WARNING 多渠道发送也被拦截"""
        user_a.dnd_schedule.enabled = True
        user_a.dnd_schedule.start_time = dtime(22, 0)
        user_a.dnd_schedule.end_time = dtime(8, 0)

        results = notification_service.send_alert_multi_channel(
            user_a.user_id, warning_alert,
            channels=["platform", "email", "sms"],
        )

        assert len(results) == 0, "免打扰期间 WARNING 多渠道通知均应被拦截"


# ============================================================
# 测试：CRITICAL 级别在免打扰时段正常发送
# ============================================================

class TestCriticalBypassesDND:
    """验收标准 2：CRITICAL 级别正常发送通知（即使免打扰开启）"""

    def test_critical_sent_when_dnd_enabled(self, store, notification_service, user_a, critical_alert):
        """免打扰开启 → CRITICAL 告警正常发送"""
        user_a.dnd_schedule.enabled = True
        user_a.dnd_schedule.start_time = dtime(22, 0)
        user_a.dnd_schedule.end_time = dtime(8, 0)

        result = notification_service.send_alert_notification(user_a.user_id, critical_alert)

        assert result is not None
        assert result.alert_id == critical_alert.id
        assert result.severity == AlertSeverity.CRITICAL

    def test_critical_not_suppressed(self, store, notification_service, user_a, critical_alert):
        """免打扰开启 → CRITICAL 不被记录到 suppressed"""
        user_a.dnd_schedule.enabled = True
        user_a.dnd_schedule.start_time = dtime(22, 0)
        user_a.dnd_schedule.end_time = dtime(8, 0)

        notification_service.send_alert_notification(user_a.user_id, critical_alert)

        assert store.get_suppressed_count() == 0

    def test_critical_sent_multi_channel_dnd(self, store, notification_service, user_a, critical_alert):
        """免打扰时段 → CRITICAL 多渠道正常发送"""
        user_a.dnd_schedule.enabled = True
        user_a.dnd_schedule.start_time = dtime(22, 0)
        user_a.dnd_schedule.end_time = dtime(8, 0)

        results = notification_service.send_alert_multi_channel(
            user_a.user_id, critical_alert,
            channels=["platform", "email", "sms"],
        )

        assert len(results) == 3
        channels_used = set(n.channel for n in results)
        assert "platform" in channels_used
        assert "email" in channels_used
        assert "sms" in channels_used

    def test_critical_sent_when_dnd_disabled(self, store, notification_service, user_a, critical_alert):
        """免打扰关闭 → CRITICAL 也正常发送（回归测试）"""
        user_a.dnd_schedule.enabled = False

        result = notification_service.send_alert_notification(user_a.user_id, critical_alert)

        assert result is not None
        assert result.severity == AlertSeverity.CRITICAL


# ============================================================
# 测试：时间感知的免打扰
# ============================================================

class TestTimeAwareDND:
    """时间感知的免打扰时段判断"""

    def test_warning_suppressed_within_time_range(self, store, user_a, warning_alert):
        """当前时间 23:00，免打扰 22:00~08:00 → WARNING 被拦截"""
        now = datetime(2026, 7, 16, 23, 30, 0, tzinfo=timezone.utc)
        user_a.dnd_schedule.enabled = True
        user_a.dnd_schedule.start_time = dtime(22, 0)
        user_a.dnd_schedule.end_time = dtime(8, 0)

        service = DNDAwareNotificationService(store, current_time=now)
        result = service.send_alert_notification(user_a.user_id, warning_alert)

        assert result is None, "23:00 在免打扰时段内，WARNING 应被拦截"

    def test_warning_sent_outside_time_range(self, store, user_a, warning_alert):
        """当前时间 14:00，免打扰 22:00~08:00 → WARNING 正常发送"""
        now = datetime(2026, 7, 16, 14, 0, 0, tzinfo=timezone.utc)
        user_a.dnd_schedule.enabled = True
        user_a.dnd_schedule.start_time = dtime(22, 0)
        user_a.dnd_schedule.end_time = dtime(8, 0)

        service = DNDAwareNotificationService(store, current_time=now)
        result = service.send_alert_notification(user_a.user_id, warning_alert)

        assert result is not None, "14:00 不在免打扰时段内，WARNING 应正常发送"

    def test_critical_sent_within_time_range_time_aware(self, store, user_a, critical_alert):
        """当前时间 03:00，免打扰 22:00~08:00 → CRITICAL 仍正常发送"""
        now = datetime(2026, 7, 16, 3, 0, 0, tzinfo=timezone.utc)
        user_a.dnd_schedule.enabled = True
        user_a.dnd_schedule.start_time = dtime(22, 0)
        user_a.dnd_schedule.end_time = dtime(8, 0)

        service = DNDAwareNotificationService(store, current_time=now)
        result = service.send_alert_notification(user_a.user_id, critical_alert)

        assert result is not None, "即使 03:00 在免打扰时段，CRITICAL 也应发送"

    def test_boundary_at_dnd_start_time(self, store, user_a, warning_alert):
        """恰好在免打扰开始时间 22:00 → WARNING 被拦截"""
        now = datetime(2026, 7, 16, 22, 0, 0, tzinfo=timezone.utc)
        user_a.dnd_schedule.enabled = True
        user_a.dnd_schedule.start_time = dtime(22, 0)
        user_a.dnd_schedule.end_time = dtime(8, 0)

        service = DNDAwareNotificationService(store, current_time=now)
        result = service.send_alert_notification(user_a.user_id, warning_alert)

        assert result is None

    def test_boundary_at_dnd_end_time(self, store, user_a, warning_alert):
        """恰好在免打扰结束时间 08:00 → WARNING 正常发送（已结束）"""
        now = datetime(2026, 7, 16, 8, 0, 0, tzinfo=timezone.utc)
        user_a.dnd_schedule.enabled = True
        user_a.dnd_schedule.start_time = dtime(22, 0)
        user_a.dnd_schedule.end_time = dtime(8, 0)

        service = DNDAwareNotificationService(store, current_time=now)
        result = service.send_alert_notification(user_a.user_id, warning_alert)

        assert result is not None, "08:00 免打扰已结束，应正常发送"

    def test_non_cross_day_schedule(self, store, user_a, warning_alert):
        """非跨天时段 22:00~23:00 → 23:30 不应被拦截"""
        now = datetime(2026, 7, 16, 23, 30, 0, tzinfo=timezone.utc)
        user_a.dnd_schedule.enabled = True
        user_a.dnd_schedule.start_time = dtime(22, 0)
        user_a.dnd_schedule.end_time = dtime(23, 0)

        service = DNDAwareNotificationService(store, current_time=now)
        result = service.send_alert_notification(user_a.user_id, warning_alert)

        assert result is not None, "23:30 不在 22:00~23:00 内，应正常发送"

    def test_non_cross_day_schedule_within_range(self, store, user_a, warning_alert):
        """非跨天时段 22:00~23:00 → 22:30 应被拦截"""
        now = datetime(2026, 7, 16, 22, 30, 0, tzinfo=timezone.utc)
        user_a.dnd_schedule.enabled = True
        user_a.dnd_schedule.start_time = dtime(22, 0)
        user_a.dnd_schedule.end_time = dtime(23, 0)

        service = DNDAwareNotificationService(store, current_time=now)
        result = service.send_alert_notification(user_a.user_id, warning_alert)

        assert result is None, "22:30 在 22:00~23:00 内，应被拦截"


# ============================================================
# 测试：用户个人设置管理免打扰时段
# ============================================================

class TestUserDNDSettingsManagement:
    """验收标准 3：用户可在个人设置中管理免打扰时段"""

    def test_get_default_dnd_schedule(self, store, user_settings_service, user_a):
        """新建用户 → 免打扰默认关闭"""
        schedule = user_settings_service.get_dnd_schedule(user_a.user_id)

        assert schedule is not None
        assert schedule.enabled is False

    def test_enable_dnd_with_time_range(self, store, user_settings_service, user_a):
        """用户设置免打扰时段 22:00~08:00 → 设置生效"""
        result = user_settings_service.enable_dnd(
            user_a.user_id,
            start_time=dtime(22, 0),
            end_time=dtime(8, 0),
        )

        assert result is True
        schedule = user_settings_service.get_dnd_schedule(user_a.user_id)
        assert schedule.enabled is True
        assert schedule.start_time == dtime(22, 0)
        assert schedule.end_time == dtime(8, 0)

    def test_disable_dnd(self, store, user_settings_service, user_a):
        """用户关闭免打扰 → enabled 变为 False"""
        user_settings_service.enable_dnd(user_a.user_id, dtime(22, 0), dtime(8, 0))
        user_settings_service.disable_dnd(user_a.user_id)

        schedule = user_settings_service.get_dnd_schedule(user_a.user_id)
        assert schedule.enabled is False

    def test_update_dnd_time_range(self, store, user_settings_service, user_a):
        """用户修改免打扰时段 → 新时段生效"""
        user_settings_service.enable_dnd(user_a.user_id, dtime(22, 0), dtime(8, 0))
        user_settings_service.set_dnd_schedule(
            user_a.user_id,
            enabled=True,
            start_time=dtime(1, 0),
            end_time=dtime(7, 0),
        )

        schedule = user_settings_service.get_dnd_schedule(user_a.user_id)
        assert schedule.start_time == dtime(1, 0)
        assert schedule.end_time == dtime(7, 0)

    def test_get_dnd_for_nonexistent_user(self, store, user_settings_service):
        """查询不存在的用户 → 返回 None"""
        result = user_settings_service.get_dnd_schedule("nonexistent-user")
        assert result is None

    def test_set_dnd_for_nonexistent_user(self, store, user_settings_service):
        """设置不存在用户的免打扰 → 返回 None"""
        result = user_settings_service.set_dnd_schedule(
            "nonexistent-user",
            enabled=True,
            start_time=dtime(22, 0),
            end_time=dtime(8, 0),
        )
        assert result is None

    def test_multiple_users_independent_dnd(self, store, user_settings_service, user_a):
        """两个用户各自设置不同的免打扰时段 → 互不影响"""
        user_b = UserSettings.create(user_id="user-002", username="bob", dnd_enabled=False)
        store.add_user(user_b)

        user_settings_service.enable_dnd(user_a.user_id, dtime(22, 0), dtime(8, 0))
        user_settings_service.enable_dnd(user_b.user_id, dtime(0, 0), dtime(6, 0))

        schedule_a = user_settings_service.get_dnd_schedule(user_a.user_id)
        schedule_b = user_settings_service.get_dnd_schedule(user_b.user_id)

        assert schedule_a.start_time == dtime(22, 0)
        assert schedule_b.start_time == dtime(0, 0)
        assert schedule_a.end_time == dtime(8, 0)
        assert schedule_b.end_time == dtime(6, 0)


# ============================================================
# 测试：免打扰时段组合场景
# ============================================================

class TestDNDEndToEnd:
    """免打扰时段端到端组合场景"""

    def test_full_scenario_warning_suppressed_critical_delivered(self, store, user_a, warning_alert, critical_alert):
        """免打扰开启 → WARNING 被拦截，CRITICAL 正常发送"""
        user_a.dnd_schedule.enabled = True
        user_a.dnd_schedule.start_time = dtime(22, 0)
        user_a.dnd_schedule.end_time = dtime(8, 0)

        service = NotificationService(store)

        # WARNING 被拦截
        warning_result = service.send_alert_notification(user_a.user_id, warning_alert)
        assert warning_result is None

        # CRITICAL 正常发送
        critical_result = service.send_alert_notification(user_a.user_id, critical_alert)
        assert critical_result is not None
        assert critical_result.severity == AlertSeverity.CRITICAL

        # suppressed 记录只有 WARNING
        assert store.get_suppressed_count() == 1
        assert store.suppressed_alerts[0]["severity"] == AlertSeverity.WARNING.value

    def test_dnd_disabled_all_severities_sent(self, store, user_a, warning_alert, critical_alert, info_alert):
        """免打扰关闭 → 所有级别都正常发送"""
        user_a.dnd_schedule.enabled = False

        service = NotificationService(store)

        n_warning = service.send_alert_notification(user_a.user_id, warning_alert)
        n_critical = service.send_alert_notification(user_a.user_id, critical_alert)
        n_info = service.send_alert_notification(user_a.user_id, info_alert)

        assert n_warning is not None
        assert n_critical is not None
        assert n_info is not None

    def test_sequential_toggle_dnd(self, store, user_settings_service, notification_service, user_a, warning_alert):
        """开启免打扰 → WARNING 被拦截 → 关闭免打扰 → WARNING 正常发送"""
        # 开启免打扰
        user_settings_service.enable_dnd(user_a.user_id, dtime(0, 0), dtime(23, 59))

        n1 = notification_service.send_alert_notification(user_a.user_id, warning_alert)
        assert n1 is None, "免打扰开启时 WARNING 应被拦截"

        # 关闭免打扰
        user_settings_service.disable_dnd(user_a.user_id)

        n2 = notification_service.send_alert_notification(user_a.user_id, warning_alert)
        assert n2 is not None, "免打扰关闭后 WARNING 应正常发送"

    def test_dnd_with_no_user(self, store, notification_service, warning_alert):
        """用户不存在 → 不发送通知，不报错"""
        result = notification_service.send_alert_notification("nonexistent", warning_alert)
        assert result is None

    def test_dnd_schedule_with_no_times(self, store, notification_service, user_a, warning_alert):
        """免打扰 enabled=True 但没有设置起止时间 → 视为不拦截"""
        user_a.dnd_schedule.enabled = True
        user_a.dnd_schedule.start_time = None
        user_a.dnd_schedule.end_time = None

        result = notification_service.send_alert_notification(user_a.user_id, warning_alert)
        assert result is not None, "没有设置起止时间时不应拦截"


if __name__ == "__main__":
    pytest.main([__file__, "-v"])
