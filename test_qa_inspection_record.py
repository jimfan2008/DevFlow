import pytest
from datetime import datetime, timezone
from typing import Dict, List, Any, Optional


# === 被测试的类/函数 ===

REQUIRED_FIELDS = ["检验ID", "步骤号", "产出人", "检验人", "提交时间", "检验结果", "不合格项"]

WEIGHTS = {
    "完整性": 0.30,
    "一致性": 0.30,
    "可验证性": 0.20,
    "无歧义性": 0.20,
}


class QAInspectionRecord:
    """QA检验记录表"""

    def __init__(
        self,
        inspection_id: str,
        step_number: int,
        producer: str,
        inspector: str,
        submit_time: Optional[datetime] = None,
        result: str = "待定",
        defects: Optional[List[Dict[str, Any]]] = None,
    ):
        self.检验ID = inspection_id
        self.步骤号 = step_number
        self.产出人 = producer
        self.检验人 = inspector
        self.提交时间 = submit_time or datetime.now(timezone.utc)
        self.检验结果 = result
        self.不合格项 = defects or []

    def to_dict(self) -> Dict[str, Any]:
        return {
            "检验ID": self.检验ID,
            "步骤号": self.步骤号,
            "产出人": self.产出人,
            "检验人": self.检验人,
            "提交时间": self.提交时间.isoformat() if self.提交时间 else None,
            "检验结果": self.检验结果,
            "不合格项": self.不合格项,
        }

    def is_complete(self) -> bool:
        d = self.to_dict()
        for field in REQUIRED_FIELDS:
            val = d.get(field)
            if val is None:
                return False
            if isinstance(val, str) and val.strip() == "":
                return False
            if field == "不合格项" and not isinstance(val, list):
                return False
        return True


def calc_record_completeness(record: Dict[str, Any]) -> float:
    """计算记录完整度百分比"""
    if not record:
        return 0.0
    present = sum(1 for f in REQUIRED_FIELDS if f in record and record[f] is not None)
    return (present / len(REQUIRED_FIELDS)) * 100


def calc_score(dimension_scores: Dict[str, float]) -> float:
    """
    score = 完整性x30% + 一致性x30% + 可验证性x20% + 无歧义性x20%
    """
    total = 0.0
    for dim, weight in WEIGHTS.items():
        total += dimension_scores.get(dim, 0.0) * weight
    return round(total, 2)


# === 测试用例 ===


class TestQAInspectionRecordFields:
    """验证QA检验记录表字段完整度"""

    def test_record_contains_all_required_fields(self):
        record = QAInspectionRecord(
            inspection_id="QA-001",
            step_number=3,
            producer="产出者A",
            inspector="检验者B",
            result="合格",
            defects=[],
        )
        d = record.to_dict()
        for field in REQUIRED_FIELDS:
            assert field in d, f"缺少必填字段: {field}"

    def test_record_completeness_100_percent(self):
        record = QAInspectionRecord(
            inspection_id="QA-002",
            step_number=5,
            producer="产出者C",
            inspector="检验者D",
            result="不合格",
            defects=[{"缺陷编号": "DEF-001", "问题": "缺少测试用例"}],
        )
        d = record.to_dict()
        completeness = calc_record_completeness(d)
        assert completeness == 100.0, f"完整度应为100%，实际{completeness}%"

    def test_record_missing_field_reduces_completeness(self):
        partial = {
            "检验ID": "QA-003",
            "步骤号": 1,
            "产出人": "某人",
        }
        completeness = calc_record_completeness(partial)
        expected = (3 / len(REQUIRED_FIELDS)) * 100
        assert completeness == expected, f"完整度应为{expected}%，实际{completeness}%"

    def test_empty_record_has_zero_completeness(self):
        assert calc_record_completeness({}) == 0.0
        assert calc_record_completeness(None) == 0.0

    def test_is_complete_returns_true_for_full_record(self):
        record = QAInspectionRecord(
            inspection_id="QA-004",
            step_number=2,
            producer="产出者E",
            inspector="检验者F",
            result="合格",
            defects=[],
        )
        assert record.is_complete() is True

    def test_is_complete_returns_false_for_empty_string_field(self):
        record = QAInspectionRecord(
            inspection_id="",
            step_number=2,
            producer="产出者E",
            inspector="检验者F",
            result="合格",
            defects=[],
        )
        assert record.is_complete() is False


class TestQAScoreCalculation:
    """验证score = 完整性x30% + 一致性x30% + 可验证性x20% + 无歧义性x20%"""

    def test_score_all满分(self):
        dims = {"完整性": 100, "一致性": 100, "可验证性": 100, "无歧义性": 100}
        score = calc_score(dims)
        expected = 100 * 0.30 + 100 * 0.30 + 100 * 0.20 + 100 * 0.20
        assert score == expected, f"应{expected}，实际{score}"

    def test_score_weighted_calculation(self):
        dims = {"完整性": 90, "一致性": 80, "可验证性": 70, "无歧义性": 60}
        score = calc_score(dims)
        expected = 90 * 0.30 + 80 * 0.30 + 70 * 0.20 + 60 * 0.20
        assert score == round(expected, 2), f"应{round(expected, 2)}，实际{score}"

    def test_score_missing_dimension_defaults_to_zero(self):
        dims = {"完整性": 90, "一致性": 80}
        score = calc_score(dims)
        expected = 90 * 0.30 + 80 * 0.30 + 0 * 0.20 + 0 * 0.20
        assert score == expected, f"应{expected}，实际{score}"

    def test_score_all_zero(self):
        dims = {"完整性": 0, "一致性": 0, "可验证性": 0, "无歧义性": 0}
        assert calc_score(dims) == 0.0

    def test_score_empty_dict(self):
        assert calc_score({}) == 0.0

    def test_score_weights_sum_to_100(self):
        total_weight = sum(WEIGHTS.values())
        assert total_weight == 1.0, f"权重之和应100%，实际{total_weight * 100}%"

    def test_score_precision_rounded(self):
        dims = {"完整性": 88, "一致性": 77, "可验证性": 66, "无歧义性": 55}
        score = calc_score(dims)
        assert score == round(88 * 0.30 + 77 * 0.30 + 66 * 0.20 + 55 * 0.20, 2)

    def test_weights_are_correct(self):
        assert WEIGHTS["完整性"] == 0.30
        assert WEIGHTS["一致性"] == 0.30
        assert WEIGHTS["可验证性"] == 0.20
        assert WEIGHTS["无歧义性"] == 0.20


class TestQAInspectionRecordIntegration:
    """端到端检验记录流程"""

    def test_full_inspection_flow_pass(self):
        submit_time = datetime(2026, 7, 20, 12, 0, 0, tzinfo=timezone.utc)
        record = QAInspectionRecord(
            inspection_id="QA-20260720-001",
            step_number=3,
            producer="侯星",
            inspector="后荣",
            submit_time=submit_time,
            result="合格",
            defects=[],
        )
        d = record.to_dict()
        assert calc_record_completeness(d) == 100.0
        dims = {"完整性": 95, "一致性": 92, "可验证性": 90, "无歧义性": 93}
        score = calc_score(dims)
        assert score > 0
        assert record.is_complete() is True
        assert d["检验结果"] == "合格"
        assert d["不合格项"] == []

    def test_full_inspection_flow_fail_with_defects(self):
        defects = [
            {
                "缺陷编号": "VER-001",
                "严重级别": "MAJOR",
                "问题": "响应时间指标不可验证",
                "修改方向": "补充具体的测试方法",
                "证据": "文档第5节未定义验证方式",
            },
            {
                "缺陷编号": "AMB-001",
                "严重级别": "MINOR",
                "问题": "术语定义模糊",
                "修改方向": "增加术语表",
                "证据": "文档多处使用'用户'一词未定义",
            },
        ]
        record = QAInspectionRecord(
            inspection_id="QA-20260720-002",
            step_number=3,
            producer="侯星",
            inspector="后荣",
            submit_time=datetime.now(timezone.utc),
            result="不合格",
            defects=defects,
        )
        d = record.to_dict()
        assert calc_record_completeness(d) == 100.0
        assert len(d["不合格项"]) == 2
        assert d["检验结果"] == "不合格"
        dims = {"完整性": 95, "一致性": 95, "可验证性": 60, "无歧义性": 70}
        score = calc_score(dims)
        expected = round(95 * 0.30 + 95 * 0.30 + 60 * 0.20 + 70 * 0.20, 2)
        assert score == expected

    def test_to_dict_serializes_datetime(self):
        submit_time = datetime(2026, 7, 20, 12, 0, 0, tzinfo=timezone.utc)
        record = QAInspectionRecord(
            inspection_id="QA-DT-001",
            step_number=1,
            producer="A",
            inspector="B",
            submit_time=submit_time,
            result="合格",
            defects=[],
        )
        d = record.to_dict()
        assert "2026-07-20" in d["提交时间"]

    def test_record_id_is_preserved(self):
        record = QAInspectionRecord(
            inspection_id="UNIQUE-ID-12345",
            step_number=7,
            producer="产出者X",
            inspector="检验者Y",
            result="合格",
            defects=[],
        )
        d = record.to_dict()
        assert d["检验ID"] == "UNIQUE-ID-12345"

    def test_step_number_is_preserved(self):
        record = QAInspectionRecord(
            inspection_id="QA-STEP-001",
            step_number=16,
            producer="A",
            inspector="B",
            result="合格",
            defects=[],
        )
        d = record.to_dict()
        assert d["步骤号"] == 16

    def test_producer_and_inspector_are_preserved(self):
        record = QAInspectionRecord(
            inspection_id="QA-PERSON-001",
            step_number=1,
            producer="产出人张三",
            inspector="检验人李四",
            result="合格",
            defects=[],
        )
        d = record.to_dict()
        assert d["产出人"] == "产出人张三"
        assert d["检验人"] == "检验人李四"
