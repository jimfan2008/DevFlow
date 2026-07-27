import pytest
from unittest.mock import patch, MagicMock
from datetime import datetime, timedelta
import time


# ── Mock modules ──────────────────────────────────────────────

class MockOllamaClient:
    """模拟Ollama客户端"""

    def __init__(self, healthy=True):
        self._healthy = healthy

    def chat(self, model, messages):
        if not self._healthy:
            raise ConnectionError("Ollama服务不可用")
        return {"content": f"ollama-{model} response"}

    def list_models(self):
        return ["llama3", "qwen2"] if self._healthy else []


class MockCloudAPI:
    """模拟云端模型 API 客户端"""

    def __init__(self, api_key="test-key"):
        self.api_key = api_key
        self._call_count = 0
        self._total_cost = 0.0

    def chat(self, model, messages):
        self._call_count += 1
        # 每次调用模拟费用 $0.50
        cost = 0.50
        self._total_cost += cost
        return {"content": f"cloud-{model} response", "cost": cost}

    @property
    def total_cost(self):
        return self._total_cost

    @property
    def call_count(self):
        return self._call_count

    def reset(self):
        self._call_count = 0
        self._total_cost = 0.0


class BudgetManager:
    """单日预算管理"""

    DEFAULT_DAILY_BUDGET = 50.0  # $50/天

    def __init__(self, daily_budget=None):
        self.daily_budget = daily_budget or self.DEFAULT_DAILY_BUDGET
        self._spent = 0.0
        self._date = datetime.now().date()
        self._circuit_open = False

    def record_cost(self, amount):
        today = datetime.now().date()
        if today != self._date:
            self._spent = 0.0
            self._date = today
            self._circuit_open = False

        if self._circuit_open:
            return

        self._spent += amount
        if self._spent >= self.daily_budget:
            self._circuit_open = True

    @property
    def remaining(self):
        return max(0.0, self.daily_budget - self._spent)

    @property
    def utilization_ratio(self):
        return self._spent / self.daily_budget if self.daily_budget > 0 else 0.0

    @property
    def is_circuit_open(self):
        return self._circuit_open


class FallbackRouter:
    """
    L1/L2 降级路由控制器

    L1: Ollama（本地模型）
    L2: 云端 API
    """

    DEFAULT_QUEUE_TIMEOUT = 60  # 秒

    def __init__(
        self,
        ollama_client=None,
        cloud_client=None,
        budget_manager=None,
        queue_timeout=None,
    ):
        self.ollama = ollama_client or MockOllamaClient(healthy=True)
        self.cloud = cloud_client or MockCloudAPI()
        self.budget = budget_manager or BudgetManager()
        self.queue_timeout = queue_timeout or self.DEFAULT_QUEUE_TIMEOUT
        self._current_level = "L1"
        self._fallback_triggered = False

    @property
    def current_level(self):
        return self._current_level

    @property
    def is_fallback_active(self):
        return self._fallback_triggered

    def chat(self, model, messages):
        """执行对话请求，自动处理降级逻辑"""
        # 检查云端预算熔断
        if self.budget.is_circuit_open:
            return self._circuit_breaker_response()

        # 尝试 L1: Ollama
        try:
            result = self._try_ollama(model, messages)
            return result
        except (ConnectionError, OSError, TimeoutError) as e:
            self._trigger_fallback(e)
            return self._call_cloud(model, messages)

    def _try_ollama(self, model, messages):
        """尝试 Ollama 请求，含排队超时检测"""
        start = time.time()
        try:
            return self.ollama.chat(model, messages)
        except Exception:
            elapsed = time.time() - start
            if elapsed >= self.queue_timeout:
                raise TimeoutError(
                    f"Ollama排队超时 ({elapsed:.1f}s >= {self.queue_timeout}s)"
                )
            raise

    def _trigger_fallback(self, error):
        """触发从 L1 到 L2 的降级"""
        self._current_level = "L2"
        self._fallback_triggered = True

    def _call_cloud(self, model, messages):
        """调用云端 API"""
        if self.budget.is_circuit_open:
            return self._circuit_breaker_response()

        result = self.cloud.chat(model, messages)
        cost = result.get("cost", 0.0)
        self.budget.record_cost(cost)
        return result

    def _circuit_breaker_response(self):
        """熔断状态下的响应"""
        return {
            "content": "SERVICE_UNAVAILABLE: 云端预算已达上限，服务已熔断",
            "error": "budget_circuit_open",
        }

    def reset(self):
        """重置路由状态（用于测试）"""
        self._current_level = "L1"
        self._fallback_triggered = False


# ── Pytest fixtures ───────────────────────────────────────────

@pytest.fixture
def healthy_ollama():
    return MockOllamaClient(healthy=True)


@pytest.fixture
def broken_ollama():
    return MockOllamaClient(healthy=False)


@pytest.fixture
def cloud_api():
    client = MockCloudAPI()
    yield client
    client.reset()


@pytest.fixture
def budget_mgr():
    return BudgetManager(daily_budget=50.0)


@pytest.fixture
def router(healthy_ollama, cloud_api, budget_mgr):
    return FallbackRouter(
        ollama_client=healthy_ollama,
        cloud_client=cloud_api,
        budget_manager=budget_mgr,
        queue_timeout=60,
    )


@pytest.fixture
def router_broken_ollama(broken_ollama, cloud_api, budget_mgr):
    return FallbackRouter(
        ollama_client=broken_ollama,
        cloud_client=cloud_api,
        budget_manager=budget_mgr,
        queue_timeout=60,
    )


# ── Tests: L1 正常时不走降级 ──────────────────────────────────

class TestL1Healthy:
    """Ollama 正常时，请求应由 L1 直接处理，不触发降级"""

    def test_initial_level_is_l1(self, router):
        assert router.current_level == "L1"
        assert not router.is_fallback_active

    def test_chat_returns_ollama_response(self, router, healthy_ollama):
        result = router.chat("llama3", [{"role": "user", "content": "你好"}])
        assert "ollama-" in result["content"]
        assert router.current_level == "L1"
        assert not router.is_fallback_active

    def test_cloud_not_called_when_ollama_healthy(self, router, cloud_api):
        router.chat("llama3", [{"role": "user", "content": "hello"}])
        assert cloud_api.call_count == 0

    def test_budget_not_consumed_when_ollama_healthy(self, router, budget_mgr):
        router.chat("llama3", [{"role": "user", "content": "hello"}])
        assert budget_mgr.remaining == 50.0
        assert budget_mgr.utilization_ratio == 0.0


# ── Tests: L1 降级至 L2 ───────────────────────────────────────

class TestFallbackL1ToL2:
    """Ollama 故障时，自动降级到 L2 云端 API"""

    def test_fallback_triggers_on_connection_error(
        self, router_broken_ollama, broken_ollama
    ):
        result = router_broken_ollama.chat("llama3", [{"role": "user", "content": "你好"}])
        assert router_broken_ollama.current_level == "L2"
        assert router_broken_ollama.is_fallback_active
        assert "cloud-" in result["content"]

    def test_cloud_called_after_fallback(self, router_broken_ollama, cloud_api):
        router_broken_ollama.chat("llama3", [{"role": "user", "content": "test"}])
        assert cloud_api.call_count == 1

    def test_budget_consumed_after_fallback(self, router_broken_ollama, budget_mgr):
        router_broken_ollama.chat("llama3", [{"role": "user", "content": "test"}])
        assert budget_mgr.remaining < 50.0
        assert budget_mgr._spent == 0.50

    def test_multiple_fallback_calls_accumulate_cost(
        self, router_broken_ollama, budget_mgr
    ):
        for _ in range(5):
            router_broken_ollama.chat("llama3", [{"role": "user", "content": "x"}])
        assert budget_mgr._spent == 5 * 0.50  # $2.50
        assert budget_mgr.remaining == 50.0 - 2.50


# ── Tests: 排队超时触发降级 ───────────────────────────────────

class TestQueueTimeoutFallback:
    """排队超时 60 秒应触发降级"""

    def test_timeout_error_triggers_fallback(self, cloud_api, budget_mgr):
        ollama = MockOllamaClient(healthy=True)
        # 模拟一个总是超时的客户端
        original_chat = ollama.chat

        def slow_chat(*args, **kwargs):
            raise TimeoutError("Ollama排队超时")

        ollama.chat = slow_chat

        router = FallbackRouter(
            ollama_client=ollama,
            cloud_client=cloud_api,
            budget_manager=budget_mgr,
            queue_timeout=60,
        )
        router.chat("llama3", [{"role": "user", "content": "hello"}])
        assert router.current_level == "L2"
        assert router.is_fallback_active

    def test_shorter_timeout_still_triggers(self, cloud_api):
        """即使设置较短的超时时间，Ollama故障仍触发降级"""
        ollama = MockOllamaClient(healthy=False)
        router = FallbackRouter(
            ollama_client=ollama,
            cloud_client=cloud_api,
            budget_manager=BudgetManager(daily_budget=50.0),
            queue_timeout=5,
        )
        result = router.chat("llama3", [{"role": "user", "content": "test"}])
        assert router.current_level == "L2"
        assert "cloud-" in result["content"]

    def test_timeout_error_type_caught(self):
        """TimeoutError 应被捕获并触发降级"""
        ollama = MockOllamaClient(healthy=True)

        def failing_chat(*args, **kwargs):
            raise TimeoutError("queue full")

        ollama.chat = failing_chat
        cloud = MockCloudAPI()
        router = FallbackRouter(
            ollama_client=ollama,
            cloud_client=cloud,
            budget_manager=BudgetManager(daily_budget=50.0),
            queue_timeout=60,
        )
        router.chat("model", [{"role": "user", "content": "x"}])
        assert router.is_fallback_active
        assert cloud.call_count == 1


# ── Tests: 单日预算 $50 ───────────────────────────────────────

class TestDailyBudget:
    """单日预算 $50 相关测试"""

    def test_default_budget_is_50(self):
        bm = BudgetManager()
        assert bm.daily_budget == 50.0

    def test_budget_remains_after_no_usage(self, budget_mgr):
        assert budget_mgr.remaining == 50.0

    def test_budget_decreases_with_cloud_cost(self, budget_mgr, cloud_api):
        budget_mgr.record_cost(5.0)
        assert budget_mgr.remaining == 45.0
        assert budget_mgr.utilization_ratio == 0.1

    def test_budget_utilization_at_50_percent(self, budget_mgr):
        budget_mgr.record_cost(25.0)
        assert budget_mgr.utilization_ratio == pytest.approx(0.5)

    def test_custom_budget(self):
        bm = BudgetManager(daily_budget=100.0)
        assert bm.daily_budget == 100.0
        bm.record_cost(30.0)
        assert bm.remaining == 70.0


# ── Tests: 预算100%熔断 ──────────────────────────────────────

class TestBudgetCircuitBreaker:
    """预算达到 100% 时自动熔断"""

    def test_circuit_opens_at_100_percent(self, budget_mgr):
        budget_mgr.record_cost(50.0)
        assert budget_mgr.is_circuit_open is True
        assert budget_mgr.remaining == 0.0
        assert budget_mgr.utilization_ratio == pytest.approx(1.0)

    def test_circuit_opens_when_over_budget(self, budget_mgr):
        budget_mgr.record_cost(55.0)
        assert budget_mgr.is_circuit_open is True
        assert budget_mgr.remaining == 0.0

    def test_circuit_prevents_cloud_calls(self, cloud_api, budget_mgr):
        budget_mgr.record_cost(50.0)  # 达到100%
        assert budget_mgr.is_circuit_open

        ollama = MockOllamaClient(healthy=False)
        router = FallbackRouter(
            ollama_client=ollama,
            cloud_client=cloud_api,
            budget_manager=budget_mgr,
        )
        result = router.chat("llama3", [{"role": "user", "content": "test"}])
        assert result.get("error") == "budget_circuit_open"
        assert cloud_api.call_count == 0

    def test_fallback_respects_open_circuit(self, cloud_api, budget_mgr):
        """即使 Ollama 故障，熔断打开时不应调用云端"""
        budget_mgr.record_cost(50.0)
        ollama = MockOllamaClient(healthy=False)
        router = FallbackRouter(
            ollama_client=ollama,
            cloud_client=cloud_api,
            budget_manager=budget_mgr,
        )
        result = router.chat("qwen", [{"role": "user", "content": "hi"}])
        assert "SERVICE_UNAVAILABLE" in result["content"]
        assert cloud_api.call_count == 0

    def test_incremental_cost_opens_circuit(self, budget_mgr):
        """逐步累积费用，到达$50时熔断"""
        for _ in range(99):
            budget_mgr.record_cost(0.50)  # $49.50
        assert not budget_mgr.is_circuit_open
        budget_mgr.record_cost(0.50)  # $50.00
        assert budget_mgr.is_circuit_open

    def test_circuit_response_format(self, cloud_api, budget_mgr):
        budget_mgr.record_cost(50.0)
        router = FallbackRouter(
            ollama_client=MockOllamaClient(healthy=True),
            cloud_client=cloud_api,
            budget_manager=budget_mgr,
        )
        result = router._circuit_breaker_response()
        assert "error" in result
        assert result["error"] == "budget_circuit_open"
        assert "content" in result


# ── Tests: 端到端降级流程 ─────────────────────────────────────

class TestEndToEnd:
    """完整的降级流程测试"""

    def test_full_fallback_flow(self):
        """Ollama故障 -> 降级L2 -> 云端回复 -> 预算扣减"""
        ollama = MockOllamaClient(healthy=False)
        cloud = MockCloudAPI()
        budget = BudgetManager(daily_budget=50.0)
        router = FallbackRouter(ollama, cloud, budget)

        result = router.chat("llama3", [{"role": "user", "content": "你好"}])
        assert router.current_level == "L2"
        assert router.is_fallback_active
        assert "cloud-" in result["content"]
        assert cloud.call_count == 1
        assert budget.remaining == 49.50

    def test_budget_exhaustion_then_circuit_break(self):
        """累积调用直到预算耗尽，验证熔断"""
        ollama = MockOllamaClient(healthy=False)
        cloud = MockCloudAPI()
        budget = BudgetManager(daily_budget=50.0)
        router = FallbackRouter(ollama, cloud, budget)

        # 100次调用 = $50，刚好达到熔断点
        for i in range(100):
            router.chat("llama3", [{"role": "user", "content": f"msg-{i}"}])

        assert budget.is_circuit_open
        assert cloud.call_count == 100

        # 第101次请求应被熔断拦截
        result = router.chat("llama3", [{"role": "user", "content": "overflow"}])
        assert result.get("error") == "budget_circuit_open"
        assert cloud.call_count == 100  # 不应再增加

    def test_reset_restores_l1(self, router):
        """重置路由状态回到 L1"""
        router._current_level = "L2"
        router._fallback_triggered = True
        router.reset()
        assert router.current_level == "L1"
        assert not router.is_fallback_active

    def test_ollama_recovery_does_not_auto_switch_back(self, cloud_api):
        """降级后即使Ollama恢复，也需要显式reset"""
        ollama = MockOllamaClient(healthy=True)
        # 先制造故障
        ollama._healthy = False
        router = FallbackRouter(
            ollama_client=ollama,
            cloud_client=cloud_api,
            budget_manager=BudgetManager(daily_budget=50.0),
        )
        router.chat("llama3", [{"role": "user", "content": "trigger fallback"}])
        assert router.current_level == "L2"

        # Ollama 恢复
        ollama._healthy = True
        # 路由应保持在 L2，不会自动切回
        assert router.current_level == "L2"
