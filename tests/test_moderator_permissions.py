import pytest
import time
from unittest.mock import MagicMock, patch
from dataclasses import dataclass
from enum import Enum
from typing import Optional


class GroupRole(Enum):
    OWNER = "owner"
    ADMIN = "admin"
    MODERATOR = "moderator"
    MEMBER = "member"


class Permission(Enum):
    MUTE = "mute"
    ANNOUNCE = "announce"
    MEETING_MANAGE = "meeting_manage"
    REMOVE_MEMBER = "remove_member"
    DISBAND_GROUP = "disband_group"


class HTTPError(Exception):
    def __init__(self, status_code: int, message: str = ""):
        self.status_code = status_code
        self.message = message
        super().__init__(f"HTTP {status_code}: {message}")


class PermissionDenied(HTTPError):
    def __init__(self, message: str = "权限不足"):
        super().__init__(403, message)


@dataclass
class GroupMember:
    user_id: str
    role: GroupRole


@dataclass
class Group:
    group_id: str
    owner_id: str
    members: list


class GroupService:
    def __init__(self):
        self._groups: dict[str, Group] = {}
        self._permission_map: dict[GroupRole, set[Permission]] = {
            GroupRole.OWNER: {
                Permission.MUTE, Permission.ANNOUNCE,
                Permission.MEETING_MANAGE, Permission.REMOVE_MEMBER,
                Permission.DISBAND_GROUP,
            },
            GroupRole.ADMIN: {
                Permission.MUTE, Permission.ANNOUNCE,
                Permission.MEETING_MANAGE, Permission.REMOVE_MEMBER,
                Permission.DISBAND_GROUP,
            },
            GroupRole.MODERATOR: {
                Permission.MUTE, Permission.ANNOUNCE,
                Permission.MEETING_MANAGE,
            },
            GroupRole.MEMBER: set(),
        }

    def create_group(self, group_id: str, owner_id: str) -> Group:
        group = Group(
            group_id=group_id,
            owner_id=owner_id,
            members=[GroupMember(user_id=owner_id, role=GroupRole.OWNER)],
        )
        self._groups[group_id] = group
        return group

    def add_member(self, group_id: str, user_id: str, role: GroupRole) -> None:
        group = self._get_group(group_id)
        group.members.append(GroupMember(user_id=user_id, role=role))

    def _get_group(self, group_id: str) -> Group:
        group = self._groups.get(group_id)
        if group is None:
            raise HTTPError(404, "群组不存在")
        return group

    def _get_member(self, group: Group, user_id: str) -> Optional[GroupMember]:
        for m in group.members:
            if m.user_id == user_id:
                return m
        return None

    def _check_permission(self, group: Group, user_id: str, permission: Permission) -> None:
        member = self._get_member(group, user_id)
        if member is None:
            raise HTTPError(404, "成员不存在于该群组")
        if permission not in self._permission_map.get(member.role, set()):
            raise PermissionDenied(f"{member.role.value} 无权执行 {permission.value}")

    def mute_member(self, group_id: str, operator_id: str, target_id: str) -> dict:
        group = self._get_group(group_id)
        self._check_permission(group, operator_id, Permission.MUTE)
        target = self._get_member(group, target_id)
        if target is None:
            raise HTTPError(404, "目标成员不存在")
        if target.role == GroupRole.OWNER:
            raise PermissionDenied("无法禁言群主")
        if target.role == GroupRole.ADMIN:
            raise PermissionDenied("无法禁言管理员")
        if target.role == GroupRole.MODERATOR and operator_id != target_id:
            raise PermissionDenied("无法禁言其他主持人")
        return {"status": "ok", "action": "mute", "target": target_id}

    def announce(self, group_id: str, operator_id: str, content: str) -> dict:
        group = self._get_group(group_id)
        self._check_permission(group, operator_id, Permission.ANNOUNCE)
        return {"status": "ok", "action": "announce", "content": content}

    def manage_meeting(self, group_id: str, operator_id: str, action: str) -> dict:
        group = self._get_group(group_id)
        self._check_permission(group, operator_id, Permission.MEETING_MANAGE)
        return {"status": "ok", "action": f"meeting_{action}"}

    def remove_member(self, group_id: str, operator_id: str, target_id: str) -> dict:
        group = self._get_group(group_id)
        self._check_permission(group, operator_id, Permission.REMOVE_MEMBER)
        return {"status": "ok", "action": "remove", "target": target_id}

    def disband_group(self, group_id: str, operator_id: str) -> dict:
        group = self._get_group(group_id)
        self._check_permission(group, operator_id, Permission.DISBAND_GROUP)
        del self._groups[group_id]
        return {"status": "ok", "action": "disband"}


class TestModeratorPermissions:
    @pytest.fixture
    def service(self):
        svc = GroupService()
        svc.create_group("g001", "owner1")
        svc.add_member("g001", "mod1", GroupRole.MODERATOR)
        svc.add_member("g001", "mod2", GroupRole.MODERATOR)
        svc.add_member("g001", "member1", GroupRole.MEMBER)
        return svc

    def test_moderator_mute_returns_ok(self, service):
        result = service.mute_member("g001", "mod1", "member1")
        assert result["status"] == "ok"
        assert result["action"] == "mute"

    def test_moderator_mute_response_within_2s(self, service):
        start = time.time()
        service.mute_member("g001", "mod1", "member1")
        elapsed = time.time() - start
        assert elapsed <= 2.0

    def test_moderator_announce_returns_ok(self, service):
        result = service.announce("g001", "mod1", "公告内容")
        assert result["status"] == "ok"
        assert result["action"] == "announce"

    def test_moderator_meeting_manage_returns_ok(self, service):
        result = service.manage_meeting("g001", "mod1", "start")
        assert result["status"] == "ok"
        assert result["action"] == "meeting_start"

    def test_moderator_remove_member_returns_403(self, service):
        with pytest.raises(PermissionDenied) as exc:
            service.remove_member("g001", "mod1", "member1")
        assert exc.value.status_code == 403

    def test_moderator_disband_group_returns_403(self, service):
        with pytest.raises(PermissionDenied) as exc:
            service.disband_group("g001", "mod1")
        assert exc.value.status_code == 403

    def test_moderator_cannot_mute_another_moderator(self, service):
        with pytest.raises(PermissionDenied) as exc:
            service.mute_member("g001", "mod1", "mod2")
        assert exc.value.status_code == 403

    def test_moderator_cannot_mute_admin(self, service):
        svc = GroupService()
        svc.create_group("g002", "owner1")
        svc.add_member("g002", "admin1", GroupRole.ADMIN)
        svc.add_member("g002", "mod1", GroupRole.MODERATOR)
        with pytest.raises(PermissionDenied) as exc:
            svc.mute_member("g002", "mod1", "admin1")
        assert exc.value.status_code == 403

    def test_moderator_cannot_mute_owner(self, service):
        with pytest.raises(PermissionDenied) as exc:
            service.mute_member("g001", "mod1", "owner1")
        assert exc.value.status_code == 403

    def test_moderator_can_mute_self(self, service):
        result = service.mute_member("g001", "mod1", "mod1")
        assert result["status"] == "ok"

    def test_non_moderator_cannot_mute(self, service):
        with pytest.raises(PermissionDenied) as exc:
            service.mute_member("g001", "member1", "mod1")
        assert exc.value.status_code == 403

    def test_moderator_permission_map_has_correct_permissions(self):
        expected = {Permission.MUTE, Permission.ANNOUNCE, Permission.MEETING_MANAGE}
        svc = GroupService()
        assert svc._permission_map[GroupRole.MODERATOR] == expected

    def test_moderator_permission_map_lacks_remove_and_disband(self):
        svc = GroupService()
        assert Permission.REMOVE_MEMBER not in svc._permission_map[GroupRole.MODERATOR]
        assert Permission.DISBAND_GROUP not in svc._permission_map[GroupRole.MODERATOR]
