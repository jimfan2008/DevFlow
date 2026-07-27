import pytest
import re


# ==================== Branch Validation ====================

BRANCH_PATTERNS = {
    "main": re.compile(r"^main$"),
    "master": re.compile(r"^master$"),
    "develop": re.compile(r"^develop$"),
    "feature": re.compile(r"^feature/[a-zA-Z0-9][a-zA-Z0-9_-]*(?:::.+)$"),
    "release": re.compile(r"^release/v?\d+(\.\d+)+(-[a-zA-Z0-9.]+)?$"),
    "hotfix": re.compile(r"^hotfix/[a-zA-Z0-9][a-zA-Z0-9_-]+$"),
    "bugfix": re.compile(r"^bugfix/[a-zA-Z0-9][a-zA-Z0-9_-]+$"),
    "chore": re.compile(r"^chore/[a-zA-Z0-9][a-zA-Z0-9_-]+$"),
}


def validate_branch_name(branch: str) -> dict:
    if not branch or not isinstance(branch, str) or not branch.strip():
        return {"branch": branch, "valid": False, "type": None, "reason": "空或无效分支名"}
    if not all(c.isascii() and (c.isalnum() or c in "-_/:.") for c in branch):
        return {"branch": branch, "valid": False, "type": None, "reason": "分支名包含非法字符"}
    for branch_type, pattern in BRANCH_PATTERNS.items():
        if pattern.match(branch):
            return {"branch": branch, "valid": True, "type": branch_type, "reason": None}
    return {"branch": branch, "valid": False, "type": None, "reason": f"不符合任何已知的Git Flow命名规范"}


def validate_branches(branches: list) -> dict:
    results = {}
    for b in branches:
        results[b] = validate_branch_name(b)
    return results


def calculate_branch_compliance(branches: list) -> float:
    if not branches:
        return 100.0
    valid_count = sum(1 for b in branches if validate_branch_name(b)["valid"])
    return (valid_count / len(branches)) * 100


# ==================== Commit Message Validation ====================

ALLOWED_TYPES = [
    "feat", "fix", "docs", "style", "refactor", "test",
    "chore", "perf", "ci", "build", "revert",
]

COMMIT_MSG_RE = re.compile(
    r"^(?P<type>" + "|".join(ALLOWED_TYPES) + r")"
    r"(?:\((?P<scope>[a-z0-9-]+)\))?"
    r"(?P<bang>!)?"
    r": (?P<description>[a-z].{0,72})$"
)


def _is_ascii_printable(s: str) -> bool:
    return all(c.isascii() and c.isprintable() for c in s)


def validate_commit_message(message: str) -> dict:
    if not message or not isinstance(message, str) or not message.strip():
        return {"message": message, "valid": False, "reason": "空或无效提交信息"}
    first_line = message.strip().split("\n")[0]
    if not _is_ascii_printable(first_line):
        return {"message": message, "valid": False, "reason": "提交信息首行包含非ASCII字符或纯空格"}
    m = COMMIT_MSG_RE.match(first_line)
    if not m:
        # Determine specific reason
        if not re.match(r"^[a-z]+", first_line):
            return {"message": message, "valid": False, "reason": "缺少有效的提交类型前缀"}
        if ":" not in first_line:
            return {"message": message, "valid": False, "reason": "缺少冒号分隔符"}
        if re.match(r"^[a-z]+\([^)]*([^a-z0-9-].*)\)", first_line):
            return {"message": message, "valid": False, "reason": "作用域包含非法字符"}
        type_match = re.match(r"^([a-z]+)", first_line)
        if type_match and type_match.group(1) not in ALLOWED_TYPES:
            return {"message": message, "valid": False, "reason": f"未知提交类型: {type_match.group(1)}"}
        if re.match(r"^[a-z]+\([^)]+\)?:$", first_line):
            return {"message": message, "valid": False, "reason": "缺少提交描述"}
        if re.match(r"^[a-z]+\([^)]+\)?:(?![ ]) ", first_line) and not re.match(r"^[a-z]+\([^)]+\)?:(?![ ])", first_line):
            return {"message": message, "valid": False, "reason": "冒号后缺少空格"}
        return {"message": message, "valid": False, "reason": "不符合 Conventional Commits 格式"}
    return {"message": message, "valid": True, "type": m.group("type"), "scope": m.group("scope"), "reason": None}


def validate_commits(messages: list) -> dict:
    return {msg: validate_commit_message(msg) for msg in messages}


def calculate_commit_compliance(messages: list) -> float:
    if not messages:
        return 100.0
    valid_count = sum(1 for m in messages if validate_commit_message(m)["valid"])
    return (valid_count / len(messages)) * 100


# ==================== Compliance Report ====================

def generate_compliance_report(branches: list, commits: list) -> dict:
    branch_compliance = calculate_branch_compliance(branches)
    commit_compliance = calculate_commit_compliance(commits)
    branch_details = validate_branches(branches) if branches else {}
    commit_details = validate_commits(commits) if commits else {}
    branch_invalid = {b: r for b, r in branch_details.items() if not r["valid"]}
    commit_invalid = {m: r for m, r in commit_details.items() if not r["valid"]}
    return {
        "branch_compliance": branch_compliance,
        "commit_compliance": commit_compliance,
        "branch_pass": branch_compliance == 100.0,
        "commit_pass": commit_compliance >= 95.0,
        "overall_pass": branch_compliance == 100.0 and commit_compliance >= 95.0,
        "invalid_branches": branch_invalid,
        "invalid_commits": commit_invalid,
        "branch_details": branch_details,
        "commit_details": commit_details,
    }


# ==================== Tests: Main Branches ====================

class TestGitFlowMainBranches:
    def test_main_branch(self):
        assert validate_branch_name("main")["valid"] is True
        assert validate_branch_name("main")["type"] == "main"

    def test_master_branch(self):
        assert validate_branch_name("master")["valid"] is True
        assert validate_branch_name("master")["type"] == "master"

    def test_develop_branch(self):
        assert validate_branch_name("develop")["valid"] is True
        assert validate_branch_name("develop")["type"] == "develop"

    def test_main_branch_with_whitespace(self):
        assert validate_branch_name("main ")["valid"] is False

    def test_lowercase_main_only(self):
        assert validate_branch_name("Main")["valid"] is False
        assert validate_branch_name("MAIN")["valid"] is False


# ==================== Tests: Feature Branches ====================

class TestGitFlowFeatureBranches:
    def test_feature_branch_basic(self):
        assert validate_branch_name("feature/auth::login-page")["valid"] is True

    def test_feature_branch_multiple_words(self):
        assert validate_branch_name("feature/ui::dashboard-redesign")["valid"] is True

    def test_feature_branch_with_ticket_number(self):
        assert validate_branch_name("feature/PROJ123::add-payout")["valid"] is True

    def test_feature_branch_with_underscore(self):
        assert validate_branch_name("feature/auth_login::page")["valid"] is True

    def test_feature_branch_without_triple_colon(self):
        assert validate_branch_name("feature/login-page")["valid"] is False

    def test_feature_branch_empty_suffix(self):
        assert validate_branch_name("feature/auth::")["valid"] is False

    def test_feature_branch_only_prefix(self):
        assert validate_branch_name("feature/")["valid"] is False


# ==================== Tests: Release Branches ====================

class TestGitFlowReleaseBranches:
    def test_release_branch_version(self):
        assert validate_branch_name("release/1.0")["valid"] is True

    def test_release_branch_semver(self):
        assert validate_branch_name("release/v2.3.1")["valid"] is True

    def test_release_branch_with_rc(self):
        assert validate_branch_name("release/1.0.0-rc1")["valid"] is True

    def test_release_branch_without_separator(self):
        assert validate_branch_name("release1.0")["valid"] is False

    def test_release_only_prefix(self):
        assert validate_branch_name("release/")["valid"] is False


# ==================== Tests: Hotfix Branches ====================

class TestGitFlowHotfixBranches:
    def test_hotfix_branch_basic(self):
        assert validate_branch_name("hotfix/security-patch")["valid"] is True

    def test_hotfix_with_issue(self):
        assert validate_branch_name("hotfix/ISSUE-42")["valid"] is True

    def test_hotfix_without_separator(self):
        assert validate_branch_name("hotfixsecurity-patch")["valid"] is False

    def test_hotfix_only_prefix(self):
        assert validate_branch_name("hotfix/")["valid"] is False


# ==================== Tests: Bugfix Branches ====================

class TestGitFlowBugfixBranches:
    def test_bugfix_branch_basic(self):
        assert validate_branch_name("bugfix/login-crash")["valid"] is True

    def test_bugfix_with_ticket(self):
        assert validate_branch_name("bugfix/BG-123")["valid"] is True

    def test_bugfix_without_separator(self):
        assert validate_branch_name("bugfixlogin-crash")["valid"] is False


# ==================== Tests: Chore Branches ====================

class TestGitFlowChoreBranches:
    def test_chore_branch_deps(self):
        assert validate_branch_name("chore/upgrade-deps")["valid"] is True

    def test_chore_branch_ci(self):
        assert validate_branch_name("chore/ci-pipeline")["valid"] is True

    def test_chore_without_separator(self):
        assert validate_branch_name("choreupgrade-deps")["valid"] is False


# ==================== Tests: Invalid Branches ====================

class TestGitFlowInvalidBranches:
    def test_random_branch_name(self):
        assert validate_branch_name("my-random-branch")["valid"] is False

    def test_empty_branch_name(self):
        assert validate_branch_name("")["valid"] is False
        assert validate_branch_name(None)["valid"] is False

    def test_whitespace_only(self):
        assert validate_branch_name("   ")["valid"] is False

    def test_special_characters(self):
        assert validate_branch_name("feature/login@page")["valid"] is False

    def test_emoji_in_branch(self):
        assert validate_branch_name("feature/login-page")["valid"] is False

    def test_chinese_characters(self):
        assert validate_branch_name("功能/登录页面")["valid"] is False

    def test_uppercase_prefix(self):
        assert validate_branch_name("Feature/login::page")["valid"] is False


# ==================== Tests: Branch Compliance Calculation ====================

class TestBranchComplianceCalculation:
    def test_all_valid_branches(self):
        branches = ["main", "develop", "feature/auth::login", "hotfix/fix-x"]
        assert calculate_branch_compliance(branches) == 100.0

    def test_all_invalid_branches(self):
        branches = ["random", "feature/", "BUG"]
        assert calculate_branch_compliance(branches) == 0.0

    def test_mixed_branches(self):
        branches = ["main", "bad_name", "feature/ui::test"]
        result = calculate_branch_compliance(branches)
        assert abs(result - 66.67) < 0.1

    def test_empty_list_returns_100(self):
        assert calculate_branch_compliance([]) == 100.0

    def test_single_valid(self):
        assert calculate_branch_compliance(["main"]) == 100.0

    def test_single_invalid(self):
        assert calculate_branch_compliance(["random-name"]) == 0.0


# ==================== Tests: Validate Branches ====================

class TestValidateBranches:
    def test_returns_dict_with_all_branches(self):
        branches = ["main", "invalid", "feature/auth::login"]
        result = validate_branches(branches)
        assert len(result) == 3
        assert "main" in result
        assert "invalid" in result

    def test_valid_branch_has_correct_structure(self):
        result = validate_branch_name("main")
        assert "branch" in result
        assert "valid" in result
        assert "type" in result
        assert result["valid"] is True

    def test_invalid_branch_has_reason(self):
        result = validate_branch_name("invalid-branch")
        assert result["valid"] is False
        assert result["reason"] is not None


# ==================== Tests: Conventional Commit Basic Types ====================

class TestConventionalCommitBasicTypes:
    def test_feat_type(self):
        result = validate_commit_message("feat: add user login")
        assert result["valid"] is True
        assert result["type"] == "feat"

    def test_fix_type(self):
        result = validate_commit_message("fix: resolve null pointer")
        assert result["valid"] is True

    def test_docs_type(self):
        assert validate_commit_message("docs: update readme")["valid"] is True

    def test_style_type(self):
        assert validate_commit_message("style: fix formatting")["valid"] is True

    def test_refactor_type(self):
        assert validate_commit_message("refactor: simplify auth logic")["valid"] is True

    def test_test_type(self):
        assert validate_commit_message("test: add unit tests")["valid"] is True

    def test_chore_type(self):
        assert validate_commit_message("chore: update dependencies")["valid"] is True

    def test_perf_type(self):
        assert validate_commit_message("perf: optimize database query")["valid"] is True

    def test_ci_type(self):
        assert validate_commit_message("ci: add github actions")["valid"] is True

    def test_build_type(self):
        assert validate_commit_message("build: update webpack config")["valid"] is True

    def test_revert_type(self):
        assert validate_commit_message("revert: undo last commit")["valid"] is True


# ==================== Tests: Commit With Scope ====================

class TestConventionalCommitWithScope:
    def test_scope_lowercase_alphanumeric(self):
        assert validate_commit_message("feat(auth): add login")["valid"] is True

    def test_scope_with_hyphen(self):
        assert validate_commit_message("fix(user-profile): fix avatar")["valid"] is True

    def test_scope_with_number(self):
        assert validate_commit_message("feat(api2): new endpoint")["valid"] is True

    def test_scope_optional(self):
        assert validate_commit_message("feat: new feature")["valid"] is True

    def test_scope_uppercase_invalid(self):
        assert validate_commit_message("feat(Auth): add login")["valid"] is False

    def test_scope_underscore_invalid(self):
        assert validate_commit_message("feat(auth_module): add login")["valid"] is False

    def test_scope_empty_parens_invalid(self):
        assert validate_commit_message("feat(): add login")["valid"] is False


# ==================== Tests: Breaking Changes ====================

class TestConventionalCommitBreakingChange:
    def test_breaking_change_with_exclamation(self):
        assert validate_commit_message("feat!: remove old api")["valid"] is True

    def test_breaking_change_with_scope_and_bang(self):
        assert validate_commit_message("feat(api)!: remove endpoint")["valid"] is True

    def test_bang_must_be_before_colon(self):
        assert validate_commit_message("feat:!remove api")["valid"] is False


# ==================== Tests: Invalid Commit Messages ====================

class TestConventionalCommitInvalid:
    def test_empty_message(self):
        assert validate_commit_message("")["valid"] is False
        assert validate_commit_message(None)["valid"] is False

    def test_only_whitespace(self):
        assert validate_commit_message("   ")["valid"] is False

    def test_missing_type(self):
        assert validate_commit_message(": add feature")["valid"] is False

    def test_missing_colon(self):
        assert validate_commit_message("feat add feature")["valid"] is False

    def test_no_space_after_colon(self):
        assert validate_commit_message("feat:add feature")["valid"] is False

    def test_missing_description(self):
        assert validate_commit_message("feat: ")["valid"] is False

    def test_description_space_only(self):
        assert validate_commit_message("feat:    ")["valid"] is False

    def test_unknown_type(self):
        assert validate_commit_message("xyz: add feature")["valid"] is False

    def test_emoji_in_message(self):
        assert validate_commit_message("feat: add fe\u2764\ufe0fture")["valid"] is False

    def test_chinese_only_message(self):
        assert validate_commit_message("新增功能")["valid"] is False

    def test_uppercase_type(self):
        assert validate_commit_message("Feat: add feature")["valid"] is False

    def test_natural_language_message(self):
        assert validate_commit_message("I fixed the bug today")["valid"] is False


# ==================== Tests: Multiline Messages ====================

class TestConventionalCommitMultiline:
    def test_multiline_with_body(self):
        msg = "feat: add login\n\nThis adds a login page with OAuth."
        assert validate_commit_message(msg)["valid"] is True

    def test_multiline_with_footer(self):
        msg = "fix: resolve crash\n\nBody text.\n\nCloses #42"
        assert validate_commit_message(msg)["valid"] is True

    def test_only_body_no_first_line(self):
        assert validate_commit_message("\n\nSome body text")["valid"] is False


# ==================== Tests: Commit Compliance Calculation ====================

class TestCommitComplianceCalculation:
    def test_all_valid_commits(self):
        commits = ["feat: login", "fix: crash", "docs: readme"]
        assert calculate_commit_compliance(commits) == 100.0

    def test_all_invalid_commits(self):
        commits = ["random message", "another bad one"]
        assert calculate_commit_compliance(commits) == 0.0

    def test_95_percent_threshold(self):
        valid = ["feat: a", "feat: b", "feat: c", "feat: d", "feat: e",
                 "feat: f", "feat: g", "feat: h", "feat: i", "feat: j"]
        invalid = ["bad message"]
        result = calculate_commit_compliance(valid + invalid)
        assert result < 95.0

    def test_meets_95_threshold(self):
        valid = ["feat: a", "feat: b", "feat: c", "feat: d", "feat: e",
                 "feat: f", "feat: g", "feat: h", "feat: i", "feat: j",
                 "fix: k", "fix: l", "fix: m", "fix: n", "fix: o",
                 "docs: p", "docs: q", "docs: r", "docs: s", "docs: t",
                 "chore: u", "chore: v", "chore: w", "chore: x", "chore: y",
                 "test: z1", "test: z2", "test: z3", "test: z4", "test: z5",
                 "style: aa", "refactor: bb", "perf: cc", "ci: dd", "build: ee",
                 "revert: ff1", "revert: ff2", "revert: ff3", "revert: ff4", "revert: ff5",
                 "feat: gg1", "feat: gg2", "feat: gg3", "feat: gg4", "feat: gg5",
                 "fix: hh1", "fix: hh2", "fix: hh3", "fix: hh4", "fix: hh5",
                 "docs: ii1", "docs: ii2"]
        invalid = ["bad one"]
        result = calculate_commit_compliance(valid + invalid)
        assert result >= 95.0

    def test_empty_list_returns_100(self):
        assert calculate_commit_compliance([]) == 100.0

    def test_single_valid_commit(self):
        assert calculate_commit_compliance(["feat: one"]) == 100.0

    def test_single_invalid_commit(self):
        assert calculate_commit_compliance(["bad"]) == 0.0


# ==================== Tests: Validate Commits ====================

class TestValidateCommits:
    def test_returns_dict_with_all_commits(self):
        commits = ["feat: login", "bad message"]
        result = validate_commits(commits)
        assert len(result) == 2
        assert "feat: login" in result
        assert "bad message" in result

    def test_result_contains_message(self):
        result = validate_commit_message("feat: login")
        assert result["message"] == "feat: login"

    def test_result_contains_reason(self):
        result = validate_commit_message("bad")
        assert result["reason"] is not None


# ==================== Tests: Full Compliance Report ====================

class TestFullComplianceReport:
    def test_all_pass_scenario(self):
        branches = ["main", "develop", "feature/auth::login"]
        commits = ["feat: login", "fix: crash", "docs: readme"]
        report = generate_compliance_report(branches, commits)
        assert report["overall_pass"] is True
        assert report["branch_compliance"] == 100.0
        assert report["commit_compliance"] == 100.0

    def test_branch_fail_scenario(self):
        branches = ["main", "invalid-branch"]
        commits = ["feat: login", "fix: crash"]
        report = generate_compliance_report(branches, commits)
        assert report["overall_pass"] is False
        assert report["branch_pass"] is False

    def test_commit_low_compliance(self):
        branches = ["main", "develop"]
        commits = ["feat: a", "bad message"]
        report = generate_compliance_report(branches, commits)
        assert report["overall_pass"] is False
        assert report["commit_pass"] is False

    def test_just_passes_threshold(self):
        branches = ["main", "develop"]
        valid_commits = [f"feat: item{i}" for i in range(19)]
        commits = valid_commits + ["bad one"]
        report = generate_compliance_report(branches, commits)
        assert report["commit_compliance"] >= 95.0
        assert report["overall_pass"] is True

    def test_report_contains_details(self):
        branches = ["main", "invalid"]
        commits = ["feat: a", "bad"]
        report = generate_compliance_report(branches, commits)
        assert len(report["invalid_branches"]) == 1
        assert len(report["invalid_commits"]) == 1

    def test_empty_input(self):
        report = generate_compliance_report([], [])
        assert report["overall_pass"] is True
        assert report["branch_compliance"] == 100.0
        assert report["commit_compliance"] == 100.0


# ==================== Tests: Acceptance Criteria ====================

class TestAcceptanceCriteria:
    def test_happy_path_realistic_project(self):
        branches = [
            "main", "develop",
            "feature/auth::login", "feature/ui::dashboard",
            "release/1.0", "hotfix/security-fix", "bugfix/crash-fix",
        ]
        commits = [
            "feat(auth): implement login", "feat(ui): add dashboard",
            "fix: resolve crash on startup", "docs: update api docs",
            "refactor: simplify auth flow", "test: add integration tests",
            "chore: update dependencies", "perf: optimize queries",
            "ci: add pipeline", "build: update config",
        ]
        report = generate_compliance_report(branches, commits)
        assert report["branch_compliance"] == 100.0
        assert report["commit_compliance"] >= 95.0
        assert report["overall_pass"] is True

    def test_fail_branch_not_100(self):
        branches = ["main", "my-random-branch"]
        commits = ["feat: a", "fix: b"]
        report = generate_compliance_report(branches, commits)
        assert report["overall_pass"] is False
        assert report["branch_pass"] is False

    def test_fail_commit_below_95(self):
        branches = ["main", "develop"]
        commits = ["feat: a", "bad message"]
        report = generate_compliance_report(branches, commits)
        assert report["overall_pass"] is False
        assert report["commit_pass"] is False

    def test_boundary_exactly_95(self):
        branches = ["main", "develop"]
        valid = [f"feat: x{i}" for i in range(19)]
        commits = valid + ["bad"]
        report = generate_compliance_report(branches, commits)
        compliance = report["commit_compliance"]
        assert compliance >= 95.0
        assert report["overall_pass"] is True

    def test_boundary_below_95(self):
        branches = ["main", "develop"]
        valid = [f"feat: x{i}" for i in range(9)]
        commits = valid + ["bad"]
        report = generate_compliance_report(branches, commits)
        assert report["commit_compliance"] < 95.0
        assert report["overall_pass"] is False
