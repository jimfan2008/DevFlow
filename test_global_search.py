import time
from unittest.mock import MagicMock, patch


class GlobalSearchService:
    """全局搜索服务，支持按项目名称和Agent产出关键词搜索。"""

    def __init__(self, index=None):
        self._index = index or {}

    def search(self, query: str) -> list:
        raise NotImplementedError("子类必须实现 search")


class SimpleGlobalSearch(GlobalSearchService):
    """基于内存索引的简单全局搜索实现。"""

    def __init__(self, index=None):
        super().__init__(index)
        self._results = []

    def build_index(self, projects: list):
        """构建搜索索引。"""
        self._index = {}
        for project in projects:
            project_key = project.get("name", "")
            self._index[project_key] = project

    def search(self, query: str) -> list:
        """执行模糊搜索，返回匹配的项目和Agent产出。"""
        query_lower = query.lower()
        results = []
        for project_name, project in self._index.items():
            matched_output = None
            if query_lower in project_name.lower():
                matched_output = project.get("agent_output", [])
            else:
                for item in project.get("agent_output", []):
                    if query_lower in str(item).lower():
                        matched_output = [item]
                        break
            if matched_output is not None:
                results.append({
                    "project_name": project_name,
                    "agent_output": matched_output,
                })
        return results


def _create_sample_projects():
    return [
        {
            "name": "Alpha项目",
            "agent_output": ["需求文档 v1.0", "接口设计稿", "测试用例集"],
        },
        {
            "name": "Beta项目",
            "agent_output": ["用户故事地图", "原型设计", "API文档 v2"],
        },
        {
            "name": "Gamma实验",
            "agent_output": ["数据迁移脚本", "性能测试报告"],
        },
        {
            "name": "Delta平台",
            "agent_output": ["部署手册", "运维监控方案"],
        },
    ]


# ── 测试用例 ──

def test_search_by_project_name_exact():
    svc = SimpleGlobalSearch()
    svc.build_index(_create_sample_projects())
    results = svc.search("Alpha项目")
    assert len(results) == 1
    assert results[0]["project_name"] == "Alpha项目"


def test_search_by_project_name_fuzzy():
    svc = SimpleGlobalSearch()
    svc.build_index(_create_sample_projects())
    results = svc.search("Alpha")
    assert len(results) >= 1
    assert any(r["project_name"] == "Alpha项目" for r in results)


def test_search_by_agent_output_keyword():
    svc = SimpleGlobalSearch()
    svc.build_index(_create_sample_projects())
    results = svc.search("API文档")
    assert len(results) >= 1
    assert any(r["project_name"] == "Beta项目" for r in results)


def test_search_by_agent_output_fuzzy():
    svc = SimpleGlobalSearch()
    svc.build_index(_create_sample_projects())
    results = svc.search("接口")
    assert len(results) >= 1
    assert any(r["project_name"] == "Alpha项目" for r in results)


def test_search_returns_agent_output_in_result():
    svc = SimpleGlobalSearch()
    svc.build_index(_create_sample_projects())
    results = svc.search("需求文档")
    assert len(results) >= 1
    matched = [r for r in results if r["project_name"] == "Alpha项目"]
    assert len(matched) == 1
    assert "需求文档 v1.0" in matched[0]["agent_output"]


def test_search_no_match_returns_empty():
    svc = SimpleGlobalSearch()
    svc.build_index(_create_sample_projects())
    results = svc.search("不存在的关键词xyz123")
    assert results == []


def test_search_empty_index_returns_empty():
    svc = SimpleGlobalSearch()
    svc.build_index([])
    results = svc.search("任意词")
    assert results == []


def test_search_response_time_within_500ms():
    svc = SimpleGlobalSearch()
    projects = _create_sample_projects() * 100
    svc.build_index(projects)
    start = time.perf_counter()
    svc.search("项目")
    elapsed_ms = (time.perf_counter() - start) * 1000
    assert elapsed_ms < 500, f"搜索耗时 {elapsed_ms:.1f}ms，超过 500ms 上限"


def test_search_case_insensitive():
    svc = SimpleGlobalSearch()
    svc.build_index(_create_sample_projects())
    result_lower = svc.search("beta")
    result_upper = svc.search("BETA")
    assert len(result_lower) == len(result_upper) >= 1


def test_search_multiple_projects_match():
    svc = SimpleGlobalSearch()
    svc.build_index(_create_sample_projects())
    results = svc.search("项目")
    assert len(results) == 2  # Alpha项目, Beta项目


def test_search_multiple_agent_outputs_match():
    svc = SimpleGlobalSearch()
    svc.build_index(_create_sample_projects())
    results = svc.search("文档")
    project_names = {r["project_name"] for r in results}
    assert "Alpha项目" in project_names
    assert "Beta项目" in project_names


def test_global_search_base_class_raises_not_implemented():
    base = GlobalSearchService()
    try:
        base.search("test")
        assert False, "应该抛出 NotImplementedError"
    except NotImplementedError:
        pass


if __name__ == "__main__":
    import pytest
    pytest.main([__file__, "-v"])
