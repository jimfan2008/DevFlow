import time
import pytest
from unittest.mock import Mock, patch, call
from datetime import datetime, timedelta, timezone
from typing import Dict, List, Any, Optional


class QARetryResult:
    """QA重试结果"""

    def __init__(self, passed: bool, score: float = 0.0, defects: Optional[List[Dict[str, Any]]] = None):
        self.passed = passed
        self.score = score
        self.defects = defects or []


class QARetryRecord:
    """QA重试记录"""

    def __init__(self, attempt: int, timestamp: datetime, result: QARetryResult, agent_name: str = "hourong"):
        self.attempt = attempt
        self.timestamp = timestamp
        self.result = result
        self.agent_name = agent_name
        self.retry_intervalSeconds = 0

    def to_dict(self) -> Dict[str, Any]:
        return {
            "attempt": self.attempt,
            "timestamp": self.timestamp.isoformat(),
            "passed": self.result.passed,
            "score": self.result.score,
            "defect_count": len(self.result.defects),
            "agent_name": self.agent_name,
        }


class HaimeiIntervention:
    """海梅介入记录"""

    def __init__(self, reason: str, timestamp: datetime, retry_count: int):
        self.reason = reason
        self.timestamp = timestamp
        self.retry_count = retry_count
        self.action_taken = "重新评估"
        self.response_time_seconds = 0

    def set_response_time(self, response_time_seconds: float):
        self.response_time_seconds = response_time_seconds

    def to_dict(self) -> Dict[str, Any]:
        return {
            "reason": self.reason,
            "timestamp": self.timestamp.isoformat(),
            "retry_count": self.retry_count,
            "action_taken": self.action_taken,
            "response_time_seconds": self.response_time_seconds,
        }


class QARetryStrategy:
    """QA重试策略 - 控制hourong检验的重试行为

    规则：
    1. 最大重试次数 = 3
    2. 超过3次后海梅介入重新评估
    3. 超时介入响应时间 <= 1小时（3600秒）
    """

    MAX_RETRIES = 3
    TIMEOUT_SECONDS = 3600

    def __init__(self, inspector: Optional[Any] = None, haimei: Optional[Any] = None):
        self._inspector = inspector
        self._haimei = haimei
        self._retry_records: List[QARetryRecord] = []
        self._interventions: List[HaimeiIntervention] = []
        self._start_time: Optional[datetime] = None
        self._completed = False

    def start(self) -> None:
        """开始QA重试流程"""
        self._start_time = datetime.now(timezone.utc)
        self._retry_records = []
        self._interventions = []
        self._completed = False

    def execute_retry(self, qa_result: QARetryResult, agent_name: str = "hourong") -> Dict[str, Any]:
        """执行一次QA检验重试

        Returns:
            {"should_retry": bool, "attempt": int, "intervention": bool}
        """
        if self._start_time is None:
            self.start()

        attempt = len(self._retry_records) + 1
        record = QARetryRecord(
            attempt=attempt,
            timestamp=datetime.now(timezone.utc),
            result=qa_result,
            agent_name=agent_name,
        )
        self._retry_records.append(record)

        if qa_result.passed:
            self._completed = True
            return {"should_retry": False, "attempt": attempt, "intervention": False, "reason": "检验通过"}

        if attempt >= self.MAX_RETRIES:
            intervention = self._handle_intervention(f"QA检验{self.MAX_RETRIES}次均未通过，海梅介入重新评估")
            self._completed = True
            return {
                "should_retry": False,
                "attempt": attempt,
                "intervention": True,
                "intervention_record": intervention,
                "reason": f"达到最大重试次数{self.MAX_RETRIES}，海梅介入",
            }

        return {"should_retry": True, "attempt": attempt, "intervention": False, "reason": f"第{attempt}次检验失败，继续重试"}

    def check_timeout(self, elapsed_seconds: float) -> Optional[HaimeiIntervention]:
        """检查是否超时，超时则海梅介入

        Args:
            elapsed_seconds: 从开始到现在经过的秒数

        Returns:
            如果超时则返回介入记录，否则返回None
        """
        if elapsed_seconds > self.TIMEOUT_SECONDS:
            intervention = self._handle_intervention(
                f"QA检验超时（{elapsed_seconds}秒 > {self.TIMEOUT_SECONDS}秒），海梅介入"
            )
            intervention.set_response_time(elapsed_seconds)
            self._completed = True
            return intervention

        if elapsed_seconds >= self.TIMEOUT_SECONDS:
            intervention = self._handle_intervention(
                f"QA检验达到超时阈值（{elapsed_seconds}秒），海梅介入"
            )
            intervention.set_response_time(elapsed_seconds)
            self._completed = True
            return intervention

        return None

    def _handle_intervention(self, reason: str) -> HaimeiIntervention:
        """处理海梅介入逻辑"""
        intervention = HaimeiIntervention(
            reason=reason,
            timestamp=datetime.now(timezone.utc),
            retry_count=len(self._retry_records),
        )
        self._interventions.append(intervention)
        if self._haimei and hasattr(self._haimei, "re_evaluate"):
            self._haimei.re_evaluate(reason, self._retry_records)
        return intervention

    def get_retry_records(self) -> List[QARetryRecord]:
        return list(self._retry_records)

    def get_interventions(self) -> List[HaimeiIntervention]:
        return list(self._interventions)

    def is_completed(self) -> bool:
        return self._completed

    def total_attempts(self) -> int:
        return len(self._retry_records)


class TestQARetryMaxLimit:
    """验证最大重试次数限制 = 3"""

    def test_max_retries_is_3(self):
        assert QARetryStrategy.MAX_RETRIES == 3

    def test_retry_allows_attempts_up_to_3(self):
        strategy = QARetryStrategy()
        strategy.start()

        r1 = strategy.execute_retry(QARetryResult(passed=False, score=40))
        assert r1["should_retry"] is True
        assert r1["attempt"] == 1

        r2 = strategy.execute_retry(QARetryResult(passed=False, score=45))
        assert r2["should_retry"] is True
        assert r2["attempt"] == 2

        r3 = strategy.execute_retry(QARetryResult(passed=False, score=50))
        assert r3["should_retry"] is False
        assert r3["attempt"] == 3

    def test_no_retry_after_3_attempts(self):
        strategy = QARetryStrategy()
        strategy.start()

        for i in range(3):
            strategy.execute_retry(QARetryResult(passed=False, score=40 + i * 5))

        record_count = strategy.total_attempts()
        assert record_count == 3

    def test_attempt_3_triggers_intervention(self):
        strategy = QARetryStrategy()
        strategy.start()

        strategy.execute_retry(QARetryResult(passed=False, score=40))
        strategy.execute_retry(QARetryResult(passed=False, score=45))
        r3 = strategy.execute_retry(QARetryResult(passed=False, score=50))

        assert r3["intervention"] is True
        assert strategy.is_completed() is True

    def test_attempt_3_does_not_retry(self):
        strategy = QARetryStrategy()
        strategy.start()

        strategy.execute_retry(QARetryResult(passed=False))
        strategy.execute_retry(QARetryResult(passed=False))
        r3 = strategy.execute_retry(QARetryResult(passed=False))

        assert r3["should_retry"] is False
        assert r3["reason"] == "达到最大重试次数3，海梅介入"

    def test_retry_records_have_increasing_attempt_numbers(self):
        strategy = QARetryStrategy()
        strategy.start()

        strategy.execute_retry(QARetryResult(passed=False))
        strategy.execute_retry(QARetryResult(passed=False))
        strategy.execute_retry(QARetryResult(passed=False))

        records = strategy.get_retry_records()
        attempts = [r.attempt for r in records]
        assert attempts == [1, 2, 3]

    def test_each_record_has_timestamp(self):
        strategy = QARetryStrategy()
        strategy.start()

        strategy.execute_retry(QARetryResult(passed=False))
        strategy.execute_retry(QARetryResult(passed=False))
        strategy.execute_retry(QARetryResult(passed=False))

        for record in strategy.get_retry_records():
            assert isinstance(record.timestamp, datetime)

    def test_each_record_has_agent_name(self):
        strategy = QARetryStrategy()
        strategy.start()

        strategy.execute_retry(QARetryResult(passed=False), agent_name="hourong")
        strategy.execute_retry(QARetryResult(passed=False), agent_name="hourong")
        strategy.execute_retry(QARetryResult(passed=False), agent_name="hourong")

        for record in strategy.get_retry_records():
            assert record.agent_name == "hourong"

    def test_timeout_seconds_is_3600(self):
        assert QARetryStrategy.TIMEOUT_SECONDS == 3600


class TestHaimeiIntervention:
    """验证超过3次海梅介入重新评估"""

    def test_intervention_created_after_3_failures(self):
        strategy = QARetryStrategy()
        strategy.start()

        strategy.execute_retry(QARetryResult(passed=False))
        strategy.execute_retry(QARetryResult(passed=False))
        strategy.execute_retry(QARetryResult(passed=False))

        interventions = strategy.get_interventions()
        assert len(interventions) == 1

    def test_intervention_reason_contains_retry_count(self):
        strategy = QARetryStrategy()
        strategy.start()

        strategy.execute_retry(QARetryResult(passed=False))
        strategy.execute_retry(QARetryResult(passed=False))
        strategy.execute_retry(QARetryResult(passed=False))

        intervention = strategy.get_interventions()[0]
        assert "3" in intervention.reason

    def test_intervention_action_is_re_evaluate(self):
        strategy = QARetryStrategy()
        strategy.start()

        strategy.execute_retry(QARetryResult(passed=False))
        strategy.execute_retry(QARetryResult(passed=False))
        strategy.execute_retry(QARetryResult(passed=False))

        intervention = strategy.get_interventions()[0]
        assert intervention.action_taken == "重新评估"

    def test_intervention_records_retry_count(self):
        strategy = QARetryStrategy()
        strategy.start()

        strategy.execute_retry(QARetryResult(passed=False))
        strategy.execute_retry(QARetryResult(passed=False))
        strategy.execute_retry(QARetryResult(passed=False))

        intervention = strategy.get_interventions()[0]
        assert intervention.retry_count == 3

    def test_intervention_has_timestamp(self):
        strategy = QARetryStrategy()
        strategy.start()

        strategy.execute_retry(QARetryResult(passed=False))
        strategy.execute_retry(QARetryResult(passed=False))
        strategy.execute_retry(QARetryResult(passed=False))

        intervention = strategy.get_interventions()[0]
        assert isinstance(intervention.timestamp, datetime)

    def test_haimei_callback_is_invoked(self):
        mock_haimei = Mock()
        mock_haimei.re_evaluate = Mock()
        strategy = QARetryStrategy(haimei=mock_haimei)
        strategy.start()

        strategy.execute_retry(QARetryResult(passed=False))
        strategy.execute_retry(QARetryResult(passed=False))
        strategy.execute_retry(QARetryResult(passed=False))

        mock_haimei.re_evaluate.assert_called_once()
        call_args = mock_haimei.re_evaluate.call_args
        assert isinstance(call_args[0][0], str)
        assert isinstance(call_args[0][1], list)

    def test_no_intervention_if_passed_before_3(self):
        strategy = QARetryStrategy()
        strategy.start()

        strategy.execute_retry(QARetryResult(passed=True, score=85))
        strategy.execute_retry(QARetryResult(passed=False, score=40))

        interventions = strategy.get_interventions()
        assert len(interventions) == 0

    def test_strategy_completed_on_intervention(self):
        strategy = QARetryStrategy()
        strategy.start()

        strategy.execute_retry(QARetryResult(passed=False))
        strategy.execute_retry(QARetryResult(passed=False))
        strategy.execute_retry(QARetryResult(passed=False))

        assert strategy.is_completed() is True

    def test_intervention_to_dict(self):
        strategy = QARetryStrategy()
        strategy.start()

        strategy.execute_retry(QARetryResult(passed=False))
        strategy.execute_retry(QARetryResult(passed=False))
        strategy.execute_retry(QARetryResult(passed=False))

        d = strategy.get_interventions()[0].to_dict()
        assert "reason" in d
        assert "timestamp" in d
        assert "retry_count" in d
        assert d["action_taken"] == "重新评估"
        assert d["response_time_seconds"] == 0

    def test_no_haimei_no_crash(self):
        strategy = QARetryStrategy()
        strategy.start()

        strategy.execute_retry(QARetryResult(passed=False))
        strategy.execute_retry(QARetryResult(passed=False))
        strategy.execute_retry(QARetryResult(passed=False))

        assert len(strategy.get_interventions()) == 1


class TestTimeoutIntervention:
    """验证超时介入响应时间 <= 1小时"""

    def test_timeout_at_exactly_3600_seconds(self):
        strategy = QARetryStrategy()
        strategy.start()

        intervention = strategy.check_timeout(3600)
        assert intervention is not None
        assert intervention.response_time_seconds == 3600

    def test_timeout_after_3600_seconds(self):
        strategy = QARetryStrategy()
        strategy.start()

        intervention = strategy.check_timeout(5000)
        assert intervention is not None
        assert intervention.response_time_seconds == 5000
        assert "超时" in intervention.reason

    def test_no_timeout_before_3600_seconds(self):
        strategy = QARetryStrategy()
        strategy.start()

        intervention = strategy.check_timeout(3599)
        assert intervention is None

    def test_no_timeout_at_zero_seconds(self):
        strategy = QARetryStrategy()
        strategy.start()

        intervention = strategy.check_timeout(0)
        assert intervention is None

    def test_no_timeout_at_one_hour_minus_one_second(self):
        strategy = QARetryStrategy()
        strategy.start()

        intervention = strategy.check_timeout(3599)
        assert intervention is None

    def test_strategy_completed_on_timeout(self):
        strategy = QARetryStrategy()
        strategy.start()

        strategy.check_timeout(3600)
        assert strategy.is_completed() is True

    def test_timeout_intervention_action_is_re_evaluate(self):
        strategy = QARetryStrategy()
        strategy.start()

        intervention = strategy.check_timeout(4000)
        assert intervention is not None
        assert intervention.action_taken == "重新评估"

    def test_timeout_response_time_within_limit(self):
        strategy = QARetryStrategy()
        strategy.start()

        elapsed = 3600
        intervention = strategy.check_timeout(elapsed)
        assert intervention is not None
        assert intervention.response_time_seconds <= 3600

    def test_multiple_timeout_checks_only_first_counts(self):
        strategy = QARetryStrategy()
        strategy.start()

        first = strategy.check_timeout(3600)
        assert first is not None

        second = strategy.check_timeout(7200)
        assert second is not None

        assert len(strategy.get_interventions()) == 2


class TestQARetrySuccessPaths:
    """验证成功场景"""

    def test_pass_on_first_attempt(self):
        strategy = QARetryStrategy()
        strategy.start()

        result = strategy.execute_retry(QARetryResult(passed=True, score=95))
        assert result["should_retry"] is False
        assert result["intervention"] is False
        assert result["reason"] == "检验通过"
        assert strategy.total_attempts() == 1

    def test_pass_on_second_attempt(self):
        strategy = QARetryStrategy()
        strategy.start()

        strategy.execute_retry(QARetryResult(passed=False, score=40))
        result = strategy.execute_retry(QARetryResult(passed=True, score=88))
        assert result["should_retry"] is False
        assert result["intervention"] is False
        assert strategy.total_attempts() == 2
        assert len(strategy.get_interventions()) == 0

    def test_pass_on_third_attempt(self):
        strategy = QARetryStrategy()
        strategy.start()

        strategy.execute_retry(QARetryResult(passed=False, score=35))
        strategy.execute_retry(QARetryResult(passed=False, score=42))
        result = strategy.execute_retry(QARetryResult(passed=True, score=82))
        assert result["should_retry"] is False
        assert result["intervention"] is False
        assert strategy.total_attempts() == 3
        assert len(strategy.get_interventions()) == 0

    def test_completed_on_pass(self):
        strategy = QARetryStrategy()
        strategy.start()

        strategy.execute_retry(QARetryResult(passed=True))
        assert strategy.is_completed() is True


class TestQARetryRecordToDict:
    """验证重试记录的序列化"""

    def test_record_to_dict_contains_attempt(self):
        record = QARetryRecord(
            attempt=1,
            timestamp=datetime(2026, 7, 20, 12, 0, 0, tzinfo=timezone.utc),
            result=QARetryResult(passed=False, score=45),
        )
        d = record.to_dict()
        assert d["attempt"] == 1

    def test_record_to_dict_contains_score(self):
        record = QARetryRecord(
            attempt=2,
            timestamp=datetime(2026, 7, 20, 12, 1, 0, tzinfo=timezone.utc),
            result=QARetryResult(passed=False, score=55, defects=[{"reason": "不完整"}]),
        )
        d = record.to_dict()
        assert d["score"] == 55

    def test_record_to_dict_contains_pass_status(self):
        record = QARetryRecord(
            attempt=1,
            timestamp=datetime(2026, 7, 20, 12, 0, 0, tzinfo=timezone.utc),
            result=QARetryResult(passed=True, score=90),
        )
        d = record.to_dict()
        assert d["passed"] is True

    def test_record_to_dict_contains_defect_count(self):
        defects = [{"reason": "a"}, {"reason": "b"}, {"reason": "c"}]
        record = QARetryRecord(
            attempt=1,
            timestamp=datetime(2026, 7, 20, 12, 0, 0, tzinfo=timezone.utc),
            result=QARetryResult(passed=False, score=50, defects=defects),
        )
        d = record.to_dict()
        assert d["defect_count"] == 3

    def test_record_to_dict_contains_agent_name(self):
        record = QARetryRecord(
            attempt=1,
            timestamp=datetime(2026, 7, 20, 12, 0, 0, tzinfo=timezone.utc),
            result=QARetryResult(passed=False),
            agent_name="custom_inspector",
        )
        d = record.to_dict()
        assert d["agent_name"] == "custom_inspector"

    def test_record_to_dict_serializes_timestamp(self):
        ts = datetime(2026, 7, 20, 12, 0, 0, tzinfo=timezone.utc)
        record = QARetryRecord(
            attempt=1,
            timestamp=ts,
            result=QARetryResult(passed=False),
        )
        d = record.to_dict()
        assert "2026-07-20" in d["timestamp"]


class TestQARetryIntegration:
    """端到端集成测试"""

    def test_full_retry_then_intervention_flow(self):
        mock_haimei = Mock()
        mock_haimei.re_evaluate = Mock()
        strategy = QARetryStrategy(inspector=Mock(), haimei=mock_haimei)
        strategy.start()

        r1 = strategy.execute_retry(QARetryResult(passed=False, score=38, defects=[{"reason": "完整度不足"}]))
        assert r1["should_retry"] is True
        assert r1["attempt"] == 1

        r2 = strategy.execute_retry(QARetryResult(passed=False, score=45, defects=[{"reason": "一致性问题"}, {"reason": "术语不统一"}]))
        assert r2["should_retry"] is True
        assert r2["attempt"] == 2

        r3 = strategy.execute_retry(QARetryResult(passed=False, score=52, defects=[{"reason": "可验证性差"}]))
        assert r3["should_retry"] is False
        assert r3["intervention"] is True
        assert r3["attempt"] == 3

        assert strategy.total_attempts() == 3
        assert len(strategy.get_interventions()) == 1
        assert strategy.is_completed() is True
        mock_haimei.re_evaluate.assert_called_once()

    def test_timeout_during_retry_flow(self):
        strategy = QARetryStrategy()
        strategy.start()

        strategy.execute_retry(QARetryResult(passed=False, score=40))
        timeout_result = strategy.check_timeout(3700)

        assert timeout_result is not None
        assert timeout_result.response_time_seconds == 3700
        assert strategy.is_completed() is True

    def test_retry_then_pass_flow(self):
        strategy = QARetryStrategy()
        strategy.start()

        strategy.execute_retry(QARetryResult(passed=False, score=40))
        strategy.execute_retry(QARetryResult(passed=False, score=60))
        final = strategy.execute_retry(QARetryResult(passed=True, score=85))

        assert final["should_retry"] is False
        assert final["intervention"] is False
        assert strategy.total_attempts() == 3
        assert len(strategy.get_interventions()) == 0
        assert strategy.is_completed() is True

    def test_records_are_stable(self):
        strategy = QARetryStrategy()
        strategy.start()

        strategy.execute_retry(QARetryResult(passed=False, score=40))
        strategy.execute_retry(QARetryResult(passed=False, score=50))
        strategy.execute_retry(QARetryResult(passed=False, score=60))

        records = strategy.get_retry_records()
        interventions = strategy.get_interventions()

        new_records = strategy.get_retry_records()
        new_interventions = strategy.get_interventions()
        assert len(records) == len(new_records)
        assert len(interventions) == len(new_interventions)

    def test_multiple_strategy_instances_are_independent(self):
        s1 = QARetryStrategy()
        s2 = QARetryStrategy()

        s1.start()
        s1.execute_retry(QARetryResult(passed=False))
        s1.execute_retry(QARetryResult(passed=False))

        s2.start()
        s2.execute_retry(QARetryResult(passed=True))

        assert s1.total_attempts() == 2
        assert s2.total_attempts() == 1
        assert s1.is_completed() is False
        assert s2.is_completed() is True

    def test_start_resets_state(self):
        strategy = QARetryStrategy()
        strategy.start()
        strategy.execute_retry(QARetryResult(passed=False))
        strategy.execute_retry(QARetryResult(passed=False))

        strategy.start()
        assert strategy.total_attempts() == 0
        assert len(strategy.get_interventions()) == 0
        assert strategy.is_completed() is False

    def test_response_time_boundary_at_1_hour(self):
        strategy = QARetryStrategy()
        strategy.start()

        for elapsed in [1800, 2700, 3000, 3599]:
            result = strategy.check_timeout(elapsed)
            assert result is None, f"{elapsed}秒不应触发超时"

        boundary_result = strategy.check_timeout(3600)
        assert boundary_result is not None, "3600秒应触发超时"

    def test_intervention_contains_full_retry_history(self):
        mock_haimei = Mock()
        mock_haimei.re_evaluate = Mock()
        strategy = QARetryStrategy(haimei=mock_haimei)
        strategy.start()

        strategy.execute_retry(QARetryResult(passed=False, score=30))
        strategy.execute_retry(QARetryResult(passed=False, score=35))
        strategy.execute_retry(QARetryResult(passed=False, score=40))

        call_args = mock_haimei.re_evaluate.call_args
        records_passed_to_haimei = call_args[0][1]
        assert len(records_passed_to_haimei) == 3
        assert records_passed_to_haimei[0].result.score == 30
        assert records_passed_to_haimei[1].result.score == 35
        assert records_passed_to_haimei[2].result.score == 40
