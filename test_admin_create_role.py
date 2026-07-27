import pytest
import time
from unittest.mock import MagicMock, patch, PropertyMock
from datetime import datetime, timezone
from typing import Optional


class CustomRole:
    def __init__(self, name: str, description: str, permissions: list[str], created_by: str):
        self.id = None
        self.name = name
        self.description = description
        self.permissions = permissions
        self.created_by = created_by
        self.created_at = datetime.now(timezone.utc)
        self.is_active = True
        self.assigned_user_ids: list[str] = []


class CustomRoleRepository:
    def __init__(self):
        self._store: dict[str, CustomRole] = {}
        self._next_id = 1

    def save(self, role: CustomRole) -> CustomRole:
        role.id = f'role-{self._next_id}'
        self._next_id += 1
        self._store[role.id] = role
        return role

    def find_by_id(self, role_id: str) -> Optional[CustomRole]:
        return self._store.get(role_id)

    def assign_to_user(self, role_id: str, user_id: str) -> bool:
        role = self.find_by_id(role_id)
        if role is None:
            return False
        if user_id not in role.assigned_user_ids:
            role.assigned_user_ids.append(user_id)
        return True


class RoleService:
    def __init__(self, repo: CustomRoleRepository):
        self.repo = repo

    def create_custom_role(self, name: str, description: str, permissions: list[str], created_by: str) -> CustomRole:
        if not name or not name.strip():
            raise ValueError('角色名称不能为空')
        if not permissions:
            raise ValueError('必须至少指定一个权限')
        role = CustomRole(name=name, description=description, permissions=permissions, created_by=created_by)
        return self.repo.save(role)

    def assign_role(self, role_id: str, user_id: str) -> bool:
        return self.repo.assign_to_user(role_id, user_id)


class TestAdminCreateCustomRole:

    @pytest.fixture
    def repo(self):
        return CustomRoleRepository()

    @pytest.fixture
    def service(self, repo):
        return RoleService(repo)

    @pytest.fixture
    def valid_role_data(self):
        return {
            'name': '数据审计员',
            'description': '可查看所有数据但无法修改',
            'permissions': ['data:read', 'audit:log:read', 'report:generate'],
            'created_by': 'admin@example.com',
        }

    def test_should_return_role_with_generated_id_when_created_successfully(self, service, valid_role_data):
        role = service.create_custom_role(**valid_role_data)
        assert role is not None
        assert role.id is not None
        assert role.id.startswith('role-')

    def test_should_create_role_with_correct_attributes(self, service, valid_role_data):
        role = service.create_custom_role(**valid_role_data)
        assert role.name == '数据审计员'
        assert role.description == '可查看所有数据但无法修改'
        assert role.permissions == ['data:read', 'audit:log:read', 'report:generate']
        assert role.created_by == 'admin@example.com'
        assert role.is_active is True
        assert role.created_at is not None

    def test_should_respond_within_300ms(self, service, valid_role_data):
        start = time.perf_counter()
        for _ in range(100):
            service.create_custom_role(**valid_role_data)
        elapsed_ms = (time.perf_counter() - start) * 1000 / 100
        assert elapsed_ms <= 300, f'平均响应时间 {elapsed_ms:.2f}ms 超过 300ms 限制'

    def test_should_persist_role_in_repository(self, service, repo, valid_role_data):
        role = service.create_custom_role(**valid_role_data)
        persisted = repo.find_by_id(role.id)
        assert persisted is not None
        assert persisted.name == valid_role_data['name']
        assert persisted.permissions == valid_role_data['permissions']

    def test_should_assign_new_role_to_user(self, service, repo, valid_role_data):
        role = service.create_custom_role(**valid_role_data)
        user_id = 'user-42'
        result = service.assign_role(role.id, user_id)
        assert result is True
        persisted = repo.find_by_id(role.id)
        assert user_id in persisted.assigned_user_ids

    def test_should_reject_role_with_empty_name(self, service, valid_role_data):
        with pytest.raises(ValueError, match='角色名称不能为空'):
            service.create_custom_role(
                name='',
                description=valid_role_data['description'],
                permissions=valid_role_data['permissions'],
                created_by=valid_role_data['created_by'],
            )

    def test_should_reject_role_without_permissions(self, service, valid_role_data):
        with pytest.raises(ValueError, match='必须至少指定一个权限'):
            service.create_custom_role(
                name=valid_role_data['name'],
                description=valid_role_data['description'],
                permissions=[],
                created_by=valid_role_data['created_by'],
            )

    def test_should_allow_multiple_users_assigned_to_same_role(self, service, repo, valid_role_data):
        role = service.create_custom_role(**valid_role_data)
        user_ids = ['user-1', 'user-2', 'user-3']
        for uid in user_ids:
            assert service.assign_role(role.id, uid) is True
        persisted = repo.find_by_id(role.id)
        assert persisted.assigned_user_ids == user_ids

    def test_should_return_false_when_assigning_to_nonexistent_role(self, service):
        result = service.assign_role('role-nonexistent', 'user-99')
        assert result is False

    def test_should_reject_role_with_whitespace_only_name(self, service, valid_role_data):
        with pytest.raises(ValueError, match="角色名称不能为空"):
            service.create_custom_role(
                name="   ",
                description=valid_role_data["description"],
                permissions=valid_role_data["permissions"],
                created_by=valid_role_data["created_by"],
            )

    def test_should_accept_role_with_single_permission(self, service, valid_role_data):
        role = service.create_custom_role(
            name=valid_role_data["name"],
            description=valid_role_data["description"],
            permissions=["data:read"],
            created_by=valid_role_data["created_by"],
        )
        assert role is not None
        assert role.id is not None
        assert role.permissions == ["data:read"]

    def test_should_reject_role_with_none_name(self, service, valid_role_data):
        with pytest.raises(ValueError, match="角色名称不能为空"):
            service.create_custom_role(
                name=None,
                description=valid_role_data["description"],
                permissions=valid_role_data["permissions"],
                created_by=valid_role_data["created_by"],
            )

    def test_should_reject_role_with_none_permissions(self, service, valid_role_data):
        with pytest.raises(ValueError, match="必须至少指定一个权限"):
            service.create_custom_role(
                name=valid_role_data["name"],
                description=valid_role_data["description"],
                permissions=None,
                created_by=valid_role_data["created_by"],
            )

    def test_should_not_duplicate_user_assignment(self, service, repo, valid_role_data):
        role = service.create_custom_role(**valid_role_data)
        user_id = 'user-1'
        service.assign_role(role.id, user_id)
        service.assign_role(role.id, user_id)
        persisted = repo.find_by_id(role.id)
        assert persisted.assigned_user_ids.count(user_id) == 1
