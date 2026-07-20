import { expect, test } from '@playwright/test';

test('renders and navigates the complete workplace shell', async ({ page }) => {
  await page.goto('/');
  await expect(page.getByRole('heading', { name: "Let's get to work." })).toBeVisible();
  await expect(page.getByText('SARA AI', { exact: true })).toBeVisible();
  const subtitle = page.getByText('RAG ENGINE ONLINE', { exact: true });
  const viewport = page.viewportSize();
  if (viewport && viewport.width < 768) {
    await expect(subtitle).toBeHidden();
    await page.getByRole('button', { name: 'Open navigation' }).click();
  } else {
    await expect(subtitle).toBeVisible();
  }
  await page.getByRole('button', { name: /Users/ }).first().click();
  await expect(page.getByRole('heading', { name: 'Users' })).toBeVisible();
  await expect(page.locator('body')).not.toContainText('Cloudflare');
  await expect(page.locator('body')).not.toContainText('Workplace Agent');
  await expect(page.locator('body')).not.toContainText('/agent/actions/propose');
});

test('opens and closes the responsive Ask AI panel', async ({ page }) => {
  await page.goto('/');
  const panel = page.getByRole('complementary', { name: 'Ask SARA' });
  const toggle = page.getByRole('button', { name: /Ask SARA/ }).first();
  await expect(toggle).toBeVisible();
  if (!(await panel.isVisible())) {
    await toggle.click();
  }
  const close = panel.getByRole('button', { name: 'Close Ask SARA' });
  await expect(close).toBeVisible();
  await close.click();
  await expect(panel).toHaveCount(0);
  await toggle.click();
  await expect(panel).toBeVisible();
});

test('keeps the SARA panel fixed while the workspace scrolls', async ({ page }) => {
  await page.goto('/');
  const panel = page.getByRole('complementary', { name: 'Ask SARA' });
  const toggle = page.getByRole('button', { name: /Ask SARA/ }).first();
  if (!(await panel.isVisible())) {
    await toggle.click();
  }
  await expect(panel).toBeVisible();

  const assistantTopBefore = await panel.evaluate(element => element.getBoundingClientRect().top);
  await page.locator('.shell-workspace').evaluate(element => {
    const spacer = document.createElement('div');
    spacer.style.height = '2200px';
    spacer.setAttribute('data-testid', 'scroll-spacer');
    element.appendChild(spacer);
    element.scrollTop = 1200;
  });

  await expect.poll(() => page.locator('.shell-workspace').evaluate(element => element.scrollTop)).toBeGreaterThan(0);
  const assistantTopAfter = await panel.evaluate(element => element.getBoundingClientRect().top);
  expect(assistantTopAfter).toBe(assistantTopBefore);
  expect(await page.evaluate(() => document.scrollingElement?.scrollTop ?? -1)).toBe(0);
  await expect(panel.getByRole('textbox', { name: 'Ask SARA' })).toBeVisible();
});

test('persists the dark theme choice', async ({ page }) => {
  await page.goto('/');
  await page.getByRole('button', { name: 'Open account preferences' }).click();
  await page.getByRole('button', { name: 'Use dark theme' }).click();
  await expect(page.locator('html')).toHaveAttribute('data-theme', 'dark');
  await page.reload();
  await expect(page.locator('html')).toHaveAttribute('data-theme', 'dark');
});
