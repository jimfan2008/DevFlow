import subprocess
from typing import Dict, List
from unittest.mock import patch, MagicMock


def count_commits_per_branch(branch_names: List[str], repo_path: str = ".") -> Dict[str, int]:
    """统计每个分支的 commit 数量"""
    result = {}
    for branch in branch_names:
        try:
            output = subprocess.run(
                ["git", "rev-list", "--count", branch],
                capture_output=True, text=True, cwd=repo_path
            )
            if output.returncode == 0:
                result[branch] = int(output.stdout.strip())
            else:
                result[branch] = 0
        except (subprocess.SubprocessError, ValueError):
            result[branch] = 0
    return result


def validate_min_commits_per_step(branch_commits: Dict[str, int], min_commits: int = 1) -> List[str]:
    """验证每个分支至少有所需的 commit 数量，返回违规分支列表"""
    violations = []
    for branch, count in branch_commits.items():
        if count < min_commits:
            violations.append(branch)
    return violations


def check_each_step_has_commit(branch_names: List[str], repo_path: str = ".") -> Dict[str, bool]:
    """检查每个开发步骤对应的分支是否至少包含1个commit"""
    branch_commits = count_commits_per_branch(branch_names, repo_path)
    result = {}
    for branch, count in branch_commits.items():
        result[branch] = count >= 1
    return result


def validate_no_zero_commit_branches(branch_commits: Dict[str, int]) -> bool:
    """验证 commit 数量统计结果中无 0 值分支"""
    return all(count > 0 for count in branch_commits.values())


# ==================== 测试代码 ====================

import pytest


def _mock_git_rev_list(return_value: str, returncode: int = 0) -> MagicMock:
    """创建模拟的 subprocess.run 返回值"""
    mock = MagicMock()
    mock.stdout = return_value
    mock.stderr = ""
    mock.returncode = returncode
    return mock


class TestCountCommitsPerBranch:
    """测试统计每个分支的 commit 数量"""

    @patch("subprocess.run")
    def test_single_branch_with_commits(self, mock_run):
        mock_run.return_value = _mock_git_rev_list("5")
        result = count_commits_per_branch(["step-1"])
        assert result == {"step-1": 5}

    @patch("subprocess.run")
    def test_multiple_branches_with_commits(self, mock_run):
        mock_run.side_effect = [
            _mock_git_rev_list("3"),
            _mock_git_rev_list("7"),
            _mock_git_rev_list("1"),
        ]
        result = count_commits_per_branch(["step-1", "step-2", "step-3"])
        assert result == {"step-1": 3, "step-2": 7, "step-3": 1}

    @patch("subprocess.run")
    def test_branch_with_zero_commits(self, mock_run):
        mock_run.return_value = _mock_git_rev_list("0")
        result = count_commits_per_branch(["empty-branch"])
        assert result == {"empty-branch": 0}

    @patch("subprocess.run")
    def test_branch_git_error_returns_zero(self, mock_run):
        mock_run.return_value = _mock_git_rev_list("", returncode=1)
        result = count_commits_per_branch(["nonexistent-branch"])
        assert result == {"nonexistent-branch": 0}

    @patch("subprocess.run")
    def test_empty_branch_list(self, mock_run):
        result = count_commits_per_branch([])
        assert result == {}
        mock_run.assert_not_called()


class TestValidateMinCommitsPerStep:
    """验证每个分支至少有最小 commit 数量"""

    def test_all_branches_pass(self):
        branch_commits = {"step-1": 3, "step-2": 1, "step-3": 5}
        violations = validate_min_commits_per_step(branch_commits, min_commits=1)
        assert violations == []

    def test_one_branch_has_zero_commits(self):
        branch_commits = {"step-1": 2, "step-2": 0, "step-3": 4}
        violations = validate_min_commits_per_step(branch_commits, min_commits=1)
        assert violations == ["step-2"]

    def test_multiple_branches_have_zero_commits(self):
        branch_commits = {"step-1": 0, "step-2": 3, "step-3": 0}
        violations = validate_min_commits_per_step(branch_commits, min_commits=1)
        assert set(violations) == {"step-1", "step-3"}

    def test_all_branches_fail(self):
        branch_commits = {"step-1": 0, "step-2": 0}
        violations = validate_min_commits_per_step(branch_commits, min_commits=1)
        assert violations == ["step-1", "step-2"]

    def test_empty_dict_returns_no_violations(self):
        violations = validate_min_commits_per_step({}, min_commits=1)
        assert violations == []

    def test_custom_min_commits_threshold(self):
        branch_commits = {"step-1": 2, "step-2": 4, "step-3": 1}
        violations = validate_min_commits_per_step(branch_commits, min_commits=2)
        assert violations == ["step-3"]


class TestCheckEachStepHasCommit:
    """测试每个开发步骤是否至少包含1个commit"""

    @patch("subprocess.run")
    def test_all_steps_have_commits(self, mock_run):
        mock_run.side_effect = [
            _mock_git_rev_list("2"),
            _mock_git_rev_list("1"),
            _mock_git_rev_list("4"),
        ]
        result = check_each_step_has_commit(["step-1", "step-2", "step-3"])
        assert result == {"step-1": True, "step-2": True, "step-3": True}

    @patch("subprocess.run")
    def test_one_step_missing_commit(self, mock_run):
        mock_run.side_effect = [
            _mock_git_rev_list("2"),
            _mock_git_rev_list("0"),
            _mock_git_rev_list("1"),
        ]
        result = check_each_step_has_commit(["step-1", "step-2", "step-3"])
        assert result == {"step-1": True, "step-2": False, "step-3": True}

    @patch("subprocess.run")
    def test_single_step_with_one_commit(self, mock_run):
        mock_run.return_value = _mock_git_rev_list("1")
        result = check_each_step_has_commit(["step-1"])
        assert result == {"step-1": True}

    @patch("subprocess.run")
    def test_single_step_with_zero_commits(self, mock_run):
        mock_run.return_value = _mock_git_rev_list("0")
        result = check_each_step_has_commit(["step-1"])
        assert result == {"step-1": False}


class TestValidateNoZeroCommitBranches:
    """验证 commit 数量统计结果中无 0 值分支"""

    def test_all_branches_have_positive_commits(self):
        branch_commits = {"step-1": 1, "step-2": 3, "step-3": 10}
        assert validate_no_zero_commit_branches(branch_commits) is True

    def test_any_branch_has_zero_commits(self):
        branch_commits = {"step-1": 2, "step-2": 0, "step-3": 5}
        assert validate_no_zero_commit_branches(branch_commits) is False

    def test_all_branches_have_zero_commits(self):
        branch_commits = {"step-1": 0, "step-2": 0}
        assert validate_no_zero_commit_branches(branch_commits) is False

    def test_empty_dict(self):
        assert validate_no_zero_commit_branches({}) is True

    def test_boundary_case_min_one_commit(self):
        branch_commits = {"step-1": 1}
        assert validate_no_zero_commit_branches(branch_commits) is True


class TestIntegration:
    """端到端集成场景：模拟完整开发流程"""

    @patch("subprocess.run")
    def test_normal_dev_flow_all_steps_have_commits(self, mock_run):
        """正常场景：3个开发步骤，每个步骤都有commit"""
        # check_each_step_has_commit 内部调用 count_commits_per_branch (3次)
        # 测试中又显式调用 count_commits_per_branch (3次)
        # 共需 6 次 mock 返回值
        mock_run.side_effect = [
            _mock_git_rev_list("1"),
            _mock_git_rev_list("3"),
            _mock_git_rev_list("2"),
            _mock_git_rev_list("1"),
            _mock_git_rev_list("3"),
            _mock_git_rev_list("2"),
        ]
        branches = ["feature/login", "feature/payment", "feature/dashboard"]

        # 检查每个步骤
        result = check_each_step_has_commit(branches)
        for branch in branches:
            assert result[branch] is True, f"{branch} 应该至少有1个commit"

        # 统计 commit 数量
        branch_commits = count_commits_per_branch(branches)
        violations = validate_min_commits_per_step(branch_commits)
        assert violations == [], "所有分支都应满足至少1个commit的要求"

        # 无0值分支
        assert validate_no_zero_commit_branches(branch_commits) is True

    @patch("subprocess.run")
    def test_dev_flow_with_missing_commit_step(self, mock_run):
        """异常场景：某个开发步骤没有commit"""
        # 第一次 count_commits (3次) + 第二次 count_commits (3次) = 6次
        mock_run.side_effect = [
            _mock_git_rev_list("2"),
            _mock_git_rev_list("0"),
            _mock_git_rev_list("1"),
            _mock_git_rev_list("2"),
            _mock_git_rev_list("0"),
            _mock_git_rev_list("1"),
        ]
        branches = ["feature/login", "feature/payment", "feature/dashboard"]

        result = check_each_step_has_commit(branches)
        assert result["feature/login"] is True
        assert result["feature/payment"] is False
        assert result["feature/dashboard"] is True

        branch_commits = count_commits_per_branch(branches)
        violations = validate_min_commits_per_step(branch_commits)
        assert "feature/payment" in violations

        assert validate_no_zero_commit_branches(branch_commits) is False

    @patch("subprocess.run")
    def test_dev_flow_git_error_on_branch(self, mock_run):
        """异常场景：某个分支 git 命令报错"""
        # 第一次 count_commits (3次) + 第二次 count_commits (3次) = 6次
        mock_run.side_effect = [
            _mock_git_rev_list("1"),
            _mock_git_rev_list("", returncode=1),
            _mock_git_rev_list("3"),
            _mock_git_rev_list("1"),
            _mock_git_rev_list("", returncode=1),
            _mock_git_rev_list("3"),
        ]
        branches = ["feature/login", "feature/payment", "feature/dashboard"]

        result = check_each_step_has_commit(branches)
        assert result["feature/payment"] is False

        branch_commits = count_commits_per_branch(branches)
        assert branch_commits["feature/payment"] == 0
        violations = validate_min_commits_per_step(branch_commits)
        assert "feature/payment" in violations
