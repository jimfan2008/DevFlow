import { test, expect } from '@playwright/test';

export async function verifyApiResponse(response, expectedStatus = 200) {
  expect(response.status()).toBe(expectedStatus);
  const data = await response.json();
  expect(data).toBeDefined();
  return data;
}

export async function waitForApiCompletion(page, urlPattern, timeout = 60000) {
  const response = await page.waitForResponse(
    resp => resp.url().includes(urlPattern) && resp.request().method() !== 'OPTIONS',
    { timeout }
  );
  return verifyApiResponse(response);
}

export async function waitForApiSuccess(page, urlPattern, timeout = 60000) {
  try {
    const data = await waitForApiCompletion(page, urlPattern, timeout);
    return { success: true, data };
  } catch (e) {
    return { success: false, error: e.message };
  }
}

export async function fillByPlaceholder(page, placeholder, value) {
  const selector = `input[placeholder="${placeholder}"], textarea[placeholder="${placeholder}"]`;
  await page.waitForSelector(selector, { timeout: 10000 });
  await page.fill(selector, value);
}

export async function clickByText(page, text, nth = 0) {
  const locator = page.getByText(text, { exact: true }).nth(nth);
  await locator.waitFor({ timeout: 10000, state: 'visible' });
  await locator.click();
}

export async function clickButtonByText(page, text) {
  const locator = page.locator(`button:has-text("${text}")`).first();
  await locator.waitFor({ timeout: 10000, state: 'visible' });
  await locator.click();
}

export async function waitForText(page, text, timeout = 15000) {
  await page.waitForSelector(`text=${text}`, { timeout });
}

export async function elementExists(page, selector, timeout = 10000) {
  try {
    await page.waitForSelector(selector, { timeout, state: 'visible' });
    return true;
  } catch {
    return false;
  }
}

export async function getTimestampedValue(value) {
  const timestamp = Date.now();
  return value.replace('{timestamp}', timestamp.toString());
}
