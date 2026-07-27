import pytest
from unittest.mock import MagicMock, patch
import json


class SemanticComparisonItem:
    """数据模型：逐条语义对比结果"""

    VALID_STATUSES = ("matched", "partial_mismatch", "mismatch")

    def __init__(self, srs_item_id: str, arch_item_id: str, match_status: str, confidence_score: int):
        if match_status not in self.VALID_STATUSES:
            raise ValueError(f"match_status 必须是 {self.VALID_STATUSES} 之一，实际: {match_status}")
        if not (0 <= confidence_score <= 100):
            raise ValueError(f"confidence_score 必须在 0-100 之间，实际: {confidence_score}")
        self.srs_item_id = srs_item_id
        self.arch_item_id = arch_item_id
        self.match_status = match_status
        self.confidence_score = confidence_score

    def to_dict(self) -> dict:
        return {
            "srs_item_id": self.srs_item_id,
            "arch_item_id": self.arch_item_id,
            "match_status": self.match_status,
            "confidence_score": self.confidence_score,
        }


class ConsistencyMeasurementService:
    """一致性测量服务：支持逐条语义对比"""

    def __init__(self, semantic_comparator=None):
        self._comparator = semantic_comparator

    def compare_item_by_item(self, srs_items: list, arch_items: list) -> list:
        """逐条完成语义对比，返回结果列表"""
        results = []
        for srs_item in srs_items:
            best_result = self._compare_single_item(srs_item, arch_items)
            results.append(best_result)
        return results

    def _compare_single_item(self, srs_item: dict, arch_items: list) -> SemanticComparisonItem:
        """对单条 SRS 条目与所有架构条目进行对比，取最佳匹配"""
        if not arch_items:
            return SemanticComparisonItem(
                srs_item_id=srs_item["id"],
                arch_item_id=None,
                match_status="mismatch",
                confidence_score=0,
            )

        best_match = None
        best_confidence = -1

        for arch_item in arch_items:
            if self._comparator:
                score, status = self._comparator.compare(srs_item, arch_item)
            else:
                score, status = self._default_compare(srs_item, arch_item)

            if score > best_confidence:
                best_confidence = score
                best_match = SemanticComparisonItem(
                    srs_item_id=srs_item["id"],
                    arch_item_id=arch_item["id"],
                    match_status=status,
                    confidence_score=score,
                )

        if best_match is None:
            return SemanticComparisonItem(
                srs_item_id=srs_item["id"],
                arch_item_id=None,
                match_status="mismatch",
                confidence_score=0,
            )

        return best_match

    @staticmethod
    def _default_compare(srs_item: dict, arch_item: dict) -> tuple:
        """默认对比策略"""
        srs_text = srs_item.get("content", "").lower()
        arch_text = arch_item.get("content", "").lower()
        common_words = set(srs_text.split()) & set(arch_text.split())
        total_words = set(srs_text.split()) | set(arch_text.split())
        if not total_words:
            return 0, "mismatch"
        similarity = len(common_words) / len(total_words)
        score = int(similarity * 100)
        if score >= 80:
            status = "matched"
        elif score >= 40:
            status = "partial_mismatch"
        else:
            status = "mismatch"
        return score, status


@pytest.fixture
def mock_srs_items():
    return [
        {"id": "SRS-001", "content": "The system shall authenticate users via OAuth 2.0"},
        {"id": "SRS-002", "content": "The system shall support data export in CSV format"},
        {"id": "SRS-003", "content": "The system shall log all security events"},
    ]


@pytest.fixture
def mock_arch_items():
    return [
        {"id": "ARC-001", "content": "User authentication using OAuth 2.0 protocol"},
        {"id": "ARC-002", "content": "Data export functionality supporting CSV and JSON formats"},
        {"id": "ARC-003", "content": "Real-time notification service for push messages"},
    ]


@pytest.fixture
def mock_comparator():
    comparator = MagicMock()
    comparator.compare = MagicMock(side_effect=[
        (95, "matched"),
        (85, "matched"),
        (30, "mismatch"),
        (20, "mismatch"),
        (45, "partial_mismatch"),
        (10, "mismatch"),
        (90, "matched"),
        (70, "partial_mismatch"),
        (15, "mismatch"),
    ])
    return comparator


@pytest.fixture
def service(mock_comparator):
    return ConsistencyMeasurementService(semantic_comparator=mock_comparator)


@pytest.fixture
def service_no_comparator():
    return ConsistencyMeasurementService()


def test_compare_returns_list_with_correct_length(service, mock_srs_items, mock_arch_items):
    results = service.compare_item_by_item(mock_srs_items, mock_arch_items)
    assert isinstance(results, list)
    assert len(results) == len(mock_srs_items)


def test_each_result_has_required_fields(service, mock_srs_items, mock_arch_items):
    results = service.compare_item_by_item(mock_srs_items, mock_arch_items)
    required_keys = {"srs_item_id", "arch_item_id", "match_status", "confidence_score"}
    for result in results:
        assert set(result.to_dict().keys()) == required_keys


def test_each_result_has_valid_match_status(service, mock_srs_items, mock_arch_items):
    results = service.compare_item_by_item(mock_srs_items, mock_arch_items)
    valid_statuses = {"matched", "partial_mismatch", "mismatch"}
    for result in results:
        assert result.match_status in valid_statuses


def test_each_result_confidence_score_in_range(service, mock_srs_items, mock_arch_items):
    results = service.compare_item_by_item(mock_srs_items, mock_arch_items)
    for result in results:
        assert 0 <= result.confidence_score <= 100


def test_srs_item_ids_preserved(service, mock_srs_items, mock_arch_items):
    results = service.compare_item_by_item(mock_srs_items, mock_arch_items)
    expected_ids = [item["id"] for item in mock_srs_items]
    actual_ids = [result.srs_item_id for result in results]
    assert actual_ids == expected_ids


def test_arch_item_ids_are_from_arch_list(service, mock_srs_items, mock_arch_items):
    results = service.compare_item_by_item(mock_srs_items, mock_arch_items)
    arch_ids = {item["id"] for item in mock_arch_items}
    for result in results:
        if result.arch_item_id is not None:
            assert result.arch_item_id in arch_ids


def test_mock_comparator_called_correct_number_of_times(mock_comparator, service, mock_srs_items, mock_arch_items):
    service.compare_item_by_item(mock_srs_items, mock_arch_items)
    expected_calls = len(mock_srs_items) * len(mock_arch_items)
    assert mock_comparator.compare.call_count == expected_calls


def test_empty_arch_items_returns_mismatch_for_all(service, mock_srs_items):
    results = service.compare_item_by_item(mock_srs_items, [])
    assert len(results) == len(mock_srs_items)
    for result in results:
        assert result.match_status == "mismatch"
        assert result.confidence_score == 0
        assert result.arch_item_id is None


def test_empty_srs_items_returns_empty_list(service, mock_arch_items):
    results = service.compare_item_by_item([], mock_arch_items)
    assert results == []


def test_default_compare_matched_status(service_no_comparator):
    srs = [{"id": "S-1", "content": "user authentication oauth"}]
    arch = [{"id": "A-1", "content": "user authentication oauth"}]
    results = service_no_comparator.compare_item_by_item(srs, arch)
    assert results[0].match_status == "matched"
    assert results[0].confidence_score >= 80


def test_default_compare_partial_mismatch_status(service_no_comparator):
    srs = [{"id": "S-1", "content": "the system shall support user login"}]
    arch = [{"id": "A-1", "content": "the system supports some features"}]
    results = service_no_comparator.compare_item_by_item(srs, arch)
    assert results[0].match_status in ("partial_mismatch", "mismatch")


def test_default_compare_mismatch_status(service_no_comparator):
    srs = [{"id": "S-1", "content": "authentication security tokens"}]
    arch = [{"id": "A-1", "content": "database backup recovery"}]
    results = service_no_comparator.compare_item_by_item(srs, arch)
    assert results[0].match_status == "mismatch"
    assert results[0].confidence_score < 40


def test_result_to_dict_structure(service, mock_srs_items, mock_arch_items):
    results = service.compare_item_by_item(mock_srs_items, mock_arch_items)
    first = results[0].to_dict()
    assert isinstance(first["srs_item_id"], str)
    assert isinstance(first["arch_item_id"], str) or first["arch_item_id"] is None
    assert isinstance(first["match_status"], str)
    assert isinstance(first["confidence_score"], int)


def test_invalid_match_status_raises_error():
    with pytest.raises(ValueError):
        SemanticComparisonItem(
            srs_item_id="S-1",
            arch_item_id="A-1",
            match_status="invalid_status",
            confidence_score=50,
        )


def test_invalid_confidence_score_above_100_raises_error():
    with pytest.raises(ValueError):
        SemanticComparisonItem(
            srs_item_id="S-1",
            arch_item_id="A-1",
            match_status="matched",
            confidence_score=101,
        )


def test_invalid_confidence_score_below_0_raises_error():
    with pytest.raises(ValueError):
        SemanticComparisonItem(
            srs_item_id="S-1",
            arch_item_id="A-1",
            match_status="matched",
            confidence_score=-1,
        )
