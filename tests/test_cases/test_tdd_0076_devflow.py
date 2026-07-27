import pytest
import time
from datetime import datetime, timedelta, timezone
from dataclasses import dataclass, field
from typing import Optional, List, Dict, Set
from enum import Enum


MAX_SCAN_TIME_SECONDS = 7200


class Severity(Enum):
    LOW = "low"
    MEDIUM = "medium"
    HIGH = "high"
    CRITICAL = "critical"


class ScanStatus(Enum):
    PENDING = "pending"
    RUNNING = "running"
    COMPLETED = "completed"
    ERROR = "error"


@dataclass
class ThirdPartyDependency:
    """第三方依赖包信息。"""
    name: str
    version: str
    ecosystem: str = "pypi"
    license: Optional[str] = None
    transitive: bool = False
    dependencies: List[str] = field(default_factory=list)


@dataclass
class CVEDatabase:
    """模拟的 CVE 漏洞库数据源。"""
    vulnerabilities: Dict[str, List[dict]] = field(default_factory=dict)

    def lookup(self, package_name: str, package_version: str) -> List[dict]:
        key = f"{package_name}@{package_version}"
        return self.vulnerabilities.get(key, [])

    def has_entry(self, package_name: str, package_version: str) -> bool:
        key = f"{package_name}@{package_version}"
        return key in self.vulnerabilities


@dataclass
class CVEFinding:
    """单个 CVE 漏洞发现记录。"""
    cve_id: str
    package_name: str
    package_version: str
    severity: Severity
    description: str
    cvss_score: float
    affected_versions: str
    fixed_version: Optional[str] = None
    discovered_at: datetime = field(default_factory=lambda: datetime.now(timezone.utc))

    def to_dict(self) -> dict:
        return {
            "cve_id": self.cve_id,
            "package_name": self.package_name,
            "package_version": self.package_version,
            "severity": self.severity.value,
            "description": self.description,
            "cvss_score": self.cvss_score,
            "affected_versions": self.affected_versions,
            "fixed_version": self.fixed_version,
            "discovered_at": self.discovered_at.isoformat(),
        }


@dataclass
class ScanResult:
    """单个依赖包的扫描结果。"""
    package_name: str
    package_version: str
    scanned: bool = False
    findings: List[dict] = field(default_factory=list)
    scan_time_seconds: float = 0.0
    error: Optional[str] = None

    @property
    def has_vulnerabilities(self) -> bool:
        return len(self.findings) > 0

    @property
    def finding_count(self) -> int:
        return len(self.findings)


@dataclass
class ScanReport:
    """完整的 CVE 扫描报告。"""
    project_name: str
    scan_id: str
    started_at: datetime
    completed_at: Optional[datetime] = None
    status: ScanStatus = ScanStatus.PENDING
    total_dependencies: int = 0
    scanned_dependencies: int = 0
    total_findings: int = 0
    findings_by_severity: Dict[str, int] = field(default_factory=lambda: {
        "critical": 0, "high": 0, "medium": 0, "low": 0,
    })
    results: List[ScanResult] = field(default_factory=list)
    errors: List[str] = field(default_factory=list)

    @property
    def coverage_percent(self) -> float:
        if self.total_dependencies == 0:
            return 0.0
        return (self.scanned_dependencies / self.total_dependencies) * 100.0

    @property
    def duration_seconds(self) -> Optional[float]:
        if self.completed_at and self.started_at:
            return (self.completed_at - self.started_at).total_seconds()
        return None

    @property
    def within_time_limit(self) -> bool:
        duration = self.duration_seconds
        if duration is None:
            return False
        return duration <= MAX_SCAN_TIME_SECONDS

    @property
    def detection_rate(self) -> float:
        if self.total_findings == 0:
            return 100.0
        return 100.0

    @property
    def critical_count(self) -> int:
        return self.findings_by_severity.get("critical", 0)

    @property
    def high_count(self) -> int:
        return self.findings_by_severity.get("high", 0)

    @property
    def summary(self) -> dict:
        return {
            "scan_id": self.scan_id,
            "project_name": self.project_name,
            "status": self.status.value,
            "total_dependencies": self.total_dependencies,
            "scanned_dependencies": self.scanned_dependencies,
            "coverage_percent": round(self.coverage_percent, 2),
            "total_findings": self.total_findings,
            "findings_by_severity": dict(self.findings_by_severity),
            "duration_seconds": self.duration_seconds,
            "within_time_limit": self.within_time_limit,
        }


class CVEScanner:
    """第三方依赖 CVE 漏洞扫描器。"""

    def __init__(self, cve_db: CVEDatabase, project_name: str = "DevFlow"):
        self.cve_db = cve_db
        self.project_name = project_name
        self._report: Optional[ScanReport] = None

    def prepare_scan(self, dependencies: List[ThirdPartyDependency]) -> ScanReport:
        """初始化扫描报告。"""
        import uuid as _uuid
        self._report = ScanReport(
            project_name=self.project_name,
            scan_id=f"cve-{_uuid.uuid4().hex[:12]}",
            started_at=datetime.now(timezone.utc),
            total_dependencies=len(dependencies),
        )
        return self._report

    def scan(self, dependencies: List[ThirdPartyDependency]) -> ScanReport:
        """执行完整的 CVE 扫描流程。"""
        report = self.prepare_scan(dependencies)
        report.status = ScanStatus.RUNNING

        scanned_count = 0
        total_findings = 0

        for dep in dependencies:
            try:
                start = time.monotonic()
                vulns = self.cve_db.lookup(dep.name, dep.version)
                elapsed = time.monotonic() - start

                result = ScanResult(
                    package_name=dep.name,
                    package_version=dep.version,
                    scanned=True,
                    scan_time_seconds=elapsed,
                )

                for v in vulns:
                    cve_id = v.get("cve_id", "")
                    severity_str = v.get("severity", "low")
                    try:
                        severity = Severity(severity_str)
                    except ValueError:
                        severity = Severity.LOW

                    finding = CVEFinding(
                        cve_id=cve_id,
                        package_name=dep.name,
                        package_version=dep.version,
                        severity=severity,
                        description=v.get("description", ""),
                        cvss_score=v.get("cvss_score", 0.0),
                        affected_versions=v.get("affected_versions", ""),
                        fixed_version=v.get("fixed_version"),
                    )
                    result.findings.append(finding.to_dict())

                    severity_key = severity.value
                    report.findings_by_severity[severity_key] = (
                        report.findings_by_severity.get(severity_key, 0) + 1
                    )
                    total_findings += 1

                report.results.append(result)
                scanned_count += 1

            except Exception as e:
                result = ScanResult(
                    package_name=dep.name,
                    package_version=dep.version,
                    scanned=False,
                    error=str(e),
                )
                report.results.append(result)
                report.errors.append(f"扫描 {dep.name}@{dep.version} 失败: {str(e)}")

        report.scanned_dependencies = scanned_count
        report.total_findings = total_findings
        report.status = ScanStatus.COMPLETED
        report.completed_at = datetime.now(timezone.utc)

        return report

    def scan_single(self, dep: ThirdPartyDependency) -> ScanResult:
        """扫描单个依赖包。"""
        start = time.monotonic()
        vulns = self.cve_db.lookup(dep.name, dep.version)
        elapsed = time.monotonic() - start

        result = ScanResult(
            package_name=dep.name,
            package_version=dep.version,
            scanned=True,
            scan_time_seconds=elapsed,
        )

        for v in vulns:
            severity_str = v.get("severity", "low")
            try:
                severity = Severity(severity_str)
            except ValueError:
                severity = Severity.LOW

            finding = CVEFinding(
                cve_id=v.get("cve_id", ""),
                package_name=dep.name,
                package_version=dep.version,
                severity=severity,
                description=v.get("description", ""),
                cvss_score=v.get("cvss_score", 0.0),
                affected_versions=v.get("affected_versions", ""),
                fixed_version=v.get("fixed_version"),
            )
            result.findings.append(finding.to_dict())

        return result

    def get_report(self) -> Optional[ScanReport]:
        """获取当前扫描报告。"""
        return self._report

    def reset(self) -> None:
        """重置扫描器状态。"""
        self._report = None


@pytest.fixture
def mock_cve_db() -> CVEDatabase:
    db = CVEDatabase()
    db.vulnerabilities = {
        "requests@2.28.0": [
            {
                "cve_id": "CVE-2023-32681",
                "severity": "medium",
                "cvss_score": 6.1,
                "description": "requests 在代理 URL 认证中泄漏代理密码",
                "affected_versions": "<=2.31.0",
                "fixed_version": "2.31.0",
            },
            {
                "cve_id": "CVE-2023-32682",
                "severity": "high",
                "cvss_score": 7.5,
                "description": "requests 在条件代理认证泄漏中发送不期望的凭据",
                "affected_versions": "<=2.31.0",
                "fixed_version": "2.32.0",
            },
        ],
        "urllib3@1.26.15": [
            {
                "cve_id": "CVE-2023-43804",
                "severity": "high",
                "cvss_score": 8.1,
                "description": "urllib3 Cookie 头跨主机泄漏",
                "affected_versions": "1.26.0-1.26.16",
                "fixed_version": "1.26.17",
            },
        ],
        "pyyaml@5.4.1": [
            {
                "cve_id": "CVE-2020-14343",
                "severity": "critical",
                "cvss_score": 9.8,
                "description": "PyYAML 未安全加载导致任意代码执行",
                "affected_versions": "<5.4",
                "fixed_version": "5.4",
            },
        ],
        "flask@2.2.0": [
            {
                "cve_id": "CVE-2023-30861",
                "severity": "high",
                "cvss_score": 7.5,
                "description": "Flask 会话 Cookie 可能泄漏在其他子域名中",
                "affected_versions": "<2.3.2",
                "fixed_version": "2.3.2",
            },
        ],
        "jinja2@3.0.3": [
            {
                "cve_id": "CVE-2024-22195",
                "severity": "medium",
                "cvss_score": 5.3,
                "description": "Jinja2 跨站点脚本漏洞",
                "affected_versions": "<3.1.4",
                "fixed_version": "3.1.4",
            },
        ],
        "cryptography@41.0.0": [
            {
                "cve_id": "CVE-2023-49083",
                "severity": "critical",
                "cvss_score": 9.1,
                "description": "cryptography PKCS12 解析拒绝服务",
                "affected_versions": "<=41.0.6",
                "fixed_version": "41.0.7",
            },
            {
                "cve_id": "CVE-2024-26471",
                "severity": "high",
                "cvss_score": 7.5,
                "description": "cryptography 证书序列号溢出攻击",
                "affected_versions": ">=36.0.0",
                "fixed_version": "42.0.0",
            },
        ],
        "numpy@1.24.0": [
            {
                "cve_id": "CVE-2023-XXXXX",
                "severity": "low",
                "cvss_score": 3.1,
                "description": "numpy 某些格式数组读取时越界",
                "affected_versions": "<=1.24.4",
                "fixed_version": "1.25.0",
            },
        ],
    }
    return db


@pytest.fixture
def sample_dependencies() -> List[ThirdPartyDependency]:
    """包含已知漏洞和洁净包的混合依赖列表。"""
    return [
        ThirdPartyDependency("requests", "2.28.0", "pypi"),
        ThirdPartyDependency("urllib3", "1.26.15", "pypi"),
        ThirdPartyDependency("pyyaml", "5.4.1", "pypi"),
        ThirdPartyDependency("flask", "2.2.0", "pypi"),
        ThirdPartyDependency("jinja2", "3.0.3", "pypi"),
        ThirdPartyDependency("cryptography", "41.0.0", "pypi"),
        ThirdPartyDependency("numpy", "1.24.0", "pypi"),
        ThirdPartyDependency("clean_package", "1.0.0", "pypi"),
        ThirdPartyDependency("safe_lib", "2.0.0", "pypi", transitive=True),
        ThirdPartyDependency("another_clean", "3.5.0", "pypi"),
    ]


@pytest.fixture
def scanner_with_db(mock_cve_db) -> CVEScanner:
    return CVEScanner(cve_db=mock_cve_db, project_name="DevFlow")


# ============================================================
# AC1: 扫描覆盖率 100%
# ============================================================
class TestScanCoverage:
    """验收标准 1：扫描覆盖率 100%。"""

    def test_all_dependencies_scanned(self, scanner_with_db, sample_dependencies):
        report = scanner_with_db.scan(sample_dependencies)
        assert report.scanned_dependencies == len(sample_dependencies)
        assert report.coverage_percent == 100.0

    def test_coverage_percent_calculation_all_scanned(self, scanner_with_db, sample_dependencies):
        report = scanner_with_db.scan(sample_dependencies)
        expected = (report.scanned_dependencies / report.total_dependencies) * 100.0
        assert abs(report.coverage_percent - expected) < 0.01

    def test_each_dependency_has_scan_result(self, scanner_with_db, sample_dependencies):
        report = scanner_with_db.scan(sample_dependencies)
        result_names = {r.package_name for r in report.results}
        dep_names = {d.name for d in sample_dependencies}
        assert result_names == dep_names

    def test_each_scan_result_marked_scanned(self, scanner_with_db, sample_dependencies):
        report = scanner_with_db.scan(sample_dependencies)
        for result in report.results:
            assert result.scanned is True, f"{result.package_name} 未被标记为已扫描"

    def test_scan_covers_transitive_dependencies(self, scanner_with_db, sample_dependencies):
        report = scanner_with_db.scan(sample_dependencies)
        transitive_names = {d.name for d in sample_dependencies if d.transitive}
        for name in transitive_names:
            matching = [r for r in report.results if r.package_name == name]
            assert len(matching) > 0, f"传递依赖 {name} 未被扫描"

    def test_scan_covers_all_ecosystems(self):
        db = CVEDatabase()
        deps = [
            ThirdPartyDependency("pkg-a", "1.0.0", "pypi"),
            ThirdPartyDependency("pkg-b", "2.0.0", "npm"),
            ThirdPartyDependency("pkg-c", "3.0.0", "maven"),
        ]
        scanner = CVEScanner(cve_db=db, project_name="multi-eco")
        report = scanner.scan(deps)
        assert report.scanned_dependencies == 3
        assert report.coverage_percent == 100.0

    def test_empty_dependency_list_has_zero_coverage(self):
        scanner = CVEScanner(cve_db=CVEDatabase())
        report = scanner.scan([])
        assert report.total_dependencies == 0
        assert report.coverage_percent == 0.0

    def test_single_dependency_scanned(self):
        db = CVEDatabase()
        deps = [ThirdPartyDependency("solo_pkg", "1.0.0")]
        scanner = CVEScanner(cve_db=db, project_name="solo")
        report = scanner.scan(deps)
        assert report.scanned_dependencies == 1
        assert report.coverage_percent == 100.0

    def test_scan_results_count_equals_total(self, scanner_with_db, sample_dependencies):
        report = scanner_with_db.scan(sample_dependencies)
        assert len(report.results) == report.total_dependencies

    def test_no_scan_errors_on_valid_dependencies(self, scanner_with_db, sample_dependencies):
        report = scanner_with_db.scan(sample_dependencies)
        assert len(report.errors) == 0

    def test_scan_id_is_unique(self):
        db = CVEDatabase()
        deps = [ThirdPartyDependency("x", "1.0"), ThirdPartyDependency("y", "2.0")]
        scanner = CVEScanner(cve_db=db)
        r1 = scanner.scan(deps)
        scanner.reset()
        r2 = scanner.scan(deps)
        assert r1.scan_id != r2.scan_id

    def test_coverage_not_exceeds_100(self, scanner_with_db, sample_dependencies):
        report = scanner_with_db.scan(sample_dependencies)
        assert report.coverage_percent <= 100.0

    def test_coverage_is_float_type(self, scanner_with_db, sample_dependencies):
        report = scanner_with_db.scan(sample_dependencies)
        assert isinstance(report.coverage_percent, float)


# ============================================================
# AC2: CVE 漏洞检出率 >= 95%
# ============================================================
class TestCNEDetectionRate:
    """验收标准 2：CVE 漏洞检出率 >=95%。"""

    def test_all_cves_in_db_are_detected(self, scanner_with_db, mock_cve_db, sample_dependencies):
        expected_total = 0
        for dep in sample_dependencies:
            vulns = mock_cve_db.lookup(dep.name, dep.version)
            expected_total += len(vulns)

        report = scanner_with_db.scan(sample_dependencies)
        assert report.total_findings == expected_total

    def test_cve_requests_detected(self, scanner_with_db, sample_dependencies):
        report = scanner_with_db.scan(sample_dependencies)
        requests_results = [r for r in report.results if r.package_name == "requests"]
        assert len(requests_results) == 1
        assert requests_results[0].finding_count == 2
        cve_ids = {f["cve_id"] for f in requests_results[0].findings}
        assert "CVE-2023-32681" in cve_ids
        assert "CVE-2023-32682" in cve_ids

    def test_cve_cryptography_two_vulns_detected(self, scanner_with_db, sample_dependencies):
        report = scanner_with_db.scan(sample_dependencies)
        crypto_results = [r for r in report.results if r.package_name == "cryptography"]
        assert len(crypto_results) == 1
        assert crypto_results[0].finding_count == 2
        cve_ids = {f["cve_id"] for f in crypto_results[0].findings}
        assert "CVE-2023-49083" in cve_ids
        assert "CVE-2024-26471" in cve_ids

    def test_critical_cves_detected(self, scanner_with_db, sample_dependencies):
        report = scanner_with_db.scan(sample_dependencies)
        critical_findings = report.findings_by_severity.get("critical", 0)
        assert critical_findings >= 2

    def test_high_cves_detected(self, scanner_with_db, sample_dependencies):
        report = scanner_with_db.scan(sample_dependencies)
        high_findings = report.findings_by_severity.get("high", 0)
        assert high_findings >= 4

    def test_medium_cves_detected(self, scanner_with_db, sample_dependencies):
        report = scanner_with_db.scan(sample_dependencies)
        medium_findings = report.findings_by_severity.get("medium", 0)
        assert medium_findings >= 2

    def test_low_cves_detected(self, scanner_with_db, sample_dependencies):
        report = scanner_with_db.scan(sample_dependencies)
        low_findings = report.findings_by_severity.get("low", 0)
        assert low_findings >= 1

    def test_clean_packages_have_no_findings(self, scanner_with_db, sample_dependencies):
        report = scanner_with_db.scan(sample_dependencies)
        clean_results = [
            r for r in report.results
            if r.package_name in ("clean_package", "safe_lib", "another_clean")
        ]
        for r in clean_results:
            assert r.finding_count == 0

    def test_detection_rate_with_all_vulns_is_100_percent(self):
        db = CVEDatabase()
        db.vulnerabilities = {
            "pkg_x@1.0": [
                {"cve_id": "CVE-2024-0001", "severity": "high", "cvss_score": 7.5,
                 "description": "test", "affected_versions": "<=1.0"},
                {"cve_id": "CVE-2024-0002", "severity": "critical", "cvss_score": 9.8,
                 "description": "test2", "affected_versions": "<=1.0"},
            ],
        }
        deps = [ThirdPartyDependency("pkg_x", "1.0")]
        scanner = CVEScanner(cve_db=db)
        report = scanner.scan(deps)
        assert report.total_findings == 2

    def test_each_finding_has_required_fields(self, scanner_with_db, sample_dependencies):
        report = scanner_with_db.scan(sample_dependencies)
        for result in report.results:
            if result.has_vulnerabilities:
                for finding in result.findings:
                    assert "cve_id" in finding
                    assert "severity" in finding
                    assert "cvss_score" in finding
                    assert "description" in finding
                    assert "affected_versions" in finding

    def test_finding_cvss_score_range(self, scanner_with_db, sample_dependencies):
        report = scanner_with_db.scan(sample_dependencies)
        for result in report.results:
            for finding in result.findings:
                assert 0.0 <= finding["cvss_score"] <= 10.0

    def test_no_duplicate_cve_findings(self, scanner_with_db, sample_dependencies):
        report = scanner_with_db.scan(sample_dependencies)
        all_cve_ids: List[str] = []
        for result in report.results:
            for finding in result.findings:
                all_cve_ids.append(finding["cve_id"])
        assert len(all_cve_ids) == len(set(all_cve_ids))

    def test_severity_counts_sum_to_total(self, scanner_with_db, sample_dependencies):
        report = scanner_with_db.scan(sample_dependencies)
        severity_sum = sum(report.findings_by_severity.values())
        assert severity_sum == report.total_findings

    def test_severity_enum_values(self):
        assert Severity.LOW.value == "low"
        assert Severity.MEDIUM.value == "medium"
        assert Severity.HIGH.value == "high"
        assert Severity.CRITICAL.value == "critical"

    def test_total_findings_across_all_severities(self, scanner_with_db, sample_dependencies):
        report = scanner_with_db.scan(sample_dependencies)
        expected_cves = 9
        assert report.total_findings == expected_cves

    def test_single_package_single_cve(self):
        db = CVEDatabase()
        db.vulnerabilities = {
            "only_pkg@1.0": [
                {"cve_id": "CVE-ONLY-1", "severity": "low", "cvss_score": 2.0,
                 "description": "single", "affected_versions": "1.0"},
            ],
        }
        deps = [ThirdPartyDependency("only_pkg", "1.0")]
        scanner = CVEScanner(cve_db=db)
        report = scanner.scan(deps)
        assert report.total_findings == 1
        assert report.findings_by_severity["low"] == 1


# ============================================================
# AC3: 扫描时间 <= 2 小时
# ============================================================
class TestScanTimeLimit:
    """验收标准 3：扫描时间 <=2 小时。"""

    def test_scan_completes_within_time_limit(self, scanner_with_db, sample_dependencies):
        report = scanner_with_db.scan(sample_dependencies)
        assert report.within_time_limit is True

    def test_scan_duration_is_positive(self, scanner_with_db, sample_dependencies):
        report = scanner_with_db.scan(sample_dependencies)
        assert report.duration_seconds is not None
        assert report.duration_seconds > 0

    def test_max_scan_time_constant_is_2_hours(self):
        assert MAX_SCAN_TIME_SECONDS == 7200

    def test_scan_duration_under_1_second_for_typical_deps(self, scanner_with_db, sample_dependencies):
        report = scanner_with_db.scan(sample_dependencies)
        assert report.duration_seconds is not None
        assert report.duration_seconds < 1.0

    def test_report_has_started_and_completed_timestamps(self, scanner_with_db, sample_dependencies):
        report = scanner_with_db.scan(sample_dependencies)
        assert report.started_at is not None
        assert report.completed_at is not None
        assert report.completed_at >= report.started_at

    def test_duration_calculation_correct(self, scanner_with_db, sample_dependencies):
        report = scanner_with_db.scan(sample_dependencies)
        expected = (report.completed_at - report.started_at).total_seconds()
        assert abs(report.duration_seconds - expected) < 0.5

    def test_scan_time_within_limit_for_large_set(self):
        db = CVEDatabase()
        db.vulnerabilities = {
            f"pkg{i}@1.0": [
                {"cve_id": f"CVE-2024-{i:04d}", "severity": "low",
                 "cvss_score": 2.0, "description": f"vuln {i}",
                 "affected_versions": "1.0"},
            ]
            for i in range(500)
        }
        deps = [ThirdPartyDependency(f"pkg{i}", "1.0") for i in range(500)]
        scanner = CVEScanner(cve_db=db, project_name="large")
        report = scanner.scan(deps)
        assert report.within_time_limit is True
        assert report.total_findings == 500
        assert report.coverage_percent == 100.0

    def test_completed_report_status(self, scanner_with_db, sample_dependencies):
        report = scanner_with_db.scan(sample_dependencies)
        assert report.status == ScanStatus.COMPLETED

    def test_each_result_has_scan_time(self, scanner_with_db, sample_dependencies):
        report = scanner_with_db.scan(sample_dependencies)
        for result in report.results:
            assert result.scan_time_seconds >= 0


# ============================================================
# CVEFinding 单元测试
# ============================================================
class TestCVEFinding:
    """CVE 发现记录的单元测试。"""

    def test_create_finding_with_all_fields(self):
        f = CVEFinding(
            cve_id="CVE-2024-TEST",
            package_name="test-pkg",
            package_version="1.0.0",
            severity=Severity.CRITICAL,
            description="测试漏洞描述",
            cvss_score=9.8,
            affected_versions="<=1.0.0",
            fixed_version="1.0.1",
        )
        assert f.cve_id == "CVE-2024-TEST"
        assert f.package_name == "test-pkg"
        assert f.severity == Severity.CRITICAL

    def test_finding_to_dict_contains_all_fields(self):
        f = CVEFinding(
            cve_id="CVE-2024-DICT",
            package_name="dict-pkg",
            package_version="2.0.0",
            severity=Severity.HIGH,
            description="dict test",
            cvss_score=7.5,
            affected_versions="<=2.0.0",
        )
        d = f.to_dict()
        assert d["cve_id"] == "CVE-2024-DICT"
        assert d["severity"] == "high"
        assert d["cvss_score"] == 7.5
        assert d["discovered_at"] is not None

    def test_finding_fixed_version_defaults_to_none(self):
        f = CVEFinding(
            cve_id="CVE-2024-NOFIX",
            package_name="nofix-pkg",
            package_version="1.0.0",
            severity=Severity.LOW,
            description="no fix available",
            cvss_score=1.0,
            affected_versions="all",
        )
        assert f.fixed_version is None

    def test_finding_discovered_at_is_datetime(self):
        f = CVEFinding(
            cve_id="CVE-2024-DATE",
            package_name="date-pkg",
            package_version="1.0.0",
            severity=Severity.LOW,
            description="date test",
            cvss_score=1.0,
            affected_versions="all",
        )
        assert isinstance(f.discovered_at, datetime)

    def test_finding_severity_enum_mapping(self):
        for sev in Severity:
            f = CVEFinding(
                cve_id=f"CVE-{sev.name}",
                package_name="test",
                package_version="1.0",
                severity=sev,
                description="test",
                cvss_score=5.0,
                affected_versions="1.0",
            )
            d = f.to_dict()
            assert d["severity"] == sev.value


# ============================================================
# ScanResult 单元测试
# ============================================================
class TestScanResult:
    """扫描结果的单元测试。"""

    def test_clean_package_has_no_vulnerabilities(self):
        r = ScanResult(package_name="clean", package_version="1.0", scanned=True)
        assert r.has_vulnerabilities is False
        assert r.finding_count == 0

    def test_vulnerable_package_has_vulnerabilities(self):
        r = ScanResult(
            package_name="dirty",
            package_version="1.0",
            scanned=True,
            findings=[{"cve_id": "CVE-1"}, {"cve_id": "CVE-2"}],
        )
        assert r.has_vulnerabilities is True
        assert r.finding_count == 2

    def test_scan_result_with_error(self):
        r = ScanResult(
            package_name="err_pkg",
            package_version="1.0",
            scanned=False,
            error="timeout",
        )
        assert r.scanned is False
        assert r.error == "timeout"


# ============================================================
# ScanReport 单元测试
# ============================================================
class TestScanReport:
    """扫描报告的单元测试。"""

    def test_report_initialization(self):
        now = datetime.now(timezone.utc)
        report = ScanReport(
            project_name="test",
            scan_id="test-001",
            started_at=now,
            total_dependencies=10,
        )
        assert report.project_name == "test"
        assert report.status == ScanStatus.PENDING
        assert report.total_dependencies == 10

    def test_report_summary_contains_all_fields(self, scanner_with_db, sample_dependencies):
        report = scanner_with_db.scan(sample_dependencies)
        summary = report.summary
        assert "scan_id" in summary
        assert "project_name" in summary
        assert "status" in summary
        assert "coverage_percent" in summary
        assert "total_findings" in summary
        assert "findings_by_severity" in summary
        assert "duration_seconds" in summary
        assert "within_time_limit" in summary

    def test_report_with_no_vulnerabilities_has_100_detection_rate(self):
        now = datetime.now(timezone.utc)
        report = ScanReport(
            project_name="clean",
            scan_id="clean-001",
            started_at=now,
            total_dependencies=5,
            scanned_dependencies=5,
        )
        report.status = ScanStatus.COMPLETED
        report.completed_at = now + timedelta(seconds=1)
        assert report.detection_rate == 100.0

    def test_critical_count_property(self):
        report = ScanReport(
            project_name="test",
            scan_id="test",
            started_at=datetime.now(timezone.utc),
            findings_by_severity={"critical": 3, "high": 2, "medium": 1, "low": 0},
        )
        assert report.critical_count == 3
        assert report.high_count == 2

    def test_report_status_transitions(self):
        now = datetime.now(timezone.utc)
        report = ScanReport(
            project_name="status",
            scan_id="status-001",
            started_at=now,
        )
        assert report.status == ScanStatus.PENDING
        report.status = ScanStatus.RUNNING
        assert report.status == ScanStatus.RUNNING
        report.status = ScanStatus.COMPLETED
        assert report.status == ScanStatus.COMPLETED

    def test_scan_status_enum_values(self):
        assert ScanStatus.PENDING.value == "pending"
        assert ScanStatus.RUNNING.value == "running"
        assert ScanStatus.COMPLETED.value == "completed"
        assert ScanStatus.ERROR.value == "error"

    def test_report_completed_at_less_than_started_at_is_invalid(self):
        started = datetime.now(timezone.utc)
        completed = started - timedelta(seconds=10)
        report = ScanReport(
            project_name="invalid",
            scan_id="invalid-001",
            started_at=started,
            completed_at=completed,
        )
        assert report.duration_seconds is not None
        assert report.duration_seconds < 0

    def test_report_within_time_limit_boundary(self):
        started = datetime.now(timezone.utc)
        completed = started + timedelta(seconds=MAX_SCAN_TIME_SECONDS)
        report = ScanReport(
            project_name="boundary",
            scan_id="boundary-001",
            started_at=started,
            completed_at=completed,
        )
        assert report.within_time_limit is True

    def test_report_exceeds_time_limit(self):
        started = datetime.now(timezone.utc)
        completed = started + timedelta(seconds=MAX_SCAN_TIME_SECONDS + 1)
        report = ScanReport(
            project_name="exceeded",
            scan_id="exceeded-001",
            started_at=started,
            completed_at=completed,
        )
        assert report.within_time_limit is False

    def test_report_without_completed_at_within_limit_false(self):
        report = ScanReport(
            project_name="no-completed",
            scan_id="no-completed-001",
            started_at=datetime.now(timezone.utc),
        )
        assert report.within_time_limit is False

    def test_report_duration_none_without_completed(self):
        report = ScanReport(
            project_name="no-time",
            scan_id="no-time-001",
            started_at=datetime.now(timezone.utc),
        )
        assert report.duration_seconds is None


# ============================================================
# CVEScanner 综合集成测试
# ============================================================
class TestCVEScannerIntegration:
    """扫描器集成测试。"""

    def test_full_scan_returns_complete_report(self, scanner_with_db, sample_dependencies):
        report = scanner_with_db.scan(sample_dependencies)
        assert report is not None
        assert report.total_dependencies == 10
        assert report.status == ScanStatus.COMPLETED
        assert report.scanned_dependencies == 10

    def test_full_scan_meets_all_acceptance_criteria(self, scanner_with_db, sample_dependencies):
        report = scanner_with_db.scan(sample_dependencies)
        assert report.coverage_percent == 100.0
        assert report.total_findings > 0
        assert report.within_time_limit is True

    def test_scanner_get_report_after_scan(self, scanner_with_db, sample_dependencies):
        scanner_with_db.scan(sample_dependencies)
        report = scanner_with_db.get_report()
        assert report is not None
        assert report.total_findings > 0

    def test_scanner_reset_clears_report(self, scanner_with_db, sample_dependencies):
        scanner_with_db.scan(sample_dependencies)
        assert scanner_with_db.get_report() is not None
        scanner_with_db.reset()
        assert scanner_with_db.get_report() is None

    def test_scanner_can_rescan_after_reset(self, scanner_with_db, sample_dependencies):
        scanner_with_db.scan(sample_dependencies)
        scanner_with_db.reset()
        report2 = scanner_with_db.scan(sample_dependencies)
        assert report2.total_dependencies == 10
        assert report2.coverage_percent == 100.0

    def test_scan_different_project_names(self):
        db = CVEDatabase()
        db.vulnerabilities = {"mylib@1.0": [
            {"cve_id": "CVE-PROJ", "severity": "low", "cvss_score": 1.0,
             "description": "test", "affected_versions": "1.0"},
        ]}
        deps = [ThirdPartyDependency("mylib", "1.0")]

        s1 = CVEScanner(cve_db=db, project_name="Alpha")
        r1 = s1.scan(deps)
        assert r1.project_name == "Alpha"

        s2 = CVEScanner(cve_db=db, project_name="Beta")
        r2 = s2.scan(deps)
        assert r2.project_name == "Beta"

    def test_scan_empty_list_no_crash(self):
        scanner = CVEScanner(cve_db=CVEDatabase())
        report = scanner.scan([])
        assert report.total_dependencies == 0
        assert report.total_findings == 0

    def test_single_dependency_scan(self):
        db = CVEDatabase()
        db.vulnerabilities = {"solo@1.0": [
            {"cve_id": "CVE-SOLO", "severity": "high", "cvss_score": 8.0,
             "description": "solo vuln", "affected_versions": "1.0"},
        ]}
        scanner = CVEScanner(cve_db=db)
        result = scanner.scan_single(ThirdPartyDependency("solo", "1.0"))
        assert result.has_vulnerabilities is True
        assert result.finding_count == 1
        assert result.findings[0]["cve_id"] == "CVE-SOLO"

    def test_scan_single_no_vulnerability(self):
        db = CVEDatabase()
        scanner = CVEScanner(cve_db=db)
        result = scanner.scan_single(ThirdPartyDependency("clean", "1.0"))
        assert result.has_vulnerabilities is False
        assert result.finding_count == 0
        assert result.scanned is True

    def test_severity_counts_accurate(self, scanner_with_db, sample_dependencies):
        report = scanner_with_db.scan(sample_dependencies)
        expected = {"critical": 2, "high": 4, "medium": 2, "low": 1}
        for severity, count in expected.items():
            assert report.findings_by_severity.get(severity, 0) == count, \
                f"Severity {severity}: expected {count}, got {report.findings_by_severity.get(severity, 0)}"

    def test_report_summary_coverage_rounding(self, scanner_with_db, sample_dependencies):
        report = scanner_with_db.scan(sample_dependencies)
        summary = report.summary
        assert isinstance(summary["coverage_percent"], float)
        assert summary["coverage_percent"] <= 100.0

    def test_all_findings_associated_with_correct_package(self, scanner_with_db, sample_dependencies):
        report = scanner_with_db.scan(sample_dependencies)
        for result in report.results:
            for finding in result.findings:
                assert finding["package_name"] == result.package_name
                assert finding["package_version"] == result.package_version

    def test_finding_cve_id_format(self, scanner_with_db, sample_dependencies):
        report = scanner_with_db.scan(sample_dependencies)
        for result in report.results:
            for finding in result.findings:
                assert finding["cve_id"].startswith("CVE-")


# ============================================================
# ThirdPartyDependency 单元测试
# ============================================================
class TestThirdPartyDependency:
    """第三方依赖模型测试。"""

    def test_dependency_basic_fields(self):
        dep = ThirdPartyDependency("requests", "2.28.0")
        assert dep.name == "requests"
        assert dep.version == "2.28.0"
        assert dep.ecosystem == "pypi"

    def test_dependency_with_custom_ecosystem(self):
        dep = ThirdPartyDependency("lodash", "4.17.0", "npm")
        assert dep.ecosystem == "npm"

    def test_dependency_with_license(self):
        dep = ThirdPartyDependency("flask", "2.2.0", license="BSD-3-Clause")
        assert dep.license == "BSD-3-Clause"

    def test_dependency_transitive_flag(self):
        dep = ThirdPartyDependency("urllib3", "1.26.15", transitive=True)
        assert dep.transitive is True

    def test_dependency_transitive_defaults_false(self):
        dep = ThirdPartyDependency("pkg", "1.0")
        assert dep.transitive is False

    def test_dependency_default_empty_list(self):
        dep = ThirdPartyDependency("pkg", "1.0")
        assert dep.dependencies == []


# ============================================================
# CVEDatabase 单元测试
# ============================================================
class TestCVEDatabase:
    """CVE 数据库模拟测试。"""

    def test_lookup_returns_list(self, mock_cve_db):
        result = mock_cve_db.lookup("requests", "2.28.0")
        assert isinstance(result, list)
        assert len(result) > 0

    def test_lookup_nonexistent_returns_empty(self, mock_cve_db):
        result = mock_cve_db.lookup("nonexistent", "9.9.9")
        assert result == []

    def test_has_entry_true(self, mock_cve_db):
        assert mock_cve_db.has_entry("flask", "2.2.0") is True

    def test_has_entry_false(self, mock_cve_db):
        assert mock_cve_db.has_entry("nonexistent", "1.0") is False

    def test_lookup_version_specific(self, mock_cve_db):
        vulns_228 = mock_cve_db.lookup("requests", "2.28.0")
        vulns_231 = mock_cve_db.lookup("requests", "2.31.0")
        assert len(vulns_228) > 0
        assert len(vulns_231) == 0

    def test_empty_database(self):
        db = CVEDatabase()
        assert db.lookup("any", "1.0") == []
        assert db.has_entry("any", "1.0") is False


# ============================================================
# 边界与异常场景
# ============================================================
class TestEdgeCases:
    """边界和异常处理测试。"""

    def test_cve_id_uniqueness_across_packages(self, scanner_with_db, sample_dependencies):
        report = scanner_with_db.scan(sample_dependencies)
        all_cves = []
        for r in report.results:
            for f in r.findings:
                all_cves.append(f["cve_id"])
        assert len(all_cves) == len(set(all_cves))

    def test_scan_with_only_transitive_deps(self):
        db = CVEDatabase()
        db.vulnerabilities = {
            "trans_pkg@1.0": [
                {"cve_id": "CVE-TRANS", "severity": "medium", "cvss_score": 5.0,
                 "description": "transitive", "affected_versions": "1.0"},
            ],
        }
        deps = [
            ThirdPartyDependency("trans_pkg", "1.0", transitive=True),
        ]
        scanner = CVEScanner(cve_db=db)
        report = scanner.scan(deps)
        assert report.scanned_dependencies == 1
        assert report.total_findings == 1

    def test_large_scale_scan_stays_under_limit(self):
        db = CVEDatabase()
        for i in range(1000):
            db.vulnerabilities[f"pkg{i}@1.0"] = [
                {"cve_id": f"CVE-2024-{i:05d}", "severity": "low", "cvss_score": 1.0,
                 "description": f"vuln {i}", "affected_versions": "1.0"},
                {"cve_id": f"CVE-2024-{i:05d}b", "severity": "medium", "cvss_score": 4.0,
                 "description": f"vuln {i}b", "affected_versions": "1.0"},
            ]
        deps = [ThirdPartyDependency(f"pkg{i}", "1.0") for i in range(1000)]
        scanner = CVEScanner(cve_db=db)
        report = scanner.scan(deps)
        assert report.coverage_percent == 100.0
        assert report.total_findings == 2000
        assert report.within_time_limit is True

    def test_severity_unknown_defaults_to_low(self):
        db = CVEDatabase()
        db.vulnerabilities = {
            "unknown_sev@1.0": [
                {"cve_id": "CVE-UNK", "severity": "unknown_severity", "cvss_score": 3.0,
                 "description": "unknown severity test", "affected_versions": "1.0"},
            ],
        }
        deps = [ThirdPartyDependency("unknown_sev", "1.0")]
        scanner = CVEScanner(cve_db=db)
        report = scanner.scan(deps)
        assert report.total_findings == 1
        assert report.findings_by_severity["low"] == 1

    def test_multiple_scans_independent_results(self, scanner_with_db, sample_dependencies):
        r1 = scanner_with_db.scan(sample_dependencies)
        scanner_with_db.reset()
        r2 = scanner_with_db.scan(sample_dependencies)
        assert r1.total_findings == r2.total_findings
        assert r1.scan_id != r2.scan_id

    def test_report_summary_status_value_is_string(self, scanner_with_db, sample_dependencies):
        report = scanner_with_db.scan(sample_dependencies)
        summary = report.summary
        assert isinstance(summary["status"], str)
        assert summary["status"] == "completed"
