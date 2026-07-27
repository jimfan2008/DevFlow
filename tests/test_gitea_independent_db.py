import pytest
import yaml
from pathlib import Path

COMPOSE_FILE = Path(__file__).resolve().parents[1] / "docker-compose.dev.yml"


def load_compose():
    with open(COMPOSE_FILE, "r", encoding="utf-8") as f:
        return yaml.safe_load(f)


@pytest.fixture
def compose():
    return load_compose()


class TestGiteaDBIndependence:
    """验证Gitea使用独立的PostgreSQL实例，不共享主库集群和数据目录。"""

    def test_gitea_db_service_exists(self, compose):
        services = compose.get("services", {})
        assert "gitea-db" in services, "缺少 gitea-db 服务定义"

    def test_main_postgres_service_exists(self, compose):
        services = compose.get("services", {})
        assert "postgres" in services, "缺少主 postgres 服务定义"

    def test_gitea_service_exists(self, compose):
        services = compose.get("services", {})
        assert "gitea" in services, "缺少 gitea 服务定义"

    def test_gitea_db_separate_container(self, compose):
        gitea_db = compose["services"]["gitea-db"]
        main_postgres = compose["services"]["postgres"]
        assert gitea_db["container_name"] != main_postgres["container_name"], (
            "Gitea 数据库应与主库使用不同容器名称"
        )
        assert gitea_db["container_name"] == "devflow-gitea-db-dev"
        assert main_postgres["container_name"] == "devflow-postgres-dev"

    def test_gitea_db_different_user(self, compose):
        gitea_db = compose["services"]["gitea-db"]
        main_postgres = compose["services"]["postgres"]
        gitea_env = parse_env(gitea_db.get("environment", []))
        main_env = parse_env(main_postgres.get("environment", []))
        assert gitea_env["POSTGRES_USER"] != main_env["POSTGRES_USER"], (
            "Gitea 数据库应与主库使用不同用户"
        )
        assert gitea_env["POSTGRES_USER"] == "gitea"

    def test_gitea_db_different_database(self, compose):
        gitea_db = compose["services"]["gitea-db"]
        main_postgres = compose["services"]["postgres"]
        gitea_env = parse_env(gitea_db.get("environment", []))
        main_env = parse_env(main_postgres.get("environment", []))
        assert gitea_env["POSTGRES_DB"] != main_env["POSTGRES_DB"], (
            "Gitea 数据库应与主库使用不同数据库名"
        )
        assert gitea_env["POSTGRES_DB"] == "gitea"

    def test_gitea_db_different_password(self, compose):
        gitea_db = compose["services"]["gitea-db"]
        main_postgres = compose["services"]["postgres"]
        gitea_env = parse_env(gitea_db.get("environment", []))
        main_env = parse_env(main_postgres.get("environment", []))
        assert gitea_env["POSTGRES_PASSWORD"] != main_env["POSTGRES_PASSWORD"], (
            "Gitea 数据库应与主库使用不同密码"
        )
        assert gitea_env["POSTGRES_PASSWORD"] == "gitea_password"

    def test_gitea_db_different_port(self, compose):
        gitea_db = compose["services"]["gitea-db"]
        main_postgres = compose["services"]["postgres"]
        gitea_ports = gitea_db.get("ports", [])
        main_ports = main_postgres.get("ports", [])
        assert gitea_ports != main_ports, (
            "Gitea 数据库应与主库映射不同端口"
        )
        assert "5433:5432" in gitea_ports

    def test_gitea_db_separate_volume(self, compose):
        gitea_db = compose["services"]["gitea-db"]
        main_postgres = compose["services"]["postgres"]
        gitea_vols = gitea_db.get("volumes", [])
        main_vols = main_postgres.get("volumes", [])
        gitea_data_vol = [v for v in gitea_vols if "/var/lib/postgresql/data" in str(v)]
        main_data_vol = [v for v in main_vols if "/var/lib/postgresql/data" in str(v)]
        assert len(gitea_data_vol) > 0, "Gitea 数据库应挂载数据目录"
        assert len(main_data_vol) > 0, "主数据库应挂载数据目录"
        gitea_vol_src = str(gitea_data_vol[0]).split(":")[0]
        main_vol_src = str(main_data_vol[0]).split(":")[0]
        assert gitea_vol_src != main_vol_src, (
            "Gitea 数据库应与主库使用独立数据目录"
        )
        assert gitea_vol_src == "gitea_db_dev_data"

    def test_gitea_db_volume_defined(self, compose):
        volumes = compose.get("volumes", {})
        assert "gitea_db_dev_data" in volumes, (
            "应在 volumes 中定义 gitea_db_dev_data"
        )
        vol_config = volumes["gitea_db_dev_data"]
        if isinstance(vol_config, dict):
            assert vol_config.get("name") == "devflow_gitea_db_dev_data"

    def test_gitea_connects_to_gitea_db(self, compose):
        gitea = compose["services"]["gitea"]
        gitea_env = parse_env(gitea.get("environment", []))
        db_host = gitea_env.get("GITEA__database__HOST", "")
        assert db_host == "gitea-db:5432", (
            f"Gitea 应连接 gitea-db:5432，实际连接 {db_host}"
        )

    def test_gitea_depends_on_gitea_db(self, compose):
        gitea = compose["services"]["gitea"]
        depends = gitea.get("depends_on", {})
        if isinstance(depends, dict):
            assert "gitea-db" in depends, (
                "Gitea 应依赖 gitea-db 服务"
            )
        elif isinstance(depends, list):
            assert "gitea-db" in depends, (
                "Gitea 应依赖 gitea-db 服务"
            )

    def test_gitea_db_healthcheck(self, compose):
        gitea_db = compose["services"]["gitea-db"]
        healthcheck = gitea_db.get("healthcheck", {})
        assert healthcheck, "Gitea 数据库应定义健康检查"
        test_cmd = healthcheck.get("test", [])
        test_str = " ".join(str(t) for t in test_cmd)
        assert "gitea" in test_str, (
            "健康检查应验证 gitea 用户/数据库"
        )

    def test_no_shared_data_directories(self, compose):
        gitea_db = compose["services"]["gitea-db"]
        main_postgres = compose["services"]["postgres"]
        gitea_vols = set(str(v) for v in gitea_db.get("volumes", []))
        main_vols = set(str(v) for v in main_postgres.get("volumes", []))
        pg_data_vols = {}
        for v in gitea_vols:
            if "/var/lib/postgresql/data" in v:
                pg_data_vols["gitea-db"] = v
        for v in main_vols:
            if "/var/lib/postgresql/data" in v:
                pg_data_vols["postgres"] = v
        assert pg_data_vols["gitea-db"] != pg_data_vols["postgres"], (
            "两个 PostgreSQL 实例不应共享数据目录"
        )


def parse_env(env_list):
    """将环境变量列表解析为字典。"""
    result = {}
    if isinstance(env_list, dict):
        return env_list
    for item in env_list:
        if "=" in str(item):
            key, value = str(item).split("=", 1)
            result[key] = value
    return result
