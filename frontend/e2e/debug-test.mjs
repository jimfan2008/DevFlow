import { chromium } from 'playwright';

const BASE = 'http://localhost:5173';

async function main() {
  const browser = await chromium.launch({ headless: true });
  const context = await browser.newContext({ viewport: { width: 1280, height: 800 } });
  const page = await context.newPage();

  // Capture console
  page.on('console', msg => console.log('CONSOLE:', msg.type(), msg.text()));
  page.on('pageerror', err => console.log('PAGE_ERROR:', err.message));

  console.log('\n=== 1. Go to register ===');
  await page.goto(`${BASE}/register`, { waitUntil: 'networkidle' });
  await page.waitForTimeout(500);
  const username = `u_${Date.now()}`;
  await page.fill('input[placeholder="用户名"]', username);
  await page.fill('input[placeholder="邮箱"]', `${username}@t.com`);
  await page.fill('input[placeholder="显示名称（可选）"]', 'Test');
  await page.fill('input[placeholder="密码"]', 'Secret123');
  await page.fill('input[placeholder="确认密码"]', 'Secret123');
  await page.screenshot({ path: '/tmp/debug-form-filled.png' });

  // Check if the submit button works
  const btn = page.locator('button:has-text("注册")');
  console.log('Register button enabled:', await btn.isEnabled());
  await btn.click();
  await page.waitForTimeout(3000);
  console.log('After register URL:', page.url());
  await page.screenshot({ path: '/tmp/debug-after-register.png' });

  // Check what's on the page
  const bodyText = await page.locator('body').innerText();
  console.log('Page text (first 300):', bodyText.substring(0, 300));

  console.log('\n=== 2. Go to boards ===');
  await page.goto(`${BASE}/boards`, { waitUntil: 'networkidle' });
  await page.waitForTimeout(1000);
  console.log('Boards URL:', page.url());
  await page.screenshot({ path: '/tmp/debug-boards.png' });

  const boardsBody = await page.locator('body').innerText();
  console.log('Boards text (first 300):', boardsBody.substring(0, 300));

  const createBtn = page.locator('button:has-text("创建看板")').first();
  console.log('Create button visible:', await createBtn.isVisible());

  if (await createBtn.isVisible()) {
    console.log('Clicking create...');
    await createBtn.click();
    await page.waitForTimeout(2000);
    await page.waitForTimeout(1000);
    await page.screenshot({ path: '/tmp/debug-create-dialog.png' });

    // Check if dialog opened
    const dialog = page.locator('.el-dialog');
    console.log('Dialog visible:', await dialog.isVisible());

    if (await dialog.isVisible()) {
      const dialogText = await dialog.innerText();
      console.log('Dialog text:', dialogText.substring(0, 200));

      // Find the name input in the dialog
      const nameInput = dialog.locator('input');
      console.log('Name input count:', await nameInput.count());

      await page.fill('.el-dialog input[placeholder="看板名称"]', '测试看板');
      await page.waitForTimeout(200);
      await dialog.locator('button:has-text("创建")').click();
      await page.waitForTimeout(3000);
      console.log('After create URL:', page.url());
      await page.screenshot({ path: '/tmp/debug-after-create.png' });

      const afterBody = await page.locator('body').innerText();
      console.log('After create text:', afterBody.substring(0, 300));
    }
  }

  console.log('\n=== 3. Check for add task on detail page ===');
  // Board creation should have navigated to board detail
  const addTask = page.locator('button:has-text("添加任务")').first();
  const addTaskVisible = await addTask.isVisible();
  console.log('Add task visible:', addTaskVisible);

  if (addTaskVisible) {
    console.log('Clicking add task...');
    await addTask.click();
    await page.waitForTimeout(1000);
    await page.screenshot({ path: '/tmp/debug-task-form.png' });

    const formDialog = page.locator('.el-dialog').last();
    const formVisible = await formDialog.isVisible();
    console.log('Task form dialog visible:', formVisible);

    if (formVisible) {
      await formDialog.locator('input[placeholder="任务标题"]').fill('测试任务-1');
      await formDialog.locator('button:has-text("创建")').click();
      await page.waitForTimeout(1500);
      await page.screenshot({ path: '/tmp/debug-task-created.png' });
      console.log('Task created!');

      // Check agent button in task form
      const agentBtn = formDialog.locator('button:has-text("Agent分配")');
      console.log('Agent assign button in form:', await agentBtn.isVisible());
    }
  }

  console.log('\n=== 4. Check agent on task detail page ===');
  // Navigate to task detail if exists
  const taskCards = page.locator('.kanban-card');
  const cardCount = await taskCards.count();
  console.log('Task cards on board:', cardCount);

  if (cardCount > 0) {
    await taskCards.first().click();
    await page.waitForTimeout(2000);
    await page.screenshot({ path: '/tmp/debug-task-detail.png' });

    const agentOnDetail = page.locator('button:has-text("Agent分配")');
    console.log('Agent assign on detail:', await agentOnDetail.isVisible());
  }

  await browser.close();
}

main().catch(err => {
  console.error('TEST FAILED:', err);
  process.exit(1);
});
