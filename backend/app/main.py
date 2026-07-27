#!/usr/bin/env python3
"""
DevFlow 项目管理平台 - FastAPI 应用入口
v4.0 - 增强启动：自动发现 Hermes Agent、初始化数据库、启动健康检查
"""

import asyncio
import os
from contextlib import asynccontextmanager
from fastapi import FastAPI
from fastapi.middleware.cors import CORSMiddleware
from app.api import main_router
from app.config import settings
from app.middleware.logging import LoggingMiddleware
from app.middleware.error_handler import register_error_handlers
from app.database import sync_engine, Base
from sqlalchemy import text
from app.services.hermes.hermes_api_client import HermesAPIClient
from app.services.hermes.hermes_health import HermesHealthChecker
import logging

logging.basicConfig(level=logging.INFO)
logger = logging.getLogger("devflow")

# ── 全局服务实例 ──────────────────────────────────────────
hermes_api_client: HermesAPIClient | None = None
hermes_health_checker: HermesHealthChecker | None = None


def _init_database():
    """启动时自动创建数据库表（仅 SQLite 开发模式）。"""
    url = settings.DATABASE_URL
    if url.startswith("sqlite"):
        logger.info("初始化数据库表...")
        Base.metadata.create_all(bind=sync_engine)
        logger.info("数据库表初始化完成")
    else:
        logger.info("生产模式（PostgreSQL），依赖 Alembic 迁移")


def _discover_hermes_agents():
    """扫描本地 Hermes 安装并注册到 Agent 表。"""
    try:
        from app.services.hermes_discovery import autodetect_and_register
        from app.database import SessionLocal

        db = SessionLocal()
        try:
            logger.info("正在自动发现 Hermes Agent...")
            result = autodetect_and_register(db, auto_configure=False)
            found = result.get("instances_found", 0)
            for action in result.get("actions", []):
                logger.info(f"  Hermes: {action}")
            for warn in result.get("warnings", []):
                logger.warning(f"  {warn}")
            logger.info(f"Hermes Agent 发现完成: {found} 个实例")
        finally:
            db.close()
    except Exception as e:
        logger.warning(f"Hermes Agent 自动发现失败（可忽略）: {e}")


def _seed_named_agents():
    """如果不存在，创建 DevFlow 10 大命名 Agent 角色。"""
    try:
        from app.database import SessionLocal
        from app.models.agent import Agent

        named_roles = [
            ("haimei", "海梅", "project_manager", "项目经理"),
            ("houxing", "后兴", "requirement_analyst", "需求分析师"),
            ("houwang", "后旺", "architect", "架构师"),
            ("houfa", "后发", "programmer", "程序员"),
            ("houda", "后达", "tester", "测试员"),
            ("houfu", "后富", "cicd_engineer", "CI/CD工程师"),
            ("hougui", "后贵", "doc_manager", "文档管理员"),
            ("hourong", "后荣", "qa", "QA质检员"),
            ("houhua", "后华", "security_officer", "安全审计员"),
        ]
        db = SessionLocal()
        try:
            for name, chinese_name, role_type, chinese_role in named_roles:
                existing = db.query(Agent).filter(
                    Agent.name == name, Agent.is_named_role == True
                ).first()
                if not existing:
                    agent = Agent(
                        name=name,
                        agent_type="hermes",
                        status="offline",
                        role_name=role_type,
                        chinese_name=chinese_name,
                        is_named_role=True,
                        discovered_by="profile_scan",
                    )
                    db.add(agent)
                    logger.info(f"  创建命名 Agent: {name} ({chinese_name})")
            db.commit()
        except Exception:
            db.rollback()
            for name, chinese_name, role_type, chinese_role in named_roles:
                existing = db.query(Agent).filter(
                    Agent.name == name, Agent.is_named_role == True
                ).first()
                if not existing:
                    db.execute(
                        text("INSERT OR IGNORE INTO agents (name, agent_type, status, role_name, chinese_name, is_named_role, discovered_by) VALUES (:name, 'hermes', 'offline', :role, :cn, 1, 'profile_scan')"),
                        {"name": name, "role": role_type, "cn": chinese_name}
                    )
                    logger.info(f"  创建命名 Agent: {name} ({chinese_name})")
            db.commit()
        finally:
            db.close()
    except Exception as e:
        logger.warning(f"命名 Agent 初始化失败: {e}")


async def _start_hermes_health_checker():
    """启动 Hermes 健康检查后台任务。"""
    global hermes_api_client, hermes_health_checker
    try:
        hermes_api_client = HermesAPIClient(
            base_url=settings.HERMES_API_BASE,
            api_key=settings.HERMES_API_KEY,
            model=settings.HERMES_MODEL,
        )
        hermes_health_checker = HermesHealthChecker(
            api_client=hermes_api_client,
            interval=settings.HERMES_HEALTH_INTERVAL,
        )
        # 立即执行一次健康检查并设置初始状态
        status = await hermes_health_checker.check_once()
        hermes_health_checker._status = status
        logger.info(f"Hermes Agent 健康状态: {status}")
        await hermes_health_checker.start()
    except Exception as e:
        logger.warning(f"Hermes 健康检查启动失败: {e}")


async def _stop_hermes_health_checker():
    global hermes_health_checker
    if hermes_health_checker:
        await hermes_health_checker.stop()
    if hermes_api_client:
        await hermes_api_client.close()



@asynccontextmanager
async def lifespan(app: FastAPI):
    logger.info(f"Starting {settings.APP_NAME} v{settings.APP_VERSION}")
    logger.info(f"Hermes API: {settings.HERMES_API_BASE}")

    # 1. 初始化数据库
    _init_database()

    # 2. 创建命名 Agent 角色
    _seed_named_agents()

    # 3. 自动发现本地 Hermes 安装
    _discover_hermes_agents()

    # 4. 启动 Hermes 健康检查
    await _start_hermes_health_checker()

    yield

    # ── 关闭 ──
    await _stop_hermes_health_checker()
    logger.info(f"Shutting down {settings.APP_NAME}")


app = FastAPI(
    title=settings.APP_NAME,
    description="DevFlow v4.0 - AI Agent 全自动软件开发项目管理平台",
    version=settings.APP_VERSION,
    docs_url="/docs",
    redoc_url="/redoc",
    redirect_slashes=False,
    lifespan=lifespan,
)

app.add_middleware(
    CORSMiddleware,
    allow_origins=[
        settings.FRONTEND_URL,
        "http://localhost:3000",
        "http://localhost:5173",
        "http://localhost",
        "http://127.0.0.1",
        "http://127.0.0.1:5173",
        "http://127.0.0.1:3000",
    ],
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


@app.get("/api/v1/discover", tags=["hermes"])
def discover_hermes():
    """手动触发 Hermes Agent 重新发现。"""
    _discover_hermes_agents()
    return {"message": "Hermes discovery triggered"}


@app.get("/api/v1/hermes/status", tags=["hermes"])
async def hermes_status():
    """获取 Hermes Agent 当前连接状态。"""
    global hermes_health_checker
    if hermes_health_checker:
        status = hermes_health_checker.status
        diagnostic = hermes_health_checker.get_diagnostic_info()
        return {"status": status, "diagnostic": diagnostic}
    return {"status": "not_started"}


if __name__ == "__main__":
    import uvicorn
    uvicorn.run("app.main:app", host="0.0.0.0", port=8000, reload=settings.DEBUG)
