import pytest
import requests
import time

CORE_ROUTES = [
    "/",
    "/login",
    "/register",
    "/dashboard",
    "/settings",
    "/profile",
]

BASE_URL = "http://localhost:5000"

TIMEOUT = 5


def test_all_core_routes_return_200():
    for route in CORE_ROUTES:
        url = f"{BASE_URL}{route}"
        response = requests.get(url, timeout=TIMEOUT)
        assert response.status_code == 200, f"{url} returned {response.status_code}"


def test_first_screen_load_time():
    url = f"{BASE_URL}/"
    start = time.time()
    requests.get(url, timeout=TIMEOUT)
    elapsed = time.time() - start
    assert elapsed <= 2.0, f"首屏加载时间 {elapsed:.3f}s 超过 2s"


def test_route_switching_time():
    TIMES = 3
    for _ in range(TIMES):
        for route in CORE_ROUTES:
            url = f"{BASE_URL}{route}"
            start = time.time()
            requests.get(url, timeout=TIMEOUT)
            elapsed = time.time() - start
            assert elapsed <= 0.3, f"路由 {route} 切换时间 {elapsed:.3f}s 超过 300ms"
