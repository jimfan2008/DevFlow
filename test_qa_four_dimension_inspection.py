import pytest
import json
from dataclasses import dataclass, field, asdict
from typing import Optional


@dataclass
class QADefect:
    """QA检验中发现的缺陷"""
    defect_id: str
    dimension: str
    severity: str  # CRITICAL / MAJOR / MINOR
    description: str
    evidence: str
    fix_direction: str


@dataclass
class DimensionResult:
    """单维度检验结果"""
    dimension_key: str
    dimension_label: str
    score: int
    passed: bool
    defects: list = field(default_factory=list)


@dataclass
class QAInspectorResult:
    """四维检验总结果"""
    completeness: DimensionResult
    consistency: DimensionResult
    verifiability: DimensionResult
    unambiguity: DimensionResult
    overall_passed: bool = False
    total_defects: int = 0
    all_defects: list = field(default_factory=list)


class QAFourDimensionInspector:
    """QA四维检验器：完整性、一致性、可验证性、无歧义性"""

    DIMENSIONS = ["completeness", "consistency", "verifiability", "unambiguity"]

    LABEL_MAP = {
        "completeness": "完整性",
        "consistency": "一致性",
        "verifiability": "可验证性",
        "unambiguity": "无歧义性",
    }

    # 合格阈值
    THRESHOLDS = {
        "completeness": 90,
        "consistency": 100,
        "verifiability": 90,
        "unambiguity": 90,
    }

    def __init__(self, document_content: str, document_type: str = "srs"):
        self.document_content = document_content
        self.document_type = document_type
        self._rules = []

    def add_check_rules(self, rules: list):
        """注册检验规则列表，每条规则包含 dimension、check_fn、weight"""
        self._rules = rules

    def inspect(self) -> QAInspectorResult:
        """执行四维检验，返回总结果"""
        completeness = self._check_completeness()
        consistency = self._check_consistency()
        verifiability = self._check_verifiability()
        unambiguity = self._check_unambiguity()

        all_results = [completeness, consistency, verifiability, unambiguity]
        all_defects = []
        total_defects = 0
        for r in all_results:
            all_defects.extend(r.defects)
            total_defects += len(r.defects)

        overall_passed = all(r.passed for r in all_results)

        return QAInspectorResult(
            completeness=completeness,
            consistency=consistency,
            verifiability=verifiability,
            unambiguity=unambiguity,
            overall_passed=overall_passed,
            total_defects=total_defects,
            all_defects=all_defects,
        )

    def _check_completeness(self) -> DimensionResult:
        """完整性检验：文档是否覆盖所有必需章节"""
        required_sections = {
            "srs": ["功能需求", "非功能需求", "验收标准", "约束条件"],
            "design": ["架构设计", "前端设计", "后端设计", "数据库设计"],
            "default": ["概述", "需求", "设计", "实现"],
        }
        sections = required_sections.get(self.document_type, required_sections["default"])
        defects = []
        missing = []
        for section in sections:
            if section not in self.document_content:
                missing.append(section)
                defects.append(QADefect(
                    defect_id=f"CMP-{len(defects)+1:03d}",
                    dimension="completeness",
                    severity="MAJOR",
                    description=f"缺少必需章节：{section}",
                    evidence=f"文档中未找到'{section}'相关描述",
                    fix_direction=f"补充'{section}'章节内容",
                ))
        covered = len(sections) - len(missing)
        score = int((covered / len(sections)) * 100) if sections else 0
        return DimensionResult(
            dimension_key="completeness",
            dimension_label="完整性",
            score=score,
            passed=score >= self.THRESHOLDS["completeness"],
            defects=defects,
        )

    def _check_consistency(self) -> DimensionResult:
        """一致性检验：文档内部是否存在矛盾描述"""
        defects = []
        contradictions = self._find_contradictions()
        for ctx, evidence in contradictions:
            defects.append(QADefect(
                defect_id=f"CNS-{len(defects)+1:03d}",
                dimension="consistency",
                severity="CRITICAL",
                description=f"存在矛盾描述：{ctx}",
                evidence=evidence,
                fix_direction="消除矛盾描述，统一说法",
            ))
        total_checks = max(len(contradictions) + 1, 1)
        passed_count = total_checks - len(contradictions)
        score = 100 if not contradictions else 0
        return DimensionResult(
            dimension_key="consistency",
            dimension_label="一致性",
            score=score,
            passed=score >= self.THRESHOLDS["consistency"],
            defects=defects,
        )

    def _check_verifiability(self) -> DimensionResult:
        """可验证性检验：验收标准是否可量化测量"""
        defects = []
        unmeasurable = []
        if self.document_type == "srs":
            accept_criteria = self._extract_acceptance_criteria()
            for criterion in accept_criteria:
                if not self._is_measurable(criterion):
                    unmeasurable.append(criterion)
                    defects.append(QADefect(
                        defect_id=f"VER-{len(defects)+1:03d}",
                        dimension="verifiability",
                        severity="MAJOR",
                        description=f"验收标准不可量化：{criterion}",
                        evidence="该标准缺少可测量的数值或判定条件",
                        fix_direction="补充具体的测试方法和判定阈值",
                    ))
            total = max(len(accept_criteria), 1)
            measurable = total - len(unmeasurable)
            score = int((measurable / total) * 100)
        else:
            score = 100
        return DimensionResult(
            dimension_key="verifiability",
            dimension_label="可验证性",
            score=score,
            passed=score >= self.THRESHOLDS["verifiability"],
            defects=defects,
        )

    def _check_unambiguity(self) -> DimensionResult:
        """无歧义性检验：是否存在模糊用语"""
        defects = []
        vague_terms = ["可能", "大概", "尽量", "尽可能", "差不多", "适当",
                        "相关", "某些", "一些", "若干"]
        found_vague = []
        for term in vague_terms:
            count = self.document_content.count(term)
            if count > 0:
                found_vague.append((term, count))
                defects.append(QADefect(
                    defect_id=f"UAM-{len(defects)+1:03d}",
                    dimension="unambiguity",
                    severity="MINOR",
                    description=f"存在模糊用语：'{term}'（出现{count}次）",
                    evidence=f"在文档中共出现{count}次'{term}'",
                    fix_direction=f"将'{term}'替换为明确具体的表述",
                ))
        total_terms = len(self.document_content.split()) if self.document_content.split() else 1
        vague_count = sum(c for _, c in found_vague)
        score = max(0, int(100 * (1 - vague_count / max(total_terms, 1))))
        return DimensionResult(
            dimension_key="unambiguity",
            dimension_label="无歧义性",
            score=score,
            passed=score >= self.THRESHOLDS["unambiguity"],
            defects=defects,
        )

    def _find_contradictions(self) -> list:
        """查找文档内部矛盾（基于规则匹配）"""
        contradictions = []
        for rule in self._rules:
            if rule.get("dimension") == "consistency":
                check_fn = rule.get("check_fn")
                if check_fn and not check_fn(self.document_content):
                    contradictions.append((rule.get("context", "未命名"), rule.get("evidence", "")))
        # 内置检查：同一指标不同数值
        import re
        perf_patterns = re.findall(r"响应.*?([0-9]+).*?秒", self.document_content)
        if len(set(perf_patterns)) > 1:
            contradictions.append(("响应时间存在多个不同数值", f"找到数值：{perf_patterns}"))
        return contradictions

    def _extract_acceptance_criteria(self) -> list:
        """提取验收标准条款"""
        import re
        lines = self.document_content.split("\n")
        criteria = []
        for line in lines:
            stripped = line.strip()
            if any(kw in stripped for kw in ["验收", "测试标准", "判定", "必须满足"]):
                criteria.append(stripped)
        return criteria

    def _is_measurable(self, criterion: str) -> bool:
        """判断验收标准是否可量化"""
        import re
        measurable_patterns = [
            r"[0-9]+%?[0-9]*",
            r"不超过|不小于|等于|大于|小于|至少|至多",
            r"秒|毫秒|分钟|小时",
            r"MB|GB|TB|Bps",
            r"PASS|FAIL|通过|不通过",
        ]
        return any(re.search(p, criterion) for p in measurable_patterns)

    def to_json_report(self, result: QAInspectorResult) -> dict:
        """将检验结果转换为标准JSON报告格式"""
        defect_chapters = []
        for dim_result in [result.completeness, result.consistency,
                           result.verifiability, result.unambiguity]:
            if not dim_result.passed or dim_result.defects:
                defect_chapters.append({
                    "dimension_key": dim_result.dimension_key,
                    "dimension_label": dim_result.dimension_label,
                    "score": dim_result.score,
                    "passed": dim_result.passed,
                    "defect_count": len(dim_result.defects),
                    "defects": [asdict(d) for d in dim_result.defects],
                })
        return {
            "report_type": "qa_four_dimension_inspection",
            "document_type": self.document_type,
            "overall_passed": result.overall_passed,
            "total_defects": result.total_defects,
            "dimensions": {
                "completeness": {"score": result.completeness.score, "passed": result.completeness.passed},
                "consistency": {"score": result.consistency.score, "passed": result.consistency.passed},
                "verifiability": {"score": result.verifiability.score, "passed": result.verifiability.passed},
                "unambiguity": {"score": result.unambiguity.score, "passed": result.unambiguity.passed},
            },
            "defect_chapters": defect_chapters,
        }


class DefectTracker:
    """缺陷跟踪器：跟踪不合格项的修复状态"""

    def __init__(self):
        self._defects = {}

    def register_defects(self, defects: list):
        """注册缺陷列表"""
        for d in defects:
            self._defects[d.defect_id] = {"defect": d, "status": "open"}

    def fix_defect(self, defect_id: str, fix_description: str):
        """标记缺陷已修复"""
        if defect_id in self._defects:
            self._defects[defect_id]["status"] = "fixed"
            self._defects[defect_id]["fix"] = fix_description

    def get_fix_rate(self) -> float:
        """计算修复率"""
        if not self._defects:
            return 100.0
        fixed = sum(1 for v in self._defects.values() if v["status"] == "fixed")
        return (fixed / len(self._defects)) * 100

    def get_open_defects(self) -> list:
        """返回未修复的缺陷"""
        return [v["defect"] for v in self._defects.values() if v["status"] == "open"]

    def all_fixed(self) -> bool:
        """是否全部修复"""
        return self.get_fix_rate() == 100.0


# ==================== 测试数据 ====================

GOOD_SRS_DOC = """
# 软件需求说明书

## 1. 功能需求
系统支持用户注册、登录、注销功能。
用户注册需要提供邮箱和密码。

## 2. 非功能需求
系统响应时间不超过2秒。
系统可用性不低于99.9%。

## 3. 验收标准
注册功能验收标准：输入合法邮箱和密码，3秒内完成注册并返回成功响应码200。
登录功能验收标准：输入正确用户名和密码，2秒内返回用户信息JSON。
系统性能验收标准：并发用户数达到1000时，平均响应时间不超过500毫秒。

## 4. 约束条件
后端框架使用FastAPI。
数据库使用PostgreSQL 15。
"""

INCOMPLETE_SRS_DOC = """
# 软件需求说明书

## 1. 功能需求
系统支持用户注册和登录。
"""

AMBIGUOUS_SRS_DOC = """
# 软件需求说明书

## 1. 功能需求
系统可能支持用户注册，大概还能登录。
用户尽量提供邮箱。

## 2. 非功能需求
响应时间要快一些。

## 3. 验收标准
注册功能验收标准：系统差不多能完成注册就行。
登录功能验收标准：能登录就通过。

## 4. 约束条件
后端用某些框架。
"""

INCONSISTENT_SRS_DOC = """
# 软件需求说明书

## 1. 功能需求
系统支持用户注册、登录、注销功能。

## 2. 非功能需求
系统响应时间不超过2秒。
系统峰值响应时间为5秒。

## 3. 验收标准
注册功能验收标准：输入合法邮箱和密码，3秒内完成注册并返回成功响应码200。
登录功能验收标准：输入正确用户名和密码，2秒内返回用户信息JSON。
系统性能验收标准：并发用户数达到1000时，平均响应时间不超过500毫秒。

## 4. 约束条件
后端框架使用FastAPI。
数据库使用PostgreSQL 15。
"""


# ==================== Tests ====================

class TestQAInspectorInstantiation:
    """检验器初始化测试"""

    def test_create_inspector_with_srs_doc(self):
        inspector = QAFourDimensionInspector(GOOD_SRS_DOC, "srs")
        assert inspector.document_content == GOOD_SRS_DOC
        assert inspector.document_type == "srs"

    def test_create_inspector_default_type(self):
        inspector = QAFourDimensionInspector("some content")
        assert inspector.document_type == "srs"

    def test_dimensions_defined(self):
        assert QAFourDimensionInspector.DIMENSIONS == [
            "completeness", "consistency", "verifiability", "unambiguity"
        ]

    def test_label_map_complete(self):
        expected = {
            "completeness": "完整性",
            "consistency": "一致性",
            "verifiability": "可验证性",
            "unambiguity": "无歧义性",
        }
        assert QAFourDimensionInspector.LABEL_MAP == expected

    def test_thresholds_defined(self):
        expected = {
            "completeness": 90,
            "consistency": 100,
            "verifiability": 90,
            "unambiguity": 90,
        }
        assert QAFourDimensionInspector.THRESHOLDS == expected


class TestCompletenessDimension:
    """完整性维度测试"""

    def test_complete_srs_passes_completeness(self):
        inspector = QAFourDimensionInspector(GOOD_SRS_DOC, "srs")
        result = inspector.inspect()
        assert result.completeness.score >= 90
        assert result.completeness.passed is True
        assert result.completeness.defects == []

    def test_incomplete_srs_fails_completeness(self):
        inspector = QAFourDimensionInspector(INCOMPLETE_SRS_DOC, "srs")
        result = inspector.inspect()
        # 只包含"功能需求"，缺"非功能需求"、"验收标准"、"约束条件"，覆盖率25%
        assert result.completeness.score == 25
        assert result.completeness.passed is False
        assert len(result.completeness.defects) == 3

    def test_completeness_defect_format(self):
        inspector = QAFourDimensionInspector(INCOMPLETE_SRS_DOC, "srs")
        result = inspector.inspect()
        for defect in result.completeness.defects:
            assert defect.defect_id.startswith("CMP-")
            assert defect.dimension == "completeness"
            assert defect.severity in ("CRITICAL", "MAJOR", "MINOR")
            assert defect.description != ""
            assert defect.evidence != ""
            assert defect.fix_direction != ""


class TestConsistencyDimension:
    """一致性维度测试"""

    def test_consistent_doc_passes_consistency(self):
        inspector = QAFourDimensionInspector(GOOD_SRS_DOC, "srs")
        result = inspector.inspect()
        assert result.consistency.score == 100
        assert result.consistency.passed is True

    def test_inconsistent_doc_fails_consistency(self):
        inspector = QAFourDimensionInspector(INCONSISTENT_SRS_DOC, "srs")
        result = inspector.inspect()
        assert result.consistency.score == 0
        assert result.consistency.passed is False
        assert len(result.consistency.defects) >= 1

    def test_consistency_threshold_is_strict_100(self):
        assert QAFourDimensionInspector.THRESHOLDS["consistency"] == 100

    def test_consistency_defect_severity_is_critical(self):
        inspector = QAFourDimensionInspector(INCONSISTENT_SRS_DOC, "srs")
        result = inspector.inspect()
        for defect in result.consistency.defects:
            assert defect.severity == "CRITICAL"


class TestVerifiabilityDimension:
    """可验证性维度测试"""

    def test_good_srs_has_measurable_criteria(self):
        inspector = QAFourDimensionInspector(GOOD_SRS_DOC, "srs")
        result = inspector.inspect()
        assert result.verifiability.score >= 90
        assert result.verifiability.passed is True

    def test_non_srs_type_returns_100(self):
        inspector = QAFourDimensionInspector("any content", "design")
        result = inspector.inspect()
        assert result.verifiability.score == 100
        assert result.verifiability.passed is True

    def test_verifiability_threshold_is_90(self):
        assert QAFourDimensionInspector.THRESHOLDS["verifiability"] == 90

    def test_measurable_criterion_detection(self):
        inspector = QAFourDimensionInspector("")
        assert inspector._is_measurable("响应时间不超过2秒") is True
        assert inspector._is_measurable("可用性不低于99.9%") is True
        assert inspector._is_measurable("并发用户数达到1000时") is True
        assert inspector._is_measurable("返回成功响应码200") is True
        assert inspector._is_measurable("测试必须PASS") is True

    def test_unmeasurable_criterion_detection(self):
        inspector = QAFourDimensionInspector("")
        assert inspector._is_measurable("尽量做得好") is False
        assert inspector._is_measurable("差不多就行") is False


class TestUnambiguityDimension:
    """无歧义性维度测试"""

    def test_clear_doc_passes_unambiguity(self):
        inspector = QAFourDimensionInspector(GOOD_SRS_DOC, "srs")
        result = inspector.inspect()
        assert result.unambiguity.score >= 90
        assert result.unambiguity.passed is True

    def test_vague_doc_fails_unambiguity(self):
        inspector = QAFourDimensionInspector(AMBIGUOUS_SRS_DOC, "srs")
        result = inspector.inspect()
        assert result.unambiguity.passed is False
        assert len(result.unambiguity.defects) >= 1

    def test_vague_terms_detected(self):
        vague_content = "系统可能需要大概尽量适当的处理"
        inspector = QAFourDimensionInspector(vague_content, "srs")
        result = inspector.inspect()
        found_dims = [d.dimension for d in result.unambiguity.defects]
        assert "unambiguity" in found_dims

    def test_unambiguity_defect_severity_is_minor(self):
        vague_content = "这个功能可能差不多就行"
        inspector = QAFourDimensionInspector(vague_content, "srs")
        result = inspector.inspect()
        for defect in result.unambiguity.defects:
            assert defect.severity == "MINOR"


class TestOverallInspection:
    """四维总检验测试"""

    def test_good_doc_passes_all_dimensions(self):
        inspector = QAFourDimensionInspector(GOOD_SRS_DOC, "srs")
        result = inspector.inspect()
        assert result.overall_passed is True
        assert result.completeness.passed is True
        assert result.consistency.passed is True
        assert result.verifiability.passed is True
        assert result.unambiguity.passed is True

    def test_any_fail_makes_overall_fail(self):
        inspector = QAFourDimensionInspector(AMBIGUOUS_SRS_DOC, "srs")
        result = inspector.inspect()
        assert result.overall_passed is False

    def test_total_defects_count(self):
        inspector = QAFourDimensionInspector(AMBIGUOUS_SRS_DOC, "srs")
        result = inspector.inspect()
        expected = (len(result.completeness.defects)
                    + len(result.consistency.defects)
                    + len(result.verifiability.defects)
                    + len(result.unambiguity.defects))
        assert result.total_defects == expected
        assert len(result.all_defects) == expected

    def test_four_dimension_coverage_is_100_percent(self):
        """四维检验完整度100%：四个维度全部有结果"""
        inspector = QAFourDimensionInspector(GOOD_SRS_DOC, "srs")
        result = inspector.inspect()
        assert result.completeness is not None
        assert result.consistency is not None
        assert result.verifiability is not None
        assert result.unambiguity is not None
        assert result.completeness.dimension_key == "completeness"
        assert result.consistency.dimension_key == "consistency"
        assert result.verifiability.dimension_key == "verifiability"
        assert result.unambiguity.dimension_key == "unambiguity"


class TestJSONReport:
    """JSON报告生成测试"""

    def test_report_contains_all_dimensions(self):
        inspector = QAFourDimensionInspector(GOOD_SRS_DOC, "srs")
        result = inspector.inspect()
        report = inspector.to_json_report(result)
        dims = report["dimensions"]
        assert "completeness" in dims
        assert "consistency" in dims
        assert "verifiability" in dims
        assert "unambiguity" in dims

    def test_report_type_label(self):
        inspector = QAFourDimensionInspector(GOOD_SRS_DOC, "srs")
        result = inspector.inspect()
        report = inspector.to_json_report(result)
        assert report["report_type"] == "qa_four_dimension_inspection"

    def test_report_defect_chapters_only_failed(self):
        inspector = QAFourDimensionInspector(INCOMPLETE_SRS_DOC, "srs")
        result = inspector.inspect()
        report = inspector.to_json_report(result)
        keys = [dc["dimension_key"] for dc in report["defect_chapters"]]
        assert "completeness" in keys

    def test_report_defects_are_serializable(self):
        inspector = QAFourDimensionInspector(GOOD_SRS_DOC, "srs")
        result = inspector.inspect()
        report = inspector.to_json_report(result)
        json_str = json.dumps(report)
        assert len(json_str) > 0


class TestDefectTracker:
    """缺陷跟踪器测试"""

    def test_register_and_fix_defects(self):
        tracker = DefectTracker()
        defects = [
            QADefect("DEF-001", "completeness", "MAJOR", "缺少章节", "证据A", "补充章节"),
            QADefect("DEF-002", "unambiguity", "MINOR", "模糊用词", "证据B", "替换用词"),
        ]
        tracker.register_defects(defects)
        assert tracker.get_fix_rate() == 0.0
        assert tracker.all_fixed() is False
        assert len(tracker.get_open_defects()) == 2

    def test_fix_all_defects(self):
        tracker = DefectTracker()
        defects = [
            QADefect("DEF-001", "completeness", "MAJOR", "缺少章节", "证据A", "补充章节"),
        ]
        tracker.register_defects(defects)
        tracker.fix_defect("DEF-001", "已补充非功能需求章节")
        assert tracker.get_fix_rate() == 100.0
        assert tracker.all_fixed() is True
        assert len(tracker.get_open_defects()) == 0

    def test_partial_fix_rate(self):
        tracker = DefectTracker()
        defects = [
            QADefect("DEF-001", "completeness", "MAJOR", "缺少章节A", "evidence", "fix"),
            QADefect("DEF-002", "completeness", "MAJOR", "缺少章节B", "evidence", "fix"),
            QADefect("DEF-003", "unambiguity", "MINOR", "模糊用词", "evidence", "fix"),
        ]
        tracker.register_defects(defects)
        tracker.fix_defect("DEF-001", "已修复A")
        tracker.fix_defect("DEF-002", "已修复B")
        assert tracker.get_fix_rate() == pytest.approx(66.67, abs=0.01)
        assert len(tracker.get_open_defects()) == 1

    def test_empty_tracker_returns_100(self):
        tracker = DefectTracker()
        assert tracker.get_fix_rate() == 100.0
        assert tracker.all_fixed() is True

    def test_fix_nonexistent_defect_ignored(self):
        tracker = DefectTracker()
        tracker.register_defects([QADefect("DEF-001", "completeness", "MAJOR", "d", "e", "f")])
        tracker.fix_defect("DEF-999", "不存在的缺陷")
        assert tracker.get_fix_rate() == 0.0
        assert tracker.all_fixed() is False


class TestEndToEndInspection:
    """端到端检验流程测试"""

    def test_complete_inspection_with_defect_remediation(self):
        """完整流程：检验 → 发现缺陷 → 修复 → 重新检验 → 全部通过"""
        # 第一阶段：有问题的文档
        inspector1 = QAFourDimensionInspector(INCOMPLETE_SRS_DOC, "srs")
        result1 = inspector1.inspect()

        # 验证：至少有一个维度不通过
        assert result1.overall_passed is False
        assert result1.total_defects > 0

        # 跟踪缺陷
        tracker = DefectTracker()
        tracker.register_defects(result1.all_defects)

        # 修复：补充文档内容
        fixed_doc = GOOD_SRS_DOC
        for defect in result1.all_defects:
            tracker.fix_defect(defect.defect_id, f"已在文档中处理：{defect.description}")

        # 修复率验证
        assert tracker.get_fix_rate() == 100.0
        assert tracker.all_fixed() is True

        # 第二阶段：修复后的文档重新检验
        inspector2 = QAFourDimensionInspector(fixed_doc, "srs")
        result2 = inspector2.inspect()

        # 验证：全部通过
        assert result2.overall_passed is True
        assert result2.completeness.passed is True
        assert result2.consistency.passed is True
        assert result2.verifiability.passed is True
        assert result2.unambiguity.passed is True
        assert result2.total_defects == 0

    def test_report_generation_is_valid_json(self):
        """检验报告可以序列化为有效JSON"""
        inspector = QAFourDimensionInspector(GOOD_SRS_DOC, "srs")
        result = inspector.inspect()
        report = inspector.to_json_report(result)

        # 序列化并反序列化
        json_str = json.dumps(report, ensure_ascii=False)
        loaded = json.loads(json_str)

        assert loaded["report_type"] == "qa_four_dimension_inspection"
        assert "dimensions" in loaded
        assert "overall_passed" in loaded
        assert "total_defects" in loaded
