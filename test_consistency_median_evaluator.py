import pytest
from typing import Dict, List, Any, Optional


# === 被测试的类/函数 ===

class EvaluatorScore:
    """评估员评分记录"""

    def __init__(
        self,
        evaluator_id: str,
        evaluator_name: str,
        score: float,
        comments: Optional[str] = None,
    ):
        if score < 0 or score > 100:
            raise ValueError(f"评分必须在0-100之间，实际: {score}")
        self.evaluator_id = evaluator_id
        self.evaluator_name = evaluator_name
        self.score = score
        self.comments = comments or ""

    def to_dict(self) -> Dict[str, Any]:
        return {
            "evaluator_id": self.evaluator_id,
            "evaluator_name": self.evaluator_name,
            "score": self.score,
            "comments": self.comments,
        }


class ConsistencyMediator:
    """
    一致性测量方法：3名评估员取中位数评分规则
    人工评估时，采用3名评估员独立打分，取中位数作为最终评分
    """

    def __init__(self):
        self._evaluator_scores: List[EvaluatorScore] = []

    def add_evaluator_score(
        self,
        evaluator_id: str,
        evaluator_name: str,
        score: float,
        comments: Optional[str] = None,
    ) -> EvaluatorScore:
        """添加一名评估员的评分"""
        evaluator = EvaluatorScore(
            evaluator_id=evaluator_id,
            evaluator_name=evaluator_name,
            score=score,
            comments=comments,
        )
        self._evaluator_scores.append(evaluator)
        return evaluator

    @property
    def evaluator_count(self) -> int:
        """当前评分的评估员数量"""
        return len(self._evaluator_scores)

    def get_median_score(self) -> Optional[float]:
        """
        取所有评估员评分的中位数。
        评估员数量为奇数时取中间值；
        评估员数量为偶数时取中间两个的平均值。
        """
        if not self._evaluator_scores:
            return None
        scores = sorted(e.score for e in self._evaluator_scores)
        n = len(scores)
        mid = n // 2
        if n % 2 == 1:
            return scores[mid]
        else:
            return round((scores[mid - 1] + scores[mid]) / 2, 2)

    def get_result_record(self) -> Dict[str, Any]:
        """
        生成包含所有评估员评分和中位数结果的综合记录。
        要求至少3名评估员。
        """
        if self.evaluator_count < 3:
            raise ValueError(
                f"至少需要3名评估员，当前仅有{self.evaluator_count}名"
            )
        record: Dict[str, Any] = {}
        for i, evaluator in enumerate(self._evaluator_scores, start=1):
            record[f"evaluator_{i}_id"] = evaluator.evaluator_id
            record[f"evaluator_{i}_name"] = evaluator.evaluator_name
            record[f"evaluator_{i}_score"] = evaluator.score
            if evaluator.comments:
                record[f"evaluator_{i}_comments"] = evaluator.comments
        record["evaluator_count"] = self.evaluator_count
        record["median_score"] = self.get_median_score()
        record["individual_scores"] = sorted(
            [e.score for e in self._evaluator_scores]
        )
        return record

    def reset(self):
        """重置所有评分记录"""
        self._evaluator_scores = []


def calc_consistency_median(scores: List[float]) -> float:
    """
    便捷函数：直接传入评分列表，返回中位数。
    要求列表长度至少为3。
    """
    if len(scores) < 3:
        raise ValueError(f"至少需要3个评分，当前仅有{len(scores)}个")
    sorted_scores = sorted(scores)
    n = len(sorted_scores)
    mid = n // 2
    if n % 2 == 1:
        return sorted_scores[mid]
    else:
        return round((sorted_scores[mid - 1] + sorted_scores[mid]) / 2, 2)


# === 测试用例 ===

class TestEvaluatorScoreValidation:
    """验证评估员评分记录的基本规则"""

    def test_evaluator_score_valid_range(self):
        score = EvaluatorScore(
            evaluator_id="EV-001",
            evaluator_name="评估员A",
            score=85,
        )
        assert score.score == 85
        assert score.evaluator_id == "EV-001"
        assert score.evaluator_name == "评估员A"

    def test_evaluator_score_boundary_zero(self):
        score = EvaluatorScore(
            evaluator_id="EV-002",
            evaluator_name="评估员B",
            score=0,
        )
        assert score.score == 0

    def test_evaluator_score_boundary_hundred(self):
        score = EvaluatorScore(
            evaluator_id="EV-003",
            evaluator_name="评估员C",
            score=100,
        )
        assert score.score == 100

    def test_evaluator_score_negative_raises(self):
        with pytest.raises(ValueError, match="评分必须在0-100之间"):
            EvaluatorScore(
                evaluator_id="EV-BAD",
                evaluator_name="不合格",
                score=-5,
            )

    def test_evaluator_score_over_hundred_raises(self):
        with pytest.raises(ValueError, match="评分必须在0-100之间"):
            EvaluatorScore(
                evaluator_id="EV-BAD",
                evaluator_name="不合格",
                score=101,
            )

    def test_evaluator_score_with_comments(self):
        score = EvaluatorScore(
            evaluator_id="EV-004",
            evaluator_name="评估员D",
            score=92,
            comments="功能完整，细节有待改善",
        )
        assert score.comments == "功能完整，细节有待改善"

    def test_evaluator_score_default_comments_empty(self):
        score = EvaluatorScore(
            evaluator_id="EV-005",
            evaluator_name="评估员E",
            score=78,
        )
        assert score.comments == ""

    def test_evaluator_score_to_dict(self):
        score = EvaluatorScore(
            evaluator_id="EV-006",
            evaluator_name="评估员F",
            score=88,
            comments="评分备注",
        )
        d = score.to_dict()
        assert d["evaluator_id"] == "EV-006"
        assert d["evaluator_name"] == "评估员F"
        assert d["score"] == 88
        assert d["comments"] == "评分备注"


class TestConsistencyMediatorMedian:
    """验证3名评估员取中位数的核心规则"""

    def test_median_of_three_scores_75_85_90(self):
        """
        验收标准核心验证：
        evaluator_1_score=75, evaluator_2_score=85, evaluator_3_score=90
        中位数 = 85
        """
        mediator = ConsistencyMediator()
        mediator.add_evaluator_score("EV-001", "评估员A", 75)
        mediator.add_evaluator_score("EV-002", "评估员B", 85)
        mediator.add_evaluator_score("EV-003", "评估员C", 90)

        median = mediator.get_median_score()
        assert median == 85, f"中位数应为85，实际{median}"

    def test_result_record_contains_all_fields(self):
        """
        验收标准验证：
        记录包含 evaluator_1_score=75、evaluator_2_score=85、
        evaluator_3_score=90、median_score=85
        """
        mediator = ConsistencyMediator()
        mediator.add_evaluator_score("EV-001", "评估员A", 75)
        mediator.add_evaluator_score("EV-002", "评估员B", 85)
        mediator.add_evaluator_score("EV-003", "评估员C", 90)

        record = mediator.get_result_record()
        assert record["evaluator_1_score"] == 75
        assert record["evaluator_2_score"] == 85
        assert record["evaluator_3_score"] == 90
        assert record["median_score"] == 85

    def test_median_with_unordered_scores(self):
        """评估员打分顺序不同，中位数不受影响"""
        mediator = ConsistencyMediator()
        mediator.add_evaluator_score("EV-001", "评估员A", 90)
        mediator.add_evaluator_score("EV-002", "评估员B", 75)
        mediator.add_evaluator_score("EV-003", "评估员C", 85)

        median = mediator.get_median_score()
        assert median == 85, f"中位数应为85，实际{median}"

    def test_median_with_two_same_scores(self):
        mediator = ConsistencyMediator()
        mediator.add_evaluator_score("EV-001", "评估员A", 80)
        mediator.add_evaluator_score("EV-002", "评估员B", 85)
        mediator.add_evaluator_score("EV-003", "评估员C", 80)

        median = mediator.get_median_score()
        assert median == 80, f"中位数应为80，实际{median}"

    def test_median_with_all_same_scores(self):
        mediator = ConsistencyMediator()
        mediator.add_evaluator_score("EV-001", "评估员A", 90)
        mediator.add_evaluator_score("EV-002", "评估员B", 90)
        mediator.add_evaluator_score("EV-003", "评估员C", 90)

        median = mediator.get_median_score()
        assert median == 90

    def test_median_requires_at_least_three_evaluators(self):
        mediator = ConsistencyMediator()
        mediator.add_evaluator_score("EV-001", "评估员A", 80)
        mediator.add_evaluator_score("EV-002", "评估员B", 85)

        with pytest.raises(ValueError, match="至少需要3名评估员"):
            mediator.get_result_record()

    def test_median_with_five_evaluators(self):
        mediator = ConsistencyMediator()
        mediator.add_evaluator_score("EV-001", "评估员A", 60)
        mediator.add_evaluator_score("EV-002", "评估员B", 70)
        mediator.add_evaluator_score("EV-003", "评估员C", 85)
        mediator.add_evaluator_score("EV-004", "评估员D", 90)
        mediator.add_evaluator_score("EV-005", "评估员E", 95)

        median = mediator.get_median_score()
        assert median == 85, f"中位数应为85，实际{median}"

    def test_median_with_four_evaluators_even_count(self):
        mediator = ConsistencyMediator()
        mediator.add_evaluator_score("EV-001", "评估员A", 70)
        mediator.add_evaluator_score("EV-002", "评估员B", 80)
        mediator.add_evaluator_score("EV-003", "评估员C", 85)
        mediator.add_evaluator_score("EV-004", "评估员D", 95)

        median = mediator.get_median_score()
        assert median == 82.5, f"中位数应为82.5，实际{median}"

    def test_no_evaluators_returns_none(self):
        mediator = ConsistencyMediator()
        assert mediator.get_median_score() is None

    def test_evaluator_count_property(self):
        mediator = ConsistencyMediator()
        assert mediator.evaluator_count == 0
        mediator.add_evaluator_score("EV-001", "评估员A", 80)
        assert mediator.evaluator_count == 1
        mediator.add_evaluator_score("EV-002", "评估员B", 85)
        assert mediator.evaluator_count == 2
        mediator.add_evaluator_score("EV-003", "评估员C", 90)
        assert mediator.evaluator_count == 3


class TestResultRecordStructure:
    """验证结果记录的结构和完整性"""

    def test_record_contains_evaluator_ids(self):
        mediator = ConsistencyMediator()
        mediator.add_evaluator_score("EV-001", "评估员A", 75)
        mediator.add_evaluator_score("EV-002", "评估员B", 85)
        mediator.add_evaluator_score("EV-003", "评估员C", 90)

        record = mediator.get_result_record()
        assert record["evaluator_1_id"] == "EV-001"
        assert record["evaluator_2_id"] == "EV-002"
        assert record["evaluator_3_id"] == "EV-003"

    def test_record_contains_evaluator_names(self):
        mediator = ConsistencyMediator()
        mediator.add_evaluator_score("EV-001", "张伟", 75)
        mediator.add_evaluator_score("EV-002", "李强", 85)
        mediator.add_evaluator_score("EV-003", "王芳", 90)

        record = mediator.get_result_record()
        assert record["evaluator_1_name"] == "张伟"
        assert record["evaluator_2_name"] == "李强"
        assert record["evaluator_3_name"] == "王芳"

    def test_record_contains_sorted_individual_scores(self):
        mediator = ConsistencyMediator()
        mediator.add_evaluator_score("EV-001", "评估员A", 90)
        mediator.add_evaluator_score("EV-002", "评估员B", 75)
        mediator.add_evaluator_score("EV-003", "评估员C", 85)

        record = mediator.get_result_record()
        assert record["individual_scores"] == [75, 85, 90]

    def test_record_contains_evaluator_count(self):
        mediator = ConsistencyMediator()
        mediator.add_evaluator_score("EV-001", "评估员A", 75)
        mediator.add_evaluator_score("EV-002", "评估员B", 85)
        mediator.add_evaluator_score("EV-003", "评估员C", 90)

        record = mediator.get_result_record()
        assert record["evaluator_count"] == 3

    def test_record_includes_comments_when_present(self):
        mediator = ConsistencyMediator()
        mediator.add_evaluator_score("EV-001", "评估员A", 75, "功能有缺陷")
        mediator.add_evaluator_score("EV-002", "评估员B", 85)
        mediator.add_evaluator_score("EV-003", "评估员C", 90, "表现优秀")

        record = mediator.get_result_record()
        assert record["evaluator_1_comments"] == "功能有缺陷"
        assert "evaluator_2_comments" not in record
        assert record["evaluator_3_comments"] == "表现优秀"


class TestConsistencyMediatorReset:
    """验证重置功能"""

    def test_reset_clears_all_scores(self):
        mediator = ConsistencyMediator()
        mediator.add_evaluator_score("EV-001", "评估员A", 75)
        mediator.add_evaluator_score("EV-002", "评估员B", 85)
        mediator.add_evaluator_score("EV-003", "评估员C", 90)

        assert mediator.evaluator_count == 3
        mediator.reset()
        assert mediator.evaluator_count == 0
        assert mediator.get_median_score() is None

    def test_reset_allows_new_round_of_scoring(self):
        mediator = ConsistencyMediator()
        mediator.add_evaluator_score("EV-001", "评估员A", 75)
        mediator.add_evaluator_score("EV-002", "评估员B", 85)
        mediator.add_evaluator_score("EV-003", "评估员C", 90)
        assert mediator.get_median_score() == 85

        mediator.reset()
        mediator.add_evaluator_score("EV-001", "评估员A", 90)
        mediator.add_evaluator_score("EV-002", "评估员B", 95)
        mediator.add_evaluator_score("EV-003", "评估员C", 88)
        assert mediator.get_median_score() == 90


class TestCalcConsistencyMedianUtility:
    """验证便捷函数 calc_consistency_median"""

    def test_median_of_three_basic(self):
        result = calc_consistency_median([75, 85, 90])
        assert result == 85

    def test_median_of_three_unordered(self):
        result = calc_consistency_median([90, 75, 85])
        assert result == 85

    def test_median_of_five(self):
        result = calc_consistency_median([60, 95, 70, 85, 90])
        assert result == 85

    def test_median_of_even_count(self):
        result = calc_consistency_median([70, 80, 85, 95])
        assert result == 82.5

    def test_median_less_than_three_raises(self):
        with pytest.raises(ValueError, match="至少需要3个评分"):
            calc_consistency_median([80, 90])

    def test_median_single_element_raises(self):
        with pytest.raises(ValueError, match="至少需要3个评分"):
            calc_consistency_median([85])

    def test_median_empty_raises(self):
        with pytest.raises(ValueError, match="至少需要3个评分"):
            calc_consistency_median([])


class TestConsistencyMediatorIntegration:
    """端到端场景：3名评估员完成评分并生成记录"""

    def test_full_workflow_3_evaluators(self):
        """
        完整流程：
        1. 3名评估员分别打分 75、85、90
        2. 取中位数 = 85 作为最终评分
        3. 生成包含所有信息的记录
        """
        mediator = ConsistencyMediator()

        mediator.add_evaluator_score("EV-001", "张伟", 75, "存在3个中等缺陷")
        mediator.add_evaluator_score("EV-002", "李强", 85, "整体良好")
        mediator.add_evaluator_score("EV-003", "王芳", 90, "质量优秀")

        record = mediator.get_result_record()

        assert record["evaluator_1_score"] == 75
        assert record["evaluator_2_score"] == 85
        assert record["evaluator_3_score"] == 90
        assert record["median_score"] == 85
        assert record["evaluator_count"] == 3
        assert record["individual_scores"] == [75, 85, 90]
        assert record["evaluator_1_id"] == "EV-001"
        assert record["evaluator_2_id"] == "EV-002"
        assert record["evaluator_3_id"] == "EV-003"

    def test_full_workflow_boundary_scores(self):
        """极端场景：3名评估员分别打 0、50、100 分"""
        mediator = ConsistencyMediator()
        mediator.add_evaluator_score("EV-001", "严格评估员", 0)
        mediator.add_evaluator_score("EV-002", "中立评估员", 50)
        mediator.add_evaluator_score("EV-003", "宽松评估员", 100)

        record = mediator.get_result_record()
        assert record["median_score"] == 50
        assert record["individual_scores"] == [0, 50, 100]

    def test_full_workflow_extreme_spread(self):
        """极端场景：3名评估员评分差异较大，中位数合理"""
        mediator = ConsistencyMediator()
        mediator.add_evaluator_score("EV-001", "评估员A", 30)
        mediator.add_evaluator_score("EV-002", "评估员B", 65)
        mediator.add_evaluator_score("EV-003", "评估员C", 95)

        record = mediator.get_result_record()
        assert record["median_score"] == 65

    def test_full_workflow_all_perfect(self):
        """所有评估员都打满分"""
        mediator = ConsistencyMediator()
        mediator.add_evaluator_score("EV-001", "评估员A", 100)
        mediator.add_evaluator_score("EV-002", "评估员B", 100)
        mediator.add_evaluator_score("EV-003", "评估员C", 100)

        record = mediator.get_result_record()
        assert record["median_score"] == 100

    def test_full_workflow_all_failing(self):
        """所有评估员都打0分"""
        mediator = ConsistencyMediator()
        mediator.add_evaluator_score("EV-001", "评估员A", 0)
        mediator.add_evaluator_score("EV-002", "评估员B", 0)
        mediator.add_evaluator_score("EV-003", "评估员C", 0)

        record = mediator.get_result_record()
        assert record["median_score"] == 0

    def test_full_workflow_float_scores(self):
        """支持小数评分"""
        mediator = ConsistencyMediator()
        mediator.add_evaluator_score("EV-001", "评估员A", 75.5)
        mediator.add_evaluator_score("EV-002", "评估员B", 85.3)
        mediator.add_evaluator_score("EV-003", "评估员C", 90.7)

        record = mediator.get_result_record()
        assert record["median_score"] == 85.3
