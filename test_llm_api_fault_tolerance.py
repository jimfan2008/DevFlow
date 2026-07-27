import pytest
import math
from datetime import datetime


class AlertSystem:
    """告警系统"""

    def __init__(self):
        self.alerts = []
        self.alert_threshold = 0.5  # 50% error rate threshold

    def check_and_alert(self, error_rate: float) -> dict:
        """检查错误率并生成告警"""
        if error_rate > self.alert_threshold:
            alert = {
                "error_rate": f"{error_rate * 100:.0f}%",
                "severity": "P1",
                "action": "circuit_breaker_tripped",
                "timestamp": datetime.now().isoformat()
            }
            self.alerts.append(alert)
            return alert
        return None


class CircuitBreaker:
    """熔断器"""

    def __init__(self, failure_threshold: int = 5, recovery_timeout: int = 30):
        self.failure_threshold = failure_threshold
        self.recovery_timeout = recovery_timeout
        self.failure_count = 0
        self.status = "closed"  # closed, open, half_open
        self.last_failure_time = None

    def record_failure(self):
        """记录一次失败"""
        self.failure_count += 1
        self.last_failure_time = datetime.now()
        if self.failure_count >= self.failure_threshold:
            self.status = "open"

    def record_success(self):
        """记录一次成功"""
        self.failure_count = 0
        self.status = "closed"

    def is_open(self) -> bool:
        """检查熔断器是否打开"""
        return self.status == "open"


class LLMAPIMonitor:
    """LLM API监控器"""

    def __init__(self):
        self.alert_system = AlertSystem()
        self.circuit_breaker = CircuitBreaker()
        self.success_count = 0
        self.failure_count = 0

    def record_response(self, success: bool):
        """记录API响应结果"""
        if success:
            self.success_count += 1
            self.circuit_breaker.record_success()
        else:
            self.failure_count += 1
            self.circuit_breaker.record_failure()

    def get_error_rate(self) -> float:
        """获取错误率"""
        total = self.success_count + self.failure_count
        if total == 0:
            return 0.0
        return self.failure_count / total

    def check_health(self) -> dict:
        """检查健康状态"""
        error_rate = self.get_error_rate()
        alert = self.alert_system.check_and_alert(error_rate)
        return {
            "error_rate": error_rate,
            "circuit_breaker_status": self.circuit_breaker.status,
            "alert": alert
        }

    def make_request(self, request_data: dict) -> dict:
        """模拟发出请求"""
        if self.circuit_breaker.is_open():
            return {
                "status_code": 503,
                "message": "Service Unavailable",
                "error": "Circuit breaker is open"
            }
        return {
            "status_code": 200,
            "message": "Success",
            "data": request_data
        }


class TestLLMAPIFaultTolerance:
    """测试LLM API故障切换P1告警触发"""

    def setup_method(self):
        """测试前设置"""
        self.monitor = LLMAPIMonitor()

    def test_error_rate_exceeds_threshold_triggers_p1_alert(self):
        """测试错误率超过阈值时触发P1告警"""
        # 模拟60%错误率：3成功4失败 = 4/7 ≈ 57%
        for _ in range(3):
            self.monitor.record_response(True)
        for _ in range(4):
            self.monitor.record_response(False)

        # 检查健康状态
        health = self.monitor.check_health()

        # 验证告警已触发
        assert health["alert"] is not None, "应该触发告警"
        assert health["alert"]["error_rate"] == "57%", f"错误率应为57%，实际为{health['alert']['error_rate']}"
        assert health["alert"]["severity"] == "P1", "告警级别应为P1"
        assert health["alert"]["action"] == "circuit_breaker_tripped", "应采取熔断措施"

    def test_circuit_breaker_trips_after_threshold(self):
        """测试熔断器在达到阈值后打开"""
        # 连续失败5次达到阈值
        for _ in range(5):
            self.monitor.record_response(False)

        # 验证熔断器状态
        assert self.monitor.circuit_breaker.status == "open", "熔断器应该打开"
        assert self.monitor.circuit_breaker.is_open(), "is_open()应返回True"

    def test_subsequent_requests_return_503_when_circuit_open(self):
        """测试熔断器打开后请求返回503"""
        # 触发熔断
        for _ in range(5):
            self.monitor.record_response(False)

        # 验证后续请求返回503
        response = self.monitor.make_request({"test": "data"})
        assert response["status_code"] == 503, f"状态码应为503，实际为{response['status_code']}"
        assert response["message"] == "Service Unavailable", "消息应为Service Unavailable"
        assert "Circuit breaker" in response["error"], "错误信息应提及熔断器"

    def test_exact_60_percent_error_rate_scenario(self):
        """测试精确60%错误率场景"""
        # 4成功6失败 = 6/10 = 60%
        for _ in range(4):
            self.monitor.record_response(True)
        for _ in range(6):
            self.monitor.record_response(False)

        health = self.monitor.check_health()

        # 验证错误率为60%
        assert math.isclose(health["error_rate"], 0.6, abs_tol=1e-9), f"错误率应为0.6，实际为{health['error_rate']}"
        assert health["alert"]["error_rate"] == "60%", f"告警错误率应为60%，实际为{health['alert']['error_rate']}"
        assert health["alert"]["severity"] == "P1", "告警级别应为P1"
        assert health["alert"]["action"] == "circuit_breaker_tripped", "应采取熔断措施"
        assert health["circuit_breaker_status"] == "open", "熔断器状态应为open"

    def test_alert_not_triggered_below_threshold(self):
        """测试错误率低于阈值时不触发告警"""
        # 9成功1失败 = 10%错误率
        for _ in range(9):
            self.monitor.record_response(True)
        for _ in range(1):
            self.monitor.record_response(False)

        health = self.monitor.check_health()

        # 验证未触发告警
        assert health["alert"] is None, "低于阈值不应触发告警"
        assert health["error_rate"] == 0.1, "错误率应为10%"
        assert health["circuit_breaker_status"] == "closed", "熔断器应保持关闭"

    def test_circuit_breaker_resets_after_success(self):
        """测试成功后熔断器状态重置"""
        # 触发熔断
        for _ in range(5):
            self.monitor.record_response(False)

        assert self.monitor.circuit_breaker.status == "open", "熔断器应该打开"

        # 模拟恢复：一次成功
        self.monitor.record_response(True)

        # 验证熔断器已关闭
        assert self.monitor.circuit_breaker.status == "closed", "成功后熔断器应关闭"
        assert not self.monitor.circuit_breaker.is_open(), "is_open()应返回False"

    def test_error_rate_at_exactly_50_percent_does_not_trigger_alert(self):
        """测试错误率恰好50%时不触发告警（严格大于阈值）"""
        # 1成功1失败 = 50%错误率，恰好等于阈值，> 0.5 为 False
        self.monitor.record_response(True)
        self.monitor.record_response(False)

        health = self.monitor.check_health()

        assert math.isclose(health["error_rate"], 0.5, abs_tol=1e-9), "错误率应为50%"
        assert health["alert"] is None, "恰好50%不应触发告警（使用严格大于）"

    def test_no_requests_yet_returns_zero_error_rate(self):
        """测试未记录任何请求时返回0%错误率（空数据边界）"""
        health = self.monitor.check_health()

        assert health["error_rate"] == 0.0, "无请求时错误率应为0"
        assert health["alert"] is None, "无请求时不应触发告警"
        assert health["circuit_breaker_status"] == "closed", "无请求时熔断器应处于关闭状态"

    def test_zero_error_rate_all_success(self):
        """测试100%成功时错误率为0%"""
        for _ in range(10):
            self.monitor.record_response(True)

        health = self.monitor.check_health()

        assert health["error_rate"] == 0.0, "全部成功时错误率应为0"
        assert health["alert"] is None, "全部成功时不应触发告警"

    def test_100_percent_error_rate_all_failures(self):
        """测试100%失败时的极端场景"""
        for _ in range(10):
            self.monitor.record_response(False)

        health = self.monitor.check_health()

        assert math.isclose(health["error_rate"], 1.0, abs_tol=1e-9), "全部失败时错误率应为100%"
        assert health["alert"] is not None, "100%错误率应触发告警"
        assert health["alert"]["severity"] == "P1", "告警级别应为P1"
        assert health["circuit_breaker_status"] == "open", "熔断器应打开"

    def test_circuit_breaker_does_not_open_at_4_failures(self):
        """测试熔断器在4次失败时不应打开（阈值-1边界）"""
        for _ in range(4):
            self.monitor.record_response(False)

        assert self.monitor.circuit_breaker.status == "closed", "4次失败时熔断器不应打开"
        assert not self.monitor.circuit_breaker.is_open(), "is_open()应返回False"
        assert self.monitor.circuit_breaker.failure_count == 4, "失败计数应为4"

    def test_circuit_breaker_closed_returns_200(self):
        """测试熔断器关闭时请求返回200"""
        response = self.monitor.make_request({"test": "data"})

        assert response["status_code"] == 200, f"状态码应为200，实际为{response['status_code']}"
        assert response["message"] == "Success", "消息应为Success"
        assert response["data"] == {"test": "data"}, "应返回原始请求数据"


if __name__ == "__main__":
    pytest.main([__file__, "-v"])
