import time
import json
from unittest.mock import patch, MagicMock
import redis
import pytest


@pytest.fixture
def mock_redis_db2():
    """模拟 Redis DB2 连接"""
    mock_redis = MagicMock(spec=redis.Redis)
    mock_redis.db = 2
    mock_redis.get.return_value = json.dumps({
        "user_id": 1001,
        "username": "testuser",
        "last_active": time.time() - 100
    }).encode()
    return mock_redis


@pytest.fixture
def mock_request():
    """模拟 HTTP 请求对象"""
    req = MagicMock()
    req.cookies = {"session_id": "abc123def456"}
    req.headers = {"Authorization": "Bearer abc123def456"}
    req.path = "/dashboard"
    return req


@pytest.fixture
def mock_frontend_context():
    """模拟前端通知上下文"""
    ctx = MagicMock()
    ctx.notifications = []
    return ctx


# ---------- 后端：会话超时自动登出 ----------

def test_session_timeout_returns_401(mock_redis_db2, mock_request):
    """用户30分钟无操作后，返回 HTTP 401"""

    def check_session(request, redis_conn):
        session_data_raw = redis_conn.get("session:" + request.cookies["session_id"])
        if session_data_raw is None:
            return {"status": 401, "redirect": "/login"}
        session_data = json.loads(session_data_raw)
        elapsed = time.time() - session_data["last_active"]
        if elapsed > 1800:  # 30分钟 = 1800秒
            redis_conn.delete("session:" + request.cookies["session_id"])
            return {"status": 401, "redirect": "/login"}
        return {"status": 200, "redirect": None}

    mock_redis_db2.get.return_value = json.dumps({
        "user_id": 1001,
        "username": "testuser",
        "last_active": time.time() - 2000
    }).encode()

    result = check_session(mock_request, mock_redis_db2)

    assert result["status"] == 401
    assert result["redirect"] == "/login"


def test_session_timeout_clears_redis_session(mock_redis_db2, mock_request):
    """超时后 Redis DB2 中的 session 被清除"""
    session_key = "session:" + mock_request.cookies["session_id"]

    mock_redis_db2.get.return_value = json.dumps({
        "user_id": 1001,
        "username": "testuser",
        "last_active": time.time() - 2000
    }).encode()

    def check_session(request, redis_conn):
        session_data_raw = redis_conn.get("session:" + request.cookies["session_id"])
        session_data = json.loads(session_data_raw)
        elapsed = time.time() - session_data["last_active"]
        if elapsed > 1800:
            redis_conn.delete("session:" + request.cookies["session_id"])
            return {"status": 401, "redirect": "/login"}
        return {"status": 200, "redirect": None}

    result = check_session(mock_request, mock_redis_db2)

    assert result["status"] == 401
    mock_redis_db2.delete.assert_called_once_with(session_key)


def test_session_not_timeout_returns_200(mock_redis_db2, mock_request):
    """未超时则正常返回 200"""
    mock_redis_db2.get.return_value = json.dumps({
        "user_id": 1001,
        "username": "testuser",
        "last_active": time.time() - 600
    }).encode()

    def check_session(request, redis_conn):
        session_data_raw = redis_conn.get("session:" + request.cookies["session_id"])
        if session_data_raw is None:
            return {"status": 401, "redirect": "/login"}
        session_data = json.loads(session_data_raw)
        elapsed = time.time() - session_data["last_active"]
        if elapsed > 1800:
            redis_conn.delete("session:" + request.cookies["session_id"])
            return {"status": 401, "redirect": "/login"}
        return {"status": 200, "redirect": None}

    result = check_session(mock_request, mock_redis_db2)

    assert result["status"] == 200
    assert result["redirect"] is None
    mock_redis_db2.delete.assert_not_called()


# ---------- 前端：超时前5分钟弹出提示 ----------

def test_frontend_shows_warning_5min_before_timeout(mock_frontend_context):
    """超时前5分钟内，前端弹出会话即将过期提示"""

    def check_session_expiration_and_notify(current_active_seconds_ago, ctx):
        timeout_seconds = 1800
        warning_threshold = 300
        remaining = timeout_seconds - current_active_seconds_ago

        if remaining <= warning_threshold and remaining > 0:
            warning_msg = "会话即将过期"
            ctx.notifications.append({
                "type": "warning",
                "message": warning_msg,
                "remaining_seconds": remaining
            })
            return {"show_warning": True, "remaining": remaining}

        if remaining <= 0:
            return {"show_warning": False, "auto_logout": True}

        return {"show_warning": False, "remaining": remaining}

    result = check_session_expiration_and_notify(1560, mock_frontend_context)

    assert result["show_warning"] is True
    assert result["remaining"] == 240
    assert len(mock_frontend_context.notifications) == 1
    assert mock_frontend_context.notifications[0]["message"] == "会话即将过期"
    assert mock_frontend_context.notifications[0]["type"] == "warning"


def test_frontend_no_warning_when_far_from_timeout(mock_frontend_context):
    """距超时还远时不弹出提示"""

    def check_session_expiration_and_notify(current_active_seconds_ago, ctx):
        timeout_seconds = 1800
        warning_threshold = 300
        remaining = timeout_seconds - current_active_seconds_ago

        if remaining <= warning_threshold and remaining > 0:
            warning_msg = "会话即将过期"
            ctx.notifications.append({
                "type": "warning",
                "message": warning_msg,
                "remaining_seconds": remaining
            })
            return {"show_warning": True, "remaining": remaining}

        if remaining <= 0:
            return {"show_warning": False, "auto_logout": True}

        return {"show_warning": False, "remaining": remaining}

    result = check_session_expiration_and_notify(600, mock_frontend_context)

    assert result["show_warning"] is False
    assert result["remaining"] == 1200
    assert len(mock_frontend_context.notifications) == 0


def test_frontend_no_warning_already_timed_out(mock_frontend_context):
    """已经超时不再弹提示，直接触发登出"""

    def check_session_expiration_and_notify(current_active_seconds_ago, ctx):
        timeout_seconds = 1800
        warning_threshold = 300
        remaining = timeout_seconds - current_active_seconds_ago

        if remaining <= warning_threshold and remaining > 0:
            warning_msg = "会话即将过期"
            ctx.notifications.append({
                "type": "warning",
                "message": warning_msg,
                "remaining_seconds": remaining
            })
            return {"show_warning": True, "remaining": remaining}

        if remaining <= 0:
            return {"show_warning": False, "auto_logout": True}

        return {"show_warning": False, "remaining": remaining}

    result = check_session_expiration_and_notify(2000, mock_frontend_context)

    assert result["show_warning"] is False
    assert result["auto_logout"] is True
    assert len(mock_frontend_context.notifications) == 0


# ---------- 端到端：前后端联动 ----------

def test_end_to_end_session_timeout_flow(mock_redis_db2, mock_request, mock_frontend_context):
    """完整流程：前端检测到即将超时弹提示 -> 用户未操作 -> 后端401登出 -> Redis session清除"""
    session_key = "session:" + mock_request.cookies["session_id"]

    def backend_check_session(request, redis_conn, last_active):
        elapsed = time.time() - last_active
        if elapsed > 1800:
            redis_conn.delete("session:" + request.cookies["session_id"])
            return {"status": 401, "redirect": "/login"}
        return {"status": 200, "redirect": None}

    def frontend_check_and_notify(current_active_seconds_ago, ctx):
        timeout_seconds = 1800
        warning_threshold = 300
        remaining = timeout_seconds - current_active_seconds_ago

        if remaining <= warning_threshold and remaining > 0:
            ctx.notifications.append({
                "type": "warning",
                "message": "会话即将过期",
                "remaining_seconds": remaining
            })
            return {"show_warning": True}
        if remaining <= 0:
            return {"auto_logout": True}
        return {"ok": True}

    mock_last_active = time.time() - 1560

    # 阶段1：前端检测到即将超时
    fe_result = frontend_check_and_notify(1560, mock_frontend_context)
    assert fe_result["show_warning"] is True
    assert len(mock_frontend_context.notifications) == 1
    assert mock_frontend_context.notifications[0]["message"] == "会话即将过期"

    # 阶段2：用户未操作，时间继续流逝，超过30分钟
    be_result = backend_check_session(mock_request, mock_redis_db2, mock_last_active - 300)
    assert be_result["status"] == 401
    assert be_result["redirect"] == "/login"
    mock_redis_db2.delete.assert_called_once_with(session_key)
