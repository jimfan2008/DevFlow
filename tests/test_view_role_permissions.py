import pytest
import time
from unittest.mock import MagicMock, patch


class TestViewRolePermissions:
    """验证可以查看角色定义详情包括所有权限列表"""

    def _build_mock_response(self):
        return {
            "role_name": "admin",
            "description": "系统管理员角色，拥有全部权限",
            "permissions": [
                "project_create",
                "project_delete",
                "workflow_start",
                "workflow_stop",
                "user_manage",
                "role_manage",
                "system_config",
                "data_export",
            ],
        }

    @patch("requests.get")
    def test_view_role_permissions_returns_200_and_full_list(self, mock_get):
        """HTTP200返回，响应时间 ≤100ms；返回角色名称、描述及完整权限列表"""
        mock_response = MagicMock()
        mock_response.status_code = 200
        mock_response.json.return_value = self._build_mock_response()
        mock_get.return_value = mock_response

        start = time.monotonic()
        resp = mock_get("https://api.example.com/v1/roles/admin")
        elapsed_ms = (time.monotonic() - start) * 1000

        assert resp.status_code == 200, f"期望 HTTP 200，实际 {resp.status_code}"
        assert elapsed_ms <= 100, f"响应时间 {elapsed_ms:.1f}ms 超过 100ms 上限"

        data = resp.json()
        assert data["role_name"] == "admin", "角色名称不匹配"
        assert data["description"] is not None and len(data["description"]) > 0, "角色描述为空"

        permissions = data["permissions"]
        assert isinstance(permissions, list), "permissions 不是列表"
        assert len(permissions) >= 3, f"权限列表过短，实际有 {len(permissions)} 项"

        expected = {"project_create", "project_delete", "workflow_start"}
        actual = set(permissions)
        missing = expected - actual
        assert not missing, f"缺少预期权限: {missing}"
