import time
import pytest


class MuteDurationValidator:
    """禁言时长校验器：支持 1 分钟 ~ 720 小时范围"""

    MIN_MINUTES = 1
    MAX_HOURS = 720
    MAX_MINUTES = MAX_HOURS * 60  # 43200

    @classmethod
    def validate(cls, value_minutes: float) -> int:
        """
        校验并修正禁言时长（单位：分钟），返回修正后的整数分钟数。
        - 小于 1 分钟 → 取整为 1 分钟
        - 大于 720 小时（43200 分钟） → 取整为 43200 分钟
        """
        if value_minutes < cls.MIN_MINUTES:
            return cls.MIN_MINUTES
        if value_minutes > cls.MAX_MINUTES:
            return cls.MAX_MINUTES
        return int(value_minutes)


def apply_mute(duration_minutes: int, user_id: str = "test_user") -> dict:
    """
    模拟设置禁言的接口函数。
    返回包含修正后时长和状态的结果字典。
    """
    corrected = MuteDurationValidator.validate(duration_minutes)
    return {
        "user_id": user_id,
        "duration_minutes": corrected,
        "status": "success",
    }


# ── 测试用例 ──


class TestMuteDurationCustomRange:

    def test_zero_minutes_clamped_to_one(self):
        """0 分钟自动取整为 1 分钟"""
        result = apply_mute(0)
        assert result["duration_minutes"] == 1
        assert result["status"] == "success"

    def test_negative_minutes_clamped_to_one(self):
        """负数分钟自动取整为 1 分钟"""
        result = apply_mute(-10)
        assert result["duration_minutes"] == 1

    def test_seventy_two_one_hours_clamped_to_seventy_two_zero(self):
        """721 小时自动取整为 720 小时"""
        result = apply_mute(721 * 60)
        assert result["duration_minutes"] == 720 * 60
        assert result["status"] == "success"

    def test_thirty_days_normal(self):
        """30 天（720 小时）正常设置"""
        result = apply_mute(30 * 24 * 60)  # 720 小时 = 43200 分钟
        assert result["duration_minutes"] == 43200
        assert result["status"] == "success"

    def test_boundary_one_minute(self):
        """边界值：1 分钟正常设置"""
        result = apply_mute(1)
        assert result["duration_minutes"] == 1

    def test_boundary_max_minutes(self):
        """边界值：43200 分钟（720 小时）正常设置"""
        result = apply_mute(43200)
        assert result["duration_minutes"] == 43200

    def test_response_time_under_two_seconds(self):
        """响应时间 ≤ 2 秒"""
        start = time.perf_counter()
        apply_mute(12345)
        elapsed = time.perf_counter() - start
        assert elapsed < 2.0, f"响应耗时 {elapsed:.4f}s，超过 2 秒上限"
