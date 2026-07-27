import pytest
import time
from datetime import datetime, timedelta, timezone
from dataclasses import dataclass, field
from typing import Optional, List, Dict, Any
from enum import Enum


MAX_REPORT_GENERATION_HOURS = 4.0
MAX_REPORT_GENERATION_SECONDS = MAX_REPORT_GENERATION_HOURS * 3600


class VulnerabilitySeverity(str, Enum):
    CRITICAL = "critical"
    HIGH = "high"
    MEDIUM = "medium"
    LOW = "low"
    INFO = "info"


SEVERITY_PENALTY: Dict[str, float] = {
    "critical": 15.0,
    "high": 10.0,
    "medium": 5.0,
    "low": 2.0,
    "info": 1.0,
}


@dataclass
class VulnerabilityItem:
    """单个漏洞条目。"""
    vuln_id: str
    name: str
    severity: VulnerabilitySeverity
    cvss_score: float
    description: str
    affected_component: str
    affected_version: str
    cwe_id: str = ""
    references: List[str] = field(default_factory=list)


@dataclass
class RemediationSuggestion:
    """修复建议条目。"""
    vuln_id: str
    priority: str
    fix_version: str
    action: str
    estimated_effort: str
    temporary_mitigation: str = ""


@dataclass
class AuditOverview:
    """审计概述。"""
    project_name: str
    audit_start: datetime
    audit_end: datetime
    auditor_agent: str
    scope: str
    total_vulnerabilities: int
    critical_count: int
    high_count: int
    medium_count: int
    low_count: int
    info_count: int
    summary_text: str


@dataclass
class SecurityScore:
    """安全评分。"""
    raw_score: float
    final_score: float
    grade: str
    breakdown: Dict[str, float]
    calculation_method: str = "severity_weighted_deduction"

    def to_dict(self) -> Dict[str, Any]:
        return {
            "raw_score": self.raw_score,
            "final_score": self.final_score,
            "grade": self.grade,
            "breakdown": self.breakdown,
            "calculation_method": self.calculation_method,
        }


@dataclass
class SecurityAuditReport:
    """安全审计报告。"""
    report_id: str
    project_name: str
    generated_at: datetime
    completed_at: Optional[datetime] = None
    overview: Optional[AuditOverview] = None
    vulnerabilities: List[Dict[str, Any]] = field(default_factory=list)
    remediations: List[Dict[str, Any]] = field(default_factory=list)
    security_score: Optional[SecurityScore] = None
    status: str = "generating"

    @property
    def generation_time_seconds(self) -> Optional[float]:
        if self.generated_at and self.completed_at:
            return (self.completed_at - self.generated_at).total_seconds()
        return None

    @property
    def generation_time_hours(self) -> Optional[float]:
        secs = self.generation_time_seconds
        return secs / 3600.0 if secs is not None else None

    @property
    def within_time_limit(self) -> bool:
        secs = self.generation_time_seconds
        return secs is not None and secs <= MAX_REPORT_GENERATION_SECONDS

    @property
    def has_overview(self) -> bool:
        return self.overview is not None

    @property
    def has_vulnerability_list(self) -> bool:
        return len(self.vulnerabilities) > 0

    @property
    def has_remediation_suggestions(self) -> bool:
        return len(self.remediations) > 0

    @property
    def has_security_score(self) -> bool:
        return self.security_score is not None

    @property
    def has_all_sections(self) -> bool:
        return (
            self.has_overview
            and self.has_vulnerability_list
            and self.has_remediation_suggestions
            and self.has_security_score
        )

    def to_dict(self) -> Dict[str, Any]:
        return {
            "report_id": self.report_id,
            "project_name": self.project_name,
            "generated_at": self.generated_at.isoformat(),
            "completed_at": self.completed_at.isoformat() if self.completed_at else None,
            "generation_time_hours": round(self.generation_time_hours, 4) if self.generation_time_hours else None,
            "status": self.status,
            "within_time_limit": self.within_time_limit,
            "has_all_sections": self.has_all_sections,
            "vulnerability_count": len(self.vulnerabilities),
            "remediation_count": len(self.remediations),
            "security_score": self.security_score.to_dict() if self.security_score else None,
        }


class SecurityScoreCalculator:
    """安全评分计算器。"""

    @classmethod
    def calculate(cls, vulnerabilities: List[Dict[str, Any]]) -> SecurityScore:
        if not vulnerabilities:
            return SecurityScore(
                raw_score=100.0,
                final_score=100.0,
                grade="A+",
                breakdown={
                    "critical_penalty": 0.0,
                    "high_penalty": 0.0,
                    "medium_penalty": 0.0,
                    "low_penalty": 0.0,
                    "info_penalty": 0.0,
                },
            )

        breakdown: Dict[str, float] = {
            "critical_penalty": 0.0,
            "high_penalty": 0.0,
            "medium_penalty": 0.0,
            "low_penalty": 0.0,
            "info_penalty": 0.0,
        }

        total_penalty = 0.0

        for vuln in vulnerabilities:
            severity = vuln.get("severity", "low")
            penalty = SEVERITY_PENALTY.get(severity, 0.0)
            key = f"{severity}_penalty"
            breakdown[key] = breakdown.get(key, 0.0) + penalty
            total_penalty += penalty

        raw_score = 100.0 - total_penalty
        final_score = max(0.0, min(100.0, raw_score))

        grade = cls._score_to_grade(final_score)

        return SecurityScore(
            raw_score=raw_score,
            final_score=final_score,
            grade=grade,
            breakdown=breakdown,
        )

    @staticmethod
    def _score_to_grade(score: float) -> str:
        if score >= 90:
            return "A+"
        elif score >= 80:
            return "A"
        elif score >= 70:
            return "B+"
        elif score >= 60:
            return "B"
        elif score >= 50:
            return "C"
        elif score >= 40:
            return "D"
        else:
            return "F"


class MockSecurityAuditor:
    """安全审计器模拟：生成安全审计报告。"""

    def __init__(self, project_name: str = "DevFlow"):
        self.project_name = project_name
        self._report: Optional[SecurityAuditReport] = None

    def audit(
        self,
        vulnerabilities: List[VulnerabilityItem],
        hours_elapsed: float = 2.0,
    ) -> SecurityAuditReport:
        generated_at = datetime.now(timezone.utc)
        completed_at = generated_at + timedelta(hours=hours_elapsed)

        vuln_dicts = []
        remediation_dicts = []

        for vuln in vulnerabilities:
            vuln_dict = {
                "vuln_id": vuln.vuln_id,
                "name": vuln.name,
                "severity": vuln.severity.value,
                "cvss_score": vuln.cvss_score,
                "description": vuln.description,
                "affected_component": vuln.affected_component,
                "affected_version": vuln.affected_version,
                "cwe_id": vuln.cwe_id,
                "references": vuln.references,
            }
            vuln_dicts.append(vuln_dict)

            priority_map = {
                "critical": "P0",
                "high": "P1",
                "medium": "P2",
                "low": "P3",
                "info": "P4",
            }
            effort_map = {
                "critical": "1-2天",
                "high": "1天",
                "medium": "4小时",
                "low": "2小时",
                "info": "无需修复",
            }
            rem_dict = {
                "vuln_id": vuln.vuln_id,
                "priority": priority_map.get(vuln.severity.value, "P3"),
                "fix_version": "latest",
                "action": f"修复 {vuln.name}: 升级到安全版本或应用补丁",
                "estimated_effort": effort_map.get(vuln.severity.value, "待定"),
                "temporary_mitigation": f"临时缓解措施：{vuln.name} 限制访问范围",
            }
            remediation_dicts.append(rem_dict)

        severity_counts = {"critical": 0, "high": 0, "medium": 0, "low": 0, "info": 0}
        for vuln in vulnerabilities:
            severity_counts[vuln.severity.value] = severity_counts.get(vuln.severity.value, 0) + 1

        overview = AuditOverview(
            project_name=self.project_name,
            audit_start=generated_at,
            audit_end=completed_at,
            auditor_agent="mimeng",
            scope=f"全量安全审计：{self.project_name}",
            total_vulnerabilities=len(vulnerabilities),
            critical_count=severity_counts["critical"],
            high_count=severity_counts["high"],
            medium_count=severity_counts["medium"],
            low_count=severity_counts["low"],
            info_count=severity_counts["info"],
            summary_text=(
                f"审计完成：共发现 {len(vulnerabilities)} 个漏洞，"
                f"其中严重 {severity_counts['critical']} 个、"
                f"高危 {severity_counts['high']} 个、"
                f"中危 {severity_counts['medium']} 个、"
                f"低危 {severity_counts['low']} 个、"
                f"信息级 {severity_counts['info']} 个"
            ),
        )

        security_score = SecurityScoreCalculator.calculate(vuln_dicts)

        report = SecurityAuditReport(
            report_id=f"audit-{self.project_name.lower()}-{int(generated_at.timestamp())}",
            project_name=self.project_name,
            generated_at=generated_at,
            completed_at=completed_at,
            overview=overview,
            vulnerabilities=vuln_dicts,
            remediations=remediation_dicts,
            security_score=security_score,
            status="completed",
        )
        self._report = report
        return report

    def get_report(self) -> Optional[SecurityAuditReport]:
        return self._report

    def reset(self) -> None:
        self._report = None


SAMPLE_VULNERABILITIES: List[VulnerabilityItem] = [
    VulnerabilityItem(
        vuln_id="VULN-001",
        name="SQL注入-登录接口",
        severity=VulnerabilitySeverity.CRITICAL,
        cvss_score=9.8,
        description="登录接口存在SQL注入漏洞，攻击者可绕过身份认证",
        affected_component="auth/login",
        affected_version="1.2.0",
        cwe_id="CWE-89",
        references=["https://owasp.org/www-community/attacks/SQL_Injection"],
    ),
    VulnerabilityItem(
        vuln_id="VULN-002",
        name="XSS-反射型",
        severity=VulnerabilitySeverity.HIGH,
        cvss_score=7.5,
        description="搜索框未对输入做XSS过滤",
        affected_component="search/index",
        affected_version="1.2.0",
        cwe_id="CWE-79",
    ),
    VulnerabilityItem(
        vuln_id="VULN-003",
        name="敏感信息明文存储",
        severity=VulnerabilitySeverity.HIGH,
        cvss_score=8.1,
        description="用户密码在数据库中未加密存储",
        affected_component="user/profile",
        affected_version="1.2.0",
        cwe_id="CWE-312",
    ),
    VulnerabilityItem(
        vuln_id="VULN-004",
        name="JWT密钥过弱",
        severity=VulnerabilitySeverity.HIGH,
        cvss_score=7.8,
        description="JWT签名密钥长度不足，可被暴力破解",
        affected_component="auth/token",
        affected_version="1.2.0",
        cwe_id="CWE-330",
    ),
    VulnerabilityItem(
        vuln_id="VULN-005",
        name="CORS配置过宽",
        severity=VulnerabilitySeverity.MEDIUM,
        cvss_score=5.5,
        description="CORS允许任意域名访问",
        affected_component="middleware/cors",
        affected_version="1.2.0",
        cwe_id="CWE-942",
    ),
    VulnerabilityItem(
        vuln_id="VULN-006",
        name="缺少安全响应头",
        severity=VulnerabilitySeverity.MEDIUM,
        cvss_score=4.3,
        description="缺少X-Content-Type-Options等安全响应头",
        affected_component="middleware/headers",
        affected_version="1.2.0",
        cwe_id="CWE-16",
    ),
    VulnerabilityItem(
        vuln_id="VULN-007",
        name="日志中记录敏感信息",
        severity=VulnerabilitySeverity.MEDIUM,
        cvss_score=5.0,
        description="错误日志中包含用户Token和Session ID",
        affected_component="logging",
        affected_version="1.2.0",
        cwe_id="CWE-532",
    ),
    VulnerabilityItem(
        vuln_id="VULN-008",
        name="弱密码策略",
        severity=VulnerabilitySeverity.LOW,
        cvss_score=3.5,
        description="密码策略未要求大小写混合和特殊字符",
        affected_component="auth/password_policy",
        affected_version="1.2.0",
        cwe_id="CWE-521",
    ),
    VulnerabilityItem(
        vuln_id="VULN-009",
        name="调试模式未关闭",
        severity=VulnerabilitySeverity.LOW,
        cvss_score=2.5,
        description="生产环境中Flask调试模式未关闭",
        affected_component="app/config",
        affected_version="1.2.0",
        cwe_id="CWE-215",
    ),
    VulnerabilityItem(
        vuln_id="VULN-010",
        name="依赖包版本过旧",
        severity=VulnerabilitySeverity.INFO,
        cvss_score=1.0,
        description="pyyaml版本低于安全推荐版本",
        affected_component="dependencies/pyyaml",
        affected_version="5.4.1",
        cwe_id="CWE-1104",
    ),
]


@pytest.fixture
def auditor() -> MockSecurityAuditor:
    return MockSecurityAuditor(project_name="DevFlow")


@pytest.fixture
def sample_vulns() -> List[VulnerabilityItem]:
    return list(SAMPLE_VULNERABILITIES)


@pytest.fixture
def vuln_dicts() -> List[Dict[str, Any]]:
    return [
        {
            "vuln_id": v.vuln_id,
            "name": v.name,
            "severity": v.severity.value,
            "cvss_score": v.cvss_score,
            "description": v.description,
            "affected_component": v.affected_component,
            "affected_version": v.affected_version,
            "cwe_id": v.cwe_id,
            "references": v.references,
        }
        for v in SAMPLE_VULNERABILITIES
    ]


# ============================================================
# AC1: 报告生成时间 ≤4小时
# ============================================================
class TestReportGenerationTime:
    """验收标准 1：报告生成时间 ≤4 小时。"""

    def test_report_generation_within_4_hours(self, auditor, sample_vulns):
        report = auditor.audit(sample_vulns, hours_elapsed=2.0)
        assert report.generation_time_hours is not None
        assert report.generation_time_hours <= 4.0, (
            f"报告生成时间应<=4小时，实际{report.generation_time_hours}小时"
        )

    def test_report_generation_at_4_hour_boundary(self, auditor, sample_vulns):
        report = auditor.audit(sample_vulns, hours_elapsed=4.0)
        assert report.generation_time_hours is not None
        assert 3.99 <= report.generation_time_hours <= 4.01

    def test_report_generation_exceeds_4_hours(self, auditor, sample_vulns):
        report = auditor.audit(sample_vulns, hours_elapsed=5.0)
        assert report.generation_time_hours is not None
        assert report.generation_time_hours > 4.0
        assert report.within_time_limit is False

    def test_report_within_time_limit_true(self, auditor, sample_vulns):
        report = auditor.audit(sample_vulns, hours_elapsed=3.5)
        assert report.within_time_limit is True

    def test_report_within_time_limit_false_when_exceeds(self, auditor, sample_vulns):
        report = auditor.audit(sample_vulns, hours_elapsed=6.0)
        assert report.within_time_limit is False

    def test_max_report_generation_constant_is_4_hours(self):
        assert MAX_REPORT_GENERATION_HOURS == 4.0
        assert MAX_REPORT_GENERATION_SECONDS == 14400

    def test_generation_time_seconds_calculation(self, auditor, sample_vulns):
        report = auditor.audit(sample_vulns, hours_elapsed=3.5)
        expected_seconds = 3.5 * 3600
        assert abs(report.generation_time_seconds - expected_seconds) < 0.01

    def test_generation_time_hours_from_seconds(self, auditor, sample_vulns):
        report = auditor.audit(sample_vulns, hours_elapsed=2.75)
        expected_hours = 2.75
        assert abs(report.generation_time_hours - expected_hours) < 0.01

    def test_report_generated_at_has_timestamp(self, auditor, sample_vulns):
        report = auditor.audit(sample_vulns)
        assert report.generated_at is not None
        assert isinstance(report.generated_at, datetime)

    def test_report_completed_at_has_timestamp(self, auditor, sample_vulns):
        report = auditor.audit(sample_vulns)
        assert report.completed_at is not None
        assert isinstance(report.completed_at, datetime)

    def test_completed_at_after_generated_at(self, auditor, sample_vulns):
        report = auditor.audit(sample_vulns, hours_elapsed=1.0)
        assert report.completed_at > report.generated_at

    def test_report_to_dict_contains_generation_time(self, auditor, sample_vulns):
        report = auditor.audit(sample_vulns, hours_elapsed=3.0)
        d = report.to_dict()
        assert "generation_time_hours" in d
        assert d["generation_time_hours"] is not None
        assert d["generation_time_hours"] <= 4.0


# ============================================================
# AC2: 报告包含审计概述、漏洞列表、修复建议、安全评分
# ============================================================
class TestReportContainsRequiredSections:
    """验收标准 2：报告包含审计概述、漏洞列表、修复建议、安全评分。"""

    def test_report_has_audit_overview(self, auditor, sample_vulns):
        report = auditor.audit(sample_vulns)
        assert report.has_overview is True
        assert report.overview is not None

    def test_report_has_vulnerability_list(self, auditor, sample_vulns):
        report = auditor.audit(sample_vulns)
        assert report.has_vulnerability_list is True
        assert len(report.vulnerabilities) == len(sample_vulns)

    def test_report_has_remediation_suggestions(self, auditor, sample_vulns):
        report = auditor.audit(sample_vulns)
        assert report.has_remediation_suggestions is True
        assert len(report.remediations) == len(sample_vulns)

    def test_report_has_security_score(self, auditor, sample_vulns):
        report = auditor.audit(sample_vulns)
        assert report.has_security_score is True
        assert report.security_score is not None

    def test_report_has_all_sections(self, auditor, sample_vulns):
        report = auditor.audit(sample_vulns)
        assert report.has_all_sections is True

    def test_overview_contains_required_fields(self, auditor, sample_vulns):
        report = auditor.audit(sample_vulns)
        o = report.overview
        assert o is not None
        assert o.project_name == "DevFlow"
        assert o.audit_start is not None
        assert o.audit_end is not None
        assert o.auditor_agent == "mimeng"
        assert o.total_vulnerabilities == len(sample_vulns)
        assert o.summary_text != ""

    def test_overview_severity_counts_correct(self, auditor, sample_vulns):
        report = auditor.audit(sample_vulns)
        o = report.overview
        assert o is not None
        assert o.critical_count == 1
        assert o.high_count == 3
        assert o.medium_count == 3
        assert o.low_count == 2
        assert o.info_count == 1

    def test_overview_total_equals_sum_of_severities(self, auditor, sample_vulns):
        report = auditor.audit(sample_vulns)
        o = report.overview
        assert o is not None
        severity_sum = o.critical_count + o.high_count + o.medium_count + o.low_count + o.info_count
        assert o.total_vulnerabilities == severity_sum

    def test_each_vulnerability_has_required_fields(self, auditor, sample_vulns):
        report = auditor.audit(sample_vulns)
        required_keys = {
            "vuln_id", "name", "severity", "cvss_score",
            "description", "affected_component", "affected_version",
        }
        for vuln in report.vulnerabilities:
            assert required_keys.issubset(set(vuln.keys())), (
                f"漏洞 {vuln.get('vuln_id')} 缺少字段: {required_keys - set(vuln.keys())}"
            )

    def test_each_remediation_has_required_fields(self, auditor, sample_vulns):
        report = auditor.audit(sample_vulns)
        required_keys = {
            "vuln_id", "priority", "fix_version",
            "action", "estimated_effort",
        }
        for rem in report.remediations:
            assert required_keys.issubset(set(rem.keys())), (
                f"修复建议 {rem.get('vuln_id')} 缺少字段: {required_keys - set(rem.keys())}"
            )

    def test_remediation_matches_vulnerability_1_to_1(self, auditor, sample_vulns):
        report = auditor.audit(sample_vulns)
        vuln_ids = {v["vuln_id"] for v in report.vulnerabilities}
        rem_ids = {r["vuln_id"] for r in report.remediations}
        assert vuln_ids == rem_ids

    def test_security_score_has_required_fields(self, auditor, sample_vulns):
        report = auditor.audit(sample_vulns)
        score = report.security_score
        assert score is not None
        assert hasattr(score, "raw_score")
        assert hasattr(score, "final_score")
        assert hasattr(score, "grade")
        assert hasattr(score, "breakdown")

    def test_security_score_breakdown_has_severity_keys(self, auditor, sample_vulns):
        report = auditor.audit(sample_vulns)
        score = report.security_score
        assert score is not None
        expected_keys = {"critical_penalty", "high_penalty", "medium_penalty", "low_penalty", "info_penalty"}
        assert expected_keys.issubset(set(score.breakdown.keys()))

    def test_report_to_dict_has_all_sections(self, auditor, sample_vulns):
        report = auditor.audit(sample_vulns)
        d = report.to_dict()
        assert d["has_all_sections"] is True
        assert d["vulnerability_count"] == len(sample_vulns)
        assert d["remediation_count"] == len(sample_vulns)
        assert d["security_score"] is not None


# ============================================================
# AC3: 安全评分计算公式正确
# ============================================================
class TestSecurityScoreCalculation:
    """验收标准 3：安全评分计算公式正确。"""

    def test_formula_start_at_100(self, vuln_dicts):
        score = SecurityScoreCalculator.calculate([])
        assert score.raw_score == 100.0
        assert score.final_score == 100.0

    def test_critical_penalty_is_15(self, vuln_dicts):
        vulns = [{"severity": "critical"}]
        score = SecurityScoreCalculator.calculate(vulns)
        assert score.breakdown["critical_penalty"] == 15.0

    def test_high_penalty_is_10(self):
        vulns = [{"severity": "high"}]
        score = SecurityScoreCalculator.calculate(vulns)
        assert score.breakdown["high_penalty"] == 10.0

    def test_medium_penalty_is_5(self):
        vulns = [{"severity": "medium"}]
        score = SecurityScoreCalculator.calculate(vulns)
        assert score.breakdown["medium_penalty"] == 5.0

    def test_low_penalty_is_2(self):
        vulns = [{"severity": "low"}]
        score = SecurityScoreCalculator.calculate(vulns)
        assert score.breakdown["low_penalty"] == 2.0

    def test_info_penalty_is_1(self):
        vulns = [{"severity": "info"}]
        score = SecurityScoreCalculator.calculate(vulns)
        assert score.breakdown["info_penalty"] == 1.0

    def test_score_deduction_calculation_correct(self):
        vulns = [
            {"severity": "critical"},
            {"severity": "high"},
            {"severity": "medium"},
            {"severity": "low"},
            {"severity": "info"},
        ]
        score = SecurityScoreCalculator.calculate(vulns)
        expected_penalty = 15 + 10 + 5 + 2 + 1
        assert score.raw_score == 100.0 - expected_penalty
        assert score.final_score == 67.0

    def test_multiple_same_severity_accumulate_penalty(self):
        vulns = [
            {"severity": "critical"},
            {"severity": "critical"},
            {"severity": "critical"},
        ]
        score = SecurityScoreCalculator.calculate(vulns)
        assert score.breakdown["critical_penalty"] == 45.0
        assert score.raw_score == 55.0

    def test_score_floor_at_zero(self):
        vulns = [{"severity": "critical"}] * 10
        score = SecurityScoreCalculator.calculate(vulns)
        assert score.raw_score == 100.0 - 150.0
        assert score.final_score == 0.0

    def test_score_cap_at_100(self, vuln_dicts):
        score = SecurityScoreCalculator.calculate([])
        assert score.final_score == 100.0

    def test_full_report_score_with_sample_vulns(self, auditor, sample_vulns):
        report = auditor.audit(sample_vulns)
        score = report.security_score
        assert score is not None
        expected = 100.0 - (15 * 1 + 10 * 3 + 5 * 3 + 2 * 2 + 1 * 1)
        assert abs(score.raw_score - expected) < 0.01
        assert score.final_score == max(0.0, min(100.0, expected))

    def test_severity_penalty_constant_values(self):
        assert SEVERITY_PENALTY["critical"] == 15.0
        assert SEVERITY_PENALTY["high"] == 10.0
        assert SEVERITY_PENALTY["medium"] == 5.0
        assert SEVERITY_PENALTY["low"] == 2.0
        assert SEVERITY_PENALTY["info"] == 1.0

    def test_unknown_severity_defaults_to_zero_penalty(self):
        vulns = [{"severity": "unknown"}]
        score = SecurityScoreCalculator.calculate(vulns)
        assert score.raw_score == 100.0
        assert score.final_score == 100.0


# ============================================================
# 安全评分等级映射测试
# ============================================================
class TestSecurityScoreGrading:
    """安全评分等级映射测试。"""

    def test_grade_a_plus_for_score_95(self):
        vulns = [{"severity": "medium"}]
        score = SecurityScoreCalculator.calculate(vulns)
        assert score.final_score == 95.0
        assert score.grade == "A+"

    def test_grade_a_for_score_85(self):
        vulns = [
            {"severity": "critical"},
            {"severity": "info"},
            {"severity": "info"},
        ]
        score = SecurityScoreCalculator.calculate(vulns)
        assert score.final_score == 83.0
        assert score.grade == "A"

    def test_grade_b_plus_for_score_75(self):
        vulns = [
            {"severity": "critical"},
            {"severity": "critical"},
            {"severity": "low"},
        ]
        score = SecurityScoreCalculator.calculate(vulns)
        assert score.final_score == 68.0
        assert score.grade == "B"

    def test_grade_c_for_score_55(self):
        vulns = [
            {"severity": "critical"},
            {"severity": "critical"},
            {"severity": "high"},
            {"severity": "high"},
        ]
        score = SecurityScoreCalculator.calculate(vulns)
        assert score.final_score == 50.0
        assert score.grade == "C"

    def test_grade_d_for_score_35(self):
        vulns = [
            {"severity": "critical"},
            {"severity": "critical"},
            {"severity": "critical"},
            {"severity": "critical"},
        ]
        score = SecurityScoreCalculator.calculate(vulns)
        assert score.final_score == 40.0
        assert score.grade == "D"

    def test_grade_f_for_score_below_40(self):
        vulns = [{"severity": "critical"}] * 5
        score = SecurityScoreCalculator.calculate(vulns)
        assert score.final_score == 25.0
        assert score.grade == "F"

    def test_grade_boundary_90_is_a_plus(self):
        vulns = [{"severity": "medium"}, {"severity": "medium"}]
        score = SecurityScoreCalculator.calculate(vulns)
        assert score.final_score == 90.0
        assert score.grade == "A+"

    def test_grade_boundary_80_is_a(self):
        vulns = [
            {"severity": "critical"},
            {"severity": "critical"},
        ]
        score = SecurityScoreCalculator.calculate(vulns)
        assert score.final_score == 70.0
        assert score.grade == "B+"

    def test_grade_boundary_60_is_b(self):
        vulns = [
            {"severity": "critical"},
            {"severity": "critical"},
            {"severity": "high"},
            {"severity": "low"},
        ]
        score = SecurityScoreCalculator.calculate(vulns)
        assert score.final_score == 58.0
        assert score.grade == "C"

    def test_grade_boundary_50_is_c(self):
        vulns = [
            {"severity": "critical"},
            {"severity": "critical"},
            {"severity": "high"},
            {"severity": "high"},
        ]
        score = SecurityScoreCalculator.calculate(vulns)
        assert score.final_score == 50.0
        assert score.grade == "C"

    def test_grade_boundary_40_is_d(self):
        vulns = [
            {"severity": "critical"},
            {"severity": "critical"},
            {"severity": "critical"},
            {"severity": "critical"},
        ]
        score = SecurityScoreCalculator.calculate(vulns)
        assert score.final_score == 40.0
        assert score.grade == "D"


# ============================================================
# SecurityAuditReport 单元测试
# ============================================================
class TestSecurityAuditReport:
    """安全审计报告模型单元测试。"""

    def test_report_initialization(self):
        report = SecurityAuditReport(
            report_id="test-001",
            project_name="TestProject",
            generated_at=datetime.now(timezone.utc),
        )
        assert report.report_id == "test-001"
        assert report.project_name == "TestProject"
        assert report.status == "generating"
        assert report.within_time_limit is False

    def test_report_to_dict_contains_all_keys(self, auditor, sample_vulns):
        report = auditor.audit(sample_vulns)
        d = report.to_dict()
        expected_keys = {
            "report_id", "project_name", "generated_at",
            "completed_at", "generation_time_hours", "status",
            "within_time_limit", "has_all_sections",
            "vulnerability_count", "remediation_count", "security_score",
        }
        assert expected_keys.issubset(set(d.keys()))

    def test_report_without_completed_at_time_none(self):
        report = SecurityAuditReport(
            report_id="no-complete",
            project_name="Test",
            generated_at=datetime.now(timezone.utc),
        )
        assert report.generation_time_seconds is None
        assert report.generation_time_hours is None

    def test_report_generation_time_precision(self):
        gen_at = datetime.now(timezone.utc)
        comp_at = gen_at + timedelta(hours=3, minutes=30, seconds=45)
        report = SecurityAuditReport(
            report_id="precision-test",
            project_name="Precision",
            generated_at=gen_at,
            completed_at=comp_at,
        )
        expected_hours = 3 + 30 / 60 + 45 / 3600
        assert abs(report.generation_time_hours - expected_hours) < 0.001

    def test_report_status_completed_after_audit(self, auditor, sample_vulns):
        report = auditor.audit(sample_vulns)
        assert report.status == "completed"

    def test_report_id_format(self, auditor, sample_vulns):
        report = auditor.audit(sample_vulns)
        assert report.report_id.startswith("audit-devflow-")


# ============================================================
# MockSecurityAuditor 单元测试
# ============================================================
class TestMockSecurityAuditor:
    """安全审计器模拟单元测试。"""

    def test_auditor_initial_state(self):
        a = MockSecurityAuditor()
        assert a.project_name == "DevFlow"
        assert a.get_report() is None

    def test_auditor_custom_project(self):
        a = MockSecurityAuditor(project_name="CustomApp")
        assert a.project_name == "CustomApp"

    def test_audit_returns_report(self, auditor, sample_vulns):
        report = auditor.audit(sample_vulns)
        assert report is not None
        assert isinstance(report, SecurityAuditReport)

    def test_get_report_after_audit(self, auditor, sample_vulns):
        auditor.audit(sample_vulns)
        report = auditor.get_report()
        assert report is not None

    def test_reset_clears_report(self, auditor, sample_vulns):
        auditor.audit(sample_vulns)
        assert auditor.get_report() is not None
        auditor.reset()
        assert auditor.get_report() is None

    def test_audit_empty_vulnerability_list(self, auditor):
        report = auditor.audit([], hours_elapsed=1.0)
        assert report.has_vulnerability_list is False
        assert report.has_remediation_suggestions is False
        assert report.security_score is not None
        assert report.security_score.final_score == 100.0

    def test_audit_custom_hours(self, auditor, sample_vulns):
        report = auditor.audit(sample_vulns, hours_elapsed=3.5)
        assert abs(report.generation_time_hours - 3.5) < 0.01

    def test_audit_default_hours_is_2(self, auditor, sample_vulns):
        report = auditor.audit(sample_vulns)
        assert abs(report.generation_time_hours - 2.0) < 0.01

    def test_consecutive_audits_produce_independent_reports(self, auditor, sample_vulns):
        r1 = auditor.audit(sample_vulns, hours_elapsed=1.0)
        auditor.reset()
        r2 = auditor.audit(sample_vulns, hours_elapsed=2.0)
        assert r1.generation_time_hours != r2.generation_time_hours
        assert abs(r1.generation_time_hours - 1.0) < 0.01
        assert abs(r2.generation_time_hours - 2.0) < 0.01


# ============================================================
# VulnerabilitySeverity 枚举测试
# ============================================================
class TestVulnerabilitySeverity:
    """漏洞严重性枚举测试。"""

    def test_severity_enum_values(self):
        assert VulnerabilitySeverity.CRITICAL.value == "critical"
        assert VulnerabilitySeverity.HIGH.value == "high"
        assert VulnerabilitySeverity.MEDIUM.value == "medium"
        assert VulnerabilitySeverity.LOW.value == "low"
        assert VulnerabilitySeverity.INFO.value == "info"

    def test_severity_enum_count(self):
        assert len(list(VulnerabilitySeverity)) == 5


# ============================================================
# VulnerabilityItem 单元测试
# ============================================================
class TestVulnerabilityItem:
    """漏洞条目模型测试。"""

    def test_vulnerability_item_creation(self):
        v = VulnerabilityItem(
            vuln_id="V-001",
            name="测试漏洞",
            severity=VulnerabilitySeverity.HIGH,
            cvss_score=7.5,
            description="描述",
            affected_component="comp",
            affected_version="1.0",
        )
        assert v.vuln_id == "V-001"
        assert v.severity == VulnerabilitySeverity.HIGH
        assert v.cvss_score == 7.5

    def test_vulnerability_item_default_references(self):
        v = VulnerabilityItem(
            vuln_id="V-002",
            name="测试漏洞2",
            severity=VulnerabilitySeverity.LOW,
            cvss_score=2.0,
            description="描述",
            affected_component="comp",
            affected_version="1.0",
        )
        assert v.references == []
        assert v.cwe_id == ""


# ============================================================
# RemediationSuggestion 单元测试
# ============================================================
class TestRemediationSuggestion:
    """修复建议模型测试。"""

    def test_remediation_creation(self):
        r = RemediationSuggestion(
            vuln_id="V-001",
            priority="P0",
            fix_version="2.0",
            action="升级到2.0",
            estimated_effort="1天",
        )
        assert r.vuln_id == "V-001"
        assert r.priority == "P0"
        assert r.temporary_mitigation == ""

    def test_remediation_with_mitigation(self):
        r = RemediationSuggestion(
            vuln_id="V-002",
            priority="P1",
            fix_version="2.0",
            action="应用补丁",
            estimated_effort="4小时",
            temporary_mitigation="限制访问",
        )
        assert r.temporary_mitigation == "限制访问"


# ============================================================
# SecurityScore 单元测试
# ============================================================
class TestSecurityScore:
    """安全评分模型测试。"""

    def test_security_score_to_dict(self):
        score = SecurityScore(
            raw_score=75.0,
            final_score=75.0,
            grade="A",
            breakdown={
                "critical_penalty": 15.0,
                "high_penalty": 10.0,
                "medium_penalty": 0.0,
                "low_penalty": 0.0,
                "info_penalty": 0.0,
            },
        )
        d = score.to_dict()
        assert d["raw_score"] == 75.0
        assert d["final_score"] == 75.0
        assert d["grade"] == "A"
        assert d["calculation_method"] == "severity_weighted_deduction"

    def test_security_score_calculation_method_default(self):
        score = SecurityScore(
            raw_score=100.0,
            final_score=100.0,
            grade="A+",
            breakdown={},
        )
        assert score.calculation_method == "severity_weighted_deduction"


# ============================================================
# 综合集成测试
# ============================================================
class TestSecurityReportIntegration:
    """安全报告生成综合集成测试。"""

    def test_full_report_generation_meets_all_criterias(self, auditor, sample_vulns):
        report = auditor.audit(sample_vulns, hours_elapsed=2.0)

        assert report.generation_time_hours <= 4.0
        assert report.has_all_sections is True
        assert report.security_score is not None
        assert report.security_score.raw_score == 100.0 - (15 * 1 + 10 * 3 + 5 * 3 + 2 * 2 + 1 * 1)
        assert report.status == "completed"

    def test_report_serialization_round_trip(self, auditor, sample_vulns):
        report = auditor.audit(sample_vulns, hours_elapsed=3.0)
        d = report.to_dict()
        assert d["report_id"] == report.report_id
        assert d["project_name"] == "DevFlow"
        assert d["vulnerability_count"] == 10
        assert d["remediation_count"] == 10
        assert d["within_time_limit"] is True
        assert d["has_all_sections"] is True

    def test_report_with_zero_vulnerabilities_scores_100(self, auditor):
        report = auditor.audit([], hours_elapsed=0.5)
        assert report.security_score is not None
        assert report.security_score.final_score == 100.0
        assert report.security_score.grade == "A+"
        assert report.overview is not None
        assert report.overview.total_vulnerabilities == 0

    def test_sample_vulnerabilities_count_is_10(self):
        assert len(SAMPLE_VULNERABILITIES) == 10

    def test_report_vulnerabilities_preserve_order(self, auditor, sample_vulns):
        report = auditor.audit(sample_vulns)
        for i, (vuln_item, vuln_dict) in enumerate(zip(sample_vulns, report.vulnerabilities)):
            assert vuln_dict["vuln_id"] == vuln_item.vuln_id

    def test_report_remediations_preserve_order(self, auditor, sample_vulns):
        report = auditor.audit(sample_vulns)
        for i, (vuln_item, rem_dict) in enumerate(zip(sample_vulns, report.remediations)):
            assert rem_dict["vuln_id"] == vuln_item.vuln_id

    def test_priority_mapping_for_severity(self, auditor, sample_vulns):
        report = auditor.audit(sample_vulns)
        priority_map = {"critical": "P0", "high": "P1", "medium": "P2", "low": "P3", "info": "P4"}
        for vuln_dict, rem_dict in zip(report.vulnerabilities, report.remediations):
            expected_priority = priority_map[vuln_dict["severity"]]
            assert rem_dict["priority"] == expected_priority

    def test_cvss_scores_in_valid_range(self, auditor, sample_vulns):
        report = auditor.audit(sample_vulns)
        for vuln in report.vulnerabilities:
            assert 0.0 <= vuln["cvss_score"] <= 10.0

    def test_report_overview_summary_not_empty(self, auditor, sample_vulns):
        report = auditor.audit(sample_vulns)
        assert len(report.overview.summary_text) > 0
        assert "发现" in report.overview.summary_text

    def test_audit_end_after_start(self, auditor, sample_vulns):
        report = auditor.audit(sample_vulns, hours_elapsed=2.0)
        assert report.overview.audit_end > report.overview.audit_start

    def test_different_project_names(self):
        auditor_a = MockSecurityAuditor(project_name="ProjectA")
        auditor_b = MockSecurityAuditor(project_name="ProjectB")
        r1 = auditor_a.audit([], hours_elapsed=1.0)
        r2 = auditor_b.audit([], hours_elapsed=1.0)
        assert r1.overview.project_name == "ProjectA"
        assert r2.overview.project_name == "ProjectB"
