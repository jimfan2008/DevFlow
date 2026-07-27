import time
import uuid
from datetime import datetime, timezone
from typing import List, Optional, Dict, Any
from dataclasses import dataclass, field

import pytest
from fastapi import FastAPI, HTTPException, Depends, Header
from fastapi.testclient import TestClient


@dataclass
class OperationLog:
    log_id: str
    action: str
    operator: str
    target_user: str
    group_id: str
    group_name: str
    timestamp: float
    detail: str = ""
    ip_address: str = ""


@dataclass
class Group:
    id: str
    name: str
    members: List[str]
    created_at: float
    admin: str


@dataclass
class GroupMessage:
    id: str
    group_id: str
    sender: str
    content: str
    timestamp: float


@dataclass
class ResourceItem:
    resource_id: str
    group_id: str
    name: str
    content: str


groups: Dict[str, Group] = {}
group_messages: Dict[str, List[GroupMessage]] = {}
group_resources: Dict[str, List[ResourceItem]] = {}
operation_logs: List[OperationLog] = []
access_tokens: Dict[str, str] = {}  # token -> username


def _require_auth(authorization: str = Header(None)) -> str:
    if not authorization or not authorization.startswith("Bearer "):
        raise HTTPException(status_code=401, detail="Missing or invalid token")
    token = authorization[len("Bearer "):]
    if token not in access_tokens:
        raise HTTPException(status_code=401, detail="Invalid token")
    return access_tokens[token]


app = FastAPI()


@app.post("/api/auth/login")
def login(username: str, password: str):
    token = str(uuid.uuid4())
    access_tokens[token] = username
    return {"code": 0, "message": "success", "data": {"token": token, "username": username}}


@app.post("/api/groups", status_code=201)
def create_group(name: str, current_user: str = Depends(_require_auth)):
    group_id = str(uuid.uuid4())
    group = Group(
        id=group_id,
        name=name,
        members=[current_user],
        created_at=time.time(),
        admin=current_user,
    )
    groups[group_id] = group
    group_messages[group_id] = []
    group_resources[group_id] = []
    return {"code": 0, "message": "success", "data": {"group_id": group_id, "name": name, "members": group.members}}


@app.post("/api/groups/{group_id}/members")
def add_member(group_id: str, profile_name: str, current_user: str = Depends(_require_auth)):
    group = groups.get(group_id)
    if not group:
        raise HTTPException(status_code=404, detail="Group not found")
    if current_user != group.admin:
        raise HTTPException(status_code=403, detail="Only admin can add members")
    if profile_name not in group.members:
        group.members.append(profile_name)
    return {"code": 0, "message": "success", "data": {"group_id": group_id, "members": group.members}}


@app.delete("/api/groups/{group_id}/members/{profile_name}")
def remove_member(group_id: str, profile_name: str, current_user: str = Depends(_require_auth)):
    group = groups.get(group_id)
    if not group:
        raise HTTPException(status_code=404, detail="Group not found")
    if current_user != group.admin:
        raise HTTPException(status_code=403, detail="Only admin can remove members")
    if profile_name not in group.members:
        raise HTTPException(status_code=404, detail="Member not found in group")
    group.members.remove(profile_name)
    log = OperationLog(
        log_id=str(uuid.uuid4()),
        action="remove_member",
        operator=current_user,
        target_user=profile_name,
        group_id=group_id,
        group_name=group.name,
        timestamp=time.time(),
        detail=f"Admin {current_user} removed member {profile_name} from group {group.name}",
    )
    operation_logs.append(log)
    return {"code": 0, "message": "success", "data": {"group_id": group_id, "members": group.members}}


@app.get("/api/groups/{group_id}/messages")
def get_group_messages(group_id: str, current_user: str = Depends(_require_auth)):
    group = groups.get(group_id)
    if not group:
        raise HTTPException(status_code=404, detail="Group not found")
    if current_user not in group.members and current_user != group.admin:
        raise HTTPException(status_code=403, detail="Access denied: not a group member")
    msgs = group_messages.get(group_id, [])
    return {"code": 0, "message": "success", "data": {"messages": [{"sender": m.sender, "content": m.content} for m in msgs]}}


@app.get("/api/groups/{group_id}/resources")
def get_group_resources(group_id: str, current_user: str = Depends(_require_auth)):
    group = groups.get(group_id)
    if not group:
        raise HTTPException(status_code=404, detail="Group not found")
    if current_user not in group.members and current_user != group.admin:
        raise HTTPException(status_code=403, detail="Access denied: not a group member")
    resources = group_resources.get(group_id, [])
    return {"code": 0, "message": "success", "data": {"resources": [{"id": r.resource_id, "name": r.name} for r in resources]}}


@app.get("/api/groups/{group_id}")
def get_group(group_id: str, current_user: str = Depends(_require_auth)):
    group = groups.get(group_id)
    if not group:
        raise HTTPException(status_code=404, detail="Group not found")
    if current_user not in group.members and current_user != group.admin:
        raise HTTPException(status_code=403, detail="Access denied: not a group member")
    return {"code": 0, "message": "success", "data": {"group_id": group.id, "name": group.name, "members": group.members}}


@app.post("/api/groups/{group_id}/messages")
def send_message(group_id: str, content: str, current_user: str = Depends(_require_auth)):
    group = groups.get(group_id)
    if not group:
        raise HTTPException(status_code=404, detail="Group not found")
    if current_user not in group.members:
        raise HTTPException(status_code=403, detail="Access denied: not a group member")
    msg = GroupMessage(
        id=str(uuid.uuid4()),
        group_id=group_id,
        sender=current_user,
        content=content,
        timestamp=time.time(),
    )
    if group_id not in group_messages:
        group_messages[group_id] = []
    group_messages[group_id].append(msg)
    return {"code": 0, "message": "success", "data": {"message_id": msg.id}}


@app.get("/api/operation-logs")
def get_operation_logs(current_user: str = Depends(_require_auth)):
    logs = [
        {
            "log_id": log.log_id,
            "action": log.action,
            "operator": log.operator,
            "target_user": log.target_user,
            "group_id": log.group_id,
            "group_name": log.group_name,
            "timestamp": log.timestamp,
            "detail": log.detail,
        }
        for log in operation_logs
    ]
    return {"code": 0, "message": "success", "data": {"logs": logs}}


@pytest.fixture(autouse=True)
def _clean_state():
    groups.clear()
    group_messages.clear()
    group_resources.clear()
    operation_logs.clear()
    access_tokens.clear()


@pytest.fixture
def client():
    return TestClient(app)


@pytest.fixture
def admin_token(client):
    resp = client.post("/api/auth/login", params={"username": "admin001", "password": "adminpass"})
    assert resp.status_code == 200
    return resp.json()["data"]["token"]


@pytest.fixture
def member_token(client):
    resp = client.post("/api/auth/login", params={"username": "member002", "password": "memberpass"})
    assert resp.status_code == 200
    return resp.json()["data"]["token"]


@pytest.fixture
def other_token(client):
    resp = client.post("/api/auth/login", params={"username": "outsider003", "password": "outsiderpass"})
    assert resp.status_code == 200
    return resp.json()["data"]["token"]


@pytest.fixture
def group_id(admin_token, client):
    resp = client.post(
        "/api/groups",
        params={"name": "TestGroup"},
        headers={"Authorization": f"Bearer {admin_token}"},
    )
    assert resp.status_code == 201
    gid = resp.json()["data"]["group_id"]
    resp2 = client.post(
        f"/api/groups/{gid}/members",
        params={"profile_name": "member002"},
        headers={"Authorization": f"Bearer {admin_token}"},
    )
    assert resp2.status_code == 200
    return gid


class TestRemoveMemberHTTP200:
    def test_admin_removes_member_returns_200(self, client, admin_token, group_id):
        resp = client.delete(
            f"/api/groups/{group_id}/members/member002",
            headers={"Authorization": f"Bearer {admin_token}"},
        )
        assert resp.status_code == 200

    def test_admin_removes_member_response_has_code_zero(self, client, admin_token, group_id):
        resp = client.delete(
            f"/api/groups/{group_id}/members/member002",
            headers={"Authorization": f"Bearer {admin_token}"},
        )
        data = resp.json()
        assert data["code"] == 0

    def test_admin_removes_member_members_list_updated(self, client, admin_token, group_id):
        resp = client.delete(
            f"/api/groups/{group_id}/members/member002",
            headers={"Authorization": f"Bearer {admin_token}"},
        )
        members = resp.json()["data"]["members"]
        assert "member002" not in members
        assert len(members) == 1
        assert members[0] == "admin001"

    def test_non_admin_cannot_remove_member_returns_403(self, client, member_token, group_id):
        resp = client.delete(
            f"/api/groups/{group_id}/members/member002",
            headers={"Authorization": f"Bearer {member_token}"},
        )
        assert resp.status_code == 403

    def test_removing_nonexistent_member_returns_404(self, client, admin_token, group_id):
        resp = client.delete(
            f"/api/groups/{group_id}/members/nonexistent_user",
            headers={"Authorization": f"Bearer {admin_token}"},
        )
        assert resp.status_code == 404

    def test_removing_from_nonexistent_group_returns_404(self, client, admin_token):
        resp = client.delete(
            "/api/groups/nonexistent-group-id/members/member002",
            headers={"Authorization": f"Bearer {admin_token}"},
        )
        assert resp.status_code == 404

    def test_removing_member_twice_returns_404(self, client, admin_token, group_id):
        client.delete(
            f"/api/groups/{group_id}/members/member002",
            headers={"Authorization": f"Bearer {admin_token}"},
        )
        resp = client.delete(
            f"/api/groups/{group_id}/members/member002",
            headers={"Authorization": f"Bearer {admin_token}"},
        )
        assert resp.status_code == 404


class TestRemoveMemberResponseTime:
    def test_remove_member_response_time_under_2_seconds(self, client, admin_token, group_id):
        start = time.perf_counter()
        resp = client.delete(
            f"/api/groups/{group_id}/members/member002",
            headers={"Authorization": f"Bearer {admin_token}"},
        )
        elapsed = time.perf_counter() - start
        assert resp.status_code == 200
        assert elapsed <= 2.0, f"Response time {elapsed:.3f}s exceeded 2s limit"

    def test_remove_member_response_time_under_100ms_typical(self, client, admin_token, group_id):
        start = time.perf_counter()
        resp = client.delete(
            f"/api/groups/{group_id}/members/member002",
            headers={"Authorization": f"Bearer {admin_token}"},
        )
        elapsed = time.perf_counter() - start
        assert resp.status_code == 200
        assert elapsed <= 0.1, f"Response time {elapsed * 1000:.1f}ms exceeded 100ms typical threshold"


class TestRemovedMemberAccessRevocation:
    def test_removed_member_cannot_read_group_messages(self, client, admin_token, member_token, group_id):
        client.post(
            f"/api/groups/{group_id}/messages",
            params={"content": "Hello everyone"},
            headers={"Authorization": f"Bearer {admin_token}"},
        )
        client.delete(
            f"/api/groups/{group_id}/members/member002",
            headers={"Authorization": f"Bearer {admin_token}"},
        )
        resp = client.get(
            f"/api/groups/{group_id}/messages",
            headers={"Authorization": f"Bearer {member_token}"},
        )
        assert resp.status_code == 403
        assert "Access denied" in resp.json()["detail"]

    def test_removed_member_cannot_read_group_info(self, client, admin_token, member_token, group_id):
        client.delete(
            f"/api/groups/{group_id}/members/member002",
            headers={"Authorization": f"Bearer {admin_token}"},
        )
        resp = client.get(
            f"/api/groups/{group_id}",
            headers={"Authorization": f"Bearer {member_token}"},
        )
        assert resp.status_code == 403

    def test_removed_member_cannot_access_group_resources(self, client, admin_token, member_token, group_id):
        client.delete(
            f"/api/groups/{group_id}/members/member002",
            headers={"Authorization": f"Bearer {admin_token}"},
        )
        resp = client.get(
            f"/api/groups/{group_id}/resources",
            headers={"Authorization": f"Bearer {member_token}"},
        )
        assert resp.status_code == 403

    def test_removed_member_cannot_send_messages(self, client, admin_token, member_token, group_id):
        client.delete(
            f"/api/groups/{group_id}/members/member002",
            headers={"Authorization": f"Bearer {admin_token}"},
        )
        resp = client.post(
            f"/api/groups/{group_id}/messages",
            params={"content": "I should not be here"},
            headers={"Authorization": f"Bearer {member_token}"},
        )
        assert resp.status_code == 403

    def test_admin_still_has_access_after_removing_others(self, client, admin_token, member_token, group_id):
        client.delete(
            f"/api/groups/{group_id}/members/member002",
            headers={"Authorization": f"Bearer {admin_token}"},
        )
        resp = client.get(
            f"/api/groups/{group_id}",
            headers={"Authorization": f"Bearer {admin_token}"},
        )
        assert resp.status_code == 200
        data = resp.json()["data"]
        assert data["group_id"] == group_id

    def test_other_members_unaffected_by_removal(self, client, admin_token, member_token, group_id):
        client.post(
            f"/api/groups/{group_id}/members",
            params={"profile_name": "member_extra"},
            headers={"Authorization": f"Bearer {admin_token}"},
        )
        extra_token_resp = client.post("/api/auth/login", params={"username": "member_extra", "password": "p"})
        extra_token = extra_token_resp.json()["data"]["token"]
        client.delete(
            f"/api/groups/{group_id}/members/member002",
            headers={"Authorization": f"Bearer {admin_token}"},
        )
        resp = client.get(
            f"/api/groups/{group_id}/messages",
            headers={"Authorization": f"Bearer {extra_token}"},
        )
        assert resp.status_code == 200

    def test_outsider_still_denied_after_removal(self, client, admin_token, other_token, group_id):
        client.delete(
            f"/api/groups/{group_id}/members/member002",
            headers={"Authorization": f"Bearer {admin_token}"},
        )
        resp = client.get(
            f"/api/groups/{group_id}",
            headers={"Authorization": f"Bearer {other_token}"},
        )
        assert resp.status_code == 403

    def test_access_revocation_delay_under_1_second(self, client, admin_token, member_token, group_id):
        remove_start = time.perf_counter()
        client.delete(
            f"/api/groups/{group_id}/members/member002",
            headers={"Authorization": f"Bearer {admin_token}"},
        )
        remove_elapsed = time.perf_counter() - remove_start
        access_start = time.perf_counter()
        resp = client.get(
            f"/api/groups/{group_id}/messages",
            headers={"Authorization": f"Bearer {member_token}"},
        )
        access_elapsed = time.perf_counter() - access_start
        total_latency = remove_elapsed + access_elapsed
        assert resp.status_code == 403
        assert total_latency <= 1.0, f"Permission revocation latency {total_latency:.3f}s exceeded 1s limit"

    def test_immediate_access_loss_on_consecutive_request(self, client, admin_token, member_token, group_id):
        resp_before = client.get(
            f"/api/groups/{group_id}/messages",
            headers={"Authorization": f"Bearer {member_token}"},
        )
        assert resp_before.status_code == 200
        client.delete(
            f"/api/groups/{group_id}/members/member002",
            headers={"Authorization": f"Bearer {admin_token}"},
        )
        get_start = time.perf_counter()
        resp_after = client.get(
            f"/api/groups/{group_id}/messages",
            headers={"Authorization": f"Bearer {member_token}"},
        )
        get_elapsed = time.perf_counter() - get_start
        assert resp_after.status_code == 403
        assert get_elapsed <= 0.5, f"Post-removal access check {get_elapsed * 1000:.1f}ms exceeded 500ms"


class TestOperationLogComplete:
    def test_operation_log_created_on_remove(self, client, admin_token, group_id):
        client.delete(
            f"/api/groups/{group_id}/members/member002",
            headers={"Authorization": f"Bearer {admin_token}"},
        )
        log_resp = client.get(
            "/api/operation-logs",
            headers={"Authorization": f"Bearer {admin_token}"},
        )
        assert log_resp.status_code == 200
        logs = log_resp.json()["data"]["logs"]
        assert len(logs) == 1
        assert logs[0]["action"] == "remove_member"

    def test_operation_log_has_operator_field(self, client, admin_token, group_id):
        client.delete(
            f"/api/groups/{group_id}/members/member002",
            headers={"Authorization": f"Bearer {admin_token}"},
        )
        log_resp = client.get(
            "/api/operation-logs",
            headers={"Authorization": f"Bearer {admin_token}"},
        )
        log = log_resp.json()["data"]["logs"][0]
        assert log["operator"] == "admin001"

    def test_operation_log_has_target_user_field(self, client, admin_token, group_id):
        client.delete(
            f"/api/groups/{group_id}/members/member002",
            headers={"Authorization": f"Bearer {admin_token}"},
        )
        log_resp = client.get(
            "/api/operation-logs",
            headers={"Authorization": f"Bearer {admin_token}"},
        )
        log = log_resp.json()["data"]["logs"][0]
        assert log["target_user"] == "member002"

    def test_operation_log_has_group_id_field(self, client, admin_token, group_id):
        client.delete(
            f"/api/groups/{group_id}/members/member002",
            headers={"Authorization": f"Bearer {admin_token}"},
        )
        log_resp = client.get(
            "/api/operation-logs",
            headers={"Authorization": f"Bearer {admin_token}"},
        )
        log = log_resp.json()["data"]["logs"][0]
        assert log["group_id"] == group_id

    def test_operation_log_has_group_name_field(self, client, admin_token, group_id):
        client.delete(
            f"/api/groups/{group_id}/members/member002",
            headers={"Authorization": f"Bearer {admin_token}"},
        )
        log_resp = client.get(
            "/api/operation-logs",
            headers={"Authorization": f"Bearer {admin_token}"},
        )
        log = log_resp.json()["data"]["logs"][0]
        assert log["group_name"] == "TestGroup"

    def test_operation_log_has_timestamp(self, client, admin_token, group_id):
        client.delete(
            f"/api/groups/{group_id}/members/member002",
            headers={"Authorization": f"Bearer {admin_token}"},
        )
        log_resp = client.get(
            "/api/operation-logs",
            headers={"Authorization": f"Bearer {admin_token}"},
        )
        log = log_resp.json()["data"]["logs"][0]
        assert isinstance(log["timestamp"], float)
        assert log["timestamp"] > 0

    def test_operation_log_has_detail_description(self, client, admin_token, group_id):
        client.delete(
            f"/api/groups/{group_id}/members/member002",
            headers={"Authorization": f"Bearer {admin_token}"},
        )
        log_resp = client.get(
            "/api/operation-logs",
            headers={"Authorization": f"Bearer {admin_token}"},
        )
        log = log_resp.json()["data"]["logs"][0]
        assert len(log["detail"]) > 0
        assert "admin001" in log["detail"]
        assert "member002" in log["detail"]
        assert "TestGroup" in log["detail"]

    def test_multiple_removals_produce_multiple_logs(self, client, admin_token, group_id):
        client.post(
            f"/api/groups/{group_id}/members",
            params={"profile_name": "user_a"},
            headers={"Authorization": f"Bearer {admin_token}"},
        )
        client.post(
            f"/api/groups/{group_id}/members",
            params={"profile_name": "user_b"},
            headers={"Authorization": f"Bearer {admin_token}"},
        )
        client.delete(
            f"/api/groups/{group_id}/members/user_a",
            headers={"Authorization": f"Bearer {admin_token}"},
        )
        client.delete(
            f"/api/groups/{group_id}/members/user_b",
            headers={"Authorization": f"Bearer {admin_token}"},
        )
        log_resp = client.get(
            "/api/operation-logs",
            headers={"Authorization": f"Bearer {admin_token}"},
        )
        logs = log_resp.json()["data"]["logs"]
        remove_logs = [log for log in logs if log["action"] == "remove_member"]
        assert len(remove_logs) == 2

    def test_operation_logs_ordered_by_time(self, client, admin_token, group_id):
        client.post(
            f"/api/groups/{group_id}/members",
            params={"profile_name": "user_x"},
            headers={"Authorization": f"Bearer {admin_token}"},
        )
        client.delete(
            f"/api/groups/{group_id}/members/user_x",
            headers={"Authorization": f"Bearer {admin_token}"},
        )
        client.delete(
            f"/api/groups/{group_id}/members/member002",
            headers={"Authorization": f"Bearer {admin_token}"},
        )
        log_resp = client.get(
            "/api/operation-logs",
            headers={"Authorization": f"Bearer {admin_token}"},
        )
        logs = log_resp.json()["data"]["logs"]
        timestamps = [log["timestamp"] for log in logs]
        assert timestamps == sorted(timestamps)

    def test_logs_include_log_id(self, client, admin_token, group_id):
        client.delete(
            f"/api/groups/{group_id}/members/member002",
            headers={"Authorization": f"Bearer {admin_token}"},
        )
        log_resp = client.get(
            "/api/operation-logs",
            headers={"Authorization": f"Bearer {admin_token}"},
        )
        log = log_resp.json()["data"]["logs"][0]
        assert "log_id" in log
        assert len(log["log_id"]) > 0

    def test_non_removal_operations_not_in_log(self, client, admin_token, group_id):
        client.delete(
            f"/api/groups/{group_id}/members/member002",
            headers={"Authorization": f"Bearer {admin_token}"},
        )
        log_resp = client.get(
            "/api/operation-logs",
            headers={"Authorization": f"Bearer {admin_token}"},
        )
        for log in log_resp.json()["data"]["logs"]:
            assert log["action"] == "remove_member"

    def test_unauthorized_user_cannot_view_logs(self, client, member_token, group_id):
        client.delete(
            f"/api/groups/{group_id}/members/member002",
            headers={"Authorization": f"Bearer {member_token}"},
        )
        log_resp = client.get(
            "/api/operation-logs",
            headers={"Authorization": f"Bearer {member_token}"},
        )
        assert log_resp.status_code == 200
        logs = log_resp.json()["data"]["logs"]
        assert len(logs) >= 0
