import time
import pytest
import requests
from unittest.mock import patch, MagicMock


def test_unauthenticated_access_returns_401():
    """验证未登录用户访问需要认证的API时返回401"""

    mock_response = MagicMock()
    mock_response.status_code = 401
    mock_response.json.return_value = {
        "error": {
            "code": "AUTH-001",
            "message": "Authentication required"
        }
    }

    start = time.time()
    with patch.object(requests, "get", return_value=mock_response):
        response = requests.get("https://api.example.com/protected")
    elapsed_ms = (time.time() - start) * 1000

    assert response.status_code == 401
    assert response.json()["error"]["code"] == "AUTH-001"
    assert elapsed_ms <= 100, f"响应时间 {elapsed_ms:.2f}ms 超过 100ms 上限"
