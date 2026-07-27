import pytest
import asyncio
from unittest.mock import AsyncMock, MagicMock, patch
import threading


class OllamaConcurrencyLimiter:
    """Ollama推理并发限制器，最大支持2个并行请求"""

    def __init__(self, max_concurrent: int = 2):
        self.max_concurrent = max_concurrent
        self._semaphore = asyncio.Semaphore(max_concurrent)
        self._active_count = 0
        self._lock = asyncio.Lock()
        self._queue = []
        self._total_processed = 0
        self._total_queued = 0

    async def submit_request(self, request_data: dict, process_func=None) -> dict:
        """提交推理请求，超过并发限制时自动排队"""
        async with self._semaphore:
            async with self._lock:
                self._active_count += 1
                current_active = self._active_count

            if process_func is None:
                process_func = self._default_process

            result = await process_func(request_data)

            async with self._lock:
                self._active_count -= 1
                self._total_processed += 1

            return result

    async def _default_process(self, request_data: dict) -> dict:
        """默认处理函数，模拟推理延迟"""
        await asyncio.sleep(0.1)
        return {"status": "completed", "request_id": request_data.get("id", "unknown")}

    async def get_active_count(self) -> int:
        """获取当前活跃请求数"""
        async with self._lock:
            return self._active_count

    async def get_queue_length(self) -> int:
        """获取排队等待的请求数"""
        return self._total_queued

    @property
    def max_concurrency(self) -> int:
        return self.max_concurrent


class VRAMMonitor:
    """显存监控器"""

    def __init__(self, total_vram_gb: float = 48.0):
        self.total_vram_gb = total_vram_gb
        self.peak_usage_gb = 0.0
        self.current_usage_gb = 0.0
        self._vram_per_request_gb = 20.0
        self._lock = threading.Lock()

    def record_request_start(self):
        """记录请求开始时的显存占用"""
        with self._lock:
            self.current_usage_gb += self._vram_per_request_gb
            if self.current_usage_gb > self.peak_usage_gb:
                self.peak_usage_gb = self.current_usage_gb

    def record_request_end(self):
        """记录请求结束时的显存释放"""
        with self._lock:
            self.current_usage_gb -= self._vram_per_request_gb
            if self.current_usage_gb < 0:
                self.current_usage_gb = 0.0

    def get_peak_usage(self) -> float:
        """获取峰值显存使用量"""
        with self._lock:
            return self.peak_usage_gb

    def get_current_usage(self) -> float:
        """获取当前显存使用量"""
        with self._lock:
            return self.current_usage_gb

    def get_remaining_vram(self) -> float:
        """获取剩余显存"""
        with self._lock:
            return self.total_vram_gb - self.current_usage_gb


@pytest.fixture
def limiter():
    """创建并发限制器实例"""
    return OllamaConcurrencyLimiter(max_concurrent=2)


@pytest.fixture
def vram_monitor():
    """创建显存监控器实例"""
    return VRAMMonitor(total_vram_gb=48.0)


class TestOllamaConcurrencyLimit:
    """测试Ollama并发限制功能"""

    async def test_max_two_concurrent_requests(self, limiter):
        """验证最大2个并发请求"""
        active_counts = []
        lock = asyncio.Lock()

        async def tracking_process(request_data: dict) -> dict:
            async with lock:
                current = await limiter.get_active_count()
                active_counts.append(current)
            await asyncio.sleep(0.2)
            return {"status": "completed", "id": request_data["id"]}

        tasks = [
            limiter.submit_request({"id": i}, process_func=tracking_process)
            for i in range(6)
        ]
        results = await asyncio.gather(*tasks)

        assert all(count <= 2 for count in active_counts), \
            f"活跃请求数超过2: {active_counts}"
        assert len(results) == 6
        assert all(r["status"] == "completed" for r in results)

    async def test_requests_queue_when_exceeding_limit(self, limiter):
        """验证超出并发限制时请求会排队"""
        execution_order = []
        lock = asyncio.Lock()
        barrier = asyncio.Event()

        async def slow_process(request_data: dict) -> dict:
            async with lock:
                execution_order.append(f"start_{request_data['id']}")
            await barrier.wait()
            async with lock:
                execution_order.append(f"end_{request_data['id']}")
            return {"status": "completed", "id": request_data["id"]}

        # 使用 create_task 立即启动任务，而不是等 gather 时才调度
        tasks = [
            asyncio.create_task(
                limiter.submit_request({"id": i}, process_func=slow_process)
            )
            for i in range(4)
        ]

        # 等待前2个任务进入活跃状态，后2个被 semaphore 阻塞
        await asyncio.sleep(0.15)
        active_starts = [x for x in execution_order if x.startswith("start_")]
        assert len(active_starts) == 2, f"预期2个活跃，实际{len(active_starts)}: {execution_order}"

        # 释放屏障，让前2个完成，后2个开始执行
        barrier.set()
        results = await asyncio.gather(*tasks)

        assert len(results) == 4
        assert all(r["status"] == "completed" for r in results)
        all_starts = [x for x in execution_order if x.startswith("start_")]
        assert len(all_starts) == 4

        # 验证排队行为：前2个的 end 必须出现在后2个的 start 之前
        end_0_idx = execution_order.index("end_0")
        end_1_idx = execution_order.index("end_1")
        start_2_idx = execution_order.index("start_2")
        start_3_idx = execution_order.index("start_3")
        assert end_0_idx < start_2_idx, "请求2应在前2个请求完成后才开始"
        assert end_1_idx < start_3_idx, "请求3应在前2个请求完成后才开始"

    async def test_all_requests_complete_successfully(self, limiter):
        """验证所有请求最终都能完成"""
        num_requests = 10

        async def fast_process(request_data: dict) -> dict:
            await asyncio.sleep(0.01)
            return {"status": "completed", "id": request_data["id"]}

        tasks = [
            limiter.submit_request({"id": i}, process_func=fast_process)
            for i in range(num_requests)
        ]
        results = await asyncio.gather(*tasks)

        assert len(results) == num_requests
        assert all(r["status"] == "completed" for r in results)
        assert all(r["id"] in range(num_requests) for r in results)

    def test_vram_peak_within_limit(self, vram_monitor):
        """验证显存峰值不超过44GB（最大并发2 × 每请求20GB = 40GB，留4GB余量）"""
        max_concurrent = 2
        vram_per_request = 20.0
        expected_peak = max_concurrent * vram_per_request  # 40.0
        safety_margin = 4.0
        max_allowed_peak = vram_monitor.total_vram_gb - safety_margin  # 44.0

        for i in range(max_concurrent):
            vram_monitor.record_request_start()

        peak = vram_monitor.get_peak_usage()
        assert peak == expected_peak, f"预期峰值{expected_peak}GB，实际{peak}GB"
        assert peak <= max_allowed_peak, f"显存峰值{peak}GB超过安全上限{max_allowed_peak}GB（需留{safety_margin}GB余量）"

        for i in range(max_concurrent):
            vram_monitor.record_request_end()

        assert vram_monitor.get_current_usage() == 0.0

    def test_vram_with_sequential_requests(self, vram_monitor):
        """验证顺序请求时显存不会累积超标"""
        for i in range(5):
            vram_monitor.record_request_start()
            vram_monitor.record_request_end()

        peak = vram_monitor.get_peak_usage()
        assert peak == 20.0
        assert vram_monitor.get_current_usage() == 0.0

    def test_vram_remaining_margin(self, vram_monitor):
        """验证显存保留4GB余量"""
        vram_monitor.record_request_start()
        vram_monitor.record_request_start()

        remaining = vram_monitor.get_remaining_vram()
        peak = vram_monitor.get_peak_usage()

        assert remaining >= 4.0, f"剩余显存{remaining}GB小于4GB余量"
        assert (48.0 - peak) >= 4.0, f"峰值后剩余显存不足4GB"

        vram_monitor.record_request_end()
        vram_monitor.record_request_end()

    async def test_concurrent_requests_with_vram_tracking(self, limiter, vram_monitor):
        """验证并发请求配合显存监控"""
        lock = asyncio.Lock()

        async def process_with_vram(request_data: dict) -> dict:
            vram_monitor.record_request_start()
            await asyncio.sleep(0.1)
            vram_monitor.record_request_end()
            return {"status": "completed", "id": request_data["id"]}

        tasks = [
            limiter.submit_request({"id": i}, process_func=process_with_vram)
            for i in range(4)
        ]
        results = await asyncio.gather(*tasks)

        assert len(results) == 4
        peak = vram_monitor.get_peak_usage()
        assert peak <= 44.0, f"显存峰值{peak}GB超过44GB"
        assert vram_monitor.get_current_usage() == 0.0

    async def test_active_count_accuracy(self, limiter):
        """验证活跃计数准确性"""
        event = asyncio.Event()

        async def blocking_process(request_data: dict) -> dict:
            event.wait()
            return {"status": "completed", "id": request_data["id"]}

        task1 = asyncio.create_task(
            limiter.submit_request({"id": 1}, process_func=blocking_process)
        )
        await asyncio.sleep(0.05)

        task2 = asyncio.create_task(
            limiter.submit_request({"id": 2}, process_func=blocking_process)
        )
        await asyncio.sleep(0.05)

        active = await limiter.get_active_count()
        assert active == 2

        event.set()
        await task1
        await task2

        active_after = await limiter.get_active_count()
        assert active_after == 0

    def test_limiter_configuration(self):
        """验证限制器配置"""
        limiter = OllamaConcurrencyLimiter(max_concurrent=2)
        assert limiter.max_concurrency == 2
        assert limiter.max_concurrent == 2

        limiter_custom = OllamaConcurrencyLimiter(max_concurrent=4)
        assert limiter_custom.max_concurrency == 4

    async def test_limiter_max_concurrent_one(self):
        """验证 max_concurrent=1 时严格串行"""
        limiter = OllamaConcurrencyLimiter(max_concurrent=1)
        active_counts = []
        lock = asyncio.Lock()

        async def tracking_process(request_data: dict) -> dict:
            async with lock:
                count = await limiter.get_active_count()
                active_counts.append(count)
            await asyncio.sleep(0.05)
            return {"status": "completed", "id": request_data["id"]}

        tasks = [
            asyncio.create_task(
                limiter.submit_request({"id": i}, process_func=tracking_process)
            )
            for i in range(4)
        ]
        await asyncio.gather(*tasks)

        assert all(c == 1 for c in active_counts), f"max_concurrent=1时活跃数应恒为1: {active_counts}"

    async def test_limiter_max_concurrent_zero_raises(self):
        """验证 max_concurrent=0 时创建 semaphore(0) 后所有请求永久阻塞"""
        limiter = OllamaConcurrencyLimiter(max_concurrent=0)
        event = asyncio.Event()

        async def blocking_process(request_data: dict) -> dict:
            event.wait()
            return {"status": "completed"}

        task = asyncio.create_task(
            limiter.submit_request({"id": 1}, process_func=blocking_process)
        )
        await asyncio.sleep(0.15)
        assert task.done() is False, "max_concurrent=0 时请求应被阻塞"

        event.set()
        task.cancel()
        try:
            await task
        except asyncio.CancelledError:
            pass

    async def test_process_func_exception_releases_semaphore(self):
        """验证 process_func 抛异常时 semaphore 正确释放"""
        limiter = OllamaConcurrencyLimiter(max_concurrent=2)

        async def failing_process(request_data: dict) -> dict:
            raise ValueError("模拟推理失败")

        async def success_process(request_data: dict) -> dict:
            await asyncio.sleep(0.05)
            return {"status": "completed", "id": request_data["id"]}

        # 先让2个失败请求占满 semaphore
        fail_tasks = [
            asyncio.create_task(
                limiter.submit_request({"id": f"fail_{i}"}, process_func=failing_process)
            )
            for i in range(2)
        ]
        for t in fail_tasks:
            with pytest.raises(ValueError):
                await t

        # 验证 semaphore 已释放，新请求可以正常进入
        success_task = asyncio.create_task(
            limiter.submit_request({"id": "success_1"}, process_func=success_process)
        )
        result = await asyncio.wait_for(success_task, timeout=2.0)
        assert result["status"] == "completed"
        active = await limiter.get_active_count()
        assert active == 0

    async def test_request_data_missing_id_key(self):
        """验证 request_data 缺少 id 键时不抛出 KeyError"""
        limiter = OllamaConcurrencyLimiter(max_concurrent=2)

        result = await limiter.submit_request({})
        assert result["status"] == "completed"
        assert result["request_id"] == "unknown"

        result2 = await limiter.submit_request({"other": "data"})
        assert result2["status"] == "completed"
        assert result2["request_id"] == "unknown"

    async def test_high_concurrency_stability(self):
        """验证 100+ 并发请求稳定性"""
        limiter = OllamaConcurrencyLimiter(max_concurrent=2)
        num_requests = 120
        errors = []

        async def fast_process(request_data: dict) -> dict:
            await asyncio.sleep(0.001)
            return {"status": "completed", "id": request_data["id"]}

        tasks = [
            asyncio.create_task(
                limiter.submit_request({"id": i}, process_func=fast_process)
            )
            for i in range(num_requests)
        ]
        results = await asyncio.gather(*tasks, return_exceptions=True)

        for i, r in enumerate(results):
            if isinstance(r, Exception):
                errors.append((i, str(r)))

        assert len(errors) == 0, f"高并发中出现异常: {errors}"
        completed = [r for r in results if not isinstance(r, Exception)]
        assert len(completed) == num_requests
        assert all(r["id"] in range(num_requests) for r in completed)
        active = await limiter.get_active_count()
        assert active == 0, "所有请求完成后活跃数应为0"

    async def test_semaphore_count_returns_to_zero(self):
        """验证连续提交请求后 semaphore 计数归零（无资源泄漏）"""
        limiter = OllamaConcurrencyLimiter(max_concurrent=2)

        for batch in range(5):
            tasks = [
                asyncio.create_task(
                    limiter.submit_request(
                        {"id": f"batch{batch}_id{j}"},
                        process_func=limiter._default_process
                    )
                )
                for j in range(3)
            ]
            await asyncio.gather(*tasks)

        active = await limiter.get_active_count()
        assert active == 0, "连续多批请求后活跃计数应为0"
        total = limiter._total_processed
        assert total == 15, f"应处理15个请求，实际{total}"


class TestVRAMMonitor:
    """测试显存监控器"""

    def test_initial_state(self, vram_monitor):
        """验证初始状态"""
        assert vram_monitor.get_current_usage() == 0.0
        assert vram_monitor.get_peak_usage() == 0.0
        assert vram_monitor.get_remaining_vram() == 48.0

    def test_peak_tracking(self, vram_monitor):
        """验证峰值追踪"""
        vram_monitor.record_request_start()
        assert vram_monitor.get_peak_usage() == 20.0

        vram_monitor.record_request_start()
        assert vram_monitor.get_peak_usage() == 40.0

        vram_monitor.record_request_end()
        assert vram_monitor.get_peak_usage() == 40.0

        vram_monitor.record_request_end()
        assert vram_monitor.get_peak_usage() == 40.0

    def test_usage_negoes_negative(self, vram_monitor):
        """验证显存使用量不会变为负数"""
        vram_monitor.record_request_end()
        assert vram_monitor.get_current_usage() == 0.0

    def test_vram_total_zero(self):
        """验证 total_vram_gb=0 的边界"""
        monitor = VRAMMonitor(total_vram_gb=0.0)
        assert monitor.get_remaining_vram() == 0.0

        monitor.record_request_start()
        assert monitor.get_peak_usage() == 20.0
        remaining = monitor.get_remaining_vram()
        assert remaining == -20.0, f"总显存0GB时，剩余显存应为负数: {remaining}"

        monitor.record_request_end()
        assert monitor.get_current_usage() == 0.0

    def test_vram_total_very_small(self):
        """验证 total_vram_gb 极小值（如 1.0GB）"""
        monitor = VRAMMonitor(total_vram_gb=1.0)

        monitor.record_request_start()
        remaining = monitor.get_remaining_vram()
        assert remaining == -19.0, f"1GB显存时启动请求后剩余应为-19GB: {remaining}"

        monitor.record_request_end()
        assert monitor.get_current_usage() == 0.0
        assert monitor.get_remaining_vram() == 1.0
