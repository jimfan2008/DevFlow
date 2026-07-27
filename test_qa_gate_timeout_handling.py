import pytest
import re
from dataclasses import dataclass
from typing import List, Optional


@dataclass
class TimeoutHandlingClause:
    condition: str
    action: str
    timeout_value: str
    section_ref: str


@dataclass
class QAGateDescription:
    timeout_handling: Optional[List[TimeoutHandlingClause]] = None


@dataclass
class FeaturePoint:
    id: str
    name: str
    qa_gate: QAGateDescription


def build_sample_srs_document() -> List[FeaturePoint]:
    return [
        FeaturePoint(
            id="FP-001",
            name="用户登录",
            qa_gate=QAGateDescription(
                timeout_handling=[
                    TimeoutHandlingClause(
                        condition="登录请求超时",
                        action="返回超时错误并提示用户重试",
                        timeout_value="5s",
                        section_ref="4.2",
                    )
                ]
            ),
        ),
        FeaturePoint(
            id="FP-002",
            name="数据导出",
            qa_gate=QAGateDescription(
                timeout_handling=[
                    TimeoutHandlingClause(
                        condition="导出操作超时",
                        action="终止导出任务，记录错误日志",
                        timeout_value="30s",
                        section_ref="4.2",
                    ),
                    TimeoutHandlingClause(
                        condition="大文件下载超时",
                        action="分片下载并允许断点续传",
                        timeout_value="120s",
                        section_ref="4.2",
                    ),
                ]
            ),
        ),
        FeaturePoint(
            id="FP-003",
            name="第三方支付回调",
            qa_gate=QAGateDescription(
                timeout_handling=[
                    TimeoutHandlingClause(
                        condition="支付回调等待超时",
                        action="主动查询支付状态并补偿",
                        timeout_value="10s",
                        section_ref="4.2",
                    )
                ]
            ),
        ),
        FeaturePoint(
            id="FP-004",
            name="实时消息推送",
            qa_gate=QAGateDescription(
                timeout_handling=[
                    TimeoutHandlingClause(
                        condition="WebSocket连接超时",
                        action="触发重连机制，指数退避",
                        timeout_value="15s",
                        section_ref="4.2",
                    )
                ]
            ),
        ),
        FeaturePoint(
            id="FP-005",
            name="批量任务调度",
            qa_gate=QAGateDescription(
                timeout_handling=[
                    TimeoutHandlingClause(
                        condition="单个子任务超时",
                        action="跳过该子任务并记录失败",
                        timeout_value="60s",
                        section_ref="4.2",
                    )
                ]
            ),
        ),
    ]


def build_srs_with_missing_timeout() -> List[FeaturePoint]:
    """Returns an SRS where FP-003 has zero timeout clauses — used for negative test."""
    features = build_sample_srs_document()
    features[2].qa_gate.timeout_handling = []
    return features


def build_srs_with_wrong_section_ref() -> List[FeaturePoint]:
    """Returns an SRS where FP-002's second clause refs '3.1' — used for negative test."""
    features = build_sample_srs_document()
    features[1].qa_gate.timeout_handling[1].section_ref = "3.1"
    return features


# ---------------------------------------------------------------------------
# Boundary-case helpers
# ---------------------------------------------------------------------------


def build_srs_with_none_timeout_handling() -> List[FeaturePoint]:
    """Returns an SRS where FP-003 has timeout_handling set to None."""
    features = build_sample_srs_document()
    features[2].qa_gate.timeout_handling = None
    return features


def build_srs_with_empty_section_ref() -> List[FeaturePoint]:
    """Returns an SRS where FP-004's clause has an empty section_ref."""
    features = build_sample_srs_document()
    features[3].qa_gate.timeout_handling[0].section_ref = ""
    return features


def build_srs_with_none_section_ref() -> List[FeaturePoint]:
    """Returns an SRS where FP-005's clause has a None section_ref."""
    features = build_sample_srs_document()
    features[4].qa_gate.timeout_handling[0].section_ref = None
    return features


def build_srs_with_duplicate_clauses() -> List[FeaturePoint]:
    """Returns an SRS where FP-001 has an identical duplicate timeout clause."""
    features = build_sample_srs_document()
    duplicate = TimeoutHandlingClause(
        condition="登录请求超时",
        action="返回超时错误并提示用户重试",
        timeout_value="5s",
        section_ref="4.2",
    )
    features[0].qa_gate.timeout_handling.append(duplicate)
    return features


def build_srs_with_invalid_timeout_values() -> List[FeaturePoint]:
    """Returns a dedicated feature with clauses covering extreme/illegal timeout values."""
    return [
        FeaturePoint(
            id="FP-BOUNDARY",
            name="边界时间值测试",
            qa_gate=QAGateDescription(
                timeout_handling=[
                    TimeoutHandlingClause(
                        condition="零秒超时",
                        action="立即超时",
                        timeout_value="0s",
                        section_ref="4.2",
                    ),
                    TimeoutHandlingClause(
                        condition="负数超时",
                        action="无效超时",
                        timeout_value="-1s",
                        section_ref="4.2",
                    ),
                    TimeoutHandlingClause(
                        condition="非数字格式",
                        action="格式错误",
                        timeout_value="five seconds",
                        section_ref="4.2",
                    ),
                    TimeoutHandlingClause(
                        condition="极大超时值",
                        action="近似无超时",
                        timeout_value="999999s",
                        section_ref="4.2",
                    ),
                    TimeoutHandlingClause(
                        condition="空超时值",
                        action="未定义",
                        timeout_value="",
                        section_ref="4.2",
                    ),
                ]
            ),
        ),
    ]


# ---------------------------------------------------------------------------
# Positive tests — valid SRS document
# ---------------------------------------------------------------------------


class TestQAGateTimeoutHandlingCoverage:
    """Verify that every feature point in the SRS document has full timeout
    handling coverage with section references pointing to 4.2."""

    def test_every_feature_point_has_at_least_one_timeout_clause(self):
        srs = build_sample_srs_document()
        for fp in srs:
            assert fp.qa_gate.timeout_handling is not None, (
                f"{fp.id} ({fp.name}) has None timeout_handling"
            )
            assert len(fp.qa_gate.timeout_handling) > 0, (
                f"{fp.id} ({fp.name}) has zero timeout handling clauses"
            )

    def test_every_timeout_clause_section_ref_points_to_4_2(self):
        srs = build_sample_srs_document()
        for fp in srs:
            for clause in fp.qa_gate.timeout_handling:
                assert clause.section_ref is not None, (
                    f"{fp.id} clause (condition='{clause.condition}') "
                    f"section_ref is None"
                )
                assert clause.section_ref == "4.2", (
                    f"{fp.id} clause (condition='{clause.condition}') "
                    f"section_ref is '{clause.section_ref}', expected '4.2'"
                )

    def test_every_clause_has_non_empty_condition_and_action(self):
        srs = build_sample_srs_document()
        for fp in srs:
            for clause in fp.qa_gate.timeout_handling:
                assert clause.condition.strip(), (
                    f"{fp.id} has empty condition"
                )
                assert clause.action.strip(), (
                    f"{fp.id} has empty action for condition '{clause.condition}'"
                )
                assert clause.timeout_value.strip(), (
                    f"{fp.id} has empty timeout_value for condition '{clause.condition}'"
                )

    def test_100_percent_feature_coverage(self):
        srs = build_sample_srs_document()
        feature_ids_with_timeout = {
            fp.id
            for fp in srs
            if fp.qa_gate.timeout_handling is not None
            and len(fp.qa_gate.timeout_handling) > 0
        }
        all_feature_ids = {fp.id for fp in srs}
        missing = all_feature_ids - feature_ids_with_timeout
        assert not missing, (
            f"Coverage gap: {len(missing)} feature(s) lack timeout handling: {missing}"
        )
        coverage = len(feature_ids_with_timeout) / len(all_feature_ids) if all_feature_ids else 1.0
        assert coverage == 1.0, f"Coverage rate is {coverage:.0%}, expected 100%"

    def test_total_clause_count_is_known(self):
        srs = build_sample_srs_document()
        total = sum(
            len(fp.qa_gate.timeout_handling) for fp in srs
            if fp.qa_gate.timeout_handling is not None
        )
        # Documented per-feature breakdown guards against accidental changes
        breakdown = {"FP-001": 1, "FP-002": 2, "FP-003": 1, "FP-004": 1, "FP-005": 1}
        expected = sum(breakdown.values())
        assert total == expected, (
            f"Expected {expected} total timeout clauses, found {total}. "
            f"Breakdown: {breakdown}"
        )


# ---------------------------------------------------------------------------
# Negative tests — deliberately broken SRS documents
# ---------------------------------------------------------------------------


class TestQAGateTimeoutHandlingFailureCases:
    """These tests verify that the detection logic correctly catches real
    defects: missing timeout clauses and wrong section references."""

    def test_detects_missing_timeout_handling(self):
        srs = build_srs_with_missing_timeout()
        failures = []
        for fp in srs:
            if not fp.qa_gate.timeout_handling:
                failures.append(fp.id)
        assert len(failures) == 1
        assert failures[0] == "FP-003"

    def test_detects_wrong_section_reference(self):
        srs = build_srs_with_wrong_section_ref()
        failures = []
        for fp in srs:
            for clause in fp.qa_gate.timeout_handling:
                if clause.section_ref != "4.2":
                    failures.append((fp.id, clause.condition, clause.section_ref))
        assert len(failures) == 1
        assert failures[0] == ("FP-002", "大文件下载超时", "3.1")

    def test_empty_srs_raises_no_false_positives(self):
        srs: List[FeaturePoint] = []
        assert len(srs) == 0
        all_ids = {fp.id for fp in srs}
        covered_ids = {
            fp.id for fp in srs
            if fp.qa_gate.timeout_handling is not None
            and len(fp.qa_gate.timeout_handling) > 0
        }
        assert all_ids == covered_ids


# ---------------------------------------------------------------------------
# Boundary tests — edge-case SRS documents
# ---------------------------------------------------------------------------


class TestQAGateTimeoutHandlingBoundaryCases:
    """Verify that boundary conditions (None values, empty fields, duplicates,
    extreme timeout values) are correctly detected and handled without crash."""

    def test_none_timeout_handling_is_detected(self):
        """When timeout_handling is None, detection logic must identify it as a gap."""
        srs = build_srs_with_none_timeout_handling()
        failures = []
        for fp in srs:
            if fp.qa_gate.timeout_handling is None:
                failures.append(fp.id)
        assert len(failures) == 1
        assert failures[0] == "FP-003"

    def test_none_timeout_handling_does_not_crash_iteration(self):
        """Iteration over a feature with None timeout_handling must not raise TypeError."""
        srs = build_srs_with_none_timeout_handling()
        collected = []
        for fp in srs:
            if fp.qa_gate.timeout_handling is None:
                collected.append((fp.id, None))
            else:
                collected.append((fp.id, len(fp.qa_gate.timeout_handling)))
        # Verify no crash occurred and all 5 features were processed
        assert len(collected) == 5
        # FP-003 should have None; others should have positive counts
        fp003 = [c for c in collected if c[0] == "FP-003"]
        assert fp003[0][1] is None
        others_with_clauses = [c for c in collected if c[0] != "FP-003" and c[1] is not None and c[1] > 0]
        assert len(others_with_clauses) == 4

    def test_empty_section_ref_is_detected(self):
        """A clause with an empty section_ref string must be flagged."""
        srs = build_srs_with_empty_section_ref()
        failures = []
        for fp in srs:
            for clause in fp.qa_gate.timeout_handling:
                if not clause.section_ref or clause.section_ref.strip() == "":
                    failures.append((fp.id, clause.condition))
        assert len(failures) == 1
        assert failures[0] == ("FP-004", "WebSocket连接超时")

    def test_none_section_ref_is_detected(self):
        """A clause with a None section_ref must be flagged."""
        srs = build_srs_with_none_section_ref()
        failures = []
        for fp in srs:
            for clause in fp.qa_gate.timeout_handling:
                if clause.section_ref is None:
                    failures.append((fp.id, clause.condition, clause.section_ref))
        assert len(failures) == 1
        assert failures[0] == ("FP-005", "单个子任务超时", None)

    def test_duplicate_clauses_are_detected(self):
        """Identical duplicate timeout clauses within the same feature must be detected."""
        srs = build_srs_with_duplicate_clauses()
        violations = []
        for fp in srs:
            seen = set()
            for clause in fp.qa_gate.timeout_handling:
                key = (clause.condition, clause.action, clause.timeout_value, clause.section_ref)
                if key in seen:
                    violations.append((fp.id, clause.condition, key))
                seen.add(key)
        assert len(violations) == 1
        assert violations[0][0] == "FP-001"

    def test_no_false_positive_on_unique_clauses(self):
        """Normal SRS with all unique clauses must not trigger duplicate detection."""
        srs = build_sample_srs_document()
        violations = []
        for fp in srs:
            seen = set()
            for clause in fp.qa_gate.timeout_handling:
                key = (clause.condition, clause.action, clause.timeout_value, clause.section_ref)
                if key in seen:
                    violations.append((fp.id, clause.condition))
                seen.add(key)
        assert len(violations) == 0

    def test_timeout_value_format_validation_detects_issues(self):
        """Timeout values with invalid format or extreme values must be flagged."""
        srs = build_srs_with_invalid_timeout_values()

        def _is_valid_timeout_value(tv: str) -> Optional[str]:
            """Returns a reason string if invalid, None if valid."""
            stripped = tv.strip()
            if not stripped:
                return "empty"
            if not re.match(r"^\d+s$", stripped):
                return f"format_invalid: '{tv}'"
            seconds = int(stripped.rstrip("s"))
            if seconds <= 0:
                return "non_positive"
            if seconds > 86400:
                return "extreme_value"
            return None

        flagged = []
        for fp in srs:
            for clause in fp.qa_gate.timeout_handling:
                reason = _is_valid_timeout_value(clause.timeout_value)
                if reason is not None:
                    flagged.append((fp.id, clause.condition, clause.timeout_value, reason))

        # Expected: 0s (non_positive), -1s (format_invalid), "five seconds" (format_invalid),
        #           999999s (extreme_value), "" (empty)
        assert len(flagged) == 5, f"Expected 5 flagged issues, got {len(flagged)}: {flagged}"
        reasons = {r[3] for r in flagged}
        assert "empty" in reasons
        assert "non_positive" in reasons or any("0s" in r[2] for r in flagged)
        assert any("format_invalid" in r[3] for r in flagged)

    def test_all_valid_timeout_values_pass_validation(self):
        """All timeout values from the sample SRS must pass basic format validation."""
        srs = build_sample_srs_document()
        for fp in srs:
            for clause in fp.qa_gate.timeout_handling:
                tv = clause.timeout_value.strip()
                assert tv, f"{fp.id} has empty timeout_value"
                assert re.match(r"^\d+s$", tv), (
                    f"{fp.id} timeout_value '{tv}' does not match expected format '\\d+s'"
                )
                seconds = int(tv.rstrip("s"))
                assert seconds > 0, f"{fp.id} timeout_value '{tv}' is not positive"
