import pytest
import time
from fastapi import FastAPI, HTTPException, Header
from fastapi.testclient import TestClient
from pydantic import BaseModel
from uuid import uuid4, UUID
from datetime import datetime, timezone
from typing import Optional


class Role(BaseModel):
    id: str
    name: str
    description: str
    permissions: list[str]
    created_at: str
    created_by: str


class CreateRoleRequest(BaseModel):
    name: str
    description: str
    permissions: list[str]


class AssignRoleRequest(BaseModel):
    user_id: str
    role_id: str


app = FastAPI()


roles_db: dict[str, Role] = {}
user_roles_db: dict[str, list[str]] = {}


def is_admin(user_id: str) -> bool:
    return user_id == "admin-001"


@app.post("/api/roles", status_code=201)
def create_role(request: CreateRoleRequest, user_id: str = Header("admin-001")):
    if not is_admin(user_id):
        raise HTTPException(status_code=403, detail="Forbidden")
    role_id = str(uuid4())
    now = datetime.now(timezone.utc).isoformat()
    role = Role(
        id=role_id,
        name=request.name,
        description=request.description,
        permissions=request.permissions,
        created_at=now,
        created_by=user_id,
    )
    roles_db[role_id] = role
    return role


@app.post("/api/users/{user_id}/roles")
def assign_role_to_user(user_id: str, request: AssignRoleRequest):
    if request.role_id not in roles_db:
        raise HTTPException(status_code=404, detail="Role not found")
    if user_id not in user_roles_db:
        user_roles_db[user_id] = []
    user_roles_db[user_id].append(request.role_id)
    return {"message": "Role assigned"}


@pytest.fixture(autouse=True)
def clear_db():
    roles_db.clear()
    user_roles_db.clear()


@pytest.fixture
def client():
    return TestClient(app)


class TestAdminCreateCustomRole:
    def test_create_role_returns_201_and_role_record(self, client):
        request_data = {
            "name": "custom-editor",
            "description": "Custom editor with limited permissions",
            "permissions": ["read", "write"],
        }
        response = client.post(
            "/api/roles",
            json=request_data,
            headers={"user-id": "admin-001"},
        )
        assert response.status_code == 201
        body = response.json()
        assert body["name"] == "custom-editor"
        assert body["description"] == "Custom editor with limited permissions"
        assert body["permissions"] == ["read", "write"]
        assert "id" in body
        assert body["created_by"] == "admin-001"
        role_id = body["id"]
        assert role_id in roles_db
        assert roles_db[role_id].name == "custom-editor"

    def test_create_role_response_time_within_300ms(self, client):
        request_data = {
            "name": "fast-role",
            "description": "test",
            "permissions": ["read"],
        }
        start = time.perf_counter()
        response = client.post(
            "/api/roles",
            json=request_data,
            headers={"user-id": "admin-001"},
        )
        elapsed = (time.perf_counter() - start) * 1000
        assert response.status_code == 201
        assert elapsed <= 300, f"Response took {elapsed:.2f}ms, expected ≤300ms"

    def test_new_role_can_be_assigned_to_user(self, client):
        create_resp = client.post(
            "/api/roles",
            json={
                "name": "assignable-role",
                "description": "test",
                "permissions": ["read"],
            },
            headers={"user-id": "admin-001"},
        )
        assert create_resp.status_code == 201
        role_id = create_resp.json()["id"]
        assign_resp = client.post(
            f"/api/users/user-999/roles",
            json={"user_id": "user-999", "role_id": role_id},
        )
        assert assign_resp.status_code == 200
        assert assign_resp.json()["message"] == "Role assigned"
        assert role_id in user_roles_db["user-999"]

    def test_non_admin_cannot_create_role(self, client):
        response = client.post(
            "/api/roles",
            json={
                "name": "unauthorized",
                "description": "test",
                "permissions": ["read"],
            },
            headers={"user-id": "user-999"},
        )
        assert response.status_code == 403
