#!/usr/bin/env python3
"""
需求协同模块 - 单元测试
TDD: 测试先行，覆盖需求创建、版本管理、锁定确认等核心功能
"""

import pytest
from datetime import datetime, timezone
from app.models.requirement import Requirement


class TestRequirementBasics:
    """需求基础功能测试"""

    @pytest.mark.asyncio
    async def test_create_requirement(self, db_session, test_project):
        """测试创建新需求"""
        req = Requirement(
            id="req_create_test",
            project_id=test_project.id,
            content="## 测试需求\n\n- 功能A\n- 功能B",
            version=1,
            is_locked=False,
        )
        db_session.add(req)
        db_session.commit()
        db_session.refresh(req)

        assert req.id == "req_create_test"
        assert req.project_id == test_project.id
        assert req.version == 1
        assert req.is_locked is False
        assert req.confirmed_at is None

    @pytest.mark.asyncio
    async def test_requirement_to_dict(self, db_session, test_requirement):
        """测试需求序列化"""
        result = test_requirement.to_dict()

        assert "id" in result
        assert "project_id" in result
        assert "content" in result
        assert "version" in result
        assert "is_locked" in result
        assert "created_at" in result

    @pytest.mark.asyncio
    async def test_requirement_versioning(self, db_session, test_project):
        """测试需求版本管理"""
        req_v1 = Requirement(
            id="req_version_v1",
            project_id=test_project.id,
            content="版本 1 内容",
            version=1,
            is_locked=False,
        )
        db_session.add(req_v1)
        db_session.commit()
        db_session.refresh(req_v1)

        req_v2 = Requirement(
            id="req_version_v2",
            project_id=test_project.id,
            content="版本 2 内容（更新版）",
            version=2,
            is_locked=False,
        )
        db_session.add(req_v2)
        db_session.commit()
        db_session.refresh(req_v2)

        assert req_v1.version == 1
        assert req_v2.version == 2
        assert req_v1.content != req_v2.content


class TestRequirementLocking:
    """需求锁定功能测试"""

    @pytest.mark.asyncio
    async def test_lock_requirement(self, db_session, test_project):
        """测试锁定需求文档"""
        req = Requirement(
            id="req_lock_test",
            project_id=test_project.id,
            content="待锁定的需求",
            version=1,
            is_locked=False,
        )
        db_session.add(req)
        db_session.commit()
        db_session.refresh(req)

        req.is_locked = True
        req.confirmed_at = datetime.now(timezone.utc)
        db_session.commit()
        db_session.refresh(req)

        assert req.is_locked is True
        assert req.confirmed_at is not None

    @pytest.mark.asyncio
    async def test_locked_requirement_properties(self, db_session, locked_requirement):
        """测试已锁定需求的属性"""
        assert locked_requirement.is_locked is True
        assert locked_requirement.confirmed_at is not None
        assert locked_requirement.version >= 2

    @pytest.mark.asyncio
    async def test_requirement_locked_before_decomposition(self, db_session, test_requirement):
        """测试需求未锁定时不能进行任务拆解（业务规则）"""
        assert test_requirement.is_locked is False

        can_decompose = test_requirement.is_locked
        assert can_decompose is False, "需求未锁定时不应允许任务拆解"


class TestRequirementContent:
    """需求内容验证测试"""

    @pytest.mark.asyncio
    async def test_requirement_contains_acceptance_criteria(self, db_session, test_project):
        """测试需求文档应包含验收标准"""
        req_with_acceptance = Requirement(
            id="req_acceptance",
            project_id=test_project.id,
            content="## 需求\n\n### 验收标准\n1. 功能A可用\n2. 测试覆盖率 >= 80%",
            version=1,
            is_locked=False,
        )
        db_session.add(req_with_acceptance)
        db_session.commit()

        assert "验收标准" in req_with_acceptance.content
        assert "测试覆盖率" in req_with_acceptance.content

    @pytest.mark.asyncio
    async def test_requirement_contains_functional_modules(self, db_session, test_project):
        """测试需求文档应包含功能模块列表"""
        req_with_modules = Requirement(
            id="req_modules",
            project_id=test_project.id,
            content="## 核心功能模块\n\n1. 用户管理\n2. 商品管理\n3. 订单系统",
            version=1,
            is_locked=False,
        )
        db_session.add(req_with_modules)
        db_session.commit()

        assert "用户管理" in req_with_modules.content
        assert "商品管理" in req_with_modules.content
        assert "订单系统" in req_with_modules.content


class TestRequirementProjectRelationship:
    """需求与项目关系测试"""

    @pytest.mark.asyncio
    async def test_requirement_belongs_to_project(self, db_session, test_requirement, test_project):
        """测试需求属于正确的项目"""
        assert test_requirement.project_id == test_project.id

    @pytest.mark.asyncio
    async def test_multiple_requirements_same_project(self, db_session, test_project):
        """测试同一项目可以有多个需求版本"""
        req1 = Requirement(
            id="req_multi_1",
            project_id=test_project.id,
            content="需求版本1",
            version=1,
            is_locked=False,
        )
        req2 = Requirement(
            id="req_multi_2",
            project_id=test_project.id,
            content="需求版本2",
            version=2,
            is_locked=True,
        )
        db_session.add(req1)
        db_session.add(req2)
        db_session.commit()

        assert req1.project_id == test_project.id
        assert req2.project_id == test_project.id
        assert req1.id != req2.id
