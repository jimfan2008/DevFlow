import re
from typing import Dict, List, Tuple
import pytest


# ==================== Git Flow 分支规范验证 ====================

GIT_FLOW_MAIN_BRANCHES = {"main", "master", "develop"}

GIT_FLOW_MAIN_RE = re.compile(r"^(main|master|develop)$")
GIT_FLOW_TYPED_RE = re.compile(
    r"^(?P<prefix>feature|release|hotfix|bugfix|chore)::.+$"
)


def validate_branch_name(branch: str) -> Tuple[bool, str]:
    """验证分支名是否符合 Git Flow 规范。

    Returns:
        (is_valid, reason)
    """
    branch = branch.strip()
    if not branch:
        return False, "分支名不能为空"

    # 分支名必须全部为 ASCII 字符（不允许 emoji、中文等）
    try:
        branch.encode("ascii")
    except UnicodeEncodeError:
        return False, f"分支名包含非 ASCII 字符: {branch}"

    if GIT_FLOW_MAIN_RE.match(branch):
        return True, "主分支"

    m = GIT_FLOW_TYPED_RE.match(branch)
    if not m:
        return False, f"不符合 Git Flow 分支命名规则: {branch}"

    prefix = m.group("prefix")
    return True, f"{prefix} 分支"


def validate_branches(branch_names: List[str]) -> Dict[str, Dict]:
    """批量验证分支名，返回每个分支的验证结果。

    Returns:
        {branch: {"valid": bool, "reason": str}}
    """
    results = {}
    for b in branch_names:
        valid, reason = validate_branch_name(b)
        results[b] = {"valid": valid, "reason": reason}
    return results


def branch_compliance(branch_names: List[str]) -> float:
    """计算分支规范符合度百分比。"""
    if not branch_names:
        return 100.0
    valid_count = sum(1 for b in branch_names if validate_branch_name(b)[0])
    return round(valid_count / len(branch_names) * 100, 2)


# ==================== Conventional Commits 验证 ====================

CONVENTIONAL_COMMIT_PATTERN = re.compile(
    r"^(feat|fix|docs|style|refactor|test|chore|perf|ci|build|revert)"
    r"(\([a-z][a-z0-9-]*\))?"
    r"(!)?"
    r": [a-zA-Z].+"
)

CONVENTIONAL_TYPES = {
    "feat": "新功能",
    "fix": "修复bug",
    "docs": "文档变更",
    "style": "代码格式",
    "refactor": "代码重构",
    "test": "测试相关",
    "chore": "构建/辅助工具",
    "perf": "性能优化",
    "ci": "持续集成",
    "build": "构建系统",
    "revert": "撤销提交",
}


def validate_commit_message(commit_msg: str) -> Tuple[bool, str]:
    """验证单条 commit message 是否符合 Conventional Commits 规范。

    Returns:
        (is_valid, reason)
    """
    first_line = commit_msg.strip().split("\n")[0]

    if not first_line:
        return False, "commit message 不能为空"

    # 描述部分必须使用英文（ASCII），不允许 emoji、中文等
    try:
        first_line.encode("ascii")
    except UnicodeEncodeError:
        return False, f"commit message 包含非 ASCII 字符: {first_line}"

    m = CONVENTIONAL_COMMIT_PATTERN.match(first_line)
    if not m:
        return False, f"不符合 Conventional Commits 格式: {first_line}"

    commit_type = m.group(1)
    return True, f"类型为 {CONVENTIONAL_TYPES.get(commit_type, commit_type)}"


def validate_commits(commit_messages: List[str]) -> Dict[int, Dict]:
    """批量验证 commit messages，返回每个提交的验证结果。

    Returns:
        {index: {"valid": bool, "reason": str, "message": str}}
    """
    results = {}
    for i, msg in enumerate(commit_messages):
        valid, reason = validate_commit_message(msg)
        results[i] = {"valid": valid, "reason": reason, "message": msg.strip()}
    return results


def commit_compliance(commit_messages: List[str]) -> float:
    """计算提交规范符合度百分比。"""
    if not commit_messages:
        return 100.0
    valid_count = sum(1 for msg in commit_messages if validate_commit_message(msg)[0])
    return round(valid_count / len(commit_messages) * 100, 2)


# ==================== 集成验证 ====================

def full_compliance_report(
    branch_names: List[str],
    commit_messages: List[str],
) -> Dict:
    """生成完整的规范符合度报告。"""
    branch_score = branch_compliance(branch_names)
    commit_score = commit_compliance(commit_messages)

    branch_details = validate_branches(branch_names)
    commit_details = validate_commits(commit_messages)

    return {
        "branch_compliance": branch_score,
        "commit_compliance": commit_score,
        "branch_details": branch_details,
        "commit_details": commit_details,
        "overall_pass": branch_score == 100.0 and commit_score >= 95.0,
    }


# ==================== 测试：Git Flow 分支规范 ====================

class TestGitFlowBranchMainBranches:
    """验证主分支命名规范。"""

    def test_main_branch(self):
        valid, reason = validate_branch_name("main")
        assert valid is True
        assert reason == "主分支"

    def test_master_branch(self):
        valid, _ = validate_branch_name("master")
        assert valid is True

    def test_develop_branch(self):
        valid, _ = validate_branch_name("develop")
        assert valid is True

    def test_main_branch_with_whitespace(self):
        valid, _ = validate_branch_name("  main  ")
        assert valid is True

    def test_lowercase_main_only(self):
        """Main/Master/Develop 大小写必须全小写。"""
        assert validate_branch_name("Main")[0] is False
        assert validate_branch_name("MAIN")[0] is False
        assert validate_branch_name("Master")[0] is False
        assert validate_branch_name("Develop")[0] is False


class TestGitFlowFeatureBranches:
    """验证 feature 分支命名规范。"""

    def test_feature_branch_basic(self):
        valid, reason = validate_branch_name("feature::add-login")
        assert valid is True
        assert "feature" in reason

    def test_feature_branch_multiple_words(self):
        valid, _ = validate_branch_name("feature::user-authentication-module")
        assert valid is True

    def test_feature_branch_with_ticket_number(self):
        valid, _ = validate_branch_name("feature::PROJ-123-add-dashboard")
        assert valid is True

    def test_feature_branch_with_underscore(self):
        valid, _ = validate_branch_name("feature::add_new_feature")
        assert valid is True

    def test_feature_branch_without_double_colon(self):
        """斜杠分隔不合规，必须用 :: 。"""
        assert validate_branch_name("feature/add-login")[0] is False
        assert validate_branch_name("feature_add_login")[0] is False

    def test_feature_branch_empty_suffix(self):
        assert validate_branch_name("feature::")[0] is False

    def test_feature_branch_only_prefix(self):
        assert validate_branch_name("feature")[0] is False


class TestGitFlowReleaseBranches:
    """验证 release 分支命名规范。"""

    def test_release_branch_version(self):
        valid, reason = validate_branch_name("release::v1.0.0")
        assert valid is True
        assert "release" in reason

    def test_release_branch_semver(self):
        valid, _ = validate_branch_name("release::2.3.1")
        assert valid is True

    def test_release_branch_with_rc(self):
        valid, _ = validate_branch_name("release::v1.0.0-rc1")
        assert valid is True

    def test_release_branch_without_separator(self):
        assert validate_branch_name("release/v1.0.0")[0] is False
        assert validate_branch_name("release_v1.0.0")[0] is False

    def test_release_only_prefix(self):
        assert validate_branch_name("release")[0] is False


class TestGitFlowHotfixBranches:
    """验证 hotfix 分支命名规范。"""

    def test_hotfix_branch_basic(self):
        valid, _ = validate_branch_name("hotfix::critical-security-patch")
        assert valid is True

    def test_hotfix_branch_with_issue(self):
        valid, _ = validate_branch_name("hotfix::fix-issue-456")
        assert valid is True

    def test_hotfix_without_separator(self):
        assert validate_branch_name("hotfix/critical-patch")[0] is False

    def test_hotfix_only_prefix(self):
        assert validate_branch_name("hotfix")[0] is False


class TestGitFlowBugfixBranches:
    """验证 bugfix 分支命名规范。"""

    def test_bugfix_branch_basic(self):
        valid, reason = validate_branch_name("bugfix::null-pointer-in-parser")
        assert valid is True
        assert "bugfix" in reason

    def test_bugfix_with_ticket(self):
        valid, _ = validate_branch_name("bugfix::BUG-789-login-crash")
        assert valid is True

    def test_bugfix_without_separator(self):
        assert validate_branch_name("bugfix/null-pointer")[0] is False


class TestGitFlowChoreBranches:
    """验证 chore 分支命名规范。"""

    def test_chore_branch_deps(self):
        valid, _ = validate_branch_name("chore::upgrade-dependencies")
        assert valid is True

    def test_chore_branch_ci(self):
        valid, _ = validate_branch_name("chore::update-ci-config")
        assert valid is True

    def test_chore_without_separator(self):
        assert validate_branch_name("chore/upgrade-deps")[0] is False


class TestGitFlowInvalidBranches:
    """验证不合规的分支命名。"""

    def test_random_branch_name(self):
        assert validate_branch_name("random-name")[0] is False

    def test_empty_branch_name(self):
        assert validate_branch_name("")[0] is False

    def test_whitespace_only(self):
        assert validate_branch_name("   ")[0] is False

    def test_special_characters(self):
        assert validate_branch_name("feature@add-login")[0] is False

    def test_emoji_in_branch(self):
        assert validate_branch_name("feature::add-login-🚀")[0] is False

    def test_chinese_characters(self):
        assert validate_branch_name("feature::添加功能")[0] is False

    def test_uppercase_prefix(self):
        assert validate_branch_name("Feature::add-login")[0] is False
        assert validate_branch_name("RELEASE::v1.0")[0] is False


class TestBranchComplianceCalculation:
    """验证分支符合度计算。"""

    def test_all_valid_branches(self):
        branches = ["main", "develop", "feature::add-login", "release::v1.0.0"]
        assert branch_compliance(branches) == 100.0

    def test_all_invalid_branches(self):
        branches = ["random1", "random2"]
        assert branch_compliance(branches) == 0.0

    def test_mixed_branches(self):
        branches = ["main", "random-invalid", "feature::valid"]
        score = branch_compliance(branches)
        assert score == round(2 / 3 * 100, 2)

    def test_empty_list_returns_100(self):
        assert branch_compliance([]) == 100.0

    def test_single_valid(self):
        assert branch_compliance(["main"]) == 100.0

    def test_single_invalid(self):
        assert branch_compliance(["invalid-name"]) == 0.0


class TestValidateBranches:
    """验证批量分支验证函数。"""

    def test_returns_dict_with_all_branches(self):
        branches = ["main", "invalid", "feature::test"]
        results = validate_branches(branches)
        assert len(results) == 3
        assert "main" in results
        assert "invalid" in results
        assert "feature::test" in results

    def test_valid_branch_has_correct_structure(self):
        results = validate_branches(["main"])
        assert results["main"]["valid"] is True
        assert "reason" in results["main"]

    def test_invalid_branch_has_reason(self):
        results = validate_branches(["bad-name"])
        assert results["bad-name"]["valid"] is False
        assert results["bad-name"]["reason"] != ""


# ==================== 测试：Conventional Commits ====================

class TestConventionalCommitBasicTypes:
    """验证 Conventional Commits 基本类型。"""

    def test_feat_type(self):
        valid, reason = validate_commit_message("feat(auth): add JWT login")
        assert valid is True
        assert "新功能" in reason

    def test_fix_type(self):
        valid, _ = validate_commit_message("fix(api): handle 500 error")
        assert valid is True

    def test_docs_type(self):
        valid, reason = validate_commit_message("docs(api): update README")
        assert valid is True
        assert "文档变更" in reason

    def test_style_type(self):
        valid, _ = validate_commit_message("style(ui): format button component")
        assert valid is True

    def test_refactor_type(self):
        valid, reason = validate_commit_message("refactor(core): simplify request handler")
        assert valid is True
        assert "代码重构" in reason

    def test_test_type(self):
        valid, _ = validate_commit_message("test(parser): add unit tests")
        assert valid is True

    def test_chore_type(self):
        valid, reason = validate_commit_message("chore(deps): upgrade dependencies")
        assert valid is True
        assert "构建/辅助工具" in reason

    def test_perf_type(self):
        valid, _ = validate_commit_message("perf(db): optimize query execution")
        assert valid is True

    def test_ci_type(self):
        valid, reason = validate_commit_message("ci(docker): update pipeline config")
        assert valid is True
        assert "持续集成" in reason

    def test_build_type(self):
        valid, _ = validate_commit_message("build(webpack): update config")
        assert valid is True

    def test_revert_type(self):
        valid, reason = validate_commit_message("revert: revert last commit")
        assert valid is True
        assert "撤销提交" in reason


class TestConventionalCommitWithScope:
    """验证带 scope 的 commit。"""

    def test_scope_lowercase_alphanumeric(self):
        valid, _ = validate_commit_message("feat(auth): add login")
        assert valid is True

    def test_scope_with_hyphen(self):
        valid, _ = validate_commit_message("fix(user-auth): fix token expiry")
        assert valid is True

    def test_scope_with_number(self):
        valid, _ = validate_commit_message("feat(api2): add v2 endpoint")
        assert valid is True

    def test_scope_optional(self):
        """scope 是可选的。"""
        assert validate_commit_message("feat: add new feature")[0] is True
        assert validate_commit_message("feat(auth): add login")[0] is True

    def test_scope_uppercase_invalid(self):
        assert validate_commit_message("feat(AUTH): add login")[0] is False

    def test_scope_underscore_invalid(self):
        assert validate_commit_message("feat(user_auth): add login")[0] is False

    def test_scope_empty_parens_invalid(self):
        assert validate_commit_message("feat(): add login")[0] is False


class TestConventionalCommitBreakingChange:
    """验证破坏性变更标记。"""

    def test_breaking_change_with_exclamation(self):
        valid, _ = validate_commit_message("feat(auth)!: change token format")
        assert valid is True

    def test_breaking_change_with_scope_and_bang(self):
        valid, _ = validate_commit_message("fix(api)!: rename all endpoints")
        assert valid is True

    def test_bang_must_be_before_colon(self):
        assert validate_commit_message("feat(auth):! change format")[0] is False


class TestConventionalCommitInvalid:
    """验证不合规的 commit message。"""

    def test_empty_message(self):
        assert validate_commit_message("")[0] is False

    def test_only_whitespace(self):
        assert validate_commit_message("   ")[0] is False

    def test_missing_type(self):
        assert validate_commit_message("(auth): add login")[0] is False

    def test_missing_colon(self):
        assert validate_commit_message("feat(auth) add login")[0] is False

    def test_no_space_after_colon(self):
        assert validate_commit_message("feat(auth):add login")[0] is False

    def test_missing_description(self):
        assert validate_commit_message("feat(auth):")[0] is False

    def test_description_space_only(self):
        assert validate_commit_message("feat(auth): ")[0] is False

    def test_unknown_type(self):
        assert validate_commit_message("wip(auth): work in progress")[0] is False

    def test_emoji_in_message(self):
        assert validate_commit_message("feat(auth): add login 🚀")[0] is False

    def test_chinese_only_message(self):
        assert validate_commit_message("feat(auth): 添加登录功能")[0] is False

    def test_uppercase_type(self):
        assert validate_commit_message("FEAT(auth): add login")[0] is False

    def test_natural_language_message(self):
        assert validate_commit_message("added new feature for login")[0] is False


class TestConventionalCommitMultiline:
    """验证多行 commit message。"""

    def test_multiline_with_body(self):
        msg = "feat(auth): add JWT login\n\nThis adds JWT-based authentication."
        assert validate_commit_message(msg)[0] is True

    def test_multiline_with_footer(self):
        msg = "fix(api): handle timeout\n\nFix connection timeout.\n\nCloses #123"
        assert validate_commit_message(msg)[0] is True

    def test_only_body_no_first_line(self):
        msg = "\n\nThis is only a body."
        assert validate_commit_message(msg)[0] is False


class TestCommitComplianceCalculation:
    """验证提交符合度计算。"""

    def test_all_valid_commits(self):
        commits = [
            "feat(auth): add login",
            "fix(api): handle timeout",
            "docs: update README",
        ]
        assert commit_compliance(commits) == 100.0

    def test_all_invalid_commits(self):
        commits = ["random message", "another random"]
        assert commit_compliance(commits) == 0.0

    def test_95_percent_threshold(self):
        commits = ["feat(auth): add login", "fix(api): handle timeout", "invalid msg"]
        score = commit_compliance(commits)
        assert score == round(2 / 3 * 100, 2)
        assert score < 95.0

    def test_meets_95_threshold(self):
        """20个中有19个合规，符合>=95%。"""
        valid = [f"feat(scope{i}): description{i}" for i in range(19)]
        commits = valid + ["invalid message"]
        score = commit_compliance(commits)
        assert score >= 95.0

    def test_empty_list_returns_100(self):
        assert commit_compliance([]) == 100.0

    def test_single_valid_commit(self):
        assert commit_compliance(["feat(auth): add login"]) == 100.0

    def test_single_invalid_commit(self):
        assert commit_compliance(["random message"]) == 0.0


class TestValidateCommits:
    """验证批量 commit 验证函数。"""

    def test_returns_dict_with_all_commits(self):
        commits = ["feat(auth): login", "invalid", "fix(api): timeout"]
        results = validate_commits(commits)
        assert len(results) == 3
        assert 0 in results
        assert 1 in results
        assert 2 in results

    def test_result_contains_message(self):
        msg = "feat(auth): add login"
        results = validate_commits([msg])
        assert results[0]["message"] == msg
        assert results[0]["valid"] is True

    def test_result_contains_reason(self):
        results = validate_commits(["feat(auth): login"])
        assert "reason" in results[0]


# ==================== 测试：集成验证 ====================

class TestFullComplianceReport:
    """验证完整的规范符合度报告。"""

    def test_all_pass_scenario(self):
        branches = ["main", "develop", "feature::add-login"]
        commits = [
            "feat(auth): add login page",
            "feat(auth): add registration",
            "fix(auth): handle validation errors",
            "test(auth): add e2e tests",
        ]
        report = full_compliance_report(branches, commits)
        assert report["branch_compliance"] == 100.0
        assert report["commit_compliance"] == 100.0
        assert report["overall_pass"] is True

    def test_branch_fail_scenario(self):
        """分支不符合导致整体不过。"""
        branches = ["main", "invalid-branch"]
        commits = ["feat(auth): add login"]
        report = full_compliance_report(branches, commits)
        assert report["branch_compliance"] < 100.0
        assert report["overall_pass"] is False

    def test_commit_low_compliance(self):
        """提交符合度低于95%导致整体不过。"""
        branches = ["main", "feature::test"]
        commits = ["feat(auth): login", "invalid message"]
        report = full_compliance_report(branches, commits)
        assert report["branch_compliance"] == 100.0
        assert report["commit_compliance"] == 50.0
        assert report["overall_pass"] is False

    def test_just_passes_threshold(self):
        """刚好满足 100% 分支 + >=95% 提交。"""
        branches = ["main", "develop"]
        commits = [f"feat(scope{i}): desc{i}" for i in range(20)]
        report = full_compliance_report(branches, commits)
        assert report["overall_pass"] is True

    def test_report_contains_details(self):
        branches = ["main", "feature::test"]
        commits = ["feat(auth): login", "fix(api): timeout"]
        report = full_compliance_report(branches, commits)
        assert "branch_details" in report
        assert "commit_details" in report
        assert len(report["branch_details"]) == 2
        assert len(report["commit_details"]) == 2

    def test_empty_input(self):
        """空输入返回全部通过。"""
        report = full_compliance_report([], [])
        assert report["branch_compliance"] == 100.0
        assert report["commit_compliance"] == 100.0
        assert report["overall_pass"] is True


class TestAcceptanceCriteria:
    """验收标准：分支规范符合度=100%，提交规范符合度>=95%。"""

    def test_happy_path_realistic_project(self):
        """模拟真实项目的分支和提交。"""
        branches = [
            "main",
            "develop",
            "feature::user-authentication",
            "feature::payment-gateway",
            "release::v2.0.0",
            "hotfix::critical-security-patch",
        ]
        commits = [
            "feat(auth): implement OAuth2 login",
            "feat(auth): add token refresh",
            "feat(payment): integrate Stripe API",
            "fix(auth): handle expired tokens",
            "tests(auth): add login tests",
            "docs(api): update authentication guide",
            "chore(deps): update dependencies",
            "refactor(auth): extract validation logic",
            "perf(api): optimize database queries",
            "ci(docker): update CI pipeline",
            "feat(payment): add refund support",
            "fix(payment): handle currency conversion",
            "docs(payment): add payment documentation",
            "test(payment): add edge case tests",
            "style(ui): format payment components",
            "feat(auth): add 2FA support",
            "fix(ui): mobile responsive issues",
            "chore(docs): update changelog",
            "perf(auth): cache user sessions",
            "build(webpack): update config",
        ]
        report = full_compliance_report(branches, commits)
        assert report["branch_compliance"] == 100.0, "分支规范符合度必须为100%"
        assert report["commit_compliance"] >= 95.0, "提交规范符合度必须>=95%"
        assert report["overall_pass"] is True

    def test_fail_branch_not_100(self):
        """分支有不合规时，即使提交100%也判定失败。"""
        branches = ["main", "random-branch"]
        commits = [f"feat(scope{i}): desc{i}" for i in range(20)]
        report = full_compliance_report(branches, commits)
        assert report["overall_pass"] is False

    def test_fail_commit_below_95(self):
        """提交符合度<95%时判定失败。"""
        branches = ["main", "develop", "feature::test"]
        commits = [
            "feat(auth): login",
            "fix(api): timeout",
            "invalid commit message",
        ]
        report = full_compliance_report(branches, commits)
        assert report["commit_compliance"] < 95.0
        assert report["overall_pass"] is False

    def test_boundary_exactly_95(self):
        """恰好95%的边界情况。"""
        branches = ["main"]
        valid_commits = [f"feat(s{i}): d{i}" for i in range(19)]
        commits = valid_commits + ["invalid"]
        report = full_compliance_report(branches, commits)
        assert report["commit_compliance"] == round(19 / 20 * 100, 2)
        assert report["commit_compliance"] >= 95.0
        assert report["overall_pass"] is True

    def test_boundary_below_95(self):
        """少于95%的情况。"""
        branches = ["main"]
        valid_commits = [f"feat(s{i}): d{i}" for i in range(18)]
        commits = valid_commits + ["invalid1", "invalid2"]
        report = full_compliance_report(branches, commits)
        assert report["commit_compliance"] == round(18 / 20 * 100, 2)
        assert report["commit_compliance"] < 95.0
        assert report["overall_pass"] is False
