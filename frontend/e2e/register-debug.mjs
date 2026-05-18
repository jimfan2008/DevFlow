import { chromium } from 'playwright';

const BASE = 'http://localhost:5173';

async function main() {
  const browser = await chromium.launch({ headless: true });
  const page = await browser.newPage();
  page.on('console', msg => console.log('CONSOLE:', msg.type(), msg.text()));
  page.on('pageerror', err => console.log('ERROR:', err.message));
  page.on('response', resp => {
    if (resp.status() >= 400) console.log('HTTP', resp.status(), resp.url());
  });

  // Go to register
  await page.goto(`${BASE}/register`, { waitUntil: 'load', timeout: 10000 }).catch(() => {});
  await page.waitForTimeout(1500);

  console.log('After load URL:', page.url());

  const username = `r_${Date.now()}`;
  await page.fill('input[placeholder="用户名"]', username);
  await page.fill('input[placeholder="邮箱"]', `${username}@t.com`);
  await page.fill('input[placeholder="显示名称（可选）"]', 'RegTest');
  await page.fill('input[placeholder="密码"]', 'Secret123');
  await page.fill('input[placeholder="确认密码"]', 'Secret123');
  await page.waitForTimeout(300);

  console.log('Filled form, clicking register...');
  await page.click('button:has-text("注册")');
  await page.waitForTimeout(3000);

  console.log('After register URL:', page.url());
  const text = await page.locator('body').innerText();
  console.log('Body:', text.substring(0, 400));

  // Check if we are now in the app (logged in)
  const headerVisible = await page.locator('.app-header').isVisible().catch(() => false);
  console.log('Header visible:', headerVisible);
  const sidebarVisible = await page.locator('.app-sidebar').isVisible().catch(() => false);
  console.log('Sidebar visible:', sidebarVisible);

  await page.screenshot({ path: '/tmp/debug-reg-result.png' });
  await browser.close();
}

main().catch(err => { console.error('FAIL:', err.message); process.exit(1); });
