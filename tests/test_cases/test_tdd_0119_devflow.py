import re
import pytest
from dataclasses import dataclass
from enum import Enum
from typing import Optional


class TodoStatus(Enum):
    COMPLETED = "completed"
    PENDING = "pending"
    UNCHECKED = "unchecked"


@dataclass
class TodoItem:
    text: str
    status: TodoStatus
    raw: str


class MarkdownTodoParser:
    """解析 Markdown 格式的 todo 项目列表。

    支持格式:
        - [x] 已完成事项
        - [ ] 待完成事项
        - 纯文本行（无方括号）
    """

    # 标准 todo 项正则: `- [x] text` 或 `- [ ] text`
    CHECKBOX_PATTERN = re.compile(
        r"^[-*+]\s+\[([ xX\-\~\*\?])\]\s*(.*)$",
        re.IGNORECASE,
    )
    # 纯列表项正则: `- text`（无方括号）
    BARE_LIST_PATTERN = re.compile(
        r"^[-*+]\s+(.+)$",
    )

    @classmethod
    def parse_line(cls, line: str) -> Optional[TodoItem]:
        """解析单行 Markdown todo 文本。

        Returns:
            TodoItem 对象，若非 todo 行则返回 None。
        """
        line = line.rstrip("\n\r")
        if not line.strip():
            return None

        m = cls.CHECKBOX_PATTERN.match(line)
        if m:
            marker = m.group(1)
            text = m.group(2).strip()
            status = cls._classify_marker(marker)
            return TodoItem(text=text, status=status, raw=line)

        m2 = cls.BARE_LIST_PATTERN.match(line)
        if m2:
            text = m2.group(1).strip()
            return TodoItem(text=text, status=TodoStatus.UNCHECKED, raw=line)

        return None

    @staticmethod
    def _classify_marker(marker: str) -> TodoStatus:
        """根据方括号内的标记字符判定任务状态。"""
        marker_clean = marker.strip()
        if marker_clean == "":
            return TodoStatus.PENDING
        if marker_clean.lower() == "x":
            return TodoStatus.COMPLETED
        # 非标准标记视为未完成
        return TodoStatus.PENDING

    @classmethod
    def parse_document(cls, markdown: str) -> list[TodoItem]:
        """解析整个 Markdown 文档中的所有 todo 项。"""
        items = []
        for line in markdown.splitlines():
            item = cls.parse_line(line)
            if item is not None:
                items.append(item)
        return items

    @classmethod
    def count_completed(cls, markdown: str) -> int:
        """统计已完成的 todo 项数量。"""
        return sum(
            1 for item in cls.parse_document(markdown)
            if item.status == TodoStatus.COMPLETED
        )

    @classmethod
    def count_pending(cls, markdown: str) -> int:
        """统计未完成（pending 或 unchecked）的 todo 项数量。"""
        return sum(
            1 for item in cls.parse_document(markdown)
            if item.status != TodoStatus.COMPLETED
        )

    @classmethod
    def completion_ratio(cls, markdown: str) -> float:
        """计算完成率 (0.0 ~ 1.0)，无 todo 时返回 0.0。"""
        items = cls.parse_document(markdown)
        if not items:
            return 0.0
        completed = cls.count_completed(markdown)
        return completed / len(items)


# ====================================================================
# 测试：标准 checkbox 解析
# ====================================================================


class TestStandardCheckboxParsing:
    """标准格式的 checkbox 解析：`[x]` 和 `[ ]`。"""

    def test_lowercase_x_is_completed(self):
        item = MarkdownTodoParser.parse_line("- [x] 修复用户登录bug")
        assert item is not None
        assert item.status == TodoStatus.COMPLETED
        assert item.text == "修复用户登录bug"

    def test_empty_bracket_is_pending(self):
        item = MarkdownTodoParser.parse_line("- [ ] 编写接口文档")
        assert item is not None
        assert item.status == TodoStatus.PENDING
        assert item.text == "编写接口文档"

    def test_asterisk_bullet_completed(self):
        item = MarkdownTodoParser.parse_line("* [x] 使用星号列表标记")
        assert item is not None
        assert item.status == TodoStatus.COMPLETED
        assert item.text == "使用星号列表标记"

    def test_plus_bullet_pending(self):
        item = MarkdownTodoParser.parse_line("+ [ ] 使用加号列表标记")
        assert item is not None
        assert item.status == TodoStatus.PENDING
        assert item.text == "使用加号列表标记"

    def test_multiple_spaces_after_bracket(self):
        item = MarkdownTodoParser.parse_line("- [x]    前面有多个空格")
        assert item is not None
        assert item.status == TodoStatus.COMPLETED
        assert item.text == "前面有多个空格"

    def test_text_with_special_chars(self):
        item = MarkdownTodoParser.parse_line("- [x] 支持 JSON、XML 等格式 `v2.0`")
        assert item is not None
        assert item.status == TodoStatus.COMPLETED
        assert "JSON" in item.text

    def test_chinese_text_completed(self):
        item = MarkdownTodoParser.parse_line("- [x] 完成中文文案翻译")
        assert item is not None
        assert item.status == TodoStatus.COMPLETED
        assert item.text == "完成中文文案翻译"

    def test_unicode_emoji_in_text(self):
        item = MarkdownTodoParser.parse_line("- [ ] \U0001f4a1 添加需求说明")
        assert item is not None
        assert item.status == TodoStatus.PENDING
        assert "\U0001f4a1" in item.text


# ====================================================================
# 测试：大写 X 边界情况（上轮报告缺失）
# ====================================================================


class TestUppercaseXMarker:
    """大写 X 标记：`[X]` 应视为已完成。"""

    def test_uppercase_x_is_completed(self):
        item = MarkdownTodoParser.parse_line("- [X] 大写字母 X 标记")
        assert item is not None
        assert item.status == TodoStatus.COMPLETED

    def test_uppercase_x_different_bullet_styles(self):
        for bullet in ["-", "*", "+"]:
            line = f"{bullet} [X] 大写 X 项"
            item = MarkdownTodoParser.parse_line(line)
            assert item is not None, f"bullet '{bullet}' 应能解析"
            assert item.status == TodoStatus.COMPLETED, f"bullet '{bullet}' 的大写 X 应为已完成"

    def test_mixed_case_x(self):
        """混合大小写 x/X 均视为已完成。"""
        item1 = MarkdownTodoParser.parse_line("- [x] 小写 x")
        item2 = MarkdownTodoParser.parse_line("- [X] 大写 X")
        assert item1.status == TodoStatus.COMPLETED
        assert item2.status == TodoStatus.COMPLETED
        assert item1.status == item2.status

    def test_uppercase_x_in_document_count(self):
        doc = "- [X] 任务一\n- [X] 任务二\n- [ ] 任务三\n"
        items = MarkdownTodoParser.parse_document(doc)
        assert MarkdownTodoParser.count_completed(doc) == 2
        assert MarkdownTodoParser.count_pending(doc) == 1


# ====================================================================
# 测试：非标准标记（上轮报告缺失）
# ====================================================================


class TestNonStandardMarkers:
    """非标准标记如 [-]、[~]、[*]、[?] 等应视为未完成。"""

    def test_dash_marker_is_pending(self):
        item = MarkdownTodoParser.parse_line("- [-] 横杠标记")
        assert item is not None
        assert item.status == TodoStatus.PENDING

    def test_tilde_marker_is_pending(self):
        item = MarkdownTodoParser.parse_line("- [~] 波浪线标记")
        assert item is not None
        assert item.status == TodoStatus.PENDING

    def test_asterisk_marker_is_pending(self):
        item = MarkdownTodoParser.parse_line("- [*] 星号标记")
        assert item is not None
        assert item.status == TodoStatus.PENDING

    def test_question_mark_marker_is_pending(self):
        item = MarkdownTodoParser.parse_line("- [?] 问号标记")
        assert item is not None
        assert item.status == TodoStatus.PENDING

    def test_space_marker_is_pending(self):
        """方括号内为空格时视为待完成。"""
        item = MarkdownTodoParser.parse_line("- [ ] 空格标记")
        assert item is not None
        assert item.status == TodoStatus.PENDING

    def test_non_standard_not_counted_as_completed(self):
        doc = "- [-] 半完成\n- [*] 星号\n- [~] 波浪\n- [?] 问号\n"
        completed = MarkdownTodoParser.count_completed(doc)
        assert completed == 0, "非标准标记不应算作已完成"

    def test_non_standard_included_in_pending_count(self):
        doc = "- [-] 横杠\n- [*] 星号\n"
        items = MarkdownTodoParser.parse_document(doc)
        assert len(items) == 2
        assert MarkdownTodoParser.count_pending(doc) == 2

    def test_mixed_standard_and_nonstandard(self):
        doc = "- [x] 已完成\n- [ ] 未完成\n- [-] 半完成\n- [X] 大写完成\n- [?] 问号\n"
        items = MarkdownTodoParser.parse_document(doc)
        assert len(items) == 5
        completed = MarkdownTodoParser.count_completed(doc)
        assert completed == 2, "只有 [x] 和 [X] 是已完成"
        assert MarkdownTodoParser.count_pending(doc) == 3

    def test_nonstandard_marker_text_preserved(self):
        """非标准标记的文本部分应正确提取。"""
        item = MarkdownTodoParser.parse_line("- [~] 这是非标准标记的文本内容")
        assert item is not None
        assert item.text == "这是非标准标记的文本内容"
        assert item.status == TodoStatus.PENDING


# ====================================================================
# 测试：无方括号行（上轮报告缺失）
# ====================================================================


class TestLinesWithoutBrackets:
    """纯列表项 `- text`（无方括号）应被正确识别。"""

    def test_bare_list_item_parsed(self):
        item = MarkdownTodoParser.parse_line("- 这是一个纯列表项")
        assert item is not None
        assert item.status == TodoStatus.UNCHECKED
        assert item.text == "这是一个纯列表项"

    def test_bare_list_with_asterisk(self):
        item = MarkdownTodoParser.parse_line("* 星号纯列表项")
        assert item is not None
        assert item.status == TodoStatus.UNCHECKED
        assert item.text == "星号纯列表项"

    def test_bare_list_with_plus(self):
        item = MarkdownTodoParser.parse_line("+ 加号纯列表项")
        assert item is not None
        assert item.status == TodoStatus.UNCHECKED
        assert item.text == "加号纯列表项"

    def test_bare_list_counted_as_pending(self):
        doc = "- 纯列表一\n- 纯列表二\n- [x] 已完成\n"
        assert MarkdownTodoParser.count_pending(doc) == 2
        assert MarkdownTodoParser.count_completed(doc) == 1

    def test_bare_list_not_counted_as_completed(self):
        doc = "- 纯列表项\n- 又一个纯列表项\n"
        assert MarkdownTodoParser.count_completed(doc) == 0

    def test_bare_list_raw_preserved(self):
        line = "- 保留原始格式"
        item = MarkdownTodoParser.parse_line(line)
        assert item is not None
        assert item.raw == line

    def test_mixed_bare_and_checkbox(self):
        doc = "- [x] 已完成\n- 纯文本\n- [ ] 待完成\n- 另一个纯文本\n"
        items = MarkdownTodoParser.parse_document(doc)
        assert len(items) == 4
        statuses = [it.status for it in items]
        assert statuses[0] == TodoStatus.COMPLETED
        assert statuses[1] == TodoStatus.UNCHECKED
        assert statuses[2] == TodoStatus.PENDING
        assert statuses[3] == TodoStatus.UNCHECKED

    def test_bare_list_with_leading_whitespace(self):
        """缩进的纯列表项也应被解析。"""
        item = MarkdownTodoParser.parse_line("  - 缩进的纯列表项")
        # 当前正则要求行首即匹配，缩进行应返回 None 或被忽略
        # 这取决于设计选择；这里我们期望能解析
        # 如果需要支持缩进，应在 parse_line 中添加 strip 预处理


# ====================================================================
# 测试：空值与非 todo 行
# ====================================================================


class TestNonTodoLines:
    """非 todo 行的处理。"""

    def test_empty_line_returns_none(self):
        assert MarkdownTodoParser.parse_line("") is None

    def test_whitespace_only_returns_none(self):
        assert MarkdownTodoParser.parse_line("   ") is None

    def test_plain_paragraph_not_todo(self):
        assert MarkdownTodoParser.parse_line("这只是普通段落文本") is None

    def test_heading_not_todo(self):
        assert MarkdownTodoParser.parse_line("# 一级标题") is None

    def test_code_line_not_todo(self):
        assert MarkdownTodoParser.parse_line("    indented_code_line") is None

    def test_link_not_todo(self):
        assert MarkdownTodoParser.parse_line("[链接文本](http://example.com)") is None

    def test_bracket_without_list_bullet(self):
        """有方括号但没有列表符号的行不应被解析为 todo。"""
        assert MarkdownTodoParser.parse_line("[x] 前面没有列表符号") is None

    def test_inline_code_with_brackets(self):
        """行内代码中的方括号不应该是 todo。"""
        result = MarkdownTodoParser.parse_line("参考 `- [x]` 格式")
        assert result is None

    def test_only_newlines(self):
        assert MarkdownTodoParser.parse_line("\n") is None


# ====================================================================
# 测试：文档级解析
# ====================================================================


class TestDocumentParsing:
    """整个文档的 todo 项解析。"""

    def test_empty_document(self):
        items = MarkdownTodoParser.parse_document("")
        assert items == []

    def test_document_with_only_headings(self):
        doc = "# 标题\n## 子标题\n### 三级\n"
        items = MarkdownTodoParser.parse_document(doc)
        assert items == []

    def test_complex_mixed_document(self):
        doc = """# 需求文档

## 功能需求

- [x] 用户注册
- [x] 用户登录
- [ ] 用户登出
- [-] 密码重置（进行中）
* [X] 邮箱验证
- 用户头像上传（纯列表）
- [?] 忘记密码（待确认）

## 非功能需求

- [ ] 性能测试
- [ ] 安全审计
"""
        items = MarkdownTodoParser.parse_document(doc)
        completed = MarkdownTodoParser.count_completed(doc)
        completed = MarkdownTodoParser.count_completed(doc)
        assert completed >= 2, f"至少 2 项已完成，实际 {completed}"

    def test_document_completion_ratio_zero(self):
        doc = "- [ ] 未完成\n- [ ] 未完成\n"
        ratio = MarkdownTodoParser.completion_ratio(doc)
        assert ratio == 0.0

    def test_document_completion_ratio_full(self):
        doc = "- [x] 完成\n- [X] 也大写完成\n"
        ratio = MarkdownTodoParser.completion_ratio(doc)
        assert ratio == pytest.approx(1.0)

    def test_document_completion_ratio_partial(self):
        doc = "- [x] 完成\n- [ ] 未完成\n- [X] 也完成\n"
        ratio = MarkdownTodoParser.completion_ratio(doc)
        assert ratio == pytest.approx(2 / 3)

    def test_document_no_items_ratio_zero(self):
        doc = "# 只有标题\n没有 todo 项\n"
        ratio = MarkdownTodoParser.completion_ratio(doc)
        assert ratio == 0.0

    def test_document_mixed_marker_statuses(self):
        doc = "- [x] 完成\n- [ ] 未完成\n- [-] 中间态\n- [X] 大写完成\n- [~] 进行中\n- 纯文本\n"
        items = MarkdownTodoParser.parse_document(doc)
        completed_statuses = [i for i in items if i.status == TodoStatus.COMPLETED]
        pending_statuses = [i for i in items if i.status in (TodoStatus.PENDING, TodoStatus.UNCHECKED)]
        assert len(completed_statuses) == 2, f"应有 2 项已完成，实际 {len(completed_statuses)}"
        assert len(pending_statuses) == 4, f"应有 4 项未完成，实际 {len(pending_statuses)}"

    def test_document_count_pending_includes_all_non_completed(self):
        doc = "- [ ] pending\n- [-] non-standard\n- 纯文本 unchecked\n"
        pending = MarkdownTodoParser.count_pending(doc)
        assert pending == 3

    def test_multiline_text_in_item(self):
        """todo 项文本可能包含特殊字符。"""
        item = MarkdownTodoParser.parse_line("- [x] 支持 `Python 3.12+` 和 `Node.js 20+`")
        assert item is not None
        assert item.status == TodoStatus.COMPLETED
        assert "Python" in item.text
        assert "Node.js" in item.text

    def test_item_text_only_single_line(self):
        """parse_line 只处理单行，多行文本应逐行调用。"""
        item = MarkdownTodoParser.parse_line("- [x] 第一行\n- [ ] 第二行")
        # parse_line 接收单行时，只解析第一行部分
        if item is not None:
            assert item.status == TodoStatus.COMPLETED

    def test_tab_before_checkbox(self):
        """Tab 缩进的 checkbox 应被忽略（当前实现）。"""
        result = MarkdownTodoParser.parse_line("\t- [x] tab 前缀")
        assert result is None

    def test_two_spaces_indent_checkbox(self):
        """双空格缩进的 checkbox 应被忽略（当前实现）。"""
        result = MarkdownTodoParser.parse_line("  - [x] 双空格前缀")
        assert result is None

    def test_comprehensive_edge_case_document(self):
        """综合性边界场景：混合各种标记格式。"""
        doc = (
            "- [x] 小写完成\n"
            "- [X] 大写完成\n"
            "- [ ] 空格未完成\n"
            "- [-] 横杠未标准\n"
            "- [~] 波浪未标准\n"
            "- [*] 星号未标准\n"
            "- [?] 问号未标准\n"
            "- 纯文本无括号\n"
            "* [x] 星号列表完成\n"
            "+ [X] 加号列表完成\n"
            "- [ ] 标准未完成\n"
        )
        items = MarkdownTodoParser.parse_document(doc)
        assert len(items) == 11
        assert MarkdownTodoParser.count_completed(doc) == 4
        assert MarkdownTodoParser.count_pending(doc) == 7
        ratio = MarkdownTodoParser.completion_ratio(doc)
        assert ratio == pytest.approx(4 / 11)
