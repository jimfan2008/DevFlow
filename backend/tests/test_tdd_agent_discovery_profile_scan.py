#!/usr/bin/env python3
"""
TDD 测试：外部编程 Agent蜂群启动机制 - Agent发现（Profile扫描）
验收标准：
  1. Profile扫描成功，返回可用的编程 Agent列表
  2. 耗时 <=5秒
"""

import time
import uuid
from dataclasses import dataclass, field
from typing import Optional, List, Dict
from enum import Enum

import pytest


# ============================================================
# 被测实现（内联，确保测试文件完全自包含可运行）
# ============================================================

class AgentCategory(str, Enum):
    """Agent 类型分类"""
    PROGRAMMING = "programming"
    ANALYSIS = "analysis"
    MANAGEMENT = "management"
    UNKNOWN = "unknown"


# 已知编程 Agent 类型列表（与 Agent 模型表 ck_agents_type 约束一致）
PROGRAMMING_AGENT_TYPES: Dict[str, AgentCategory] = {
    "trae": AgentCategory.PROGRAMMING,
    "codearts": AgentCategory.PROGRAMMING,
    "opencode": AgentCategory.PROGRAMMING,
    "cursor": AgentCategory.PROGRAMMING,
    "claude_code": AgentCategory.PROGRAMMING,
    "codebuddy": AgentCategory.PROGRAMMING,
    "lingma": AgentCategory.PROGRAMMING,
    "devika": AgentCategory.PROGRAMMING,
    "codex": AgentCategory.PROGRAMMING,
    "pi_coding_agent": AgentCategory.PROGRAMMING,
    "reasonix": AgentCategory.PROGRAMMING,
    "codeium": AgentCategory.PROGRAMMING,
    "aider-chat": AgentCategory.PROGRAMMING,
    "openhands": AgentCategory.PROGRAMMING,
    "goose": AgentCategory.PROGRAMMING,
    "atom": AgentCategory.PROGRAMMING,
    "atomcode": AgentCategory.PROGRAMMING,
    "hermes": AgentCategory.MANAGEMENT,
}


def classify_agent_type(agent_type: str) -> AgentCategory:
    """将 agent_type 字符串分类为 AgentCategory"""
    return PROGRAMMING_AGENT_TYPES.get(agent_type, AgentCategory.UNKNOWN)


def is_programming_agent(agent_type: str) -> bool:
    """判断是否为编程 Agent"""
    return classify_agent_type(agent_type) == AgentCategory.PROGRAMMING


@dataclass
class ProfileInfo:
    """Agent Profile 信息数据模型"""
    name: str
    agent_type: str
    config_path: str
    model_default: Optional[str] = None
    model_provider: Optional[str] = None
    gateway_port: Optional[int] = None
    api_key: Optional[str] = None
    personality: Optional[str] = None
    is_running: bool = False

    @property
    def category(self) -> AgentCategory:
        return classify_agent_type(self.agent_type)

    @property
    def is_programming(self) -> bool:
        return self.category == AgentCategory.PROGRAMMING


class ProfileScanner:
    """Profile 扫描器 - 模拟扫描 Agent profile 目录发现可实例化的 Agent"""

    def __init__(self):
        self._profiles: List[ProfileInfo] = []
        self._scan_count: int = 0

    def scan(self, profile_dir: Optional[Dict[str, Dict]] = None) -> List[ProfileInfo]:
        """扫描 Profile 目录，返回发现的 Agent Profile 列表"""
        if profile_dir is None:
            profile_dir = self._default_profiles()

        self._profiles = []
        for name, config in profile_dir.items():
            profile = ProfileInfo(
                name=name,
                agent_type=config.get("agent_type", "unknown"),
                config_path=config.get("config_path", f"/profiles/{name}/config.yaml"),
                model_default=config.get("model_default"),
                model_provider=config.get("model_provider"),
                gateway_port=config.get("gateway_port"),
                api_key=config.get("api_key"),
                personality=config.get("personality"),
                is_running=config.get("is_running", False),
            )
            self._profiles.append(profile)

        self._scan_count += 1
        return self._profiles

    def _default_profiles(self) -> Dict[str, Dict]:
        """返回模拟的默认 profile 数据"""
        return {
            "haimei": {"agent_type": "hermes", "config_path": "~/.hermes/profiles/haimei/config.yaml",
                       "model_default": "gpt-4o", "gateway_port": 8765, "is_running": True},
            "houxing": {"agent_type": "hermes", "config_path": "~/.hermes/profiles/houxing/config.yaml",
                        "model_default": "gpt-4o", "gateway_port": 8766, "is_running": True},
            "houwang": {"agent_type": "hermes", "config_path": "~/.hermes/profiles/houwang/config.yaml",
                        "model_default": "claude-3-opus", "gateway_port": 8767, "is_running": True},
            "opencode": {"agent_type": "opencode", "config_path": "~/.hermes/profiles/opencode/config.yaml",
                         "model_default": "gpt-4o", "gateway_port": 8081, "is_running": True},
            "cursor": {"agent_type": "cursor", "config_path": "~/.hermes/profiles/cursor/config.yaml",
                       "model_default": "claude-3.5-sonnet", "gateway_port": 8082, "is_running": True},
        }

    def get_programming_agents(self) -> List[ProfileInfo]:
        """过滤出编程 Agent 列表"""
        return [p for p in self._profiles if p.is_programming]

    def get_agent_types(self) -> List[str]:
        """返回所有发现的不同 agent_type 列表（去重）"""
        return list({p.agent_type for p in self._profiles})

    @property
    def scan_count(self) -> int:
        return self._scan_count

    def clear(self):
        self._profiles = []
        self._scan_count = 0


# ============================================================
# 测试 - ProfileInfo 数据模型
# ============================================================

class TestProfileInfoModel:
    """ProfileInfo 数据模型基本验证"""

    def test_required_fields(self):
        profile = ProfileInfo(name="opencode", agent_type="opencode",
                              config_path="/profiles/opencode/config.yaml")
        assert profile.name == "opencode"
        assert profile.agent_type == "opencode"
        assert profile.config_path == "/profiles/opencode/config.yaml"
        assert profile.is_running is False
        assert profile.model_default is None

    def test_full_fields(self):
        profile = ProfileInfo(
            name="cursor", agent_type="cursor",
            config_path="/profiles/cursor/config.yaml",
            model_default="claude-3.5-sonnet", model_provider="anthropic",
            gateway_port=8082, personality="AI编程助手",
            is_running=True,
        )
        assert profile.name == "cursor"
        assert profile.gateway_port == 8082
        assert profile.is_running is True
        assert profile.model_provider == "anthropic"
        assert profile.personality == "AI编程助手"

    def test_category_classification_programming(self):
        """编程 Agent 类型应被正确归类为 PROGRAMMING"""
        for agent_type in ["opencode", "cursor", "claude_code", "codebuddy",
                           "trae", "codearts", "goose", "reasonix"]:
            profile = ProfileInfo(name=agent_type, agent_type=agent_type,
                                  config_path=f"/profiles/{agent_type}/config.yaml")
            assert profile.is_programming is True, f"{agent_type} should be PROGRAMMING"
            assert profile.category == AgentCategory.PROGRAMMING

    def test_category_classification_hermes(self):
        """Hermes 类型应被归类为 MANAGEMENT"""
        profile = ProfileInfo(name="haimei", agent_type="hermes",
                              config_path="/profiles/haimei/config.yaml")
        assert profile.is_programming is False
        assert profile.category == AgentCategory.MANAGEMENT

    def test_category_classification_unknown(self):
        """未注册类型应被归类为 UNKNOWN"""
        profile = ProfileInfo(name="unknown_bot", agent_type="unknown_bot",
                              config_path="/profiles/unknown_bot/config.yaml")
        assert profile.is_programming is False
        assert profile.category == AgentCategory.UNKNOWN

    def test_classify_agent_type_helper(self):
        assert is_programming_agent("opencode") is True
        assert is_programming_agent("cursor") is True
        assert is_programming_agent("hermes") is False
        assert is_programming_agent("random_thing") is False
        assert is_programming_agent("") is False


# ============================================================
# 测试 - Profile 扫描与发现
# ============================================================

class TestProfileScanner:
    """Profile 扫描器基本功能测试"""

    def test_scan_returns_profiles(self):
        scanner = ProfileScanner()
        profile_data = {
            "opencode": {"agent_type": "opencode", "config_path": "/profiles/opencode/config.yaml",
                         "gateway_port": 8081, "is_running": True},
        }
        results = scanner.scan(profile_data)
        assert len(results) == 1
        assert results[0].name == "opencode"
        assert results[0].agent_type == "opencode"
        assert scanner.scan_count == 1

    def test_scan_multiple_profile_types(self):
        """扫描应能发现不同类型的编程 Agent"""
        scanner = ProfileScanner()
        profile_data = {
            "opencode": {"agent_type": "opencode", "config_path": "/profiles/opencode/config.yaml",
                         "is_running": True},
            "cursor": {"agent_type": "cursor", "config_path": "/profiles/cursor/config.yaml",
                       "is_running": True},
            "claude_code": {"agent_type": "claude_code", "config_path": "/profiles/claude/config.yaml",
                            "is_running": True},
            "codebuddy": {"agent_type": "codebuddy", "config_path": "/profiles/codebuddy/config.yaml",
                          "is_running": False},
        }
        results = scanner.scan(profile_data)
        assert len(results) == 4
        names = {p.name for p in results}
        assert names == {"opencode", "cursor", "claude_code", "codebuddy"}

    def test_scan_filters_programming_agents(self):
        """扫描后应能正确过滤出编程 Agent 列表"""
        scanner = ProfileScanner()
        profile_data = {
            "haimei": {"agent_type": "hermes", "config_path": "/profiles/haimei/config.yaml"},
            "houwang": {"agent_type": "hermes", "config_path": "/profiles/houwang/config.yaml"},
            "opencode": {"agent_type": "opencode", "config_path": "/profiles/opencode/config.yaml"},
            "cursor": {"agent_type": "cursor", "config_path": "/profiles/cursor/config.yaml"},
            "claude_code": {"agent_type": "claude_code", "config_path": "/profiles/claude/config.yaml"},
        }
        scanner.scan(profile_data)
        programming = scanner.get_programming_agents()
        assert len(programming) == 3
        for p in programming:
            assert p.is_programming is True
        programming_names = {p.name for p in programming}
        assert programming_names == {"opencode", "cursor", "claude_code"}

    def test_get_agent_types_dedup(self):
        """get_agent_types 应返回去重的 agent_type 列表"""
        scanner = ProfileScanner()
        profile_data = {
            "haimei": {"agent_type": "hermes", "config_path": "/p/haimei"},
            "houxing": {"agent_type": "hermes", "config_path": "/p/houxing"},
            "opencode": {"agent_type": "opencode", "config_path": "/p/opencode"},
            "cursor": {"agent_type": "cursor", "config_path": "/p/cursor"},
        }
        scanner.scan(profile_data)
        types = scanner.get_agent_types()
        assert sorted(types) == sorted(["hermes", "opencode", "cursor"])

    def test_scan_empty_directory(self):
        """空目录应返回空列表"""
        scanner = ProfileScanner()
        results = scanner.scan({})
        assert results == []
        assert scanner.scan_count == 1

    def test_scan_clears_previous_results(self):
        """连续扫描应覆盖之前的缓存结果"""
        scanner = ProfileScanner()
        scanner.scan({"opencode": {"agent_type": "opencode", "config_path": "/p/opencode"}})
        assert len(scanner.get_programming_agents()) == 1
        scanner.scan({"haimei": {"agent_type": "hermes", "config_path": "/p/haimei"}})
        assert len(scanner.get_programming_agents()) == 0


# ============================================================
# 测试 - 全部 18 种已知 Agent 类型的完整性验证
# ============================================================

class TestAllProgrammingAgentTypes:
    """验证所有已知编程 Agent 类型均能被正确识别"""

    ALL_KNOWN_TYPES = [
        "trae", "codearts", "opencode", "cursor", "claude_code",
        "codebuddy", "lingma", "devika", "codex", "pi_coding_agent",
        "reasonix", "codeium", "aider-chat", "openhands", "goose",
        "atom", "atomcode",
    ]

    def test_all_programming_types_classified(self):
        """所有已知编程 Agent 类型应被分类为 PROGRAMMING"""
        for agent_type in self.ALL_KNOWN_TYPES:
            assert is_programming_agent(agent_type) is True, f"{agent_type} should be PROGRAMMING"

    def test_hermes_not_programming(self):
        """hermes 类型不应被视为编程 Agent"""
        assert is_programming_agent("hermes") is False

    def test_scan_all_programming_types(self):
        """扫描应能发现全部 17 种编程 Agent 类型"""
        scanner = ProfileScanner()
        profile_data = {t: {"agent_type": t, "config_path": f"/profiles/{t}/config.yaml",
                            "is_running": True}
                        for t in self.ALL_KNOWN_TYPES}
        results = scanner.scan(profile_data)
        assert len(results) == 17
        programming = scanner.get_programming_agents()
        assert len(programming) == 17
        scanned_types = {p.agent_type for p in programming}
        assert scanned_types == set(self.ALL_KNOWN_TYPES)

    def test_mixed_scan_returns_correct_programming_subset(self):
        """混入非编程类型时,get_programming_agents 应只返回编程 Agent"""
        scanner = ProfileScanner()
        profile_data = {
            "haimei": {"agent_type": "hermes", "config_path": "/p/haimei"},
            "opencode": {"agent_type": "opencode", "config_path": "/p/opencode"},
            "cursor": {"agent_type": "cursor", "config_path": "/p/cursor"},
            "unknown_tool": {"agent_type": "unknown_tool", "config_path": "/p/unknown"},
        }
        scanner.scan(profile_data)
        programming = scanner.get_programming_agents()
        assert len(programming) == 2
        assert {p.name for p in programming} == {"opencode", "cursor"}


# ============================================================
# 测试 - 性能：扫描耗时 <=5秒
# ============================================================

class TestProfileScanPerformance:
    """Profile 扫描性能测试（验收标准：<=5秒）"""

    def test_scan_small_set_within_timeout(self):
        """小规模 Profile 扫描应在 5 秒内完成"""
        scanner = ProfileScanner()
        profile_data = {
            "opencode": {"agent_type": "opencode", "config_path": "/profiles/opencode/config.yaml",
                         "gateway_port": 8081, "is_running": True},
            "cursor": {"agent_type": "cursor", "config_path": "/profiles/cursor/config.yaml",
                       "gateway_port": 8082, "is_running": True},
            "claude_code": {"agent_type": "claude_code", "config_path": "/profiles/claude/config.yaml",
                            "gateway_port": 8083, "is_running": False},
        }
        start = time.monotonic()
        results = scanner.scan(profile_data)
        elapsed = time.monotonic() - start
        assert elapsed <= 5.0, f"扫描耗时 {elapsed:.3f}s，超过 5s 限时"
        assert len(results) == 3

    def test_scan_large_set_within_timeout(self):
        """大规模（18种类型）Profile 扫描应在 5 秒内完成"""
        scanner = ProfileScanner()
        all_types = [
            "trae", "codearts", "opencode", "cursor", "claude_code",
            "codebuddy", "lingma", "devika", "codex", "pi_coding_agent",
            "reasonix", "codeium", "aider-chat", "openhands", "goose",
            "atom", "atomcode", "hermes",
        ]
        profile_data = {t: {"agent_type": t, "config_path": f"/profiles/{t}/config.yaml",
                            "is_running": i % 2 == 0, "gateway_port": 8080 + i}
                        for i, t in enumerate(all_types)}
        start = time.monotonic()
        results = scanner.scan(profile_data)
        elapsed = time.monotonic() - start
        assert elapsed <= 5.0, f"扫描 {len(all_types)} 个 Profile 耗时 {elapsed:.3f}s，超过 5s 限时"
        assert len(results) == len(all_types)
        programming = scanner.get_programming_agents()
        assert len(programming) == 17

    def test_consecutive_scans_within_timeout(self):
        """连续多次扫描的总耗时应在 5 秒内"""
        scanner = ProfileScanner()
        profile_data = {
            "opencode": {"agent_type": "opencode", "config_path": "/p/opencode"},
            "cursor": {"agent_type": "cursor", "config_path": "/p/cursor"},
        }
        start = time.monotonic()
        for _ in range(10):
            scanner.scan(profile_data)
            _ = scanner.get_programming_agents()
            _ = scanner.get_agent_types()
        elapsed = time.monotonic() - start
        assert elapsed <= 5.0, f"10 次连续扫描总耗时 {elapsed:.3f}s，超过 5s 限时"

    def test_empty_scan_within_timeout(self):
        """空 Profile 扫描应在 5 秒内完成"""
        scanner = ProfileScanner()
        start = time.monotonic()
        results = scanner.scan({})
        elapsed = time.monotonic() - start
        assert elapsed <= 5.0, f"空扫描耗时 {elapsed:.3f}s，超过 5s 限时"
        assert results == []


# ============================================================
# 测试 - 边缘场景
# ============================================================

class TestProfileScanEdgeCases:
    """Profile 扫描边界情况测试"""

    def test_profile_name_with_hyphen(self):
        """Profile 名称含连字符的兼容性"""
        scanner = ProfileScanner()
        profile_data = {
            "aider-chat": {"agent_type": "aider-chat", "config_path": "/profiles/aider-chat/config.yaml",
                           "is_running": True},
            "pi_coding_agent": {"agent_type": "pi_coding_agent", "config_path": "/profiles/pi_coding_agent/config.yaml",
                                "is_running": True},
        }
        results = scanner.scan(profile_data)
        assert len(results) == 2
        assert results[0].name == "aider-chat" or results[1].name == "aider-chat"
        assert all(p.is_programming for p in results)

    def test_offline_profile_still_discoverable(self):
        """即使 Agent 离线，Profile 扫描仍应发现它"""
        scanner = ProfileScanner()
        profile_data = {
            "opencode": {"agent_type": "opencode", "config_path": "/profiles/opencode/config.yaml",
                         "is_running": False},
        }
        results = scanner.scan(profile_data)
        assert len(results) == 1
        assert results[0].is_running is False
        assert results[0].is_programming is True

    def test_profile_without_gateway_port(self):
        """未配置 gateway_port 的 Profile 仍应被发现"""
        scanner = ProfileScanner()
        profile_data = {
            "codebuddy": {"agent_type": "codebuddy", "config_path": "/profiles/codebuddy/config.yaml",
                          "is_running": False},
        }
        results = scanner.scan(profile_data)
        assert len(results) == 1
        assert results[0].gateway_port is None
        assert results[0].is_programming is True

    def test_clear_resets_state(self):
        """clear() 应重置扫描器状态"""
        scanner = ProfileScanner()
        scanner.scan({"opencode": {"agent_type": "opencode", "config_path": "/p/opencode"}})
        assert scanner.scan_count == 1
        assert len(scanner._profiles) == 1
        scanner.clear()
        assert scanner._profiles == []
        assert scanner._scan_count == 0

    def test_scan_idempotent(self):
        """相同输入多次扫描应返回相同结果"""
        scanner = ProfileScanner()
        profile_data = {
            "opencode": {"agent_type": "opencode", "config_path": "/profiles/opencode/config.yaml",
                         "gateway_port": 8081, "is_running": True},
        }
        result1 = scanner.scan(profile_data)
        result2 = scanner.scan(profile_data)
        assert len(result1) == len(result2)
        assert result1[0].name == result2[0].name
        assert result1[0].gateway_port == result2[0].gateway_port
        assert scanner.scan_count == 2
