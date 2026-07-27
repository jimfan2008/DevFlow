import time
import uuid
import asyncio
import pytest
from datetime import datetime, timezone
from typing import Optional

from httpx import ASGITransport, AsyncClient
from fastapi import FastAPI, HTTPException
from pydantic import BaseModel


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


class PresetTemplate(BaseModel):
    template_id: str
    name: str
    rule_type: str
    default_threshold: float
    default_duration_seconds: int
    description: str


PRESET_TEMPLATES = [
    PresetTemplate(
        template_id="agent_timeout",
        name="Agent 超时告警",
        rule_type="agent_timeout",
        default_threshold=30.0,
        default_duration_seconds=300,
        description="当 Agent 执行超时超过阈值时触发告警",
    ),
    PresetTemplate(
        template_id="consecutive_failure",
        name="连续失败告警",
        rule_type="consecutive_failure",
        default_threshold=5.0,
        default_duration_seconds=600,
        description="当连续失败次数超过阈值时触发告警",
    ),
    PresetTemplate(
        template_id="resource_exceed",
        name="资源超限告警",
        rule_type="resource_exceed",
        default_threshold=80.0,
        default_duration_seconds=300,
        description="当资源使用率超过阈值时触发告警",
    ),
]


TEMPLATE_MAP = {t.template_id: t for t in PRESET_TEMPLATES}

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


class PresetTemplate(BaseModel):
    template_id: str
    name: str
    rule_type: str
    default_threshold: float
    default_duration_seconds: int
    description: str


PRESET_TEMPLATES = [
    PresetTemplate(
        template_id="agent_timeout",
        name="Agent 超时告警",
        rule_type="agent_timeout",
        default_threshold=30.0,
        default_duration_seconds=300,
        description="当 Agent 执行超时超过阈值时触发告警",
    ),
    PresetTemplate(
        template_id="consecutive_failure",
        name="连续失败告警",
        rule_type="consecutive_failure",
        default_threshold=5.0,
        default_duration_seconds=600,
        description="当连续失败次数超过阈值时触发告警",
    ),
    PresetTemplate(
        template_id="resource_exceed",
        name="资源超限告警",
        rule_type="resource_exceed",
        default_threshold=80.0,
        default_duration_seconds=300,
        description="当资源使用率超过阈值时触发告警",
    ),
]

TEMPLATE_MAP = {t.template_id: t for t in PRESET_TEMPLATES}


class AlertRuleRepository:
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


app = FastAPI(title="AlertRule Preset API")
repo = AlertRuleRepository()


@app.get("/preset-templates")
async def list_preset_templates():
    return [t.model_dump() for t in PRESET_TEMPLATES]


@app.post("/preset-templates/{template_id}/enable", status_code=201)
async def enable_preset_template(template_id: str):
    template = TEMPLATE_MAP.get(template_id)
    if template is None:
        raise HTTPException(status_code=404, detail="Template not found")
    rule_input = AlertRuleInput(
        name=template.name,
        rule_type=template.rule_type,
        threshold=template.default_threshold,
        duration_seconds=template.default_duration_seconds,
        description=template.description,
    )
    rule = repo.insert(rule_input)
    return rule.model_dump()


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


class TestPresetTemplateCount:
    async def test_at_least_three_presets(self):
        assert len(PRESET_TEMPLATES) >= 3

    async def test_includes_agent_timeout(self):
        ids = [t.template_id for t in PRESET_TEMPLATES]
        assert "agent_timeout" in ids

    async def test_includes_consecutive_failure(self):
        ids = [t.template_id for t in PRESET_TEMPLATES]
        assert "consecutive_failure" in ids

    async def test_includes_resource_exceed(self):
        ids = [t.template_id for t in PRESET_TEMPLATES]
        assert "resource_exceed" in ids

    async def test_list_endpoint_returns_all_templates(self, http_client):
        resp = await http_client.get("/preset-templates")
        assert resp.status_code == 200
        data = resp.json()
        assert len(data) >= 3


class TestPresetTemplateEnable:
    async def test_enable_agent_timeout_creates_rule(self, http_client):
        resp = await http_client.post("/preset-templates/agent_timeout/enable")
        assert resp.status_code == 201
        body = resp.json()
        assert body["rule_type"] == "agent_timeout"
        assert body["threshold"] == 30.0
        assert body["name"] == "Agent 超时告警"

    async def test_enable_consecutive_failure_creates_rule(self, http_client):
        resp = await http_client.post("/preset-templates/consecutive_failure/enable")
        assert resp.status_code == 201
        body = resp.json()
        assert body["rule_type"] == "consecutive_failure"
        assert body["threshold"] == 5.0
        assert body["name"] == "连续失败告警"

    async def test_enable_resource_exceed_creates_rule(self, http_client):
        resp = await http_client.post("/preset-templates/resource_exceed/enable")
        assert resp.status_code == 201
        body = resp.json()
        assert body["rule_type"] == "resource_exceed"
        assert body["threshold"] == 80.0
        assert body["name"] == "资源超限告警"

    async def test_enabled_rule_appears_in_alert_rules(self, http_client):
        await http_client.post("/preset-templates/agent_timeout/enable")
        resp = await http_client.get("/alert-rules")
        rules = resp.json()
        assert len(rules) == 1
        assert rules[0]["rule_type"] == "agent_timeout"

    async def test_enable_unknown_template_returns_404(self, http_client):
        resp = await http_client.post("/preset-templates/nonexistent/enable")
        assert resp.status_code == 404

    async def test_enable_generates_unique_rule_id(self, http_client):
        r1 = await http_client.post("/preset-templates/agent_timeout/enable")
        r2 = await http_client.post("/preset-templates/consecutive_failure/enable")
        id1 = r1.json()["id"]
        id2 = r2.json()["id"]
        assert id1 != id2

    async def test_multiple_enable_creates_multiple_rules(self, http_client):
        for tid in ["agent_timeout", "consecutive_failure", "resource_exceed"]:
            await http_client.post(f"/preset-templates/{tid}/enable")
        all_rules = repo.find_all()
        assert len(all_rules) == 3

    async def test_enabled_rule_has_timestamps(self, http_client):
        resp = await http_client.post("/preset-templates/agent_timeout/enable")
        body = resp.json()
        assert body["created_at"] is not None
        assert body["updated_at"] is not None

    async def test_enabled_rule_defaults_enabled_true(self, http_client):
        resp = await http_client.post("/preset-templates/agent_timeout/enable")
        body = resp.json()
        assert body["enabled"] is True

    async def test_enabled_rule_inherits_template_description(self, http_client):
        resp = await http_client.post("/preset-templates/agent_timeout/enable")
        body = resp.json()
        assert "超时" in body["description"]


class TestPresetTemplateResponseTime:
    async def test_list_templates_under_500ms(self, http_client):
        start = time.monotonic()
        await http_client.get("/preset-templates")
        elapsed_ms = (time.monotonic() - start) * 1000
        assert elapsed_ms <= 500, f"获取模板列表耗时 {elapsed_ms:.1f}ms 超过 500ms"

    async def test_enable_template_under_500ms(self, http_client):
        start = time.monotonic()
        await http_client.post("/preset-templates/agent_timeout/enable")
        elapsed_ms = (time.monotonic() - start) * 1000
        assert elapsed_ms <= 500, f"启用模板耗时 {elapsed_ms:.1f}ms 超过 500ms"

    async def test_batch_enable_all_under_500ms(self, http_client):
        for tid in ["agent_timeout", "consecutive_failure", "resource_exceed"]:
            start = time.monotonic()
            resp = await http_client.post(f"/preset-templates/{tid}/enable")
            elapsed_ms = (time.monotonic() - start) * 1000
            assert resp.status_code == 201
            assert elapsed_ms <= 500, f"启用 {tid} 耗时 {elapsed_ms:.1f}ms 超过 500ms"


if __name__ == "__main__":
    pytest.main([__file__, "-v"])
