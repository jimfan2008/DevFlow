import pytest
from unittest.mock import MagicMock, PropertyMock


class DockerHealthMonitor:
    def __init__(self, client=None):
        self.client = client
        self.health_check_interval = 10

    def get_container_health(self, container_name):
        container = self.client.containers.get(container_name)
        attrs = container.attrs
        health = attrs.get("State", {}).get("Health", {})
        return health.get("Status", "unknown")

    def _get_health_from_container(self, container):
        attrs = container.attrs
        health = attrs.get("State", {}).get("Health", {})
        return health.get("Status", "unknown")

    def check_all_containers_healthy(self):
        containers = self.client.containers.list()
        for container in containers:
            health_status = self._get_health_from_container(container)
            if health_status != "healthy":
                return False
        return True

    def restart_unhealthy_containers(self):
        containers = self.client.containers.list()
        restarted = []
        for container in containers:
            health_status = self._get_health_from_container(container)
            if health_status == "unhealthy":
                container.restart()
                restarted.append(container.name)
        return restarted


@pytest.fixture
def mock_docker_client():
    return MagicMock()


@pytest.fixture
def monitor(mock_docker_client):
    return DockerHealthMonitor(client=mock_docker_client)


def create_mock_container(name, health_status, health_log=None):
    container = MagicMock()
    container.name = name
    health = {"Status": health_status}
    if health_log:
        health["Log"] = health_log
    type(container).attrs = PropertyMock(
        return_value={"State": {"Health": health}}
    )
    return container


class TestDockerContainerHealthStatus:
    def test_single_container_healthy(self, monitor, mock_docker_client):
        container = create_mock_container("devflow-postgres", "healthy")
        mock_docker_client.containers.get.return_value = container
        status = monitor.get_container_health("devflow-postgres")
        assert status == "healthy"

    def test_single_container_unhealthy(self, monitor, mock_docker_client):
        container = create_mock_container("devflow-postgres", "unhealthy")
        mock_docker_client.containers.get.return_value = container
        status = monitor.get_container_health("devflow-postgres")
        assert status == "unhealthy"

    def test_single_container_starting(self, monitor, mock_docker_client):
        container = create_mock_container("devflow-redis", "starting")
        mock_docker_client.containers.get.return_value = container
        status = monitor.get_container_health("devflow-redis")
        assert status == "starting"

    def test_container_not_found(self, monitor, mock_docker_client):
        mock_docker_client.containers.get.side_effect = Exception("container not found")
        with pytest.raises(Exception):
            monitor.get_container_health("nonexistent")

    def test_container_state_no_health_key(self, monitor, mock_docker_client):
        container = MagicMock()
        container.name = "devflow-nginx"
        type(container).attrs = PropertyMock(return_value={"State": {}})
        mock_docker_client.containers.get.return_value = container
        status = monitor.get_container_health("devflow-nginx")
        assert status == "unknown"


class TestAllContainersHealthy:
    def test_all_containers_healthy(self, monitor, mock_docker_client):
        containers = [
            create_mock_container("devflow-postgres", "healthy"),
            create_mock_container("devflow-redis", "healthy"),
            create_mock_container("devflow-fastapi", "healthy"),
        ]
        mock_docker_client.containers.list.return_value = containers
        assert monitor.check_all_containers_healthy() is True

    def test_one_container_unhealthy(self, monitor, mock_docker_client):
        containers = [
            create_mock_container("devflow-postgres", "healthy"),
            create_mock_container("devflow-redis", "unhealthy"),
            create_mock_container("devflow-fastapi", "healthy"),
        ]
        mock_docker_client.containers.list.return_value = containers
        assert monitor.check_all_containers_healthy() is False

    def test_no_containers(self, monitor, mock_docker_client):
        mock_docker_client.containers.list.return_value = []
        assert monitor.check_all_containers_healthy() is True

    def test_mixed_health_statuses(self, monitor, mock_docker_client):
        containers = [
            create_mock_container("devflow-postgres", "healthy"),
            create_mock_container("devflow-redis", "starting"),
            create_mock_container("devflow-fastapi", "healthy"),
        ]
        mock_docker_client.containers.list.return_value = containers
        assert monitor.check_all_containers_healthy() is False


class TestHealthCheckInterval:
    def test_default_interval_within_limit(self, monitor):
        assert monitor.health_check_interval <= 30

    def test_interval_configured_to_10s(self, monitor):
        assert monitor.health_check_interval == 10

    def test_interval_can_be_customized(self, monitor):
        monitor.health_check_interval = 5
        assert monitor.health_check_interval <= 30

    def test_interval_at_boundary(self, monitor):
        monitor.health_check_interval = 30
        assert monitor.health_check_interval <= 30

    def test_interval_exceeds_limit_detection(self, monitor):
        monitor.health_check_interval = 31
        assert monitor.health_check_interval > 30


class TestUnhealthyContainerAutoRestart:
    def test_restart_unhealthy_container(self, monitor, mock_docker_client):
        unhealthy = create_mock_container("devflow-redis", "unhealthy")
        healthy = create_mock_container("devflow-postgres", "healthy")
        mock_docker_client.containers.list.return_value = [unhealthy, healthy]
        restarted = monitor.restart_unhealthy_containers()
        unhealthy.restart.assert_called_once()
        assert "devflow-redis" in restarted

    def test_no_restart_when_all_healthy(self, monitor, mock_docker_client):
        containers = [
            create_mock_container("devflow-postgres", "healthy"),
            create_mock_container("devflow-redis", "healthy"),
        ]
        mock_docker_client.containers.list.return_value = containers
        restarted = monitor.restart_unhealthy_containers()
        assert restarted == []

    def test_multiple_unhealthy_containers(self, monitor, mock_docker_client):
        unhealthy1 = create_mock_container("devflow-postgres", "unhealthy")
        unhealthy2 = create_mock_container("devflow-redis", "unhealthy")
        mock_docker_client.containers.list.return_value = [unhealthy1, unhealthy2]
        restarted = monitor.restart_unhealthy_containers()
        assert len(restarted) == 2
        unhealthy1.restart.assert_called_once()
        unhealthy2.restart.assert_called_once()

    def test_starting_container_not_restarted(self, monitor, mock_docker_client):
        starting = create_mock_container("devflow-redis", "starting")
        mock_docker_client.containers.list.return_value = [starting]
        restarted = monitor.restart_unhealthy_containers()
        assert restarted == []

    def test_restart_returns_container_names(self, monitor, mock_docker_client):
        unhealthy = create_mock_container("devflow-redis", "unhealthy")
        mock_docker_client.containers.list.return_value = [unhealthy]
        restarted = monitor.restart_unhealthy_containers()
        assert restarted == ["devflow-redis"]

    def test_restart_container_raises_exception(self, monitor, mock_docker_client):
        unhealthy = create_mock_container("devflow-redis", "unhealthy")
        unhealthy.restart.side_effect = Exception("restart failed")
        mock_docker_client.containers.list.return_value = [unhealthy]
        with pytest.raises(Exception, match="restart failed"):
            monitor.restart_unhealthy_containers()


class TestDockerHealthMonitorEdgeCases:
    def test_attrs_is_empty_dict(self, monitor, mock_docker_client):
        container = MagicMock()
        type(container).attrs = PropertyMock(return_value={})
        mock_docker_client.containers.get.return_value = container
        status = monitor.get_container_health("devflow-postgres")
        assert status == "unknown"

    def test_attrs_is_none(self, monitor, mock_docker_client):
        container = MagicMock()
        type(container).attrs = PropertyMock(return_value=None)
        mock_docker_client.containers.get.return_value = container
        with pytest.raises(AttributeError):
            monitor.get_container_health("devflow-postgres")

    def test_containers_list_raises_exception(self, monitor, mock_docker_client):
        mock_docker_client.containers.list.side_effect = Exception("daemon unavailable")
        with pytest.raises(Exception, match="daemon unavailable"):
            monitor.check_all_containers_healthy()

    def test_containers_list_raises_exception_on_restart(self, monitor, mock_docker_client):
        mock_docker_client.containers.list.side_effect = Exception("daemon unavailable")
        with pytest.raises(Exception, match="daemon unavailable"):
            monitor.restart_unhealthy_containers()
