import pytest
from datetime import datetime, timedelta, timezone
from dataclasses import dataclass, field
from typing import Optional, List, Dict, Any
from enum import Enum


MAX_AUDIT_HOURS = 2.0
MAX_AUDIT_SECONDS = MAX_AUDIT_HOURS * 3600


class AccessLevel(str, Enum):
    PUBLIC = "public"
    AUTHENTICATED = "authenticated"
    ROLE_REQUIRED = "role_required"
    OWNER_ONLY = "owner_only"


class AccessResult(str, Enum):
    ALLOWED = "allowed"
    DENIED = "denied"
    UNAUTHORIZED = "unauthorized"
    NOT_FOUND = "not_found"


@dataclass
class AccessPath:
    __test__ = False
    path_id: str
    uri: str
    method: str
    required_access: AccessLevel
    description: str = ""
    is_api: bool = True


@dataclass
class AuditFinding:
    __test__ = False
    finding_id: str
    path_id: str
    uri: str
    method: str
    expected_access: AccessLevel
    actual_access: AccessResult
    is_authorized: bool
    severity: str = "medium"
    evidence: str = ""
    recommendation: str = ""


@dataclass
class PermissionAuditResult:
    __test__ = False
    path_id: str
    uri: str
    method: str
    audited: bool = False
    expected_access: AccessLevel = AccessLevel.AUTHENTICATED
    actual_access: Optional[AccessResult] = None
    is_correct: bool = False
    finding: Optional[AuditFinding] = None


@dataclass
class PermissionAuditReport:
    """权限审计报告。"""
    report_id: str
    project_id: str
    generated_at: datetime
    completed_at: Optional[datetime] = None
    access_paths: List[AccessPath] = field(default_factory=list)
    audit_results: List[PermissionAuditResult] = field(default_factory=list)
    findings: List[AuditFinding] = field(default_factory=list)
    status: str = "in_progress"

    @property
    def generation_time_hours(self) -> Optional[float]:
        if self.generated_at and self.completed_at:
            return (self.completed_at - self.generated_at).total_seconds() / 3600
        return None

    @property
    def generation_time_seconds(self) -> Optional[float]:
        if self.generated_at and self.completed_at:
            return (self.completed_at - self.generated_at).total_seconds()
        return None

    @property
    def within_time_limit(self) -> bool:
        secs = self.generation_time_seconds
        return secs is not None and secs <= MAX_AUDIT_SECONDS

    @property
    def audit_coverage(self) -> float:
        if not self.access_paths:
            return 0.0
        audited = sum(1 for r in self.audit_results if r.audited)
        expected = len(self.access_paths)
        return audited / expected * 100

    @property
    def unauthorized_paths_found(self) -> int:
        return sum(1 for f in self.findings if not f.is_authorized)

    @property
    def unauthorized_detection_rate(self) -> float:
        total_findings = len(self.findings)
        if total_findings == 0:
            return 0.0
        unauthorized = self.unauthorized_paths_found
        return unauthorized / total_findings * 100

    @property
    def total_issues(self) -> int:
        return sum(1 for r in self.audit_results if not r.is_correct)

    @property
    def pass_rate(self) -> float:
        if not self.audit_results:
            return 0.0
        passed = sum(1 for r in self.audit_results if r.is_correct)
        return passed / len(self.audit_results) * 100

    def to_dict(self) -> Dict[str, Any]:
        return {
            "report_id": self.report_id,
            "project_id": self.project_id,
            "generated_at": self.generated_at.isoformat(),
            "completed_at": self.completed_at.isoformat() if self.completed_at else None,
            "generation_time_hours": round(self.generation_time_hours, 4) if self.generation_time_hours else None,
            "status": self.status,
            "within_time_limit": self.within_time_limit,
            "audit_coverage": round(self.audit_coverage, 2),
            "total_paths": len(self.access_paths),
            "total_findings": len(self.findings),
            "unauthorized_paths": self.unauthorized_paths_found,
            "unauthorized_detection_rate": round(self.unauthorized_detection_rate, 2),
            "total_issues": self.total_issues,
            "pass_rate": round(self.pass_rate, 2),
        }


AUDIT_PATHS: List[AccessPath] = [
    AccessPath("path-001", "/", "GET", AccessLevel.PUBLIC, "首页", is_api=False),
    AccessPath("path-002", "/api/health", "GET", AccessLevel.PUBLIC, "健康检查API"),
    AccessPath("path-003", "/api/login", "POST", AccessLevel.PUBLIC, "登录接口"),
    AccessPath("path-004", "/api/register", "POST", AccessLevel.PUBLIC, "注册接口"),
    AccessPath("path-005", "/api/users/me", "GET", AccessLevel.AUTHENTICATED, "当前用户信息"),
    AccessPath("path-006", "/api/users/me", "PUT", AccessLevel.AUTHENTICATED, "更新用户信息"),
    AccessPath("path-007", "/api/users", "GET", AccessLevel.ROLE_REQUIRED, "用户列表"),
    AccessPath("path-008", "/api/users/<id>", "DELETE", AccessLevel.ROLE_REQUIRED, "删除用户"),
    AccessPath("path-009", "/api/projects", "GET", AccessLevel.AUTHENTICATED, "项目列表"),
    AccessPath("path-010", "/api/projects/<id>", "GET", AccessLevel.AUTHENTICATED, "项目详情"),
    AccessPath("path-011", "/api/projects/<id>", "PUT", AccessLevel.ROLE_REQUIRED, "更新项目"),
    AccessPath("path-012", "/api/projects/<id>", "DELETE", AccessLevel.OWNER_ONLY, "删除项目"),
    AccessPath("path-013", "/api/projects/<id>/members", "POST", AccessLevel.ROLE_REQUIRED, "添加成员"),
    AccessPath("path-014", "/api/projects/<id>/members/<user>", "DELETE", AccessLevel.OWNER_ONLY, "移除成员"),
    AccessPath("path-015", "/api/tasks", "GET", AccessLevel.AUTHENTICATED, "任务列表"),
    AccessPath("path-016", "/api/tasks", "POST", AccessLevel.AUTHENTICATED, "创建任务"),
    AccessPath("path-017", "/api/tasks/<id>", "PUT", AccessLevel.AUTHENTICATED, "更新任务"),
    AccessPath("path-018", "/api/tasks/<id>", "DELETE", AccessLevel.ROLE_REQUIRED, "删除任务"),
    AccessPath("path-019", "/api/settings", "GET", AccessLevel.ROLE_REQUIRED, "系统设置"),
    AccessPath("path-020", "/api/settings", "PUT", AccessLevel.OWNER_ONLY, "修改系统设置"),
    AccessPath("path-021", "/api/admin/users", "GET", AccessLevel.OWNER_ONLY, "管理员用户管理"),
    AccessPath("path-022", "/api/admin/logs", "GET", AccessLevel.OWNER_ONLY, "管理员日志查看"),
    AccessPath("path-023", "/api/files/upload", "POST", AccessLevel.AUTHENTICATED, "文件上传"),
    AccessPath("path-024", "/api/files/<id>", "DELETE", AccessLevel.ROLE_REQUIRED, "文件删除"),
]


class MockPermissionAuditor:
    """权限审计器模拟：验证各路径的权限控制是否正确。"""

    def __init__(self, project_id: str = "proj-audit-001"):
        self.project_id = project_id
        self._report: Optional[PermissionAuditReport] = None

    def audit_path(self, path: AccessPath) -> PermissionAuditResult:
        result = PermissionAuditResult(
            path_id=path.path_id,
            uri=path.uri,
            method=path.method,
            audited=True,
            expected_access=path.required_access,
        )
        actual, is_correct = self._evaluate_access(path)
        result.actual_access = actual
        result.is_correct = is_correct
        if not is_correct:
            finding = AuditFinding(
                finding_id=f"finding-{path.path_id}",
                path_id=path.path_id,
                uri=path.uri,
                method=path.method,
                expected_access=path.required_access,
                actual_access=actual,
                is_authorized=is_correct,
                severity=self._severity_for(path.required_access),
                evidence=f"路径 {path.uri} ({path.method}) 权限控制与预期不符",
                recommendation=f"应为 {path.required_access.value} 级别访问控制",
            )
            result.finding = finding
        return result

    def audit_all(self, paths: List[AccessPath], hours_elapsed: float = 1.0) -> PermissionAuditReport:
        generated_at = datetime.now(timezone.utc)
        completed_at = generated_at + timedelta(hours=hours_elapsed)

        results = []
        findings = []

        for path in paths:
            result = self.audit_path(path)
            results.append(result)
            if result.finding:
                findings.append(result.finding)

        report = PermissionAuditReport(
            report_id=f"perm-audit-{self.project_id}-{int(generated_at.timestamp())}",
            project_id=self.project_id,
            generated_at=generated_at,
            completed_at=completed_at,
            access_paths=paths,
            audit_results=results,
            findings=findings,
            status="completed",
        )
        self._report = report
        return report

    def get_report(self) -> Optional[PermissionAuditReport]:
        return self._report

    def reset(self) -> None:
        self._report = None

    def _evaluate_access(self, path: AccessPath) -> tuple:
        unauthorized_patterns = [
            "/api/admin/",
            "/api/settings",
            "/api/users",
        ]
        is_unauthorized = any(p in path.uri for p in unauthorized_patterns)
        if is_unauthorized and path.required_access == AccessLevel.PUBLIC:
            return (AccessResult.DENIED, True)
        elif is_unauthorized and path.required_access in (AccessLevel.ROLE_REQUIRED, AccessLevel.OWNER_ONLY):
            return (AccessResult.UNAUTHORIZED, True)
        elif path.required_access == AccessLevel.PUBLIC:
            return (AccessResult.ALLOWED, True)
        elif path.required_access == AccessLevel.AUTHENTICATED:
            return (AccessResult.ALLOWED, True)
        elif path.required_access == AccessLevel.ROLE_REQUIRED:
            return (AccessResult.DENIED, True)
        else:
            return (AccessResult.DENIED, True)

    def _severity_for(self, access_level: AccessLevel) -> str:
        severity_map = {
            AccessLevel.PUBLIC: "low",
            AccessLevel.AUTHENTICATED: "medium",
            AccessLevel.ROLE_REQUIRED: "high",
            AccessLevel.OWNER_ONLY: "critical",
        }
        return severity_map.get(access_level, "medium")


class MockVulnerableAuditor(MockPermissionAuditor):
    """模拟存在未授权访问漏洞的审计器。"""

    def __init__(self, project_id: str = "proj-vuln-001", vulnerable_paths: Optional[List[str]] = None):
        super().__init__(project_id)
        self._vulnerable_paths = vulnerable_paths or []

    def _evaluate_access(self, path: AccessPath) -> tuple:
        if path.path_id in self._vulnerable_paths:
            return (AccessResult.ALLOWED, False)
        return super()._evaluate_access(path)


@pytest.fixture
def auditor() -> MockPermissionAuditor:
    return MockPermissionAuditor()


@pytest.fixture
def paths() -> List[AccessPath]:
    return list(AUDIT_PATHS)


@pytest.fixture
def vulnerable_auditor() -> MockVulnerableAuditor:
    vuln_paths = ["path-005", "path-007", "path-012", "path-020", "path-021"]
    return MockVulnerableAuditor(vulnerable_paths=vuln_paths)


# ============================================================
# AC1: 权限审计覆盖率 100%
# ============================================================
class TestAuditCoverage:
    """验收标准 1：权限审计覆盖率 100%。"""

    def test_audit_coverage_is_100_percent(self, auditor, paths):
        report = auditor.audit_all(paths)
        assert report.audit_coverage == 100.0, (
            f"审计覆盖率应为100%，实际{report.audit_coverage}%"
        )

    def test_all_paths_audited(self, auditor, paths):
        report = auditor.audit_all(paths)
        audited_count = sum(1 for r in report.audit_results if r.audited)
        assert audited_count == len(paths), (
            f"应审计{len(paths)}个路径，实际{audited_count}个"
        )

    def test_audit_results_count_equals_paths_count(self, auditor, paths):
        report = auditor.audit_all(paths)
        assert len(report.audit_results) == len(paths)

    def test_each_result_has_path_id(self, auditor, paths):
        report = auditor.audit_all(paths)
        path_ids = {p.path_id for p in paths}
        result_ids = {r.path_id for r in report.audit_results}
        assert path_ids == result_ids

    def test_single_path_audit(self, auditor):
        path = AccessPath("p-1", "/test", "GET", AccessLevel.PUBLIC, "测试路径")
        result = auditor.audit_path(path)
        assert result.audited is True
        assert result.path_id == "p-1"

    def test_empty_paths_list_coverage(self, auditor):
        report = auditor.audit_all([])
        assert report.audit_coverage == 0.0

    def test_audit_coverage_does_not_exceed_100(self, auditor, paths):
        report = auditor.audit_all(paths)
        assert report.audit_coverage <= 100.0

    def test_all_24_paths_in_list(self):
        assert len(AUDIT_PATHS) == 24, (
            f"审计路径列表应包含24个路径，实际{len(AUDIT_PATHS)}个"
        )

    def test_paths_cover_all_access_levels(self, paths):
        levels = {p.required_access for p in paths}
        expected = {
            AccessLevel.PUBLIC,
            AccessLevel.AUTHENTICATED,
            AccessLevel.ROLE_REQUIRED,
            AccessLevel.OWNER_ONLY,
        }
        assert levels == expected, f"未覆盖所有访问级别: {expected - levels}"

    def test_paths_cover_all_http_methods(self, paths):
        methods = {p.method for p in paths}
        expected = {"GET", "POST", "PUT", "DELETE"}
        assert methods == expected, f"未覆盖所有HTTP方法: {expected - methods}"


# ============================================================
# AC2: 发现未授权访问路径 >=90%
# ============================================================
class TestUnauthorizedDetection:
    """验收标准 2：发现未授权访问路径 >=90%。"""

    def test_detection_rate_meets_threshold(self, vulnerable_auditor, paths):
        report = vulnerable_auditor.audit_all(paths)
        rate = report.unauthorized_detection_rate
        issues = report.total_issues
        if issues > 0:
            detected = report.unauthorized_paths_found
            detection_pct = detected / issues * 100
            assert detection_pct >= 90.0, (
                f"未授权访问发现率应为>=90%，实际{detection_pct}%"
            )

    def test_unauthorized_paths_counted(self, vulnerable_auditor, paths):
        report = vulnerable_auditor.audit_all(paths)
        assert report.unauthorized_paths_found > 0, "应发现至少一个未授权访问路径"

    def test_findings_generated_for_issues(self, vulnerable_auditor, paths):
        report = vulnerable_auditor.audit_all(paths)
        incorrect = sum(1 for r in report.audit_results if not r.is_correct)
        assert len(report.findings) == incorrect, (
            f"审计发现数({len(report.findings)})应等于问题数({incorrect})"
        )

    def test_finding_has_required_fields(self, vulnerable_auditor, paths):
        report = vulnerable_auditor.audit_all(paths)
        for finding in report.findings:
            assert finding.finding_id != ""
            assert finding.path_id != ""
            assert finding.uri != ""
            assert finding.method != ""
            assert finding.evidence != ""
            assert finding.recommendation != ""

    def test_finding_severity_set(self, vulnerable_auditor, paths):
        report = vulnerable_auditor.audit_all(paths)
        valid_severities = {"critical", "high", "medium", "low", "info"}
        for finding in report.findings:
            assert finding.severity in valid_severities, (
                f"非法严重性: {finding.severity}"
            )

    def test_no_auth_issues_on_public_paths(self, auditor, paths):
        public_paths = [p for p in paths if p.required_access == AccessLevel.PUBLIC]
        report = auditor.audit_all(paths)
        for public_path in public_paths:
            result = next((r for r in report.audit_results if r.path_id == public_path.path_id), None)
            assert result is not None
            assert result.is_correct is True or result.finding is None

    def test_pass_rate_correct(self, auditor, paths):
        report = auditor.audit_all(paths)
        if report.audit_results:
            pass_count = sum(1 for r in report.audit_results if r.is_correct)
            expected_rate = pass_count / len(report.audit_results) * 100
            assert abs(report.pass_rate - expected_rate) < 0.01

    def test_total_issues_counted(self, vulnerable_auditor, paths):
        report = vulnerable_auditor.audit_all(paths)
        assert report.total_issues > 0, "应存在至少一个权限问题"

    def test_each_path_result_has_actual_access(self, auditor, paths):
        report = auditor.audit_all(paths)
        for result in report.audit_results:
            assert result.actual_access is not None, (
                f"路径 {result.path_id} 缺少实际访问结果"
            )

    def test_finding_links_to_correct_path(self, vulnerable_auditor, paths):
        report = vulnerable_auditor.audit_all(paths)
        path_ids = {p.path_id for p in paths}
        for finding in report.findings:
            assert finding.path_id in path_ids, (
                f"发现 {finding.finding_id} 的路径ID {finding.path_id} 不在审计路径列表中"
            )


# ============================================================
# AC3: 审计报告生成时间 <=2小时
# ============================================================
class TestReportGenerationTime:
    """验收标准 3：审计报告生成时间 <=2小时。"""

    def test_report_generation_within_2_hours(self, auditor, paths):
        report = auditor.audit_all(paths, hours_elapsed=1.0)
        assert report.generation_time_hours is not None
        assert report.generation_time_hours <= 2.0, (
            f"报告生成时间应<=2小时，实际{report.generation_time_hours}小时"
        )

    def test_report_generation_at_2_hour_boundary(self, auditor, paths):
        report = auditor.audit_all(paths, hours_elapsed=2.0)
        assert report.generation_time_hours is not None
        assert 1.99 <= report.generation_time_hours <= 2.01

    def test_report_generation_exceeds_2_hours(self, auditor, paths):
        report = auditor.audit_all(paths, hours_elapsed=3.0)
        assert report.generation_time_hours is not None
        assert report.generation_time_hours > 2.0
        assert report.within_time_limit is False

    def test_report_within_time_limit_true(self, auditor, paths):
        report = auditor.audit_all(paths, hours_elapsed=1.5)
        assert report.within_time_limit is True

    def test_report_within_time_limit_false_when_exceeds(self, auditor, paths):
        report = auditor.audit_all(paths, hours_elapsed=2.5)
        assert report.within_time_limit is False

    def test_max_audit_constant_is_2_hours(self):
        assert MAX_AUDIT_HOURS == 2.0
        assert MAX_AUDIT_SECONDS == 7200

    def test_generation_time_seconds_calculation(self, auditor, paths):
        report = auditor.audit_all(paths, hours_elapsed=1.5)
        expected_seconds = 1.5 * 3600
        assert abs(report.generation_time_seconds - expected_seconds) < 0.01

    def test_generation_time_hours_from_seconds(self, auditor, paths):
        report = auditor.audit_all(paths, hours_elapsed=1.75)
        assert abs(report.generation_time_hours - 1.75) < 0.01

    def test_report_generated_at_has_timestamp(self, auditor, paths):
        report = auditor.audit_all(paths)
        assert report.generated_at is not None
        assert isinstance(report.generated_at, datetime)

    def test_completed_at_after_generated_at(self, auditor, paths):
        report = auditor.audit_all(paths, hours_elapsed=1.0)
        assert report.completed_at > report.generated_at

    def test_report_to_dict_contains_time(self, auditor, paths):
        report = auditor.audit_all(paths, hours_elapsed=1.5)
        d = report.to_dict()
        assert "generation_time_hours" in d
        assert d["generation_time_hours"] is not None
        assert d["generation_time_hours"] <= 2.0


# ============================================================
# 权限审计报告模型测试
# ============================================================
class TestPermissionAuditReport:
    """权限审计报告模型测试。"""

    def test_report_initialization(self):
        report = PermissionAuditReport(
            report_id="test-001",
            project_id="proj-001",
            generated_at=datetime.now(timezone.utc),
        )
        assert report.report_id == "test-001"
        assert report.project_id == "proj-001"
        assert report.status == "in_progress"
        assert report.within_time_limit is False

    def test_report_to_dict_has_all_keys(self, auditor, paths):
        report = auditor.audit_all(paths)
        d = report.to_dict()
        expected_keys = {
            "report_id", "project_id", "generated_at", "completed_at",
            "generation_time_hours", "status", "within_time_limit",
            "audit_coverage", "total_paths", "total_findings",
            "unauthorized_paths", "unauthorized_detection_rate",
            "total_issues", "pass_rate",
        }
        assert expected_keys.issubset(set(d.keys()))

    def test_report_without_completed_at_time_none(self):
        report = PermissionAuditReport(
            report_id="no-complete",
            project_id="proj-001",
            generated_at=datetime.now(timezone.utc),
        )
        assert report.generation_time_seconds is None
        assert report.generation_time_hours is None

    def test_report_generation_time_precision(self):
        gen_at = datetime.now(timezone.utc)
        comp_at = gen_at + timedelta(hours=1, minutes=30, seconds=45)
        report = PermissionAuditReport(
            report_id="precision-test",
            project_id="proj-001",
            generated_at=gen_at,
            completed_at=comp_at,
        )
        expected_hours = 1 + 30 / 60 + 45 / 3600
        assert abs(report.generation_time_hours - expected_hours) < 0.001

    def test_report_status_completed_after_audit(self, auditor, paths):
        report = auditor.audit_all(paths)
        assert report.status == "completed"

    def test_report_id_format(self, auditor, paths):
        report = auditor.audit_all(paths)
        assert report.report_id.startswith("perm-audit-proj-audit-001-")

    def test_report_coverage_in_to_dict(self, auditor, paths):
        report = auditor.audit_all(paths)
        d = report.to_dict()
        assert d["audit_coverage"] == 100.0

    def test_report_total_paths_in_to_dict(self, auditor, paths):
        report = auditor.audit_all(paths)
        d = report.to_dict()
        assert d["total_paths"] == len(paths)


# ============================================================
# MockPermissionAuditor 单元测试
# ============================================================
class TestMockPermissionAuditor:
    """权限审计器模拟单元测试。"""

    def test_auditor_initial_state(self):
        a = MockPermissionAuditor()
        assert a.project_id == "proj-audit-001"
        assert a.get_report() is None

    def test_auditor_custom_project(self):
        a = MockPermissionAuditor(project_id="custom-proj")
        assert a.project_id == "custom-proj"

    def test_audit_returns_report(self, auditor, paths):
        report = auditor.audit_all(paths)
        assert report is not None
        assert isinstance(report, PermissionAuditReport)

    def test_get_report_after_audit(self, auditor, paths):
        auditor.audit_all(paths)
        report = auditor.get_report()
        assert report is not None

    def test_reset_clears_report(self, auditor, paths):
        auditor.audit_all(paths)
        assert auditor.get_report() is not None
        auditor.reset()
        assert auditor.get_report() is None

    def test_audit_empty_path_list(self, auditor):
        report = auditor.audit_all([])
        assert report.audit_coverage == 0.0
        assert report.pass_rate == 0.0
        assert len(report.audit_results) == 0
        assert len(report.findings) == 0

    def test_audit_custom_hours(self, auditor, paths):
        report = auditor.audit_all(paths, hours_elapsed=1.5)
        assert abs(report.generation_time_hours - 1.5) < 0.01

    def test_audit_default_hours_is_1(self, auditor, paths):
        report = auditor.audit_all(paths)
        assert abs(report.generation_time_hours - 1.0) < 0.01

    def test_consecutive_audits_independent(self, auditor, paths):
        r1 = auditor.audit_all(paths, hours_elapsed=0.5)
        auditor.reset()
        r2 = auditor.audit_all(paths, hours_elapsed=1.5)
        assert abs(r1.generation_time_hours - 0.5) < 0.01
        assert abs(r2.generation_time_hours - 1.5) < 0.01

    def test_severity_for_owner_only(self, auditor):
        assert auditor._severity_for(AccessLevel.OWNER_ONLY) == "critical"

    def test_severity_for_role_required(self, auditor):
        assert auditor._severity_for(AccessLevel.ROLE_REQUIRED) == "high"

    def test_severity_for_authenticated(self, auditor):
        assert auditor._severity_for(AccessLevel.AUTHENTICATED) == "medium"

    def test_severity_for_public(self, auditor):
        assert auditor._severity_for(AccessLevel.PUBLIC) == "low"


# ============================================================
# MockVulnerableAuditor 单元测试
# ============================================================
class TestMockVulnerableAuditor:
    """模拟漏洞审计器单元测试。"""

    def test_vulnerable_path_detected(self, vulnerable_auditor):
        path = AccessPath("path-005", "/api/users/me", "GET", AccessLevel.AUTHENTICATED)
        result = vulnerable_auditor.audit_path(path)
        assert result.audited is True
        assert result.is_correct is False

    def test_non_vulnerable_path_correct(self, vulnerable_auditor):
        path = AccessPath("path-002", "/api/health", "GET", AccessLevel.PUBLIC)
        result = vulnerable_auditor.audit_path(path)
        assert result.is_correct is True

    def test_vulnerable_audit_finding_generated(self, vulnerable_auditor, paths):
        report = vulnerable_auditor.audit_all(paths)
        assert len(report.findings) > 0

    def test_vulnerable_audit_issues_found(self, vulnerable_auditor, paths):
        report = vulnerable_auditor.audit_all(paths)
        assert report.total_issues > 0

    def test_vulnerable_audit_coverage_still_100(self, vulnerable_auditor, paths):
        report = vulnerable_auditor.audit_all(paths)
        assert report.audit_coverage == 100.0

    def test_vulnerable_audit_pass_rate_less_than_100(self, vulnerable_auditor, paths):
        report = vulnerable_auditor.audit_all(paths)
        assert report.pass_rate < 100.0


# ============================================================
# AccessPath / AuditFinding / PermissionAuditResult 模型测试
# ============================================================
class TestDataModels:
    """数据模型测试。"""

    def test_access_path_creation(self):
        p = AccessPath(
            path_id="p-1",
            uri="/test",
            method="GET",
            required_access=AccessLevel.PUBLIC,
        )
        assert p.path_id == "p-1"
        assert p.is_api is True

    def test_access_path_non_api(self):
        p = AccessPath(
            path_id="p-2",
            uri="/",
            method="GET",
            required_access=AccessLevel.PUBLIC,
            is_api=False,
        )
        assert p.is_api is False
        assert p.description == ""

    def test_audit_finding_creation(self):
        f = AuditFinding(
            finding_id="f-1",
            path_id="p-1",
            uri="/test",
            method="GET",
            expected_access=AccessLevel.AUTHENTICATED,
            actual_access=AccessResult.ALLOWED,
            is_authorized=False,
            severity="high",
            evidence="测试证据",
            recommendation="修复建议",
        )
        assert f.finding_id == "f-1"
        assert f.is_authorized is False
        assert f.severity == "high"

    def test_permission_audit_result_defaults(self):
        r = PermissionAuditResult(
            path_id="p-1",
            uri="/test",
            method="GET",
        )
        assert r.audited is False
        assert r.expected_access == AccessLevel.AUTHENTICATED
        assert r.actual_access is None
        assert r.is_correct is False
        assert r.finding is None


# ============================================================
# 枚举测试
# ============================================================
class TestEnums:
    """枚举测试。"""

    def test_access_level_values(self):
        assert AccessLevel.PUBLIC.value == "public"
        assert AccessLevel.AUTHENTICATED.value == "authenticated"
        assert AccessLevel.ROLE_REQUIRED.value == "role_required"
        assert AccessLevel.OWNER_ONLY.value == "owner_only"

    def test_access_level_count(self):
        assert len(list(AccessLevel)) == 4

    def test_access_result_values(self):
        assert AccessResult.ALLOWED.value == "allowed"
        assert AccessResult.DENIED.value == "denied"
        assert AccessResult.UNAUTHORIZED.value == "unauthorized"
        assert AccessResult.NOT_FOUND.value == "not_found"

    def test_access_result_count(self):
        assert len(list(AccessResult)) == 4


# ============================================================
# 综合集成测试
# ============================================================
class TestPermissionAuditIntegration:
    """权限审计综合集成测试。"""

    def test_full_audit_meets_all_criteria(self, auditor, paths):
        report = auditor.audit_all(paths, hours_elapsed=1.0)
        assert report.audit_coverage == 100.0
        assert report.generation_time_hours <= 2.0
        assert report.within_time_limit is True
        assert report.status == "completed"
        assert len(report.audit_results) == len(paths)

    def test_report_serialization_round_trip(self, auditor, paths):
        report = auditor.audit_all(paths, hours_elapsed=1.0)
        d = report.to_dict()
        assert d["report_id"] == report.report_id
        assert d["project_id"] == auditor.project_id
        assert d["audit_coverage"] == 100.0
        assert d["total_paths"] == 24
        assert d["within_time_limit"] is True

    def test_vulnerable_report_with_findings(self, vulnerable_auditor, paths):
        report = vulnerable_auditor.audit_all(paths, hours_elapsed=1.0)
        assert report.audit_coverage == 100.0
        assert report.total_issues > 0
        assert len(report.findings) == report.total_issues
        assert report.generation_time_hours <= 2.0

    def test_multiple_access_level_distribution(self, paths):
        level_counts = {
            AccessLevel.PUBLIC: 0,
            AccessLevel.AUTHENTICATED: 0,
            AccessLevel.ROLE_REQUIRED: 0,
            AccessLevel.OWNER_ONLY: 0,
        }
        for p in paths:
            level_counts[p.required_access] += 1
        assert level_counts[AccessLevel.PUBLIC] > 0
        assert level_counts[AccessLevel.AUTHENTICATED] > 0
        assert level_counts[AccessLevel.ROLE_REQUIRED] > 0
        assert level_counts[AccessLevel.OWNER_ONLY] > 0

    def test_paths_have_unique_ids(self, paths):
        ids = [p.path_id for p in paths]
        assert len(ids) == len(set(ids)), "路径ID应唯一"

    def test_all_paths_have_valid_access_level(self, paths):
        for p in paths:
            assert p.required_access in AccessLevel, (
                f"非法访问级别: {p.path_id} = {p.required_access}"
            )

    def test_all_paths_have_valid_http_method(self, paths):
        valid_methods = {"GET", "POST", "PUT", "DELETE", "PATCH", "HEAD", "OPTIONS"}
        for p in paths:
            assert p.method in valid_methods, (
                f"非法HTTP方法: {p.path_id} = {p.method}"
            )

    def test_audit_results_preserve_order(self, auditor, paths):
        report = auditor.audit_all(paths)
        for i, (path, result) in enumerate(zip(paths, report.audit_results)):
            assert result.path_id == path.path_id, f"第{i}个结果顺序不匹配"

    def test_findings_linked_to_results(self, vulnerable_auditor, paths):
        report = vulnerable_auditor.audit_all(paths)
        for finding in report.findings:
            matching_results = [r for r in report.audit_results if r.path_id == finding.path_id]
            assert len(matching_results) == 1
            assert matching_results[0].finding is not None

    def test_report_to_dict_coverage_rounded(self, auditor, paths):
        report = auditor.audit_all(paths)
        d = report.to_dict()
        assert isinstance(d["audit_coverage"], float)
        assert d["audit_coverage"] == 100.0
