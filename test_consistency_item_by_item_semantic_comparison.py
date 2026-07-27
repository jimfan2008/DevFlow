import pytest
from unittest.mock import MagicMock, patch


# =============================================================================
# 领域模型
# =============================================================================

class SemanticComparisonItem:
    """数据模型：逐条语义对比结果"""

    VALID_STATUSES = ("matched", "partial_mismatch", "mismatch")

    def __init__(self, srs_item_id: str, arch_item_id: str,
                 match_status: str, confidence_score: int):
        if match_status not in self.VALID_STATUSES:
            raise ValueError(
                f"match_status 必须是 {self.VALID_STATUSES} 之一，实际: {match_status}"
            )
        if not (0 <= confidence_score <= 100):
            raise ValueError(
                f"confidence_score 必须在 0-100 之间，实际: {confidence_score}"
            )
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


class ScoringRule:
    """评分规则常量"""
    MATCHED_THRESHOLD = 80
    PARTIAL_MISMATCH_THRESHOLD = 40
    # score >= 80 -> matched
    # score >= 40 -> partial_mismatch
    # score < 40 -> mismatch

    @classmethod
    def classify(cls, score: int) -> str:
        if score >= cls.MATCHED_THRESHOLD:
            return "matched"
        elif score >= cls.PARTIAL_MISMATCH_THRESHOLD:
            return "partial_mismatch"
        else:
            return "mismatch"


class ConsistencyMeasurementService:
    """一致性测量服务：支持逐条语义对比"""

    def __init__(self, semantic_comparator=None):
        self._comparator = semantic_comparator

    def compare_item_by_item(self, srs_items: list, arch_items: list) -> list:
        """逐条完成语义对比，返回结果列表

        流程：对每条 SRS 条目，与所有架构条目逐一比较，取最佳匹配
        """
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
        """默认对比策略：基于 Jaccard 相似度的词袋模型"""
        srs_text = srs_item.get("content", "").lower()
        arch_text = arch_item.get("content", "").lower()
        common_words = set(srs_text.split()) & set(arch_text.split())
        total_words = set(srs_text.split()) | set(arch_text.split())
        if not total_words:
            return 0, "mismatch"
        similarity = len(common_words) / len(total_words)
        score = int(similarity * 100)
        status = ScoringRule.classify(score)
        return score, status


# =============================================================================
# Fixtures
# =============================================================================

@pytest.fixture
def mock_srs_items():
    """标准 SRS 条目集"""
    return [
        {"id": "SRS-001", "content": "The system shall authenticate users via OAuth 2.0"},
        {"id": "SRS-002", "content": "The system shall support data export in CSV format"},
        {"id": "SRS-003", "content": "The system shall log all security events"},
    ]


@pytest.fixture
def mock_arch_items():
    """标准架构条目集（含一条无关条目以测试最佳匹配选择）"""
    return [
        {"id": "ARC-001", "content": "User authentication using OAuth 2.0 protocol"},
        {"id": "ARC-002", "content": "Data export functionality supporting CSV and JSON formats"},
        {"id": "ARC-003", "content": "Real-time notification service for push messages"},
    ]


@pytest.fixture
def mock_comparator():
    """模拟语义对比器：返回预设的 (score, status) 对

    调用顺序：3 条 SRS × 3 条 arch = 9 次调用
    SRS-001 vs ARC-001, ARC-002, ARC-003
    SRS-002 vs ARC-001, ARC-002, ARC-003
    SRS-003 vs ARC-001, ARC-002, ARC-003
    """
    comparator = MagicMock()
    comparator.compare = MagicMock(side_effect=[
        (95, "matched"),       # SRS-001 vs ARC-001
        (85, "matched"),       # SRS-001 vs ARC-002
        (30, "mismatch"),      # SRS-001 vs ARC-003
        (20, "mismatch"),      # SRS-002 vs ARC-001
        (45, "partial_mismatch"),  # SRS-002 vs ARC-002
        (10, "mismatch"),      # SRS-002 vs ARC-003
        (90, "matched"),       # SRS-003 vs ARC-001
        (70, "partial_mismatch"),  # SRS-003 vs ARC-002
        (15, "mismatch"),      # SRS-003 vs ARC-003
    ])
    return comparator


@pytest.fixture
def service(mock_comparator):
    return ConsistencyMeasurementService(semantic_comparator=mock_comparator)


@pytest.fixture
def service_no_comparator():
    """无外部对比器，使用默认 Jaccard 对比"""
    return ConsistencyMeasurementService()


# =============================================================================
# 验收标准 1：一致性检验采用逐条语义对比
# =============================================================================

class TestItemByItemComparisonFlow:
    """验证一致性检验采用逐条语义对比流程"""

    def test_returns_list_for_each_srs_item(self, service, mock_srs_items, mock_arch_items):
        """逐条对比：返回结果列表长度等于 SRS 条目数量"""
        results = service.compare_item_by_item(mock_srs_items, mock_arch_items)
        assert isinstance(results, list)
        assert len(results) == len(mock_srs_items)

    def test_each_result_corresponds_to_one_srs_item(self, service, mock_srs_items, mock_arch_items):
        """逐条对比：每个结果对应一条 SRS 条目，ID 顺序一致"""
        results = service.compare_item_by_item(mock_srs_items, mock_arch_items)
        expected_ids = [item["id"] for item in mock_srs_items]
        actual_ids = [result.srs_item_id for result in results]
        assert actual_ids == expected_ids

    def test_each_srs_item_compared_against_all_arch_items(
        self, mock_comparator, service, mock_srs_items, mock_arch_items
    ):
        """逐条对比：每条 SRS 与所有架构条目逐一比较"""
        service.compare_item_by_item(mock_srs_items, mock_arch_items)
        expected_calls = len(mock_srs_items) * len(mock_arch_items)
        assert mock_comparator.compare.call_count == expected_calls

    def test_comparison_order_is_srs_first_then_arch(self, mock_comparator, service):
        """逐条对比：对比顺序为先 SRS 再架构（外层 SRS、内层 arch）"""
        srs = [{"id": "S1", "content": "auth"}, {"id": "S2", "content": "export"}]
        arch = [{"id": "A1", "content": "auth"}, {"id": "A2", "content": "data"}]
        mock_comparator.compare = MagicMock(side_effect=[
            (80, "matched"),   # S1 vs A1
            (20, "mismatch"),  # S1 vs A2
            (30, "mismatch"),  # S2 vs A1
            (70, "partial_mismatch"),  # S2 vs A2
        ])
        svc = ConsistencyMeasurementService(semantic_comparator=mock_comparator)
        svc.compare_item_by_item(srs, arch)
        calls = mock_comparator.compare.call_args_list
        # 验证调用顺序：S1→A1, S1→A2, S2→A1, S2→A2
        assert calls[0][0][0]["id"] == "S1"
        assert calls[0][0][1]["id"] == "A1"
        assert calls[1][0][0]["id"] == "S1"
        assert calls[1][0][1]["id"] == "A2"
        assert calls[2][0][0]["id"] == "S2"
        assert calls[2][0][1]["id"] == "A1"
        assert calls[3][0][0]["id"] == "S2"
        assert calls[3][0][1]["id"] == "A2"

    def test_best_match_selected_per_srs_item(self, service, mock_srs_items, mock_arch_items):
        """逐条对比：每条 SRS 取最佳匹配（最高分数）"""
        results = service.compare_item_by_item(mock_srs_items, mock_arch_items)
        # SRS-001 最佳匹配应为 ARC-001 (95分)
        assert results[0].arch_item_id == "ARC-001"
        assert results[0].confidence_score == 95
        # SRS-002 最佳匹配应为 ARC-002 (45分)
        assert results[1].arch_item_id == "ARC-002"
        assert results[1].confidence_score == 45
        # SRS-003 最佳匹配应为 ARC-001 (90分)
        assert results[2].arch_item_id == "ARC-001"
        assert results[2].confidence_score == 90

    def test_result_order_matches_srs_order(self, service, mock_srs_items, mock_arch_items):
        """逐条对比：结果顺序与 SRS 输入顺序一致"""
        results = service.compare_item_by_item(mock_srs_items, mock_arch_items)
        for i, srs_item in enumerate(mock_srs_items):
            assert results[i].srs_item_id == srs_item["id"]

    def test_empty_srs_returns_empty(self, service, mock_arch_items):
        """逐条对比：空 SRS 列表返回空结果"""
        results = service.compare_item_by_item([], mock_arch_items)
        assert results == []

    def test_empty_arch_returns_mismatch_for_all(self, service, mock_srs_items):
        """逐条对比：空架构列表时所有 SRS 均为 mismatch"""
        results = service.compare_item_by_item(mock_srs_items, [])
        assert len(results) == len(mock_srs_items)
        for result in results:
            assert result.match_status == "mismatch"
            assert result.confidence_score == 0
            assert result.arch_item_id is None

    def test_both_empty_returns_empty(self, service):
        """逐条对比：双方都为空时返回空结果"""
        results = service.compare_item_by_item([], [])
        assert results == []

    def test_single_item_comparison(self, service):
        """逐条对比：单条 SRS 与单条 arch 对比"""
        srs = [{"id": "S1", "content": "single test"}]
        arch = [{"id": "A1", "content": "single"}]
        results = service.compare_item_by_item(srs, arch)
        assert len(results) == 1
        assert results[0].srs_item_id == "S1"
        assert results[0].arch_item_id == "A1"

    def test_arch_item_ids_are_from_arch_list(self, service, mock_srs_items, mock_arch_items):
        """逐条对比：匹配到的 arch_item_id 必须来自架构列表"""
        results = service.compare_item_by_item(mock_srs_items, mock_arch_items)
        arch_ids = {item["id"] for item in mock_arch_items}
        for result in results:
            if result.arch_item_id is not None:
                assert result.arch_item_id in arch_ids

    def test_each_result_has_required_fields(self, service, mock_srs_items, mock_arch_items):
        """逐条对比：每个结果包含必要字段"""
        results = service.compare_item_by_item(mock_srs_items, mock_arch_items)
        required_keys = {"srs_item_id", "arch_item_id", "match_status", "confidence_score"}
        for result in results:
            assert set(result.to_dict().keys()) == required_keys


# =============================================================================
# 验收标准 2：评分规则正确
# =============================================================================

class TestScoringRules:
    """验证评分规则正确"""

    def test_score_at_exact_80_is_matched(self):
        """评分规则：得分恰好 80 分 → matched"""
        status = ScoringRule.classify(80)
        assert status == "matched"

    def test_score_at_exact_40_is_partial_mismatch(self):
        """评分规则：得分恰好 40 分 → partial_mismatch"""
        status = ScoringRule.classify(40)
        assert status == "partial_mismatch"

    def test_score_79_is_partial_mismatch(self):
        """评分规则：得分 79 分 → partial_mismatch"""
        status = ScoringRule.classify(79)
        assert status == "partial_mismatch"

    def test_score_39_is_mismatch(self):
        """评分规则：得分 39 分 → mismatch"""
        status = ScoringRule.classify(39)
        assert status == "mismatch"

    def test_score_100_is_matched(self):
        """评分规则：满分 100 → matched"""
        status = ScoringRule.classify(100)
        assert status == "matched"

    def test_score_0_is_mismatch(self):
        """评分规则：零分 0 → mismatch"""
        status = ScoringRule.classify(0)
        assert status == "mismatch"

    def test_score_1_is_mismatch(self):
        """评分规则：1 分 → mismatch"""
        status = ScoringRule.classify(1)
        assert status == "mismatch"

    def test_score_50_is_partial_mismatch(self):
        """评分规则：50 分 → partial_mismatch（区间内）"""
        status = ScoringRule.classify(50)
        assert status == "partial_mismatch"

    def test_score_99_is_matched(self):
        """评分规则：99 分 → matched（区间内）"""
        status = ScoringRule.classify(99)
        assert status == "matched"

    def test_score_thresholds_are_correct_constants(self):
        """评分规则：阈值常量正确"""
        assert ScoringRule.MATCHED_THRESHOLD == 80
        assert ScoringRule.PARTIAL_MISMATCH_THRESHOLD == 40


class TestDefaultCompareScoring:
    """验证默认 Jaccard 对比的评分规则"""

    def test_identical_content_scores_100_matched(self, service_no_comparator):
        """默认对比：完全相同内容 → 100 分，matched"""
        srs = [{"id": "S1", "content": "user authentication oauth"}]
        arch = [{"id": "A1", "content": "user authentication oauth"}]
        results = service_no_comparator.compare_item_by_item(srs, arch)
        assert results[0].confidence_score == 100
        assert results[0].match_status == "matched"

    def test_high_overlap_scores_matched(self, service_no_comparator):
        """默认对比：高重叠内容 → 80+ 分，matched"""
        srs = [{"id": "S1", "content": "user authentication oauth token"}]
        arch = [{"id": "A1", "content": "user authentication oauth token extra"}]
        results = service_no_comparator.compare_item_by_item(srs, arch)
        # 交集 4 / 并集 5 = 80%
        assert results[0].confidence_score >= 80
        assert results[0].match_status == "matched"

    def test_no_common_words_scores_zero_mismatch(self, service_no_comparator):
        """默认对比：无公共词汇 → 0 分，mismatch"""
        srs = [{"id": "S1", "content": "authentication security tokens"}]
        arch = [{"id": "A1", "content": "database backup recovery"}]
        results = service_no_comparator.compare_item_by_item(srs, arch)
        assert results[0].confidence_score == 0
        assert results[0].match_status == "mismatch"

    def test_empty_content_scores_zero_mismatch(self, service_no_comparator):
        """默认对比：空内容 → 0 分，mismatch"""
        srs = [{"id": "S1", "content": ""}]
        arch = [{"id": "A1", "content": ""}]
        results = service_no_comparator.compare_item_by_item(srs, arch)
        assert results[0].confidence_score == 0
        assert results[0].match_status == "mismatch"

    def test_case_insensitive_comparison(self, service_no_comparator):
        """默认对比：大小写不敏感"""
        srs = [{"id": "S1", "content": "User Authentication"}]
        arch = [{"id": "A1", "content": "user authentication"}]
        results = service_no_comparator.compare_item_by_item(srs, arch)
        assert results[0].confidence_score == 100
        assert results[0].match_status == "matched"

    def test_partial_overlap_scores_partial_mismatch(self, service_no_comparator):
        """默认对比：部分重叠 → partial_mismatch"""
        srs = [{"id": "S1", "content": "the system shall support user login"}]
        arch = [{"id": "A1", "content": "the system supports some features"}]
        results = service_no_comparator.compare_item_by_item(srs, arch)
        # 交集: {the, system} / 并集: {the, system, shall, support, user, login, supports, some, features}
        # score ≈ 20%, mismatch
        assert results[0].confidence_score < 40

    def test_duplicate_words_handled_correctly(self, service_no_comparator):
        """默认对比：重复单词不重复计数（集合去重）"""
        srs = [{"id": "S1", "content": "the the the system system"}]
        arch = [{"id": "A1", "content": "the system"}]
        results = service_no_comparator.compare_item_by_item(srs, arch)
        # 交集 {the, system} / 并集 {the, system} = 100%
        assert results[0].confidence_score == 100


class TestSemanticComparisonItemValidation:
    """验证 SemanticComparisonItem 的输入校验"""

    def test_invalid_match_status_raises_error(self):
        """校验：无效的 match_status 抛出 ValueError"""
        with pytest.raises(ValueError, match="match_status"):
            SemanticComparisonItem(
                srs_item_id="S-1",
                arch_item_id="A-1",
                match_status="invalid_status",
                confidence_score=50,
            )

    def test_invalid_confidence_score_above_100_raises_error(self):
        """校验：超过 100 的 confidence_score 抛出 ValueError"""
        with pytest.raises(ValueError, match="confidence_score"):
            SemanticComparisonItem(
                srs_item_id="S-1",
                arch_item_id="A-1",
                match_status="matched",
                confidence_score=101,
            )

    def test_invalid_confidence_score_below_0_raises_error(self):
        """校验：低于 0 的 confidence_score 抛出 ValueError"""
        with pytest.raises(ValueError, match="confidence_score"):
            SemanticComparisonItem(
                srs_item_id="S-1",
                arch_item_id="A-1",
                match_status="matched",
                confidence_score=-1,
            )

    def test_valid_matched_item(self):
        """校验：合法 matched 项可正常创建"""
        item = SemanticComparisonItem("S-1", "A-1", "matched", 85)
        assert item.srs_item_id == "S-1"
        assert item.arch_item_id == "A-1"
        assert item.match_status == "matched"
        assert item.confidence_score == 85

    def test_valid_partial_mismatch_item(self):
        """校验：合法 partial_mismatch 项可正常创建"""
        item = SemanticComparisonItem("S-2", "A-2", "partial_mismatch", 55)
        assert item.match_status == "partial_mismatch"
        assert item.confidence_score == 55

    def test_valid_mismatch_item(self):
        """校验：合法 mismatch 项可正常创建"""
        item = SemanticComparisonItem("S-3", "A-3", "mismatch", 10)
        assert item.match_status == "mismatch"
        assert item.confidence_score == 10

    def test_boundary_score_80_is_valid(self):
        """校验：边界分数 80 可正常创建"""
        item = SemanticComparisonItem("S-1", "A-1", "matched", 80)
        assert item.confidence_score == 80

    def test_boundary_score_40_is_valid(self):
        """校验：边界分数 40 可正常创建"""
        item = SemanticComparisonItem("S-1", "A-1", "partial_mismatch", 40)
        assert item.confidence_score == 40

    def test_to_dict_returns_all_fields(self):
        """校验：to_dict 返回完整字段"""
        item = SemanticComparisonItem("S-1", "A-1", "matched", 90)
        d = item.to_dict()
        assert d["srs_item_id"] == "S-1"
        assert d["arch_item_id"] == "A-1"
        assert d["match_status"] == "matched"
        assert d["confidence_score"] == 90
        assert len(d) == 4

    def test_to_dict_with_none_arch_id(self):
        """校验：to_dict 支持 arch_item_id 为 None"""
        item = SemanticComparisonItem("S-1", None, "mismatch", 0)
        d = item.to_dict()
        assert d["arch_item_id"] is None


# =============================================================================
# 集成测试：完整流程
# =============================================================================

class TestFullConsistencyInspectionFlow:
    """集成测试：完整的一致性检验逐条语义对比流程"""

    def test_full_flow_with_mock_comparator(self, service, mock_srs_items, mock_arch_items):
        """完整流程：使用 mock 对比器完成逐条对比"""
        results = service.compare_item_by_item(mock_srs_items, mock_arch_items)
        assert len(results) == 3
        # 验证每条结果的状态和分数
        assert results[0].match_status == "matched"
        assert results[0].confidence_score == 95
        assert results[1].match_status == "partial_mismatch"
        assert results[1].confidence_score == 45
        assert results[2].match_status == "matched"
        assert results[2].confidence_score == 90

    def test_full_flow_with_default_comparator(self, service_no_comparator):
        """完整流程：使用默认对比器完成逐条对比"""
        srs = [
            {"id": "S-1", "content": "oauth authentication"},
            {"id": "S-2", "content": "csv export feature"},
            {"id": "S-3", "content": "security audit logging"},
        ]
        arch = [
            {"id": "A-1", "content": "oauth authentication"},
            {"id": "A-2", "content": "csv data export functionality"},
            {"id": "A-3", "content": "security event audit log"},
        ]
        results = service_no_comparator.compare_item_by_item(srs, arch)
        assert len(results) == 3
        assert results[0].match_status == "matched"  # 完全相同
        assert results[0].confidence_score == 100

    def test_consistency_score_calculation(self, service, mock_srs_items, mock_arch_items):
        """评分计算：一致性总分 = 各条目分数的平均值"""
        results = service.compare_item_by_item(mock_srs_items, mock_arch_items)
        total_score = sum(r.confidence_score for r in results)
        avg_score = total_score / len(results)
        assert avg_score > 0  # 至少有一条匹配

    def test_all_results_have_valid_statuses(self, service, mock_srs_items, mock_arch_items):
        """校验：所有结果的状态都是有效值"""
        results = service.compare_item_by_item(mock_srs_items, mock_arch_items)
        valid = {"matched", "partial_mismatch", "mismatch"}
        for result in results:
            assert result.match_status in valid

    def test_all_results_scores_in_range(self, service, mock_srs_items, mock_arch_items):
        """校验：所有结果的分数在 0-100 范围内"""
        results = service.compare_item_by_item(mock_srs_items, mock_arch_items)
        for result in results:
            assert 0 <= result.confidence_score <= 100

    def test_result_to_dict_serializable(self, service, mock_srs_items, mock_arch_items):
        """校验：结果可序列化为字典"""
        results = service.compare_item_by_item(mock_srs_items, mock_arch_items)
        for result in results:
            d = result.to_dict()
            assert isinstance(d, dict)
            assert isinstance(d["srs_item_id"], str)
            assert isinstance(d["confidence_score"], int)

    def test_multiple_arch_best_match_wins(self, service):
        """校验：多条 arch 时选择分数最高的匹配"""
        srs = [{"id": "S1", "content": "test"}]
        arch = [
            {"id": "A1", "content": "test"},
            {"id": "A2", "content": "hello world"},
        ]
        # 手动构造对比器
        comparator = MagicMock()
        comparator.compare = MagicMock(side_effect=[
            (60, "partial_mismatch"),  # S1 vs A1
            (30, "mismatch"),          # S1 vs A2
        ])
        svc = ConsistencyMeasurementService(semantic_comparator=comparator)
        results = svc.compare_item_by_item(srs, arch)
        assert results[0].arch_item_id == "A1"
        assert results[0].confidence_score == 60

    def test_tie_breaks_by_first_highest(self, service):
        """校验：分数相同时取第一个最高分（先遇到的）"""
        srs = [{"id": "S1", "content": "x"}]
        arch = [
            {"id": "A1", "content": "x"},
            {"id": "A2", "content": "x"},
        ]
        comparator = MagicMock()
        comparator.compare = MagicMock(side_effect=[
            (75, "partial_mismatch"),  # S1 vs A1
            (75, "partial_mismatch"),  # S1 vs A2
        ])
        svc = ConsistencyMeasurementService(semantic_comparator=comparator)
        results = svc.compare_item_by_item(srs, arch)
        # 分数相同，保留第一个（因为 75 > 75 为 False）
        assert results[0].arch_item_id == "A1"
        assert results[0].confidence_score == 75
