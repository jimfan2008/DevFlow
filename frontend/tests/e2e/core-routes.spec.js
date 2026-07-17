import { test, expect } from '@playwright/test';

/**
 * 核心页面路由可访问测试
 *
 * 验收标准：
 *   1. 所有路由返回 HTTP 200
 *   2. 首屏加载时间 ≤ 2 秒
 *   3. 路由切换时间 ≤ 300 ms
 */

// ============================================================
// 公开路由（无需认证）
// ============================================================
const PUBLIC_ROUTES = [
  { path: '/login',       name: '登录' },
  { path: '/register',    name: '注册' },
];

// ============================================================
// 需认证路由（通过 localStorage 注入假 token 绕过守卫）
// ============================================================
const AUTH_ROUTES = [
  { path: '/projects',          name: '项目管理' },
  { path: '/projects/1',        name: '项目详情' },
  { path: '/agents',            name: 'Agent 管理' },
  { path: '/agents/1',          name: 'Agent 详情' },
  { path: '/skills',            name: 'Skill 管理' },
  { path: '/chat',              name: '群聊与会议' },
  { path: '/boards',            name: '看板列表' },
  { path: '/boards/1',          name: '看板详情' },
  { path: '/boards/1/tasks/1',  name: '任务详情' },
  { path: '/task-board',        name: '任务看板' },
  { path: '/repos',             name: '代码仓库' },
  { path: '/acceptance',        name: '验收报告' },
  { path: '/notifications',     name: '通知中心' },
  { path: '/delivery',          name: '项目交付' },
  { path: '/requirements',      name: '需求管理' },
  { path: '/profile',           name: '个人资料' },
  { path: '/step1/1',           name: '第一步' },
  { path: '/step2/1',           name: '第二步' },
  { path: '/step3/1',           name: '第三步' },
  { path: '/step3/1/qa',        name: '第三步 QA' },
  { path: '/step4/1',           name: '第四步' },
  { path: '/step5/1',           name: '第五步' },
  { path: '/step6/1',           name: '第六步' },
  { path: '/step7/1',           name: '第七步' },
  { path: '/step8/1',           name: '第八步' },
  { path: '/step9/1',           name: '第九步' },
  { path: '/step10/1',          name: '第十步' },
  { path: '/step11/1',          name: '第十一步' },
  { path: '/step12/1',          name: '第十二步' },
  { path: '/step13/1',          name: '第十三步' },
  { path: '/step14/1',          name: '第十四步' },
  { path: '/step15/1',          name: '第十五步' },
  { path: '/step16/1',          name: '第十六步' },
];

const FIRST_SCREEN_TIMEOUT = 2000;
const ROUTE_SWITCH_TIMEOUT = 300;

// 注入假 token 到 localStorage
async function injectMockToken(page) {
  await page.evaluate(() => {
    localStorage.setItem('access_token', 'mock-token-for-routing-test');
    localStorage.setItem('refresh_token', 'mock-refresh-for-routing-test');
  });
}

// 清除 localStorage 中的 token
async function clearTokens(page) {
  await page.evaluate(() => {
    localStorage.removeItem('access_token');
    localStorage.removeItem('refresh_token');
  });
}

// ============================================================
// 公开路由可访问
// ============================================================
test.describe('公开路由可访问', () => {
  for (const route of PUBLIC_ROUTES) {
    test(`[${route.name}] ${route.path} 返回 200 且首屏 ≤ 2s`, async ({ page }) => {
      await clearTokens(page);

      const startTime = performance.now();
      const response = await page.goto(route.path);
      const loadTime = performance.now() - startTime;

      expect(response?.status()).toBe(200);
      expect(loadTime).toBeLessThanOrEqual(FIRST_SCREEN_TIMEOUT);

      const title = await page.title();
      expect(title).toContain('DevFlow');
    });
  }
});

// ============================================================
// 根路径重定向
// ============================================================
test.describe('根路径重定向', () => {
  test('/ 未登录时最终到达 /login', async ({ page }) => {
    await clearTokens(page);
    await page.goto('/');
    await page.waitForTimeout(800);

    const url = page.url();
    expect(url).toContain('/login');
  });

  test('/ 已登录时重定向到 /projects', async ({ page }) => {
    await injectMockToken(page);
    await page.goto('/');
    await page.waitForTimeout(500);
    await page.reload();
    await page.waitForTimeout(500);

    const url = page.url();
    expect(url).toContain('/projects');
  });
});

// ============================================================
// 需认证路由可访问
// ============================================================
test.describe('需认证路由可访问', () => {
  for (const route of AUTH_ROUTES) {
    test(`[${route.name}] ${route.path} 可访问`, async ({ page }) => {
      await injectMockToken(page);
      await page.goto('/');
      await page.waitForTimeout(300);

      const response = await page.goto(route.path);
      expect(response?.status()).toBe(200);

      const url = page.url();
      expect(url).toContain(route.path);
    });
  }
});

// ============================================================
// 404 页面
// ============================================================
test.describe('404 页面', () => {
  test('未知路径显示 404', async ({ page }) => {
    const response = await page.goto('/this/page/does/not/exist');
    expect(response?.status()).toBe(200);

    const title = await page.title();
    expect(title.includes('404') || title.includes('页面不存在')).toBe(true);
  });
});

// ============================================================
// 路由切换性能
// ============================================================
test.describe('路由切换性能', () => {
  test('公开路由间切换 ≤ 300ms', async ({ page }) => {
    await clearTokens(page);
    await page.goto('/login');
    await page.waitForTimeout(500);

    const start = performance.now();
    await page.goto('/register');
    await page.waitForLoadState('domcontentloaded');
    const switchTime = performance.now() - start;

    expect(switchTime).toBeLessThanOrEqual(ROUTE_SWITCH_TIMEOUT);
  });

  test('认证路由间切换 ≤ 300ms', async ({ page }) => {
    await injectMockToken(page);
    await page.goto('/');
    await page.waitForTimeout(300);

    await page.goto('/projects');
    await page.waitForLoadState('domcontentloaded');
    await page.waitForTimeout(500);

    const start = performance.now();
    await page.goto('/agents');
    await page.waitForLoadState('domcontentloaded');
    const switchTime = performance.now() - start;

    expect(switchTime).toBeLessThanOrEqual(ROUTE_SWITCH_TIMEOUT);
  });
});
