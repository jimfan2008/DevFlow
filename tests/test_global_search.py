import time
from unittest.mock import MagicMock


class MockSearchService:
    def __init__(self, projects):
        self._projects = projects

    def search(self, query):
        results = []
        query_lower = query.lower()
        for project in self._projects:
            matched_agents = []
            for agent in project.get("agents", []):
                if (query_lower in agent.get("name", "").lower() or
                        query_lower in agent.get("output", "").lower()):
                    matched_agents.append(agent)
            if (query_lower in project.get("name", "").lower() or
                    matched_agents):
                results.append({
                    "project_name": project["name"],
                    "matched_agents": matched_agents,
                })
        return results


def _build_projects():
    return [
        {
            "name": "Alpha Dashboard",
            "agents": [
                {"name": "ReportGen", "output": "Monthly sales report PDF"},
                {"name": "DataSync", "output": "CSV export pipeline"},
            ],
        },
        {
            "name": "Beta Pipeline",
            "agents": [
                {"name": "ETLRunner", "output": "Kafka stream aggregation"},
            ],
        },
        {
            "name": "Gamma Notes",
            "agents": [
                {"name": "Summarizer", "output": "Meeting notes summary"},
                {"name": "Transcriber", "output": "Audio transcription result"},
            ],
        },
        {
            "name": "Delta Infra",
            "agents": [
                {"name": "DeployBot", "output": "Kubernetes deployment manifest"},
            ],
        },
    ]


def test_search_by_project_name_exact():
    service = MockSearchService(_build_projects())
    results = service.search("Alpha Dashboard")
    assert len(results) == 1
    assert results[0]["project_name"] == "Alpha Dashboard"


def test_search_by_project_name_fuzzy():
    service = MockSearchService(_build_projects())
    results = service.search("alpha")
    assert len(results) == 1
    assert results[0]["project_name"] == "Alpha Dashboard"


def test_search_by_agent_output_keyword():
    service = MockSearchService(_build_projects())
    results = service.search("Kafka")
    assert len(results) == 1
    assert results[0]["project_name"] == "Beta Pipeline"
    assert len(results[0]["matched_agents"]) == 1
    assert results[0]["matched_agents"][0]["name"] == "ETLRunner"


def test_search_by_agent_name_keyword():
    service = MockSearchService(_build_projects())
    results = service.search("summarizer")
    assert len(results) == 1
    assert results[0]["project_name"] == "Gamma Notes"


def test_search_returns_multiple_matches():
    service = MockSearchService(_build_projects())
    results = service.search("report")
    matching_projects = {r["project_name"] for r in results}
    assert "Alpha Dashboard" in matching_projects


def test_search_case_insensitive():
    service = MockSearchService(_build_projects())
    results_upper = service.search("GAMMA")
    results_lower = service.search("gamma")
    assert len(results_upper) == len(results_lower) == 1


def test_search_no_match_returns_empty():
    service = MockSearchService(_build_projects())
    results = service.search("zzzznotexist")
    assert results == []


def test_search_performance_under_500ms():
    large_projects = [
        {
            "name": f"Project-{i}",
            "agents": [
                {"name": f"Agent-{i}-{j}", "output": f"Output for project {i} agent {j}"}
                for j in range(50)
            ],
        }
        for i in range(200)
    ]
    service = MockSearchService(large_projects)
    start = time.perf_counter()
    service.search("project-100")
    elapsed_ms = (time.perf_counter() - start) * 1000
    assert elapsed_ms < 500, f"Search took {elapsed_ms:.1f}ms, exceeds 500ms limit"


def test_search_returns_matched_agent_details():
    service = MockSearchService(_build_projects())
    results = service.search("transcription")
    assert len(results) == 1
    agent = results[0]["matched_agents"][0]
    assert agent["name"] == "Transcriber"
    assert "transcription" in agent["output"].lower()


def test_search_project_match_without_agent_match_includes_empty_agents():
    service = MockSearchService(_build_projects())
    results = service.search("delta infra")
    assert len(results) == 1
    assert results[0]["project_name"] == "Delta Infra"
    assert results[0]["matched_agents"] == []
