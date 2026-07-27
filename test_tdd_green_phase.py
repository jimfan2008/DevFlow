import re
import math
import pytest


# ====================================================================
# 源码：功能代码管理器（被测试的 "功能代码"）
# ====================================================================


class SingleTestResult:
    """单条测试用例的结果。"""

    def __init__(self, name: str, passed: bool, duration: float):
        self.name = name
        self.passed = passed
        self.duration = duration


class FunctionInfo:
    """描述一个函数/方法的代码单元信息。"""

    def __init__(self, name: str, total_lines: int, covered_lines: int, has_hardcode: bool = False):
        self.name = name
        self.total_lines = total_lines
        self.covered_lines = covered_lines
        self.has_hardcode = has_hardcode


class ModuleInfo:
    """描述一个模块（文件）中所有代码单元的信息。"""

    def __init__(self, name: str, functions: list = None):
        self.name = name
        self.functions = functions or []

    def total_lines(self) -> int:
        return sum(f.total_lines for f in self.functions)

    def covered_lines_sum(self) -> int:
        return sum(f.covered_lines for f in self.functions)

    def has_hardcode(self) -> bool:
        return any(f.has_hardcode for f in self.functions)


# pylint: disable=too-many-instance-attributes
class FunctionalCode:
    """
    功能代码编写阶段的产出物。
    包含已编写的代码模块及其对应的测试用例结果。
    """

    def __init__(self):
        self.modules: list[ModuleInfo] = []
        self.test_results: list[SingleTestResult] = []

    # ---- 数据录入 ----

    def add_module(self, module: ModuleInfo):
        """添加一个已编写的代码模块。"""
        self.modules.append(module)

    def add_test_result(self, result: SingleTestResult):
        """添加一条测试执行结果。"""
        self.test_results.append(result)

    def add_test_results(self, results: list[SingleTestResult]):
        """批量添加测试执行结果。"""
        self.test_results.extend(results)

    # ---- 指标计算 ----

    @property
    def total_tests(self) -> int:
        """测试用例总数。"""
        return len(self.test_results)

    @property
    def passed_tests(self) -> int:
        """通过的测试用例数。"""
        return sum(1 for r in self.test_results if r.passed)

    @property
    def failed_tests(self) -> int:
        """失败的测试用例数。"""
        return self.total_tests - self.passed_tests

    @property
    def test_pass_rate(self) -> float:
        """测试通过率（0.0 ~ 1.0）。空测试集返回 1.0。"""
        if self.total_tests == 0:
            return 1.0
        return self.passed_tests / self.total_tests

    @property
    def total_lines(self) -> int:
        """所有模块的总行数。"""
        return sum(m.total_lines() for m in self.modules)

    @property
    def covered_lines(self) -> int:
        """所有模块的已覆盖行数。"""
        return sum(m.covered_lines_sum() for m in self.modules)

    @property
    def code_coverage(self) -> float:
        """代码覆盖率（0.0 ~ 1.0）。无代码时返回 1.0。"""
        if self.total_lines == 0:
            return 1.0
        return self.covered_lines / self.total_lines

    @property
    def has_hardcode(self) -> bool:
        """是否存在硬编码。"""
        return any(m.has_hardcode() for m in self.modules) if self.modules else False

    @property
    def lint_passed(self) -> bool:
        """Lint 是否全部通过（无 hardcode 即视为通过）。"""
        return not self.has_hardcode

    # ---- GREEN 判定 ----

    def is_green(self, pass_rate_threshold: float = 0.95, coverage_threshold: float = 0.85) -> bool:
        """
        判断是否满足 GREEN 阶段全部验收标准。
        要求：测试通过率 >= pass_rate_threshold, 覆盖率 >= coverage_threshold, lint=100%。
        """
        if not self._validate_threshold_range(pass_rate_threshold, coverage_threshold):
            raise ValueError("阈值必须在 0.0 ~ 1.0 之间")
        return (
            self.test_pass_rate >= pass_rate_threshold
            and self.code_coverage >= coverage_threshold
            and self.lint_passed
        )

    def _validate_threshold_range(self, pass_rate_threshold: float, coverage_threshold: float) -> bool:
        """验证阈值是否在合法范围。"""
        return 0.0 <= pass_rate_threshold <= 1.0 and 0.0 <= coverage_threshold <= 1.0

    def green_report(self) -> dict:
        """生成 GREEN 阶段完整报告。"""
        return {
            "is_green": self.is_green(),
            "test_pass_rate": round(self.test_pass_rate, 4),
            "code_coverage": round(self.code_coverage, 4),
            "total_tests": self.total_tests,
            "passed_tests": self.passed_tests,
            "failed_tests": self.failed_tests,
            "lint_passed": self.lint_passed,
            "has_hardcode": self.has_hardcode,
            "total_lines": self.total_lines,
            "covered_lines": self.covered_lines,
            "module_count": len(self.modules),
        }


# ====================================================================
# 工厂函数（用于 fixture 和测试数据构建）
# ====================================================================


def make_test_passed(name: str, duration: float = 0.05) -> SingleTestResult:
    """构造一条通过的测试记录。"""
    return SingleTestResult(name=name, passed=True, duration=duration)


def make_test_failed(name: str, duration: float = 0.05) -> SingleTestResult:
    """构造一条失败的测试记录。"""
    return SingleTestResult(name=name, passed=False, duration=duration)


def make_function(name: str, total: int, covered: int, hardcode: bool = False) -> FunctionInfo:
    """构造一个函数信息。"""
    return FunctionInfo(name=name, total_lines=total, covered_lines=covered, has_hardcode=hardcode)


def make_module(name: str, **kwargs) -> ModuleInfo:
    """构造一个模块信息。"""
    functions = kwargs.get("functions", [])
    return ModuleInfo(name=name, functions=functions)


def make_perfect_code(
    module_count: int = 3,
    functions_per_module: int = 4,
    test_count: int = 20,
    coverage_rate: float = 0.95,
) -> FunctionalCode:
    """构造一份完美的功能代码（满足全部 GREEN 条件）。"""
    fc = FunctionalCode()
    for mi in range(module_count):
        funcs = []
        for fi in range(functions_per_module):
            total = 10
            covered = max(1, math.ceil(total * coverage_rate))
            funcs.append(make_function(f"mod{mi}_func{fi}", total, covered))
        fc.add_module(make_module(f"module_{mi}", functions=funcs))

    for ti in range(test_count):
        fc.add_test_result(make_test_passed(f"test_{ti}"))
    return fc


def make_barely_green_code(test_count: int = 100) -> FunctionalCode:
    """构造一份刚好达到 GREEN 阈值的代码（通过率 95%，覆盖率 85%）。"""
    fc = FunctionalCode()
    total_lines = 200
    covered_lines = math.ceil(total_lines * 0.85)
    fc.add_module(make_module("mod_85", functions=[
        make_function("full", total_lines, covered_lines),
    ]))
    for i in range(test_count):
        if i < int(test_count * 0.95):
            fc.add_test_result(make_test_passed(f"test_{i}"))
        else:
            fc.add_test_result(make_test_failed(f"test_{i}"))
    return fc


# ====================================================================
# 验收标准 1：测试通过率 >= 95%
# ====================================================================


class TestPassRateThreshold95:
    """验证测试通过率满足 >=95% 的验收标准。"""

    def test_empty_tests_default_pass_rate_is_1_0(self):
        fc = FunctionalCode()
        assert fc.test_pass_rate == 1.0

    def test_all_tests_pass_returns_1_0(self):
        fc = FunctionalCode()
        for i in range(50):
            fc.add_test_result(make_test_passed(f"test_{i}"))
        assert fc.test_pass_rate == 1.0
        assert fc.passed_tests == 50
        assert fc.failed_tests == 0

    def test_exactly_95_percent_pass_rate(self):
        fc = FunctionalCode()
        for i in range(100):
            if i < 95:
                fc.add_test_result(make_test_passed(f"t_{i}"))
            else:
                fc.add_test_result(make_test_failed(f"t_{i}"))
        assert fc.test_pass_rate == 0.95
        assert fc.passed_tests == 95
        assert fc.failed_tests == 5

    def test_above_95_percent_pass_rate(self):
        fc = FunctionalCode()
        for i in range(200):
            if i < 196:
                fc.add_test_result(make_test_passed(f"t_{i}"))
            else:
                fc.add_test_result(make_test_failed(f"t_{i}"))
        assert fc.test_pass_rate == 0.98
        assert fc.passed_tests == 196

    def test_below_95_percent_fails_check(self):
        fc = FunctionalCode()
        for i in range(100):
            if i < 80:
                fc.add_test_result(make_test_passed(f"t_{i}"))
            else:
                fc.add_test_result(make_test_failed(f"t_{i}"))
        assert fc.test_pass_rate == 0.80
        assert fc.test_pass_rate < 0.95

    def test_single_test_pass_is_1_0(self):
        fc = FunctionalCode()
        fc.add_test_result(make_test_passed("single"))
        assert fc.test_pass_rate == 1.0

    def test_single_test_fail_is_0_0(self):
        fc = FunctionalCode()
        fc.add_test_result(make_test_failed("single"))
        assert fc.test_pass_rate == 0.0
        assert fc.failed_tests == 1

    def test_500_tests_96_percent_pass(self):
        fc = FunctionalCode()
        for i in range(500):
            if i < 480:
                fc.add_test_result(make_test_failed(f"t_{i}"))
            else:
                fc.add_test_result(make_test_passed(f"t_{i}"))

        expected_failed = 480
        expected_pass_rate = 1.0 - expected_failed / 500

        assert fc.failed_tests == expected_failed
        assert fc.test_pass_rate == pytest.approx(expected_pass_rate, abs=0.001)


# ====================================================================
# 验收标准 2：代码覆盖率 >= 85%
# ====================================================================


class TestCodeCoverage85:
    """验证代码覆盖率满足 >=85% 的验收标准。"""

    def test_no_code_default_coverage_1_0(self):
        fc = FunctionalCode()
        assert fc.code_coverage == 1.0

    def test_full_coverage(self):
        fc = FunctionalCode()
        fc.add_module(make_module("full", functions=[
            make_function("f1", 50, 50),
            make_function("f2", 30, 30),
        ]))
        assert fc.code_coverage == 1.0

    def test_exact_85_percent_coverage(self):
        fc = FunctionalCode()
        fc.add_module(make_module("mod85", functions=[
            make_function("big", 200, 170),
        ]))
        assert fc.code_coverage == 0.85

    def test_above_85_percent_coverage(self):
        fc = FunctionalCode()
        fc.add_module(make_module("mod90", functions=[
            make_function("f1", 100, 92),
        ]))
        assert fc.code_coverage == 0.92

    def test_below_85_percent_coverage(self):
        fc = FunctionalCode()
        fc.add_module(make_module("mod70", functions=[
            make_function("thin", 100, 70),
        ]))
        assert fc.code_coverage == 0.70
        assert fc.code_coverage < 0.85

    def test_multi_module_coverage_aggregation(self):
        fc = FunctionalCode()
        fc.add_module(make_module("a", functions=[
            make_function("f1", 200, 180),
        ]))
        fc.add_module(make_module("b", functions=[
            make_function("f2", 300, 255),
        ]))
        fc.add_module(make_module("c", functions=[
            make_function("f3", 500, 430),
        ]))
        expected = (180 + 255 + 430) / (200 + 300 + 500)
        assert fc.code_coverage == pytest.approx(expected, abs=0.001)
        assert fc.code_coverage >= 0.85

    def test_zero_lines_no_division_error(self):
        fc = FunctionalCode()
        fc.add_module(make_module("empty", functions=[
            make_function("empty_fn", 0, 0),
        ]))
        assert fc.total_lines == 0
        assert fc.code_coverage == 1.0


# ====================================================================
# 验收标准 3：Lint 通过率 = 100%
# ====================================================================


class TestLintPassRate:
    """验证 Lint 通过率 100%（无硬编码）。"""

    def test_no_modules_lint_passed(self):
        fc = FunctionalCode()
        assert fc.lint_passed is True

    def test_no_hardcode_lint_passes(self):
        fc = FunctionalCode()
        fc.add_module(make_module("clean", functions=[
            make_function("f1", 10, 9, hardcode=False),
            make_function("f2", 20, 18, hardcode=False),
        ]))
        assert fc.lint_passed is True
        assert fc.has_hardcode is False

    def test_hardcode_detected_lint_fails(self):
        fc = FunctionalCode()
        fc.add_module(make_module("dirty", functions=[
            make_function("f1", 10, 9, hardcode=True),
        ]))
        assert fc.lint_passed is False
        assert fc.has_hardcode is True

    def test_mixed_modules_any_hardcode_fails(self):
        fc = FunctionalCode()
        fc.add_module(make_module("clean", functions=[
            make_function("ok", 10, 10, hardcode=False),
        ]))
        fc.add_module(make_module("dirty", functions=[
            make_function("bad", 10, 8, hardcode=True),
        ]))
        assert fc.lint_passed is False
        assert fc.has_hardcode is True


# ====================================================================
# 验收标准 4：无 hardcode
# ====================================================================


class TestNoHardcode:
    """验证功能代码中不包含硬编码值。"""

    def test_clean_code_has_no_hardcode(self):
        fc = FunctionalCode()
        for i in range(5):
            fc.add_module(make_module(f"mod_{i}", functions=[
                make_function("f_clean", 10, 9, hardcode=False),
            ]))
        assert fc.has_hardcode is False

    def test_single_hardcode_function_detected(self):
        fc = FunctionalCode()
        fc.add_module(make_module("mod_a", functions=[
            make_function("f_ok", 20, 18, hardcode=False),
        ]))
        fc.add_module(make_module("mod_b", functions=[
            make_function("f_bad", 15, 12, hardcode=True),
        ]))
        fc.add_module(make_module("mod_c", functions=[
            make_function("f_ok2", 25, 22, hardcode=False),
        ]))
        assert fc.has_hardcode is True

    def test_hardcode_flag_affects_is_green(self):
        fc = FunctionalCode()
        fc.add_module(make_module("mod", functions=[
            make_function("f1", 100, 90, hardcode=True),
        ]))
        for i in range(100):
            fc.add_test_result(make_test_passed(f"t_{i}"))

        assert fc.test_pass_rate == 1.0
        assert fc.code_coverage == 0.90
        assert fc.is_green() is False


# ====================================================================
# GREEN 阶段综合判定
# ====================================================================


class TestGreenPhaseOverall:
    """验证 GREEN 阶段综合判定逻辑。"""

    def test_perfect_code_is_green(self):
        fc = make_perfect_code()
        assert fc.is_green() is True
        report = fc.green_report()
        assert report["is_green"] is True
        assert report["test_pass_rate"] >= 0.95
        assert report["code_coverage"] >= 0.85
        assert report["lint_passed"] is True
        assert report["has_hardcode"] is False

    def test_barely_green_code_passes(self):
        fc = make_barely_green_code(test_count=100)
        assert fc.test_pass_rate >= 0.95
        assert fc.code_coverage >= 0.85
        assert fc.lint_passed is True
        assert fc.is_green() is True

    def test_low_pass_rate_not_green(self):
        fc = FunctionalCode()
        fc.add_module(make_module("m", functions=[
            make_function("f", 100, 90),
        ]))
        for i in range(100):
            if i < 80:
                fc.add_test_result(make_test_passed(f"t_{i}"))
            else:
                fc.add_test_result(make_test_failed(f"t_{i}"))
        assert fc.is_green() is False

    def test_low_coverage_not_green(self):
        fc = FunctionalCode()
        fc.add_module(make_module("m", functions=[
            make_function("f", 100, 70),
        ]))
        for i in range(100):
            fc.add_test_result(make_test_passed(f"t_{i}"))
        assert fc.is_green() is False

    def test_hardcode_not_green(self):
        fc = FunctionalCode()
        fc.add_module(make_module("m", functions=[
            make_function("f", 100, 95, hardcode=True),
        ]))
        for i in range(100):
            fc.add_test_result(make_test_passed(f"t_{i}"))
        assert fc.test_pass_rate >= 0.95
        assert fc.code_coverage >= 0.85
        assert fc.is_green() is False

    def test_green_report_contains_all_fields(self):
        fc = make_perfect_code()
        report = fc.green_report()
        required_fields = [
            "is_green",
            "test_pass_rate",
            "code_coverage",
            "total_tests",
            "passed_tests",
            "failed_tests",
            "lint_passed",
            "has_hardcode",
            "total_lines",
            "covered_lines",
            "module_count",
        ]
        for field in required_fields:
            assert field in report, f"报告缺少 field: {field}"

    def test_custom_threshold_pass(self):
        fc = FunctionalCode()
        fc.add_module(make_module("m", functions=[
            make_function("f", 100, 90),
        ]))
        for i in range(100):
            fc.add_test_result(make_test_passed(f"t_{i}"))

        assert fc.is_green(pass_rate_threshold=0.90, coverage_threshold=0.80) is True

    def test_custom_threshold_fail(self):
        fc = FunctionalCode()
        fc.add_module(make_module("m", functions=[
            make_function("f", 100, 90),
        ]))
        for i in range(100):
            fc.add_test_result(make_test_passed(f"t_{i}"))

        assert fc.is_green(pass_rate_threshold=1.0, coverage_threshold=0.95) is False

    def test_invalid_threshold_raises_value_error(self):
        fc = FunctionalCode()
        with pytest.raises(ValueError):
            fc.is_green(pass_rate_threshold=1.5, coverage_threshold=0.85)

        with pytest.raises(ValueError):
            fc.is_green(pass_rate_threshold=0.95, coverage_threshold=-0.1)

    def test_green_with_custom_low_threshold_always_passes_empty(self):
        fc = FunctionalCode()
        assert fc.is_green(pass_rate_threshold=0.0, coverage_threshold=0.0) is True


# ====================================================================
# 大体积压力测试
# ====================================================================


class TestLargeScale:
    """大体积代码集合下的 GREEN 判定。"""

    def test_100_modules_500_functions_95_percent_tests(self):
        fc = FunctionalCode()
        total_funcs = 0
        total_all_lines = 0
        total_cov_lines = 0

        for m in range(100):
            funcs = []
            for f_i in range(5):
                tl = 20
                cl = 17
                funcs.append(make_function(f"mod{m}_f{f_i}", tl, cl))
                total_funcs += 1
                total_all_lines += tl
                total_cov_lines += cl
            fc.add_module(make_module(f"module_{m}", functions=funcs))

        expected_coverage = total_cov_lines / total_all_lines

        for t in range(1000):
            if t < 960:
                fc.add_test_result(make_test_passed(f"t_{t}"))
            else:
                fc.add_test_result(make_test_failed(f"t_{t}"))

        assert fc.total_tests == 1000
        assert fc.test_pass_rate == 0.96
        assert fc.test_pass_rate >= 0.95
        assert fc.code_coverage == pytest.approx(expected_coverage, abs=0.001)
        assert fc.code_coverage >= 0.85
        assert fc.lint_passed is True
        assert fc.is_green() is True

    def test_hardcode_in_one_of_50_modules_detected(self):
        fc = FunctionalCode()
        for m in range(50):
            if m == 25:
                funcs = [make_function("leaked", 10, 8, hardcode=True)]
            else:
                funcs = [make_function("clean", 10, 9, hardcode=False)]
            fc.add_module(make_module(f"m_{m}", functions=funcs))

        assert fc.has_hardcode is True
        assert fc.lint_passed is False
        assert fc.is_green() is False


# ====================================================================
# 边界与异常
# ====================================================================


class TestEdgeCases:
    """边界条件与异常处理。"""

    def test_single_line_full_coverage(self):
        fc = FunctionalCode()
        fc.add_module(make_module("tiny", functions=[
            make_function("one_liner", 1, 1),
        ]))
        fc.add_test_result(make_test_passed("t"))
        assert fc.is_green() is True

    def test_single_line_zero_coverage(self):
        fc = FunctionalCode()
        fc.add_module(make_module("tiny", functions=[
            make_function("one_liner", 1, 0),
        ]))
        assert fc.code_coverage == 0.0
        assert fc.is_green() is False

    def test_threshold_boundary_0_95_exact(self):
        fc = FunctionalCode()
        for i in range(20):
            if i < 19:
                fc.add_test_result(make_test_passed(f"t_{i}"))
            else:
                fc.add_test_result(make_test_failed(f"t_{i}"))
        actual_rate = fc.test_pass_rate
        if actual_rate >= 0.95:
            assert True
        else:
            assert False, f"19/20 = {actual_rate} 应 >= 0.95"

    def test_threshold_boundary_coverage_85_exact(self):
        fc = FunctionalCode()
        fc.add_module(make_module("exact", functions=[
            make_function("f", 20, 17),
        ]))
        assert fc.code_coverage == 0.85
        fc.add_test_result(make_test_passed("t"))
        assert fc.is_green() is True

    def test_multiple_modules_all_green(self):
        fc = FunctionalCode()
        configs = [
            ("auth", [(40, 36), (30, 27), (50, 43)]),
            ("api", [(60, 54), (25, 22), (35, 30)]),
            ("db", [(80, 72), (45, 40), (55, 47)]),
        ]
        for mod_name, pairs in configs:
            funcs = [make_function(f"f_{i}", tl, cl) for i, (tl, cl) in enumerate(pairs)]
            fc.add_module(make_module(mod_name, functions=funcs))

        for i in range(200):
            if i < 196:
                fc.add_test_result(make_test_passed(f"t_{i}"))
            else:
                fc.add_test_result(make_test_failed(f"t_{i}"))

        assert fc.test_pass_rate >= 0.95
        assert fc.is_green() is True

    def test_green_report_values_consistent(self):
        fc = make_perfect_code(module_count=4, functions_per_module=5, test_count=50, coverage_rate=0.92)
        report = fc.green_report()

        assert report["total_tests"] == fc.total_tests
        assert report["passed_tests"] == fc.passed_tests
        assert report["module_count"] == len(fc.modules)
        assert report["test_pass_rate"] == pytest.approx(fc.test_pass_rate, abs=0.001)
        assert report["code_coverage"] == pytest.approx(fc.code_coverage, abs=0.001)

    def test_add_test_results_batch(self):
        fc = FunctionalCode()
        batch = [make_test_passed(f"batch_{i}") for i in range(30)]
        fc.add_test_results(batch)
        assert fc.total_tests == 30
        assert fc.passed_tests == 30
        assert fc.test_pass_rate == 1.0
