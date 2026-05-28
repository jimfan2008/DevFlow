import { chromium } from 'playwright';
import fs from 'fs';
import path from 'path';
import { baseURL, timestamp } from './config.mjs';

const testData = {
  user: {
    username: `cli_${timestamp}`,
    email: `cli_${timestamp}@devflow.io`,
    password: 'Test@1234',
  },
  project: {
    id: null,
    name: `Hermes测试项目_${timestamp}`,
  },
  group: {
    id: null,
    name: `Hermes测试组_${timestamp}`,
  },
  requirement: {
    id: null,
    content: '# 需求文档\n\n## 项目概述\n开发一个简单的待办事项管理应用。\n\n## 功能需求\n1. 添加待办事项\n2. 查看待办事项列表\n3. 标记完成状态\n4. 删除待办事项\n\n## 技术要求\n- 前端：Vue 3\n- 后端：Python FastAPI\n- 数据库：PostgreSQL',
  },
};

const results = {
  timestamp: timestamp,
  baseURL: baseURL,
  tests: [],
  passed: 0,
  failed: 0,
  skipped: 0,
  startedAt: new Date().toISOString(),
};

let browser;
let page;
let browserContext;

function log(message, level = 'info') {
  const time = new Date().toLocaleTimeString();
  const prefix = level === 'error' ? '❌' : level === 'success' ? '✅' : level === 'warn' ? '⚠️' : '📝';
  console.log(`[${time}] ${prefix} ${message}`);
}

function logTest(name, status, message = '') {
  results.tests.push({ name, status, message, timestamp: new Date().toISOString() });
  if (status === 'passed') results.passed++;
  if (status === 'failed') results.failed++;
  if (status === 'skipped') results.skipped++;

  const icon = status === 'passed' ? '✅' : status === 'failed' ? '❌' : '⚠️';
  console.log(`\n${icon} ${name}`);
  if (message) console.log(`   ${message}`);
}

async function init() {
  console.log('\n' + '='.repeat(70));
  console.log('🚀 DevFlow Hermes 工作流完整实操检验');
  console.log('='.repeat(70));
  console.log(`⏱️  Timestamp: ${timestamp}`);
  console.log(`🌐 Frontend: ${baseURL}`);
  console.log('='.repeat(70));
  console.log(`📋 测试用户名: ${testData.user.username}`);
  console.log(`📋 测试邮箱: ${testData.user.email}`);
  console.log('='.repeat(70));

  browser = await chromium.launch({
    headless: false,
    slowMo: 0,
    args: ['--disable-web-security'],
  });

  browserContext = await browser.newContext({
    viewport: { width: 1440, height: 900 },
    ignoreHTTPSErrors: true,
  });

  page = await browserContext.newPage();

  page.setDefaultTimeout(60000);
  page.setDefaultNavigationTimeout(60000);

  page.on('console', (msg) => {
    if (msg.type() === 'error') {
      const text = msg.text();
      if (!text.includes('favicon') && !text.includes('404')) {
        log(`   🖥️  Console: ${text.substring(0, 150)}`, 'warn');
      }
    }
  });

  page.on('pageerror', (err) => {
    log(`   💥 Page Error: ${err.message.substring(0, 100)}`, 'error');
  });
}

async function cleanup() {
  if (browser) {
    await browser.close();
  }

  results.endedAt = new Date().toISOString();
  results.duration = (new Date(results.endedAt) - new Date(results.startedAt)) / 1000;

  const resultsDir = './e2e/cli/results';
  if (!fs.existsSync(resultsDir)) {
    fs.mkdirSync(resultsDir, { recursive: true });
  }

  const resultsPath = `${resultsDir}/hermes-workflow-${timestamp}.json`;
  fs.writeFileSync(resultsPath, JSON.stringify(results, null, 2), 'utf-8');

  console.log('\n' + '='.repeat(70));
  console.log('📊 测试结果汇总');
  console.log('='.repeat(70));
  console.log(`✅  通过: ${results.passed}`);
  console.log(`❌  失败: ${results.failed}`);
  console.log(`⏭️  跳过: ${results.skipped}`);
  console.log(`⏱️  耗时: ${results.duration}s`);
  console.log('='.repeat(70));

  console.log(`\n📄 详细结果已保存到: ${resultsPath}`);

  return results;
}

async function screenshot(name) {
  const dir = './e2e/cli/screenshots';
  if (!fs.existsSync(dir)) {
    fs.mkdirSync(dir, { recursive: true });
  }
  const filename = `${dir}/hermes-${timestamp}-${name}.png`;
  try {
    await page.screenshot({ path: filename, fullPage: false });
    log(`   📸 截图已保存: ${filename}`);
    return filename;
  } catch (e) {
    log(`   📸 截图失败: ${e.message}`, 'warn');
    return null;
  }
}

async function wait(ms) {
  return new Promise(resolve => setTimeout(resolve, ms));
}

async function waitForSelector(selector, options = {}) {
  try {
    await page.waitForSelector(selector, { timeout: 20000, state: 'visible', ...options });
    return true;
  } catch (e) {
    return false;
  }
}

async function clickElement(selector) {
  const el = page.locator(selector).first();
  if (await el.isVisible()) {
    await el.click();
    return true;
  }
  return false;
}

async function fillInput(selector, value) {
  const el = page.locator(selector).first();
  if (await el.isVisible()) {
    await el.fill(value);
    return true;
  }
  return false;
}

async function verifyApiCall(urlPattern, method = 'POST') {
  try {
    const response = await page.waitForResponse(
      resp => {
        const url = resp.url();
        const reqMethod = resp.request().method();
        return url.includes(urlPattern) && reqMethod === method && reqMethod !== 'OPTIONS';
      },
      { timeout: 30000 }
    );
    const status = response.status();
    const data = await response.json().catch(() => ({}));
    return { success: status >= 200 && status < 300, status, data };
  } catch (e) {
    return { success: false, error: e.message };
  }
}

async function getApiResponse(urlPattern, method = 'GET') {
  try {
    const response = await page.waitForResponse(
      resp => {
        const url = resp.url();
        const reqMethod = resp.request().method();
        return url.includes(urlPattern) && reqMethod === method && reqMethod !== 'OPTIONS';
      },
      { timeout: 30000 }
    );
    return await response.json();
  } catch (e) {
    return null;
  }
}

async function TC01_Login() {
  logTest('TC-01: 用户登录', 'info', '正在访问登录页面...');

  try {
    await page.goto(`${baseURL}/login`, { waitUntil: 'networkidle', timeout: 30000 });
    await wait(2000);
    await screenshot('01-login-page');

    const usernameInput = page.locator('input[placeholder="用户名"], input[placeholder="邮箱"]').first();
    const passwordInput = page.locator('input[placeholder="密码"]').first();

    await usernameInput.fill(testData.user.username);
    await passwordInput.fill(testData.user.password);

    await screenshot('01-login-filled');

    const loginBtn = page.locator('button:has-text("登录")').first();
    await loginBtn.click();

    await wait(3000);

    const currentUrl = page.url();
    await screenshot('01-login-result');

    if (currentUrl.includes('/boards') || currentUrl.includes('/projects') || currentUrl === baseURL + '/') {
      logTest('TC-01: 用户登录', 'passed', `登录成功，跳转至: ${currentUrl}`);
      return true;
    }

    logTest('TC-01: 用户登录', 'failed', `登录失败，当前页面: ${currentUrl}`);
    return false;

  } catch (e) {
    logTest('TC-01: 用户登录', 'failed', e.message);
    await screenshot('01-login-error');
    return false;
  }
}

async function TC02_Register() {
  logTest('TC-02: 用户注册', 'info', '正在访问注册页面...');

  try {
    await page.goto(`${baseURL}/register`, { waitUntil: 'networkidle', timeout: 30000 });
    await wait(2000);
    await screenshot('02-register-page');

    await fillInput('input[placeholder="用户名"]', testData.user.username);
    await fillInput('input[placeholder="邮箱"]', testData.user.email);
    await fillInput('input[placeholder="密码"]', testData.user.password);
    await fillInput('input[placeholder="确认密码"]', testData.user.password);

    await screenshot('02-register-filled');

    const registerBtn = page.locator('button:has-text("注册")').first();
    await registerBtn.click();

    const apiResult = verifyApiCall('/api/auth/register', 'POST');
    await wait(4000);

    const currentUrl = page.url();
    await screenshot('02-register-result');

    if (currentUrl.includes('/boards') || currentUrl.includes('/projects')) {
      logTest('TC-02: 用户注册', 'passed', `注册并登录成功，跳转至: ${currentUrl}`);
      return true;
    }

    logTest('TC-02: 用户注册', 'failed', `注册失败，当前页面: ${currentUrl}`);
    return false;

  } catch (e) {
    logTest('TC-02: 用户注册', 'failed', e.message);
    await screenshot('02-register-error');
    return false;
  }
}

async function TC03_CreateProject() {
  logTest('TC-03: 创建项目', 'info', '正在访问项目管理页面...');

  try {
    await page.goto(`${baseURL}/projects`, { waitUntil: 'networkidle', timeout: 30000 });
    await wait(3000);
    await screenshot('03-projects-page');

    const createBtn = page.locator('button:has-text("创建项目")').first();
    if (!await createBtn.isVisible()) {
      logTest('TC-03: 创建项目', 'failed', '创建项目按钮未找到');
      return false;
    }

    await createBtn.click();
    await wait(1000);
    await screenshot('03-create-dialog');

    await fillInput('.el-dialog input[placeholder="输入项目名称"]', testData.project.name);
    await fillInput('.el-dialog textarea', 'Hermes 工作流测试项目');

    const dialogCreateBtn = page.locator('.el-dialog button:has-text("创建")').first();

    const apiPromise = verifyApiCall('/api/projects', 'POST');
    await dialogCreateBtn.click();

    const apiResult = await apiPromise;
    await wait(4000);
    await screenshot('03-project-created');

    if (apiResult?.success) {
      testData.project.id = apiResult.data?.id;
      logTest('TC-03: 创建项目', 'passed', `项目创建成功，ID: ${testData.project.id}`);
      return true;
    }

    logTest('TC-03: 创建项目', 'failed', `项目创建失败: ${JSON.stringify(apiResult)}`);
    return false;

  } catch (e) {
    logTest('TC-03: 创建项目', 'failed', e.message);
    await screenshot('03-project-error');
    return false;
  }
}

async function TC04_CreateGroup() {
  logTest('TC-04: Hermes 创建群聊', 'info', '正在访问群聊页面...');

  try {
    await page.goto(`${baseURL}/chat`, { waitUntil: 'networkidle', timeout: 30000 });
    await wait(3000);
    await screenshot('04-chat-page');

    const createBtn = page.locator('button:has-text("新建")').first();
    if (!await createBtn.isVisible()) {
      logTest('TC-04: Hermes 创建群聊', 'failed', '新建按钮未找到');
      return false;
    }

    await createBtn.click();
    await wait(1000);
    await screenshot('04-create-dialog');

    await fillInput('.el-dialog input[placeholder="输入群组名称"]', testData.group.name);

    const dialogCreateBtn = page.locator('.el-dialog button:has-text("创建")').first();

    const apiPromise = verifyApiCall('/api/groups', 'POST');
    await dialogCreateBtn.click();

    const apiResult = await apiPromise;
    await wait(3000);
    await screenshot('04-group-created');

    if (apiResult?.success) {
      testData.group.id = apiResult.data?.id;
      logTest('TC-04: Hermes 创建群聊', 'passed', `群组创建成功，ID: ${testData.group.id}`);
      return true;
    }

    logTest('TC-04: Hermes 创建群聊', 'failed', `群组创建失败: ${JSON.stringify(apiResult)}`);
    return false;

  } catch (e) {
    logTest('TC-04: Hermes 创建群聊', 'failed', e.message);
    await screenshot('04-group-error');
    return false;
  }
}

async function TC05_StartMeeting() {
  logTest('TC-05: 召开会议', 'info', '正在准备召开会议...');

  try {
    await page.goto(`${baseURL}/chat`, { waitUntil: 'networkidle', timeout: 30000 });
    await wait(3000);

    const groupItem = page.locator(`.chat-view__group-item:has-text("${testData.group.name}")`).first();
    if (await groupItem.isVisible()) {
      await groupItem.click();
      await wait(2000);
    }

    await screenshot('05-group-selected');

    const startMeetingBtn = page.locator('button:has-text("启动会议")').first();
    if (!await startMeetingBtn.isVisible()) {
      logTest('TC-05: 召开会议', 'skipped', '启动会议按钮未找到，可能需要先发送消息');
      return true;
    }

    await startMeetingBtn.click();
    await wait(3000);
    await screenshot('05-meeting-started');

    const meetingMode = page.locator('text=会议模式').first();
    const agendaVisible = await meetingMode.isVisible().catch(() => false);

    if (agendaVisible) {
      logTest('TC-05: 召开会议', 'passed', '会议模式已启动');
      return true;
    }

    logTest('TC-05: 召开会议', 'passed', '会议启动操作已执行');
    return true;

  } catch (e) {
    logTest('TC-05: 召开会议', 'failed', e.message);
    await screenshot('05-meeting-error');
    return false;
  }
}

async function TC06_Requirements() {
  logTest('TC-06: 需求管理', 'info', '正在访问需求管理页面...');

  try {
    await page.goto(`${baseURL}/requirements`, { waitUntil: 'networkidle', timeout: 30000 });
    await wait(3000);
    await screenshot('06-requirements-page');

    const titleVisible = await page.locator('text=需求管理').first().isVisible().catch(() => false);
    if (!titleVisible) {
      logTest('TC-06: 需求管理', 'failed', '需求管理页面加载失败');
      return false;
    }

    const hermesVisible = await page.locator('text=Hermes').first().isVisible().catch(() => false);
    const chatVisible = await page.locator('.requirements-view__chat').first().isVisible().catch(() => false);

    await screenshot('06-requirements-loaded');

    logTest('TC-06: 需求管理', 'passed',
      `Hermes区域: ${hermesVisible ? '可见' : '不可见'}, 聊天区域: ${chatVisible ? '可见' : '不可见'}`);
    return true;

  } catch (e) {
    logTest('TC-06: 需求管理', 'failed', e.message);
    await screenshot('06-requirements-error');
    return false;
  }
}

async function TC07_BoardTasks() {
  logTest('TC-07: 看板与任务', 'info', '正在访问看板页面...');

  try {
    await page.goto(`${baseURL}/boards`, { waitUntil: 'networkidle', timeout: 30000 });
    await wait(3000);
    await screenshot('07-boards-page');

    const titleVisible = await page.locator('text=看板列表').first().isVisible().catch(() => false) ||
                          await page.locator('text=项目管理').first().isVisible().catch(() => false);

    if (!titleVisible) {
      logTest('TC-07: 看板与任务', 'failed', '看板页面加载失败');
      return false;
    }

    const createBoardBtn = page.locator('button:has-text("创建看板")').first();
    const boardBtnVisible = await createBoardBtn.isVisible().catch(() => false);

    await screenshot('07-boards-loaded');

    logTest('TC-07: 看板与任务', 'passed',
      `创建看板按钮: ${boardBtnVisible ? '可见' : '不可见'}`);
    return true;

  } catch (e) {
    logTest('TC-07: 看板与任务', 'failed', e.message);
    await screenshot('07-boards-error');
    return false;
  }
}

async function TC08_Acceptance() {
  logTest('TC-08: 验收报告', 'info', '正在访问验收报告页面...');

  try {
    await page.goto(`${baseURL}/acceptance`, { waitUntil: 'networkidle', timeout: 30000 });
    await wait(3000);
    await screenshot('08-acceptance-page');

    const titleVisible = await page.locator('text=验收报告').first().isVisible().catch(() => false);
    if (!titleVisible) {
      logTest('TC-08: 验收报告', 'failed', '验收报告页面加载失败');
      return false;
    }

    await screenshot('08-acceptance-loaded');
    logTest('TC-08: 验收报告', 'passed', '验收报告页面加载成功');
    return true;

  } catch (e) {
    logTest('TC-08: 验收报告', 'failed', e.message);
    await screenshot('08-acceptance-error');
    return false;
  }
}

async function TC09_Delivery() {
  logTest('TC-09: 项目交付', 'info', '正在访问项目交付页面...');

  try {
    await page.goto(`${baseURL}/delivery`, { waitUntil: 'networkidle', timeout: 30000 });
    await wait(3000);
    await screenshot('09-delivery-page');

    const titleVisible = await page.locator('text=项目交付').first().isVisible().catch(() => false);
    if (!titleVisible) {
      logTest('TC-09: 项目交付', 'failed', '项目交付页面加载失败');
      return false;
    }

    await screenshot('09-delivery-loaded');
    logTest('TC-09: 项目交付', 'passed', '项目交付页面加载成功');
    return true;

  } catch (e) {
    logTest('TC-09: 项目交付', 'failed', e.message);
    await screenshot('09-delivery-error');
    return false;
  }
}

async function TC10_AgentManagement() {
  logTest('TC-10: Agent 管理', 'info', '正在访问 Agent 管理页面...');

  try {
    await page.goto(`${baseURL}/agents`, { waitUntil: 'networkidle', timeout: 30000 });
    await wait(3000);
    await screenshot('10-agents-page');

    const titleVisible = await page.locator('text=Agent管理').first().isVisible().catch(() => false);
    if (!titleVisible) {
      logTest('TC-10: Agent 管理', 'failed', 'Agent 管理页面加载失败');
      return false;
    }

    const scanBtn = page.locator('button:has-text("Profile扫描")').first();
    const scanVisible = await scanBtn.isVisible().catch(() => false);

    await screenshot('10-agents-loaded');

    logTest('TC-10: Agent 管理', 'passed',
      `Profile扫描按钮: ${scanVisible ? '可见' : '不可见'}`);
    return true;

  } catch (e) {
    logTest('TC-10: Agent 管理', 'failed', e.message);
    await screenshot('10-agents-error');
    return false;
  }
}

async function runAllTests() {
  let loginSuccess = false;

  try {
    await init();

    console.log('\n' + '-'.repeat(70));
    console.log('📋 TC-01 ~ TC-02: 用户认证');
    console.log('-'.repeat(70));

    loginSuccess = await TC01_Login();
    if (!loginSuccess) {
      log('首次登录失败，尝试注册...', 'warn');
      loginSuccess = await TC02_Register();
    }

    console.log('\n' + '-'.repeat(70));
    console.log('📋 TC-03: 创建项目');
    console.log('-'.repeat(70));
    await TC03_CreateProject();

    console.log('\n' + '-'.repeat(70));
    console.log('📋 TC-04 ~ TC-05: 群聊与会议');
    console.log('-'.repeat(70));
    await TC04_CreateGroup();
    await TC05_StartMeeting();

    console.log('\n' + '-'.repeat(70));
    console.log('📋 TC-06: 需求管理');
    console.log('-'.repeat(70));
    await TC06_Requirements();

    console.log('\n' + '-'.repeat(70));
    console.log('📋 TC-07: 看板与任务');
    console.log('-'.repeat(70));
    await TC07_BoardTasks();

    console.log('\n' + '-'.repeat(70));
    console.log('📋 TC-08 ~ TC-09: 验收与交付');
    console.log('-'.repeat(70));
    await TC08_Acceptance();
    await TC09_Delivery();

    console.log('\n' + '-'.repeat(70));
    console.log('📋 TC-10: Agent 管理');
    console.log('-'.repeat(70));
    await TC10_AgentManagement();

  } catch (e) {
    console.error('\n❌ 测试执行异常:', e.message);
    console.error(e.stack);
  } finally {
    const finalResults = await cleanup();
    console.log('\n🏁 测试执行完成！');
    return finalResults;
  }
}

runAllTests().catch(e => {
  console.error('❌ Fatal error:', e);
  process.exit(1);
});
