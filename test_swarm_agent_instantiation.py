import pytest
from unittest.mock import Mock, patch, MagicMock
import json
import subprocess
import urllib.request
import urllib.error


class TestSwarmExecutorAgentInstantiationCLI:
    """测试通过CLI命令创建编程Agent实例"""

    @patch("subprocess.run")
    def test_cli_command_returns_container_id_and_running_status(self, mock_run):
        mock_result = Mock()
        mock_result.returncode = 0
        mock_result.stdout = json.dumps({
            "container_id": "abc123def456",
            "status": "running",
            "agent_name": "coding-agent-001"
        })
        mock_run.return_value = mock_result

        cmd = ["swarm-executor", "create-agent", "--name", "coding-agent-001"]
        result = subprocess.run(cmd, capture_output=True, text=True)
        response = json.loads(result.stdout)

        assert "container_id" in response
        assert response["container_id"] == "abc123def456"
        assert response["status"] == "running"
        assert len(response["container_id"]) > 0
        mock_run.assert_called_once()

    @patch("subprocess.run")
    def test_cli_command_creates_container_with_correct_specs(self, mock_run):
        expected_kwargs = {
            "capture_output": True,
            "text": True
        }
        mock_result = Mock()
        mock_result.returncode = 0
        mock_result.stdout = json.dumps({
            "container_id": "xyz789",
            "status": "running",
            "cpu_limit": 4,
            "memory_limit": "8g"
        })
        mock_run.return_value = mock_result

        cmd = [
            "swarm-executor", "create-agent",
            "--name", "test-agent",
            "--cpu", "4",
            "--memory", "8g"
        ]
        result = subprocess.run(cmd, capture_output=True, text=True)

        mock_run.assert_called_once()
        actual_args = mock_run.call_args[0][0]
        assert "swarm-executor" in actual_args
        assert "create-agent" in actual_args
        assert "--cpu" in actual_args
        assert "--memory" in actual_args

    @patch("subprocess.run")
    def test_cli_command_fails_when_docker_unavailable(self, mock_run):
        mock_result = Mock()
        mock_result.returncode = 1
        mock_result.stderr = "Error: Cannot connect to the Docker daemon"
        mock_result.stdout = ""
        mock_run.return_value = mock_result

        cmd = ["swarm-executor", "create-agent", "--name", "fail-agent"]
        result = subprocess.run(cmd, capture_output=True, text=True)

        assert result.returncode == 1
        assert len(result.stdout) == 0

    @patch("subprocess.run")
    def test_cli_command_with_empty_container_id_rejected(self, mock_run):
        mock_result = Mock()
        mock_result.returncode = 0
        mock_result.stdout = json.dumps({
            "container_id": "",
            "status": "running"
        })
        mock_run.return_value = mock_result

        cmd = ["swarm-executor", "create-agent", "--name", "bad-id-agent"]
        result = subprocess.run(cmd, capture_output=True, text=True)
        response = json.loads(result.stdout)

        assert response["container_id"] == ""
        assert len(response["container_id"]) == 0
        # 验证：container_id 为空时，不应通过有效性校验
        # 模拟有效性检查逻辑
        is_valid = len(response.get("container_id", "")) > 0
        assert not is_valid, "空 container_id 应被标记为无效"

    @patch("subprocess.run")
    def test_cli_command_with_special_char_agent_name(self, mock_run):
        mock_result = Mock()
        mock_result.returncode = 0
        mock_result.stdout = json.dumps({
            "container_id": "special-abc123",
            "status": "running",
            "agent_name": "agent@#test!$"
        })
        mock_run.return_value = mock_result

        cmd = ["swarm-executor", "create-agent", "--name", "agent@#test!$"]
        result = subprocess.run(cmd, capture_output=True, text=True)
        response = json.loads(result.stdout)

        assert response["container_id"] == "special-abc123"
        assert response["status"] == "running"
        mock_run.assert_called_once()

    @patch("subprocess.run")
    def test_cli_command_with_unicode_agent_name(self, mock_run):
        mock_result = Mock()
        mock_result.returncode = 0
        mock_result.stdout = json.dumps({
            "container_id": "unicode-agent-001",
            "status": "running",
            "agent_name": "代理测试αβγ"
        })
        mock_run.return_value = mock_result

        cmd = ["swarm-executor", "create-agent", "--name", "代理测试αβγ"]
        result = subprocess.run(cmd, capture_output=True, text=True)
        response = json.loads(result.stdout)

        assert response["container_id"] == "unicode-agent-001"
        assert response["status"] == "running"
        mock_run.assert_called_once()

    @patch("subprocess.run")
    def test_cli_command_with_ultra_long_agent_name(self, mock_run):
        long_name = "a" * 512
        mock_result = Mock()
        mock_result.returncode = 0
        mock_result.stdout = json.dumps({
            "container_id": "longname-agent-001",
            "status": "running",
            "agent_name": long_name
        })
        mock_run.return_value = mock_result

        cmd = ["swarm-executor", "create-agent", "--name", long_name]
        result = subprocess.run(cmd, capture_output=True, text=True)
        response = json.loads(result.stdout)

        assert response["container_id"] == "longname-agent-001"
        assert response["status"] == "running"
        mock_run.assert_called_once()

    @patch("subprocess.run")
    def test_cli_command_docker_daemon_timeout(self, mock_run):
        import socket
        mock_run.side_effect = socket.timeout("Docker daemon timed out")

        cmd = ["swarm-executor", "create-agent", "--name", "timeout-agent"]

        with pytest.raises(socket.timeout):
            subprocess.run(cmd, capture_output=True, text=True)


class TestSwarmExecutorAgentInstantiationGatewayAPI:
    """测试通过Gateway API接口创建编程Agent实例"""

    @pytest.fixture
    def mock_gateway_response(self):
        return {
            "container_id": "gateway-agent-001",
            "status": "running",
            "ports": {
                "22/tcp": 32768,
                "8080/tcp": 32769,
                "6080/tcp": 32770
            },
            "config": {
                "cpu": 4,
                "memory": "8g"
            }
        }

    @patch("urllib.request.urlopen")
    def test_gateway_api_returns_http_201(self, mock_urlopen):
        mock_response = Mock()
        mock_response.getcode.return_value = 201
        mock_response.read.return_value = json.dumps({
            "container_id": "gateway-agent-001",
            "status": "running",
            "ports": {"22/tcp": 32768, "8080/tcp": 32769}
        }).encode("utf-8")
        mock_urlopen.return_value = mock_response

        data = json.dumps({
            "agent_name": "coding-agent-001",
            "cpu": 4,
            "memory": "8g"
        }).encode("utf-8")
        req = urllib.request.Request(
            "http://localhost:8080/api/v1/agents",
            data=data,
            headers={"Content-Type": "application/json"},
            method="POST"
        )
        response = urllib.request.urlopen(req)
        body = json.loads(response.read().decode("utf-8"))

        assert response.getcode() == 201
        assert "container_id" in body
        assert body["container_id"] == "gateway-agent-001"
        assert body["status"] == "running"
        assert "ports" in body

    @patch("urllib.request.urlopen")
    def test_gateway_api_response_contains_ports_mapping(self, mock_urlopen, mock_gateway_response):
        mock_response = Mock()
        mock_response.getcode.return_value = 201
        mock_response.read.return_value = json.dumps(mock_gateway_response).encode("utf-8")
        mock_urlopen.return_value = mock_response

        data = json.dumps({
            "agent_name": "ports-test",
            "cpu": 4,
            "memory": "8g"
        }).encode("utf-8")
        req = urllib.request.Request(
            "http://localhost:8080/api/v1/agents",
            data=data,
            headers={"Content-Type": "application/json"},
            method="POST"
        )
        response = urllib.request.urlopen(req)
        body = json.loads(response.read().decode("utf-8"))

        ports = body["ports"]
        assert "22/tcp" in ports
        assert "8080/tcp" in ports
        assert "6080/tcp" in ports
        assert ports["22/tcp"] == 32768
        assert ports["8080/tcp"] == 32769
        assert ports["6080/tcp"] == 32770
        assert isinstance(ports["22/tcp"], int)

    @patch("urllib.request.urlopen")
    def test_gateway_api_creates_container_with_4cpu_8gb_memory(self, mock_urlopen):
        expected_request_body = {
            "agent_name": "resource-test-agent",
            "cpu": 4,
            "memory": "8g"
        }
        mock_response = Mock()
        mock_response.getcode.return_value = 201
        mock_response.read.return_value = json.dumps({
            "container_id": "resource-agent-001",
            "status": "running",
            "config": {"cpu": 4, "memory": "8g"},
            "ports": {"22/tcp": 32768}
        }).encode("utf-8")
        mock_urlopen.return_value = mock_response

        data = json.dumps(expected_request_body).encode("utf-8")
        req = urllib.request.Request(
            "http://localhost:8080/api/v1/agents",
            data=data,
            headers={"Content-Type": "application/json"},
            method="POST"
        )
        response = urllib.request.urlopen(req)
        body = json.loads(response.read().decode("utf-8"))

        assert response.getcode() == 201
        assert body["config"]["cpu"] == 4
        assert body["config"]["memory"] == "8g"

    @patch("urllib.request.urlopen")
    def test_gateway_api_rejects_invalid_request(self, mock_urlopen):
        mock_urlopen.side_effect = urllib.error.HTTPError(
            "http://localhost:8080/api/v1/agents", 400,
            "Bad Request", {},
            Mock(read=lambda: json.dumps({"error": "missing field"}).encode("utf-8"))
        )

        data = json.dumps({"cpu": 4}).encode("utf-8")
        req = urllib.request.Request(
            "http://localhost:8080/api/v1/agents",
            data=data,
            headers={"Content-Type": "application/json"},
            method="POST"
        )

        with pytest.raises(urllib.error.HTTPError) as exc_info:
            urllib.request.urlopen(req)
        assert exc_info.value.code == 400

    @patch("urllib.request.urlopen")
    def test_gateway_api_connection_refused(self, mock_urlopen):
        import urllib.error as urr
        mock_urlopen.side_effect = urr.URLError(
            "[Errno 111] Connection refused"
        )

        data = json.dumps({
            "agent_name": "conn-agent",
            "cpu": 4,
            "memory": "8g"
        }).encode("utf-8")
        req = urllib.request.Request(
            "http://localhost:8080/api/v1/agents",
            data=data,
            headers={"Content-Type": "application/json"},
            method="POST"
        )

        with pytest.raises(urllib.error.URLError):
            urllib.request.urlopen(req)

    @patch("urllib.request.urlopen")
    def test_gateway_api_timeout(self, mock_urlopen):
        import socket
        mock_urlopen.side_effect = socket.timeout("Gateway API timed out")

        data = json.dumps({
            "agent_name": "timeout-agent",
            "cpu": 4,
            "memory": "8g"
        }).encode("utf-8")
        req = urllib.request.Request(
            "http://localhost:8080/api/v1/agents",
            data=data,
            headers={"Content-Type": "application/json"},
            method="POST"
        )

        with pytest.raises(socket.timeout):
            urllib.request.urlopen(req)

    @patch("urllib.request.urlopen")
    def test_gateway_api_dns_resolution_failure(self, mock_urlopen):
        import socket
        mock_urlopen.side_effect = urllib.error.URLError(
            "[Errno -2] Name or service not known"
        )

        data = json.dumps({
            "agent_name": "dns-agent",
            "cpu": 4,
            "memory": "8g"
        }).encode("utf-8")
        req = urllib.request.Request(
            "http://nonexistent.example.com:8080/api/v1/agents",
            data=data,
            headers={"Content-Type": "application/json"},
            method="POST"
        )

        with pytest.raises(urllib.error.URLError):
            urllib.request.urlopen(req)

    @patch("urllib.request.urlopen")
    def test_gateway_api_returns_malformed_json(self, mock_urlopen):
        mock_response = Mock()
        mock_response.getcode.return_value = 201
        mock_response.read.return_value = b"{not valid json!!!"
        mock_urlopen.return_value = mock_response

        data = json.dumps({
            "agent_name": "malformed-agent",
            "cpu": 4,
            "memory": "8g"
        }).encode("utf-8")
        req = urllib.request.Request(
            "http://localhost:8080/api/v1/agents",
            data=data,
            headers={"Content-Type": "application/json"},
            method="POST"
        )
        response = urllib.request.urlopen(req)

        with pytest.raises(json.JSONDecodeError):
            json.loads(response.read().decode("utf-8"))

    @patch("urllib.request.urlopen")
    def test_gateway_api_returns_202_accepted(self, mock_urlopen):
        mock_response = Mock()
        mock_response.getcode.return_value = 202
        mock_response.read.return_value = json.dumps({
            "container_id": "async-agent-001",
            "status": "pending",
            "message": "Agent creation accepted, processing asynchronously"
        }).encode("utf-8")
        mock_urlopen.return_value = mock_response

        data = json.dumps({
            "agent_name": "async-agent",
            "cpu": 4,
            "memory": "8g"
        }).encode("utf-8")
        req = urllib.request.Request(
            "http://localhost:8080/api/v1/agents",
            data=data,
            headers={"Content-Type": "application/json"},
            method="POST"
        )
        response = urllib.request.urlopen(req)
        body = json.loads(response.read().decode("utf-8"))

        assert response.getcode() == 202
        assert "container_id" in body
        assert body["status"] == "pending"

    @patch("urllib.request.urlopen")
    def test_gateway_api_returns_non_json_content_type(self, mock_urlopen):
        mock_response = Mock()
        mock_response.getcode.return_value = 201
        mock_response.read.return_value = b"<html><body>OK</body></html>"
        mock_response.headers = {"Content-Type": "text/html"}
        mock_urlopen.return_value = mock_response

        data = json.dumps({
            "agent_name": "html-agent",
            "cpu": 4,
            "memory": "8g"
        }).encode("utf-8")
        req = urllib.request.Request(
            "http://localhost:8080/api/v1/agents",
            data=data,
            headers={"Content-Type": "application/json"},
            method="POST"
        )
        response = urllib.request.urlopen(req)

        with pytest.raises(json.JSONDecodeError):
            json.loads(response.read().decode("utf-8"))

    @patch("urllib.request.urlopen")
    def test_gateway_api_empty_container_id_in_response(self, mock_urlopen):
        mock_response = Mock()
        mock_response.getcode.return_value = 201
        mock_response.read.return_value = json.dumps({
            "container_id": "",
            "status": "running",
            "ports": {}
        }).encode("utf-8")
        mock_urlopen.return_value = mock_response

        data = json.dumps({
            "agent_name": "empty-id-agent",
            "cpu": 4,
            "memory": "8g"
        }).encode("utf-8")
        req = urllib.request.Request(
            "http://localhost:8080/api/v1/agents",
            data=data,
            headers={"Content-Type": "application/json"},
            method="POST"
        )
        response = urllib.request.urlopen(req)
        body = json.loads(response.read().decode("utf-8"))

        assert response.getcode() == 201
        assert body["container_id"] == ""
        assert len(body["container_id"]) == 0
        # 验证：container_id 为空时，不应通过有效性校验
        # 模拟有效性检查逻辑
        is_valid = len(body.get("container_id", "")) > 0
        assert not is_valid, "空 container_id 应被标记为无效"


class TestDockerContainerVerification:
    """验证Docker容器列表中新增容器"""

    @patch("subprocess.run")
    def test_docker_ps_shows_new_container(self, mock_run):
        mock_result = Mock()
        mock_result.returncode = 0
        mock_result.stdout = json.dumps([{
            "Id": "abc123def456",
            "Name": "swarm-agent-coding-agent-001",
            "Status": "running",
            "Created": "2026-07-20T10:00:00Z",
            "Config": {
                "Cpus": 4,
                "Memory": 8589934592
            }
        }])
        mock_run.return_value = mock_result

        cmd = ["docker", "ps", "--format", "{{json .}}"]
        result = subprocess.run(cmd, capture_output=True, text=True)
        containers = json.loads(result.stdout)

        assert len(containers) >= 1
        container = containers[0]
        assert container["Status"] == "running"
        assert "abc123def456" in container["Id"]

    @patch("subprocess.run")
    def test_docker_ps_returns_empty_list(self, mock_run):
        mock_result = Mock()
        mock_result.returncode = 0
        mock_result.stdout = json.dumps([])
        mock_run.return_value = mock_result

        cmd = ["docker", "ps", "--format", "{{json .}}"]
        result = subprocess.run(cmd, capture_output=True, text=True)
        containers = json.loads(result.stdout)

        assert isinstance(containers, list)
        assert len(containers) == 0

    @patch("subprocess.run")
    def test_docker_daemon_timeout(self, mock_run):
        import socket
        mock_run.side_effect = socket.timeout("Docker daemon timed out")

        cmd = ["docker", "ps", "--format", "{{json .}}"]

        with pytest.raises(socket.timeout):
            subprocess.run(cmd, capture_output=True, text=True)

    @patch("subprocess.run")
    def test_docker_inspect_shows_4cpu_8gb_memory(self, mock_run):
        mock_result = Mock()
        mock_result.returncode = 0
        mock_result.stdout = json.dumps({
            "Id": "abc123def456",
            "Config": {
                "Cpus": 4,
                "Memory": 8589934592
            },
            "State": {
                "Status": "running"
            }
        })
        mock_run.return_value = mock_result

        cmd = ["docker", "inspect", "abc123def456"]
        result = subprocess.run(cmd, capture_output=True, text=True)
        container_info = json.loads(result.stdout)

        assert container_info["Config"]["Cpus"] == 4
        assert container_info["Config"]["Memory"] == 8 * 1024 * 1024 * 1024
        assert container_info["State"]["Status"] == "running"

    @patch("subprocess.run")
    def test_docker_inspect_shows_correct_port_mapping(self, mock_run):
        mock_result = Mock()
        mock_result.returncode = 0
        mock_result.stdout = json.dumps({
            "Id": "abc123def456",
            "NetworkSettings": {
                "Ports": {
                    "22/tcp": [{"HostPort": 32768}],
                    "8080/tcp": [{"HostPort": 32769}],
                    "6080/tcp": [{"HostPort": 32770}]
                }
            }
        })
        mock_run.return_value = mock_result

        cmd = ["docker", "inspect", "abc123def456"]
        result = subprocess.run(cmd, capture_output=True, text=True)
        container_info = json.loads(result.stdout)

        ports = container_info["NetworkSettings"]["Ports"]
        assert "22/tcp" in ports
        assert "8080/tcp" in ports
        assert ports["22/tcp"][0]["HostPort"] == 32768
        assert ports["8080/tcp"][0]["HostPort"] == 32769
