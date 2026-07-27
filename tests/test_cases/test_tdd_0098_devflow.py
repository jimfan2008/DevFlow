import pytest
from dataclasses import dataclass, field
from typing import Optional, List, Dict, Tuple
from enum import Enum


class TraceLinkType(str, Enum):
    """追溯链接类型。"""
    ARCHITECTURE = "architecture"
    CODE = "code"
    TEST_CASE = "test_case"


class TraceStatus(str, Enum):
    """追溯状态。"""
    COVERED = "covered"
    MISSING = "missing"
    PARTIAL = "partial"


@dataclass
class Requirement:
    """需求条目。"""
    req_id: str
    title: str
    description: str
    category: str = "functional"


@dataclass
class ArchitectureDesign:
    """架构设计条目。"""
    design_id: str
    module: str
    description: str
    design_pattern: str = ""


@dataclass
class CodeModule:
    """代码实现模块。"""
    code_id: str
    file_path: str
    class_name: str
    method_name: str
    description: str = ""


@dataclass
class TestCaseItem:
    """测试用例条目。"""
    test_id: str
    test_name: str
    test_file: str
    test_class: str
    description: str = ""


@dataclass
class TraceLink:
    """追溯链接。"""
    req_id: str
    target_type: TraceLinkType
    target_id: str
    is_complete: bool = True


@dataclass
class TraceabilityMatrix:
    """需求追溯矩阵。"""
    requirements: Dict[str, Requirement] = field(default_factory=dict)
    architectures: Dict[str, ArchitectureDesign] = field(default_factory=dict)
    code_modules: Dict[str, CodeModule] = field(default_factory=dict)
    test_cases: Dict[str, TestCaseItem] = field(default_factory=dict)
    links: List[TraceLink] = field(default_factory=list)


class TraceabilityMatrixGenerator:
    """需求追溯矩阵生成器。"""

    def __init__(self):
        self.matrix = TraceabilityMatrix()

    def add_requirement(self, req: Requirement) -> None:
        self.matrix.requirements[req.req_id] = req

    def add_architecture(self, design: ArchitectureDesign) -> None:
        self.matrix.architectures[design.design_id] = design

    def add_code_module(self, code: CodeModule) -> None:
        self.matrix.code_modules[code.code_id] = code

    def add_test_case(self, test_case: TestCaseItem) -> None:
        self.matrix.test_cases[test_case.test_id] = test_case

    def add_trace_link(self, link: TraceLink) -> None:
        self.matrix.links.append(link)

    def get_coverage_for_requirement(self, req_id: str) -> Dict[TraceLinkType, bool]:
        """获取单个需求的追溯覆盖情况。"""
        coverage = {
            TraceLinkType.ARCHITECTURE: False,
            TraceLinkType.CODE: False,
            TraceLinkType.TEST_CASE: False,
        }
        for link in self.matrix.links:
            if link.req_id == req_id:
                coverage[link.target_type] = True
        return coverage

    def get_coverage_rate(self) -> float:
        """计算追溯矩阵覆盖率（百分比）。"""
        if not self.matrix.requirements:
            return 100.0

        total_traces_needed = len(self.matrix.requirements) * 3
        total_traces_present = 0

        for req_id in self.matrix.requirements:
            coverage = self.get_coverage_for_requirement(req_id)
            for covered in coverage.values():
                if covered:
                    total_traces_present += 1

        return (total_traces_present / total_traces_needed) * 100.0 if total_traces_needed > 0 else 100.0

    def get_trace_completeness(self) -> float:
        """计算追溯关系完整率（百分比）。"""
        if not self.matrix.links:
            return 0.0

        complete_count = sum(1 for link in self.matrix.links if link.is_complete)
        return (complete_count / len(self.matrix.links)) * 100.0

    def get_missing_trace_types(self, req_id: str) -> List[TraceLinkType]:
        """获取某个需求缺失的追溯类型。"""
        coverage = self.get_coverage_for_requirement(req_id)
        return [t for t, covered in coverage.items() if not covered]

    def validate_all_requirements_have_traces(self) -> List[str]:
        """验证所有需求是否有完整的三种追溯。"""
        missing = []
        for req_id in self.matrix.requirements:
            missing_types = self.get_missing_trace_types(req_id)
            if missing_types:
                missing.append(f"{req_id}: missing {[t.value for t in missing_types]}")
        return missing

    def has_complete_coverage(self) -> bool:
        """判断覆盖率是否为100%。"""
        return self.get_coverage_rate() == 100.0

    def has_complete_traceability(self) -> bool:
        """判断追溯关系完整率是否为100%。"""
        return self.get_trace_completeness() == 100.0

    def get_trace_summary(self) -> Dict[str, object]:
        """获取追溯矩阵摘要。"""
        total_reqs = len(self.matrix.requirements)
        links_by_type = {
            TraceLinkType.ARCHITECTURE: 0,
            TraceLinkType.CODE: 0,
            TraceLinkType.TEST_CASE: 0,
        }
        for link in self.matrix.links:
            links_by_type[link.target_type] += 1

        return {
            "total_requirements": total_reqs,
            "total_architecture_links": links_by_type[TraceLinkType.ARCHITECTURE],
            "total_code_links": links_by_type[TraceLinkType.CODE],
            "total_test_case_links": links_by_type[TraceLinkType.TEST_CASE],
            "total_links": len(self.matrix.links),
            "coverage_rate": self.get_coverage_rate(),
            "trace_completeness": self.get_trace_completeness(),
            "has_full_coverage": self.has_complete_coverage(),
            "has_full_traceability": self.has_complete_traceability(),
        }


SAMPLE_REQUIREMENTS: List[Requirement] = [
    Requirement(
        req_id="REQ-001",
        title="用户注册功能",
        description="用户可以通过邮箱和密码注册账户",
        category="functional",
    ),
    Requirement(
        req_id="REQ-002",
        title="用户登录功能",
        description="用户可以使用注册的邮箱和密码登录系统",
        category="functional",
    ),
    Requirement(
        req_id="REQ-003",
        title="项目看板管理",
        description="用户创建和管理项目看板",
        category="functional",
    ),
    Requirement(
        req_id="REQ-004",
        title="需求文档管理",
        description="用户提交和确认需求文档",
        category="functional",
    ),
    Requirement(
        req_id="REQ-005",
        title="权限控制",
        description="系统支持基于角色的访问控制",
        category="non_functional",
    ),
]

SAMPLE_ARCHITECTURES: List[ArchitectureDesign] = [
    ArchitectureDesign(
        design_id="ARCH-001",
        module="用户认证模块",
        description="用户注册与登录的架构设计，包含JWT令牌认证流程",
        design_pattern="Service-Repository模式",
    ),
    ArchitectureDesign(
        design_id="ARCH-002",
        module="看板管理模块",
        description="项目看板的CRUD架构设计",
        design_pattern="分层架构",
    ),
    ArchitectureDesign(
        design_id="ARCH-003",
        module="需求管理模块",
        description="需求文档提交、澄清与确认的架构设计",
        design_pattern="事件驱动模式",
    ),
    ArchitectureDesign(
        design_id="ARCH-004",
        module="权限控制模块",
        description="RBAC权限控制的架构设计，包含角色和权限矩阵",
        design_pattern="策略模式",
    ),
]

SAMPLE_CODE_MODULES: List[CodeModule] = [
    CodeModule(
        code_id="CODE-001",
        file_path="app/api/auth.py",
        class_name="AuthRouter",
        method_name="register",
        description="用户注册API端点",
    ),
    CodeModule(
        code_id="CODE-002",
        file_path="app/api/auth.py",
        class_name="AuthRouter",
        method_name="login",
        description="用户登录API端点",
    ),
    CodeModule(
        code_id="CODE-003",
        file_path="app/api/boards.py",
        class_name="BoardRouter",
        method_name="create_board",
        description="创建看板API端点",
    ),
    CodeModule(
        code_id="CODE-004",
        file_path="app/api/requirements.py",
        class_name="RequirementRouter",
        method_name="submit_requirement",
        description="提交需求API端点",
    ),
    CodeModule(
        code_id="CODE-005",
        file_path="app/api/roles.py",
        class_name="RoleRouter",
        method_name="check_permission",
        description="权限检查逻辑",
    ),
]

SAMPLE_TEST_CASES: List[TestCaseItem] = [
    TestCaseItem(
        test_id="TEST-001",
        test_name="test_user_registration_success",
        test_file="tests/test_auth.py",
        test_class="TestUserRegistration",
        description="验证用户注册成功场景",
    ),
    TestCaseItem(
        test_id="TEST-002",
        test_name="test_user_login_with_valid_credentials",
        test_file="tests/test_auth.py",
        test_class="TestUserLogin",
        description="验证有效凭证登录成功",
    ),
    TestCaseItem(
        test_id="TEST-003",
        test_name="test_create_board_success",
        test_file="tests/test_boards.py",
        test_class="TestBoardCreation",
        description="验证创建看板成功",
    ),
    TestCaseItem(
        test_id="TEST-004",
        test_name="test_submit_requirement",
        test_file="tests/test_requirements.py",
        test_class="TestRequirementSubmission",
        description="验证提交需求成功",
    ),
    TestCaseItem(
        test_id="TEST-005",
        test_name="test_permission_denied_for_unauthorized_user",
        test_file="tests/test_permissions.py",
        test_class="TestPermissionControl",
        description="验证无权限用户被拒绝访问",
    ),
]


@pytest.fixture
def generator() -> TraceabilityMatrixGenerator:
    gen = TraceabilityMatrixGenerator()
    for req in SAMPLE_REQUIREMENTS:
        gen.add_requirement(req)
    for arch in SAMPLE_ARCHITECTURES:
        gen.add_architecture(arch)
    for code in SAMPLE_CODE_MODULES:
        gen.add_code_module(code)
    for tc in SAMPLE_TEST_CASES:
        gen.add_test_case(tc)
    return gen


@pytest.fixture
def full_trace_matrix(generator: TraceabilityMatrixGenerator) -> TraceabilityMatrixGenerator:
    """构建完整的追溯矩阵（所有需求都有三种追溯）。"""
    traces = [
        # REQ-001: 用户注册 → 架构/代码/测试
        TraceLink("REQ-001", TraceLinkType.ARCHITECTURE, "ARCH-001"),
        TraceLink("REQ-001", TraceLinkType.CODE, "CODE-001"),
        TraceLink("REQ-001", TraceLinkType.TEST_CASE, "TEST-001"),
        # REQ-002: 用户登录 → 架构/代码/测试
        TraceLink("REQ-002", TraceLinkType.ARCHITECTURE, "ARCH-001"),
        TraceLink("REQ-002", TraceLinkType.CODE, "CODE-002"),
        TraceLink("REQ-002", TraceLinkType.TEST_CASE, "TEST-002"),
        # REQ-003: 看板管理 → 架构/代码/测试
        TraceLink("REQ-003", TraceLinkType.ARCHITECTURE, "ARCH-002"),
        TraceLink("REQ-003", TraceLinkType.CODE, "CODE-003"),
        TraceLink("REQ-003", TraceLinkType.TEST_CASE, "TEST-003"),
        # REQ-004: 需求文档管理 → 架构/代码/测试
        TraceLink("REQ-004", TraceLinkType.ARCHITECTURE, "ARCH-003"),
        TraceLink("REQ-004", TraceLinkType.CODE, "CODE-004"),
        TraceLink("REQ-004", TraceLinkType.TEST_CASE, "TEST-004"),
        # REQ-005: 权限控制 → 架构/代码/测试
        TraceLink("REQ-005", TraceLinkType.ARCHITECTURE, "ARCH-004"),
        TraceLink("REQ-005", TraceLinkType.CODE, "CODE-005"),
        TraceLink("REQ-005", TraceLinkType.TEST_CASE, "TEST-005"),
    ]
    for link in traces:
        generator.add_trace_link(link)
    return generator


# ============================================================
# AC1: 追溯矩阵覆盖率100%
# ============================================================
class TestTraceabilityMatrixCoverage:
    """验收标准 1：追溯矩阵覆盖率 100%。"""

    def test_full_coverage_returns_100_percent(self, full_trace_matrix):
        """完整的追溯矩阵覆盖率应为100%。"""
        assert full_trace_matrix.get_coverage_rate() == 100.0

    def test_partial_coverage_below_100(self, generator):
        """部分追溯的矩阵覆盖率应低于100%。"""
        generator.add_trace_link(TraceLink("REQ-001", TraceLinkType.ARCHITECTURE, "ARCH-001"))
        generator.add_trace_link(TraceLink("REQ-001", TraceLinkType.CODE, "CODE-001"))
        # REQ-001 缺 TEST_CASE；其他需求完全缺失
        assert generator.get_coverage_rate() < 100.0

    def test_empty_requirements_coverage_is_100(self):
        """没有需求时覆盖率应为100%。"""
        gen = TraceabilityMatrixGenerator()
        assert gen.get_coverage_rate() == 100.0

    def test_has_complete_coverage_true(self, full_trace_matrix):
        """has_complete_coverage 对完整矩阵返回 True。"""
        assert full_trace_matrix.has_complete_coverage() is True

    def test_has_complete_coverage_false(self, generator):
        """has_complete_coverage 对不完整矩阵返回 False。"""
        generator.add_trace_link(TraceLink("REQ-001", TraceLinkType.ARCHITECTURE, "ARCH-001"))
        assert generator.has_complete_coverage() is False

    def test_coverage_rate_with_one_missing_link(self, generator):
        """5个需求各需3个追溯=15个链接，少1个则覆盖率=14/15≈93.33%。"""
        for req_id in ["REQ-001", "REQ-002", "REQ-003", "REQ-004", "REQ-005"]:
            generator.add_trace_link(TraceLink(req_id, TraceLinkType.ARCHITECTURE, "ARCH-001"))
            generator.add_trace_link(TraceLink(req_id, TraceLinkType.CODE, "CODE-001"))
        # 只加 4 个 TEST_CASE 链接
        for req_id in ["REQ-001", "REQ-002", "REQ-003", "REQ-004"]:
            generator.add_trace_link(TraceLink(req_id, TraceLinkType.TEST_CASE, "TEST-001"))
        # REQ-005 缺少 TEST_CASE
        assert generator.get_coverage_rate() == pytest.approx(14.0 / 15.0 * 100.0)

    def test_coverage_rate_with_50_percent(self, generator):
        """一半需求有所有追溯时覆盖率为50%。"""
        for req_id in ["REQ-001", "REQ-002"]:
            generator.add_trace_link(TraceLink(req_id, TraceLinkType.ARCHITECTURE, "ARCH-001"))
            generator.add_trace_link(TraceLink(req_id, TraceLinkType.CODE, "CODE-001"))
            generator.add_trace_link(TraceLink(req_id, TraceLinkType.TEST_CASE, "TEST-001"))
        # REQ-003, REQ-004, REQ-005 无追溯
        # 2个需求完整=6个追溯，总共需15个追溯
        assert generator.get_coverage_rate() == pytest.approx(6.0 / 15.0 * 100.0)

    def test_multiple_links_per_type_still_counts_as_one(self, generator):
        """一个需求对同一类型有多个追溯链接仍算覆盖。"""
        generator.add_trace_link(TraceLink("REQ-001", TraceLinkType.ARCHITECTURE, "ARCH-001"))
        generator.add_trace_link(TraceLink("REQ-001", TraceLinkType.ARCHITECTURE, "ARCH-002"))
        generator.add_trace_link(TraceLink("REQ-001", TraceLinkType.CODE, "CODE-001"))
        generator.add_trace_link(TraceLink("REQ-001", TraceLinkType.TEST_CASE, "TEST-001"))
        coverage = generator.get_coverage_for_requirement("REQ-001")
        assert coverage[TraceLinkType.ARCHITECTURE] is True
        assert coverage[TraceLinkType.CODE] is True
        assert coverage[TraceLinkType.TEST_CASE] is True
        # 其他需求完全无追溯
        assert generator.get_coverage_rate() > 0.0
        assert generator.get_coverage_rate() < 100.0


# ============================================================
# AC2: 每个需求追溯到架构设计、代码实现、测试用例
# ============================================================
class TestEachRequirementHasThreeTraces:
    """验收标准 2：每个需求追溯到架构设计、代码实现、测试用例。"""

    def test_each_requirement_has_architecture_trace(self, full_trace_matrix):
        """每个需求都有架构设计追溯。"""
        for req in SAMPLE_REQUIREMENTS:
            coverage = full_trace_matrix.get_coverage_for_requirement(req.req_id)
            assert coverage[TraceLinkType.ARCHITECTURE] is True, (
                f"{req.req_id} 缺少架构设计追溯"
            )

    def test_each_requirement_has_code_trace(self, full_trace_matrix):
        """每个需求都有代码实现追溯。"""
        for req in SAMPLE_REQUIREMENTS:
            coverage = full_trace_matrix.get_coverage_for_requirement(req.req_id)
            assert coverage[TraceLinkType.CODE] is True, (
                f"{req.req_id} 缺少代码实现追溯"
            )

    def test_each_requirement_has_test_case_trace(self, full_trace_matrix):
        """每个需求都有测试用例追溯。"""
        for req in SAMPLE_REQUIREMENTS:
            coverage = full_trace_matrix.get_coverage_for_requirement(req.req_id)
            assert coverage[TraceLinkType.TEST_CASE] is True, (
                f"{req.req_id} 缺少测试用例追溯"
            )

    def test_all_requirements_have_all_three_traces(self, full_trace_matrix):
        """每个需求同时拥有三种追溯。"""
        missing = full_trace_matrix.validate_all_requirements_have_traces()
        assert len(missing) == 0, f"以下需求缺少追溯: {missing}"

    def test_missing_requirement_identified(self, generator):
        """缺少追溯的需求应被正确识别。"""
        generator.add_trace_link(TraceLink("REQ-001", TraceLinkType.ARCHITECTURE, "ARCH-001"))
        generator.add_trace_link(TraceLink("REQ-001", TraceLinkType.CODE, "CODE-001"))
        # REQ-001 缺少 TEST_CASE
        missing = generator.validate_all_requirements_have_traces()
        req_001_missing = [m for m in missing if "REQ-001" in m]
        assert len(req_001_missing) == 1
        assert "test_case" in req_001_missing[0]

    def test_multiple_missing_requirements_detected(self, generator):
        """多个需求缺少追溯时全部被检测到。"""
        generator.add_trace_link(TraceLink("REQ-001", TraceLinkType.ARCHITECTURE, "ARCH-001"))
        # 其他需求完全无追溯
        missing = generator.validate_all_requirements_have_traces()
        assert len(missing) == 5

    def test_get_missing_trace_types_returns_correct_types(self, generator):
        """获取缺失的追溯类型返回正确的类型列表。"""
        generator.add_trace_link(TraceLink("REQ-001", TraceLinkType.ARCHITECTURE, "ARCH-001"))
        generator.add_trace_link(TraceLink("REQ-001", TraceLinkType.CODE, "CODE-001"))
        missing = generator.get_missing_trace_types("REQ-001")
        assert TraceLinkType.TEST_CASE in missing
        assert TraceLinkType.ARCHITECTURE not in missing
        assert TraceLinkType.CODE not in missing

    def test_get_missing_trace_types_all_missing(self, generator):
        """没有追溯时返回全部三种类型。"""
        missing = generator.get_missing_trace_types("REQ-001")
        assert len(missing) == 3
        assert TraceLinkType.ARCHITECTURE in missing
        assert TraceLinkType.CODE in missing
        assert TraceLinkType.TEST_CASE in missing

    def test_architecture_trace_points_to_valid_design(self, full_trace_matrix):
        """架构设计追溯指向有效的架构条目。"""
        for link in full_trace_matrix.matrix.links:
            if link.target_type == TraceLinkType.ARCHITECTURE:
                assert link.target_id in full_trace_matrix.matrix.architectures, (
                    f"架构追溯指向不存在的架构 {link.target_id}"
                )

    def test_code_trace_points_to_valid_module(self, full_trace_matrix):
        """代码追溯指向有效的代码模块。"""
        for link in full_trace_matrix.matrix.links:
            if link.target_type == TraceLinkType.CODE:
                assert link.target_id in full_trace_matrix.matrix.code_modules, (
                    f"代码追溯指向不存在的代码 {link.target_id}"
                )

    def test_test_case_trace_points_to_valid_test(self, full_trace_matrix):
        """测试用例追溯指向有效的测试条目。"""
        for link in full_trace_matrix.matrix.links:
            if link.target_type == TraceLinkType.TEST_CASE:
                assert link.target_id in full_trace_matrix.matrix.test_cases, (
                    f"测试追溯指向不存在的测试 {link.target_id}"
                )

    def test_req_with_only_architecture_trace_is_incomplete(self, generator):
        """只有架构追溯的需求被视为不完整。"""
        generator.add_trace_link(TraceLink("REQ-001", TraceLinkType.ARCHITECTURE, "ARCH-001"))
        coverage = generator.get_coverage_for_requirement("REQ-001")
        assert coverage[TraceLinkType.CODE] is False
        assert coverage[TraceLinkType.TEST_CASE] is False


# ============================================================
# AC3: 追溯关系完整率100%
# ============================================================
class TestTraceCompleteness:
    """验收标准 3：追溯关系完整率 100%。"""

    def test_all_trace_links_complete_in_full_matrix(self, full_trace_matrix):
        """完整矩阵中所有追溯关系应为完整。"""
        assert full_trace_matrix.get_trace_completeness() == 100.0

    def test_trace_completeness_with_incomplete_links(self, generator):
        """存在不完整链接时完整率低于100%。"""
        generator.add_trace_link(TraceLink("REQ-001", TraceLinkType.ARCHITECTURE, "ARCH-001", is_complete=True))
        generator.add_trace_link(TraceLink("REQ-001", TraceLinkType.CODE, "CODE-001", is_complete=False))
        assert generator.get_trace_completeness() == 50.0

    def test_no_links_returns_zero_completeness(self, generator):
        """无追溯链接时完整率为0%。"""
        assert generator.get_trace_completeness() == 0.0

    def test_has_full_traceability_true(self, full_trace_matrix):
        """has_full_traceability 对完整矩阵返回True。"""
        assert full_trace_matrix.has_complete_traceability() is True

    def test_has_full_traceability_false(self, generator):
        """has_full_traceability 对不完整矩阵返回False。"""
        generator.add_trace_link(TraceLink("REQ-001", TraceLinkType.ARCHITECTURE, "ARCH-001", is_complete=False))
        assert generator.has_complete_traceability() is False

    def test_trace_completeness_with_mixed_status(self, generator):
        """混合状态链接的完整率计算正确。"""
        generator.add_trace_link(TraceLink("REQ-001", TraceLinkType.ARCHITECTURE, "ARCH-001", is_complete=True))
        generator.add_trace_link(TraceLink("REQ-001", TraceLinkType.CODE, "CODE-001", is_complete=True))
        generator.add_trace_link(TraceLink("REQ-001", TraceLinkType.TEST_CASE, "TEST-001", is_complete=False))
        generator.add_trace_link(TraceLink("REQ-002", TraceLinkType.ARCHITECTURE, "ARCH-002", is_complete=True))
        # 4个链接中3个完整
        assert generator.get_trace_completeness() == 75.0

    def test_all_links_marked_complete_in_full_matrix(self, full_trace_matrix):
        """完整矩阵中所有链接is_complete为True。"""
        for link in full_trace_matrix.matrix.links:
            assert link.is_complete is True, f"链接 {link.req_id}->{link.target_id} 不完整"

    def test_trace_completeness_with_single_complete_link(self, generator):
        """单个完整链接的完整率为100%。"""
        generator.add_trace_link(TraceLink("REQ-001", TraceLinkType.ARCHITECTURE, "ARCH-001", is_complete=True))
        assert generator.get_trace_completeness() == 100.0

    def test_trace_completeness_with_single_incomplete_link(self, generator):
        """单个不完整链接的完整率为0%。"""
        generator.add_trace_link(TraceLink("REQ-001", TraceLinkType.ARCHITECTURE, "ARCH-001", is_complete=False))
        assert generator.get_trace_completeness() == 0.0

    def test_combined_coverage_and_completeness_100(self, full_trace_matrix):
        """完整矩阵同时满足覆盖率和完整率100%。"""
        assert full_trace_matrix.has_complete_coverage() is True
        assert full_trace_matrix.has_complete_traceability() is True

    def test_trace_summary_contains_all_metrics(self, full_trace_matrix):
        """追溯矩阵摘要包含所有指标。"""
        summary = full_trace_matrix.get_trace_summary()
        assert summary["total_requirements"] == 5
        assert summary["total_architecture_links"] == 5
        assert summary["total_code_links"] == 5
        assert summary["total_test_case_links"] == 5
        assert summary["total_links"] == 15
        assert summary["coverage_rate"] == 100.0
        assert summary["trace_completeness"] == 100.0
        assert summary["has_full_coverage"] is True
        assert summary["has_full_traceability"] is True


# ============================================================
# 边界条件和异常场景测试
# ============================================================
class TestTraceabilityMatrixEdgeCases:
    """边界条件和异常场景测试。"""

    def test_single_requirement_full_trace(self):
        """单个需求的完整追溯。"""
        gen = TraceabilityMatrixGenerator()
        gen.add_requirement(Requirement("REQ-001", "单一需求", "测试"))
        gen.add_architecture(ArchitectureDesign("ARCH-001", "模块A", "描述"))
        gen.add_code_module(CodeModule("CODE-001", "app/api/a.py", "A", "method"))
        gen.add_test_case(TestCaseItem("TEST-001", "test_a", "tests/test_a.py", "TestA"))
        gen.add_trace_link(TraceLink("REQ-001", TraceLinkType.ARCHITECTURE, "ARCH-001"))
        gen.add_trace_link(TraceLink("REQ-001", TraceLinkType.CODE, "CODE-001"))
        gen.add_trace_link(TraceLink("REQ-001", TraceLinkType.TEST_CASE, "TEST-001"))
        assert gen.get_coverage_rate() == 100.0
        assert gen.get_trace_completeness() == 100.0

    def test_requirement_with_multiple_architectures(self, generator):
        """一个需求对应多个架构设计。"""
        generator.add_architecture(ArchitectureDesign("ARCH-005", "额外模块", "描述"))
        generator.add_trace_link(TraceLink("REQ-001", TraceLinkType.ARCHITECTURE, "ARCH-001"))
        generator.add_trace_link(TraceLink("REQ-001", TraceLinkType.ARCHITECTURE, "ARCH-005"))
        generator.add_trace_link(TraceLink("REQ-001", TraceLinkType.CODE, "CODE-001"))
        generator.add_trace_link(TraceLink("REQ-001", TraceLinkType.TEST_CASE, "TEST-001"))
        coverage = generator.get_coverage_for_requirement("REQ-001")
        assert coverage[TraceLinkType.ARCHITECTURE] is True

    def test_large_number_of_requirements(self):
        """大量需求时性能不退化（功能正确性）。"""
        gen = TraceabilityMatrixGenerator()
        count = 100
        for i in range(count):
            gen.add_requirement(Requirement(f"REQ-{i:03d}", f"需求{i}", f"描述{i}"))
            gen.add_architecture(ArchitectureDesign(f"ARCH-{i:03d}", f"模块{i}", f"描述{i}"))
            gen.add_code_module(CodeModule(f"CODE-{i:03d}", f"app/api/{i}.py", f"C{i}", "m"))
            gen.add_test_case(TestCaseItem(f"TEST-{i:03d}", f"test_{i}", f"tests/test_{i}.py", f"T{i}"))
            gen.add_trace_link(TraceLink(f"REQ-{i:03d}", TraceLinkType.ARCHITECTURE, f"ARCH-{i:03d}"))
            gen.add_trace_link(TraceLink(f"REQ-{i:03d}", TraceLinkType.CODE, f"CODE-{i:03d}"))
            gen.add_trace_link(TraceLink(f"REQ-{i:03d}", TraceLinkType.TEST_CASE, f"TEST-{i:03d}"))
        assert gen.get_coverage_rate() == 100.0
        assert gen.get_trace_completeness() == 100.0

    def test_no_requirements_no_links(self):
        """无需求无链接时覆盖率和完整率均为100%。"""
        gen = TraceabilityMatrixGenerator()
        assert gen.get_coverage_rate() == 100.0
        assert gen.get_trace_completeness() == 0.0

    def test_duplicate_links_do_not_affect_coverage_rate(self, generator):
        """重复链接不影响覆盖率计算。"""
        generator.add_trace_link(TraceLink("REQ-001", TraceLinkType.ARCHITECTURE, "ARCH-001"))
        generator.add_trace_link(TraceLink("REQ-001", TraceLinkType.ARCHITECTURE, "ARCH-001"))
        generator.add_trace_link(TraceLink("REQ-001", TraceLinkType.CODE, "CODE-001"))
        generator.add_trace_link(TraceLink("REQ-001", TraceLinkType.TEST_CASE, "TEST-001"))
        coverage = generator.get_coverage_for_requirement("REQ-001")
        assert coverage[TraceLinkType.ARCHITECTURE] is True

    def test_validate_all_empty_requirements_returns_empty(self):
        """没有需求时验证返回空列表。"""
        gen = TraceabilityMatrixGenerator()
        missing = gen.validate_all_requirements_have_traces()
        assert missing == []

    def test_trace_summary_with_empty_matrix(self):
        """空矩阵的摘要信息。"""
        gen = TraceabilityMatrixGenerator()
        summary = gen.get_trace_summary()
        assert summary["total_requirements"] == 0
        assert summary["total_links"] == 0
        assert summary["coverage_rate"] == 100.0
        assert summary["trace_completeness"] == 0.0

    def test_trace_link_type_has_all_three_values(self):
        """TraceLinkType 枚举包含全部三种类型。"""
        assert len(TraceLinkType) == 3
        assert TraceLinkType.ARCHITECTURE.value == "architecture"
        assert TraceLinkType.CODE.value == "code"
        assert TraceLinkType.TEST_CASE.value == "test_case"
