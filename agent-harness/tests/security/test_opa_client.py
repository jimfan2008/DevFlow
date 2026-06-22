import pytest
from backend.security.opa_client import OPAClient, OPARequest


class TestOPAClient:
    def test_opa_request_model(self):
        req = OPARequest(
            action="register_agent",
            subject="spiffe://prod/admin",
            resource="agent:hr-sourcer",
        )
        assert req.action == "register_agent"
        assert req.subject == "spiffe://prod/admin"

    def test_opa_allow_all_policy(self):
        client = OPAClient(opa_url="http://test:8181")
        # With no real OPA, default should be deny
        assert client._default_decision() is False

    def test_opa_prepare_input(self):
        client = OPAClient(opa_url="http://test:8181")
        inp = client._prepare_input(
            "delete_agent", "spiffe://prod/admin", "agent:db-prod"
        )
        assert inp["input"]["action"] == "delete_agent"
        assert inp["input"]["subject"] == "spiffe://prod/admin"
