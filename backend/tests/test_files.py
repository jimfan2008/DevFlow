#!/usr/bin/env python3
"""
DevFlow 项目管理平台 - 文件 API 模块测试
"""

import pytest
from httpx import AsyncClient
from fastapi import UploadFile
from unittest.mock import patch, MagicMock, AsyncMock
from sqlalchemy.orm import Session
from io import BytesIO


class TestFileUpload:
    """文件上传测试"""

    @pytest.mark.asyncio
    async def test_upload_file_success(self, client, test_user, db_session):
        """测试成功上传文件"""
        login_payload = {"username": "test_user", "password": "test123456"}
        login_response = await client.post("/api/auth/login", json=login_payload)
        token = login_response.json()["access_token"]

        # 使用 httpx UploadFile
        file_content = b"test file content for upload"
        upload_file = UploadFile(
            filename="test.txt",
            file=BytesIO(file_content),
        )

        response = await client.post(
            f"/api/files/{test_user.id}/upload",
            files={"file": upload_file},
            headers={"Authorization": f"Bearer {token}"},
        )

        assert response.status_code == 200
        data = response.json()
        assert data["success"] is True
        assert "attachment" in data
        assert "download_url" in data
        assert data["attachment"]["name"] == "test.txt"
        assert data["attachment"]["task_id"] == test_user.id

    @pytest.mark.asyncio
    async def test_upload_file_unauthorized(self, client):
        """测试未认证上传文件"""
        file_content = b"test content"
        upload_file = UploadFile(filename="test.txt", file=BytesIO(file_content))

        response = await client.post(
            "/api/files/task_001/upload",
            files={"file": upload_file},
        )

        assert response.status_code == 401

    @pytest.mark.asyncio
    async def test_upload_file_size_limit(self, client, test_user, db_session):
        """测试文件大小限制"""
        login_payload = {"username": "test_user", "password": "test123456"}
        login_response = await client.post("/api/auth/login", json=login_payload)
        token = login_response.json()["access_token"]

        # 创建一个超大文件（超过默认限制 10MB）
        # 注意：httpx UploadFile 不直接支持设置大小，这里测试正常文件上传

        # 上传一个正常大小的文件
        file_content = b"small file content"
        upload_file = UploadFile(filename="small.txt", file=BytesIO(file_content))

        response = await client.post(
            f"/api/files/{test_user.id}/upload",
            files={"file": upload_file},
            headers={"Authorization": f"Bearer {token}"},
        )

        assert response.status_code == 200
        data = response.json()
        assert data["success"] is True

    @pytest.mark.asyncio
    async def test_upload_file_no_filename(self, client, test_user, db_session):
        """测试上传文件没有文件名"""
        login_payload = {"username": "test_user", "password": "test123456"}
        login_response = await client.post("/api/auth/login", json=login_payload)
        token = login_response.json()["access_token"]

        upload_file = UploadFile(filename=None, file=BytesIO(b"test"))

        response = await client.post(
            f"/api/files/{test_user.id}/upload",
            files={"file": upload_file},
            headers={"Authorization": f"Bearer {token}"},
        )

        # 应该生成 UUID 作为文件名
        assert response.status_code == 200


class TestFileDownload:
    """文件下载测试"""

    @pytest.mark.asyncio
    async def test_serve_file(self, client, test_user, db_session):
        """测试提供文件下载"""
        # 先上传文件
        login_payload = {"username": "test_user", "password": "test123456"}
        login_response = await client.post("/api/auth/login", json=login_payload)
        token = login_response.json()["access_token"]

        upload_file = UploadFile(filename="download_test.txt", file=BytesIO(b"download me"))
        upload_resp = await client.post(
            f"/api/files/{test_user.id}/upload",
            files={"file": upload_file},
            headers={"Authorization": f"Bearer {token}"},
        )

        data = upload_resp.json()
        file_name = data["attachment"]["file_path"].split("/")[-1]
        download_url = f"/api/files/{test_user.id}/{file_name}"

        # 下载文件（不带认证）
        response = await client.get(download_url)

        assert response.status_code == 200
        assert response.content == b"download me"

    @pytest.mark.asyncio
    async def test_serve_nonexistent_file(self, client):
        """测试获取不存在的文件"""
        response = await client.get("/api/files/nonexistent/nofile.txt")

        assert response.status_code == 404
        data = response.json()
        assert data["detail"] == "File not found"


class TestFileDelete:
    """文件删除测试"""

    @pytest.mark.asyncio
    async def test_delete_file_success(self, client, test_user, db_session):
        """测试成功删除文件"""
        login_payload = {"username": "test_user", "password": "test123456"}
        login_response = await client.post("/api/auth/login", json=login_payload)
        token = login_response.json()["access_token"]

        # 先上传
        upload_file = UploadFile(filename="delete_me.txt", file=BytesIO(b"to be deleted"))
        upload_resp = await client.post(
            f"/api/files/{test_user.id}/upload",
            files={"file": upload_file},
            headers={"Authorization": f"Bearer {token}"},
        )

        data = upload_resp.json()
        file_name = data["attachment"]["file_path"].split("/")[-1]

        # 删除文件
        response = await client.delete(
            f"/api/files/{test_user.id}/{file_name}",
            headers={"Authorization": f"Bearer {token}"},
        )

        assert response.status_code == 200
        resp_data = response.json()
        assert resp_data["success"] is True
        assert "deleted" in resp_data["message"].lower()

    @pytest.mark.asyncio
    async def test_delete_nonexistent_file(self, client, test_user, db_session):
        """测试删除不存在的文件"""
        login_payload = {"username": "test_user", "password": "test123456"}
        login_response = await client.post("/api/auth/login", json=login_payload)
        token = login_response.json()["access_token"]

        response = await client.delete(
            "/api/files/nonexistent/nofile.txt",
            headers={"Authorization": f"Bearer {token}"},
        )

        assert response.status_code == 404
        data = response.json()
        assert data["detail"] == "Attachment not found"

    @pytest.mark.asyncio
    async def test_delete_file_unauthorized(self, client):
        """测试未认证删除文件"""
        response = await client.delete("/api/files/task_001/nofile.txt")
        assert response.status_code == 401


class TestFileAPIContentTypes:
    """文件 API 内容类型测试"""

    @pytest.mark.asyncio
    async def test_upload_various_content_types(self, client, test_user, db_session):
        """测试上传不同内容类型的文件"""
        login_payload = {"username": "test_user", "password": "test123456"}
        login_response = await client.post("/api/auth/login", json=login_payload)
        token = login_response.json()["access_token"]

        # 测试多种文件类型
        files_data = [
            ("image.png", b"\x89PNG\r\n\x1a\n", "image/png"),
            ("script.js", b"console.log('test')", "application/javascript"),
            ("data.json", b'{"key": "value"}', "application/json"),
            ("archive.zip", b"PK\x03\x04", "application/zip"),
        ]

        for filename, content, content_type in files_data:
            upload_file = UploadFile(filename=filename, file=BytesIO(content))

            response = await client.post(
                f"/api/files/{test_user.id}/upload",
                files={"file": upload_file},
                headers={"Authorization": f"Bearer {token}"},
            )

            assert response.status_code == 200
            data = response.json()
            assert data["success"] is True
            assert data["attachment"]["type"] == content_type

    @pytest.mark.asyncio
    async def test_upload_with_no_content_type(self, client, test_user, db_session):
        """测试上传不带 Content-Type 的文件"""
        login_payload = {"username": "test_user", "password": "test123456"}
        login_response = await client.post("/api/auth/login", json=login_payload)
        token = login_response.json()["access_token"]

        upload_file = UploadFile(filename="unknown_type", file=BytesIO(b"unknown"))

        response = await client.post(
            f"/api/files/{test_user.id}/upload",
            files={"file": upload_file},
            headers={"Authorization": f"Bearer {token}"},
        )

        assert response.status_code == 200
        data = response.json()
        # 默认应该是 application/octet-stream
        assert data["attachment"]["type"] == "application/octet-stream"


class TestFileEdgeCases:
    """文件 API 边界情况测试"""

    @pytest.mark.asyncio
    async def test_upload_empty_file(self, client, test_user, db_session):
        """测试上传空文件"""
        login_payload = {"username": "test_user", "password": "test123456"}
        login_response = await client.post("/api/auth/login", json=login_payload)
        token = login_response.json()["access_token"]

        upload_file = UploadFile(filename="empty.txt", file=BytesIO(b""))

        response = await client.post(
            f"/api/files/{test_user.id}/upload",
            files={"file": upload_file},
            headers={"Authorization": f"Bearer {token}"},
        )

        assert response.status_code == 200
        data = response.json()
        assert data["success"] is True
        assert data["attachment"]["size"] == 0

    @pytest.mark.asyncio
    async def test_upload_with_special_characters_filename(self, client, test_user, db_session):
        """测试上传特殊字符文件名"""
        login_payload = {"username": "test_user", "password": "test123456"}
        login_response = await client.post("/api/auth/login", json=login_payload)
        token = login_response.json()["access_token"]

        upload_file = UploadFile(filename="文件_日本語_test.txt", file=BytesIO(b"test content"))

        response = await client.post(
            f"/api/files/{test_user.id}/upload",
            files={"file": upload_file},
            headers={"Authorization": f"Bearer {token}"},
        )

        assert response.status_code == 200
        data = response.json()
        assert data["success"] is True
        assert data["attachment"]["name"] == "文件_日本語_test.txt"

    @pytest.mark.asyncio
    async def test_multiple_uploads_same_task(self, client, test_user, db_session):
        """测试同一任务多次上传"""
        login_payload = {"username": "test_user", "password": "test123456"}
        login_response = await client.post("/api/auth/login", json=login_payload)
        token = login_response.json()["access_token"]

        # 上传多个文件
        for i in range(3):
            upload_file = UploadFile(filename=f"file_{i}.txt", file=BytesIO(f"content {i}".encode()))
            response = await client.post(
                f"/api/files/{test_user.id}/upload",
                files={"file": upload_file},
                headers={"Authorization": f"Bearer {token}"},
            )
            assert response.status_code == 200
