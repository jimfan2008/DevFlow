### Task 1: Project Scaffolding + Agent Data Models

**Files:**
- Create: `backend/__init__.py`
- Create: `backend/shared/__init__.py`
- Create: `backend/shared/config.py`
- Create: `backend/shared/types.py`
- Create: `backend/agent_registry/__init__.py`
- Create: `backend/agent_registry/models.py`
- Create: `tests/__init__.py`
- Create: `tests/conftest.py`
- Create: `tests/agent_registry/__init__.py`
- Create: `tests/agent_registry/test_models.py`
- Create: `pyproject.toml`
- Create: `.env.example`

**Interfaces:**
- Consumes: Nothing (first task)
- Produces: `AgentStatus` enum, `AgentCard` model, `HealthStatus` model, `Config` dataclass

- [ ] **Step 1: Create pyproject.toml with project metadata and dependencies**

```toml
[project]
name = "agent-harness"
version = "0.1.0"
requires-python = ">=3.12"
dependencies = [
    "fastapi>=0.115.0",
    "uvicorn[standard]>=0.32.0",
    "pydantic>=2.10.0",
    "pydantic-settings>=2.6.0",
    "temporalio>=1.8.0",
    "opentelemetry-api>=1.28.0",
    "opentelemetry-sdk>=1.28.0",
    "opentelemetry-instrumentation-fastapi>=0.49b0",
    "httpx>=0.28.0",
    "structlog>=24.4.0",
    "aiosqlite>=0.20.0",
]

[project.optional-dependencies]
dev = [
    "pytest>=8.3.0",
    "pytest-asyncio>=0.24.0",
    "pytest-httpx>=0.35.0",
    "pytest-cov>=6.0.0",
]

[tool.pytest.ini_options]
asyncio_mode = "auto"
testpaths = ["tests"]
```

- [ ] **Step 2: Write the failing model tests**

```python
# tests/agent_registry/test_models.py
import pytest
from pydantic import ValidationError
from backend.agent_registry.models import AgentStatus, AgentCard, HealthStatus


class TestAgentStatus:
    def test_enum_values(self):
        assert AgentStatus.ACTIVE.value == "active"
        assert AgentStatus.INACTIVE.value == "inactive"
        assert AgentStatus.DEGRADED.value == "degraded"
        assert AgentStatus.ERROR.value == "error"


class TestAgentCard:
    def test_valid_agent_card(self):
        card = AgentCard(
            agent_id="test-agent-1",
            name="test-agent",
            version="1.0.0",
            capabilities=["search", "parse"],
            auth_spiffe_id="spiffe://prod/test/agent",
            endpoints={"a2a": "a2a://registry/test/agent"},
            status=AgentStatus.ACTIVE,
        )
        assert card.agent_id == "test-agent-1"
        assert card.status == AgentStatus.ACTIVE

    def test_agent_card_missing_required_fields(self):
        with pytest.raises(ValidationError):
            AgentCard()

    def test_agent_card_invalid_endpoints(self):
        with pytest.raises(ValidationError):
            AgentCard(
                agent_id="test",
                name="test",
                version="1.0.0",
                capabilities=[],
                endpoints="not-a-dict",
            )


class TestHealthStatus:
    def test_valid_health_status(self):
        hs = HealthStatus(
            agent_id="test-1",
            status=AgentStatus.ACTIVE,
            last_heartbeat="2026-06-22T00:00:00Z",
            metrics={"cpu": 0.5, "memory": 128},
        )
        assert hs.agent_id == "test-1"

    def test_health_status_defaults(self):
        hs = HealthStatus(agent_id="test-2", status=AgentStatus.ACTIVE)
        assert hs.last_heartbeat is not None
        assert hs.metrics == {}
```

- [ ] **Step 3: Run tests to verify they fail**

Run: `uv run pytest tests/agent_registry/test_models.py -v`
Expected: FAIL with `ModuleNotFoundError` for `backend`

- [ ] **Step 4: Write the models implementation**

```python
# backend/shared/__init__.py
```

```python
# backend/shared/config.py
from pydantic_settings import BaseSettings


class Config(BaseSettings):
    database_url: str = "sqlite+aiosqlite:///./agent_harness.db"
    temporal_host: str = "localhost:7233"
    spire_socket_path: str = "/tmp/spire-agent/api.sock"
    opa_url: str = "http://localhost:8181"
    otel_service_name: str = "agent-harness"
    otel_endpoint: str = "http://localhost:4318"
    log_level: str = "INFO"

    model_config = {"env_prefix": "AH_", "env_file": ".env"}


config = Config()
```

```python
# backend/shared/types.py
from typing import TypeAlias
from datetime import datetime

AgentID: TypeAlias = str
WorkflowID: TypeAlias = str
SPIFFEID: TypeAlias = str
Timestamp: TypeAlias = datetime
```

```python
# backend/agent_registry/__init__.py
from backend.agent_registry.models import AgentStatus, AgentCard, HealthStatus

__all__ = ["AgentStatus", "AgentCard", "HealthStatus"]
```

```python
# backend/agent_registry/models.py
from datetime import datetime, timezone
from enum import Enum
from typing import Optional
from pydantic import BaseModel, Field


class AgentStatus(str, Enum):
    ACTIVE = "active"
    INACTIVE = "inactive"
    DEGRADED = "degraded"
    ERROR = "error"


class AgentCard(BaseModel):
    agent_id: str
    name: str
    version: str
    description: Optional[str] = None
    capabilities: list[str] = Field(default_factory=list)
    auth_spiffe_id: Optional[str] = None
    endpoints: dict[str, str] = Field(default_factory=dict)
    status: AgentStatus = AgentStatus.INACTIVE
    metadata: dict[str, str] = Field(default_factory=dict)
    registered_at: datetime = Field(default_factory=lambda: datetime.now(timezone.utc))
    updated_at: datetime = Field(default_factory=lambda: datetime.now(timezone.utc))


class HealthStatus(BaseModel):
    agent_id: str
    status: AgentStatus
    last_heartbeat: str = Field(
        default_factory=lambda: datetime.now(timezone.utc).isoformat()
    )
    message: Optional[str] = None
    metrics: dict[str, float] = Field(default_factory=dict)
```

```python
# backend/__init__.py
```

- [ ] **Step 5: Run tests to verify they pass**

Run: `uv run pytest tests/agent_registry/test_models.py -v`
Expected: PASS

- [ ] **Step 6: Create .env.example and __init__ files**

```bash
# .env.example
AH_DATABASE_URL=sqlite+aiosqlite:///./agent_harness.db
AH_TEMPORAL_HOST=localhost:7233
AH_SPIRE_SOCKET_PATH=/tmp/spire-agent/api.sock
AH_OPA_URL=http://localhost:8181
AH_OTEL_SERVICE_NAME=agent-harness
AH_OTEL_ENDPOINT=http://localhost:4318
AH_LOG_LEVEL=INFO
```

```bash
# Create empty __init__ files
touch tests/__init__.py
touch tests/agent_registry/__init__.py
```

- [ ] **Step 7: Commit**

```bash
git add -A
git commit -m "feat: project scaffolding + Agent models (AgentCard, HealthStatus, AgentStatus)"
```

---

