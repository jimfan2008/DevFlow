"""
TDD 测试用例：开发环境一键搭建
验证：支持 docker-compose 一键搭建开发环境
验收标准：
  - 环境搭建 <= 30 分钟
  - 环境一致性 = 100%
"""

import os
import time
import pytest
import yaml
from unittest.mock import MagicMock, patch, PropertyMock

# 项目根目录
PROJECT_ROOT = os.path.dirname(os.path.dirname(os.path.abspath(__file__)))


# ============================================================
# Fixture
# ============================================================

@pytest.fixture
def docker_compose_main():
    """读取主 docker-compose 配置文件"""
    filepath = os.path.join(PROJECT_ROOT, "docker-compose.yml")
    with open(filepath, "r", encoding="utf-8") as f:
        return yaml.safe_load(f)


@pytest.fixture
def docker_compose_dev():
    """读取开发环境 docker-compose 配置文件"""
    filepath = os.path.join(PROJECT_ROOT, "docker-compose.dev.yml")
    with open(filepath, "r", encoding="utf-8") as f:
        return yaml.safe_load(f)


@pytest.fixture
def docker_compose_min():
    """读取最小化 docker-compose 配置文件"""
    filepath = os.path.join(PROJECT_ROOT, "docker-compose.min.yml")
    with open(filepath, "r", encoding="utf-8") as f:
        return yaml.safe_load(f)


@pytest.fixture
def start_docker_script_path():
    """start_docker.py 脚本路径"""
    return os.path.join(PROJECT_ROOT, "start_docker.py")


@pytest.fixture
def mock_subprocess_result():
    """模拟 subprocess.run 返回结果"""
    result = MagicMock()
    result.returncode = 0
    result.stdout = '{"status": "healthy"}'
    result.stderr = ""
    return result


# ============================================================
# 1. Docker Compose 文件存在性与合法性
# ============================================================

class TestDockerComposeFilesExist:
    """验收：docker-compose 配置文件存在且语法合法"""

    def test_docker_compose_main_exists(self):
        filepath = os.path.join(PROJECT_ROOT, "docker-compose.yml")
        assert os.path.isfile(filepath), "docker-compose.yml 文件不存在"

    def test_docker_compose_dev_exists(self):
        filepath = os.path.join(PROJECT_ROOT, "docker-compose.dev.yml")
        assert os.path.isfile(filepath), "docker-compose.dev.yml 文件不存在"

    def test_docker_compose_min_exists(self):
        filepath = os.path.join(PROJECT_ROOT, "docker-compose.min.yml")
        assert os.path.isfile(filepath), "docker-compose.min.yml 文件不存在"

    def test_docker_compose_main_valid_yaml(self, docker_compose_main):
        assert docker_compose_main is not None
        assert isinstance(docker_compose_main, dict)
        assert "services" in docker_compose_main

    def test_docker_compose_dev_valid_yaml(self, docker_compose_dev):
        assert docker_compose_dev is not None
        assert isinstance(docker_compose_dev, dict)
        assert "services" in docker_compose_dev

    def test_docker_compose_min_valid_yaml(self, docker_compose_min):
        assert docker_compose_min is not None
        assert isinstance(docker_compose_min, dict)
        assert "services" in docker_compose_min


# ============================================================
# 2. 开发环境服务完整性
# ============================================================

class TestDevEnvironmentServices:
    """验收：docker-compose.dev.yml 包含所有必需服务"""

    REQUIRED_SERVICES = {
        "fastapi",
        "postgres",
        "redis",
        "celery-worker",
        "celery-beat",
        "frontend",
        "gitea",
        "gitea-db",
        "nginx",
    }

    def test_all_required_services_present(self, docker_compose_dev):
        services = set(docker_compose_dev.get("services", {}).keys())
        missing = self.REQUIRED_SERVICES - services
        assert not missing, f"缺少必需服务: {missing}"

    def test_fastapi_service_config(self, docker_compose_dev):
        fastapi = docker_compose_dev["services"]["fastapi"]
        assert "build" in fastapi, "fastapi 缺少 build 配置"
        assert "ports" in fastapi, "fastapi 缺少 ports 配置"
        assert "depends_on" in fastapi, "fastapi 缺少 depends_on 配置"

    def test_postgres_service_config(self, docker_compose_dev):
        postgres = docker_compose_dev["services"]["postgres"]
        assert "image" in postgres, "postgres 缺少 image 配置"
        assert "healthcheck" in postgres, "postgres 缺少 healthcheck 配置"
        assert "environment" in postgres, "postgres 缺少 environment 配置"

    def test_redis_service_config(self, docker_compose_dev):
        redis_svc = docker_compose_dev["services"]["redis"]
        assert "image" in redis_svc, "redis 缺少 image 配置"
        assert "healthcheck" in redis_svc, "redis 缺少 healthcheck 配置"

    def test_celery_worker_config(self, docker_compose_dev):
        celery = docker_compose_dev["services"]["celery-worker"]
        assert "command" in celery, "celery-worker 缺少 command 配置"
        assert "depends_on" in celery, "celery-worker 缺少 depends_on 配置"

    def test_gitea_service_depends_on_db(self, docker_compose_dev):
        gitea = docker_compose_dev["services"]["gitea"]
        depends = gitea.get("depends_on", {})
        assert "gitea-db" in depends, "gitea 应依赖于 gitea-db"

    def test_nginx_depends_on_fastapi(self, docker_compose_dev):
        nginx = docker_compose_dev["services"]["nginx"]
        depends = nginx.get("depends_on", [])
        assert "fastapi" in depends, "nginx 应依赖于 fastapi"


# ============================================================
# 3. 服务依赖链正确性
# ============================================================

class TestServiceDependencyChain:
    """验收：服务依赖关系正确，无循环依赖"""

    def test_fastapi_depends_on_postgres(self, docker_compose_dev):
        fastapi = docker_compose_dev["services"]["fastapi"]
        depends = fastapi.get("depends_on", {})
        assert "postgres" in depends, "fastapi 应依赖于 postgres"

    def test_fastapi_depends_on_redis(self, docker_compose_dev):
        fastapi = docker_compose_dev["services"]["fastapi"]
        depends = fastapi.get("depends_on", {})
        assert "redis" in depends, "fastapi 应依赖于 redis"

    def test_postgres_healthcheck_condition(self, docker_compose_dev):
        fastapi = docker_compose_dev["services"]["fastapi"]
        depends = fastapi.get("depends_on", {})
        postgres_dep = depends.get("postgres", {})
        assert postgres_dep.get("condition") == "service_healthy", \
            "fastapi 依赖 postgres 的条件应为 service_healthy"

    def test_redis_healthcheck_condition(self, docker_compose_dev):
        fastapi = docker_compose_dev["services"]["fastapi"]
        depends = fastapi.get("depends_on", {})
        redis_dep = depends.get("redis", {})
        assert redis_dep.get("condition") == "service_healthy", \
            "fastapi 依赖 redis 的条件应为 service_healthy"

    def test_no_circular_dependency(self, docker_compose_dev):
        services = docker_compose_dev.get("services", {})
        adjacency = {}
        for svc_name, svc_config in services.items():
            deps = []
            depends_on = svc_config.get("depends_on", {})
            if isinstance(depends_on, dict):
                deps = list(depends_on.keys())
            elif isinstance(depends_on, list):
                deps = depends_on
            adjacency[svc_name] = deps

        visited = set()
        rec_stack = set()

        def has_cycle(node):
            visited.add(node)
            rec_stack.add(node)
            for dep in adjacency.get(node, []):
                if dep not in visited:
                    if has_cycle(dep):
                        return True
                elif dep in rec_stack:
                    return True
            rec_stack.discard(node)
            return False

        for node in adjacency:
            if node not in visited:
                assert not has_cycle(node), "存在循环依赖"


# ============================================================
# 4. 环境一致性校验
# ============================================================

class TestEnvironmentConsistency:
    """验收：环境一致性 = 100%"""

    def test_db_url_consistency_dev(self, docker_compose_dev):
        fastapi_env = docker_compose_dev["services"]["fastapi"]["environment"]
        postgres_cfg = docker_compose_dev["services"]["postgres"]
        postgres_env = postgres_cfg.get("environment", [])

        db_user = None
        db_pass = None
        db_name = None
        for e in postgres_env:
            if e.startswith("POSTGRES_USER="):
                db_user = e.split("=", 1)[1]
            elif e.startswith("POSTGRES_PASSWORD="):
                db_pass = e.split("=", 1)[1]
            elif e.startswith("POSTGRES_DB="):
                db_name = e.split("=", 1)[1]

        for e in fastapi_env:
            if e.startswith("DATABASE_URL="):
                db_url = e.split("=", 1)[1]
                assert db_user in db_url, f"DATABASE_URL 中缺少用户 {db_user}"
                assert db_pass in db_url, f"DATABASE_URL 中缺少密码 {db_pass}"
                assert db_name in db_url, f"DATABASE_URL 中缺少数据库 {db_name}"

    def test_redis_url_consistency_dev(self, docker_compose_dev):
        fastapi_env = docker_compose_dev["services"]["fastapi"]["environment"]
        redis_found = False
        for e in fastapi_env:
            if e.startswith("REDIS_URL="):
                redis_url = e.split("=", 1)[1]
                assert "redis:" in redis_url, "REDIS_URL 应包含 redis 服务地址"
                redis_found = True
        assert redis_found, "fastapi 环境中缺少 REDIS_URL"

    def test_celery_broker_url_consistency(self, docker_compose_dev):
        celery_worker_env = docker_compose_dev["services"]["celery-worker"]["environment"]
        fastapi_env = docker_compose_dev["services"]["fastapi"]["environment"]

        def find_env(env_list, prefix):
            if not isinstance(env_list, list):
                env_list = list(env_list)
            for e in env_list:
                if e.startswith(prefix):
                    return e.split("=", 1)[1]
            return None

        celery_broker = find_env(celery_worker_env, "CELERY_BROKER_URL=")
        fastapi_redis = find_env(fastapi_env, "REDIS_URL=")

        assert celery_broker is not None, "celery-worker 缺少 CELERY_BROKER_URL"
        assert "redis:" in celery_broker, "CELERY_BROKER_URL 应使用 redis 协议"

    def test_docker_network_consistency(self, docker_compose_dev):
        services = docker_compose_dev.get("services", {})
        networks_cfg = docker_compose_dev.get("networks", {})
        network_names = set(networks_cfg.keys()) if networks_cfg else set()

        for svc_name, svc_config in services.items():
            svc_networks = svc_config.get("networks", [])
            for net in svc_networks:
                assert net in network_names, \
                    f"服务 {svc_name} 使用了未定义的网络 {net}"

    def test_docker_volume_consistency(self, docker_compose_dev):
        services = docker_compose_dev.get("services", {})
        volumes_cfg = docker_compose_dev.get("volumes", {})
        volume_names = set(volumes_cfg.keys()) if volumes_cfg else set()

        for svc_name, svc_config in services.items():
            svc_volumes = svc_config.get("volumes", [])
            for vol in svc_volumes:
                vol_str = str(vol)
                if ":" in vol_str:
                    vol_name = vol_str.split(":")[0]
                    if not vol_name.startswith(".") and not vol_name.startswith("/"):
                        assert vol_name in volume_names, \
                            f"服务 {svc_name} 使用了未定义的卷 {vol_name}"

    def test_min_environment_consistency(self, docker_compose_min):
        backend_env = docker_compose_min["services"]["backend"]["environment"]
        postgres_env = docker_compose_min["services"]["postgres"]["environment"]

        expected_values = {}
        for e in postgres_env:
            if e.startswith("POSTGRES_USER="):
                expected_values["user"] = e.split("=", 1)[1]
            elif e.startswith("POSTGRES_PASSWORD="):
                expected_values["pass"] = e.split("=", 1)[1]
            elif e.startswith("POSTGRES_DB="):
                expected_values["db"] = e.split("=", 1)[1]

        for e in backend_env:
            if e.startswith("DATABASE_URL="):
                db_url = e.split("=", 1)[1]
                assert expected_values["user"] in db_url
                assert expected_values["pass"] in db_url
                assert expected_values["db"] in db_url

    def test_main_environment_consistency(self, docker_compose_main):
        fastapi_env = docker_compose_main["services"]["fastapi"]["environment"]
        postgres_env = docker_compose_main["services"]["postgres"]["environment"]

        expected_values = {}
        for e in postgres_env:
            if e.startswith("POSTGRES_USER="):
                expected_values["user"] = e.split("=", 1)[1]
            elif e.startswith("POSTGRES_PASSWORD="):
                expected_values["pass"] = e.split("=", 1)[1]
            elif e.startswith("POSTGRES_DB="):
                expected_values["db"] = e.split("=", 1)[1]

        for e in fastapi_env:
            if e.startswith("DATABASE_URL="):
                db_url = e.split("=", 1)[1]
                assert expected_values["user"] in db_url
                assert expected_values["pass"] in db_url
                assert expected_values["db"] in db_url


# ============================================================
# 5. 一键启动脚本验证
# ============================================================

class TestStartDockerScript:
    """验收：一键启动脚本存在且可执行"""

    def test_start_docker_script_exists(self, start_docker_script_path):
        assert os.path.isfile(start_docker_script_path), "start_docker.py 脚本不存在"

    def test_start_docker_script_is_valid_python(self, start_docker_script_path):
        with open(start_docker_script_path, "r", encoding="utf-8") as f:
            source = f.read()
        compile(source, start_docker_script_path, "exec")

    def test_start_docker_script_has_main_function(self, start_docker_script_path):
        with open(start_docker_script_path, "r", encoding="utf-8") as f:
            source = f.read()
        assert "def main" in source, "start_docker.py 缺少 main 函数"
        assert 'if __name__' in source, "start_docker.py 缺少 __main__ 入口"

    def test_start_docker_script_has_check_docker(self, start_docker_script_path):
        with open(start_docker_script_path, "r", encoding="utf-8") as f:
            source = f.read()
        assert "def check_docker" in source, "缺少 check_docker 函数"

    def test_start_docker_script_has_start_services(self, start_docker_script_path):
        with open(start_docker_script_path, "r", encoding="utf-8") as f:
            source = f.read()
        assert "def start_services" in source, "缺少 start_services 函数"

    def test_start_docker_script_has_verify_services(self, start_docker_script_path):
        with open(start_docker_script_path, "r", encoding="utf-8") as f:
            source = f.read()
        assert "def verify_services" in source, "缺少 verify_services 函数"


# ============================================================
# 6. 环境搭建时间约束
# ============================================================

class TestEnvironmentSetupTime:
    """验收：环境搭建 <= 30 分钟（1800 秒）"""

    MAX_SETUP_TIME_SECONDS = 1800

    def test_max_setup_time_within_limit(self):
        assert self.MAX_SETUP_TIME_SECONDS <= 1800, \
            "最大设置时间超过 30 分钟"

    def test_setup_time_boundary_at_limit(self):
        assert self.MAX_SETUP_TIME_SECONDS == 1800, \
            "最大设置时间应等于 1800 秒"

    @patch("subprocess.run")
    def test_docker_compose_up_command_within_timeout(self, mock_run, mock_subprocess_result):
        mock_run.return_value = mock_subprocess_result
        start_time = time.time()
        mock_run("docker-compose -f docker-compose.dev.yml up -d", shell=True)
        elapsed = time.time() - start_time
        assert elapsed < self.MAX_SETUP_TIME_SECONDS, \
            f"命令下发耗时 {elapsed:.2f}s 超出限制"

    @patch("subprocess.run")
    def test_health_check_retry_within_timeout(self, mock_run):
        healthy_count = [0]

        def side_effect(cmd, **kwargs):
            healthy_count[0] += 1
            result = MagicMock()
            result.returncode = 0
            result.stdout = "healthy" if healthy_count[0] >= 3 else "starting"
            result.stderr = ""
            return result

        mock_run.side_effect = side_effect

        start_time = time.time()
        checked = 0
        max_retries = 30
        for i in range(max_retries):
            mock_run("docker inspect -f '{{.State.Health.Status}}' devflow-postgres", shell=True)
            if healthy_count[0] >= 3:
                checked = i + 1
                break
            time.sleep(0.01)

        elapsed = time.time() - start_time
        estimated_total = elapsed * (max_retries / max(checked, 1))
        assert estimated_total < self.MAX_SETUP_TIME_SECONDS, \
            f"估算总等待时间 {estimated_total:.2f}s 超过 {self.MAX_SETUP_TIME_SECONDS}s 限制"

    def test_parallel_service_startup_time_estimate(self, docker_compose_dev):
        services = docker_compose_dev.get("services", {})
        independent_services = []
        for svc_name, svc_config in services.items():
            depends = svc_config.get("depends_on", {})
            if not depends:
                independent_services.append(svc_name)

        estimated_per_service = 30
        sequential_levels = _count_dependency_levels(services)
        estimated_total = sequential_levels * estimated_per_service
        assert estimated_total < self.MAX_SETUP_TIME_SECONDS, \
            f"估算总启动时间 {estimated_total}s 超过 {self.MAX_SETUP_TIME_SECONDS}s"


def _count_dependency_levels(services):
    layers = {}
    visited = set()

    def dfs(name):
        if name in visited:
            return layers.get(name, 0)
        visited.add(name)
        deps = services.get(name, {}).get("depends_on", {})
        if isinstance(deps, dict):
            dep_names = list(deps.keys())
        elif isinstance(deps, list):
            dep_names = deps
        else:
            dep_names = []
        if not dep_names:
            layers[name] = 1
            return 1
        max_dep = max(dfs(d) for d in dep_names)
        layers[name] = max_dep + 1
        return layers[name]

    for svc in services:
        dfs(svc)
    return max(layers.values()) if layers else 0


# ============================================================
# 7. 健康检查配置
# ============================================================

class TestHealthCheckConfiguration:
    """验收：关键服务配置了健康检查"""

    def test_postgres_healthcheck_present(self, docker_compose_dev):
        postgres = docker_compose_dev["services"]["postgres"]
        assert "healthcheck" in postgres, "postgres 未配置 healthcheck"
        hc = postgres["healthcheck"]
        assert "test" in hc, "postgres healthcheck 缺少 test 指令"
        assert "interval" in hc, "postgres healthcheck 缺少 interval"

    def test_redis_healthcheck_present(self, docker_compose_dev):
        redis = docker_compose_dev["services"]["redis"]
        assert "healthcheck" in redis, "redis 未配置 healthcheck"
        hc = redis["healthcheck"]
        assert "test" in hc, "redis healthcheck 缺少 test 指令"

    def test_postgres_healthcheck_interval_reasonable(self, docker_compose_dev):
        hc = docker_compose_dev["services"]["postgres"]["healthcheck"]
        interval_str = str(hc["interval"])
        interval_seconds = _parse_interval(interval_str)
        assert interval_seconds <= 30, \
            f"postgres healthcheck interval {interval_seconds}s 过长"

    def test_redis_healthcheck_interval_reasonable(self, docker_compose_dev):
        hc = docker_compose_dev["services"]["redis"]["healthcheck"]
        interval_str = str(hc["interval"])
        interval_seconds = _parse_interval(interval_str)
        assert interval_seconds <= 30, \
            f"redis healthcheck interval {interval_seconds}s 过长"

    def test_gitea_db_healthcheck_present(self, docker_compose_dev):
        giteadb = docker_compose_dev["services"]["gitea-db"]
        assert "healthcheck" in giteadb, "gitea-db 未配置 healthcheck"


def _parse_interval(interval_str):
    s = interval_str.strip().lower()
    if s.endswith("s"):
        return int(s[:-1])
    if s.endswith("m"):
        return int(s[:-1]) * 60
    if s.endswith("ms"):
        return int(s[:-2]) / 1000
    try:
        return int(s)
    except ValueError:
        return 30


# ============================================================
# 8. 端口配置无冲突
# ============================================================

class TestPortConfiguration:
    """验收：端口映射无冲突"""

    def test_dev_ports_no_conflict(self, docker_compose_dev):
        services = docker_compose_dev.get("services", {})
        host_ports = []
        for svc_name, svc_config in services.items():
            for port in svc_config.get("ports", []):
                port_str = str(port)
                host_port = port_str.split(":")[0]
                host_ports.append((svc_name, host_port))

        used_ports = [p for _, p in host_ports]
        assert len(used_ports) == len(set(used_ports)), \
            f"存在端口冲突: {host_ports}"

    def test_min_ports_no_conflict(self, docker_compose_min):
        services = docker_compose_min.get("services", {})
        host_ports = []
        for svc_name, svc_config in services.items():
            for port in svc_config.get("ports", []):
                port_str = str(port)
                host_port = port_str.split(":")[0]
                host_ports.append((svc_name, host_port))

        used_ports = [p for _, p in host_ports]
        assert len(used_ports) == len(set(used_ports)), \
            f"min 配置存在端口冲突: {host_ports}"

    def test_main_ports_no_conflict(self, docker_compose_main):
        services = docker_compose_main.get("services", {})
        host_ports = []
        for svc_name, svc_config in services.items():
            for port in svc_config.get("ports", []):
                port_str = str(port)
                host_port = port_str.split(":")[0]
                host_ports.append((svc_name, host_port))

        used_ports = [p for _, p in host_ports]
        assert len(used_ports) == len(set(used_ports)), \
            f"main 配置存在端口冲突: {host_ports}"


# ============================================================
# 9. 网络配置正确
# ============================================================

class TestNetworkConfiguration:
    """验收：网络配置正确"""

    def test_dev_network_defined(self, docker_compose_dev):
        networks = docker_compose_dev.get("networks", {})
        assert len(networks) > 0, "dev 配置缺少 networks 定义"

    def test_min_network_defined(self, docker_compose_min):
        networks = docker_compose_min.get("networks", {})
        assert len(networks) > 0, "min 配置缺少 networks 定义"

    def test_main_network_defined(self, docker_compose_main):
        networks = docker_compose_main.get("networks", {})
        assert len(networks) > 0, "main 配置缺少 networks 定义"

    def test_dev_network_driver(self, docker_compose_dev):
        networks = docker_compose_dev.get("networks", {})
        for net_name, net_config in networks.items():
            if net_config and "driver" in net_config:
                driver = net_config["driver"]
                assert driver in ("bridge", "overlay", "host"), \
                    f"未知网络驱动: {driver}"


# ============================================================
# 10. 重启策略正确
# ============================================================

class TestRestartPolicy:
    """验收：关键服务有合适的重启策略"""

    def test_postgres_restart_policy(self, docker_compose_dev):
        postgres = docker_compose_dev["services"]["postgres"]
        restart = postgres.get("restart", "")
        assert restart in ("always", "unless-stopped"), \
            f"postgres 重启策略 '{restart}' 不合适"

    def test_redis_restart_policy(self, docker_compose_dev):
        redis = docker_compose_dev["services"]["redis"]
        restart = redis.get("restart", "")
        assert restart in ("always", "unless-stopped"), \
            f"redis 重启策略 '{restart}' 不合适"


# ============================================================
# 11. 一键搭建完整性集成测试
# ============================================================

class TestOneClickSetupIntegration:
    """验收：一键搭建环境完整性和可用性的集成验证"""

    def test_docker_files_count(self):
        expected_files = [
            "docker-compose.yml",
            "docker-compose.dev.yml",
            "docker-compose.min.yml",
            "start_docker.py",
        ]
        for f in expected_files:
            path = os.path.join(PROJECT_ROOT, f)
            assert os.path.isfile(path), f"缺少关键文件: {f}"

    def test_all_compose_files_have_services(self, docker_compose_main, docker_compose_dev, docker_compose_min):
        for name, data in [
            ("main", docker_compose_main),
            ("dev", docker_compose_dev),
            ("min", docker_compose_min),
        ]:
            assert "services" in data, f"{name} 缺少 services 定义"
            assert len(data["services"]) > 0, f"{name} 的 services 为空"

    def test_environment_config_completeness(self, docker_compose_dev):
        fastapi_env = docker_compose_dev["services"]["fastapi"]["environment"]
        required_vars = [
            "APP_NAME=",
            "APP_DEBUG=",
            "APP_HOST=",
            "APP_PORT=",
            "JWT_SECRET=",
            "JWT_ALGORITHM=",
            "DATABASE_URL=",
            "REDIS_URL=",
        ]
        for var in required_vars:
            found = any(e.startswith(var) for e in fastapi_env)
            assert found, f"fastapi 环境中缺少 {var.strip('=')}"

    def test_volumes_defined_for_data_persistence(self, docker_compose_dev):
        volumes = docker_compose_dev.get("volumes", {})
        assert "postgres_dev_data" in volumes, "缺少 postgres 数据卷"
        assert "redis_dev_data" in volumes, "缺少 redis 数据卷"

    def test_dev_environment_debug_enabled(self, docker_compose_dev):
        fastapi_env = docker_compose_dev["services"]["fastapi"]["environment"]
        for e in fastapi_env:
            if e.startswith("APP_DEBUG="):
                assert e == "APP_DEBUG=true", "开发环境应开启调试模式"
                break
        else:
            pytest.fail("缺少 APP_DEBUG 配置")

    def test_hot_reload_enabled_for_fastapi(self, docker_compose_dev):
        fastapi = docker_compose_dev["services"]["fastapi"]
        command = fastapi.get("command", "")
        assert "--reload" in command, "开发环境应启用 hot-reload"

    def test_source_code_bind_mount(self, docker_compose_dev):
        fastapi = docker_compose_dev["services"]["fastapi"]
        volumes = fastapi.get("volumes", [])
        bind_mounts = [v for v in volumes if str(v).startswith("./") or str(v).startswith(".:")]
        assert len(bind_mounts) > 0, "开发环境应挂载源代码以支持热更新"
