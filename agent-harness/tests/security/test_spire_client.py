import pytest
from backend.security.spire_client import SPIREIdentity


class TestSPIREIdentity:
    def test_parse_valid_spiffe_id(self):
        identity = SPIREIdentity()
        result = identity.parse_spiffe_id("spiffe://prod/agent/hr-sourcer")
        assert result["trust_domain"] == "prod"
        assert result["path"] == "/agent/hr-sourcer"

    def test_parse_invalid_spiffe_id(self):
        identity = SPIREIdentity()
        result = identity.parse_spiffe_id("not-spiffe")
        assert result is None

    def test_validate_id_format(self):
        identity = SPIREIdentity()
        assert identity.is_valid("spiffe://prod/agent/hr") is True
        assert identity.is_valid("spiffe://prod/workflow/abc") is True
        assert identity.is_valid("spiffe:///no-domain") is False
