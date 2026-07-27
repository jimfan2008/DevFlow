import time
import difflib
from dataclasses import dataclass, field
from typing import List, Dict, Any

import pytest


@dataclass
class Project:
    id: str
    name: str
    description: str = ""
    status: str = "active"


@dataclass
class AgentOutput:
    id: str
    agent_name: str
    content: str
    project_id: str = ""
    keywords: List[str] = field(default_factory=list)
    created_at: float = 0.0


class GlobalSearchEngine:
    """全局搜索引擎，支持按项目名称和 Agent 产出关键词模糊搜索"""

    DEFAULT_MIN_SCORE = 0.3
    DEFAULT_LIMIT = 50

    def __init__(self, min_score: float = DEFAULT_MIN_SCORE, limit: int = DEFAULT_LIMIT):
        self._min_score = min_score
        self._limit = limit
        self._projects: List[Project] = []
        self._agent_outputs: List[AgentOutput] = []

    def add_project(self, project: Project) -> None:
        self._projects.append(project)

    def add_projects(self, projects: List[Project]) -> None:
        self._projects.extend(projects)

    def add_agent_output(self, output: AgentOutput) -> None:
        self._agent_outputs.append(output)

    def add_agent_outputs(self, outputs: List[AgentOutput]) -> None:
        self._agent_outputs.extend(outputs)

    def clear(self) -> None:
        self._projects.clear()
        self._agent_outputs.clear()

    def search(self, query: str) -> Dict[str, Any]:
        """执行全局搜索，返回匹配的项目和 Agent 产出"""
        t0 = time.perf_counter()
        query = (query or "").strip()

        if not query:
            return self._build_empty_result(query, t0)

        matched_projects = self._search_projects(query)
        matched_outputs = self._search_agent_outputs(query)

        matched_projects.sort(key=lambda x: x["match_score"], reverse=True)
        matched_outputs.sort(key=lambda x: x["match_score"], reverse=True)

        matched_projects = matched_projects[: self._limit]
        matched_outputs = matched_outputs[: self._limit]

        elapsed_ms = round((time.perf_counter() - t0) * 1000, 2)
        return {
            "query": query,
            "total_projects": len(matched_projects),
            "total_agent_outputs": len(matched_outputs),
            "projects": matched_projects,
            "agent_outputs": matched_outputs,
            "elapsed_ms": elapsed_ms,
        }

    def _search_projects(self, query: str) -> List[Dict[str, Any]]:
        results = []
        for p in self._projects:
            score = self._compute_fuzzy_score(query, p.name)
            if score > self._min_score:
                results.append({
                    "type": "project",
                    "id": p.id,
                    "title": p.name,
                    "snippet": p.description,
                    "match_score": round(score, 4),
                    "metadata": {"status": p.status, "description": p.description},
                })
        return results

    def _search_agent_outputs(self, query: str) -> List[Dict[str, Any]]:
        results = []
        for o in self._agent_outputs:
            max_score = self._compute_fuzzy_score(query, o.content)
            for kw in o.keywords:
                s = self._compute_fuzzy_score(query, kw)
                if s > max_score:
                    max_score = s
            if max_score > self._min_score:
                results.append({
                    "type": "agent_output",
                    "id": o.id,
                    "title": o.agent_name,
                    "snippet": o.content,
                    "match_score": round(max_score, 4),
                    "metadata": {
                        "agent_name": o.agent_name,
                        "project_id": o.project_id,
                        "keywords": o.keywords,
                        "created_at": o.created_at,
                    },
                })
        return results

    def _compute_fuzzy_score(self, query: str, text: str) -> float:
        """计算模糊匹配分数"""
        if not query or not text:
            return 0.0
        q_low = query.lower()
        t_low = text.lower()
        if q_low in t_low:
            return 1.0
        ratio = difflib.SequenceMatcher(None, q_low, t_low).ratio()
        return ratio if ratio >= self._min_score else 0.0

    def _build_empty_result(self, query: str, t0: float) -> Dict[str, Any]:
        elapsed_ms = round((time.perf_counter() - t0) * 1000, 2)
        return {
            "query": query,
            "total_projects": 0,
            "total_agent_outputs": 0,
            "projects": [],
            "agent_outputs": [],
            "elapsed_ms": elapsed_ms,
        }


# ===================== Fixtures =====================

@pytest.fixture
def engine_with_data():
    eng = GlobalSearchEngine()
    eng.add_projects([
        Project(id="p1", name="电商交易平台", description="在线电商项目", status="active"),
        Project(id="p2", name="数据分析平台", description="数据分析与可视化", status="active"),
        Project(id="p3", name="用户认证服务", description="OAuth 认证微服务", status="inactive"),
        Project(id="p4", name="项目管理工具", description="敏捷项目管理", status="completed"),
        Project(id="p5", name="AI 智能客服", description="AI 客服对话系统", status="active"),
    ])
    eng.add_agent_outputs([
        AgentOutput(
            id="a1", agent_name="OpenCode Agent",
            content="已完成用户登录模块，包含密码验证和 JWT 令牌签发",
            project_id="p3", keywords=["登录", "JWT", "令牌"],
            created_at=1000.0,
        ),
        AgentOutput(
            id="a2", agent_name="Cursor Agent",
            content="完成 ECharts 柱状图和折线图组件，支持动态数据绑定",
            project_id="p2", keywords=["图表", "可视化", "ECharts"],
            created_at=2000.0,
        ),
        AgentOutput(
            id="a3", agent_name="OpenCode Agent",
            content="完成 refresh_token 自动刷新，支持 401 自动重试",
            project_id="p3", keywords=["token", "刷新", "重试"],
            created_at=3000.0,
        ),
        AgentOutput(
            id="a4", agent_name="Copilot Agent",
            content="生成月度报表和数据可视化图表",
            project_id="p2", keywords=["报表", "图表"],
            created_at=4000.0,
        ),
        AgentOutput(
            id="a5", agent_name="OpenCode Agent",
            content="实现购物车结算流程和订单状态机",
            project_id="p1", keywords=["购物车", "订单", "结算"],
            created_at=5000.0,
        ),
    ])
    return eng


@pytest.fixture
def empty_engine():
    return GlobalSearchEngine()


@pytest.fixture
def large_engine():
    eng = GlobalSearchEngine()
    for i in range(500):
        eng.add_project(Project(
            id=f"big_p{i}", name=f"测试项目-{i} 模块",
            description=f"这是第 {i} 个测试项目", status="active",
        ))
    for i in range(500):
        eng.add_agent_output(AgentOutput(
            id=f"big_a{i}", agent_name=f"Agent-{i % 5}",
            content=f"完成任务编号 {i}，涉及模块 {i}，产出代码 {i * 10} 行",
            project_id=f"big_p{i}", keywords=[f"模块{i}", f"任务{i}"],
            created_at=float(i),
        ))
    return eng


# ===================== 测试类 =====================

class TestSearchByProjectName:

    def test_exact_match_returns_single_project(self, engine_with_data):
        result = engine_with_data.search("电商交易平台")
        assert result["total_projects"] >= 1
        assert result["projects"][0]["title"] == "电商交易平台"
        assert result["projects"][0]["match_score"] == 1.0

    def test_substring_match_returns_project(self, engine_with_data):
        result = engine_with_data.search("电商")
        assert result["total_projects"] >= 1
        names = [p["title"] for p in result["projects"]]
        assert "电商交易平台" in names

    def test_multiple_projects_matched(self, engine_with_data):
        result = engine_with_data.search("平台")
        assert result["total_projects"] >= 2
        names = [p["title"] for p in result["projects"]]
        assert "电商交易平台" in names
        assert "数据分析平台" in names

    def test_no_match_returns_empty_projects(self, engine_with_data):
        result = engine_with_data.search("不存在的量子项目 XXXX")
        assert result["total_projects"] == 0
        assert result["projects"] == []

    def test_empty_query_returns_no_projects(self, engine_with_data):
        result = engine_with_data.search("")
        assert result["total_projects"] == 0

    def test_whitespace_query_returns_no_projects(self, engine_with_data):
        result = engine_with_data.search("   \t  ")
        assert result["total_projects"] == 0

    def test_case_insensitive_project_name(self, empty_engine):
        empty_engine.add_project(Project(id="p10", name="DataAnalysis Platform"))
        result = empty_engine.search("dataanalysis")
        assert result["total_projects"] == 1
        assert result["projects"][0]["title"] == "DataAnalysis Platform"

    def test_result_includes_project_status(self, engine_with_data):
        result = engine_with_data.search("认证")
        assert result["total_projects"] >= 1
        assert result["projects"][0]["metadata"]["status"] == "inactive"

    def test_result_includes_project_description(self, engine_with_data):
        result = engine_with_data.search("电商")
        assert result["projects"][0]["metadata"]["description"] == "在线电商项目"

    def test_results_sorted_by_score_descending(self, engine_with_data):
        result = engine_with_data.search("平台")
        scores = [p["match_score"] for p in result["projects"]]
        assert scores == sorted(scores, reverse=True)


class TestSearchByAgentOutput:

    def test_exact_keyword_in_content(self, engine_with_data):
        result = engine_with_data.search("JWT")
        assert result["total_agent_outputs"] >= 1
        assert "JWT" in result["agent_outputs"][0]["snippet"]

    def test_exact_keyword_in_keywords_field(self, engine_with_data):
        result = engine_with_data.search("购物车")
        assert result["total_agent_outputs"] >= 1

    def test_substring_match_in_content(self, engine_with_data):
        result = engine_with_data.search("令牌")
        assert result["total_agent_outputs"] >= 1

    def test_no_match_returns_empty_outputs(self, engine_with_data):
        result = engine_with_data.search("不存在的产出关键词 ZZZZ")
        assert result["total_agent_outputs"] == 0

    def test_empty_query_returns_no_outputs(self, engine_with_data):
        result = engine_with_data.search("")
        assert result["total_agent_outputs"] == 0

    def test_result_includes_agent_name(self, engine_with_data):
        result = engine_with_data.search("ECharts")
        assert result["total_agent_outputs"] >= 1
        assert result["agent_outputs"][0]["title"] == "Cursor Agent"

    def test_result_includes_project_id(self, engine_with_data):
        result = engine_with_data.search("refresh_token")
        assert result["total_agent_outputs"] >= 1
        assert result["agent_outputs"][0]["metadata"]["project_id"] == "p3"

    def test_result_includes_created_at(self, engine_with_data):
        result = engine_with_data.search("登录")
        assert result["total_agent_outputs"] >= 1
        assert result["agent_outputs"][0]["metadata"]["created_at"] == 1000.0

    def test_multiple_outputs_matched(self, engine_with_data):
        result = engine_with_data.search("完成")
        assert result["total_agent_outputs"] >= 2

    def test_search_by_keyword_field_matches(self, engine_with_data):
        result = engine_with_data.search("报表")
        assert result["total_agent_outputs"] >= 1

    def test_agent_output_result_has_match_score(self, engine_with_data):
        result = engine_with_data.search("JWT")
        assert "match_score" in result["agent_outputs"][0]
        assert 0 < result["agent_outputs"][0]["match_score"] <= 1.0


class TestFuzzyMatching:

    def test_fuzzy_exact_inclusion_score_is_one(self, engine_with_data):
        score = engine_with_data._compute_fuzzy_score("电商", "电商交易平台")
        assert score == 1.0

    def test_fuzzy_partial_score_between_zero_and_one(self, engine_with_data):
        score = engine_with_data._compute_fuzzy_score("电商交易", "电商业平台")
        assert 0 < score < 1.0

    def test_fuzzy_no_match_score_is_zero(self, engine_with_data):
        score = engine_with_data._compute_fuzzy_score("abcdefg", "1234567")
        assert score == 0.0

    def test_fuzzy_case_insensitive(self, engine_with_data):
        s1 = engine_with_data._compute_fuzzy_score("JWT", "jwt token")
        s2 = engine_with_data._compute_fuzzy_score("jwt", "JWT token")
        assert s1 == s2

    def test_fuzzy_empty_query_returns_zero(self, engine_with_data):
        assert engine_with_data._compute_fuzzy_score("", "任意文本") == 0.0

    def test_fuzzy_empty_text_returns_zero(self, engine_with_data):
        assert engine_with_data._compute_fuzzy_score("任意文本", "") == 0.0

    def test_fuzzy_retrieves_project_with_partial_match(self, engine_with_data):
        result = engine_with_data.search("电交平")
        assert result["total_projects"] >= 1

    def test_fuzzy_retrieves_agent_output_with_partial(self, engine_with_data):
        result = engine_with_data.search("柱状图")
        assert result["total_agent_outputs"] >= 1

    def test_fuzzy_via_difflib_ratio(self, engine_with_data):
        result = engine_with_data.search("电商交易平")
        assert result["total_projects"] >= 1

    def test_min_score_threshold_filters_low_scores(self, empty_engine):
        eng = GlobalSearchEngine(min_score=0.8)
        eng.add_project(Project(id="p1", name="电商平台"))
        result = eng.search("电子商店")
        assert result["total_projects"] == 0


class TestSearchPerformance:

    def test_small_dataset_under_500ms(self, engine_with_data):
        start = time.perf_counter()
        engine_with_data.search("电商")
        elapsed_ms = (time.perf_counter() - start) * 1000
        assert elapsed_ms <= 500, f"响应时间 {elapsed_ms:.1f}ms 超过 500ms"

    def test_fuzzy_search_under_500ms(self, engine_with_data):
        start = time.perf_counter()
        engine_with_data.search("电交易")
        elapsed_ms = (time.perf_counter() - start) * 1000
        assert elapsed_ms <= 500, f"响应时间 {elapsed_ms:.1f}ms 超过 500ms"

    def test_agent_output_search_under_500ms(self, engine_with_data):
        start = time.perf_counter()
        engine_with_data.search("refresh_token")
        elapsed_ms = (time.perf_counter() - start) * 1000
        assert elapsed_ms <= 500, f"响应时间 {elapsed_ms:.1f}ms 超过 500ms"

    def test_elapsed_ms_field_present_and_non_negative(self, engine_with_data):
        result = engine_with_data.search("用户")
        assert "elapsed_ms" in result
        assert result["elapsed_ms"] >= 0

    def test_large_dataset_under_500ms(self, large_engine):
        start = time.perf_counter()
        large_engine.search("测试项目")
        elapsed_ms = (time.perf_counter() - start) * 1000
        assert elapsed_ms <= 500, f"大数据集响应时间 {elapsed_ms:.1f}ms 超过 500ms"

    def test_large_dataset_agent_search_under_500ms(self, large_engine):
        start = time.perf_counter()
        large_engine.search("模块 42")
        elapsed_ms = (time.perf_counter() - start) * 1000
        assert elapsed_ms <= 500, f"大数据集 Agent 搜索响应时间 {elapsed_ms:.1f}ms 超过 500ms"


class TestSearchResultStructure:

    def test_result_contains_all_required_fields(self, engine_with_data):
        result = engine_with_data.search("数据")
        required = {"query", "total_projects", "total_agent_outputs", "projects", "agent_outputs", "elapsed_ms"}
        assert required.issubset(result.keys())

    def test_query_echoed_back(self, engine_with_data):
        result = engine_with_data.search("项目管理")
        assert result["query"] == "项目管理"

    def test_project_results_have_type_project(self, engine_with_data):
        result = engine_with_data.search("电商")
        for p in result["projects"]:
            assert p["type"] == "project"

    def test_agent_output_results_have_type_agent_output(self, engine_with_data):
        result = engine_with_data.search("JWT")
        for a in result["agent_outputs"]:
            assert a["type"] == "agent_output"

    def test_search_returns_both_projects_and_outputs(self, engine_with_data):
        result = engine_with_data.search("用户")
        assert "projects" in result
        assert "agent_outputs" in result

    def test_limit_param_restricts_count(self, engine_with_data):
        eng = GlobalSearchEngine(limit=1)
        eng.add_projects([
            Project(id="p1", name="电商交易平台"),
            Project(id="p2", name="数据分析平台"),
            Project(id="p3", name="用户增长平台"),
        ])
        result = eng.search("平台")
        assert len(result["projects"]) <= 1

    def test_project_result_has_match_score(self, engine_with_data):
        result = engine_with_data.search("电商")
        assert "match_score" in result["projects"][0]
        assert 0 < result["projects"][0]["match_score"] <= 1.0

    def test_total_counts_match_actual_arrays(self, engine_with_data):
        result = engine_with_data.search("平台")
        assert result["total_projects"] == len(result["projects"])
        assert result["total_agent_outputs"] == len(result["agent_outputs"])


class TestSearchEdgeCases:

    def test_empty_engine_returns_empty_result(self, empty_engine):
        result = empty_engine.search("任意")
        assert result["total_projects"] == 0
        assert result["total_agent_outputs"] == 0

    def test_single_char_query(self, engine_with_data):
        result = engine_with_data.search("电")
        assert result is not None
        assert "projects" in result

    def test_unicode_query(self, engine_with_data):
        result = engine_with_data.search("认证")
        assert result is not None
        assert "elapsed_ms" in result

    def test_special_characters_query(self, engine_with_data):
        result = engine_with_data.search("JWT 令牌签发")
        assert result is not None

    def test_very_long_query(self, engine_with_data):
        result = engine_with_data.search("电" * 500)
        assert result is not None
        assert "elapsed_ms" in result

    def test_none_query_handled(self, engine_with_data):
        result = engine_with_data.search(None)
        assert result["total_projects"] == 0
        assert result["total_agent_outputs"] == 0

    def test_empty_name_project_does_not_crash(self, empty_engine):
        empty_engine.add_project(Project(id="p99", name="", description=""))
        result = empty_engine.search("任意")
        assert result["total_projects"] == 0

    def test_clear_removes_all_data(self, engine_with_data):
        engine_with_data.clear()
        result = engine_with_data.search("电商")
        assert result["total_projects"] == 0
        assert result["total_agent_outputs"] == 0

    def test_results_sorted_by_score_for_agent_outputs(self, engine_with_data):
        result = engine_with_data.search("完成")
        scores = [a["match_score"] for a in result["agent_outputs"]]
        assert scores == sorted(scores, reverse=True)

    def test_multiple_same_keyword_in_outputs(self, engine_with_data):
        result = engine_with_data.search("图表")
        assert result["total_agent_outputs"] >= 1
        for a in result["agent_outputs"]:
            assert a["match_score"] > 0


class TestCombinedSearch:

    def test_search_matches_both_projects_and_outputs(self, engine_with_data):
        result = engine_with_data.search("用户")
        has_project = result["total_projects"] >= 1
        has_output = result["total_agent_outputs"] >= 1
        assert has_project or has_output

    def test_project_name_search_does_not_leak_into_agent(self, engine_with_data):
        result = engine_with_data.search("电商交易平台")
        assert result["total_projects"] >= 1
        assert result["projects"][0]["title"] == "电商交易平台"
        assert result["projects"][0]["match_score"] == 1.0
        for a in result["agent_outputs"]:
            assert "电商交易平台" not in a["metadata"].get("agent_name", "")

    def test_agent_keyword_not_in_project_name(self, engine_with_data):
        result = engine_with_data.search("JWT")
        project_names = [p["title"] for p in result["projects"]]
        assert "JWT" not in str(project_names)


if __name__ == "__main__":
    pytest.main([__file__, "-v"])
