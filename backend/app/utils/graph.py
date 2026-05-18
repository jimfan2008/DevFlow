#!/usr/bin/env python3
"""DAG 工具 - 循环检测、拓扑排序"""


def has_cycle(adjacency: dict) -> bool:
    """使用 DFS 检测有向图中的循环"""
    WHITE, GRAY, BLACK = 0, 1, 2
    color = {node: WHITE for node in adjacency}

    def dfs(node):
        color[node] = GRAY
        for neighbor in adjacency.get(node, []):
            if color.get(neighbor, WHITE) == GRAY:
                return True
            if color.get(neighbor, WHITE) == WHITE and dfs(neighbor):
                return True
        color[node] = BLACK
        return False

    for node in adjacency:
        if color[node] == WHITE:
            if dfs(node):
                return True
    return False


def topological_sort(adjacency: dict) -> list:
    """拓扑排序（Kahn 算法）"""
    in_degree = {node: 0 for node in adjacency}
    for node in adjacency:
        for neighbor in adjacency[node]:
            in_degree[neighbor] = in_degree.get(neighbor, 0) + 1
    queue = [node for node in in_degree if in_degree[node] == 0]
    result = []
    while queue:
        node = queue.pop(0)
        result.append(node)
        for neighbor in adjacency.get(node, []):
            in_degree[neighbor] -= 1
            if in_degree[neighbor] == 0:
                queue.append(neighbor)
    return result


def find_all_paths(adjacency: dict, start: str, end: str) -> list:
    """查找两个节点之间的所有路径"""
    paths = []
    stack = [(start, [start])]
    while stack:
        node, path = stack.pop()
        if node == end:
            paths.append(path)
            continue
        for neighbor in adjacency.get(node, []):
            if neighbor not in path:
                stack.append((neighbor, path + [neighbor]))
    return paths


def detect_cycle_in_tasks(edges: list) -> bool:
    """从边列表检测任务依赖循环"""
    adjacency = {}
    for source, target in edges:
        adjacency.setdefault(source, [])
        adjacency[source].append(target)
    return has_cycle(adjacency)
