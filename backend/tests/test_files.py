#!/usr/bin/env python3
"""DevFlow 文件 API 模块测试"""
import pytest


class TestFileUpload:
    @pytest.mark.asyncio
    async def test_upload_file_unauthorized(self, client):
        response = await client.post("/api/files/task_001/upload")
        assert response.status_code in (401, 403, 405, 422)


class TestFileDownload:
    @pytest.mark.asyncio
    async def test_serve_nonexistent_file(self, client):
        response = await client.get("/api/files/nonexistent/nofile.txt")
        assert response.status_code == 404


class TestFileDelete:
    @pytest.mark.asyncio
    async def test_delete_file_unauthorized(self, client):
        response = await client.delete("/api/files/task_001/nofile.txt")
        assert response.status_code in (401, 403)
