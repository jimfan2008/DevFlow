import pytest
import time
from datetime import datetime, timedelta
from typing import List, Dict, Any, Optional
from dataclasses import dataclass, field
from enum import Enum


class PRStatus(Enum):
    OPEN = "open"
    UNDER_REVIEW = "under_review"
    APPROVED = "approved"
    REJECTED = "rejected"
    MERGED = "merged"


class ReviewAction(Enum):
    APPROVE = "approve"
    REQUEST_CHANGES = "request_changes"
    COMMENT = "comment"


@dataclass
class PRComment:
    author_id: str
    content: str
    timestamp: datetime
    is_review_comment: bool = False


@dataclass
class PRReview:
    reviewer_id: str
    action: ReviewAction
    comments: List[str] = field(default_factory=list)
    submitted_at: datetime = field(default_factory=datetime.now)
    response_time_seconds: float = 0.0


@dataclass
class PullRequest:
    pr_id: str
    title: str
    author_id: str
    files_changed: int
    lines_added: int
    lines_deleted: int
    status: PRStatus = PRStatus.OPEN
    created_at: datetime = field(default_factory=datetime.now)
    reviews: List[PRReview] = field(default_factory=list)
    comments: List[PRComment] = field(default_factory=list)
    merged_at: Optional[datetime] = None


@dataclass
class SwarmMember:
    member_id: str
    name: str
    role: str  # "reviewer", "author", "admin"
    is_active: bool = True


@dataclass
class PRMergeResult:
    pr_id: str
    success: bool
    merged_at: Optional[datetime]
    review_pass_rate: float
    response_time_seconds: float
    blocker_count: int


class CodeReviewCoordinator:
    """PR审查协调器 — 蜂群成员代码提交的审查与合并"""

    def __init__(self, max_response_hours: float = 2.0, pass_rate_threshold: float = 0.9):
        self.max_response_hours = max_response_hours
        self.pass_rate_threshold = pass_rate_threshold
        self.members: Dict[str, SwarmMember] = {}
        self.pull_requests: Dict[str, PullRequest] = {}
        self.merge_results: List[PRMergeResult] = []

    def register_member(self, member: SwarmMember):
        """注册蜂群成员"""
        self.members[member.member_id] = member

    def create_pr(self, pr: PullRequest) -> PullRequest:
        """创建PR"""
        self.pull_requests[pr.pr_id] = pr
        return pr

    def submit_review(self, pr_id: str, reviewer_id: str,
                      action: ReviewAction, comments: Optional[List[str]] = None,
                      response_time_seconds: float = 0.0) -> Optional[PRReview]:
        """提交审查意见"""
        pr = self.pull_requests.get(pr_id)
        if not pr:
            return None
        if reviewer_id not in self.members:
            return None
        member = self.members[reviewer_id]
        if not member.is_active:
            return None

        review = PRReview(
            reviewer_id=reviewer_id,
            action=action,
            comments=comments or [],
            response_time_seconds=response_time_seconds
        )
        pr.reviews.append(review)
        if action == ReviewAction.REQUEST_CHANGES:
            pr.status = PRStatus.OPEN
        elif action == ReviewAction.APPROVE:
            pr.status = PRStatus.APPROVED
        return review

    def merge_pr(self, pr_id: str) -> PRMergeResult:
        """合并PR"""
        pr = self.pull_requests.get(pr_id)
        if not pr:
            return PRMergeResult(
                pr_id=pr_id, success=False, merged_at=None,
                review_pass_rate=0.0, response_time_seconds=0.0, blocker_count=0
            )
        if not pr.reviews:
            return PRMergeResult(
                pr_id=pr_id, success=False, merged_at=None,
                review_pass_rate=0.0, response_time_seconds=0.0, blocker_count=0
            )

        blocker_count = sum(
            1 for r in pr.reviews if r.action == ReviewAction.REQUEST_CHANGES
        )
        if blocker_count > 0:
            return PRMergeResult(
                pr_id=pr_id, success=False, merged_at=None,
                review_pass_rate=0.0, response_time_seconds=0.0,
                blocker_count=blocker_count
            )

        now = datetime.now()
        pr.status = PRStatus.MERGED
        pr.merged_at = now

        pass_rate = self._calculate_pass_rate(pr)
        avg_response = self._calculate_avg_response_time(pr)

        result = PRMergeResult(
            pr_id=pr_id,
            success=True,
            merged_at=now,
            review_pass_rate=pass_rate,
            response_time_seconds=avg_response,
            blocker_count=0
        )
        self.merge_results.append(result)
        return result

    def get_review_response_time(self, pr_id: str) -> float:
        """获取PR的平均审查响应时间（秒）"""
        pr = self.pull_requests.get(pr_id)
        if not pr or not pr.reviews:
            return 0.0
        return self._calculate_avg_response_time(pr)

    def get_review_pass_rate(self, pr_id: str) -> float:
        """获取PR的审查通过率"""
        pr = self.pull_requests.get(pr_id)
        if not pr:
            return 0.0
        return self._calculate_pass_rate(pr)

    def check_response_within_limit(self, pr_id: str) -> bool:
        """检查PR审查响应是否在时限内（默认2小时）"""
        pr = self.pull_requests.get(pr_id)
        if not pr or not pr.reviews:
            return True
        max_seconds = self.max_response_hours * 3600
        for review in pr.reviews:
            if review.response_time_seconds > max_seconds:
                return False
        return True

    def check_pass_rate_above_threshold(self, pr_id: str) -> bool:
        """检查PR审查通过率是否达标"""
        pass_rate = self.get_review_pass_rate(pr_id)
        return pass_rate >= self.pass_rate_threshold

    def _calculate_pass_rate(self, pr: PullRequest) -> float:
        """计算审查通过率"""
        if not pr.reviews:
            return 0.0
        approve_count = sum(
            1 for r in pr.reviews if r.action == ReviewAction.APPROVE
        )
        return approve_count / len(pr.reviews)

    def _calculate_avg_response_time(self, pr: PullRequest) -> float:
        """计算平均响应时间（秒）"""
        if not pr.reviews:
            return 0.0
        total = sum(r.response_time_seconds for r in pr.reviews)
        return total / len(pr.reviews)


# ── 测试数据工厂 ──

def create_swarm_member(member_id: str = "reviewer-1",
                        role: str = "reviewer") -> SwarmMember:
    return SwarmMember(
        member_id=member_id,
        name=f"蜂群成员{member_id}",
        role=role,
        is_active=True
    )


def create_pr(pr_id: str = "pr-1",
              author_id: str = "author-1") -> PullRequest:
    return PullRequest(
        pr_id=pr_id,
        title="功能开发提交",
        author_id=author_id,
        files_changed=5,
        lines_added=120,
        lines_deleted=30
    )


# ── 测试用例：代码审查与PR合并 ──

class TestCodeReviewAndPRMerge:
    """验证后发审查蜂群成员代码提交"""

    def setup_method(self):
        """每个测试方法执行前初始化"""
        self.coordinator = CodeReviewCoordinator(
            max_response_hours=2.0,
            pass_rate_threshold=0.9
        )

    def test_pr_review_response_within_2_hours(self):
        """验收标准1：PR审查响应 <= 2小时"""
        reviewer = create_swarm_member("r1")
        self.coordinator.register_member(reviewer)
        pr = create_pr("pr-1")
        self.coordinator.create_pr(pr)

        # 响应时间为1.5小时（5400秒），小于2小时
        response_seconds = 1.5 * 3600
        self.coordinator.submit_review(
            pr_id="pr-1",
            reviewer_id="r1",
            action=ReviewAction.APPROVE,
            response_time_seconds=response_seconds
        )

        within_limit = self.coordinator.check_response_within_limit("pr-1")
        assert within_limit is True, "1.5小时的响应应在2小时时限内"

    def test_pr_review_response_exceeds_2_hours(self):
        """验收标准1边界：PR审查响应超过2小时应判定不通过"""
        reviewer = create_swarm_member("r2")
        self.coordinator.register_member(reviewer)
        pr = create_pr("pr-2")
        self.coordinator.create_pr(pr)

        # 响应时间为2.5小时（9000秒），超过2小时
        response_seconds = 2.5 * 3600
        self.coordinator.submit_review(
            pr_id="pr-2",
            reviewer_id="r2",
            action=ReviewAction.APPROVE,
            response_time_seconds=response_seconds
        )

        within_limit = self.coordinator.check_response_within_limit("pr-2")
        assert within_limit is False, "2.5小时的响应应超出2小时时限"

    def test_pr_review_response_exactly_2_hours(self):
        """验收标准1边界：PR审查响应恰好2小时应判定通过"""
        reviewer = create_swarm_member("r3")
        self.coordinator.register_member(reviewer)
        pr = create_pr("pr-3")
        self.coordinator.create_pr(pr)

        # 恰好2小时
        response_seconds = 2.0 * 3600
        self.coordinator.submit_review(
            pr_id="pr-3",
            reviewer_id="r3",
            action=ReviewAction.APPROVE,
            response_time_seconds=response_seconds
        )

        within_limit = self.coordinator.check_response_within_limit("pr-3")
        assert within_limit is True, "恰好2小时的响应应判定通过"

    def test_pr_review_response_zero_seconds(self):
        """验收标准1边界：即时响应（0秒）应判定通过"""
        reviewer = create_swarm_member("r4")
        self.coordinator.register_member(reviewer)
        pr = create_pr("pr-4")
        self.coordinator.create_pr(pr)

        self.coordinator.submit_review(
            pr_id="pr-4",
            reviewer_id="r4",
            action=ReviewAction.APPROVE,
            response_time_seconds=0.0
        )

        within_limit = self.coordinator.check_response_within_limit("pr-4")
        assert within_limit is True, "即时响应应判定通过"

    def test_review_pass_rate_90_percent_pass(self):
        """验收标准2：审查通过率 >= 90%（10审9过）"""
        coordinator = CodeReviewCoordinator(pass_rate_threshold=0.9)
        reviewers = [
            create_swarm_member(f"r{i}") for i in range(10)
        ]
        for r in reviewers:
            coordinator.register_member(r)
        pr = create_pr("pr-90")
        coordinator.create_pr(pr)

        # 9个通过，1个请求修改 = 90%
        for i in range(9):
            coordinator.submit_review(
                pr_id="pr-90",
                reviewer_id=f"r{i}",
                action=ReviewAction.APPROVE,
                response_time_seconds=1800
            )
        coordinator.submit_review(
            pr_id="pr-90",
            reviewer_id="r9",
            action=ReviewAction.REQUEST_CHANGES,
            response_time_seconds=1800
        )

        pass_rate = coordinator.get_review_pass_rate("pr-90")
        above_threshold = coordinator.check_pass_rate_above_threshold("pr-90")
        assert pass_rate == 0.9, f"通过率应为0.9，实际为{pass_rate}"
        assert above_threshold is True, "90%通过率应达标"

    def test_review_pass_rate_below_90_percent_fail(self):
        """验收标准2边界：审查通过率低于90%应不达标"""
        coordinator = CodeReviewCoordinator(pass_rate_threshold=0.9)
        reviewers = [
            create_swarm_member(f"r{i}") for i in range(10)
        ]
        for r in reviewers:
            coordinator.register_member(r)
        pr = create_pr("pr-below-90")
        coordinator.create_pr(pr)

        # 8个通过，2个请求修改 = 80%
        for i in range(8):
            coordinator.submit_review(
                pr_id="pr-below-90",
                reviewer_id=f"r{i}",
                action=ReviewAction.APPROVE,
                response_time_seconds=1800
            )
        for i in range(8, 10):
            coordinator.submit_review(
                pr_id="pr-below-90",
                reviewer_id=f"r{i}",
                action=ReviewAction.REQUEST_CHANGES,
                response_time_seconds=1800
            )

        pass_rate = coordinator.get_review_pass_rate("pr-below-90")
        above_threshold = coordinator.check_pass_rate_above_threshold("pr-below-90")
        assert pass_rate == 0.8, f"通过率应为0.8，实际为{pass_rate}"
        assert above_threshold is False, "80%通过率应不达标"

    def test_review_pass_rate_100_percent(self):
        """验收标准2：审查通过率100%（全通过）"""
        coordinator = CodeReviewCoordinator(pass_rate_threshold=0.9)
        reviewers = [
            create_swarm_member(f"r{i}") for i in range(5)
        ]
        for r in reviewers:
            coordinator.register_member(r)
        pr = create_pr("pr-100")
        coordinator.create_pr(pr)

        for i in range(5):
            coordinator.submit_review(
                pr_id="pr-100",
                reviewer_id=f"r{i}",
                action=ReviewAction.APPROVE,
                response_time_seconds=3600
            )

        pass_rate = coordinator.get_review_pass_rate("pr-100")
        assert pass_rate == 1.0, f"通过率应为1.0，实际为{pass_rate}"
        above = coordinator.check_pass_rate_above_threshold("pr-100")
        assert above is True, "100%通过率应达标"

    def test_pr_merge_success_when_all_approved(self):
        """PR合并：所有审查通过时可成功合并"""
        reviewers = [
            create_swarm_member(f"r{i}") for i in range(3)
        ]
        for r in reviewers:
            self.coordinator.register_member(r)
        pr = create_pr("pr-merge-ok")
        self.coordinator.create_pr(pr)

        for i in range(3):
            self.coordinator.submit_review(
                pr_id="pr-merge-ok",
                reviewer_id=f"r{i}",
                action=ReviewAction.APPROVE,
                response_time_seconds=1800
            )

        result = self.coordinator.merge_pr("pr-merge-ok")
        assert result.success is True, "所有审查通过时合并应成功"
        assert result.merged_at is not None, "合并成功应有合并时间"
        assert result.blocker_count == 0, "应无阻塞项"
        assert result.review_pass_rate == 1.0, "通过率应为100%"

    def test_pr_merge_fails_when_request_changes(self):
        """PR合并：有request_changes时应合并失败"""
        reviewers = [
            create_swarm_member(f"r{i}") for i in range(2)
        ]
        for r in reviewers:
            self.coordinator.register_member(r)
        pr = create_pr("pr-merge-fail")
        self.coordinator.create_pr(pr)

        self.coordinator.submit_review(
            pr_id="pr-merge-fail",
            reviewer_id="r0",
            action=ReviewAction.APPROVE,
            response_time_seconds=1800
        )
        self.coordinator.submit_review(
            pr_id="pr-merge-fail",
            reviewer_id="r1",
            action=ReviewAction.REQUEST_CHANGES,
            response_time_seconds=1800
        )

        result = self.coordinator.merge_pr("pr-merge-fail")
        assert result.success is False, "有请求修改时合并应失败"
        assert result.blocker_count == 1, "应有1个阻塞项"

    def test_pr_merge_fails_when_no_reviews(self):
        """PR合并：无审查意见时不可合并"""
        pr = create_pr("pr-no-review")
        self.coordinator.create_pr(pr)

        result = self.coordinator.merge_pr("pr-no-review")
        assert result.success is False, "无审查时不可合并"

    def test_pr_merge_nonexistent_pr(self):
        """PR合并：不存在的PR合并应失败"""
        result = self.coordinator.merge_pr("pr-nonexistent")
        assert result.success is False, "不存在的PR合并应失败"

    def test_swarm_member_submit_review_workflow(self):
        """完整流程：蜂群成员提交代码 → 审查 → 合并"""
        author = create_swarm_member("author-1", "author")
        reviewer1 = create_swarm_member("reviewer-1", "reviewer")
        reviewer2 = create_swarm_member("reviewer-2", "reviewer")
        reviewer3 = create_swarm_member("reviewer-3", "reviewer")

        for m in [author, reviewer1, reviewer2, reviewer3]:
            self.coordinator.register_member(m)

        pr = create_pr("pr-workflow", "author-1")
        self.coordinator.create_pr(pr)

        assert pr.status == PRStatus.OPEN

        self.coordinator.submit_review(
            pr_id="pr-workflow",
            reviewer_id="reviewer-1",
            action=ReviewAction.APPROVE,
            response_time_seconds=3600
        )
        self.coordinator.submit_review(
            pr_id="pr-workflow",
            reviewer_id="reviewer-2",
            action=ReviewAction.APPROVE,
            response_time_seconds=5400
        )
        self.coordinator.submit_review(
            pr_id="pr-workflow",
            reviewer_id="reviewer-3",
            action=ReviewAction.APPROVE,
            response_time_seconds=7200
        )

        response_ok = self.coordinator.check_response_within_limit("pr-workflow")
        pass_ok = self.coordinator.check_pass_rate_above_threshold("pr-workflow")

        assert response_ok is True, "所有响应应在时限内"
        assert pass_ok is True, "通过率应达标"

        result = self.coordinator.merge_pr("pr-workflow")
        assert result.success is True
        assert result.review_pass_rate == 1.0
        assert result.response_time_seconds <= 2.0 * 3600

    def test_inactive_member_cannot_submit_review(self):
        """非活跃蜂群成员不能提交审查"""
        member = create_swarm_member("inactive-1")
        member.is_active = False
        self.coordinator.register_member(member)
        pr = create_pr("pr-inactive")
        self.coordinator.create_pr(pr)

        review = self.coordinator.submit_review(
            pr_id="pr-inactive",
            reviewer_id="inactive-1",
            action=ReviewAction.APPROVE
        )
        assert review is None, "非活跃成员提交的审查应返回None"

    def test_unregistered_member_cannot_submit_review(self):
        """未注册的成员不能提交审查"""
        pr = create_pr("pr-unreg")
        self.coordinator.create_pr(pr)

        review = self.coordinator.submit_review(
            pr_id="pr-unreg",
            reviewer_id="unregistered-member",
            action=ReviewAction.APPROVE
        )
        assert review is None, "未注册成员提交的审查应返回None"

    def test_multiple_reviews_mixed_actions(self):
        """多个审查意见混合（approve + request_changes + comment）"""
        reviewers = [
            create_swarm_member(f"r{i}") for i in range(5)
        ]
        for r in reviewers:
            self.coordinator.register_member(r)
        pr = create_pr("pr-mixed")
        self.coordinator.create_pr(pr)

        # 3 approve, 1 comment, 1 request_changes
        self.coordinator.submit_review(
            pr_id="pr-mixed", reviewer_id="r0",
            action=ReviewAction.APPROVE, response_time_seconds=1800
        )
        self.coordinator.submit_review(
            pr_id="pr-mixed", reviewer_id="r1",
            action=ReviewAction.APPROVE, response_time_seconds=3600
        )
        self.coordinator.submit_review(
            pr_id="pr-mixed", reviewer_id="r2",
            action=ReviewAction.APPROVE, response_time_seconds=5400
        )
        self.coordinator.submit_review(
            pr_id="pr-mixed", reviewer_id="r3",
            action=ReviewAction.COMMENT, response_time_seconds=7200
        )
        self.coordinator.submit_review(
            pr_id="pr-mixed", reviewer_id="r4",
            action=ReviewAction.REQUEST_CHANGES, response_time_seconds=1800
        )

        result = self.coordinator.merge_pr("pr-mixed")
        assert result.success is False, "有request_changes时合并应失败"
        assert result.blocker_count == 1

    def test_review_response_time_boundary_1_hour_59_min(self):
        """响应时间1小时59分应判定通过"""
        reviewer = create_swarm_member("r-boundary")
        self.coordinator.register_member(reviewer)
        pr = create_pr("pr-boundary-1")
        self.coordinator.create_pr(pr)

        response_seconds = 1.9833 * 3600  # 约1小时59分
        self.coordinator.submit_review(
            pr_id="pr-boundary-1",
            reviewer_id="r-boundary",
            action=ReviewAction.APPROVE,
            response_time_seconds=response_seconds
        )

        within = self.coordinator.check_response_within_limit("pr-boundary-1")
        assert within is True, "1小时59分应在时限内"

    def test_review_response_time_boundary_2_hours_1_min(self):
        """响应时间2小时1分应判定超时"""
        reviewer = create_swarm_member("r-boundary2")
        self.coordinator.register_member(reviewer)
        pr = create_pr("pr-boundary-2")
        self.coordinator.create_pr(pr)

        response_seconds = 2.0167 * 3600  # 约2小时1分
        self.coordinator.submit_review(
            pr_id="pr-boundary-2",
            reviewer_id="r-boundary2",
            action=ReviewAction.APPROVE,
            response_time_seconds=response_seconds
        )

        within = self.coordinator.check_response_within_limit("pr-boundary-2")
        assert within is False, "2小时1分应超时"

    def test_merge_result_stored_in_history(self):
        """合并结果应保存在历史记录中"""
        reviewer = create_swarm_member("r-history")
        self.coordinator.register_member(reviewer)
        pr = create_pr("pr-history")
        self.coordinator.create_pr(pr)

        self.coordinator.submit_review(
            pr_id="pr-history",
            reviewer_id="r-history",
            action=ReviewAction.APPROVE,
            response_time_seconds=1800
        )

        result = self.coordinator.merge_pr("pr-history")
        assert result.success is True
        assert len(self.coordinator.merge_results) == 1
        stored = self.coordinator.merge_results[0]
        assert stored.pr_id == "pr-history"
        assert stored.success is True

    def test_pr_status_transitions(self):
        """PR状态流转：OPEN → APPROVED → MERGED"""
        reviewer = create_swarm_member("r-status")
        self.coordinator.register_member(reviewer)
        pr = create_pr("pr-status")
        self.coordinator.create_pr(pr)

        assert pr.status == PRStatus.OPEN

        self.coordinator.submit_review(
            pr_id="pr-status",
            reviewer_id="r-status",
            action=ReviewAction.APPROVE,
            response_time_seconds=1800
        )
        assert pr.status == PRStatus.APPROVED

        self.coordinator.merge_pr("pr-status")
        assert pr.status == PRStatus.MERGED
        assert pr.merged_at is not None

    def test_pr_status_request_changes_back_to_open(self):
        """PR收到request_changes应回到OPEN状态"""
        reviewer = create_swarm_member("r-revert")
        self.coordinator.register_member(reviewer)
        pr = create_pr("pr-revert")
        self.coordinator.create_pr(pr)

        self.coordinator.submit_review(
            pr_id="pr-revert",
            reviewer_id="r-revert",
            action=ReviewAction.APPROVE,
            response_time_seconds=1800
        )
        assert pr.status == PRStatus.APPROVED

        self.coordinator.submit_review(
            pr_id="pr-revert",
            reviewer_id="r-revert",
            action=ReviewAction.REQUEST_CHANGES,
            response_time_seconds=3600
        )
        assert pr.status == PRStatus.OPEN

    def test_get_response_time_no_reviews_returns_zero(self):
        """无审查的PR响应时间应返回0"""
        pr = create_pr("pr-no-rev-time")
        self.coordinator.create_pr(pr)

        avg_time = self.coordinator.get_review_response_time("pr-no-rev-time")
        assert avg_time == 0.0

    def test_get_pass_rate_no_reviews_returns_zero(self):
        """无审查的PR通过率应返回0"""
        pr = create_pr("pr-no-rev-rate")
        self.coordinator.create_pr(pr)

        rate = self.coordinator.get_review_pass_rate("pr-no-rev-rate")
        assert rate == 0.0

    def test_custom_response_limit(self):
        """自定义响应时限（非默认2小时）"""
        short_coordinator = CodeReviewCoordinator(max_response_hours=0.5)
        reviewer = create_swarm_member("r-short")
        short_coordinator.register_member(reviewer)
        pr = create_pr("pr-short")
        short_coordinator.create_pr(pr)

        response_seconds = 1.0 * 3600  # 1小时
        short_coordinator.submit_review(
            pr_id="pr-short",
            reviewer_id="r-short",
            action=ReviewAction.APPROVE,
            response_time_seconds=response_seconds
        )

        within = short_coordinator.check_response_within_limit("pr-short")
        assert within is False, "1小时应超过0.5小时时限"

    def test_custom_pass_rate_threshold(self):
        """自定义通过率阈值（非默认90%）"""
        strict_coordinator = CodeReviewCoordinator(pass_rate_threshold=0.95)
        reviewers = [
            create_swarm_member(f"r{i}") for i in range(10)
        ]
        for r in reviewers:
            strict_coordinator.register_member(r)
        pr = create_pr("pr-strict")
        strict_coordinator.create_pr(pr)

        # 9/10 = 90%，低于95%
        for i in range(9):
            strict_coordinator.submit_review(
                pr_id="pr-strict",
                reviewer_id=f"r{i}",
                action=ReviewAction.APPROVE,
                response_time_seconds=1800
            )
        strict_coordinator.submit_review(
            pr_id="pr-strict",
            reviewer_id="r9",
            action=ReviewAction.REQUEST_CHANGES,
            response_time_seconds=1800
        )

        above = strict_coordinator.check_pass_rate_above_threshold("pr-strict")
        assert above is False, "90%应低于95%阈值"

    def test_end_to_end_swarm_review_and_merge(self):
        """端到端验收：蜂群成员提交 → 多人审查 → 响应及时 + 通过率高 → 成功合并"""
        coordinator = CodeReviewCoordinator(
            max_response_hours=2.0,
            pass_rate_threshold=0.9
        )

        author = create_swarm_member("author-swarm", "author")
        reviewers = [
            create_swarm_member(f"swarm-r{i}") for i in range(10)
        ]
        coordinator.register_member(author)
        for r in reviewers:
            coordinator.register_member(r)

        pr = create_pr("pr-e2e", "author-swarm")
        coordinator.create_pr(pr)

        # 10个approve，响应时间 600s ~ 6000s，均<2小时
        for i in range(10):
            coordinator.submit_review(
                pr_id="pr-e2e",
                reviewer_id=f"swarm-r{i}",
                action=ReviewAction.APPROVE,
                response_time_seconds=(i + 1) * 600
            )

        # 响应检查：所有10个审查都在2小时内
        response_ok = coordinator.check_response_within_limit("pr-e2e")

        # 通过率检查
        pass_ok = coordinator.check_pass_rate_above_threshold("pr-e2e")
        pass_rate = coordinator.get_review_pass_rate("pr-e2e")

        # 合并
        result = coordinator.merge_pr("pr-e2e")

        assert response_ok is True, "所有审查响应应在2小时内"
        assert pass_ok is True, "通过率应>=90%"
        assert pass_rate == 1.0, "10审10过，通过率应为100%"
        assert result.success is True, "合并应成功"
        assert result.review_pass_rate == 1.0
        assert result.blocker_count == 0
        assert result.merged_at is not None

    def test_pr_merge_avg_response_time_calculation(self):
        """合并结果中的平均响应时间计算正确"""
        reviewers = [
            create_swarm_member(f"r{i}") for i in range(3)
        ]
        for r in reviewers:
            self.coordinator.register_member(r)
        pr = create_pr("pr-avg-time")
        self.coordinator.create_pr(pr)

        self.coordinator.submit_review(
            pr_id="pr-avg-time", reviewer_id="r0",
            action=ReviewAction.APPROVE, response_time_seconds=1800
        )
        self.coordinator.submit_review(
            pr_id="pr-avg-time", reviewer_id="r1",
            action=ReviewAction.APPROVE, response_time_seconds=3600
        )
        self.coordinator.submit_review(
            pr_id="pr-avg-time", reviewer_id="r2",
            action=ReviewAction.APPROVE, response_time_seconds=5400
        )

        result = self.coordinator.merge_pr("pr-avg-time")
        expected_avg = (1800 + 3600 + 5400) / 3  # 3600
        assert result.response_time_seconds == expected_avg, \
            f"平均响应时间应为{expected_avg}秒，实际为{result.response_time_seconds}秒"


if __name__ == "__main__":
    pytest.main([__file__, "-v"])
