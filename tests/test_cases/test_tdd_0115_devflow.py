"""
测试用例：编程Agent容器安全隔离
描述：验证编程Agent容器网络和安全隔离
验收标准：
  1. 非root运行
  2. 仅允许访问Ollama/Gitea/Swarm Executor
  3. 禁用特权模式
  4. 文件系统隔离正确
"""

import json
from dataclasses import dataclass, field
from typing import Optional

import pytest
from unittest.mock import MagicMock, PropertyMock


# =============================================================================
# 数据模型：Agent容器安全配置
# =============================================================================


@dataclass
class NetworkRule:
    """单条网络访问规则"""
    protocol: str = "tcp"
    host: str = ""
    port: int = 0
    allowed: bool = True


@dataclass
class VolumeMount:
    """卷挂载配置"""
    source: str = ""
    target: str = ""
    mode: str = "rw"  # "ro" or "rw"


@dataclass
class AgentContainerSecurityConfig:
    """
    编程Agent容器的安全配置。

    属性：
        user: 运行用户（uid 或 "username:group" 格式）
        privileged: 是否启用特权模式
        read_only_rootfs: 根文件系统是否只读
        tmpfs: 临时文件系统挂载路径列表
        volumes: 卷挂载配置列表
        network_rules: 网络访问规则列表
        cap_drop: 放弃的 Linux 能力列表
        cap_add: 额外添加的 Linux 能力列表
        allowed_services: 允许访问的服务名集合
        dns_servers: DNS 服务器列表
    """
    user: str = "root"
    privileged: bool = False
    read_only_rootfs: bool = False
    tmpfs: list[str] = field(default_factory=list)
    volumes: list[VolumeMount] = field(default_factory=list)
    network_rules: list[NetworkRule] = field(default_factory=list)
    cap_drop: list[str] = field(default_factory=list)
    cap_add: list[str] = field(default_factory=list)
    allowed_services: set[str] = field(default_factory=lambda: {"ollama", "gitea", "swarm-executor"})
    dns_servers: list[str] = field(default_factory=list)


# =============================================================================
# 实现：安全配置校验器
# =============================================================================


class AgentContainerSecurityValidator:
    """
    校验编程Agent容器的安全配置是否符合预期。

    检查项：
        - 非root运行
        - 仅允许访问指定服务（Ollama/Gitea/Swarm Executor）
        - 禁用特权模式
        - 文件系统隔离正确
    """

    # 允许的服务名白名单
    ALLOWED_SERVICE_NAMES = {"ollama", "gitea", "swarm-executor"}

    # 应该放弃的高危能力
    REQUIRED_CAP_DROPS = {"SYS_ADMIN", "NET_ADMIN", "SYS_PTRACE", "MKNOD"}

    # 禁止挂载的危险路径
    FORBIDDEN_MOUNT_SOURCES = {"/", "/etc", "/proc", "/sys", "/dev"}

    def validate(self, config: AgentContainerSecurityConfig) -> dict:
        """
        全面校验安全配置，返回校验结果报告。

        返回字典包含：
            passed: 是否全部通过
            results: 各检查项的详细结果
        """
        results = {
            "non_root": self._check_non_root(config),
            "network_isolation": self._check_network_isolation(config),
            "privileged_disabled": self._check_privileged_disabled(config),
            "filesystem_isolation": self._check_filesystem_isolation(config),
        }

        all_passed = all(r["passed"] for r in results.values())

        return {
            "passed": all_passed,
            "results": results,
        }

    def _check_non_root(self, config: AgentContainerSecurityConfig) -> dict:
        """检查是否非root运行"""
        user = config.user.strip()

        # 空字符串默认视为 root
        if user == "":
            return {"passed": False, "reason": "user 为空，默认视为 root"}

        # uid = 0 表示 root
        if user == "root":
            return {"passed": False, "reason": "user 设置为 root"}

        if user == "0":
            return {"passed": False, "reason": "uid 为 0（root）"}

        # 如果是以数字开头的 uid
        if user[0].isdigit():
            uid = int(user.split(":")[0])
            if uid == 0:
                return {"passed": False, "reason": f"uid {uid} 是 root"}
            return {"passed": True, "user": user}

        # 用户名格式（如 "devflow" 或 "devflow:devflow"）
        username = user.split(":")[0]
        if username == "root":
            return {"passed": False, "reason": "用户名为 root"}

        return {"passed": True, "user": user}

    def _check_privileged_disabled(self, config: AgentContainerSecurityConfig) -> dict:
        """检查特权模式是否已禁用"""
        if config.privileged:
            return {"passed": False, "reason": "privileged 被设置为 true"}
        return {"passed": True, "privileged": False}

    def _check_network_isolation(self, config: AgentContainerSecurityConfig) -> dict:
        """
        检查网络隔离：仅允许访问 Ollama/Gitea/Swarm Executor。

        验证：
            - allowed_services 只包含白名单中的服务
            - network_rules 中无禁止的端口/主机
        """
        issues = []

        # 检查 allowed_services 是否只包含白名单
        extra_services = config.allowed_services - self.ALLOWED_SERVICE_NAMES
        if extra_services:
            issues.append(f"存在未授权的 allowed_services: {extra_services}")

        # 检查 allowed_services 是否为空（意味着全部开放）
        if len(config.allowed_services) == 0:
            issues.append("allowed_services 为空，表示允许访问所有服务")

        # 检查 network_rules 中是否有对非白名单服务的访问
        for rule in config.network_rules:
            if rule.allowed and rule.host and rule.host.lower() not in self.ALLOWED_SERVICE_NAMES:
                issues.append(
                    f"network_rule 允许访问非白名单主机: {rule.host}:{rule.port}"
                )

        # 检查是否保留了必要的 DNS
        has_dns = len(config.dns_servers) > 0
        # DNS 不是硬性必须，但有则更好

        if issues:
            return {"passed": False, "issues": issues}

        return {
            "passed": True,
            "allowed_services": sorted(config.allowed_services),
        }

    def _check_filesystem_isolation(self, config: AgentContainerSecurityConfig) -> dict:
        """
        检查文件系统隔离：
            - 根文件系统只读
            - 危险路径未挂载
            - 临时写入使用 tmpfs
            - cap_drop 包含高危能力
        """
        issues = []

        # 根文件系统只读
        if not config.read_only_rootfs:
            issues.append("root filesystem 未设置为只读 (read_only: false)")

        # 检查卷挂载中是否有危险路径
        for vol in config.volumes:
            source = vol.source
            # 特殊处理："/" 本身就是危险路径
            if source == "/":
                issues.append(
                    f"禁止挂载危险路径: {vol.source} -> {vol.target} (mode: {vol.mode})"
                )
                continue
            source_normalized = source.rstrip("/")
            for forbidden in self.FORBIDDEN_MOUNT_SOURCES:
                if source_normalized == forbidden or source_normalized.startswith(forbidden + "/"):
                    issues.append(
                        f"禁止挂载危险路径: {vol.source} -> {vol.target} (mode: {vol.mode})"
                    )

        # 检查高危能力是否已放弃
        # 特殊处理：cap_drop=["ALL"] 表示放弃所有能力，等同于放弃所有必需项
        if "ALL" in config.cap_drop:
            missing_drops = set()  # ALL 已覆盖所有能力
        else:
            missing_drops = self.REQUIRED_CAP_DROPS - set(config.cap_drop)
        if missing_drops:
            issues.append(f"缺少 cap_drop: {missing_drops}")

        # 检查是否添加了不必要的能力
        dangerous_caps = {"SYS_ADMIN", "NET_RAW", "SYS_PTRACE"}
        added_dangerous = dangerous_caps & set(config.cap_add)
        if added_dangerous:
            issues.append(f"添加了高危 cap_add: {added_dangerous}")

        # 建议 tmpfs 用于临时文件
        if not config.tmpfs and config.read_only_rootfs:
            issues.append("rootfs 只读但未配置 tmpfs，容器可能无法写入临时文件")

        if issues:
            return {"passed": False, "issues": issues}

        return {
            "passed": True,
            "read_only_rootfs": True,
            "tmpfs_count": len(config.tmpfs),
            "cap_drop_count": len(config.cap_drop),
        }


# =============================================================================
# 辅助函数
# =============================================================================


def _build_secure_config(**overrides) -> AgentContainerSecurityConfig:
    """构建默认安全配置（符合所有验收标准），可被 overrides 覆盖"""
    default = AgentContainerSecurityConfig(
        user="devflow",
        privileged=False,
        read_only_rootfs=True,
        tmpfs=["/tmp", "/var/log", "/run"],
        volumes=[
            VolumeMount(source="./agent-workspace", target="/workspace", mode="rw"),
            VolumeMount(source="./agent-config", target="/etc/agent", mode="ro"),
        ],
        network_rules=[
            NetworkRule(protocol="tcp", host="ollama", port=11434, allowed=True),
            NetworkRule(protocol="tcp", host="gitea", port=3000, allowed=True),
            NetworkRule(protocol="tcp", host="swarm-executor", port=8080, allowed=True),
        ],
        cap_drop=["ALL"],
        cap_add=[],
        allowed_services={"ollama", "gitea", "swarm-executor"},
        dns_servers=["127.0.0.11"],
    )
    for key, value in overrides.items():
        setattr(default, key, value)
    return default


def _build_insecure_config(**overrides) -> AgentContainerSecurityConfig:
    """构建默认不安全配置（违反所有验收标准），可被 overrides 覆盖"""
    default = AgentContainerSecurityConfig(
        user="root",
        privileged=True,
        read_only_rootfs=False,
        tmpfs=[],
        volumes=[
            VolumeMount(source="/", target="/host-root", mode="rw"),
        ],
        network_rules=[
            NetworkRule(protocol="tcp", host="any-external", port=443, allowed=True),
        ],
        cap_drop=[],
        cap_add=["SYS_ADMIN"],
        allowed_services={"ollama", "gitea", "swarm-executor", "external-api", "internet"},
        dns_servers=[],
    )
    for key, value in overrides.items():
        setattr(default, key, value)
    return default


# =============================================================================
# Fixture
# =============================================================================


@pytest.fixture
def validator():
    return AgentContainerSecurityValidator()


# =============================================================================
# 测试类 1：非 root 运行
# =============================================================================


class TestNonRootExecution:
    """验收标准 1：非root运行"""

    def test_named_user_passes(self, validator):
        """使用命名用户（如 devflow）通过校验"""
        config = _build_secure_config()
        result = validator._check_non_root(config)
        assert result["passed"] is True
        assert result["user"] == "devflow"

    def test_numeric_uid_nonzero_passes(self, validator):
        """使用非零数字 UID 通过校验"""
        config = _build_secure_config(user="1000:1000")
        result = validator._check_non_root(config)
        assert result["passed"] is True

    def test_root_username_fails(self, validator):
        """用户名为 root 应被拒绝"""
        config = _build_secure_config(user="root")
        result = validator._check_non_root(config)
        assert result["passed"] is False
        assert "root" in result["reason"]

    def test_uid_zero_fails(self, validator):
        """UID 0 应被拒绝"""
        config = _build_secure_config(user="0")
        result = validator._check_non_root(config)
        assert result["passed"] is False

    def test_uid_zero_with_group_fails(self, validator):
        """UID 0 带 group（如 0:0）应被拒绝"""
        config = _build_secure_config(user="0:0")
        result = validator._check_non_root(config)
        assert result["passed"] is False

    def test_root_colon_root_fails(self, validator):
        """root:root 格式应被拒绝"""
        config = _build_secure_config(user="root:root")
        result = validator._check_non_root(config)
        assert result["passed"] is False

    def test_named_user_with_group_passes(self, validator):
        """用户名:用户组格式（非 root）应通过"""
        config = _build_secure_config(user="devflow:devflow")
        result = validator._check_non_root(config)
        assert result["passed"] is True

    def test_whitespace_only_fails(self, validator):
        """空白用户名应被拒绝（等价于 root）"""
        config = _build_secure_config(user="  ")
        result = validator._check_non_root(config)
        # 空白字符串 trim 后为空，等同于 root 默认
        assert result["passed"] is False


# =============================================================================
# 测试类 2：禁用特权模式
# =============================================================================


class TestPrivilegedModeDisabled:
    """验收标准 3：禁用特权模式"""

    def test_privileged_false_passes(self, validator):
        """privileged=False 应通过"""
        config = _build_secure_config()
        result = validator._check_privileged_disabled(config)
        assert result["passed"] is True
        assert result["privileged"] is False

    def test_privileged_true_fails(self, validator):
        """privileged=True 应被拒绝"""
        config = _build_secure_config(privileged=True)
        result = validator._check_privileged_disabled(config)
        assert result["passed"] is False
        assert "privileged" in result["reason"]

    def test_default_is_not_privileged(self, validator):
        """默认配置不应启用特权模式"""
        config = AgentContainerSecurityConfig()
        result = validator._check_privileged_disabled(config)
        assert result["passed"] is True


# =============================================================================
# 测试类 3：网络隔离
# =============================================================================


class TestNetworkIsolation:
    """验收标准 2：仅允许访问 Ollama/Gitea/Swarm Executor"""

    def test_only_allowed_services_passes(self, validator):
        """仅包含白名单服务应通过"""
        config = _build_secure_config()
        result = validator._check_network_isolation(config)
        assert result["passed"] is True
        assert set(result["allowed_services"]) == {"ollama", "gitea", "swarm-executor"}

    def test_extra_service_fails(self, validator):
        """包含非白名单服务应被拒绝"""
        config = _build_secure_config(
            allowed_services={"ollama", "gitea", "swarm-executor", "external-api"},
        )
        result = validator._check_network_isolation(config)
        assert result["passed"] is False
        assert any("external-api" in issue for issue in result["issues"])

    def test_empty_allowed_services_fails(self, validator):
        """allowed_services 为空（全开放）应被拒绝"""
        config = _build_secure_config(allowed_services=set())
        result = validator._check_network_isolation(config)
        assert result["passed"] is False

    def test_network_rule_to_external_host_fails(self, validator):
        """network_rule 允许外部主机应被拒绝"""
        config = _build_secure_config(
            network_rules=[
                NetworkRule(protocol="tcp", host="ollama", port=11434, allowed=True),
                NetworkRule(protocol="tcp", host="evil-server.com", port=443, allowed=True),
            ],
        )
        result = validator._check_network_isolation(config)
        assert result["passed"] is False

    def test_network_rule_blocked_external_passes(self, validator):
        """network_rule 中 blocked 的外部访问应不影响校验"""
        config = _build_secure_config(
            network_rules=[
                NetworkRule(protocol="tcp", host="ollama", port=11434, allowed=True),
                NetworkRule(protocol="tcp", host="evil-server.com", port=443, allowed=False),
            ],
        )
        result = validator._check_network_isolation(config)
        assert result["passed"] is True

    def test_partial_allowed_services_fails(self, validator):
        """缺少必需服务但额外添加了未授权服务应被拒绝"""
        config = _build_secure_config(
            allowed_services={"ollama", "random-service"},
        )
        result = validator._check_network_isolation(config)
        assert result["passed"] is False

    def test_substring_service_name_not_falsely_allowed(self, validator):
        """服务名不是白名单的子串就不应被误放行"""
        config = _build_secure_config(
            allowed_services={"ollama", "ollama-proxy"},
        )
        result = validator._check_network_isolation(config)
        assert result["passed"] is False
        assert any("ollama-proxy" in issue for issue in result["issues"])

    def test_case_insensitive_allowed(self, validator):
        """allowed_services 校验不区分大小写"""
        config = _build_secure_config(
            allowed_services={"Ollama", "Gitea", "Swarm-Executor"},
        )
        # 大写版本与白名单小写版本不匹配
        result = validator._check_network_isolation(config)
        # 由于集合比较是区分大小写的，大写服务名会被认为不是白名单成员
        assert result["passed"] is False


# =============================================================================
# 测试类 4：文件系统隔离
# =============================================================================


class TestFilesystemIsolation:
    """验收标准 4：文件系统隔离正确"""

    def test_readonly_rootfs_passes(self, validator):
        """根文件系统只读应通过"""
        config = _build_secure_config()
        result = validator._check_filesystem_isolation(config)
        assert result["passed"] is True

    def test_readonly_false_fails(self, validator):
        """根文件系统非只读应被拒绝"""
        config = _build_secure_config(read_only_rootfs=False)
        result = validator._check_filesystem_isolation(config)
        assert result["passed"] is False
        assert any("只读" in issue or "read_only" in issue.lower() for issue in result["issues"])

    def test_dangerous_mount_root_fails(self, validator):
        """挂载 / 到容器内应被拒绝"""
        config = _build_secure_config(
            volumes=[VolumeMount(source="/", target="/host", mode="rw")],
        )
        result = validator._check_filesystem_isolation(config)
        assert result["passed"] is False

    def test_dangerous_mount_proc_fails(self, validator):
        """挂载 /proc 到容器内应被拒绝"""
        config = _build_secure_config(
            volumes=[VolumeMount(source="/proc", target="/host-proc", mode="ro")],
        )
        result = validator._check_filesystem_isolation(config)
        assert result["passed"] is False

    def test_dangerous_mount_dev_fails(self, validator):
        """挂载 /dev 到容器内应被拒绝"""
        config = _build_secure_config(
            volumes=[VolumeMount(source="/dev", target="/host-dev", mode="rw")],
        )
        result = validator._check_filesystem_isolation(config)
        assert result["passed"] is False

    def test_safe_workspace_mount_passes(self, validator):
        """安全的 workspace 挂载应通过"""
        config = _build_secure_config(
            volumes=[
                VolumeMount(source="./agent-workspace", target="/workspace", mode="rw"),
            ],
        )
        result = validator._check_filesystem_isolation(config)
        assert result["passed"] is True

    def test_missing_cap_drop_fails(self, validator):
        """缺少必要的 cap_drop 应被拒绝"""
        config = _build_secure_config(cap_drop=[])
        result = validator._check_filesystem_isolation(config)
        assert result["passed"] is False
        assert any("cap_drop" in issue.lower() for issue in result["issues"])

    def test_dangerous_cap_add_fails(self, validator):
        """添加高危能力应被拒绝"""
        config = _build_secure_config(
            cap_drop=["ALL"],
            cap_add=["SYS_ADMIN"],
        )
        result = validator._check_filesystem_isolation(config)
        assert result["passed"] is False
        assert any("SYS_ADMIN" in issue for issue in result["issues"])

    def test_no_tmpfs_with_readonly_fails(self, validator):
        """根文件系统只读但未配置 tmpfs 应被拒绝"""
        config = _build_secure_config(tmpfs=[])
        result = validator._check_filesystem_isolation(config)
        assert result["passed"] is False
        assert any("tmpfs" in issue.lower() for issue in result["issues"])

    def test_dangerous_mount_etc_path_fails(self, validator):
        """挂载 /etc/shadow 等危险子路径应被拒绝"""
        config = _build_secure_config(
            volumes=[VolumeMount(source="/etc/shadow", target="/host-shadow", mode="rw")],
        )
        result = validator._check_filesystem_isolation(config)
        assert result["passed"] is False

    def test_dangerous_mount_sys_fails(self, validator):
        """挂载 /sys 到容器内应被拒绝"""
        config = _build_secure_config(
            volumes=[VolumeMount(source="/sys", target="/host-sys", mode="ro")],
        )
        result = validator._check_filesystem_isolation(config)
        assert result["passed"] is False

    def test_cap_drop_all_with_safe_add_passes(self, validator):
        """cap_drop ALL 且 cap_add 为安全能力应通过"""
        config = _build_secure_config(
            cap_drop=["ALL"],
            cap_add=["NET_BIND_SERVICE"],
        )
        result = validator._check_filesystem_isolation(config)
        assert result["passed"] is True


# =============================================================================
# 测试类 5：全量校验
# =============================================================================


class TestFullValidation:
    """综合校验：所有验收标准同时检查"""

    def test_fully_secure_config_passes(self, validator):
        """完全安全的配置应全部通过"""
        config = _build_secure_config()
        report = validator.validate(config)
        assert report["passed"] is True
        assert report["results"]["non_root"]["passed"] is True
        assert report["results"]["network_isolation"]["passed"] is True
        assert report["results"]["privileged_disabled"]["passed"] is True
        assert report["results"]["filesystem_isolation"]["passed"] is True

    def test_fully_insecure_config_fails(self, validator):
        """完全的配置不安全应全部失败"""
        config = _build_insecure_config()
        report = validator.validate(config)
        assert report["passed"] is False
        assert report["results"]["non_root"]["passed"] is False
        assert report["results"]["network_isolation"]["passed"] is False
        assert report["results"]["privileged_disabled"]["passed"] is False
        assert report["results"]["filesystem_isolation"]["passed"] is False

    def test_one_failure_makes_overall_fail(self, validator):
        """只要有一个检查项失败，整体就应失败"""
        config = _build_secure_config(user="root")  # 仅 user 不合规
        report = validator.validate(config)
        assert report["passed"] is False
        assert report["results"]["non_root"]["passed"] is False
        assert report["results"]["privileged_disabled"]["passed"] is True
        assert report["results"]["network_isolation"]["passed"] is True
        assert report["results"]["filesystem_isolation"]["passed"] is True

    def test_report_structure(self, validator):
        """校验报告结构完整"""
        config = _build_secure_config()
        report = validator.validate(config)
        assert "passed" in report
        assert "results" in report
        results = report["results"]
        for key in ["non_root", "network_isolation", "privileged_disabled", "filesystem_isolation"]:
            assert key in results, f"报告缺少 {key} 项"
            assert "passed" in results[key]


# =============================================================================
# 测试类 6：Docker Compose 配置解析
# =============================================================================


class TestDockerComposeParsing:
    """验证 docker-compose 配置能正确映射到安全配置"""

    def test_parse_user_from_compose(self):
        """从 docker-compose 配置解析 user 字段"""
        compose_config = {"user": "1000:1000"}
        config = AgentContainerSecurityConfig(user=compose_config["user"])
        assert config.user == "1000:1000"

    def test_parse_privileged_from_compose(self):
        """从 docker-compose 配置解析 privileged 字段"""
        compose_config = {"privileged": False}
        config = AgentContainerSecurityConfig(privileged=compose_config["privileged"])
        assert config.privileged is False

    def test_parse_readonly_from_compose(self):
        """从 docker-compose 配置解析 read_only 字段"""
        compose_config = {"read_only": True}
        config = AgentContainerSecurityConfig(read_only_rootfs=compose_config["read_only"])
        assert config.read_only_rootfs is True

    def test_parse_cap_drop_from_compose(self):
        """从 docker-compose 配置解析 cap_drop 字段"""
        compose_config = {"cap_drop": ["SYS_ADMIN", "NET_ADMIN"]}
        config = AgentContainerSecurityConfig(cap_drop=compose_config["cap_drop"])
        assert "SYS_ADMIN" in config.cap_drop
        assert "NET_ADMIN" in config.cap_drop

    def test_default_config_is_insecure(self, validator):
        """默认未配置的安全配置应不安全（安全优先）"""
        config = AgentContainerSecurityConfig()
        report = validator.validate(config)
        assert report["passed"] is False, "默认配置不应自动通过安全校验"

    def test_dockerfile_user_devflow_passes(self, validator):
        """Dockerfile 中定义的 devflow 用户应通过非 root 校验"""
        config = _build_secure_config(user="devflow")
        result = validator._check_non_root(config)
        assert result["passed"] is True


# =============================================================================
# 测试类 7：边界情况
# =============================================================================


class TestEdgeCases:
    """边界情况测试"""

    def test_uid_1_daemon_user_passes(self, validator):
        """UID 1（daemon 用户）应通过非 root 校验"""
        config = _build_secure_config(user="1")
        result = validator._check_non_root(config)
        assert result["passed"] is True

    def test_uid_65534_nobody_passes(self, validator):
        """UID 65534（nobody 用户）应通过非 root 校验"""
        config = _build_secure_config(user="65534")
        result = validator._check_non_root(config)
        assert result["passed"] is True

    def test_cap_drop_all_passes(self, validator):
        """cap_drop ALL 应通过文件系统隔离校验"""
        config = _build_secure_config(cap_drop=["ALL"])
        result = validator._check_filesystem_isolation(config)
        assert result["passed"] is True

    def test_multiple_dangerous_mounts_all_detected(self, validator):
        """多个危险挂载应全部被检测到"""
        config = _build_secure_config(
            volumes=[
                VolumeMount(source="/proc", target="/h-proc", mode="ro"),
                VolumeMount(source="/sys", target="/h-sys", mode="ro"),
                VolumeMount(source="/dev", target="/h-dev", mode="rw"),
            ],
        )
        result = validator._check_filesystem_isolation(config)
        assert result["passed"] is False
        issues = result["issues"]
        assert any("proc" in issue.lower() for issue in issues)
        assert any("sys" in issue.lower() for issue in issues)
        assert any("dev" in issue.lower() for issue in issues)

    def test_network_rule_empty_host_allowed_is_ok(self, validator):
        """network_rule 中 host 为空且 allowed=True 不应被误判"""
        config = _build_secure_config(
            network_rules=[
                NetworkRule(protocol="tcp", host="", port=80, allowed=True),
            ],
        )
        result = validator._check_network_isolation(config)
        assert result["passed"] is True

    def test_allowed_services_subset_of_whitelist_with_extra_fails(self, validator):
        """白名单子集加上额外服务应被拒绝"""
        config = _build_secure_config(
            allowed_services={"ollama", "swarm-executor", "mysql"},
        )
        result = validator._check_network_isolation(config)
        assert result["passed"] is False

    def test_network_rule_port_zero_does_not_cause_false_positive(self, validator):
        """network_rule 端口为 0 不应导致误报"""
        config = _build_secure_config(
            network_rules=[
                NetworkRule(protocol="tcp", host="ollama", port=0, allowed=True),
            ],
        )
        result = validator._check_network_isolation(config)
        assert result["passed"] is True

    def test_cap_add_net_raw_is_dangerous(self, validator):
        """cap_add NET_RAW 应被拒绝（高危能力）"""
        config = _build_secure_config(
            cap_drop=["ALL"],
            cap_add=["NET_RAW"],
        )
        result = validator._check_filesystem_isolation(config)
        assert result["passed"] is False

    def test_cap_add_sys_ptrace_is_dangerous(self, validator):
        """cap_add SYS_PTRACE 应被拒绝（高危能力）"""
        config = _build_secure_config(
            cap_drop=["ALL"],
            cap_add=["SYS_PTRACE"],
        )
        result = validator._check_filesystem_isolation(config)
        assert result["passed"] is False
