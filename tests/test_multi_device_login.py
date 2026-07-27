import pytest
import uuid
import threading
from typing import Dict


class SessionStore:
    def __init__(self):
        self._store: Dict[str, Dict[str, str]] = {}

    def create_session(self, user_id: str, device_id: str) -> str:
        session_id = str(uuid.uuid4())
        if user_id not in self._store:
            self._store[user_id] = {}
        self._store[user_id][session_id] = device_id
        return session_id

    def get_active_sessions(self, user_id: str) -> Dict[str, str]:
        return self._store.get(user_id, {}).copy()

    def remove_session(self, user_id: str, session_id: str) -> bool:
        if user_id in self._store and session_id in self._store[user_id]:
            del self._store[user_id][session_id]
            if not self._store[user_id]:
                del self._store[user_id]
            return True
        return False

    def is_session_valid(self, user_id: str, session_id: str) -> bool:
        return user_id in self._store and session_id in self._store[user_id]

    def verify_session(self, session_id: str) -> int:
        for user_id in self._store:
            if session_id in self._store[user_id]:
                return 200
        return 401

    def access_resource(self, user_id: str, session_id: str) -> int:
        if self.is_session_valid(user_id, session_id):
            return 200
        return 401


class TestMultiDeviceLogin:
    def test_multiple_devices_can_login_simultaneously(self):
        store = SessionStore()
        sid_a = store.create_session("user1", "device_a")
        sid_b = store.create_session("user1", "device_b")
        sessions = store.get_active_sessions("user1")
        assert sid_a in sessions
        assert sid_b in sessions
        assert len(sessions) == 2

    def test_device_b_access_returns_http200(self):
        store = SessionStore()
        store.create_session("user1", "device_a")
        sid_b = store.create_session("user1", "device_b")
        status = store.access_resource("user1", sid_b)
        assert status == 200

    def test_device_b_session_independent_from_device_a(self):
        store = SessionStore()
        sid_a = store.create_session("user1", "device_a")
        sid_b = store.create_session("user1", "device_b")
        store.remove_session("user1", sid_a)
        assert store.is_session_valid("user1", sid_b)
        assert not store.is_session_valid("user1", sid_a)

    def test_device_a_logout_only_clears_device_a_session(self):
        store = SessionStore()
        sid_a = store.create_session("user1", "device_a")
        sid_b = store.create_session("user1", "device_b")
        store.remove_session("user1", sid_a)
        assert not store.is_session_valid("user1", sid_a)
        assert store.is_session_valid("user1", sid_b)
        sessions = store.get_active_sessions("user1")
        assert sid_b in sessions
        assert sid_a not in sessions

    def test_concurrent_login_from_multiple_devices(self):
        store = SessionStore()
        results = []
        errors = []

        def login_device(device_id: str):
            try:
                session_id = store.create_session("user1", device_id)
                results.append(session_id)
            except Exception as e:
                errors.append(str(e))

        threads = [threading.Thread(target=login_device, args=(f"device_{i}",)) for i in range(5)]
        for t in threads:
            t.start()
        for t in threads:
            t.join()

        assert len(errors) == 0
        assert len(set(results)) == 5

    def test_verify_nonexistent_session_returns_401(self):
        store = SessionStore()
        assert store.verify_session("nonexistent") == 401

    def test_duplicate_device_login_returns_new_session(self):
        store = SessionStore()
        sid_a = store.create_session("user1", "device_a")
        sid_b = store.create_session("user1", "device_a")
        assert sid_a != sid_b
        assert store.is_session_valid("user1", sid_a)
        assert store.is_session_valid("user1", sid_b)

    def test_logout_invalidated_session_returns_false(self):
        store = SessionStore()
        sid = store.create_session("user1", "device_a")
        assert store.remove_session("user1", sid) is True
        assert store.remove_session("user1", sid) is False

    def test_empty_user_id_returns_empty_sessions(self):
        store = SessionStore()
        assert store.get_active_sessions("") == {}

    def test_get_active_sessions_no_sessions(self):
        store = SessionStore()
        assert store.get_active_sessions("nonexistent_user") == {}
