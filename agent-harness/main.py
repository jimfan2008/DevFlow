from contextlib import asynccontextmanager
from fastapi import FastAPI
from backend.agent_registry.api import router as agent_router
from backend.agent_registry.service import RegistryService
from backend.observability.telemetry import setup_telemetry
from backend.shared.config import config


@asynccontextmanager
async def lifespan(app: FastAPI):
    setup_telemetry()
    svc = RegistryService(config.database_url)
    await svc.initialize()
    app.state.registry_service = svc
    yield
    await svc.close()


def create_app(db_url: str = config.database_url):
    app = FastAPI(title="Agent Harness", lifespan=lifespan)
    app.state.config = config
    app.include_router(agent_router)
    return app


app = create_app()
