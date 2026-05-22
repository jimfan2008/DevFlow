#!/usr/bin/env python3
"""DevFlow 负载分析模块测试"""
import pytest


class TestWorkloadHeatmap:
    @pytest.mark.asyncio
    async def test_get_workload_heatmap_success(self, client, test_user, test_project, db_session):
        from app.utils.security import create_access_token
        token = create_access_token(user_id=test_user.id)
        response = await client.get(
            f"/api/workload/{test_project.id}/workload",
            headers={"Authorization": f"Bearer {token}"}
        )
        assert response.status_code == 200

    @pytest.mark.asyncio
    async def test_workload_idle_status(self, client, test_user, test_project, db_session):
        from app.utils.security import create_access_token
        token = create_access_token(user_id=test_user.id)
        response = await client.get(
            f"/api/workload/{test_project.id}/workload",
            headers={"Authorization": f"Bearer {token}"}
        )
        assert response.status_code == 200


class TestWorkloadTrend:
    @pytest.mark.asyncio
    async def test_get_workload_trend(self, client, test_user, test_project, db_session):
        from app.utils.security import create_access_token
        token = create_access_token(user_id=test_user.id)
        response = await client.get(
            f"/api/workload/{test_project.id}/workload/trend",
            headers={"Authorization": f"Bearer {token}"}
        )
        assert response.status_code == 200
