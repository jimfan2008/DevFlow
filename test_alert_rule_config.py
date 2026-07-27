import time
import uuid
import asyncio
import pytest
from datetime import datetime, timezone
from typing import Optional

from httpx import ASGITransport, AsyncClient
from fastapi import FastAPI
from pydantic import BaseModel


# ====================================================================
# 被测试的领域模型
# ====================================================================

RULE_TYPES = {"agent_timeout", "consecutive_failure", "resource_exceed"}


class AlertRuleInput(BaseModel):
    name: str
    rule_type: str
    threshold: float
    duration_seconds: int = 300
    enabled: bool = True
    description: Optional[str] = None


class AlertRule(AlertRuleInput):
    id: str
    created_at: str
    updated_at: str


class AlertRuleRepository:
    """内存级存储，模拟持久化层"""

    def __init__(self):
        self._store: dict = {}

    def insert(self, data: AlertRuleInput) -> AlertRule:
        now = datetime.now(timezone.utc).isoformat()
        rule = AlertRule(
            id=str(uuid.uuid4()),
            created_at=now,
            updated_at=now,
            **data.model_dump(),
        )
        self._store[rule.id] = rule
        return rule

    def find_all(self) -> list:
        return list(self._store.values())

    def find_by_id(self, rule_id: str) -> Optional[AlertRule]:
        return self._store.get(rule_id)

    def count_enabled(self) -> int:
        return sum(1 for r in self._store.values() if r.enabled)

    def clear(self):
        self._store.clear()


# ====================================================================
# FastAPI 应用
# ====================================================================

app = FastAPI(title="AlertRule API")
repo = AlertRuleRepository()


@app.post("/alert-rules", status_code=201)
async def create_alert_rule(payload: AlertRuleInput):
    rule = repo.insert(payload)
    return rule.model_dump()


@app.get("/alert-rules")
async def list_alert_rules():
    return [r.model_dump() for r in repo.find_all()]


# ====================================================================
# Fixtures
# ====================================================================

@pytest.fixture(autouse=True)
def _clean_repo():
    repo.clear()


@pytest.fixture
def event_loop():
    loop = asyncio.new_event_loop()
    yield loop
    loop.close()


@pytest.fixture
async def http_client(event_loop):
    transport = ASGITransport(app=app)
    async with AsyncClient(transport=transport, base_url="http://test") as client:
        yield client


# ====================================================================
# 测试用例
# ====================================================================

class TestAlertRuleHTTP201:
    """验收标准 1：HTTP 201 返回"""

    async def test_returns_201_on_create(self, http_client):
        resp = await http_client.post("/alert-rules", json={
            "name": "agent-超时告警",
            "rule_type": "agent_timeout",
            "threshold": 30.0,
        })
        assert resp.status_code == 201

    async def test_response_contains_rule_id(self, http_client):
        resp = await http_client.post("/alert-rules", json={
            "name": "test-rule",
            "rule_type": "agent_timeout",
            "threshold": 10.0,
        })
        body = resp.json()
        assert body["id"] is not None
        assert len(body["id"]) > 0

    async def test_response_echoes_input_fields(self, http_client):
        payload = {
            "name": "echo-test",
            "rule_type": "consecutive_failure",
            "threshold": 5.0,
            "duration_seconds": 120,
            "enabled": True,
        }
        resp = await http_client.post("/alert-rules", json=payload)
        body = resp.json()
        assert body["name"] == "echo-test"
        assert body["rule_type"] == "consecutive_failure"
        assert body["threshold"] == 5.0
        assert body["duration_seconds"] == 120


class TestAlertRuleResponseTime:
    """验收标准 1（续）：响应时间不超过 500ms"""

    async def test_single_create_under_500ms(self, http_client):
        start = time.monotonic()
        await http_client.post("/alert-rules", json={
            "name": "perf-single",
            "rule_type": "agent_timeout",
            "threshold": 10.0,
        })
        elapsed_ms = (time.monotonic() - start) * 1000
        assert elapsed_ms <= 500, f"单次创建耗时 {elapsed_ms:.1f}ms 超过 500ms"

    async def test_batch_10_creates_each_under_500ms(self, http_client):
        for i in range(10):
            start = time.monotonic()
            resp = await http_client.post("/alert-rules", json={
                "name": f"perf-batch-{i}",
                "rule_type": "resource_exceed",
                "threshold": float(i + 1),
            })
            elapsed_ms = (time.monotonic() - start) * 1000
            assert resp.status_code == 201
            assert elapsed_ms <= 500, f"第 {i} 条耗时 {elapsed_ms:.1f}ms 超过 500ms"


class TestAlertRulePersistence:
    """验收标准 2：规则保存成功"""

    async def test_saved_rule_retrievable_by_id(self, http_client):
        payload = {
            "name": "persistence-test",
            "rule_type": "consecutive_failure",
            "threshold": 3.0,
        }
        resp = await http_client.post("/alert-rules", json=payload)
        body = resp.json()
        rule_id = body["id"]

        rule = repo.find_by_id(rule_id)
        assert rule is not None
        assert rule.name == "persistence-test"
        assert rule.rule_type == "consecutive_failure"
        assert rule.threshold == 3.0

    async def test_saved_rule_has_timestamps(self, http_client):
        resp = await http_client.post("/alert-rules", json={
            "name": "timestamp-test",
            "rule_type": "agent_timeout",
            "threshold": 15.0,
        })
        body = resp.json()
        assert body["created_at"] is not None
        assert body["updated_at"] is not None

    async def test_default_values_applied_on_save(self, http_client):
        payload = {
            "name": "defaults-test",
            "rule_type": "resource_exceed",
            "threshold": 80.0,
        }
        resp = await http_client.post("/alert-rules", json=payload)
        body = resp.json()
        assert body["duration_seconds"] == 300
        assert body["enabled"] is True
        assert body["description"] is None


class TestAlertRuleList:
    """验收标准 3：规则列表中新增一条告警规则"""

    async def test_list_grows_by_one_after_create(self, http_client):
        before = await http_client.get("/alert-rules")
        before_count = len(before.json())

        await http_client.post("/alert-rules", json={
            "name": "new-entry",
            "rule_type": "agent_timeout",
            "threshold": 20.0,
        })

        after = await http_client.get("/alert-rules")
        after_count = len(after.json())
        assert after_count == before_count + 1

    async def test_new_rule_appears_in_list(self, http_client):
        unique_name = f"unique-rule-{uuid.uuid4().hex[:8]}"
        await http_client.post("/alert-rules", json={
            "name": unique_name,
            "rule_type": "resource_exceed",
            "threshold": 90.0,
        })
        resp = await http_client.get("/alert-rules")
        names = [r["name"] for r in resp.json()]
        assert unique_name in names

    async def test_multiple_rules_in_list(self, http_client):
        for i in range(5):
            await http_client.post("/alert-rules", json={
                "name": f"multi-{i}",
                "rule_type": "agent_timeout",
                "threshold": float(i + 1),
            })
        resp = await http_client.get("/alert-rules")
        assert len(resp.json()) == 5


class TestAlertRuleConcurrentLimit:
    """验收标准 4：支持同时生效不少于 50 条规则"""

    async def test_create_55_rules_all_active(self, http_client):
        rule_types = ["agent_timeout", "consecutive_failure", "resource_exceed"]
        for i in range(55):
            resp = await http_client.post("/alert-rules", json={
                "name": f"bulk-{i}",
                "rule_type": rule_types[i % 3],
                "threshold": float(i + 1),
                "enabled": True,
            })
            assert resp.status_code == 201

        resp = await http_client.get("/alert-rules")
        all_rules = resp.json()
        assert len(all_rules) == 55

        enabled = [r for r in all_rules if r["enabled"]]
        assert len(enabled) >= 50

    async def test_repository_counts_enabled_correctly(self, http_client):
        for i in range(60):
            await http_client.post("/alert-rules", json={
                "name": f"count-test-{i}",
                "rule_type": "agent_timeout",
                "threshold": float(i),
                "enabled": i % 3 != 0,
            })
        assert repo.count_enabled() >= 40

    async def test_mixed_enabled_disabled_still_meets_threshold(self, http_client):
        for i in range(70):
            enabled = i < 55
            await http_client.post("/alert-rules", json={
                "name": f"mixed-{i}",
                "rule_type": "resource_exceed",
                "threshold": 50.0,
                "enabled": enabled,
            })
        assert repo.count_enabled() >= 50


if __name__ == "__main__":
    pytest.main([__file__, "-v"])
