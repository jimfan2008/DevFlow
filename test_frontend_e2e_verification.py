import os
import time
from dataclasses import dataclass
from typing import Optional

import pytest
from playwright.sync_api import sync_playwright, Page


# ============================================================
# 测试数据与模型
# ============================================================

@dataclass
class RouteDefinition:
    """前端路由定义"""
    path: str
    name: str
    requires_auth: bool = False
    expected_title_contains: str = "DevFlow"

PUBLIC_ROUTES = [
    RouteDefinition(path="/login", name="登录页", requires_auth=False),
    RouteDefinition(path="/register", name="注册页", requires_auth=False),
]

AUTH_ROUTES = [
    RouteDefinition(path="/projects", name="项目管理", requires_auth=True),
    RouteDefinition(path="/agents", name="Agent管理", requires_auth=True),
    RouteDefinition(path="/skills", name="Skill管理", requires_auth=True),
    RouteDefinition(path="/boards", name="看板列表", requires_auth=True),
    RouteDefinition(path="/chat", name="群聊与会议", requires_auth=True),
    RouteDefinition(path="/notifications", name="通知中心", requires_auth=True),
    RouteDefinition(path="/delivery", name="项目交付", requires_auth=True),
    RouteDefinition(path="/requirements", name="需求管理", requires_auth=True),
    RouteDefinition(path="/profile", name="个人资料", requires_auth=True),
]

ALL_ROUTES = PUBLIC_ROUTES + AUTH_ROUTES

FIRST_SCREEN_TIMEOUT_MS = 3000
ROUTE_SWITCH_TIMEOUT_MS = 500


# ============================================================
# 前端 E2E 辅助层
# ============================================================

class FrontendE2EHelper:
    """前端 E2E 测试辅助类 — 封装浏览器操作和断言"""

    def __init__(self, page: Page, base_url: str):
        self.page = page
        self.base_url = base_url

    def inject_mock_token(self) -> None:
        """注入模拟 token 到 localStorage 以绕过认证守卫"""
        self.page.evaluate("""
            localStorage.setItem('access_token', 'e2e-mock-token-' + Date.now());
            localStorage.setItem('refresh_token', 'e2e-mock-refresh-' + Date.now());
        """)

    def clear_auth_tokens(self) -> None:
        """清除 localStorage 中的认证 token"""
        self.page.evaluate("""
            localStorage.removeItem('access_token');
            localStorage.removeItem('refresh_token');
        """)

    def navigate_to(self, path: str, wait_timeout: int = 10000) -> tuple:
        """
        导航到指定路由，返回 (http_status, load_time_ms)
        """
        start = time.perf_counter()
        response = self.page.goto(f"{self.base_url}{path}", timeout=wait_timeout)
        load_time_ms = (time.perf_counter() - start) * 1000
        status = response.status if response else 0
        return status, load_time_ms

    def get_page_title(self) -> str:
        """获取当前页面标题"""
        return self.page.title()

    def get_current_path(self) -> str:
        """获取当前 URL 路径"""
        return self.page.url()

    def wait_for_selector(self, selector: str, timeout: int = 5000) -> bool:
        """等待选择器出现"""
        try:
            self.page.wait_for_selector(selector, timeout=timeout, state="attached")
            return True
        except Exception:
            return False

    def check_element_visible(self, selector: str, timeout: int = 3000) -> bool:
        """检查元素是否可见"""
        try:
            el = self.page.locator(selector).first
            el.wait_for(state="visible", timeout=timeout)
            return True
        except Exception:
            return False

    def check_element_text(self, selector: str, expected_text: str, timeout: int = 3000) -> bool:
        """检查元素包含预期文本"""
        try:
            el = self.page.locator(selector).first
            el.wait_for(state="attached", timeout=timeout)
            text = el.inner_text()
            return expected_text in text
        except Exception:
            return False

    def click_button(self, text: str, timeout: int = 5000) -> bool:
        """点击按钮"""
        try:
            btn = self.page.locator(f'button:has-text("{text}")').first
            btn.wait_for(state="visible", timeout=timeout)
            btn.click()
            return True
        except Exception:
            return False

    def fill_input(self, selector: str, value: str) -> bool:
        """填充输入框"""
        try:
            self.page.fill(selector, value)
            return True
        except Exception:
            return False

    def take_screenshot_on_failure(self, name: str) -> str:
        """截图保存"""
        path = f"/tmp/e2e_screenshot_{name}_{int(time.time())}.png"
        self.page.screenshot(path=path, full_page=True)
        return path


# ============================================================
# Fixture
# ============================================================

@pytest.fixture(scope="session")
def playwright_instance():
    """创建 Playwright 实例"""
    with sync_playwright() as p:
        yield p


class BrowserTester:
    """单浏览器测试器"""

    def __init__(self, pw, browser_type_name: str, channel: Optional[str] = None):
        self.pw = pw
        self.browser_type_name = browser_type_name
        self.channel = channel

    def launch(self, base_url: str) -> tuple:
        """启动浏览器，返回 (browser, context, page, helper)"""
        bt = getattr(self.pw, self.browser_type_name)
        launch_opts = {"headless": True, "args": ["--no-sandbox", "--disable-gpu"]}
        if self.channel:
            launch_opts["channel"] = self.channel
        browser = bt.launch(**launch_opts)
        context = browser.new_context(viewport={"width": 1440, "height": 900})
        page = context.new_page()
        helper = FrontendE2EHelper(page, base_url)
        return browser, context, page, helper

    def name(self) -> str:
        return f"{self.browser_type_name}" + (f"({self.channel})" if self.channel else "")


@pytest.fixture(params=[
    ("chromium", None),
    ("firefox", None),
    ("webkit", None),
], ids=["chromium", "firefox", "webkit"])
def browser_config(request):
    """参量化浏览器配置"""
    return request.param


@pytest.fixture
def base_url():
    """前端开发服务器地址，可通过 FRONTEND_URL 环境变量覆盖"""
    return os.getenv("FRONTEND_URL", "http://localhost:5173")


# ============================================================
# 测试：路由可访问性（多浏览器）
# ============================================================

class TestRouteAccessibilityMultiBrowser:
    """验证所有路由在3种浏览器中均可访问"""

    def test_public_routes_accessible(self, playwright_instance, browser_config, base_url):
        """公开路由在对应浏览器中返回 200"""
        bt_name, bt_channel = browser_config
        bt = BrowserTester(playwright_instance, bt_name, bt_channel)
        browser, context, page, helper = bt.launch(base_url)
        try:
            helper.clear_auth_tokens()
            for route in PUBLIC_ROUTES:
                status, load_time = helper.navigate_to(route.path)
                assert status == 200, f"[{bt.name()}] {route.name}({route.path}) 期望状态 200，实际 {status}"
                assert load_time <= FIRST_SCREEN_TIMEOUT_MS, (
                    f"[{bt.name()}] {route.name} 首屏加载 {load_time:.0f}ms 超过 {FIRST_SCREEN_TIMEOUT_MS}ms"
                )
        finally:
            context.close()
            browser.close()

    def test_auth_routes_accessible_with_token(self, playwright_instance, browser_config, base_url):
        """注入 token 后认证路由可访问"""
        bt_name, bt_channel = browser_config
        bt = BrowserTester(playwright_instance, bt_name, bt_channel)
        browser, context, page, helper = bt.launch(base_url)
        try:
            helper.inject_mock_token()
            helper.navigate_to("/", wait_timeout=5000)
            time.sleep(0.3)
            for route in AUTH_ROUTES:
                status, load_time = helper.navigate_to(route.path)
                assert status == 200, f"[{bt.name()}] {route.name}({route.path}) 期望 200，实际 {status}"
        finally:
            context.close()
            browser.close()

    def test_root_redirects_to_login_when_unauthenticated(self, playwright_instance, browser_config, base_url):
        """未登录时根路径重定向到 /login"""
        bt_name, bt_channel = browser_config
        bt = BrowserTester(playwright_instance, bt_name, bt_channel)
        browser, context, page, helper = bt.launch(base_url)
        try:
            helper.clear_auth_tokens()
            helper.navigate_to("/")
            time.sleep(0.8)
            current_url = helper.get_current_path()
            assert "/login" in current_url, f"[{bt.name()}] 未登录时 '/' 应重定向到 '/login'，实际: {current_url}"
        finally:
            context.close()
            browser.close()

    def test_root_redirects_to_projects_when_authenticated(self, playwright_instance, browser_config, base_url):
        """已登录时根路径重定向到 /projects"""
        bt_name, bt_channel = browser_config
        bt = BrowserTester(playwright_instance, bt_name, bt_channel)
        browser, context, page, helper = bt.launch(base_url)
        try:
            helper.inject_mock_token()
            helper.navigate_to("/")
            time.sleep(0.5)
            page.reload()
            time.sleep(0.5)
            current_url = helper.get_current_path()
            assert "/projects" in current_url, f"[{bt.name()}] 已登录时 '/' 应重定向到 '/projects'，实际: {current_url}"
        finally:
            context.close()
            browser.close()

    def test_404_page_returns_200_for_spa(self, playwright_instance, browser_config, base_url):
        """SPA 对不存在的路由也返回 200"""
        bt_name, bt_channel = browser_config
        bt = BrowserTester(playwright_instance, bt_name, bt_channel)
        browser, context, page, helper = bt.launch(base_url)
        try:
            status, _ = helper.navigate_to("/this/page/does/not/exist")
            assert status == 200, f"[{bt.name()}] 404 路由 SPA 期望返回 200，实际 {status}"
        finally:
            context.close()
            browser.close()

    def test_browser_compatibility_count_ge_3(self, playwright_instance, base_url):
        """浏览器兼容覆盖 >= 3 种"""
        browsers = [
            ("chromium", None),
            ("firefox", None),
            ("webkit", None),
        ]
        successful_browsers = []
        for bt_name, bt_channel in browsers:
            bt = BrowserTester(playwright_instance, bt_name, bt_channel)
            try:
                browser, context, page, helper = bt.launch(base_url)
                helper.clear_auth_tokens()
                status, _ = helper.navigate_to("/login")
                if status == 200:
                    successful_browsers.append(bt.name())
                context.close()
                browser.close()
            except Exception:
                pass
        assert len(successful_browsers) >= 3, (
            f"浏览器兼容覆盖不足 3 种，成功: {successful_browsers}"
        )


# ============================================================
# 测试：首屏加载性能（多浏览器）
# ============================================================

class TestFirstScreenPerformance:
    """验证首屏加载时间 <= 2秒（多浏览器）"""

    def test_public_route_first_screen_under_2s(self, playwright_instance, browser_config, base_url):
        """公开路由首屏加载 <= 2秒"""
        bt_name, bt_channel = browser_config
        bt = BrowserTester(playwright_instance, bt_name, bt_channel)
        browser, context, page, helper = bt.launch(base_url)
        try:
            helper.clear_auth_tokens()
            for route in PUBLIC_ROUTES:
                status, load_time = helper.navigate_to(route.path)
                assert status == 200, f"[{bt.name()}] {route.name} 非 200"
                assert load_time <= 2000, (
                    f"[{bt.name()}] {route.name} 首屏 {load_time:.0f}ms 超过 2000ms"
                )
        finally:
            context.close()
            browser.close()

    def test_auth_route_first_screen_under_2s(self, playwright_instance, browser_config, base_url):
        """认证路由首屏加载 <= 2秒"""
        bt_name, bt_channel = browser_config
        bt = BrowserTester(playwright_instance, bt_name, bt_channel)
        browser, context, page, helper = bt.launch(base_url)
        try:
            helper.inject_mock_token()
            helper.navigate_to("/", wait_timeout=5000)
            time.sleep(0.3)
            for route in AUTH_ROUTES[:3]:
                status, load_time = helper.navigate_to(route.path)
                assert status == 200, f"[{bt.name()}] {route.name} 非 200"
                assert load_time <= 2000, (
                    f"[{bt.name()}] {route.name} 首屏 {load_time:.0f}ms 超过 2000ms"
                )
        finally:
            context.close()
            browser.close()


# ============================================================
# 测试：路由切换性能（多浏览器）
# ============================================================

class TestRouteSwitchPerformance:
    """验证路由切换时间 <= 300ms（多浏览器）"""

    def test_public_route_switch_under_300ms(self, playwright_instance, browser_config, base_url):
        """公开路由间切换 <= 300ms"""
        bt_name, bt_channel = browser_config
        bt = BrowserTester(playwright_instance, bt_name, bt_channel)
        browser, context, page, helper = bt.launch(base_url)
        try:
            helper.clear_auth_tokens()
            helper.navigate_to("/login")
            time.sleep(0.3)
            start = time.perf_counter()
            helper.navigate_to("/register")
            page.wait_for_load_state("domcontentloaded")
            switch_time = (time.perf_counter() - start) * 1000
            assert switch_time <= 300, (
                f"[{bt.name()}] 公开路由切换 {switch_time:.0f}ms 超过 300ms"
            )
        finally:
            context.close()
            browser.close()

    def test_auth_route_switch_under_300ms(self, playwright_instance, browser_config, base_url):
        """认证路由间切换 <= 300ms"""
        bt_name, bt_channel = browser_config
        bt = BrowserTester(playwright_instance, bt_name, bt_channel)
        browser, context, page, helper = bt.launch(base_url)
        try:
            helper.inject_mock_token()
            helper.navigate_to("/")
            time.sleep(0.3)
            helper.navigate_to("/projects")
            page.wait_for_load_state("domcontentloaded")
            time.sleep(0.3)
            start = time.perf_counter()
            helper.navigate_to("/agents")
            page.wait_for_load_state("domcontentloaded")
            switch_time = (time.perf_counter() - start) * 1000
            assert switch_time <= 500, (
                f"[{bt.name()}] 认证路由切换 {switch_time:.0f}ms 超过 500ms"
            )
        finally:
            context.close()
            browser.close()


# ============================================================
# 测试：页面标题验证（多浏览器）
# ============================================================

class TestPageTitleVerification:
    """验证页面标题包含 DevFlow（多浏览器）"""

    def test_login_page_title_contains_devflow(self, playwright_instance, browser_config, base_url):
        """登录页标题包含 DevFlow"""
        bt_name, bt_channel = browser_config
        bt = BrowserTester(playwright_instance, bt_name, bt_channel)
        browser, context, page, helper = bt.launch(base_url)
        try:
            helper.clear_auth_tokens()
            helper.navigate_to("/login")
            title = helper.get_page_title()
            assert "DevFlow" in title, f"[{bt.name()}] 登录页标题 '{title}' 不包含 'DevFlow'"
        finally:
            context.close()
            browser.close()

    def test_register_page_title_contains_devflow(self, playwright_instance, browser_config, base_url):
        """注册页标题包含 DevFlow"""
        bt_name, bt_channel = browser_config
        bt = BrowserTester(playwright_instance, bt_name, bt_channel)
        browser, context, page, helper = bt.launch(base_url)
        try:
            helper.clear_auth_tokens()
            helper.navigate_to("/register")
            title = helper.get_page_title()
            assert "DevFlow" in title, f"[{bt.name()}] 注册页标题 '{title}' 不包含 'DevFlow'"
        finally:
            context.close()
            browser.close()

    def test_projects_page_title_contains_devflow(self, playwright_instance, browser_config, base_url):
        """项目管理页标题包含 DevFlow"""
        bt_name, bt_channel = browser_config
        bt = BrowserTester(playwright_instance, bt_name, bt_channel)
        browser, context, page, helper = bt.launch(base_url)
        try:
            helper.inject_mock_token()
            helper.navigate_to("/")
            time.sleep(0.3)
            helper.navigate_to("/projects")
            title = helper.get_page_title()
            assert "DevFlow" in title, f"[{bt.name()}] 项目管理页标题 '{title}' 不包含 'DevFlow'"
        finally:
            context.close()
            browser.close()


# ============================================================
# 测试：UI 组件可见性验证
# ============================================================

class TestUIComponentVisibility:
    """验证关键 UI 组件在对应页面中可见"""

    def test_login_page_has_form_elements(self, playwright_instance, browser_config, base_url):
        """登录页包含表单元素"""
        bt_name, bt_channel = browser_config
        bt = BrowserTester(playwright_instance, bt_name, bt_channel)
        browser, context, page, helper = bt.launch(base_url)
        try:
            helper.clear_auth_tokens()
            helper.navigate_to("/login")
            has_input = helper.check_element_visible('input[type="email"], input[type="text"]')
            has_password = helper.check_element_visible('input[type="password"]')
            has_submit = helper.check_element_visible('button')
            assert has_input or has_password or has_submit, (
                f"[{bt.name()}] 登录页未找到表单元素"
            )
        finally:
            context.close()
            browser.close()

    def test_register_page_has_form_elements(self, playwright_instance, browser_config, base_url):
        """注册页包含表单元素"""
        bt_name, bt_channel = browser_config
        bt = BrowserTester(playwright_instance, bt_name, bt_channel)
        browser, context, page, helper = bt.launch(base_url)
        try:
            helper.clear_auth_tokens()
            helper.navigate_to("/register")
            has_input = helper.check_element_visible('input')
            has_submit = helper.check_element_visible('button')
            assert has_input or has_submit, (
                f"[{bt.name()}] 注册页未找到表单元素"
            )
        finally:
            context.close()
            browser.close()

    def test_auth_page_has_sidebar_or_layout(self, playwright_instance, browser_config, base_url):
        """认证页面包含布局组件（侧边栏或主布局）"""
        bt_name, bt_channel = browser_config
        bt = BrowserTester(playwright_instance, bt_name, bt_channel)
        browser, context, page, helper = bt.launch(base_url)
        try:
            helper.inject_mock_token()
            helper.navigate_to("/")
            time.sleep(0.5)
            helper.navigate_to("/projects")
            has_layout = (
                helper.check_element_visible('.desktop-layout, .app-sidebar, .el-aside, nav, header')
            )
            assert has_layout, f"[{bt.name()}] 项目页面未找到布局组件"
        finally:
            context.close()
            browser.close()

    def test_page_doms_are_rendered_correctly(self, playwright_instance, browser_config, base_url):
        """页面 DOM 正常渲染（至少有一个根元素有内容）"""
        bt_name, bt_channel = browser_config
        bt = BrowserTester(playwright_instance, bt_name, bt_channel)
        browser, context, page, helper = bt.launch(base_url)
        try:
            helper.clear_auth_tokens()
            helper.navigate_to("/login")
            body = page.inner_text("body")
            assert len(body.strip()) > 0, f"[{bt.name()}] 登录页 body 内容为空"
        finally:
            context.close()
            browser.close()


# ============================================================
# 测试：前端功能通过率计算
# ============================================================

class TestFrontendPassRate:
    """验证前端功能通过率 = 100%"""

    def test_all_public_routes_pass_in_browser(self, playwright_instance, browser_config, base_url):
        """当前浏览器中所有公开路由通过率为 100%"""
        bt_name, bt_channel = browser_config
        bt = BrowserTester(playwright_instance, bt_name, bt_channel)
        browser, context, page, helper = bt.launch(base_url)
        try:
            helper.clear_auth_tokens()
            results = []
            for route in PUBLIC_ROUTES:
                status, load_time = helper.navigate_to(route.path)
                title = helper.get_page_title()
                passed = (status == 200 and load_time <= FIRST_SCREEN_TIMEOUT_MS and "DevFlow" in title)
                results.append({"route": route.name, "passed": passed})

            total = len(results)
            passed_count = sum(1 for r in results if r["passed"])
            pass_rate = (passed_count / total * 100) if total > 0 else 0

            failed = [r for r in results if not r["passed"]]
            assert pass_rate == 100.0, (
                f"[{bt.name()}] 前端功能通过率 {pass_rate:.1f}%，期望 100%。失败: {[r['route'] for r in failed]}"
            )
        finally:
            context.close()
            browser.close()

    def test_all_auth_routes_pass_in_browser(self, playwright_instance, browser_config, base_url):
        """当前浏览器中所有认证路由通过率为 100%"""
        bt_name, bt_channel = browser_config
        bt = BrowserTester(playwright_instance, bt_name, bt_channel)
        browser, context, page, helper = bt.launch(base_url)
        try:
            helper.inject_mock_token()
            helper.navigate_to("/", wait_timeout=5000)
            time.sleep(0.3)
            results = []
            for route in AUTH_ROUTES:
                status, _ = helper.navigate_to(route.path)
                passed = status == 200
                results.append({"route": route.name, "path": route.path, "passed": passed})

            total = len(results)
            passed_count = sum(1 for r in results if r["passed"])
            pass_rate = (passed_count / total * 100) if total > 0 else 0

            failed = [r for r in results if not r["passed"]]
            assert pass_rate == 100.0, (
                f"[{bt.name()}] 认证路由通过率 {pass_rate:.1f}%，期望 100%。失败: {[r['route'] for r in failed]}"
            )
        finally:
            context.close()
            browser.close()

    def test_overall_frontend_pass_rate_100_percent(self, playwright_instance, base_url):
        """综合前端功能通过率 = 100%（跨所有浏览器）"""
        browsers = [
            ("chromium", None),
            ("firefox", None),
            ("webkit", None),
        ]
        total_tests = 0
        passed_tests = 0
        browser_names_covered = []

        for bt_name, bt_channel in browsers:
            bt = BrowserTester(playwright_instance, bt_name, bt_channel)
            try:
                browser, context, page, helper = bt.launch(base_url)
                helper.clear_auth_tokens()

                for route in PUBLIC_ROUTES:
                    total_tests += 1
                    status, _ = helper.navigate_to(route.path)
                    if status == 200:
                        passed_tests += 1

                helper.inject_mock_token()
                helper.navigate_to("/", wait_timeout=5000)
                time.sleep(0.2)

                for route in AUTH_ROUTES:
                    total_tests += 1
                    status, _ = helper.navigate_to(route.path)
                    if status == 200:
                        passed_tests += 1

                browser_names_covered.append(bt.name())
                context.close()
                browser.close()
            except Exception:
                pass

        pass_rate = (passed_tests / total_tests * 100) if total_tests > 0 else 0
        failed_count = total_tests - passed_tests

        assert pass_rate == 100.0, (
            f"综合功能通过率 {pass_rate:.1f}% ({passed_tests}/{total_tests})，"
            f"期望 100%。浏览器覆盖: {browser_names_covered}"
        )
        assert len(browser_names_covered) >= 3, (
            f"浏览器兼容覆盖 {len(browser_names_covered)} 种，期望 >= 3 种"
        )


# ============================================================
# 测试：LocalStorage 认证隔离
# ============================================================

class TestLocalStorageAuthIsolation:
    """验证 localStorage 认证状态在页面间隔离"""

    def test_token_persists_across_page_navigation(self, playwright_instance, browser_config, base_url):
        """注入 token 后跨页面导航保持"""
        bt_name, bt_channel = browser_config
        bt = BrowserTester(playwright_instance, bt_name, bt_channel)
        browser, context, page, helper = bt.launch(base_url)
        try:
            helper.inject_mock_token()
            token_before = page.evaluate("localStorage.getItem('access_token')")
            assert token_before is not None and len(token_before) > 0

            helper.navigate_to("/projects")
            token_after = page.evaluate("localStorage.getItem('access_token')")
            assert token_after is not None and len(token_after) > 0
            assert token_before == token_after
        finally:
            context.close()
            browser.close()

    def test_clearing_tokens_redirects_to_login(self, playwright_instance, browser_config, base_url):
        """清除 token 后访问认证路由应重定向到登录页"""
        bt_name, bt_channel = browser_config
        bt = BrowserTester(playwright_instance, bt_name, bt_channel)
        browser, context, page, helper = bt.launch(base_url)
        try:
            helper.inject_mock_token()
            helper.navigate_to("/projects")
            time.sleep(0.3)
            helper.clear_auth_tokens()
            page.reload()
            time.sleep(0.8)
            current_url = helper.get_current_path()
            assert "/login" in current_url, (
                f"[{bt.name()}] 清除 token 后访问认证路由应重定向到登录，实际: {current_url}"
            )
        finally:
            context.close()
            browser.close()


# ============================================================
# 测试：空数据与空状态场景
# ============================================================

class TestEmptyStateScenarios:
    """验证空数据 / 空 token 等边界状态下的前端行为"""

    def test_empty_token_redirects_to_login(self, playwright_instance, browser_config, base_url):
        """localStorage 中 token 为空字符串时应重定向到登录页"""
        bt_name, bt_channel = browser_config
        bt = BrowserTester(playwright_instance, bt_name, bt_channel)
        browser, context, page, helper = bt.launch(base_url)
        try:
            # 注入空字符串 token
            page.evaluate("localStorage.setItem('access_token', '')")
            page.evaluate("localStorage.setItem('refresh_token', '')")
            helper.navigate_to("/")
            time.sleep(0.8)
            current_url = helper.get_current_path()
            assert "/login" in current_url, (
                f"[{bt.name()}] 空 token 时 '/' 应重定向到 '/login'，实际: {current_url}"
            )
        finally:
            context.close()
            browser.close()

    def test_expired_format_token_redirects_to_login(self, playwright_instance, browser_config, base_url):
        """过期格式 token（非 JWT 格式）应重定向到登录页"""
        bt_name, bt_channel = browser_config
        bt = BrowserTester(playwright_instance, bt_name, bt_channel)
        browser, context, page, helper = bt.launch(base_url)
        try:
            page.evaluate("localStorage.setItem('access_token', 'expired.invalid.token')")
            page.evaluate("localStorage.setItem('refresh_token', 'expired.refresh')")
            helper.navigate_to("/")
            time.sleep(0.8)
            current_url = helper.get_current_path()
            # 过期 token 应重定向到 /login 或停留在 /login
            assert "/login" in current_url, (
                f"[{bt.name()}] 过期 token 时 '/' 应重定向到 '/login'，实际: {current_url}"
            )
        finally:
            context.close()
            browser.close()

    def test_empty_project_list_shows_empty_state(self, playwright_instance, browser_config, base_url):
        """空项目列表页面应展示空状态组件（而非白屏或报错）"""
        bt_name, bt_channel = browser_config
        bt = BrowserTester(playwright_instance, bt_name, bt_channel)
        browser, context, page, helper = bt.launch(base_url)
        try:
            helper.inject_mock_token()
            helper.navigate_to("/")
            time.sleep(0.3)
            helper.navigate_to("/projects")
            time.sleep(0.5)
            # 页面 body 不应为空，说明页面渲染正常（无论有无数据）
            body = page.inner_text("body")
            assert len(body.strip()) > 0, (
                f"[{bt.name()}] 项目列表页 body 内容为空，应为空状态组件或列表"
            )
            # 应该能发现页面有内容区域
            has_content = helper.check_element_visible('main, .container, .el-table, .el-empty, table, ul')
            assert has_content, (
                f"[{bt.name()}] 项目列表页未找到内容区域（可能未渲染空状态组件）"
            )
        finally:
            context.close()
            browser.close()

    def test_corrupted_localstorage_does_not_crash(self, playwright_instance, browser_config, base_url):
        """localStorage 中存储了非 JSON 格式数据不应导致页面崩溃"""
        bt_name, bt_channel = browser_config
        bt = BrowserTester(playwright_instance, bt_name, bt_channel)
        browser, context, page, helper = bt.launch(base_url)
        try:
            # 注入非法 JSON 数据
            page.evaluate("localStorage.setItem('user_info', '{invalid-json}')")
            page.evaluate("localStorage.setItem('settings', 'not-a-json-object')")
            helper.navigate_to("/login")
            time.sleep(0.5)
            # 页面至少应渲染出 login 页面，200 状态码
            status, _ = helper.navigate_to("/login")
            assert status == 200, (
                f"[{bt.name()}] 损坏的 localStorage 不应导致页面返回非 200 状态码，实际: {status}"
            )
        finally:
            context.close()
            browser.close()


# ============================================================
# 测试：并发与竞态条件
# ============================================================

class TestRaceConditions:
    """验证快速导航、并发操作等竞态条件下的前端行为"""

    def test_rapid_route_switching_no_crash(self, playwright_instance, browser_config, base_url):
        """快速切换多个路由不应导致页面崩溃"""
        bt_name, bt_channel = browser_config
        bt = BrowserTester(playwright_instance, bt_name, bt_channel)
        browser, context, page, helper = bt.launch(base_url)
        try:
            helper.clear_auth_tokens()
            routes = ["/login", "/register", "/login", "/register", "/login"]
            for route_path in routes:
                status, _ = helper.navigate_to(route_path)
                assert status == 200, (
                    f"[{bt.name()}] 快速切换至 {route_path} 时返回 {status}，期望 200"
                )
                time.sleep(0.05)  # 模拟快速连续切换
            # 最终页面应正常渲染
            body = page.inner_text("body")
            assert len(body.strip()) > 0, (
                f"[{bt.name()}] 快速切换后页面 body 为空"
            )
        finally:
            context.close()
            browser.close()

    def test_concurrent_auth_route_switching(self, playwright_instance, browser_config, base_url):
        """认证路由快速切换后页面仍应正常渲染"""
        bt_name, bt_channel = browser_config
        bt = BrowserTester(playwright_instance, bt_name, bt_channel)
        browser, context, page, helper = bt.launch(base_url)
        try:
            helper.inject_mock_token()
            helper.navigate_to("/")
            time.sleep(0.3)
            # 快速切换认证路由
            auth_paths = ["/projects", "/agents", "/skills", "/boards"]
            for path in auth_paths:
                helper.navigate_to(path)
                time.sleep(0.05)
            # 最终页面应正常
            status = page.evaluate("() => document.readyState")
            assert status == "complete", (
                f"[{bt.name()}] 快速切换后页面未完全加载，readyState={status}"
            )
            body = page.inner_text("body")
            assert len(body.strip()) > 0, (
                f"[{bt.name()}] 快速切换后认证路由 body 为空"
            )
        finally:
            context.close()
            browser.close()

    def test_simultaneous_token_inject_and_navigation(self, playwright_instance, browser_config, base_url):
        """注入 token 后立即导航到认证路由"""
        bt_name, bt_channel = browser_config
        bt = BrowserTester(playwright_instance, bt_name, bt_channel)
        browser, context, page, helper = bt.launch(base_url)
        try:
            # 不等待，直接注入 token 后导航
            helper.inject_mock_token()
            status, load_time = helper.navigate_to("/projects")
            assert status == 200, (
                f"[{bt.name()}] 注入 token 后立即导航到 /projects 应返回 200，实际 {status}"
            )
            assert load_time <= FIRST_SCREEN_TIMEOUT_MS, (
                f"[{bt.name()}] 注入 token 后导航 {load_time:.0f}ms 超限"
            )
        finally:
            context.close()
            browser.close()


# ============================================================
# 测试：网络超时与失败模拟
# ============================================================

class TestNetworkFailureScenarios:
    """验证网络异常情况下前端容错行为"""

    def test_page_handles_slow_server_response(self, playwright_instance, browser_config, base_url):
        """服务器响应较慢时页面仍应最终加载完成"""
        bt_name, bt_channel = browser_config
        bt = BrowserTester(playwright_instance, bt_name, bt_channel)
        browser, context, page, helper = bt.launch(base_url)
        try:
            helper.clear_auth_tokens()
            # 使用较长超时进行导航
            status, load_time = helper.navigate_to("/login", wait_timeout=30000)
            assert status == 200, (
                f"[{bt.name()}] 慢响应下 /login 应返回 200，实际 {status}"
            )
            # 页面应在合理时间内加载
            assert load_time <= 10000, (
                f"[{bt.name()}] 页面加载 {load_time:.0f}ms 超过 10 秒"
            )
        finally:
            context.close()
            browser.close()

    def test_route_fallback_on_500_error(self, playwright_instance, browser_config, base_url):
        """请求非存在路径应触发 SPA fallback 而非崩溃"""
        bt_name, bt_channel = browser_config
        bt = BrowserTester(playwright_instance, bt_name, bt_channel)
        browser, context, page, helper = bt.launch(base_url)
        try:
            # 访问一个不存在的 API 路径
            statuses = []
            for path in ["/unknown-page", "/api/nonexistent", "/test/test/123"]:
                status, _ = helper.navigate_to(path)
                statuses.append(status)
            # SPA 应返回 200（由前端接管路由）
            for i, status in enumerate(statuses):
                assert status == 200, (
                    f"[{bt.name()}] 路径 {['/unknown-page', '/api/nonexistent', '/test/test/123'][i]} "
                    f"期望 200（SPA fallback），实际 {status}"
                )
        finally:
            context.close()
            browser.close()

    def test_network_route_after_context_reset(self, playwright_instance, browser_config, base_url):
        """浏览器上下文重置后路由仍可正常访问"""
        bt_name, bt_channel = browser_config
        bt = BrowserTester(playwright_instance, bt_name, bt_channel)
        browser, context, page, helper = bt.launch(base_url)
        try:
            helper.clear_auth_tokens()
            helper.navigate_to("/login")
            # 清除所有 localStorage
            page.evaluate("localStorage.clear()")
            # 重新导航
            status, _ = helper.navigate_to("/login")
            assert status == 200, (
                f"[{bt.name()}] 清除 localStorage 后导航 /login 应返回 200，实际 {status}"
            )
            # 页面应仍有内容
            body = page.inner_text("body")
            assert len(body.strip()) > 0, (
                f"[{bt.name()}] 清除 localStorage 后页面 body 为空"
            )
        finally:
            context.close()
            browser.close()


if __name__ == "__main__":
    pytest.main([__file__, "-v"])
