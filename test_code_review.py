import pytest
import time
from datetime import datetime, timedelta
from typing import List, Dict, Any, Optional
from dataclasses import dataclass, field
from enum import Enum


class ReviewStatus(Enum):
    PENDING = "pending"
    IN_PROGRESS = "in_progress"
    COMPLETED = "completed"
    FAILED = "failed"


class ViolationSeverity(Enum):
    LOW = "low"
    MEDIUM = "medium"
    HIGH = "high"
    CRITICAL = "critical"


@dataclass
class CodeFile:
    path: str
    content: str
    lines: int = 0
    reviewed: bool = False
    violations: List[str] = field(default_factory=list)

    def __post_init__(self):
        self.lines = len(self.content.split('\n')) if self.content else 0


@dataclass
class Violation:
    file_path: str
    line_number: int
    rule_id: str
    description: str
    severity: ViolationSeverity
    suggestion: str = ""


@dataclass
class ReviewReport:
    total_files: int
    reviewed_files: int
    total_violations: int
    violations_by_severity: Dict[str, int]
    review_duration: float
    timestamp: str
    violations: List[Violation] = field(default_factory=list)


class CodeReviewEngine:
    """代码自动审查引擎"""

    def __init__(self):
        self.files_to_review: List[CodeFile] = []
        self.violations: List[Violation] = []
        self.start_time: Optional[float] = None
        self.end_time: Optional[float] = None
        self.review_rules = self._init_review_rules()

    def _init_review_rules(self) -> Dict[str, Dict[str, Any]]:
        """初始化代码审查规则"""
        return {
            "PEP8_INDENTATION": {
                "name": "PEP8缩进检查",
                "severity": ViolationSeverity.MEDIUM,
                "check_fn": self._check_indentation
            },
            "PEP8_LINE_LENGTH": {
                "name": "PEP8行长度检查",
                "severity": ViolationSeverity.LOW,
                "check_fn": self._check_line_length
            },
            "NO_PRINT_STATEMENT": {
                "name": "禁止print语句",
                "severity": ViolationSeverity.HIGH,
                "check_fn": self._check_print_statement
            },
            "NO_EVAL": {
                "name": "禁止eval使用",
                "severity": ViolationSeverity.CRITICAL,
                "check_fn": self._check_eval_usage
            },
            "FUNCTION_LENGTH": {
                "name": "函数长度检查",
                "severity": ViolationSeverity.MEDIUM,
                "check_fn": self._check_function_length
            },
            "MISSING_DOCSTRING": {
                "name": "缺少文档字符串",
                "severity": ViolationSeverity.LOW,
                "check_fn": self._check_docstring
            },
            "NO_HARDcoded_PASSWORD": {
                "name": "硬编码密码检查",
                "severity": ViolationSeverity.CRITICAL,
                "check_fn": self._check_hardcoded_password
            },
            "NO_SQL_INJECTION": {
                "name": "SQL注入检查",
                "severity": ViolationSeverity.CRITICAL,
                "check_fn": self._check_sql_injection
            },
            "NO_MAGIC_NUMBER": {
                "name": "魔法数字检查",
                "severity": ViolationSeverity.LOW,
                "check_fn": self._check_magic_number
            },
            "NO_EXCEPT_PASS": {
                "name": "禁止except pass",
                "severity": ViolationSeverity.HIGH,
                "check_fn": self._check_except_pass
            }
        }

    def _check_indentation(self, content: str, line_numbers: range) -> List[Violation]:
        """检查缩进是否符合PEP8"""
        violations = []
        lines = content.split('\n')
        for i in line_numbers:
            if i < len(lines):
                line = lines[i]
                stripped = line.lstrip()
                if stripped and len(line) - len(stripped) > 0:
                    if (len(line) - len(stripped)) % 4 != 0:
                        violations.append(Violation(
                            file_path="",
                            line_number=i + 1,
                            rule_id="PEP8_INDENTATION",
                            description=f"缩进不符合PEP8标准，应为4的倍数",
                            severity=ViolationSeverity.MEDIUM
                        ))
        return violations

    def _check_line_length(self, content: str, line_numbers: range) -> List[Violation]:
        """检查行长度是否超过120字符"""
        violations = []
        lines = content.split('\n')
        for i in line_numbers:
            if i < len(lines):
                line = lines[i]
                if len(line) > 120:
                    violations.append(Violation(
                        file_path="",
                        line_number=i + 1,
                        rule_id="PEP8_LINE_LENGTH",
                        description=f"行长度超过120字符，当前长度: {len(line)}",
                        severity=ViolationSeverity.LOW
                    ))
        return violations

    def _check_print_statement(self, content: str, line_numbers: range) -> List[Violation]:
        """检查是否使用print语句"""
        violations = []
        lines = content.split('\n')
        for i in line_numbers:
            if i < len(lines):
                line = lines[i].strip()
                if line.startswith('print('):
                    violations.append(Violation(
                        file_path="",
                        line_number=i + 1,
                        rule_id="NO_PRINT_STATEMENT",
                        description="使用print语句，建议使用日志模块",
                        severity=ViolationSeverity.HIGH
                    ))
        return violations

    def _check_eval_usage(self, content: str, line_numbers: range) -> List[Violation]:
        """检查是否使用eval"""
        violations = []
        lines = content.split('\n')
        for i in line_numbers:
            if i < len(lines):
                line = lines[i]
                if 'eval(' in line and not line.strip().startswith('#'):
                    violations.append(Violation(
                        file_path="",
                        line_number=i + 1,
                        rule_id="NO_EVAL",
                        description="使用eval函数，存在安全风险",
                        severity=ViolationSeverity.CRITICAL
                    ))
        return violations

    def _check_function_length(self, content: str, line_numbers: range) -> List[Violation]:
        """检查函数长度是否超过50行"""
        violations = []
        lines = content.split('\n')
        in_function = False
        function_start = 0
        function_lines = 0

        for i in line_numbers:
            if i < len(lines):
                line = lines[i]
                if 'def ' in line and not line.strip().startswith('#'):
                    if in_function and function_lines > 50:
                        violations.append(Violation(
                            file_path="",
                            line_number=function_start + 1,
                            rule_id="FUNCTION_LENGTH",
                            description=f"函数过长，共{function_lines}行，建议拆分为更小的函数",
                            severity=ViolationSeverity.MEDIUM
                        ))
                    in_function = True
                    function_start = i
                    function_lines = 0
                elif in_function:
                    function_lines += 1

        if in_function and function_lines > 50:
            violations.append(Violation(
                file_path="",
                line_number=function_start + 1,
                rule_id="FUNCTION_LENGTH",
                description=f"函数过长，共{function_lines}行，建议拆分为更小的函数",
                severity=ViolationSeverity.MEDIUM
            ))

        return violations

    def _check_docstring(self, content: str, line_numbers: range) -> List[Violation]:
        """检查函数/类是否有文档字符串"""
        violations = []
        lines = content.split('\n')

        for i in line_numbers:
            if i < len(lines):
                line = lines[i].strip()
                if (line.startswith('def ') or line.startswith('class ')) and not line.startswith('#'):
                    next_line = lines[i + 1].strip() if i + 1 < len(lines) else ""
                    if not (next_line.startswith('\"\"\"') or next_line.startswith("'''")):
                        violations.append(Violation(
                            file_path="",
                            line_number=i + 1,
                            rule_id="MISSING_DOCSTRING",
                            description="缺少文档字符串",
                            severity=ViolationSeverity.LOW
                        ))

        return violations

    def _check_hardcoded_password(self, content: str, line_numbers: range) -> List[Violation]:
        """检查是否有硬编码密码"""
        violations = []
        lines = content.split('\n')
        password_patterns = ['password', 'passwd', 'pwd', 'secret']

        for i in line_numbers:
            if i < len(lines):
                line = lines[i].lower()
                if any(pattern in line for pattern in password_patterns):
                    if '=' in line and ('"' in line or "'" in line) and not line.strip().startswith('#'):
                        violations.append(Violation(
                            file_path="",
                            line_number=i + 1,
                            rule_id="NO_HARDcoded_PASSWORD",
                            description="检测到硬编码密码，请使用环境变量或配置管理",
                            severity=ViolationSeverity.CRITICAL
                        ))

        return violations

    def _check_sql_injection(self, content: str, line_numbers: range) -> List[Violation]:
        """检查是否存在SQL注入风险"""
        violations = []
        lines = content.split('\n')

        for i in line_numbers:
            if i < len(lines):
                line = lines[i]
                if ('execute(' in line or 'executemany(' in line) and not line.strip().startswith('#'):
                    if ('%' in line or '+' in line or 'f"' in line or "f'" in line or '.format(' in line):
                        violations.append(Violation(
                            file_path="",
                            line_number=i + 1,
                            rule_id="NO_SQL_INJECTION",
                            description="存在SQL注入风险，请使用参数化查询",
                            severity=ViolationSeverity.CRITICAL
                        ))

        return violations

    def _check_magic_number(self, content: str, line_numbers: range) -> List[Violation]:
        """检查是否使用魔法数字"""
        violations = []
        lines = content.split('\n')
        import re
        number_pattern = re.compile(r'\b[0-9]{3,}\b')

        for i in line_numbers:
            if i < len(lines):
                line = lines[i]
                if not line.strip().startswith('#'):
                    matches = number_pattern.findall(line)
                    for match in matches:
                        if int(match) > 1000 and not line.strip().startswith('import'):
                            violations.append(Violation(
                                file_path="",
                                line_number=i + 1,
                                rule_id="NO_MAGIC_NUMBER",
                                description=f"使用魔法数字 {match}，建议定义为常量",
                                severity=ViolationSeverity.LOW
                            ))

        return violations

    def _check_except_pass(self, content: str, line_numbers: range) -> List[Violation]:
        """检查是否有except pass"""
        violations = []
        lines = content.split('\n')

        for i in line_numbers:
            if i < len(lines):
                line = lines[i].strip()
                if line == 'pass' and i > 0:
                    prev_line = lines[i - 1].strip()
                    if prev_line.startswith('except'):
                        violations.append(Violation(
                            file_path="",
                            line_number=i + 1,
                            rule_id="NO_EXCEPT_PASS",
                            description="except pass 没有处理异常，请添加适当的异常处理",
                            severity=ViolationSeverity.HIGH
                        ))

        return violations

    def add_files(self, files: List[CodeFile]):
        """添加需要审查的文件"""
        self.files_to_review.extend(files)

    def review_file(self, file: CodeFile) -> List[Violation]:
        """审查单个文件"""
        if not file.content:
            return []

        file_violations = []
        line_range = range(len(file.content.split('\n')))

        for rule_id, rule in self.review_rules.items():
            check_fn = rule['check_fn']
            violations = check_fn(file.content, line_range)
            for violation in violations:
                violation.file_path = file.path
                file_violations.append(violation)

        file.reviewed = True
        file.violations = [v.rule_id for v in file_violations]
        self.violations.extend(file_violations)

        return file_violations

    def review_all(self) -> List[Violation]:
        """审查所有文件"""
        self.start_time = time.time()
        all_violations = []

        for file in self.files_to_review:
            violations = self.review_file(file)
            all_violations.extend(violations)

        self.end_time = time.time()
        return all_violations

    def get_review_coverage(self) -> float:
        """获取审查覆盖率"""
        if not self.files_to_review:
            return 0.0
        reviewed_count = sum(1 for f in self.files_to_review if f.reviewed)
        return (reviewed_count / len(self.files_to_review)) * 100.0

    def get_violation_detection_rate(self, expected_violations: int) -> float:
        """获取违规检出率"""
        if expected_violations == 0:
            return 100.0 if len(self.violations) == 0 else 0.0
        detected = len(self.violations)
        return min((detected / expected_violations) * 100.0, 100.0)

    def generate_report(self) -> ReviewReport:
        """生成审查报告"""
        if self.start_time is None or self.end_time is None:
            raise RuntimeError("请先执行审查")

        duration = self.end_time - self.start_time

        violations_by_severity = {
            "LOW": 0,
            "MEDIUM": 0,
            "HIGH": 0,
            "CRITICAL": 0
        }

        for violation in self.violations:
            severity_key = violation.severity.value.upper()
            violations_by_severity[severity_key] = violations_by_severity.get(severity_key, 0) + 1

        return ReviewReport(
            total_files=len(self.files_to_review),
            reviewed_files=sum(1 for f in self.files_to_review if f.reviewed),
            total_violations=len(self.violations),
            violations_by_severity=violations_by_severity,
            review_duration=duration,
            timestamp=datetime.now().isoformat(),
            violations=self.violations
        )


def create_test_file_with_violations() -> CodeFile:
    """创建包含违规的代码文件"""
    content = '''def bad_function():
    x = 12345
    print("test")
    result = eval("1 + 1")
    password = "123456"
    cursor.execute(f"SELECT * FROM users WHERE id = {user_id}")
    try:
        pass
    except:
        pass
'''
    return CodeFile(path="test_bad.py", content=content)


def create_test_file_without_violations() -> CodeFile:
    """创建不包含违规的代码文件"""
    content = '''def good_function():
    """这是一个好的函数"""
    constant_value = 100
    return constant_value
'''
    return CodeFile(path="test_good.py", content=content)


def create_long_function_file() -> CodeFile:
    """创建包含过长函数的文件"""
    lines = ["def very_long_function():"] + ["    pass"] * 55
    content = '\n'.join(lines)
    return CodeFile(path="test_long.py", content=content)


class TestCodeAutoReview:
    """代码自动审查测试类"""

    def setup_method(self):
        """每个测试方法执行前初始化"""
        self.engine = CodeReviewEngine()

    def test_review_coverage_100_percent(self):
        """测试审查覆盖率达到100%"""
        files = [
            create_test_file_with_violations(),
            create_test_file_without_violations(),
            create_long_function_file()
        ]
        self.engine.add_files(files)
        self.engine.review_all()

        coverage = self.engine.get_review_coverage()
        assert coverage == 100.0, f"审查覆盖率应为100%，实际为{coverage}%"

    def test_violation_detection_rate_ge_90_percent(self):
        """测试代码规范违规检出率 ≥90%"""
        file = create_test_file_with_violations()
        self.engine.add_files([file])
        self.engine.review_all()

        violations = self.engine.violations
        expected_violation_count = 7

        detection_rate = self.engine.get_violation_detection_rate(expected_violation_count)
        assert detection_rate >= 90.0, f"违规检出率应≥90%，实际为{detection_rate}%"

    def test_report_generation_time_le_1_hour(self):
        """测试审查报告生成时间 ≤1小时"""
        files = [
            create_test_file_with_violations(),
            create_test_file_without_violations(),
            create_long_function_file()
        ]
        self.engine.add_files(files)
        self.engine.review_all()

        report = self.engine.generate_report()
        max_allowed_time = 3600.0

        assert report.review_duration <= max_allowed_time, \
            f"审查报告生成时间应≤1小时，实际为{report.review_duration}秒"

    def test_detect_print_statement(self):
        """测试检测print语句"""
        file = create_test_file_with_violations()
        self.engine.add_files([file])
        self.engine.review_all()

        print_violations = [v for v in self.engine.violations if v.rule_id == "NO_PRINT_STATEMENT"]
        assert len(print_violations) > 0, "应检测到print语句违规"

    def test_detect_eval_usage(self):
        """测试检测eval使用"""
        file = create_test_file_with_violations()
        self.engine.add_files([file])
        self.engine.review_all()

        eval_violations = [v for v in self.engine.violations if v.rule_id == "NO_EVAL"]
        assert len(eval_violations) > 0, "应检测到eval使用违规"

    def test_detect_hardcoded_password(self):
        """测试检测硬编码密码"""
        file = create_test_file_with_violations()
        self.engine.add_files([file])
        self.engine.review_all()

        password_violations = [v for v in self.engine.violations if v.rule_id == "NO_HARDcoded_PASSWORD"]
        assert len(password_violations) > 0, "应检测到硬编码密码违规"

    def test_detect_sql_injection(self):
        """测试检测SQL注入"""
        file = create_test_file_with_violations()
        self.engine.add_files([file])
        self.engine.review_all()

        sql_violations = [v for v in self.engine.violations if v.rule_id == "NO_SQL_INJECTION"]
        assert len(sql_violations) > 0, "应检测到SQL注入风险"

    def test_detect_missing_docstring(self):
        """测试检测缺少文档字符串"""
        file = create_test_file_with_violations()
        self.engine.add_files([file])
        self.engine.review_all()

        docstring_violations = [v for v in self.engine.violations if v.rule_id == "MISSING_DOCSTRING"]
        assert len(docstring_violations) > 0, "应检测到缺少文档字符串违规"

    def test_detect_long_function(self):
        """测试检测过长函数"""
        file = create_long_function_file()
        self.engine.add_files([file])
        self.engine.review_all()

        long_func_violations = [v for v in self.engine.violations if v.rule_id == "FUNCTION_LENGTH"]
        assert len(long_func_violations) > 0, "应检测到过长函数违规"

    def test_no_false_positive_for_good_code(self):
        """测试对良好代码无误报"""
        file = create_test_file_without_violations()
        self.engine.add_files([file])
        self.engine.review_all()

        violations = self.engine.violations
        assert len(violations) == 0, f"良好代码不应有违规，实际检测到{len(violations)}个"

    def test_report_structure(self):
        """测试审查报告结构完整性"""
        files = [create_test_file_with_violations()]
        self.engine.add_files(files)
        self.engine.review_all()

        report = self.engine.generate_report()
        assert report.total_files == 1
        assert report.reviewed_files == 1
        assert report.total_violations > 0
        assert len(report.violations_by_severity) == 4
        assert report.review_duration > 0
        assert report.timestamp != ""

    def test_empty_file_handling(self):
        """测试空文件处理"""
        empty_file = CodeFile(path="empty.py", content="")
        self.engine.add_files([empty_file])
        self.engine.review_all()

        violations = self.engine.violations
        assert len(violations) == 0, "空文件不应产生违规"

    def test_multiple_files_review(self):
        """测试多文件审查"""
        files = [
            create_test_file_with_violations(),
            create_test_file_without_violations(),
            create_long_function_file(),
            create_test_file_with_violations()
        ]
        self.engine.add_files(files)
        self.engine.review_all()

        coverage = self.engine.get_review_coverage()
        assert coverage == 100.0, f"多文件审查覆盖率应为100%，实际为{coverage}%"

    def test_severity_distribution(self):
        """测试违规严重程度分布"""
        file = create_test_file_with_violations()
        self.engine.add_files([file])
        self.engine.review_all()

        report = self.engine.generate_report()
        severity_sum = sum(report.violations_by_severity.values())
        assert severity_sum == report.total_violations, \
            "严重程度分布总和应等于总违规数"

    def test_review_duration_is_positive(self):
        """测试审查持续时间是否为正数"""
        files = [create_test_file_with_violations()]
        self.engine.add_files(files)
        self.engine.review_all()

        report = self.engine.generate_report()
        assert report.review_duration > 0, "审查持续时间应为正数"

    def test_violation_details_completeness(self):
        """测试违规详情完整性"""
        file = create_test_file_with_violations()
        self.engine.add_files([file])
        self.engine.review_all()

        for violation in self.engine.violations:
            assert violation.file_path != "", "违规应有文件路径"
            assert violation.line_number > 0, "违规行号应大于0"
            assert violation.rule_id != "", "违规应有规则ID"
            assert violation.description != "", "违规应有描述"
            assert violation.severity in [s for s in ViolationSeverity], \
                "违规应有有效的严重程度"

    def test_report_generation_before_review_raises_error(self):
        """测试在审查前生成报告应抛出异常"""
        with pytest.raises(RuntimeError, match="请先执行审查"):
            self.engine.generate_report()

    def test_get_review_coverage_with_no_files(self):
        """测试无文件时审查覆盖率返回0"""
        coverage = self.engine.get_review_coverage()
        assert coverage == 0.0, "无文件时审查覆盖率应为0%"

    def test_get_violation_detection_rate_with_zero_expected(self):
        """测试预期违规为0时的检出率计算"""
        file = create_test_file_without_violations()
        self.engine.add_files([file])
        self.engine.review_all()

        detection_rate = self.engine.get_violation_detection_rate(0)
        assert detection_rate == 100.0, "预期违规为0且实际无违规时，检出率应为100%"

    def test_comprehensive_review_workflow(self):
        """测试完整的审查工作流"""
        files = [
            create_test_file_with_violations(),
            create_test_file_without_violations(),
            create_long_function_file()
        ]
        self.engine.add_files(files)

        violations = self.engine.review_all()
        assert len(violations) > 0, "应检测到违规"

        coverage = self.engine.get_review_coverage()
        assert coverage == 100.0, f"覆盖率应为100%，实际为{coverage}%"

        report = self.engine.generate_report()
        assert report.total_files == 3
        assert report.reviewed_files == 3
        assert report.total_violations == len(violations)
        assert report.review_duration <= 3600.0

        expected_violations = 10
        detection_rate = self.engine.get_violation_detection_rate(expected_violations)
        assert detection_rate >= 90.0, f"检出率应≥90%，实际为{detection_rate}%"

    def test_review_empty_file_list(self):
        """测试审查空文件列表"""
        self.engine.review_all()
        coverage = self.engine.get_review_coverage()
        assert coverage == 0.0, "空文件列表覆盖率应为0%"

    def test_review_file_with_only_whitespace(self):
        """测试仅包含空格的代码文件"""
        content = "   \n  \n   \n"
        file = CodeFile(path="whitespace.py", content=content)
        self.engine.add_files([file])
        self.engine.review_all()
        violations = self.engine.violations
        assert len(violations) == 0, "纯空格文件不应产生违规"

    def test_review_file_with_unicode_content(self):
        """测试包含unicode字符的代码文件"""
        content = 'def hello():\n    """你好世界"""\n    msg = "你好"\n    return msg\n'
        file = CodeFile(path="unicode_test.py", content=content)
        self.engine.add_files([file])
        self.engine.review_all()
        coverage = self.engine.get_review_coverage()
        assert coverage == 100.0, "unicode文件覆盖率应为100%"

    def test_violation_severity_enum_values(self):
        """测试ViolationSeverity枚举值"""
        assert ViolationSeverity.LOW.value == "low"
        assert ViolationSeverity.MEDIUM.value == "medium"
        assert ViolationSeverity.HIGH.value == "high"
        assert ViolationSeverity.CRITICAL.value == "critical"

    def test_code_file_lines_count(self):
        """测试CodeFile行号计算"""
        content = "line1\nline2\nline3"
        file = CodeFile(path="count.py", content=content)
        assert file.lines == 3, f"应有3行，实际{file.lines}行"

    def test_code_file_empty_content_lines(self):
        """测试空内容CodeFile行号"""
        file = CodeFile(path="empty.py", content="")
        assert file.lines == 0, "空内容行数应为0"

    def test_add_files_multiple_times(self):
        """测试多次添加文件"""
        file1 = create_test_file_with_violations()
        file2 = create_test_file_without_violations()
        self.engine.add_files([file1])
        self.engine.add_files([file2])
        assert len(self.engine.files_to_review) == 2, "应添加两个文件"

    def test_detect_except_pass_violation(self):
        """测试检测except pass违规"""
        content = '''def bad_exception():
    try:
        x = 1
    except:
        pass
'''
        file = CodeFile(path="except_pass_test.py", content=content)
        self.engine.add_files([file])
        self.engine.review_all()
        except_pass_violations = [v for v in self.engine.violations if v.rule_id == "NO_EXCEPT_PASS"]
        assert len(except_pass_violations) > 0, "应检测到except pass违规"

    def test_detect_magic_number_violation(self):
        """测试检测魔法数字违规"""
        content = '''def calc():
    x = 99999
    return x
'''
        file = CodeFile(path="magic_num_test.py", content=content)
        self.engine.add_files([file])
        self.engine.review_all()
        magic_violations = [v for v in self.engine.violations if v.rule_id == "NO_MAGIC_NUMBER"]
        assert len(magic_violations) > 0, "应检测到魔法数字违规"

    def test_detect_line_length_violation(self):
        """测试检测过长行违规"""
        long_line = "x = " + "a" * 130
        content = f"def bad():\n{long_line}\n"
        file = CodeFile(path="long_line_test.py", content=content)
        self.engine.add_files([file])
        self.engine.review_all()
        line_length_violations = [v for v in self.engine.violations if v.rule_id == "PEP8_LINE_LENGTH"]
        assert len(line_length_violations) > 0, "应检测到行长度违规"

    def test_detect_indentation_violation(self):
        """测试检测缩进违规"""
        content = "def bad():\n    x = 1\n   y = 2\n"
        file = CodeFile(path="indent_test.py", content=content)
        self.engine.add_files([file])
        self.engine.review_all()
        indent_violations = [v for v in self.engine.violations if v.rule_id == "PEP8_INDENTATION"]
        assert len(indent_violations) > 0, "应检测到缩进违规"

    def test_review_report_violations_list_matches_total(self):
        """测试报告中违规列表长度等于total_violations"""
        file = create_test_file_with_violations()
        self.engine.add_files([file])
        self.engine.review_all()
        report = self.engine.generate_report()
        assert report.total_violations == len(report.violations), \
            "报告中total_violations应等于violations列表长度"

    def test_review_all_returns_all_violations(self):
        """测试review_all返回的违规列表非空"""
        file = create_test_file_with_violations()
        self.engine.add_files([file])
        all_violations = self.engine.review_all()
        assert len(all_violations) == len(self.engine.violations), \
            "review_all返回值应与engine.violations一致"

    def test_multiple_reviews_accumulate_violations(self):
        """测试多次审查累加违规"""
        file1 = create_test_file_with_violations()
        self.engine.add_files([file1])
        self.engine.review_all()
        first_count = len(self.engine.violations)
        file2 = create_test_file_with_violations()
        self.engine.add_files([file2])
        self.engine.review_all()
        second_count = len(self.engine.violations)
        assert second_count > first_count, "第二次审查后违规数应增加"


if __name__ == "__main__":
    pytest.main([__file__, "-v"])
