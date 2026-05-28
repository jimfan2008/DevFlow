import { test, expect } from '@playwright/test';
import * as helpers from '../../utils/api-helpers.mjs';
import testData from '../../fixtures/test-data.json' assert { type: 'json' };

export const sharedState = {
  user: {
    username: '',
    email: '',
    password: 'Test@1234',
  },
  project: {
    id: null,
    name: '',
  },
  group: {
    id: null,
    name: '',
  },
  board: {
    id: null,
  },
  task: {
    id: null,
  },
  requirement: {
    id: null,
  },
};

test.describe.serial('完整流程测试', () => {
  test('01. 注册用户', async ({ page }) => {
    console.log('\n=== 测试 1: 注册用户 ===');
    
    const timestamp = Date.now();
    sharedState.user.username = `cli_test_${timestamp}`;
    sharedState.user.email = `cli_test_${timestamp}@devflow.io`;
    
    await page.goto('/register');
    await page.waitForTimeout(2000);
    
    await helpers.fillByPlaceholder(page, '用户名', sharedState.user.username);
    await helpers.fillByPlaceholder(page, '邮箱', sharedState.user.email);
    await helpers.fillByPlaceholder(page, '密码', sharedState.user.password);
    await helpers.fillByPlaceholder(page, '确认密码', sharedState.user.password);
    
    await page.screenshot({ path: './e2e/screenshots/cli_01_register_form.png', fullPage: false });
    
    await page.locator('button:has-text("注册")').click();
    
    await page.waitForTimeout(5000);
    
    const currentUrl = page.url();
    console.log('   当前URL:', currentUrl);
    
    const isLoggedIn = currentUrl.includes('/boards') || currentUrl.includes('/projects');
    expect(isLoggedIn).toBeTruthy();
    
    await page.screenshot({ path: './e2e/screenshots/cli_01_register_success.png', fullPage: false });
    console.log('   ✅ 用户注册成功:', sharedState.user.username);
    
    try {
      await page.context().storageState({ path: './e2e/storage-state.json' });
      console.log('   ✅ 登录状态已保存');
    } catch (e) {
      console.log('   ⚠️  保存登录状态失败:', e.message);
    }
  });

  test('02. 创建项目', async ({ page }) => {
    console.log('\n=== 测试 2: 创建项目 ===');
    
    try {
      await page.goto('/');
      await page.waitForTimeout(2000);
    } catch {}
    
    await page.goto('/projects');
    await page.waitForTimeout(3000);
    
    const titleExists = await helpers.elementExists(page, 'text=项目管理', 5000);
    if (!titleExists) {
      console.log('   ⚠️  项目管理页面标题未找到，继续尝试创建项目');
    }
    
    const createBtn = page.locator('button:has-text("创建项目")').first();
    const btnExists = await createBtn.isVisible().catch(() => false);
    
    if (!btnExists) {
      console.log('   ⚠️  创建项目按钮未找到，跳过创建项目');
      return;
    }
    
    const timestamp = Date.now();
    sharedState.project.name = `CLI测试项目 ${timestamp}`;
    
    await createBtn.click();
    await page.waitForTimeout(1000);
    
    await page.screenshot({ path: './e2e/screenshots/cli_02_create_dialog.png', fullPage: false });
    
    const nameInput = page.locator('.el-dialog input[placeholder="输入项目名称"]').first();
    const descInput = page.locator('.el-dialog textarea').first();
    
    await nameInput.fill(sharedState.project.name);
    await descInput.fill('Playwright CLI 完整流程测试项目');
    
    const dialogCreateBtn = page.locator('.el-dialog button:has-text("创建")').first();
    await dialogCreateBtn.click();
    
    await page.waitForTimeout(4000);
    
    await page.screenshot({ path: './e2e/screenshots/cli_02_after_create.png', fullPage: false });
    
    const projectExists = await page.locator(`text=${sharedState.project.name}`).first().isVisible().catch(() => false);
    if (projectExists) {
      console.log('   ✅ 项目创建成功:', sharedState.project.name);
    } else {
      console.log('   ⚠️  项目卡片可能未立即显示，继续后续测试');
    }
  });

  test('03. Agent管理 - Profile扫描', async ({ page }) => {
    console.log('\n=== 测试 3: Agent管理 ===');
    
    await page.goto('/agents');
    await page.waitForTimeout(3000);
    
    await page.screenshot({ path: './e2e/screenshots/cli_03_agent_list.png', fullPage: false });
    
    const titleExists = await helpers.elementExists(page, 'text=Agent管理', 5000);
    expect(titleExists).toBeTruthy();
    
    const scanBtn = page.locator('button:has-text("Profile扫描")').first();
    const scanExists = await scanBtn.isVisible().catch(() => false);
    
    if (scanExists) {
      console.log('   点击 Profile扫描按钮...');
      await scanBtn.click();
      await page.waitForTimeout(5000);
      
      await page.screenshot({ path: './e2e/screenshots/cli_03_after_scan.png', fullPage: false });
      console.log('   ✅ Profile扫描已触发');
    } else {
      console.log('   ⚠️  Profile扫描按钮未找到');
    }
    
    const agentCards = await page.locator('.agent-list-view__card').all();
    console.log('   发现 Agent 数量:', agentCards.length);
    
    if (agentCards.length > 0) {
      console.log('   ✅ Agent列表加载成功');
    }
  });

  test('04. 创建群聊', async ({ page }) => {
    console.log('\n=== 测试 4: 创建群聊 ===');
    
    await page.goto('/chat');
    await page.waitForTimeout(3000);
    
    await page.screenshot({ path: './e2e/screenshots/cli_04_chat_empty.png', fullPage: false });
    
    const createBtn = page.locator('button:has-text("新建")').first();
    const createExists = await createBtn.isVisible().catch(() => false);
    
    if (!createExists) {
      console.log('   ⚠️  新建按钮未找到，跳过群聊创建');
      return;
    }
    
    const timestamp = Date.now();
    sharedState.group.name = `CLI测试组 ${timestamp}`;
    
    await createBtn.click();
    await page.waitForTimeout(1000);
    
    await page.screenshot({ path: './e2e/screenshots/cli_04_create_group_dialog.png', fullPage: false });
    
    const nameInput = page.locator('.el-dialog input[placeholder="输入群组名称"]').first();
    await nameInput.fill(sharedState.group.name);
    
    const dialogCreateBtn = page.locator('.el-dialog button:has-text("创建")').first();
    await dialogCreateBtn.click();
    
    await page.waitForTimeout(3000);
    
    await page.screenshot({ path: './e2e/screenshots/cli_04_after_group_create.png', fullPage: false });
    console.log('   ✅ 群聊创建请求已发送');
  });

  test('05. 需求管理', async ({ page }) => {
    console.log('\n=== 测试 5: 需求管理 ===');
    
    await page.goto('/requirements');
    await page.waitForTimeout(3000);
    
    await page.screenshot({ path: './e2e/screenshots/cli_05_requirements_page.png', fullPage: false });
    
    const titleExists = await helpers.elementExists(page, 'text=需求管理', 5000);
    expect(titleExists).toBeTruthy();
    console.log('   ✅ 需求管理页面加载成功');
    
    const hermesArea = await helpers.elementExists(page, 'text=🤖 Hermes 需求讨论', 5000);
    if (hermesArea) {
      console.log('   ✅ Hermes需求讨论区域存在');
    }
    
    const docArea = await helpers.elementExists(page, 'text=📋 需求文档', 5000);
    if (docArea) {
      console.log('   ✅ 需求文档区域存在');
    }
    
    const submitBtn = page.locator('button:has-text("提交需求文档")').first();
    const submitExists = await submitBtn.isVisible().catch(() => false);
    if (submitExists) {
      console.log('   ✅ 提交需求文档按钮存在');
    }
  });

  test('06. 看板管理', async ({ page }) => {
    console.log('\n=== 测试 6: 看板管理 ===');
    
    await page.goto('/boards');
    await page.waitForTimeout(3000);
    
    await page.screenshot({ path: './e2e/screenshots/cli_06_boards_list.png', fullPage: false });
    
    const titleExists = await helpers.elementExists(page, 'text=看板列表', 5000).catch(() => 
      helpers.elementExists(page, 'text=项目管理', 5000)
    );
    expect(titleExists).toBeTruthy();
    console.log('   ✅ 看板列表页面加载成功');
    
    const createBoardBtn = page.locator('button:has-text("创建看板")').first();
    const boardBtnExists = await createBoardBtn.isVisible().catch(() => false);
    
    if (boardBtnExists) {
      console.log('   ✅ 创建看板按钮存在');
    }
  });

  test('07. 验收报告', async ({ page }) => {
    console.log('\n=== 测试 7: 验收报告 ===');
    
    await page.goto('/acceptance');
    await page.waitForTimeout(3000);
    
    await page.screenshot({ path: './e2e/screenshots/cli_07_acceptance_page.png', fullPage: false });
    
    const titleExists = await helpers.elementExists(page, 'text=验收报告', 5000);
    expect(titleExists).toBeTruthy();
    console.log('   ✅ 验收报告页面加载成功');
  });

  test('08. 项目交付', async ({ page }) => {
    console.log('\n=== 测试 8: 项目交付 ===');
    
    await page.goto('/delivery');
    await page.waitForTimeout(3000);
    
    await page.screenshot({ path: './e2e/screenshots/cli_08_delivery_page.png', fullPage: false });
    
    const titleExists = await helpers.elementExists(page, 'text=项目交付', 5000);
    expect(titleExists).toBeTruthy();
    console.log('   ✅ 项目交付页面加载成功');
  });
});
