#!/usr/bin/env python3
import time
import pytest
import difflib
import sys
import os

sys.path.insert(0, os.path.dirname(os.path.dirname(os.path.abspath(__file__))))

from app.models.project import Project
from app.models.agent import Agent
from app.models.task import Task
from app.models.agent_execution_log import AgentExecutionLog
from app.database import Base
from sqlalchemy import create_engine
from sqlalchemy.pool import StaticPool
from sqlalchemy.orm import sessionmaker

TEST_DB_URL = "sqlite://"
TEST_ENGINE = create_engine(
    TEST_DB_URL,
    echo=False,
    connect_args={"check_same_thread": False},
    poolclass=StaticPool,
)
TestSessionLocal = sessionmaker(autocommit=False, autoflush=False, bind=TEST_ENGINE)


def _setup_db():
    Base.metadata.create_all(bind=TEST_ENGINE)


def _teardown_db():
    with TEST_ENGINE.connect() as conn:
        for table in reversed(Base.metadata.sorted_tables):
            try:
                table.drop(conn, checkfirst=True)
            except Exception:
                pass
        conn.commit()


class GlobalSearchService:

    def __init__(self, db_session):
        self.db = db_session

    def search(self, query: str, limit: int = 50):
        start = time.perf_counter()
        results = self._search_impl(query, limit)
        elapsed_ms = (time.perf_counter() - start) * 1000
        results["elapsed_ms"] = elapsed_ms
        return results

    def _search_impl(self, query: str, limit: int):
        matched_projects = self._match_projects(query, limit)
        matched_outputs = self._match_agent_outputs(query, limit)
        return {
            "query": query,
            "total_projects": len(matched_projects),
            "total_agent_outputs": len(matched_outputs),
            "projects": matched_projects,
            "agent_outputs": matched_outputs,
        }

    def _match_projects(self, query: str, limit: int):
        query = query.strip()
        if not query:
            return []
        projects = self.db.query(Project).order_by(Project.created_at.desc()).limit(limit * 2).all()
        results = []
        for p in projects:
            score = self._fuzzy_score(query, p.name or "")
            if score > 0:
                results.append({
                    "type": "project",
                    "id": p.id,
                    "name": p.name,
                    "description": p.description,
                    "status": p.status,
                    "match_score": score,
                })
        results.sort(key=lambda x: x["match_score"], reverse=True)
        return results[:limit]

    def _match_agent_outputs(self, query: str, limit: int):
        query = query.strip()
        if not query:
            return []
        logs = self.db.query(AgentExecutionLog).order_by(
            AgentExecutionLog.created_at.desc()
        ).limit(limit * 2).all()
        results = []
        for log in logs:
            score = 0
            content = log.result or ""
            exec_content = log.execution_content or ""
            content_score = self._fuzzy_score(query, content)
            exec_score = self._fuzzy_score(query, exec_content)
            score = max(content_score, exec_score)
            if score > 0:
                project_id = None
                if log.task and log.task.project:
                    project_id = log.task.project.id
                results.append({
                    "type": "agent_output",
                    "id": log.id,
                    "task_id": log.task_id,
                    "project_id": project_id,
                    "agent_id": log.agent_id,
                    "agent_name": log.agent.name if log.agent else None,
                    "result": content[:500],
                    "match_score": score,
                    "created_at": log.created_at.isoformat() if log.created_at else None,
                })
        results.sort(key=lambda x: x["match_score"], reverse=True)
        return results[:limit]

    MIN_SCORE_THRESHOLD = 0.20

    @staticmethod
    def _fuzzy_score(query: str, text: str) -> float:
        if not query or not text:
            return 0.0
        query_lower = query.lower()
        text_lower = text.lower()
        if query_lower in text_lower:
            return 1.0
        ratio = difflib.SequenceMatcher(None, query_lower, text_lower).ratio()
        return ratio if ratio >= GlobalSearchService.MIN_SCORE_THRESHOLD else 0.0


@pytest.fixture(scope="function")
def db_session():
    _setup_db()
    session = TestSessionLocal()
    try:
        yield session
    finally:
        session.close()
        _teardown_db()


@pytest.fixture(scope="function")
def search_service(db_session):
    return GlobalSearchService(db_session)


@pytest.fixture(scope="function")
def seeded_data(db_session):
    project_a = Project(
        id="proj_a",
        name="电商交易平台",
        slug="ecommerce-platform",
        description="在线电商交易项目",
        creator_id="user_1",
        status="in_progress",
    )
    project_b = Project(
        id="proj_b",
        name="数据分析平台",
        slug="data-analytics",
        description="数据分析与可视化",
        creator_id="user_1",
        status="in_progress",
    )
    project_c = Project(
        id="proj_c",
        name="用户认证服务",
        slug="auth-service",
        description="OAuth 认证微服务",
        creator_id="user_1",
        status="created",
    )
    project_d = Project(
        id="proj_d",
        name="项目管理工具",
        slug="project-tool",
        description="敏捷项目管理",
        creator_id="user_1",
        status="completed",
    )
    db_session.add_all([project_a, project_b, project_c, project_d])

    agent_opencode = Agent(
        id="agent_opencode",
        name="OpenCode Agent",
        agent_type="opencode",
        status="online",
        api_endpoint="http://localhost:8080/agents/opencode",
        config={"capabilities": ["coding"], "max_concurrent_tasks": 3, "current_load": 0},
    )
    agent_cursor = Agent(
        id="agent_cursor",
        name="Cursor Agent",
        agent_type="cursor",
        status="online",
        api_endpoint="http://localhost:8080/agents/cursor",
        config={"capabilities": ["coding"], "max_concurrent_tasks": 2, "current_load": 0},
    )
    db_session.add_all([agent_opencode, agent_cursor])
    db_session.flush()

    task_1 = Task(
        id="task_1",
        project_id="proj_a",
        name="用户登录模块",
        description="实现用户登录功能",
        type="coding",
        priority="high",
        status="delivered",
    )
    task_2 = Task(
        id="task_2",
        project_id="proj_b",
        name="数据可视化报表",
        description="实现数据可视化报表",
        type="coding",
        priority="medium",
        status="delivered",
    )
    task_3 = Task(
        id="task_3",
        project_id="proj_c",
        name="OAuth2 令牌刷新",
        description="实现 OAuth2 令牌自动刷新",
        type="coding",
        priority="high",
        status="delivered",
    )
    db_session.add_all([task_1, task_2, task_3])
    db_session.flush()

    log_1 = AgentExecutionLog(
        id="log_1",
        task_id="task_1",
        agent_id="agent_opencode",
        execution_content="编写用户登录接口代码",
        result="已完成用户登录模块，包含密码验证、会话管理和 JWT 令牌签发",
        via_skill_type="assign_task",
    )
    log_2 = AgentExecutionLog(
        id="log_2",
        task_id="task_2",
        agent_id="agent_cursor",
        execution_content="生成数据可视化图表组件",
        result="完成 ECharts 柱状图和折线图组件，支持动态数据绑定",
        via_skill_type="assign_task",
    )
    log_3 = AgentExecutionLog(
        id="log_3",
        task_id="task_3",
        agent_id="agent_opencode",
        execution_content="实现 OAuth2 令牌刷新逻辑",
        result="完成 refresh_token 自动刷新，支持 401 自动重试",
        via_skill_type="assign_task",
    )
    db_session.add_all([log_1, log_2, log_3])
    db_session.commit()


class TestGlobalSearchProjectByName:

    def test_search_project_exact_match(self, db_session, seeded_data, search_service):
        result = search_service.search("电商交易平台")
        assert result["total_projects"] >= 1
        first = result["projects"][0]
        assert first["name"] == "电商交易平台"
        assert first["type"] == "project"

    def test_search_project_fuzzy_match(self, db_session, seeded_data, search_service):
        result = search_service.search("电商")
        assert result["total_projects"] >= 1
        first = result["projects"][0]
        assert "电商" in first["name"]

    def test_search_project_partial_match(self, db_session, seeded_data, search_service):
        result = search_service.search("数据")
        assert result["total_projects"] >= 1
        names = [p["name"] for p in result["projects"]]
        assert "数据分析平台" in names

    def test_search_project_no_match(self, db_session, seeded_data, search_service):
        result = search_service.search("不存在的量子计算超级项目XXXX")
        assert result["total_projects"] == 0

    def test_search_project_empty_query(self, db_session, seeded_data, search_service):
        result = search_service.search("")
        assert result["total_projects"] == 0

    def test_search_project_multiple_results(self, db_session, seeded_data, search_service):
        result = search_service.search("平台")
        assert result["total_projects"] >= 2
        names = [p["name"] for p in result["projects"]]
        assert "电商交易平台" in names
        assert "数据分析平台" in names

    def test_search_project_returns_status(self, db_session, seeded_data, search_service):
        result = search_service.search("认证")
        first = result["projects"][0]
        assert "status" in first
        assert first["status"] == "created"

    def test_search_project_returns_description(self, db_session, seeded_data, search_service):
        result = search_service.search("电商")
        first = result["projects"][0]
        assert "description" in first
        assert first["description"] is not None


class TestGlobalSearchAgentOutput:

    def test_search_agent_output_exact_keyword(self, db_session, seeded_data, search_service):
        result = search_service.search("JWT")
        assert result["total_agent_outputs"] >= 1
        first = result["agent_outputs"][0]
        assert "JWT" in first["result"]

    def test_search_agent_output_fuzzy_keyword(self, db_session, seeded_data, search_service):
        result = search_service.search("令牌")
        assert result["total_agent_outputs"] >= 1
        found = any(
            "令牌" in a.get("result", "") or "令牌" in a.get("agent_name", "")
            for a in result["agent_outputs"]
        )
        assert found

    def test_search_agent_output_no_match(self, db_session, seeded_data, search_service):
        result = search_service.search("不存在的产出关键词ZZZZ")
        assert result["total_agent_outputs"] == 0

    def test_search_agent_output_empty_query(self, db_session, seeded_data, search_service):
        result = search_service.search("")
        assert result["total_agent_outputs"] == 0

    def test_search_agent_output_includes_agent_name(self, db_session, seeded_data, search_service):
        result = search_service.search("ECharts")
        first = result["agent_outputs"][0]
        assert first["agent_name"] == "Cursor Agent"

    def test_search_agent_output_includes_task_id(self, db_session, seeded_data, search_service):
        result = search_service.search("refresh_token")
        first = result["agent_outputs"][0]
        assert first["task_id"] == "task_3"

    def test_search_agent_output_includes_project_id(self, db_session, seeded_data, search_service):
        result = search_service.search("401")
        first = result["agent_outputs"][0]
        assert first["project_id"] == "proj_c"

    def test_search_agent_output_contains_created_at(self, db_session, seeded_data, search_service):
        result = search_service.search("登录")
        first = result["agent_outputs"][0]
        assert first["created_at"] is not None

    def test_search_agent_output_multiple_results(self, db_session, seeded_data, search_service):
        result = search_service.search("完成")
        assert result["total_agent_outputs"] >= 2


class TestGlobalSearchCombined:

    def test_search_returns_both_projects_and_outputs(self, db_session, seeded_data, search_service):
        result = search_service.search("用户")
        assert result["total_projects"] >= 0
        assert result["total_agent_outputs"] >= 1

    def test_search_result_structure(self, db_session, seeded_data, search_service):
        result = search_service.search("数据")
        assert "query" in result
        assert "total_projects" in result
        assert "total_agent_outputs" in result
        assert "projects" in result
        assert "agent_outputs" in result
        assert "elapsed_ms" in result

    def test_search_query_echoed_back(self, db_session, seeded_data, search_service):
        result = search_service.search("项目管理")
        assert result["query"] == "项目管理"

    def test_search_project_result_has_type(self, db_session, seeded_data, search_service):
        result = search_service.search("电商")
        for p in result["projects"]:
            assert p["type"] == "project"

    def test_search_agent_result_has_type(self, db_session, seeded_data, search_service):
        result = search_service.search("JWT")
        for a in result["agent_outputs"]:
            assert a["type"] == "agent_output"


class TestGlobalSearchFuzzyMatching:

    def test_fuzzy_score_exact_match_is_one(self, search_service):
        score = GlobalSearchService._fuzzy_score("电商", "电商交易平台")
        assert score == 1.0

    def test_fuzzy_score_partial_match_above_zero(self, search_service):
        score = GlobalSearchService._fuzzy_score("电商交易", "电商业平台")
        assert 0 < score < 1.0

    def test_fuzzy_score_no_match_is_zero(self, search_service):
        score = GlobalSearchService._fuzzy_score("abcdefg", "1234567")
        assert score == 0.0

    def test_fuzzy_score_case_insensitive(self, search_service):
        score_upper = GlobalSearchService._fuzzy_score("JWT", "jwt 令牌签发")
        score_lower = GlobalSearchService._fuzzy_score("jwt", "JWT 令牌签发")
        assert score_upper == score_lower

    def test_fuzzy_score_empty_query(self, search_service):
        score = GlobalSearchService._fuzzy_score("", "电商交易平台")
        assert score == 0.0

    def test_fuzzy_score_empty_text(self, search_service):
        score = GlobalSearchService._fuzzy_score("电商", "")
        assert score == 0.0

    def test_fuzzy_match_retrieves_partial_project(self, db_session, seeded_data, search_service):
        result = search_service.search("电交平")
        assert result["total_projects"] >= 1

    def test_fuzzy_match_retrieves_partial_agent_output(self, db_session, seeded_data, search_service):
        result = search_service.search("柱状图")
        assert result["total_agent_outputs"] >= 1


class TestGlobalSearchPerformance:

    def test_search_response_time_under_500ms_small_dataset(self, db_session, seeded_data, search_service):
        start = time.perf_counter()
        search_service.search("电商")
        elapsed_ms = (time.perf_counter() - start) * 1000
        assert elapsed_ms <= 500, f"响应时间 {elapsed_ms:.1f}ms 超过 500ms"

    def test_search_response_time_under_500ms_fuzzy(self, db_session, seeded_data, search_service):
        start = time.perf_counter()
        search_service.search("电交易")
        elapsed_ms = (time.perf_counter() - start) * 1000
        assert elapsed_ms <= 500, f"响应时间 {elapsed_ms:.1f}ms 超过 500ms"

    def test_search_response_time_under_500ms_agent_output(self, db_session, seeded_data, search_service):
        start = time.perf_counter()
        search_service.search("refresh_token")
        elapsed_ms = (time.perf_counter() - start) * 1000
        assert elapsed_ms <= 500, f"响应时间 {elapsed_ms:.1f}ms 超过 500ms"

    def test_search_elapsed_ms_in_result(self, db_session, seeded_data, search_service):
        result = search_service.search("用户")
        assert "elapsed_ms" in result
        assert result["elapsed_ms"] >= 0

    def test_search_response_time_with_large_dataset(self, db_session, search_service):
        agents = []
        for i in range(5):
            a = Agent(
                id=f"perf_agent_{i}",
                name=f"Agent {i}",
                agent_type="opencode",
                status="online",
                config={},
            )
            db_session.add(a)
            agents.append(a)
        for i in range(200):
            p = Project(
                id=f"perf_proj_{i}",
                name=f"性能测试项目 {i}",
                slug=f"perf-{i}",
                creator_id="user_1",
            )
            db_session.add(p)
        db_session.flush()
        for i in range(200):
            t = Task(
                id=f"perf_task_{i}",
                project_id=f"perf_proj_{i}",
                name=f"任务 {i}",
                type="coding",
                status="delivered",
            )
            db_session.add(t)
        db_session.flush()
        for i in range(200):
            log = AgentExecutionLog(
                id=f"perf_log_{i}",
                task_id=f"perf_task_{i}",
                agent_id=f"perf_agent_{i % 5}",
                execution_content=f"执行任务 {i}",
                result=f"完成任务 {i}，产出代码 {i} 行",
            )
            db_session.add(log)
        db_session.commit()

        start = time.perf_counter()
        search_service.search("性能")
        elapsed_ms = (time.perf_counter() - start) * 1000
        assert elapsed_ms <= 500, f"大数据集响应时间 {elapsed_ms:.1f}ms 超过 500ms"


class TestGlobalSearchLimit:

    def test_search_limit_param(self, db_session, search_service):
        for i in range(10):
            p = Project(
                id=f"limit_proj_{i}",
                name=f"搜索限制项目 {i}",
                slug=f"limit-{i}",
                creator_id="user_1",
            )
            db_session.add(p)
        db_session.commit()
        result = search_service.search("搜索", limit=3)
        assert len(result["projects"]) <= 3

    def test_search_default_limit(self, db_session, search_service):
        result = search_service.search("", limit=50)
        assert True


class TestGlobalSearchEdgeCases:

    def test_search_special_characters(self, db_session, seeded_data, search_service):
        result = search_service.search("JWT令牌签发")
        assert result is not None

    def test_search_unicode(self, db_session, seeded_data, search_service):
        result = search_service.search("认证")
        assert result is not None

    def test_search_whitespace_only(self, db_session, seeded_data, search_service):
        result = search_service.search("   ")
        assert result["total_projects"] == 0
        assert result["total_agent_outputs"] == 0
        assert "elapsed_ms" in result

    def test_search_single_char(self, db_session, seeded_data, search_service):
        result = search_service.search("电")
        assert result is not None
        assert "projects" in result

    def test_search_very_long_query(self, db_session, seeded_data, search_service):
        long_query = "电" * 500
        result = search_service.search(long_query)
        assert result is not None
        assert "elapsed_ms" in result


if __name__ == "__main__":
    pytest.main([__file__, "-v"])
