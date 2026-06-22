# REASONIX.md — DevFlow

## Stack

- **Backend**: Python 3.12+, FastAPI (0.109), SQLAlchemy 2.0 ORM, Alembic migrations
- **Frontend**: Vue 3.4 (Composition API), Pinia stores, Vue Router, Element Plus UI
- **Async**: Celery + Redis broker, WebSocket pub/sub (step progress broadcasting)
- **AI**: Hermes Gateway API for LLM calls (project-isolated via `chat_isolated`), 10 named Agent profiles
- **Test**: pytest 7+, pytest-asyncio (auto mode), pytest-cov, httpx AsyncClient

## Layout

| Path | Contents |
|------|----------|
| `backend/app/` | FastAPI app: `api/` (routers), `models/` (SQLAlchemy), `services/` (WorkflowEngine, GatewayClient, Hermes), `tasks/` (Celery), `ws/` (WebSocket broadcast), `middleware/`, `caches/` |
| `backend/tests/` | pytest tests, conftest.py with fixtures + factories, test data under `data/fixtures/` |
| `frontend/src/` | Vue 3: `views/`, `components/`, `stores/`, `router/`, `api/`, `composables/`, `utils/` |
| `docs/` | SRS docs, architecture designs, deployment guides |
| `docker/` | Docker configs: nginx, postgres, redis, init scripts |
| `projects/` | Generated project outputs (per-project subdirs) |

## Commands

| Action | Backend | Frontend |
|--------|---------|----------|
| dev server | `make dev` (uvicorn reload) | `npm run dev` (vite) |
| test | `make test` (pytest --cov) | `npm run test` (vitest) |
| lint | `make lint` (ruff check) | `npm run lint` (eslint) |
| format | `make format` (ruff format) | `npm run format` (prettier) |
| docker | `make docker-{build,up,down}` | — |

## Conventions

- **Ruff**: line-length 88, double quotes, isort (I), flake8-bugbear (B), E501 ignored
- **Pytest**: `asyncio_mode = auto`; test files `backend/tests/test_*.py`; DB fixtures via `SessionLocal()` in conftest
- **Backend naming**: `snake_case` modules, `PascalCase` models, `camelCase` for config keys
- **API routers**: each domain gets `backend/app/api/{name}.py` with `router = APIRouter()`, registered in `api/__init__.py`
- **16-step workflow**: each step has a file `backend/app/api/workflow/step{N}.py`, a row in `workflow_steps` table, and optionally an executor registered in `services/haimei_auto_execute.py`
- **Error handling**: domain exceptions in `core/exceptions.py` caught by `middleware/error_handler.py`

## Rules (non-negotiable)

- **Backup before edit**: Before modifying ANY file, `cp` a `.bak` copy (append `.bak.YYYYMMDD_HHMMSS`) in the same directory. If the file is outside the project (e.g. `~/.hermes/`), copy to a known backup location first. Never overwrite without a recoverable snapshot.

## Watch out for

- **WorkflowEngine pass_qa gap**: `complete_step()` sets QA-required steps to `qa_review` (not `completed`). Manual API paths call `pass_qa()` separately. Auto-executor (`haimei_auto_execute.py`) must call `pass_qa()` after `complete_step()` — missing one stalls the pipeline.
- **GatewayClient prerequisites**: All LLM calls go through `GatewayClient.chat_isolated()`. Requires Hermes Gateway running with per-profile config (`~/.hermes/profiles/{houwang,hourong,haimei,etc}/config.yaml`) or `HERMES_API_BASE` env var. No graceful offline mode.
- **Auto-executor silent drops**: `haimei_auto_execute.py` uses `asyncio.gather(return_exceptions=True)` + `isinstance(r, dict)` filter. Sub-flow exceptions (profile not found, gateway timeout) are silently dropped unless explicitly logged.
- **DB session sharing**: `haimei_auto_advance()` passes `self.db` to `auto_dispatch_step()`, which creates a nested `WorkflowEngine` with the same session. Mutations from the background task affect the parent session.
- **Frontend build output**: `frontend/dist/` is gitignored; served by Nginx in Docker.
