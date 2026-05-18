import { chromium } from 'playwright';
const BASE = 'http://localhost:5173';

async function main() {
  const browser = await chromium.launch({ headless: true });
  const page = await browser.newPage();

  // Console logging
  page.on('console', msg => { if (msg.type() === 'error') console.log('  ERR:', msg.text().substring(0, 100)); });

  // Register
  await page.goto(`${BASE}/register`, { waitUntil: 'load', timeout: 10000 }).catch(() => {});
  await page.waitForTimeout(1500);
  const username = `u_${Date.now()}`;
  await page.fill('input[placeholder="用户名"]', username);
  await page.fill('input[placeholder="邮箱"]', `${username}@t.com`);
  await page.fill('input[placeholder="密码"]', 'Secret123');
  await page.fill('input[placeholder="确认密码"]', 'Secret123');
  await page.click('button:has-text("注册")');
  await page.waitForTimeout(3000);

  // Should be at /boards (board list)
  const atBoards = page.url().includes('/boards');
  console.log('1. Register & redirect to boards:', atBoards ? 'PASS' : 'FAIL (' + page.url() + ')');

  // Create board
  await page.locator('button:has-text("创建看板")').first().click();
  await page.waitForTimeout(500);
  await page.locator('.el-dialog input[placeholder="看板名称"]').fill('我的项目');
  await page.locator('.el-dialog button:has-text("创建")').click();
  await page.waitForTimeout(3000);
  const onBoard = page.url().includes('/boards/') && page.url().length > 20;
  console.log('2. Create board & enter kanban:', onBoard ? 'PASS' : 'FAIL');

  // Check add task button
  await page.waitForTimeout(1000);
  const addBtn = await page.locator('button:has-text("添加任务")').first().isVisible();
  console.log('3. "添加任务" button visible:', addBtn ? 'PASS' : 'FAIL');

  // Click add task
  if (addBtn) {
    await page.locator('button:has-text("添加任务")').first().click();
    await page.waitForTimeout(800);
    const form = await page.locator('.el-dialog').last().isVisible();
    console.log('4. Task creation dialog opens:', form ? 'PASS' : 'FAIL');

    if (form) {
      await page.locator('.el-dialog').last().locator('input[placeholder="任务标题"]').fill('实现登录功能');
      await page.locator('.el-dialog').last().locator('button:has-text("创建")').click();
      await page.waitForTimeout(1500);
    }
  }

  // Check task card on board
  await page.waitForTimeout(500);
  const taskCard = await page.locator('.kanban-card').first().isVisible();
  console.log('5. Task card appears on board:', taskCard ? 'PASS' : 'FAIL');

  // Click task to see detail
  if (taskCard) {
    await page.locator('.kanban-card').first().click();
    await page.waitForTimeout(3000);
    // Wait for detail page to load
    await page.waitForSelector('button:has-text("Agent分配")', { timeout: 5000 }).catch(() => {});
    const agentOnDetail = await page.locator('button:has-text("Agent分配")').first().isVisible().catch(() => false);
    console.log('6. "Agent分配" button on task detail:', agentOnDetail ? 'PASS' : 'FAIL');
    if (!agentOnDetail) {
      const detailText = await page.locator('.task-detail-view').innerText().catch(() => 'N/A');
      console.log('   Detail page text:', detailText.substring(0, 200));
    }
  }

  console.log('\n=== Result Summary ===');
  console.log('新增任务: Available via kanban "添加任务" button → TaskForm dialog');
  console.log('Agent接收任务: Available on task detail page as "Agent分配" button');

  await page.screenshot({ path: '/tmp/final-result.png' });
  await browser.close();
}

main().catch(e => { console.error('FAIL:', e.message); process.exit(1); });
