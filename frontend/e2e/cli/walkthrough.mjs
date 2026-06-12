/**
 * 真人操作：Step2 全流程逐步演示
 * 使用：node e2e/cli/walkthrough.mjs
 */
import { chromium } from 'playwright';
import fs from 'fs';

const BASE = process.env.BASE_URL || 'http://localhost:3000';
const TS = Date.now();
const DIR = path.resolve('e2e/cli/screenshots');
fs.mkdirSync(DIR, { recursive: true });

const USER = { username: `human_${TS}`, email: `human_${TS}@devflow.io`, password: 'Test@1234' };
let page, browser, context;

async function shot(name) {
  await page.screenshot({ path: `${DIR}/${name}.png`, fullPage: false });
  console.log(`  📸 ${name}`);
}

async function wait(ms) {
  await new Promise(r => setTimeout(r, ms));
}

async function step(label, fn) {
  console.log(`\n━━━ ${label} ━━━`);
  try { await fn(); console.log(`  ✅ ${label}`); }
  catch (e) { console.log(`  ❌ ${label}: ${e.message}`); throw e; }
}

async function fillByPlaceholder(placeholder, value) {
  const el = page.locator(`input[placeholder="${placeholder}"]`).first();
  await el.waitFor({ state: 'visible', timeout: 5000 });
  await el.fill(value);
  console.log(`  填 "${placeholder}" → ${value}`);
}

async function clickButton(text, force = false) {
  const btn = page.locator(`button:has-text("${text}")`).first();
  await btn.waitFor({ state: 'visible', timeout: 5000 });
  await btn.click({ force });
  console.log(`  点击 "${text}"${force ? ' (force)' : ''}`);
}

async function main() {
  console.log('══════════════════════════════════════════════');
  console.log('  真人操作演示：DevFlow Step2 全流程');
  console.log(`  时间: ${new Date().toISOString()}`);
  console.log(`  前端地址: ${BASE}`);
  console.log(`  用户: ${USER.username} / ${USER.email}`);
  console.log('══════════════════════════════════════════════\n');

  browser = await chromium.launch({ headless: true, args: ['--no-sandbox'] });
  context = await browser.newContext({ viewport: { width: 1440, height: 900 } });
  page = await context.newPage();

  // ── 1. 打开登录页面 ──
  await step('打开登录页面', async () => {
    await page.goto(`${BASE}/login`, { waitUntil: 'networkidle' });
    await shot('01-login');
    console.log(`  URL: ${page.url()}`);
  });

  // ── 2. 尝试登录 ──
  await step('填写登录表单（用邮箱）', async () => {
    await fillByPlaceholder('邮箱', USER.email);
    await fillByPlaceholder('密码', USER.password);
    await clickButton('登录');
    await wait(2000);
    await shot('02-login-attempt');
    console.log(`  URL: ${page.url()}`);
  });

  // ── 3. 如果登录失败，注册 ──
  if (page.url().includes('login')) {
    console.log('  ⚠️ 登录失败 → 去注册');
    await step('跳转注册', async () => {
      await page.goto(`${BASE}/register`, { waitUntil: 'networkidle' });
      await shot('03-register');
    });

    await step('填写注册表单', async () => {
      await fillByPlaceholder('用户名', USER.username);
      await fillByPlaceholder('邮箱', USER.email);
      await fillByPlaceholder('密码', USER.password);
      await fillByPlaceholder('确认密码', USER.password);
      await shot('04-register-filled');
      await clickButton('注册');
      await wait(3000);
      await shot('04-registered');
      console.log(`  URL: ${page.url()}`);
    });

    if (page.url().includes('login')) {
      // 注册后需要手动登录
      await step('注册完毕，手动登录', async () => {
        await fillByPlaceholder('邮箱', USER.email);
        await fillByPlaceholder('密码', USER.password);
        await clickButton('登录');
        await wait(3000);
        await shot('05-login2');
        console.log(`  URL: ${page.url()}`);
      });
    } else {
      // 注册后已自动登录（直接到了 /boards）
      console.log('  ✅ 注册后已自动登录');
    }
  }

  // ── 4. 进入看板 ──
  await step('进入看板', async () => {
    if (page.url().includes('login')) {
      // 又被重定向到登录
      await fillByPlaceholder('邮箱', USER.email);
      await fillByPlaceholder('密码', USER.password);
      await clickButton('登录');
      await wait(3000);
    }
    if (!page.url().includes('boards')) {
      await page.goto(`${BASE}/boards`, { waitUntil: 'networkidle' });
    }
    await shot('06-boards');
    console.log(`  URL: ${page.url()}`);
  });

  // ── 5. 创建项目 ──
  await step('创建新项目（看板）', async () => {
    await clickButton('创建看板');
    await wait(1000);
    await shot('07-create-dialog');
    const projName = `Step2演示_${TS}`;
    await fillByPlaceholder('看板名称', projName);
    console.log(`  项目名: ${projName}`);
    await clickButton('创建', true);
    await wait(3000);
    await shot('07-created');
    console.log(`  URL: ${page.url()}`);
  });

  // ── 6. 进入项目 → 流程 → Step2 ──
  await step('进入项目详情', async () => {
    await page.goto(`${BASE}/projects`, { waitUntil: 'networkidle' });
    await wait(2000);
    await shot('08-projects-list');
    console.log(`  URL: ${page.url()}`);

    // 点击项目卡片（el-card）
    const card = page.locator('.project-list-view__card').first();
    if (await card.isVisible()) {
      console.log('  点击项目卡片...');
      await card.click({ force: true });
      await wait(2000);
    }
    await shot('08-project-detail');
    console.log(`  URL: ${page.url()}`);
  });

  await step('切换到流程步骤Tab', async () => {
    const tab = page.locator('button:has-text("流程"), button:has-text("步骤"), .el-tabs .el-tabs__item:has-text("流程")').first();
    if (await tab.isVisible()) {
      console.log('  点击流程步骤Tab...');
      await tab.click({ force: true });
      await wait(1500);
    }
    await shot('09-tabs');
    console.log(`  URL: ${page.url()}`);
  });

  await step('进入 Step2', async () => {
    // 如果URL包含projectId，直接导航到step2
    const urlPath = page.url();
    const projMatch = urlPath.match(/\/projects\/([^\/\?]+)/);
    if (projMatch) {
      const projId = projMatch[1];
      console.log(`  项目ID: ${projId}，直接导航到 Step2 页面`);
      await page.goto(`${BASE}/step2/${projId}`, { waitUntil: 'networkidle' });
      await wait(2000);
    } else {
      // 否则在页面上找 Step2 入口
      const step2 = page.locator('text=核心目标确认').first();
      if (await step2.isVisible()) {
        await step2.click({ force: true });
        await wait(2000);
      }
    }
    await shot('10-step2');
    console.log(`  URL: ${page.url()}`);
  });

  // ── 7. 走 Step2 流程 ──
  await step('观察 HaiMei 打招呼', async () => {
    // 需要启动的话就点启动
    const start = page.locator('button:has-text("开始"), button:has-text("启动"), button:has-text("Execute")').first();
    if (await start.isVisible()) {
      await start.click();
      await wait(2000);
    }
    await wait(1000);
    await shot('11-haimei');
    const body = await page.locator('body').innerText();
    const lines = body.split('\n').filter(l => l.trim()).slice(0, 15);
    lines.forEach(l => console.log(`  ${l.trim()}`));
  });

  await step('给海梅发消息', async () => {
    // 找聊天输入框 (step2-view__chat-input 内的 textarea)
    const chatArea = page.locator('.step2-view__chat-input textarea, .step2-view__chat-input .el-textarea__inner').first();
    if (await chatArea.isVisible()) {
      await chatArea.click();
      await chatArea.fill('我们想做AI驱动的DevOps协作平台，核心是自动化工作流管理');
      await wait(500);
      await shot('12-chat-typed');
      // 用 Ctrl+Enter 发送
      await chatArea.press('Control+Enter');
      await wait(3000);
      await shot('12-chat-reply');
    } else {
      console.log('  ⚠️ 未找到聊天输入框');
    }
  });

  await step('多轮对话 + 确认核心目标', async () => {
    const chatArea = page.locator('.step2-view__chat-input textarea, .step2-view__chat-input .el-textarea__inner').first();
    if (await chatArea.isVisible()) {
      await chatArea.click();
      await chatArea.fill('核心目标是建立端到端的CI/CD工作流自动化管理平台');
      await wait(500);
      await chatArea.press('Control+Enter');
      await wait(3000);
    }
    // 看是否进入了 confirming 阶段
    const body = await page.locator('body').innerText();
    if (body.includes('确认核心目标')) {
      // 点击确认核心目标按钮
      const confirmBtn = page.locator('button:has-text("确认核心目标")').first();
      if (await confirmBtn.isVisible()) {
        await confirmBtn.click({ force: true });
        await wait(2000);
        console.log('  ✅ 核心目标已确认');
      }
    }
    await shot('13-confirmed');
    const text = await page.locator('body').innerText();
    if (text.includes('搭建架构')) console.log('  ✅ 已进入搭建架构阶段');
    else console.log('  ⚠️ 仍然在聊天阶段（可能API调用失败）');
  });

  await step('查看组织架构（9个Agent）', async () => {
    await wait(1000);
    await shot('14-agents');
    const body = await page.locator('body').innerText();
    const agents = ['海梅', '后浪', '后发', '后达', '后华', '后贵', '后荣', '后莱', '后鹏'];
    let found = 0;
    for (const a of agents) {
      const ok = body.includes(a);
      if (ok) found++;
      console.log(`  ${ok ? '✅' : '❌'} ${a}`);
    }
    console.log(`  已找到 ${found}/9 个Agent角色`);
  });

  await step('创建讨论群', async () => {
    const create = page.locator('button:has-text("创建群"), button:has-text("创建讨论"), button:has-text("创建组")').first();
    if (await create.isVisible()) {
      await create.click();
      await wait(2000);
      console.log('  ✅ 创建讨论群');
    }
    await shot('15-group');
  });

  await step('QA 检验', async () => {
    await wait(1000);
    const pass = page.locator('button:has-text("通过")').first();
    if (await pass.isVisible()) {
      await pass.click();
      await wait(1500);
      console.log('  ✅ QA 通过');
    }
    await shot('16-qa');
  });

  await step('查看完成状态', async () => {
    await wait(1000);
    await shot('17-complete');
    const body = await page.locator('body').innerText();
    if (body.includes('完成')) console.log('  ✅ 第二步已完成！');
    const top = body.split('\n').filter(l => l.trim()).slice(0, 15);
    top.forEach(l => console.log(`  ${l.trim()}`));
    console.log(`  URL: ${page.url()}`);
  });

  console.log('\n══════════════════════════════════════════════');
  console.log('  🎉 全流程演示完成！');
  console.log(`  截图: ${DIR}/`);
  console.log('══════════════════════════════════════════════');

  await browser.close();
}

import path from 'path';
main().catch(e => {
  console.error(`\n❌ 崩溃: ${e.message}`);
  process.exit(1);
});
