import { expect, test } from '@playwright/test';

test('renders and navigates the complete workplace shell', async ({ page }) => {
  await page.goto('/');
  await expect(page.getByRole('heading', { name: "Let's get to work." })).toBeVisible();
  const viewport = page.viewportSize();
  if (viewport && viewport.width < 768) {
    await page.getByRole('button', { name: 'Open navigation' }).click();
  }
  await page.getByRole('button', { name: /Users/ }).first().click();
  await expect(page.getByRole('heading', { name: 'Users' })).toBeVisible();
  await expect(page.locator('body')).not.toContainText('Cloudflare');
  await expect(page.locator('body')).not.toContainText('/agent/actions/propose');
});

test('opens and closes the responsive Ask AI panel', async ({ page }) => {
  await page.goto('/');
  const panel = page.getByRole('complementary', { name: 'Ask AI' });
  const toggle = page.getByRole('button', { name: /Ask AI/ }).first();
  await expect(toggle).toBeVisible();
  if (!(await panel.isVisible())) {
    await toggle.click();
  }
  const close = panel.getByRole('button', { name: 'Close Ask AI' });
  await expect(close).toBeVisible();
  await close.click();
  await expect(panel).toHaveCount(0);
  await toggle.click();
  await expect(panel).toBeVisible();
});

test('persists the dark theme choice', async ({ page }) => {
  await page.goto('/');
  await page.getByRole('button', { name: 'Open account preferences' }).click();
  await page.getByRole('button', { name: 'Use dark theme' }).click();
  await expect(page.locator('html')).toHaveAttribute('data-theme', 'dark');
  await page.reload();
  await expect(page.locator('html')).toHaveAttribute('data-theme', 'dark');
});
