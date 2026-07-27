import time
import pytest


class MuteDurationValidator:
    """禁言时长校验器：支持 1 分钟 ~ 720 小时范围的自定义输入"""

    MIN_MINUTES = 1
    MAX_HOURS = 720
    MAX_MINUTES = MAX_HOURS * 60  # 43200

    @classmethod
    def validate(cls, value_minutes: float) -> int:
        """校验并修正禁言时长（单位：分钟），返回修正后的整数分钟数。
        - 小于 1 分钟 → 取整为 1 分钟
        - 大于 720 小时（43200 分钟） → 取整为 43200 分钟
        """
        if value_minutes < cls.MIN_MINUTES:
            return cls.MIN_MINUTES
        if value_minutes > cls.MAX_MINUTES:
            return cls.MAX_MINUTES
        return int(value_minutes)


class MockMuteService:
    """模拟禁言服务，封装禁言时长的校验与设置逻辑。"""

    def __init__(self):
        self.mute_records: list[dict] = []

    def apply_mute(self, user_id: str, duration_minutes: float) -> dict:
        """对指定用户设置禁言，时长自动修正后返回结果。"""
        corrected = MuteDurationValidator.validate(duration_minutes)
        record = {
            "user_id": user_id,
            "duration_minutes": corrected,
            "status": "success",
            "timestamp": time.time(),
        }
        self.mute_records.append(record)
        return record

    def get_active_mute(self, user_id: str) -> dict | None:
        """查询指定用户的当前禁言记录。"""
        for record in self.mute_records:
            if record["user_id"] == user_id and record["status"] == "success":
                return record
        return None

    def clear_mutes(self):
        """清空所有禁言记录（测试辅助用）。"""
        self.mute_records.clear()


@pytest.fixture
def mute_service():
    return MockMuteService()


class TestMuteDurationCustomRange:
    """禁言时长自定义范围验证——验收测试"""

    # ── AC1：0 分钟自动取整为 1 分钟 ──

    def test_zero_minutes_clamped_to_one(self, mute_service):
        """AC1: 0 分钟自动取整为 1 分钟"""
        result = mute_service.apply_mute("user_001", 0)
        assert result["duration_minutes"] == MuteDurationValidator.MIN_MINUTES
        assert result["status"] == "success"

    def test_zero_point_five_minutes_clamped_to_one(self, mute_service):
        """AC1 edge: 0.5 分钟自动取整为 1 分钟"""
        result = mute_service.apply_mute("user_002", 0.5)
        assert result["duration_minutes"] == 1

    def test_negative_minutes_clamped_to_one(self, mute_service):
        """AC1 edge: 负数分钟自动取整为 1 分钟"""
        result = mute_service.apply_mute("user_003", -100)
        assert result["duration_minutes"] == 1

    def test_negative_float_clamped_to_one(self, mute_service):
        """AC1 edge: 负浮点数自动取整为 1 分钟"""
        result = mute_service.apply_mute("user_004", -0.001)
        assert result["duration_minutes"] == 1

    # ── AC2：721 小时自动取整为 720 小时 ──

    def test_721_hours_clamped_to_720(self, mute_service):
        """AC2: 721 小时自动取整为 720 小时"""
        result = mute_service.apply_mute("user_010", 721 * 60)
        assert result["duration_minutes"] == 720 * 60
        assert result["status"] == "success"

    def test_1000_hours_clamped_to_720(self, mute_service):
        """AC2 edge: 1000 小时自动取整为 720 小时"""
        result = mute_service.apply_mute("user_011", 1000 * 60)
        assert result["duration_minutes"] == 720 * 60

    def test_43201_minutes_clamped_to_43200(self, mute_service):
        """AC2 edge: 43201 分钟（略超 720h）取整为 43200"""
        result = mute_service.apply_mute("user_012", 43201)
        assert result["duration_minutes"] == 43200

    def test_float_overflow_clamped_to_max(self, mute_service):
        """AC2 edge: 720.5 小时浮点数取整为 43200 分钟"""
        result = mute_service.apply_mute("user_013", 720.5 * 60)
        assert result["duration_minutes"] == 43200

    def test_hugely_excessive_clamped_to_max(self, mute_service):
        """AC2 edge: 极大值（999999 分钟）取整为 43200"""
        result = mute_service.apply_mute("user_014", 999999)
        assert result["duration_minutes"] == 43200

    # ── AC3：30 天（720 小时）正常设置 ──

    def test_thirty_days_normal(self, mute_service):
        """AC3: 30 天（720 小时）正常设置"""
        result = mute_service.apply_mute("user_020", 30 * 24 * 60)
        assert result["duration_minutes"] == 43200
        assert result["status"] == "success"

    def test_max_boundary_exact(self, mute_service):
        """AC3 boundary: 精确 43200 分钟（720h）正常设置"""
        result = mute_service.apply_mute("user_021", 43200)
        assert result["duration_minutes"] == 43200

    def test_one_minute_normal(self, mute_service):
        """AC3 boundary: 最小有效值 1 分钟正常设置"""
        result = mute_service.apply_mute("user_022", 1)
        assert result["duration_minutes"] == 1

    def test_one_hour_normal(self, mute_service):
        """AC3 intermediate: 1 小时正常设置"""
        result = mute_service.apply_mute("user_023", 60)
        assert result["duration_minutes"] == 60

    def test_24_hours_normal(self, mute_service):
        """AC3 intermediate: 24 小时正常设置"""
        result = mute_service.apply_mute("user_024", 24 * 60)
        assert result["duration_minutes"] == 1440

    def test_15_days_normal(self, mute_service):
        """AC3 intermediate: 15 天（360h）正常设置"""
        result = mute_service.apply_mute("user_025", 15 * 24 * 60)
        assert result["duration_minutes"] == 21600

    def test_valid_integer_values_are_preserved(self, mute_service):
        """AC3: 有效整数时长精确保持不被修正"""
        valid_values = [1, 5, 10, 30, 60, 120, 360, 1440, 4320, 10080, 43200]
        for i, minutes in enumerate(valid_values):
            result = mute_service.apply_mute(f"user_vld_{i:03d}", minutes)
            assert result["duration_minutes"] == minutes, (
                f"Valid duration {minutes} min was modified to {result['duration_minutes']}"
            )

    # ── AC4：响应时间 ≤ 2 秒 ──

    def test_response_time_within_2_seconds(self, mute_service):
        """AC4: 禁言时长校验响应时间 ≤ 2 秒"""
        start = time.perf_counter()
        for user_id in [f"user_perf_{i:03d}" for i in range(100)]:
            mute_service.apply_mute(user_id, 30)
        elapsed = time.perf_counter() - start
        assert elapsed < 2.0, f"Bulk (100 calls) response took {elapsed:.4f}s, exceeds 2s limit"

    def test_single_call_response_time_within_2_seconds(self, mute_service):
        """AC4 single: 单次校验响应时间 ≤ 2 秒"""
        start = time.perf_counter()
        mute_service.apply_mute("user_perf_single", 12345)
        elapsed = time.perf_counter() - start
        assert elapsed < 2.0, f"Single call response took {elapsed:.6f}s, exceeds 2s limit"

    # ── 附加：模拟 API 层响应时间验证 ──

    def test_mute_service_record_is_stored(self, mute_service):
        """禁言记录被正确存储"""
        result = mute_service.apply_mute("user_record_001", 60)
        assert result["duration_minutes"] == 60
        record = mute_service.get_active_mute("user_record_001")
        assert record is not None
        assert record["user_id"] == "user_record_001"
        assert record["duration_minutes"] == 60

    def test_mute_service_clear(self, mute_service):
        """清空记录后查询不到原禁言"""
        mute_service.apply_mute("user_clear_001", 30)
        assert mute_service.get_active_mute("user_clear_001") is not None
        mute_service.clear_mutes()
        assert mute_service.get_active_mute("user_clear_001") is None

    def test_multiple_users_independent(self, mute_service):
        """多个用户的禁言互不影响"""
        for i in range(20):
            mute_service.apply_mute(f"user_indep_{i:03d}", i + 1)
        for i in range(20):
            record = mute_service.get_active_mute(f"user_indep_{i:03d}")
            assert record is not None
            assert record["duration_minutes"] == i + 1


class TestMuteDurationValidatorUnit:
    """MuteDurationValidator 单元测试——纯逻辑验证"""

    def test_validate_exact_min(self):
        assert MuteDurationValidator.validate(1) == 1

    def test_validate_exact_max(self):
        assert MuteDurationValidator.validate(43200) == 43200

    def test_validate_below_min_clamped(self):
        assert MuteDurationValidator.validate(0) == 1

    def test_validate_above_max_clamped(self):
        assert MuteDurationValidator.validate(43300) == 43200

    def test_validate_return_type_is_int(self):
        result = MuteDurationValidator.validate(5.7)
        assert isinstance(result, int)
        assert result == 5

    def test_validate_decimal_input(self):
        assert MuteDurationValidator.validate(30.9) == 30

    def test_validate_zero_input_type_preserved(self):
        result = MuteDurationValidator.validate(0.0)
        assert isinstance(result, int)
        assert result == 1
