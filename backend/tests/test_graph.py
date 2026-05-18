#!/usr/bin/env python3
"""
DevFlow 项目管理平台 - DAG 图工具单元测试
测试循环检测、拓扑排序、路径查找等核心图算法
"""

import pytest
import sys
import os

sys.path.insert(0, os.path.dirname(os.path.dirname(os.path.abspath(__file__))))

from app.utils.graph import has_cycle, topological_sort, find_all_paths, detect_cycle_in_tasks


class TestHasCycle:
    """测试 has_cycle 函数 - DFS 有向图循环检测"""

    def test_empty_graph_no_cycle(self):
        """空图不应检测到循环"""
        assert has_cycle({}) is False

    def test_single_node_no_cycle(self):
        """单节点无出边不应有循环"""
        assert has_cycle({"A": []}) is False

    def test_simple_linear_no_cycle(self):
        """线性结构 A->B->C 不应有循环"""
        adj = {
            "A": ["B"],
            "B": ["C"],
            "C": [],
        }
        assert has_cycle(adj) is False

    def test_simple_cycle(self):
        """A->B->A 循环"""
        adj = {
            "A": ["B"],
            "B": ["A"],
        }
        assert has_cycle(adj) is True

    def test_three_node_cycle(self):
        """A->B->C->A 循环"""
        adj = {
            "A": ["B"],
            "B": ["C"],
            "C": ["A"],
        }
        assert has_cycle(adj) is True

    def test_diamond_no_cycle(self):
        """菱形结构 A->B, A->C, B->D, C->D 不应有循环"""
        adj = {
            "A": ["B", "C"],
            "B": ["D"],
            "C": ["D"],
            "D": [],
        }
        assert has_cycle(adj) is False

    def test_partial_cycle(self):
        """部分节点有循环"""
        # A->B->C->A 循环，D 是孤立的
        adj = {
            "A": ["B"],
            "B": ["C"],
            "C": ["A"],
            "D": [],
        }
        assert has_cycle(adj) is True

    def test_self_loop(self):
        """自环 A->A 应检测到循环"""
        adj = {"A": ["A"]}
        assert has_cycle(adj) is True

    def test_complex_dag_no_cycle(self):
        """复杂 DAG 不应有循环"""
        adj = {
            "A": ["B", "C"],
            "B": ["D", "E"],
            "C": ["E"],
            "D": ["F"],
            "E": ["F"],
            "F": [],
        }
        assert has_cycle(adj) is False

    def test_disconnected_components_with_cycle(self):
        """多个连通分量，其中一个有循环"""
        adj = {
            "A": ["B"],
            "B": ["A"],
            "C": ["D"],
            "D": [],
        }
        assert has_cycle(adj) is True


class TestTopologicalSort:
    """测试 topological_sort 函数 - Kahn 算法拓扑排序"""

    def test_empty_graph(self):
        """空图的拓扑排序结果为空列表"""
        assert topological_sort({}) == []

    def test_single_node(self):
        """单节点的拓扑排序"""
        result = topological_sort({"A": []})
        assert result == ["A"]

    def test_linear_chain(self):
        """线性链 A->B->C 的拓扑排序"""
        adj = {
            "A": ["B"],
            "B": ["C"],
            "C": [],
        }
        result = topological_sort(adj)
        # 验证相对顺序: A 在 B 之前，B 在 C 之前
        assert result.index("A") < result.index("B")
        assert result.index("B") < result.index("C")

    def test_diamond(self):
        """菱形结构的拓扑排序"""
        adj = {
            "A": ["B", "C"],
            "B": ["D"],
            "C": ["D"],
            "D": [],
        }
        result = topological_sort(adj)
        assert result.index("A") < result.index("B")
        assert result.index("A") < result.index("C")
        assert result.index("B") < result.index("D")
        assert result.index("C") < result.index("D")

    def test_complex_dag(self):
        """复杂 DAG 的拓扑排序"""
        adj = {
            "A": ["B", "C"],
            "B": ["D"],
            "C": ["D", "E"],
            "D": ["F"],
            "E": ["F"],
            "F": [],
        }
        result = topological_sort(adj)
        # 验证所有边的源节点在目标节点之前
        for node, neighbors in adj.items():
            for neighbor in neighbors:
                assert result.index(node) < result.index(neighbor), \
                    f"拓扑顺序错误: {node} (idx {result.index(node)}) 应在 {neighbor} (idx {result.index(neighbor)}) 之前"

    def test_multiple_roots(self):
        """多个根节点"""
        adj = {
            "A": ["C"],
            "B": ["C"],
            "C": [],
        }
        result = topological_sort(adj)
        # A 和 B 都应在 C 之前，A 和 B 的相对顺序不固定
        assert result.index("C") > result.index("A") or result.index("C") > result.index("B")

    def test_all_results_consistent(self):
        """多次排序结果应都有效（即使顺序可能不同）"""
        adj = {
            "A": ["C", "D"],
            "B": ["C"],
            "C": ["E"],
            "D": ["E"],
            "E": [],
        }
        results = [topological_sort(adj) for _ in range(10)]
        for result in results:
            for node, neighbors in adj.items():
                for neighbor in neighbors:
                    assert result.index(node) < result.index(neighbor)


class TestFindAllPaths:
    """测试 find_all_paths 函数 - 查找所有路径"""

    def test_no_path(self):
        """不存在路径"""
        adj = {
            "A": ["B"],
            "B": [],
        }
        paths = find_all_paths(adj, "A", "C")
        assert paths == []

    def test_single_path(self):
        """只有一条路径"""
        adj = {
            "A": ["B"],
            "B": ["C"],
        }
        paths = find_all_paths(adj, "A", "C")
        assert paths == [["A", "B", "C"]]

    def test_multiple_paths(self):
        """多条路径"""
        adj = {
            "A": ["B", "C"],
            "B": ["D"],
            "C": ["D"],
        }
        paths = find_all_paths(adj, "A", "D")
        assert len(paths) == 2
        assert ["A", "B", "D"] in paths
        assert ["A", "C", "D"] in paths

    def test_no_start_end(self):
        """起点等于终点"""
        adj = {"A": ["B"], "B": []}
        paths = find_all_paths(adj, "A", "A")
        # 起点等于终点时，路径包含单个节点 [A]
        assert paths == [["A"]]

    def test_path_with_branches(self):
        """分支结构"""
        adj = {
            "A": ["B", "C"],
            "B": ["C", "D"],
            "C": ["D"],
            "D": [],
        }
        paths = find_all_paths(adj, "A", "D")
        # A->B->D, A->B->C->D, A->C->D
        assert len(paths) == 3

    def test_disconnected_nodes(self):
        """不连通节点"""
        adj = {
            "A": ["B"],
            "B": [],
            "C": ["D"],
            "D": [],
        }
        paths = find_all_paths(adj, "A", "D")
        assert paths == []


class TestDetectCycleInTasks:
    """测试 detect_cycle_in_tasks 函数 - 从边列表检测循环"""

    def test_no_edges(self):
        """空边列表"""
        assert detect_cycle_in_tasks([]) is False

    def test_single_edge(self):
        """单条边"""
        assert detect_cycle_in_tasks([("A", "B")]) is False

    def test_two_node_cycle(self):
        """A->B, B->A 循环"""
        edges = [("A", "B"), ("B", "A")]
        assert detect_cycle_in_tasks(edges) is True

    def test_three_node_cycle(self):
        """A->B->C->A 循环"""
        edges = [("A", "B"), ("B", "C"), ("C", "A")]
        assert detect_cycle_in_tasks(edges) is True

    def test_linear_edges(self):
        """线性边列表"""
        edges = [("A", "B"), ("B", "C"), ("C", "D")]
        assert detect_cycle_in_tasks(edges) is False

    def test_partial_cycle(self):
        """部分边形成循环"""
        edges = [("A", "B"), ("B", "C"), ("C", "A"), ("D", "E")]
        assert detect_cycle_in_tasks(edges) is True

    def test_duplicate_edges(self):
        """重复边"""
        edges = [("A", "B"), ("A", "B"), ("B", "C")]
        assert detect_cycle_in_tasks(edges) is False

    def test_complex_task_dependency(self):
        """复杂任务依赖（无循环）"""
        edges = [
            ("task_1", "task_2"),
            ("task_1", "task_3"),
            ("task_2", "task_4"),
            ("task_3", "task_4"),
            ("task_4", "task_5"),
        ]
        assert detect_cycle_in_tasks(edges) is False

    def test_complex_task_dependency_with_cycle(self):
        """复杂任务依赖（有循环）"""
        edges = [
            ("task_1", "task_2"),
            ("task_2", "task_3"),
            ("task_3", "task_1"),  # 循环!
            ("task_2", "task_4"),
        ]
        assert detect_cycle_in_tasks(edges) is True

    def test_disconnected_with_cycle(self):
        """断开图的循环检测"""
        # A->B->A 循环, C->D 无循环
        edges = [("A", "B"), ("B", "A"), ("C", "D")]
        assert detect_cycle_in_tasks(edges) is True

    def test_four_node_cycle(self):
        """四节点循环"""
        edges = [("A", "B"), ("B", "C"), ("C", "D"), ("D", "A")]
        assert detect_cycle_in_tasks(edges) is True

    def test_multiple_independent_cycles(self):
        """多个独立循环"""
        edges = [("A", "B"), ("B", "A"), ("C", "D"), ("D", "C")]
        assert detect_cycle_in_tasks(edges) is True
