import time
import difflib
from dataclasses import dataclass
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
    created_at: float = 0.0


class GlobalSearchComponent:
    """全局搜索组件 - 支持按项目名称和 Agent 产出关键词搜索"""

    def __init__(self, min_score: float = 0.35):
        self.projects: List[Project] = []
        self.agent_outputs: List[AgentOutput] = []
        self.min_score = min_score

    def add_project(self, project: Project) -> None:
        self.projects.append(project)

    def add_agent_output(self, output: AgentOutput) -> None:
        self.agent_outputs.append(output)

    def search(self, query: str, limit: int = 50) -> Dict[str, Any]:
        """执行全局搜索，返回匹配的项目和 Agent 产出"""
        start = time.perf_counter()
        q = (query or "").strip()

        matched_projects: List[Dict[str, Any]] = []
        matched_outputs: List[Dict[str, Any]] = []

        if q:
            for p in self.projects:
                score = self._fuzzy_score(q, p.name)
                if score > 0:
                    matched_projects.append({
                        "type": "project",
                        "id": p.id,
                        "name": p.name,
                        "description": p.description,
                        "status": p.status,
                        "match_score": round(score, 4),
                    })
            matched_projects.sort(key=lambda x: x["match_score"], reverse=True)
            matched_projects = matched_projects[:limit]

            for o in self.agent_outputs:
                score = self._fuzzy_score(q, o.content)
                if score > 0:
                    matched_outputs.append({
                        "type": "agent_output",
                        "id": o.id,
                        "agent_name": o.agent_name,
                        "content": o.content,
                        "project_id": o.project_id,
                        "match_score": round(score, 4),
                        "created_at": o.created_at,
                    })
            matched_outputs.sort(key=lambda x: x["match_score"], reverse=True)
            matched_outputs = matched_outputs[:limit]

        elapsed_ms = (time.perf_counter() - start) * 1000
        return {
            "query": query,
            "total_projects": len(matched_projects),
            "total_agent_outputs": len(matched_outputs),
            "projects": matched_projects,
            "agent_outputs": matched_outputs,
            "elapsed_ms": round(elapsed_ms, 2),
        }

    def _fuzzy_score(self, query: str, text: str) -> float:
        """计算模糊匹配分数：完全包含 1.0，difflib 比率（>= min_score 阈值），否则 0"""
        if not query or not text:
            return 0.0
        q_lower = query.lower()
        t_lower = text.lower()
        if q_lower in t_lower:
            return 1.0
        ratio = difflib.SequenceMatcher(None, q_lower, t_lower).ratio()
        return ratio if ratio >= self.min_score else 0.0


@pytest.fixture
def search_component():
    """创建带预置数据的全局搜索组件"""
    comp = GlobalSearchComponent()

    comp.add_project(Project(
        id="p1", name="电商交易平台",
        description="在线电商项目", status="active",
    ))
    comp.add_project(Project(
        id="p2", name="数据分析平台",
        description="数据分析与可视化", status="active",
    ))
    comp.add_project(Project(
        id="p3", name="用户认证服务",
        description="OAuth 认证微服务", status="inactive",
    ))
    comp.add_project(Project(
        id="p4", name="项目管理工具",
        description="敏捷项目管理", status="completed",
    ))

    comp.add_agent_output(AgentOutput(
        id="a1", agent_name="OpenCode Agent",
        content="已完成用户登录模块，包含密码验证和 JWT 令牌签发",
        project_id="p1", created_at=1000.0,
    ))
    comp.add_agent_output(AgentOutput(
        id="a2", agent_name="Cursor Agent",
        content="完成 ECharts 柱状图和折线图组件，支持动态数据绑定",
        project_id="p2", created_at=2000.0,
    ))
    comp.add_agent_output(AgentOutput(
        id="a3", agent_name="OpenCode Agent",
        content="完成 refresh_token 自动刷新，支持 401 自动重试",
        project_id="p3", created_at=3000.0,
    ))
    comp.add_agent_output(AgentOutput(
        id="a4", agent_name="Copilot Agent",
        content="生成月度报表和数据可视化图表",
        project_id="p2", created_at=4000.0,
    ))

    return comp


@pytest.fixture
def empty_component():
    """创建空的全局搜索组件"""
    return GlobalSearchComponent()


class TestSearchByProjectName:
    """验证按项目名称搜索的功能"""

    def test_exact_match_project_name(self, search_component):
        """精确匹配项目名称"""
        result = search_component.search("电商交易平台")
        assert result["total_projects"] == 1
        assert result["projects"][0]["name"] == "电商交易平台"
        assert result["projects"][0]["match_score"] == 1.0

    def test_partial_match_project_name(self, search_component):
        """子串匹配项目名称"""
        result = search_component.search("电商")
        assert result["total_projects"] >= 1
        assert result["projects"][0]["name"] == "电商交易平台"

    def test_multiple_projects_matched(self, search_component):
        """多个项目命中同一个关键词"""
        result = search_component.search("平台")
        assert result["total_projects"] >= 2
        names = [p["name"] for p in result["projects"]]
        assert "电商交易平台" in names
        assert "数据分析平台" in names

    def test_no_match_returns_empty(self, search_component):
        """无匹配时返回空列表"""
        result = search_component.search("不存在的量子项目XXXX")
        assert result["total_projects"] == 0
        assert result["projects"] == []

    def test_empty_query_returns_no_projects(self, search_component):
        """空查询不返回任何项目"""
        result = search_component.search("")
        assert result["total_projects"] == 0

    def test_whitespace_only_query_returns_no_projects(self, search_component):
        """纯空白查询不返回任何项目"""
        result = search_component.search("   ")
        assert result["total_projects"] == 0

    def test_result_contains_project_status(self, search_component):
        """搜索结果包含项目状态字段"""
        result = search_component.search("认证")
        assert result["total_projects"] >= 1
        assert result["projects"][0]["status"] == "inactive"

    def test_result_contains_project_description(self, search_component):
        """搜索结果包含项目描述字段"""
        result = search_component.search("电商")
        assert result["projects"][0]["description"] == "在线电商项目"

    def test_case_insensitive_project_name(self):
        """项目名称搜索不区分大小写"""
        comp = GlobalSearchComponent()
        comp.add_project(Project(id="p10", name="DataAnalysis Platform"))
        result = comp.search("dataanalysis")
        assert result["total_projects"] == 1
        assert result["projects"][0]["name"] == "DataAnalysis Platform"


class TestSearchByAgentOutput:
    """验证按 Agent 产出关键词搜索的功能"""

    def test_exact_keyword_in_agent_output(self, search_component):
        """精确关键词匹配 Agent 产出"""
        result = search_component.search("JWT")
        assert result["total_agent_outputs"] >= 1
        assert "JWT" in result["agent_outputs"][0]["content"]

    def test_partial_keyword_in_agent_output(self, search_component):
        """子串匹配 Agent 产出"""
        result = search_component.search("令牌")
        assert result["total_agent_outputs"] >= 1

    def test_no_match_returns_empty(self, search_component):
        """无匹配时 Agent 产出为空"""
        result = search_component.search("不存在的产出关键词ZZZZ")
        assert result["total_agent_outputs"] == 0

    def test_empty_query_returns_no_outputs(self, search_component):
        """空查询不返回任何 Agent 产出"""
        result = search_component.search("")
        assert result["total_agent_outputs"] == 0

    def test_result_includes_agent_name(self, search_component):
        """搜索结果包含 Agent 名称"""
        result = search_component.search("ECharts")
        assert result["total_agent_outputs"] >= 1
        assert result["agent_outputs"][0]["agent_name"] == "Cursor Agent"

    def test_result_includes_project_id(self, search_component):
        """搜索结果包含关联的项目 ID"""
        result = search_component.search("refresh_token")
        assert result["total_agent_outputs"] >= 1
        assert result["agent_outputs"][0]["project_id"] == "p3"

    def test_result_includes_created_at(self, search_component):
        """搜索结果包含创建时间"""
        result = search_component.search("登录")
        assert result["total_agent_outputs"] >= 1
        assert result["agent_outputs"][0]["created_at"] == 1000.0

    def test_multiple_agent_outputs_matched(self, search_component):
        """多个 Agent 产出命中同一个关键词"""
        result = search_component.search("完成")
        assert result["total_agent_outputs"] >= 2


class TestFuzzyMatching:
    """验证模糊匹配功能"""

    def test_fuzzy_score_exact_is_one(self, search_component):
        """完全包含时分数为 1.0"""
        score = search_component._fuzzy_score("电商", "电商交易平台")
        assert score == 1.0

    def test_fuzzy_score_partial_above_threshold(self, search_component):
        """部分匹配的分数在 0 和 1 之间"""
        score = search_component._fuzzy_score("电商交易", "电商业平台")
        assert 0 < score < 1.0

    def test_fuzzy_score_no_match_is_zero(self, search_component):
        """完全无关的文本分数为 0"""
        score = search_component._fuzzy_score("abcdefg", "1234567")
        assert score == 0.0

    def test_fuzzy_score_case_insensitive(self, search_component):
        """模糊匹配不区分大小写"""
        s1 = search_component._fuzzy_score("JWT", "jwt token")
        s2 = search_component._fuzzy_score("jwt", "JWT token")
        assert s1 == s2

    def test_fuzzy_score_empty_query(self, search_component):
        """空查询返回 0"""
        assert search_component._fuzzy_score("", "任意文本") == 0.0

    def test_fuzzy_score_empty_text(self, search_component):
        """空文本返回 0"""
        assert search_component._fuzzy_score("任意文本", "") == 0.0

    def test_fuzzy_retrieves_project_with_partial_match(self, search_component):
        """模糊匹配可以检索到部分匹配的项目"""
        result = search_component.search("电交平")
        assert result["total_projects"] >= 1

    def test_fuzzy_retrieves_agent_output_with_partial_match(self, search_component):
        """模糊匹配可以检索到部分匹配的 Agent 产出"""
        result = search_component.search("柱状图")
        assert result["total_agent_outputs"] >= 1

    def test_fuzzy_match_via_difflib(self, search_component):
        """通过 difflib 比率实现的模糊匹配"""
        result = search_component.search("电商交易平")
        assert result["total_projects"] >= 1


class TestSearchPerformance:
    """验证搜索响应时间在 500ms 以内"""

    def test_response_time_under_500ms_small_dataset(self, search_component):
        """小数据集搜索响应时间 < 500ms"""
        start = time.perf_counter()
        search_component.search("电商")
        elapsed_ms = (time.perf_counter() - start) * 1000
        assert elapsed_ms <= 500, f"响应时间 {elapsed_ms:.1f}ms 超过 500ms"

    def test_response_time_under_500ms_fuzzy_search(self, search_component):
        """模糊搜索响应时间 < 500ms"""
        start = time.perf_counter()
        search_component.search("电交易")
        elapsed_ms = (time.perf_counter() - start) * 1000
        assert elapsed_ms <= 500, f"响应时间 {elapsed_ms:.1f}ms 超过 500ms"

    def test_response_time_under_500ms_agent_output_search(self, search_component):
        """Agent 产出搜索响应时间 < 500ms"""
        start = time.perf_counter()
        search_component.search("refresh_token")
        elapsed_ms = (time.perf_counter() - start) * 1000
        assert elapsed_ms <= 500, f"响应时间 {elapsed_ms:.1f}ms 超过 500ms"

    def test_elapsed_ms_present_in_result(self, search_component):
        """搜索结果包含 elapsed_ms 字段"""
        result = search_component.search("用户")
        assert "elapsed_ms" in result
        assert result["elapsed_ms"] >= 0

    def test_response_time_under_500ms_large_dataset(self, search_component):
        """大数据集（500 个项目 + 500 条产出）搜索响应时间 < 500ms"""
        for i in range(500):
            search_component.add_project(Project(
                id=f"perf_p{i}", name=f"性能测试项目 {i}",
                description=f"描述 {i}", status="active",
            ))
        for i in range(500):
            search_component.add_agent_output(AgentOutput(
                id=f"perf_a{i}", agent_name=f"Agent {i % 3}",
                content=f"完成任务 {i}，产出代码 {i} 行",
                project_id=f"perf_p{i}", created_at=float(i),
            ))
        start = time.perf_counter()
        search_component.search("性能")
        elapsed_ms = (time.perf_counter() - start) * 1000
        assert elapsed_ms <= 500, f"大数据集响应时间 {elapsed_ms:.1f}ms 超过 500ms"


class TestSearchResultStructure:
    """验证搜索结果的数据结构"""

    def test_result_contains_all_required_fields(self, search_component):
        """结果包含所有必需字段"""
        result = search_component.search("数据")
        assert "query" in result
        assert "total_projects" in result
        assert "total_agent_outputs" in result
        assert "projects" in result
        assert "agent_outputs" in result
        assert "elapsed_ms" in result

    def test_query_echoed_back(self, search_component):
        """查询词回显"""
        result = search_component.search("项目管理")
        assert result["query"] == "项目管理"

    def test_project_results_have_type_field(self, search_component):
        """项目结果带有 type 标记"""
        result = search_component.search("电商")
        for p in result["projects"]:
            assert p["type"] == "project"

    def test_agent_output_results_have_type_field(self, search_component):
        """Agent 产出结果带有 type 标记"""
        result = search_component.search("JWT")
        for a in result["agent_outputs"]:
            assert a["type"] == "agent_output"

    def test_search_returns_both_projects_and_outputs(self, search_component):
        """搜索可同时返回项目和 Agent 产出"""
        result = search_component.search("用户")
        assert result["total_projects"] >= 0
        assert result["total_agent_outputs"] >= 1

    def test_search_limit_param_works(self, search_component):
        """limit 参数限制返回数量"""
        result = search_component.search("平台", limit=1)
        assert len(result["projects"]) <= 1

    def test_project_result_has_match_score(self, search_component):
        """项目结果包含匹配分数"""
        result = search_component.search("电商")
        assert "match_score" in result["projects"][0]
        assert 0 < result["projects"][0]["match_score"] <= 1.0

    def test_agent_output_result_has_match_score(self, search_component):
        """Agent 产出结果包含匹配分数"""
        result = search_component.search("JWT")
        assert "match_score" in result["agent_outputs"][0]
        assert 0 < result["agent_outputs"][0]["match_score"] <= 1.0


class TestSearchEdgeCases:
    """验证边界情况"""

    def test_empty_component_search(self, empty_component):
        """空组件搜索返回空结果"""
        result = empty_component.search("任意")
        assert result["total_projects"] == 0
        assert result["total_agent_outputs"] == 0

    def test_single_char_query(self, search_component):
        """单字符查询正常工作"""
        result = search_component.search("电")
        assert result is not None
        assert "projects" in result

    def test_unicode_query(self, search_component):
        """Unicode 查询正常工作"""
        result = search_component.search("认证")
        assert result is not None

    def test_special_characters_query(self, search_component):
        """特殊字符查询不报错"""
        result = search_component.search("JWT令牌签发")
        assert result is not None

    def test_very_long_query(self, search_component):
        """超长查询不报错"""
        result = search_component.search("电" * 500)
        assert result is not None
        assert "elapsed_ms" in result

    def test_results_sorted_by_score_descending(self, search_component):
        """结果按匹配分数降序排列"""
        result = search_component.search("平台")
        scores = [p["match_score"] for p in result["projects"]]
        assert scores == sorted(scores, reverse=True)

    def test_search_with_none_like_content(self, empty_component):
        """空内容项目不会报错"""
        empty_component.add_project(Project(id="p99", name="", description=""))
        result = empty_component.search("任意")
        assert result["total_projects"] == 0

    def test_multiple_same_keyword_outputs_all_match(self, search_component):
        """相同关键词在多个产出中都能匹配到"""
        result = search_component.search("图表")
        assert result["total_agent_outputs"] >= 1
        for a in result["agent_outputs"]:
            score = search_component._fuzzy_score("图表", a["content"])
            assert "图表" in a["content"] or score > 0


if __name__ == "__main__":
    pytest.main([__file__, "-v"])
