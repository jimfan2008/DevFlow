import pytest
import threading
import time
from http.server import HTTPServer, SimpleHTTPRequestHandler
from pathlib import Path
import tempfile
import os
from playwright.sync_api import sync_playwright

TEST_HTML = """<!DOCTYPE html>
<html lang="zh-CN">
<head>
<meta charset="UTF-8">
<meta name="viewport" content="width=device-width, initial-scale=1.0">
<title>桌面端布局测试</title>
<style>
* { margin: 0; padding: 0; box-sizing: border-box; }
html, body { height: 100%; }
.layout { display: flex; height: 100vh; }
.sidebar {
  width: 260px; min-width: 260px; background: #f0f0f0;
  padding: 16px; display: flex; flex-direction: column; gap: 12px;
}
.sidebar .nav-item { padding: 8px 12px; background: #fff; border-radius: 4px; cursor: pointer; }
.sidebar .nav-item:hover { background: #e0e0e0; }
.content { flex: 1; padding: 24px; overflow-y: auto; }
.content .card { background: #fff; border: 1px solid #ddd; border-radius: 8px; padding: 16px; margin-bottom: 16px; }
.content .card .btn { display: inline-block; padding: 8px 16px; background: #1890ff; color: #fff; border: none; border-radius: 4px; cursor: pointer; }
.content .card .btn:hover { background: #40a9ff; }
.detail-panel {
  width: 320px; min-width: 320px; background: #fafafa;
  border-left: 1px solid #ddd; padding: 16px; display: flex; flex-direction: column; gap: 12px;
}
.detail-panel .detail-item { padding: 8px 12px; background: #fff; border-radius: 4px; }
</style>
</head>
<body>
<div class="layout">
  <aside class="sidebar" data-testid="sidebar">
    <div class="nav-item" data-testid="nav-item-1">导航项 1</div>
    <div class="nav-item" data-testid="nav-item-2">导航项 2</div>
    <div class="nav-item" data-testid="nav-item-3">导航项 3</div>
  </aside>
  <main class="content" data-testid="content">
    <div class="card" data-testid="card-1">
      <h3>卡片标题 1</h3>
      <p>卡片内容描述</p>
      <button class="btn" data-testid="btn-1">操作按钮</button>
    </div>
    <div class="card" data-testid="card-2">
      <h3>卡片标题 2</h3>
      <p>卡片内容描述</p>
      <button class="btn" data-testid="btn-2">操作按钮</button>
    </div>
  </main>
  <aside class="detail-panel" data-testid="detail-panel">
    <div class="detail-item" data-testid="detail-item-1">详情项 1</div>
    <div class="detail-item" data-testid="detail-item-2">详情项 2</div>
    <div class="detail-item" data-testid="detail-item-3">详情项 3</div>
  </aside>
</div>
</body>
</html>"""

@pytest.fixture(scope="module")
def test_server():
    with tempfile.TemporaryDirectory() as tmpdir:
        html_path = Path(tmpdir) / "index.html"
        html_path.write_text(TEST_HTML, encoding="utf-8")
        original_dir = os.getcwd()
        os.chdir(tmpdir)
        server = HTTPServer(("localhost", 0), SimpleHTTPRequestHandler)
        port = server.server_address[1]
        thread = threading.Thread(target=server.serve_forever)
        thread.daemon = True
        thread.start()
        url = f"http://localhost:{port}/index.html"
        yield url
        server.shutdown()
        os.chdir(original_dir)


class TestDesktopLayout:
    def test_three_column_layout_exists(self, test_server):
        with sync_playwright() as p:
            browser = p.chromium.launch()
            page = browser.new_page(viewport={"width": 1280, "height": 800})
            page.goto(test_server, wait_until="networkidle")
            sidebar = page.locator("[data-testid='sidebar']")
            content = page.locator("[data-testid='content']")
            detail_panel = page.locator("[data-testid='detail-panel']")
            assert sidebar.is_visible()
            assert content.is_visible()
            assert detail_panel.is_visible()
            sidebar_box = sidebar.bounding_box()
            content_box = content.bounding_box()
            detail_box = detail_panel.bounding_box()
            assert sidebar_box["x"] < content_box["x"] < detail_box["x"]
            browser.close()

    def test_first_screen_load_within_2s(self, test_server):
        with sync_playwright() as p:
            browser = p.chromium.launch()
            page = browser.new_page(viewport={"width": 1280, "height": 800})
            start = time.time()
            page.goto(test_server, wait_until="networkidle")
            load_time = time.time() - start
            assert load_time < 2.0, f"首屏加载时间 {load_time:.2f}s 超过 2s 限制"
            browser.close()

    def test_interactive_elements_displayed(self, test_server):
        with sync_playwright() as p:
            browser = p.chromium.launch()
            page = browser.new_page(viewport={"width": 1280, "height": 800})
            page.goto(test_server, wait_until="networkidle")
            nav_items = page.locator("[data-testid^='nav-item-']")
            nav_count = nav_items.count()
            assert nav_count == 3, f"期望 3 个导航项, 实际 {nav_count}"
            btns = page.locator("[data-testid^='btn-']")
            btn_count = btns.count()
            assert btn_count == 2, f"期望 2 个操作按钮, 实际 {btn_count}"
            detail_items = page.locator("[data-testid^='detail-item-']")
            detail_count = detail_items.count()
            assert detail_count == 3, f"期望 3 个详情项, 实际 {detail_count}"
            all_interactive = page.locator("[data-testid^='nav-item-'], [data-testid^='btn-'], [data-testid^='detail-item-']")
            for i in range(all_interactive.count()):
                el = all_interactive.nth(i)
                assert el.is_visible(), f"交互元素 {i} 不可见"
                box = el.bounding_box()
                assert box["width"] > 0 and box["height"] > 0, f"交互元素 {i} 尺寸无效"
            browser.close()
