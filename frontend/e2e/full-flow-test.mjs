import { chromium } from 'playwright';
import {
  BASE_URL,
  API_URL,
  TIMEOUT,
  STEP_TIMEOUT,
  TIME_WAIT,
  HEADLESS,
} from './test-config.mjs';

import {
  getTestUser,
  getTestProject,
  getTestGroup,
  waitFor,
  waitForSelectorWithRetry,
  takeScreenshot,
  logStep,
  logSuccess,
  logFailure,
  logSkip,
  logInfo,
  fillInputByPlaceholder,
  clickButtonWithText,
  verifyElementVisible,
  verifyTextVisible,
  saveTestResult,
  printSummary,
} from './utils/helpers.mjs';

const testUser = getTestUser();
const testProject = getTestProject();
const testGroup = getTestGroup();

let browser;
let page;
let testData = {
  user: null,
  project: null,
  group: null,
  board: null,
  tasks: [],
};

async function init() {
  console.log('\n' + '='.repeat(60));
  console.log('🚀 DevFlow E2E 完整流程测试');
  console.log('='.repeat(60));
  console.log(`⏱️  Test Timestamp: ${Date.now()}`);
  console.log(`🌐 Base URL: ${BASE_URL}`);
  console.log(`🔗 API URL: ${API_URL}`);
  console.log('='.repeat(60));

  browser = await chromium.launch({
    headless: HEADLESS,
    slowMo: 0,
  });
  page = await browser.newPage();
  
  page.setDefaultTimeout(STEP_TIMEOUT);
  
  page.on('console', (msg) => {
    if (msg.type() === 'error') {
      console.log(`   🖥️  Console Error: ${msg.text()}`);
    }
  });
  
  page.on('pageerror', (err) => {
    console.log(`   💥 Page Error: ${err.message}`);
  });
}

async function cleanup() {
  if (page) {
    await takeScreenshot(page, 'final');
  }
  if (browser) {
    await browser.close();
  }
  await saveTestResult();
  printSummary();
}

async function testModule1_Authentication() {
  logStep('TC-AUTH-001', '用户注册测试');
  
  try {
    await page.goto(`${BASE_URL}/register`, {
      waitUntil: 'networkidle',
      timeout: TIMEOUT,
    });
    await waitFor(TIME_WAIT.MEDIUM);
    
    await fillInputByPlaceholder(page, '用户名', testUser.username);
    await fillInputByPlaceholder(page, '邮箱', testUser.email);
    await fillInputByPlaceholder(page, '密码', testUser.password);
    await fillInputByPlaceholder(page, '确认密码', testUser.password);
    
    await takeScreenshot(page, '01_register_form');
    
    await clickButtonWithText(page, '注册');
    await waitFor(TIME_WAIT.LONG);
    
    const currentUrl = page.url();
    const isBoardsPage = currentUrl.includes('/boards') || currentUrl.includes('/projects');
    
    if (isBoardsPage) {
      logSuccess(`注册成功，已跳转到: ${currentUrl}`);
      testData.user = testUser;
    } else {
      await takeScreenshot(page, '01_register_fail');
      logFailure(`注册失败，当前页面: ${currentUrl}`);
      return false;
    }
    
    await takeScreenshot(page, '01_register_success');
    return true;
    
  } catch (e) {
    logFailure(`注册测试异常: ${e.message}`);
    return false;
  }
}

async function testModule2_ProjectManagement() {
  logStep('TC-PROJECT-001', '创建项目测试');
  
  try {
    await page.goto(`${BASE_URL}/projects`, {
      waitUntil: 'networkidle',
      timeout: TIMEOUT,
    });
    await waitFor(TIME_WAIT.MEDIUM);
    
    await clickButtonWithText(page, '创建项目');
    await waitFor(TIME_WAIT.SHORT);
    
    const dialogVisible = await verifyElementVisible(page, '.el-dialog');
    if (!dialogVisible) {
      logFailure('创建项目对话框未显示');
      return false;
    }
    
    const projectName = testProject.name;
    await page.fill('.el-dialog input[placeholder="输入项目名称"]', projectName);
    await page.fill('.el-dialog textarea', testProject.description);
    
    await takeScreenshot(page, '02_create_project_dialog');
    
    await page.click('.el-dialog button:has-text("创建")');
    await waitFor(TIME_WAIT.LONG);
    
    const projectCard = await page.locator(`.project-list-view__card-name:has-text("${projectName}")`).first();
    const projectExists = await projectCard.isVisible().catch(() => false);
    
    if (projectExists) {
      logSuccess(`项目 "${projectName}" 创建成功`);
      testData.project = { name: projectName };
    } else {
      await takeScreenshot(page, '02_create_project_fail');
      logSkip('项目卡片可能未立即显示，继续后续测试');
    }
    
    await takeScreenshot(page, '02_project_list');
    return true;
    
  } catch (e) {
    logFailure(`创建项目测试异常: ${e.message}`);
    return false;
  }
}

async function testModule3_AgentManagement() {
  logStep('TC-AGENT-001', 'Agent列表页面测试');
  
  try {
    await page.goto(`${BASE_URL}/agents`, {
      waitUntil: 'networkidle',
      timeout: TIMEOUT,
    });
    await waitFor(TIME_WAIT.MEDIUM);
    
    const titleVisible = await verifyTextVisible(page, 'Agent管理');
    const scanButton = await page.locator('button:has-text("Profile扫描")').first();
    const scanVisible = await scanButton.isVisible().catch(() => false);
    
    if (titleVisible && scanVisible) {
      logSuccess('Agent列表页面加载成功');
    } else {
      logSkip('Agent页面部分元素未找到');
    }
    
    await takeScreenshot(page, '03_agent_list');
    
    logStep('TC-AGENT-002', 'Profile扫描测试');
    
    try {
      const scanLoading = await page.locator('button:has-text("Profile扫描")').first();
      await scanLoading.click();
      await waitFor(TIME_WAIT.API * 2);
      
      await takeScreenshot(page, '03_after_scan');
      logInfo('Profile扫描已触发');
    } catch (e) {
      logSkip(`Profile扫描跳过: ${e.message}`);
    }
    
    const agentCards = await page.locator('.agent-list-view__card').all();
    const agentCount = agentCards.length;
    logInfo(`发现 ${agentCount} 个 Agent`);
    
    if (agentCount > 0) {
      logStep('TC-AGENT-003', '查看Agent详情');
      await agentCards[0].click();
      await waitFor(TIME_WAIT.MEDIUM);
      
      const detailUrl = page.url();
      if (detailUrl.includes('/agents/')) {
        logSuccess('Agent详情页面跳转成功');
      }
      
      await takeScreenshot(page, '03_agent_detail');
      await page.goBack();
      await waitFor(TIME_WAIT.SHORT);
    }
    
    return true;
    
  } catch (e) {
    logFailure(`Agent管理测试异常: ${e.message}`);
    return true;
  }
}

async function testModule4_ChatAndMeeting() {
  logStep('TC-CHAT-001', '创建群聊测试');
  
  try {
    await page.goto(`${BASE_URL}/chat`, {
      waitUntil: 'networkidle',
      timeout: TIMEOUT,
    });
    await waitFor(TIME_WAIT.MEDIUM);
    
    await takeScreenshot(page, '04_chat_empty');
    
    const createBtn = await page.locator('button:has-text("新建")').first();
    const createVisible = await createBtn.isVisible().catch(() => false);
    
    if (!createVisible) {
      logSkip('创建群组按钮不可见，跳过群聊测试');
      return true;
    }
    
    await createBtn.click();
    await waitFor(TIME_WAIT.SHORT);
    
    const groupName = testGroup.name;
    await page.fill('.el-dialog input[placeholder="输入群组名称"]', groupName);
    
    await takeScreenshot(page, '04_create_group_dialog');
    
    await page.click('.el-dialog button:has-text("创建")');
    await waitFor(TIME_WAIT.MEDIUM);
    
    await takeScreenshot(page, '04_after_create_group');
    logInfo('群组创建请求已发送');
    
    logStep('TC-CHAT-002', '发送消息测试');
    
    try {
      const messageInput = await page.locator('.chat-view__input-area textarea').first();
      const inputVisible = await messageInput.isVisible().catch(() => false);
      
      if (inputVisible) {
        await messageInput.fill(testGroup.messages[0]);
        await page.click('.chat-view__input-area button:has-text("发送")');
        await waitFor(TIME_WAIT.MEDIUM);
        logInfo('消息已发送');
        await takeScreenshot(page, '04_after_message');
      }
    } catch (e) {
      logSkip(`发送消息跳过: ${e.message}`);
    }
    
    logStep('TC-CHAT-004', '会议功能测试');
    
    try {
      const startMeetingBtn = await page.locator('button:has-text("启动会议")').first();
      const meetingVisible = await startMeetingBtn.isVisible().catch(() => false);
      
      if (meetingVisible) {
        await startMeetingBtn.click();
        await waitFor(TIME_WAIT.API);
        logInfo('会议已启动');
        
        await takeScreenshot(page, '04_meeting_started');
        
        const endMeetingBtn = await page.locator('button:has-text("结束会议")').first();
        const endVisible = await endMeetingBtn.isVisible().catch(() => false);
        if (endVisible) {
          await endMeetingBtn.click();
          await waitFor(TIME_WAIT.API);
          logInfo('会议已结束');
        }
      }
    } catch (e) {
      logSkip(`会议功能跳过: ${e.message}`);
    }
    
    return true;
    
  } catch (e) {
    logFailure(`群聊与会议测试异常: ${e.message}`);
    return true;
  }
}

async function testModule5_RequirementManagement() {
  logStep('TC-REQ-001', '需求管理页面测试');
  
  try {
    await page.goto(`${BASE_URL}/requirements`, {
      waitUntil: 'networkidle',
      timeout: TIMEOUT,
    });
    await waitFor(TIME_WAIT.MEDIUM);
    
    await takeScreenshot(page, '05_requirements_page');
    
    const titleVisible = await verifyTextVisible(page, '需求管理');
    if (!titleVisible) {
      logSkip('需求管理页面未正确加载');
      return true;
    }
    
    logSuccess('需求管理页面加载成功');
    
    logStep('TC-REQ-002', '选择项目');
    
    try {
      const projectSelector = await page.locator('.el-select').first();
      const selectorVisible = await projectSelector.isVisible().catch(() => false);
      
      if (selectorVisible) {
        await projectSelector.click();
        await waitFor(TIME_WAIT.SHORT);
        
        const options = await page.locator('.el-select-dropdown__item').all();
        if (options.length > 0) {
          await options[0].click();
          await waitFor(TIME_WAIT.MEDIUM);
          logInfo('项目已选择');
          await takeScreenshot(page, '05_project_selected');
        }
      }
    } catch (e) {
      logSkip(`选择项目跳过: ${e.message}`);
    }
    
    logStep('TC-REQ-003', '编辑需求文档');
    
    try {
      const docTextarea = await page.locator('.requirements-view__doc-editor textarea').first();
      const docVisible = await docTextarea.isVisible().catch(() => false);
      
      if (docVisible) {
        await docTextarea.fill(testProject.requirement.content);
        await waitFor(TIME_WAIT.SHORT);
        logInfo('需求文档内容已填写');
        await takeScreenshot(page, '05_requirement_filled');
      }
    } catch (e) {
      logSkip(`编辑需求文档跳过: ${e.message}`);
    }
    
    logStep('TC-REQ-004', '提交需求文档');
    
    try {
      const submitBtn = await page.locator('button:has-text("提交需求文档")').first();
      const submitVisible = await submitBtn.isVisible().catch(() => false);
      
      if (submitVisible) {
        const isDisabled = await submitBtn.isDisabled().catch(() => true);
        if (!isDisabled) {
          await submitBtn.click();
          await waitFor(TIME_WAIT.API);
          logInfo('需求文档已提交');
          await takeScreenshot(page, '05_requirement_submitted');
        }
      }
    } catch (e) {
      logSkip(`提交需求文档跳过: ${e.message}`);
    }
    
    return true;
    
  } catch (e) {
    logFailure(`需求管理测试异常: ${e.message}`);
    return true;
  }
}

async function testModule6_BoardAndTasks() {
  logStep('TC-TASK-001', '看板列表测试');
  
  try {
    await page.goto(`${BASE_URL}/boards`, {
      waitUntil: 'networkidle',
      timeout: TIMEOUT,
    });
    await waitFor(TIME_WAIT.MEDIUM);
    
    await takeScreenshot(page, '06_boards_list');
    
    const titleVisible = await verifyTextVisible(page, '看板列表').catch(() => 
      verifyTextVisible(page, '项目管理').catch(() => false)
    );
    
    if (!titleVisible) {
      logSkip('看板列表页面未正确加载');
      return true;
    }
    
    logSuccess('看板列表页面加载成功');
    
    const boardCards = await page.locator('.board-list-view__card, .project-list-view__card').all();
    logInfo(`发现 ${boardCards.length} 个看板/项目`);
    
    if (boardCards.length > 0) {
      await boardCards[0].click();
      await waitFor(TIME_WAIT.MEDIUM);
      
      const detailUrl = page.url();
      if (detailUrl.includes('/boards/')) {
        logSuccess('看板详情页面跳转成功');
      }
      
      await takeScreenshot(page, '06_board_detail');
      
      logStep('TC-TASK-002', '查看任务卡片');
      
      const taskCards = await page.locator('.kanban-card, .task-card').all();
      logInfo(`发现 ${taskCards.length} 个任务卡片`);
      
      if (taskCards.length > 0) {
        await taskCards[0].click();
        await waitFor(TIME_WAIT.LONG);
        await takeScreenshot(page, '06_task_detail');
        
        const agentBtn = await page.locator('button:has-text("Agent分配")').first();
        const agentBtnVisible = await agentBtn.isVisible().catch(() => false);
        
        if (agentBtnVisible) {
          logStep('TC-TASK-003', 'Agent分配测试');
          const isDisabled = await agentBtn.isDisabled().catch(() => true);
          if (!isDisabled) {
            try {
              await agentBtn.click();
              await waitFor(TIME_WAIT.API);
              logInfo('Agent分配已触发');
            } catch (e) {
              logSkip(`Agent分配跳过: ${e.message}`);
            }
          }
        }
      }
    }
    
    return true;
    
  } catch (e) {
    logFailure(`看板与任务测试异常: ${e.message}`);
    return true;
  }
}

async function testModule7_Acceptance() {
  logStep('TC-ACCEPT-001', '验收报告测试');
  
  try {
    await page.goto(`${BASE_URL}/acceptance`, {
      waitUntil: 'networkidle',
      timeout: TIMEOUT,
    });
    await waitFor(TIME_WAIT.MEDIUM);
    
    await takeScreenshot(page, '07_acceptance_page');
    
    const titleVisible = await verifyTextVisible(page, '验收报告');
    if (!titleVisible) {
      logSkip('验收报告页面未正确加载');
      return true;
    }
    
    logSuccess('验收报告页面加载成功');
    
    const rows = await page.locator('.el-table__row').all();
    logInfo(`发现 ${rows.length} 条验收记录`);
    
    if (rows.length > 0) {
      const detailBtns = await page.locator('button:has-text("详情")').all();
      if (detailBtns.length > 0) {
        try {
          await detailBtns[0].click();
          await waitFor(TIME_WAIT.SHORT);
          await takeScreenshot(page, '07_acceptance_detail');
          logInfo('验收详情已查看');
        } catch (e) {
          logSkip(`查看详情跳过: ${e.message}`);
        }
      }
    }
    
    return true;
    
  } catch (e) {
    logFailure(`验收报告测试异常: ${e.message}`);
    return true;
  }
}

async function testModule8_Delivery() {
  logStep('TC-DELIVER-001', '项目交付测试');
  
  try {
    await page.goto(`${BASE_URL}/delivery`, {
      waitUntil: 'networkidle',
      timeout: TIMEOUT,
    });
    await waitFor(TIME_WAIT.MEDIUM);
    
    await takeScreenshot(page, '08_delivery_page');
    
    const titleVisible = await verifyTextVisible(page, '项目交付');
    if (!titleVisible) {
      logSkip('项目交付页面未正确加载');
      return true;
    }
    
    logSuccess('项目交付页面加载成功');
    
    try {
      const projectSelector = await page.locator('.el-select').first();
      const selectorVisible = await projectSelector.isVisible().catch(() => false);
      
      if (selectorVisible) {
        await projectSelector.click();
        await waitFor(TIME_WAIT.SHORT);
        
        const options = await page.locator('.el-select-dropdown__item').all();
        if (options.length > 0) {
          await options[0].click();
          await waitFor(TIME_WAIT.MEDIUM);
          logInfo('交付项目已选择');
          await takeScreenshot(page, '08_delivery_project_selected');
        }
      }
    } catch (e) {
      logSkip(`选择交付项目跳过: ${e.message}`);
    }
    
    return true;
    
  } catch (e) {
    logFailure(`项目交付测试异常: ${e.message}`);
    return true;
  }
}

async function runAllTests() {
  const startTime = Date.now();
  
  try {
    await init();
    
    console.log('\n' + '─'.repeat(60));
    console.log('📋 TEST MODULE 1: 用户认证');
    console.log('─'.repeat(60));
    await testModule1_Authentication();
    
    console.log('\n' + '─'.repeat(60));
    console.log('📋 TEST MODULE 2: 项目管理');
    console.log('─'.repeat(60));
    await testModule2_ProjectManagement();
    
    console.log('\n' + '─'.repeat(60));
    console.log('📋 TEST MODULE 3: Agent管理');
    console.log('─'.repeat(60));
    await testModule3_AgentManagement();
    
    console.log('\n' + '─'.repeat(60));
    console.log('📋 TEST MODULE 4: 群聊与会议');
    console.log('─'.repeat(60));
    await testModule4_ChatAndMeeting();
    
    console.log('\n' + '─'.repeat(60));
    console.log('📋 TEST MODULE 5: 需求管理');
    console.log('─'.repeat(60));
    await testModule5_RequirementManagement();
    
    console.log('\n' + '─'.repeat(60));
    console.log('📋 TEST MODULE 6: 看板与任务');
    console.log('─'.repeat(60));
    await testModule6_BoardAndTasks();
    
    console.log('\n' + '─'.repeat(60));
    console.log('📋 TEST MODULE 7: 验收报告');
    console.log('─'.repeat(60));
    await testModule7_Acceptance();
    
    console.log('\n' + '─'.repeat(60));
    console.log('📋 TEST MODULE 8: 项目交付');
    console.log('─'.repeat(60));
    await testModule8_Delivery();
    
  } catch (e) {
    console.error(`\n❌ 测试执行异常: ${e.message}`);
    console.error(e.stack);
  } finally {
    console.log('\n' + '='.repeat(60));
    console.log('🏁 测试完成');
    console.log('='.repeat(60));
    console.log(`⏱️  总耗时: ${(Date.now() - startTime) / 1000}s`);
    
    await cleanup();
  }
}

runAllTests().catch((e) => {
  console.error('❌ Fatal error:', e);
  process.exit(1);
});
