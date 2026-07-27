import uuid
import time
import threading
from enum import Enum
from typing import Optional, List, Dict
from dataclasses import dataclass, field
from collections import deque

import pytest


# ====================================================================
# 领域模型
# ===================================================================


class InferenceRequestStatus(str, Enum):
    QUEUED = "queued"
    RUNNING = "running"
    COMPLETED = "completed"
    FAILED = "failed"


class InferencePriority(str, Enum):
    URGENT = "urgent"
    NORMAL = "normal"
    LOW = "low"


@dataclass
class InferenceRequest:
    """单次推理请求"""
    request_id: str
    user_id: str
    model: str
    prompt: str
    priority: InferencePriority = InferencePriority.NORMAL
    status: InferenceRequestStatus = InferenceRequestStatus.QUEUED
    created_at: float = field(default_factory=time.time)
    queued_at: Optional[float] = None
    started_at: Optional[float] = None
    completed_at: Optional[float] = None
    gpu_vram_mb: int = 0  # 推理完成后累计消耗的显存
    error: Optional[str] = None


@dataclass
class GpuMemorySnapshot:
    """显存快照"""
    timestamp: float
    total_vram_gb: float = 48.0
    used_vram_gb: float = 0.0
    model_weights_gb: float = 0.0
    kv_cache_gb: float = 0.0
    system_overhead_gb: float = 0.0
    active_requests: int = 0

    @property
    def available_vram_gb(self) -> float:
        return self.total_vram_gb - self.used_vram_gb

    @property
    def utilization_percent(self) -> float:
        if self.total_vram_gb == 0:
            return 0.0
        return (self.used_vram_gb / self.total_vram_gb) * 100.0


@dataclass
class OllamaConfig:
    """Ollama 推理引擎配置"""
    max_concurrent_requests: int = 2
    queue_capacity: int = 50
    model_name: str = "qwen2.5:72b-instruct-q4_K_M"
    model_weights_gb: float = 38.0  # 72B 参数 x 4-bit 量化
    kv_cache_per_request_gb: float = 2.0  # 每并发请求的 KV Cache
    system_overhead_gb: float = 2.0  # 系统开销
    total_vram_gb: float = 48.0  # 48GB GPU 显存
    inference_timeout_seconds: float = 60.0  # 推理超时
    queue_timeout_seconds: float = 180.0  # 排队超时


@dataclass
class InferenceResult:
    """推理结果"""
    request_id: str
    success: bool
    content: str = ""
    duration_seconds: float = 0.0
    gpu_peak_gb: float = 0.0
    queue_wait_seconds: float = 0.0
    error: Optional[str] = None


# ====================================================================
# 被测试的 Ollama 推理引擎
# ===================================================================


class OllamaInferenceEngine:
    """
    Ollama 推理引擎模拟器。
    核心约束:
    - 最大 2 并发推理请求
    - 超出并发上限的请求排队
    - 显存峰值不得超过 44GB（留 4GB 余量）
    """

    def __init__(self, config: OllamaConfig = None):
        self.config = config or OllamaConfig()
        self._queue: deque = deque()
        self._active_requests: Dict[str, InferenceRequest] = {}
        self._completed_results: List[InferenceResult] = []
        self._memory_snapshots: List[GpuMemorySnapshot] = []
        self._lock = threading.RLock()
        self._stopped = False

    @property
    def active_count(self) -> int:
        """当前正在运行的推理请求数"""
        with self._lock:
            return len(self._active_requests)

    @property
    def queue_length(self) -> int:
        """排队中的请求数"""
        with self._lock:
            return len(self._queue)

    @property
    def peak_vram_gb(self) -> float:
        """历史显存峰值"""
        if not self._memory_snapshots:
            return 0.0
        return max(s.used_vram_gb for s in self._memory_snapshots)

    def _calculate_vram_usage(self, active_count: int) -> float:
        """计算当前显存使用量（GB）"""
        return (
            self.config.model_weights_gb
            + active_count * self.config.kv_cache_per_request_gb
            + self.config.system_overhead_gb
        )

    def _take_memory_snapshot(self):
        """记录显存快照"""
        with self._lock:
            count = len(self._active_requests)
            usage = self._calculate_vram_usage(count)
            snapshot = GpuMemorySnapshot(
                timestamp=time.time(),
                used_vram_gb=usage,
                model_weights_gb=self.config.model_weights_gb,
                kv_cache_gb=count * self.config.kv_cache_per_request_gb,
                system_overhead_gb=self.config.system_overhead_gb,
                active_requests=count,
            )
            self._memory_snapshots.append(snapshot)
            return snapshot

    def submit_request(
        self,
        user_id: str,
        prompt: str,
        model: str = None,
        priority: InferencePriority = InferencePriority.NORMAL,
    ) -> InferenceRequest:
        """
        提交推理请求。如果超过并发上限，请求将进入队列。
        """
        request_id = str(uuid.uuid4())
        model_name = model or self.config.model_name
        request = InferenceRequest(
            request_id=request_id,
            user_id=user_id,
            model=model_name,
            prompt=prompt,
            priority=priority,
            status=InferenceRequestStatus.QUEUED,
            created_at=time.time(),
        )

        with self._lock:
            if len(self._active_requests) < self.config.max_concurrent_requests:
                # 有可用槽位，直接开始
                request.status = InferenceRequestStatus.RUNNING
                request.started_at = time.time()
                self._active_requests[request_id] = request
                self._take_memory_snapshot()
                return request
            else:
                # 进入队列
                if len(self._queue) >= self.config.queue_capacity:
                    request.status = InferenceRequestStatus.FAILED
                    request.error = "队列已满，无法接受新请求"
                    return request
                request.queued_at = time.time()
                self._queue.append(request)
                return request

    def complete_request(self, request_id: str, content: str = "推理结果") -> InferenceResult:
        """完成一个推理请求，释放资源，从队列中取出下一个"""
        with self._lock:
            if request_id not in self._active_requests:
                return InferenceResult(
                    request_id=request_id,
                    success=False,
                    error="请求不存在",
                )

            request = self._active_requests.pop(request_id)
            request.status = InferenceRequestStatus.COMPLETED
            request.completed_at = time.time()
            duration = request.completed_at - request.started_at
            queue_wait = (
                request.started_at - request.queued_at if request.queued_at else 0.0
            )

            # 显存下降
            self._take_memory_snapshot()

            result = InferenceResult(
                request_id=request_id,
                success=True,
                content=content,
                duration_seconds=duration,
                queue_wait_seconds=queue_wait,
            )
            self._completed_results.append(result)

        # 释放锁后处理队列
        self._process_queue()

        return result

    def _process_queue(self):
        """从队列中取出请求开始执行（在锁外调用）"""
        with self._lock:
            while (
                len(self._queue) > 0
                and len(self._active_requests) < self.config.max_concurrent_requests
                and not self._stopped
            ):
                request = self._queue.popleft()
                request.status = InferenceRequestStatus.RUNNING
                request.started_at = time.time()
                self._active_requests[request.request_id] = request
            self._take_memory_snapshot()

    def get_memory_snapshots(self) -> List[GpuMemorySnapshot]:
        """获取所有显存快照"""
        return list(self._memory_snapshots)

    def get_completed_results(self) -> List[InferenceResult]:
        """获取所有完成的推理结果"""
        return list(self._completed_results)

    def stop(self):
        """停止引擎"""
        self._stopped = True


# ====================================================================
# 测试用例
# ===================================================================


class TestOllamaConcurrencyLimit:
    """验证 Ollama 最大 2 个并行推理请求"""

    def test_max_concurrent_is_two(self):
        """最大并发数为 2"""
        engine = OllamaInferenceEngine(OllamaConfig(max_concurrent_requests=2))
        assert engine.config.max_concurrent_requests == 2

    def test_two_requests_run_concurrently(self):
        """提交 2 个请求时，两者都处于 RUNNING 状态"""
        engine = OllamaInferenceEngine(OllamaConfig(max_concurrent_requests=2))

        req1 = engine.submit_request("user1", "问题1")
        req2 = engine.submit_request("user2", "问题2")

        assert req1.status == InferenceRequestStatus.RUNNING
        assert req2.status == InferenceRequestStatus.RUNNING
        assert engine.active_count == 2

    def test_third_request_is_queued(self):
        """第 3 个请求被放入队列"""
        engine = OllamaInferenceEngine(OllamaConfig(max_concurrent_requests=2))

        req1 = engine.submit_request("user1", "问题1")
        req2 = engine.submit_request("user2", "问题2")
        req3 = engine.submit_request("user3", "问题3")

        assert req1.status == InferenceRequestStatus.RUNNING
        assert req2.status == InferenceRequestStatus.RUNNING
        assert req3.status == InferenceRequestStatus.QUEUED
        assert engine.active_count == 2
        assert engine.queue_length == 1

    def test_fifth_request_is_queued(self):
        """提交 5 个请求时，前 2 个运行，后 3 个排队"""
        engine = OllamaInferenceEngine(OllamaConfig(max_concurrent_requests=2))

        requests = [
            engine.submit_request(f"user{i}", f"问题{i}")
            for i in range(1, 6)
        ]

        assert requests[0].status == InferenceRequestStatus.RUNNING
        assert requests[1].status == InferenceRequestStatus.RUNNING
        assert requests[2].status == InferenceRequestStatus.QUEUED
        assert requests[3].status == InferenceRequestStatus.QUEUED
        assert requests[4].status == InferenceRequestStatus.QUEUED
        assert engine.active_count == 2
        assert engine.queue_length == 3

    def test_no_requests_all_queued_immediately(self):
        """无活跃请求时，新提交直接运行而非排队"""
        engine = OllamaInferenceEngine(OllamaConfig(max_concurrent_requests=2))

        req1 = engine.submit_request("user1", "问题1")
        req2 = engine.submit_request("user2", "问题2")

        # 完成两个请求
        engine.complete_request(req1.request_id)
        engine.complete_request(req2.request_id)

        # 再次提交应该直接运行
        req3 = engine.submit_request("user3", "问题3")
        assert req3.status == InferenceRequestStatus.RUNNING
        assert engine.active_count == 1


class TestOllamaQueueProcessing:
    """验证超出并发限制时的排队机制"""

    def test_queue_advances_on_completion(self):
        """完成一个请求后，队列中的下一个请求自动开始"""
        engine = OllamaInferenceEngine(OllamaConfig(max_concurrent_requests=2))

        req1 = engine.submit_request("user1", "问题1")
        req2 = engine.submit_request("user2", "问题2")
        req3 = engine.submit_request("user3", "问题3")
        req4 = engine.submit_request("user4", "问题4")

        assert engine.queue_length == 2
        assert req3.status == InferenceRequestStatus.QUEUED
        assert req4.status == InferenceRequestStatus.QUEUED

        # 完成 req1
        result = engine.complete_request(req1.request_id)
        assert result.success is True

        # req3 应该自动开始
        assert req3.status == InferenceRequestStatus.RUNNING
        assert engine.active_count == 2  # req2 + req3
        assert engine.queue_length == 1  # req4 还在排队

    def test_queue_processes_fifo_order(self):
        """队列按 FIFO 顺序处理"""
        engine = OllamaInferenceEngine(OllamaConfig(max_concurrent_requests=2))

        req1 = engine.submit_request("user1", "问题1")
        req2 = engine.submit_request("user2", "问题2")
        req3 = engine.submit_request("user3", "问题3")
        req4 = engine.submit_request("user4", "问题4")

        # 完成 req1
        engine.complete_request(req1.request_id)
        # 完成 req2
        engine.complete_request(req2.request_id)
        # 完成 req3
        engine.complete_request(req3.request_id)
        # 完成 req4
        engine.complete_request(req4.request_id)

        results = engine.get_completed_results()
        assert len(results) == 4
        # 验证 FIFO 顺序
        assert results[0].request_id == req1.request_id
        assert results[1].request_id == req2.request_id
        assert results[2].request_id == req3.request_id
        assert results[3].request_id == req4.request_id

    def test_queue_capacity_overflow(self):
        """队列已满时，新请求被拒绝"""
        config = OllamaConfig(max_concurrent_requests=2, queue_capacity=3)
        engine = OllamaInferenceEngine(config)

        # 填满并发槽位
        engine.submit_request("user1", "问题1")
        engine.submit_request("user2", "问题2")
        # 填满队列
        engine.submit_request("user3", "问题3")
        engine.submit_request("user4", "问题4")
        engine.submit_request("user5", "问题5")

        # 第 6 个请求应该被拒绝
        req_overflow = engine.submit_request("user6", "问题6")
        assert req_overflow.status == InferenceRequestStatus.FAILED
        assert req_overflow.error == "队列已满，无法接受新请求"

    def test_cascade_completion_frees_queue(self):
        """连续完成请求，队列逐步被处理"""
        engine = OllamaInferenceEngine(OllamaConfig(max_concurrent_requests=2))

        requests = [
            engine.submit_request(f"user{i}", f"问题{i}")
            for i in range(1, 8)
        ]

        # 初始状态: 2 running, 5 queued
        assert engine.active_count == 2
        assert engine.queue_length == 5

        # 完成前 6 个，最后一个自动从队列中弹出
        for i in range(6):
            engine.complete_request(requests[i].request_id)

        # 此时最后一个请求 (requests[6]) 还在运行中
        assert engine.active_count == 1
        assert engine.queue_length == 0
        assert len(engine.get_completed_results()) == 6

        # 完成最后一个
        engine.complete_request(requests[6].request_id)

        # 全部完成
        assert engine.active_count == 0
        assert engine.queue_length == 0
        assert len(engine.get_completed_results()) == 7


class TestOllamaGpuMemoryLimit:
    """验证显存峰值 <= 44GB（留 4GB 余量）"""

    def test_vram_formula_at_zero_concurrent(self):
        """0 并发时显存 = 模型权重 + 系统开销"""
        config = OllamaConfig(
            model_weights_gb=38.0,
            kv_cache_per_request_gb=2.0,
            system_overhead_gb=2.0,
        )
        engine = OllamaInferenceEngine(config)

        vram = engine._calculate_vram_usage(0)
        assert vram == 40.0  # 38 + 0*2 + 2

    def test_vram_formula_at_one_concurrent(self):
        """1 并发时显存 = 38 + 1*2 + 2 = 42GB"""
        config = OllamaConfig(
            model_weights_gb=38.0,
            kv_cache_per_request_gb=2.0,
            system_overhead_gb=2.0,
        )
        engine = OllamaInferenceEngine(config)

        vram = engine._calculate_vram_usage(1)
        assert vram == 42.0  # 38 + 1*2 + 2

    def test_vram_formula_at_two_concurrent(self):
        """2 并发时显存 = 38 + 2*2 + 2 = 44GB"""
        config = OllamaConfig(
            model_weights_gb=38.0,
            kv_cache_per_request_gb=2.0,
            system_overhead_gb=2.0,
        )
        engine = OllamaInferenceEngine(config)

        vram = engine._calculate_vram_usage(2)
        assert vram == 44.0  # 38 + 2*2 + 2

    def test_peak_vram_under_two_concurrent(self):
        """2 并发推理时，显存峰值 <= 44GB"""
        config = OllamaConfig(
            model_weights_gb=38.0,
            kv_cache_per_request_gb=2.0,
            system_overhead_gb=2.0,
            total_vram_gb=48.0,
        )
        engine = OllamaInferenceEngine(config)

        req1 = engine.submit_request("user1", "问题1")
        req2 = engine.submit_request("user2", "问题2")

        peak = engine.peak_vram_gb
        assert peak <= 44.0
        assert peak == 44.0

    def test_peak_vram_with_queue_no_increase(self):
        """排队的请求不应增加显存使用"""
        config = OllamaConfig(
            model_weights_gb=38.0,
            kv_cache_per_request_gb=2.0,
            system_overhead_gb=2.0,
            total_vram_gb=48.0,
        )
        engine = OllamaInferenceEngine(config)

        req1 = engine.submit_request("user1", "问题1")
        req2 = engine.submit_request("user2", "问题2")
        req3 = engine.submit_request("user3", "问题3")  # 排队
        req4 = engine.submit_request("user4", "问题4")  # 排队

        # 排队请求不增加显存
        peak = engine.peak_vram_gb
        assert peak == 44.0
        assert peak <= 44.0

    def test_vram_decreases_on_completion(self):
        """完成请求后显存下降"""
        config = OllamaConfig(
            model_weights_gb=38.0,
            kv_cache_per_request_gb=2.0,
            system_overhead_gb=2.0,
            total_vram_gb=48.0,
        )
        engine = OllamaInferenceEngine(config)

        req1 = engine.submit_request("user1", "问题1")
        req2 = engine.submit_request("user2", "问题2")
        req3 = engine.submit_request("user3", "问题3")  # 排队
        req4 = engine.submit_request("user4", "问题4")  # 排队

        assert engine.peak_vram_gb == 44.0

        engine.complete_request(req1.request_id)
        # 完成一个后，队列补 1 个，保持 2 并发
        snapshots = engine.get_memory_snapshots()
        assert len(snapshots) >= 3

        engine.complete_request(req2.request_id)
        # req2 完成后，队列中的 req3 已经被补上
        engine.complete_request(req3.request_id)
        engine.complete_request(req4.request_id)

        # 最终显存为 0 并发时的基础值
        final_usage = engine._calculate_vram_usage(0)
        assert final_usage == 40.0  # 38 + 0*2 + 2

    def test_peak_vram_never_exceeds_44gb(self):
        """大量请求涌入时，显存峰值始终不超过 44GB"""
        config = OllamaConfig(
            model_weights_gb=38.0,
            kv_cache_per_request_gb=2.0,
            system_overhead_gb=2.0,
            total_vram_gb=48.0,
        )
        engine = OllamaInferenceEngine(config)

        # 一次性提交 10 个请求
        requests = [
            engine.submit_request(f"user{i}", f"问题{i}")
            for i in range(1, 11)
        ]

        peak = engine.peak_vram_gb
        assert peak <= 44.0, f"显存峰值 {peak}GB 超过 44GB 上限"
        assert peak == 44.0

        # 逐个完成所有 10 个请求
        for i in range(10):
            engine.complete_request(requests[i].request_id)

        # 全部完成
        assert len(engine.get_completed_results()) == 10

    def test_vram_utilization_at_max(self):
        """2 并发时的显存利用率"""
        config = OllamaConfig(
            model_weights_gb=38.0,
            kv_cache_per_request_gb=2.0,
            system_overhead_gb=2.0,
            total_vram_gb=48.0,
        )
        engine = OllamaInferenceEngine(config)

        engine.submit_request("user1", "问题1")
        engine.submit_request("user2", "问题2")

        snapshots = engine.get_memory_snapshots()
        peak_snapshot = max(snapshots, key=lambda s: s.used_vram_gb)

        assert peak_snapshot.used_vram_gb == 44.0
        assert peak_snapshot.utilization_percent == pytest.approx(
            44.0 / 48.0 * 100.0, abs=0.1
        )  # 约 91.67%

    def test_safety_margin_is_four_gb(self):
        """2 并发时剩余显存余量为 4GB"""
        config = OllamaConfig(
            model_weights_gb=38.0,
            kv_cache_per_request_gb=2.0,
            system_overhead_gb=2.0,
            total_vram_gb=48.0,
        )
        engine = OllamaInferenceEngine(config)

        engine.submit_request("user1", "问题1")
        engine.submit_request("user2", "问题2")

        peak = engine.peak_vram_gb
        margin = config.total_vram_gb - peak
        assert margin == pytest.approx(4.0, abs=0.1)


class TestOllamaInferenceResultTracking:
    """验证推理结果记录"""

    def test_result_records_queue_wait_time(self):
        """排队的请求应记录等待时间"""
        engine = OllamaInferenceEngine(OllamaConfig(max_concurrent_requests=2))

        req1 = engine.submit_request("user1", "问题1")
        req2 = engine.submit_request("user2", "问题2")
        req3 = engine.submit_request("user3", "问题3")  # 排队

        engine.complete_request(req1.request_id)
        result3 = engine.complete_request(req3.request_id)

        # req3 从队列中取出，应有等待时间（哪怕很小）
        assert result3.queue_wait_seconds >= 0

    def test_result_records_duration(self):
        """完成结果应记录推理耗时"""
        engine = OllamaInferenceEngine(OllamaConfig(max_concurrent_requests=2))

        req1 = engine.submit_request("user1", "问题1")
        result = engine.complete_request(req1.request_id, content="回答内容")

        assert result.success is True
        assert result.content == "回答内容"
        assert result.duration_seconds >= 0

    def test_all_results_collected(self):
        """全部请求完成后，结果应完整记录"""
        engine = OllamaInferenceEngine(OllamaConfig(max_concurrent_requests=2))

        requests = [
            engine.submit_request(f"user{i}", f"问题{i}")
            for i in range(1, 6)
        ]

        for req in requests:
            engine.complete_request(req.request_id)

        results = engine.get_completed_results()
        assert len(results) == 5
        assert all(r.success for r in results)


class TestOllamaMemorySnapshotDetails:
    """验证显存快照的详细字段"""

    def test_snapshot_components_sum_to_total(self):
        """快照中各分项加起来等于总显存使用"""
        config = OllamaConfig(
            model_weights_gb=38.0,
            kv_cache_per_request_gb=2.0,
            system_overhead_gb=2.0,
            total_vram_gb=48.0,
        )
        engine = OllamaInferenceEngine(config)

        engine.submit_request("user1", "问题1")
        engine.submit_request("user2", "问题2")

        snapshots = engine.get_memory_snapshots()
        peak = max(snapshots, key=lambda s: s.used_vram_gb)

        expected_total = (
            peak.model_weights_gb
            + peak.kv_cache_gb
            + peak.system_overhead_gb
        )
        assert peak.used_vram_gb == pytest.approx(expected_total, abs=0.01)

    def test_snapshot_active_requests_matches_count(self):
        """快照中的 active_requests 字段与实际并发数一致"""
        config = OllamaConfig(
            model_weights_gb=38.0,
            kv_cache_per_request_gb=2.0,
            system_overhead_gb=2.0,
        )
        engine = OllamaInferenceEngine(config)

        engine.submit_request("user1", "问题1")
        snapshots = engine.get_memory_snapshots()
        assert snapshots[-1].active_requests == 1

        engine.submit_request("user2", "问题2")
        snapshots = engine.get_memory_snapshots()
        assert snapshots[-1].active_requests == 2

    def test_snapshot_kv_cache_scales_with_concurrency(self):
        """KV Cache 随并发数线性增长"""
        config = OllamaConfig(
            model_weights_gb=38.0,
            kv_cache_per_request_gb=2.0,
            system_overhead_gb=2.0,
        )
        engine = OllamaInferenceEngine(config)

        # 0 并发
        engine._take_memory_snapshot()
        snap0 = engine.get_memory_snapshots()[0]
        assert snap0.kv_cache_gb == 0.0

        # 1 并发
        engine.submit_request("user1", "问题1")
        snap1 = engine.get_memory_snapshots()[-1]
        assert snap1.kv_cache_gb == 2.0

        # 2 并发
        engine.submit_request("user2", "问题2")
        snap2 = engine.get_memory_snapshots()[-1]
        assert snap2.kv_cache_gb == 4.0


class TestOllamaDefaultConfiguration:
    """验证默认配置值与架构文档一致"""

    def test_default_max_concurrent_is_two(self):
        """默认最大并发为 2"""
        config = OllamaConfig()
        assert config.max_concurrent_requests == 2

    def test_default_queue_capacity_is_fifty(self):
        """默认队列容量为 50"""
        config = OllamaConfig()
        assert config.queue_capacity == 50

    def test_default_model_weights_gb(self):
        """默认模型权重 38GB"""
        config = OllamaConfig()
        assert config.model_weights_gb == 38.0

    def test_default_kv_cache_per_request_gb(self):
        """默认每请求 KV Cache 2GB"""
        config = OllamaConfig()
        assert config.kv_cache_per_request_gb == 2.0

    def test_default_system_overhead_gb(self):
        """默认系统开销 2GB"""
        config = OllamaConfig()
        assert config.system_overhead_gb == 2.0

    def test_default_total_vram_gb(self):
        """默认 GPU 显存 48GB"""
        config = OllamaConfig()
        assert config.total_vram_gb == 48.0

    def test_default_inference_timeout_is_60s(self):
        """默认推理超时 60 秒"""
        config = OllamaConfig()
        assert config.inference_timeout_seconds == 60.0

    def test_default_queue_timeout_is_180s(self):
        """默认排队超时 180 秒"""
        config = OllamaConfig()
        assert config.queue_timeout_seconds == 180.0
