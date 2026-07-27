import pytest
from datetime import datetime, timezone
from typing import Dict, List, Any, Optional


# === 被测试的类/函数 ===


class Defect:
    """缺陷实体"""

    def __init__(self, defect_id: str, severity: str, description: str):
        self.defect_id = defect_id
        self.severity = severity
        self.description = description

    def to_dict(self) -> Dict[str, Any]:
        return {
            "defect_id": self.defect_id,
            "severity": self.severity,
            "description": self.description,
        }


class InspectionReport:
    """检验报告表 - 记录QA门控的检验结果与漏检率"""

    def __init__(
        self,
        report_id: str,
        step_number: int,
        inspector: str,
        total_defects: int = 0,
        detected_defects: int = 0,
        missed_defects: int = 0,
        defects: Optional[List[Dict[str, Any]]] = None,
        inspect_time: Optional[datetime] = None,
    ):
        self.report_id = report_id
        self.step_number = step_number
        self.inspector = inspector
        self.total_defects = total_defects
        self.detected_defects = detected_defects
        self.missed_defects = missed_defects
        self.defects = defects or []
        self.inspect_time = inspect_time or datetime.now(timezone.utc)

    @property
    def missed_rate(self) -> float:
        """漏检率 = 漏检数 / 总缺陷数（百分比）"""
        if self.total_defects == 0:
            return 0.0
        return round((self.missed_defects / self.total_defects) * 100, 2)

    def save_to_table(self, table: List["InspectionReport"]) -> None:
        """将报告保存到 inspection_report 表中"""
        table.append(self)

    def to_dict(self) -> Dict[str, Any]:
        return {
            "report_id": self.report_id,
            "step_number": self.step_number,
            "inspector": self.inspector,
            "total_defects": self.total_defects,
            "detected_defects": self.detected_defects,
            "missed_defects": self.missed_defects,
            "missed_rate": self.missed_rate,
            "defects": self.defects,
            "inspect_time": self.inspect_time.isoformat() if self.inspect_time else None,
        }


def calc_missed_rate(total_defects: int, missed_defects: int) -> float:
    """计算漏检率（百分比），总缺陷为0时返回0"""
    if total_defects == 0:
        return 0.0
    return round((missed_defects / total_defects) * 100, 2)


def is_within_threshold(missed_rate: float, threshold: float = 5.0) -> bool:
    """判断漏检率是否在阈值范围内"""
    return missed_rate <= threshold


# === 验收标准：漏检率<=5% ===


class TestMissedRateCalculation:
    """验证漏检率计算逻辑"""

    def test_missed_rate_100_defects_0_missed(self):
        rate = calc_missed_rate(100, 0)
        assert rate == 0.0, "0/100的漏检率应为0.0%"

    def test_missed_rate_100_defects_1_missed(self):
        rate = calc_missed_rate(100, 1)
        assert rate == 1.0, "1/100的漏检率应为1.0%"

    def test_missed_rate_100_defects_5_missed(self):
        rate = calc_missed_rate(100, 5)
        assert rate == 5.0, "5/100的漏检率应为5.0%"

    def test_missed_rate_100_defects_6_missed(self):
        rate = calc_missed_rate(100, 6)
        assert rate == 6.0, "6/100的漏检率应为6.0%"

    def test_missed_rate_zero_total_defects(self):
        rate = calc_missed_rate(0, 0)
        assert rate == 0.0, "总缺陷为0时，漏检率应为0.0%而非异常"

    def test_missed_rate_fractional(self):
        rate = calc_missed_rate(200, 7)
        assert rate == 3.5, "7/200的漏检率应为3.5%"

    def test_missed_rate_rounds_to_2_decimals(self):
        rate = calc_missed_rate(300, 1)
        assert rate == 0.33, "1/300的漏检率应四舍五入为0.33%"

    def test_missed_rate_property_consistent_with_function(self):
        report = InspectionReport(
            report_id="RPT-001",
            step_number=3,
            inspector="",
            total_defects=100,
            detected_defects=95,
            missed_defects=5,
        )
        func_rate = calc_missed_rate(100, 5)
        assert report.missed_rate == func_rate, (
            f"属性missed_rate({report.missed_rate})应与calc_missed_rate({func_rate})一致"
        )


class TestMissedRateThreshold:
    """验证漏检率<=5%的阈值判断"""

    def test_threshold_default_is_5_percent(self):
        assert is_within_threshold(5.0) is True, "5.0%应等于默认阈值5.0%，判定通过"
        assert is_within_threshold(5.0, 5.0) is True, "显式指定5.0%阈值时5.0%应通过"

    def test_zero_missed_rate_within_threshold(self):
        assert is_within_threshold(0.0) is True, "0%漏检率应通过阈值检查"

    def test_1_percent_within_threshold(self):
        assert is_within_threshold(1.0) is True, "1%漏检率应通过阈值检查"

    def test_4_99_percent_within_threshold(self):
        assert is_within_threshold(4.99) is True, "4.99%漏检率应通过阈值检查"

    def test_5_percent_exactly_within_threshold(self):
        assert is_within_threshold(5.0) is True, "恰好5.0%应通过阈值检查（<=）"

    def test_5_01_percent_exceeds_threshold(self):
        assert is_within_threshold(5.01) is False, "5.01%漏检率应超过阈值判定为不通过"

    def test_6_percent_exceeds_threshold(self):
        assert is_within_threshold(6.0) is False, "6%漏检率应超过阈值判定为不通过"

    def test_10_percent_exceeds_threshold(self):
        assert is_within_threshold(10.0) is False, "10%漏检率应超过阈值判定为不通过"

    def test_100_percent_exceeds_threshold(self):
        assert is_within_threshold(100.0) is False, "100%漏检率应超过阈值判定为不通过"

    def test_custom_threshold_10_percent(self):
        assert is_within_threshold(9.9, 10.0) is True, "9.9%在10%阈值内应通过"
        assert is_within_threshold(10.0, 10.0) is True, "10.0%恰好等于阈值应通过"
        assert is_within_threshold(10.1, 10.0) is False, "10.1%超过10%阈值应不通过"


class TestQAGateMissedRateLessOrEqual5Percent:
    """核心验收：QA门控漏检率<=5%（100个缺陷中最多5个被漏检）"""

    def test_100_defects_0_missed_passes(self):
        report = InspectionReport(
            report_id="RPT-100-0",
            step_number=3,
            inspector="",
            total_defects=100,
            detected_defects=100,
            missed_defects=0,
        )
        assert report.missed_rate <= 5.0, "0/100漏检率应为0%，满足<=5%"
        assert is_within_threshold(report.missed_rate) is True, "0%应在阈值内通过门控"

    def test_100_defects_1_missed_passes(self):
        report = InspectionReport(
            report_id="RPT-100-1",
            step_number=3,
            inspector="",
            total_defects=100,
            detected_defects=99,
            missed_defects=1,
        )
        assert report.missed_rate == 1.0, "1/100漏检率应为1.0%"
        assert report.missed_rate <= 5.0, "1.0%应满足<=5%"

    def test_100_defects_4_missed_passes(self):
        report = InspectionReport(
            report_id="RPT-100-4",
            step_number=3,
            inspector="",
            total_defects=100,
            detected_defects=96,
            missed_defects=4,
        )
        assert report.missed_rate == 4.0, "4/100漏检率应为4.0%"
        assert is_within_threshold(report.missed_rate) is True, "4.0%应在阈值内通过门控"

    def test_100_defects_5_missed_boundary_passes(self):
        report = InspectionReport(
            report_id="RPT-100-5",
            step_number=3,
            inspector="",
            total_defects=100,
            detected_defects=95,
            missed_defects=5,
        )
        assert report.missed_rate == 5.0, "5/100漏检率应为5.0%"
        assert report.missed_rate <= 5.0, "5.0%应满足<=5%（含边界）"
        assert is_within_threshold(report.missed_rate) is True, "5.0%边界应在阈值内"

    def test_100_defects_6_missed_fails(self):
        report = InspectionReport(
            report_id="RPT-100-6",
            step_number=3,
            inspector="",
            total_defects=100,
            detected_defects=94,
            missed_defects=6,
        )
        assert report.missed_rate == 6.0, "6/100漏检率应为6.0%"
        assert is_within_threshold(report.missed_rate) is False, "6.0%应超过阈值被门控拦截"

    def test_50_defects_2_missed_passes(self):
        report = InspectionReport(
            report_id="RPT-050-2",
            step_number=5,
            inspector="",
            total_defects=50,
            detected_defects=48,
            missed_defects=2,
        )
        assert report.missed_rate == 4.0, "2/50漏检率应为4.0%"
        assert is_within_threshold(report.missed_rate) is True, "4.0%应在阈值内"

    def test_50_defects_3_missed_exceeds(self):
        report = InspectionReport(
            report_id="RPT-050-3",
            step_number=5,
            inspector="",
            total_defects=50,
            detected_defects=47,
            missed_defects=3,
        )
        assert report.missed_rate == 6.0, "3/50漏检率应为6.0%"
        assert is_within_threshold(report.missed_rate) is False, "6.0%应超过阈值"

    def test_200_defects_10_missed_boundary(self):
        report = InspectionReport(
            report_id="RPT-200-10",
            step_number=7,
            inspector="",
            total_defects=200,
            detected_defects=190,
            missed_defects=10,
        )
        assert report.missed_rate == 5.0, "10/200漏检率应为5.0%"
        assert is_within_threshold(report.missed_rate) is True, "5.0%边界应在阈值内"

    def test_200_defects_11_missed_exceeds(self):
        report = InspectionReport(
            report_id="RPT-200-11",
            step_number=7,
            inspector="",
            total_defects=200,
            detected_defects=189,
            missed_defects=11,
        )
        assert report.missed_rate == 5.5, "11/200漏检率应为5.5%"
        assert is_within_threshold(report.missed_rate) is False, "5.5%应超过阈值"

    def test_10_defects_0_missed_passes(self):
        report = InspectionReport(
            report_id="RPT-010-0",
            step_number=9,
            inspector="",
            total_defects=10,
            detected_defects=10,
            missed_defects=0,
        )
        assert report.missed_rate == 0.0, "0/10漏检率应为0.0%"
        assert is_within_threshold(report.missed_rate) is True, "0%应在阈值内"

    def test_10_defects_1_missed_exceeds(self):
        report = InspectionReport(
            report_id="RPT-010-1",
            step_number=9,
            inspector="",
            total_defects=10,
            detected_defects=9,
            missed_defects=1,
        )
        assert report.missed_rate == 10.0, "1/10漏检率应为10.0%"
        assert is_within_threshold(report.missed_rate) is False, "10%应超过阈值"


@pytest.fixture
def empty_inspection_table():
    """返回一个空inspection_report表，确保每次测试独立隔离"""
    return []


class TestInspectionReportTable:
    """验证漏检率数值记录到inspection_report表"""

    def test_report_saved_to_table(self, empty_inspection_table):
        table = empty_inspection_table
        assert len(table) == 0, "初始表应为空"
        report = InspectionReport(
            report_id="RPT-001",
            step_number=3,
            inspector="",
            total_defects=100,
            detected_defects=95,
            missed_defects=5,
        )
        report.save_to_table(table)
        assert len(table) == 1, "保存后表内含1条记录"
        assert table[0].report_id == "RPT-001", "保存的report_id应为RPT-001"
        assert table[0].missed_rate == 5.0, "保存的漏检率应为5.0%"

    def test_report_to_dict_contains_missed_rate(self, empty_inspection_table):
        report = InspectionReport(
            report_id="RPT-002",
            step_number=5,
            inspector="",
            total_defects=100,
            detected_defects=97,
            missed_defects=3,
        )
        d = report.to_dict()
        assert "missed_rate" in d, "to_dict()结果应包含missed_rate字段"
        assert d["missed_rate"] == 3.0, "missed_rate字段值应为3.0%"

    def test_multiple_reports_in_table(self, empty_inspection_table):
        table = empty_inspection_table
        for i in range(5):
            r = InspectionReport(
                report_id=f"RPT-BULK-{i}",
                step_number=3 + i,
                inspector="",
                total_defects=100,
                detected_defects=95 + i,
                missed_defects=5 - i,
            )
            r.save_to_table(table)
        assert len(table) == 5, "应保存5条报告记录"
        for idx, report in enumerate(table):
            assert report.missed_rate <= 5.0, f"第{idx}条记录漏检率{report.missed_rate}%应<=5%"

    def test_report_records_all_required_fields(self, empty_inspection_table):
        table = empty_inspection_table
        fixed_time = datetime(2026, 7, 20, 12, 0, 0, tzinfo=timezone.utc)
        report = InspectionReport(
            report_id="RPT-FULL-001",
            step_number=3,
            inspector="",
            total_defects=100,
            detected_defects=95,
            missed_defects=5,
            defects=[
                {"defect_id": "DEF-001", "severity": "MAJOR", "description": "未检测到的缺陷1"},
                {"defect_id": "DEF-002", "severity": "MINOR", "description": "未检测到的缺陷2"},
            ],
            inspect_time=fixed_time,
        )
        report.save_to_table(table)
        d = table[0].to_dict()
        assert d["report_id"] == "RPT-FULL-001", "report_id应正确记录"
        assert d["step_number"] == 3, "step_number应正确记录为3"
        assert d["total_defects"] == 100, "total_defects应正确记录为100"
        assert d["detected_defects"] == 95, "detected_defects应正确记录为95"
        assert d["missed_defects"] == 5, "missed_defects应正确记录为5"
        assert d["missed_rate"] == 5.0, "missed_rate应正确计算为5.0%"
        assert len(d["defects"]) == 2, "defects列表应包含2条缺陷"
        assert "2026-07-20" in d["inspect_time"], "inspect_time应包含固定日期2026-07-20"

    def test_table_report_missed_rate_persists_correctly(self, empty_inspection_table):
        table = empty_inspection_table
        report = InspectionReport(
            report_id="RPT-PERSIST-001",
            step_number=5,
            inspector="",
            total_defects=200,
            detected_defects=192,
            missed_defects=8,
        )
        report.save_to_table(table)
        stored = table[0]
        assert stored.missed_rate == 4.0, "持久化的漏检率属性应为4.0%"
        assert stored.to_dict()["missed_rate"] == 4.0, "持久化的to_dict()中missed_rate应为4.0%"

    def test_table_report_zero_total_defects_has_zero_rate(self, empty_inspection_table):
        table = empty_inspection_table
        report = InspectionReport(
            report_id="RPT-ZERO-001",
            step_number=1,
            inspector="",
            total_defects=0,
            detected_defects=0,
            missed_defects=0,
        )
        report.save_to_table(table)
        assert table[0].missed_rate == 0.0, "零缺陷场景下漏检率属性应为0.0%"
        assert table[0].to_dict()["missed_rate"] == 0.0, "零缺陷场景下to_dict()中missed_rate应为0.0%"


class TestFullQAInspectionFlow:
    """端到端：QA门控检验流程 - 从缺陷注入到漏检率记录"""

    def test_qa_gate_flow_with_5_percent_missed(self):
        """模拟100个缺陷注入，QA检出95个，漏检5个，漏检率=5%，应通过门控"""
        total_defects = 100
        injected_defects = [
            Defect(f"DEF-{i:03d}", "MAJOR" if i < 20 else "MINOR", f"缺陷")
            for i in range(total_defects)
        ]

        detected_count = 95
        missed_count = 5
        detected_defects = [d.to_dict() for d in injected_defects[:detected_count]]

        report = InspectionReport(
            report_id="QA-FLOW-001",
            step_number=3,
            inspector="",
            total_defects=total_defects,
            detected_defects=detected_count,
            missed_defects=missed_count,
            defects=detected_defects,
            inspect_time=datetime(2026, 7, 20, 10, 0, 0, tzinfo=timezone.utc),
        )

        table: List[InspectionReport] = []
        report.save_to_table(table)

        assert len(table) == 1, "门控流程应产生1条检验报告"
        stored = table[0]
        assert stored.missed_rate == 5.0, "100缺陷5漏检的漏检率应为5.0%"
        assert is_within_threshold(stored.missed_rate) is True, "5.0%应通过门控"
        assert stored.to_dict()["missed_rate"] == 5.0, "报告字典中漏检率应为5.0%"

    def test_qa_gate_flow_with_0_percent_missed(self):
        """模拟100个缺陷注入，QA全部检出，漏检率=0%，应通过门控"""
        total_defects = 100
        detected_count = 100
        missed_count = 0

        report = InspectionReport(
            report_id="QA-FLOW-002",
            step_number=5,
            inspector="",
            total_defects=total_defects,
            detected_defects=detected_count,
            missed_defects=missed_count,
            inspect_time=datetime(2026, 7, 20, 11, 0, 0, tzinfo=timezone.utc),
        )

        table: List[InspectionReport] = []
        report.save_to_table(table)

        assert table[0].missed_rate == 0.0, "全部检出时漏检率应为0.0%"
        assert is_within_threshold(0.0) is True, "0%漏检率应通过门控"

    def test_qa_gate_flow_6_percent_missed_gate_blocks(self):
        """模拟100个缺陷注入，QA检出94个，漏检6个，漏检率=6%，门控应拦截"""
        total_defects = 100
        detected_count = 94
        missed_count = 6

        report = InspectionReport(
            report_id="QA-FLOW-FAIL",
            step_number=7,
            inspector="",
            total_defects=total_defects,
            detected_defects=detected_count,
            missed_defects=missed_count,
            inspect_time=datetime(2026, 7, 20, 12, 0, 0, tzinfo=timezone.utc),
        )

        table: List[InspectionReport] = []
        report.save_to_table(table)

        stored = table[0]
        assert stored.missed_rate == 6.0, "100缺陷6漏检的漏检率应为6.0%"
        assert is_within_threshold(stored.missed_rate) is False, "6.0%应被门控拦截"

    def test_multi_step_qa_inspection_all_within_threshold(self):
        """模拟多步骤检验，所有步骤漏检率均<=5%"""
        table: List[InspectionReport] = []
        step_configs: list[tuple[int, int, int, int]] = [
            (2, 50, 48, 2),
            (3, 100, 96, 4),
            (4, 150, 143, 7),
            (5, 80, 78, 2),
            (6, 200, 190, 10),
        ]

        for step_num, total, detected, missed in step_configs:
            report = InspectionReport(
                report_id=f"QA-MULTI-STEP-{step_num}",
                step_number=step_num,
                inspector="",
                total_defects=total,
                detected_defects=detected,
                missed_defects=missed,
            )
            report.save_to_table(table)

        assert len(table) == 5, "应产生5条步骤检验报告"
        for report in table:
            assert report.missed_rate <= 5.0, (
                f"步骤{report.step_number}漏检率{report.missed_rate}%应<=5%"
            )
            assert is_within_threshold(report.missed_rate) is True, (
                f"步骤{report.step_number}应通过阈值检查"
            )

    def test_multi_step_qa_inspection_one_exceeds_threshold(self):
        """多步骤检验中，有一步漏检率超过5%，应能准确定位"""
        table: List[InspectionReport] = []
        step_configs: list[tuple[int, int, int, int]] = [
            (2, 100, 99, 1),
            (3, 100, 93, 7),
            (4, 100, 97, 3),
        ]

        for step_num, total, detected, missed in step_configs:
            report = InspectionReport(
                report_id=f"QA-MULTI-EXCEED-{step_num}",
                step_number=step_num,
                inspector="",
                total_defects=total,
                detected_defects=detected,
                missed_defects=missed,
            )
            report.save_to_table(table)

        failing = [r for r in table if not is_within_threshold(r.missed_rate)]
        assert len(failing) == 1, "应仅有1个步骤超过阈值"
        assert failing[0].step_number == 3, "超过阈值的步骤应为步骤3"
        assert failing[0].missed_rate == 7.0, "步骤3的漏检率应为7.0%"
