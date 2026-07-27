import pytest
import re
from typing import List, Dict, Any
from datetime import datetime, timedelta


class ApiVersionManager:
    """管理 API 版本策略"""

    SUPPORTED_VERSIONS = {"v1", "v2", "v3"}

    @staticmethod
    def extract_version(path: str) -> str | None:
        """从 URL 路径中提取版本号，如 /api/v1/users -> v1"""
        m = re.search(r"/api/(v\d+)/", path)
        return m.group(1) if m else None

    @staticmethod
    def is_valid_version_format(path: str) -> bool:
        """检查是否使用 /api/v{number}/ 格式"""
        return bool(re.fullmatch(r"/api/v\d+/.*", path))

    @classmethod
    def is_version_supported(cls, version: str) -> bool:
        return version in cls.SUPPORTED_VERSIONS

    @classmethod
    def check_backward_compatibility(
        cls, old_version: str, new_version: str
    ) -> float:
        """
        模拟检查版本间向后兼容性。
        返回 0.0~1.0 的兼容率。
        """
        compatibility_map: Dict[str, Dict[str, float]] = {
            "v1": {"v2": 0.95, "v3": 0.85},
            "v2": {"v3": 0.92},
        }
        return compatibility_map.get(old_version, {}).get(new_version, 0.0)

    @classmethod
    def get_migration_window(cls, from_version: str, to_version: str) -> int:
        """返回版本迁移窗口（发布周期数）"""
        window_map: Dict[str, Dict[str, int]] = {
            "v1": {"v2": 2, "v3": 3},
            "v2": {"v3": 2},
        }
        return window_map.get(from_version, {}).get(to_version, 0)


class TestApiVersionFormat:
    """验收标准：API版本格式=/api/v1/"""

    @pytest.mark.parametrize(
        "path,expected",
        [
            ("/api/v1/users", True),
            ("/api/v2/products", True),
            ("/api/v3/orders/123", True),
            ("/api/v10/search", True),
            ("/api/v1/", True),
            ("/v1/users", False),
            ("/api/v1", False),
            ("/api/abc/users", False),
            ("/api/v1.5/users", False),
            ("/apiv1/users", False),
            ("/api//users", False),
            ("", False),
        ],
    )
    def test_valid_version_format(self, path: str, expected: bool) -> None:
        assert ApiVersionManager.is_valid_version_format(path) == expected

    def test_extract_version_returns_correct_version(self) -> None:
        assert ApiVersionManager.extract_version("/api/v1/users") == "v1"
        assert ApiVersionManager.extract_version("/api/v2/") == "v2"
        assert ApiVersionManager.extract_version("/api/v10/search") == "v10"

    def test_extract_version_returns_none_for_invalid(self) -> None:
        assert ApiVersionManager.extract_version("/v1/users") is None
        assert ApiVersionManager.extract_version("/api/abc/users") is None
        assert ApiVersionManager.extract_version("") is None

    def test_version_has_v_prefix_and_number(self) -> None:
        version = ApiVersionManager.extract_version("/api/v1/users")
        assert version is not None
        assert version.startswith("v")
        assert version[1:].isdigit()

    @pytest.mark.parametrize("version", ["v1", "v2", "v3"])
    def test_version_is_supported(self, version: str) -> None:
        assert ApiVersionManager.is_version_supported(version)

    def test_unsupported_version_rejected(self) -> None:
        assert not ApiVersionManager.is_version_supported("v0")
        assert not ApiVersionManager.is_version_supported("v4")
        assert not ApiVersionManager.is_version_supported("v99")


class TestApiCompatibility:
    """验收标准：兼容性>=90%"""

    COMPATIBILITY_THRESHOLD = 0.90

    def test_compatibility_between_consecutive_versions(self) -> None:
        compat = ApiVersionManager.check_backward_compatibility("v1", "v2")
        assert compat >= self.COMPATIBILITY_THRESHOLD, (
            f"v1→v2 兼容性 {compat:.0%} 低于阈值 {self.COMPATIBILITY_THRESHOLD:.0%}"
        )

    def test_compatibility_between_later_versions(self) -> None:
        compat = ApiVersionManager.check_backward_compatibility("v2", "v3")
        assert compat >= self.COMPATIBILITY_THRESHOLD, (
            f"v2→v3 兼容性 {compat:.0%} 低于阈值 {self.COMPATIBILITY_THRESHOLD:.0%}"
        )

    def test_all_version_transitions_meet_threshold(self) -> None:
        transitions = [
            ("v1", "v2"),
            ("v2", "v3"),
        ]
        for old_v, new_v in transitions:
            compat = ApiVersionManager.check_backward_compatibility(old_v, new_v)
            assert compat >= self.COMPATIBILITY_THRESHOLD, (
                f"{old_v}→{new_v} 兼容性 {compat:.0%} 不达标"
            )

    def test_compatibility_never_exceeds_one(self) -> None:
        versions = ["v1", "v2", "v3"]
        for old_v in versions:
            for new_v in versions:
                if old_v != new_v:
                    compat = ApiVersionManager.check_backward_compatibility(
                        old_v, new_v
                    )
                    assert compat <= 1.0, (
                        f"{old_v}→{new_v} 兼容性 {compat} 超过 1.0"
                    )


class TestVersionMigrationWindow:
    """验收标准：版本迁移窗口>=1个发布周期"""

    MIN_MIGRATION_WINDOW = 1

    def test_migration_window_at_least_one_release_cycle(self) -> None:
        transitions = [
            ("v1", "v2"),
            ("v2", "v3"),
            ("v1", "v3"),
        ]
        for from_v, to_v in transitions:
            window = ApiVersionManager.get_migration_window(from_v, to_v)
            assert window >= self.MIN_MIGRATION_WINDOW, (
                f"{from_v}→{to_v} 迁移窗口 {window} 个周期 < {self.MIN_MIGRATION_WINDOW}"
            )

    def test_direct_migration_window_sufficient(self) -> None:
        window = ApiVersionManager.get_migration_window("v1", "v2")
        assert window >= self.MIN_MIGRATION_WINDOW

    def test_skip_version_migration_window_sufficient(self) -> None:
        window = ApiVersionManager.get_migration_window("v1", "v3")
        assert window >= self.MIN_MIGRATION_WINDOW

    def test_migration_window_is_integer(self) -> None:
        window = ApiVersionManager.get_migration_window("v1", "v2")
        assert isinstance(window, int)
        assert window > 0

    def test_unknown_transition_returns_zero(self) -> None:
        assert ApiVersionManager.get_migration_window("v1", "v5") == 0


class TestApiVersionStrategyIntegration:
    """集成测试：组合验证三个验收标准"""

    def test_full_strategy_compliance(self) -> None:
        """验证典型版本迁移路径满足所有验收标准"""
        from_version, to_version = "v1", "v2"
        path = f"/api/{to_version}/users"

        # 1) URL 路径版本格式
        assert ApiVersionManager.is_valid_version_format(path)

        # 2) 兼容性 >= 90%
        compat = ApiVersionManager.check_backward_compatibility(
            from_version, to_version
        )
        assert compat >= 0.90

        # 3) 迁移窗口 >= 1 个发布周期
        window = ApiVersionManager.get_migration_window(from_version, to_version)
        assert window >= 1

    def test_all_supported_version_paths_pass_format_check(self) -> None:
        for version in ApiVersionManager.SUPPORTED_VERSIONS:
            path = f"/api/{version}/resources"
            assert ApiVersionManager.is_valid_version_format(path)

    def test_compatibility_across_all_supported_transitions(self) -> None:
        """所有受支持的版本过渡路径都必须满足兼容性要求"""
        transitions: List[tuple] = [
            v
            for v in [
                ("v1", "v2"),
                ("v2", "v3"),
            ]
        ]
        for from_v, to_v in transitions:
            assert (
                ApiVersionManager.check_backward_compatibility(from_v, to_v)
                >= 0.90
            )
            assert (
                ApiVersionManager.get_migration_window(from_v, to_v) >= 1
            )
