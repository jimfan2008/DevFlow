"""Initialize database tables."""
import asyncio
from app.database import engine, Base
import app.models  # noqa: F401


async def init():
    async with engine.begin() as conn:
        await conn.run_sync(Base.metadata.create_all)
    print("Tables created successfully")
    await engine.dispose()


asyncio.run(init())
