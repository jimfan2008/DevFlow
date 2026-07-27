import pytest
import re
import time
from typing import Set, Optional
from fastapi import FastAPI, APIRouter, HTTPException, status
from fastapi.testclient import TestClient
from pydantic import BaseModel, validator

VALID_ROLES: Set[str] = {"admin", "manager", "developer", "viewer"}
ROLE_CONSTRAINT_SQL = "CHECK (role IN ('admin', 'manager', 'developer', 'viewer'))"

PREDEFINED_ROLES = [
    {"name": "System Administrator", "role": "admin"},
    {"name": "Project Manager", "role": "manager"},
    {"name": "Developer", "role": "developer"},
    {"name": "Read-only Observer", "role": "viewer"},
]


def validate_role(role: Optional[str]) -> bool:
    if role is None:
        return False
    return role in VALID_ROLES


class RoleCreate(BaseModel):
    name: str
    role: str

    @validator("role")
    def role_must_be_predefined(cls, v):
        if v not in VALID_ROLES:
            raise ValueError(f"role must be one of {sorted(VALID_ROLES)}")
        return v


role_router = APIRouter()


@role_router.get("/api/roles")
def list_predefined_roles():
    return PREDEFINED_ROLES


@role_router.post("/api/roles", status_code=status.HTTP_201_CREATED)
def create_predefined_role(role: RoleCreate):
    return {"name": role.name, "role": role.role}


def build_test_client() -> TestClient:
    app = FastAPI()
    app.include_router(role_router)
    return TestClient(app)


class TestPredefinedRolesAPI:
    def test_returns_200_and_four_roles(self):
        client = build_test_client()
        response = client.get("/api/roles")
        assert response.status_code == 200
        roles = response.json()
        assert len(roles) == 4
        role_types = {r["role"] for r in roles}
        assert role_types == VALID_ROLES

    def test_role_names_match_expectations(self):
        client = build_test_client()
        response = client.get("/api/roles")
        assert response.status_code == 200
        roles = response.json()
        by_role = {r["role"]: r["name"] for r in roles}
        assert by_role["admin"] == "System Administrator"
        assert by_role["manager"] == "Project Manager"
        assert by_role["developer"] == "Developer"
        assert by_role["viewer"] == "Read-only Observer"


class TestResponseTime:
    def test_single_request_within_limit(self):
        client = build_test_client()
        start = time.perf_counter()
        response = client.get("/api/roles")
        elapsed = (time.perf_counter() - start) * 1000
        assert response.status_code == 200
        assert elapsed <= 200, f"{elapsed:.1f} ms exceeds 200 ms limit"

    @pytest.mark.parametrize("count", [5, 10, 20])
    def test_consecutive_requests_within_limit(self, count):
        client = build_test_client()
        times = []
        for _ in range(count):
            start = time.perf_counter()
            response = client.get("/api/roles")
            elapsed = (time.perf_counter() - start) * 1000
            assert response.status_code == 200
            times.append(elapsed)
        avg = sum(times) / len(times)
        assert avg <= 200, f"Average {avg:.1f} ms over {count} requests exceeds limit"


class TestRoleValidation:
    def test_each_valid_role_passes(self):
        for role in VALID_ROLES:
            assert validate_role(role), f"'{role}' should be valid"

    def test_none_rejected(self):
        assert not validate_role(None)

    def test_empty_string_rejected(self):
        assert not validate_role("")

    def test_invalid_role_string_rejected(self):
        assert not validate_role("superadmin")
        assert not validate_role("guest")
        assert not validate_role("auditor")

    def test_special_characters_rejected(self):
        assert not validate_role("admin; drop table")
        assert not validate_role("' OR '1'='1")
        assert not validate_role("<script>")

    def test_case_variation_rejected(self):
        assert not validate_role("Admin")
        assert not validate_role("ADMIN")
        assert not validate_role("Manager")

    def test_whitespace_rejected(self):
        assert not validate_role(" admin")
        assert not validate_role("admin ")
        assert not validate_role("  ")


class TestRoleAPIAcceptReject:
    def test_valid_role_accepted_by_api(self):
        client = build_test_client()
        for role in VALID_ROLES:
            response = client.post("/api/roles", json={"name": "Tester", "role": role})
            assert response.status_code == 201, f"role '{role}' should be accepted"

    def test_invalid_role_rejected_with_422(self):
        client = build_test_client()
        response = client.post("/api/roles", json={"name": "Hacker", "role": "superadmin"})
        assert response.status_code == 422

    def test_empty_role_rejected_with_422(self):
        client = build_test_client()
        response = client.post("/api/roles", json={"name": "Hacker", "role": ""})
        assert response.status_code == 422

    def test_none_role_rejected_with_422(self):
        client = build_test_client()
        response = client.post("/api/roles", json={"name": "Hacker", "role": None})
        assert response.status_code == 422

    def test_special_char_role_rejected_with_422(self):
        client = build_test_client()
        response = client.post("/api/roles", json={"name": "Hacker", "role": "admin'--"})
        assert response.status_code == 422

    def test_case_variant_role_rejected_with_422(self):
        client = build_test_client()
        response = client.post("/api/roles", json={"name": "Hacker", "role": "Admin"})
        assert response.status_code == 422


class TestDBConstraint:
    def test_constraint_contains_all_valid_roles(self):
        for role in VALID_ROLES:
            assert role in ROLE_CONSTRAINT_SQL, f"'{role}' missing from SQL constraint"

    def test_constraint_exact_count(self):
        tokens = re.findall(r"'([^']+)'", ROLE_CONSTRAINT_SQL)
        assert len(tokens) == 4

    def test_unit_roles_are_unique(self):
        assert len(VALID_ROLES) == 4


class TestIdempotency:
    def test_multiple_requests_return_same_roles(self):
        client = build_test_client()
        first = client.get("/api/roles").json()
        for _ in range(3):
            response = client.get("/api/roles")
            assert response.status_code == 200
            assert response.json() == first

    def test_roles_set_is_stable(self):
        client = build_test_client()
        responses = [client.get("/api/roles").json() for _ in range(5)]
        role_sets = [{r["role"] for r in resp} for resp in responses]
        for rs in role_sets:
            assert rs == VALID_ROLES
