import re
import time
from datetime import datetime, timezone, timedelta
from typing import Dict, List, Optional, Tuple
from dataclasses import dataclass, field
from enum import Enum
from io import StringIO

import pytest


# ====================================================================
# 领域模型
# ====================================================================

class RequestStatus(str, Enum):
    """LLM 请求状态"""
    PENDING = "pending"
    PROCESSING = "processing"
    COMPLETED = "completed"
    TIMED_OUT = "timed_out"
    FAILED = "failed"


@dataclass
class LlmRequestRecord:
    """LLM 请求记录"""
    request_id: str
    model: str
    provider: str
    started_at: datetime
    finished_at: Optional[datetime] = None
    status: str = RequestStatus.PENDING.value
    duration_seconds: float = 0.0
    timed_out: bool = False
    timeout_threshold: float = 60.0

    def record_start(self):
        self.status = RequestStatus.PROCESSING.value
        self.started_at = datetime.now(timezone.utc)

    def record_success(self, duration: float):
        self.status = RequestStatus.COMPLETED.value
        self.finished_at = datetime.now(timezone.utc)
        self.duration_seconds = duration
        self.timed_out = False

    def record_timeout(self, waited: float, threshold: float = None):
        self.status = RequestStatus.TIMED_OUT.value
        self.finished_at = datetime.now(timezone.utc)
        self.duration_seconds = waited
        self.timed_out = True
        if threshold is not None:
            self.timeout_threshold = threshold

    def record_failure(self, duration: float):
        self.status = RequestStatus.FAILED.value
        self.finished_at = datetime.now(timezone.utc)
        self.duration_seconds = duration
        self.timed_out = False


# ====================================================================
# Prometheus 指标收集器（自实现，不依赖外部 prometheus_client）
# ====================================================================

@dataclass
class CounterSample:
    """计数器采样点"""
    name: str
    labels: Dict[str, str]
    value: float

    def format_prometheus(self) -> str:
        label_str = self._format_labels()
        return f'{self.name}{label_str} {self.value}'

    def _format_labels(self) -> str:
        if not self.labels:
            return ""
        parts = [f'{k}="{v}"' for k, v in sorted(self.labels.items())]
        return "{" + ",".join(parts) + "}"


@dataclass
class HistogramSample:
    """直方图采样点"""
    name: str
    labels: Dict[str, str]
    buckets: List[Tuple[str, float]]  # (le_value, cumulative_count)
    sum_value: float
    count_value: float

    def format_prometheus(self) -> str:
        lines = []
        for le, cnt in self.buckets:
            all_labels = dict(self.labels)
            all_labels["le"] = le
            label_str = self._format_labels_from(all_labels)
            lines.append(f'{self.name}_bucket{label_str} {cnt}')
        lines.append(f'{self.name}_sum{self._format_labels()} {self.sum_value}')
        lines.append(f'{self.name}_count{self._format_labels()} {self.count_value}')
        return "\n".join(lines)

    def _format_labels(self) -> str:
        if not self.labels:
            return ""
        parts = [f'{k}="{v}"' for k, v in sorted(self.labels.items())]
        return "{" + ",".join(parts) + "}"

    def _format_labels_from(self, labels: Dict[str, str]) -> str:
        if not labels:
            return ""
        parts = [f'{k}="{v}"' for k, v in sorted(labels.items())]
        return "{" + ",".join(parts) + "}"


class LlmMetricsCollector:
    """
    LLM 指标收集器

    收集两类指标：
    - llm_request_timeout_total: 计数器，记录超时请求数
    - llm_request_duration_seconds: 直方图，记录请求耗时分布
    """

    DEFAULT_TIMEOUT_THRESHOLD = 60.0

    # 直方图桶边界（秒）
    # 直方图桶边界（秒），使用 float('inf') 表示 +Inf
    DEFAULT_BUCKETS = [0.1, 0.5, 1.0, 2.5, 5.0, 10.0, 30.0, 60.0, 120.0, 300.0, float('inf')]

    def __init__(self, timeout_threshold: float = None, buckets: List[float] = None, default_timeout: float = None):
        self._timeout_threshold = timeout_threshold or default_timeout or self.DEFAULT_TIMEOUT_THRESHOLD
        self._buckets = buckets or self.DEFAULT_BUCKETS
        # 计数器: {(model, provider): timeout_count}
        self._timeout_counts: Dict[Tuple[str, str], int] = {}
        # 直方图: {(model, provider): list of durations}
        self._duration_samples: Dict[Tuple[str, str], List[float]] = {}

    def record_request_success(self, model: str, provider: str, duration: float):
        """记录成功的请求耗时"""
        key = (model, provider)
        if key not in self._duration_samples:
            self._duration_samples[key] = []
        self._duration_samples[key].append(duration)

    def record_request_timeout(self, model: str, provider: str, duration: float):
        """记录超时的请求（同时计入超时计数器和耗时直方图）"""
        key = (model, provider)
        # 超时计数器 +1
        self._timeout_counts[key] = self._timeout_counts.get(key, 0) + 1
        # 同时记录到耗时直方图
        if key not in self._duration_samples:
            self._duration_samples[key] = []
        self._duration_samples[key].append(duration)

    def record_request_failure(self, model: str, provider: str, duration: float):
        """记录失败的请求耗时（非超时）"""
        key = (model, provider)
        if key not in self._duration_samples:
            self._duration_samples[key] = []
        self._duration_samples[key].append(duration)

    def get_timeout_total(self, model: str = None, provider: str = None) -> int:
        """
        获取超时请求总数。

        如果指定 model/provider，返回该维度的超时数；
        否则返回所有维度超时数的总和。
        """
        if model is not None and provider is not None:
            return self._timeout_counts.get((model, provider), 0)
        return sum(self._timeout_counts.values())

    def get_duration_histogram(self, model: str, provider: str) -> Optional[HistogramSample]:
        """获取指定 model/provider 的耗时直方图"""
        key = (model, provider)
        durations = self._duration_samples.get(key, [])
        if not durations:
            return None
        return self._build_histogram(model, provider, durations)

    def get_all_duration_histograms(self) -> List[HistogramSample]:
        """获取所有维度的耗时直方图"""
        results = []
        for (model, provider), durations in self._duration_samples.items():
            if durations:
                results.append(self._build_histogram(model, provider, durations))
        return results

    def collect_metrics(self) -> str:
        """
        收集所有指标并格式化为 Prometheus 文本格式输出。

        返回包含 HELP、TYPE 声明以及所有样本数据的字符串。
        """
        lines = []

        # --- 超时计数器 ---
        lines.append("# HELP llm_request_timeout_total 超时请求总数")
        lines.append("# TYPE llm_request_timeout_total counter")
        for (model, provider), count in sorted(self._timeout_counts.items()):
            labels = {
                'model': model,
                'provider': provider,
            }
            sample = CounterSample(
                name="llm_request_timeout_total",
                labels=labels,
                value=float(count),
            )
            lines.append(sample.format_prometheus())

        # --- 耗时直方图 ---
        lines.append("# HELP llm_request_duration_seconds 请求耗时分布（秒）")
        lines.append("# TYPE llm_request_duration_seconds histogram")
        for (model, provider), durations in sorted(self._duration_samples.items()):
            if durations:
                hist = self._build_histogram(model, provider, durations)
                lines.append(hist.format_prometheus())

        return "\n".join(lines)

    def _build_histogram(self, model: str, provider: str, durations: List[float]) -> HistogramSample:
        """根据耗时采样数据和桶边界构建直方图"""
        labels = {'model': model, 'provider': provider}
        sorted_buckets = sorted(self._buckets)
        buckets = []
        for boundary in sorted_buckets:
            if boundary == float('inf'):
                # +Inf 桶包含所有样本
                buckets.append(("+Inf", len(durations)))
            else:
                count = sum(1 for d in durations if d <= boundary)
                buckets.append((str(boundary), count))

        duration_sum = sum(durations)
        duration_count = len(durations)

        return HistogramSample(
            name="llm_request_duration_seconds",
            labels=labels,
            buckets=buckets,
            sum_value=duration_sum,
            count_value=duration_count,
        )


# ====================================================================
# 被测试的 LLM 请求网关
# ====================================================================

class LlmRequestGateway:
    """
    LLM 请求网关

    负责：
    1. 发起 LLM 请求
    2. 跟踪请求生命周期
    3. 向指标收集器上报指标
    """

    def __init__(self, metrics_collector: LlmMetricsCollector, default_timeout: float = 60.0):
        self.metrics = metrics_collector
        self._default_timeout = default_timeout
        self._requests: Dict[str, LlmRequestRecord] = {}
        self._request_counter = 0

    def create_request(self, model: str, provider: str, timeout: float = None) -> str:
        """创建 LLM 请求记录，返回 request_id"""
        self._request_counter += 1
        request_id = f"req-{self._request_counter:04d}"
        record = LlmRequestRecord(
            request_id=request_id,
            model=model,
            provider=provider,
            started_at=datetime.now(timezone.utc),
            timeout_threshold=timeout or self._default_timeout,
        )
        self._requests[request_id] = record
        return request_id

    def complete_request(self, request_id: str, duration: float):
        """标记请求成功完成"""
        record = self._requests.get(request_id)
        if record is None:
            raise ValueError(f"请求 {request_id} 不存在")
        record.record_success(duration)
        self.metrics.record_request_success(record.model, record.provider, duration)

    def timeout_request(self, request_id: str, waited: float):
        """标记请求超时"""
        record = self._requests.get(request_id)
        if record is None:
            raise ValueError(f"请求 {request_id} 不存在")
        record.record_timeout(waited, self._default_timeout)
        self.metrics.record_request_timeout(record.model, record.provider, waited)

    def fail_request(self, request_id: str, duration: float):
        """标记请求失败（非超时）"""
        record = self._requests.get(request_id)
        if record is None:
            raise ValueError(f"请求 {request_id} 不存在")
        record.record_failure(duration)
        self.metrics.record_request_failure(record.model, record.provider, duration)

    def get_request(self, request_id: str) -> Optional[LlmRequestRecord]:
        return self._requests.get(request_id)

    @property
    def total_requests(self) -> int:
        return len(self._requests)


# ====================================================================
# Prometheus metrics 端点解析器
# ====================================================================

def parse_prometheus_metrics(text: str) -> Dict[str, List[Dict]]:
    """
    解析 Prometheus 文本格式的 metrics 输出。

    返回: {metric_name: [sample_dict, ...]}
    每个 sample_dict 包含: labels (dict), value (float)
    """
    result: Dict[str, List[Dict]] = {}
    for line in text.strip().split("\n"):
        line = line.strip()
        if not line or line.startswith("#"):
            continue
        # 解析: metric_name{labels} value
        match = re.match(r'^([a-zA-Z_:][a-zA-Z0-9_:]*)(\{[^}]*\})?\s+([0-9eE.+-]+)$', line)
        if not match:
            continue
        name = match.group(1)
        label_str = match.group(2) or ""
        value = float(match.group(3))
        labels = _parse_labels(label_str)
        if name not in result:
            result[name] = []
        result[name].append({"labels": labels, "value": value})
    return result


def _parse_labels(label_str: str) -> Dict[str, str]:
    """解析 {key1="val1",key2="val2"} 格式的标签字符串"""
    labels = {}
    if not label_str:
        return labels
    inner = label_str.strip("{}")
    if not inner:
        return labels
    pairs = re.findall(r'(\w+)="([^"]*)"', inner)
    for k, v in pairs:
        labels[k] = v
    return labels


# ====================================================================
# 测试用例
# ====================================================================

class TestLlmMetricsCollector:
    """测试 LLM 指标收集器"""

    @pytest.fixture
    def collector(self):
        return LlmMetricsCollector()

    def test_initial_timeout_total_is_zero(self, collector):
        """初始状态下超时计数器为 0"""
        assert collector.get_timeout_total() == 0

    def test_initial_no_duration_samples(self, collector):
        """初始状态下没有耗时采样数据"""
        histograms = collector.get_all_duration_histograms()
        assert len(histograms) == 0

    def test_record_success_only_affects_duration_not_timeout(self, collector):
        """成功请求只影响耗时直方图，不影响超时计数器"""
        collector.record_request_success("gpt-4", "openai", 2.5)
        # 超时计数器不变
        assert collector.get_timeout_total() == 0
        # 耗时直方图有数据
        hist = collector.get_duration_histogram("gpt-4", "openai")
        assert hist is not None
        assert hist.count_value == 1
        assert abs(hist.sum_value - 2.5) < 0.001

    def test_record_timeout_increments_counter(self, collector):
        """超时请求使超时计数器 +1"""
        collector.record_request_timeout("gpt-4", "openai", 60.0)
        assert collector.get_timeout_total() == 1
        assert collector.get_timeout_total("gpt-4", "openai") == 1

    def test_record_timeout_also_goes_to_duration_histogram(self, collector):
        """超时请求同时记录到耗时直方图"""
        collector.record_request_timeout("gpt-4", "openai", 60.0)
        hist = collector.get_duration_histogram("gpt-4", "openai")
        assert hist is not None
        assert hist.count_value == 1
        assert abs(hist.sum_value - 60.0) < 0.001

    def test_multiple_timeouts_accumulate_correctly(self, collector):
        """多次超时请求累加计数正确"""
        for i in range(5):
            collector.record_request_timeout("gpt-4", "openai", 60.0 + i)
        assert collector.get_timeout_total() == 5
        assert collector.get_timeout_total("gpt-4", "openai") == 5

    def test_timeout_counter_per_dimension(self, collector):
        """超时计数器按 model/provider 维度独立统计"""
        collector.record_request_timeout("gpt-4", "openai", 60.0)
        collector.record_request_timeout("gpt-4", "openai", 60.0)
        collector.record_request_timeout("claude-3", "anthropic", 60.0)
        assert collector.get_timeout_total() == 3
        assert collector.get_timeout_total("gpt-4", "openai") == 2
        assert collector.get_timeout_total("claude-3", "anthropic") == 1

    def test_duration_histogram_count_matches_total_requests(self, collector):
        """耗时直方图的 count 等于该维度的总请求数（含成功 + 超时 + 失败）"""
        collector.record_request_success("gpt-4", "openai", 1.0)
        collector.record_request_success("gpt-4", "openai", 2.0)
        collector.record_request_timeout("gpt-4", "openai", 60.0)
        collector.record_request_failure("gpt-4", "openai", 0.5)
        hist = collector.get_duration_histogram("gpt-4", "openai")
        assert hist.count_value == 4

    def test_duration_histogram_sum_is_correct(self, collector):
        """耗时直方图的 sum 等于所有请求耗时之和"""
        collector.record_request_success("gpt-4", "openai", 1.0)
        collector.record_request_success("gpt-4", "openai", 2.0)
        collector.record_request_timeout("gpt-4", "openai", 60.0)
        collector.record_request_failure("gpt-4", "openai", 0.5)
        hist = collector.get_duration_histogram("gpt-4", "openai")
        expected_sum = 1.0 + 2.0 + 60.0 + 0.5
        assert abs(hist.sum_value - expected_sum) < 0.001


class TestPrometheusMetricsEndpoint:
    """测试 Prometheus metrics 端点输出格式"""

    @pytest.fixture
    def collector(self):
        return LlmMetricsCollector()

    def test_metrics_output_contains_timeout_counter_help_and_type(self, collector):
        """metrics 输出包含超时计数器的 HELP 和 TYPE 声明"""
        collector.record_request_timeout("gpt-4", "openai", 60.0)
        output = collector.collect_metrics()
        assert "# HELP llm_request_timeout_total" in output
        assert "# TYPE llm_request_timeout_total counter" in output

    def test_metrics_output_contains_duration_histogram_help_and_type(self, collector):
        """metrics 输出包含耗时直方图的 HELP 和 TYPE 声明"""
        collector.record_request_success("gpt-4", "openai", 2.5)
        output = collector.collect_metrics()
        assert "# HELP llm_request_duration_seconds" in output
        assert "# TYPE llm_request_duration_seconds histogram" in output

    def test_metrics_output_timeout_total_value_equals_timeout_count(self, collector):
        """
        验收标准 1：llm_request_timeout_total 计数器值等于超时请求数量
        """
        num_timeouts = 7
        for i in range(num_timeouts):
            collector.record_request_timeout("gpt-4", "openai", 60.0 + i * 0.1)
        # 也记录一些成功请求，确保它们不影响超时计数
        for i in range(3):
            collector.record_request_success("gpt-4", "openai", 1.0 + i * 0.5)

        output = collector.collect_metrics()
        parsed = parse_prometheus_metrics(output)

        # 验证超时计数器的值
        timeout_samples = parsed.get("llm_request_timeout_total", [])
        assert len(timeout_samples) > 0
        gpt4_sample = next(
            (s for s in timeout_samples if s["labels"].get("model") == "gpt-4"),
            None,
        )
        assert gpt4_sample is not None
        assert gpt4_sample["value"] == num_timeouts

    def test_metrics_output_duration_histogram_contains_all_request_durations(self, collector):
        """
        验收标准 2：llm_request_duration_seconds 直方图包含所有请求的耗时分布数据
        """
        durations = [0.5, 1.0, 2.5, 5.0, 10.0, 60.0]
        for d in durations:
            if d >= 60.0:
                collector.record_request_timeout("gpt-4", "openai", d)
            else:
                collector.record_request_success("gpt-4", "openai", d)

        output = collector.collect_metrics()
        parsed = parse_prometheus_metrics(output)

        # 验证直方图的 count 等于总请求数
        duration_count_samples = parsed.get("llm_request_duration_seconds_count", [])
        assert len(duration_count_samples) > 0
        assert duration_count_samples[0]["value"] == len(durations)

        # 验证直方图的 sum 等于总耗时
        duration_sum_samples = parsed.get("llm_request_duration_seconds_sum", [])
        assert len(duration_sum_samples) > 0
        expected_sum = sum(durations)
        assert abs(duration_sum_samples[0]["value"] - expected_sum) < 0.001

        # 验证直方图 bucket 数据存在
        bucket_samples = parsed.get("llm_request_duration_seconds_bucket", [])
        assert len(bucket_samples) > 0

    def test_metrics_output_format_is_prometheus_compliant(self, collector):
        """metrics 输出格式符合 Prometheus 规范"""
        collector.record_request_success("gpt-4", "openai", 2.5)
        collector.record_request_timeout("gpt-4", "openai", 60.0)
        collector.record_request_success("claude-3", "anthropic", 1.5)

        output = collector.collect_metrics()

        # 验证 HELP 和 TYPE 行
        assert "# HELP" in output
        assert "# TYPE" in output

        # 验证数据行格式: metric_name{labels} value
        data_lines = [l for l in output.split("\n") if l.strip() and not l.startswith("#")]
        for line in data_lines:
            assert re.match(r'^[a-zA-Z_][a-zA-Z0-9_:]*\{[^}]*\}\s+[\d.eE+-]+$', line), \
                f"不符合 Prometheus 格式: {line}"

    def test_metrics_output_contains_bucket_boundaries(self, collector):
        """直方图包含正确的桶边界"""
        collector.record_request_success("gpt-4", "openai", 2.5)
        output = collector.collect_metrics()
        assert 'le="0.1"' in output
        assert 'le="0.5"' in output
        assert 'le="1.0"' in output
        assert 'le="2.5"' in output
        assert 'le="+Inf"' in output

    def test_metrics_output_cumulative_buckets_increasing(self, collector):
        """直方图桶的累计值是单调递增的"""
        durations = [0.2, 0.3, 0.8, 1.5, 3.0, 7.0, 45.0]
        for d in durations:
            collector.record_request_success("gpt-4", "openai", d)

        output = collector.collect_metrics()
        parsed = parse_prometheus_metrics(output)
        bucket_samples = parsed.get("llm_request_duration_seconds_bucket", [])
        # 过滤出 gpt-4/openai 的 bucket 且不含 +Inf
        gpt4_buckets = [s for s in bucket_samples if s["labels"].get("model") == "gpt-4" and s["labels"].get("le") != "+Inf"]
        values = [s["value"] for s in gpt4_buckets]
        # 验证单调非递减
        for i in range(1, len(values)):
            assert values[i] >= values[i - 1], \
                f"直方图桶非单调递增: {values}"


class TestLlmRequestGatewayIntegration:
    """测试 LLM 请求网关与指标收集的集成"""

    @pytest.fixture
    def collector(self):
        return LlmMetricsCollector(default_timeout=30.0)

    @pytest.fixture
    def gateway(self, collector):
        return LlmRequestGateway(collector, default_timeout=30.0)

    def test_gateway_creates_and_tracks_requests(self, gateway):
        """网关创建请求后能正确追踪"""
        req_id = gateway.create_request("gpt-4", "openai")
        assert req_id is not None
        record = gateway.get_request(req_id)
        assert record is not None
        assert record.model == "gpt-4"
        assert record.provider == "openai"
        assert record.status == RequestStatus.PENDING.value

    def test_gateway_complete_request_records_duration(self, gateway, collector):
        """网关完成请求后正确记录耗时到直方图"""
        req_id = gateway.create_request("gpt-4", "openai")
        gateway.complete_request(req_id, 3.5)

        record = gateway.get_request(req_id)
        assert record.status == RequestStatus.COMPLETED.value
        assert abs(record.duration_seconds - 3.5) < 0.001

        hist = collector.get_duration_histogram("gpt-4", "openai")
        assert hist is not None
        assert hist.count_value == 1

    def test_gateway_timeout_request_records_both_metrics(self, gateway, collector):
        """网关超时请求后同时记录超时计数和耗时直方图"""
        req_id = gateway.create_request("gpt-4", "openai")
        gateway.timeout_request(req_id, 30.0)

        # 验证记录状态
        record = gateway.get_request(req_id)
        assert record.status == RequestStatus.TIMED_OUT.value
        assert record.timed_out is True

        # 验证超时计数器
        assert collector.get_timeout_total() == 1
        assert collector.get_timeout_total("gpt-4", "openai") == 1

        # 验证耗时直方图
        hist = collector.get_duration_histogram("gpt-4", "openai")
        assert hist is not None
        assert hist.count_value == 1
        assert abs(hist.sum_value - 30.0) < 0.001

    def test_gateway_mixed_requests_full_metrics_pipeline(self, gateway, collector):
        """
        完整管道测试：混合请求场景下所有指标正确采集

        模拟 10 个请求：
        - 5 个成功（不同耗时）
        - 3 个超时
        - 2 个失败
        验证 metrics 端点输出正确
        """
        # 创建 5 个成功请求
        success_ids = []
        for i in range(5):
            req_id = gateway.create_request("gpt-4", "openai")
            success_ids.append(req_id)

        # 创建 3 个超时请求
        timeout_ids = []
        for i in range(3):
            req_id = gateway.create_request("gpt-4", "openai")
            timeout_ids.append(req_id)

        # 创建 2 个失败请求
        fail_ids = []
        for i in range(2):
            req_id = gateway.create_request("gpt-4", "openai")
            fail_ids.append(req_id)

        # 记录结果
        for i, req_id in enumerate(success_ids):
            gateway.complete_request(req_id, 1.0 + i * 0.5)
        for req_id in timeout_ids:
            gateway.timeout_request(req_id, 30.0)
        for req_id in fail_ids:
            gateway.fail_request(req_id, 0.5)

        # 验收标准 1: 超时计数器 = 3
        assert collector.get_timeout_total() == 3

        # 验收标准 2: 直方图 count = 10（全部请求）
        hist = collector.get_duration_histogram("gpt-4", "openai")
        assert hist.count_value == 10

        # 验证 metrics 端点输出
        output = collector.collect_metrics()
        parsed = parse_prometheus_metrics(output)

        # 超时计数器验证
        timeout_samples = parsed.get("llm_request_timeout_total", [])
        assert len(timeout_samples) == 1
        assert timeout_samples[0]["value"] == 3.0

        # 直方图 count 验证
        count_samples = parsed.get("llm_request_duration_seconds_count", [])
        assert len(count_samples) == 1
        assert count_samples[0]["value"] == 10.0

        # 直方图 sum 验证
        expected_sum = (1.0 + 1.5 + 2.0 + 2.5 + 3.0) + (30.0 * 3) + (0.5 * 2)
        sum_samples = parsed.get("llm_request_duration_seconds_sum", [])
        assert len(sum_samples) == 1
        assert abs(sum_samples[0]["value"] - expected_sum) < 0.001

    def test_gateway_multi_provider_metrics_isolation(self, gateway, collector):
        """不同 provider 的指标相互隔离"""
        # openai 请求
        for i in range(3):
            req_id = gateway.create_request("gpt-4", "openai")
            gateway.complete_request(req_id, 2.0)
        req_id = gateway.create_request("gpt-4", "openai")
        gateway.timeout_request(req_id, 30.0)

        # anthropic 请求
        for i in range(2):
            req_id = gateway.create_request("claude-3", "anthropic")
            gateway.complete_request(req_id, 1.5)
        req_id = gateway.create_request("claude-3", "anthropic")
        gateway.timeout_request(req_id, 30.0)
        req_id = gateway.create_request("claude-3", "anthropic")
        gateway.timeout_request(req_id, 30.0)

        # 验证指标隔离
        assert collector.get_timeout_total("gpt-4", "openai") == 1
        assert collector.get_timeout_total("claude-3", "anthropic") == 2
        assert collector.get_timeout_total() == 3

        # 直方图隔离
        hist_openai = collector.get_duration_histogram("gpt-4", "openai")
        hist_anthropic = collector.get_duration_histogram("claude-3", "anthropic")
        assert hist_openai.count_value == 4
        assert hist_anthropic.count_value == 4

    def test_gateway_no_requests_yields_empty_metrics(self, gateway, collector):
        """无请求时 metrics 输出不包含数据行"""
        output = collector.collect_metrics()
        data_lines = [l for l in output.split("\n") if l.strip() and not l.startswith("#")]
        # 只有 HELP/TYPE 声明，无数据行
        assert len(data_lines) == 0

    def test_gateway_timeout_request_not_found_raises_error(self, gateway):
        """对不存在的 request_id 调用超时方法应抛出异常"""
        with pytest.raises(ValueError, match="不存在"):
            gateway.timeout_request("nonexistent-id", 30.0)

    def test_gateway_complete_request_not_found_raises_error(self, gateway):
        """对不存在的 request_id 调用完成方法应抛出异常"""
        with pytest.raises(ValueError, match="不存在"):
            gateway.complete_request("nonexistent-id", 2.0)
