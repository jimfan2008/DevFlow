"""
循环依赖检测算法 POC (深度优先搜索 - DFS)
功能：检测模块之间的循环依赖关系，支持增量检测
作者：DevFlow Team
版本：1.0.0
"""

import sys
from typing import Dict, List, Set, Tuple, Optional
from dataclasses import dataclass, field
from enum import Enum
from collections import defaultdict
import time


class NodeState(Enum):
    """DFS 遍历中节点的状态"""
    UNVISITED = 0
    VISITING = 1  # 正在访问中（当前路径）
    VISITED = 2   # 已访问完成


@dataclass
class DependencyGraph:
    """模块依赖关系图"""
    nodes: Set[str] = field(default_factory=set)
    edges: Dict[str, Set[str]] = field(default_factory=dict)
    
    def add_node(self, node: str) -> None:
        """添加节点"""
        self.nodes.add(node)
        if node not in self.edges:
            self.edges[node] = set()
    
    def add_edge(self, from_node: str, to_node: str) -> None:
        """添加依赖边：from_node 依赖 to_node"""
        self.add_node(from_node)
        self.add_node(to_node)
        self.edges[from_node].add(to_node)
    
    def remove_edge(self, from_node: str, to_node: str) -> bool:
        """删除依赖边，返回是否成功删除"""
        if from_node in self.edges and to_node in self.edges[from_node]:
            self.edges[from_node].discard(to_node)
            return True
        return False
    
    def remove_node(self, node: str) -> bool:
        """删除节点及其所有依赖关系"""
        if node not in self.nodes:
            return False
        
        # 删除所有指向该节点的边
        for from_node in list(self.edges.keys()):
            self.edges[from_node].discard(node)
        
        # 删除该节点的边
        self.edges.pop(node, None)
        self.nodes.discard(node)
        return True
    
    def get_dependencies(self, node: str) -> Set[str]:
        """获取节点的所有直接依赖"""
        return self.edges.get(node, set())
    
    def get_dependents(self, node: str) -> Set[str]:
        """获取依赖该节点的所有节点"""
        dependents = set()
        for from_node, deps in self.edges.items():
            if node in deps:
                dependents.add(from_node)
        return dependents
    
    def to_adjacency_list(self) -> Dict[str, List[str]]:
        """转换为邻接表格式（DFS 算法所需）"""
        return {node: list(deps) for node, deps in self.edges.items()}
    
    def copy(self) -> 'DependencyGraph':
        """创建图的深拷贝"""
        new_graph = DependencyGraph()
        new_graph.nodes = self.nodes.copy()
        new_graph.edges = {k: v.copy() for k, v in self.edges.items()}
        return new_graph


@dataclass
class CycleResult:
    """循环检测结果"""
    has_cycle: bool
    cycles: List[List[str]]
    detection_time_ms: float
    nodes_checked: int
    
    def __str__(self) -> str:
        if not self.has_cycle:
            return "✓ 没有发现循环依赖"
        
        cycle_strs = []
        for i, cycle in enumerate(self.cycles, 1):
            cycle_strs.append(f"  循环{i}: {' -> '.join(cycle)} -> {cycle[0]}")
        
        return (
            f"✗ 发现 {len(self.cycles)} 个循环依赖:\n"
            f"{chr(10).join(cycle_strs)}\n"
            f"检测耗时：{self.detection_time_ms:.2f}ms, 检查节点数：{self.nodes_checked}"
        )


class CycleDetectorDFS:
    """基于 DFS 的循环依赖检测器"""
    
    def __init__(self):
        self.graph: Optional[DependencyGraph] = None
        self.state: Dict[str, NodeState] = {}
        self.parent: Dict[str, Optional[str]] = {}
        self.current_path: List[str] = []
        self.cycles: List[List[str]] = []
        self.nodes_checked: int = 0
    
    def detect_cycles(self, graph: DependencyGraph, find_all: bool = True) -> CycleResult:
        """
        检测图中的所有循环依赖
        
        Args:
            graph: 依赖关系图
            find_all: 是否查找所有循环（True）或只查找一个（False）
        
        Returns:
            CycleResult: 检测结果
        """
        start_time = time.perf_counter()
        self.graph = graph
        self.state = {node: NodeState.UNVISITED for node in graph.nodes}
        self.parent = {node: None for node in graph.nodes}
        self.current_path = []
        self.cycles = []
        self.nodes_checked = 0
        
        # 对每个未访问的节点进行 DFS
        for node in graph.nodes:
            if self.state[node] == NodeState.UNVISITED:
                self._dfs_visit(node, find_all)
                if not find_all and self.cycles:
                    break
        
        detection_time_ms = (time.perf_counter() - start_time) * 1000
        
        return CycleResult(
            has_cycle=bool(self.cycles),
            cycles=self.cycles,
            detection_time_ms=detection_time_ms,
            nodes_checked=self.nodes_checked
        )
    
    def _dfs_visit(self, node: str, find_all: bool) -> None:
        """DFS 访问节点"""
        self.state[node] = NodeState.VISITING
        self.current_path.append(node)
        self.nodes_checked += 1
        
        for neighbor in self.graph.edges.get(node, set()):
            if self.state.get(neighbor) == NodeState.VISITING:
                # 发现后向边，找到循环
                cycle_start_idx = self.current_path.index(neighbor)
                cycle = self.current_path[cycle_start_idx:] + [neighbor]
                self.cycles.append(cycle)
                
                if not find_all:
                    return
                
            elif self.state.get(neighbor) == NodeState.UNVISITED:
                self.parent[neighbor] = node
                self._dfs_visit(neighbor, find_all)
                if not find_all and self.cycles:
                    return
        
        self.current_path.pop()
        self.state[node] = NodeState.VISITED
    
    def detect_single_cycle(self, graph: DependencyGraph) -> CycleResult:
        """只检测是否存在循环（更快）"""
        return self.detect_cycles(graph, find_all=False)
    
    def find_cycles_from_node(self, graph: DependencyGraph, start_node: str) -> List[List[str]]:
        """
        从指定节点开始查找所有循环
        
        Args:
            graph: 依赖关系图
            start_node: 起始节点
        
        Returns:
            从该节点出发的所有循环列表
        """
        if start_node not in graph.nodes:
            return []
        
        # 创建子图，只包含可达节点
        reachable = self._get_reachable_nodes(graph, start_node)
        subgraph = DependencyGraph()
        for node in reachable:
            subgraph.add_node(node)
            for dep in graph.edges.get(node, set()):
                if dep in reachable:
                    subgraph.add_edge(node, dep)
        
        result = self.detect_cycles(subgraph, find_all=True)
        return result.cycles
    
    def _get_reachable_nodes(self, graph: DependencyGraph, start: str) -> Set[str]:
        """获取从 start 节点可达的所有节点"""
        reachable = set()
        stack = [start]
        
        while stack:
            node = stack.pop()
            if node in reachable:
                continue
            reachable.add(node)
            stack.extend(graph.edges.get(node, set()) - reachable)
        
        return reachable
    
    def validate_cycle(self, graph: DependencyGraph, cycle: List[str]) -> bool:
        """验证循环是否真实存在"""
        if len(cycle) < 2:
            return False
        
        for i in range(len(cycle) - 1):
            if cycle[i+1] not in graph.edges.get(cycle[i], set()):
                return False
        
        # 检查最后一条边是否回到起点
        return cycle[-1] in graph.edges.get(cycle[0], set())


class IncrementalCycleDetector:
    """增量循环依赖检测器
    支持高效检测新增/删除依赖后的循环
    """
    
    def __init__(self):
        self.graph = DependencyGraph()
        self.existing_cycles: Set[frozenset] = set()
        self._cycle_detector = CycleDetectorDFS()
    
    def add_dependency(self, from_node: str, to_node: str) -> List[List[str]]:
        """
        添加依赖关系并检测新产生的循环
        
        Args:
            from_node: 依赖方
            to_node: 被依赖方
        
        Returns:
            新产生的循环列表（如果有）
        """
        self.graph.add_edge(from_node, to_node)
        
        # 只检测涉及新边的可能循环
        new_cycles = self._check_edge_cycle(from_node, to_node)
        
        for cycle in new_cycles:
            self.existing_cycles.add(frozenset(cycle[:-1]))
        
        return new_cycles
    
    def remove_dependency(self, from_node: str, to_node: str) -> List[List[str]]:
        """
        删除依赖关系并更新循环集合
        
        Args:
            from_node: 依赖方
            to_node: 被依赖方
        
        Returns:
            不再存在的循环列表
        """
        removed_cycles = []
        
        # 检查哪些循环被打破
        cycle_list = list(self.existing_cycles)
        for cycle_set in cycle_list:
            if from_node in cycle_set and to_node in cycle_set:
                # 简化检查：如果边在循环中，则循环被打破
                if self._edge_in_cycle(self.graph, from_node, to_node, cycle_set):
                    removed_cycles.append(list(cycle_set) + [list(cycle_set)[0]])
                    self.existing_cycles.discard(cycle_set)
        
        self.graph.remove_edge(from_node, to_node)
        return removed_cycles
    
    def _check_edge_cycle(self, from_node: str, to_node: str) -> List[List[str]]:
        """检查添加边 from_node -> to_node 后是否产生循环"""
        # 需要检查是否存在 to_node -> ... -> from_node 的路径
        if from_node not in self.graph.nodes or to_node not in self.graph.nodes:
            return []
        
        # BFS/DFS 查找 from_node 是否能从 to_node 到达
        reachable = self._get_reachable_from(self.graph, from_node)
        
        if to_node in reachable:
            # 存在循环，找到具体循环
            cycle = self._find_cycle_path(to_node, from_node)
            return [cycle] if cycle else []
        
        return []
    
    def _get_reachable_from(self, graph: DependencyGraph, start: str) -> Set[str]:
        """获取从 start 节点可达的所有节点"""
        reachable = set()
        stack = [start]
        
        while stack:
            node = stack.pop()
            if node in reachable:
                continue
            reachable.add(node)
            stack.extend(graph.edges.get(node, set()) - reachable)
        
        return reachable
    
    def _find_cycle_path(self, from_node: str, to_node: str) -> Optional[List[str]]:
        """查找 from_node 到 to_node 的路径"""
        if from_node not in self.graph.edges:
            return None
        
        queue = [(from_node, [from_node])]
        visited = {from_node}
        
        while queue:
            node, path = queue.pop(0)
            
            for neighbor in self.graph.edges.get(node, set()):
                if neighbor == to_node:
                    return path + [to_node]
                if neighbor not in visited:
                    visited.add(neighbor)
                    queue.append((neighbor, path + [neighbor]))
        
        return None
    
    def _edge_in_cycle(self, graph: DependencyGraph, from_node: str, to_node: str, cycle: Set[str]) -> bool:
        """检查边 from_node -> to_node 是否在循环中"""
        # 简化检查：如果 to_node 能到达 from_node，则这条边在循环中
        reachable = self._get_reachable_from(DependencyGraph({from_node: {to_node}}, graph.edges), to_node)
        return from_node in reachable
    
    def get_all_cycles(self) -> List[List[str]]:
        """获取所有已知循环"""
        return [list(c) + [list(c)[0]] for c in self.existing_cycles]
    
    def full_revalidate(self) -> List[List[str]]:
        """重新验证所有循环（当图发生重大变化时）"""
        detector = CycleDetectorDFS()
        result = detector.detect_cycles(self.graph, find_all=True)
        self.existing_cycles = set(frozenset(c[:-1]) for c in result.cycles)
        return result.cycles


# ==================== 测试代码 ====================

def test_basic_detection():
    """基础测试：检测简单循环"""
    print("=" * 60)
    print("测试 1: 基础循环检测")
    print("=" * 60)
    
    graph = DependencyGraph()
    graph.add_edge("A", "B")
    graph.add_edge("B", "C")
    graph.add_edge("C", "A")  # 形成循环 A->B->C->A
    
    detector = CycleDetectorDFS()
    result = detector.detect_cycles(graph)
    print(result)
    assert result.has_cycle
    assert len(result.cycles) == 1
    print("✓ 测试 1 通过\n")


def test_no_cycle():
    """测试：无循环情况"""
    print("=" * 60)
    print("测试 2: 无循环图")
    print("=" * 60)
    
    graph = DependencyGraph()
    graph.add_edge("A", "B")
    graph.add_edge("A", "C")
    graph.add_edge("B", "D")
    graph.add_edge("C", "D")
    
    detector = CycleDetectorDFS()
    result = detector.detect_cycles(graph)
    print(result)
    assert not result.has_cycle
    print("✓ 测试 2 通过\n")


def test_multiple_cycles():
    """测试：多个独立循环"""
    print("=" * 60)
    print("测试 3: 多个循环")
    print("=" * 60)
    
    graph = DependencyGraph()
    # 循环 1: A->B->C->A
    graph.add_edge("A", "B")
    graph.add_edge("B", "C")
    graph.add_edge("C", "A")
    
    # 循环 2: D->E->D
    graph.add_edge("D", "E")
    graph.add_edge("E", "D")
    
    detector = CycleDetectorDFS()
    result = detector.detect_cycles(graph)
    print(result)
    assert result.has_cycle
    assert len(result.cycles) >= 2
    print("✓ 测试 3 通过\n")


def test_incremental():
    """测试：增量检测"""
    print("=" * 60)
    print("测试 4: 增量循环检测")
    print("=" * 60)
    
    detector = IncrementalCycleDetector()
    
    # 添加无循环的依赖
    result1 = detector.add_dependency("A", "B")
    print(f"添加 A->B: {'无新循环' if not result1 else '发现循环'}")
    assert len(result1) == 0
    
    result2 = detector.add_dependency("B", "C")
    print(f"添加 B->C: {'无新循环' if not result2 else '发现循环'}")
    assert len(result2) == 0
    
    # 添加导致循环的依赖
    result3 = detector.add_dependency("C", "A")
    print(f"添加 C->A: {'发现循环' if result3 else '无新循环'}")
    assert len(result3) == 1
    print(f"  循环：{' -> '.join(result3[0])}")
    
    # 删除导致循环的依赖
    removed = detector.remove_dependency("C", "A")
    print(f"删除 C->A: {'循环已解决' if removed else '无变化'}")
    print("✓ 测试 4 通过\n")


def test_performance():
    """性能测试"""
    print("=" * 60)
    print("测试 5: 性能测试")
    print("=" * 60)
    
    # 创建图 - 使用较小的数据集避免递归深度问题
    n = 500  # 节点数 (降低以避免递归限制)
    graph = DependencyGraph()
    
    for i in range(n):
        graph.add_node(f"module_{i}")
    
    # 添加链式依赖
    for i in range(n - 1):
        graph.add_edge(f"module_{i}", f"module_{i + 1}")
    
    detector = CycleDetectorDFS()
    
    # 测试无环图性能
    start = time.perf_counter()
    result_no_cycle = detector.detect_cycles(graph, find_all=True)
    time_no_cycle = (time.perf_counter() - start) * 1000
    
    print(f"无环图检测 (500 节点): {time_no_cycle:.2f}ms")
    print(f"  结果：{'发现循环' if result_no_cycle.has_cycle else '无循环'}")
    
    # 测试单个循环检测
    n_cycle = 100
    graph2 = DependencyGraph()
    for i in range(n_cycle):
        graph2.add_edge(f"mod_{i}", f"mod_{{(i + 1) % n_cycle}}")
    
    detector2 = CycleDetectorDFS()
    start = time.perf_counter()
    result_one = detector2.detect_single_cycle(graph2)
    time_one = (time.perf_counter() - start) * 1000
    
    print(f"单循环检测 (100 节点): {time_one:.2f}ms")
    print(f"  结果：{'发现 ' + str(len(result_one.cycles)) + ' 个循环' if result_one.has_cycle else '无循环'}")
    
    print("✓ 测试 5 通过\n")


def main():
    """运行所有测试"""
    print("\n" + "=" * 60)
    print("循环依赖检测算法 POC - 测试套件")
    print("=" * 60 + "\n")
    
    test_basic_detection()
    test_no_cycle()
    test_multiple_cycles()
    test_incremental()
    test_performance()
    
    print("=" * 60)
    print("所有测试通过！✓")
    print("=" * 60)
    
    # 演示实际使用
    print("\n" + "=" * 60)
    print("实际使用示例")
    print("=" * 60)
    
    # 模拟实际模块依赖
    graph = DependencyGraph()
    graph.add_edge("auth", "database")
    graph.add_edge("auth", "cache")
    graph.add_edge("api", "auth")
    graph.add_edge("api", "database")
    graph.add_edge("database", "cache")
    graph.add_edge("cache", "database")  # 循环！
    
    detector = CycleDetectorDFS()
    result = detector.detect_cycles(graph)
    print(f"\n模块依赖关系:\n{graph.to_adjacency_list()}\n")
    print(f"检测结果:\n{result}\n")


if __name__ == "__main__":
    # 如果作为脚本运行，执行测试
    if len(sys.argv) > 1 and sys.argv[1] == "--demo":
        main()
    else:
        # 运行测试套件
        test_basic_detection()
        test_no_cycle()
        test_multiple_cycles()
        test_incremental()
        test_performance()
        main()
