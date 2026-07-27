import time
import pytest
from unittest.mock import Mock, patch, call
from datetime import datetime, timedelta


class TaskError(Exception):
    """Celery 任务执行异常"""
    pass


class CeleryTaskRetry:
    """Celery 任务指数退避重试机制"""

    MAX_RETRIES = 3
    BACKOFF_INTERVALS = [1, 5, 15]  # 单位：分钟

    def __init__(self, task_func, alert_handler=None):
        self._task_func = task_func
        self._alert_handler = alert_handler or Mock()
        self.status = "pending"
        self.retry_count = 0
        self.retry_records = []
        self.error = None

    def execute_with_retry(self, *args, **kwargs):
        for attempt, interval in enumerate(self.BACKOFF_INTERVALS, start=1):
            self.retry_count = attempt
            try:
                result = self._task_func(*args, **kwargs)
                self.status = "success"
                self.retry_records.append({
                    "attempt": attempt,
                    "interval_mins": interval,
                    "timestamp": datetime.now(),
                    "result": "success",
                })
                return result
            except TaskError as e:
                self.error = str(e)
                self.retry_records.append({
                    "attempt": attempt,
                    "interval_mins": interval,
                    "timestamp": datetime.now(),
                    "result": "failed",
                    "error": str(e),
                })
                if attempt < self.MAX_RETRIES:
                    time.sleep(interval * 60)

        self.status = "blocked"
        self._alert_handler.alert(
            task_name=self._task_func.__name__,
            retries=self.retry_count,
            error=self.error,
            status=self.status,
        )
        return None


class TestCeleryTaskRetryExponentialBackoff:

    @pytest.fixture(autouse=True)
    def mock_sleep(self):
        with patch.object(time, "sleep") as m:
            yield m

    @pytest.fixture
    def alert_handler(self):
        return Mock()

    @pytest.fixture
    def task_func(self):
        return Mock()

    @pytest.fixture
    def retry(self, task_func, alert_handler):
        return CeleryTaskRetry(task_func, alert_handler)

    # --- 最大重试次数 ---

    def test_max_retries_is_3(self):
        assert CeleryTaskRetry.MAX_RETRIES == 3

    def test_fails_after_3_retries(self, task_func, retry):
        task_func.side_effect = TaskError("timeout")
        result = retry.execute_with_retry()
        assert result is None
        assert task_func.call_count == 3
        assert retry.retry_count == 3

    def test_no_infinite_retry(self, task_func, retry):
        task_func.side_effect = TaskError("service unavailable")
        retry.execute_with_retry()
        assert retry.retry_count <= CeleryTaskRetry.MAX_RETRIES

    # --- 指数退避间隔 ---

    def test_backoff_intervals_are_1_5_15(self):
        assert CeleryTaskRetry.BACKOFF_INTERVALS == [1, 5, 15]

    def test_sleep_intervals_in_seconds(self, mock_sleep, task_func, alert_handler):
        task_func.side_effect = TaskError("error")
        retry = CeleryTaskRetry(task_func, alert_handler)
        retry.execute_with_retry()
        expected_calls = [
            call(1 * 60),
            call(5 * 60),
        ]
        mock_sleep.assert_has_calls(expected_calls)

    def test_no_sleep_after_last_failure(self, mock_sleep, task_func, alert_handler):
        task_func.side_effect = TaskError("error")
        retry = CeleryTaskRetry(task_func, alert_handler)
        retry.execute_with_retry()
        assert mock_sleep.call_count == 2

    def test_retry_records_contain_intervals(self, task_func, retry):
        task_func.side_effect = TaskError("error")
        retry.execute_with_retry()
        intervals = [r["interval_mins"] for r in retry.retry_records]
        assert intervals == [1, 5, 15]

    # --- 重试后状态为 blocked ---

    def test_status_blocked_after_3_failures(self, task_func, retry):
        task_func.side_effect = TaskError("error")
        retry.execute_with_retry()
        assert retry.status == "blocked"

    def test_status_not_blocked_on_success(self, task_func, retry):
        task_func.return_value = "ok"
        retry.execute_with_retry()
        assert retry.status == "success"

    # --- 告警触发 ---

    def test_alert_triggered_after_blocked(self, task_func, alert_handler, retry):
        task_func.side_effect = TaskError("db connection lost")
        retry.execute_with_retry()
        alert_handler.alert.assert_called_once()
        call_kwargs = alert_handler.alert.call_args[1]
        assert call_kwargs["task_name"] == task_func.__name__
        assert call_kwargs["retries"] == 3
        assert call_kwargs["error"] == "db connection lost"
        assert call_kwargs["status"] == "blocked"

    def test_alert_not_triggered_on_success(self, task_func, alert_handler, retry):
        task_func.return_value = "ok"
        retry.execute_with_retry()
        alert_handler.alert.assert_not_called()

    def test_alert_not_triggered_on_partial_success(self, task_func, alert_handler):
        task_func.side_effect = [TaskError("err1"), "ok"]
        retry = CeleryTaskRetry(task_func, alert_handler)
        retry.execute_with_retry()
        alert_handler.alert.assert_not_called()
        assert retry.status == "success"

    # --- 中间重试成功 ---

    def test_success_on_first_retry(self, task_func, retry):
        task_func.side_effect = [TaskError("err"), "ok"]
        result = retry.execute_with_retry()
        assert result == "ok"
        assert retry.status == "success"
        assert task_func.call_count == 2
        assert retry.retry_count == 2

    def test_success_on_second_retry(self, task_func, retry):
        task_func.side_effect = [TaskError("err1"), TaskError("err2"), "ok"]
        result = retry.execute_with_retry()
        assert result == "ok"
        assert retry.status == "success"
        assert task_func.call_count == 3
        assert retry.retry_count == 3

    # --- 重试记录 ---

    def test_retry_records_length_on_all_fail(self, task_func, retry):
        task_func.side_effect = TaskError("err")
        retry.execute_with_retry()
        assert len(retry.retry_records) == 3

    def test_retry_records_length_on_success_first(self, task_func, retry):
        task_func.return_value = "ok"
        retry.execute_with_retry()
        assert len(retry.retry_records) == 1
        assert retry.retry_records[0]["result"] == "success"

    def test_retry_records_length_on_second_success(self, task_func, retry):
        task_func.side_effect = [TaskError("err"), "ok"]
        retry.execute_with_retry()
        assert len(retry.retry_records) == 2

    def test_retry_records_attempt_numbers(self, task_func, retry):
        task_func.side_effect = TaskError("err")
        retry.execute_with_retry()
        attempts = [r["attempt"] for r in retry.retry_records]
        assert attempts == [1, 2, 3]

    def test_retry_records_contain_timestamp(self, task_func, retry):
        task_func.side_effect = TaskError("err")
        retry.execute_with_retry()
        for record in retry.retry_records:
            assert isinstance(record["timestamp"], datetime)

    def test_retry_records_failed_contain_error(self, task_func, retry):
        task_func.side_effect = TaskError("specific error")
        retry.execute_with_retry()
        for record in retry.retry_records:
            assert record["error"] == "specific error"

    # --- 初始状态 ---

    def test_initial_status_is_pending(self, retry):
        assert retry.status == "pending"

    def test_initial_retry_count_is_0(self, retry):
        assert retry.retry_count == 0

    def test_initial_retry_records_empty(self, retry):
        assert retry.retry_records == []

    # --- 非 TaskError 异常传播 ---

    def test_non_task_error_propagates(self, task_func, retry):
        task_func.side_effect = ConnectionError("network down")
        with pytest.raises(ConnectionError):
            retry.execute_with_retry()

    # --- 无告警处理器 ---

    def test_default_alert_handler_is_mock(self, task_func):
        retry = CeleryTaskRetry(task_func)
        task_func.side_effect = TaskError("err")
        retry.execute_with_retry()
        retry._alert_handler.alert.assert_called_once()
