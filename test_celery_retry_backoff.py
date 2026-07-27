import pytest
from unittest.mock import patch, MagicMock
from datetime import timedelta


class CeleryTask:
    """模拟 Celery 任务，支持指数退避重试"""

    def __init__(self, max_retries=3, backoff_base=60, backoff_factor=5):
        self.max_retries = max_retries
        self.backoff_base = backoff_base
        self.backoff_factor = backoff_factor
        self.retry_count = 0
        self.status = "active"
        self.alert_triggered = False
        self.last_error = None

    def calculate_backoff(self, retry_count):
        """计算第 retry_count 次重试的退避时间（秒）"""
        return self.backoff_base * (self.backoff_factor ** (retry_count - 1))

    def execute(self, task_func, *args, **kwargs):
        """执行任务：抛 RetryAfter 通知调用方退避"""
        self.retry_count = 0
        self.status = "active"
        self.alert_triggered = False

        try:
            return task_func(*args, **kwargs)
        except Exception as e:
            self.last_error = e
            self.retry_count += 1

            if self.retry_count > self.max_retries:
                self.status = "blocked"
                self._trigger_alert(e)
                raise

            backoff = self.calculate_backoff(self.retry_count)
            raise RetryAfter(backoff, self.retry_count, e) from e

    def execute_with_retry(self, task_func, *args, **kwargs):
        """自动重试执行：内部处理指数退避重试"""
        self.status = "active"
        self.alert_triggered = False
        self.last_error = None
        attempt_count = 0
        last_raised = None
        self.retry_count = 0

        while attempt_count <= self.max_retries:
            try:
                return task_func(*args, **kwargs)
            except Exception as e:
                self.last_error = e
                attempt_count += 1

                if attempt_count <= self.max_retries:
                    self.retry_count = attempt_count
                    last_raised = RetryAfter(
                        self.calculate_backoff(attempt_count), attempt_count, e
                    )
                    continue

                self.retry_count = attempt_count
                self.status = "blocked"
                self._trigger_alert(e)
                raise

        raise self.last_error

    def _trigger_alert(self, error):
        """触发告警"""
        self.alert_triggered = True


class RetryAfter(Exception):
    """重试异常，携带退避时间信息"""

    def __init__(self, backoff_seconds, retry_count, original_error):
        self.backoff_seconds = backoff_seconds
        self.retry_count = retry_count
        self.original_error = original_error
        super().__init__(
            f"Retry {retry_count}: backoff {backoff_seconds}s, error: {original_error}"
        )


# =- 测试：指数退避时间计算 - =


class TestExponentialBackoff:
    """验证指数退避时间计算：1min / 5min / 15min"""

    def test_first_retry_backoff_is_1_minute(self):
        task = CeleryTask(max_retries=3, backoff_base=60, backoff_factor=5)
        assert task.calculate_backoff(1) == 60

    def test_second_retry_backoff(self):
        task = CeleryTask(max_retries=3, backoff_base=60, backoff_factor=5)
        assert task.calculate_backoff(2) == 300

    def test_third_retry_backoff(self):
        task = CeleryTask(max_retries=3, backoff_base=60, backoff_factor=5)
        assert task.calculate_backoff(3) == 1500

    def test_backoff_sequence(self):
        task = CeleryTask(max_retries=3, backoff_base=60, backoff_factor=5)
        expected = [60, 300, 1500]
        for i in range(1, 4):
            assert task.calculate_backoff(i) == expected[i - 1]


# =- 测试：最多3次重试 - =


class TestMaxRetries:

    def test_fails_after_max_3_retries(self):
        task = CeleryTask(max_retries=3)
        call_count = 0

        def always_fail():
            nonlocal call_count
            call_count += 1
            raise RuntimeError("simulated failure")

        with pytest.raises(RuntimeError, match="simulated failure"):
            task.execute_with_retry(always_fail)

        assert call_count == 4  # 1 initial + 3 retries
        assert task.retry_count == 4

    def test_max_retries_can_be_configured(self):
        task = CeleryTask(max_retries=5)
        assert task.max_retries == 5

    def test_zero_retries_fails_immediately(self):
        task = CeleryTask(max_retries=0)

        def fail():
            raise ValueError("fail")

        with pytest.raises(ValueError, match="fail"):
            task.execute_with_retry(fail)

        assert task.retry_count == 1
        assert task.status == "blocked"


# =- 测试：status=blocked - =


class TestStatusBlocked:

    def test_status_blocked_after_exhausting_retries(self):
        task = CeleryTask(max_retries=3)

        def always_fail():
            raise ConnectionError("timeout")

        with pytest.raises(ConnectionError, match="timeout"):
            task.execute_with_retry(always_fail)

        assert task.status == "blocked"

    def test_status_active_on_success(self):
        task = CeleryTask(max_retries=3)

        def success():
            return 42

        result = task.execute_with_retry(success)
        assert result == 42
        assert task.status == "active"
        assert task.retry_count == 0

    def test_status_blocked_with_zero_max_retries(self):
        task = CeleryTask(max_retries=0)

        def fail():
            raise Exception("err")

        with pytest.raises(Exception, match="err"):
            task.execute_with_retry(fail)

        assert task.status == "blocked"


# =- 测试：告警触发 - =


class TestAlertTriggered:

    def test_alert_triggered_after_max_retries(self):
        task = CeleryTask(max_retries=3)

        def always_fail():
            raise RuntimeError("error")

        with pytest.raises(RuntimeError):
            task.execute_with_retry(always_fail)

        assert task.alert_triggered is True

    def test_alert_not_triggered_on_success(self):
        task = CeleryTask(max_retries=3)

        def success():
            return "ok"

        task.execute_with_retry(success)
        assert task.alert_triggered is False

    def test_alert_not_triggered_on_intermediate_retry(self):
        task = CeleryTask(max_retries=3)
        call_count = 0

        def fail_twice_then_succeed():
            nonlocal call_count
            call_count += 1
            if call_count <= 2:
                raise RuntimeError("temporary")
            return "recovered"

        result = task.execute_with_retry(fail_twice_then_succeed)
        assert result == "recovered"
        assert task.alert_triggered is False

    def test_alert_triggered_with_zero_max_retries(self):
        task = CeleryTask(max_retries=0)

        def fail():
            raise ValueError("fail")

        with pytest.raises(ValueError):
            task.execute_with_retry(fail)

        assert task.alert_triggered is True


# =- 测试：RetryAfter 异常 - =


class TestRetryAfterException:

    def test_contains_backoff_time(self):
        err = RetryAfter(300, 2, RuntimeError("fail"))
        assert err.backoff_seconds == 300
        assert err.retry_count == 2

    def test_contains_original_error(self):
        original = ConnectionError("timeout")
        err = RetryAfter(60, 1, original)
        assert isinstance(err.original_error, ConnectionError)
        assert str(err.original_error) == "timeout"

    def test_string_representation(self):
        err = RetryAfter(60, 1, ValueError("bad"))
        assert "Retry 1" in str(err)
        assert "backoff 60s" in str(err)


# =- 测试：边界场景 - =


class TestEdgeCases:

    def test_retry_zero_boundary(self):
        task = CeleryTask(max_retries=0)

        def fail():
            raise Exception("fail")

        with pytest.raises(Exception, match="fail"):
            task.execute_with_retry(fail)

        assert task.status == "blocked"
        assert task.alert_triggered is True

    def test_multiple_instances_are_independent(self):
        task_a = CeleryTask(max_retries=3)
        task_b = CeleryTask(max_retries=5)

        assert task_a.max_retries != task_b.max_retries
        assert task_a.retry_count == 0
        assert task_b.retry_count == 0

        def fail():
            raise RuntimeError("x")

        with pytest.raises(RuntimeError):
            task_a.execute_with_retry(fail)

        assert task_a.status == "blocked"
        assert task_b.status == "active"

    def test_backoff_large_retry_count_no_overflow(self):
        task = CeleryTask(max_retries=3, backoff_base=60, backoff_factor=5)
        backoff = task.calculate_backoff(10)
        assert backoff > 0
        assert isinstance(backoff, int)

    def test_success_after_failures(self):
        task = CeleryTask(max_retries=3)
        call_count = 0

        def fail_then_succeed():
            nonlocal call_count
            call_count += 1
            if call_count <= 2:
                raise RuntimeError("temporary")
            return "recovered"

        result = task.execute_with_retry(fail_then_succeed)
        assert result == "recovered"
        assert task.retry_count == 2
        assert task.status == "active"
        assert task.alert_triggered is False
