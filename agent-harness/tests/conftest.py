import pytest
from unittest.mock import AsyncMock, patch


@pytest.fixture(autouse=True)
def mock_opa_client():
    mock = AsyncMock(return_value=True)
    with patch("backend.security.opa_client.OPAClient.check_permission", mock):
        yield
