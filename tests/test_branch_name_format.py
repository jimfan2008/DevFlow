import re
import pytest

BRANCH_REGEX = re.compile(r"^feature/[0-9]+-[a-zA-Z0-9_-]+$")


def test_branch_name_matches_feature_format():
    assert BRANCH_REGEX.match("feature/3-requirements")


def test_branch_name_with_numbers_in_name():
    assert BRANCH_REGEX.match("feature/1-login2")


def test_branch_name_with_underscore_in_name():
    assert BRANCH_REGEX.match("feature/5-user_profile")


def test_branch_name_with_hyphen_in_name():
    assert BRANCH_REGEX.match("feature/2-api-v2")


def test_branch_name_multiple_digits_step():
    assert BRANCH_REGEX.match("feature/123-data_sync_v3")


@pytest.mark.parametrize("invalid_branch", [
    "main",
    "feature/3",
    "feature/-fix",
    "feature/3fix",
    "bugfix/3-fix",
    "Feature/3-fix",
    "feature/3/",
    "feature/3-fix!",
    "feature/3.1-fix",
    "",
])
def test_branch_name_rejects_invalid_formats(invalid_branch):
    assert not BRANCH_REGEX.match(invalid_branch)


def test_regex_pattern_is_correct():
    expected = r"^feature/[0-9]+-[a-zA-Z0-9_-]+$"
    assert BRANCH_REGEX.pattern == expected
