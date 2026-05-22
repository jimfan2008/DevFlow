#!/usr/bin/env python3
"""
DevFlow 项目管理平台 - FastAPI 应用入口
"""

from contextlib import asynccontextmanager
from fastapi import FastAPI
from fastapi.middleware.cors import CORSMiddleware
from app.api import main_router
from app.config import settings
from app.middleware.logging import LoggingMiddleware
from app.middleware.error_handler import register_error_handlers
import logging

logging.basicConfig(level=logging.INFO)
logger = logging.getLogger("devflow")


@asynccontextmanager
async def lifespan(app: FastAPI):
    logger.info(f"Starting {settings.APP_NAME} v{settings.APP_VERSION}")
    yield
    logger.info(f"Shutting down {settings.APP_NAME}")


app = FastAPI(
    title=settings.APP_NAME,
    description="项目管理平台 API",
    version=settings.APP_VERSION,
    docs_url="/docs",
    redoc_url="/redoc",
    redirect_slashes=False,
    lifespan=lifespan,
)

app.add_middleware(
    CORSMiddleware,
    allow_origins=[settings.FRONTEND_URL, "http://localhost:5173", "http://localhost", "http://127.0.0.1", "http://127.0.0.1:5173"],
    allow_credentials=True,
    allow_methods=["*"],
    allow_headers=["*"],
)

app.add_middleware(LoggingMiddleware)

register_error_handlers(app)

app.include_router(main_router)


@app.get("/", tags=["health"])
def root():
    return {"message": "DevFlow API is running", "version": settings.APP_VERSION}


@app.get("/health", tags=["health"])
def health_check():
    return {"status": "healthy"}


if __name__ == "__main__":
    import uvicorn
    uvicorn.run("app.main:app", host="0.0.0.0", port=8000, reload=settings.DEBUG)
