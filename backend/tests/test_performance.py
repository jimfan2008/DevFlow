#!/usr/bin/env python3
"""
DevFlow 项目管理平台 - 性能测试

涵盖：
1. API 响应时间测试
2. 数据库查询性能测试
3. 并发请求压力测试
"""

import pytest
import pytest_asyncio
import asyncio
import time
import statistics
import sys
import os
from concurrent.futures import ThreadPoolExecutor
from httpx import AsyncClient, ASGITransport

sys.path.insert(0, os.path.dirname(os.path.dirname(os.path.abspath(__file__))))

from app.main import app
from app.database import get_db, engine, Base
from app.models.user import User
from app.models.board import Board
from app.models.project import Project
from app.models.task import Task
from app.models.dependency import TaskDependency
from sqlalchemy import create_engine
from sqlalchemy.orm import sessionmaker


# ── 共享测试引擎/session（避免每次重复创建） ─────────────────
@pytest.fixture(scope="session")
def shared_test_engine():
    """session 级共享测试引擎"""
    eng = create_engine("sqlite:///./test_perf_devflow.db")
    Base.metadata.create_all(bind=eng)
    yield eng
    Base.metadata.drop_all(bind=eng)
    eng.dispose()


@pytest_asyncio.fixture(scope="function")
def perf_db_session(shared_test_engine):
    """function 级独立事务 session"""
    SessionLocal = sessionmaker(autocommit=False, autoflush=False, bind=shared_test_engine)
    session = SessionLocal()
    try:
        yield session
    finally:
        session.close()


@pytest_asyncio.fixture(scope="function")
async def perf_client(perf_db_session):
    """创建性能测试客户端"""
    def override_get_db():
        try:
            yield perf_db_session
        finally:
            pass

    app.dependency_overrides[get_db] = override_get_db
    async with AsyncClient(
        transport=ASGITransport(app=app),
        base_url="http://test",
    ) as ac:
        yield ac
    app.dependency_overrides.clear()


# ── 辅助：注册并登录获取 token ──────────────────────────────────
async def _register_and_login(client, username="perf_user", password="perf123456"):
    """快捷注册+登录，返回 token"""
    await client.post("/api/auth/register", json={
        "username": username,
        "email": f"{username}@perf.com",
        "password": password,
    })
    resp = await client.post("/api/auth/login", json={
        "username": username,
        "password": password,
    })
    data = resp.json()
    tokens = data.get("data", {}).get("tokens", {})
    return tokens.get("access_token", ""), resp.status_code


# ═══════════════════════════════════════════════════════════════
# 1. API 响应时间测试
# ═══════════════════════════════════════════════════════════════

class TestAPIResponseTime:
    """测试各个 API 端点的响应时间"""

    def test_health_endpoint_response_time(self, perf_client):
        """健康检查端点响应时间 < 50ms"""
        start = time.perf_counter()
        resp = perf_client.get("/health")
        latency = time.perf_counter() - start

        assert resp.status_code == 200
        assert latency < 0.05, f"健康检查响应过慢: {latency*1000:.1f}ms"

    def test_root_endpoint_response_time(self, perf_client):
        """根端点响应时间 < 50ms"""
        start = time.perf_counter()
        resp = perf_client.get("/")
        latency = time.perf_counter() - start

        assert resp.status_code == 200
        assert latency < 0.05, f"根端点响应过慢: {latency*1000:.1f}ms"

    @pytest_asyncio.fixture(scope="function")
    async def logged_in_client(self, perf_db_session, perf_client):
        """已登录的测试客户端"""
        _, code = await _register_and_login(perf_client)
        assert code == 200, "注册或登录失败"
        return perf_client

    @pytest.mark.asyncio
    async def test_register_response_time(self, perf_client):
        """注册接口响应时间 < 500ms（含 bcrypt 哈希）"""
        start = time.perf_counter()
        resp = await perf_client.post("/api/auth/register", json={
            "username": "perf_reg_user",
            "email": "perf_reg@perf.com",
            "password": "perf123456",
        })
        latency = time.perf_counter() - start

        assert resp.status_code == 200
        assert latency < 0.5, f"注册响应过慢: {latency*1000:.1f}ms"

    @pytest.mark.asyncio
    async def test_login_response_time(self, perf_client):
        """登录接口响应时间 < 500ms"""
        # 先注册
        await perf_client.post("/api/auth/register", json={
            "username": "perf_login_user",
            "email": "perf_login@perf.com",
            "password": "perf123456",
        })
        # 再登录
        start = time.perf_counter()
        resp = await perf_client.post("/api/auth/login", json={
            "username": "perf_login_user",
            "password": "perf123456",
        })
        latency = time.perf_counter() - start

        assert resp.status_code == 200
        assert latency < 0.5, f"登录响应过慢: {latency*1000:.1f}ms"

    @pytest.mark.asyncio
    async def test_me_endpoint_response_time(self, logged_in_client):
        """获取当前用户接口响应时间 < 200ms"""
        start = time.perf_counter()
        resp = await logged_in_client.get("/api/auth/me")
        latency = time.perf_counter() - start

        assert resp.status_code == 200
        assert latency < 0.2, f"获取用户信息响应过慢: {latency*1000:.1f}ms"

    @pytest.mark.asyncio
    async def test_multiple_endpoints_response_time(self, perf_db_session, perf_client):
        """多个端点批量响应时间测试"""
        endpoints = [
            ("GET", "/health"),
            ("GET", "/"),
        ]
        all_latencies = []

        for method, path in endpoints:
            start = time.perf_counter()
            if method == "GET":
                resp = perf_client.get(path)
            else:
                resp = perf_client.post(path)
            latency = time.perf_counter() - start
            all_latencies.append(latency)

        avg = statistics.mean(all_latencies)
        assert avg < 0.1, f"端点平均响应过慢: {avg*1000:.1f}ms"

    @pytest.mark.asyncio
    async def test_p95_response_time(self, perf_db_session, perf_client):
        """P95 响应时间 < 300ms（多次采样）"""
        latencies = []
        num_runs = 10

        for _ in range(num_runs):
            start = time.perf_counter()
            perf_client.get("/health")
            latency = time.perf_counter() - start
            latencies.append(latency * 1000)  # 转为 ms

        latencies.sort()
        p95_idx = int(num_runs * 0.95)
        p95 = latencies[p95_idx]

        assert p95 < 300, f"P95 响应时间 {p95:.1f}ms 超过阈值 300ms"


# ═══════════════════════════════════════════════════════════════
# 2. 数据库查询性能测试
# ═══════════════════════════════════════════════════════════════

class TestDatabaseQueryPerformance:
    """测试数据库查询性能"""

    def _create_test_data(self, session, num_users=10, num_boards=5, num_tasks_per_board=20):
        """批量创建测试数据"""
        from app.utils.security import hash_password
        from datetime import datetime

        # 批量创建用户
        users = []
        for i in range(num_users):
            user = User(
                id=f"perf_user_{i}",
                username=f"perf_user_{i}",
                email=f"perf_user_{i}@perf.com",
                password_hash=hash_password("perf123456"),
                role="member",
            )
            users.append(user)
        session.add_all(users)
        session.flush()

        # 批量创建项目和看板
        projects = []
        for i in range(min(num_users, 3)):
            project = Project(
                id=f"perf_project_{i}",
                name=f"测试项目{i}",
                slug=f"perf-project-{i}",
                description="性能测试项目",
                creator_id=users[i].id,
            )
            projects.append(project)
        session.add_all(projects)
        session.flush()

        boards = []
        for j in range(num_boards):
            board = Board(
                id=f"perf_board_{j}",
                project_id=projects[j % len(projects)].id,
                name=f"测试看板{j}",
                slug=f"perf-board-{j}",
                position=j,
                color="#3b82f6",
            )
            boards.append(board)
        session.add_all(boards)
        session.flush()

        # 批量创建任务
        tasks = []
        for board in boards:
            for k in range(num_tasks_per_board):
                task = Task(
                    id=f"perf_task_{board.id}_{k}",
                    title=f"任务 {k}",
                    description=f"描述 {k}",
                    board_id=board.id,
                    status="todo",
                    priority="medium",
                    assignee_id=users[k % len(users)].id,
                    creator_id=users[k % len(users)].id,
                )
                tasks.append(task)
        session.add_all(tasks)
        session.flush()

        return users, boards, tasks

    @pytest.mark.asyncio
    async def test_bulk_insert_performance(self, perf_db_session, perf_client):
        """批量插入性能：10 用户 + 5 看板 + 100 任务 < 2s"""
        start = time.perf_counter()
        users, boards, tasks = self._create_test_data(
            perf_db_session, num_users=10, num_boards=5, num_tasks_per_board=20
        )
        perf_db_session.commit()
        latency = time.perf_counter() - start

        assert len(users) == 10
        assert len(boards) == 5
        assert len(tasks) == 100
        assert latency < 2.0, f"批量插入耗时 {latency*1000:.1f}ms，超过 2s"

    @pytest.mark.asyncio
    async def test_select_by_id_performance(self, perf_db_session, perf_client):
        """按 ID 查询性能 < 50ms"""
        # 准备数据
        users, _, _ = self._create_test_data(perf_db_session, num_users=5)
        perf_db_session.commit()

        target_user = users[2]
        latencies = []

        for _ in range(5):
            start = time.perf_counter()
            result = perf_db_session.query(User).filter(
                User.id == target_user.id
            ).first()
            latency = time.perf_counter() - start
            latencies.append(latency)
            assert result is not None

        avg = statistics.mean(latencies)
        assert avg < 0.05, f"按ID查询平均耗时 {avg*1000:.1f}ms，超过 50ms"

    @pytest.mark.asyncio
    async def test_list_query_performance(self, perf_db_session, perf_client):
        """列表查询性能（50 条记录）< 200ms"""
        users, boards, tasks = self._create_test_data(
            perf_db_session, num_users=5, num_boards=3, num_tasks_per_board=15
        )
        perf_db_session.commit()

        start = time.perf_counter()
        task_list = perf_db_session.query(Task).all()
        latency = time.perf_counter() - start

        assert len(task_list) == 45  # 3 boards * 15 tasks
        assert latency < 0.2, f"列表查询耗时 {latency*1000:.1f}ms，超过 200ms"

    @pytest.mark.asyncio
    async def test_filtered_query_performance(self, perf_db_session, perf_client):
        """带条件过滤查询 < 100ms"""
        users, boards, tasks = self._create_test_data(
            perf_db_session, num_users=5, num_boards=3, num_tasks_per_board=20
        )
        perf_db_session.commit()

        board_id = boards[0].id
        start = time.perf_counter()
        result = perf_db_session.query(Task).filter(
            Task.board_id == board_id
        ).all()
        latency = time.perf_counter() - start

        assert len(result) == 20
        assert latency < 0.1, f"过滤查询耗时 {latency*1000:.1f}ms，超过 100ms"

    @pytest.mark.asyncio
    async def test_aggregation_query_performance(self, perf_db_session, perf_client):
        """聚合查询（count/group）性能 < 200ms"""
        users, boards, tasks = self._create_test_data(
            perf_db_session, num_users=5, num_boards=3, num_tasks_per_board=30
        )
        perf_db_session.commit()

        start = time.perf_counter()
        from sqlalchemy import func
        task_count = perf_db_session.query(func.count(Task.id)).scalar()
        latency = time.perf_counter() - start

        assert task_count == 90  # 3 boards * 30 tasks
        assert latency < 0.2, f"聚合查询耗时 {latency*1000:.1f}ms，超过 200ms"

    @pytest.mark.asyncio
    async def test_nested_query_performance(self, perf_db_session, perf_client):
        """嵌套查询（board->tasks）性能 < 300ms"""
        users, boards, _ = self._create_test_data(
            perf_db_session, num_users=3, num_boards=3, num_tasks_per_board=10
        )
        perf_db_session.commit()

        board = boards[0]
        start = time.perf_counter()
        tasks = perf_db_session.query(Task).filter(
            Task.board_id == board.id
        ).all()
        latency = time.perf_counter() - start

        assert len(tasks) == 10
        assert latency < 0.3, f"嵌套查询耗时 {latency*1000:.1f}ms，超过 300ms"


# ═══════════════════════════════════════════════════════════════
# 3. 并发请求压力测试
# ═══════════════════════════════════════════════════════════════

class TestConcurrentRequests:
    """并发请求压力测试"""

    @pytest.mark.asyncio
    async def test_concurrent_health_checks(self, perf_db_session, perf_client):
        """并发健康检查：20 个并发请求"""
        num_concurrent = 20
        tasks = []
        start = time.perf_counter()

        async def single_request():
            resp = perf_client.get("/health")
            return resp.status_code

        # 使用 asyncio.gather 模拟并发
        results = await asyncio.gather(*[single_request() for _ in range(num_concurrent)])

        latency = time.perf_counter() - start

        # 所有请求应成功
        assert all(r == 200 for r in results), f"部分请求失败: {results}"
        # 总耗时应合理
        assert latency < 5.0, f"并发健康检查总耗时 {latency:.2f}s，超过 5s"

    @pytest.mark.asyncio
    async def test_concurrent_auth_flow(self, perf_db_session, perf_client):
        """并发认证流程：10 个并发注册请求"""
        num_concurrent = 10
        latencies = []
        start = time.perf_counter()

        async def single_register(idx):
            s = time.perf_counter()
            resp = await perf_client.post("/api/auth/register", json={
                "username": f"concurrent_user_{idx}",
                "email": f"concurrent_{idx}@perf.com",
                "password": "concurrent123",
            })
            elapsed = time.perf_counter() - s
            return resp.status_code, elapsed

        results = await asyncio.gather(*[
            single_register(i) for i in range(num_concurrent)
        ])

        total_latency = time.perf_counter() - start

        success_count = sum(1 for status, _ in results if status == 200)
        assert success_count >= num_concurrent, f"只有 {success_count}/{num_concurrent} 注册成功"
        assert total_latency < 10.0, f"并发注册总耗时 {total_latency:.2f}s，超过 10s"

    @pytest.mark.asyncio
    async def test_concurrent_login(self, perf_db_session, perf_client):
        """并发登录：10 个不同用户同时登录"""
        # 先注册 10 个用户
        for i in range(10):
            resp = await perf_client.post("/api/auth/register", json={
                "username": f"login_user_{i}",
                "email": f"login_{i}@perf.com",
                "password": "login123456",
            })
            assert resp.status_code == 200

        # 并发登录
        start = time.perf_counter()

        async def single_login(idx):
            resp = await perf_client.post("/api/auth/login", json={
                "username": f"login_user_{idx}",
                "password": "login123456",
            })
            return resp.status_code

        results = await asyncio.gather(*[single_login(i) for i in range(10)])

        latency = time.perf_counter() - start

        assert all(r == 200 for r in results), f"部分登录失败: {results}"
        assert latency < 5.0, f"并发登录耗时 {latency:.2f}s，超过 5s"

    @pytest.mark.asyncio
    async def test_concurrent_read_operations(self, perf_db_session, perf_client):
        """并发只读操作：10 个并发查询"""
        # 准备数据
        from app.utils.security import hash_password
        user = User(
            id="perf_concurrent_user",
            username="perf_concurrent_user",
            email="perf_concurrent@perf.com",
            password_hash=hash_password("perf123456"),
            role="member",
        )
        perf_db_session.add(user)
        perf_db_session.commit()

        async def single_read():
            resp = await perf_client.post("/api/auth/login", json={
                "username": "perf_concurrent_user",
                "password": "perf123456",
            })
            return resp.status_code

        start = time.perf_counter()
        results = await asyncio.gather(*[single_read() for _ in range(10)])
        latency = time.perf_counter() - start

        assert all(r == 200 for r in results)
        assert latency < 5.0, f"并发读取耗时 {latency:.2f}s，超过 5s"

    @pytest.mark.asyncio
    async def test_stress_response_time_regression(self, perf_db_session, perf_client):
        """响应时间回归测试：50 次请求 P95 < 300ms"""
        latencies = []
        num_requests = 50

        for _ in range(num_requests):
            start = time.perf_counter()
            resp = perf_client.get("/health")
            latency = time.perf_counter() - start
            latencies.append(latency * 1000)  # ms

        latencies.sort()
        p95_idx = int(num_requests * 0.95)
        p95_ms = latencies[p95_idx]
        avg_ms = statistics.mean(latencies)
        min_ms = min(latencies)
        max_ms = max(latencies)

        assert p95_ms < 300, f"P95 响应时间 {p95_ms:.1f}ms 超过阈值 300ms"
        assert avg_ms < 100, f"平均响应时间 {avg_ms:.1f}ms 超过阈值 100ms"

    @pytest.mark.asyncio
    async def test_rapid_registration_rate(self, perf_db_session, perf_client):
        """连续注册速率测试：每秒至少 2 个注册"""
        num_users = 10
        start = time.perf_counter()

        for i in range(num_users):
            resp = await perf_client.post("/api/auth/register", json={
                "username": f"rate_user_{i}",
                "email": f"rate_{i}@perf.com",
                "password": "rate123456",
            })
            assert resp.status_code == 200, f"第 {i} 个注册失败"

        total_latency = time.perf_counter() - start
        rate = num_users / total_latency if total_latency > 0 else 0

        assert rate >= 1.0, f"注册速率 {rate:.2f}/s，低于 1/s 阈值"
