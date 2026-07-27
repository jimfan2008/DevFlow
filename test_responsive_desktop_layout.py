import pytest
import time
import os
import tempfile
from selenium import webdriver
from selenium.webdriver.common.by import By
from selenium.webdriver.chrome.options import Options
from selenium.webdriver.chrome.service import Service
from webdriver_manager.chrome import ChromeDriverManager


LAYOUT_HTML = """<!DOCTYPE html>
<html><head>
<style>
* { margin:0; padding:0; box-sizing:border-box; }
body { font-family:Arial,sans-serif; }
.container { display:grid; grid-template-columns:240px 1fr 320px; min-height:100vh; }
.sidebar { background:#f0f0f0; padding:20px; }
.main { background:#fff; padding:20px; }
.detail-panel { background:#fafafa; padding:20px; }
.nav-item, .main-button, .detail-item { margin:10px 0; padding:10px; border:1px solid #ddd; }
.sidebar a { display:block; padding:8px; color:#333; text-decoration:none; }
</style></head>
<body>
<div class="container">
<aside class="sidebar" id="sidebar"><h2>导航</h2><a href="#" class="nav-item">首页</a><a href="#" class="nav-item">设置</a><a href="#" class="nav-item">关于</a></aside>
<main class="main" id="main-content"><h1>主内容区</h1><button class="main-button">提交</button><button class="main-button">取消</button></main>
<section class="detail-panel" id="detail-panel"><h3>详情面板</h3><div class="detail-item">项目A</div><div class="detail-item">项目B</div><div class="detail-item">项目C</div></section>
</div>
</body></html>"""


@pytest.fixture(scope="module")
def driver():
    options = Options()
    options.add_argument("--headless=new")
    options.add_argument("--window-size=1400,900")
    service = Service(ChromeDriverManager().install())
    d = webdriver.Chrome(service=service, options=options)
    yield d
    d.quit()


@pytest.fixture
def layout_page(driver):
    tmp = tempfile.NamedTemporaryFile(mode="w", suffix=".html", delete=False)
    tmp.write(LAYOUT_HTML)
    tmp.close()
    driver.get(f"file://{tmp.name}")
    yield driver
    os.unlink(tmp.name)


class TestResponsiveDesktopLayout:
    def test_three_column_layout(self, layout_page):
        sidebar = layout_page.find_element(By.ID, "sidebar")
        main_content = layout_page.find_element(By.ID, "main-content")
        detail_panel = layout_page.find_element(By.ID, "detail-panel")
        assert sidebar.is_displayed()
        assert main_content.is_displayed()
        assert detail_panel.is_displayed()
        sidebar_width = sidebar.size["width"]
        total_width = layout_page.execute_script(
            "return document.querySelector('.container').offsetWidth"
        )
        assert sidebar_width == 240
        assert total_width >= 1280

    def test_first_load_within_2_seconds(self, driver):
        tmp = tempfile.NamedTemporaryFile(mode="w", suffix=".html", delete=False)
        tmp.write(LAYOUT_HTML)
        tmp.close()
        start = time.time()
        driver.get(f"file://{tmp.name}")
        elapsed = time.time() - start
        os.unlink(tmp.name)
        assert elapsed <= 2.0, f"首屏加载 {elapsed:.2f}s 超过 2s 限制"

    def test_interactive_elements_displayed(self, layout_page):
        nav_items = layout_page.find_elements(By.CLASS_NAME, "nav-item")
        assert len(nav_items) == 3
        for item in nav_items:
            assert item.is_displayed()
            assert item.is_enabled()
        buttons = layout_page.find_elements(By.CLASS_NAME, "main-button")
        assert len(buttons) == 2
        for btn in buttons:
            assert btn.is_displayed()
            assert btn.is_enabled()
        details = layout_page.find_elements(By.CLASS_NAME, "detail-item")
        assert len(details) == 3
        for d in details:
            assert d.is_displayed()
