from contextlib import asynccontextmanager
from fastapi import FastAPI
from fastapi.responses import JSONResponse
from backend.agent_registry.api import router as agent_router
from backend.agent_registry.service import RegistryService
from backend.observability.telemetry import setup_telemetry
from backend.security.middleware import auth_middleware
from backend.shared.config import config


@asynccontextmanager
async def lifespan(app: FastAPI):
    setup_telemetry()
    db_url = getattr(app.state, "db_url", config.database_url)
    svc = RegistryService(db_url)
    await svc.initialize()
    app.state.registry_service = svc
    yield
    await svc.close()


def create_app(db_url: str = config.database_url) -> FastAPI:
    app = FastAPI(title="Agent Harness", lifespan=lifespan)
    app.state.db_url = db_url
    app.state.config = config
    app.include_router(agent_router)
    app.middleware("http")(auth_middleware)

    @app.get("/health")
    async def health() -> JSONResponse:
        return JSONResponse({"status": "ok", "service": "agent-harness"})

    return app


app = create_app()
