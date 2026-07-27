import re
import pytest


COMMIT_MSG_PATTERN = re.compile(r"^(feat|fix|docs|style|refactor|test|chore)\([a-z-]+\): .+")


def _validate_first_line(commit_message: str) -> bool:
    """Validate the first line of a commit message matches the required format."""
    first_line = commit_message.strip().split("\n")[0]
    return bool(COMMIT_MSG_PATTERN.match(first_line))


class TestCommitMessageFirstLineFormat:
    """验证 commit message 首行符合 '类型(范围): 描述' 格式。"""

    # -- 合法 case --

    def test_valid_feat_type(self):
        msg = "feat(parser): add SRS parsing logic"
        assert _validate_first_line(msg) is True

    def test_valid_fix_type(self):
        msg = "fix(auth): resolve token expiration issue"
        assert _validate_first_line(msg) is True

    def test_valid_docs_type(self):
        msg = "docs(api): update endpoint documentation"
        assert _validate_first_line(msg) is True

    def test_valid_style_type(self):
        msg = "style(ui): format button component"
        assert _validate_first_line(msg) is True

    def test_valid_refactor_type(self):
        msg = "refactor(core): simplify request handler"
        assert _validate_first_line(msg) is True

    def test_valid_test_type(self):
        msg = "test(parser): add unit tests for tokenizer"
        assert _validate_first_line(msg) is True

    def test_valid_chore_type(self):
        msg = "chore(deps): upgrade dependencies to latest"
        assert _validate_first_line(msg) is True

    def test_valid_scope_with_hyphen(self):
        msg = "feat(user-auth): implement OAuth2 login flow"
        assert _validate_first_line(msg) is True

    def test_valid_multiline_commit(self):
        msg = "feat(api): add rate limiting\n\nThis adds rate limiting to all endpoints."
        assert _validate_first_line(msg) is True

    def test_valid_with_leading_whitespace(self):
        msg = "  fix(db): handle connection timeout  "
        assert _validate_first_line(msg) is True

    # -- 非法 case --

    def test_invalid_unknown_type(self):
        msg = "wip(parser): work in progress"
        assert _validate_first_line(msg) is False

    def test_invalid_missing_scope(self):
        msg = "feat: add new feature"
        assert _validate_first_line(msg) is False

    def test_invalid_empty_scope(self):
        msg = "feat(): add new feature"
        assert _validate_first_line(msg) is False

    def test_invalid_scope_uppercase(self):
        msg = "feat(_PARSER_): add parsing logic"
        assert _validate_first_line(msg) is False

    def test_invalid_scope_with_underscore(self):
        msg = "feat(user_auth): add auth logic"
        assert _validate_first_line(msg) is False

    def test_invalid_missing_colon(self):
        msg = "feat(parser) add parsing logic"
        assert _validate_first_line(msg) is False

    def test_invalid_no_space_after_colon(self):
        msg = "feat(parser):add parsing logic"
        assert _validate_first_line(msg) is False

    def test_invalid_empty_message(self):
        msg = ""
        assert _validate_first_line(msg) is False

    def test_invalid_only_multiline_no_first(self):
        msg = "\n\nbody without first line"
        assert _validate_first_line(msg) is False

    def test_invalid_scope_contains_number(self):
        msg = "feat(parser2): add parsing logic"
        assert _validate_first_line(msg) is False

    def test_invalid_missing_description(self):
        msg = "feat(parser):"
        assert _validate_first_line(msg) is False

    def test_invalid_missing_description_with_space_only(self):
        msg = "feat(parser): "
        assert _validate_first_line(msg) is False

    # -- 边界 case --

    def test_valid_minimal_description(self):
        msg = "fix(a): x"
        assert _validate_first_line(msg) is True

    def test_valid_long_scope(self):
        msg = "feat(very-long-scope-name-here): describe the change"
        assert _validate_first_line(msg) is True

    def test_valid_conventional_types_exhaustive(self):
        """遍历所有允许的类型，逐一验证。"""
        allowed_types = ["feat", "fix", "docs", "style", "refactor", "test", "chore"]
        for t in allowed_types:
            msg = f"{t}(scope): some description"
            assert _validate_first_line(msg) is True, f"Type '{t}' should be valid"
