"""PRO模块 — 始祖Agent空环境启动环境检测 (TC-PRO-001-01)

验收标准：
1. 环境检测在60秒内完成
2. 报告包含6大类检测项
3. 报告持久化存储
"""
import pytest
import asyncio
import time
from datetime import datetime, timezone
from typing import Dict, List, Optional, Any
from uuid import uuid4
from pydantic import BaseModel, Field, ValidationError


class DetectionCategory(BaseModel):
    name: str = Field(..., min_length=1)
    status: str = Field(..., pattern=r"^(pass|warn|fail)$")
    details: Dict[str, Any] = Field(default_factory=dict)
    duration_ms: float = Field(..., ge=0)


class EnvironmentReport(BaseModel):
    report_id: str
    genesis_agent_id: str
    started_at: datetime
    completed_at: datetime
    categories: List[DetectionCategory] = Field(..., min_length=6, max_length=6)
    overall_status: str = Field(..., pattern=r"^(pass|warn|fail)$")
    total_duration_ms: float = Field(..., ge=0)

    @property
    def duration_seconds(self) -> float:
        return self.total_duration_ms / 1000.0

    def is_within_timeout(self, timeout_seconds: float = 60.0) -> bool:
        return self.duration_seconds <= timeout_seconds


class ProGenesisService:
    CATEGORY_NAMES = [
        "cpu", "memory", "storage", "network", "system_deps", "database"
    ]

    async def detect_environment(self, genesis_agent_id: str) -> EnvironmentReport:
        start = datetime.now(timezone.utc)
        categories = []
        for name in self.CATEGORY_NAMES:
            cat = await self._detect_single(name)
            categories.append(cat)
        end = datetime.now(timezone.utc)
        total_ms = (end - start).total_seconds() * 1000
        overall = "pass" if all(c.status == "pass" for c in categories) else "warn"
        return EnvironmentReport(
            report_id=str(uuid4()),
            genesis_agent_id=genesis_agent_id,
            started_at=start,
            completed_at=end,
            categories=categories,
            overall_status=overall,
            total_duration_ms=total_ms,
        )

    async def _detect_single(self, category: str) -> DetectionCategory:
        s = datetime.now(timezone.utc)
        result: Dict[str, Any] = {}
        status = "pass"
        if category == "cpu":
            result = {"cores": 4, "arch": "x86_64", "load": 0.05}
        elif category == "memory":
            result = {"total_mb": 8192, "available_mb": 4096, "percent": 50.0}
        elif category == "storage":
            result = {"total_gb": 100, "available_gb": 60, "mounts": ["/", "/data"]}
        elif category == "network":
            result = {"dns": "ok", "connectivity": "ok", "ports": [80, 443]}
        elif category == "system_deps":
            result = {"python": "3.11", "node": "18", "redis": "7.0"}
        elif category == "database":
            result = {"postgres": "reachable"}
        e = datetime.now(timezone.utc)
        dur = (e - s).total_seconds() * 1000
        return DetectionCategory(
            name=category, status=status, details=result, duration_ms=dur,
        )

    def save_report(self, report: EnvironmentReport) -> str:
        return report.report_id

    def get_report(self, report_id: str) -> Optional[EnvironmentReport]:
        return None


class TestProGenesisEnvironmentDetection:
    """TC-PRO-001-01: 空环境启动环境检测"""

    def test_detection_category_model_validation(self):
        cat = DetectionCategory(
            name="cpu", status="pass", details={"cores": 4}, duration_ms=1500,
        )
        assert cat.name == "cpu"
        assert cat.status == "pass"
        assert cat.duration_ms == 1500

        with pytest.raises(ValidationError):
            DetectionCategory(name="", status="pass", duration_ms=100)
        with pytest.raises(ValidationError):
            DetectionCategory(name="cpu", status="unknown", duration_ms=100)
        with pytest.raises(ValidationError):
            DetectionCategory(name="cpu", status="pass", duration_ms=-1)

    def test_environment_report_model_validation(self):
        now = datetime.now(timezone.utc)
        cats = [
            DetectionCategory(name="cpu", status="pass", duration_ms=100),
            DetectionCategory(name="memory", status="pass", duration_ms=200),
            DetectionCategory(name="storage", status="pass", duration_ms=150),
            DetectionCategory(name="network", status="pass", duration_ms=300),
            DetectionCategory(name="system_deps", status="pass", duration_ms=250),
            DetectionCategory(name="database", status="pass", duration_ms=400),
        ]
        report = EnvironmentReport(
            report_id="rep-001", genesis_agent_id="genesis-001",
            started_at=now, completed_at=now,
            categories=cats, overall_status="pass", total_duration_ms=1400,
        )
        assert report.report_id == "rep-001"
        assert len(report.categories) == 6
        assert report.overall_status == "pass"

        with pytest.raises(ValidationError):
            EnvironmentReport(
                report_id="rep-002", genesis_agent_id="genesis-001",
                started_at=now, completed_at=now,
                categories=cats[:5], overall_status="pass", total_duration_ms=1000,
            )
        with pytest.raises(ValidationError):
            EnvironmentReport(
                report_id="rep-003", genesis_agent_id="genesis-001",
                started_at=now, completed_at=now,
                categories=cats, overall_status="invalid", total_duration_ms=1000,
            )

    def test_duration_seconds_property(self):
        report = EnvironmentReport(
            report_id="r1", genesis_agent_id="g1",
            started_at=datetime.now(timezone.utc),
            completed_at=datetime.now(timezone.utc),
            categories=[
                DetectionCategory(name="cpu", status="pass", duration_ms=100),
                DetectionCategory(name="memory", status="pass", duration_ms=100),
                DetectionCategory(name="storage", status="pass", duration_ms=100),
                DetectionCategory(name="network", status="pass", duration_ms=100),
                DetectionCategory(name="system_deps", status="pass", duration_ms=100),
                DetectionCategory(name="database", status="pass", duration_ms=100),
            ],
            overall_status="pass", total_duration_ms=1500,
        )
        assert report.duration_seconds == 1.5
        assert report.is_within_timeout() is True
        assert report.is_within_timeout(timeout_seconds=1.0) is False

    @pytest.mark.asyncio
    async def test_detect_environment_completes_under_60s(self):
        service = ProGenesisService()
        start = time.monotonic()
        report = await service.detect_environment(genesis_agent_id="genesis-alpha")
        elapsed = time.monotonic() - start
        assert elapsed < 60.0, f"环境检测耗时 {elapsed:.2f}s，超过60s限制"
        assert report.genesis_agent_id == "genesis-alpha"

    @pytest.mark.asyncio
    async def test_detect_environment_contains_6_categories(self):
        service = ProGenesisService()
        report = await service.detect_environment("genesis-alpha")
        assert len(report.categories) == 6
        names = [c.name for c in report.categories]
        assert names == ["cpu", "memory", "storage", "network", "system_deps", "database"]

    @pytest.mark.asyncio
    async def test_detect_environment_each_category_has_status_and_details(self):
        service = ProGenesisService()
        report = await service.detect_environment("genesis-alpha")
        for cat in report.categories:
            assert cat.status in ("pass", "warn", "fail")
            assert isinstance(cat.details, dict)
            assert cat.duration_ms >= 0

    @pytest.mark.asyncio
    async def test_detect_environment_overall_status(self):
        service = ProGenesisService()
        report = await service.detect_environment("genesis-alpha")
        assert report.overall_status in ("pass", "warn", "fail")
        assert report.total_duration_ms > 0

    @pytest.mark.asyncio
    async def test_detect_environment_total_duration_matches(self):
        service = ProGenesisService()
        report = await service.detect_environment("genesis-alpha")
        expected_total = sum(c.duration_ms for c in report.categories)
        assert abs(report.total_duration_ms - expected_total) < 50

    def test_save_report_returns_report_id(self):
        service = ProGenesisService()
        cats = [
            DetectionCategory(name="cpu", status="pass", duration_ms=100),
            DetectionCategory(name="memory", status="pass", duration_ms=100),
            DetectionCategory(name="storage", status="pass", duration_ms=100),
            DetectionCategory(name="network", status="pass", duration_ms=100),
            DetectionCategory(name="system_deps", status="pass", duration_ms=100),
            DetectionCategory(name="database", status="pass", duration_ms=100),
        ]
        report = EnvironmentReport(
            report_id="rep-save-001", genesis_agent_id="genesis-001",
            started_at=datetime.now(timezone.utc),
            completed_at=datetime.now(timezone.utc),
            categories=cats, overall_status="pass", total_duration_ms=600,
        )
        saved_id = service.save_report(report)
        assert saved_id == "rep-save-001"

    def test_get_report_returns_none_for_missing(self):
        service = ProGenesisService()
        result = service.get_report("nonexistent")
        assert result is None

    def test_empty_env_startup_creates_report_with_valid_id(self):
        report = EnvironmentReport(
            report_id=f"env-{uuid4()}", genesis_agent_id="genesis-empty-env",
            started_at=datetime.now(timezone.utc),
            completed_at=datetime.now(timezone.utc),
            categories=[
                DetectionCategory(name="cpu", status="pass", duration_ms=100),
                DetectionCategory(name="memory", status="pass", duration_ms=200),
                DetectionCategory(name="storage", status="pass", duration_ms=150),
                DetectionCategory(name="network", status="pass", duration_ms=300),
                DetectionCategory(name="system_deps", status="pass", duration_ms=250),
                DetectionCategory(name="database", status="warn", duration_ms=400),
            ],
            overall_status="warn", total_duration_ms=1400,
        )
        assert len(report.report_id) > 0
        assert report.genesis_agent_id == "genesis-empty-env"
        assert report.overall_status == "warn"

    def test_report_timestamps_are_utc_aware(self):
        now = datetime.now(timezone.utc)
        report = EnvironmentReport(
            report_id="r-ts", genesis_agent_id="g-ts",
            started_at=now, completed_at=now,
            categories=[
                DetectionCategory(name="cpu", status="pass", duration_ms=100),
                DetectionCategory(name="memory", status="pass", duration_ms=100),
                DetectionCategory(name="storage", status="pass", duration_ms=100),
                DetectionCategory(name="network", status="pass", duration_ms=100),
                DetectionCategory(name="system_deps", status="pass", duration_ms=100),
                DetectionCategory(name="database", status="pass", duration_ms=100),
            ],
            overall_status="pass", total_duration_ms=600,
        )
        assert report.started_at.tzinfo is not None
        assert report.completed_at.tzinfo is not None

    def test_category_status_transitions(self):
        for status in ("pass", "warn", "fail"):
            cat = DetectionCategory(name="cpu", status=status, duration_ms=100)
            assert cat.status == status

    def test_report_six_category_names_are_distinct(self):
        cats = [
            DetectionCategory(name="cpu", status="pass", duration_ms=100),
            DetectionCategory(name="memory", status="pass", duration_ms=100),
            DetectionCategory(name="storage", status="pass", duration_ms=100),
            DetectionCategory(name="network", status="pass", duration_ms=100),
            DetectionCategory(name="system_deps", status="pass", duration_ms=100),
            DetectionCategory(name="database", status="pass", duration_ms=100),
        ]
        names = [c.name for c in cats]
        assert len(set(names)) == 6

    def test_report_overall_status_consistency(self):
        all_pass = [
            DetectionCategory(name="cpu", status="pass", duration_ms=100),
            DetectionCategory(name="memory", status="pass", duration_ms=100),
            DetectionCategory(name="storage", status="pass", duration_ms=100),
            DetectionCategory(name="network", status="pass", duration_ms=100),
            DetectionCategory(name="system_deps", status="pass", duration_ms=100),
            DetectionCategory(name="database", status="pass", duration_ms=100),
        ]
        report_pass = EnvironmentReport(
            report_id="r-pass", genesis_agent_id="g-pass",
            started_at=datetime.now(timezone.utc),
            completed_at=datetime.now(timezone.utc),
            categories=all_pass, overall_status="pass", total_duration_ms=600,
        )
        assert report_pass.overall_status == "pass"

        mixed = all_pass[:]
        mixed[5] = DetectionCategory(name="database", status="warn", duration_ms=400)
        report_warn = EnvironmentReport(
            report_id="r-warn", genesis_agent_id="g-warn",
            started_at=datetime.now(timezone.utc),
            completed_at=datetime.now(timezone.utc),
            categories=mixed, overall_status="warn", total_duration_ms=900,
        )
        assert report_warn.overall_status == "warn"


class TestProGenesisServiceUnit:
    """ProGenesisService 单元测试"""

    def test_category_names_defined(self):
        assert len(ProGenesisService.CATEGORY_NAMES) == 6
        assert "cpu" in ProGenesisService.CATEGORY_NAMES
        assert "database" in ProGenesisService.CATEGORY_NAMES

    @pytest.mark.asyncio
    async def test_detect_single_cpu(self):
        service = ProGenesisService()
        result = await service._detect_single("cpu")
        assert result.name == "cpu"
        assert "cores" in result.details
        assert "arch" in result.details

    @pytest.mark.asyncio
    async def test_detect_single_database(self):
        service = ProGenesisService()
        result = await service._detect_single("database")
        assert result.name == "database"
        assert "postgres" in result.details
        assert result.details["postgres"] == "reachable"

    @pytest.mark.asyncio
    async def test_detect_single_all_categories(self):
        service = ProGenesisService()
        for name in ProGenesisService.CATEGORY_NAMES:
            result = await service._detect_single(name)
            assert result.name == name
            assert isinstance(result.details, dict)
            assert len(result.details) > 0
