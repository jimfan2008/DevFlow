#!/usr/bin/env python3
"""
DevFlow 前端 - 测试配置和工具
"""

import pytest
import pytest_asyncio
from httpx import AsyncClient
import asyncio


@pytest.fixture(scope="session")
def event_loop():
    """创建事件循环"""
    loop = asyncio.get_event_loop_policy().new_event_loop()
    yield loop
    loop.close()


@pytest_asyncio.fixture(scope="function")
async def frontend_client():
    """创建前端测试客户端"""
    async with AsyncClient(app=None, base_url="http://localhost:3000") as ac:
        yield ac
