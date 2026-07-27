import pytest
from dataclasses import dataclass, field
from typing import Any, Callable


@dataclass
class QAGateIssue:
    category: str
    severity: str
    description: str
    location: str | None = None


@dataclass
class QAGateResult:
    target_id: str
    passed: bool
    issues: list[QAGateIssue] = field(default_factory=list)
    error: str | None = None


@dataclass
class QAGateConfig:
    max_critical: int = 0
    max_major: int = 2
    max_minor: int = 5
    blocked_categories: set[str] = field(default_factory=lambda: set(["security", "data_loss"]))


class QAGate:
    def __init__(self, config = None):
        self.config = config or QAGateConfig()

    def check(self, target):
        target_id = target.get("id", "unknown")
        issues = []
        checkers = [
            ("null_safety", self._check_null_values),
            ("boundary", self._check_boundaries),
            ("type_safety", self._check_types),
            ("security", self._check_security),
            ("consistency", self._check_consistency),
        ]
        for name, checker in checkers:
            try:
                issues.extend(checker(target))
            except Exception as exc:
                return QAGateResult(
                    target_id=target_id, passed=False, issues=[],
                    error=f"Checker '{name}' failed: {exc}",
                )
        passed = self._evaluate_pass_fail(issues)
        return QAGateResult(target_id=target_id, passed=passed, issues=issues)

    def _evaluate_pass_fail(self, issues):
        c = sum(1 for i in issues if i.severity == "critical")
        m = sum(1 for i in issues if i.severity == "major")
        n = sum(1 for i in issues if i.severity == "minor")
        b = any(i.category in self.config.blocked_categories for i in issues)
        if b or c > self.config.max_critical:
            return False
        if m > self.config.max_major:
            return False
        if n > self.config.max_minor:
            return False
        return True

    def _check_null_values(self, target):
        issues = []
        for fn in ("name","version","checksum","timestamp"):
            if target.get(fn) is None:
                issues.append(QAGateIssue("null_safety","major",f"Required field '{fn}' is null",fn))
        return issues

    def _check_boundaries(self, target):
        issues = []
        d = target.get("duration_ms")
        if d is not None and isinstance(d, (int, float)):
            if d < 0: issues.append(QAGateIssue("boundary","critical",f"Negative duration: {d}ms","duration_ms"))
            elif d > 30000: issues.append(QAGateIssue("boundary","minor",f"Duration {d}ms exceeds 30s threshold","duration_ms"))
        s = target.get("size_bytes")
        if s is not None and isinstance(s, (int, float)):
            if s <= 0: issues.append(QAGateIssue("boundary","critical",f"Non-positive size: {s}","size_bytes"))
            elif s > 100000000: issues.append(QAGateIssue("boundary","major",f"Size {s} exceeds 100MB limit","size_bytes"))
        return issues

    def _check_types(self, target):
        issues = []
        checks = [("name",str,"name must be a string"),("version",str,"version must be a string"),("checksum",str,"checksum must be a string"),("duration_ms",(int,float),"duration_ms must be numeric")]
        for fn,et,msg in checks:
            v = target.get(fn)
            if v is not None and not isinstance(v, et): issues.append(QAGateIssue("type_safety","major",msg,fn))
        return issues

    def _check_security(self, target):
        issues = []
        cs = target.get("checksum","")
        if isinstance(cs, str) and cs.strip() == "": issues.append(QAGateIssue("security","critical","Empty checksum - integrity cannot be verified","checksum"))
        src = target.get("source")
        if src is not None and isinstance(src, str):
            if any(src.startswith(p) for p in ["../../","/etc/","|",";"]):
                issues.append(QAGateIssue("security","critical",f"Potentially malicious source path: '{src}'","source"))
        return issues

    def _check_consistency(self, target):
        issues = []
        v = target.get("version")
        dv = target.get("dep_version")
        if v and dv and isinstance(v, str) and isinstance(dv, str):
            if v > dv: issues.append(QAGateIssue("consistency","minor",f"Version {v} > dependency version {dv}","version/dep_version"))
        nm = target.get("name")
        fn = target.get("file_name")
        if nm and fn and isinstance(nm, str) and isinstance(fn, str):
            if nm not in fn: issues.append(QAGateIssue("consistency","minor",f"Name '{nm}' not found in file_name '{fn}'","name/file_name"))
        return issues


def _build_clean_target(target_id):
    return {
        "id": target_id,
        "name": "pkg-core",
        "version": "2.1.0",
        "checksum": "a1b2c3d4e5f6",
        "timestamp": 1712345678,
        "duration_ms": 1200,
        "size_bytes": 4096,
        "source": "/data/packages/pkg-core.tar.gz",
        "file_name": "pkg-core-v2.1.0.tar.gz",
        "dep_version": "2.1.0",
    }


def _seed_issue(target, issue_kind):
    t = dict(target)
    if issue_kind == "null_name": t["name"] = None
    elif issue_kind == "null_version": t["version"] = None
    elif issue_kind == "null_checksum": t["checksum"] = None
    elif issue_kind == "null_timestamp": t["timestamp"] = None
    elif issue_kind == "negative_duration": t["duration_ms"] = -500
    elif issue_kind == "oversize_duration": t["duration_ms"] = 60000
    elif issue_kind == "zero_size": t["size_bytes"] = 0
    elif issue_kind == "negative_size": t["size_bytes"] = -100
    elif issue_kind == "oversize": t["size_bytes"] = 200000000
    elif issue_kind == "wrong_name_type": t["name"] = 42
    elif issue_kind == "wrong_version_type": t["version"] = True
    elif issue_kind == "wrong_duration_type": t["duration_ms"] = "fast"
    elif issue_kind == "empty_checksum": t["checksum"] = ""
    elif issue_kind == "malicious_source_path_traversal": t["source"] = "../../etc/shadow"
    elif issue_kind == "malicious_source_pipe": t["source"] = "| rm -rf /"
    elif issue_kind == "version_drift": t["version"] = "3.0.0"; t["dep_version"] = "2.0.0"
    elif issue_kind == "name_file_mismatch": t["name"] = "pkg-other"; t["file_name"] = "pkg-core-v2.1.0.tar.gz"
    else: raise ValueError("Unknown issue_kind: " + issue_kind)
    return t

ISSUE_KINDS = [
    "null_name", "null_version", "null_checksum", "null_timestamp",
    "negative_duration", "oversize_duration", "zero_size", "negative_size",
    "oversize", "wrong_name_type", "wrong_version_type", "wrong_duration_type",
    "empty_checksum", "malicious_source_path_traversal", "malicious_source_pipe",
    "version_drift", "name_file_mismatch",
]


class _BadStr(str):
    def strip(self):
        raise RuntimeError("simulated checker crash")


class TestQAGateDetectionRate:

    @pytest.fixture
    def gate(self):
        return QAGate(QAGateConfig(max_critical=0, max_major=0, max_minor=0))

    def test_clean_target_passes(self, gate):
        r = gate.check(_build_clean_target("t1"))
        assert r.passed, f"Clean target should pass, got issues: {r.issues}"

    @pytest.mark.parametrize("kind", ISSUE_KINDS)
    def test_each_defect_is_detected(self, gate, kind):
        r = gate.check(_seed_issue(_build_clean_target("t1"), kind))
        assert not r.passed, "QA gate should reject target with defect: " + kind + ""

    def test_detection_rate_meets_threshold(self, gate):
        batch = []
        for i in range(50):
            batch.append((_build_clean_target(f"clean-{i}"), True))
        for idx, k in enumerate(ISSUE_KINDS):
            batch.append((_seed_issue(_build_clean_target(f"single-{idx}"), k), False))
        multi = [
            ("null_name", "negative_duration"),
            ("empty_checksum", "zero_size"),
            ("malicious_source_path_traversal", "oversize_duration"),
            ("null_checksum", "wrong_duration_type", "version_drift"),
            ("null_timestamp", "null_name"),
        ]
        for idx, combo in enumerate(multi):
            t = _build_clean_target(f"multi-{idx}")
            for k in combo: t = _seed_issue(t, k)
            batch.append((t, False))
        dc = sum(0 if e else 1 for _, e in batch)
        tp = fp = fn = tn = 0
        for target, exp in batch:
            r = gate.check(target)
            if not exp and not r.passed: tp += 1
            elif not exp and r.passed: fn += 1
            elif exp and not r.passed: fp += 1
            else: tn += 1
        dr = tp / dc if dc else 1.0
        mr = fn / dc if dc else 0.0
        print(f"DR: {dr:.2%} ({tp}/{dc}) MR: {mr:.2%} ({fn}/{dc})")
        assert dr >= 0.95, f"Detection rate {dr:.2%} < 95%"
        assert mr <= 0.05, f"Miss rate {mr:.2%} > 5%"

    def test_checker_crash_is_reported(self, gate):
        t = {"id": "crash-target", "checksum": _BadStr("")}
        r = gate.check(t)
        assert not r.passed
        assert r.error is not None
        assert "crash" in r.error.lower()

    def test_empty_target_is_rejected(self, gate):
        r = gate.check({"id": "empty"})
        assert not r.passed
        assert any("null" in i.category for i in r.issues)
