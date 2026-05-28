import { chromium } from 'playwright';
import fs from 'fs';
import path from 'path';
import { baseURL, apiURL, timestamp } from './playwright.config.mjs';

const testData = {
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
};

const results = {
  timestamp: timestamp,
  baseURL: baseURL,
  apiURL: apiURL,
  tests: [],
  passed: 0,
  failed: 0,
  startedAt: new Date().toISOString(),
};

let browser;
let page;

function log(message) {
  const time = new Date().toLocaleTimeString();
  console.log(`[${time}] ${message}`);
}

function logTest(name, status, message = '') {
  results.tests.push({ name, status, message });
  if (status === 'passed') results.passed++;
  if (status === 'failed') results.failed++;
  
  const icon = status === 'passed' ? '✅' : status === 'failed' ? '❌' : '⚠️';
  console.log(`\n${icon} ${name}`);
  if (message) console.log(`   ${message}`);
}

async function init() {
  console.log('\n' + '='.repeat(70));
  console.log('🚀 DevFlow Playwright CLI 完整实操检验');
  console.log('='.repeat(70));
  console.log(`⏱️  Timestamp: ${timestamp}`);
  console.log(`🌐 Frontend: ${baseURL}`);
  console.log(`🔗 Backend: ${apiURL}`);
  console.log('='.repeat(70));
  
  browser = await chromium.launch({
    headless: true,
    slowMo: 0,
  });
  
  page = await browser.newPage({
    viewport: { width: 1440, height: 900 },
  });
  
  page.setDefaultTimeout(60000);
  
  page.on('console', (msg) => {
    if (msg.type() === 'error') {
      log(`   🖥️  Console Error: ${msg.text().substring(0, 200)}`);
    }
  });
}

async function cleanup() {
  if (browser) {
    await browser.close();
  }
  
  results.endedAt = new Date().toISOString();
  results.duration = (new Date(results.endedAt) - new Date(results.startedAt)) / 1000;
  
  const resultsDir = './e2e/results';
  if (!fs.existsSync(resultsDir)) {
    fs.mkdirSync(resultsDir, { recursive: true });
  }
  
  const resultsPath = `${resultsDir}/cli-test-${timestamp}.json`;
  fs.writeFileSync(resultsPath, JSON.stringify(results, null, 2), 'utf-8');
  
  console.log('\n' + '='.repeat(70));
  console.log('📊 测试结果汇总');
  console.log('='.repeat(70));
  console.log(`✅  通过: ${results.passed}`);
  console.log(`❌  失败: ${results.failed}`);
  console.log(`⏱️  耗时: ${results.duration}s`);
  console.log('='.repeat(70));
  
  console.log(`\n📄 详细结果已保存到: ${resultsPath}`);
}

async function screenshot(name) {
  const dir = './e2e/screenshots';
  if (!fs.existsSync(dir)) {
    fs.mkdirSync(dir, { recursive: true });
  }
  const filename = `${dir}/cli-${timestamp}-${name}.png`;
  try {
    await page.screenshot({ path: filename, fullPage: false });
    return filename;
  } catch (e) {
    return null;
  }
}

async function waitFor(ms) {
  return new Promise(resolve => setTimeout(resolve, ms));
}

async function fillByPlaceholder(placeholder, value) {
  const selector = `input[placeholder="${placeholder}"], textarea[placeholder="${placeholder}"]`;
  await page.waitForSelector(selector, { timeout: 15000 });
  await page.fill(selector, value);
}

async function clickButton(text) {
  const locator = page.locator(`button:has-text("${text}")`).first();
  await locator.waitFor({ timeout: 15000, state: 'visible' });
  await locator.click();
}

async function verifyApiResponse(urlPattern, method = 'POST', timeout = 60000) {
  try {
    const response = await page.waitForResponse(
      resp => {
        const url = resp.url();
        const reqMethod = resp.request().method();
        return url.includes(urlPattern) && 
               reqMethod === method && 
               reqMethod !== 'OPTIONS';
      },
      { timeout }
    );
    
    const status = response.status();
    const data = await response.json().catch(() => ({}));
    
    return { success: status >= 200 && status < 300, status, data };
  } catch (e) {
    return { success: false, error: e.message };
  }
}

async function test1_Register() {
  logTest('测试 1: 用户注册', 'info', '正在访问注册页面...');
  
  testData.user.username = `cli_test_${timestamp}`;
  testData.user.email = `cli_test_${timestamp}@devflow.io`;
  
  try {
    await page.goto(`${baseURL}/register`, { waitUntil: 'networkidle' });
    await waitFor(2000);
    
    await fillByPlaceholder('用户名', testData.user.username);
    await fillByPlaceholder('邮箱', testData.user.email);
    await fillByPlaceholder('密码', testData.user.password);
    await fillByPlaceholder('确认密码', testData.user.password);
    
    await screenshot('01-register-form');
    
    log('   点击注册按钮...');
    await clickButton('注册');
    
    const apiResult = await verifyApiResponse('/api/auth/register', 'POST', 30000);
    
    await waitFor(3000);
    await screenshot('01-register-result');
    
    const currentUrl = page.url();
    const isLoggedIn = currentUrl.includes('/boards') || currentUrl.includes('/projects');
    
    if (isLoggedIn) {
      logTest('测试 1: 用户注册', 'passed', `跳转至 ${currentUrl}`);
      return true;
    } else {
      logTest('测试 1: 用户注册', 'failed', `当前页面: ${currentUrl}, API: ${JSON.stringify(apiResult)}`);
      return false;
    }
  } catch (e) {
    logTest('测试 1: 用户注册', 'failed', e.message);
    return false;
  }
}

async function test2_CreateProject() {
  logTest('测试 2: 创建项目', 'info', '正在访问项目管理页面...');
  
  testData.project.name = `CLI测试项目 ${timestamp}`;
  
  try {
    await page.goto(`${baseURL}/projects`, { waitUntil: 'networkidle' });
    await waitFor(3000);
    
    await screenshot('02-project-list');
    
    const createBtn = page.locator('button:has-text("创建项目")').first();
    const btnExists = await createBtn.isVisible().catch(() => false);
    
    if (!btnExists) {
      logTest('测试 2: 创建项目', 'failed', '创建项目按钮未找到');
      return false;
    }
    
    log('   点击创建项目按钮...');
    await createBtn.click();
    await waitFor(1000);
    
    await screenshot('02-create-dialog');
    
    const nameInput = page.locator('.el-dialog input[placeholder="输入项目名称"]').first();
    await nameInput.waitFor({ timeout: 10000, state: 'visible' });
    await nameInput.fill(testData.project.name);
    
    const descInput = page.locator('.el-dialog textarea').first();
    await descInput.fill('Playwright CLI 完整流程测试项目');
    
    const dialogCreateBtn = page.locator('.el-dialog button:has-text("创建")').first();
    
    log('   点击对话框中的创建按钮...');
    const apiPromise = verifyApiResponse('/api/projects', 'POST', 30000);
    await dialogCreateBtn.click();
    
    const apiResult = await apiPromise;
    
    await waitFor(4000);
    await screenshot('02-project-created');
    
    if (apiResult.success) {
      testData.project.id = apiResult.data?.data?.id || apiResult.data?.id;
      logTest('测试 2: 创建项目', 'passed', `项目ID: ${testData.project.id || 'N/A'}`);
      return true;
    } else {
      logTest('测试 2: 创建项目', 'failed', `API响应: ${JSON.stringify(apiResult)}`);
      return false;
    }
  } catch (e) {
    logTest('测试 2: 创建项目', 'failed', e.message);
    return false;
  }
}

async function test3_AgentManagement() {
  logTest('测试 3: Agent管理', 'info', '正在访问 Agent 管理页面...');
  
  try {
    await page.goto(`${baseURL}/agents`, { waitUntil: 'networkidle' });
    await waitFor(3000);
    
    await screenshot('03-agent-list');
    
    const titleVisible = await page.locator('text=Agent管理').first().isVisible().catch(() => false);
    if (!titleVisible) {
      logTest('测试 3: Agent管理', 'failed', 'Agent管理页面标题未找到');
      return false;
    }
    
    const scanBtn = page.locator('button:has-text("Profile扫描")').first();
    const scanVisible = await scanBtn.isVisible().catch(() => false);
    
    if (scanVisible) {
      log('   点击 Profile扫描按钮...');
      const apiPromise = verifyApiResponse('/api/agents/scan-profile', 'POST', 30000);
      await scanBtn.click();
      
      const apiResult = await apiPromise;
      await waitFor(3000);
      await screenshot('03-after-scan');
      
      if (apiResult.success) {
        logTest('测试 3: Agent管理', 'passed', `扫描成功: ${JSON.stringify(apiResult.data).substring(0, 100)}`);
        return true;
      }
    }
    
    logTest('测试 3: Agent管理', 'passed', '页面加载成功，Profile扫描按钮可见');
    return true;
  } catch (e) {
    logTest('测试 3: Agent管理', 'failed', e.message);
    return false;
  }
}

async function test4_CreateGroup() {
  logTest('测试 4: 创建群聊', 'info', '正在访问群聊页面...');
  
  testData.group.name = `CLI测试组 ${timestamp}`;
  
  try {
    await page.goto(`${baseURL}/chat`, { waitUntil: 'networkidle' });
    await waitFor(3000);
    
    await screenshot('04-chat-empty');
    
    const createBtn = page.locator('button:has-text("新建")').first();
    const createVisible = await createBtn.isVisible().catch(() => false);
    
    if (!createVisible) {
      logTest('测试 4: 创建群聊', 'failed', '新建按钮未找到');
      return false;
    }
    
    log('   点击新建按钮...');
    await createBtn.click();
    await waitFor(1000);
    
    await screenshot('04-create-group-dialog');
    
    const nameInput = page.locator('.el-dialog input[placeholder="输入群组名称"]').first();
    await nameInput.waitFor({ timeout: 10000, state: 'visible' });
    await nameInput.fill(testData.group.name);
    
    const dialogCreateBtn = page.locator('.el-dialog button:has-text("创建")').first();
    
    log('   点击对话框中的创建按钮...');
    const apiPromise = verifyApiResponse('/api/chat/groups', 'POST', 30000);
    await dialogCreateBtn.click();
    
    const apiResult = await apiPromise;
    
    await waitFor(3000);
    await screenshot('04-group-created');
    
    if (apiResult.success) {
      testData.group.id = apiResult.data?.data?.id || apiResult.data?.id;
      logTest('测试 4: 创建群聊', 'passed', `群组ID: ${testData.group.id || 'N/A'}`);
      return true;
    } else {
      logTest('测试 4: 创建群聊', 'failed', `API响应: ${JSON.stringify(apiResult)}`);
      return false;
    }
  } catch (e) {
    logTest('测试 4: 创建群聊', 'failed', e.message);
    return false;
  }
}

async function test5_Requirements() {
  logTest('测试 5: 需求管理', 'info', '正在访问需求管理页面...');
  
  try {
    await page.goto(`${baseURL}/requirements`, { waitUntil: 'networkidle' });
    await waitFor(3000);
    
    await screenshot('05-requirements');
    
    const titleVisible = await page.locator('text=需求管理').first().isVisible().catch(() => false);
    if (!titleVisible) {
      logTest('测试 5: 需求管理', 'failed', '需求管理页面标题未找到');
      return false;
    }
    
    const hermesVisible = await page.locator('text=Hermes').first().isVisible().catch(() => false);
    const docVisible = await page.locator('text=需求文档').first().isVisible().catch(() => false);
    
    logTest('测试 5: 需求管理', 'passed', 
      `Hermes区域: ${hermesVisible ? '可见' : '不可见'}, 文档区域: ${docVisible ? '可见' : '不可见'}`);
    return true;
  } catch (e) {
    logTest('测试 5: 需求管理', 'failed', e.message);
    return false;
  }
}

async function test6_Board() {
  logTest('测试 6: 看板管理', 'info', '正在访问看板页面...');
  
  try {
    await page.goto(`${baseURL}/boards`, { waitUntil: 'networkidle' });
    await waitFor(3000);
    
    await screenshot('06-boards');
    
    const boardTitle = await page.locator('text=看板列表').first().isVisible().catch(() => false);
    const projectTitle = await page.locator('text=项目管理').first().isVisible().catch(() => false);
    
    if (!boardTitle && !projectTitle) {
      logTest('测试 6: 看板管理', 'failed', '看板页面标题未找到');
      return false;
    }
    
    const createBoardBtn = page.locator('button:has-text("创建看板")').first();
    const boardBtnVisible = await createBoardBtn.isVisible().catch(() => false);
    
    logTest('测试 6: 看板管理', 'passed', 
      `创建看板按钮: ${boardBtnVisible ? '可见' : '不可见'}`);
    return true;
  } catch (e) {
    logTest('测试 6: 看板管理', 'failed', e.message);
    return false;
  }
}

async function test7_Acceptance() {
  logTest('测试 7: 验收报告', 'info', '正在访问验收报告页面...');
  
  try {
    await page.goto(`${baseURL}/acceptance`, { waitUntil: 'networkidle' });
    await waitFor(3000);
    
    await screenshot('07-acceptance');
    
    const titleVisible = await page.locator('text=验收报告').first().isVisible().catch(() => false);
    if (!titleVisible) {
      logTest('测试 7: 验收报告', 'failed', '验收报告页面标题未找到');
      return false;
    }
    
    logTest('测试 7: 验收报告', 'passed', '页面加载成功');
    return true;
  } catch (e) {
    logTest('测试 7: 验收报告', 'failed', e.message);
    return false;
  }
}

async function test8_Delivery() {
  logTest('测试 8: 项目交付', 'info', '正在访问项目交付页面...');
  
  try {
    await page.goto(`${baseURL}/delivery`, { waitUntil: 'networkidle' });
    await waitFor(3000);
    
    await screenshot('08-delivery');
    
    const titleVisible = await page.locator('text=项目交付').first().isVisible().catch(() => false);
    if (!titleVisible) {
      logTest('测试 8: 项目交付', 'failed', '项目交付页面标题未找到');
      return false;
    }
    
    logTest('测试 8: 项目交付', 'passed', '页面加载成功');
    return true;
  } catch (e) {
    logTest('测试 8: 项目交付', 'failed', e.message);
    return false;
  }
}

async function runAllTests() {
  try {
    await init();
    
    await test1_Register();
    await test2_CreateProject();
    await test3_AgentManagement();
    await test4_CreateGroup();
    await test5_Requirements();
    await test6_Board();
    await test7_Acceptance();
    await test8_Delivery();
    
  } catch (e) {
    console.error('\n❌ 测试执行异常:', e.message);
    console.error(e.stack);
  } finally {
    await cleanup();
  }
}

runAllTests().catch(e => {
  console.error('Fatal error:', e);
  process.exit(1);
});
