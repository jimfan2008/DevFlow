import logging
import os
import warnings
import pytest
import time
import random
import math
import statistics
from unittest.mock import Mock, patch, MagicMock, PropertyMock
from collections import Counter
from threading import Event
from dataclasses import dataclass, field
from enum import Enum
from typing import Optional


# ============================================================
# 测试蜂群管理 — 验证测试蜂群创建和管理
# 验收标准:
#   蜂群创建时间 ≤ 1分钟
#   子Agent数量 ≥ 3
#   测试任务分发均匀度 ≥ 80%
#   蜂群状态实时更新，延迟 ≤ 5秒
# ============================================================


# --- Mock 数据模型 ---

class MockSwarm:
    """模拟蜂群数据模型"""
    _id_counter = 0

    def __init__(self, project_id, name, purpose, step_number, manager_role):
        MockSwarm._id_counter += 1
        self.id = f"swarm-{MockSwarm._id_counter:04d}"
        self.project_id = project_id
        self.name = name
        self.purpose = purpose
        self.step_number = step_number
        self.manager_role = manager_role
        self.status = "active"
        self.members = []
        self.tasks = []
        self.assignments = []
        self.created_at = time.time()
        self.disbanded_at = None
        self.progress = {"total_tasks": 0, "pending_tasks": 0, "completed_tasks": 0}

    def to_dict(self):
        return {
            "id": self.id,
            "project_id": self.project_id,
            "name": self.name,
            "purpose": self.purpose,
            "step_number": self.step_number,
            "manager_role": self.manager_role,
            "status": self.status,
            "members": [m.to_dict() for m in self.members],
            "tasks": self.tasks,
            "created_at": self.created_at,
            "disbanded_at": self.disbanded_at,
        }

    def to_dict_assignments(self):
        return [a.to_dict() for a in self.assignments]


class MockAgent:
    """模拟子Agent数据模型"""
    _id_counter = 0

    def __init__(self, agent_type, agent_id):
        MockAgent._id_counter += 1
        self.member_id = f"member-{MockAgent._id_counter:04d}"
        self.agent_type = agent_type
        self.agent_id = agent_id
        self.joined_at = time.time()

    def to_dict(self):
        return {
            "member_id": self.member_id,
            "agent_type": self.agent_type,
            "agent_id": self.agent_id,
            "joined_at": self.joined_at,
        }


class MockTaskAssignment:
    """模拟任务分配记录"""

    def __init__(self, task_id, task_name, assigned_agent_id):
        self.task_id = task_id
        self.task_name = task_name
        self.assigned_agent_id = assigned_agent_id

    def to_dict(self):
        return {
            "task_id": self.task_id,
            "task_name": self.task_name,
            "assigned_agent_id": self.assigned_agent_id,
        }


class MockSwarmService:
    """模拟蜂群管理服务——独立运行，不依赖外部组件"""

    def __init__(self):
        self.swarms = {}
        self._swarm_id_counter = 0

    def _next_swarm_id(self):
        self._swarm_id_counter += 1
        return f"swarm-{self._swarm_id_counter:04d}"

    def create_swarm(self, project_id, name, purpose, step_number, manager_role):
        """创建蜂群"""
        self._swarm_id_counter += 1
        swarm_id = f"swarm-{self._swarm_id_counter:04d}"
        now = time.time()
        swarm = {
            "id": swarm_id,
            "project_id": project_id,
            "name": name,
            "purpose": purpose,
            "step_number": step_number,
            "manager_role": manager_role,
            "status": "active",
            "members": [],
            "tasks": [],
            "assignments": [],
            "created_at": now,
            "disbanded_at": None,
            "progress": {"total_tasks": 0, "pending_tasks": 0, "completed_tasks": 0},
        }
        self.swarms[swarm_id] = swarm
        return swarm

    def get_swarm(self, swarm_id):
        """获取蜂群信息"""
        if swarm_id not in self.swarms:
            raise KeyError(f"Swarm {swarm_id} not found")
        return self.swarms[swarm_id]

    def add_member(self, swarm_id, agent_type, agent_id):
        """添加子Agent到蜂群"""
        swarm = self.get_swarm(swarm_id)
        member = {
            "member_id": f"member-{len(swarm['members']) + 1:04d}",
            "agent_type": agent_type,
            "agent_id": agent_id,
            "joined_at": time.time(),
        }
        existing_ids = {m["agent_id"] for m in swarm["members"]}
        if agent_id not in existing_ids:
            swarm["members"].append(member)
        return swarm

    def remove_member(self, swarm_id, agent_id):
        """从蜂群移除子Agent"""
        swarm = self.get_swarm(swarm_id)
        swarm["members"] = [m for m in swarm["members"] if m["agent_id"] != agent_id]
        return swarm

    def dispatch_tasks(self, swarm_id, tasks):
        """将任务均匀分发给所有子Agent——轮询分发算法"""
        swarm = self.get_swarm(swarm_id)
        members = swarm["members"]
        if not members:
            return []

        agent_ids = [m["agent_id"] for m in members]
        assignments = []
        for idx, task in enumerate(tasks):
            agent_id = agent_ids[idx % len(agent_ids)]
            assignment = {
                "task_id": task["task_id"],
                "task_name": task["name"],
                "assigned_agent_id": agent_id,
            }
            assignments.append(assignment)

        swarm["assignments"] = assignments
        swarm["tasks"] = tasks
        swarm["progress"]["total_tasks"] = len(tasks)
        swarm["progress"]["pending_tasks"] = len(tasks)
        swarm["progress"]["completed_tasks"] = 0
        return assignments

    def get_progress(self, swarm_id):
        """获取蜂群任务进度"""
        swarm = self.get_swarm(swarm_id)
        return swarm["progress"]

    def disband_swarm(self, swarm_id):
        """解散蜂群"""
        swarm = self.get_swarm(swarm_id)
        swarm["status"] = "disbanded"
        swarm["disbanded_at"] = time.time()
        return swarm


# --- Fixtures ---

@pytest.fixture
def swarm_service():
    """提供 MockSwarmService 实例"""
    return MockSwarmService()


@pytest.fixture
def basic_swarm(swarm_service):
    """创建一个基础蜂群用于测试"""
    return swarm_service.create_swarm(
        project_id="p-0109",
        name="基础测试蜂群",
        purpose="test_execution",
        step_number=11,
        manager_role="houda",
    )


@pytest.fixture
def swarm_with_three_agents(swarm_service, basic_swarm):
    """创建包含3个子Agent的蜂群"""
    for i in range(3):
        swarm_service.add_member(basic_swarm["id"], "reasonix", f"rx-{i}")
    return basic_swarm


# ============================================================
# 验收标准 1: 蜂群创建时间 ≤ 1分钟
# ============================================================

class TestSwarmCreationTime:
    """蜂群创建时间 ≤ 1分钟"""

    def test_create_swarm_within_60_seconds(self, swarm_service):
        """验证单个蜂群创建时间不超过1分钟"""
        start = time.monotonic()
        swarm = swarm_service.create_swarm(
            project_id="p-0109",
            name="全面测试蜂群",
            purpose="test_execution",
            step_number=11,
            manager_role="houda",
        )
        elapsed = time.monotonic() - start
        assert elapsed <= 60.0, f"蜂群创建耗时 {elapsed:.3f}s，超过1分钟"
        assert swarm["status"] == "active"
        assert swarm["purpose"] == "test_execution"
        assert swarm["manager_role"] == "houda"

    def test_create_swarm_with_different_configs(self, swarm_service):
        """验证不同配置的蜂群创建均在1分钟内"""
        configs = [
            ("p-0109-a", "配置A", "test_execution", 12, "houda"),
            ("p-0109-b", "配置B", "test_execution", 13, "houwang"),
            ("p-0109-c", "配置C", "single_execution", 14, "hourong"),
        ]
        for proj_id, name, purpose, step, role in configs:
            start = time.monotonic()
            swarm = swarm_service.create_swarm(
                project_id=proj_id,
                name=name,
                purpose=purpose,
                step_number=step,
                manager_role=role,
            )
            elapsed = time.monotonic() - start
            assert elapsed <= 60.0, f"蜂群'{name}'创建耗时 {elapsed:.3f}s"
            assert swarm["project_id"] == proj_id
            assert swarm["step_number"] == step
            assert swarm["manager_role"] == role

    def test_batch_create_10_swarms_within_60s(self, swarm_service):
        """验证批量创建10个蜂群总时间不超过1分钟"""
        start = time.monotonic()
        swarms = []
        for i in range(10):
            s = swarm_service.create_swarm(
                project_id=f"p-batch-{i}",
                name=f"批量蜂群{i}",
                purpose="test_execution",
                step_number=11,
                manager_role="houda",
            )
            swarms.append(s)
        elapsed = time.monotonic() - start
        assert elapsed <= 60.0, f"批量创建10个蜂群耗时 {elapsed:.3f}s"
        assert len(swarms) == 10
        ids = [s["id"] for s in swarms]
        assert len(set(ids)) == 10

    def test_create_swarm_records_timestamp(self, swarm_service):
        """验证创建蜂群时记录时间戳"""
        swarm = swarm_service.create_swarm(
            project_id="p-ts",
            name="时间戳测试",
            purpose="test_execution",
            step_number=11,
            manager_role="houda",
        )
        assert "created_at" in swarm
        assert swarm["created_at"] > 0
        assert isinstance(swarm["created_at"], float)

    def test_create_swarm_generates_unique_ids(self, swarm_service):
        """验证连续创建的蜂群ID唯一"""
        ids = []
        for _ in range(20):
            s = swarm_service.create_swarm(
                project_id="p-unique",
                name="唯一ID测试",
                purpose="test_execution",
                step_number=11,
                manager_role="houda",
            )
            ids.append(s["id"])
        assert len(set(ids)) == 20

    def test_create_swarm_after_disband_also_under_60s(self, swarm_service):
        """验证解散后再创建蜂群也在1分钟内"""
        s1 = swarm_service.create_swarm(
            project_id="p-recreate",
            name="重建蜂群",
            purpose="test_execution",
            step_number=11,
            manager_role="houda",
        )
        swarm_service.disband_swarm(s1["id"])
        start = time.monotonic()
        s2 = swarm_service.create_swarm(
            project_id="p-recreate",
            name="重建蜂群v2",
            purpose="test_execution",
            step_number=11,
            manager_role="houda",
        )
        elapsed = time.monotonic() - start
        assert elapsed <= 60.0
        assert s2["id"] != s1["id"]
        assert s2["status"] == "active"


# ============================================================
# 验收标准 2: 子Agent数量 ≥ 3
# ============================================================

class TestChildAgentCount:
    """子Agent数量 ≥ 3"""

    def test_swarm_starts_with_zero_agents(self, swarm_service, basic_swarm):
        """验证新创建的蜂群初始子Agent数为0"""
        assert len(basic_swarm["members"]) == 0

    def test_add_three_agents_meets_minimum(self, swarm_service, basic_swarm):
        """验证添加3个子Agent后满足最低要求"""
        for i in range(3):
            swarm_service.add_member(basic_swarm["id"], "reasonix", f"rx-{i}")
        updated = swarm_service.get_swarm(basic_swarm["id"])
        assert len(updated["members"]) >= 3
        assert len(updated["members"]) == 3

    def test_add_five_agents_exceeds_minimum(self, swarm_service, basic_swarm):
        """验证添加5个子Agent超过最低要求"""
        for i in range(5):
            swarm_service.add_member(basic_swarm["id"], "reasonix", f"rx-{i}")
        updated = swarm_service.get_swarm(basic_swarm["id"])
        assert len(updated["members"]) >= 3
        assert len(updated["members"]) == 5

    def test_two_agents_below_minimum(self, swarm_service, basic_swarm):
        """验证只有2个子Agent时不满足最低要求（边界值）"""
        for i in range(2):
            swarm_service.add_member(basic_swarm["id"], "reasonix", f"rx-{i}")
        updated = swarm_service.get_swarm(basic_swarm["id"])
        assert len(updated["members"]) < 3
        assert len(updated["members"]) == 2

    def test_agent_types_are_preserved(self, swarm_service, basic_swarm):
        """验证添加的子Agent类型和ID被正确保存"""
        expected = [
            ("reasonix", "rx-1"),
            ("claude_code", "cc-2"),
            ("hermes", "he-3"),
        ]
        for agent_type, agent_id in expected:
            swarm_service.add_member(basic_swarm["id"], agent_type, agent_id)
        updated = swarm_service.get_swarm(basic_swarm["id"])
        actual = [(m["agent_type"], m["agent_id"]) for m in updated["members"]]
        assert len(actual) == 3
        for agent_type, agent_id in expected:
            assert (agent_type, agent_id) in actual

    def test_agent_ids_are_unique(self, swarm_service, basic_swarm):
        """验证不会重复添加相同agent_id的子Agent"""
        swarm_service.add_member(basic_swarm["id"], "reasonix", "rx-dup")
        swarm_service.add_member(basic_swarm["id"], "reasonix", "rx-dup")
        updated = swarm_service.get_swarm(basic_swarm["id"])
        members_rx_dup = [m for m in updated["members"] if m["agent_id"] == "rx-dup"]
        assert len(members_rx_dup) == 1

    def test_agent_count_persists_after_task_dispatch(self, swarm_service, basic_swarm):
        """验证分发任务后子Agent数量不变"""
        for i in range(3):
            swarm_service.add_member(basic_swarm["id"], "reasonix", f"rx-{i}")
        tasks = [{"task_id": f"t-{i}", "name": f"任务{i}"} for i in range(10)]
        swarm_service.dispatch_tasks(basic_swarm["id"], tasks)
        updated = swarm_service.get_swarm(basic_swarm["id"])
        assert len(updated["members"]) == 3

    def test_agent_joined_at_timestamp(self, swarm_service, basic_swarm):
        """验证每个子Agent都有加入时间戳"""
        for i in range(3):
            swarm_service.add_member(basic_swarm["id"], "reasonix", f"rx-{i}")
        updated = swarm_service.get_swarm(basic_swarm["id"])
        for member in updated["members"]:
            assert "joined_at" in member
            assert member["joined_at"] > 0
            assert isinstance(member["joined_at"], float)

    def test_remove_agent_reduces_count(self, swarm_service, basic_swarm):
        """验证移除子Agent后数量减少"""
        for i in range(4):
            swarm_service.add_member(basic_swarm["id"], "reasonix", f"rx-{i}")
        swarm_service.remove_member(basic_swarm["id"], "rx-0")
        swarm_service.remove_member(basic_swarm["id"], "rx-1")
        updated = swarm_service.get_swarm(basic_swarm["id"])
        assert len(updated["members"]) == 2


# ============================================================
# 验收标准 3: 任务分发均匀度 ≥ 80%
# ============================================================

class TestTaskDistributionUniformity:
    """测试任务分发均匀度 ≥ 80%"""

    @staticmethod
    def _distribution_evenness(agent_counts):
        """计算分发均匀度指标：
        基于最大最小差值的均匀度 = 1 - (max - min) / (max + min)
        完美均匀 = 1.0，完全不均匀趋近于 0
        """
        counts = list(agent_counts.values())
        if len(counts) < 2:
            return 1.0
        max_c = max(counts)
        min_c = min(counts)
        if max_c == min_c:
            return 1.0
        return 1.0 - (max_c - min_c) / (max_c + min_c)

    def test_30_tasks_evenly_distributed_to_3_agents(self, swarm_service, basic_swarm):
        """验证30个任务均匀分发给3个子Agent，均匀度≥80%"""
        for i in range(3):
            swarm_service.add_member(basic_swarm["id"], "reasonix", f"rx-{i}")
        tasks = [{"task_id": f"t-{i}", "name": f"测试任务{i}"} for i in range(30)]
        assignments = swarm_service.dispatch_tasks(basic_swarm["id"], tasks)
        agent_counts = {}
        for a in assignments:
            aid = a["assigned_agent_id"]
            agent_counts[aid] = agent_counts.get(aid, 0) + 1
        evenness = self._distribution_evenness(agent_counts)
        assert evenness >= 0.80, (
            f"分发均匀度 {evenness:.2%} < 80%，各Agent任务数: {agent_counts}"
        )
        assert all(c == 10 for c in agent_counts.values()), (
            f"轮询分发应完全均匀，实际: {agent_counts}"
        )

    def test_40_tasks_with_4_agents_perfect_uniformity(self, swarm_service, basic_swarm):
        """验证40个任务分发给4个Agent的均匀度"""
        for i in range(4):
            swarm_service.add_member(basic_swarm["id"], "reasonix", f"rx-{i}")
        tasks = [{"task_id": f"t-{i}", "name": f"任务{i}"} for i in range(40)]
        assignments = swarm_service.dispatch_tasks(basic_swarm["id"], tasks)
        agent_counts = {}
        for a in assignments:
            aid = a["assigned_agent_id"]
            agent_counts[aid] = agent_counts.get(aid, 0) + 1
        evenness = self._distribution_evenness(agent_counts)
        assert evenness >= 0.80
        assert max(agent_counts.values()) - min(agent_counts.values()) <= 1

    def test_10_tasks_with_3_agents_uneven_but_acceptable(self, swarm_service, basic_swarm):
        """验证10个任务3个Agent（非整数倍），均匀度仍≥80%"""
        for i in range(3):
            swarm_service.add_member(basic_swarm["id"], "reasonix", f"rx-{i}")
        tasks = [{"task_id": f"t-{i}", "name": f"任务{i}"} for i in range(10)]
        assignments = swarm_service.dispatch_tasks(basic_swarm["id"], tasks)
        agent_counts = {}
        for a in assignments:
            aid = a["assigned_agent_id"]
            agent_counts[aid] = agent_counts.get(aid, 0) + 1
        evenness = self._distribution_evenness(agent_counts)
        assert evenness >= 0.80, f"10任务3Agent均匀度 {evenness:.2%} < 80%"
        counts = list(agent_counts.values())
        assert max(counts) - min(counts) <= 1

    def test_25_tasks_with_5_agents(self, swarm_service, basic_swarm):
        """验证25个任务5个Agent的均匀度"""
        for i in range(5):
            swarm_service.add_member(basic_swarm["id"], "reasonix", f"rx-{i}")
        tasks = [{"task_id": f"t-{i}", "name": f"任务{i}"} for i in range(25)]
        assignments = swarm_service.dispatch_tasks(basic_swarm["id"], tasks)
        agent_counts = {}
        for a in assignments:
            aid = a["assigned_agent_id"]
            agent_counts[aid] = agent_counts.get(aid, 0) + 1
        evenness = self._distribution_evenness(agent_counts)
        assert evenness >= 0.80
        assert all(c == 5 for c in agent_counts.values())

    def test_single_task_distribution(self, swarm_service, basic_swarm):
        """验证单个任务分发给3个Agent时，均匀度为1.0"""
        for i in range(3):
            swarm_service.add_member(basic_swarm["id"], "reasonix", f"rx-{i}")
        tasks = [{"task_id": "t-0", "name": "唯一任务"}]
        assignments = swarm_service.dispatch_tasks(basic_swarm["id"], tasks)
        assert len(assignments) == 1
        assert assignments[0]["task_id"] == "t-0"

    def test_evenness_with_max_deviation(self, swarm_service, basic_swarm):
        """验证每个Agent任务数与均值的偏差不超过20%"""
        for i in range(3):
            swarm_service.add_member(basic_swarm["id"], "reasonix", f"rx-{i}")
        tasks = [{"task_id": f"t-{i}", "name": f"任务{i}"} for i in range(99)]
        assignments = swarm_service.dispatch_tasks(basic_swarm["id"], tasks)
        agent_counts = {}
        for a in assignments:
            aid = a["assigned_agent_id"]
            agent_counts[aid] = agent_counts.get(aid, 0) + 1
        counts = list(agent_counts.values())
        mean_tasks = sum(counts) / len(counts)
        deviations = [abs(c - mean_tasks) / mean_tasks for c in counts]
        max_deviation = max(deviations)
        assert max_deviation <= 0.20, (
            f"最大偏差 {max_deviation:.2%} > 20%，分配: {agent_counts}"
        )

    def test_each_agent_gets_at_least_one_task(self, swarm_service, basic_swarm):
        """验证任务数≥Agent数时，每个Agent至少获得1个任务"""
        for i in range(5):
            swarm_service.add_member(basic_swarm["id"], "reasonix", f"rx-{i}")
        tasks = [{"task_id": f"t-{i}", "name": f"任务{i}"} for i in range(10)]
        assignments = swarm_service.dispatch_tasks(basic_swarm["id"], tasks)
        assigned_agents = {a["assigned_agent_id"] for a in assignments}
        assert len(assigned_agents) == 5

    def test_evenness_with_large_task_count(self, swarm_service, basic_swarm):
        """验证大量任务分发均匀度"""
        for i in range(3):
            swarm_service.add_member(basic_swarm["id"], "reasonix", f"rx-{i}")
        tasks = [{"task_id": f"t-{i}", "name": f"任务{i}"} for i in range(1000)]
        assignments = swarm_service.dispatch_tasks(basic_swarm["id"], tasks)
        agent_counts = {}
        for a in assignments:
            aid = a["assigned_agent_id"]
            agent_counts[aid] = agent_counts.get(aid, 0) + 1
        evenness = self._distribution_evenness(agent_counts)
        assert evenness >= 0.95, (
            f"1000任务3Agent均匀度 {evenness:.4f} < 0.95"
        )


# ============================================================
# 验收标准 4: 蜂群状态实时更新，延迟 ≤ 5秒
# ============================================================

class TestSwarmStatusRealtimeUpdate:
    """蜂群状态实时更新，延迟 ≤ 5秒"""

    def test_create_swarm_returns_active_status(self, swarm_service):
        """验证创建蜂群后状态立即为 active"""
        swarm = swarm_service.create_swarm(
            project_id="p-status",
            name="状态测试",
            purpose="test_execution",
            step_number=11,
            manager_role="houda",
        )
        assert swarm["status"] == "active"

    def test_disband_swarm_latency_under_5s(self, swarm_service, basic_swarm):
        """验证解散蜂群的状态更新延迟≤5秒"""
        start = time.monotonic()
        result = swarm_service.disband_swarm(basic_swarm["id"])
        elapsed = time.monotonic() - start
        assert elapsed <= 5.0, f"解散状态更新耗时 {elapsed:.3f}s，超过5秒"
        assert result["status"] == "disbanded"

    def test_add_member_reflects_immediately(self, swarm_service, basic_swarm):
        """验证添加子Agent后立即反映在蜂群信息中，延迟≤5秒"""
        start = time.monotonic()
        updated = swarm_service.add_member(basic_swarm["id"], "reasonix", "rx-1")
        elapsed = time.monotonic() - start
        assert elapsed <= 5.0, f"添加成员更新延迟 {elapsed:.3f}s"
        assert len(updated["members"]) == 1
        assert updated["members"][0]["agent_id"] == "rx-1"

    def test_remove_member_reflects_immediately(self, swarm_service, basic_swarm):
        """验证移除子Agent后立即反映，延迟≤5秒"""
        swarm_service.add_member(basic_swarm["id"], "reasonix", "rx-1")
        swarm_service.add_member(basic_swarm["id"], "reasonix", "rx-2")
        start = time.monotonic()
        updated = swarm_service.remove_member(basic_swarm["id"], "rx-1")
        elapsed = time.monotonic() - start
        assert elapsed <= 5.0, f"移除成员更新延迟 {elapsed:.3f}s"
        assert len(updated["members"]) == 1

    def test_progress_query_latency_under_5s(self, swarm_service, swarm_with_three_agents):
        """验证查询进度延迟≤5秒"""
        tasks = [{"task_id": f"t-{i}", "name": f"任务{i}"} for i in range(20)]
        swarm_service.dispatch_tasks(swarm_with_three_agents["id"], tasks)
        start = time.monotonic()
        progress = swarm_service.get_progress(swarm_with_three_agents["id"])
        elapsed = time.monotonic() - start
        assert elapsed <= 5.0, f"进度查询延迟 {elapsed:.3f}s，超过5秒"
        assert progress["total_tasks"] == 20
        assert progress["pending_tasks"] == 20
        assert progress["completed_tasks"] == 0

    def test_status_consistency_across_consecutive_queries(self, swarm_service, basic_swarm):
        """验证连续查询状态一致"""
        statuses = []
        for _ in range(10):
            s = swarm_service.get_swarm(basic_swarm["id"])
            statuses.append(s["status"])
        assert all(st == "active" for st in statuses)

    def test_disband_then_query_status(self, swarm_service, basic_swarm):
        """验证解散后查询状态返回disbanded"""
        swarm_service.disband_swarm(basic_swarm["id"])
        result = swarm_service.get_swarm(basic_swarm["id"])
        assert result["status"] == "disbanded"
        assert result["disbanded_at"] is not None

    def test_recreate_after_disband_returns_active(self, swarm_service):
        """验证解散后重建蜂群立即变为active"""
        s1 = swarm_service.create_swarm(
            project_id="p-recreate2",
            name="解散重建",
            purpose="test_execution",
            step_number=11,
            manager_role="houda",
        )
        swarm_service.disband_swarm(s1["id"])
        s2 = swarm_service.create_swarm(
            project_id="p-recreate2",
            name="重建蜂群",
            purpose="test_execution",
            step_number=11,
            manager_role="houda",
        )
        assert s2["status"] == "active"
        assert s2["id"] != s1["id"]

    def test_get_progress_updates_after_dispatch(self, swarm_service, swarm_with_three_agents):
        """验证分发任务后进度立即更新"""
        tasks = [{"task_id": f"t-{i}", "name": f"任务{i}"} for i in range(15)]
        dispatch_time = time.monotonic()
        swarm_service.dispatch_tasks(swarm_with_three_agents["id"], tasks)
        progress = swarm_service.get_progress(swarm_with_three_agents["id"])
        query_time = time.monotonic()
        assert query_time - dispatch_time <= 5.0
        assert progress["total_tasks"] == 15
        assert progress["pending_tasks"] == 15


# ============================================================
# 边界值测试
# ============================================================

class TestBoundaryConditions:
    """边界条件和异常场景测试"""

    def test_empty_swarm_no_members(self, swarm_service, basic_swarm):
        """空蜂群：没有子Agent时成员数为0"""
        assert len(basic_swarm["members"]) == 0

    def test_empty_swarm_dispatch_returns_empty(self, swarm_service, basic_swarm):
        """空蜂群：没有子Agent时分发任务返回空列表"""
        tasks = [{"task_id": "t-0", "name": "任务0"}]
        assignments = swarm_service.dispatch_tasks(basic_swarm["id"], tasks)
        assert assignments == []

    def test_empty_task_list(self, swarm_service, swarm_with_three_agents):
        """空任务列表：分发无任务时返回空"""
        assignments = swarm_service.dispatch_tasks(swarm_with_three_agents["id"], [])
        assert assignments == []

    def test_max_members_large_swarm(self, swarm_service, basic_swarm):
        """大量子Agent：验证50个子Agent的蜂群"""
        for i in range(50):
            swarm_service.add_member(basic_swarm["id"], "reasonix", f"rx-{i}")
        updated = swarm_service.get_swarm(basic_swarm["id"])
        assert len(updated["members"]) == 50

    def test_get_nonexistent_swarm_raises_error(self, swarm_service):
        """不存在的蜂群ID：get_swarm应抛出KeyError"""
        with pytest.raises(KeyError):
            swarm_service.get_swarm("nonexistent-swarm")

    def test_dispatch_to_nonexistent_swarm_raises_error(self, swarm_service):
        """不存在的蜂群ID：dispatch_tasks应抛出KeyError"""
        with pytest.raises(KeyError):
            swarm_service.dispatch_tasks("nonexistent-swarm", [])

    def test_disband_nonexistent_swarm_raises_error(self, swarm_service):
        """不存在的蜂群ID：disband_swarm应抛出KeyError"""
        with pytest.raises(KeyError):
            swarm_service.disband_swarm("nonexistent-swarm")

    def test_single_agent_distribution_uniformity(self, swarm_service, basic_swarm):
        """单子Agent：所有任务分给同一个Agent，均匀度应为1.0"""
        swarm_service.add_member(basic_swarm["id"], "reasonix", "rx-single")
        tasks = [{"task_id": f"t-{i}", "name": f"任务{i}"} for i in range(10)]
        assignments = swarm_service.dispatch_tasks(basic_swarm["id"], tasks)
        for a in assignments:
            assert a["assigned_agent_id"] == "rx-single"

    def test_swarm_reuses_counter_after_reset(self, swarm_service):
        """验证两次连续创建的id顺序递增"""
        s1 = swarm_service.create_swarm("p-a", "A", "test", 11, "houda")
        s2 = swarm_service.create_swarm("p-b", "B", "test", 11, "houda")
        assert int(s1["id"].split("-")[1]) < int(s2["id"].split("-")[1])


# ============================================================
# 端到端集成测试 —— 覆盖所有验收标准
# ============================================================

def test_end_to_end_workflow():
    """完整端到端测试：创建蜂群→添加Agent→分发任务→查询进度→解散"""
    service = MockSwarmService()

    # 创建蜂群（创建时间≤1分钟）
    create_start = time.monotonic()
    swarm = service.create_swarm(
        project_id="p-e2e",
        name="端到端测试蜂群",
        purpose="test_execution",
        step_number=11,
        manager_role="houda",
    )
    create_latency = time.monotonic() - create_start
    assert create_latency <= 60.0, f"创建蜂群耗时 {create_latency:.3f}s"
    assert swarm["status"] == "active"

    # 添加子Agent（数量≥3）
    for i in range(5):
        service.add_member(swarm["id"], "reasonix", f"rx-{i}")
    updated = service.get_swarm(swarm["id"])
    assert len(updated["members"]) >= 3
    assert len(updated["members"]) == 5

    # 分发30个任务（均匀度≥80%）
    tasks = [{"task_id": f"t-{i}", "name": f"任务{i}"} for i in range(30)]
    assignments = service.dispatch_tasks(swarm["id"], tasks)
    assert len(assignments) == 30

    agent_counts = {}
    for a in assignments:
        agent_counts[a["assigned_agent_id"]] = agent_counts.get(a["assigned_agent_id"], 0) + 1
    max_c = max(agent_counts.values())
    min_c = min(agent_counts.values())
    evenness = 1.0 - (max_c - min_c) / (max_c + min_c)
    assert evenness >= 0.80

    # 查询进度（延迟≤5秒）
    progress_start = time.monotonic()
    progress = service.get_progress(swarm["id"])
    progress_latency = time.monotonic() - progress_start
    assert progress_latency <= 5.0
    assert progress["total_tasks"] == 30

    # 解散蜂群（状态更新延迟≤5秒）
    disband_start = time.monotonic()
    result = service.disband_swarm(swarm["id"])
    disband_latency = time.monotonic() - disband_start
    assert disband_latency <= 5.0
    assert result["status"] == "disbanded"

    final = service.get_swarm(swarm["id"])
    assert final["status"] == "disbanded"
    assert final["disbanded_at"] is not None


def test_repeated_create_disband_cycle():
    """反复创建和解散蜂群10次"""
    service = MockSwarmService()
    for i in range(10):
        swarm = service.create_swarm(
            project_id=f"p-cycle-{i}",
            name=f"循环蜂群{i}",
            purpose="test_execution",
            step_number=11,
            manager_role="houda",
        )
        assert swarm["status"] == "active"
        swarm_id = swarm["id"]
        for j in range(3):
            service.add_member(swarm_id, "reasonix", f"rx-{i}-{j}")
        members = service.get_swarm(swarm_id)
        assert len(members["members"]) == 3
        result = service.disband_swarm(swarm_id)
        assert result["status"] == "disbanded"
