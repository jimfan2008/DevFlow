import time
from datetime import datetime, timedelta, date
from dataclasses import dataclass, field
from typing import Optional, List


# ─── Domain Models ─────────────────────────────────────────────

@dataclass
class ArchiveGroup:
    """归档群组，包含保留期和通知配置。"""
    id: str
    name: str
    created_at: datetime
    retention_days: int
    admin_emails: List[str] = field(default_factory=list)

    @property
    def expiry_date(self) -> date:
        """计算归档到期日期。"""
        return (self.created_at + timedelta(days=self.retention_days)).date()

    @property
    def days_until_expiry(self) -> int:
        """距离到期还剩多少天（可为负值表示已过期天数）。"""
        return (self.expiry_date - date.today()).days


@dataclass
class ExpiryNotification:
    """到期提醒通知的数据结构。"""
    archive_group_id: str
    archive_group_name: str
    expiry_date: date
    days_until_expiry: int
    handling_suggestions: List[str]
    sent_at: Optional[datetime] = None
    success: bool = False
    error: Optional[str] = None


# ─── Services ──────────────────────────────────────────────────

class NotificationService:
    """通知发送服务，封装发送逻辑并支持模拟失败率配置。"""

    def __init__(self, fail_rate: float = 0.0):
        self.fail_rate = fail_rate
        self._send_count = 0

    def send_reminder(self, notification: ExpiryNotification) -> tuple:
        """发送提醒通知，返回 (success: bool, error: Optional[str])。"""
        self._send_count += 1
        if self.fail_rate > 0 and self._send_count % max(1, int(1 / self.fail_rate)) == 0:
            return False, "Simulated notification send failure"
        return True, None


class ArchiveExpiryService:
    """归档到期提醒服务，扫描过期归档并发送提醒。"""

    def __init__(self, notifier: Optional[NotificationService] = None):
        self.notifier = notifier or NotificationService()
        self._sent_notifications: List[ExpiryNotification] = []
        self._reminded_ids: set = set()

    def check_and_remind(self, groups: List[ArchiveGroup],
                         threshold_days: int = 30) -> dict:
        """扫描归档群组，对 threshold_days 内到期的发送提醒，返回统计报告。"""
        results: List[ExpiryNotification] = []
        for group in groups:
            if group.id in self._reminded_ids:
                continue
            if 0 <= group.days_until_expiry <= threshold_days:
                notification = self._build_notification(group)
                success, error = self.notifier.send_reminder(notification)
                notification.success = success
                notification.error = error
                notification.sent_at = datetime.now()
                results.append(notification)
                self._sent_notifications.append(notification)
                self._reminded_ids.add(group.id)
        return self._build_report(results)

    def _build_notification(self, group: ArchiveGroup) -> ExpiryNotification:
        """根据归档群组构建通知对象。"""
        suggestions = self._build_suggestions(group)
        return ExpiryNotification(
            archive_group_id=group.id,
            archive_group_name=group.name,
            expiry_date=group.expiry_date,
            days_until_expiry=group.days_until_expiry,
            handling_suggestions=suggestions,
        )

    def _build_suggestions(self, group: ArchiveGroup) -> List[str]:
        """根据到期紧迫程度生成处理建议列表。"""
        suggestions = [
            f"归档群组「{group.name}」(ID: {group.id}) 将于 {group.expiry_date} 到期",
            f"距离到期还有 {group.days_until_expiry} 天",
        ]
        if group.days_until_expiry <= 7:
            suggestions.append("建议：立即续期或备份数据，避免数据丢失")
        elif group.days_until_expiry <= 14:
            suggestions.append("建议：尽快处理续期或归档迁移")
        else:
            suggestions.append("建议：检查数据状态，根据需要续期或归档")
        suggestions.append("操作方式：登录管理后台 → 归档管理 → 续期/删除")
        return suggestions

    def _build_report(self, notifications: List[ExpiryNotification]) -> dict:
        """生成统计报告。"""
        total = len(notifications)
        success_count = sum(1 for n in notifications if n.success)
        success_rate = (success_count / total * 100.0) if total > 0 else 100.0
        return {
            "total": total,
            "success": success_count,
            "failed": total - success_count,
            "success_rate": success_rate,
            "notifications": notifications,
        }


# ─── Fixtures ──────────────────────────────────────────────────

def _make_group(group_id: str, name: str, days_from_now: int,
                admin_emails: Optional[List[str]] = None) -> ArchiveGroup:
    """辅助函数：创建一个距离到期还有指定天数的归档群组。"""
    expiry = date.today() + timedelta(days=days_from_now)
    created = datetime(expiry.year, expiry.month, expiry.day) - timedelta(days=90)
    return ArchiveGroup(
        id=group_id,
        name=name,
        created_at=created,
        retention_days=90,
        admin_emails=admin_emails or ["admin@example.com"],
    )


# ─── Tests ─────────────────────────────────────────────────────

class TestArchiveGroupModel:
    """归档群组模型单元测试。"""

    def test_expiry_date_calculation(self):
        """验证到期日期 = 创建日期 + 保留天数。"""
        group = ArchiveGroup(
            id="a1", name="测试组",
            created_at=datetime(2024, 1, 1), retention_days=90,
        )
        assert group.expiry_date == date(2024, 4, 1)

    def test_days_until_expiry_future(self):
        """验证未来到期的天数计算正确。"""
        future = date.today() + timedelta(days=15)
        created = datetime(future.year, future.month, future.day) - timedelta(days=30)
        group = ArchiveGroup("a2", "未来组", created, retention_days=30)
        assert group.days_until_expiry == 15

    def test_days_until_expiry_exact_today(self):
        """验证当天到期返回 0。"""
        group = ArchiveGroup(
            id="a3", name="今天到期",
            created_at=datetime.now() - timedelta(days=90),
            retention_days=90,
        )
        assert group.days_until_expiry == 0

    def test_days_until_expiry_past(self):
        """验证已过期返回负数。"""
        group = ArchiveGroup(
            id="a4", name="已过期",
            created_at=datetime.now() - timedelta(days=100),
            retention_days=90,
        )
        assert group.days_until_expiry < 0


class TestArchiveExpiryService:
    """归档到期提醒服务验收测试。"""

    # ── AC1：到期前30天自动发送提醒 ──

    def test_sends_reminder_within_30_days(self):
        """AC1：30天内的归档收到提醒。"""
        service = ArchiveExpiryService()
        groups = [
            _make_group("g1", "5天到期", days_from_now=5),
            _make_group("g2", "15天到期", days_from_now=15),
            _make_group("g3", "30天到期", days_from_now=30),
        ]
        report = service.check_and_remind(groups)
        assert report["total"] == 3
        assert report["success"] == 3

    def test_no_reminder_beyond_30_days(self):
        """AC1：超过30天的不发送提醒。"""
        service = ArchiveExpiryService()
        groups = [
            _make_group("g4", "45天到期", days_from_now=45),
            _make_group("g5", "90天到期", days_from_now=90),
        ]
        report = service.check_and_remind(groups)
        assert report["total"] == 0

    def test_mixed_eligibility(self):
        """AC1：混合场景下只提醒符合条件的归档。"""
        service = ArchiveExpiryService()
        groups = [
            _make_group("g6", "10天", days_from_now=10),
            _make_group("g7", "60天", days_from_now=60),
            _make_group("g8", "30天", days_from_now=30),
        ]
        report = service.check_and_remind(groups)
        assert report["total"] == 2
        reminded_ids = {n.archive_group_id for n in report["notifications"]}
        assert "g6" in reminded_ids
        assert "g8" in reminded_ids
        assert "g7" not in reminded_ids

    def test_exactly_30_days_triggers_reminder(self):
        """AC1 boundary：恰好 30 天触发提醒。"""
        service = ArchiveExpiryService()
        group = _make_group("g9", "临界30天", days_from_now=30)
        report = service.check_and_remind([group])
        assert report["total"] == 1

    def test_expired_archive_at_0_days_triggers_reminder(self):
        """AC1 boundary：当天到期（0天）触发提醒。"""
        service = ArchiveExpiryService()
        group = _make_group("g10", "当天到期", days_from_now=0)
        report = service.check_and_remind([group])
        assert report["total"] == 1

    def test_negative_days_skipped(self):
        """AC1 boundary：已过期（负天数）不触发提醒。"""
        service = ArchiveExpiryService()
        group = _make_group("g11", "已过期10天", days_from_now=-10)
        report = service.check_and_remind([group])
        assert report["total"] == 0

    # ── AC2：通知包含归档群组ID、到期日期、处理建议 ──

    def test_notification_contains_group_id(self):
        """AC2：通知包含归档群组 ID。"""
        service = ArchiveExpiryService()
        group = _make_group("arch-id-test", "ID测试", days_from_now=10)
        report = service.check_and_remind([group])
        assert report["notifications"][0].archive_group_id == "arch-id-test"

    def test_notification_contains_expiry_date(self):
        """AC2：通知包含到期日期。"""
        service = ArchiveExpiryService()
        expected = date.today() + timedelta(days=10)
        group = _make_group("arch-date-test", "日期测试", days_from_now=10)
        report = service.check_and_remind([group])
        assert report["notifications"][0].expiry_date == expected

    def test_notification_contains_handling_suggestions(self):
        """AC2：通知包含处理建议。"""
        service = ArchiveExpiryService()
        group = _make_group("arch-suggest-test", "建议测试", days_from_now=10)
        report = service.check_and_remind([group])
        suggestions = report["notifications"][0].handling_suggestions
        assert len(suggestions) > 0
        assert all(isinstance(s, str) for s in suggestions)
        assert any("建议测试" in s for s in suggestions)

    def test_suggestions_mention_group_id(self):
        """AC2：处理建议中包含群组 ID。"""
        service = ArchiveExpiryService()
        group = _make_group("arch-sug-id", "建议ID测试", days_from_now=10)
        report = service.check_and_remind([group])
        suggestions_text = " ".join(report["notifications"][0].handling_suggestions)
        assert "arch-sug-id" in suggestions_text

    def test_suggestions_mention_expiry_date(self):
        """AC2：处理建议中包含到期日期。"""
        service = ArchiveExpiryService()
        group = _make_group("arch-sug-date", "建议日期测试", days_from_now=10)
        report = service.check_and_remind([group])
        suggestions_text = " ".join(report["notifications"][0].handling_suggestions)
        expected_date_str = str(group.expiry_date)
        assert expected_date_str in suggestions_text

    # ── AC3：提醒发送成功率 ≥99% ──

    def test_success_rate_100_percent_with_reliable_notifier(self):
        """AC3：可靠通知服务成功率 100%。"""
        service = ArchiveExpiryService()
        groups = [
            _make_group(f"bulk-{i}", f"批量归档{i}", days_from_now=15)
            for i in range(100)
        ]
        report = service.check_and_remind(groups)
        assert report["success_rate"] == 100.0

    def test_success_rate_meets_99_percent_threshold_bulk(self):
        """AC3：批量发送成功率 ≥99%。"""
        notifier = NotificationService(fail_rate=0.005)
        service = ArchiveExpiryService(notifier=notifier)
        groups = [
            _make_group(f"bulk-perf-{i}", f"性能归档{i}", days_from_now=10)
            for i in range(1000)
        ]
        report = service.check_and_remind(groups)
        assert report["success_rate"] >= 99.0, (
            f"Success rate {report['success_rate']:.2f}% < 99%"
        )

    def test_success_rate_calculation_precision(self):
        """AC3：成功率计算精确。"""
        notifier = NotificationService(fail_rate=0.1)
        service = ArchiveExpiryService(notifier=notifier)
        groups = [
            _make_group(f"stat-{i}", f"统计{i}", days_from_now=10)
            for i in range(10)
        ]
        report = service.check_and_remind(groups)
        expected_rate = (report["success"] / report["total"]) * 100
        assert report["success_rate"] == expected_rate

    def test_failure_recorded_when_notification_fails(self):
        """AC3：发送失败时记录错误信息。"""
        notifier = NotificationService(fail_rate=1.0)
        service = ArchiveExpiryService(notifier=notifier)
        group = _make_group("fail-test", "失败测试", days_from_now=5)
        report = service.check_and_remind([group])
        assert report["total"] == 1
        assert report["success"] == 0
        assert report["failed"] == 1
        assert report["notifications"][0].error is not None

    # ── 附加测试：幂等性、边界情况、数据完整性 ──

    def test_no_duplicate_reminders(self):
        """验证同一归档不会收到重复提醒。"""
        service = ArchiveExpiryService()
        group = _make_group("dedup", "防重复", days_from_now=10)
        r1 = service.check_and_remind([group])
        assert r1["total"] == 1
        r2 = service.check_and_remind([group])
        assert r2["total"] == 0

    def test_empty_group_list(self):
        """验证空列表处理正常。"""
        service = ArchiveExpiryService()
        report = service.check_and_remind([])
        assert report["total"] == 0
        assert report["success_rate"] == 100.0

    def test_sent_at_timestamp_recorded(self):
        """验证成功通知记录发送时间戳。"""
        service = ArchiveExpiryService()
        group = _make_group("ts-test", "时间戳测试", days_from_now=10)
        report = service.check_and_remind([group])
        assert report["notifications"][0].sent_at is not None
        assert isinstance(report["notifications"][0].sent_at, datetime)

    def test_urgent_suggestion_differs_from_moderate(self):
        """验证紧急程度不同时处理建议不同。"""
        urgent_svc = ArchiveExpiryService()
        urgent_group = _make_group("urg", "紧急", days_from_now=5)
        urgent_report = urgent_svc.check_and_remind([urgent_group])
        urgent_suggestions = urgent_report["notifications"][0].handling_suggestions

        moderate_svc = ArchiveExpiryService()
        moderate_group = _make_group("mod", "中等", days_from_now=20)
        moderate_report = moderate_svc.check_and_remind([moderate_group])
        moderate_suggestions = moderate_report["notifications"][0].handling_suggestions

        assert urgent_suggestions != moderate_suggestions

    def test_urgent_suggestion_contains_immediate_action(self):
        """验证紧急归档（≤7天）建议中包含立即处理提示。"""
        service = ArchiveExpiryService()
        group = _make_group("urg2", "紧急归档", days_from_now=3)
        report = service.check_and_remind([group])
        suggestions = " ".join(report["notifications"][0].handling_suggestions)
        assert "立即" in suggestions or "备份" in suggestions

    def test_moderate_suggestion_within_14_days(self):
        """验证 8~14 天内归档的建议提示尽快处理。"""
        service = ArchiveExpiryService()
        group = _make_group("mod2", "中等紧急", days_from_now=10)
        report = service.check_and_remind([group])
        suggestions = " ".join(report["notifications"][0].handling_suggestions)
        assert "尽快" in suggestions

    def test_operation_guide_included(self):
        """验证建议中包含操作指引。"""
        service = ArchiveExpiryService()
        group = _make_group("op-guide", "操作引导", days_from_now=20)
        report = service.check_and_remind([group])
        suggestions = " ".join(report["notifications"][0].handling_suggestions)
        assert "登录管理后台" in suggestions or "操作" in suggestions

    def test_multiple_admin_emails_stored(self):
        """验证归档群组可存储多个管理员邮箱。"""
        emails = ["admin@a.com", "admin@b.com", "ops@c.com"]
        group = _make_group("multi-admin", "多管理员", days_from_now=10, admin_emails=emails)
        assert group.admin_emails == emails
        assert len(group.admin_emails) == 3

    def test_days_until_expiry_consistency(self):
        """验证 days_until_expiry 与 expiry_date 的一致性。"""
        group = _make_group("consistency", "一致性", days_from_now=20)
        computed_days = (group.expiry_date - date.today()).days
        assert group.days_until_expiry == computed_days

    def test_notification_days_until_expiry_correct(self):
        """验证通知中的剩余天数与归档群组一致。"""
        service = ArchiveExpiryService()
        group = _make_group("ndays", "天数验证", days_from_now=7)
        report = service.check_and_remind([group])
        assert report["notifications"][0].days_until_expiry == group.days_until_expiry

    def test_response_time_within_threshold(self):
        """验证批量检查响应时间在合理范围内。"""
        service = ArchiveExpiryService()
        groups = [
            _make_group(f"perf-{i}", f"性能{i}", days_from_now=15)
            for i in range(500)
        ]
        start = time.perf_counter()
        service.check_and_remind(groups)
        elapsed = time.perf_counter() - start
        assert elapsed < 5.0, f"Bulk check took {elapsed:.4f}s, exceeds 5s limit"

    def test_isolation_between_service_instances(self):
        """验证不同服务实例的提醒记录互不干扰。"""
        s1 = ArchiveExpiryService()
        s2 = ArchiveExpiryService()
        g1 = _make_group("iso-1", "实例1", days_from_now=10)
        g2 = _make_group("iso-2", "实例2", days_from_now=10)
        s1.check_and_remind([g1])
        s2.check_and_remind([g2])
        assert len(s1._sent_notifications) == 1
        assert len(s2._sent_notifications) == 1
        assert s1._sent_notifications[0].archive_group_id == "iso-1"
        assert s2._sent_notifications[0].archive_group_id == "iso-2"


class TestNotificationServiceUnit:
    """NotificationService 单元测试。"""

    def test_successful_send(self):
        """默认配置下发送成功。"""
        ns = NotificationService()
        notif = ExpiryNotification(
            archive_group_id="u1", archive_group_name="单元测试",
            expiry_date=date(2025, 1, 1), days_until_expiry=30,
            handling_suggestions=["建议"],
        )
        success, error = ns.send_reminder(notif)
        assert success is True
        assert error is None

    def test_failure_with_high_fail_rate(self):
        """高失败率配置下发送失败。"""
        ns = NotificationService(fail_rate=1.0)
        notif = ExpiryNotification(
            archive_group_id="u2", archive_group_name="失败测试",
            expiry_date=date(2025, 1, 1), days_until_expiry=30,
            handling_suggestions=["建议"],
        )
        success, error = ns.send_reminder(notif)
        assert success is False
        assert error is not None
