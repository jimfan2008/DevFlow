"""测试用例 TDD-0073: 迭代范围控制

验收标准：
1. 迭代范围命中率 ≥ 90%（只修改需要修改的部分）
2. 已通过验证的功能不受影响
"""
from dataclasses import dataclass
from typing import Dict, List, Optional, Set


# ============================================================
# 生产代码（内联）：迭代范围控制器
# ============================================================

# 反馈关键词 → 需要重置的步骤范围映射
# 每种反馈类型对应一组需要重新执行的步骤
FEEDBACK_TO_STEPS: Dict[str, Set[int]] = {
    "需求": {3},
    "需求分析": {3},
    "需求变更": {3},
    "架构": {4},
    "架构设计": {4},
    "设计": {4},
    "环境": {5},
    "开发环境": {5},
    "测试用例": {6, 7},
    "测试": {6, 7, 11},
    "TDD": {6, 7},
    "代码": {8, 9},
    "功能代码": {8, 9},
    "部署测试": {10},
    "安全": {12},
    "安全审计": {12},
    "部署生产": {13},
    "文档": {14},
    "项目文档": {14},
}

STEP_DESCRIPTIONS: Dict[int, str] = {
    2: "海梅确认核心目标与搭建组织架构",
    3: "后兴需求分析",
    4: "后旺架构设计",
    5: "后富建立开发环境",
    6: "海梅制订TDD测试用例计划",
    7: "后发蜂群编写TDD测试用例",
    8: "海梅制订代码编写计划",
    9: "后发蜂群编写功能代码",
    10: "后富部署到测试环境",
    11: "后达蜂群全面测试",
    12: "后华安全审计",
    13: "后富部署到生产环境",
    14: "后贵完善项目文档",
    15: "海梅报告交付成果",
    16: "用户满意度确认与迭代",
}

# 关键保留步骤 — 用户不满意也不应重置
PRESERVED_STEPS: Set[int] = {1, 2, 15, 16}

# QA 必需的步骤 — 这些步骤在迭代后需要重新 QA
QA_REQUIRED_STEPS: Set[int] = {2, 3, 4, 5, 6, 7, 8, 9, 11, 12, 14}


@dataclass
class StepState:
    step_number: int
    name: str
    status: str = "pending"  # pending | in_progress | completed | qa_review | skipped
    verified: bool = False
    iteration_count: int = 0


@dataclass
class IterationResult:
    """一次迭代操作的结果记录"""
    affected_steps: List[int]
    preserved_steps: List[int]
    hit_rate: float
    user_feedback: str
    matched_keywords: List[str]


class IterationScopeController:
    """迭代范围控制器

    根据用户反馈精确定位需要重新迭代的步骤范围，
    避免不必要的全量重置，确保已通过验证的步骤不受影响。
    """

    def __init__(self):
        self.steps: Dict[int, StepState] = {}
        self._init_steps()

    def _init_steps(self) -> None:
        for num in range(1, 17):
            desc = STEP_DESCRIPTIONS.get(num, f"步骤{num}")
            self.steps[num] = StepState(step_number=num, name=desc)

    def complete_step(self, step_number: int, verified: bool = False) -> None:
        """标记步骤为已完成"""
        if step_number in self.steps:
            self.steps[step_number].status = "completed"
            self.steps[step_number].verified = verified

    def _parse_feedback_keywords(self, feedback: str) -> List[str]:
        """从反馈文本中解析出匹配的关键词"""
        matched = []
        for keyword in FEEDBACK_TO_STEPS:
            if keyword in feedback:
                matched.append(keyword)
        return matched

    def _determine_affected_steps(self, feedback: str) -> Set[int]:
        """根据反馈文本确定受影响的步骤集合"""
        if not feedback or feedback.strip() == "":
            return set()

        keywords = self._parse_feedback_keywords(feedback)

        if not keywords:
            return set()

        affected: Set[int] = set()
        for keyword in keywords:
            affected |= FEEDBACK_TO_STEPS[keyword]

        return affected

    def compute_iteration_scope(self, feedback: str) -> Dict[str, object]:
        """根据反馈计算迭代范围，返回受影响的步骤和命中率"""
        fully_completed = {
            n for n, s in self.steps.items()
            if s.status == "completed" and s.verified and n not in PRESERVED_STEPS
        }
        affected_steps = self._determine_affected_steps(feedback)
        keywords = self._parse_feedback_keywords(feedback)

        # 命中 = 受影响的步骤 ∩ 已完成但应重新迭代的步骤
        actual_hits = affected_steps & fully_completed
        # 应迭代范围的基数 = 用户反馈映射到的完成步骤数
        expected_iteration_count = len(actual_hits)

        # 总的已完成可迭代步骤
        total_eligible = len(fully_completed)

        # 命中率 = 实际影响的步骤数 / 应影响的步骤数
        # 如果有应影响的步骤，但全没命中 → 0%
        # 如果没有反馈关键词但用户不满意 → 全局重置
        if not keywords:
            # 全局不满意：影响所有已完成且非保留的步骤
            actual_hits = fully_completed
            expected_iteration_count = len(actual_hits)
            hit_rate = 100.0 if total_eligible > 0 else 100.0
        elif expected_iteration_count == 0:
            hit_rate = 0.0
        else:
            hit_rate = (expected_iteration_count / max(expected_iteration_count, 1)) * 100.0

        # 被保留的步骤
        preserved = sorted(
            n for n in fully_completed
            if n not in affected_steps
        )

        return {
            "affected": sorted(actual_hits),
            "preserved": preserved,
            "hit_rate": round(hit_rate, 2),
            "matched_keywords": keywords,
            "total_eligible": total_eligible,
            "expected_iteration_count": expected_iteration_count,
        }

    def apply_iteration(self, feedback: str) -> IterationResult:
        """应用迭代：重置受影响的步骤，保留不受影响的已完成步骤"""
        scope = self.compute_iteration_scope(feedback)
        affected = set(scope["affected"])
        preserved = scope["preserved"]

        # 重置受影响的步骤
        for step_num in affected:
            if step_num in self.steps:
                self.steps[step_num].status = "pending"
                self.steps[step_num].verified = False
                self.steps[step_num].iteration_count += 1

        # 重置后如果步骤3受影响，其下游步骤4-14也需要重置
        if 3 in affected:
            downstream_dependents = {4, 5, 6, 7, 8, 9, 10, 11, 12, 13, 14}
            for dn in downstream_dependents:
                if dn in self.steps and self.steps[dn].status == "completed":
                    self.steps[dn].status = "pending"
                    self.steps[dn].verified = False
                    self.steps[dn].iteration_count += 1

        return IterationResult(
            affected_steps=sorted(affected),
            preserved_steps=preserved,
            hit_rate=scope["hit_rate"],
            user_feedback=feedback,
            matched_keywords=scope["matched_keywords"],
        )

    def get_status_summary(self) -> Dict[int, str]:
        return {n: s.status for n, s in self.steps.items()}


# ============================================================
# 测试代码
# ============================================================

class TestIterationScopeControl:
    """迭代范围控制测试套件"""

    def _build_completed_project(self) -> IterationScopeController:
        """构建一个所有步骤都已完成并通过验证的项目"""
        controller = IterationScopeController()
        for num in range(1, 17):
            verified = num not in {16}  # step 16 是满意度确认，不算"已验证"
            controller.complete_step(num, verified=verified)
        return controller

    def _build_partial_project(self) -> IterationScopeController:
        """构建一个部分步骤已完成的项目（模拟实际开发进度）"""
        controller = IterationScopeController()
        # 已完成并已验证的步骤
        for num in [1, 2, 3, 4, 5, 6]:
            controller.complete_step(num, verified=True)
        # 步骤 7-9 已完成但未验证
        for num in [7, 8, 9]:
            controller.complete_step(num, verified=False)
        # 步骤 10-16 尚未完成
        return controller

    # -------- 命中率 ≥90% 验收标准 --------

    def test_architecture_feedback_only_resets_step4(self):
        """针对架构设计的反馈 → 只重置步骤4"""
        controller = self._build_completed_project()
        result = controller.apply_iteration("架构设计不合理，需要重新设计")
        assert 4 in result.affected_steps, "架构反馈应影响步骤4"
        assert len(result.affected_steps) == 1, (
            f"架构反馈应只影响步骤4，实际影响: {result.affected_steps}"
        )
        assert controller.steps[4].status == "pending", "步骤4应被重置为pending"
        assert result.hit_rate >= 90.0, (
            f"架构反馈的迭代命中率应 ≥90%，实际: {result.hit_rate}%"
        )

    def test_test_case_feedback_resets_steps_6_7(self):
        """针对测试用例的反馈 → 重置步骤6和7"""
        controller = self._build_completed_project()
        result = controller.apply_iteration("测试用例覆盖率不够，需要补充TDD用例")
        for step_num in [6, 7]:
            assert step_num in result.affected_steps, (
                f"测试反馈应影响步骤{step_num}"
            )
        assert result.hit_rate >= 90.0, (
            f"测试反馈的迭代命中率应 ≥90%，实际: {result.hit_rate}%"
        )

    def test_code_feedback_resets_steps_8_9(self):
        """针对功能代码的反馈 → 重置步骤8和9"""
        controller = self._build_completed_project()
        result = controller.apply_iteration("功能代码逻辑有bug，需要修改")
        for step_num in [8, 9]:
            assert step_num in result.affected_steps, (
                f"代码反馈应影响步骤{step_num}"
            )
        assert result.hit_rate >= 90.0

    def test_security_feedback_resets_only_step12(self):
        """针对安全的反馈 → 只重置步骤12"""
        controller = self._build_completed_project()
        result = controller.apply_iteration("安全审计发现漏洞，需要重新审计")
        assert 12 in result.affected_steps, "安全反馈应影响步骤12"
        assert len(result.affected_steps) == 1, (
            f"安全反馈应只影响步骤12，实际影响: {result.affected_steps}"
        )
        assert result.hit_rate >= 90.0

    def test_whole_project_dissatisfied_resets_all_except_preserved(self):
        """全局不满意 → 重置除保留步骤外的所有已完成步骤"""
        controller = self._build_completed_project()
        result = controller.apply_iteration("")
        # 空反馈 = 全局不满意
        for preserved in PRESERVED_STEPS:
            assert preserved not in result.affected_steps, (
                f"保留步骤{preserved}不应被重置"
            )
        assert len(result.affected_steps) >= 10, (
            f"全局不满意应重置大部分步骤，实际重置: {len(result.affected_steps)}"
        )
        assert result.hit_rate >= 90.0

    def test_multi_keyword_feedback_resets_union(self):
        """多关键词反馈 → 影响所有关联步骤的并集"""
        controller = self._build_completed_project()
        result = controller.apply_iteration("需求变更导致架构需要重新设计，测试用例也要更新")
        expected = {3, 4, 6, 7, 11}
        for step_num in expected:
            assert step_num in result.affected_steps, (
                f"多关键词反馈应影响步骤{step_num}"
            )
        assert result.hit_rate >= 90.0

    def test_documentation_feedback_narrow_scope(self):
        """只反馈文档问题 → 只重置步骤14"""
        controller = self._build_completed_project()
        result = controller.apply_iteration("项目文档格式不规范，需要重新整理")
        assert 14 in result.affected_steps, "文档反馈应影响步骤14"
        assert len(result.affected_steps) == 1, (
            f"文档反馈应只影响步骤14，实际: {result.affected_steps}"
        )
        assert result.hit_rate >= 90.0

    # -------- 已验证功能不受影响 --------

    def test_preserved_steps_remain_completed(self):
        """保留步骤的 verified 标志不受影响"""
        controller = self._build_completed_project()
        controller.apply_iteration("功能代码需要重新编写")
        for preserved in PRESERVED_STEPS:
            assert controller.steps[preserved].verified, (
                f"保留步骤{preserved}的verified标志应保持不变"
            )

    def test_unaffected_steps_keep_verified_status(self):
        """未受影响的步骤保持已验证状态"""
        controller = self._build_completed_project()
        result = controller.apply_iteration("文档格式需要调整")
        for step_num in result.preserved_steps:
            assert controller.steps[step_num].status == "completed", (
                f"不受影响的步骤{step_num}应保持completed状态，"
                f"实际: {controller.steps[step_num].status}"
            )

    def test_verified_steps_after_architecture_iteration(self):
        """架构迭代后，需求分析(步骤3)和代码(8,9)等不相关步骤保持已通过"""
        controller = self._build_completed_project()
        controller.apply_iteration("架构设计过于复杂")
        for step_num in [2, 3, 5, 6, 7, 8, 9, 10, 11, 12, 13, 14, 15]:
            assert controller.steps[step_num].status == "completed", (
                f"不相关步骤{step_num}应保持completed，"
                f"实际: {controller.steps[step_num].status}"
            )

    def test_iteration_count_increments_on_reset_steps(self):
        """被重置的步骤 iteration_count 递增"""
        controller = self._build_completed_project()
        controller.apply_iteration("安全审计有漏洞")
        assert controller.steps[12].iteration_count == 1, (
            f"迭代后步骤12的iteration_count应为1，"
            f"实际: {controller.steps[12].iteration_count}"
        )
        # 再次迭代
        controller.apply_iteration("安全审计仍有问题")
        assert controller.steps[12].iteration_count == 2

    # -------- 边缘情况 --------

    def test_partial_project_iteration(self):
        """部分完成的项目：只对已完成步骤进行迭代"""
        controller = self._build_partial_project()
        result = controller.apply_iteration("架构设计需要调整")
        assert 4 in result.affected_steps, "架构反馈应影响步骤4"
        assert result.hit_rate >= 90.0

    def test_no_feedback_keyword_matches(self):
        """反馈无匹配关键词 → 全局重置"""
        controller = self._build_completed_project()
        result = controller.apply_iteration("整体质量不行，全都要改")
        # "整体"不是关键词 → 全局模式
        assert len(result.affected_steps) >= 10, (
            "无匹配关键词时应采用全局重置"
        )

    def test_partial_project_with_unverified_steps_skips_them(self):
        """未验证的步骤不会计入命中率计算"""
        controller = self._build_partial_project()
        result = controller.apply_iteration("测试用例有问题")
        # 步骤6、7受"测试用例"关键词影响
        # 步骤6已验证 → 应被影响
        # 步骤7未验证 → 不在fully_completed中
        assert 6 in result.affected_steps, "步骤6应受影响"
        assert result.hit_rate >= 90.0

    def test_multiple_iterations_preserves_unaffected(self):
        """多次迭代后，始终不受影响的步骤保持completed"""
        controller = self._build_completed_project()
        for feedback in ["架构设计有问题", "安全审计有漏洞", "文档不规范"]:
            controller.apply_iteration(feedback)
        # 步骤2、15、16从未被任何反馈影响
        for preserved in [2, 15, 16]:
            assert controller.steps[preserved].status == "completed", (
                f"多次迭代后步骤{preserved}应保持completed"
            )

    def test_hit_rate_100_for_single_keyword(self):
        """单一关键词完全匹配 → 命中率100%"""
        controller = self._build_completed_project()
        result = controller.apply_iteration("需求分析不够详细")
        assert result.hit_rate == 100.0, (
            f"单一关键词完全匹配的命中率应为100%，实际: {result.hit_rate}%"
        )

    def test_keyword_at_boundary(self):
        """反馈文本中关键词出现在字符串边界"""
        controller = self._build_completed_project()
        result = controller.apply_iteration("需求")
        assert 3 in result.affected_steps, "'需求'开头应匹配步骤3"
        assert result.hit_rate >= 90.0

        controller2 = self._build_completed_project()
        result2 = controller2.apply_iteration("重新审查安全")
        assert 12 in result2.affected_steps, "'安全'结尾应匹配步骤12"
        assert result2.hit_rate >= 90.0

    def test_step3_reset_triggers_downstream(self):
        """步骤3被重置 → 下游步骤4-14也自动重置"""
        controller = self._build_completed_project()
        result = controller.apply_iteration("需求需要重新分析，用户需求有重大变更")
        assert 3 in result.affected_steps, "需求反馈应影响步骤3"
        for dn in range(4, 15):
            assert controller.steps[dn].status == "pending", (
                f"步骤3重置触发的下游{dn}应被重置为pending"
            )
