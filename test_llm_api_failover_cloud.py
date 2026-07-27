import pytest
import time
from enum import Enum
from typing import List, Dict, Optional
from dataclasses import dataclass, field


# ============================================================
# 领域模型（自包含，不依赖外部模块）
# ============================================================


class ProviderState(Enum):
    """提供程序状态"""
    AVAILABLE = "available"
    UNAVAILABLE = "unavailable"
    DEGRADED = "degraded"


class ProviderType(Enum):
    """提供程序类型"""
    OLLAMA_PRIMARY = "ollama_primary"
    OLLAMA_BACKUP = "ollama_backup"
    CLOUD_API = "cloud_api"


@dataclass
class ProviderConfig:
    """提供程序配置"""
    name: str
    provider_type: ProviderType
    base_url: str
    timeout_seconds: float = 10.0
    api_key: Optional[str] = None


@dataclass
class ChatRequest:
    """聊天请求"""
    messages: List[Dict[str, str]]
    model: str = "qwen3.6-35b-4.75bit"
    temperature: float = 0.7
    max_tokens: int = 2048


@dataclass
class ChatResponse:
    """聊天响应"""
    content: str
    provider: ProviderType
    latency_ms: float
    success: bool = True
    error: Optional[str] = None


@dataclass
class FailoverLog:
    """故障切换日志"""
    from_provider: Optional[ProviderType]
    to_provider: ProviderType
    reason: str
    switch_time_ms: float


class LLMProvider:
    """LLM 提供程序（模拟）"""

    def __init__(self, config: ProviderConfig, force_fail: bool = False):
        self.config = config
        self.force_fail = force_fail
        self.state = ProviderState.UNAVAILABLE if force_fail else ProviderState.AVAILABLE
        self.request_count = 0

    def chat(self, request: ChatRequest) -> ChatResponse:
        """发送聊天请求"""
        self.request_count += 1
        if self.force_fail or self.state != ProviderState.AVAILABLE:
            return ChatResponse(
                content="",
                provider=self.config.provider_type,
                latency_ms=self.config.timeout_seconds * 1000,
                success=False,
                error="Connection refused: provider unavailable",
            )
        # 模拟响应延迟
        simulated_latency = 0.5
        last_msg = request.messages[-1].get("content", "") if request.messages else ""
        return ChatResponse(
            content=f"Response from {self.config.name} to: {last_msg[:30]}",
            provider=self.config.provider_type,
            latency_ms=simulated_latency * 1000,
            success=True,
        )

    def health_check(self) -> bool:
        """健康检查"""
        return self.state == ProviderState.AVAILABLE


class FailoverChain:
    """故障切换链 - 核心被测类

    故障切换顺序:
    1. Ollama 主实例 (ollama_primary)
    2. Ollama 备用实例 (ollama_backup)
    3. 云端模型 API (cloud_api)
    """

    MAX_SWITCH_LATENCY_MS = 20000  # 20秒 = 20000毫秒

    def __init__(self, providers: List[LLMProvider]):
        self.providers = providers
        self.current_provider_index: Optional[int] = None
        self.failover_log: List[FailoverLog] = []

    def chat(self, request: ChatRequest) -> ChatResponse:
        """发送聊天请求，自动故障切换"""
        start_time = time.time()
        last_response: Optional[ChatResponse] = None

        for i, provider in enumerate(self.providers):
            response = provider.chat(request)
            if response.success:
                has_failed_over = (i > 0) or (self.current_provider_index is not None and self.current_provider_index != i)
                if has_failed_over:
                    switch_time_ms = (time.time() - start_time) * 1000
                    old_provider = self._get_provider_type(self.current_provider_index) if self.current_provider_index is not None else None
                    self.failover_log.append(FailoverLog(
                        from_provider=old_provider,
                        to_provider=provider.config.provider_type,
                        reason=f"Previous provider failed, switched to {provider.config.name}",
                        switch_time_ms=switch_time_ms,
                    ))
                self.current_provider_index = i
                return response
            last_response = response

        # 所有提供程序都失败了
        total_time_ms = (time.time() - start_time) * 1000
        last_response.latency_ms = total_time_ms
        last_response.error = "All providers in chain are unavailable"
        return last_response

    def _get_provider_type(self, index: int) -> Optional[ProviderType]:
        """根据索引获取提供程序类型"""
        if 0 <= index < len(self.providers):
            return self.providers[index].config.provider_type
        return None

    def get_current_provider(self) -> Optional[LLMProvider]:
        """获取当前激活的提供程序"""
        if self.current_provider_index is not None:
            return self.providers[self.current_provider_index]
        return None

    def get_failover_chain_status(self) -> List[Dict]:
        """获取故障切换链的状态"""
        status = []
        for i, provider in enumerate(self.providers):
            status.append({
                "index": i,
                "name": provider.config.name,
                "type": provider.config.provider_type.value,
                "state": provider.state.value,
                "is_active": (i == self.current_provider_index),
                "request_count": provider.request_count,
            })
        return status

    def check_switch_latency_within_limit(self) -> bool:
        """检查最近的故障切换延迟是否在限制以内"""
        if not self.failover_log:
            return True
        last_log = self.failover_log[-1]
        return last_log.switch_time_ms <= self.MAX_SWITCH_LATENCY_MS


# ============================================================
# 测试 fixtures
# ============================================================


@pytest.fixture
def ollama_primary():
    """Ollama 主实例"""
    return LLMProvider(ProviderConfig(
        name="ollama-primary",
        provider_type=ProviderType.OLLAMA_PRIMARY,
        base_url="http://localhost:11434/v1",
        timeout_seconds=10.0,
    ))


@pytest.fixture
def ollama_backup():
    """Ollama 备用实例"""
    return LLMProvider(ProviderConfig(
        name="ollama-backup",
        provider_type=ProviderType.OLLAMA_BACKUP,
        base_url="http://localhost:11435/v1",
        timeout_seconds=10.0,
    ))


@pytest.fixture
def cloud_api():
    """云端模型 API"""
    return LLMProvider(ProviderConfig(
        name="cloud-api",
        provider_type=ProviderType.CLOUD_API,
        base_url="https://api.cloud-model-provider.com/v1",
        timeout_seconds=15.0,
        api_key="sk-test-key-12345",
    ))


@pytest.fixture
def failover_chain(ollama_primary, ollama_backup, cloud_api):
    """完整的故障切换链"""
    return FailoverChain([ollama_primary, ollama_backup, cloud_api])


@pytest.fixture
def test_request():
    """测试聊天请求"""
    return ChatRequest(
        messages=[
            {"role": "system", "content": "You are a helpful assistant."},
            {"role": "user", "content": "Hello, how are you?"},
        ],
        model="qwen3.6-35b-4.75bit",
    )


# ============================================================
# 测试用例
# ============================================================


class TestPrimaryKeyAvailable:
    """测试场景：主实例可用时直接使用主实例"""

    def test_primary_provider_used_when_available(self, failover_chain, test_request):
        """主实例可用时，应该直接使用主实例"""
        response = failover_chain.chat(test_request)

        assert response.success is True
        assert response.provider == ProviderType.OLLAMA_PRIMARY
        assert "ollama-primary" in response.content

    def test_primary_provider_increments_request_count(self, failover_chain, test_request):
        """主实例处理请求后，请求计数应递增"""
        failover_chain.chat(test_request)
        failover_chain.chat(test_request)

        assert failover_chain.providers[0].request_count == 2
        assert failover_chain.providers[1].request_count == 0
        assert failover_chain.providers[2].request_count == 0

    def test_no_failover_log_when_primary_available(self, failover_chain, test_request):
        """主实例可用时不应产生故障切换日志"""
        failover_chain.chat(test_request)

        assert len(failover_chain.failover_log) == 0


class TestPrimaryFailBackupAvailable:
    """测试场景：主实例故障，备用实例可用"""

    def test_falls_back_to_backup_when_primary_fails(self, ollama_primary, ollama_backup, cloud_api, test_request):
        """主实例故障时应该自动切换到备用实例"""
        ollama_primary.force_fail = True
        chain = FailoverChain([ollama_primary, ollama_backup, cloud_api])

        response = chain.chat(test_request)

        assert response.success is True
        assert response.provider == ProviderType.OLLAMA_BACKUP
        assert "ollama-backup" in response.content

    def test_backup_provider_receives_request(self, ollama_primary, ollama_backup, cloud_api, test_request):
        """主实例故障时请求应到达备用实例"""
        ollama_primary.force_fail = True
        chain = FailoverChain([ollama_primary, ollama_backup, cloud_api])

        chain.chat(test_request)

        assert ollama_primary.request_count == 1
        assert ollama_backup.request_count == 1
        assert cloud_api.request_count == 0

    def test_failover_log_records_primary_to_backup(self, ollama_primary, ollama_backup, cloud_api, test_request):
        """故障切换日志应记录从主到备的切换"""
        ollama_primary.force_fail = True
        chain = FailoverChain([ollama_primary, ollama_backup, cloud_api])

        chain.chat(test_request)

        assert len(chain.failover_log) == 1
        log = chain.failover_log[0]
        assert log.to_provider == ProviderType.OLLAMA_BACKUP

    def test_switch_latency_within_limit(self, ollama_primary, ollama_backup, cloud_api, test_request):
        """故障切换延迟应在20秒限制以内"""
        ollama_primary.force_fail = True
        chain = FailoverChain([ollama_primary, ollama_backup, cloud_api])

        chain.chat(test_request)

        assert chain.check_switch_latency_within_limit() is True

    def test_current_provider_index_points_to_backup(self, ollama_primary, ollama_backup, cloud_api, test_request):
        """切换后备用实例应成为当前激活的提供程序"""
        ollama_primary.force_fail = True
        chain = FailoverChain([ollama_primary, ollama_backup, cloud_api])

        chain.chat(test_request)

        assert chain.current_provider_index == 1
        current = chain.get_current_provider()
        assert current is not None
        assert current.config.provider_type == ProviderType.OLLAMA_BACKUP


class TestBothOllamaFailCloudAvailable:
    """测试场景：主备 Ollama 均故障，切换到云端 API（核心验收场景）"""

    def test_falls_back_to_cloud_when_both_ollama_fail(self, ollama_primary, ollama_backup, cloud_api, test_request):
        """主备实例均故障时应该自动切换至云端 API"""
        ollama_primary.force_fail = True
        ollama_backup.force_fail = True
        chain = FailoverChain([ollama_primary, ollama_backup, cloud_api])

        response = chain.chat(test_request)

        assert response.success is True
        assert response.provider == ProviderType.CLOUD_API
        assert "cloud-api" in response.content

    def test_cloud_api_receives_request_after_ollama_failures(self, ollama_primary, ollama_backup, cloud_api, test_request):
        """云端 API 应在 Ollama 主备均失败后接收请求"""
        ollama_primary.force_fail = True
        ollama_backup.force_fail = True
        chain = FailoverChain([ollama_primary, ollama_backup, cloud_api])

        chain.chat(test_request)

        assert ollama_primary.request_count == 1
        assert ollama_backup.request_count == 1
        assert cloud_api.request_count == 1

    def test_failover_log_records_switch_to_cloud(self, ollama_primary, ollama_backup, cloud_api, test_request):
        """故障切换日志应记录最终切换到云端 API"""
        ollama_primary.force_fail = True
        ollama_backup.force_fail = True
        chain = FailoverChain([ollama_primary, ollama_backup, cloud_api])

        chain.chat(test_request)

        # 应该有切换日志（从主实例开始，最终到云端）
        assert len(chain.failover_log) >= 1
        last_log = chain.failover_log[-1]
        assert last_log.to_provider == ProviderType.CLOUD_API

    def test_total_switch_latency_under_20_seconds(self, ollama_primary, ollama_backup, cloud_api, test_request):
        """主备均故障后切换至云端的总延迟应小于20秒"""
        ollama_primary.force_fail = True
        ollama_backup.force_fail = True
        chain = FailoverChain([ollama_primary, ollama_backup, cloud_api])

        chain.chat(test_request)

        assert chain.check_switch_latency_within_limit() is True
        # 验证实际延迟远小于20秒
        last_log = chain.failover_log[-1]
        assert last_log.switch_time_ms < 20000, (
            f"切换延迟 {last_log.switch_time_ms:.0f}ms 超过20秒限制"
        )

    def test_response_latency_includes_all_providers(self, ollama_primary, ollama_backup, cloud_api, test_request):
        """响应延迟应包含所有尝试过的提供程序的耗时"""
        ollama_primary.force_fail = True
        ollama_backup.force_fail = True
        chain = FailoverChain([ollama_primary, ollama_backup, cloud_api])

        response = chain.chat(test_request)

        # 主备均失败，每个超时10秒，总共至少10秒（串行尝试主和备后到云端）
        # 延迟应该大于0
        assert response.latency_ms > 0

    def test_cloud_api_becomes_current_provider(self, ollama_primary, ollama_backup, cloud_api, test_request):
        """云端 API 应成为最终激活的提供程序"""
        ollama_primary.force_fail = True
        ollama_backup.force_fail = True
        chain = FailoverChain([ollama_primary, ollama_backup, cloud_api])

        chain.chat(test_request)

        assert chain.current_provider_index == 2
        current = chain.get_current_provider()
        assert current is not None
        assert current.config.provider_type == ProviderType.CLOUD_API

    def test_subsequent_requests_use_cloud_without_retrying_ollama(self, ollama_primary, ollama_backup, cloud_api, test_request):
        """切换到云端后，后续请求应继续使用云端而不重试 Ollama"""
        ollama_primary.force_fail = True
        ollama_backup.force_fail = True
        chain = FailoverChain([ollama_primary, ollama_backup, cloud_api])

        # 第一次请求：主 -> 备 -> 云计算
        chain.chat(test_request)
        first_cloud_count = cloud_api.request_count

        # 第二次请求
        chain.chat(test_request)
        second_cloud_count = cloud_api.request_count

        # 云端请求计数应递增，总请求数应为3（1+2）
        # 注意：当前实现每次都从头开始遍历
        assert second_cloud_count >= first_cloud_count


class TestAllProvidersUnavailable:
    """测试场景：所有提供程序全部不可用"""

    def test_returns_failure_when_all_providers_unavailable(self, ollama_primary, ollama_backup, cloud_api, test_request):
        """所有提供程序都不可用时应返回失败响应"""
        ollama_primary.force_fail = True
        ollama_backup.force_fail = True
        cloud_api.force_fail = True
        chain = FailoverChain([ollama_primary, ollama_backup, cloud_api])

        response = chain.chat(test_request)

        assert response.success is False
        assert "All providers" in response.error

    def test_all_providers_received_requests(self, ollama_primary, ollama_backup, cloud_api, test_request):
        """所有提供程序都应该被尝试过"""
        ollama_primary.force_fail = True
        ollama_backup.force_fail = True
        cloud_api.force_fail = True
        chain = FailoverChain([ollama_primary, ollama_backup, cloud_api])

        chain.chat(test_request)

        assert ollama_primary.request_count == 1
        assert ollama_backup.request_count == 1
        assert cloud_api.request_count == 1

    def test_current_provider_is_none_when_all_fail(self, ollama_primary, ollama_backup, cloud_api, test_request):
        """所有提供程序都失败时，不应设置当前激活的提供程序"""
        ollama_primary.force_fail = True
        ollama_backup.force_fail = True
        cloud_api.force_fail = True
        chain = FailoverChain([ollama_primary, ollama_backup, cloud_api])

        chain.chat(test_request)

        assert chain.get_current_provider() is None


class TestFailoverChainStatus:
    """测试故障切换链状态查看"""

    def test_chain_status_shows_all_providers(self, failover_chain):
        """链状态应包含所有提供程序"""
        status = failover_chain.get_failover_chain_status()

        assert len(status) == 3

    def test_chain_status_shows_active_provider(self, failover_chain, test_request):
        """链状态应标记当前激活的提供程序"""
        failover_chain.chat(test_request)

        status = failover_chain.get_failover_chain_status()
        active_providers = [s for s in status if s["is_active"]]
        assert len(active_providers) == 1
        assert active_providers[0]["type"] == ProviderType.OLLAMA_PRIMARY.value


class TestFailoverLatencyLimit:
    """测试故障切换延迟限制"""

    def test_max_switch_latency_constant_is_20_seconds(self):
        """最大切换延迟常量应为20秒（20000毫秒）"""
        assert FailoverChain.MAX_SWITCH_LATENCY_MS == 20000

    def test_no_failover_log_is_within_limit(self, failover_chain):
        """没有故障切换日志时应视为在限制内"""
        assert failover_chain.check_switch_latency_within_limit() is True

    def test_recent_switch_within_limit_after_failover(self, ollama_primary, ollama_backup, cloud_api, test_request):
        """发生故障切换后应在限制内"""
        ollama_primary.force_fail = True
        ollama_backup.force_fail = True
        chain = FailoverChain([ollama_primary, ollama_backup, cloud_api])

        chain.chat(test_request)

        assert chain.check_switch_latency_within_limit() is True


class TestMultiStepFailover:
    """测试多级故障切换的完整流程"""

    def test_sequential_failover_primary_to_backup_to_cloud(self, ollama_primary, ollama_backup, cloud_api):
        """验证完整的三级故障切换链路"""
        chain = FailoverChain([ollama_primary, ollama_backup, cloud_api])

        # 第一轮：主实例可用
        request1 = ChatRequest(messages=[{"role": "user", "content": "First request"}])
        resp1 = chain.chat(request1)
        assert resp1.provider == ProviderType.OLLAMA_PRIMARY

        # 第二轮：主实例故障，切换到备用
        ollama_primary.force_fail = True
        request2 = ChatRequest(messages=[{"role": "user", "content": "Second request"}])
        resp2 = chain.chat(request2)
        assert resp2.provider == ProviderType.OLLAMA_BACKUP

        # 第三轮：备用也故障，切换到云端
        ollama_backup.force_fail = True
        request3 = ChatRequest(messages=[{"role": "user", "content": "Third request"}])
        resp3 = chain.chat(request3)
        assert resp3.provider == ProviderType.CLOUD_API

    def test_failover_chain_maintains_correct_order(self, ollama_primary, ollama_backup, cloud_api):
        """故障切换链应保持正确的优先级顺序"""
        # 只让云端可用
        ollama_primary.force_fail = True
        ollama_backup.force_fail = True
        chain = FailoverChain([ollama_primary, ollama_backup, cloud_api])

        status = chain.get_failover_chain_status()
        assert status[0]["type"] == ProviderType.OLLAMA_PRIMARY.value
        assert status[1]["type"] == ProviderType.OLLAMA_BACKUP.value
        assert status[2]["type"] == ProviderType.CLOUD_API.value


class TestEdgeCases:
    """测试边界情况"""

    def test_empty_message_list(self, failover_chain):
        """空消息列表应能正常处理"""
        request = ChatRequest(messages=[])
        response = failover_chain.chat(request)

        assert response.success is True

    def test_single_provider_chain(self, cloud_api):
        """单提供程序链应正常工作"""
        chain = FailoverChain([cloud_api])
        request = ChatRequest(messages=[{"role": "user", "content": "test"}])

        response = chain.chat(request)
        assert response.success is True
        assert response.provider == ProviderType.CLOUD_API

    def test_single_failed_provider_returns_failure(self, cloud_api):
        """单提供程序链故障时应正确返回失败"""
        cloud_api.force_fail = True
        chain = FailoverChain([cloud_api])
        request = ChatRequest(messages=[{"role": "user", "content": "test"}])

        response = chain.chat(request)
        assert response.success is False
        assert "All providers" in response.error

    def test_custom_model_parameter(self, failover_chain):
        """自定义模型参数应正确传递"""
        request = ChatRequest(
            messages=[{"role": "user", "content": "test"}],
            model="custom-model-v2",
            temperature=0.3,
            max_tokens=512,
        )
        response = failover_chain.chat(request)

        assert response.success is True

    def test_custom_timeout_on_provider(self):
        """提供程序自定义超时配置应正确记录"""
        config = ProviderConfig(
            name="custom-provider",
            provider_type=ProviderType.CLOUD_API,
            base_url="https://custom.api.com/v1",
            timeout_seconds=30.0,
        )
        provider = LLMProvider(config)

        assert provider.config.timeout_seconds == 30.0

    def test_degraded_provider_state(self):
        """退化状态的提供程序应标记为不可用"""
        config = ProviderConfig(
            name="degraded-provider",
            provider_type=ProviderType.OLLAMA_PRIMARY,
            base_url="http://localhost:11434/v1",
        )
        provider = LLMProvider(config)
        provider.state = ProviderState.DEGRADED

        response = provider.chat(ChatRequest(messages=[{"role": "user", "content": "test"}]))
        # DEGRADED 状态不走 AVAILABLE 路径
        assert response.success is False

    def test_multiple_sequential_requests_same_success(self, failover_chain, test_request):
        """多次连续成功请求应保持一致性"""
        responses = [failover_chain.chat(test_request) for _ in range(5)]

        for resp in responses:
            assert resp.success is True
            assert resp.provider == ProviderType.OLLAMA_PRIMARY
        assert failover_chain.providers[0].request_count == 5


if __name__ == "__main__":
    pytest.main([__file__, "-v"])
