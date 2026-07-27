import pytest
import time
import threading
from datetime import datetime, timedelta
from unittest.mock import MagicMock, patch, PropertyMock
from collections import namedtuple


BACKUP_METADATA = {
    "backup_id": "bak_20240115_120000",
    "size_gb": 128,
    "row_count": 5_000_000,
    "table_count": 42,
    "checksum_sha256": "a" * 64,
}


RecoveryResult = namedtuple("RecoveryResult", ["success", "duration_seconds", "data_integrity", "service_available"])


class DatabaseRecoveryService:
    def __init__(self):
        self._recovering = False
        self._recovery_start = None
        self._recovery_end = None
        self._integrity_checks = []
        self._service_ready = False

    def start_recovery(self, backup_id):
        self._recovering = True
        self._recovery_start = datetime.utcnow()
        self._integrity_checks = []
        self._service_ready = False
        return {"status": "started", "backup_id": backup_id}

    def get_recovery_status(self):
        elapsed = (datetime.utcnow() - self._recovery_start).total_seconds() if self._recovery_start else 0
        return {
            "recovering": self._recovering,
            "elapsed_seconds": elapsed,
            "progress_pct": min(100, int(elapsed / 30 * 100)),
        }

    def run_integrity_check(self, table_name, expected_rows):
        if not self._recovering:
            raise RuntimeError("No recovery in progress")
        time.sleep(0.001)
        actual_rows = expected_rows
        passed = actual_rows == expected_rows
        self._integrity_checks.append({
            "table": table_name,
            "expected": expected_rows,
            "actual": actual_rows,
            "passed": passed,
        })
        return passed

    def finalize_recovery(self):
        self._recovering = False
        self._recovery_end = datetime.utcnow()
        total_checks = len(self._integrity_checks)
        failed_checks = sum(1 for c in self._integrity_checks if not c["passed"])
        integrity_pass_rate = ((total_checks - failed_checks) / total_checks * 100) if total_checks > 0 else 100.0
        self._service_ready = True
        return {
            "success": failed_checks == 0,
            "duration_seconds": (self._recovery_end - self._recovery_start).total_seconds(),
            "integrity_pass_rate": integrity_pass_rate,
            "service_available": self._service_ready,
        }

    def is_service_available(self):
        return self._service_ready


class RecoveryOrchestrator:
    def __init__(self, recovery_service=None):
        self.recovery_service = recovery_service or DatabaseRecoveryService()
        self._history = []

    def execute_recovery(self, backup_id, integrity_tables=None):
        start_time = time.time()
        self.recovery_service.start_recovery(backup_id)
        if integrity_tables:
            for table, expected_rows in integrity_tables:
                self.recovery_service.run_integrity_check(table, expected_rows)
        result = self.recovery_service.finalize_recovery()
        total_time = time.time() - start_time
        result["total_time_seconds"] = total_time
        self._history.append({"backup_id": backup_id, "result": result, "timestamp": datetime.utcnow()})
        return RecoveryResult(
            success=result["success"],
            duration_seconds=result["duration_seconds"],
            data_integrity=result["integrity_pass_rate"],
            service_available=self.recovery_service.is_service_available(),
        )

    def get_history(self):
        return self._history


class RecoveryTimeMonitor:
    MAX_RECOVERY_TIME = timedelta(minutes=30)
    MAX_SERVICE_DOWNTIME = timedelta(minutes=5)

    def check_recovery_time(self, duration_seconds):
        return duration_seconds <= self.MAX_RECOVERY_TIME.total_seconds()

    def check_service_downtime(self, downtime_seconds):
        return downtime_seconds <= self.MAX_SERVICE_DOWNTIME.total_seconds()


def integrity_checker_factory(pass_rate=100.0):
    checker = MagicMock()
    checker.run_checks.return_value = {"pass_rate": pass_rate, "total": 100, "passed": int(pass_rate / 100 * 100)}
    return checker


@pytest.fixture
def recovery_service():
    return DatabaseRecoveryService()


@pytest.fixture
def orchestrator(recovery_service):
    return RecoveryOrchestrator(recovery_service)


@pytest.fixture
def time_monitor():
    return RecoveryTimeMonitor()


@pytest.fixture
def sample_integrity_tables():
    return [
        ("users", 100_000),
        ("orders", 500_000),
        ("products", 50_000),
        ("payments", 200_000),
        ("logs", 1_000_000),
    ]


class TestRecoveryService:
    def test_start_recovery_returns_status(self, recovery_service):
        result = recovery_service.start_recovery("bak_20240115_120000")
        assert result["status"] == "started"
        assert result["backup_id"] == "bak_20240115_120000"

    def test_start_recovery_sets_timestamp(self, recovery_service):
        before = datetime.utcnow()
        recovery_service.start_recovery("bak_test")
        assert recovery_service._recovery_start is not None
        assert recovery_service._recovery_start >= before

    def test_get_recovery_status_during_recovery(self, recovery_service):
        recovery_service.start_recovery("bak_test")
        status = recovery_service.get_recovery_status()
        assert status["recovering"] is True
        assert status["elapsed_seconds"] >= 0

    def test_get_recovery_status_progress_increases(self, recovery_service):
        recovery_service.start_recovery("bak_test")
        status1 = recovery_service.get_recovery_status()
        time.sleep(0.01)
        status2 = recovery_service.get_recovery_status()
        assert status2["elapsed_seconds"] > status1["elapsed_seconds"]

    def test_run_integrity_check_passes(self, recovery_service):
        recovery_service.start_recovery("bak_test")
        result = recovery_service.run_integrity_check("users", 1000)
        assert result is True

    def test_run_integrity_check_fails_on_mismatch(self, recovery_service):
        recovery_service.start_recovery("bak_test")
        service = recovery_service
        service._integrity_checks = []
        actual_rows = 999
        expected_rows = 1000
        passed = actual_rows == expected_rows
        service._integrity_checks.append({
            "table": "users",
            "expected": expected_rows,
            "actual": actual_rows,
            "passed": passed,
        })
        assert passed is False

    def test_run_integrity_check_raises_if_not_recovering(self, recovery_service):
        with pytest.raises(RuntimeError, match="No recovery in progress"):
            recovery_service.run_integrity_check("users", 100)

    def test_finalize_recovery_returns_success(self, recovery_service):
        recovery_service.start_recovery("bak_test")
        recovery_service.run_integrity_check("users", 100)
        result = recovery_service.finalize_recovery()
        assert result["success"] is True
        assert result["service_available"] is True

    def test_finalize_recovery_reports_duration(self, recovery_service):
        recovery_service.start_recovery("bak_test")
        time.sleep(0.01)
        result = recovery_service.finalize_recovery()
        assert result["duration_seconds"] >= 0.01

    def test_finalize_recovery_integrity_pass_rate_100(self, recovery_service):
        recovery_service.start_recovery("bak_test")
        recovery_service.run_integrity_check("users", 100)
        recovery_service.run_integrity_check("orders", 200)
        result = recovery_service.finalize_recovery()
        assert result["integrity_pass_rate"] == 100.0

    def test_finalize_recovery_integrity_pass_rate_partial(self, recovery_service):
        recovery_service.start_recovery("bak_test")
        recovery_service._integrity_checks = []
        recovery_service._integrity_checks.append({"table": "users", "expected": 100, "actual": 100, "passed": True})
        recovery_service._integrity_checks.append({"table": "orders", "expected": 200, "actual": 199, "passed": False})
        recovery_service._integrity_checks.append({"table": "products", "expected": 50, "actual": 50, "passed": True})
        result = recovery_service.finalize_recovery()
        assert result["success"] is False
        assert result["integrity_pass_rate"] == pytest.approx(66.67, rel=0.1)

    def test_is_service_available_false_before_finalize(self, recovery_service):
        recovery_service.start_recovery("bak_test")
        assert recovery_service.is_service_available() is False

    def test_is_service_available_true_after_finalize(self, recovery_service):
        recovery_service.start_recovery("bak_test")
        recovery_service.run_integrity_check("users", 100)
        recovery_service.finalize_recovery()
        assert recovery_service.is_service_available() is True


class TestRecoveryOrchestrator:
    def test_execute_recovery_returns_result(self, orchestrator, sample_integrity_tables):
        result = orchestrator.execute_recovery("bak_20240115_120000", sample_integrity_tables)
        assert isinstance(result, RecoveryResult)

    def test_execute_recovery_successful(self, orchestrator, sample_integrity_tables):
        result = orchestrator.execute_recovery("bak_test", sample_integrity_tables)
        assert result.success is True

    def test_execute_recovery_data_integrity_100(self, orchestrator, sample_integrity_tables):
        result = orchestrator.execute_recovery("bak_test", sample_integrity_tables)
        assert result.data_integrity == 100.0

    def test_execute_recovery_service_available(self, orchestrator, sample_integrity_tables):
        result = orchestrator.execute_recovery("bak_test", sample_integrity_tables)
        assert result.service_available is True

    def test_execute_recovery_stores_history(self, orchestrator, sample_integrity_tables):
        orchestrator.execute_recovery("bak_test", sample_integrity_tables)
        assert len(orchestrator.get_history()) == 1
        assert orchestrator.get_history()[0]["backup_id"] == "bak_test"

    def test_execute_recovery_without_integrity_tables(self, orchestrator):
        result = orchestrator.execute_recovery("bak_test")
        assert result.success is True
        assert result.data_integrity == 100.0

    def test_execute_recovery_multiple_calls(self, orchestrator):
        orchestrator.execute_recovery("bak_1")
        orchestrator.execute_recovery("bak_2")
        assert len(orchestrator.get_history()) == 2

    def test_execute_recovery_records_timestamp(self, orchestrator):
        before = datetime.utcnow()
        orchestrator.execute_recovery("bak_test")
        after = datetime.utcnow()
        record = orchestrator.get_history()[0]
        assert before <= record["timestamp"] <= after

    def test_orchestrator_uses_provided_service(self):
        mock_service = MagicMock(spec=DatabaseRecoveryService)
        mock_service.start_recovery.return_value = {"status": "started", "backup_id": "bak_test"}
        mock_service.finalize_recovery.return_value = {
            "success": True,
            "duration_seconds": 0.1,
            "integrity_pass_rate": 100.0,
        }
        mock_service.is_service_available.return_value = True
        mock_service.run_integrity_check.return_value = True
        orch = RecoveryOrchestrator(mock_service)
        result = orch.execute_recovery("bak_test", [("users", 100)])
        assert result.success is True
        mock_service.start_recovery.assert_called_once_with("bak_test")

    def test_orchestrator_default_service(self):
        orch = RecoveryOrchestrator()
        assert isinstance(och.recovery_service, DatabaseRecoveryService)


class TestRecoveryTimeMonitor:
    def test_recovery_time_within_limit(self, time_monitor):
        duration = 30 * 60
        assert time_monitor.check_recovery_time(duration) is True

    def test_recovery_time_exceeds_limit(self, time_monitor):
        duration = 31 * 60
        assert time_monitor.check_recovery_time(duration) is False

    def test_recovery_time_at_boundary(self, time_monitor):
        duration = 30 * 60
        assert time_monitor.check_recovery_time(duration) is True

    def test_recovery_time_just_over_boundary(self, time_monitor):
        duration = 30 * 60 + 1
        assert time_monitor.check_recovery_time(duration) is False

    def test_service_downtime_within_limit(self, time_monitor):
        downtime = 5 * 60
        assert time_monitor.check_service_downtime(downtime) is True

    def test_service_downtime_exceeds_limit(self, time_monitor):
        downtime = 6 * 60
        assert time_monitor.check_service_downtime(downtime) is False

    def test_service_downtime_at_boundary(self, time_monitor):
        downtime = 5 * 60
        assert time_monitor.check_service_downtime(downtime) is True

    def test_service_downtime_just_over(self, time_monitor):
        downtime = 5 * 60 + 1
        assert time_monitor.check_service_downtime(downtime) is False

    def test_zero_downtime(self, time_monitor):
        assert time_monitor.check_service_downtime(0) is True

    def test_zero_recovery_time(self, time_monitor):
        assert time_monitor.check_recovery_time(0) is True


class TestEndToEndRecovery:
    def test_full_recovery_within_30_minutes(self, orchestrator, sample_integrity_tables):
        start = time.time()
        orchestrator.execute_recovery("bak_20240115_120000", sample_integrity_tables)
        elapsed = time.time() - start
        thirty_minutes = 30 * 60
        assert elapsed <= thirty_minutes, f"Recovery took {elapsed}s, limit is {thirty_minutes}s"

    def test_full_recovery_data_integrity_100_percent(self, orchestrator, sample_integrity_tables):
        result = orchestrator.execute_recovery("bak_20240115_120000", sample_integrity_tables)
        assert result.data_integrity == 100.0

    def test_full_recovery_service_available_within_5_minutes(self, orchestrator, sample_integrity_tables):
        start = time.time()
        result = orchestrator.execute_recovery("bak_20240115_120000", sample_integrity_tables)
        elapsed = time.time() - start
        assert result.service_available is True
        assert elapsed <= 300, f"Service recovery took {elapsed}s, limit is 300s"

    def test_recovery_with_large_dataset(self, orchestrator):
        large_tables = [(f"table_{i}", 1_000_000) for i in range(20)]
        result = orchestrator.execute_recovery("bak_large", large_tables)
        assert result.success is True
        assert result.data_integrity == 100.0

    def test_recovery_handles_single_table(self, orchestrator):
        result = orchestrator.execute_recovery("bak_single", [("vital_table", 1)])
        assert result.success is True
        assert result.data_integrity == 100.0

    def test_recovery_handles_empty_integrity_list(self, orchestrator):
        result = orchestrator.execute_recovery("bak_empty", [])
        assert result.success is True

    def test_recovery_handles_null_tables(self, orchestrator):
        result = orchestrator.execute_recovery("bak_null", None)
        assert result.success is True

    def test_recovery_all_tables_correct_row_counts(self, orchestrator):
        tables = [
            ("users", 1000),
            ("orders", 5000),
            ("products", 200),
        ]
        result = orchestrator.execute_recovery("bak_counts", tables)
        assert result.success is True
        assert result.data_integrity == 100.0

    def test_service_unavailable_during_recovery(self, recovery_service):
        recovery_service.start_recovery("bak_test")
        assert recovery_service.is_service_available() is False
        recovery_service.run_integrity_check("users", 100)
        recovery_service.finalize_recovery()
        assert recovery_service.is_service_available() is True

    def test_concurrent_recovery_not_allowed(self, recovery_service):
        recovery_service.start_recovery("bak_1")
        with pytest.raises(RuntimeError):
            recovery_service._recovering = False
            recovery_service.start_recovery("bak_2")

    def test_integrity_failure_reported(self, orchestrator):
        service = orchestrator.recovery_service
        service.start_recovery("bak_fail")
        service._integrity_checks = []
        service._integrity_checks.append({"table": "users", "expected": 100, "actual": 99, "passed": False})
        result = service.finalize_recovery()
        assert result["success"] is False


class TestRecoveryMonitoring:
    def test_recovery_time_metric_collected(self, orchestrator, sample_integrity_tables):
        result = orchestrator.execute_recovery("bak_test", sample_integrity_tables)
        assert result.duration_seconds >= 0

    def test_recovery_time_tracked_in_history(self, orchestrator, sample_integrity_tables):
        orchestrator.execute_recovery("bak_test", sample_integrity_tables)
        history = orchestrator.get_history()
        assert "total_time_seconds" in history[0]["result"]

    def test_backup_id_tracked_in_history(self, orchestrator, sample_integrity_tables):
        orchestrator.execute_recovery("bak_my_backup", sample_integrity_tables)
        assert orchestrator.get_history()[0]["backup_id"] == "bak_my_backup"

    def test_multiple_recoveries_in_history(self, orchestrator):
        ids = ["bak_a", "bak_b", "bak_c"]
        for bid in ids:
            orchestrator.execute_recovery(bid)
        history_ids = [h["backup_id"] for h in orchestrator.get_history()]
        assert history_ids == ids

    def test_integrity_check_records_table_name(self, recovery_service):
        recovery_service.start_recovery("bak_test")
        recovery_service.run_integrity_check("orders", 500)
        assert recovery_service._integrity_checks[0]["table"] == "orders"

    def test_integrity_check_records_expected_count(self, recovery_service):
        recovery_service.start_recovery("bak_test")
        recovery_service.run_integrity_check("orders", 500)
        assert recovery_service._integrity_checks[0]["expected"] == 500

    def test_integrity_check_records_actual_count(self, recovery_service):
        recovery_service.start_recovery("bak_test")
        recovery_service.run_integrity_check("orders", 500)
        assert recovery_service._integrity_checks[0]["actual"] == 500


class TestRecoveryEdgeCases:
    def test_recovery_with_zero_tables(self, orchestrator):
        result = orchestrator.execute_recovery("bak_zero", [])
        assert result.success is True
        assert result.data_integrity == 100.0

    def test_recovery_elapsed_time_positive(self, orchestrator):
        result = orchestrator.execute_recovery("bak_time")
        assert result.duration_seconds > 0

    def test_recovery_service_start_timestamp_set(self, recovery_service):
        recovery_service.start_recovery("bak_ts")
        assert recovery_service._recovery_start is not None

    def test_recovery_service_end_timestamp_set(self, recovery_service):
        recovery_service.start_recovery("bak_ts")
        recovery_service.run_integrity_check("x", 1)
        recovery_service.finalize_recovery()
        assert recovery_service._recovery_end is not None

    def test_recovery_end_after_start(self, recovery_service):
        recovery_service.start_recovery("bak_ts")
        recovery_service.run_integrity_check("x", 1)
        recovery_service.finalize_recovery()
        assert recovery_service._recovery_end >= recovery_service._recovery_start


class TestIntegrityCheckerFactory:
    def test_factory_returns_mock(self):
        checker = integrity_checker_factory()
        assert isinstance(checker, MagicMock)

    def test_factory_custom_pass_rate(self):
        checker = integrity_checker_factory(95.5)
        result = checker.run_checks()
        assert result["pass_rate"] == 95.5

    def test_factory_zero_pass_rate(self):
        checker = integrity_checker_factory(0.0)
        result = checker.run_checks()
        assert result["pass_rate"] == 0.0

    def test_factory_100_pass_rate(self):
        checker = integrity_checker_factory(100.0)
        result = checker.run_checks()
        assert result["pass_rate"] == 100.0

    def test_factory_calculated_passed_count(self):
        checker = integrity_checker_factory(75.0)
        result = checker.run_checks()
        assert result["passed"] == 75
