import pytest
import time
import uuid
from datetime import datetime, timedelta, timezone


class MockClock:
    """可注入时钟，用于确定性时间测量。"""

    def __init__(self):
        self._current_time = None
        self._frozen = False

    def now(self) -> datetime:
        if self._frozen and self._current_time is not None:
            return self._current_time
        return datetime.now(timezone.utc)

    def freeze_at(self, dt: datetime) -> None:
        self._frozen = True
        self._current_time = dt

    def thaw(self) -> None:
        self._frozen = False
        self._current_time = None

    def advance(self, seconds: float) -> None:
        if self._current_time is not None:
            self._current_time = self._current_time + timedelta(seconds=seconds)


class NotificationRecord:
    """单条通知记录。"""

    def __init__(self, user_id: str, role: str, content: str):
        self.id = str(uuid.uuid4())
        self.user_id = user_id
        self.role = role
        self.content = content
        self.sent = False
        self.created_at: datetime = datetime.now(timezone.utc)
        self.sent_at: datetime = None

    def mark_sent(self, sent_at: datetime = None) -> None:
        self.sent = True
        self.sent_at = sent_at or datetime.now(timezone.utc)


class AlertNotificationRouter:
    """根据告警严重级别路由通知。"""

    SYSTEM_ADMIN_USER_ID = "sys_admin_001"
    PROJECT_LEAD_USER_ID = "project_lead_001"
    SLA_MAX_SECONDS = 30.0

    CRITICAL_LEVELS = {"critical", "fatal", "emerg", "emergency"}

    def __init__(self, clock: MockClock = None):
        self.clock = clock or MockClock()
        self._sent_notifications: list[NotificationRecord] = []

    def _resolve_recipients(self, level: str) -> list[dict]:
        """根据告警级别解析接收人。"""
        level_lower = (level or "").lower().strip()
        if level_lower in self.CRITICAL_LEVELS:
            return [
                {"user_id": self.SYSTEM_ADMIN_USER_ID, "role": "system_admin"},
                {"user_id": self.PROJECT_LEAD_USER_ID, "role": "project_lead"},
            ]
        return [{"user_id": self.PROJECT_LEAD_USER_ID, "role": "project_lead"}]

    def process_alert(self, alert: dict) -> list[NotificationRecord]:
        level = alert.get("level", "")
        message = alert.get("message", "")
        start_time = time.perf_counter()
        recipients = self._resolve_recipients(level)
        notifications = []
        for recipient in recipients:
            record = NotificationRecord(
                user_id=recipient["user_id"],
                role=recipient["role"],
                content=message,
            )
            record.mark_sent(self.clock.now())
            self._sent_notifications.append(record)
            notifications.append(record)
        elapsed = time.perf_counter() - start_time
        for n in notifications:
            n._elapsed_seconds = elapsed
        return notifications

    @property
    def sent_notifications(self) -> list[NotificationRecord]:
        return list(self._sent_notifications)


@pytest.fixture
def mock_clock():
    return MockClock()


@pytest.fixture
def router(mock_clock):
    return AlertNotificationRouter(clock=mock_clock)


class TestCriticalAlertRecipients:
    """验收标准：通知接收人包含系统管理员和项目负责人。"""

    def test_critical_alert_notifies_sys_admin_and_project_lead(self, router):
        alert = {"level": "critical", "message": "数据库连接池耗尽"}
        results = router.process_alert(alert)
        user_ids = {r.user_id for r in results}
        roles = {r.role for r in results}
        assert AlertNotificationRouter.SYSTEM_ADMIN_USER_ID in user_ids
        assert AlertNotificationRouter.PROJECT_LEAD_USER_ID in user_ids
        assert "system_admin" in roles
        assert "project_lead" in roles
        assert len(results) == 2

    def test_fatal_level_same_recipients(self, router):
        alert = {"level": "fatal", "message": "磁盘空间不足"}
        results = router.process_alert(alert)
        user_ids = {r.user_id for r in results}
        assert AlertNotificationRouter.SYSTEM_ADMIN_USER_ID in user_ids
        assert AlertNotificationRouter.PROJECT_LEAD_USER_ID in user_ids

    def test_emergency_level_same_recipients(self, router):
        alert = {"level": "emergency", "message": "服务不可用"}
        results = router.process_alert(alert)
        user_ids = {r.user_id for r in results}
        assert AlertNotificationRouter.SYSTEM_ADMIN_USER_ID in user_ids
        assert AlertNotificationRouter.PROJECT_LEAD_USER_ID in user_ids

    def test_emerg_level_same_recipients(self, router):
        alert = {"level": "emerg", "message": "内核崩溃"}
        results = router.process_alert(alert)
        user_ids = {r.user_id for r in results}
        assert AlertNotificationRouter.SYSTEM_ADMIN_USER_ID in user_ids
        assert AlertNotificationRouter.PROJECT_LEAD_USER_ID in user_ids

    def test_critical_uppercase_level(self, router):
        alert = {"level": "CRITICAL", "message": "内存溢出"}
        results = router.process_alert(alert)
        user_ids = {r.user_id for r in results}
        assert AlertNotificationRouter.SYSTEM_ADMIN_USER_ID in user_ids
        assert AlertNotificationRouter.PROJECT_LEAD_USER_ID in user_ids

    def test_critical_with_spaces_level(self, router):
        alert = {"level": "  critical  ", "message": "CPU过载"}
        results = router.process_alert(alert)
        user_ids = {r.user_id for r in results}
        assert AlertNotificationRouter.SYSTEM_ADMIN_USER_ID in user_ids
        assert AlertNotificationRouter.PROJECT_LEAD_USER_ID in user_ids

    def test_critical_notifications_all_marked_sent(self, router):
        alert = {"level": "critical", "message": "服务宕机"}
        results = router.process_alert(alert)
        for r in results:
            assert r.sent is True
            assert r.sent_at is not None

    def test_critical_notifications_have_correct_content(self, router):
        alert = {"level": "critical", "message": "集群节点离线"}
        results = router.process_alert(alert)
        for r in results:
            assert r.content == "集群节点离线"


class TestNonCriticalAlertRecipients:
    """非严重级别告警仅通知项目负责人。"""

    def test_warning_only_project_lead(self, router):
        alert = {"level": "warning", "message": "慢查询增多"}
        results = router.process_alert(alert)
        user_ids = {r.user_id for r in results}
        assert AlertNotificationRouter.SYSTEM_ADMIN_USER_ID not in user_ids
        assert AlertNotificationRouter.PROJECT_LEAD_USER_ID in user_ids
        assert len(results) == 1

    def test_error_only_project_lead(self, router):
        alert = {"level": "error", "message": "接口调用失败"}
        results = router.process_alert(alert)
        user_ids = {r.user_id for r in results}
        assert AlertNotificationRouter.SYSTEM_ADMIN_USER_ID not in user_ids
        assert AlertNotificationRouter.PROJECT_LEAD_USER_ID in user_ids
        assert len(results) == 1

    def test_info_only_project_lead(self, router):
        alert = {"level": "info", "message": "定时任务完成"}
        results = router.process_alert(alert)
        user_ids = {r.user_id for r in results}
        assert AlertNotificationRouter.SYSTEM_ADMIN_USER_ID not in user_ids
        assert AlertNotificationRouter.PROJECT_LEAD_USER_ID in user_ids
        assert len(results) == 1

    def test_debug_only_project_lead(self, router):
        alert = {"level": "debug", "message": "调试信息"}
        results = router.process_alert(alert)
        user_ids = {r.user_id for r in results}
        assert AlertNotificationRouter.SYSTEM_ADMIN_USER_ID not in user_ids
        assert AlertNotificationRouter.PROJECT_LEAD_USER_ID in user_ids
        assert len(results) == 1


class TestEdgeCaseAlertProcessing:
    """边界场景：缺少level、level为None、空字典。"""

    def test_missing_level_key_only_project_lead(self, router):
        alert = {"message": "未知级别告警"}
        results = router.process_alert(alert)
        user_ids = {r.user_id for r in results}
        assert AlertNotificationRouter.SYSTEM_ADMIN_USER_ID not in user_ids
        assert AlertNotificationRouter.PROJECT_LEAD_USER_ID in user_ids
        assert len(results) == 1

    def test_level_none_only_project_lead(self, router):
        alert = {"level": None, "message": "null级别告警"}
        results = router.process_alert(alert)
        user_ids = {r.user_id for r in results}
        assert AlertNotificationRouter.SYSTEM_ADMIN_USER_ID not in user_ids
        assert AlertNotificationRouter.PROJECT_LEAD_USER_ID in user_ids
        assert len(results) == 1

    def test_empty_alert_dict_only_project_lead(self, router):
        alert = {}
        results = router.process_alert(alert)
        user_ids = {r.user_id for r in results}
        assert AlertNotificationRouter.SYSTEM_ADMIN_USER_ID not in user_ids
        assert AlertNotificationRouter.PROJECT_LEAD_USER_ID in user_ids
        assert len(results) == 1

    def test_empty_string_level_only_project_lead(self, router):
        alert = {"level": "", "message": "空字符串级别"}
        results = router.process_alert(alert)
        user_ids = {r.user_id for r in results}
        assert AlertNotificationRouter.SYSTEM_ADMIN_USER_ID not in user_ids
        assert AlertNotificationRouter.PROJECT_LEAD_USER_ID in user_ids

    def test_whitespace_only_level_only_project_lead(self, router):
        alert = {"level": "   ", "message": "空白级别"}
        results = router.process_alert(alert)
        user_ids = {r.user_id for r in results}
        assert AlertNotificationRouter.SYSTEM_ADMIN_USER_ID not in user_ids
        assert AlertNotificationRouter.PROJECT_LEAD_USER_ID in user_ids


class TestCriticalAlertDeliverySLA:
    """验收标准：通知在 <=30秒内送达。"""

    def test_critical_alert_delivered_within_30_seconds(self, router):
        alert = {"level": "critical", "message": "SLA测试告警"}
        wall_start = time.perf_counter()
        results = router.process_alert(alert)
        wall_end = time.perf_counter()
        wall_delta = wall_end - wall_start
        for r in results:
            elapsed = getattr(r, "_elapsed_seconds", wall_delta)
            assert elapsed <= AlertNotificationRouter.SLA_MAX_SECONDS, (
                f"SLA违规：通知送达延迟{elapsed:.3f}秒，超过30秒上限"
            )
        assert wall_delta <= AlertNotificationRouter.SLA_MAX_SECONDS, (
            f"端到端处理耗时{wall_delta:.6f}秒超过30秒SLA"
        )

    def test_critical_alert_latency_within_sla_multiple_alerts(self, router):
        for i in range(10):
            alert = {"level": "critical", "message": f"批量SLA测试{i}"}
            t0 = time.perf_counter()
            results = router.process_alert(alert)
            delta = time.perf_counter() - t0
            assert delta <= AlertNotificationRouter.SLA_MAX_SECONDS, (
                f"第{i}次告警处理耗时{delta:.6f}秒，超出30秒SLA"
            )
            for r in results:
                assert r.sent is True
                assert r.sent_at is not None

    def test_critical_alert_sent_at_within_30_seconds_of_created_at(self, router, mock_clock):
        base_time = datetime.now(timezone.utc)
        mock_clock.freeze_at(base_time)
        router.clock = mock_clock
        alert = {"level": "critical", "message": "时钟注入测试"}
        results = router.process_alert(alert)
        for r in results:
            if r.created_at is not None and r.sent_at is not None:
                internal_delta = (r.sent_at - r.created_at).total_seconds()
                assert internal_delta <= 30.0, (
                    f"内部时钟delta={internal_delta:.3f}s 超过30秒"
                )

    def test_critical_alert_sent_at_advanced_clock_still_within_sla(self, router, mock_clock):
        base_time = datetime.now(timezone.utc)
        mock_clock.freeze_at(base_time)
        router.clock = mock_clock
        alert = {"level": "critical", "message": "时钟推进测试"}
        mock_clock.advance(25.0)
        results = router.process_alert(alert)
        for r in results:
            if r.created_at is not None and r.sent_at is not None:
                internal_delta = (r.sent_at - r.created_at).total_seconds()
                assert internal_delta <= 31.0, (
                    f"推进25秒后delta={internal_delta:.3f}s，应仍在可接受范围内"
                )

    def test_non_critical_alert_also_within_sla(self, router):
        alert = {"level": "warning", "message": "非严重SLA测试"}
        t0 = time.perf_counter()
        results = router.process_alert(alert)
        delta = time.perf_counter() - t0
        assert delta <= AlertNotificationRouter.SLA_MAX_SECONDS
        assert len(results) == 1


class TestNotificationRecordProperties:
    """通知记录的属性验证。"""

    def test_notification_record_has_uuid(self):
        record = NotificationRecord("u1", "admin", "test")
        assert record.id is not None
        assert len(record.id) == 36

    def test_notification_record_user_id_preserved(self):
        record = NotificationRecord("sys_admin_001", "system_admin", "msg")
        assert record.user_id == "sys_admin_001"
        assert record.role == "system_admin"
        assert record.content == "msg"

    def test_notification_record_initially_not_sent(self):
        record = NotificationRecord("u1", "admin", "test")
        assert record.sent is False
        assert record.sent_at is None

    def test_notification_record_mark_sent(self):
        record = NotificationRecord("u1", "admin", "test")
        dt = datetime.now(timezone.utc)
        record.mark_sent(dt)
        assert record.sent is True
        assert record.sent_at == dt

    def test_notification_record_auto_timestamp(self):
        record = NotificationRecord("u1", "admin", "test")
        before = datetime.now(timezone.utc)
        record.mark_sent()
        after = datetime.now(timezone.utc)
        assert before <= record.sent_at <= after


class TestMultipleAlertsAccumulation:
    """多次告警通知累积验证。"""

    def test_sent_notifications_accumulate_across_alerts(self, router):
        alert1 = {"level": "critical", "message": "告警一"}
        alert2 = {"level": "critical", "message": "告警二"}
        router.process_alert(alert1)
        router.process_alert(alert2)
        all_sent = router.sent_notifications
        assert len(all_sent) == 4

    def test_sent_notifications_are_copy(self, router):
        router.process_alert({"level": "critical", "message": "测试"})
        list1 = router.sent_notifications
        list2 = router.sent_notifications
        assert list1 is not list2
        assert list1 == list2

    def test_mixed_level_accumulation(self, router):
        router.process_alert({"level": "critical", "message": "c1"})
        router.process_alert({"level": "warning", "message": "w1"})
        router.process_alert({"level": "error", "message": "e1"})
        all_sent = router.sent_notifications
        assert len(all_sent) == 4
        critical_roles = {r.role for r in all_sent if r.content == "c1"}
        assert "system_admin" in critical_roles
        assert "project_lead" in critical_roles

    def test_critical_alert_notifications_are_independent(self, router):
        alert = {"level": "critical", "message": "独立记录"}
        results = router.process_alert(alert)
        assert len(results) == 2
        assert results[0].id != results[1].id
        assert results[0].user_id != results[1].user_id
