import { expect, test } from '@playwright/test';

test('renders the Phase 2 design-system showcase', async ({ page }) => {
  await page.goto('/');
  await expect(page.getByRole('heading', { name: 'Cloudflare-quality Angular primitives' })).toBeVisible();
  const viewport = page.viewportSize();
  if (viewport && viewport.width >= 1024) {
    await expect(page.getByRole('complementary', { name: 'Ask AI preview' })).toBeVisible();
  }
  await expect(page.getByRole('button', { name: 'Approve' })).toBeVisible();
  await expect(page.locator('body')).not.toContainText('/agent/actions/propose');
});

test('persists the dark theme choice', async ({ page }) => {
  await page.goto('/');
  await page.getByRole('button', { name: 'Use dark theme' }).click();
  await expect(page.locator('html')).toHaveAttribute('data-theme', 'dark');
  await page.reload();
  await expect(page.locator('html')).toHaveAttribute('data-theme', 'dark');
});
