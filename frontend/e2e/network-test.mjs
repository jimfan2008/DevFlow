import { chromium } from 'playwright';

const BASE = 'http://localhost:5173';

async function main() {
  const browser = await chromium.launch({ headless: true });
  const page = await browser.newPage();

  // Track failed requests
  page.on('requestfailed', req => console.log('REQUEST FAILED:', req.url(), req.failure()?.errorText));
  // Track all responses with errors
  page.on('response', resp => {
    if (resp.status() >= 400) console.log('RESPONSE ERROR:', resp.status(), resp.url());
  });
  page.on('pageerror', err => console.log('PAGE_ERROR:', err.message));
  page.on('console', msg => {
    if (msg.type() === 'error') console.log('CONSOLE ERROR:', msg.text());
  });

  console.log('=== Go to Register ===');
  await page.goto(`${BASE}/register`, { waitUntil: 'networkidle' });

  const username = `n_${Date.now()}`;
  await page.fill('input[placeholder="用户名"]', username);
  await page.fill('input[placeholder="邮箱"]', `${username}@t.com`);
  await page.fill('input[placeholder="显示名称（可选）"]', 'NetTest');
  await page.fill('input[placeholder="密码"]', 'Secret123');
  await page.fill('input[placeholder="确认密码"]', 'Secret123');
  await page.waitForTimeout(200);

  console.log('Clicking register...');
  await page.click('button:has-text("注册")');
  await page.waitForTimeout(3000);

  console.log('URL after register:', page.url());
  const text = await page.locator('body').innerText();
  console.log('Body:', text.substring(0, 500));

  await page.screenshot({ path: '/tmp/net-after-register.png' });

  await browser.close();
}

main().catch(err => {
  console.error('FAILED:', err.message);
  process.exit(1);
});
