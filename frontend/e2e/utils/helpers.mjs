import { TIMEOUT, TIME_WAIT } from '../test-config.mjs';
import fs from 'fs';
import path from 'path';

export const timestamp = Date.now();
let stepCount = 0;
let resultData = {
  startAt: new Date().toISOString(),
  timestamp: timestamp,
  passed: 0,
  failed: 0,
  skipped: 0,
  steps: [],
  endAt: null,
  totalDuration: 0,
};

export function replaceTimestamp(str) {
  return str.replace(/{timestamp}/g, timestamp.toString());
}

export function loadTestData() {
  const dataPath = path.resolve('./e2e/test-data.json');
  const raw = fs.readFileSync(dataPath, 'utf-8');
  let data = JSON.parse(raw);
  
  data = JSON.parse(replaceTimestamp(JSON.stringify(data)));
  return data;
}

export function getTestUser() {
  const data = loadTestData();
  return data.testUser;
}

export function getTestProject() {
  const data = loadTestData();
  return data.testProject;
}

export function getTestGroup() {
  const data = loadTestData();
  return data.testGroup;
}

export async function waitFor(ms) {
  return new Promise(resolve => setTimeout(resolve, ms));
}

export async function waitForSelectorWithRetry(page, selector, options = {}) {
  const timeout = options.timeout || TIMEOUT;
  const retries = options.retries || 3;
  const interval = options.interval || 1000;
  
  let lastError = null;
  for (let i = 0; i < retries; i++) {
    try {
      return await page.waitForSelector(selector, { timeout: timeout / retries });
    } catch (e) {
      lastError = e;
      if (i < retries - 1) await waitFor(interval);
    }
  }
  throw lastError;
}

export async function takeScreenshot(page, name) {
  const dir = './e2e/screenshots';
  if (!fs.existsSync(dir)) {
    fs.mkdirSync(dir, { recursive: true });
  }
  const filename = `${dir}/${timestamp}_${String(++stepCount).padStart(2, '0')}_${name}.png`;
  try {
    await page.screenshot({ path: filename, fullPage: false });
    console.log(`   📸 Screenshot: ${filename}`);
  } catch (e) {
    console.log(`   ⚠️  Screenshot failed: ${e.message}`);
  }
  return filename;
}

export function logStep(step, message, status = 'info') {
  const statusIcon = status === 'success' ? '✅' : status === 'fail' ? '❌' : status === 'skip' ? '⚠️' : 'ℹ️';
  console.log(`\n${statusIcon} [${step}] ${message}`);
  
  if (status !== 'info') {
    resultData.steps.push({
      step: step,
      message: message,
      status: status,
      timestamp: new Date().toISOString(),
    });
  }
}

export function logSuccess(message) {
  console.log(`   ✅ ${message}`);
  resultData.passed++;
}

export function logFailure(message) {
  console.log(`   ❌ ${message}`);
  resultData.failed++;
}

export function logSkip(message) {
  console.log(`   ⚠️  ${message}`);
  resultData.skipped++;
}

export function logInfo(message) {
  console.log(`   ℹ️  ${message}`);
}

export async function fillInputByPlaceholder(page, placeholder, value) {
  const selector = `input[placeholder="${placeholder}"], textarea[placeholder="${placeholder}"]`;
  await waitForSelectorWithRetry(page, selector);
  await page.fill(selector, value);
  await waitFor(TIME_WAIT.SHORT);
}

export async function clickButtonWithText(page, text) {
  const selector = `button:has-text("${text}")`;
  await waitForSelectorWithRetry(page, selector);
  await page.click(selector);
}

export async function verifyElementVisible(page, selector, timeout = TIME_WAIT.MEDIUM) {
  try {
    await page.waitForSelector(selector, { timeout, state: 'visible' });
    return true;
  } catch {
    return false;
  }
}

export async function verifyTextVisible(page, text, timeout = TIME_WAIT.MEDIUM) {
  try {
    await page.waitForSelector(`text="${text}"`, { timeout });
    return true;
  } catch {
    return false;
  }
}

export async function saveTestResult() {
  resultData.endAt = new Date().toISOString();
  resultData.totalDuration = (new Date(resultData.endAt) - new Date(resultData.startAt)) / 1000;
  
  const dir = './e2e/results';
  if (!fs.existsSync(dir)) {
    fs.mkdirSync(dir, { recursive: true });
  }
  
  const filename = `${dir}/result_${timestamp}.json`;
  fs.writeFileSync(filename, JSON.stringify(resultData, null, 2), 'utf-8');
  console.log(`\n📊 Test result saved to: ${filename}`);
  
  return resultData;
}

export function printSummary() {
  console.log('\n' + '='.repeat(60));
  console.log('📊 TEST SUMMARY');
  console.log('='.repeat(60));
  console.log(`✅ Passed:  ${resultData.passed}`);
  console.log(`❌ Failed:  ${resultData.failed}`);
  console.log(`⚠️  Skipped: ${resultData.skipped}`);
  console.log(`⏱️  Duration: ${resultData.totalDuration || (Date.now() - new Date(resultData.startAt).getTime()) / 1000}s`);
  console.log('='.repeat(60));
}
