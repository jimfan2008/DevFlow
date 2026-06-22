from contextlib import asynccontextmanager
from fastapi import FastAPI
from backend.agent_registry.api import router as agent_router
from backend.agent_registry.service import RegistryService


@asynccontextmanager
async def lifespan(app: FastAPI):
    svc = RegistryService(app.state.db_url)
    await svc.initialize()
    app.state.registry_service = svc
    yield
    await svc.close()


def create_app(db_url: str = "sqlite+aiosqlite:///./agent_harness.db"):
    app = FastAPI(title="Agent Harness", lifespan=lifespan)
    app.state.db_url = db_url
    app.include_router(agent_router)
    return app


app = create_app()
