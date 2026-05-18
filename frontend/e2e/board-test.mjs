import { chromium } from 'playwright';

const BASE = 'http://localhost:5173';

async function main() {
  const browser = await chromium.launch({ headless: true });
  const context = await browser.newContext({ viewport: { width: 1280, height: 800 } });
  const page = await context.newPage();

  console.log('=== 1. Open app ===');
  await page.goto(BASE, { waitUntil: 'load', timeout: 10000 }).catch(() => {});
  await page.waitForTimeout(2000);
  console.log('Title:', await page.title());
  await page.screenshot({ path: '/tmp/e2e-01-landing.png' });

  console.log('\n=== 2. Register ===');
  await page.goto(`${BASE}/register`, { waitUntil: 'load', timeout: 10000 }).catch(() => {});
  await page.waitForTimeout(2000);
  const username = `testuser_${Date.now()}`;
  await page.fill('input[placeholder="用户名"]', username);
  await page.fill('input[placeholder="邮箱"]', `${username}@test.com`);
  await page.fill('input[placeholder="显示名称（可选）"]', '测试用户');
  await page.fill('input[placeholder="密码"]', 'Secret123');
  await page.fill('input[placeholder="确认密码"]', 'Secret123');
  // Capture errors
  page.on('console', msg => { if (msg.type() === 'error') console.log('  ERR:', msg.text()); });
  page.on('pageerror', err => console.log('  PAGE_ERR:', err.message));
  await page.click('button:has-text("注册")');
  await page.waitForTimeout(1500);
  // Wait for URL to change from /register
  for (let i = 0; i < 10; i++) {
    await page.waitForTimeout(500);
    const url = page.url();
    if (!url.includes('/register')) break;
  }
  await page.screenshot({ path: '/tmp/e2e-02-registered.png' });
  console.log('URL after register:', page.url());

  console.log('\n=== 3. Check board list ===');
  await page.waitForTimeout(2000);
  await page.screenshot({ path: '/tmp/e2e-03-boards.png' });
  const hasCreateBoardBtn = await page.locator('button:has-text("创建看板")').first().isVisible().catch(() => false);
  console.log('Create board button visible:', hasCreateBoardBtn);


  console.log('\n=== 4. Create a board ===');
  if (hasCreateBoardBtn) {
    await page.locator('button:has-text("创建看板")').first().click();
    await page.waitForTimeout(800);
    await page.screenshot({ path: '/tmp/e2e-04-dialog.png' });
    const dialog = page.locator('.el-dialog');
    if (await dialog.isVisible()) {
      await page.fill('.el-dialog input[placeholder="看板名称"]', '测试看板');
      await page.waitForTimeout(200);
      await dialog.locator('button:has-text("创建")').click();
      await page.waitForTimeout(3000);
      await page.screenshot({ path: '/tmp/e2e-04-board-created.png' });
      console.log('URL after board create:', page.url());
    }
  }

  console.log('\n=== 5. Check for task form ===');
  const hasAddTaskBtn = await page.locator('button:has-text("添加任务")').first().isVisible().catch(() => false);
  console.log('Add task button visible:', hasAddTaskBtn);

  if (hasAddTaskBtn) {
    await page.locator('button:has-text("添加任务")').first().click();
    await page.waitForTimeout(800);
    await page.screenshot({ path: '/tmp/e2e-05-task-form.png' });
    const formVisible = await page.locator('.el-dialog').last().isVisible().catch(() => false);
    console.log('Task form dialog visible:', formVisible);

    if (formVisible) {
      await page.locator('.el-dialog').last().locator('input[placeholder="任务标题"]').fill('测试任务');
      await page.locator('.el-dialog').last().locator('button:has-text("创建")').click();
      await page.waitForTimeout(1500);
      await page.screenshot({ path: '/tmp/e2e-06-task-created.png' });
      console.log('Task created!');
    }
  }

  console.log('\n=== 6. Check agent auto-assign button ===');
  const hasAgentBtn = await page.locator('button:has-text("Agent分配")').first().isVisible().catch(() => false);
  console.log('Agent分配 button visible:', hasAgentBtn);

  await page.screenshot({ path: '/tmp/e2e-07-final.png' });
  console.log('\nScreenshots saved to /tmp/e2e-*.png');

  await browser.close();
}

main().catch(err => {
  console.error('TEST FAILED:', err);
  process.exit(1);
});
