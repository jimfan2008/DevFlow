#!/usr/bin/env python3
"""
DevFlow 项目管理平台 - 看板管理模块测试
"""

import pytest
from httpx import AsyncClient


class TestBoardCreation:
    """看板列创建测试"""
    
    @pytest.mark.asyncio
    async def test_create_column_success(self, client, test_user, db_session):
        """测试成功创建看板列"""
        # 先登录获取 token
        login_payload = {
            "username": "test_user",
            "password": "test123456"
        }
        login_response = await client.post("/api/auth/login", json=login_payload)
        token = login_response.json()["access_token"]
        
        # 创建看板列
        payload = {
            "project_id": "project_001",
            "name": "新列",
            "color": "#10b981",
            "position": 1
        }
        
        response = await client.post(
            "/api/boards",
            json=payload,
            headers={"Authorization": f"Bearer {token}"}
        )
        
        assert response.status_code == 200
        data = response.json()
        assert data["success"] is True
        assert "id" in data["board"]
        assert data["board"]["name"] == "新列"
        assert data["board"]["color"] == "#10b981"
        assert data["board"]["position"] == 1
    
    @pytest.mark.asyncio
    async def test_create_column_duplicate_name(self, client, test_user, test_board, db_session):
        """测试重复名称的看板列"""
        # 先登录获取 token
        login_payload = {
            "username": "test_user",
            "password": "test123456"
        }
        login_response = await client.post("/api/auth/login", json=login_payload)
        token = login_response.json()["access_token"]
        
        # 创建同名看板列
        payload = {
            "project_id": "project_001",
            "name": "测试看板",  # 与现有看板同名
            "color": "#10b981",
            "position": 1
        }
        
        response = await client.post(
            "/api/boards",
            json=payload,
            headers={"Authorization": f"Bearer {token}"}
        )
        
        assert response.status_code == 400
        data = response.json()
        assert data["success"] is False
        assert "name" in data["error"]
    
    @pytest.mark.asyncio
    async def test_create_column_missing_name(self, client, test_user, db_session):
        """测试创建看板列缺少名称"""
        # 先登录获取 token
        login_payload = {
            "username": "test_user",
            "password": "test123456"
        }
        login_response = await client.post("/api/auth/login", json=login_payload)
        token = login_response.json()["access_token"]
        
        # 创建无名称看板列
        payload = {
            "project_id": "project_001",
            "color": "#10b981",
            "position": 1
        }
        
        response = await client.post(
            "/api/boards",
            json=payload,
            headers={"Authorization": f"Bearer {token}"}
        )
        
        assert response.status_code == 422  # Validation Error
    
    @pytest.mark.asyncio
    async def test_create_column_invalid_color(self, client, test_user, db_session):
        """测试创建看板列无效的颜色代码"""
        # 先登录获取 token
        login_payload = {
            "username": "test_user",
            "password": "test123456"
        }
        login_response = await client.post("/api/auth/login", json=login_payload)
        token = login_response.json()["access_token"]
        
        # 创建无效颜色看板列
        payload = {
            "project_id": "project_001",
            "name": "新列",
            "color": "not-a-color",  # 无效颜色
            "position": 1
        }
        
        response = await client.post(
            "/api/boards",
            json=payload,
            headers={"Authorization": f"Bearer {token}"}
        )
        
        assert response.status_code == 422


class TestBoardUpdate:
    """看板列更新测试"""
    
    @pytest.mark.asyncio
    async def test_update_column_success(self, client, test_user, test_board, db_session):
        """测试成功更新看板列"""
        # 先登录获取 token
        login_payload = {
            "username": "test_user",
            "password": "test123456"
        }
        login_response = await client.post("/api/auth/login", json=login_payload)
        token = login_response.json()["access_token"]
        
        # 更新看板列
        payload = {
            "name": "更新后的列名",
            "color": "#ef4444"
        }
        
        response = await client.put(
            f"/api/boards/{test_board.id}",
            json=payload,
            headers={"Authorization": f"Bearer {token}"}
        )
        
        assert response.status_code == 200
        data = response.json()
        assert data["success"] is True
        assert data["board"]["name"] == "更新后的列名"
        assert data["board"]["color"] == "#ef4444"
    
    @pytest.mark.asyncio
    async def test_update_column_not_found(self, client, test_user, db_session):
        """测试更新不存在的看板列"""
        # 先登录获取 token
        login_payload = {
            "username": "test_user",
            "password": "test123456"
        }
        login_response = await client.post("/api/auth/login", json=login_payload)
        token = login_response.json()["access_token"]
        
        # 更新不存在的看板列
        payload = {
            "name": "新名称"
        }
        
        response = await client.put(
            "/api/boards/nonexistent_id",
            json=payload,
            headers={"Authorization": f"Bearer {token}"}
        )
        
        assert response.status_code == 404
        data = response.json()
        assert data["success"] is False
        assert "not found" in data["error"].lower()


class TestBoardDelete:
    """看板列删除测试"""
    
    @pytest.mark.asyncio
    async def test_delete_column_success(self, client, test_user, test_board, db_session):
        """测试成功删除看板列"""
        # 先登录获取 token
        login_payload = {
            "username": "test_user",
            "password": "test123456"
        }
        login_response = await client.post("/api/auth/login", json=login_payload)
        token = login_response.json()["access_token"]
        
        response = await client.delete(
            f"/api/boards/{test_board.id}",
            headers={"Authorization": f"Bearer {token}"}
        )
        
        assert response.status_code == 200
        data = response.json()
        assert data["success"] is True
    
    @pytest.mark.asyncio
    async def test_delete_column_not_found(self, client, test_user, db_session):
        """测试删除不存在的看板列"""
        # 先登录获取 token
        login_payload = {
            "username": "test_user",
            "password": "test123456"
        }
        login_response = await client.post("/api/auth/login", json=login_payload)
        token = login_response.json()["access_token"]
        
        response = await client.delete(
            "/api/boards/nonexistent_id",
            headers={"Authorization": f"Bearer {token}"}
        )
        
        assert response.status_code == 404


class TestBoardList:
    """看板列表查询测试"""
    
    @pytest.mark.asyncio
    async def test_list_boards_success(self, client, test_user, test_board, db_session):
        """测试获取看板列表"""
        # 先登录获取 token
        login_payload = {
            "username": "test_user",
            "password": "test123456"
        }
        login_response = await client.post("/api/auth/login", json=login_payload)
        token = login_response.json()["access_token"]
        
        response = await client.get(
            "/api/projects/project_001/boards",
            headers={"Authorization": f"Bearer {token}"}
        )
        
        assert response.status_code == 200
        data = response.json()
        assert data["success"] is True
        assert "boards" in data
        assert len(data["boards"]) >= 1
        assert any(b["id"] == test_board.id for b in data["boards"])
    
    @pytest.mark.asyncio
    async def test_list_boards_empty(self, client, test_user, db_session):
        """测试空看板列表"""
        # 先登录获取 token
        login_payload = {
            "username": "test_user",
            "password": "test123456"
        }
        login_response = await client.post("/api/auth/login", json=login_payload)
        token = login_response.json()["access_token"]
        
        response = await client.get(
            "/api/projects/nonexistent_project/boards",
            headers={"Authorization": f"Bearer {token}"}
        )
        
        assert response.status_code == 200
        data = response.json()
        assert data["success"] is True
        assert "boards" in data
        assert len(data["boards"]) == 0


class TestBoardDefaultColumns:
    """默认看板列测试"""
    
    @pytest.mark.asyncio
    async def test_default_columns_exist(self, client, test_user, test_board, db_session):
        """测试默认列存在"""
        # 先登录获取 token
        login_payload = {
            "username": "test_user",
            "password": "test123456"
        }
        login_response = await client.post("/api/auth/login", json=login_payload)
        token = login_response.json()["access_token"]
        
        response = await client.get(
            f"/api/boards/{test_board.id}",
            headers={"Authorization": f"Bearer {token}"}
        )
        
        assert response.status_code == 200
        data = response.json()
        
        # 检查默认列：To Do, In Progress, Review, Done
        column_names = [col["name"] for col in data["board"]["columns"]]
        default_columns = ["To Do", "In Progress", "Review", "Done"]
        
        for col in default_columns:
            assert col in column_names


class TestBoardPositionUpdate:
    """看板列位置更新测试"""
    
    @pytest.mark.asyncio
    async def test_update_column_position_success(self, client, test_user, test_board, db_session):
        """测试成功更新看板列位置"""
        # 先登录获取 token
        login_payload = {
            "username": "test_user",
            "password": "test123456"
        }
        login_response = await client.post("/api/auth/login", json=login_payload)
        token = login_response.json()["access_token"]
        
        # 创建额外的列用于位置测试
        payload = {
            "project_id": "project_001",
            "name": "新列",
            "color": "#10b981",
            "position": 5
        }
        
        await client.post(
            "/api/boards",
            json=payload,
            headers={"Authorization": f"Bearer {token}"}
        )
        
        # 更新位置
        payload = {"position": 2}
        
        response = await client.put(
            f"/api/boards/{test_board.id}",
            json=payload,
            headers={"Authorization": f"Bearer {token}"}
        )
        
        assert response.status_code == 200
        data = response.json()
        assert data["board"]["position"] == 2
